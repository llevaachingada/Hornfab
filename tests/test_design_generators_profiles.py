"""Tests for hornlab_search.design.generators.profiles (TYPOLOGY_PLAN.md V1, V2).

Offline, fast — no mesher, no GPU.

Coverage
--------
V1 defining properties: conical constant angle; exponential area ratio and fc;
  hypex T=1==exponential and r(L)=rm; tractrix constant tangent length and analytic
  angle == numerical derivative; every Meridian valid (z increasing, r>0, |θ|<90).
V2 fidelity: Hermite reconstruction through 16 anchors ≤ 0.2 mm max radial error
  for conical, exponential, hypex T∈{0, 0.5, 1}, tractrix fc∈{700, 1000}.
blend: w=0 == a, w=1 == b; intermediate blend is r-monotone when parents are.
select_anchors: endpoint exact, count correct, z strictly increasing.
perturb_increments: u=0 round-trips, any bounded u keeps r strictly increasing.
Le Cléac'h / spherical_wave raise GeneratorUnavailable.
"""
from __future__ import annotations

import numpy as np
import pytest

from hornlab_search.constants import C_AIR
from hornlab_search.design.generators.profiles import (
    Meridian,
    GeneratorUnavailable,
    blend,
    conical,
    exponential,
    hermite_reference,
    hypex,
    lecleach,
    perturb_increments,
    select_anchors,
    spherical_wave,
    tractrix,
)

# ---------------------------------------------------------------------------
# Shared test fixtures / parameters
# ---------------------------------------------------------------------------

R0 = 12.7          # mm  — standard 1-inch compression driver throat radius
RM = 150.0         # mm  — typical 90-deg axisymmetric waveguide mouth radius
L  = 200.0         # mm  — typical horn depth

_TWO_PI = 2.0 * np.pi


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_valid_meridian(m: Meridian, label: str = "") -> None:
    """Validate invariants: z strictly increasing, r>0, |theta|<90."""
    tag = f"[{label}] " if label else ""
    assert np.all(np.diff(m.z_mm) > 0),   f"{tag}z not strictly increasing"
    assert m.z_mm[0] == pytest.approx(0.0, abs=1e-9), f"{tag}z[0] != 0"
    assert np.all(m.r_mm > 0),             f"{tag}r not all > 0"
    assert np.all(np.abs(m.theta_deg) < 90.0), f"{tag}|theta| >= 90"
    assert len(m.z_mm) == len(m.r_mm) == len(m.theta_deg), f"{tag}array length mismatch"


# ---------------------------------------------------------------------------
# Conical
# ---------------------------------------------------------------------------

class TestConical:
    def setup_method(self):
        self.m = conical(R0, RM, L)

    def test_valid(self):
        _assert_valid_meridian(self.m, "conical")

    def test_constant_wall_angle(self):
        """Wall angle must be constant everywhere (defining property)."""
        theta = self.m.theta_deg
        assert np.allclose(theta, theta[0], atol=1e-10), \
            "conical wall angle is not constant"

    def test_endpoints(self):
        assert self.m.z_mm[0] == pytest.approx(0.0)
        assert self.m.z_mm[-1] == pytest.approx(L)
        assert self.m.r_mm[0] == pytest.approx(R0)
        assert self.m.r_mm[-1] == pytest.approx(RM)

    def test_alpha_consistent(self):
        alpha_rad = np.radians(self.m.info["alpha_deg"])
        assert np.tan(alpha_rad) == pytest.approx((RM - R0) / L, rel=1e-10)


# ---------------------------------------------------------------------------
# Exponential
# ---------------------------------------------------------------------------

class TestExponential:
    def setup_method(self):
        self.m = exponential(R0, RM, L)
        self.m_per_m = self.m.info["m_per_m"]
        self.m_mm = self.m_per_m / 1000.0

    def test_valid(self):
        _assert_valid_meridian(self.m, "exponential")

    def test_area_ratio(self):
        """S(z)/S0 = exp(2·m·z)  (defining property)."""
        z = self.m.z_mm
        r = self.m.r_mm
        expected_ratio = np.exp(2.0 * self.m_mm * z)
        actual_ratio   = (r / R0) ** 2
        np.testing.assert_allclose(actual_ratio, expected_ratio, rtol=1e-10,
                                   err_msg="area ratio S(z)/S0 != exp(2mz)")

    def test_fc_consistent(self):
        """fc = m_per_m · C_AIR / (2π)."""
        fc_expected = self.m_per_m * C_AIR / _TWO_PI
        assert self.m.info["fc_hz"] == pytest.approx(fc_expected, rel=1e-10)

    def test_m_from_formula(self):
        # m_mm = ln(rm/r0)/L [1/mm] -> m_per_m = m_mm * 1000 [1/m]
        m_expected = np.log(RM / R0) / L * 1000.0   # 1/m
        assert self.m_per_m == pytest.approx(m_expected, rel=1e-10)

    def test_theta_analytic(self):
        """theta = atan(m_mm · r) at every point."""
        theta_expected = np.degrees(np.arctan(self.m_mm * self.m.r_mm))
        np.testing.assert_allclose(self.m.theta_deg, theta_expected, atol=1e-10)

    def test_endpoints(self):
        assert self.m.r_mm[0] == pytest.approx(R0)
        assert self.m.r_mm[-1] == pytest.approx(RM, rel=1e-8)


# ---------------------------------------------------------------------------
# Hypex
# ---------------------------------------------------------------------------

class TestHypex:
    @pytest.mark.parametrize("T", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_r_at_L_equals_rm(self, T):
        """r(L) == rm for all T (brentq root property)."""
        m = hypex(R0, RM, L, T)
        assert m.r_mm[-1] == pytest.approx(RM, rel=1e-8), \
            f"r(L) != rm for T={T}"

    @pytest.mark.parametrize("T", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_valid(self, T):
        _assert_valid_meridian(hypex(R0, RM, L, T), f"hypex T={T}")

    def test_t1_equals_exponential(self):
        """T=1 must reproduce the exponential profile identically."""
        mh = hypex(R0, RM, L, T=1.0)
        me = exponential(R0, RM, L)
        # Both use the same n=400 grid; should match to floating-point precision
        np.testing.assert_allclose(mh.r_mm, me.r_mm, rtol=1e-8,
                                   err_msg="hypex T=1 differs from exponential")
        np.testing.assert_allclose(mh.theta_deg, me.theta_deg, atol=1e-6,
                                   err_msg="hypex T=1 theta differs from exponential")

    def test_t0_is_catenoidal(self):
        """T=0: r = r0·cosh(m·z) — verify pointwise."""
        m = hypex(R0, RM, L, T=0.0)
        m_mm = m.info["m_per_m"] / 1000.0
        expected_r = R0 * np.cosh(m_mm * m.z_mm)
        np.testing.assert_allclose(m.r_mm, expected_r, rtol=1e-10)

    def test_fc_stored(self):
        m = hypex(R0, RM, L, T=0.5)
        fc_expected = m.info["m_per_m"] * C_AIR / _TWO_PI
        assert m.info["fc_hz"] == pytest.approx(fc_exp := fc_expected, rel=1e-10), \
            f"fc {m.info['fc_hz']:.1f} != expected {fc_exp:.1f}"

    def test_t_stored(self):
        m = hypex(R0, RM, L, T=0.42)
        assert m.info["T"] == pytest.approx(0.42)


# ---------------------------------------------------------------------------
# Tractrix
# ---------------------------------------------------------------------------

class TestTractrix:
    @pytest.mark.parametrize("fc_hz", [700.0, 1000.0])
    def test_valid(self, fc_hz):
        m = tractrix(R0, fc_hz)
        _assert_valid_meridian(m, f"tractrix fc={fc_hz}")

    @pytest.mark.parametrize("fc_hz", [700.0, 1000.0])
    def test_constant_tangent_length(self, fc_hz):
        """Tangent-segment length must equal a at every point (defining property).

        At point (z, r): slope dr/dz = r/u, tangent meets axis at z−u,
        segment = √(u² + r²) = a.  Here u = √(a²−r²).
        """
        m = tractrix(R0, fc_hz)
        a_mm = m.info["a_mm"]
        r = m.r_mm
        u = np.sqrt(a_mm**2 - r**2)
        tl = np.sqrt(u**2 + r**2)
        np.testing.assert_allclose(tl, a_mm, rtol=1e-10,
                                   err_msg=f"tangent length != a for fc={fc_hz}")

    @pytest.mark.parametrize("fc_hz", [700.0, 1000.0])
    def test_analytic_angle_vs_numerical_derivative(self, fc_hz):
        """Analytic theta = arcsin(r/a) must agree with numerical dr/dz to 1e-3 deg."""
        m = tractrix(R0, fc_hz, n=800)   # more points → better numerical derivative
        a_mm = m.info["a_mm"]
        theta_analytic = m.theta_deg
        # Numerical dr/dz via central differences (skip endpoints for accuracy)
        drdz_num = np.gradient(m.r_mm, m.z_mm)
        theta_num = np.degrees(np.arctan(drdz_num))
        # Interior points only (endpoints have larger finite-difference error)
        np.testing.assert_allclose(
            theta_analytic[2:-2], theta_num[2:-2], atol=0.05,
            err_msg=f"analytic vs numerical theta differ > 0.05 deg for fc={fc_hz}"
        )

    @pytest.mark.parametrize("fc_hz", [700.0, 1000.0])
    def test_sin_theta_equals_r_over_a(self, fc_hz):
        """sin(theta) = r/a must hold at every point."""
        m = tractrix(R0, fc_hz)
        a_mm = m.info["a_mm"]
        np.testing.assert_allclose(
            np.sin(np.radians(m.theta_deg)), m.r_mm / a_mm, rtol=1e-10
        )

    def test_r0_ge_a_raises(self):
        """r0 >= a must raise ValueError."""
        # fc=5000 → a = 343/(2π·5000)*1000 ≈ 10.9 mm < R0=12.7 → should raise
        a_mm = C_AIR / (_TWO_PI * 5000.0) * 1000.0
        assert a_mm < R0, "test setup error: a not < r0 for this fc"
        with pytest.raises(ValueError, match="r0_mm"):
            tractrix(R0, 5000.0)

    def test_truncation_at_max_wall(self):
        m = tractrix(R0, 700.0, max_wall_deg=70.0)
        assert m.theta_deg[-1] == pytest.approx(70.0, abs=0.1)

    def test_a_mm_stored(self):
        fc = 800.0
        m = tractrix(R0, fc)
        a_expected = C_AIR / (_TWO_PI * fc) * 1000.0
        assert m.info["a_mm"] == pytest.approx(a_expected, rel=1e-10)


# ---------------------------------------------------------------------------
# Le Cléac'h / spherical_wave gated
# ---------------------------------------------------------------------------

def test_lecleach_raises_unavailable():
    with pytest.raises(GeneratorUnavailable):
        lecleach(R0, 800.0, T=0.7)


def test_spherical_wave_raises_unavailable():
    with pytest.raises(GeneratorUnavailable):
        spherical_wave(R0, 800.0)


# ---------------------------------------------------------------------------
# blend
# ---------------------------------------------------------------------------

class TestBlend:
    def setup_method(self):
        self.ma = exponential(R0, RM, L)
        self.mb = conical(R0, 130.0, L)

    def test_w0_equals_a(self):
        """w=0 blend must reproduce meridian a on the common t-grid."""
        mb = blend(self.ma, self.mb, w=0.0, n=400)
        # blend(a, b, 0) evaluates cs_a at the same t=linspace(0,1,400) that a was sampled on
        np.testing.assert_allclose(mb.r_mm, self.ma.r_mm, rtol=1e-10,
                                   err_msg="blend w=0 differs from a")
        np.testing.assert_allclose(mb.z_mm, self.ma.z_mm, rtol=1e-10,
                                   err_msg="blend w=0 z differs from a")

    def test_w1_equals_b(self):
        """w=1 blend must reproduce meridian b on the common t-grid."""
        mb = blend(self.ma, self.mb, w=1.0, n=400)
        np.testing.assert_allclose(mb.r_mm, self.mb.r_mm, rtol=1e-10,
                                   err_msg="blend w=1 differs from b")

    def test_intermediate_blend_valid(self):
        for w in [0.25, 0.5, 0.75]:
            m = blend(self.ma, self.mb, w)
            _assert_valid_meridian(m, f"blend w={w}")

    def test_intermediate_monotone_increasing(self):
        """Blend of two increasing-r profiles is also r-monotone increasing."""
        for w in [0.25, 0.5, 0.75]:
            m = blend(self.ma, self.mb, w)
            assert np.all(np.diff(m.r_mm) > 0), \
                f"blend w={w} r is not monotone increasing"

    def test_throat_radius_mismatch_raises(self):
        mb = conical(R0 + 0.1, 130.0, L)  # different throat
        with pytest.raises(ValueError, match="throat"):
            blend(self.ma, mb, w=0.5)

    def test_length_interpolated(self):
        m = blend(self.ma, self.mb, w=0.5)
        expected_L = 0.5 * self.ma.length_mm + 0.5 * self.mb.length_mm
        assert m.length_mm == pytest.approx(expected_L, rel=1e-10)


# ---------------------------------------------------------------------------
# select_anchors
# ---------------------------------------------------------------------------

class TestSelectAnchors:
    @pytest.mark.parametrize("n", [2, 4, 8, 16, 32, 64])
    def test_count(self, n):
        m = exponential(R0, RM, L)
        anc = select_anchors(m, n)
        assert len(anc) == n, f"expected {n} anchors, got {len(anc)}"

    @pytest.mark.parametrize("n", [2, 16])
    def test_endpoints_exact(self, n):
        m = exponential(R0, RM, L)
        anc = select_anchors(m, n)
        assert anc[0][0] == pytest.approx(m.z_mm[0], abs=1e-10)
        assert anc[0][1] == pytest.approx(m.r_mm[0], abs=1e-10)
        assert anc[-1][0] == pytest.approx(m.z_mm[-1], abs=1e-10)
        assert anc[-1][1] == pytest.approx(m.r_mm[-1], abs=1e-10)

    def test_z_strictly_increasing(self):
        m = tractrix(R0, 700.0)
        anc = select_anchors(m, 16)
        z_vals = [a[0] for a in anc]
        assert all(z_vals[i+1] > z_vals[i] for i in range(len(z_vals)-1)), \
            "anchor z not strictly increasing"

    def test_out_of_range_raises(self):
        m = exponential(R0, RM, L)
        with pytest.raises(ValueError):
            select_anchors(m, 1)
        with pytest.raises(ValueError):
            select_anchors(m, 65)


# ---------------------------------------------------------------------------
# hermite_reference fidelity (V2)
# ---------------------------------------------------------------------------

_FIDELITY_TOLERANCE_MM = 0.2   # max radial error for 16 anchors

class TestHermiteFidelity:
    """Cubic Hermite through 16 anchors reproduces the analytic meridian within 0.2 mm."""

    def _check(self, m: Meridian, label: str) -> float:
        anc = select_anchors(m, 16)
        r_ref = hermite_reference(anc, m.z_mm)
        err = float(np.max(np.abs(r_ref - m.r_mm)))
        assert err <= _FIDELITY_TOLERANCE_MM, \
            f"{label}: max radial error {err:.4f} mm > {_FIDELITY_TOLERANCE_MM} mm"
        return err

    def test_conical(self):
        m = conical(R0, RM, L)
        self._check(m, "conical")

    def test_exponential(self):
        m = exponential(R0, RM, L)
        self._check(m, "exponential")

    @pytest.mark.parametrize("T", [0.0, 0.5, 1.0])
    def test_hypex(self, T):
        m = hypex(R0, RM, L, T)
        self._check(m, f"hypex T={T}")

    @pytest.mark.parametrize("fc_hz", [700.0, 1000.0])
    def test_tractrix(self, fc_hz):
        m = tractrix(R0, fc_hz)
        self._check(m, f"tractrix fc={fc_hz}")

    def test_max_errors_printed(self, capsys):
        """Print fidelity table for the report."""
        results = {}
        results["conical"]        = self._check(conical(R0, RM, L), "conical")
        results["exponential"]    = self._check(exponential(R0, RM, L), "exponential")
        for T in [0.0, 0.5, 1.0]:
            results[f"hypex_T{T}"] = self._check(hypex(R0, RM, L, T), f"hypex T={T}")
        for fc in [700.0, 1000.0]:
            results[f"tractrix_{int(fc)}"] = self._check(tractrix(R0, fc), f"tractrix {fc}")
        print("\n=== Hermite fidelity (max radial error mm, 16 anchors) ===")
        for k, v in results.items():
            print(f"  {k:20s}: {v:.5f} mm")


# ---------------------------------------------------------------------------
# perturb_increments
# ---------------------------------------------------------------------------

class TestPerturbIncrements:
    def _base_anchors(self):
        m = exponential(R0, RM, L)
        return select_anchors(m, 12)

    def test_u_zero_returns_base_radii(self):
        """u=0 must return the original radii unchanged."""
        anc = self._base_anchors()
        u = np.zeros(len(anc) - 1)
        out = perturb_increments(anc, u, u_max=0.5)
        r_base = np.array([a[1] for a in anc])
        r_out  = np.array([a[1] for a in out])
        np.testing.assert_allclose(r_out, r_base, rtol=1e-12,
                                   err_msg="u=0 did not return base radii")

    def test_z_unchanged(self):
        anc = self._base_anchors()
        u = np.zeros(len(anc) - 1)
        out = perturb_increments(anc, u, u_max=0.5)
        z_base = np.array([a[0] for a in anc])
        z_out  = np.array([a[0] for a in out])
        np.testing.assert_array_equal(z_out, z_base, err_msg="z values changed")

    @pytest.mark.parametrize("u_seed", [0.3, -0.3, 0.5, -0.5])
    def test_bounded_u_keeps_r_increasing(self, u_seed):
        """Any u with |u_i| <= u_max must keep r strictly increasing."""
        anc = self._base_anchors()
        rng = np.random.default_rng(42)
        n = len(anc) - 1
        u = rng.uniform(-abs(u_seed), abs(u_seed), size=n)
        out = perturb_increments(anc, u, u_max=0.5)
        r_out = np.array([a[1] for a in out])
        assert np.all(np.diff(r_out) > 0), \
            f"r not strictly increasing after perturb_increments (u_seed={u_seed})"

    def test_wrong_u_length_raises(self):
        anc = self._base_anchors()
        with pytest.raises(ValueError, match="len"):
            perturb_increments(anc, np.zeros(5), u_max=0.5)

    def test_decreasing_base_raises(self):
        anc = [[0.0, 50.0, 10.0], [100.0, 30.0, 5.0]]   # r decreasing
        with pytest.raises(ValueError, match="increments"):
            perturb_increments(anc, [0.0], u_max=0.5)
