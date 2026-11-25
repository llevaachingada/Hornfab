"""Survey (CPU, no solver): which saved rows/freeform designs could use the CD backbone lever.

For every run with best.json whose design is a rows-kind GRID recipe, keep the best J per (rows type, brief, mode).
Then, for the best design of each type, rebuild its inner sheet through the registered family adapter and report the
quantities that predicted the backbone's effect on the rolled/Lamé anchors:

* has_return: the H row's forward (max-z) station lies before the last station (a returned lip exists);
* chord angle (deg) from throat to the H/V forward stations, i.e. a straight-wall bound on the body angle;
* parent wall angle at 10 / 20 / 30 / 45 % of the pre-roll arc (H and V);
* gap = chord - wall at 30 %: large positive gap = the early wall flares slowly (beams at 6-8 kHz), the case the
  backbone fixed on the rolled anchor.

    .venv\\Scripts\\python.exe docs/evidence/cd_backbone_2026-11-25/survey_rows_families.py
"""
import glob, json, math, os, sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path.cwd()))
HERE = Path('docs/evidence/cd_backbone_2026-11-25')


def scan():
    best = {}
    for b in glob.glob('runs/*/best.json'):
        try:
            d = json.load(open(b, encoding='utf-8'))
        except Exception:
            continue
        g = (d.get('params') or {}).get('grid')
        if not isinstance(g, dict) or not isinstance(g.get('rows'), dict) or d.get('objective') is None:
            continue
        run = Path(b).parent
        try:
            cfg = yaml.safe_load((run / 'config.yaml').read_text(encoding='utf-8'))
        except Exception:
            continue
        brief = (cfg.get('brief') or {}).get('name')
        ver = (cfg.get('objective') or {}).get('version')
        key = (g['rows'].get('type'), brief, d.get('mode'))
        if key not in best or d['objective'] < best[key]['J']:
            best[key] = {'J': float(d['objective']), 'run': run.as_posix(), 'design': d.get('design_hash'),
                         'version': ver, 'grid': g, 'brief': cfg.get('brief')}
    return best


def wall(points, row):
    r = points[row]
    rho = np.hypot(r[:, 0], r[:, 1]); z = r[:, 2]
    f = int(np.argmax(z))
    ds = np.hypot(np.diff(z[:f + 1]), np.diff(rho[:f + 1]))
    u = np.r_[0.0, np.cumsum(ds)] / max(ds.sum(), 1e-12)
    ang = np.degrees(np.arctan2(np.gradient(rho[:f + 1]), np.gradient(z[:f + 1])))
    chord = math.degrees(math.atan2(rho[f] - rho[0], z[f] - z[0]))
    return {'forward_station': f, 'n': len(z), 'has_return': f < len(z) - 2, 'chord_deg': round(chord, 1),
            'wall_deg': [round(float(np.interp(x, u, ang)), 1) for x in (0.1, 0.2, 0.3, 0.45)],
            'gap_at_30pct_deg': round(chord - float(np.interp(0.3, u, ang)), 1)}


def inner_points(grid, brief):
    from hornlab_search.config import brief_for_envelope_adapter
    from hornlab_search.design.generators import grid as grid_gen
    spec = {k: v for k, v in grid.items() if k != 'knobs'}
    pts, _meta = grid_gen.rows_grid_points(spec, grid['knobs'], brief_for_envelope_adapter(brief))
    return np.asarray(pts, dtype=float)


def main():
    best = scan()
    by_type = {}
    for (t, brief, mode), rec in best.items():
        if t not in by_type or rec['J'] < by_type[t][1]['J']:
            by_type[t] = ((brief, mode), rec)
    out = {'per_type_brief_mode': {f'{k[0]} | {k[1]} | {k[2]}': {x: v for x, v in r.items() if x not in ('grid', 'brief')}
                                   for k, r in sorted(best.items(), key=lambda kv: (str(kv[0][0]), kv[1]['J']))},
           'geometry_of_best_per_type': {}}
    for t, ((brief, mode), rec) in sorted(by_type.items(), key=lambda kv: str(kv[0])):
        row = {'brief': brief, 'mode': mode, 'J': rec['J'], 'version': rec['version'], 'run': rec['run'],
               'design': rec['design']}
        try:
            pts = inner_points(rec['grid'], rec['brief'])
            row['H'] = wall(pts, 0)
            row['V'] = wall(pts, -1)
            row['rows'] = int(pts.shape[0])
        except Exception as exc:
            row['error'] = f'{type(exc).__name__}: {str(exc)[:160]}'
        out['geometry_of_best_per_type'][str(t)] = row
        g = row.get('H'), row.get('V')
        if 'error' in row:
            print(f'{str(t):32s} J {rec["J"]:7.3f} {str(brief)[:40]:40s} ERROR {row["error"][:90]}')
        else:
            print(f'{str(t):32s} J {rec["J"]:7.3f} {str(brief)[:40]:40s} return {row["H"]["has_return"]}  '
                  f'H chord {row["H"]["chord_deg"]:5.1f} wall10/20/30/45 {row["H"]["wall_deg"]} gap {row["H"]["gap_at_30pct_deg"]:5.1f} | '
                  f'V chord {row["V"]["chord_deg"]:5.1f} wall {row["V"]["wall_deg"]} gap {row["V"]["gap_at_30pct_deg"]:5.1f}')
    (HERE / 'survey_rows_families.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
