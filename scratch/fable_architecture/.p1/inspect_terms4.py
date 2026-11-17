"""Read-only: exact cov/di terms via the repo term functions on a stored metric row."""
import pickle, pathlib, sys
import numpy as np
sys.path.insert(0, r'C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp')
import fable_replay_harness as H
from hornlab_search.types import MetricSet
from hornlab_search.objective.scalar_v4 import _cov_term
from hornlab_search.objective.scalar_v2 import _objective_v2

REPO = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
rows = [r for r in pickle.load(open(REPO / 'scratch/fable_architecture/.fable/rows.pkl', 'rb')) if r['ok']]
b = H.landscape_brief()
params = b.objective_params
print('cov_v_weight', params.cov_v_weight, 'ratio', params.cov_narrow_ratio, 'below', params.cov_below_f0)
for r in rows[:12]:
    f = np.asarray(r['f'], float)
    band = (f >= b.target.band_lo_hz) & (f <= b.target.band_hi_hz)
    m = MetricSet(freqs_hz=f, bw_h_deg=np.asarray(r['bwh'], float), bw_v_deg=np.asarray(r['bwv'], float),
                  di_db=np.asarray(r['di'], float), di_source='balloon',
                  ripple_h_db=np.full(f.size, np.nan), ripple_v_db=np.full(f.size, np.nan),
                  on_axis_db=np.full(f.size, np.nan), z_throat_real=None)
    c = _cov_term(m, b.target, f, band, params)
    _, t2 = _objective_v2(m, None, True, b.target, b.weights)
    print(r['config'], '| cov', round(c, 3), 'stored', round(r['terms']['cov'], 3),
          '| di', round(t2['di'], 3), 'stored', round(r['terms']['di'], 3))
