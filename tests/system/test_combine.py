"""SYS-08 analytic + SYS-06/SYS-15 tests for ``hornlab_search.system.combine``.

The physical setup carries every spatial phase INSIDE the input arrays; the combiner is only
allowed to apply DSP and linear input levels. These tests therefore pin the phase-once rule, the
delay convention, the magnitude-only refusal and the pure-recombination cache identity.
"""
from __future__ import annotations

import math
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.meh import dsp as meh_dsp  # noqa: E402
from hornlab_search.system import combine as comb  # noqa: E402
from hornlab_search.system import contracts as C  # noqa: E402
from hornlab_search.system import dsp as sys_dsp  # noqa: E402
from hornlab_search.system.score import flag_off_axis_cancellation  # noqa: E402


def _basis(**kw: Any) -> C.SourceBasis:
    defaults: dict[str, Any] = dict(
        per_input="normal_velocity_mps",
        distance_m=1.0,
        origin_xyz_m=(0.0, 0.0, 0.0),
        angular_frame="cartesian_dirs",
        source_geometry_hash="geom-a",
    )
    defaults.update(kw)
    return C.SourceBasis(**defaults)


def _response(freqs, fields: dict[str, np.ndarray], *,
              bases: dict[str, C.SourceBasis] | None = None,
              fidelity: str = "SCREEN_COMPLEX_APPROX",
              data_quality: dict[str, Any] | None = None,
              directions: np.ndarray | None = None) -> C.SystemResponse:
    names = tuple(fields)
    return C.SystemResponse(
        frequencies_hz=np.asarray(freqs, dtype=np.float64),
        excitation_names=names,
        p_by_excitation={name: np.asarray(arr, dtype=np.complex128)
                         for name, arr in fields.items()},
        excitation_bases=bases or {name: _basis() for name in names},
        p_total=None,
        magnitude_screen=None,
        observation_directions=directions,
        observation_angles_deg=None,
        fidelity=fidelity,
        data_quality=data_quality or {},
    )


# --------------------------------------------------------------------------- SYS-08 analytic

def test_two_equal_coherent_sources_sum_to_exactly_plus_six_db() -> None:
    f = np.array([1000.0])
    single = np.array([[2.0 + 1.0j]])            # one source, on axis, shape (nf, nobs)
    response = _response(f, {"horn": single, "woofer": single})
    out = comb.combine(response, {"horn": np.ones(1), "woofer": np.ones(1)},
                       {"horn": 1.0, "woofer": 1.0})
    assert out.p_total is not None
    np.testing.assert_allclose(out.p_total, 2.0 * single, rtol=0.0, atol=0.0)
    gain_db = 20.0 * math.log10(abs(out.p_total[0, 0]) / abs(single[0, 0]))
    assert gain_db == pytest.approx(20.0 * math.log10(2.0), rel=0.0, abs=1e-12)


def _two_source_geometry():
    """Return (freqs, directions, p_horn, p_woofer, k, d) with spatial phase already applied."""
    c = 343.0
    freq = 1000.0
    k = 2.0 * math.pi * freq / c
    d = 0.2
    step_deg = 0.05
    theta_deg = np.arange(0.0, 80.0 + 0.5 * step_deg, step_deg)
    theta = np.deg2rad(theta_deg)
    directions = np.stack([np.sin(theta), np.cos(theta), np.zeros_like(theta)], axis=1)
    r_horn = np.array([0.0, 0.0, 0.0])
    r_woofer = np.array([d, 0.0, 0.0])
    p0 = 0.7 + 0.2j
    p_horn = p0 * np.exp(-1j * k * (directions @ r_horn))
    p_woofer = p0 * np.exp(-1j * k * (directions @ r_woofer))
    return (np.array([freq]), directions, p_horn[None, :], p_woofer[None, :],
            k, d, theta_deg)


def test_first_destructive_interference_angle_matches_k_d_sin_theta_pi() -> None:
    freqs, directions, p_horn, p_woofer, k, d, theta_deg = _two_source_geometry()
    response = _response(freqs, {"horn": p_horn, "woofer": p_woofer}, directions=directions)

    # Delay factor comes from meh.dsp.delay: zero delay is exactly unity.
    zero_delay = meh_dsp.delay(freqs, 0.0)
    assert np.allclose(zero_delay, 1.0 + 0.0j)
    out = comb.combine(response, {"horn": zero_delay, "woofer": np.ones(1)},
                       {"horn": 1.0, "woofer": 1.0})
    total = out.p_total
    assert total is not None

    # On axis the two equal sources add (+6 dB); the first null is at k*d*sin(theta) = pi.
    assert abs(total[0, 0]) == pytest.approx(2.0 * abs(p_horn[0, 0]), rel=1e-12)
    predicted_deg = math.degrees(math.asin(math.pi / (k * d)))
    index = int(np.argmin(np.abs(total[0])))
    assert abs(theta_deg[index] - predicted_deg) <= 0.5 * (theta_deg[1] - theta_deg[0])
    assert abs(total[0, index]) < 0.02 * abs(total[0, 0])


def test_no_propagation_phase_is_applied_twice_by_combine() -> None:
    freqs, directions, p_horn, p_woofer, k, d, theta_deg = _two_source_geometry()
    response = _response(freqs, {"horn": p_horn, "woofer": p_woofer}, directions=directions)
    out = comb.combine(response, {"horn": np.ones(1), "woofer": np.ones(1)},
                       {"horn": 1.0, "woofer": 1.0})
    total = out.p_total
    assert total is not None
    index = int(np.argmin(np.abs(total[0])))
    correct_relative = abs(total[0, index]) / abs(total[0, 0])
    assert correct_relative < 0.02

    # A buggy combiner that re-applies the per-source propagation phase (a 1 m reference plus
    # the geometric path difference) visibly destroys the null. `combine` must not do this.
    theta = np.deg2rad(theta_deg)[index]
    r1 = 1.0
    r2 = 1.0 + d * math.sin(theta)
    wrong_at_null = (p_horn[0, index] * np.exp(-1j * k * r1)
                     + p_woofer[0, index] * np.exp(-1j * k * r2))
    wrong_relative = abs(wrong_at_null) / abs(total[0, 0])
    assert wrong_relative > 0.5
    assert correct_relative < 0.01 * wrong_relative


def test_woofer_polarity_flip_nulls_the_on_axis_sum() -> None:
    f = np.array([1000.0])
    single = np.array([[1.5 - 0.25j]])
    response = _response(f, {"horn": single, "woofer": single})
    bank = {"horn": np.ones(1), "woofer": meh_dsp.polarity(-1.0) * np.ones(1)}
    out = comb.combine(response, bank, {"horn": 1.0, "woofer": 1.0})
    assert out.p_total is not None
    np.testing.assert_allclose(out.p_total, 0.0 + 0.0j, atol=1e-15)


# --------------------------------------------------------------------------- phase honesty

def test_magnitude_only_response_is_refused_not_imputed() -> None:
    f = np.array([700.0, 1000.0])
    screen = C.SystemResponse(
        frequencies_hz=f,
        excitation_names=(),
        p_by_excitation=None,
        excitation_bases={},
        p_total=None,
        magnitude_screen=np.zeros((2, 3)),
        observation_directions=None,
        observation_angles_deg=None,
        fidelity="SCREEN_MAGNITUDE",
        data_quality={"quality": "MAGNITUDE_ONLY"},
    )
    with pytest.raises(C.PhaseUnavailable) as exc:
        comb.combine(screen, {}, {})
    message = str(exc.value)
    assert "MAGNITUDE_ONLY / PHASE_ALIGNMENT_UNAVAILABLE" in message
    assert "MAGNITUDE_ONLY" in message and "PHASE_ALIGNMENT_UNAVAILABLE" in message


def test_incompatible_bases_are_refused() -> None:
    f = np.array([1000.0])
    field = np.ones((1, 2), dtype=np.complex128)
    response = _response(
        f, {"horn": field, "woofer": field},
        bases={"horn": _basis(), "woofer": _basis(per_input="V_rms")})
    with pytest.raises(C.IncompatibleBasis, match="per_input"):
        comb.combine(response, {"horn": np.ones(1), "woofer": np.ones(1)},
                     {"horn": 1.0, "woofer": 1.0})


# --------------------------------------------------------------------------- SYS-15 recombine

def _recombine_fixture():
    freqs = np.array([500.0, 1000.0, 2000.0])
    nobs = 3
    rng = np.random.default_rng(7)
    fields = {
        "horn": (rng.normal(size=(3, nobs)) + 1j * rng.normal(size=(3, nobs))),
        "woofer": (rng.normal(size=(3, nobs)) + 1j * rng.normal(size=(3, nobs))),
    }
    response = _response(freqs, fields)
    point = C.DspPoint("LR4", 1000.0, -3.0, 1.5, 0.4, -1.0, ((900.0, 2.0, 1.0),))
    levels = {"horn": 1.0, "woofer": 0.5}
    return response, point, levels, fields, freqs


def test_recombine_with_dsp_matches_the_manual_sum() -> None:
    response, point, levels, fields, freqs = _recombine_fixture()
    out = comb.recombine_with_dsp(response, point, levels)
    bank = sys_dsp.filter_bank(point, freqs)
    manual = (fields["horn"] * bank["horn"][:, None] * levels["horn"]
              + fields["woofer"] * bank["woofer"][:, None] * levels["woofer"])
    assert out.p_total is not None
    np.testing.assert_allclose(out.p_total, manual, rtol=1e-14, atol=0.0)
    # A different point produces a genuinely different total (same bases).
    other = replace(point, xo_hz=1200.0)
    out2 = comb.recombine_with_dsp(response, other, levels)
    assert out2.p_total is not None
    assert not np.allclose(out2.p_total, out.p_total)


def test_recombine_is_pure_and_leaves_the_input_untouched() -> None:
    response, point, levels, fields, _ = _recombine_fixture()
    original = response.p_by_excitation
    assert original is not None
    before = {name: arr.copy() for name, arr in original.items()}
    assert response.p_total is None
    out_a = comb.recombine_with_dsp(response, point, levels)
    out_b = comb.recombine_with_dsp(response, point, levels)
    assert out_a.p_total is not None and out_b.p_total is not None
    np.testing.assert_array_equal(out_a.p_total, out_b.p_total)
    assert response.p_total is None
    for name, arr in before.items():
        np.testing.assert_array_equal(original[name], arr)
        np.testing.assert_array_equal(original[name], fields[name])
    assert out_a is not response


def test_recombine_cache_key_is_deterministic_and_sensitive() -> None:
    response, point, levels, fields, _ = _recombine_fixture()
    key = comb.recombine_cache_key(point, levels, response)
    assert key == comb.recombine_cache_key(point, levels, response)
    assert key == comb.recombine_cache_key(point, dict(reversed(list(levels.items()))),
                                           fields)
    assert len(key) == 16

    assert key != comb.recombine_cache_key(replace(point, xo_hz=1100.0), levels, response)
    assert key != comb.recombine_cache_key(point, {"horn": 0.9, "woofer": 0.5}, response)

    changed = dict(fields)
    changed["horn"] = changed["horn"] + 1e-9
    assert key != comb.recombine_cache_key(point, levels, changed)


def test_sys18_detector_feeds_a_refused_single_winner() -> None:
    freqs = np.geomspace(200.0, 5000.0, 400)
    on_axis = np.zeros_like(freqs)
    in_band = (freqs >= 1000.0 * 2.0 ** -0.5) & (freqs <= 1000.0 * 2.0 ** 0.5)
    off_axis = np.where(in_band, -12.0, 0.0)
    result = flag_off_axis_cancellation(
        {"on_axis": on_axis, "h=+20,v=0": off_axis, "h=-20,v=0": off_axis},
        freqs_hz=freqs, xo_hz=1000.0)
    assert result["status"] == "FAIL: vertical/oblique null"
    assert result["axis"] == "crossover_physics"
    assert result["worst_drop_db"] > 6.0
