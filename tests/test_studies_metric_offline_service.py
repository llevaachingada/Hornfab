"""Study-service intake provenance and reuse gates; no solver is invoked."""
import pytest

from hornlab_search.studies import metric_intake, metric_study
from hornlab_search.studies.schema import Unavailable
from test_studies_metric import _study
from test_bo_policy_metric import _identity, _pool, _selection


def test_offline_service_binds_provenance_and_rechecks_before_reuse(tmp_path, monkeypatch):
    service, sid = _study(tmp_path)
    calls = []
    def select(intake, *, snapshot):
        calls.append(intake['catalog']['sha256'])
        if intake['catalog']['sha256'] == 'changed-on-disk':
            raise Unavailable('catalog sha256 mismatch')
        return _selection(), _identity()
    monkeypatch.setattr(metric_intake, 'select_offline_metric_cohort', select)
    intake = {'catalog': {'path': 'catalog.csv', 'sha256': 'first'}}
    first = metric_study.build_metric_training(service, sid, root=tmp_path, offline_intake=intake)
    assert not first['idempotent']
    manifest = metric_study._json(service, sid, metric_study.METRIC_TRAINING_MANIFEST_KIND)
    assert manifest['synthetic'] is False
    assert manifest['offline_intake'] == intake
    assert metric_study.build_metric_training(service, sid, root=tmp_path,
                                             offline_intake=intake)['idempotent']
    assert calls == ['first', 'first']
    with pytest.raises(Unavailable, match='different offline intake provenance'):
        metric_study.build_metric_training(service, sid, root=tmp_path,
                                           offline_intake={'catalog': {'path': 'other', 'sha256': 'first'}})
    with pytest.raises(Unavailable, match='catalog sha256 mismatch'):
        metric_study.build_metric_training(service, sid, root=tmp_path,
                                           offline_intake={'catalog': {'sha256': 'changed-on-disk'}})
    with pytest.raises(Unavailable, match='different offline intake provenance'):
        metric_study.build_metric_training(service, sid, root=tmp_path)


def test_offline_selection_cannot_be_mixed_with_explicit_selection(tmp_path):
    service, sid = _study(tmp_path)
    with pytest.raises(Unavailable, match='cannot be combined'):
        metric_study.build_metric_training(service, sid, root=tmp_path,
                                           offline_intake={}, selection=_selection())


def test_offline_provenance_reaches_the_proposal_and_blocks_synthetic_packaging(tmp_path, monkeypatch):
    service, sid = _study(tmp_path)
    monkeypatch.setattr(metric_intake, 'select_offline_metric_cohort',
                        lambda intake, *, snapshot: (_selection(), _identity()))
    metric_study.build_metric_training(service, sid, root=tmp_path, offline_intake={})
    metric_study.build_metric_model(service, sid, root=tmp_path)
    metric_study.build_metric_pool(service, sid, root=tmp_path, pool=_pool(n=10))
    metric_study.build_metric_proposal(service, sid, root=tmp_path)
    for kind in ('model', 'pool', 'proposal'):
        assert metric_study._json(service, sid, kind)['synthetic'] is False
    assert metric_study.metric_bindings(service, sid)['synthetic'] is False
    with pytest.raises(Unavailable, match='requires the offline metric package'):
        metric_study.prepare_metric_run_package(service, sid)
