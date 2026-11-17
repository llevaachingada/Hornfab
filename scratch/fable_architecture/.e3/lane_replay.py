import sys,pathlib,pickle,json,collections,numpy as np
sys.path.insert(0,'scratch/fable_architecture/.tmp')
import fable_replay_harness as H
from hornlab_search.objective.scalar_v7 import resolve_v7_weights,V7_WEIGHTED_KEYS
from hornlab_search.objective.scalar_v2 import freq_weight_vector
from hornlab_search.objective.scalar_v4 import _side_weight
R=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb')); cache={}; lanes=collections.defaultdict(list); skip=collections.Counter()
for r in R:
 if not r['ok'] or not r['f'] or len(r['f'])!=18 or r['J'] is None: continue
 try:
  run=r['run']; b=cache.get(run); b=b if b is not None else H.brief(pathlib.Path('runs')/run/'config.yaml'); cache[run]=b; t=b.target;p=b.objective_params;w=resolve_v7_weights(b.weights)
  assert all(r['terms'][k]>=0 for k in V7_WEIGHTED_KEYS) and abs(sum(w[k]*r['terms'][k] for k in V7_WEIGHTED_KEYS)-r['J'])<1e-7
  if any(w[k]<0 for k in V7_WEIGHTED_KEYS) or t.coverage_v_up_deg is not None or t.coverage_v_down_deg is not None:raise ValueError('unsupported weights/asymmetric')
  f=np.asarray(r['f']); band=(f>=t.band_lo_hz)&(f<=t.band_hi_hz);fw=freq_weight_vector(f,t);parts=[]
  for bw,ct,f0,scale in [(r['bwh'],t.coverage_h_deg,t.f0_effective_hz(),1),(r['bwv'],t.coverage_v_deg,t.f0_v_hz or t.f0_effective_hz(),p.cov_v_weight)]:
   err=np.asarray(bw)-ct; inc=band if p.cov_below_f0=='one_sided' else band&(f>=f0);side=_side_weight(err,p.cov_narrow_ratio)
   if p.cov_below_f0=='one_sided':side=np.where((f<f0)&(err>0),0,side)
   assert np.isfinite(err).all() and np.all(fw[inc]>0) and inc.any()
   parts.append(np.where(inc,side*err**2/100*fw,0)/sum(fw[inc])*scale)
  contribution=(parts[0]+parts[1])*w['cov']/p.tolerances['cov']; assert sum(contribution)<=r['J']+1e-7
  order=[]
  for v in [t.f0_effective_hz(),np.sqrt(t.f0_effective_hz()*t.band_hi_hz),t.band_hi_hz,t.band_lo_hz]:
   idx=int(np.argmin(abs(np.log(f/v))));
   if idx not in order:order.append(idx)
  order += [i for i in range(18) if i not in order]
  lanes[(r['config'],r['brief'])].append((r['created'],r['J'],contribution,order))
 except Exception as e: skip[str(e)]+=1
out=[]
for key,data in lanes.items():
 data.sort(key=lambda v:v[0]); values=np.array([x[1] for x in data]); cutoff=np.percentile(values,10)
 for margin in [.5,1.,2.]:
  inc=float('inf'); saved=stops=false=0; positions=collections.defaultdict(lambda:[0,0,0])
  for pos,(_,j,contrib,order) in enumerate(data):
   dec=min(3,4*pos//len(data));positions[dec][0]+=1
   if pos==0: inc=j; continue
   bound=0
   for k,i in enumerate(order,1):
    bound+=contrib[i]
    if bound>inc+margin and k<18:
     saved+=18-k;stops+=1;positions[dec][1]+=18-k;positions[dec][2]+=1;false+=j<=cutoff
     break
   else: inc=min(inc,j)
  out.append(dict(lane=key[0],brief=key[1],n=len(data),margin=margin,saved=saved,stops=stops,false_top10=false,positions=dict(positions)))
print(json.dumps(dict(rows=out,skip=dict(skip)),indent=2,default=lambda x:int(x) if isinstance(x,np.integer) else float(x)))


