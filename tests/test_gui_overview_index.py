"""WP2.3 -- persisted Overview index cache (gui/data_overview_index.py).

Offline and headless: a synthetic repo with ``examples/score_identities.yaml`` and a few run
folders, exactly like ``tests/test_gui_overview.py``. No solver, no GPU, no live runs/ tree.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import yaml

from hornlab_search.gui import data as D
from hornlab_search.gui import data_overview as OV
from hornlab_search.gui import data_overview_index as IDX

REPO = Path(__file__).resolve().parents[1]

_N = [0]


def _ts(minutes_ago: float) -> str:
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    runs = root / "runs"
    runs.mkdir(parents=True)
    (root / "examples").mkdir()
    reg = {"schema": "score_identities_v1", "updated": "2026-11-19",
           "defaults": {"min_valid_for_leader": 3, "legacy_below_version": 7},
           "identities": [{"id": "home_v10", "label": "Home v10", "brief": "home_v10",
                           "objective_version": 10, "floor_j": 0.5, "status": "current"}]}
    (root / "examples" / "score_identities.yaml").write_text(yaml.safe_dump(reg), encoding="utf-8")
    return root, runs


def _run(runs: Path, name: str, js: list[float], minutes_ago: float = 5,
         brief: str = "home_v10", version: int = 10) -> str:
    _N[0] += 1
    rid = f"20261119T{_N[0]:06d}Z-screen-{_N[0]:06x}"
    d = runs / rid
    d.mkdir()
    cfg = {"name": name, "family": "OSSE", "brief": {"name": brief},
           "objective": {"version": version}}
    (d / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    rows = [{"n": i, "design_hash": f"{i:012x}", "ok": True, "objective": j,
             "mode": "screen", "family": "OSSE",
             "created_utc": _ts(minutes_ago + len(js) - i)} for i, j in enumerate(js)]
    (d / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                                     encoding="utf-8")
    return rid


def _since() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)


def _reset_caches() -> None:
    """Simulate a fresh process: both the module layer and data.py's own run_summary memo."""
    IDX.reset_cache()
    D._RUN_SUMMARY_CACHE.clear()


# ---------------------------------------------------------------------------- equality

def test_index_directory_is_lazy_and_output_matches_run_records(tmp_path):
    root, runs = _repo(tmp_path)
    _run(runs, "hl__morph_a", [3.0, 2.0, 1.2])
    _run(runs, "hl__fold_b", [2.0, 1.6, 1.4])
    _run(runs, "probe_twinray", [0.1])
    assert not (runs / "overview").exists(), "index dir must not exist before the first call"

    out = IDX.cached_records(runs, _since())
    reference = OV.run_records(runs, _since())
    assert out == reference
    assert [r["id"] for r in out] == [r["id"] for r in reference]

    idx = runs / "overview" / "index.json"
    assert idx.is_file()
    payload = json.loads(idx.read_text(encoding="utf-8"))
    assert payload["schema"] == IDX.SCHEMA == "overview_index_v1"
    assert set(payload["runs"]) == {r["id"] for r in reference}
    for rid, ent in payload["runs"].items():
        assert isinstance(ent["summary"], dict)
        assert isinstance(ent["ndjson"], list) and len(ent["ndjson"]) == 2
        assert ent["run_json"] is None


# ---------------------------------------------------------------------------- zero reads

def test_second_cold_call_reads_zero_ndjson(tmp_path, monkeypatch):
    _, runs = _repo(tmp_path)
    _run(runs, "hl__morph_a", [3.0, 2.0, 1.2])
    _run(runs, "hl__fold_b", [2.0, 1.6, 1.4])
    _run(runs, "hl__ext_throat", [4.0, 3.0, 2.5])
    first = IDX.cached_records(runs, _since())
    assert len(first) == 3

    _reset_caches()
    calls = []
    real = D.read_ndjson                     # data.py resolves this global at call time

    def counting(path):
        calls.append(path)
        return real(path)

    monkeypatch.setattr(D, "read_ndjson", counting)
    second = IDX.cached_records(runs, _since())
    assert calls == [], f"cache hit still read {len(calls)} ndjson file(s)"
    assert second == first


# ---------------------------------------------------------------------------- change detection

def test_touched_ndjson_is_reread(tmp_path, monkeypatch):
    _, runs = _repo(tmp_path)
    rid_touched = _run(runs, "hl__morph_a", [3.0, 2.0, 1.2])
    _run(runs, "hl__fold_b", [2.0, 1.6, 1.4])
    IDX.cached_records(runs, _since())

    # append a better row to exactly one run (size + mtime both change)
    path = runs / rid_touched / "search.ndjson"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"n": 3, "design_hash": "00000000000a", "ok": True,
                             "objective": 0.9, "mode": "screen", "family": "OSSE",
                             "created_utc": _ts(1)}) + "\n")

    _reset_caches()
    calls = []
    real = D.read_ndjson
    monkeypatch.setattr(D, "read_ndjson", lambda p, real=real: (calls.append(p), real(p))[1])

    out = IDX.cached_records(runs, _since())
    assert len(calls) == 1, f"expected one re-read, got {len(calls)}"
    touched = next(r for r in out if r["id"] == rid_touched)
    assert touched["best_j"] == 0.9 and touched["n"] == 4


# ---------------------------------------------------------------------------- rebuild

def test_corrupt_and_wrong_schema_index_rebuilds(tmp_path, monkeypatch):
    _, runs = _repo(tmp_path)
    _run(runs, "hl__morph_a", [3.0, 2.0, 1.2])
    _run(runs, "hl__fold_b", [2.0, 1.6, 1.4])
    reference = IDX.cached_records(runs, _since())
    idx = runs / "overview" / "index.json"

    real = D.read_ndjson
    calls: list[Path] = []

    def counting(path):
        calls.append(path)
        return real(path)

    monkeypatch.setattr(D, "read_ndjson", counting)
    for blob in ("{ this is not json", json.dumps({"schema": "other", "runs": {}})):
        idx.write_text(blob, encoding="utf-8")
        _reset_caches()
        calls.clear()
        out = IDX.cached_records(runs, _since())
        assert out == reference
        assert len(calls) == 2, "a rebuilt index must re-read every run"
        assert json.loads(idx.read_text(encoding="utf-8"))["schema"] == IDX.SCHEMA


def test_empty_and_missing_runs_tree_are_safe(tmp_path):
    missing = tmp_path / "nope"
    assert IDX.cached_records(missing, _since()) == []
    assert not missing.exists()
    empty = tmp_path / "empty-runs"
    empty.mkdir()
    assert IDX.cached_records(empty, _since()) == []
    assert not (empty / "overview").exists(), "no index is written for an empty tree"
