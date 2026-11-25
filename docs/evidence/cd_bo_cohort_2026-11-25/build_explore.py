"""Exploration cohorts (owner, 2026-11-25 14:20: explore first, all families, may run 24+ h).

Purpose: train the metric-aware BO model and learn which knobs control which acoustic result. That needs coverage
and independent groups, not polish (bo-study-v1.1 screening policy: >= 100 unique observations from >= 5
independent groups per identity). So, per family:

* ONE search box (= one BO identity) = every live knob opened to its legal range (GRID: probed through the real
  generator with the open v11 CD XO900 brief, so the 1.15 size cap is part of legality; formula OSSE: family
  documented ranges), max 20 dims (encoder limit). Locks are only for inert / mode-switch / driver-fixed /
  duplicate-lever knobs, each listed with its reason in EXPLORE_PROTOCOL.md.
* K independent CMA runs (= K groups): run 1 starts at the best known design (sigma 0.15), runs 2..K start at
  scrambled-Sobol points of the box (sigma 0.25), each 'budget' valid. Watchdog stops disabled except failures.

    .venv\\Scripts\\python.exe docs/evidence/cd_bo_cohort_2026-11-25/build_explore.py [--only fam ...]
"""
import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import qmc

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_v4 as V4  # noqa: E402
from hornlab_search.config import load_config  # noqa: E402
from hornlab_search.design.generated import materialize  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402

SRC = Path('examples/typologies/cd_bo_cohort_2026-11-25')
OUT = Path('examples/typologies/cd_explore_2026-11-25')
HERE = Path(__file__).resolve().parent
SEARCH = {'algorithm': 'cma', 'budget_counts': 'valid', 'error_policy': 'retry_same_then_stop',
          'infeasible_penalty': 'resample_strict', 'popsize': None, 'tolfun': 0.001}

ROLLED_OVERRIDE = {**V4.ROLLED_BOX_OVERRIDE,
                   # landscape law: the height box must stay below the width box (height_hi < width_lo)
                   'g_width_mm': (500.0, 690.0), 'g_height_mm': (220.0, 495.0)}
ROWS_BB = {'g_bb_h': (0.3, 1.0), 'g_bb_v': (0.0, 0.5)}       # reopened for attribution (were frozen at limits)
SCULPT_SWEEP_SCAN = {'g_sweep': (-1.0, 1.5), 'g_diagonal_delta_deg': (-6.0, 6.0), 'g_aperture_scale': (0.75, 1.25)}
SCULPT_BEAK_SCAN = {'g_h_setback_mm': (-40.0, 80.0), 'g_v_projection_mm': (-40.0, 80.0)}
OSSE_BOX = {'L_mm': (160.0, 420.0), 'a0_deg': (1.0, 3.0), 'a_deg': (18.0, 45.0), 'az_a_cos_amp': (0.0, 20.0),
            'az_a_cos_pow': (1.0, 6.0), 'az_s_cos2_amp': (-0.25, 0.5), 'k': (0.3, 4.0), 'morph_corner_mm': (20.0, 130.0),
            'morph_height_mm': (300.0, 520.0), 'morph_rate': (1.0, 8.0), 'morph_width_mm': (460.0, 660.0),
            'n': (2.0, 14.0), 'q': (0.9, 1.0), 's': (0.2, 1.2),
            # opened (were inherited locks; ranges inside the family table, families.py:58-119)
            'aspect_ratio': (0.8, 1.6), 'exponent': (2.0, 6.0), 'az_a_sf_amp': (-15.0, 15.0),
            'az_n_cos2_amp': (-4.0, 4.0), 'morph_fixed': (0.0, 0.5)}


def best_over(runs):
    best = None
    for run in runs:
        p, j, h = V4.run_best(run)
        if best is None or j < best[1]:
            best = (p, j, h, run)
    return best


def sobol_points(box, n, seed):
    keys = sorted(box)
    pts = qmc.Sobol(len(keys), scramble=True, seed=seed).random(n)
    return [{k: float(box[k][0] + u * (box[k][1] - box[k][0])) for k, u in zip(keys, row)} for row in pts]


def write(path, cfg, seed_knobs, box, name, sigma, budget, label):
    cfg = copy.deepcopy(cfg)
    bounds = {}
    for k, v in seed_knobs.items():
        if k in box:
            bounds[k] = {'lo': float(box[k][0]), 'hi': float(box[k][1]), 'search': True}
        elif isinstance(v, (list, tuple)):
            bounds[k] = {'lo': v, 'hi': v, 'search': False}
        else:
            bounds[k] = {'lo': float(v), 'hi': float(v), 'search': False}
    cfg.update(name=name, seed_params=dict(seed_knobs), bounds=bounds, brief=copy.deepcopy(V4.OPEN_BRIEF),
               brief_file=None,
               search={**SEARCH, 'budget': budget, 'max_attempts': 8 * budget, 'sigma0': sigma,
                       'seed': 90000 + (abs(hash(name)) % 9000)},
               description=f'{label}. EXPLORATION cohort member {name} (2026-11-25): box = legal range, '
                           f'{len(box)} active dims, shared by every run of this family (one BO identity).')
    cfg['mesh'] = {**cfg['mesh'], 'dof_cap_screen': 24000}
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8', newline='\n')


def grid_cohort(fam, template_cfg, seed_knobs, scan, override, k, budget, label, report, fixed=None):
    gen = template_cfg['_loaded_generator']
    cfg = {key: v for key, v in template_cfg.items() if key != '_loaded_generator'}
    seed = {**cfg['seed_params'], **seed_knobs, **(fixed or {})}
    print(f'{fam}: probing {len(scan)} knobs')
    box, rep = V4.probe(gen, seed, scan)
    for key, (lo, hi) in (override or {}).items():
        plo, phi = box[key]
        box[key] = (max(lo, plo), min(hi, phi))
        rep[key]['box_after_joint_law'] = list(box[key])
    report[fam] = {'box': {key: list(v) for key, v in box.items()}, 'probe': rep}
    starts, tried = [seed], 0
    for pt in sobol_points(box, 64, seed=len(fam) * 7919):
        if len(starts) >= k:
            break
        cand = {**seed, **pt}
        tried += 1
        try:
            materialize(gen, cand, V4.OPEN_BRIEF)
            starts.append(cand)
        except Exception:  # noqa: BLE001 - joint-law refusal: skip this Sobol point
            continue
    report[fam]['sobol_starts'] = f'{len(starts) - 1} accepted of {tried} tried'
    paths = []
    for i, s in enumerate(starts, start=1):
        name = f'{fam}_r{i}'
        p = OUT / f'{name}.yaml'
        write(p, cfg, s, box, name, 0.15 if i == 1 else 0.25, budget, label)
        paths.append(p)
    print(f'   {len(paths)} runs, {len(box)} dims, Sobol starts accepted {len(starts) - 1}/{tried}')
    return paths


def load_template(path_or_cfg):
    if isinstance(path_or_cfg, Path):
        raw = yaml.safe_load(path_or_cfg.read_text(encoding='utf-8'))
        raw['_loaded_generator'] = load_config(path_or_cfg).generator
        return raw
    return path_or_cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', nargs='*')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    want = lambda f: not args.only or f in args.only  # noqa: E731
    rep_path = HERE / 'explore_boxes.json'
    report = json.loads(rep_path.read_text(encoding='utf-8')) if rep_path.exists() else {}

    if want('rolled'):
        runs = [V4.night_run(j) for j in ('rolled_v3_s1', 'rolled_beak_cohort_s1', 'rolled_beak_cohort_s2')]
        try:
            runs.append(V4.night_run('rolled_v3_s2'))
        except SystemExit:
            pass
        p, j, h, run = best_over(runs)
        print(f'rolled seed {h} J {j:.4f} ({run})')
        grid_cohort('rolled', load_template(SRC / 'rolled_v4_s1.yaml'),
                    {**p['grid']['knobs'], 'g_bb_v': 0.0, 'g_throat_hv_ratio': 1.0}, V4.ROLLED_SCAN, ROLLED_OVERRIDE,
                    8, 50, 'Rolled hybrid + CD backbone (20 live knobs; g_cd_* duplicate law and bb_v off)', report)
    if want('lcl'):
        p, j, h = V4.run_best(V4.night_run('lcl_bb_cohort'))
        print(f'lcl seed {h} J {j:.4f}')
        base = yaml.safe_load((SRC / 'lcl_beak_v4_s1.yaml').read_text(encoding='utf-8'))['seed_params']
        grid_cohort('lcl_beak', load_template(SRC / 'lcl_beak_v4_s1.yaml'), {**base, **p['grid']['knobs']},
                    {**V4.LCL_SCAN, **ROWS_BB}, {}, 6, 50,
                    "LABELED HYPOTHESIS: Le Cleac'h H/V + CD backbone + rim beak", report)
    if want('iwar'):
        p, j, h = V4.run_best(V4.night_run('iwar_bb_cohort'))
        print(f'iwar seed {h} J {j:.4f}')
        base = yaml.safe_load((SRC / 'iwar_beak_v4_s1.yaml').read_text(encoding='utf-8'))['seed_params']
        grid_cohort('iwar_beak', load_template(SRC / 'iwar_beak_v4_s1.yaml'), {**base, **p['grid']['knobs']},
                    {**V4.IWAR_SCAN, **ROWS_BB}, {}, 6, 50, 'LABELED HYPOTHESIS: Iwata AR + CD backbone + rim beak',
                    report)
    if want('klang'):
        p, j, h = V4.run_best('runs/20261120T085629Z-screen-90752f')
        print(f'klangfilm seed {h} J {j:.4f}')
        grid_cohort('klangfilm', load_template(SRC / 'klangfilm_v4_s1.yaml'), p['grid']['knobs'], V4.KLANG_SCAN, {},
                    6, 50, 'LABELED HYPOTHESIS: Klangfilm-Lame H/V core (all live core knobs incl. V beak)', report)
    if want('sculpted'):
        p, j, h = V4.run_best('runs/20261121T135752Z-screen-8c15a8')
        print(f'sculpted sweep seed {h} J {j:.4f}')
        grid_cohort('sculpted_sweep', load_template(SRC / 'sculpted_v4_s1.yaml'), p['grid']['knobs'],
                    SCULPT_SWEEP_SCAN, {}, 4, 30, 'Sculpted R-OSSE meridians, sweep mode', report)
        p, j, h = V4.run_best('runs/20261121T142221Z-screen-54497b')
        print(f'sculpted beak seed {h} J {j:.4f}')
        tmpl = load_template(SRC / 'sculpted_v4_s1.yaml')
        tmpl = {**tmpl, 'seed_params': dict(p['grid']['knobs'])}
        grid_cohort('sculpted_beak', tmpl, p['grid']['knobs'], SCULPT_BEAK_SCAN, {}, 4, 30,
                    'Sculpted R-OSSE meridians, beak mode (H setback / V projection)', report)
    if want('osse'):
        run = 'runs/20261124T001003Z-screen-ec87fc'
        cfg = json.loads((Path(run) / 'run.json').read_text(encoding='utf-8'))['config']
        p, j, h = V4.run_best(run)
        print(f'osse seed {h} J {j:.4f}')
        seed = {k: p[k] for k in cfg['seed_params']}
        starts = [seed]
        for pt in sobol_points(OSSE_BOX, 16, seed=4242):
            if len(starts) >= 8:
                break
            starts.append({**seed, **pt})
        for i, s in enumerate(starts, start=1):
            name = f'osse_morph_r{i}'
            write(OUT / f'{name}.yaml', cfg, s, OSSE_BOX, name, 0.15 if i == 1 else 0.25, 50,
                  'OSSE morph (CD-native waveguide; leads J on this scorer; 5 inherited locks opened)')
        report['osse_morph'] = {'box': {k: list(v) for k, v in OSSE_BOX.items()},
                                'note': 'formula family: documented ranges; mesh admission checked by shape_check'}
        print(f'osse_morph: {len(starts)} runs, {len(OSSE_BOX)} dims')
    rep_path.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
