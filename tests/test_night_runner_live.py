"""Live night queue (2026-11-16): the night file is re-read before every job; PAUSE/STOP control.

Offline: a fake runner stands in for hygiene/subprocesses, and a hook edits the night file while a
"job" is running, exactly as an agent would.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import tools.run_campaign_night as night


def _write(path: Path, ids, *, extra: str = "", name: str = "live_t") -> None:
    lines = [f"night: {name}", extra, "jobs:"] if extra else [f"night: {name}", "jobs:"]
    for i in ids:
        lines.append(f"  - {{id: {i}, kind: command, argv: [python, -c, pass]}}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class HookRunner:
    """Fake runner; ``hooks[job_id]`` runs while that job is "running"."""

    def __init__(self, hooks=None):
        self.hooks = dict(hooks or {})
        self.ran: list[str] = []

    def pre_hygiene(self, job, log_path):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("pre\n", encoding="utf-8")
        return {"baseline_mb": None, "note": ""}

    def run(self, job, log_path):
        self.ran.append(job.id)
        hook = self.hooks.get(job.id)
        if hook:
            hook()
        return 0, False

    def post_hygiene(self, job, log_path):
        return {"after_mb": None, "peak_mb": None, "note": ""}


def _run(tmp_path, nf, runner, **kw):
    plan = night.load_night(nf, repo_root=tmp_path)
    runs_root = tmp_path / "runs"
    night.run_night(plan, repo_root=tmp_path, runs_root=runs_root, runner=runner,
                    control_poll_s=0.01, **kw)
    return runs_root / "nights" / plan.night


def test_reorder_insert_and_remove_take_effect_after_current_job(tmp_path):
    nf = tmp_path / "n.yaml"
    _write(nf, ["a", "b", "c", "d"])
    # while "a" runs: drop b, move d before c, insert e at the front of what's left
    runner = HookRunner({"a": lambda: _write(nf, ["a", "e", "d", "c"])})
    nd = _run(tmp_path, nf, runner)
    assert runner.ran == ["a", "e", "d", "c"]
    state = json.loads((nd / "queue_state.json").read_text(encoding="utf-8"))
    assert state["state"] == "done" and state["done"] == ["a", "e", "d", "c"]


def test_finished_ids_never_rerun_even_if_moved_back(tmp_path):
    nf = tmp_path / "n.yaml"
    _write(nf, ["a", "b"])
    runner = HookRunner({"b": lambda: _write(nf, ["b", "a", "c"])})
    _run(tmp_path, nf, runner)
    assert runner.ran == ["a", "b", "c"]


def test_cpu_lane_gpu_clean_forces_past_a_busy_gpu_lane(tmp_path, monkeypatch):
    """A CPU-lane job must not inherit the GPU-busy refusal (and the false blocked retry)."""
    seen: list[list[str]] = []

    def fake_run(argv, timeout, cwd=None):
        seen.append([str(a) for a in argv])
        return 0, ""

    monkeypatch.setattr(night, "_run_capture", fake_run)
    runner = night.NightRunner(repo_root=tmp_path, runs_root=tmp_path / "runs",
                               cli_exe=tmp_path / "cli.exe", lane="cpu")
    assert runner._gpu_clean(tmp_path / "cpu.log") == 0
    assert "--force" in seen[-1]
    gpu = night.NightRunner(repo_root=tmp_path, runs_root=tmp_path / "runs",
                            cli_exe=tmp_path / "cli.exe", lane="gpu")
    assert gpu._gpu_clean(tmp_path / "gpu.log") == 0
    assert "--force" not in seen[-1]


def test_invalid_edit_keeps_last_good_plan(tmp_path):
    nf = tmp_path / "n.yaml"
    _write(nf, ["a", "b", "c"])
    runner = HookRunner({"a": lambda: nf.write_text("night: live_t\njobs: [ {id: x", encoding="utf-8")})
    _run(tmp_path, nf, runner)
    assert runner.ran == ["a", "b", "c"]
    log = (tmp_path / "runs" / "overnight" / "queue_live_t.log").read_text(encoding="utf-8")
    assert "RELOAD FAILED" in log


def test_night_name_change_is_refused(tmp_path):
    nf = tmp_path / "n.yaml"
    _write(nf, ["a", "b"])
    runner = HookRunner({"a": lambda: _write(nf, ["a", "z"], name="other")})
    _run(tmp_path, nf, runner)
    assert runner.ran == ["a", "b"]


def test_stop_file_ends_after_current_job(tmp_path):
    nf = tmp_path / "n.yaml"
    _write(nf, ["a", "b", "c"])
    nd = tmp_path / "runs" / "nights" / "live_t"
    runner = HookRunner({"a": lambda: (nd / "STOP").write_text("", encoding="utf-8")})
    _run(tmp_path, nf, runner)
    assert runner.ran == ["a"]
    assert json.loads((nd / "queue_state.json").read_text(encoding="utf-8"))["state"] == "stopped"


def test_stop_key_in_yaml(tmp_path):
    nf = tmp_path / "n.yaml"
    _write(nf, ["a", "b"])
    runner = HookRunner({"a": lambda: _write(nf, ["a", "b"], extra="stop: true")})
    _run(tmp_path, nf, runner)
    assert runner.ran == ["a"]


def test_pause_file_holds_then_resumes_with_edits_made_while_paused(tmp_path):
    nf = tmp_path / "n.yaml"
    _write(nf, ["a", "b", "c"])
    nd = tmp_path / "runs" / "nights" / "live_t"
    seen = {}

    def pause_then_edit():
        (nd / "PAUSE").write_text("", encoding="utf-8")

        def later():
            time.sleep(0.3)
            state = json.loads((nd / "queue_state.json").read_text(encoding="utf-8"))
            seen["state"] = state["state"]
            _write(nf, ["a", "c", "b"])          # reorder while paused
            time.sleep(0.05)
            (nd / "PAUSE").unlink()
        threading.Thread(target=later, daemon=True).start()

    runner = HookRunner({"a": pause_then_edit})
    _run(tmp_path, nf, runner)
    assert seen["state"] == "paused"
    assert runner.ran == ["a", "c", "b"]
    log = (tmp_path / "runs" / "overnight" / "queue_live_t.log").read_text(encoding="utf-8")
    assert "PAUSED" in log and "RESUMED" in log


def test_admission_skips_unlisted_reloaded_job(tmp_path):
    nf = tmp_path / "n.yaml"
    _write(nf, ["a", "b"])
    runner = HookRunner({"a": lambda: _write(nf, ["a", "evil", "b"])})
    _run(tmp_path, nf, runner, admission={"night": "live_t", "allowed_job_ids": ("a", "b")})
    assert runner.ran == ["a", "b"]


def test_no_live_reads_once(tmp_path):
    nf = tmp_path / "n.yaml"
    _write(nf, ["a", "b"])
    runner = HookRunner({"a": lambda: _write(nf, ["a", "c"])})
    _run(tmp_path, nf, runner, live=False)
    assert runner.ran == ["a", "b"]


def test_pause_flag_must_be_bool(tmp_path):
    nf = tmp_path / "n.yaml"
    _write(nf, ["a"], extra="pause: maybe")
    try:
        night.load_night(nf, repo_root=tmp_path)
    except ValueError as exc:
        assert "pause" in str(exc)
    else:
        raise AssertionError("pause: maybe accepted")
