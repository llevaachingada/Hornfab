"""Write a night-queue file for a prepared study package.

This module deliberately does not launch a runner.  The GUI server must never start a second
GPU runner beside a live night (night-queue rule 3), so the safe action is to produce a new
night file and hand the owner the exact queue command.  The caller can launch it detached after
checking that no other runner is live.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import yaml

from hornlab_search.studies.schema import Conflict, Unavailable
from hornlab_search.studies.service import StudyService

NIGHT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return str(path)


def queue_study(service: StudyService, study_id: str, *, root: Path, runs_root: Path,
                payload: dict) -> dict:
    """Write ``runs/nights/study-<pkg16>.yaml``; return its path and the queue command."""
    if not isinstance(payload, dict):
        raise Unavailable("queue request must be an object")
    study = service.get_study(study_id)
    meta = service.get_artifact_metadata(study_id, "package")
    if meta.get("status") != "available":
        raise Unavailable("prepare the immutable solve package before queueing this study")
    package_id = meta.get("sha256")
    if not isinstance(package_id, str) or len(package_id) != 64:
        raise Unavailable("package identity is missing")
    package_path = Path(service.store.root) / "package.json"
    if not package_path.is_file():
        raise Unavailable("package.json is missing in the study root; prepare it from the CLI")
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Unavailable(f"package.json is unreadable: {type(exc).__name__}") from exc
    if not isinstance(package, dict):
        raise Unavailable("package.json is not an object")
    declared = package.get("package_id", package_id)
    if declared != package_id:
        raise Conflict("package.json does not match the current registered package")
    if package.get("spec_revision") not in (None, study.get("revision")):
        raise Conflict("package.json belongs to a stale study revision")
    lane = str(payload.get("lane") or package.get("lane") or "gpu").lower()
    if lane not in ("cpu", "gpu"):
        raise Unavailable("lane must be cpu or gpu")
    night = f"study-{package_id[:16]}"
    if not NIGHT_ID.match(night):
        raise Unavailable("invalid study night identity")
    nights = Path(runs_root) / "nights"
    nights.mkdir(parents=True, exist_ok=True)
    target = nights / f"{night}.yaml"
    from hornlab_search.studies.production import study_interpreter
    argv = [
        str(study_interpreter(Path(root))), "-m", "hornlab_search.studies.cli", "run",
        "--root", str(Path(service.store.root)), "--package", "package.json",
        "--execute", "--project-root", str(Path(root)),
    ]
    body = {
        "night": night,
        "lane": lane,
        "jobs": [{
            "id": f"study_{package_id[:16]}",
            "kind": "command",
            "timeout_s": 21600,
            "argv": argv,
        }],
    }
    if target.is_file():
        return {
            "status": "ok", "night": night, "path": _relative(root, target),
            "command": f"powershell -NoProfile -ExecutionPolicy Bypass -File tools\\night_queue\\queue.ps1 -Nights {night}",
            "existing": True,
            "note": "Night file already exists; it was not overwritten. Launch it only after the live runner stops.",
        }
    temporary = target.with_suffix(".yaml.tmp")
    temporary.write_text(yaml.safe_dump(body, sort_keys=False, width=4096), encoding="utf-8")
    os.replace(temporary, target)
    return {
        "status": "ok", "night": night, "path": _relative(root, target),
        "command": f"powershell -NoProfile -ExecutionPolicy Bypass -File tools\\night_queue\\queue.ps1 -Nights {night}",
        "existing": False,
        "note": ("Written, not launched. If another runner is live, launch via launch_detached.ps1 "
                 "with -WaitPid <runner pid> -WaitMatch <runner text>."),
    }


__all__ = ["queue_study"]
