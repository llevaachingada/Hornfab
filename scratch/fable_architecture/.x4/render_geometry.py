import json,numpy as np
paths=['scratch/fable_architecture/.x4/geometry.json','scratch/fable_architecture/.x4/geometry_fifth.json','scratch/fable_architecture/.x4/generated_geometry.json'];parts=['\n## Follow-up: five-lane exploratory Jacobians and conditionals\n','This section supersedes the earlier statement that GRID/GEN-FF Jacobians were not implemented. The same 1%-bound-range, one-sided finite difference and provisional X1 sampling protocol was run on five lanes spanning all three engine groups. For generated lanes, knobs were rematerialized with each original run config; every included baseline regenerated the archived design hash. Each table shows RMS displacement across surface sample points in mm, median and maximum across the 11 sampled designs, not maximum displacement at any point. Full singular values and per-design cosine pairs are in the JSON artifacts. Sampler fidelity, near-throat behavior and box-corner checks remain unverified.\n']
for path in paths:
 data=json.load(open(path))
 for lane,d in data.items():
  a=[x for x in d['results'] if 'movement'in x]
  if not a: continue
  m=np.array([x['movement'] for x in a]);parts+=['\n### '+lane+f" (n={len(a)}, normalized ranks {min(x['rank'] for x in a)}–{max(x['rank'] for x in a)})\n",'| Knob | Median movement (mm) | Maximum of design RMS (mm) |','|---|---:|---:|']
  for i,k in enumerate(d['keys']):parts.append(f'| {k} | {np.median(m[:,i]):.4f} | {np.max(m[:,i]):.4f} |')
  pairs=sorted(set((p[0],p[1]) for x in a for p in x['pairs']));parts.append('\nPairs exceeding absolute cosine .95 on at least one design: '+(', '.join(f'`{x}` / `{y}`' for x,y in pairs) if pairs else 'none')+'.')
parts+=['''

### Conditional spot checks

On the best stored `hl__osse_rrect_fold_warm_v7` native design, varying the following at the stated condition produced zero pointwise displacement on the sampled surface: `n` and `q` at `s=0` (also forcing `s1=s2=0` and azimuthal s modulation to zero); `s1` when `s2=0`; `s2` when `s1=0`; morph width and morph rate when `morph_target=0`; morph exponent at target 1. Positive controls produced RMS movement of 1.052 mm for `n` at positive `s`, 56.533 mm for `s1` at positive `s2`, 2.679 mm for `s2` at positive `s1`, and 18.589 mm for morph exponent at target 3. The positive `q` control failed: `UnsupportedGeometryError`, axial chord still 8.77 times its limit at the 2,048-segment refinement ceiling. `guiding curve` replacement of `a_deg` and `rot_deg` coupling were not tested. These are single-design checks with experimental sampling and selected values, not a box-wide inactivity classification; actual settings and errors are recorded in `.x4/conditionals.py` and `.x4/conditionals.txt`.

### Reproducibility blockers

All 11 attempted rematerializations for each of `hl__klangfilm_lame_curved_v1`, `hl__crowe_panel_home_v7`, and `hl__rosse_rect_cd_v7` failed before sampling. Current `generated.materialize` reports `GeneratorError: unknown rows type` respectively `klangfilm_lame`, `crowe_panel`, and `rosse_rect`; the complete messages and rows are in `.x4/generated_geometry.json`, `.x4/generated_geometry_extra.json`, and `.x4/generated_geometry_fifth.json`. This is an adapter compatibility finding at the current code, not evidence of inactive knobs or bad archived designs.

The five-lane geometric quota is now sampled, but classification, constraint margins, per-point maxima, targeted near-throat weighting, corner scans, all conditional cases, all-lane acoustic evidence and Parts C/D agreement criteria are still incomplete. These data do not support an overall X4 pass/failure or any fix/link recommendation.
''']
with open('scratch/fable_architecture/X4_PARAMETER_SPACE.md','a',encoding='utf8') as f:f.write('\n'.join(parts))
