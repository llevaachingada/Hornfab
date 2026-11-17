import sqlite3, pathlib, json
REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
p = REPO / 'runs/bo_multityp_2026-11-16/bo_ath14_s71002/studies.sqlite3'
con = sqlite3.connect('file:' + str(p.resolve()) + '?mode=ro', uri=True)
for _id, kind, cj, rj in con.execute('select id, kind, candidate_json, result_json from attempts'):
    c = json.loads(cj)
    if c.get('selection_reason') is None:
        print('None row:', kind, c.get('candidate_id'), c.get('design_hash'))
        print(json.dumps({k: c.get(k) for k in ('acquisition', 'selection_reason', 'trust_region', 'predicted', 'status')}, indent=1)[:800])
con.close()
