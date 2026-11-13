"""M3 API tests: typed HTTP status codes, idempotency, artifacts, launch/cancel."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from hornlab_search.gui.server import App, make_handler
from hornlab_search.gui.study_jobs import StudyJobError
from hornlab_search.studies.package import prepare_run_package
from hornlab_search.studies.schema import Conflict, NotFound, Unavailable
from hornlab_search.studies.service import DraftAttemptJournal, StudyService

SPEC = {"protocol": "bo-study-v1.1", "name": "api fixture"}


def _attached_study(root, *, with_artifacts=True):
    service = StudyService(root)
    sid = service.create_study(SPEC, "create")["id"]
    if with_artifacts:
        snapshot = service.attach_artifact(sid, 1, "snapshot",
                                           b'{"snapshot":1}', {}, "snap")
        model = service.attach_artifact(sid, 1, "model", b'{"model":1}',
                                        {"snapshot": snapshot["sha256"]}, "model")
        service.attach_artifact(sid, 1, "proposal",
                                b'{"proposal":1,"proposal_policy":"scalar"}',
                                {"model": model["sha256"]}, "proposal")
    return service, sid


def _app(tmp_path, service, **kwargs):
    return App(tmp_path, runs=tmp_path / "runs", study_service=service, **kwargs)


def test_artifact_view_by_kind_and_sha_and_bounded_payload(tmp_path):
    service, sid = _attached_study(tmp_path / "registry")
    app = _app(tmp_path, service)
    view = app.get(f"/api/studies/{sid}/artifacts/snapshot", {})
    assert view["kind"] == "snapshot" and view["data"] == {"snapshot": 1}
    assert view["status"] == "available" and view["binary"] is False
    by_sha = app.get(f"/api/studies/{sid}/artifacts/{view['sha256']}", {})
    assert by_sha["data"] == {"snapshot": 1}

    binary = service.attach_artifact(sid, 1, "training", b"PK\x03\x04binary", {}, "train")
    binary_view = app.get(f"/api/studies/{sid}/artifacts/training", {})
    assert binary_view["binary"] is True and binary_view["data"] is None
    assert binary_view["sha256"] == binary["sha256"]

    big = json.dumps({"rows": ["x" * 200] * 2000}).encode()
    service.attach_artifact(sid, 1, "analysis", big, {}, "big")
    big_view = app.get(f"/api/studies/{sid}/artifacts/analysis", {})
    assert big_view["binary"] is True and big_view["data"] is None
    assert big_view["status"] == "partial"

    for artifact_id in ("missing-kind", "..secret", "C:\\secret", "a" * 64):
        with pytest.raises(NotFound):
            app.get(f"/api/studies/{sid}/artifacts/{artifact_id}", {})


def test_package_launch_cancel_and_decision_status_codes(tmp_path):
    service, sid = _attached_study(tmp_path / "registry")
    launched = []
    app = _app(tmp_path, service,
               study_launcher=lambda package: launched.append(package["package_id"]) or {
                   "job_id": f"job-{len(launched)}", "package_id": package["package_id"]})

    package = app.post(f"/api/studies/{sid}/package",
                       {"lane": "cpu", "deadline": "2099-01-01T00:00:00Z",
                        "idempotency_key": "pkg-1"})
    assert package["proposal_policy"]["policy"] == "scalar"
    assert package["proposal_policy"]["source"] == "proposal"
    repeated = app.post(f"/api/studies/{sid}/package",
                        {"lane": "cpu", "deadline": "2099-01-01T00:00:00Z",
                         "idempotency_key": "pkg-1"})
    assert repeated["package_id"] == package["package_id"]

    body = {"package_id": package["package_id"], "expected_revision": 1,
            "idempotency_key": "launch-1"}
    first = app.post(f"/api/studies/{sid}/launch", body)
    second = app.post(f"/api/studies/{sid}/launch", body)
    assert first == second == {"job_id": "job-1", "package_id": package["package_id"]}
    assert len(launched) == 1
    with pytest.raises(StudyJobError) as exc:
        app.post(f"/api/studies/{sid}/launch",
                 {**body, "idempotency_key": "launch-2"})
    assert exc.value.http_status == 409

    decision = app.post(f"/api/studies/{sid}/decision",
                        {"expected_revision": 1, "outcome": "inconclusive",
                         "rationale": "fixture only", "idempotency_key": "dec-1"})
    assert decision["outcome"] == "inconclusive"
    assert app.post(f"/api/studies/{sid}/decide",
                    {"expected_revision": 1, "outcome": "accept",
                     "rationale": "alias", "idempotency_key": "dec-2"})["outcome"] == "accept"

    journal = DraftAttemptJournal(service)
    assert journal.claim(package)
    cancelled = app.post(f"/api/studies/{sid}/cancel",
                         {"package_id": package["package_id"],
                          "idempotency_key": "cancel-1"})
    assert cancelled["cancelled"] is True
    assert app.post(f"/api/studies/{sid}/cancel",
                    {"package_id": package["package_id"],
                     "idempotency_key": "cancel-1"}) == cancelled


def test_launch_refuses_stale_and_missing_engine(tmp_path):
    service, sid = _attached_study(tmp_path / "registry")
    app = _app(tmp_path, service)
    package = prepare_run_package(service, sid, lane="cpu",
                                  deadline="2099-01-01T00:00:00Z",
                                  idempotency_key="pkg")
    with pytest.raises(StudyJobError) as exc:
        app.post(f"/api/studies/{sid}/launch",
                 {"package_id": package["package_id"], "expected_revision": 1,
                  "idempotency_key": "launch"})
    assert exc.value.http_status == 503

    service.revise(sid, {**SPEC, "name": "next"}, 1, "revise")
    with pytest.raises(StudyJobError) as exc:
        app.post(f"/api/studies/{sid}/launch",
                 {"package_id": package["package_id"], "expected_revision": 1,
                  "idempotency_key": "launch"})
    assert exc.value.http_status == 409


def test_package_requires_artifacts_and_cancel_unknown_is_404(tmp_path):
    service, sid = _attached_study(tmp_path / "registry", with_artifacts=False)
    app = _app(tmp_path, service)
    with pytest.raises(StudyJobError) as exc:
        app.post(f"/api/studies/{sid}/package",
                 {"lane": "cpu", "deadline": "2099-01-01T00:00:00Z"})
    assert exc.value.http_status == 422
    with pytest.raises(Exception) as exc:
        app.post(f"/api/studies/{sid}/cancel",
                 {"package_id": "a" * 64, "idempotency_key": "cancel"})
    assert getattr(exc.value, "http_status", getattr(exc.value, "status_code", None)) == 404


def test_real_http_status_codes_not_200_envelopes(tmp_path):
    service, sid = _attached_study(tmp_path / "registry", with_artifacts=False)
    app = App(tmp_path, runs=tmp_path / "runs", study_service=service)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app, 0))
    server.RequestHandlerClass = make_handler(app, server.server_port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def request(path, payload=None):
        req = urllib.request.Request(
            base + path,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={} if payload is None else {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)

    try:
        assert request(f"/api/studies/{sid}/artifacts/snapshot")[0] == 404
        assert request(f"/api/studies/{sid}/artifacts/%2E%2E%2Fsecret")[0] == 404
        assert request(f"/api/studies/{sid}/package",
                       {"lane": "cpu", "deadline": "2099-01-01T00:00:00Z"})[0] == 422
        snapshot = service.attach_artifact(sid, 1, "snapshot", b'{"snapshot":1}', {}, "snap")
        model = service.attach_artifact(sid, 1, "model", b'{"model":1}',
                                        {"snapshot": snapshot["sha256"]}, "model")
        service.attach_artifact(sid, 1, "proposal", b'{"proposal":1}', {"model": model["sha256"]}, "proposal")
        package = request(f"/api/studies/{sid}/package",
                          {"lane": "cpu", "deadline": "2099-01-01T00:00:00Z",
                           "idempotency_key": "pkg"})[1]
        assert request(f"/api/studies/{sid}/launch",
                       {"package_id": package["package_id"],
                        "idempotency_key": "launch"})[0] == 503
        assert request(f"/api/studies/{sid}/decision",
                       {"expected_revision": 1, "outcome": "inconclusive",
                        "rationale": "fixture", "idempotency_key": "dec"})[0] == 200
        assert request(f"/api/studies/{sid}/revise",
                       {"spec": SPEC, "expected_revision": 0,
                        "idempotency_key": "revise"})[0] == 409
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
