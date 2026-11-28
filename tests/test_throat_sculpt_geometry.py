"""CPU contracts for the throat-sculpt overlay (kind throat_sculpt_v1, throat-sculpt-v1). No mesher call, no solver.

Parent: FAV-001 (osse_rollback, design 4140768780f0) from fav8__k1_cd_polish.yaml; r0 = 18 mm, a0 = 2 deg.
"""
import copy
import math

import numpy as np
import pytest

from conftest import REPO
from hornlab_search.config import load_config
from hornlab_search.design.generators import _throat_sculpt_v1 as kernel
from hornlab_search.design.generators import cd_backbone_rows_family, grid, rim_beak_family
from hornlab_search.design.generators import throat_sculpt_family as fam
from hornlab_search.design.generators.registry import GeneratorError
from hornlab_search.types import Design

CFG = REPO / "examples/typologies/fav8_2026-11-20/fav8__k1_cd_polish.yaml"
SPEC = {"rows": {"type": fam.KIND, "parent_rows": {"type": "osse_rollback"}}, "n_phi": 25, "n_s": 64,
        "wall_thickness_mm": 3.0}


@pytest.fixture(scope="module")
def fav():
    cfg = load_config(CFG)
    return cfg.brief, dict(cfg.raw["seed_params"])


def _resolve(fav, **ts):
    brief, seed = fav
    block = fam.design_params(SPEC, {**seed, **{f"g_{k}": float(v) for k, v in ts.items()}}, brief)["grid"]
    return block, fam.resolve_grid(block, brief)


def _r_of_z(inner, row, z):
    x = inner[row, :, 2]
    r = np.hypot(inner[row, :, 0], inner[row, :, 1])
    k = int(np.argmax(x))
    return np.interp(z, x[: k + 1], r[: k + 1])


def _parent(fav, n_s=64):
    brief, seed = fav
    pspec = {"rows": {"type": "osse_rollback"}, "n_phi": 25, "n_s": n_s, "wall_thickness_mm": 3.0}
    block = grid.design_params(pspec, seed, brief)["grid"]
    return grid.rows_grid_points({k: v for k, v in block.items() if k != "knobs"}, block["knobs"], brief)


# ----------------------------------------------------------------------------- kernel laws
def test_slot_map_is_c2_monotone_and_recovers():
    for D, zr in ((5.0, 45.0), (20.0, 60.0), (35.0, 40.0)):
        z = np.linspace(0.0, 1.5 * zr, 20001)
        m = kernel.slot_map(z, D, zr)
        assert np.all(m[z <= D] == 0.0) and np.allclose(m[z >= zr], z[z >= zr])
        dm = np.gradient(m, z)
        assert np.all(dm >= -1e-9)                               # monotone
        h = z[1] - z[0]
        for z_j, slope in ((D, 0.0), (zr, 1.0)):                 # C1 at both joins
            i = int(round(z_j / h))
            assert abs(dm[i - 3] - slope) < 2e-3 and abs(dm[i + 3] - slope) < 2e-3
        d2 = np.gradient(dm, z)
        i = int(round(D / h)); j = int(round(zr / h))
        scale = np.max(np.abs(d2[i + 3: j - 3]))                 # C2: curvature -> 0 at both joins
        assert abs(d2[i + 2]) < 0.02 * scale and abs(d2[j - 2]) < 0.02 * scale


def test_bump_window_is_compact_c2_and_peaks_at_one():
    ts = {**kernel.DEFAULTS, "ts_on_mm": 2.0, "ts_rise_mm": 10.0, "ts_fall_mm": 20.0}
    z = np.linspace(0.0, 40.0, 40001)
    w = kernel.bump(z, ts)
    assert w[z <= 2.0].max() == 0.0 and w[z >= 32.0].max() == 0.0
    assert abs(kernel.bump(np.array([12.0]), ts)[0] - 1.0) < 1e-12
    dw = np.gradient(w, z)
    assert abs(dw[np.searchsorted(z, 2.0) + 2]) < 1e-3 and abs(dw[np.searchsorted(z, 32.0) - 2]) < 1e-3


def test_kernel_limits_and_neutral():
    assert kernel.is_neutral(dict(kernel.DEFAULTS))
    with pytest.raises(ValueError):
        kernel.validate({**kernel.DEFAULTS, "ts_c2": -0.9})
    with pytest.raises(ValueError):
        kernel.validate({**kernel.DEFAULTS, "ts_area": 0.5})


# ----------------------------------------------------------------------------- family contracts
def test_neutral_is_bit_for_bit_parent(fav):
    _block, child = _resolve(fav)
    inner, meta = _parent(fav)
    assert np.array_equal(child["inner_points"], inner)
    assert "outer_points" not in child and child["meta"] == meta


def test_parent_replay_hash_is_fav001(fav):
    brief, seed = fav
    pspec = {"rows": {"type": "osse_rollback"}, "n_phi": 25, "n_s": 40, "wall_thickness_mm": 3.0}
    assert Design("FREEFORM", grid.design_params(pspec, seed, brief)).hash() == "4140768780f0"


def test_station_control_keeps_the_surface(fav):
    _b, child = _resolve(fav, ts_c2=1e-9)
    inner, _ = _parent(fav, n_s=600)
    z = np.linspace(0.0, 150.0, 301)
    for row in (0, 12, 24):
        assert np.max(np.abs(_r_of_z(child["inner_points"], row, z) - _r_of_z(inner, row, z))) < 0.05
    assert child["meta"]["throat_sculpt_achieved"]["core_stations"] >= 15


def test_true_pinch_source_circle_and_untouched_body(fav):
    brief, _ = fav
    r0 = brief["driver"]["exit_radius_mm"]
    _b, child = _resolve(fav, ts_c2=-0.30, ts_rise_mm=12.0, ts_fall_mm=30.0)
    inner = child["inner_points"]
    a = child["meta"]["throat_sculpt_achieved"]
    assert a["true_pinch"] and a["r_min_psi_deg"] == 0.0 and a["pinch_ratio"] < 0.85
    ring = np.hypot(inner[:, 0, 0], inner[:, 0, 1])
    assert np.allclose(ring, r0, atol=1e-9) and np.allclose(inner[:, 0, 2], 0.0, atol=1e-9)
    ref, _ = _parent(fav, n_s=600)
    z_body = np.linspace(50.0, 150.0, 101)                           # past the core end (42 mm + margin)
    for row in range(inner.shape[0]):
        assert np.max(np.abs(_r_of_z(inner, row, z_body) - _r_of_z(ref, row, z_body))) < 0.05
    # V widens where H narrows (c2 < 0)
    assert _r_of_z(inner, 24, 12.0) > _r_of_z(ref, 24, 12.0) + 3.0
    assert _r_of_z(inner, 0, 12.0) < r0


def test_area_policy_preserves_section_area(fav):
    brief, _ = fav
    _b, free = _resolve(fav, ts_c2=-0.35, ts_rise_mm=12.0, ts_fall_mm=30.0)
    _b, kept = _resolve(fav, ts_c2=-0.35, ts_rise_mm=12.0, ts_fall_mm=30.0, ts_area=1.0)
    ref, _ = _parent(fav, n_s=600)
    psis = np.linspace(0.0, 0.5 * math.pi, 25)

    def area(inner, z):
        r = np.array([_r_of_z(inner, i, z) for i in range(25)])
        return 2.0 * np.trapezoid(r ** 2, psis)
    for z in (6.0, 12.0, 25.0):
        assert abs(area(kept["inner_points"], z) / area(ref, z) - 1.0) < 5e-3
    assert abs(area(free["inner_points"], 12.0) / area(ref, 12.0) - 1.0) > 0.02   # the free arm changes area


def test_slot_delays_onset_without_contraction(fav):
    brief, _ = fav
    r0, a0 = brief["driver"]["exit_radius_mm"], brief["driver"]["exit_angle_deg"]
    _b, child = _resolve(fav, ts_slot_h_mm=20.0)
    inner = child["inner_points"]
    z = np.linspace(0.0, 19.5, 40)
    assert np.allclose(_r_of_z(inner, 0, z), r0 + z * math.tan(math.radians(a0)), atol=0.02)   # H = source cone
    rz = _r_of_z(inner, 0, np.linspace(0.0, 80.0, 801))
    assert np.all(np.diff(rz) >= -1e-6)                          # no contraction anywhere on H
    assert not child["meta"]["throat_sculpt_achieved"]["true_pinch"]
    ref, _ = _parent(fav, n_s=600)
    zb = np.linspace(70.0, 150.0, 41)                            # z_rec = 20 + 40 = 60 mm
    assert np.max(np.abs(_r_of_z(inner, 0, zb) - _r_of_z(ref, 0, zb))) < 0.05


def test_recipe_refusals_and_design_identity(fav):
    brief, _ = fav
    block, _ = _resolve(fav, ts_c2=-0.2)
    for key, value in (("schema", "throat-sculpt-family-v0"), ("implementation_sha256", "0" * 64)):
        bad = copy.deepcopy(block)
        bad["rows"][key] = value
        with pytest.raises(GeneratorError):
            fam.resolve_grid(bad, brief)
    other, _ = _resolve(fav, ts_c2=-0.21)
    assert Design("FREEFORM", {"grid": block}).hash() != Design("FREEFORM", {"grid": other}).hash()
    with pytest.raises(GeneratorError):
        _resolve(fav, ts_c2=-0.2, ts_rise_mm=80.0, ts_fall_mm=160.0, ts_on_mm=60.0)   # past the forward station?
    with pytest.raises(GeneratorError):
        fam.design_params(dict(SPEC, n_s=20), {**fav[1], "g_ts_c2": -0.2}, brief)      # too few stations


def test_new_kind_does_not_enter_existing_digests():
    mine = {fam.__file__, kernel.__file__}
    assert not mine & {str(p) for p in cd_backbone_rows_family._sources()}
    assert rim_beak_family.implementation_digest() != fam.implementation_digest()
