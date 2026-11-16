from types import SimpleNamespace
import json

import numpy as np
import pytest

from hornlab_search.types import Design
from tools.night_queue.run_matched_home import selected_rows
from tools.night_queue import run_matched_home as comparison


def fixture_training():
    ids = [f'p{i}' for i in range(100)]
    metas = {}
    identities = {}
    for i, oid in enumerate(ids):
        params = {'a': float(i)}
        design_hash = Design('OSSE', params).hash()
        metas[i] = {'ok': True, 'params': params, 'family': 'OSSE', 'design_hash': design_hash}
        identities[oid] = {'shard': 1, 'row': i, 'J': float(i), 'design_hash': design_hash}
    # A scored but unselected row in the source must never appear in CMA's input.
    metas[100] = {'ok': True, 'params': {'a': -1}, 'family': 'OSSE', 'design_hash': 'excluded'}
    tr = SimpleNamespace(status='ok', n=100, selected_ids=ids, ids=ids,
                         J=np.arange(100, dtype=float), meta={'identities': identities})
    return tr, metas


def test_reconstructs_only_selected_rows():
    tr, metas = fixture_training()
    rows = selected_rows(tr, 'dataset', lambda root, shard, cache: metas)
    assert len(rows) == 100
    assert {row['physical_id'] for row in rows} == set(tr.selected_ids)
    assert all(row['design_hash'] != 'excluded' for row in rows)


@pytest.mark.parametrize('change', ['hash', 'score', 'missing'])
def test_refuses_changed_selected_evidence(change):
    tr, metas = fixture_training()
    if change == 'hash':
        metas[0]['params']['a'] = 500
    elif change == 'score':
        tr.meta['identities']['p0']['J'] = 500
    else:
        del metas[0]
    with pytest.raises(ValueError):
        selected_rows(tr, 'dataset', lambda root, shard, cache: metas)


@pytest.mark.parametrize('raises', [False, True])
def test_arm_records_wall_time_and_failure(tmp_path, monkeypatch, raises):
    monkeypatch.setattr(comparison, 'check', lambda root: {})
    def run(*args):
        if raises:
            raise ValueError('deliberate failure')
        return 7
    monkeypatch.setattr(comparison, 'execute_arm', run)
    if raises:
        with pytest.raises(ValueError):
            comparison.arm(tmp_path, 'cma', 88101)
    else:
        assert comparison.arm(tmp_path, 'cma', 88101) == 7
    status = json.loads((tmp_path / 'cma_88101/arm_status.json').read_text())
    assert status['elapsed_seconds'] >= 0
    assert status['started_utc'] and status['ended_utc']
    assert status['state'] == ('exception' if raises else 'ended')
    assert status['returncode'] == (None if raises else 7)


def test_report_keeps_failed_arm_visible_without_run(tmp_path, monkeypatch):
    monkeypatch.setattr(comparison, 'check', lambda root: {'best': {'J': 3.0}})
    (tmp_path / 'manifest.json').write_text('{}')
    arm = tmp_path / 'cma_88101'
    arm.mkdir()
    (arm / 'arm_status.json').write_text(json.dumps({'state': 'ended', 'returncode': 7}))
    comparison.report(tmp_path)
    result = json.loads((tmp_path / 'report.json').read_text())
    assert result['arms'][0]['status'] == 'arm_failed'
    assert result['arms'][1]['status'] == 'not_started'
