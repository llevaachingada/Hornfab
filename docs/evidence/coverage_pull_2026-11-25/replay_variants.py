"""Offline re-score (no solver) of a run's stored responses under coverage-profile variants of its brief.

Question (owner, 2026-11-25): favL__2in_c500_open115 converges to ~65 x 62 deg although the brief says 80 x 50.
Cause: v9/v10/v11 corridor mode charges nothing between min_deg and max_deg (scalar_v9._plane_cov_cost); the
preferred 80/50 is unused. This replays every design of the run under:
  A current brief (parity: replayed J must equal stored J)
  B tight corridor centred on the preferred widths (H 72-88, V 42-58)
  C target mode (cost grows with distance from preferred 80/50; narrow side x cov_narrow_ratio)
and reports the J-best designs' mean H/V widths 0.9-8 kHz under each.

    .venv\Scripts\python.exe docs/evidence/coverage_pull_2026-11-25/replay_variants.py runs/<run>
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
    out = {'A_current': brief}
    b = copy.deepcopy(brief)
    prof = b['target']['coverage_profile']
    for a in prof['h']:
        a.update(min_deg=72.0, max_deg=88.0)
    for a in prof['v']:
        a.update(min_deg=42.0, max_deg=58.0)
    b['name'] += '__tight_corridor'
    out['B_tight_corridor'] = b
    c = copy.deepcopy(brief)
    c['target']['coverage_profile']['mode'] = 'target'
    for plane in ('h', 'v'):
        for a in c['target']['coverage_profile'][plane]:
            a.pop('min_deg', None)
            a.pop('max_deg', None)
    c['name'] += '__target_mode'
    out['C_target_mode'] = c
    return out


def widths(run, h):
    m = json.loads((run / 'designs' / h / 'metrics.json').read_text(encoding='utf-8'))
    f = np.array(m['freqs_hz'])
    sel = f >= 900
    return (float(np.mean(np.array(m['bw_h_deg'])[sel])), float(np.mean(np.array(m['bw_v_deg'])[sel])))


def main(run):
    run = Path(run)
    cfg = json.loads((run / 'run.json').read_text(encoding='utf-8'))['config']
    designs = sorted(p.name for p in (run / 'designs').iterdir() if (p / 'metrics.json').exists())
    report = {}
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
                hw, vw = widths(run, h)
                rows.append({'design': h, 'J': r.j, 'stored_J': r.stored_j, 'cov': (r.terms or {}).get('cov_profile'),
                             'H_mean': round(hw, 1), 'V_mean': round(vw, 1)})
            rows.sort(key=lambda r: r['J'])
            par = max((abs(r['J'] - r['stored_J']) for r in rows if r['stored_J'] is not None), default=None)
            report[name] = {'n': len(rows), 'max_parity_diff' if name == 'A_current' else 'n_scored': par if name == 'A_current' else len(rows),
                            'top5': rows[:5],
                            'spearman_vs_current': None}
            print(f'\n{name}: {len(rows)} designs' + (f', parity max |dJ| {par:.2e}' if name == 'A_current' else ''))
            for r in rows[:5]:
                print(f"   J {r['J']:.3f}  cov {r['cov'] if r['cov'] is None else round(r['cov'], 3)}  "
                      f"H {r['H_mean']}  V {r['V_mean']}  {r['design']}")
    (HERE / f'replay_{run.name}.json').write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1])
