import json, pathlib, warnings, numpy as np
warnings.filterwarnings('ignore')
from hornlab_search.solve.cache import load_response
from hornlab_search.objective import replay as R
from hornlab_search.metrics.compute import compute_metrics

root = pathlib.Path(r'C:\Users\hunte\Hrns\hornlab-search')
pairs = []
for S in sorted((root/'runs').glob('study-*')):
    sd, vd = S/'screen', S/'verify'
    if not (sd/'designs').is_dir() or not (vd/'designs').is_dir():
        continue
    common = sorted({p.name for p in (sd/'designs').iterdir() if p.is_dir()} &
                    {p.name for p in (vd/'designs').iterdir() if p.is_dir()})
    bs = R.brief_from_config(sd/'config.yaml')
    bv = R.brief_from_config(vd/'config.yaml')
    for h in common:
        try:
            sa = json.load(open(sd/'designs'/h/'status.json'))
            sv = json.load(open(vd/'designs'/h/'status.json'))
            if not (sa.get('ok') and sv.get('ok')):
                continue
            ra = load_response(sd/'designs'/h/'response.npz')
            rv = load_response(vd/'designs'/h/'response.npz')
            ma = json.load(open(sd/'designs'/h/'metrics.json'))
            mv = json.load(open(vd/'designs'/h/'metrics.json'))
            pairs.append((S.name, h, bs, bv, ra, rv, sa, sv, ma, mv))
        except Exception as e:
            print('skip', S.name, h, repr(e)[:120])

print('pairs', len(pairs))
diffs = []
for S, h, bs, bv, ra, rv, sa, sv, ma, mv in pairs:
    # stored-metrics replay (no regeneration): should be exact
    rs_a = R._replay_core(dict(sa, design_hash=h, mesh_hash=sa.get('mesh_hash'), objective_version=7),
                          None, response=ra, stored_metrics=None, stored_metric_reasons=[],
                          brief=bs, target=None, weights_override=None, objective_params_override=None,
                          objective_version_override=None, regenerate_metrics=False,
                          allow_metric_regeneration=True)
    # regenerate from response
    rg_a = R._replay_core(dict(sa, design_hash=h, mesh_hash=sa.get('mesh_hash'), objective_version=7),
                          None, response=ra, stored_metrics=None, stored_metric_reasons=[],
                          brief=bs, target=None, weights_override=None, objective_params_override=None,
                          objective_version_override=None, regenerate_metrics=True,
                          allow_metric_regeneration=True)
    # di comparison
    md = compute_metrics(ra, bs.target)
    di_stored = np.asarray(ma['di_db'], float)
    di_regen = np.asarray(md.di_db, float)
    di_max = float(np.nanmax(np.abs(di_stored - di_regen))) if di_stored.shape == di_regen.shape else float('nan')
    diffs.append((S, h, sa.get('objective'), rs_a.j, rg_a.j, di_max,
                  ma.get('scalars', {}).get('di_source'), md.di_source,
                  ra.spl_balloon_db is not None, rv.spl_balloon_db is not None,
                  len(ra.freqs_hz), len(rv.freqs_hz)))
arr = np.array([(d[2], d[3], d[4], d[5]) for d in diffs], float)
print('screen stored-J vs replay(no regen): max', np.nanmax(np.abs(arr[:,1]-arr[:,0])))
print('screen stored-J vs replay(regen)   : max', np.nanmax(np.abs(arr[:,2]-arr[:,0])))
print('di max regen-stored: max', np.nanmax(arr[:,3]))
print('di_source stored/regen:', {(d[6], d[7]): sum(1 for x in diffs if (x[6],x[7])==(d[6],d[7])) for d in diffs})
print('balloon screen/verify:', sum(1 for d in diffs if d[8]), sum(1 for d in diffs if d[9]))
for d in diffs:
    if abs(d[4]-d[2]) > 1e-6 or d[5] > 1e-6:
        print('DELTA', d[0], d[1][:10], 'storedJ %.6f' % d[2], 'regenJ %.6f' % d[4], 'di_max %.6f' % d[5], d[6], d[7])
