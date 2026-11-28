"""Source pinning and value cells for the M1 research snapshot.

Every number in a snapshot is a *cell*: ``{"v": value, "src": "<source path>#<pointer>"}`` for a
persisted value, or ``{"v": value, "calc": name, "calc_version": GENERATOR, "inputs": [...]}`` for
a deterministic calculation over other cells. ``Registry`` reads each source once, records its
sha256 and origin, and hands out the bytes. Committed sources are read from a pinned git commit
(``git show <sha>:<path>``) so a dirty working tree cannot leak in; untracked ``runs/`` sources are
read from disk and pinned by the sha256 of the bytes actually used (for append-only logs, only the
lines at or before the cutoff, so a night appending after the cutoff does not change the input).

Read-only: nothing here writes outside the caller's output directory, imports a solver, or
touches the GPU.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

#: Bumped whenever a calculation or the snapshot shape changes (part of the snapshot id).
GENERATOR = "research-snapshot-m1/4"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_utc(text: str | None) -> datetime | None:
    """ISO-8601 (``Z`` or offset) or a run-dir prefix ``YYYYMMDDTHHMMSSZ`` -> aware UTC datetime."""
    if not isinstance(text, str) or not text:
        return None
    t = text.strip()
    try:
        if len(t) >= 16 and t[8] == "T" and t[15] == "Z" and t[:8].isdigit():
            return datetime.strptime(t[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def iso(dt: datetime | None) -> str | None:
    return None if dt is None else dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_CRLF, _LF = bytes((13, 10)), bytes((10,))


def _lf(data: bytes) -> bytes:
    """Normalise CRLF to LF (git autocrlf checkouts differ from the blob only in line endings)."""
    return data.replace(_CRLF, _LF)


def finite(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    f = float(v)
    return f if math.isfinite(f) else None


def cell(value: Any, src: str, pointer: str) -> dict:
    """A persisted value. Non-finite numbers become ``None`` with ``status: unknown``."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"v": None, "src": f"{src}#{pointer}", "status": "unknown", "raw": repr(value)}
    return {"v": value, "src": f"{src}#{pointer}"}


def missing(reason: str, src: str | None = None) -> dict:
    out = {"v": None, "status": "missing", "reason": reason}
    if src:
        out["src"] = src
    return out


def calc(value: Any, name: str, inputs: Iterable[dict | str]) -> dict:
    refs = []
    for i in inputs:
        if isinstance(i, dict):
            refs.append(i.get("src") or i.get("calc"))
        else:
            refs.append(i)
    return {"v": value, "calc": name, "calc_version": GENERATOR, "inputs": refs}


def json_pointer(*parts: Any) -> str:
    return "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in parts)


class Registry:
    """Reads and pins every input of one snapshot."""

    def __init__(self, root: Path, commit: str):
        self.root = Path(root)
        self.commit = commit
        self.sources: dict[str, dict] = {}
        self.exclusions: list[dict] = []

    # -------------------------------------------------------------- committed (git-pinned)
    def git_bytes(self, rel: str) -> bytes | None:
        rel = rel.replace("\\", "/")
        r = subprocess.run(["git", "show", f"{self.commit}:{rel}"], cwd=self.root,
                           capture_output=True)
        if r.returncode != 0:
            self.sources[rel] = {"path": rel, "origin": f"git:{self.commit}", "status": "missing"}
            return None
        data = r.stdout
        disk = self.root / rel
        entry = {"path": rel, "origin": f"git:{self.commit}", "sha256": sha256(data),
                 "bytes": len(data)}
        if disk.is_file():
            wt = disk.read_bytes()
            if sha256(wt) != entry["sha256"]:
                same_text = _lf(wt) == _lf(data)
                entry["worktree"] = "eol_only" if same_text else "differs"
            else:
                entry["worktree"] = "identical"
        self.sources[rel] = entry
        return data

    def git_json(self, rel: str) -> Any:
        data = self.git_bytes(rel)
        return None if data is None else json.loads(data.decode("utf-8"))

    def git_text(self, rel: str) -> str | None:
        data = self.git_bytes(rel)
        return None if data is None else data.decode("utf-8-sig")

    # -------------------------------------------------------------- untracked (disk-pinned)
    def rel(self, path: Path) -> str:
        try:
            return Path(path).resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return Path(path).as_posix()

    def disk_bytes(self, path: Path) -> bytes | None:
        rel = self.rel(path)
        p = Path(path)
        if not p.is_file():
            self.sources[rel] = {"path": rel, "origin": "disk", "status": "missing"}
            return None
        data = p.read_bytes()
        self.sources[rel] = {"path": rel, "origin": "disk", "sha256": sha256(data),
                             "bytes": len(data)}
        return data

    def disk_json(self, path: Path) -> Any:
        data = self.disk_bytes(path)
        if data is None:
            return None
        try:
            return json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self.sources[self.rel(path)]["status"] = "unreadable"
            return None

    def disk_ndjson(self, path: Path, keep: Callable[[dict], bool]) -> list[tuple[int, dict]]:
        """(1-based line, row) for rows ``keep`` accepts; pins the kept lines' bytes only."""
        rel = self.rel(path)
        p = Path(path)
        if not p.is_file():
            self.sources[rel] = {"path": rel, "origin": "disk", "status": "missing"}
            return []
        raw = p.read_bytes()
        kept_bytes = bytearray()
        rows, n_total, n_bad, n_after = [], 0, 0, 0
        for i, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            n_total += 1
            try:
                row = json.loads(line.decode("utf-8", errors="replace"))
            except ValueError:
                n_bad += 1
                continue
            if not isinstance(row, dict):
                n_bad += 1
                continue
            if not keep(row):
                n_after += 1
                continue
            rows.append((i, row))
            kept_bytes += line + b"\n"
        self.sources[rel] = {"path": rel, "origin": "disk", "sha256_included": sha256(bytes(kept_bytes)),
                             "lines_total": n_total, "lines_included": len(rows),
                             "lines_after_cutoff": n_after, "lines_unparseable": n_bad}
        return rows

    def exclude(self, what: str, reason: str, when: str | None = None) -> None:
        self.exclusions.append({"what": what, "reason": reason, "time": when})
