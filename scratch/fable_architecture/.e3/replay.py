import sys,pathlib,json,numpy as np
sys.path.insert(0,'scratch/fable_architecture/.tmp')
import fable_replay_harness as H
from hornlab_search.objective.scalar_v7 import resolve_v7_weights,V7_WEIGHTED_KEYS
from hornlab_search.objective.scalar_v2 import freq_weight_vector
from hornlab_search.objective.scalar_v4 import _side_weight
from hornlab_search.objective.terms import PENALTY_FAILED
root=pathlib.Path('runs'); out=[]; skipped=[]
for s in sorted(root.glob('study-*')):
 d=s/'screen'/'designs'; cfg=s/'screen'/'config.yaml'
 if not d.is_dir() or not cfg.is_file():continue
 b=H.brief(cfg); t=b.target; p=b.objective_params; w=resolve_v7_weights(b.weights)
 if any(w[k]<0 for k in V7_WEIGHTED_KEYS) or t.freq_weights is not None or getattr(t,'coverage_v_up_deg',None) is not None or getattr(t,'coverage_v_down_deg',None) is not None:
  skipped.append((s.name,'unsupported weights or asymmetric V'));continue
 candidates=[]
 for q in sorted(d.iterdir()):
  try:
   st=H.json_load(q/'status.json')
   if not st.get('ok'):continue
   r=H.load_response(q/'response.npz'); f=np.asarray(r.freqs_hz); m=H.metrics_parity(r,t); j,terms=H.score_v7(m,r,t,b.weights,p)
   if len(f)!=18 or abs(j-float(st['objective']))>1e-7 or j>=PENALTY_FAILED or any(terms[k]<0 for k in V7_WEIGHTED_KEYS): raise ValueError('parity or nonnegative assumptions')
   # Every finite known coverage contribution divided by maximum possible count is a lower bound.
   band=(f>=t.band_lo_hz)&(f<=t.band_hi_hz); parts=[]
   for bw,ct,f0,scale in [(m.bw_h_deg,t.coverage_h_deg,t.f0_effective_hz(),1),(m.bw_v_deg,t.coverage_v_deg,t.f0_v_hz or t.f0_effective_hz(),p.cov_v_weight)]:
    err=np.asarray(bw)-ct; inc=band if p.cov_below_f0=='one_sided' else band&(f>=f0); side=_side_weight(err,p.cov_narrow_ratio)
    if p.cov_below_f0=='one_sided':side=np.where((f<f0)&(err>0),0,side)
    val=np.where(inc & np.isfinite(err),side*err**2/100,0); parts.append(val/max(1,inc.sum())*scale)
   contrib=(parts[0]+parts[1])*w['cov']/p.tolerances['cov']; cap=w['cov']*terms['cov']; assert np.sum(contrib)<=cap+1e-8 and cap<=j+1e-8
   candidates.append((q.name,j,contrib))
  except Exception as e: skipped.append((str(q),str(e)))
 if not candidates: continue
 # Fixed prespecified high-to-low frequency order, no lookahead; first candidate fully evaluated.
 incumbent=candidates[0][1]; saved=0; stopped=0; false=0; comparisons=0; bound_viol=0
 for name,j,contrib in candidates[1:]:
  comparisons+=1; lower=0
  for k,idx in enumerate(reversed(range(18)),1):
   lower+=contrib[idx]
   if lower>j+1e-8:bound_viol+=1
   if lower>incumbent-0.17 and k<18:
    stopped+=1;saved+=18-k
    if j<incumbent-0.17:false+=1
    break
  else: incumbent=min(incumbent,j)
 out.append(dict(study=s.name,n=len(candidates),comparisons=comparisons,stopped=stopped,saved=saved,false=false,bound_viol=bound_viol,full=18*comparisons))
print(json.dumps({'rows':out,'skipped':skipped},indent=2))
