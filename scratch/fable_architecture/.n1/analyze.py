"""N1 analysis: determinism, refinement, inner-wall mesh agreement, envelope, metadata.

Reads .n1/build1, .n1/build2, .n1/build_ref and the stored meshes. Writes .n1/results.json.
"""
import sys, json, pathlib, collections, warnings
import numpy as np, yaml
from scipy.spatial import cKDTree

sys.path.insert(0, '.')
warnings.filterwarnings('ignore')

ROOT = pathlib.Path('scratch/fable_architecture')
B1, B2, BR = ROOT / '.n1/build1', ROOT / '.n1/build2', ROOT / '.n1/build_ref'
LANES = ['hl__ext_throat_hvlaw_v7', 'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'rf__section_axial_home_v7', 'hl__klangfilm_lame_curved_v1', 'hl__biradial_es_style_v7']
FIXED = {'hl__crowe_x_osse_cd_v7', 'rf__section_axial_home_v7', 'hl__klangfilm_lame_curved_v1'}
NPHI, NS = 31, 65


def patch_distance(pts, grid):
    a = grid[:-1, :-1].reshape(-1, 3)
    b = grid[1:, :-1].reshape(-1, 3) - a
    c = grid[:-1, 1:].reshape(-1, 3) - a
    d = grid[1:, 1:].reshape(-1, 3) - a - b - c
    centres = a + .5 * b + .5 * c + .25 * d
    inds = cKDTree(centres).query(pts, k=12)[1]
    out = []
    for start in range(0, len(pts), 1000):
        pp = pts[start:start + 1000, None, :]
        idx = inds[start:start + 1000]
        A, B, C, D = a[idx], b[idx], c[idx], d[idx]
        u = np.full(idx.shape, .5)
        v = u.copy()
        for _ in range(14):
            res = A + u[..., None] * B + v[..., None] * C + (u * v)[..., None] * D - pp
            du = B + v[..., None] * D
            dv = C + u[..., None] * D
            aa = np.sum(du * du, axis=-1)
            bb = np.sum(du * dv, axis=-1)
            cc = np.sum(dv * dv, axis=-1)
            rr = np.sum(du * res, axis=-1)
            ss = np.sum(dv * res, axis=-1)
            det = np.maximum(aa * cc - bb * bb, 1e-14)
            u = np.clip(u - (cc * rr - bb * ss) / det, 0, 1)
            v = np.clip(v - (aa * ss - bb * rr) / det, 0, 1)
        err = np.linalg.norm(A + u[..., None] * B + v[..., None] * C + (u * v)[..., None] * D - pp, axis=-1)
        out.extend(err.min(axis=1))
    return np.array(out)


def read_msh(path):
    txt = pathlib.Path(path).read_text()
    a = txt.index('$Nodes') + 7
    b = txt.index('$EndNodes')
    block = txt[a:b].strip().split('\n')
    nd = np.array(' '.join(block[1:]).split(), float).reshape(-1, 4)
    ids = nd[:, 0].astype(np.int64)
    xyz = nd[:, 1:] * 1000.0
    idx = {int(i): k for k, i in enumerate(ids)}
    e0 = txt.index('$Elements') + 10
    e1 = txt.index('$EndElements')
    t1, t2 = set(), set()
    ents = collections.Counter()
    for line in txt[e0:e1].split('\n')[1:]:
        p = line.split()
        if len(p) >= 8 and p[1] == '2':
            if p[3] == '1':
                t1.update(idx[int(x)] for x in p[-3:])
                ents[p[4]] += 1
            elif p[3] == '2':
                t2.update(idx[int(x)] for x in p[-3:])
    return xyz, sorted(t1), sorted(t2), dict(ents)


def descriptor(inner):
    """32-station H/V/45-degree radial curves, depth, wall angle, section area/aspect/index."""
    out = {}
    ph = np.arctan2(inner[:, -1, 1], inner[:, -1, 0])
    i_h, i_v = 0, len(inner) - 1
    i_d = int(np.argmin(np.abs(ph - np.pi / 4)))
    st = np.linspace(0, NS - 1, 32).astype(int)
    for nm, i in (('h', i_h), ('v', i_v), ('d', i_d)):
        ri = np.hypot(inner[i, :, 0], inner[i, :, 1])[st]
        z = inner[i, :, 2][st]
        out[nm + '_r'] = ri
        out[nm + '_z'] = z
        dr = np.diff(ri)
        dz = np.diff(z)
        out[nm + '_psi_deg'] = np.degrees(np.arctan2(dr, np.where(np.abs(dz) < 1e-9, 1e-9, dz)))
    r = np.hypot(inner[..., 0], inner[..., 1])
    area = np.zeros(NS)
    for j in range(NS):
        x, y = inner[:, j, 0], inner[:, j, 1]
        area[j] = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    out['area'] = area[st]
    out['aspect'] = (np.ptp(inner[0, st, 0]) / np.maximum(np.ptp(inner[-1, st, 1]), 1e-12)) * \
        np.ones(len(st)) if False else (r[0, st] / np.maximum(r[-1, st], 1e-12))
    return out


def rel_change(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    m = np.maximum(np.abs(a), 1e-9)
    return float(np.max(np.abs(b - a) / m))


def classify_termination(lane, block, inner):
    rows = (block.get('rows') or {}) if block else {}
    rt = str(rows.get('type', ''))
    if 'rollback' in rt:
        return 'rollback', 'recipe:design.json params.grid.rows.type=' + rt
    if rt.startswith('rolled_family'):
        return 'rollback', 'recipe:design.json params.grid.rows.type=' + rt
    if rt == 'klangfilm_lame':
        return 'rollback', 'recipe:design.json params.grid.rows.type=' + rt
    z = inner[:, :, 2]
    nonmono = int(np.sum(np.diff(z, axis=1).min(axis=1) < -1e-6))
    return ('not found (recipe/config silent; measured non-monotone-z azimuths: %d/%d)' % (nonmono, len(inner)),
            'not found')


def metadata(lane, r, cv, inner):
    p = json.loads((pathlib.Path('runs') / r['run'] / 'designs' / r['h'] / 'design.json').read_text())['params']
    brief = cv.get('brief') or {}
    fields = {}
    block = p.get('grid') if isinstance(p, dict) else None
    knobs = (block or {}).get('knobs') or {}
    rows = (block or {}).get('rows') or {}
    driver = brief.get('driver') or {}
    # throat radius
    if block is None and p.get('r0_mm') is not None:
        fields['throat_radius_mm'] = (float(p['r0_mm']), 'recipe:design.json params.r0_mm')
    elif 'g_r0_mm' in knobs:
        fields['throat_radius_mm'] = (float(knobs['g_r0_mm']), 'recipe:design.json params.grid.knobs.g_r0_mm')
    elif rows.get('driver', {}).get('exit_radius_mm') is not None:
        fields['throat_radius_mm'] = (float(rows['driver']['exit_radius_mm']), 'recipe:design.json params.grid.rows.driver.exit_radius_mm')
    elif driver.get('exit_radius_mm') is not None:
        fields['throat_radius_mm'] = (float(driver['exit_radius_mm']), 'config:config.yaml brief.driver.exit_radius_mm')
    else:
        fields['throat_radius_mm'] = (None, 'not found')
    # exit angle
    if rows.get('driver', {}).get('exit_angle_deg') is not None:
        fields['exit_angle_deg'] = (float(rows['driver']['exit_angle_deg']), 'recipe:design.json params.grid.rows.driver.exit_angle_deg')
    elif driver.get('exit_angle_deg') is not None:
        fields['exit_angle_deg'] = (float(driver['exit_angle_deg']), 'config:config.yaml brief.driver.exit_angle_deg')
    else:
        fields['exit_angle_deg'] = (None, 'not found')
    # symmetry / quadrants
    fields['symmetry'] = ((brief.get('symmetry')), 'config:config.yaml brief.symmetry')
    fields['quadrants'] = (((cv.get('mesh') or {}).get('quadrants')), 'config:config.yaml mesh.quadrants')
    # wall thickness
    if isinstance(p, dict) and p.get('wall_thickness_mm') is not None:
        fields['wall_thickness_mm'] = (float(p['wall_thickness_mm']), 'recipe:design.json params.wall_thickness_mm')
    elif block is not None and block.get('wall_thickness_mm') is not None:
        fields['wall_thickness_mm'] = (float(block['wall_thickness_mm']), 'recipe:design.json params.grid.wall_thickness_mm')
    else:
        fields['wall_thickness_mm'] = (None, 'not found')
    # source cap settings
    src = brief.get('source')
    fields['source_cap'] = (json.dumps(src, sort_keys=True) if src is not None else None,
                            'config:config.yaml brief.source' if src is not None else 'not found')
    # termination kind
    kind, where = classify_termination(lane, block, inner)
    fields['termination_kind'] = (kind, where)
    # mounting
    mount = brief.get('mounting')
    fields['mounting'] = ('none' if not mount else json.dumps(mount, sort_keys=True),
                          'config:config.yaml brief.mounting' + (' absent -> none' if not mount else ''))
    return fields


def main():
    import pickle
    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    bbox = {(x['run'], x['h']): x['bbox'] for x in rows if x.get('bbox')}
    res = {'determinism': {}, 'refinement': {}, 'mesh_agreement': {}, 'envelope': {},
           'metadata': {}, 'notes': []}
    files = sorted(B1.glob('*.npz'))
    per_lane = collections.defaultdict(list)
    for f in files:
        z = np.load(f, allow_pickle=False)
        ln, h, run = str(z['lane']), str(z['design_hash']), str(z['run'])
        inner = z['inner']; outer = z['outer']
        has_outer = outer.size > 0
        z2 = np.load(B2 / (h + '.npz'), allow_pickle=False)
        zr = np.load(BR / (h + '.npz'), allow_pickle=False)
        det = bool(np.array_equal(inner, z2['inner']) and
                   (not has_outer or np.array_equal(outer, z2['outer'])))
        per_lane[ln].append(dict(h=h, run=run, det=det, has_outer=has_outer))
        # refinement (native lanes only)
        if ln not in FIXED:
            d = np.linalg.norm(inner - zr['inner'], axis=-1)
            db = descriptor(inner); dr = descriptor(zr['inner'])
            rel = {k: rel_change(db[k], dr[k]) for k in db if not k.endswith('psi_deg')}
            psi = float(np.max(np.abs(db['h_psi_deg'] - dr['h_psi_deg'])))
            res['refinement'].setdefault(ln, []).append(
                dict(h=h, max_point_mm=float(d.max()), p99_mm=float(np.quantile(d, .99)),
                     max_descriptor_rel=float(max(rel.values())), max_psi_deg=psi,
                     worst_desc=max(rel.items(), key=lambda kv: kv[1])[0]))
        # mesh agreement
        mpath = pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh'
        xyz, t1, t2, ents = read_msh(mpath)
        pts = xyz[t1]
        din = patch_distance(pts, inner)
        if has_outer:
            dout = patch_distance(pts, outer)
            assign_in = din <= dout
            nearest = np.minimum(din, dout)
            unassigned = nearest > 3.0
            scored = assign_in & ~unassigned
            partial = False
        else:
            assign_in = np.ones(len(pts), bool)
            nearest = din
            unassigned = np.zeros(len(pts), bool)
            scored = din <= 1.0
            partial = True
        q = np.quantile(din[scored], [.5, .99]) if scored.any() else [np.nan, np.nan]
        res['mesh_agreement'].setdefault(ln, []).append(dict(
            h=h, run=run, n_tag1=int(len(pts)), n_inner=int(assign_in.sum()),
            n_outer=int((~assign_in).sum()), n_unassigned=int(unassigned.sum()),
            n_scored=int(scored.sum()), median_mm=float(q[0]), p99_mm=float(q[1]),
            partial=partial, pass_=bool(not partial and q[0] <= 0.3 and q[1] <= 1.0)))
        # envelope
        allpts = np.concatenate([inner.reshape(-1, 3)] +
                                ([outer.reshape(-1, 3)] if has_outer else []))
        full = np.array([2 * np.abs(allpts[:, 0]).max(), 2 * np.abs(allpts[:, 1]).max(),
                         np.ptp(allpts[:, 2])])
        sb = np.array(bbox[(run, h)], float) * 1000
        stored = np.array([2 * (sb[3] - sb[0]), 2 * (sb[4] - sb[1]), sb[5] - sb[2]])
        res['envelope'].setdefault(ln, []).append(dict(h=h, sampled=full.tolist(), stored=stored.tolist(),
                                                       delta=(full - stored).tolist(),
                                                       tag2_z_min_mm=float(xyz[t2][:, 2].min()) if t2 else None,
                                                       tag1_z_min_mm=float(pts[:, 2].min())))
        # metadata
        cv = yaml.safe_load((pathlib.Path('runs') / run / 'config.yaml').read_text())
        res['metadata'].setdefault(ln, []).append(dict(h=h, fields=metadata(ln, dict(run=run, h=h), cv, inner)))
    # determinism summary
    for ln in LANES:
        d = per_lane[ln]
        res['determinism'][ln] = dict(n=len(d), identical=sum(x['det'] for x in d),
                                      has_outer=sum(x['has_outer'] for x in d))
    # mesh agreement summary
    for ln in LANES:
        d = res['mesh_agreement'][ln]
        res['mesh_agreement'][ln] = dict(rows=d,
                                         n_pass=sum(x['pass_'] for x in d),
                                         median_of_medians=float(np.median([x['median_mm'] for x in d])),
                                         worst_p99=float(np.max([x['p99_mm'] for x in d])),
                                         partial=any(x['partial'] for x in d))
    for ln in LANES:
        d = res['refinement'].get(ln)
        if d:
            res['refinement'][ln] = dict(rows=d, n=len(d), n_pass=sum(x['max_point_mm'] <= 0.2 for x in d),
                                         worst=float(max(x['max_point_mm'] for x in d)),
                                         worst_desc=float(max(x['max_descriptor_rel'] for x in d)))
        else:
            res['refinement'][ln] = 'fixed-resolution recipe: not testable by refinement'
    (ROOT / '.n1/results_partial.json').write_text(json.dumps(res, indent=1, default=str))
    print('determinism', json.dumps({k: v['identical'] for k, v in res['determinism'].items()}))
    print('refinement', json.dumps({k: (v if isinstance(v, str) else {'n_pass': v['n_pass'], 'worst': round(v['worst'], 4),
                                                                     'worst_desc': round(v['worst_desc'], 5)})
                                    for k, v in res['refinement'].items()}))
    print('mesh', json.dumps({k: {'n_pass': v['n_pass'], 'median_of_medians': round(v['median_of_medians'], 4),
                                  'worst_p99': round(v['worst_p99'], 4), 'partial': v['partial']}
                              for k, v in res['mesh_agreement'].items()}))
    print('envelope (sampled W/H/D):')
    for ln in LANES:
        print(' ', ln, [(x['h'], [round(v, 2) for v in x['sampled']]) for x in res['envelope'][ln]])


if __name__ == '__main__':
    main()
