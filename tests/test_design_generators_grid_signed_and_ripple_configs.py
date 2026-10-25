"""S1a config-gap coverage (2026-10-25): the two shipped-but-never-loaded grid-row configs.

``salmon_x_signed.yaml`` is the signed x_amp SIGN demo and ``salmon_ripple12.yaml`` the
even-lobe mouth ripple (12 lobes / 3 mm / window 0.8, half model, quadrants '14'). It
applies the REAL ``load_config`` path with the named brief resolving, the pure-Python
rows march at the seed (no mesher, no GPU), and the pinned envelope/span/penalty truth --
following tests/test_design_generators_biradial.py conventions.

S1a RESEED (2026-10-25, owner-directed driver pass; the smoke-matrix findings): the
shipped x_signed seed (stop 170 / x_amp -0.25) was NOT buildable - the cardinal rows
crossed the 180 deg cap-area asymptote (z-span 332.47 mm vs the 275 limit, overshoot
0.2201, mesh 14,414 tris > 11,275) - and the shipped ripple seed exceeded the 5,000-dof
screen cap (5,358 dofs). Both are reseeded (stop 150; x_amp -0.15) and the own brief now
carries f0 1900 + objective v3, so the loaded seeds are the DERIVED ones (fc 1200/843.5).
The tests below pin the reseeded truth; the old values are kept in the docstrings as the
dated record. The organic brief revision also derives the fc knobs at load, so knob
assertions that the derivation owns (fc) are not pinned here - shape knobs are.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from conftest import EXAMPLES
from hornlab_search.config import load_config
from hornlab_search.design import families
from hornlab_search.design.generated import GeneratedSpace
from hornlab_search.design.generators import grid as G
from hornlab_search.design.generators import registry
from hornlab_search.design.space import DesignSpace

TYP = EXAMPLES / "typologies"
CONFIGS = ("salmon_x_signed", "salmon_ripple12")
BRIEF_FILE = "../briefs/organic_rollback_1in.yaml"
BRIEF_NAME = "organic_rollback_1in"


def _march(block, brief):
    """The pure-Python design march the mesher consumes (no mesher, no GPU)."""
    return G.rows_grid_points(
        {k: v for k, v in block.items() if k != "knobs"}, block["knobs"], brief)


@pytest.fixture(scope="module")
def x_signed():
    """One materialization shared by the SIGN-demo tests (the seed march is not free)."""
    cfg = load_config(TYP / "salmon_x_signed.yaml")
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace)
    return cfg, space


@pytest.fixture(scope="module")
def ripple12():
    cfg = load_config(TYP / "salmon_ripple12.yaml")
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace)
    return cfg, space


# ---------------------------------------------------------------- config + brief load

@pytest.mark.parametrize("name", CONFIGS)
def test_config_loads_and_its_named_brief_file_resolves(name):
    cfg = load_config(TYP / f"{name}.yaml")
    assert cfg.name == name
    assert cfg.family == "FREEFORM"
    # the REAL load path resolved the relative brief_file against the config's directory
    assert cfg.raw["brief_file"] == BRIEF_FILE
    brief = cfg.brief
    assert brief is not None
    assert brief["name"] == BRIEF_NAME
    resolved = Path(brief["path"])
    assert resolved.is_file()
    assert resolved.resolve() == (EXAMPLES / "briefs" / "organic_rollback_1in.yaml").resolve()
    generator = cfg.generator
    assert generator is not None
    assert generator["name"] == "grid"
    assert generator["rows"] == {"type": "salmon_elliptical"}


# ------------------------------------------------- signed x_amp (the SIGN demo)

def test_x_signed_seed_march_succeeds_as_a_signed_quarter_model(x_signed):
    cfg, space = x_signed
    families.validate(space.seed)
    json.dumps(space.seed.params)
    json.dumps(space.provenance(space.seed))

    block = space.seed.params["grid"]
    G.validate_grid_params(block)
    assert block["n_phi"] == 15 and block["n_s"] == 32
    assert "span" not in block                  # the quarter recipe carries no span key
    assert cfg.mesh.quadrants == "1"

    # the SIGN demo: a NEGATIVE seed knob inside its own signed bounds (S1a reseed: -0.15;
    # -0.25 at stop 150 meshes defectively - non-sliver triangles in the x=0 plane)
    assert cfg.seed_params["g_x_amp"] == pytest.approx(-0.15)
    assert cfg.seed_params["g_stop_deg"] == pytest.approx(150.0)
    assert cfg.bounds_raw["g_x_amp"] == {"lo": -0.4, "hi": 0.4}
    x_amp = block["knobs"]["g_x_amp"]
    assert -0.4 <= x_amp <= 0.4
    assert x_amp < 0.0
    assert block["knobs"]["g_x_fc"] == pytest.approx(0.15)

    inner, meta = _march(block, cfg.brief)
    assert inner.shape == (15, 33, 3) and np.isfinite(inner).all()
    assert meta["span"] == "quarter" and meta["row_span"] == "quarter"
    assert meta["quadrants"] == "1" and meta["quarter"] is True
    assert meta["x_amp"] == pytest.approx(-0.15)
    assert meta["x_fc"] == pytest.approx(0.15)
    assert meta["ripple_lobes"] == 0            # no ripple on this config
    # S1a reseed: the mouth AND the depth now fit the brief (the shipped seed's z-span
    # 332.47 mm exceeded the 260 mm envelope; the reseeded/derived seed fits)
    env = space.brief["envelope"]
    assert meta["mouth_w_mm"] < env["max_mouth_w_mm"]
    assert meta["mouth_h_mm"] < env["max_mouth_h_mm"]
    assert meta["x_span_mm"] < env["max_depth_mm"]


def test_x_signed_seed_is_envelope_true_after_the_s1a_reseed(x_signed):
    """S1a reseed record: the shipped seed (stop 170 / x_amp -0.25) overshot 0.2201
    (z-span 335.52 mm vs the 275 mm limit; smoke-matrix run 20261025T182430Z). The
    reseeded seed (stop 150 / -0.15, derived fc 1200/843.5 under the f0-1900 brief) is
    envelope-true; this pins the repaired truth."""
    _cfg, space = x_signed
    assert registry.envelope_overshoot_estimate(space.seed.params, space.brief) == 0.0


# ------------------------------------------------ even-lobe mouth ripple (pleats)

def test_ripple12_seed_march_is_a_half_model_with_the_four_samples_per_lobe_bar(ripple12):
    cfg, space = ripple12
    families.validate(space.seed)
    json.dumps(space.seed.params)
    json.dumps(space.provenance(space.seed))
    assert set(space.keys()) == {"g_T", "g_fc_h_hz", "g_fc_v_hz", "g_ripple_amp_mm",
                                 "g_ripple_lobes", "g_ripple_start", "g_stop_deg"}

    block = space.seed.params["grid"]
    G.validate_grid_params(block)
    assert block["span"] == "half" and block["n_phi"] == 25
    assert cfg.seed_params["g_stop_deg"] == pytest.approx(150.0)   # S1a reseed (was 170:
    # 5,358 dofs > the 5,000 cap; at 150: 2,852 seed / 2,567 derived, measured)
    assert cfg.mesh.quadrants == "14"

    lobes = block["knobs"]["g_ripple_lobes"]
    assert block["knobs"]["g_ripple_amp_mm"] == pytest.approx(3.0)
    assert block["knobs"]["g_ripple_start"] == pytest.approx(0.8)
    assert cfg.bounds_raw["g_ripple_lobes"] == {"lo": 6.0, "hi": 24.0}
    assert 6.0 <= lobes <= 24.0 and int(lobes) == lobes and int(lobes) % 2 == 0

    # The honest-resolution bar the full-ring tests enforce: >= 4 phi samples per lobe
    # period on the row span.  span half = pi over n_phi 25 -> d_phi = pi/24; 12 lobes ->
    # (2 pi / 12) / (pi / 24) = exactly 4.0.  The guard passes at 12 and refuses 24.
    span_rad = math.pi
    per_period = (2.0 * math.pi / lobes) / (span_rad / (block["n_phi"] - 1))
    assert G.ROWS_RIPPLE_SAMPLES_PER_LOBE == pytest.approx(4.0)
    assert per_period == pytest.approx(
        G.ROWS_RIPPLE_SAMPLES_PER_LOBE, rel=0.0, abs=1e-12)
    G._rows_ripple_resolution_guard(int(lobes), span_rad, block["n_phi"])
    with pytest.raises(registry.GeneratorError, match="samples per lobe"):
        G._rows_ripple_resolution_guard(24, span_rad, block["n_phi"])

    inner, meta = _march(block, cfg.brief)
    assert inner.shape == (25, 33, 3) and np.isfinite(inner).all()
    assert meta["span"] == "half" and meta["row_span"] == "half"
    assert meta["half_model"] is True
    assert meta["quadrants"] == "14" and meta["symmetry_plane"] == "yz"
    assert meta["ripple_lobes"] == 12
    assert meta["ripple_amp_mm"] == pytest.approx(3.0)
    assert meta["ripple_start"] == pytest.approx(0.8)
    assert "ripple_law" in meta


def test_ripple12_seed_is_envelope_true(ripple12):
    """The sibling envelope fact: the ripple seed materializes inside the brief envelope.

    The pre-mesh estimate includes the shell and the outer radius field, so this single
    assertion covers all three dimensions (the sibling config tests' ``== 0.0`` shape).
    """
    _cfg, space = ripple12
    assert registry.envelope_overshoot_estimate(space.seed.params, space.brief) == 0.0


# ------------------------------------------------------------- graded penalty

@pytest.mark.parametrize("name", CONFIGS)
def test_configs_record_the_graded_infeasible_penalty(name):
    cfg = load_config(TYP / f"{name}.yaml")
    assert cfg.raw["search"]["infeasible_penalty"] == "graded"
    assert cfg.search.infeasible_penalty == "graded"
