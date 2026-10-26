"""Offline tests for the per-direction (Ath CORE) az_* law in design/families.py.

The published CORE recipe (https://at-horns.eu/core.html, see
docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md section 5b):

    a(p) = 5 + 35*sf(4,12,15,16,1,0.618,p) - 15*cos(p)^10
    n(p) = 6.0 + 1.5*cos(p)^2
    s(p) = 0.6 + 0.23*cos(p)^2

The law lives only in the search layer: it never reaches the mesher as an ``az_`` key,
it is folded into the mesher's own p-expressions for ``a_deg`` / ``n`` / ``s``.
"""
from __future__ import annotations

import copy
import json

import pytest

from hornlab_search.design import families
from hornlab_search.mesh import sizing
from hornlab_search.types import Design, GeometryInvalidError, MeshSpec

# The published CORE values, exactly as the recipe names them.
CORE = {
    "a_deg": 5.0,
    "az_a_sf_amp": 35.0,
    "az_sf_m": 4.0,
    "az_sf_n1": 12.0,
    "az_sf_n2": 15.0,
    "az_sf_n3": 16.0,
    "az_sf_a": 1.0,
    "az_sf_b": 0.618,
    "az_a_cos_amp": -15.0,
    "az_a_cos_pow": 10.0,
    "n": 6.0,
    "az_n_cos2_amp": 1.5,
    "s": 0.6,
    "az_s_cos2_amp": 0.23,
}


def _mspec() -> MeshSpec:
    return MeshSpec(epw=6.0, f_max_hz=10000.0, quadrants="1", max_triangles=73600)


def _core_osse(**over) -> dict:
    """A valid OSSE design carrying the published CORE law (throat etc. from the seed)."""
    params = {
        "r0_mm": 25.4,
        "a0_deg": 1.2,
        "L_mm": 260.0,
        "q": 0.996,
        "k": 1.0,
        "exponent": 2.0,
        "aspect_ratio": 1.0,
        "s1": 1.14,
        "s2": 0.025,
        **CORE,
    }
    params.update(over)
    return params


def _plain_osse() -> dict:
    """The same family without any az_ key (the byte-identity baseline)."""
    return {
        "r0_mm": 17.78,
        "a_deg": 37.5,
        "a0_deg": 15.5,
        "L_mm": 260.0,
        "n": 4.0,
        "s": 0.7,
        "q": 0.995,
        "k": 1.0,
        "exponent": 4.0,
        "aspect_ratio": 1.25,
    }


def _cfg(params: dict, tmp_path) -> dict:
    res = sizing.res_mm_for(6.0, 10000.0)
    return families.to_mesher_config(
        Design("OSSE", copy.deepcopy(params)), _mspec(), res, tmp_path / "m.msh")


def _keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _keys(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _keys(value)


# ------------------------------------------------------------------ (a) published numbers

def test_published_core_values_give_the_a_n_s_table():
    from math import radians

    for deg, a_exp in ((0, 25.0), (45, 33.8), (90, 23.4)):
        v = families.azlaw_values(CORE, radians(deg))
        assert v["a_deg"] == pytest.approx(a_exp, abs=0.05), (deg, v)
    assert families.azlaw_values(CORE, radians(0))["n"] == pytest.approx(7.5, abs=0.05)
    assert families.azlaw_values(CORE, radians(90))["n"] == pytest.approx(6.0, abs=0.05)
    assert families.azlaw_values(CORE, radians(0))["s"] == pytest.approx(0.83, abs=0.05)
    assert families.azlaw_values(CORE, radians(90))["s"] == pytest.approx(0.60, abs=0.05)


# ------------------------------------------------------------------ (b) inert when absent

def test_without_az_keys_the_mesher_config_is_byte_identical_and_has_no_az_trace(tmp_path):
    params = _plain_osse()
    cfg = _cfg(params, tmp_path)

    # Same call on a params copy that has no az_ keys.
    cfg_copy = _cfg(copy.deepcopy(params), tmp_path)
    assert json.dumps(cfg, sort_keys=True) == json.dumps(cfg_copy, sort_keys=True)

    # The law is inert: present but with every amplitude zero changes nothing.
    zeroed = {**copy.deepcopy(params), "az_sf_m": 4.0, "az_a_sf_amp": 0.0,
              "az_a_cos_amp": 0.0, "az_n_cos2_amp": 0.0, "az_s_cos2_amp": 0.0}
    cfg_zeroed = _cfg(zeroed, tmp_path)
    assert json.dumps(cfg, sort_keys=True) == json.dumps(cfg_zeroed, sort_keys=True)

    # "output" is the caller's temp path; it carries no law. Everything else must be clean.
    law_cfg = {k: v for k, v in cfg.items() if k != "output"}
    assert "az_" not in json.dumps(law_cfg, sort_keys=True)
    assert not [k for k in _keys(cfg) if "az_" in k]


# ------------------------------------------------------------------ (c) m must be a multiple of 4

def test_az_sf_m_not_a_multiple_of_four_is_refused_by_name():
    with pytest.raises(GeometryInvalidError, match="az_sf_m"):
        families.validate(Design("OSSE", _core_osse(az_sf_m=6.0)))


# ------------------------------------------------------------------ (d) a(p) must stay positive

def test_amplitudes_that_push_the_wall_angle_nonpositive_are_refused():
    # a(0) = 5 + 35 - 60 = -20 deg.
    with pytest.raises(GeometryInvalidError, match="per-direction wall angle"):
        families.validate(Design("OSSE", _core_osse(az_a_cos_amp=-60.0)))


# ------------------------------------------------------------------ (e) folded into expressions

def test_core_keys_fold_into_the_mesher_expressions_and_never_leak_as_keys(tmp_path):
    cfg = _cfg(_core_osse(), tmp_path)
    assert not [k for k in _keys(cfg) if "az_" in k]
    assert "az_" not in json.dumps(cfg, sort_keys=True)
    a = cfg["profile"]["a_deg"]
    assert isinstance(a, str)
    assert "cos(" in a


# ------------------------------------------------------------------ regression: missing base key

def test_law_still_applies_when_the_base_key_is_absent(tmp_path):
    """The expression must be emitted even if a_deg/n/s are absent (the mesher default is
    then the base), otherwise the per-direction term is silently dropped.

    The amplitudes are small enough that the default 60 deg base stays inside (0.5, 89.5).
    """
    params = {
        "r0_mm": 25.4, "a0_deg": 1.2, "L_mm": 260.0, "q": 0.996, "k": 1.0,
        "exponent": 2.0, "aspect_ratio": 1.0,
        "az_a_sf_amp": 10.0, "az_sf_m": 4.0, "az_sf_n1": 12.0, "az_sf_n2": 15.0,
        "az_sf_n3": 16.0, "az_sf_a": 1.0, "az_sf_b": 0.618,
        "az_a_cos_amp": -5.0, "az_a_cos_pow": 10.0,
        "az_n_cos2_amp": 1.5, "az_s_cos2_amp": 0.23,
    }
    cfg = _cfg(params, tmp_path)
    for key in ("a_deg", "n", "s"):
        assert isinstance(cfg["profile"][key], str), key
        assert "cos(" in cfg["profile"][key], key
    assert "az_" not in json.dumps(cfg["profile"], sort_keys=True)
