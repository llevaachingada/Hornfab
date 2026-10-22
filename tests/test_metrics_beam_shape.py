"""Forward beam shape superellipse fit."""
from __future__ import annotations

import numpy as np
import pytest

from hornlab_search.metrics.beam_shape import band_mean, forward_beam_shape


def fibonacci(n):
    i = np.arange(n) + 0.5
    z = 1 - 2 * i / n
    r = np.sqrt(1 - z * z)
    phi = np.pi * (1 + 5 ** 0.5) * i
    return np.column_stack([r * np.cos(phi), r * np.sin(phi), z])


def theta_phi(nt, nph):
    th = np.radians(np.linspace(0, 180, nt))
    ph = np.linspace(0, 2 * np.pi, nph, endpoint=False)
    T, P = np.meshgrid(th, ph, indexing="ij")
    return np.column_stack([(np.sin(T) * np.cos(P)).ravel(), (np.sin(T) * np.sin(P)).ravel(),
                            np.cos(T).ravel()])


def synth(dirs, p, a, b, offset=0.0):
    z = np.where(dirs[:, 2] > 1e-6, dirs[:, 2], np.nan)
    u, v = dirs[:, 0] / z, dirs[:, 1] / z
    lvl = -6.0 * (np.abs(u / a) ** p + np.abs(v / b) ** p) ** (1.0 / p)
    lvl = np.where(np.isnan(lvl), -80.0, np.maximum(lvl, -80.0))   # back hemisphere: quiet
    return (lvl + offset)[None, :]


CASES = [(2, np.tan(np.radians(40)), np.tan(np.radians(40))),
         (4, np.tan(np.radians(45)), np.tan(np.radians(30))),
         (8, np.tan(np.radians(35)), np.tan(np.radians(35)))]

# measured tolerances, see report: Fibonacci 3000 pts and 91x72 grid
# Fibonacci: linear interpolation rounds the corners (p=8 reads 7.4, half widths ~+1 deg).
TOL_P_FIB, TOL_P_GRID, TOL_DEG, TOL_RES = 0.7, 0.1, 1.5, 2.0


@pytest.mark.parametrize("kind", ["fib", "grid"])
@pytest.mark.parametrize("p,a,b", CASES)
def test_recovers_parameters(kind, p, a, b):
    dirs = fibonacci(3000) if kind == "fib" else theta_phi(91, 72)
    r = forward_beam_shape(dirs, synth(dirs, p, a, b))
    tol = TOL_P_FIB if kind == "fib" else TOL_P_GRID
    assert abs(r["p"][0] - p) < tol
    assert abs(r["half_width_h_deg"][0] - np.degrees(np.arctan(a))) < TOL_DEG
    assert abs(r["half_width_v_deg"][0] - np.degrees(np.arctan(b))) < TOL_DEG
    assert r["residual_pct"][0] < TOL_RES


def test_offset_invariance_with_on_axis_db():
    dirs = fibonacci(3000)
    p, a, b = CASES[1]
    r0 = forward_beam_shape(dirs, synth(dirs, p, a, b))
    r1 = forward_beam_shape(dirs, synth(dirs, p, a, b, offset=17.0), on_axis_db=[17.0])
    r2 = forward_beam_shape(dirs, synth(dirs, p, a, b, offset=17.0))
    assert r1["p"][0] == pytest.approx(r0["p"][0], abs=0.05)  # r0 uses nearest-axis sample, not exact 0 dB
    assert r2["p"][0] == pytest.approx(r0["p"][0], abs=0.05)


def test_wide_beam_is_nan_and_multi_freq():
    dirs = fibonacci(3000)
    wide = synth(dirs, 2, np.tan(np.radians(88.5)) * 3, np.tan(np.radians(88.5)) * 3)
    ok = synth(dirs, *CASES[0])
    r = forward_beam_shape(dirs, np.vstack([wide, ok]))
    assert np.isnan(r["p"][0]) and np.isnan(r["half_width_h_deg"][0])
    assert np.isfinite(r["p"][1])


def test_shape_errors():
    dirs = fibonacci(100)
    with pytest.raises(ValueError):
        forward_beam_shape(dirs[:, :2], np.zeros((1, 100)))
    with pytest.raises(ValueError):
        forward_beam_shape(dirs, np.zeros((1, 99)))
    with pytest.raises(ValueError):
        forward_beam_shape(dirs, np.zeros((1, 100)), on_axis_db=[0.0, 1.0])


def test_band_mean():
    f = np.array([100.0, 200.0, 300.0, 400.0])
    x = np.array([1.0, np.nan, 3.0, 9.0])
    assert band_mean(x, f, 100, 300) == pytest.approx(2.0)
    assert np.isnan(band_mean(x, f, 1000, 2000))


def test_coarse_balloon_noise():
    """512-point screen-mode scale (measured errors: grid p<=1.1, fib p<=2.5): p is biased low
    for square-ish beams; half widths stay usable on the grid, ~2.6 deg high on Fibonacci."""
    for dirs, tp, thw in [(theta_phi(16, 32), 1.5, 1.0), (fibonacci(512), 2.7, 3.0)]:
        for p, a, b in CASES:
            r = forward_beam_shape(dirs, synth(dirs, p, a, b))
            assert abs(r["p"][0] - p) < tp
            assert abs(r["half_width_h_deg"][0] - np.degrees(np.arctan(a))) < thw
