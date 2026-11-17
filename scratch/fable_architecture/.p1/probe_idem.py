"""Read-only: recover per-proposal selection_reason from the idempotency/response records."""
import sqlite3, pathlib, json, collections
REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
for name in ['bo_vs_cma_2026-11-15/bo_s31001', 'home_landscape_d_2026-11-15/turbo_s62001_rerun']:
    p = REPO / 'runs' / name / 'studies.sqlite3'
    con = sqlite3.connect('file:' + str(p.resolve()) + '?mode=ro', uri=True)
    print('==', name)
    print('idem scopes', collections.Counter(r[0] for r in con.execute('select scope from idempotency')))
    rows = list(con.execute('select scope, key, response_json from idempotency'))
    sr = collections.Counter()
    n = 0
    for scope, key, resp in rows:
        try:
            d = json.loads(resp)
        except Exception:
            continue
        if isinstance(d, dict) and ('selection_reason' in d or 'candidate' in d):
            n += 1
            sr[str(d.get('selection_reason'))] += 1
    print('responses with proposal shape', n, dict(sr))
    print('sample key', rows[0][1] if rows else None)
    con.close()
