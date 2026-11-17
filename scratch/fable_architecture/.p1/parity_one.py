"""Read-only: parity-check one stored landscape screen row through the harness; print the exact
target, objective params and regenerated terms against the stored terms."""
import sys, pathlib, json, pickle
import numpy as np
sys.path.insert(0, r'C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp')
import fable_replay_harness as H

REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
rows = [r for r in pickle.load(open(REPO / 'scratch/fable_architecture/.fable/rows.pkl', 'rb')) if r['ok']]
r = rows[0]
print('row', r['run'], r['h'], r['config'], 'stored J', r['J'])
print('stored terms', json.dumps(r['terms'], indent=1))
b = H.landscape_brief()
print('brief object', type(b), sorted(b.__dict__.keys()) if hasattr(b, '__dict__') else b)
t = getattr(b, 'target', None)
print('target', t)
print('weights', getattr(b, 'weights', None))
print('params', getattr(b, 'params', None))
resp = H.resp_from_run(REPO / 'runs' / r['run'], r['h'])
m = H.metrics_parity(resp, t)
print('regenerated cov-ish? di', np.asarray(m.di_db)[:5], 'bwh', np.asarray(m.bw_h_deg)[:5])
res = H.replay_exact_v7(REPO / 'runs' / r['run'], r['h'], brief_obj=b, regenerate_metrics=True)
print('replay result fields', type(res), getattr(res, '__dict__', {}).keys() if hasattr(res, '__dict__') else '')
print('replay', res)
