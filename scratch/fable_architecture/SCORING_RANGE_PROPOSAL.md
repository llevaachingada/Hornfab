# SCORING_RANGE_PROPOSAL — acceptance ranges plus constancy

> **Results update, checked at HEAD `01560e5`.** S1 (`S1_RANGE_SCORING.md`) scored 3,414 stored
> attempts. Within each original-objective cohort, stored v7 and v9-plus-constancy shared 3 of the
> top 20 observations; the cohorts were not pooled for that comparison. Across the combined
> v9-plus-constancy sensitivity cases, 15–20 of the base top 20 remained. R3 used a different
> corridor and a common v7 baseline and found 4/20 overlap; its three onset choices had the same
> top-20 set. Neither study isolates the corridor effect from the changed term set. The v7
> screen/verify spread is not a validated noise floor for this proposed score. Owner choices of
> ranges and weights, same-term comparison (A9) and grid-independent scoring (A4) remain open.

**Written:** 2026-11-16. **Code read at** `main` @ `207f97a`. **Status:** proposal for the owner;
nothing is implemented or changed. The numbers in §4 are measured from stored runs with
`.fable/an6.py` (read-only, no solve). Starting values in §5 are placeholders for the owner to set.

## 1. The question

> Can each part of the score have an acceptable range, for example horizontal coverage anywhere
> from 60° to 80°, so that a horn scores best when it holds a *constant* pattern with little ripple,
> wherever inside that range it sits?

**Yes.** Half of it already exists in objective v9; the other half is a small, well-defined
addition. This note explains both, shows what the change does to the existing 3,414 designs, and
gives a brief a lower-cost agent can run.

## 2. What exists today

**Objective v7 (what the home searches use).** Coverage is scored against one exact point: 80° H
and 50° V at every frequency. A horn that holds a perfectly steady 70° is penalized as if it were
wrong. The "tolerance" numbers in the brief are *dividers* that set how much a term weighs. They
are not acceptance ranges: there is no zone inside which a term costs nothing.

**Objective v9 (committed, not yet used by any home brief).** In `corridor` mode the brief gives a
minimum and maximum beamwidth per plane, optionally changing with frequency. At each frequency the
cost is zero inside the range and grows with the square of the distance outside it; narrower than
the minimum is charged more than wider than the maximum
(`hornlab_search/objective/scalar_v9.py:331-374`). Ripple is measured inside the corridor width.
DI is scored for slope and for roughness about a straight line.

**The gap.** v9 checks each frequency on its own. A horn whose beamwidth swings from 60° to 80° and
back scores exactly the same on coverage as one that holds 70° throughout: both are "inside". The
only pressure toward steadiness is indirect, through the DI terms. So v9 gives you the range, but
not "constant within the range".

## 3. The proposed addition: range plus constancy

For each plane, over the scored band:

1. Take the horn's own average beamwidth, `level`.
2. Clamp it into the allowed range: `c* = min(max(level, lo), hi)`.
3. Cost = the mean squared distance of the beamwidth curve from `c*`.

In symbols: `cost = mean over f of (bw(f) − c*)² / 100`.

What this does:

| Horn behaviour | Cost |
|---|---|
| Steady 70° (inside 60–80) | Zero |
| Steady 62° or steady 78° | Zero: any level inside the range is equally good |
| Averages 70° but wanders ±8° | Charged for the wandering |
| Steady 55° (below the range) | Charged for being 5° outside |
| Averages 85° and wanders | Charged for both |

So the horn chooses its own level inside the range, and is judged on how well it holds it. This is
exactly "constant directivity anywhere between 60° and 80°".

**Design choices the owner needs to make.**

- **The ranges.** H 60–80° and V 40–60° are used below because they are the ranges written in the
  home brief's comment. They are placeholders.
- **Where vertical scoring starts.** No design in the 480 mm envelope holds vertical pattern below
  about 1 kHz. Scoring vertical from 700 Hz charges every horn for something none can do.
- **Strict constancy or smooth narrowing.** The formula above demands a flat line. If a gentle,
  steady narrowing toward high frequency is acceptable, replace "distance from a constant" with
  "distance from the best straight line whose slope is within an allowed limit". This is the same
  idea v9 already uses for DI.
- **Keep the per-frequency corridor too.** Recommended: keep v9's corridor as the hard edge (no
  frequency may leave the range without cost) and add the constancy cost as a new term. The two
  answer different questions.

## 4. What it does to the designs already solved **[measured]**

Coverage cost only, H 60–80° from 700 Hz, V 40–60°. Full J also includes loading, ripple and
on-axis terms, which are *not* in this comparison.

- **The gap in v9 is real.** 152 stored designs have horizontal beamwidth inside 60–80° at every
  scored frequency. A per-frequency corridor scores all of them zero in H. Of those, 129 swing by
  more than 10° across the band and 38 by more than 15°.
- **It changes which horns win.** Of the 50 best designs by v7's J, none are in the 50 best by
  range-plus-constancy coverage. The v7 winner (J 3.10) ranks about 395th of 3,414 on this cost: its
  horizontal beamwidth averages 71° but varies by ±6.5°.
- **A steadier horn already exists in the data.** With vertical scored from 1 kHz:

| Lane | H level and variation | V level and variation | v7 J |
|---|---|---|---|
| `hl__rosse_rect_cd_v7` | 75° ± 2.6° | 60° ± 2.5° | 5.29 |
| `hl__rosse_rect_cd_v7` | 73° ± 2.6° | 57° ± 3.1° | 5.24 |
| `hl__crowe_x_osse_cd_v7` | 75° ± 3.8° | 62° ± 3.3° | 6.02 |
| `hl__osse_rrect_morph_v7` | 62° ± 3.9° | 53° ± 4.8° | 5.60 |
| `hl__ext_throat_hvlaw_v7` (the v7 winning lane) | 69° ± 4.9° | 55° ± 4.4° | 3.90 |

  The steadiest designs were ranked well down under v7, partly because they sit at 75° rather than
  80° and partly on other terms. Whether they are better horns overall depends on those other terms
  (the `rosse_rect` designs had weaker loading), which is what the brief in §7 checks.

## 5. Ranges for the other parts of the score

The same idea, "free inside a range, charged outside", can be applied to every term. The general
form is a dead band:

`cost = max(0, value − free_limit) / scale`

| Term | What it measures | Today | With a dead band | Placeholder free limit |
|---|---|---|---|---|
| Coverage (H, V) | Beamwidth against target | Exact point (v7) or per-frequency corridor (v9) | Corridor plus constancy, §3 | H 60–80°, V 40–60° |
| Ripple | Unevenness across the listening window | Every 0.1 dB costs | Free below a threshold | 1.0 dB |
| DI roughness | Wiggle of DI about a straight line | Every 0.1 dB costs | Free below a threshold | 0.5 dB |
| DI slope | Rise of DI with frequency | Distance from one target slope | Free inside a slope range | 0 to +3 dB/decade |
| On-axis flatness | Deviation after a straight-line fit | Every 0.1 dB costs | Free below what equalization removes easily | 1.0 dB |
| Loading | Throat resistance at crossover | Already a dead band (free once resistance is high enough) | Unchanged | — |

**A warning about making everything a range.** If every term is free inside its range, many horns
score exactly zero and the optimizer has nothing to climb: the surface is flat. Three ways to avoid
that, in order of preference:

1. Keep one or two terms as true "less is better" measures (constancy and ripple are the natural
   ones), and turn the rest into ranges.
2. Treat the ranges as pass or fail gates and present every horn that passes as a menu, ranked by
   a quality the owner cares about (smallest, steadiest, best loading).
3. Add a very small preference toward the middle of each range, only to break ties.

## 6. How this fits the code and the architecture

- It needs a new objective version or a new, explicitly weighted term in v9. v9's rules were set by
  an owner-approved RFC (`docs/research/typologies/NON_CD_OBJECTIVE_PROFILE_RFC_2026-11-16.md`), so
  this is an amendment for the owner to approve, not a silent edit.
- Stored J values never change: a new term means a new score identity, and every stored response
  can be re-scored under it for free (`hornlab_search/objective/replay.py`).
- It strengthens the case in `ARCHITECTURE_SYNTHESIS.md` for modelling responses rather than J.
  The owner's intent is evidently "a set of acceptable horns, steadiest first". A model of the
  response curves can be re-scored under any such rule; a model of v7's J cannot.

## 7. Brief for a lower-cost agent: S1, range-plus-constancy replay

**Question.** Under a full objective with acceptance ranges and a constancy term, which stored
designs and lanes rank best, and how different is that from v7?

**Rules.** Read-only. No solve, no mesh build, no edits to tracked files. Write only under
`scratch/fable_architecture/`. Interpreter `.venv\Scripts\python.exe`.

**Sources.**
- Rows: `scratch/fable_architecture/.fable/rows.pkl` (rebuild with `.fable/load.py`).
- Starting script: `.fable/an6.py` (coverage costs only).
- Canonical re-scoring: `hornlab_search/objective/replay.py`; v9 scorer
  `hornlab_search/objective/scalar_v9.py`; profile schema `hornlab_search/targets/profile.py` and
  `tests/test_target_profile.py`.
- Per-design responses: `runs/<run>/designs/<hash>/response.npz`.

**Method.**
1. Write a scratch brief (not under `examples/`) using v9 corridor mode with H 60–80° from 700 Hz
   and V 40–60° from 1,000 Hz. Re-score every valid row with the real v9 scorer.
2. Compute the constancy cost of §3 for each plane from the stored beamwidth curves, in both the
   strict form and the "straight line with slope limit" form.
3. Form three totals: v7 J as stored; v9 corridor; v9 corridor plus constancy (weight 1, divider
   chosen so that a ±5° variation costs about the same as 1 dB of ripple; state the value used).
4. Repeat step 3 with the dead bands of §5 applied to ripple, DI roughness and flatness.

**Report (`S1_RANGE_SCORING.md`).**
- Top 20 designs under each total, with level and variation per plane, ripple, loading term, lane.
- Overlap of the top 20 and top 100 between totals; rank correlation.
- Best design per lane under each total, and lanes whose position changes by more than three.
- How many designs tie at zero when all dead bands are on.
- Sensitivity: repeat with ranges shifted by ±5° and the vertical start at 700 and 1,250 Hz.

**Pass lines.** None: this is a description for the owner. State plainly which conclusions hold
across the sensitivity cases and which do not.

**Do not** tune ranges or weights to make a particular horn win, and do not recommend a winner.
The roughly 0.17 J screen/verify spread was measured for a different score. The noise floor of
this proposed score is not established; small ranking differences require a separate fidelity study.

## 8. Continuation: evidence, replay and decisions

This section is a reading and execution guide for the next agent. The results above are retrospective
observations, not a selected horn, an approved objective, or proof that a proposed scoring change
will improve a future search. In particular, the statement in §3 about vertical performance is an
observation of the sampled designs, not a physical impossibility claim for every geometry in the
envelope. The §4 comparison is coverage-only and cannot establish an overall winner.

### What the evidence does and does not distinguish

- S1's 3/20 overlaps compare stored v7 with v9 plus constancy **within each original-objective
  cohort**; its combined sensitivity table compares variants of that new scratch score. Its
  ±5° and onset experiments do not establish robustness outside those tested choices. The
  constancy term and corridor can both charge an out-of-range curve.
- R3 applies a common v7 brief and a different placeholder corridor to all eligible observations.
  Its 4/20 result and unchanged top-20 set across the three onsets describe that experiment. Both
  R3 and S1 change several terms at once, including ripple semantics; neither measures the
  independent effect of the corridor. Compare ranks, not numerical J across score identities.
- R1 has only two low-J pairs and confounded solve conditions. Screen and verify share a mesh.
  R2's 22-point result is relative to an interpolated baseline, not independently solved truth;
  interpolation alone changed the score. Neither establishes the proposed score's noise floor,
  mesh convergence, an accepted frequency budget, or the significance of a close rank gap.

### Replay contract

Use the same response and target identity, frequency support, row inclusion and tie rule for each
paired comparison. Retain run plus design identity: repeated hashes across runs can carry distinct
responses. Record exclusions and missing fields. Stored DI is the sin-theta-weighted balloon DI
used by `search/evaluate.metrics_from_response`; plain `compute_metrics` regeneration is not
parity-equivalent. For v7 start with `.tmp/fable_replay_harness.py`, which matched stored J on its
116-row check. V9 is not dispatched by `objective/replay.py`: call the v9 scorer explicitly, as
`.s1/replay.py` does. S1 corrected the DI-dependent contributions from stored DI and checked the
adjustment on sampled rows; its three beamwidth checks are not a complete parity audit. Validate
new harnesses against stored scores where applicable and independently check v9 component values.
Record objective version, full profile, weights, frequency grid, DI provenance and script revision
with every output. A new scoring rule requires a new identity; do not overwrite historical J.

### Independent scratch work: A4 and A9

**A4 — grid dependence.** Reproduce the R2 parity baseline first. In scratch, define each v7 and
v9 frequency-dependent term as an explicitly normalized weighted integral over log frequency,
including band boundaries and the existing weights; document how fits, extrema and non-integral
terms are handled rather than assuming they integrate unchanged. Compare old and proposed
per-term contributions on the same responses, then repeat the R2 point-count experiment with the
same subsets and interpolant. Report bias, spread, rank effects and the count reaching the stated
0.10 J SD criterion *against that interpolated reference*, separately by term and total. Check
sensitivity to interpolation and band edges; flag any term that cannot be consistently redefined.
This is a numerical stability experiment, not a physical convergence test or permission to change
production scoring. See `FREQUENCY_BUDGET.md` for the precise historical baseline.

**A9 — isolate point versus corridor.** Use the same eligible rows, stored responses and v9
configuration in both arms; change only coverage mode and the necessary point/corridor parameters.
Fix and document the ripple window explicitly if mode changes its semantics; if the scorer cannot
hold it fixed, report a controlled scratch decomposition or disclose the residual confound rather
than calling the comparison isolated. Do not add constancy in one arm only. Predeclare point target,
corridor, onsets, frequency weighting and tie handling, and report per-term deltas, top-20 and
top-100 overlaps, rank correlation, inclusion counts and exclusions. A second sensitivity case may
show dependence on the chosen corridor but must remain separate from the primary comparison. See
`CORRIDOR_RERANK.md` and S1 for the prior, differently configured comparisons.

Both tasks are CPU-only, read-only with respect to source, configs, queues, examples and runs;
write artifacts only in `scratch/fable_architecture/`, and preserve existing scripts and outputs.
They can run independently. Neither authorizes solves or a production scoring amendment.

### Owner decisions before an implementation brief

Confirm H and V ranges and their frequency dependence; vertical onset and below-onset behavior;
flat constancy versus permitted slope and its bound; whether corridor and constancy both penalize
excursions; term weights, normalization and any dead bands; and whether the deliverable is one
winner or a menu. The example values in §§3–5 and S1 are placeholders. Decide how diagonal
coverage and ripple-window semantics express the listening intent. The implementation plan should
identify the objective version and validation criteria only after these decisions and A4/A9; mesh
and frequency fidelity for finalists require a separately approved matched study (handoff B1).
