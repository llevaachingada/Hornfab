"""Export the best GPU-solved horn designs per typology and score set.

The search tree keeps every evaluated design in ``<run>/search.ndjson`` and the full acoustic
response in ``<run>/designs/<design_hash>/response.npz``.  Those live under the git-ignored
``runs/`` tree, so a cloud agent cannot see them.  This tool writes a self-describing,
regenerable export under ``--out`` (default ``docs/top_designs``):

* ``top_designs.csv``    - one flat row per selected design: typology, score set, J, dimensions,
                           every scalar parameter, every objective term, metric scalars, and the
                           acoustic-array key.
* ``top_designs.json``   - the full manifest: grouping rules, group census, shared run/score
                           config blocks, every selected design with nested params/terms,
                           per-frequency metric arrays, dimensions and provenance.
* ``top_designs_acoustics.npz`` - the full stored acoustic magnitude response per selected design
                           (H/V cuts, balloon SPL + directions, throat impedance), float32 where
                           safe, keyed ``<acoustics_id>__<array>``.

Ranking is **ascending objective** (lower J is better; the repo minimises J).  The default score
set is the objective version (``v4``, ``v7``, ``v10``, ...), matching the repo rule "never rank J
across versions".  ``--group-by score-config`` additionally splits on the resolved objective
block + target + weights, for strict same-brief comparisons.  Rows with no recorded objective
version are kept as ``unversioned`` unless ``--exclude-unversioned`` is given.

Only provable GPU solves are included: a row is accepted when its own ``backend`` is
``beat_cuda`` or its ``lane`` is ``gpu``, falling back to the owning run's ``backend``/``lane``
for older rows that predate per-row provenance.  CPU rows are excluded.  Duplicate occurrences of
the same physical solve (``design_hash|mesh_hash|solve_hash``) inside one score set are collapsed
to the best (lowest) J; the same physical solve may appear once per score set because a stored
solve can be re-scored under another objective version.

Read-only over ``runs/``; the only writes are under ``--out``.  Archived copies under
``runs/analysis`` (and ``_inputs`` / ``_backup*`` trees) are skipped so the same row is not
counted twice.  Arrays are never dumped wholesale for all rows: the first pass keeps compact
line references, and only the selected top-N rows are re-read and have their responses loaded.

Usage (from the repository root)::

    .venv\\Scripts\\python.exe tools\\data\\top_designs.py
    .venv\\Scripts\\python.exe tools\\data\\top_designs.py --top 10 --out docs/top_designs
    .venv\\Scripts\\python.exe tools\\data\\top_designs.py --group-by score-config --exclude-unversioned
    .venv\\Scripts\\python.exe tools\\data\\top_designs.py --no-acoustics   # fast manifest only
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hornlab_search.dataset.record import typology_name  # noqa: E402

TOOL = "top_designs"
SCHEMA_VERSION = 1
DEFAULT_TOP = 10

#: Archive/provenance subtrees that must not be counted as independent runs.
SKIP_DIR_PARTS = frozenset({"analysis", "_inputs", ".gui_cache", "__pycache__"})
SKIP_DIR_PREFIXES = ("_backup",)

#: Stored response arrays copied to the bundle.  Raw complex pressure arrays (``p_h``,
#: ``p_v``, ``p_balloon``) are intentionally not copied: the SPL magnitude cuts + full balloon
#: SPL + throat impedance are the analysable acoustic response and keep the committed bundle
#: reviewable.  The local ``response.npz`` remains the provenance source for phase.
ACOUSTIC_ARRAYS = (
    "freqs_hz",
    "h_angles_deg",
    "v_angles_deg",
    "spl_h_db",
    "spl_v_db",
    "balloon_dirs",
    "spl_balloon_db",
    "z_throat",
)

#: Metric arrays kept inline in the JSON manifest (small; one vector per frequency).
METRIC_ARRAY_KEYS = (
    "freqs_hz",
    "bw_h_deg",
    "bw_v_deg",
    "di_db",
    "ripple_h_db",
    "ripple_v_db",
    "on_axis_db",
    "z_throat_real",
)

#: Scalar parameter names that are duplicated into the CSV with this prefix.
PARAM_PREFIX = "param_"
TERM_PREFIX = "term_"
METRIC_PREFIX = "metric_"

BASE_CSV_FIELDS = (
    "row_id",
    "group_id",
    "rank",
    "typology",
    "typology_label",
    "score_set",
    "objective_version",
    "version_source",
    "objective",
    "n_scored_in_group",
    "design_hash",
    "mesh_hash",
    "solve_hash",
    "design_id",
    "family",
    "mode",
    "run_rel",
    "run_id",
    "config_name",
    "config_sha",
    "config_path",
    "brief_file",
    "score_config_sha",
    "objective_config_sha",
    "target_sha",
    "created_utc",
    "cached",
    "backend",
    "lane",
    "n_dof",
    "n_triangles",
    "quadrants",
    "symmetry_plane",
    "res_throat_mm",
    "res_mouth_mm",
    "res_rear_mm",
    "peak_vram_mb",
    "solve_seconds",
    "total_seconds",
    "bbox_x_mm",
    "bbox_y_mm",
    "bbox_z_mm",
    "mouth_width_mm_est",
    "mouth_height_mm_est",
    "depth_mm_est",
    "area_m2_quadrant",
    "area_m2_full_est",
    "acoustics_id",
    "acoustics_file",
    "acoustics_arrays",
)


# --------------------------------------------------------------------------- small helpers


def _finite(value: object) -> float | None:
    """A finite float or ``None`` (bools are not numbers)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _sha16(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _clean(value: Any) -> Any:
    """JSON-safe recursively; non-finite floats become ``None``."""
    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if isinstance(value, (np.generic,)):
        value = value.item()
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    return value


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _git_head(root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() or None


def _iter_ndjson(runs_root: Path) -> Iterable[Path]:
    """Every real run's ``search.ndjson``, deterministically ordered, archives skipped."""
    paths: list[Path] = []
    for path in runs_root.rglob("search.ndjson"):
        rel_parts = path.relative_to(runs_root).parts[:-1]
        if any(part in SKIP_DIR_PARTS for part in rel_parts):
            continue
        if any(part.startswith(SKIP_DIR_PREFIXES) for part in rel_parts):
            continue
        paths.append(path)
    return sorted(paths)


def _nearest_run_dir(ndjson_dir: Path, runs_root: Path) -> Path:
    """The closest ancestor carrying ``run.json`` (nested ``screen/`` and ``verify/`` dirs)."""
    current = ndjson_dir
    root = runs_root.resolve()
    while True:
        if (current / "run.json").is_file():
            return current
        if current.resolve() == root or current.parent == current:
            return ndjson_dir
        current = current.parent


def _run_meta(run_dir: Path) -> dict:
    meta = _read_json(run_dir / "run.json")
    raw_config = meta.get("config")
    config: dict = raw_config if isinstance(raw_config, dict) else {}
    return {
        "run_id": _text(meta.get("run_id")) or run_dir.name,
        "config_name": _text(meta.get("config_name")) or _text(config.get("name")),
        "config_sha": _text(meta.get("config_sha")),
        "config_path": _text(meta.get("config_path")),
        "family": _text(meta.get("family")) or _text(config.get("family")),
        "backend": _text(meta.get("backend")),
        "lane": _text(meta.get("lane")),
        "objective_version": meta.get("objective_version"),
        "lib_shas": meta.get("lib_shas") if isinstance(meta.get("lib_shas"), dict) else {},
        "created_utc": _text(meta.get("created_utc")),
        "started_utc": _text(meta.get("started_utc")),
        "mode": _text(meta.get("mode")),
        "status": _text(meta.get("status")),
        "command": _text(meta.get("command")),
        "_config": config,
    }


def _version_label(version: object) -> str:
    if version is None:
        return "unversioned"
    if isinstance(version, bool):
        return f"v{int(version)}"
    if isinstance(version, (int, float)) and float(version).is_integer():
        return f"v{int(version)}"
    text = str(version).strip()
    return f"v{text}" if text else "unversioned"


def _normalise_typology(label: str) -> str:
    """A display/group label that does not split the same native family in two.

    ``typology_name`` returns ``typology:osse`` for generated designs and plain ``OSSE`` for
    older family-only rows.  Both are the same OSSE typology, so the ``typology:`` prefix is
    dropped and the four native family names are canonicalised case-insensitively.  The raw
    helper output is kept as ``typology_label`` for provenance.
    """
    text = _text(label).strip()
    if text.lower().startswith("typology:"):
        text = text.split(":", 1)[1].strip()
    upper = text.upper()
    if upper in {"OSSE", "R-OSSE", "ICW", "FREEFORM"}:
        return upper
    return text or "unknown"


def _score_identity(meta: dict, version: object) -> tuple[str, str, str]:
    """``(score_config_sha, objective_config_sha, target_sha)`` from a run's config snapshot."""
    raw_config = meta.get("_config")
    config: dict = raw_config if isinstance(raw_config, dict) else {}
    objective_block = config.get("objective")
    weights = config.get("weights")
    target = config.get("target")
    objective_sha = _sha16({"objective": objective_block, "weights": weights})
    target_sha = _sha16({"target": target})
    score_sha = _sha16(
        {
            "objective_version": version,
            "objective_config_sha": objective_sha,
            "target_sha": target_sha,
        }
    )
    return score_sha, objective_sha, target_sha


# --------------------------------------------------------------------------- scan / select


def _scan(
    runs_root: Path,
    *,
    group_by: str,
    include_unversioned: bool,
) -> tuple[dict[tuple[object, ...], dict], dict[str, dict], dict[str, dict], dict]:
    """First pass: compact rows only, deduped by physical solve inside one score set.

    Returns ``(best_by_key, groups, run_meta, stats)``.  ``best_by_key`` values carry a
    ``ndjson_path`` + ``line_no`` reference; the selected top-N rows are re-read later.
    """
    stats: Counter[str] = Counter()
    run_meta: dict[str, dict] = {}
    best: dict[tuple[object, ...], dict] = {}
    groups: dict[str, dict] = {}
    scanned_files = 0

    for ndjson_path in _iter_ndjson(runs_root):
        scanned_files += 1
        run_dir = _nearest_run_dir(ndjson_path.parent, runs_root)
        run_key = _rel(run_dir, runs_root)
        if run_key not in run_meta:
            run_meta[run_key] = _run_meta(run_dir)
        meta = run_meta[run_key]

        try:
            handle = ndjson_path.open("r", encoding="utf-8", errors="replace")
        except OSError:
            stats["ndjson_unreadable"] += 1
            continue

        with handle:
            for line_no, line in enumerate(handle, 1):
                line = line.strip()
                if not line:
                    continue
                stats["rows_scanned"] += 1
                try:
                    row = json.loads(line)
                except ValueError:
                    stats["bad_json"] += 1
                    continue
                if not isinstance(row, dict):
                    stats["non_object_json"] += 1
                    continue
                stats["rows_ok" if row.get("ok") else "rows_failed"] += 1
                if not row.get("ok"):
                    continue
                objective = _finite(row.get("objective"))
                if objective is None:
                    stats["no_finite_objective"] += 1
                    continue

                backend = _text(row.get("backend")) or meta.get("backend")
                lane = _text(row.get("lane"))
                if backend != "beat_cuda" and lane != "gpu":
                    stats["not_gpu"] += 1
                    continue
                stats["rows_gpu"] += 1

                version = row.get("objective_version")
                version_source = "row"
                if version is None:
                    version = meta.get("objective_version")
                    version_source = "run" if version is not None else "missing"
                if version is None and not include_unversioned:
                    stats["unversioned_excluded"] += 1
                    continue

                score_set = _version_label(version)
                typology_label = typology_name(row.get("generator"), row.get("family")) or "unknown"
                typology = _normalise_typology(typology_label)
                score_sha, objective_sha, target_sha = _score_identity(meta, version)
                if group_by == "score-config":
                    score_set = f"{score_set}:{score_sha[:8]}"

                group_id = f"{typology}|{score_set}"
                design_hash = _text(row.get("design_hash"))
                mesh_hash = _text(row.get("mesh_hash"))
                solve_hash = _text(row.get("solve_hash"))
                physical = f"{design_hash}|{mesh_hash}|{solve_hash}"
                key = (physical, group_id)

                compact = {
                    "group_id": group_id,
                    "typology": typology,
                    "typology_label": typology_label,
                    "score_set": score_set,
                    "objective_version": version,
                    "version_source": version_source,
                    "objective": objective,
                    "design_hash": design_hash,
                    "mesh_hash": mesh_hash,
                    "solve_hash": solve_hash,
                    "physical": physical,
                    "family": _text(row.get("family")) or meta.get("family", ""),
                    "mode": _text(row.get("mode")),
                    "run_rel": run_key,
                    "run_dir": str(run_dir),
                    "ndjson_path": str(ndjson_path),
                    "line_no": line_no,
                    "score_config_sha": score_sha,
                    "objective_config_sha": objective_sha,
                    "target_sha": target_sha,
                }
                previous = best.get(key)
                if previous is None or (
                    objective,
                    str(ndjson_path),
                    line_no,
                ) < (
                    previous["objective"],
                    previous["ndjson_path"],
                    previous["line_no"],
                ):
                    best[key] = compact

    for record in best.values():
        group = groups.setdefault(
            record["group_id"],
            {
                "group_id": record["group_id"],
                "typology": record["typology"],
                "typology_label": record["typology_label"],
                "score_set": record["score_set"],
                "objective_version": record["objective_version"],
                "n_scored": 0,
                "score_config_shas": set(),
                "target_shas": set(),
                "run_rels": set(),
                "modes": Counter(),
                "families": Counter(),
            },
        )
        group["n_scored"] += 1
        group["score_config_shas"].add(record["score_config_sha"])
        group["target_shas"].add(record["target_sha"])
        group["run_rels"].add(record["run_rel"])
        group["modes"][record["mode"]] += 1
        group["families"][record["family"]] += 1

    stats["ndjson_files"] = scanned_files
    stats["unique_scored_solves"] = len(best)
    return best, groups, run_meta, dict(stats)


def _select(
    best: dict[tuple[object, ...], dict],
    groups: dict[str, dict],
    *,
    top_n: int,
    require_acoustics: bool,
) -> tuple[list[dict], dict]:
    """Pick the lowest-J rows per group, deterministically, and assign ranks."""
    by_group: dict[str, list[dict]] = defaultdict(list)
    for record in best.values():
        by_group[record["group_id"]].append(record)

    selected: list[dict] = []
    skipped_no_acoustics = 0
    for group_id in sorted(by_group):
        candidates = sorted(
            by_group[group_id],
            key=lambda record: (
                record["objective"],
                record["design_hash"],
                record["solve_hash"],
                record["ndjson_path"],
                record["line_no"],
            ),
        )
        chosen: list[dict] = []
        for record in candidates:
            if require_acoustics and _find_design_dir(record) is None:
                skipped_no_acoustics += 1
                continue
            chosen.append(record)
            if len(chosen) >= top_n:
                break
        for rank, record in enumerate(chosen, 1):
            record["rank"] = rank
            record["row_id"] = f"{group_id}#{rank:02d}"
            record["n_scored_in_group"] = len(candidates)
            selected.append(record)
        groups[group_id]["n_selected"] = len(chosen)
        if chosen:
            groups[group_id]["best_objective"] = chosen[0]["objective"]

    selected.sort(key=lambda record: (record["group_id"], record["rank"]))
    return selected, {"skipped_no_acoustics": skipped_no_acoustics}


def _read_selected_rows(selected: list[dict]) -> dict[str, dict]:
    """Second pass: re-read only the chosen lines, grouped by file, one stream per file."""
    wanted_by_path: dict[str, set[int]] = defaultdict(set)
    for record in selected:
        wanted_by_path[record["ndjson_path"]].add(record["line_no"])
    rows_by_key: dict[tuple[str, int], dict] = {}
    for path_text, line_numbers in sorted(wanted_by_path.items()):
        try:
            handle = Path(path_text).open("r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        with handle:
            for line_no, line in enumerate(handle, 1):
                if line_no not in line_numbers:
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    rows_by_key[(path_text, line_no)] = row
    full: dict[str, dict] = {}
    for record in selected:
        row = rows_by_key.get((record["ndjson_path"], record["line_no"]))
        if row is not None:
            full[record["row_id"]] = row
    return full


# --------------------------------------------------------------------------- artifacts


def _candidate_design_dirs(record: dict) -> list[Path]:
    design_hash = record["design_hash"]
    ndjson_dir = Path(record["ndjson_path"]).parent
    run_dir = Path(record["run_dir"])
    bases = [ndjson_dir, ndjson_dir.parent, run_dir, run_dir.parent]
    candidates: list[Path] = []
    seen: set[str] = set()
    for base in bases:
        for suffix in ("designs", "verify/designs", "screen/designs"):
            candidate = base / suffix / design_hash
            key = str(candidate).lower()
            if key in seen:
                continue
            seen.add(key)
            candidates.append(candidate)
    return candidates


def _find_design_dir(record: dict) -> Path | None:
    for candidate in _candidate_design_dirs(record):
        if (candidate / "response.npz").is_file():
            return candidate
    # Fallback for cached/replayed rows whose artifacts live in a sibling run subtree.  Only
    # called for selected rows (top-N), never for the whole scan.
    design_hash = record["design_hash"]
    for base in (Path(record["run_dir"]), Path(record["run_dir"]).parent):
        try:
            for match in base.glob(f"**/designs/{design_hash}/response.npz"):
                if match.is_file():
                    return match.parent
        except OSError:
            continue
    return None


def _load_acoustics(response_path: Path) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    try:
        with np.load(response_path, allow_pickle=False) as archive:
            for key in ACOUSTIC_ARRAYS:
                if key not in archive.files:
                    continue
                array = np.asarray(archive[key])
                if array.dtype.kind == "c":
                    array = array.astype(np.complex128)
                elif array.dtype.kind in "fiu":
                    array = array.astype(np.float32)
                else:
                    continue
                arrays[key] = array
    except (OSError, ValueError):
        return {}
    return arrays


def _dimensions(row: dict, mesh_meta: dict) -> dict:
    """Raw quadrant bbox + an explicitly labelled full-horn reconstruction.

    The mesher writes one fundamental domain (``quadrants='1'`` = quarter: x >= 0 and y >= 0,
    symmetry plane ``yz+xz``).  The raw bbox therefore spans half the mouth in each symmetric
    axis.  The reconstruction multiplies by 2 per symmetry plane; it is an estimate, not a
    measured mouth outline, and every raw value is kept beside it.
    """
    bbox = row.get("bbox_m")
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 6:
        result = (mesh_meta.get("result") if isinstance(mesh_meta.get("result"), dict) else {})
        bbox = result.get("bbox_m") if isinstance(result, dict) else None
    dims: dict[str, Any] = {
        "bbox_m": None,
        "bbox_quadrant_mm": None,
        "bbox_full_est_mm": None,
        "mouth_width_mm_est": None,
        "mouth_height_mm_est": None,
        "depth_mm_est": None,
        "area_m2_quadrant": None,
        "area_m2_full_est": None,
        "symmetry_plane": row.get("symmetry_plane"),
        "quadrants": row.get("quadrants"),
        "note": (
            "bbox_quadrant_mm is the stored fundamental-domain bbox; bbox_full_est_mm doubles "
            "each axis listed in symmetry_plane (yz -> x, xz -> y).  depth is the z span; axis "
            "conventions are family-specific, so compare raw bbox values when in doubt."
        ),
    }
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 6:
        return dims
    try:
        spans = [float(bbox[index + 3]) - float(bbox[index]) for index in range(3)]
    except (TypeError, ValueError):
        return dims
    if any(not math.isfinite(span) for span in spans):
        return dims
    dims["bbox_m"] = [float(value) for value in bbox]
    dims["bbox_quadrant_mm"] = [round(span * 1000.0, 6) for span in spans]
    symmetry = _text(row.get("symmetry_plane"))
    factor_x = 2 if "yz" in symmetry else 1
    factor_y = 2 if "xz" in symmetry else 1
    full = [spans[0] * factor_x * 1000.0, spans[1] * factor_y * 1000.0, spans[2] * 1000.0]
    dims["bbox_full_est_mm"] = [round(value, 6) for value in full]
    dims["mouth_width_mm_est"] = round(full[0], 3)
    dims["mouth_height_mm_est"] = round(full[1], 3)
    dims["depth_mm_est"] = round(full[2], 3)
    raw_summary = mesh_meta.get("summary")
    summary: dict = raw_summary if isinstance(raw_summary, dict) else {}
    area = _finite(summary.get("area_m2"))
    if area is None:
        result = mesh_meta.get("result") if isinstance(mesh_meta.get("result"), dict) else {}
        area = _finite((result or {}).get("area_m2"))
    if area is not None:
        dims["area_m2_quadrant"] = area
        dims["area_m2_full_est"] = area * factor_x * factor_y
    return dims


def _metric_block(row: dict, design_dir: Path | None = None) -> dict:
    raw_metrics = row.get("metrics")
    metrics: dict = raw_metrics if isinstance(raw_metrics, dict) else {}
    if (not metrics or not any(key in metrics for key in METRIC_ARRAY_KEYS)) and design_dir:
        # A few late verify/replay rows omit the inline metrics block; the design dir's
        # metrics.json is the same stored calculation.
        fallback = _read_json(design_dir / "metrics.json")
        if fallback:
            metrics = fallback
    arrays: dict[str, list] = {}
    for key in METRIC_ARRAY_KEYS:
        value = metrics.get(key)
        if isinstance(value, (list, tuple)):
            arrays[key] = _clean(list(value))
    raw_scalars = metrics.get("scalars")
    scalars: dict = raw_scalars if isinstance(raw_scalars, dict) else {}
    if not scalars and metrics:
        scalars = {
            key: value
            for key, value in metrics.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
    return {
        "arrays": arrays,
        "scalars": _clean(scalars),
        "di_source": _text(metrics.get("di_source")) or _text(row.get("di_source")),
    }


# --------------------------------------------------------------------------- document


def _run_document(run_meta: dict) -> dict:
    meta = dict(run_meta)
    raw_config = meta.pop("_config", {})
    config: dict = raw_config if isinstance(raw_config, dict) else {}
    return {
        "run_id": meta.get("run_id"),
        "config_name": meta.get("config_name"),
        "config_sha": meta.get("config_sha"),
        "config_path": meta.get("config_path"),
        "family": meta.get("family"),
        "backend": meta.get("backend"),
        "lane": meta.get("lane"),
        "objective_version": meta.get("objective_version"),
        "lib_shas": meta.get("lib_shas") or {},
        "created_utc": meta.get("created_utc"),
        "started_utc": meta.get("started_utc"),
        "mode": meta.get("mode"),
        "status": meta.get("status"),
        "command": meta.get("command"),
        "brief_file": _text(config.get("brief_file")),
        "brief_description": _text(config.get("brief")),
    }


def _score_document(run_meta: dict, version: object) -> dict:
    raw_config = run_meta.get("_config")
    config: dict = raw_config if isinstance(raw_config, dict) else {}
    objective = config.get("objective")
    weights = config.get("weights")
    target = config.get("target")
    return {
        "objective_version": version,
        "objective": _clean(objective),
        "weights": _clean(weights),
        "target": _clean(target),
        "brief_file": _text(config.get("brief_file")),
        "brief": _text(config.get("brief")),
        "config_name": _text(config.get("name")) or run_meta.get("config_name"),
        "config_sha": run_meta.get("config_sha"),
    }


def _csv_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, dict):
        return json.dumps(_clean(value), sort_keys=True, separators=(",", ":"))
    if isinstance(value, (list, tuple)):
        return json.dumps(_clean(list(value)), sort_keys=True, separators=(",", ":"))
    return value


def _flat_map(prefix: str, mapping: object) -> dict[str, object]:
    flat: dict[str, object] = {}
    if not isinstance(mapping, dict):
        return flat
    for key, value in mapping.items():
        if isinstance(value, bool) or isinstance(value, (int, float, str)) or value is None:
            flat[f"{prefix}{key}"] = value
    return flat


def _build_design(
    record: dict,
    row: dict,
    run_meta: dict,
    *,
    acoustics_file: str,
) -> tuple[dict, dict[str, np.ndarray], Path | None]:
    design_dir = _find_design_dir(record)
    mesh_meta: dict = {}
    if design_dir is not None:
        mesh_meta = _read_json(design_dir / "mesh_meta.json")
    metrics = _metric_block(row, design_dir)
    dimensions = _dimensions(row, mesh_meta)
    acoustics_id = _sha16(
        {
            "design_hash": record["design_hash"],
            "mesh_hash": record["mesh_hash"],
            "solve_hash": record["solve_hash"],
        }
    )
    arrays: dict[str, np.ndarray] = {}
    if design_dir is not None and acoustics_file:
        arrays = _load_acoustics(design_dir / "response.npz")
    if not arrays:
        acoustics_id = ""

    seconds = row.get("seconds") if isinstance(row.get("seconds"), dict) else {}
    res_mm = row.get("res_mm") if isinstance(row.get("res_mm"), dict) else {}
    design = {
        "row_id": record["row_id"],
        "group_id": record["group_id"],
        "rank": record["rank"],
        "typology": record["typology"],
        "typology_label": record["typology_label"],
        "score_set": record["score_set"],
        "objective_version": record["objective_version"],
        "version_source": record["version_source"],
        "objective": record["objective"],
        "n_scored_in_group": record["n_scored_in_group"],
        "design_id": f"{record['design_hash']}-{record['solve_hash']}",
        "design_hash": record["design_hash"],
        "mesh_hash": record["mesh_hash"],
        "solve_hash": record["solve_hash"],
        "family": record["family"],
        "mode": record["mode"],
        "run_rel": record["run_rel"],
        "run_id": run_meta.get("run_id"),
        "config_name": run_meta.get("config_name"),
        "config_sha": run_meta.get("config_sha"),
        "config_path": run_meta.get("config_path"),
        "brief_file": _text((run_meta.get("_config") or {}).get("brief_file")),
        "score_config_sha": record["score_config_sha"],
        "objective_config_sha": record["objective_config_sha"],
        "target_sha": record["target_sha"],
        "created_utc": _text(row.get("created_utc")),
        "cached": bool(row.get("cached")),
        "backend": _text(row.get("backend")) or run_meta.get("backend"),
        "lane": _text(row.get("lane")),
        "params": _clean(row.get("params")) if isinstance(row.get("params"), dict) else {},
        "generator": _clean(row.get("generator")) if isinstance(row.get("generator"), dict) else None,
        "mounting": _clean(row.get("mounting")) if isinstance(row.get("mounting"), dict) else None,
        "cad": _clean(row.get("cad")) if isinstance(row.get("cad"), dict) else None,
        "terms": _clean(row.get("terms")) if isinstance(row.get("terms"), dict) else {},
        "dimensions": dimensions,
        "metrics": metrics,
        "solve": {
            "n_dof": row.get("n_dof"),
            "n_triangles": row.get("n_triangles"),
            "quadrants": row.get("quadrants"),
            "symmetry_plane": row.get("symmetry_plane"),
            "res_mm": _clean(res_mm),
            "peak_vram_mb": row.get("peak_vram_mb"),
            "seconds": _clean(seconds),
            "build_box_m": _clean(row.get("build_box_m")),
        },
        "acoustics_id": acoustics_id or None,
        "acoustics_file": acoustics_file or None,
        "acoustics_arrays": sorted(arrays),
    }
    return design, arrays, design_dir


def run(
    *,
    runs_root: Path,
    out_dir: Path,
    top_n: int = DEFAULT_TOP,
    group_by: str = "score",
    include_unversioned: bool = True,
    require_acoustics: bool = False,
    write_acoustics: bool = True,
    csv_name: str = "top_designs.csv",
    json_name: str = "top_designs.json",
    npz_name: str = "top_designs_acoustics.npz",
) -> dict:
    """Build the export and return its summary document.  Deterministic for a given tree."""
    if top_n < 1:
        raise ValueError("top_n must be >= 1")
    if group_by not in ("score", "score-config"):
        raise ValueError("group_by must be 'score' or 'score-config'")

    best, groups, run_meta, scan_stats = _scan(
        runs_root,
        group_by=group_by,
        include_unversioned=include_unversioned,
    )
    selected, select_stats = _select(
        best,
        groups,
        top_n=top_n,
        require_acoustics=require_acoustics,
    )
    full_rows = _read_selected_rows(selected)

    designs: list[dict] = []
    acoustics: dict[str, np.ndarray] = {}
    acoustics_meta: list[dict] = []
    missing_full_rows = 0
    missing_design_dirs = 0
    for record in selected:
        row = full_rows.get(record["row_id"])
        if row is None:
            missing_full_rows += 1
            continue
        meta = run_meta[record["run_rel"]]
        design, arrays, design_dir = _build_design(
            record,
            row,
            meta,
            acoustics_file=npz_name if write_acoustics else "",
        )
        if design_dir is None:
            missing_design_dirs += 1
        if arrays and write_acoustics:
            acoustics_id = design["acoustics_id"]
            for key, array in arrays.items():
                acoustics[f"{acoustics_id}__{key}"] = array
            acoustics_meta.append(
                {
                    "acoustics_id": acoustics_id,
                    "row_id": design["row_id"],
                    "design_hash": design["design_hash"],
                    "solve_hash": design["solve_hash"],
                    "arrays": sorted(arrays),
                }
            )
        designs.append(design)

    group_docs: list[dict] = []
    for group_id in sorted(groups):
        group = groups[group_id]
        chosen_ids = [design["row_id"] for design in designs if design["group_id"] == group_id]
        group_docs.append(
            {
                "group_id": group_id,
                "typology": group["typology"],
                "typology_label": group["typology_label"],
                "score_set": group["score_set"],
                "objective_version": group["objective_version"],
                "n_scored": group["n_scored"],
                "n_selected": len(chosen_ids),
                "best_objective": group.get("best_objective"),
                "score_config_shas": sorted(group["score_config_shas"]),
                "target_shas": sorted(group["target_shas"]),
                "run_rels": sorted(group["run_rels"]),
                "modes": dict(sorted(group["modes"].items())),
                "families": dict(sorted(group["families"].items())),
                "design_row_ids": chosen_ids,
            }
        )

    score_configs: dict[str, dict] = {}
    for record in selected:
        meta = run_meta[record["run_rel"]]
        score_configs.setdefault(
            record["score_config_sha"],
            _score_document(meta, record["objective_version"]),
        )
    run_docs = {run_rel: _run_document(meta) for run_rel, meta in sorted(run_meta.items())}

    counts = {
        **scan_stats,
        **select_stats,
        "groups": len(group_docs),
        "selected": len(designs),
        "missing_full_rows": missing_full_rows,
        "missing_design_dirs": missing_design_dirs,
        "designs_with_acoustics": sum(1 for design in designs if design["acoustics_arrays"]),
        "acoustics_array_count": len(acoustics),
    }
    document = {
        "tool": TOOL,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "runs_root": _rel(runs_root, REPO_ROOT),
            "repo_head": _git_head(REPO_ROOT),
            "tool_path": str(Path(__file__).resolve().relative_to(REPO_ROOT).as_posix()),
        },
        "grouping": {
            "top_n": top_n,
            "group_by": group_by,
            "score_set": (
                "objective_version"
                if group_by == "score"
                else "objective_version + resolved score config (objective+weights+target)"
            ),
            "ranking": "ascending objective (lower is better)",
            "typology": "hornlab_search.dataset.record.typology_name(generator, family), "
            "with the 'typology:' prefix and native family case normalised for grouping "
            "(raw value kept as typology_label)",
            "gpu_filter": "row backend == beat_cuda or lane == gpu (run fallback); CPU excluded",
            "dedupe": (
                "same design_hash|mesh_hash|solve_hash inside one score set keeps the lowest J; "
                "a physical solve may appear once per score set"
            ),
            "unversioned": include_unversioned,
        },
        "counts": counts,
        "score_configs": score_configs,
        "runs": run_docs,
        "groups": group_docs,
        "designs": designs,
        "acoustics": {
            "file": npz_name if write_acoustics else None,
            "format": "numpy .npz (savez_compressed)",
            "key_template": "<acoustics_id>__<array>",
            "arrays": list(ACOUSTIC_ARRAYS),
            "float32_arrays": [key for key in ACOUSTIC_ARRAYS if key != "z_throat"],
            "complex128_arrays": ["z_throat"],
            "designs_with_arrays": counts["designs_with_acoustics"],
            "count": len(acoustics),
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / csv_name
    json_path = out_dir / json_name
    npz_path = out_dir / npz_name if write_acoustics else None

    _write_csv(csv_path, designs, counts=counts)
    if npz_path is not None:
        _write_npz(npz_path, acoustics)
    document["outputs"] = {
        "csv": csv_name,
        "json": json_name,
        "acoustics": npz_name if write_acoustics else None,
        "csv_bytes": csv_path.stat().st_size if csv_path.is_file() else None,
        "acoustics_bytes": npz_path.stat().st_size if npz_path is not None and npz_path.is_file() else None,
    }
    _write_json(json_path, document)
    return document


def _write_csv(path: Path, designs: list[dict], *, counts: dict) -> None:
    rows: list[dict] = []
    for design in designs:
        raw_dimensions = design.get("dimensions")
        dimensions = raw_dimensions if isinstance(raw_dimensions, dict) else {}
        raw_metrics = design.get("metrics")
        metrics = raw_metrics if isinstance(raw_metrics, dict) else {}
        raw_scalars = metrics.get("scalars")
        scalars = raw_scalars if isinstance(raw_scalars, dict) else {}
        raw_solve = design.get("solve")
        solve = raw_solve if isinstance(raw_solve, dict) else {}
        raw_res = solve.get("res_mm")
        res_mm = raw_res if isinstance(raw_res, dict) else {}
        raw_seconds = solve.get("seconds")
        seconds = raw_seconds if isinstance(raw_seconds, dict) else {}
        row: dict[str, object] = {
            "row_id": design.get("row_id"),
            "group_id": design.get("group_id"),
            "rank": design.get("rank"),
            "typology": design.get("typology"),
            "typology_label": design.get("typology_label"),
            "score_set": design.get("score_set"),
            "objective_version": design.get("objective_version"),
            "version_source": design.get("version_source"),
            "objective": design.get("objective"),
            "n_scored_in_group": design.get("n_scored_in_group"),
            "design_hash": design.get("design_hash"),
            "mesh_hash": design.get("mesh_hash"),
            "solve_hash": design.get("solve_hash"),
            "design_id": design.get("design_id"),
            "family": design.get("family"),
            "mode": design.get("mode"),
            "run_rel": design.get("run_rel"),
            "run_id": design.get("run_id"),
            "config_name": design.get("config_name"),
            "config_sha": design.get("config_sha"),
            "config_path": design.get("config_path"),
            "brief_file": design.get("brief_file"),
            "score_config_sha": design.get("score_config_sha"),
            "objective_config_sha": design.get("objective_config_sha"),
            "target_sha": design.get("target_sha"),
            "created_utc": design.get("created_utc"),
            "cached": design.get("cached"),
            "backend": design.get("backend"),
            "lane": design.get("lane"),
            "n_dof": solve.get("n_dof"),
            "n_triangles": solve.get("n_triangles"),
            "quadrants": solve.get("quadrants"),
            "symmetry_plane": solve.get("symmetry_plane"),
            "res_throat_mm": res_mm.get("throat"),
            "res_mouth_mm": res_mm.get("mouth"),
            "res_rear_mm": res_mm.get("rear"),
            "peak_vram_mb": solve.get("peak_vram_mb"),
            "solve_seconds": seconds.get("solve"),
            "total_seconds": seconds.get("total"),
            "bbox_x_mm": (dimensions.get("bbox_quadrant_mm") or [None, None, None])[0],
            "bbox_y_mm": (dimensions.get("bbox_quadrant_mm") or [None, None, None])[1],
            "bbox_z_mm": (dimensions.get("bbox_quadrant_mm") or [None, None, None])[2],
            "mouth_width_mm_est": dimensions.get("mouth_width_mm_est"),
            "mouth_height_mm_est": dimensions.get("mouth_height_mm_est"),
            "depth_mm_est": dimensions.get("depth_mm_est"),
            "area_m2_quadrant": dimensions.get("area_m2_quadrant"),
            "area_m2_full_est": dimensions.get("area_m2_full_est"),
            "acoustics_id": design.get("acoustics_id"),
            "acoustics_file": design.get("acoustics_file"),
            "acoustics_arrays": design.get("acoustics_arrays"),
        }
        row.update(_flat_map(PARAM_PREFIX, design.get("params")))
        row.update(_flat_map(TERM_PREFIX, design.get("terms")))
        row.update(_flat_map(METRIC_PREFIX, scalars))
        rows.append(row)

    fieldnames = list(BASE_CSV_FIELDS)
    extras = sorted({key for row in rows for key in row if key not in BASE_CSV_FIELDS})
    fieldnames.extend(extras)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})
    os.replace(tmp, path)


def _write_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    os.replace(tmp, path)


def _write_json(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(_clean(document), indent=2, sort_keys=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


# --------------------------------------------------------------------------- CLI


def _summary_lines(document: dict, out_dir: Path) -> list[str]:
    counts = document["counts"]
    acoustics = document["acoustics"]
    lines = [
        "top_designs: best GPU-solved designs per typology and score set",
        f"  ndjson files      : {counts.get('ndjson_files', 0)}",
        f"  rows scanned      : {counts.get('rows_scanned', 0)} "
        f"(GPU {counts.get('rows_gpu', 0)}, not GPU {counts.get('not_gpu', 0)})",
        f"  unique scored     : {counts.get('unique_scored_solves', 0)} physical solves",
        f"  groups            : {counts.get('groups', 0)}",
        f"  selected          : {counts.get('selected', 0)} designs "
        f"(top {document['grouping']['top_n']} per group)",
        f"  acoustics         : {counts.get('designs_with_acoustics', 0)} designs, "
        f"{counts.get('acoustics_array_count', 0)} arrays"
        + (
            f", {acoustics['file']}"
            if acoustics.get("file")
            else " (not written)"
        ),
    ]
    if counts.get("missing_design_dirs"):
        lines.append(f"  missing design dir: {counts['missing_design_dirs']}")
    if counts.get("missing_full_rows"):
        lines.append(f"  missing full rows : {counts['missing_full_rows']}")
    lines.append(f"  output            : {out_dir}")
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="top_designs.py",
        description=(
            "Export the top-N lowest-objective GPU-solved designs per typology and score set, "
            "with full acoustic arrays and geometry metadata."
        ),
    )
    parser.add_argument("--runs", default="runs", help="run tree root (default: runs)")
    parser.add_argument(
        "--out",
        default="docs/top_designs",
        help="output directory (default: docs/top_designs)",
    )
    parser.add_argument("--top", type=int, default=DEFAULT_TOP, help="designs per group (default: 10)")
    parser.add_argument(
        "--group-by",
        choices=("score", "score-config"),
        default="score",
        help=(
            "score = objective version only (default, repo ranking identity); "
            "score-config = version + resolved objective/weights/target identity"
        ),
    )
    parser.add_argument(
        "--exclude-unversioned",
        action="store_true",
        help="drop rows whose run/row recorded no objective version (default: keep as 'unversioned')",
    )
    parser.add_argument(
        "--require-acoustics",
        action="store_true",
        help="only rank rows whose response.npz exists (default: rank all, flag missing arrays)",
    )
    parser.add_argument(
        "--no-acoustics",
        action="store_true",
        help="write CSV+JSON only, no .npz bundle",
    )
    parser.add_argument("--csv-name", default="top_designs.csv")
    parser.add_argument("--json-name", default="top_designs.json")
    parser.add_argument("--npz-name", default="top_designs_acoustics.npz")
    parser.add_argument("--quiet", action="store_true", help="do not print the summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runs_root = Path(args.runs)
    out_dir = Path(args.out)
    if not runs_root.is_absolute():
        runs_root = REPO_ROOT / runs_root
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    document = run(
        runs_root=runs_root,
        out_dir=out_dir,
        top_n=args.top,
        group_by=args.group_by,
        include_unversioned=not args.exclude_unversioned,
        require_acoustics=args.require_acoustics,
        write_acoustics=not args.no_acoustics,
        csv_name=args.csv_name,
        json_name=args.json_name,
        npz_name=args.npz_name,
    )
    if not args.quiet:
        for line in _summary_lines(document, out_dir):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
