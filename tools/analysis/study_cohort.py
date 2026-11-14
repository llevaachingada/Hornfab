"""Prepare a task-specific scalar study cohort using canonical offline replay.

Reads dataset metadata/arrays without opening a writable DatasetStore. The caller
chooses one config, backend and fidelity. Distinct dependency/grid groups remain
separate; the largest compatible group is selected and all exclusions disclosed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys

import numpy as np

from hornlab_search.config import load_config
from hornlab_search.objective import replay
# Existing analysis CLIs share their sibling _common module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools.analysis import catalog
from tools.analysis.offline_scores import iter_dataset_rows


def prepare(config, dataset, out, *, limit=256):
    config, dataset, out = map(lambda p: Path(p).resolve(), (config, dataset, out))
    if out == dataset or dataset in out.parents:
        raise ValueError('output must be outside the source dataset')
    cfg = load_config(config)
    brief = replay.brief_from_config(config)
    groups = {}
    excluded = Counter()
    for shard, row, meta, _ in iter_dataset_rows(dataset):
        if catalog._config_name(meta) != cfg.name:
            continue
        solve = catalog._solve_block(meta)
        if (meta.get('ok') is not True or meta.get('objective_version') != cfg.objective_version
                or solve.get('mode') != 'screen' or solve.get('backend') != cfg.solve.backend):
            excluded['failed_or_incompatible_version_backend_fidelity'] += 1
            continue
        entry = catalog._record_entry(dataset, {'shard': shard, 'name': f'shard-{shard:04d}.jsonl'},
                                      {'row': row, 'meta': meta, 'line': row + 1, 'offset': None},
                                      index_entry=None)
        # bo.data joins catalog locators by the explicit dataset root's name.
        entry['source']['root'] = dataset.name
        prov = entry['provenance']
        key = (entry['dependency_hash'], entry['grid_hash'], prov.get('brief_hash'),
               entry['task_identity'])
        groups.setdefault(key, []).append((shard, row, meta, entry))
    if not groups:
        raise ValueError('no successful screen records for the selected task/backend/version')
    key = sorted(groups, key=lambda k: (-len(groups[k]), str(k)))[0]
    selected = groups[key]
    excluded['other_dependency_grid_brief_groups'] = sum(len(v) for k, v in groups.items() if k != key)
    rows, entries = [], []
    for shard, row, meta, entry in selected[:limit]:
        path = dataset / f'shard-{shard:04d}' / f'rec-{row:04d}.npz'
        if not path.is_file():
            excluded['missing_arrays'] += 1
            continue
        with np.load(path, allow_pickle=False) as arrays:
            result = replay.replay_record(meta, {k: arrays[k] for k in arrays.files}, brief=brief)
        rows.append({'shard': shard, 'row': row, 'config_name': cfg.name,
                     'catalog_run_id': entry.get('run_id'),
                     'stored_objective_version': meta.get('objective_version'), **result.to_dict()})
        entries.append(entry)
    out.mkdir(parents=True, exist_ok=True)
    fields, csv_rows = catalog._csv_rows({'records': entries})
    with (out / 'catalog.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(csv_rows)
    counts = Counter(r['status'] for r in rows)
    payload = {'tool': 'study_cohort', 'cohort': {'native_config': cfg.name},
               'brief': {'objective_version': cfg.objective_version}, 'rows': rows,
               'selection': {'group': list(key), 'group_count': len(groups),
                             'dependency_pins': {k: v for k, v in selected[0][2].get('lib_shas', {}).items()
                                                 if k in ('hornlab_mesher', 'hornlab_beat_bem', 'hornlab_plots')},
                             'available': len(selected), 'limit': limit, 'excluded': dict(excluded)},
               'counts': dict(counts), 'no_backend_calls': True}
    (out / 'offline_scores.json').write_text(json.dumps(payload, allow_nan=False, indent=2), encoding='utf-8')
    return {'source': {'scores_json': str(out / 'offline_scores.json'),
                       'catalog_csv': str(out / 'catalog.csv'), 'dataset_root': str(dataset)},
            'counts': dict(counts), 'selection': payload['selection']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--limit', type=int, default=256)
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error('--limit must be positive')
    print(json.dumps(prepare(args.config, args.dataset, args.out, limit=args.limit), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
