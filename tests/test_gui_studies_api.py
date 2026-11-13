import pytest

from hornlab_search.gui.server import App
from hornlab_search.studies.schema import Conflict
from hornlab_search.studies.service import StudyService


def test_study_api_create_list_panel_revision_and_missing_jobs(tmp_path):
    service = StudyService(tmp_path / "registry")
    app = App(tmp_path, runs=tmp_path / "runs", study_service=service)
    created = app.post("/api/studies", {"spec": {"protocol": "bo-study-v1.1"}, "idempotency_key": "create-1"})
    sid = created["id"]
    assert app.get("/api/studies", {})["studies"][0]["id"] == sid
    assert app.get(f"/api/studies/{sid}/overview", {})["status"] == "partial"
    assert app.get(f"/api/studies/{sid}/propose", {})["status"] == "missing"
    updated = app.post(f"/api/studies/{sid}/revise", {"spec": {"protocol": "bo-study-v1.1", "name": "next"},
                       "expected_revision": 1, "idempotency_key": "update-1"})
    assert updated["revision"] == 2
    with pytest.raises(Conflict):
        app.post(f"/api/studies/{sid}/revise", {"spec": {"protocol": "bo-study-v1.1"},
                 "expected_revision": 1, "idempotency_key": "update-2"})
    assert app.get(f"/api/studies/{sid}/jobs", {}) == {"jobs": []}
