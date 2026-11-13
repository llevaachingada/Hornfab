from copy import deepcopy

import pytest

from hornlab_search.gui.data_studies import build_study_view, study_summaries
from hornlab_search.gui.study_jobs import StudyCpuJobs, StudyJobError, contained_path


class Registry:
    def __init__(self):
        self.jobs = {}
        self.keys = {}
    def reserve_cpu_job(self, study_id, expected_revision, idempotency_key, request_hash, kind, package_hash):
        if expected_revision != 2:
            raise StudyJobError("stale_revision", "stale", 409)
        if idempotency_key in self.keys:
            old_hash, jid = self.keys[idempotency_key]
            if old_hash != request_hash:
                raise StudyJobError("idempotency_conflict", "conflict", 409)
            return deepcopy(self.jobs[jid]), False
        jid = f"job{len(self.jobs)}"
        job = {"id": jid, "kind": kind, "status": "queued"}
        self.jobs[jid] = job
        self.keys[idempotency_key] = (request_hash, jid)
        return deepcopy(job), True
    def compare_and_set_cpu_job(self, study_id, job_id, expected_states, new_state, fields, idempotency_key):
        job = self.jobs[job_id]
        if job["status"] not in expected_states:
            raise StudyJobError("conflict", "state conflict", 409)
        job.update(fields, status=new_state)
        return deepcopy(job)
    def get_cpu_job(self, study_id, job_id):
        return deepcopy(self.jobs[job_id])
    def list_cpu_jobs(self, study_id, limit):
        return [deepcopy(j) for j in list(self.jobs.values())[:limit]]


def request(**kw):
    return {"kind": "analyze", "expected_revision": 2, "idempotency_key": "key1", "package_hash": "a" * 64, **kw}


def test_views_never_infer_readiness_and_preserve_context():
    study = {"id": "study", "revision": 2, "huge_arrays": [1] * 1000}
    artifact = {"revision": 2, "status": "ready", "validated": True,
                "data": {"coverage": {"value": 4, "unit": "deg", "direction": "minimize"},
                         "run_link": "/runs/r?study=study"}, "provenance": {"source": "measured"}}
    panel = build_study_view(study, "propose", artifact)
    assert panel.status == "ready" and panel.data["coverage"]["unit"] == "deg"
    assert build_study_view(study, "propose", {**artifact, "revision": 1}).status == "stale"
    assert build_study_view(study, "propose", {**artifact, "validated": False}).status == "unknown"
    assert build_study_view(study, "propose").status == "missing"
    assert "huge_arrays" not in study_summaries([study])[0]
    with pytest.raises(ValueError):
        build_study_view(study, "data", {**artifact, "data": {"rows": list(range(51))}})


def test_atomic_duplicate_submission_dispatches_once_and_stale_conflicts():
    registry = Registry()
    calls = []
    bridge = StudyCpuJobs(registry, lambda kind, sid, jid: calls.append((kind, sid, jid)) or {"pid": 123}, prerequisite=lambda *args: True)
    first = bridge.submit("study", request())
    second = bridge.submit("study", request())
    assert first == second and len(calls) == 1 and first["status"] == "running"
    with pytest.raises(StudyJobError) as exc:
        bridge.submit("study", request(kind="propose"))
    assert exc.value.http_status == 409
    with pytest.raises(StudyJobError):
        bridge.submit("study", request(expected_revision=1, idempotency_key="key2"))


def test_dispatch_failure_and_restart_never_claim_complete():
    registry = Registry()
    def fail(*args):
        raise RuntimeError("ambiguous")
    bridge = StudyCpuJobs(registry, fail, prerequisite=lambda *args: True)
    job = bridge.submit("study", request())
    assert job["status"] == "unknown"
    bridge2 = StudyCpuJobs(registry, lambda *args: {"pid": 2}, prerequisite=lambda *args: True)
    bridge2.submit("study", request(idempotency_key="key2"))
    assert {j["status"] for j in bridge2.reconcile_after_restart("study")} == {"unknown"}


def test_invalid_client_args_and_paths_never_dispatch(tmp_path):
    bridge = StudyCpuJobs(Registry(), lambda *args: pytest.fail("must not dispatch"))
    with pytest.raises(StudyJobError):
        bridge.submit("../bad", request())
    with pytest.raises(StudyJobError):
        bridge.submit("study", {**request(), "argv": "rm -rf /"})
    for path in ("../secret", "C:\\secret", "..\\secret", "/secret"):
        with pytest.raises(StudyJobError):
            contained_path(tmp_path, path)
    assert contained_path(tmp_path, "artifact.json") == tmp_path / "artifact.json"
    with pytest.raises(StudyJobError) as exc:
        StudyCpuJobs(Registry()).submit("study", request())
    assert exc.value.http_status == 503


def test_success_requires_valid_registered_artifact():
    registry = Registry()
    bridge = StudyCpuJobs(registry, lambda *args: {"pid": 1}, prerequisite=lambda *args: True)
    job = bridge.submit("study", request())
    with pytest.raises(StudyJobError):
        bridge.finish("study", job["id"], exit_code=0, artifact_identity={"id": "a"})
    assert registry.jobs[job["id"]]["status"] == "running"
    bridge.artifact_validator = lambda study, jid, artifact: artifact == {"id": "verified"}
    with pytest.raises(StudyJobError):
        bridge.finish("study", job["id"], exit_code=0, artifact_identity={"id": "wrong"})
    done = bridge.finish("study", job["id"], exit_code=0, artifact_identity={"id": "verified"})
    assert done["status"] == "complete"


def test_actual_registry_reservation_reopens_and_preserves_job(tmp_path):
    from hornlab_search.studies.service import StudyService
    service = StudyService(tmp_path)
    study = service.create_study({"protocol": "bo-study-v1.1"}, "create")
    artifact = service.attach_artifact(study["id"], 1, "package", b"fixture", {}, "package")
    seen = []
    bridge = StudyCpuJobs(service, lambda kind, sid, jid: seen.append(jid) or {"pid": 1},
                          prerequisite=lambda *args: True)
    data = request(expected_revision=1, package_hash=artifact["sha256"])
    first = bridge.submit(study["id"], data)
    reopened = StudyCpuJobs(StudyService(tmp_path), lambda *args: pytest.fail("duplicate dispatch"),
                            prerequisite=lambda *args: True)
    second = reopened.submit(study["id"], data)
    assert first["id"] == second["id"] and second["status"] == "running" and len(seen) == 1
    assert reopened.reconcile_after_restart(study["id"])[0]["status"] == "unknown"
