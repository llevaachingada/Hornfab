"""Index the saved audit without changing production code or historical artifacts."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
Q=ROOT/'docs/queue/rolled_readiness_2026-11-15'

def append(path,text):
    if text.encode('utf8') in (ROOT/path).read_bytes():return
    with (ROOT/path).open('ab') as f:f.write(text.encode('utf8'))

def after_header(path,text):
    p=ROOT/path;b=p.read_bytes();i=b.find(b'\n')+1
    if text.encode('utf8') in b:return
    p.write_bytes(b[:i]+text.encode('utf8')+b[i:])

link='docs/research/typologies/audit_2026-11-15/'
block='''
## 2026-11-15 — Rolled-family senior audit; spiral diagnostics and guarded queue

- Read `docs/research/typologies/audit_2026-11-15/HANDOFF.md` then `READINESS.md` in that directory.
- Owner subsequently allowed a few isolated acoustic diagnostics; full searches remain held on unresolved families. No Bayesian work on new typologies. Two real uncached spiral seed evaluations completed, EPW6/8, same design,4500/5277DOFs,J29.915059/29.913599. Not established convergence; GPU workers cleaned afterward.
- New queue draft `docs/queue/rolled_readiness_2026-11-15/pilot_HELD.yaml`: two guarded spiral RNGseeds1234/5678,30 valid-target evaluations each. No controller launched; admission is false.26 frozen horn/brief config copies load; other families excluded pending gates. Retry/validation cost must be reconciled before campaign release. Preserve old D/E history; do not resume its unused BO/long-run tail.
- Research corrected source/construction/objective claims: HF1440 combined exit does not establish2deg cone; Hypex mislabeled Crowe variant; distd is DI std, not detrended smoothness; actual Gaussian DI target13.079574dB; raw Crowe normal angle is not proof of inverted winding. Primary sources,600-row domains,17-run histories,32 exact offline score replays, original-mesh witnesses and bounded implementation prompts saved.
- Verification:61 native CPU tests plus9 wrapper checks and5 generic strict-resume tests; dedicated spiral real-evaluator/CPU-mesh/synthetic-backend resume preserved5 cached rows and added4, all9 full surfaces replayed. Synthetic responses are clearly segregated. Original generators/briefs/configs and concurrent dirty work preserved. No commits.

'''
after_header(Path('docs/CONTINUITY.md'),block)
after_header(Path('docs/ISSUES.md'),'''\nLocal-only2026-11-15 (**rolled readiness audit; no GitHub issue state changed**):
- Complete current pickup: `docs/research/typologies/audit_2026-11-15/HANDOFF.md` and `READINESS.md`.
- Two isolated spiral acoustic diagnostics completed under updated owner permission; no full searches or Bayesian jobs. New guarded30x2 spiral draft and26 load-checked frozen configs: `docs/queue/rolled_readiness_2026-11-15/README.md`. Source/objective/body/cost gates remain; admission held. Preserve all old D/E records and original designs.

''')
append(Path('NOTES_FOR_SENIOR.md'),'''\n## 2026-11-15 — Rolled/ATH/Crowe audit completion and remaining admission gates

Read `docs/research/typologies/audit_2026-11-15/HANDOFF.md`. Critical new source finding: FaitalPRO HF1440 specifies35.8mm combined exit, not a2deg cone; preserve18mm/2deg as historical model assumptions.32 stored scores replay exactly. Crowe raw fold angles reproduce but original indexed winding is consistent. Source/body/physical control and objective decisions remain senior work. Priority spiral execution, actual CPU mesh/resume and two real spatial-resolution seed diagnostics now have evidence;26 frozen configs load. Guarded queue is held, no BO and no launch. Budget30 valid targets does not hard-cap retries/verification; finish accounting before release. No original source/brief/domain changes or commits in this audit.
''')
append(Path('docs/INDEX.md'),'''\n## Rolled-family readiness pickup (2026-11-15)

- [Senior findings and readiness matrix](research/typologies/audit_2026-11-15/READINESS.md)
- [Next senior handoff](research/typologies/audit_2026-11-15/HANDOFF.md)
- [Exact domains and coupled constraints](research/typologies/audit_2026-11-15/PARAMETER_DOMAINS.md)
- [Held queue and26 prepared horn files](queue/rolled_readiness_2026-11-15/README.md)
''')
append(Path('docs/CODE_MAP.md'),'''\n## Rolled readiness audit tooling (2026-11-15)

`docs/research/typologies/audit_2026-11-15/` contains reproducible source-equation, domain, mesh topology, offline objective, spiral mock/resume and evidence-packaging scripts. They are research tooling, not production generators. `docs/queue/rolled_readiness_2026-11-15/reviewed_job.py` is an additive fail-closed queue gate;26 frozen configs and matching entry points are recorded in admission.json. See that packet's README before use; no full-search admission granted.
''')
append(Path('.claude/skills/hornlab-typology-research/SKILL.md'),'''\n## Saved Crowe / ATH / rolled-family audit (2026-11-15)

For these families, start with `docs/research/typologies/audit_2026-11-15/HANDOFF.md` and `READINESS.md`; source tables, exact domains, equation checks, original-mesh witnesses and objective ablations are already saved. Avoid repeating the full research pass. Key distinctions: axial relief vs radial morph; original spiral/hybrid vs proprietary Crowe CAD; R-OSSE nominal angle vs actual tangent; configured driver interface vs manufacturer combined exit. A rendered return, indexed winding, successful mesh, full-rank geometry Jacobian or low J is a separate claim from useful converged acoustics. Wrapper source bytes are pinned; use the existing direct spiral verify-night helper instead of casually patching a wrapper. The current owner authorizes a few isolated diagnostics, not a full unresolved search; no BO on new typologies.
''')
ac=json.loads((HERE/'SPIRAL_ACOUSTICS.json').read_text())
(HERE/'SPIRAL_ACOUSTICS.md').write_text('''# Real spiral diagnostics — two calls only

Exact numeric provenance and raw paths: [SPIRAL_ACOUSTICS.json](SPIRAL_ACOUSTICS.json). Same physical design and solve hash, fixed surface sampling/frequencies/angular observations; spatial EPW6→8 only.4500→5277 DOFs, J29.915059→29.913599. Full search readiness and asymptotic convergence are not claimed.

Baseline before first job921MiB and before finer job is saved in spiral_acoustic_epw8_baseline.txt (desktop usage varied). WDDM process-tree monitors reported dedicated peaks330/348MiB and shared80/80MiB, no spill by the tool's threshold; these process-tree figures are not whole-GPU usage and should not be substituted for it. No general speed/VRAM-ceiling claim. Runtime wall54.016/50.125s includes cold start. Cleanup removed this pass's worker trees.

Fresh generated views from the EPW6 solved mesh:

![Front oblique](spiral_renders/spiral_a.png)
![Rear oblique](spiral_renders/spiral_b.png)
![Underside](spiral_renders/spiral_u.png)

[H/V sections of the matching seed](../img_biradial_crowe_2026-11-15/packet/sections_es_spiral.png). The sections show the original seed geometry; newly generated views above use this pass's actual solved mesh. All model/source limitations in READINESS.md apply.
''',encoding='utf8')
(HERE/'QUEUE_REVIEW.json').write_text(json.dumps({'current':'held','new_queue':str((Q/'pilot_HELD.yaml').relative_to(ROOT)),
 'old_E_tail':'do not resume; retain evidence; long CMA/verify/cohort/BO jobs quarantined by plan',
 'new_jobs':['spiral_s1234','spiral_s5678'],'valid_target_each':30,'proposal_draw_cap_each':45,
 'real_diagnostic_calls_completed':2,'bayesian_jobs':0,'controller_started':False,
 'remaining_gates':['source model','objective','full body','control capability','retry+validation total cost','explicit campaign release']},indent=2)+'\n')
snapshot={'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
 'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
 'note':'Concurrent dirty changes preserved; no commit performed by audit.'}
(HERE/'final_snapshot.json').write_text(json.dumps(snapshot,indent=2)+'\n')
files=[p for folder in (HERE,Q) for p in folder.rglob('*') if p.is_file() and p.name!='manifest.json' and '__pycache__' not in str(p)]
(HERE/'manifest.json').write_text(json.dumps({'files':[{ 'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]},indent=2)+'\n')
print('Indexed audit in CONTINUITY, ISSUES, NOTES, INDEX, CODE_MAP and project research skill; manifest saved.')
