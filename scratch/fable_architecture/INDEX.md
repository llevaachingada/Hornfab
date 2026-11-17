# Hornfab discovery architecture — evidence dossier (READ THIS FIRST)

> **Senior decisions and plan (2026-11-17), read these first now:**
> `FABLE_SENIOR_REVIEW_2026-11-17.md` (verdict on the lane review, the reserved generator and
> search decisions, corrections, owner decision cards) and
> `ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md` (target architecture, stages 0-8 with gates, GPU
> budget, and how each work package becomes an implementation task file). They take precedence
> over `LOW_COST_AGENT_HANDOFF.md` and every position document below; result files still outrank
> all position documents on facts.

> **Current navigation and evidence:** start with `LOW_COST_AGENT_HANDOFF.md` and the individual result reports. The dossier below records a historical snapshot, not current repository state. At observed HEAD `01560e5`, v9 and `targets/profile.py` are tracked and version 9 is registered; the snapshot finding that v9 was unimportable is historical. Concurrent report edits may be present. The experimental corpus was committed in `207f97a` and `01560e5`; reproduction scripts may overwrite tracked artifacts.

**Prepared:** 2026-11-16, read-only research pass. **Repo:** `C:\Users\hunte\Hrns\hornlab-search`
(canonical checkout). **Snapshot of record:** `main` @
`601be8ceeb48f1750bb4f3f6c1fdc682967c8b94`, observed 2026-11-16T20:43:51-05:00.
**`origin/main` is `2c0e2928…`; local main is 11 commits ahead of the handoff's snapshot.**
A concurrent lane was committing and editing throughout; a Julia solve and night queue were live.
Nothing was modified except this ignored `scratch/fable_architecture/` folder.

**Snapshot drift at dossier close (2026-11-16T20:46:32-05:00):** HEAD is now
`0750a3053875e9060e92af1a2b44f21a4efdc110` (one further commit, a CROWE V2A timing-law fix).
`git diff --stat 601be8c..0750a30` over **all cited paths** (`search/`, `bo/`, `targets/`,
`objective/`, the cited `design/` modules, `dataset/`, the runner, `tools/analysis/`, the home
brief) is empty, so every citation remains valid. Local main is now **12 commits ahead** of
`origin/main`. The snapshot of record stays `601be8c`; re-read the tree before acting.

**Provenance update (2026-11-16, after the research pass closed):** this whole folder — the **40
top-level reports** (the original 25 plus `UNIVERSAL_HORN_FAMILY.md`, `PREDICTOR_AND_WORKFLOW.md`,
`SCORING_RANGE_PROPOSAL.md`, `CORRIDOR_RERANK.md`, `SEED_SPREAD.md`, `S1_RANGE_SCORING.md`, the
`E1`/`E2`/`E2_LOCAL`/`E3` experiment records and `X1`-`X5`), `fable_zero_gpu_checks.py`, the
`.fable/` analysis helpers (`an1`-`an7.py`, `load.py`, `rows.pkl`, `desc.npz`), the `.tmp/`
recon/replay harness, and the per-experiment reproduction directories (`.e1`-`.e3`, `.s1`,
`.x1`-`.x5`, with their scripts, JSON/JSONL outputs and NPZ geometry) — is now **tracked on
`main`**, force-added past the repo's `/scratch/` ignore rule (only `__pycache__/` excluded). The
first batch (the original 25 reports) landed in `207f97a`; the remainder and the revised reports
landed in `01560e5`. The "ignored scratch folder / nothing modified outside it" statements
above describe the research pass itself and stay historically accurate; they no longer describe the
tree's tracking state. The committed copy is the working copy, byte-identical apart from the
bytecode exclusion.

**The question:** what representation of horn designs, design goals, feasibility constraints and
search process will discover more acoustically excellent, diverse, feasible horns per unit of
compute, while retaining the value of existing results?

**What this is not:** a final architecture. No route below is recommended. Every headline is
evidence with a status; interpretation is marked as such. Where the repository and the handoff
disagree, the repository at `601be8c` wins.

---

## Top findings (highest decision value first)

1. **The refusal taxonomy is not trustworthy as a geometry/envelope split.** A post-mesh envelope
   violation is returned as `invalid_geometry` (`search/evaluate.py:1580`), and a family
   `GeneratorError` whose text begins `"GeneratorError: invalid_envelope…"` fails the
   `startswith` test and is also coded geometry (`evaluate.py:1546`). Any statistic that counts
   `invalid_geometry` as "bad shape" over-counts geometry and under-counts the owner envelope.
   Consequence: the graded penalty is unreachable for native families
   (`evaluate.py:1046-1052`, `objective/terms.py:101-115`).

2. **On the current home brief the binding wall is envelope/geometry, not GPU.** Parsing 53 runs
   from 2026-11-16: 2,538 attempts → 2,249 complete non-cached BEM solves (88.6 %), 81 pre-mesh
   `invalid_envelope`, 169 `invalid_geometry` (26 of them actually post-mesh envelope), **zero**
   `mesh_too_large` / `solve_failed` / `metrics_failed`. The 2026-11-14 "694/2,728 ≈ 25 % never
   reached the solver" is a historical 2026-11-12 record from a lower DOF-cap era, not a current
   rate.

3. **The generic-GRID pre-mesh extent estimate is conservative on both axes, but realised false
   refusals are unmeasured.** `grid.envelope_extents` returns `W = H = 2(max_φ radius + wall)` for
   the generic radial route (`design/generators/grid.py:2989-3020`), so an asymmetric section's
   smaller axis is over-reported, and a positive estimate is a hard pre-mesh refusal
   (`design/generated.py:210-221`). Rows, generated-FREEFORM, family and CAD routes use per-plane
   methods. **No measurement in this pass shows that a refused candidate would have meshed.**

4. **Catalogue "diversity" is mostly names, carries and briefs, not engines.** The distinct
   engines are OSSE, R-OSSE, ICW, FREEFORM, the point-grid builder and CAD STEP. `spherical_wave`
   is `lecleach(T=1)`; `salmon_axisym` is `salmon_elliptical` with `fc=fc_h`; generator `osse` is
   native OSSE resampled; `native__ath_core_v4` vs `…2in_v5` differ only by brief/name. A master
   typology over these names would not add physics.

5. **Composability stops before the meshed surface.** The generator emits exactly two
   cross-section stations (`design/generators/registry.py:315-332`); arbitrary stations exist only
   in native FREEFORM. `morph_target` is a categorical forced into a rounded continuous box
   (`families.py:73`, `space.py:148-152`); ICW `termination` cannot be searched at all
   (`families.py:238-239`); an active guiding curve replaces `a_deg`
   (`profile_formulas.py:389-393`). `search.links` explicitly refuses generator blocks
   (`search/links.py:36-37`) — so the proposed "couple the knobs with links" remedy is unavailable
   for exactly the grid/rolled/KlangFilm families that need it.

6. **The objective is an exact point target inside a stated owner range.** v7 is
   `J = Σ w_k raw_k/tol_k` over nine scalar terms (`objective/scalar_v7.py:549-552`); the only
   local operators are the one-sided 8 kHz floor and the `load` window minimum. The brief demands
   80 H × 50 V at every scored frequency while its own comment says 80/50 is the centre of
   **60–90 H / 40–60 V** (brief L8 vs L28-29). Flat DI is soft (tol 9 ⇒ +5 dB/dec ≈ 2.78);
   off-axis leakage outside coverage, true rear energy and arbitrary-plane polar smoothness are
   unscored; SPDI/listening-window are report-only.

7. **A corridor objective (v9) is already in flight — but the snapshot is incomplete.** An
   untracked `objective/scalar_v9.py` (561 lines, dated 2026-11-17) implements frequency-dependent
   H/V coverage profiles, detrended DI roughness and an optional HF floor, and
   `objective/versions.py` is modified to list 9 as supported. It imports
   `hornlab_search.targets.profile`, **which does not exist in this snapshot**, so v9 is not
   importable today. The "goal regions" alternative is therefore under active construction, not
   hypothetical; do not evaluate it as a proposal only.

8. **Reuse is response-anchored and identity-gated.** `physical_solve_id` / `analysis_id` /
   `score_id` / `study_id` separate solve, metric, score and study (`dataset/identity_v2.py`).
   Objective and DSP re-scores are free within stored frequencies/angles; new geometry, source,
   symmetry or frequency support requires a solve. Two "cohort" gates disagree: the strict
   `bo/cohort.py` refuses `objective_version != 4`, while `bo/data.py` and production accept v7.
   The DSP rerank evidence is one run / 32 designs (v7 #1 → rank 12), a sensitivity demonstration,
   not a universal perceptual ranking.

9. **Optimizer capability is narrower than the documentation suggests.** Five policies exist;
   only scalar, TuRBO and Pareto are production-executable; there is **no in-run policy switch**,
   and changing the policy invalidates the prepared package. Scalar BO is one `SingleTaskGP` over
   one frozen task; refusals are excluded from training; no multi-task/cross-family sharing; no
   constraint output. Encoding is 1–20 **continuous** dims and refuses discrete/categorical keys
   and historical clipping. `n_min = max(16, 2(d+1))`, a 4096-point pool, and a separate ≥100-row
   study floor. A prepared package can be unexecutable: `bo_cov_s71001` has 18/155 code pins
   differing and an expired deadline.

10. **The watchdog is a safety net, not a scientist.** Its bad-outcome test is
    `(not ok) or non-finite(J) or J >= 900` (`tools/run_campaign_night.py:166-168`), merging five
    outcome classes that `search/outcomes.py` deliberately separates; it never watches BoTorch
    study, verify or cohort jobs (`:97-98`); `pin_min_valid`/`pin_frac`/`pin_count` are hard-coded
    and **not** public YAML (only `pin_ignore` is). Replaying it: 5/6 stop reasons reproduce
    exactly, but a QD run would have been killed at row 25 and in reality reached best 6.636 and a
    5/324 archive; two `no gain` stops discarded later gains of 2.4 % and 4.7 %. All 38
    watchdog-stopped summary rows have `best_J: null`.

11. **Live-reload and queue controls are committed and tested — and one doc contradicts them.**
    Reorder/insert/remove, PAUSE/STOP, admission and "finished IDs never rerun within the process"
    all exist (`run_campaign_night.py:1232-1422`, two test files). `queue.ps1:21-22` still says a
    started night is read once. **Idempotency is per-process only**: `done` starts empty and
    `queue_state.json` is never read back, so a restart can double-run a finished job.

12. **No adaptive-policy claim has been validated here.** The historical BO-vs-CMA gap is
    confounded (BO: 185 prior rows, size-pre-checked pool, 60/60/60 valid screens; CMA: one start,
    31/44/46 valid, 14–29 refusals). Every supervisor option has concrete evidence against it;
    the safest default while score truth is contested is: keep the watchdog as a safety net, keep
    the advisor read-only, do not auto-switch, and spend the next cheap work on validity, data and
    objective.

---

## Important contradictions and stale claims (preserved, not resolved by guessing)

| Claim in circulation | Status at `601be8c` |
|---|---|
| Handoff: remote main `2c0e2928` describes the checkout | Local main is 11 commits ahead; a live lane was still editing |
| `grid.py` is 2,813 lines | 3,020 lines; `envelope_extents` at L2989 (earlier count skipped blank lines) |
| "25 % never reached the solver" is current | Historical 2026-11-12 record; 2026-11-16 window is 88.6 % complete-BEM, 0 resource faults |
| BoTorch learns from refusals | False here: refusals are excluded from training |
| The graded infeasibility penalty applies generally | Unreachable for native families; generated-FREEFORM only |
| `queue.ps1` says a started night is read once | Contradicted by committed live-reload code and tests |
| "Nothing committed" for runner live-reload (HOME_18H) | Stale; all of it is committed |
| The BO stack supports v7 / refuses v7 | Both true at different gates (`bo/data.py` vs `bo/cohort.py`, `bo/metrics.py`) |
| CMA budget "including cache outcomes" | Cache hits are free (`budget_counts: new`); refusals consume budget |
| `flat` and `flat_cv` use the same dispersion | `flat` ddof=2, `flat_cv` ddof=0 — undocumented inconsistency |
| "FREEFORM refuses morph + non-elliptical section" | Search-layer policy, not a mesher refusal |

---

## Candidate architecture routes (unranked; may combine; none preselected)

1. **Minimal unification + truth fixes (control).** Keep the families; fix the envelope/geometry
   classification, the family-error prefix bug, the conservative grid estimate (if Q1 shows a
   realised loss), generator-aware `links`, and the v4/v7 cohort split. Cheapest; does not recover
   genuinely oversized designs or add new physics.
2. **Hierarchical composable geometry grammar.** Meridian/azimuth expression grammar with typed
   units and declared `active_when` predicates; dormancy becomes data instead of per-family
   tables. Expressive over H/V asymmetry, blends, splices, lips and folds; risks a DSL with silent
   no-ops and evaluation cost, and still cannot express a boolean multi-entry topology.
3. **Shared constrained body representation (freeform/point-grid + body graph).** One body model
   with declared throat, envelope, self-intersection and convexity constraints; families become
   initializers. The only route that naturally covers rollback, asymmetric/swept surfaces and
   multi-entry; loses published-family parameterization and needs new mesher/fork capability.
4. **Quality-diversity-first repertoire, paired with a region objective.** Treat the deliverable
   as a menu of coverage/ripple/size trade-offs rather than one scalar winner; needs a meaningful
   descriptor (the current default is achieved H/V beamwidth) and enough solves to populate an
   archive (existing evidence: 10/324 cells at 200 solves).
5. **Optimizer portfolio / adaptive supervisor.** Only after Q3–Q5 show screen-J is a stable
   proxy and equality-of-information experiments are affordable. Current code has no state
   migration between policies, packages are invalidated by policy changes, and arms are
   non-stationary with unequal valid-row budgets.
6. **Separate over-envelope acoustic exploration (include or rule out).** Not justified by current
   evidence: no acoustic datum exists for any oversize design; the code conservatism (finding 3)
   may explain some refusals and must be measured first; an exploratory campaign would need a new
   versioned brief, matched source/frequency/metric identities, re-optimization at the HF1440
   throat, a DOF/cost ceiling and owner approval. A watchdog must never silently convert the
   600 mm production brief into an oversize one. Fable may legitimately allocate **zero** GPU time
   to this.

**Decision levers the size evidence actually exposes:** (a) keep 600×480×480 and fix the
measurement; (b) widen the product envelope — an owner decision; (c) widen the search box only —
does not touch envelope refusals; (d) change the construction so the horn fits — needs
generator-aware coupling first.

---

## What Fable needs to decide (not what the dossier decides)

- Is the dominant loss **false refusal**, **valid oversize pruning**, **tight parameterization**,
  **a point objective that misstates the owner's region**, or **unstable acoustic ranking**? The
  evidence permits several; it does not rank them.
- Should the deliverable be a scalar winner, a feasible-region menu, a repertoire, or a dataset of
  reusable responses?
- Is a shared geometry representation worth its cost relative to the cheap truth fixes?
- Should size be hard, soft, report-only, constrained or multiobjective — and different by use case?
- Is an adaptive supervisor premature while the objective is under active revision (v9 in flight)?

**Open questions, cheap tests and the unchosen-counterfactual limits are in
`OPEN_QUESTIONS.md`.** The three zero-GPU tests that would most change the decision: screen-vs-
verify rank stability, held-out GP ranking at 100–231 rows, and refusal-margin learnability.

---

## v3: search supervision and experimental resource allocation

- **What exists:** a committed search watchdog (30 s poll; refusal-rate, no-gain, stall and
  bound-pin rules; exit 75; partial rows preserved), a committed live queue (reorder/insert/
  remove, PAUSE/STOP, admission, last-good YAML), and a read-only advisory
  (`tools/analysis/optimizer_switch.py`). It does **not** watch BO studies, and there is no policy
  controller.
- **What the replay shows:** 5/6 historical stops reproduce; the refusal rule would have killed a
  productive QD run at row 25; `no gain` stops discarded 2.4 % and 4.7 % later gains; the exact
  stop row is poll-timing dependent (±1–2 rows); archive state at the trigger is unknown.
- **What is missing for any switch:** no state migration (TuRBO trust state, Pareto metric
  observations, CMA warm start are different artifacts), no common cost unit (screen calls vs new
  candidates vs valid rows), packages invalidated by policy/pin changes, and no equal-information
  experiment.
- **Options compared:** keep watchdog + better reports; shadow-mode advisor; bounded between-job
  controller; portfolio/racing; geometry/cost-aware experiment design; defer automation. Evidence
  **against** each is in `SUPERVISOR_OPTIONS.md`; the switch gates are in
  `SWITCH_ADMISSION_MATRIX.md`; decision-changing unknowns are in `ADAPTIVE_UNKNOWNS.md`.
- **Bottom line:** the highest-return next spend is validity/data/objective work, not an
  auto-switcher. A supervisor, if built, should start as a read-only shadow with a predeclared
  decision rule and a held-out evaluation period.

---

## File map

| File | What it answers |
|---|---|
| `SOURCE_INDEX.md` | exact paths, SHAs, hashes, timestamps, run artifacts, method |
| `GEOMETRY_AND_PARAMETER_MAP.md` | families vs constructions vs presets; parameter semantics/units/activity/coupling; composition breaks; existing analyzers; five unranked representations |
| `FAILURE_AND_BOUNDARY_AUDIT.md` | refusal categories with denominators; five boundaries; classification; what optimizers learn; proposed (unrun) experiments |
| `SIZE_FEASIBILITY_EVIDENCE.md` | every envelope enforcement point by route; the conservative grid estimate; BO pool vs production; cost curve; size levers |
| `OPTIMIZATION_AND_BRIEF_AUDIT.md` | v7 term-by-term; target precision; goal-region alternatives; zero-GPU reuse matrix; rerank/QD evidence limits |
| `OPTIMIZER_AND_SWITCH_SECTION.md` | implemented vs documented optimizers; GP sharing rules; v4/v7 gates; TuRBO/Pareto/CMA/QD; unequal-information comparison |
| `EXTERNAL_EVIDENCE.md` | 13 primary sources with transfer conditions and failure modes |
| `SEARCH_CONTROL_MAP.md` | runner flags/thresholds/exclusions/resume/queue/locks/idempotency/shadow seam |
| `WATCHDOG_REPLAY.md` | time-ordered replay of representative runs; counterfactual limits |
| `SWITCH_ADMISSION_MATRIX.md` | seven run states × next-policy admissibility under strict eligibility |
| `SUPERVISOR_OPTIONS.md` | six options, evidence against each, simpler baseline |
| `ADAPTIVE_UNKNOWNS.md` | seven decision-changing questions + falsifying tests |
| `EVIDENCE_LEDGER.md` | 59 atomic status-labelled claims with counters and follow-ups |
| `OPEN_QUESTIONS.md` | prioritized gaps: architecture-changing, cheap tests, original-thought questions |
| `FABLE_DISCOVERY.md` | first Fable pass: broad discovery narrative |
| `FABLE_OPTIONS_REVIEW.md` | ranked reading of the candidate routes |
| `FABLE_RESEARCH_REQUESTS.md` | the exact research/experiment asks handed to the next pass |
| `ARCHITECTURE_SYNTHESIS.md` | combined architecture case + the plain-language guide to each suggested change (§8) |
| `ARCHITECTURE_DECISION_RECORD.md` | options, criteria and the record of what was decided (or deferred) |
| `CANONICAL_SURFACE_CONTRACT.md` | what a canonical horn surface record must carry |
| `UNIVERSAL_HORN_FAMILY.md` | what one parameterised universal family would be, could make, and whether to build it |
| `PREDICTOR_AND_WORKFLOW.md` | what the response predictor is and how it would plug into the search |
| `SCORING_RANGE_PROPOSAL.md` | acceptance ranges plus constancy as an objective alternative |
| `S1_RANGE_SCORING.md` | S1 replay over all 3,414 stored attempts: within-cohort v7 vs v9-plus-constancy top-20 overlap |
| `CORRIDOR_RERANK.md` | corridor re-rank of 3,414 ok rows from 75 landscape runs / 35 configs |
| `SEED_SPREAD.md` | seed-to-seed spread across the same 75 landscape runs |
| `FREQUENCY_BUDGET.md` | where the solve budget goes by frequency and what re-allocation would buy |
| `MESH_FIDELITY_PAIRS.md` | mesh-fidelity A/B pairs and what they can resolve |
| `VALIDATION_EXPERIMENTS.md` | full experiment briefs (E1–E3, X1–X5, S1, U1–U3) with decision rules |
| `LOW_COST_AGENT_HANDOFF.md` | handoff for a cheap agent picking the work up cold |
| `E1_RESPONSE_VS_SCORE.md` | E1: response-curve vs score targets — no advantage; cross-engine recall failed for GEN-FF |
| `E2_LOCAL_INVERTIBILITY.md` | E2 exploratory: stored-data local invertibility (superseded by the brief) |
| `E2_INVERTIBILITY.md` | E2 brief run: minimum-norm inverse fails the stated decision rule |
| `E3_FREQUENCY_STAGING.md` | E3: conservative partial replay of frequency staging |
| `X1_ROUND_TRIP.md` | X1: partial surface round trip, 50/60 designs sampled; Klangfilm reconstruction and contract remain open |
| `X1_CONTRACT_TESTS.md` | N1: six-lane contract tests (T1–T5) at the 65×31 record; two or more lanes fail inner-wall agreement, X1 failure condition met; U1 gated |
| `X2_AUTHORITY.md` | X2: module authority under held-out engines — not established |
| `X3_TRANSFER.md` | X3: partial strict transfer; tested H-plane skill below 0.6 for each held-out engine, with later target and augmentation results |
| `X4_PARAMETER_SPACE.md` | X4: five-lane exploratory parameter-space checks; sampler and classification gates remain open |
| `X5_ALLOCATION.md` | X5: corrected allocation replay — policy comparison degenerate at the stated target |
| `fable_zero_gpu_checks.py` | the zero-GPU reproduction checks named in the reports |
| `LANE_REVIEW_FOR_FABLE_2026-11-17.md` | lower-cost lane's corpus review handed to the senior reviewer |
| `X1_ACCEPTANCE_TABLE.md` | consolidated X1 per-test verdict (ruled by the senior review: accepted for geometry, open for metadata) |
| `OWNER_DECISIONS_2026-11-17.md` | owner options menu C1-C6 (options only) |
| `FABLE_SENIOR_REVIEW_2026-11-17.md` | **senior verdict**: confirm/amend/overrule table, corrections C-1..C-5, reserved decisions SD-1..SD-8, owner decision cards, supersession register |
| `ORCHESTRATOR_HANDOFF_2026-11-17.md` | **handoff for the local orchestrator**: rules, inventory, verification, stage-5 workflow, ordered tasks |
| `U3_RECORD_EDITS_CPU_2026-11-17.md` | U3 CPU stage on a biradial seed |
| `space_cards/` | parameter-space cards and `__space_v1` proposals for five lanes |
| `ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md` | **target architecture and staged plan**: layers, contracts, stages 0-8 with work packages and exit gates, GPU budget, invariants, task-file template and readiness |

## Tracked digest

The repository carries a condensed, tracked version of the original dossier at
`docs/research/FABLE_DISCOVERY_EVIDENCE_HANDOFF_2026-11-16.md`, committed as `3ad8b1d` and pushed to
`origin/main`; the curated 15-file copy and the v3 handoff text live in
`docs/research/fable_architecture_2026-11-16/`. **This folder is no longer git-ignored** — the full
corpus, harness and reproduction outputs are tracked on `main` (first batch `207f97a`, remainder in
`01560e5`), force-added past `/scratch/`; `__pycache__/` is the only exclusion.

## Safety / compliance

No tracked file, config, cache, queue or process was modified by the research pass; no GPU/BEM
solve, mesher run, pytest, process kill or lane lock occurred. Historical numbers are labelled as
records; only the stored-data replays and the watchdog replay are reproductions. The concurrent
lane's work was observed and preserved, never overwritten. **Tracking state changed after the pass
closed:** `.gitignore:9` (`/scratch/`) still ignores the folder by default, but this subtree was
force-added on owner instruction, so subsequent edits here now show up in `git status`.

## Local orchestrator pass (2026-11-17)

- `EVIDENCE_VERIFY_2026-11-17.md` - what the Windows checkout actually returned for handoff §2:
  tests, full-suite triage, U3 CPU tables, record-shadow counts, space-card batch and the 22 configs
  that could not be carded, with the source log/JSON named under each block.
- `space_cards/` - 29 lane cards + `shared_map.md` + `summary.json` (`--points 8 --box 96 --sigma-n 48`).
- `.evidence/verify_20261117/` - raw logs and JSON behind the note (`pytest_targeted.log`,
  `u3_cpu.json`, `record_shadow_recent/summary.json`, `space_cards_run/batch*.log`).
