"""Objective v11 (2026-11-20, owner-directed): v10 plus a CD-matrix block.

V11 is a NEW identity: v10 (v9 corridor/target profile + preferred-edge ripple) **plus** the
constant-directivity matrix from ``docs/research/cd_metrics_2026-11-20/V11_CD_MATRIX.md``. It never
edits v9/v10 and never ranks against them.

The CD block lives in ``objective.cd`` and is REQUIRED for v11 (there is no default; a v11 brief
without it is a config error). Its shape::

    objective:
      version: 11
      # ... every v10 key unchanged (ripple_region: preferred_edge, tolerances, ...)
      cd:
        band_hz: [700.0, 8000.0]
        window_h_deg: 30.0
        window_v_deg: 10.0
        lw:      {weight: 1.5, tolerance_db: 1.5}
        di_std:  {weight: 0.75, tolerance_db: 1.0}
        nacc:    {weight: 0.75, tolerance: 0.02}
        offaxis: {weight: 1.0, tolerance_db: 1.0, reference: band_mean,
                  band_hz: [2500.0, 8000.0],
                  angles_h_deg: [-40, -30, 30, 40], angles_v_deg: [-25, -10, 10, 25]}
        report:  {omega: true, contour: false}

The weighted term set is the v9 weighted keys (``di_roughness`` stays a separate bumpiness term)
plus ``cd_lw``, ``cd_di_std``, ``cd_nacc`` and ``offaxis_smooth``. Base weights are the brief's
``weights:`` block resolved through :func:`resolve_v9_weights`; the CD weights/tolerances come
ONLY from ``objective.cd``. ``cd_omega_2pi`` and ``cd_status`` are report-only and always emitted.

``objective_v11`` never raises and never returns nan or inf in the weighted total. Pure numpy plus
the pure-numpy ``metrics.cd`` module; no solver.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
from dataclasses import dataclass

from ..targets.spec import Target
from .scalar_v10 import V10_ALL_KEYS, V10Params, _objective_v10
from .scalar_v9 import (V9_BOOKKEEPING_KEYS, V9_DIAGNOSTIC_KEYS, V9_OPTIONAL_WEIGHTED_KEYS,
                        V9_UNWEIGHTED_KEYS, V9_WEIGHTED_KEYS, _on_score_grid, resolve_v9_weights)
from .terms import NAN_TERM_FILL, PENALTY_FAILED

log = logging.getLogger("hornlab_search.objective.scalar_v11")

__all__ = ["objective_v11", "V11Params", "CDParams", "V11_ALL_KEYS", "V11_CD_KEYS",
           "V11_SCORE_IDENTITY_NAME", "resolve_v11_weights", "worst_valid_v11_j",
           "v11_score_identity"]

#: The four CD terms that enter the weighted sum (``cd_status_code``/``cd_omega_2pi`` report-only).
V11_CD_TERM_KEYS = ("cd_lw", "cd_di_std", "cd_nacc", "offaxis_smooth")
#: Every key v11 adds to the v10 term row. ``terms`` holds floats only: the status is a numeric
#: code (see :data:`CD_STATUS_CODES`) so stored-term/report code is never handed a string.
V11_CD_KEYS = V11_CD_TERM_KEYS + ("cd_omega_2pi", "cd_status_code")
#: The v11 term row: v10's keys plus the CD keys.
V11_ALL_KEYS = V10_ALL_KEYS + V11_CD_KEYS
V11_SCORE_IDENTITY_NAME = "objective_v11_cd_matrix"
#: ``cd_status`` (from ``metrics.cd``) -> ``cd_status_code`` stored in ``terms``.
CD_STATUS_BALLOON = 0.0
CD_STATUS_CUTS_FALLBACK = 1.0
CD_STATUS_UNMEASURABLE = 2.0
CD_STATUS_CODES = {"balloon": CD_STATUS_BALLOON, "cuts_fallback": CD_STATUS_CUTS_FALLBACK,
                   "unmeasurable": CD_STATUS_UNMEASURABLE}
#: ``cd_omega_2pi`` is report-only; -1.0 means "not measurable" (never NaN, never NAN_TERM_FILL).
CD_OMEGA_2PI_UNMEASURABLE = -1.0

_CD_BLOCK_KEYS = {"band_hz", "window_h_deg", "window_v_deg", "lw", "di_std", "nacc", "offaxis",
                  "report"}
_LW_KEYS = {"weight", "tolerance_db"}
_DI_STD_KEYS = {"weight", "tolerance_db"}
_NACC_KEYS = {"weight", "tolerance"}
_OFFAXIS_KEYS = {"weight", "tolerance_db", "reference", "band_hz", "angles_h_deg",
                 "angles_v_deg"}
_REPORT_KEYS = {"omega", "contour"}
_REFERENCES = ("band_mean", "trend")


def _finite(value, where: str, *, minimum: float | None = None, maximum: float | None = None,
            strictly_gt: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{where} must be a finite number, got {value!r}")
    v = float(value)
    if not math.isfinite(v):
        raise ValueError(f"{where} must be a finite number, got {value!r}")
    if strictly_gt:
        if not v > (minimum if minimum is not None else 0.0):
            raise ValueError(f"{where} must be > {minimum if minimum is not None else 0.0:g}, "
                             f"got {value!r}")
    elif minimum is not None and v < minimum:
        raise ValueError(f"{where} must be >= {minimum:g}, got {value!r}")
    if maximum is not None and v > maximum:
        raise ValueError(f"{where} must be <= {maximum:g}, got {value!r}")
    return v


def _band_pair(raw, where: str) -> tuple[float, float]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise ValueError(f"{where} must be a [lo, hi] pair, got {raw!r}")
    lo = _finite(raw[0], f"{where}[0]")
    hi = _finite(raw[1], f"{where}[1]")
    if not lo < hi:
        raise ValueError(f"{where} must have lo < hi, got {raw!r}")
    return lo, hi


def _angle(raw, where: str) -> float:
    return _finite(raw, where, minimum=-90.0, maximum=90.0)


def _angle_list(raw, where: str) -> list[float]:
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError(f"{where} must be a non-empty list of angles, got {raw!r}")
    return [_angle(v, f"{where}[{i}]") for i, v in enumerate(raw)]


def _weight_tolerance(raw, name: str, tol_key: str, allowed: set[str]) -> dict:
    where = f"objective.cd.{name}"
    if not isinstance(raw, dict):
        raise ValueError(f"{where} must be a mapping with keys {sorted(allowed)}, got {raw!r}")
    unknown = sorted(set(raw) - allowed)
    missing = sorted(allowed - set(raw))
    if unknown or missing:
        raise ValueError(f"{where}: missing {missing}, unknown {unknown} "
                         f"(required: {sorted(allowed)})")
    return {"weight": _finite(raw["weight"], f"{where}.weight", minimum=0.0),
            tol_key: _finite(raw[tol_key], f"{where}.{tol_key}", strictly_gt=True)}


def _validate_offaxis(raw) -> dict:
    where = "objective.cd.offaxis"
    if not isinstance(raw, dict):
        raise ValueError(f"{where} must be a mapping with keys {sorted(_OFFAXIS_KEYS)}, "
                         f"got {raw!r}")
    unknown = sorted(set(raw) - _OFFAXIS_KEYS)
    missing = sorted(_OFFAXIS_KEYS - set(raw))
    if unknown or missing:
        raise ValueError(f"{where}: missing {missing}, unknown {unknown} "
                         f"(required: {sorted(_OFFAXIS_KEYS)})")
    ref = raw["reference"]
    if ref not in _REFERENCES:
        raise ValueError(f"{where}.reference must be one of {list(_REFERENCES)}, got {ref!r}")
    return {
        "weight": _finite(raw["weight"], f"{where}.weight", minimum=0.0),
        "tolerance_db": _finite(raw["tolerance_db"], f"{where}.tolerance_db", strictly_gt=True),
        "reference": str(ref),
        "band_hz": _band_pair(raw["band_hz"], f"{where}.band_hz"),
        "angles_h_deg": _angle_list(raw["angles_h_deg"], f"{where}.angles_h_deg"),
        "angles_v_deg": _angle_list(raw["angles_v_deg"], f"{where}.angles_v_deg"),
    }


def _validate_report(raw) -> dict:
    where = "objective.cd.report"
    if not isinstance(raw, dict):
        raise ValueError(f"{where} must be a mapping with keys {sorted(_REPORT_KEYS)}, "
                         f"got {raw!r}")
    unknown = sorted(set(raw) - _REPORT_KEYS)
    missing = sorted(_REPORT_KEYS - set(raw))
    if unknown or missing:
        raise ValueError(f"{where}: missing {missing}, unknown {unknown} "
                         f"(required: {sorted(_REPORT_KEYS)})")
    out = {}
    for k in ("omega", "contour"):
        v = raw[k]
        if not isinstance(v, bool):
            raise ValueError(f"{where}.{k} must be true or false, got {v!r}")
        out[k] = v
    return out


@dataclass(frozen=True)
class CDParams:
    """The validated ``objective.cd`` block. There is NO default: v11 requires it."""

    band_hz: tuple[float, float]
    window_h_deg: float
    window_v_deg: float
    lw: dict
    di_std: dict
    nacc: dict
    offaxis: dict
    report: dict

    @classmethod
    def from_block(cls, block) -> "CDParams":
        if block is None:
            raise ValueError("objective v11 requires an objective.cd mapping (no default; see "
                             "docs/research/cd_metrics_2026-11-20/V11_CD_MATRIX.md)")
        if not isinstance(block, dict):
            raise ValueError(f"objective.cd must be a mapping, got {block!r}")
        unknown = sorted(set(block) - _CD_BLOCK_KEYS)
        missing = sorted(_CD_BLOCK_KEYS - set(block))
        if unknown or missing:
            raise ValueError(f"objective.cd: missing {missing}, unknown {unknown} "
                             f"(required: {sorted(_CD_BLOCK_KEYS)})")
        return cls(
            band_hz=_band_pair(block["band_hz"], "objective.cd.band_hz"),
            window_h_deg=_finite(block["window_h_deg"], "objective.cd.window_h_deg",
                                 minimum=0.0, maximum=90.0, strictly_gt=True),
            window_v_deg=_finite(block["window_v_deg"], "objective.cd.window_v_deg",
                                 minimum=0.0, maximum=90.0, strictly_gt=True),
            lw=_weight_tolerance(block["lw"], "lw", "tolerance_db", _LW_KEYS),
            di_std=_weight_tolerance(block["di_std"], "di_std", "tolerance_db", _DI_STD_KEYS),
            nacc=_weight_tolerance(block["nacc"], "nacc", "tolerance", _NACC_KEYS),
            offaxis=_validate_offaxis(block["offaxis"]),
            report=_validate_report(block["report"]),
        )

    def to_block(self) -> dict:
        return {
            "band_hz": [float(self.band_hz[0]), float(self.band_hz[1])],
            "window_h_deg": float(self.window_h_deg),
            "window_v_deg": float(self.window_v_deg),
            "lw": dict(self.lw),
            "di_std": dict(self.di_std),
            "nacc": dict(self.nacc),
            "offaxis": {
                "weight": float(self.offaxis["weight"]),
                "tolerance_db": float(self.offaxis["tolerance_db"]),
                "reference": str(self.offaxis["reference"]),
                "band_hz": [float(self.offaxis["band_hz"][0]),
                            float(self.offaxis["band_hz"][1])],
                "angles_h_deg": [float(a) for a in self.offaxis["angles_h_deg"]],
                "angles_v_deg": [float(a) for a in self.offaxis["angles_v_deg"]],
            },
            "report": dict(self.report),
        }


@dataclass(frozen=True)
class V11Params:
    """A v11 ``objective:`` block: a validated :class:`V10Params` plus :class:`CDParams`."""

    v10: V10Params
    cd: CDParams

    def __getattr__(self, name):
        # Callers that read v9/v10 fields see the wrapped object's values.
        if name in ("v10", "cd"):
            raise AttributeError(name)
        return getattr(self.v10, name)

    def weighted_keys(self) -> tuple[str, ...]:
        return self.v10.weighted_keys()

    @classmethod
    def from_block(cls, block: dict) -> "V11Params":
        if not isinstance(block, dict):
            raise ValueError("objective must be a mapping")
        if block.get("version") != 11:
            raise ValueError(f"V11Params needs objective.version 11, got {block.get('version')!r}")
        if "cd" not in block:
            raise ValueError("objective v11 requires an objective.cd mapping (no default)")
        cd = CDParams.from_block(block["cd"])
        rest = {k: v for k, v in block.items() if k not in ("cd", "version")}
        rest["version"] = 10          # V10Params validates its own version key
        return cls(v10=V10Params.from_block(rest), cd=cd)

    def to_block(self) -> dict:
        out = self.v10.to_block()
        out["version"] = 11
        out["cd"] = self.cd.to_block()
        return out


def resolve_v11_weights(weights: dict | None, params: V11Params | None = None) -> dict:
    """v9 base weights (through :func:`resolve_v9_weights`) plus the CD weights.

    CD weights come ONLY from ``objective.cd`` (``params.cd``), never from the brief's
    ``weights:`` block.
    """
    p9 = None if params is None else params.v10.v9
    out = resolve_v9_weights(weights, p9)
    if params is not None:
        cd = params.cd
        out["cd_lw"] = float(cd.lw["weight"])
        out["cd_di_std"] = float(cd.di_std["weight"])
        out["cd_nacc"] = float(cd.nacc["weight"])
        out["offaxis_smooth"] = float(cd.offaxis["weight"])
    else:
        for k in V11_CD_TERM_KEYS:
            out.setdefault(k, 0.0)
    return out


def _base_tolerance(p9, key: str) -> float:
    if key == "hf_floor":
        return float(p9.hf_floor["tolerance"]) if p9.hf_floor is not None else 1.0
    if key == "constancy":
        return float(p9.constancy["tolerance"]) if p9.constancy is not None else 1.0
    return float(p9.tolerances[key])


def worst_valid_v11_j(params: V11Params, weights: dict | None) -> float:
    """J of a VALID design whose every weighted term is unmeasurable.

    Base terms follow v9's convention (raw ``NAN_TERM_FILL`` normalised by the tolerance); a
    missing/unmeasurable CD value is the normalised ``NAN_TERM_FILL`` directly (the task's CD
    convention). The config gate requires this to sit far below ``PENALTY_INVALID``.
    """
    w = resolve_v11_weights(weights, params)
    p9 = params.v10.v9
    total = sum(w[k] * NAN_TERM_FILL / _base_tolerance(p9, k) for k in p9.weighted_keys())
    for k, tol in (("cd_lw", params.cd.lw["tolerance_db"]),
                   ("cd_di_std", params.cd.di_std["tolerance_db"]),
                   ("cd_nacc", params.cd.nacc["tolerance"]),
                   ("offaxis_smooth", params.cd.offaxis["tolerance_db"])):
        total += w[k] * NAN_TERM_FILL
    return float(total)


def v11_score_identity(params: V11Params) -> dict:
    """Stable identity of a v11 scoring definition: name + normalised block + sha256."""
    block = params.to_block()
    canon = json.dumps(block, sort_keys=True, separators=(",", ":"))
    return {"name": V11_SCORE_IDENTITY_NAME, "block": block,
            "sha256": hashlib.sha256(canon.encode("utf-8")).hexdigest()}


def _v11_penalty(value: float = PENALTY_FAILED, *, n_in_band: int = 0) -> tuple[float, dict]:
    """The failure row: every v11 key present and finite; weighted terms 0.0, reports fill."""
    t = {k: 0.0 for k in (V9_WEIGHTED_KEYS + V9_OPTIONAL_WEIGHTED_KEYS + V9_UNWEIGHTED_KEYS)}
    t.update({k: 0.0 for k in V9_BOOKKEEPING_KEYS})
    t["penalty"] = float(value)
    t["total"] = float(value)
    t["n_in_band"] = int(n_in_band)
    for k in V9_DIAGNOSTIC_KEYS:
        t[k] = NAN_TERM_FILL
    for k in V11_CD_TERM_KEYS:
        t[k] = 0.0
    t["cd_omega_2pi"] = CD_OMEGA_2PI_UNMEASURABLE
    t["cd_status_code"] = CD_STATUS_UNMEASURABLE
    assert set(t) == set(V11_ALL_KEYS)
    return float(value), t


def objective_v11(metrics, resp, ok, target: Target, weights: dict | None, params: V11Params):
    """Score one evaluation under objective v11. ``(J, terms)``; ``terms`` has ``V11_ALL_KEYS``."""
    try:
        if not isinstance(params, V11Params):
            raise ValueError("objective_v11 needs V11Params")
        if ok and params.v10.v9.score_grid is not None:
            metrics, resp = _on_score_grid(metrics, resp, target, params.v10.v9)
        return _objective_v11(metrics, resp, ok, target, weights, params)
    except Exception:  # noqa: BLE001 - the contract says never raises
        log.exception("objective_v11() failed; returning the failure penalty")
        return _v11_penalty(PENALTY_FAILED)


def _cd_values(metrics, resp, cd: CDParams) -> dict:
    """Call the pure-numpy CD module; an import/implementation failure is unmeasurable, not fatal."""
    try:
        from ..metrics.cd import cd_metrics
        raw = cd_metrics(metrics, resp, cd.band_hz, cd.window_h_deg, cd.window_v_deg,
                         cd.offaxis["band_hz"], cd.offaxis["angles_h_deg"],
                         cd.offaxis["angles_v_deg"], cd.offaxis["reference"])
        return raw if isinstance(raw, dict) else {}
    except Exception:  # noqa: BLE001 - a missing CD module/value is an unmeasurable term
        log.exception("cd_metrics() failed; CD terms are unmeasurable")
        return {}


def _norm_cd(raw_val, tolerance: float) -> float:
    """A CD raw value normalised by its tolerance; unmeasurable -> ``NAN_TERM_FILL``."""
    try:
        v = float(raw_val)
    except (TypeError, ValueError):
        return float(NAN_TERM_FILL)
    return float(v / tolerance) if math.isfinite(v) else float(NAN_TERM_FILL)


def _norm_nacc(raw_val, tolerance: float) -> float:
    """``(1 - nacc) / tolerance``; unmeasurable -> ``NAN_TERM_FILL``."""
    try:
        v = float(raw_val)
    except (TypeError, ValueError):
        return float(NAN_TERM_FILL)
    return float((1.0 - v) / tolerance) if math.isfinite(v) else float(NAN_TERM_FILL)


def _objective_v11(metrics, resp, ok, target: Target, weights, params: V11Params):
    p9 = params.v10.v9
    j10, t10 = _objective_v10(metrics, resp, ok, target, weights, params.v10)
    if float(t10.get("penalty", 0.0)) > 0.0:
        return _v11_penalty(float(t10["penalty"]), n_in_band=int(t10.get("n_in_band", 0) or 0))

    w = resolve_v11_weights(weights, params)
    t = dict(t10)

    # Reconstruct the raw existing terms from the normalised v10 row, then re-normalise through
    # the same (v9) tolerances. HF/constancy are optional keys, present only when declared.
    active_base = list(p9.weighted_keys())
    for k in active_base:
        tol = _base_tolerance(p9, k)
        raw_k = float(t10[k]) * tol
        t[k] = raw_k / tol

    cd_raw = _cd_values(metrics, resp, params.cd)
    t["cd_lw"] = _norm_cd(cd_raw.get("cd_lw_db"), params.cd.lw["tolerance_db"])
    t["cd_di_std"] = _norm_cd(cd_raw.get("cd_di_std_db"), params.cd.di_std["tolerance_db"])
    t["cd_nacc"] = _norm_nacc(cd_raw.get("cd_nacc"), params.cd.nacc["tolerance"])
    t["offaxis_smooth"] = _norm_cd(cd_raw.get("offaxis_smooth_db"),
                                   params.cd.offaxis["tolerance_db"])

    omega = cd_raw.get("cd_omega_2pi")
    try:
        omega_f = float(omega)
        t["cd_omega_2pi"] = omega_f if math.isfinite(omega_f) else CD_OMEGA_2PI_UNMEASURABLE
    except (TypeError, ValueError):
        t["cd_omega_2pi"] = CD_OMEGA_2PI_UNMEASURABLE
    status = cd_raw.get("cd_status")
    code = CD_STATUS_CODES.get(status) if isinstance(status, str) else None
    t["cd_status_code"] = CD_STATUS_UNMEASURABLE if code is None else code

    total = math.fsum(w[k] * t[k] for k in active_base)
    total += math.fsum(w[k] * t[k] for k in V11_CD_TERM_KEYS)
    if not math.isfinite(total):
        return _v11_penalty(PENALTY_FAILED, n_in_band=int(t10.get("n_in_band", 0) or 0))

    t["penalty"] = 0.0
    t["total"] = float(total)
    assert set(t) == set(V11_ALL_KEYS)
    return float(total), t
