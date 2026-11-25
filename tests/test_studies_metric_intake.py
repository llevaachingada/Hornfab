"""Offline metric intake refuses missing, modified and mismatched pinned inputs."""
import hashlib

import pytest

from hornlab_search.studies.metric_intake import _pinned_file, select_offline_metric_cohort
from hornlab_search.studies.schema import Unavailable


def test_pinned_file_checks_bytes_and_requires_hash(tmp_path):
    path = tmp_path / 'source'
    path.write_bytes(b'original')
    pin = {'path': str(path), 'sha256': hashlib.sha256(b'original').hexdigest()}
    assert _pinned_file(pin, 'source')[1] == b'original'
    path.write_bytes(b'modified')
    with pytest.raises(Unavailable, match='sha256 mismatch'):
        _pinned_file(pin, 'source')
    with pytest.raises(Unavailable, match='path and sha256'):
        _pinned_file({'path': str(path)}, 'source')


def test_intake_rejects_config_not_bound_to_snapshot(tmp_path):
    path = tmp_path / 'config'
    path.write_bytes(b'config')
    pin = {'path': str(path), 'sha256': hashlib.sha256(b'config').hexdigest()}
    intake = {'config': pin, 'catalog': pin, 'replay': pin}
    snapshot = {'task': {'config': str(tmp_path / 'other'), 'config_sha256': pin['sha256']}}
    with pytest.raises(Unavailable, match='config differs from frozen snapshot path'):
        select_offline_metric_cohort(intake, snapshot=snapshot)
