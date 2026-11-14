"""Tests for the dense-memory feasibility preflight (plan A5).

The fused-CUDA model is re-based on the 2026-11-13 measured anchors (solver 38e5b1f,
speed program E6; docs/evidence/SPEED_ADOPTION_2026-11-14.md). The old pin-A arithmetic
(4.0 x 8N^2, "20,237 -> refuse") was declared stale by the G2 fork A/B and is FALSIFIED
by measurement: 24,973 quarter-DOF fits on the 8 GB card. These tests encode the measured
reality — re-based by fix, not by weakening.
"""

from hornlab_search.solve.feasibility import (
    GIB,
    FUSED_CUDA_MEASURED_ANCHORS,
    assess,
    dense_bytes_lower_bound,
    fused_cuda_need_gib,
)


def test_fused_cuda_12183_dof_is_not_refused():
    result = assess(12183, "beat_cuda", cuda_fused=True)
    assert result["verdict"] in {"fit", "risky"}
    assert result["basis"] == "calibrated"


def test_fused_cuda_20237_dof_fits_after_measured_rebase():
    # Old pin-A arithmetic refused 20,237; measured on the new solver it is well inside
    # the fit region (E6 ceiling sweep: 20,152 -> 3.4 GiB measured peak).
    result = assess(20237, "beat_cuda", cuda_fused=True)
    assert result["verdict"] == "fit"
    assert result["basis"] == "calibrated"


def test_fused_cuda_23850_dof_fits_and_24973_is_risky_not_refused():
    # Both measured-fit anchors from the E6 ceiling sweep.
    assert assess(23850, "beat_cuda", cuda_fused=True)["verdict"] == "fit"
    risky = assess(24973, "beat_cuda", cuda_fused=True)
    assert risky["verdict"] == "risky"  # measured fit, but within the risky band
    assert risky["verdict"] != "refuse"


def test_fused_cuda_refuses_beyond_last_measured_anchor():
    # No measured evidence above 24,973; the envelope extrapolates the final measured
    # slope, so past-anchor sizes are refused until a new measured anchor lands.
    result = assess(28000, "beat_cuda", cuda_fused=True)
    assert result["verdict"] == "refuse"


def test_fused_cuda_production_caps_must_stay_fit():
    # Owner guard (caps raised 12,000 -> 24,000 by owner decision 2026-11-14): the production
    # dof caps in the print configs + fused_cuda profile must remain inside the FIT band under
    # the calibrated envelope. If a future re-base pushes these out of "fit", that re-base is
    # wrong or the anchors must be re-measured BEFORE any cap change — the owner constraint
    # forbids silently vetoing existing production sizes. 24,000 interpolates to ~4.7 GiB.
    for n in (12000, 24000):
        result = assess(n, "beat_cuda", cuda_fused=True)
        assert result["verdict"] == "fit", f"caps {n}: " + result["reason"]


def test_fused_cuda_need_gib_is_monotone_and_matches_anchor_points():
    for i, (n_dof, peak_mib) in enumerate(FUSED_CUDA_MEASURED_ANCHORS):
        if i == 0:
            continue  # first anchor rides the origin chord, not an exact pass-through
        need = fused_cuda_need_gib(n_dof)
        assert abs(need - peak_mib / 1024) < 1e-9
    vals = [fused_cuda_need_gib(500 * n) for n in range(1, 60)]
    assert vals == sorted(vals)


def test_cpu_34000_dof_is_refused_with_expected_need():
    result = assess(34000, "bempp_cpu")
    assert result["verdict"] == "refuse"
    expected_gib = 3 * 16 * 34000**2 / GIB
    assert abs(result["need_gib"] - expected_gib) < 0.01
    assert expected_gib > 24
    assert result["basis"] == "provisional"


def test_dense_bytes_lower_bound_is_complex64_square():
    assert dense_bytes_lower_bound(1000) == 8 * 1000**2
    assert dense_bytes_lower_bound(1000, dtype_bytes=16) == 16 * 1000**2
