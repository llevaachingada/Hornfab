import yaml

from tools.analysis.queue_score_audit import ROOT, audit


def test_resolves_registered_task_and_brief_overrides_inline(tmp_path):
    queue = tmp_path / 'queue.yaml'
    queue.write_text(yaml.safe_dump({'jobs': [
        {'id': 'old', 'argv': ['run', '--task', 'p80x60__ext_throat_corelaw_v7']},
        {'id': 'trit', 'argv': ['run', '--config',
          'examples/typologies/home_landscape_2026-11-15/hl__ath_tritonia_landscape_v8.yaml']},
        {'id': 'package', 'argv': ['run', '--package', 'package.json']},
    ]}), encoding='utf-8')
    old, trit, package = audit(queue, ROOT)['jobs']
    assert old['status'] == trit['status'] == 'resolved'
    assert old['score']['target']['coverage_v_deg'] == 60
    assert trit['score']['target']['coverage_v_deg'] == 50
    assert trit['score']['weights']['dislope'] == 1
    assert len(trit['config_sha256']) == len(trit['score_fingerprint_sha256']) == 64
    assert old['score_fingerprint_sha256'] != trit['score_fingerprint_sha256']
    assert package['status'] == 'indirect_or_non_scoring'


def test_unknown_task_is_explicitly_unresolved(tmp_path):
    queue = tmp_path / 'queue.yaml'
    queue.write_text(yaml.safe_dump({'jobs': [{'id': 'unknown', 'argv': ['--task', 'no-such-task']}]}),
                     encoding='utf-8')
    row = audit(queue, ROOT)['jobs'][0]
    assert row['status'] == 'unresolved'
    assert 'unknown task identity' in row['reason']
