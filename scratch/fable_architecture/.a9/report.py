import json, numpy as np, collections
from scipy.stats import spearmanr
R=json.load(open('scratch/fable_architecture/.a9/records.json'))
print('rows',len(R),'parity max|v7 regenerated - stored| on cd rows:',max(abs(r['v7']-r['v7_stored']) for r in R if r['brief']=='cd'))
def topk(key,k,rows): 
    o=sorted(range(len(rows)),key=lambda i:rows[i][key]); return set(o[:k])
for coh in ('all','cd'):
    rows=R if coh=='all' else [r for r in R if r['brief']=='cd']
    print(f'\n== cohort {coh} n={len(rows)}')
    keys=['v7','v9_pt','v9_swap','v9_cor']
    print('pair                      top20 overlap  top100 overlap  spearman(all)  spearman(within a-top100)')
    for a,b in (('v7','v9_pt'),('v9_pt','v9_swap'),('v9_swap','v9_cor'),('v9_pt','v9_cor'),('v7','v9_cor')):
        A=np.array([r[a] for r in rows]); B=np.array([r[b] for r in rows]); t=sorted(topk(a,100,rows))
        print(f'{a:8s} -> {b:8s}        {len(topk(a,20,rows)&topk(b,20,rows)):2d}/20          {len(topk(a,100,rows)&topk(b,100,rows)):3d}/100        {spearmanr(A,B)[0]:.3f}          {spearmanr(A[t],B[t])[0]:.3f}')
    rp=np.array([r['rip_pt'] for r in rows]); rc=np.array([r['rip_cor'] for r in rows]); cp=np.array([r['cov_pt'] for r in rows]); cc=np.array([r['cov_cor'] for r in rows])
    print('ripple term (normalised): point-mode median %.3f  corridor-mode median %.3f  ratio of medians %.2f ; spearman %.2f'%(np.median(rp),np.median(rc),np.median(rc)/np.median(rp),spearmanr(rp,rc)[0]))
    print('coverage term: point median %.3f  corridor median %.3f ; rows with corridor coverage exactly 0: %d'%(np.median(cp),np.median(cc),(cc==0).sum()))
    for key in keys:
        best=collections.OrderedDict()
        for i in sorted(range(len(rows)),key=lambda i:rows[i][key]):
            best.setdefault(rows[i]['lane'],rows[i][key])
            if len(best)>=6: break
        print(f'  best lanes under {key:8s}:',', '.join(f"{l.replace('hl__','')[:22]} {v:.2f}" for l,v in best.items()))
