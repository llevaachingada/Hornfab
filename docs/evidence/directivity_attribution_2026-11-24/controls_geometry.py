"""Matched fixed-candidate controls for the rolled and Lamé anchors. CPU geometry only; no solver.

Reproduce from the repository root:
    .venv\\Scripts\\python.exe docs/evidence/directivity_attribution_2026-11-24/controls_geometry.py

Reads the neutral anchor configs in docs/evidence/size_aware_2026-11-24/, writes one fixed-seed YAML per
candidate next to this script and controls_geometry.json (displacements, lip/throat/return parity,
extents, meridian wall-angle samples, and the rolled H+V geometric superposition check).
"""
import copy, json, math, sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.design.generators import rolled_cd_family, klangfilm_lame_hv_family  # noqa: E402

SRC = Path('docs/evidence/size_aware_2026-11-24')
DEST = Path('docs/evidence/directivity_attribution_2026-11-24')

# Every candidate changes only the listed knobs of its neutral anchor.
ROLLED = {
    'rolled_h10_v0': {'g_cd_h_deg': 10.0},                         # H-only control, original window
    'rolled_h0_v6': {'g_cd_v_deg': 6.0},                          # V-only control, original window
    'rolled_h10_v6': {'g_cd_h_deg': 10.0, 'g_cd_v_deg': 6.0},     # = the verified combined variant (geometry ref)
    'rolled_h10_early': {'g_cd_h_deg': 10.0, 'g_cd_start_s': 0.12, 'g_cd_peak_s': 0.40, 'g_cd_end_s': 0.65},
    'rolled_h20_early': {'g_cd_h_deg': 20.0, 'g_cd_start_s': 0.12, 'g_cd_peak_s': 0.40, 'g_cd_end_s': 0.65},
    'rolled_h10_late': {'g_cd_h_deg': 10.0, 'g_cd_start_s': 0.55, 'g_cd_peak_s': 0.75, 'g_cd_end_s': 0.94},
}
LAME = {
    'lame_morph_040': {'g_morph_frac': 0.40},                     # earlier round-to-Lamé transition
    'lame_morph_085': {'g_morph_frac': 0.85},                     # later round-to-Lamé transition
    'lame_hmid_m2': {'g_cd_core_blend': 1.0, 'g_h_mid_gain_mm': -2.0},   # sign mirror of the solved +2 mm
}
U = [0.0, 0.05, 0.10, 0.20, 0.30, 0.45, 0.60, 0.75, 0.88, 1.0]


def load(name):
    return yaml.safe_load((SRC / f'anchor_{name}_neutral.yaml').read_text(encoding='utf-8'))


def spec_of(cfg):
    g = copy.deepcopy(cfg['generator'])
    return {k: g[k] for k in ('name', 'n_phi', 'n_s', 'span', 'wall_thickness_mm', 'rows')}


def resolve(adapter, cfg, knobs):
    brief = cfg['brief']
    block = adapter.design_params(spec_of(cfg), knobs, brief)['grid']
    return adapter.resolve_grid(block, brief)


def meridian(points, axis):
    """Station wall angle (deg from axis) against normalized arc to the forward (max-z) station."""
    row = points[0 if axis == 'H' else -1]
    rad = row[:, 0 if axis == 'H' else 1]
    z = row[:, 2]
    f = int(np.argmax(z))
    ds = np.hypot(np.diff(z[:f + 1]), np.diff(rad[:f + 1]))
    u = np.r_[0.0, np.cumsum(ds)] / np.sum(ds)
    ang = np.degrees(np.arctan2(np.gradient(rad[:f + 1]), np.gradient(z[:f + 1])))
    return u, ang, rad, z, f


def angle_samples(points, axis):
    u, ang, rad, z, f = meridian(points, axis)
    return {'u': U, 'wall_deg': [round(float(np.interp(x, u, ang)), 3) for x in U],
            'z_mm': [round(float(np.interp(x, u, z[:f + 1])), 3) for x in U],
            'r_mm': [round(float(np.interp(x, u, rad[:f + 1])), 3) for x in U],
            'forward_station': f, 'pre_roll_arc_mm': round(float(np.sum(np.hypot(np.diff(z[:f + 1]), np.diff(rad[:f + 1])))), 3)}


def compare(ref, test):
    a, b = ref['inner_points'], test['inner_points']
    d = np.linalg.norm(b - a, axis=2)
    n = a.shape[1]
    out = {'inner_max_delta_mm': float(d.max()), 'throat_station_max_delta_mm': float(d[:, 0].max()),
           'first_5pct_max_delta_mm': float(d[:, :max(2, int(.05 * n))].max()),
           'lip_max_delta_mm': float(d[:, -1].max()), 'final_10pct_max_delta_mm': float(d[:, int(.9 * n):].max())}
    for axis in ('H', 'V'):
        _, _, _, _, f = meridian(a, axis)
        r = 0 if axis == 'H' else -1
        out[f'{axis}_return_after_forward_max_delta_mm'] = float(d[r, f:].max())
        out[f'{axis}_return_to_curve_max_mm'] = curve_distance(b[r, f:], a[r, max(f - 1, 0):])
    out['rim_to_curve_max_mm'] = curve_distance(b[:, -1], a[:, -1])
    return out


def curve_distance(points, ref):
    """Max distance from sampled points to the dense reference polyline (sampling-invariant)."""
    t = np.linspace(0.0, 1.0, 40)[:, None]
    dense = np.concatenate([ref[i] + t * (ref[i + 1] - ref[i]) for i in range(len(ref) - 1)])
    return float(max(np.min(np.linalg.norm(dense - q, axis=1)) for q in points))


def extents(res):
    both = np.concatenate((res['inner_points'].reshape(-1, 3), res['outer_points'].reshape(-1, 3)))
    return [round(float(2 * np.max(abs(both[:, 0]))), 3), round(float(2 * np.max(abs(both[:, 1]))), 3),
            round(float(np.ptp(both[:, 2])), 3)]


def write_config(base, label, knobs, note):
    cfg = copy.deepcopy(base)
    cfg['name'] = f'{label}_2026_11_24'
    cfg['description'] = note
    cfg['seed_params'] = knobs
    cfg['bounds'] = {k: {'lo': v, 'hi': v, 'search': False} for k, v in knobs.items()}
    (DEST / f'{label}.yaml').write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8')


report = {}
for family, cases, adapter in (('rolled', ROLLED, rolled_cd_family), ('lame', LAME, klangfilm_lame_hv_family)):
    base = load(family)
    neutral_knobs = dict(base['seed_params'])
    ref = resolve(adapter, base, neutral_knobs)
    fam = {'neutral': {'extents_mm': extents(ref), 'H': angle_samples(ref['inner_points'], 'H'),
                       'V': angle_samples(ref['inner_points'], 'V'), 'digest': adapter.implementation_digest()}}
    deltas = {}
    for label, change in cases.items():
        knobs = {**neutral_knobs, **change}
        try:
            res = resolve(adapter, base, knobs)
        except Exception as exc:                     # a refusal is a result
            fam[label] = {'change': change, 'refused': f'{type(exc).__name__}: {exc}'}
            continue
        deltas[label] = res['inner_points'] - ref['inner_points']
        fam[label] = {'change': change, 'extents_mm': extents(res), **compare(ref, res),
                      'H': angle_samples(res['inner_points'], 'H'), 'V': angle_samples(res['inner_points'], 'V')}
        if family == 'lame' and 'core_info' in res['meta']:
            fam[label]['phase_a_core_info'] = res['meta']['core_info']
        note = (f'FIXED CANDIDATE 2026-11-24 ({family}): neutral anchor '
                f'docs/evidence/size_aware_2026-11-24/anchor_{family}_neutral.yaml with only {change} changed. '
                'Same brief, source, mesh and solve settings; verify-grid comparison only within this group.')
        write_config(base, label, knobs, note)
    if family == 'rolled' and {'rolled_h10_v0', 'rolled_h0_v6', 'rolled_h10_v6'} <= set(deltas):
        s = deltas['rolled_h10_v0'] + deltas['rolled_h0_v6'] - deltas['rolled_h10_v6']
        fam['superposition_max_residual_mm'] = float(np.abs(s).max())
    report[family] = fam

(DEST / 'controls_geometry.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
for family, fam in report.items():
    print(f'## {family}  neutral extents {fam["neutral"]["extents_mm"]}')
    for label, info in fam.items():
        if label in ('neutral',) or not isinstance(info, dict):
            continue
        if 'refused' in info:
            print(f'  {label:18s} REFUSED {info["refused"]}')
            continue
        print(f'  {label:18s} ext {info["extents_mm"]} max {info["inner_max_delta_mm"]:.3f} throat '
              f'{info["throat_station_max_delta_mm"]:.4f} lip {info["lip_max_delta_mm"]:.4f} '
              f'last10% {info["final_10pct_max_delta_mm"]:.4f} Hret {info["H_return_after_forward_max_delta_mm"]:.4f} '
              f'Vret {info["V_return_after_forward_max_delta_mm"]:.4f} | to-curve Hret {info["H_return_to_curve_max_mm"]:.4f} '
              f'Vret {info["V_return_to_curve_max_mm"]:.4f} rim {info["rim_to_curve_max_mm"]:.4f}')
        print(f'      H wall {info["H"]["wall_deg"]}')
        print(f'      V wall {info["V"]["wall_deg"]}')
    print(f'  neutral H wall {fam["neutral"]["H"]["wall_deg"]}')
    print(f'  neutral V wall {fam["neutral"]["V"]["wall_deg"]}')
    if 'superposition_max_residual_mm' in fam:
        print(f'  superposition residual (H-only + V-only - combined) {fam["superposition_max_residual_mm"]:.3e} mm')
