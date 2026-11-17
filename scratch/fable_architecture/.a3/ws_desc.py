"""A3 whole-surface descriptors, version A3-WS-v1, from the A1/N1b canonical records.

Record source: scratch/fable_architecture/.n1b/build/*.npz (inner/outer at 65 arc-length stations x
61 azimuths, quarter sector 0..90 deg). The lecleach lane is excluded: N1b found its stored meshes
are not rebuildable at HEAD (X1B_CONTRACT_V2.md), so no valid canonical record exists for it.

A3-WS-v1 (404 numbers), all lengths mm, angles degrees:
  * 32 stations x (r_H, r_V, r_45)            half-widths in the H (phi=0), V (phi=90) and 45 deg planes
  * 32 stations x (z_H, z_V, z_45)            axial coordinate in those planes
  * 32 stations x (ang_H, ang_V, ang_45)      wall half-angle from the +z axis (atan2(dr, dz)); >90 = rolled
  * 32 stations x (area, aspect, shape)       full-section area (sector x 2pi/dphi), W/H, area/(W*H)
  * 20 scalars: mouth W/H, inner depth, outer envelope W/H/D, wall thickness, throat r_H/r_V/area/
    angles, lip curvature radius (H), lip wrap angle, rollback depth, forward-wall end fraction,
    non-monotone-z flag, sector angle, n_phi, n_s.

Writes .a3/ws_desc.pkl.
"""
import json
import pathlib
import pickle

import numpy as np

ROOT = pathlib.Path('scratch/fable_architecture')
SRC = ROOT / '.n1b/build'
NST = 32
EXCLUDE = {'hl__lecleach_hv_landscape_smooth_v7'}   # N1b: not reproducible at HEAD


def circ_radius(p0, p1, p2):
    a = np.linalg.norm(p1 - p0); b = np.linalg.norm(p2 - p1); c = np.linalg.norm(p2 - p0)
    s = 0.5 * (a + b + c)
    ar = max(s * (s - a) * (s - b) * (s - c), 0.0) ** 0.5
    return float(a * b * c / (4 * ar)) if ar > 1e-12 else float('nan')


def desc_one(z):
    inner = np.asarray(z['inner'], float)      # (61, 65, 3): phi, s, xyz mm
    outer = np.asarray(z['outer'], float) if z['outer'].size else np.zeros((0, 0, 3))
    nphi, ns, _ = inner.shape
    phis = np.degrees(np.arctan2(inner[:, 0, 1], inner[:, 0, 0]))
    sector = float(phis.max() - phis.min())
    t = np.linspace(0.0, 1.0, NST)
    s_old = np.linspace(0.0, 1.0, ns)
    # resample every azimuth meridian to 32 stations
    res = np.stack([np.stack([np.interp(t, s_old, inner[j, :, k]) for k in range(3)], -1)
                    for j in range(nphi)], 0)  # (nphi, NST, 3)
    iH, iV, i45 = 0, nphi - 1, int(round((nphi - 1) / 2))
    r = np.linalg.norm(res[:, :, :2], axis=2)
    rH, rV, r45 = r[iH], r[iV], r[i45]
    zH, zV, z45 = res[iH, :, 2], res[iV, :, 2], res[i45, :, 2]
    angH = np.degrees(np.arctan2(np.gradient(rH), np.gradient(zH)))
    angV = np.degrees(np.arctan2(np.gradient(rV), np.gradient(zV)))
    ang45 = np.degrees(np.arctan2(np.gradient(r45), np.gradient(z45)))
    # section: closed by the origin, quarter (or half) symmetry
    fac = 360.0 / sector
    area = np.empty(NST)
    for k in range(NST):
        xy = res[:, k, :2]
        x, y = xy[:, 0], xy[:, 1]
        # sector closed through the axis origin: drop the straight chord p_last -> p_first
        cr = x * np.roll(y, -1) - np.roll(x, -1) * y
        chord = x[-1] * y[0] - x[0] * y[-1]
        area[k] = 0.5 * abs(cr.sum() - chord) * fac
    aspect = rH / np.maximum(rV, 1e-9)
    shape = area / np.maximum(4.0 * rH * rV, 1e-9)
    # envelope (outer shell if present, else inner + thickness)
    wt = float(z['wall_thickness_mm'])
    if outer.size:
        W = 2 * float(np.max(np.abs(outer[:, :, 0])))
        H = 2 * float(np.max(np.abs(outer[:, :, 1])))
        D = float(outer[:, :, 2].max() - outer[:, :, 2].min())
    else:
        W = 2 * rH.max() + 2 * wt; H = 2 * rV.max() + 2 * wt; D = float(inner[:, :, 2].max()) + wt
    imax = int(np.argmax(zH))
    zmax = float(np.max(inner[:, :, 2]))
    scales = [float(rH[-1] * 2), float(rV[-1] * 2), float(np.max(inner[:, :, 2]) - np.min(inner[:, :, 2])),
              W, H, D, wt, float(rH[0]), float(rV[0]), float(area[0]),
              float(angH[0]), float(angV[0]),
              circ_radius(res[iH, -3], res[iH, -2], res[iH, -1]),
              float(angH[-1]), float(zmax - zH[-1]), float(imax / (NST - 1)),
              float(1.0 if np.any(np.diff(inner[:, :, 2], axis=1) < -1e-9) else 0.0),
              sector, float(nphi), float(ns)]
    vec = np.concatenate([rH, rV, r45, zH, zV, z45, angH, angV, ang45, area, aspect, shape, scales])
    names = ([f'r_{p}[{i}]' for p in ('H', 'V', '45') for i in range(NST)] +
             [f'z_{p}[{i}]' for p in ('H', 'V', '45') for i in range(NST)] +
             [f'ang_{p}[{i}]' for p in ('H', 'V', '45') for i in range(NST)] +
             [f'{q}[{i}]' for q in ('area', 'aspect', 'shape') for i in range(NST)] +
             ['mouth_W', 'mouth_H', 'inner_depth', 'env_W', 'env_H', 'env_D', 'wall_thickness',
              'throat_rH', 'throat_rV', 'throat_area', 'throat_angH', 'throat_angV',
              'lip_radius_H', 'lip_wrap_deg', 'rollback_depth', 'forward_end_frac',
              'nonmonotone_z', 'sector_deg', 'n_phi', 'n_s'])
    assert vec.size == len(names)
    return vec, names


recs = []
for f in sorted(SRC.glob('*.npz')):
    z = np.load(f)
    lane = str(z['lane'])
    if lane in EXCLUDE:
        print('excluded (N1b not reproducible at HEAD)', lane, str(z['design_hash']))
        continue
    vec, names = desc_one(z)
    recs.append(dict(lane=lane, run=str(z['run']), h=str(z['design_hash']), mode=str(z['mode']),
                     vec=vec.astype(float)))
print('records', len(recs), 'per lane', {g: sum(1 for r in recs if r['lane'] == g) for g in sorted({r['lane'] for r in recs})})
print('descriptor length', len(names))
V = np.asarray([r['vec'] for r in recs])
print('nonfinite', int((~np.isfinite(V)).sum()))
pickle.dump(dict(recs=recs, names=names, version='A3-WS-v1', n_st=32,
                 source='.n1b/build/*.npz (65x61, contract v2)', excluded=sorted(EXCLUDE)),
            open(ROOT / '.a3/ws_desc.pkl', 'wb'))
print('wrote ws_desc.pkl')
