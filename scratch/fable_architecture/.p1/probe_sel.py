"""Read-only: selection_reason from attempt candidate_json, per study arm."""
import sqlite3, pathlib, json, collections

REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
arms = [p.parent for p in sorted((REPO / 'runs').rglob('studies.sqlite3')) if p.parent.name != 'studies']
for arm in arms:
    db = arm / 'studies.sqlite3'
    con = sqlite3.connect('file:' + str(db.resolve()) + '?mode=ro', uri=True)
    try:
        attempts = list(con.execute('select id, kind, candidate_json, status from attempts'))
        if not attempts:
            continue
        sel = collections.Counter()
        kinds = collections.Counter()
        for _id, kind, cj, status in attempts:
            c = json.loads(cj)
            sel[c.get('selection_reason', '<missing>')] += 1
            kinds[kind] += 1
        print(arm.parent.name + '/' + arm.name, dict(kinds))
        print('   ', dict(sel))
    finally:
        con.close()
