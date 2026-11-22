"""Regression tests for the measured sculpted R-OSSE optimizer seeds."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.config import load_config, mesh_spec, solve_spec
from hornlab_search.design.generated import GeneratedSpace
from hornlab_search.design.generators import grid, sculpted_rosse_family as family
from hornlab_search.design.generators.registry import GeneratorError

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "examples/typologies/sculpted_xo900_cma_2026-11-21"
PRIMARY = ROOT / "examples/briefs/home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd.yaml"

# Surface identity from the independent physical-measurement checkpoint, in
# little-endian float64 sampled azimuth/station order.
SURFACES = {
    "r3": (
        "f45ecdf3a7531549fac7b8c1add69be33e71368c797e0ba1379681a383233a21",
        "6b166a8b62aadf50fdfbb4fe0e5db506d5bbc5b6d83e490395110b6a52b9131f",
    ),
    "k1": (
        "ec81d05b25865736b48ecf5b3d7624a4168cd5db79648205246d01877939b934",
        "118fae5aafc3ef6c4dc3b43326bfc70df632787772a3855f46425a9c32e9ce35",
    ),
}
K1_NEUTRAL = (
    "fa139389f7527b0478d6b66410fb0daf99eeb1819e7cdd73a174fc0d63693d6a",
    "f80dbd622e10e1f9cf0883170d91c69c99aa3df3adacf3a61a0f30ec2c4859ce",
)


def hashes(surface):
    return tuple(sha256(np.ascontiguousarray(surface[name], dtype="<f8").tobytes()).hexdigest()
                 for name in ("inner_points", "outer_points"))


@pytest.mark.parametrize("case", ["r3", "k1"])
def test_normal_seed_reproduces_measured_surface(case):
    cfg = load_config(CONFIG / f"{case}.yaml")
    space = GeneratedSpace.from_config(cfg)
    block = space.seed.params["grid"]
    surface = family.resolve_grid(block, cfg.brief)
    assert hashes(surface) == SURFACES[case]
    inner, meta = grid.rows_grid_points(block, block["knobs"], cfg.brief)
    assert np.array_equal(inner, surface["inner_points"])
    assert meta["row_span"] == "quarter"


def test_k_neutral_is_the_saved_original_and_source_is_immutable():
    cfg = load_config(CONFIG / "k1.yaml")
    seed = GeneratedSpace.from_config(cfg).seed.params["grid"]
    neutral = deepcopy(seed)
    neutral["knobs"] = {"g_h_setback_mm": 0.0, "g_v_projection_mm": 0.0}
    assert hashes(family.resolve_grid(neutral, cfg.brief)) == K1_NEUTRAL
    modified = deepcopy(cfg.brief)
    modified["driver"]["exit_radius_mm"] = 19.0
    with pytest.raises(GeneratorError):
        family.resolve_grid(seed, modified)


def test_recipe_digest_and_active_knobs_are_preserved():
    cfg = load_config(CONFIG / "r3.yaml")
    space = GeneratedSpace.from_config(cfg)
    seed = space.seed.params["grid"]
    stale = deepcopy(seed)
    stale["rows"]["implementation_sha256"] = "0" * 64
    with pytest.raises(GeneratorError, match="differs"):
        family.resolve_grid(stale, cfg.brief)
    moved = deepcopy(seed)
    moved["knobs"]["g_sweep"] = 1.0
    assert hashes(family.resolve_grid(moved, cfg.brief)) != SURFACES["r3"]
    assert set(space.keys()) == {"g_sweep", "g_diagonal_delta_deg", "g_aperture_scale"}


@pytest.mark.parametrize("case", ["r3", "k1"])
def test_v11_acoustic_settings_and_screen_observation_are_common(case):
    cfg = load_config(CONFIG / f"{case}.yaml")
    primary = load_config(CONFIG / f"{case}.yaml", brief=PRIMARY)
    assert cfg.objective_version == primary.objective_version == 11
    assert cfg.brief["target"] == primary.brief["target"]
    assert cfg.brief["objective"] == primary.brief["objective"]
    assert cfg.brief["weights"] == primary.brief["weights"]
    assert cfg.brief["driver"] == primary.brief["driver"]
    assert cfg.brief["source"] == primary.brief["source"]
    assert mesh_spec("screen", cfg) == mesh_spec("screen", primary)
    assert solve_spec("screen", cfg) == solve_spec("screen", primary)
    obs = solve_spec("screen", cfg).observation
    assert obs.balloon and obs.balloon_points == 1024

