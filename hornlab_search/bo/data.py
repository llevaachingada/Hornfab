"""Pure data adapters for advisory Bayesian proposals (protocol bo-study-v1.1, B2).

Two responsibilities, both offline and backend-free:

* :func:`build_training_set` — deterministic min/cap selection with explicit observation IDs,
  geometry deduplication, ``Y = -J`` (no scorer math, no fabricated ``J=1000`` rows), and a
  reproducible ``needs_initial_data`` preparation manifest below ``n_min``.
* :func:`build_candidate_pool` — a finite scrambled-Sobol candidate pool (default 4096) through
  the audited projection.  Every pool candidate gets only cheap materialization/schema/envelope/
  throat checks.  No mesh is built, no BEM/GPU call is made, and a candidate is explicitly labelled
  **"cheap-check-passed; mesh/acoustic eligibility unknown"**.

The module imports the mesher lazily inside :func:`materialize_geometry` / the pool, so the pure
training-set fixtures run with only numpy (+ scipy for the Sobol preparation).
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Mapping

import csv

import numpy as np

DEFAULT_N_MAX = 256
DEFAULT_ELITE_N = 64
N_MIN_FLOOR = 16
POOL_SIZE = 4096
POOL_STATUS_NOTE = "cheap-check-passed; mesh/acoustic eligibility unknown"
NEAR_DUPLICATE_TOL = 1e-6


class DataError(ValueError):
    """Base class for refused training/pool requests."""


class UnsupportedGeometryError(DataError):
    """A CAD/grid/non-star-shaped surface has no supported canonical radial representation."""


# ---------------------------------------------------------------------------- training set


@dataclass(frozen=True)
class TrainingObservation:
    """One explicitly eligible measurement used by :func:`build_training_set`.

    ``status`` must say the observation is complete; a solver/infra/gate failure is excluded by
    its typed status, never inferred from a large ``J``.  ``J`` is the frozen scalar objective
    value (lower is better); this module emits ``Y = -J`` for the model.
    """

    observation_id: str
    x: np.ndarray
    J: float
    status: str = "ok"
    eligible: bool = True
    geometry_hash: str | None = None
    solve_hash: str | None = None
    y_phys: tuple[float, ...] | None = None
    G: tuple[float, ...] | None = None


_ELIGIBLE_STATUS = frozenset({"ok", "complete", "success", "valid"})


def n_min_for(d: int) -> int:
    """``max(16, 2*(d+1))`` usable unique geometries (spec section 3.2)."""
    if d < 1:
        raise DataError(f"d must be >= 1, got {d}")
    return max(N_MIN_FLOOR, 2 * (int(d) + 1))


def _coerce_observation(row) -> TrainingObservation:
    if isinstance(row, TrainingObservation):
        return row
    if not isinstance(row, Mapping):
        raise DataError(f"observation must be a TrainingObservation or mapping, got {type(row)!r}")
    oid = row.get("observation_id", row.get("id"))
    if oid is None:
        raise DataError("observation is missing an observation_id/id")
    x = row.get("x", row.get("unit_vector", row.get("active_vector")))
    if x is None:
        raise DataError(f"observation {oid!r} is missing an active unit vector (x)")
    J = row.get("J", row.get("objective"))
    if J is None:
        raise DataError(f"observation {oid!r} is missing J")
    y_phys = row.get("y_phys", row.get("Y_phys"))
    G = row.get("G", row.get("g"))
    return TrainingObservation(
        observation_id=str(oid),
        x=np.asarray(x, dtype=float).reshape(-1),
        J=float(J),
        status=str(row.get("status", "ok")),
        eligible=bool(row.get("eligible", True)),
        geometry_hash=None if row.get("geometry_hash") is None else str(row["geometry_hash"]),
        solve_hash=None if row.get("solve_hash") is None else str(row["solve_hash"]),
        y_phys=None if y_phys is None else tuple(float(v) for v in y_phys),
        G=None if G is None else tuple(float(v) for v in G),
    )


def _valid_observation(obs: TrainingObservation, d: int) -> bool:
    if not obs.eligible or obs.status not in _ELIGIBLE_STATUS:
        return False
    if obs.x.size != d or not np.all(np.isfinite(obs.x)):
        return False
    return math.isfinite(float(obs.J))


def _maximin_select(candidates: list[TrainingObservation], selected: list[TrainingObservation],
                    k: int) -> list[TrainingObservation]:
    """Deterministic farthest-point selection; ties by observation id (spec 3.2)."""
    if k <= 0 or not candidates:
        return []
    cand_x = np.vstack([o.x for o in candidates])
    if selected:
        sel_x = np.vstack([o.x for o in selected])
        min_dist = np.min(
            np.linalg.norm(cand_x[:, None, :] - sel_x[None, :, :], axis=2), axis=1)
    else:
        min_dist = np.full(cand_x.shape[0], np.inf, dtype=float)
    taken = np.zeros(len(candidates), dtype=bool)
    chosen: list[TrainingObservation] = []
    for _ in range(min(k, len(candidates))):
        best = float(np.max(min_dist))
        tied = np.flatnonzero(min_dist >= best - 1e-12)
        pick = min((int(i) for i in tied),
                   key=lambda i: (candidates[i].observation_id, i))
        chosen.append(candidates[pick])
        taken[pick] = True
        min_dist[pick] = -np.inf
        d = np.linalg.norm(cand_x - cand_x[pick], axis=1)
        min_dist = np.minimum(min_dist, d)
    return chosen


def _sobol_points(d: int, n: int, seed: int) -> np.ndarray:
    """Scrambled Sobol points in [0,1]^d for the needs_initial_data preparation manifest."""
    if n <= 0:
        return np.empty((0, d), dtype=float)
    try:
        from scipy.stats import qmc
    except Exception:  # noqa: BLE001 - numpy fallback only for the preparation manifest
        rng = np.random.default_rng(int(seed))
        return rng.random((n, d))
    m = int(math.ceil(math.log2(max(1, n))))
    sampler = qmc.Sobol(d=d, scramble=True, seed=int(seed))
    return np.asarray(sampler.random_base2(m), dtype=float)[:n]


@dataclass(frozen=True)
class TrainingSet:
    """Frozen numeric training arrays plus reproducible selection IDs."""

    status: str                                  # "ok" | "needs_initial_data"
    d: int
    n: int
    X: np.ndarray | None
    J: np.ndarray | None
    Y: np.ndarray | None
    Y_phys: np.ndarray | None
    G: np.ndarray | None
    ids: tuple[str, ...]
    selected_ids: tuple[str, ...]
    excluded_ids: tuple[str, ...]
    elite_ids: tuple[str, ...]
    maximin_ids: tuple[str, ...]
    n_eligible: int
    n_unique: int
    n_min: int
    n_max: int
    active_keys: tuple[str, ...]
    projection_version: str | None
    preparation: dict | None
    meta: dict = field(default_factory=dict)

    def arrays(self) -> dict:
        return {"X": self.X, "J": self.J, "Y": self.Y, "Y_phys": self.Y_phys, "G": self.G}

    def manifest(self) -> dict:
        return {
            "status": self.status,
            "d": self.d,
            "n": self.n,
            "n_min": self.n_min,
            "n_max": self.n_max,
            "n_eligible": self.n_eligible,
            "n_unique": self.n_unique,
            "ids": list(self.ids),
            "selected_ids": list(self.selected_ids),
            "excluded_ids": list(self.excluded_ids),
            "elite_ids": list(self.elite_ids),
            "maximin_ids": list(self.maximin_ids),
            "active_keys": list(self.active_keys),
            "projection_version": self.projection_version,
            "preparation": self.preparation,
            "meta": dict(self.meta),
        }


def build_training_set(observations: Iterable, *, encoding=None, d: int | None = None,
                       n_max: int = DEFAULT_N_MAX, elite_n: int = DEFAULT_ELITE_N,
                       seed: int = 0) -> TrainingSet:
    """Select a deterministic training subset from *explicitly eligible* observations.

    ``n_min = max(16, 2*(d+1))``; below it the result is ``needs_initial_data`` with a
    reproducible scrambled-Sobol preparation manifest.  Above the 256 cap this keeps the lowest-J
    ``elite_n`` rows plus deterministic maximin-diversity rows from the remainder, ties by ID.
    """
    if encoding is not None:
        d = int(encoding.d)
        active_keys = tuple(encoding.active_keys)
        projection_version = getattr(encoding, "version", None)
    else:
        if d is None:
            raise DataError("build_training_set needs encoding= or d=")
        d = int(d)
        active_keys = tuple()
        projection_version = None
    if d < 1:
        raise DataError(f"d must be >= 1, got {d}")
    n_min = n_min_for(d)
    n_max = int(n_max)
    if n_max < 1:
        raise DataError(f"n_max must be >= 1, got {n_max}")

    raw = [_coerce_observation(row) for row in observations]
    # Historical vectors are already normalized by the audited projection. Never clip or
    # silently discard an otherwise eligible out-of-domain observation: it indicates a
    # mismatch between the snapshot and the current space and requires investigation.
    for obs in raw:
        if (obs.eligible and obs.status in _ELIGIBLE_STATUS and obs.x.size == d
                and np.all(np.isfinite(obs.x)) and math.isfinite(float(obs.J))
                and np.any((obs.x < 0.0) | (obs.x > 1.0))):
            raise DataError(f"observation {obs.observation_id!r} is outside the normalized unit box; historical clipping is forbidden")
    valid = [o for o in raw if _valid_observation(o, d)]
    # Physical uniqueness: repeated identical geometry/solve identities are not independent
    # observations (one cached solve cannot inflate independent evidence).
    by_identity: dict[tuple[str | None, str | None], TrainingObservation] = {}
    duplicates: list[str] = []
    for obs in valid:
        if obs.geometry_hash is None and obs.solve_hash is None:
            continue
        key = (obs.geometry_hash, obs.solve_hash)
        prior = by_identity.get(key)
        if prior is None:
            by_identity[key] = obs
        else:
            keep = obs if (obs.J, obs.observation_id) < (prior.J, prior.observation_id) else prior
            drop = prior if keep is obs else obs
            by_identity[key] = keep
            duplicates.append(drop.observation_id)
    if by_identity:
        seen_ids = {o.observation_id for o in by_identity.values()}
        unique = [o for o in valid
                  if (o.geometry_hash is None and o.solve_hash is None)
                  or o.observation_id in seen_ids]
    else:
        unique = list(valid)
    # A duplicate ID must not double-count even without a geometry/solve hash.
    deduped: dict[str, TrainingObservation] = {}
    for obs in unique:
        prior = deduped.get(obs.observation_id)
        if prior is None or (obs.J, obs.observation_id) < (prior.J, prior.observation_id):
            deduped[obs.observation_id] = obs
    unique = list(deduped.values())

    ordered = sorted(unique, key=lambda o: (float(o.J), o.observation_id))
    excluded = [o.observation_id for o in raw if o.observation_id not in
                {x.observation_id for x in unique}]
    excluded.extend(duplicates)

    if len(unique) < n_min:
        return TrainingSet(
            status="needs_initial_data", d=d, n=0, X=None, J=None, Y=None, Y_phys=None, G=None,
            ids=(), selected_ids=(), excluded_ids=tuple(sorted(set(excluded))),
            elite_ids=(), maximin_ids=(), n_eligible=len(valid), n_unique=len(unique),
            n_min=n_min, n_max=n_max, active_keys=active_keys,
            projection_version=projection_version,
            preparation={
                "method": "scrambled_sobol",
                "d": d,
                "seed": int(seed),
                "n_have": len(unique),
                "n_missing": int(n_min - len(unique)),
                "n_min": n_min,
                "points": _sobol_points(d, n_min - len(unique), seed).tolist(),
                "note": "no trained model exists below n_min; fill with legal observations",
            },
            meta={"eligible_ids": [o.observation_id for o in valid],
                  "n_duplicates_removed": len(duplicates)},
        )

    if len(ordered) <= n_max:
        selected = ordered
        elites, maximin = ordered, []
    else:
        elite_n = max(0, min(int(elite_n), n_max))
        elites = ordered[:elite_n]
        remaining = ordered[elite_n:]
        maximin = _maximin_select(remaining, elites, n_max - elite_n)
        selected = elites + maximin

    X = np.vstack([o.x for o in selected]).astype(np.float64)
    J = np.asarray([o.J for o in selected], dtype=np.float64).reshape(-1, 1)
    Y = -J
    y_phys = _stack_optional([o.y_phys for o in selected])
    G = _stack_optional([o.G for o in selected])
    selected_set = {o.observation_id for o in selected}
    excluded.extend(o.observation_id for o in unique if o.observation_id not in selected_set)
    return TrainingSet(
        status="ok", d=d, n=len(selected), X=X, J=J, Y=Y, Y_phys=y_phys, G=G,
        ids=tuple(o.observation_id for o in selected),
        selected_ids=tuple(o.observation_id for o in selected),
        excluded_ids=tuple(sorted(set(excluded))),
        elite_ids=tuple(o.observation_id for o in elites),
        maximin_ids=tuple(o.observation_id for o in maximin),
        n_eligible=len(valid), n_unique=len(unique), n_min=n_min, n_max=n_max,
        active_keys=active_keys, projection_version=projection_version, preparation=None,
        meta={"n_duplicates_removed": len(duplicates)},
    )


def _stack_optional(rows: list[tuple[float, ...] | None]) -> np.ndarray | None:
    if not rows or any(r is None for r in rows):
        return None
    widths = {len(r) for r in rows if r is not None}
    if len(widths) != 1:
        return None
    return np.asarray(rows, dtype=np.float64)


def make_pure_observations(d: int, n: int, *, seed: int = 0,
                           geometry_hashes: bool = True) -> list[TrainingObservation]:
    """Deterministic, no-sentinel fixture observations (a smooth quadratic objective).

    This is a *fixture*, not archive evidence.  ``J`` is a finite quadratic bowl; no row is
    fabricated as ``J=1000`` and no failure row is relabelled as an acoustic observation.
    """
    if d < 1 or n < 0:
        raise DataError("d must be >= 1 and n >= 0")
    rng = np.random.default_rng(int(seed))
    x = rng.random((int(n), int(d)))
    centre = np.full(int(d), 0.37, dtype=float)
    J = np.sum((x - centre) ** 2, axis=1) + 0.01
    out: list[TrainingObservation] = []
    for i in range(int(n)):
        gh = (hashlib.sha256(np.round(x[i], 8).tobytes()).hexdigest()[:16]
              if geometry_hashes else None)
        out.append(TrainingObservation(observation_id=f"fixture-{i:04d}", x=x[i], J=float(J[i]),
                                       status="ok", geometry_hash=gh))
    return out


# ---------------------------------------------------------------------------- native cohort


#: Reason codes for an honestly refused native archive row (never an invented value).
NATIVE_R_CATALOG_ROW_MISSING = "catalog_row_missing"
NATIVE_R_CONFIG_MISMATCH = "config_mismatch"
NATIVE_R_INCOMPLETE_SCORE = "incomplete_score"
NATIVE_R_NONFINITE_J = "nonfinite_J"
NATIVE_R_IDENTITY_MISSING = "identity_missing"
NATIVE_R_DATASET_ROW_MISSING = "dataset_row_missing"
NATIVE_R_RECORD_NOT_OK = "record_not_ok"
NATIVE_R_DESIGN_PARAMS_MISSING = "design_params_missing"
NATIVE_R_DESIGN_FAMILY_MISSING = "design_family_missing"
NATIVE_R_DESIGN_HASH_MISMATCH = "design_hash_mismatch"
NATIVE_R_ENCODE_REFUSED = "encode_refused"
NATIVE_R_NONFINITE_VECTOR = "nonfinite_vector"
NATIVE_R_MISSING_PROVENANCE = "missing_provenance"

NATIVE_REFUSAL_REASONS = {
    NATIVE_R_CATALOG_ROW_MISSING: "the S0 catalog has no row for this (root, shard, row)",
    NATIVE_R_CONFIG_MISMATCH: "the catalog/score row names a different config",
    NATIVE_R_INCOMPLETE_SCORE: "the score row is not exact_complete; it is not a training J",
    NATIVE_R_NONFINITE_J: "the score row has no finite exact J",
    NATIVE_R_IDENTITY_MISSING: "the score artifact does not carry the full identity triple",
    NATIVE_R_DATASET_ROW_MISSING: "the dataset shard line for this provenance is absent",
    NATIVE_R_RECORD_NOT_OK: "the stored dataset record is a failed evaluation (ok=false)",
    NATIVE_R_DESIGN_PARAMS_MISSING: "the stored record carries no design params",
    NATIVE_R_DESIGN_FAMILY_MISSING: "the stored record carries no design family",
    NATIVE_R_DESIGN_HASH_MISMATCH: "params do not reproduce the recorded design hash",
    NATIVE_R_ENCODE_REFUSED: "the bo encoding refused the historical params/geometry",
    NATIVE_R_NONFINITE_VECTOR: "the encoded active vector is not finite",
    NATIVE_R_MISSING_PROVENANCE: "the score row has no usable shard/row provenance",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_catalog_index(catalog_csv) -> dict:
    """``(root, shard_index, row) -> catalog row`` (same join as offline_scores).

    Only the numeric shard id and the zero-based row are keyed; both catalog export
    generations (``shard`` filename vs ``shard_index``) are accepted.
    """
    out: dict[tuple[str, str, str], dict] = {}
    with open(catalog_csv, encoding="utf-8", newline="") as fh:
        for rec in csv.DictReader(fh):
            shard_num = str(rec.get("shard_index") or "") or str(rec.get("shard") or "")
            out[(str(rec.get("root") or ""), shard_num, str(rec.get("row") or ""))] = rec
    return out


def _read_shard_metas(dataset_root, shard: int, cache: dict) -> dict[int, dict | None]:
    """Read one shard's record metadata read-only; never constructs a ``DatasetStore``."""
    if shard in cache:
        return cache[shard]
    path = Path(dataset_root) / f"shard-{int(shard):04d}.jsonl"
    rows: dict[int, dict | None] = {}
    if path.is_file():
        with open(path, "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows[i] = json.loads(line)
                except ValueError:
                    rows[i] = None
    cache[shard] = rows
    return rows


def build_native_training_set(config_path, *, scores_json, catalog_csv, limit=None,
                              dataset_root=None) -> TrainingSet:
    """Build a real :class:`TrainingSet` from the native ATH score/replay artifacts.

    The score rows come from the R0 ``offline_scores.json`` artifact (exact v4 ``j`` plus
    ``(shard, row)`` provenance and the three identity hashes).  Each row's design params are
    read from the **live dataset** shard metadata with plain read-only file reads (no writable
    ``DatasetStore``), joined through the S0 catalog on ``(root, shard_index, row)``.  The
    design is normalized through the audited ``active-projection-v1`` encoding (``d=13``,
    full alphabetical vector, ``morph_exponent`` reconstructed at 4.0) and the deterministic
    min/cap subset policy is delegated to :func:`build_training_set`.

    A row whose params/geometry/identity is missing or unrepresentable is skipped with a
    reason code; no value is invented.  The returned ``meta`` publishes the refused rows and
    their reasons, the identity triple, and the retained/excluded subset IDs.
    """
    from ..config import load_config
    from ..design.space import DesignSpace
    from ..types import Design
    from .encoding import ActiveProjection, EncodingError

    if limit is not None and int(limit) < 1:
        raise DataError(f"limit must be >= 1 or None, got {limit!r}")

    config_path = Path(config_path)
    cfg = load_config(config_path)
    space = DesignSpace.from_config(cfg)
    projection = ActiveProjection.from_space(space, no_ops={"morph_exponent": 4.0})
    d = int(projection.d)

    payload = json.loads(Path(scores_json).read_text(encoding="utf-8"))
    all_rows = list(payload.get("rows") or [])
    rows = all_rows if limit is None else all_rows[:int(limit)]
    expected_config = str((payload.get("cohort") or {}).get("native_config")
                          or config_path.stem)

    dataset_root = Path(dataset_root) if dataset_root is not None else _repo_root() / "dataset"
    root_key = dataset_root.name
    catalog = _load_catalog_index(catalog_csv)
    shard_cache: dict[int, dict[int, dict | None]] = {}

    observations: list[TrainingObservation] = []
    refused: list[dict] = []
    identities: dict[str, dict] = {}

    def refuse(observation_id, reasons, *, shard=None, row=None, detail=None):
        rec = {"id": observation_id, "reasons": list(reasons)}
        if shard is not None:
            rec["shard"] = int(shard)
        if row is not None:
            rec["row"] = int(row)
        if detail:
            rec["detail"] = detail
        refused.append(rec)

    for score_row in rows:
        if not isinstance(score_row, Mapping):
            refuse(None, [NATIVE_R_MISSING_PROVENANCE], detail="row is not a mapping")
            continue
        try:
            shard = int(score_row["shard"])
            row_idx = int(score_row["row"])
        except (KeyError, TypeError, ValueError):
            refuse(score_row.get("physical_id"), [NATIVE_R_MISSING_PROVENANCE])
            continue
        obs_id = str(score_row.get("physical_id") or f"native-s{shard:04d}-r{row_idx:04d}")

        catalog_row = catalog.get((root_key, str(shard), str(row_idx)))
        if catalog_row is None:
            refuse(obs_id, [NATIVE_R_CATALOG_ROW_MISSING], shard=shard, row=row_idx)
            continue
        catalog_config = str(catalog_row.get("config_name") or "")
        score_config = str(score_row.get("config_name") or "")
        effective_config = catalog_config or score_config
        if effective_config != expected_config or (
                score_config and score_config != expected_config):
            refuse(obs_id, [NATIVE_R_CONFIG_MISMATCH], shard=shard, row=row_idx,
                   detail=f"catalog={catalog_config!r} score={score_config!r} "
                          f"expected={expected_config!r}")
            continue

        status = str(score_row.get("status") or "")
        if status != "exact_complete" or score_row.get("complete") is False:
            refuse(obs_id, [f"{NATIVE_R_INCOMPLETE_SCORE}:{status or 'unknown'}"],
                   shard=shard, row=row_idx)
            continue
        try:
            J = float(score_row.get("j"))
        except (TypeError, ValueError):
            refuse(obs_id, [NATIVE_R_NONFINITE_J], shard=shard, row=row_idx)
            continue
        if not math.isfinite(J):
            refuse(obs_id, [NATIVE_R_NONFINITE_J], shard=shard, row=row_idx)
            continue

        physical_id = score_row.get("physical_id")
        metric_id = score_row.get("metric_id")
        score_id = score_row.get("score_id")
        if not (physical_id and metric_id and score_id):
            refuse(obs_id, [NATIVE_R_IDENTITY_MISSING], shard=shard, row=row_idx)
            continue

        meta = _read_shard_metas(dataset_root, shard, shard_cache).get(row_idx)
        if meta is None:
            refuse(obs_id, [NATIVE_R_DATASET_ROW_MISSING], shard=shard, row=row_idx)
            continue
        if meta.get("ok") is not True:
            refuse(obs_id, [NATIVE_R_RECORD_NOT_OK], shard=shard, row=row_idx,
                   detail=str(meta.get("error") or "")[:200])
            continue

        params = meta.get("params")
        if not isinstance(params, dict) or not params:
            refuse(obs_id, [NATIVE_R_DESIGN_PARAMS_MISSING], shard=shard, row=row_idx)
            continue
        family = meta.get("family")
        if not isinstance(family, str) or not family:
            refuse(obs_id, [NATIVE_R_DESIGN_FAMILY_MISSING], shard=shard, row=row_idx)
            continue

        meta_design_hash = meta.get("design_hash")
        score_design_hash = score_row.get("design_hash")
        if (meta_design_hash and score_design_hash
                and str(meta_design_hash) != str(score_design_hash)):
            refuse(obs_id, [NATIVE_R_DESIGN_HASH_MISMATCH], shard=shard, row=row_idx,
                   detail=f"dataset={meta_design_hash!r} score={score_design_hash!r}")
            continue

        try:
            design = Design(str(family), dict(params))
            actual_design_hash = design.hash()
        except Exception as exc:  # noqa: BLE001 - a malformed stored design is refused
            refuse(obs_id, [f"{NATIVE_R_ENCODE_REFUSED}:{type(exc).__name__}"],
                   shard=shard, row=row_idx, detail=str(exc)[:200])
            continue
        if meta_design_hash and str(actual_design_hash) != str(meta_design_hash):
            refuse(obs_id, [NATIVE_R_DESIGN_HASH_MISMATCH], shard=shard, row=row_idx,
                   detail=f"params hash {actual_design_hash!r} != recorded "
                          f"{meta_design_hash!r}")
            continue

        # The projection drops only ``morph_exponent`` (inactive at ``morph_target == 1``).
        # Its historical value may legally differ from the 4.0 reconstruction reference, so a
        # hash-exact round-trip is NOT required for that one dropped key.  Every other stored
        # parameter must round-trip exactly; a difference there means the historical design is
        # outside this space/projection and is refused, never clipped.
        if "morph_target" in params:
            try:
                morph_target = int(params["morph_target"])
            except (TypeError, ValueError):
                refuse(obs_id, [f"{NATIVE_R_ENCODE_REFUSED}:invalid_morph_target"],
                       shard=shard, row=row_idx,
                       detail=f"morph_target={params['morph_target']!r} is not an integer")
                continue
            if morph_target != 1:
                refuse(obs_id, [f"{NATIVE_R_ENCODE_REFUSED}:morph_exponent_active"],
                       shard=shard, row=row_idx,
                       detail=f"morph_target={params['morph_target']!r} makes morph_exponent "
                              "active; the active-projection-v1 no-op does not apply")
                continue
        try:
            x = projection.normalize_design(design, verify_round_trip=False)
            reconstructed = projection.denormalize(x)
        except EncodingError as exc:
            refuse(obs_id, [f"{NATIVE_R_ENCODE_REFUSED}:{type(exc).__name__}"],
                   shard=shard, row=row_idx, detail=str(exc)[:200])
            continue
        except Exception as exc:  # noqa: BLE001 - never invent a vector
            refuse(obs_id, [f"{NATIVE_R_ENCODE_REFUSED}:{type(exc).__name__}"],
                   shard=shard, row=row_idx, detail=str(exc)[:200])
            continue
        x = np.asarray(x, dtype=float).reshape(-1)
        if x.size != d or not np.all(np.isfinite(x)):
            refuse(obs_id, [NATIVE_R_NONFINITE_VECTOR], shard=shard, row=row_idx)
            continue
        dropped = set(projection.fixed_values)
        stored_params = dict(getattr(design, "params", {}) or {})
        rebuilt_params = dict(getattr(reconstructed, "params", {}) or {})
        changed = sorted(
            key for key in set(stored_params) | set(rebuilt_params)
            if key not in dropped and stored_params.get(key) != rebuilt_params.get(key))
        if changed:
            refuse(obs_id, [f"{NATIVE_R_ENCODE_REFUSED}:projection_roundtrip_mismatch"],
                   shard=shard, row=row_idx,
                   detail=f"non-dropped parameter(s) changed: {changed[:8]}")
            continue

        geometry_hash = str(meta_design_hash or actual_design_hash)
        solve_hash = meta.get("solve_hash")
        observations.append(TrainingObservation(
            observation_id=obs_id, x=x, J=J, status="ok", eligible=True,
            geometry_hash=geometry_hash,
            solve_hash=None if solve_hash is None else str(solve_hash),
            y_phys=(J,),
        ))
        identities[obs_id] = {
            "physical_id": str(physical_id),
            "metric_id": str(metric_id),
            "score_id": str(score_id),
            "design_hash": geometry_hash,
            "solve_hash": None if solve_hash is None else str(solve_hash),
            "shard": int(shard),
            "row": int(row_idx),
            "J": float(J),
            "stored_j": (None if score_row.get("stored_j") is None
                         else float(score_row["stored_j"])),
            "parity_delta": (None if score_row.get("parity_delta") is None
                             else float(score_row["parity_delta"])),
            "stored_objective_version": score_row.get("stored_objective_version"),
        }

    ts = build_training_set(observations, encoding=projection)
    refusal_counts: dict[str, int] = {}
    for rec in refused:
        for reason in rec["reasons"]:
            key = reason.split(":", 1)[0]
            refusal_counts[key] = refusal_counts.get(key, 0) + 1
    extra_meta = {
        "builder": "build_native_training_set",
        "config_name": expected_config,
        "config": str(config_path),
        "scores_json": str(scores_json),
        "catalog_csv": str(catalog_csv),
        "dataset_root": str(dataset_root),
        "n_scored_rows_available": len(all_rows),
        "n_scored_rows_considered": len(rows),
        "n_observations": len(observations),
        "n_refused": len(refused),
        "refused": refused,
        "refusal_reasons": dict(sorted(refusal_counts.items())),
        "n_unique_design_hashes": len({o.geometry_hash for o in observations}),
        "identities": identities,
        "subset_policy": {
            "method": "build_training_set",
            "n_min": ts.n_min,
            "n_max": ts.n_max,
            "elite_n": DEFAULT_ELITE_N,
            "cap": DEFAULT_N_MAX,
            "rule": "64 lowest-J + 192 deterministic maximin when above the cap; "
                    "ties by observation/design ID",
        },
    }
    return replace(ts, meta={**ts.meta, **extra_meta})


# ---------------------------------------------------------------------------- candidate pool


def _sha(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=float)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _geometry_hash(points: np.ndarray, formula: str) -> str:
    rounded = np.round(np.asarray(points, dtype=np.float64), 6)
    h = hashlib.sha256()
    h.update(str(formula).encode())
    h.update(str(tuple(rounded.shape)).encode())
    h.update(np.ascontiguousarray(rounded, dtype="<f8").tobytes())
    return h.hexdigest()[:20]


def _brief_envelope(config) -> dict:
    brief = getattr(config, "brief", None)
    if not isinstance(brief, dict):
        brief = (getattr(config, "raw", None) or {}).get("brief")
    env = (brief or {}).get("envelope") or {}
    return dict(env) if isinstance(env, dict) else {}


def _expected_throat_radius(params: Mapping[str, Any]) -> float | None:
    if "r0_mm" not in params:
        return None
    try:
        r0 = float(params["r0_mm"])
        ext = float(params.get("throat_ext_length_mm", 0.0) or 0.0)
        ang = float(params.get("throat_ext_angle_deg", 0.0) or 0.0)
    except (TypeError, ValueError):
        return None
    if ext > 0.0:
        return r0 - ext * math.tan(math.radians(ang))
    return r0


def materialize_geometry(design, config, *, resolution_mm: float = 20.0) -> dict:
    """Resolve the installed mesher's canonical point grid without meshing.

    Returns the inner surface ``(n_phi, n_station+1, 3)`` in millimetres plus identity metadata.
    CAD/grid designs are refused because they have no supported radial surface representation.
    """
    params = getattr(design, "params", None)
    if isinstance(params, dict) and ("cad" in params or "grid" in params):
        raise UnsupportedGeometryError(
            "CAD/point-grid designs are unsupported by the canonical radial surface sampler")
    try:
        from hornlab_search.config import mesh_spec
        from hornlab_search.design import families
        from hornlab_mesher.config_builder import resolve_geometry
    except Exception as exc:  # noqa: BLE001 - the mesher is an installed optional dependency
        raise UnsupportedGeometryError(f"hornlab_mesher is unavailable: {exc}") from exc
    if config is None:
        raise UnsupportedGeometryError("materialize_geometry needs a resolved Config")
    msp = mesh_spec("screen", config)
    res = {"throat": float(resolution_mm), "mouth": float(resolution_mm),
           "rear": float(resolution_mm)}
    mcfg = families.to_mesher_config(design, msp, res, Path("<bo-canonical-surface>"),
                                     mounting=getattr(config, "mounting", None))
    # The canonical acoustic surface is the inner wall.  With no brief mounting and no
    # explicitly searched build mode, sample it in inner-only "bare" mode: this skips the
    # outer printed shell (whose offset is irrelevant here and can emit self-intersection
    # warnings on strongly curved mouths) without changing the inner geometry.
    if getattr(config, "mounting", None) is None and not (
            isinstance(params, dict) and "mode" in params):
        mcfg["mode"] = "bare"
        mcfg.pop("enclosure", None)
    mcfg.setdefault("mesh", {}).update({
        "throat_res_mm": float(resolution_mm), "mouth_res_mm": float(resolution_mm),
        "rear_res_mm": float(resolution_mm), "allow_large_mesh": True,
    })
    try:
        rg = resolve_geometry(mcfg, allow_large_mesh=True)
    except Exception as exc:  # noqa: BLE001 - a refused geometry is a rejected candidate
        raise UnsupportedGeometryError(f"geometry resolve failed: {type(exc).__name__}: {exc}") from exc
    points = np.asarray(rg.geometry.inner_points, dtype=np.float64)
    if points.ndim != 3 or points.shape[2] != 3 or not np.all(np.isfinite(points)):
        raise UnsupportedGeometryError("resolved geometry is not a finite (n_phi, n_s, 3) grid")
    return {
        "inner_points": points,
        "formula": str(rg.formula),
        "mode": str(rg.mode),
        "quadrants": str(rg.quadrants),
        "native_symmetry_plane": rg.native_symmetry_plane,
        "surface_fit": getattr(rg.geometry, "surface_fit", None),
        "sampling_metadata": dict(rg.sampling_metadata or {}),
        "resolution_mm": float(resolution_mm),
        "api": "hornlab_mesher.config_builder.resolve_geometry",
    }


def intended_solve_identity(config) -> str:
    """Stable identity of the intended screen solve (mesh + solve specs), recorded in the pool."""
    from hornlab_search.config import mesh_spec, solve_spec

    ms = mesh_spec("screen", config)
    ss = solve_spec("screen", config)
    return _sha({"mesh": ms.hash(), "solve": ss.hash(), "mode": "screen"})


def is_near_duplicate(unit_vector, accepted: list[np.ndarray] | np.ndarray,
                      tol: float = NEAR_DUPLICATE_TOL) -> bool:
    """Infinity-norm near-duplicate in normalized unit coordinates (spec 3.4 step 2)."""
    if accepted is None:
        return False
    arr = np.asarray(accepted, dtype=float)
    if arr.size == 0:
        return False
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    u = np.asarray(unit_vector, dtype=float).reshape(-1)
    return bool(np.any(np.max(np.abs(arr - u), axis=1) <= float(tol)))


@dataclass(frozen=True)
class PoolCandidate:
    candidate_id: str
    pool_index: int
    seed: int
    active_vector: np.ndarray
    full_vector: np.ndarray
    design_hash: str
    geometry_hash: str
    intended_solve_hash: str
    params: dict
    descriptors: dict
    checks: dict
    status: str = POOL_STATUS_NOTE

    def as_dict(self, *, include_vectors: bool = False) -> dict:
        out = {
            "candidate_id": self.candidate_id,
            "pool_index": int(self.pool_index),
            "seed": int(self.seed),
            "design_hash": self.design_hash,
            "geometry_hash": self.geometry_hash,
            "intended_solve_hash": self.intended_solve_hash,
            "params": dict(self.params),
            "descriptors": dict(self.descriptors),
            "checks": dict(self.checks),
            "status": self.status,
        }
        if include_vectors:
            out["active_vector"] = self.active_vector.tolist()
            out["full_vector"] = self.full_vector.tolist()
        return out


@dataclass(frozen=True)
class CandidatePool:
    status: str                                  # "ok" | "pool_exhausted"
    requested: int
    seed: int | None
    seeds_tried: tuple[int, ...]
    candidates: tuple[PoolCandidate, ...]
    counts: dict
    seed_reports: tuple[dict, ...]
    intended_solve_hash: str | None
    note: str

    def summary(self) -> dict:
        return {
            "status": self.status,
            "requested": int(self.requested),
            "seed": self.seed,
            "seeds_tried": list(self.seeds_tried),
            "counts": dict(self.counts),
            "seed_reports": [dict(r) for r in self.seed_reports],
            "intended_solve_hash": self.intended_solve_hash,
            "status_note": POOL_STATUS_NOTE,
            "note": self.note,
            "n_candidates": len(self.candidates),
        }

    def candidates_json(self, *, include_vectors: bool = False) -> list[dict]:
        return [c.as_dict(include_vectors=include_vectors) for c in self.candidates]


def _sobol_unit(d: int, n: int, seed: int) -> tuple[np.ndarray, str]:
    from scipy.stats import qmc

    sampler = qmc.Sobol(d=int(d), scramble=True, seed=int(seed))
    power = int(round(math.log2(n))) if n > 0 else 0
    if n > 0 and 2 ** power == n:
        return np.asarray(sampler.random_base2(power), dtype=float), "random_base2"
    return np.asarray(sampler.random(int(n)), dtype=float), "random"


def _empty_counts() -> dict:
    return {
        "generated": 0,
        "schema_rejected": 0,
        "envelope_rejected": 0,
        "throat_rejected": 0,
        "geometry_rejected": 0,
        "geometry_duplicate": 0,
        "near_duplicate": 0,
        "known_duplicate": 0,
        "unique": 0,
        "novel": 0,
    }


def build_candidate_pool(space, encoding, config, *, n: int = POOL_SIZE, seed: int = 0,
                         known_geometry_hashes: Iterable[str] | None = None,
                         known_identities: Iterable[tuple[str, str]] | None = None,
                         max_extra_seeds: int = 2,
                         resolution_mm: float = 30.0) -> CandidatePool:
    """Generate a finite scrambled-Sobol pool through the audited active projection.

    Cheap checks only: schema validation, a pure geometry resolve (no gmsh/BEM), brief envelope,
    and a positive/materially-consistent throat.  Deduplication is by materialized geometry plus
    intended solve identity first, then by active-vector infinity norm ``<= 1e-6``.  If no novel
    legal candidate survives, at most two further recorded seeds are tried, then
    ``status="pool_exhausted"``.
    """
    if n < 1:
        raise DataError(f"n must be >= 1, got {n}")
    d = int(encoding.d)
    solve_hash = intended_solve_identity(config)
    env = _brief_envelope(config)
    known = {str(h) for h in (known_geometry_hashes or ())}
    known_ids = {(str(a), str(b)) for a, b in (known_identities or ())}
    if known:
        # A bare known geometry hash is assumed to be the same intended screen solve.
        known_ids |= {(gh, solve_hash) for gh in known}

    seed_reports: list[dict] = []
    aggregate = _empty_counts()
    tried: list[int] = []
    for attempt in range(1 + max(0, int(max_extra_seeds))):
        this_seed = int(seed) + attempt
        tried.append(this_seed)
        counts = _empty_counts()
        accepted: list[PoolCandidate] = []
        accepted_vectors: list[np.ndarray] = []
        seen_geometry: dict[tuple[str, str], str] = {}
        unit, method = _sobol_unit(d, n, this_seed)
        counts["generated"] = int(unit.shape[0])
        for i in range(unit.shape[0]):
            active = np.asarray(unit[i], dtype=float)
            try:
                full = encoding.to_full(active)
                design = space.denormalize(full)
            except Exception:  # noqa: BLE001 - a bad decoded corner is a rejected candidate
                counts["schema_rejected"] += 1
                continue
            params = getattr(design, "params", None)
            if isinstance(params, dict) and params.get("_generator_error"):
                counts["schema_rejected"] += 1
                continue
            try:
                from hornlab_search.design import families
                families.validate(design)
            except Exception:  # noqa: BLE001
                counts["schema_rejected"] += 1
                continue
            try:
                mat = materialize_geometry(design, config, resolution_mm=resolution_mm)
            except Exception:  # noqa: BLE001 - unsupported/resolve failure
                counts["geometry_rejected"] += 1
                continue
            desc = _surface_descriptors(mat["inner_points"])
            if not _envelope_ok(desc, env):
                counts["envelope_rejected"] += 1
                continue
            expected_throat = _expected_throat_radius(params if isinstance(params, dict) else {})
            if not _throat_ok(desc["throat_radius_mm"], expected_throat):
                counts["throat_rejected"] += 1
                continue
            ghash = _geometry_hash(mat["inner_points"], mat["formula"])
            identity = (ghash, solve_hash)
            if identity in seen_geometry:
                counts["geometry_duplicate"] += 1
                continue
            if is_near_duplicate(active, accepted_vectors, NEAR_DUPLICATE_TOL):
                counts["near_duplicate"] += 1
                continue
            if identity in known_ids:
                counts["known_duplicate"] += 1
                seen_geometry[identity] = "known"
                continue
            dh = design.hash()
            cand = PoolCandidate(
                candidate_id=f"pool-{this_seed}-{i:05d}-{ghash[:8]}",
                pool_index=i, seed=this_seed, active_vector=active.copy(),
                full_vector=np.asarray(full, dtype=float).copy(), design_hash=dh,
                geometry_hash=ghash, intended_solve_hash=solve_hash,
                params=_jsonable_params(params), descriptors=desc,
                checks={"schema": "passed", "envelope": "passed", "throat": "passed",
                        "materialized": True, "mesh_built": False, "bem_called": False},
            )
            accepted.append(cand)
            accepted_vectors.append(active.copy())
            seen_geometry[identity] = cand.candidate_id
            counts["unique"] += 1
            counts["novel"] += 1
        aggregate["generated"] += counts["generated"]
        for key in ("schema_rejected", "envelope_rejected", "throat_rejected",
                    "geometry_rejected", "geometry_duplicate", "near_duplicate",
                    "known_duplicate", "unique", "novel"):
            aggregate[key] += counts[key]
        seed_reports.append({"seed": this_seed, "method": method, "counts": dict(counts)})
        if counts["novel"] > 0:
            aggregate["generated"] = int(unit.shape[0])
            return CandidatePool(
                status="ok", requested=int(n), seed=this_seed, seeds_tried=tuple(tried),
                candidates=tuple(accepted), counts=counts, seed_reports=tuple(seed_reports),
                intended_solve_hash=solve_hash,
                note=POOL_STATUS_NOTE,
            )
    return CandidatePool(
        status="pool_exhausted", requested=int(n), seed=None, seeds_tried=tuple(tried),
        candidates=(), counts=aggregate, seed_reports=tuple(seed_reports),
        intended_solve_hash=solve_hash,
        note=("no novel legal candidate after "
              f"{len(tried)} recorded seed(s); mesh/acoustic eligibility unknown"),
    )


def _jsonable_params(params) -> dict:
    if not isinstance(params, dict):
        return {}
    out: dict = {}
    for key, value in params.items():
        if isinstance(value, (np.floating, np.integer)):
            value = float(value) if isinstance(value, np.floating) else int(value)
        if isinstance(value, (list, tuple)):
            out[str(key)] = [float(v) if isinstance(v, (int, float, np.floating, np.integer)) else v
                             for v in value]
        elif isinstance(value, (int, float, bool, str)) or value is None:
            out[str(key)] = value
        else:
            out[str(key)] = str(value)
    return out


def _surface_descriptors(points: np.ndarray) -> dict:
    """Cheap descriptors from the sampled point grid (mm); no meshing or BEM."""
    x = points[:, :, 0]
    y = points[:, :, 1]
    z = points[:, :, 2]
    r = np.hypot(x, y)
    throat = float(np.mean(r[:, 0]))
    mouth_r = r[:, -1]
    return {
        "throat_radius_mm": throat,
        "mouth_width_mm": float(2.0 * np.max(np.abs(x[:, -1]))),
        "mouth_height_mm": float(2.0 * np.max(np.abs(y[:, -1]))),
        "depth_mm": float(np.max(z) - np.min(z)),
        "mouth_radius_min_mm": float(np.min(mouth_r)),
        "mouth_radius_max_mm": float(np.max(mouth_r)),
        "radius_min_mm": float(np.min(r)),
    }


def _envelope_ok(desc: Mapping[str, float], env: Mapping[str, Any]) -> bool:
    checks = (
        ("max_mouth_w_mm", "mouth_width_mm"),
        ("max_mouth_h_mm", "mouth_height_mm"),
        ("max_depth_mm", "depth_mm"),
    )
    for env_key, desc_key in checks:
        if env_key not in env:
            continue
        try:
            limit = float(env[env_key])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(limit):
            continue
        if float(desc[desc_key]) > limit + 0.5:
            return False
    return True


def _throat_ok(throat_radius_mm: float, expected: float | None) -> bool:
    if not math.isfinite(float(throat_radius_mm)) or float(throat_radius_mm) <= 0.0:
        return False
    if expected is None:
        return True
    expected = float(expected)
    if not math.isfinite(expected) or expected <= 0.0:
        return False
    return abs(float(throat_radius_mm) - expected) <= max(0.5, 0.02 * expected)


__all__ = [
    "DEFAULT_N_MAX",
    "DEFAULT_ELITE_N",
    "N_MIN_FLOOR",
    "POOL_SIZE",
    "POOL_STATUS_NOTE",
    "NEAR_DUPLICATE_TOL",
    "DataError",
    "UnsupportedGeometryError",
    "TrainingObservation",
    "TrainingSet",
    "n_min_for",
    "build_training_set",
    "build_native_training_set",
    "NATIVE_REFUSAL_REASONS",
    "make_pure_observations",
    "materialize_geometry",
    "intended_solve_identity",
    "is_near_duplicate",
    "PoolCandidate",
    "CandidatePool",
    "build_candidate_pool",
]
