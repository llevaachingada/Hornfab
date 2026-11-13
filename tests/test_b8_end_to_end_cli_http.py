"""B8 end-to-end, offline: create -> snapshot -> explain -> propose -> package ->
dry-run -> fake run -> decide -> export, driven twice:

1. through the ``hornlab-search study`` CLI (``hornlab_search.cli.main`` -> study);
2. through the real HTTP routes of an in-process GUI server with fakes.

Fixtures only: the 32-row native fixture from ``test_study_builders`` (legal OSSE
designs, no mesher/BEM), a serialized candidate pool, a monkeypatched BoTorch
policy (engine absent in CI) and the analytic ``CoupledEvaluator``.  No solver,
GPU, subprocess or live dataset/cache is touched.
"""
from __future__ import annotations

import contextlib
import io
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import numpy as np
import pytest

from b8_fake_study import CanonicalJournal, CoupledEvaluator
from test_study_builders import _tiny_fixture
from hornlab_search.bo.policy import ProposalOutcome
from hornlab_search.gui.server import App, make_handler
from hornlab_search.studies.lanes import StudyLane
from hornlab_search.studies.runner import run_package
from hornlab_search.studies.service import StudyService

D = 13


def _write_pool(root):
    path = root / "fixtures" / "pool.json"
    candidates = [{
        "candidate_id": f"c{i}", "pool_index": i, "seed": 0,
        "active_vector": [0.4 + 0.05 * i] * D, "full_vector": [0.0] * (D + 1),
        "design_hash": f"design-{i}", "geometry_hash": f"geometry-{i}",
        "intended_solve_hash": f"solve-{i}", "params": {}, "descriptors": {}, "checks": {},
    } for i in range(4)]
    path.write_text(json.dumps({"summary": {"status": "ok", "requested": 4, "seed": 0},
                                "candidates": candidates}), encoding="utf-8")
    return path


def _spec(root):
    spec = _tiny_fixture(root)
    spec["source"]["pool_json"] = str(_write_pool(root))
    return {"protocol": "bo-study-v1.1", "name": "b8 end-to-end",
            "question": "Does the full offline workflow hold together?", **spec}


@pytest.fixture
def fake_engine(monkeypatch):
    """Stand-in for the optional BoTorch engine: a tagged, never-measured prediction."""
    from hornlab_search.bo import policy as policy_mod
    calls = []

    def fit_and_propose(*args, **kwargs):
        calls.append(kwargs.get("seed"))
        return ProposalOutcome(
            status="ok", reason="ok", policy="scalar", selection_reason="acquisition",
            proposal={"candidate_id": "c1", "geometry_hash": "geometry-1", "design_hash": "design-1",
                      "intended_solve_hash": "solve-1", "active_vector": [0.45] * D,
                      "params": {}, "checks": {}},
            predicted={"j_mean": 2.0, "j_lower": 1.5, "j_upper": 2.5,
                       "interval_label": "model credible interval", "observation_noise": False},
            acquisition={"value": -0.25, "units": "log acquisition ranking diagnostic"},
            verification_mode="scalar", library_versions={"engine": "fixture"})

    monkeypatch.setattr(policy_mod, "capability_status",
                        lambda *a, **k: {"status": "ok", "reason": None, "detail": None,
                                         "library_versions": {}})
    monkeypatch.setattr(policy_mod, "fit_and_propose", fit_and_propose)
    return calls


def _lane(tmp_path):
    return StudyLane(runs_root=tmp_path / "runs", cpu_cache=tmp_path / "cache" / "cpu",
                     gpu_cache=tmp_path / "cache" / "gpu", cpu_dataset=tmp_path / "dataset" / "cpu",
                     gpu_dataset=tmp_path / "dataset" / "gpu")


def _fake_run(tmp_path, service, package):
    evaluator = CoupledEvaluator()
    result = run_package(package, evaluator, _lane(tmp_path), CanonicalJournal(service))
    assert result["status"] == "pool_exhausted", result
    state = CanonicalJournal(service).state(package["package_id"])
    assert (state["screen_calls"], state["verify_calls"], state["unresolved"]) == (8, 6, False)
    assert evaluator.evaluate_calls == 14
    return state


def _cli(argv):
    """Run the real top-level CLI (``hornlab-search study ...``) and parse its JSON line."""
    from hornlab_search.cli import main
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(["study", *argv])
    out = buf.getvalue().strip().splitlines()
    return code, json.loads(out[-1]) if out else {}


def test_cli_full_workflow(tmp_path, fake_engine, monkeypatch):
    monkeypatch.delenv("HORNLAB_CPU_LANE_LOCK_OWNER", raising=False)
    monkeypatch.delenv("HORNLAB_GPU_LOCK_OWNER", raising=False)
    root = tmp_path / "registry"
    root.mkdir()
    (root / "spec.json").write_text(json.dumps(_spec(root)), encoding="utf-8")
    r = ["--root", str(root)]

    code, out = _cli(["validate", *r, "--spec", "spec.json"])
    assert code == 0 and out["status"] == "valid"
    code, out = _cli(["create", *r, "--spec", "spec.json", "--key", "create-1"])
    assert code == 0
    sid = out["study"]["id"]
    assert _cli(["create", *r, "--spec", "spec.json", "--key", "create-1"])[1]["study"]["id"] == sid

    code, out = _cli(["snapshot", *r, "--study", sid])
    assert code == 0 and out["status"] == "ok"
    snapshot_sha = out["snapshot"]["sha256"]
    code, out = _cli(["analyze", *r, "--study", sid])          # "explain"
    assert code == 0 and out["status"] == "ok"
    analysis = json.loads(StudyService(root).store.read_artifact(out["analysis"]["sha256"]))
    assert analysis["recommendation_status"] == "suppressed"
    assert analysis["metric_math_recomputed"] is False

    code, out = _cli(["propose", *r, "--study", sid, "--policy", "scalar", "--seed", "7"])
    assert code == 0 and out["status"] == "ok", out
    assert fake_engine == [7]
    proposal = json.loads(StudyService(root).store.read_artifact(out["proposal"]["sha256"]))
    assert proposal["candidate"]["candidate_id"] == "c1"
    assert proposal["predictions_appended_to_measured_rows"] is False

    code, out = _cli(["package", *r, "--study", sid, "--out", "pkg.json", "--lane", "cpu",
                      "--deadline", "2099-01-01T00:00:00Z", "--key", "pkg-1"])
    assert code == 0, out
    package = json.loads((root / "pkg.json").read_text(encoding="utf-8"))
    assert package["artifacts"]["snapshot"] == snapshot_sha
    assert package["lane"] == "cpu" and package["deadline"] == "2099-01-01T00:00:00Z"

    before = sorted(p.name for p in (root / "artifacts").iterdir())
    code, out = _cli(["run", *r, "--package", "pkg.json", "--dry-run"])
    assert code == 0 and out["status"] == "dry_run"
    assert sorted(p.name for p in (root / "artifacts").iterdir()) == before
    assert not (tmp_path / "runs").exists()
    code, out = _cli(["run", *r, "--package", "pkg.json"])     # real run is never via CLI
    assert code == 2

    service = StudyService(root)
    _fake_run(tmp_path, service, package)
    assert _cli(["reconcile", *r, "--study", sid])[0] == 0

    (root / "decision.json").write_text(json.dumps(
        {"outcome": "inconclusive", "rationale": "Offline fixture only; no acoustic claim."}))
    code, out = _cli(["decide", *r, "--study", sid, "--payload", "decision.json", "--key", "dec-1"])
    assert code == 0 and out["decision"]["outcome"] == "inconclusive"
    code, out = _cli(["export", *r, "--study", sid, "--out", "export.json"])
    assert code == 0 and out["study_id"] == sid
    record = json.loads((root / "export.json").read_text(encoding="utf-8"))
    kinds = {a["kind"] for a in record["artifacts"]}
    assert {"snapshot", "analysis", "model", "pool", "proposal", "package"} <= kinds
    assert [d["outcome"] for d in record["decisions"]] == ["inconclusive"]


class _Http:
    def __init__(self, app):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app, 0))
        self.server.RequestHandlerClass = make_handler(app, self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def __call__(self, path, payload=None):
        req = urllib.request.Request(
            self.base + path, data=None if payload is None else json.dumps(payload).encode(),
            headers={} if payload is None else {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)


def test_http_full_workflow_with_durable_launch(tmp_path, fake_engine, monkeypatch):
    monkeypatch.delenv("HORNLAB_CPU_LANE_LOCK_OWNER", raising=False)
    monkeypatch.delenv("HORNLAB_GPU_LOCK_OWNER", raising=False)
    from hornlab_search.studies import builders
    root = tmp_path / "registry"
    root.mkdir()
    spec = _spec(root)
    service = StudyService(root)
    runs = []

    def launcher(package):
        """Fake lane launcher: runs the real serial runner with the analytic evaluator."""
        runs.append(_fake_run(tmp_path, service, package))
        return {"job_id": f"fake-{len(runs)}", "package_id": package["package_id"]}

    app = App(tmp_path, runs=tmp_path / "runs", study_service=service, study_launcher=launcher)
    with _Http(app) as http:
        code, created = http("/api/studies", {"spec": spec, "idempotency_key": "create"})
        assert code == 200
        sid = created["id"]
        assert http("/api/studies", {"spec": spec, "idempotency_key": "create"})[1]["id"] == sid
        assert http(f"/api/studies/{sid}/explain")[1]["status"] == "missing"

        # No POST builder route exists by design: CPU builders are server-side code.
        current = service.get_study(sid)["spec"]
        builders.freeze_snapshot(service, sid, root=root, spec=current)
        builders.build_training(service, sid, root=root, spec=current)
        builders.build_analysis(service, sid, root=root, spec=current)
        builders.build_proposal(service, sid, root=root, spec=current, policy="scalar", seed=3)

        code, snap = http(f"/api/studies/{sid}/data")
        assert code == 200 and snap["status"] != "missing"
        code, explain = http(f"/api/studies/{sid}/explain")
        assert code == 200 and explain["status"] != "missing"
        code, propose = http(f"/api/studies/{sid}/propose")
        assert code == 200 and propose["status"] != "missing"

        code, package = http(f"/api/studies/{sid}/package", {
            "lane": "cpu", "deadline": "2099-01-01T00:00:00Z", "idempotency_key": "pkg"})
        assert code == 200, package
        dry = run_package(package, None, None, None, dry_run=True)
        assert dry["status"] == "dry_run" and runs == []

        launch = {"package_id": package["package_id"], "expected_revision": 1,
                  "idempotency_key": "launch-1"}
        code, first = http(f"/api/studies/{sid}/launch", {k: v for k, v in launch.items()
                                                         if k != "idempotency_key"})
        assert code == 400 and runs == []                       # missing_idempotency_key
        code, first = http(f"/api/studies/{sid}/launch", launch)
        assert code == 200 and first["job_id"] == "fake-1" and len(runs) == 1

    # Server restart: a fresh App/service over the same registry root.
    app2 = App(tmp_path, runs=tmp_path / "runs", study_service=StudyService(root),
               study_launcher=launcher)
    with _Http(app2) as http:
        code, again = http(f"/api/studies/{sid}/launch", launch)
        assert code == 200 and again == first and len(runs) == 1
        code, _ = http(f"/api/studies/{sid}/launch", {**launch, "idempotency_key": "launch-2"})
        assert code == 409 and len(runs) == 1

        code, decision = http(f"/api/studies/{sid}/decision", {
            "expected_revision": 1, "outcome": "inconclusive",
            "rationale": "Offline fixture only.", "idempotency_key": "dec"})
        assert code == 200 and decision["outcome"] == "inconclusive"
        code, record = http(f"/api/studies/{sid}/export")
        assert code == 200 and record["study"]["id"] == sid
        assert {"snapshot", "analysis", "proposal", "package"} <= {a["kind"] for a in record["artifacts"]}
        assert [d["outcome"] for d in record["decisions"]] == ["inconclusive"]
        assert http("/api/studies/nope/export")[0] == 404
    assert np.isfinite(runs[0]["total_calls"])
