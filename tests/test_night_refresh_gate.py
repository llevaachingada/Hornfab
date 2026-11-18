"""Lane gate (2026-11-17): a BO arm's ``study <study_id>`` lock holder is OUR job, not a foreign one.

Regression for the false ``PAUSE`` that stalled ``cd_rrect_2026-11-17``: ``studies.cli run
--execute`` writes ``{"command": "study <study_id>"}`` into ``runs/.gpu.lock``
(``hornlab_search/studies/lanes.py``), which shares no token with the runner's
``run_bo_arm.py --root <arm>`` argv, so the gate paused our own queue for ~19 minutes.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import tools.night_queue.refresh_watchdog as rw

NIGHT = "night_gate_test"
JOB = "arm_job"
ARM_ROOT = "runs/night31_x/turbo_arm"
STUDY_ID = "1ff9fb9cb6d04e358685213206425478"


def _repo(tmp_path: Path, *, study_id: str | None) -> Path:
    root = tmp_path
    night_dir = root / "runs" / "nights" / NIGHT
    night_dir.mkdir(parents=True)
    (root / "runs" / "nights" / f"{NIGHT}.yaml").write_text(
        "night: %s\njobs:\n  - id: %s\n    kind: command\n    argv:\n"
        "      - python\n      - tools/night_queue/run_bo_arm.py\n      - --root\n      - %s\n"
        % (NIGHT, JOB, ARM_ROOT),
        encoding="utf-8",
    )
    (night_dir / "queue_state.json").write_text(
        json.dumps({"night": NIGHT, "state": "running", "running": JOB, "pending": []}),
        encoding="utf-8",
    )
    (root / "runs" / ".gpu.lock").write_text(
        json.dumps({"pid": os.getpid(), "user": "test", "command": f"study {study_id}"}),
        encoding="utf-8",
    )
    arm = root / ARM_ROOT
    arm.mkdir(parents=True)
    con = sqlite3.connect(arm / "studies.sqlite3")
    try:
        con.execute("create table studies (id text primary key, parent_id text, spec_revision int, event_seq int)")
        if study_id:
            con.execute("insert into studies values (?, null, 1, 1)", (study_id,))
        con.commit()
    finally:
        con.close()
    return root


def test_our_own_study_arm_holds_the_lock_without_pausing(tmp_path):
    root = _repo(tmp_path, study_id=STUDY_ID)
    result = rw.gate(NIGHT, root=root)
    assert result["gate"] == "clear", result
    assert not (root / "runs" / "nights" / NIGHT / "PAUSE").exists()


def test_our_arm_clears_a_stale_pause(tmp_path):
    root = _repo(tmp_path, study_id=STUDY_ID)
    pause = root / "runs" / "nights" / NIGHT / "PAUSE"
    pause.write_text("foreign GPU-lock holder\n", encoding="utf-8")
    result = rw.gate(NIGHT, root=root)
    assert result["gate"].startswith("RESUMED"), result
    assert not pause.exists()


def test_foreign_study_holder_still_pauses(tmp_path):
    root = _repo(tmp_path, study_id=STUDY_ID)
    result = rw.gate(NIGHT, root=root)  # our id -> clear
    assert result["gate"] == "clear", result
    # same lock file, an id that is NOT registered under our arm root
    (root / "runs" / ".gpu.lock").write_text(
        json.dumps({"pid": os.getpid(), "user": "test", "command": "study someone-elses-study"}),
        encoding="utf-8",
    )
    result = rw.gate(NIGHT, root=root)
    assert result["gate"].startswith("PAUSED"), result
    assert (root / "runs" / "nights" / NIGHT / "PAUSE").exists()


def test_arm_root_without_registry_is_not_claimed(tmp_path):
    root = _repo(tmp_path, study_id=None)
    result = rw.gate(NIGHT, root=root)
    assert result["gate"].startswith("PAUSED"), result
