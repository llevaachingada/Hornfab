"""A4: where does the grid dependence of J come from, and is 'J on a uniform dense log grid' a
well-defined, grid-independent quantity? Read-only, CPU. 58 study screen/verify pairs (same mesh).
Uses the parity-exact harness; v7 scorer from each study's own config."""
import sys, json, pathlib, warnings, collections
import numpy as np
warnings.filterwarnings('ignore')
sys.path.insert(0,'scratch/fable_architecture/.tmp')
import fable_replay_harness as H
from scipy.stats import spearmanr
KEYS=['cov','rip','di','dislope','flat','load','distd','diag','flat_cv']
def score(resp,b):
    m=H.metrics_parity(resp,b.target); j,t=H.score_v7(m,resp,b.target,b.weights,b.objective_params)
    return float(j),{k:float(b.weights.get(k,0))*float(t.get(k,0.0)) for k in KEYS}
def dense(resp,n,method='pchip'): return H.interp_response(resp,np.geomspace(350.0,8000.0,n),method=method)
rec=[]
for S in sorted(pathlib.Path('runs').glob('study-*')):
    if not (S/'screen/designs').is_dir() or not (S/'verify/designs').is_dir(): continue
    bs=H.brief(S/'screen/config.yaml'); bv=H.brief(S/'verify/config.yaml')
    for h in sorted({p.name for p in (S/'screen/designs').iterdir()}&{p.name for p in (S/'verify/designs').iterdir()}):
        try:
            a=json.load(open(S/'screen/designs'/h/'status.json')); b=json.load(open(S/'verify/designs'/h/'status.json'))
            if not(a.get('ok') and b.get('ok')): continue
            rs=H.resp_from_run(S/'screen',h); rv=H.resp_from_run(S/'verify',h)
            d={'h':h,'s_native':score(rs,bs),'v_native':score(rv,bv)}
            for n in (58,116,232): d[f'v_{n}']=score(dense(rv,n),bv); d[f's_{n}']=score(dense(rs,n),bv)
            rec.append(d)
        except Exception as e: print('skip',S.name,h[:8],repr(e)[:120])
print('pairs',len(rec))
J=lambda k: np.array([r[k][0] for r in rec]); T=lambda k,t: np.array([r[k][1][t] for r in rec])
top=J('s_native')<3.6
def line(name,a,b,m=None):
    m=np.ones(len(rec),bool) if m is None else m; d=(J(b)-J(a))[m]
    print(f'{name:52s} n={m.sum():2d} mean {d.mean():+.3f} sd {d.std(ddof=1):.3f}  spearman {spearmanr(J(a)[m],J(b)[m])[0]:.3f}')
print('\n== 1. parity: native-grid replay vs stored'); 
print('== 2. J differences (b - a)')
for m,lab in ((None,'all'),(top,'top (screen J<3.6)')):
    print('--',lab)
    line('stored-grid screen(18) -> stored-grid verify(29)','s_native','v_native',m)
    line('verify native 29 -> verify dense 58 (definition change)','v_native','v_58',m)
    line('verify dense 58 -> dense 116 (is the definition converged?)','v_58','v_116',m)
    line('verify dense 116 -> dense 232','v_116','v_232',m)
    line('DENSE 232: from 18 solved pts -> from 29 solved pts','s_232','v_232',m)
    line('DENSE 58 : from 18 solved pts -> from 29 solved pts','s_58','v_58',m)
print('\n== 3. which terms carry each difference? weighted term contributions, mean / sd of difference (all pairs | top pairs)')
for a,b,lab in (('v_native','v_58','native 29 -> dense 58'),('v_58','v_232','dense 58 -> dense 232'),('s_232','v_232','dense: 18-pt source -> 29-pt source'),('s_native','v_native','stored screen -> stored verify')):
    print('--',lab)
    for t in KEYS:
        d=T(b,t)-T(a,t)
        print(f'   {t:8s} all {d.mean():+.3f} / {d.std(ddof=1):.3f}   top {d[top].mean():+.3f} / {d[top].std(ddof=1):.3f}')
json.dump(rec,open('scratch/fable_architecture/.a4/records.json','w'))
