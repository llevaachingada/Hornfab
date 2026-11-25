r"""favL on the +-5 deg brief with a box that can REACH 80 x 50 (2026-11-25 18:10).

osse_rollback's a(phi) = a_h cos^2 + a_v sin^2 is the coverage half-angle law: the favL best (a_h 33.1, a_v 31.0)
measures ~66 H x 62 V. 80 x 50 needs ~40 / 25, but favl_pm5 inherited the continuation box (a_h <= 34.5,
a_v >= 27.5), tuned for the old zero-cost corridor. Widen to the legal law (grid.py ROWS_OSSE_ROLL_A_RANGE 5-85; k, n
> 0; s >= 0) where it matters, and seed at a_h 40 / a_v 25 with L chosen so the mouth fits the open 575 mm cap.

    .venv\Scripts\python.exe docs/evidence/cd_pm5const_2026-11-25/build_favl_wide.py --L 200
"""
import argparse
from pathlib import Path

import yaml

SRC = Path('examples/typologies/cd_pm5const_2026-11-25/favl_pm5.yaml')
BOX = {'g_a_h_deg': (30.0, 46.0), 'g_a_v_deg': (18.0, 34.0), 'g_k': (0.6, 1.6), 'g_n': (1.8, 4.0),
       'g_s': (0.2, 0.7), 'g_L_mm': (150.0, 300.0), 'g_r_lip_mm': (8.0, 25.0), 'g_throat_hv_ratio': (0.85, 2.0),
       'g_wrap_deg': (60.0, 150.0), 'g_sf_ab': (0.80, 0.95), 'g_sf_amt': (0.10, 0.40)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--L', type=float, default=200.0)
    ap.add_argument('--out', default='favl_pm5_wide')
    a = ap.parse_args()
    cfg = yaml.safe_load(SRC.read_text(encoding='utf-8'))
    seed = dict(cfg['seed_params'])
    seed.update(g_a_h_deg=40.0, g_a_v_deg=25.0, g_L_mm=a.L)
    for k, (lo, hi) in BOX.items():
        cfg['bounds'][k] = {'lo': lo, 'hi': hi}
        assert lo <= seed[k] <= hi, (k, seed[k])
    cfg.update(name=a.out, seed_params=seed)
    cfg['search'] = {**cfg['search'], 'sigma0': 0.2, 'seed': 52611}
    cfg['description'] = ('favL on the +-5 deg constant-directivity compact500 brief with a box that can reach 80 x 50 '
                          '(a_h/a_v are the coverage half-angles; favl_pm5 capped a_h 34.5 / floored a_v 27.5). Seed '
                          f'a_h 40, a_v 25, L {a.L:g} (mouth inside the open cap), other knobs = the 150-valid best. '
                          '100 valid screen solves; NEW BO identity (box changed).')
    out = SRC.parent / f'{a.out}.yaml'
    out.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8', newline='\n')
    print('wrote', out)


if __name__ == '__main__':
    main()
