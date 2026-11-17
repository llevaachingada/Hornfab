"""X4 completion: Test 2 (inner-wall agreement) for the five `.x4` lanes under contract v2.

Same method as `.n1b/inner.py` (unchanged topology-based inner-sheet isolation), applied to the
`.x4c/build` records (65 stations x 61 azimuths).  Reports, per lane: native-floor p99 (stored
mesh nodes against the generator's own native points), canonical-record p99, threshold
max(1.0, 1.25 x floor), median-of-medians, per-design pass, and the v2 rule-2 verdict.

Writes `.x4c/inner.json` and `.x4c/inner_summary.json`.
"""
import sys, json, pathlib, importlib.util as ilu
import numpy as np

sys.path.insert(0, 'scratch/fable_architecture/.n1')
sys.path.insert(0, '.')
import analyze as A


def _load(name, path):
    s = ilu.spec_from_file_location(name, path)
    m = ilu.module_from_spec(s); s.loader.exec_module(m); return m


C = _load('n1_comp', 'scratch/fable_architecture/.n1/component_check.py')
ROOT = pathlib.Path('scratch/fable_architecture')
LANES = ['hl__osse_rrect_fold_warm_v7', 'hl__ext_throat_hvlaw_v7',
         'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'hl__biradial_es_style_v7']


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


def run():
    res = {}
    for f in sorted((ROOT / '.x4c/build').glob('*.npz')):
        z = np.load(f)
        ln, h, run = str(z['lane']), str(z['design_hash']), str(z['run'])
        pts, T = C.parse(pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh')
        chosen, info = isolate(pts, T, z['inner'])
        nodes = chosen['nodes']
        p = pts[nodes]
        if not reproducible(chosen, info):
            rec = dict(lane=ln, h=h, run=run, n_components=len(info), n_nodes=len(nodes),
                       area_cm2=chosen['area_cm2'],
                       largest_area_cm2=max(x['area_cm2'] for x in info),
                       reproducible=False,
                       note='no component within 0.5 mm is a real surface')
            res.setdefault(ln, []).append(rec)
            print(json.dumps(rec), flush=True)
            continue
        d_rec = A.patch_distance(p, z['inner'])
        d_nat = A.patch_distance(p, z['inner_native'])
        rec = dict(lane=ln, h=h, run=run, n_components=len(info), n_nodes=len(nodes),
                   area_cm2=chosen['area_cm2'], reproducible=True,
                   record=quant(d_rec), native=quant(d_nat))
        res.setdefault(ln, []).append(rec)
        print(json.dumps(rec), flush=True)
    json.dump(res, open(ROOT / '.x4c/inner.json', 'w'), indent=1)

    print('\nSUMMARY  (record 65 stations x 61 azimuths; v2 rule 2)')
    summary = {}
    for ln in LANES:
        d = res.get(ln, [])
        bad = [x for x in d if not x['reproducible']]
        if not d:
            summary[ln] = dict(n=0, note='no record')
            print(ln, 'NO RECORDS', flush=True)
            continue
        if bad:
            summary[ln] = dict(n=len(d), reproducible=False, n_not_reproducible=len(bad),
                               not_reproducible=[x['h'] for x in bad])
            print(ln, 'NOT REPRODUCIBLE: %d/%d' % (len(bad), len(d)), flush=True)
            continue
        floor = max(x['native']['p99_mm'] for x in d)
        rec_p99 = max(x['record']['p99_mm'] for x in d)
        thr = max(1.0, 1.25 * floor)
        per_design = sum(x['record']['median_mm'] <= 0.3 and
                         x['record']['p99_mm'] <= max(1.0, 1.25 * x['native']['p99_mm'])
                         for x in d)
        summary[ln] = dict(n=len(d), native_floor_p99=floor, record_p99=rec_p99, threshold=thr,
                           median_max=max(x['record']['median_mm'] for x in d),
                           pass_lane=bool(all(x['record']['median_mm'] <= 0.3 for x in d)
                                          and rec_p99 <= thr),
                           pass_per_design=per_design,
                           hand_back=bool(rec_p99 > 1.25 * floor and rec_p99 > 1.0))
        print(ln, 'n', len(d), 'floor p99 %.3f' % floor, 'record p99 %.3f' % rec_p99,
              'thr %.3f' % thr, 'max median %.3f' % summary[ln]['median_max'],
              'PASS' if summary[ln]['pass_lane'] else 'FAIL',
              'per-design %d/%d' % (per_design, len(d)), flush=True)
    json.dump(summary, open(ROOT / '.x4c/inner_summary.json', 'w'), indent=1)


if __name__ == '__main__':
    run()
