import ast,pathlib,copy,pickle,json,numpy as np
from hornlab_search.config import load_config
from hornlab_search.types import Design
from hornlab_search.bo.data import materialize_geometry
s=pathlib.Path('scratch/fable_architecture/.x1/probe.py').read_text();fn=next(x for x in ast.parse(s).body if isinstance(x,ast.FunctionDef) and x.name=='sample');exec(compile(ast.Module(body=[fn],type_ignores=[]),'x1sample','exec'))
R=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb'));r=min((r for r in R if r['ok'] and r['config']=='hl__osse_rrect_fold_warm_v7'),key=lambda r:r['J']);p=pathlib.Path('runs')/r['run'];cfg=load_config(p/'config.yaml');recipe=json.load(open(p/'designs'/r['h']/'design.json'));base=recipe['params']
def surf(d):return sample(materialize_geometry(Design(recipe['family'],d),cfg,resolution_mm=10)['inner_points'],31,65)
cases=[('n_at_s0',{'s':0,'s1':0,'s2':0,'az_s_cos2_amp':0},{'n':3},{'n':8}),('q_at_s0',{'s':0,'s1':0,'s2':0,'az_s_cos2_amp':0},{'q':.7},{'q':1.2}),('s1_when_s2zero',{'s2':0},{'s1':0},{'s1':1}),('s2_when_s1zero',{'s1':0},{'s2':0},{'s2':.5}),('morph_width_target0',{'morph_target':0},{'morph_width_mm':450},{'morph_width_mm':550}),('morph_rate_target0',{'morph_target':0},{'morph_rate':1},{'morph_rate':4}),('morph_exponent_target1',{'morph_target':1},{'morph_exponent':2},{'morph_exponent':8}),('morph_exponent_target3',{'morph_target':3},{'morph_exponent':2},{'morph_exponent':8})]
cases += [('n_at_spositive',{'s':.6,'s1':0,'s2':0,'az_s_cos2_amp':0},{'n':3},{'n':8}),('q_at_spositive',{'s':.6,'s1':0,'s2':0,'az_s_cos2_amp':0},{'q':.7},{'q':1.2}),('s1_when_s2positive',{'s2':.5},{'s1':.1},{'s1':1}),('s2_when_s1positive',{'s1':1},{'s2':.1},{'s2':.5})]
for name,shared,a,b in cases:
 try:
  p1={**base,**shared,**a};p2={**base,**shared,**b};d=surf(p1)-surf(p2);norm=np.linalg.norm(d,axis=2);print(name,'rms',float(np.sqrt(np.mean(norm**2))),'max',float(norm.max()))
 except Exception as e:print(name,'ERROR',type(e).__name__,str(e))

