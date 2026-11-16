"""Offline spiral strict-CMA and full-surface cold-replay probe; no mesher or solver."""
import copy, dataclasses, hashlib, json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'tests'))
from tools.geometry import rolled_rect_cli as bridge
bridge.install()  # required in every fresh process
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import build as mesh_build, grid_build
from hornlab_search.search import cma as cma_mod
from hornlab_search.types import Design, Evaluation, SolveOutcome, MeshResult
from test_search_support import SyntheticBackend, LIBS
CFG=ROOT/'examples/typologies/home_landscape_2026-11-15/hl__rolled_es_spiral_v7.yaml'
OUT=Path(__file__).with_suffix('.json')
def digest(inner,outer):
 h=hashlib.sha256(b'spiral-audit-inner-outer-v1\0')
 for points in (inner,outer):
  arr=np.ascontiguousarray(np.round(np.asarray(points,dtype=float),6),dtype='<f8')
  h.update(str(arr.shape).encode()); h.update(arr.tobytes())
 return h.hexdigest()
def seam(design,cfg,tmp):
 saved=grid_build.build_grid_mesh
 def capture(geometry,mesh,path,config,**kw):
  inner,outer,_,_,_=grid_build._resolve_grid(geometry,enclosure=kw.get('mounting'))
  return inner,outer
 grid_build.build_grid_mesh=capture
 try: return mesh_build._build_grid_mesh(design,None,cfg,tmp,mode='screen')
 finally: grid_build.build_grid_mesh=saved
if '--cold' in sys.argv:
 cfg=load_config(CFG); recipe=json.load(sys.stdin); design=Design('FREEFORM',recipe)
 with tempfile.TemporaryDirectory() as td: i,o=seam(design,cfg,td)
 print(json.dumps({'design_hash':design.hash(),'surface_hash':digest(i,o),'inner_shape':list(i.shape),'outer_shape':list(o.shape)})); sys.exit(0)
cfg=load_config(CFG); space=DesignSpace.from_config(cfg); assert len(space.keys())==10
# Only shorten runtime and stabilize the test: exact seed, generator, bounds and strict policies retained.
cfg=dataclasses.replace(cfg,search=dataclasses.replace(cfg.search,popsize=4,tolfun=1e-12))
seen=[]; injected={'refused':False,'transient':False}; pending=set(); tells=[]
real_es=cma_mod.cma_lib.CMAEvolutionStrategy
class Spy(real_es):
 def tell(self,X,F,*a,**kw):
  tells.append([float(x) for x in F]); return super().tell(X,F,*a,**kw)
cma_mod.cma_lib.CMAEvolutionStrategy=Spy
with tempfile.TemporaryDirectory(prefix='spiral-cma-audit-') as td:
 def fake(design,space,config,mode,run_dir,store,backend,*,ctx=None,**kwargs):
  err=''; dh=design.hash(); mesh=None; sh=None
  if '_generator_error' in design.params: err='invalid_geometry: generated refusal'
  elif len(seen)>0 and not injected['refused']:
   injected['refused']=True; err='invalid_geometry: injected deterministic refusal'
  else:
   i,o=seam(design,config,td); sh=digest(i,o); mesh=MeshResult('mock.msh',1,1,'1','yz+xz',{},(0,0,0,1,1,1),0.0)
   if len(seen)>1 and not injected['transient']:
    injected['transient']=True; pending.add(dh); err='solve_failed: injected temporary failure'
  score=10.0 - len(seen)*0.01 if not err else 10000.0
  ev=Evaluation(dh,design,mesh,'mock-solve',score,{'total':score},None,mesh,SolveOutcome(not bool(err),None,0.0,None,''),cached=False,error=err)
  seen.append({'design_hash':dh,'surface_hash':sh,'error':err,'score':score})
  return ev
 cma_mod.evaluate=fake
 winner=cma_mod.search(cfg,Path(td)/'run','screen',backend=SyntheticBackend(),budget=6,lib_shas=LIBS)
 summary=json.loads((Path(td)/'run'/'run.json').read_text()); state=json.loads((Path(td)/'run'/'cma'/'strict_state.json').read_text())
 assert winner and not winner.error and tells and all(v<10000 for F in tells for v in F)
 assert injected['refused'] and injected['transient']
 assert state['replacements']>=1 and state['retries']==1 and state['valid']==6
 failed=next(i for i,x in enumerate(seen) if x['error'].startswith('solve_failed'))
 assert seen[failed]['design_hash']==seen[failed+1]['design_hash']
 i,o=seam(winner.design,cfg,td); winner_hash=digest(i,o)
 child=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--cold'],input=json.dumps(winner.design.params),capture_output=True,text=True,cwd=ROOT,timeout=60,check=True)
 cold=json.loads(child.stdout.strip().splitlines()[-1]); assert cold['surface_hash']==winner_hash and cold['design_hash']==winner.design_hash
 block=winner.design.params['grid']; bad=copy.deepcopy(block); bad['rows']['implementation_sha256']='0'*64
 guards={}
 for label,block2,brief in [('digest',bad,cfg.brief),('driver',block,{**cfg.brief,'driver':{**cfg.brief['driver'],'exit_radius_mm':cfg.brief['driver']['exit_radius_mm']+1}})]:
  try: bridge._points(block2,block2['knobs'],brief)
  except Exception as exc: guards[label]=str(exc)
  else: raise AssertionError(label+' mismatch not refused')
 result={'config':str(CFG.relative_to(ROOT)),'config_sha256':hashlib.sha256(CFG.read_bytes()).hexdigest(),'wrapper_sha256':hashlib.sha256(Path(bridge.__file__).read_bytes()).hexdigest(),'implementation_sha256':bridge.implementation_digest(),'keys':space.keys(),'original_search':{'budget':96,'popsize':None,'sigma0':0.2,'infeasible_penalty':cfg.search.infeasible_penalty,'budget_counts':cfg.search.budget_counts,'error_policy':cfg.search.error_policy},'probe_overrides':{'budget':6,'popsize':4,'tolfun':1e-12},'winner':{'design_hash':winner.design_hash,'surface_hash':winner_hash,'recipe':winner.design.params,'cold':cold},'strict':summary.get('strict'),'budget_counts':summary.get('budget_counts'),'tell_batches':tells,'evaluations':seen,'guards':guards,'limitations':'Injected outcomes and synthetic scores; no actual backend, mesh, acoustics or production optimization.'}
 OUT.write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps({'dimensions':len(space.keys()),'winner_surface_hash':winner_hash,'strict':summary.get('strict'),'tells':len(tells),'guards':guards},indent=2))
