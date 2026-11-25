"""CPU feasibility (no mesher, no solver): non-CD returned-lip rows parents rebuilt on the CD brief.

For each target design: rebuild the saved rows recipe on the CD brief (room_landscape_80x50_900_hf1440_v11cd,
taken from the rolled keeper config), report the original vs CD-brief driver, extents incl. 3 mm shell, the H/V
straight chord to the roll-on (max-z) station, the wall at 10/20/30/45 % of the pre-roll arc, the gap
(chord - wall at 30 %), and the solved backbone body angle theta_c for the predeclared recipes.

    .venv\Scripts\python.exe docs/evidence/cd_variants_2026-11-25/feasibility.py
"""
import json, math, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.config import load_config  # noqa: E402
from hornlab_search.design.generators import _cd_backbone_v1 as kernel  # noqa: E402
from hornlab_search.design.generators import grid as G  # noqa: E402

HERE = Path('docs/evidence/cd_variants_2026-11-25')
CD_CFG = Path('examples/typologies/cd_backbone_2026-11-25/rolled2_bb_control.yaml')
TARGETS = [
    ('lecleach_ar', 'runs/20261119T205130Z-screen-5dbd97', '5f7fbfc276b9'),
    ('lecleach', 'runs/20261116T040157Z-screen-402831', 'a85be6929ad5'),
    ('iwata_ar', 'runs/20261119T062638Z-screen-03ae3c', '06a008612260'),
    ('iwata_ar_b3bt', 'runs/20261027T085242Z-screen-c7d820', 'b01fcfa4b50a'),
    ('salmon_elliptical', 'runs/20261027T083216Z-screen-23544f', '63034eff4baf'),
    ('lecleach_asym', 'runs/20261027T064411Z-screen-019599', 'fd63b53adeaf'),
    ('lecleach_1in', 'runs/20261118T195131Z-screen-8cd85f', '5a5fa1c976c2'),
]
RECIPES = {'t25_r30': (0.25, 0.30), 't25_r20': (0.25, 0.20), 't30_r20': (0.30, 0.20)}


def wall(pts, row):
    r = pts[row]
    rho = np.hypot(r[:, 0], r[:, 1]); z = r[:, 2]
    f = int(np.argmax(z))
    ds = np.hypot(np.diff(z[:f + 1]), np.diff(rho[:f + 1]))
    u = np.r_[0.0, np.cumsum(ds)] / max(ds.sum(), 1e-12)
    ang = np.degrees(np.arctan2(np.gradient(rho[:f + 1]), np.gradient(z[:f + 1])))
    chord = math.degrees(math.atan2(rho[f] - rho[0], z[f] - z[0]))
    return {'forward_station': f, 'n': len(z), 'has_return': bool(f < len(z) - 2),
            'roll_on_z_mm': round(float(z[f] - z[0]), 1), 'roll_on_r_mm': round(float(rho[f]), 1),
            'chord_deg': round(chord, 1), 'wall_deg': [round(float(np.interp(x, u, ang)), 1) for x in (.1, .2, .3, .45)],
            'gap_at_30pct_deg': round(chord - float(np.interp(0.3, u, ang)), 1)}


def main():
    cd_brief = load_config(CD_CFG).brief
    out = {'cd_brief': cd_brief['name'], 'cd_driver': cd_brief['driver'], 'cd_envelope': cd_brief['envelope'],
           'targets': {}}
    for name, run, des in TARGETS:
        d = json.loads(Path(run, 'designs', des, 'design.json').read_text(encoding='utf-8'))
        rj = json.loads(Path(run, 'run.json').read_text(encoding='utf-8'))
        g = d['params']['grid']
        spec = {k: v for k, v in g.items() if k != 'knobs'}
        rec = {'run': run, 'design': des, 'rows': g['rows'], 'span': g.get('span', 'quarter'),
               'orig_brief': rj['config']['brief']['name'], 'orig_driver': rj['config']['brief']['driver'],
               'orig_envelope': rj['config']['brief']['envelope']}
        try:
            inner, meta = G.rows_grid_points(spec, g['knobs'], cd_brief)
            inner = np.asarray(inner, float)
            outer = G.grid_outer_points(inner, float(g.get('wall_thickness_mm', 3.0)))
            both = np.concatenate((inner.reshape(-1, 3), outer.reshape(-1, 3)))
            rec['extents_mm'] = [round(float(2 * np.max(abs(both[:, 0]))), 1),
                                 round(float(2 * np.max(abs(both[:, 1]))), 1), round(float(np.ptp(both[:, 2])), 1)]
            env = cd_brief['envelope']
            rec['fits_cd_envelope'] = bool(rec['extents_mm'][0] <= env['max_mouth_w_mm'] and
                                           rec['extents_mm'][1] <= env['max_mouth_h_mm'] and
                                           rec['extents_mm'][2] <= env['max_depth_mm'])
            rec['grid_shape'] = list(inner.shape)
            rec['H'], rec['V'] = wall(inner, 0), wall(inner, -1)
            bb = {}
            for key, (lt, lr) in RECIPES.items():
                try:
                    new, info = kernel.apply_to_inner(inner, {'bb_h': 1.0, 'bb_v': 1.0, 'bb_throat_frac': lt,
                                                              'bb_rollin_frac': lr})
                    bb[key] = {'theta_c_h_deg': info[0]['theta_c_deg'], 'theta_c_v_deg': info[-1]['theta_c_deg'],
                               'max_disp_mm': round(float(np.abs(new - inner).max()), 1)}
                except Exception as exc:
                    bb[key] = {'error': f'{type(exc).__name__}: {exc}'[:160]}
            rec['backbone_full_strength'] = bb
        except Exception as exc:
            rec['error'] = f'{type(exc).__name__}: {exc}'[:200]
        out['targets'][name] = rec
        if 'error' in rec:
            print(f'{name:18s} ERROR {rec["error"]}')
            continue
        print(f'{name:18s} {rec["orig_brief"][:34]:34s} drv {rec["orig_driver"]["exit_radius_mm"]:4.1f} span {rec["span"]:7s} '
              f'ext {rec["extents_mm"]} fit {rec["fits_cd_envelope"]} | H chord {rec["H"]["chord_deg"]} walls {rec["H"]["wall_deg"]} '
              f'gap {rec["H"]["gap_at_30pct_deg"]} | V chord {rec["V"]["chord_deg"]} walls {rec["V"]["wall_deg"]} gap {rec["V"]["gap_at_30pct_deg"]}')
        for k, v in rec['backbone_full_strength'].items():
            print(f'    {k}: {v}')
    (HERE / 'feasibility.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
