# Evidence dossier: file layout and quality contract

This file is a **suggested output contract for research artifacts, not a mandated software architecture**. Its purpose is to prevent cheap agents from giving Fable polished but unsubstantiated recommendations.

## Output directory

Create in an ignored `scratch/fable_architecture/` folder after verifying it will not enter the tracked tree, or use an external notes folder. Output:

```
INDEX.md                         ~1–3 pages; first file Fable reads
SOURCE_INDEX.md                  exact source links, relative paths, hashes, timestamps
GEOMETRY_AND_PARAMETER_MAP.md    facts on shape families, controls, equivalence and coupling
FAILURE_AND_BOUNDARY_AUDIT.md    failure mechanisms, constraint classes, sample denominators
OPTIMIZATION_AND_BRIEF_AUDIT.md  actual optimizer compatibility, scoring and data reuse
SIZE_FEASIBILITY_EVIDENCE.md     optional: separate size-constraint vs acoustic-discovery audit
EXTERNAL_EVIDENCE.md            primary research and points of disagreement
EVIDENCE_LEDGER.md              compact atomic claims with references
OPEN_QUESTIONS.md               prioritized research gaps and uncertainties
```

Agents may combine or split files if justified; they must maintain a clear index.

## Atomic evidence ledger entry

Use one entry per nontrivial claim:

```markdown
### E-018: [short, testable claim]
- **Status:** directly verified | historical run record | reproduction | plausible inference | unverified | contradicted
- **Claim:** precise statement, including which config/family/mode it applies to
- **Evidence:** `path/to/file.py:L123-L140` at commit SHA; run ID, `run.json` key, raw command/output; URL or exact paper section
- **Counterevidence / limits:** cases where it may fail, missing local data, other possible causes
- **Implication:** optional, one sentence; label this as interpretation rather than fact
- **Follow-up:** specific cheap check or Fable judgment needed, if any
```

For external research include author/title/year, stable URL/DOI, the actual claim supported, and conditions under which the result transfers to Hornfab. An abstract isn't proof that an algorithm beats our pipeline on expensive BEM.

## Mandatory distinctions

- **Search boundary** versus **mesher hard validity** versus **physical/manufacturing limit** versus **brief/envelope requirement** versus **GPU/resource limit**.
- **Product size envelope** versus **geometric correctness** versus **throat/source physics** versus **finite GPU resources**. Differentiate *conservative pre-mesh size estimate*, *true mesh bounding box*, and *user's final acceptable dimensions*. An oversize rejection has no measured acoustic score.
- If proposing to widen a design space, identify the matched experiment controls, old/new vector re-encoding, solver/score identity compatibility, and a realistic compute cap; no new GPU work is automatically authorized.
- **Candidate attempts**, **unique candidates**, **valid geometry**, **complete BEM solves**, **verified finalists**, **time**, and **cache hits** have different denominators.
- **CMA-ES informed by penalties**, **CMA strict rejection/resampling**, **BoTorch complete acoustic training data**, and **a separate learned feasibility model** are different. Rejected geometry must not be represented as measured acoustic performance.
- **Physical response replay** and **objective re-score** may reuse data, but not necessarily across changed meshes, source models, symmetry assumptions, frequency support, or fields absent from a saved response.
- The user's **idealization of the HF1440 driver exit**, published-horn reference claims, and actual physical source behavior are distinct.
- `main` and a local dirty branch may differ. Every report must say **which one it actually checked**.
- **Unsolved** is not **unbuildable**. **CPU geom pass** is not **BEM verified**. **High score** is not **listening superiority**.

## Acceptance checklist for the consolidating agent

- [ ] Exact commit, local branch, working-tree condition, evidence/report timestamps recorded.
- [ ] Direct source references support every headline; historical claims clearly dated.
- [ ] Old plans are not reported as new work; implementation status checked in actual code.
- [ ] Existing analyzers and tests were inventoried before suggesting new code.
- [ ] Contradictory facts were preserved with uncertainty, not resolved by guessing.
- [ ] Each task has relevant negative evidence/failure cases.
- [ ] Handoff index is short enough for Fable to scan before opening deeper files.
- [ ] **No tracked files changed; no live queue changed; no GPU solve executed** during research.
- [ ] Open questions identify the *decision they would change*, not merely that further research is possible.

## v3: time-ordered adaptive-policy evidence

For watchdog/switch findings include **local commit SHA, exact code branch/rule, observation timestamp/row, failure category, physical-versus-cached call status, actual cost when known, measured metric/score version, compatible cohort/active dimension, strict BO readiness and baseline alternative**. Separate *observed stop and subsequent actual continuation* from **unknown unchosen counterfactual**. Mark whether best scalar `J` and/or QD/novelty/verified physical metrics improved; a stalled objective is not equivalent to no scientific value. Record estimated costs as estimates with method and uncertainty. When counting prior rows, respect scorer/source/frequency/sampling identities. The additional source-backed outputs are specified in `10_CHEAP_AGENT_SEARCH_SUPERVISOR_PASS.md`.
