"""Finding state store (WP3.4) — dismiss / acknowledge / reopen a finding, GUI-written only.

The only state the Overview writes lives in ``<runs>/overview/finding_state.json`` (owner decision
O4), never inside a run folder::

    {"<finding_id>": {"status": "dismissed" | "acknowledged" | "open",
                      "note": "..." | null, "by": "gui", "at_utc": "2026-11-19T12:00:00Z"}}

Writes are atomic (``tmp`` + ``os.replace``): a crash never leaves a half-written file, and a
successful write leaves no ``.tmp`` behind. The ``overview`` directory is created lazily on the
first write, never at import.

:func:`merge_state` is the documented merge for the findings engine. The stored state wins over a
computed ``open`` or ``superseded`` finding, but NEVER over a computed ``resolved`` one: once the
evidence says a finding is resolved, a stale dismiss cannot un-resolve it.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STATUSES = ("dismissed", "acknowledged", "open")
_ID_RE = re.compile(r"^[0-9a-f]{16}$")

_FILE = "finding_state.json"
_DIR = "overview"


# --------------------------------------------------------------------------- paths

def state_path(runs: Path) -> Path:
    """``<runs>/overview/finding_state.json`` (the directory is NOT created here)."""
    return Path(runs) / _DIR / _FILE


# --------------------------------------------------------------------------- read / write

def load_state(runs: Path) -> dict:
    """The stored state, or ``{}`` for a missing / corrupt / wrong-shaped file (never raises)."""
    path = state_path(runs)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): v for k, v in data.items() if isinstance(v, dict)}


def set_status(runs: Path, finding_id: str, status: str, note: str | None = None,
               by: str = "gui") -> dict:
    """Record one finding's status and return the new whole state (atomic write).

    ``status`` must be one of :data:`STATUSES`; ``finding_id`` must be a 16-hex string. Both are
    validated before anything is written, so a bad request cannot leave a partial state file.
    """
    if status not in STATUSES:
        raise ValueError(f"bad status {status!r}: expected one of {', '.join(STATUSES)}")
    if not isinstance(finding_id, str) or not _ID_RE.match(finding_id):
        raise ValueError(f"bad finding id {finding_id!r}: expected 16 hex characters")

    state = load_state(runs)
    state[finding_id] = {
        "status": status,
        "note": note,
        "by": str(by),
        "at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    _write_atomic(state_path(runs), state)
    return state


def _write_atomic(path: Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".finding_state.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# --------------------------------------------------------------------------- merge

def merge_state(findings_list: list[dict], state: dict) -> list[dict]:
    """Merge the stored state into a computed findings list (returns a new list of copies).

    Rule: the stored status wins over a computed ``open`` or ``superseded``, but a computed
    ``resolved`` finding stays ``resolved`` regardless of the stored status. An unknown stored
    status is ignored, never guessed. ``{}`` returns the input list unchanged.
    """
    if not state:
        return findings_list
    out: list[dict] = []
    for finding in findings_list:
        merged = dict(finding)
        entry = state.get(merged.get("id"))
        if isinstance(entry, dict) and merged.get("status") != "resolved":
            status = entry.get("status")
            if status in STATUSES:
                merged["status"] = status
                merged["state_note"] = entry.get("note")
                merged["state_by"] = entry.get("by")
                merged["state_at_utc"] = entry.get("at_utc")
        out.append(merged)
    return out
