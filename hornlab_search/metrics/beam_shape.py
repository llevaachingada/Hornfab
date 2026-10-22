"""Forward beam shape: superellipse fit to the -6 dB contour of the balloon.

Method after Boundary Lab's forward-beam-shape / CEA-2034 docs (idea only; independent implementation).
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import LinearNDInterpolator
from scipy.optimize import least_squares

_N_STEPS = 600


def band_mean(x, freqs, lo, hi) -> float:
    """nanmean of x over lo <= freqs <= hi (Hz); NaN if the band holds no finite value."""
    x = np.asarray(x, dtype=float)
    f = np.asarray(freqs, dtype=float)
    if x.shape != f.shape:
        raise ValueError(f"band_mean: x {x.shape} and freqs {f.shape} differ")
    v = x[(f >= lo) & (f <= hi)]
    v = v[np.isfinite(v)]
    return float(np.mean(v)) if v.size else float("nan")


def _superellipse(psi, a, b, p):
    c = np.abs(np.cos(psi) / a) ** p
    s = np.abs(np.sin(psi) / b) ** p
    return (c + s) ** (-1.0 / p)


def _contour_radii(interp, psi, level_db, rmax):
    """First -level crossing radius along each ray in the tangent plane, NaN if none."""
    r = np.linspace(0.0, rmax, _N_STEPS)
    u = r[None, :] * np.cos(psi)[:, None]
    v = r[None, :] * np.sin(psi)[:, None]
    val = interp(u, v)                                   # (n_rays, n_steps)
    bad = np.isnan(val)
    hit = (val <= level_db) & ~bad
    stop = hit | bad
    out = np.full(psi.size, np.nan)
    has = stop.any(axis=1)
    first = np.argmax(stop, axis=1)
    for k in np.nonzero(has)[0]:
        j = first[k]
        if bad[k, j] or j == 0:
            continue
        v0, v1 = val[k, j - 1], val[k, j]
        t = (level_db - v0) / (v1 - v0) if v1 != v0 else 1.0
        out[k] = r[j - 1] + t * (r[j] - r[j - 1])
    return out


def _fit_one(psi, rad):
    a0 = max(float(np.mean(rad[[0, rad.size // 2]])), 1e-3)
    b0 = max(float(np.mean(rad[[rad.size // 4, 3 * rad.size // 4]])), 1e-3)

    def res(q):
        return _superellipse(psi, q[0], q[1], q[2]) - rad

    sol = least_squares(res, [a0, b0, 2.0], bounds=([1e-4, 1e-4, 1.0], [1e3, 1e3, 12.0]))
    a, b, p = sol.x
    rms = float(np.sqrt(np.mean(sol.fun ** 2)))
    return a, b, p, 100.0 * rms / float(np.mean(rad))


def forward_beam_shape(dirs, spl_db, *, on_axis_db=None, level_db=-6.0,
                       max_angle_deg=89.0, n_rays=72) -> dict:
    """Superellipse exponent of the forward -6 dB contour, per frequency.

    Coordinates: forward axis +Z, tangent plane u = x/z, v = y/z. SPL is normalized to
    the on-axis level (``on_axis_db[i]`` if given, else the balloon sample with the
    largest z). The contour r(psi) is found by marching along n_rays rays and is fitted
    by r(psi) = (|cos psi/a|^p + |sin psi/b|^p)^(-1/p), p in [1, 12].

    p = 2 is an ellipse (circle if a == b), p ~ 4 a rounded square, p -> large a square.
    Report-only diagnostic; do not optimise against it.

    Parameters
    ----------
    dirs : (nb, 3) unit vectors; spl_db : (nf, nb) absolute dB.

    Returns
    -------
    dict of (nf,) arrays: ``p``, ``residual_pct`` (100*rms(r - model)/mean(r)),
    ``half_width_h_deg`` = atan(a), ``half_width_v_deg`` = atan(b). All NaN for a
    frequency where any ray never crosses level_db below max_angle_deg (beam wider
    than the cap) or the interpolation is undefined.
    """
    d = np.asarray(dirs, dtype=float)
    s = np.asarray(spl_db, dtype=float)
    if d.ndim != 2 or d.shape[1] != 3:
        raise ValueError(f"forward_beam_shape: dirs has shape {d.shape}, expected (nb, 3)")
    if s.ndim != 2 or s.shape[1] != d.shape[0]:
        raise ValueError(f"forward_beam_shape: spl_db has shape {s.shape}, expected (nf, {d.shape[0]})")
    nf = s.shape[0]
    on = None
    if on_axis_db is not None:
        on = np.asarray(on_axis_db, dtype=float).ravel()
        if on.shape != (nf,):
            raise ValueError(f"forward_beam_shape: on_axis_db has shape {on.shape}, expected ({nf},)")

    out = {k: np.full(nf, np.nan) for k in ("p", "residual_pct", "half_width_h_deg", "half_width_v_deg")}
    z = d[:, 2]
    cos_max = np.cos(np.radians(max_angle_deg))
    fwd = z >= max(cos_max, 1e-9)
    if fwd.sum() < 4:
        return out
    ax_idx = int(np.argmax(z))
    pts = np.column_stack([d[fwd, 0] / z[fwd], d[fwd, 1] / z[fwd]])
    key = np.round(pts, 9)
    _, uniq = np.unique(key, axis=0, return_index=True)   # poles of a theta-phi grid repeat
    uniq = np.sort(uniq)
    pts = pts[uniq]
    fwd_idx = np.nonzero(fwd)[0][uniq]
    rmax = float(np.tan(np.radians(max_angle_deg)))
    psi = np.linspace(0.0, 2.0 * np.pi, int(n_rays), endpoint=False)

    for i in range(nf):
        ref = on[i] if on is not None else s[i, ax_idx]
        vals = s[i, fwd_idx] - ref
        if not np.all(np.isfinite(vals)):
            continue
        try:
            interp = LinearNDInterpolator(pts, vals)
            rad = _contour_radii(interp, psi, level_db, rmax)
            if not np.all(np.isfinite(rad)):
                continue
            a, b, p, rp = _fit_one(psi, rad)
        except Exception:   # degenerate geometry (qhull) or fit failure: NaN, never raise
            continue
        out["p"][i] = p
        out["residual_pct"][i] = rp
        out["half_width_h_deg"][i] = np.degrees(np.arctan(a))
        out["half_width_v_deg"][i] = np.degrees(np.arctan(b))
    return out
