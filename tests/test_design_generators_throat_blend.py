"""WP9 G3 throat_blend_mm (Report 4 WP9 step 2; dossier section 2.2). Offline.

Ship bar
--------
P1 DEFAULT 0 reproduces today's profile: a stored hypex seed with and without the knob
   gives byte-equal profileH/profileV anchor arrays.
P2 r(0) = r_OS(0) = the throat radius; the classical meridian continues unchanged
   beyond L_b (same arrays).
P3 w is C1 (smoothstep): w'(0) = w'(L_b) = 0 and the blended wall angle lands exactly on
   the classical angle at L_b.
Plus an anchor/Hermite fidelity sanity (0.2 mm) and GeneratorError (not clamping) for a
blend longer than the classical meridian.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from conftest import EXAMPLES, requires_mesher
from hornlab_search.config import load_config
from hornlab_search.design.generated import GENERATOR_ERROR_KEY, GeneratedSpace
from hornlab_search.design.generators import profiles as P
from hornlab_search.design.generators import registry
from hornlab_search.design.space import DesignSpace

R0 = 12.7
A0 = 5.0
MAX_WALL = 80.0
TYP = EXAMPLES / "typologies"
_FIDELITY_TOL_MM = 0.2


def _meridian(t: str, knobs: dict, L: float) -> P.Meridian:
    return registry.build_meridian(
        {"type": t}, {"L_mm": L, **knobs}, "h", r0=R0, a0=A0, L=L,
        max_wall=MAX_WALL, phi=0.0)


def _hypex(length: float = 190.0) -> P.Meridian:
    return _meridian("hypex", {"h_rm_mm": 140.0, "h_T": 0.7}, length)


# ---------------------------------------------------------------------------
# P1: default 0 is today's exact profile
# ---------------------------------------------------------------------------

@requires_mesher
def test_default_zero_is_bit_for_bit_todays_profile():
    cfg = load_config(TYP / "hypex.yaml")
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace)
    assert cfg.generator is not None and cfg.brief is not None
    knobs_with_zero = {**space.seed_knobs, "h_throat_blend_mm": 0.0}
    params_zero = registry.materialize(cfg.generator, knobs_with_zero, cfg.brief)
    params_absent = space.seed.params
    assert params_zero == params_absent                 # the blend block is never entered
    for plane in ("profileH", "profileV"):
        z = np.asarray(params_zero[plane]["points"], dtype=float)
        a = np.asarray(params_absent[plane]["points"], dtype=float)
        np.testing.assert_allclose(z, a, rtol=0.0, atol=1e-12)


# ---------------------------------------------------------------------------
# P2: throat untouched, classical continues beyond L_b
# ---------------------------------------------------------------------------

@requires_mesher
@pytest.mark.parametrize("L_b", [8.0, 30.0, 100.0])
def test_throat_and_far_field_endpoints(L_b):
    classical = _hypex()
    blended = registry.build_meridian(
        {"type": "hypex"},
        {"L_mm": 190.0, "h_rm_mm": 140.0, "h_T": 0.7, "h_throat_blend_mm": L_b},
        "h", r0=R0, a0=A0, L=190.0, max_wall=MAX_WALL, phi=0.0)
    # P2: r(0) = r_OS(0) = the driver exit radius; throat angle = driver exit angle.
    assert blended.r_mm[0] == pytest.approx(classical.r_mm[0])
    assert blended.r_mm[0] == pytest.approx(R0)
    assert blended.theta_deg[0] == pytest.approx(A0, abs=1e-9)
    # The classical profile is copied unchanged past L_b (byte-identical arrays).
    outside = blended.z_mm > L_b
    assert outside.any()
    np.testing.assert_array_equal(blended.r_mm[outside], classical.r_mm[outside])
    np.testing.assert_array_equal(blended.theta_deg[outside], classical.theta_deg[outside])
    # At L_b the blend lands exactly on the classical radius and angle.
    i = int(np.argmin(np.abs(blended.z_mm - L_b)))
    assert blended.r_mm[i] == pytest.approx(float(np.interp(blended.z_mm[i], classical.z_mm,
                                                            classical.r_mm)), abs=1e-9)
    assert blended.theta_deg[i] == pytest.approx(
        float(np.interp(blended.z_mm[i], classical.z_mm, classical.theta_deg)), abs=1e-6)
    assert np.all(np.diff(blended.z_mm) > 0)
    assert np.all(blended.r_mm > 0)


# ---------------------------------------------------------------------------
# P3: smoothstep w is C1 at both ends
# ---------------------------------------------------------------------------

def test_smoothstep_has_zero_derivative_at_both_ends():
    t = np.linspace(0.0, 1.0, 2001)
    w = 3.0 * t**2 - 2.0 * t**3
    dw = 6.0 * t - 6.0 * t**2
    assert w[0] == pytest.approx(0.0) and w[-1] == pytest.approx(1.0)
    assert dw[0] == pytest.approx(0.0, abs=1e-12)
    assert dw[-1] == pytest.approx(0.0, abs=1e-12)


@requires_mesher
def test_blended_wall_angle_is_continuous_at_L_b():
    L_b = 30.0
    classical = _hypex()
    blended = registry.build_meridian(
        {"type": "hypex"},
        {"L_mm": 190.0, "h_rm_mm": 140.0, "h_T": 0.7, "h_throat_blend_mm": L_b},
        "h", r0=R0, a0=A0, L=190.0, max_wall=MAX_WALL, phi=0.0)
    # Analytic angle at L_b equals the classical angle there (no kink).
    i = int(np.argmin(np.abs(blended.z_mm - L_b)))
    assert blended.theta_deg[i] == pytest.approx(
        float(np.interp(blended.z_mm[i], classical.z_mm, classical.theta_deg)), abs=1e-6)
    # Numerically: the one-sided slopes at L_b agree within the FD resolution.
    z, r = blended.z_mm, blended.r_mm
    j = np.searchsorted(z, L_b)
    left = (r[j] - r[j - 2]) / (z[j] - z[j - 2])
    right = (r[j + 2] - r[j]) / (z[j + 2] - z[j])
    assert abs(np.degrees(np.arctan(right)) - np.degrees(np.arctan(left))) < 0.2


# ---------------------------------------------------------------------------
# Hermite fidelity (existing generator style, V2)
# ---------------------------------------------------------------------------

@requires_mesher
@pytest.mark.parametrize("L_b", [0.0, 8.0, 30.0])
def test_blended_hermite_fidelity(L_b):
    m = _meridian("hypex", {"h_rm_mm": 140.0, "h_T": 0.7, "h_throat_blend_mm": L_b}, 190.0)
    anc = P.select_anchors(m, 16)
    r_ref = P.hermite_reference(anc, m.z_mm)
    assert np.abs(r_ref - m.r_mm).max() <= _FIDELITY_TOL_MM


# ---------------------------------------------------------------------------
# All four supported typologies
# ---------------------------------------------------------------------------

@requires_mesher
@pytest.mark.parametrize("t,knobs", [
    ("conical", {"h_rm_mm": 120.0}),
    ("exponential", {"h_rm_mm": 120.0}),
    ("hypex", {"h_rm_mm": 120.0, "h_T": 0.7}),
    ("tractrix", {"h_fc_hz": 700.0}),
])
def test_blend_supported_for_the_four_classical_types(t, knobs):
    m = _meridian(t, {**knobs, "h_throat_blend_mm": 10.0}, 150.0)
    assert m.r_mm[0] == pytest.approx(R0)
    assert m.theta_deg[0] == pytest.approx(A0, abs=1e-9)
    outside = m.z_mm > 10.0
    assert m.r_mm[outside].size > 0
    assert np.all(np.abs(m.theta_deg) < 90.0)


# ---------------------------------------------------------------------------
# Refusals: GeneratorError, never a clamped profile
# ---------------------------------------------------------------------------

@requires_mesher
def test_blend_longer_than_the_meridian_is_a_generator_error():
    with pytest.raises(registry.GeneratorError, match="throat_blend_mm"):
        registry.build_meridian(
            {"type": "hypex"},
            {"L_mm": 190.0, "h_rm_mm": 140.0, "h_T": 0.7, "h_throat_blend_mm": 250.0},
            "h", r0=R0, a0=A0, L=190.0, max_wall=MAX_WALL, phi=0.0)


@requires_mesher
def test_example_config_seed_and_provenance():
    cfg = load_config(TYP / "throatblend_hypex.yaml")
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace) and space.family == "FREEFORM"
    assert set(space.keys()) == {"L_mm", "h_rm_mm", "h_T", "h_throat_blend_mm"}
    assert cfg.bounds_raw["h_throat_blend_mm"]["lo"] == 0.0
    assert cfg.bounds_raw["h_throat_blend_mm"]["hi"] == 30.0
    assert space.seed_knobs["h_throat_blend_mm"] == 8.0
    pH = space.seed.params["profileH"]["points"]
    assert pH[0][1] == pytest.approx(R0)
    assert space.seed.params["profileV"] == space.seed.params["profileH"]
    prov = space.provenance(space.seed)
    assert prov is not None and prov["derived"]["h"]["throat_blend_mm"] == 8.0
    json.dumps(prov)
    json.dumps(space.seed.params)


@requires_mesher
def test_envelope_short_blend_does_not_touch_the_zero_default():
    """A blended seed is legal and distinct; the zero-knob seed is the stored baseline."""
    cfg = load_config(TYP / "hypex.yaml")
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace)
    assert cfg.generator is not None and cfg.brief is not None
    blended = registry.materialize(
        cfg.generator, {**space.seed_knobs, "h_throat_blend_mm": 8.0}, cfg.brief)
    assert blended != space.seed.params
    assert GENERATOR_ERROR_KEY not in blended
