"""A8 addendum: ROSSE digest-bypass geometry check.

The stored `hl__rosse_rect_cd_v7` recipes carry `implementation_sha256 = 9b040e37...`.  That
digest was produced by `rosse_rect_cli.implementation_digest()` at `406dc50` (the commit that
added the lane).  HEAD `601056d0...` differs only because `tools/geometry/rosse_rect.py` gained a
widened `b` lower bound and its comment in commit `a10e784`; `make_grid` itself is unchanged.

This script rebuilds the 11 `.x4`-selected grids through the same in-process bridge the other CLI
wrappers install (`rosse_rect_cli.install()`), and bypasses ONLY the persisted-digest equality:
`rolled_rect_cli._check_rows` is wrapped to substitute HEAD's current digest into an in-memory
copy of the rows metadata before calling the original, so the schema and driver checks still run.
No source, config or run file is modified.

Then, exactly as `.n1b/inner.py`: isolate the stored mesh's tag-1 inner sheet, and measure the
patch distance from those nodes to the rebuilt 65 x 61 inner surface (and to the rebuilt native
points), plus the sampled bounding box against the stored `bbox_m`.

Writes `.x4c/rosse_bypass.json` and `.x4c/rosse_bypass.txt`.
"""
import sys, json, copy, pickle, pathlib, importlib.util as ilu
import numpy as np

sys.path.insert(0, 'scratch/fable_architecture/.n1')
sys.path.insert(0, '.')
import analyze as A
from hornlab_search.config import load_config
from hornlab_search.design.generators import grid
from hornlab_search.types import Design


def _load(name, path):
    s = ilu.spec_from_file_location(name, path)
    m = ilu.module_from_spec(s); s.loader.exec_module(m); return m


C = _load('n1_comp', 'scratch/fable_architecture/.n1/component_check.py')
_s = ilu.spec_from_file_location('n1_build', 'scratch/fable_architecture/.n1/build.py')
N1 = ilu.module_from_spec(_s); _s.loader.exec_module(N1)

ROOT = pathlib.Path('scratch/fable_architecture')
LANE = 'hl__rosse_rect_cd_v7'
NPHI, NS = 61, 65


def sampled(pts):
    return N1.sample(np.asarray(pts, float), NPHI, NS)


def isolate(pts, T, inner_rec):
    comp, cr = C.components(T, pts)
    info = []
    for key, faces in comp.items():
        nodes = sorted(set(T[faces].reshape(-1).tolist()))
        p = pts[nodes]
        sel = p if len(p) <= 800 else p[np.linspace(0, len(p) - 1, 800).astype(int)]
        d = A.patch_distance(sel, inner_rec)
        area = 0.5 * np.linalg.norm(np.cross(pts[T[faces, 1]] - pts[T[faces, 0]],
                                            pts[T[faces, 2]] - pts[T[faces, 0]]), axis=1).sum()
        info.append(dict(nodes=nodes, area_cm2=float(area / 100),
                         med_mm=float(np.median(d))))
    cands = [x for x in info if x['med_mm'] <= 0.5]
    chosen = max(cands, key=lambda x: len(x['nodes'])) if cands else min(info, key=lambda x: x['med_mm'])
    return chosen, info


def reproducible(chosen, info):
    biggest = max(info, key=lambda x: x['area_cm2'])
    return chosen['area_cm2'] >= 0.1 * biggest['area_cm2']


def quant(d):
    q = np.quantile(d, [.5, .99])
    return dict(median_mm=float(q[0]), p99_mm=float(q[1]), max_mm=float(d.max()),
                gt1=int((d > 1.0).sum()), n=int(len(d)))


def box(inner, outer):
    pts = inner if outer is None else np.vstack([inner.reshape(-1, 3), outer.reshape(-1, 3)])
    return dict(W_mm=2.0 * float(np.max(np.abs(pts[:, 0]))),
                H_mm=2.0 * float(np.max(np.abs(pts[:, 1]))),
                D_mm=float(np.ptp(pts[:, 2])))


def stored_box(r):
    b = r['bbox']
    return dict(W_mm=2.0 * (b[3] - b[0]) * 1000.0,
                H_mm=2.0 * (b[4] - b[1]) * 1000.0,
                D_mm=(b[5] - b[2]) * 1000.0)


def main():
    from tools.geometry import rosse_rect_cli, rolled_rect_cli as bridge
    rosse_rect_cli.install()
    original_check = bridge._check_rows

    def check_no_digest(spec, brief=None, *, require_digest=False):
        s = copy.deepcopy(spec)
        rows = s.get('rows') or {}
        if rows.get('implementation_sha256') is not None:
            # the ONLY bypass: make the persisted digest equal HEAD's for an in-memory copy
            s['rows']['implementation_sha256'] = rosse_rect_cli.implementation_digest()
        return original_check(s, brief, require_digest=require_digest)

    bridge._check_rows = check_no_digest

    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    hashes = [x['hash'] for x in json.loads(
        (ROOT / '.x4/generated_geometry_fifth.json').read_text())[LANE]['results']]
    out = dict(lane=LANE, head_digest=rosse_rect_cli.implementation_digest(),
               stored_digest_sample='9b040e3782ad2dcffeafcde901050f9932c32378e8ec1a5b6fb9992cb807c8c4',
               bypass='rolled_rect_cli._check_rows wrapped: in-memory rows copy gets HEAD digest; '
                      'schema and driver checks still run; no file modified',
               records=[])
    for h in hashes:
        r = next(x for x in rows if x['ok'] and x['config'] == LANE and x['h'] == h)
        cfg = load_config(pathlib.Path('runs') / r['run'] / 'config.yaml')
        recipe = json.loads((pathlib.Path('runs') / r['run'] / 'designs' / h /
                             'design.json').read_text())
        block = recipe['params']['grid']
        t = float(block.get('wall_thickness_mm') or 3.0)
        inner, meta = grid.rows_grid_points(block, block.get('knobs', {}), cfg.brief)
        outer = grid.grid_outer_points(inner, t)
        rec_pts = sampled(inner)
        nat_pts = np.asarray(inner, float)
        rec = dict(h=h, run=r['run'],
                   hash_ok=bool(Design(recipe['family'], recipe['params']).hash() == h),
                   shape=list(np.shape(inner)),
                   stored_digest=block['rows'].get('implementation_sha256'),
                   built_digest=meta.get('implementation_sha256'))
        pts, T = C.parse(pathlib.Path('runs') / r['run'] / 'designs' / h / 'mesh.msh')
        chosen, info = isolate(pts, T, rec_pts)
        nodes = chosen['nodes']
        if not reproducible(chosen, info):
            rec.update(reproducible=False, n_components=len(info), n_nodes=len(nodes),
                       note='no component within 0.5 mm is a real inner sheet')
        else:
            p = pts[nodes]
            rec.update(reproducible=True, n_components=len(info), n_nodes=len(nodes),
                       record=quant(A.patch_distance(p, rec_pts)),
                       native=quant(A.patch_distance(p, nat_pts)))
        sb = stored_box(r)
        nb = box(inner, outer)
        rb = box(sampled(inner), sampled(outer))
        # rear closure exactly as .n1b/envelope.py: tag-1 z-min against the sampled z-min
        xyz, t1, _t2, _ents = A.read_msh(pathlib.Path('runs') / r['run'] / 'designs' / h /
                                         'mesh.msh')
        sampled_zmin = float(np.vstack([rec_pts.reshape(-1, 3),
                                        sampled(outer).reshape(-1, 3)])[:, 2].min())
        closure_delta = float(xyz[t1][:, 2].min() - sampled_zmin)
        rec.update(stored_box=sb, native_box=nb, record_box=rb,
                   delta_native={k: nb[k] - sb[k] for k in sb},
                   delta_record={k: rb[k] - sb[k] for k in sb},
                   tag1_zmin=float(xyz[t1][:, 2].min()), sampled_zmin=sampled_zmin,
                   closure_delta=closure_delta,
                   D_after_closure=float(rb['D_mm'] - sb['D_mm'] - closure_delta))
        out['records'].append(rec)
        print(json.dumps({k: v for k, v in rec.items()
                          if k not in ('stored_box', 'native_box', 'record_box')}), flush=True)

    good = [x for x in out['records'] if x.get('reproducible')]
    if good:
        floor = max(x['native']['p99_mm'] for x in good)
        rec_p99 = max(x['record']['p99_mm'] for x in good)
        thr = max(1.0, 1.25 * floor)
        out['summary'] = dict(
            n=len(out['records']), built=len(out['records']),
            hash_ok=sum(1 for x in out['records'] if x.get('hash_ok')),
            reproducible=len(good),
            native_floor_p99=floor, record_p99=rec_p99, threshold=thr,
            median_max=max(x['record']['median_mm'] for x in good),
            pass_lane=bool(all(x['record']['median_mm'] <= 0.3 for x in good) and rec_p99 <= thr),
            delta_native_W=[min(x['delta_native']['W_mm'] for x in good),
                            max(x['delta_native']['W_mm'] for x in good)],
            delta_native_H=[min(x['delta_native']['H_mm'] for x in good),
                            max(x['delta_native']['H_mm'] for x in good)],
            delta_native_D=[min(x['delta_native']['D_mm'] for x in good),
                            max(x['delta_native']['D_mm'] for x in good)],
            delta_record_W=[min(x['delta_record']['W_mm'] for x in good),
                            max(x['delta_record']['W_mm'] for x in good)],
            delta_record_H=[min(x['delta_record']['H_mm'] for x in good),
                            max(x['delta_record']['H_mm'] for x in good)],
            delta_record_D=[min(x['delta_record']['D_mm'] for x in good),
                            max(x['delta_record']['D_mm'] for x in good)],
            closure_delta=[min(x['closure_delta'] for x in good),
                           max(x['closure_delta'] for x in good)],
            D_after_closure=[min(x['D_after_closure'] for x in good),
                             max(x['D_after_closure'] for x in good)],
        )
        print('SUMMARY', json.dumps(out['summary']), flush=True)
    (ROOT / '.x4c/rosse_bypass.json').write_text(json.dumps(out, indent=1))

    lines = ['=' * 78, '%s  HEAD digest %s  stored %s' %
             (LANE, out['head_digest'][:10], out['stored_digest_sample'][:10]),
             'bypass: ' + out['bypass']]
    for x in out['records']:
        if x.get('reproducible'):
            lines.append('  %s %s shape %s  median %.3f  p99 %.3f  native p99 %.3f  '
                         'box delta W %+.2f H %+.2f D %+.2f (D after closure %+.2f)' %
                         (x['h'], x['run'], x['shape'], x['record']['median_mm'],
                          x['record']['p99_mm'], x['native']['p99_mm'],
                          x['delta_record']['W_mm'], x['delta_record']['H_mm'],
                          x['delta_record']['D_mm'], x['D_after_closure']))
        else:
            lines.append('  %s %s NOT REPRODUCIBLE %s' % (x['h'], x['run'], x.get('note')))
    if 'summary' in out:
        s = out['summary']
        lines.append('  LANE n=%d hash %d/%d reproducible %d/%d  native floor p99 %.3f  '
                     'record p99 %.3f  thr %.3f  max median %.3f  %s' %
                     (s['n'], s['hash_ok'], s['n'], s['reproducible'], s['n'],
                      s['native_floor_p99'], s['record_p99'], s['threshold'],
                      s['median_max'], 'PASS' if s['pass_lane'] else 'FAIL'))
        lines.append('  box deltas (record - stored, mm): W %+.2f..%+.2f  H %+.2f..%+.2f  '
                     'D %+.2f..%+.2f  closure %+.2f..%+.2f  D after closure %+.2f..%+.2f' %
                     (*s['delta_record_W'], *s['delta_record_H'], *s['delta_record_D'],
                      *s['closure_delta'], *s['D_after_closure']))
    (ROOT / '.x4c/rosse_bypass.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
