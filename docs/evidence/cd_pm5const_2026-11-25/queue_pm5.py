r"""Insert the seven pm5 jobs into the live night, right after the running job (nothing removed or reordered).

    .venv\Scripts\python.exe docs/evidence/cd_pm5const_2026-11-25/queue_pm5.py [--night cd_bo_cohort_2026-11-25] [--before klangfilm_core_beak_cohort]
"""
import argparse
from pathlib import Path

import yaml

ORDER = ['favl_pm5', 'rolled_pm5', 'lcl_beak_pm5', 'iwar_beak_pm5', 'sculpted_beak_pm5', 'sculpted_sweep_pm5',
         'klangfilm_pm5']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--night', default='cd_bo_cohort_2026-11-25')
    ap.add_argument('--before', default='klangfilm_core_beak_cohort')
    a = ap.parse_args()
    path = Path('runs/nights') / f'{a.night}.yaml'
    text = path.read_text(encoding='utf-8')
    night = yaml.safe_load(text)
    jobs = {j['id']: j for j in night['jobs']}
    if any(n in jobs for n in ORDER):
        raise SystemExit('pm5 jobs already queued')
    new = []
    for name in ORDER:
        src = jobs['favl_c500_open115_150'] if name == 'favl_pm5' else jobs[name.replace('_pm5', '_r1')]
        wd = dict(src['watchdog'])
        new.append({'id': name, 'kind': 'command', 'timeout_s': 10800, 'env': {'HORNLAB_GPU_LOCK': 'refuse'},
                    'watchdog': wd,
                    'argv': [r'.venv\Scripts\hornlab-search.exe', 'search', '--config',
                             f'examples/typologies/cd_pm5const_2026-11-25/{name}.yaml', '--mode', 'screen',
                             '--dataset-dir', 'dataset', '--cache-dir', f'runs/cd_pm5const_2026-11-25/cache_{name}',
                             '--budget', '100']})
    block = yaml.safe_dump(new, sort_keys=False, width=200)
    marker = f'- id: {a.before}\n'
    if text.count(marker) != 1:
        raise SystemExit(f'marker {marker!r} not found exactly once')
    note = ('# 17:55 EST: +-5 deg constant-directivity jobs (owner 17:43) INSERTED before '
            f'{a.before}; nothing removed. docs/evidence/cd_pm5const_2026-11-25/\n')
    head, tail = text.split(marker)
    head = head.replace('night: ', note + 'night: ', 1)
    out = head + block + marker + tail
    after = yaml.safe_load(out)
    ids = [j['id'] for j in after['jobs']]
    assert set(jobs) <= set(ids) and len(ids) == len(jobs) + len(ORDER), 'job set changed unexpectedly'
    path.write_text(out, encoding='utf-8', newline='\n')
    print(len(jobs), '->', len(ids), 'jobs; inserted', ORDER)


if __name__ == '__main__':
    main()
