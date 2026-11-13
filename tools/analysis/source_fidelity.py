"""S6 source-fidelity / source-context cards for the native ATH cohort (bo-study-v1.1).

Read-only companion to the R0 ``offline_scores`` artifact and the S0 catalog. For every
native ``native__ath_core_v4`` ok row the current S0 catalog can resolve, emit one card:

* ``di_source`` — ``balloon`` / ``cuts_estimate`` read from the stored ``metrics_scalars``
  (never inferred from terms);
* ``missingness`` — which balloon / cuts / throat-impedance arrays the stored ``.npz`` holds;
* ``physical_size`` — mouth width/height/depth from the stored design parameters
  (``morph_width_mm`` / ``morph_height_mm`` / ``L_mm``) unless a per-design B2 descriptor
  index is trivially joinable;
* ``backend`` and ``fidelity`` (``screen`` / ``verify``) from the stored solve record,
  cross-checked against the catalog;
* ``verify_pairing`` — the screen/verify pair inside one run, resolved through
  ``tools/analysis/fidelity.py``'s public pairing resolver when importable and always
  cross-checked against exact ``(design_hash, mesh_hash, solve_hash)`` run provenance.
  It never pairs two rows from different runs or two rows that only share a design hash;
* the frozen 2-inch uniform-piston / f11 3957 Hz / loading-weight-0 / size-frequency
  confounding context (band 300-8000 Hz, f0 1280 Hz).

Hard guarantees
---------------
* **Read-only.** Only ``--out`` is written; dataset, runs, catalog, scores and brief are
  hashed before/after and a change is a hard failure.
* **Zero backend.** No solver/BEM/GPU/mesh module is imported; the fidelity resolver reads
  ``search.ndjson`` only.
* **Honest unknowns.** A missing ``di_source``, unreadable ``.npz``, absent verify row or
  ambiguous run provenance stays explicit (``null`` / ``pairing_unavailable`` + reasons);
  nothing is invented. Loading weight is 0: no loading/efficiency/SPL claims.

Usage::

    .venv\\Scripts\\python.exe tools/analysis/source_fidelity.py \\
        --scores scratch/bo_m0/r0/offline_scores_native/offline_scores.json \\
        --catalog scratch/bo_m0/s0/catalog/catalog.csv \\
        --dataset dataset --runs runs \\
        --out scratch/bo_m0/s6

No commit, no upload, no writes outside ``--out``.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]

TOOL = "source_fidelity"
SCHEMA_VERSION = 1
PROTOCOL = "bo-study-v1.1"
NATIVE_CONFIG = "native__ath_core_v4"

DEFAULT_SCORES = REPO_ROOT / "scratch" / "bo_m0" / "r0" / "offline_scores_native" / "offline_scores.json"
DEFAULT_CATALOG = REPO_ROOT / "scratch" / "bo_m0" / "s0" / "catalog" / "catalog.csv"
DEFAULT_DATASET = REPO_ROOT / "dataset"
DEFAULT_RUNS = REPO_ROOT / "runs"
DEFAULT_BRIEF = (REPO_ROOT / "examples" / "briefs" / "campaign_2026-10-26_v4"
                 / "native_ath_core_2in_v4.yaml")
DEFAULT_OUT = REPO_ROOT / "scratch" / "bo_m0" / "s6"

#: Stored array groups of the native dataset record (verified against the archive).
BALLOON_ARRAYS = ("balloon_dirs", "spl_balloon_db")
CUTS_ARRAYS = ("spl_h_db", "spl_v_db", "h_angles_deg", "v_angles_deg",
               "di_db", "ripple_h_db", "ripple_v_db", "on_axis_db")
Z_ARRAYS = ("z_throat",)

#: Frozen source-assumption context (parent M0 freeze, sections 1 and 6).
SOURCE_ASSUMPTION_CONTEXT = {
    "source_model": "2-inch compression driver modelled as a uniform piston",
    "excitation": ("uniform_normal_velocity on source tag SD1D1001 (rescaled to unit "
                   "normal acceleration by hornlab-beat-bem)"),
    "f11_hz": 3957.0,
    "f11_statement": ("above ~3957 Hz the uniform-piston source is a geometry comparison, "
                      "not a real 2-inch driver exit behaviour"),
    "loading_weight": 0.0,
    "loading_weight_statement": ("loading weight is 0: no loading, efficiency, distortion "
                                 "or maximum-SPL claims are made"),
    "band_hz": [300.0, 8000.0],
    "f0_hz": 1280.0,
    "size_frequency_confounding_note": (
        "J mixes physical size and frequency: a longer/wider horn can score better while "
        "its aperture grows. Report absolute dimensions and the band/f0; do not attribute "
        "the whole score change to the flare law, and do not condition away a deterministic "
        "construction relationship as a causal law."),
}


# ------------------------------------------------------------------ small helpers

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _clean(obj):
    """JSON-safe copy: numpy scalars -> Python, non-finite floats -> None."""
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, Path):
        return str(obj)
    return obj


def _is_true(value) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return False


def _as_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _as_float(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


# ------------------------------------------------------------------ inputs

def load_catalog(path: Path) -> list[dict]:
    """S0 catalog rows (plain ``csv.DictReader``; read-only)."""
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_scores(path: Path) -> dict:
    """R0 offline-scores artifact (the file is a JSON object)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_brief(path: Path) -> dict:
    """Brief YAML if parseable, else ``{}`` (its absence is reported, never invented)."""
    try:
        import yaml  # local import: the tool already depends on the analysis stack
    except Exception:  # noqa: BLE001 - optional at import time
        return {}
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def select_native_rows(catalog: list[dict], config: str = NATIVE_CONFIG) -> list[dict]:
    """Every ``ok`` row of the frozen native config (all other rows are excluded)."""
    return [r for r in catalog
            if str(r.get("config_name") or "") == config and _is_true(r.get("ok"))]


def _shard_of(row: dict):
    shard = _as_int(row.get("shard_index"))
    if shard is None:
        shard = _as_int(row.get("shard"))
    return shard


def read_shard_table(dataset_root: Path, shard_ids) -> dict[int, dict]:
    """``{shard: {rows, sha256, size, path}}`` for the shards the cohort reads.

    ``rows`` is indexed by physical line number; a torn/blank line is ``None`` so indices
    never shift. The exact bytes read are hashed for the source guard.
    """
    out: dict[int, dict] = {}
    for shard in sorted(set(int(s) for s in shard_ids if s is not None)):
        p = Path(dataset_root) / f"shard-{shard:04d}.jsonl"
        entry = {"path": p, "exists": p.is_file(), "rows": [], "sha256": None,
                 "size": None}
        if p.is_file():
            blob = p.read_bytes()
            entry["sha256"] = _sha256_bytes(blob)
            entry["size"] = len(blob)
            for line in blob.decode("utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    entry["rows"].append(None)
                    continue
                try:
                    entry["rows"].append(json.loads(line))
                except ValueError:
                    entry["rows"].append(None)
        out[shard] = entry
    return out


def _npz_summary(path: Path) -> dict:
    """Stored arrays of one record: readability, keys and the required groups."""
    summary = {"path": str(path), "exists": Path(path).is_file(), "readable": False,
               "sha256": None, "keys": [], "balloon": {"present": False,
               "missing_arrays": list(BALLOON_ARRAYS), "spl_balloon_shape": None,
               "n_balloon_dirs": None, "n_finite": 0},
               "cuts": {"present": False, "missing_arrays": list(CUTS_ARRAYS)},
               "z": {"present": False, "missing_arrays": list(Z_ARRAYS),
                     "n": None, "n_finite": None}}
    if not Path(path).is_file():
        return summary
    summary["sha256"] = _sha256_file(Path(path))
    try:
        with np.load(path, allow_pickle=False) as z:
            keys = list(z.files)
            summary["readable"] = True
            summary["keys"] = sorted(keys)
            balloon_missing = [k for k in BALLOON_ARRAYS if k not in keys]
            if not balloon_missing:
                balloon = z["spl_balloon_db"]
                dirs = z["balloon_dirs"]
                finite = int(np.isfinite(balloon).sum()) if balloon.size else 0
                summary["balloon"] = {
                    "present": bool(balloon.size and dirs.size and finite),
                    "missing_arrays": [],
                    "spl_balloon_shape": list(balloon.shape),
                    "n_balloon_dirs": int(dirs.shape[0]) if dirs.ndim >= 1 else None,
                    "n_finite": finite,
                }
            else:
                summary["balloon"]["missing_arrays"] = balloon_missing
            cuts_missing = [k for k in CUTS_ARRAYS if k not in keys]
            cuts_present = not cuts_missing and all(
                np.asarray(z[k]).size > 0 for k in CUTS_ARRAYS)
            summary["cuts"] = {"present": bool(cuts_present),
                               "missing_arrays": cuts_missing}
            z_missing = [k for k in Z_ARRAYS if k not in keys]
            if not z_missing:
                arr = z["z_throat"]
                summary["z"] = {"present": bool(arr.size and np.isfinite(arr).any()),
                                "missing_arrays": [], "n": int(arr.size),
                                "n_finite": int(np.isfinite(arr).sum())}
            else:
                summary["z"]["missing_arrays"] = z_missing
    except Exception:  # noqa: BLE001 - a corrupt npz is an honest unreadable record
        summary["readable"] = False
    return summary


# ------------------------------------------------------------------ run provenance / pairing

def build_run_index(runs_root: Path, target_keys) -> dict:
    """Exact ``(design_hash, mesh_hash, solve_hash)`` provenance from run ndjson files.

    Never matches on ``design_hash`` alone. The returned ``files`` map carries the hash of
    every ndjson file whose rows informed the artifact (for the source guard).
    """
    index: dict[tuple, list[dict]] = {}
    files: dict[str, dict] = {}
    runs_scanned = 0
    root = Path(runs_root)
    if not root.is_dir():
        return {"index": index, "files": files, "runs_scanned": 0, "exists": False}
    for run_dir in sorted(p for p in root.iterdir()
                          if p.is_dir() and not p.name.startswith(".")):
        runs_scanned += 1
        for rel in ("search.ndjson", "verify/search.ndjson"):
            p = run_dir / rel
            if not p.is_file():
                continue
            blob = p.read_bytes()
            matched = False
            for line in blob.decode("utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                key = (row.get("design_hash"), row.get("mesh_hash"), row.get("solve_hash"))
                if key in target_keys:
                    matched = True
                    index.setdefault(key, []).append({
                        "run_id": run_dir.name,
                        "file": rel,
                        "mode": row.get("mode"),
                        "n": row.get("n"),
                    })
            if matched:
                files[f"{run_dir.name}/{rel}"] = {
                    "sha256": _sha256_bytes(blob), "size": len(blob)}
    return {"index": index, "files": files, "runs_scanned": runs_scanned, "exists": True}


def _load_fidelity_resolver():
    """Import ``tools/analysis/fidelity.py`` read-only; ``(module, error)``."""
    try:
        here = Path(__file__).resolve().parent
        if str(here) not in sys.path:
            sys.path.insert(0, str(here))
        return importlib.import_module("fidelity"), None
    except Exception as exc:  # noqa: BLE001 - the fallback is explicit
        return None, f"{type(exc).__name__}: {exc}"


def _run_matches_for_key(run_index: dict, key: tuple) -> list[dict]:
    return list((run_index.get("index") or {}).get(key, []))


def resolve_pairing(cards: list[dict], run_index: dict, runs_root: Path,
                    fidelity_mod, fidelity_error) -> dict:
    """Attach run provenance and screen/verify pairing to every card, in place.

    A pair requires (a) both exact physical keys in the *same* run directory and (b) a
    verify row in that run's ``verify/search.ndjson``. The public fidelity resolver is used
    only to confirm/report the within-run pair; a failed import falls back to the exact
    run-provenance linkage (never a cross-run design-hash join).
    """
    screen_by_hash: dict[str, list[dict]] = {}
    verify_by_hash: dict[str, list[dict]] = {}
    for c in cards:
        if c["fidelity"] == "screen":
            screen_by_hash.setdefault(c["design_hash"], []).append(c)
        elif c["fidelity"] == "verify":
            verify_by_hash.setdefault(c["design_hash"], []).append(c)

    # provenance for every card (exact physical key only)
    for c in cards:
        matches = _run_matches_for_key(run_index, c["_key"])
        run_ids = sorted({m["run_id"] for m in matches})
        if not matches:
            status = "unavailable"
        elif len(run_ids) > 1:
            status = "ambiguous"
        else:
            status = "resolved"
        c["run_provenance"] = {
            "status": status,
            "run_ids": run_ids,
            "matches": matches,
            "recovered_by": "exact (design_hash, mesh_hash, solve_hash) match in run ndjson",
        }

    pairing_by_hash: dict[str, dict] = {}
    for dh, vcards in verify_by_hash.items():
        for vc in vcards:
            reasons: list[str] = []
            warnings: list[str] = []
            matches = _run_matches_for_key(run_index, vc["_key"])
            run_ids = sorted({m["run_id"] for m in matches})
            paired = None
            run_id = None
            if not matches:
                reasons.append("run_provenance_unavailable")
            elif len(run_ids) > 1:
                reasons.append("run_provenance_ambiguous")
            else:
                run_id = run_ids[0]
                if not any(m["file"] == "verify/search.ndjson" for m in matches):
                    reasons.append("verify_row_not_found_in_run_verify_index")
                screens = screen_by_hash.get(dh, [])
                if not screens:
                    reasons.append("screen_counterpart_missing_from_cohort")
                elif len(screens) > 1:
                    reasons.append("multiple_screen_counterparts_in_cohort")
                else:
                    sc = screens[0]
                    smatches = _run_matches_for_key(run_index, sc["_key"])
                    if not any(m["run_id"] == run_id for m in smatches):
                        reasons.append("screen_counterpart_not_in_same_run")
                    else:
                        paired = sc

            resolver_pair = None
            method = None
            if paired is not None and not reasons and run_id is not None:
                method = "run_provenance_exact_physical_identity"
                if fidelity_mod is not None:
                    try:
                        payload = fidelity_mod.analyse_run(Path(runs_root) / run_id)
                        for pair in payload.get("pairs") or []:
                            if pair.get("design_hash") == dh:
                                resolver_pair = pair
                                break
                        if resolver_pair is not None:
                            method = "reused_tools.analysis.fidelity.analyse_run"
                        else:
                            warnings.append("fidelity_resolver_found_no_pair")
                    except Exception as exc:  # noqa: BLE001
                        warnings.append(f"fidelity_resolver_error:{type(exc).__name__}")
                else:
                    warnings.append(f"fidelity_resolver_unavailable:{fidelity_error}")

            if paired is not None and not reasons:
                pairing = {
                    "status": "paired",
                    "method": method,
                    "run_id": run_id,
                    "paired_design_hash": paired["design_hash"],
                    "paired_physical_solve_id": paired["physical_solve_id"],
                    "paired_fidelity": paired["fidelity"],
                    "paired_shard": paired["shard"],
                    "paired_row": paired["row"],
                    "resolver_pair": resolver_pair,
                    "reasons": [],
                    "warnings": warnings,
                    "note": ("both exact physical keys found in the same run; the public "
                             "fidelity resolver confirms the within-run pair"),
                }
            else:
                pairing = {
                    "status": "pairing_unavailable",
                    "method": None,
                    "run_id": run_id,
                    "paired_design_hash": None,
                    "paired_physical_solve_id": None,
                    "paired_fidelity": None,
                    "paired_shard": None,
                    "paired_row": None,
                    "resolver_pair": None,
                    "reasons": reasons or ["pairing_not_supported_for_these_rows"],
                    "warnings": warnings,
                    "note": "no verify pairing is asserted without same-run physical provenance",
                }
            vc["verify_pairing"] = pairing
            pairing_by_hash.setdefault(dh, pairing)

    for c in cards:
        if "verify_pairing" in c and c["fidelity"] == "verify":
            continue
        dh = c["design_hash"]
        if dh in verify_by_hash:
            vpair = pairing_by_hash[dh]
            verify_card = verify_by_hash[dh][0]
            if vpair["status"] == "paired":
                c["verify_pairing"] = {
                    "status": "paired",
                    "method": vpair["method"],
                    "run_id": vpair["run_id"],
                    "paired_design_hash": dh,
                    "paired_physical_solve_id": verify_card["physical_solve_id"],
                    "paired_fidelity": "verify",
                    "paired_shard": verify_card["shard"],
                    "paired_row": verify_card["row"],
                    "resolver_pair": vpair["resolver_pair"],
                    "reasons": [],
                    "warnings": list(vpair.get("warnings") or []),
                    "note": "same-run verify row exists for this design",
                }
            else:
                c["verify_pairing"] = {
                    "status": "pairing_unavailable",
                    "method": None,
                    "run_id": vpair.get("run_id"),
                    "paired_design_hash": None,
                    "paired_physical_solve_id": None,
                    "paired_fidelity": None,
                    "paired_shard": None,
                    "paired_row": None,
                    "resolver_pair": None,
                    "reasons": list(vpair.get("reasons") or []),
                    "warnings": list(vpair.get("warnings") or []),
                    "note": "a verify row for this design exists but could not be paired",
                }
        else:
            c["verify_pairing"] = {
                "status": "no_verify_row",
                "method": None,
                "run_id": (c.get("run_provenance") or {}).get("run_ids", [None])[0]
                if (c.get("run_provenance") or {}).get("status") == "resolved" else None,
                "paired_design_hash": None,
                "paired_physical_solve_id": None,
                "paired_fidelity": None,
                "paired_shard": None,
                "paired_row": None,
                "resolver_pair": None,
                "reasons": ["no_verify_row_for_design_in_native_cohort"],
                "warnings": [],
                "note": "the cohort has no verify row for this design",
            }
    return pairing_by_hash


# ------------------------------------------------------------------ cards

def _card_from_row(row: dict, meta, npz: dict, offline_score, brief: dict) -> dict:
    """One per-row fidelity/source card (all unknowns stay ``None``)."""
    params = (meta or {}).get("params") if isinstance(meta, dict) else None
    if not isinstance(params, dict):
        params = {}
    metrics = (meta or {}).get("metrics_scalars") if isinstance(meta, dict) else None
    if not isinstance(metrics, dict):
        metrics = {}
    solve = (meta or {}).get("solve") if isinstance(meta, dict) else None
    if not isinstance(solve, dict):
        solve = {}
    terms = (meta or {}).get("terms") if isinstance(meta, dict) else None
    if not isinstance(terms, dict):
        terms = {}

    design_hash = str(row.get("design_hash") or "")
    shard = _shard_of(row)
    row_index = _as_int(row.get("row"))
    mesh_hash = str(row.get("mesh_hash") or "")
    solve_hash = str(row.get("solve_hash") or "")
    catalog_backend = str(row.get("backend") or "") or None
    catalog_fidelity = str(row.get("fidelity") or "") or None
    stored_mode = solve.get("mode")
    stored_backend = solve.get("backend")

    warnings: list[str] = []
    resolution = "ok"
    if meta is None:
        resolution = "dataset_row_missing"
        warnings.append("dataset row missing or unparseable at catalog (shard,row)")
    else:
        if meta.get("design_hash") not in (None, design_hash):
            warnings.append("dataset design_hash differs from catalog design_hash")
        if mesh_hash and meta.get("mesh_hash") not in (None, mesh_hash):
            warnings.append("dataset mesh_hash differs from catalog mesh_hash")
        if solve_hash and meta.get("solve_hash") not in (None, solve_hash):
            warnings.append("dataset solve_hash differs from catalog solve_hash")
        if catalog_backend and stored_backend and catalog_backend != stored_backend:
            warnings.append("catalog backend differs from stored solve.backend")
        if catalog_fidelity and stored_mode and catalog_fidelity != stored_mode:
            warnings.append("catalog fidelity differs from stored solve.mode")

    stored_di = metrics.get("di_source")
    di_source = stored_di if stored_di in ("balloon", "cuts_estimate") else None
    di_evidence = {
        "stored_field": "metrics_scalars.di_source",
        "stored_value": stored_di,
        "di_estimated_term": terms.get("di_estimated"),
    }
    if di_source is None:
        di_evidence["reason"] = "di_source_absent_or_not_recognised_in_stored_metrics"

    size = {
        "mouth_w_mm": _as_float(params.get("morph_width_mm")),
        "mouth_h_mm": _as_float(params.get("morph_height_mm")),
        "depth_mm": _as_float(params.get("L_mm")),
        "source": "stored_design_params",
        "b2_geometry_descriptors": {
            "joinable": False,
            "reason": ("the B2 artifact is a single seed-design contour, not a "
                       "per-design descriptor index"),
        },
        "note": ("nominal morph target dimensions before later transforms; not a measured "
                 "mouth or an acoustic size law"),
    }

    fidelity = catalog_fidelity or (stored_mode if stored_mode in ("screen", "verify") else None)
    backend = stored_backend or catalog_backend

    card = {
        "design_hash": design_hash,
        "shard": shard,
        "row": row_index,
        "catalog_root": row.get("root"),
        "physical_solve_id": row.get("physical_solve_id"),
        "mesh_hash": mesh_hash or None,
        "solve_hash": solve_hash or None,
        "config_name": row.get("config_name"),
        "brief": row.get("brief"),
        "brief_hash": row.get("brief_hash"),
        "catalog_run_id": row.get("run_id") or "",
        "fidelity": fidelity,
        "backend": backend,
        "di_source": di_source,
        "di_source_evidence": di_evidence,
        "missingness": {
            "npz_readable": npz["readable"],
            "balloon": npz["balloon"],
            "cuts": npz["cuts"],
            "z": npz["z"],
            "stored_npz_keys": npz["keys"],
        },
        "physical_size": size,
        "stored_metrics": {
            "objective": meta.get("objective") if isinstance(meta, dict) else None,
            "objective_version": meta.get("objective_version") if isinstance(meta, dict) else None,
            "f11_hz": metrics.get("f11_hz"),
            "di_mean_db": metrics.get("di_mean_db"),
            "ripple_mean_db": metrics.get("ripple_mean_db"),
            "bw_h_mean_deg": metrics.get("bw_h_mean_deg"),
            "bw_v_mean_deg": metrics.get("bw_v_mean_deg"),
        },
        "source_context": {
            "f11_hz": SOURCE_ASSUMPTION_CONTEXT["f11_hz"],
            "stored_f11_hz": metrics.get("f11_hz"),
            "loading_weight": SOURCE_ASSUMPTION_CONTEXT["loading_weight"],
            "band_hz": list(SOURCE_ASSUMPTION_CONTEXT["band_hz"]),
            "f0_hz": SOURCE_ASSUMPTION_CONTEXT["f0_hz"],
            "note": "see top-level source_assumption_context",
        },
        "offline_score": offline_score,
        "resolution": resolution,
        "warnings": warnings,
        "_key": (design_hash, mesh_hash, solve_hash),
    }
    return card


# ------------------------------------------------------------------ cohort summary

def _dist(values) -> dict:
    out: dict[str, int] = {}
    for v in values:
        key = "unknown" if v is None else str(v)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def _cohort_summary(cards: list[dict], score_artifact: dict, run_index: dict,
                    fidelity_error) -> dict:
    pairing_counts = _dist(c.get("verify_pairing", {}).get("status") for c in cards)
    reasons: dict[str, int] = {}
    for c in cards:
        pairing = c.get("verify_pairing") or {}
        if pairing.get("status") == "pairing_unavailable":
            for reason in pairing.get("reasons") or []:
                reasons[reason] = reasons.get(reason, 0) + 1
    verify_run_set = set()
    for c in cards:
        pairing = c.get("verify_pairing") or {}
        if (c.get("fidelity") == "verify" and pairing.get("status") == "paired"
                and pairing.get("run_id")):
            verify_run_set.add(pairing["run_id"])
    verify_runs = sorted(verify_run_set)
    provenance = _dist((c.get("run_provenance") or {}).get("status") for c in cards)
    offline_matched = sum(1 for c in cards if c.get("offline_score") is not None)
    return {
        "config": NATIVE_CONFIG,
        "rows": len(cards),
        "unique_design_hash": len({c["design_hash"] for c in cards}),
        "with_balloon": sum(1 for c in cards
                            if (c["missingness"]["balloon"] or {}).get("present")),
        "with_z": sum(1 for c in cards if (c["missingness"]["z"] or {}).get("present")),
        "screen_vs_verify": {
            "screen": sum(1 for c in cards if c.get("fidelity") == "screen"),
            "verify": sum(1 for c in cards if c.get("fidelity") == "verify"),
        },
        "di_source_counts": _dist(c.get("di_source") for c in cards),
        "pairing_status_counts": pairing_counts,
        "pairing_unavailable_reasons": dict(sorted(reasons.items())),
        "verify_runs_found": len(verify_runs),
        "verify_runs": verify_runs,
        "run_provenance_counts": provenance,
        "runs_scanned": run_index.get("runs_scanned"),
        "run_ndjson_files_informing_artifact": len(run_index.get("files") or {}),
        "offline_scores_rows_matched": offline_matched,
        "offline_scores_rows_in_artifact": len((score_artifact or {}).get("rows") or []),
        "offline_scores_reported_scored": (((score_artifact or {}).get("counts") or {})
                                           .get("scored")),
        "fidelity_resolver": ("available" if fidelity_error is None
                              else "unavailable: " + str(fidelity_error)),
    }


# ------------------------------------------------------------------ source guard

def _snapshot_paths(paths: list[Path]) -> dict[str, str]:
    out = {}
    for p in paths:
        p = Path(p)
        try:
            out[str(p)] = _sha256_file(p) if p.is_file() else "MISSING"
        except OSError as exc:
            out[str(p)] = f"ERROR:{type(exc).__name__}"
    return out


def _compare_snapshot(before: dict[str, str], after: dict[str, str]) -> dict:
    problems = []
    for path, digest in before.items():
        if after.get(path) != digest:
            if after.get(path) == "MISSING":
                problems.append(f"{path} disappeared")
            elif digest == "MISSING":
                problems.append(f"{path} appeared")
            else:
                problems.append(f"{path} content changed")
    return {"unchanged": not problems, "problems": problems,
            "files_checked": len(before)}


# ------------------------------------------------------------------ markdown

def _fmt(value, digits=3):
    try:
        x = float(value)
    except (TypeError, ValueError):
        return "n/a"
    return f"{x:.{digits}g}" if math.isfinite(x) else "n/a"


def _markdown(payload: dict) -> str:
    c = payload["cohort"]
    ctx = payload["source_assumption_context"]
    lines = [
        "# Source fidelity / source context (S6, bo-study-v1.1)",
        "",
        f"- generated: `{payload['generated_utc']}`",
        f"- config: `{c['config']}`",
        f"- **rows: {c['rows']}** ({c['unique_design_hash']} unique design hashes; "
        f"{c['screen_vs_verify']['screen']} screen / "
        f"{c['screen_vs_verify']['verify']} verify)",
        f"- with balloon arrays: **{c['with_balloon']}**; with throat-impedance: "
        f"**{c['with_z']}**",
        f"- verify pairing: {c['pairing_status_counts']}",
        f"- verify runs found: {c['verify_runs_found']} "
        f"({', '.join(c['verify_runs']) or 'none'})",
        f"- fidelity resolver: {c['fidelity_resolver']}",
        "",
        "## Frozen source-assumption context",
        "",
        f"- source: {ctx['source_model']} ({ctx['excitation']})",
        f"- **f11 = {ctx['f11_hz']:.0f} Hz** — {ctx['f11_statement']}",
        f"- band {ctx['band_hz'][0]:.0f}-{ctx['band_hz'][1]:.0f} Hz, f0 "
        f"{ctx['f0_hz']:.0f} Hz",
        f"- **loading weight = {ctx['loading_weight']:.1f}** — "
        f"{ctx['loading_weight_statement']}",
        f"- size/frequency confounding: {ctx['size_frequency_confounding_note']}",
        "",
        "## DI source",
        "",
        f"- {c['di_source_counts']}",
        "",
        "## Verify pairing",
        "",
        f"- run provenance: {c['run_provenance_counts']}",
        f"- pairing unavailable reasons: {c['pairing_unavailable_reasons'] or 'none'}",
        "",
        "| design_hash | fidelity | physical_solve_id | pairing | run |",
        "|---|---|---|---|---|",
    ]
    for card in sorted(payload["designs"],
                       key=lambda d: (d["design_hash"], d["fidelity"] or "")):
        pair = card.get("verify_pairing") or {}
        lines.append(
            f"| `{card['design_hash']}` | {card.get('fidelity') or 'unknown'} | "
            f"`{card.get('physical_solve_id') or '—'}` | "
            f"{pair.get('status') or 'unknown'} | {pair.get('run_id') or '—'} |")
    lines += [
        "",
        "## Per-design cards",
        "",
        "| design_hash | shard/row | fidelity | di_source | W×H×D mm | balloon | z | "
        "pairing |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for card in sorted(payload["designs"],
                       key=lambda d: (d["design_hash"], d["fidelity"] or "")):
        size = card["physical_size"]
        pair = card.get("verify_pairing") or {}
        dims = (f"{_fmt(size['mouth_w_mm'])}×{_fmt(size['mouth_h_mm'])}×"
                f"{_fmt(size['depth_mm'])}")
        lines.append(
            f"| `{card['design_hash']}` | {card.get('shard')}/{card.get('row')} | "
            f"{card.get('fidelity') or 'unknown'} | {card.get('di_source') or 'unknown'} | "
            f"{dims} | {card['missingness']['balloon'].get('present')} | "
            f"{card['missingness']['z'].get('present')} | "
            f"{pair.get('status') or 'unknown'} |")
    lines += ["", "## Offline-scores join", "",
              f"- matched design hashes: {c['offline_scores_rows_matched']} / "
              f"{c['rows']}",
              f"- exposed rows in the R0 artifact: {c['offline_scores_rows_in_artifact']} "
              f"(reported scored: {c['offline_scores_reported_scored']})", "",
              "## Limitations", ""]
    lines += [f"- {item}" for item in payload.get("limitations") or []]
    lines.append("")
    return "\n".join(lines)


def write_outputs(out_dir: Path, payload: dict) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    jpath = out_dir / f"{TOOL}.json"
    mpath = out_dir / f"{TOOL}.md"
    jpath.write_text(json.dumps(_clean(payload), indent=1, allow_nan=False,
                                sort_keys=True), encoding="utf-8")
    mpath.write_text(_markdown(payload), encoding="utf-8")
    return {"json": str(jpath), "md": str(mpath)}


# ------------------------------------------------------------------ run

def analyse(*, scores: Path, catalog: Path, dataset: Path, runs: Path, brief: Path,
            out: Path | None = None) -> dict:
    """Build the source-fidelity payload (read-only; ``out`` only affects the source guard)."""
    scores = Path(scores)
    catalog = Path(catalog)
    dataset = Path(dataset)
    runs = Path(runs)
    brief = Path(brief)

    # Read the three identity inputs and hash the exact bytes read.
    catalog_rows = load_catalog(catalog)
    score_artifact = load_scores(scores)
    brief_data = load_brief(brief)
    identity_snapshot = {
        str(catalog): _sha256_file(catalog),
        str(scores): _sha256_file(scores),
        str(brief): _sha256_file(brief) if brief.is_file() else "MISSING",
    }

    native_rows = select_native_rows(catalog_rows)
    score_rows = (score_artifact.get("rows") or []) if isinstance(score_artifact, dict) else []
    scores_by_hash = {}
    for sr in score_rows:
        dh = sr.get("design_hash")
        if dh:
            scores_by_hash[str(dh)] = sr

    shard_ids = [_shard_of(r) for r in native_rows]
    shards = read_shard_table(dataset, shard_ids)

    target_keys = {(str(r.get("design_hash") or ""), str(r.get("mesh_hash") or ""),
                    str(r.get("solve_hash") or "")) for r in native_rows}
    run_index = build_run_index(runs, target_keys)

    read_files = [catalog, scores, brief] + [s["path"] for s in shards.values()]
    npz_paths = [dataset / f"shard-{_shard_of(r):04d}" / f"rec-{_as_int(r.get('row')):04d}.npz"
                 for r in native_rows]
    read_files += npz_paths
    read_files += [runs / rel for rel in (run_index.get("files") or {})]
    before = _snapshot_paths(read_files)

    fidelity_mod, fidelity_error = _load_fidelity_resolver()

    cards: list[dict] = []
    for row in native_rows:
        shard = _shard_of(row)
        row_index = _as_int(row.get("row"))
        meta = None
        if shard is not None and row_index is not None:
            shard_entry = shards.get(shard) or {}
            rows = shard_entry.get("rows") or []
            if 0 <= row_index < len(rows):
                meta = rows[row_index]
        npz_path = dataset / f"shard-{shard:04d}" / f"rec-{row_index:04d}.npz"
        npz = _npz_summary(npz_path)
        dh = str(row.get("design_hash") or "")
        cards.append(_card_from_row(row, meta, npz, scores_by_hash.get(dh), brief_data))

    resolve_pairing(cards, run_index, runs, fidelity_mod, fidelity_error)
    for card in cards:
        card.pop("_key", None)

    after = _snapshot_paths(read_files)
    source_guard = _compare_snapshot(before, after)
    source_guard["scope"] = ("catalog, scores, brief, the dataset shards/npz read for the "
                             "cohort, and run ndjson files whose rows informed provenance; "
                             "the live queue may append to unrelated run directories")
    if identity_snapshot[str(catalog)] != before.get(str(catalog)) or \
            identity_snapshot[str(scores)] != before.get(str(scores)):
        source_guard["unchanged"] = False
        source_guard["problems"].append(
            "an identity input changed between the initial read and the guard snapshot")

    brief_weights = brief_data.get("weights") if isinstance(brief_data, dict) else None
    brief_target = brief_data.get("target") if isinstance(brief_data, dict) else None
    if not isinstance(brief_weights, dict):
        brief_weights = {}
    if not isinstance(brief_target, dict):
        brief_target = {}
    loading_weight = _as_float(brief_weights.get("load"))

    payload = {
        "tool": TOOL,
        "schema_version": SCHEMA_VERSION,
        "protocol": PROTOCOL,
        "generated_utc": _utc_now(),
        "read_only": True,
        "task_identity": {
            "config": NATIVE_CONFIG,
            "brief_name": brief_data.get("name"),
            "brief_path": str(brief),
            "brief_sha256": identity_snapshot.get(str(brief)),
            "objective_version": ((brief_data.get("objective") or {}).get("version")
                                  if isinstance(brief_data.get("objective"), dict) else None),
            "weights": brief_weights,
            "tolerances": ((brief_data.get("objective") or {}).get("tolerances")
                           if isinstance(brief_data.get("objective"), dict) else None),
            "band_hz": [_as_float(brief_target.get("band_lo_hz")),
                        _as_float(brief_target.get("band_hi_hz"))],
            "f0_hz": _as_float(brief_target.get("f0_hz")),
        },
        "inputs": {
            "scores": str(scores),
            "catalog": str(catalog),
            "dataset": str(dataset),
            "runs": str(runs),
            "brief": str(brief),
        },
        "source_assumption_context": dict(SOURCE_ASSUMPTION_CONTEXT,
                                          loading_weight_from_brief=loading_weight,
                                          loading_weight_consistent=(loading_weight == 0.0)),
        "cohort": _cohort_summary(cards, score_artifact, run_index, fidelity_error),
        "designs": cards,
        "source_guard": source_guard,
        "snapshot": {
            "catalog": {str(catalog): identity_snapshot[str(catalog)]},
            "scores": {str(scores): identity_snapshot[str(scores)]},
            "brief": {str(brief): identity_snapshot[str(brief)]},
            "dataset_shards": {
                str(s["path"]): {"sha256": s["sha256"], "size": s["size"],
                                 "exists": s["exists"]}
                for s in shards.values()},
            "npz": {str(p): before.get(str(p)) for p in npz_paths},
            "run_ndjson": {str(runs / rel): rec
                           for rel, rec in (run_index.get("files") or {}).items()},
        },
        "limitations": [
            "Coverage is the current S0 catalog native cohort; the parent joins by "
            "design_hash. The R0 artifact embeds only its 50-row display subset while its "
            "counts report 200 scored rows, so offline_score status is attached only where "
            "the artifact exposes a design_hash.",
            "run_id is empty on every native catalog row; run provenance is recovered only "
            "by exact (design_hash, mesh_hash, solve_hash) match in run ndjson. A physical "
            "key found in multiple runs is reported as ambiguous, never assigned.",
            "Verify pairing is asserted only for rows whose verify ndjson exists in the same "
            "run as the screen counterpart. The dataset has no verify_of field; screen rows "
            "with no verify row stay 'no_verify_row'.",
            "There is no per-design B2 geometry-descriptor index; physical size uses stored "
            "design parameters (morph_width_mm, morph_height_mm, L_mm), which are nominal "
            "morph targets, not a measured mouth or an acoustic size law.",
            "Loading weight is 0: no loading, efficiency, distortion or maximum-SPL claims.",
            "Above f11 the uniform-piston source is a geometry comparison; the size/frequency "
            "confounding stays explicit and uncorrected.",
        ],
    }
    if out is not None and source_guard["unchanged"]:
        payload["outputs"] = write_outputs(Path(out), payload)
    return payload


# ------------------------------------------------------------------ CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Read-only S6 source-fidelity cards for the native ATH cohort")
    ap.add_argument("--scores", type=Path, default=DEFAULT_SCORES)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    ap.add_argument("--brief", type=Path, default=DEFAULT_BRIEF)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    for name in ("scores", "catalog", "dataset", "runs"):
        path = getattr(args, name)
        if not Path(path).exists():
            print(f"error: --{name} {path} does not exist", file=sys.stderr)
            return 2
    out = Path(args.out).resolve()
    for root_name in ("dataset", "runs"):
        try:
            if out.is_relative_to(Path(getattr(args, root_name)).resolve()):
                print(f"error: --out must not be inside the read-only {root_name} root",
                      file=sys.stderr)
                return 2
        except (OSError, ValueError):
            pass

    try:
        payload = analyse(scores=args.scores, catalog=args.catalog, dataset=args.dataset,
                          runs=args.runs, brief=args.brief, out=args.out)
    except Exception as exc:  # noqa: BLE001 - explicit nonzero on failure
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3

    if not payload["source_guard"]["unchanged"]:
        print("error: a read source changed during the read-only run", file=sys.stderr)
        for problem in payload["source_guard"]["problems"]:
            print(f"  {problem}", file=sys.stderr)
        return 4

    c = payload["cohort"]
    print(f"wrote {payload['outputs']['json']} and {payload['outputs']['md']}")
    print("COUNTS " + json.dumps({
        "rows": c["rows"], "unique_design_hash": c["unique_design_hash"],
        "with_balloon": c["with_balloon"], "with_z": c["with_z"],
        "screen": c["screen_vs_verify"]["screen"],
        "verify": c["screen_vs_verify"]["verify"],
        "pairing": c["pairing_status_counts"],
        "verify_runs_found": c["verify_runs_found"],
        "di_source": c["di_source_counts"],
    }, sort_keys=True))
    print(f"SOURCE_GUARD unchanged={payload['source_guard']['unchanged']} "
          f"files={payload['source_guard']['files_checked']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
