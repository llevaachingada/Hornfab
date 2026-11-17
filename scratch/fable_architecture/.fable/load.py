"""Read-only loader: every ok row on the 80x50 / 600x480x480 landscape brief -> pickle."""
import json, glob, pathlib, pickle, yaml, numpy as np
rows=[]
for rd in sorted(glob.glob('runs/2026111[5-7]*-screen-*')):
    rd=pathlib.Path(rd)
    try: cfg=yaml.safe_load(open(rd/'config.yaml'))
    except Exception: continue
    br=cfg.get('brief') or {}; t=cfg.get('target') or {}; env=br.get('envelope') or {}
    if not (t.get('coverage_h_deg')==80 and t.get('coverage_v_deg')==50 and env.get('max_mouth_h_mm')==480): continue
    brief='smooth' if 'smooth' in str(br.get('name')) else 'cd'
    gen=cfg.get('generator') or {}
    engine=cfg.get('family') or ''
    gname=(gen.get('name') if isinstance(gen,dict) else '') or ''
    rtype=((gen.get('spec') or {}).get('rows') or {}).get('type','') if isinstance(gen,dict) else ''
    search=cfg.get('search') or {}
    bounds=cfg.get('bounds') or {}
    try: lines=[json.loads(l) for l in open(rd/'search.ndjson')]
    except Exception: continue
    for r in lines:
        ok=bool(r.get('ok')) and isinstance(r.get('objective'),(int,float)) and r['objective']<900
        m=r.get('metrics') or {}
        rows.append(dict(run=rd.name,config=cfg.get('name'),brief=brief,engine=engine,gen=gname,rtype=rtype,
            algo=search.get('algorithm','cma'),n=r.get('n'),ok=ok,kind=r.get('kind'),J=r.get('objective') if ok else None,
            terms=r.get('terms') if ok else None,params=r.get('params'),knobs=(r.get('generator') or {}).get('knobs') if isinstance(r.get('generator'),dict) else None,
            bbox=r.get('bbox_m'),ndof=r.get('n_dof'),h=r.get('design_hash'),sec=(r.get('seconds') or {}).get('total') if isinstance(r.get('seconds'),dict) else None,
            f=m.get('freqs_hz'),bwh=m.get('bw_h_deg'),bwv=m.get('bw_v_deg'),di=m.get('di_db'),cached=r.get('cached'),
            bounds=bounds, created=r.get('created_utc')))
pickle.dump(rows,open('scratch/fable_architecture/.fable/rows.pkl','wb'))
import collections
print(len(rows),'rows', sum(r['ok'] for r in rows),'ok')
c=collections.Counter((r['engine'],r['gen'],r['rtype']) for r in rows if r['ok']); print(c.most_common(30))
print(collections.Counter(r['algo'] for r in rows))
r=[x for x in rows if x['ok']][0]; print({k:(v if not isinstance(v,(list,dict)) else type(v).__name__+str(len(v))) for k,v in r.items()}); print(r['params'] if not r['knobs'] else r['knobs']); print(list(r['bounds'].items())[:3])
