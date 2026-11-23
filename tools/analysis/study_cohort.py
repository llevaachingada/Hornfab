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

from hornlab_search.bo.encoding import ActiveProjection
from hornlab_search.bo.metric_contracts import MetricTrainingCandidate, SelectionPolicy
from hornlab_search.bo.metric_training import (bounds_identity,
                                                select_metric_training_observations)
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.objective import replay
from hornlab_search.types import Design
# Existing analysis CLIs share their sibling _common module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools.analysis import catalog
from tools.analysis.offline_scores import iter_dataset_rows

_METRIC_OBJECTIVE_VERSIONS = (10, 11)


def _metric_candidates(selected, *, cfg, projection):
    """Encode every compatible group member through ``ActiveProjection`` for metric selection.

    Returns ``(candidates, by_id, exclusions)``. A record whose design cannot be represented is
    published as an exclusion instead of being dropped silently or clipped.
    """
    expected_bounds = bounds_identity(projection)
    candidates, by_id, exclusions = [], {}, []
    for shard, row, meta, entry in selected:
        observation_id = str(entry.get('physical_solve_id')
                             or f'native-s{shard:04d}-r{row:04d}')
        try:
            stored_j = float(meta.get('objective'))
        except (TypeError, ValueError):
            exclusions.append({'observation_id': observation_id,
                               'reasons': ['missing_stored_j'],
                               'source': {'shard': shard, 'row': row}})
            continue
        if not np.isfinite(stored_j):
            exclusions.append({'observation_id': observation_id,
                               'reasons': ['nonfinite_stored_j'],
                               'source': {'shard': shard, 'row': row}})
            continue
        params = meta.get('params')
        family = meta.get('family')
        if not isinstance(params, dict) or not params or not isinstance(family, str) or not family:
            exclusions.append({'observation_id': observation_id,
                               'reasons': ['design_params_missing'],
                               'source': {'shard': shard, 'row': row}})
            continue
        try:
            design = Design(str(family), dict(params))
            # A historical vector must reproduce the recorded design hash; a non-invertible
            # encoding is refused (``encode_refused:HashMismatchError``) rather than trained on.
            x = projection.normalize_design(design, verify_round_trip=True)
        except Exception as exc:  # noqa: BLE001 - an unrepresentable row is refused, never clipped
            exclusions.append({'observation_id': observation_id,
                               'reasons': [f'encode_refused:{type(exc).__name__}'],
                               'detail': str(exc)[:200],
                               'source': {'shard': shard, 'row': row}})
            continue
        candidate = MetricTrainingCandidate(
            observation_id=observation_id,
            x=np.asarray(x, dtype=float).reshape(-1),
            J=stored_j,
            objective_version=int(cfg.objective_version),
            physical_id=str(entry.get('physical_solve_id') or ''),
            solve_id=str(entry.get('solve_hash') or ''),
            design_hash=str(entry.get('design_hash') or ''),
            geometry_hash=str(entry.get('design_hash') or entry.get('geometry_id') or ''),
            brief_hash=str((entry.get('provenance') or {}).get('brief_hash') or ''),
            score_hash=str(entry.get('score_identity') or ''),
            task_identity=str(entry.get('task_identity') or ''),
            backend=str(entry.get('backend') or ''),
            fidelity=str(entry.get('fidelity') or ''),
            grid_hash=str(entry.get('grid_hash') or ''),
            dependency_hash=str(entry.get('dependency_hash') or ''),
            mesh_hash=str(entry.get('mesh_hash') or ''),
            active_keys=tuple(projection.active_keys),
            bounds_hash=expected_bounds,
            status='ok',
            source={'shard': shard, 'row': row},
        )
        candidates.append(candidate)
        by_id[observation_id] = (shard, row, meta, entry)
    return candidates, by_id, exclusions


def _score_identity_of(entry) -> str:
    return str(entry.get('score_identity') or '').strip()


def _score_identity_problem(entry, expected_score_identity, expected_brief_hash):
    """Return ``(reason, detail)`` when stored ``J`` is not an equivalent ranked label."""
    score_id = _score_identity_of(entry)
    brief = str((entry.get('provenance') or {}).get('brief_hash') or '').strip()
    if not score_id:
        return 'score_identity_unavailable', 'catalog score_identity is missing'
    if not brief:
        return 'score_identity_unavailable', 'provenance brief_hash is missing'
    if expected_score_identity is not None and score_id != str(expected_score_identity):
        return ('score_identity_unavailable',
                f'catalog score_identity {score_id!r} != expected {expected_score_identity!r}')
    if expected_brief_hash is not None and brief != str(expected_brief_hash):
        return ('score_identity_unavailable',
                f'provenance brief_hash {brief!r} != expected {expected_brief_hash!r}')
    return None, None


def _identity_exclusion(shard, row, entry, reason, detail) -> dict:
    observation_id = str(entry.get('physical_solve_id')
                         or f'native-s{shard:04d}-r{row:04d}')
    return {'observation_id': observation_id, 'reasons': [reason], 'detail': detail,
            'source': {'shard': shard, 'row': row}}


def prepare(config, dataset, out, *, limit=256, run_ids=None,
            allow_unranked_replay=False, expected_score_identity=None,
            expected_brief_hash=None):
    """``run_ids`` (optional) keeps only records whose catalog run id is listed, so a matched
    comparison can train on exactly one prior run (e.g. never a previous study's own rows).

    ``limit`` is a *training-selection cap* (``n_max``), never a raw-discovery cap: every
    compatible completed observation in the chosen group is considered, encoded through the
    audited ``ActiveProjection``, deduplicated and ranked (64 lowest-J + deterministic maximin)
    before only the selected rows are replayed.

    For v10/v11 a group with zero encodable candidates is a typed refusal
    (``metric_selection_unavailable``) with no rows replayed.  ``allow_unranked_replay=True`` is
    the only way to replay such a group, and the output then records
    ``status="replay_authorized"`` so it can never masquerade as ranked selection.  Non-metric
    (legacy) objective versions keep their historical behaviour exactly.
    """
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
        if run_ids is not None and entry.get('run_id') not in run_ids:
            excluded['other_runs'] += 1
            continue
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

    # Rank/select over the WHOLE compatible group before any positional cap. v10/v11 use the
    # metric-aware selector; other objective identities keep the historical replay path but still
    # consider every compatible record (never ``selected[:limit]``).
    metric_selection = None
    selection_excluded = []
    identity_excluded = []
    selection_meta = {'status': 'not_applicable'}
    try:
        metric_version = int(cfg.objective_version)
    except (TypeError, ValueError):
        metric_version = None
    if metric_version in _METRIC_OBJECTIVE_VERSIONS:
        space = DesignSpace.from_config(cfg)
        no_ops = {'morph_exponent': 4.0} if 'morph_exponent' in space.keys() else {}
        projection = ActiveProjection.from_space(space, no_ops=no_ops)

        # Pre-replay score identity: stored J is only an equivalent *scored label* when every
        # ranked record carries the same non-empty catalog score identity and provenance brief.
        # Ambiguity or a missing/mismatched identity is excluded, never silently ranked.
        distinct_scores = {sid for sid in (_score_identity_of(entry)
                                           for _, _, _, entry in selected) if sid}
        if len(distinct_scores) > 1:
            for shard, row, _meta, entry in selected:
                identity_excluded.append(_identity_exclusion(
                    shard, row, entry, 'score_identity_unavailable',
                    f'compatible group has {len(distinct_scores)} catalog score identities'))
            eligible = []
        else:
            eligible = []
            for record in selected:
                shard, row, _meta, entry = record
                reason, detail = _score_identity_problem(
                    entry, expected_score_identity, expected_brief_hash)
                if reason is not None:
                    identity_excluded.append(
                        _identity_exclusion(shard, row, entry, reason, detail))
                    continue
                eligible.append(record)
        selection_excluded.extend(identity_excluded)

        candidates, by_id, encode_excluded = _metric_candidates(
            eligible, cfg=cfg, projection=projection)
        selection_excluded.extend(encode_excluded)
        if candidates:
            metric_selection = select_metric_training_observations(
                candidates, encoding=projection,
                policy=SelectionPolicy(n_max=int(limit)))
            chosen = [by_id[cid] for cid in metric_selection.selected_ids if cid in by_id]
            selection_meta = metric_selection.to_dict()
            selection_meta['n_records_considered'] = len(selected)
            selection_meta['identity_excluded'] = [dict(item) for item in identity_excluded]
        else:
            # Zero encodable (or zero score-identified) candidates cannot rank stored J.  The
            # default is a typed refusal with no rows replayed; only an explicit
            # ``allow_unranked_replay`` may replay the compatible group, and that is recorded.
            allowed = bool(allow_unranked_replay) and bool(selected)
            chosen = list(selected) if allowed else []
            selection_meta = {
                'status': 'replay_authorized' if allowed else 'refused',
                'reason': 'metric_selection_unavailable',
                'n_records_considered': len(selected),
                'n_encodable': 0,
                'n_identity_excluded': len(identity_excluded),
                'allow_unranked_replay': bool(allow_unranked_replay),
                'basis': ('allow_unranked_replay' if allowed
                          else 'no encodable v10/v11 candidate; stored J is not a ranked label'),
                'n_replayed': len(chosen) if allowed else 0,
                'selected_ids': [
                    str((entry.get('physical_solve_id') or f'native-s{shard:04d}-r{row:04d}'))
                    for shard, row, _meta, entry in chosen],
                'excluded': [dict(item) for item in selection_excluded],
                'identity_excluded': [dict(item) for item in identity_excluded],
                'detail': ('v10/v11 cohort has zero encodable candidates; the default is a typed '
                           'refusal, never an uncapped replay of stored J'),
            }
    else:
        chosen = list(selected)

    rows, entries = [], []
    for shard, row, meta, entry in chosen:
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

    selected_ids = [str((entry.get('physical_solve_id') or f'native-s{shard:04d}-r{row:04d}'))
                    for shard, row, _meta, entry in chosen]
    excluded_details = list(selection_excluded)
    if metric_selection is not None:
        excluded_details.extend(dict(item) for item in metric_selection.excluded)
    # A non-v10/v11 objective has no component schema; the historical replay path keeps every
    # compatible record and there is no metric-selection exclusion to report (selection_meta was
    # initialised to ``not_applicable`` and is only overwritten by the metric branch).

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
                             'available': len(selected), 'limit': limit,
                             'selected_ids': selected_ids,
                             'excluded_ids': sorted({str(item.get('observation_id'))
                                                     for item in excluded_details}),
                             'excluded_reasons': [dict(item) for item in excluded_details],
                             'metric_selection': selection_meta,
                             'excluded': dict(excluded),
                             'run_ids': sorted(run_ids) if run_ids is not None else None},
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
    parser.add_argument('--run-id', action='append', default=None,
                        help='keep only records of this catalog run id (repeatable)')
    parser.add_argument('--allow-unranked-replay', action='store_true',
                        help='explicitly authorise replaying a v10/v11 group with zero encodable '
                             'candidates (recorded as status=replay_authorized)')
    parser.add_argument('--expected-score-identity', default=None,
                        help='require this catalog score identity for every ranked record')
    parser.add_argument('--expected-brief-hash', default=None,
                        help='require this provenance brief_hash for every ranked record')
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error('--limit must be positive')
    print(json.dumps(prepare(args.config, args.dataset, args.out, limit=args.limit,
                             run_ids=set(args.run_id) if args.run_id else None,
                             allow_unranked_replay=bool(args.allow_unranked_replay),
                             expected_score_identity=args.expected_score_identity,
                             expected_brief_hash=args.expected_brief_hash), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
