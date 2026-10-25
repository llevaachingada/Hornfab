"""Quadratic-Throat Waveguide (Hughes/Peavey white paper) generator tests. Offline, pure laws.

The published arc rule (sweep dossier 3.4 S4, read from the white paper): the throat arc
starts with the wall PARALLEL to the axis, turns exactly a_deg (half the dispersion
angle), meets the straight bell tangentially (C1), and the bell runs at the same wall
angle to the mouth - so rm is derived, not searched.
"""
import json

import numpy as np
import pytest

from conftest import EXAMPLES
from hornlab_search.config import load_config
from hornlab_search.design import families
from hornlab_search.design.generated import GeneratedSpace
from hornlab_search.design.generators import profiles as P
from hornlab_search.design.generators import registry
from hornlab_search.design.space import DesignSpace

TYP = EXAMPLES / "typologies"


def test_throat_arc_matches_the_published_rule():
    m = P.qtw_waveguide(12.7, 190.0, 45.0, 45.0)
    # step 3: the wall is parallel to the axis at the throat perimeter
    assert m.theta_deg[0] == pytest.approx(0.0, abs=1e-9)
    # the arc's included angle == half the dispersion angle (a_deg): the turn ends at z* = R sin(a)
    z_star = 45.0 * np.sin(np.radians(45.0))
    assert m.info["z_arc_end_mm"] == pytest.approx(z_star, rel=1e-9)
    assert float(np.interp(z_star, m.z_mm, m.theta_deg)) == pytest.approx(45.0, abs=0.05)
    # C1 at the arc/bell joint: the arc's last sample IS z* (theta == a_deg exactly) and
    # the bell's first sample is the same angle - the sampled joint step is zero. (The
    # ANALYTIC curve is smooth; sampled arc angles near the joint move ~1.8 deg per
    # 0.5 mm sample by asin(z/R) alone, so value windows would falsely read a kink.)
    i = int(np.argmin(np.abs(m.z_mm - z_star)))
    assert m.theta_deg[i] == pytest.approx(45.0, abs=1e-6)
    assert m.theta_deg[i + 1] == pytest.approx(45.0, abs=1e-6)
    assert abs(m.theta_deg[i + 1] - m.theta_deg[i]) < 1e-9        # the joint step == 0 (C1)
    # and the arc-side tangent recovers the bell's slope to sub-degree in a fitted window
    j0 = i - 3
    coef = np.polyfit(m.z_mm[j0:i + 1], m.r_mm[j0:i + 1], 2)
    tail_slope_deg = float(np.degrees(np.arctan(np.polyval(np.polyder(coef), z_star))))
    assert tail_slope_deg == pytest.approx(45.0, abs=0.2)
    # the bell is straight at the same wall angle; rm is DERIVED from (L, a, R)
    r_star = 12.7 + 45.0 * (1.0 - np.cos(np.radians(45.0)))
    assert m.r_mm[-1] == pytest.approx(r_star + (190.0 - z_star) * np.tan(np.radians(45.0)), abs=0.05)
    assert np.all(np.diff(m.r_mm) > 0) and np.all(m.theta_deg < 90.0)


def test_v_plane_seed_value():
    m = P.qtw_waveguide(12.7, 190.0, 30.0, 45.0)
    r_star = 12.7 + 45.0 * (1.0 - np.cos(np.radians(30.0)))
    z_star = 45.0 * np.sin(np.radians(30.0))
    expected = r_star + (190.0 - z_star) * np.tan(np.radians(30.0))
    assert m.r_mm[-1] == pytest.approx(expected, abs=0.05)
    assert m.r_mm[-1] == pytest.approx(115.46, abs=0.2)   # the config seed's V mouth radius


@pytest.mark.parametrize("R, a, L", [(0.0, 45.0, 190.0), (45.0, 90.0, 190.0),
                                     (45.0, -1.0, 190.0)])
def test_bad_geometry_is_refused(R, a, L):
    if a >= 90.0 or a <= 0.0 or R <= 0.0:
        with pytest.raises(ValueError):
            P.qtw_waveguide(12.7, L, a, R)
    # L shorter than the arc: the bell has no room -> GeneratorError
    with pytest.raises(registry.GeneratorError, match="no length"):
        P.qtw_waveguide(12.7, 30.0, 45.0, 45.0)


def test_config_materializes_and_is_envelope_true():
    cfg = load_config(TYP / "qtw_waveguide.yaml")
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace)
    families.validate(space.seed)
    json.dumps(space.seed.params)
    json.dumps(space.provenance(space.seed))
    assert registry.envelope_overshoot_estimate(space.seed.params, cfg.brief) == 0.0
    info = registry.info(cfg.raw["generator"], cfg.raw["seed_params"], cfg.brief)
    assert "h" in info and "v" in info
    assert info["h"]["type"] == "qtw_waveguide"
    # the derived mouth radii match the hand calculation in the config's seed note
    assert info["h"]["mouth_radius_mm"] == pytest.approx(184.06, abs=0.2)
    assert info["v"]["mouth_radius_mm"] == pytest.approx(115.46, abs=0.2)
    print(f"\nqtw seed: H mouth {2 * info['h']['mouth_radius_mm']:.1f} mm "
          f"(V {2 * info['v']['mouth_radius_mm']:.1f} mm), depth {info['h']['length_mm']:.1f} mm")