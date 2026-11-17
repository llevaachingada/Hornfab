import json,pathlib,collections,sys,pickle,numpy as np
from hornlab_search.metrics.di import di_slope_db_per_decade
from scipy.stats import spearmanr
cohort=sys.argv[1] if len(sys.argv)>1 else 'cd'
paths=([pathlib.Path('scratch/fable_architecture/.s1/records_cd_corrected.jsonl'),pathlib.Path('scratch/fable_architecture/.s1/records_smooth_corrected.jsonl')] if cohort=='combined' else [pathlib.Path('scratch/fable_architecture/.s1/records_'+cohort+'_corrected.jsonl')])
allrows=[]
for p in paths:
 if p.exists():
  for line in p.open(encoding='utf-8-sig'): 
   try: allrows.append(json.loads(line))
   except json.JSONDecodeError: pass
rows=[]; seen=set()
lookup={(r['run'],r['h']):r for r in pickle.load(open('scratch/fable_architecture/.fable/rows.pkl','rb')) if r['ok']}
for r in allrows:
 key=(r['run'],r['hash'])
 if r['run'] and r['hash'] and key not in seen:
  src=lookup[key]; f=np.array(src['f']); di=np.array(src['di']); use=(f>=700)&(f<=8000); slope=di_slope_db_per_decade(f[use],di[use])
  for v in r['cases'].values(): v['all_dead']=v['dead']+(max(0.,-slope,slope-3.)**2-slope**2)/9.
  rows.append(r);seen.add(key)
n=len(rows); keys=(['v9','strict','linear','dead','all_dead'] if cohort=='combined' else ['v7','v9','strict','linear','dead','all_dead']); base='0,1000'
def score(r,k,case=base):return r['v7'] if k=='v7' else r['cases'][case][k]
def top(k,case=base):return sorted(range(n),key=lambda i:(score(rows[i],k,case),rows[i]['hash'],rows[i]['run']))
order={k:top(k) for k in keys}; lanes=sorted(set(r['lane'] for r in rows)); out=[]
out.append(f'Scored attempts {len(allrows)}, unique run/design {n}, unique design hashes {len(set(r["hash"] for r in rows))}; duplicate attempts within a run are collapsed for ranking. Across-run responses remain separate observations.\n')
for k in keys:
 out.append('\n## '+k+' top 20\n\n| Rank | Run / hash | Lane | Score | H mean ± SD | V mean ± SD | Ripple dB | Loading normalized |\n|---:|---|---|---:|---:|---:|---:|---:|')
 for j,i in enumerate(order[k][:20],1):
  r=rows[i]; c=r['cases'][base]; h=c['h']; v=c['v']; out.append(f'| {j} | {r["run"]} / {r["hash"]} | {r["lane"]} | {score(r,k):.4f} | {h[0]:.1f} ± {h[1]:.1f} | {v[0]:.1f} ± {v[1]:.1f} | {c["rip_db"]:.3f} | {c["load_term"]:.3f} |')
out.append('\n## Comparisons\n')
for i,k in enumerate(keys):
 for l in keys[i+1:]:
  ov20=len(set(order[k][:20])&set(order[l][:20]));ov100=len(set(order[k][:100])&set(order[l][:100])); rho=spearmanr([score(r,k) for r in rows],[score(r,l) for r in rows]).statistic
  out.append(f'- {k} / {l}: top-20 overlap {ov20}; top-100 overlap {ov100}; Spearman {rho:.3f}.')
out.append('\n## Best by lane\n\n| Lane | '+' | '.join(k+' hash / J' for k in keys)+' |\n|---|'+'---|'*len(keys))
for lane in lanes:
 rr=[r for r in rows if r['lane']==lane]; cells=[]
 for k in keys:
  r=min(rr,key=lambda r:score(r,k));cells.append(f'{r["hash"]} / {score(r,k):.3f}')
 out.append('| '+lane+' | '+' | '.join(cells)+' |')
ranks={}
for k in keys:
 ordered=sorted(lanes,key=lambda lane:min(score(r,k) for r in rows if r['lane']==lane)); ranks[k]={lane:i+1 for i,lane in enumerate(ordered)}
out.append('\n## Lane ranks under every total (lanes spanning more than three positions)\n\n| Lane | '+' | '.join(keys)+' |\n|---|'+'---:|'*len(keys))
for l in lanes:
 vals=[ranks[k][l] for k in keys]
 if max(vals)-min(vals)>3: out.append('| '+l+' | '+' | '.join(map(str,vals))+' |')
if 'v7' in keys:
 out.append('\n## Lane rank changes greater than three (v7 → strict)\n')
 for l in lanes:
  a,b=ranks['v7'][l],ranks['strict'][l]
  if abs(a-b)>3:out.append(f'- {l}: {a} → {b} ({b-a:+d})')
out.append(f'\nZero total with three specified dead bands: {sum(abs(score(r,"dead"))<1e-12 for r in rows)}; adding DI slope range 0–3 dB/decade: {sum(abs(score(r,"all_dead"))<1e-12 for r in rows)}. Flat CV and constancy remain active.\n')
out.append('\n## Sensitivity (within each objective, overlap with its base case and Spearman against base)\n')
for s in (-5,0,5):
 for v in (700,1000,1250):
  case=f'{s},{v}'
  for k in ('v9','strict','linear','dead','all_dead'):
   baseorder=order[k]; b=[score(r,k) for r in rows]; order2=top(k,case); x=[score(r,k,case) for r in rows];out.append(f'- {k}, shift {s:+d}°, V onset {v} Hz: top-20 / top-100 overlap {len(set(baseorder[:20])&set(order2[:20]))} / {len(set(baseorder[:100])&set(order2[:100]))}; Spearman {spearmanr(b,x).statistic:.3f}; first {rows[order2[0]]["lane"]} / {rows[order2[0]]["hash"]}.')
pathlib.Path('scratch/fable_architecture/.s1/tables_'+cohort+'.md').write_text('\n'.join(out),encoding='utf-8')
print('wrote',n,'rows')
