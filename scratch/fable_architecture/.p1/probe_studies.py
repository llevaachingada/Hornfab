"""Read-only: classify study attempt selection provenance (no design-dir search)."""
import sqlite3, pathlib, json, collections

REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
arms = [p.parent for p in sorted((REPO / 'runs').rglob('studies.sqlite3')) if p.parent.name != 'studies']
for arm in arms:
    db = arm / 'studies.sqlite3'
    con = sqlite3.connect('file:' + str(db.resolve()) + '?mode=ro', uri=True)
    try:
        attempts = list(con.execute('select id, kind, candidate_json, status, result_json from attempts'))
        obs = list(con.execute('select observation_seq, attempt_id from observations'))
        if not attempts:
            print(arm.parent.name + '/' + arm.name, 'NO ATTEMPTS')
            continue
        cand = json.loads(attempts[0][2])
        res = json.loads(attempts[0][4]) if attempts[0][4] else {}
        sr = collections.Counter()
        for a in attempts:
            try:
                r = json.loads(a[4]) if a[4] else {}
            except Exception:
                r = {}
            sr[(r.get('selection_reason') or '')] += 1
        kinds = collections.Counter(a[1] for a in attempts)
        statuses = collections.Counter(a[3] for a in attempts)
        print('==', arm.parent.name + '/' + arm.name, '| attempts', len(attempts), dict(kinds), dict(statuses), '| obs', len(obs))
        print('   sel', dict(sr))
        print('   cand keys', sorted(cand.keys()))
        print('   res keys', sorted(res.keys()))
        print('   first candidate_ids', [json.loads(a[2]).get('candidate_id') for a in attempts[:4]])
    finally:
        con.close()
