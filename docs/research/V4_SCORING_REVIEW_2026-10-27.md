# Objective v4 scoring review - 2026-10-27

What else should change in J before v4 ships, with numbers recomputed offline from stored records.
No GPU was run. Provenance tags: **[M]** measured from stored data this pass, **[D]** derived/recomputed
offline, **[E]** estimate/judgement. The "could not verify" list is section 9.

Basis: `docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md`, `docs/IMPLEMENTATION_PLAN_2026-10-27.md` §3,
`docs/research/V4_TOLERANCE_RESEARCH_2026-10-27.md` (orchestrator; its numbers are [E] proposals, tested here),
and the scorer code (`objective/scalar_v2.py`, `objective/terms.py`, `metrics/*.py`), all read 2026-10-27.
Companion tolerance tables: `docs/evidence/OBJECTIVE_V4_TOLERANCES.md`. Analysis scripts:
`scratch/v4_review/` (read-only; reproduce with `.venv\Scripts\python.exe`).

## 0. What I could reconstruct, and the fidelity check

The v4 plan's claim that J is recomputable offline is **confirmed and exact** [M]. Every ok record stores the
73-point H/V cuts, the 512-point balloon + directions, `z_throat`, and the six metric curves
(`dataset/record.py` ARRAY_KEYS). Rebuilding a `Response`+`MetricSet`+`Target` and calling the installed
`objective_v3` reproduces the stored `objective` to **max |err| 2.8e-14** across all 50 ok v3 records
(`scratch/v4_review/load_v3.py`). Per-config weights were recovered by least squares from the stored
`(terms, total)` pairs (residual < 1e-14) and agree with the briefs: `native__lecleach_rollback` =
cov 0.3 / rip 1 / di 0.3 / dislope 0 / flat 0.5 / load 0.5; the rest = contract defaults.

**The data available is thin and must be stated up front** [M]:
- The smoke night wrote **no dataset records** (the v3 rejection bug), so its per-evaluation rows with raw
  arrays are gone. Only **54 v3 records exist (50 ok)**, across three configs: `native__lecleach_rollback`
  (43), `crease__core_law` (5), `gcurve__osse_b1w` (2). Diagonal/asymmetric-coverage analysis, which needs raw
  balloons, is limited to these.
- The smoke-night **search trajectories survived** in `runs/<ts>-screen-*/search.ndjson` (params + `terms` +
  objective per eval), and ~130 older runs have the same. Term-only recomputation (which is all v4
  normalisation needs) therefore runs over **100+ cells**; this is the basis for the rank-correlation work
  (section 3). It cannot recompute the *raw* cov/diagonal terms (no arrays), only re-weight the stored ones.

## 1. Top 5 findings

1. **Normalisation is not cosmetic - it changes the winner.** Over 100+ stored search cells, v3 vs
   v4-with-physical-tolerances has a high *global* rank correlation (median Spearman ~0.93) but the
   **argmin (the design the search would pick) changes in ~40 % of cells, and top-5 overlap is routinely
   0-3 of 5** [M]. On the loading briefs it collapses outright: `native__lecleach_rollback` Spearman **0.10**
   (n=74) and **-0.01** on the 43 dataset records, top-5 overlap **0/5**; `lecleach_rollback` (older, n=130)
   Spearman **0.34**. The choice of tolerances is a real decision, concentrated exactly where we care (the
   top few) and worst on the briefs where terms are balanced. v4 is worth doing, and the tolerances must be
   chosen, not defaulted.

2. **The six-term normalisation the plan describes is necessary but not sufficient; the highest-value
   additions are a DI-constancy term and a presence-band narrow-coverage penalty.** `dislope` (a single
   slope number) and DI standard deviation are nearly independent on the stored data (Spearman between them
   **-0.37** on lecleach, **+0.90** on crease) [M] - they measure different things, confirming Princeton S1.
   And the band the owner calls most audible (2.5-5.5 kHz) is only **3 of 12 screen points** [M]; adding a
   narrow-side penalty there reshuffles the loading-brief ranking (top-5 overlap drops to 1/5) [M].

3. **The balloon already drives J heavily - but only as a scalar DI, never as shape.** Balloon-derived terms
   (`di`+`dislope`) carry **9 % (lecleach) to 77 % (crease__core_law)** of J [D]. So "the polar data counts"
   is true via DI; but a creased pattern and a smooth pattern with the *same* DI score identically, so the
   diagonal/45-135 *shape* is invisible. `cov` and `rip` are H/V-cut only. A diagonal term is the only thing
   that reads the shape the crease/pucker classes exist to make.

4. **Data-driven tolerances can break penalty ordering; physical tolerances do not.** With a tolerance set to
   the median raw term and floored at 1e-3, the worst plausible *valid* v4 J (all terms at `NAN_TERM_FILL`=30)
   reaches **1572 on lecleach - above `PENALTY_INVALID`=1000**, because `load`/`rip` medians are ~0 [D]. An
   invalid design would then outrank a valid-but-unmeasurable one: a correctness bug, not a tuning choice.
   Physical tolerances keep the worst valid J at **79-117** [D]. Any data-driven tolerance needs a physical
   floor, and the penalty-ordering test (plan 3f) must run per brief, not once.

5. **Widening the parameter boxes will not cut the 33 % refusal rate - that is dominated by
   `invalid_geometry` (89 of 124), a geometry-law limit, not a box edge.** Only 26 refusals were envelope and
   9 mesh-too-large. The real box problems are the opposite: a handful of knobs rail hard (section 6), and one
   seed was simply unreachable (`gcurve`, now fixed). The widening table (appendix) is about *reaching better
   designs*, not about refusals.

## 2. What the score contains today, and the per-term reality

The six terms (`objective/terms.py`), with their measured weighted share of J on the three v3 cells [M]
(scripts: `scratch/v4_review/analyze.py` A):

| cell (weights) | cov | rip | di | dislope | flat | load | dominant |
|---|---|---|---|---|---|---|---|
| `crease__core_law` (defaults) | 15 % | 1 % | 2 % | **75 %** | 7 % | 0 % | dislope (max 91 %) |
| `native__lecleach_rollback` (cov.3/load.5/dsl0) | 44 % | 0.4 % | 9 % | 0 % | **45 %** | **1.8 %** | flat/cov tie |
| `gcurve__osse_b1w` (defaults) | **55 %** | 2 % | 3 % | 19 % | 22 % | 0 % | cov |

This reproduces the smoke report's two findings independently: single-term domination, and the **load
experiment failing at 1.8 %** despite weight 0.5. The cause is raw scale: per-config median raw terms span
`rip` 0.02-0.14, `di` 0.76-1.7, `cov` 2-8, `flat` 1.3-5.2, `dislope` **20-57** [M] - a **150x-2800x** spread
at nominally comparable weights. Normalisation (divide each term by a tolerance) is the right fix and the
plan's design (`J = sum w_i term_i / tol_i`, tolerances in the brief) is sound.

### Frequency-grid reality [M]
Screen grid = **12 log-spaced points, 500-8000 Hz** (`[500, 643, 828, 1065, 1370, 1763, 2269, 2919, 3756,
4832, 6218, 8000]`). The v3 f0 mask removes cov+dislope below f0, so on these cells **cov_h is scored on
8-9 of 12 points, cov_v on 7-8**; `rip`/`di`/`flat` use all 12. The three sub-f0 points (500/643/828) carry
only rip/di/flat. The 300 Hz band floor in the briefs is never exercised on screen (grid starts at 500) - it
is a verify-only promise, as the smoke report said.

## 3. Candidate terms - what each measures, computability, scoring effect, recommendation

| Candidate | Measures | Computable from stored data? | Effect on stored designs | Recommend |
|---|---|---|---|---|
| **Diagonal 45/135 vs intended** | pattern shape off the H/V planes | **Yes** from the balloon [M] | measurable; rank effect unverifiable (see §9) | **Include**, option (b), owner picks the intended-diagonal reference |
| **DI standard deviation** | directivity *constancy* (not slope) | Yes (di_db curve) [M] | independent of dislope (ρ -0.37..+0.90) | **Include** as supplement to / replacement of dislope |
| **Presence-band narrow penalty (2.5-5.5 kHz)** | the audible mid narrowing | Yes [M] | reshuffles loading cells (top5 1/5) | **Include** as a brief-set `freq_weights` + asymmetric cov, not a new term |
| **Asymmetric coverage (narrow > wide)** | "do not be beamy" | Yes [M] | raises cov 24-73 %; class-dependent | **Include**, class-gated (off for loading) |
| **beam_shape.py superellipse p** | square-vs-round mouth footprint | function exists but **not wired into `compute_metrics`** (not in SCALAR_KEYS) [M] | not computed in-pipeline | **Defer** to finalist report; diagnostic only (its own docstring says so) |
| **spinorama LW / SPDI** | in-room preference proxy | standalone, **not computed in-pipeline** [M] | n/a | **Defer**; room-listening, not PA coverage (S2 caveat) |
| **n_multilobe_h/v** | HOM / lobing proxy | **already computed, unscored** (`metrics/compute.py`) [M] | free to add | **Consider** a cheap guard term (count of lobed frequencies) |
| **f_break / f11** | design-check frequencies | already in scalars, unscored [M] | diagnostic | **Keep diagnostic**; already in the feasibility record |
| **Impedance ripple** | throat loading smoothness | z_throat stored [M] | load term already uses Re(z) | **Defer**; the load term is the loading channel |
| **Time-domain / ringing** | stored energy / HOM audibility | needs a dense uniform resolve | n/a | **Defer to finalist stage** - I agree with `TIME_DOMAIN_RINGING.md` |

**Time-domain, explicitly:** I agree it is finalist-stage, not in-loop. It is ~20x a screen eval, the screen
grid is 12 log points (useless for a waterfall), and a scalar "ringing" number is unvalidated. Nothing
in-loop is worth having here; the cheap frequency-domain proxies (DI std, multilobe count) capture the part
of "ringing" that correlates with HOM without a transient solve.

### 3a. Diagonal term - the reference choice is the whole decision [M/D]
Measured from the stored balloon (`scratch/v4_review/analyze.py` E), band-mean 45/135 beamwidth vs H/V:

| cell | target | measured diag45 / 135 | bw_h / bw_v | separable-diag ref | round ref (mean HV) |
|---|---|---|---|---|---|
| `crease__core_law` | 50x50 | 58 / 58 | 60 / 60 | 36.5 | 50 |
| `gcurve__osse_b1w` | 90x60 | 87 / 87 | 90 / 88 | 53.1 | 75 |
| `native__lecleach_rollback` | 90x90 | 95 / 95 | 110 / 110 | 70.5 | 90 |

The owner's lean to option (b) "diagonal vs intended coverage" is right, **but "intended" has two defensible
definitions that penalise in opposite directions** [D]:
- **Separable reference** (what a perfect independent-H/V waveguide gives, 36-71 deg): every real design's
  diagonal is *wider* than this, so it penalises all of them and rewards a pinched/rhombus diagonal - the
  *opposite* of even coverage.
- **Round reference** (mean of H/V, i.e. "same angle in every azimuth", 50-90 deg): rewards a diagonal that
  matches the planes - even angular coverage, which is the owner's stated priority.

Recommendation: use the **round reference** (target_diag = f(cov_h, cov_v), e.g. the mean, or the ellipse
radius at 45 deg), penalise `(measured_diag - target_diag)^2` with its own tolerance, and - per the owner's
note that option (a) would punish the crease shapes - do **not** penalise diagonal-vs-H/V *consistency*.
This is a config/term design choice; the owner picks the reference. This cannot be ranked on stored data
because the one asymmetric-diagonal cell (`crease__osse_b1w`) has no stored balloon (§9).

## 4. Hypothesis tests from the tolerance-research note (its numbers were [E]; these are [M])

- **H1 asymmetric coverage (narrow penalised 2x wide):** raises the cov term by **24 % (crease) to 73 %
  (lecleach)** [M]; 61 % of lecleach's in-band samples are narrower than target. **Survives, class-gated:**
  correct for CD/waveguide briefs ("do not be beamy") but wrong for a loading brief where narrowing *is* the
  design - exactly the class split the note proposes. Do not apply it globally.
- **H2 one-sided cov below f0 (narrow everywhere, wide free below f0):** gives a lower, better-behaved cov
  than the v3 hard mask while still scoring low-frequency beaming [M]. **Survives** for the low-reach PA
  class; cheap (a sign test in the cov term). It recovers information the v3 mask throws away (a horn that
  beams *below* f0 is a real defect; a horn that is *wide* below f0 is physics).
- **H3 DI std vs dislope:** DI std = 1.8-3.5 dB on the stored cells; its Spearman with `dislope` is -0.37
  (lecleach) / +0.90 (crease) [M]. **Survives** - they are not redundant. On lecleach, where dislope is
  weighted 0, DI still wobbles 3.5 dB and v3 scores none of it; DI std would. Recommend adding DI std
  (optionally alongside dislope, each with a tolerance).
- **H4 presence band 2.5-5.5 kHz:** exactly **3 of 12 screen points** (2919/3756/4832 Hz), matching the
  owner's estimate [M]. Those designs *do* narrow there (lecleach mean deficit 10.6 deg) [M], and a
  narrow-side penalty over that band changes the ranking (Spearman 0.50, top-5 overlap 1/5) [M].
  **Survives.** Cheapest implementation is a brief `freq_weights` emphasis on 2.5-5.5 kHz plus the H1
  asymmetric cov, not a new term. A denser grid there (section 8) would sharpen it; cost below.
- **Class-specific tolerance blocks:** supported - see the per-class share tables in
  `OBJECTIVE_V4_TOLERANCES.md`. A global default tolerance is wrong (finding 1).

## 5. Ranked recommendation for v4

**Include now (in the first v4):**
1. **Per-term normalisation with tolerances in the brief** - the plan's core. Cost: ~the plan's estimate.
   Risk: penalty ordering (finding 4) - mitigate with a physical tolerance floor and a per-brief ordering test.
2. **Class-specific tolerance blocks** (CD waveguide / loading-rollback / low-reach PA), never a global
   default. Cost: config only. Risk: low.
3. **Asymmetric coverage error**, class-gated (narrow side ~2x, off for loading). Cost: ~10 lines in the cov
   term + a brief flag. Risk: low; it is a reshaping of an existing term.
4. **DI standard deviation** term (supplement to or, on flat-slope briefs, replacement of dislope). Cost:
   one metric (std of the existing di_db band) + a tolerance. Risk: low; independent signal, bounded.

**Include if cheap, else fast-follow:**
5. **Diagonal 45/135 term** (option b, round reference), computed from the stored balloon. Cost: a metric +
   a reference function + a tolerance (~40 lines). Risk: medium - the reference choice (section 3a) and it
   cannot be rank-validated until the T3 balloons run. It needs no new solves for *existing* ballooned
   records but the screen path must keep storing the balloon (it does).
6. **Presence-band `freq_weights`** emphasis (2.5-5.5 kHz) in the CD/PA brief set. Cost: config. Risk: low.

**Defer:**
7. beam_shape `p`, spinorama LW/SPDI, impedance ripple, time-domain ringing - all finalist-stage report
   metrics, not in-loop. Wire beam_shape/spinorama into the finalist report, not the objective.
8. `n_multilobe` as a scored guard - plausible but unneeded if the diagonal + DI-std terms land; revisit
   if lobing survives them.

**Drop:** nothing from the current six. `dislope` stays but is demoted where DI std covers it (keep both on
briefs that want a specific DI tilt; the Le Cleac'h class already sets dislope 0).

## 6. Owner decisions required

1. **The tolerance set** (per class), from the two options in `OBJECTIVE_V4_TOLERANCES.md`. This changes the
   winner (finding 1) - it is the single most consequential choice.
2. **Diagonal reference** for option (b): separable vs round vs ellipse-at-45. I recommend round. (Section 3a.)
3. **Whether DI std replaces or supplements dislope**, per class.
4. **Asymmetric-cov ratio** (e.g. 2:1 narrow:wide) and which classes it applies to.
5. **Whether the presence band gets a denser grid** (section 8) or just a `freq_weights` emphasis.
6. **The box-widening table** (appendix) - owner-gated per config, never applied here.

## 7. Tolerance proposal

Two fully-worked options with weighted-share tables and the penalty-ordering check are in
`docs/evidence/OBJECTIVE_V4_TOLERANCES.md`. Summary: **Option A (physical)** keeps penalty ordering and
spreads the share sensibly; **Option B (data-median)** equalises shares best but breaks penalty ordering
for near-zero terms unless floored. Recommendation: **Option A with per-class blocks**, floors from the
solver noise anchors (DI 0.3 dB, beamwidth 2 deg).

## 8. Grid-density note (owner H4 (c): is a denser grid needed in 2.5-5.5 kHz?)

The screen grid puts **3 of 12 points** in 2.5-5.5 kHz [M]. Because the smoke night established that inside
one frequency **assembly is 73-96 % of the cost and is paid per frequency** (one eval ~ n_freq x
assembly(dofs)), grid cost is **linear in point count** [M, smoke report §2]. Adding 3-4 points in
2.5-5.5 kHz raises the screen grid from 12 to 15-16 points, i.e. **+25-33 % screen GPU time** [E]. For a
band the owner flags as audibly decisive and where the narrowing actually happens, that is a reasonable buy
for the *verify/compare* tiers; on *screen* (a ranking filter) a `freq_weights` emphasis on the existing 3
points is the cheaper first move. Recommendation: **`freq_weights` on screen; denser grid on verify.**

## 9. What I could NOT verify (be explicit)

- **The diagonal term's effect on ranking.** The only cell with a genuine asymmetric diagonal crease
  (`crease__osse_b1w`) has **no stored balloon v3 record** - it was not re-run after the v3 fix. The diagonal
  measurement *works* on the symmetric cells (where diag=H=V by construction), but I cannot show it
  re-ranks crease vs control. That needs the queued T3 balloons (**GPU**: the two b1w-pair best designs,
  45/135 planes, raw polars, no J). This is the one place GPU is genuinely required, and it is already queued
  as plan item 4.
- **The smoke night's four single-term-dominated cells, directly.** Their records were lost; I reproduced the
  *pattern* (75-91 % dislope on crease, etc.) on the surviving three configs and 100+ older trajectories, not
  those exact eight rows.
- **Per-class tolerance share on the PA 90x90@400 and B3b loading briefs** at the raw level - no v3 raw
  records for them (only term-level trajectories, which cannot recompute asymmetric cov).
- **beam_shape / spinorama on real designs** - they are not computed in the pipeline, so there is no stored
  output to score; wiring them in is itself the (deferred) work.
- Whether the mesher stores the balloon in *every* future screen config (the three I checked set
  `balloon: true`); a v4 that scores diagonals must assert the balloon is present or fall back cleanly.

## Appendix A: parameter-box / range audit (thread 2)

Owner-gated; **nothing applied**. At-limit = a searched knob within 3 % of a box edge among valid designs
(`scratch/v4_review/bound_audit.py`, over `runs/.../search.ndjson`). Campaign cells (Oct-27, current boxes):

| cell | knob | box | top-decile at edge | all-valid at edge | read |
|---|---|---|---|---|---|
| `crease__core_law` | `k` | 0.3..5 | 2/4 lo | 15/44 lo | fast-flare wall wanted; **widen lo** (or accept as physical) |
| `crease__core_law` | `morph_fixed` | 0..0.6 | 1/4 lo | 18/44 lo | pins at 0; likely a dead knob here |
| `control__osse_morph_b1w` | `q` | 0.9..1 | 2/4 hi | 13/40 hi | smooth-wall termination; **widen hi to 1.0 cap** (already near) |
| `control__osse_morph_b1w` | `n` | 1..10 | 2/4 lo | 6/40 lo | fast flare; consider lo < 1 if family allows |
| `b1t__rosse_morph` | `tmax` | 0.6..1 | 1/3 hi | 7/14 hi | **widen hi** (R-OSSE termination) |
| `b1t__rosse_morph` | `exponent` | 2..10 | 1/3 lo | 6/14 lo | **widen lo** |

Structural signals from older (pre-widening) runs - indicative, different scoring/boxes [M]:

| typology | knob | box | signal |
|---|---|---|---|
| `osse_baseline` | `n` | 2..8 | **140/140 top designs at lo** - box floor strongly binding; widen lo |
| `osse_baseline` | `q` | 0.9..1 | 58/140 top at lo | 
| `icw_termination` | `hold_end`, `kappa0` | 0.55..0.9 / 0..0.5 | ~all designs at lo - rails |
| `throat_adapter` | `k`, `throat_ext_angle_deg` | 0.3..2.5 / 0..15 | all top designs at hi - wants more |

**Proposed widening/narrowing table (owner-gated, [E]):**

| config | knob | current | proposed | reason |
|---|---|---|---|---|
| `b1t__rosse_morph` | `tmax` | 0.6..1 | 0.6..1 (at cap) / review family max | rails high; confirm KeySpec hard max |
| `b1t__rosse_morph` | `exponent` | 2..10 | **1.5..10** | rails low |
| `osse_baseline`* | `n` | 2..8 | **1.2..8** | 140/140 at lo |
| `crease__core_law` | `k` | 0.3..5 | **0.15..5** if KeySpec allows | half the best at lo |
| (all) | `invalid_geometry` refusals | n/a | **not a box issue** | 89/124 refusals are geometry-law, not edges; narrow seeds / fix unreachable seeds instead |

\* older config; verify against the current shipped `osse_baseline` before any change. **Narrowing** is
warranted only where a knob is provably dead (`morph_fixed` pinning at 0 across a cell) - but those are
already `search: false` in most campaign cells, so the live over-constraint is the *low/high rails above*,
not dead knobs. The 33 % refusal rate is not a bounds problem (finding 5).
