"""Probe: does the brief-target replay of a 46b68c row differ only because the stored target
carries driver_exit_radius_mm? Read-only; zero backend calls."""
import dataclasses, json, sys
from pathlib import Path
import numpy as np
REPO = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(REPO))
from hornlab_search.objective import replay
from hornlab_search.targets.spec import Target
brief = replay.load_brief_context(REPO / 'examples/briefs/campaign_2026-10-26_v4/native_ath_core_2in_v4.yaml')
def load(shard, row):
    with open(REPO / f'dataset/shard-{shard:04d}.jsonl', encoding='utf-8') as f:
        for i, l in enumerate(f):
            if i == row: meta = json.loads(l); break
    npz = REPO / f'dataset/shard-{shard:04d}/rec-{row:04d}.npz'
    with np.load(npz, allow_pickle=False) as z: arrays = {k: z[k] for k in z.files}
    return meta, arrays
out = {}
for label, (s, r) in {'new_46b68c': (57, 387), 'old_d37d64': (37, 356)}.items():
    meta, arrays = load(s, r)
    a = replay.replay_record(meta, arrays, brief=brief)
    t_with = dataclasses.replace(brief.target, driver_exit_radius_mm=25.4)
    b = replay.replay_record(meta, arrays, brief=brief, target=t_with)
    m2 = dict(meta); m2['target'] = {k: v for k, v in meta['target'].items() if k != 'driver_exit_radius_mm'}
    c = replay.replay_record(m2, arrays, brief=brief)
    out[label] = {'stored_j': meta.get('objective'),
                  'brief_target': [a.j, a.metric_source, a.to_dict()['diagnostics'].get('target_changed')],
                  'brief_target_plus_radius': [b.j, b.metric_source, b.to_dict()['diagnostics'].get('target_changed')],
                  'stored_target_without_radius': [c.j, c.metric_source],
                  'brief_terms': a.to_dict()['terms'], 'stored_terms': meta.get('terms')}
print(json.dumps(out, indent=1, default=str))
