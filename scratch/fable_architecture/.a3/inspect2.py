"""A3: lane/config/response inspection. Read-only."""
import pathlib, pickle, collections, time, json, sys
import numpy as np

ROOT = pathlib.Path('scratch/fable_architecture')
sys.path.insert(0, str((ROOT / '.tmp').resolve()))
import fable_replay_harness as H

rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
data, _ = pickle.load(open(ROOT / '.e1/descriptors.pkl', 'rb'))
lanes = [g for g, n in collections.Counter(r['config'] for r, _, _ in data if r['brief'] == 'cd').items() if n >= 100]
print('lanes', lanes)
cache = {}
for g in lanes:
    r = next(r for r, _, _ in data if r['config'] == g)
    bp = pathlib.Path('runs') / r['run'] / 'config.yaml'
    b = cache.setdefault(str(bp), H.brief(bp))
    p = pathlib.Path('runs') / r['run'] / 'designs' / r['h'] / 'response.npz'
    z = np.load(p)
    print()
    print('LANE', g, 'brief', r['brief'], 'run', r['run'], 'n', sum(1 for x, _, _ in data if x['config'] == g))
    print('  config', bp)
    print('  objective_version', b.objective_version, 'params', type(b.objective_params).__name__)
    print('  weights', {k: v for k, v in b.weights.items() if v})
    print('  block', b.objective_block)
    t = b.target
    print('  target band', t.band_lo_hz, t.band_hi_hz, 'f0', t.f0_effective_hz(), 'f0v', t.f0_v_hz, 'cov', t.coverage_h_deg, t.coverage_v_deg)
    print('  coverage_profile', getattr(t, 'coverage_profile', None))
    print('  freq_weights', t.freq_weights)
    print('  resp keys', z.files)
    print('  spl_h', z['spl_h_db'].shape, 'spl_v', z['spl_v_db'].shape, 'balloon', z['spl_balloon_db'].shape if 'spl_balloon_db' in z else None,
          'z', z['z_throat'].shape if 'z_throat' in z else None, 'ndirs', z['balloon_dirs'].shape if 'balloon_dirs' in z else None)
    print('  freqs', z['freqs_hz'])
    print('  h_angles', z['h_angles_deg'])
    print('  v_angles', z['v_angles_deg'])
    print('  stored J', r['J'], 'nrows', sum(1 for x in rows if x['config'] == g and x['ok']))
    print('  terms keys', sorted(r['terms']))
