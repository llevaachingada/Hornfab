# FABLE_DISCOVERY — independent architectural review of Hornfab

> **Results update, 2026-11-16 23:15.** Two corrections from requests R1–R4.
> (1) The replay in §5.1 regenerated DI with the wrong rule. Re-measured with the parity-exact
> harness (`A4_GRID_INDEPENDENT_SCORE.md`): among the best 28 pairs, dense-grid scoring gives
> sd 0.13 and rank correlation 0.88 (stored grids: 0.17 and 0.81), so the §5.1 conclusion stands.
> Over all 58 pairs the dense figure is sd 0.20. Scoring on a uniform dense log grid *is*
> grid-independent (58 → 116 points changes J by sd 0.045). The sd 0.61 shift R2 reported for
> "29 → 58 points alone" is the change of definition from an uneven grid to a uniform one, not
> noise; dense J is therefore not comparable with stored J.
> (2) The stored-versus-stored numbers (bias +0.19, sd 0.17 among the best pairs; same mesh for
> screen and verify) stand. R1 found mesh refinement effects small but had only two pairs with
> J < 5, both same-DOF pairs. R3 and S1 show ranking changes under combined objective changes;
> neither isolates a corridor from other v7-to-v9 changes. R4: the ratio of median seed spread
> to median gap between neighbouring configs is about 0.57. See `LOW_COST_AGENT_HANDOFF.md` §4.

**Date:** 2026-11-16 (evening). **Tree reviewed:** `main` @ `f0dd019` (dossier snapshot was `601be8c`;
`origin/main` is now `37dd1f3`). **Mode:** read-only. No tracked file, queue, config or process was
touched; no GPU/BEM solve or mesher run. The only new files are this document,
`FABLE_RESEARCH_REQUESTS.md` and the analysis script `fable_zero_gpu_checks.py`. The corpus was
subsequently committed; current HEAD when this context was refreshed is `01560e5`.

Status labels: **[verified]** read in code at `f0dd019`; **[measured]** computed here from stored run
artifacts; **[dossier]** taken from the evidence dossier without re-checking; **[inference]** my
interpretation.

---

## 1. Short verdict

**The most consequential problem is not the geometry representation, the optimizer, or the refusal
rate. It is that the measurement-and-goal layer cannot resolve the differences the search is
chasing, and the compute is spread over about 35 lanes that cannot be compared with each other.**
Three measured facts support this:

1. **"Verify" is not a higher-fidelity solve; it is the same mesh on a different frequency grid.**
   In all 58 screen/verify pairs under `runs/study-*`, the mesh hash and DOF count are identical;
   only the frequency list changes (18 points → 29 points, with one frequency in common)
   **[measured]**. So the screen-to-verify gap is purely how J samples a frequency-dependent curve.
   Among the 28 best pairs (screen J < 3.6) that gap is **+0.19 J bias with 0.17 J standard
   deviation**, rank correlation 0.81; on the 21 best unique pairs in the BO-vs-CMA report the rank
   correlation is 0.36 **[measured]**. For scale: the four best configs on the home landscape brief
   span J 3.10–3.99, the watchdog's "no gain" rule acts on 0.5 %, and the "discarded gains" the
   dossier worries about are 2.4 % and 4.7 %. All of those are at or below a single screen's noise
   (about 5 %). Mesh-convergence error is not measured at this step at all.

2. **The 80×50 brief is partly unreachable inside the 600×480 envelope, and every lane pays the
   same floor.** Across the best design of each of the 35 configs run on this brief (3,414 valid
   rows, 2026-11-15..17), vertical beamwidth at 700–1,100 Hz is never below 66°, and is 70–78° for
   the best designs, against a 50° target **[measured]**. The best designs deliver roughly
   65–76° H × 54–56° V mid-band, never 80×50. This is what aperture physics predicts for a mouth at
   most 480 mm tall. Rescoring stored responses under geometric similarity (see §5) confirms it:
   the same horns at 1.2× and 1.5× scale give 67° and 56° in that band. A shared irreducible
   penalty compresses the differences between designs and pushes the optimizer to trade real
   qualities for coverage it cannot get.

3. **Compute is fragmented.** The median config on this brief has about 50 valid rows at 6–14
   search dimensions. About 32 % of the constant-directivity-brief rows (829 of 2,595) went to
   families whose best J is 17–33, whose mouths are far inside the envelope (e.g. 417×203 mm) and
   whose low-frequency vertical beamwidth is 120–160° **[measured]**. Those families are not
   failing a search; they are being scored against a target they are not built for, which the
   repo's own acoustic-grounding rule already forbids. Four of the five best configs are the same
   OSSE engine.

**Consequence for the owner's four hypotheses:**

| Hypothesis | Verdict |
|---|---|
| Over-restrictive bounds and refusals | Real but second-order. On the current brief 88.6 % of attempts reach a full solve **[dossier, code path verified]**; fixing every refusal buys at most about 11 % more solves. |
| Narrow typology lanes | Half right. The damage is too many thin, non-comparable lanes, not that each lane is narrow. A universal family would add a taxonomy, not physics. |
| Awkward or inactive knobs | True **[dossier, spot-verified]**, and worth cleaning up, but not what limits results today. |
| Exact briefs exclude equally good patterns | Right, and understated: the exact brief is partly unattainable in the envelope. |

**Uncertainty:** the noise figures come from one cohort (58 pairs, 1.6k–8.1k DOF, the BO-vs-CMA
typology); other families may differ. A rank correlation of 0.8 at the top means the search still
mostly climbs the right hill, so the gain from fixing this is in which finalist is picked and in
not chasing sub-noise gains, not a step change in search speed.

---

## 2. Corrections to the dossier at current HEAD

- **v9 is no longer "in flight and unimportable".** `objective/scalar_v9.py` and
  `targets/profile.py` are committed (`c2310c8`, `37dd1f3`) and import cleanly **[verified]**.
  I found no brief under `examples/` that carries a `coverage_profile`, so no home search uses it
  yet; CONTINUITY lists the "owner smooth-brief re-baselining decision" as open.
- **Klangfilm H/V Stage A has a result:** throat-only arms moved the intended axis by ≤ 2.74° and
  scored worse; the pre-declared 3° rule failed (`STAGE_A_VS_B_DECISION.md`, commit `8421497`).
  Phase B (monotone H/V core) is geometry-only so far. This is direct evidence that H/V authority
  is the geometry capability that is actually missing.
- **Still true at `f0dd019` [verified]:** the `startswith("invalid_envelope")` mapper (now
  `evaluate.py:1562`); the generic-grid extent returning `2·max_φ r` for both width and height;
  `search.links` refusing generator blocks; `bo/cohort.py:96` refusing objective versions other
  than 4; the watchdog's `obj >= 900` bad-outcome test; `done` starting empty on every night run.
- The dossier's "screen J is a proxy for verify" question (Q3/Q10) is now answered more sharply
  than it was posed: the two differ only by frequency sampling.

---

## 3. Option comparison

| | A. Measurement and goal first | B. Truth fixes only | C. Targeted H/V-authority geometry | D. Universal grammar / shared body | E. Menu (QD / Pareto) | F. Adaptive supervisor |
|---|---|---|---|---|---|---|
| What it is | Grid-invariant J on a common interpolated frequency grid; a stated noise floor; a v9 corridor home brief the envelope can meet; finalists confirmed by re-solve; lanes consolidated by physics | Fix refusal taxonomy, prefix bug, extent estimate, generator links, v4/v7 cohort gate | One capability: independent H and V wall laws on an existing engine, admitted by a pre-declared authority test | One grammar or one constrained freeform body for all families | Archive over achieved coverage, or coverage/ripple Pareto | Shadow advisor → between-job controller → portfolio |
| Benefit | Makes every later comparison meaningful; changes which design wins; mostly free rescoring | Honest statistics; up to ~11 % more solves | Attacks the measured gap (H/V ratio ≈ 1.3 achieved vs 1.6 asked) | Expressiveness; one BO encoding | Matches "several acceptable outcomes" | Less wasted GPU if signals were trustworthy |
| Code dependency | Objective version + metric identity (already separated by `identity_v2`); replay seam exists | Small, local | Phase B core exists as a tool; needs family adapter and BO geometry adapter | Large; new mesher capability; new BO encoding (categoricals are refused today) | Pareto path exists but is unwired; QD descriptors configurable | No state migration between policies; packages invalidated by policy change |
| Dimensions / solve cost | Unchanged | Unchanged | +3 to 6 dims; same per-solve cost | 15–30+ dims; hundreds of rows before any model ranks | Archive needs far more solves than available (10/324 cells at 200) | n/a |
| Data reused | All stored responses, exactly | All | Existing OSSE rows as priors only if the old box embeds in the new one | Little: old knob vectors do not map | All responses for descriptors | All logs |
| Likely failure point | Residual noise stays ~0.12 J even on a common grid; owner may not want a corridor | Mistaken for progress | A new shape cannot be shown better while differences sit under the noise and floor | Silent no-op knobs, invalid shapes, a year of plumbing | Thin archive; elites unverified | Learns preferences from noise and from BO inheriting CMA data |
| Reason not to choose it | Adds no new shapes | Not sufficient alone | Premature before A | Evidence does not show it would repay its cost | Sample-hungry at this GPU budget | Its inputs are below the noise floor |

Not unifying is the right call for multi-entry horns, CAD bodies and anything with a different
source condition or symmetry: they share data model and reporting, not a search space or a
surrogate. Two designs are "equivalent enough" to share a model only when engine, source, symmetry
and brief identity all match; across families, share responses and response-derived descriptors,
never knob vectors.

**Size (option 08).** Not justified as a GPU campaign now. The similarity rescoring in §5 is a
zero-GPU instrument that already answers the first-order question, and its answer is "size buys
low-frequency vertical control and loading, but does not by itself lower the coverage error".

---

## 4. Disconfirming evidence against option A (my favourite)

- A rank correlation of 0.81–0.89 among the best pairs is not chaos. BO's GP already models noise.
  The search-efficiency gain from denoising may be small; the gain is mainly in finalist choice.
- Putting both grids onto one dense interpolated grid removed the bias (+0.19 → +0.02) but only
  cut the spread from 0.17 to 0.12 J. Eighteen frequencies do not fully determine the response with
  the simple interpolation I used; a better interpolant is untested.
- My replay harness reproduces every stored term exactly except `di`, which it regenerates from a
  different DI source (stored 0.53 vs replayed 6.06 on one design). So J-level numbers from my
  replays are indicative; term-level numbers (coverage, loading, beamwidth) are sound.
- "The brief is unreachable" rests on what 35 searches achieved plus aperture physics plus the
  similarity trend. That is strong but not a proof; a geometry with real vertical authority and a
  mouth using the full 480 mm (the best designs use about 400 mm) could move the floor somewhat.
- The owner's comment in the brief ("60–90 H, 40–60 V") is dated context, not an approved corridor.
- Unsupported premise I am relying on: that mesh error is smaller than frequency-sampling error.
  Nothing in the screen/verify data can show that (request R1).

---

## 5. What I established myself (zero GPU, option C of the prompt)

Script: `scratch/fable_architecture/fable_zero_gpu_checks.py` (modes `A` and `B`). Read-only replay
of stored `response.npz` through `objective/replay.py`.

**5.1 Screen vs verify.** 58 pairs, all same mesh and DOF, 18 vs 29 frequencies.

| Comparison (28 best pairs) | Bias (J) | Std dev (J) | Rank corr. |
|---|---:|---:|---:|
| Stored screen J vs stored verify J | +0.19 | 0.17 | 0.81 |
| Both responses interpolated to one 58-point log grid, same scorer | +0.02 | 0.12 | 0.89 |

The largest single-term bias is `flat_cv` (+0.135 raw), a standard deviation over few points. J is
grid-dependent by construction: its terms are sample means and standard deviations over whatever
frequencies were solved, and the screen grid adds extra points at 2.5–4.3 kHz, so the grid itself is
an unstated frequency weighting.

**5.2 Achieved coverage on the home landscape brief.** Best design per config, mean beamwidth by
band (H then V, degrees; target 80 / 50):

| Config (best J) | Mouth W×H mm | H 0.7–1.1k | H 1.1–2.5k | H 2.5–5.5k | V 0.7–1.1k | V 1.1–2.5k | V 2.5–5.5k |
|---|---|---:|---:|---:|---:|---:|---:|
| `hl__ext_throat_hvlaw_v7` (3.10) | 580×401 | 63 | 67 | 76 | 78 | 54 | 56 |
| `hl__osse_rrect_fold_warm_v7` (3.62) | 587×414 | 65 | 75 | 69 | 70 | 50 | 58 |
| `hl__osse_rrect_morph_v8` (3.92) | 599×369 | 63 | 77 | 76 | 76 | 43 | 54 |
| `hl__rosse_rect_cd_v7` (4.56) | 563×411 | 71 | 82 | 80 | 75 | 56 | 54 |
| `hl__crowe_x_osse_cd_v7` (5.34) | 593×412 | 69 | 81 | 74 | 76 | 62 | 56 |
| `hl__crowe_panel_home_v7` (16.9) | 580×293 | 88 | 84 | 69 | 124 | 90 | 65 |
| `rr__crowe_panel_es600_v7` (22.5) | 417×203 | 94 | 87 | 73 | 159 | 109 | 70 |

Width is pinned near the 600 mm limit for every good design; height is not. Horizontal coverage is
also too narrow at 700–1,100 Hz (63–71°), the usual narrowing near the mouth-control frequency.

**5.3 Size sensitivity by similarity.** A horn scaled by `s` has the same directivity at
frequencies divided by `s`. Dividing the stored frequency axis by `s` therefore gives the exact
response of the scaled horn with no solve. Median over the 12 best landscape configs, scored on the
common band 350–5,333 Hz:

| Scale (envelope) | V bw 0.7–1.1k | H bw 0.7–1.1k | Coverage term (raw) | Loading term (raw) |
|---|---:|---:|---:|---:|
| 1.0 (600×480) | 80 | 65 | 1.02 | 0.93 |
| 1.1 (660×528) | 73 | 67 | 0.94 | 0.46 |
| 1.2 (720×576) | 67 | 70 | 0.94 | 0.08 |
| 1.35 (810×648) | 60 | 73 | 0.88 | 0.00 |
| 1.5 (900×720) | 56 | 76 | 0.94 | 0.00 |

Low-frequency control and loading improve with size as expected; the coverage term barely moves
because the error relocates to higher frequencies in designs that were optimized at 1.0. Three
FREEFORM-engine designs (`rosse_rect`, `crowe_x_osse`, `biradial_es`) do improve their coverage
term by 40–50 %. Caveat: the scaled horn has a scaled throat (43 mm at 1.2×), so it is not an
HF1440 horn; the top octave and the loading numbers are for a different driver.

---

## 6. Top uncertainties, ranked by decision value

1. **The owner's acceptable corridor**, especially the vertical onset frequency and whether about
   70×55 mid-band is acceptable. Only the owner can settle it, and it re-ranks everything.
2. **Mesh-convergence error at the top of the ranking.** Unmeasured; if it is comparable to 0.17 J
   the top of every leaderboard is undetermined (R1).
3. **Whether a corridor objective re-ranks designs and families** on the 3,414 existing rows (R3).
4. **Seed-to-seed spread of best J versus between-config gaps** (R4). If seeds differ by more than
   configs do, lane comparisons to date say little.
5. **How many screen frequencies are actually needed** once J is grid-invariant (R2). Solve cost is
   linear in frequency count, so this is a direct throughput lever.
6. Generic-grid false refusals (dossier Q1) and held-out GP ranking (Q8): lower value now, because
   refusals cap at about 10 % and BO investment is not the next decision.

---

## 7. Choice under item 5 of the prompt: B, after doing C

I did the cheap tests that could be done directly (§5). Four bounded requests remain in
`FABLE_RESEARCH_REQUESTS.md`; R1 and R3 could change the recommendation, R2 and R4 size it.

---

## 8. Provisional recommendation and next phase

**Recommendation (conditional on R1 not showing mesh error larger than sampling error, and on the
owner accepting a corridor):** choose option A now, do option B's truth fixes alongside it because
they are cheap, hold option C until A is in place, and do not build D, E or F yet.

Concretely, as proposals for the specification phase, not authorized changes:

- Define J terms as log-frequency quadratures on one common interpolated grid, as a new objective
  or metric version, so screen and verify estimate the same number. Old J replays stay exact.
- Publish a noise floor per brief and express every stop, "no gain" and comparison rule in units
  of it. Until then the watchdog stays a safety net and its 0.5 % rule should not be read as
  science.
- Owner picks a v9 corridor for the home brief whose vertical onset the 480 mm envelope can meet;
  rescore all stored rows under it at zero GPU before any new search.
- Stop scoring non-constant-directivity families against the constant-directivity brief. Group
  lanes by engine and source physics (about four to six), and give each enough rows to mean
  something.
- Replace "verify" with a finalist race: the top handful re-solved on a dense grid and a finer
  mesh, ending in a short menu for the owner rather than one scalar winner.
- Keep the 600×480×480 brief as is. Use similarity rescoring to price any size question first.
- Supervisor: defer. Revisit as a read-only shadow only after the noise floor and corridor exist.

**Next phase in one paragraph.** Run R1–R4 (all zero-GPU or CPU-only) and get the owner's corridor
decision. If mesh error is small and the corridor re-ranks the top, write the final specification
around option A plus the truth fixes, with H/V-authority geometry as the first capability to admit
afterwards under a pre-declared authority test like Klangfilm's 3° rule. If mesh error is large,
the specification leads with a fidelity ladder instead, and everything else waits. If the corridor
does not re-rank anything and seeds agree, option A shrinks to the grid-invariant J alone and
option C moves up.

**What would falsify this recommendation:** R1 finding mesh deltas well under 0.05 J *and* R3
finding the top-20 unchanged under any reasonable corridor *and* R4 finding seed spread far below
config gaps. In that case the measurement layer is good enough and geometry authority is the
bottleneck after all.
