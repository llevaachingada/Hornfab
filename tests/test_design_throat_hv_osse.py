"""Shared near-throat H/V block: shared math and the native OSSE mapping (CPU, no mesher)."""
from __future__ import annotations

import copy
import math

import numpy as np
import pytest

from hornlab_search.design import throat_hv
from hornlab_search.design.families import to_mesher_config, validate
from hornlab_search.mesh import sizing
from hornlab_search.types import Design, GeometryInvalidError, MeshSpec

OSSE = dict(r0_mm=17.78, a_deg=37.5, a0_deg=15.5, L_mm=260.0, n=4.0, s=0.7, q=0.995, k=1.0,
            exponent=2.0, aspect_ratio=1.0)
MORPH = dict(morph_target=3, morph_width_mm=500.0, morph_height_mm=300.0, morph_exponent=4.0)


def _cfg(params, tmp_path):
    ms = MeshSpec(epw=6.0, f_max_hz=10000.0, quadrants="1", max_triangles=73600)
    return to_mesher_config(Design("OSSE", copy.deepcopy(params)), ms,
                            sizing.res_mm_for(6.0, 10000.0), tmp_path / "m.msh")


# ------------------------------------------------------------------ shared math

def test_hv_scale_is_exact_identity_at_rho_one():
    phi = np.linspace(0.0, 2.0 * math.pi, 37)
    assert np.array_equal(throat_hv.hv_scale(1.0, phi), np.ones_like(phi))
    assert throat_hv.hv_scale(None, 0.3) == 1.0


def test_hv_scale_axes_mirror_and_geometric_mean():
    rho = 2.25
    assert throat_hv.hv_scale(rho, 0.0) == pytest.approx(1.5)
    assert throat_hv.hv_scale(rho, math.pi / 2) == pytest.approx(1.0 / 1.5)
    for p in (0.2, 0.7, 1.1):                          # mirror planes x and y
        assert throat_hv.hv_scale(rho, p) == pytest.approx(throat_hv.hv_scale(rho, -p))
        assert throat_hv.hv_scale(rho, p) == pytest.approx(throat_hv.hv_scale(rho, math.pi - p))
    assert throat_hv.hv_scale(rho, 0.0) * throat_hv.hv_scale(rho, math.pi / 2) == pytest.approx(1.0)


def test_ath_ramp_matches_ath_morph_factor():
    t = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    w = throat_hv.ath_ramp(t, 0.5, 2.0)
    assert np.allclose(w, [0.0, 0.0, 0.0, 0.25, 1.0])
    assert throat_hv.ath_ramp(1.0, None, None) == 1.0
    assert throat_hv.ath_ramp(0.5, None, None) == pytest.approx(0.125)   # Ath default gamma 3


def test_parse_ranges():
    assert throat_hv.parse({}) == dict.fromkeys(throat_hv.KEYS)
    with pytest.raises(throat_hv.ThroatHVError):
        throat_hv.parse({"throat_hv_ratio": 5.0})
    with pytest.raises(throat_hv.ThroatHVError):
        throat_hv.parse({"g_hv_onset_frac": 0.95}, prefix="g_")


def test_os_k_expression_keeps_driver_slope_and_splits_planes():
    """OS-SE base(z) with k(p): slope at z=0 is tan(a0) on every azimuth; H grows sooner."""
    r0, a0, a, rho = 18.0, math.radians(2.0), math.radians(40.0), 4.0

    def base(z, k):
        return math.sqrt((k * r0) ** 2 + 2 * k * r0 * z * math.tan(a0) + (z * math.tan(a)) ** 2) \
            + r0 * (1 - k)

    k_h = 1.0 * throat_hv.hv_scale_inverse(rho, 0.0)
    k_v = 1.0 * throat_hv.hv_scale_inverse(rho, math.pi / 2)
    dz = 1e-6
    for k in (k_h, k_v):
        assert base(0.0, k) == pytest.approx(r0)
        assert (base(dz, k) - base(0.0, k)) / dz == pytest.approx(math.tan(a0), rel=1e-3)
    assert base(40.0, k_h) > base(40.0, 1.0) > base(40.0, k_v)


# ------------------------------------------------------------------ native OSSE mapping

def test_absent_block_is_byte_identical(tmp_path):
    assert _cfg(OSSE, tmp_path) == _cfg({**OSSE}, tmp_path)
    cfg = _cfg(OSSE, tmp_path)
    assert cfg["profile"]["k"] == 1.0
    assert not any(k in cfg.get("profile", {}) for k in throat_hv.KEYS)


def test_ratio_one_is_byte_identical(tmp_path):
    assert _cfg({**OSSE, "throat_hv_ratio": 1.0}, tmp_path) == _cfg(OSSE, tmp_path)


def test_ratio_becomes_k_expression(tmp_path):
    cfg = _cfg({**OSSE, "throat_hv_ratio": 2.0}, tmp_path)
    expr = cfg["profile"]["k"]
    assert isinstance(expr, str) and "cos(2*p)" in expr
    val = eval(expr, {"cos": math.cos, "p": 0.0})        # noqa: S307 - our own literal expression
    assert val == pytest.approx(1.0 / math.sqrt(2.0))
    assert "throat_hv_ratio" not in cfg["profile"]


def test_onset_and_ramp_alias_morph(tmp_path):
    cfg = _cfg({**OSSE, **MORPH, "hv_onset_frac": 0.1, "section_exp_ramp": 1.5}, tmp_path)
    assert cfg["morph"]["morph_fixed"] == 0.1 and cfg["morph"]["morph_rate"] == 1.5
    assert "hv_onset_frac" not in cfg["morph"]


def test_refusals():
    with pytest.raises(GeometryInvalidError):          # inactive without a morph target
        validate(Design("OSSE", {**OSSE, "hv_onset_frac": 0.1}))
    with pytest.raises(GeometryInvalidError):          # alias and native both given
        validate(Design("OSSE", {**OSSE, **MORPH, "hv_onset_frac": 0.1, "morph_fixed": 0.2}))
    with pytest.raises(GeometryInvalidError):          # out of range
        validate(Design("OSSE", {**OSSE, "throat_hv_ratio": 9.0}))
