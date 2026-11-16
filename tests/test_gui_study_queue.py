import json
from pathlib import Path

import pytest
import yaml

from hornlab_search.gui.server import App
from hornlab_search.gui.study_queue import queue_study
from hornlab_search.studies.schema import StudyError, Unavailable
from hornlab_search.studies.service import StudyService


def _study(tmp_path):
    service = StudyService(tmp_path / "registry")
    created = service.create_study({"protocol": "bo-study-v1.1", "question": "queue me"}, "create")
    package = service.attach_artifact(
        created["id"], 1, "package", b'{"package_id":"placeholder"}', {}, "package")
    (tmp_path / "registry" / "package.json").write_text(json.dumps({
        "package_id": package["sha256"], "spec_revision": 1, "lane": "gpu",
    }), encoding="utf-8")
    return service, created["id"], package["sha256"]


def test_queue_study_writes_a_night_file_and_never_launches(tmp_path):
    service, sid, package_id = _study(tmp_path)
    result = queue_study(service, sid, root=tmp_path, runs_root=tmp_path / "runs", payload={})
    night = tmp_path / "runs" / "nights" / f"study-{package_id[:16]}.yaml"
    assert result["status"] == "ok" and result["existing"] is False
    assert night.is_file()
    payload = yaml.safe_load(night.read_text(encoding="utf-8"))
    assert payload["night"] == f"study-{package_id[:16]}"
    assert payload["lane"] == "gpu"
    job = payload["jobs"][0]
    assert job["kind"] == "command"
    assert job["argv"][-5:] == ["--package", "package.json", "--execute", "--project-root", str(tmp_path)]
    assert "queue.ps1" in result["command"]
    assert "not launched" in result["note"].lower()


def test_queue_study_is_idempotent_and_refuses_missing_package(tmp_path):
    service, sid, package_id = _study(tmp_path)
    first = queue_study(service, sid, root=tmp_path, runs_root=tmp_path / "runs", payload={})
    night = tmp_path / "runs" / "nights" / f"study-{package_id[:16]}.yaml"
    before = night.read_text(encoding="utf-8")
    second = queue_study(service, sid, root=tmp_path, runs_root=tmp_path / "runs", payload={})
    assert second["existing"] is True
    assert night.read_text(encoding="utf-8") == before
    service2 = StudyService(tmp_path / "other")
    other = service2.create_study({"protocol": "bo-study-v1.1"}, "create")
    with pytest.raises(Unavailable):
        queue_study(service2, other["id"], root=tmp_path, runs_root=tmp_path / "runs", payload={})


def test_queue_route_uses_the_owning_root(tmp_path):
    service, sid, package_id = _study(tmp_path)
    app = App(tmp_path, runs=tmp_path / "runs", study_service=service)
    # The route resolves the discovered root; force discovery after writing the registry.
    result = app.post(f"/api/studies/{sid}/queue", {"expected_revision": 1})
    assert result["night"] == f"study-{package_id[:16]}"
    assert (tmp_path / "runs" / "nights" / f"study-{package_id[:16]}.yaml").is_file()


def test_child_route_clones_the_parent_spec_and_sets_the_policy(tmp_path):
    service, sid, _package_id = _study(tmp_path)
    app = App(tmp_path, runs=tmp_path / "runs", study_service=service)
    parent = service.get_study(sid)
    child = app.post(f"/api/studies/{sid}/child", {
        "question": "Polish this winner", "policy": "turbo", "idempotency_key": "child-1"})
    assert child["parent_id"] == sid
    created = service.get_study(child["id"])
    assert created["spec"]["question"] == "Polish this winner"
    assert created["spec"]["policy"]["proposal_policy"] == "turbo"
    assert created["parent_id"] == sid
    assert created["spec"].get("source") == parent["spec"].get("source")
    with pytest.raises(StudyError):
        app.post(f"/api/studies/{sid}/child", {"question": "", "policy": "turbo",
                                              "idempotency_key": "child-2"})


