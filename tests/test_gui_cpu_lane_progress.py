"""Offline tests for the CPU lane's status/progress payload (gui/data.py).

Synthetic runs/ trees only: a live lane lock (our own pid), the night queue log, run folders and
their ndjson rows. The Julia/VRAM probes are patched out, so no solver, GPU or real run is used.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
from pathlib import Path

from hornlab_search.gui import data as D

NIGHT = "cpu_progress_2026-11-13"
FRESH = "20261113T200000Z-screen-abc123"
OLD = "20261113T180000Z-screen-def456"


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    runs = root / "runs"
    runs.mkdir(parents=True)
    return root, runs


def _utc(minutes_ago: float) -> str:
    t = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _local(minutes_ago: float) -> str:
    t = dt.datetime.now() - dt.timedelta(minutes=minutes_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%S")


def _write_lock(runs: Path, night: str) -> None:
    (runs / ".cpu.lane.lock").write_text(
        json.dumps({"pid": os.getpid(), "command": f"night {night}", "start_time": "x"}),
        encoding="utf-8")


def _write_queue_log(runs: Path, night: str, started: str, command: str,
                     name: str = "cpu_job") -> None:
    ov = runs / "overnight"
    ov.mkdir(parents=True, exist_ok=True)
    (ov / f"queue_{night}.log").write_text(
        f"=== {started} START {name} : {command}\n", encoding="utf-8")


def _row(n: int, ts: str, j: float | None, *, ok: bool = True, h: str = "a" * 12,
         lane: str = "cpu") -> dict:
    return {"n": n, "design_hash": h, "ok": ok, "objective": j, "mode": "screen",
            "family": "OSSE", "params": {"L_mm": 100.0 + n}, "created_utc": ts,
            "lane": lane, "backend": "beat_cpu" if lane == "cpu" else "beat_cuda"}


def _write_run(runs: Path, rid: str, rows: list[dict], run_json: dict | None = None) -> Path:
    d = runs / rid
    d.mkdir(parents=True, exist_ok=True)
    (d / "search.ndjson").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    if run_json is not None:
        (d / "run.json").write_text(json.dumps(run_json), encoding="utf-8")
    return d


def _status(root: Path, runs: Path, monkeypatch) -> dict:
    from hornlab_search.search import hygiene
    monkeypatch.setattr(hygiene, "list_project_julia", lambda: [])
    monkeypatch.setattr(hygiene, "vram_used_mib", lambda: None)
    return D.status(root, runs)


def test_cpu_search_progress_without_job_log_output_line(tmp_path: Path, monkeypatch):
    """A fresh --config CPU search: no job-log ``output`` line and no --resume. The lane still
    resolves the run from its cpu-tagged last row and reports real session/rate/ETA/best/failures."""
    root, runs = _repo(tmp_path)
    _write_lock(runs, NIGHT)
    started = _local(14)
    command = ("hornlab-search search --config examples/x.yaml --mode screen --budget 60 "
               "--backend beat_cpu")
    _write_queue_log(runs, NIGHT, started, command, name="cpu_search")
    fresh = _write_run(runs, FRESH, [
        _row(0, _utc(13), 5.0, h="a" * 12),          # seed, 13 min ago
        _row(1, _utc(7), None, ok=False, h="b" * 12),  # a failure, 7 min ago
        _row(2, _utc(1), 3.0, h="c" * 12),           # best, 1 min ago (12 min span)
    ], {"command": command, "backend": "beat_cpu", "mode": "screen"})

    out = _status(root, runs, monkeypatch)
    cc = out["cpu_current"]

    assert cc is not None
    assert cc["kind"] == "search" and cc["mode"] == "screen"
    assert cc["run_id"] == FRESH
    assert cc["n"] == 3
    assert cc["session"]["n"] == 3 and cc["session"]["budget"] == 60
    assert cc["session"]["resumed"] is False and cc["session"]["n_resumes"] == 0
    assert abs(cc["rate_per_h"] - 10.0) < 0.5
    assert abs(cc["eta_min"] - 342.0) < 2.0
    assert cc["best_j"] == 3.0 and cc["seed_j"] == 5.0 and cc["session_best_j"] == 3.0
    assert cc["failures_session"] == 1
    assert cc["started"] == started
    assert cc["backend"] == "beat_cpu"
    # the job's own command rides in the payload (no cross-block local reference)
    assert out["cpu_job"]["command"] == command

    # Misattribution guard: an older completed cpu-lane run must not be claimed as this job's run.
    # Delete the fresh dir and make the old run the mtime-newest candidate; its session started
    # long before the queue job, so the fallback is rejected (honest None, not a false card).
    _write_run(runs, OLD, [_row(0, _utc(180), 4.0), _row(1, _utc(174), 4.5, h="d" * 12)],
               {"command": "hornlab-search search --config old.yaml --budget 30",
                "backend": "beat_cpu", "mode": "screen"})
    shutil.rmtree(fresh)
    now = dt.datetime.now().timestamp()
    os.utime(runs / OLD / "search.ndjson", (now, now))
    out2 = _status(root, runs, monkeypatch)
    assert out2["cpu_current"] is None


def test_cpu_verify_progress(tmp_path: Path, monkeypatch):
    """A queued CPU verify reports the job's own rows against its --top target: n / budget,
    rate, ETA, best score and failures — the same numbers the GPU card shows."""
    root, runs = _repo(tmp_path)
    night = "cpu_verify_progress_2026-11-13"
    rid = "20261113T190000Z-verify-abc123"
    _write_lock(runs, night)
    started = _local(10)
    command = f"hornlab-search verify --run runs/{rid} --top 4"
    _write_queue_log(runs, night, started, command, name="cpu_verify")
    _write_run(runs, rid, [])
    (runs / rid / "verify").mkdir(parents=True, exist_ok=True)
    (runs / rid / "verify" / "search.ndjson").write_text(
        "\n".join(json.dumps(r) for r in [
            _row(0, _utc(8), 4.0, h="e" * 12),
            _row(1, _utc(2), 3.5, h="f" * 12),
        ]) + "\n", encoding="utf-8")

    out = _status(root, runs, monkeypatch)
    cc = out["cpu_current"]

    assert cc is not None
    assert cc["kind"] == "verify" and cc["mode"] == "verify"
    assert cc["run_id"] == rid
    assert cc["n"] == 2 and cc["session"]["n"] == 2
    assert cc["session"]["budget"] == 4
    assert cc["session"]["resumed"] is False and cc["session"]["n_resumes"] == 0
    assert abs(cc["rate_per_h"] - 10.0) < 0.5
    assert abs(cc["eta_min"] - 12.0) < 0.5
    assert cc["best_j"] == 3.5 and cc["session_best_j"] == 3.5
    assert cc["seed_j"] is None
    assert cc["failures_session"] == 0
    assert cc["started"] == started
    assert cc["backend"] == "beat_cpu"


def test_cpu_verify_without_run_id_uses_mtime_fallback(tmp_path: Path, monkeypatch):
    """A verify job whose command carries no --run keeps the mtime-newest verify output branch."""
    root, runs = _repo(tmp_path)
    night = "cpu_verify_fallback_2026-11-13"
    rid = "20261113T170000Z-screen-fedcba"
    _write_lock(runs, night)
    started = _local(8)
    _write_queue_log(runs, night, started, "hornlab-search verify --top 2", name="cpu_verify2")
    _write_run(runs, rid, [])
    (runs / rid / "verify").mkdir(parents=True, exist_ok=True)
    (runs / rid / "verify" / "search.ndjson").write_text(
        "\n".join(json.dumps(r) for r in [
            _row(0, _utc(6), 4.0, h="1" * 12),
            _row(1, _utc(1), 3.0, h="2" * 12),
        ]) + "\n", encoding="utf-8")

    cc = _status(root, runs, monkeypatch)["cpu_current"]
    assert cc is not None
    assert cc["kind"] == "verify" and cc["run_id"] == rid
    assert cc["n"] == 2 and cc["session"]["budget"] == 2
    assert cc["rate_per_h"] is not None and cc["best_j"] == 3.0


def test_cpu_lane_idle_and_empty_tree(tmp_path: Path, monkeypatch):
    """No live CPU lock -> no cpu_current; an empty/missing runs tree must not raise."""
    root, runs = _repo(tmp_path)
    out = _status(root, runs, monkeypatch)
    assert out["cpu_current"] is None

    out2 = _status(root, root / "missing_runs", monkeypatch)
    assert out2["cpu_current"] is None


def test_cpu_search_resume_reports_current_session(tmp_path: Path, monkeypatch):
    """A resumed CPU search (``--resume``) resolves by path and reports the CURRENT invocation:
    session rows/budget from the new command, rate/ETA over the post-resume rows only."""
    root, runs = _repo(tmp_path)
    night = "cpu_resume_2026-11-13"
    rid = "20261113T150000Z-screen-a1b2c3"
    _write_lock(runs, night)
    command = f"hornlab-search search --resume runs/{rid} --budget 40 --backend beat_cpu"
    _write_queue_log(runs, night, _local(6), command, name="cpu_resumed")
    _write_run(runs, rid, [
        _row(0, _utc(30), 6.0, h="a" * 12),   # previous invocation
        _row(1, _utc(25), 5.5, h="b" * 12),
        _row(2, _utc(5), 5.0, h="c" * 12),    # current invocation (3 rows, 4 min span)
        _row(3, _utc(4), 4.0, h="d" * 12),
        _row(4, _utc(1), 3.0, h="e" * 12),
    ], {"command": command, "resumes": [_utc(5)], "mode": "screen", "backend": "beat_cpu"})

    cc = _status(root, runs, monkeypatch)["cpu_current"]
    assert cc is not None
    assert cc["kind"] == "search" and cc["run_id"] == rid
    assert cc["n"] == 5                                     # lifetime rows
    assert cc["session"]["n"] == 3 and cc["session"]["budget"] == 40
    assert cc["session"]["resumed"] is True and cc["session"]["n_resumes"] == 1
    assert abs(cc["rate_per_h"] - 30.0) < 0.5
    assert abs(cc["eta_min"] - 74.0) < 1.0
    assert cc["session_best_j"] == 3.0


def test_two_lane_split_gpu_and_cpu_current_are_independent(tmp_path: Path, monkeypatch):
    """With both lanes live, the GPU card keeps the GPU run and the CPU card takes the newest
    CPU-tagged run — neither swallows the other's rows."""
    root, runs = _repo(tmp_path)
    gpu_rid = "20261113T180000Z-screen-aaaaaa"
    cpu_rid = "20261113T200000Z-screen-bbbbbb"
    _write_run(runs, gpu_rid, [_row(0, _utc(20), 5.0, lane="gpu"),
                               _row(1, _utc(15), 4.5, lane="gpu")])
    _write_run(runs, cpu_rid, [_row(0, _utc(4), 5.0, lane="cpu"),
                               _row(1, _utc(1), 4.0, lane="cpu")])
    gpu_cmd = f"hornlab-search search --resume runs/{gpu_rid} --budget 100"
    _write_queue_log(runs, "gpu_split", _local(21), gpu_cmd, name="g1")
    (runs / ".gpu.lock").write_text(
        json.dumps({"pid": os.getpid(), "command": "night gpu_split", "start_time": "x"}),
        encoding="utf-8")
    _write_lock(runs, "cpu_split")
    _write_queue_log(runs, "cpu_split", _local(5),
                     "hornlab-search search --config examples/c.yaml --budget 60 --backend beat_cpu",
                     name="c1")

    out = _status(root, runs, monkeypatch)
    assert out["current"] is not None and out["current"]["id"] == gpu_rid
    assert out["cpu_current"] is not None and out["cpu_current"]["run_id"] == cpu_rid
    assert out["cpu_current"]["kind"] == "search"


def test_cpu_lock_alive_without_queue_step_is_honest_none(tmp_path: Path, monkeypatch):
    """A live CPU lock with no parseable queue step cannot name a job: cpu_current stays None
    (the frontend's honest 'waiting' card) instead of guessing a run."""
    root, runs = _repo(tmp_path)
    _write_lock(runs, "lonely_cpu_night")
    out = _status(root, runs, monkeypatch)
    assert out["cpu_lock"]["alive"] is True
    assert out["cpu_job"] is None
    assert out["cpu_current"] is None


def test_lane_status_resolves_fresh_search_runs_for_both_lanes(tmp_path: Path):
    """The /api/lanes table gets the same run/progress resolution as the cards: a fresh
    ``--config`` job (no --resume/--out) resolves to its own lane's newest run, so rows, rate and
    ETA render instead of 'run dir not resolved'. Each lane keeps its own run."""
    root, runs = _repo(tmp_path)
    gpu_rid = "20261113T180000Z-screen-aaaaaa"
    cpu_rid = "20261113T200000Z-screen-bbbbbb"
    _write_run(runs, gpu_rid, [
        _row(0, _utc(9), 5.0, lane="gpu"),
        _row(1, _utc(6), 4.5, lane="gpu"),
        _row(2, _utc(3), 4.0, lane="gpu"),
    ], {"command": "hornlab-search search --config g.yaml --budget 100", "mode": "screen"})
    _write_run(runs, cpu_rid, [
        _row(0, _utc(4), 5.0),
        _row(1, _utc(2), 4.5, h="b" * 12),
        _row(2, _utc(1), 4.0, h="c" * 12),
    ], {"command": "hornlab-search search --config c.yaml --budget 60 --backend beat_cpu",
        "mode": "screen", "backend": "beat_cpu"})
    _write_queue_log(runs, "gpu_day", _local(10),
                     "hornlab-search search --config g.yaml --budget 100", name="g1")
    (runs / ".gpu.lock").write_text(
        json.dumps({"pid": os.getpid(), "command": "night gpu_day", "start_time": "x"}),
        encoding="utf-8")
    _write_lock(runs, "cpu_day")
    _write_queue_log(runs, "cpu_day", _local(5),
                     "hornlab-search search --config c.yaml --budget 60 --backend beat_cpu",
                     name="c1")

    lanes = {l["lane"]: l for l in D.lane_status(runs)["lanes"]}
    assert lanes["gpu"]["run"]["id"] == gpu_rid
    assert lanes["cpu"]["run"]["id"] == cpu_rid
    assert lanes["gpu"]["run"]["n_rows"] == 3 and lanes["cpu"]["run"]["n_rows"] == 3
    assert lanes["cpu"]["run"]["budget"] == 60
    assert lanes["cpu"]["run"]["rate_per_h"] is not None
    assert lanes["cpu"]["run"]["eta_min"] is not None
    # a lane row that resolved a run no longer prints the unresolved note
    assert lanes["cpu"]["note"] is None and lanes["gpu"]["note"] is None
