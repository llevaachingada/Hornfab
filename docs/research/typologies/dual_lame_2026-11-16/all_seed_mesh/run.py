"""CPU-only mesh/source audit for supplied K/L seeds. Run from repo root with .venv Python.

Retains generated fixed configs and meshes; never calls an acoustic solver or queue.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import traceback

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
import numpy as np
import scipy
import yaml
from tools import shape_check

HERE = Path(__file__).resolve().parent
BASE = ROOT / 'examples/typologies/dual_lame_2026-11-16'
SOURCE = HERE.parent
BRIEF = ROOT / 'examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7_smooth.yaml'
AUDIT = SOURCE / 'mesh_audit/audit_mesh.py'
spec = importlib.util.spec_from_file_location('dual_mesh_audit', AUDIT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
inputs = [SOURCE / 'k_visual_seeds_supplied.yaml', SOURCE / 'L/seeds.yaml',
          SOURCE / 'screen/candidate_geometry.jsonl', SOURCE / 'screen/invalid_geometry.jsonl',
          BASE / 'k01_geometry_only.yaml', BASE / 'l01_geometry_only.yaml', BRIEF,
          ROOT / 'tools/shape_check.py', AUDIT, Path(__file__)]
inputs.extend(ROOT / 'hornlab_search/design/generators' / n for n in ('klangfilm_lame_family.py', '_klangfilm_lame_v1.py', '_lame_cap_v1.py', 'lecleach_swept_hv.py', 'section_lame.py', 'profiles.py', 'lame_shell.py', 'grid.py'))
provenance = {'input_sha256': {str(p.relative_to(ROOT)): sha(p) for p in inputs},
              'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__,
              'pyyaml': yaml.__version__, 'scope': 'CPU mesh only; no solve, GPU or queue',
              'mapping': 'K rim_sweep -> g_rim_sweep_ratio; K additional fixed knobs from K01. L core keys kept, extension prefixed g_. All other config settings copied from K01/L01; brief path re-rooted only.'}
(HERE / 'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n', encoding='utf-8')
records = {}
for f in ('screen/candidate_geometry.jsonl', 'screen/invalid_geometry.jsonl'):
    for line in (SOURCE / f).read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        records[row['id']] = row
cases = []
for family, pack_path in [('K', inputs[0]), ('L', inputs[1])]:
    pack = yaml.safe_load(pack_path.read_text(encoding='utf-8'))
    template = yaml.safe_load((BASE / f'{family.lower()}01_geometry_only.yaml').read_text(encoding='utf-8'))
    for sample in pack['samples']:
        sid = sample['id']
        if family == 'K':
            mapped = dict(template['seed_params'])
            for key, value in sample['params'].items():
                mapped['g_' + ('rim_sweep_ratio' if key == 'rim_sweep' else key)] = value
        else:
            mapped = dict(sample['core_existing_iwata_ar'])
            mapped.update({'g_'+k: v for k, v in sample['proposed_extension'].items()})
        if sid not in records or mapped != records[sid]['params']:
            raise ValueError(f'{sid}: mapped seed differs from adapter screen record')
        config = dict(template)
        config['name'] = sid.lower() + '_geometry_only'
        config['brief_file'] = Path(os.path.relpath(BRIEF, HERE / 'configs')).as_posix()
        config['seed_params'] = mapped
        config['bounds'] = {k: {'lo': v, 'hi': v, 'search': False} for k, v in mapped.items()}
        configs = HERE / 'configs'
        configs.mkdir(exist_ok=True)
        cfgpath = configs / (sid.lower() + '.yaml')
        cfgpath.write_text(yaml.safe_dump(config, sort_keys=False), encoding='utf-8')
        result = {'id': sid, 'family': family, 'adapter_screen_status': records[sid]['status'],
                  'adapter_screen_passed': records[sid]['sampled_checks_passed'],
                  'adapter_screen_implementation_sha256': records[sid]['implementation_sha256'],
                  'params': mapped, 'config_sha256': sha(cfgpath)}
        try:
            result['shape_check'] = shape_check.check(str(cfgpath), None, 'screen', HERE / 'meshes', False)
            mesh = HERE / 'meshes' / cfgpath.stem / 'mesh.msh'
            if result['shape_check'].get('saved') and mesh.exists():
                result['mesh_audit'] = audit.audit(mesh)
            else:
                result['mesh_audit'] = None
        except Exception as exc:
            result['exception'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
        cases.append(result)
        (HERE / 'results.json').write_text(json.dumps(cases, indent=2, allow_nan=False)+'\n', encoding='utf-8')
        print(sid, result.get('shape_check', result.get('exception')), flush=True)
print(f'Completed {len(cases)} seeds.', flush=True)
