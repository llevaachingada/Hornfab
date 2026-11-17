"""Read-only: exact term arithmetic using the repo's own term functions for one stored row."""
import pickle, pathlib, json, sys
import numpy as np
sys.path.insert(0, r'C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp')
import fable_replay_harness as H
from hornlab_search.objective import scalar_v1 as v1
from hornlab_search.objective.scalar_v4 import _cov_term, V4Params
from hornlab_search.metrics.di import target_di_gaussian_db

REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
rows = [r for r in pickle.load(open(REPO / 'scratch/fable_architecture/.fable/rows.pkl', 'rb')) if r['ok']]
r = rows[0]
b = H.landscape_brief()
target = b.target
f = np.asarray(r['f'], float)
band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz)
print('band n', band.sum(), 'terms n_in_band', r['terms']['n_in_band'])
from hornlab_search.types import MetricSet
m = MetricSet(freqs_hz=f, bw_h_deg=np.asarray(r['bwh'], float), bw_v_deg=np.asarray(r['bwv'], float),
              di_db=np.asarray(r['di'], float), on_axis_db=np.full(f.size, np.nan),
              ripple_h_db=np.full(f.size, np.nan), ripple_v_db=np.full(f.size, np.nan))
print('v1 cov_term', v1.cov_term(m.bw_h_deg[band], m.bw_v_deg[band], target))
for ratio in (1.0, 2.0):
    for cvw in (1.0, 0.5):
        p = V4Params(tolerances={}, cov_narrow_ratio=ratio, cov_below_f0='mask', cov_v_weight=cvw)
        try:
            print('v4 cov ratio', ratio, 'cvw', cvw, _cov_term(m, target, f, band, p))
        except Exception as e:
            print('v4 err', e)
print('di exact-band', np.mean((m.di_db[band] - target_di_gaussian_db(80, 50)) ** 2) / 10)
print('di all', np.mean((m.di_db - target_di_gaussian_db(80, 50)) ** 2) / 10)
print('stored terms cov/di', r['terms']['cov'], r['terms']['di'])
print('target', target)
print('params block', json.dumps(b.objective_params)[:600] if hasattr(b, 'objective_params') else None)
