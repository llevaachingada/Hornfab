"""Meridian fold + cos(2p) tilt on the per-azimuth OSSE wall angle (2026-11-16)."""
from __future__ import annotations

from math import acos, cos, degrees, pi, sin

import pytest

from hornlab_search.design import families as fam

TRITONIA_WIDTH = degrees(acos(0.5 ** (1.0 / 12.0)))      # |sin p|^12 half depth


def tritonia_a(p):
    """at-horns.eu/ext/Tritonia.txt: a = 48.5 - 7*cos(2p)^5 - 16*sin(p)^12."""
    return 48.5 - 7.0 * cos(2 * p) ** 5 - 16.0 * sin(p) ** 12


TRITONIA = {"a_deg": 48.5, "az_a_cos2p_amp": -7.0, "az_a_cos2p_pow": 5.0,
            "az_fold_v_deg": -16.0, "az_fold_v_width_deg": TRITONIA_WIDTH}


def test_fold_exponent_matches_ath_power():
    assert fam.fold_exponent(TRITONIA_WIDTH) == pytest.approx(12.0, rel=1e-9)
    assert TRITONIA_WIDTH == pytest.approx(19.29, abs=0.01)


@pytest.mark.parametrize("p_deg", [0, 10, 22.5, 45, 60, 70.5, 80, 90])
def test_tritonia_law_reproduced(p_deg):
    p = p_deg * pi / 180
    assert fam.azlaw_values(TRITONIA, p)["a_deg"] == pytest.approx(tritonia_a(p), abs=1e-9)


@pytest.mark.parametrize("p_deg", [0, 15, 45, 75, 90])
def test_expression_evaluates_like_values(p_deg):
    p = p_deg * pi / 180
    expr = fam.azlaw_expressions(TRITONIA)["a_deg"]
    got = eval(expr, {"cos": cos, "sin": sin, "abs": abs, "p": p})     # noqa: S307 - test-only, our own string
    assert got == pytest.approx(tritonia_a(p), abs=1e-9)


def test_absent_fold_is_byte_identical():
    base = {"a_deg": 30.0, "az_a_cos_amp": 12.0, "az_a_cos_pow": 1.5, "az_s_cos2_amp": 0.1, "s": 0.6}
    with_zero = {**base, "az_fold_v_deg": 0.0, "az_fold_h_deg": 0.0, "az_a_cos2p_amp": 0.0,
                 "az_fold_v_width_deg": 25.0}
    assert fam.azlaw_expressions(base) == fam.azlaw_expressions(with_zero)
    assert fam.azlaw_expressions({"a_deg": 30.0}) == {}


def test_fold_alone_emits_expression_and_is_quarter_symmetric():
    params = {"a_deg": 40.0, "az_fold_v_deg": -10.0, "az_fold_v_width_deg": 15.0,
              "az_fold_h_deg": -5.0, "az_fold_h_width_deg": 30.0}
    assert "a_deg" in fam.azlaw_expressions(params)
    for p_deg in (10, 30, 60, 80):
        p = p_deg * pi / 180
        a = fam.azlaw_values(params, p)["a_deg"]
        assert fam.azlaw_values(params, pi - p)["a_deg"] == pytest.approx(a)
        assert fam.azlaw_values(params, -p)["a_deg"] == pytest.approx(a)
    v = fam.azlaw_values(params, pi / 2)["a_deg"]
    assert v == pytest.approx(40.0 - 10.0 + (-5.0) * 0.0)
    half = fam.azlaw_values({"a_deg": 40.0, "az_fold_v_deg": -10.0, "az_fold_v_width_deg": 15.0},
                            (90 - 15) * pi / 180)["a_deg"]
    assert half == pytest.approx(35.0, abs=1e-9)                     # half depth at the width
