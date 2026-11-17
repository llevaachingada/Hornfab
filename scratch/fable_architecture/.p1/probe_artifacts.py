import sqlite3, pathlib, json
REPO = pathlib.Path('runs')
for arm in ['bo_multityp_2026-11-16/bo_cov_s71001',
            'bo_multityp_2026-11-16/bo_ath14_s71002',
            'home_landscape_d_2026-11-15/pareto_s63001',
            'bo_vs_cma_2026-11-15/bo_s31002']:
    p = REPO / arm / 'studies.sqlite3'
    con = sqlite3.connect('file:' + str(p.resolve()) + '?mode=ro', uri=True)
    print('==', arm)
    for kind, sha in con.execute("select kind, sha256 from artifacts where kind in ('proposal','pool','model')"):
        f = REPO / arm / 'artifacts' / sha
        if not f.is_file():
            print('  missing', kind)
            continue
        try:
            d = json.loads(f.read_text())
        except Exception as e:
            print('  bad', kind, e)
            continue
        acq = d.get('acquisition') or {}
        print('  %-8s sel=%s acq_value=%s n_cand=%s keys=%s' % (
            kind, d.get('selection_reason'), acq.get('value'), acq.get('n_candidates'),
            sorted(d.keys())[:8]))
    con.close()
