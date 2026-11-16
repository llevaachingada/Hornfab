"""Save reviewed configs, queue draft, acoustic comparison and reusable handoff metadata."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import yaml
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from hornlab_search.config import _load_yaml_extends
from hornlab_search.solve.cache import load_response
from hornlab_search.metrics.di import di_slope_db_per_decade
Q=ROOT/'docs/queue/rolled_readiness_2026-11-15'
Q.mkdir(parents=True,exist_ok=True)
(Q/'configs').mkdir(exist_ok=True)
(Q/'briefs').mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
inventory=json.loads((HERE/'domains_current.json').read_text())
cells={}
for c in inventory['configs']:
    source=ROOT/c['path'];raw=_load_yaml_extends(source)
    if raw.get('brief_file'):
        brief=(source.parent/raw['brief_file']).resolve()
        dest=Q/'briefs'/(sha(brief)[:12]+'.yaml')
        if not dest.exists():shutil.copy2(brief,dest)
        raw['brief_file']=str(dest.resolve())
    raw['search']['budget']=30
    raw['search']['max_attempts']=45
    config=Q/'configs'/(c['name']+'.yaml')
    config.write_text(yaml.safe_dump(raw,sort_keys=False),encoding='utf8')
    rt=(raw.get('generator',{}).get('rows') or {}).get('type')
    bridge={'rolled_rect':'rolled_rect_cli','rolled_rect_pucker':'rolled_rect_cli',
            'crowe_panel':'crowe_panel_cli','section_pucker':'section_pucker_cli','rosse_rect':'rosse_rect_cli'}.get(rt)
    files=[config,source,Q/'reviewed_job.py']
    if raw.get('brief_file'):files.append(Path(raw['brief_file']))
    if bridge:
        files += [ROOT/'tools/geometry'/f'{bridge}.py',ROOT/'tools/geometry/rolled_rect.py',ROOT/'tools/geometry/rolled_rect_cli.py']
        if bridge=='crowe_panel_cli' or bridge=='section_pucker_cli':files += [ROOT/'tools/geometry/crowe_panel.py',ROOT/'examples/prototypes/rolled_rect_2026-11-15/crowe_section_reference.yaml']
        if bridge=='rosse_rect_cli':files.append(ROOT/'tools/geometry/rosse_rect.py')
        if bridge=='section_pucker_cli':files += [ROOT/'tools/geometry/section_pucker.py',ROOT/'tools/geometry/crowe_panel_cli.py']
    else:files += [ROOT/'hornlab_search/design/generators/grid.py',ROOT/'hornlab_search/design/generators/rolled_family.py']
    cells[c['name']]={'config':str(config.relative_to(ROOT)).replace('\\','/'),'original':c['path'],
       'bridge':bridge,'status':'held','gates':['source_interface','objective','full_body','domain_capability','convergence','explicit_search_release'],
       'pins':{str(f.relative_to(ROOT)).replace('\\','/'):sha(f) for f in files}}
(Q/'admission.json').write_text(json.dumps({'full_search_released':False,'bayesian_jobs_allowed':False,'cells':cells},indent=2)+'\n')
night={'night':'rolled_review_spiral_30x2_2026-11-15','lane':'gpu','jobs':[
    {'id':f'spiral_s{seed}','kind':'command','timeout_s':3600,
     'argv':['.venv/Scripts/python.exe','docs/queue/rolled_readiness_2026-11-15/reviewed_job.py','--cell','hl__rolled_es_spiral_v7','--seed',str(seed)]}
    for seed in (1234,5678)]}
(Q/'pilot_HELD.yaml').write_text(yaml.safe_dump(night,sort_keys=False))
checks=[]
for name in cells:
    r=subprocess.run([sys.executable,str(Q/'reviewed_job.py'),'--cell',name,'--check'],cwd=ROOT,capture_output=True,text=True)
    checks.append({'cell':name,'exit_code':r.returncode,'output':(r.stdout+r.stderr).strip()})
(Q/'config_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print('CONFIG CHECKS',sum(r['exit_code']==0 for r in checks),'/',len(checks),flush=True)
rows=[]
base=ROOT/'scratch/2026-11-15_readiness/spiral_acoustics'
for label in ('epw6','epw8'):
    rd=next((base/label/'runs').iterdir())
    r=json.loads((rd/'search.ndjson').read_text().strip().splitlines()[0])
    response=load_response(rd/'designs'/r['design_hash']/'response.npz')
    watch=json.loads((base/f'{label}_memwatch.json').read_text())
    rows.append({'label':label,'run':str(rd.relative_to(ROOT)),'design_hash':r['design_hash'],
      'mesh_hash':r['mesh_hash'],'solve_hash':r['solve_hash'],'objective':r['objective'],'terms':r['terms'],
      'cached':r['cached'],'n_dof':r['n_dof'],'res_mm':r['res_mm'],
      'freqs_hz':response.freqs_hz.tolist(),'balloon_grid':response.meta.get('balloon_grid'),
      'bw_h_deg':r['metrics']['bw_h_deg'],'bw_v_deg':r['metrics']['bw_v_deg'],'di_db':r['metrics']['di_db'],
      'z_real':r['metrics']['z_throat_real'],'source':{k:response.meta.get(k) for k in ('spl_reference','distance_m','source_motion')},
      'memwatch':watch,'response_sha256':sha(rd/'designs'/r['design_hash']/'response.npz')})
    shutil.copy2(base/f'{label}_memwatch.json',HERE/f'spiral_acoustic_{label}_memwatch.json')
result={'acoustic_candidate_evaluations':2,'no_search_campaign':True,'rows':rows,
 'delta_J_epw8_minus_epw6':rows[1]['objective']-rows[0]['objective'],
 'max_abs_delta':{key:float(np.max(abs(np.array(rows[1][key])-np.array(rows[0][key])))) for key in ('bw_h_deg','bw_v_deg','di_db','z_real')},
 'limitations':['Two spatial meshes only; not established convergence.','Same geometry sampling and frequency/angular grids; no frequency/angular refinement.','Source and objective assumptions unresolved; no readiness claim.']}
(HERE/'SPIRAL_ACOUSTICS.json').write_text(json.dumps(result,indent=2)+'\n')
print('ACOUSTIC RESULT',json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
