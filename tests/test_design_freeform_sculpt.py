"""examples/freeform_sculpt.yaml: wall control points are searched. These tests pin the rules that
keep every candidate legal for the mesher (hornlab_mesher/freeform.py): z pinned and strictly
increasing, throat pinned and equal in H and V, anchor radius ranges disjoint and increasing (so
any CMA-ES pick flares outward), quarter domain consistent with the native symmetry flag."""
import numpy as np
import pytest

from conftest import EXAMPLES, requires_mesher
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design import families
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import sizing
from hornlab_search.search.evaluate import throat_radius_m
from hornlab_search.types import Design

CFG = EXAMPLES / "freeform_sculpt.yaml"
SYM = (EXAMPLES / "freeform_sculpt_symcheck_quarter.yaml",
       EXAMPLES / "freeform_sculpt_symcheck_full.yaml")


@pytest.fixture(scope="module")
def space():
    return DesignSpace.from_config(load_config(CFG))


def _radius_bounds(space, plane):
    out = {}
    for k, b in space.bounds.items():
        parts = k.split(".")
        if parts[0] == plane and len(parts) == 4 and parts[1] == "points":
            assert parts[3] == "1", f"{k}: only radii (column 1) may be searched; z stays pinned"
            out[int(parts[2])] = b
    return out


def test_search_keys_resolve_and_seed_validates(space):
    assert len(space.keys()) == 11
    for k in space.keys():
        families.param_get("FREEFORM", space.seed.params, k)       # every path exists
    families.validate(space.seed)


@pytest.mark.parametrize("plane", ["profileH", "profileV"])
def test_radius_ranges_are_disjoint_and_increasing(space, plane):
    rb = _radius_bounds(space, plane)
    pts = space.seed.params[plane]["points"]
    assert 0 not in rb, "the throat radius (anchor 0) must stay pinned to the driver exit"
    assert sorted(rb) == list(range(1, len(pts)))
    prev_hi = pts[0][1]
    for i in sorted(rb):
        assert rb[i].lo > prev_hi, f"anchor {i} range overlaps anchor {i - 1}: walls could pinch"
        prev_hi = rb[i].hi


def test_random_candidates_keep_z_increasing_and_radii_increasing(space):
    rng = np.random.default_rng(0)
    for _ in range(200):
        d = space.denormalize(rng.random(len(space.keys())))
        families.validate(d)
        for plane in ("profileH", "profileV"):
            p = np.asarray(d.params[plane]["points"], float)
            assert np.all(np.diff(p[:, 0]) > 0) and np.all(np.diff(p[:, 1]) > 0)
        zH = [r[0] for r in d.params["profileH"]["points"]]
        zV = [r[0] for r in d.params["profileV"]["points"]]
        assert zH[0] == zV[0] and zH[-1] == zV[-1]                  # shared axial span
        assert d.params["profileH"]["points"][0][1] == d.params["profileV"]["points"][0][1]


def test_throat_radius_for_freeform_comes_from_anchor_zero(space):
    assert throat_radius_m(space.seed) == pytest.approx(0.0127)
    p = dict(space.seed.params)
    p["profileV"] = dict(p["profileV"], points=[[0.0, 10.0]] + p["profileV"]["points"][1:])
    assert throat_radius_m(Design("FREEFORM", p)) == pytest.approx(0.010)
    assert throat_radius_m(Design("OSSE", {"r0_mm": 17.78})) == pytest.approx(0.01778)


def test_symcheck_configs_differ_only_in_domain_and_cap():
    q, f = (load_config(p) for p in SYM)
    assert q.raw["seed_params"] == f.raw["seed_params"] == load_config(CFG).raw["seed_params"]
    assert q.target_raw == f.target_raw and q.target_raw["band_hi_hz"] == 3000.0
    assert (q.mesh.quadrants, f.mesh.quadrants) == ("1", "1234")
    assert sizing.SYMMETRY_PLANE["1"] and sizing.SYMMETRY_PLANE["1234"] is None
    assert q.mesh.epw == f.mesh.epw


@requires_mesher
@pytest.mark.timeout(900)
def test_seed_and_samples_mesh_on_the_real_mesher(tmp_path, space):
    from hornlab_search.mesh.build import build_mesh
    cfg = load_config(CFG)
    ms = mesh_spec("screen", cfg)
    m = build_mesh(space.seed, ms, cfg, tmp_path / "seed", mode="screen")
    assert m.quadrants == "1" and m.symmetry_plane == sizing.SYMMETRY_PLANE["1"]
    rng = np.random.default_rng(1)
    ok = 0
    for i in range(6):
        try:
            build_mesh(space.denormalize(rng.random(len(space.keys()))), ms, cfg,
                       tmp_path / str(i), mode="screen")
            ok += 1
        except Exception:  # noqa: BLE001 - a refused candidate is data, counted below
            pass
    assert ok >= 5           # measured 41 of 41 mesh at these bounds (examples/freeform_sculpt.yaml)


def test_throat_angles_are_pinned_and_equal(space):
    assert not any("throatAngleDeg" in k for k in space.keys())
    assert (space.seed.params["profileH"]["throatAngleDeg"]
            == space.seed.params["profileV"]["throatAngleDeg"])
