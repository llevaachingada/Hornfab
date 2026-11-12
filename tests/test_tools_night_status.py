"""Offline tests for tools/night_status.py's two-lane section (D.1, 2026-11-12).

Hermetic: the runs tree (queue logs, night dirs, locks) is a fixture in tmp_path; the clock and
the liveness probe are injected. No real runs/, no processes, no GPU.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

from conftest import REPO

TOOL = REPO / "tools" / "night_status.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("night_status_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


status = _load_tool()


# ------------------------------------------------------------------ fixtures


def _write_runs_tree(tmp_path: Path, *, gpu_age_s: float = 60.0, cpu_age_s: float = 2400.0,
                     gpu_dead_holder: bool = False) -> tuple[Path, Path, float]:
    """A fake runs tree with two queue logs, two night dirs, and both lock files."""
    runs_root = tmp_path / "runs"
    now = time.time()

    # GPU lane: job running, run dir fresh
    gpu_nd = runs_root / "nights" / "gpu_day_2026-11-12"
    gpu_run = tmp_path / "runs_roots_gpu" / "20261112T100001Z-screen-aaaa1"
    gpu_run.mkdir(parents=True)
    (gpu_run / "search.ndjson").write_text('{"ok": true}\n' * 40, encoding="utf-8")
    os.utime(gpu_run / "search.ndjson", (now - gpu_age_s, now - gpu_age_s))
    gpu_nd.mkdir(parents=True)
    (gpu_nd / "g1.log").write_text(
        f"search: g1 mode screen, output {gpu_run}\n", encoding="utf-8")
    overnight = runs_root / "overnight"
    overnight.mkdir(parents=True)
    (overnight / "queue_gpu_day_2026-11-12.log").write_text(
        "=== 2026-11-12T10:00:00 START g1 : hornlab-search.exe search --config c.yaml\n"
        "=== 2026-11-12T10:01:40 RETRY g1 blocked (GPU busy); retrying once in 120s\n"
        "=== 2026-11-12T10:03:40 RETRY g1 now (attempt 2)\n",  # no END yet: still open
        encoding="utf-8")
    gpu_lock = runs_root / ".gpu.lock"
    holder_pid = 987654321 if gpu_dead_holder else os.getpid()
    gpu_lock.write_text(json.dumps({
        "pid": holder_pid, "user": "hunte",
        "command": "hornlab-search search --config c.yaml",
        "start_time": "2026-11-12T10:00:01",
    }), encoding="utf-8")

    # CPU lane: job running, run dir stale (should ALERT when cpu_age_s > 1800)
    cpu_nd = runs_root / "nights" / "cpu_day_2026-11-12"
    cpu_run = tmp_path / "runs_roots_cpu" / "20261112T100002Z-screen-bbbb2"
    cpu_run.mkdir(parents=True)
    (cpu_run / "search.ndjson").write_text('{"ok": true}\n' * 7, encoding="utf-8")
    os.utime(cpu_run / "search.ndjson", (now - cpu_age_s, now - cpu_age_s))
    cpu_nd.mkdir(parents=True)
    (cpu_nd / "c2.log").write_text(
        f"search: c2 mode screen, output {cpu_run}\n", encoding="utf-8")
    (overnight / "queue_cpu_day_2026-11-12.log").write_text(
        "=== 2026-11-12T10:00:05 START c2 : hornlab-search.exe search --config d.yaml "
        "--backend beat_cpu --cache-dir cache_cpu\n",  # no END yet: still open -> ALERT
        encoding="utf-8")
    (runs_root / ".cpu.lane.lock").write_text(json.dumps({
        "pid": os.getpid(), "user": "hunte", "command": "night cpu_day_2026-11-12",
        "start_time": "2026-11-12T10:00:31",
    }), encoding="utf-8")

    # A controller queue log for the gpu night (deduped in favour of the runner's log)
    (runs_root / "nights" / "queue_gpu_day_2026-11-12.log").write_text(
        "2026-11-12T10:00:00 queue start (pid 42612): gpu_day_2026-11-12\n"
        "2026-11-12T10:00:00 starting gpu_day_2026-11-12\n", encoding="utf-8")
    return runs_root, tmp_path, now


# ------------------------------------------------------------------ pure helpers


def test_lane_of_argv():
    assert status.lane_of_argv("search --config x --backend beat_cpu --cache-dir cache_cpu") == "cpu"
    assert status.lane_of_argv("search --config x --backend=beat_cpu") == "cpu"
    assert status.lane_of_argv("search --config x") == "gpu"
    assert status.lane_of_argv("verify --run runs/x") == "gpu"


def test_parse_queue_log_open_jobs_and_retry_semantics():
    text = (
        "=== 2026-11-12T09:35:01 START g0 : search --run runs/a\n"
        "=== 2026-11-12T09:35:21 END g0 exit 0\n"
        "=== 2026-11-12T09:35:21 START g1 : search --config c.yaml\n"
        "=== 2026-11-12T09:35:30 RETRY g1 now (attempt 2)\n"
        "=== 2026-11-12T09:35:40 START g2 : search --config d.yaml\n"
        "=== 2026-11-12T09:35:50 END g2 exit 3\n"
    )
    open_jobs = status.parse_queue_log(text)
    assert [job["id"] for job in open_jobs] == ["g1"]      # g0/g2 closed; RETRY keeps g1 open
    assert open_jobs[0]["argv"] == "search --config c.yaml"

    # a START with no END at all is open
    assert [job["id"] for job in status.parse_queue_log(
        "=== 2026-11-12T10:00:00 START zz : echo hi\n")] == ["zz"]


def test_night_queue_logs_dedupes_runner_over_controller(tmp_path):
    runs_root = tmp_path / "runs"
    (runs_root / "overnight").mkdir(parents=True)
    (runs_root / "nights").mkdir(parents=True)
    runner = runs_root / "overnight" / "queue_gpu_day.log"
    controller = runs_root / "nights" / "queue_gpu_day.log"
    runner.write_text("x", encoding="utf-8")
    controller.write_text("y", encoding="utf-8")
    pairs = dict(status.night_queue_logs(runs_root))
    assert pairs["gpu_day"] == runner          # the runner log carries the START/END lines


# ------------------------------------------------------------------ locks


def test_lock_status_reports_live_and_stale_holders(tmp_path):
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    live = status.lock_status("cpu", runs_root, alive_fn=lambda pid: pid == os.getpid())
    assert live["held"] is False and live["pid"] is None

    (runs_root / ".cpu.lane.lock").write_text(json.dumps({
        "pid": os.getpid(), "user": "hunte", "command": "night x",
        "start_time": "2026-11-12T10:00:31"}), encoding="utf-8")
    live = status.lock_status("cpu", runs_root, alive_fn=lambda pid: pid == os.getpid())
    assert live["held"] is True and live["alive"] is True and live["record"]["user"] == "hunte"

    (runs_root / ".gpu.lock").write_text(json.dumps({
        "pid": 90_000_000, "user": "gone", "command": "old",
        "start_time": "2026-11-11T23:00:00"}), encoding="utf-8")
    stale = status.lock_status("gpu", runs_root, alive_fn=lambda pid: pid == os.getpid())
    assert stale["held"] is True and stale["alive"] is False and stale["pid"] == 90_000_000


# ------------------------------------------------------------------ the two-lane report


def _report(runs_root, repo_root, **kw):
    return "\n".join(status.build_lane_report(runs_root, repo_root, **kw))


def test_lane_report_shows_running_jobs_rows_and_ages(tmp_path):
    runs_root, tmp_path, now = _write_runs_tree(tmp_path, gpu_age_s=120.0, cpu_age_s=600.0)
    text = _report(runs_root, tmp_path, now=now)

    assert "## Lanes" in text
    assert '- lane gpu: lock' in text and "HELD by pid" in text and "live holder" in text
    assert str(runs_root / ".gpu.lock") in text
    # GPU running job with a fresh run dir: 40 rows, ~2 min old, NO alert
    gpu_line = [line for line in text.splitlines() if "running job g1" in line][0]
    assert "night gpu_day_2026-11-12" in gpu_line and "40 rows" in gpu_line and "2 min old" in gpu_line
    assert "ALERT" not in text.split("## Lanes")[1].split("running job c2")[0]
    # CPU running job: 7 rows
    cpu_line = [line for line in text.splitlines() if "running job c2" in line][0]
    assert "night cpu_day_2026-11-12" in cpu_line and "7 rows" in cpu_line


def test_alert_when_newest_row_is_over_30_minutes_old(tmp_path):
    runs_root, tmp_path, now = _write_runs_tree(tmp_path, cpu_age_s=45 * 60.0)
    text = _report(runs_root, tmp_path, now=now)

    assert "ALERT lane cpu: newest row is 45 min old" in text
    assert "while job c2 runs" in text
    assert "ALERT lane gpu" not in text           # the gpu run dir is fresh


def test_no_alert_when_the_row_age_is_under_the_threshold(tmp_path):
    runs_root, tmp_path, now = _write_runs_tree(tmp_path, cpu_age_s=20 * 60.0)
    assert "ALERT" not in _report(runs_root, tmp_path, now=now)


def test_stale_lock_holder_is_named_in_the_report(tmp_path):
    runs_root, tmp_path, now = _write_runs_tree(tmp_path, gpu_dead_holder=True)
    text = _report(runs_root, tmp_path, now=now, alive_fn=lambda pid: pid == os.getpid())
    assert "STALE holder (pid gone; take over)" in text


def test_abandoned_old_queue_logs_hold_no_running_job(tmp_path):
    """A queue log whose runner died weeks ago shows no running job (its mtime is stale)."""
    runs_root, tmp_path, now = _write_runs_tree(tmp_path)
    stale = time.time() - 20 * 86400
    os.utime(runs_root / "overnight" / "queue_gpu_day_2026-11-12.log", (stale, stale))
    os.utime(runs_root / "overnight" / "queue_cpu_day_2026-11-12.log", (stale, stale))
    text = _report(runs_root, tmp_path, now=now)
    assert text.count("  - running job: none") == 2
    assert "running job g1" not in text and "running job c2" not in text
    assert "ALERT" not in text
