"""N1 path test: can we resolve inner+outer exactly as the build route for each lane?"""
import pickle, json, pathlib, warnings, sys
import numpy as np, yaml
warnings.filterwarnings('ignore')
sys.path.insert(0, '.')
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.types import Design
from hornlab_search.design import families
from hornlab_search.design.generators import grid, rolled_family
from hornlab_mesher.config_builder import resolve_geometry
from tools.geometry import klangfilm_lame

rows = pickle.load(open('scratch/fable_architecture/.fable/rows.pkl', 'rb'))
LANES = ['hl__ext_throat_hvlaw_v7', 'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'rf__section_axial_home_v7', 'hl__klangfilm_lame_curved_v1', 'hl__biradial_es_style_v7']

def native_outer(design, config, res=10):
    msp = mesh_spec('screen', config)
    mcfg = families.to_mesher_config(design, msp, {'throat': res, 'mouth': res, 'rear': res},
                                     pathlib.Path('<n1-test>'), mounting=config.mounting)
    mcfg['mesh'].update({'throat_res_mm': res, 'mouth_res_mm': res, 'rear_res_mm': res,
                         'allow_large_mesh': True})
    rg = resolve_geometry(mcfg, allow_large_mesh=True)
    return (np.asarray(rg.geometry.inner_points, float),
            None if getattr(rg.geometry, 'outer_points', None) is None
            else np.asarray(rg.geometry.outer_points, float), rg.mode)

for ln in LANES:
    r = [x for x in rows if x['config'] == ln and x['ok']][0]
    run = pathlib.Path('runs') / r['run']
    d = run / 'designs' / r['h']
    j = json.load(open(d / 'design.json'))
    cfg = load_config(run / 'config.yaml')
    print('\n==', ln)
    try:
        if 'grid' not in j['params']:
            inner, outer, mode = native_outer(Design(j['family'], j['params']), cfg)
            print(' native mode', mode, 'inner', inner.shape, 'outer', None if outer is None else outer.shape)
        else:
            b = j['params']['grid']
            if klangfilm_lame.SCHEMA == (b.get('rows') or {}).get('schema'):
                shape = {k: b['knobs']['g_' + k] for k in klangfilm_lame.SHAPE_KEYS - {'n_phi', 'n_s', 'wall_thickness_mm'}}
                shape.update({k: b[k] for k in ('n_phi', 'n_s', 'wall_thickness_mm')})
                inner, meta = klangfilm_lame.make_grid(shape, cfg.brief)
                outer = grid.grid_outer_points(inner, b['wall_thickness_mm'])
                print(' klangfilm inner', inner.shape, 'outer', outer.shape, 'r0', meta['r0_mm'])
            elif rolled_family.is_family_spec(b):
                g = rolled_family.resolve_grid(b, cfg.brief)
                inner, outer = g['inner_points'], g['outer_points']
                print(' rolled inner', inner.shape, 'outer', outer.shape)
            else:
                inner, meta = grid.grid_points(b, b.get('knobs', {}), cfg.brief)
                outer = grid.grid_outer_points(inner, b['wall_thickness_mm'])
                print(' grid inner', inner.shape, 'outer', outer.shape, 'meta keys', sorted(meta)[:12])
        # extents check vs stored bbox
        pts = outer if 'outer' in dir() and outer is not None else inner
        bb = np.array([pts[..., 0].min(), pts[..., 1].min(), pts[..., 2].min(),
                       pts[..., 0].max(), pts[..., 1].max(), pts[..., 2].max()])
        full = np.array([2 * bb[3], 2 * bb[4], bb[5] - bb[2]])
        stored = np.array(r['bbox'], float) * 1000
        print(' sampled full W/H/D', full.round(2), 'stored', [round(2 * (stored[3] - stored[0]), 2),
              round(2 * (stored[4] - stored[1]), 2), round(stored[5] - stored[2], 2)])
    except Exception as e:
        import traceback; traceback.print_exc()
