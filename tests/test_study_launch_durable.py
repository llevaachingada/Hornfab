"""B4/B5: launch idempotency is durable in the studies SQLite registry.

Fixtures only: no solver, mesher, GPU or subprocess. "Restart" = a brand-new
StudyService + StudyRunBridge over the same on-disk root (the old in-memory
``_launched`` dict would have forgotten the first launch).
"""
from __future__ import annotations

import sqlite3

import pytest

from hornlab_search.gui.study_jobs import StudyCpuJobs, StudyJobError, StudyRunBridge
from hornlab_search.studies.package import prepare_run_package
from hornlab_search.studies.service import StudyService
from hornlab_search.studies.store import MIGRATIONS

SPEC = {"protocol": "bo-study-v1.1", "name": "durable launch fixture"}


def _study(root):
    service = StudyService(root)
    sid = service.create_study(SPEC, "create")["id"]
    snap = service.attach_artifact(sid, 1, "snapshot", b'{"snapshot":1}', {}, "snap")
    model = service.attach_artifact(sid, 1, "model", b'{"model":1}', {"snapshot": snap["sha256"]}, "model")
    service.attach_artifact(sid, 1, "proposal", b'{"proposal":1,"proposal_policy":"scalar"}',
                            {"model": model["sha256"]}, "proposal")
    package = prepare_run_package(service, sid, lane="cpu", deadline="2099-01-01T00:00:00Z",
                                  idempotency_key="pkg")
    return service, sid, package


class Launcher:
    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail

    def __call__(self, package):
        self.calls.append(package["package_id"])
        if self.fail is not None:
            raise self.fail
        return {"job_id": f"job-{len(self.calls)}", "package_id": package["package_id"]}


def _body(package, key="launch-1"):
    return {"package_id": package["package_id"], "expected_revision": 1, "idempotency_key": key}


def test_duplicate_launch_after_restart_is_replayed_not_redispatched(tmp_path):
    root = tmp_path / "registry"
    service, sid, package = _study(root)
    first_launcher = Launcher()
    first = StudyRunBridge(service, launcher=first_launcher).launch(sid, _body(package))
    assert first_launcher.calls == [package["package_id"]]

    # Simulated server restart: new service object, new bridge, new launcher.
    restarted_launcher = Launcher()
    restarted = StudyRunBridge(StudyService(root), launcher=restarted_launcher)
    assert restarted.launch(sid, _body(package)) == first
    assert restarted_launcher.calls == []
    with pytest.raises(StudyJobError) as exc:
        restarted.launch(sid, _body(package, "launch-other"))
    assert exc.value.code == "launch_conflict" and exc.value.http_status == 409
    assert restarted_launcher.calls == []
    record = StudyService(root).get_launch(sid, package["package_id"])
    assert record["status"] == "launched" and record["result"] == first


def test_ambiguous_launcher_failure_is_unknown_and_never_relaunched(tmp_path):
    root = tmp_path / "registry"
    service, sid, package = _study(root)
    launcher = Launcher(fail=RuntimeError("socket dropped after spawn?"))
    with pytest.raises(StudyJobError) as exc:
        StudyRunBridge(service, launcher=launcher).launch(sid, _body(package))
    assert exc.value.code == "unknown"
    assert service.get_launch(sid, package["package_id"])["status"] == "unknown"

    healthy = Launcher()
    bridge = StudyRunBridge(StudyService(root), launcher=healthy)
    for key in ("launch-1", "launch-2"):
        with pytest.raises(StudyJobError) as exc:
            bridge.launch(sid, _body(package, key))
        assert exc.value.http_status in (409, 503)
    assert healthy.calls == []


def test_crash_between_claim_and_settle_blocks_relaunch(tmp_path):
    root = tmp_path / "registry"
    service, sid, package = _study(root)
    # The process died after the durable claim and before settle_launch.
    claim, created = service.claim_launch(sid, package["package_id"], "launch-1")
    assert created and claim["status"] == "launching"
    launcher = Launcher()
    bridge = StudyRunBridge(StudyService(root), launcher=launcher)
    with pytest.raises(StudyJobError) as exc:
        bridge.launch(sid, _body(package))
    assert exc.value.code == "unknown" and exc.value.http_status == 503
    assert launcher.calls == []


def test_typed_refusal_releases_claim_so_a_retry_can_launch(tmp_path):
    root = tmp_path / "registry"
    service, sid, package = _study(root)
    refusing = Launcher(fail=StudyJobError("unavailable", "lane busy", 422))
    with pytest.raises(StudyJobError):
        StudyRunBridge(service, launcher=refusing).launch(sid, _body(package))
    assert service.get_launch(sid, package["package_id"]) is None
    ok = Launcher()
    result = StudyRunBridge(service, launcher=ok).launch(sid, _body(package))
    assert result["job_id"] == "job-1" and len(ok.calls) == 1


def test_missing_idempotency_key_has_its_own_error_code(tmp_path):
    service, sid, package = _study(tmp_path / "registry")
    launcher = Launcher()
    bridge = StudyRunBridge(service, launcher=launcher)
    for body in ({"package_id": package["package_id"]},
                 {"package_id": package["package_id"], "idempotency_key": ""},
                 {"package_id": package["package_id"], "idempotency_key": None}):
        with pytest.raises(StudyJobError) as exc:
            bridge.launch(sid, body)
        assert exc.value.code == "missing_idempotency_key" and exc.value.http_status == 400
    with pytest.raises(StudyJobError) as exc:
        bridge.cancel(sid, {"package_id": package["package_id"]})
    assert exc.value.code == "missing_idempotency_key"
    with pytest.raises(StudyJobError) as exc:
        StudyCpuJobs(service).submit(sid, {"kind": "propose", "expected_revision": 1,
                                           "package_hash": "a" * 64})
    assert exc.value.code == "missing_idempotency_key"
    # Malformed (present but invalid) keys stay invalid_input.
    with pytest.raises(StudyJobError) as exc:
        bridge.launch(sid, {"package_id": package["package_id"], "idempotency_key": "../x"})
    assert exc.value.code == "invalid_input"
    assert launcher.calls == []


def test_registry_without_launch_table_methods_refuses_instead_of_memory(tmp_path):
    service, sid, package = _study(tmp_path / "registry")

    class Legacy:
        def __getattr__(self, name):
            if name in ("claim_launch", "settle_launch", "release_launch"):
                raise AttributeError(name)
            return getattr(service, name)

    launcher = Launcher()
    with pytest.raises(StudyJobError) as exc:
        StudyRunBridge(Legacy(), launcher=launcher).launch(sid, _body(package))
    assert exc.value.code == "capability_missing" and launcher.calls == []


def test_migration_upgrades_a_version_1_registry_in_place(tmp_path):
    root = tmp_path / "registry"
    root.mkdir()
    db = root / "studies.sqlite3"
    conn = sqlite3.connect(db, isolation_level=None)
    conn.executescript("BEGIN;" + MIGRATIONS[1] + "PRAGMA user_version=1; COMMIT;")
    conn.execute("INSERT INTO studies(id,spec_revision) VALUES ('old-study',1)")
    conn.close()
    service = StudyService(root)
    with sqlite3.connect(db) as check:
        assert check.execute("PRAGMA user_version").fetchone()[0] == max(MIGRATIONS) >= 2
        tables = {r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "launches" in tables
        assert check.execute("SELECT id FROM studies").fetchall() == [("old-study",)]
    claim, created = service.claim_launch("old-study", "a" * 64, "k")
    assert created and claim["status"] == "launching"
