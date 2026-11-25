"""Offline metric package is hash-bound and never grants execution authority."""
import copy
import pytest

from hornlab_search.studies.package import (REAL_DATA_OFFLINE, package_hash, verify_package,
    prepare_real_data_offline_metric_package)
from hornlab_search.studies.metric_study import metric_execution_gate
from hornlab_search.studies.schema import StudyError, Unavailable, digest
from test_studies_metric import _stages


def _offline(package):
    p = copy.deepcopy(package)
    source = {'config': {'sha256': 'a' * 64}, 'shards': {'0': {'sha256': 'b' * 64}}}
    p['metric'].update(provenance_mode=REAL_DATA_OFFLINE, synthetic=False,
        source_provenance=source, source_provenance_sha256=digest(source))
    p['artifacts']['metric_training'] = p['metric']['training_artifact_sha256']
    p['artifacts']['metric_training_manifest'] = p['metric']['training_manifest_sha256']
    p['package_id'] = package_hash(p)
    return p


def test_offline_shape_hash_and_execution_gate(tmp_path):
    p = _offline(_stages(tmp_path)['package'])
    assert verify_package(p) == p
    assert metric_execution_gate(p, allow_real_solver=True)['status'] == 'refused'
    assert metric_execution_gate(p, synthetic_evaluator=lambda *a: None)['status'] == 'refused'
    p['metric']['source_provenance']['config']['sha256'] = 'f' * 64
    with pytest.raises(Unavailable, match='hash mismatch'):
        verify_package(p)
    p['package_id'] = package_hash(p)
    with pytest.raises(StudyError, match='provenance hash mismatch'):
        verify_package(p)


@pytest.mark.parametrize('mutation', ['mode', 'allowed', 'manifest', 'policy', 'pins'])
def test_offline_malformed_blocks_refuse_even_with_new_package_hash(tmp_path, mutation):
    p = _offline(_stages(tmp_path)['package'])
    if mutation == 'mode': p['metric']['provenance_mode'] = 'other'
    if mutation == 'allowed': p['metric']['real_solver_allowed'] = True
    if mutation == 'manifest': p['metric']['training_manifest_sha256'] = '0' * 64
    if mutation == 'policy': p['proposal_policy']['policy'] = 'scalar'
    if mutation == 'pins': p['dependency_pins'] = {}
    p['package_id'] = package_hash(p)
    with pytest.raises(StudyError): verify_package(p)


def test_synthetic_artifact_cannot_be_relabelled_offline(tmp_path):
    stages = _stages(tmp_path)
    with pytest.raises(Unavailable, match='offline intake provenance unavailable'):
        prepare_real_data_offline_metric_package(stages['service'], stages['sid'])
