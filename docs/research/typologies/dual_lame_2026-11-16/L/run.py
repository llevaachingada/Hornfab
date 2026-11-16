"""Run from repository root: python docs/research/typologies/dual_lame_2026-11-16/L/run.py"""
from pathlib import Path
import hashlib
import json
import platform
import sys
import traceback

root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(root))
import numpy as np
import scipy
import yaml
from hornlab_search.design.generators import lecleach_swept_hv as kernel

here = Path(__file__).resolve().parent
seed_file = here / 'seeds.yaml'
seed = yaml.safe_load(seed_file.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
files = ['hornlab_search/design/generators/lecleach_swept_hv.py',
         'hornlab_search/design/generators/section_lame.py',
         'hornlab_search/design/generators/profiles.py']
provenance = {'status': 'SURFACE_ONLY_UNVALIDATED', 'seed_sha256': sha(seed_file),
              'script_sha256': sha(Path(__file__)),
              'source_sha256': {f: sha(root / f) for f in files},
              'python': platform.python_version(), 'numpy': np.__version__,
              'scipy': scipy.__version__, 'pyyaml': yaml.__version__,
              'driver': {'throat_radius_mm': 18.0, 'throat_half_angle_deg': 2.0,
                         'note': 'legacy modeling assumptions; 36 mm diameter versus 35.8 mm manufacturer outlet'},
              'sampling': {'n_phi': 25, 'n_s': 96, 'dl_mm': 1.0},
              'limitations': 'Point surfaces only. No shell, intersection, curvature, mesh, acoustic or readiness validation. Lip follows the discrete parent endpoint tangent; 45-degree wrap. Width/height/depth are sampled surface bounds.'}
(here / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
rows = []
for sample in seed['samples']:
    params = dict(sample['core_existing_iwata_ar'])
    params.update({'g_' + k: v for k, v in sample['proposed_extension'].items()})
    result = {'id': sample['id'], 'style': sample['style'], 'params': params,
              'status': 'SURFACE_ONLY_UNVALIDATED'}
    try:
        pts, meta = kernel.make_grid(params, throat_radius_mm=18., throat_half_angle_deg=2.,
                                     n_phi=25, n_s=96, dl_mm=1.)
        result.update({'generated': True, 'surface_shape': list(pts.shape),
                       'surface_sha256_float64': hashlib.sha256(np.asarray(pts, dtype='<f8').tobytes()).hexdigest(),
                       'width_mm': meta['width_mm'], 'height_mm': meta['height_mm'],
                       'depth_mm': meta['depth_mm'], 'axial_warp_delta_mm': meta['axial_warp_delta_mm'],
                       'lip_wrap_deg': meta['lip_wrap_deg'], 'lip_continuity': meta['lip_continuity'],
                       'within_envelope_sampled_surface': meta['width_mm'] <= 600 and meta['height_mm'] <= 480 and meta['depth_mm'] <= 480})
    except Exception as exc:
        result.update({'generated': False, 'exception_type': type(exc).__name__, 'exception': str(exc),
                       'traceback': traceback.format_exc()})
    rows.append(result)
(here / 'results.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
print(f"Generated {sum(r['generated'] for r in rows)}/{len(rows)} surfaces; results remain unvalidated.")
