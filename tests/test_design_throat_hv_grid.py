"""Shared near-throat H/V block (throat_hv) in the grid rows routes. Offline, CPU only.

Le Cleac'h pair: rho scales the per-plane flare T (larger T = faster expansion, eq 42);
onset/ramp blend the round core section into the plane axes. osse_rollback: rho -> per-azimuth k,
onset/ramp -> the superformula window (needs hornlab_mesher, skipped when absent).
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from hornlab_search.design import throat_hv
from hornlab_search.design.generators import grid as G
from hornlab_search.design.generators import profiles as P
from hornlab_search.design.generators import registry

BRIEF = {"driver": {"exit_radius_mm": 18.0, "exit_angle_deg": 2.0}}
LC_SPEC = {"rows": {"type": "lecleach"}, "n_phi": 15, "n_s": 32, "name": "grid"}
OS_SPEC = {"rows": {"type": "osse_rollback"}, "n_phi": 13, "n_s": 40, "span": "quarter"}


def _lc(**extra):
    k = {"g_fc_hz": 450.0, "g_fc_h_hz": 450.0, "g_fc_v_hz": 800.0, "g_T": 0.6, "g_stop_deg": 200.0}
    k.update(extra)
    return k


def _lc_rows(knobs):
    return G.rows_per_azimuth(LC_SPEC, knobs, BRIEF)


def _half_width_ratio(grid, j):
    """H over V section radius at station j (phi = 0 row over phi = 90 row)."""
    r = np.hypot(grid[:, j, 0], grid[:, j, 1])
    return float(r[0] / r[-1])


# ---- Le Cleac'h pair -------------------------------------------------------------------------
def test_lc_absent_and_neutral_rho_are_identical():
    base, _ = _lc_rows(_lc())
    one, _ = _lc_rows(_lc(g_throat_hv_ratio=1.0))
    np.testing.assert_array_equal(base, one)


def test_lc_rho_opens_h_sooner_and_keeps_round_throat():
    base, _ = _lc_rows(_lc())
    hi, _ = _lc_rows(_lc(g_throat_hv_ratio=2.0))
    j = int(round(0.25 * (base.shape[1] - 1)))
    assert _half_width_ratio(hi, j) > _half_width_ratio(base, j)
    r0 = np.hypot(hi[:, 0, 0], hi[:, 0, 1])
    np.testing.assert_allclose(r0, 18.0, atol=1e-9)
    np.testing.assert_array_equal(hi[:, 0, :], base[:, 0, :])


def test_T_direction_larger_T_is_faster_expansion():
    """Direction evidence: at equal fc/stop the larger T has the larger radius at equal arc fraction."""
    def r_at(T):
        xs, ys, _p, _m = P.lecleach_exact(18.0, 500.0, T, 2.0, 200.0, dl_mm=1.0)
        return float(G._resample_arc(xs, ys, 32)[1][8])
    assert r_at(1.0) > r_at(0.4)


def test_lc_onset_leaves_early_stations_round():
    grid, _ = _lc_rows(_lc(g_hv_onset_frac=0.5))
    n_s = grid.shape[1] - 1
    r = np.hypot(grid[:, :, 0], grid[:, :, 1])
    xs, ys, _p, _m = P.lecleach_exact(18.0, math.sqrt(450.0 * 800.0), 0.6, 2.0, 200.0, dl_mm=1.0)
    core_r = G._resample_arc(xs, ys, n_s)[1]
    early = [j for j in range(n_s + 1) if j / n_s < 0.5]
    for j in early:
        np.testing.assert_allclose(r[:, j], core_r[j], atol=1e-9)
    assert abs(r[0, -1] - r[-1, -1]) > 1.0   # the mouth is still H/V split


def test_lc_refusals():
    for bad in ({"g_throat_hv_ratio": 9.0}, {"g_hv_onset_frac": 0.95}, {"g_section_exp_ramp": 0.1}):
        with pytest.raises(registry.GeneratorError):
            _lc_rows(_lc(**bad))
    with pytest.raises(registry.GeneratorError):      # block needs the fc pair
        G.rows_per_azimuth(LC_SPEC, {"g_fc_hz": 450.0, "g_T": 0.6, "g_stop_deg": 200.0,
                                     "g_throat_hv_ratio": 2.0}, BRIEF)


def test_lc_meta_carries_provenance_only_when_active():
    _g, meta = _lc_rows(_lc(g_throat_hv_ratio=2.0))
    assert "LABELED HYBRID" in meta["throat_hv_status"]
    _g, meta0 = _lc_rows(_lc())
    assert "throat_hv_status" not in meta0


# ---- osse_rollback (needs the mesher) --------------------------------------------------------
SEED = {"g_a_h_deg": 45.0, "g_a_v_deg": 45.0, "g_k": 1.0, "g_L_mm": 200.0, "g_r_lip_mm": 20.0,
        "g_wrap_deg": 90.0}
SF = {"g_sf_m": 4, "g_sf_amt": 0.3}


def _os(knobs):
    pytest.importorskip("hornlab_mesher")
    return G._rows_marches(OS_SPEC, {**SEED, **knobs}, BRIEF)


def _same(a, b):
    assert len(a) == len(b)
    for ra, rb in zip(a, b):
        np.testing.assert_array_equal(ra["x"], rb["x"])
        np.testing.assert_array_equal(ra["y"], rb["y"])


def test_os_absent_and_neutral_rho_identical():
    _same(_os({}), _os({"g_throat_hv_ratio": 1.0}))


def test_os_rho_changes_h_vs_v_only_off_neutral():
    base, hi = _os({}), _os({"g_throat_hv_ratio": 2.0})
    j = 100
    assert hi[0]["y"][j] > base[0]["y"][j] and hi[-1]["y"][j] < base[-1]["y"][j]   # H opens sooner


def test_os_onset_ramp_and_refusals():
    pytest.importorskip("hornlab_mesher")
    ramp = _os({**SF, "g_hv_onset_frac": 0.5})
    assert len(ramp) == OS_SPEC["n_phi"]
    for bad in ({**SF, "g_hv_onset_frac": 0.5, "g_sf_start": 0.2},   # two onset knobs
                {"g_hv_onset_frac": 0.5},                             # sf_m == 0
                {"g_sf_m": 4, "g_hv_onset_frac": 0.5},                # sf_amt == 0
                {"g_throat_hv_ratio": 9.0}):
        with pytest.raises(registry.GeneratorError):
            _os(bad)


def test_os_knob_validation_is_mesher_free():
    """The refusals live in the knob validator, so they run without hornlab_mesher."""
    for bad in ({**SF, "g_hv_onset_frac": 0.5, "g_sf_start": 0.2}, {"g_hv_onset_frac": 0.5},
                {"g_sf_m": 4, "g_hv_onset_frac": 0.5}, {"g_throat_hv_ratio": 9.0}):
        with pytest.raises(registry.GeneratorError):
            G._rows_osse_rollback_knobs({**SEED, **bad})
    ok = G._rows_osse_rollback_knobs({**SEED, **SF, "g_hv_onset_frac": 0.5})
    assert ok["_hv"]["hv_onset_frac"] == 0.5
    assert "_hv" not in G._rows_osse_rollback_knobs({**SEED, "g_throat_hv_ratio": 1.0})
    assert throat_hv.STATUS["osse_rollback"]


# ---- iwata_ar onset adoption (2026-11-18 W4b; LABELED HYBRID on the reconstruction) ----------
IW_SPEC = {"rows": {"type": "iwata_ar"}, "n_phi": 15, "n_s": 32, "name": "grid"}


def _iw(**extra):
    k = {"g_fc_hz": 450.0, "g_T": 0.5, "g_stop_deg": 200.0, "g_ar_m": 2.5}
    k.update(extra)
    return k


def _iw_rows(knobs):
    return G.rows_per_azimuth(IW_SPEC, knobs, BRIEF)


def test_iw_absent_block_and_onset_zero_are_identical():
    base, meta = _iw_rows(_iw(g_ar_p=1.5))
    assert "throat_hv" not in meta
    zero, zmeta = _iw_rows(_iw(g_ar_p=1.5, g_hv_onset_frac=0.0))
    np.testing.assert_allclose(zero, base, rtol=0, atol=1e-9)
    assert zmeta["throat_hv"] == {"hv_onset_frac": 0.0}
    assert zmeta["throat_hv_status"] == throat_hv.STATUS["iwata_ar"]


def test_iw_onset_keeps_sections_round_until_onset_then_splits():
    base, _ = _iw_rows(_iw(g_ar_p=1.5))
    late, meta = _iw_rows(_iw(g_ar_p=1.5, g_hv_onset_frac=0.5))
    n = late.shape[1]
    early_j = int(round(0.3 * (n - 1)))
    after_j = int(round(0.8 * (n - 1)))
    assert _half_width_ratio(late, early_j) == pytest.approx(1.0, abs=1e-9)
    assert _half_width_ratio(base, early_j) > 1.0 + 1e-3
    assert _half_width_ratio(late, after_j) > 1.0 + 1e-3
    # same mouth AR (the law still reaches AR_m at l = L0) and the round throat is untouched
    assert _half_width_ratio(late, n - 1) == pytest.approx(_half_width_ratio(base, n - 1), rel=1e-9)
    np.testing.assert_array_equal(late[:, 0, :], base[:, 0, :])


def test_iw_section_exp_ramp_is_the_ar_exponent_alias():
    a, _ = _iw_rows(_iw(g_ar_p=2.0))
    b, meta = _iw_rows(_iw(g_section_exp_ramp=2.0))
    np.testing.assert_array_equal(a, b)
    assert meta["ar_p"] == 2.0 and meta["throat_hv"] == {"section_exp_ramp": 2.0}
    with pytest.raises(registry.GeneratorError, match="alias"):
        _iw_rows(_iw(g_ar_p=2.0, g_section_exp_ramp=2.0))


def test_iw_ratio_is_not_mapped_and_is_refused():
    with pytest.raises(registry.GeneratorError, match="not mapped for iwata_ar"):
        _iw_rows(_iw(g_throat_hv_ratio=1.5))


@pytest.mark.parametrize("onset", [-0.1, 0.95, float("nan")])
def test_iw_out_of_range_onset_is_refused(onset):
    with pytest.raises(registry.GeneratorError):
        _iw_rows(_iw(g_hv_onset_frac=onset))
