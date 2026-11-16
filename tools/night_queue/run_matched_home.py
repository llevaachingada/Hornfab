"""Frozen-cohort home comparison. Prepare once, then run individual bounded arms.

No solve is performed by prepare. An arm refuses any changed frozen input or selected
training set. The screen budgets are nominally 80, not identical BEM-call budgets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
CONFIG = REPO / 'examples/typologies/home_landscape_2026-11-15/hl__osse_rrect_fold_warm_v7.yaml'
DATASET = REPO / 'dataset'
PYTHON = REPO / '.venv/Scripts/python.exe'
CLI = REPO / '.venv/Scripts/hornlab-search.exe'
SEEDS = (88101, 88102)
ORDER = [('cma', 88101), ('scalar', 88101), ('turbo', 88101),
         ('turbo', 88102), ('cma', 88102), ('scalar', 88102)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def selected_rows(training, dataset, read_metas):
    """Recover precisely the native builder's selected measured rows, never raw run rows."""
    from hornlab_search.types import Design
    if training.status != 'ok' or training.n < 100:
        raise ValueError(f'cohort not eligible: {training.status}, n={training.n}')
    ids = list(training.selected_ids)
    if len(ids) != training.n or len(set(ids)) != len(ids):
        raise ValueError('selected training IDs are missing or duplicated')
    by_id = {oid: float(value[0]) if getattr(value, 'ndim', 0) else float(value)
             for oid, value in zip(training.ids, training.J)}
    identities = training.meta['identities']
    cache, rows = {}, []
    for oid in ids:
        identity = identities[oid]
        meta = read_metas(dataset, int(identity['shard']), cache).get(int(identity['row']))
        if not isinstance(meta, dict) or meta.get('ok') is not True:
            raise ValueError(f'{oid}: missing valid dataset record')
        params, family = meta.get('params'), meta.get('family')
        if not isinstance(params, dict) or not isinstance(family, str):
            raise ValueError(f'{oid}: missing design')
        actual = Design(family, params).hash()
        if actual != identity['design_hash'] or actual != meta.get('design_hash'):
            raise ValueError(f'{oid}: design hash mismatch')
        j = float(identity['J'])
        if not math.isfinite(j) or oid not in by_id or float(by_id[oid]) != j:
            raise ValueError(f'{oid}: score mismatch')
        rows.append({'n': len(rows), 'ok': True, 'params': params, 'objective': j,
                     'design_hash': actual, 'physical_id': oid})
    return rows


def training(cohort):
    from hornlab_search.bo.data import build_native_training_set
    return build_native_training_set(str(CONFIG), scores_json=str(cohort / 'offline_scores.json'),
                                     catalog_csv=str(cohort / 'catalog.csv'),
                                     dataset_root=str(DATASET), require_single_fidelity=True)


def tracked_files(brief):
    # Freeze all project Python code used by execution, not only this wrapper.
    files = [CONFIG, brief, Path(__file__).resolve(), REPO / 'tools/night_queue/run_bo_arm.py',
             REPO / 'tools/bo_compare/prepare_study.py']
    files.extend(sorted((REPO / 'hornlab_search').rglob('*.py')))
    return files


def prepare(root):
    from hornlab_search.bo.data import _read_shard_metas
    from hornlab_search.config import _load_yaml_extends, _resolve_path, load_config
    from hornlab_search.search.evaluate import collect_lib_shas
    if root.exists():
        raise ValueError('comparison root already exists')
    root.mkdir(parents=True)
    cohort = root / 'cohort'
    cmd = [str(PYTHON), '-m', 'tools.analysis.study_cohort', '--config', str(CONFIG),
           '--dataset', str(DATASET), '--out', str(cohort), '--limit', '1024']
    subprocess.run(cmd, cwd=REPO, check=True, timeout=1800)
    tr = training(cohort)
    rows = selected_rows(tr, DATASET, _read_shard_metas)
    raw = _load_yaml_extends(CONFIG)
    cfg = load_config(CONFIG)
    brief = _resolve_path(raw['brief_file'], CONFIG.parent, REPO).resolve()
    pins = json.loads((cohort / 'offline_scores.json').read_text(encoding='utf-8')).get('selection', {}).get('dependency_pins', {})
    actual_pins = collect_lib_shas()
    for key in ('hornlab_mesher', 'hornlab_beat_bem', 'hornlab_plots'):
        if not pins.get(key) or pins[key] == 'unknown' or pins[key] != actual_pins.get(key):
            raise ValueError(f'dependency pin mismatch {key}: {pins.get(key)} != {actual_pins.get(key)}')
    raw['brief_file'] = str(brief)
    source = root / 'warm_source'
    source.mkdir()
    (source / 'run.json').write_text(json.dumps({'family': cfg.family, 'config': raw,
        'objective_version': cfg.objective_version, 'adapter': 'strict-selected-native-v1'}, indent=2), encoding='utf-8')
    (source / 'search.ndjson').write_text(''.join(json.dumps(r, allow_nan=False) + '\n' for r in rows), encoding='utf-8')
    best = min(rows, key=lambda r: (r['objective'], r['design_hash']))
    raw['seed_params'] = best['params']
    if isinstance(raw.get('generator'), dict):
        raw['generator']['seed_policy'] = 'explicit'
    raw.setdefault('search', {}).update({'budget': 80, 'budget_counts': 'new', 'max_attempts': None,
        'warm_start': {'from_runs': [str(source)], 'top_k': 10, 'sigma_from_spread': True}})
    cma_config = root / 'cma.yaml'
    cma_config.write_text(yaml.safe_dump(raw, sort_keys=False), encoding='utf-8')
    files = tracked_files(brief) + [cohort / 'catalog.csv', cohort / 'offline_scores.json',
                                  source / 'run.json', source / 'search.ndjson', cma_config]
    manifest = {'schema': 'home-matched-v1', 'config': str(CONFIG), 'brief': str(brief),
                'cohort': str(cohort), 'dataset': str(DATASET), 'rows': tr.n,
                'selected_ids': list(tr.selected_ids), 'dependency_pins': pins,
                'best': {'design_hash': best['design_hash'], 'J': best['objective']},
                'arms': [{'method': m, 'seed': s} for m, s in ORDER],
                'budget': {'cma_new_candidates': 80, 'bo_screen_call_cap': 80, 'verify_cap': 2},
                'cache': 'normal project cache; cache hits and refusals counted separately',
                'files_sha256': {str(p): sha(p) for p in files}}
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'status': 'prepared', 'manifest': str(root / 'manifest.json'), 'rows': tr.n}))


def check(root):
    global CONFIG
    from hornlab_search.bo.data import _read_shard_metas
    from hornlab_search.search.evaluate import collect_lib_shas
    m = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    CONFIG = Path(m['config'])
    for path, expected in m['files_sha256'].items():
        if sha(path) != expected:
            raise ValueError(f'frozen input changed: {path}')
    pins = collect_lib_shas()
    for key, expected in m['dependency_pins'].items():
        if key in ('hornlab_mesher', 'hornlab_beat_bem', 'hornlab_plots') and pins.get(key) != expected:
            raise ValueError(f'dependency pin changed: {key}')
    tr = training(Path(m['cohort']))
    if list(tr.selected_ids) != m['selected_ids']:
        raise ValueError('training selection changed')
    rows = selected_rows(tr, DATASET, _read_shard_metas)
    saved = [json.loads(x) for x in (root / 'warm_source/search.ndjson').read_text(encoding='utf-8').splitlines()]
    if rows != saved:
        raise ValueError('selected dataset rows changed')
    return m


def arm(root, method, seed):
    m = check(root)
    if (method, seed) not in ORDER:
        raise ValueError('arm not in manifest')
    arm_root = root / f'{method}_{seed}'
    if arm_root.exists():
        raise ValueError('arm already exists; reconciliation is required')
    arm_root.mkdir()
    status_path = arm_root / 'arm_status.json'
    status = {'method': method, 'seed': seed, 'state': 'started',
              'started_utc': datetime.now(timezone.utc).isoformat()}
    status_path.write_text(json.dumps(status, indent=2), encoding='utf-8')
    started = time.monotonic()
    try:
        rc = execute_arm(root, arm_root, m, method, seed)
        status.update(state='ended', returncode=rc)
        return rc
    except BaseException as exc:
        status.update(state='exception', returncode=None, exception=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        status.update(ended_utc=datetime.now(timezone.utc).isoformat(),
                      elapsed_seconds=time.monotonic() - started)
        status_path.write_text(json.dumps(status, indent=2), encoding='utf-8')


def execute_arm(root, arm_root, m, method, seed):
    if method in ('scalar', 'turbo'):
        cmd = [sys.executable, str(REPO / 'tools/night_queue/run_bo_arm.py'),
               '--root', str(arm_root / 'study'), '--cohort', m['cohort'], '--config', str(CONFIG),
               '--policy', method, '--seed', str(seed), '--budget-profile', 'comparison-80x2',
               '--scores-sha256', m['files_sha256'][str(Path(m['cohort']) / 'offline_scores.json')],
               '--catalog-sha256', m['files_sha256'][str(Path(m['cohort']) / 'catalog.csv')]]
        return subprocess.run(cmd, cwd=REPO, check=False).returncode
    runs = arm_root / 'runs'
    runs.mkdir()
    cmd = [str(CLI), 'search', '--config', str(root / 'cma.yaml'), '--mode', 'screen',
           '--budget', '80', '--cma-seed', str(seed), '--runs-dir', str(runs)]
    rc = subprocess.run(cmd, cwd=REPO, check=False).returncode
    candidates = [p for p in runs.iterdir() if p.is_dir() and (p / 'search.ndjson').is_file()]
    if rc or len(candidates) != 1:
        raise ValueError(f'CMA search rc={rc}, candidate run count={len(candidates)}')
    check(root)
    return subprocess.run([str(CLI), 'verify', '--run', str(candidates[0]), '--top', '2'],
                          cwd=REPO, check=False).returncode


def report(root):
    from tools.analysis._common import cost_ledger, read_ndjson
    m = check(root)
    result = {'schema': 'home-matched-report-v1', 'manifest_sha256': sha(root / 'manifest.json'),
              'baseline': m['best'], 'arms': [],
              'limits': 'Candidate budgets differ from BEM call caps. Compare successful-query prefixes and observed/inferred costs separately; missing arms or verify are censored. Do not pool J across tasks.'}
    for method, seed in ORDER:
        arm_root = root / f'{method}_{seed}'
        row = {'method': method, 'seed': seed, 'status': 'not_started'}
        if arm_root.exists():
            row['status'] = 'incomplete'
            status_file = arm_root / 'arm_status.json'
            if status_file.is_file():
                row['execution'] = json.loads(status_file.read_text(encoding='utf-8'))
                execution = row['execution']
                if execution.get('state') == 'exception' or (execution.get('state') == 'ended' and execution.get('returncode') != 0):
                    row['status'] = 'arm_failed'
            run = None
            if method == 'cma':
                run_dirs = list((arm_root / 'runs').glob('*-screen-*')) if (arm_root / 'runs').exists() else []
                if len(run_dirs) == 1:
                    run = run_dirs[0]
            else:
                package = arm_root / 'study/package.json'
                if package.is_file():
                    pkg = json.loads(package.read_text(encoding='utf-8'))
                    run = REPO / 'runs' / ('study-' + pkg['package_id'][:16]) / 'screen'
            if run and (run / 'search.ndjson').is_file():
                screens = read_ndjson(run / 'search.ndjson')
                verify = read_ndjson(run.parent / 'verify/search.ndjson' if method != 'cma' else run / 'verify/search.ndjson')
                good_by_id = {r['design_hash']: r for r in verify if r.get('ok') is True
                              and r.get('design_hash') and isinstance(r.get('objective'), (int, float))
                              and math.isfinite(r['objective']) and r['objective'] < 900}
                good = list(good_by_id.values())
                execution = row.get('execution', {})
                verified_status = ('verified_available' if len(good) >= 2 and
                                   execution.get('state') == 'ended' and execution.get('returncode') == 0
                                   else 'verify_incomplete')
                if execution.get('state') == 'exception' or (execution.get('state') == 'ended' and execution.get('returncode') != 0):
                    verified_status = 'arm_failed'
                row.update(run=str(run), screen_cost=cost_ledger(screens), verify_cost=cost_ledger(verify),
                           successful_screen_j=[r['objective'] for r in screens if r.get('ok') is True and isinstance(r.get('objective'), (int, float)) and math.isfinite(r['objective'])],
                           verified_best=min((r['objective'] for r in good), default=None),
                           verified_count=len(good), status=verified_status)
        result['arms'].append(row)
    out = root / 'report.json'
    out.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({'report': str(out), 'arms': [{'method': r['method'], 'seed': r['seed'], 'status': r['status']} for r in result['arms']]}))


def main():
    global CONFIG
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'arm', 'report'))
    parser.add_argument('--root', required=True)
    parser.add_argument('--config', help='task config for prepare')
    parser.add_argument('--method', choices=('cma', 'scalar', 'turbo'))
    parser.add_argument('--seed', type=int)
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        if args.action == 'prepare':
            if args.config:
                CONFIG = Path(args.config).resolve()
            prepare(root)
            return 0
        if args.config:
            parser.error('--config is only valid for prepare')
        if args.action == 'report':
            report(root)
            return 0
        if args.method is None or args.seed is None:
            parser.error('arm requires --method and --seed')
        return arm(root, args.method, args.seed)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f'comparison refused: {exc}', file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
