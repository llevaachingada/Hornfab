import collections,json,pickle,re
import numpy as np
from pathlib import Path
root=Path('scratch/fable_architecture'); data,_=pickle.load(open(root/'.e1/descriptors.pkl','rb')); p=json.load(open(root/'.e1/results.json'))
def sibling(g):
    g=re.sub(r'_v\d+$','',g).replace('_smooth','')
    if g.startswith('sp__'): return 'sp__control_moderate_strong'
    if g.startswith('rr__pucker') or g=='rr__reference': return 'rr__reference_pucker'
    if g.startswith('klangfilm_hv__a'): return 'klangfilm_hv__axis_variants'
    return g
groups=collections.defaultdict(lambda:collections.defaultdict(set))
for r,_,_ in data:
    e='OSSE' if not r['gen'] else ('GRID' if r['gen']=='grid' else 'GEN-FF')
    groups[sibling(r['config'])][e].add(r['config'])
print('cross-engine sibling groups:',{k:{e:sorted(v) for e,v in x.items()} for k,x in groups.items() if len(x)>1})
ks=('score','response','actual','random','transfer'); a=[]
for g,v in p['lanes'].items():
    if 'error' in v: print('ERROR',g,v); continue
    vals=[float(np.median(np.maximum(8,v[k]))) for k in ks]; a.append(vals)
    print(g,v['n'],*vals,v['proxy_best_full_j_decile'])
print('median',np.median(a,axis=0)); print('part C',p['cross_engine'])
