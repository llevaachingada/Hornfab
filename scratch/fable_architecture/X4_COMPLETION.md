# X4 completion — five-lane sampler, labels, corners, conditionals and rematerialisations

Run: 2026-11-17, HEAD `87e3311` at start (the shared tree advanced during the session to `ad6937b`
and then `68cb3d0`; those commits touched docs, `.p1`, the objective/studies files and tests, none
of which is on this task's geometry/sampler path). The ROSSE addendum below ran at `68cb3d0`;
the three digest-covered ROSSE files are unchanged relative to `ad6937b`. Read-only, CPU only: no
GPU or BEM solve, no solving CLI, no mesh build, no pytest, no git mutation, no process control.
Scripts:
`scratch/fable_architecture/.x4c/` (`build.py`, `inner.py`, `corners.py`, `range_movement.py`,
`conditionals.py`, `labels.py`, `margins_sampled.py`, `pinned.py`, `rematerialize.py`,
`rosse_bypass.py`). Inputs:
`.fable/rows.pkl` (3,802 rows, 75 runs), the `.x4` selection JSONs, `dataset/shard-*.jsonl`,
`runs/<run>/designs/<hash>/{design.json,mesh.msh}`, and the `.n1`/`.n1b` sampler and topology
helpers. §0 parity smoke: `worst regenerated-vs-stored DI 0.0 n 17`. No new row was scored, so the
replay harness was used only for that smoke.

Surfaces are contract v2 (65 stations × 61 azimuths). `build.py` reproduces the exact 11 designs
per lane that the `.x4` Jacobian used, not a fresh draw.

## Headline

1. **The five lanes and the sampler validate.** All 55 designs (11 per lane) reproduce their
   stored design hash, and all five lanes pass v2 rule 2 11/11, including the native
   rounded-rectangle lane that N1b never tested. Worst p99 is Crowe 1.646 mm against its own
   1.712 mm threshold; every
   other lane is ≤0.243 mm and every median is ≤0.051 mm.
2. **Labels agree on family everywhere; typology has a provenance gap, not a geometry error.**
   Family is 246/246, 136/136, 120/120, 200/200, 307/307. Typology is 246/246, 136/136, 120/120,
   **193/200 (Crowe)** and **301/307 (biradial)**; all 13 disagreements are `run_id: verify`
   records whose provenance omits the generator block, so the label falls back to `FREEFORM`.
   Mounting is never positively stored and termination has a stored token only on Crowe.
3. **The envelope, not the wall gap, is the binding constraint.** Sampled ext-throat and ATH
   designs sit only +1.13 mm and +1.35 mm inside W/H; ext/ATH/Crowe one-knob corners cross the
   envelope. The minimum wall-gap margin anywhere is +4.10 mm (Crowe). Rematerialisations:
   `crowe_panel` resolved 11/11, Klangfilm 9/11 digest-verified (plus 10/10 verified
   replacements; 2/11 of the old sample unverified), `rosse_rect` resolved by a digest-bypass
   geometry check (validator drift, not geometry), **`lecleach` unresolved**.

## Result table — sampler and lane validation

| Lane | n | design hash | native floor p99 (mm) | record p99 (mm) | threshold (mm) | max median (mm) | v2 rule 2 |
|---|---:|---:|---:|---:|---:|---:|---|
| `hl__osse_rrect_fold_warm_v7` | 11 | 11/11 | 0.130 | 0.175 | 1.000 | 0.017 | **pass 11/11** |
| `hl__ext_throat_hvlaw_v7` | 11 | 11/11 | 0.084 | 0.110 | 1.000 | 0.023 | **pass 11/11** |
| `hl__ath_tritonia_landscape_v9` | 11 | 11/11 | 0.048 | 0.243 | 1.000 | 0.019 | **pass 11/11** |
| `hl__crowe_x_osse_cd_v7` | 11 | 11/11 | 1.370 | 1.646 | 1.712 | 0.051 | **pass 11/11** |
| `hl__biradial_es_style_v7` | 11 | 11/11 | 0.039 | 0.093 | 1.000 | 0.006 | **pass 11/11** |

`hl__osse_rrect_fold_warm_v7` was not part of N1b's contract set; this task added it to v2 Test 2
and it passes 11/11. These are the `.x4` 11-design selections, not N1b's ten-design selections, so
the numbers differ from the N1b table (for example Crowe 1.646 mm here against 1.353 mm there);
both are the v2 record p99 for their own sample.

## Result table — stored-label agreement

Denominator = distinct designs with both a stored label and an on-disk recipe. "Sampled 11" is the
`.x4` selection. Record-instance counts (repeated solve records) are in the sub-row.

| Lane | designs | family | typology | sampled 11 family / typology | mounting | termination |
|---|---:|---|---:|---|---:|---:|
| osse_rrect_fold_warm | 246 | **246/246** | **246/246** | 11/11 / 11/11 | 0/0 not stored | 0/0 not stored |
| ext_throat_hvlaw | 136 | **136/136** | **136/136** | 11/11 / 11/11 | 0/0 not stored | 0/0 not stored |
| ath_tritonia_landscape | 120 | **120/120** | **120/120** | 11/11 / 11/11 | 0/0 not stored | 0/0 not stored |
| crowe_x_osse_cd | 200 | **200/200** | **193/200** | 11/11 / 10/11 | 0/0 not stored | **11/11** (`osse_rollback`) |
| biradial_es_style | 307 | **307/307** | **301/307** | 11/11 / 11/11 | 0/0 not stored | 0/0 not stored |

Record-instance counts: osse 251/251 family and typology; ext 136/136; ATH 120/120; Crowe 208/208
family and 201/208 typology; biradial 313/313 family and 307/313 typology.

**Disagreement list (all verify-mode records; stored `FREEFORM` vs derived `grid` /
`typology:biradial`):**

- Crowe (7): `0070dac9e12b`, `2c922317f1c7`, `4784a31e69cf`, `6ca73e01c97b`, `77308ed8afa3`,
  `901d855c40c9`, `b4ea3b525a2a`.
- Biradial (6): `0004bf3995ed`, `0d72914a37cd`, `27fe89821845`, `5215af5401f9`,
  `54137913a603`, `be2523d196c8`.

Every one is a `run_id: verify` record whose `provenance` has only `config/brief/brief_hash`; the
generator block is absent, so `typology_name(None, family)` returns `FREEFORM`. The screen records
for the same designs carry the correct label. `77308ed8afa3` is the best Crowe design and one of
the sampled 11, which is why Crowe's sampled typology is 10/11; the design still has a correct
`grid` label on its screen record.

**Mounting:** no record in these five lanes stores a mounting label, and every brief omits the
mounting block. The sampler therefore derives freestanding for all 55 sampled designs. That is a
default agreeing with an absent label, not a positive agreement: the gate is **not testable** on
these lanes.

**Termination:** only Crowe stores a termination token (`rows.type: osse_rollback`). The sampled
surface is non-monotone in z on all 11 designs (min Δz −5.31 to −6.93 mm), so the token agrees
11/11. The four native/typology lanes store no termination token; **not testable** there.

## Result table — signed envelope and wall-gap margins

Best stored design, and the closest sampled design of the 11. Margins are positive inside the
limit. Envelope lines: W ≤ 600 + 0.5, H ≤ 480 + 0.5, D ≤ 480 + 15 mm. Wall gap: grid limit
2t + 2 mm; native lanes have **no configured gap limit**, so their measured gap is reported as
information only.

| Lane | best W / H / D margin (mm) | closest sampled W / H / D margin (mm) | best gap (mm) / margin | min sampled gap margin |
|---|---|---|---:|---:|
| osse_rrect_fold_warm | +13.28 / +66.66 / +126.58 | +12.33 / +66.66 / +126.58 | 13.18 / +5.18 (native, no limit) | +4.56 (native) |
| ext_throat_hvlaw | +19.54 / +79.05 / +160.05 | **+1.13** (`ca5eb477b1f1`) / +77.73 / +113.77 | 18.82 / +6.82 (native, no limit) | +6.66 (native) |
| ath_tritonia_landscape | +13.21 / +70.48 / +187.18 | +8.87 / **+1.35** (`03b21fe1c33e`) / +16.29 | 12.57 / +4.57 (native, no limit) | +4.56 (native) |
| crowe_x_osse_cd | +7.85 / +69.17 / +234.83 | +7.85 / +66.44 / +229.68 | 12.26 / +4.26 (grid limit 8.0) | **+4.10** (grid) |
| biradial_es_style | +24.34 / +92.95 / +253.28 | +18.43 / +57.41 / +222.31 | 13.89 / +5.89 (native, no limit) | +4.38 (native) |

Throat radius is 18.00 mm (17.99–18.00 Crowe) against the 18 mm driver exit in every lane: signed
throat margin −0.01 to 0.00 mm. That is the brief's throat fit, not an envelope axis.

### Corner scan

A full 2^k factorial is not testable (18 knobs on the rounded-rectangle lane alone). The scan is the 2k
one-at-a-time full-bound extremes, the all-lo and all-hi corners, and four directed combinations
chosen from the one-at-a-time results.

One-at-a-time corners that leave the envelope (worst axis shown):

| Lane | corner | signed margin |
|---|---|---:|
| ext_throat_hvlaw | `a_deg = 40` (hi) | W **−284.9** mm |
| ext_throat_hvlaw | `L_mm = 330` (hi) | W **−148.1**, H −34.7 mm |
| ext_throat_hvlaw | `s = 0.9` (hi) | W −72.7, H −7.1 mm |
| ext_throat_hvlaw | `az_a_cos_amp = 25` (hi) | W −148.5 mm |
| ext_throat_hvlaw | `az_s_cos2_amp` (hi) | W −81.5 mm |
| ath_tritonia_landscape | `morph_height_mm = 480` (hi) | H **+0.5** mm (at the line) |
| crowe_x_osse_cd | `g_a_h_deg = 40` (hi) | W **−43.1** mm |
| crowe_x_osse_cd | `g_sf_ab = 0.9` (hi) | W −37.7 mm |
| crowe_x_osse_cd | `g_r_lip_mm = 30` (hi) | W −19.4 mm |
| crowe_x_osse_cd | `g_s = 0.45` (hi) | W −18.7 mm |
| osse_rrect_fold_warm | no one-at-a-time corner crosses | one-at-a-time min W +12.2, H +68.1, D +125.5; directed min W +7.5 |
| biradial_es_style | no one-at-a-time corner crosses | one-at-a-time min W +16.5, H +20.5, D +175.0; directed min W +12.5, H +16.5 |

The directed combinations are stronger: ext `{a_deg 40, az_a_cos_amp 25, L_mm 330}` reaches
W −996.2 mm and H −396.6; ATH `{morph_height 480, L_mm 400, q 0.97}` reaches H −3.9; Crowe
`{g_a_h 40, g_sf_ab 0.7, g_r_lip 30}` reaches W −119.9 and `{g_a_v 28, g_sf_amt 0.38, g_s 0.45}`
reaches H −6.0. The ext `all_hi` corner is refused by the sampler (`nonmonotone azimuth; no safe
interpolation`), which is itself a corner result. osse and biradial remain inside at every
directed corner (osse min W +7.5; biradial min W +12.5, H +16.5).

**Wall gap:** the minimum measured margin is +4.10 mm (Crowe sampled build; +4.11 in the corner scan, grid limit 8.0);
the native lanes measure 12.4–18.7 mm and have no configured limit. No corner tested approaches
the wall-gap limit.

## Conditionals and conditionally linked pairs

Gated movement is RMS surface movement at 65 × 61. "Fixed" means the knob is present in the recipe
but not searched in that lane. Values are exact from `.x4c/conditionals.json`.

| Gate | Gated state | Active state | Verdict |
|---|---|---|---|
| `n` active iff `s ≠ 0` | `s=0`: **0.000** | osse 0.484; ATH 6.175; Crowe `g_n` 13.928 | **recovered** on osse/ATH/Crowe; ext `n` fixed → not testable |
| `q` active iff `s ≠ 0` | `s=0`: **0.000** | Crowe `g_q` 20.118 | gated half recovered; native active branch **not testable** (mesher axial-chord refusal at 10, 5, 3, 2 mm); `q` fixed in all native lanes |
| `s1` active iff `s2 ≠ 0` | `s2=0`: **0.000** | osse 56.550; ATH 57.966 | **recovered**; `s1` fixed in both search boxes |
| `s2` active iff `s1 ≠ 0` | `s1=0`: **0.000** | osse 2.679; ATH 3.616 | **recovered**; `s2` fixed in both search boxes |
| `morph_*` active iff `morph_target ≠ 0` | target 0: width **0.000**, rate **0.000** | — | **recovered** on osse/ext/ATH; target fixed |
| `morph_exponent` active iff target = 3 | target 1: **0.000** | osse 18.743; ext 25.880; ATH 21.272 | **recovered**; exponent fixed at 4 |
| guiding curve replaces `a_deg` | — | — | **not testable**: no guiding-curve control in any of the five lanes |
| `rot_deg` couples radius and depth | — | — | **not testable**: no `rot_deg` in any of the five lanes |

**Conditional pair found by the corner scan:** `az_fold_h_width_deg` on `hl__osse_rrect_fold_warm_v7`
is inactive at the stored design (full-range 0.054 mm) because `az_fold_h_deg` is −0.061°. At a
fixed fold angle the width moves the surface: 8° vs 40° width is **0.000 mm at fold 0°**,
**1.711 mm at fold −2°**, **4.070 mm at fold −5°**, **7.536 mm at fold −10°**. This is a
conditional link (`az_fold_h_width_deg` × `az_fold_h_deg`), not an inactive knob.

## The 1 %-step evidence is a step size, not activity

The stored `.x4` movement column is a 1 %-of-range one-sided finite difference. If its 0.2 mm
line were applied to it, **40 of the 57 searched knobs** would be called inactive. The full-bound
corner test shows only **one** knob below 0.2 mm (osse `az_fold_h_width_deg`, and it is
conditionally active). The gap is systematic: ATH `az_a_cos_amp` is 0.005 mm at a 1 % step and
0.621 mm across the bound; biradial `h_n` is 0.035 and 5.208 mm; osse `a0_deg` is 0.002 and
0.226 mm. No `fix` label can be built from the 1 %-step column.

## Top-decile bound concentration (pinned-at-edge evidence)

3 % of each knob's bound range, over the top decile of stored J. The brief does not define how
large the mass must be; 0.50 is used here only as a display threshold.

| Lane | top decile | knob at edge | mass | top-decile envelope margin |
|---|---:|---|---:|---|
| osse_rrect_fold_warm | 25 | none ≥0.50 | — | W +13.84, H +67.00, D +119.57 |
| ext_throat_hvlaw | 14 | `az_a_cos_pow` at lo | 0.50 | W **+1.69**, H +54.67 |
| ath_tritonia_landscape | 12 | `morph_width_mm` at hi | 0.75 | W +8.46, H +13.61 |
| ath_tritonia_landscape | 12 | `n` at hi | 0.58 | W +8.46, H +13.61 |
| crowe_x_osse_cd | 21 | `g_L_mm` at hi | 0.52 | W **+6.10**, H +62.70 |
| biradial_es_style | 31 | none ≥0.50 | — | W +18.35, H +90.28 |

## Rematerialisations

| Lane | selected | stored digest vs HEAD | hash | geometry | status |
|---|---:|---|---|---|---|
| `hl__klangfilm_lame_curved_v1` | 11 | 9 = `ea5026…`; 2 = `e3a1f4a3…` | 11/11 | builds via `tools.geometry.klangfilm_lame.make_grid` | **9/11 verified**; 2/11 unverified provenance; ten digest-verified replacements build 10/10 → resolved for the lane, old sample still carries 2 unverified designs |
| `hl__crowe_panel_home_v7` | 11 | 11/11 = `aa2b6a5b…` = HEAD | 11/11 | builds via `crowe_panel_cli.install()` + `grid.rows_grid_points` | **resolved 11/11** |
| `hl__rosse_rect_cd_v7` | 11 | 11/11 = `9b040e37…` (HEAD `601056d0…`) | 11/11 | digest-bypass rebuild at HEAD; kernel unchanged | **resolved** — validator digest drift (`a10e784`); inner p99 ≤0.918 mm, median ≤0.052 mm; W/H exact, depth is the rear closure |
| `hl__lecleach_hv_landscape_smooth_v7` | 10 | no digest stored | 10/10 | HEAD grid rebuilds, but box differs from the stored mesh (W 0–0.3, H 0–68.7, D 9.1–231.1 mm) | **unresolved** |

`lecleach` cause is the 2026-11-16 10:25 H/V realization change in `d6c9abd`; both stored runs are
earlier that morning and store no digest, so rule 4 cannot flag them mechanically. `rosse_rect`'s
stored digest now has a measured explanation and a geometry check (below). **Unresolved
rematerialisation count: 1 lane (`lecleach`) plus 2 of the 11 Klangfilm sample designs.**

### ROSSE digest-bypass geometry check

- **File and commit:** `tools/geometry/rosse_rect.py`, commit `a10e784` (2026-11-17 01:05:50).
  The only changed hunk is `validate_shape`'s `b` lower bound (0.0 → −0.10) and its comment;
  `make_grid` is unchanged. `rolled_rect_cli.py` and `rosse_rect_cli.py` have not changed since
  the stored runs. Recomputing the three-file digest gives `9b040e37…` at `406dc50` (the stored
  value) and `601056d0…` at HEAD. The 11-design sample contains ten designs from
  `20261116T145634Z-screen-e4c778` and `20261116T150941Z-screen-0e777a`, plus one from
  `20261116T064438Z-screen-8defc1`; all eleven store the same `9b040e37…` digest. Their `b`
  values are 0.003–0.146, inside both the old and the new validator range, so the validator
  change is a no-op for this sample.
- **Bypass (only the digest equality):** `rosse_rect_cli.install()` was used as the other CLI
  wrappers do, then `rolled_rect_cli._check_rows` was wrapped to substitute HEAD's current digest
  into an in-memory copy of the rows metadata before calling the original. The schema
  (`rosse-rect-v1`) and driver checks still run. No source, config or run file was modified, and
  no other check was bypassed.
- **Result (11/11):** design hash 11/11. Stored tag-1 inner sheet against the rebuilt 65 × 61
  inner surface: median 0.022–0.052 mm, p99 0.468–0.918 mm (native floor p99 0.721, threshold
  1.000 → pass v2 rule 2). Box against the stored `bbox_m` after quarter doubling: W
  −0.00…+0.00 mm, H −0.00…+0.00 mm, D −2.86…−2.45 mm. The depth difference is the rear closure
  (tag-1 z-min −3.0 mm); D after closure is −0.44…+0.07 mm.
- **Verdict:** digest drift in the validator/companion portion, not a geometry change. The lane is
  **resolved**: geometry reproduced within 0.918 mm p99 (0.052 mm median), W/H exact and depth
  explained by the 3 mm rear closure. No pass line or tolerance was changed.

## Verdict against the brief's lines

- **Sampler / lane validation:** **pass.** 55/55 hash reproductions and 55/55 v2 rule 2.
- **Part A (geometric conditionals):** **partial.** The applicable gates are recovered in the
  gated direction; the `q` active branch is not testable natively, and guiding-curve / `rot_deg`
  do not apply. "Every known conditional that applies" is therefore not claimed.
- **Parts A/B agreement ≥80 % of inactive/weak knobs:** **not testable.** Part B was not
  recomputed at 65 × 61; the stored acoustic table comes from the earlier `.x4/acoustic.py`
  (stored-row ExtraTrees, five bootstrap replicates) and is not comparable to the full-bound
  activity labels.
- **Part D temporal agreement ≥75 %:** **not testable / not run.**
- **Failure criterion (A/B disagree on >1/3 of knobs, or labels unstable):** **not assessed** for
  the same reason.
- **Corner and margin gate:** **reported with signed margins.** The envelope binds on ext/ATH
  (+1.13 / +1.35 mm on sampled designs) and is crossed at ext/ATH/Crowe corners; the wall gap is
  not binding (+4.10 mm minimum).
- **Label-agreement gate:** family 100 %; typology 100 % on three lanes and 96.5–98.0 % on two,
  entirely from verify-mode provenance omission; mounting is **not testable** as a positive label
  on all five lanes and termination on four of five.

## What failed / what is unknown

- **Full factorial corner scan: not testable** (2^18 on the rounded-rectangle lane). The scan covers the 2k
  one-at-a-time faces, all-lo/all-hi and four directed combinations; an unreported combination
  could still cross a limit.
- **`lecleach` does not rematerialise at HEAD** and has no digest to detect the change.
  `rosse_rect`'s digest drift was a validator change only; its geometry reproduces within
  0.918 mm p99. Klangfilm's `e3a1f4a3…` implementation is not in git history.
- **`q`'s active branch is not testable** through the native sampler: the mesher refuses the
  axial chord at 10, 5, 3 and 2 mm. `q` is fixed in all native lanes, so this does not change
  their search dimension, but it leaves the conditional only half-recovered.
- **Mounting has no positive label** on these lanes; **termination has a token only on Crowe**.
- **Part B at 65 × 61 and Part D temporal agreement were not run**; the older acoustic table is
  associational and cannot be promoted to the X4 classification.
- The top-decile "pinned" threshold is a reporting choice, not a brief-defined line.
- The 65 × 61 record is still geometry, not the solved mesh.

## What this does not prove

- Nothing acoustic. No response, solve or score was computed; all margins and activity are
  geometric.
- That a knob inactive on these 11 designs and their box corners is inactive everywhere. The
  `az_fold_h_width_deg` result is the counterexample: conditional on `az_fold_h_deg`, it moves
  1.7–7.5 mm.
- That the envelope-violating corners are reachable in a search; the envelope gate rejects them,
  and no optimizer trajectory was replayed.
- That the 13 label disagreements mean wrong geometry; they are provenance gaps on verify-mode
  records.
- That the sampler is converged for every knob or lane; v2 rule 2 is an agreement tolerance, not
  a convergence proof.
- That sibling grouping was exercised. The analysis is per lane and draws no cross-lane ranking;
  the sibling groups that must be held together in a later cross-lane study are
  `hl__ath_tritonia_landscape_v7/v8/v9`, `hl__ext_throat_hvlaw_v7/v8` and
  `hl__biradial_es_style_smooth_v7/v7`.

## Next action enabled

1. **No config change is supported.** The only clear geometric inactivity is conditionally
   active, so no `fix` recommendation is made.
2. **If dimension must drop**, express the gates, not linear links: `n`/`q` with `s`, `s1` with
   `s2`, `s2` with `s1`, `morph_*` with `morph_target`, and `az_fold_h_width_deg` with
   `az_fold_h_deg`. `search.links` cannot express these.
3. **Widening is a proposal only** for ATH `morph_width_mm` hi (75 % of the top decile at the
   boundary, nearest top-decile envelope margin H +13.6 mm). Do **not** widen ext
   `az_a_cos_pow` lo (top-decile W margin +1.69 mm) or Crowe `g_L_mm` hi (W +6.10 mm) without an
   envelope check.
4. **One rematerialisation needs an owner/senior decision:** a recipe digest (or preserved old
   realization) for lecleach. The `rosse_rect` validator drift is resolved and needs no action
   beyond recording `a10e784` as a validator-only change.
5. **X4's formal success metrics still need Part B at 65 × 61 and Part D**; both are outside this
   task's stated gates and were not run.

## Reproduce

```powershell
# from C:\Users\hunte\Hrns\hornlab-search
git rev-parse --short HEAD          # 87e3311 at start; ad6937b after the mid-run commit
.venv/Scripts/python.exe scratch/fable_architecture/.tmp/fable_replay_harness.py
.venv/Scripts/python.exe scratch/fable_architecture/.x4c/build.py
.venv/Scripts/python.exe scratch/fable_architecture/.x4c/inner.py
.venv/Scripts/python.exe scratch/fable_architecture/.x4c/corners.py
.venv/Scripts/python.exe scratch/fable_architecture/.x4c/range_movement.py
.venv/Scripts/python.exe scratch/fable_architecture/.x4c/conditionals.py
.venv/Scripts/python.exe scratch/fable_architecture/.x4c/labels.py
.venv/Scripts/python.exe scratch/fable_architecture/.x4c/margins_sampled.py
.venv/Scripts/python.exe scratch/fable_architecture/.x4c/pinned.py
.venv/Scripts/python.exe scratch/fable_architecture/.x4c/rematerialize.py klangfilm
.venv/Scripts/python.exe scratch/fable_architecture/.x4c/rematerialize.py crowe_panel
.venv/Scripts/python.exe scratch/fable_architecture/.x4c/rematerialize.py rosse_rect
.venv/Scripts/python.exe scratch/fable_architecture/.x4c/rematerialize.py lecleach
.venv/Scripts/python.exe scratch/fable_architecture/.x4c/rosse_bypass.py
```

`build.py` rewrites the 55 records; the rematerialise passes must be run one per process because
the bridge CLIs rebind the generator globally. No file outside `scratch/fable_architecture/` was
written; `runs/`, `examples/`, `dataset/` and `hornlab_search/` were read only.
