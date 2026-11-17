import sys, numpy as np
sys.path.insert(0, r'C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp')
import fable_replay_harness as H

# 1) pressure -> SPL parity
d = H.REPO/'runs/study-e312cd2d498983d8/verify/designs'
h = sorted(p.name for p in d.iterdir() if p.is_dir())[0]
resp = H.load_response(d/h/'response.npz')
print('design', h)
print('max |spl_from_pressure(p_h)-spl_h_db|', np.nanmax(np.abs(H.spl_from_pressure(resp.p_h) - resp.spl_h_db)))
print('max |spl_from_pressure(p_v)-spl_v_db|', np.nanmax(np.abs(H.spl_from_pressure(resp.p_v) - resp.spl_v_db)))
print('max |spl_from_pressure(p_balloon)-spl_balloon_db|', np.nanmax(np.abs(H.spl_from_pressure(resp.p_balloon) - resp.spl_balloon_db)) if resp.p_balloon is not None else 'no p_balloon')
print('freqs', np.round(resp.freqs_hz, 1))

# 2) interpolate at nodes: both methods should reproduce stored arrays
grid = resp.freqs_hz
r1 = H.interp_response(resp, grid, method='pchip')
r2 = H.interp_response(resp, grid, method='rational_pressure')
print('pchip spl err', np.nanmax(np.abs(r1.spl_h_db-resp.spl_h_db)))
print('rational spl err', np.nanmax(np.abs(r2.spl_h_db-resp.spl_h_db)))
# 3) subsample selection check: how log-uniform is verify grid
f = resp.freqs_hz
print('log spacing diffs (octaves)', np.round(np.diff(np.log2(f)), 3))
for n in (8,10,12,15,18,22):
    idx = np.unique(np.round(np.linspace(0, len(f)-1, n)).astype(int))
    print('n', n, 'picked', len(idx), 'first/last', f[idx[0]], f[idx[-1]], 'log gaps oct', np.round(np.diff(np.log2(f[idx])),2))
