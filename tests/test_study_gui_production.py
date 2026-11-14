"""Production GUI contracts, using an isolated registry and no acoustic backend."""
from hornlab_search.gui.server import App
from hornlab_search.gui.study_jobs import StudyCpuJobs
from hornlab_search.studies.service import StudyService


def test_new_study_can_analyze_before_package_exists(tmp_path):
    service = StudyService(tmp_path / "studies")
    study = service.create_study({"protocol": "bo-study-v1.1"}, "create")
    bridge = StudyCpuJobs(service, dispatcher=lambda *args: {"pid": 123},
                          prerequisite=lambda *args: True)
    result = bridge.submit(study["id"], {"kind": "analyze", "expected_revision": 1,
        "idempotency_key": "analyze", "package_hash": None})
    assert result["status"] == "running"
    assert result["package_hash"] is None


def test_server_supplies_next_steps_for_unprepared_draft(tmp_path):
    service = StudyService(tmp_path / "studies")
    study = service.create_study({"protocol": "bo-study-v1.1", "task": {
        "name": "p80x60__osse_ext_throat_home700_v7"}, "policy": {"proposal_policy": "scalar"}}, "create")
    app = App(tmp_path, study_service=service)
    panel = app.get(f"/api/studies/{study['id']}/data", {})
    assert panel["status"] == "missing"
    assert panel["data"]["actions"][0]["kind"] == "analyze"
    assert panel["data"]["actions"][0]["enabled"] is True
    proposal = app.get(f"/api/studies/{study['id']}/propose", {})
    assert next(a for a in proposal["data"]["actions"] if a["kind"] == "propose")["enabled"] is False
    assert all(p["status"] != "ready" for p in proposal["data"]["policies"])


def test_active_job_disables_duplicate_work_and_exposes_cancel(tmp_path):
    service = StudyService(tmp_path / "studies")
    study = service.create_study({"protocol": "bo-study-v1.1"}, "create")
    service.reserve_cpu_job(study["id"], 1, "reserve", "request", "analyze")
    panel = App(tmp_path, study_service=service).get(f"/api/studies/{study['id']}/explain", {})
    assert panel["data"]["actions"][0]["enabled"] is False
    assert panel["data"]["job"]["status"] == "unknown"
    assert panel["data"]["actions"][-1]["kind"] == "cancel"


def test_default_server_dispatches_owned_cpu_process(tmp_path, monkeypatch):
    import subprocess
    import threading
    from types import SimpleNamespace
    calls = []
    monkeypatch.setattr(subprocess, "Popen", lambda argv, **kw: calls.append((argv, kw)) or SimpleNamespace(pid=123))
    monkeypatch.setattr(threading, "Thread", lambda **kw: SimpleNamespace(start=lambda: None))
    service = StudyService(tmp_path / "studies")
    study = service.create_study({"protocol": "bo-study-v1.1"}, "create")
    app = App(tmp_path, study_service=service)
    response = app.post(f"/api/studies/{study['id']}/jobs", {"kind": "analyze", "expected_revision": 1,
        "idempotency_key": "analyze", "package_hash": None})
    assert response["status"] == "running"
    argv, kwargs = calls[0]
    assert argv[1:4] == ["-m", "hornlab_search.studies.cli", "analyze"]
    assert argv[argv.index("--study") + 1] == study["id"]
    assert argv[argv.index("--expected-revision") + 1] == "1"
    assert kwargs["cwd"] == tmp_path
    assert kwargs.get("shell", False) is False


def test_restart_keeps_prior_cpu_jobs_unknown_without_dispatch(tmp_path, monkeypatch):
    import subprocess
    service = StudyService(tmp_path / "studies")
    study = service.create_study({"protocol": "bo-study-v1.1"}, "create")
    job, _ = service.reserve_cpu_job(study["id"], 1, "reserve", "request", "analyze")
    service.compare_and_set_cpu_job(study["id"], job["id"], ("queued",), "running",
        {"process_identity": {"pid": 123}}, "running")
    def forbidden(*args, **kwargs):
        raise AssertionError("Restart must never redispatch an ambiguous job")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    app = App(tmp_path, study_service=service)
    jobs = app.get(f"/api/studies/{study['id']}/jobs", {})["jobs"]
    assert jobs[0]["status"] == "unknown"
    assert jobs[0]["fields"]["error"] == "process state not established after restart"
    assert app.get(f"/api/studies/{study['id']}/jobs", {})["jobs"] == jobs


def test_decision_allows_inconclusive_without_verification_and_remains_available_after_record(tmp_path):
    service = StudyService(tmp_path / "studies")
    study = service.create_study({"protocol": "bo-study-v1.1"}, "create")
    app = App(tmp_path, study_service=service)
    panel = app.get(f"/api/studies/{study['id']}/decide", {})
    decision = next(a for a in panel["data"]["actions"] if a["kind"] == "decision")
    assert decision["enabled"] is True
    assert decision["allowed_outcomes"] == ["inconclusive"]
    assert "verification" in decision["reason"].lower()
    app.post(f"/api/studies/{study['id']}/decision", {"expected_revision": 1, "outcome": "inconclusive",
        "rationale": "No verification yet", "idempotency_key": "decision"})
    panel = app.get(f"/api/studies/{study['id']}/decide", {})
    assert next(a for a in panel["data"]["actions"] if a["kind"] == "decision")["enabled"] is True
    exported = app.get(f"/api/studies/{study['id']}/export", {})
    assert exported["decisions"][0]["outcome"] == "inconclusive"


def test_known_proposal_ready_requires_current_dependency_graph(tmp_path):
    import json
    service = StudyService(tmp_path / "studies")
    study = service.create_study({"protocol": "bo-study-v1.1", "policy": {"proposal_policy": "scalar"}}, "create")
    sid = study["id"]
    def attach(kind, data, deps):
        return service.attach_artifact(sid, 1, kind, json.dumps(data).encode(), deps, kind)["sha256"]
    snapshot = attach("snapshot", {}, {})
    training = attach("training", {}, {"snapshot": snapshot})
    manifest = attach("training_manifest", {"schema": "study-training-manifest-v1", "status": "ok", "n": 16,
        "n_min": 16}, {"training": training})
    analysis = attach("analysis", {}, {"snapshot": snapshot})
    model = attach("model", {}, {"training_manifest": manifest})
    pool = attach("pool", {}, {"snapshot": snapshot})
    deps = {"snapshot": snapshot, "training": training, "training_manifest": manifest,
            "analysis": analysis, "model": model, "pool": pool}
    attach("proposal", {"schema": "study-proposal-v1", "status": "ok", "study_id": sid, "revision": 1,
        "candidate": {"candidate_id": "candidate1"}}, deps)
    app = App(tmp_path, study_service=service)
    panel = app.get(f"/api/studies/{sid}/propose", {})
    assert panel["status"] == "ready"
    assert any("unmeasured" in reason for reason in panel["reasons"])
    # The same schema/status is insufficient when even one dependency identity drifts.
    with service.store.connect() as conn:
        conn.execute("UPDATE artifacts SET dependencies_json=? WHERE study_id=? AND kind='proposal'",
                     (json.dumps({**deps, "pool": "0" * 64}), sid))
        conn.commit()
    assert app.get(f"/api/studies/{sid}/propose", {})["status"] == "unknown"


def test_existing_unsupported_policy_is_disclosed(tmp_path):
    service = StudyService(tmp_path / "studies")
    study = service.create_study({"protocol": "bo-study-v1.1", "policy": {"proposal_policy": "pareto"}}, "create")
    panel = App(tmp_path, study_service=service).get(f"/api/studies/{study['id']}/propose", {})
    assert panel["data"]["current_policy"] == "pareto"
    assert any("Current policy is pareto" in reason for reason in panel["reasons"])
    assert next(a for a in panel["data"]["actions"] if a["kind"] == "propose")["enabled"] is False


def test_launched_package_replaces_not_launched_fallback_with_journal_progress(tmp_path, monkeypatch):
    from hornlab_search.studies.package import prepare_run_package
    from hornlab_search.studies.service import DraftAttemptJournal
    from hornlab_search.studies import production
    service = StudyService(tmp_path / "studies")
    sid = service.create_study({"protocol": "bo-study-v1.1"}, "create")["id"]
    snapshot = service.attach_artifact(sid, 1, "snapshot", b'{"snapshot":1}', {}, "snapshot")
    model = service.attach_artifact(sid, 1, "model", b'{"model":1}', {"snapshot": snapshot["sha256"]}, "model")
    service.attach_artifact(sid, 1, "proposal", b'{"proposal":1,"proposal_policy":"scalar"}', {"model": model["sha256"]}, "proposal")
    package = prepare_run_package(service, sid, lane="cpu", deadline="2099-01-01T00:00:00Z")
    journal = DraftAttemptJournal(service)
    assert journal.claim(package)
    monkeypatch.setattr(production, "execution_capability", lambda *args, **kwargs: {"status": "ok"})
    panel = App(tmp_path, study_service=service).get(f"/api/studies/{sid}/execute", {})
    assert panel["status"] == "partial"
    assert panel["data"]["run_status"]["status"] == "running"
    assert panel["data"]["call_counts"]["total_calls"] == 0
    assert panel["data"]["progress"]["proposed"] == 0
    assert "not launched" not in " ".join(panel["reasons"])
    assert any("durable attempt journal" in r for r in panel["reasons"])
