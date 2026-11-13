"""Fake-only, no backend tests for M2 diagnostics."""
import json

import numpy as np

from tools.analysis.bo_sensitivity import run_diagnostics


def _input(n=30):
    return dict(X=np.column_stack((np.linspace(0, 1, n), np.full(n, .4))),
                J=np.linspace(1, 5, n), ids=[f'id-{i}' for i in range(n)],
                groups=[f'group-{i // 3}' for i in range(n)],
                cohort_ids=['same'] * n, validation_evidence_id='fixture-only')


def _fit(x, j, ids, noise):
    return {'mean': float(j.mean()), 'ids': ids, 'noise': noise}


def _predict(model, x):
    return np.full(len(x), model['mean'])


def _propose(model, seed):
    return {'geometry_hash': f'fake-{seed}'}


def test_missing_evidence_and_callbacks_report_capability_missing():
    result = run_diagnostics()
    assert result['reason_code'] == 'capability_missing'
    assert result['gate_pass'] is None
    assert result['simple_cma_comparison']['status'] == 'unmeasured'
    assert run_diagnostics(**_input())['status'] == 'unavailable'


def test_grouped_holdout_callbacks_only_receive_training_and_all_variations():
    data = _input()
    result = run_diagnostics(**data, fit=_fit, predict=_predict, propose=_propose,
                             max_train=16, all_data_limit=30, split_seed=7)
    assert result['status'] == 'complete_diagnostics'
    assert result['gate_pass'] is None
    assert result['simple_cma_comparison']['status'] == 'unmeasured'
    assert len(result['results']) == 5 * 3 * 3
    for fold in result['folds']:
        assert set(fold['held_out_ids']).isdisjoint(fold['training_ids'])
        groups = {data['groups'][data['ids'].index(i)] for i in fold['training_ids']}
        assert groups.isdisjoint(fold['held_out_groups'])
    for cell in result['results']:
        fold = result['folds'][cell['fold']]
        assert set(cell['train_ids']) <= set(fold['training_ids'])
        assert cell['noise_multiplier'] in (0.1, 1.0, 10.0)
        assert cell['same_proposal_geometry'] is False
    assert result == run_diagnostics(**data, fit=_fit, predict=_predict, propose=_propose,
                                     max_train=16, all_data_limit=30, split_seed=7)
    json.dumps(result, allow_nan=False)


def test_mixed_cohorts_and_insufficient_group_links_refuse():
    data = _input()
    data['cohort_ids'][0] = 'other'
    assert run_diagnostics(**data, fit=_fit, predict=_predict, propose=_propose)['status'] == 'unavailable'
    data = _input()
    data['groups'] = ['unknown'] * 30
    assert run_diagnostics(**data, fit=_fit, predict=_predict, propose=_propose)['status'] == 'unavailable'


def test_failure_and_unmeasured_all_data_are_explicit():
    def broken(*args):
        raise RuntimeError('engine unavailable')
    result = run_diagnostics(**_input(), fit=broken, predict=_predict, propose=_propose,
                             max_train=16)
    assert result['status'] == 'partial'
    assert all(r['status'] == 'unavailable' and 'engine unavailable' in r['reason'] for r in result['results'])
    assert any('all-training comparison unavailable' in note for note in result['limitations'])
