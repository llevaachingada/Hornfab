import sys, numpy as np
sys.path.insert(0, r'C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp')
import fable_replay_harness as H

S = H.REPO/'runs/study-e312cd2d498983d8'
vd = S/'verify'; b = H.brief(S/'screen'/'config.yaml')
h = sorted(p.name for p in (vd/'designs').iterdir() if p.is_dir())[0]
rv = H.load_response(vd/'designs'/h/'response.npz')
def score(resp, method):
    m = H.metrics_parity(resp, b.target)
    return H.score_v7(m, resp, b.target, b.weights, b.objective_params)
for method in ('pchip','rational_pressure'):
    base = H.interp_response(rv, H.GRID_58, method=method)
    jb, tb = score(base, method)
    print(method, 'full29 J', jb, 'n_nan', tb.get('n_nan'), 'penalty', tb.get('penalty'))
    for n in (8,10,12,15,18,22):
        idx = H.select_log_spaced(rv.freqs_hz, n)
        sub = H.dataclasses.replace(rv)
        kw = dict(freqs_hz=rv.freqs_hz[idx])
        for name in ('spl_h_db','spl_v_db','spl_balloon_db','z_throat','p_h','p_v','p_balloon'):
            v = getattr(rv, name); kw[name] = None if v is None else np.asarray(v)[idx]
        sub = H.dataclasses.replace(rv, **kw)
        r58 = H.interp_response(sub, H.GRID_58, method=method)
        j, t = score(r58, method)
        print('  n', n, 'J %.4f' % j, 'dJ %+.4f' % (j-jb), 'n_nan', t.get('n_nan'), 'penalty', t.get('penalty'),
              'terms', {k: round(t.get(k),3) for k in ('cov','rip','di','dislope','flat','load','distd','diag','flat_cv')})
