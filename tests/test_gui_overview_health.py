"""WP3.3 — software health as findings (gui/data_overview_health.py).

Headless and offline: synthetic repos exactly like tests/test_gui_overview_findings.py. No solver,
no GPU, no live runs/ tree.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import yaml

from hornlab_search.gui import data_overview as O
from hornlab_search.gui import data_overview_health as H
from hornlab_search.gui import data_overview_registry as R

_N = [0]


def _ts(minutes_ago: float) -> str:
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    runs = root / "runs"
    runs.mkdir(parents=True)
    (root / "examples").mkdir()
    _write_yaml(root / "examples" / "score_identities.yaml", {
        "schema": "score_identities_v1", "updated": "2026-11-19",
        "defaults": {"min_valid_for_leader": 3, "legacy_below_version": 7},
        "identities": [{"id": "home_v10", "label": "Home v10", "brief": "home_v10",
                        "objective_version": 10, "floor_j": 0.5, "status": "current"}]})
    # Valid registry files: registry health is a source, so an empty tree must stay empty.
    _write_yaml(root / R.PROJECT_REL, {"schema": "project_readiness_v1"})
    _write_yaml(root / R.HW_REL, {"schema": "hw_readiness_v1"})
    return root, runs


def _run(runs: Path, name: str, brief: str, version: int, js: list[float | None],
         minutes_ago: float = 5, errors: list[str] | None = None) -> str:
    _N[0] += 1
    rid = f"20261119T{_N[0]:06d}Z-screen-{_N[0]:06x}"
    d = runs / rid
    d.mkdir()
    cfg = {"name": name, "family": "OSSE", "brief": {"name": brief},
           "objective": {"version": version}}
    _write_yaml(d / "config.yaml", cfg)
    errs = list(errors or [])
    rows, ei = [], 0
    for i, j in enumerate(js):
        ok = j is not None
        row = {"n": i, "design_hash": f"{i:012x}", "ok": ok, "objective": j if ok else None,
               "mode": "screen", "family": "OSSE",
               "created_utc": _ts(minutes_ago + len(js) - i)}
        if not ok:
            row["error"] = errs[ei] if ei < len(errs) else "mesh_bad: synthetic"
            ei += 1
        rows.append(row)
    (d / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                                     encoding="utf-8")
    return rid


def _ov(root: Path, runs: Path) -> dict:
    return O.overview(root, runs, days=1)


def _software(fs: list[dict]) -> list[dict]:
    return [f for f in fs if f["kind"] == "software"]


# ---------------------------------------------------------------------------- sources

def test_refusal_heavy_identity_becomes_a_software_finding(tmp_path):
    root, runs = _repo(tmp_path)
    _run(runs, "hl__morph_a", "home_v10", 10, [2.0, None, None, 1.5],
         errors=["mesh_bad: synthetic"])
    fs = H.health_findings(_ov(root, runs), root, runs)
    refusals = [f for f in _software(fs) if f["line_key"] == "refusals"]
    assert len(refusals) == 1
    f = refusals[0]
    assert f["identity_id"] == "home_v10"
    assert f["severity"] == "high"
    assert "mesh_bad" in f["detail"]
    assert f["status"] == "open"
    assert len(f["why"]) == 3


def test_repeated_solve_failed_rows_on_a_best_run_become_one_finding(tmp_path):
    root, runs = _repo(tmp_path)
    rid = _run(runs, "hl__morph_a", "home_v10", 10, [2.0, 1.5, 1.2, None, None],
               errors=["solve_failed: boom", "solve_failed: boom again"])
    fs = _software(H.health_findings(_ov(root, runs), root, runs))
    solver = [f for f in fs if f["line_key"] == f"solver:{rid}"]
    assert len(solver) == 1
    f = solver[0]
    assert f["identity_id"] == "home_v10"
    assert f["subject_type"] == "run"
    assert f["href"] == f"#/run/{rid}"
    assert f["severity"] == "high"
    assert "solve_failed" in f["detail"]


def test_alerted_lane_becomes_a_high_finding(tmp_path):
    root, _runs = _repo(tmp_path)
    ov = {"identities": [], "lanes": {"lanes": [
        {"lane": "gpu", "alert": {"job": "night", "age_min": 41.5,
                                  "reason": "newest row 41.5 min old while job 'night' is running"}},
        {"lane": "cpu", "alert": None}]}, "registry": {"error": None}}
    fs = _software(H.health_findings(ov, root))
    assert len(fs) == 1
    f = fs[0]
    assert f["severity"] == "high"
    assert f["identity_id"] == ""
    assert f["subject_type"] == "lane"
    assert "41.5" in f["detail"]
    assert f["href"] == "#/overview?tab=decisions"


def test_analysis_set_with_section_errors_becomes_a_medium_finding(tmp_path):
    root, runs = _repo(tmp_path)
    setdir = runs / "analysis" / "set1"
    setdir.mkdir(parents=True)
    (setdir / "report_day.json").write_text(json.dumps({
        "tool": "report_day", "generated_utc": "2026-11-19T07:00:00Z",
        "sections": [{"tool": "convergence", "status": "error"},
                     {"tool": "walls", "status": "ok"}]}), encoding="utf-8")
    fs = _software(H.health_findings({"identities": [], "lanes": None}, root, runs))
    assert len(fs) == 1
    f = fs[0]
    assert f["severity"] == "medium"
    assert f["subject_type"] == "analysis"
    assert f["identity_id"] == ""
    assert f["href"] == "#/analysis/set1"
    assert f["first_seen_utc"] == "2026-11-19T07:00:00Z"


def test_bad_registry_becomes_a_critical_finding(tmp_path):
    root, _runs = _repo(tmp_path)
    _write_yaml(root / R.PROJECT_REL, {"schema": "not_the_schema"})
    ov = {"identities": [], "lanes": None,
          "registry": {"error": "score identities exploded"}}
    fs = _software(H.health_findings(ov, root))
    assert len(fs) == 2
    assert all(f["severity"] == "critical" for f in fs)
    assert all(f["identity_id"] == "" for f in fs)
    details = " ".join(f["detail"] for f in fs)
    assert "score identities exploded" in details
    assert "schema" in details


# ---------------------------------------------------------------------------- safety

def test_zero_sources_gives_empty_list_and_no_exception(tmp_path):
    root, _runs = _repo(tmp_path)
    assert H.health_findings({}, root) == []
    # A missing analysis/runs tree is an empty source too, never an error.
    assert H.health_findings({"identities": [], "lanes": None}, root,
                             tmp_path / "no-runs") == []


def test_one_subject_yields_no_duplicate(tmp_path):
    root, _runs = _repo(tmp_path)
    alert = {"job": "night", "age_min": 41.5, "reason": "same stalled lane"}
    ov = {"identities": [], "lanes": {"lanes": [
        {"lane": "gpu", "alert": dict(alert)},
        {"lane": "gpu", "alert": dict(alert)}]}, "registry": {"error": None}}
    fs = _software(H.health_findings(ov, root))
    assert len(fs) == 1


def test_software_finding_never_carries_two_identity_ids(tmp_path):
    root, runs = _repo(tmp_path)
    _run(runs, "hl__morph_a", "home_v10", 10, [2.0, 1.5, 1.2, None, None],
         errors=["solve_failed: a", "solve_failed: b"])
    fs = H.health_findings(_ov(root, runs), root, runs)
    assert fs
    known = {"home_v10", ""}
    for f in fs:
        assert f["kind"] == "software"
        assert isinstance(f["identity_id"], str)
        assert f["identity_id"] in known
        assert not isinstance(f["identity_id"], (list, dict, tuple))
        assert len({f["identity_id"]}) == 1
    # The refusal source is identity-level and names the identity exactly once.
    refusals = [f for f in fs if f["line_key"] == "refusals"]
    assert len(refusals) == 1 and refusals[0]["identity_id"] == "home_v10"
