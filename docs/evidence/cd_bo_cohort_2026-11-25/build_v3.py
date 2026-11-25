"""v3 cohort configs after the bound-pinned watchdog stops (owner, 2026-11-25 13:30: "over-constrained").

Every batch-1/2 campaign stopped at 30-35 valid rows on a pinned knob (pin_map.json). Three remedies, nothing else
changed (same open v11 CD XO900 brief, CMA, 100 valid, resample_strict):

1. WIDEN a search-box pin: rolled g_depth_mm floor 200 -> 165 (the floor existed only because of the 10 %-of-depth
   axial-relief law at the old seed; the new seeds allow 165).
2. FREEZE a knob whose top designs sit on a hard kernel floor/ceiling that cannot be widened: rolled g_bb_v = 0 (floor;
   matches the earlier finding that a V blend narrows V), rows g_bb_h = 1.0 (kernel max) and g_bb_v = 0.
3. Let the watchdog IGNORE knobs pinned on a family law that couples to other knobs (axial relief <= 10 % depth,
   inward relief >= 0, terminal <= 280 deg, depth_h_ratio <= 1.2): their rows are reported, not stopped on.
   (pin_ignore lists live in the queue file; see PIN_IGNORE below.)

Each campaign is seeded from the best design found so far in its family (continuation), not from the old seed.

    .venv\\Scripts\\python.exe docs/evidence/cd_bo_cohort_2026-11-25/build_v3.py [--only name ...]
"""
import argparse
import copy
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path.cwd()))
OUT = Path('examples/typologies/cd_bo_cohort_2026-11-25')
NIGHT = Path('runs/nights/cd_bo_cohort_2026-11-25/summary.jsonl')

PIN_IGNORE = {
    'rolled': ['g_depth_mm', 'g_axial_h_mm', 'g_axial_v_mm', 'g_inward_h_mm', 'g_inward_v_mm', 'g_terminal_deg',
               'g_depth_h_ratio'],
    'rows': ['g_bb_throat_frac', 'g_bb_rollin_frac'],
    'rows_beak': ['g_bb_throat_frac', 'g_bb_rollin_frac', 'g_rb_h_mm', 'g_rb_v_mm', 'g_rb_d_mm'],
}

# name: (template config, seed job id in the night summary, widen {knob: (lo, hi)}, freeze {knob: value}, group, CMA seed)
V3 = {
    'rolled_v3_s1': ('rolled_beak_cohort_s1', 'rolled_beak_cohort_s2', {'g_depth_mm': (165.0, 340.0)},
                     {'g_bb_v': 0.0}, 'rolled', 81521),
    'rolled_v3_s2': ('rolled_beak_cohort_s2', 'rolled_beak_cohort_s1', {'g_depth_mm': (165.0, 340.0)},
                     {'g_bb_v': 0.0}, 'rolled', 81522),
    'lcl_v3': ('lcl_bb_cohort', 'lcl_bb_cohort', {}, {'g_bb_h': 1.0, 'g_bb_v': 0.0}, 'rows', 81523),
    'lcl_beak_v3': ('lcl_beak_cohort', 'lcl_bb_cohort', {}, {'g_bb_h': 1.0, 'g_bb_v': 0.0}, 'rows_beak', 81524),
    'iwar_v3': ('iwar_bb_cohort', 'iwar_bb_cohort', {}, {'g_bb_h': 1.0, 'g_bb_v': 0.0}, 'rows', 81525),
    'iwar_beak_v3': ('iwar_beak_cohort', 'iwar_bb_cohort', {}, {'g_bb_h': 1.0, 'g_bb_v': 0.0}, 'rows_beak', 81526),
}


def best_knobs(job_id):
    for line in NIGHT.read_text(encoding='utf-8').splitlines():
        job = json.loads(line)
        if job['id'] != job_id:
            continue
        run = Path(job['run_dir'])
        rows = [json.loads(x) for x in (run / 'search.ndjson').read_text(encoding='utf-8').splitlines() if x.strip()]
        best = min((r for r in rows if r.get('ok')), key=lambda r: r['objective'])
        return best['params']['grid']['knobs'], best['objective'], best['design_hash'], run.as_posix()
    raise SystemExit(f'no finished job {job_id!r} in {NIGHT}')


def build(name):
    template, seed_job, widen, freeze, group, cma_seed = V3[name]
    cfg = yaml.safe_load((OUT / f'{template}.yaml').read_text(encoding='utf-8'))
    knobs, J, design, run = best_knobs(seed_job)
    seed = dict(cfg['seed_params'])
    seed.update({k: v for k, v in knobs.items() if k in seed})          # beak templates keep their rb_* seed
    seed.update(freeze)
    bounds = copy.deepcopy(cfg['bounds'])
    for k, (lo, hi) in widen.items():
        bounds[k] = {'lo': lo, 'hi': hi, 'search': True}
    for k, v in freeze.items():
        bounds[k] = {'lo': float(v), 'hi': float(v), 'search': False}
    for k, b in bounds.items():
        if b.get('search', True) and b['lo'] != b['hi'] and not b['lo'] <= float(seed[k]) <= b['hi']:
            raise SystemExit(f'{name}: seed {k}={seed[k]} outside [{b["lo"]}, {b["hi"]}]')
    active = sum(1 for b in bounds.values() if b.get('search', True) and b['lo'] != b['hi'])
    cfg.update(name=name, seed_params=seed, bounds=bounds, search={**cfg['search'], 'seed': cma_seed},
               description=(f"v3 of {template} (owner 13:30: over-constrained). Seed = best of {seed_job} "
                            f"({design}, screen J {J:.4f}, {run}). Widened {sorted(widen) or 'none'}; frozen at a "
                            f"kernel floor/ceiling {freeze}; watchdog ignores law-coupled pins {PIN_IGNORE[group]}. "
                            f"{active} active continuous dims (metric-BO identity). Judged by the six CD rules on "
                            f"verify, not J alone."))
    path = OUT / f'{name}.yaml'
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8', newline='\n')
    print('wrote', path.as_posix(), 'active', active, 'seed J', round(J, 4), design)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', nargs='*')
    args = ap.parse_args()
    for name in (args.only or V3):
        build(name)


if __name__ == '__main__':
    main()
