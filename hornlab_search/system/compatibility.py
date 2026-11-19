"""Tier-0 compatibility questions for saved horn assets (``hornlab_search.system``).

This module answers **only** Tier-0, read-only questions about a
:class:`hornlab_search.system.contracts.HornAsset`:

* does the asset actually carry complex H/V polar fields?
* does it carry a complex balloon field?
* does its frequency grid cover a requested ``(f_lo, f_hi)``?
* is its provenance stale or unknown?
* which stored family / brief does it belong to?

Nothing here optimises, searches, designs a crossover, combines phases, or reports a fidelity
comparison. Any attempt to ask a Tier-1+ question raises :class:`TierTooHigh` immediately; it is
never silently downgraded. Every answer is a frozen dataclass row so callers can log/report it
without re-deriving anything.

Stage-5 addition (review 2026-11-18 §3.2): the **report-only directional fingerprint screen** below
measures a normalized level-shape mismatch between the stored horn pattern and a labelled rigid
baffled-piston model over candidate-crossover overlap bands. It is explicitly *not* a Tier-0 claim
and *not* an optimiser: it never selects a winner, never imputes phase, and never extrapolates a
missing frequency or angle. All original Tier-0 behaviour and refusal tokens are unchanged.

Phase honesty is explicit: ``has_complex_hv``/``has_complex_balloon`` report *array presence*,
while :attr:`ProvenanceFlags.basis_verified` reports whether the asset's
:class:`~hornlab_search.system.contracts.SourceBasis` is proven (``quality == "EXACT_COMPLEX"``).
A magnitude-only asset therefore answers "complex arrays present" honestly but is still refused by
``require_phase_usable`` queries and by ``HornAsset.require_complex()``.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from hornlab_search.solve import cache as solve_cache
from hornlab_search.system import piston
from hornlab_search.system.contracts import DataQualityError, HornAsset, PhaseUnavailable

__all__ = [
    "TierTooHigh",
    "TIER0_CLAIMS",
    "FreqCoverage",
    "ProvenanceFlags",
    "FamilyBrief",
    "Tier0Query",
    "Tier0Row",
    "assert_tier0",
    "has_complex_hv",
    "has_complex_balloon",
    "covers_band",
    "provenance_flags",
    "family_brief",
    "evaluate_tier0",
    # Report-only directional fingerprint screen (stage 5; no optimisation/scalar objective).
    "HornFingerprint",
    "BandSelection",
    "ShapeMismatch",
    "XoCandidate",
    "GoodMatchBand",
    "XoScreen",
    "make_fingerprint",
    "extract_horn_fingerprints",
    "select_overlap_band",
    "shape_mismatch",
    "screen_xo_bands",
    "require_phase_alignment",
    "REPORT_FLOOR_DB",
    "NULL_FLAG_DB",
    "DEFAULT_OVERLAP_HALF_OCTAVES",
    "DEFAULT_MIN_BAND_FREQS",
    "DEFAULT_MIN_BAND_DIRS",
    "DEFAULT_GOOD_MATCH_DB2",
]

#: The only question classes Tier 0 is allowed to answer.
TIER0_CLAIMS: frozenset[str] = frozenset({
    "complex_hv", "complex_balloon", "band_coverage", "provenance", "family_brief",
    "tier0_evaluation",
})

_COMPLEX_HV = frozenset({"p_h", "p_v"})


class TierTooHigh(ValueError):
    """A Tier-1+ (optimisation/crossover/combination) question was asked of the Tier-0 layer."""


def assert_tier0(claim: str) -> None:
    """Refuse any claim outside the Tier-0 question set."""
    if claim not in TIER0_CLAIMS:
        raise TierTooHigh(
            f"claim {claim!r} is outside Tier 0; compatibility.py answers only "
            f"{sorted(TIER0_CLAIMS)} (no optimisation, crossover or phase combination)")


# --------------------------------------------------------------------------- rows


@dataclass(frozen=True)
class FreqCoverage:
    """Whether the asset's stored frequency grid spans the requested band."""

    f_lo_hz: float
    f_hi_hz: float
    asset_lo_hz: float | None
    asset_hi_hz: float | None
    covered: bool


@dataclass(frozen=True)
class ProvenanceFlags:
    """Stored provenance state, including the phase-usability fact."""

    quality: str
    stale: bool
    unknown: bool
    basis_verified: bool
    complex_present: bool
    provenance: str | None
    notes: tuple[str, ...]


@dataclass(frozen=True)
class FamilyBrief:
    """Family / brief classification taken from stored metadata (never inferred from names)."""

    family: str | None
    brief_id: str | None
    objective_version: str | None


@dataclass(frozen=True)
class Tier0Query:
    """A Tier-0 question. All flags are conjunctive requirements."""

    f_lo_hz: float
    f_hi_hz: float
    require_complex_hv: bool = False
    require_complex_balloon: bool = False
    require_fresh: bool = False
    require_phase_usable: bool = False
    family: str | None = None
    brief_id: str | None = None

    def __post_init__(self) -> None:
        for name, value in (("f_lo_hz", self.f_lo_hz), ("f_hi_hz", self.f_hi_hz)):
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite, got {value!r}")
        if float(self.f_lo_hz) > float(self.f_hi_hz):
            raise ValueError(
                f"f_lo_hz must be <= f_hi_hz, got [{self.f_lo_hz!r}, {self.f_hi_hz!r}]")


@dataclass(frozen=True)
class Tier0Row:
    """One structured Tier-0 answer for one asset."""

    asset_id: str
    quality: str
    has_complex_hv: bool
    has_complex_balloon: bool
    coverage: FreqCoverage
    provenance: ProvenanceFlags
    family: FamilyBrief
    accepted: bool
    reasons: tuple[str, ...]


# --------------------------------------------------------------------------- Tier-0 questions


def has_complex_hv(asset: HornAsset) -> bool:
    """Whether both complex H and V polar arrays are actually present."""
    assert_tier0("complex_hv")
    return _COMPLEX_HV <= set(asset.available_fields)


def has_complex_balloon(asset: HornAsset) -> bool:
    """Whether a complex balloon array is actually present."""
    assert_tier0("complex_balloon")
    return "p_balloon" in asset.available_fields


def covers_band(asset: HornAsset, f_lo_hz: float, f_hi_hz: float) -> FreqCoverage:
    """Whether the stored frequency grid spans ``[f_lo_hz, f_hi_hz]`` (inclusive)."""
    assert_tier0("band_coverage")
    if not math.isfinite(float(f_lo_hz)) or not math.isfinite(float(f_hi_hz)):
        raise ValueError("band bounds must be finite")
    if float(f_lo_hz) > float(f_hi_hz):
        raise ValueError(f"f_lo_hz must be <= f_hi_hz, got [{f_lo_hz!r}, {f_hi_hz!r}]")
    if not asset.freqs_hz:
        return FreqCoverage(float(f_lo_hz), float(f_hi_hz), None, None, False)
    lo, hi = float(min(asset.freqs_hz)), float(max(asset.freqs_hz))
    return FreqCoverage(float(f_lo_hz), float(f_hi_hz), lo, hi,
                        lo <= float(f_lo_hz) and hi >= float(f_hi_hz))


def provenance_flags(asset: HornAsset) -> ProvenanceFlags:
    """Stale/unknown provenance flags plus the phase-usability fact."""
    assert_tier0("provenance")
    extra = asset.geometry.extra
    provenance = extra.get("provenance") if isinstance(extra, Mapping) else None
    data_quality = extra.get("data_quality") if isinstance(extra, Mapping) else None
    notes: tuple[str, ...] = (str(data_quality),) if data_quality else ()
    stale = asset.quality == "STALE_SOURCE"
    unknown = (asset.quality in ("GEOMETRY_ONLY", "INCOMPATIBLE")
               or provenance in (None, "status_missing", "geometry_only"))
    return ProvenanceFlags(
        quality=asset.quality,
        stale=stale,
        unknown=unknown,
        basis_verified=asset.quality == "EXACT_COMPLEX" and asset.source_basis is not None,
        complex_present=bool(set(asset.available_fields) & {"p_h", "p_v", "p_balloon"}),
        provenance=provenance if isinstance(provenance, str) else None,
        notes=notes,
    )


def family_brief(asset: HornAsset) -> FamilyBrief:
    """Family / brief / objective version taken from stored metadata only."""
    assert_tier0("family_brief")
    geometry = asset.geometry
    return FamilyBrief(
        family=geometry.family,
        brief_id=geometry.brief_id,
        objective_version=geometry.objective_version,
    )


def evaluate_tier0(asset: HornAsset, query: Tier0Query) -> Tier0Row:
    """Answer one Tier-0 query as a structured row. Never lowers a requirement."""
    assert_tier0("tier0_evaluation")
    coverage = covers_band(asset, query.f_lo_hz, query.f_hi_hz)
    provenance = provenance_flags(asset)
    family = family_brief(asset)
    hv = has_complex_hv(asset)
    balloon = has_complex_balloon(asset)

    reasons: list[str] = []
    if query.require_complex_hv and not hv:
        reasons.append("complex H/V polar arrays absent")
    if query.require_complex_balloon and not balloon:
        reasons.append("complex balloon array absent")
    if not coverage.covered:
        reasons.append(
            f"frequency grid [{coverage.asset_lo_hz}, {coverage.asset_hi_hz}] does not cover "
            f"[{coverage.f_lo_hz}, {coverage.f_hi_hz}]")
    if query.require_fresh and (provenance.stale or provenance.unknown):
        reasons.append(
            "provenance is not fresh"
            f" (quality={provenance.quality!r}, provenance={provenance.provenance!r})")
    if query.require_phase_usable and not provenance.basis_verified:
        reasons.append("phase claims refused: asset is not EXACT_COMPLEX with a proven SourceBasis")
    if query.family is not None and family.family != query.family:
        reasons.append(f"family {family.family!r} != requested {query.family!r}")
    if query.brief_id is not None and family.brief_id != query.brief_id:
        reasons.append(f"brief_id {family.brief_id!r} != requested {query.brief_id!r}")

    return Tier0Row(
        asset_id=asset.asset_id,
        quality=asset.quality,
        has_complex_hv=hv,
        has_complex_balloon=balloon,
        coverage=coverage,
        provenance=provenance,
        family=family,
        accepted=not reasons,
        reasons=tuple(reasons),
    )


# =============================================================================================
# Stage-5 report-only directional fingerprint screen (review 2026-11-18 §3.2)
#
# Definitions (implemented literally below):
#   L_h,rel(f, dir) = SPL_h(f, dir) - SPL_h(f, on_axis)
#   L_w,rel(f, dir) = 20 log10 |2 J1(k a sin(theta)) / (k a sin(theta))|   (piston; 0 dB on axis)
#   E_shape(f_x, plane) = sum_f w_f [ sum_dir w_dir (L_h,rel - L_w,rel)^2 / sum_dir w_dir ]
#                         / sum_f w_f
# Frequency support is the intersection of the candidate-crossover octave band
# [f_x / 2**h, f_x * 2**h] with the asset's *stored* frequency samples.  Nothing is interpolated.
# H and V planes are separate evaluations.  The listening front region is the only direction set.
# =============================================================================================

#: Finite reporting floor for relative levels [dB].  Deep nulls are clamped, never hidden: the
#: separate ``null_mask``/``null_fraction`` report is what a caller must honour.
REPORT_FLOOR_DB: float = float(piston.REPORT_FLOOR_DB)
#: A relative level at/below this value is a deep null for reporting purposes.
NULL_FLAG_DB: float = float(piston.NULL_FLAG_DB)
#: Candidate-specific overlap band width (half-octaves around f_x).  The stored 12-point asset
#: grid is a third-octave grid, so a one-third-octave half-width selects the centre sample plus
#: its nearest neighbours (three stored samples).  It is NOT a fixed universal 700-1300 Hz window.
DEFAULT_OVERLAP_HALF_OCTAVES: float = 1.0 / 3.0
DEFAULT_MIN_BAND_FREQS: int = 3
DEFAULT_MIN_BAND_DIRS: int = 3
#: Provisional good-match threshold in mean-squared dB (3 dB RMS).  A reporting label, not a gate.
DEFAULT_GOOD_MATCH_DB2: float = 9.0
_ON_AXIS_TOL_DEG: float = 1e-9
_BALLOON_PLANE_TOL_DEG: float = 5.0


def _jsonable(value: Any) -> Any:
    """Recursively convert numpy values to JSON-safe values; non-finite floats become None."""
    if isinstance(value, np.ndarray):
        return [_jsonable(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int)):
        return value
    return str(value)


@dataclass(frozen=True)
class HornFingerprint:
    """One plane's stored horn relative pattern (level-only; no phase claim)."""

    plane: str
    freqs_hz: np.ndarray
    angles_deg: np.ndarray
    levels_db: np.ndarray                 # relative to the on-axis sample, clamped to floor
    null_mask: np.ndarray                 # raw relative level <= NULL_FLAG_DB
    on_axis_index: int | None
    on_axis_angle_deg: float | None
    source: str
    data_quality: str
    asset_id: str = ""
    accepted: bool = True
    reasons: tuple[str, ...] = ()

    @property
    def n_freqs(self) -> int:
        return int(self.levels_db.shape[0]) if self.levels_db.ndim == 2 else 0

    @property
    def n_dirs(self) -> int:
        return int(self.levels_db.shape[1]) if self.levels_db.ndim == 2 else 0

    def summary(self) -> dict[str, Any]:
        return {
            "plane": self.plane,
            "n_freqs": self.n_freqs,
            "n_dirs": self.n_dirs,
            "freq_lo_hz": None if self.freqs_hz.size == 0 else float(self.freqs_hz[0]),
            "freq_hi_hz": None if self.freqs_hz.size == 0 else float(self.freqs_hz[-1]),
            "angle_min_deg": None if self.angles_deg.size == 0 else float(self.angles_deg.min()),
            "angle_max_deg": None if self.angles_deg.size == 0 else float(self.angles_deg.max()),
            "on_axis_index": self.on_axis_index,
            "source": self.source,
            "data_quality": self.data_quality,
            "null_fraction": (float(np.mean(self.null_mask)) if self.null_mask.size else None),
            "accepted": self.accepted,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class BandSelection:
    """Stored frequencies selected by one candidate crossover band (no interpolation)."""

    f_x_hz: float
    f_lo_hz: float
    f_hi_hz: float
    half_octaves: float
    freqs_hz: tuple[float, ...]
    freq_indices: tuple[int, ...]
    min_freqs: int
    accepted: bool
    reasons: tuple[str, ...] = ()

    @property
    def n_freqs(self) -> int:
        return len(self.freqs_hz)


@dataclass(frozen=True)
class ShapeMismatch:
    """One E_shape evaluation for one (f_x, plane)."""

    f_x_hz: float
    plane: str
    band: BandSelection
    e_shape_db2: float | None
    e_shape_rms_db: float | None
    n_freqs: int
    n_dirs: int
    weights: Mapping[str, Any]
    null_fraction: float | None
    uncertainty_db2: float | None
    good_match: bool
    data_quality: str
    accepted: bool
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _jsonable({
            "f_x_hz": self.f_x_hz,
            "plane": self.plane,
            "band_hz": [self.band.f_lo_hz, self.band.f_hi_hz],
            "band_freqs_hz": list(self.band.freqs_hz),
            "e_shape_db2": self.e_shape_db2,
            "e_shape_rms_db": self.e_shape_rms_db,
            "n_freqs": self.n_freqs,
            "n_dirs": self.n_dirs,
            "weights": dict(self.weights),
            "null_fraction": self.null_fraction,
            "uncertainty_db2": self.uncertainty_db2,
            "good_match": self.good_match,
            "data_quality": self.data_quality,
            "accepted": self.accepted,
            "reasons": list(self.reasons),
        })


@dataclass(frozen=True)
class XoCandidate:
    """One candidate crossover evaluation (H and V kept separate)."""

    f_x_hz: float
    mismatches: Mapping[str, ShapeMismatch]
    e_max_db2: float | None
    accepted: bool
    good_match: bool
    reasons: tuple[str, ...] = ()

    @property
    def band_hz(self) -> tuple[float, float] | None:
        for mismatch in self.mismatches.values():
            if mismatch.band.accepted:
                return (mismatch.band.f_lo_hz, mismatch.band.f_hi_hz)
        return None

    def to_dict(self) -> dict[str, Any]:
        return _jsonable({
            "f_x_hz": self.f_x_hz,
            "band_hz": list(self.band_hz) if self.band_hz else None,
            "e_max_db2": self.e_max_db2,
            "accepted": self.accepted,
            "good_match": self.good_match,
            "reasons": list(self.reasons),
            "planes": {plane: m.to_dict() for plane, m in sorted(self.mismatches.items())},
        })


@dataclass(frozen=True)
class GoodMatchBand:
    """A contiguous run of good-match candidate crossovers (provisional)."""

    f_lo_hz: float
    f_hi_hz: float
    centers_hz: tuple[float, ...]
    provisional: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "f_lo_hz": self.f_lo_hz,
            "f_hi_hz": self.f_hi_hz,
            "centers_hz": list(self.centers_hz),
            "n_centers": len(self.centers_hz),
            "provisional": self.provisional,
        }


@dataclass(frozen=True)
class XoScreen:
    """All candidate crossovers + provisional good-match bands for one woofer."""

    candidates: tuple[XoCandidate, ...]
    good_bands: tuple[GoodMatchBand, ...]
    hypothesis_centers_hz: tuple[float, ...]
    fallback_used: bool
    threshold_db2: float
    half_octaves: float
    min_freqs: int
    min_dirs: int
    data_quality: str
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _jsonable({
            "threshold_db2": self.threshold_db2,
            "half_octaves": self.half_octaves,
            "min_freqs": self.min_freqs,
            "min_dirs": self.min_dirs,
            "good_bands": [b.to_dict() for b in self.good_bands],
            "hypothesis_centers_hz": list(self.hypothesis_centers_hz),
            "fallback_used": self.fallback_used,
            "data_quality": self.data_quality,
            "reasons": list(self.reasons),
            "candidates": [c.to_dict() for c in self.candidates],
        })


# --------------------------------------------------------------------------- fingerprint builders


def make_fingerprint(
    plane: str,
    freqs_hz: Any,
    angles_deg: Any,
    levels_db: Any,
    *,
    on_axis_angle_deg: float = 0.0,
    source: str = "synthetic",
    data_quality: str = "SCREEN_MAGNITUDE level-only",
    asset_id: str = "",
    floor_db: float = REPORT_FLOOR_DB,
    null_flag_db: float = NULL_FLAG_DB,
) -> HornFingerprint:
    """Build a validated relative fingerprint from absolute stored levels.

    ``levels_db`` is ``(n_freqs, n_dirs)`` absolute dB (or any common reference).  It is
    converted to a relative pattern versus the stored sample at ``on_axis_angle_deg``; if that
    sample is absent the fingerprint is **rejected** rather than interpolated.
    """
    plane_key = str(plane).upper()
    if plane_key not in ("H", "V"):
        raise ValueError(f"plane must be 'H' or 'V', got {plane!r}")
    f = np.asarray(freqs_hz, dtype=float).reshape(-1)
    a = np.asarray(angles_deg, dtype=float).reshape(-1)
    levels = np.asarray(levels_db, dtype=float)
    reasons: list[str] = []
    if f.size == 0 or np.any(~np.isfinite(f)) or np.any(f <= 0.0):
        reasons.append("frequency axis is empty/non-finite/non-positive")
    if a.size == 0 or np.any(~np.isfinite(a)):
        reasons.append("angle axis is empty/non-finite")
    if levels.ndim != 2 or levels.shape != (f.size, a.size):
        raise ValueError(
            f"levels_db shape {levels.shape} does not match (n_freqs, n_dirs)={(f.size, a.size)}")

    # Deterministic angle order; keep a parallel permutation for the level rows.
    order = np.argsort(a, kind="stable")
    a = a[order]
    levels = levels[:, order]

    on_idx: int | None = None
    if a.size:
        exact = np.nonzero(np.abs(a - float(on_axis_angle_deg)) <= _ON_AXIS_TOL_DEG)[0]
        if exact.size:
            on_idx = int(exact[0])
        else:
            reasons.append(
                f"no stored on-axis sample at {float(on_axis_angle_deg):g} deg "
                f"(nearest {float(a[int(np.argmin(np.abs(a - float(on_axis_angle_deg))))]):g} deg); "
                "refused instead of interpolating")

    if levels.size:
        bad = ~np.isfinite(levels)
        if np.any(bad):
            bad_f, bad_d = np.nonzero(bad)
            reasons.append(
                f"non-finite stored levels at {int(bad_f.size)} sample(s), "
                f"first (f_index={int(bad_f[0])}, dir_index={int(bad_d[0])})")

    if reasons or on_idx is None:
        return HornFingerprint(
            plane=plane_key, freqs_hz=f, angles_deg=a,
            levels_db=np.zeros((f.size, a.size), dtype=float),
            null_mask=np.zeros((f.size, a.size), dtype=bool),
            on_axis_index=None, on_axis_angle_deg=None, source=source,
            data_quality=data_quality, asset_id=asset_id, accepted=False,
            reasons=tuple(reasons))

    rel = levels - levels[:, [on_idx]]
    null = rel <= float(null_flag_db)
    clamped = np.maximum(np.where(np.isfinite(rel), rel, floor_db), float(floor_db))
    return HornFingerprint(
        plane=plane_key, freqs_hz=f, angles_deg=a, levels_db=clamped, null_mask=null,
        on_axis_index=on_idx, on_axis_angle_deg=float(a[on_idx]), source=source,
        data_quality=data_quality, asset_id=asset_id, accepted=True)


def _rejected_fingerprint(plane: str, source: str, reasons: Sequence[str],
                          data_quality: str, asset_id: str) -> HornFingerprint:
    empty = np.zeros((0, 0), dtype=float)
    return HornFingerprint(
        plane=plane, freqs_hz=np.zeros(0), angles_deg=np.zeros(0), levels_db=empty,
        null_mask=np.zeros((0, 0), dtype=bool), on_axis_index=None,
        on_axis_angle_deg=None, source=source, data_quality=data_quality,
        asset_id=asset_id, accepted=False, reasons=tuple(str(r) for r in reasons))


def _levels_from_response(resp: Any, plane: str) -> tuple[np.ndarray, np.ndarray, str] | None:
    """Return (angles, absolute dB, source-label) for one plane, or None when absent."""
    if plane == "H":
        angles = getattr(resp, "h_angles_deg", None)
        spl = getattr(resp, "spl_h_db", None)
        p = getattr(resp, "p_h", None)
        spl_name, p_name = "stored_spl_h_db", "stored_complex_p_h_magnitude"
    else:
        angles = getattr(resp, "v_angles_deg", None)
        spl = getattr(resp, "spl_v_db", None)
        p = getattr(resp, "p_v", None)
        spl_name, p_name = "stored_spl_v_db", "stored_complex_p_v_magnitude"

    if angles is None:
        return None
    angle_arr = np.asarray(angles, dtype=float).reshape(-1)
    if spl is not None:
        values = np.asarray(spl, dtype=float)
        if values.ndim == 2 and values.shape[1] == angle_arr.size:
            return angle_arr, values, spl_name
    if p is not None:
        values = np.asarray(p)
        if values.ndim == 2 and values.shape[1] == angle_arr.size:
            mag = np.abs(values)
            with np.errstate(divide="ignore"):
                db = 20.0 * np.log10(mag)
            return angle_arr, np.asarray(db, dtype=float), p_name
    return None


def _balloon_plane(resp: Any, plane: str, *, plane_tol_deg: float,
                   listening_max_deg: float) -> tuple[np.ndarray, np.ndarray, str] | None:
    dirs = getattr(resp, "balloon_dirs", None)
    if dirs is None:
        return None
    d = np.asarray(dirs, dtype=float)
    if d.ndim != 2 or d.shape[1] != 3:
        return None
    spl = getattr(resp, "spl_balloon_db", None)
    p = getattr(resp, "p_balloon", None)
    if spl is not None:
        levels = np.asarray(spl, dtype=float)
        source = "stored_spl_balloon_db"
    elif p is not None:
        with np.errstate(divide="ignore"):
            levels = 20.0 * np.log10(np.abs(np.asarray(p, dtype=complex)))
        source = "stored_complex_p_balloon_magnitude"
    else:
        return None
    if levels.ndim != 2 or levels.shape[1] != d.shape[0]:
        return None

    front = d[:, 2] > 0.0
    tol = math.sin(math.radians(float(plane_tol_deg)))
    if plane == "H":
        on_plane = front & (np.abs(d[:, 1]) <= tol)
        angle = np.degrees(np.arctan2(d[:, 0], d[:, 2]))
    else:
        on_plane = front & (np.abs(d[:, 0]) <= tol)
        angle = np.degrees(np.arctan2(d[:, 1], d[:, 2]))
    idx = np.nonzero(on_plane & (np.abs(angle) <= float(listening_max_deg)))[0]
    if idx.size == 0:
        return None

    # The balloon has many azimuth samples on the axis; collapse to unique angles first-wins.
    ang = angle[idx]
    order = np.argsort(ang, kind="stable")
    idx, ang = idx[order], ang[order]
    _, first = np.unique(np.round(ang, 9), return_index=True)
    first.sort()
    idx, ang = idx[first], ang[first]
    return ang, levels[:, idx], source


def extract_horn_fingerprints(
    asset: HornAsset,
    *,
    listening_h_deg: float = 30.0,
    listening_v_deg: float = 15.0,
    plane_tol_deg: float = _BALLOON_PLANE_TOL_DEG,
    prefer: str = "cuts",
) -> dict[str, HornFingerprint]:
    """Extract H and V relative fingerprints from the **stored** asset arrays.

    ``prefer="cuts"`` uses the stored H/V cut plausibility first and falls back to the balloon;
    ``prefer="balloon"`` reverses that order.  Missing axes, missing on-axis samples and
    non-finite levels are explicit rejections, never interpolated.  Only the listening front
    region is retained (no back-hemisphere comparison).
    """
    if prefer not in ("cuts", "balloon"):
        raise ValueError(f"prefer must be 'cuts' or 'balloon', got {prefer!r}")
    if not asset.response_path:
        raise DataQualityError(f"asset {asset.asset_id!r} has no response_path")
    resp = solve_cache.load_response(Path(asset.response_path))
    quality = "SCREEN_MAGNITUDE level-only (stored magnitudes; no phase/delay claim)"
    out: dict[str, HornFingerprint] = {}
    for plane, limit in (("H", listening_h_deg), ("V", listening_v_deg)):
        attempts: list[tuple[str, str, tuple[str, ...]]] = []
        extracted: tuple[np.ndarray, np.ndarray, str] | None = None
        if prefer == "cuts":
            cuts = _levels_from_response(resp, plane)
            if cuts is not None:
                angles, levels, source = cuts
                mask = (np.abs(angles) <= float(limit)) & (np.abs(angles) <= 90.0)
                if np.count_nonzero(mask) >= 1:
                    extracted = (angles[mask], levels[:, mask], source)
                else:
                    attempts.append((plane, "cuts", ("no cut angles inside the listening region",)))
            else:
                attempts.append((plane, "cuts", ("stored H/V cut arrays absent",)))
        if extracted is None:
            balloon = _balloon_plane(resp, plane, plane_tol_deg=plane_tol_deg,
                                     listening_max_deg=float(limit))
            if balloon is not None:
                extracted = balloon
            else:
                attempts.append((plane, "balloon",
                                 ("no front-hemisphere balloon samples on this plane inside "
                                  "the listening region",)))
        if extracted is None:
            out[plane] = _rejected_fingerprint(
                plane, "none", [f"{src}: {reason}" for _p, src, rs in attempts for reason in rs],
                quality, asset.asset_id)
            continue
        angles, levels, source = extracted
        fp = make_fingerprint(
            plane, resp.freqs_hz, angles, levels, source=source,
            data_quality=f"{quality}; stored fields={sorted(asset.available_fields)}",
            asset_id=asset.asset_id)
        if not fp.accepted and prefer == "cuts":
            balloon2 = _balloon_plane(resp, plane, plane_tol_deg=plane_tol_deg,
                                      listening_max_deg=float(limit))
            if balloon2 is not None:
                angles2, levels2, source2 = balloon2
                fp2 = make_fingerprint(
                    plane, resp.freqs_hz, angles2, levels2, source=source2,
                    data_quality=f"{quality}; fallback from cuts ({list(fp.reasons)})",
                    asset_id=asset.asset_id)
                if fp2.accepted:
                    out[plane] = fp2
                    continue
        out[plane] = fp
    return out


def require_phase_alignment(asset: HornAsset) -> Any:
    """Phase/delay gate for the screen: raises :class:`PhaseUnavailable` for magnitude-only.

    Reuses :meth:`contracts.HornAsset.require_complex` unchanged, so the refusal tokens remain
    ``MAGNITUDE_ONLY / PHASE_ALIGNMENT_UNAVAILABLE``.  A level-shape screen may still run.
    """
    return asset.require_complex()


# --------------------------------------------------------------------------- overlap + E_shape


def select_overlap_band(
    freqs_hz: Any,
    f_x_hz: float,
    *,
    half_octaves: float = DEFAULT_OVERLAP_HALF_OCTAVES,
    min_freqs: int = DEFAULT_MIN_BAND_FREQS,
) -> BandSelection:
    """Stored frequencies inside ``[f_x/2**h, f_x*2**h]``; never interpolate.

    The band is candidate-specific.  A band holding fewer than ``min_freqs`` stored samples is
    rejected with an explicit reason (it is not widened, shifted or interpolated).
    """
    fx = float(f_x_hz)
    h = float(half_octaves)
    if not (math.isfinite(fx) and fx > 0.0):
        raise ValueError(f"f_x_hz must be finite and > 0, got {f_x_hz!r}")
    if not (math.isfinite(h) and h > 0.0):
        raise ValueError(f"half_octaves must be finite and > 0, got {half_octaves!r}")
    if int(min_freqs) < 1:
        raise ValueError(f"min_freqs must be >= 1, got {min_freqs!r}")
    f = np.asarray(freqs_hz, dtype=float).reshape(-1)
    lo = fx * 2.0 ** (-h)
    hi = fx * 2.0 ** (h)
    idx = np.nonzero((f >= lo) & (f <= hi) & np.isfinite(f))[0]
    freqs = tuple(float(f[i]) for i in idx)
    reasons: list[str] = []
    if len(idx) < int(min_freqs):
        reasons.append(
            f"only {len(idx)} stored frequency sample(s) inside the candidate band "
            f"[{lo:.3f}, {hi:.3f}] Hz (need >= {int(min_freqs)}); refused instead of "
            "interpolating or widening the band")
    return BandSelection(
        f_x_hz=fx, f_lo_hz=lo, f_hi_hz=hi, half_octaves=h, freqs_hz=freqs,
        freq_indices=tuple(int(i) for i in idx), min_freqs=int(min_freqs),
        accepted=not reasons, reasons=tuple(reasons))


def _axis_weights(weights: Any, axis: np.ndarray, name: str) -> np.ndarray:
    if weights is None:
        return np.ones(axis.size, dtype=float)
    if isinstance(weights, Mapping):
        values = np.array([float(weights.get(float(x), weights.get(str(float(x)), 1.0)))
                           for x in axis], dtype=float)
    else:
        values = np.asarray(weights, dtype=float).reshape(-1)
        if values.size != axis.size:
            raise ValueError(f"{name} weights length {values.size} != {axis.size}")
    if np.any(~np.isfinite(values)) or np.any(values < 0.0):
        raise ValueError(f"{name} weights must be finite and >= 0")
    if float(values.sum()) <= 0.0:
        raise ValueError(f"{name} weights must not all be zero")
    return values


def shape_mismatch(
    horn_fp: HornFingerprint,
    a_m: float,
    f_x_hz: float,
    *,
    half_octaves: float = DEFAULT_OVERLAP_HALF_OCTAVES,
    min_freqs: int = DEFAULT_MIN_BAND_FREQS,
    min_dirs: int = DEFAULT_MIN_BAND_DIRS,
    good_match_db2: float = DEFAULT_GOOD_MATCH_DB2,
    freq_weights: Any = None,
    dir_weights: Any = None,
    c: float | None = None,
) -> ShapeMismatch:
    """Evaluate E_shape for one (f_x, plane); H/V are separate because callers pass one plane.

    Weights default to uniform (``w_f = w_dir = 1``) and are recorded in the result.  The dB
    differences are squared and averaged (no dB-power averaging).  A deep-null flag is reported
    separately; the numeric E uses the finite reporting floor, so it stays finite.
    """
    band = select_overlap_band(horn_fp.freqs_hz, f_x_hz, half_octaves=half_octaves,
                               min_freqs=min_freqs)
    reasons = list(band.reasons)
    data_quality = horn_fp.data_quality
    if not horn_fp.accepted:
        reasons.extend(f"fingerprint: {r}" for r in horn_fp.reasons)
    if horn_fp.n_dirs < int(min_dirs):
        reasons.append(
            f"only {horn_fp.n_dirs} stored direction(s) in the listening region "
            f"(need >= {int(min_dirs)}); refused instead of interpolating")
    if reasons:
        return ShapeMismatch(
            f_x_hz=float(f_x_hz), plane=horn_fp.plane, band=band, e_shape_db2=None,
            e_shape_rms_db=None, n_freqs=band.n_freqs, n_dirs=horn_fp.n_dirs,
            weights={}, null_fraction=None, uncertainty_db2=None, good_match=False,
            data_quality=data_quality, accepted=False, reasons=tuple(reasons))

    idx = list(band.freq_indices)
    freqs = np.asarray([horn_fp.freqs_hz[i] for i in idx], dtype=float)
    levels = horn_fp.levels_db[idx, :]
    piston_report = piston.relative_report(freqs, a_m, horn_fp.angles_deg, c=c)
    piston_levels = np.asarray(piston_report["level_db"], dtype=float)
    diff = levels - piston_levels
    if np.any(~np.isfinite(diff)):
        return ShapeMismatch(
            f_x_hz=float(f_x_hz), plane=horn_fp.plane, band=band, e_shape_db2=None,
            e_shape_rms_db=None, n_freqs=band.n_freqs, n_dirs=horn_fp.n_dirs,
            weights={}, null_fraction=None, uncertainty_db2=None, good_match=False,
            data_quality=data_quality, accepted=False,
            reasons=tuple(reasons + ["non-finite dB difference in the overlap band"]))

    wf = _axis_weights(freq_weights, freqs, "frequency")
    wd = _axis_weights(dir_weights, horn_fp.angles_deg, "direction")
    per_freq = (np.square(diff) * wd[None, :]).sum(axis=1) / float(wd.sum())
    e = float((per_freq * wf).sum() / float(wf.sum()))
    uncertainty = (float(np.std(per_freq, ddof=1) / math.sqrt(per_freq.size))
                   if per_freq.size > 1 else None)
    null_any = (horn_fp.null_mask[idx, :]
                | np.asarray(piston_report["null_mask"], dtype=bool))
    null_fraction = float(np.mean(null_any)) if null_any.size else None
    reasons2 = list(reasons)
    good = bool(e <= float(good_match_db2) and (null_fraction or 0.0) == 0.0)
    if null_fraction:
        reasons2.append(
            f"deep null(s) present in {null_fraction:.3f} of band samples; E is floored but "
            "the band is not labelled a good match")
    return ShapeMismatch(
        f_x_hz=float(f_x_hz), plane=horn_fp.plane, band=band, e_shape_db2=e,
        e_shape_rms_db=math.sqrt(e), n_freqs=int(freqs.size),
        n_dirs=int(horn_fp.n_dirs),
        weights={
            "freq": "uniform" if freq_weights is None else "caller-supplied",
            "dir": "uniform" if dir_weights is None else "caller-supplied",
            "freq_sum": float(wf.sum()), "dir_sum": float(wd.sum()),
            "floor_db": REPORT_FLOOR_DB, "null_flag_db": NULL_FLAG_DB,
        },
        null_fraction=null_fraction, uncertainty_db2=uncertainty, good_match=good,
        data_quality=data_quality, accepted=True, reasons=tuple(reasons2))


def screen_xo_bands(
    horn_fps: Mapping[str, HornFingerprint],
    a_m: float,
    *,
    candidate_centers_hz: Sequence[float] | None = None,
    half_octaves: float = DEFAULT_OVERLAP_HALF_OCTAVES,
    min_freqs: int = DEFAULT_MIN_BAND_FREQS,
    min_dirs: int = DEFAULT_MIN_BAND_DIRS,
    good_match_db2: float = DEFAULT_GOOD_MATCH_DB2,
    freq_weights: Any = None,
    dir_weights: Any = None,
    c: float | None = None,
) -> XoScreen:
    """Evaluate every candidate crossover and group contiguous good-match bands.

    H and V are evaluated separately; a candidate is "good" only when both accepted planes are
    under threshold and have no deep-null samples.  If no good band exists, the single best
    candidate is returned as an explicitly provisional hypothesis (``fallback_used=True``).
    """
    planes = {str(k).upper(): v for k, v in horn_fps.items()}
    accepted_planes = {p: fp for p, fp in planes.items() if fp.accepted}
    if not accepted_planes:
        return XoScreen(
            candidates=(), good_bands=(), hypothesis_centers_hz=(), fallback_used=False,
            threshold_db2=float(good_match_db2), half_octaves=float(half_octaves),
            min_freqs=int(min_freqs), min_dirs=int(min_dirs),
            data_quality="REFUSED: no accepted horn fingerprint plane",
            reasons=tuple(r for fp in planes.values() for r in fp.reasons))
    if candidate_centers_hz is None:
        reference = accepted_planes.get("H") or next(iter(accepted_planes.values()))
        centers = sorted({float(x) for x in reference.freqs_hz})
    else:
        centers = sorted({float(x) for x in candidate_centers_hz})

    candidates: list[XoCandidate] = []
    for center in centers:
        mismatches = {
            plane: shape_mismatch(
                fp, a_m, center, half_octaves=half_octaves, min_freqs=min_freqs,
                min_dirs=min_dirs, good_match_db2=good_match_db2,
                freq_weights=freq_weights, dir_weights=dir_weights, c=c)
            for plane, fp in sorted(accepted_planes.items())
        }
        reasons = tuple(r for m in mismatches.values() for r in m.reasons)
        accepted = all(m.accepted for m in mismatches.values())
        es = [m.e_shape_db2 for m in mismatches.values() if m.e_shape_db2 is not None]
        e_max = max(es) if es else None
        good = bool(accepted and mismatches and all(m.good_match for m in mismatches.values()))
        candidates.append(XoCandidate(
            f_x_hz=center, mismatches=mismatches, e_max_db2=e_max, accepted=accepted,
            good_match=good, reasons=reasons))

    good_bands: list[GoodMatchBand] = []
    run: list[float] = []

    def _close() -> None:
        if run:
            good_bands.append(GoodMatchBand(
                f_lo_hz=float(min(run)), f_hi_hz=float(max(run)),
                centers_hz=tuple(float(x) for x in run), provisional=len(run) == 1))

    for candidate in candidates:
        if candidate.good_match:
            run.append(candidate.f_x_hz)
        else:
            _close()
            run = []
    _close()

    hypothesis: list[float] = [c for b in good_bands for c in b.centers_hz]
    fallback = False
    if not hypothesis:
        accepted = [c for c in candidates if c.accepted and c.e_max_db2 is not None]
        if accepted:
            best = min(accepted, key=lambda cand: (
                float(cand.e_max_db2) if cand.e_max_db2 is not None else math.inf,
                cand.f_x_hz))
            hypothesis = [best.f_x_hz]
            fallback = True

    quality = ("SCREEN_MAGNITUDE level-only; H and V separate; good-match bands are provisional "
               "reporting labels, not a validated ranking")
    return XoScreen(
        candidates=tuple(candidates), good_bands=tuple(good_bands),
        hypothesis_centers_hz=tuple(hypothesis), fallback_used=fallback,
        threshold_db2=float(good_match_db2), half_octaves=float(half_octaves),
        min_freqs=int(min_freqs), min_dirs=int(min_dirs), data_quality=quality,
        reasons=())
