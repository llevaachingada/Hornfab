"""Read-only probe of BoTorch study sqlite packages (no writes)."""
import sqlite3, pathlib, json, sys

paths = [
    r'runs/bo_vs_cma_2026-11-15/bo_s31001/studies.sqlite3',
    r'runs/bo_multityp_2026-11-16/bo_cov_s71001/studies.sqlite3',
]
for p in paths:
    pp = pathlib.Path(p)
    print('===', p, pp.is_file(), pp.stat().st_size if pp.is_file() else None)
    if not pp.is_file():
        continue
    con = sqlite3.connect('file:' + str(pp.resolve()) + '?mode=ro', uri=True)
    tabs = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
    print('tables', tabs)
    for t in tabs:
        cols = [r[1] for r in con.execute('pragma table_info(%s)' % t)]
        n = con.execute('select count(*) from %s' % t).fetchone()[0]
        print(' ', t, 'n', n, 'cols', cols)
    con.close()
