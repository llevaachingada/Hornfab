"""Read stored responses and ablate stored v7 terms. Never calls a solver or writes history."""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from hornlab_search.metrics.di import di_from_cuts, di_slope_db_per_decade, target_di_gaussian_db
from hornlab_search.metrics.diagonal import diagonal_beamwidths_deg
from hornlab_search.objective.scalar_v7 import V7Params, objective_v7
from hornlab_search.search.evaluate import metrics_from_response
from hornlab_search.solve.cache import load_response
from hornlab_search.targets.spec import Target

OUT = Path(__file__).resolve().parent
KEYS = ('cov', 'rip', 'di', 'dislope', 'flat', 'load', 'distd', 'diag', 'flat_cv')
ABLATIONS = {'original': (), 'omit_dislope': ('dislope',), 'omit_distd': ('distd',),
             'omit_absolute_di': ('di',), 'omit_diagonal': ('diag',),
             'omit_di_priors_and_diagonal': ('dislope', 'di', 'distd', 'diag')}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fit(f, d, lo, hi):
    use = (f >= lo) & (f <= hi) & np.isfinite(d)
    if use.sum() < 2:
        return None
    x, y = np.log10(f[use]), d[use]
    coeff = np.polyfit(x, y, 1)
    residual = y - np.polyval(coeff, x)
    return {'requested_hz': [lo, hi], 'actual_hz': [float(f[use][0]), float(f[use][-1])],
            'n': int(use.sum()), 'db_per_decade': float(coeff[0]),
            'db_per_octave': float(coeff[0] * math.log10(2)),
            'std_di_db': float(np.std(y)), 'std_fit_residual_db': float(np.std(residual))}


def analyze_run(item):
    run = ROOT / 'runs' / item['run']
    cfg = yaml.safe_load((run / 'config.yaml').read_text(encoding='utf-8'))
    target = Target.from_dict(cfg['target'])
    params = V7Params.from_block(cfg['objective'])
    weights = cfg['weights']
    rows = [json.loads(line) for line in (run / 'search.ndjson').read_text(encoding='utf-8').splitlines() if line.strip()]
    rows = [r for r in rows if r.get('ok') and r.get('metrics') and np.isfinite(r['objective'])]
    result = {'run': item['run'], 'name': cfg['name'], 'config_sha256': sha(run / 'config.yaml'),
              'target': cfg['target'], 'weights': weights, 'objective': cfg['objective'], 'usable_rows': len(rows)}
    if not rows:
        return result
    for r in rows:
        r['_weighted'] = {k: float(weights[k]) * float(r['terms'][k]) for k in KEYS}
    result['maximum_weight_sum_delta'] = float(max(abs(sum(r['_weighted'].values())-r['objective']) for r in rows))
    result['ablations'] = {}
    for name, remove in ABLATIONS.items():
        scored = [(sum(v for k, v in r['_weighted'].items() if k not in remove), r) for r in rows]
        j, winner = min(scored, key=lambda pair: pair[0])
        result['ablations'][name] = {'best_diagnostic_J': j, 'winner_hash': winner['design_hash'],
                                     'winner_n': winner['n'], 'stored_J': winner['objective'],
                                     'seed_diagnostic_J': scored[0][0], 'weighted_terms': winner['_weighted']}
    result['response_checks'] = []
    winners = {rows[0]['design_hash']: rows[0], min(rows, key=lambda r: r['objective'])['design_hash']: min(rows, key=lambda r: r['objective'])}
    for digest, row in winners.items():
        file = run / 'designs' / digest / 'response.npz'
        if not file.exists():
            result['response_checks'].append({'hash': digest, 'missing_response': True})
            continue
        response = load_response(file)
        m = metrics_from_response(response, target)
        j, terms = objective_v7(m, response, True, target, weights, params)
        stored_di = np.asarray(row['metrics']['di_db'])
        cut_di = np.array([di_from_cuts(h, v) for h, v in zip(m.bw_h_deg, m.bw_v_deg)])
        f = m.freqs_hz
        fits = {f'{lo:g}_{hi:g}': {'balloon': fit(f, m.di_db, lo, hi), 'cuts_estimate': fit(f, cut_di, lo, hi)}
                for lo, hi in ((350,8000), (700,8000), (1000,5600), (700,5600), (2500,5500))}
        original = row['_weighted']
        smooth_raw = yaml.safe_load((ROOT/'examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7_smooth.yaml').read_text())
        smooth_target = replace(target, di_slope_target=float(smooth_raw['target']['di_slope_target']))
        sj, st = objective_v7(m, response, True, smooth_target, smooth_raw['weights'], V7Params.from_block(smooth_raw['objective']))
        result['response_checks'].append({'hash': digest, 'n': row['n'], 'response_sha256': sha(file),
            'di_source': m.di_source, 'balloon_grid': response.meta.get('balloon_grid'),
            'balloon_count': len(response.balloon_dirs) if response.balloon_dirs is not None else 0,
            'meta': {k: response.meta.get(k) for k in ('spl_reference','source_motion','distance_m','mesh_scale','z_throat_convention','angle_count')},
            'recomputed_J': j, 'stored_J': row['objective'], 'delta_J': j-row['objective'],
            'max_di_recompute_delta_db': float(np.max(abs(stored_di-m.di_db))),
            'weighted_terms': original, 'fits': fits, 'freqs_hz': f.tolist(), 'di_db': m.di_db.tolist(),
            'bw_h_deg': m.bw_h_deg.tolist(), 'bw_v_deg': m.bw_v_deg.tolist(),
            'cuts_di_db': cut_di.tolist(), 'smooth_existing_diagnostic_J': sj,
            'smooth_weighted_terms': {k: float(smooth_raw['weights'][k])*float(st[k]) for k in KEYS},
            'mesh': {k: row.get(k) for k in ('n_dof','mesh_hash','solve_hash','res_mm')},
        })
    return result


def synthetic_diagonal():
    # Analytic tangent-plane elliptical Gaussian and superellipse contours share the same H/V widths.
    h, v = np.tan(np.radians(40)), np.tan(np.radians(25))
    answer = {'reference_round_deg': 65.0, 'models': []}
    for power in (2,4,8,32):
        r = ((abs(np.cos(np.pi/4))/h)**power + (abs(np.sin(np.pi/4))/v)**power)**(-1/power)
        exact = float(2*np.degrees(np.arctan(r)))
        answer['models'].append({'contour_power': power, 'true_diagonal_deg': exact,
            'round_reference_raw_error': 2*(exact-65)**2/100,
            'note': 'Same80x50 H/V crossings; model choice is illustrative, not a new target.'})
    for ntheta, nphi in ((17,32),(23,46),(45,90),(91,180)):
        theta = np.linspace(0,np.pi,ntheta)
        phi = np.linspace(0,2*np.pi,nphi,endpoint=False)
        th, ph = np.meshgrid(theta,phi,indexing='ij')
        dirs = np.stack((np.sin(th)*np.cos(ph),np.sin(th)*np.sin(ph),np.cos(th)),axis=-1).reshape(-1,3)
        safe = np.maximum(dirs[:,2],1e-9)
        u, w = dirs[:,0]/safe, dirs[:,1]/safe
        db = -20*np.log10(2)*((u/h)**2 + (w/v)**2)
        db[dirs[:,2]<=0] = -120
        estimated = diagonal_beamwidths_deg(dirs,db,0)
        answer.setdefault('estimator_checks',[]).append({'theta_phi': [ntheta,nphi], 'estimated_diagonal_deg': list(estimated)})
    f = np.geomspace(700,8000,13)
    x = np.log10(f/700)
    for slope in (0,5,8.6):
        di = 8+slope*x
        answer.setdefault('linear_di_checks',[]).append({'slope_db_per_decade': slope,
            'std_di_db': float(np.std(di)), 'std_fit_residual_db': float(np.std(di-np.polyval(np.polyfit(np.log10(f),di,1),np.log10(f))))})
    answer['gaussian_target_di_80x50_db'] = target_di_gaussian_db(80,50)
    return answer


def main():
    inv = json.loads((OUT/'runs_current.json').read_text())
    results = []
    for item in inv:
        try:
            r = analyze_run(item)
            results.append(r)
            print(item['run'], r['name'], r['usable_rows'], 'checks',len(r.get('response_checks',[])), flush=True)
        except Exception as exc:
            results.append({'run':item['run'],'error':repr(exc)})
            print('ERROR',item['run'],repr(exc),flush=True)
    result = {'kind':'offline_diagnostic_only_no_solver_calls', 'runs':results, 'synthetic_checks':synthetic_diagonal()}
    (OUT/'objective_ablation.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    lines = ['# Offline objective evidence\n', 'Diagnostic leave-term-out scores are not approved objectives or new solves. Original terms are normalized; ablations multiply by the recorded weights. Response checks recompute the original objective through the current code.\n', '| Config/run | Stored best | Omit slope | Omit diagonal | Omit DI priors+diagonal | Original winner slope dB/dec (dB/oct) |', '|---|---:|---:|---:|---:|---:|']
    for r in results:
        if not r.get('ablations'): continue
        a = r['ablations']; check = min(r['response_checks'],key=lambda c:c.get('stored_J',1e6))
        fitval = check['fits']['700_8000']['balloon']
        lines.append(f"| {r['name']} / {r['run'][-6:]} | {a['original']['best_diagnostic_J']:.4f} | {a['omit_dislope']['best_diagnostic_J']:.4f} | {a['omit_diagonal']['best_diagnostic_J']:.4f} | {a['omit_di_priors_and_diagonal']['best_diagnostic_J']:.4f} | {fitval['db_per_decade']:.3f} ({fitval['db_per_octave']:.3f}) |")
    lines += ['\nFull numeric evidence, actual fit bands, winner changes, response SHA256 and source conventions: objective_ablation.json. No fabricated 700 Hz sample is added; actual score-band endpoints are recorded.', '\nSynthetic checks:\n```json',json.dumps(result['synthetic_checks'],indent=2),'```']
    (OUT/'OBJECTIVE_OFFLINE.md').write_text('\n'.join(lines)+'\n')
    print('WROTE objective_ablation.json OBJECTIVE_OFFLINE.md',flush=True)


if __name__ == '__main__': main()
