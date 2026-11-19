"""Horn + woofer GUI — the fixed-horn **screen** store (P2): read-only, no BL import, no solver.

Reads ``woofer_seed.json`` payloads (schema :data:`hornlab_search.system.woofer_seed.SEED_SCHEMA`)
from an allow-list of roots inside the system store:

* ``<store>/woofer_seed*/woofer_seed.json`` — the parent's recorded seed-screen runs;
* ``<store>/screens/<study>/woofer_seed.json`` — GUI-launched screens (P5 writes here).

Everything returned is the recorded JSON, verbatim: the shortlist, kept rows, metric spec, catalog,
envelope, XO screens and the rejection ledger are echoed, never recomputed.  Two things are
computed in Python and labelled as such:

* ``pareto_ids`` — the non-dominated set of ``kept_rows``, recomputed with
  :func:`hornlab_search.system.score.dominates` and the study's own ``axis_directions`` (the
  cross-check of the recorded ``counts.pareto_front_rows``);
* the front-baffle separation numbers of :func:`panel_fit`, which come from
  :func:`hornlab_search.system.woofer_seed.bl_panel_fit_separation` (the same arithmetic as the
  screen's panel gate).

Honesty rules copied from ``gui/data_hw.py``:

* the study JSON carries **no timestamp**; ``mtime_utc`` is the file's mtime and is labelled as
  such (it is not a study-creation time);
* a file with an invalid ``study_id`` is reported in ``errors`` — never silently skipped;
* a ``woofer_seed.json`` larger than :data:`SCREEN_MAX_BYTES` is refused unread;
* no BL import, no file writes, no solver.

No endpoint here sums channels or ranks designs: a screen is a heuristic screen, not a result.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from hornlab_search.system import contracts as C
from hornlab_search.system import score
from hornlab_search.system import woofer_seed as W

STUDY_FILE = "woofer_seed.json"
#: A study JSON is ~0.25-0.8 MB today; 40 MB is far past any real file and bounds memory.
SCREEN_MAX_BYTES = 40 * 1024 * 1024
_STUDY_ID = re.compile(r"^[0-9a-f]{16}$")
_KEY_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$")
#: Counters the KPI strip reads; a study recorded before a counter existed reports ``None``.
_COUNT_KEYS = (
    "drivers_loaded", "drivers_rejected", "boxes_considered", "boxes_rejected",
    "bl_panel_fit_rejected", "xo_hypotheses", "xo_rejected", "placements_considered",
    "placements_rejected", "candidates_kept", "pareto_front_rows", "shortlist_rows",
)
#: Canonical ledger order for the Rejected tab (unknown stages follow, alphabetically).
_STAGE_ORDER = ("driver_catalog", "driver_geometry", "box_grid", "box_gate", "bl_panel_fit",
                "xo_data", "placement")
_CACHE: dict[tuple, Any] = {}
_CACHE_MAX = 64


# --------------------------------------------------------------------------- paths & cache

def _store_root(store: Path) -> Path:
    return Path(store).resolve()


def _stamp(p: Path) -> tuple:
    st = p.stat()
    return (str(p), st.st_mtime_ns, st.st_size)


def _cached(key: tuple, fn):
    if key in _CACHE:
        return _CACHE[key]
    value = fn()
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = value
    return value


def _inside(base: Path, path: Path) -> bool:
    """Whether the resolved ``path`` is inside the resolved store root."""
    return base in Path(path).resolve().parents


def _rel(base: Path, path: Path) -> str:
    return Path(path).resolve().relative_to(base).as_posix()


def _iso_utc(ns: int) -> str:
    ts = _dt.datetime.fromtimestamp(ns / 1e9, tz=_dt.timezone.utc)
    return ts.isoformat().replace("+00:00", "Z")


def _study_dirs(store: Path) -> list[Path]:
    """Allow-listed study dirs: ``woofer_seed*`` and ``screens/*``, each holding a study file."""
    base = _store_root(store)
    if not base.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(base.glob("woofer_seed*")):
        if p.is_dir() and not p.is_symlink() and _inside(base, p):
            if (p / STUDY_FILE).is_file() and _inside(base, p / STUDY_FILE):
                out.append(p.resolve())
    screens = base / "screens"
    if screens.is_dir() and not screens.is_symlink():
        for p in sorted(screens.iterdir()):
            if (not p.is_dir() or p.is_symlink() or not _KEY_PART.match(p.name)
                    or not _inside(base, p)):
                continue
            if (p / STUDY_FILE).is_file() and _inside(base, p / STUDY_FILE):
                out.append(p.resolve())
    return out


def _study_payload(path: Path) -> dict[str, Any]:
    """The parsed study JSON, refused above :data:`SCREEN_MAX_BYTES` and cached by mtime+size."""
    def read() -> dict[str, Any]:
        st = path.stat()
        if st.st_size > SCREEN_MAX_BYTES:
            raise ValueError(
                f"{path.name} is {st.st_size} bytes > {SCREEN_MAX_BYTES} byte limit; refused unread")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path.name}: top-level JSON must be an object")
        sid = data.get("study_id")
        if not isinstance(sid, str) or not _STUDY_ID.match(sid):
            raise ValueError(f"{path.name}: study_id {sid!r} is not 16 lowercase hex")
        if not isinstance(data.get("schema"), str) or not data["schema"]:
            raise ValueError(f"{path.name}: missing schema")
        return data
    return _cached(("study",) + _stamp(path), read)


def _sha256(path: Path) -> str:
    def read() -> str:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    return _cached(("sha",) + _stamp(path), read)


# --------------------------------------------------------------------------- payload views

def _counts(payload: dict[str, Any]) -> tuple[dict[str, int | None], list[str]]:
    raw = payload.get("counts")
    if not isinstance(raw, dict):
        raw = {}
    counts: dict[str, int | None] = {str(k): v for k, v in raw.items()}
    missing = [k for k in _COUNT_KEYS if k not in raw]
    for k in missing:
        counts[k] = None
    return counts, missing


def _asset(payload: dict[str, Any]) -> dict[str, Any]:
    a = payload.get("asset")
    if not isinstance(a, dict):
        a = {}
    return {k: a.get(k) for k in ("asset_id", "brief_id", "design_hash", "family", "quality",
                                  "freq_lo_hz", "freq_hi_hz", "n_freqs")}


def _horn(payload: dict[str, Any]) -> dict[str, Any]:
    a = payload.get("asset")
    if not isinstance(a, dict):
        a = {}
    return {k: a.get(k) for k in ("brief_id", "design_hash", "family", "quality")}


def _drivers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for entry in payload.get("catalog") or []:
        if isinstance(entry, dict):
            out.append({"driver_id": entry.get("driver_id"), "driver_name": entry.get("name")})
    return out


def _axis_directions(payload: dict[str, Any]) -> dict[str, str]:
    rows = list(payload.get("shortlist") or []) + list(payload.get("kept_rows") or [])
    for row in rows:
        if isinstance(row, dict):
            recorded = row.get("axis_directions")
            if isinstance(recorded, dict) and recorded:
                return {str(k): str(v) for k, v in recorded.items()}
    return dict(W.SEED_AXIS_DIRECTIONS)


def _rejected(payload: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in payload.get("rejected_ledger") or []:
        if isinstance(row, dict):
            groups.setdefault(str(row.get("stage") or "?"), []).append(row)
    order = [s for s in _STAGE_ORDER if s in groups]
    order += sorted(set(groups) - set(_STAGE_ORDER))
    return [{"stage": stage, "count": len(groups[stage]), "rows": groups[stage]}
            for stage in order]


def _pareto_ids(payload: dict[str, Any], directions: dict[str, str]) -> list[str]:
    """The non-dominated ``kept_rows`` set, recomputed in Python from the recorded axes."""
    rows = [r for r in payload.get("kept_rows") or [] if isinstance(r, dict)]
    front: list[str] = []
    for i, row in enumerate(rows):
        dominated = any(score.dominates(other, row, directions)
                        for j, other in enumerate(rows) if j != i)
        if not dominated and row.get("candidate_id") is not None:
            front.append(str(row["candidate_id"]))
    return front


def _replay(base: Path, dirs: list[Path]) -> dict[str, Any]:
    shas = [_sha256(d / STUDY_FILE) for d in dirs]
    return {
        "paths": [_rel(base, d) for d in dirs],
        "count": len(dirs),
        "byte_identical": len(set(shas)) == 1,
        "sha256": shas,
    }


# --------------------------------------------------------------------------- public views

def hw_screens(root: Path, store: Path) -> dict:
    """One row per ``woofer_seed.json`` under the allow-listed roots, replays grouped by id.

    ``root`` is accepted for signature parity with :func:`gui.data_hw.hw_cases`; every path read
    here resolves inside ``store``.  Files that cannot be read or carry an invalid ``study_id``
    appear in ``errors`` (with the store-relative path), never dropped silently.
    """
    base = _store_root(store)
    groups: dict[str, list[Path]] = {}
    errors: list[dict[str, str]] = []
    for d in _study_dirs(store):
        try:
            payload = _study_payload(d / STUDY_FILE)
        except Exception as exc:  # noqa: BLE001 - reported, never hidden
            errors.append({"path": _rel(base, d), "error": f"{type(exc).__name__}: {exc}"})
            continue
        groups.setdefault(str(payload["study_id"]), []).append(d)

    studies = []
    for sid, dirs in groups.items():
        dirs = sorted(dirs)
        replay = _replay(base, dirs)
        payload = _study_payload(dirs[0] / STUDY_FILE)
        counts, counts_missing = _counts(payload)
        drivers = _drivers(payload)
        st = (dirs[0] / STUDY_FILE).stat()
        studies.append({
            "study_id": sid,
            "dir": _rel(base, dirs[0]),
            "paths": replay["paths"],
            "mtime_utc": _iso_utc(st.st_mtime_ns),
            "sha256": replay["sha256"][0],
            "replay_count": replay["count"],
            "byte_identical": replay["byte_identical"],
            "horn": _horn(payload),
            "drivers": drivers,
            "driver_count": len(drivers),
            "counts": counts,
            "counts_missing": counts_missing,
            "claim": payload.get("claim"),
            "schema": payload.get("schema"),
        })
    studies.sort(key=lambda s: (s["mtime_utc"], s["study_id"]), reverse=True)
    return {"store": str(base), "studies": studies, "errors": errors}


def _resolve_study(store: Path, study: str) -> tuple[Path, list[Path], dict[str, Any]]:
    sid = str(study).strip()
    if not _STUDY_ID.match(sid):
        raise ValueError(f"bad study id {study!r}: expected 16 lowercase hex characters")
    base = _store_root(store)
    dirs: list[Path] = []
    payload: dict[str, Any] | None = None
    for d in _study_dirs(store):
        try:
            candidate = _study_payload(d / STUDY_FILE)
        except Exception:  # noqa: BLE001 - an unreadable file cannot claim this id
            continue
        if str(candidate["study_id"]) == sid:
            dirs.append(d)
            payload = payload or candidate
    if not dirs or payload is None:
        raise FileNotFoundError(sid)
    return base, sorted(dirs), payload


def hw_screen(root: Path, store: Path, study: str) -> dict:
    """Detail for one recorded screen: verbatim rows plus the recomputed non-dominated set.

    Refuses an id that is not 16 lowercase hex with :class:`ValueError` and an allow-listed id
    that is not on disk with :class:`FileNotFoundError`; there is no path argument to traverse.
    """
    base, dirs, payload = _resolve_study(store, study)
    counts, counts_missing = _counts(payload)
    directions = _axis_directions(payload)
    replay = _replay(base, dirs)
    st = (dirs[0] / STUDY_FILE).stat()
    return {
        "study_id": str(payload["study_id"]),
        "sha256": replay["sha256"][0],
        "dir": _rel(base, dirs[0]),
        "mtime_utc": _iso_utc(st.st_mtime_ns),
        "schema": payload.get("schema"),
        "claim": payload.get("claim"),
        "counts": counts,
        "counts_missing": counts_missing,
        "asset": _asset(payload),
        "envelope": payload.get("envelope"),
        "metric_spec": payload.get("metric_spec"),
        "catalog": payload.get("catalog"),
        "axis_directions": directions,
        "numeric_axes": list(W.SEED_AXIS_DIRECTIONS),
        "shortlist": payload.get("shortlist") or [],
        "kept_rows": payload.get("kept_rows") or [],
        "pareto_ids": _pareto_ids(payload, directions),
        "rejected": _rejected(payload),
        "xo_screens": payload.get("xo_screens"),
        "replay": {k: replay[k] for k in ("paths", "count", "byte_identical")},
    }


# --------------------------------------------------------------------------- panel fit

#: Payload bounds, all inclusive.  ``width_mm``/``depth_mm`` are optional (the selected row's
#: values); the front-panel default is the recorded 371.2 mm demo cell.
_FIT_BOUNDS: dict[str, tuple[float, float]] = {
    "height_mm": (100.0, 2000.0),
    "port_throat_area_cm2": (5.0, 600.0),
    "net_volume_l": (5.0, 400.0),
    "wall_mm": (6.0, 40.0),
    "driver_moving_diameter_m": (0.100, 0.400),
    "clearance_m": (0.001, 0.020),
    "width_mm": (100.0, 2000.0),
    "depth_mm": (100.0, 2000.0),
}
_FIT_REQUIRED = ("height_mm", "port_throat_area_cm2", "net_volume_l", "wall_mm")
_FIT_DEFAULTS: dict[str, float] = {
    "driver_moving_diameter_m": W.BL_DEMO_DRIVER_MOVING_DIAMETER_M,
    "clearance_m": W.BL_VALIDATE_CLEARANCE_M,
    "width_mm": 371.2,
    "depth_mm": 371.2,
}


def panel_fit(payload: dict) -> dict:
    """The front-baffle panel-fit pre-check for the GUI's Panel fit tab.  Pure; never writes.

    Validates ``height_mm``/``port_throat_area_cm2``/``net_volume_l``/``wall_mm`` (required) plus
    the optional ``driver_moving_diameter_m`` (BL demo default 200 mm), ``clearance_m``,
    ``width_mm`` and ``depth_mm`` (default 371.2 mm, the recorded demo cell's front).  Unknown
    keys, non-numbers and out-of-range values are refused with a message naming the field.

    The payload carries no tuning, so the box point has no ``derived_effective_port_length_m``:
    the front-panel rules (walls, separation, cone) are judged and, when they all pass, the
    verdict is ``BL_PANEL_FIT_PORT_LENGTH_UNAVAILABLE`` rather than an assumed length.  The
    separation numbers are always reported.
    """
    if not isinstance(payload, dict):
        raise ValueError("panel-fit payload must be an object")
    values: dict[str, float] = {}
    for key in payload:
        if key not in _FIT_BOUNDS:
            raise ValueError(f"unknown panel-fit field {key!r}; expected one of "
                             f"{sorted(_FIT_BOUNDS)}")
    for key, (lo, hi) in _FIT_BOUNDS.items():
        if key not in payload:
            if key in _FIT_REQUIRED:
                raise ValueError(f"missing panel-fit field {key!r}")
            values[key] = float(_FIT_DEFAULTS[key])
            continue
        raw = payload[key]
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"{key} must be a number, got {raw!r}")
        value = float(raw)
        if not (lo <= value <= hi):
            raise ValueError(f"{key} must be between {lo:g} and {hi:g}, got {value:g}")
        values[key] = value

    point = C.BoxPoint(
        kind="vented",
        external_width_mm=values["width_mm"],
        external_height_mm=values["height_mm"],
        external_depth_mm=values["depth_mm"],
        net_volume_l=values["net_volume_l"],
        wall_mm=values["wall_mm"],
        port_type="round_flared",
        port_throat_area_cm2=values["port_throat_area_cm2"],
        port_nfr=0.0,                       # the LF-tier straight-port convention
        requested_tuning_hz=0.0,            # no tuning in the payload; never used as a length
        derived_effective_port_length_m=None,
        derived_tuning_hz=None,
        fits={},
    )
    sep = W.bl_panel_fit_separation(
        point, driver_moving_diameter_m=values["driver_moving_diameter_m"],
        clearance_m=values["clearance_m"])
    return {
        "feasible": bool(sep["feasible"]),
        "reason": sep["reason"],
        "required_m": round(float(sep["required_m"]), 6),
        "available_m": round(float(sep["available_m"]), 6),
        "driver_y_m": round(float(sep["driver_y_m"]), 6),
        "port_y_m": round(float(sep["port_y_m"]), 6),
        "port_length_checked": bool(sep["port_length_checked"]),
        "inputs": {k: values[k] for k in _FIT_BOUNDS},
    }
