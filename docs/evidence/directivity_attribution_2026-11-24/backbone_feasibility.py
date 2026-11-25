"""CPU feasibility of a CD wall-angle backbone that keeps each anchor's forward (roll-on) station and return.

LABELED HYPOTHESIS, no published name, no solver call. For each anchor meridian (H, V) the parent pre-roll wall is
replaced, on paper, by a prescribed wall-angle schedule in arc length s:

    theta(s) = theta_0 + (theta_c - theta_0) * S(s / Lt)          throat transition (C2 quintic S)
             -> theta_c                                            conical body
             -> theta_c + (theta_f - theta_c) * S((s - (L - Lr)) / Lr)   terminal roll-in to the parent's
                                                                   tangent at the forward station

with theta_0 = the driver exit angle (2 deg, the brief's assumption) and theta_f = the parent's own wall angle at the
forward station, so the existing return attaches with the same tangent. Two unknowns (theta_c, L) are solved so the
integrated wall lands exactly on the parent's forward station (z_f, r_f). The return after it is untouched.

    .venv\\Scripts\\python.exe docs/evidence/directivity_attribution_2026-11-24/backbone_feasibility.py
"""
import json, math, sys
from pathlib import Path

import numpy as np
from scipy.optimize import fsolve

sys.path.insert(0, str(Path.cwd()))
HERE = Path('docs/evidence/directivity_attribution_2026-11-24')
sys.path.insert(0, str(HERE))
import station_map as sm  # noqa: E402


def S(x):
    x = np.clip(x, 0.0, 1.0)
    return x ** 3 * (10 - 15 * x + 6 * x * x)


def profile(theta0, thc, thf, L, lt, lr, n=2001):
    s = np.linspace(0.0, L, n)
    th = theta0 + (thc - theta0) * S(s / (lt * L))
    th = th + (thf - thc) * S((s - (1 - lr) * L) / (lr * L))
    t = np.radians(th)
    ds = np.diff(s)
    z = np.r_[0.0, np.cumsum(0.5 * (np.cos(t[1:]) + np.cos(t[:-1])) * ds)]
    r = np.r_[0.0, np.cumsum(0.5 * (np.sin(t[1:]) + np.sin(t[:-1])) * ds)]
    return s, th, z, r


def solve(r0, zf, rf, theta0, thf, lt, lr):
    def eq(x):
        thc, L = x
        _, _, z, r = profile(theta0, thc, thf, L, lt, lr)
        return [z[-1] - zf, r0 + r[-1] - rf]
    guess = [math.degrees(math.atan2(rf - r0, zf)), math.hypot(zf, rf - r0)]
    (thc, L), info, ok, msg = fsolve(eq, guess, full_output=True)
    return thc, L, ok == 1


def main():
    report = {}
    for fam in ('rolled', 'lame'):
        pts = sm.surface(fam, {})
        for plane, row in (('H', 0), ('V', -1)):
            rr = pts[row]
            rho = np.hypot(rr[:, 0], rr[:, 1]); z = rr[:, 2]
            f = int(np.argmax(z))
            u, ang = sm.wall(pts, plane)
            thf = float(ang[-1])
            out = {'forward_station_mm': [round(float(z[f]), 2), round(float(rho[f]), 2)],
                   'parent_tangent_at_forward_deg': round(thf, 2),
                   'chord_angle_deg': round(math.degrees(math.atan2(rho[f] - rho[0], z[f] - z[0])), 2), 'cases': {}}
            for lt, lr in ((0.10, 0.25), (0.15, 0.30), (0.20, 0.35)):
                thc, L, ok = solve(float(rho[0]), float(z[f] - z[0]), float(rho[f]), 2.0, thf, lt, lr)
                s, th, zz, r = profile(2.0, thc, thf, L, lt, lr)
                uu = s / L
                out['cases'][f'lt{lt:.2f}_lr{lr:.2f}'] = {
                    'solved': bool(ok), 'theta_c_deg': round(float(thc), 2), 'two_theta_c_deg': round(2 * float(thc), 1),
                    'arc_mm': round(float(L), 1), 'monotone_radius': bool(np.all(np.diff(r) >= -1e-9)),
                    'wall_deg_at_u': {str(x): round(float(np.interp(x, uu, th)), 1) for x in (0.1, 0.2, 0.3, 0.45, 0.6, 0.75, 0.9)},
                    'parent_wall_deg_at_u': {str(x): round(float(np.interp(x, u, ang)), 1) for x in (0.1, 0.2, 0.3, 0.45, 0.6, 0.75, 0.9)}}
            report[f'{fam}_{plane}'] = out
    (HERE / 'backbone_feasibility.json').write_text(json.dumps(report, indent=2) + chr(10), encoding='utf-8')
    for k, v in report.items():
        print(f"{k}: forward {v['forward_station_mm']} chord {v['chord_angle_deg']} parent tangent at forward {v['parent_tangent_at_forward_deg']}")
        for c, d in v['cases'].items():
            print(f"   {c}: ok={d['solved']} theta_c={d['theta_c_deg']} (2x {d['two_theta_c_deg']}) arc {d['arc_mm']} monotone={d['monotone_radius']}")
            print(f"      backbone wall u.1-.9 {list(d['wall_deg_at_u'].values())}   parent {list(d['parent_wall_deg_at_u'].values())}")


if __name__ == '__main__':
    main()
