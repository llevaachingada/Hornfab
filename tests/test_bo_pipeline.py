"""B2/B3 evidence boundary; synthetic rows and no solver."""
from copy import deepcopy
from types import SimpleNamespace

from hornlab_search.bo.pipeline import fit_validated_cohort
from test_bo_cohort_gate import row


def _rows(n=16):
    rows = [row(i) for i in range(n)]
    for i, item in enumerate(rows):
        item['x'] = [i / max(1, n - 1), .3]
    return rows


def test_validated_rows_reach_fitter_with_frozen_selection_and_policy():
    calls = []
    def fake(training, model_policy, seed):
        calls.append((training, model_policy, seed))
        return SimpleNamespace(status='ok', reason='ok')
    result = fit_validated_cohort(_rows(20), d=2, seed=42, _fit=fake)
    assert result.status == 'ok'
    training, policy, seed = calls[0]
    assert policy == 'scalar_pool_v1' and seed == 42
    assert training.n == 20 and training.ids == result.training.selected_ids
    assert all(y == -j for y, j in zip(training.Y[:, 0], training.J[:, 0]))
    assert len(result.policy_identity) > 0


def test_missing_or_mixed_evidence_never_reaches_fitter():
    def never(*args, **kwargs):
        raise AssertionError('fitter must not be called')
    rows = _rows()
    del rows[0]['policy']['frequency_masks']
    assert fit_validated_cohort(rows, d=2, _fit=never).status == 'capability_missing'
    rows = _rows()
    rows[-1]['policy']['frequency_masks']['value'] = 'different'
    assert fit_validated_cohort(rows, d=2, _fit=never).status == 'incompatible'
    rows = _rows()
    rows[0]['replay']['status'] = 'partial_unsupported'
    assert fit_validated_cohort(rows, d=2, _fit=never).status == 'incompatible'


def test_insufficient_data_refuses_fit_and_preserves_diagnostics():
    result = fit_validated_cohort(_rows(15), d=2, _fit=lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    assert result.status == 'needs_initial_data'
    assert result.training.n_unique == 15 and result.training.preparation


def test_failed_model_is_tagged_and_selected_ids_preserved():
    result = fit_validated_cohort(_rows(), d=2,
        _fit=lambda *a, **k: SimpleNamespace(status='unavailable', reason='capability_missing'))
    assert result.status == 'unavailable' and result.reasons == ('capability_missing',)
    assert len(result.training.selected_ids) == 16
