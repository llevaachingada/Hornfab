"""Constant-directivity (CD) metrics from Sridhar, Tylka & Choueiri, JAES 67(9):666-678, 2019.

Spec and exact equations: ``docs/research/cd_metrics_2026-11-20/V11_CD_MATRIX.md`` section 1.1.
Everything here is pure numpy over already-stored arrays. No solver, no GPU, no file I/O.

Metrics implemented
-------------------
* **M2** listening-window distortion ``C_LW``  -> :func:`listening_window_metrics` /
  :func:`cd_metrics` (``cd_lw_db``).
* **M3** forward clean-region solid angle ``Omega_CD`` -> ``cd_omega_2pi`` / ``omega_cd_2pi``.
* **M4** log-frequency-weighted DI standard deviation ``sigma_DI`` -> :func:`di_std_log_db`.
* **M5** mean normalised aligned cross-correlation ``Phi_bar`` -> :func:`nacc_mean`.

Conventions (read before using the numbers)
-------------------------------------------
* Powers, not dB, are averaged: ``P = 10**(SPL/10)``. Non-finite SPL is floored at ``1e-12`` so a
  dead sample can never turn a metric into ``nan``.
* Band weights are trapezoid weights in ``log10(f)`` over the selected samples, normalised to sum
  to 1. A band with fewer than two usable samples refuses (``ValueError`` for the public weight
  helper; ``nan`` inside the higher-level metrics).
* ``balloon_grid`` is the solver's structured ``[n_theta, n_phi]`` theta-major grid
  (``solve/base.py``). The M3 region is an axis-connected flood fill on that grid, with phi
  wrapping. Area weights are ``sin(theta)`` normalised over the whole balloon.
* M3/Oomega convention (spec 1.1): ``Omega_CD = 4*pi * sum_region w`` with ``w`` normalised over
  the FULL sphere, so an omni source restricted to its forward hemisphere reads
  ``Omega_CD = 2*pi`` and ``omega_cd_2pi = Omega_CD/(2*pi) = 1``.
* Missing or short arrays never raise from :func:`cd_metrics`; they return ``nan`` and a status.
  Structural shape errors (wrong array rank, balloon/direction mismatch) do raise ``ValueError``.
"""
from __future__ import annotations

from collections import deque

import numpy as np

#: Power floor for a non-finite SPL sample (spec: non-finite floored at 1e-12).
FLOOR_POWER = 1e-12

#: Default score band (M2-M4) for the v11 CD block.
DEFAULT_BAND_HZ = (700.0, 8000.0)

#: Default HF off-axis reporting band (spec section 2).
DEFAULT_OFFAXIS_BAND_HZ = (2500.0, 8000.0)


# --------------------------------------------------------------------------- primitives


def power_from_spl_db(spl_db):
    """``10**(spl/10)``; every non-finite value (NaN or +-inf) becomes :data:`FLOOR_POWER`."""
    s = np.asarray(spl_db, dtype=float)
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        p = 10.0 ** (s / 10.0)
    if not np.all(np.isfinite(p)):
        p = np.where(np.isfinite(p), p, FLOOR_POWER)
    return p


def log_frequency_weights(freqs_hz, band_mask=None):
    """Trapezoid weights in ``log10(f)`` over the selected samples, normalised to sum to 1.

    Returns an array shaped like ``freqs_hz``: selected samples carry their normalised weight,
    everything else is 0. A sample is selected when the mask is true, the frequency is finite and
    positive, and (for interior weights) the log-spacing is strictly positive.

    Raises ``ValueError`` for a non-1-D frequency array, a mask with the wrong shape, or fewer
    than two selected samples. The two-point case is equal weights (0.5 each).
    """
    f = np.asarray(freqs_hz, dtype=float)
    if f.ndim != 1:
        raise ValueError(f"log_frequency_weights: freqs_hz must be 1-D, got shape {f.shape}")
    if band_mask is None:
        mask = np.ones(f.shape, dtype=bool)
    else:
        mask = np.asarray(band_mask, dtype=bool)
        if mask.shape != f.shape:
            raise ValueError(
                f"log_frequency_weights: band_mask {mask.shape} does not match freqs {f.shape}")
    sel = mask & np.isfinite(f) & (f > 0.0)
    n = int(np.count_nonzero(sel))
    if n < 2:
        raise ValueError(
            f"log_frequency_weights: need >= 2 selected positive finite frequencies, got {n}")

    lf = np.log10(f[sel])
    gaps = np.diff(lf)
    if np.any(gaps <= 0.0):
        raise ValueError(
            "log_frequency_weights: selected frequencies must be strictly increasing")
    w = np.empty(n, dtype=float)
    if n == 2:
        w[:] = 0.5
    else:
        w[0] = 0.5 * (lf[1] - lf[0])
        w[-1] = 0.5 * (lf[-1] - lf[-2])
        w[1:-1] = 0.5 * (lf[2:] - lf[:-2])
    total = float(w.sum())
    if not total > 0.0:
        raise ValueError("log_frequency_weights: degenerate log-frequency span")
    out = np.zeros(f.shape, dtype=float)
    out[sel] = w / total
    return out


def _band_mask(freqs_hz, band_hz):
    lo, hi = float(band_hz[0]), float(band_hz[1])
    return (freqs_hz >= lo) & (freqs_hz <= hi)


def di_std_log_db(freqs_hz, di_db, band_hz=DEFAULT_BAND_HZ):
    """M4: log-frequency-weighted standard deviation of DI over ``band_hz``.

    ``sigma_DI = sqrt(sum_k w_k (DI_k - mean_w)^2 / sum_k w_k)`` with ``w_k`` the trapezoid
    weights in ``log10(f)``. Only finite DI samples inside the band are used. Returns ``nan`` when
    fewer than three usable samples remain.
    """
    f = np.asarray(freqs_hz, dtype=float)
    d = np.asarray(di_db, dtype=float)
    if f.ndim != 1 or d.ndim != 1:
        raise ValueError(
            f"di_std_log_db: freqs_hz and di_db must be 1-D, got {f.shape} and {d.shape}")
    if f.shape != d.shape:
        raise ValueError(
            f"di_std_log_db: freqs_hz {f.shape} and di_db {d.shape} must have the same shape")
    use = _band_mask(f, band_hz) & np.isfinite(f) & np.isfinite(d) & (f > 0.0)
    if int(np.count_nonzero(use)) < 3:
        return float("nan")
    try:
        w = log_frequency_weights(f, use)
    except ValueError:
        return float("nan")
    df = d[use]
    wf = w[use]
    sw = float(wf.sum())
    if not sw > 0.0:
        return float("nan")
    mean = float(np.sum(wf * df) / sw)
    var = float(np.sum(wf * (df - mean) ** 2) / sw)
    return float(np.sqrt(max(var, 0.0)))


# --------------------------------------------------------------------------- M5


def nacc_matrix(spl_db, angles_deg):
    """M5: normalised aligned cross-correlation of one plane's POWER polar responses.

    ``Phi[k, k'] = sum_n P[k,n] P[k',n] / sqrt(sum_n P[k,n]^2 sum_n P[k',n]^2)`` with
    ``P = 10**(spl/10)``. The diagonal is set to exactly 1.0. Rows with zero power (impossible for
    finite input after the 1e-12 floor) would be ``nan`` off-diagonal.

    ``angles_deg`` is validated against the column count; it does not enter the correlation.
    """
    s = np.asarray(spl_db, dtype=float)
    a = np.asarray(angles_deg, dtype=float).ravel()
    if s.ndim != 2:
        raise ValueError(f"nacc_matrix: spl_db must be 2-D (nf, na), got shape {s.shape}")
    if s.shape[1] != a.size:
        raise ValueError(
            f"nacc_matrix: spl_db has {s.shape[1]} angles but angles_deg has {a.size}")
    p = power_from_spl_db(s)
    nf = p.shape[0]
    out = np.full((nf, nf), np.nan, dtype=float)
    if nf == 0:
        return out
    norm = np.sqrt(np.sum(p * p, axis=1))
    good = norm > 0.0
    if np.any(good):
        idx = np.flatnonzero(good)
        a_norm = p[good] / norm[good, None]
        m = a_norm @ a_norm.T
        out[np.ix_(idx, idx)] = np.clip(m, -1.0, 1.0)
    np.fill_diagonal(out, 1.0)
    return out


def nacc_mean(freqs_hz, spl_h_db, spl_v_db, h_angles_deg, v_angles_deg,
              band_hz=DEFAULT_BAND_HZ):
    """M5 mean ``Phi_bar`` over all in-band frequency pairs of the H/V-averaged matrix.

    Returns ``{"nacc", "matrix_h", "matrix_v", "n_pairs"}``. ``matrix_h``/``matrix_v`` are full
    ``(nf, nf)`` matrices. ``nacc`` is ``sum_kk' w_k w_k' Phi[k,k'] / sum_kk' w_k w_k'`` over the
    finite in-band pairs; ``n_pairs`` is how many pairs contributed. Fewer than two in-band
    frequencies (or mismatched array lengths) returns ``nacc = nan`` and ``n_pairs = 0``.
    """
    f = np.asarray(freqs_hz, dtype=float)
    if f.ndim != 1:
        raise ValueError(f"nacc_mean: freqs_hz must be 1-D, got shape {f.shape}")
    mh = nacc_matrix(spl_h_db, h_angles_deg)
    mv = nacc_matrix(spl_v_db, v_angles_deg)
    out = {"nacc": float("nan"), "matrix_h": mh, "matrix_v": mv, "n_pairs": 0}
    if mh.shape != mv.shape or mh.shape[0] != f.size:
        return out
    phi = 0.5 * (mh + mv)
    band = _band_mask(f, band_hz) & np.isfinite(f) & (f > 0.0)
    if int(np.count_nonzero(band)) < 2:
        return out
    try:
        w = log_frequency_weights(f, band)
    except ValueError:
        return out
    ww = np.outer(w, w)
    use = np.isfinite(phi) & (ww > 0.0)
    if not np.any(use):
        return out
    denom = float(ww[use].sum())
    if not denom > 0.0:
        return out
    out["nacc"] = float(np.sum(ww[use] * phi[use]) / denom)
    out["n_pairs"] = int(np.count_nonzero(use))
    return out


# --------------------------------------------------------------------------- balloon helpers


def _dirs_geometry(balloon_dirs):
    """``(x, y, z, theta_deg)`` for an ``(n, 3)`` direction array (unit-normalised)."""
    d = np.asarray(balloon_dirs, dtype=float)
    if d.ndim != 2 or d.shape[1] != 3:
        raise ValueError(f"balloon_dirs must be (n, 3), got shape {d.shape}")
    norm = np.linalg.norm(d, axis=1, keepdims=True)
    unit = d / np.where(norm > 0.0, norm, 1.0)
    x, y, z = unit[:, 0], unit[:, 1], unit[:, 2]
    theta = np.degrees(np.arccos(np.clip(z, -1.0, 1.0)))
    return x, y, z, theta


def _window_lw(P, band_w, axis_idx, window_mask, window_w):
    """M2 core. Returns ``(lw_db, per_freq_lw_db)``; ``nan`` where undefined.

    ``P`` is power ``(nf, nd)``; ``band_w`` is a full-length log-frequency weight vector
    (0 outside the band); ``window_w`` is the per-direction area weight (0 outside the window).
    """
    nf, nd = P.shape
    per = np.full(nf, np.nan, dtype=float)
    lw = float("nan")
    if axis_idx is None or nd == 0:
        return lw, per
    pbar = band_w @ P
    if not np.isfinite(pbar[axis_idx]) or pbar[axis_idx] <= 0.0:
        return lw, per
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        ratio = (np.sqrt(P / pbar[None, :])
                 / np.sqrt(P[:, axis_idx] / pbar[axis_idx])[:, None])
        E = 10.0 ** np.abs(np.log10(ratio))
    denom = float(np.sum(window_w))
    if not denom > 0.0:
        return lw, per
    C2 = (E * E) @ window_w / denom
    with np.errstate(divide="ignore", invalid="ignore"):
        per = 10.0 * np.log10(C2)
        num = float(band_w @ C2)
        lw = float(10.0 * np.log10(num)) if (np.isfinite(num) and num > 0.0) else float("nan")
    return lw, per


def _omega_forward_region(E, theta_deg, grid, area_w, e_star):
    """M3 per-frequency ``Omega_CD/(2*pi)`` by axis-connected flood fill on a theta-major grid.

    ``area_w`` is ``sin(theta)`` normalised over the whole balloon (sums to 1). Since
    ``Omega_CD = 4*pi * sum_region w``, the returned value is ``2 * sum_region w``.
    Returns ``None`` if the grid does not describe the balloon.
    """
    nf, nb = E.shape
    try:
        n_t, n_p = int(grid[0]), int(grid[1])
    except (TypeError, ValueError, IndexError):
        return None
    if n_t * n_p != nb or n_t < 2 or n_p < 2:
        return None
    total_w = float(np.sum(area_w))
    if not total_w > 0.0:
        return None

    e3 = E.reshape(nf, n_t, n_p)
    th3 = np.reshape(theta_deg, (n_t, n_p))
    w3 = np.reshape(area_w, (n_t, n_p))
    forward = th3 <= 90.0
    row_theta = th3[:, 0]
    i0 = int(np.argmin(row_theta))

    allowed_all = forward[None, :, :] & (e3 <= e_star)
    out = np.full(nf, np.nan, dtype=float)
    for k in range(nf):
        allowed = allowed_all[k]
        if not np.any(allowed[i0]):
            continue
        visited = np.zeros((n_t, n_p), dtype=bool)
        q = deque()
        for j in range(n_p):
            if allowed[i0, j]:
                visited[i0, j] = True
                q.append((i0, j))
        while q:
            i, j = q.popleft()
            if i > 0 and allowed[i - 1, j] and not visited[i - 1, j]:
                visited[i - 1, j] = True
                q.append((i - 1, j))
            if i + 1 < n_t and allowed[i + 1, j] and not visited[i + 1, j]:
                visited[i + 1, j] = True
                q.append((i + 1, j))
            jm = (j - 1) % n_p
            jp = (j + 1) % n_p
            if allowed[i, jm] and not visited[i, jm]:
                visited[i, jm] = True
                q.append((i, jm))
            if allowed[i, jp] and not visited[i, jp]:
                visited[i, jp] = True
                q.append((i, jp))
        out[k] = 2.0 * float(np.sum(w3[visited])) / total_w
    return out


# --------------------------------------------------------------------------- M2 + M3 public


def listening_window_metrics(spl_balloon_db, balloon_dirs, grid, freqs_hz,
                             band_hz=DEFAULT_BAND_HZ, window_h_deg=30.0,
                             window_v_deg=10.0, e_star_3db=10.0 ** (3.0 / 20.0)):
    """M2 (listening-window distortion) and M3 (forward clean-region solid angle) from a balloon.

    Parameters
    ----------
    spl_balloon_db : 2-D array ``(nf, nb)`` or ``None``
    balloon_dirs : 2-D array ``(nb, 3)`` or ``None``
    grid : ``[n_theta, n_phi]`` or ``None`` — ``Response.meta['balloon_grid']``. Without it the
        M2 value is still computed (it needs no structure) but M3 is ``nan``.
    freqs_hz : 1-D array ``(nf,)``
    band_hz, window_h_deg, window_v_deg : score band and CTA-2034 listening window
    e_star_3db : M3 threshold ``10**(3/20)`` (3 dB amplitude).

    Returns
    -------
    dict
        ``lw_distortion_db`` (M2, dB), ``omega_cd_2pi`` (M3, ``Omega_CD/(2*pi)``),
        ``n_dirs``, ``status`` (``"balloon"`` or ``"unmeasurable"``),
        ``per_freq_lw_db`` and ``per_freq_omega_2pi`` (full-length, ``nan`` where undefined).

    The listening-window mask is ``(theta_h/window_h)^2 + (theta_v/window_v)^2 <= 1`` with
    ``theta_h = atan2(x, z)`` and ``theta_v = atan2(y, z)``. Window directions are weighted by
    ``sin(theta)``.
    """
    f = np.asarray(freqs_hz, dtype=float)
    out = {
        "lw_distortion_db": float("nan"),
        "omega_cd_2pi": float("nan"),
        "n_dirs": 0,
        "status": "unmeasurable",
        "per_freq_lw_db": np.array([], dtype=float),
        "per_freq_omega_2pi": np.array([], dtype=float),
    }
    if spl_balloon_db is None or balloon_dirs is None:
        return out

    s = np.asarray(spl_balloon_db, dtype=float)
    if s.ndim == 1:
        s = s[None, :]
    if s.ndim != 2:
        raise ValueError(f"listening_window_metrics: spl_balloon_db must be 2-D, got {s.shape}")
    d = np.asarray(balloon_dirs, dtype=float)
    if d.ndim != 2 or d.shape[1] != 3:
        raise ValueError(f"listening_window_metrics: balloon_dirs must be (n, 3), got {d.shape}")
    if s.shape[1] != d.shape[0]:
        raise ValueError(
            f"listening_window_metrics: balloon levels have {s.shape[1]} directions, "
            f"dirs has {d.shape[0]}")
    if f.ndim != 1:
        raise ValueError(
            f"listening_window_metrics: freqs_hz must be 1-D, got shape {f.shape}")
    if s.shape[0] != f.size:
        raise ValueError(
            f"listening_window_metrics: {s.shape[0]} frequency rows but {f.size} frequencies")

    nb = s.shape[1]
    nf = s.shape[0]
    out["n_dirs"] = nb
    out["per_freq_lw_db"] = np.full(nf, np.nan, dtype=float)
    out["per_freq_omega_2pi"] = np.full(nf, np.nan, dtype=float)

    band = _band_mask(f, band_hz) & np.isfinite(f) & (f > 0.0)
    if int(np.count_nonzero(band)) < 2 or nb < 2:
        return out
    try:
        band_w = log_frequency_weights(f, band)
    except ValueError:
        return out

    P = power_from_spl_db(s)
    x, y, z, theta = _dirs_geometry(d)
    sin_w = np.sin(np.radians(theta))
    axis_idx = int(np.argmax(z))

    th_h = np.degrees(np.arctan2(x, z))
    th_v = np.degrees(np.arctan2(y, z))
    window_mask = (th_h / float(window_h_deg)) ** 2 + (th_v / float(window_v_deg)) ** 2 <= 1.0
    window_w = np.where(window_mask, sin_w, 0.0)

    lw, per_lw = _window_lw(P, band_w, axis_idx, window_mask, window_w)
    out["lw_distortion_db"] = lw
    out["per_freq_lw_db"] = per_lw

    sw = float(np.sum(sin_w))
    if sw > 0.0:
        area_w = sin_w / sw
        omega_per = _omega_forward_region(
            _window_E(P, band_w, axis_idx), theta, grid, area_w, float(e_star_3db))
        if omega_per is not None:
            out["per_freq_omega_2pi"] = omega_per
            use = np.isfinite(omega_per) & (band_w > 0.0)
            if np.any(use):
                wsum = float(np.sum(band_w[use]))
                if wsum > 0.0:
                    out["omega_cd_2pi"] = float(
                        np.sum(band_w[use] * omega_per[use]) / wsum)

    out["status"] = "balloon"
    return out


def _window_E(P, band_w, axis_idx):
    """Per-sample M2 distortion factor ``E = 10**|log10 D|`` for a power array.

    Shared by M2 and M3: M3's clean region is the set where this ``E`` is <= the 3 dB threshold.
    """
    pbar = band_w @ P
    if not np.isfinite(pbar[axis_idx]) or pbar[axis_idx] <= 0.0:
        return np.full(P.shape, np.inf, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        ratio = (np.sqrt(P / pbar[None, :])
                 / np.sqrt(P[:, axis_idx] / pbar[axis_idx])[:, None])
        return 10.0 ** np.abs(np.log10(ratio))


# --------------------------------------------------------------------------- cuts fallback


def _lw_from_cuts(f, spl_h, spl_v, h_angles, v_angles, band_hz, window_h_deg, window_v_deg):
    """M2 applied to the H/V cuts inside the listening window (no-balloon fallback).

    H samples map to ``(sin a, 0, cos a)`` and V samples to ``(0, sin a, cos a)`` so the same
    elliptical window test and ``sin(theta)`` weighting apply. Returns ``nan`` on an unusable cut.
    """
    h = np.asarray(spl_h, dtype=float)
    v = np.asarray(spl_v, dtype=float)
    ha = np.asarray(h_angles, dtype=float).ravel()
    va = np.asarray(v_angles, dtype=float).ravel()
    if h.ndim != 2 or v.ndim != 2:
        return float("nan")
    if h.shape[0] != f.size or v.shape[0] != f.size:
        return float("nan")
    if h.shape[1] != ha.size or v.shape[1] != va.size:
        return float("nan")

    sel_h = np.isfinite(ha) & (np.abs(ha) <= float(window_h_deg) + 1e-12)
    sel_v = np.isfinite(va) & (np.abs(va) <= float(window_v_deg) + 1e-12)
    cols = np.concatenate([h[:, sel_h], v[:, sel_v]], axis=1)
    if cols.shape[1] == 0:
        return float("nan")
    th = np.concatenate([np.abs(ha[sel_h]), np.abs(va[sel_v])])

    band = _band_mask(f, band_hz) & np.isfinite(f) & (f > 0.0)
    if int(np.count_nonzero(band)) < 2:
        return float("nan")
    try:
        band_w = log_frequency_weights(f, band)
    except ValueError:
        return float("nan")

    sin_w = np.sin(np.radians(th))
    den = float(np.sum(sin_w))
    if not den > 0.0:
        return float("nan")
    axis_idx = int(np.argmin(th))
    P = power_from_spl_db(cols)
    lw, _per = _window_lw(P, band_w, axis_idx, np.ones(cols.shape[1], dtype=bool), sin_w)
    return lw


# --------------------------------------------------------------------------- aggregate


def _attr(obj, name, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def cd_metrics(metrics, resp, band_hz=DEFAULT_BAND_HZ, window_h_deg=30.0,
               window_v_deg=10.0, offaxis_band_hz=DEFAULT_OFFAXIS_BAND_HZ,
               offaxis_angles_h_deg=(-40.0, -30.0, 30.0, 40.0),
               offaxis_angles_v_deg=(-25.0, -10.0, 10.0, 25.0),
               offaxis_reference="band_mean"):
    """All v11 CD terms for one response.

    Returns ``{"cd_lw_db", "cd_omega_2pi", "cd_di_std_db", "cd_nacc", "offaxis_smooth_db",
    "cd_status"}``.

    * ``cd_di_std_db`` — M4 from ``metrics.di_db``.
    * ``cd_nacc``       — M5 from ``resp.spl_h_db`` / ``resp.spl_v_db``.
    * ``cd_lw_db`` / ``cd_omega_2pi`` — M2/M3 from the balloon when present. Without a balloon
      the level term falls back to the H/V cuts inside the listening window
      (``cd_status="cuts_fallback"``) and ``cd_omega_2pi`` is ``nan``.
    * ``offaxis_smooth_db`` — worst band-mean fixed-angle residual over the declared H and V
      angles (missing angle samples are skipped; ``nan`` if none is usable).

    Never raises on missing/short arrays: those yield ``nan`` plus a status. Real shape errors
    (wrong array rank) raise ``ValueError``.
    """
    out = {
        "cd_lw_db": float("nan"),
        "cd_omega_2pi": float("nan"),
        "cd_di_std_db": float("nan"),
        "cd_nacc": float("nan"),
        "offaxis_smooth_db": float("nan"),
        "cd_status": "unmeasurable",
    }

    f = _attr(metrics, "freqs_hz")
    if f is None:
        f = _attr(resp, "freqs_hz")
    if f is None:
        return out
    f = np.asarray(f, dtype=float)
    if f.ndim != 1:
        raise ValueError(f"cd_metrics: freqs_hz must be 1-D, got shape {f.shape}")
    f = f.ravel()

    # ---- M4
    di = _attr(metrics, "di_db")
    if di is not None:
        di = np.asarray(di, dtype=float).ravel()
        if di.size == f.size:
            out["cd_di_std_db"] = di_std_log_db(f, di, band_hz)

    # ---- M5 + cuts pieces
    h_angles = _attr(resp, "h_angles_deg")
    v_angles = _attr(resp, "v_angles_deg")
    spl_h = _attr(resp, "spl_h_db")
    spl_v = _attr(resp, "spl_v_db")

    h_ok = False
    v_ok = False
    if h_angles is not None and spl_h is not None:
        ha = np.asarray(h_angles, dtype=float).ravel()
        sh = np.asarray(spl_h, dtype=float)
        h_ok = sh.ndim == 2 and sh.shape == (f.size, ha.size)
    else:
        ha = np.array([], dtype=float)
    if v_angles is not None and spl_v is not None:
        va = np.asarray(v_angles, dtype=float).ravel()
        sv = np.asarray(spl_v, dtype=float)
        v_ok = sv.ndim == 2 and sv.shape == (f.size, va.size)
    else:
        va = np.array([], dtype=float)

    if h_ok and v_ok:
        try:
            out["cd_nacc"] = nacc_mean(f, spl_h, spl_v, ha, va, band_hz)["nacc"]
        except ValueError:
            out["cd_nacc"] = float("nan")

    # ---- M2/M3 from the balloon, else the cuts fallback
    ball = _attr(resp, "spl_balloon_db")
    dirs = _attr(resp, "balloon_dirs")
    grid = None
    meta = _attr(resp, "meta") or {}
    if isinstance(meta, dict):
        grid = meta.get("balloon_grid")

    use_balloon = False
    if ball is not None and dirs is not None:
        b = np.asarray(ball, dtype=float)
        d = np.asarray(dirs, dtype=float)
        if b.ndim == 2 and d.ndim == 2 and d.shape[1] == 3 \
                and b.shape[0] == f.size and b.shape[1] == d.shape[0]:
            use_balloon = True

    if use_balloon:
        lwm = listening_window_metrics(
            ball, dirs, grid, f, band_hz=band_hz,
            window_h_deg=window_h_deg, window_v_deg=window_v_deg)
        out["cd_lw_db"] = lwm["lw_distortion_db"]
        out["cd_omega_2pi"] = lwm["omega_cd_2pi"]
        out["cd_status"] = "balloon" if lwm["status"] == "balloon" else "unmeasurable"
    elif h_ok and v_ok:
        out["cd_lw_db"] = _lw_from_cuts(
            f, spl_h, spl_v, ha, va, band_hz, window_h_deg, window_v_deg)
        out["cd_omega_2pi"] = float("nan")
        out["cd_status"] = "cuts_fallback"

    # ---- off-axis fixed-angle smoothness (spectral.py, band-mean reference)
    from .spectral import fixed_angle_residual_db

    vals = []
    for spl, angles, targets in (
            (spl_h, ha, offaxis_angles_h_deg),
            (spl_v, va, offaxis_angles_v_deg)):
        if spl is None or angles is None:
            continue
        arr = np.asarray(spl, dtype=float)
        ang = np.asarray(angles, dtype=float).ravel()
        if arr.ndim != 2 or arr.shape != (f.size, ang.size):
            continue
        for target in targets:
            try:
                r = fixed_angle_residual_db(
                    f, arr, ang, float(target),
                    reference=offaxis_reference, band_hz=offaxis_band_hz)
            except ValueError:
                r = float("nan")
            if np.isfinite(r):
                vals.append(float(r))
    if vals:
        out["offaxis_smooth_db"] = float(np.max(vals))

    return out
