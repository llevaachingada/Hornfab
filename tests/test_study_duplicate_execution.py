"""A duplicate worker must leave the active worker's durable identity untouched."""
import json
from types import SimpleNamespace

import pytest

from hornlab_search.studies import production, runner


@pytest.fixture
def duplicate_execution(tmp_path, monkeypatch):
    package_id = "a" * 64
    package = {"package_id": package_id}
    service = SimpleNamespace(store=SimpleNamespace(root=tmp_path / "registry"))
    worker = service.store.root / "workers" / package_id
    worker.mkdir(parents=True)
    process_file = worker / "process.json"
    process_file.write_text(json.dumps({"pid": 73123}), encoding="utf-8")
    result_file = worker / "result.json"
    result_file.write_text(json.dumps({"status": "running", "owner": "original"}), encoding="utf-8")
    run_json = tmp_path / "runs" / ("study-" + package_id[:16]) / "screen" / "run.json"
    run_json.parent.mkdir(parents=True)
    run_json.write_text(json.dumps({"status": "running", "owner": "original"}), encoding="utf-8")
    before = {path: path.read_bytes() for path in (process_file, result_file, run_json)}
    monkeypatch.setattr(production, "execution_capability", lambda *a, **k: {"status": "ok"})
    monkeypatch.setattr(production, "build_worker", lambda *a, **k: (None, None, None))
    monkeypatch.setattr(runner, "run_package", lambda *a, **k: {"status": "launch_conflict_or_stale"})
    result = production.execute_study(service, package, root=tmp_path)
    return result, before


def test_duplicate_execution_does_not_replace_live_worker_identity(duplicate_execution):
    result, before = duplicate_execution
    assert result["status"] == "launch_conflict_or_stale"
    process = next(path for path in before if path.name == "process.json")
    assert process.read_bytes() == before[process]


def test_duplicate_execution_does_not_rewrite_active_run_or_result(duplicate_execution):
    _, before = duplicate_execution
    for path, content in before.items():
        if path.name != "process.json":
            assert path.read_bytes() == content
