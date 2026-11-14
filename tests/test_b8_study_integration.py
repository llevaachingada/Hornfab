from types import SimpleNamespace

import numpy as np


def test_cost_training_rejects_unknown_cache_and_untyped_call_flags(monkeypatch):
    """Unknown provenance cannot turn 30 timings into measured uncached calls."""
    import hornlab_search.bo.model as model
    from hornlab_search.bo.extensions import fit_cost_model
    monkeypatch.setattr(model, "fit_model", lambda *args, **kwargs: SimpleNamespace(status="ok"))
    X = np.linspace(0, 1, 60).reshape(30, 2)
    result = fit_cost_model(X, np.arange(1., 31.), [str(i) for i in range(30)],
                            cached=[None] * 30, actual_bem=["false"] * 30)
    assert result["status"] == "capability_missing"


def test_analysis_cannot_dispatch_without_prerequisite_adapter(tmp_path):
    from hornlab_search.gui.study_jobs import StudyCpuJobs, StudyJobError
    from hornlab_search.studies.service import StudyService
    import pytest
    service = StudyService(tmp_path)
    study = service.create_study({"protocol": "bo-study-v1.1"}, "create")
    pkg = service.attach_artifact(study["id"], 1, "package", b"fixture", {}, "package")
    called = []
    bridge = StudyCpuJobs(service, dispatcher=lambda *a: called.append(a))
    with pytest.raises(StudyJobError) as exc:
        bridge.submit(study["id"], {"kind": "propose", "expected_revision": 1,
            "package_hash": pkg["sha256"], "idempotency_key": "one"})
    assert exc.value.http_status == 503
    assert not called and service.list_cpu_jobs(study["id"]) == []


def test_pareto_requires_bound_complete_canonical_metrics(monkeypatch):
    from test_bo_cohort_gate import row
    from hornlab_search.bo.cohort import validate_cohort
    from hornlab_search.bo.metrics import MetricObservation
    from hornlab_search.bo import pareto
    rows = [row(i) for i in range(16)]
    metric_hash = "a" * 64
    for i, item in enumerate(rows):
        item["x"] = [i / 20, i / 21]
        for key in ("metric_policy", "frequency_masks"):
            item["policy"][key] = {"namespace": "bo.physical_metric_spec_hash",
                                  "value": metric_hash, "evidence": "metric support manifest"}
    cohort = validate_cohort(rows, d=2)
    assert cohort.ok, cohort.reasons
    metrics = {o.observation_id: MetricObservation("complete", None, metric_hash, 1 + i, 2 + i)
               for i, o in enumerate(cohort.observations)}
    seen = []
    monkeypatch.setattr(pareto, "_fit_pareto_numeric", lambda X, e, ids, **kw: seen.append((X, e, ids, kw)) or SimpleNamespace(status="ok"))
    assert pareto.fit_pareto(cohort, metrics).status == "ok"
    assert seen[0][3]["reference"]["limits"] == [17.5, 18.5]
    assert pareto.fit_pareto(None, metrics).reason == "validated_cohort_required"
    removed = dict(metrics); removed.pop(next(iter(removed)))
    assert pareto.fit_pareto(cohort, removed).reason == "metric_observation_binding_mismatch"
    bad = dict(metrics); first = next(iter(bad))
    bad[first] = MetricObservation("partial", None, metric_hash, 1, 2)
    assert pareto.fit_pareto(cohort, bad).reason == "metric_observation_incomplete_or_incompatible"
    bad[first] = MetricObservation("complete", None, "b" * 64, 1, 2)
    assert pareto.fit_pareto(cohort, bad).reason == "metric_observation_incomplete_or_incompatible"


def test_production_wiring_refuses_without_a_pipeline_factory():
    from hornlab_search.studies.evaluator import build_production_wiring
    result = build_production_wiring(None, {'package_id': 'p'}, root='.',
                                     config_path=None, pipeline_factory=None)
    assert result['status'] == 'capability_missing'
    assert result['reason'] == 'production_wiring_unavailable'
    assert 'pipeline_factory' in result['missing']


def test_real_http_study_routes_conflict_and_missing_engine(tmp_path):
    import json
    import threading
    import urllib.error
    import urllib.request
    from http.server import ThreadingHTTPServer
    from hornlab_search.gui.server import App, make_handler
    from hornlab_search.studies.service import StudyService

    service = StudyService(tmp_path / "registry")
    app = App(tmp_path, runs=tmp_path / "runs", study_service=service)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app, 0))
    server.RequestHandlerClass = make_handler(app, server.server_port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    def request(path, payload=None):
        req = urllib.request.Request(base + path, data=None if payload is None else json.dumps(payload).encode(),
                                     headers={} if payload is None else {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)
    try:
        create = {"spec": {"protocol": "bo-study-v1.1", "question": "Inspect"}, "idempotency_key": "request"}
        code, a = request("/api/studies", create)
        assert code == 200
        assert request("/api/studies", create)[1]["id"] == a["id"]
        sid = a["id"]
        assert request(f"/api/studies/{sid}/overview")[1]["status"] == "partial"
        assert request(f"/api/studies/{sid}/propose")[1]["status"] == "missing"
        stale = {"spec": create["spec"], "idempotency_key": "edit", "expected_revision": 0}
        assert request(f"/api/studies/{sid}/revise", stale)[0] == 409
        job = {"kind": "propose", "expected_revision": 1, "idempotency_key": "job", "package_hash": "a"*64}
        # The production dispatcher now exists, but an unregistered package is refused.
        assert request(f"/api/studies/{sid}/jobs", job)[0] == 422
        assert service.list_cpu_jobs(sid) == []
        assert request("/api/studies/nonexistent")[0] == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
