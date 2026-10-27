# Objective v4 tolerances - options for the owner to choose

Companion to `docs/research/V4_SCORING_REVIEW_2026-10-27.md` (findings) and `IMPLEMENTATION_PLAN_2026-10-27.md`
§3e. The owner picks; nothing here is applied, and no v3 brief is changed. Tags: **[M]** measured offline this
pass, **[D]** derived, **[E]** reasoned estimate. Numbers from `scratch/v4_review/analyze2.py` over the 50 ok v3
records. v4 scores `J = sum_i w_i * term_i / tol_i + penalty`; a tolerance is "the size of a miss that counts as
one unit of bad".

## Term units and definitions (file:line)

| term | raw definition | unit | source |
|---|---|---|---|
| `cov` | mean_f((bw_h-t_h)^2+(bw_v-t_v)^2)/100 over the f0-masked band | (deg^2)/100 | `objective/scalar_v2.py:332`, `terms.py:49` |
| `rip` | mean_f(ripple_detrended_h + ripple_detrended_v) | dB (summed H+V) | `scalar_v2.py:230`, `smoothness.py:59` |
| `di` | mean_f((di_db - di_ref)^2)/10 vs Gaussian-beam ref | (dB^2)/10 | `scalar_v2.py:379`, `di.py:127` |
| `dislope` | (slope - target)^2, slope = polyfit(log10 f, di) | (dB/decade)^2 | `terms.py:73` |
| `flat` | std of on-axis dB after log2-f detrend | dB | `smoothness.py:93` |
| `load` | mean_f(max(0, z_min - Re z_throat)) | normalised Re(z) shortfall | `terms.py:92` |

Solver-noise anchors (nothing below these is signal) [R, tolerance-research §2]: DI 0.3 dB, beamwidth 2 deg,
beat-vs-bempp SPL 0.04-0.06 dB.

## Option A - physical tolerances (recommended)

Reasoned from units and a "what miss = 1 unit" target [E]:

| term | tol | reasoning |
|---|---|---|
| `cov` | **2.0** | a uniform 10 deg/plane coverage miss -> 2*10^2/100 = 2.0 |
| `rip` | **1.0** | ~0.5 dB detrended ripple per plane, summed over H+V |
| `di` | **0.4** | a 2 dB DI error -> 2^2/10 = 0.4 (well above the 0.3 dB noise floor) |
| `dislope` | **9.0** | a 3 dB/decade slope error -> 3^2 (CD working def: DI flat to +/-2-3 dB) |
| `flat` | **1.5** | 1.5 dB of on-axis roughness after EQ-able tilt removed |
| `load` | **0.3** | a 0.3 shortfall in normalised Re(z) at the throat |

Weighted shares under Option A [M]:

| cell | cov | rip | di | dislope | flat | load | max term |
|---|---|---|---|---|---|---|---|
| `gcurve__osse_b1w` | 52 | 3 | 14 | 4 | 27 | 0 | 52 % |
| `native__lecleach_rollback` | 28 | 0.5 | 27 | 0 | 37 | 7 | 37 % |
| `crease__core_law` | 27 | 4 | 17 | 37 | 14 | 0 | 37 % |

vs v3 (no normalisation), the max single-term share drops from 55/45/75 % to 52/37/37 %. The 2 %-load problem
is fixed (load now 7 % on the loading brief at weight 0.5), and dislope's 75 % domination on crease falls to
37 %.

## Option B - data-median tolerances

`tol_i` = median raw term over the cell's records, floored at 1e-3 [M]. Equalises shares best:

| cell | cov | rip | di | dislope | flat | load | max term |
|---|---|---|---|---|---|---|---|
| `gcurve__osse_b1w` | 30 | 31 | 9 | 15 | 15 | 0 | 31 % |
| `native__lecleach_rollback` | 12 | 40 | 11 | 0 | 19 | 19 | 40 % |
| `crease__core_law` | 27 | 31 | 8 | 20 | 14 | 0 | 31 % |

Flatter, but: (i) it is **circular** - the tolerance is read off the designs being scored, so it drifts every
campaign; (ii) it inflates `rip` (median ~0.02-0.14) into a 30-40 % share, over-weighting a term near the
noise floor; (iii) it **breaks penalty ordering** (below).

## Penalty-ordering check (plan 3d.2 / 3f) [D]

`PENALTY_INVALID` = `PENALTY_FAILED` = 1000; graded envelope cap = 2000; `NAN_TERM_FILL` = 30. A valid design
with every term unmeasurable scores `sum_i w_i * 30 / tol_i`; this must stay **well below 1000** or an invalid
design outranks it.

| cell | worst-seen valid J | all-NaN-fill valid J | verdict |
|---|---|---|---|
| **Option A** `gcurve` | 4.9 | **79** | OK |
| **Option A** `lecleach` | 4.9 | **117** | OK |
| **Option A** `crease` | 8.4 | **79** | OK |
| **Option B** `gcurve` | 3.7 | 245 | OK |
| **Option B** `lecleach` | 3.5 | **1572** | **FAIL (> 1000)** |
| **Option B** `crease` | 5.9 | 312 | OK |

Option B fails on the loading brief because `load`/`rip` medians are ~0, so the 1e-3 floor makes
`30/0.001 * 0.5 = 15000` possible. **Any data-driven tolerance must be floored at a physical minimum**
(the noise anchors), and the ordering test must run per brief before a v4 campaign - not once globally.
`PENALTY_INVALID` may also need a per-version bump (plan 3d.2) if a tight tolerance pushes a legitimate valid
J toward 100+; Option A does not, so no rescale is required for it.

## Per-class blocks (recommended structure) [E, from tolerance-research §3]

| class | cov | cov shape | rip | di / DI-std | dislope | load |
|---|---|---|---|---|---|---|
| **A. CD waveguide** (B1/B2 hi-fi/PA) | 2.0 | asymmetric 2:1 narrow:wide | 1.0 | di 0.4, add DI-std tol ~2 dB | 9.0 | off |
| **B. Loading / rollback** (Le Cleac'h, salmon, B3b) | 4.5 (looser) | symmetric or off | 1.5 | looser; DI rises by design | **off (0)** | on, z_min 0.7, tol 0.3 |
| **C. Low-reach PA** (B3a 90x90@400) | 4.5 | one-sided below f0 | 1.5 | loose below f0 | from f0 only | per brief |

cov tol 4.5 = a ~15 deg/plane miss (2*15^2/100). These are starting points; each must pass the penalty-ordering
test for its brief.

## Recommendation

**Option A (physical) with per-class blocks and floors from the noise anchors.** It keeps penalty ordering,
is not circular, demotes the dominating terms without over-weighting noise, and leaves `PENALTY_INVALID`
unchanged. Add DI-std and asymmetric-cov per the scoring review before fine-tuning any weight.
