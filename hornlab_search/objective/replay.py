"""Canonical, backend-free replay of stored evaluations under a chosen scoring brief.

This module is the R0 seam between *immutable physical data* and *scoring variants*. It never
solves, meshes or calls a backend: it reconstructs the stored ``Response``/``MetricSet`` from
dataset arrays (or a run directory's ``response.npz`` + ``metrics.json``) and dispatches to the
existing canonical scorer (``objective/scalar*.py`` via ``objective/versions.py``). No objective
formula is re-implemented here.

Three identities are emitted separately and never collapsed:

* ``physical_id`` -- immutable solve/response identity (design/mesh/solve hashes, family, params,
  solve/observation metadata, pins, and a digest of every stored raw response array).
* ``metric_id`` -- derived metric identity: physical id + metric code version + target/coverage/
  band/frequency weights + the metric arrays actually used (or an explicit "unavailable" marker).
* ``score_id`` -- metric id + objective version + weights + objective block/brief identity +
  score code version.

Every replay returns one of the three statuses from the parent contract:

``exact_complete``
    All inputs required by the selected objective are present and the canonical response-based
    paths were used (detrended ripple, response flatness, balloon diagonal where weighted).
``partial_unsupported``
    A score can be computed for diagnosis, but something required for *exact* parity/completeness
    is absent (e.g. metrics-only replay, no balloon for a weighted ``diag`` term, legacy ripple
    fallback). Such rows must never rank beside ``exact_complete`` rows.
``additional_data_or_solve_required``
    A required physical input is missing or the requested change cannot be supported by the stored
    arrays (impedance/loading, MEH channels, throat geometry, a target band with no stored bins,
    a regeneration that needs response arrays that are absent). No score is returned.

Missing impedance/throat/balloon/MEH inputs are *never* treated as a pass. In particular, an
active ``load`` weight with no ``z_throat``, a v5 MEH objective with no MEH inputs, or a target
change without response arrays refuse rather than silently scoring a fabricated/absent term.

The module is pure numpy + stdlib. Importing it does not import a solver.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ..metrics.compute import compute_metrics
from ..targets.spec import Target
from ..types import MetricSet, Response
from .scalar import objective as _objective_v1
from .scalar import resolve_weights as _resolve_weights
from .scalar_v2 import (_cut_arrays, _on_axis_index, _v2_ripple_values, objective_v2,
                        objective_v3)
from .scalar_v4 import V4Params, _diag_term, objective_v4, resolve_v4_weights
from .terms import NAN_TERM_FILL
from .versions import SUPPORTED_OBJECTIVE_VERSIONS, is_supported_objective_version

__all__ = [
    "Brief",
    "ReplayResult",
    "STATUS_EXACT_COMPLETE",
    "STATUS_PARTIAL_UNSUPPORTED",
    "STATUS_ADDITIONAL_DATA_OR_SOLVE_REQUIRED",
    "STATUSES",
    "REASONS",
    "load_brief_context",
    "brief_from_config",
    "replay_record",
    "replay_run_dir",
    "rank_complete",
    "incomplete_results",
]

# ------------------------------------------------------------------ statuses / reason codes

STATUS_EXACT_COMPLETE = "exact_complete"
STATUS_PARTIAL_UNSUPPORTED = "partial_unsupported"
STATUS_ADDITIONAL_DATA_OR_SOLVE_REQUIRED = "additional_data_or_solve_required"
STATUSES = (STATUS_EXACT_COMPLETE, STATUS_PARTIAL_UNSUPPORTED,
            STATUS_ADDITIONAL_DATA_OR_SOLVE_REQUIRED)

R_OK = "ok"
R_RECORD_NOT_OK = "record_not_ok"
R_NO_METRICS = "no_stored_metrics"
R_NO_RESPONSE = "no_response_arrays"
R_STORED_TARGET_MISSING = "stored_target_unavailable"
R_TARGET_REGEN_UNSUPPORTED = "target_regeneration_unsupported"
R_METRIC_REGEN_DISABLED = "metric_regeneration_disabled"
R_MISSING_BALLOON = "missing_balloon"
R_MISSING_IMPEDANCE = "missing_impedance"
R_MISSING_MEH = "missing_meh_inputs"
R_MISSING_THROAT = "missing_throat_geometry"
R_RIPPLE_LEGACY = "ripple_legacy_fallback"
R_FLAT_LEGACY = "flat_legacy_fallback"
R_DIAG_UNAVAILABLE = "diag_unmeasurable"
R_BAND_NOT_COVERED = "band_not_covered"
R_F0_NOT_COVERED = "f0_not_covered"
R_UNSUPPORTED_OBJECTIVE = "unsupported_objective_version"
R_REPLAY_VERSION_UNSUPPORTED = "objective_version_not_supported_by_replay"
R_METRIC_ARRAY = "metric_array_problem"
R_NO_SCORE_CONFIG = "missing_score_config"
R_NO_TARGET = "missing_target"

#: Reasons that force ``additional_data_or_solve_required`` (no score returned).
_HARD_REASONS = frozenset({
    R_RECORD_NOT_OK, R_NO_METRICS, R_TARGET_REGEN_UNSUPPORTED, R_METRIC_REGEN_DISABLED,
    R_MISSING_IMPEDANCE, R_MISSING_MEH, R_MISSING_THROAT, R_BAND_NOT_COVERED, R_F0_NOT_COVERED,
    R_UNSUPPORTED_OBJECTIVE, R_REPLAY_VERSION_UNSUPPORTED, R_NO_SCORE_CONFIG, R_NO_TARGET,
})

#: Reasons that force ``partial_unsupported`` (score may be returned for diagnosis only).
_PARTIAL_REASONS = frozenset({
    R_NO_RESPONSE, R_STORED_TARGET_MISSING, R_MISSING_BALLOON, R_RIPPLE_LEGACY,
    R_FLAT_LEGACY, R_DIAG_UNAVAILABLE, R_METRIC_ARRAY,
})

REASONS = {
    R_OK: "complete replay",
    R_RECORD_NOT_OK: "the stored record is a failure (ok=false); there is nothing to re-score",
    R_NO_METRICS: "no stored metric arrays and no response arrays to regenerate them",
    R_NO_RESPONSE: "no h/v-angle + spl response arrays; response-based ripple/flat/diag are unavailable",
    R_STORED_TARGET_MISSING: "the record carries no target, so target identity cannot be verified",
    R_TARGET_REGEN_UNSUPPORTED: "the requested target/band change needs response arrays that are absent",
    R_METRIC_REGEN_DISABLED: "target-dependent metric regeneration was explicitly disabled",
    R_MISSING_BALLOON: "a weighted v4 diag term needs balloon_dirs + spl_balloon_db",
    R_MISSING_IMPEDANCE: "an active loading term needs z_throat; impedance was not stored",
    R_MISSING_MEH: "objective v5 needs MEH channel/impedance-matrix inputs",
    R_MISSING_THROAT: "the selected objective needs throat geometry, which is not stored",
    R_RIPPLE_LEGACY: "the canonical scorer fell back to stored v1 ripple (_used_resp=False)",
    R_FLAT_LEGACY: "the canonical scorer fell back to stored on_axis_db instead of the response",
    R_DIAG_UNAVAILABLE: "the canonical v4 diag term is NAN_TERM_FILL (no measurable balloon diagonal)",
    R_BAND_NOT_COVERED: "no stored frequency lies inside the requested target band",
    R_F0_NOT_COVERED: "no stored frequency lies at/above the requested f0 inside the band",
    R_UNSUPPORTED_OBJECTIVE: "objective version is not in objective.versions.SUPPORTED_OBJECTIVE_VERSIONS",
    R_REPLAY_VERSION_UNSUPPORTED: "this replay adapter currently dispatches only objective versions 1-4",
    R_METRIC_ARRAY: "a stored metric array is missing or has the wrong shape",
    R_NO_SCORE_CONFIG: "no weights/objective block (brief or explicit override) were supplied",
    R_NO_TARGET: "no target was available from the record, the brief or an explicit override",
}

#: Bump when the *metric reconstruction* convention changes. It is part of ``metric_id``.
METRIC_CODE_VERSION = "metrics.compute.v1"
#: Bump when the *score dispatch* convention changes. It is part of ``score_id``.
SCORE_CODE_VERSION = "objective.dispatch.v1"

_RAW_ARRAY_KEYS = ("freqs_hz", "h_angles_deg", "v_angles_deg", "spl_h_db", "spl_v_db",
                   "balloon_dirs", "spl_balloon_db", "z_throat", "channel_pressure",
                   "channel_sphere_pressure", "impedance_matrix")
_METRIC_ARRAY_KEYS = ("freqs_hz", "bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db", "ripple_v_db",
                      "on_axis_db", "z_throat")


# ------------------------------------------------------------------ brief resolution

@dataclass(frozen=True)
class Brief:
    """A brief resolved through ``hornlab_search.config.load_brief`` (or ``load_config``)."""

    name: str
    target: Target
    weights: dict
    objective_version: int
    objective_block: dict | None
    objective_params: Any
    raw: dict = field(default_factory=dict)
    source_path: str | None = None

    def brief_hash(self) -> str:
        return _hash({"kind": "brief", "raw": _plain(self.raw),
                      "name": self.name, "version": self.objective_version})


def _params_from_block(version: int, block: dict | None):
    """Validate/build the canonical params object for a version (only v4 is needed here)."""
    if version == 4:
        if block is None:
            raise ValueError("objective v4 needs its objective block (tolerances)")
        if isinstance(block, V4Params):
            return block
        return V4Params.from_block(dict(block))
    return None


def load_brief_context(path) -> Brief:
    """Resolve a brief YAML through the real loader (validated) into a :class:`Brief`."""
    from ..config import load_brief as _load_brief

    raw = _load_brief(path)
    block = dict(raw["objective"]) if isinstance(raw.get("objective"), dict) else None
    version = int((block or {}).get("version", 1))
    return Brief(
        name=str(raw.get("name") or Path(path).stem),
        target=Target.from_dict(dict(raw["target"])),
        weights=dict(raw["weights"]),
        objective_version=version,
        objective_block=block,
        objective_params=_params_from_block(version, block),
        raw=raw,
        source_path=str(path),
    )


def brief_from_config(path) -> Brief:
    """Resolve a full config YAML through ``load_config`` (the real brief-resolution path)."""
    from ..config import load_config

    cfg = load_config(path)
    raw_brief = dict(cfg.brief or {})
    if cfg.objective_params is not None:
        block = dict(cfg.objective_params)
    elif isinstance(raw_brief.get("objective"), dict):
        block = dict(raw_brief["objective"])
    else:
        block = {"version": int(cfg.objective_version)}
    version = int(cfg.objective_version)
    return Brief(
        name=str(cfg.name),
        target=Target.from_dict(dict(cfg.target_raw)),
        weights=dict(cfg.weights),
        objective_version=version,
        objective_block=block,
        objective_params=_params_from_block(version, block),
        raw={"config": str(path), "brief": raw_brief},
        source_path=str(path),
    )


# ------------------------------------------------------------------ tiny canonical helpers

def _plain(obj):
    """Recursively convert to plain JSON types (numpy scalars/arrays -> Python)."""
    if obj is None or isinstance(obj, (str, bool)):
        return obj
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return float(obj) if math.isfinite(float(obj)) else None
    if isinstance(obj, np.ndarray):
        return _plain(obj.tolist())
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return _plain(dataclasses.asdict(obj))
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


def _hash(obj) -> str:
    text = json.dumps(_plain(obj), sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _array_digest(arr) -> str | None:
    if arr is None:
        return None
    a = np.ascontiguousarray(arr)
    if a.dtype == object:
        return _hash({"object": a.tolist()})
    h = hashlib.sha256()
    h.update(a.dtype.str.encode("ascii"))
    h.update(repr(tuple(a.shape)).encode("ascii"))
    h.update(a.tobytes(order="C"))
    return h.hexdigest()


def _array_digests(arrays: dict | None, keys) -> dict:
    arrays = arrays or {}
    return {k: _array_digest(arrays.get(k)) for k in keys}


def _as_1d(name: str, arrays: dict | None, n: int | None = None):
    if not arrays or name not in arrays:
        return None
    a = np.asarray(arrays[name], dtype=float)
    if a.ndim != 1 or (n is not None and a.size != n):
        return None
    return a


def _as_2d(name: str, arrays: dict | None, n: int | None = None):
    if not arrays or name not in arrays:
        return None
    a = np.asarray(arrays[name], dtype=float)
    if a.ndim != 2 or (n is not None and a.shape[0] != n):
        return None
    return a


def _target_key(target: Target | None) -> dict | None:
    return None if target is None else _plain(dataclasses.asdict(target))


def _stored_j(meta: dict | None) -> float | None:
    raw = (meta or {}).get("objective")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(float(raw)):
        return float(raw)
    return None


# ------------------------------------------------------------------ response / metric rebuild

def _metricset_from_arrays(meta: dict | None, arrays: dict | None, target: Target | None):
    """Rebuild the *stored* MetricSet exactly as recorded (no formula re-implementation)."""
    reasons: list[str] = []
    f = _as_1d("freqs_hz", arrays)
    if f is None:
        return None, [R_NO_METRICS]
    n = f.size

    def metric(name: str) -> np.ndarray:
        a = _as_1d(name, arrays, n)
        if a is None:
            reasons.append(f"{R_METRIC_ARRAY}:{name}")
            return np.full(n, np.nan)
        return a

    bw_h = metric("bw_h_deg")
    bw_v = metric("bw_v_deg")
    di = metric("di_db")
    rip_h = metric("ripple_h_db")
    rip_v = metric("ripple_v_db")
    on_axis = metric("on_axis_db")

    z_real = None
    if arrays and arrays.get("z_throat") is not None:
        z = np.asarray(arrays["z_throat"], dtype=complex)
        if z.ndim == 1 and z.size == n:
            z_real = np.real(z).astype(float)
        else:
            reasons.append(f"{R_METRIC_ARRAY}:z_throat")

    scalars = dict((meta or {}).get("metrics_scalars") or {})
    di_source = scalars.get("di_source")
    if not di_source:
        di_source = "balloon" if (arrays or {}).get("spl_balloon_db") is not None \
            else "cuts_estimate"
    return MetricSet(
        freqs_hz=f, bw_h_deg=bw_h, bw_v_deg=bw_v, di_db=di, di_source=str(di_source),
        ripple_h_db=rip_h, ripple_v_db=rip_v, on_axis_db=on_axis,
        z_throat_real=z_real, scalars=scalars,
    ), reasons


def _response_from_arrays(meta: dict | None, arrays: dict | None):
    """Rebuild a canonical ``Response`` from stored arrays, or return a reason."""
    arrays = arrays or {}
    f = _as_1d("freqs_hz", arrays)
    ha = _as_1d("h_angles_deg", arrays)
    va = _as_1d("v_angles_deg", arrays)
    sh = _as_2d("spl_h_db", arrays)
    sv = _as_2d("spl_v_db", arrays)
    if f is None or ha is None or va is None or sh is None or sv is None:
        return None, R_NO_RESPONSE
    n = f.size
    if sh.shape != (n, ha.size) or sv.shape != (n, va.size) or ha.size == 0 or va.size == 0:
        return None, R_NO_RESPONSE

    balloon_dirs = arrays.get("balloon_dirs")
    spl_balloon = arrays.get("spl_balloon_db")
    if balloon_dirs is not None:
        balloon_dirs = np.asarray(balloon_dirs, dtype=float)
    if spl_balloon is not None:
        spl_balloon = np.asarray(spl_balloon, dtype=float)
    if (balloon_dirs is None) != (spl_balloon is None):
        # A half-stored balloon is not usable; do not fabricate the missing half.
        balloon_dirs = spl_balloon = None
    if spl_balloon is not None and (spl_balloon.ndim != 2 or spl_balloon.shape[0] != n):
        balloon_dirs = spl_balloon = None

    z = arrays.get("z_throat")
    if z is not None:
        z = np.asarray(z, dtype=complex)
        if z.ndim != 1 or z.size != n:
            z = None

    def maybe(name: str):
        v = arrays.get(name)
        return None if v is None else np.asarray(v)

    backend = str(((meta or {}).get("solve") or {}).get("backend") or "")
    n_dof = ((meta or {}).get("solve") or {}).get("n_dof")
    resp = Response(
        freqs_hz=f, h_angles_deg=ha, v_angles_deg=va, spl_h_db=sh, spl_v_db=sv,
        balloon_dirs=balloon_dirs, spl_balloon_db=spl_balloon, z_throat=z,
        p_h=maybe("p_h"), p_v=maybe("p_v"), p_balloon=maybe("p_balloon"),
        backend=backend, n_dof=(None if n_dof is None else int(n_dof)),
        meta={"distance_m": (((meta or {}).get("solve") or {}).get("observation") or {})
              .get("distance_m")},
        channel_pressure=maybe("channel_pressure"),
        channel_sphere_pressure=maybe("channel_sphere_pressure"),
        impedance_matrix=maybe("impedance_matrix"),
    )
    return resp, None


def _arrays_from_response(resp: Response) -> dict:
    out: dict = {}
    for name in ("freqs_hz", "h_angles_deg", "v_angles_deg", "spl_h_db", "spl_v_db",
                 "balloon_dirs", "spl_balloon_db", "z_throat", "p_h", "p_v", "p_balloon",
                 "channel_pressure", "channel_sphere_pressure", "impedance_matrix"):
        v = getattr(resp, name, None)
        if v is not None:
            out[name] = np.asarray(v)
    return out


# ------------------------------------------------------------------ result object

@dataclass(frozen=True)
class ReplayResult:
    status: str
    reasons: tuple[str, ...]
    physical_id: str
    metric_id: str
    score_id: str
    objective_version: int
    metric_source: str
    design_hash: str | None = None
    j: float | None = None
    terms: dict | None = None
    stored_j: float | None = None
    parity_delta: float | None = None
    target: dict | None = None
    weights: dict | None = None
    diagnostics: dict = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return self.status == STATUS_EXACT_COMPLETE

    def to_dict(self) -> dict:
        return _plain({
            "status": self.status,
            "complete": self.complete,
            "reasons": list(self.reasons),
            "physical_id": self.physical_id,
            "metric_id": self.metric_id,
            "score_id": self.score_id,
            "objective_version": self.objective_version,
            "metric_source": self.metric_source,
            "design_hash": self.design_hash,
            "j": self.j,
            "terms": self.terms,
            "stored_j": self.stored_j,
            "parity_delta": self.parity_delta,
            "target": self.target,
            "weights": self.weights,
            "diagnostics": self.diagnostics,
        })


def rank_complete(results) -> list[ReplayResult]:
    """Only ``exact_complete`` rows, sorted by J then design hash.

    Incomplete scores must never rank as equivalents beside complete scores; this is the one
    sanctioned ranking entry point for replay tables.
    """
    complete = [r for r in results if r.complete and r.j is not None]
    return sorted(complete, key=lambda r: (float(r.j), r.design_hash or ""))


def incomplete_results(results) -> list[ReplayResult]:
    return [r for r in results if not r.complete]


# ------------------------------------------------------------------ identity construction

def _physical_identity(meta: dict | None, arrays: dict | None, response: Response | None) -> str:
    meta = meta or {}
    raw = _array_digests(arrays, _RAW_ARRAY_KEYS)
    if response is not None:
        for k, v in _arrays_from_response(response).items():
            if raw.get(k) is None:
                raw[k] = _array_digest(v)
    return _hash({
        "kind": "physical",
        "design_hash": meta.get("design_hash"),
        "mesh_hash": meta.get("mesh_hash"),
        "solve_hash": meta.get("solve_hash"),
        "family": meta.get("family"),
        "params": meta.get("params"),
        "mesh": meta.get("mesh"),
        "solve": meta.get("solve"),
        "excitation": meta.get("excitation"),
        "lib_shas": meta.get("lib_shas"),
        "raw_arrays": raw,
    })


def _identity(
    meta: dict | None,
    arrays: dict | None,
    response: Response | None,
    metrics: MetricSet | None,
    target: Target | None,
    metric_source: str,
    version: int,
    weights: dict | None,
    objective_block: dict | None,
    brief: Brief | None,
) -> tuple[str, str, str]:
    physical_id = _physical_identity(meta, arrays, response)
    if metrics is None:
        metric_arrays = _array_digests(arrays, _METRIC_ARRAY_KEYS)
        metric_available = False
        di_source = None
    else:
        metric_arrays = {
            "freqs_hz": _array_digest(metrics.freqs_hz),
            "bw_h_deg": _array_digest(metrics.bw_h_deg),
            "bw_v_deg": _array_digest(metrics.bw_v_deg),
            "di_db": _array_digest(metrics.di_db),
            "ripple_h_db": _array_digest(metrics.ripple_h_db),
            "ripple_v_db": _array_digest(metrics.ripple_v_db),
            "on_axis_db": _array_digest(metrics.on_axis_db),
            "z_throat_real": _array_digest(metrics.z_throat_real),
        }
        metric_available = True
        di_source = metrics.di_source
    metric_id = _hash({
        "kind": "metric",
        "physical_id": physical_id,
        "metric_code": METRIC_CODE_VERSION,
        "metric_source": metric_source,
        "metric_available": metric_available,
        "target": _target_key(target),
        "di_source": di_source,
        "metric_arrays": metric_arrays,
    })
    score_id = _hash({
        "kind": "score",
        "metric_id": metric_id,
        "score_code": SCORE_CODE_VERSION,
        "objective_version": version,
        "weights": weights,
        "objective_block": objective_block,
        "brief_hash": (brief.brief_hash() if brief is not None else None),
        "brief_name": (brief.name if brief is not None else None),
    })
    return physical_id, metric_id, score_id


# ------------------------------------------------------------------ dispatch

def _dispatch(version: int, metrics: MetricSet, response: Response | None, target: Target,
              weights: dict, params):
    if version == 1:
        return _objective_v1(metrics, True, target, weights)
    if version == 2:
        return objective_v2(metrics, response, True, target, weights)
    if version == 3:
        return objective_v3(metrics, response, True, target, weights)
    if version == 4:
        return objective_v4(metrics, response, True, target, weights, params)
    raise ValueError(f"no replay dispatch for objective version {version}")


def _weight_for(version: int, weights: dict, key: str) -> float:
    if version == 4:
        return float(resolve_v4_weights(weights).get(key, 0.0))
    return float(_resolve_weights(weights).get(key, 0.0))


# ------------------------------------------------------------------ the replay core

def _replay_core(
    meta: dict | None,
    arrays: dict | None,
    *,
    response: Response | None = None,
    stored_metrics: MetricSet | None = None,
    stored_metric_reasons: list[str] | None = None,
    brief: Brief | None,
    target: Target | None,
    weights_override: dict | None,
    objective_params_override,
    objective_version_override: int | None,
    regenerate_metrics: bool | None,
    allow_metric_regeneration: bool,
) -> ReplayResult:
    meta = meta or {}
    arrays = arrays or {}
    stored_metric_reasons = list(stored_metric_reasons or [])

    # ---- resolve target / score config -----------------------------------------------------
    stored_target_dict = meta.get("target")
    stored_target = None
    stored_target_verified = False
    if isinstance(stored_target_dict, dict):
        try:
            stored_target = Target.from_dict(stored_target_dict)
            stored_target_verified = True
        except ValueError:
            stored_target = None
    if stored_target is None and brief is not None:
        stored_target = brief.target

    # The scoring target for a brief-supplied replay is the resolved brief, not the stored
    # record target: the brief carries the parent-frozen optional scoring fields (e.g.
    # freq_weights) the historical record may not have. The stored target remains the sole
    # parity/target-change comparator. An explicit ``target=`` argument still wins.
    requested_target: Target | None = None
    if target is not None:
        requested_target = target
    elif brief is not None and brief.target is not None:
        requested_target = brief.target
    else:
        requested_target = stored_target
    if requested_target is None:
        return _refuse(meta, arrays, response, stored_metrics, stored_target, brief,
                       objective_version_override or 1, weights_override,
                       objective_params_override, R_NO_TARGET)

    version = (objective_version_override if objective_version_override is not None
               else (brief.objective_version if brief is not None
                     else int(meta.get("objective_version", 1))))
    weights = weights_override if weights_override is not None \
        else (brief.weights if brief is not None else None)
    block = objective_params_override if objective_params_override is not None \
        else (brief.objective_block if brief is not None else None)

    if weights is None:
        return _refuse(meta, arrays, response, stored_metrics, requested_target, brief, version,
                       weights, block, R_NO_SCORE_CONFIG)
    if version == 4 and block is None:
        return _refuse(meta, arrays, response, stored_metrics, requested_target, brief, version,
                       weights, block, R_NO_SCORE_CONFIG)

    if not is_supported_objective_version(version):
        return _refuse(meta, arrays, response, stored_metrics, requested_target, brief, version,
                       weights, block, R_UNSUPPORTED_OBJECTIVE)
    if version not in (1, 2, 3, 4):
        return _refuse(meta, arrays, response, stored_metrics, requested_target, brief, version,
                       weights, block, R_REPLAY_VERSION_UNSUPPORTED)

    try:
        params = _params_from_block(version, block)
    except ValueError:
        return _refuse(meta, arrays, response, stored_metrics, requested_target, brief, version,
                       weights, block, R_NO_SCORE_CONFIG)

    target_changed = (stored_target is not None
                      and _target_key(requested_target) != _target_key(stored_target))

    # ---- identity (available inputs, even for refusals) -----------------------------------
    physical_id, metric_id, score_id = _identity(
        meta, arrays, response, stored_metrics, requested_target, "stored", version, weights,
        block, brief)

    # ---- failed record ---------------------------------------------------------------------
    if meta.get("ok") is False:
        return ReplayResult(
            status=STATUS_ADDITIONAL_DATA_OR_SOLVE_REQUIRED, reasons=(R_RECORD_NOT_OK,),
            physical_id=physical_id, metric_id=metric_id, score_id=score_id,
            objective_version=version, metric_source="none", design_hash=meta.get("design_hash"),
            stored_j=_stored_j(meta), target=_target_key(requested_target), weights=weights,
            diagnostics={"record_error": meta.get("error")},
        )

    # ---- metric reconstruction ------------------------------------------------------------
    need_regen = (target_changed if regenerate_metrics is None else bool(regenerate_metrics))
    reasons: list[str] = []
    metric_source = "stored"
    metrics: MetricSet | None

    if target_changed and not stored_target_verified:
        reasons.append(R_STORED_TARGET_MISSING)

    if need_regen:
        if response is None:
            return _refuse(meta, arrays, response, stored_metrics, requested_target, brief,
                           version, weights, block, R_TARGET_REGEN_UNSUPPORTED)
        if not allow_metric_regeneration:
            return _refuse(meta, arrays, response, stored_metrics, requested_target, brief,
                           version, weights, block, R_METRIC_REGEN_DISABLED)
        metrics = compute_metrics(response, requested_target)
        metric_source = "regenerated"
    elif stored_metrics is not None:
        metrics = stored_metrics
        reasons.extend(stored_metric_reasons)
    elif response is not None:
        metrics = compute_metrics(response, requested_target)
        metric_source = "regenerated"
        reasons.append(R_NO_METRICS)
    else:
        return _refuse(meta, arrays, response, stored_metrics, requested_target, brief, version,
                       weights, block, R_NO_METRICS)

    assert metrics is not None
    f = np.asarray(metrics.freqs_hz, dtype=float)
    band = (f >= requested_target.band_lo_hz) & (f <= requested_target.band_hi_hz)
    if not bool(band.any()):
        return _refuse(meta, arrays, response, metrics, requested_target, brief, version,
                       weights, block, R_BAND_NOT_COVERED)
    score = None
    if version >= 3:
        score = band & (f >= requested_target.f0_effective_hz())
        if not bool(score.any()):
            return _refuse(meta, arrays, response, metrics, requested_target, brief, version,
                           weights, block, R_F0_NOT_COVERED)

    # ---- required inputs (missing => refuse; never a pass) --------------------------------
    if _weight_for(version, weights, "load") > 0.0 and metrics.z_throat_real is None:
        return _refuse(meta, arrays, response, metrics, requested_target, brief, version,
                       weights, block, R_MISSING_IMPEDANCE)
    if version == 5:
        return _refuse(meta, arrays, response, metrics, requested_target, brief, version,
                       weights, block, R_MISSING_MEH)
    # The brief's optional round-throat gate is an eligibility input, not a J term. The dataset
    # stores no mesh/throat shape, so a replay cannot evaluate it; refusing is the honest result.
    if brief is not None and bool(((brief.raw.get("gates") or {}) or {}).get("round_throat")):
        return _refuse(meta, arrays, response, metrics, requested_target, brief, version,
                       weights, block, R_MISSING_THROAT)

    # ---- canonical score ------------------------------------------------------------------
    diag_active = version == 4 and _weight_for(version, weights, "diag") > 0.0
    diag_available = None
    if diag_active:
        assert score is not None and isinstance(params, V4Params)
        try:
            diag_val = _diag_term(metrics, response, requested_target, f, score, params)
            diag_available = (math.isfinite(float(diag_val))
                              and float(diag_val) != float(NAN_TERM_FILL))
        except Exception:  # noqa: BLE001 - private diagnostic seam only
            diag_available = False

    try:
        j, terms = _dispatch(version, metrics, response, requested_target, weights, params)
    except Exception as exc:  # noqa: BLE001 - canonical scorer is expected not to raise
        return ReplayResult(
            status=STATUS_PARTIAL_UNSUPPORTED, reasons=tuple(reasons + [R_METRIC_ARRAY]),
            physical_id=physical_id, metric_id=metric_id, score_id=score_id,
            objective_version=version, metric_source=metric_source,
            design_hash=meta.get("design_hash"), stored_j=_stored_j(meta),
            target=_target_key(requested_target), weights=weights,
            diagnostics={"score_error": f"{type(exc).__name__}: {exc}"},
        )

    # ---- completeness diagnostics ---------------------------------------------------------
    ripple_used_resp = None
    flat_used_resp = None
    if version >= 2:
        if response is None:
            reasons.append(R_NO_RESPONSE)
        else:
            try:
                _vals, ripple_used_resp = _v2_ripple_values(metrics, response, requested_target,
                                                             band)
            except Exception:  # noqa: BLE001
                ripple_used_resp = False
            cuts = _cut_arrays(response, f.size)
            flat_used_resp = (cuts is not None
                              and _on_axis_index(response, cuts[0]) is not None)
            if not ripple_used_resp:
                reasons.append(R_RIPPLE_LEGACY)
            if not flat_used_resp:
                reasons.append(R_FLAT_LEGACY)

    if diag_active and diag_available is False:
        balloon_present = (response is not None and response.balloon_dirs is not None
                           and response.spl_balloon_db is not None)
        reasons.append(R_MISSING_BALLOON if not balloon_present else R_DIAG_UNAVAILABLE)

    if metric_source == "regenerated" and stored_metrics is None and R_NO_METRICS not in reasons:
        # regeneration is fine; only note it when it replaced absent stored metrics.
        pass

    if R_NO_RESPONSE in reasons and version >= 2:
        # metrics-only replay is diagnostic, never exact.
        pass

    reasons = _dedupe(reasons)
    status = _status_for(reasons)

    orig = _stored_j(meta)
    stored_version = meta.get("objective_version")
    try:
        stored_version_int = int(stored_version) if stored_version is not None else 1
    except (TypeError, ValueError):
        stored_version_int = None
    # A stored J is only a parity reference when it was produced by the same objective version.
    # Replaying a v3 row under v4 is a legitimate re-score, not a parity failure.
    parity = None
    if (orig is not None and j is not None and not target_changed
            and weights_override is None and objective_params_override is None
            and stored_target_verified and stored_version_int == version):
        parity = float(j) - float(orig)

    _, metric_id, score_id = _identity(
        meta, arrays, response, metrics, requested_target, metric_source, version, weights,
        block, brief)

    return ReplayResult(
        status=status, reasons=tuple(reasons), physical_id=physical_id, metric_id=metric_id,
        score_id=score_id, objective_version=version, metric_source=metric_source,
        design_hash=meta.get("design_hash"), j=(None if j is None else float(j)),
        terms=dict(terms), stored_j=orig, parity_delta=parity,
        target=_target_key(requested_target), weights=dict(weights),
        diagnostics={
            "target_changed": bool(target_changed),
            "stored_target_verified": bool(stored_target_verified),
            "ripple_used_response": ripple_used_resp,
            "flat_used_response": flat_used_resp,
            "diag_active": bool(diag_active),
            "diag_available": diag_available,
            "stored_metrics_used": metric_source == "stored",
            "band_bins": int(band.sum()),
            "f0_score_bins": (int((band & (f >= requested_target.f0_effective_hz())).sum())
                              if version >= 3 else None),
        },
    )


def _dedupe(reasons: list[str]) -> list[str]:
    seen = set()
    out = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _status_for(reasons: list[str]) -> str:
    if any(r.split(":", 1)[0] in _HARD_REASONS for r in reasons):
        return STATUS_ADDITIONAL_DATA_OR_SOLVE_REQUIRED
    if any(r.split(":", 1)[0] in _PARTIAL_REASONS for r in reasons):
        return STATUS_PARTIAL_UNSUPPORTED
    return STATUS_EXACT_COMPLETE


def _refuse(meta, arrays, response, metrics, target: Target | None, brief: Brief | None,
            version: int, weights, block, reason: str) -> ReplayResult:
    physical_id, metric_id, score_id = _identity(
        meta, arrays, response, metrics, target, "unavailable", version, weights, block, brief)
    return ReplayResult(
        status=STATUS_ADDITIONAL_DATA_OR_SOLVE_REQUIRED, reasons=(reason,),
        physical_id=physical_id, metric_id=metric_id, score_id=score_id,
        objective_version=version, metric_source="unavailable",
        design_hash=(meta or {}).get("design_hash"), stored_j=_stored_j(meta),
        target=_target_key(target), weights=(None if weights is None else dict(weights)),
        diagnostics={},
    )


# ------------------------------------------------------------------ public entry points

def replay_record(meta: dict | None, arrays: dict | None, *, brief: Brief | str | None = None,
                  target: Target | dict | None = None, weights: dict | None = None,
                  objective_params=None, objective_version: int | None = None,
                  regenerate_metrics: bool | None = None,
                  allow_metric_regeneration: bool = True) -> ReplayResult:
    """Replay one stored record.

    ``meta``/``arrays`` are the dataset record metadata and array dict. ``brief`` may be a
    :class:`Brief`, a path, or omitted when the target/weights/objective block are supplied
    explicitly. The record's own ``target`` is the source of truth for "original replay"; passing
    ``target`` requests a supported target/band/coverage change (which regenerates target-dependent
    metrics from the response arrays, never reweights stored terms).
    """
    if isinstance(brief, (str, Path)):
        brief = load_brief_context(brief)
    if isinstance(target, dict):
        target = Target.from_dict(target)
    response, _response_reason = _response_from_arrays(meta, arrays)
    metrics, metric_reasons = _metricset_from_arrays(meta, arrays, target)
    # The stored metric arrays are the original table; ``_replay_core`` decides whether they may be
    # used (target unchanged) or must be regenerated (target change).
    return _replay_core(
        meta, arrays, response=response, stored_metrics=metrics,
        stored_metric_reasons=metric_reasons, brief=brief, target=target,
        weights_override=weights, objective_params_override=objective_params,
        objective_version_override=objective_version, regenerate_metrics=regenerate_metrics,
        allow_metric_regeneration=allow_metric_regeneration,
    )


def _metrics_from_json(payload: dict | None) -> MetricSet | None:
    """Run-dir ``metrics.json`` -> MetricSet (parsing only; no formula)."""
    if not payload:
        return None

    def arr(name, n: int | None = None, typ=float):
        raw = payload.get(name)
        if raw is None:
            return None if n is None else np.full(n, np.nan)
        return np.array([np.nan if v is None else v for v in raw], dtype=typ)

    f = arr("freqs_hz")
    if f is None:
        return None
    n = f.size
    return MetricSet(
        freqs_hz=f, bw_h_deg=arr("bw_h_deg", n), bw_v_deg=arr("bw_v_deg", n),
        di_db=arr("di_db", n),
        di_source=str(payload.get("di_source") or "balloon"),
        ripple_h_db=arr("ripple_h_db", n), ripple_v_db=arr("ripple_v_db", n),
        on_axis_db=arr("on_axis_db", n), z_throat_real=arr("z_throat_real", n),
        scalars=dict(payload.get("scalars") or {}),
    )


def replay_run_dir(run_dir, design_hash: str | None = None, *, brief: Brief | str | None = None,
                   config_path=None, target: Target | dict | None = None,
                   weights: dict | None = None, objective_params=None,
                   objective_version: int | None = None,
                   regenerate_metrics: bool | None = None,
                   allow_metric_regeneration: bool = True) -> ReplayResult:
    """Replay a run directory's stored ``response.npz`` + ``metrics.json``.

    ``run_dir/designs/<hash>/`` is tried first, then ``run_dir/verify/designs/<hash>/``. Nothing
    is written; the solve cache's read-only loader is used.
    """
    run_dir = Path(run_dir)
    if design_hash is None:
        dirs = sorted((run_dir / "designs").glob("*")) if (run_dir / "designs").is_dir() else []
        if len(dirs) != 1:
            raise ValueError("replay_run_dir: pass design_hash when the run has != 1 design")
        design_hash = dirs[0].name

    candidates = [run_dir / "designs" / design_hash,
                  run_dir / "verify" / "designs" / design_hash]
    ddir = next((p for p in candidates if p.is_dir()), None)
    if ddir is None:
        raise FileNotFoundError(f"replay_run_dir: no design directory for {design_hash!r}")

    if isinstance(brief, (str, Path)):
        brief = load_brief_context(brief)
    if isinstance(target, dict):
        target = Target.from_dict(target)

    # Resolve the run's original target from its config (if present) separately from the brief used
    # to re-score. An explicit brief may be a *variant*; the run config still defines the stored
    # target identity, which is what target-change detection must compare against.
    cfg_brief = None
    cfg_path = Path(config_path) if config_path is not None else run_dir / "config.yaml"
    if cfg_path.is_file():
        try:
            cfg_brief = brief_from_config(cfg_path)
        except Exception:  # noqa: BLE001 - fall back to explicit args / record target
            cfg_brief = None
    if brief is None:
        brief = cfg_brief

    response = None
    rp = ddir / "response.npz"
    if rp.is_file():
        from ..solve.cache import load_response
        response = load_response(rp)

    metrics_payload = None
    mp = ddir / "metrics.json"
    if mp.is_file():
        try:
            metrics_payload = json.loads(mp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            metrics_payload = None
    stored_metrics = _metrics_from_json(metrics_payload)

    design: dict = {}
    dp = ddir / "design.json"
    if dp.is_file():
        try:
            design = json.loads(dp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            design = {}
    status: dict = {}
    sp = ddir / "status.json"
    if sp.is_file():
        try:
            status = json.loads(sp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            status = {}

    arrays = _arrays_from_response(response) if response is not None else {}
    if metrics_payload:
        for k in ("bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db", "ripple_v_db",
                  "on_axis_db", "z_throat_real"):
            if k in metrics_payload:
                arrays[k] = np.asarray(metrics_payload[k], dtype=float)
        # metrics.json stores z as REAL; response.npz carries the complex array.
        if "z_throat_real" in arrays and "z_throat" not in arrays:
            arrays["z_throat"] = arrays.pop("z_throat_real").astype(complex)

    base_target_dict = (cfg_brief.target if cfg_brief is not None
                        else (brief.target if brief is not None else None))
    stored_version = status.get("objective_version")
    if stored_version is None and cfg_brief is not None:
        stored_version = cfg_brief.objective_version
    meta = {
        "ok": bool(status.get("ok", True)),
        "design_hash": design_hash,
        "mesh_hash": status.get("mesh_hash") or design.get("mesh_hash"),
        "solve_hash": status.get("solve_hash") or design.get("solve_hash"),
        "family": design.get("family") or status.get("family") or "",
        "params": design.get("params") or {},
        "mesh": status.get("mesh") or {},
        "solve": {
            "backend": (response.backend if response is not None else status.get("backend")),
            "mode": status.get("mode"),
            "freqs_hz": (list(response.freqs_hz) if response is not None else []),
            "observation": status.get("observation") or {},
            "seconds": status.get("seconds"),
            "n_dof": (response.n_dof if response is not None else status.get("n_dof")),
        },
        "excitation": status.get("excitation"),
        "lib_shas": status.get("lib_shas") or {},
        "metrics_scalars": (dict((metrics_payload or {}).get("scalars") or {})),
        "objective": status.get("objective"),
        "objective_version": (1 if stored_version is None else stored_version),
        "target": (dataclasses.asdict(base_target_dict) if base_target_dict is not None else None),
    }
    return _replay_core(
        meta, arrays, response=response, stored_metrics=stored_metrics,
        stored_metric_reasons=[], brief=brief, target=target, weights_override=weights,
        objective_params_override=objective_params,
        objective_version_override=objective_version, regenerate_metrics=regenerate_metrics,
        allow_metric_regeneration=allow_metric_regeneration,
    )
