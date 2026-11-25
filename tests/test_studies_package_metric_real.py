"""Real-metric package contract: opt-in, task-approved, and never implied.

All fixtures are synthetic (a real StudyService, a real metric-training artifact built from an
explicit selection, a real CPU GP fit, a real proposal).  The approvals record is a temp file
resolved through an injected root.  No mesh, BEM/GPU, pipeline, dataset or queue call is made.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from hornlab_search.bo import metric_identity
from hornlab_search.studies import metric_intake, metric_study, package as package_mod
from hornlab_search.studies.package import (
    BUDGET_PROFILES,
    METRIC_APPROVALS_SCHEMA,
    REAL_METRIC,
    prepare_real_metric_package,
    verify_package,
    verify_real_metric_package_files,
)
from hornlab_search.studies.schema import Conflict, NotFound, StudyError, Unavailable, digest
from test_bo_policy_metric import _identity, _pool, _selection
from test_studies_metric import _study

TASK_IDENTITY = '82dbd04691c7b456'
BRIEF_HASH = 'c6bc496e7b4f'
SCORE_HASH = '77d4fdd49bd2c3b4'
DEEP_TASK = {
    'task_identity': TASK_IDENTITY,
    'backend': 'beat_cuda',
    'fidelity': 'screen',
    'grid_hash': 'c41ff9a7581ba429',
    'dependency_hash': 'f4dcdca807bdfad0',
    'mesh_hash': '8e789cd0deef',
}


def _deadline(hours=2):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


#: A stable future deadline keeps repeated preparation byte-identical (idempotency evidence).
FUTURE_DEADLINE = '2099-01-01T00:00:00Z'


def _pin(path):
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def _write(tmp_path, name, text):
    path = tmp_path / 'intake' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def _real_identity():
    meta = dict(_identity())
    payload = metric_identity.score_payload(
        objective_version=int(meta['objective_version']), brief_hash=BRIEF_HASH,
        score_hash=SCORE_HASH)
    meta.update(DEEP_TASK)
    meta.update(brief_hash=BRIEF_HASH, score_hash=SCORE_HASH,
                score_identity_payload=payload,
                score_identity=metric_identity.recompute_score_hash(payload))
    return meta


def _real_stages(tmp_path, monkeypatch):
    service, sid = _study(tmp_path)
    meta = _real_identity()
    monkeypatch.setattr(metric_intake, 'select_offline_metric_cohort',
                        lambda intake, *, snapshot: (_selection(), meta))
    config = _write(tmp_path, 'config.yaml', 'config: pinned\n')
    brief = _write(tmp_path, 'brief.yaml', 'brief: pinned\n')
    catalog = _write(tmp_path, 'catalog.csv', 'id,j\n0,1\n')
    replay = _write(tmp_path, 'offline_scores.json', '{"rows": []}\n')
    shard = _write(tmp_path, 'shard-0000.jsonl', '{"row": 0}\n')
    intake = {
        'config': _pin(config), 'brief': _pin(brief), 'catalog': _pin(catalog),
        'replay': _pin(replay), 'shards': {'0': _pin(shard)},
        'identity': {**DEEP_TASK, 'brief_hash': BRIEF_HASH, 'score_hash': SCORE_HASH},
    }
    metric_study.build_metric_training(service, sid, root=tmp_path, offline_intake=intake)
    metric_study.build_metric_model(service, sid, root=tmp_path, seed=0)
    metric_study.build_metric_pool(service, sid, root=tmp_path, pool=_pool(n=10))
    metric_study.build_metric_proposal(service, sid, root=tmp_path, seed=0)
    manifest = metric_study._json(service, sid, metric_study.METRIC_TRAINING_MANIFEST_KIND)
    return {'service': service, 'sid': sid, 'manifest': manifest, 'intake': intake}


def _approval_identity(stages):
    manifest = stages['manifest']
    score = manifest['score']['payload']
    return {
        **{key: manifest['task'][key] for key in
           ('task_identity', 'backend', 'fidelity', 'grid_hash', 'dependency_hash', 'mesh_hash')},
        'brief_hash': score['brief_hash'],
        'score_hash': score['score_hash'],
    }


def _approval_record(tmp_path, stages, *, profile='metric-canary-8x2',
                     status='APPROVED_FOR_CANARY', **overrides):
    manifest = stages['manifest']
    caps = BUDGET_PROFILES[profile]
    record = {
        'schema': METRIC_APPROVALS_SCHEMA,
        'status': status,
        'profile': profile,
        'task_identity': manifest['task']['task_identity'],
        'artifact_sha256': manifest['checksum'],
        'screen_cap': caps['screen_calls'],
        'verify_cap': caps['verify_calls'],
        'refit_every': 4,
        'lane': 'gpu',
        'identity': _approval_identity(stages),
        'owner_authorization': {'authorized': True, 'by': 'test-owner'},
    }
    record.update(overrides)
    path = tmp_path / 'approvals' / 'canary.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding='utf-8')
    return 'approvals/canary.json'


def _prepare(stages, record, tmp_path, **kwargs):
    options = {
        'approvals_record': record,
        'budget_profile': 'metric-canary-8x2',
        'lane': 'gpu',
        'deadline': FUTURE_DEADLINE,
        'dependency_pins': {'hornlab_mesher': 'a' * 64, 'hornlab_beat_bem': 'b' * 64},
        'approvals_root': tmp_path,
    }
    options.update(kwargs)
    return prepare_real_metric_package(stages['service'], stages['sid'], **options)


def test_real_metric_package_roundtrip_and_plan(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages)
    package = _prepare(stages, record, tmp_path)

    assert package['metric']['provenance_mode'] == REAL_METRIC
    assert package['metric']['synthetic'] is False
    assert package['metric']['real_solver_allowed'] is True
    assert package['metric']['approvals'] == {
        'record': record,
        'task_identity': TASK_IDENTITY,
        'artifact_sha256': stages['manifest']['checksum'],
        'screen_cap': 8,
        'verify_cap': 2,
        'refit_every': 4,
    }
    assert package['budget'] == BUDGET_PROFILES['metric-canary-8x2']
    assert package['budget_profile'] == 'metric-canary-8x2'
    assert package['lane'] == 'gpu'
    assert package['proposal_policy']['policy'] == 'metric_composite_v1'
    assert package['code_pins'] and package['dependency_pins']
    assert package['resolved_config']['interpreter']['executable']
    assert package['resolved_config']['config']['path']
    assert package['resolved_config']['brief']['path']
    assert package['metric']['training_checksum'] == stages['manifest']['checksum']
    assert verify_package(package) is package

    evidence = verify_real_metric_package_files(package, root=tmp_path)
    assert evidence['status'] == 'ok'
    assert evidence['approvals']['status'] == 'APPROVED_FOR_CANARY'
    assert evidence['approvals']['profile'] == 'metric-canary-8x2'

    # The package is published at its own content address and is idempotent on re-prepare.
    metadata = stages['service'].get_artifact_metadata(stages['sid'], package_mod.PACKAGE_KIND)
    assert metadata['sha256'] == package['package_id']
    repeated = _prepare(stages, record, tmp_path)
    assert repeated['package_id'] == package['package_id']
    assert repeated == package


def test_tampered_training_artifact_is_refused(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages)
    package = _prepare(stages, record, tmp_path)
    training_sha = stages['service'].get_artifact_metadata(
        stages['sid'], metric_study.METRIC_TRAINING_KIND)['sha256']
    blob = stages['service'].store.read_artifact(training_sha)
    (stages['service'].store.artifacts / training_sha).write_bytes(blob + b' ')
    with pytest.raises(Unavailable):
        _prepare(stages, record, tmp_path, idempotency_key='tampered')


def test_stale_absent_revision_and_missing_study(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages)
    with pytest.raises(Conflict):
        _prepare(stages, record, tmp_path, expected_revision=2)
    with pytest.raises(StudyError):
        _prepare(stages, record, tmp_path, expected_revision=0)
    with pytest.raises(NotFound):
        prepare_real_metric_package(stages['service'], 'missing', approvals_record=record,
                                    budget_profile='metric-canary-8x2', lane='gpu',
                                    deadline=_deadline(), approvals_root=tmp_path)


def test_changed_config_brief_and_budget_profile_are_refused(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages)

    changed = json.loads((tmp_path / record).read_text(encoding='utf-8'))
    changed['identity']['brief_hash'] = 'f' * 12
    (tmp_path / record).write_text(json.dumps(changed), encoding='utf-8')
    with pytest.raises(Unavailable):
        _prepare(stages, record, tmp_path)
    _approval_record(tmp_path, stages)

    # Changing an actually pinned intake file is refused even with a fresh package hash.
    intake = stages['intake']
    from pathlib import Path
    Path(intake['config']['path']).write_text('config: changed\n', encoding='utf-8')
    with pytest.raises(Unavailable, match='config sha256 mismatch'):
        _prepare(stages, record, tmp_path)

    # A profile whose caps differ from the approval record is refused.
    with pytest.raises(StudyError):
        _prepare(stages, record, tmp_path, budget_profile='metric-adaptive-30x2')


def test_wrong_policy_and_mixed_provenance_are_refused(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages)
    package = _prepare(stages, record, tmp_path)

    forged = json.loads(json.dumps(package))
    forged['proposal_policy']['policy'] = 'scalar'
    forged['package_id'] = package_mod.package_hash(forged)
    with pytest.raises(StudyError):
        verify_package(forged)

    forged = json.loads(json.dumps(package))
    forged['metric']['policy'] = 'scalar'
    forged['package_id'] = package_mod.package_hash(forged)
    with pytest.raises(StudyError):
        verify_package(forged)

    forged = json.loads(json.dumps(package))
    forged['metric']['synthetic'] = True
    forged['package_id'] = package_mod.package_hash(forged)
    with pytest.raises(StudyError):
        verify_package(forged)

    forged = json.loads(json.dumps(package))
    forged['metric']['provenance_mode'] = 'other'
    forged['package_id'] = package_mod.package_hash(forged)
    with pytest.raises(StudyError):
        verify_package(forged)


def test_missing_or_mismatched_approvals_are_refused(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    with pytest.raises(Unavailable, match='cannot be read'):
        _prepare(stages, 'approvals/missing.json', tmp_path)

    record = _approval_record(
        tmp_path, stages, task_identity='0' * 16,
        identity={**_approval_identity(stages), 'task_identity': '0' * 16})
    with pytest.raises(Unavailable, match='task_identity'):
        _prepare(stages, record, tmp_path)

    record = _approval_record(tmp_path, stages, artifact_sha256='f' * 64)
    with pytest.raises(Unavailable, match='artifact_sha256'):
        _prepare(stages, record, tmp_path)

    record = _approval_record(tmp_path, stages, screen_cap=9)
    with pytest.raises(StudyError):
        _prepare(stages, record, tmp_path)

    record = _approval_record(tmp_path, stages, refit_every=5)
    with pytest.raises(StudyError):
        _prepare(stages, record, tmp_path)

def test_adaptive_profile_requires_an_accepted_canary(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages, profile='metric-adaptive-30x2')
    with pytest.raises(StudyError, match='accepted canary'):
        _prepare(stages, record, tmp_path, budget_profile='metric-adaptive-30x2')

    record = _approval_record(
        tmp_path, stages, profile='metric-adaptive-30x2',
        canary_acceptance={'accepted': True, 'canary_package_id': 'a' * 64,
                           'accepted_by': 'parent'})
    package = _prepare(stages, record, tmp_path, budget_profile='metric-adaptive-30x2',
                       idempotency_key='adaptive')
    assert package['budget'] == BUDGET_PROFILES['metric-adaptive-30x2']
    assert package['metric']['approvals']['screen_cap'] == 30
    assert package['metric']['approvals']['verify_cap'] == 2


def test_lane_and_deadline_refusals(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages)
    with pytest.raises(StudyError, match='gpu lane'):
        _prepare(stages, record, tmp_path, lane='cpu')
    with pytest.raises(StudyError, match='timezone-aware'):
        _prepare(stages, record, tmp_path, deadline='2099-01-01T00:00:00')
    with pytest.raises(StudyError, match='future'):
        _prepare(stages, record, tmp_path, deadline='2000-01-01T00:00:00+00:00')
    with pytest.raises(StudyError, match='deadline'):
        _prepare(stages, record, tmp_path, deadline=None)


def test_forged_real_package_deadline_and_lane_fail_closed(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages)
    package = _prepare(stages, record, tmp_path)
    for field, value in (('deadline', None), ('deadline', '2099-01-01T00:00:00'),
                         ('deadline', '2000-01-01T00:00:00+00:00'),
                         ('lane', 'cpu')):
        forged = json.loads(json.dumps(package))
        forged[field] = value
        forged['package_id'] = package_mod.package_hash(forged)
        with pytest.raises(StudyError):
            verify_package(forged)


def test_duplicate_prepare_is_idempotent_or_refused(tmp_path, monkeypatch):
    stages = _real_stages(tmp_path, monkeypatch)
    record = _approval_record(tmp_path, stages)
    first = _prepare(stages, record, tmp_path)
    second = _prepare(stages, record, tmp_path)
    assert first == second
    with pytest.raises(Conflict):
        # A different idempotency key for the same revision/kind must not duplicate silently.
        _prepare(stages, record, tmp_path, idempotency_key='duplicate')
    with stages['service'].store.connect() as conn:
        rows = conn.execute('SELECT COUNT(*) FROM artifacts WHERE kind=?',
                            (package_mod.PACKAGE_KIND,)).fetchone()[0]
    assert rows == 1


def test_dependency_pins_accept_archived_git_shas_and_refuse_unknown(tmp_path, monkeypatch):
    """The archived package carries 40-hex ``direct_url.json`` git SHAs, not sha256."""
    archived = {
        'hornlab_mesher': '55da4f46d662d8dcd7a9f94a609eeea4009fcd62',
        'hornlab_beat_bem': '38e5b1f8ca840ebf6351c54611a08fedb1a0750f',
        'hornlab_bempp_bem': '8e6910602ece9abb2e9ce0db7a637f4bedf17f53',
        'hornlab_plots': '9e4a6d0dd2ccb6e735dd00233dccccb50d12ed44',
    }
    git_root = tmp_path / 'git'
    git_stages = _real_stages(git_root, monkeypatch)
    package = _prepare(git_stages, _approval_record(git_root, git_stages), git_root,
                       dependency_pins=archived)
    assert package['dependency_pins'] == archived
    assert all(len(value) == 40 for value in package['dependency_pins'].values())

    sha_root = tmp_path / 'sha'
    sha_stages = _real_stages(sha_root, monkeypatch)
    sha256_pins = {key: hashlib.sha256(key.encode()).hexdigest() for key in archived}
    package = _prepare(sha_stages, _approval_record(sha_root, sha_stages), sha_root,
                       dependency_pins=sha256_pins)
    assert package['dependency_pins'] == sha256_pins

    record = _approval_record(git_root, git_stages)
    for mutation in ('unknown', 'UPPER', 'short', 'nondigest'):
        pins = dict(archived)
        pins['hornlab_beat_bem'] = {
            'unknown': 'unknown',
            'UPPER': 'A' * 40,
            'short': 'a' * 39,
            'nondigest': 'z' * 40,
        }[mutation]
        with pytest.raises(StudyError, match='dependency pin'):
            _prepare(git_stages, record, git_root, dependency_pins=pins,
                     idempotency_key='bad-' + mutation)
