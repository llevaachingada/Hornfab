"""Neutral backbone controls must build the saved verify meshes byte-for-byte. CPU only; no solver.

    .venv\\Scripts\\python.exe docs/evidence/cd_backbone_2026-11-25/neutral_parity.py
"""
import glob, hashlib, json, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from hornlab_search.config import load_config, mesh_spec  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402
from hornlab_search.mesh.build import build_mesh  # noqa: E402

EX = Path('examples/typologies/cd_backbone_2026-11-25')
HERE = Path('docs/evidence/cd_backbone_2026-11-25')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_dir(night, job):
    for line in Path(f'runs/nights/{night}/summary.jsonl').read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        if row['id'] == job:
            return Path(row['run_dir'])
    raise KeyError(job)


PAIRS = [
    ('rolled_bb_control', Path('runs/rolled_lame_anchor_verify_2026-11-24/rolled')),
    ('lame_bb_control', Path('runs/rolled_lame_anchor_verify_2026-11-24/lame')),
    ('lame_bb_control_m040', run_dir('directivity_attribution_2026-11-24', 'lame_morph_040')),
]

report = {}
with tempfile.TemporaryDirectory(prefix='bb-parity-') as td:
    for i, (name, ref_run) in enumerate(PAIRS):
        cfg = load_config(EX / f'{name}.yaml')
        design = DesignSpace.from_config(cfg).seed
        work = Path(td) / str(i)
        work.mkdir()
        mesh = build_mesh(design, mesh_spec('verify', cfg), cfg, work, mode='verify')
        ref = Path(glob.glob(str(ref_run / 'designs' / '*' / 'mesh.msh'))[0])
        report[name] = {'fresh_sha256': sha(mesh.path), 'saved_sha256': sha(ref), 'saved_mesh': ref.as_posix(),
                        'byte_identical': sha(mesh.path) == sha(ref), 'triangles': mesh.n_triangles,
                        'design_hash': design.hash()}
        print(name, 'BYTE-IDENTICAL' if report[name]['byte_identical'] else 'DIFFERENT',
              report[name]['fresh_sha256'][:16], report[name]['saved_sha256'][:16], mesh.n_triangles)
(HERE / 'neutral_parity.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
