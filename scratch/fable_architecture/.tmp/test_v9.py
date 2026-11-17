import sys, json, copy, numpy as np
sys.path.insert(0, r'C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp')
import fable_replay_harness as H
from hornlab_search.objective.scalar_v9 import V9Params, resolve_v9_weights, objective_v9
from hornlab_search.objective.scalar_v7 import V7Params

b = H.landscape_brief()
print('v7 target', b.target)
print('v7 weights', b.weights)
print('v7 params', b.objective_params)

target_dict = {
    'coverage_h_deg': 80.0, 'coverage_v_deg': 50.0, 'band_lo_hz': 350.0, 'band_hi_hz': 8000.0,
    'di_target_db': None, 'di_slope_target': 0.0, 'z_min': 0.5, 'f0_hz': 700.0, 'f0_v_hz': 700.0,
    'loaded_hi_hz': 5600.0, 'freq_weights': {'band_hz': [[2500.0, 5500.0, 2.0]]},
    'coverage_profile': {
        'mode': 'corridor', 'interpolation': 'log_frequency',
        'h': [{'hz': 700, 'preferred_deg': 80, 'min_deg': 60, 'max_deg': 90},
              {'hz': 8000, 'preferred_deg': 80, 'min_deg': 60, 'max_deg': 90}],
        'v': [{'hz': 1000, 'preferred_deg': 50, 'min_deg': 40, 'max_deg': 60},
              {'hz': 8000, 'preferred_deg': 50, 'min_deg': 40, 'max_deg': 60}],
    },
}
t = H.Target.from_dict(target_dict)
print('v9 target profile', t.coverage_profile_mode, t.coverage_profile_h, t.coverage_profile_v)
block = {'version': 9, 'tolerances': {'cov_profile': 3.0, 'rip': 1.0, 'flat': 1.5, 'load': 0.3,
                                       'dislope': 9.0, 'di_roughness': 1.0, 'flat_cv': 1.5},
         'cov_narrow_ratio': 2.0, 'cov_below_f0': 'one_sided', 'cov_v_weight': 0.5,
         'flat_band': 'scored', 'loaded_re_z': 0.5, 'lfp_re_z': 0.2, 'lfp_crossover_ratio': 1.6}
p9 = V9Params.from_block(block)
w9 = {'cov_profile': 1.0, 'rip': 1.0, 'flat': 0.5, 'load': 1.0, 'dislope': 1.0,
      'di_roughness': 1.0, 'flat_cv': 1.0}
print('v9 weights', resolve_v9_weights(w9, p9))

# score one landscape run's first ok row
runs = H.load_landscape_runs()
rd = runs[0]
print('run', rd['dir'].name, 'rows', len(rd['rows']))
row = next(r for r in rd['rows'] if r.get('ok') and isinstance(r.get('objective'), (int, float)))
h = row['design_hash']
resp = H.resp_from_run(rd['dir'], h)
print('response freqs', len(resp.freqs_hz), 'balloon', resp.spl_balloon_db.shape if resp.spl_balloon_db is not None else None)
m7 = H.metrics_parity(resp, b.target)
j7, t7 = H.objective_v7(m7, resp, True, b.target, b.weights, b.objective_params)
print('v7 replay J', j7, 'stored', row['objective'], 'terms', {k: round(v,3) for k,v in t7.items() if isinstance(v,(int,float))})
m9 = H.metrics_parity(resp, t)
j9, t9 = H.objective_v9(m9, resp, True, t, w9, p9)
print('v9 J', j9, 'terms', {k: round(v,3) for k,v in t9.items() if isinstance(v,(int,float))})
