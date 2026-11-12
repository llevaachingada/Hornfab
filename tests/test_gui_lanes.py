"""Group E.2 lanes tests: the /api/lanes status read in gui/data.py (day-plan D.1 duplicate).

Headless and offline: synthetic runs/nights/ + runs/overnight/ folders, a lane lock file and a
fake pid for the stale case. No solver, no queue process, and the live lane box (which exists
only on the owner's machine) is never required — every fixture degrades to an empty lane.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time
from pathlib import Path

from hornlab_search.gui import data as D
from hornlab_search.gui.server import App

RID = "20261111T000000Z-screen-aaaaaa"


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    runs = root / "runs"
    runs.mkdir(parents=True)
    return root, runs


def _queue_log(path: Path, running_cmd: str | None, rid: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "=== 2026-11-11T09:00:01 START g0_done : hornlab-search verify --run runs/" + rid,
        "=== 2026-11-11T09:00:05 END g0_done exit 0",
    ]
    if running_cmd:
        lines.append("=== 2026-11-11T09:00:06 START g1_running : " + running_cmd)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _recent_night() -> str:
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=2)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _old_night() -> str:
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=2)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _write_ndjson(runs: Path, rid: str, rows: list[dict]) -> None:
    d = runs / rid
    d.mkdir(parents=True, exist_ok=True)
    (d / "search.ndjson").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _row(n: int, ts: str, j: float) -> dict:
    return {"n": n, "design_hash": f"{'a' * 12}", "ok": True, "objective": j,
            "mode": "screen", "family": "OSSE", "params": {"L_mm": 100.0 + n},
            "created_utc": ts}


def test_lane_status_missing_everything(tmp_path: Path):
    """An empty (or absent) runs tree yields idle lanes and no alert — never a crash."""
    root, runs = _repo(tmp_path)
    out = D.lane_status(runs)
    assert out["alert"] is False and out["alert_lanes"] == []
    assert [l["lane"] for l in out["lanes"]] == ["gpu", "cpu"]
    for lane in out["lanes"]:
        assert lane["lock"] is None and lane["job"] is None and lane["run"] is None
        assert lane["queue_log"] is None and lane["alert"] is None
    # even a wholly missing runs dir must not raise
    out2 = D.lane_status(runs / "nope")
    assert out2["alert"] is False


def test_lane_running_job_from_queue_log(tmp_path: Path):
    """The running job is the last queue step STARTed without END; its --resume run dir gives
    row count / newest-row age, and a fresh lane raises no alert."""
    root, runs = _repo(tmp_path)
    _queue_log(runs / "overnight" / "queue_gpu_day_2026-11-12.log",
               f"hornlab-search search --resume runs/{RID} --budget 300", RID)
    _write_ndjson(runs, RID, [_row(0, _recent_night(), 5.0), _row(1, _recent_night(), 4.0)])
    (runs / ".gpu.lock").write_text(
        json.dumps({"pid": os.getpid(), "command": "night gpu", "start_time": "x"}),
        encoding="utf-8")
    out = D.lane_status(runs)
    gpu = next(l for l in out["lanes"] if l["lane"] == "gpu")
    cpu = next(l for l in out["lanes"] if l["lane"] == "cpu")
    assert gpu["lock"]["alive"] is True
    assert gpu["job"]["name"] == "g1_running"
    assert gpu["job"]["run_dir"].endswith(str(Path("runs") / RID))
    assert gpu["run"]["n_rows"] == 2 and gpu["run"]["n_ok"] == 2
    assert gpu["run"]["best_j"] == 4.0 and gpu["run"]["id"] == RID
    assert gpu["run"]["newest_row_age_min"] < 30.0
    assert gpu["alert"] is None
    assert out["alert"] is False
    # the CPU lane has no lock/log here: idle, no alert
    assert cpu["lock"] is None and cpu["job"] is None and cpu["alert"] is None


def test_lane_alert_when_newest_row_is_stale(tmp_path: Path):
    """D.1: newest row older than 30 min while the job runs -> ALERT."""
    root, runs = _repo(tmp_path)
    _queue_log(runs / "overnight" / "queue_gpu_day.log", f"search --resume runs/{RID}", RID)
    _write_ndjson(runs, RID, [_row(0, _old_night(), 5.0)])
    out = D.lane_status(runs)
    gpu = next(l for l in out["lanes"] if l["lane"] == "gpu")
    assert gpu["alert"] is not None and gpu["alert"]["age_min"] > 30.0
    assert out["alert"] is True and out["alert_lanes"] == ["gpu"]


def test_lane_alert_when_no_rows_yet(tmp_path: Path):
    """A running job whose run dir has no rows at all alerts only once the job itself has run
    for a while (started long ago in the queue log)."""
    root, runs = _repo(tmp_path)
    _queue_log(runs / "overnight" / "queue_gpu_day.log", f"search --resume runs/{RID}", RID)
    (runs / RID).mkdir()
    (runs / RID / "search.ndjson").write_text("", encoding="utf-8")
    out = D.lane_status(runs)
    gpu = next(l for l in out["lanes"] if l["lane"] == "gpu")
    # the queue-log START line is dated 2026-11-11: hours ago
    assert gpu["alert"] is not None and "no evaluable row" in gpu["alert"]["reason"]


def test_lane_stale_lock_and_last_completed_job(tmp_path: Path):
    """A lock whose holder pid is gone reads as stale; the lane's newest night dir supplies the
    last completed job row (context, never an alert)."""
    root, runs = _repo(tmp_path)
    night = runs / "nights" / "cpu_day_2026-11-12"
    night.mkdir(parents=True)
    (night / "summary.jsonl").write_text(json.dumps({
        "id": "c1_verify", "start": "2026-11-11T08:00:00Z", "end": "2026-11-11T08:10:00Z",
        "seconds": 600.0, "exit_code": 0, "run_dir": str(runs / RID),
        "evals_ndjson": 8, "best_J": 9.5, "note": ""}) + "\n", encoding="utf-8")
    (runs / ".cpu.lane.lock").write_text(
        json.dumps({"pid": 999_999_999, "command": "night cpu", "start_time": "x"}),
        encoding="utf-8")
    out = D.lane_status(runs)
    cpu = next(l for l in out["lanes"] if l["lane"] == "cpu")
    assert cpu["lock"]["alive"] is False
    assert cpu["last_job"]["id"] == "c1_verify" and cpu["last_job"]["exit_code"] == 0
    assert cpu["alert"] is None and cpu["job"] is None


def test_lanes_api_route(tmp_path: Path):
    """GET /api/lanes serves the same payload through the App routing."""
    root, runs = _repo(tmp_path)
    _queue_log(runs / "overnight" / "queue_gpu_day.log", f"search --resume runs/{RID}", RID)
    _write_ndjson(runs, RID, [_row(0, _recent_night(), 4.0)])
    out = App(root, runs).get("/api/lanes", {})
    assert [l["lane"] for l in out["lanes"]] == ["gpu", "cpu"]
    assert out["alert"] is False
