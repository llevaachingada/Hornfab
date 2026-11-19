"""2026-11-19: V-lip beak record edit, normal-offset shell replay, host-relative validity, and the
fable_v2 lanes (Klangfilm-Lame c200 host, rolled-rect h12 host) seeded exactly on their hosts."""
import copy
import glob
import json
import pathlib

import numpy as np
import pytest
import yaml

from hornlab_search.design.generators import grid as G
from hornlab_search.design.generators import record_body as RB
from hornlab_search.design.generators.registry import GeneratorError
from hornlab_search.geometry import edits as E
from hornlab_search.geometry import record as R

ROOT = pathlib.Path(__file__).resolve().parents[1]
LANES = ROOT / "examples/typologies/fable_v2_2026-11-19"


class _B:
    def __init__(self, lo, hi):
        self.lo, self.hi = lo, hi


def _run(tag):
    return pathlib.Path(glob.glob(str(ROOT / f"docs/evidence/runs/*{tag}"))[0])


def _klangfilm_host():
    d = _run("517217")
    brief = yaml.safe_load((d / "config.yaml").read_text())["brief"]
    gb = json.loads((d / "designs/88973b1e44e9/design.json").read_text())["params"]["grid"]
    spec0 = {"name": "grid", "rows": {"type": "klangfilm_lame_v1"}, "n_phi": gb["n_phi"], "n_s": gb["n_s"],
             "wall_thickness_mm": gb["wall_thickness_mm"], "span": "quarter"}
    fresh = G.design_params(spec0, gb["knobs"], brief)["grid"]
    from hornlab_search.design.generators import klangfilm_lame_family as KF
    return KF.resolve_grid(fresh, brief)


def _rolled_host():
    d = _run("643de7")
    src = yaml.safe_load((d / "config.yaml").read_text())
    k = json.loads((d / "designs/445dafb7e760/design.json").read_text())["params"]["grid"]["knobs"]
    g = copy.deepcopy(src["generator"])
    g.pop("seed_policy", None)
    from hornlab_search.design.generators import rolled_family as RF
    return RF.resolve_grid(G.design_params(g, k, src["brief"])["grid"], src["brief"])


def _rec(inner):
    inner = np.asarray(inner, float)
    return R.SurfaceRecord(inner, np.zeros(inner.shape[:2]), "t", wall_thickness_mm=3.0)


def test_beak_is_a_v_only_axial_offset_and_zero_is_a_noop():
    host = _rec(_rolled_host()["inner_points"])
    assert np.array_equal(E.vertical_beak(host, projection_mm=0.0).inner, host.inner)
    v = E.vertical_beak(host, projection_mm=20.0, start=0.5)
    dz = v.inner[:, :, 2] - host.inner[:, :, 2]
    assert np.allclose(dz[0], 0.0)                         # H plane untouched
    assert dz[-1, -1] == pytest.approx(20.0)               # V lip moves the full amount
    assert np.allclose(dz[:, : int(0.5 * (host.n_s - 1))], 0.0)   # nothing before the start
    assert np.allclose(v.inner[:, :, :2], host.inner[:, :, :2])


def test_klangfilm_host_replays_its_own_normal_offset_shell_exactly():
    fam = _klangfilm_host()
    spec = RB.spec_from_record(_rec(fam["inner_points"]), wall_thickness_mm=3.0,
                               source_auto_angle_deg=2.0, outer_offset="normal")
    out = RB.resolve_grid(spec, {})
    assert np.allclose(out["inner_points"], fam["inner_points"])
    assert np.allclose(out["outer_points"], fam["outer_points"], atol=1e-9)
    grid_shell = RB.resolve_grid({**spec, "rows": {**spec["rows"], "outer_offset": "grid"}}, {})
    assert not np.allclose(grid_shell["outer_points"], fam["outer_points"], atol=0.5)   # why the option exists


def test_rolled_host_replays_on_the_default_shell_and_rolled_hosts_accept_edits():
    fam = _rolled_host()
    spec = RB.spec_from_record(_rec(fam["inner_points"]), wall_thickness_mm=3.0, source_auto_angle_deg=2.0)
    out = RB.resolve_grid(spec, {})
    assert np.allclose(out["outer_points"], fam["outer_points"], atol=1e-9)
    assert E.validity(_rec(fam["inner_points"]))["no_fold_before_lip"] is False     # rolled by design
    RB.resolve_grid({**spec, "knobs": {"g_beak_v_mm": 30.0, "g_beak_start": 0.5}}, {})   # host-relative: accepted
    h0 = RB.host_mouth_height_mm(fam["inner_points"])
    edited = RB.resolve_grid({**spec, "knobs": {"g_vt_mm": h0 + 100, "g_vt_hold": 0.0}}, {})
    assert RB.host_mouth_height_mm(edited["inner_points"]) == pytest.approx(h0 + 100)


def test_beak_bounds_must_contain_zero_and_start_needs_a_beak():
    fam = _rolled_host()
    spec = RB.spec_from_record(_rec(fam["inner_points"]), wall_thickness_mm=3.0, source_auto_angle_deg=2.0)
    with pytest.raises(GeneratorError, match="exclude the host"):
        RB.validate_search_config(spec, {"g_beak_v_mm": 10.0}, {"g_beak_v_mm": _B(5.0, 40.0)}, {})
    with pytest.raises(GeneratorError, match="needs g_beak_v_mm"):
        RB.resolve_grid({**spec, "knobs": {"g_beak_start": 0.5}}, {})


def test_fable_v2_lanes_score_on_v10_and_pass_meridian_sanity():
    import sys
    sys.path.insert(0, str(ROOT / "tools/analysis"))
    import meridian_sanity as M
    from hornlab_search.config import load_config
    for name in ("hl__klangfilm_hv_core_c200form_v10_v1", "hl__rolled_rect_clean_v10_v1"):
        cfg = load_config(LANES / f"{name}.yaml")
        assert cfg.objective_version == 10
        assert M.check_grid(M.grid_for_config(LANES / f"{name}.yaml"))["ok"], name


def test_rolled_clean_lane_box_is_free_of_s_curves_and_deep_rollback():
    import sys
    sys.path.insert(0, str(ROOT / "tools/analysis"))
    import meridian_sanity as M
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    cfg = load_config(LANES / "hl__rolled_rect_clean_v10_v1.yaml")
    sp = DesignSpace.from_config(cfg)
    for x in np.random.default_rng(5).random((24, len(sp.keys()))):
        d = sp.denormalize(x)
        if "grid" not in d.params:
            continue
        gb = d.params["grid"]
        q, _ = G.rows_grid_points(gb, gb["knobs"], cfg.brief)
        assert M.check_grid(q)["ok"]
