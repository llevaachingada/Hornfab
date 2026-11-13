"""M2 gate diagnostics on the frozen native-only cohort (bo-study-v1.1).

Run in the isolated BoTorch venv from the repository root::

    bayes-venv\\Scripts\\python.exe scratch\\bo_m0\\m2_gate\\m2_gate_diagnostics.py

Read-only over runs/, dataset/ and evidence; every read input is SHA-256 hashed; output is
``scratch/bo_m0/m2_gate/m2_gate_diagnostics.json``.  No solver, mesher, GPU or lane is touched.

Sections:
  1. cohort identity     - committed TrainingSet hashes, re-joined to a fresh read-only catalog
  2. group recovery      - training rows mapped to the run directories that produced them
  3. strict harness      - bo_sensitivity.run_diagnostics with the recovered groups
  4. external holdout    - an independent CMA run of the same config (seed 1235), replayed with
                           zero backend calls, predicted by models fit on the frozen cohort
  5. baselines           - training-mean and 1-NN predictors on the same holdout
  6. CMA trajectories    - best-so-far J for the two independent CMA runs at equal budgets
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from hornlab_search.bo.data import build_native_training_set  # noqa: E402
from hornlab_search.bo.model import fit_model, predict_j  # noqa: E402
from tools.analysis import bo_sensitivity as bs  # noqa: E402

OUT = REPO / 'scratch/bo_m0/m2_gate'
CONFIG = REPO / 'examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml'
TRAIN_JSON = REPO / 'docs/evidence/bo_study_2026-11-12/b2_native/native_trainingset.json'
R0_FROZEN = REPO / 'docs/evidence/bo_study_2026-11-12/r0/offline_scores.json'
R0_SCRATCH = REPO / 'scratch/bo_m0/r0/offline_scores_native_full/offline_scores.json'
R0_NEW = OUT / 'offline_scores_native_20261113/offline_scores.json'
CATALOG_NEW = OUT / 'catalog_20261113/catalog.csv'
SENS_COMMITTED = REPO / 'docs/evidence/bo_study_2026-11-12/m2/sensitivity.json'
SENS_RERUN = OUT / 'sensitivity_rerun/sensitivity.json'
RUNS = {
    'c41398': REPO / 'runs/20261027T045427Z-screen-c41398',
    'd37d64': REPO / 'runs/20261027T070736Z-screen-d37d64',
    'd37d64_verify': REPO / 'runs/20261027T070736Z-screen-d37d64/verify',
    '46b68c': REPO / 'runs/20261113T004133Z-screen-46b68c',
}
HOLDOUT_RUN_ID = '20261113T004133Z-screen-46b68c'
hashes: dict[str, str] = {}


def sha_file(path: Path) -> str:
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    hashes[str(path.relative_to(REPO))] = h
    return h


def read_ndjson(path: Path) -> list[dict]:
    sha_file(path)
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def spearman(a, b) -> float:
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def main() -> int:
    report: dict = {'tool': 'm2_gate_diagnostics', 'protocol': 'bo-study-v1.1'}
    for p in (CONFIG, TRAIN_JSON, TRAIN_JSON.with_suffix('.npz'), R0_FROZEN, R0_SCRATCH, R0_NEW,
              CATALOG_NEW, SENS_COMMITTED, SENS_RERUN):
        sha_file(p)

    # ---------------------------------------------------------------- 1. cohort identity
    loaded = bs.load_native_training_set(TRAIN_JSON)
    assert loaded['status'] == 'ok', loaded
    ts, prov = loaded['training'], loaded['provenance']
    payload = json.loads(TRAIN_JSON.read_text(encoding='utf-8'))
    idents = payload['identities']
    import csv
    catalog = {}
    with open(CATALOG_NEW, encoding='utf-8', newline='') as fh:
        for rec in csv.DictReader(fh):
            catalog[(rec['shard_index'], rec['row'])] = rec
    join = {'n': 0, 'config': {}, 'dependency_hash': {}, 'fidelity': {}, 'objective_version': {},
            'run_id': {}, 'design_hash_agree': 0, 'missing': []}
    for oid in ts.ids:
        ident = idents[oid]
        rec = catalog.get((str(ident['shard']), str(ident['row'])))
        if rec is None:
            join['missing'].append(oid)
            continue
        join['n'] += 1
        for key, field in (('config', 'config_name'), ('dependency_hash', 'dependency_hash'),
                           ('fidelity', 'fidelity'), ('objective_version', 'objective_version'),
                           ('run_id', 'run_id')):
            join[key][rec[field]] = join[key].get(rec[field], 0) + 1
        join['design_hash_agree'] += int(rec['design_hash'] == ident['design_hash'])
    r0_same = hashes[str(R0_FROZEN.relative_to(REPO))] == hashes[str(R0_SCRATCH.relative_to(REPO))]
    report['cohort_identity'] = {
        'training_hashes_verified': prov.get('hashes_verified'),
        'recomputed_hashes': prov.get('recomputed_hashes'),
        'n': ts.n, 'd': ts.d, 'active_keys': list(ts.active_keys),
        'projection_version': ts.projection_version,
        'r0_committed_equals_builder_input': r0_same,
        'fresh_catalog_join': join,
        'solve_hash_groups': prov.get('solve_hash_groups') or prov.get('majority_solve_group', {}).get('counts'),
    }

    # ---------------------------------------------------------------- 2. group recovery
    run_keys: dict[str, set] = {}
    for name, rdir in RUNS.items():
        rows = read_ndjson(rdir / 'search.ndjson')
        run_keys[name] = {(r.get('design_hash'), r.get('solve_hash')) for r in rows if r.get('ok')}
        rj = rdir / 'run.json'
        if rj.is_file():
            sha_file(rj)
    membership = {}
    for oid in ts.ids:
        ident = idents[oid]
        key = (ident['design_hash'], ident['solve_hash'])
        membership[oid] = sorted(n for n, keys in run_keys.items() if key in keys)
    # Connected components: a row in several runs links them (shared seed design, resume,
    # verify-of-run).  The verify dir is produced FROM d37d64 finalists, so it is linked to it.
    parent = {n: n for n in RUNS}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    union('d37d64_verify', 'd37d64')
    for runs in membership.values():
        for other in runs[1:]:
            union(runs[0], other)
    groups = {oid: (find(runs[0]) if runs else 'unmapped') for oid, runs in membership.items()}
    group_counts: dict[str, int] = {}
    for g in groups.values():
        group_counts[g] = group_counts.get(g, 0) + 1
    combos: dict[str, int] = {}
    for runs in membership.values():
        k = '+'.join(runs) or 'unmapped'
        combos[k] = combos.get(k, 0) + 1
    report['group_recovery'] = {
        'method': ('exact (design_hash, solve_hash) membership in each native run directory '
                   'search.ndjson; verify dir linked to its parent screen run; rows in several '
                   'runs union those runs'),
        'membership_counts': combos,
        'connected_group_counts': group_counts,
        'n_independent_groups': len([g for g in group_counts if g != 'unmapped']),
        'note': ('c41398 is a 1-evaluation smoke run whose only row is the config seed design, '
                 'which d37d64 also evaluates first; d37d64 is one CMA experiment (seed 1234) '
                 'with one resume segment; its verify rows re-solve d37d64 finalists.'),
    }

    # ---------------------------------------------------------------- 3. strict harness
    X = np.asarray(ts.X, float)
    J = np.asarray(ts.J, float).reshape(-1)
    strict = bs.run_diagnostics(
        X=X, J=J, ids=ts.ids, groups=[groups[i] for i in ts.ids],
        cohort_ids=['native__ath_core_v4|active-projection-v1|objective_v4'] * ts.n,
        validation_evidence_id='m2_gate_group_recovery_20261113',
        fit=lambda *a: None, predict=lambda *a: None, propose=lambda *a: None,
        pool_seeds=(20261112, 20261113))
    report['strict_group_heldout'] = {'status': strict.get('status'),
                                      'reason': strict.get('reason'),
                                      'gate_pass': strict.get('gate_pass')}

    # ---------------------------------------------------------------- 4. external holdout
    new_payload = json.loads(R0_NEW.read_text(encoding='utf-8'))
    hold_rows = [r for r in new_payload['rows'] if r.get('catalog_run_id') == HOLDOUT_RUN_ID]
    filtered = dict(new_payload)
    filtered['rows'] = hold_rows
    filtered_path = OUT / 'holdout_46b68c_scores.json'
    filtered_path.write_text(json.dumps(filtered), encoding='utf-8')
    hold = build_native_training_set(CONFIG, scores_json=filtered_path, catalog_csv=CATALOG_NEW)
    combined = build_native_training_set(CONFIG, scores_json=R0_NEW, catalog_csv=CATALOG_NEW)
    train_geoms = {idents[i]['design_hash'] for i in ts.ids}
    hold_meta = hold.meta['identities']
    # Use every eligible holdout row (not only the capped subset; n < cap anyway).
    hold_ids = [i for i in hold.ids if hold_meta[i]['design_hash'] not in train_geoms]
    pos = {oid: k for k, oid in enumerate(hold.ids)}
    Xh = np.asarray(hold.X, float)[[pos[i] for i in hold_ids]]
    Jh = np.asarray(hold.J, float).reshape(-1)[[pos[i] for i in hold_ids]]
    parity = [abs(hold_meta[i]['parity_delta']) for i in hold_ids
              if hold_meta[i].get('parity_delta') is not None]
    report['external_holdout'] = {
        'source': HOLDOUT_RUN_ID,
        'replay': {'r0_status': new_payload.get('status'),
                   'backend_calls': new_payload.get('backend_guard', {}).get('calls'),
                   'source_unchanged': new_payload.get('source_guard', {}).get('unchanged'),
                   'n_rows_from_run': len(hold_rows),
                   'max_abs_parity_delta': max(parity) if parity else None,
                   'n_parity': len(parity)},
        'holdout_training_set_status': hold.status,
        'holdout_cohort_policy': hold.meta['cohort_policy']['status'],
        'holdout_refusals': hold.meta['refusal_reasons'],
        'n_eligible': hold.n_eligible,
        'n_excluded_shared_geometry_with_training': hold.n_eligible - len(hold_ids),
        'n_holdout': len(hold_ids),
        'pooled_frozen_plus_holdout_builder': {
            'status': combined.status,
            'cohort_policy_status': combined.meta['cohort_policy']['status'],
            'conflicts': combined.meta['cohort_policy']['conflicts'],
            'dependency_hash_values': combined.meta['cohort_policy']['values']['dependency_hash'],
        },
        'caveats': [
            'One independent experiment group only (CMA seed 1235); the protocol needs five '
            'connected groups for a gate-grade group-held-out estimate.',
            'Dependency-shifted: the holdout run used different pinned beat/mesher/hornlab_search '
            'SHAs (dependency_hash 84709bd8e737cca4 vs e3614d0ba5956ded); same solve_hash and '
            'mesh spec.  The strict builder refuses pooling the two (shown above).',
            'Screen-fidelity holdout; the frozen training set mixes 192 screen + 5 verify rows.',
        ],
    }

    definitions = bs._subset_definitions(ts, prov, (64, 128))
    nn_dist = ((Xh[:, None, :] - X[None, :, :]) ** 2).sum(-1)
    Jh_stored = np.asarray([hold_meta[i]['stored_j'] for i in hold_ids], float)
    report['holdout_prediction'] = {}
    for label, Jh in (('replayed_brief_target_regenerated', Jh), ('stored_runtime_j', Jh_stored)):
      results = evaluate(definitions, ts, Xh, Jh, nn_dist)
      report['holdout_prediction'][label] = {
        'n_holdout': int(len(Jh)),
        'holdout_J': {'min': float(Jh.min()), 'median': float(np.median(Jh)), 'max': float(Jh.max())},
        'training_J': {'min': float(J.min()), 'median': float(np.median(J)), 'max': float(J.max())},
        'results': results}
    report['holdout_prediction']['interpretation_rule'] = (
        'GP is useful on this holdout only if its RMSE is below BOTH the training-mean and 1-NN '
        'baselines and its Spearman rank correlation is clearly positive; one holdout group is '
        'descriptive, not a gate-grade estimate.')
    _section6(report)
    return _finish(report)


def evaluate(definitions, ts, Xh, Jh, nn_dist):
    results = []
    for definition in definitions:
        sub = bs._subset_training_set(ts, definition['indices'])
        Xs = np.asarray(sub.X, float)
        Js = np.asarray(sub.J, float).reshape(-1)
        idx = np.asarray(definition['indices'], int)
        nn = Js[np.argmin(nn_dist[:, idx], axis=1)]
        mean_rmse = float(np.sqrt(np.mean((Js.mean() - Jh) ** 2)))
        nn_rmse = float(np.sqrt(np.mean((nn - Jh) ** 2)))
        for mult in (0.1, 1.0, 10.0):
            entry = {'subset': definition['name'], 'n_train': int(sub.n), 'noise_multiplier': mult,
                     'training_mean_rmse_j': mean_rmse, 'nearest_neighbour_rmse_j': nn_rmse,
                     'nearest_neighbour_spearman': spearman(nn, Jh)}
            fitted = bs._fit_with_noise_multiplier(sub, mult, seed=0)
            if getattr(fitted, 'status', None) != 'ok':
                entry.update(status='fit_unavailable', reason=getattr(fitted, 'reason', None))
                results.append(entry)
                continue
            pred = predict_j(fitted, Xh)
            if pred.status != 'ok':
                entry.update(status='predict_unavailable', reason=pred.reason)
                results.append(entry)
                continue
            mu = np.asarray(pred.j_mean, float).reshape(-1)
            lo = np.asarray(pred.j_lower, float).reshape(-1)
            hi = np.asarray(pred.j_upper, float).reshape(-1)
            k = 20
            top_true = set(np.argsort(Jh)[:k])
            top_pred = set(np.argsort(mu)[:k])
            entry.update(
                status='ok',
                gp_rmse_j=float(np.sqrt(np.mean((mu - Jh) ** 2))),
                gp_mae_j=float(np.mean(np.abs(mu - Jh))),
                gp_spearman=spearman(mu, Jh),
                gp_interval_coverage_95=float(np.mean((Jh >= np.minimum(lo, hi)) & (Jh <= np.maximum(lo, hi)))),
                gp_negative_predicted_j=int(np.sum(mu < 0)),
                gp_top20_overlap=len(top_true & top_pred),
                gp_predicted_best_actual_j=float(Jh[int(np.argmin(mu))]),
                holdout_best_actual_j=float(Jh.min()),
            )
            results.append(entry)
    return results


def _section6(report):
    # ---------------------------------------------------------------- 6. CMA trajectories
    traj = {}
    for name in ('d37d64', '46b68c'):
        rows = read_ndjson(RUNS[name] / 'search.ndjson')
        best, nvalid, attempts, seconds, curve = np.inf, 0, 0, 0.0, {}
        for r in rows:
            attempts += 1
            sec = r.get('seconds')
            if isinstance(sec, dict) and isinstance(sec.get('total'), (int, float)):
                seconds += float(sec['total'])
            if r.get('ok'):
                nvalid += 1
                best = min(best, float(r['objective']))
                if nvalid in (18, 24, 50, 100, 150, 192):
                    curve[str(nvalid)] = {'best_j': best, 'attempts': attempts,
                                          'candidate_seconds': round(seconds, 1)}
        traj[name] = {'valid': nvalid, 'final_best_j': best, 'best_so_far': curve}
    sens = json.loads(SENS_COMMITTED.read_text(encoding='utf-8'))
    proposals = [{'subset': p.get('subset'), 'pool_seed': p.get('pool_seed'),
                  'geometry_hash': p.get('geometry_hash'),
                  'predicted_j_mean': (p.get('predicted') or {}).get('j_mean'),
                  'predicted_j_interval': [(p.get('predicted') or {}).get('j_lower'),
                                           (p.get('predicted') or {}).get('j_upper')]}
                 for p in sens.get('proposals', [])]
    rerun = json.loads(SENS_RERUN.read_text(encoding='utf-8'))
    same = sum(1 for a, b in zip(sens['proposals'], rerun['proposals'])
               if a.get('geometry_hash') == b.get('geometry_hash'))
    report['cma_and_bo'] = {
        'cma_trajectories': traj,
        'cma_seed_spread_at_18_valid': abs(traj['d37d64']['best_so_far']['18']['best_j']
                                           - traj['46b68c']['best_so_far']['18']['best_j']),
        'bo_proposals_predicted_only': proposals,
        'bo_measured_outcomes': 'none - no BO proposal has been solved; BO benefit is unmeasured',
        'sensitivity_rerun_identical_proposals': f'{same}/{len(sens["proposals"])}',
    }


def _finish(report):
    report['input_sha256'] = hashes
    out = OUT / 'm2_gate_diagnostics.json'
    out.write_text(json.dumps(report, indent=1, default=float), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('strict_group_heldout', 'group_recovery')}, indent=1))
    print('wrote', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
