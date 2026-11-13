import pytest

from hornlab_search.gui.server import App
from hornlab_search.studies.schema import Conflict
from hornlab_search.studies.service import StudyService


def test_study_artifact_view_package_and_decision_alias(tmp_path):
    service = StudyService(tmp_path / "registry")
    app = App(tmp_path, runs=tmp_path / "runs", study_service=service)
    sid = app.post("/api/studies", {"spec": {"protocol": "bo-study-v1.1"},
                                    "idempotency_key": "create-m3"})["id"]
    snapshot = service.attach_artifact(sid, 1, "snapshot", b'{"snapshot":1}', {}, "snap")
    model = service.attach_artifact(sid, 1, "model", b'{"model":1}',
                                    {"snapshot": snapshot["sha256"]}, "model")
    service.attach_artifact(sid, 1, "proposal", b'{"proposal":1}',
                            {"model": model["sha256"]}, "proposal")
    view = app.get(f"/api/studies/{sid}/artifacts/snapshot", {})
    assert view["kind"] == "snapshot" and view["data"] == {"snapshot": 1}
    with pytest.raises(Exception):
        app.get(f"/api/studies/{sid}/artifacts/../secret", {})
    package = app.post(f"/api/studies/{sid}/package",
                       {"lane": "cpu", "deadline": "2099-01-01T00:00:00Z",
                        "idempotency_key": "pkg"})
    assert package["proposal_policy"]["policy"] == "scalar"
    assert package["proposal_policy"]["verification_mode"] == "scalar"
    decision = app.post(f"/api/studies/{sid}/decision",
                        {"expected_revision": 1, "outcome": "inconclusive",
                         "rationale": "fixture", "idempotency_key": "decision"})
    assert decision["outcome"] == "inconclusive"


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
