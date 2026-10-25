"""WP3: pre-mesh envelope estimate, its generated.py error channel, and the graded penalty.

Offline (no mesher, no GPU). Fixtures are the real ``examples/typologies`` configs and briefs,
parsed with PyYAML; the oversized case is a real conical materialization at the brief's inner
mouth limit (the outer 3 mm shell then exceeds it), not an invented geometry.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.design.generated import (
    GENERATOR_ERROR_KEY,
    GENERATOR_OVERSHOOT_KEY,
    GeneratedSpace,
)
from hornlab_search.design.generators import registry
from hornlab_search.design.space import Bound
from hornlab_search.objective.terms import (
    PENALTY_INVALID,
    PENALTY_INVALID_GRADED_CAP,
    graded_infeasible_penalty,
)
from hornlab_search.search.evaluate import envelope_violation
from hornlab_search.types import MeshResult


def _load(name: str):
    """(raw config, brief, knobs, bounds) for a typology fixture, without config-level wiring."""
    typo_path = EXAMPLES / "typologies" / f"{name}.yaml"
    raw = yaml.safe_load(typo_path.read_text())
    brief_path = (typo_path.parent / raw["brief_file"]).resolve()
    brief = yaml.safe_load(brief_path.read_text())
    brief["name"] = brief.get("name", brief_path.stem)
    knobs = {k: float(v) for k, v in raw["seed_params"].items()}
    for key, b in raw["bounds"].items():
        if key not in knobs:
            knobs[key] = 0.5 * (float(b["lo"]) + float(b["hi"]))
    bounds = {k: Bound(lo=float(v["lo"]), hi=float(v["hi"]),
                       search=bool(v.get("search", True)), log=bool(v.get("log", False)))
              for k, v in raw["bounds"].items()}
    return raw, brief, knobs, bounds


def _outer_dims_mm(params: dict) -> tuple[float, float, float]:
    """Independent re-statement of the estimator's dimensions (for the agreement check)."""
    wt = float(params["wall_thickness_mm"])
    ah = params["profileH"]["points"]
    av = params["profileV"]["points"]
    w = 2.0 * (max(p[1] for p in ah) + wt)
    h = 2.0 * (max(p[1] for p in av) + wt)
    zs = [p[0] for p in ah] + [p[0] for p in av]
    depth = max(zs) - min(zs) + wt
    return w, h, depth


def _mesh_from_dims(w_mm: float, h_mm: float, d_mm: float) -> MeshResult:
    return MeshResult(path="", n_triangles=1, n_dof=1, quadrants="1", symmetry_plane="",
                      res_mm={}, bbox_m=(0.0, 0.0, 0.0, w_mm / 1000.0, h_mm / 1000.0, d_mm / 1000.0),
                      seconds=0.0)


def _conical_params(knobs_override: dict | None = None):
    raw, brief, knobs, _ = _load("conical")
    knobs = {**knobs, **(knobs_override or {})}
    return registry.materialize(raw["generator"], knobs, brief), brief


# ---------------------------------------------------------------------------
# estimator
# ---------------------------------------------------------------------------


class TestEnvelopeOvershootEstimate:
    @pytest.mark.parametrize("name", ["conical", "perturbed_tractrix"])
    def test_real_typology_seeds_are_inside(self, name):
        raw, brief, knobs, _ = _load(name)
        params = registry.materialize(raw["generator"], knobs, brief)
        assert registry.envelope_overshoot_estimate(params, brief) == 0.0

    def test_oversized_mouth_is_positive(self):
        """Conical at the inner-mouth limit: the outer 3 mm shell pushes it out."""
        params, brief = _conical_params({"h_rm_mm": 180.0})   # 2*180 = 360 == max_mouth_w
        overshoot = registry.envelope_overshoot_estimate(params, brief)
        assert overshoot is not None and overshoot > 0.0
        # 366 outer width vs the 360 + 0.5 mm post-mesh limit
        assert overshoot == pytest.approx(366.0 / 360.5 - 1.0, rel=1e-9)

    def test_synthetic_inflated_anchors_are_positive(self):
        """Synthetic anchors (2x radii) exercise the estimator without a mesher."""
        params, brief = _conical_params()
        inflated = {
            **params,
            "profileH": {**params["profileH"],
                         "points": [[z, 2.0 * r, a] for z, r, a in params["profileH"]["points"]]},
            "profileV": {**params["profileV"],
                         "points": [[z, 2.0 * r, a] for z, r, a in params["profileV"]["points"]]},
        }
        inflated_overshoot = registry.envelope_overshoot_estimate(inflated, brief)
        assert inflated_overshoot is not None and inflated_overshoot > 0.3

    def test_depth_overshoot_is_positive(self):
        params, brief = _conical_params()
        tight = {**brief, "envelope": {**brief["envelope"], "max_depth_mm": 100.0}}
        # inner z span 180 + 3 mm shell vs 100 + 15 mm allowance
        assert registry.envelope_overshoot_estimate(params, tight) == pytest.approx(
            183.0 / 115.0 - 1.0, rel=1e-9)

    def test_agrees_with_post_mesh_envelope_violation_on_clear_cases(self):
        inside, brief = _conical_params()
        assert registry.envelope_overshoot_estimate(inside, brief) == 0.0
        assert envelope_violation(_mesh_from_dims(*_outer_dims_mm(inside)), brief) == ""

        outside, brief = _conical_params({"h_rm_mm": 180.0})
        overshoot = registry.envelope_overshoot_estimate(outside, brief)
        assert overshoot is not None and overshoot > 0.0
        msg = envelope_violation(_mesh_from_dims(*_outer_dims_mm(outside)), brief)
        assert msg.startswith("outside the brief envelope") and "width 366" in msg

    def test_none_for_missing_brief_or_non_generated_params(self):
        params, brief = _conical_params()
        assert registry.envelope_overshoot_estimate(params, None) is None
        assert registry.envelope_overshoot_estimate({"r0_mm": 12.7, "L_mm": 100.0}, brief) is None
        assert registry.envelope_overshoot_estimate({"profileH": {"points": [[0.0, 12.7, 5.0]]}},
                                                    brief) is None

    def test_brief_without_envelope_is_zero(self):
        params, brief = _conical_params()
        no_env = {k: v for k, v in brief.items() if k != "envelope"}
        assert registry.envelope_overshoot_estimate(params, no_env) == 0.0


# ---------------------------------------------------------------------------
# generated.py error channel
# ---------------------------------------------------------------------------


class TestGeneratedEnvelopeChannel:
    def _space(self):
        raw, brief, knobs, bounds = _load("conical")
        return GeneratedSpace(raw["generator"], brief, knobs, bounds)

    def test_happy_path_has_no_envelope_keys(self):
        space = self._space()
        assert GENERATOR_ERROR_KEY not in space.seed.params
        assert GENERATOR_OVERSHOOT_KEY not in space.seed.params
        d = space.design_from_knobs(dict(space.seed_knobs))
        assert GENERATOR_ERROR_KEY not in d.params and GENERATOR_OVERSHOOT_KEY not in d.params

    def test_estimated_violation_uses_the_structured_error_channel(self):
        space = self._space()
        d = space.design_from_knobs({**space.seed_knobs, "h_rm_mm": 180.0})
        assert d.params[GENERATOR_ERROR_KEY].startswith("invalid_envelope:")
        value = d.params[GENERATOR_OVERSHOOT_KEY]
        assert math.isfinite(value) and value > 0.0
        assert value <= 10.0
        assert d.params["_knobs"]["h_rm_mm"] == 180.0
        assert "profileH" in d.params                      # materialized anchors are retained
        expected = registry.envelope_overshoot_estimate(d.params, space.brief)
        assert value == pytest.approx(expected)

    def test_non_envelope_generator_error_has_no_overshoot_key(self):
        space = self._space()
        # h_rm_mm past the INNER mouth limit -> materialize raises, legacy error path
        d = space.design_from_knobs({**space.seed_knobs, "h_rm_mm": 400.0})
        assert GENERATOR_ERROR_KEY in d.params and "envelope" in d.params[GENERATOR_ERROR_KEY]
        assert GENERATOR_OVERSHOOT_KEY not in d.params


# ---------------------------------------------------------------------------
# graded penalty
# ---------------------------------------------------------------------------


class TestGradedInfeasiblePenalty:
    def test_finite_non_decreasing_above_valid_J_and_capped(self):
        grid = np.array([0.0, 1e-6, 0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 1e3, 1e6])
        vals = np.array([graded_infeasible_penalty(o) for o in grid])
        assert np.all(np.isfinite(vals))
        assert np.all(np.diff(vals) >= 0.0)                    # strictly non-decreasing
        assert vals[0] == PENALTY_INVALID and np.all(vals >= PENALTY_INVALID)
        assert np.all(vals > 1e3 - 1e-12)                      # > any valid J (O(10-100))
        assert vals[-1] == PENALTY_INVALID_GRADED_CAP
        assert PENALTY_INVALID_GRADED_CAP == 2.0e3

    def test_linear_below_the_cap(self):
        assert graded_infeasible_penalty(0.25) == pytest.approx(PENALTY_INVALID + 25.0)

    def test_negative_overshoot_is_treated_as_zero(self):
        assert graded_infeasible_penalty(-1.0) == PENALTY_INVALID

    def test_nan_and_inf_are_finite(self):
        assert math.isfinite(graded_infeasible_penalty(float("nan")))
        assert graded_infeasible_penalty(float("inf")) == PENALTY_INVALID_GRADED_CAP
