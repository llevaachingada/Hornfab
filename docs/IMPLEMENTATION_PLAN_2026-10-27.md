# Implementation plan, 2026-10-27: after the campaign smoke night

Written 2026-10-27 at the owner's request. Basis: `docs/evidence/CAMPAIGN_SMOKE_2026-10-27.md` (the smoke night),
the code paths cited below (checked 2026-10-27), and the owner conversation that reviewed another agent's
next-step list. Referenced from `docs/NEXT_DEV_PRIORITIES.md` P10.

**Status:** items 1-2 are ready to dispatch; item 3 is ready to dispatch but stops for an owner decision
(tolerances) before any GPU work; items 4-8 are sequenced after them. Section 9 is a separate, later idea.

## 0. Order, and why

| # | Item | GPU | Cost | Depends on |
|---|---|---|---|---|
| 1 | Dataset records accept the scorer's objective versions | no | ~1 h | - |
| 2 | `gcurve__osse_b1w` reseed | 1 T0 run | ~30 min | - |
| 3 | Objective v4 (per-term normalisation) | 27 T0 runs | 3-5 h code + ~25 min GPU | 1, owner picks tolerances |
| 4 | T3 diagonal-balloon check (45/135 deg) | yes | ~1-2 h | 1 (only so records are saved) |
| 5 | Second seed, same-brief pairs | yes | ~2.5 h | 3 |
| 6 | `compare` tier on the top 2-3 | yes | ~12 h | 3, 5 |
| 7 | Narrow-box polish on the single winner | yes | ~30 min | 6 |
| 8 | Fluted / lobed walls (Solana-derived) | later | see section 9 | 3 |

Do 1 and 2 first (no or one GPU run). Item 4 is the only search-adjacent run that is safe before v4, because it
records raw polars, not J. Items 5-7 all rank designs by J, so running them on v3 spends GPU on a scoring the
smoke night showed does not do what the weights say. **More solves on the same run before these fixes would write
records that cannot be saved (item 1) under weights that do not mean influence (item 3).**

## 1. Fix 1: dataset records reject objective v3

**Bug.** `hornlab_search/dataset/record.py:420-424` raises `'objective_version' must be 1 or 2`; the scorer
dispatches v3 at `search/evaluate.py:761`. Every v3 evaluation wrote no dataset record. Seen in
`runs/nights/smoke_2026-10-27/*.log` (for example `t0__b1t__lecleach_iwata_ar.log`), `runs/nights/runner_stdout.log`,
and `runs/gui_jobs/20261025T144106-cf2200.log` (so since at least 2026-10-25).

**Fix.** The allowed versions come from one source of truth shared with `_score`'s dispatch; do not hard-code
`(1, 2, 3)`, v4 is coming. Keep the bool rejection and "absent = v1". If the right home is a file the agent does
not own (ownership table in `CLAUDE.md`), append the exact change to `NOTES_FOR_SENIOR.md`.

**Tests.** v3 record round-trips; unknown version (99) rejected; `True` rejected.

**Investigate, do not rebuild.** Can the smoke night's lost v3 evaluations be reconstructed from
`runs/nights/smoke_2026-10-27/` (logs, campaign JSONL)? Report yes/no and what is missing.

## 2. Fix 2: `gcurve__osse_b1w` seed is invalid

**Failure.** `invalid_geometry: outside the brief envelope (width 783 > 380.0 mm, height 581 > 300.0 mm)`.

**Cause.** The mesher solves the OSSE coverage angle so the wall meets the guiding curve at `gcurveDist x L`
from the throat (`forks/hornlab-waveguide-mesher/hornlab_mesher/profile_morph.py`, around line 254). With
`gcurve_dist 0.5` and `gcurve_width_mm 335`, a 335 mm outline sits half way down the horn and the flare keeps
growing to the mouth; Morph cannot pull it back in (`morphAllowShrinkage` off). The other agent's reading
("the width is not the mouth width") was right; the reason is the station.

**Fix (preferred).** Seed `gcurve_dist: 1.0` and keep width 335, so the outline is the mouth; widen the
`gcurve_dist` box hi 0.9 -> 1.0 (check `families.py` KeySpec allows it). Fallback: keep 0.5 and reseed width
to the seed horn's measured diameter at L/2 (~140-160 mm; measure, do not guess). Update the header comment.

**Verify.**
`.venv\Scripts\python.exe .venv\Scripts\hornlab-search.exe search --config examples\typologies\campaign_2026-10-26\gcurve__osse_b1w.yaml --budget 1 --mode screen`
Seed valid and inside 380 x 300; report seed J, dofs, mouth size.

**Note, do not change.** The cell pins `aspect_ratio 1.0` while `control__osse_morph_b1w` runs 1.15, so it is
not a clean A/B; and J is H/V-only, blind to what a guiding curve does at the diagonals.

## 3. Objective v4: per-term normalisation

### 3a. Evidence

- Four of eight scored smoke-night cells are 82-92 % one term (smoke report section 4).
- Raw scales differ ~300x (dislope ~30 raw, rip ~0.1) at the same nominal weight.
- `native__lecleach_rollback`: `load` weight 0.5 contributes `0.5 x 0.22 = 0.11` of 5.60 J, **2 %**.

### 3b. Why it is not "now or never"

Every dataset record stores the raw `terms` and the target-free metric curves (`record.py:299, 346`). Once fix 1
is in, J under any normalisation is recomputable offline with no new solves. What recomputation cannot fix:
CMA-ES trajectories steered by the old J; their "best" designs are best under the old scoring. The smoke night
had no records saved (fix 1), so its T0 table must be re-run, not rescored.

### 3c. Design

- New `objective_v4` next to `objective_v3` in `objective/scalar_v2.py`: **identical raw terms to v3** (freq-weighted
  cov, below-f0 mask; reuse, do not copy), then `J = sum_i w_i * term_i / tol_i + penalty`. Same key set; also
  return the normalised terms.
- **Do not rewrite v3.** Old scores stay readable; every record says which version scored it.
- Tolerances live **in the brief** (`objective: {version: 4, tolerances: {cov, rip, di, dislope, flat, load}}`).
  A v4 brief missing any tolerance is a config error, no silent default; each must be > 0 and finite.
- The tolerances are a design decision: **owner's call, not the code's.**

### 3d. Effects to manage

1. **Old results:** none change; v1-v3 reproduce bit-for-bit.
2. **Penalty scale (the real risk):** `PENALTY_INVALID` (1000), `PENALTY_FAILED`, `graded_infeasible_penalty` are
   sized for J ~5-35. v4 J may be ~1-10, or ~100 with a tight tolerance. Penalties must still dominate every valid
   design, and the graded envelope penalty must still slope toward the valid region. Rescale per version only.
3. **CMA-ES:** sigma is in parameter space, unaffected. Flat-fitness / tolfun stops in `search/cma.py` are in J
   units and may need per-version values.
4. **Frozen contract:** `docs/plan/01_CONTRACTS.md` section 11 fixes the term list; v4 keeps the same terms. Flag
   anything that would need the owner; never edit the file.
5. **Version isolation:** never rank J across versions. Compare tier, reports, GUI and surrogate dataset loading
   must refuse or separate mixed versions, like the frequency-grid check.
6. **Meaning of weights:** after v4 a weight of 0.5 is half the influence *relative to the chosen tolerance*.

### 3e. Tolerance proposal (agent writes, owner picks)

`docs/evidence/OBJECTIVE_V4_TOLERANCES.md` (add to `docs/INDEX.md`): for each term, unit and definition with
file:line; (a) a physical tolerance with reasoning (coverage error in deg, DI slope in dB/oct, ...); (b) a
data-driven alternative (median raw value over the smoke-night best designs, section 4 table); and the
weighted-share table recomputed under each option. **Stop and ask the owner. No GPU before the choice.**

### 3f. Tests (offline)

All tolerances = 1 gives v3's J; scaling one tolerance by k scales that contribution by 1/k; missing/zero
tolerance rejected; v1-v3 unchanged; penalty ordering holds at the worst plausible valid v4 J; a v4 record
round-trips.

### 3g. After the owner approves

Add tolerances as **new v4 briefs** (or a v4 block if the owner prefers); never change a v3 brief in place.
Re-run T0 on all 27 cells in `examples/typologies/campaign_2026-10-26/` (~25 min, one GPU job at a time,
`CLAUDE.md` hygiene). Write `docs/evidence/T0_V4_<date>.md`: seed J, per-term weighted share, flag any cell still
> 70 % one term. Mark the smoke-night results as pre-normalisation history in `docs/CONTINUITY.md`.

## 4. T3 diagonal-balloon check

J scores the H and V planes only; the crease class's whole point is at 45/135 deg. Raw polars, so independent of
v3/v4; needs only fix 1 so the records are kept.

**Pairing correction.** The -85 % headline is `crease__core_law` on the **CORE 2-inch** brief; the control
`control__osse_morph_b1w` is on **b1w**. Different briefs, different scoring: not a fair pair. The same-brief pair
is `crease__osse_b1w` vs `control__osse_morph_b1w`. Run both pairs if time allows; the b1w pair first.

## 5. Second seed (after v4)

Right worry (one seed cannot tell "good typology" from "lucky seed"), wrong selection: "top 5 cells by J" ranks
across briefs whose J scales differ and, under v3, mostly ranks the dominant term. Choose seeds **by question, on
same-brief pairs** (crease vs control on b1w; the R-OSSE cells per brief), 60 evals each, scored v4. Ranking rule
as in the 2026-10-23 compare: "A beats B" only when medians differ by more than both spreads.

## 6. `compare` tier (after v4 and item 5)

Verify grid, 2 seeds, 150 evals, top 2-3 only (~12 h). On v3 these would be "publishable" numbers on weights about
to be replaced; rescoring stored terms does not change where the search went.

## 7. Narrow-box polish (last)

On the v4 winner only (~30 min). Polishing a v3 winner fine-tunes against the term imbalance.

## 8. What not to do

- No second seeds, compare or polish on v3.
- No reuse of smoke-night J across the three rescored briefs (`native_ath_core_2in`, `native_twinray_380_14in`,
  `native_lecleach_1200_1in`); smoke report section 0.
- No cross-brief "top N" by J.

## 9. Later: fluted / lobed walls (from JW Sound "Solana")

Source: jw_sound Instagram posts 2024-09-03 ("rapid prototyping of waveguides via genetic algorithms") and
2024-11-07 (Solana update), screenshots from the owner. Solana is multi-entry (woofer ports between flutes), which
stays deferred; only the wall geometry is considered. ~8 radial flutes from a non-round throat to a twisted,
square-ish petal mouth, pinwheel (not mirror-symmetric); GA-searched; horizontal polar holds roughly +/-45-60 deg
from ~700 Hz to 10 kHz, a disturbance near 1.8-2 kHz (likely ports/crossover), ragged off-axis above 5 kHz.

**Already expressible here:** N-lobed outlines (OSSE guiding curve with the Gielis superformula, P6), round-to-square
(Morph targets 1/3, FREEFORM `crossSections`), non-planar mouth (`p`-expressions on any OSSE parameter, `L`
included), parametrized search (CMA-ES; `perturbed_osse_hv`).

**Not expressible (mesher fork source):**
1. Lobe amplitude that rises mid-horn and fades at the mouth. OSSE/R-OSSE build one meridian per azimuth, so a
   lobe from `a(p)` or the guiding curve only deepens toward the mouth; parameter expressions admit `p` only
   (`profile_common.py` `_ParamExpressionValidator`); Morph blends only toward the mouth; FREEFORM stations have
   no lobed shape (ellipse, superellipse, rounded rectangle).
2. Twist: needs `z`/`t` in expressions or a per-station phi offset, and breaks the H/V mirror symmetry quarter
   meshing relies on (only `cos(2m*p)` survives): full model, ~4x BEM cost.
3. Non-round throat (FREEFORM first station circle/ellipse; OSSE starts at `r0`). Mostly a port artefact; low.

**Physics expectation:** flutes 30-50 mm deep matter above roughly 3-5 kHz, where Solana's map is ragged; its
500 Hz-2 kHz control comes from mouth size and port loading, which do not transfer while multi-entry is deferred.

**Steps (each gated on a real J gain under v4, compare-tier rule):**
- **9a.** The superformula guiding-curve cell is P6 / item 2 above; once reseeded and scored v4, add an m = 8
  (quarter-symmetric) variant.
- **9b.** `harmonic` FREEFORM cross-section station, fork change in `forks/hornlab-waveguide-mesher`
  (`docs/FORKS.md`): `r(phi) = r_ellipse(phi) * (1 + sum c_m cos(4m*phi))`, existing smootherstep blend, end
  stations ellipse / rounded rectangle so lobing rises mid-horn and fades at the mouth. ~30 lines in `freeform.py`
  (`_station_radius` + validation, guard r > 0). Typology = `perturbed_osse_hv` + a few `c_m` at 2-3 interior
  stations; reuse the monotone-increment idea from `perturb_increments` for the `c_m` bounds.
- **9c.** Twist, only if 9a or 9b wins, with the full-model cost accepted.
- Score with item 4's diagonal balloons and the 12 kHz finalist pass (P2): the band where flutes act.

## Appendix: dispatch prompts

Verbatim handoffs for items 1+2 and item 3 were given in the owner conversation of 2026-10-27; sections 1-3 above
are their content. A dispatching agent should build its prompt from those sections plus: read `CLAUDE.md`,
`docs/CONTINUITY.md`, the smoke report; interpreter `.venv\Scripts\python.exe`; do not touch the owner's
uncommitted files (`examples/briefs/user/`, `examples/typologies/shape_variants/`, `tools/make_shape_variants.py`,
modified `examples/typologies/perturbed_osse_hv.yaml`); every pushed commit updates `docs/CONTINUITY.md` and
`docs/ISSUES.md`; do not push unless the owner says so.
