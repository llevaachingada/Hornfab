# Senior verdicts on HANDBACK_LOCAL_2026-11-18 §2.1 and §2.2 (cloud Fable senior, 2026-11-19)

Base: `main` @ `7b2107b` (= `hornfab-all-2026-11-18` @ `bc22d6c` + merge). CPU only, committed data
only. Every number below was recomputed in this session from the files cited.

## Verdict 1: rho20 vs the "rho inert" park (G5)

**Keep the park. Rewrite the two §10.2 rows as below. Do not move the 3° threshold.**

| Claim | Result | Basis |
|---|---|---|
| rho20 meets the U3 rule as written | TRUE, barely: H +3.12° in 2.5-5.5 kHz, V +0.56° (< half) | `throat_hv_2026-11-18/authority_A_vs_v8.json` [verified] |
| The margin is real | NO. The band mean rests on 6 solved frequencies; per-frequency dH = 1.88 / 2.33 / 2.33 / 4.39 / 3.63 / 4.17°, sd 1.07, **SE 0.44°**. 3.12 is 0.27 SE above the line | recomputed from `authority_A_vs_v8/hv_beamwidth_{control,rho20}.csv` [verified arithmetic] |
| The move is the rho knob's | NO. rho's own swing (A_r15 → A_r20) moves the top band **+1.28° H / +0.26° V**. The 3.12° is v8 → A (construction change + rho), not rho alone | same CSVs, `rho15` vs `rho20` [verified] |
| It is mesh-backed | NO. The A family parent refuses at epw 12; no mesh floor exists for it | `.b1/b1_mesh_feasibility.md`; G5 rec. point 4 [primary] |
| It buys J | NO. A_r20 − v8 = +0.024 J under v7 (worse, tie under either floor) | G5 rec. point 2; `lane_bests_side_by_side.csv` [verified] |
| Direction | H widens (≈76° → 80°) | CSVs [verified]. Toward the 80° H target, which is why J does not punish it, but not a gain either |

**Reading.** "rho inert in this envelope" stands for the rho knob itself (1.28° < 3°). What
crossed the line is the bundled v8 → A_r20 comparison, by less than half a standard error, with no
mesh floor, at zero J benefit. None of those change the park.

**§10.2 rows to write (replace the pending text):**
- `A: v8 → A_r15` = no authority [verified, per band; max 1.84° H].
- `A: v8 → A_r20` = **borderline** authority, H 2.5-5.5 kHz +3.12° (SE 0.44°, 6 freqs, no mesh
  floor); rho-only swing r15 → r20 = 1.28° H → **rho knob inert** [verified]. ΔJ tie. Park stands.

**Borderline-band policy (U3, going forward).** Keep 3° as the predeclared threshold (moving it after
seeing data would be a post-hoc goalpost change). Add an evidence-grade label instead:
- *Authority* = band-mean move ≥ 3° **and** (move − 3°) ≥ 1 SE of the per-frequency deltas in that band.
- *Borderline* = meets 3° but not the 1 SE margin. A borderline result changes no decision on its
  own; it needs a denser frequency grid in that band or a mesh-floor check first.
- Report SE and frequency count next to every authority call. (vt_460 at +32.32° is unaffected.)
- Code change, if wanted: `tools/analysis/u3_authority.py` emits `se_deg` and `grade`; not done here
  (owner/local lane owns the run; small, CPU-only, testable on the committed CSVs).

## Verdict 2: v7 floor 0.310 vs 0.13

**Re-pin: stored-J tie calls under v7 use 0.31 J (combined 0.3105). 0.13 stays valid only for
dense-scored J.** The two numbers measure different things; neither is a bug.

| | 0.13 (D8 / A4 / N3) | 0.310 (`floor` subcommand) |
|---|---|---|
| What J | **dense-232 log-grid J** (stored response PCHIP-interpolated, then scored) | **stored-grid J**, exactly as runs and rankings carry it |
| Pairs | 58 screen/verify, BO-vs-CMA study cohort only | 257 screen/verify, all home-brief runs |
| Statistic | sd(dense-from-18 − dense-from-29), best 28 = 0.126 | sd(stored screen − stored verify), top 28 by verify J = 0.310 |
| Contains grid-weighting shift | no (removed by the dense definition) | **yes** (A4: sd 0.197 at the top by itself) |
| Source | `A4_GRID_INDEPENDENT_SCORE.md` headline 3 + Numbers table [primary] | `results/floor_v7_summary.json` [primary] |

Why 0.31 is the right pin for current tie calls:
1. Every J on the critical path (lane bests, rescore columns, G5 deltas, WP 4.4 success test) is a
   **stored-grid** J. A4 itself says dense J "is not comparable with any stored J". Pinning a
   dense-J floor onto stored J was a transfer error. The senior review already flagged the family of
   mistake (C-3: a floor belongs to one identity and one frequency count).
2. A4's own stored-grid row on its 58 pairs was already 0.169 at the top, not 0.13. The larger,
   multi-family 257-pair population lifts it to 0.31 [inferred: population; not decomposed here].
3. v10 (0.468) and v10_slope5 (0.486) were measured by the same command. Same protocol across
   identities is the only way the three floors can be read side by side.
4. Conservative direction: it can turn a claimed win into a tie, never the reverse.

Caveats [inferred]: 0.31 is the sd of a screen-minus-verify *difference*; a verify-vs-verify call
on identical grids has less error than that, so 0.31 is an upper bound there. The plan's "12/25
frequencies" wording for v7 disagrees with A4's 18 vs 29 [unverified which is right for the 257
pairs]. Neither caveat flips any call below.

**What the re-pin changes (v7 lane bests, `lane_bests_side_by_side.csv`):**

| Call | Δ J (v7) | Under 0.13 | Under 0.31 |
|---|---|---|---|
| ext_throat v7 leader vs A_r15 | 0.586 | win | win |
| A_r15 / v8 / A_r20 cluster | ≤ 0.044 | tie | tie |
| **fold_warm v7 vs the throat cluster** | 0.203-0.246 | **behind** | **tie** |
| morph v8 and below vs cluster | ≥ 0.79 | behind | behind |
| G5: A vs v8; Phase 3 vs B_o50 | 0.019-0.090 | tie | tie |
| B vs A (throat block) | ~2.7-3.2 | behind | behind |

Downstream edits implied:
- **fold_warm v7 joins the throat cluster as a tie.** It is already in the B6 matched-rerun set, so
  no queue change; the B6 readout must not call it "behind".
- **WP 4.4 vt probe success test** moves from > 0.1302 J to **> 0.3105 J** over the control.
- **D8 continuation rule** (last-100-eval improvement > floor) uses 0.31 for v7.
- Every tie call cites "v7 stored-J floor 0.31 (protocol basis)" from here on.

## Not done here (rest of §2)

§2.3 judgment-call checks and §2.4 (steer_early/late intended planes) are not reviewed in this pass.
