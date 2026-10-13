"""Offline tests for design/space.py (04 tests 1-4 and the search-vector rules)."""
from __future__ import annotations

import copy
import logging
import math
from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.config import load_config
from hornlab_search.design import families
from hornlab_search.design.space import Bound, DesignSpace
from hornlab_search.types import Design, GeometryInvalidError

from conftest import EXAMPLES

ROSSE_SEED = dict(R_mm=150.0, r0_mm=12.7, a_deg=60.0, a0_deg=15.5, k=1.0, q=1.0, exponent=2.0,
                  aspect_ratio=1.0)
ROSSE_BOUNDS = {
    "R_mm": {"lo": 100.0, "hi": 220.0}, "a_deg": {"lo": 30.0, "hi": 70.0},
    "a0_deg": {"lo": 5.0, "hi": 30.0}, "k": {"lo": 0.3, "hi": 2.5},
    "q": {"lo": 0.9, "hi": 1.0}, "exponent": {"lo": 2.0, "hi": 6.0},
    "r0_mm": {"lo": 12.7, "hi": 12.7, "search": False},
}


def rosse_cfg():
    return SimpleNamespace(family="R-OSSE", seed_params=copy.deepcopy(ROSSE_SEED),
                           bounds_raw=copy.deepcopy(ROSSE_BOUNDS))


def all_spaces():
    out = {}
    for name in ("osse_baseline.yaml", "throat_adapter.yaml", "icw_termination.yaml",
                 "freeform_hv.yaml"):
        out[name] = DesignSpace.from_config(load_config(EXAMPLES / name))
    out["rosse (inline)"] = DesignSpace.from_config(rosse_cfg())
    return out


def close(a, b, tol=1e-9) -> bool:
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k], tol) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and not isinstance(a, bool):
        return abs(float(a) - float(b)) <= tol
    return a == b


def random_design(space: DesignSpace, rng) -> Design:
    """Independent of denormalize: sample each searchable key directly inside its bound."""
    params = copy.deepcopy(space.seed.params)
    for k in space.keys():
        b = space.bounds[k]
        u = rng.uniform()
        v = 10 ** (math.log10(b.lo) + u * (math.log10(b.hi) - math.log10(b.lo))) if b.log \
            else b.lo + u * (b.hi - b.lo)
        families.param_set(space.family, params, k, float(v))
    return Design(space.family, params)


# ------------------------------------------------------------------ test 1


def test_keys_alphabetical_and_independent_of_yaml_order():
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    sp = DesignSpace.from_config(cfg)
    assert sp.keys() == sorted(sp.keys())
    assert "r0_mm" not in sp.keys()                 # search: false
    reordered = copy.copy(cfg)
    reordered.bounds_raw = dict(reversed(list(cfg.bounds_raw.items())))
    assert list(reordered.bounds_raw) != list(cfg.bounds_raw)
    sp2 = DesignSpace.from_config(reordered)
    assert sp2.keys() == sp.keys()
    d = sp.denormalize(np.linspace(0.05, 0.95, len(sp.keys())))
    assert np.array_equal(sp.normalize(d), sp2.normalize(d))


# ------------------------------------------------------------------ test 2


@pytest.mark.parametrize("name", list(all_spaces()))
def test_roundtrip_seed_and_200_random_designs(name, rng):
    sp = all_spaces()[name]
    assert len(sp.keys()) >= 3
    designs = [sp.seed] + [random_design(sp, rng) for _ in range(200)]
    for d in designs:
        back = sp.denormalize(sp.normalize(d))
        assert close(back.params, d.params, 1e-9), (name, d.params, back.params)
        families.validate(back)             # every vector decodes to a legal design


def test_normalize_stays_in_unit_box(rng):
    for sp in all_spaces().values():
        for _ in range(20):
            x = sp.normalize(random_design(sp, rng))
            assert x.shape == (len(sp.keys()),)
            assert np.all(x >= 0.0) and np.all(x <= 1.0)


def test_denormalize_clips_and_checks_length():
    sp = DesignSpace.from_config(load_config(EXAMPLES / "osse_baseline.yaml"))
    k = len(sp.keys())
    lo = sp.denormalize(np.full(k, -5.0))
    hi = sp.denormalize(np.full(k, 7.0))
    for key in sp.keys():
        assert lo.params[key] == pytest.approx(sp.bounds[key].lo)
        assert hi.params[key] == pytest.approx(sp.bounds[key].hi)
    with pytest.raises(ValueError, match="length"):
        sp.denormalize(np.zeros(k + 1))


def test_non_searched_keys_keep_seed_values():
    sp = DesignSpace.from_config(load_config(EXAMPLES / "osse_baseline.yaml"))
    d = sp.denormalize(np.full(len(sp.keys()), 0.3))
    assert d.params["r0_mm"] == sp.seed.params["r0_mm"]


# ------------------------------------------------------------------ test 3


def test_normalize_clips_out_of_bounds_seed_and_warns(caplog):
    cfg = load_config(EXAMPLES / "osse_baseline.yaml")
    cfg = copy.copy(cfg)
    cfg.seed_params = {**cfg.seed_params, "a_deg": 80.0, "L_mm": 50.0}   # outside bounds
    sp = DesignSpace.from_config(cfg)
    with caplog.at_level(logging.WARNING, logger="hornlab_search.design.space"):
        x = sp.normalize(sp.seed)                    # must not raise
    keys = sp.keys()
    assert x[keys.index("a_deg")] == 1.0
    assert x[keys.index("L_mm")] == 0.0
    text = caplog.text
    assert "a_deg" in text and "L_mm" in text and "clipped" in text


# ------------------------------------------------------------------ test 4


def test_log_bound_requires_positive_lo_at_construction():
    with pytest.raises(ValueError, match="lo > 0"):
        Bound(lo=0.0, hi=10.0, log=True)
    with pytest.raises(ValueError, match="lo > 0"):
        Bound(lo=-1.0, hi=10.0, log=True)
    Bound(lo=0.001, hi=10.0, log=True)


def test_log_bound_via_from_config_raises_at_construction():
    cfg = rosse_cfg()
    cfg.bounds_raw["R_mm"] = {"lo": 0.0, "hi": 220.0, "log": True}
    with pytest.raises(ValueError, match="lo > 0"):
        DesignSpace.from_config(cfg)


def test_log_bound_maps_through_log10():
    b = Bound(lo=10.0, hi=1000.0, log=True)
    assert b.to_unit(100.0)[0] == pytest.approx(0.5)
    assert b.from_unit(0.5) == pytest.approx(100.0)
    cfg = rosse_cfg()
    cfg.bounds_raw["R_mm"] = {"lo": 50.0, "hi": 500.0, "log": True}
    sp = DesignSpace.from_config(cfg)
    x = sp.normalize(Design("R-OSSE", {**ROSSE_SEED, "R_mm": math.sqrt(50.0 * 500.0)}))
    assert x[sp.keys().index("R_mm")] == pytest.approx(0.5)


def test_searchable_bound_needs_a_span():
    with pytest.raises(ValueError, match="lo < hi"):
        Bound(lo=1.0, hi=1.0)
    Bound(lo=1.0, hi=1.0, search=False)
    with pytest.raises(ValueError):
        Bound(lo=2.0, hi=1.0, search=False)


# ------------------------------------------------------------------ family specifics


def test_illegal_bound_key_rejected_at_construction():
    cfg = rosse_cfg()
    cfg.bounds_raw["rot_deg"] = {"lo": 0.0, "hi": 10.0}
    with pytest.raises(GeometryInvalidError, match="rot_deg"):
        DesignSpace.from_config(cfg)


# Senior ruling 2026-10-13 (user-confirmed): the shipped ICW example carries an EXPLICIT
# kappa0/theta1_deg seed; the silent midpoint fill is only a defensive net for a genuinely
# missing key, never something a shipped example relies on.
def test_icw_example_seed_is_explicit_no_fill(caplog):
    cfg = load_config(EXAMPLES / "icw_termination.yaml")
    with caplog.at_level(logging.WARNING, logger="hornlab_search.design.space"):
        sp = DesignSpace.from_config(cfg)
    assert cfg.seed_params["kappa0"] == pytest.approx(0.25)       # explicit in the example
    assert cfg.seed_params["theta1_deg"] == pytest.approx(16.0)
    assert sp.seed.params["kappa0"] == pytest.approx(0.25)
    assert sp.seed.params["theta1_deg"] == pytest.approx(16.0)
    assert "kappa0" not in caplog.text and "theta1_deg" not in caplog.text
    assert "termination" not in sp.keys()                        # categorical, not searchable


def test_missing_searchable_keys_filled_with_midpoint_is_defensive_net(caplog):
    cfg = load_config(EXAMPLES / "icw_termination.yaml")
    raw = SimpleNamespace(
        family="ICW",
        seed_params={k: copy.deepcopy(v) for k, v in cfg.seed_params.items()
                     if k not in ("kappa0", "theta1_deg")},
        bounds_raw=copy.deepcopy(cfg.bounds_raw))
    with caplog.at_level(logging.WARNING, logger="hornlab_search.design.space"):
        sp = DesignSpace.from_config(raw)
    assert "kappa0" not in raw.seed_params and "theta1_deg" not in raw.seed_params
    assert sp.seed.params["kappa0"] == pytest.approx(0.25)       # (0.0 + 0.5) / 2
    assert sp.seed.params["theta1_deg"] == pytest.approx(16.0)   # (2 + 30) / 2
    assert "kappa0" in caplog.text and "theta1_deg" in caplog.text
    assert raw.seed_params.get("kappa0") is None                  # input not mutated


def test_freeform_dotted_and_alias_keys():
    cfg = load_config(EXAMPLES / "freeform_hv.yaml")
    sp = DesignSpace.from_config(cfg)
    assert sp.keys() == sorted(["profileH.mouthAngleDeg", "profileV.mouthAngleDeg", "exponent"])
    d = sp.denormalize(np.array([1.0, 0.0, 1.0]))     # alphabetical: exponent, profileH, profileV
    assert d.params["crossSections"][1]["exponent"] == pytest.approx(8.0)
    assert d.params["profileH"]["mouthAngleDeg"] == pytest.approx(40.0)
    assert d.params["profileV"]["mouthAngleDeg"] == pytest.approx(80.0)
    assert d.params["profileH"]["points"] == cfg.seed_params["profileH"]["points"]
    assert "exponent" not in d.params                  # alias never leaks a top-level key
    families.validate(d)


def test_freeform_point_list_paths_work():
    cfg = SimpleNamespace(
        family="FREEFORM",
        seed_params=copy.deepcopy(load_config(EXAMPLES / "freeform_hv.yaml").seed_params),
        bounds_raw={"profileH.points.2.1": {"lo": 120.0, "hi": 200.0}})
    sp = DesignSpace.from_config(cfg)
    d = sp.denormalize(np.array([1.0]))
    assert d.params["profileH"]["points"][2][1] == pytest.approx(200.0)
    assert d.params["profileH"]["points"][1][1] == 80.0
    bad = copy.deepcopy(cfg)
    bad.bounds_raw = {"profileH.points.9.1": {"lo": 1.0, "hi": 2.0}}
    with pytest.raises(GeometryInvalidError, match="path does not exist"):
        DesignSpace.from_config(bad)


def test_integer_keys_round_on_denormalize():
    cfg = SimpleNamespace(
        family="ICW", seed_params=dict(termination="flat_baffle", r0_mm=12.7, a0_deg=14.5,
                                       L_mm=160.0, R_mm=130.0, n_coeff=12),
        bounds_raw={"n_coeff": {"lo": 8.0, "hi": 20.0}})
    sp = DesignSpace.from_config(cfg)
    d = sp.denormalize(np.array([0.4]))
    assert isinstance(d.params["n_coeff"], int) and d.params["n_coeff"] == 13


def test_denormalized_hash_is_stable_across_roundtrip(rng):
    sp = DesignSpace.from_config(load_config(EXAMPLES / "freeform_hv.yaml"))
    for _ in range(20):
        d = sp.denormalize(rng.uniform(size=len(sp.keys())))
        again = sp.denormalize(sp.normalize(d))
        assert again.hash() == d.hash()


def test_all_example_seeds_validate_after_space_construction():
    for name, sp in all_spaces().items():
        families.validate(sp.seed)
