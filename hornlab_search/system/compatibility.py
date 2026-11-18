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

Phase honesty is explicit: ``has_complex_hv``/``has_complex_balloon`` report *array presence*,
while :attr:`ProvenanceFlags.basis_verified` reports whether the asset's
:class:`~hornlab_search.system.contracts.SourceBasis` is proven (``quality == "EXACT_COMPLEX"``).
A magnitude-only asset therefore answers "complex arrays present" honestly but is still refused by
``require_phase_usable`` queries and by ``HornAsset.require_complex()``.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from hornlab_search.system.contracts import HornAsset

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
