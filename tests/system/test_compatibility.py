"""Tier-0 compatibility tests (Stage 1, Lane A).

SYS-05: a magnitude-only asset reports its arrays honestly but refuses phase claims through the
real ``HornAsset.require_complex()`` API and through Tier-0 ``require_phase_usable`` queries.
SYS-06: an ``EXACT_COMPLEX`` asset with a proven basis passes the phase gate and is accepted by a
Tier-0 query whose band and family it satisfies. Any Tier-1+ question raises ``TierTooHigh``.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from hornlab_search.system import compatibility as K
from hornlab_search.system import contracts as C
from hornlab_search.system import piston

REPO = Path(__file__).resolve().parents[2]


def _basis() -> C.SourceBasis:
    return C.SourceBasis(
        per_input="normal_velocity_mps", distance_m=2.0,
        origin_xyz_m=(0.0, 0.0, 0.0), angular_frame="hornfab_cuts_hv",
        source_geometry_hash="mesh-sha",
    )


def _asset(quality: C.AssetQuality, *, fields: frozenset[str] | None = None,
           freqs: tuple[float, ...] = (500.0, 1000.0, 2000.0, 4000.0, 8000.0),
           family: str | None = "OSSE", brief_id: str | None = "home_landscape",
           provenance: str = "status_ok",
           data_quality: str = "test fixture") -> C.HornAsset:
    if fields is None:
        fields = frozenset({"p_h", "p_v", "p_balloon", "spl_h_db", "spl_v_db", "z_throat"})
    return C.HornAsset(
        asset_id="asset-000000000000",
        design_hash="0123456789ab",
        response_path="runs/run/designs/0123456789ab/response.npz",
        mesh_path=None,
        geometry=C.GeometryMetadata(
            family=family, brief_id=brief_id, physical_solve_id="pid",
            objective_version="7", band_hz=(freqs[0], freqs[-1]) if freqs else None,
            extra={"provenance": provenance, "data_quality": data_quality},
        ),
        available_fields=fields,
        quality=quality,
        freqs_hz=freqs,
        source_basis=_basis() if quality == "EXACT_COMPLEX" else None,
    )


# --------------------------------------------------------------------------- Tier-0 questions


def test_has_complex_hv_and_balloon_report_actual_fields() -> None:
    full = _asset("EXACT_COMPLEX")
    assert K.has_complex_hv(full) is True
    assert K.has_complex_balloon(full) is True

    only_h = _asset("MAGNITUDE_ONLY", fields=frozenset({"p_h"}))
    assert K.has_complex_hv(only_h) is False
    assert K.has_complex_balloon(only_h) is False


def test_covers_band_is_inclusive_and_explicit_about_missing_grid() -> None:
    asset = _asset("EXACT_COMPLEX")
    assert K.covers_band(asset, 700.0, 8000.0).covered is True
    edge = K.covers_band(asset, 500.0, 8000.0)
    assert edge.covered is True and edge.asset_lo_hz == 500.0
    low = K.covers_band(asset, 300.0, 8000.0)
    assert low.covered is False and low.asset_lo_hz == 500.0
    empty = K.covers_band(_asset("GEOMETRY_ONLY", fields=frozenset(), freqs=()), 500.0, 8000.0)
    assert empty.covered is False and empty.asset_lo_hz is None


def test_provenance_flags_distinguish_stale_unknown_and_basis() -> None:
    stale = K.provenance_flags(_asset("STALE_SOURCE", provenance="status_failed",
                                      data_quality="status.json ok=false: boom"))
    assert stale.stale is True and stale.unknown is False
    assert stale.basis_verified is False

    unknown = K.provenance_flags(_asset("GEOMETRY_ONLY", fields=frozenset(), freqs=(),
                                        provenance="geometry_only"))
    assert unknown.stale is False and unknown.unknown is True

    exact = K.provenance_flags(_asset("EXACT_COMPLEX"))
    assert exact.basis_verified is True and exact.stale is False
    assert exact.complex_present is True

    magnitude = K.provenance_flags(_asset("MAGNITUDE_ONLY"))
    assert magnitude.complex_present is True and magnitude.basis_verified is False


def test_family_brief_reads_stored_metadata_only() -> None:
    flags = K.family_brief(_asset("EXACT_COMPLEX", family="R-OSSE", brief_id="brief-42"))
    assert flags.family == "R-OSSE"
    assert flags.brief_id == "brief-42"
    assert flags.objective_version == "7"

    missing = K.family_brief(_asset("MAGNITUDE_ONLY", family=None, brief_id=None))
    assert missing.family is None and missing.brief_id is None


# --------------------------------------------------------------------------- SYS-05 / SYS-06


def test_sys05_magnitude_only_refuses_phase_through_real_hornasset_api() -> None:
    asset = _asset("MAGNITUDE_ONLY")
    with pytest.raises(C.PhaseUnavailable):
        asset.require_complex()

    query = K.Tier0Query(f_lo_hz=700.0, f_hi_hz=8000.0, require_complex_hv=True,
                         require_phase_usable=True)
    row = K.evaluate_tier0(asset, query)
    assert row.has_complex_hv is True          # arrays exist ...
    assert row.accepted is False               # ... but the phase requirement is not met
    assert any("phase claims refused" in reason for reason in row.reasons)


def test_sys06_exact_complex_passes_phase_and_tier0() -> None:
    asset = _asset("EXACT_COMPLEX")
    assert asset.require_complex().per_input == "normal_velocity_mps"

    query = K.Tier0Query(f_lo_hz=700.0, f_hi_hz=8000.0, require_complex_hv=True,
                         require_complex_balloon=True, require_fresh=True,
                         require_phase_usable=True, family="OSSE", brief_id="home_landscape")
    row = K.evaluate_tier0(asset, query)
    assert row.accepted is True, row.reasons
    assert row.reasons == ()
    assert row.family.family == "OSSE"


def test_tier0_rejects_wrong_band_family_and_stale_provenance() -> None:
    asset = _asset("EXACT_COMPLEX", family="OSSE")
    row = K.evaluate_tier0(
        asset, K.Tier0Query(f_lo_hz=100.0, f_hi_hz=8000.0, require_fresh=True, family="ICW"))
    assert row.accepted is False
    joined = " | ".join(row.reasons)
    assert "does not cover" in joined and "family" in joined

    stale = _asset("STALE_SOURCE", provenance="status_failed")
    row = K.evaluate_tier0(stale, K.Tier0Query(f_lo_hz=700.0, f_hi_hz=8000.0, require_fresh=True))
    assert row.accepted is False
    assert any("not fresh" in reason for reason in row.reasons)


# --------------------------------------------------------------------------- tier guard / query


def test_tier1_questions_raise_tier_too_high() -> None:
    with pytest.raises(K.TierTooHigh):
        K.assert_tier0("crossover_optimization")
    with pytest.raises(K.TierTooHigh):
        K.assert_tier0("phase_combination")
    K.assert_tier0("band_coverage")  # a Tier-0 claim is fine


def test_query_rejects_malformed_bands() -> None:
    with pytest.raises(ValueError, match="lo"):
        K.Tier0Query(f_lo_hz=8000.0, f_hi_hz=700.0)
    with pytest.raises(ValueError):
        K.Tier0Query(f_lo_hz=float("nan"), f_hi_hz=8000.0)

# --------------------------------------------------------------------------- stage-5 fingerprint


def _fingerprint(plane: str, levels: np.ndarray, *,
                 angles: np.ndarray | None = None,
                 freqs: tuple[float, ...] = (500.0, 600.0, 700.0, 800.0, 900.0, 1000.0),
                 a_m: float = 0.11) -> K.HornFingerprint:
    if angles is None:
        angles = np.arange(-30.0, 30.1, 10.0)
    return K.make_fingerprint(
        plane, np.asarray(freqs, dtype=float), angles, levels,
        source="synthetic-test")


def _piston_levels(freqs: tuple[float, ...], angles: np.ndarray, a_m: float) -> np.ndarray:
    rel = piston.relative_level_db(
        np.asarray(freqs, dtype=float)[:, None], a_m, angles[None, :])
    return 100.0 + np.asarray(rel, dtype=float)


def test_h_left_right_parity_and_asymmetry_scores_worse() -> None:
    angles = np.arange(-30.0, 30.1, 10.0)
    freqs = (500.0, 600.0, 700.0, 800.0, 900.0, 1000.0)
    a_m = 0.11
    levels = _piston_levels(freqs, angles, a_m)
    symmetric = _fingerprint("H", levels, angles=angles, freqs=freqs, a_m=a_m)
    mirrored = _fingerprint("H", levels[:, ::-1], angles=angles, freqs=freqs, a_m=a_m)

    e_sym = K.shape_mismatch(symmetric, a_m, 700.0)
    e_mirror = K.shape_mismatch(mirrored, a_m, 700.0)
    assert e_sym.accepted and e_mirror.accepted
    assert e_sym.e_shape_db2 == pytest.approx(e_mirror.e_shape_db2, abs=1e-12)

    asymmetric_levels = levels.copy()
    asymmetric_levels[:, angles > 0.0] += 2.0
    asymmetric = _fingerprint("H", asymmetric_levels, angles=angles, freqs=freqs, a_m=a_m)
    e_asym = K.shape_mismatch(asymmetric, a_m, 700.0)
    assert e_asym.accepted
    assert e_asym.e_shape_db2 > e_sym.e_shape_db2 + 1.0


def test_hv_planes_stay_separate_and_a_mismatch_scores_worse() -> None:
    angles = np.arange(-15.0, 15.1, 5.0)
    freqs = (500.0, 600.0, 700.0, 800.0, 900.0, 1000.0)
    a_m = 0.11
    matched = _piston_levels(freqs, angles, a_m)

    h_good = _fingerprint("H", matched, angles=angles, freqs=freqs, a_m=a_m)
    v_good = _fingerprint("V", matched, angles=angles, freqs=freqs, a_m=a_m)
    v_bad = _fingerprint("V", matched - 2.0 * np.abs(angles)[None, :],
                         angles=angles, freqs=freqs, a_m=a_m)

    e_h_good = K.shape_mismatch(h_good, a_m, 700.0)
    e_v_good = K.shape_mismatch(v_good, a_m, 700.0)
    e_v_bad = K.shape_mismatch(v_bad, a_m, 700.0)
    assert e_h_good.e_shape_db2 == pytest.approx(0.0, abs=1e-12)
    assert e_v_good.e_shape_db2 == pytest.approx(0.0, abs=1e-12)
    assert e_v_bad.e_shape_db2 > e_v_good.e_shape_db2 + 1.0
    # Changing only V must not change H (separate planes, no pooled metric).
    e_h_again = K.shape_mismatch(h_good, a_m, 700.0)
    assert e_h_again.e_shape_db2 == pytest.approx(e_h_good.e_shape_db2, abs=1e-15)


def test_missing_frequency_or_angle_is_rejected_not_interpolated() -> None:
    angles = np.arange(-30.0, 30.1, 10.0)
    freqs = (500.0, 600.0, 700.0, 800.0, 900.0, 1000.0)
    levels = _piston_levels(freqs, angles, 0.11)
    fp = _fingerprint("H", levels, angles=angles, freqs=freqs)

    band = K.select_overlap_band((500.0, 600.0), 500.0, min_freqs=3)
    assert band.accepted is False
    assert any("interpolating" in reason for reason in band.reasons)

    rejected = K.shape_mismatch(fp, 0.11, 500.0, min_freqs=3)
    assert rejected.accepted is False
    assert any("interpolating" in reason for reason in rejected.reasons)

    no_axis = K.make_fingerprint(
        "H", np.asarray(freqs), np.array([-20.0, -10.0, 10.0, 20.0]),
        np.zeros((len(freqs), 4)), source="synthetic-test")
    assert no_axis.accepted is False
    assert any("on-axis" in reason for reason in no_axis.reasons)


def test_magnitude_only_asset_refuses_phase_alignment_with_existing_tokens() -> None:
    asset = _asset("MAGNITUDE_ONLY")
    with pytest.raises(C.PhaseUnavailable) as excinfo:
        K.require_phase_alignment(asset)
    message = str(excinfo.value)
    assert "MAGNITUDE_ONLY" in message
    assert "PHASE_ALIGNMENT_UNAVAILABLE" in message
