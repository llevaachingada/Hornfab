"""Read-only: verify cov via v7 internals (tolerance-normalised) on a stored row."""
import pickle, pathlib, sys
import numpy as np
sys.path.insert(0, r'C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp')
import fable_replay_harness as H
from hornlab_search.types import MetricSet
from hornlab_search.objective.scalar_v7 import _cov_term_v5, _objective_v3
from hornlab_search.objective.scalar_v2 import _objective_v2

REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
rows = [r for r in pickle.load(open(REPO / 'scratch/fable_architecture/.fable/rows.pkl', 'rb')) if r['ok']]
b = H.landscape_brief()
P = b.objective_params
print('tol cov', P.tolerances['cov'], 'tol di', P.tolerances['di'])
bad = 0
for r in rows[:60]:
    f = np.asarray(r['f'], float)
    band = (f >= b.target.band_lo_hz) & (f <= b.target.band_hi_hz)
    m = MetricSet(freqs_hz=f, bw_h_deg=np.asarray(r['bwh'], float), bw_v_deg=np.asarray(r['bwv'], float),
                  di_db=np.asarray(r['di'], float), di_source='balloon',
                  ripple_h_db=np.full(f.size, np.nan), ripple_v_db=np.full(f.size, np.nan),
                  on_axis_db=np.full(f.size, np.nan), z_throat_real=None)
    cov_s = _cov_term_v5(m, None, b.target, f, band, P) / P.tolerances['cov']
    _, t2 = _objective_v2(m, None, True, b.target, b.weights)
    di_s = t2['di'] / P.tolerances['di']
    d1, d2 = abs(cov_s - r['terms']['cov']), abs(di_s - r['terms']['di'])
    if d1 > 0.02 or d2 > 0.02:
        bad += 1
        if bad <= 6:
            print('BAD', r['config'], 'cov', round(cov_s, 3), r['terms']['cov'], 'di', round(di_s, 3), r['terms']['di'])
print('bad', bad, 'of 60')
