import json,pathlib
root=pathlib.Path('scratch/fable_architecture'); data=json.load(open(root/'.x5/lineage.json'))
lines=['# Run lineage evidence','', 'First-row matches are to a best design observed strictly before the run, within numerical parameter tolerance or with the same design hash. A match supports continuity; it does not prove the historical authoring mechanism. No match means origin unknown, not necessarily a hand-written seed. Explicit warm-start fields are reported separately.','', '| Run | Config | Brief | First J | Earlier best match | Warm start |','|---|---|---|---:|---|---|']
for r in data:
    matches='; '.join(m['config']+' / '+m['run']+(' (same lane)' if m['same_config'] else ' (cross-lane)')+(' within 0.17' if m['within_noise'] else '') for m in r['matches']) or 'unknown'
    warm=', '.join(r['warm_start'].get('from_runs',[])) if r['warm_start'] else 'none declared'
    lines.append(f"| {r['run']} | {r['config']} | {r['brief']} | {r['first_J'] if r['first_J'] is not None else 'invalid'} | {matches} | {warm} |")
(root/'.x5/lineage.md').write_text('\n'.join(lines)+'\n',encoding='utf8'); print('wrote',len(data),'runs')
