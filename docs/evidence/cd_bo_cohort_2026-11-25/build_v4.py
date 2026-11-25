"""v4: the 16-hour cohort (owner, 2026-11-25 13:40: "is this the best way? ... expand to a 16 hour queue").

Design rules, chosen so the night is not cut short by bound-pinning and every campaign feeds a usable metric-BO
identity:

* ONE frozen search space per family (brief + bounds = BO identity), shared by every seed of that family, so the
  seeds pool into one cohort (200-300 rows) instead of fragmenting.
* The box of every GRID knob is its LEGAL range at the primary seed, found by probing the real generator
  (``generated.materialize`` with the open v11 CD XO900 brief, so the 1.15 size cap is part of legality) across a
  wide candidate range: a pin can then only mean a family law, so the watchdog ignores all searched knobs and
  every campaign runs its full 100 valid. Joint-law refusals (e.g. axial relief <= 10 % of depth) are resampled.
* Locked knobs opened where they change the shape: rolled relief window + throat H/V ratio (20 dims, the encoder
  max), Le Cleac'h lip radius, Klangfilm aspect / fc / Lame p / end / morph / rim sweep. The superseded CD law
  (g_cd_*) stays off on rolled (the backbone replaces it); V backbone stays frozen at 0 (it narrows V).
* Families added because they lead J on this scorer: OSSE morph (screen J 2.899 on the same CD XO900 brief) and
  sculpted R-OSSE meridians (2.071, advisory-size variant). OSSE is formula-native: its box is widened by hand
  where the old run's best crowded it; the meshed preflight checks admission.

    .venv\\Scripts\\python.exe docs/evidence/cd_bo_cohort_2026-11-25/build_v4.py [--probe-only]
"""
import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.config import load_config  # noqa: E402
from hornlab_search.design.generated import materialize  # noqa: E402

OUT = Path('examples/typologies/cd_bo_cohort_2026-11-25')
HERE = Path('docs/evidence/cd_bo_cohort_2026-11-25')
NIGHT = Path('runs/nights/cd_bo_cohort_2026-11-25/summary.jsonl')
OPEN_BRIEF = load_config(OUT / 'rolled_v3_s1.yaml').brief
SEARCH = {'algorithm': 'cma', 'budget': 100, 'budget_counts': 'valid', 'error_policy': 'retry_same_then_stop',
          'infeasible_penalty': 'resample_strict', 'max_attempts': 600, 'popsize': None, 'sigma0': 0.10,
          'tolfun': 0.001}
# Per-seed CMA step (search settings are not part of the BO identity): s1 refines the best design, later seeds
# explore further (rolled_v3_s1 found nothing better than its seed in 30 evals at sigma 0.12).
SIGMA = {1: 0.10, 2: 0.18, 3: 0.25}

# Wide candidate ranges scanned by the probe (the legal sub-interval around the seed becomes the box).
ROLLED_SCAN = {
    'g_axial_h_mm': (-40, 40), 'g_axial_v_mm': (-40, 40), 'g_decay': (0.3, 1.0), 'g_depth_h_ratio': (0.5, 1.2),
    'g_depth_mm': (120, 420), 'g_height_mm': (220, 560), 'g_inward_h_mm': (0, 80), 'g_inward_v_mm': (0, 80),
    'g_rect_exponent': (2, 20), 'g_rect_turn_deg': (30, 89), 'g_terminal_deg': (181, 280),
    'g_throat_turn_deg': (4, 60), 'g_width_mm': (420, 700), 'g_bb_h': (0.3, 1.0), 'g_bb_throat_frac': (0.05, 0.30),
    'g_bb_rollin_frac': (0.15, 0.45), 'g_relief_start_s': (0.15, 0.80), 'g_relief_peak_s': (0.25, 0.92),
    'g_relief_end_s': (0.40, 0.96), 'g_throat_hv_ratio': (0.4, 2.5),
}
LCL_SCAN = {'g_T': (0.1, 1.5), 'g_fc_h_hz': (150, 1200), 'g_fc_v_hz': (200, 2000), 'g_stop_deg': (60, 240),
            'g_bb_throat_frac': (0.05, 0.30), 'g_bb_rollin_frac': (0.15, 0.45),   # r_lip legal only 0-2.1 mm here (probe)
            'g_rb_h_mm': (-60, 60), 'g_rb_v_mm': (-60, 60), 'g_rb_d_mm': (-30, 30), 'g_rb_start_frac': (0.30, 0.90)}
IWAR_SCAN = {'g_T': (0.1, 1.5), 'g_ar_m': (0.5, 4.0), 'g_ar_p': (0.2, 8.0), 'g_fc_hz': (150, 1200),
             'g_stop_deg': (60, 240), 'g_bb_throat_frac': (0.05, 0.30), 'g_bb_rollin_frac': (0.15, 0.45),
             'g_rb_h_mm': (-60, 60), 'g_rb_v_mm': (-60, 60), 'g_rb_d_mm': (-30, 30), 'g_rb_start_frac': (0.30, 0.90)}
# hv_core mode (cd_core_blend = 1): every Phase-A parent knob (aspect, fc, Lame p, end/morph frac, rim sweep, entry
# angle, source blend) is INERT (_INERT_AT_ONE) and must stay fixed; only the core knobs are live levers.
KLANG_SCAN = {'g_beak_h_setback_mm': (0, 60), 'g_beak_v_projection_mm': (0, 45), 'g_beak_diagonal_mm': (-20, 20),
              'g_beak_start_frac': (0.5, 0.99), 'g_core_length_mm': (150, 500), 'g_lame_end_frac': (0.4, 0.99),
              'g_lame_p_mouth': (2.0, 8.0), 'g_lame_start_frac': (0.05, 0.40), 'g_theta_h0_deg': (2, 15),
              'g_theta_h1_deg': (20, 60), 'g_theta_v0_deg': (2, 15), 'g_theta_v1_deg': (10, 50)}


def run_best(run, rank=0, exclude=()):
    rows = [json.loads(x) for x in (Path(run) / 'search.ndjson').read_text(encoding='utf-8').splitlines() if x.strip()]
    seen, out = set(exclude), []
    for r in sorted((r for r in rows if r.get('ok')), key=lambda r: r['objective']):
        if r['design_hash'] in seen:
            continue
        seen.add(r['design_hash'])
        out.append(r)
    r = out[rank]
    return r['params'], r['objective'], r['design_hash']


def night_run(job_id):
    for line in NIGHT.read_text(encoding='utf-8').splitlines():
        j = json.loads(line)
        if j['id'] == job_id:
            return j['run_dir']
    raise SystemExit(f'{job_id} not finished')


def legal_interval(gen, knobs, key, scan, n=29):
    """Contiguous legal sub-interval of ``scan`` containing the seed value (others held at the seed)."""
    lo, hi = scan
    seed = float(knobs[key])
    grid = sorted(set(np.linspace(lo, hi, n).round(6).tolist()) | {seed})
    ok = {}
    for v in grid:
        try:
            materialize(gen, {**knobs, key: float(v)}, OPEN_BRIEF)
            ok[v] = True
        except Exception:  # noqa: BLE001 - any refusal = not legal here
            ok[v] = False
    if not ok[seed]:
        raise SystemExit(f'{key}: seed {seed} itself is refused')
    i = grid.index(seed)
    a = i
    while a > 0 and ok[grid[a - 1]]:
        a -= 1
    b = i
    while b < len(grid) - 1 and ok[grid[b + 1]]:
        b += 1
    return grid[a], grid[b], sum(ok.values()), len(grid)


def probe(gen, knobs, scan):
    box, report = {}, {}
    for key, rng in scan.items():
        if key not in knobs:
            raise SystemExit(f'scan key {key} not in seed knobs')
        lo, hi, n_ok, n = legal_interval(gen, knobs, key, rng)
        if hi - lo <= 1e-9:
            raise SystemExit(f'{key}: legal interval collapsed at the seed ({lo})')
        box[key] = (lo, hi)
        report[key] = {'scan': list(rng), 'legal_at_seed': [lo, hi], 'legal_points': f'{n_ok}/{n}',
                       'seed': float(knobs[key])}
        print(f'   {key:24s} scan {rng}  legal [{lo:.4g}, {hi:.4g}]  ({n_ok}/{n})  seed {float(knobs[key]):.4g}')
    return box, report


def write(name, cfg, gen, seed_knobs, box, cma_seed, label, extra_fixed=None):
    cfg = copy.deepcopy(cfg)
    bounds = {}
    for k, v in seed_knobs.items():
        if k in box:
            lo, hi = box[k]
            if not lo <= float(v) <= hi:
                raise SystemExit(f'{name}: seed {k}={v} outside its box [{lo}, {hi}]')
            bounds[k] = {'lo': float(lo), 'hi': float(hi), 'search': True}
        elif isinstance(v, (list, tuple)):
            bounds[k] = {'lo': v, 'hi': v, 'search': False}
        else:
            bounds[k] = {'lo': float(v), 'hi': float(v), 'search': False}
    cfg.update(name=name, generator=gen, seed_params=dict(seed_knobs), bounds=bounds, brief=copy.deepcopy(OPEN_BRIEF),
               brief_file=None, search={**SEARCH, 'seed': cma_seed, 'sigma0': SIGMA[int(name[-1])]},
               description=f'{label} v4 cohort (16-h queue): box = legal range at the primary seed (probe_v4.json); '
                           f'{len(box)} active dims; frozen identity shared by every seed of this family.')
    cfg['mesh'] = {**cfg['mesh'], 'dof_cap_screen': 24000}
    path = OUT / f'{name}.yaml'
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8', newline='\n')
    print('wrote', path.as_posix(), 'active', len(box))
    return path


# The rolled law needs DISJOINT relief-window boxes (start < peak < end everywhere in the box); the one-knob probe
# cannot see that, so the probed legal ranges are split at fixed cut points that keep every seed inside.
ROLLED_BOX_OVERRIDE = {'g_relief_start_s': (0.2196, 0.55), 'g_relief_peak_s': (0.56, 0.81),
                       'g_relief_end_s': (0.82, 0.96),
                       # relief position is dormant (law) if every strength can be zero: every rolled seed has
                       # axial_v 5.9-13.9 mm, so a 2 mm floor keeps the position knobs live.
                       'g_axial_v_mm': (2.0, 20.0)}


def grid_family(prefix, template, scan, seeds, label, report, fixed_updates=None, box_override=None):
    cfg = yaml.safe_load((OUT / f'{template}.yaml').read_text(encoding='utf-8'))
    gen = load_config(OUT / f'{template}.yaml').generator      # loader-normalised block (what the search uses)
    primary = {**cfg['seed_params'], **seeds[0][0]}
    primary.update(fixed_updates or {})
    print(f'{prefix}: probing {len(scan)} knobs at the primary seed')
    box, rep = probe(gen, primary, scan)
    for k, (lo, hi) in (box_override or {}).items():
        plo, phi = box[k]
        box[k] = (max(lo, plo), min(hi, phi))
        rep[k]['box_after_joint_law_split'] = list(box[k])
    report[prefix] = rep
    out = []
    for i, (knobs, cma_seed) in enumerate(seeds, start=1):
        sk = {**cfg['seed_params'], **knobs, **(fixed_updates or {})}
        materialize(gen, sk, OPEN_BRIEF)
        out.append(write(f'{prefix}_s{i}', cfg, cfg['generator'], sk, box, cma_seed, label))
    return out


def formula_family(prefix, run, widen, seeds, label):
    rj = json.loads((Path(run) / 'run.json').read_text(encoding='utf-8'))['config']
    cfg = copy.deepcopy(rj)
    out = []
    for i, (params, cma_seed) in enumerate(seeds, start=1):
        c = copy.deepcopy(cfg)
        bounds = copy.deepcopy(c['bounds'])
        for k, (lo, hi) in widen.items():
            bounds[k] = {'lo': lo, 'hi': hi, 'search': True}
        for k, b in bounds.items():
            v = params[k]
            if b.get('search', True) and b['lo'] != b['hi'] and not b['lo'] <= float(v) <= b['hi']:
                raise SystemExit(f'{prefix}_s{i}: seed {k}={v} outside [{b["lo"]}, {b["hi"]}]')
        active = sum(1 for b in bounds.values() if b.get('search', True) and b['lo'] != b['hi'])
        c.update(name=f'{prefix}_s{i}', seed_params={k: params[k] for k in c['seed_params']}, bounds=bounds,
                 brief=copy.deepcopy(OPEN_BRIEF), brief_file=None,
                 search={**SEARCH, 'seed': cma_seed, 'sigma0': SIGMA[i]},
                 description=f'{label} v4 cohort (16-h queue), {active} active dims; widened {sorted(widen)}; '
                             f'frozen identity shared by every seed of this family.')
        c['mesh'] = {**c['mesh'], 'dof_cap_screen': 24000}
        path = OUT / f'{prefix}_s{i}.yaml'
        path.write_text(yaml.safe_dump(c, sort_keys=False), encoding='utf-8', newline='\n')
        print('wrote', path.as_posix(), 'active', active)
        out.append(path)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', nargs='*')
    args = ap.parse_args()
    report = {}
    want = lambda f: not args.only or f in args.only  # noqa: E731

    if want('rolled'):
        live = Path(sorted(Path('runs').glob('*-screen-*'), key=lambda p: p.stat().st_mtime)[-1])
        cfgname = json.loads((live / 'run.json').read_text(encoding='utf-8'))['config']['name']
        src = live if cfgname == 'rolled_v3_s1' else night_run('rolled_v3_s1')
        p1, j1, h1 = run_best(src)
        p2, j2, h2 = run_best(night_run('rolled_beak_cohort_s1'))
        p3, j3, h3 = run_best(night_run('rolled_bb_cohort_s1'))
        print(f'rolled seeds: {h1} J {j1:.3f} | {h2} J {j2:.3f} | {h3} J {j3:.3f}')
        rolled = lambda p: {**p['grid']['knobs'], 'g_bb_v': 0.0, 'g_throat_hv_ratio': 1.0}  # noqa: E731
        grid_family('rolled_v4', 'rolled_v3_s1', ROLLED_SCAN,
                    [(rolled(p1), 81531), (rolled(p2), 81532), (rolled(p3), 81533)],
                    'Rolled hybrid + CD backbone (H/V depth split both ways, relief window and throat H/V ratio '
                    'opened)', report, box_override=ROLLED_BOX_OVERRIDE)
    if want('lcl'):
        p1, j1, h1 = run_best(night_run('lcl_bb_cohort'))
        print(f'lcl seed {h1} J {j1:.3f}')
        base = yaml.safe_load((OUT / 'lcl_beak_v3.yaml').read_text(encoding='utf-8'))['seed_params']
        k1 = {**base, **p1['grid']['knobs'], 'g_bb_h': 1.0, 'g_bb_v': 0.0}
        grid_family('lcl_beak_v4', 'lcl_beak_v3', LCL_SCAN, [(k1, 81541), (k1, 81542)],
                    "LABELED HYPOTHESIS: Le Cleac'h H/V + CD backbone + rim beak (lip radius opened)", report)
    if want('iwar'):
        p1, j1, h1 = run_best(night_run('iwar_bb_cohort'))
        print(f'iwar seed {h1} J {j1:.3f}')
        base = yaml.safe_load((OUT / 'iwar_beak_v3.yaml').read_text(encoding='utf-8'))['seed_params']
        k1 = {**base, **p1['grid']['knobs'], 'g_bb_h': 1.0, 'g_bb_v': 0.0}
        grid_family('iwar_beak_v4', 'iwar_beak_v3', IWAR_SCAN, [(k1, 81551), (k1, 81552)],
                    'LABELED HYPOTHESIS: Iwata AR + CD backbone + rim beak', report)
    if want('klang'):
        run = 'runs/20261120T085629Z-screen-90752f'
        p1, j1, h1 = run_best(run)
        p2, j2, h2 = run_best(run, rank=1)
        print(f'klangfilm seeds {h1} J {j1:.3f} | {h2} J {j2:.3f}')
        grid_family('klangfilm_v4', 'klangfilm_core_beak_cohort', KLANG_SCAN,
                    [(p1['grid']['knobs'], 81561), (p2['grid']['knobs'], 81562)],
                    'LABELED HYPOTHESIS: Klangfilm-Lame H/V core, own beak + aspect/fc/Lame p/end/morph/rim sweep '
                    'opened', report)
    if want('osse'):
        run = 'runs/20261124T001003Z-screen-ec87fc'
        picks = [run_best(run, rank=r) for r in (0, 2, 4)]
        print('osse seeds', [(h, round(j, 3)) for _p, j, h in picks])
        widen = {'L_mm': (160.0, 420.0), 'n': (2.0, 14.0), 'a_deg': (18.0, 45.0), 'k': (0.3, 4.0),
                 'morph_width_mm': (460.0, 660.0), 'morph_height_mm': (300.0, 520.0),
                 'morph_corner_mm': (20.0, 130.0), 'morph_rate': (1.0, 8.0), 'az_a_cos_amp': (0.0, 20.0)}
        formula_family('osse_morph_v4', run, widen, [(p, 81570 + i) for i, (p, _j, _h) in enumerate(picks, 1)],
                       'OSSE morph (CD-native waveguide; leads J on this scorer)')
    if want('sculpted'):
        run = 'runs/20261121T135752Z-screen-8c15a8'
        p1, j1, h1 = run_best(run)
        print(f'sculpted seed {h1} J {j1:.3f}')
        formula_family('sculpted_v4', run, {}, [(p1['grid']['knobs'], 81581)],
                       'Sculpted R-OSSE meridians (leads J on the advisory-size variant)')
    if report:
        prev = json.loads((HERE / 'probe_v4.json').read_text(encoding='utf-8')) if (HERE / 'probe_v4.json').exists() else {}
        prev.update(report)
        (HERE / 'probe_v4.json').write_text(json.dumps(prev, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
