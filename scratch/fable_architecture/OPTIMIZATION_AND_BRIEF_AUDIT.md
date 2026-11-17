# Objectives, Briefs, Acoustic Truth and Data Reuse — read-only audit

- Repo root: `C:\Users\hunte\Hrns\hornlab-search` (canonical checkout; `*-wt` ignored)
- Branch: `main`
- HEAD at dispatch (orchestrator): `2c0e2928e932a47975fc284401eafa74ebfc5002`
- HEAD observed by this pass, 2026-11-16 ~19:43 local: `d187c0677948bf70673ecb5038a5d242f100a5d1`
  (`feat(design): Klangfilm HV GRID family + scoring-view compare endpoint ...`)
- HEAD advanced during the pass: `2c0e292` → `3efe9be` → `ded9e62` → `d187c06`. A live julia/python
  solve was reported; nothing was run against it, no process touched, no git mutation made.
- Working tree at write time (`git status --short`, 19:43): clean except untracked
  `.claude/worktrees/` and `docs/research/BO_GUI_SOURCE_AUDIT_HANDOFF_2026-11-16.md`.
  (`targets/scoring_view.py` was uncommitted when dispatched and is committed by `d187c06`.)
- Date of this audit: 2026-11-16. Interpreter available: `.venv\Scripts\python.exe` (used only for a
  2-line closed-form check; no solver, no pytest, no mesher).

Status legend (every nontrivial claim carries one):
**verified** = read in the working tree or computed here; **historical record** = a past run/report
number not re-run; **plausible inference** = follows from code but not separately measured;
**unverified** = believed but not checked; **contradicted** = two sources disagree.

Facts are stated as facts; interpretation is marked `[interp]`.

---

## 1. What objective v7 actually implements

`objective_v7` **never raises and never returns NaN/inf** (`hornlab_search/objective/scalar_v7.py:52-53`,
`:226-232`). It inherits `rip/di/dislope/flat/distd` and the frequency weighting from `_objective_v3`
(`scalar_v7.py:519-535`, `hornlab_search/objective/scalar_v2.py:301-408`) and re-implements `cov` and
`load` plus adds `flat_cv` (`scalar_v7.py:6-11`, `:78-85`). J is a **plain weighted sum of
tolerance-normalised terms**:

```
J = Σ_k w_k · raw_k / tolerance_k        k ∈ {cov,rip,di,dislope,flat,load,distd,diag,flat_cv}
```
(`scalar_v7.py:549-552`; v4's normalisation rationale `hornlab_search/objective/scalar_v4.py:1-13`).

### 1.1 Term decomposition (home landscape brief)

Home brief weights/tolerances: `examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml:41-50`
(weights) and `:58-67` (tolerances); `cov_v_weight: 0.5`, `flat_band: scored`, `cov_narrow_ratio: 2.0`,
`cov_below_f0: mask` (`:54-73`). Target: 80 H × 50 V, 350–8000 Hz, f0=f0_v=700, loaded_hi 5600,
2× freq weight 2500–5500 (`:28-40`). Confirmed resolved block: `docs/queue/HOME_SCORE_AUDIT_2026-11-16.json`
job[0].score (verified).

| Term | What the code computes (raw) | Path:line | Freq-resolved? | Failure / cliff behaviour | Home w/tol |
|---|---|---|---|---|---|
| `cov` | Horizontal: freq-weighted mean over `f≥f0` of `side·(bwH−80)²/100`, `side=2` if narrower than target else 1; Vertical multiplied by `cov_v_weight=0.5` (symmetric path) or scored as signed halves if `coverage_v_up/down` present (absent here). Below f0 is masked. | `scalar_v7.py:410-513`; `scalar_v4.py:165-195`; band mask `scalar_v2.py:316-357` | Yes: per-frequency error → weighted mean | Narrow side doubled (cliff at zero error); no hard per-frequency cap; below-f0 dropped | 1.0 / 3.0 |
| `cov` + 8 kHz floor | Adds `(dh²+dv²)/100`, `d = max(0, 0.75·target − bw)` measured at the **single** highest solved f ≤ min(8000, band_hi); only narrowing charged | `scalar_v7.py:384-407`, `:508-513` | No: one frequency | One-sided **floor/cliff** at 8 kHz; wider is free | folded into `cov` |
| `rip` | `mean_f[ripple_detrended(H) + ripple_detrended(V)]`, each the sample-std residual of an even quartic fit inside `±target/2`, dropping samples < −40 dB, needing ≥7 samples | `scalar_v2.py:140-163`, `:364-370`; `metrics/smoothness.py:59-90` | Yes: per-f within-coverage residual → weighted mean | All-NaN f → `NAN_TERM_FILL`; a lobe **outside** the coverage window is invisible | 1.0 / 1.0 |
| `di` | `mean_band[(DI − DI_ref)²]/10`, `DI_ref = target_di_gaussian_db(80,50)` when `di_target_db` is null | `scalar_v2.py:372-381`; `metrics/di.py:127-143` | Yes (in-band mean) | Uses **full in-band** set (not score band); DI_source cuts_estimate is flagged but not rejected | 0.3 / 0.4 |
| `dislope` | `(slope − target)²`, `slope = polyfit(log10 f, DI)[0]` over the score band; <2 points → 0.0 | `scalar_v2.py:359-360`; `metrics/di.py:89-97`; `objective/terms.py:73-79` | No: one regression slope | Translation-invariant in dB; a curved DI has one slope | 1.0 / 9.0 |
| `flat` | Std of on-axis residual about a straight line vs log2 f; `flat_band=scored` ⇒ over `f≥f0` only (else 350–8000) | `scalar_v7.py:533-534`; `scalar_v2.py:166-187`; `metrics/smoothness.py:93-117` | Yes (std over f) | <4 usable points → `NAN_TERM_FILL`; ddof=2 | 0.5 / 1.5 |
| `load` (v7 = C1) | `lfp_pen + rez_pen`: `lfp_pen = max(0, log2(1.6·LFP20/F_X))` with `LFP20` = first ascending Re z crossing 0.20; `rez_pen = max(0, 0.5 − min Re z)` over `[F_X, min(band_hi, f11)]` | `scalar_v7.py:313-350`, `:238-263`; window bound `:292-310` | No: crossing + window minimum | Unmeasurable window/crossing → `NAN_TERM_FILL`; tol 0.3 makes an unmeasurable load ≈ 100·w | 1.0 / 0.3 |
| `distd` | `std(DI)` over the score band (`f≥f0`) | `scalar_v7.py:537-542` | Yes (std over f) | <2 finite → 0.0 (free); **not** residual — a linear rise keeps distd>0 (`scoring_view.py:61-65`) | 0.5 / 2.0 |
| `diag` | Mean over score band of `side·(bw45−65)²/100 + side·(bw135−65)²/100`, ref = (80+50)/2 = 65 | `scalar_v4.py:198-223` | Yes: per-f → mean | No balloon/axis → `NAN_TERM_FILL`; does not penalise diagonal-vs-H/V inconsistency (`scalar_v4.py:30-31`) | 1.0 / 2.0 |
| `flat_cv` (C2) | Population std (ddof=0) of residual of `on_axis + 20·log10 f` vs log2 f over `[F_X, 3000]` | `scalar_v7.py:356-378`, `:547` | Yes (std over f) | <2 points → `NAN_TERM_FILL`; zero weight stores 0.0 | 1.0 / 1.5 |
| `penalty` | `PENALTY_FAILED = 1e3` added as `total` on invalid/failed evaluation; also `PENALTY_INVALID = 1e3` | `objective/terms.py:18-19`; `scalar.py:54-60`; `scalar_v7.py:520-526`, `:550-554` | n/a | Hard **cliff**: a failed solve ⇒ J=1000, far above any valid J | — |
| `NAN_TERM_FILL` | A term whose every in-band input is unmeasurable is set to **30.0 raw**, then normalised | `objective/terms.py:32-35`; `scalar_v7.py:216-223`, `:549` | n/a | Deliberately unflattering but below the 1e3 failure penalty | — |

**Integrated scalars vs frequency-resolved constraints (verified).** Every term is reduced to a scalar
before entering J: `cov/rip/di/diag` are frequency-weighted means of per-f errors; `flat/flat_cv/distd`
are standard deviations over frequency; `dislope` is a single regression slope. The only local/extremal
operators are the **single-frequency 8 kHz floor** (`scalar_v7.py:391-407`) and the **window minimum**
inside `load` (`scalar_v7.py:332-346`). There is no surviving hard per-frequency band constraint.
The 2× frequency emphasis (`brief:38-40`) reaches `cov`, `rip`, `diag` and per-f means only — not
`di`, `dislope`, `distd`, `flat` or `flat_cv` (`scalar_v4.py:32-33`; `scalar_v2.py:57-75`, `:364-370`).

**Penalty ordering invariant.** `worst_valid_j` = J of a valid design whose every term is unmeasurable;
config must keep it far below `PENALTY_INVALID` (`scalar_v7.py:207-213`). With home tolerances, `load`
tol 0.3 alone contributes `1·30/0.3 = 100` to that worst case — an unmeasurable loading term
dominates J `[interp]`.

---

## 2. How precise is "80H × 50V"?

**Fact: it is an exact, frequency-flat point target, not a band.** `cov` measures
`bw(f) − 80` (H) and `bw(f) − 50` (V) squared at every scored f ≥ 700, then averages
(`scalar_v7.py:410-449`; `scalar_v4.py:170-195`). The target has no per-band values and no tolerance
band; the only "tolerance" is a **normaliser** (divide by 3.0), not an acceptance interval
(`scalar_v4.py:1-13`). The brief comment states 80×50 is "the middle of the owner's home range:
60-90 H, 40-60 V" (`brief:8`) — i.e. the single point is a *centre*, and the accepted region is
broader than what is scored `[interp]`.

How the target's precision is softened or distorted by the real terms:

- **Frequency dependence:** the target is constant in f, but the score only starts at 700 Hz
  (`brief:35-36`); below f0 coverage is masked (`cov_below_f0: mask`, `brief:69`), so a horn that
  cannot hold pattern at 400 Hz is neither rewarded nor punished there. Above 700 the *same* 80/50 is
  demanded up to 8000 except for the one-sided 8 kHz floor (`scalar_v7.py:384-407`).
- **Asymmetry:** because `coverage_v_up_deg/coverage_v_down_deg` are absent (`brief:28-37`; validation
  `targets/spec.py:104-127`), V is scored as one total width. A horn with 30° up / 20° down scores
  identically to 25/25 (`scalar_v7.py:497-507`) `[interp]`.
- **Flat DI:** `di_target_db: null` ⇒ `di` scores against the separable-Gaussian DI of 80×50
  (`scalar_v2.py:377-379`; `metrics/di.py:127-143`), and `di_slope_target: 0` (`brief:33`) with
  tolerance 9.0 makes a +5 dB/dec slope cost only 25/9 ≈ 2.78 (`HOME_SCORE_AUDIT:34`, verified against
  `scalar_v2.py:359-360` and `terms.py:73-79`). A "flat DI" goal is therefore **soft**, not a gate.
- **Lobes:** beamwidth uses the **outermost** −6 dB crossings (`metrics/polar.py:69-121`), so a strong
  wide-angle lobe can keep or inflate the reported width; ripple only sees in-coverage samples within
  `±target/2` and above −40 dB (`smoothness.py:59-90`). An off-axis lobe beyond the coverage window is
  not charged by `cov` or `rip` `[interp]`.
- **Narrowing floors:** the only explicit floor is the one-sided 8 kHz check
  (`bw8k_floor·target`, `scalar_v7.py:403-407`). Between 700 Hz and the 8 kHz sample, narrowing is
  penalised smoothly (×2 on the narrow side via `cov_narrow_ratio`, `brief:68`), not by a cliff.
- **Missing metrics:** no term scores off-axis leakage outside ±coverage/2, rear/side energy
  separately, polar smoothness across arbitrary planes, or H/V coupling. `di` integrates full-sphere
  balloon energy into one number when `di_source=="balloon"` (`evaluate.py:508-531`); `diag` samples
  only the 45°/135° planes (`scalar_v4.py:198-223`). Listening-window / SPDI / forward-beam-shape
  scalars exist but are **report-only, never in J** (`evaluate.py:508-543`).
- **Vertical weighting:** V counts half (`cov_v_weight 0.5`, `brief:11`, `scalar_v7.py:503-505`), an
  owner-ear preference, not an acoustic equivalence `[interp]`.

Net: "80×50" is exact where it is scored (f≥700, symmetric V), but the total J is dominated by the
*normaliser*, *weights* and *aggregation choice*, not by a hard 80/50 acceptance test.

---

## 3. Goal regions / alternatives (unranked, not recommendations)

These are distinct framings that the evidence could distinguish; none is a finished design.

1. **Acceptance band set (region).** Replace the point 80/50 with a scored *interval* per plane, e.g.
   H∈[60,90], V∈[40,60] per the brief's owner quote (`brief:8`), optionally frequency-dependent. Distinguishes:
   whether a design inside the band but off-centre (e.g. 72H/45V) is acceptable rather than penalised
   quadratically. Evidence needed: owner pairwise preferences among in-band designs, plus verify-grid
   beamwidth curves. Note: this is **not** a recommendation to widen a tolerance — it changes what is
   scored from a point to a feasibility region, which is a different objective shape.
2. **Frequency-dependent corridor (smooth narrowing).** Coverage allowed to narrow smoothly above
   crossover. The repo already encodes a crude version: the `_smooth` brief relaxes `di_slope_target`
   to 5 dB/dec, `cov` tol to 8, `cov_narrow_ratio` to 1, `di` weight to 0 (`smooth.yaml:1-8`, `:41-76`).
   Distinguishes CD-flat vs smooth-narrowing philosophies. Evidence needed: a corridor spec (bw(f)
   bounds) validated against listening tests, not just a slope target.
3. **Pareto menu (set-valued output).** Keep several non-dominated designs along trade-offs
   (coverage accuracy vs DI smoothness vs on-axis vs size). The repo has a Pareto engine, but its errors
   are physical **coverage (deg)/ripple (dB)** only (`bo/pareto.py:221-250`), and it is fit on a
   validated cohort, not the full v7 term vector. Distinguishes: whether human choice (not a scalar
   minimum) should end the search.
4. **Utility / preference learning.** Learn weights or a monotone utility from human pairwise judgements
   (e.g. A/B on rendered designs), rather than hand-set weights/tolerances. No such code was found in
   the assigned set (`unverified`: not searched exhaustively).
5. **System/DSP-aware measures.** Score what an EQ cannot fix: seat-to-seat spread, crossover hand-off,
   in-room shape, fine roughness (`tools/analysis/hifi_rescore.py:9-35`, `:80-131`). Evidence: the
   offline rerank in §5.
6. **Staged rejection criteria.** Hard feasibility gates (envelope/throat, solved, finite, `di_source`
   balloon) → soft J → verify-grid confirmation → human selection. The existing `PENALTY_*` and
   `NAN_TERM_FILL` hierarchy is a partial version (`objective/terms.py:18-35`); the verify grid is
   6 points/octave (`brief:52`) vs screen, and `hifi_rescore.py:39-41` prefers verify evidence.

**What a "verified finalist" gate should plausibly require** `[interp]` (no such gate exists in the
assigned code; stated as design criteria, not implemented): (a) a `verify`-grid solve (not screen
rows) with `di_source=="balloon"` (`types.py:168`; AGENTS.md "no checkpoint passes on cuts_estimate");
(b) a recomputed `score_id` from stored response + frozen brief, matching the run's identity
(`dataset/identity_v2.py:50-59`); (c) invariants under ≥2 briefs / a region formulation, so the pick
is not an artefact of one weight vector; (d) a human listening/selection step; (e) explicit recording
that DSP terms were computed from stored responses, not invented.

---

## 4. Zero-GPU reuse matrix

Identity layers (verified): `physical_solve_id` = sha16 of `[design_hash, mesh_hash, solve_hash]`;
`analysis_id` = response checksum + metric method + options; `score_id` = analysis ids + objective
version + scorer code sha + resolved brief + weights/tolerances/gates; `study_id` =
optimizer/cohort/model/acquisition/seeds (`dataset/identity_v2.py:1-13`, `:40-63`). The **response is
the physics anchor**; everything downstream is recomputable only when the response (and its checksum)
is preserved.

Persisted per design (`evaluate.py:1665-1680`): `design.json` (family, params, hash), `status.json`
(ok/terms/key), `response.npz`, `metrics.json`. `response.npz` carries `freqs_hz`, `h_angles_deg`,
`v_angles_deg`, `spl_h_db`, `spl_v_db`, `balloon_dirs`, `spl_balloon_db`, `z_throat` (and MEH channel
arrays when present) (`dataset/record.py:245-274`; `record.py:38-39`). Cut angles are `−90..+90`
(`types.py:113-114`).

| Artifact / field | Reusable at zero GPU under which identity | Blocked by | Status |
|---|---|---|---|
| `response.npz` cut SPL + balloon | Any v7 term using stored f/angles (cov, rip, flat, di, dislope, distd, diag, flat_cv, 8k floor) — objective is pure numpy over the response (`scalar_v7.py:52-53`) | Never blocked for stored support | verified |
| Same, re-scored under new weights/tolerances/brief | New `score_id`, **same** `physical_solve_id` and (if metric method/options unchanged) same `analysis_id` | A changed target/f0/freq grid changes `analysis_id` only if metric options change; a changed brief/weights changes `score_id` only (`identity_v2.py:55-59`) | verified |
| `hifi_rescore` seat/xo/pir/rough/shape | Recomputed offline from `response.npz` (`hifi_rescore.py:173-200`, `:80-131`) | Needs the requested angles on the solved grid (±1.3°, `hifi_rescore.py:64`, `:73-77`); rear approximated by ±90° cuts, not true 180° (`:16-18`) | verified for method; numbers historical |
| `metrics.json` / ndjson `terms` | Re-ranking by new **weights only** if raw arrays also stored (they are); a new metric method/version needs recompute from response → new `analysis_id` | A metric method/version change; missing raw arrays | plausible inference |
| New frequency support (finer or outside ≥18-point screen grid) | — | **Requires a new solve** (frequency grid is a solve input) | verified (grid is solve config, `config.py:1606-1622`) |
| New angles beyond stored H/V cuts / true rear hemisphere | — | **Requires a new solve** or a finer balloon; ±90° cuts cannot yield 180° | verified (`types.py:113-118`) |
| Changed geometry / mesh | — | New `physical_solve_id` (mesh_hash changes) → full re-solve | verified (`identity_v2.py:40-42`) |
| Changed source model (excitation, cap, MEH channels) | — | New drive → new solve; response is source-specific | verified (record stores excitation/network; `record.py:245-258`) |
| Changed symmetry assumption (hv vs axi) | — | Different solved domain → new solve; axisymmetric incompatible with H≠V (`search/campaign.py:122-148`) | verified |
| BO training reuse | Only if cohort gate passes: objective version must equal **4** (`bo/cohort.py:96-97`), `exact_complete`, response-detrended ripple evidenced, resolved target/weights/metric_source present, and all policy fields identical across rows (`bo/data.py:383-387`, `:464-472`, `:657-675`, `:730-749`). No partial pooling. | A v7 run is refused by `cohort.py:96`; mixed brief/weights/grids refused; `morph_exponent`-active designs refused (`bo/data.py:614-627`) | verified |
| Compatible-state vocabulary | `exact_complete` / `partial_unsupported` / `additional_data_or_solve_required` (`identity_v2.py:66-77`) | — | verified |

**Practical consequence `[interp]`:** the entire objective can be re-scored offline from
`response.npz` (that is exactly what `HOME_OSSE_HIFI_RERANK` did), but **only within the stored
frequency and angle support**. Anything that changes physics (geometry, source, symmetry), adds
frequencies, or needs true rear/full-sphere where only ±90° cuts exist is `additional_data_or_solve_required`
— new GPU solves, not a re-score.

---

## 5. Existing evidence review and its scope limits

**HOME_SCORE_AUDIT_2026-11-16** (`docs/queue/HOME_SCORE_AUDIT_2026-11-16.md`):
- Header states it is a read-only scoring/source-intent audit, "not an acoustic certification", and the
  JSON is a queue snapshot to be re-keyed by SHA before use (`:3`). Verified: JSON carries
  `queue_sha256=260a8721…c304`, 28 jobs; limitations = "Fingerprints are audit-specific, not result
  identities … no acoustic certification" (`HOME_SCORE_AUDIT_2026-11-16.json`.
- Effective scoring for the landscape briefs: v7, 350–8000 Hz, 700 Hz XO, 5600 Hz loaded bound, 2×
  freq weight 2500–5500 (`:26`, `:28-34`). Verified against `brief:28-40,58-67` and job[0].score.
- It correctly warns the v8/v9 labels on configs are **not** objective versions (`:26`, `:17`).
- It notes the smooth brief sets V weight 0.5 and `flat_band: scored`, old brief does not (`:33-34`);
  verified against the two YAMLs.

**DSP-aware rerank** (`HOME_SCORE_AUDIT:36-40`; `docs/evidence/HOME_OSSE_HIFI_RERANK_2026-11-16.md`):
- Method: `J_dsp = J_v7 − weighted(flat+flat_cv) + seat/t_seat + 0.5·xo/t_xo + pir/t_pir +
  0.5·rough/t_rough`; passive adds `shape/t_shape` (`audit:38`; `hifi_rescore.py:137-160`).
- Tolerances are **top-decile medians of the sampled cohort**, floor 0.05 dB, "not established
  perceptual thresholds" (`audit:38`; `hifi_rescore.py:142-150`).
- Observed on run `5d1082`, 32 designs: v7 #1 `5c8864decc06` J 3.924 → DSP 8.291, **rank 12**
  (passive rank 11); seed `7de69ffa75e8` J 3.992 rank 2 → 3; Spearman 0.87 (dsp) / 0.89 (passive);
  seat spread 1.10 vs 0.59 dB (`audit:40`; `RERANK:7-14`, `:20-31`) — **historical record**.
- **Scope limits (verified in text):** it *retains* v7 coverage and dislope, so "cannot fix a
  mismatched brief" (`audit:38`); rear is approximated by ±90° cuts; no room/EQ/driver model
  (`:40`); tolerances recalibrate per report so numbers are not comparable across arms (`:40`);
  it "neither changes nor drives the queued objective" (`audit:38`). This is **one run / one brief
  group** — a ranking-sensitivity demonstration, not a universal listening metric `[interp]`.

**QD archive** (`search/cma_me.py`): the measure space is **mean in-band beamwidth H and V**, a fixed
`0–180°` interval (`cma_me.py:71-74`, `:99-100`, `:114-147`; `config.py:39-42`). The grid archive
rewards new cells / better elites (`cma_me.py:1-38`, `:384-405`), and `archive.json` stores the
minimisation J per cell (`:528-582`). So QD diversity is diversity of **achieved coverage**, not of a
goal region or a perceptual criterion; it does not score "distance from 80×50" directly. The archive
refuses non-complete evaluations (`cma_me.py:222-262`), so failed rows never become elites (verified).

---

## 6. Unverified, contradicted, and provenance notes

- **HEAD / dirty-state contradiction (resolved by observation).** Dispatch said HEAD `2c0e2928` with
  four modified files; this pass observed HEAD `d187c06` and a clean tracked tree (tracked changes
  committed by the concurrent lane). Findings here are against **committed** `d187c06` code;
  `targets/scoring_view.py` was uncommitted at dispatch and is committed at `d187c06`
  (`git diff` empty). Status: **contradicted vs dispatch, resolved against working tree**.
- **`scoring_view.py` is display-only.** It "never recomputes or changes J" (`scoring_view.py:1-7`,
  `:32-34`); v7 coverage window reconstruction is `h_lo=f0, v_lo=f0_v, below_mode=cov_below_f0,
  narrow_ratio=cov_narrow_ratio` (`:285-292`), and the 8 kHz floor mirror matches
  `scalar_v7._bw8k_floor_penalty` (`:359-414`). Verified; this is **not** the scorer.
- **`flat` vs `flat_cv` dispersion convention differs.** `flat` uses sample std (`ddof=2`,
  `smoothness.py:116`); `flat_cv` uses numpy's default population std (ddof=0, `scalar_v7.py:374`).
  Same units, slightly different estimator; not documented as intentional anywhere read → **plausible
  inconsistency**, flagged not resolved.
- **`di` uses the full in-band set, not the score band.** `dislope` and `distd` use the score band,
  but `di` and `rip` use `f≥band_lo` (`scalar_v2.py:364-381`; `scalar_v7.py:537-542`). The audit's
  one-line "DI-slope term fits … on the scored band" (`audit:34`) is correct for `dislope` only.
- **`distd` is not residual roughness.** It is `std(DI)` over the score band, so a perfectly linear DI
  rise keeps `distd>0` (`scoring_view.py:61-65`; `scalar_v7.py:537-542`). Any doc implying "DI
  steadiness = smooth DI" is imprecise → **plausible over-reading**.
- **`loaded_hi_hz` / f11 consistency (verified).** `BESSEL_J1P_11=1.8412`, `C_AIR=343`
  (`constants.py:3,13-16`); driver radius 18 mm ⇒ f11 = 1.8412·343/(2π·0.018) ≈ **5584 Hz**, matching
  `loaded_hi_hz: 5600` (`brief:14,37`) within rounding. No contradiction.
- **The 80×50 point is a centre, not a limit.** The brief's own owner quote is a 60-90 H / 40-60 V
  range (`brief:8`), while the scorer uses 80/50 at every scored f. This is the central
  objective-vs-intent gap → **verified fact, interpretation flagged**; resolving it is a goal-shape
  question, not a tolerance tweak.
- **HOME_SCORE_AUDIT "35.8 mm exit" vs `driver.exit_radius_mm: 18.0`.** 18 mm radius ⇒ 36 mm exit,
  consistent with a 1.4-inch driver (`brief:14,18`); the "35.8 mm" is the nominal driver exit, not the
  YAML radius. Consistent, not a contradiction.
- **Historical vs current:** every number in §5 is a **historical record** from 2026-11-16 runs; none
  was re-run here. The code paths in §1–§4 are **current committed** (`d187c06`). Do not mix the two.
- **Not investigated** (outside assigned scope, marked unverified): whether a UTILITY/preference-learning
  implementation exists elsewhere in the repo; the exact balloon angular resolution; whether any queue
  job actually ran on the post-`d187c06` code.

---

### Bottom line (facts only)

1. v7 is a normalised weighted sum of nine scalar terms; no hard per-frequency constraint survives
   except the one-sided 8 kHz floor and the `load` window minimum.
2. The "80×50" target is exact and frequency-flat where scored (f≥700, symmetric V, V half-weighted),
   while the owner's accepted region is explicitly 60-90 H / 40-60 V.
3. Flat DI is soft (slope tolerance 9), lobes beyond the coverage window and off-axis leakage are
   largely unscored; listening-window/SPDI are report-only.
4. Reuse is response-anchored: objective and DSP terms recompute at zero GPU within stored
   frequency/angle support; geometry/source/symmetry/new-frequency changes need new solves.
5. The BO/cohort gates are strict and currently v4-only; v7 evidence cannot be pooled without a new
   score identity and a version-compatible cohort.
6. The rerank evidence (v7 #1 → DSP #12) is a single-run sensitivity demonstration, not proof of a
   universal perceptual ranking.
