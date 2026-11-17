import sys, numpy as np
sys.path.insert(0, r'C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp')
import fable_replay_harness as H

# pick one study verify response
S = H.REPO/'runs/study-e312cd2d498983d8'
h = sorted(p.name for p in (S/'verify/designs').iterdir() if p.is_dir())[0]
resp = H.load_response(S/'verify/designs'/h/'response.npz')
f = resp.freqs_hz
print('design', h, 'nf', len(f))

# test FH on a smooth complex function first
t = np.linspace(-1, 1, 29)
y = np.exp(2j*np.pi*t) * (1 + 0.1*t)
for d in (1,2,3,4):
    yy = H.fh_interp_columns(t, y[:,None], np.linspace(-1,1,200), d=d)[:,0]
    print('FH d', d, 'max err smooth', np.max(np.abs(yy - np.exp(2j*np.pi*np.linspace(-1,1,200))*(1+0.1*np.linspace(-1,1,200)))))

# real data: compare rational vs pchip SPL on 58 grid, per d
grid = H.GRID_58
x = np.log(f); xn = np.log(grid)
pchip = H.interp_response(resp, grid, method='pchip')
print('pchip spl_h range', np.nanmin(pchip.spl_h_db), np.nanmax(pchip.spl_h_db))
for d in (1,2,3,4):
    ph = H.fh_interp_columns(x, resp.p_h, xn, d=d)
    spl = H.spl_from_pressure(ph)
    print('d', d, 'spl_h range', np.nanmin(spl), np.nanmax(spl),
          'max |spl-pchip|', np.nanmax(np.abs(spl - pchip.spl_h_db)),
          'median |diff|', np.nanmedian(np.abs(spl - pchip.spl_h_db)))
    # per-column max error location
    err = np.abs(spl - pchip.spl_h_db)
    i, j = np.unravel_index(np.nanargmax(err), err.shape)
    print('   worst at f', grid[i], 'angle', resp.h_angles_deg[j], 'err', err[i,j], 'pchip', pchip.spl_h_db[i,j], 'rat', spl[i,j])
