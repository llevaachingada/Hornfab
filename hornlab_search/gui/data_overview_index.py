"""Overview phase 2 (WP2.3): persisted index cache behind the live run scan.

The Overview rollup calls :func:`hornlab_search.gui.data_overview.run_records`, which reads every
recent run's ``search.ndjson`` on a cold start (~13 s for a 14-day window). This module keeps the
same output but serves unchanged runs from a GUI-owned JSON index so a cold server start only reads
the runs that actually changed.

Read-only contract (plan section 1):

* run folders are only ever read;
* the single file this module writes is ``<runs>/overview/index.json`` (its ``overview/`` directory
  is created lazily, never at import), atomically via a ``.tmp`` sibling + :func:`os.replace`;
* no GPU, no network, stdlib only. Values are made JSON-safe with :func:`data.clean`.

The index maps run id to ``{"ndjson": [mtime_ns, size] | null,
"run_json": [mtime_ns, size] | null, "summary": <D.run_summary output>}``. A run whose ndjson or
run.json stamp changed is re-read; a run whose stamps are unchanged is served from the cache without
any :func:`data.read_ndjson` call. A schema mismatch, corrupt JSON or ``OSError`` silently rebuilds
the whole index; no exception escapes :func:`cached_records`.
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from . import data as D

SCHEMA = "overview_index_v1"
#: Relative to the runs root: ``runs/overview/index.json``.
INDEX_REL = Path("overview") / "index.json"

#: ``str(index path) -> {"stamp": [mtime_ns, size] | None, "runs": {...}}``. The on-disk index is
#: the durable cache; this in-memory layer avoids re-parsing it on every request. The stamp lets an
#: externally rewritten/corrupted file trigger a reload.
_CACHE: dict[str, dict] = {}
_LOCK = threading.RLock()


# ---------------------------------------------------------------------------- helpers

def _parse_utc(s: str | None) -> datetime | None:
    """Same parse as ``data_overview._parse_utc`` so the time filter matches exactly."""
    if not s:
        return None
    try:
        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _stat_pair(p: Path) -> list[int] | None:
    try:
        st = p.stat()
    except OSError:
        return None
    return [int(st.st_mtime_ns), int(st.st_size)]


def _index_stamp(path: Path) -> list[int] | None:
    return _stat_pair(path)


def _stamp(value) -> list[int] | None:
    """Normalise a stored stamp (``[mtime_ns, size]`` or null) from JSON."""
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            return [int(value[0]), int(value[1])]
        except (TypeError, ValueError):
            return None
    return None


def _load_index(path: Path) -> dict[str, dict] | None:
    """The stored run mapping, or ``None`` when the file is absent/corrupt/another schema."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        return None
    runs = raw.get("runs")
    if not isinstance(runs, dict):
        return None
    out: dict[str, dict] = {}
    for rid, ent in runs.items():
        if not isinstance(ent, dict):
            continue
        summary = ent.get("summary")
        if not isinstance(summary, dict):
            continue
        out[str(rid)] = {"ndjson": _stamp(ent.get("ndjson")),
                         "run_json": _stamp(ent.get("run_json")), "summary": summary}
    return out


def _cache_for(path: Path) -> dict:
    """The in-memory index for ``path``, reloaded when the file's stamp changed or after reset."""
    key = str(path.resolve())
    stamp = _index_stamp(path)
    hit = _CACHE.get(key)
    if hit is not None and hit.get("stamp") == stamp:
        return hit
    runs = _load_index(path)
    if runs is None:                       # absent, corrupt or wrong schema -> rebuild in memory
        runs = {}
    hit = {"stamp": stamp, "runs": runs}
    _CACHE[key] = hit
    return hit


def _write_index(path: Path, runs: dict[str, dict]) -> list[int] | None:
    """Atomic best-effort write; never raises. Returns the new on-disk stamp."""
    payload = {"schema": SCHEMA,
               "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "runs": runs}
    tmp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(D.clean(payload), ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    except (OSError, TypeError, ValueError):
        try:
            tmp.unlink()
        except OSError:
            pass
        return _index_stamp(path)
    return _index_stamp(path)


def reset_cache() -> None:
    """Drop the in-memory index (tests use this to simulate a fresh process; the disk index stays)."""
    with _LOCK:
        _CACHE.clear()


# ---------------------------------------------------------------------------- public API

def cached_records(runs: Path, since: datetime) -> list[dict]:
    """Exactly :func:`data_overview.run_records` -- same rows, same order -- with a disk index.

    The ndjson mtime pre-filter (3600 s slack), the ``last >= since`` filter and the ``_run_dirs``
    (newest-name-first) order are copied from ``run_records``. Unchanged runs are served from the
    index; only runs whose ndjson or run.json stamp changed are re-read.
    """
    runs = Path(runs)
    if not runs.is_dir():
        return []
    dirs = D._run_dirs(runs)
    if not dirs:
        return []

    idx_path = runs / INDEX_REL
    cutoff = since.timestamp() - 3600
    now = time.time()
    out: list[dict] = []
    with _LOCK:
        cache = _cache_for(idx_path)
        index = cache["runs"]
        changed = False
        for d in dirs:
            nd = _stat_pair(d / "search.ndjson")
            if nd is None or (nd[0] / 1_000_000_000.0) < cutoff:
                continue                       # same cheap pre-filter as run_records
            rj = _stat_pair(d / "run.json")
            ent = index.get(d.name)
            if ent is not None and ent.get("ndjson") == nd and ent.get("run_json") == rj:
                summary = dict(ent.get("summary") or {})
                # ``active`` depends on wall-clock time, so refresh it from the cached stamp exactly
                # as D.run_summary's cache-hit path does -- no ndjson read.
                summary["active"] = bool(nd is not None and (now - nd[0] / 1_000_000_000.0) < 120.0)
            else:
                try:
                    summary = D.run_summary(d)
                except Exception:              # noqa: BLE001 - one unreadable run never hides the rest
                    continue
                index[d.name] = {"ndjson": nd, "run_json": rj,
                                 "summary": D.clean(dict(summary))}
                changed = True
                summary = dict(summary)
            last = _parse_utc(summary.get("last"))
            if last is None or last < since:
                continue
            out.append(summary)
        if changed:
            cache["stamp"] = _write_index(idx_path, index)
    return out
