r"""+-5 deg constant-directivity briefs and queue jobs (owner, 2026-11-25 17:43).

Owner intent for corridor mode: a horn may hold ANY constant beamwidth inside a +-5 deg window around 80 H x 50 V
(e.g. a flat 78 x 48 is a perfect coverage score), but it must be flat across frequency at that angle. Encoded with
existing v11 machinery only (no scorer code change):
  * corridor H 75-85, V 45-55 (both anchors);
  * the opt-in v9 `constancy` term (scalar_v9._plane_constancy_cost): per plane, fit a constant level, clamp it into
    [min, max], charge mean squared deviation (deg^2/100) / tolerance. strict, weight 1.0, tolerance 0.25
    (5 deg rms off a flat in-corridor line = 1.0; same scale as S1's strict mean(d^2)/25).
Two briefs (each a NEW J/BO identity): the room_landscape open115 brief (exploration families) and the compact500
2-inch open115 brief (favL). Configs: each family's exploration run-1 config (best known start), brief swapped to
brief_file, 100 valid screen solves, sigma0 0.15; favL from its continuation config, seeded at the 150-valid run's
best (6552f5c8c536), sigma0 0.2, no warm start (the warm start's top-10 all sit at the old ~66 x 62 optimum).

    .venv\Scripts\python.exe docs/evidence/cd_pm5const_2026-11-25/build_pm5.py
"""
import copy
import json
from pathlib import Path

import yaml

CFG_OUT = Path('examples/typologies/cd_pm5const_2026-11-25')
EXPLORE = Path('examples/typologies/cd_explore_2026-11-25')
FAVL_CFG = Path('examples/typologies/favL_2026-11-20/favL__2in_c500_open115.yaml')
FAVL_RUN = Path('runs/20261125T204727Z-screen-02b4bf')
BRIEFS = {
    'room': (Path('examples/briefs/home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd_open115_2026-11-25.yaml'),
             Path('examples/briefs/home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd_open115_pm5const_2026-11-25.yaml')),
    'c500': (Path('examples/briefs/hf2in_2026-11-20/compact500_xo900_80x50_hf2in_v11cd_open115.yaml'),
             Path('examples/briefs/hf2in_2026-11-20/compact500_xo900_80x50_hf2in_v11cd_open115_pm5const_2026-11-25.yaml')),
}
FAMILIES = ['rolled', 'lcl_beak', 'iwar_beak', 'sculpted_beak', 'sculpted_sweep', 'klangfilm']
CMA_SEED0 = 52500


def make_brief(src, dst):
    b = yaml.safe_load(src.read_text(encoding='utf-8'))
    b['name'] += '_pm5const'
    b['description'] = (f'(objective v11) {src.name} with the owner\'s +-5 deg constant-directivity corridor '
                        '(2026-11-25 17:43): H 75-85, V 45-55, and the opt-in v9 constancy term (strict, weight 1.0, '
                        'tolerance 0.25: 5 deg rms off a flat in-corridor line = 1.0). Any constant angle inside the '
                        'window scores as well as 80 x 50; wobble across frequency and leaving the window cost. '
                        'Builder: docs/evidence/cd_pm5const_2026-11-25/build_pm5.py. NEW J/BO IDENTITY.')
    prof = b['target']['coverage_profile']
    for a in prof['h']:
        a.update(min_deg=75, max_deg=85, preferred_deg=80)
    for a in prof['v']:
        a.update(min_deg=45, max_deg=55, preferred_deg=50)
    b['objective']['constancy'] = {'mode': 'strict', 'weight': 1.0, 'tolerance': 0.25}
    dst.write_text(f'# 2026-11-25: +-5 deg constant-directivity copy of {src.name}; see description.\n'
                   + yaml.safe_dump(b, sort_keys=False), encoding='utf-8', newline='\n')
    return dst


def rel(target, cfg_dir):
    return Path('../../briefs') / target.parent.name / target.name


def family_config(fam, i):
    cfg = yaml.safe_load((EXPLORE / f'{fam}_r1.yaml').read_text(encoding='utf-8'))
    for k in ('brief', 'target', 'weights', 'objective', 'grid'):
        cfg.pop(k, None)
    cfg['brief_file'] = rel(BRIEFS['room'][1], CFG_OUT).as_posix()
    cfg['name'] = f'{fam}_pm5'
    cfg['search'] = {**cfg['search'], 'budget': 100, 'sigma0': 0.15, 'seed': CMA_SEED0 + i}
    cfg['description'] = (f'{fam} on the +-5 deg constant-directivity brief (owner 2026-11-25 17:43). Box, seed and '
                          f'knobs = {fam}_r1 (best known design of the family, exploration box); only the brief '
                          f'changed. 100 valid screen solves. Judged on verify by the six CD rules, not J alone.')
    return cfg


def favl_config():
    cfg = yaml.safe_load(FAVL_CFG.read_text(encoding='utf-8'))
    rows = [json.loads(x) for x in (FAVL_RUN / 'search.ndjson').read_text(encoding='utf-8').splitlines() if x.strip()]
    best = min((r for r in rows if r.get('ok') and r.get('objective') is not None), key=lambda r: r['objective'])
    knobs = best['params']['grid']['knobs'] if isinstance(best['params'].get('grid'), dict) else best['params']
    seed = dict(cfg['seed_params'])
    seed.update({k: v for k, v in knobs.items() if k in seed})
    cfg['seed_params'] = seed
    cfg['brief_file'] = rel(BRIEFS['c500'][1], CFG_OUT).as_posix()
    cfg['name'] = 'favL__2in_c500_pm5'
    s = dict(cfg['search'])
    s.pop('warm_start', None)
    s.update(budget=100, sigma0=0.2, seed=CMA_SEED0 + 99)
    cfg['search'] = s
    cfg['description'] = (f'favL__2in_c500 on the +-5 deg constant-directivity compact500 brief (owner 2026-11-25 '
                          f'17:43). Seed = best of {FAVL_RUN.name} ({best["design_hash"]}, screen J '
                          f'{best["objective"]:.4f} on the open115 brief, ~66 H x 62 V); box unchanged; no warm '
                          f'start; sigma0 0.2. 100 valid screen solves.')
    return cfg


def main():
    for src, dst in BRIEFS.values():
        print('brief', make_brief(src, dst))
    CFG_OUT.mkdir(parents=True, exist_ok=True)
    out = {f'{f}_pm5': family_config(f, i) for i, f in enumerate(FAMILIES)}
    out['favl_pm5'] = favl_config()
    for name, cfg in out.items():
        p = CFG_OUT / f'{name}.yaml'
        p.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8', newline='\n')
        print('config', p.as_posix())


if __name__ == '__main__':
    main()
