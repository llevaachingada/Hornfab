"""GUI leaderboard performance (2026-10-28): one request builds ONE snapshot of the campaign state.

``/api/leaders`` used to re-walk every run dir (~43x) and re-parse every brief YAML (~48x) per
request, and to build the full per-design curve payload (125 ``design_curves`` calls) that it never
reads.  These tests pin the three properties that fix it:

* ``leaders()`` walks the runs and parses the briefs at most once per call (and again on the NEXT
  call: the snapshot must never survive a request, so a new campaign dir is seen immediately);
* ``leaders()`` builds no curve payloads; the full detail views still do (default ``curves=True``);
* the leaderboard rows keep their standings keys when the curves are dropped.

Offline, no GPU, no server.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from hornlab_search.gui import data as D
from test_gui import _design, _row

BRIEF = "pbrief"
AUTO_ID = f"auto_{BRIEF}__screen"


def _mk_run(runs: Path, rid: str, name: str, best_j: float, best_hash: str) -> Path:
    """A run with a brief, one seed row and one better row, and both designs on disk."""
    run = runs / rid
    run.mkdir(parents=True)
    (run / "config.yaml").write_text(yaml.safe_dump({
        "name": name, "family": "FREEFORM", "brief": {"name": BRIEF},
        "bounds": {"L_mm": {"lo": 90.0, "hi": 140.0}}}))
    rows = [_row(0, "aaaaaaaaaaaa", True, best_j + 5.0, 100.0),
            _row(1, best_hash, True, best_j, 110.0)]
    for r in rows:                                  # a real 200 x 100 mm mouth, 100 mm deep
        r["bbox_m"] = [-0.1, -0.05, 0.0, 0.1, 0.05, 0.1]
    (run / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    _design(run, best_hash, 0.0)
    return run


@pytest.fixture()
def perf_repo(tmp_path):
    """Two runs no campaign claims (=> one auto campaign) and a brief they both name."""
    root = tmp_path / "repo"
    runs = root / "runs"
    briefs = root / "examples" / "briefs"
    briefs.mkdir(parents=True)
    (briefs / f"{BRIEF}.yaml").write_text(yaml.safe_dump(
        {"name": BRIEF, "family": "FREEFORM", "target": {"coverage_h_deg": 90}}))
    _mk_run(runs, "20261026T010000Z-screen-aaaaaa", "cell_one", 9.0, "bbbbbbbbbbbb")
    _mk_run(runs, "20261026T020000Z-screen-bbbbbb", "cell_two", 12.0, "cccccccccccc")
    return root


def _counting(monkeypatch, name: str, log: list) -> None:
    """Wrap ``D.<name>`` so every call is recorded and the real one still runs."""
    real = getattr(D, name)
    monkeypatch.setattr(D, name, lambda *a, **k: (log.append(name), real(*a, **k))[1])


def test_leaders_walks_runs_and_briefs_at_most_once_per_call(perf_repo, monkeypatch):
    runs = perf_repo / "runs"
    auto_calls: list = []
    brief_calls: list = []
    _counting(monkeypatch, "_auto_groups", auto_calls)
    _counting(monkeypatch, "list_briefs", brief_calls)

    [row] = D.leaders(runs)
    assert row["campaign_id"] == AUTO_ID and row["family"] == "cell_one"
    assert len(auto_calls) <= 1, f"_auto_groups ran {len(auto_calls)}x in one leaders() call"
    assert len(brief_calls) <= 1, f"list_briefs ran {len(brief_calls)}x in one leaders() call"
    assert len(brief_calls) == 1, "the briefs were not read at all: a cache is hiding the parse"
    first = (len(auto_calls), len(brief_calls))

    # A second call is a second request: the snapshot is per-call, never a module-level cache.
    [row] = D.leaders(runs)
    assert row["campaign_id"] == AUTO_ID
    assert len(brief_calls) == first[1] + 1
    assert len(auto_calls) <= first[0] + 1


def test_leaders_builds_no_curve_payloads(perf_repo, monkeypatch):
    runs = perf_repo / "runs"
    calls: list = []
    _counting(monkeypatch, "design_curves", calls)

    [row] = D.leaders(runs)
    assert calls == [], f"leaders() built {len(calls)} curve payloads it never reads"
    assert row["median_j"] == pytest.approx(9.0) and row["best_j"] == pytest.approx(9.0)
    assert row["dims"]["mouth_w_mm"] == 200.0 and row["n_families"] == 2
    assert row["best_run_id"] == "20261026T010000Z-screen-aaaaaa"


def test_standings_only_detail_drops_best_but_keeps_the_standings(perf_repo):
    runs = perf_repo / "runs"
    d = D.campaign_detail(runs, AUTO_ID, curves=False)
    entries = {e["name"]: e for e in d["entries"]}
    assert set(entries) == {"cell_one", "cell_two"}           # ranked by J
    assert list(entries) == ["cell_one", "cell_two"]
    entry = entries["cell_one"]
    assert entry["best"] is None
    assert entry["name"] == "cell_one" and entry["group"] is None
    assert entry["median_j"] == pytest.approx(9.0) and entry["spread"] is None
    assert entry["best_j"] == pytest.approx(9.0) and entry["evals"] == 2
    assert entry["failures"] == {} and entry["dims"]["mouth_w_mm"] == 200.0
    assert entry["best_run_id"] == "20261026T010000Z-screen-aaaaaa"
    assert entry["jobs"][0]["run_id"] == "20261026T010000Z-screen-aaaaaa"


def test_campaign_detail_keeps_the_curves_by_default(perf_repo):
    """``/api/campaign/<id>`` (and the typologies view) read the full payload: default True."""
    runs = perf_repo / "runs"
    d = D.campaign_detail(runs, AUTO_ID)
    entry = {e["name"]: e for e in d["entries"]}["cell_one"]
    assert entry["best"] is not None
    assert entry["best"]["hash"] == "bbbbbbbbbbbb"
    assert entry["best"]["profile"]["h"], "the typologies view reads the wall profile from best"
    assert entry["median_j"] == pytest.approx(9.0)


def test_a_campaign_dir_created_between_two_calls_is_seen(perf_repo):
    """Shape of tests/test_gui.py:342 — the snapshot must die with its request."""
    runs = perf_repo / "runs"
    [row] = D.leaders(runs)
    assert row["campaign_id"] == AUTO_ID                       # the auto campaign leads (screen)

    claimed = _mk_run(runs, "20261026T030000Z-verify-cccccc", "gamma", 1.0, "dddddddddddd")
    camp = runs / "campaign_20261026T090000Z"
    camp.mkdir()
    (camp / "campaign.json").write_text(json.dumps({
        "tier": "compare", "brief_name": BRIEF, "seeds": [1, 2],
        "entries": [{"name": "gamma", "group": "g", "jobs": [
            {"seed": 1, "best_j": 1.0, "run_dir": str(claimed), "stats": {"evaluations": 5}},
            {"seed": 2, "best_j": 1.2, "run_dir": str(claimed), "stats": {"evaluations": 5}}]}]}))

    [row] = D.leaders(runs)                                    # a new request: must see the dir
    assert row["campaign_id"] == "campaign_20261026T090000Z"
    assert row["tier"] == "compare" and row["family"] == "gamma"
    assert row["median_j"] == pytest.approx(1.1) and row["clearly_ahead"] is False
