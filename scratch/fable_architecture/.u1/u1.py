"""N4 / U1: can a layered form reproduce existing horns?

For the best valid design of each lane that passed N1b (rolled substitutes for lecleach):
  * target surface = the contract-v2 record (65 stations x 61 azimuths) built from the generator;
  * three ribs at azimuth 0, 45, 90 degrees; per rib the wall angle psi from one station to the next;
  * ribs rebuilt from psi alone (a trigonometric identity check, must return within 0.01 mm);
  * section at each station = superellipse through r(0) and r(90) with exponent p fitted to r(45),
    clipped to [1, 16]; p clipped where the 45-degree radius cannot be matched;
  * depth at each azimuth = piecewise-linear in the superellipse's own parametric angle theta through
    the three ribs' depths (the runbook leaves the blend open; this is the section's own blend);
  * repeat with psi replaced by a Pchip spline through 4, 6, 8 equally spaced control values.

Writes .u1/u1.json and .u1/<lane>.png (five section overlays). Read-only; no mesh build, no solve.
"""
import sys, json, pathlib, importlib.util as ilu, warnings
import numpy as np

sys.path.insert(0, 'scratch/fable_architecture/.n1'); sys.path.insert(0, '.')
warnings.filterwarnings('ignore')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator
from hornlab_search.config import load_config
from tools.geometry import klangfilm_lame_cli

_spec = ilu.spec_from_file_location('n1_build', 'scratch/fable_architecture/.n1/build.py')
NB = ilu.module_from_spec(_spec); _spec.loader.exec_module(NB)

ROOT = pathlib.Path('scratch/fable_architecture')
OUT = ROOT / '.u1'
NS, NPHI = 65, 61
PHI_IDX = (0, NPHI // 2, NPHI - 1)          # 0, 45, 90 degrees
LANES = ['hl__ext_throat_hvlaw_v7', 'hl__biradial_es_style_v7', 'hl__crowe_x_osse_cd_v7',
         'rf__section_axial_home_v7', 'hl__klangfilm_lame_curved_v1']
KL = 'hl__klangfilm_lame_curved_v1'
CUR = klangfilm_lame_cli.implementation_digest()


def best_design(rows, lane):
    rr = [r for r in rows if r['config'] == lane and r['ok'] and r['J'] is not None]
    if lane == KL:
        def dig(r):
            p = json.loads((pathlib.Path('runs') / r['run'] / 'designs' / r['h'] /
                            'design.json').read_text())['params']
            return ((p.get('grid') or {}).get('rows') or {}).get('implementation_sha256')
        rr = [r for r in rr if dig(r) == CUR]
    return min(rr, key=lambda r: r['J'])


def rib_geometry(inner, j):
    """r, z, azimuth, step lengths and wall angles psi for one record rib (record is [phi, station, 3])."""
    p = inner[j, :, :]
    r = np.hypot(p[:, 0], p[:, 1])
    z = p[:, 2]
    phi = np.unwrap(np.arctan2(p[:, 1], p[:, 0]))
    ds = np.linalg.norm(np.diff(p, axis=0), axis=1)
    dr = np.diff(r); dz = np.diff(z)
    psi = np.arctan2(dr, dz)                       # angle of the step from the +z axis
    return r, z, phi, ds, psi


def rebuild_rib(r0, z0, ds, psi, phi0):
    r = np.empty(NS); z = np.empty(NS)
    r[0], z[0] = r0, z0
    for i in range(NS - 1):
        r[i + 1] = r[i] + ds[i] * np.sin(psi[i])
        z[i + 1] = z[i] + ds[i] * np.cos(psi[i])
    return r, z


def solve_p(a, b, r45):
    """Superellipse exponent p with r(45) == r45; clipped to [1, 16]."""
    c = np.cos(np.pi / 4)

    def f(p):
        return ((c / a) ** p + (c / b) ** p) ** (-1.0 / p)

    lo, hi = 1.0, 16.0
    if r45 <= f(lo):
        return lo, 'low'
    if r45 >= f(hi):
        return hi, 'high'
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if f(mid) < r45:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi), None


def section_radius(phi, a, b, p):
    return ((np.abs(np.cos(phi)) / a) ** p + (np.abs(np.sin(phi)) / b) ** p) ** (-1.0 / p)


def theta_of(r, phi, a, b, p):
    x = r * np.cos(phi); y = r * np.sin(phi)
    return np.arctan2(np.maximum(np.abs(y) / b, 1e-15) ** (p / 2),
                      np.maximum(np.abs(x) / a, 1e-15) ** (p / 2))


def blend_depth(th, z0, z45, z90, th45):
    lo = z0 + (z45 - z0) * th / th45 if th45 > 0 else z0
    hi = z45 + (z90 - z45) * (th - th45) / (np.pi / 2 - th45)
    return np.where(th <= th45, lo, hi)


def rebuild(inner, psi_ribs):
    """psi_ribs: dict j -> psi array. Returns surface (NS, NPHI, 3) and clip info."""
    ribs = {}
    for j in PHI_IDX:
        r, z, phi, ds, psi = rib_geometry(inner, j)
        rr, zz = rebuild_rib(r[0], z[0], ds, psi_ribs[j], phi[0])
        ribs[j] = (rr, zz, phi)
    out = np.empty((NPHI, NS, 3))
    clips = []
    for i in range(NS):
        a = ribs[PHI_IDX[0]][0][i]; b = ribs[PHI_IDX[2]][0][i]
        r45 = ribs[PHI_IDX[1]][0][i]
        p, why = solve_p(a, b, r45)
        clips.append(why)
        z0 = ribs[PHI_IDX[0]][1][i]; z45 = ribs[PHI_IDX[1]][1][i]; z90 = ribs[PHI_IDX[2]][1][i]
        r45cos = section_radius(np.pi / 4, a, b, p)
        th45 = theta_of(np.array([r45cos]), np.array([np.pi / 4]), a, b, p)[0]
        for jj in range(NPHI):
            phi = np.arctan2(inner[jj, i, 1], inner[jj, i, 0])
            rr = section_radius(phi, a, b, p)
            th = theta_of(np.array([rr]), np.array([phi]), a, b, p)[0]
            out[jj, i, 0] = rr * np.cos(phi)
            out[jj, i, 1] = rr * np.sin(phi)
            out[jj, i, 2] = blend_depth(th, z0, z45, z90, th45)
    return out, clips


def region(station, phi_idx):
    if station < int(0.10 * (NS - 1)):
        z = 'throat'
    elif station > int(0.85 * (NS - 1)):
        z = 'lip'
    else:
        z = 'body'
    az = 'corner' if 20 <= phi_idx <= 40 else ''
    return (z + ('/' + az if az else ''))


def stats(dev, phi_deg):
    """dev is [phi_index, station] (record layout)."""
    worst = np.unravel_index(np.argmax(dev), dev.shape)
    j, i = int(worst[0]), int(worst[1])
    return dict(median_mm=float(np.median(dev)), p95_mm=float(np.quantile(dev, 0.95)),
                worst_mm=float(dev.max()), worst_station=i, worst_phi_index=j,
                worst_phi_deg=float(phi_deg[j, i]), worst_region=region(i, j))


def rib_interp(inner, idxs):
    """Section and depth at every azimuth from radii/depths at M ribs (Pchip in azimuth)."""
    out = np.empty((NPHI, NS, 3))
    for i in range(NS):
        phi_k = np.array([np.arctan2(inner[j, i, 1], inner[j, i, 0]) for j in idxs])
        r_k = np.array([np.hypot(inner[j, i, 0], inner[j, i, 1]) for j in idxs])
        z_k = np.array([inner[j, i, 2] for j in idxs])
        phi = np.array([np.arctan2(inner[jj, i, 1], inner[jj, i, 0]) for jj in range(NPHI)])
        if np.all(np.diff(phi_k) > 1e-12):
            r = PchipInterpolator(phi_k, r_k)(phi); z = PchipInterpolator(phi_k, z_k)(phi)
        else:
            r = np.interp(phi, phi_k, r_k); z = np.interp(phi, phi_k, z_k)
        out[:, i, 0] = r * np.cos(phi); out[:, i, 1] = r * np.sin(phi); out[:, i, 2] = z
    return out


def overlay(inner, rebuilt, lane, path):
    fig, axes = plt.subplots(1, 5, figsize=(15, 3.4))
    for ax, i in zip(axes, np.linspace(0, NS - 1, 5).astype(int)):
        ax.plot(inner[:, i, 0], inner[:, i, 1], 'k-', lw=1.4, label='target')
        ax.plot(rebuilt[:, i, 0], rebuilt[:, i, 1], 'r--', lw=1.0, label='rebuild')
        ax.set_aspect('equal'); ax.set_title('station %d' % i)
        ax.set_xlim(left=0); ax.set_ylim(bottom=0)
    axes[0].legend(fontsize=7)
    fig.suptitle(lane + ' — section outlines, target vs layered rebuild')
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    import pickle
    OUT.mkdir(parents=True, exist_ok=True)
    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    res = {}
    for lane in LANES:
        r = best_design(rows, lane)
        cfg = load_config(pathlib.Path('runs') / r['run'] / 'config.yaml')
        inner, outer, mode, prov, t = NB.build_one(lane, r, cfg, 10.0)
        target = NB.sample(inner, NPHI, NS)
        # rib identity check
        identity = {}
        base = {}
        for j in PHI_IDX:
            rib_r, rib_z, phi, ds, psi = rib_geometry(target, j)
            rr, zz = rebuild_rib(rib_r[0], rib_z[0], ds, psi, phi[0])
            identity[j] = float(max(np.abs(rr - rib_r).max(), np.abs(zz - rib_z).max()))
            base[j] = psi
        reb, clips = rebuild(target, base)
        phi_deg = np.degrees(np.arctan2(target[..., 1], target[..., 0]))
        dev = np.linalg.norm(reb - target, axis=-1)
        entry = dict(lane=lane, h=r['h'], run=r['run'], J=float(r['J']), mode=mode,
                     native_shape=list(np.shape(inner)), wall=t,
                     rib_identity_max_mm=max(identity.values()),
                     clip_low=sum(1 for c in clips if c == 'low'),
                     clip_high=sum(1 for c in clips if c == 'high'),
                     exact=stats(dev, phi_deg), splines={}, extra_ribs={})
        overlay(target, reb, lane, OUT / (lane.replace('__', '_') + '.png'))
        for k in (4, 6, 8):
            ctrl = np.linspace(0, NS - 2, k).astype(int)
            sp = {j: PchipInterpolator(ctrl, base[j][ctrl], extrapolate=True)(np.arange(NS - 1))
                  for j in PHI_IDX}
            reb_k, _ = rebuild(target, sp)
            entry['splines'][str(k)] = stats(np.linalg.norm(reb_k - target, axis=-1), phi_deg)
        for m in (5, 9, 17):
            idxs = list(np.linspace(0, NPHI - 1, m).astype(int))
            reb_m = rib_interp(target, idxs)
            entry['extra_ribs'][str(m)] = dict(
                azimuth_deg=[float(np.degrees(np.arctan2(target[j, 0, 1], target[j, 0, 0])))
                             for j in idxs],
                **stats(np.linalg.norm(reb_m - target, axis=-1), phi_deg))
        res[lane] = entry
        print(json.dumps(entry), flush=True)
    json.dump(res, open(OUT / 'u1.json', 'w'), indent=1)

    print('\nSUMMARY (own-rib exact-psi layered rebuild, 65 x 61)')
    npass = 0
    for lane in LANES:
        e = res[lane]['exact']
        ok = e['worst_mm'] <= 0.5
        npass += ok
        print('%-38s median %.3f p95 %.3f worst %.3f (%s, station %d, phi %.1f deg) %s  clips low/high %d/%d'
              % (lane, e['median_mm'], e['p95_mm'], e['worst_mm'], e['worst_region'],
                 e['worst_station'], e['worst_phi_deg'], 'PASS' if ok else 'fail',
                 res[lane]['clip_low'], res[lane]['clip_high']), flush=True)
        x = res[lane]['extra_ribs']
        print('    extra ribs: 5 (%s deg) worst %.2f | 9 (%s deg) worst %.2f' %
              (x['5']['azimuth_deg'][:3], x['5']['worst_mm'],
               x['9']['azimuth_deg'][:3], x['9']['worst_mm']), flush=True)
    print('lanes at or under 0.5 mm: %d / %d' % (npass, len(LANES)))


if __name__ == '__main__':
    main()
