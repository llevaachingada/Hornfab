"""Alignment, derived curves, per-band statistics and verdicts for the A/B comparison.

Rules this module keeps:

* Original data is never replaced. Alignment makes COPIES on a common grid and says what it interpolated.
* Quantities that depend on a whole pattern (beamwidth, DI) are computed on each side's NATIVE angle / direction
  grid first and only then compared at common frequencies.
* Interpolation is for comparison only: log-frequency axis, linear in dB, unwrapped phase for phase.
* Tolerances are STARTING POINTS for this check (see ``DEFAULT_TOLERANCES``), not standards.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from ..metrics.di import di_from_balloon, di_from_cuts, sin_theta_weights
from ..metrics.polar import beamwidth_deg
from .model import AbData

BANDS_DEFAULT: tuple[tuple[str, float, float], ...] = (
    ("<1k", 0.0, 1000.0), ("1-5k", 1000.0, 5000.0), ("5-10k", 5000.0, 10000.0), (">10k", 10000.0, float("inf")))
OFF_AXIS_ANGLES = (15.0, 30.0, 45.0, 60.0, 90.0)
SHAPE_BAND_HZ = (1000.0, 5000.0)
ORDER = {"pass": 0, "warn": 1, "fail": 2}


@dataclass
class Tolerances:
    """Starting-point tolerances. Absolute differences, A (Hornfab) minus B (Boundary Lab).

    PASS: max |delta| in the band is within tol. WARN: the RMS is within tol, or the max is within ``warn_factor`` x tol.
    FAIL: anything worse. These numbers come from the solver noise floor already measured for Hornfab
    (about 0.04 dB between two solves) plus allowances for different meshing and a float32 solver; they are chosen
    to be informative for a first sanity check, and are not a standard. Override with ``--tolerances file.json``.
    """
    on_axis_db: float = 1.0
    off_axis_db: float = 1.5
    polar_map_db: float = 2.0
    beamwidth_deg: float = 5.0
    di_db: float = 0.5
    balloon_db: float = 2.0
    phase_deg: float = 20.0
    z_real: float = 0.15
    z_imag: float = 0.15
    map_floor_db: float = -30.0        # map / balloon statistics ignore points below this (both sides, re on-axis)
    warn_factor: float = 2.0

    @classmethod
    def from_dict(cls, d: dict | None) -> "Tolerances":
        t = cls()
        for k, v in (d or {}).items():
            if not hasattr(t, k):
                raise ValueError(f"unknown tolerance {k!r}; known: {sorted(asdict(t))}")
            setattr(t, k, float(v))
        return t


DEFAULT_TOLERANCES = Tolerances()


# ------------------------------------------------------------------ derived (native grids)

@dataclass
class Derived:
    label: str
    freqs: np.ndarray
    angles: np.ndarray
    axis_abs_db: np.ndarray | None
    norm_h: np.ndarray | None
    norm_v: np.ndarray | None
    rel_phase_h: np.ndarray | None
    rel_phase_v: np.ndarray | None
    axis_phase_deg: np.ndarray | None
    bw_h: np.ndarray | None
    bw_v: np.ndarray | None
    di: np.ndarray | None
    di_source: str
    z: np.ndarray | None
    balloon_dirs: np.ndarray | None
    balloon_norm: np.ndarray | None
    meta: dict = field(default_factory=dict)


def _wrap(deg):
    return (np.asarray(deg, dtype=float) + 180.0) % 360.0 - 180.0


def _rel_phase(d: AbData, plane: str) -> np.ndarray | None:
    p = d.p_h if plane == "H" else d.p_v
    ph = d.phase_h_deg if plane == "H" else d.phase_v_deg
    if p is not None:
        ref = p[:, [d.axis_index]]
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.rad2deg(np.angle(p / ref))
    return None if ph is None else _wrap(ph)


def _beamwidths(angles: np.ndarray, norm: np.ndarray | None) -> np.ndarray | None:
    if norm is None or angles.size < 3 or not np.any(np.abs(angles) < 1e-9):
        return None
    return np.array([beamwidth_deg(angles, row)[0] for row in norm])


def derive(d: AbData) -> Derived:
    nh, nv = d.normalized("H"), d.normalized("V")
    ax = d.axis_db_absolute()
    bw_h, bw_v = _beamwidths(d.angles_deg, nh), _beamwidths(d.angles_deg, nv)
    di, di_src, bn = None, "none", None
    if d.balloon_spl_db is not None and d.balloon_dirs is not None:
        ref = 0.0 if d.level == "normalized" else (ax if ax is not None else None)
        if ref is None:
            ref = np.zeros(d.freqs_hz.size)
        ref = np.broadcast_to(np.asarray(ref, dtype=float), (d.freqs_hz.size,))
        bn = d.balloon_spl_db - ref[:, None]
        w = sin_theta_weights(np.degrees(np.arccos(np.clip(d.balloon_dirs[:, 2], -1, 1)))) \
            if d.balloon_kind == "theta_phi" else None
        di = np.array([di_from_balloon(row, 0.0, w) for row in bn])
        di_src = "balloon"
    elif bw_h is not None and bw_v is not None:
        di = np.array([di_from_cuts(h, v) for h, v in zip(bw_h, bw_v)])
        di_src = "cuts_estimate"
    return Derived(label=d.label, freqs=d.freqs_hz.copy(), angles=d.angles_deg.copy(), axis_abs_db=ax,
                   norm_h=nh, norm_v=nv, rel_phase_h=_rel_phase(d, "H"), rel_phase_v=_rel_phase(d, "V"),
                   axis_phase_deg=d.axis_phase_aligned_deg(), bw_h=bw_h, bw_v=bw_v, di=di, di_source=di_src,
                   z=None if d.z_norm is None else np.asarray(d.z_norm, dtype=complex),
                   balloon_dirs=d.balloon_dirs, balloon_norm=bn, meta=dict(d.meta))


# ------------------------------------------------------------------ alignment (copies only)

def _interp_rows(f_src, arr, f_new, *, phase: bool = False):
    """Interpolate along axis 0 on log f. Phase arrays (degrees) are unwrapped first."""
    arr = np.asarray(arr, dtype=float)
    x, xn = np.log(f_src), np.log(f_new)
    flat = arr.reshape(arr.shape[0], -1)
    out = np.empty((xn.size, flat.shape[1]))
    for j in range(flat.shape[1]):
        col = np.rad2deg(np.unwrap(np.deg2rad(flat[:, j]))) if phase else flat[:, j]
        out[:, j] = np.interp(xn, x, col)
    out = out.reshape((xn.size,) + arr.shape[1:])
    return _wrap(out) if phase else out


def _take(x, idx, f_src=None, f_new=None, *, phase=False, complex_=False):
    if x is None:
        return None
    if idx is not None:
        return x[idx]
    if complex_:
        return _interp_rows(f_src, x.real, f_new) + 1j * _interp_rows(f_src, x.imag, f_new)
    return _interp_rows(f_src, x, f_new, phase=phase)


def _match_indices(f_src: np.ndarray, f_new: np.ndarray, rtol: float):
    """Index of each f_new in f_src if EVERY point matches within rtol, else None (needs interpolation)."""
    j = np.clip(np.searchsorted(f_src, f_new), 1, f_src.size - 1) if f_src.size > 1 else np.zeros(f_new.size, int)
    cand = np.where(np.abs(f_src[j - 1] - f_new) <= np.abs(f_src[j] - f_new), j - 1, j) if f_src.size > 1 else j
    ok = np.abs(f_src[cand] - f_new) <= rtol * f_new
    return cand if ok.all() else None


def _resample(d: Derived, f_new: np.ndarray, rtol: float) -> tuple[Derived, bool]:
    idx = _match_indices(d.freqs, f_new, rtol)
    interp = idx is None
    fs = d.freqs

    def t(x, **kw):
        return _take(x, idx, fs, f_new, **kw)
    out = Derived(label=d.label, freqs=f_new.copy(), angles=d.angles, axis_abs_db=t(d.axis_abs_db),
                  norm_h=t(d.norm_h), norm_v=t(d.norm_v), rel_phase_h=t(d.rel_phase_h, phase=True),
                  rel_phase_v=t(d.rel_phase_v, phase=True), axis_phase_deg=t(d.axis_phase_deg, phase=True),
                  bw_h=t(d.bw_h), bw_v=t(d.bw_v), di=t(d.di), di_source=d.di_source,
                  z=t(d.z, complex_=True), balloon_dirs=d.balloon_dirs, balloon_norm=t(d.balloon_norm), meta=d.meta)
    return out, interp


def align_frequencies(a: Derived, b: Derived, rtol: float = 1e-4):
    """-> (a_on_grid, b_on_grid, info). Common grid = the COARSER side's points inside the overlap; the denser side is
    interpolated only when its points do not already coincide."""
    lo, hi = max(a.freqs[0], b.freqs[0]), min(a.freqs[-1], b.freqs[-1])
    if lo > hi:
        raise ValueError(f"the two data sets share no frequency range: A {a.freqs[0]:g}-{a.freqs[-1]:g} Hz, "
                         f"B {b.freqs[0]:g}-{b.freqs[-1]:g} Hz")
    sel = lambda f: f[(f >= lo * (1 - rtol)) & (f <= hi * (1 + rtol))]    # noqa: E731
    fa, fb = sel(a.freqs), sel(b.freqs)
    base, grid_of = (a, "A") if fa.size <= fb.size else (b, "B")
    grid = fa if grid_of == "A" else fb
    ra, ia = _resample(a, grid, rtol)
    rb, ib = _resample(b, grid, rtol)
    info = {"n_common": int(grid.size), "grid_from": grid_of, "interpolated_A": bool(ia), "interpolated_B": bool(ib),
            "overlap_hz": [float(lo), float(hi)], "n_A": int(a.freqs.size), "n_B": int(b.freqs.size),
            "A_range_hz": [float(a.freqs[0]), float(a.freqs[-1])], "B_range_hz": [float(b.freqs[0]), float(b.freqs[-1])],
            "note": ("identical frequency grids: no interpolation" if not (ia or ib) else
                     "interpolated for comparison only (log f, linear dB / unwrapped phase); stored data is untouched")}
    if grid.size < 3:
        info["warning"] = "fewer than 3 common frequencies: statistics are not meaningful"
    return ra, rb, info


def _angle_grid_common(a: Derived, b: Derived):
    """Common angle list (coarser grid inside the overlap, |angle| <= 90). Returns (angles, idxA|None, idxB|None...)."""
    lo, hi = max(a.angles.min(), b.angles.min(), -90.0), min(a.angles.max(), b.angles.max(), 90.0)
    ca = a.angles[(a.angles >= lo - 1e-9) & (a.angles <= hi + 1e-9)]
    cb = b.angles[(b.angles >= lo - 1e-9) & (b.angles <= hi + 1e-9)]
    return (ca if ca.size <= cb.size else cb), (ca.size != cb.size or not np.allclose(ca, cb))


def _on_angles(arr, src_angles, new_angles):
    if arr is None:
        return None
    if src_angles.size == new_angles.size and np.allclose(src_angles, new_angles, atol=1e-9):
        return arr
    return np.stack([np.interp(new_angles, src_angles, row) for row in arr])


def _on_angles_phase(arr, src_angles, new_angles):
    if arr is None:
        return None
    if src_angles.size == new_angles.size and np.allclose(src_angles, new_angles, atol=1e-9):
        return arr
    return _wrap(np.stack([np.interp(new_angles, src_angles, np.rad2deg(np.unwrap(np.deg2rad(row)))) for row in arr]))


# ------------------------------------------------------------------ statistics & verdicts

def band_masks(freqs: np.ndarray, bands) -> dict[str, np.ndarray]:
    out = {name: (freqs >= lo) & (freqs < hi) for name, lo, hi in bands}
    out["all"] = np.ones(freqs.size, dtype=bool)
    return out


def _stats(delta: np.ndarray, mask: np.ndarray) -> dict:
    x = np.asarray(delta, dtype=float)
    x = x[mask] if x.ndim == 1 else x[mask].ravel()
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {"n": 0, "max_abs": None, "rms": None, "median": None, "p95_abs": None}
    return {"n": int(x.size), "max_abs": float(np.max(np.abs(x))), "rms": float(np.sqrt(np.mean(x ** 2))),
            "median": float(np.median(x)), "p95_abs": float(np.percentile(np.abs(x), 95))}


def classify(st: dict, tol: float, warn_factor: float) -> str:
    if not st or st.get("n", 0) == 0 or st["max_abs"] is None:
        return "n/a"
    if st["max_abs"] <= tol:
        return "pass"
    if st["rms"] <= tol or st["max_abs"] <= warn_factor * tol:
        return "warn"
    return "fail"


def worst(verdicts) -> str:
    v = [x for x in verdicts if x in ORDER]
    return max(v, key=ORDER.__getitem__) if v else "n/a"


@dataclass
class Metric:
    key: str
    title: str
    unit: str
    tol: float
    delta: np.ndarray                   # (nf,) or (nf, k) A - B on the common grid
    stats: dict                         # band -> stats
    verdicts: dict                      # band -> pass/warn/fail/n/a
    overall: str
    note: str = ""


def _metric(key, title, unit, tol, delta, freqs, bands, warn_factor, note="", cap: str | None = None) -> Metric:
    masks = band_masks(freqs, bands)
    stats = {b: _stats(delta, m) for b, m in masks.items()}
    verd = {b: classify(s, tol, warn_factor) for b, s in stats.items()}
    overall = worst([v for b, v in verd.items() if b != "all"]) if any(
        stats[b]["n"] for b in stats if b != "all") else "n/a"
    if cap and overall == "pass":
        overall, note = cap, (note + " ").lstrip() + f"verdict capped at {cap}: {cap!r} source"
    return Metric(key, title, unit, tol, np.asarray(delta, dtype=float), stats, verd, overall, note)


# ------------------------------------------------------------------ balloon projection

def fibonacci_dirs(n: int) -> np.ndarray:
    i = np.arange(n, dtype=float)
    z = 1.0 - 2.0 * (i + 0.5) / n
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    phi = np.pi * (3.0 - np.sqrt(5.0)) * i
    return np.column_stack([r * np.cos(phi), r * np.sin(phi), z])


def local_fit_weights(src_dirs: np.ndarray, dst_dirs: np.ndarray, k: int = 10):
    """For every destination direction: the ``k`` nearest source directions and the weights that evaluate a distance-weighted
    local QUADRATIC least-squares fit (in the tangent plane) at the destination. The weights depend only on geometry, so
    they are computed once and applied to every frequency. Falls back to inverse-distance weights if a fit is ill-posed."""
    s = src_dirs / np.linalg.norm(src_dirs, axis=1, keepdims=True)
    k = int(min(k, s.shape[0]))
    idx = np.empty((dst_dirs.shape[0], k), dtype=np.int64)
    wts = np.empty((dst_dirs.shape[0], k))
    for lo in range(0, dst_dirs.shape[0], 512):
        dots = dst_dirs[lo:lo + 512] @ s.T
        part = np.argpartition(-dots, k - 1, axis=1)[:, :k]
        idx[lo:lo + 512] = part
    for n in range(dst_dirs.shape[0]):
        d = dst_dirs[n]
        nb = s[idx[n]]
        ang = np.arccos(np.clip(nb @ d, -1, 1))
        e1 = np.cross(d, [0.0, 0.0, 1.0] if abs(d[2]) < 0.9 else [1.0, 0.0, 0.0])
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(d, e1)
        u, v = nb @ e1, nb @ e2
        X = np.column_stack([np.ones(k), u, v, u * u, u * v, v * v]) if k >= 8 else np.column_stack([np.ones(k), u, v])
        h = max(ang.max(), 1e-6)
        wd = np.exp(-((ang / h) ** 2) * 1.5)
        try:
            P = np.linalg.pinv(X * wd[:, None], rcond=1e-6)
            row = P[0] * wd
            if not np.all(np.isfinite(row)) or abs(row.sum() - 1.0) > 1e-3 or np.abs(row).sum() > 6.0:
                raise np.linalg.LinAlgError
        except np.linalg.LinAlgError:
            w = 1.0 / np.maximum(ang, 1e-6)
            row = w / w.sum()
        wts[n] = row
    return idx, wts


def project_balloon(dirs: np.ndarray, vals_db: np.ndarray, dst: np.ndarray, k: int = 10, floor_db: float = -80.0) -> np.ndarray:
    """Interpolate (nf, n) dB values on ``dirs`` onto ``dst`` directions (local quadratic fit in dB; floored so -inf cannot
    poison a fit). Comparison use only: this never replaces either side's data."""
    idx, w = local_fit_weights(dirs, dst, k)
    v = np.maximum(np.nan_to_num(np.asarray(vals_db, dtype=float), nan=floor_db, neginf=floor_db), floor_db)
    return np.einsum("fnk,nk->fn", v[:, idx], w)


# ------------------------------------------------------------------ the comparison

@dataclass
class Comparison:
    label_a: str
    label_b: str
    freqs: np.ndarray
    angles: np.ndarray | None
    a: Derived
    b: Derived
    metrics: dict
    info: dict
    tolerances: Tolerances
    bands: tuple
    maps: dict = field(default_factory=dict)
    curves: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    conventions: list = field(default_factory=list)

    @property
    def overall(self) -> str:
        return worst([m.overall for m in self.metrics.values()])

    def to_json(self) -> dict:
        def num(x):
            return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else x
        mets = {}
        for k, m in self.metrics.items():
            mets[k] = {"title": m.title, "unit": m.unit, "tolerance": m.tol, "overall": m.overall, "note": m.note,
                       "bands": {b: {"verdict": m.verdicts[b], **{s: num(v) for s, v in m.stats[b].items()}}
                                 for b in m.stats}}
        return {"format": 1, "A": self.label_a, "B": self.label_b, "overall": self.overall,
                "tolerances": asdict(self.tolerances), "tolerance_note": "starting points for this check, not standards",
                "bands_hz": [[n, lo, None if not np.isfinite(hi) else hi] for n, lo, hi in self.bands],
                "alignment": self.info, "metrics": mets, "notes": self.notes,
                "convention_findings": self.conventions,
                "di_source": {"A": self.a.di_source, "B": self.b.di_source}}


def compare(a_data: AbData, b_data: AbData, *, tolerances: Tolerances | None = None, bands=BANDS_DEFAULT,
            map_angles: np.ndarray | None = None, n_balloon_dirs: int = 1500, freq_rtol: float = 1e-4) -> Comparison:
    """A = Hornfab, B = Boundary Lab (the sign of every delta is A - B)."""
    tol = tolerances or Tolerances()
    da, db_ = derive(a_data), derive(b_data)
    a, b, info = align_frequencies(da, db_, freq_rtol)
    f = a.freqs
    notes: list[str] = []
    if info.get("warning"):
        notes.append(info["warning"])
    if info["interpolated_A"] or info["interpolated_B"]:
        notes.append(info["note"])
    angles, ang_interp = _angle_grid_common(a, b)
    step = float(np.median(np.diff(angles))) if angles.size > 1 else float("nan")
    if ang_interp:
        notes.append(f"angle grids differ: compared on the coarser grid ({angles.size} angles, step ~{step:g} deg); "
                     "the finer side is linearly interpolated in dB for the maps only")
    if np.isfinite(step) and step > 5.0:
        notes.append(f"polar step is {step:g} deg: beamwidth and map statistics are coarse (edges are interpolated)")
    wf = tol.warn_factor
    M: dict[str, Metric] = {}
    curves: dict = {}
    maps: dict = {}
    # ---- on-axis
    if a.axis_abs_db is not None and b.axis_abs_db is not None:
        d = a.axis_abs_db - b.axis_abs_db
        M["on_axis_abs"] = _metric("on_axis_abs", "On-axis SPL, absolute", "dB", tol.on_axis_db, d, f, bands, wf)
        lo, hi = SHAPE_BAND_HZ
        m = (f >= lo) & (f <= hi)
        if not m.any():
            m = np.ones(f.size, dtype=bool)
        sa, sb = a.axis_abs_db - np.mean(a.axis_abs_db[m]), b.axis_abs_db - np.mean(b.axis_abs_db[m])
        M["on_axis_shape"] = _metric("on_axis_shape", "On-axis SPL, shape (band-mean removed)", "dB", tol.on_axis_db,
                                     sa - sb, f, bands, wf,
                                     note=f"each side minus its own mean over {lo:g}-{hi:g} Hz")
        curves["on_axis"] = {"A": a.axis_abs_db, "B": b.axis_abs_db, "A_shape": sa, "B_shape": sb}
    else:
        notes.append("absolute on-axis level is not available on one side (Boundary Lab polar files are normalized; "
                     "send the on-axis export or the headless run): absolute on-axis comparison skipped")
    # ---- off-axis family and maps
    for plane, na_, nb_ in (("H", a.norm_h, b.norm_h), ("V", a.norm_v, b.norm_v)):
        if na_ is None or nb_ is None:
            continue
        A_ = _on_angles(na_, a.angles, angles)
        B_ = _on_angles(nb_, b.angles, angles)
        sel = [ang for ang in OFF_AXIS_ANGLES if ang <= angles.max() + 1e-9]
        fam = {}
        for ang in sel:
            fam[ang] = (np.array([np.interp(ang, angles, r) for r in A_]), np.array([np.interp(ang, angles, r) for r in B_]))
        if fam:
            dl = np.stack([fam[g][0] - fam[g][1] for g in sel], axis=1)
            M[f"off_axis_{plane}"] = _metric(f"off_axis_{plane}", f"Off-axis SPL re on-axis, {plane} plane "
                                             f"({', '.join(f'{g:g}' for g in sel)} deg)", "dB", tol.off_axis_db, dl, f,
                                             bands, wf)
            curves[f"off_axis_{plane}"] = fam
        dmap = A_ - B_
        valid = (A_ > tol.map_floor_db) | (B_ > tol.map_floor_db)
        dm = np.where(valid, dmap, np.nan)
        rms_per_f = np.array([np.sqrt(np.nanmean(r ** 2)) if np.isfinite(r).any() else np.nan for r in dm])
        mx_per_f = np.array([np.nanmax(np.abs(r)) if np.isfinite(r).any() else np.nan for r in dm])
        M[f"polar_map_{plane}"] = _metric(f"polar_map_{plane}", f"{plane} polar map difference (RMS over angle, points above "
                                          f"{tol.map_floor_db:g} dB)", "dB", tol.polar_map_db, rms_per_f, f, bands, wf)
        if np.isfinite(mx_per_f).any():
            M[f"polar_map_{plane}"].note = f"largest single-cell difference {float(np.nanmax(mx_per_f)):.2f} dB"
        maps[plane] = {"A": A_, "B": B_, "diff": dmap, "angles": angles}
        # relative phase over the map (only where both have it and the level is within 20 dB of on-axis)
        pa = _on_angles_phase(a.rel_phase_h if plane == "H" else a.rel_phase_v, a.angles, angles)
        pb = _on_angles_phase(b.rel_phase_h if plane == "H" else b.rel_phase_v, b.angles, angles)
        if pa is not None and pb is not None:
            ok = (A_ > -20.0) & (B_ > -20.0)
            pd = np.where(ok, _wrap(pa - pb), np.nan)
            pr = np.array([np.sqrt(np.nanmean(r ** 2)) if np.isfinite(r).any() else np.nan for r in pd])
            M[f"phase_map_{plane}"] = _metric(f"phase_map_{plane}", f"{plane} relative phase vs on-axis (RMS over angle, within 20 dB)",
                                              "deg", tol.phase_deg, pr, f, bands, wf)
    # ---- beamwidth
    for plane, ba, bb in (("H", a.bw_h, b.bw_h), ("V", a.bw_v, b.bw_v)):
        if ba is not None and bb is not None:
            M[f"beamwidth_{plane}"] = _metric(f"beamwidth_{plane}", f"-6 dB beamwidth, {plane} plane", "deg",
                                              tol.beamwidth_deg, ba - bb, f, bands, wf,
                                              note="total included angle between the outermost -6 dB crossings, "
                                                   "native grids; 180 means no crossing inside +-90")
            curves[f"beamwidth_{plane}"] = {"A": ba, "B": bb}
    # ---- DI
    if a.di is not None and b.di is not None:
        both_bal = a.di_source == "balloon" and b.di_source == "balloon"
        cap = None if both_bal else "warn"
        why = "" if both_bal else f"DI source is {a.di_source!r} (A) / {b.di_source!r} (B); only 'balloon' DI can pass"
        M["di"] = _metric("di", "Directivity index", "dB", tol.di_db, a.di - b.di, f, bands, wf, note=why, cap=cap)
        curves["di"] = {"A": a.di, "B": b.di}
    else:
        notes.append("DI skipped: neither a balloon nor both polar cuts are present on both sides")
    # ---- balloon difference
    if a.balloon_dirs is not None and b.balloon_dirs is not None and a.balloon_norm is not None and b.balloon_norm is not None:
        dst = fibonacci_dirs(n_balloon_dirs)
        ba_ = project_balloon(a.balloon_dirs, a.balloon_norm, dst)
        bb_ = project_balloon(b.balloon_dirs, b.balloon_norm, dst)
        clips = [c for c in (a.meta.get("clip_db"), b.meta.get("clip_db")) if c and c[0] is not None]
        if clips:
            lo_c, hi_c = max(c[0] for c in clips), min(c[1] for c in clips)
            ba_, bb_ = np.clip(ba_, lo_c, hi_c), np.clip(bb_, lo_c, hi_c)
            notes.append(f"balloon differences use both sides clipped to {lo_c:g}..{hi_c:g} dB "
                         "(Boundary Lab's export range); DI from clipped data is biased low in directivity")
        dd = ba_ - bb_
        valid = (ba_ > tol.map_floor_db) | (bb_ > tol.map_floor_db)
        dm = np.where(valid, dd, np.nan)
        rms = np.array([np.sqrt(np.nanmean(r ** 2)) if np.isfinite(r).any() else np.nan for r in dm])
        M["balloon"] = _metric("balloon", f"Balloon difference (RMS over {n_balloon_dirs} equal-area directions, above "
                               f"{tol.map_floor_db:g} dB)", "dB", tol.balloon_db, rms, f, bands, wf)
        maps["balloon"] = {"A": ba_, "B": bb_, "diff": dd, "dirs": dst}
    elif a.balloon_dirs is None or b.balloon_dirs is None:
        notes.append("balloon comparison skipped: no balloon on one side")
    # ---- phase (on-axis, propagation removed)
    if a.axis_phase_deg is not None and b.axis_phase_deg is not None:
        d = _wrap(a.axis_phase_deg - b.axis_phase_deg)
        M["phase_axis"] = _metric("phase_axis", "On-axis phase (propagation delay removed)", "deg", tol.phase_deg, d, f,
                                  bands, wf)
        curves["phase_axis"] = {"A": a.axis_phase_deg, "B": b.axis_phase_deg}
    else:
        notes.append("on-axis phase skipped: needs complex pressure (or a phase column) and the observation distance on both sides")
    # ---- impedance
    if a.z is not None and b.z is not None:
        M["z_real"] = _metric("z_real", "Throat impedance, real part (Z/rho c)", "", tol.z_real, a.z.real - b.z.real, f,
                              bands, wf)
        M["z_imag"] = _metric("z_imag", "Throat impedance, imaginary part (Z/rho c)", "", tol.z_imag, a.z.imag - b.z.imag,
                              f, bands, wf)
        curves["z"] = {"A": a.z, "B": b.z}
    else:
        notes.append("throat impedance skipped: not provided by one side (Boundary Lab's GUI may not export it; the headless run does)")
    return Comparison(a.label, b.label, f, angles, a, b, M, info, tol, tuple(bands), maps, curves, notes)
