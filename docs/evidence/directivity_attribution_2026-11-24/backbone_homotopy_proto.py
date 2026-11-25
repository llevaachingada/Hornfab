"""PROTOTYPE (CPU only, not a generator): wall-angle homotopy from each parent row toward a CD backbone.

LABELED HYPOTHESIS, no published name. For every azimuth row of an anchor's inner point grid, the pre-roll part
(throat to that row's forward/max-z station) is rebuilt from a wall-angle schedule

    theta(u) = (1 - lam) * theta_parent(u) + lam * theta_bb(u; theta_c, lt, lr)

where theta_bb is the backbone of backbone_feasibility.py (C2 throat transition from the row's own throat angle,
conical body theta_c, C2 roll-in to the row's own tangent at the forward station). theta_c and the arc length are
solved so the rebuilt row lands exactly on its own forward station; every station after it (the return) and the
rim are untouched, and lam = 0 returns the parent arrays unchanged. lam(psi) = lam_H cos^2 psi + lam_V sin^2 psi.
Stations are re-sampled at the parent's arc fractions so the row keeps its station count.

    .venv\\Scripts\\python.exe docs/evidence/directivity_attribution_2026-11-24/backbone_homotopy_proto.py
"""
import json, math, sys
from pathlib import Path

import numpy as np
from scipy.optimize import fsolve

sys.path.insert(0, str(Path.cwd()))
HERE = Path('docs/evidence/directivity_attribution_2026-11-24')
sys.path.insert(0, str(HERE))
import station_map as sm  # noqa: E402
from backbone_feasibility import S  # noqa: E402


def row_profile(row):
    rho = np.hypot(row[:, 0], row[:, 1]); z = row[:, 2]
    f = int(np.argmax(z))
    ds = np.hypot(np.diff(z[:f + 1]), np.diff(rho[:f + 1]))
    u = np.r_[0.0, np.cumsum(ds)] / ds.sum()
    th = np.degrees(np.arctan2(np.gradient(rho[:f + 1]), np.gradient(z[:f + 1])))
    return rho, z, f, u, th, float(ds.sum())


def build(u_par, th_par, lam, thc, L, lt, lr, c=0.0, n=4001):
    """Blended schedule; c adds a C2 body bump (zero at throat and in the roll-in) to close the endpoint."""
    uu = np.linspace(0.0, 1.0, n)
    tp = np.interp(uu, u_par, th_par)
    t0, tf = th_par[0], th_par[-1]
    bb = t0 + (thc - t0) * S(uu / lt)
    bb = bb + (tf - thc) * S((uu - (1 - lr)) / lr)
    body = S((uu - 0.5 * lt) / (0.5 * lt)) * S(((1 - 0.5 * lr) - uu) / (0.5 * lr))
    th = (1 - lam) * tp + lam * bb + c * body
    t = np.radians(th)
    du = np.diff(uu) * L
    z = np.r_[0.0, np.cumsum(0.5 * (np.cos(t[1:]) + np.cos(t[:-1])) * du)]
    r = np.r_[0.0, np.cumsum(0.5 * (np.sin(t[1:]) + np.sin(t[:-1])) * du)]
    return uu, th, z, r


def _solve(f, x0):
    sol, _, ok, _ = fsolve(f, x0, full_output=True)
    if ok != 1 or np.max(np.abs(f(sol))) > 1e-6:
        raise ValueError('endpoint solve failed')
    return sol


def apply(inner, lam_h, lam_v, lt=0.15, lr=0.30):
    if lam_h == 0.0 and lam_v == 0.0:
        return inner, []
    out = inner.copy()
    h = inner[0, :, 0]; v = inner[-1, :, 1]
    info = []
    for j in range(inner.shape[0]):
        row = inner[j]
        rho, z, f, u, th, L0 = row_profile(row)
        psi = math.atan2(row[f, 1] / v[f], row[f, 0] / h[f])
        lam = lam_h * math.cos(psi) ** 2 + lam_v * math.sin(psi) ** 2
        if lam <= 1e-12:
            continue                                   # exact parent row
        zf, rf = z[f] - z[0], rho[f] - rho[0]
        # 1) the row's own full backbone (lam = 1): theta_c and arc length that land on the forward station
        thc, Lb = _solve(lambda x: (lambda r: [r[2][-1] - zf, r[3][-1] - rf])(build(u, th, 1.0, x[0], x[1], lt, lr)),
                         [math.degrees(math.atan2(rf, zf)), L0])
        # 2) blend, closing the endpoint with a body offset c and the arc length
        c, L = _solve(lambda x: (lambda r: [r[2][-1] - zf, r[3][-1] - rf])(build(u, th, lam, thc, x[1], lt, lr, c=x[0])),
                      [0.0, (1 - lam) * L0 + lam * Lb])
        uu, thn, zz, rr = build(u, th, lam, thc, L, lt, lr, c=c)
        z_new = z[0] + np.interp(u, uu, zz)
        r_new = rho[0] + np.interp(u, uu, rr)
        z_new[-1], r_new[-1] = z[f], rho[f]           # land exactly on the kept forward station
        if not np.all(np.diff(z_new) > 0):
            raise ValueError(f'row {j}: pre-roll z not monotone')
        if np.any(np.diff(r_new) < -1e-6):
            raise ValueError(f'row {j}: constriction before the roll')
        scale = r_new / rho[:f + 1]
        out[j, :f + 1, 0] = row[:f + 1, 0] * scale
        out[j, :f + 1, 1] = row[:f + 1, 1] * scale
        out[j, :f + 1, 2] = z_new
        info.append({'row': j, 'psi_deg': round(math.degrees(psi), 1), 'lam': round(lam, 3),
                     'theta_c': round(float(thc), 2), 'closure_c_deg': round(float(c), 3)})
    return out, info


if __name__ == '__main__':
    from hornlab_search.design.generators import grid
    report = {}
    for fam in ('rolled', 'lame'):
        pts = sm.surface(fam, {})
        for lam_h, lam_v in ((0.5, 0.0), (1.0, 0.0), (0.5, 0.5), (1.0, 1.0)):
            key = f'{fam}_lamH{lam_h}_lamV{lam_v}'
            try:
                new, info = apply(pts, lam_h, lam_v)
                outer = grid.grid_outer_points(new, 3.0)
                grid.check_self_approach(new, outer, 3.0)
                d = np.linalg.norm(new - pts, axis=2)
                rec = {'ok': True, 'max_disp_mm': round(float(d.max()), 2), 'rim_delta_mm': float(d[:, -1].max()),
                       'return_delta_mm': float(max(d[j, int(np.argmax(pts[j, :, 2])):].max() for j in range(pts.shape[0]))),
                       'extents_mm': [round(float(2 * np.abs(np.r_[new[..., 0].ravel(), outer[..., 0].ravel()]).max()), 1),
                                      round(float(2 * np.abs(np.r_[new[..., 1].ravel(), outer[..., 1].ravel()]).max()), 1),
                                      round(float(np.ptp(np.r_[new[..., 2].ravel(), outer[..., 2].ravel()])), 1)],
                       'theta_c_H': info[0]['theta_c'] if info and info[0]['row'] == 0 else None,
                       'theta_c_V': info[-1]['theta_c'] if info and info[-1]['row'] == pts.shape[0] - 1 else None,
                       'max_closure_c_deg': max(abs(i['closure_c_deg']) for i in info)}
                for p in 'HV':
                    u, a = sm.wall(new, p)
                    rec[f'{p}_wall_u.2/.3/.45'] = [round(float(np.interp(x, u, a)), 1) for x in (0.2, 0.3, 0.45)]
            except Exception as exc:
                rec = {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}
            report[key] = rec
            print(key, rec)
    (HERE / 'backbone_homotopy_proto.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
