"""Analytic R-OSSE reconstruction vs a sectioned reference CAD (angular_radii.npz).

Evaluates the pinned mesher's own R-OSSE formula (``hornlab_mesher.profile_formulas.profile_points``,
azimuth expressions in ``p`` are the mesher's ATH-style ``eval_param`` syntax) on every azimuth,
interpolates r(z) at the CAD's section stations, and reports per-station / per-meridian residuals.
Optionally least-squares refits a small parameter subset (``--fit``) so that the claimed recipe
and the CAD-best recipe are both on record.  Report-only; no geometry identity is created here.

Example (ST260-BLD, the transcription carried by the 2026-11-25 handoff)::

    .venv\\Scripts\\python.exe tools\\geometry\\rosse_reference_fit.py \\
        runs\\throat_sculpt_2026-11-25\\reference\\bld_stl\\angular_radii.npz \\
        --param R=130 r0=12.7 "a0=8-35*sin(p)^4" a=39.5 k=3 r=0.25 b=0.29 m=0.82 q=4.5 \\
        --zmax 50 --out runs\\throat_sculpt_2026-11-25\\reference\\bld_rosse_fit
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


def _num(v: str):
    try:
        return float(v)
    except ValueError:
        return v


def rosse_r_of_z(params: dict, phis: np.ndarray, z: np.ndarray, n: int = 2000) -> np.ndarray:
    from hornlab_mesher.profile_formulas import profile_points
    out = np.full((z.size, phis.size), np.nan)
    for j, ph in enumerate(phis):
        pts = np.asarray(profile_points(dict(params, type="R-OSSE"), n, float(ph)), float)
        x, y = pts[:, 0] - pts[0, 0], pts[:, 1]
        k = int(np.argmax(np.diff(x) <= 0)) + 1 if np.any(np.diff(x) <= 0) else x.size
        x, y = x[:k], y[:k]                      # forward branch only (rolled lips fold back)
        out[:, j] = np.where(z <= x[-1], np.interp(z, x, y), np.nan)
    return out


def compare(npz: Path, params: dict, zmax: float, phi_step_deg: float = 5.0) -> dict:
    d = np.load(npz)
    z_all, phi_all, r_all = d["z_mm"], d["phi_rad"], d["r_mm"]
    zsel = z_all <= zmax
    jsel = np.arange(0, phi_all.size, max(1, int(round(phi_step_deg / (360 / phi_all.size)))))
    jsel = jsel[phi_all[jsel] <= math.pi / 2 + 1e-9]
    z, phis = z_all[zsel], phi_all[jsel]
    ref = r_all[zsel][:, jsel]
    # The CAD may be rotated by a quarter turn vs the formula's p origin; test both.
    best = None
    for rot in (0.0, 0.5 * math.pi):
        ana = rosse_r_of_z(params, phis + rot, z)
        err = ana - ref
        rms = float(np.sqrt(np.nanmean(err ** 2)))
        if best is None or rms < best["rms_mm"]:
            best = {"rotation_deg": math.degrees(rot), "rms_mm": rms,
                    "max_abs_mm": float(np.nanmax(np.abs(err))), "err": err, "ana": ana}
    err = best.pop("err")
    ana = best.pop("ana")
    per_phi = {f"{math.degrees(p):.1f}": float(np.sqrt(np.nanmean(err[:, i] ** 2))) for i, p in enumerate(phis)}
    i_min = np.unravel_index(np.nanargmin(ana), ana.shape)
    j_ref = np.unravel_index(np.nanargmin(ref), ref.shape)
    best.update({"per_phi_rms_mm": per_phi, "z_range_mm": [float(z[0]), float(z[-1])],
                 "analytic_r_min_mm": float(ana[i_min]), "analytic_r_min_z_mm": float(z[i_min[0]]),
                 "analytic_r_min_phi_deg": float(math.degrees(phis[i_min[1]])),
                 "cad_r_min_mm": float(ref[j_ref]), "cad_r_min_z_mm": float(z[j_ref[0]]),
                 "cad_r_min_phi_deg": float(math.degrees(phis[j_ref[1]]))})
    # initial wall angle per meridian (slope over the first 0.5 mm) for both
    k = int(np.argmin(np.abs(z - 0.5)))
    best["initial_angle_deg"] = {
        f"{math.degrees(p):.0f}": {"cad": math.degrees(math.atan((ref[k, i] - ref[0, i]) / (z[k] - z[0]))),
                                   "analytic": math.degrees(math.atan((ana[k, i] - ana[0, i]) / (z[k] - z[0])))}
        for i, p in enumerate(phis) if abs(math.degrees(p) % 22.5) < 1e-6}
    return best


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("npz")
    ap.add_argument("--param", nargs="+", required=True, help="name=value (value may be a p-expression)")
    ap.add_argument("--zmax", type=float, default=50.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    params = {kv.split("=", 1)[0]: _num(kv.split("=", 1)[1]) for kv in a.param}
    res = compare(Path(a.npz), params, a.zmax)
    res["params"] = params
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "fit.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
