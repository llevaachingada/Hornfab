"""Offline M2 sensitivity harness; no solver, acquisition policy or data ingestion.

``run_diagnostics`` accepts an independently validated, single-cohort snapshot:
unit-box ``X`` (n,d), finite original-unit ``J`` (n,), unique observation IDs,
connected run/resume/duplicate-geometry group IDs, a cohort ID for *each* row,
and a nonempty validation evidence ID. The caller is responsible for validating
the cohort, physical eligibility and group links; this module cannot prove them.

Injected ``fit(X, J, ids, noise_multiplier)``, ``predict(model, X)`` (original
J units), and ``propose(model, pool_seed)`` functions perform CPU-only model and
pool work. Proposals return mappings with a nonempty ``geometry_hash``. The
noise argument is a multiplier of the frozen 1e-6 variance floor, exclusively
for this diagnostic; it does not alter the production policy. Callback work
must not launch solvers. This module does not read data or write artifacts.
"""
from __future__ import annotations

import hashlib
import json
from typing import Callable

import numpy as np

NOISE_MULTIPLIERS = (0.1, 1.0, 10.0)
PROTOCOL = 'bo-study-v1.1'


def _unavailable(reason: str) -> dict:
    return {'status': 'unavailable', 'reason': reason, 'protocol': PROTOCOL,
            'reason_code': 'capability_missing', 'gate_pass': None, 'results': [],
            'simple_cma_comparison': {'status': 'unmeasured', 'reason': 'independently validated comparable outcomes not provided'}}


def _group_folds(groups: tuple[str, ...], seed: int, count: int) -> list[list[int]]:
    unique = sorted(set(groups), key=lambda group: (
        hashlib.sha256(f'{seed}:{group}'.encode()).hexdigest(), group))
    folds = [[] for _ in range(count)]
    # Largest groups first to limit imbalance; digest order is deterministic for ties.
    order = {g: i for i, g in enumerate(unique)}
    unique.sort(key=lambda group: (-groups.count(group), order[group]))
    for group in unique:
        fold = min(range(count), key=lambda i: (len(folds[i]), i))
        folds[fold].extend(i for i, g in enumerate(groups) if g == group)
    return [sorted(fold) for fold in folds]


def _baseline(X: np.ndarray, J: np.ndarray, ids: tuple[str, ...], cap: int) -> list[int]:
    order = sorted(range(len(ids)), key=lambda i: (J[i], ids[i]))
    if len(order) <= cap:
        return order
    chosen = order[:min(64, cap)]
    remaining = set(order) - set(chosen)
    while remaining and len(chosen) < cap:
        dist = {i: float(np.min(np.linalg.norm(X[chosen] - X[i], axis=1))) for i in remaining}
        best = max(dist.values())
        pick = min((i for i in remaining if dist[i] >= best - 1e-12), key=lambda i: ids[i])
        chosen.append(pick)
        remaining.remove(pick)
    return chosen


def _stratified(J: np.ndarray, ids: tuple[str, ...], cap: int) -> list[int]:
    """Select evenly spaced ranks of training J; ties are resolved by ID."""
    order = sorted(range(len(ids)), key=lambda i: (J[i], ids[i]))
    if len(order) <= cap:
        return order
    ranks = np.linspace(0, len(order) - 1, cap, dtype=int)
    return [order[int(i)] for i in ranks]


def run_diagnostics(*, X=None, J=None, ids=None, groups=None, cohort_ids=None,
                    validation_evidence_id=None, fit: Callable | None = None,
                    predict: Callable | None = None, propose: Callable | None = None,
                    split_seed: int = 0, pool_seeds=(101, 202), folds: int = 5,
                    max_train: int = 256, all_data_limit: int | None = None) -> dict:
    """Return held-out and proposal sensitivity evidence, never an M2 pass verdict.

    Groups identify connected records, not merely geometric similarity estimates.
    Subsets are selected only after each group split, and test rows are never
    passed to fit or proposal callbacks. ``all_data_limit`` declares the largest
    all-training fit considered tractable; None honestly leaves that arm absent.
    """
    if any(v is None for v in (X, J, ids, groups, cohort_ids)) or not validation_evidence_id:
        return _unavailable('validated cohort arrays, identities, groups and validation evidence are required')
    if not all(callable(fn) for fn in (fit, predict, propose)):
        return _unavailable('fit, predict and proposal callbacks are required')
    try:
        x = np.asarray(X, dtype=np.float64)
        y = np.asarray(J, dtype=np.float64).reshape(-1)
        ids = tuple(str(i) if i is not None else '' for i in ids)
        groups = tuple(str(g) if g is not None else '' for g in groups)
        cohort_ids = tuple(str(c) if c is not None else '' for c in cohort_ids)
        seeds = tuple(int(s) for s in pool_seeds)
    except (ValueError, TypeError):
        return _unavailable('invalid inputs')
    if (x.ndim != 2 or not 1 <= x.shape[1] <= 20 or x.shape[0] != len(y)
            or len(ids) != len(y) or len(groups) != len(y) or len(cohort_ids) != len(y)
            or len(set(ids)) != len(ids) or any(not v for v in ids + groups + cohort_ids)
            or len(set(cohort_ids)) != 1 or not np.isfinite(x).all() or not np.isfinite(y).all()
            or np.any((x < 0) | (x > 1))):
        return _unavailable('invalid, mixed, incomplete or out-of-domain cohort')
    if folds != 5 or len(set(groups)) < 5:
        return _unavailable('five group folds and at least five independent connected groups are required')
    if len(seeds) != 2 or seeds[0] == seeds[1]:
        return _unavailable('two distinct prespecified pool seeds are required')
    n_min = max(16, 2 * (x.shape[1] + 1))
    if not isinstance(max_train, int) or max_train < n_min or max_train > 256:
        return _unavailable('invalid subset cap')
    if all_data_limit is not None and (not isinstance(all_data_limit, int) or all_data_limit < n_min):
        return _unavailable('invalid all-data tractability limit')
    group_folds = _group_folds(groups, int(split_seed), folds)
    if any(len(y) - len(test) < n_min for test in group_folds):
        return _unavailable('a group split has insufficient training observations')
    report = {'status': 'partial', 'protocol': PROTOCOL, 'gate_pass': None,
              'cohort_id': cohort_ids[0], 'validation_evidence_id': str(validation_evidence_id),
              'split_seed': int(split_seed), 'pool_seeds': list(seeds),
              'noise_multipliers': list(NOISE_MULTIPLIERS), 'folds': [], 'results': [],
              'simple_cma_comparison': {'status': 'unmeasured', 'reason': 'independently validated comparable outcomes not provided'},
              'limitations': ['caller attests cohort and group validation',
                              'diagnostic noise variations do not modify the production model policy',
                              'offline prediction does not establish optimization speedup',
                              'matching pool-seed geometry IDs is descriptive, not a measure of global pool coverage'],
              'all_data_limit': all_data_limit}
    for fold_no, test in enumerate(group_folds):
        held = set(test)
        train = [i for i in range(len(y)) if i not in held]
        xt, yt = x[train], y[train]
        train_ids = tuple(ids[i] for i in train)
        choices = {'frozen_subset': _baseline(xt, yt, train_ids, max_train),
                   'stratified_subset': _stratified(yt, train_ids, max_train)}
        if all_data_limit is not None and len(train) <= all_data_limit:
            choices['all_training'] = list(range(len(train)))
        report['folds'].append({'fold': fold_no, 'held_out_ids': [ids[i] for i in test],
                                'held_out_groups': sorted({groups[i] for i in test}),
                                'training_ids': list(train_ids), 'n_training': len(train)})
        for name, selected in choices.items():
            subset_ids = tuple(train_ids[i] for i in selected)
            for multiplier in NOISE_MULTIPLIERS:
                result = {'fold': fold_no, 'subset': name, 'train_ids': list(subset_ids),
                          'noise_multiplier': multiplier, 'status': 'unavailable',
                          'held_out_rmse_j': None, 'training_mean_baseline_rmse_j': None,
                          'proposals': []}
                try:
                    model = fit(xt[selected].copy(), yt[selected].copy(), subset_ids, multiplier)
                    if model is None:
                        raise ValueError('fit returned no model')
                    pred = np.asarray(predict(model, x[test].copy()), dtype=float).reshape(-1)
                    if pred.shape != (len(test),) or not np.isfinite(pred).all():
                        raise ValueError('prediction must be finite and match held-out rows')
                    actual = y[test]
                    result['held_out_rmse_j'] = float(np.sqrt(np.mean((pred - actual) ** 2)))
                    result['training_mean_baseline_rmse_j'] = float(np.sqrt(np.mean((yt[selected].mean() - actual) ** 2)))
                    for seed in seeds:
                        item = propose(model, seed)
                        if not isinstance(item, dict) or not isinstance(item.get('geometry_hash'), str) or not item['geometry_hash']:
                            raise ValueError('proposal needs a geometry_hash')
                        result['proposals'].append({'pool_seed': seed, 'geometry_hash': item['geometry_hash']})
                    result['same_proposal_geometry'] = result['proposals'][0]['geometry_hash'] == result['proposals'][1]['geometry_hash']
                    result['status'] = 'ok'
                except Exception as exc:  # callbacks are isolated failures, not inferred results
                    result['reason'] = f'{type(exc).__name__}: {exc}'
                report['results'].append(result)
    if all_data_limit is None or any(len(f['training_ids']) > all_data_limit for f in report['folds']):
        report['limitations'].append('all-training comparison unavailable or exceeds the declared tractability limit')
    if all(r['status'] == 'ok' for r in report['results']) and len(report['limitations']) == 4:
        report['status'] = 'complete_diagnostics'
    # Guard against accidental NaN serialization; all results must remain portable JSON.
    json.dumps(report, allow_nan=False)
    return report
