"""Offline M2 sensitivity harness; no solver, acquisition policy or data ingestion.

Two entry points:

* :func:`run_diagnostics` - the original injected-callback, group-held-out harness.  It refuses
  honestly when independent connected groups or validated cohort evidence are absent.
* :func:`load_native_training_set` / :func:`run_real_diagnostics` - the documented real-data
  entry point.  It reads the committed native ``TrainingSet`` artifact, verifies its input hashes,
  and runs the bo-study-v1.1 M2 subset/noise/pool diagnostics.  The committed native artifact has
  **no independent run/resume group links**, so the real-data path is explicitly descriptive
  (in-sample) and does not invent groups.  The CLI (``python -m tools.analysis.bo_sensitivity``)
  also exposes ``generate-pools``/``select``/``publish`` for the immutable M2 proposal.

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
must not launch solvers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Callable

import numpy as np

NOISE_MULTIPLIERS = (0.1, 1.0, 10.0)
PROTOCOL = 'bo-study-v1.1'
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRAINING_JSON = (REPO_ROOT / 'docs' / 'evidence' / 'bo_study_2026-11-12'
                         / 'b2_native' / 'native_trainingset.json')
DEFAULT_POOL_MANIFEST = (REPO_ROOT / 'docs' / 'evidence' / 'bo_study_2026-11-12'
                         / 'b2' / 'pool_manifest.json')
DEFAULT_CONFIG = (REPO_ROOT / 'examples' / 'typologies' / 'campaign_2026-10-26_v4'
                  / 'native__ath_core_v4.yaml')
DEFAULT_OUT_DIR = (REPO_ROOT / 'docs' / 'evidence' / 'bo_study_2026-11-12' / 'm2')
NATIVE_CONFIG_NAME = 'native__ath_core_v4.yaml'
EXPECTED_PROJECTION = 'active-projection-v1'
DIAGNOSTIC_CAPS = (64, 128)
PRODUCTION_POOL_SEED = 20261112
DEFAULT_POOL_SEEDS = (PRODUCTION_POOL_SEED, 20261113)
POOL_STATUS_NOTE = 'cheap-check-passed; mesh/acoustic eligibility unknown'


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


# --------------------------------------------------------------------------- real-data support


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_array(array) -> str:
    return _sha256_bytes(np.ascontiguousarray(np.asarray(array)).tobytes())


def _sha256_ids(ids) -> str:
    blob = json.dumps([str(i) for i in ids], separators=(',', ':')).encode()
    return _sha256_bytes(blob)


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, Path):
        return str(value)
    return value


def _write_json(path, payload) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True,
                               allow_nan=False) + '\n', encoding='utf-8')


def _write_text(path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def _artifact_unavailable(reason: str, *, provenance=None, limitations=(),
                          reason_code: str = 'invalid_input') -> dict:
    return {
        'tool': 'bo_sensitivity',
        'schema_version': 2,
        'protocol': PROTOCOL,
        'generated_utc': _utc_now(),
        'status': 'unavailable',
        'reason': reason,
        'reason_code': reason_code,
        'gate_pass': None,
        'training': None,
        'provenance': provenance or {},
        'input': provenance or {},
        'limitations': list(limitations),
        'subsets': [],
        'fits': [],
        'proposals': [],
        'simple_cma_comparison': {
            'status': 'unmeasured',
            'reason': 'independently validated comparable outcomes not provided',
        },
    }


def load_native_training_set(json_path=None, npz_path=None, *, config_path=None,
                             require_projection: str = EXPECTED_PROJECTION) -> dict:
    """Load and verify the committed native ``TrainingSet`` artifact (no engine import).

    Checks the declared shape, the unit box, ``Y == -J``, the frozen config/projection
    identity, a single stored objective version, the declared unique-design count, and the
    committed ``hashes`` block.  Missing or mixed identities are refused explicitly; nothing
    is invented.
    """
    from hornlab_search.bo.data import TrainingSet

    json_path = Path(json_path) if json_path is not None else DEFAULT_TRAINING_JSON
    npz_path = Path(npz_path) if npz_path is not None else json_path.with_suffix('.npz')
    if not json_path.is_file():
        return _artifact_unavailable(f'training artifact not found: {json_path}')
    if not npz_path.is_file():
        return _artifact_unavailable(f'training arrays not found: {npz_path}')
    try:
        payload = json.loads(json_path.read_text(encoding='utf-8'))
        with np.load(npz_path, allow_pickle=False) as arrays:
            X = np.asarray(arrays['X'], dtype=np.float64)
            J = np.asarray(arrays['J'], dtype=np.float64).reshape(-1)
            Y = np.asarray(arrays['Y'], dtype=np.float64).reshape(-1)
            Y_phys = (np.asarray(arrays['Y_phys'], dtype=np.float64).reshape(-1)
                      if 'Y_phys' in arrays.files else None)
            ids = tuple(str(i) for i in arrays['ids'].tolist())
    except Exception as exc:  # noqa: BLE001 - an unreadable artifact is a refusal, not a crash
        return _artifact_unavailable(
            f'training artifact could not be read: {type(exc).__name__}: {exc}')

    provenance = {
        'json_path': str(json_path),
        'npz_path': str(npz_path),
        'json_sha256': _sha256_file(json_path),
        'npz_sha256': _sha256_file(npz_path),
    }
    try:
        d = int(payload['d'])
        n = int(payload['n'])
        active_keys = tuple(str(k) for k in payload['active_keys'])
        projection_version = str(payload.get('projection_version') or '')
    except (KeyError, TypeError, ValueError) as exc:
        return _artifact_unavailable(
            f'training artifact metadata is incomplete: {exc}', provenance=provenance)

    if payload.get('status') != 'ok':
        return _artifact_unavailable(
            f"training artifact status is {payload.get('status')!r}", provenance=provenance)
    if X.ndim != 2 or X.shape[1] != d or X.shape[0] != n:
        return _artifact_unavailable(
            f'X shape {X.shape} does not match d={d}, n={n}', provenance=provenance)
    if not (len(J) == len(Y) == len(ids) == n):
        return _artifact_unavailable('array lengths disagree with n', provenance=provenance)
    if active_keys and len(active_keys) != d:
        return _artifact_unavailable('active_keys length disagrees with d',
                                     provenance=provenance)
    if len(set(ids)) != len(ids):
        return _artifact_unavailable('duplicate observation IDs', provenance=provenance)
    if not (np.all(np.isfinite(X)) and np.all(np.isfinite(J)) and np.all(np.isfinite(Y))
            and (Y_phys is None or np.all(np.isfinite(Y_phys)))):
        return _artifact_unavailable('X/J/Y contains NaN or Inf', provenance=provenance)
    if np.any((X < 0.0) | (X > 1.0)):
        return _artifact_unavailable('X leaves the normalized unit box', provenance=provenance)
    if not np.array_equal(Y, -J):
        return _artifact_unavailable('Y is not exactly -J', provenance=provenance)
    if projection_version != require_projection:
        return _artifact_unavailable(
            f'projection {projection_version!r} != {require_projection!r}',
            provenance=provenance)

    artifact_config = str(payload.get('config') or '')
    artifact_config_name = PureWindowsPath(artifact_config).name if artifact_config else ''
    if artifact_config_name != NATIVE_CONFIG_NAME:
        return _artifact_unavailable(
            f'cohort config {artifact_config_name!r} is not the frozen '
            f'{NATIVE_CONFIG_NAME!r}', provenance=provenance)
    if config_path is not None and PureWindowsPath(str(config_path)).name != NATIVE_CONFIG_NAME:
        return _artifact_unavailable(
            f'requested config {PureWindowsPath(str(config_path)).name!r} is not the frozen '
            f'{NATIVE_CONFIG_NAME!r}', provenance=provenance)

    expected = dict(payload.get('hashes') or {})
    recomputed = {
        'x_sha256': _sha256_array(X),
        'j_sha256': _sha256_array(J),
        'y_sha256': _sha256_array(Y),
        'y_phys_sha256': None if Y_phys is None else _sha256_array(Y_phys),
        'ids_sha256': _sha256_ids(ids),
    }
    comparisons = {}
    for key, value in recomputed.items():
        if key in expected and expected[key] is not None:
            comparisons[key] = bool(value == expected[key])
        else:
            comparisons[key] = None
    if any(value is False for value in comparisons.values()):
        return _artifact_unavailable('artifact array hash mismatch', provenance=provenance)
    hashes_verified = any(value is True for value in comparisons.values())

    limitations: list[str] = []
    identities = payload.get('identities') or {}
    objective_versions = sorted({int(v['stored_objective_version'])
                                 for v in identities.values()
                                 if isinstance(v, dict)
                                 and v.get('stored_objective_version') is not None})
    if len(objective_versions) > 1:
        return _artifact_unavailable(
            f'mixed objective versions in the artifact: {objective_versions}',
            provenance=provenance)
    design_hashes = {str(v['design_hash']) for v in identities.values()
                     if isinstance(v, dict) and v.get('design_hash')}
    declared_unique = payload.get('n_unique_design_hashes')
    if (design_hashes and declared_unique is not None
            and len(design_hashes) != int(declared_unique)):
        return _artifact_unavailable(
            f'declared unique design hashes {declared_unique} != recomputed '
            f'{len(design_hashes)}', provenance=provenance)

    solve_groups: dict[str, list[str]] = {}
    for observation_id, record in identities.items():
        if isinstance(record, dict) and record.get('solve_hash') is not None:
            solve_groups.setdefault(str(record['solve_hash']), []).append(
                str(observation_id))
    majority_group = None
    if solve_groups:
        majority_hash = sorted(solve_groups,
                               key=lambda value: (-len(solve_groups[value]), value))[0]
        majority_group = {
            'solve_hash': majority_hash,
            'n': len(solve_groups[majority_hash]),
            'ids': sorted(solve_groups[majority_hash]),
        }
        if len(solve_groups) > 1:
            limitations.append(
                'the frozen artifact mixes solve hashes '
                f'({ {h: len(v) for h, v in solve_groups.items()} }); the freeze records '
                '192 screen + 5 verify rows, so this is a mixed-fidelity advisory fit, '
                'not a strict single-fidelity GP')
    group_fields = sorted({key for record in identities.values() if isinstance(record, dict)
                           for key in ('run_id', 'run', 'group_id', 'experiment_id')
                           if record.get(key) is not None})
    groups_available = bool(group_fields)
    if not groups_available:
        limitations.append(
            'the committed native artifact has no independent run/resume group identity; '
            'real-data diagnostics are descriptive (in-sample) and do not invent groups')

    selected_ids = tuple(str(i) for i in (payload.get('selected_ids') or ids))
    excluded_ids = tuple(str(i) for i in (payload.get('excluded_ids') or ()))
    elite_ids = tuple(str(i) for i in (payload.get('elite_ids') or selected_ids))
    maximin_ids = tuple(str(i) for i in (payload.get('maximin_ids') or ()))
    known_ids = set(ids)
    if not set(selected_ids) <= known_ids or not set(excluded_ids) <= known_ids:
        return _artifact_unavailable('selected/excluded IDs are not a subset of ids',
                                     provenance=provenance)
    if set(selected_ids) & set(excluded_ids):
        return _artifact_unavailable('selected and excluded IDs overlap',
                                     provenance=provenance)
    objective = objective_versions[0] if objective_versions else None
    cohort_id = f'{NATIVE_CONFIG_NAME}|{projection_version}|objective_v{objective}'
    provenance.update({
        'n': n,
        'd': d,
        'n_eligible': int(payload.get('n_eligible', n)),
        'n_unique': int(payload.get('n_unique', n)),
        'n_unique_design_hashes': (int(declared_unique) if declared_unique is not None
                                   else len(design_hashes)),
        'n_refused': len(payload.get('refused') or []),
        'refusals': list(payload.get('refused') or []),
        'refusal_reasons': dict(payload.get('refusal_reasons') or {}),
        'active_keys': list(active_keys),
        'projection_version': projection_version,
        'config': artifact_config,
        'config_name': artifact_config_name,
        'selected_ids': list(selected_ids),
        'excluded_ids': list(excluded_ids),
        'elite_ids': list(elite_ids),
        'maximin_ids': list(maximin_ids),
        'objective_versions': objective_versions,
        'identity_count': len(identities),
        'solve_hash_groups': {value: len(group) for value, group
                              in sorted(solve_groups.items())},
        'majority_solve_group': majority_group,
        'group_fields_present': group_fields,
        'independent_groups_available': groups_available,
        'independent_groups_reason': (
            'no run/resume/experiment group field in the frozen artifact'
            if not groups_available else 'group fields present'),
        'cohort_id': cohort_id,
        'subset_policy': dict(payload.get('subset_policy') or {}),
        'artifact_hashes': expected,
        'recomputed_hashes': recomputed,
        'hash_comparisons': comparisons,
        'hashes_verified': hashes_verified,
    })
    provenance['training_set_id'] = _sha256_bytes(json.dumps({
        'x': recomputed['x_sha256'],
        'j': recomputed['j_sha256'],
        'y': recomputed['y_sha256'],
        'ids': recomputed['ids_sha256'],
        'projection': projection_version,
        'active_keys': list(active_keys),
        'config': artifact_config_name,
        'objective_versions': objective_versions,
    }, sort_keys=True, separators=(',', ':')).encode())

    training = TrainingSet(
        status='ok', d=d, n=n, X=X,
        J=J.reshape(-1, 1), Y=Y.reshape(-1, 1),
        Y_phys=(None if Y_phys is None else Y_phys.reshape(-1, 1)), G=None,
        ids=ids, selected_ids=selected_ids, excluded_ids=excluded_ids,
        elite_ids=elite_ids, maximin_ids=maximin_ids,
        n_eligible=int(provenance['n_eligible']),
        n_unique=int(provenance['n_unique']),
        n_min=int(payload.get('n_min', max(16, 2 * (d + 1)))),
        n_max=int(payload.get('n_max', 256)),
        active_keys=active_keys, projection_version=projection_version,
        preparation=None,
        meta={'artifact': str(json_path), 'artifact_sha256': provenance['json_sha256']},
    )
    return {
        'status': 'ok',
        'reason': 'ok',
        'training': training,
        'provenance': provenance,
        'limitations': limitations,
    }


def _training_set_from_arrays(base_training_set, X, J, ids):
    """Build a subset :class:`TrainingSet` for the group-held-out callback path."""
    X = np.asarray(X, dtype=np.float64)
    J = np.asarray(J, dtype=np.float64).reshape(-1)
    ids = tuple(str(i) for i in ids)
    J2 = J.reshape(-1, 1)
    return replace(
        base_training_set, n=len(ids), X=X, J=J2, Y=-J2, Y_phys=None, ids=ids,
        selected_ids=ids, excluded_ids=(), elite_ids=ids, maximin_ids=(),
        n_eligible=len(ids), n_unique=len(ids))


def _subset_training_set(training_set, indices):
    idx = np.asarray(indices, dtype=int)
    ids = tuple(training_set.ids[i] for i in idx)
    selected = set(ids)
    return replace(
        training_set, n=len(ids),
        X=np.array(training_set.X[idx], copy=True),
        J=np.array(training_set.J[idx], copy=True),
        Y=np.array(training_set.Y[idx], copy=True),
        Y_phys=(None if training_set.Y_phys is None
                else np.array(training_set.Y_phys[idx], copy=True)),
        ids=ids, selected_ids=ids,
        excluded_ids=tuple(i for i in training_set.ids if i not in selected),
        elite_ids=ids, maximin_ids=(), n_eligible=len(ids), n_unique=len(ids))


def _fit_with_noise_multiplier(training_set, multiplier, *, seed: int = 0):
    """Fit the locked model with a diagnostic scaling of the fixed variance floor.

    The production policy is ``train_Yvar = 1e-6 * s2``.  M2 asks for diagnostics at
    ``0.1/1/10`` times that floor.  The engine's public ``fit_model`` intentionally has no
    noise argument, so this helper scales the module's declared constant for the duration of
    the call only and restores it in ``finally``.  Multiplier ``1.0`` is the production policy;
    no multiplier is used to choose an optimum.
    """
    from hornlab_search.bo import model as model_mod

    base = float(model_mod.NOISE_FLOOR_MULTIPLIER)
    scaling = float(multiplier)
    if not np.isfinite(scaling) or scaling <= 0.0:
        raise ValueError(f'noise multiplier must be positive and finite, got {multiplier!r}')
    try:
        model_mod.NOISE_FLOOR_MULTIPLIER = base * scaling
        return model_mod.fit_model(training_set, seed=int(seed))
    finally:
        model_mod.NOISE_FLOOR_MULTIPLIER = base


def _real_predict(model_result, X):
    from hornlab_search.bo.model import predict_j

    result = predict_j(model_result, X)
    if result.status != 'ok' or result.j_mean is None:
        raise RuntimeError(f'prediction unavailable: {result.reason}: {result.detail}')
    return np.asarray(result.j_mean, dtype=float), result


def real_propose_from_pools(pools: dict):
    """Return a ``propose(model, pool_seed)`` callback backed by real candidate pools.

    This uses the locked selection half of ``propose_one`` (acquisition/maximin and posterior
    prediction).  The publication half (``validate_selected_candidate``) is intentionally run
    later in the project venv, which owns the mesher; the policy itself is unchanged.
    """
    from hornlab_search.bo.propose import ProposalHistory, _propose_one

    def propose(model_result, pool_seed):
        pool = pools.get(int(pool_seed))
        if pool is None:
            raise KeyError(f'no candidate pool for seed {pool_seed}')
        result = _propose_one(model_result, pool,
                              history=ProposalHistory(proposal_index=0))
        if not result.geometry_hash:
            raise RuntimeError(
                f'proposal unavailable: {result.reason}: {result.detail}')
        return {
            'status': result.status,
            'reason': result.reason,
            'candidate_id': result.candidate_id,
            'geometry_hash': result.geometry_hash,
            'selection_reason': result.selection_reason,
            'predicted': result.predicted,
            'acquisition': result.acquisition,
            'counts': result.counts,
            'next_proposal_index': result.next_proposal_index,
        }

    return propose


def _encoding_identity(encoding) -> dict:
    return {
        'version': getattr(encoding, 'version', None),
        'd': int(encoding.d),
        'active_keys': list(encoding.active_keys),
        'full_keys': list(encoding.full_keys),
        'fixed_values': dict(encoding.fixed_values),
        'key_order': 'alphabetical space.keys()',
    }


def _config_identity(config_path) -> dict:
    path = Path(config_path)
    brief_file = None
    try:
        import yaml
        raw = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        brief_file = raw.get('brief_file')
    except Exception:  # noqa: BLE001 - the brief reference is descriptive only
        brief_file = None
    return {
        'path': str(path),
        'name': path.name,
        'brief_file': brief_file,
        'objective_version': 4,
        'protocol': PROTOCOL,
    }


def save_candidate_pool(path, pool, *, config_path=None, encoding=None) -> dict:
    """Persist a full candidate pool (vectors included) for the cross-venv proposal leg."""
    from hornlab_search.bo.model import library_versions

    payload = {
        'tool': 'bo_candidate_pool',
        'schema_version': 1,
        'protocol': PROTOCOL,
        'generated_utc': _utc_now(),
        'config': {
            'path': str(config_path) if config_path else None,
            'name': Path(config_path).name if config_path else None,
        },
        'encoding': (None if encoding is None else _encoding_identity(encoding)),
        'summary': pool.summary(),
        'candidates': pool.candidates_json(include_vectors=True),
        'library_versions': library_versions(),
    }
    _write_json(path, payload)
    return payload


def load_candidate_pool(path):
    """Load a serialized candidate pool back into the B2/B3 dataclasses."""
    from hornlab_search.bo.data import CandidatePool, PoolCandidate

    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    candidates = []
    for record in payload.get('candidates') or ():
        candidates.append(PoolCandidate(
            candidate_id=str(record['candidate_id']),
            pool_index=int(record['pool_index']),
            seed=int(record['seed']),
            active_vector=np.asarray(record['active_vector'], dtype=float),
            full_vector=np.asarray(record['full_vector'], dtype=float),
            design_hash=str(record['design_hash']),
            geometry_hash=str(record['geometry_hash']),
            intended_solve_hash=str(record['intended_solve_hash']),
            params=dict(record.get('params') or {}),
            descriptors=dict(record.get('descriptors') or {}),
            checks=dict(record.get('checks') or {}),
            status=str(record.get('status') or POOL_STATUS_NOTE),
        ))
    summary = dict(payload.get('summary') or {})
    return CandidatePool(
        status=str(summary.get('status') or 'ok'),
        requested=int(summary.get('requested') or len(candidates)),
        seed=summary.get('seed'),
        seeds_tried=tuple(int(s) for s in (summary.get('seeds_tried') or ())),
        candidates=tuple(candidates),
        counts=dict(summary.get('counts') or {}),
        seed_reports=tuple(summary.get('seed_reports') or ()),
        intended_solve_hash=summary.get('intended_solve_hash'),
        note=str(summary.get('note') or summary.get('status_note') or POOL_STATUS_NOTE),
    )


def _subset_definitions(training_set, provenance, caps) -> list[dict]:
    ids = list(training_set.ids)
    position = {observation_id: index for index, observation_id in enumerate(ids)}
    J = np.asarray(training_set.J, dtype=float).reshape(-1)
    X = np.asarray(training_set.X, dtype=float)
    definitions: list[dict] = []
    selected = [position[i] for i in training_set.selected_ids if i in position]
    definitions.append({
        'name': 'frozen_subset',
        'indices': selected,
        'rule': 'training artifact selected_ids (production subset)',
        'production_recipe': True,
        'diagnostic_only': False,
    })
    definitions.append({
        'name': 'all_eligible',
        'indices': list(range(len(ids))),
        'rule': 'all eligible rows in the frozen artifact',
        'production_recipe': False,
        'diagnostic_only': True,
    })
    for cap in caps:
        cap = int(cap)
        if cap < 1 or cap >= len(ids):
            continue
        definitions.append({
            'name': f'stratified_by_J_cap{cap}',
            'indices': _stratified(J, training_set.ids, cap),
            'rule': f'evenly spaced J ranks, diagnostic cap {cap}',
            'production_recipe': False,
            'diagnostic_only': True,
        })
        definitions.append({
            'name': f'lowJ_plus_maximin_cap{cap}',
            'indices': _baseline(X, J, training_set.ids, cap),
            'rule': f'production subset rule at diagnostic cap {cap} '
                    '(64 lowest-J + deterministic maximin)',
            'production_recipe': False,
            'diagnostic_only': True,
        })
    majority = (provenance or {}).get('majority_solve_group')
    if majority and majority.get('ids'):
        indices = [position[i] for i in majority['ids'] if i in position]
        if 0 < len(indices) < len(ids):
            definitions.append({
                'name': f"majority_solve_group_{len(indices)}",
                'indices': indices,
                'rule': 'majority solve-hash group (the freeze records this as the screen group)',
                'production_recipe': False,
                'diagnostic_only': True,
                'note': 'mixed-fidelity sensitivity arm; not a single-fidelity model',
            })
    return definitions


def _subset_report(training_set, definitions) -> list[dict]:
    report = []
    for definition in definitions:
        retained = [training_set.ids[i] for i in definition['indices']]
        retained_set = set(retained)
        report.append({
            'name': definition['name'],
            'n': len(retained),
            'rule': definition['rule'],
            'production_recipe': definition['production_recipe'],
            'diagnostic_only': definition['diagnostic_only'],
            'retained_ids': retained,
            'excluded_ids': [i for i in training_set.ids if i not in retained_set],
            'note': definition.get('note'),
        })
    return report


def _space_filling_reference(pools: dict, training_X) -> list[dict]:
    """Deterministic maximin reference from the same frozen pools (no model, no solve)."""
    from hornlab_search.bo.data import is_near_duplicate
    from hornlab_search.bo.propose import _maximin_pick

    out: list[dict] = []
    if training_X is None:
        return out
    reference = [np.asarray(row, dtype=float)
                 for row in np.asarray(training_X, dtype=float)]
    for seed, pool in sorted(pools.items()):
        legal = []
        for candidate in pool.candidates:
            vector = np.asarray(candidate.active_vector, dtype=float)
            if not np.all(np.isfinite(vector)):
                continue
            if reference and is_near_duplicate(vector, reference, tol=1e-6):
                continue
            legal.append((candidate, vector))
        if not legal:
            out.append({'pool_seed': int(seed), 'status': 'pool_exhausted'})
            continue
        candidate, _vector, distance = _maximin_pick(legal, reference)
        out.append({
            'pool_seed': int(seed),
            'status': 'ok',
            'candidate_id': candidate.candidate_id,
            'geometry_hash': candidate.geometry_hash,
            'distance_l2': float(distance),
            'note': ('space-filling maximin reference from the same frozen pool; '
                     'not a BO acquisition pick'),
        })
    return out


def _run_group_diagnostics(*, training_set, provenance, groups, cohort_ids,
                           validation_evidence_id, fit, predict, propose, pool_seeds,
                           split_seed, max_train) -> dict:
    def fit_callback(X, J, ids, noise_multiplier):
        subset = _training_set_from_arrays(training_set, X, J, ids)
        if fit is not None:
            return fit(subset, noise_multiplier)
        return _fit_with_noise_multiplier(subset, noise_multiplier)

    def predict_callback(model_result, X):
        raw = (predict(model_result, X) if predict is not None
               else _real_predict(model_result, X))
        if isinstance(raw, tuple):
            raw = raw[0]
        values = np.asarray(raw, dtype=float).reshape(-1)
        if values.shape != (len(X),) or not np.all(np.isfinite(values)):
            raise ValueError('prediction must be finite and match the held-out rows')
        return values

    def propose_callback(model_result, seed):
        if propose is None:
            raise RuntimeError('no proposal callback')
        return propose(model_result, seed)

    all_data_limit = len(training_set.ids) if len(training_set.ids) <= max_train else None
    report = run_diagnostics(
        X=training_set.X, J=np.asarray(training_set.J).reshape(-1), ids=training_set.ids,
        groups=groups, cohort_ids=cohort_ids,
        validation_evidence_id=validation_evidence_id,
        fit=fit_callback, predict=predict_callback, propose=propose_callback,
        split_seed=split_seed, pool_seeds=pool_seeds, folds=5, max_train=max_train,
        all_data_limit=all_data_limit,
    )
    report['tool'] = 'bo_sensitivity'
    report['schema_version'] = 2
    report['generated_utc'] = _utc_now()
    report['validation_mode'] = 'group_held_out'
    report['input'] = provenance
    report['cohort'] = {
        'cohort_id': cohort_ids[0],
        'n': len(training_set.ids),
        'n_groups': len(set(groups)),
        'independent_groups_available': True,
        'independent_groups_reason': 'caller-supplied connected group links',
        'objective_versions': provenance.get('objective_versions', []),
    }
    report['limitations'] = list(report.get('limitations') or []) + [
        'off-policy retrospective diagnostics; no closed-loop speedup or acoustic-benefit claim',
        'noise multipliers are diagnostic only and never used to choose a new optimum',
        'candidate proposals are cheap-check-passed; mesh/acoustic eligibility unknown',
    ]
    return report


def run_real_diagnostics(*, training_set=None, provenance=None, X=None, J=None, ids=None,
                         groups=None, cohort_ids=None, validation_evidence_id=None,
                         fit=None, predict=None, propose=None, pools=None,
                         pool_seeds=DEFAULT_POOL_SEEDS,
                         noise_multipliers=NOISE_MULTIPLIERS,
                         diagnostic_caps=DIAGNOSTIC_CAPS,
                         proposal_noise_multiplier: float = 1.0,
                         require_groups: bool = False, split_seed: int = 0,
                         max_train: int = 256, extra_subsets=None) -> dict:
    """Run the bo-study-v1.1 M2 diagnostics on a real ``TrainingSet``.

    With independent group links the strict group-held-out harness is used.  Without them the
    report is explicitly descriptive: subsets are fit on the full artifact and predictions are
    in-sample.  No groups are invented and ``gate_pass`` is always ``None``.
    """
    if training_set is None:
        if X is None or J is None or ids is None:
            return _artifact_unavailable('training_set or X/J/ids are required')
        from hornlab_search.bo.data import TrainingSet
        X_arr = np.asarray(X, dtype=np.float64)
        J_arr = np.asarray(J, dtype=np.float64).reshape(-1)
        id_tuple = tuple(str(i) for i in ids)
        d = int(X_arr.shape[1])
        training_set = TrainingSet(
            status='ok', d=d, n=len(id_tuple), X=X_arr, J=J_arr.reshape(-1, 1),
            Y=-J_arr.reshape(-1, 1), Y_phys=None, G=None, ids=id_tuple,
            selected_ids=id_tuple, excluded_ids=(), elite_ids=id_tuple, maximin_ids=(),
            n_eligible=len(id_tuple), n_unique=len(id_tuple),
            n_min=max(16, 2 * (d + 1)), n_max=int(max_train), active_keys=(),
            projection_version=None, preparation=None)
    n = int(training_set.n)
    d = int(training_set.d)
    if training_set.X is None or training_set.J is None:
        return _artifact_unavailable('training set has no X/J arrays')
    if (np.asarray(training_set.X).shape != (n, d)
            or not np.all(np.isfinite(training_set.X))
            or not np.all(np.isfinite(training_set.J))):
        return _artifact_unavailable('training arrays are malformed or nonfinite')

    if provenance is None:
        provenance = {
            'n': n,
            'd': d,
            'n_eligible': int(getattr(training_set, 'n_eligible', n)),
            'n_unique': int(getattr(training_set, 'n_unique', n)),
            'selected_ids': list(training_set.selected_ids),
            'excluded_ids': list(training_set.excluded_ids),
            'active_keys': list(getattr(training_set, 'active_keys', ()) or ()),
            'projection_version': getattr(training_set, 'projection_version', None),
            'objective_versions': [],
            'solve_hash_groups': {},
            'independent_groups_available': False,
            'independent_groups_reason': 'no independent group identity supplied',
            'cohort_id': 'synthetic|unspecified',
            'hashes_verified': False,
            'input_hashes': {},
        }
    provenance = dict(provenance)

    if cohort_ids is not None:
        cohort_tuple = tuple(str(c) for c in cohort_ids)
        if len(cohort_tuple) != n or any(not c for c in cohort_tuple):
            return _artifact_unavailable(
                'cohort_ids must be nonempty and match the rows', provenance=provenance)
        if len(set(cohort_tuple)) != 1:
            return _artifact_unavailable(
                'mixed cohorts are not comparable; a single score/task identity is required',
                provenance=provenance, reason_code='capability_missing')
        cohort_id = cohort_tuple[0]
    else:
        cohort_id = provenance.get('cohort_id')

    if groups is not None:
        group_tuple = tuple(str(g) if g is not None else '' for g in groups)
        if len(group_tuple) != n or any(not g for g in group_tuple):
            return _artifact_unavailable(
                'groups must be nonempty and match the rows', provenance=provenance)
    else:
        group_tuple = None

    seeds = tuple(int(s) for s in pool_seeds)
    if len(seeds) != 2 or seeds[0] == seeds[1]:
        return _artifact_unavailable(
            'two distinct prespecified pool seeds are required', provenance=provenance)
    multipliers = tuple(float(m) for m in noise_multipliers)
    if not multipliers or any(not np.isfinite(m) or m <= 0.0 for m in multipliers):
        return _artifact_unavailable('noise multipliers must be positive and finite',
                                     provenance=provenance)
    caps = tuple(int(c) for c in diagnostic_caps)
    if propose is None and pools:
        propose = real_propose_from_pools(pools)

    if require_groups:
        if group_tuple is None:
            return _artifact_unavailable(
                'independent connected group links are unavailable; refusing to fabricate a '
                'group-held-out validation', provenance=provenance,
                reason_code='capability_missing',
                limitations=['the committed native artifact has no run/resume group identity'])
        if len(set(group_tuple)) < 5:
            return _artifact_unavailable(
                f'at least five independent connected groups are required, got '
                f'{len(set(group_tuple))}', provenance=provenance,
                reason_code='capability_missing')
        if not validation_evidence_id:
            return _artifact_unavailable(
                'a nonempty validation evidence ID is required', provenance=provenance,
                reason_code='capability_missing')
        return _run_group_diagnostics(
            training_set=training_set, provenance=provenance, groups=group_tuple,
            cohort_ids=(cohort_id,) * n, validation_evidence_id=validation_evidence_id,
            fit=fit, predict=predict, propose=propose, pool_seeds=seeds,
            split_seed=split_seed, max_train=max_train)

    definitions = _subset_definitions(training_set, provenance, caps)
    if extra_subsets:
        definitions.extend(extra_subsets)
    subset_reports = _subset_report(training_set, definitions)

    engine_versions = None
    try:
        from hornlab_search.bo.model import library_versions
        engine_versions = library_versions()
    except Exception as exc:  # noqa: BLE001 - absence is reported, not hidden
        engine_versions = {'engine': 'botorch', 'available': False,
                           'import_error': f'{type(exc).__name__}: {exc}'}

    limitations = [
        'descriptive in-sample diagnostics only; no independent-group held-out estimate and '
        'no gate pass',
        'the committed native artifact has no independent run/resume group identity; groups '
        'were not invented',
        'noise multipliers 0.1/1/10 are diagnostics of the fixed regularization floor, not '
        'measured solver noise and not a new policy',
        'proposals are off-policy retrospective suggestions; matching pool-seed geometry IDs '
        'are descriptive, not global pool coverage',
        'candidate pool entries are cheap-check-passed; mesh/acoustic eligibility unknown',
        'predictions are model outputs and are never appended as measured rows',
        'J is objective v4 only; no cross-objective-version ranking',
        'no closed-loop optimization speedup, acoustic benefit, adoption or manufacturing '
        'claim is made',
    ]
    if provenance.get('solve_hash_groups') and len(provenance['solve_hash_groups']) > 1:
        limitations.append(
            'mixed solve-hash groups are present; this is a mixed-fidelity advisory fit')
    limitations.extend(provenance.get('limitations') or [])

    report = {
        'tool': 'bo_sensitivity',
        'schema_version': 2,
        'protocol': PROTOCOL,
        'generated_utc': _utc_now(),
        'status': 'partial',
        'reason_code': None,
        'gate_pass': None,
        'validation_mode': 'descriptive_no_independent_groups',
        'input': provenance,
        'cohort': {
            'cohort_id': cohort_id,
            'n': n,
            'n_eligible': provenance.get('n_eligible', n),
            'n_unique': provenance.get('n_unique', n),
            'fidelity': provenance.get('solve_hash_groups', {}),
            'objective_versions': provenance.get('objective_versions', []),
            'independent_groups_available': bool(
                provenance.get('independent_groups_available', False)),
            'independent_groups_reason': provenance.get('independent_groups_reason'),
            'cohort_ids_checked': cohort_ids is not None,
        },
        'method': {
            'fit': 'locked scalar_pool_v1 fit_model; train_Yvar = noise_multiplier * 1e-6 * s2',
            'predict': 'predict_j (predicted J = -posterior mean(Y); reversed interval)',
            'proposal': 'locked scalar_pool_v1 selection; every-fourth maximin cadence',
            'noise_multipliers': [float(m) for m in multipliers],
            'noise_multiplier_use': 'diagnostic only; never used to pick a new optimum',
            'proposal_noise_multiplier': float(proposal_noise_multiplier),
            'pool_seeds': [int(s) for s in seeds],
            'diagnostic_caps': [int(c) for c in caps],
            'validation': 'descriptive in-sample prediction; independent-group folds are '
                          'not available',
            'n_pools': len(pools or {}),
            'engine_versions': engine_versions,
        },
        'subsets': subset_reports,
        'fits': [],
        'proposals': [],
        'simple_cma_comparison': {
            'status': 'unmeasured',
            'reason': 'no independently validated comparable CMA outcomes in the committed '
                      'artifact; retrospective BO diagnostics only',
        },
        'limitations': limitations,
    }

    for definition in definitions:
        subset = _subset_training_set(training_set, definition['indices'])
        for multiplier in multipliers:
            cell = {
                'subset': definition['name'],
                'n': int(subset.n),
                'noise_multiplier': float(multiplier),
                'production_noise_multiplier': bool(abs(float(multiplier) - 1.0) <= 1e-12),
                'not_used_for_selection': True,
                'status': 'unavailable',
                'reason': None,
                'model_reason': None,
                'in_sample_rmse_j': None,
                'train_rmse_j': None,
                'training_mean_baseline_rmse_j': None,
                'predicted_j_mean': None,
                'predicted_j_min': None,
                'predicted_j_max': None,
                'negative_predicted_j': None,
                'prediction_flags': [],
                's2_original': None,
                'train_Yvar_original': None,
                'model': None,
            }
            try:
                fit_result = (fit(subset, multiplier) if fit is not None
                              else _fit_with_noise_multiplier(subset, multiplier))
            except Exception as exc:  # noqa: BLE001 - a failed fit is a reported refusal
                cell['reason'] = f'{type(exc).__name__}: {exc}'
                report['fits'].append(cell)
                continue
            if fit_result is None or getattr(fit_result, 'status', None) != 'ok':
                cell['reason'] = (getattr(fit_result, 'reason', None) or 'model_unavailable'
                                  if fit_result is not None else 'fit returned no model')
                cell['model_reason'] = cell['reason']
                if hasattr(fit_result, 'to_dict'):
                    cell['model'] = fit_result.to_dict()
                report['fits'].append(cell)
                continue
            try:
                raw_all = (predict(fit_result, training_set.X) if predict is not None
                           else _real_predict(fit_result, training_set.X))
                raw_train = (predict(fit_result, subset.X) if predict is not None
                             else _real_predict(fit_result, subset.X))
                if isinstance(raw_all, tuple):
                    pred_all, pred_result = raw_all
                else:
                    pred_all, pred_result = raw_all, None
                pred_train = raw_train[0] if isinstance(raw_train, tuple) else raw_train
                pred_all = np.asarray(pred_all, dtype=float).reshape(-1)
                pred_train = np.asarray(pred_train, dtype=float).reshape(-1)
                if pred_all.shape != (n,) or pred_train.shape != (int(subset.n),):
                    raise ValueError('prediction length mismatch')
                if not (np.all(np.isfinite(pred_all)) and np.all(np.isfinite(pred_train))):
                    raise ValueError('nonfinite prediction')
            except Exception as exc:  # noqa: BLE001 - a failed posterior is a refusal
                cell['reason'] = f'{type(exc).__name__}: {exc}'
                if hasattr(fit_result, 'to_dict'):
                    cell['model'] = fit_result.to_dict()
                report['fits'].append(cell)
                continue
            actual_all = np.asarray(training_set.J, dtype=float).reshape(-1)
            actual_train = np.asarray(subset.J, dtype=float).reshape(-1)
            cell.update({
                'status': 'ok',
                'in_sample_rmse_j': float(np.sqrt(np.mean((pred_all - actual_all) ** 2))),
                'train_rmse_j': float(np.sqrt(np.mean((pred_train - actual_train) ** 2))),
                'training_mean_baseline_rmse_j': float(np.sqrt(np.mean(
                    (actual_train.mean() - actual_all) ** 2))),
                'predicted_j_mean': float(np.mean(pred_all)),
                'predicted_j_min': float(np.min(pred_all)),
                'predicted_j_max': float(np.max(pred_all)),
                'negative_predicted_j': bool(np.any(pred_all < 0.0)),
                'prediction_flags': (list(getattr(pred_result, 'flags', ()) or ())
                                     if pred_result is not None else []),
                's2_original': getattr(fit_result, 's2_original', None),
                'train_Yvar_original': getattr(fit_result, 'train_Yvar_original', None),
                'model': (fit_result.to_dict() if hasattr(fit_result, 'to_dict') else None),
            })
            report['fits'].append(cell)

            if abs(float(multiplier) - float(proposal_noise_multiplier)) > 1e-12:
                continue
            for seed in seeds:
                proposal = {
                    'subset': definition['name'],
                    'noise_multiplier': float(multiplier),
                    'pool_seed': int(seed),
                    'status': 'unavailable',
                    'reason': None,
                    'geometry_hash': None,
                    'candidate_id': None,
                    'selection_reason': None,
                    'predicted': None,
                    'acquisition': None,
                }
                if propose is None:
                    proposal['reason'] = 'candidate pools not provided'
                    report['proposals'].append(proposal)
                    continue
                try:
                    item = propose(fit_result, int(seed))
                    if (not isinstance(item, dict)
                            or not isinstance(item.get('geometry_hash'), str)
                            or not item['geometry_hash']):
                        raise ValueError('proposal needs a nonempty geometry_hash')
                    proposal.update({
                        'status': str(item.get('status', 'ok')),
                        'geometry_hash': str(item['geometry_hash']),
                        'candidate_id': item.get('candidate_id'),
                        'selection_reason': item.get('selection_reason'),
                        'predicted': item.get('predicted'),
                        'acquisition': item.get('acquisition'),
                    })
                except Exception as exc:  # noqa: BLE001 - a failed proposal is a refusal
                    proposal['reason'] = f'{type(exc).__name__}: {exc}'
                report['proposals'].append(proposal)

    report['limitations'] = list(dict.fromkeys(report['limitations']))
    fit_statuses = [cell['status'] for cell in report['fits']]
    model_reasons = {cell.get('model_reason') for cell in report['fits']
                     if cell.get('model_reason')}
    proposal_ok = all(p['status'] in {'ok', 'acquisition', 'exploration',
                                      'exploration_fallback'}
                      for p in report['proposals'])
    if report['fits'] and all(status == 'ok' for status in fit_statuses):
        if report['proposals'] and proposal_ok:
            report['status'] = 'complete_descriptive'
        else:
            report['status'] = 'partial'
            if not report['proposals']:
                report['limitations'].append(
                    'candidate-pool proposal comparison was not provided')
    elif model_reasons == {'capability_missing'}:
        report['status'] = 'capability_missing'
        report['reason_code'] = 'capability_missing'
    elif any(status == 'ok' for status in fit_statuses):
        report['status'] = 'partial'
    else:
        report['status'] = 'unavailable'
        report['reason_code'] = ('capability_missing'
                                 if model_reasons == {'capability_missing'}
                                 else 'model_unavailable')
    if pools:
        space_filling = _space_filling_reference(pools, training_set.X)
        space_filling_status = 'prepared'
    else:
        space_filling = []
        space_filling_status = 'not_computed'
    report['comparison_preparation'] = {
        'status': 'preparation_only_off_policy_retrospective',
        'bo': {
            'method': 'qLogNEI acquisition from the finite scrambled-Sobol pool',
            'proposals': [
                {'subset': proposal['subset'],
                 'pool_seed': proposal['pool_seed'],
                 'status': proposal['status'],
                 'geometry_hash': proposal['geometry_hash'],
                 'selection_reason': proposal['selection_reason']}
                for proposal in report['proposals']
            ],
        },
        'space_filling': {
            'method': ('deterministic maximin (farthest-point) reference from the same '
                       'frozen scrambled-Sobol pool'),
            'status': space_filling_status,
            'proposals': space_filling,
        },
        'cma_seed': {
            'status': 'unmeasured',
            'reason': ('no independently validated comparable CMA-seed outcomes in the '
                       'committed artifact; no speedup or acoustic-benefit claim'),
        },
        'comparison_status': 'preparation_only_off_policy_retrospective',
        'next_step': ('an equal-cost screen of the prepared geometry hashes would be '
                      'required before any comparison; no BEM/GPU solve was run here'),
    }
    json.dumps(_jsonable(report), allow_nan=False)
    return report


def _candidate_dict(candidate) -> dict | None:
    if candidate is None:
        return None
    if hasattr(candidate, 'as_dict'):
        return candidate.as_dict(include_vectors=True)
    return dict(candidate)


def _build_proposal_artifact(*, selection, candidate, training, pool, encoding, config,
                             validation=None, generated_utc=None,
                             limitations=None) -> dict:
    """Assemble the immutable proposal record without any engine or solver call."""
    selected = selection.get('selection') or {}
    model = selection.get('model') or {}
    status = str(selection.get('status') or 'unavailable')
    reason = selection.get('reason')
    # Tag an unavailable selection with its concrete engine reason (model_unavailable,
    # capability_missing, pool_exhausted, ...) instead of a generic status.
    if status == 'unavailable':
        status = str(reason or 'model_unavailable')
    validation = validation or {'status': 'not_run'}
    if status == 'ok' and validation.get('status') != 'ok':
        status = 'capability_missing'
        reason = validation.get('reason') or 'proposal_validation_failed'
    publishable = status == 'ok'
    predicted = selected.get('predicted') if publishable else None
    acquisition = selected.get('acquisition') if publishable else None
    index = int(selected.get('proposal_index') or 0)
    exploration_every = 4
    cadence = {
        'every': exploration_every,
        'proposal_index': index,
        'index_is_exploration': (index + 1) % exploration_every == 0,
        'exploration_indices': [i for i in range(max(exploration_every, index + 1))
                                if (i + 1) % exploration_every == 0],
    }
    if status == 'ok':
        reason_code = None
    elif status == 'capability_missing':
        reason_code = 'capability_missing'
    elif status == 'unavailable':
        reason_code = str(reason or 'model_unavailable')
    else:
        reason_code = status
    artifact = {
        'tool': 'bo_proposal',
        'schema_version': 1,
        'protocol': PROTOCOL,
        'generated_utc': generated_utc or _utc_now(),
        'status': status,
        'reason': reason,
        'reason_code': reason_code,
        'model': model,
        'training': training,
        'pool': pool,
        'encoding': encoding,
        'config': config,
        'protocol_details': {
            'protocol': PROTOCOL,
            'target': 'Y = -J (minimise the frozen scalar objective J)',
            'predicted_j': 'predicted J = -posterior mean(Y)',
            'interval': ((predicted or {}).get('interval_label')
                         or 'model credible interval: marginal mu +/- 1.96*sigma from the '
                            'latent posterior (observation_noise=False)'),
            'model_policy': model.get('model_policy'),
            'selection_engine': (
                'hornlab_search.bo.propose._propose_one (locked scalar_pool_v1 selection in '
                'the BoTorch venv) + publish.validate_selected_candidate (project venv '
                'geometry leg); the public propose_one is split only by interpreter isolation'),
            'acquisition': 'qLogNoisyExpectedImprovement (qLogNEI); the log score is a '
                           'technical ranking diagnostic',
            'exploration_every': exploration_every,
            'acq_seed': (selected.get('acquisition') or {}).get('acq_seed'),
            'sampler_sample_shape': 128,
            'pool_chunk_size': 64,
            'prune_baseline': False,
            'near_duplicate_tol': 1e-6,
        },
        'selection': {
            'proposal_index': index,
            'next_proposal_index': selected.get('next_proposal_index'),
            'selection_reason': selected.get('selection_reason'),
            'exploration_cadence': cadence,
            'exploration': selected.get('exploration'),
            'counts': selected.get('counts') or {},
            'seeds_tried': selected.get('seeds_tried') or [],
        },
        'candidate': _candidate_dict(candidate),
        'predicted': predicted,
        'acquisition': acquisition,
        'validation': validation,
        'predictions_appended_to_measured_rows': False,
        'limitations': list(limitations or []),
    }
    if publishable and predicted is not None:
        low = float(predicted['j_lower'])
        mean = float(predicted['j_mean'])
        high = float(predicted['j_upper'])
        predicted['interval_lower_negative'] = bool(low < 0.0)
        predicted['interval_upper_negative'] = bool(high < 0.0)
        if low < 0.0:
            artifact['limitations'].append(
                'The model credible interval includes negative (nonphysical) J values; the '
                'predicted mean and interval are reported without clamping and the interval is '
                'a model diagnostic, not a physical tolerance.')
        lengthscales = (model.get('hyperparameters') or {}).get('lengthscales') or []
        if any(abs(float(value)) >= 4.0 - 1e-6 for value in lengthscales):
            artifact['limitations'].append(
                'At least one ARD lengthscale is at the locked upper bound (4.0); the '
                'mixed-fidelity fit is weakly constrained, so the proposal is advisory.')
        if not (low <= mean <= high):
            artifact['status'] = 'capability_missing'
            artifact['reason'] = 'predicted interval endpoints are not ordered'
            artifact['predicted'] = None
            artifact['acquisition'] = None
            publishable = False
    if publishable and acquisition is not None:
        units = str(acquisition.get('units') or '')
        if 'ranking diagnostic' not in units:
            acquisition['units'] = units + ' (technical ranking diagnostic)'
    if not publishable and candidate is not None:
        artifact['exploration_fallback'] = {
            'candidate_id': getattr(candidate, 'candidate_id', None),
            'geometry_hash': getattr(candidate, 'geometry_hash', None),
            'predicted': None,
            'note': 'labelled non-BO maximin fallback; no predictions are fabricated',
        }
    if artifact['candidate'] is not None:
        artifact['candidate']['key_order'] = list(encoding.get('active_keys') or ())
        artifact['candidate']['status_note'] = POOL_STATUS_NOTE
    artifact['limitations'] = list(dict.fromkeys(
        artifact['limitations'] + list((training or {}).get('limitations') or []) + [
        'Advisory offline proposal; no BEM/GPU solve was run.',
        'The candidate is cheap-check-passed; mesh/acoustic eligibility is unknown.',
        'Predicted J and its credible interval are model outputs, not measured results, '
        'and are never appended as measured rows.',
        'The acquisition value is a technical ranking diagnostic, not predicted J or a '
        'probability of success.',
        'J is objective v4 only; no cross-version ranking.',
        'One proposal index is published; the every-fourth exploration cadence is stateful '
        'and does not reset on resume.',
    ]))
    json.dumps(_jsonable(artifact), allow_nan=False)
    return artifact


def render_sensitivity_md(report: dict) -> str:
    lines = [
        '# M2 sensitivity (real native TrainingSet)', '',
        f"Status: **{report.get('status')}** · protocol `{report.get('protocol')}` · "
        f"generated `{report.get('generated_utc')}`", '',
        '## Input', '',
    ]
    source = report.get('input') or {}
    if source:
        lines += [
            f"- training JSON: `{source.get('json_path')}` sha256 "
            f"`{source.get('json_sha256')}`",
            f"- training NPZ: `{source.get('npz_path')}` sha256 "
            f"`{source.get('npz_sha256')}`",
            f"- recomputed X/J/Y/ids hashes: `{source.get('recomputed_hashes')}`",
            f"- counts: n={source.get('n')} d={source.get('d')} "
            f"eligible={source.get('n_eligible')} unique={source.get('n_unique')} "
            f"unique_designs={source.get('n_unique_design_hashes')} "
            f"refused={source.get('n_refused')}",
            f"- active keys ({source.get('projection_version')}): "
            f"`{', '.join(source.get('active_keys') or [])}`",
            f"- objective versions: {source.get('objective_versions')}",
            f"- solve-hash groups: {source.get('solve_hash_groups')}",
            '',
        ]
    cohort = report.get('cohort') or {}
    lines += [
        '## Cohort and validation mode', '',
        f"- cohort: `{cohort.get('cohort_id')}`",
        f"- independent groups available: `{cohort.get('independent_groups_available')}`",
        f"- reason: {cohort.get('independent_groups_reason')}",
        f"- validation mode: `{report.get('validation_mode')}`", '',
    ]
    method = report.get('method') or {}
    lines += [
        '## Method', '',
        f"- {method.get('fit')}",
        f"- {method.get('predict')}",
        f"- {method.get('proposal')}",
        f"- noise multipliers: {method.get('noise_multipliers')} "
        f"({method.get('noise_multiplier_use')})",
        f"- pool seeds: {method.get('pool_seeds')}",
        f"- diagnostic caps: {method.get('diagnostic_caps')}",
        f"- engine versions: `{method.get('engine_versions')}`", '',
    ]
    lines += ['## Subsets', '',
              '| subset | n | rule | production | diagnostic-only |',
              '|---|---:|---|---:|---:|']
    for subset in report.get('subsets') or []:
        lines.append(
            f"| `{subset['name']}` | {subset['n']} | {subset['rule']} | "
            f"{subset['production_recipe']} | {subset['diagnostic_only']} |")
    lines += ['', '## Fit sensitivity (descriptive in-sample)', '',
              '| subset | noise x | status | in-sample RMSE J | train-mean baseline | '
              'pred J mean | pred J range | s2 | train_Yvar |',
              '|---|---:|---|---:|---:|---:|---|---:|---:|']
    for fit in report.get('fits') or []:
        rng = '—'
        if fit.get('predicted_j_min') is not None:
            rng = f"[{fit['predicted_j_min']:.4g}, {fit['predicted_j_max']:.4g}]"
        rmse = fit.get('in_sample_rmse_j')
        baseline = fit.get('training_mean_baseline_rmse_j')
        mean = fit.get('predicted_j_mean')
        lines.append(
            f"| `{fit['subset']}` | {fit['noise_multiplier']} | {fit['status']} | "
            f"{'—' if rmse is None else f'{rmse:.6g}'} | "
            f"{'—' if baseline is None else f'{baseline:.6g}'} | "
            f"{'—' if mean is None else f'{mean:.6g}'} | {rng} | "
            f"{fit.get('s2_original')} | {fit.get('train_Yvar_original')} |")
    lines += ['', '## Proposal sensitivity (off-policy retrospective)', '',
              '| subset | pool seed | status | selection | geometry hash | pred J mean | '
              'pred J interval | acquisition (technical) |',
              '|---|---:|---|---|---|---:|---|---:|']
    for proposal in report.get('proposals') or []:
        predicted = proposal.get('predicted') or {}
        mean = predicted.get('j_mean')
        interval = '—'
        if predicted.get('j_lower') is not None:
            interval = f"[{predicted.get('j_lower')}, {predicted.get('j_upper')}]"
        acquisition = (proposal.get('acquisition') or {}).get('value')
        lines.append(
            f"| `{proposal['subset']}` | {proposal['pool_seed']} | {proposal['status']} | "
            f"{proposal.get('selection_reason') or '—'} | "
            f"`{proposal.get('geometry_hash')}` | "
            f"{'—' if mean is None else f'{mean:.6g}'} | {interval} | "
            f"{'—' if acquisition is None else f'{acquisition:.6g}'} |")
    comparison = report.get('comparison_preparation') or {}
    lines += ['', '## Space-filling vs BO vs CMA preparation', '',
              f"- comparison status: `{comparison.get('comparison_status')}`",
              f"- BO: {comparison.get('bo', {}).get('method')}",
              f"- space-filling: {comparison.get('space_filling', {}).get('method')} "
              f"(`{comparison.get('space_filling', {}).get('status')}`)",
              f"- CMA seed: `{comparison.get('cma_seed', {}).get('status')}` — "
              f"{comparison.get('cma_seed', {}).get('reason')}",
              f"- next step: {comparison.get('next_step')}", '']
    for item in comparison.get('space_filling', {}).get('proposals') or []:
        lines.append(f"  - space-filling pool seed {item.get('pool_seed')}: "
                     f"`{item.get('geometry_hash')}` ({item.get('status')})")
    lines += ['', '## Limitations', '']
    lines += [f'- {note}' for note in report.get('limitations') or []]
    comparison = report.get('simple_cma_comparison') or {}
    lines += ['', '## Simple/CMA comparison', '',
              f"- status: `{comparison.get('status')}`",
              f"- reason: {comparison.get('reason')}", '']
    return '\n'.join(lines) + '\n'


def _cmd_sensitivity(args) -> int:
    loaded = load_native_training_set(args.training_json, args.npz,
                                      config_path=args.config)
    out_dir = Path(args.out)
    if loaded['status'] != 'ok':
        report = {
            'tool': 'bo_sensitivity', 'schema_version': 2, 'protocol': PROTOCOL,
            'generated_utc': _utc_now(), 'status': 'unavailable',
            'reason': loaded.get('reason'), 'reason_code': loaded.get('reason_code'),
            'gate_pass': None, 'input': loaded.get('provenance') or {},
            'limitations': loaded.get('limitations') or [], 'subsets': [],
            'fits': [], 'proposals': [],
            'simple_cma_comparison': {
                'status': 'unmeasured',
                'reason': 'training artifact unavailable',
            },
        }
        _write_json(out_dir / 'sensitivity.json', report)
        _write_text(out_dir / 'sensitivity.md', render_sensitivity_md(report))
        print(json.dumps({'status': report['status'], 'reason': report['reason']},
                         indent=2))
        return 2

    training = loaded['training']
    provenance = dict(loaded['provenance'])
    provenance['limitations'] = loaded.get('limitations') or []
    pools = {}
    for seed, pool_path in ((args.pool_seeds[0], args.pool_a),
                            (args.pool_seeds[1], args.pool_b)):
        if pool_path:
            pools[int(seed)] = load_candidate_pool(pool_path)
    groups = None
    cohort_ids = None
    validation_evidence_id = None
    if args.groups_json:
        data = json.loads(Path(args.groups_json).read_text(encoding='utf-8'))
        groups = data.get('groups')
        cohort_ids = data.get('cohort_ids')
        validation_evidence_id = data.get('validation_evidence_id')
    report = run_real_diagnostics(
        training_set=training, provenance=provenance, groups=groups,
        cohort_ids=cohort_ids, validation_evidence_id=validation_evidence_id,
        propose=(real_propose_from_pools(pools) if pools else None), pools=pools,
        pool_seeds=tuple(args.pool_seeds),
        noise_multipliers=tuple(args.noise_multipliers),
        diagnostic_caps=tuple(args.diagnostic_caps),
        require_groups=args.require_groups, split_seed=args.split_seed)
    _write_json(out_dir / 'sensitivity.json', report)
    _write_text(out_dir / 'sensitivity.md', render_sensitivity_md(report))
    print(json.dumps({
        'status': report['status'],
        'n': (report.get('cohort') or {}).get('n'),
        'n_subsets': len(report.get('subsets') or []),
        'n_fits': len(report.get('fits') or []),
        'n_proposals': len(report.get('proposals') or []),
    }, indent=2))
    return 0 if report['status'] in ('complete_descriptive', 'partial',
                                     'complete_diagnostics') else 2


def _cmd_generate_pools(args) -> int:
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.bo.encoding import ActiveProjection
    from hornlab_search.bo.data import build_candidate_pool
    from hornlab_search.bo.model import library_versions

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    space = DesignSpace.from_config(config)
    projection = ActiveProjection.from_space(space, no_ops={'morph_exponent': 4.0})
    encoding_identity = _encoding_identity(projection)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    committed = None
    if DEFAULT_POOL_MANIFEST.is_file():
        committed = json.loads(DEFAULT_POOL_MANIFEST.read_text(encoding='utf-8'))
    index = {
        'tool': 'bo_pool_index', 'schema_version': 1, 'protocol': PROTOCOL,
        'generated_utc': _utc_now(), 'config': str(config_path),
        'encoding': encoding_identity, 'pools': {},
    }
    for seed in [int(s) for s in args.seeds]:
        pool = build_candidate_pool(space, projection, config, n=int(args.n), seed=seed,
                                    resolution_mm=float(args.resolution_mm))
        payload = {
            'tool': 'bo_candidate_pool', 'schema_version': 1, 'protocol': PROTOCOL,
            'generated_utc': _utc_now(),
            'config': {'path': str(config_path), 'name': config_path.name},
            'encoding': encoding_identity, 'summary': pool.summary(),
            'candidates': pool.candidates_json(include_vectors=True),
            'library_versions': library_versions(),
        }
        path = out_dir / f'pool-{seed}.json'
        _write_json(path, payload)
        entry = {'path': str(path), 'sha256': _sha256_file(path),
                 'summary': pool.summary()}
        if committed is not None and int(committed.get('seed') or -1) == seed:
            match = {
                'requested': int(committed.get('requested', -1)) == int(pool.requested),
                'n_candidates': int(committed.get('n_candidates', -1)) == len(pool.candidates),
                'counts': dict(committed.get('counts') or {}) == dict(pool.counts),
                'intended_solve_hash': (str(committed.get('intended_solve_hash'))
                                        == str(pool.intended_solve_hash)),
            }
            samples = committed.get('candidate_sample') or []
            by_id = {candidate.candidate_id: candidate for candidate in pool.candidates}
            checks = []
            for sample in samples:
                candidate = by_id.get(str(sample.get('candidate_id')))
                checks.append(bool(
                    candidate is not None
                    and candidate.geometry_hash == sample.get('geometry_hash')
                    and candidate.design_hash == sample.get('design_hash')
                    and candidate.intended_solve_hash == sample.get('intended_solve_hash')
                    and candidate.params == sample.get('params')))
            match['candidate_sample_match'] = bool(samples) and all(checks)
            match['n_candidate_samples_checked'] = len(samples)
            entry['committed_manifest_match'] = match
        index['pools'][str(seed)] = entry
        print(f'pool seed {seed}: {len(pool.candidates)} candidates -> {path}')
    _write_json(out_dir / 'pool_index.json', index)
    print(json.dumps(_jsonable(index), indent=2))
    return 0 if all(value['summary']['status'] == 'ok'
                    for value in index['pools'].values()) else 2


def _cmd_select(args) -> int:
    loaded = load_native_training_set(args.training_json, args.npz,
                                      config_path=args.config)
    if loaded['status'] != 'ok':
        payload = {
            'tool': 'bo_proposal_selection', 'schema_version': 1,
            'protocol': PROTOCOL, 'generated_utc': _utc_now(),
            'status': 'unavailable', 'reason': loaded.get('reason'),
            'model': None, 'selection': None,
            'training': loaded.get('provenance') or {},
        }
        _write_json(args.out, payload)
        print(json.dumps({'status': payload['status'], 'reason': payload['reason']},
                         indent=2))
        return 2

    from hornlab_search.bo.model import fit_model, library_versions
    from hornlab_search.bo.propose import ProposalHistory, ProposalPolicy, _propose_one

    training = loaded['training']
    provenance = dict(loaded['provenance'])
    provenance['limitations'] = loaded.get('limitations') or []
    pool_path = Path(args.pool)
    pool = load_candidate_pool(pool_path)
    fit_result = fit_model(training, seed=int(args.model_seed))
    selection = _propose_one(
        fit_result, pool,
        proposal_policy=ProposalPolicy(acq_seed=int(args.acq_seed)),
        history=ProposalHistory(proposal_index=int(args.proposal_index)))
    payload = {
        'tool': 'bo_proposal_selection', 'schema_version': 1,
        'protocol': PROTOCOL, 'generated_utc': _utc_now(),
        'status': selection.status, 'reason': selection.reason,
        'model': fit_result.to_dict(),
        'selection': selection.to_dict(),
        'training': provenance,
        'pool': {'path': str(pool_path), 'sha256': _sha256_file(pool_path),
                 'summary': pool.summary()},
        'engine': {
            'library_versions': library_versions(),
            'selection_function': ('hornlab_search.bo.propose._propose_one '
                                   '(locked scalar_pool_v1 selection)'),
        },
    }
    _write_json(args.out, payload)
    print(json.dumps({
        'status': payload['status'], 'reason': payload['reason'],
        'candidate_id': selection.candidate_id,
        'geometry_hash': selection.geometry_hash,
        'selection_reason': selection.selection_reason,
    }, indent=2))
    return 0 if selection.geometry_hash else 2


def _cmd_publish(args) -> int:
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.bo.encoding import ActiveProjection
    from hornlab_search.bo.propose import validate_selected_candidate

    selection = json.loads(Path(args.selection).read_text(encoding='utf-8'))
    pool_path = Path(args.pool)
    pool = load_candidate_pool(pool_path)
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    space = DesignSpace.from_config(config)
    projection = ActiveProjection.from_space(space, no_ops={'morph_exponent': 4.0})
    selected = selection.get('selection') or {}
    candidate_id = selected.get('candidate_id')
    candidate = next((item for item in pool.candidates
                      if item.candidate_id == candidate_id), None)
    validation = {'status': 'not_run', 'reason': 'selection is not publishable'}
    if candidate is not None and selection.get('status') == 'ok':
        try:
            validate_selected_candidate(candidate, pool, encoding=projection,
                                        config=config,
                                        resolution_mm=float(args.resolution_mm))
            validation = {
                'status': 'ok',
                'checks': ['active_vector_projection', 'design_hash', 'params',
                           'intended_solve_hash', 'materialized_geometry_hash',
                           'brief_envelope', 'throat'],
                'resolution_mm': float(args.resolution_mm),
                'function': ('hornlab_search.bo.propose.'
                             'validate_selected_candidate'),
            }
        except Exception as exc:  # noqa: BLE001 - a refused geometry is reported
            validation = {'status': 'failed',
                          'reason': f'{type(exc).__name__}: {exc}',
                          'resolution_mm': float(args.resolution_mm)}

    reference = {}
    source = (Path(args.pool_manifest_source) if args.pool_manifest_source
              else DEFAULT_POOL_MANIFEST)
    out_dir = Path(args.out).parent
    if source.is_file():
        destination = out_dir / 'pool_manifest.json'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        reference = {'source': str(source), 'path': str(destination),
                     'sha256': _sha256_file(destination),
                     'bytes': int(destination.stat().st_size)}
    else:
        reference = {'source': str(source), 'path': None, 'sha256': None,
                     'bytes': None, 'note': 'committed pool manifest not found'}
    pool_identity = {
        'path': str(pool_path), 'sha256': _sha256_file(pool_path),
        'summary': pool.summary(), 'status_note': POOL_STATUS_NOTE,
        'reference_manifest': reference,
    }
    if args.pool_index and Path(args.pool_index).is_file():
        pool_index = json.loads(Path(args.pool_index).read_text(encoding='utf-8'))
        for seed, entry in (pool_index.get('pools') or {}).items():
            if entry.get('sha256') == pool_identity['sha256']:
                pool_identity['committed_manifest_match'] = entry.get(
                    'committed_manifest_match')
                pool_identity['index_entry'] = {'seed': seed,
                                                'path': entry.get('path')}
                break
    artifact = _build_proposal_artifact(
        selection=selection, candidate=candidate,
        training=selection.get('training') or {}, pool=pool_identity,
        encoding=_encoding_identity(projection),
        config=_config_identity(config_path), validation=validation)
    _write_json(args.out, artifact)
    print(json.dumps({
        'status': artifact['status'], 'reason': artifact['reason'],
        'candidate_id': (artifact.get('candidate') or {}).get('candidate_id'),
        'geometry_hash': (artifact.get('candidate') or {}).get('geometry_hash'),
        'predicted': artifact.get('predicted'),
        'validation': artifact.get('validation'),
    }, indent=2))
    return 0 if artifact['status'] == 'ok' else 2


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest='command', required=True)

    sensitivity = subparsers.add_parser(
        'sensitivity', help='real-data M2 subset/noise/pool diagnostics')
    sensitivity.add_argument('--training-json', default=str(DEFAULT_TRAINING_JSON))
    sensitivity.add_argument('--npz', default=None)
    sensitivity.add_argument('--config', default=str(DEFAULT_CONFIG))
    sensitivity.add_argument('--out', default=str(DEFAULT_OUT_DIR))
    sensitivity.add_argument('--pool-a', default=None)
    sensitivity.add_argument('--pool-b', default=None)
    sensitivity.add_argument('--pool-seeds', nargs=2, type=int,
                             default=list(DEFAULT_POOL_SEEDS))
    sensitivity.add_argument('--noise-multipliers', nargs='+', type=float,
                             default=list(NOISE_MULTIPLIERS))
    sensitivity.add_argument('--diagnostic-caps', nargs='+', type=int,
                             default=list(DIAGNOSTIC_CAPS))
    sensitivity.add_argument('--groups-json', default=None,
                             help='optional JSON with groups/cohort_ids/'
                                  'validation_evidence_id')
    sensitivity.add_argument('--require-groups', action='store_true')
    sensitivity.add_argument('--split-seed', type=int, default=0)
    sensitivity.set_defaults(func=_cmd_sensitivity)

    pools = subparsers.add_parser(
        'generate-pools', help='generate candidate pools (project venv; needs the mesher)')
    pools.add_argument('--config', default=str(DEFAULT_CONFIG))
    pools.add_argument('--out-dir',
                       default=str(REPO_ROOT / 'scratch' / 'bo_m0' / 'm2' / 'pools'))
    pools.add_argument('--n', type=int, default=4096)
    pools.add_argument('--seeds', nargs='+', type=int, default=list(DEFAULT_POOL_SEEDS))
    pools.add_argument('--resolution-mm', type=float, default=30.0)
    pools.set_defaults(func=_cmd_generate_pools)

    select = subparsers.add_parser(
        'select', help='fit the locked model and select a proposal (bayes venv)')
    select.add_argument('--training-json', default=str(DEFAULT_TRAINING_JSON))
    select.add_argument('--npz', default=None)
    select.add_argument('--config', default=str(DEFAULT_CONFIG))
    select.add_argument('--pool', required=True)
    select.add_argument('--out', required=True)
    select.add_argument('--model-seed', type=int, default=0)
    select.add_argument('--acq-seed', type=int, default=0)
    select.add_argument('--proposal-index', type=int, default=0)
    select.set_defaults(func=_cmd_select)

    publish = subparsers.add_parser(
        'publish', help='revalidate the geometry and publish the proposal (project venv)')
    publish.add_argument('--selection', required=True)
    publish.add_argument('--pool', required=True)
    publish.add_argument('--config', default=str(DEFAULT_CONFIG))
    publish.add_argument('--out', required=True)
    publish.add_argument('--pool-manifest-source', default=str(DEFAULT_POOL_MANIFEST))
    publish.add_argument('--pool-index', default=None)
    publish.add_argument('--resolution-mm', type=float, default=30.0)
    publish.set_defaults(func=_cmd_publish)

    args = parser.parse_args(argv)
    return int(args.func(args))


__all__ = [
    'run_diagnostics',
    'load_native_training_set',
    'run_real_diagnostics',
    'real_propose_from_pools',
    'save_candidate_pool',
    'load_candidate_pool',
    'render_sensitivity_md',
    'main',
]


if __name__ == '__main__':
    raise SystemExit(main())
