"""Tests for the dense-memory feasibility preflight (plan A5)."""

from hornlab_search.solve.feasibility import GIB, assess, dense_bytes_lower_bound


def test_fused_cuda_12183_dof_is_not_refused():
    result = assess(12183, "beat_cuda", cuda_fused=True)
    assert result["verdict"] in {"fit", "risky"}
    assert result["basis"] == "calibrated"


def test_fused_cuda_20237_dof_is_refused():
    result = assess(20237, "beat_cuda", cuda_fused=True)
    assert result["verdict"] == "refuse"
    assert result["basis"] == "calibrated"


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
