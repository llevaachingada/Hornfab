"""Read-only probe #2: study events / attempts / observations provenance."""
import sqlite3, pathlib, json, collections

p = pathlib.Path(r'runs/bo_vs_cma_2026-11-15/bo_s31001/studies.sqlite3')
con = sqlite3.connect('file:' + str(p.resolve()) + '?mode=ro', uri=True)
print('events kinds', collections.Counter(r[0] for r in con.execute('select kind from events')))
for seq, kind, payload in con.execute('select seq, kind, payload_json from events order by seq limit 40'):
    print(seq, kind, payload[:300])
print('--- attempts ---')
for r in con.execute('select id, kind, candidate_json, status, result_json from attempts order by rowid limit 8'):
    print(json.dumps({'id': r[0], 'kind': r[1], 'cand': r[2][:400], 'status': r[3], 'result': (r[4] or '')[:300]}, indent=1))
print('attempt kinds', collections.Counter(r[0] for r in con.execute('select kind from attempts')))
print('candidate keys', [r[0] for r in con.execute('select candidate_json from attempts limit 1')][0][:1200])
print('--- observations ---')
for r in con.execute('select observation_seq, attempt_id, physical_id, score_id from observations order by observation_seq limit 10'):
    print(r)
print('observations n', con.execute('select count(*) from observations').fetchone()[0])
print('--- package budget ---')
pk = con.execute('select package_json from packages').fetchone()[0]
d = json.loads(pk)
print(json.dumps({k: d[k] for k in d if k in ('budget', 'adaptive_policy', 'proposal_policy', 'execution_mode', 'resolved_config', 'verification_policy')}, indent=1)[:2000])
print('--- revision spec ---')
spec = json.loads(con.execute('select spec_json from revisions limit 1').fetchone()[0])
print(json.dumps(spec, indent=1)[:2500])
con.close()
