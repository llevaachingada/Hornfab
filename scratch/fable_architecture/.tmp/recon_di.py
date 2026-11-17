import json, numpy as np, sys
sys.path.insert(0, r'C:\Users\hunte\Hrns\hornlab-search')
from hornlab_search.solve.cache import load_response
from hornlab_search.metrics.di import di_from_balloon, sin_theta_weights

p = r'C:\Users\hunte\Hrns\hornlab-search\runs\study-0c9805ad97208a2e\screen\designs\3f6533769704'
m = json.load(open(p + r'\metrics.json'))
r = load_response(p + r'\response.npz')
d = r.balloon_dirs
theta = np.degrees(np.arccos(np.clip(d[:, 2], -1, 1)))
ax = np.argmin(abs(r.h_angles_deg))
stored = np.asarray(m['di_db'], float)
di_eq = np.array([di_from_balloon(r.spl_balloon_db[i], r.spl_h_db[i, ax]) for i in range(len(r.freqs_hz))])
w = sin_theta_weights(theta)
di_w = np.array([di_from_balloon(r.spl_balloon_db[i], r.spl_h_db[i, ax], w) for i in range(len(r.freqs_hz))])
print('eq diff', np.round(stored - di_eq, 4)[:6])
print('wt diff', np.round(stored - di_w, 4)[:6])
print('max wt diff', np.nanmax(abs(stored - di_w)))
print('theta range', theta.min(), theta.max(), 'unique', len(np.unique(np.round(theta, 4))))
# test alternative axis: maybe spl_h axis index or on-axis interpolation
print('axis angle', r.h_angles_deg[ax])
print('dirs first5', d[:5])
print('n per theta', np.unique(np.round(theta, 3), return_counts=True)[0][:10])
