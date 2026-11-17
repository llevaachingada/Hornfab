# A3 — E1 follow-up: full J, whole-surface descriptors, term-level error

Run: 2026-11-17, started at HEAD `8562e1b`. Read-only, CPU only; no solve, no mesh build, no solving CLI,
no pytest, no git mutation, no process control. (HEAD moved to `ad6937b` during the run: docs, a
skill, NOTES and one example config only — no source, objective, metrics or stored run changed; all
inputs used here are the stored rows and records.) Scripts: `scratch/fable_architecture/.a3/`.
Inputs: `.fable/rows.pkl` (3,802 rows), `.e1/descriptors.pkl` (3,410 extracted rows; **2,595 CD**),
`.n1b/build/*.npz` (70 records, 65 stations × 61 azimuths, contract v2), `.tmp/fable_replay_harness.py`.
All writes are under `.a3/` plus this report.

**Objective version.** All ten E1 lanes run **objective v7**. The lane label
`hl__ath_tritonia_landscape_v9` is a geometry/config version, not an objective version; no v9
objective exists in this pool. J is therefore never compared across versions. (E1's earlier proxy
result for that lane was also v7.)

## Headline

1. **With parity-exact full J as the truth, E1's "no advantage" survives and hardens.** Median lane
   reveals (10 lanes, 10 starts, 8-design initial set, batch 8): score head 18.5, same head on
   geometry descriptors 18.25, E1 curve head 24.0, response-functional head 18.25, actual history
   87.25, random 55.25. Part A, Part B and Part C all fail their stated lines.
2. **The identified cause of the earlier proxy-level picture is the proxy objective, not the pool or
   the two-plane input.** The *same* curve selector needs 10.0 median reveals when judged on the
   coverage+DI proxy and 24.0 when judged on full J; the score head goes 9.5 → 18.5. The proxy-best
   design is outside the full-J top decile in 4/10 lanes (one at rank 145/158), and the coverage+DI
   part is only 28.5 % of mean J.
3. **The error sits mainly in `diag` and `dislope`, then `cov` and `load`.** For the full-J
   response-functional head (27-d descriptor → 9 terms), mean shares of absolute weighted term error:
   `diag` 0.287, `dislope` 0.228, `cov` 0.211, `load` 0.105, `flat_cv` 0.061; all others ≤ 0.033.
   The E1 curve head's own error is in `cov` (weighted RMSE 0.253 vs 0.040 for DI). Whole-surface
   descriptors are built and versioned (**A3-WS-v1, 404 numbers, 60 records**) but the available
   record set gives only 10 designs per lane, so that arm is inconclusive.

## Gates and method

**Parity gate (passed).** Regenerating every CD row through `metrics_parity` + `objective_v7` gives
`max |ΔJ| = 0.0` and `max |Δterm| = 0.0` on all **2,595** CD rows (1,861 in the ten lanes). Stored
`terms` values are already tolerance-normalised; `J = Σ_k w_k t_k` holds to 1.4e-14.
`prep.log`, `prep_all.log`, `.a3/prep.pkl`, `.a3/all.pkl`.

**E1 reproduction gate (passed).** Re-running the *same* selectors with E1's coverage+DI proxy as the
truth reproduces E1's Part A medians exactly — scalar **9.5**, response **10.0**, actual **29.75** —
and E1's Part C numbers exactly (OSSE 51.5 %/73.2 %, GRID 36.4 %/71.2 %, GEN-FF 0 %/0 %). The replay
machinery is therefore E1-compatible; the differences below come from the truth, not the code.
(`.a3/replay_proxy.json`; random differs, 13.5 vs 12.25, through RNG use only.)

**Selectors** (all refit every 8 reveals; only revealed rows train unless marked `tr`):

| name | input | output | score |
|---|---|---|---|
| `score` | lane knobs | full J | predicted J |
| `score_desc` | 27-d mesh descriptor | full J | predicted J |
| `resp_curve` | 27-d mesh descriptor | `bw_h`,`bw_v`,`di` (54) | E1 coverage+DI proxy |
| `resp_term` | 27-d mesh descriptor | the 9 normalised v7 terms | `Σ w_k t_k` (exact linear form) |
| `actual` / `random` | historical / shuffled order | — | — |
| `resp_*_tr` | + rows from the other engine groups | as above | as above |

Curve transfer trains on all 3,410 descriptor rows (all briefs, as E1 did); term transfer trains on
the 2,595 CD rows only, because the normalised terms are brief-specific.

`resp_term` is the full-J extension of "response modelling": it predicts every scored response
functional rather than raw SPL curves. It is deliberately generous to the response hypothesis — no
proxy loss at all. It is brief-specific (the normalised terms are v7-CD quantities), so its transfer
test is same-brief only. `resp_curve` is E1's model, used unchanged.

Hit rule: first revealed design with `J ≤ min(J_lane) + 0.1`, floor of 8 reveals, exactly as E1.
Secondary outcome: first design in the lane's full-J top decile. Both are reported; neither pass line
is moved.

**Sibling rule.** Part A never trains across lanes, so twins cannot leak into their own lane. Part B
and Part C train strictly on other engine groups; `.e2/sibling_seeds.txt` groups ath tritonia v8/v9,
biradial v7/smooth, ext-throat v7/v8 and rf-section v7/smooth, and none of those groups spans engine
groups (as E1 found), so named siblings are never in the training set. Part C holds each engine out
whole, so twins in the held-out engine are held out together.

## Result table — Part A (within lane, full-J truth)

Denominators: 10 lanes, 10 random starts each = 100 starts per selector; 8 reveals per batch; floor 8.
`hit 0.1` is the number of designs within 0.1 J of the lane best (the target set). `proxy-best rank`
is the full-J rank of the design that minimises the proxy.

| Lane | n | best J | hit 0.1 | proxy ρ | proxy-best rank | score | score_desc | resp_curve | resp_term | actual | random |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ath tritonia v8 | 112 | 5.692 | 1 | 0.947 | 6 | 19.5 | 16.0 | 26.5 | 15.0 | 66.0 | 58.0 |
| ath tritonia v9 | 120 | 5.015 | 2 | 0.765 | 11 | 18.5 | 16.0 | 22.0 | 17.5 | 76.5 | 52.5 |
| ath twinray v8 | 161 | 4.914 | 1 | 0.796 | 10 | 56.0 | 28.0 | 26.0 | 35.0 | 135.0 | 91.0 |
| biradial v7 | 309 | 6.447 | 5 | 0.810 | 127 | 16.0 | 18.5 | 19.0 | 22.5 | 132.5 | 39.5 |
| crowe panel home | 158 | 16.918 | 2 | 0.309 | 145 | 18.5 | 20.0 | 79.0 | 19.5 | 38.0 | 58.5 |
| crowe × osse | 202 | 5.344 | 6 | 0.653 | 14 | 8.5 | 9.0 | 15.0 | 8.5 | 61.0 | 10.5 |
| ext throat hvlaw | 137 | 3.103 | 1 | 0.947 | 8 | 32.5 | 28.0 | 26.0 | 30.0 | 44.5 | 83.5 |
| osse rrect fold | 248 | 3.621 | 6 | 0.583 | 50 | 18.0 | 18.0 | 14.0 | 14.5 | 98.0 | 44.0 |
| rosse rect cd | 254 | 4.563 | 2 | 0.908 | 69 | 29.5 | 24.0 | 45.5 | 19.0 | 188.5 | 71.5 |
| rr crowe es600 | 160 | 22.542 | 2 | 0.620 | 1 | 18.5 | 15.5 | 16.5 | 13.0 | 123.0 | 23.0 |
| **Median of lanes** | | | **2** | **0.78** | | **18.5** | **18.25** | **24.0** | **18.25** | **87.25** | **55.25** |

E1's comparator, for orientation only (proxy truth): scalar 9.5, response 10.0, actual 29.75.

**Floor and power.** The initial 8-design set already contains a hit in **15/100** starts, so those
starts give reveals = 8 for every selector. The hit sets are tiny (1–6 designs; median 2), far below
any model's achievable error (below). Restricting to the **85 informative starts** removes the floor:
median reveals score 12.5, score_desc 13.8, resp_curve 18.0, resp_term 13.0, actual 99.5, random 49.0
(`.a3/extra.py`). The top-decile outcome is degenerate (median 8 for every selector, because 8 random
draws from 112–309 designs usually contain a top-decile design); it is not used for any verdict.

## Result table — proxy truth vs full-J truth (paired)

Same selectors, same starts; only the truth/threshold changes. `score` and `score_desc` are
retargeted at whichever objective is the truth (a score model must predict the objective it is
judged on); `resp_curve` is byte-identical in both runs, so its delta is a clean measurement of the
objective change.

| Lane | score proxy→J | Δ | curve proxy→J | Δ |
|---|---|---:|---:|---:|
| ath tritonia v8 | 13.5 → 19.5 | +6.0 | 16.0 → 26.5 | +10.5 |
| ath tritonia v9 | 8.5 → 18.5 | +10.0 | 8.5 → 22.0 | +13.5 |
| ath twinray v8 | 20.5 → 56.0 | +35.5 | 21.5 → 26.0 | +4.5 |
| biradial v7 | 8.0 → 16.0 | +8.0 | 8.0 → 19.0 | +11.0 |
| crowe panel home | 10.5 → 18.5 | +8.0 | 11.5 → 79.0 | +67.5 |
| crowe × osse | 8.5 → 8.5 | 0.0 | 8.5 → 15.0 | +6.5 |
| ext throat hvlaw | 29.5 → 32.5 | +3.0 | 22.5 → 26.0 | +3.5 |
| osse rrect fold | 8.0 → 18.0 | +10.0 | 8.0 → 14.0 | +6.0 |
| rosse rect cd | 8.0 → 29.5 | +21.5 | 8.0 → 45.5 | +37.5 |
| rr crowe es600 | 14.0 → 18.5 | +4.5 | 16.5 → 16.5 | 0.0 |
| **Median** | **9.5 → 18.5** | **+8.0** | **10.0 → 24.0** | **+8.5** |

## Result table — Part B (other-engine data, medians)

| Lane | curve | curve+transfer | term | term+transfer |
|---|---:|---:|---:|---:|
| ath tritonia v8 | 26.5 | 10.5 | 15.0 | 10.0 |
| ath tritonia v9 | 22.0 | 22.0 | 17.5 | 14.0 |
| ath twinray v8 | 26.0 | 37.0 | 35.0 | 81.0 |
| biradial v7 | 19.0 | 48.5 | 22.5 | 33.0 |
| crowe panel home | 79.0 | 79.5 | 19.5 | 37.0 |
| crowe × osse | 15.0 | 9.0 | 8.5 | 8.5 |
| ext throat hvlaw | 26.0 | 20.5 | 30.0 | 22.0 |
| osse rrect fold | 14.0 | 30.0 | 14.5 | 36.5 |
| rosse rect cd | 45.5 | 43.0 | 19.0 | 31.5 |
| rr crowe es600 | 16.5 | 22.5 | 13.0 | 25.0 |
| **Median** | **24.0** | **26.25** | **18.25** | **28.25** |

Curve-head transfer: **+0.25 median (+1 %)**. Term-head transfer: **+11.2 (+62 %)**. Neither is the
required 20 % reduction; the curve head improves in three lanes (ath tritonia v8, crowe × osse,
ext-throat), is neutral in ath tritonia v9, and worsens in the other six.

## Result table — Part C (held-out engine, full-J truth)

Denominators: held-out CD pool per engine (n), true full-J top decile (top_n). Train: curve head
2,887/1,493/2,440 descriptor rows (all briefs, as in E1); term head 2,286/1,279/1,625 CD rows.
The last column is the same curve head judged on the proxy truth — it reproduces E1 exactly.

| Held-out engine | n | top_n | head | top-10 % | top-25 % |
|---|---:|---:|---|---:|---:|
| GEN-FF | 309 | 31 | score_desc | 0.000 | 0.065 |
| | | | resp_term | 0.000 | 0.000 |
| | | | resp_curve (J truth) | 0.000 | 0.032 |
| | | | resp_curve (proxy truth) | 0.000 | 0.000 |
| GRID | 1,316 | 132 | score_desc | 0.326 | 0.508 |
| | | | resp_term | 0.288 | 0.523 |
| | | | resp_curve (J truth) | **0.455** | **0.788** |
| | | | resp_curve (proxy truth) | 0.364 | 0.712 |
| OSSE | 970 | 97 | score_desc | 0.000 | 0.031 |
| | | | resp_term | 0.000 | 0.010 |
| | | | resp_curve (J truth) | 0.010 | 0.031 |
| | | | resp_curve (proxy truth) | **0.515** | **0.732** |

Chance at top-25 % is 25 %. **The deciles are lane-concentrated under both truths**, so Part C is
closer to a lane-ranking test than a within-lane design ranking: full-J deciles are 100 % biradial
(GEN-FF), 77 % rosse-rect (GRID), 76 % osse-rrect (OSSE); proxy deciles are 100 % biradial, 87 %
rosse-rect, 57 % ath-tritonia-v9. The change from proxy to full J therefore changes *which lane* the
held-out ranking should favour, and the OSSE collapse (51.5 % → 1.0 %) is the clearest instance.

## Result table — where the error sits (10-fold CV, 27-d descriptor head)

Denominators: 10 lanes, 2,595 rows, 10 folds each. `norm RMSE` is the median over lanes of the
normalised-term RMSE (tolerance units). `error share` is the mean over lanes of
`|w_k·err_k| / Σ|w·err|`, i.e. where the composed J error comes from. `J share` is the term's mean
contribution to J (per-lane shares sum to 1).

| Term | w | median R² | norm RMSE | error share | J share |
|---|---:|---:|---:|---:|---:|
| cov | 1.0 | 0.73 | 0.201 | **0.211** | 0.201 |
| rip | 1.0 | 0.65 | 0.037 | 0.024 | 0.026 |
| di | 0.3 | 0.84 | 0.127 | 0.031 | 0.084 |
| dislope | 1.0 | 0.81 | 0.194 | **0.228** | 0.185 |
| flat | 0.5 | 0.57 | 0.077 | 0.033 | 0.041 |
| load | 1.0 | 0.81 | 0.153 | **0.105** | 0.180 |
| distd | 0.5 | 0.68 | 0.049 | 0.021 | 0.032 |
| diag | 1.0 | 0.74 | 0.367 | **0.287** | 0.193 |
| flat_cv | 1.0 | 0.60 | 0.077 | 0.061 | 0.059 |

Composed J accuracy of this head: median lane RMSE **0.63**, median |ΔJ| **0.25**, median Spearman
**0.88** (lane range 0.82–0.95). It is a good ranker and a poor 0.1-unit estimator. Leave-one-out
prediction of each lane's *best* design is off by **+0.13 to +1.44 J** (median +0.48), i.e. by more
than the 0.1 hit radius in every lane.

**Curve head (E1's model), same folds.** It models `cov` + `di` only. Its own weighted error is
concentrated in **cov** (weighted RMSE median **0.253**, lane range 0.036–1.10) and almost absent in
DI (**0.040**, 0.002–0.10); predicted-vs-true proxy ρ median 0.844. The two terms it models carry
**28.5 % of mean J** (cov 20.1 %, di 8.4 %); the seven terms it does not model carry **71.5 %** by
the same mean-share arithmetic (the lane median of the per-lane ratio is 72.9 %, range 53.5–79.9 %).
The truth-level gap `J − proxy` is exactly the seven non-proxy weighted terms (residual ≤ 7.1e-15)
and is **2.50–15.78 J** per lane (median 5.94).

## Whole-surface descriptors (A3-WS-v1) and the input question

**Descriptor set (explicit, versioned):** 404 numbers, all lengths mm, angles degrees:
32 arc-length stations × (`r_H`,`r_V`,`r_45`) half-widths, 32 × (`z_H`,`z_V`,`z_45`) axial
coordinates, 32 × (`ang_H`,`ang_V`,`ang_45`) wall half-angle from the +z axis (atan2(dr,dz); >90 =
rolled), 32 × (section `area`, `aspect`=W/H, `shape`=area/(W·H)); 20 scalars: mouth W/H, inner depth,
outer envelope W/H/D, wall thickness, throat r_H/r_V/area/angles, H lip curvature radius, lip wrap
angle, rollback depth, forward-wall end fraction, non-monotone-z flag, sector angle, n_φ, n_s.
Source: the N1b canonical records at 65 × 61 (contract v2), inner sheet; outer used for the envelope.
Version `A3-WS-v1`. Script `.a3/ws_desc.py`; records `.a3/ws_desc.pkl`.

**Coverage of the A1 record set.** 70 records exist; **60 usable** after excluding
`hl__lecleach_hv_landscape_smooth_v7` (N1b: stored meshes are not rebuildable at HEAD — the same
provenance failure as the Klangfilm digest class, but with no digest to flag it). The Klangfilm
records are the ten digest-verified N1b replacements; they are built but **excluded from the J
comparison** because that lane runs the `smooth` brief, so its J is not comparable with the CD lanes.
Comparable set: **5 CD lanes × 10 designs = 50**, of which four lanes (40 designs) are E1 Part A
lanes. `rf__section_axial_home_v7` has 51 CD rows and was below E1's 100-row lane floor.

**Test.** Within-lane leave-one-out and leave-one-lane-out, predicting the 9 terms and J; E1's
ExtraTrees recipe, ridge (α=1), and standardised 1-NN. Medians over the 5 lanes:

| Feature set | model | J, within ρ | J, cross-lane ρ | terms, within ρ | terms, cross-lane ρ |
|---|---|---:|---:|---:|---:|
| A3-WS-v1 (404) | ExtraTrees | 0.10 | 0.28 | **0.53** | 0.15 |
| old 27-d | ExtraTrees | −0.41 | 0.14 | **−0.48** | 0.20 |
| A3-WS-v1 (404) | ridge | **0.35** | 0.30 | 0.35 | 0.30 |
| old 27-d | ridge | 0.19 | 0.36 | 0.19 | 0.36 |

Descriptor spread (standardised, within/between lane): WS 10.8/29.7, old 2.5/7.4 — the WS set is far
more discriminative. **This arm cannot settle the input question.** It is directionally positive
in-lane (terms ρ 0.53 vs −0.48; J 0.10 vs −0.41; ridge 0.35 vs 0.19) and mixed across lanes, but with
10 designs per lane and 5 lanes the median has no meaningful confidence interval. A replay on WS
descriptors is impossible: only 10 designs per lane exist, below the 8-design initial set + any
selection.

## The four explanations in handoff §5 item 4

| Explanation | Evidence | Standing |
|---|---|---|
| **(a) The proxy objective** | Same selector: 10.0 → 24.0 median reveals when the truth changes proxy → J; score head 9.5 → 18.5. Proxy ρ with J 0.31–0.95 (median 0.78); proxy-best design outside the full-J top decile in 4/10 lanes (worst rank 145/158); `J − proxy` 2.50–15.78 J, exactly the seven non-proxy terms. Part C: proxy truth 51.5 %/73.2 % (OSSE) → J truth 1.0 %/3.1 %. | **Supported as the main cause of the proxy-level picture.** It does not reverse the no-advantage conclusion: at full J the response heads still do not beat the score head. |
| **(b) The visited-design pool** | Hit sets are 1–6 designs (median 2) at the brief's 0.1 radius; 15/100 starts are decided by the initial 8; actual history is worse than random (87.25 vs 55.25; above-floor 99.5 vs 49.0), so the pool is picked over. No new design can be created without a solve. | **Cannot be distinguished from (d).** This replay cannot separate "the historical pool has no remaining response-model upside" from "response modelling has no upside". |
| **(c) The two-plane/two-profile inputs** | The same 27-d input supports a much better full-J head (term head 18.25 vs curve head 24.0), so the input is not the dominant loss in E1. WS descriptors (adds 45° plane, section, termination) improve in-lane term ρ 0.53 vs −0.48 and J ρ 0.10 vs −0.41, but cross-lane transfer is mixed and n = 10/lane. | **Not supported as the primary explanation; unresolved.** Extra surface information may help, but this record set cannot quantify it. |
| **(d) A real absence of benefit** | Even the most generous response-level head — every scored term, no proxy loss — ties the score head (18.25 vs 18.5) and is nowhere near half. Transfer does not help (+1 % curve, +62 % term). Part C full-J recovery fails two of three engines (GEN-FF 3.2 %, OSSE 3.1 % at top-25). | **Survives as the reading of this replay, with (b)'s caveat.** It is "not demonstrated in this historical pool at full J", not "prospectively absent". |

**Cannot be separated here:** (b) from (d), because no unbiased pool exists without new solves. (c) is
formally unknown: the descriptor test is under-powered, and a 404-number descriptor on a 10-design
sample is not a fair trial of the idea.

## Verdict against E1's stated lines

- **Part A** (response needs at most half of score **and** actual, median lane): **not met.** E1
  curve head 24.0 vs score 18.5 (needs ≤ 9.25) and actual 87.25 (needs ≤ 43.6). Full-J response head
  18.25 vs score 18.5 (needs ≤ 9.25). No lane meets both halves.
- **Part B** (other-engine data reduces reveals by ≥ 20 %): **not met.** Curve +0.25 median (+1 %);
  term +11.2 (+62 %). Transfer is beneficial in only 3/10 lanes for the curve head (one neutral).
- **Part C** (≥ 40 % of the true best decile in the model's top 25 %, two of three engines):
  **not met.** Curve head reaches the line only for GRID (78.8 %); term head only for GRID (52.3 %).
  GEN-FF 3.2 %/0 % and OSSE 3.1 %/1.0 % are at or below the 25 % chance line.
- **Failure criterion** ("(b) is not clearly faster than (a) in Part A, and Part C is at chance"):
  **met.** Under the proxy truth E1's Part C numerical screen passed for two engines, so E1's
  composite failure criterion was not fully met. Under full J it is.
- **E1's own conclusion is not overturned; it is strengthened for the objective E1 did not test.**
  E1 said its result was proxy-level evidence. At full J, the "no advantage" answer is the same and
  the two-engine Part C success disappears.

## What failed / what is unknown

- **The whole-surface descriptor arm cannot be run as a replay.** Only 10 designs per lane are in the
  A1/N1b record set; the ten E1 lanes overlap it in only four lanes. `lecleach` is excluded (N1b
  cannot rebuild it at HEAD); Klangfilm is built but not J-comparable (different brief). No
  conclusion about input sufficiency can be drawn from 50 designs.
- **The 0.1 hit radius is below the models' resolution.** The full-J term head's median |ΔJ| is 0.25
  (range 0.03–1.34) and its leave-one-out error at the lane-best design is +0.13 to +1.44 J. The
  hit sets are 1–6 designs. Reveal counts therefore measure luck plus ordering, and 15 % of starts
  are pure floor. This is a property of the stated criterion, not a changed pass line.
- **Part C's decile is lane-dominated under both truths.** The clean statement is about which lane
  the model ranks first, not about within-lane design ranking.
- **The term head is brief-specific.** It cannot transfer across briefs, unlike the curve head. Its
  Part B result is a same-brief cross-engine test only.
- **Descriptor provenance.** A3-WS-v1 is the generator's surface at HEAD (contract v2), not the
  stored mesh. N1b records the mesh-vs-generator gap for Crowe (≤ 1.64 mm) and rolled (≤ 0.70 mm);
  for those lanes the descriptor describes the design, not the solved surface.
- **No acoustic, prospective or solve-based claim.** Nothing here creates a design or solves one.

## What this does not prove

- That response modelling cannot help a *fresh* pool or a prospective campaign. That needs B4 (40
  solves: two lanes, top-10 picks and 10 random each) or B6 (matched-budget reruns), owner approval.
- That the term-level errors (`diag`, `dislope`, `cov`) are irreducible, or that a different model
  class (e.g. a physical parameterisation of the diagonal and slope) could not reduce them.
- That whole-surface descriptors are unhelpful. The test was under-powered by construction.
- That the 0.1-J hit radius is the right operational definition of success. It is E1's stated rule.
- Anything about acoustic discovery, family quality, or protected lanes.

## Next action enabled

1. **Do not promote the response-model spine** on this evidence. Use full-J parity and the full term
   vector for any future "response vs score" replay; the coverage+DI proxy overstates the response
   model and overstates cross-engine recall (OSSE 51.5 % → 1.0 % on the same model).
2. **The decisive next test is a fresh pool:** B4 — two lanes, 10 response-head picks and 10 random
   each, 40 solves, owner approval. A cheap pre-step is to extend the A1/N1b record set to ≥ 50
   designs for the four overlapping lanes (CPU-only generator sampling, no solves) and rerun
   `.a3/ws_test.py`; that would give the descriptor arm its first real power.
3. **Report to the scoring workstream (A4/S1):** the proxy-best design's full-J rank spans 1–145, it
   falls outside the full-J top decile in 4/10 lanes, and `J − proxy` is 2.5–15.8 J; any replay that
   uses the proxy should say so explicitly, as E1 did.

## Reproduce

```powershell
# from C:\Users\hunte\Hrns\hornlab-search   (run started at 8562e1b; HEAD was ad6937b at write time)
git rev-parse --short HEAD
.venv\Scripts\python.exe scratch\fable_architecture\.a3\prep.py       # ten-lane parity table
.venv\Scripts\python.exe scratch\fable_architecture\.a3\prep_all.py   # all 2,595 CD rows, parity gate
.venv\Scripts\python.exe scratch\fable_architecture\.a3\replay.py 10  # Part A/B/C, full-J truth
.venv\Scripts\python.exe scratch\fable_architecture\.a3\replay_proxy.py  # E1 reproduction gate
.venv\Scripts\python.exe scratch\fable_architecture\.a3\terms.py      # term error decomposition
.venv\Scripts\python.exe scratch\fable_architecture\.a3\head_error.py # curve-head decomposition
.venv\Scripts\python.exe scratch\fable_architecture\.a3\ws_desc.py    # A3-WS-v1, 60 records
.venv\Scripts\python.exe scratch\fable_architecture\.a3\ws_test.py    # descriptor-arm tests
.venv\Scripts\python.exe scratch\fable_architecture\.a3\extra.py      # floor-excluded + paired tables
.venv\Scripts\python.exe scratch\fable_architecture\.a3\summarize.py  # report tables
```

Runtime: prep 5 min + prep_all 7 min + replay 4 min + proxy 2 min + terms/head/WS 2 min. No file
outside `scratch/fable_architecture/` was written; `runs/`, `examples/`, `hornlab_search/` and
`tools/` were read only.
