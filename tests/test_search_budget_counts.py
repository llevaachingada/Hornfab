"""B.4 (day 2026-11-12): ``search.budget_counts: valid`` — refusals do not consume budget,
with the ``search.max_attempts`` hard ceiling (default 4 x budget) so an all-refusing box still
stops. The default ``new`` keeps today's semantics byte-for-byte (no run.json key, same counts).
"""
from __future__ import annotations

import json

import pytest
import yaml

from hornlab_search.config import ConfigError, load_config
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.search import cma as cma_mod
from hornlab_search.search.evaluate import read_ndjson
from test_search_support import LIBS, SyntheticBackend, fast_cfg, install_fakes

EXTRA = {"hornlab_mesher": "0123456789abcdef", "hornlab_beat_bem": "0123456789abcdef",
         "hornlab_bempp_bem": "0123456789abcdef", "hornlab_plots": "0123456789abcdef",
         "hornlab_search": "0123456789abcdef"}


def _write_cfg(tmp_path, base_yaml, **search_patch):
    """search_smoke.yaml with a patched search block, written to tmp_path."""
    raw = yaml.safe_load((base_yaml).read_text(encoding="utf-8"))
    raw["search"].update(search_patch)
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return p


def _run(cfg, run_dir, backend, budget):
    return cma_mod.search(cfg, run_dir, "screen", backend=backend, budget=budget,
                          store=DatasetStore(run_dir / "ds"), lib_shas=LIBS)


def test_refusals_do_not_consume_the_valid_budget(smoke_cfg, tmp_path, monkeypatch):
    cfg = fast_cfg(smoke_cfg, budget_counts="valid")
    be = SyntheticBackend()
    install_fakes(monkeypatch, be, invalid_if=lambda p: p["a_deg"] > 45)  # ~a quarter refused
    _run(cfg, tmp_path / "r", be, 10)
    rows = read_ndjson(tmp_path / "r" / "search.ndjson")
    ok = [r for r in rows if r["ok"]]
    refused = [r for r in rows if r["kind"] == "invalid_geometry"]
    assert len(ok) == 10, "the valid budget must be reached exactly"
    assert len(refused) > 0 and len(rows) == len(ok) + len(refused)
    bc = json.loads((tmp_path / "r" / "run.json").read_text())["budget_counts"]
    assert bc["mode"] == "valid" and bc["budget"] == 10
    assert bc["valid"] == 10
    assert bc["refused_free"] == len(refused)
    assert bc["attempts"] == len(rows)
    assert bc["attempts_cap"] == 40                       # 4 x budget default


def test_all_refusing_box_stops_at_the_attempts_ceiling(smoke_cfg, tmp_path, monkeypatch):
    cfg = fast_cfg(smoke_cfg, budget_counts="valid")
    be = SyntheticBackend()
    install_fakes(monkeypatch, be, invalid_if=lambda p: True)            # refuses everything
    best = _run(cfg, tmp_path / "r", be, 3)                              # cap = 12 attempts
    rows = read_ndjson(tmp_path / "r" / "search.ndjson")
    assert len(rows) == 12 and all(r["kind"] == "invalid_geometry" for r in rows)
    run_json = json.loads((tmp_path / "r" / "run.json").read_text())
    assert run_json["status"] == "finished" and run_json["stop_reason"] == "budget"
    bc = run_json["budget_counts"]
    assert bc == {"mode": "valid", "budget": 3, "attempts_cap": 12, "attempts": 12,
                  "valid": 0, "refused_free": 12}
    assert best is not None


def test_explicit_max_attempts_overrides_the_default(smoke_cfg, tmp_path, monkeypatch):
    cfg = fast_cfg(smoke_cfg, budget_counts="valid", max_attempts=5)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be, invalid_if=lambda p: True)
    _run(cfg, tmp_path / "r", be, 100)
    rows = read_ndjson(tmp_path / "r" / "search.ndjson")
    assert len(rows) == 5
    assert json.loads((tmp_path / "r" / "run.json").read_text())["budget_counts"]["attempts_cap"] == 5


def test_default_budget_counts_new_is_byte_for_byte_todays_semantics(smoke_cfg, tmp_path, monkeypatch):
    cfg = fast_cfg(smoke_cfg)                                             # budget_counts absent
    be = SyntheticBackend()
    install_fakes(monkeypatch, be, invalid_if=lambda p: p["a_deg"] > 45)
    _run(cfg, tmp_path / "r", be, 8)
    rows = read_ndjson(tmp_path / "r" / "search.ndjson")
    ok = [r for r in rows if r["ok"]]
    assert len(rows) == 8                              # refusals DO consume budget (valid+refused)
    assert be.calls == len(ok)                         # the backend only runs for the valid subset
    assert any(r["kind"] == "invalid_geometry" for r in rows)
    run_json = json.loads((tmp_path / "r" / "run.json").read_text())
    assert "budget_counts" not in run_json                                # today's schema unchanged


def test_max_attempts_applies_with_the_default_mode_too(smoke_cfg, tmp_path, monkeypatch):
    cfg = fast_cfg(smoke_cfg, max_attempts=4)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    _run(cfg, tmp_path / "r", be, 50)
    rows = read_ndjson(tmp_path / "r" / "search.ndjson")
    assert len(rows) == 4
    assert json.loads((tmp_path / "r" / "run.json").read_text())["budget_counts"]["mode"] == "new"


@pytest.mark.parametrize("patch,bad", [
    ({"budget_counts": "valid_only"}, "budget_counts"),
    ({"budget_counts": True}, "budget_counts"),
    ({"max_attempts": 0}, "max_attempts"),
    ({"max_attempts": True}, "max_attempts"),
    ({"max_attempts": 2.5}, "max_attempts"),
])
def test_config_refuses_bad_budget_keys(tmp_path, smoke_cfg_path, patch, bad):
    with pytest.raises(ConfigError, match=bad):
        load_config(_write_cfg(tmp_path, smoke_cfg_path, **patch))


@pytest.fixture
def smoke_cfg_path():
    from pathlib import Path
    return Path(__file__).resolve().parents[1] / "examples" / "search_smoke.yaml"


def test_valid_values_load(tmp_path, smoke_cfg_path):
    cfg = load_config(_write_cfg(tmp_path, smoke_cfg_path, budget_counts="valid", max_attempts=7))
    assert cfg.search.budget_counts == "valid" and cfg.search.max_attempts == 7
    cfg = load_config(_write_cfg(tmp_path, smoke_cfg_path))
    assert cfg.search.budget_counts == "new" and cfg.search.max_attempts is None
