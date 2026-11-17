import json,numpy as np
p='scratch/fable_architecture/X4_PARAMETER_SPACE.md';a=json.load(open('scratch/fable_architecture/.x4/acoustic.json'));s=['\n## Exploratory acoustic importance\n','For each lane and target, five bootstrap training resamples were fit with ExtraTrees; each replicate uses a held-out random 20% from the same time subset and five permutation repeats. Entries are medians of held-out R² drop, with the range across the five bootstrap replicates in parentheses. Negative values indicate degradation in estimated importance, not evidence of inactivity. H and V targets are mean squared differences from 80° and 50° over frequencies ≥700 Hz, not full objective components. Sampling is clustered and models/importance are associational. Early and late halves are separately fit; no geometric labels, margin checks or classification agreement are inferred.\n']
for name,d in a.items():
 s+=['\n### '+name+f" (n={d['n']})\n",'| Knob | J median [min,max] | H coverage error | V coverage error |','|---|---:|---:|---:|']
 m=d['models']['all'];
 for i,k in enumerate(d['keys']):
  vals=[f"{m['median'][j][i]:.3f} [{m['minimum'][j][i]:.3f}, {m['maximum'][j][i]:.3f}]" for j in range(3)];s.append('| '+k+' | '+' | '.join(vals)+' |')
 for j,t in enumerate(['J','H','V']):
  n=max(1,int(np.ceil(len(d['keys'])/3)));e=set(np.argsort(d['models']['early']['median'][j])[-n:]);l=set(np.argsort(d['models']['late']['median'][j])[-n:]);s.append(f"\n{t} top-third early/late feature overlap: {len(e&l)}/{n}; descriptive ranking stability, not X4 Part D label agreement.")
open(p,'a',encoding='utf8').write('\n'.join(s)+'\n\nSee `.x4/acoustic.py` and `.x4/acoustic.json` for complete reproducible results.\n')
