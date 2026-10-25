"""WP9 G4 spherical_salmon march (Report 2 section 3; dossier section 2.3). Offline.

Ship bar
--------
P1 the Salmon area law is satisfied at EVERY march step (relative error < 1e-6).
P2 z is strictly increasing.
P3 theta is monotone non-decreasing.
P4 plane-wave limit: the cap area -> pi r^2 as theta -> 0 (loose 1e-3), and a small-angle
   march starts plane-wave-like.
P5 refusals raise GeneratorError instead of clamping (bad knobs, a bracket that cannot
   keep theta non-decreasing, a non-monotone/self-approaching step).
Plus T=1 closed-form sanity, knob determinism, the L_mm-shortens-only contract, and the
Le Cleac'h/spherical_wave are live (verified Fourcade construction, R9-J).
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from conftest import EXAMPLES
from hornlab_search.config import load_config
from hornlab_search.design import families
from hornlab_search.design.generated import GENERATOR_ERROR_KEY, GeneratedSpace
from hornlab_search.design.generators import profiles as P
from hornlab_search.design.generators import registry
from hornlab_search.design.space import DesignSpace

R0 = 12.7
A0 = 5.0
TYP = EXAMPLES / "typologies"
_FIDELITY_TOL_MM = 0.2


def _march(fc=800.0, T=0.8, th0=A0, maxw=80.0):
    return P._salmon_march(R0, fc, T, th0, maxw, 0.25)


def _meridian(**knobs) -> P.Meridian:
    base = {"L_mm": 220.0, "h_fc_hz": 800.0, "h_T": 0.8, "h_max_wall_deg": 80.0}
    allk = {**base, **knobs}
    return registry.build_meridian({"type": "spherical_salmon"}, allk, "h",
                                   r0=R0, a0=A0, L=allk["L_mm"], max_wall=88.0, phi=0.0)


# ---------------------------------------------------------------------------
# P1: area law at every step
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fc,T,th0", [(800.0, 0.8, 5.0), (600.0, 0.8, 5.0),
                                      (1000.0, 0.5, 5.0), (800.0, 1.0, 5.0)])
def test_area_law_at_every_march_step(fc, T, th0):
    z, r, th, s, A0, x0 = _march(fc=fc, T=T, th0=th0)
    cap = 2.0 * np.pi * (r / np.sin(th)) ** 2 * (1.0 - np.cos(th))
    law = A0 * (np.cosh(s / x0) + T * np.sinh(s / x0)) ** 2
    rel = np.abs(cap - law) / law
    assert rel.max() < 1e-6, f"area law rel error {rel.max():.3e} at fc={fc} T={T}"


# ---------------------------------------------------------------------------
# P2/P3: monotone z and theta
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fc,T", [(800.0, 0.8), (600.0, 0.8), (1200.0, 0.5)])
def test_z_strictly_increasing_and_theta_monotone(fc, T):
    z, r, th, s, _A0, _x0 = _march(fc=fc, T=T)
    assert np.all(np.diff(z) > 0), "z is not strictly increasing"
    assert np.all(np.diff(th) >= -1e-12), "theta is not monotone non-decreasing"
    assert np.all(r > 0) and np.all(th < np.radians(90.0))
    assert th[-1] == pytest.approx(np.radians(80.0), abs=1e-9)


# ---------------------------------------------------------------------------
# P4: plane-wave limit
# ---------------------------------------------------------------------------

def test_cap_area_tends_to_plane_wave_pi_r_squared():
    r = R0
    for theta_deg in (1e-4, 1e-3, 0.01, 0.1, 0.5):
        th = np.radians(theta_deg)
        cap = 2.0 * np.pi * (r / np.sin(th)) ** 2 * (1.0 - np.cos(th))
        assert abs(cap / (np.pi * r**2) - 1.0) < 1e-3


def test_small_angle_march_starts_plane_wave_like():
    z, r, th, s, _A0, _x0 = _march(fc=300.0, T=1.0, th0=0.5)
    cap = 2.0 * np.pi * (r / np.sin(th)) ** 2 * (1.0 - np.cos(th))
    plane = np.pi * r**2
    early = th < np.radians(2.0)
    assert early.any()
    rel = np.abs(cap[early] / plane[early] - 1.0).max()
    assert rel < 1e-3
    assert np.all(np.diff(z) > 0)


# ---------------------------------------------------------------------------
# P5: refusals raise GeneratorError, never clamp
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("knobs,reason", [
    ({"h_T": -0.1}, "T must be >= 0"),
    ({"h_max_wall_deg": 90.0}, "max_wall_deg < 90"),
    ({"h_max_wall_deg": 4.0}, "theta0_deg < max_wall_deg"),      # below the brief's 5 deg exit
    ({"h_fc_hz": 300.0}, "area law grows slower"),               # bracket cannot stay monotone
])
def test_refusals_raise_generator_error(knobs, reason):
    with pytest.raises(registry.GeneratorError, match=reason):
        _meridian(**knobs)


def test_bad_fc_is_a_generator_error():
    with pytest.raises(registry.GeneratorError, match="fc_hz must be > 0"):
        _meridian(h_fc_hz=-1.0)


# ---------------------------------------------------------------------------
# T = 1 closed form, determinism, L_mm shortens only
# ---------------------------------------------------------------------------

def test_t1_matches_the_exponential_closed_form():
    T = 1.0
    z, r, th, s, A0, x0 = _march(fc=800.0, T=T)
    cap = 2.0 * np.pi * (r / np.sin(th)) ** 2 * (1.0 - np.cos(th))
    closed = A0 * np.exp(2.0 * s / x0)          # cosh+sinh == exp for T = 1
    np.testing.assert_allclose(cap, closed, rtol=1e-12, atol=0.0)


def test_knob_determinism():
    a = _meridian()
    b = _meridian()
    np.testing.assert_array_equal(a.z_mm, b.z_mm)
    np.testing.assert_array_equal(a.r_mm, b.r_mm)
    np.testing.assert_array_equal(a.theta_deg, b.theta_deg)
    assert a.info == b.info


def test_l_mm_may_only_shorten_the_march():
    intrinsic = _meridian()                       # L_mm 220 > march length
    assert intrinsic.length_mm == pytest.approx(128.59522101765026, abs=1e-9)
    short = _meridian(L_mm=100.0)
    assert short.length_mm == pytest.approx(100.0)
    assert short.info["truncated_to_mm"] == pytest.approx(100.0)
    # The truncated piece is the same geometry up to z = 100.
    np.testing.assert_allclose(
        np.interp(short.z_mm, intrinsic.z_mm, intrinsic.r_mm), short.r_mm, rtol=1e-12, atol=1e-10)


# ---------------------------------------------------------------------------
# Hermite fidelity and R9 gate
# ---------------------------------------------------------------------------

def test_hermite_fidelity_through_16_anchors():
    m = registry._truncate(_meridian(), 128.0)
    anc = P.select_anchors(m, 16)
    r_ref = P.hermite_reference(anc, m.z_mm)
    assert np.abs(r_ref - m.r_mm).max() <= _FIDELITY_TOL_MM


def test_lecleach_and_spherical_wave_are_live():
    # R9-J (2026-10-25): the verified Fourcade construction replaced the gated stub.
    lc = P.lecleach(R0, 800.0, 0.7, 80.0, phi0_deg=A0)
    assert lc.r_mm[0] == pytest.approx(R0) and lc.name == "lecleach"
    sw = P.spherical_wave(R0, 800.0, 80.0, phi0_deg=A0)
    assert sw.info["T"] == 1.0


# ---------------------------------------------------------------------------
# Registry, config, provenance
# ---------------------------------------------------------------------------

def test_example_config_seed_and_provenance():
    cfg = load_config(TYP / "spherical_salmon.yaml")
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace) and space.family == "FREEFORM"
    assert set(space.keys()) == {"h_fc_hz", "h_T", "h_max_wall_deg"}
    assert cfg.bounds_raw["h_fc_hz"] == {"lo": 600.0, "hi": 1200.0}
    assert cfg.bounds_raw["h_T"] == {"lo": 0.3, "hi": 1.0}
    assert cfg.bounds_raw["h_max_wall_deg"] == {"lo": 60.0, "hi": 88.0}
    families.validate(space.seed)
    pH = space.seed.params["profileH"]["points"]
    assert pH[0][0] == 0.0 and pH[0][1] == pytest.approx(R0)
    assert space.seed.params["profileV"] == space.seed.params["profileH"]
    assert max(row[1] for row in pH) * 2.0 < 360.0        # mouth inside the brief envelope
    assert pH[-1][0] < 220.0                              # depth inside the brief envelope
    prov = space.provenance(space.seed)
    assert prov is not None
    assert prov["spec"]["profile_h"] == {"type": "spherical_salmon"}
    assert prov["derived"]["h"]["stop_deg"] == pytest.approx(80.0)
    json.dumps(prov)
    json.dumps(space.seed.params)


def test_infeasible_knob_is_graded_not_raised_by_the_space():
    cfg = load_config(TYP / "spherical_salmon.yaml")
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace)
    d = space.design_from_knobs({**space.seed_knobs, "h_fc_hz": 300.0, "h_T": 0.8})
    assert GENERATOR_ERROR_KEY in d.params
    assert "spherical_salmon" in d.params[GENERATOR_ERROR_KEY]
