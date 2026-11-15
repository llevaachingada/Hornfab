import json
from pathlib import Path
import sys

from tools.geometry import verify_rolled_rect_night as verifier


def add_run(tmp_path, job="one", exit_code=0):
    run = tmp_path / ("run_" + job)
    run.mkdir()
    (run / "search.ndjson").write_text("", encoding="utf-8")
    night = tmp_path / "night_a"
    night.mkdir(exist_ok=True)
    with (night / "summary.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"id": job, "exit_code": exit_code, "run_dir": str(run)}) + "\n")
    return run


def test_invokes_adapter_memwatch_and_batch(tmp_path, monkeypatch):
    run = add_run(tmp_path)
    calls = []
    monkeypatch.setattr(verifier.subprocess, "call", lambda argv, **kw: calls.append((argv, kw)) or 0)
    assert verifier.main(["--night", "night_a", "--nights-dir", str(tmp_path), "--jobs", "one"]) == 0
    argv, kwargs = calls[0]
    assert argv == [sys.executable, str(verifier.MEMWATCH), "--out", str(tmp_path / "night_a" / "memwatch" / "one.json"),
                    "--", sys.executable, str(verifier.WRAPPER), "verify", "--run", str(run), "--top", "1"]
    assert kwargs["env"]["HORNLAB_FREQ_BATCH_SIZE"] == "12"
    assert kwargs["cwd"] == str(verifier.ROOT)


def test_dry_run_never_launches_and_missing_is_failure(tmp_path, monkeypatch):
    add_run(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("dry run launched subprocess")
    monkeypatch.setattr(verifier.subprocess, "call", forbidden)
    assert verifier.main(["--night", "night_a", "--nights-dir", str(tmp_path), "--jobs", "one", "--dry-run"]) == 0
    assert verifier.main(["--night", "night_a", "--nights-dir", str(tmp_path), "--jobs", "missing", "--dry-run"]) == 3


def test_sequential_failures_and_skipped_propagate(tmp_path, monkeypatch):
    add_run(tmp_path, "one")
    add_run(tmp_path, "two")
    add_run(tmp_path, "failed_search", exit_code=1)
    calls = []
    def invoke(argv, **kwargs):
        calls.append(argv)
        return 1 if len(calls) == 1 else 0
    monkeypatch.setattr(verifier.subprocess, "call", invoke)
    assert verifier.main(["--night", "night_a", "--nights-dir", str(tmp_path), "--jobs", "one,two,failed_search", "--top", "2"]) == 3
    assert len(calls) == 2
    assert all(c[-2:] == ["--top", "2"] for c in calls)
