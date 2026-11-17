"""N1 surface build: resolve each selected design's inner (and outer, where the build route
provides one) surface, resample to 65 stations x 31 azimuths, save to a per-invocation folder.

Run once per process: .n1/build.py <outdir> [--res 10]
Read-only w.r.t. runs/; writes only under the given .n1/ subfolder.
"""
import sys, json, pickle, pathlib, warnings
import numpy as np
import yaml

sys.path.insert(0, '.')
warnings.filterwarnings('ignore')

from hornlab_search.config import load_config, mesh_spec
from hornlab_search.types import Design
from hornlab_search.design import families
from hornlab_search.design.generators import grid, rolled_family
from hornlab_mesher.config_builder import resolve_geometry
from tools.geometry import klangfilm_lame

LANES = ['hl__ext_throat_hvlaw_v7', 'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'rf__section_axial_home_v7', 'hl__klangfilm_lame_curved_v1', 'hl__biradial_es_style_v7']
FIXED = {'hl__crowe_x_osse_cd_v7', 'rf__section_axial_home_v7', 'hl__klangfilm_lame_curved_v1'}
NS, NPHI = 65, 31


def sample(points, nphi, ns):
    a = np.asarray(points, float)
    t = np.linspace(0, 1, ns)
    b = []
    for mer in a:
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(mer, axis=0), axis=1))]
        if arc[-1] <= 0:
            raise ValueError('zero-length meridian')
        arc = arc / arc[-1]
        keep = np.r_[True, np.diff(arc) > 1e-12]
        b.append(np.stack([np.interp(t, arc[keep], mer[keep, k]) for k in range(3)], axis=-1))
    b = np.array(b)
    out = np.empty((nphi, ns, 3))
    for j in range(ns):
        ph = np.unwrap(np.arctan2(b[:, j, 1], b[:, j, 0]))
        if np.any(np.diff(ph) < -1e-8):
            raise ValueError('nonmonotone azimuth; no safe interpolation')
        phi = np.linspace(ph[0], ph[-1], nphi)
        for k in range(3):
            out[:, j, k] = np.interp(phi, ph, b[:, j, k])
    return out


def native(design, config, res):
    msp = mesh_spec('screen', config)
    mcfg = families.to_mesher_config(design, msp, {'throat': res, 'mouth': res, 'rear': res},
                                     pathlib.Path('<n1>'), mounting=config.mounting)
    mcfg['mesh'].update({'throat_res_mm': res, 'mouth_res_mm': res, 'rear_res_mm': res,
                         'allow_large_mesh': True})
    rg = resolve_geometry(mcfg, allow_large_mesh=True)
    outer = getattr(rg.geometry, 'outer_points', None)
    return (np.asarray(rg.geometry.inner_points, float),
            None if outer is None else np.asarray(outer, float), rg.mode,
            'hornlab_mesher.config_builder.resolve_geometry')


def build_one(lane, r, cfg, res):
    j = json.loads((pathlib.Path('runs') / r['run'] / 'designs' / r['h'] / 'design.json').read_text())
    p = j['params']
    if 'grid' not in p:
        inner, outer, mode, prov = native(Design(j['family'], p), cfg, res)
        return inner, outer, 'native', prov, float(p.get('wall_thickness_mm') or 0.0)
    b = p['grid']
    rows = b.get('rows') or {}
    t = float(b.get('wall_thickness_mm') or 0.0)
    if rows.get('schema') == klangfilm_lame.SCHEMA:
        shape = {k: b['knobs']['g_' + k] for k in
                 klangfilm_lame.SHAPE_KEYS - {'n_phi', 'n_s', 'wall_thickness_mm'}}
        shape.update({k: b[k] for k in ('n_phi', 'n_s', 'wall_thickness_mm')})
        inner, meta = klangfilm_lame.make_grid(shape, cfg.brief)
        outer = grid.grid_outer_points(inner, t)
        return inner, outer, 'klangfilm', 'tools.geometry.klangfilm_lame.make_grid', t
    if rolled_family.is_family_spec(b):
        g = rolled_family.resolve_grid(b, cfg.brief)
        return (np.asarray(g['inner_points'], float), np.asarray(g['outer_points'], float),
                'rolled', 'hornlab_search.design.generators.rolled_family.resolve_grid', t)
    inner, meta = grid.grid_points(b, b.get('knobs', {}), cfg.brief)
    outer = grid.grid_outer_points(inner, t)
    return inner, outer, 'grid', 'hornlab_search.design.generators.grid.grid_points+grid_outer_points', t


def selection():
    rows = pickle.load(open('scratch/fable_architecture/.fable/rows.pkl', 'rb'))
    by = {}
    # five lanes: reuse the ten .x1 npz records
    for f in sorted(pathlib.Path('scratch/fable_architecture/.x1').glob('*.npz')):
        z = np.load(f)
        ln = str(z['lane'])
        if ln == 'hl__klangfilm_lame_curved_v1':
            continue
        by.setdefault(ln, []).append((str(z['design_hash']), str(z['run'])))
    # klangfilm: ten hashes from legacy_k_results.txt
    kh = []
    for line in pathlib.Path('scratch/fable_architecture/.x1/legacy_k_results.txt').read_text().splitlines():
        if line.strip():
            kh.append(line.split()[0])
    h2run = {r['h']: r['run'] for r in rows if r['config'] == 'hl__klangfilm_lame_curved_v1' and r['ok']}
    by['hl__klangfilm_lame_curved_v1'] = [(h, h2run[h]) for h in kh if h in h2run]
    out = []
    for ln in LANES:
        seen = set()
        for h, run in by.get(ln, []):
            if h in seen:
                continue
            seen.add(h)
            r = next((x for x in rows if x['run'] == run and x['h'] == h), None)
            if r is not None:
                out.append((ln, r))
        print(ln, 'selected', len(seen), flush=True)
    return out


def main():
    outdir = pathlib.Path(sys.argv[1])
    res = 10.0
    if '--res' in sys.argv:
        res = float(sys.argv[sys.argv.index('--res') + 1])
    outdir.mkdir(parents=True, exist_ok=True)
    for lane, r in selection():
        cfg = load_config(pathlib.Path('runs') / r['run'] / 'config.yaml')
        try:
            inner, outer, mode, prov, t = build_one(lane, r, cfg, res)
            ci = sample(inner, NPHI, NS)
            co = None if outer is None else sample(outer, NPHI, NS)
            np.savez_compressed(outdir / (r['h'] + '.npz'), inner=ci,
                                outer=(np.zeros((0, 0, 0)) if co is None else co),
                                lane=lane, design_hash=r['h'], run=r['run'], mode=mode,
                                provenance=prov, wall_thickness_mm=t, res_mm=res,
                                native_inner_shape=np.array(inner.shape),
                                native_outer_shape=np.array((0, 0, 0) if outer is None else outer.shape))
            print(lane, r['h'], mode, 'inner', inner.shape,
                  'outer', None if outer is None else outer.shape, 'res', res, flush=True)
        except Exception as e:
            import traceback; traceback.print_exc()
            print('FAILED', lane, r['h'], type(e).__name__, str(e)[:200], flush=True)


if __name__ == '__main__':
    main()
