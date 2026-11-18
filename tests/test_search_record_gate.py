"""WP 3.3 (day 2026-11-17): opt-in ``search.record_gate``.

* absent / ``""`` -> today's behaviour byte-identically (no record build, no extra row keys);
* ``shadow`` -> only two additive ndjson row keys: ``record_margin_mm`` and
  ``record_gate_agrees``;
* ``resample`` -> in the DEFAULT CMA sweep, a candidate whose PRE-MESH record lies outside the
  brief envelope is replaced before ``run_one``; an outside candidate is never evaluated unless
  the RESAMPLE_CAP draws are exhausted (then the last replacement is admitted).
"""
from __future__ import annotations

import json

import pytest
import yaml

from hornlab_search.config import ConfigError, load_config
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.search import cma as cma_mod
from hornlab_search.search import evaluate as ev_mod
from hornlab_search.search.evaluate import read_ndjson
from test_search_support import SyntheticBackend, fast_cfg, install_fakes

# Only wall-clock/timing fields legitimately differ between two identical-seed runs. The
# orchestrator's "strip created_utc" plus ``seconds`` (measured solve/mesh duration) is the
# minimum stable projection of an ndjson row.
VOLATILE = ("created_utc", "seconds")
NEW_KEYS = {"record_margin_mm", "record_gate_agrees"}


@pytest.fixture
def smoke_cfg_path():
    from pathlib import Path
    return Path(__file__).resolve().parents[1] / "examples" / "search_smoke.yaml"


def _raw(smoke_cfg_path) -> dict:
    from pathlib import Path
    return yaml.safe_load(Path(smoke_cfg_path).read_text(encoding="utf-8"))


def _write(tmp_path, raw, name="cfg.yaml"):
    p = tmp_path / name
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return p


def _stable(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in VOLATILE}


def _run(cfg, tmp_path, monkeypatch, name="r", *, backend=None, budget=4):
    be = backend or SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / name
    cma_mod.search(cfg, rd, "screen", backend=be, budget=budget,
                   store=DatasetStore(rd / "ds"))
    return rd, read_ndjson(rd / "search.ndjson")


# ------------------------------------------------------------------ default: byte-identical


def test_absent_key_gives_identical_rows_and_no_record_keys(tmp_path, smoke_cfg, monkeypatch):
    cfg = fast_cfg(smoke_cfg, budget=4, popsize=4)
    rd_a, rows_a = _run(cfg, tmp_path, monkeypatch, name="a")
    rd_b, rows_b = _run(cfg, tmp_path, monkeypatch, name="b")
    assert rows_a and len(rows_a) == len(rows_b)
    assert [_stable(r) for r in rows_a] == [_stable(r) for r in rows_b]
    for r in rows_a:
        assert not [k for k in r if k.startswith("record_")], "absent key adds no row keys"
    # the config field is normalised to the empty default
    assert cfg.search.record_gate == ""


# ------------------------------------------------------------------ shadow: two additive keys


def test_shadow_adds_exactly_two_row_keys_and_keeps_everything_else(
        tmp_path, smoke_cfg, smoke_cfg_path, monkeypatch):
    base = fast_cfg(smoke_cfg, budget=4, popsize=4)
    _, rows_default = _run(base, tmp_path, monkeypatch, name="default")

    raw = _raw(smoke_cfg_path)
    raw["search"]["record_gate"] = "shadow"
    shadow = fast_cfg(load_config(_write(tmp_path, raw)), budget=4, popsize=4)
    _, rows_shadow = _run(shadow, tmp_path, monkeypatch, name="shadow")

    assert len(rows_shadow) == len(rows_default)
    for drow, srow in zip(rows_default, rows_shadow):
        assert set(srow) - set(drow) == NEW_KEYS
        assert set(drow) - set(srow) == set()
        assert {k: v for k, v in drow.items() if k not in VOLATILE} == {
            k: v for k, v in _stable(srow).items() if k not in NEW_KEYS
        }
        assert srow["record_margin_mm"] is None      # smoke has no brief envelope
        assert srow["record_gate_agrees"] is None


# ------------------------------------------------------------------ resample: pre-evaluation


@pytest.mark.parametrize("prefetch", [0, 2])
def test_resample_never_submits_an_outside_candidate(tmp_path, smoke_cfg, smoke_cfg_path,
                                                     monkeypatch, prefetch):
    raw = _raw(smoke_cfg_path)
    raw["search"]["record_gate"] = "resample"
    raw["search"]["seed"] = 1234
    raw["search"]["sigma0"] = 0.35                   # a population that straddles a_deg = 45
    cfg = fast_cfg(load_config(_write(tmp_path, raw)), budget=10, popsize=4,
                   pipeline_prefetch=prefetch)

    # A huge cap keeps the assertion deterministic: the only failure mode of a bounded gate is
    # exhausting RESAMPLE_CAP and admitting the last (outside) draw. 200 draws make that
    # probability zero for a distribution that straddles the threshold, while the gate still
    # certainly fires. The default cap's admit-last fallback is exercised elsewhere.
    monkeypatch.setattr(cma_mod, "RESAMPLE_CAP", 200)

    calls = []

    def fake_margin(design, cfg_):
        a = float(design.params["a_deg"])
        calls.append(a)
        return -1.0 if a > 45.0 else 1.0

    monkeypatch.setattr(ev_mod, "record_gate_margin", fake_margin)
    rd, rows = _run(cfg, tmp_path, monkeypatch, name="r", budget=10)

    assert rows, "the seed is always evaluated"
    assert all(r["params"]["a_deg"] <= 45.0 for r in rows), {
        r["n"]: r["params"]["a_deg"] for r in rows}
    # every spent evaluation budgets one admitted design: the gate never starves the run
    run_json = json.loads((rd / "run.json").read_text(encoding="utf-8"))
    assert run_json["stats"]["evaluations"] == 10
    assert len(rows) == 10
    # the helper was consulted for candidates that were then replaced
    assert any(a > 45.0 for a in calls), "the synthetic gate actually fired"


# ------------------------------------------------------------------ config validation


def test_absent_record_gate_defaults_to_empty(smoke_cfg):
    assert smoke_cfg.search.record_gate == ""


def test_empty_record_gate_is_today(tmp_path, smoke_cfg_path):
    raw = _raw(smoke_cfg_path)
    raw["search"]["record_gate"] = ""
    assert load_config(_write(tmp_path, raw)).search.record_gate == ""


@pytest.mark.parametrize("token", ["shadow", "resample"])
def test_supported_record_gate_tokens_load(tmp_path, smoke_cfg_path, token):
    raw = _raw(smoke_cfg_path)
    raw["search"]["record_gate"] = token
    assert load_config(_write(tmp_path, raw)).search.record_gate == token


def test_bad_record_gate_token_is_refused(tmp_path, smoke_cfg_path):
    raw = _raw(smoke_cfg_path)
    raw["search"]["record_gate"] = "nonsense"
    with pytest.raises(ConfigError, match="record_gate"):
        load_config(_write(tmp_path, raw))


def test_resample_with_cma_me_is_refused(tmp_path, smoke_cfg_path):
    raw = _raw(smoke_cfg_path)
    raw["search"]["algorithm"] = "cma_me"
    raw["search"]["qd"] = {"bins_h": 8, "bins_v": 8}
    raw["search"]["record_gate"] = "resample"
    with pytest.raises(ConfigError, match="record_gate"):
        load_config(_write(tmp_path, raw))
