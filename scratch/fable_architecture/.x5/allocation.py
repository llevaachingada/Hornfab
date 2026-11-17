import collections,json,math,pathlib,pickle
import numpy as np
from scipy.stats import spearmanr
root=pathlib.Path('scratch/fable_architecture'); rows=pickle.load(open(root/'.fable/rows.pkl','rb'))
cd=[r for r in rows if r['brief']=='cd']; lineage=json.load(open(root/'.x5/lineage.json'))
parents={m['config']:None for l in lineage for m in l['matches'] if False}
for l in lineage:
    for m in l['matches']:
        if l['brief']=='cd' and not m['same_config'] and m['within_noise']:
            parents[l['config']]=m['config']
def arm(c):
    seen=set()
    while c in parents and c not in seen: seen.add(c); c=parents[c]
    return c
groups=collections.defaultdict(list)
for r in cd: groups[arm(r['config'])].append(r)
for a in groups: groups[a].sort(key=lambda r:(r['created'],r['run'],r['n'] or 0))
names=sorted(groups); best=min(r['J'] for r in cd if r['ok']); threshold=best+.17
final={a:min((r['J'] for r in rs if r['ok']),default=1e9) for a,rs in groups.items()}; top=sorted(names,key=lambda a:final[a])[:3]
# The exact globally complete owner-protected set is not available; these are directly named in
# the day-queue owner direction. They provide a lower bound, never a permission to drop others.
protected={a for a in names if any(q in a for q in ('ath_tritonia','ath_twinray','biradial','ext_throat_hvlaw','osse_rrect_fold_warm'))}
clock=sorted(r['created'] for r in cd); release={run:min(r['created'] for r in cd if r['run']==run) for run in {r['run'] for r in cd}}
def sequence(seed):
    rng=np.random.default_rng(seed); result={}
    for a,rs in groups.items():
        byrun=collections.defaultdict(list)
        for r in rs: byrun[r['run']].append(r)
        out=[]
        for run in sorted(byrun,key=lambda k:release[k]):
            block=byrun[run]; out.extend(block if seed is None else [block[i] for i in rng.permutation(len(block))])
        result[a]=out
    return result
def replay(policy,seed):
    seq=sequence(seed); pos={a:0 for a in names}; cur={a:float('inf') for a in names}; dropped={}; used=0; reached=None; time_idx=0; step=0; epoch=0; epoch_done=set(); roundquota=16 if policy=='halving' else 32
    while time_idx<len(clock):
        now=clock[time_idx]
        eligible=[a for a in names if a not in dropped and pos[a]<len(seq[a]) and release[seq[a][pos[a]]['run']]<=now]
        if not eligible: time_idx+=1; continue
        if policy in ('halving','halving_floor'):
            todo=[a for a in eligible if pos[a]<roundquota and a not in epoch_done]
            if not todo:
                # Eliminate only among arms currently available and with enough evidence.
                contenders=[a for a in eligible if pos[a]>=roundquota]
                if len(contenders)>1:
                    keep=set(sorted(contenders,key=lambda a:(cur[a],a))[:max(1,(len(contenders)+1)//2)])
                    for a in contenders:
                        if a not in keep: dropped[a]={'at':used,'seen_best':cur[a],'eventual_best':final[a],'n_pulled':pos[a]}
                    roundquota*=2; epoch+=1; epoch_done=set(); continue
                # A lone available arm cannot be halved against a future arm.
                todo=eligible
            a=min(todo,key=lambda x:(pos[x],names.index(x)))
        elif policy=='round_robin': a=min(eligible,key=lambda x:(pos[x],names.index(x)))
        elif policy=='bandit':
            untried=[a for a in eligible if pos[a]<8]
            if untried: a=min(untried,key=lambda x:(pos[x],names.index(x)))
            else: a=max(eligible,key=lambda x:(-(math.log(cur[x]) if math.isfinite(cur[x]) else 5)+.35*math.sqrt(math.log(used+2)/(pos[x]/8)),-names.index(x)))
        else: raise ValueError(policy)
        r=seq[a][pos[a]]; pos[a]+=1; used+=1; time_idx+=1; step+=1
        if r['ok']: cur[a]=min(cur[a],r['J'])
        if reached is None and min(cur.values())<=threshold: reached=used
    return {'reach':reached,'used':used,'dropped':dropped,'top_dropped':[a for a in top if a in dropped], 'protected_dropped':sorted(set(dropped)&protected),'remaining':{a:len(seq[a])-pos[a] for a in names if len(seq[a])>pos[a]}}
def actual():
    cur=float('inf'); reach=None
    for i,r in enumerate(sorted(cd,key=lambda r:(r['created'],r['run'],r['n'] or 0)),1):
        if r['ok']: cur=min(cur,r['J'])
        if reach is None and cur<=threshold: reach=i
    return {'reach':reach,'used':len(cd)}
results={'threshold':threshold,'best':best,'parents':parents,'top3':top,'protected_lower_bound':sorted(protected),'arms':{a:{'attempts':len(groups[a]),'best':final[a]} for a in names},'actual':actual(),'runs':{}}
for policy in ('round_robin','halving','halving_floor','bandit'):
    results['runs'][policy]={'original':replay(policy,None),'shuffle':[replay(policy,i) for i in range(20)]}
    print(policy,'original',results['runs'][policy]['original']['reach'],'median shuffle',np.median([x['reach'] if x['reach'] is not None else np.nan for x in results['runs'][policy]['shuffle']]),flush=True)
results['predictability']={}
for n in (8,16,32):
    items=[]
    for a in names:
        if len(groups[a])<n: continue
        first=min((r['J'] for r in groups[a][:n] if r['ok']),default=np.nan)
        if np.isfinite(first) and np.isfinite(final[a]): items.append((first,final[a]))
    results['predictability'][str(n)]={'n_arms':len(items),'spearman':float(spearmanr(*zip(*items)).statistic)}
(root/'.x5/allocation.json').write_text(json.dumps(results,indent=2,allow_nan=False))
print('actual',results['actual'],'best',best,'target',threshold,'top',top,'predictability',results['predictability'])
