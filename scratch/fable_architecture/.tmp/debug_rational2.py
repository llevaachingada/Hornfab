import sys, numpy as np
sys.path.insert(0, r'C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp')
import fable_replay_harness as H

S = H.REPO/'runs/study-e312cd2d498983d8'
h = sorted(p.name for p in (S/'verify/designs').iterdir() if p.is_dir())[0]
resp = H.load_response(S/'verify/designs'/h/'response.npz')
f = resp.freqs_hz
grid = H.GRID_58
pchip = H.interp_response(resp, grid, method='pchip')
for label, x, xn in (('log', np.log(f), np.log(grid)), ('linear-f', f, grid), ('log10', np.log10(f), np.log10(grid))):
    for d in (2, 3):
        ph = H.fh_interp_columns(x, resp.p_h, xn, d=d)
        spl = H.spl_from_pressure(ph)
        print(label, 'd', d, 'max', np.nanmax(np.abs(spl-pchip.spl_h_db)), 'median', np.nanmedian(np.abs(spl-pchip.spl_h_db)))
# also test a 6-point smooth region only: angles near 0
ax = np.argmin(abs(resp.h_angles_deg))
for label, x, xn in (('log', np.log(f), np.log(grid)), ('linear-f', f, grid)):
    ph = H.fh_interp_columns(x, resp.p_h[:, ax:ax+1], xn, d=3)[:,0]
    spl = H.spl_from_pressure(ph)
    print(label, 'axis col max', np.nanmax(np.abs(spl-pchip.spl_h_db[:,ax])), 'median', np.nanmedian(np.abs(spl-pchip.spl_h_db[:,ax])))
