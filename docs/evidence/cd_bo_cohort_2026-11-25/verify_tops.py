"""Queue step after the exploration cohorts: verify the family-wide top designs (GPU, one solve at a time).

For each family, pool every finished exploration run of the night (job ids ``<family>_r<i>``), take the top-N unique
designs by screen J across all runs, and re-solve each at verify fidelity with the built-in
``hornlab-search verify --run <its run> --designs <hash>`` (outputs in ``<run>/verify``). The six predeclared CD
rules are then applied offline against each family's seed design (run 1's first row), which is also verified here.
Writes ``verify_tops.json`` (what was verified, where, exit codes). J alone never promotes a design.

    .venv\\Scripts\\python.exe docs/evidence/cd_bo_cohort_2026-11-25/verify_tops.py --night cd_bo_cohort_2026-11-25 [--top 4]
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXE = str(Path('.venv') / 'Scripts' / 'hornlab-search.exe')


def family_rows(night):
    fams = {}
    for line in (Path('runs/nights') / night / 'summary.jsonl').read_text(encoding='utf-8').splitlines():
        job = json.loads(line)
        m = re.fullmatch(r'(.+)_r(\d+)', job['id'])
        if not m or not job.get('run_dir'):
            continue
        run = Path(job['run_dir'])
        nd = run / 'search.ndjson'
        if not nd.exists():
            continue
        for x in nd.read_text(encoding='utf-8').splitlines():
            if not x.strip():
                continue
            r = json.loads(x)
            if r.get('ok') and r.get('objective') is not None:
                fams.setdefault(m.group(1), []).append((r['objective'], r['design_hash'], str(run), int(m.group(2)),
                                                        r.get('n')))
    return fams


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--night', required=True)
    ap.add_argument('--top', type=int, default=4)
    args = ap.parse_args()
    plan, log = [], []
    for fam, rows in sorted(family_rows(args.night).items()):
        seen, picks = set(), []
        seed = [r for r in rows if r[3] == 1 and r[4] == 0]
        for r in seed + sorted(rows):
            if r[1] in seen:
                continue
            seen.add(r[1])
            picks.append({'family': fam, 'J_screen': r[0], 'design': r[1], 'run': r[2],
                          'role': 'seed' if r in seed else 'top'})
            if len([p for p in picks if p['role'] == 'top']) >= args.top:
                break
        plan.extend(picks)
    print(f'verifying {len(plan)} designs')
    for p in plan:
        t0 = time.time()
        cmd = [EXE, 'verify', '--run', p['run'], '--designs', p['design']]
        print('===', p['family'], p['role'], p['design'], 'screen J', round(p['J_screen'], 4), flush=True)
        rc = subprocess.call(cmd)
        log.append({**p, 'exit': rc, 'seconds': round(time.time() - t0, 1), 'verify_dir': str(Path(p['run']) / 'verify')})
        (HERE / 'verify_tops.json').write_text(json.dumps(log, indent=1) + '\n', encoding='utf-8')
    bad = [x for x in log if x['exit'] != 0]
    print(f'done: {len(log) - len(bad)} ok, {len(bad)} failed')
    return 1 if bad and len(bad) == len(log) else 0


if __name__ == '__main__':
    sys.exit(main())
