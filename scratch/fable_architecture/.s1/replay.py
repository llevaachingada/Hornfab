import pickle, pathlib, json, sys, collections, numpy as np, yaml
from hornlab_search.objective.replay import _response_from_arrays
from hornlab_search.objective.scalar_v9 import V9Params,objective_v9,resolve_v9_weights,_cov_profile_term
from hornlab_search.targets.spec import Target
from hornlab_search.metrics.compute import compute_metrics

base={'coverage_h_deg':80.,'coverage_v_deg':50.,'band_lo_hz':350.,'band_hi_hz':8000.,'f0_hz':700.,'f0_v_hz':1000.,'di_slope_target':0.,'z_min':.5,'loaded_hi_hz':5600.,'freq_weights':{'band_hz':[[2500.,5500.,2.]]}}
block={'version':9,'flat_band':'scored','cov_v_weight':.5,'cov_narrow_ratio':2.,'cov_below_f0':'mask','tolerances':{'cov_profile':3.,'rip':1.,'flat':1.5,'load':.3,'dislope':9.,'di_roughness':.5,'flat_cv':1.5}}
weights={'cov_profile':1.,'rip':1.,'flat':.5,'load':1.,'dislope':1.,'di_roughness':1.,'flat_cv':1.}
params=V9Params.from_block(block); w=resolve_v9_weights(weights,params)
def target(shift,onset):
 t=dict(base);t['f0_v_hz']=onset
 t['coverage_profile']={'mode':'corridor','h':[[700,70+shift,60+shift,80+shift],[8000,70+shift,60+shift,80+shift]],'v':[[onset,50+shift,40+shift,60+shift],[8000,50+shift,40+shift,60+shift]]}
 return Target.from_dict(t)
targets={(s,o):target(s,o) for s in (-5,0,5) for o in (700,1000,1250)}
yaml.safe_dump({'target':{**base,'coverage_profile':{'mode':'corridor','h':[[700,70,60,80],[8000,70,60,80]],'v':[[1000,50,40,60],[8000,50,40,60]]}},'objective':block,'weights':weights},open('scratch/fable_architecture/.s1/brief.yaml','w'),sort_keys=False)
def constancy(f,b,lo,hi,onset,linear=False):
 m=(f>=onset)&(f<=8000)&np.isfinite(b); a=b[m]; x=np.log10(f[m]); level=np.clip(a.mean(),lo,hi)
 if linear:
  # Unconstrained fit slope clipped to placeholder ±5 degrees/decade; then intercept
  # clipped so the fitted center at mean log frequency lies in the corridor.
  slope=np.clip(np.polyfit(x,a,1)[0],-5,5) if len(a)>1 else 0
  centre=np.clip(np.mean(a-slope*(x-x.mean())),lo,hi); pred=centre+slope*(x-x.mean())
 else: pred=level
 return float(np.mean((a-pred)**2)/25),float(a.mean()),float(a.std())
cohort=sys.argv[1] if len(sys.argv)>1 else 'cd'
rows=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb')); rows=[r for r in rows if r['ok'] and r['brief']==cohort]
out=open('scratch/fable_architecture/.s1/records_'+cohort+'.jsonl','w'); counts=collections.Counter()
for idx,r in enumerate(rows):
 try:
  path=pathlib.Path('runs')/r['run']/'designs'/r['h']/'response.npz'; z=np.load(path,allow_pickle=False)
  keys=['freqs_hz','h_angles_deg','v_angles_deg','spl_h_db','spl_v_db','balloon_dirs','spl_balloon_db','z_throat']; arrays={k:z[k] for k in keys if k in z}
  resp,reason=_response_from_arrays({},arrays)
  if reason or resp.z_throat is None or resp.spl_balloon_db is None: counts['missing_response_impedance_or_balloon']+=1;continue
  met=compute_metrics(resp,targets[(0,1000)]); f=np.asarray(met.freqs_hz); bh=np.asarray(met.bw_h_deg); bv=np.asarray(met.bw_v_deg)
  if not (np.isfinite(bh).all() and np.isfinite(bv).all()): counts['nonfinite_beamwidth']+=1;continue
  baseline,t=objective_v9(met,resp,True,targets[(0,1000)],weights,params)
  if t['penalty'] or not np.isfinite(baseline): raise ValueError('scorer penalty')
  band=(f>=350)&(f<=8000)
  cases={}
  for (s,o),tar in targets.items():
   # Shift keeps corridor widths identical, so v9 ripple and all other components
   # are unchanged; recompute the canonical coverage term for each target.
   cov=_cov_profile_term(met,tar,f,band,params)/params.tolerances['cov_profile']
   j=baseline+w['cov_profile']*(cov-t['cov_profile'])
   if idx < 3:
    check,ct=objective_v9(met,resp,True,tar,weights,params)
    if ct['penalty'] or not np.isclose(j,check,rtol=1e-10,atol=1e-10): raise ValueError('case decomposition mismatch')
   h=constancy(f,bh,60+s,80+s,700); v=constancy(f,bv,40+s,60+s,o)
   hl=constancy(f,bh,60+s,80+s,700,True); vl=constancy(f,bv,40+s,60+s,o,True)
   # t values are normalized by per-term tolerance. Apply free limits in raw dB.
   dead=j
   for k,free in [('rip',1.),('di_roughness',.5),('flat',1.)]:
    tol=params.tolerances[k]; dead+=w[k]*(max(0.,t[k]*tol-free)/tol-t[k])
   cases[f'{s},{o}']={'v9':j,'strict':j+h[0]+.5*v[0],'linear':j+hl[0]+.5*vl[0],'dead':dead+h[0]+.5*v[0], 'h':h[1:],'v':v[1:], 'rip_db':t['rip']*params.tolerances['rip'],'load_term':t['load']}
  out.write(json.dumps({'hash':r['h'],'run':r['run'],'lane':r['config'],'v7':r['J'],'cases':cases})+'\n'); counts['scored']+=1
 except Exception as e: counts[type(e).__name__+': '+str(e)[:130]]+=1
 if idx and idx%100==0: print(idx,dict(counts),flush=True);out.flush()
out.close();print('final',dict(counts),flush=True);json.dump(dict(counts),open('scratch/fable_architecture/.s1/counts_'+cohort+'.json','w'))
