"""GUI real-metric surface: opt-in prepare/launch reaches the same checked API.

The fixtures are a real StudyService, real metric artifacts, a real package prepare and a temp
approvals record.  A counting fake launcher plus failing backend/subprocess stubs prove every
GUI prepare/dry-run/refusal route makes zero acoustic calls.  No mesh, BEM/GPU, dataset or queue
job is created and no night/queue file is touched.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from hornlab_search.gui.server import App
from hornlab_search.gui.study_jobs import StudyJobError, StudyRunBridge
from hornlab_search.studies import package as package_mod
from hornlab_search.studies import production
from hornlab_search.studies.cli import REAL_METRIC_RELEASE_ENV
from hornlab_search.studies.service import StudyService
from test_studies_metric import _stages as synthetic_stages
from test_studies_metric_offline_package import _offline
from test_studies_package_metric_real import FUTURE_DEADLINE, _approval_record, _real_stages


class _CountingLauncher:
    def __init__(self):
        self.calls = []

    def __call__(self, package):
        self.calls.append(package["package_id"])
        return {"pid": 4242, "kind": "fake-launcher"}


def _no_backend(monkeypatch):
    """Fail loudly on any backend/spawn, and keep the GUI interpreter probe in-process."""
    launcher = _CountingLauncher()
    monkeypatch.setattr(production, "build_worker",
                        lambda *a, **k: pytest.fail("backend worker was built"))
    monkeypatch.setattr(production, "execute_study",
                        lambda *a, **k: pytest.fail("execute_study was called"))
    monkeypatch.setattr(production, "study_interpreter", lambda root: Path(sys.executable))
    from hornlab_search.solve import base as solve_base
    monkeypatch.setattr(solve_base, "get_backend",
                        lambda *a, **k: pytest.fail("backend was acquired"))
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: pytest.fail("subprocess.run was spawned"))
    monkeypatch.setattr(subprocess, "Popen",
                        lambda *a, **k: pytest.fail("Popen was spawned"))
    monkeypatch.setattr(os, "system", lambda *a, **k: pytest.fail("os.system was called"))
    return launcher


def _bridge_and_app(tmp_path, stages, launcher):
    bridge = StudyRunBridge(
        stages["service"], launcher=launcher, approvals_root=tmp_path,
        dependency_pins={"hornlab_mesher": "a" * 64, "hornlab_beat_bem": "b" * 64})
    app = App(tmp_path, tmp_path / "runs", study_service=stages["service"], study_runs=bridge)
    return app, bridge


def _metric_package_body(record, *, revision=1, lane="gpu", deadline=FUTURE_DEADLINE,
                         key="metric-package"):
    return {"expected_revision": revision, "lane": lane, "deadline": deadline,
            "idempotency_key": key, "metric": "real_metric_v1",
            "budget_profile": "metric-canary-8x2", "approvals_record": record}


def _launch_body(package, *, revision=1, key="launch"):
    return {"package_id": package["package_id"], "package_hash": package["package_id"],
            "expected_revision": revision, "idempotency_key": key}


def _execute_panel(app, sid):
    return app.get(f"/api/studies/{sid}/execute", {})


def test_gui_prepare_held_package_shows_identity_and_refuses_launch(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages, status="HELD_PENDING_PARENT_RELEASE",
                              owner_authorization={"authorized": False})
    launcher = _no_backend(monkeypatch)
    app, _bridge = _bridge_and_app(tmp_path, stages, launcher)
    sid = stages["sid"]

    package = app.post(f"/api/studies/{sid}/package", _metric_package_body(record))
    assert package["metric"]["provenance_mode"] == "real_metric_v1"
    assert package["metric"]["real_solver_allowed"] is True
    assert package["budget"] == {"screen_calls": 8, "verify_calls": 2,
                                 "total_calls": 10, "attempts": 60}

    metric = _execute_panel(app, sid)["data"]["metric"]
    assert metric["status"] == "ready"
    assert metric["task_identity"] == stages["manifest"]["task"]["task_identity"]
    assert metric["qualified_rows"] == stages["manifest"]["n"]
    assert metric["artifact_revision"] == 1
    assert metric["artifact_sha256"] == stages["service"].get_artifact_metadata(
        sid, "metric_training")["sha256"]
    assert metric["mode"] == "real_metric_v1"
    assert metric["budget_profile"] == "metric-canary-8x2"
    assert metric["lane"] == "gpu"
    assert metric["deadline"] == package["deadline"]
    assert metric["release"]["approvals_status"] == "HELD_PENDING_PARENT_RELEASE"
    assert metric["release"]["owner_authorized"] is False
    assert metric["release"]["status"] == "unavailable"
    # Observed J and predictions stay separate; nothing synthetic is shown as measured.
    assert metric["observed"]["status"] in ("missing", "measured")
    assert "observed_j" in metric["observed"]["source"]
    assert metric["predicted"]["measured"] is False

    panel = _execute_panel(app, sid)
    launch = next(a for a in panel["data"]["actions"] if a["kind"] == "launch")
    assert launch["enabled"] is False
    with pytest.raises(StudyJobError) as exc:
        app.post(f"/api/studies/{sid}/launch", _launch_body(package, key="launch-held"))
    assert exc.value.http_status == 422
    assert "HELD_PENDING_PARENT_RELEASE" in exc.value.message
    assert launcher.calls == []


def test_gui_panel_offers_the_opt_in_metric_package_before_any_package(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages)
    launcher = _no_backend(monkeypatch)
    app, _bridge = _bridge_and_app(tmp_path, stages, launcher)

    panel = _execute_panel(app, stages["sid"])
    metric = panel["data"]["metric"]
    assert metric["status"] == "ready"
    assert metric["qualified_rows"] == stages["manifest"]["n"]
    package_action = next(a for a in panel["data"]["actions"]
                          if a["kind"] == "package" and a.get("metric") is True)
    assert package_action["enabled"] is True
    assert package_action["payload"]["metric"] == "real_metric_v1"
    assert package_action["payload"]["budget_profile"] == "metric-canary-8x2"
    assert package_action["payload"]["lane"] == "gpu"
    # A metric study never offers the legacy scalar package as a fall-through.
    assert not any(a["kind"] == "package" and not a.get("metric")
                   for a in panel["data"]["actions"])
    assert launcher.calls == []


def test_production_launch_delegates_to_the_cli_release_gate(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages)
    launcher = _no_backend(monkeypatch)
    app, _bridge = _bridge_and_app(tmp_path, stages, launcher)
    package = app.post(f"/api/studies/{stages['sid']}/package", _metric_package_body(record))

    from hornlab_search.studies import cli as cli_mod
    from hornlab_search.studies.schema import Unavailable
    calls = []

    def refuse(pkg):
        calls.append(pkg["package_id"])
        raise Unavailable("planted CLI release gate")

    monkeypatch.setattr(cli_mod, "_require_real_metric_release", refuse)
    production_bridge = StudyRunBridge(stages["service"], launcher=launcher)
    with pytest.raises(StudyJobError) as exc:
        production_bridge.launch(stages["sid"], _launch_body(package, key="launch-cli-gate"))
    assert exc.value.http_status == 422
    assert "planted CLI release gate" in exc.value.message
    assert calls == [package["package_id"]]
    assert launcher.calls == []


def test_gui_approved_package_still_needs_parent_release_then_delegates(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages)       # APPROVED_FOR_CANARY + owner authorized
    launcher = _no_backend(monkeypatch)
    app, _bridge = _bridge_and_app(tmp_path, stages, launcher)
    sid = stages["sid"]

    package = app.post(f"/api/studies/{sid}/package", _metric_package_body(record))
    monkeypatch.delenv(REAL_METRIC_RELEASE_ENV, raising=False)

    metric = _execute_panel(app, sid)["data"]["metric"]
    assert metric["release"]["approvals_status"] == "APPROVED_FOR_CANARY"
    assert metric["release"]["owner_authorized"] is True
    assert metric["release"]["parent_release"] is False
    assert metric["release"]["status"] == "unavailable"
    launch = next(a for a in _execute_panel(app, sid)["data"]["actions"]
                  if a["kind"] == "launch")
    assert launch["enabled"] is False

    with pytest.raises(StudyJobError, match=REAL_METRIC_RELEASE_ENV):
        app.post(f"/api/studies/{sid}/launch", _launch_body(package, key="launch-no-env"))
    assert launcher.calls == []

    # The parent sets the one explicit release gate; the same GUI route now reaches the fake
    # launcher exactly once (never a backend).
    monkeypatch.setenv(REAL_METRIC_RELEASE_ENV, "1")
    result = app.post(f"/api/studies/{sid}/launch", _launch_body(package, key="launch-released"))
    assert result["pid"] == 4242
    assert launcher.calls == [package["package_id"]]


@pytest.mark.parametrize("case", ["missing", "bad_schema", "missing_budget"])
def test_gui_metric_prepare_refusals_are_typed_and_zero_call(tmp_path, monkeypatch, case):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages)
    launcher = _no_backend(monkeypatch)
    app, _bridge = _bridge_and_app(tmp_path, stages, launcher)
    sid = stages["sid"]
    body = _metric_package_body(record)
    expected = 422
    if case == "missing":
        body["approvals_record"] = "approvals/missing.json"
    elif case == "bad_schema":
        import json
        (tmp_path / record).write_text(json.dumps({"schema": "wrong"}), encoding="utf-8")
        expected = 400
    elif case == "missing_budget":
        body.pop("budget_profile")
        expected = 400
    with pytest.raises(StudyJobError) as exc:
        app.post(f"/api/studies/{sid}/package", body)
    assert exc.value.http_status == expected
    assert launcher.calls == []


def test_gui_metric_prepare_refuses_fall_through_scalar_policy(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages)
    launcher = _no_backend(monkeypatch)
    app, _bridge = _bridge_and_app(tmp_path, stages, launcher)
    # Force the packaging lane to see a scalar proposal policy: the real-metric contract must
    # refuse rather than silently prepare a scalar package.
    monkeypatch.setattr(package_mod, "_proposal_identity",
                        lambda *a, **k: {"policy": "scalar", "verification_mode": "scalar",
                                         "source": "test"})
    with pytest.raises(StudyJobError) as exc:
        app.post(f"/api/studies/{stages['sid']}/package",
                 _metric_package_body(record, key="metric-package-scalar"))
    assert exc.value.http_status == 400
    assert "metric" in exc.value.message.lower()
    assert launcher.calls == []


def test_synthetic_and_offline_packages_can_never_authorize_a_solver(tmp_path, monkeypatch):
    synthetic = synthetic_stages(tmp_path / "syn")
    offline = _offline(synthetic_stages(tmp_path / "off")["package"])
    launcher = _no_backend(monkeypatch)
    bridge = StudyRunBridge(synthetic["service"], launcher=launcher)
    with pytest.raises(StudyJobError) as exc:
        bridge.launch(synthetic["sid"], _launch_body(synthetic["package"], key="syn-launch"))
    assert exc.value.http_status == 422
    assert "never authorize a real solver" in exc.value.message
    assert launcher.calls == []

    with pytest.raises(StudyJobError) as exc:
        bridge._require_metric_release_if_any(offline)
    assert exc.value.http_status == 422
    assert "never authorize a real solver" in exc.value.message
    assert launcher.calls == []


def test_synthetic_package_panel_never_enables_a_live_solve(tmp_path, monkeypatch):
    stages = synthetic_stages(tmp_path / "syn")
    launcher = _no_backend(monkeypatch)
    bridge = StudyRunBridge(stages["service"], launcher=launcher)
    app = App(tmp_path / "syn", tmp_path / "syn" / "runs",
              study_service=stages["service"], study_runs=bridge)

    panel = app.get(f"/api/studies/{stages['sid']}/execute", {})
    assert panel["data"]["metric"]["mode"] == "synthetic_metric"
    assert panel["data"]["metric"]["release"]["status"] == "unavailable"
    launch = next(a for a in panel["data"]["actions"] if a["kind"] == "launch")
    assert launch["enabled"] is False
    assert "never authorize" in (launch.get("reason") or "")
    assert launcher.calls == []


def test_legacy_scalar_study_keeps_the_legacy_package_route(tmp_path):
    service = StudyService(tmp_path / "registry")
    sid = service.create_study(
        {"protocol": "bo-study-v1.1", "policy": {"proposal_policy": "scalar"}}, "create")["id"]
    app = App(tmp_path, tmp_path / "runs", study_service=service)
    panel = app.get(f"/api/studies/{sid}/propose", {})
    assert panel["data"]["metric"]["status"] == "missing"
    assert not any(a["kind"] == "package" and a.get("metric") is True
                   for a in panel["data"]["actions"])
    legacy = next(a for a in panel["data"]["actions"] if a["kind"] == "package")
    assert legacy["label"] == "Prepare immutable solve package"


def test_stale_revision_disables_and_refuses_launch(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages)
    launcher = _no_backend(monkeypatch)
    app, _bridge = _bridge_and_app(tmp_path, stages, launcher)
    sid = stages["sid"]
    package = app.post(f"/api/studies/{sid}/package", _metric_package_body(record))

    study = stages["service"].get_study(sid)
    stages["service"].revise(sid, {**study["spec"], "question": "revised"}, 1, "revise")
    assert stages["service"].get_study(sid)["revision"] == 2

    panel = _execute_panel(app, sid)
    assert all(not (a["kind"] == "launch" and a["enabled"]) for a in panel["data"]["actions"])
    with pytest.raises(StudyJobError) as exc:
        app.post(f"/api/studies/{sid}/launch", _launch_body(package, key="launch-stale"))
    assert exc.value.http_status == 409
    assert launcher.calls == []
