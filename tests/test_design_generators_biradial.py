"""Biradial (Keele/JBL US4308932A) generator tests (2026-10-25 C1). Offline, pure laws.

The reference-case scalars are the biradial dossier's 4.3 measured numbers (the
implementation reproduces them exactly); the H-plane inward-turn case is the dossier's
own documented failure mode and must be REFUSED, never shipped (dossier 4.4 item 5).
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


def test_keele_sizing_rule_reproduces_the_published_example():
    """Dossier 4.3 [measured]: W = K/(A*F) with the patent's own ~25,000 constant."""
    assert P.biradial_mouth_mm(80.0, 400.0) == pytest.approx(781.25, abs=0.5)
    assert P.biradial_mouth_mm(36.0, 400.0) == pytest.approx(1736.11, abs=0.5)
    # the repo's settled Hughes constant (KEELE_K 25,400) sits 1.6% from the patent's
    # ~25,000: both are published numbers, quoted here so neither is silently swapped.
    from hornlab_search.constants import KEELE_K
    assert P.biradial_mouth_mm(80.0, 400.0) == pytest.approx(25_000.0 / (80.0 * 400.0) * 1000.0)
    assert KEELE_K / (80.0 * 400.0) * 1000.0 == pytest.approx(793.75, abs=0.5)


def test_reference_v_plane_march_matches_the_dossier_numbers():
    """Dossier 4.3 [measured]: r0 24.4, a 18 deg, n 4, L 815.1, rm 390 ->
    c = 2.28e-10, r(516) = 208.2 mm, end slope 0.819 (wall 39.3 deg)."""
    m = P.biradial_contour(24.4, 390.0, 815.1, 18.0, 4.0)
    assert m.info["c_mm_per_mm_n"] == pytest.approx(2.2847e-10, rel=2e-3)
    assert float(np.interp(516.0, m.z_mm, m.r_mm)) == pytest.approx(208.2, abs=0.5)
    assert m.theta_deg[-1] == pytest.approx(np.degrees(np.arctan(0.8192)), abs=0.2)
    assert np.all(np.diff(m.r_mm) > 0)
    assert np.all(m.theta_deg < 90.0)
    assert m.r_mm[0] == pytest.approx(24.4)


def test_documented_h_plane_failure_mode_is_refused_not_shipped():
    """Dossier 4.3/4.4-5 [measured]: the naive axial H-pair march (a=40, n=5.5) cannot
    close on the 390 mm mouth (tan(40 deg) alone overshoots: 24.4 + 0.8391*815.1 = 708 mm
    > 390, so c < 0) and the wall turns inward (measured end slope -1.309); the law
    REFUSES it - shipping it under the published name would be exactly the mislabeling
    the R9 gate forbids. The rm-close refusal fires first here; the end-slope guard is
    the same class of refusal for the marginal cases."""
    with pytest.raises(registry.GeneratorError, match="cannot close"):
        P.biradial_contour(24.4, 390.0, 815.1, 40.0, 5.5)
    # (the rm-closing check is the first and tightest guard; the end-slope refusal behind
    # it only nets floating-point roundoff cases, so the test pins the guard that fires.)


@pytest.mark.parametrize("bad_n", [1.0, 9.0])
def test_flare_exponent_is_within_claim_14_range(bad_n):
    with pytest.raises(ValueError, match="claim 14"):
        P.biradial_contour(12.7, 150.0, 190.0, 20.0, bad_n)


def test_new_types_and_defaults_are_registered():
    assert "biradial" in registry.TYPES and "qtw_waveguide" in registry.TYPES
    assert registry.DEFAULT_KNOBS["R_arc_mm"] == 45.0


def test_config_materializes_and_is_envelope_true():
    """The seed is the K-law-aimed 90x60 biradial at the 1-inch envelope's limit."""
    cfg = load_config(TYP / "biradial_keele.yaml")
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace)
    families.validate(space.seed)
    json.dumps(space.seed.params)
    json.dumps(space.provenance(space.seed))
    assert registry.envelope_overshoot_estimate(space.seed.params, cfg.brief) == 0.0
    info = registry.info(cfg.raw["generator"], cfg.raw["seed_params"], cfg.brief)
    assert "h" in info and "v" in info
    assert info["h"]["type"] == "biradial" and info["v"]["type"] == "biradial"
    assert info["h"]["c_mm_per_mm_n"] >= 0.0 and info["v"]["c_mm_per_mm_n"] >= 0.0
    assert float(info["h"]["end_wall_deg"]) < 90.0
    print(f"\nbiradial seed: h c={info['h']['c_mm_per_mm_n']:.4g} end={info['h']['end_wall_deg']:.2f} "
          f"deg | v c={info['v']['c_mm_per_mm_n']:.4g} end={info['v']['end_wall_deg']:.2f} deg; "
          f"mouth W {2 * info['h']['mouth_radius_mm']:.1f} x H {2 * info['v']['mouth_radius_mm']:.1f} mm")


def test_config_mouth_hits_the_envelope_limit_like_the_seed_note_says():
    cfg = load_config(TYP / "biradial_keele.yaml")
    space = DesignSpace.from_config(cfg)
    anchors = space.seed.params  # envelope check happens in materialize; here assert the seed
    w_mm = 2.0 * max(float(row[1]) for row in anchors["profileH"]["points"]) + 6.0
    h_mm = 2.0 * max(float(row[1]) for row in anchors["profileV"]["points"]) + 6.0
    assert w_mm == pytest.approx(396.0, abs=1.0)     # 2*(195+3), inside the 400 mm envelope
    assert h_mm == pytest.approx(296.0, abs=1.0)     # 2*(145+3), inside the 300 mm envelope