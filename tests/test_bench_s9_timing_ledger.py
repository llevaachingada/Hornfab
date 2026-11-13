from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.bench.timing_ledger import summarize


def test_overlapping_timing_and_unknown_verification(tmp_path):
    rows = [
        {'stage': 'candidate_total', 'seconds': 8},
        {'stage': 'mesh_prefetch', 'seconds': 4},
        {'stage': 'solve', 'seconds': 5},
        {'stage': 'solver_path', 'seconds': 0, 'timings': {'assembly': 3, 'solve': 2}},
        {'stage': 'candidate_total', 'seconds': 6},
    ]
    (tmp_path / 'stages.ndjson').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    manifest = {'elapsed_s': 10, 'stage_files': ['stages.ndjson'], 'attempts': [
        {'cache': 'new', 'outcome': 'physical_solve', 'thermal': 'cold', 'verified_useful': True},
        {'cache': 'hit', 'outcome': 'refusal', 'thermal': 'warm', 'verified_useful': None},
    ]}
    result = summarize(manifest, tmp_path)
    assert result['stage_seconds']['candidate_total'] == 14
    assert result['candidate_total_minus_elapsed_s'] == 4
    assert result['nested_solver_seconds'] == {'assembly': 3, 'solve': 2}
    assert result['counts']['outcome:refusal'] == 1
    assert result['verified_useful_per_hour'] is None
    manifest['attempts'][1]['verified_useful'] = False
    assert summarize(manifest, tmp_path)['verified_useful_per_hour'] == 360


def test_invalid_duration_refused(tmp_path):
    with pytest.raises(ValueError):
        summarize({'elapsed_s': 0}, tmp_path)
    (tmp_path / 'bad').write_text('{"stage":"solve","seconds":-1}\n')
    with pytest.raises(ValueError):
        summarize({'elapsed_s': 1, 'stage_files': ['bad']}, tmp_path)


def test_cli_fake_manifest(tmp_path):
    manifest = {'source': 'synthetic', 'elapsed_s': 20, 'stage_files': [],
                'identity': {'spec_hash': 'fixture', 'lib_shas': {'beat': 'fixture'}},
                'attempts': [{'cache': 'new', 'outcome': 'failed_solve', 'thermal': 'warm',
                              'verified_useful': False}], 'overhead_seconds': {'training': 2}}
    p = tmp_path / 'manifest.json'
    p.write_text(json.dumps(manifest))
    script = Path(__file__).resolve().parents[1] / 'tools/bench/timing_ledger.py'
    result = subprocess.run([sys.executable, str(script), str(p)], capture_output=True, text=True, check=True)
    out = json.loads(result.stdout)
    assert out['source'] == 'synthetic' and out['verified_useful_per_hour'] == 0
    assert out['counts']['outcome:failed_solve'] == 1 and out['overhead_seconds']['training'] == 2
