"""Inventory queued scoring contracts without starting workers or solving acoustics.

Hashes of resolved score, bounds and fidelity are audit fingerprints, not the
project's result identities. An untagged config is not evidence of a mismatch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hornlab_search.config import load_config  # noqa: E402
from hornlab_search.studies.builders import _read_task  # noqa: E402


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     default=str).encode()).hexdigest()


def option(argv, name):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def audit(queue, root=ROOT):
    root = Path(root).resolve()
    queue = Path(queue).resolve()
    data = yaml.safe_load(queue.read_text(encoding='utf-8'))
    result = {'queue': str(queue), 'queue_sha256': hashlib.sha256(queue.read_bytes()).hexdigest(),
              'limitations': 'Fingerprints are audit-specific, not result identities. Untagged is not proof of mismatch; no acoustic certification. Indirect jobs require execution artifact review.',
              'jobs': []}
    for job in data['jobs']:
        argv = job.get('argv', [])
        config, task = option(argv, '--config'), option(argv, '--task')
        row = {'id': job['id'], 'argv': argv, 'status': 'indirect_or_non_scoring'}
        if not config and not task:
            row['reason'] = 'No explicit --config or --task; review package, source job, or verification inputs.'
        else:
            try:
                resolved = _read_task({'name': task} if task else {}, root=root,
                                      config=(root / config) if config else None)
                cfg = load_config(resolved['config'])
                config_tag = cfg.raw.get('directivity')
                brief_tag = (cfg.brief or {}).get('directivity')
                valid_tags = {'cd', 'narrowing'}
                tag_status = ('untagged_or_unrecognized' if config_tag not in valid_tags or brief_tag not in valid_tags
                              else 'declared_match' if config_tag == brief_tag else 'declared_mismatch')
                score = {'objective_version': cfg.objective_version, 'target': cfg.target_raw,
                         'weights': cfg.weights, 'objective': cfg.objective_params}
                fidelity = {'grid': cfg.grid, 'mesh': cfg.raw.get('mesh'), 'solve': cfg.raw.get('solve'),
                            'mode': option(argv, '--mode'), 'budget_profile': option(argv, '--budget-profile')}
                row.update(status='resolved', task=task, config=str(resolved['config']),
                           config_sha256=resolved['config_sha256'], brief=str(resolved['brief']),
                           brief_sha256=resolved['brief_sha256'], family=cfg.family,
                           directivity_tags={'config': config_tag, 'brief': brief_tag, 'status': tag_status},
                           acoustic_review='manual_review_required_not_certified',
                           score=score, score_fingerprint_sha256=fingerprint(score),
                           bounds=cfg.bounds_raw, bounds_fingerprint_sha256=fingerprint(cfg.bounds_raw),
                           fidelity=fidelity, fidelity_fingerprint_sha256=fingerprint(fidelity))
            except Exception as exc:
                row.update(status='unresolved', reason=f'{type(exc).__name__}: {exc}')
        result['jobs'].append(row)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('queue', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.queue)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(f"{len(result['jobs'])} jobs; {sum(j['status'] == 'unresolved' for j in result['jobs'])} unresolved; {args.out}")
    return int(any(j['status'] == 'unresolved' for j in result['jobs']))


if __name__ == '__main__':
    raise SystemExit(main())
