"""Write fixed, geometry-only examples from the supplied first K and L seeds.

These are shape-check inputs, not queue entries or acoustic-readiness claims.
Run from the repository root using the project's virtual environment.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'examples/typologies/dual_lame_2026-11-16'
BASE = ROOT / 'examples/typologies/home_landscape_2026-11-15'
BRIEF = '../../briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7_smooth.yaml'


def write(name, source, rows, knobs, n_phi, n_s):
    config = yaml.safe_load((BASE / source).read_text(encoding='utf-8'))
    config['name'] = name
    config['brief_file'] = BRIEF
    config['description'] = 'Geometry diagnostic only; no acoustic readiness or queue admission.'
    config['generator'] = {'name': 'grid', 'rows': rows, 'n_phi': n_phi, 'n_s': n_s,
                           'wall_thickness_mm': 3.0, 'span': 'quarter'}
    config['seed_params'] = knobs
    config['bounds'] = {key: {'lo': val, 'hi': val, 'search': False} for key, val in knobs.items()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{name}.yaml').write_text(yaml.safe_dump(config, sort_keys=False), encoding='utf-8')


write('k01_geometry_only', 'hl__klangfilm_lame_curved_v1.yaml', {'type': 'klangfilm_lame_v1'},
      {'g_fc_hz': 560.0, 'g_aspect': 1.6, 'g_lame_p': 2.0, 'g_end_frac': 1.25,
       'g_rim_sweep_ratio': 0.0, 'g_morph_frac': 0.3, 'g_source_blend_ratio': 0.0,
       'g_entry_half_angle_deg': 2.0}, 19, 64)
write('l01_geometry_only', 'hl__lecleach_iwata_ar_landscape_smooth_v7.yaml',
      {'type': 'lecleach_swept_hv', 'schema': 'lecleach-swept-hv-v1',
       'area_mode': 'flat_section_parent', 'aspect_progression': 'quintic',
       'lame_progression': 'quintic', 'lip_model': 'tangent_arc'},
      {'g_fc_hz': 500.0, 'g_T': 0.5, 'g_stop_deg': 118.0, 'g_ar_m': 1.52,
       'g_ar_p': 1.05, 'g_lame_p_mouth': 2.0, 'g_lip_radius_mm': 0.0,
       'g_rim_sweep_mm': 0.0, 'g_axial_length_factor': 1.0}, 25, 96)
