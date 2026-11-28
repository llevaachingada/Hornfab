"""GUI bridge for the M1 research snapshot: the CPU-only ``research-snapshot`` job and its listing.

Offline: synthetic analysis trees; the build itself is exercised in ``test_research_snapshot.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hornlab_search.gui import data_research as R
from hornlab_search.gui.jobs import GPU_KINDS, RESEARCH_ENTRY, JobError, JobManager
from hornlab_search.gui.server import App


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    runs = root / "runs"
    (runs / "analysis").mkdir(parents=True)
    return root, runs


def test_research_is_a_cpu_kind_with_its_own_entry(tmp_path):
    root, runs = _repo(tmp_path)
    jm = JobManager(root, runs)
    argv, gpu = jm.build_argv("research-snapshot", {})
    assert gpu is False and "research-snapshot" not in GPU_KINDS
    assert argv == ["--cutoff", "now"]
    assert jm._entry_for("research-snapshot", argv) == RESEARCH_ENTRY
    assert jm.preview("research-snapshot", {})["command"].startswith("python " + RESEARCH_ENTRY)


@pytest.mark.parametrize("raw,expect", [
    (None, "now"), ("", "now"), ("now", "now"),
    ("2026-11-25", "2026-11-25T23:59:59Z"),
    ("2026-11-25T12:00", "2026-11-25T12:00:00Z"),
    ("2026-11-25T12:00:30", "2026-11-25T12:00:30Z"),
    ("2026-11-25T23:59:59Z", "2026-11-25T23:59:59Z"),
    ("2026-11-25T18:00:00-05:00", "2026-11-25T18:00:00-05:00"),
])
def test_cutoff_normalisation(raw, expect):
    assert R.normalise_cutoff(raw) == expect


@pytest.mark.parametrize("bad", ["yesterday", "2026-13", "2026-11-25; rm -rf /", "--out=x", "2026/11/25"])
def test_bad_cutoff_is_refused_by_the_job_manager(tmp_path, bad):
    root, runs = _repo(tmp_path)
    with pytest.raises(JobError, match="cutoff"):
        JobManager(root, runs).build_argv("research-snapshot", {"cutoff": bad})


def _snap_dir(runs: Path, name: str, cutoff: str, complete: bool = True, schema="hornfab-research-summary-m1"):
    d = runs / "analysis" / name
    d.mkdir(parents=True)
    (d / "snapshot.json").write_text("{}", encoding="utf-8")
    if complete:
        (d / "summary.json").write_text(json.dumps({
            "schema": schema, "snapshot_id": name[-8:] + "0" * 8, "cutoff_utc": cutoff,
            "source_commit": "a" * 40, "generator": "g", "counts": {"findings": 2, "cohorts": 3, "sources": 4},
            "headlines": [{"id": "x", "kind": "k", "severity": "decision", "title": "T", "plain": "P"},
                          {"id": "y", "kind": "i", "severity": "info", "title": "I", "plain": "Q"}],
            "next_steps": [{"what": "w"}]}), encoding="utf-8")
    return d


def test_listing_keeps_only_complete_research_snapshots_newest_first(tmp_path):
    _, runs = _repo(tmp_path)
    _snap_dir(runs, "research_2026-11-24_aaaaaaaa", "2026-11-24T23:59:59Z")
    _snap_dir(runs, "research_2026-11-25_bbbbbbbb", "2026-11-25T23:59:59Z")
    _snap_dir(runs, "research_2026-11-26_cccccccc", "2026-11-26T00:00:00Z", complete=False)   # still writing
    _snap_dir(runs, "research_2026-11-26_dddddddd", "2026-11-26T00:00:00Z", schema="other")   # foreign
    _snap_dir(runs, "overview_2026-11-25", "2026-11-25T00:00:00Z")                           # other kind
    out = R.snapshots(runs)
    assert [s["id"] for s in out] == ["research_2026-11-25_bbbbbbbb", "research_2026-11-24_aaaaaaaa"]
    top = out[0]
    assert top["href"] == "/analysis/research_2026-11-25_bbbbbbbb/index.html"
    assert top["files"]["summary.json"].endswith("/summary.json")
    assert [h["severity"] for h in top["headlines"]] == ["decision"]      # info rows are not headlines
    assert top["n_next_steps"] == 1


def test_api_route_lists_snapshots(tmp_path):
    root, runs = _repo(tmp_path)
    _snap_dir(runs, "research_2026-11-25_bbbbbbbb", "2026-11-25T23:59:59Z")
    app = App(root, runs)
    got = app.get("/api/research/snapshots", {})
    assert [s["id"] for s in got["snapshots"]] == ["research_2026-11-25_bbbbbbbb"]


def test_preview_prints_the_entry_script_not_the_stock_cli(tmp_path):
    root, runs = _repo(tmp_path)
    app = App(root, runs)
    prev = app.post("/api/preview", {"kind": "research-snapshot", "args": {"cutoff": "2026-11-25"}})
    assert prev["gpu"] is False
    assert prev["command"].startswith("python " + RESEARCH_ENTRY)
    assert "2026-11-25T23:59:59Z" in prev["command"]


def test_overview_js_wires_the_button_to_the_research_kind():
    js = (Path(__file__).resolve().parents[1] / "hornlab_search/gui/static/overview.js").read_text(encoding="utf-8")
    assert 'id="ov-research-go"' in js and '"research-snapshot"' in js
    assert "/api/research/snapshots" in js and "/api/job/" in js
