"""Findings engine WP2.1 (gui/data_overview_findings.py).

Headless and offline: synthetic repos exactly like tests/test_gui_overview.py. No solver, no GPU,
no live runs/ tree.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import yaml

from hornlab_search.gui import data_overview as O
from hornlab_search.gui import data_overview_findings as F

_N = [0]


def _ts(minutes_ago: float) -> str:
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _repo(tmp_path: Path, identities: list[dict] | None = None) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    runs = root / "runs"
    runs.mkdir(parents=True)
    (root / "examples").mkdir()
    reg = {"schema": "score_identities_v1", "updated": "2026-11-19",
           "defaults": {"min_valid_for_leader": 3, "legacy_below_version": 7},
           "identities": identities if identities is not None else [
               {"id": "home_v10", "label": "Home v10", "brief": "home_v10", "objective_version": 10,
                "floor_j": 0.5, "status": "current"}]}
    (root / "examples" / "score_identities.yaml").write_text(yaml.safe_dump(reg), encoding="utf-8")
    return root, runs


def _run(runs: Path, name: str, brief: str, version: int, js: list[float | None],
         minutes_ago: float = 5, family: str = "OSSE",
         errors: list[str] | None = None) -> str:
    _N[0] += 1
    rid = f"20261119T{_N[0]:06d}Z-screen-{_N[0]:06x}"
    d = runs / rid
    d.mkdir()
    cfg = {"name": name, "family": family, "brief": {"name": brief},
           "objective": {"version": version}}
    (d / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    errs = list(errors or [])
    rows = []
    ei = 0
    for i, j in enumerate(js):
        ok = j is not None
        row = {"n": i, "design_hash": f"{i:012x}", "ok": ok,
               "objective": j if ok else None, "mode": "screen", "family": family,
               "created_utc": _ts(minutes_ago + len(js) - i)}
        if not ok:
            row["error"] = errs[ei] if ei < len(errs) else "mesh_bad: synthetic"
            ei += 1
        rows.append(row)
    (d / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return rid


def _ov(root: Path, runs: Path, days: float = 1, show_legacy: bool = False) -> dict:
    return O.overview(root, runs, days=days, show_legacy=show_legacy)


def _of_kind(fs: list[dict], kind: str) -> list[dict]:
    return [f for f in fs if f["kind"] == kind]


# ---------------------------------------------------------------------------- budget

def test_still_improving_line_is_one_open_budget_finding(tmp_path):
    root, runs = _repo(tmp_path)
    _run(runs, "c4_morph_a", "home_v10", 10, [3.0, 2.0, 1.2])
    fs = F.findings(_ov(root, runs), runs)
    budget = _of_kind(fs, "budget")
    assert len(budget) == 1
    assert budget[0]["status"] == "open"
    assert budget[0]["severity"] == "medium"
    assert budget[0]["identity_id"] == "home_v10"
    assert budget[0]["resolved_by"] is None
    assert len(budget[0]["why"]) == 3


def test_later_run_in_same_line_resolves_budget(tmp_path):
    root, runs = _repo(tmp_path)
    _run(runs, "c4_morph_a", "home_v10", 10, [3.0, 2.0, 1.2], minutes_ago=60)
    first = F.findings(_ov(root, runs), runs)
    open_budget = _of_kind(first, "budget")
    assert len(open_budget) == 1 and open_budget[0]["status"] == "open"

    later = _run(runs, "c4_morph_cont", "home_v10", 10, [2.0, 1.6, 1.4], minutes_ago=5)
    fs = F.findings(_ov(root, runs), runs)
    budget = _of_kind(fs, "budget")
    assert len(budget) == 1
    assert budget[0]["status"] == "resolved"
    assert budget[0]["resolved_by"] == later
    assert budget[0]["id"] == open_budget[0]["id"], "the finding keeps its id when resolved"


# ---------------------------------------------------------------------------- identity rules

def test_two_lines_inside_floor_is_exactly_one_tie_verify(tmp_path):
    root, runs = _repo(tmp_path)
    _run(runs, "hl__morph_a", "home_v10", 10, [1.2, 1.1, 1.0])
    _run(runs, "hl__fold_a", "home_v10", 10, [1.4, 1.3, 1.2])
    ov = _ov(root, runs)
    ident = ov["identities"][0]
    assert ident["n_tied"] == 2
    ties = _of_kind(F.findings(ov, runs), "tie_verify")
    assert len(ties) == 1
    assert ties[0]["identity_id"] == "home_v10"
    assert ties[0]["severity"] == "high"


def test_refusal_severity_boundaries(tmp_path):
    root, runs = _repo(tmp_path)
    _run(runs, "hl__morph_a", "home_v10", 10, [2.0, 1.5, 1.2, None])
    _run(runs, "hl__fold_a", "home_v10", 10, [1.9, 1.4, None, None, 1.1])
    ov = _ov(root, runs)
    ref = {f["line_key"]: f for f in _of_kind(F.findings(ov, runs), "refusals")}
    morph = next(f for k, f in ref.items() if k.endswith("|morph"))
    fold = next(f for k, f in ref.items() if k.endswith("|fold"))
    assert morph["status"] == "open" and morph["severity"] == "medium"
    assert fold["status"] == "open" and fold["severity"] == "high"
    assert "mesh_bad" in morph["detail"]


# ---------------------------------------------------------------------------- determinism + identity safety

def test_identical_inputs_give_identical_ids_and_order(tmp_path):
    root, runs = _repo(tmp_path)
    _run(runs, "hl__morph_a", "home_v10", 10, [3.0, 2.0, 1.2])
    _run(runs, "hl__fold_a", "home_v10", 10, [1.4, 1.3, 1.2])
    ov = _ov(root, runs)
    a = F.findings(ov, runs)
    b = F.findings(ov, runs)
    assert [f["id"] for f in a] == [f["id"] for f in b]
    assert a == b
    # ids are stable across a rebuild of the payload too
    c = F.findings(_ov(root, runs), runs)
    assert [f["id"] for f in a] == [f["id"] for f in c]
    for f in a:
        assert len(f["id"]) == 16


def test_every_finding_has_exactly_one_identity(tmp_path):
    root, runs = _repo(tmp_path)
    _run(runs, "hl__morph_a", "home_v10", 10, [3.0, 2.0, 1.2])
    _run(runs, "hl__morph_b", "home_v10", 7, [2.0, 1.5, 1.2])
    ov = _ov(root, runs)
    ids = {i["id"] for i in ov["identities"]}
    fs = F.findings(ov, runs)
    assert fs
    for f in fs:
        assert isinstance(f["identity_id"], str) and f["identity_id"]
        assert f["identity_id"] in ids
        assert not isinstance(f["identity_id"], (list, dict, tuple))


def test_legacy_finding_scores_below_current_with_same_facts(tmp_path):
    root, runs = _repo(tmp_path, identities=[
        {"id": "home_v10", "label": "Home v10", "brief": "home_v10", "objective_version": 10,
         "floor_j": 0.5, "status": "current"},
        {"id": "old_v4", "label": "Old v4", "brief": "old_v4", "objective_version": 4,
         "floor_j": 0.5, "status": "legacy"}])
    _run(runs, "hl__morph_a", "home_v10", 10, [3.0, 2.0, 1.2])
    _run(runs, "hl__morph_a", "old_v4", 4, [3.0, 2.0, 1.2])
    fs = _of_kind(F.findings(_ov(root, runs, show_legacy=True), runs), "budget")
    by = {f["identity_id"]: f for f in fs}
    assert set(by) == {"home_v10", "old_v4"}
    assert by["old_v4"]["score"] < by["home_v10"]["score"]
    assert by["old_v4"]["why"][2].startswith("legacy score")


# ---------------------------------------------------------------------------- state hook

def test_apply_state_is_noop_for_empty_state(tmp_path):
    root, runs = _repo(tmp_path)
    _run(runs, "c4_morph_a", "home_v10", 10, [3.0, 2.0, 1.2])
    ov = _ov(root, runs)
    fs = F.findings(ov, runs)
    assert F.apply_state(fs, {}) == fs
