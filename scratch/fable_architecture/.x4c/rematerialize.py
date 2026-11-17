"""X4 completion: resolve the failed rematerializations.

Each lane is tested in its own process because the bridge CLIs rebind the generator globally:

    python .x4c/rematerialize.py klangfilm
    python .x4c/rematerialize.py crowe_panel
    python .x4c/rematerialize.py rosse_rect
    python .x4c/rematerialize.py lecleach

Recorded: recipe-hash reproduction, stored vs HEAD implementation digest, whether the geometry
builds, and - for le cleach - the HEAD generator box against the stored mesh box.  No digest is
bypassed: a mismatching stored recipe is reported as unresolved, not rebuilt.
"""
import sys, json, pickle, pathlib, warnings
import numpy as np

sys.path.insert(0, 'scratch/fable_architecture/.n1')
sys.path.insert(0, '.')
warnings.filterwarnings('ignore')

import importlib.util as ilu
_s = ilu.spec_from_file_location('n1_build', 'scratch/fable_architecture/.n1/build.py')
N1 = ilu.module_from_spec(_s); _s.loader.exec_module(N1)
from hornlab_search.config import load_config
from hornlab_search.design.generators import grid
from hornlab_search.types import Design

ROOT = pathlib.Path('scratch/fable_architecture')
LANE = {
    'klangfilm': ('hl__klangfilm_lame_curved_v1', 'generated_geometry.json', 'klangfilm_lame'),
    'crowe_panel': ('hl__crowe_panel_home_v7', 'generated_geometry_extra.json', 'crowe_panel'),
    'rosse_rect': ('hl__rosse_rect_cd_v7', 'generated_geometry_fifth.json', 'rosse_rect'),
    'lecleach': ('hl__lecleach_hv_landscape_smooth_v7', None, 'lecleach'),
}


def selected_hashes(name, lane, src):
    if src:
        d = json.loads((ROOT / '.x4' / src).read_text())
        return [r['hash'] for r in d[lane]['results']]
    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    pool = [r for r in rows if r['ok'] and r['config'] == lane
            and (pathlib.Path('runs') / r['run'] / 'designs' / r['h'] / 'mesh.msh').is_file()]
    pool.sort(key=lambda r: (r['run'], r['h']))
    seen, out = set(), []
    for r in pool:
        if r['h'] in seen:
            continue
        seen.add(r['h']); out.append(r['h'])
        if len(out) == 10:
            break
    return out


def row_for(lane, h):
    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    return next(r for r in rows if r['ok'] and r['config'] == lane and r['h'] == h)


def digest(recipe):
    p = recipe['params']
    return (((p.get('grid') or {}).get('rows') or {}).get('implementation_sha256'))


def head_digest(name):
    if name == 'klangfilm_lame':
        from tools.geometry import klangfilm_lame_cli
        return klangfilm_lame_cli.implementation_digest()
    if name == 'crowe_panel':
        from tools.geometry import crowe_panel_cli
        return crowe_panel_cli.implementation_digest()
    if name == 'rosse_rect':
        from tools.geometry import rosse_rect_cli
        return rosse_rect_cli.implementation_digest()
    return None


def box_of(inner):
    pts = np.asarray(inner, float)
    return dict(W_mm=2.0 * float(np.max(np.abs(pts[:, :, 0]))),
                H_mm=2.0 * float(np.max(np.abs(pts[:, :, 1]))),
                D_mm=float(np.ptp(pts[:, :, 2])))


def main():
    name = sys.argv[1]
    lane, src, kind = LANE[name]
    hashes = selected_hashes(name, lane, src)
    hd = head_digest(kind)
    if kind == 'crowe_panel':
        from tools.geometry import crowe_panel_cli
        crowe_panel_cli.install()
    elif kind == 'rosse_rect':
        from tools.geometry import rosse_rect_cli
        rosse_rect_cli.install()
    out = dict(lane=lane, kind=kind, head_digest=hd, records=[])
    for h in hashes:
        r = row_for(lane, h)
        recipe = json.loads((pathlib.Path('runs') / r['run'] / 'designs' / h /
                             'design.json').read_text())
        rec = dict(h=h, run=r['run'], stored_digest=digest(recipe), head_digest=hd)
        try:
            rec['hash_ok'] = bool(Design(recipe['family'], recipe['params']).hash() == h)
            if kind in ('klangfilm_lame', 'lecleach'):
                inner, outer, mode, prov, t = N1.build_one(lane, r, load_config(
                    pathlib.Path('runs') / r['run'] / 'config.yaml'), 10.0)
                rec.update(built=True, mode=mode, provenance=prov,
                           inner_shape=list(np.shape(inner)), box=box_of(inner))
            else:
                cfg = load_config(pathlib.Path('runs') / r['run'] / 'config.yaml')
                b = recipe['params']['grid']
                inner, meta = grid.rows_grid_points(b, b.get('knobs', {}), cfg.brief)
                rec.update(built=True, mode='bridge', provenance='grid.rows_grid_points',
                           inner_shape=list(np.shape(inner)), box=box_of(inner),
                           built_digest=meta.get('implementation_sha256'))
            rec['digest_match'] = (rec['stored_digest'] == hd) if rec['stored_digest'] else None
        except Exception as e:
            rec.update(built=False, error='%s: %s' % (type(e).__name__, str(e)[:240]),
                       digest_match=(rec['stored_digest'] == hd) if rec['stored_digest'] else None)
        out['records'].append(rec)
        print(json.dumps({k: v for k, v in rec.items() if k != 'box'}), flush=True)

    # Klangfilm: the X1B replacement rule - first ten digest-verified designs with a stored mesh
    if name == 'klangfilm':
        from tools.geometry import klangfilm_lame_cli
        cur = klangfilm_lame_cli.implementation_digest()
        rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
        pool = []
        for r in rows:
            if not (r['ok'] and r['config'] == lane):
                continue
            p = json.loads((pathlib.Path('runs') / r['run'] / 'designs' / r['h'] /
                            'design.json').read_text())
            d = (((p['params'].get('grid') or {}).get('rows') or {})
                 .get('implementation_sha256'))
            if d == cur and (pathlib.Path('runs') / r['run'] / 'designs' / r['h'] /
                             'mesh.msh').is_file():
                pool.append(r)
        pool.sort(key=lambda r: (r['run'], r['h']))
        seen, verified = set(), []
        for r in pool:
            if r['h'] in seen:
                continue
            seen.add(r['h']); verified.append(r)
            if len(verified) == 10:
                break
        vrecs = []
        for r in verified:
            recipe = json.loads((pathlib.Path('runs') / r['run'] / 'designs' / r['h'] /
                                 'design.json').read_text())
            try:
                inner, outer, mode, prov, t = N1.build_one(
                    lane, r, load_config(pathlib.Path('runs') / r['run'] / 'config.yaml'), 10.0)
                vrecs.append(dict(h=r['h'], run=r['run'], built=True, mode=mode,
                                  hash_ok=bool(Design(recipe['family'],
                                                      recipe['params']).hash() == r['h']),
                                  digest_match=True, box=box_of(inner)))
            except Exception as e:
                vrecs.append(dict(h=r['h'], run=r['run'], built=False,
                                  error='%s: %s' % (type(e).__name__, str(e)[:200])))
        out['verified_replacements'] = vrecs
        print('verified replacements', len(vrecs), 'built',
              sum(1 for x in vrecs if x.get('built')), flush=True)

    if name == 'lecleach':
        # compare HEAD generator box with the stored mesh bbox (rows.pkl, metres)
        for rec in out['records']:
            if not rec.get('built'):
                continue
            r = row_for(lane, rec['h'])
            b = r['bbox']  # [xmin, ymin, zmin, xmax, ymax, zmax] metres
            stored = dict(W_mm=2.0 * (b[3] - b[0]) * 1000.0,
                          H_mm=2.0 * (b[4] - b[1]) * 1000.0,
                          D_mm=(b[5] - b[2]) * 1000.0)
            rec['stored_mesh_box'] = stored
            rec['delta_mm'] = {k: rec['box'][k] - stored[k] for k in stored}
        print('lecleach box deltas',
              [rec.get('delta_mm') for rec in out['records'] if rec.get('delta_mm')], flush=True)

    (ROOT / '.x4c' / ('rematerialize_%s.json' % name)).write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
