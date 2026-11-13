"""acoustic_metrics_v2 (proposed, additive): status-aware main-lobe descriptors on a polar cut.

Rev2 plan section 5 (docs/research/QUEUE_PLAN_REV2_2026-11-13.md). Does NOT replace or change
``metrics/polar.py::beamwidth_deg`` (legacy OUTERMOST crossings, 180 deg sentinel), which every
objective version still uses. Nothing here feeds an objective. Pure numpy, no solver.

Main-lobe width = the FIRST threshold crossing walking outward from 0 deg on each side, so a
detached side lobe cannot widen it. Each side is ``valid`` or ``censored`` (no crossing inside the
sampled range); a censored side reports the range edge as a lower bound, never 180 deg as a
measurement.
"""
from __future__ import annotations

import numpy as np

from .polar import _threshold_db, normalized_db

METHOD_VERSION = "acoustic_v2.0"


def _first_crossing(a: np.ndarray, d: np.ndarray, thr: float) -> tuple[float, str]:
    """a, d start at 0 deg and walk outward. Linear-in-dB interpolation, like legacy."""
    for i in range(1, len(a)):
        if d[i] <= thr < d[i - 1] or d[i] <= thr <= d[i - 1] and d[i - 1] > thr:
            t = (d[i - 1] - thr) / (d[i - 1] - d[i])
            return float(a[i - 1] + t * (a[i] - a[i - 1])), "valid"
    return float(a[-1]), "censored"


def main_lobe(angles_deg, spl_db, drop_db: float = 6.0) -> dict:
    """Main-lobe width and off-axis peak on one cut. Reference is the 0 deg sample.

    Returns {width_deg, left_deg, right_deg, left_status, right_status, status,
    max_offaxis_db, max_offaxis_angle_deg, outside_peak_db, method}.
    ``outside_peak_db``: highest level outside the main lobe (dB re axis), so a detached side lobe
    or a lobe above axis shows up even though the main width ignores it. None if nothing outside.
    """
    a = np.asarray(angles_deg, float)
    s = np.asarray(spl_db, float)
    if a.ndim != 1 or a.shape != s.shape:
        raise ValueError("angles_deg and spl_db must be 1-D and the same length")
    order = np.argsort(a)
    a, s = a[order], s[order]
    k = np.flatnonzero(np.abs(a) < 1e-9)
    if k.size != 1:
        raise ValueError("need exactly one 0-degree sample")
    k = int(k[0])
    d = normalized_db(s, s[k])
    thr = _threshold_db(drop_db)
    r_ang, r_st = _first_crossing(a[k:], d[k:], thr)
    l_ang, l_st = _first_crossing(-a[k::-1], d[k::-1], thr)
    out = (a > r_ang) | (a < -l_ang)
    off = np.abs(a) > 1e-9
    j = int(np.argmax(np.where(off, d, -np.inf))) if off.any() else None
    status = "valid" if (l_st == r_st == "valid") else "censored"
    return {
        "width_deg": l_ang + r_ang, "left_deg": l_ang, "right_deg": r_ang,
        "left_status": l_st, "right_status": r_st, "status": status,
        "max_offaxis_db": float(d[j]) if j is not None else None,
        "max_offaxis_angle_deg": float(a[j]) if j is not None else None,
        "outside_peak_db": float(d[out].max()) if out.any() else None,
        "drop_db": float(drop_db), "method": METHOD_VERSION,
    }


# ----------------------------------------------------------------------------- full sphere
# Rev2 5 / P0. The stored balloon is theta-major (theta 0..180 INCLUSIVE from +Z, phi 0..360
# exclusive from +X), NOT equal-area. Every sphere integral here goes through ONE quadrature:
# trapezoid in theta times sin(theta), uniform in phi, normalized to sum 1 (a 4*pi average).

def sphere_weights(grid) -> np.ndarray:
    """Quadrature weights (n_theta*n_phi,), theta-major, summing to 1."""
    nT, nP = int(grid[0]), int(grid[1])
    if nT < 3 or nP < 3:
        raise ValueError(f"balloon grid {grid!r} too small for quadrature")
    th = np.linspace(0.0, np.pi, nT)
    wt = np.full(nT, th[1] - th[0])
    wt[0] *= 0.5
    wt[-1] *= 0.5
    w = np.repeat(wt * np.sin(th), nP)
    return w / w.sum()


def _rel_db(spl_db, grid):
    nT, nP = int(grid[0]), int(grid[1])
    s = np.asarray(spl_db, float)
    if s.ndim != 2 or s.shape[1] != nT * nP:
        raise ValueError(f"spl_balloon_db shape {s.shape} does not match grid {grid!r}")
    ref = s[:, :nP].mean(axis=1)                    # theta = 0 pole row = on axis (+Z)
    return s - ref[:, None], nT, nP


def balloon_di(spl_db, grid) -> dict:
    """DI(f) = 10 log10(|p_axis|^2 / mean_sphere |p|^2), linear-power quadrature.

    Status per frequency: ``valid`` or ``invalid`` (non-finite or zero power). Never 0 dB as a
    stand-in (legacy ``di_from_balloon`` does that; it is left unchanged for old objectives).
    """
    rel, nT, nP = _rel_db(spl_db, grid)
    w = sphere_weights(grid)
    lin = np.where(np.isfinite(rel), 10.0 ** (rel / 10.0), np.nan)
    mean = np.nansum(lin * w, axis=1)
    bad = ~np.isfinite(rel).all(axis=1) | (mean <= 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        di = -10.0 * np.log10(mean)
    di = np.where(bad, np.nan, di)
    return {"di_db": di, "status": np.where(bad, "invalid", "valid"),
            "quadrature": "theta_trapz_sin_x_phi_uniform", "di_source": "balloon",
            "method": METHOD_VERSION}


def _flood_main(mask2d: np.ndarray) -> np.ndarray:
    """Connected region of mask containing the theta=0 pole row; phi wraps."""
    nT, nP = mask2d.shape
    seen = np.zeros_like(mask2d, bool)
    stack = [(0, j) for j in range(nP) if mask2d[0, j]]
    for i, j in stack:
        seen[i, j] = True
    while stack:
        i, j = stack.pop()
        for a, b in ((i + 1, j), (i - 1, j), (i, (j + 1) % nP), (i, (j - 1) % nP)):
            if 0 <= a < nT and mask2d[a, b] and not seen[a, b]:
                seen[a, b] = True
                stack.append((a, b))
    if seen[0].any():
        seen[0, :] = True                           # the pole row is one direction
    return seen


def _islands(mask2d: np.ndarray) -> int:
    nT, nP = mask2d.shape
    seen = np.zeros_like(mask2d, bool)
    n = 0
    for i0 in range(nT):
        for j0 in range(nP):
            if mask2d[i0, j0] and not seen[i0, j0]:
                n += 1
                stack = [(i0, j0)]
                seen[i0, j0] = True
                while stack:
                    i, j = stack.pop()
                    for a, b in ((i + 1, j), (i - 1, j), (i, (j + 1) % nP), (i, (j - 1) % nP)):
                        if 0 <= a < nT and mask2d[a, b] and not seen[a, b]:
                            seen[a, b] = True
                            stack.append((a, b))
    return n


def balloon_lobes(spl_db, grid, drop_db: float = 6.0) -> dict:
    """Per frequency: connected main region (>= -drop from axis, containing the axis), the
    largest level OUTSIDE it, its direction, the count of detached islands above threshold,
    the fraction of radiated power outside the main region, and the max level above axis
    anywhere (a +dB hot spot). All in linear power with the shared quadrature.
    """
    rel, nT, nP = _rel_db(spl_db, grid)
    w = sphere_weights(grid).reshape(nT, nP)
    thr = _threshold_db(drop_db)
    th = np.repeat(np.linspace(0, 180, nT), nP).reshape(nT, nP)
    ph = np.tile(np.linspace(0, 360, nP, endpoint=False), nT).reshape(nT, nP)
    out = {k: [] for k in ("outside_peak_db", "outside_peak_theta_deg", "outside_peak_phi_deg",
                           "island_count", "outside_power_fraction", "max_above_axis_db",
                           "main_solid_angle_sr", "status")}
    for f in range(rel.shape[0]):
        r = rel[f].reshape(nT, nP)
        if not np.isfinite(r).all():
            for k in out:
                out[k].append(None)
            out["status"][-1] = "invalid"
            continue
        above = r >= thr
        main = _flood_main(above)
        outside = ~main
        lin = 10.0 ** (r / 10.0)
        tot = float((lin * w).sum())
        if outside.any():
            k = np.argmax(np.where(outside, r, -np.inf))
            out["outside_peak_db"].append(float(r.flat[k]))
            out["outside_peak_theta_deg"].append(float(th.flat[k]))
            out["outside_peak_phi_deg"].append(float(ph.flat[k]))
        else:
            out["outside_peak_db"].append(None)
            out["outside_peak_theta_deg"].append(None)
            out["outside_peak_phi_deg"].append(None)
        out["island_count"].append(_islands(above & outside))
        out["outside_power_fraction"].append(float((lin * w)[outside].sum() / tot) if tot > 0 else None)
        out["max_above_axis_db"].append(float(r.max()))
        out["main_solid_angle_sr"].append(float(4 * np.pi * w[main].sum()))
        out["status"].append("valid")
    out["drop_db"] = float(drop_db)
    out["method"] = METHOD_VERSION
    return out


# ----------------------------------------------------------------------------- onsets

def _sustained_onset(freqs, ok, dwell: int) -> dict:
    """Lowest frequency f_i such that ok holds for f_i and the next dwell-1 samples AND every
    sample above. Bracket = (f_{i-1}, f_i); censored when ok already holds at the lowest bin.
    """
    f = np.asarray(freqs, float)
    ok = np.asarray(ok, bool)
    n = len(f)
    if n == 0:
        return {"onset_hz": None, "bracket_hz": None, "status": "missing"}
    tail_ok = np.flip(np.logical_and.accumulate(np.flip(ok)))
    idx = np.flatnonzero(tail_ok)
    if idx.size == 0 or (n - idx[0]) < dwell:
        return {"onset_hz": None, "bracket_hz": None, "status": "not_reached"}
    i = int(idx[0])
    if i == 0:
        return {"onset_hz": float(f[0]), "bracket_hz": [None, float(f[0])], "status": "censored_low"}
    return {"onset_hz": float(f[i]), "bracket_hz": [float(f[i - 1]), float(f[i])], "status": "valid"}


def loading_onset(freqs, z_throat, threshold: float = 0.7, dwell: int = 2) -> dict:
    """Lowest frequency above which Re(z_throat/rho c) stays >= threshold. Missing impedance
    is ``missing``, never a pass. Convention recorded."""
    if z_throat is None:
        return {"onset_hz": None, "bracket_hz": None, "status": "missing"}
    z = np.asarray(z_throat)
    re = np.real(z).astype(float)
    r = _sustained_onset(freqs, np.isfinite(re) & (re >= threshold), dwell)
    r.update(threshold=threshold, dwell=dwell, convention="Re(z_throat)/(rho c), source basis per response meta",
             method=METHOD_VERSION)
    return r


def pattern_control_onset(freqs, width_deg, target_deg, tol_deg, outside_peak_db=None,
                          max_outside_db: float = -6.0, dwell: int = 3) -> dict:
    """Lowest frequency above which main-lobe width stays within target +/- tol AND (when given)
    no out-of-main lobe exceeds max_outside_db. Predeclare target/tol/dwell in the study config.
    Never inferred from mouth size."""
    w = np.asarray(width_deg, float)
    ok = np.isfinite(w) & (np.abs(w - target_deg) <= tol_deg)
    if outside_peak_db is not None:
        o = np.array([np.nan if v is None else v for v in outside_peak_db], float)
        ok &= ~(o > max_outside_db)
    r = _sustained_onset(freqs, ok, dwell)
    r.update(target_deg=target_deg, tol_deg=tol_deg, max_outside_db=max_outside_db, dwell=dwell,
             method=METHOD_VERSION)
    return r


def keele_estimate(f_hz: float | None = None, coverage_deg: float = 90.0,
                   dimension_mm: float | None = None) -> dict:
    """Keele-style heuristic (25.4e6 / (f * coverage)), labeled as a planning ESTIMATE only
    (Rev2 3.1): not a feasibility proof, not an onset, not a gate."""
    out = {"method": "heuristic", "binding": False, "coverage_deg": coverage_deg}
    if f_hz:
        out["keele_estimated_dimension_mm"] = 25_400_000.0 / (float(f_hz) * coverage_deg)
    if dimension_mm:
        out["keele_estimated_break_hz"] = 25_400_000.0 / (float(dimension_mm) * coverage_deg)
    return out


# ----------------------------------------------------------------------------- one response

def analyze_response(path, coverage_h_deg: float | None = None, coverage_v_deg: float | None = None,
                     tol_deg: float = 10.0) -> dict:
    """All v2 descriptors from one stored ``response.npz`` (read-only, zero BEM)."""
    from pathlib import Path as _Path

    from ..solve.cache import load_response
    r = load_response(_Path(path))                   # the cache's own reader: _NULL sentinels -> None
    freqs = np.asarray(r.freqs_hz, float)
    ha, va, sh, sv = r.h_angles_deg, r.v_angles_deg, r.spl_h_db, r.spl_v_db
    bal, zt, meta = r.spl_balloon_db, r.z_throat, (r.meta or {})
    has_phase = any(x is not None for x in (r.p_h, r.p_v, r.p_balloon))
    res = {"method": METHOD_VERSION, "freqs_hz": freqs.tolist(),
           "observation": {"distance_m": meta.get("distance_m"), "observation_kind": "finite_radius_pressure",
                           "far_field_validated": False},
           "available": {"cuts": sh is not None, "balloon": bal is not None,
                         "z_throat": zt is not None, "phase": has_phase}}
    for name, a, s in (("h", ha, sh), ("v", va, sv)):
        if a is None or s is None:
            res[f"main_{name}"] = {"status": "missing"}
            continue
        rows = [main_lobe(a, s[i]) for i in range(len(freqs))]
        res[f"main_{name}"] = {k: [r[k] for r in rows] for k in rows[0]}
    grid = meta.get("balloon_grid")
    if bal is not None and isinstance(grid, list) and len(grid) == 2:
        di = balloon_di(bal, grid)
        res["di_balloon"] = {"di_db": [None if not np.isfinite(v) else float(v) for v in di["di_db"]],
                             "status": di["status"].tolist(), "quadrature": di["quadrature"]}
        res["lobes"] = balloon_lobes(bal, grid)
    else:
        res["di_balloon"] = {"status": "missing"}
        res["lobes"] = {"status": "missing"}
    res["loading"] = loading_onset(freqs, zt)
    out_pk = res["lobes"].get("outside_peak_db") if isinstance(res["lobes"], dict) else None
    for name, cov in (("h", coverage_h_deg), ("v", coverage_v_deg)):
        m = res.get(f"main_{name}", {})
        if cov and "width_deg" in m:
            res[f"pattern_onset_{name}"] = pattern_control_onset(freqs, m["width_deg"], cov, tol_deg,
                                                                 out_pk if isinstance(out_pk, list) else None)
    return res
