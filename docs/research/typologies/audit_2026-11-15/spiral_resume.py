"""Exact spiral real-evaluation synthetic-backend resume probe; creates labeled scratch evidence."""
import copy, dataclasses, hashlib, json, subprocess, sys, time, traceback
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]; sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from tools.geometry import rolled_rect_cli as bridge
bridge.install()
from hornlab_search.config import load_config
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.search import cma
from hornlab_search.mesh import grid_build
from test_search_support import SyntheticBackend, LIBS
cfg=load_config(ROOT/'examples/typologies/home_landscape_2026-11-15/hl__rolled_es_spiral_v7.yaml')
# Explicit synthetic backend in persisted metadata prevents confusion with a physical CUDA run.
raw=copy.deepcopy(cfg.raw); raw['solve']['backend']='synthetic'; raw['solve']['cuda_fused']=False; raw['search']['popsize']=4
cfg=dataclasses.replace(cfg,raw=raw,solve=dataclasses.replace(cfg.solve,backend='synthetic',cuda_fused=False),search=dataclasses.replace(cfg.search,popsize=4))
rd=ROOT/'scratch'/'spiral_resume_synthetic'/time.strftime('%Y%m%d-%H%M%S'); rd.mkdir(parents=True,exist_ok=False)
(rd/'SYNTHETIC_ONLY.txt').write_text('Synthetic response. Not acoustic evidence. Real CPU gmsh geometry; no GPU or real solve.\n')
surface_captures=[]
real_mesh=grid_build.build_grid_mesh
def capture_grid(geometry,mesh,path,config,**kw):
 inner,outer,_,_,_=grid_build._resolve_grid(geometry,enclosure=kw.get('mounting'))
 h=hashlib.sha256(b'spiral-audit-inner-outer-v1\0')
 for points in (inner,outer):
  arr=np.ascontiguousarray(np.round(np.asarray(points,dtype=float),6),dtype='<f8')
  h.update(str(arr.shape).encode()); h.update(arr.tobytes())
 surface_captures.append({'design_hash':Path(path).parent.name,'surface_hash':h.hexdigest()})
 return real_mesh(geometry,mesh,path,config,**kw)
grid_build.build_grid_mesh=capture_grid
store=DatasetStore(rd/'dataset'); backend=SyntheticBackend(); out={'run_dir':str(rd),'backend':'synthetic','overrides':{'budget_first':5,'budget_resumed_cumulative':9,'popsize':4,'trace_fraction':0,'backend_metadata':'synthetic'},'original_strict_policies':{'infeasible_penalty':cfg.search.infeasible_penalty,'budget_counts':cfg.search.budget_counts,'error_policy':cfg.search.error_policy},'attempted':True}
try:
 best1=cma.search(cfg,rd,'screen',backend=backend,budget=5,store=store,lib_shas=LIBS,trace_fraction=0)
 journal=rd/'search.ndjson'; before=journal.read_bytes() if journal.exists() else b''
 s1=json.loads((rd/'cma'/'strict_state.json').read_text()); b1=backend.calls
 print('FIRST',json.dumps({'backend_calls':b1,'strict':{k:s1.get(k) for k in ('draws','valid','refusals','told','stop_reason','boundary')}}),flush=True)
 best2=cma.search(cfg,rd,'screen',resume=rd,backend=backend,budget=9,store=store,lib_shas=LIBS,trace_fraction=0)
 after=journal.read_bytes(); s2=json.loads((rd/'cma'/'strict_state.json').read_text()); run=json.loads((rd/'run.json').read_text())
 assert after.startswith(before),'journal prefix changed'; rows=[json.loads(x) for x in after.splitlines() if x.strip()]
 best=json.loads((rd/'best.json').read_text()); replay=subprocess.run([sys.executable,str(Path(__file__).with_name('spiral_execution.py')),'--cold'],input=json.dumps(best['params']),capture_output=True,text=True,cwd=ROOT,check=True,timeout=60)
 cold=json.loads(replay.stdout.strip().splitlines()[-1]); assert cold['design_hash']==best['design_hash']
 captures={r['design_hash']:r['surface_hash'] for r in surface_captures}; surface_checks=[]
 for row in rows:
  if not row.get('ok'): continue
  child=subprocess.run([sys.executable,str(Path(__file__).with_name('spiral_execution.py')),'--cold'],input=json.dumps(row['params']),capture_output=True,text=True,cwd=ROOT,check=True,timeout=60)
  rec=json.loads(child.stdout.strip().splitlines()[-1]); dh=row['design_hash']
  assert rec['design_hash']==dh and captures[dh]==rec['surface_hash'],dh
  surface_checks.append({'design_hash':dh,'mesh_seam_hash':captures[dh],'cold_hash':rec['surface_hash']})
 guard_results={}
 block=best['params']['grid']
 for label in ('digest','driver'):
  tampered=copy.deepcopy(block); brief=copy.deepcopy(cfg.brief)
  if label=='digest': tampered['rows']['implementation_sha256']='0'*64
  else: brief['driver']['exit_radius_mm']+=1
  try: bridge._points(tampered,tampered['knobs'],brief)
  except Exception as exc: guard_results[label]=str(exc)
  else: raise AssertionError(label+' guard did not refuse')
 out.update({'source_guards':guard_results,'completed':True,'backend_calls_first':b1,'backend_calls_resume':backend.calls-b1,'first_state':s1,'resumed_state':s2,'journal_prefix_bytes_unchanged':True,'first_journal_lines':len(before.splitlines()),'final_journal_lines':len(rows),'new_rows':len(after.splitlines())-len(before.splitlines()),'rows_summary':[{'design_hash':r.get('design_hash'),'cached':r.get('cached'),'kind':r.get('kind'),'ok':r.get('ok')} for r in rows], 'unique_design_hashes':len({r.get('design_hash') for r in rows}),'dataset_index_rows':len(store.index),'best':{'design_hash':best['design_hash'],'cold':cold},'surface_checks':surface_checks,'run_stats':run.get('stats'),'last_invocation':run.get('last_invocation')})
 print('RESUME',json.dumps({'backend_calls_resume':backend.calls-b1,'prefix_unchanged':True,'journal_rows':len(rows),'dataset_rows':len(store.index),'surface_checks':len(surface_checks),'best':out['best'],'strict':{k:s2.get(k) for k in ('draws','valid','refusals','told','stop_reason','extensions')}}),flush=True)
except Exception as e:
 out.update({'completed':False,'error':repr(e),'traceback':traceback.format_exc(),'backend_calls':backend.calls}); print(out['traceback'],flush=True)
finally:
 Path(__file__).with_suffix('.json').write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')
if not out['completed']: sys.exit(1)
