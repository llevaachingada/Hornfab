"""Convention / unit sanity checker: "this looks like X" findings, never silent fixes.

Each hypothesis predicts a specific transform of side B (Boundary Lab) relative to A (Hornfab). A finding is raised only
when removing that transform makes the data agree much better than before (residual RMS drops to a small fraction and
to an absolute small value) so a clean comparison produces no findings and a noisy one is not mislabelled.
Findings are advice for a human: they do NOT change any number in the report.
"""
from __future__ import annotations

import numpy as np

from .analysis import Comparison, _wrap

OFFSETS_DB = (
    (6.0206, "6.02 dB constant offset: half-space (2 pi sr, infinite baffle) vs full-space (4 pi sr) radiation, or a "
             "factor 2 in source amplitude / driven area"),
    (3.0103, "3.01 dB constant offset: RMS vs peak (amplitude) pressure convention, or a factor 2 in power"),
    (12.0412, "12.04 dB constant offset: a factor 4 in amplitude, typically a quarter-symmetry model whose source is "
              "counted 4 times (or not at all) in one tool"),
    (9.5424, "9.54 dB constant offset: a factor 3 in amplitude (check source area / symmetry factor)"),
    (60.0, "60 dB constant offset: 20 log10(1000), a millimetre vs metre mix-up in distance or length"),
    (120.0, "120 dB constant offset: 40 log10(1000), a mm vs m mix-up in area"),
)
RADIUS_CANDIDATES_M = (0.5, 1.0, 1.5, 3.0, 4.0, 5.0, 10.0)
FREQ_SCALES = ((0.5, "factor 2"), (2.0, "factor 2"), (1000.0, "mm vs m (x1000)"), (0.001, "mm vs m (/1000)"),
               (25.4, "inch vs mm"), (1 / 25.4, "inch vs mm"))


def _rms(x) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return float(np.sqrt(np.mean(x ** 2))) if x.size else float("nan")


def _circ_mean(d_deg) -> float:
    return float(np.angle(np.mean(np.exp(1j * np.deg2rad(np.asarray(d_deg, dtype=float)))), deg=True))


def _delay_search(f, d_deg, max_ms: float = 5.0, step_ms: float = 0.002):
    """Pure-delay model d = 360 f tau + c (deg): grid search of tau by phasor coherence (robust to phase wrapping
    between grid points, where an unwrap-and-fit would fail). Returns (tau_s, residual_rms_deg, c_deg)."""
    f = np.asarray(f, dtype=float)
    z = np.exp(1j * np.deg2rad(np.asarray(d_deg, dtype=float)))
    taus = np.arange(-max_ms, max_ms + 0.5 * step_ms, step_ms) * 1e-3
    coh = np.abs(np.exp(-2j * np.pi * np.outer(taus, f)) @ z) / f.size
    tau = float(taus[int(np.argmax(coh))])
    c = _circ_mean(np.asarray(d_deg, dtype=float) - 360.0 * f * tau)
    return tau, _rms(_wrap(np.asarray(d_deg, dtype=float) - 360.0 * f * tau - c)), c


def _finding(code, likelihood, message, **evidence) -> dict:
    return {"code": code, "likelihood": likelihood, "message": message,
            "evidence": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in evidence.items()}}


def check_conventions(cmp: Comparison, *, offset_tol_db: float = 0.35) -> list[dict]:
    a, b, f = cmp.a, cmp.b, cmp.freqs
    out: list[dict] = []
    tol = cmp.tolerances

    # ---------------- level: constant offset, slope
    if a.axis_abs_db is not None and b.axis_abs_db is not None:
        d = a.axis_abs_db - b.axis_abs_db
        base = _rms(d)
        med = float(np.median(d))
        spread = _rms(d - med)
        if base > tol.on_axis_db:
            hit = False
            for val, msg in OFFSETS_DB:
                for sign in (1, -1):
                    if abs(med - sign * val) <= offset_tol_db and spread <= max(0.5, 0.35 * abs(med)):
                        who = "A (Hornfab) is higher than B" if sign > 0 else "A (Hornfab) is lower than B"
                        out.append(_finding("constant_offset", "likely", f"{msg}. {who} by {med:+.2f} dB with only "
                                            f"{spread:.2f} dB of remaining spread.", median_offset_db=med, spread_db=spread))
                        hit = True
                        break
                if hit:
                    break
            ra, rb = a.meta.get("distance_m"), b.meta.get("distance_m")
            if not hit and ra and rb and abs(ra - rb) > 1e-6 * ra:
                exp = 20.0 * np.log10(rb / ra)          # farther observer = quieter: A - B = 20 log10(rB / rA)
                if abs(med - exp) <= offset_tol_db and spread <= 0.6:
                    out.append(_finding("radius_mismatch", "likely", f"observation radius differs (A {ra:g} m, B {rb:g} m); the "
                                        f"offset {med:+.2f} dB matches 20 log10(rB/rA) = {exp:+.2f} dB. Re-run one side at the "
                                        "other's radius.", median_offset_db=med, expected_db=exp))
                    hit = True
            if not hit and not (ra and rb) and ra:
                for rc in RADIUS_CANDIDATES_M:
                    exp = 20.0 * np.log10(rc / ra)
                    if abs(rc - ra) > 1e-6 and abs(med - exp) <= offset_tol_db and spread <= 0.6:
                        out.append(_finding("radius_mismatch", "possible", f"B's level is {-med:+.2f} dB relative to A at every frequency, "
                                            f"which is exactly what an observation radius of {rc:g} m instead of {ra:g} m would give "
                                            f"(20 log10({rc:g}/{ra:g}) = {exp:+.2f} dB). Check Polar Observation Distance in Boundary Lab.",
                                            median_offset_db=med, candidate_radius_m=rc))
                        hit = True
                        break
            lf = np.log10(f)
            if f.size >= 4 and np.ptp(lf) > 0.3:
                slope, icpt = np.polyfit(lf, d, 1)
                resid = _rms(d - (slope * lf + icpt))
                for target, msg in ((20.0, "a +20 dB/decade slope: one side is driven with unit velocity and the other with "
                                           "unit acceleration (or the 20 log10(2 pi f) conversion was applied twice / not at all)"),
                                    (40.0, "a +40 dB/decade slope: the velocity/acceleration conversion is off by two "
                                           "integrations (applied twice, or double-differentiated)")):
                    for sign in (1, -1):
                        if abs(slope - sign * target) <= 0.15 * target and resid <= max(0.6, 0.3 * base):
                            out.append(_finding("drive_basis_slope", "likely", f"On-axis A-B has {msg}. Measured slope "
                                                f"{slope:+.1f} dB/decade, remaining spread {resid:.2f} dB.", slope_db_per_decade=slope,
                                                spread_db=resid))
                            hit = True
            if not hit and base > 3 * tol.on_axis_db:
                out.append(_finding("level_unexplained", "possible", f"On-axis level differs by {med:+.2f} dB (median) with "
                                    f"{spread:.2f} dB spread and matches none of the known conventions. Check source amplitude, "
                                    "driven area, symmetry factor and observation radius first.", median_offset_db=med,
                                    spread_db=spread))
    # ---------------- phase
    pa, pb = a.axis_phase_deg, b.axis_phase_deg
    if pa is not None and pb is not None:
        d = _wrap(pa - pb)
        base = _rms(d)
        if base > tol.phase_deg:
            r_ref = a.meta.get("distance_m") or b.meta.get("distance_m")
            cands = []                                              # (residual rms, finding)
            c0 = _circ_mean(d)
            cands.append((_rms(_wrap(d - c0)), "const", c0, None))
            if r_ref:
                bconj = -pb + 360.0 * f * 2.0 * float(r_ref) / 343.0           # conjugate the UNALIGNED phase, re-align
                cands.append((_rms(_wrap(pa - bconj)), "conj", None, None))
            tau, resid_d, c_d = _delay_search(f, d)
            cands.append((resid_d, "delay", c_d, tau))
            ok = [c for c in cands if c[0] < 0.35 * base and c[0] < tol.phase_deg]
            if ok:
                res, kind, c, tau = min(ok, key=lambda x: x[0])
                if kind == "conj":
                    out.append(_finding("time_convention", "likely", "On-axis phase of A matches B only after conjugating B (and re-removing the "
                                        "propagation delay): the tools use opposite time conventions (exp(-i w t) vs exp(+i w t)). "
                                        "Hornfab's importer already converts its own side, so check that B is really exp(+i w t) and "
                                        "that the Boundary Lab export was not conjugated twice.", rms_before_deg=base, rms_after_deg=res))
                elif kind == "const":
                    if abs(abs(c) - 180.0) <= 25.0:
                        out.append(_finding("polarity", "likely", f"On-axis phase differs by ~180 deg ({c:+.0f}) at all frequencies: inverted "
                                            "polarity (source normal pointing the other way, or the sign of the drive).",
                                            mean_offset_deg=c, rms_after_deg=res))
                    elif abs(abs(c) - 90.0) <= 25.0:
                        out.append(_finding("velocity_vs_acceleration_phase", "likely", f"On-axis phase differs by ~{c:+.0f} deg at all "
                                            "frequencies: a factor +-i, i.e. velocity vs acceleration (one integration) drive.",
                                            mean_offset_deg=c, rms_after_deg=res))
                    else:
                        out.append(_finding("constant_phase_offset", "possible", f"On-axis phase differs by a constant {c:+.0f} deg.",
                                            mean_offset_deg=c, rms_after_deg=res))
                else:
                    dist = abs(tau) * 343.0
                    out.append(_finding("propagation_delay", "likely", f"On-axis phase difference is a pure delay of {tau * 1e3:+.3f} ms "
                                        f"(about {dist * 100:.1f} cm of path at 343 m/s): the two sides reference phase to different "
                                        "distances (observation radius, or one side did not remove the propagation delay).",
                                        delay_ms=tau * 1e3, path_cm=dist * 100, rms_after_deg=res))
    # ---------------- angles
    for plane in ("H", "V"):
        m = cmp.maps.get(plane)
        if not m:
            continue
        A_, B_ = m["A"], m["B"]
        base = _rms(np.where((A_ > tol.map_floor_db) | (B_ > tol.map_floor_db), A_ - B_, np.nan))
        if base > 0.75 * tol.polar_map_db:
            mir = _rms(np.where((A_ > tol.map_floor_db) | (B_[:, ::-1] > tol.map_floor_db), A_ - B_[:, ::-1], np.nan))
            if mir < 0.4 * base and mir < tol.polar_map_db:
                out.append(_finding("mirrored_angles", "likely", f"The {plane} polar map matches B with the angle axis MIRRORED "
                                    f"(rms {base:.2f} -> {mir:.2f} dB): the sign of the {plane} angle is flipped in one tool "
                                    "(+angle should be toward +X on H and +Y on V in both).", plane=plane, rms_before=base,
                                    rms_after=mir))
    mh, mv = cmp.maps.get("H"), cmp.maps.get("V")
    if mh and mv:
        def err(x, y):
            return _rms(np.where((x > tol.map_floor_db) | (y > tol.map_floor_db), x - y, np.nan))
        base = 0.5 * (err(mh["A"], mh["B"]) + err(mv["A"], mv["B"]))
        swap = 0.5 * (err(mh["A"], mv["B"]) + err(mv["A"], mh["B"]))
        if base > tol.polar_map_db and swap < 0.5 * base and swap < 1.5 * tol.polar_map_db:
            out.append(_finding("hv_swapped", "likely", "H and V maps agree once swapped: the horizontal and vertical planes (or the "
                                "x/y axes of the mesh) are interchanged between the tools. Check the mesh orientation "
                                "(+X = horizontal) and the files named 'H *.txt' vs 'V *.txt'.", rms_before=base, rms_after=swap))
    # ---------------- radius note
    ra, rb = a.meta.get("distance_m"), b.meta.get("distance_m")
    if ra and rb and abs(ra - rb) > 1e-6 * ra:
        out.append(_finding("radius_differs", "info", f"Observation radius differs: A {ra:g} m, B {rb:g} m. Normalized patterns are "
                            "comparable only in the far field; absolute level differs by 20 log10(rB/rA).", rA=ra, rB=rb))
    # ---------------- frequency axis scale (geometry scaled): beamwidth shift
    if "beamwidth_H" in cmp.curves and f.size >= 8:
        ba, bb = cmp.curves["beamwidth_H"]["A"], cmp.curves["beamwidth_H"]["B"]
        base = _rms(ba - bb)
        if base > tol.beamwidth_deg and np.ptp(ba) > 5.0:
            best = None
            for k, name in FREQ_SCALES:
                fb = f * k
                if fb.min() >= f.min() and fb.max() <= f.max() * 1.0001:
                    shifted = np.interp(np.log(fb), np.log(f), bb)
                    r = _rms(ba - shifted)
                    if best is None or r < best[0]:
                        best = (r, k, name)
            if best and best[0] < 0.4 * base:
                out.append(_finding("frequency_scale", "possible", f"The beamwidth curve of B lines up with A after scaling its "
                                    f"frequency axis by {best[1]:g} ({best[2]}): the geometry scale (mm vs m vs inch) or the frequency "
                                    "units differ between the tools. Check Meshes > scale (must be 1 for a metre mesh).",
                                    scale=best[1], rms_before=base, rms_after=best[0]))
    # ---------------- ordinary things worth stating
    ra_rho = a.meta.get("rho")
    rb_rho = b.meta.get("rho")
    if ra_rho and rb_rho and abs(ra_rho - rb_rho) > 1e-4:
        out.append(_finding("air_density", "info", f"Air density differs (A {ra_rho:g}, B {rb_rho:g} kg/m^3): absolute pressure scales "
                            f"with it, {20 * np.log10(rb_rho / ra_rho):+.3f} dB expected. Negligible against the tolerances.",
                            rho_A=ra_rho, rho_B=rb_rho))
    return out
