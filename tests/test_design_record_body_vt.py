"""WP 4.4 (senior verdict 2026-11-19): the vt freedom as two searched knobs on a record body."""
import numpy as np
import pytest

from hornlab_search.design.generators import record_body as RB
from hornlab_search.design.generators.registry import GeneratorError
from hornlab_search.geometry import edits as E
from hornlab_search.geometry import record as R
from tests.test_geometry_record import _elliptic_cone


class _B:
    def __init__(self, lo, hi):
        self.lo, self.hi = lo, hi


def _spec():
    # proxy of the biradial seed: 560 W x 350 H mouth, 255 mm deep
    rec = R.sample_record(_elliptic_cone(n_mer=60, a0=12.7, b0=12.7, a1=280.0, b1=175.0, L=255.0),
                          wall_thickness_mm=3.0)
    return rec, RB.spec_from_record(rec, wall_thickness_mm=3.0, source_auto_angle_deg=30.0)


def test_host_point_reproduces_the_control_exactly():
    rec, spec = _spec()
    h0 = RB.host_mouth_height_mm(rec.inner)
    assert h0 == pytest.approx(350.0, abs=0.5)
    out = RB.resolve_grid({**spec, "knobs": {"g_vt_mm": h0, "g_vt_hold": 0.0}}, {})
    assert np.allclose(out["inner_points"], rec.inner, atol=1e-9)


def test_knobs_match_the_u3_edit_and_change_the_digest():
    rec, spec = _spec()
    out = RB.resolve_grid({**spec, "knobs": {"g_vt_mm": 460.0, "g_vt_hold": 0.5}}, {})
    assert np.allclose(out["inner_points"], E.vertical_timing(rec, mouth_height_mm=460.0).inner)
    assert out["meta"]["record_digest"] != out["meta"]["host_digest"] == rec.digest()
    assert out["meta"]["knobs"] == {"g_vt_mm": 460.0, "g_vt_hold": 0.5}


@pytest.mark.parametrize("h", [275.0, 350.0, 420.0, 465.0])
def test_owner_range_275_to_465_builds(h):
    _, spec = _spec()
    out = RB.resolve_grid({**spec, "knobs": {"g_vt_mm": h, "g_vt_hold": 0.25}}, {})
    inner = out["inner_points"]
    assert RB.host_mouth_height_mm(inner) == pytest.approx(h)          # V-axis mouth height
    bbox_h = 2.0 * float(np.max(np.abs(inner[:, -1, 1])))
    assert bbox_h >= h - 1e-6   # below ~280 mm on this proxy the diagonals stay taller than the axis


def test_design_params_hash_differs_by_knob_and_validates():
    _, spec = _spec()
    a = RB.design_params(spec, {"g_vt_mm": 400.0, "g_vt_hold": 0.0}, {})
    b = RB.design_params(spec, {"g_vt_mm": 401.0, "g_vt_hold": 0.0}, {})
    assert a["grid"]["knobs"] != b["grid"]["knobs"]
    RB.validate_grid_params(a["grid"])
    assert RB.design_params(spec, {}, {}) == {"grid": dict(spec)}   # unedited route unchanged


def test_refusals():
    _, spec = _spec()
    with pytest.raises(GeneratorError, match="unknown knobs"):
        RB.resolve_grid({**spec, "knobs": {"g_vt_mm": 400.0, "g_vt_hold": 0.0, "g_x": 1.0}}, {})
    with pytest.raises(GeneratorError, match="missing"):
        RB.resolve_grid({**spec, "knobs": {"g_vt_mm": 400.0}}, {})
    with pytest.raises(GeneratorError, match="outside"):
        RB.resolve_grid({**spec, "knobs": {"g_vt_mm": 400.0, "g_vt_hold": 1.5}}, {})


def test_search_config_requires_the_control_inside_the_bounds():
    _, spec = _spec()
    seed = {"g_vt_mm": 350.0, "g_vt_hold": 0.0}
    RB.validate_search_config(spec, seed, {"g_vt_mm": _B(275.0, 465.0), "g_vt_hold": _B(0.0, 0.5)}, {})
    with pytest.raises(GeneratorError, match="exclude the host"):
        RB.validate_search_config(spec, {"g_vt_mm": 450.0, "g_vt_hold": 0.0},
                                  {"g_vt_mm": _B(440.0, 465.0), "g_vt_hold": _B(0.0, 0.5)}, {})


def test_shipped_vt_v1_config_seeds_the_control_and_spans_the_owner_bounds():
    import pathlib
    import yaml
    from hornlab_search.config import load_config
    from hornlab_search.design.generators import grid as G
    from hornlab_search.design.space import DesignSpace
    here = pathlib.Path(__file__).resolve().parents[1] / "examples/studies/u3_biradial_es_style_v7"
    cfg = load_config(here / "vt_v1.yaml")
    sp = DesignSpace.from_config(cfg)
    assert sorted(sp.keys()) == ["g_vt_hold", "g_vt_mm"]
    assert (cfg.bounds_raw["g_vt_mm"]["lo"], cfg.bounds_raw["g_vt_mm"]["hi"]) == (275.0, 465.0)
    ctl = np.array(yaml.safe_load((here / "control.yaml").read_text())["seed_params"]["grid"]["rows"]["points"])
    seed = sp.design_from_knobs({"g_vt_mm": 386.727504, "g_vt_hold": 0.0})
    inner, _ = G.rows_grid_points(seed.params["grid"], seed.params["grid"]["knobs"], cfg.brief)
    assert np.allclose(inner, ctl, atol=1e-6)
