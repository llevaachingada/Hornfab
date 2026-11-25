"""Batch-4 predictions (CPU only): throat-transition and roll-in variants of the rolled backbone.

Writes the candidate YAMLs (copies of rolled_bb_h050.yaml with only g_bb_h / g_bb_throat_frac /
g_bb_rollin_frac changed) and prints, per candidate:
  * near-throat flare proxies: wall angle at u = 0.05 / 0.10 / 0.15 and radius at u = 0.10, 0.20 (H row);
  * the station-map heuristic change of H width at 2037 Hz and the five 6-8 kHz bins, relative to the
    MEASURED reference run named in REF (small geometric differences -> inside the heuristic's
    calibrated range; gain 0.605 from directivity_attribution_2026-11-24/station_map.py).

    .venv\\Scripts\\python.exe docs/evidence/cd_backbone_2026-11-25/predict_b4.py
"""
import copy, json, sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, 'docs/evidence/directivity_attribution_2026-11-24')
import station_map as sm  # noqa: E402
from hornlab_search.config import brief_for_envelope_adapter, load_config  # noqa: E402
from hornlab_search.design.generators import cd_backbone_family as bf  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402

EX = Path('examples/typologies/cd_backbone_2026-11-25')
HERE = Path('docs/evidence/cd_backbone_2026-11-25')
GAIN_H = 0.605
BINS = [2037, 6085, 6325, 6977, 7113, 8000]

# name -> (changes, reference measured job)
CANDS = {
    'rolled_bb_h065_th025': ({'g_bb_h': 0.65, 'g_bb_throat_frac': 0.25}, 'rolled_bb_h065'),
    'rolled_bb_h065_th030': ({'g_bb_h': 0.65, 'g_bb_throat_frac': 0.30}, 'rolled_bb_h065'),
    'rolled_bb_h065_ri022': ({'g_bb_h': 0.65, 'g_bb_rollin_frac': 0.22}, 'rolled_bb_h065'),
    'rolled_bb_h065_ri038': ({'g_bb_h': 0.65, 'g_bb_rollin_frac': 0.38}, 'rolled_bb_h065'),
    'rolled_bb_h050_th025': ({'g_bb_h': 0.50, 'g_bb_throat_frac': 0.25}, 'rolled_bb_h050'),
    'rolled_bb_h080_th030': ({'g_bb_h': 0.80, 'g_bb_throat_frac': 0.30}, 'rolled_bb_h065'),
}
REF_CFG = {'rolled_bb_h065': 'rolled_bb_h065', 'rolled_bb_h050': 'rolled_bb_h050'}


def points(path):
    cfg = load_config(path)
    block = DesignSpace.from_config(cfg).seed.params['grid']
    return bf.resolve_grid(block, brief_for_envelope_adapter(cfg.brief))['inner_points']


def run_of(job):
    for night in ('cd_backbone_2026-11-25', 'cd_backbone_b2_2026-11-25', 'cd_backbone_b3_2026-11-25'):
        p = Path('runs/nights') / night / 'summary.jsonl'
        if p.exists():
            for line in p.read_text(encoding='utf-8').splitlines():
                row = json.loads(line)
                if row['id'] == job and row.get('status') == 'ok':
                    return row['run_dir']
    raise KeyError(job)


def flare(pts):
    u, ang = sm.wall(pts, 'H')
    rr = pts[0]
    rho = np.hypot(rr[:, 0], rr[:, 1]); z = rr[:, 2]; f = int(np.argmax(z))
    ds = np.hypot(np.diff(z[:f + 1]), np.diff(rho[:f + 1])); uu = np.r_[0, np.cumsum(ds)] / ds.sum()
    return {'wall_u05': float(np.interp(0.05, u, ang)), 'wall_u10': float(np.interp(0.10, u, ang)),
            'wall_u15': float(np.interp(0.15, u, ang)), 'r_u10': float(np.interp(0.10, uu, rho[:f + 1])),
            'r_u20': float(np.interp(0.20, uu, rho[:f + 1]))}


def main():
    base_cfg = yaml.safe_load((EX / 'rolled_bb_h050.yaml').read_text(encoding='utf-8'))
    out = {}
    refs = {}
    for ref, stem in REF_CFG.items():
        pts = points(EX / f'{stem}.yaml')
        m = sm.metrics(run_of(ref))
        refs[ref] = (pts, m, {'H': sm.station_map(pts, m, 'H')}, flare(pts))
    for name, (change, ref) in CANDS.items():
        cfg = copy.deepcopy(base_cfg)
        knobs = {**cfg['seed_params'], **change}
        cfg['seed_params'] = knobs
        cfg['bounds'] = {k: {'lo': v, 'hi': v, 'search': False} for k, v in knobs.items()}
        cfg['name'] = f'{name}_2026_11_25'
        cfg['description'] = (f'CD BACKBONE batch 4 (2026-11-25), fixed candidate: rolled_bb_h050.yaml with only {change} '
                              'changed. Same brief, source, mesh and solve; predeclared in '
                              'docs/evidence/cd_backbone_2026-11-25/PREDECLARED.md (batch-4 addendum).')
        path = EX / f'{name}.yaml'
        path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8', newline='\n')
        pts = points(path)
        rpts, rm, rmap, rfl = refs[ref]
        d = sm.raw_delta(pts, rpts, rmap['H'], 'H')
        base = dict(zip(rm['freqs_hz'], rm['bw_h_deg']))
        pred = {}
        for b in BINS:
            f = min(d, key=lambda x: abs(x - b))
            pred[str(b)] = round(base[f] + GAIN_H * d[f], 1)
        fl = flare(pts)
        out[name] = {'change': change, 'reference_job': ref, 'predicted_H': pred,
                     'reference_H': {str(b): round(base[min(base, key=lambda x: abs(x - b))], 1) for b in BINS},
                     'flare': {k: round(v, 2) for k, v in fl.items()},
                     'reference_flare': {k: round(v, 2) for k, v in rfl.items()}}
        print(f"{name:22s} ref {ref}: H pred {list(pred.values())} vs ref {list(out[name]['reference_H'].values())}")
        print(f"   flare wall u.05/.10/.15 {fl['wall_u05']:.1f}/{fl['wall_u10']:.1f}/{fl['wall_u15']:.1f} "
              f"(ref {rfl['wall_u05']:.1f}/{rfl['wall_u10']:.1f}/{rfl['wall_u15']:.1f}); r u.10/.20 {fl['r_u10']:.1f}/{fl['r_u20']:.1f} "
              f"(ref {rfl['r_u10']:.1f}/{rfl['r_u20']:.1f})")
    (HERE / 'predict_b4.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
