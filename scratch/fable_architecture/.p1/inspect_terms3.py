"""Read-only: exact cov/di terms via objective_v7 on a stored metric row (no regeneration)."""
import pickle, pathlib, json, sys
import numpy as np
sys.path.insert(0, r'C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp')
import fable_replay_harness as H
from hornlab_search.types import MetricSet
from hornlab_search.objective.scalar_v7 import V7Params, objective_v7

REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
rows = [r for r in pickle.load(open(REPO / 'scratch/fable_architecture/.fable/rows.pkl', 'rb')) if r['ok']]
b = H.landscape_brief()
params = V7Params.from_block(b.objective_params)
print('params', params)
print('weights', b.weights)
bad = 0
for r in rows[:20]:
    f = np.asarray(r['f'], float)
    m = MetricSet(freqs_hz=f, bw_h_deg=np.asarray(r['bwh'], float), bw_v_deg=np.asarray(r['bwv'], float),
                  di_db=np.asarray(r['di'], float), di_source='balloon',
                  ripple_h_db=np.full(f.size, np.nan), ripple_v_db=np.full(f.size, np.nan),
                  on_axis_db=np.full(f.size, np.nan), z_throat_real=None)
    J, t = objective_v7(m, None, True, b.target, b.weights, params)
    print(r['config'], 'J', round(J, 3), 'stored', round(r['J'], 3), '| cov', round(t['cov'], 3),
          round(r['terms']['cov'], 3), '| di', round(t['di'], 3), round(r['terms']['di'], 3))
    if abs(t['cov'] - r['terms']['cov']) > 0.03 or abs(t['di'] - r['terms']['di']) > 0.03:
        bad += 1
print('bad', bad, 'of 20')
