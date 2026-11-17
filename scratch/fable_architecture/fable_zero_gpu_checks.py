import json, glob, pathlib, dataclasses, sys, warnings
import numpy as np
from scipy.interpolate import PchipInterpolator
warnings.filterwarnings('ignore')
from hornlab_search.solve.cache import load_response
from hornlab_search.objective import replay as R
from hornlab_search.targets.spec import Target

def score(resp, brief, target=None):
    meta={"ok":True,"design_hash":"x","family":"","params":{}}
    res=R._replay_core(meta, None, response=resp, stored_metrics=None, stored_metric_reasons=[],
        brief=brief, target=target, weights_override=None, objective_params_override=None,
        objective_version_override=None, regenerate_metrics=True, allow_metric_regeneration=True)
    return res

def interp(resp, fnew):
    lf=np.log(resp.freqs_hz); ln=np.log(fnew)
    def I(a):
        if a is None: return None
        a=np.asarray(a)
        if np.iscomplexobj(a):
            return PchipInterpolator(lf,a.real,axis=0)(ln)+1j*PchipInterpolator(lf,a.imag,axis=0)(ln)
        return PchipInterpolator(lf,a,axis=0)(ln)
    return dataclasses.replace(resp, freqs_hz=np.asarray(fnew,float), spl_h_db=I(resp.spl_h_db), spl_v_db=I(resp.spl_v_db),
        spl_balloon_db=I(resp.spl_balloon_db), z_throat=I(resp.z_throat), p_h=None,p_v=None,p_balloon=None)

if sys.argv[1]=='A':
    rows=[]
    for S in sorted(glob.glob('runs/study-*')):
        S=pathlib.Path(S)
        if not (S/'verify/designs').is_dir() or not (S/'screen/designs').is_dir(): continue
        bs=R.brief_from_config(S/'screen/config.yaml'); bv=R.brief_from_config(S/'verify/config.yaml')
        for h in sorted({p.name for p in (S/'screen/designs').iterdir()}&{p.name for p in (S/'verify/designs').iterdir()}):
            try:
                a=json.load(open(S/'screen/designs'/h/'status.json')); b=json.load(open(S/'verify/designs'/h/'status.json'))
                if not(a.get('ok') and b.get('ok')): continue
                ra=load_response(S/'screen/designs'/h/'response.npz'); rb=load_response(S/'verify/designs'/h/'response.npz')
                js=score(ra,bs); jv=score(rb,bv); ji=score(interp(ra,rb.freqs_hz),bv)
                dense=np.geomspace(300,8000,58)
                jd_s=score(interp(ra,dense),bv); jd_v=score(interp(rb,dense),bv)
                rows.append((a['objective'],b['objective'],js.j,jv.j,ji.j,jd_s.j,jd_v.j,js.status))
            except Exception as e:
                print('skip',S.name,h[:8],repr(e)[:150])
    r=np.array([x[:7] for x in rows],float); print('n',len(r), 'status',set(x[7] for x in rows))
    print('replay parity: max|screen replay-stored| %.4f  max|verify replay-stored| %.4f'%(np.nanmax(abs(r[:,2]-r[:,0])),np.nanmax(abs(r[:,3]-r[:,1]))))
    from scipy.stats import spearmanr
    for name,m in (('all',np.ones(len(r),bool)),('top (screen J<3.6)',r[:,0]<3.6)):
        x=r[m]
        def st(d): return 'bias %+.3f sd %.3f'%(np.mean(d),np.std(d,ddof=1))
        print(name,'n',m.sum())
        print('  raw screen vs verify      :',st(x[:,1]-x[:,0]),' spearman %.2f'%spearmanr(x[:,0],x[:,1])[0])
        print('  screen->verify-grid interp:',st(x[:,1]-x[:,4]),' spearman %.2f'%spearmanr(x[:,4],x[:,1])[0])
        print('  both on dense 58pt grid   :',st(x[:,6]-x[:,5]),' spearman %.2f'%spearmanr(x[:,5],x[:,6])[0])

if sys.argv[1]=='B':
    import yaml, collections
    best={}
    for rd in sorted(glob.glob('runs/2026111[5-7]*-screen-*')):
        rd=pathlib.Path(rd)
        try: cfg=yaml.safe_load(open(rd/'config.yaml'))
        except Exception: continue
        br=cfg.get('brief') or {}; t=cfg.get('target') or {}; env=br.get('envelope') or {}
        if not (t.get('coverage_h_deg')==80 and t.get('coverage_v_deg')==50 and env.get('max_mouth_h_mm')==480): continue
        if 'smooth' in str(br.get('name')): continue
        try: rows=[json.loads(l) for l in open(rd/'search.ndjson')]
        except Exception: continue
        ok=[r for r in rows if r.get('ok') and isinstance(r.get('objective'),(int,float)) and r['objective']<900]
        if not ok: continue
        b=min(ok,key=lambda r:r['objective']); k=cfg.get('name')
        if k not in best or b['objective']<best[k][0]: best[k]=(b['objective'],rd,b)
    top=sorted(best.items(),key=lambda kv:kv[1][0])[:12]
    SC=[1.0,1.1,1.2,1.35,1.5]; g=np.geomspace(250,8000/1.5,44)
    def bwm(m,f,key,lo,hi):
        bw=np.asarray(getattr(m,key),float); mm=(f>=lo)&(f<=hi); return np.nanmean(bw[mm])
    print('scale s => envelope %s' % ', '.join(f'{s}:{600*s:.0f}x{480*s:.0f}' for s in SC))
    print('columns per s: J(trunc band 350-5333) | cov-term raw | V bw 700-1.1k | H bw 700-1.1k')
    agg=collections.defaultdict(list)
    for name,(J,rd,b) in top:
        try:
            brief=R.brief_from_config(rd/'config.yaml')
            resp=load_response(rd/'designs'/b['design_hash']/'response.npz')
            td=(dataclasses.asdict(brief.target) if dataclasses.is_dataclass(brief.target) else dict(brief.target)); td['band_hi_hz']=float(g[-1]); td['loaded_hi_hz']=min(td.get('loaded_hi_hz') or 1e9, float(g[-1]))
            line=f'{name[:34]:34s} J0={J:5.2f} '
            for s in SC:
                rs=dataclasses.replace(resp,freqs_hz=resp.freqs_hz/s)
                ri=interp(rs,g)
                res=score(ri,brief,target=Target.from_dict(td))
                from hornlab_search.metrics.compute import compute_metrics
                m=compute_metrics(ri,Target.from_dict(td))
                v=bwm(m,g,'bw_v_deg',700,1100); h=bwm(m,g,'bw_h_deg',700,1100)
                T=res.terms; line+=f"| {res.j:5.2f} {T.get('cov',0):4.2f} {T.get('load',0):4.2f} {v:3.0f} {h:3.0f} "
                agg[s].append((res.j,res.terms.get('cov',np.nan),v,h, res.terms.get('load',np.nan)))
            print(line)
        except Exception as e:
            print(name,'ERR',repr(e)[:200])
    for s in SC:
        a=np.array(agg[s]); print(f's={s}: median J {np.median(a[:,0]):.2f}  median cov {np.nanmedian(a[:,1]):.2f}  median V(700-1.1k) {np.median(a[:,2]):.0f}  H {np.median(a[:,3]):.0f}  median load-term {np.nanmedian(a[:,4]):.3f}')
