import pickle,pathlib,yaml,collections,re,json
R=pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb')); groups=collections.defaultdict(dict)
def sib(g):
 g=re.sub(r'_v\d+$','',g).replace('_smooth','')
 if g.startswith('sp__'):return 'sp__control_moderate_strong'
 if g.startswith('rr__pucker') or g=='rr__reference':return 'rr__reference_pucker'
 if g.startswith('klangfilm_hv__a'):return 'klangfilm_hv__axis_variants'
 return g
for r in R:
 if r['config'] not in groups[sib(r['config'])]:
  p=pathlib.Path('runs')/r['run']/'config.yaml';cfg=yaml.safe_load(p.read_text());groups[sib(r['config'])][r['config']]=dict(seed=cfg.get('seed_params',{}),generator=cfg.get('grid',{}))
out={}
for g,lanes in groups.items():
 if len(lanes)<2: continue
 keys=sorted(lanes); pairs=[]
 for i in range(len(keys)):
  for j in range(i+1,len(keys)):
   a,b=lanes[keys[i]],lanes[keys[j]];ka=set(a['seed'])|set(b['seed']);diff=[k for k in sorted(ka) if a['seed'].get(k)!=b['seed'].get(k)];pairs.append(dict(a=keys[i],b=keys[j],seed_differences=diff,generator_equal=a['generator']==b['generator']))
 out[g]=pairs
print(json.dumps(out,indent=2))
