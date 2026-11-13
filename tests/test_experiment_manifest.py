"""Offline tests for preparation-only experiment manifests."""
import copy

import pytest

from tools.experiments.manifest import parse_results, prepare, validate


def test_frozen_task_and_preparation_blockers():
    manifest = prepare()
    assert manifest['status'] == 'preparation_blocked'
    assert manifest['execution_authorized'] is False
    assert manifest['task']['objective_version'] == 4
    assert len(manifest['task']['config_sha256']) == 64
    assert len(manifest['task']['brief_sha256']) == 64
    assert len(manifest['pilots']) == 2
    assert any('threshold' in item for item in validate(manifest))
    for pilot in manifest['pilots']:
        assert len({pair['cma_seed'] for pair in pilot['pairs']}) == 5
        assert pilot['pairs'][0]['order'] != pilot['pairs'][1]['order']


def test_validation_rejects_duplicate_replicates_and_bad_budgets():
    manifest = copy.deepcopy(prepare())
    pilot = manifest['pilots'][0]
    pilot['pairs'][1]['cma_seed'] = pilot['pairs'][0]['cma_seed']
    pilot['budget']['calls_per_arm'] = float('nan')
    errors = validate(manifest)
    assert any('unique integer seeds' in e for e in errors)
    assert any('calls_per_arm' in e for e in errors)


def test_results_preserve_failure_and_unknown_without_fabricated_j():
    rows = [{'status': 'complete', 'verified_j': 2.4},
            {'status': 'physical_refusal', 'verified_j': None},
            {'status': 'infrastructure_failure'}, {'status': 'unknown'}]
    assert parse_results(rows) == rows
    with pytest.raises(ValueError):
        parse_results([{'status': 'unknown', 'verified_j': 1000}])
    with pytest.raises(ValueError):
        parse_results([{'status': 'complete', 'verified_j': float('nan')}])
