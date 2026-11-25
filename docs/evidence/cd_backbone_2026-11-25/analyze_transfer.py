"""Batch 7 readout: the rolled keeper recipe on a second rolled body, scored against its own control.

Reuses analyze.py's load/summarize/check (the predeclared six rules). No solver calls.

    .venv\\Scripts\\python.exe docs/evidence/cd_backbone_2026-11-25/analyze_transfer.py
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, 'docs/evidence/cd_backbone_2026-11-25')
import analyze as A  # noqa: E402

NIGHT = 'cd_backbone_b7_2026-11-25'
jobs = A.jobs_from([NIGHT])
recs = {k: A.load(v['run']) for k, v in jobs.items()}
runs = {k: A.summarize(v) for k, v in recs.items()}
ctl = runs['rolled2_bb_control']
out = {'runs': runs, 'jobs': jobs,
       'checks': {k: A.check(k, v, ctl) for k, v in runs.items() if k != 'rolled2_bb_control'},
       'deltas_vs_control': {k: A.deltas(ctl, v) for k, v in runs.items() if k != 'rolled2_bb_control'}}
(A.HERE / 'results_transfer.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
for k, r in runs.items():
    f = [round(x) for x in r['freqs']]
    g = lambda key, b: r[key][f.index(b)]
    print(f"{k:24s} J {r['J']:.3f} Re896 {g('re_z', 896):.3f} minRe {r['min_re_z_from_900']:.3f} "
          f"mid {[round(g('H', b), 1) for b in A.MID]} HF {[round(g('H', b), 1) for b in A.HF]} "
          f"V8k {g('V', 8000):.1f} D8k {g('D', 8000):.1f} lobes {r['multilobe_h']}/{r['multilobe_v']}")
for k, c in out['checks'].items():
    print('CHECK', k, ' '.join(f'{a}={b}' for a, b in c.items()))
