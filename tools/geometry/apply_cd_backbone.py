"""Wrap a saved design in the CD wall-angle backbone (cd-backbone-v1) as fixed-candidate configs. CPU only.

Supported saved parents (rows type of the design's grid recipe):
  rolled_family_rect_v1   -> rolled_family_rect_bb_v1 (CD law added at neutral)
  rolled_family_rect_cd_v1 -> rolled_family_rect_bb_v1 (its CD knobs kept)
  klangfilm_lame_hv_cd    -> klangfilm_lame_hv_bb_v1
  lecleach / lecleach_ar / iwata_ar / salmon_elliptical / lecleach_mod / toroidal_rollback (generic WP9b rows,
                          quarter span) -> rows_bb_v1, a LABELED CD HYBRID of a non-CD parent (new identity)

--base-config <yaml> takes the brief, objective, mesh and solve settings from that config instead of the source
run (use it to re-score a parent from another brief on the CD brief). It also writes <prefix>_parent.yaml (the bare
parent recipe on that brief) and checks that the neutral control builds the parent's verify mesh byte-for-byte.

Writes <out>/<prefix>_control.yaml (backbone neutral) plus one YAML per --recipe, each the run's exact saved
effective config with only the generator kind and backbone knobs changed, then (unless --no-parity) checks that the
neutral control builds the design's saved mesh byte-for-byte. Default recipe = the rolled keeper of
docs/evidence/cd_backbone_2026-11-25 (bb_h 0.65, throat 0.25, roll-in 0.30, bb_v 0). The backbone is a LABELED
HYPOTHESIS; see docs/research/typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md.

    .venv\\Scripts\\python.exe tools/geometry/apply_cd_backbone.py --run runs/<run> --design <hash> \\
        --out examples/typologies/<folder> --prefix body3 [--recipe 0.65,0,0.25,0.30 --recipe 0.5,0,0.25,0.30]
"""
from __future__ import annotations

import argparse, copy, hashlib, json, sys, tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

KIND_MAP = {'rolled_family_rect_v1': 'rolled_family_rect_bb_v1',
            'rolled_family_rect_cd_v1': 'rolled_family_rect_bb_v1',
            'klangfilm_lame_hv_cd': 'klangfilm_lame_hv_bb_v1',
            **{t: 'rows_bb_v1' for t in ('lecleach', 'lecleach_ar', 'iwata_ar', 'salmon_elliptical',
                                         'lecleach_mod', 'toroidal_rollback')}}
CD_NEUTRAL = {'g_cd_h_deg': 0.0, 'g_cd_v_deg': 0.0, 'g_cd_start_s': 0.3, 'g_cd_peak_s': 0.6, 'g_cd_end_s': 0.88}


def recipe(text):
    h, v, t, r = (float(x) for x in text.split(','))
    return {'g_bb_h': h, 'g_bb_v': v, 'g_bb_throat_frac': t, 'g_bb_rollin_frac': r}


def build_configs(run: Path, design: str, recipes, out: Path, prefix: str, base_config: Path | None = None):
    cfg0 = json.loads((run / 'run.json').read_text(encoding='utf-8'))['config']
    if base_config is not None:
        cfg0 = yaml.safe_load(base_config.read_text(encoding='utf-8'))
    grid = json.loads((run / 'designs' / design / 'design.json').read_text(encoding='utf-8'))['params']['grid']
    kind = grid['rows'].get('type')
    if kind not in KIND_MAP:
        raise SystemExit(f'unsupported parent rows type {kind!r}; supported: {sorted(KIND_MAP)}')
    knobs = dict(grid['knobs'])
    if kind == 'rolled_family_rect_v1':
        knobs.update(CD_NEUTRAL)
    gen = {k: grid[k] for k in ('n_phi', 'n_s', 'span', 'wall_thickness_mm') if k in grid}
    rows = {'type': KIND_MAP[kind]}
    if 'mode' in grid['rows']:
        rows['mode'] = grid['rows']['mode']
    if KIND_MAP[kind] == 'rows_bb_v1':
        if grid.get('span', 'quarter') != 'quarter':
            raise SystemExit(f'rows_bb_v1 needs a quarter-span parent; {design} is span {grid.get("span")!r}')
        rows = {'type': 'rows_bb_v1', 'parent_rows': copy.deepcopy(grid['rows'])}
    parent_gen = {**gen, 'name': 'grid', 'rows': copy.deepcopy(grid['rows']), 'seed_policy': 'explicit'}
    gen.update(name='grid', rows=rows, seed_policy='explicit')
    if 'size_policy' in grid:
        gen['size_policy'] = grid['size_policy']
    out.mkdir(parents=True, exist_ok=True)
    written = []
    label = ('LABELED CD HYBRID of a non-CD parent: a new identity, scored only on this brief against its own '
             'neutral control. ' if KIND_MAP[kind] == 'rows_bb_v1' else '')
    if base_config is not None:
        cfg = copy.deepcopy(cfg0)
        cfg.update(generator=parent_gen, seed_params=dict(knobs), brief_file=None, name=f'{prefix}_parent',
                   bounds={k: {'lo': v, 'hi': v, 'search': False} for k, v in knobs.items()},
                   description=(f'Bare parent {design} from {run.as_posix()} ({kind}) re-built on '
                                f'{(cfg0.get("brief") or {}).get("name")}. Parity reference only.'))
        path = out / f'{prefix}_parent.yaml'
        path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8', newline='\n')
        written.append(path)
    neutral = {'g_bb_h': 0.0, 'g_bb_v': 0.0, 'g_bb_throat_frac': 0.15, 'g_bb_rollin_frac': 0.30}
    for name, bb in [(f'{prefix}_control', neutral)] + [
            (f"{prefix}_bb_h{int(round(r['g_bb_h'] * 100)):03d}_v{int(round(r['g_bb_v'] * 100)):03d}"
             f"_t{int(round(r['g_bb_throat_frac'] * 100)):02d}_r{int(round(r['g_bb_rollin_frac'] * 100)):02d}", r)
            for r in recipes]:
        cfg = copy.deepcopy(cfg0)
        kn = {**knobs, **bb}
        cfg.update(generator=gen, seed_params=kn, brief_file=None, name=f'{name}',
                   bounds={k: {'lo': v, 'hi': v, 'search': False} for k, v in kn.items()},
                   description=(f'{label}CD BACKBONE wrap of {design} from {run.as_posix()} ({kind}); backbone {bb}. '
                                'Fixed candidate; compare only with its own neutral control on the same verify grid.'))
        path = out / f'{name}.yaml'
        path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8', newline='\n')
        written.append(path)
    return written


def mesh_sha(config: Path):
    from hornlab_search.config import load_config, mesh_spec
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.mesh.build import build_mesh
    cfg = load_config(config)
    design = DesignSpace.from_config(cfg).seed
    with tempfile.TemporaryDirectory(prefix='bb-wrap-') as td:
        mesh = build_mesh(design, mesh_spec('verify', cfg), cfg, Path(td), mode='verify')
        return hashlib.sha256(Path(mesh.path).read_bytes()).hexdigest()


def parity(control: Path, saved_mesh: Path):
    from hornlab_search.config import load_config, mesh_spec
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.mesh.build import build_mesh
    cfg = load_config(control)
    design = DesignSpace.from_config(cfg).seed
    with tempfile.TemporaryDirectory(prefix='bb-wrap-') as td:
        mesh = build_mesh(design, mesh_spec('verify', cfg), cfg, Path(td), mode='verify')
        a = hashlib.sha256(Path(mesh.path).read_bytes()).hexdigest()
    b = hashlib.sha256(saved_mesh.read_bytes()).hexdigest()
    return a == b, a, b


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--run', required=True, type=Path)
    ap.add_argument('--design', required=True)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--prefix', required=True)
    ap.add_argument('--recipe', action='append', type=recipe,
                    help='bb_h,bb_v,throat_frac,rollin_frac (default: 0.65,0,0.25,0.30)')
    ap.add_argument('--no-parity', action='store_true')
    ap.add_argument('--base-config', type=Path,
                    help='take brief/objective/mesh/solve from this config (re-score a parent on another brief)')
    args = ap.parse_args()
    recipes = args.recipe or [recipe('0.65,0,0.25,0.30')]
    paths = build_configs(args.run, args.design, recipes, args.out, args.prefix, args.base_config)
    for p in paths:
        print('wrote', p.as_posix())
    if args.base_config is not None:
        if not args.no_parity:
            a, b = mesh_sha(paths[0]), mesh_sha(paths[1])
            print('neutral control verify mesh', 'BYTE-IDENTICAL to bare parent' if a == b
                  else f'DIFFERS from bare parent ({b[:12]} vs {a[:12]})')
            if a != b:
                raise SystemExit(2)
        return
    saved = args.run / 'designs' / args.design / 'mesh.msh'
    if not args.no_parity and saved.exists():
        ok, a, b = parity(paths[0], saved)
        print('neutral control mesh', 'BYTE-IDENTICAL to saved' if ok else f'DIFFERS from saved ({a[:12]} vs {b[:12]})')
        if not ok:
            raise SystemExit(2)


if __name__ == '__main__':
    main()
