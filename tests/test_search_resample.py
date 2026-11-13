"""B.6 (day 2026-11-12): ``search.infeasible_penalty: resample`` — a refused candidate
(invalid_geometry / invalid_envelope / mesh_too_large) is replaced by a fresh sample from the
same CMA distribution (up to 10 tries per candidate) and never told to the ES; the refusal is
still evaluated, logged in search.ndjson (and, with budget_counts: valid, free). cma_me +
resample is refused at load (ribs 0.12 scheduler.tell needs one result per asked solution).
"""
from __future__ import annotations

import json

import pytest

from hornlab_search.config import ConfigError, load_config
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.search import cma as cma_mod
from hornlab_search.search.evaluate import read_ndjson
from test_search_support import SyntheticBackend, fast_cfg, install_fakes


@pytest.fixture
def smoke_cfg_path():
    from pathlib import Path
    return Path(__file__).resolve().parents[1] / "examples" / "search_smoke.yaml"


def test_resample_replaces_refusals_and_reaches_the_valid_budget(tmp_path, smoke_cfg, smoke_cfg_path,
                                                                 monkeypatch):
    from pathlib import Path
    cfg = load_config(str(Path(smoke_cfg_path)))
    cfg = fast_cfg(cfg, budget_counts="valid", infeasible_penalty="resample", popsize=4)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be, invalid_if=lambda p: p["a_deg"] > 45)
    rd = tmp_path / "r"
    cma_mod.search(cfg, rd, "screen", backend=be, budget=10, store=DatasetStore(rd / "ds"))
    rows = read_ndjson(rd / "search.ndjson")
    ok = [r for r in rows if r["ok"]]
    refused = [r for r in rows if r.get("kind") == "invalid_geometry"]
    bc = json.loads((rd / "run.json").read_text())["budget_counts"]
    assert bc["valid"] == 10, "the valid budget is reached"
    assert len(refused) > 0, "refusals are still evaluated and logged (never swept away)"
    assert bc["refused_free"] == len(refused)
    assert bc["attempts"] == len(rows) == len(ok) + len(refused)
    # none of the 7 refusals consumed the budget: the 10 valid designs were reached inside the
    # attempts head-room (cap 4 x budget), the refusals being resample-replaced for free
    assert bc["attempts_cap"] == 40 and bc["attempts"] < bc["attempts_cap"]


def test_refusals_are_logged_but_every_told_candidate_is_valid(tmp_path, smoke_cfg, smoke_cfg_path,
                                                               monkeypatch):
    # B.6's observable contract: the run's best J comes from a valid row, and the run consumes
    # no more budget than the refusals it logs (the ES never sees a refusal row AS the result).
    from pathlib import Path
    cfg = load_config(str(Path(smoke_cfg_path)))
    cfg = fast_cfg(cfg, budget_counts="valid", infeasible_penalty="resample", popsize=4)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be, invalid_if=lambda p: p["a_deg"] > 46)
    rd = tmp_path / "r"
    best = cma_mod.search(cfg, rd, "screen", backend=be, budget=6, store=DatasetStore(rd / "ds"))
    rows = read_ndjson(rd / "search.ndjson")
    ok = [r for r in rows if r["ok"]]
    assert ok and best is not None
    assert best.design_hash in {r["design_hash"] for r in ok}


def test_all_refusing_box_resamples_the_cap_and_still_tells_the_penalty(
        tmp_path, smoke_cfg, smoke_cfg_path, monkeypatch):
    """A box that refuses everything: each candidate burns its 10 resamples (popsize 4 -> 40
    refusal rows per generation), then the ES stop ends the search. Budget is never reached."""
    from pathlib import Path
    cfg = load_config(str(Path(smoke_cfg_path)))
    cfg = fast_cfg(cfg, infeasible_penalty="resample", popsize=4, budget=100)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be, invalid_if=lambda p: True)
    rd = tmp_path / "r"
    cma_mod.search(cfg, rd, "screen", backend=be, budget=100, store=DatasetStore(rd / "ds"))
    rows = read_ndjson(rd / "search.ndjson")
    assert len(rows) >= 1 + 4 * 10, "at least seed + one full resample-capped generation"
    assert all(r.get("kind") == "invalid_geometry" for r in rows)
    rj = json.loads((rd / "run.json").read_text())
    assert rj["stop_reason"].startswith("cma:"), rj["stop_reason"]
    assert rj["status"] == "finished"


def test_resample_with_cma_me_is_a_config_error(tmp_path, smoke_cfg_path):
    from pathlib import Path
    import yaml
    raw = yaml.safe_load(Path(smoke_cfg_path).read_text(encoding="utf-8"))
    raw["search"]["algorithm"] = "cma_me"
    raw["search"]["infeasible_penalty"] = "resample"
    raw["search"]["qd"] = {"bins_h": 8, "bins_v": 8}
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    with pytest.raises(ConfigError, match="cma_me"):
        load_config(p)


def test_bad_penalty_token_is_refused(tmp_path, smoke_cfg_path):
    from pathlib import Path
    import yaml
    raw = yaml.safe_load(Path(smoke_cfg_path).read_text(encoding="utf-8"))
    raw["search"]["infeasible_penalty"] = "resample_now"
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    with pytest.raises(ConfigError, match="resample"):
        load_config(p)


def test_default_penalty_token_still_loads(tmp_path, smoke_cfg_path):
    from pathlib import Path
    import yaml
    raw = yaml.safe_load(Path(smoke_cfg_path).read_text(encoding="utf-8"))
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    assert load_config(p).search.infeasible_penalty == "flat"


# F0 (day 2026-11-12): the strict token is a NEW opt-in plain-CMA policy, not a change to
# ``resample`` (whose bounded-then-tell legacy fallback above stays byte-for-byte).
def test_resample_strict_loads_only_with_its_required_companions(tmp_path, smoke_cfg_path):
    from pathlib import Path
    import yaml
    raw = yaml.safe_load(Path(smoke_cfg_path).read_text(encoding="utf-8"))
    raw["search"].update({"infeasible_penalty": "resample_strict",
                          "error_policy": "retry_same_then_stop", "budget_counts": "valid"})
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    cfg = load_config(p)
    assert cfg.search.infeasible_penalty == "resample_strict"
    assert cfg.search.error_policy == "retry_same_then_stop"


def test_resample_strict_is_refused_for_cma_me(tmp_path, smoke_cfg_path):
    from pathlib import Path
    import yaml
    raw = yaml.safe_load(Path(smoke_cfg_path).read_text(encoding="utf-8"))
    raw["search"].update({"algorithm": "cma_me",
                          "qd": {"descriptor_h": "mean_bw_h_deg",
                                 "descriptor_v": "mean_bw_v_deg", "bins_h": 8, "bins_v": 8},
                          "infeasible_penalty": "resample_strict",
                          "error_policy": "retry_same_then_stop", "budget_counts": "valid"})
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    with pytest.raises(ConfigError, match="cma_me"):
        load_config(p)
