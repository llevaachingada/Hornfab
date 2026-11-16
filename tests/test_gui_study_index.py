import json
from pathlib import Path

import pytest

from hornlab_search.gui.server import App
from hornlab_search.gui.study_index import StudyIndex
from hornlab_search.studies.schema import Conflict, NotFound
from hornlab_search.studies.service import StudyService


def _root(path: Path, question: str):
    service = StudyService(path)
    study = service.create_study({"protocol": "bo-study-v1.1", "question": question}, "create")
    return service, study["id"]


def test_index_discovers_night_roots_and_keeps_root_ids_stable(tmp_path):
    runs = tmp_path / "runs"
    _service_a, sid_a = _root(runs / "night" / "arm_a", "arm a")
    _service_b, sid_b = _root(runs / "night" / "arm_b", "arm b")
    index = StudyIndex(tmp_path, primary_root=runs / "studies")
    rows = index.list_studies(limit=50)
    assert {row["id"] for row in rows} == {sid_a, sid_b}
    assert all(row["root"] and row["root_label"].startswith("runs/") for row in rows)
    roots = {item["id"]: item for item in index.roots()}
    assert len(roots) == 2
    assert roots[index._root_id((runs / "night" / "arm_a").resolve())]["label"] == "runs/night/arm_a"
    with pytest.raises(NotFound):
        index.service_for_path(tmp_path.parent)
    with pytest.raises(NotFound):
        index.resolve("not-a-study")


def test_app_routes_reads_and_writes_to_the_owning_root(tmp_path):
    runs = tmp_path / "runs"
    service_a, sid_a = _root(runs / "night" / "arm_a", "arm a")
    service_b, sid_b = _root(runs / "night" / "arm_b", "arm b")
    app = App(tmp_path, runs=runs)
    listing = app.get("/api/studies", {})
    assert {row["id"] for row in listing["studies"]} == {sid_a, sid_b}
    assert len(listing["roots"]) == 2
    row_b = next(row for row in listing["studies"] if row["id"] == sid_b)
    panel = app.get(f"/api/studies/{sid_b}/overview", {"root": [row_b["root"]]})
    assert panel["phase"] == "overview" and panel["revision"] == 1
    assert panel["data"]["bo"]["phase"] == "overview"
    assert app.get(f"/api/studies/{sid_b}", {"root": [row_b["root"]]})["root"] == row_b["root"]

    revised = app.post(f"/api/studies/{sid_b}/revise", {
        "root": row_b["root"],
        "spec": {"protocol": "bo-study-v1.1", "question": "arm b revised"},
        "expected_revision": 1,
        "idempotency_key": "revise-b",
    })
    assert revised["revision"] == 2
    assert service_b.get_study(sid_b)["revision"] == 2
    assert service_a.get_study(sid_a)["revision"] == 1
    assert app.get("/api/studies", {})["studies"]


def test_ambiguous_study_id_requires_a_root(tmp_path):
    runs = tmp_path / "runs"
    _service, sid = _root(runs / "night" / "arm_a", "arm a")
    other = StudyService(runs / "night" / "arm_b")
    other.create_study({"protocol": "bo-study-v1.1", "question": "arm b"}, "create")
    # A second registry can legitimately carry the same study id (independent roots).
    import shutil
    shutil.copy2(runs / "night" / "arm_a" / "studies.sqlite3",
                 runs / "night" / "arm_b" / "studies.sqlite3")
    index = StudyIndex(tmp_path, primary_root=runs / "studies")
    with pytest.raises(Conflict):
        index.resolve(sid)


def test_comparison_specs_are_exposed_by_the_server(tmp_path):
    runs = tmp_path / "runs"
    _root(runs / "night" / "arm_a", "arm a")
    specs = tmp_path / "tools" / "analysis" / "specs"
    specs.mkdir(parents=True)
    (specs / "bo_test.yaml").write_text(json.dumps({
        "name": "test", "target_j": 3.2,
        "arms": [{"id": "cma", "method": "cma", "run": "r1"}],
        "comparisons": [],
    }), encoding="utf-8")
    app = App(tmp_path, runs=runs)
    listing = app.get("/api/comparisons", {})
    assert listing["comparisons"][0]["name"] == "bo_test"
