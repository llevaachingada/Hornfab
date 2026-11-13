"""Canonical v4 raw metric policy for advisory BO (protocol bo-study-v1.1, M2).

This module freezes the *inputs* the locked metric contract requires from the **resolved
brief**: the v4 objective parameters, tolerances, weights, target/band/f0 support, frequency
weights and the response-detrended ripple requirement.  It deliberately implements no scoring
formula: all coverage/ripple math stays in the canonical ``objective`` helpers.

Two things are refused rather than silently repaired:

* the legacy stored-ripple fallback is a **distinct metric identity**
  (:func:`make_legacy_ripple_policy`), never pooled under the response-detrended label;
* malformed declared per-plane masks/weights (missing bins, unequal support, an empty scored
  mask, invalid weights, zero total weight) raise a reason-coded ``ValueError``.

No GP/torch/botorch import exists anywhere in this file.  The compatibility helpers at the
bottom (:func:`freeze_metric_policy`/:func:`measure_metrics`) predate this policy seam and only
delegate measurements to the existing scalar helpers; they are kept so the provisional B3
adapter test remains valid.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from pathlib import Path
from typing import NoReturn

import numpy as np

from ..metrics import smoothness
from ..objective import scalar_v2, scalar_v8
from ..objective.replay import Brief, load_brief_context
from ..objective.scalar_v4 import V4Params, resolve_v4_weights
from ..objective.terms import NAN_TERM_FILL
from ..targets.spec import Target

# ------------------------------------------------------------------ identity labels

RIPPLE_RESPONSE_DETRENDED = "response_detrended_required"
RIPPLE_LEGACY = "legacy_stored_ripple_partial"
METRIC_SCHEMA = "bo-physical-metric-v1"
REQUIRED_COV_NARROW_RATIO = 2.0

#: Reason codes carried by ``ValueError`` labels (the text after ``:`` is diagnostic only).
R_UNSUPPORTED_OBJECTIVE = "unsupported_objective_version"
R_MISSING_TARGET = "missing_target"
R_MISSING_OBJECTIVE_BLOCK = "missing_objective_block"
R_COV_NARROW_RATIO = "cov_narrow_ratio_not_2"
R_COV_BELOW_F0 = "unsupported_cov_below_f0"
R_DIAG_REFERENCE = "unsupported_diag_reference"
R_INVALID_WEIGHTS = "invalid_weights"
R_ZERO_TOTAL_WEIGHT = "zero_total_weight"
R_INVALID_FREQS = "invalid_frequency_support"
R_NO_SCORED_MASK = "no_scored_mask"
R_UNEQUAL_SUPPORT = "unequal_support"
R_MISSING_BINS = "unexpected_missing_bins"
R_EXTRA_BINS = "unexpected_extra_bins"
R_MASK_MISMATCH = "declared_mask_mismatch"
R_INVALID_RESTRICTION = "invalid_restricted_mask"
R_RIPPLE_LEGACY_FALLBACK = "ripple_legacy_fallback"
R_NO_SCORED_SUPPORT = "no_scored_support"

REASONS = {
    R_UNSUPPORTED_OBJECTIVE: "only the resolved objective v4 brief is supported",
    R_MISSING_TARGET: "the resolved brief carries no target",
    R_MISSING_OBJECTIVE_BLOCK: "objective v4 requires its validated objective block",
    R_COV_NARROW_RATIO: "the frozen ATH task requires cov_narrow_ratio == 2.0",
    R_COV_BELOW_F0: "only the f0-masked coverage convention is supported",
    R_DIAG_REFERENCE: "only the round-diagonal reference is supported",
    R_INVALID_WEIGHTS: "frequency weights must be finite and nonnegative",
    R_ZERO_TOTAL_WEIGHT: "every scored mask must carry a positive total weight",
    R_INVALID_FREQS: "frequencies must be finite, positive and strictly increasing",
    R_NO_SCORED_MASK: "a declared/derived scored mask is empty",
    R_UNEQUAL_SUPPORT: "declared mask/weight arrays must share one support length",
    R_MISSING_BINS: "declared masks drop bins the frozen target requires",
    R_EXTRA_BINS: "declared masks add bins outside the frozen target support",
    R_MASK_MISMATCH: "declared masks differ from the frozen policy for another reason",
    R_INVALID_RESTRICTION: "a shared restriction needs a name and a proper non-empty subset",
    R_RIPPLE_LEGACY_FALLBACK: "ripple did not use the response-detrended branch",
    R_NO_SCORED_SUPPORT: "scored support must be a non-empty boolean mask",
}


def _raise(code: str, detail: str) -> NoReturn:
    raise ValueError(f"{code}: {detail}")


# ------------------------------------------------------------------ helpers


def _coerce_brief(brief) -> Brief:
    if isinstance(brief, Brief):
        return brief
    if isinstance(brief, (str, Path)):
        return load_brief_context(brief)
    raise TypeError(f"resolve_metric_policy needs a resolved Brief or brief path, got {type(brief)!r}")


def _canonical_weights(weights: dict | None) -> dict:
    resolved = resolve_v4_weights(dict(weights or {}))
    for key, value in resolved.items():
        try:
            x = float(value)
        except (TypeError, ValueError):
            _raise(R_INVALID_WEIGHTS, f"weight {key!r}={value!r} is not a number")
        if not math.isfinite(x) or x < 0.0:
            _raise(R_INVALID_WEIGHTS, f"weight {key!r}={value!r} must be finite and nonnegative")
        resolved[key] = x
    return {k: resolved[k] for k in sorted(resolved)}


def _freq_weights_signature(target: Target) -> tuple[tuple[float, float, float], ...]:
    raw = getattr(target, "freq_weights", None)
    if raw is None:
        return ()
    if not isinstance(raw, dict) or not isinstance(raw.get("band_hz"), (list, tuple)):
        _raise(R_INVALID_WEIGHTS, "freq_weights must be a mapping with a band_hz list")
    out: list[tuple[float, float, float]] = []
    for row in raw["band_hz"]:
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            _raise(R_INVALID_WEIGHTS, f"freq_weights row must be [lo_hz, hi_hz, w], got {row!r}")
        try:
            lo, hi, w = (float(row[0]), float(row[1]), float(row[2]))
        except (TypeError, ValueError):
            _raise(R_INVALID_WEIGHTS, f"freq_weights row must be numeric, got {row!r}")
        if not (math.isfinite(lo) and math.isfinite(hi) and math.isfinite(w)) or w < 0.0:
            _raise(R_INVALID_WEIGHTS, f"freq_weights row must be finite/nonnegative, got {row!r}")
        out.append((lo, hi, w))
    return tuple(sorted(out))


def _as_frequencies(freqs_hz) -> np.ndarray:
    f = np.asarray(freqs_hz, dtype=float)
    if (f.ndim != 1 or f.size == 0 or not np.all(np.isfinite(f))
            or np.any(f <= 0.0) or np.any(np.diff(f) <= 0.0)):
        _raise(R_INVALID_FREQS, "frequencies must be finite, positive and strictly increasing")
    return f


def _expected_masks(f: np.ndarray, target: Target) -> dict[str, np.ndarray]:
    band = (f >= float(target.band_lo_hz)) & (f <= float(target.band_hi_hz))
    if not band.any():
        _raise(R_NO_SCORED_MASK, "no stored frequency lies inside the target band")
    h = band & (f >= target.f0_effective_hz())
    f0_v = target.f0_v_hz if target.f0_v_hz is not None else target.f0_effective_hz()
    v = band & (f >= float(f0_v))
    masks = {"ripple": band, "coverage_h": h, "coverage_v": v}
    for name, mask in masks.items():
        if not mask.any():
            _raise(R_NO_SCORED_MASK, f"the {name} mask has no scored bins")
    return masks


def _as_mask(name: str, value, shape: tuple[int, ...]) -> np.ndarray:
    arr = np.asarray(value)
    if arr.dtype != np.bool_:
        _raise(R_MASK_MISMATCH, f"declared mask {name!r} must be boolean, got dtype {arr.dtype}")
    if arr.shape != shape:
        _raise(R_UNEQUAL_SUPPORT,
               f"declared mask {name!r} has shape {arr.shape}, expected {shape}")
    if not arr.any():
        _raise(R_NO_SCORED_MASK, f"declared mask {name!r} is empty")
    return arr


def _check_weight_totals(weights: np.ndarray, masks: dict[str, np.ndarray]) -> None:
    if weights.shape != next(iter(masks.values())).shape:
        _raise(R_UNEQUAL_SUPPORT, "frequency weights do not match the mask support length")
    if not np.all(np.isfinite(weights)):
        _raise(R_INVALID_WEIGHTS, "frequency weights contain nonfinite values")
    if np.any(weights < 0.0):
        _raise(R_INVALID_WEIGHTS, "frequency weights contain negative values")
    for name, mask in masks.items():
        total = float(np.sum(weights[mask]))
        if not math.isfinite(total):
            _raise(R_INVALID_WEIGHTS, f"{name} mask total weight is nonfinite")
        if total <= 0.0:
            _raise(R_ZERO_TOTAL_WEIGHT, f"{name} mask total weight is zero")


def _policy_hash(payload: dict) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ public policy


@dataclass(frozen=True)
class MetricPolicy:
    """Immutable frozen metric/scoring inputs for one resolved v4 brief.

    ``masks``/``frequency_weights`` are present only when a frequency support was supplied.
    A predeclared shared restriction produces ``status="partial"`` and a distinct
    ``metric_spec_hash`` (a different metric identity, never pooled with the full support).
    """

    brief_hash: str
    brief_name: str
    objective_version: int
    weights: dict
    tolerances: dict
    cov_narrow_ratio: float | None
    cov_below_f0: str | None
    diag_reference: str | None
    freq_weights_signature: tuple
    metric_spec_hash: str
    ripple: str = RIPPLE_RESPONSE_DETRENDED
    reasons: tuple[str, ...] = ()
    status: str = "complete"
    restriction_name: str | None = None
    frequency_hz: tuple[float, ...] | None = None
    masks: dict | None = None
    frequency_weights: tuple[float, ...] | None = None

    @property
    def partial(self) -> bool:
        return self.status != "complete"

    @property
    def physical_metric_spec_hash(self) -> str:
        """Alias used by the hardening/spec text for the deterministic masks/weights hash."""
        return self.metric_spec_hash

    @property
    def masks_weights_hash(self) -> str:
        return self.metric_spec_hash

    def as_dict(self) -> dict:
        return {
            "brief_hash": self.brief_hash,
            "brief_name": self.brief_name,
            "objective_version": self.objective_version,
            "weights": dict(self.weights),
            "tolerances": dict(self.tolerances),
            "cov_narrow_ratio": self.cov_narrow_ratio,
            "cov_below_f0": self.cov_below_f0,
            "diag_reference": self.diag_reference,
            "freq_weights_signature": [list(row) for row in self.freq_weights_signature],
            "metric_spec_hash": self.metric_spec_hash,
            "ripple": self.ripple,
            "reasons": list(self.reasons),
            "status": self.status,
            "restriction_name": self.restriction_name,
            "frequency_hz": None if self.frequency_hz is None else list(self.frequency_hz),
            "masks": None if self.masks is None else {
                k: [bool(v) for v in self.masks[k]] for k in sorted(self.masks)},
            "frequency_weights": (None if self.frequency_weights is None
                                  else list(self.frequency_weights)),
        }


def resolve_metric_policy(brief, freqs_hz=None, *, declared_masks: dict | None = None,
                          declared_weights=None, restricted_mask=None,
                          restriction_name: str | None = None) -> MetricPolicy:
    """Freeze the v4 raw-metric policy from a resolved brief.

    ``brief`` may be a :class:`~hornlab_search.objective.replay.Brief` or a brief path (loaded
    through the canonical ``load_brief_context``).  ``freqs_hz`` enables the per-plane support
    masks; without it only the brief-level policy identity is frozen.  ``declared_masks`` /
    ``declared_weights`` let a caller supply an intended shared support explicitly; malformed or
    unsupported declarations raise a reason-coded ``ValueError``.
    """
    brief = _coerce_brief(brief)
    version = int(brief.objective_version)
    if version != 4:
        _raise(R_UNSUPPORTED_OBJECTIVE, f"got objective version {version}, expected 4")
    if brief.target is None:
        _raise(R_MISSING_TARGET, "the resolved brief has no target")
    block = brief.objective_block
    if not isinstance(block, dict):
        _raise(R_MISSING_OBJECTIVE_BLOCK, "objective v4 needs its validated objective block")
    params = V4Params.from_block(dict(block))
    if float(params.cov_narrow_ratio) != REQUIRED_COV_NARROW_RATIO:
        _raise(R_COV_NARROW_RATIO,
               f"got {params.cov_narrow_ratio!r}; the frozen ATH task requires "
               f"{REQUIRED_COV_NARROW_RATIO!r}")
    if params.cov_below_f0 != "mask":
        _raise(R_COV_BELOW_F0, f"got {params.cov_below_f0!r}, expected 'mask'")
    if params.diag_reference != "round":
        _raise(R_DIAG_REFERENCE, f"got {params.diag_reference!r}, expected 'round'")

    weights = _canonical_weights(brief.weights)
    tolerances = {k: float(v) for k, v in sorted(params.tolerances.items())}
    signature = _freq_weights_signature(brief.target)
    brief_hash = brief.brief_hash()
    reasons: list[str] = [
        "resolved_from_brief",
        "objective_version=4",
        f"cov_narrow_ratio={params.cov_narrow_ratio:g}",
        f"cov_below_f0={params.cov_below_f0}",
        f"diag_reference={params.diag_reference}",
        f"ripple={RIPPLE_RESPONSE_DETRENDED}",
    ]
    if float(weights.get("load", 0.0)) == 0.0:
        reasons.append("load_weight_zero_no_impedance_claim")

    f: np.ndarray | None = None
    masks: dict[str, np.ndarray] | None = None
    freq_weights: np.ndarray | None = None
    status = "complete"

    if declared_masks is None and declared_weights is None and restricted_mask is None:
        if freqs_hz is not None:
            f = _as_frequencies(freqs_hz)
            masks = _expected_masks(f, brief.target)
            freq_weights = scalar_v2.freq_weight_vector(f, brief.target)
            _check_weight_totals(np.asarray(freq_weights, dtype=float), masks)
    else:
        if freqs_hz is None:
            _raise(R_INVALID_FREQS, "declared masks/weights/restrictions require freqs_hz")
        f = _as_frequencies(freqs_hz)
        expected = _expected_masks(f, brief.target)

        if restricted_mask is not None:
            restriction = np.asarray(restricted_mask)
            if restriction.dtype != np.bool_ or restriction.shape != f.shape:
                _raise(R_INVALID_RESTRICTION,
                       "restricted_mask must be a boolean array matching the frequency support")
            if not restriction_name or not str(restriction_name).strip():
                _raise(R_INVALID_RESTRICTION, "a shared restriction requires a nonempty name")
            if not restriction.any() or restriction.all():
                _raise(R_INVALID_RESTRICTION,
                       "a shared restriction must be a proper, non-empty subset")
            expected = {name: mask & restriction for name, mask in expected.items()}
            for name, mask in expected.items():
                if not mask.any():
                    _raise(R_NO_SCORED_MASK,
                           f"the shared restriction empties the {name} mask")
            status = "partial"
            reasons.extend([f"predeclared_restricted_mask:{restriction_name}",
                            "partial_shared_restriction"])

        if declared_masks is not None:
            if not isinstance(declared_masks, dict):
                _raise(R_MASK_MISMATCH, "declared_masks must be a mapping of plane -> mask")
            missing = [k for k in ("ripple", "coverage_h", "coverage_v")
                       if k not in declared_masks]
            if missing:
                _raise(R_NO_SCORED_MASK,
                       f"declared_masks is missing required mask(s): {missing}")
            declared = {name: _as_mask(name, declared_masks[name], f.shape)
                        for name in ("ripple", "coverage_h", "coverage_v")}
            if not all(np.array_equal(declared[k], expected[k]) for k in expected):
                for name in expected:
                    if np.any(expected[name] & ~declared[name]):
                        _raise(R_MISSING_BINS,
                               f"declared {name!r} mask drops bins the target requires")
                for name in expected:
                    if np.any(declared[name] & ~expected[name]):
                        _raise(R_EXTRA_BINS,
                               f"declared {name!r} mask adds bins outside the target support")
                _raise(R_MASK_MISMATCH, "declared masks are not the frozen target support")
            masks = declared
        else:
            masks = expected

        if declared_weights is not None:
            w = np.asarray(declared_weights, dtype=float)
            if w.shape != f.shape:
                _raise(R_UNEQUAL_SUPPORT,
                       f"declared weights have shape {w.shape}, expected {f.shape}")
            freq_weights = w
        else:
            freq_weights = np.asarray(scalar_v2.freq_weight_vector(f, brief.target), dtype=float)
        _check_weight_totals(np.asarray(freq_weights, dtype=float), masks)

    payload = {
        "schema": METRIC_SCHEMA,
        "kind": "metric_policy",
        "brief_hash": brief_hash,
        "brief_name": str(brief.name),
        "objective_version": 4,
        "weights": weights,
        "tolerances": tolerances,
        "cov_narrow_ratio": float(params.cov_narrow_ratio),
        "cov_below_f0": str(params.cov_below_f0),
        "diag_reference": str(params.diag_reference),
        "freq_weights_signature": [list(row) for row in signature],
        "ripple": RIPPLE_RESPONSE_DETRENDED,
        "status": status,
        "frequency_hz": None if f is None else [float(x) for x in f],
        "masks": None if masks is None else {
            k: [bool(v) for v in masks[k]] for k in sorted(masks)},
        "frequency_weights": (None if freq_weights is None
                              else [float(x) for x in np.asarray(freq_weights, dtype=float)]),
    }
    return MetricPolicy(
        brief_hash=brief_hash, brief_name=str(brief.name), objective_version=4,
        weights=weights, tolerances=tolerances,
        cov_narrow_ratio=float(params.cov_narrow_ratio),
        cov_below_f0=str(params.cov_below_f0), diag_reference=str(params.diag_reference),
        freq_weights_signature=signature, metric_spec_hash=_policy_hash(payload),
        ripple=RIPPLE_RESPONSE_DETRENDED, reasons=tuple(reasons), status=status,
        restriction_name=restriction_name,
        frequency_hz=None if f is None else tuple(float(x) for x in f),
        masks=None if masks is None else {
            k: tuple(bool(v) for v in masks[k]) for k in sorted(masks)},
        frequency_weights=(None if freq_weights is None
                           else tuple(float(x) for x in np.asarray(freq_weights, dtype=float))),
    )


def assert_ripple_response_detrended(ripple_used_response: bool,
                                     scored_support_mask) -> bool:
    """Require the response-detrended ripple branch on a non-empty scored support.

    Returns ``True`` when the observation is admissible.  A legacy fallback or an empty/missing
    support raises a reason-coded ``ValueError``; the caller must then either exclude the
    observation or label it with :func:`make_legacy_ripple_policy` (a distinct identity).
    """
    if not isinstance(ripple_used_response, (bool, np.bool_)) or not bool(ripple_used_response):
        _raise(R_RIPPLE_LEGACY_FALLBACK,
               "the canonical scorer fell back to stored legacy ripple (ripple_used_response "
               "is not True); this is a distinct partial metric, not the response-detrended one")
    if scored_support_mask is None:
        _raise(R_NO_SCORED_SUPPORT, "scored_support_mask is missing")
    mask = np.asarray(scored_support_mask)
    if mask.ndim != 1 or mask.dtype != np.bool_:
        _raise(R_NO_SCORED_SUPPORT, "scored_support_mask must be a 1-D boolean array")
    if not mask.any():
        _raise(R_NO_SCORED_SUPPORT, "the scored support mask has no True bins")
    return True


def make_legacy_ripple_policy(brief=None, *, freqs_hz=None,
                              restriction_name: str | None = None) -> MetricPolicy:
    """A distinctly named metric identity for the stored-legacy ripple fallback.

    This policy is never interchangeable with a response-detrended policy: its ``ripple`` label
    and ``metric_spec_hash`` differ even for the same brief/target, and it always has
    ``status="partial"``.
    """
    base = None
    if brief is not None:
        base = _coerce_brief(brief)
    params = None
    tolerances: dict = {}
    weights: dict = {}
    signature: tuple = ()
    brief_hash = ""
    brief_name = "<legacy_ripple>"
    if base is not None:
        brief_hash = base.brief_hash()
        brief_name = str(base.name)
        weights = _canonical_weights(base.weights)
        signature = _freq_weights_signature(base.target) if base.target is not None else ()
        if isinstance(base.objective_block, dict):
            try:
                params = V4Params.from_block(dict(base.objective_block))
            except ValueError:
                params = None
            if params is not None:
                tolerances = {k: float(v) for k, v in sorted(params.tolerances.items())}
    masks = None
    freq_weights = None
    frequency_hz = None
    if freqs_hz is not None:
        f = _as_frequencies(freqs_hz)
        frequency_hz = tuple(float(x) for x in f)
        if base is not None and base.target is not None:
            masks = _expected_masks(f, base.target)
            freq_weights = tuple(float(x) for x in np.asarray(
                scalar_v2.freq_weight_vector(f, base.target), dtype=float))
    payload = {
        "schema": METRIC_SCHEMA,
        "kind": "metric_policy",
        "brief_hash": brief_hash,
        "brief_name": brief_name,
        "objective_version": 4,
        "weights": weights,
        "tolerances": tolerances,
        "cov_narrow_ratio": None if params is None else float(params.cov_narrow_ratio),
        "cov_below_f0": None if params is None else str(params.cov_below_f0),
        "diag_reference": None if params is None else str(params.diag_reference),
        "freq_weights_signature": [list(row) for row in signature],
        "ripple": RIPPLE_LEGACY,
        "status": "partial",
        "frequency_hz": None if frequency_hz is None else list(frequency_hz),
        "masks": None if masks is None else {
            k: [bool(v) for v in masks[k]] for k in sorted(masks)},
        "frequency_weights": None if freq_weights is None else list(freq_weights),
    }
    return MetricPolicy(
        brief_hash=brief_hash, brief_name=brief_name, objective_version=4,
        weights=weights, tolerances=tolerances,
        cov_narrow_ratio=None if params is None else float(params.cov_narrow_ratio),
        cov_below_f0=None if params is None else str(params.cov_below_f0),
        diag_reference=None if params is None else str(params.diag_reference),
        freq_weights_signature=signature, metric_spec_hash=_policy_hash(payload),
        ripple=RIPPLE_LEGACY, reasons=(
            "legacy_ripple_fallback", "distinct_metric_spec",
            "never_pooled_with_response_detrended"),
        status="partial", restriction_name=restriction_name,
        frequency_hz=frequency_hz, masks=masks, frequency_weights=freq_weights,
    )


# ------------------------------------------------------------------ provisional B3 adapter
# These helpers predate the policy seam above.  They only freeze one frequency support and
# delegate all measurement math to the canonical helpers, so they remain valid for the B3
# diagnostics test.  New code should use ``resolve_metric_policy`` above.


@dataclass(frozen=True)
class FrozenSupport:
    """Serialized immutable common support, to reuse unchanged for every design."""

    payload_json: str
    physical_metric_spec_hash: str

    @property
    def payload(self) -> dict:
        return json.loads(self.payload_json)


@dataclass(frozen=True)
class MetricObservation:
    status: str
    reason: str | None
    physical_metric_spec_hash: str | None
    coverage_deg: float | None = None
    ripple_db: float | None = None


def freeze_metric_policy(brief: Brief, freqs_hz, *, restricted_mask=None,
                         restriction_name: str | None = None) -> FrozenSupport:
    """Freeze a brief and frequency support; a shared restriction is explicitly partial."""
    if not isinstance(brief, Brief) or brief.objective_version != 4:
        raise ValueError("a resolved v4 replay Brief is required")
    block = brief.objective_block
    if not isinstance(block, dict):
        raise ValueError("objective v4 needs its validated objective block")
    params = V4Params.from_block(block)
    if params.cov_below_f0 != "mask" or params.diag_reference != "round":
        raise ValueError("unsupported coverage or diagonal convention")
    t = Target.from_dict(asdict(brief.target))
    f = np.asarray(freqs_hz, dtype=float)
    if (f.ndim != 1 or f.size == 0 or not np.all(np.isfinite(f)) or np.any(f <= 0)
            or np.any(np.diff(f) <= 0)):
        raise ValueError("frequencies must be finite, positive and strictly increasing")
    intended = (f >= t.band_lo_hz) & (f <= t.band_hi_hz)
    if restricted_mask is None:
        if restriction_name is not None:
            raise ValueError("restriction name requires a mask")
        restriction = np.ones(f.size, dtype=bool)
    else:
        restriction = np.asarray(restricted_mask)
        if (restriction.dtype != np.bool_ or restriction.shape != f.shape
                or not restriction_name or not restriction_name.strip()):
            raise ValueError("a shared restricted mask requires a nonempty name and matching "
                             "boolean array")
    band = intended & restriction
    h = band & (f >= t.f0_effective_hz())
    v = band & (f >= (t.f0_v_hz if t.f0_v_hz is not None else t.f0_effective_hz()))
    w = scalar_v2.freq_weight_vector(f, t)
    if not np.all(np.isfinite(w)) or np.any(w < 0):
        raise ValueError("frequency weights must be finite and nonnegative")
    for mask in (band, h, v):
        if not mask.any() or not np.isfinite(w[mask].sum()) or w[mask].sum() <= 0:
            raise ValueError("each intended mask requires positive total weight")
    # Zero-weight bins are explicit exclusions; source target validation currently requires
    # positive weights.
    code = {m.__name__: hashlib.sha256(Path(str(m.__file__)).read_bytes()).hexdigest()
            for m in (scalar_v2, scalar_v8, smoothness)}
    payload = {"schema": METRIC_SCHEMA, "objective_version": 4,
               "target": asdict(t), "v4_params": params.to_block(),
               "brief_hash": brief.brief_hash(), "objective_weights": brief.weights,
               "frequency_hz": f.tolist(),
               "masks": {"ripple": band.tolist(), "coverage_h": h.tolist(),
                         "coverage_v": v.tolist()},
               "weights": w.tolist(), "restriction_name": restriction_name,
               "status": "partial" if restricted_mask is not None else "complete",
               "units": {"coverage": "deg", "ripple": "dB"},
               "ripple_definition": "response_detrended_h_plus_v", "code_sha256": code}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return FrozenSupport(encoded, hashlib.sha256(encoded.encode()).hexdigest())


def measure_metrics(policy: FrozenSupport, metrics, response) -> MetricObservation:
    """Return strictly comparable raw observations or an explicit capability refusal."""
    def missing(reason):
        return MetricObservation("capability_missing", reason, policy.physical_metric_spec_hash)

    try:
        if (hashlib.sha256(policy.payload_json.encode()).hexdigest()
                != policy.physical_metric_spec_hash):
            return missing("metric policy hash mismatch")
        p = policy.payload
        f = np.asarray(metrics.freqs_hz, dtype=float)
        if not np.array_equal(f, np.asarray(p["frequency_hz"], dtype=float)):
            return missing("frequency support differs from frozen policy")
        band = np.asarray(p["masks"]["ripple"], dtype=bool)
        h = np.asarray(p["masks"]["coverage_h"], dtype=bool)
        v = np.asarray(p["masks"]["coverage_v"], dtype=bool)
        for name, mask in (("bw_h_deg", h), ("bw_v_deg", v)):
            a = np.asarray(getattr(metrics, name), dtype=float)
            if a.shape != f.shape or not np.all(np.isfinite(a[mask])):
                return missing(f"{name} missing intended bins")
        target = Target.from_dict(p["target"])
        values, used = scalar_v2._v2_ripple_values(metrics, response, target, band)
        if not used or values.shape != f.shape or not np.all(np.isfinite(values[band])):
            return missing("response-detrended ripple unavailable on intended bins")
        # A separate helper diagnostic detects legacy fallback before v8_raw_terms recomputes it.
        v4 = V4Params.from_block(p["v4_params"])
        helper_params = scalar_v8.V8Params(tolerances={}, cov_narrow_ratio=v4.cov_narrow_ratio,
                                           cov_below_f0=v4.cov_below_f0,
                                           diag_reference=v4.diag_reference, gates=())
        raw = scalar_v8.v8_raw_terms(metrics, response, target, band, h, helper_params)["raw"]
        cov, rip = float(raw["cov"]), float(raw["rip"])
        if (not np.isfinite(cov) or not np.isfinite(rip) or cov == NAN_TERM_FILL
                or rip == NAN_TERM_FILL):
            return missing("raw helper returned invalid or sentinel value")
        return MetricObservation(p["status"], None, policy.physical_metric_spec_hash, cov, rip)
    except (AttributeError, TypeError, ValueError, IndexError, KeyError, ArithmeticError) as exc:
        return missing(f"required metric input unavailable: {exc}")


__all__ = [
    "RIPPLE_RESPONSE_DETRENDED",
    "RIPPLE_LEGACY",
    "METRIC_SCHEMA",
    "REQUIRED_COV_NARROW_RATIO",
    "REASONS",
    "MetricPolicy",
    "resolve_metric_policy",
    "assert_ripple_response_detrended",
    "make_legacy_ripple_policy",
    "FrozenSupport",
    "MetricObservation",
    "freeze_metric_policy",
    "measure_metrics",
]
