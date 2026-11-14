"""Task intake preserves source files and separates solve policy groups."""
import json
import numpy as np
from test_replay_v7_study import CONFIG, record
from hornlab_search.config import load_config
from tools.analysis.study_cohort import prepare


def test_intake_uses_real_v7_replay_and_separates_dependencies(tmp_path):
    dataset = tmp_path / 'dataset'
    dataset.mkdir()
    array_root = dataset / 'shard-0000'
    array_root.mkdir()
    cfg = load_config(CONFIG)
    lines = []
    for i in range(3):
        _, meta, arrays, _ = record()
        meta.update(config_name=cfg.name, run_id='run', family='OSSE',
                    lib_shas={'hornlab_beat_bem': 'a' if i < 2 else 'b'},
                    provenance={'config': cfg.name, 'brief_hash': 'brief'},
                    solve={'mode': 'screen', 'backend': cfg.solve.backend, 'freqs_hz': [500, 8000]})
        lines.append(json.dumps(meta) + '\n')
        np.savez(array_root / f'rec-{i:04d}.npz', **arrays)
    source = dataset / 'shard-0000.jsonl'
    source.write_text(''.join(lines), encoding='utf-8')
    before = source.read_bytes()
    result = prepare(CONFIG, dataset, tmp_path / 'out')
    assert result['counts'] == {'exact_complete': 2}
    assert result['selection']['group_count'] == 2
    assert result['selection']['excluded']['other_dependency_grid_brief_groups'] == 1
    assert source.read_bytes() == before
    scores = json.loads((tmp_path / 'out/offline_scores.json').read_text())
    assert scores['brief']['objective_version'] == 7
    assert scores['no_backend_calls'] is True
    import csv
    with (tmp_path / 'out/catalog.csv').open(encoding='utf-8') as handle:
        assert {r['root'] for r in csv.DictReader(handle)} == {'dataset'}
