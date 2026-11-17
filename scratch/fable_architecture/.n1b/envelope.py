"""N1b Test 3 under contract v2 (rule 5).

Per design: sampled box (union of the 65 x 61 inner and outer records), the stored row bbox_m,
the mesh's used-node box, the tag-1 and tag-2 z extremes, and the generator's inner-native box.
Names the rear-closure and mouth-rim cause per lane instead of calling a difference a sampler
failure. For biradial: identifies which surface the stored box equals, and counts stored
biradial designs within 3.5 mm of the 600 mm (W) or 480 mm (H) limit.
Writes .n1b/envelope.json and .n1b/biradial_limit.json.
"""
import sys, json, pickle, pathlib
import numpy as np

sys.path.insert(0, 'scratch/fable_architecture/.n1'); sys.path.insert(0, '.')
import analyze as A

ROOT = pathlib.Path('scratch/fable_architecture')
LANES = ['hl__ext_throat_hvlaw_v7', 'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'rf__section_axial_home_v7', 'hl__klangfilm_lame_curved_v1', 'hl__biradial_es_style_v7']
BIRADIAL = 'hl__biradial_es_style_v7'


def ext(p, quarter=True):
    p = np.asarray(p, float)
    if p.size == 0:
        return None
    p = p.reshape(-1, 3)
    return np.array([2 * np.abs(p[:, 0]).max() if quarter else np.ptp(p[:, 0]),
                     2 * np.abs(p[:, 1]).max() if quarter else np.ptp(p[:, 1]),
                     np.ptp(p[:, 2])])


def run():
    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    bbox = {(x['run'], x['h']): x['bbox'] for x in rows if x.get('bbox')}
    res = {}
    for f in sorted((ROOT / '.n1b/build').glob('*.npz')):
        z = np.load(f)
        ln, h, run_ = str(z['lane']), str(z['design_hash']), str(z['run'])
        inner, outer, inat = z['inner'], z['outer'], z['inner_native']
        has_outer = outer.size > 0
        xyz, t1, t2, ents = A.read_msh(pathlib.Path('runs') / run_ / 'designs' / h / 'mesh.msh')
        union = np.concatenate([inner.reshape(-1, 3)] + ([outer.reshape(-1, 3)] if has_outer else []))
        sampled = ext(union)
        sampled_in = ext(inner)
        sampled_out = ext(outer) if has_outer else None
        native_in = ext(inat)
        mesh_box = ext(xyz)
        mesh_t1 = ext(xyz[t1])
        sb = np.array(bbox[(run_, h)], float) * 1000
        stored = np.array([2 * (sb[3] - sb[0]), 2 * (sb[4] - sb[1]), sb[5] - sb[2]])
        t = float(z['wall_thickness_mm'])
        rec = dict(lane=ln, h=h, run=run_, wall=t,
                   sampled=sampled, sampled_inner=sampled_in,
                   sampled_outer=sampled_out, native_inner=native_in,
                   mesh_all=mesh_box, mesh_tag1=mesh_t1, stored=stored,
                   delta_union=sampled - stored,
                   delta_inner=sampled_in - stored,
                   tag1_zmin=float(xyz[t1][:, 2].min()), tag1_zmax=float(xyz[t1][:, 2].max()),
                   tag2_zmin=float(xyz[t2][:, 2].min()) if t2 else None,
                   sampled_zmin=float(union[:, 2].min()), sampled_zmax=float(union[:, 2].max()))
        # rear closure: the mesh starts at z = -t; sampled starts at z = 0 (or rollback)
        rec['closure_delta'] = rec['tag1_zmin'] - rec['sampled_zmin']
        # mouth rim: how far the generator's outer sheet sits beyond its inner sheet (per side)
        if has_outer:
            rec['outer_over_inner_per_side_wh'] = (sampled_out[:2] - sampled_in[:2]) / 2.0
        res.setdefault(ln, []).append(rec)
        print(json.dumps({k: rec[k] for k in ('lane', 'h', 'wall', 'delta_union', 'delta_inner',
                                              'closure_delta', 'tag1_zmin', 'tag1_zmax')},
                         default=lambda o: np.round(o, 3).tolist() if isinstance(o, np.ndarray) else o),
              flush=True)
    json.dump(res, open(ROOT / '.n1b/envelope.json', 'w'), indent=1, default=lambda o: o.tolist()
              if isinstance(o, np.ndarray) else o)

    print('\nSUMMARY (mm; W/H/D deltas sampled-union minus stored, before closure correction)')
    for ln in LANES:
        d = res[ln]
        du = np.array([x['delta_union'] for x in d])
        di = np.array([x['delta_inner'] for x in d])
        cl = np.array([x['closure_delta'] for x in d])
        print(ln, 'union W %+.2f..%+.2f H %+.2f..%+.2f D %+.2f..%+.2f' %
              (du[:, 0].min(), du[:, 0].max(), du[:, 1].min(), du[:, 1].max(),
               du[:, 2].min(), du[:, 2].max()), flush=True)
        print('   inner-only W %+.2f..%+.2f H %+.2f..%+.2f | closure z-min shift %+.2f..%+.2f' %
              (di[:, 0].min(), di[:, 0].max(), di[:, 1].min(), di[:, 1].max(), cl.min(), cl.max()),
              flush=True)
        print('   D after closure %+.2f..%+.2f' %
              ((du[:, 2] - cl).min(), (du[:, 2] - cl).max()), flush=True)

    # biradial: which surface does the stored box equal?
    print('\nBIRADIAL stored-box investigation')
    ident = {'stored_eq_native_inner': 0, 'stored_eq_mesh_all': 0, 'stored_eq_sampled_inner': 0, 'n': 0}
    for x in res[BIRADIAL]:
        okn = np.allclose(x['stored'][:2], x['native_inner'][:2], atol=0.02)
        okm = np.allclose(x['stored'][:2], x['mesh_all'][:2], atol=0.02)
        oki = np.allclose(x['stored'][:2], x['sampled_inner'][:2], atol=0.02)
        ident['stored_eq_native_inner'] += int(okn)
        ident['stored_eq_mesh_all'] += int(okm)
        ident['stored_eq_sampled_inner'] += int(oki)
        ident['n'] += 1
        print(x['h'], 'stored', np.round(x['stored'], 2), 'inner', np.round(x['native_inner'], 2),
              'outer', np.round(x['sampled_outer'], 2), 'mesh', np.round(x['mesh_all'], 2),
              'eq_native', okn, 'eq_mesh', okm, flush=True)
    print('identity counts', ident, flush=True)

    # biradial designs near the envelope limits (all stored valid rows, not only the ten)
    br = [r for r in rows if r['config'] == BIRADIAL and r['ok'] and r.get('bbox')]
    near = {'n': len(br), 'w_below': [], 'w_above': [], 'h_below': [], 'h_above': []}
    for r in br:
        b = r['bbox']
        W = 2 * (b[3] - b[0]) * 1000; H = 2 * (b[4] - b[1]) * 1000
        if 0 <= 600 - W <= 3.5:
            near['w_below'].append((r['h'], round(W, 2)))
        elif 0 <= W - 600 <= 3.5:
            near['w_above'].append((r['h'], round(W, 2)))
        if 0 <= 480 - H <= 3.5:
            near['h_below'].append((r['h'], round(H, 2)))
        elif 0 <= H - 480 <= 3.5:
            near['h_above'].append((r['h'], round(H, 2)))
    print('\nBIRADIAL near-limit (600 W / 480 H, +/-3.5 mm): n=%d designs; '
          'W below %d, W above %d, H below %d, H above %d' %
          (near['n'], len(near['w_below']), len(near['w_above']),
           len(near['h_below']), len(near['h_above'])), flush=True)
    print('   w_below', near['w_below'][:8], 'h_below', near['h_below'][:8], flush=True)
    json.dump(near, open(ROOT / '.n1b/biradial_limit.json', 'w'), indent=1)


if __name__ == '__main__':
    run()
