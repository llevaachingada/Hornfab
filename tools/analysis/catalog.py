"""S0 read-only experiment catalog over ``dataset/`` shards (2026-11-12).

Why a separate reader instead of ``DatasetStore``: opening a ``DatasetStore`` on a live
``dataset/`` root **repairs** it (truncates a torn tail, deletes uncommitted array files,
re-derives index lines).  This tool must never write to a live source, so it streams the
on-disk artifacts itself:

* every ``shard-NNNN.jsonl`` is read as bytes; only newline-terminated lines are records;
* the highest-numbered shard is the *active* shard, and only its committed prefix (complete
  lines before any unterminated tail) is snapshotted; its torn tail is reported, not repaired;
* ``index.jsonl`` rows are counted **separately** from shard records and reconciled against
  them by ``(shard, row)``; disagreement is reported, never fixed;
* every successful record's ``shard-NNNN/rec-RRRR.npz`` is opened read-only to validate
  presence/readability and the required arrays for the record's objective version;
* source hashes cover the committed bytes only, so an active shard's changing tail does not
  make an earlier snapshot ambiguous.

Identities are kept separate (hardening decision section 2):

``geometry_id``
    the recorded source ``design_hash``.  A parameter hash is **not** proof of a unique
    physical surface (ignored fields can change it); use it as the recorded source identity.
``physical_solve_id``
    hash of ``(design_hash, mesh_hash, solve_hash)`` - the cache/solve identity.  Repeated
    rows (cache replays, duplicate runs) do not create new independent solves.
``score_identity``
    hash of the task/target/objective/brief identity plus the terms schema.  The record does
    not store weights/tolerances; that is called out as ``score_parameters_not_stored`` and a
    cohort may attach a resolved score spec (see ``cohorts.py``).
``experiment_id``
    ``run_id`` when recorded.  Older records lack it: absence is reported, never inferred
    from timestamps, config names or design hashes.

The tool exports JSON + CSV + Markdown into a caller-provided ``--out`` folder.  It refuses
an ``--out`` inside an input dataset root.  Arrays are never dumped wholesale; pass
``--array KEY[,KEY...]`` for a bounded per-record summary of selected arrays.

Schema (analysis-only; new names are not production config keys)::

    catalog.json
      tool, schema_version, generated_utc
      roots: [{root, index:{...}, shards:[...], active_shard, ...}]
      counts: {index_rows, shard_records, records, ...}
      coherence: {...}
      records: [record-entry, ...]        # one compact entry per record
      exclusions: [{source, reason, ...}]
      unknowns: {global unknown classes and counts}

Usage::

    .venv\\Scripts\\python.exe tools\\analysis\\catalog.py \\
        --root dataset --root dataset_cpu --out scratch\\bo_m0\\s0\\catalog

Read-only over the sources; the only writes are under ``--out``.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

try:  # reuse the frozen record schema constants; never instantiate DatasetStore
    from hornlab_search.dataset.record import (ARRAY_KEYS as _RECORD_ARRAY_KEYS,
                                               REQUIRED_LIB_SHAS as _RECORD_REQUIRED_LIB_SHAS,
                                               lib_sha_key as _record_lib_sha_key,
                                               validate_record as _validate_record)
except Exception:  # noqa: BLE001 - keep the analysis tool usable without the package
    _validate_record = None  # type: ignore[assignment]
    _RECORD_ARRAY_KEYS = (
        "freqs_hz", "h_angles_deg", "v_angles_deg", "spl_h_db", "spl_v_db",
        "balloon_dirs", "spl_balloon_db", "z_throat", "bw_h_deg", "bw_v_deg", "di_db",
        "ripple_h_db", "ripple_v_db", "on_axis_db", "channel_pressure",
        "channel_sphere_pressure", "impedance_matrix")
    _RECORD_REQUIRED_LIB_SHAS = ("hornlab_mesher", "hornlab_beat_bem",
                                 "hornlab_bempp_bem", "hornlab_plots", "hornlab_search")

    def _record_lib_sha_key(lib_shas: dict) -> str:  # type: ignore[misc]
        return f"{str((lib_shas or {}).get('hornlab_mesher', ''))[:10]}+" \
               f"{str((lib_shas or {}).get('hornlab_beat_bem', ''))[:10]}"

from _common import add_out_arg, fail, jsonable, utc_now

TOOL = "catalog"
SCHEMA_VERSION = 1

#: Successful records only; failures have no solve and no arrays.
_NPZ_KEYS = tuple(_RECORD_ARRAY_KEYS)

#: Parent-frozen completeness rule for a replayable v4 score (2026-11-12): the stored
#: response arrays the v4 objective reads, plus the H/V cuts and on_axis.  The diagonal
#: term is NaN without the balloon; response-detrended ripple needs the cuts.
V4_SCORE_ARRAYS = ("h_angles_deg", "v_angles_deg", "spl_h_db", "spl_v_db",
                   "balloon_dirs", "spl_balloon_db", "on_axis_db")
#: Loading inputs are tracked separately from the v4 score arrays.  ATH's load weight is
#: 0.0, but a missing loading input still marks a row incomplete, never passing.
V4_LOADING_ARRAYS = ("z_throat",)
#: Frequency axis is stored in the record's solve block; the npz copy is useful but the
#: record grid is the authority.  Tracked, not folded into the v4 score-array missingness.
AUX_ARRAYS = ("freqs_hz",)

SCORE_ARRAY_REQUIREMENTS: dict[int, tuple[str, ...]] = {4: V4_SCORE_ARRAYS}
LOADING_ARRAY_REQUIREMENTS: dict[int, tuple[str, ...]] = {4: V4_LOADING_ARRAYS}
#: v5/v6/v7 need at least the v4 response arrays for their pattern terms; their extra
#: system/loading inputs are not silently assumed complete by this first catalog slice.
for _v in (5, 6, 7):
    SCORE_ARRAY_REQUIREMENTS[_v] = V4_SCORE_ARRAYS
    LOADING_ARRAY_REQUIREMENTS[_v] = V4_LOADING_ARRAYS + ("impedance_matrix",)

_SHARD_RE = re.compile(r"^shard-(\d+)\.jsonl$")
_EXTERNAL_LIBS = ("hornlab_mesher", "hornlab_beat_bem", "hornlab_bempp_bem", "hornlab_plots")


# ------------------------------------------------------------------ small helpers


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha16(obj: Any) -> str:
    blob = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _finite(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _num_or_none(x) -> float | None:
    return _finite(x)


def _int_or_none(x) -> int | None:
    if x is None or isinstance(x, bool):
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def _str_or_none(x) -> str | None:
    if isinstance(x, str) and x:
        return x
    return None


def _dict_or_empty(x) -> dict:
    return x if isinstance(x, dict) else {}


def _scan_lines(data: bytes) -> tuple[list[tuple[int, int]], int]:
    """(start, length including newline) of every complete line; length of the tail."""
    offsets: list[tuple[int, int]] = []
    pos = 0
    while True:
        nl = data.find(b"\n", pos)
        if nl < 0:
            break
        offsets.append((pos, nl + 1 - pos))
        pos = nl + 1
    return offsets, len(data) - pos


def _safe_rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def _read_json_bytes(raw: bytes) -> tuple[dict | None, str | None]:
    try:
        obj = json.loads(raw.decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001 - report per-line, never fatal
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(obj, dict):
        return None, "JSON value is not an object"
    return obj, None


# ------------------------------------------------------------------ source scanning


def _shard_files(root: Path) -> list[tuple[int, Path]]:
    out: list[tuple[int, Path]] = []
    try:
        for p in root.iterdir():
            m = _SHARD_RE.match(p.name)
            if m and p.is_file():
                out.append((int(m.group(1)), p))
    except OSError:
        return []
    return sorted(out, key=lambda x: x[0])


def _active_shard_number(root: Path) -> int | None:
    """The store treats the highest-numbered shard as open; same convention here."""
    shards = _shard_files(root)
    return shards[-1][0] if shards else None


def _read_index(root: Path) -> dict:
    path = root / "index.jsonl"
    info: dict[str, Any] = {
        "path": _safe_rel(path, root),
        "exists": path.is_file(),
        "bytes": 0, "committed_bytes": 0, "sha256": None,
        "torn_tail_bytes": 0, "malformed_lines": 0, "blank_lines": 0,
        "rows": 0, "entries": [], "line_errors": [],
    }
    if not path.is_file():
        return info
    try:
        data = path.read_bytes()
    except OSError as exc:
        info["line_errors"].append({"line": None, "error": f"{type(exc).__name__}: {exc}"})
        return info
    offsets, tail = _scan_lines(data)
    committed = len(data) - tail
    info.update({"bytes": len(data), "committed_bytes": committed,
                 "sha256": _sha256_bytes(data[:committed]),
                 "torn_tail_bytes": tail})
    for i, (start, ln) in enumerate(offsets):
        raw = data[start:start + ln]
        if not raw.strip():
            info["blank_lines"] += 1
            continue
        entry, err = _read_json_bytes(raw)
        if err is not None:
            info["malformed_lines"] += 1
            if len(info["line_errors"]) < 100:
                info["line_errors"].append({"line": i + 1, "error": err})
            continue
        assert entry is not None
        entry = dict(entry)
        entry["_line"] = i + 1
        entry["_offset"] = start
        entry["_record_sha256"] = _sha256_bytes(raw.rstrip(b"\r\n"))
        info["entries"].append(entry)
    info["rows"] = len(info["entries"])
    return info


def _read_shard(root: Path, shard: int, path: Path, *, active: bool,
                limit: int | None = None) -> dict:
    info: dict[str, Any] = {
        "shard": shard, "name": path.name,
        "path": _safe_rel(path, root), "active": bool(active),
        "bytes": 0, "committed_bytes": 0, "sha256": None,
        "torn_tail_bytes": 0, "malformed_lines": 0, "blank_lines": 0,
        "records": 0, "truncated": False,
        "records_data": [], "line_errors": [],
    }
    try:
        data = path.read_bytes()
    except OSError as exc:
        info["line_errors"].append({"line": None, "error": f"{type(exc).__name__}: {exc}"})
        return info
    offsets, tail = _scan_lines(data)
    committed = len(data) - tail
    info.update({"bytes": len(data), "committed_bytes": committed,
                 "sha256": _sha256_bytes(data[:committed]),
                 "torn_tail_bytes": tail})
    row = 0
    for i, (start, ln) in enumerate(offsets):
        raw = data[start:start + ln]
        if not raw.strip():
            info["blank_lines"] += 1
            continue
        meta, err = _read_json_bytes(raw)
        if err is not None:
            info["malformed_lines"] += 1
            if len(info["line_errors"]) < 100:
                info["line_errors"].append({"line": i + 1, "row": row, "error": err})
            row += 1
            continue
        if limit is not None and info["records"] >= limit:
            info["truncated"] = True
            break
        info["records_data"].append({
            "meta": meta, "row": row, "line": i + 1, "offset": start,
            "record_sha256": _sha256_bytes(raw.rstrip(b"\r\n")),
        })
        row += 1
        info["records"] += 1
    return info


def _npz_inspect(path: Path, *, selected_keys: Iterable[str] | None = None,
                 deep_keys: Iterable[str] | None = None) -> dict:
    """Read-only NPZ validation.  ``selected_keys`` are summarised, not returned wholesale."""
    out: dict[str, Any] = {"exists": path.is_file(), "path": str(path),
                           "readable": False, "keys": [], "error": None,
                           "selected": {}, "deep": {}}
    if not out["exists"]:
        return out
    try:
        import numpy as np

        with np.load(path, allow_pickle=False) as z:
            keys = list(z.files)
            out["readable"] = True
            out["keys"] = keys
            for key in selected_keys or ():
                if key not in z.files:
                    continue
                arr = np.asarray(z[key])
                finite = None
                if arr.dtype.kind in "fc":
                    finite = int(np.count_nonzero(np.isfinite(arr)))
                out["selected"][key] = {
                    "shape": list(arr.shape), "dtype": str(arr.dtype),
                    "finite_values": finite,
                    "sha256": _sha256_bytes(np.ascontiguousarray(arr).tobytes()),
                }
            for key in deep_keys or ():
                if key not in z.files:
                    continue
                arr = np.asarray(z[key])
                out["deep"][key] = {"shape": list(arr.shape), "dtype": str(arr.dtype)}
    except Exception as exc:  # noqa: BLE001 - a corrupt NPZ is a catalogued artifact
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def _objective_version(meta: dict) -> tuple[int, str]:
    if "objective_version" in meta:
        v = meta.get("objective_version")
        if isinstance(v, int) and not isinstance(v, bool):
            return v, "record"
        try:
            return int(str(v)), "record_coerced"
        except (TypeError, ValueError):
            return 1, "invalid_defaults_to_v1"
    return 1, "absent_defaults_to_v1"


def _lib_shas(meta: dict) -> dict[str, str]:
    raw = _dict_or_empty(meta.get("lib_shas"))
    return {str(k): str(v) for k, v in raw.items() if isinstance(v, (str, int, float))}


def _dependency_hash(shas: dict[str, str]) -> str:
    return _sha16({k: shas.get(k) for k in _EXTERNAL_LIBS})


def _software_hash(shas: dict[str, str]) -> str:
    return _sha16(shas)


def _generator_provenance(meta: dict) -> dict:
    prov = _dict_or_empty(meta.get("provenance"))
    gen = _dict_or_empty(prov.get("generator"))
    params = _dict_or_empty(meta.get("params"))
    grid = _dict_or_empty(params.get("grid"))
    grid_knobs = grid.get("knobs") if isinstance(grid.get("knobs"), dict) else None
    gen_knobs = gen.get("knobs") if isinstance(gen.get("knobs"), dict) else None
    if gen_knobs is not None:
        knobs, source = dict(gen_knobs), "provenance.generator.knobs"
    elif grid_knobs is not None:
        knobs, source = dict(grid_knobs), "params.grid.knobs"
    else:
        knobs, source = None, None
    return {
        "name": _str_or_none(gen.get("name")),
        "spec": gen.get("spec") if isinstance(gen.get("spec"), dict) else None,
        "brief": _str_or_none(gen.get("brief")),
        "brief_hash": _str_or_none(gen.get("brief_hash")),
        "knobs": knobs,
        "knob_source": source,
        "knobs_unknown": knobs is None and bool(gen or grid),
        "derived": gen.get("derived") if isinstance(gen.get("derived"), dict) else None,
    }


def _target_block(meta: dict) -> dict:
    target = _dict_or_empty(meta.get("target"))
    return {
        "coverage_h_deg": _num_or_none(target.get("coverage_h_deg")),
        "coverage_v_deg": _num_or_none(target.get("coverage_v_deg")),
        "coverage_v_up_deg": _num_or_none(target.get("coverage_v_up_deg")),
        "coverage_v_down_deg": _num_or_none(target.get("coverage_v_down_deg")),
        "band_lo_hz": _num_or_none(target.get("band_lo_hz")),
        "band_hi_hz": _num_or_none(target.get("band_hi_hz")),
        "f0_hz": _num_or_none(target.get("f0_hz")),
        "f0_v_hz": _num_or_none(target.get("f0_v_hz")),
        "di_target_db": _num_or_none(target.get("di_target_db")),
        "di_slope_target": _num_or_none(target.get("di_slope_target")),
        "z_min": _num_or_none(target.get("z_min")),
        "driver_exit_radius_mm": _num_or_none(target.get("driver_exit_radius_mm")),
        "freq_weights": target.get("freq_weights"),
        "raw_keys": sorted(str(k) for k in target),
    }


def _target_identity(target: dict) -> dict:
    """Semantic scoring target identity; ``raw_keys`` is provenance, not scoring."""
    return {k: target.get(k) for k in (
        "coverage_h_deg", "coverage_v_deg", "coverage_v_up_deg", "coverage_v_down_deg",
        "band_lo_hz", "band_hi_hz", "f0_hz", "f0_v_hz", "di_target_db",
        "di_slope_target", "z_min", "freq_weights")}


def _mesh_block(meta: dict) -> dict:
    mesh = _dict_or_empty(meta.get("mesh"))
    grid = _dict_or_empty(mesh.get("grid"))
    return {
        "n_triangles": _int_or_none(mesh.get("n_triangles")),
        "n_dof": _int_or_none(mesh.get("n_dof")),
        "quadrants": _str_or_none(mesh.get("quadrants")),
        "res_mm": mesh.get("res_mm") if isinstance(mesh.get("res_mm"), dict) else None,
        "bbox_m": mesh.get("bbox_m") if isinstance(mesh.get("bbox_m"), list) else None,
        "area_m2": _num_or_none(mesh.get("area_m2")),
        "seconds": _num_or_none(mesh.get("seconds")),
        "grid": {
            "angular_segments": _int_or_none(grid.get("angular_segments")),
            "length_segments": _int_or_none(grid.get("length_segments")),
            "available": grid.get("available") if isinstance(grid.get("available"), bool) else None,
        },
    }


def _solve_block(meta: dict) -> dict:
    solve = _dict_or_empty(meta.get("solve"))
    obs = _dict_or_empty(solve.get("observation"))
    freqs = solve.get("freqs_hz")
    freqs = [round(float(f), 6) for f in freqs] if isinstance(freqs, list) else []
    return {
        "backend": _str_or_none(solve.get("backend")),
        "mode": _str_or_none(solve.get("mode")),
        "freqs_hz": freqs,
        "observation": {
            "distance_m": _num_or_none(obs.get("distance_m")),
            "angle_count": _int_or_none(obs.get("angle_count")),
            "balloon": obs.get("balloon") if isinstance(obs.get("balloon"), bool) else None,
            "balloon_points": _int_or_none(obs.get("balloon_points")),
        },
        "gmres_tol": _num_or_none(solve.get("gmres_tol")),
        "seconds": _num_or_none(solve.get("seconds")),
        "peak_vram_mb": _num_or_none(solve.get("peak_vram_mb")),
        "n_dof": _int_or_none(solve.get("n_dof")),
    }


def _terms_identity(meta: dict) -> dict:
    terms = _dict_or_empty(meta.get("terms"))
    metrics = _dict_or_empty(meta.get("metrics_scalars"))
    return {
        "keys": sorted(str(k) for k in terms),
        "penalty": _num_or_none(terms.get("penalty")),
        "total": _num_or_none(terms.get("total")),
        "n_in_band": _int_or_none(terms.get("n_in_band")),
        "n_nan": _int_or_none(terms.get("n_nan")),
        "di_estimated": terms.get("di_estimated"),
        "di_source": _str_or_none(metrics.get("di_source")),
    }


def _grid_hash(solve: dict) -> str:
    return _sha16({"freqs_hz": solve.get("freqs_hz"),
                   "observation": solve.get("observation"),
                   "gmres_tol": solve.get("gmres_tol")})


def _run_id(meta: dict) -> str | None:
    value = meta.get("run_id")
    return str(value) if isinstance(value, str) and value else None


def _config_name(meta: dict) -> str | None:
    value = meta.get("config_name")
    if isinstance(value, str) and value:
        return value
    prov = _dict_or_empty(meta.get("provenance"))
    value = prov.get("config")
    return str(value) if isinstance(value, str) and value else None


def _failure_kind(meta: dict) -> str:
    err = meta.get("error")
    if isinstance(err, str) and err:
        head = err.split(":", 1)[0].strip()
        return head or "unknown"
    return "unknown"


def _gate_failures(meta: dict, terms: dict) -> list[str]:
    out: list[str] = []
    if meta.get("ok") is not True:
        return ["not_ok"]
    if terms.get("penalty") not in (0, 0.0, None):
        out.append("penalty_nonzero")
    if terms.get("penalty") is None:
        out.append("penalty_unknown")
    if terms.get("n_in_band") is None:
        out.append("n_in_band_unknown")
    elif int(terms["n_in_band"]) <= 0:
        out.append("n_in_band_zero")
    if terms.get("di_estimated") is None:
        out.append("di_estimated_unknown")
    elif bool(terms["di_estimated"]):
        out.append("di_estimated_cuts")
    if terms.get("di_source") == "cuts_estimate":
        out.append("di_source_cuts_estimate")
    return out


def _shape_issues(meta: dict, npz: dict) -> list[str]:
    """Basic metadata/NPZ coherence: the stored shapes must agree with the solve grid."""
    solve = _solve_block(meta)
    nf = len(solve.get("freqs_hz") or [])
    na = (solve.get("observation") or {}).get("angle_count")
    deep = npz.get("deep") or {}
    issues: list[str] = []

    def shape(key):
        return tuple(deep.get(key, {}).get("shape") or ())

    if na and "h_angles_deg" in deep and shape("h_angles_deg") != (na,):
        issues.append(f"h_angles_deg {shape('h_angles_deg')} != ({na},)")
    if na and "v_angles_deg" in deep and shape("v_angles_deg") != (na,):
        issues.append(f"v_angles_deg {shape('v_angles_deg')} != ({na},)")
    for key in ("spl_h_db", "spl_v_db"):
        if nf and na and key in deep and shape(key) != (nf, na):
            issues.append(f"{key} {shape(key)} != ({nf}, {na})")
    if nf and "on_axis_db" in deep and shape("on_axis_db") != (nf,):
        issues.append(f"on_axis_db {shape('on_axis_db')} != ({nf},)")
    if "balloon_dirs" in deep:
        s = shape("balloon_dirs")
        if len(s) != 2 or s[1] != 3:
            issues.append(f"balloon_dirs {s} is not (n, 3)")
    if nf and "spl_balloon_db" in deep:
        s = shape("spl_balloon_db")
        if len(s) != 2 or s[0] != nf:
            issues.append(f"spl_balloon_db {s} first axis != {nf}")
    if nf and "z_throat" in deep and shape("z_throat") != (nf,):
        issues.append(f"z_throat {shape('z_throat')} != ({nf},)")
    return issues


def _completeness(meta: dict, npz: dict, *, selected_keys=None) -> dict:
    ov, _ = _objective_version(meta)
    score_req = SCORE_ARRAY_REQUIREMENTS.get(ov)
    load_req = LOADING_ARRAY_REQUIREMENTS.get(ov)
    terms = _terms_identity(meta)
    result: dict[str, Any] = {
        "objective_version": ov,
        "requirements": {"score_arrays": list(score_req or ()),
                         "loading_arrays": list(load_req or ())},
        "npz_exists": bool(npz.get("exists")),
        "npz_readable": bool(npz.get("readable")),
        "npz_error": npz.get("error"),
        "npz_keys": sorted(npz.get("keys") or []),
        "missing_score_arrays": [],
        "missing_loading_arrays": [],
        "missing_aux_arrays": [],
        "shape_issues": [],
        "gate_failures": [],
        "score_complete": None,
        "loading_complete": None,
        "complete_replayable": None,
        "classification": "unknown",
    }
    if meta.get("ok") is not True:
        result.update({"score_complete": False, "loading_complete": False,
                       "complete_replayable": False, "classification": "failed"})
        return result
    if score_req is None:
        result["classification"] = "not_evaluated_for_version"
        return result
    if not npz.get("exists"):
        result.update({"score_complete": False, "loading_complete": False,
                       "complete_replayable": False, "classification": "missing_npz"})
        return result
    if not npz.get("readable"):
        result.update({"score_complete": False, "loading_complete": False,
                       "complete_replayable": False, "classification": "torn_artifact"})
        return result
    keys = set(npz.get("keys") or [])
    missing_score = [k for k in score_req if k not in keys]
    missing_loading = [k for k in (load_req or ()) if k not in keys]
    missing_aux = [k for k in AUX_ARRAYS if k not in keys]
    shape_issues = _shape_issues(meta, npz) if not missing_score and not missing_loading else []
    gates = _gate_failures(meta, terms)
    result.update({"missing_score_arrays": missing_score,
                   "missing_loading_arrays": missing_loading,
                   "missing_aux_arrays": missing_aux,
                   "shape_issues": shape_issues,
                   "gate_failures": gates,
                   "score_complete": not missing_score and not shape_issues,
                   "loading_complete": not missing_loading})
    if missing_score:
        classification = "partial_unsupported"
    elif missing_loading:
        classification = "partial_loading_inputs"
    elif shape_issues:
        classification = "shape_incoherent"
    elif gates:
        classification = "gate_incomplete"
    else:
        classification = "complete"
    result["classification"] = classification
    result["complete_replayable"] = classification == "complete"
    return result


def _record_entry(root: Path, shard_info: dict, item: dict, *,
                  index_entry: dict | None, selected_keys=None,
                  deep_keys=None, include_params: bool = False) -> dict:
    meta = item["meta"]
    shard = shard_info["shard"]
    row = item["row"]
    ov, ov_source = _objective_version(meta)
    required_deep = tuple(SCORE_ARRAY_REQUIREMENTS.get(ov) or ()) + \
        tuple(LOADING_ARRAY_REQUIREMENTS.get(ov) or ())
    deep_for_check = tuple(dict.fromkeys([*(deep_keys or ()), *required_deep]))
    npz_path = root / f"shard-{shard:04d}" / f"rec-{row:04d}.npz"
    npz = _npz_inspect(npz_path, selected_keys=selected_keys, deep_keys=deep_for_check)
    target = _target_block(meta)
    mesh = _mesh_block(meta)
    solve = _solve_block(meta)
    lib_shas = _lib_shas(meta)
    prov = _dict_or_empty(meta.get("provenance"))
    gen = _generator_provenance(meta)
    terms = _terms_identity(meta)
    completeness = _completeness(meta, npz, selected_keys=selected_keys)
    target_hash = _sha16(_target_identity(target))
    source_identity = _sha16({
        "excitation": meta.get("excitation"),
        "driver_exit_radius_mm": target.get("driver_exit_radius_mm"),
        "mounting": prov.get("mounting"),
    })
    score_schema = {"objective_version": ov, "target": target_hash,
                    "brief": prov.get("brief"), "brief_hash": prov.get("brief_hash"),
                    "terms_keys": terms["keys"], "terms_schema": True}
    score_identity = _sha16(score_schema)
    task_identity = _sha16({"family": meta.get("family"), "brief": prov.get("brief"),
                            "brief_hash": prov.get("brief_hash"), "target": target_hash,
                            "objective_version": ov})
    run_id = _run_id(meta)
    config_name = _config_name(meta)
    unknowns: list[str] = []
    if ov_source != "record":
        unknowns.append("objective_version_" + ov_source)
    if not prov:
        unknowns.append("provenance_missing")
    if not prov.get("brief"):
        unknowns.append("brief_missing")
    if not prov.get("brief_hash"):
        unknowns.append("brief_hash_missing")
    if not run_id:
        unknowns.append("run_id_missing")
    if not config_name:
        unknowns.append("config_missing")
    missing_libs = [k for k in _RECORD_REQUIRED_LIB_SHAS if not lib_shas.get(k)]
    if missing_libs:
        unknowns.append("lib_shas_missing")
    if lib_shas.get("hornlab_mesher") == "unknown" or lib_shas.get("hornlab_beat_bem") == "unknown":
        unknowns.append("dependency_sha_unknown")
    if gen["knobs_unknown"]:
        unknowns.append("generator_knobs_missing")
    if mesh["grid"].get("available") is None:
        unknowns.append("mesh_grid_availability_unknown")
    if mesh["n_dof"] is None:
        unknowns.append("mesh_n_dof_missing")
    if solve["mode"] is None:
        unknowns.append("fidelity_missing")
    if solve["backend"] is None:
        unknowns.append("backend_missing")
    if not solve["freqs_hz"]:
        unknowns.append("solve_freq_grid_missing")
    if terms["keys"] == [] and meta.get("ok") is True:
        unknowns.append("terms_missing")
    entry = {
        "source": {
            "root": str(root), "root_name": root.name,
            "shard": shard_info["name"], "shard_index": shard,
            "row": row, "line": item["line"], "offset": item["offset"],
            "npz": _safe_rel(npz_path, root) if npz.get("exists") else None,
            "active_shard": bool(shard_info.get("active")),
        },
        "record_sha256": item.get("record_sha256"),
        "schema_version": meta.get("schema_version"),
        "design_hash": _str_or_none(meta.get("design_hash")),
        "mesh_hash": _str_or_none(meta.get("mesh_hash")),
        "solve_hash": _str_or_none(meta.get("solve_hash")),
        "geometry_id": _str_or_none(meta.get("design_hash")),
        "mesh_spec_id": _str_or_none(meta.get("mesh_hash")),
        "solve_spec_id": _str_or_none(meta.get("solve_hash")),
        "physical_solve_id": _sha16([meta.get("design_hash"), meta.get("mesh_hash"),
                                     meta.get("solve_hash")]),
        "family": _str_or_none(meta.get("family")),
        "ok": meta.get("ok") if isinstance(meta.get("ok"), bool) else None,
        "error": meta.get("error") if isinstance(meta.get("error"), str) else None,
        "failure_kind": _failure_kind(meta) if meta.get("ok") is not True else None,
        "objective": _num_or_none(meta.get("objective")),
        "objective_version": ov,
        "objective_version_source": ov_source,
        "target": target,
        "target_hash": target_hash,
        "terms": terms,
        "mesh": mesh,
        "solve": solve,
        "fidelity": solve.get("mode"),
        "backend": solve.get("backend"),
        "grid_hash": _grid_hash(solve),
        "excitation": meta.get("excitation") if isinstance(meta.get("excitation"), dict) else None,
        "traces": meta.get("traces") if isinstance(meta.get("traces"), dict) else None,
        "lib_shas": lib_shas,
        "dependency_hash": _dependency_hash(lib_shas),
        "software_hash": _software_hash(lib_shas),
        "own_commit": lib_shas.get("hornlab_search"),
        "provenance": {
            "config": prov.get("config"),
            "brief": prov.get("brief"),
            "brief_hash": prov.get("brief_hash"),
            "brief_path": prov.get("brief_path"),
            "mesh_policy": prov.get("mesh_policy"),
            "cad": prov.get("cad"),
            "mounting": prov.get("mounting"),
            "meh": prov.get("meh"),
            "generator": gen,
        },
        "run_id": run_id,
        "experiment_id": run_id,
        "experiment_source": "record.run_id" if run_id else "absent",
        "config_name": config_name,
        "treatment_id": config_name,
        "typology": _str_or_none(meta.get("typology")),
        "task_identity": task_identity,
        "source_identity": source_identity,
        "score_identity": score_identity,
        "score_parameters_known": False,
        "score_parameters_note": "record stores target/version/terms, not weights/tolerances",
        "unknowns": sorted(set(unknowns)),
        "arrays": {
            "exists": npz.get("exists"), "readable": npz.get("readable"),
            "keys": sorted(npz.get("keys") or []),
            "error": npz.get("error"),
            "selected": npz.get("selected") or {},
            "deep": npz.get("deep") or {},
        },
        "completeness": completeness,
        "index_entry": index_entry,
    }
    if include_params:
        entry["params"] = meta.get("params") if isinstance(meta.get("params"), dict) else None
    else:
        params = meta.get("params") if isinstance(meta.get("params"), dict) else {}
        entry["params_keys"] = sorted(str(k) for k in params)
        entry["params_hash"] = _sha16(params)
    return entry


def _index_core(entry: dict | None) -> dict | None:
    if not isinstance(entry, dict):
        return None
    return {k: entry.get(k) for k in ("shard", "row", "design_hash", "ok", "family",
                                      "backend", "mode", "objective", "lib_sha",
                                      "created_utc", "traces")}


def _index_mismatches(meta: dict, index_entry: dict | None) -> list[str]:
    if not isinstance(index_entry, dict):
        return ["record_without_index"]
    out: list[str] = []
    if index_entry.get("design_hash") != meta.get("design_hash"):
        out.append("index_design_hash_mismatch")
    if bool(index_entry.get("ok")) != bool(meta.get("ok")):
        out.append("index_ok_mismatch")
    solve = _dict_or_empty(meta.get("solve"))
    if index_entry.get("backend") != solve.get("backend"):
        out.append("index_backend_mismatch")
    if index_entry.get("mode") != solve.get("mode"):
        out.append("index_mode_mismatch")
    a, b = _num_or_none(index_entry.get("objective")), _num_or_none(meta.get("objective"))
    if a is not None and b is not None and abs(a - b) > 1e-9:
        out.append("index_objective_mismatch")
    expected_lib = _record_lib_sha_key(_dict_or_empty(meta.get("lib_shas")))
    if index_entry.get("lib_sha") and index_entry.get("lib_sha") != expected_lib:
        out.append("index_lib_sha_mismatch")
    return out


# ------------------------------------------------------------------ public API


def scan_root(root: str | Path, *, limit: int | None = None,
              selected_arrays: Iterable[str] | None = None,
              deep_arrays: Iterable[str] | None = None,
              include_params: bool = False,
              validate_npz: bool = True) -> dict:
    """Read one dataset root read-only and return its catalog scan.

    ``limit`` bounds the number of shard records processed (for a bounded pilot); it does
    not alter the source.  ``selected_arrays`` summarises only the named NPZ arrays;
    ``deep_arrays`` additionally checks that those named arrays load.
    """
    root = Path(root)
    active = _active_shard_number(root)
    selected = tuple(selected_arrays or ())
    deep = tuple(deep_arrays or ())
    index = _read_index(root)
    index_by_pos: dict[tuple[int, int], dict] = {}
    for entry in index["entries"]:
        s, r = entry.get("shard"), entry.get("row")
        if isinstance(s, int) and isinstance(r, int):
            index_by_pos[(s, r)] = entry

    shard_infos: list[dict] = []
    records: list[dict] = []
    exclusions: list[dict] = []
    remaining = limit
    truncated = False
    shard_paths = _shard_files(root)
    for shard, path in shard_paths:
        if remaining is not None and remaining <= 0:
            truncated = True
            exclusions.append({"source": {"root": str(root), "shard": path.name,
                                          "row": None, "line": None},
                               "reason": "limit_reached",
                               "detail": {"limit": limit, "records": len(records)}})
            break
        is_active = (shard == active)
        info = _read_shard(root, shard, path, active=is_active, limit=remaining)
        # Drop the bulky record payload from the source summary before export.
        rec_items = info.pop("records_data", [])
        shard_infos.append(info)
        for item in rec_items:
            meta = item["meta"]
            key = (shard, item["row"])
            idx = index_by_pos.get(key)
            mismatches = _index_mismatches(meta, idx)
            metadata_error = None
            if _validate_record is not None:
                try:
                    _validate_record(meta)
                except Exception as exc:  # noqa: BLE001 - record, never fatal
                    metadata_error = f"{type(exc).__name__}: {exc}"
            entry = _record_entry(root, info, item, index_entry=_index_core(idx),
                                  selected_keys=selected, deep_keys=deep,
                                  include_params=include_params)
            entry["index_mismatches"] = mismatches
            entry["metadata_validation_error"] = metadata_error
            entry["metadata_schema_valid"] = metadata_error is None
            if metadata_error:
                entry["excluded"] = "metadata_schema"
                entry["exclusion_reason"] = metadata_error
                exclusions.append({"source": entry["source"], "reason": "metadata_schema",
                                   "detail": metadata_error})
            if mismatches:
                if not entry.get("excluded"):
                    entry["excluded"] = "index_coherence"
                    entry["exclusion_reason"] = ",".join(mismatches)
                exclusions.append({"source": entry["source"], "reason": "index_coherence",
                                   "detail": mismatches})
            records.append(entry)
        if remaining is not None:
            remaining -= info["records"]
        for err in info.get("line_errors") or []:
            exclusions.append({"source": {"root": str(root), "shard": path.name,
                                          "row": err.get("row"), "line": err.get("line")},
                               "reason": "malformed_line", "detail": err.get("error")})
        if info["torn_tail_bytes"]:
            exclusions.append({"source": {"root": str(root), "shard": path.name,
                                          "row": None, "line": None},
                               "reason": "torn_tail_skipped",
                               "detail": {"bytes": info["torn_tail_bytes"],
                                          "active_shard": is_active}})
        if info.get("truncated"):
            truncated = True
            exclusions.append({"source": {"root": str(root), "shard": path.name,
                                          "row": None, "line": None},
                               "reason": "limit_reached",
                               "detail": {"limit": limit, "records": info["records"]}})
            break

    # Index entries with no corresponding committed shard record (writer died after index
    # write, or a record was removed).  Report only; never delete/rewrite.  A bounded scan
    # cannot claim unprocessed index rows are orphans, so it defers that check.
    index_orphans: list[dict] = []
    if not truncated:
        shard_positions = {(r["source"]["shard_index"], r["source"]["row"]) for r in records}
        for key, entry in sorted(index_by_pos.items()):
            if key not in shard_positions:
                index_orphans.append({"_line": entry.get("_line"), "shard": key[0],
                                      "row": key[1], "design_hash": entry.get("design_hash")})
                exclusions.append({"source": {"root": str(root),
                                              "index_line": entry.get("_line"),
                                              "shard_index": key[0], "row": key[1]},
                                   "reason": "index_without_record",
                                   "detail": {"design_hash": entry.get("design_hash")}})

    counts = _count_records(records)
    counts.update({
        "index_rows": index["rows"],
        "index_malformed_lines": index["malformed_lines"],
        "index_torn_tail_bytes": index["torn_tail_bytes"],
        "shard_records": sum(s["records"] for s in shard_infos),
        "shard_malformed_lines": sum(s["malformed_lines"] for s in shard_infos),
        "shard_torn_tail_bytes": sum(s["torn_tail_bytes"] for s in shard_infos),
        "shards": len(shard_infos),
        "index_orphans": len(index_orphans),
        "exclusions": len(exclusions),
        "truncated": truncated,
        "index_orphans_not_evaluated": truncated,
        "record_without_index": sum(
            1 for r in records if "record_without_index" in (r.get("index_mismatches") or [])),
    })
    replay_links = _replay_links(records)
    counts["duplicate_physical_solve_rows"] = replay_links["n_rows_beyond_first_physical_solve"]
    counts["geometries_with_multiple_solves"] = replay_links["n_geometries_with_multiple_solves"]
    coherence = _coherence(index, records, index_by_pos, index_orphans)
    coherence["limited"] = truncated
    if truncated:
        coherence["index_without_record_not_evaluated"] = True
    return {
        "root": str(root),
        "root_name": root.name,
        "active_shard": active,
        "truncated": truncated,
        "replay_links": replay_links,
        "index": {k: v for k, v in index.items() if k not in ("entries",)},
        "index_entries": len(index["entries"]),
        "index_orphans": index_orphans[:100],
        "shards": shard_infos,
        "records": records,
        "exclusions": exclusions,
        "counts": counts,
        "coherence": coherence,
    }


def _replay_links(records: list[dict]) -> dict:
    """Rows that share a physical solve or geometry: cache/replay links stay visible.

    A shared ``physical_solve_id`` is not extra independent evidence; it is the link between
    scored/cached observations.  The list is bounded, the counts are exact.
    """
    by_solve: dict[str, list[dict]] = defaultdict(list)
    by_geom: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("physical_solve_id"):
            by_solve[str(r["physical_solve_id"])].append(r)
        if r.get("geometry_id"):
            by_geom[str(r["geometry_id"])].append(r)
    dup_solves = []
    rows_beyond_first = 0
    for sid, rows in sorted(by_solve.items()):
        if len(rows) <= 1:
            continue
        rows_beyond_first += len(rows) - 1
        if len(dup_solves) < 100:
            dup_solves.append({
                "physical_solve_id": sid,
                "n_records": len(rows),
                "sources": [r.get("source") for r in rows[:20]],
                "run_ids": sorted({r.get("run_id") for r in rows if r.get("run_id")}),
                "score_identities": sorted({r.get("score_identity") for r in rows
                                            if r.get("score_identity")}),
            })
    multi_geom = [{"geometry_id": gid, "n_solves": len({
        r.get("physical_solve_id") for r in rows if r.get("physical_solve_id")})}
        for gid, rows in sorted(by_geom.items())
        if len({r.get("physical_solve_id") for r in rows if r.get("physical_solve_id")}) > 1]
    return {
        "n_physical_solves_with_duplicate_rows": len(dup_solves),
        "n_rows_beyond_first_physical_solve": rows_beyond_first,
        "duplicate_physical_solves": dup_solves,
        "n_geometries_with_multiple_solves": len(multi_geom),
        "geometries_with_multiple_solves": multi_geom[:100],
        "note": "shared physical_solve_id rows are cache/replay links, not independent solves",
    }


def _count_records(records: list[dict]) -> dict:
    ok = [r for r in records if r.get("ok") is True]
    failed = [r for r in records if r.get("ok") is not True]
    complete = [r for r in ok if (r.get("completeness") or {}).get("complete_replayable")]
    missing_score = [r for r in ok if (r.get("completeness") or {}).get("missing_score_arrays")]
    missing_load = [r for r in ok if (r.get("completeness") or {}).get("missing_loading_arrays")]
    torn = [r for r in ok if (r.get("completeness") or {}).get("classification") == "torn_artifact"]
    no_npz = [r for r in ok if (r.get("completeness") or {}).get("classification") == "missing_npz"]
    experiments = {r.get("experiment_id") for r in records if r.get("experiment_id")}
    out = {
        "records": len(records),
        "records_excluded": sum(1 for r in records if r.get("excluded")),
        "records_metadata_invalid": sum(
            1 for r in records if r.get("metadata_schema_valid") is False),
        "records_ok": len(ok),
        "records_failed": len(failed),
        "records_complete_replayable": len(complete),
        "records_missing_score_arrays": len(missing_score),
        "records_missing_loading_arrays": len(missing_load),
        "records_torn_artifact": len(torn),
        "records_missing_npz": len(no_npz),
        "records_shape_incoherent": sum(
            1 for r in ok if (r.get("completeness") or {}).get("classification")
            == "shape_incoherent"),
        "unique_geometries": len({r.get("geometry_id") for r in ok if r.get("geometry_id")}),
        "unique_physical_solves": len({r.get("physical_solve_id") for r in ok
                                       if r.get("physical_solve_id")}),
        "unique_score_identities": len({r.get("score_identity") for r in records
                                        if r.get("score_identity")}),
        "unique_mesh_specs": len({r.get("mesh_spec_id") for r in ok if r.get("mesh_spec_id")}),
        "unique_solve_specs": len({r.get("solve_spec_id") for r in ok if r.get("solve_spec_id")}),
        "unique_experiments_known": len(experiments),
        "records_experiment_unknown": sum(1 for r in records if not r.get("experiment_id")),
        "unique_configs": len({r.get("config_name") for r in records if r.get("config_name")}),
        "records_config_unknown": sum(1 for r in records if not r.get("config_name")),
        "failure_kinds": dict(sorted(Counter(r.get("failure_kind") for r in failed
                                             if r.get("failure_kind")).items())),
        "unknown_field_counts": _unknown_counts(records),
    }
    return out


def _unknown_counts(records: list[dict]) -> dict:
    counts: Counter[str] = Counter()
    for r in records:
        for key in r.get("unknowns") or []:
            counts[str(key)] += 1
    return dict(sorted(counts.items()))


def _coherence(index: dict, records: list[dict], index_by_pos: dict,
               index_orphans: list[dict]) -> dict:
    mismatch_counts: Counter[str] = Counter()
    examples: list[dict] = []
    for r in records:
        for m in r.get("index_mismatches") or []:
            mismatch_counts[m] += 1
            if len(examples) < 100:
                examples.append({"source": r["source"], "issue": m})
    return {
        "index_rows": index["rows"],
        "record_rows": len(records),
        "index_minus_records": index["rows"] - len(records),
        "index_without_record": len(index_orphans),
        "record_without_index": mismatch_counts.get("record_without_index", 0),
        "mismatch_counts": dict(sorted(mismatch_counts.items())),
        "examples": examples,
        "index_torn_tail_bytes": index["torn_tail_bytes"],
    }


def build_catalog(roots: Iterable[str | Path], *, limit: int | None = None,
                  selected_arrays: Iterable[str] | None = None,
                  deep_arrays: Iterable[str] | None = None,
                  include_params: bool = False,
                  validate_npz: bool = True) -> dict:
    """Scan several roots and merge the identity/count summary (records are not deduplicated)."""
    scans = [scan_root(root, limit=limit, selected_arrays=selected_arrays,
                       deep_arrays=deep_arrays, include_params=include_params,
                       validate_npz=validate_npz) for root in roots]
    records = [r for scan in scans for r in scan["records"]]
    exclusions = [e for scan in scans for e in scan["exclusions"]]
    counts = _count_records(records)
    for key in ("index_rows", "index_malformed_lines", "index_torn_tail_bytes",
                "shard_records", "shard_malformed_lines", "shard_torn_tail_bytes",
                "shards", "index_orphans", "exclusions",
                "index_orphans_not_evaluated", "record_without_index",
                "duplicate_physical_solve_rows", "geometries_with_multiple_solves"):
        counts[key] = sum(int(scan["counts"].get(key) or 0) for scan in scans)
    # The merged identity counts above are already global; totals stay explicit.
    counts["roots"] = len(scans)
    counts["truncated"] = any(bool(scan.get("truncated")) for scan in scans)
    duplicate_links = [link for scan in scans
                       for link in (scan.get("replay_links") or {}).get(
                           "duplicate_physical_solves", [])]
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL,
        "sources": scans,
        "records": records,
        "exclusions": exclusions,
        "counts": counts,
        "replay_links": {
            "duplicate_physical_solves": duplicate_links[:100],
            "n_physical_solves_with_duplicate_rows": counts[
                "duplicate_physical_solve_rows"],
            "n_geometries_with_multiple_solves": counts[
                "geometries_with_multiple_solves"],
            "note": "shared physical_solve_id rows are cache/replay links, not independent solves",
        },
        "coherence": {
            "roots": {scan["root"]: scan["coherence"] for scan in scans},
            "index_rows": counts["index_rows"],
            "record_rows": len(records),
            "index_without_record": counts["index_orphans"],
            "record_without_index": sum(
                (scan["coherence"] or {}).get("record_without_index", 0) for scan in scans),
            "note": "index rows are counted separately from committed shard records",
        },
    }


def records_for(catalog: dict, *, ok: bool | None = None, brief: str | None = None,
                brief_hash: str | None = None, family: str | None = None,
                objective_version: int | None = None, fidelity: str | None = None,
                backend: str | None = None, software_hash: str | None = None,
                dependency_hash: str | None = None, config_name: str | None = None,
                require: Iterable[str] = ()) -> list[dict]:
    """Small filter helper shared by CLI/tests/cohorts (does not mutate the catalog)."""
    out: list[dict] = []
    for r in catalog.get("records") or []:
        if ok is not None and bool(r.get("ok")) is not bool(ok):
            continue
        prov = r.get("provenance") or {}
        if brief is not None and prov.get("brief") != brief:
            continue
        if brief_hash is not None and prov.get("brief_hash") != brief_hash:
            continue
        if family is not None and r.get("family") != family:
            continue
        if objective_version is not None and r.get("objective_version") != objective_version:
            continue
        if fidelity is not None and r.get("fidelity") != fidelity:
            continue
        if backend is not None and r.get("backend") != backend:
            continue
        if software_hash is not None and r.get("software_hash") != software_hash:
            continue
        if dependency_hash is not None and r.get("dependency_hash") != dependency_hash:
            continue
        if config_name is not None and r.get("config_name") != config_name:
            continue
        comp = r.get("completeness") or {}
        if any(comp.get(k) is not True for k in require):
            continue
        out.append(r)
    return out


def array_summary(record: dict) -> dict:
    """Selected-array summary only; never returns wholesale arrays."""
    return dict((record.get("arrays") or {}).get("selected") or {})


def source_summary(scan: dict) -> dict:
    """A source summary without its full record list (records are exported separately)."""
    return {k: v for k, v in (scan or {}).items() if k != "records"}


def deterministic_payload(catalog: dict, *, generated_utc: str | None = None,
                          include_records: bool = True) -> dict:
    """The JSON document with stable ordering (records are already in source order)."""
    payload = {
        "tool": TOOL,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": generated_utc or utc_now(),
        "counts": catalog.get("counts") or {},
        "coherence": catalog.get("coherence") or {},
        "sources": [source_summary(scan) for scan in (catalog.get("sources") or [])],
        "replay_links": catalog.get("replay_links") or {},
        "exclusions": catalog.get("exclusions") or [],
        "unknowns": {
            "score_parameters_not_stored": True,
            "note": "weights/tolerances are not in a dataset record; attach a resolved "
                    "score spec in cohorts.py for score-identity comparisons",
            "field_counts": (catalog.get("counts") or {}).get("unknown_field_counts") or {},
        },
        "records_omitted": not include_records,
    }
    if include_records:
        payload["records"] = catalog.get("records") or []
    return jsonable(payload)


def _md(payload: dict) -> str:
    c = payload.get("counts") or {}
    coh = payload.get("coherence") or {}
    lines = ["# Experiment catalog (read-only)", "",
             f"- generated: `{payload.get('generated_utc')}`",
             f"- roots: **{c.get('roots', 0)}**",
             f"- index rows: **{c.get('index_rows', 0)}**; committed shard records: "
             f"**{c.get('shard_records', 0)}**; catalogued records: **{c.get('records', 0)}**",
             f"- ok/failed: **{c.get('records_ok', 0)} / {c.get('records_failed', 0)}**",
             f"- complete replayable (requirements known): "
             f"**{c.get('records_complete_replayable', 0)}**",
             f"- unique geometries / physical solves / score identities / experiments: "
             f"**{c.get('unique_geometries', 0)} / {c.get('unique_physical_solves', 0)} / "
             f"{c.get('unique_score_identities', 0)} / {c.get('unique_experiments_known', 0)}**",
             f"- records without an experiment id: **{c.get('records_experiment_unknown', 0)}**",
             f"- missing score arrays / loading arrays / torn NPZ: "
             f"**{c.get('records_missing_score_arrays', 0)} / "
             f"{c.get('records_missing_loading_arrays', 0)} / "
             f"{c.get('records_torn_artifact', 0)}**",
             f"- index orphans / record-without-index: **{c.get('index_orphans', 0)} / "
             f"{coh.get('record_without_index', 0)}**",
             f"- duplicate rows sharing a physical solve: "
             f"**{c.get('duplicate_physical_solve_rows', 0)}**; geometries with "
             f"multiple solves: **{c.get('geometries_with_multiple_solves', 0)}**"]
    if payload.get("records_omitted"):
        lines.append("- per-record entries omitted from this JSON (`--summary-only`); "
                     "the CSV carries them")
    lines += ["", "## Failure kinds", ""]
    fk = c.get("failure_kinds") or {}
    if fk:
        lines.append("| kind | rows |")
        lines.append("|---|---:|")
        for k, v in fk.items():
            lines.append(f"| `{k}` | {v} |")
    else:
        lines.append("No failed records.")
    unk = (payload.get("unknowns") or {}).get("field_counts") or {}
    lines += ["", "## Unknown provenance counts", ""]
    if unk:
        lines.append("| unknown | records |")
        lines.append("|---|---:|")
        for k, v in unk.items():
            lines.append(f"| `{k}` | {v} |")
    else:
        lines.append("No record-level unknowns.")
    lines += ["", "## Sources", ""]
    for src in payload.get("sources") or []:
        idx = src.get("index") or {}
        lines.append(f"### `{src.get('root')}`")
        lines.append(f"- active shard: {src.get('active_shard')}; shards: "
                     f"{len(src.get('shards') or [])}; index rows: {idx.get('rows')}")
        lines.append(f"- index sha256: `{idx.get('sha256')}`; torn tail: "
                     f"{idx.get('torn_tail_bytes')} bytes")
        for sh in src.get("shards") or []:
            lines.append(f"- `{sh.get('name')}`: {sh.get('records')} records, "
                         f"{sh.get('malformed_lines')} malformed, "
                         f"{sh.get('torn_tail_bytes')} torn tail bytes"
                         + (" (active)" if sh.get("active") else ""))
    lines.append("")
    return "\n".join(lines)


def _csv_rows(payload: dict) -> tuple[list[str], list[dict]]:
    fields = [
        "root", "shard", "shard_index", "row", "line", "record_sha256",
        "design_hash", "mesh_hash", "solve_hash", "geometry_id", "physical_solve_id",
        "family", "ok", "failure_kind", "objective", "objective_version",
        "brief", "brief_hash", "config_name", "run_id", "experiment_id",
        "fidelity", "backend", "grid_hash", "mesh_spec_id", "solve_spec_id",
        "dependency_hash", "software_hash", "own_commit",
        "task_identity", "score_identity", "score_parameters_known",
        "completeness", "missing_score_arrays", "missing_loading_arrays",
        "gate_failures", "npz_readable", "unknowns", "index_mismatches",
    ]
    rows: list[dict] = []
    for r in payload.get("records") or []:
        src = r.get("source") or {}
        prov = r.get("provenance") or {}
        comp = r.get("completeness") or {}
        row = {
            "root": src.get("root"), "shard": src.get("shard"),
            "shard_index": src.get("shard_index"), "row": src.get("row"),
            "line": src.get("line"), "record_sha256": r.get("record_sha256"),
            "design_hash": r.get("design_hash"), "mesh_hash": r.get("mesh_hash"),
            "solve_hash": r.get("solve_hash"), "geometry_id": r.get("geometry_id"),
            "physical_solve_id": r.get("physical_solve_id"),
            "family": r.get("family"), "ok": r.get("ok"),
            "failure_kind": r.get("failure_kind"), "objective": r.get("objective"),
            "objective_version": r.get("objective_version"),
            "brief": prov.get("brief"), "brief_hash": prov.get("brief_hash"),
            "config_name": r.get("config_name"), "run_id": r.get("run_id"),
            "experiment_id": r.get("experiment_id"),
            "fidelity": r.get("fidelity"), "backend": r.get("backend"),
            "grid_hash": r.get("grid_hash"), "mesh_spec_id": r.get("mesh_spec_id"),
            "solve_spec_id": r.get("solve_spec_id"),
            "dependency_hash": r.get("dependency_hash"),
            "software_hash": r.get("software_hash"), "own_commit": r.get("own_commit"),
            "task_identity": r.get("task_identity"),
            "score_identity": r.get("score_identity"),
            "score_parameters_known": r.get("score_parameters_known"),
            "completeness": comp.get("classification"),
            "missing_score_arrays": ",".join(comp.get("missing_score_arrays") or []),
            "missing_loading_arrays": ",".join(comp.get("missing_loading_arrays") or []),
            "gate_failures": ",".join(comp.get("gate_failures") or []),
            "npz_readable": (r.get("arrays") or {}).get("readable"),
            "unknowns": ",".join(r.get("unknowns") or []),
            "index_mismatches": ",".join(r.get("index_mismatches") or []),
        }
        rows.append(row)
    return fields, rows


def write_catalog(catalog: dict, out_dir: str | Path, *,
                  generated_utc: str | None = None, csv_export: bool = True,
                  include_records: bool = True) -> dict:
    """Write deterministic JSON/MD (+ CSV) under ``out_dir``; returns written paths.

    ``include_records=False`` keeps the JSON summary compact (counts/coherence/sources/
    exclusions) while the CSV still carries the per-record table.
    """
    out = Path(out_dir)
    roots = [scan.get("root") for scan in catalog.get("sources") or []]
    if not roots and catalog.get("root"):
        roots = [catalog["root"]]
    if any(root and _is_inside(out, Path(root)) for root in roots):
        raise ValueError(f"refusing to write inside an input dataset root: {out}")
    payload = deterministic_payload(catalog, generated_utc=generated_utc,
                                    include_records=include_records)
    out.mkdir(parents=True, exist_ok=True)
    jpath = out / "catalog.json"
    jpath.write_text(json.dumps(payload, indent=1, sort_keys=True, allow_nan=False,
                                ensure_ascii=False) + "\n", encoding="utf-8")
    mpath = out / "catalog.md"
    mpath.write_text(_md(payload), encoding="utf-8")
    written = {"json": str(jpath), "md": str(mpath)}
    if csv_export:
        fields, rows = _csv_rows({**payload, "records": catalog.get("records") or []})
        cpath = out / "catalog.csv"
        with cpath.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for row in sorted(rows, key=lambda x: (str(x["root"]), str(x["shard_index"]),
                                                   int(x["row"] if x["row"] is not None else -1))):
                writer.writerow(row)
        written["csv"] = str(cpath)
    return written


# ------------------------------------------------------------------ CLI


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="catalog.py",
        description="Read-only experiment catalog over dataset shards (no Store, no writes "
                    "to sources).",
    )
    ap.add_argument("--root", action="append", required=True,
                    help="dataset root holding shard-*.jsonl (repeat for dataset_cpu, ...)")
    add_out_arg(ap)
    ap.add_argument("--limit", type=int, default=None,
                    help="max shard records processed per root (bounded pilot)")
    ap.add_argument("--array", action="append", default=None,
                    help="NPZ array key to summarise (repeatable; default: none)")
    ap.add_argument("--deep-array", action="append", default=None,
                    help="NPZ array key to load for a shape/readability check (repeatable)")
    ap.add_argument("--include-params", action="store_true",
                    help="include the full recorded design params per row (larger JSON)")
    ap.add_argument("--summary-only", action="store_true",
                    help="omit per-record entries from catalog.json (CSV still has them)")
    ap.add_argument("--no-csv", action="store_true", help="skip the deterministic CSV export")
    args = ap.parse_args(argv)
    selected = [k for raw in (args.array or []) for k in raw.split(",") if k]
    deep = [k for raw in (args.deep_array or []) for k in raw.split(",") if k]
    try:
        catalog = build_catalog(args.root, limit=args.limit,
                                selected_arrays=selected, deep_arrays=deep,
                                include_params=args.include_params)
        written = write_catalog(catalog, args.out, csv_export=not args.no_csv,
                                include_records=not args.summary_only)
    except (OSError, ValueError) as exc:
        raise fail(str(exc))
    c = catalog["counts"]
    print(f"catalog OK: roots={c['roots']} index_rows={c['index_rows']} "
          f"records={c['records']} ok={c['records_ok']} failed={c['records_failed']} "
          f"complete={c['records_complete_replayable']} "
          f"solves={c['unique_physical_solves']} geoms={c['unique_geometries']}")
    print(f"  json={written['json']}")
    if "csv" in written:
        print(f"  csv={written['csv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
