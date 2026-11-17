# Fable discovery evidence handoff (2026-11-16)

**Status:** research dossier delivered; **no code, config, queue, objective, solver or pin was
changed.** This note is the tracked digest. The full evidence dossier was produced read-only in the
local git-ignored folder `scratch/fable_architecture/` per the v3 handoff instruction
(`02_EVIDENCE_FORMAT.md`), so it is not in this commit. Re-run the same read-only pass, or read the
local folder, to get the 15 artifact files listed below.

**Question:** what representation of horn designs, design goals, feasibility constraints and search
process discovers more acoustically excellent, diverse, feasible horns per unit of compute, while
retaining the value of existing results? This is preparation for a Fable discovery/decision pass, not
an architecture decision.

## Snapshot and provenance

- Repo `C:\Users\hunte\Hrns\hornlab-search`, branch `main`.
- Dossier snapshot of record `601be8c` (`601be8ceeb48f1750bb4f3f6c1fdc682967c8b94`), observed
  2026-11-16T20:43:51-05:00. At close the tree had advanced to `0750a30` (CROWE V2A timing-law fix):
  `git diff --stat 601be8c..0750a30` over every cited path is empty, so the dossier's citations
  remain valid.
- The checkout is **12 commits ahead of `origin/main = 2c0e2928…`**, the commit named by the v3
  handoff. Treat the handoff's file/line claims as historical and re-check against the local HEAD.
- A concurrent lane was committing and editing throughout (CROWE/KlangFilm geometry, GUI, objective
  v9). A Julia solve host and night queue were live. Nothing was touched.
- Evidence classes: source read at the snapshot; two NDJSON aggregations; one import of the pure
  `watchdog_verdict` function. **No GPU/BEM solve, mesher run, pytest, git mutation, queue edit,
  process signal or lock.** Historical report numbers are labelled as records, not measurements.

## Dossier artifacts (local, git-ignored `scratch/fable_architecture/`)

| File | Contents |
|---|---|
| `INDEX.md` | read-first index: findings, contradictions, six unranked routes, supervisor section |
| `SOURCE_INDEX.md` | paths, SHAs, SHA-256 hashes, run artifacts, method |
| `EVIDENCE_LEDGER.md` | 59 atomic status-labelled claims |
| `OPEN_QUESTIONS.md` | 10 architecture-changing questions, 7 cheap tests, original-thought items |
| `GEOMETRY_AND_PARAMETER_MAP.md` | constructions vs presets; parameter semantics; composition breaks; 5 representations |
| `FAILURE_AND_BOUNDARY_AUDIT.md` | refusal denominators; five boundaries; what optimizers learn |
| `SIZE_FEASIBILITY_EVIDENCE.md` | every envelope enforcement point; conservative grid estimate; cost curve |
| `OPTIMIZATION_AND_BRIEF_AUDIT.md` | v7 term-by-term; target precision; zero-GPU reuse matrix |
| `OPTIMIZER_AND_SWITCH_SECTION.md` | implemented vs documented optimizers; GP sharing; v4/v7 gates |
| `EXTERNAL_EVIDENCE.md` | 13 primary sources with transfer conditions and failure modes |
| `SEARCH_CONTROL_MAP.md` | runner flags/thresholds/queue/locks/idempotency/shadow seam |
| `WATCHDOG_REPLAY.md` | time-ordered replay of representative runs |
| `SWITCH_ADMISSION_MATRIX.md` | seven run states × next-policy admissibility |
| `SUPERVISOR_OPTIONS.md` | six supervisor options with evidence against each |
| `ADAPTIVE_UNKNOWNS.md` | seven decision-changing questions and falsifying tests |

## Highest-value findings

1. **The refusal taxonomy cannot be read as geometry vs envelope.** Post-mesh envelope violations
   return `invalid_geometry` (`search/evaluate.py:1580`), and a family error prefixed
   `"GeneratorError: invalid_envelope…"` fails the `startswith` test and also becomes geometry
   (`evaluate.py:1546`). The graded infeasibility penalty is therefore unreachable for native
   families (`:1046-1052`, `objective/terms.py:101-115`).
2. **On the current home brief the wall is envelope/geometry, not GPU.** 53 runs from 2026-11-16:
   2,538 attempts → 2,249 complete non-cached BEM solves (88.6 %), 81 pre-mesh `invalid_envelope`,
   169 `invalid_geometry` (26 of them post-mesh envelope), **zero** `mesh_too_large`/`solve_failed`/
   `metrics_failed`. The "694/2,728 (≈25 %) never reached the solver" figure is a historical
   2026-11-12 record from a lower DOF-cap era.
3. **The generic-GRID pre-mesh extent estimate is conservative, but realised false refusals are
   unmeasured.** `grid.envelope_extents` returns `W = H = 2(max_φ radius + wall)` for the generic
   radial route (`design/generators/grid.py:2989-3020`), so an asymmetric section's smaller axis is
   over-reported, and a positive estimate is a hard pre-mesh refusal (`design/generated.py:210-221`).
   Rows, generated-FREEFORM, family and CAD routes use per-plane methods. The exact CPU
   surface-vs-mesh check is specified in `SIZE_FEASIBILITY_EVIDENCE.md` §7 and was **not run**.
4. **Catalogue "diversity" is mostly names, carries and briefs.** The distinct engines are OSSE,
   R-OSSE, ICW, FREEFORM, the point-grid builder and CAD STEP. `spherical_wave` is
   `lecleach(T=1)`; `salmon_axisym` is `salmon_elliptical` with `fc=fc_h`; generator `osse` is
   native OSSE resampled; `native__ath_core_v4` vs `…2in_v5` differ only by brief/name.
5. **Composability stops before the meshed surface.** The generator emits exactly two cross-section
   stations (`design/generators/registry.py:315-332`); `morph_target` is a categorical forced into a
   rounded continuous box (`families.py:73`, `space.py:148-152`); ICW `termination` cannot be
   searched; an active guiding curve replaces `a_deg`; `search.links` refuses generator blocks
   (`search/links.py:36-37`), blocking the proposed coupling remedy for the families that need it.
6. **The objective is an exact point inside a stated owner range.** v7 is
   `J = Σ w_k raw_k/tol_k` over nine terms with only two local operators; the brief demands
   80 H × 50 V at every scored frequency while calling 80/50 the centre of **60–90 H / 40–60 V**
   (brief L8 vs L28-29). Flat DI is soft (tol 9); off-axis leakage outside coverage, true rear and
   arbitrary-plane smoothness are unscored; SPDI is report-only.
7. **A corridor objective (v9) is in flight and incomplete.** Untracked `objective/scalar_v9.py`
   (561 lines) implements frequency-dependent H/V coverage profiles, detrended DI roughness and an
   optional HF floor; `objective/versions.py` is modified to list 9. It imports
   `hornlab_search.targets.profile`, **which does not exist at the snapshot**, so v9 is not
   importable. The "goal regions" alternative is under active construction, not hypothetical.
8. **Reuse is response-anchored and identity-gated.** Objective/DSP re-scores are free only within
   stored frequencies and angles; geometry/source/symmetry/new-frequency changes need a solve. Two
   cohort gates disagree: `bo/cohort.py` refuses `objective_version != 4`; `bo/data.py` and
   production accept v7. The DSP rerank (v7 #1 → rank 12) is one run / 32 designs.
9. **Optimizer capability is narrower than the docs imply.** Five policies exist; only scalar,
   TuRBO and Pareto are production-executable; there is no in-run switch and a policy change
   invalidates the prepared package. Scalar BO is one `SingleTaskGP` over one frozen task; refusals
   are excluded from training; encoding is 1–20 continuous dims and refuses categorical/clipped
   rows; `n_min = max(16, 2(d+1))`, 4096-point pool, separate ≥100-row study floor. A prepared
   package can be unexecutable (18/155 pins differ; deadline past).
10. **The watchdog is a safety net, not a scientist.** `(not ok) or non-finite(J) or J >= 900` merges
    five outcome classes (`tools/run_campaign_night.py:166-168`); it never watches BO study/verify/
    cohort jobs; `pin_min_valid`/`pin_frac`/`pin_count` are hard-coded (only `pin_ignore` is public).
    Replay: 5/6 stops reproduce; a QD run would have been killed at row 25 but reached best 6.636
    and a 5/324 archive; two `no gain` stops discarded 2.4 %/4.7 % later gains; all 38
    watchdog-stopped summary rows have `best_J: null`.
11. **Live-reload is committed; idempotency is not durable.** Reorder/insert/remove, PAUSE/STOP,
    admission and per-process "finished IDs never rerun" exist and are tested; `queue.ps1:21-22`
    still documents the old read-once behaviour. `done` starts empty each run and
    `queue_state.json` is never read back, so a restart can double-run a finished job.
12. **No adaptive-policy claim is validated.** The historical BO-vs-CMA gap is confounded (BO: 185
    prior rows, pre-checked pool, 60/60/60 valid screens; CMA: one start, 31/44/46 valid, 14–29
    refusals). Every supervisor option has concrete evidence against it.

## Contradictions preserved

| Claim in circulation | Snapshot result |
|---|---|
| Handoff's `2c0e2928` describes the checkout | Local main is 12 commits ahead; a lane was still editing |
| `grid.py` is 2,813 lines | 3,020 lines; `envelope_extents` at L2989 |
| "25 % never reached the solver" is current | Historical 2026-11-12 record; 2026-11-16 is 88.6 % complete-BEM |
| BoTorch learns from refusals | False here: refusals are excluded from training |
| Graded penalty applies generally | Unreachable for native families |
| `queue.ps1`: a started night is read once | Contradicted by committed live-reload code/tests |
| "Nothing committed" for runner live-reload | Stale: all committed |
| BO supports v7 / refuses v7 | Both at different gates (`bo/data.py` vs `bo/cohort.py`) |
| CMA budget "including cache outcomes" | Cache hits are free; refusals consume budget |
| `flat` / `flat_cv` same dispersion | ddof=2 vs ddof=0, undocumented |
| FREEFORM refuses morph + non-elliptical | Search-layer policy, not a mesher refusal |

## Candidate routes (unranked, may combine, none preselected)

1. Minimal unification + truth fixes (classification, prefix bug, conservative estimator if Q1
   shows a loss, generator-aware links, v4/v7 gate split).
2. Hierarchical composable geometry grammar with declared `active_when` predicates.
3. Shared constrained body representation (freeform/point-grid + body graph) covering rollback,
   asymmetric and multi-entry surfaces.
4. Quality-diversity-first repertoire paired with a region objective.
5. Optimizer portfolio / adaptive supervisor — only after screen-J proxy validity is shown.
6. Separate over-envelope acoustic exploration — **not justified by current evidence**; no acoustic
   datum exists for any oversize design, and the estimator may explain part of the refusals. If ever
   studied: versioned brief, matched identities, re-optimization at the HF1440 throat, DOF ceiling,
   owner approval; a watchdog must never silently convert the production brief.

## Decisions that need Fable / owner judgement

- Is the dominant loss false refusal, valid oversize pruning, tight parameterization, a point
  objective that misstates intent, or unstable acoustic ranking?
- Is the deliverable a scalar winner, a feasible-region menu, a repertoire, or a reusable response
  dataset?
- Is a shared geometry representation worth its cost versus the cheap truth fixes?
- Should size be hard, soft, report-only, constrained or multiobjective?
- Is an adaptive supervisor premature while the objective is being revised (v9 in flight)?

Three zero-GPU tests would most change the decision: screen-vs-verify rank stability, held-out GP
ranking at 100–231 rows, and refusal-margin learnability. See `OPEN_QUESTIONS.md` in the local
dossier for the exact procedures and predeclared failure thresholds.

## v3 search-supervision addendum (summary)

Existing: committed search watchdog, committed live queue, read-only advisory. Missing: any policy
controller, BO-study observation, state migration between policies, common cost unit, or
equal-information experiment. Options compared with evidence against each: keep watchdog + reports;
shadow-mode advisor; bounded between-job controller; portfolio/racing; geometry/cost-aware design;
defer automation. The defensible default while score truth is contested is to keep the watchdog as a
safety net, keep the advisor read-only, do not auto-switch, and spend the next cheap work on
validity, data and objective quality.

## Compliance

No tracked file was modified by the research pass; this note is the only tracked artifact it adds.
No GPU/BEM solve, mesher run, pytest, git mutation, queue edit, process signal, threshold change or
lock occurred. Historical results are labelled as records; only the NDJSON aggregations and the
watchdog replay are reproductions.
