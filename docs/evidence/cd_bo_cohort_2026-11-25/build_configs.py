"""Build the 2026-11-25 CD-backbone CMA cohort configs (CPU only, no solver).

Four CMA screen campaigns, 100 VALID solves each, on the v11 CD XO900 brief with an OPEN envelope
(enforce false, max_utilization 1.15 -> candidate box 690 x 552 x 552 mm; oversize candidates are refused
before meshing and redrawn by resample_strict; every row records size_feasibility). Each campaign's bounds are a
frozen metric-BO identity (continuous knobs only, <= 20 active dims); the two rolled campaigns share one identity
so their rows pool.

    .venv\\Scripts\\python.exe docs/evidence/cd_bo_cohort_2026-11-25/build_configs.py
"""
import copy
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path.cwd()))
BRIEF_SRC = Path('examples/briefs/home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd.yaml')
BRIEF_OUT = Path('examples/briefs/home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd_open115_2026-11-25.yaml')
OUT = Path('examples/typologies/cd_bo_cohort_2026-11-25')
BB = Path('examples/typologies/cd_backbone_2026-11-25')
VAR = Path('examples/typologies/cd_variants_2026-11-25')

SEARCH = {'algorithm': 'cma', 'budget': 100, 'budget_counts': 'valid', 'error_policy': 'retry_same_then_stop',
          'infeasible_penalty': 'resample_strict', 'max_attempts': 500, 'popsize': None, 'sigma0': 0.12,
          'tolfun': 0.001}

ROLLED_BOUNDS = {  # parent: the source campaign's searched ranges (a07561), widened where a keeper sat at an edge
    'g_axial_h_mm': (-20.0, 20.0), 'g_axial_v_mm': (-20.0, 20.0), 'g_decay': (0.6, 0.9),
    'g_depth_h_ratio': (0.55, 1.0), 'g_depth_mm': (200.0, 340.0), 'g_height_mm': (280.0, 480.0),
    'g_inward_h_mm': (0.0, 40.0), 'g_inward_v_mm': (0.0, 40.0), 'g_rect_exponent': (4.0, 12.0),
    'g_rect_turn_deg': (45.0, 80.0), 'g_terminal_deg': (225.0, 280.0), 'g_throat_turn_deg': (10.0, 40.0),
    'g_width_mm': (500.0, 650.0),
    # backbone: around the passing recipe (0.45-0.65 / throat 0.25 / roll-in 0.30), bb_v opened to 0.5
    'g_bb_h': (0.45, 0.85), 'g_bb_v': (0.0, 0.5), 'g_bb_throat_frac': (0.15, 0.30), 'g_bb_rollin_frac': (0.20, 0.40),
}
# Batch 2 (2026-11-25 12:27): s1 was stopped by the bound-pinned watchdog after 30 rows with 4/6 of the top 6 at
# g_depth_h_ratio = 1.0, the SEARCH box ceiling (the kernel allows 0.5-1.2). > 1 = H panels/lips ahead of V (the
# owner's H-forward saddle), < 1 = V ahead. New identity with the kernel's range; everything else unchanged.
ROLLED_BEAK_BOUNDS = {**ROLLED_BOUNDS, 'g_depth_h_ratio': (0.55, 1.2)}
LCL_BOUNDS = {'g_T': (0.4, 0.9), 'g_fc_h_hz': (250.0, 900.0), 'g_fc_v_hz': (350.0, 1400.0), 'g_stop_deg': (60.0, 200.0),
              'g_bb_h': (0.6, 1.0), 'g_bb_v': (0.0, 0.5), 'g_bb_throat_frac': (0.15, 0.30),
              'g_bb_rollin_frac': (0.15, 0.30)}
IWAR_BOUNDS = {'g_T': (0.4, 0.9), 'g_ar_m': (1.0, 2.4), 'g_ar_p': (0.5, 2.0), 'g_fc_hz': (300.0, 900.0),
               'g_stop_deg': (88.0, 200.0),
               'g_bb_h': (0.6, 1.0), 'g_bb_v': (0.0, 0.5), 'g_bb_throat_frac': (0.15, 0.30),
               'g_bb_rollin_frac': (0.15, 0.30)}

# Owner request 2026-11-25 12:40: bring back pulled-back / pushed-forward beak mouths (freestanding horns). The
# rim-beak overlay (kind beak_v1) wraps the rows_bb_v1 CD hybrids; seeds start at zero beak (= the known variant).
RB_BOUNDS = {'g_rb_h_mm': (-60.0, 60.0), 'g_rb_v_mm': (-60.0, 60.0), 'g_rb_d_mm': (-30.0, 30.0),
             'g_rb_start_frac': (0.40, 0.85)}
RB_SEED = {'g_rb_h_mm': 0.0, 'g_rb_v_mm': 0.0, 'g_rb_d_mm': 0.0, 'g_rb_start_frac': 0.60}
BEAK = object()   # marker: wrap the seed config's generator in beak_v1

CAMPAIGNS = [  # name, seed config, bounds, CMA seed, label
    ('rolled_bb_cohort_s1', BB / 'rolled_bb_h065_th025.yaml', ROLLED_BOUNDS, 81501,
     'Rolled hybrid + CD backbone (seed: body 1 keeper, passes all six rules)'),
    ('rolled_bb_cohort_s2', BB / 'rolled2_bb_h065_th025.yaml', ROLLED_BOUNDS, 81502,
     'Rolled hybrid + CD backbone (seed: body 2 keeper, passes all six rules)'),
    ('rolled_beak_cohort_s1', BB / 'rolled_bb_h065_th025.yaml', ROLLED_BEAK_BOUNDS, 81511,
     'Rolled hybrid + CD backbone, H/V depth split opened both ways (seed: body 1 keeper)'),
    ('rolled_beak_cohort_s2', BB / 'rolled2_bb_h065_th025.yaml', ROLLED_BEAK_BOUNDS, 81512,
     'Rolled hybrid + CD backbone, H/V depth split opened both ways (seed: body 2 keeper)'),
    ('lcl_bb_cohort', VAR / 'lcl_bb_h100_v000_t25_r20.yaml', LCL_BOUNDS, 81503,
     "LABELED CD HYBRID: Le Cleac'h H/V + CD backbone (seed: closest variant, misses 8 kHz by 3.3 deg)"),
    ('iwar_bb_cohort', VAR / 'iwar_bb_h100_v000_t25_r20.yaml', IWAR_BOUNDS, 81504,
     'LABELED CD HYBRID: Iwata AR + CD backbone (seed: roll-in 0.20 variant, 2-4 kHz waistband)'),
    ('lcl_beak_cohort', VAR / 'lcl_bb_h100_v000_t25_r20.yaml', {**LCL_BOUNDS, **RB_BOUNDS}, 81513,
     "LABELED HYPOTHESIS: Le Cleac'h H/V + CD backbone + rim beak (H/V lips forward or back, 45-deg scoop)", BEAK),
    ('iwar_beak_cohort', VAR / 'iwar_bb_h100_v000_t25_r20.yaml', {**IWAR_BOUNDS, **RB_BOUNDS}, 81514,
     'LABELED HYPOTHESIS: Iwata AR + CD backbone + rim beak (H/V lips forward or back, 45-deg scoop)', BEAK),
]


def open_brief():
    b = yaml.safe_load(BRIEF_SRC.read_text(encoding='utf-8'))
    b['name'] = 'room_landscape_80x50_900_hf1440_v11cd_open115'
    b['description'] = (
        '(objective v11) HOME XO900 CD identity (room_landscape_80x50_900_hf1440_v11cd) with an OPEN size policy: '
        'envelope.enforce false, max_utilization 1.15 per axis (candidate box 690 x 552 x 552 mm, product box '
        '600 x 480 x 480 mm). Over-cap candidates are refused pre-mesh; every row records size_feasibility '
        '(margins, max utilization) for post-hoc and Pareto filtering. NEW J/BO IDENTITY: not rankable against '
        'the closed v11cd brief.')
    b['envelope'] = {**b['envelope'], 'enforce': False, 'max_utilization': 1.15, 'sanity_max_mm': 1200.0}
    return b


def main():
    brief = open_brief()
    BRIEF_OUT.write_text('# 2026-11-25: open-size copy of room_landscape_80x50_900_hf1440_v11cd.yaml for the CD-backbone '
                         'BO cohort.\n' + yaml.safe_dump(brief, sort_keys=False), encoding='utf-8', newline='\n')
    OUT.mkdir(parents=True, exist_ok=True)
    for name, src, bounds, seed, label, *wrap in CAMPAIGNS:
        cfg = yaml.safe_load(src.read_text(encoding='utf-8'))
        if wrap and wrap[0] is BEAK:
            cfg['generator'] = {**cfg['generator'], 'rows': {'type': 'beak_v1', 'parent_rows': cfg['generator']['rows']}}
            cfg['seed_params'] = {**cfg['seed_params'], **RB_SEED}
        knobs = cfg['seed_params']
        missing = sorted(set(bounds) - set(knobs))
        if missing:
            raise SystemExit(f'{name}: bounds for unknown knobs {missing}')
        out_bounds = {}
        for k, v in knobs.items():
            if k in bounds:
                lo, hi = bounds[k]
                if not lo <= float(v) <= hi:
                    raise SystemExit(f'{name}: seed {k}={v} outside [{lo}, {hi}]')
                out_bounds[k] = {'lo': float(lo), 'hi': float(hi), 'search': True}
            elif isinstance(v, (list, tuple)):
                out_bounds[k] = copy.deepcopy(cfg['bounds'][k])
            else:
                out_bounds[k] = {'lo': float(v), 'hi': float(v), 'search': False}
        cfg['mesh'] = {**cfg['mesh'], 'dof_cap_screen': 24000}   # 6000 refused ~30 % of wide rolled draws (preflight)
        cfg.update(name=name, brief=copy.deepcopy(brief), brief_file=None, bounds=out_bounds,
                   search={**SEARCH, 'seed': seed},
                   description=(f'{label}. CMA screen cohort, 100 valid solves, v11 CD XO900 OPEN (max_utilization '
                                f'1.15) brief; frozen bounds = metric-BO identity ({len(bounds)} active continuous '
                                f'dims). Winners are judged with the six predeclared CD rules, not J alone.'))
        path = OUT / f'{name}.yaml'
        path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8', newline='\n')
        print('wrote', path.as_posix(), 'active dims', len(bounds))
    klangfilm_core()



NL = chr(10)
KLANG_RUN = Path('runs/20261120T085629Z-screen-90752f')   # cd11c__klangfilm_b3_soft, v11, best J 7.048
KLANG_BEAK = {'g_beak_h_setback_mm': (0.0, 60.0), 'g_beak_v_projection_mm': (0.0, 45.0),
              'g_beak_diagonal_mm': (-20.0, 20.0), 'g_beak_start_frac': (0.50, 0.99)}   # = kernel _CORE_BOUNDS


def klangfilm_core():
    """Klangfilm-Lame H/V core: its own swept beak reopened to the kernel range (was 0-10 / pinned 0.04 / +-5)."""
    import json
    cfg = json.loads((KLANG_RUN / 'run.json').read_text(encoding='utf-8'))['config']
    best = json.loads((KLANG_RUN / 'best.json').read_text(encoding='utf-8'))
    knobs = best['params']['grid']['knobs']
    bounds = {}
    for k, b in cfg['bounds'].items():
        if k in KLANG_BEAK:
            lo, hi = KLANG_BEAK[k]
            bounds[k] = {'lo': lo, 'hi': hi, 'search': True}
        else:
            bounds[k] = dict(b)
    name = 'klangfilm_core_beak_cohort'
    cfg.update(name=name, brief=open_brief(), brief_file=None, bounds=bounds, seed_params=dict(knobs),
               search={**SEARCH, 'seed': 81515},
               description=('LABELED HYPOTHESIS (Klangfilm-Lame H/V Phase B core): own swept beak reopened to the kernel '
                            'range (H setback 0-60, V projection 0-45, diagonal +-20 mm; this kernel only sets H back / '
                            'V forward). Seed: best of cd11c__klangfilm_b3_soft (v11, J 7.048 on the 700 Hz brief). '
                            'CMA screen cohort, 100 valid, v11 CD XO900 OPEN (max_utilization 1.15).'))
    cfg['mesh'] = {**cfg['mesh'], 'dof_cap_screen': 24000}
    path = OUT / f'{name}.yaml'
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8', newline=NL)
    print('wrote', path.as_posix(), 'active dims', sum(1 for b in bounds.values() if b.get('search', True)))


if __name__ == '__main__':
    main()
