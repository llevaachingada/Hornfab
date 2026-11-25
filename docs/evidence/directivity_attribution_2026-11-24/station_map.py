"""Empirical station map: beamwidth(f) ~ 2 x wall angle at a fixed meridian station (HEURISTIC, not physics).

For each anchor and plane, find the pre-roll arc fraction u*(f) where twice the anchor's wall angle equals
its measured -6 dB width. A candidate's predicted width change is GAIN x 2 x (its wall angle - the anchor's)
at u_eff(f) = u*(f) + k * SHIFT, where k is the fitted du/d(log2 f) of the map (SHIFT = 0.5 octave moves the
station toward the throat). SHIFT and GAIN per plane are fitted on the two already-solved variants
(rolled H+10/V+6, Lamé H mid-gain +2 mm) and printed with their residuals; Lamé V has no calibration
variant and borrows the rolled V gain. This assumes the wavefront detaches at a station that the
perturbation does not move; it ignores mouth diffraction, the return and higher-order modes. It is a
screening heuristic for predeclaring direction and rough size, never a substitute for a solve.

    .venv\\Scripts\\python.exe docs/evidence/directivity_attribution_2026-11-24/station_map.py
"""
import glob, json, sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.design.generators import rolled_cd_family, klangfilm_lame_hv_family  # noqa: E402

HERE = Path('docs/evidence/directivity_attribution_2026-11-24')
SRC = Path('docs/evidence/size_aware_2026-11-24')
ANCHOR = {'rolled': 'runs/rolled_lame_anchor_verify_2026-11-24/rolled', 'lame': 'runs/rolled_lame_anchor_verify_2026-11-24/lame'}
SOLVED = {'rolled_h10_v6': 'runs/20261124T222433Z-verify-4617d0', 'lame_hmid2': 'runs/20261124T222525Z-verify-b5497c'}
ADAPTER = {'rolled': rolled_cd_family, 'lame': klangfilm_lame_hv_family}
BAND = (1990.0, 8100.0)
SHIFT = {'H': 0.5, 'V': 0.0}


def metrics(run):
    return json.load(open(glob.glob(f'{run}/designs/*/metrics.json')[0], encoding='utf-8'))


def surface(family, knobs):
    cfg = yaml.safe_load((SRC / f'anchor_{family}_neutral.yaml').read_text(encoding='utf-8'))
    g = cfg['generator']
    spec = {k: g[k] for k in ('name', 'n_phi', 'n_s', 'span', 'wall_thickness_mm', 'rows')}
    ad = ADAPTER[family]
    block = ad.design_params(spec, {**cfg['seed_params'], **knobs}, cfg['brief'])['grid']
    return ad.resolve_grid(block, cfg['brief'])['inner_points']


def wall(points, plane):
    row = points[0 if plane == 'H' else -1]
    rad, z = row[:, 0 if plane == 'H' else 1], row[:, 2]
    f = int(np.argmax(z))
    ds = np.hypot(np.diff(z[:f + 1]), np.diff(rad[:f + 1]))
    u = np.r_[0.0, np.cumsum(ds)] / ds.sum()
    return u, np.degrees(np.arctan2(np.gradient(rad[:f + 1]), np.gradient(z[:f + 1])))


def station_map(points, m, plane):
    u, ang = wall(points, plane)
    env = np.maximum.accumulate(ang)                      # first station reaching each angle
    out = {}
    for f, bw in zip(m['freqs_hz'], m[f'bw_{plane.lower()}_deg']):
        if BAND[0] <= f <= BAND[1]:
            out[f] = float(np.interp(bw / 2.0, env, u))
    return out


def shifted(smap, plane):
    f = np.array(list(smap)); u = np.array(list(smap.values()))
    k = np.polyfit(np.log2(f), u, 1)[0]
    return {fi: ui + k * SHIFT[plane] for fi, ui in zip(f, u)}


def raw_delta(points, ref_pts, smap, plane):
    u, ang = wall(points, plane); ur, ar = wall(ref_pts, plane)
    return {f: 2.0 * (float(np.interp(us, u, ang)) - float(np.interp(us, ur, ar))) for f, us in shifted(smap, plane).items()}


def candidates(family):
    path = HERE / 'controls_geometry.json'
    data = json.loads(path.read_text(encoding='utf-8'))[family]
    return {k: v['change'] for k, v in data.items() if isinstance(v, dict) and 'change' in v and 'refused' not in v}


if __name__ == '__main__':
    report, gains = {}, {}
    calib = {'rolled': ('rolled_h10_v6', {'g_cd_h_deg': 10.0, 'g_cd_v_deg': 6.0}),
             'lame': ('lame_hmid2', {'g_cd_core_blend': 1.0, 'g_h_mid_gain_mm': 2.0})}
    refs, maps, anchors = {}, {}, {}
    for family in ('rolled', 'lame'):
        refs[family] = surface(family, {}); anchors[family] = metrics(ANCHOR[family])
        maps[family] = {p: station_map(refs[family], anchors[family], p) for p in 'HV'}
        label, change = calib[family]
        pts, sm = surface(family, change), metrics(SOLVED[label])
        for p in 'HV':
            raw = raw_delta(pts, refs[family], maps[family][p], p)
            base = dict(zip(anchors[family]['freqs_hz'], anchors[family][f'bw_{p.lower()}_deg']))
            got = dict(zip(sm['freqs_hz'], sm[f'bw_{p.lower()}_deg']))
            x = np.array(list(raw.values())); y = np.array([got[f] - base[f] for f in raw])
            if np.abs(x).max() > 0.5:
                g = float(x @ y / (x @ x))
                gains[(family, p)] = {'gain': round(g, 3), 'rms_after_gain_deg': round(float(np.sqrt(np.mean((g * x - y) ** 2))), 3),
                                      'calibrated_on': label}
    gains[('lame', 'V')] = {**gains[('rolled', 'V')], 'calibrated_on': 'borrowed from rolled V (no Lamé V calibration)'}
    for family in ('rolled', 'lame'):
        fam = {'shift_octaves': SHIFT, 'gain': {p: gains[(family, p)] for p in 'HV'},
               'station_u': {p: {f'{f:.0f}': round(u, 3) for f, u in maps[family][p].items()} for p in 'HV'}}
        for label, change in candidates(family).items():
            pts = surface(family, change)
            fam[label] = {'change': change, 'predicted_delta_deg': {
                p: {f'{f:.0f}': round(gains[(family, p)]['gain'] * d, 2)
                    for f, d in raw_delta(pts, refs[family], maps[family][p], p).items()} for p in 'HV'}}
        report[family] = fam
    (HERE / 'station_map.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    for family, fam in report.items():
        print(f"## {family}  gains {json.dumps(fam['gain'])}")
        freqs = list(fam['station_u']['H'])
        print('  ' + ' ' * 28 + ' '.join(f'{f:>6s}' for f in freqs))
        for label, info in fam.items():
            if not isinstance(info, dict) or 'predicted_delta_deg' not in info:
                continue
            for p, vals in info['predicted_delta_deg'].items():
                print(f'  {label:20s} {p} pred ', ' '.join(f'{v:+6.1f}' for v in vals.values()))
