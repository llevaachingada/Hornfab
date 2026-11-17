"""P1 step 7 (unbiased-pool count) and stopping rule.

Counts, per lane/config, the stored solved designs that were NOT chosen by an optimizer:
  strict   : unconditional initial Sobol / pool rows solved without any selection rule  -> 0
  generous : proposals whose documented selection_reason is model-free 'exploration'
             (maximin over a Sobol pool, no J/GP acquisition); recorded where the arm stored it,
             otherwise an upper bound from the frozen every-fourth-proposal cadence.
Also inventories the CMA runs: every run config uses algorithm cma/cma_me, so every run row is
optimizer-visited.
"""
import sqlite3, pathlib, json, sys, collections, yaml
REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
OUT = REPO / 'scratch/fable_architecture/.p1'
sys.path.insert(0, str(REPO))
from hornlab_search.studies import builders

# ---- CMA run inventory: there are no non-CMA run rows
algos = collections.Counter()
for p in (REPO / 'runs').rglob('config.yaml'):
    try:
        c = yaml.safe_load(p.read_text())
    except Exception:
        continue
    if isinstance(c, dict):
        algos[str((c.get('search') or {}).get('algorithm', 'cma'))] += 1

arms = []
for p in sorted((REPO / 'runs').rglob('studies.sqlite3')):
    arm = p.parent
    if arm.name == 'studies':
        continue
    con = sqlite3.connect('file:' + str(p.resolve()) + '?mode=ro', uri=True)
    try:
        row = con.execute('select spec_json from revisions order by revision desc limit 1').fetchone()
        if not row:
            continue
        spec = json.loads(row[0])
        task = spec.get('task') or {}
        if 'name' in task:
            entry = builders._TASK_REGISTRY.get(task['name'])
            cfg = str(entry['config']) if entry else None
        else:
            cfg = task.get('config')
        lane = None
        if cfg and pathlib.Path(cfg).is_file():
            try:
                lane = yaml.safe_load(pathlib.Path(cfg).read_text()).get('name')
            except Exception:
                lane = None
        nobs = con.execute('select count(*) from observations').fetchone()[0]
        attempts = list(con.execute('select id, kind, candidate_json, result_json from attempts'))
        if nobs == 0 and not attempts:
            continue
        sel = collections.Counter()
        for _id, kind, cj, rj in attempts:
            c = json.loads(cj) if cj else {}
            sel[str(c.get('selection_reason'))] += 1
        nscreen = sum(1 for a in attempts if a[1] == 'screen')
        n_acq = int(sel.get('acquisition', 0)) + int(sel.get('trust_region_acquisition', 0))
        n_exp = int(sel.get('exploration', 0))
        n_unrec = int(sel.get('None', 0)) + int(sel.get('<missing>', 0))
        # pool size from the initial proposal artifact, where present
        pool = None
        for kind, sha in con.execute("select kind, sha256 from artifacts where kind in ('proposal','pool')"):
            f = arm / 'artifacts' / sha
            if not f.is_file():
                continue
            try:
                d = json.loads(f.read_text())
            except Exception:
                continue
            if kind == 'proposal':
                acq = d.get('acquisition') or {}
                if 'n_candidates' in acq:
                    pool = acq.get('n_candidates')
        arms.append({'arm': f'{arm.parent.name}/{arm.name}', 'lane': lane,
                     'observations': int(nobs), 'screen_attempts': int(nscreen),
                     'recorded_acquisition': n_acq, 'recorded_exploration': n_exp,
                     'unrecorded': n_unrec, 'pool_candidates': pool,
                     'selection_counts': dict(sel)})
    finally:
        con.close()

# lane aggregation
lanes = collections.defaultdict(lambda: {'observations': 0, 'recorded_exploration': 0,
                                         'recorded_acquisition': 0, 'unrecorded': 0,
                                         'arms': [], 'strict_unbiased': 0,
                                         'upper_bound_model_free': 0})
for a in arms:
    l = lanes[a['lane']]
    l['observations'] += a['observations']
    l['recorded_exploration'] += a['recorded_exploration']
    l['recorded_acquisition'] += a['recorded_acquisition']
    l['unrecorded'] += a['unrecorded']
    l['arms'].append(a['arm'])
    # frozen cadence: every fourth 0-based proposal index is the maximin exploration arm
    l['upper_bound_model_free'] += a['recorded_exploration'] + (a['unrecorded'] + 3) // 4

stop = {k: v['upper_bound_model_free'] for k, v in lanes.items() if v['upper_bound_model_free'] < 30}
res = {'cma_run_algorithms': dict(algos), 'arms': arms,
       'lanes': {k: dict(v) for k, v in lanes.items()},
       'lanes_with_fewer_than_30_unbiased': stop,
       'stop_condition_fired': bool(stop),
       'strict_unbiased_total': 0}
(OUT / 'fairpool.json').write_text(json.dumps(res, indent=1))

print('run algorithms:', dict(algos))
print('\nARM TABLE')
for a in arms:
    print('%-46s lane=%-38s obs=%3d screens=%3d acq=%3d exp=%3d unrec=%3d pool=%s' % (
        a['arm'], str(a['lane']), a['observations'], a['screen_attempts'],
        a['recorded_acquisition'], a['recorded_exploration'], a['unrecorded'], a['pool_candidates']))
print('\nLANE TABLE (strict unbiased = 0 everywhere)')
for k, v in sorted(lanes.items()):
    print('%-42s obs=%3d exp_recorded=%3d upper_bound=%3d arms=%d' % (
        k, v['observations'], v['recorded_exploration'], v['upper_bound_model_free'], len(v['arms'])))
print('\nlanes with a generous upper bound < 30:', len(stop), 'of', len(lanes))
