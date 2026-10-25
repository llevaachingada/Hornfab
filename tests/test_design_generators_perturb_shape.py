"""WP3: shape-only generator perturbation + the registry ``perturb: {mode: ...}`` switch.

Offline (no mesher, no GPU). The legacy-vs-absent check reuses the real
``examples/typologies/perturbed_tractrix.yaml`` spec that ``test_design_generated.py`` covers,
loaded directly with PyYAML so it exercises the generator layer only.
"""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.design.generators import registry
from hornlab_search.design.generators.profiles import (
    exponential,
    perturb_increments,
    perturb_increments_shape,
    select_anchors,
)

R0, RM, L = 12.7, 150.0, 200.0      # mm, same seeds as test_design_generators_profiles.py


def _base_anchors(n: int = 12):
    return select_anchors(exponential(R0, RM, L), n)


def _typo_and_brief(name: str = "perturbed_tractrix"):
    """(generator block, brief, knobs) for a real typology fixture, with nonzero u knobs."""
    typo_path = EXAMPLES / "typologies" / f"{name}.yaml"
    raw = yaml.safe_load(typo_path.read_text())
    brief_path = (typo_path.parent / raw["brief_file"]).resolve()
    brief = yaml.safe_load(brief_path.read_text())
    brief["name"] = brief.get("name", brief_path.stem)
    knobs = {k: float(v) for k, v in raw["seed_params"].items()}
    # n_anchors=8 -> u0..u6; make the perturbation path run
    knobs.update({"h_u0": 0.2, "h_u3": -0.15, "h_u6": 0.1})
    return raw["generator"], brief, knobs


# ---------------------------------------------------------------------------
# perturb_increments_shape
# ---------------------------------------------------------------------------


class TestShapePerturbation:
    @pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
    def test_mouth_radius_is_preserved(self, seed):
        """Sum of increments (the mouth radius) is unchanged to 1e-9."""
        anc = _base_anchors()
        r_base = np.array([a[1] for a in anc])
        rng = np.random.default_rng(seed)
        u = rng.uniform(-0.5, 0.5, len(anc) - 1)
        out = perturb_increments_shape(anc, u, u_max=0.5)
        r_out = np.array([a[1] for a in out])
        assert abs(r_out[-1] - r_base[-1]) <= 1e-9
        # every increment positive: same direction class as the legacy path
        assert np.all(np.diff(r_out) > 0.0)

    def test_z_unchanged_and_throat_angle_kept(self):
        anc = _base_anchors()
        u = np.full(len(anc) - 1, 0.3)
        out = perturb_increments_shape(anc, u, u_max=0.5)
        np.testing.assert_array_equal([a[0] for a in out], [a[0] for a in anc])
        assert out[0][2] == pytest.approx(anc[0][2], abs=1e-12)

    def test_u_zero_returns_base_radii(self):
        anc = _base_anchors()
        out = perturb_increments_shape(anc, np.zeros(len(anc) - 1), u_max=0.5)
        np.testing.assert_allclose([a[1] for a in out], [a[1] for a in anc], rtol=1e-12)

    def test_clamping_matches_legacy_direction_class(self):
        """u beyond u_max is clipped exactly as the legacy path clips it."""
        anc = _base_anchors()
        u = np.array([5.0, -5.0, 2.0, -2.0, 0.5, -0.5, 0.25, -0.25, 1.0, -1.0, 3.0])
        u_max = 0.5
        raw = perturb_increments_shape(anc, u, u_max)
        clipped = perturb_increments_shape(anc, np.clip(u, -u_max, u_max), u_max)
        np.testing.assert_allclose([a[1] for a in raw], [a[1] for a in clipped], rtol=0.0, atol=1e-12)

    def test_increments_are_a_rescaling_of_the_legacy_increments(self):
        """Each shape increment is the legacy increment times one common scalar."""
        anc = _base_anchors()
        rng = np.random.default_rng(11)
        u = rng.uniform(-0.5, 0.5, len(anc) - 1)
        legacy = perturb_increments(anc, u, 0.5)
        shape = perturb_increments_shape(anc, u, 0.5)
        d_legacy = np.diff([a[1] for a in legacy])
        d_shape = np.diff([a[1] for a in shape])
        ratios = d_shape / d_legacy
        np.testing.assert_allclose(ratios, ratios[0], rtol=1e-12)

    def test_wrong_u_length_raises(self):
        anc = _base_anchors()
        with pytest.raises(ValueError, match="len"):
            perturb_increments_shape(anc, np.zeros(5), u_max=0.5)

    def test_decreasing_base_raises_like_legacy(self):
        anc = [[0.0, 50.0, 10.0], [100.0, 30.0, 5.0]]
        with pytest.raises(ValueError, match="increments"):
            perturb_increments_shape(anc, [0.0], u_max=0.5)

    def test_nonfinite_rescale_raises(self):
        """An impossible u_max makes exp() overflow; the guard refuses it (bad-knob path)."""
        anc = _base_anchors()
        with np.errstate(over="ignore"):
            with pytest.raises(ValueError, match="finite"):
                perturb_increments_shape(anc, np.full(len(anc) - 1, 10_000.0), u_max=10_000.0)


# ---------------------------------------------------------------------------
# registry perturb block mode switch
# ---------------------------------------------------------------------------


class TestRegistryPerturbMode:
    def test_legacy_mode_reproduces_absent_mode_exactly(self):
        """Default (key absent) and explicit {mode: legacy} must be bit-for-bit equal."""
        gen, brief, knobs = _typo_and_brief()
        assert "mode" not in gen["perturb"]

        gen_legacy = copy.deepcopy(gen)
        gen_legacy["perturb"]["mode"] = "legacy"

        absent = registry.materialize(gen, knobs, brief)
        legacy = registry.materialize(gen_legacy, knobs, brief)
        assert absent == legacy

    def test_shape_mode_keeps_the_parent_mouth_radius(self):
        """'shape' leaves the mouth alone; the legacy path moves it with the same u."""
        gen, brief, knobs = _typo_and_brief()
        gen_shape = copy.deepcopy(gen)
        gen_shape["perturb"]["mode"] = "shape"
        gen_legacy = copy.deepcopy(gen)
        gen_legacy["perturb"]["mode"] = "legacy"

        parent = registry.materialize(gen, {**knobs, **{k: 0.0 for k in knobs if "_u" in k}}, brief)
        shape = registry.materialize(gen_shape, knobs, brief)
        legacy = registry.materialize(gen_legacy, knobs, brief)

        mouth = parent["profileH"]["points"][-1][1]
        assert shape["profileH"]["points"][-1][1] == pytest.approx(mouth, abs=1e-9)
        assert shape["profileV"]["points"][-1][1] == pytest.approx(mouth, abs=1e-9)
        assert legacy["profileH"]["points"][-1][1] != pytest.approx(mouth, abs=1e-6)

    def test_unknown_mode_raises_generator_error(self):
        gen, brief, knobs = _typo_and_brief()
        gen_bad = copy.deepcopy(gen)
        gen_bad["perturb"]["mode"] = "nonsense"
        with pytest.raises(registry.GeneratorError, match="mode"):
            registry.materialize(gen_bad, knobs, brief)
