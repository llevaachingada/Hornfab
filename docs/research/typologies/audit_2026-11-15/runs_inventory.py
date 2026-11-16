import json,csv,pathlib,hashlib,collections,math
root=pathlib.Path('.'); out=root/'docs/research/typologies/audit_2026-11-15'; records=[]
for p in sorted((root/'runs').glob('20261115*/run.json')):
 d=json.loads(p.read_text()); cmd=d.get('command','');
 if not any(x in cmd for x in ('home_landscape_2026-11-15','rolled_rect_2026-11-15','section_pucker_2026-11-15')): continue
 f=p.parent/'search.ndjson'
 if not f.exists():continue
 rows=[json.loads(x) for x in f.read_text().splitlines() if x.strip()]; valid=[r for r in rows if r.get('ok') and isinstance(r.get('objective'),(float,int)) and math.isfinite(r['objective'])]; seed=next((r for r in valid if r.get('n')==0),None); best=min(valid,key=lambda r:r['objective']) if valid else None; first=next((r for r in valid if seed and r['n']>0 and r['objective']<seed['objective']),None)
 cfg=d.get('config',{}); bounds=cfg.get('bounds',{}); pars=(best or {}).get('params',{}); knobs=pars.get('grid',{}).get('knobs',pars.get('osse',{})); pinned=[]
 for k,b in bounds.items():
  v=knobs.get(k); lo=b.get('lo'); hi=b.get('hi');
  if isinstance(v,(float,int)) and isinstance(lo,(float,int)) and isinstance(hi,(float,int)) and hi>lo and min(abs(v-lo),abs(v-hi))/(hi-lo)<.05: pinned.append(k)
 identities=collections.Counter((r.get('params',{}).get('grid',{}).get('rows',{}).get('implementation_sha256'),r.get('generator',{}).get('brief_hash')) for r in rows)
 rec={'run':p.parent.name,'command':cmd,'config_path':d.get('config_path'),'config_sha':d.get('config_sha'),'objective_version':d.get('objective_version'),'status':d.get('status'),'budget':d.get('budget'),'cma_seed':d.get('cma_seed'),'search':cfg.get('search'),'attempt_rows':len(rows),'usable_rows':len(valid),'cached_rows':sum(bool(r.get('cached')) for r in rows),'refusals':dict(collections.Counter((r.get('kind') or r.get('error') or 'unknown') for r in rows if not r.get('ok'))),'seed_J':seed.get('objective') if seed else None,'best_J':best.get('objective') if best else None,'gain':seed['objective']-best['objective'] if seed and best else None,'best_at':best.get('n') if best else None,'first_improvement':first.get('n') if first else None,'best_terms':best.get('terms') if best else None,'seed_terms':seed.get('terms') if seed else None,'best_design_hash':best.get('design_hash') if best else None,'best_boundary_5pct':pinned,'inactive_or_fixed':[k for k,b in bounds.items() if not b.get('search',True) or b.get('hi')==b.get('lo')],'identity_counts':[{'implementation_sha256':a,'brief_hash':b,'count':n} for (a,b),n in identities.items()],'source':str(f).replace('\\','/')};records.append(rec)
(out/'runs_current.json').write_text(json.dumps(records,indent=2)+'\n'); fields=['run','config_path','status','budget','cma_seed','attempt_rows','usable_rows','cached_rows','refusals','seed_J','best_J','gain','best_at','first_improvement','best_boundary_5pct','inactive_or_fixed','identity_counts','source'];
with (out/'runs_current.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(records)
for r in records:print(r['run'],pathlib.Path(str(r['config_path'])).stem,'rows',r['attempt_rows'],'ok/cache',r['usable_rows'],r['cached_rows'],'fail',r['refusals'],'seed/best',r['seed_J'],r['best_J'],'first/best',r['first_improvement'],r['best_at'],'pinned',r['best_boundary_5pct'])
