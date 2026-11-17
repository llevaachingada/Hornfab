"""A9: separate the corridor's effect from v9's other term changes. Read-only, CPU.
Every valid landscape row is scored four ways from its stored response with parity-exact metrics:
  v7      : standard landscape v7 brief
  v9_pt   : v9, coverage_profile mode 'target' (point 80 / 50, i.e. v7-style coverage inside v9's term set)
  v9_swap : v9_pt total with ONLY the coverage term replaced by the corridor coverage term
  v9_cor  : v9, coverage_profile mode 'corridor' (also changes v9's ripple window)
Corridor: H 60-90 from 700 Hz, V 40-60 from 1000 Hz (R3 placeholder)."""
import sys, json, pickle, pathlib, collections, warnings
import numpy as np
warnings.filterwarnings('ignore')
sys.path.insert(0, 'scratch/fable_architecture/.tmp')
import fable_replay_harness as H
from hornlab_search.objective.scalar_v9 import V9Params, objective_v9, resolve_v9_weights, _cov_profile_term
from hornlab_search.objective.scalar_v7 import V7Params, objective_v7, resolve_v7_weights
from hornlab_search.targets.spec import Target
from hornlab_search.solve.cache import load_response
base={'coverage_h_deg':80.,'coverage_v_deg':50.,'band_lo_hz':350.,'band_hi_hz':8000.,'f0_hz':700.,'f0_v_hz':1000.,'di_slope_target':0.,'z_min':.5,'loaded_hi_hz':5600.,'freq_weights':{'band_hz':[[2500.,5500.,2.]]}}
block={'version':9,'flat_band':'scored','cov_v_weight':.5,'cov_narrow_ratio':2.,'cov_below_f0':'mask','tolerances':{'cov_profile':3.,'rip':1.,'flat':1.5,'load':.3,'dislope':9.,'di_roughness':.5,'flat_cv':1.5}}
weights={'cov_profile':1.,'rip':1.,'flat':.5,'load':1.,'dislope':1.,'di_roughness':1.,'flat_cv':1.}
p9=V9Params.from_block(block); w9=resolve_v9_weights(weights,p9)
T_pt=Target.from_dict({**base,'coverage_profile':{'mode':'target','h':[[700,80]],'v':[[1000,50]]}})
T_co=Target.from_dict({**base,'coverage_profile':{'mode':'corridor','h':[[700,75,60,90],[8000,75,60,90]],'v':[[1000,50,40,60],[8000,50,40,60]]}})
b7=H.landscape_brief(); 
rows=[r for r in pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb')) if r['ok']]
out=[]; cnt=collections.Counter()
for i,r in enumerate(rows):
    try:
        resp=load_response(pathlib.Path('runs')/r['run']/'designs'/r['h']/'response.npz')
        m7=H.metrics_parity(resp,b7.target); res7=H.R._dispatch if False else None
        j7,t7=objective_v7(m7,resp,True,b7.target,b7.weights,b7.objective_params) if hasattr(b7,'objective_params') else (r['J'],{})
        m=H.metrics_parity(resp,T_pt); f=np.asarray(m.freqs_hz); band=(f>=350)&(f<=8000)
        jp,tp=objective_v9(m,resp,True,T_pt,weights,p9)
        jc,tc=objective_v9(m,resp,True,T_co,weights,p9)
        cov_c=_cov_profile_term(m,T_co,f,band,p9)/p9.tolerances['cov_profile']
        js=jp+w9['cov_profile']*(cov_c-tp['cov_profile'])
        if tp['penalty'] or tc['penalty']: cnt['penalty']+=1; continue
        out.append(dict(h=r['h'],run=r['run'],lane=r['config'],brief=r['brief'],v7_stored=r['J'],v7=float(j7),v9_pt=float(jp),v9_swap=float(js),v9_cor=float(jc),
                        cov_pt=float(tp['cov_profile']),cov_cor=float(cov_c),rip_pt=float(tp['rip']),rip_cor=float(tc['rip'])))
        cnt['scored']+=1
    except Exception as e:
        cnt[type(e).__name__+': '+str(e)[:100]]+=1
    if i%400==0: print(i,dict(cnt),flush=True)
json.dump(out,open('scratch/fable_architecture/.a9/records.json','w')); print('final',dict(cnt))
