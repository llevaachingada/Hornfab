"""Offline tests for design/families.py (04 tests 5-8, 13 and the key-table rules)."""
from __future__ import annotations

import copy

import pytest

from hornlab_search.config import load_config
from hornlab_search.design import families
from hornlab_search.design.families import FAMILY_KEYS, to_mesher_config, validate
from hornlab_search.mesh import sizing
from hornlab_search.types import Design, GeometryInvalidError, MeshSpec

from conftest import EXAMPLES

OSSE = dict(r0_mm=17.78, a_deg=37.5, a0_deg=15.5, L_mm=260.0, n=4.0, s=0.7, q=0.995, k=1.0,
            exponent=4.0, aspect_ratio=1.25)
ROSSE = dict(R_mm=150.0, r0_mm=12.7, a_deg=60.0, a0_deg=15.5, k=1.0, q=1.0, exponent=2.0,
             aspect_ratio=1.0)
ICW = dict(termination="flat_baffle", r0_mm=12.7, a0_deg=14.5, L_mm=160.0, R_mm=130.0,
           coverage_angle_deg=50.0, hold_start=0.3, hold_end=0.7)


def ffm(**over):
    p = {
        "profileH": {"points": [[0.0, 12.7], [60.0, 80.0], [120.0, 160.0]],
                     "throatAngleDeg": 15.5, "mouthAngleDeg": 70.0},
        "profileV": {"points": [[0.0, 12.7], [60.0, 60.0], [120.0, 110.0]],
                     "throatAngleDeg": 15.5, "mouthAngleDeg": 60.0},
        "crossSections": [{"t": 0.0, "shape": "circle"},
                          {"t": 1.0, "shape": "superellipse", "exponent": 4.0}],
    }
    p.update(over)
    return p


def mspec(**kw):
    base = dict(epw=6.0, f_max_hz=10000.0, quadrants="1", max_triangles=73600)
    base.update(kw)
    return MeshSpec(**base)


# ------------------------------------------------------------------ acceptance


@pytest.mark.parametrize("family,params", [
    ("OSSE", OSSE), ("R-OSSE", ROSSE), ("ICW", ICW), ("FREEFORM", ffm())])
def test_valid_seeds_pass(family, params):
    validate(Design(family, copy.deepcopy(params)))


def test_example_yaml_seeds_pass_where_complete():
    for name in ("osse_baseline.yaml", "throat_adapter.yaml", "freeform_hv.yaml",
                 "icw_termination.yaml"):
        cfg = load_config(EXAMPLES / name)
        validate(Design(cfg.family, copy.deepcopy(cfg.seed_params)))


def test_tables_exist_for_four_families():
    assert set(FAMILY_KEYS) == {"OSSE", "R-OSSE", "ICW", "FREEFORM"}


def test_fork_keys_are_table_rows():
    """Guiding-curve superformula, ICW curvature controls and morph keys are table rows."""
    for k in ("gcurve_sf_a", "gcurve_sf_b", "gcurve_sf_m1", "gcurve_sf_m2", "gcurve_sf_n1",
              "gcurve_sf_n2", "gcurve_sf_n3", "gcurve_se_n", "morph_target", "morph_width_mm",
              "morph_height_mm", "morph_corner_mm", "morph_rate"):
        assert k in FAMILY_KEYS["OSSE"], k
    for k in ("kappa0", "theta1_deg", "hold_start", "hold_end", "kappa_abs_max",
              "dkappa_ds_abs_max", "n_coeff"):
        assert k in FAMILY_KEYS["ICW"], k


# ------------------------------------------------------------------ test 5


def test_unknown_key_rejected_and_named():
    with pytest.raises(GeometryInvalidError, match="bogus_key"):
        validate(Design("OSSE", {**OSSE, "bogus_key": 1.0}))


def test_unknown_family_rejected():
    with pytest.raises(GeometryInvalidError, match="family"):
        validate(Design("NOPE", {}))


# ------------------------------------------------------------------ test 6


def test_rosse_rejects_rot_deg_and_explicit_L():
    with pytest.raises(GeometryInvalidError, match="rot_deg"):
        validate(Design("R-OSSE", {**ROSSE, "rot_deg": 10.0}))
    with pytest.raises(GeometryInvalidError, match="L_mm"):
        validate(Design("R-OSSE", {**ROSSE, "L_mm": 200.0}))


@pytest.mark.parametrize("key", ["n", "s", "q", "k", "a_deg", "s1", "s2", "rot_deg", "h"])
def test_icw_rejects_osse_shape_keys(key):
    with pytest.raises(GeometryInvalidError, match=key):
        validate(Design("ICW", {**ICW, key: 1.0}))


def test_icw_rejects_zmap_keys():
    for key in ("zmap", "z_map_points", "sampling_mode"):
        with pytest.raises(GeometryInvalidError, match=key):
            validate(Design("ICW", {**ICW, key: 1.0}))


def test_osse_rejects_rosse_keys():
    with pytest.raises(GeometryInvalidError, match="R_mm"):
        validate(Design("OSSE", {**OSSE, "R_mm": 150.0}))


# ------------------------------------------------------------------ test 7


def test_freeform_rejects_nonincreasing_z():
    f = ffm()
    f["profileH"]["points"] = [[0.0, 12.7], [60.0, 80.0], [60.0, 160.0]]
    with pytest.raises(GeometryInvalidError, match="profileH.*strictly increasing"):
        validate(Design("FREEFORM", f))
    f["profileH"]["points"] = [[0.0, 12.7], [80.0, 80.0], [60.0, 160.0]]
    with pytest.raises(GeometryInvalidError, match="strictly increasing"):
        validate(Design("FREEFORM", f))


@pytest.mark.parametrize("exponent", [1.5, 20.0])
def test_freeform_rejects_superellipse_exponent_out_of_range(exponent):
    f = ffm()
    f["crossSections"][1]["exponent"] = exponent
    with pytest.raises(GeometryInvalidError, match="exponent"):
        validate(Design("FREEFORM", f))


@pytest.mark.parametrize("exponent", [2.0, 16.0])
def test_freeform_accepts_exponent_limits(exponent):
    f = ffm()
    f["crossSections"][1]["exponent"] = exponent
    validate(Design("FREEFORM", f))


def test_freeform_structure_rules():
    with pytest.raises(GeometryInvalidError, match="profileV"):
        validate(Design("FREEFORM", {k: v for k, v in ffm().items() if k != "profileV"}))
    f = ffm()
    f["profileH"]["points"] = [[0.0, 12.7]]
    with pytest.raises(GeometryInvalidError, match="2 to 64"):
        validate(Design("FREEFORM", f))
    f = ffm()
    f["profileH"]["tangentScale"] = 1.0
    with pytest.raises(GeometryInvalidError, match="tangentScale"):
        validate(Design("FREEFORM", f))
    f = ffm()
    f["crossSections"][0]["t"] = 0.1
    with pytest.raises(GeometryInvalidError, match="t=0"):
        validate(Design("FREEFORM", f))
    f = ffm()
    f["crossSections"].append({"t": 0.5, "shape": "rounded_rectangle"})
    with pytest.raises(GeometryInvalidError):          # non-increasing t and missing corner
        validate(Design("FREEFORM", f))
    f = ffm(exponent=4.0)       # legacy cross-section key is refused for FREEFORM
    with pytest.raises(GeometryInvalidError, match="exponent"):
        validate(Design("FREEFORM", f))


# ------------------------------------------------------------------ schema constraints


def test_osse_n_and_q_positive_while_s_nonzero():
    with pytest.raises(GeometryInvalidError, match="'n'"):
        validate(Design("OSSE", {**OSSE, "n": 0.0}))
    with pytest.raises(GeometryInvalidError, match="'q'"):
        validate(Design("OSSE", {**OSSE, "q": -0.1}))
    validate(Design("OSSE", {**OSSE, "n": -1.0, "s": 0.0}))   # termination off: legal


@pytest.mark.parametrize("key,val", [("s1", -0.1), ("s1", 10.5), ("s2", -1.0), ("s2", 11.0)])
def test_s1_s2_range(key, val):
    with pytest.raises(GeometryInvalidError, match=key):
        validate(Design("OSSE", {**OSSE, key: val}))


def test_s1_must_be_a_plain_number():
    with pytest.raises(GeometryInvalidError, match="s1"):
        validate(Design("OSSE", {**OSSE, "s1": "1+1"}))      # expression: per-azimuth form
    with pytest.raises(GeometryInvalidError, match="s1"):
        validate(Design("OSSE", {**OSSE, "s1": float("nan")}))


def test_icw_hold_ordering_and_termination_choice():
    with pytest.raises(GeometryInvalidError, match="hold_start"):
        validate(Design("ICW", {**ICW, "hold_start": 0.8, "hold_end": 0.2}))
    with pytest.raises(GeometryInvalidError, match="termination"):
        validate(Design("ICW", {**ICW, "termination": "banana"}))


def test_bool_is_not_a_number():
    with pytest.raises(GeometryInvalidError, match="r0_mm"):
        validate(Design("OSSE", {**OSSE, "r0_mm": True}))


# ------------------------------------------------------------------ test 8


@pytest.mark.parametrize("family,params", [
    ("OSSE", OSSE), ("R-OSSE", ROSSE), ("ICW", ICW), ("FREEFORM", ffm())])
def test_to_mesher_config_invariants(family, params, tmp_path):
    ms = mspec()
    res = sizing.res_mm_for(ms.epw, ms.f_max_hz)
    cfg = to_mesher_config(Design(family, copy.deepcopy(params)), ms, res, tmp_path / "m.msh")
    assert cfg["formula"] == family
    assert cfg["mode"] == "freestanding"
    m = cfg["mesh"]
    assert m["scale_to_metres"] is True
    assert m["allow_large_mesh"] is False
    assert m["throat_res_mm"] == res["throat"]
    assert m["mouth_res_mm"] == res["mouth"]
    assert m["rear_res_mm"] == res["rear"]
    assert m["quadrants"] == "1"
    assert m["max_triangles"] == 73600
    assert cfg["output"] == {"path": str(tmp_path / "m.msh")}


def test_to_mesher_config_routes_keys_to_their_sections(tmp_path):
    d = Design("OSSE", {**OSSE, "morph_target": 1, "gcurve_type": 2, "mode": "bare",
                        "wall_thickness_mm": 4.0})
    cfg = to_mesher_config(d, mspec(), sizing.res_mm_for(6.0, 10000.0), tmp_path / "m.msh")
    assert cfg["cross_section"] == {"exponent": 4.0, "aspect_ratio": 1.25}
    assert cfg["morph"] == {"morph_target": 1}
    assert cfg["gcurve"] == {"gcurve_type": 2}
    assert cfg["mode"] == "bare"                       # a design may override the default mode
    assert cfg["mesh"]["wall_thickness_mm"] == 4.0
    assert cfg["profile"]["L_mm"] == 260.0
    assert "exponent" not in cfg["profile"]


def test_to_mesher_config_does_not_alias_the_design(tmp_path):
    d = Design("FREEFORM", ffm())
    cfg = to_mesher_config(d, mspec(quadrants="1234"), sizing.res_mm_for(6.0, 10000.0),
                           tmp_path / "m.msh")
    cfg["profile"]["profileH"]["points"][0][1] = 999.0
    assert d.params["profileH"]["points"][0][1] == 12.7


def test_to_mesher_config_validates():
    with pytest.raises(GeometryInvalidError, match="bogus"):
        to_mesher_config(Design("OSSE", {"bogus": 1}), mspec(), {"throat": 1, "mouth": 2, "rear": 2},
                         "x.msh")


# ------------------------------------------------------------------ test 13


def test_design_hash_order_and_ninth_decimal():
    a = Design("OSSE", {"r0_mm": 17.78, "a_deg": 37.5, "L_mm": 260.0})
    b = Design("OSSE", {"L_mm": 260.0, "a_deg": 37.5, "r0_mm": 17.78})
    assert a.hash() == b.hash()
    c = Design("OSSE", {"r0_mm": 17.78, "a_deg": 37.5, "L_mm": 260.0 + 1e-9})
    assert c.hash() != a.hash()                      # change in the ninth decimal
    d = Design("OSSE", {"r0_mm": 17.78, "a_deg": 37.5, "L_mm": 260.0 + 1e-11})
    assert d.hash() == a.hash()                      # below the canonicalization floor


def test_wrap_mesher_error_preserves_message_and_points_at_custom():
    e = families.wrap_mesher_error(ValueError("per-azimuth throat stretch is not supported yet; s1"))
    assert isinstance(e, GeometryInvalidError)
    assert "per-azimuth throat stretch is not supported yet; s1" in str(e)
    assert "design/custom.py" in str(e)
    e2 = families.wrap_mesher_error(ValueError("something else"))
    assert str(e2) == "something else"
