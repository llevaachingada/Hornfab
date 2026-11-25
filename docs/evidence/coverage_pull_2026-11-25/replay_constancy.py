r"""Offline re-score (no solver): what the opt-in v9 `constancy` term would do to a run (owner, 2026-11-25 17:35).

Owner intent for corridor mode: the beamwidth may sit at ANY constant angle inside the corridor, but must be flat
across frequency at that angle (e.g. 78 H / 48 V, constant 1-8 kHz = perfect). The corridor alone does not encode
that (zero cost anywhere inside [min, max]); the opt-in `objective.constancy` term (scalar_v9._plane_constancy_cost)
does: per plane, fit a constant level, clamp it into [min, max], charge mean squared deviation (deg^2/100)/tolerance.
The current briefs do not declare it. Variants:
  A current brief (parity)
  D current corridor (H 60-90, V 40-60) + constancy strict tol 0.25 (5 deg rms = 1.0)
  E +-10 corridor (H 70-90, V 40-60)  + constancy strict tol 0.25
  F +-10 corridor + constancy strict tol 1.0 (10 deg rms = 1.0)

    .venv\Scripts\python.exe docs/evidence/coverage_pull_2026-11-25/replay_constancy.py runs/<run>
"""
import copy
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.objective.replay import load_brief_context, replay_run_dir  # noqa: E402

HERE = Path(__file__).resolve().parent


def variants(brief):
    def mk(tag, h=None, v=None, tol=None):
        b = copy.deepcopy(brief)
        prof = b['target']['coverage_profile']
        if h:
            for a in prof['h']:
                a.update(min_deg=h[0], max_deg=h[1])
        if v:
            for a in prof['v']:
                a.update(min_deg=v[0], max_deg=v[1])
        if tol:
            b['objective']['constancy'] = {'mode': 'strict', 'weight': 1.0, 'tolerance': tol}
        b['name'] += '__' + tag
        return b
    return {'A_current': brief,
            'D_constancy_t025': mk('constancy_t025', tol=0.25),
            'E_pm10_constancy_t025': mk('pm10_constancy_t025', h=(70.0, 90.0), v=(40.0, 60.0), tol=0.25),
            'F_pm10_constancy_t1': mk('pm10_constancy_t1', h=(70.0, 90.0), v=(40.0, 60.0), tol=1.0)}


def shape(run, h):
    m = json.loads((run / 'designs' / h / 'metrics.json').read_text(encoding='utf-8'))
    f = np.array(m['freqs_hz'])
    sel = (f >= 900) & (f <= 8000)
    bh, bv = np.array(m['bw_h_deg'], float)[sel], np.array(m['bw_v_deg'], float)[sel]
    return {'H_mean': round(float(np.nanmean(bh)), 1), 'H_std': round(float(np.nanstd(bh)), 1),
            'H_range': [round(float(np.nanmin(bh)), 1), round(float(np.nanmax(bh)), 1)],
            'V_mean': round(float(np.nanmean(bv)), 1), 'V_std': round(float(np.nanstd(bv)), 1),
            'V_range': [round(float(np.nanmin(bv)), 1), round(float(np.nanmax(bv)), 1)]}


def main(run):
    run = Path(run)
    cfg = json.loads((run / 'run.json').read_text(encoding='utf-8'))['config']
    designs = sorted(p.name for p in (run / 'designs').iterdir() if (p / 'metrics.json').exists())
    shapes = {h: shape(run, h) for h in designs}
    report, ranks = {}, {}
    with tempfile.TemporaryDirectory() as td:
        for name, b in variants(cfg['brief']).items():
            path = Path(td) / f'{name}.yaml'
            path.write_text(yaml.safe_dump(b, sort_keys=False), encoding='utf-8')
            brief = load_brief_context(path)
            rows = []
            for h in designs:
                r = replay_run_dir(run, h, brief=brief)
                if r.j is None:
                    continue
                t = r.terms or {}
                rows.append({'design': h, 'J': round(r.j, 4), 'stored_J': r.stored_j,
                             'cov': round(t.get('cov_profile', 0.0), 4),
                             'constancy': round(t['constancy'], 4) if 'constancy' in t else None, **shapes[h]})
            rows.sort(key=lambda r: r['J'])
            ranks[name] = [r['design'] for r in rows]
            par = max((abs(r['J'] - r['stored_J']) for r in rows if r['stored_J'] is not None), default=None)
            report[name] = {'n': len(rows), 'parity_max_dJ': par if name == 'A_current' else None, 'top5': rows[:5]}
    best_a = ranks['A_current'][0]
    for name in report:
        report[name]['rank_of_current_best'] = ranks[name].index(best_a) + 1
        report[name]['current_best_row'] = next(r for r in [*report[name]['top5']] if r['design'] == best_a) \
            if best_a in [r['design'] for r in report[name]['top5']] else None
    out = HERE / f'replay_constancy_{run.name}.json'
    out.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    for name, rep in report.items():
        print(f"\n{name}: n={rep['n']} rank of A-best={rep['rank_of_current_best']}"
              + (f" parity {rep['parity_max_dJ']:.1e}" if rep['parity_max_dJ'] is not None else ''))
        for r in rep['top5']:
            print(f"  {r['design'][:12]} J {r['J']:.3f} cov {r['cov']:.3f} const {r['constancy']}  "
                  f"H {r['H_mean']}±{r['H_std']} {r['H_range']}  V {r['V_mean']}±{r['V_std']} {r['V_range']}")
    print('wrote', out)


if __name__ == '__main__':
    main(sys.argv[1])
