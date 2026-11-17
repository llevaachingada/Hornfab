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
    for h in common:
        sa = json.load(open(sd/'designs'/h/'status.json'))
        sv = json.load(open(vd/'designs'/h/'status.json'))
        if not (sa.get('ok') and sv.get('ok')):
            continue
        pairs.append((S, sd, vd, h, sa, sv))

print('pairs', len(pairs))
rows = []
for S, sd, vd, h, sa, sv in pairs:
    try:
        stored = R.replay_run_dir(sd, h, regenerate_metrics=False)
        regen = R.replay_run_dir(sd, h, regenerate_metrics=True)
        ra = load_response(sd/'designs'/h/'response.npz')
        ma = json.load(open(sd/'designs'/h/'metrics.json'))
        brief = R.brief_from_config(sd/'config.yaml')
        md = compute_metrics(ra, brief.target)
    except Exception as e:
        print('ERR', S.name, h, repr(e)[:160]); continue
    di_stored = np.asarray(ma['di_db'], float)
    di_regen = np.asarray(md.di_db, float)
    di_max = float(np.nanmax(np.abs(di_stored - di_regen))) if di_stored.shape == di_regen.shape else float('nan')
    rows.append(dict(S=S.name, h=h, storedJ=sa.get('objective'), noRegenJ=stored.j, regenJ=regen.j,
                     di_max=di_max, di_stored=ma.get('scalars', {}).get('di_source'), di_regen=md.di_source,
                     bal=ra.spl_balloon_db is not None, nf=len(ra.freqs_hz)))
print('stored-J vs no-regen replay max', max(abs(r['noRegenJ']-r['storedJ']) for r in rows))
print('stored-J vs regen replay max', max(abs(r['regenJ']-r['storedJ']) for r in rows))
print('di max regen-stored max', max(r['di_max'] for r in rows))
print('di_source combos', {(r['di_stored'], r['di_regen']): sum(1 for x in rows if (x['di_stored'],x['di_regen'])==(r['di_stored'],r['di_regen'])) for r in rows})
print('balloon present', sum(1 for r in rows if r['bal']), '/', len(rows))
for r in rows:
    if abs(r['regenJ']-r['storedJ']) > 1e-6 or r['di_max'] > 1e-6:
        print('DELTA', r['S'], r['h'][:10], 'stored %.9f noRegen %.9f regen %.9f di_max %.3g' % (r['storedJ'], r['noRegenJ'], r['regenJ'], r['di_max']), r['di_stored'], r['di_regen'], 'bal', r['bal'])
