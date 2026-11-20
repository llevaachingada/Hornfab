"""WP3.1 — the project + HW readiness registry merge (gui/data_overview_registry.py).

Headless and offline: synthetic ``docs/`` trees, plus one check that the committed registry files
parse. No solver, no GPU, no live runs/ tree.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from hornlab_search.gui import data_overview_registry as R

REPO = Path(__file__).resolve().parents[1]


def _write(root: Path, rel: Path, data: dict) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _hw() -> dict:
    return {
        "schema": "hw_readiness_v1",
        "risks": [
            {"id": "R1", "level": "CRITICAL", "status": "open", "wp": "WP4",
             "title": "mixed references", "evidence": "combine.py"},
            {"id": "R2", "level": "HIGH", "status": "closed", "wp": "WP1",
             "title": "LF never solved", "evidence": "grids"},
        ],
        "decisions": [
            {"id": 1, "question": "shape?", "recommendation": "procure", "status": "open",
             "blocks": "box axis"},
        ],
    }


def _project() -> dict:
    return {
        "schema": "project_readiness_v1",
        "updated": "2026-11-19",
        "sources": [R.HW_REL.as_posix(), "docs/ISSUES.md"],
        "risks": [
            {"id": "S1", "area": "search", "level": "HIGH", "status": "open", "wp": "-",
             "title": "verify the cluster", "blocked_by": None, "evidence": "4-way tie",
             "source": "docs/ISSUES.md (2026-11-19 item)"},
            {"id": "S2", "area": "data", "level": "LOW", "status": "open", "wp": "-",
             "title": "consume bundle", "blocked_by": None, "evidence": "437 designs",
             "source": "docs/ISSUES.md (2026-11-19 item)"},
        ],
        "decisions": [
            {"id": "O1", "area": "gui", "question": "landing page?", "recommendation": "yes",
             "status": "open", "decided": None, "source": "plan section 5"},
        ],
    }


def _tree(tmp_path: Path, *, project: dict | None = None, hw: dict | None = None) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    if project is not None:
        _write(root, R.PROJECT_REL, project)
    if hw is not None:
        _write(root, R.HW_REL, hw)
    return root


# ---------------------------------------------------------------------------- merge

def test_merged_counts_equal_hw_plus_project_rows(tmp_path):
    root = _tree(tmp_path, project=_project(), hw=_hw())
    got = R.load_project_registry(root)

    assert got["schema"] == "project_readiness_v1"
    assert got["errors"] == []
    assert got["counts"]["hw"] == 3
    assert got["counts"]["project"] == 3
    assert got["counts"]["total"] == 6
    assert got["counts"]["total"] == got["counts"]["hw"] + got["counts"]["project"]
    assert len(got["risks"]) == 4
    assert len(got["decisions"]) == 2
    # HW rows carry area "hw"; the project rows keep their declared area.
    assert {r["id"] for r in got["risks"] if r["area"] == "hw"} == {"R1", "R2"}
    assert {r["id"] for r in got["risks"] if r["area"] == "search"} == {"S1"}
    assert all(d["area"] == "hw" for d in got["decisions"] if d["id"] == 1)
    assert got["counts"]["by_level"] == {"CRITICAL": 1, "HIGH": 2, "LOW": 1}
    assert got["counts"]["open"] == 5           # R1, decision 1, S1, S2, O1


def test_sources_name_the_hw_file(tmp_path):
    root = _tree(tmp_path, project=_project(), hw=_hw())
    got = R.load_project_registry(root)
    assert R.HW_REL.as_posix() in got["sources"]
    assert R.PROJECT_REL.as_posix() in got["sources"]


# ---------------------------------------------------------------------------- errors

def test_duplicate_id_across_files_is_an_error_and_drops_the_later_row(tmp_path):
    project = _project()
    project["risks"].append({"id": "R1", "area": "search", "level": "LOW", "status": "open",
                             "title": "collides with HW R1", "source": "docs/ISSUES.md"})
    root = _tree(tmp_path, project=project, hw=_hw())
    got = R.load_project_registry(root)

    assert any("duplicate" in e and "R1" in e for e in got["errors"])
    assert [r["id"] for r in got["risks"]].count("R1") == 1
    # The HW row survives (loaded first); the later project row is dropped.
    kept = next(r for r in got["risks"] if r["id"] == "R1")
    assert kept["area"] == "hw"
    assert got["counts"]["hw"] == 3
    assert got["counts"]["project"] == 3         # S1, S2, O1 (the colliding risk is dropped)
    assert got["counts"]["total"] == 6


def test_missing_project_file_reports_error_and_keeps_hw_rows(tmp_path):
    root = _tree(tmp_path, project=None, hw=_hw())
    got = R.load_project_registry(root)

    assert any("not found" in e and R.PROJECT_REL.as_posix() in e for e in got["errors"])
    assert got["counts"]["hw"] == 3
    assert got["counts"]["project"] == 0
    assert [r["id"] for r in got["risks"]] == ["R1", "R2"]
    assert [d["id"] for d in got["decisions"]] == [1]


def test_missing_hw_file_reports_error_and_keeps_project_rows(tmp_path):
    root = _tree(tmp_path, project=_project(), hw=None)
    got = R.load_project_registry(root)

    assert any("not found" in e and R.HW_REL.as_posix() in e for e in got["errors"])
    assert got["counts"]["project"] == 3
    assert got["counts"]["hw"] == 0
    assert {r["id"] for r in got["risks"]} == {"S1", "S2"}


def test_missing_schema_is_reported_but_rows_are_kept(tmp_path):
    project = _project()
    del project["schema"]
    root = _tree(tmp_path, project=project, hw=_hw())
    got = R.load_project_registry(root)

    assert any("schema" in e for e in got["errors"])
    assert got["counts"]["project"] == 3


def test_missing_area_defaults_and_is_reported(tmp_path):
    project = _project()
    del project["risks"][0]["area"]                    # S1 loses its area
    root = _tree(tmp_path, project=project, hw=_hw())
    got = R.load_project_registry(root)

    assert any("missing area" in e and "S1" in e for e in got["errors"])
    s1 = next(r for r in got["risks"] if r["id"] == "S1")
    assert s1["area"] == "search"                      # documented project-side default


def test_committed_registry_files_parse_without_errors():
    got = R.load_project_registry(REPO)
    assert got["schema"] == "project_readiness_v1"
    assert got["errors"] == []
    assert got["counts"]["project"] >= 6
    assert got["counts"]["hw"] >= 6
    assert got["counts"]["total"] == got["counts"]["hw"] + got["counts"]["project"]
    assert all(r["area"] in R.AREAS for r in got["risks"] + got["decisions"])
    assert {"O1", "O2", "O3", "O4", "O5", "O6"} <= {str(d["id"]) for d in got["decisions"]}
