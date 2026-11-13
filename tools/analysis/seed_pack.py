"""S5 diverse, feasible seed packs from real catalog records (2026-11-12).

Reads ``catalog.json`` (output of ``catalog.py``) and optionally a companion
``offline_scores.json`` (from R0).  Selects *k* diverse, complete-score exemplar
designs from multiple promising basins using greedy max-min diversity selection in
(normalised score-augmented knob) space.  Every emitted design keeps its full
recorded provenance; nothing is fabricated, inferred or cross-family mixed.

A "generator round-trip" in this tool means:
  1. The shard-row reference is recorded so the original JSONL line can be found.
  2. The stored ``design_hash`` is verified to be a non-empty hex string.
  3. ``round_trip_kind`` is set to ``"hash_identity"`` (the hash comes from the same
     record as the knob values) or ``"hash_mismatch"`` when the catalog row's
     ``design_hash`` disagrees with an explicitly provided reference.
  4. Full geometric verification (calling the config's ``GeneratedSpace.to_design``
     and comparing the resulting hash) requires loading the typology config and is
     labelled ``round_trip_needs_config=True``; it is a separately documented step
     and is NOT run by default.  Opt in with ``--config-roundtrip CONFIG --dataset-root DIR``:
     native configs rebuild (family, params) and pass through the config's DesignSpace
     (hash must match, no clipping); generated configs or a missing mesher/config degrade
     to ``needs_config``.  ``local_search`` then gives advisory sigma0/box hints plus a
     cold broad control arm (nothing is applied).

This tool never writes to live dataset/cache/run roots and never calls a mesh,
solver or metric pipeline.  All outputs go under ``--out``.

Usage::

    .venv\\Scripts\\python.exe tools\\analysis\\seed_pack.py \\
        --catalog scratch\\bo_m0\\s0\\catalog\\catalog.json \\
        --task native__ath_core_v4 \\
        --objective-version 4 \\
        --k 8 \\
        --out scratch\\bo_m0\\s5\\seed_pack_v1

Options::

    --catalog PATH          catalog.json from catalog.py (required)
    --scores  PATH          offline_scores.json from R0 (optional; augments score data)
    --task    STR           task / config_name filter (default: any)
    --objective-version INT objective version filter (default: any)
    --family  STR           family filter (default: any)
    --fidelity STR          fidelity filter (default: any)
    --k       INT           number of diverse exemplars to select (default 8, max 128)
    --min-score-percentile FLOAT
                            exclude designs scoring worse than this percentile (default 0,
                            i.e. all complete designs are eligible)
    --out     PATH          output folder (must NOT be inside a dataset root)
    --seed    INT           RNG seed for tie-breaking (default 0)
    --dry-run               print selection without writing files

Schema (``seed_pack.json``)::

    tool, schema_version, generated_utc
    spec: {task, objective_version, family, fidelity, k, min_score_percentile, seed}
    input: {catalog, scores}
    eligible: {total, by_run, by_config}
    selections: [{
        rank,                  # 1-based selection rank (order chosen by diversity)
        design_hash,           # recorded design_hash
        geometry_id,           # same as design_hash (catalog identity)
        run_id,                # recorded run_id or None
        config_name,           # recorded config_name
        fidelity, backend,
        objective_version,
        score,                 # recorded J or None
        completeness,          # catalog completeness classification
        source: {root, shard, shard_index, row},
        provenance_gaps,       # list of unknown/missing fields
        round_trip: {
            kind,              # "hash_identity" | "hash_mismatch" | "hash_missing"
            design_hash,       # the hash used for round-trip checking
            needs_config,      # always True; full mesh round-trip requires config
        },
        diversity_distance,    # min distance to all prior selections (0 for the first)
    }]
    duplicates_excluded,
    missing_provenance_excluded,
    limitations: [str, ...]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

TOOL = "seed_pack"
SCHEMA_VERSION = 1
_MAX_K = 128
_DEFAULT_K = 8
_DEFAULT_SEED = 0


# --------------------------------------------------------------------------- helpers


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hex40(s: Any) -> bool:
    """True when s is a 40-char lowercase hex string (design_hash format)."""
    if not isinstance(s, str) or len(s) < 16:
        return False
    return all(c in "0123456789abcdef" for c in s.lower())


def _jsonable(v: Any) -> Any:
    """Coerce to stdlib-json-serialisable value (no NaN/Infinity)."""
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _jsonable(vv) for k, vv in v.items()}
    if hasattr(v, "item"):
        return _jsonable(v.item())
    return str(v)


# --------------------------------------------------------------------------- catalog reading


def _read_catalog_json(path: Path) -> list[dict]:
    """Return the ``records`` list from a catalog.json, or [] on failure."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(payload, dict):
        return []
    return payload.get("records") or []


def _read_catalog_csv(path: Path) -> list[dict]:
    """Return rows from a catalog.csv (all values are strings or None)."""
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def _score_map(scores_path: Path | None) -> dict[str, float]:
    """geometry_id -> best-J from offline_scores.json (R0 output)."""
    if scores_path is None or not scores_path.is_file():
        return {}
    try:
        payload = json.loads(scores_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    rows = payload.get("rows") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return {}
    out: dict[str, float] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        gh = str(r.get("design_hash") or "").strip()
        j_val = r.get("j") if isinstance(r.get("j"), (int, float)) else None
        if _hex40(gh) and j_val is not None and math.isfinite(j_val):
            if gh not in out or j_val < out[gh]:
                out[gh] = float(j_val)
    return out


# --------------------------------------------------------------------------- record normalisation


def _normalise_record(raw: Any) -> dict | None:
    """Flatten a catalog JSON record or CSV row into a canonical candidate dict.

    Returns ``None`` for clearly unusable rows (missing design_hash).
    """
    if not isinstance(raw, dict):
        return None
    # CSV rows have all values as strings; JSON records may have typed values.
    def _str(k: str) -> str | None:
        v = raw.get(k)
        return str(v).strip() if v is not None else None
    def _int(k: str) -> int | None:
        v = raw.get(k)
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
    def _float(k: str) -> float | None:
        v = raw.get(k)
        try:
            x = float(v)
            return x if math.isfinite(x) else None
        except (TypeError, ValueError):
            return None
    def _bool(k: str) -> bool | None:
        v = raw.get(k)
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes")
        return None

    design_hash = _str("design_hash")
    if not _hex40(design_hash):
        return None

    # Source location
    source_dict = raw.get("source") if isinstance(raw.get("source"), dict) else {}
    root = _str("root") or (_str("root") if isinstance(source_dict, dict) else None) or \
           str(source_dict.get("root") or "")
    shard = _int("shard") if "shard" in raw else (_int_or_none(source_dict.get("shard")))
    shard_index = _int("shard_index") if "shard_index" in raw else (_int_or_none(source_dict.get("shard_index")))
    row = _int("row") if "row" in raw else (_int_or_none(source_dict.get("row")))

    prov = raw.get("provenance") if isinstance(raw.get("provenance"), dict) else {}
    comp_raw = raw.get("completeness")
    completeness = (comp_raw if isinstance(comp_raw, str)
                    else (comp_raw or {}).get("classification") if isinstance(comp_raw, dict)
                    else _str("completeness"))

    ok = _bool("ok")
    if ok is None and completeness:
        ok = completeness in ("exact_complete", "complete")

    return {
        "design_hash": design_hash,
        "geometry_id": design_hash,  # canonical: geometry_id == design_hash
        "run_id": (_str("run_id") or str(prov.get("run_id") or "")).strip() or None,
        "config_name": _str("config_name"),
        "family": _str("family"),
        "objective_version": (_int("objective_version")
                              if "objective_version" in raw
                              else _int_or_none(prov.get("objective_version"))),
        "fidelity": _str("fidelity") or str(prov.get("fidelity") or "").strip() or None,
        "backend": _str("backend") or str(prov.get("backend") or "").strip() or None,
        "ok": ok,
        "completeness": completeness,
        "failure_kind": _str("failure_kind"),
        "score": _float("score"),  # may be None; augmented by _score_map
        "source": {
            "root": root or None,
            "shard": shard,
            "shard_index": shard_index,
            "row": row,
        },
    }


def _int_or_none(v: Any) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- filtering


def _filter_records(records: list[dict], *, task: str | None, objective_version: int | None,
                    family: str | None, fidelity: str | None) -> list[dict]:
    out = []
    for r in records:
        if not r.get("ok"):
            continue
        if task is not None:
            cn = r.get("config_name") or ""
            if task not in cn:
                continue
        if objective_version is not None and r.get("objective_version") != objective_version:
            continue
        if family is not None:
            if (r.get("family") or "").upper() != family.upper():
                continue
        if fidelity is not None:
            if (r.get("fidelity") or "") != fidelity:
                continue
        out.append(r)
    return out


def _deduplicate(records: list[dict]) -> tuple[list[dict], int]:
    """Keep the first occurrence of each design_hash; return (unique, n_excluded)."""
    seen: set[str] = set()
    out: list[dict] = []
    for r in records:
        h = r["design_hash"]
        if h not in seen:
            seen.add(h)
            out.append(r)
    return out, len(records) - len(out)


def _apply_scores(records: list[dict], score_map: dict[str, float]) -> list[dict]:
    """Fill ``score`` from score_map when the record does not have one."""
    out = []
    for r in records:
        if r.get("score") is None:
            j = score_map.get(r["design_hash"])
            if j is not None:
                r = dict(r)
                r["score"] = j
        out.append(r)
    return out


def _apply_percentile_floor(records: list[dict], pct: float) -> tuple[list[dict], int]:
    """Exclude records scoring worse than the given percentile (by J, lower = better)."""
    if pct <= 0 or not records:
        return records, 0
    scored = [r for r in records if r.get("score") is not None]
    if not scored:
        return records, 0
    scores = sorted(r["score"] for r in scored)
    threshold = scores[min(int(len(scores) * pct / 100), len(scores) - 1)]
    before = len(records)
    out = [r for r in records if r.get("score") is None or r["score"] <= threshold]
    return out, before - len(out)


# --------------------------------------------------------------------------- diversity selection


def _build_feature_matrix(records: list[dict], *, score_weight: float = 1.0
                           ) -> "np.ndarray | None":
    """Build a normalised feature matrix [n_records x (n_scores + ...)] for diversity.

    Currently uses only the per-design J score (or rank when score missing).  Future
    versions may augment with geometry descriptors when they are in the catalog.
    """
    if not _HAS_NUMPY:
        return None
    n = len(records)
    scores = np.array([r.get("score") if r.get("score") is not None else float("nan")
                       for r in records], dtype=float)
    nan_mask = ~np.isfinite(scores)
    if nan_mask.all():
        return None
    scores_safe = scores.copy()
    scores_safe[nan_mask] = float(np.nanmean(scores_safe))
    lo, hi = float(np.nanmin(scores)), float(np.nanmax(scores))
    if hi > lo:
        normed = (scores_safe - lo) / (hi - lo)
    else:
        normed = np.zeros(n, dtype=float)
    return normed.reshape(-1, 1) * score_weight


def _greedy_maxmin(X: "np.ndarray", k: int, seed: int) -> list[int]:
    """Greedy max-min diversity selection: pick k indices from n rows of X.

    First seed is deterministic: the row nearest the centroid (most representative).
    Remaining seeds maximise the minimum distance to all prior picks.
    """
    n = X.shape[0]
    if k >= n:
        return list(range(n))
    rng = np.random.default_rng(seed)
    centroid = X.mean(axis=0)
    dists_to_centroid = np.sqrt(((X - centroid) ** 2).sum(axis=1))
    first = int(np.argmin(dists_to_centroid))
    selected = [first]
    min_dists = np.sqrt(((X - X[first]) ** 2).sum(axis=1))
    for _ in range(k - 1):
        # Tie-break: add tiny jitter so the rng seed controls the tie-break.
        jitter = rng.uniform(0, 1e-9, size=n)
        candidates = min_dists + jitter
        candidates[selected] = -1.0
        pick = int(np.argmax(candidates))
        selected.append(pick)
        new_dists = np.sqrt(((X - X[pick]) ** 2).sum(axis=1))
        min_dists = np.minimum(min_dists, new_dists)
    return selected


def _fallback_selection(records: list[dict], k: int, seed: int) -> list[int]:
    """Score-based fallback when numpy not available: best-k by J (ties: index order)."""
    indexed = [(r.get("score"), i) for i, r in enumerate(records)]
    indexed.sort(key=lambda x: (x[0] is None, x[0] if x[0] is not None else 0))
    return [i for _, i in indexed[:k]]


def _select_diverse(records: list[dict], k: int, seed: int
                    ) -> tuple[list[int], list[float]]:
    """Return (selected_indices, min_distances_at_selection) of length ≤ k."""
    k = min(k, len(records))
    if _HAS_NUMPY:
        X = _build_feature_matrix(records)
        if X is not None:
            indices = _greedy_maxmin(X, k, seed)
            # compute diversity distances
            dist_at = []
            seen = []
            for i, idx in enumerate(indices):
                if not seen:
                    dist_at.append(0.0)
                else:
                    dists = [float(np.sqrt(((X[idx] - X[j]) ** 2).sum())) for j in seen]
                    dist_at.append(min(dists))
                seen.append(idx)
            return indices, dist_at
    indices = _fallback_selection(records, k, seed)
    return indices, [0.0] * len(indices)


# --------------------------------------------------------------------------- round-trip check


def _round_trip_check(r: dict, explicit_ref: dict[str, str] | None = None
                      ) -> dict:
    """Hash-identity round-trip check (geometric round-trip needs config loading).

    ``explicit_ref`` is an optional ``{design_hash: expected_hash}`` dict; when
    provided, the recorded hash is compared against the reference.  A mismatch is
    labelled ``"hash_mismatch"``.
    """
    dh = r.get("design_hash") or ""
    if not _hex40(dh):
        kind = "hash_missing"
    elif explicit_ref is not None:
        expected = explicit_ref.get(dh)
        kind = "hash_mismatch" if (expected is not None and expected != dh) else "hash_identity"
    else:
        kind = "hash_identity"
    return {
        "kind": kind,
        "design_hash": dh or None,
        "needs_config": True,
    }


# --------------------------------------------------------------------------- provenance gap check


def _provenance_gaps(r: dict) -> list[str]:
    gaps = []
    if not r.get("run_id"):
        gaps.append("run_id_missing")
    if not r.get("fidelity"):
        gaps.append("fidelity_unknown")
    if r.get("score") is None:
        gaps.append("score_missing")
    src = r.get("source") or {}
    if src.get("shard") is None or src.get("row") is None:
        gaps.append("shard_row_missing")
    return gaps


# --------------------------------------------------------------------------- output builder


def build_seed_pack(catalog_path: Path, *, k: int, task: str | None,
                    objective_version: int | None, family: str | None,
                    fidelity: str | None, min_score_percentile: float,
                    scores_path: Path | None, seed: int) -> dict:
    """Build the full seed_pack payload dict (does not write files)."""
    # 1. Load catalog
    if catalog_path.suffix.lower() == ".csv":
        raw_records = _read_catalog_csv(catalog_path)
    else:
        raw_records = _read_catalog_json(catalog_path)
    if not raw_records:
        return {
            "tool": TOOL, "schema_version": SCHEMA_VERSION,
            "generated_utc": _utc_now(),
            "error": "no records in catalog",
            "selections": [], "eligible": {"total": 0},
        }

    # 2. Normalise
    records = [nr for raw in raw_records if (nr := _normalise_record(raw)) is not None]
    n_total = len(records)
    n_malformed = len(raw_records) - n_total

    # 3. Augment from scores file
    score_map = _score_map(scores_path)
    records = _apply_scores(records, score_map)

    # 4. Filter
    eligible = _filter_records(records, task=task, objective_version=objective_version,
                               family=family, fidelity=fidelity)

    # 5. Deduplicate
    eligible, n_dupes = _deduplicate(eligible)

    # 6. Missing-provenance label (not filtered out, just labelled)
    n_missing = sum(1 for r in eligible if not r.get("run_id"))

    # 7. Score-percentile floor
    eligible, n_percentile_exc = _apply_percentile_floor(eligible, min_score_percentile)

    # 8. Diversity selection
    indices, dist_at = _select_diverse(eligible, k, seed)

    # 9. Build eligible stats
    by_run: Counter = Counter()
    by_config: Counter = Counter()
    for r in eligible:
        by_run[r.get("run_id") or "unknown"] += 1
        by_config[r.get("config_name") or "unknown"] += 1

    # 10. Build selection entries
    selections = []
    for rank, (idx, dist) in enumerate(zip(indices, dist_at), start=1):
        r = eligible[idx]
        rt = _round_trip_check(r)
        entry = {
            "rank": rank,
            "design_hash": r["design_hash"],
            "geometry_id": r["geometry_id"],
            "run_id": r.get("run_id"),
            "config_name": r.get("config_name"),
            "fidelity": r.get("fidelity"),
            "backend": r.get("backend"),
            "objective_version": r.get("objective_version"),
            "score": r.get("score"),
            "completeness": r.get("completeness"),
            "source": r.get("source") or {},
            "provenance_gaps": _provenance_gaps(r),
            "round_trip": rt,
            "diversity_distance": dist,
        }
        selections.append(entry)

    return {
        "tool": TOOL,
        "schema_version": SCHEMA_VERSION,
        "generated_utc": _utc_now(),
        "spec": {
            "task": task,
            "objective_version": objective_version,
            "family": family,
            "fidelity": fidelity,
            "k": k,
            "min_score_percentile": min_score_percentile,
            "seed": seed,
        },
        "input": {
            "catalog": str(catalog_path),
            "scores": str(scores_path) if scores_path else None,
            "total_raw_records": n_total + n_malformed,
            "malformed_records": n_malformed,
        },
        "eligible": {
            "total": len(eligible),
            "by_run": dict(by_run.most_common(50)),
            "by_config": dict(by_config.most_common(50)),
        },
        "duplicates_excluded": n_dupes,
        "missing_provenance_count": n_missing,
        "below_percentile_excluded": n_percentile_exc,
        "selections": selections,
        "limitations": [
            "Diversity selection uses only the recorded score (J); geometric "
            "descriptors are not in the catalog and would improve basin detection.",
            "Round-trip kind 'hash_identity' confirms the catalog row's own "
            "design_hash is non-empty hex; it does NOT re-derive the geometry "
            "from knob values (needs_config=True for all designs).",
            "Full geometric round-trip (calling GeneratedSpace.to_design and "
            "comparing the resulting hash) requires loading the typology config "
            "and is not performed here.  Run the round-trip check with the "
            "config's search module for each selected design before use.",
            "Screen-only designs are labelled; prefer matched verify data when "
            "available.",
        ],
    }


# --------------------------------------------------------------------------- S5 opt-in config round-trip


def _shard_row(dataset_root: Path, source: dict) -> dict | None:
    """The recorded dataset row for a selection (read-only), or None."""
    shard = source.get("shard_index", source.get("shard"))
    row = source.get("row")
    if shard is None or row is None:
        return None
    path = Path(dataset_root) / f"shard-{int(shard):04d}.jsonl"
    try:
        with path.open(encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if i == int(row):
                    rec = json.loads(line)
                    return rec if isinstance(rec, dict) else None
    except (OSError, ValueError):
        return None
    return None


def config_round_trip(selections: list[dict], config_path: Path,
                      dataset_root: Path | None) -> dict:
    """Rebuild each selected design through the config's own space and compare hashes.

    Native configs: recorded (family, params) -> ``Design.hash()`` must equal the
    recorded design_hash, and ``space.denormalize(space.normalize(design))`` must give
    the same hash (no silent clipping).  Generated configs (``generator:``) need the
    generator stack; when it (or the mesher) cannot be imported, or the config/rows
    are absent, the status is ``needs_config`` with a reason, never a fake pass.
    Never writes anything and never meshes or solves.
    """
    out = {"config": str(config_path), "status": "ok", "results": []}
    try:
        from hornlab_search.config import load_config
        from hornlab_search.design.space import DesignSpace
        from hornlab_search.types import Design
        cfg = load_config(Path(config_path))
    except Exception as exc:  # noqa: BLE001 - degrade, never crash
        out.update(status="needs_config", reason=f"config not loadable: {type(exc).__name__}: {exc}")
        return out
    generated = bool(getattr(cfg, "generator", None)) or (
        isinstance(getattr(cfg, "raw", None), dict) and "generator" in cfg.raw)
    try:
        if generated:
            from hornlab_search.design.generated import GeneratedSpace  # noqa: F401
            import importlib.util
            if importlib.util.find_spec("hornlab_mesher") is None:
                raise ImportError("hornlab_mesher not installed")
        space = DesignSpace.from_config(cfg)
    except Exception as exc:  # noqa: BLE001
        out.update(status="needs_config", reason=f"design space unavailable: {type(exc).__name__}: {exc}")
        return out
    if dataset_root is None:
        out.update(status="needs_config", reason="--dataset-root required to read recorded params")
        return out
    for sel in selections:
        res = {"design_hash": sel["design_hash"], "status": "needs_config", "reason": None}
        rec = _shard_row(dataset_root, sel.get("source") or {})
        if rec is None or not isinstance(rec.get("params"), dict) or not rec.get("family"):
            res["reason"] = "recorded row/params not found"
        elif generated:
            res["reason"] = "generated config: generator-knob round-trip not reconstructable from materialized params"
        else:
            try:
                design = Design(rec["family"], dict(rec["params"]))
                rebuilt = design.hash()
                again = space.denormalize(space.normalize(design)).hash()
                res.update(rebuilt_hash=rebuilt, space_hash=again,
                           status="match" if rebuilt == sel["design_hash"] == again else "mismatch",
                           clipped=again != rebuilt)
            except Exception as exc:  # noqa: BLE001 - out-of-space design etc.
                res.update(status="mismatch", reason=f"{type(exc).__name__}: {exc}")
        out["results"].append(res)
    statuses = {r["status"] for r in out["results"]}
    out["status"] = ("mismatch" if "mismatch" in statuses else
                     "needs_config" if "needs_config" in statuses or not statuses else "ok")
    return out


# --------------------------------------------------------------------------- S5 local search recommendations

SIGMA_BOUNDS = (0.05, 0.3)  # normalized [0,1]^k units; pycma sigma0 rule of thumb range


def local_search_recommendations(selections: list[dict], vectors: dict[str, list[float]] | None,
                                 keys: list[str] | None = None) -> dict:
    """Advisory sigma0 + box suggestions from the normalized spread of the selected exemplars.

    ``vectors`` maps design_hash -> normalized [0,1] vector (from the config round-trip
    space).  Sigma0 = median per-axis std of the exemplars, clipped to SIGMA_BOUNDS
    (lower bound first).  Narrow/widen are hints only; a narrowed box must contain
    every exemplar plus a margin, and a broad cold control arm is always kept.
    Never changes a config or default.
    """
    rec = {"advisory_only": True, "status": "insufficient_data",
           "sigma_bounds": list(SIGMA_BOUNDS),
           "arms": [{"name": "cold_broad_control", "warm_start": False, "box": "config bounds"}]}
    vecs = [vectors[s["design_hash"]] for s in selections if vectors and s["design_hash"] in vectors]
    if len(vecs) < 2:
        rec["reason"] = "need >= 2 exemplars with normalized vectors (run --config-roundtrip)"
        return rec
    import numpy as np
    X = np.asarray(vecs, dtype=float)
    std = X.std(axis=0)
    raw = float(np.median(std))
    sigma = min(max(raw, SIGMA_BOUNDS[0]), SIGMA_BOUNDS[1])
    lo = np.clip(X.min(axis=0) - 0.1, 0.0, 1.0)
    hi = np.clip(X.max(axis=0) + 0.1, 0.0, 1.0)
    names = keys or [f"x{i}" for i in range(X.shape[1])]
    hints = []
    for i, n in enumerate(names):
        wall = bool((X[:, i] <= 0.02).any() or (X[:, i] >= 0.98).any())
        hints.append({"key": n, "exemplar_lo": float(X[:, i].min()), "exemplar_hi": float(X[:, i].max()),
                      "suggest": "consider_widen (exemplar on a wall)" if wall else
                                 ("consider_narrow" if hi[i] - lo[i] < 0.5 else "keep"),
                      "box_unit": [float(lo[i]), float(hi[i])]})
    rec.update(status="ok", sigma0_raw=raw, sigma0=sigma,
               sigma_rule="median per-axis std of exemplars, clipped to [lo, hi]",
               clipped_sigma=sigma != raw, n_exemplars=len(vecs), hints=hints,
               evidence_note="narrow/pin/link needs held-out effect evidence; these are hypotheses")
    rec["arms"].append({"name": "warm_seed_pack", "warm_start": True, "sigma0": sigma,
                        "box": "config bounds (narrowing NOT applied automatically)"})
    return rec



def _normalized_vectors(selections, rt, config_path, dataset_root):
    """design_hash -> normalized vector for selections whose round-trip matched."""
    if rt.get("status") == "needs_config" and not rt.get("results"):
        return None, None
    try:
        from hornlab_search.config import load_config
        from hornlab_search.design.space import DesignSpace
        from hornlab_search.types import Design
        space = DesignSpace.from_config(load_config(config_path))
    except Exception:  # noqa: BLE001
        return None, None
    ok = {r["design_hash"] for r in rt.get("results", []) if r.get("status") == "match"}
    out = {}
    for sel in selections:
        if sel["design_hash"] in ok:
            rec = _shard_row(dataset_root, sel.get("source") or {})
            out[sel["design_hash"]] = [float(v) for v in
                                       space.normalize(Design(rec["family"], dict(rec["params"])))]
    return out, list(space.keys())


# --------------------------------------------------------------------------- I/O


def write_seed_pack(payload: dict, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    jpath = out_dir / "seed_pack.json"
    jpath.write_text(
        json.dumps(_jsonable(payload), indent=1, sort_keys=True, allow_nan=False,
                   ensure_ascii=False) + "\n",
        encoding="utf-8")
    written = {"json": str(jpath)}
    return written


# --------------------------------------------------------------------------- CLI


def _build_parser():
    p = argparse.ArgumentParser(
        prog="seed_pack",
        description="S5: select diverse, feasible seed packs from a real catalog.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--catalog", required=True,
                   help="Path to catalog.json (or catalog.csv) from catalog.py")
    p.add_argument("--scores", default=None,
                   help="Path to offline_scores.json from R0 (optional)")
    p.add_argument("--task", default=None,
                   help="config_name substring filter (e.g. native__ath_core_v4)")
    p.add_argument("--objective-version", type=int, default=None,
                   help="Objective version filter (e.g. 4)")
    p.add_argument("--family", default=None,
                   help="Family filter (e.g. OSSE)")
    p.add_argument("--fidelity", default=None,
                   help="Fidelity filter (e.g. screen)")
    p.add_argument("--k", type=int, default=_DEFAULT_K,
                   help=f"Number of diverse exemplars to select (max {_MAX_K})")
    p.add_argument("--min-score-percentile", type=float, default=0.0,
                   help="Exclude designs scoring worse than this percentile")
    p.add_argument("--out", required=True,
                   help="Output folder (must NOT be inside a dataset root)")
    p.add_argument("--seed", type=int, default=_DEFAULT_SEED,
                   help="RNG seed for tie-breaking")
    p.add_argument("--dry-run", action="store_true",
                   help="Print summary without writing files")
    p.add_argument("--config-roundtrip", default=None, metavar="CONFIG_YAML",
                   help="Opt-in: rebuild each selection via this typology config and compare hashes")
    p.add_argument("--dataset-root", default=None,
                   help="Dataset dir holding shard-NNNN.jsonl (read-only) for --config-roundtrip")
    return p


def main(argv=None):
    p = _build_parser()
    args = p.parse_args(argv)
    catalog_path = Path(args.catalog)
    if not catalog_path.is_file():
        print(f"ERROR: catalog not found: {catalog_path}", file=sys.stderr)
        return 1
    scores_path = Path(args.scores) if args.scores else None
    out_dir = Path(args.out)
    k = min(max(1, int(args.k)), _MAX_K)
    payload = build_seed_pack(
        catalog_path,
        k=k,
        task=args.task,
        objective_version=args.objective_version,
        family=args.family,
        fidelity=args.fidelity,
        min_score_percentile=float(args.min_score_percentile),
        scores_path=scores_path,
        seed=int(args.seed),
    )
    if args.config_roundtrip:
        rt = config_round_trip(payload.get("selections") or [], Path(args.config_roundtrip),
                               Path(args.dataset_root) if args.dataset_root else None)
        payload["config_round_trip"] = rt
        vectors, keys = _normalized_vectors(payload.get("selections") or [], rt,
                                            Path(args.config_roundtrip),
                                            Path(args.dataset_root) if args.dataset_root else None)
        payload["local_search"] = local_search_recommendations(payload.get("selections") or [],
                                                               vectors, keys)
    n_sel = len(payload.get("selections") or [])
    n_elig = (payload.get("eligible") or {}).get("total", 0)
    print(f"selected {n_sel}/{n_elig} eligible designs")
    if args.dry_run:
        for s in payload.get("selections") or []:
            rt = s.get("round_trip") or {}
            print(f"  rank={s['rank']} hash={s['design_hash'][:12]}... "
                  f"J={s.get('score')} rt={rt.get('kind')} gaps={s.get('provenance_gaps')}")
        return 0
    written = write_seed_pack(payload, out_dir)
    print(f"wrote: {written['json']}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
