# PREDICTOR_AND_WORKFLOW — what the predictor is and how it would plug in

> **Results update, 2026-11-16 23:15.** Stricter tests weakened the predictor's case. X3: with a
> whole engine held out, horizontal-plane skill stayed below 0.6 and ranking inside an unseen lane
> fell to 0.49. E1: response curves gave no advantage over predicting the coverage-plus-DI proxy in the fixed-pool replay; full J was not tested. X5:
> lane racing saved nothing after corrections. Hook A (lane ordering) remains the only plausible
> use and is itself unconfirmed under sibling-excluded splits. Any replay must use the DI rule in
> `LOW_COST_AGENT_HANDOFF.md` §2; the scripts cited here predate that fix but use stored metrics,
> not regenerated ones.

> **NOTE ON AUTHORSHIP (2026-11-17, added by the lower-cost continuation lane agent).** The
> **lane note** at the end of this file was appended by the **lower-cost continuation agent** —
> **not by Fable (the senior/high-thinking reviewer) and not by the owner**. It is **not a gated
> decision**: it changes no pass line, threshold, split, frozen contract, brief, use-gate, or
> workflow decision recorded above, and the original text of this document — including the
> §11 "continue research, not deployment" decision — remains exactly as its senior author wrote
> it. Reader rule: where the original text and a lane note differ, the original governs intent;
> the lane note is evidence only.

**Written:** 2026-11-16. **Code read at** `main` @ `207f97a`. **Status:** historical explanation and proposal; the research corpus is now tracked.
The proposed predictor workflow is not established as implemented. Measurements are from stored runs
(scripts `.fable/an3.py`, `an5.py`, `an7.py`). This expands "Change 1" to "Change 3" of
`ARCHITECTURE_SYNTHESIS.md` §8.

---

## 1. In one paragraph

The predictor is a fast statistical model that looks at a horn's **shape** and estimates its
**response curves** (beamwidth against frequency in both planes, directivity index, and later
throat loading) without running a simulation. Its job is not to replace simulations. Its proposed job is to inform **which horns are worth simulating**: which family to start with, which starting shape to
give CMA-ES, and which candidates to skip. Every design that matters is still solved by the real
solver, and only solved results are ever reported as acoustics.

## 2. Hornfab already has two predictors. This is a third kind.

| | Existing: metric surrogate (`hornlab_search/surrogate/`) | Existing: `search.surrogate: lq` in CMA | Proposed: cross-family response predictor |
|---|---|---|---|
| Input | One lane's knob values | One run's knob values | Shape measurements taken from the surface (same for every family) |
| Output | Metric curves and a validity flag | The score J | Response curves; J is computed afterwards with the normal scorer |
| Learns from | One family's dataset | The current run only | Every solved horn of every family |
| Works for a brand-new lane | No: needs that lane's data first | No: starts empty each run | Intended use; strict generalization remains unverified |
| Scoring supported | Objective v1 only (`surrogate/capability.py`; kept v1-only by decision of 2026-11-13) | Whatever the run uses | Only objectives whose required predicted fields and compatible scoring semantics are available and validated |
| Model | Neural network ensemble (needs torch) | Linear-quadratic model inside pycma | Tree ensemble to start (scikit-learn, trains in seconds) |
| Wiring that exists | `surrogate train / propose / round` CLI; acceptance gates; proposals file solved through the normal path | Config key; CMA uses it internally | None yet; it can reuse the first column's proposals-and-round path |

**Reuse, do not rebuild.** The existing package already contains the two pieces that are hardest to
get right: acceptance gates (`surrogate/gates.py`) and a "proposals are only hypotheses until
solved" round that sends proposals through the normal evaluation path and compares them with a
random baseline (`surrogate/round.py`). The proposed predictor should feed that same path.

## 3. How the predictor works

**3.1 Training data.** One row per solved design: shape measurements in, response curves out. All
of it already exists under `runs/`. Today there are 3,414 valid rows on the home landscape brief
alone. A response belongs to the shape and the driver, not to the brief, so rows from every brief
with the same driver and source model can be pooled.

**3.2 Inputs (shape measurements).** The version I tested used 27 numbers read from each stored
mesh: depth, half-width, half-height, and the inner wall's distance from the axis at 12 depths in
the horizontal plane and 12 in the vertical plane. The intended version uses the fuller set in
`CANONICAL_SURFACE_CONTRACT.md` §7 (wall angles, section area and aspect along the wall, lip
radius), optionally expressed in wavelengths so one model covers all frequencies.

**3.3 Outputs.** Beamwidth in H and V and directivity index at each frequency. X3 subsequently tested stored throat resistance, in-coverage ripple and on-axis response retrospectively; transfer varied sharply by engine and target.

**3.4 From prediction to score.** The predicted curves are passed to the same scoring code that
scores real solves. A new objective can reuse predictions only if all required fields, frequency coverage and scoring conventions are supported; otherwise model or data changes and validation are needed.

**3.5 Knowing when not to trust it.** Two safeguards:
- *Distance check.* If a candidate's shape is farther from every training shape than almost all
  training shapes are from each other, the predictor returns "no prediction". The existing
  analysis tool already behaves this way ("no prediction (outside training support)").
- *Spread.* The ensemble's disagreement is reported with each prediction. It is a rough guide, not
  a calibrated uncertainty.

**3.6 Keeping it honest: the ledger.** Every time a predicted design is later solved, the pair
(predicted, solved) is appended to a ledger. The gates in §4 are recomputed from the ledger. If
they fail, the predictor is demoted to report-only automatically.

**3.7 Retraining.** After each night's runs finish: minutes of CPU, no GPU. The model file is a
scratch artifact keyed by the data snapshot it was trained on; it is not part of any design, solve
or score identity.

## 4. How good is it today, measured against the repo's own gates

The existing gates were written for a surrogate that *replaces* solves, and they are strict
(`surrogate/gates.py`): rank correlation ≥ 0.90, at least 12 of the true top 20 found, beamwidth
error ≤ 2.0°, DI error ≤ 0.3 dB, on ≥ 500 held-out designs.

| Measure | Gate for replacing a solve | Proposed predictor, lane never seen | Verdict |
|---|---|---|---|
| Beamwidth error | ≤ 2.0° | 4.0–4.5° | Fails |
| DI error | ≤ 0.3 dB | 0.4 dB | Fails |
| Rank correlation inside an unseen lane | ≥ 0.90 | 0.77 median | Fails |
| Ranking whole lanes against each other | (no gate) | 0.90–0.96 | Preliminary; siblings not excluded |
| Engine group never seen | (no gate) | Skill 0.18–0.71, error 8–16° | Weak |

**So the predictor must not be used to replace solves, and I am not proposing that.** It is
proposed only for *choosing what to solve*, which tolerates much larger errors because every choice
is checked by a real solve. That use needs its own, weaker gates:

| Use | Proposed gate (to be confirmed by experiment X3 and E1) |
|---|---|
| Ranking lanes | Rank correlation ≥ 0.8 against solved lane results, siblings excluded |
| Choosing starting shapes | Predictor's picks beat the usual starts in at least two thirds of lanes (see §6) |
| Skipping candidates | Of designs it would skip, fewer than 2 % turn out to be in the lane's top 10 % |

## 5. Where it plugs into the existing workflow

Today's workflow, and the five places the predictor could act. Each uses a hook that already
exists.

```
 owner writes brief + lane configs
        │
        ▼
 night queue (YAML, live-reloaded)  ◄── A. order and admit lanes
        │
        ▼
 per lane: CMA-ES search
   seed / warm start  ◄──────────────── B. choose the starting shape and step size
   loop:  ask → [candidates] ─────────── D. filter or add candidates inside the loop
             → mesh → solve → score → tell
        │
        ▼
 results (search.ndjson, designs/, dataset)
        │                          ▲
        ▼                          │
 retrain predictor (CPU) ──────────┘   C. a short "scouting round" of predictor picks,
                                          solved before CMA starts
        │
        ▼
 BoTorch study pool  ◄───────────────── E. rank the candidate pool
```

| Hook | What the predictor does | Existing mechanism it uses | What the owner sees | Risk |
|---|---|---|---|---|
| **A. Lane ordering** | Before a night, generate a few hundred shapes per lane on CPU, predict them, and rank lanes by their best predicted results | The night YAML is re-read before every job and supports reorder, insert and remove (`tools/run_campaign_night.py`, about lines 1232–1422) | A proposed job order with reasons; owner-requested lanes are never dropped | Low: only the order changes |
| **B. Start picking** | Choose CMA's starting shape and step size from the predictor's best candidates instead of a hand-written seed | `seed_params` in the config and `search.warm_start` (`hornlab_search/search/warmstart.py`); CMA reads the start at `search/cma.py:517-529` | A proposed config copy with a different seed | Low: CMA then runs exactly as now |
| **C. Scouting round** | Solve the predictor's top picks plus a few deliberately unusual ones, then start CMA from the best solved result | `proposals.json` solved through the normal path with a random baseline for comparison (`surrogate/round.py`, CLI `surrogate round`) | A short report: picks against random, all solved for real | Low to medium: spends 20–40 solves per lane before CMA |
| **D. In-loop filter** | Each generation, CMA proposes more candidates than will be solved; the predictor drops the worst-looking ones, or adds its own suggestions | CMA's ask/tell loop (`search/cma.py:859-920`) and `es.inject`, already used by the `lq` option (`:1076`) | A new search option, off by default | Highest: it steers the optimizer; a wrong model slows or misleads the search |
| **E. Pool ranking for BoTorch** | Rank or thin the candidate pool before the GP sees it, and supply a prior for a lane with few rows | The finite candidate pool (`hornlab_search/bo/data.py:1068`, `build_candidate_pool`) | A pre-ranked pool | Medium: interacts with the study package pins |

**What I would switch on first, and why.** Hook A only, as a written proposal the owner approves.
It is a candidate for further evaluation (§6); it leaves every optimizer untouched and only
changes the order of jobs. The existing lane-order measurement is not a validated deployment gate. Hooks B and C are cheap to wire but unproven: the replay in §6 could
not show the predictor choosing better designs than random picks. They should be tried next as a
small, approved experiment, not adopted. D and E change optimizer behaviour and should wait until
the ledger shows the predictor passing its gates for a sustained period.

## 6. Would it have helped? A replay on stored data **[measured]**

**Lane ordering (hook A): preliminary and unconfirmed.** Trained on other lanes, the predictor ranks lanes it has
never seen at rank correlation 0.90 (lane median) and 0.96 (lane best decile), and identifies 6 of
the true top 8 lanes (`.fable/an5.py`). Sibling lanes were *not* excluded in that run, so treat it
as an upper estimate.

**Choosing which designs to solve first (hooks B and C): not supported by this replay.**
For 19 constant-directivity lanes, with the lane *and its siblings* excluded from training, I
compared the best true J among three sets of eight designs (`.fable/an7.py`):

| Set of eight | Median gap to the lane's best J | Median rank within the lane (0 = best) |
|---|---|---|
| The eight earliest designs the run actually solved | 0.55 | 40th percentile |
| The predictor's top eight | 0.43 | 11th percentile |
| Eight drawn at random from the lane's solved designs | 0.30 | — |

The predictor's picks beat the earliest solves in 12 of 19 lanes, but beat random picks in only 9
of 19, which is a coin toss, and random was slightly better in the median. Beating the earliest
solves proves little, because anything chosen from the whole run beats its first rows.

Why this replay cannot settle the matter, in either direction:
- The designs available to choose from are the ones CMA-ES visited, which cluster near the lane's
  good region. A random draw from them is already a good design. In real use the predictor would
  choose from shapes spread across the whole range, where random picks are much worse.
- The predictor ranked by coverage only; J also contains loading, ripple and flatness.
- Only 70 designs per lane were sampled.

A fair test needs designs spread evenly across a lane's ranges with known results. The BoTorch
studies' initial Sobol rows are the nearest stored thing; otherwise it needs new solves. Until
then, **hooks B and C are unproven**, and one example cuts against them: for
`hl__osse_rrect_morph_v7` the predictor's best pick was J 6.95 where the run's early rows already
had 4.36.

## 7. A worked night, step by step (hooks A, B, C)

1. **Afternoon, CPU only.** Retrain the predictor on everything solved so far (minutes).
2. **Generate.** For each lane in tonight's plan, draw a few hundred shapes inside its ranges.
   Build each shape on the CPU. Discard any that break the size limit or throat fit; these would
   have been refusals during the run.
3. **Predict and score.** Predict response curves for the survivors and score them with tonight's
   objective. Mark any candidate that is outside the training data as "no prediction".
4. **Rank lanes (hook A).** Order lanes by their best predicted scores. Write the proposed order
   and the reasons. Owner-requested lanes stay in regardless.
5. **Pick starts (hook B) or scouts (hook C).** For each lane, write either a config copy seeded
   from the best predicted shape, or a proposals file with the top picks and a few unusual ones.
6. **Owner approves** the order and the proposed configs. Nothing runs without this step until the
   owner decides a hook has earned automatic use.
7. **Night, GPU.** Scouting rounds and CMA runs execute exactly as today. Every result is a real
   solve.
8. **Morning.** Append predicted-against-solved pairs to the ledger; recompute the gates; report
   whether the picks beat the usual starts.

## 8. What is needed before any of this can run

| Need | Why | State |
|---|---|---|
| Shape measurements for a candidate *before* it is solved | The tested version read them from stored meshes, which exist only after meshing | Either build the mesh without solving (seconds per candidate on CPU, fine for hundreds) or sample the surface directly (milliseconds, needs experiment X1) |
| Loading in the outputs | The score includes throat loading | X3 tested stored resistance retrospectively; held-out-engine results were mixed and do not validate a deployed predictor |
| Proof it survives stricter tests | Sibling lanes inflate the numbers | Experiments X3 and E1 |
| Trustworthy score differences | Choosing "better" candidates needs differences larger than the scoring noise | Scoring work R1–R4, with another agent |
| A proposals format that carries generator designs | The existing round validates `family` and `params`; grid and rolled designs carry a generator recipe | To check in X1 |

## 9. What could go wrong

- **It keeps choosing what it knows.** A model trained on existing horns prefers shapes like
  existing horns. The scouting round deliberately includes a few unusual picks for this reason.
- **It is confidently wrong about a new family.** Engine-level skill is weak. The distance check
  returns "no prediction" rather than a guess, and such lanes fall back to today's workflow.
- **It optimizes the predictable part of the score.** Coverage is predictable; ripple and fine
  flatness may not be. CMA on real solves remains the final judge.
- **Feedback loop.** If the predictor chooses its own future training data, it stops seeing
  evidence against its beliefs. Keep a fixed share of solves chosen at random or by plain CMA.

## 10. Brief for a lower-cost agent: P1, predictor replay for hooks A, B and C

**Question.** On stored data, would predictor-chosen lane order, starting shapes and scouting picks
have beaten what was actually done, with siblings excluded?

**Rules.** Read-only; no solve; mesh builds not needed. Write only under
`scratch/fable_architecture/`. Interpreter `.venv\Scripts\python.exe`.

**Sources.** `.fable/an3.py` (descriptor extraction and model), `.fable/an5.py` (lane ranking and
learning curves), `.fable/an7.py` (first-eight replay), `.fable/rows.pkl`; the sibling-lane rule in
`VALIDATION_EXPERIMENTS.md` (shared data section); gates in `hornlab_search/surrogate/gates.py`.

**Method.**
1. Rebuild descriptors for *all* valid rows, not a 70-per-lane sample.
2. Hook A: for each lane, train on all other construction groups; rank lanes by predicted best
   decile; compare with solved lane results. Report rank correlation and how many of the true top
   five lanes are in the predicted top five. Repeat with the lane's whole engine group excluded.
3. Hook B: for each lane compare the full-J of (a) the actual first solved design, (b) the
   predictor's top pick, (c) the median random design.
4. Hook C: compare best full-J among (a) the first 8, 16, 32 designs actually solved, (b) the
   predictor's top 8, 16, 32, (c) random 8, 16, 32, each then expressed as "how many further CMA
   rows did the real run need to reach that J".
5. Skip test: how many designs in the predictor's bottom half were in the lane's true top 10 %.
6. Repeat 2–5 using coverage-plus-DI only and using full J, to show what the missing loading
   prediction costs.
7. Fair-pool version of steps 3–5: find stored designs that were *not* chosen by an optimizer
   (the initial Sobol or pool rows of BoTorch studies under `runs/study-*` and
   `runs/bo_*`; list how many exist per lane). Repeat the comparison on those only. If fewer than
   30 such designs exist for a lane, say so; do not substitute optimizer-visited designs.

**Known result to reproduce first.** `.fable/an7.py`: predictor top-8 beats the earliest-8 in 12 of
19 lanes but random-8 in only 9 of 19; median gap to lane best 0.43 (predictor), 0.55 (earliest),
0.30 (random). Random draws come from designs the optimizer visited, which is why step 7 matters.

**Optional BEM stage (owner approval required, do not run).** For two lanes: generate 300 shapes
spread across the ranges on CPU; solve the predictor's top 10 and 10 chosen at random; 40 solves in
all. This is the only clean test of hooks B and C.

**Report (`P1_PREDICTOR_REPLAY.md`).** One table per hook; verdict against the proposed gates in
§4; the lanes where the predictor was worst and why (distance from training data).

**Do not** report any predicted value as an acoustic result, and do not tune the model after
looking at the held-out lanes.


## 11. Continuation decisions and evidence boundaries

**Decision now:** continue research, not deployment. A is a proposal for owner-reviewed ordering
only if its stricter replay is informative; the existing 0.90–0.96 lane ranking allowed sibling
information into training. B and C have not beaten a credible random baseline; D, E, automatic
pruning and allocation have no demonstrated justification. The gates in §4 are proposed decision
criteria, not measured guarantees. Fix the criteria and comparison protocol before inspecting held-out
results; a passing retrospective screen still needs an approved prospective test.

**Read the evidence at its actual scope.** E1 compared response and scalar models on a
coverage-plus-DI proxy in ten lanes using a fixed historical candidate pool: median 10 versus 9.5
valid-design reveals, with an eight-reveal initial floor. It excluded failed attempts and does not
measure GPU time or prospective CMA trajectories. The proxy-best row was in the full-J top decile
in only six lanes; full-J and term-level error remain open. E2's failed inverse recovered historical
geometry from two-plane profiles, with global PCA leaking unsupervised test-distribution information;
it does not rule out another geometry reaching a response target. E3's conservative bound saved
0.1% of frequency evaluations on stored rows, not wall-clock time; incremental response and cache
semantics are not established. None of these results validates a predictor-driven solver shortcut.

**Separate the three generalization questions.** X3's lane holdout, provisional sibling-group
holdout, and whole-engine holdout answer increasingly demanding questions and have different test
populations and training-mean baselines. Its two-plane input gave median within-lane coverage rank
0.761, 0.720, and 0.489 respectively; horizontal skill was below 0.6 for every held-out engine.
Additional stored loading, ripple and on-axis targets had mixed transfer. Training-only similarity
augmentation improved its paired retrospective baseline but still missed the H-plane line; it
assumes physical similarity and does not prove transfer with the same driver. Whole-surface and
explicit wavelength-scaled representations, complete construction/seed/warm-start lineage, and
solve-value estimates remain open. Do not infer that leakage alone explains poor transfer.

**P1 execution sequence.** First complete X1's provenance and surface validation (handoff A1),
then inventory available rows and construction ancestry. Reproduce the existing 19-lane result
before changing the model. Freeze family groupings, splits, metrics, budgets and random seeds; fit
preprocessing, feature selection, model and any augmentation on training folds only. Remove
matching design hashes and all known siblings before augmentation; report unresolved ancestry and
repeat under whole-engine holdout. Use identical candidate eligibility and solve budgets for
predictor, actual first rows and repeated random draws, with uncertainty and per-lane outcomes.
Historical optimizer-selected pools are biased; identify genuinely independent initial Sobol/pool
rows and report counts and provenance, leaving a lane untested if fewer than 30 qualify. Report
coverage-plus-DI separately from full J, hold frequency grid and objective fixed, and use the
parity-exact DI replay rule in the handoff. If required response fields or compatible scoring are
missing, mark full-J prediction unavailable rather than silently scoring a partial substitute.
Report both valid reveals and, where records permit, attempts including refusals and cache hits;
neither is an estimate of GPU time without measured cost.

**Governance and failure modes.** Model predictions and ensemble spread are hypotheses, not
solved acoustics or calibrated uncertainty. Distance rejection and ledger-based demotion in §3
are proposed safeguards requiring implementation and validation; they do not establish safety
outside training support. Preserve random or ordinary-search comparisons to detect feedback bias.
X5's corrected availability replay saved 0% in a non-discriminating case, and its counterfactual
default watchdog would have stopped the eventual winner before its best result; lineage and actual
overrides are incomplete. Keep watchdog decisions human-reviewed, never cut owner-requested
families, and do not change bounds, fidelity, queue or optimizer from these results. Any BEM test,
including P1's 40-solve proposal, requires owner approval; a prospective protocol should specify
matched budgets, baselines, protected families, measured cost, stopping and reporting beforehand.

---

> **Lane note, 2026-11-17 (lower-cost continuation agent; NOT a gated decision).** Hook A now
> also fails its stated line: rank correlation 0.733 against the lanes' best full J (line >= 0.8)
> and only 1 of the true top five lanes recovered (`P1_PREDICTOR_REPLAY.md`). Hooks B and C fail
> (pick beats first solve 11/19 against the 13/19 line; the scouting win belongs to the pool —
> random draws beat the predictor 10/12/10); the skip test fails at 8.9 % against < 2 %. The
> unbiased-pool gate fired: 0 strict unbiased designs exist in any study lane, so a fair-pool
> test is not runnable from stored data. The section-8 use-gates and the section-11 decision are
> unchanged; this note only records that the stored record resolves them negatively.
