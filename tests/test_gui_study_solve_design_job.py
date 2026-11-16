"""`solve_design`: the one GPU verify job the study page can start.

No BEM solve is run here.  The work is exercised with an injected fake runner; the real runner is
the ordinary ``hornlab_search.cli verify`` body in the study interpreter.  These tests cover the
run-dir builder, the refusal paths (GPU lane held / unknown design / no results / non-physical /
no config) and the durable (study, design) -> run mapping.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from hornlab_search.config import load_config
from hornlab_search.gui.data_studies import study_solves
from hornlab_search.gui.study_jobs import (
    StudyJobError,
    StudySolveDesignJobs,
    new_verify_run_dir,
    prepare_verify_run,
    read_solve_ledger,
)
from hornlab_search.studies.service import StudyService

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "examples" / "osse_baseline.yaml"
RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-studyverify-[0-9a-f]{6}$")


def _study(tmp_path, *, task_config: Path | None = CONFIG):
    service = StudyService(tmp_path / "registry")
    spec = {"protocol": "bo-study-v1.1", "question": "verify view",
            "policy": {"proposal_policy": "scalar", "seed": 7}}
    if task_config is not None:
        spec["task"] = {"config": str(task_config)}
    created = service.create_study(spec, "create")
    return service, created["id"]


def _attach(service, sid, kind, value, key=None):
    content = value if isinstance(value, bytes) else json.dumps(value).encode()
    return service.attach_artifact(sid, 1, kind, content, {}, key or kind)


def _results(design_hash="abc12345", *, physical=True, j=2.5):
    return {"status": "pool_exhausted", "observations": [{
        "candidate": {"design_hash": design_hash, "kind": "screen",
                      "params": {"L_mm": 120.0}, "descriptors": {"d": 1}, "x": [0.1]},
        "result": {"design_hash": design_hash, "kind": "screen", "observed_j": j,
                   "physical_measurement": physical, "outcome": "success",
                   "params": {"L_mm": 120.0},
                   "pareto_metric": {"status": "complete", "coverage_deg": 1.2,
                                     "ripple_db": 0.3}},
    }]}


def _request(design_hash="abc12345", key="k1"):
    return {"kind": "solve_design", "expected_revision": 1,
            "idempotency_key": key, "design_hash": design_hash}


def _job(service, tmp_path, **kw):
    return StudySolveDesignJobs(service, runs_root=tmp_path / "runs", root=tmp_path, **kw)


def _fake_runner(calls=None):
    def runner(run_dir, design_hash, env):
        if calls is not None:
            calls.append((run_dir, design_hash, dict(env)))
        design = run_dir / "designs" / design_hash
        design.mkdir(parents=True, exist_ok=True)
        (design / "metrics.json").write_text(json.dumps({"freqs_hz": [100.0]}), encoding="utf-8")
        with (run_dir / "search.ndjson").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"ok": True, "design_hash": design_hash, "mode": "verify",
                                     "objective": 2.4}) + "\n")
        return 0
    return runner


# ---------------------------------------------------------------- run-dir builder


def test_prepare_verify_run_writes_a_real_standalone_verify_run(tmp_path):
    cfg = load_config(CONFIG)
    run_dir = new_verify_run_dir(tmp_path / "runs", "abc12345")
    assert RUN_ID.fullmatch(run_dir.name), run_dir.name
    prepare_verify_run(run_dir, cfg, study_id="study1", design_hash="abc12345",
                       family=cfg.family, params={"L_mm": 120.0}, objective=2.5,
                       policy="scalar", study={"name": "Study one"})

    assert (run_dir / "config.yaml").is_file()
    assert load_config(run_dir / "config.yaml").family == cfg.family
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert meta["mode"] == "verify" and "verify_of" not in meta
    assert meta["family"] == cfg.family and meta["status"] == "running"
    assert meta["study_provenance"]["study_id"] == "study1"
    assert meta["study_provenance"]["design_hash"] == "abc12345"
    assert meta["study_provenance"]["policy"] == "scalar"
    assert meta["study_provenance"]["study_name"] == "Study one"

    rows = [json.loads(line) for line in
            (run_dir / "search.ndjson").read_text(encoding="utf-8").splitlines() if line]
    assert len(rows) == 1
    assert rows[0] == {**rows[0], "ok": True, "design_hash": "abc12345",
                       "family": cfg.family, "params": {"L_mm": 120.0},
                       "objective": 2.5, "mode": "screen"}


# ---------------------------------------------------------------- refusal paths


def test_job_refuses_when_gpu_lane_is_held_without_creating_a_run(tmp_path):
    service, sid = _study(tmp_path)
    _attach(service, sid, "snapshot", {"task": {"config": str(CONFIG)}})
    _attach(service, sid, "results", _results())
    bridge = _job(service, tmp_path, gpu_busy=lambda: "GPU busy: live holder",
                  synchronous=True, runner=_fake_runner())
    with pytest.raises(StudyJobError) as exc:
        bridge.submit(sid, _request())
    assert exc.value.http_status == 422 and "GPU busy" in str(exc.value)
    assert not list((tmp_path / "runs").glob("*"))
    failed = list(read_solve_ledger(service.store.root)["jobs"].values())
    assert len(failed) == 1 and failed[0]["status"] == "failed"
    assert "GPU busy" in failed[0]["reason"]


def test_job_refuses_an_unknown_design(tmp_path):
    service, sid = _study(tmp_path)
    _attach(service, sid, "snapshot", {"task": {"config": str(CONFIG)}})
    _attach(service, sid, "results", _results("11111111"))
    bridge = _job(service, tmp_path, gpu_busy=lambda: None, synchronous=True,
                  runner=_fake_runner())
    with pytest.raises(StudyJobError) as exc:
        bridge.submit(sid, _request("22222222"))
    assert exc.value.http_status == 422 and "not an observation" in str(exc.value)
    assert not list((tmp_path / "runs").glob("*"))


def test_job_refuses_when_the_study_has_no_results(tmp_path):
    service, sid = _study(tmp_path)
    _attach(service, sid, "snapshot", {"task": {"config": str(CONFIG)}})
    bridge = _job(service, tmp_path, gpu_busy=lambda: None, synchronous=True,
                  runner=_fake_runner())
    with pytest.raises(StudyJobError) as exc:
        bridge.submit(sid, _request())
    assert "results" in str(exc.value)
    assert not list((tmp_path / "runs").glob("*"))


def test_job_refuses_a_design_without_a_physical_measurement(tmp_path):
    service, sid = _study(tmp_path)
    _attach(service, sid, "snapshot", {"task": {"config": str(CONFIG)}})
    _attach(service, sid, "results", _results(physical=False))
    bridge = _job(service, tmp_path, gpu_busy=lambda: None, synchronous=True,
                  runner=_fake_runner())
    with pytest.raises(StudyJobError) as exc:
        bridge.submit(sid, _request())
    assert "physical measurement" in str(exc.value)
    assert not list((tmp_path / "runs").glob("*"))


def test_job_refuses_when_no_study_config_is_recorded(tmp_path):
    service, sid = _study(tmp_path, task_config=None)
    _attach(service, sid, "results", _results())
    bridge = _job(service, tmp_path, gpu_busy=lambda: None, synchronous=True,
                  runner=_fake_runner())
    with pytest.raises(StudyJobError) as exc:
        bridge.submit(sid, _request())
    assert exc.value.http_status in (422, 503)
    assert "task config" in str(exc.value)


# ---------------------------------------------------------------- happy path / failure


def test_job_records_the_run_and_links_the_3d_view(tmp_path):
    service, sid = _study(tmp_path)
    _attach(service, sid, "snapshot", {"task": {"config": str(CONFIG)}})
    results = _results()
    _attach(service, sid, "results", results)
    calls = []
    bridge = _job(service, tmp_path, gpu_busy=lambda: None, synchronous=True,
                  runner=_fake_runner(calls))
    job = bridge.submit(sid, _request())

    assert job["status"] == "complete", job
    run_id = job["run_id"]
    assert RUN_ID.fullmatch(run_id)
    run_dir = tmp_path / "runs" / run_id
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert meta["status"] == "finished" and meta["mode"] == "verify"
    assert (run_dir / "designs" / "abc12345" / "metrics.json").is_file()

    ledger = read_solve_ledger(service.store.root)
    assert ledger["solves"][f"{sid}/abc12345"]["run_id"] == run_id
    view = study_solves(results, study_id=sid, runs_root=tmp_path / "runs", ledger=ledger)
    assert view["rows"][0]["verify_run_id"] == run_id

    # It is a real GUI run: /api/runs lists it and #/run/<id> can resolve it.
    from hornlab_search.gui import data as D
    assert any(row["id"] == run_id for row in D.list_runs(tmp_path / "runs"))
    assert D._resolve_run(tmp_path / "runs", run_id) == run_dir

    # The child owns the lane itself; no inherited owner claim may bypass the lock.
    assert calls[0][2]["HORNLAB_GPU_LOCK"] == "refuse"
    assert "HORNLAB_GPU_LOCK_OWNER" not in calls[0][2]


def test_duplicate_submit_reuses_the_same_job_and_one_run_dir(tmp_path):
    service, sid = _study(tmp_path)
    _attach(service, sid, "snapshot", {"task": {"config": str(CONFIG)}})
    _attach(service, sid, "results", _results())
    bridge = _job(service, tmp_path, gpu_busy=lambda: None, synchronous=True,
                  runner=_fake_runner())
    first = bridge.submit(sid, _request())
    second = bridge.submit(sid, _request())
    assert first["job_id"] == second["job_id"] and second["status"] == "complete"
    assert len(list((tmp_path / "runs").glob("*"))) == 1


def test_workflow_panel_exposes_solves_for_execute_and_decide(tmp_path):
    from hornlab_search.gui.data_studies import workflow_panel

    service, sid = _study(tmp_path)
    _attach(service, sid, "snapshot", {"task": {"config": str(CONFIG)}})
    _attach(service, sid, "results", _results())
    study = service.get_study(sid)
    artifact = {"status": "partial", "revision": study["revision"], "data": {}, "provenance": {}}
    for phase in ("execute", "decide"):
        panel = workflow_panel(service, study, phase, artifact, root=tmp_path,
                               runs_root=tmp_path / "runs")
        solves = panel["data"]["solves"]
        assert solves["rows"][0]["design_hash"] == "abc12345"
        assert solves["n_total"] == 1 and solves["n_measured"] == 1

    empty_service, empty_sid = _study(tmp_path / "no-results")
    empty_study = empty_service.get_study(empty_sid)
    empty = workflow_panel(empty_service, empty_study, "execute", artifact, root=tmp_path,
                           runs_root=tmp_path / "runs")
    assert "solves" not in empty["data"]      # absent results leave the panel unchanged


def test_server_routes_solve_design_to_the_gpu_job_bridge(tmp_path):
    from hornlab_search.gui.server import App

    service, sid = _study(tmp_path)
    app = App(tmp_path, runs=tmp_path / "runs", study_service=service)
    seen = []

    class FakeBridge:
        def submit(self, study_id, body):
            seen.append((study_id, body))
            return {"status": "queued", "design_hash": body["design_hash"]}

    app._study_solve_jobs_by_root[service.store.root.resolve()] = FakeBridge()
    body = {"kind": "solve_design", "design_hash": "abc12345",
            "expected_revision": 1, "idempotency_key": "k1"}
    out = app.post(f"/api/studies/{sid}/jobs", dict(body))
    assert out == {"status": "queued", "design_hash": "abc12345"}
    assert seen == [(sid, body)]


def test_failed_verify_never_advertises_a_finished_run(tmp_path):
    service, sid = _study(tmp_path)
    _attach(service, sid, "snapshot", {"task": {"config": str(CONFIG)}})
    results = _results()
    _attach(service, sid, "results", results)

    def failing(run_dir, design_hash, env):
        return 1

    bridge = _job(service, tmp_path, gpu_busy=lambda: None, synchronous=True,
                  runner=failing)
    job = bridge.submit(sid, _request())
    assert job["status"] == "failed" and "verify exited 1" in (job["reason"] or "")
    meta = json.loads((tmp_path / "runs" / job["run_id"] / "run.json").read_text(encoding="utf-8"))
    assert meta["status"] == "failed"
    ledger = read_solve_ledger(service.store.root)
    assert f"{sid}/abc12345" not in ledger["solves"]
    view = study_solves(results, study_id=sid, runs_root=tmp_path / "runs", ledger=ledger)
    assert view["rows"][0]["verify_run_id"] is None
