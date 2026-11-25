"""Continuation of favL__2in_c500 (run 20261121T003823Z-screen-75c147) on the open115 brief.

Owner ask (2026-11-25): open the knobs that are pinned at a wall, narrow the knobs that are not
moving J, continue for another 150 valid solves, and keep it cumulatively usable by the scalar
and metric-aware BO pipelines.

Rules used (established 2026-11-25, docs/evidence/cd_bo_cohort_2026-11-25/PREDECLARED.md):
* open envelope: enforce: false + max_utilization 1.15 -> candidate box 575 mm per axis; over-cap
  candidates are redrawn pre-mesh, every row records size_feasibility. There is no soft size
  term in J.
* ONE frozen search box + brief = ONE BO identity. 150 valid rows clears the metric-BO gate
  (>=100 usable screen rows/identity) and stays under the 256 training-selection cap.
* wall knobs opened; inert knobs narrowed around the incumbent; every box clamped to the legal
  interval probed through the real generator with the open brief.

    .venv\\Scripts\\python.exe docs/evidence/favL_2in_c500_continue_2026-11-25/build.py --write
"""
import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.bo.encoding import ActiveProjection  # noqa: E402
from hornlab_search.config import load_config  # noqa: E402
from hornlab_search.design.generated import materialize  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = Path.cwd()
BRIEF_SRC = REPO / 'examples/briefs/hf2in_2026-11-20/compact500_xo900_80x50_hf2in_v11cd.yaml'
BRIEF_OUT = REPO / 'examples/briefs/hf2in_2026-11-20/compact500_xo900_80x50_hf2in_v11cd_open115.yaml'
CFG_OUT = REPO / 'examples/typologies/favL_2026-11-20/favL__2in_c500_open115.yaml'
RUN75 = REPO / 'runs/20261121T003823Z-screen-75c147'
CFG_SRC = REPO / 'examples/typologies/favL_2026-11-20/favL__2in_c500.yaml'

#: Wide candidate scan per knob (the legal sub-interval containing the seed becomes the box).
SCAN = {
    'g_k': (0.4, 2.2),
    'g_a_v_deg': (24.0, 40.0),
    'g_s': (0.24, 0.44),
    'g_throat_hv_ratio': (0.4, 2.5),
    'g_wrap_deg': (50.0, 160.0),
    'g_L_mm': (200.0, 290.0),
    'g_r_lip_mm': (8.0, 30.0),
    'g_a_h_deg': (30.0, 38.0),
    'g_n': (1.8, 3.4),
    'g_sf_ab': (0.78, 0.98),
    'g_sf_amt': (0.10, 0.32),
}
#: Desired continuation box: open the three walls, tighten the low-influence knobs.
DESIRED = {
    'g_k': (0.85, 1.35),              # was 1.000-2.200, best 1.001 at the low wall (rho +0.58)
    'g_a_v_deg': (27.5, 34.5),        # was 20-31, best 31.000 at the high wall (rho -0.55)
    'g_s': (0.30, 0.40),              # was 0.200-0.380, best 0.340, rho -0.54, opens the high side
    'g_throat_hv_ratio': (0.85, 1.80),  # was 1.000-4.000, best 1.121, 3/6 at the low wall
    'g_wrap_deg': (70.0, 130.0),      # was 50-160, rho -0.19
    'g_L_mm': (230.0, 275.0),         # was 190-290, rho -0.17; high L drove the envelope refusals
    'g_r_lip_mm': (13.0, 23.0),       # was 8-30, rho +0.14
    'g_a_h_deg': (32.2, 34.5),        # was 32-37, rho +0.10
    'g_n': (2.5, 3.1),                # was 1.8-3.2, rho -0.08
    'g_sf_ab': (0.86, 0.91),          # was 0.700-0.900, rho 0.05 (inert); tiny opening clears the wall
    'g_sf_amt': (0.19, 0.26),         # was 0.120-0.380, rho -0.01 (inert)
}


def load_seed():
    best = json.loads((RUN75 / 'best.json').read_text(encoding='utf-8'))
    return best['design_hash'], best['objective'], dict(best['params']['grid']['knobs'])


def write_brief():
    brief = yaml.safe_load(BRIEF_SRC.read_text(encoding='utf-8'))
    brief['name'] = 'compact500_xo900_80x50_hf2in_v11cd_open115'
    brief['description'] = (
        '(objective v11) COMPACT500 XO900 2-INCH CD identity (compact500_xo900_80x50_hf2in_v11cd) '
        'with an OPEN size policy: envelope.enforce false, max_utilization 1.15 per axis '
        '(candidate box 575 x 575 x 575 mm, product box 500 x 500 x 500 mm). Over-cap candidates '
        'are refused pre-mesh; every row records size_feasibility (margins, max utilization) for '
        'post-hoc and Pareto filtering. There is no soft size term in J. NEW J/BO IDENTITY: not '
        'rankable against the closed v11cd brief or any v7/v9/v10 brief.'
    )
    brief['envelope'] = {
        'max_depth_mm': 500.0, 'max_mouth_h_mm': 500.0, 'max_mouth_w_mm': 500.0,
        'enforce': False, 'max_utilization': 1.15, 'sanity_max_mm': 1200.0,
    }
    header = ('# 2026-11-25: open-size copy of compact500_xo900_80x50_hf2in_v11cd.yaml for the\n'
              '# favL__2in_c500 continuation. Same acoustic target; NEW J/BO identity.\n')
    BRIEF_OUT.write_text(header + yaml.safe_dump(brief, sort_keys=False, allow_unicode=True),
                         encoding='utf-8', newline='\n')
    print('wrote', BRIEF_OUT.relative_to(REPO))


def legal_interval(gen, knobs, key, scan, brief, n=41):
    """Contiguous legal sub-interval of scan containing the seed (all other knobs at the seed)."""
    lo, hi = scan
    seed = float(knobs[key])
    grid = sorted(set(np.linspace(lo, hi, n).round(6).tolist()) | {seed})
    ok = {}
    for v in grid:
        try:
            materialize(gen, {**knobs, key: float(v)}, brief)
            ok[v] = True
        except Exception:  # noqa: BLE001 - any refusal = not legal at this point
            ok[v] = False
    if not ok[seed]:
        raise SystemExit(f'{key}: seed {seed} itself is refused with the open brief')
    i = grid.index(seed)
    a = i
    while a > 0 and ok[grid[a - 1]]:
        a -= 1
    b = i
    while b < len(grid) - 1 and ok[grid[b + 1]]:
        b += 1
    return grid[a], grid[b], sum(ok.values()), len(grid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true', help='write brief + config after printing')
    args = ap.parse_args()

    write_brief()
    cfg = yaml.safe_load(CFG_SRC.read_text(encoding='utf-8'))
    loaded = load_config(CFG_SRC)
    brief = loaded.brief
    brief['name'] = 'compact500_xo900_80x50_hf2in_v11cd_open115'
    brief['envelope'] = {**brief['envelope'], 'enforce': False, 'max_utilization': 1.15,
                         'sanity_max_mm': 1200.0}
    gen = loaded.generator
    seed_hash, seed_j, seed_knobs = load_seed()
    print(f'seed {seed_hash} J {seed_j:.5f}')

    report = {'seed': {'design_hash': seed_hash, 'objective': seed_j, 'knobs': seed_knobs},
              'scan': {k: list(v) for k, v in SCAN.items()}, 'desired': {k: list(v) for k, v in DESIRED.items()},
              'legal': {}}
    box = {}
    for key, rng in SCAN.items():
        lo, hi, n_ok, n = legal_interval(gen, seed_knobs, key, rng, brief)
        report['legal'][key] = {'legal_at_seed': [lo, hi], 'legal_points': f'{n_ok}/{n}', 'seed': seed_knobs[key]}
        dlo, dhi = DESIRED[key]
        blo, bhi = max(dlo, lo), min(dhi, hi)
        if not blo <= float(seed_knobs[key]) <= bhi:
            raise SystemExit(f'{key}: desired [{dlo}, {dhi}] clipped by legal [{lo}, {hi}] loses the seed')
        box[key] = (blo, bhi)
        print(f'   {key:20s} legal [{lo:9.4f}, {hi:9.4f}]  desired [{dlo:8.4f}, {dhi:8.4f}]  -> box [{blo:8.4f}, {bhi:8.4f}]')
    report['box'] = {k: list(v) for k, v in box.items()}

    # Uniform admission over the final box, through the real generator + open brief.
    rng = np.random.default_rng(20261125)
    kinds = {}
    n_draws = 128
    for _ in range(n_draws):
        cand = {**seed_knobs}
        for k in box:
            lo, hi = box[k]
            cand[k] = float(lo + rng.random() * (hi - lo))
        try:
            materialize(gen, cand, brief)
            kinds['ok'] = kinds.get('ok', 0) + 1
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            key = 'invalid_envelope' if 'invalid_envelope' in msg else msg.split(':')[0][:50]
            kinds[key] = kinds.get(key, 0) + 1
    report['uniform_admission'] = {'draws': n_draws, 'counts': kinds}
    print(f'   uniform admission {kinds.get("ok", 0)}/{n_draws}  {kinds}')

    fixed = {k: float(v) for k, v in seed_knobs.items() if k not in box}
    bounds = {k: {'lo': float(lo), 'hi': float(hi)} for k, (lo, hi) in box.items()}
    bounds.update({k: {'lo': v, 'hi': v, 'search': False} for k, v in fixed.items()})
    new_cfg = copy.deepcopy(cfg)
    new_cfg.update(
        name='favL__2in_c500_open115',
        brief_file='../../briefs/hf2in_2026-11-20/compact500_xo900_80x50_hf2in_v11cd_open115.yaml',
        seed_params=dict(seed_knobs),
        bounds=bounds,
        search={
            'algorithm': 'cma', 'sigma0': 0.12, 'seed': 1234, 'budget': 150,
            'popsize': None, 'tolfun': 0.001,
            'infeasible_penalty': 'resample_strict', 'budget_counts': 'valid',
            'max_attempts': 450, 'error_policy': 'retry_same_then_stop',
            'warm_start': {
                'from_runs': [str(RUN75)], 'top_k': 10, 'sigma_from_spread': True,
                # The only brief delta is envelope.enforce false + max_utilization 1.15. Every
                # accepted row in 75c147 is inside the open cap, so its acoustic J is unchanged;
                # the cross-brief flag is the deliberate continuation override, not a merge.
                'allow_cross_brief': True,
            },
        },
        description=('Continuation of favL__2in_c500 (run 20261121T003823Z-screen-75c147, 80 valid, '
                     'best J 1.870458 at n=119, design 0ae816f04c06) on the open115 brief: g_k low, '
                     'g_a_v high and g_throat_hv_ratio low opened off their walls; inert g_sf_amt / '
                     'g_sf_ab / g_n / g_a_h tightened; 150 valid screen solves; one frozen BO identity '
                     '(no soft size term in J; size_feasibility is post-hoc).'),
    )
    report['config'] = {k: new_cfg[k] for k in ('name', 'brief_file', 'seed_params', 'bounds', 'search')}
    (HERE / 'probe.json').write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    print('wrote', (HERE / 'probe.json').relative_to(REPO))

    if not args.write:
        return
    CFG_OUT.write_text(yaml.safe_dump(new_cfg, sort_keys=False, allow_unicode=True),
                       encoding='utf-8', newline='\n')
    print('wrote', CFG_OUT.relative_to(REPO))

    # BO encoding round trip + admission through the canonical DesignSpace path.
    c = load_config(CFG_OUT)
    space = DesignSpace.from_config(c)
    proj = ActiveProjection.identity(space)
    v = proj.normalize_design(space.seed, verify_round_trip=True)
    rt = proj.denormalize(v).hash() == space.seed.hash()
    r2 = np.random.default_rng(1)
    ok = 0
    kinds2 = {}
    n2 = 128
    for _ in range(n2):
        try:
            space.denormalize(r2.random(len(space.keys())))
            ok += 1
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            key = 'invalid_envelope' if 'invalid_envelope' in msg else msg.split(':')[0][:50]
            kinds2[key] = kinds2.get(key, 0) + 1
    out = {'encoding_dims': proj.d, 'seed_round_trip': bool(rt), 'admission': ok / n2,
           'draws': n2, 'counts': kinds2, 'keys': list(space.keys())}
    (HERE / 'space_preflight.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    print(f'BO encoding d={proj.d} round-trip {rt} admission {ok}/{n2} {kinds2}')


if __name__ == '__main__':
    main()
