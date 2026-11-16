"""Screen supplied seeds through the versioned adapters; no solve or validity certification."""
from pathlib import Path
import csv
import hashlib
import json
import sys

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hornlab_search.design.generators import klangfilm_lame_family as K, lecleach_swept_hv as L

OUT = ROOT / 'docs/research/typologies/dual_lame_2026-11-16/screen'
PACK = OUT.parent
BRIEF_PATH = ROOT / 'examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7_smooth.yaml'
brief = yaml.safe_load(BRIEF_PATH.read_text(encoding='utf-8'))
packs = [('K', K, yaml.safe_load((PACK / 'k_visual_seeds_supplied.yaml').read_text(encoding='utf-8'))),
         ('L', L, yaml.safe_load((PACK / 'L/seeds.yaml').read_text(encoding='utf-8')))]
results = []
for label, family, pack in packs:
    for sample in pack['samples']:
        if label == 'K':
            values = dict(sample['params'])
            values['rim_sweep_ratio'] = values.pop('rim_sweep')
            values.update(morph_frac=.3, source_blend_ratio=0., entry_half_angle_deg=2.)
            knobs = {'g_' + k: v for k, v in values.items()}
            spec = {'name': 'grid', 'rows': {'type': K.KIND}, 'n_phi': 19, 'n_s': 64,
                    'wall_thickness_mm': 3., 'span': 'quarter'}
        else:
            knobs = dict(sample['core_existing_iwata_ar'])
            knobs.update({'g_' + k: v for k, v in sample['proposed_extension'].items()})
            spec = {'name': 'grid', 'rows': dict(L.ROW_FIELDS), 'n_phi': 25, 'n_s': 96,
                    'wall_thickness_mm': 3., 'span': 'quarter'}
        row = {'id': sample['id'], 'family': label, 'params': knobs,
               'implementation_sha256': family.implementation_digest(),
               'status': 'sampled_checks_only', 'global_intersections': 'not_checked',
               'acoustic_status': 'unsolved'}
        try:
            block = family.design_params(spec, knobs, brief)['grid']
            geom = family.resolve_grid(block, brief)
            data = np.asarray(geom['inner_points'], dtype='<f8').tobytes() + np.asarray(geom['outer_points'], dtype='<f8').tobytes()
            meta = geom['meta']
            inner = geom['inner_points']
            radii = np.hypot(inner[..., 0], inner[..., 1])
            minimum_increment = min(float(np.diff(radii[i, :int(np.argmax(radii[i])) + 1]).min())
                                    for i in range(len(inner)) if np.argmax(radii[i]) > 0)
            def entrance_angle(index):
                dr = radii[index, 1] - radii[index, 0]
                dz = inner[index, 1, 2] - inner[index, 0, 2]
                return float(np.degrees(np.arctan2(dr, dz)))
            a, b = inner[:, 1:-1] - inner[:, :-2], inner[:, 2:] - inner[:, 1:-1]
            c = inner[:, 2:] - inner[:, :-2]
            cross = np.linalg.norm(np.cross(a, b), axis=-1)
            lengths = np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1) * np.linalg.norm(c, axis=-1)
            curved = cross > 1e-12
            min_curvature_radius = float(np.min(lengths[curved] / (2 * cross[curved]))) if np.any(curved) else None
            row.update(sampled_checks_passed=True, geometry_sha256=hashlib.sha256(data).hexdigest(),
                       width_mm=meta['mouth_w_mm'], height_mm=meta['mouth_h_mm'], depth_mm=meta['x_span_mm'],
                       throat_chord_h_deg=entrance_angle(0), throat_chord_v_deg=entrance_angle(-1),
                       min_pre_max_radius_increment_mm=minimum_increment,
                       min_sampled_meridian_curvature_radius_mm=min_curvature_radius)
        except Exception as exc:
            row.update(sampled_checks_passed=False, error=f'{type(exc).__name__}: {exc}')
        results.append(row)
OUT.mkdir(parents=True, exist_ok=True)
for filename, passed in [('candidate_geometry.jsonl', True), ('invalid_geometry.jsonl', False)]:
    (OUT / filename).write_text(''.join(json.dumps(row, sort_keys=True) + '\n' for row in results
                                        if row['sampled_checks_passed'] is passed), encoding='utf-8')
with (OUT / 'geometry_metrics.csv').open('w', newline='', encoding='utf-8') as f:
    keys = ['id', 'family', 'sampled_checks_passed', 'width_mm', 'height_mm', 'depth_mm',
            'throat_chord_h_deg', 'throat_chord_v_deg', 'min_pre_max_radius_increment_mm',
            'min_sampled_meridian_curvature_radius_mm',
            'geometry_sha256', 'implementation_sha256', 'global_intersections', 'acoustic_status', 'error']
    writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(results)
print(f"{sum(r['sampled_checks_passed'] for r in results)}/{len(results)} passed sampled adapter checks; not geometry certification")
