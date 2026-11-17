# Non-CD effective-run score truth table (deliverable #1)

**Date:** 2026-11-16 · **Lane:** read-only analysis over immutable run files · **Helper:** `hornlab_search.targets.scoring_view`
**Scope:** proof-of-effective-score for four real runs. No J was recomputed or modified; every field below comes from a run file or from the read-only helper called on that run's captured config + best design.

## Summary table

| Run | Config / brief identity | Obj | Scored H×V | Onset h / v | Below mode | Narrow | v6 fc → f_pattern | Weights (cov,di,dislope/di_rise,distd,diag,…) | DI level (src, dB, scored) / tgt slope / measured | 8k floor (Hz; H/V deg; best BW; raw) | Diag ref / weighted | Best J |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 `20261116T225543Z-screen-6acf41` | `hl__klangfilm_lame_curved_v1`; brief `room_landscape_80x50_700_hf1440_v7_smooth`, `89e7b98566b5`; cfg `edbe29bcd503eef5` | v7 | 80×50 (cov_v_weight 0.5) | 700 / 700 | mask | 1.0 | — | cov1, di0, dislope1, distd1, diag1; +rip1, flat.5, load1, flat_cv1 | gaussian 13.08, **not scored** (di=0) / 5.0 / **9.57** | 8000; 60 / 37.5; 39.48 / 33.85; **4.344** | 65° / yes | **8.9236** |
| 2 `20261112T113047Z-screen-24053e` | `lecleach_rollback`; brief `lecleach_rollback_1in_v6`, `b3ccc26d382f`; cfg `91dbb8b56494a284` | v6 | 90×60 | 1200 / 1200 (DI-side); coverage onset **1920** | one_sided | 1.0 | 1200 → **1920** (all designs) | load_near1, z_smooth.8, flat.5, rip.8, cov_pat.3, di_rise.4, distd.3, diag0 | none (v6 has no DI level) / 5.0 / **8.42** | — (no floor) | 75° / **no** | **1.5292** |
| 3 `20261027T045054Z-screen-79f496` | `b3a__rosse_morph_v4`; brief `b3a_pa_90x90_400_square_v4`, hash n/a; cfg `45390148353efc4d` | v4 | 90×90 | 400 / 400 | one_sided | 2.0 | — | cov1, di.3, dislope.5, distd.3, diag.5; +rip1, flat.5, load0 | gaussian 10.33, **scored** / 0.0 / **−0.56** | — (no floor) | 90° / yes | **8.2928** |
| 4 `20261115T205453Z-screen-32f7c4` | **Crowe ES-600** `hl__crowe_panel_home_v7`; brief **`room_landscape_80x50_700_hf1440_v7` (BASE CD)**, `12462c62abcd`; cfg `b836d0483bb0687f` | v7 | 80×50 (cov_v_weight 0.5) | 700 / 700 | mask | 2.0 | — | cov1, di.3, dislope1, distd.5, diag1; +rip1, flat.5, load1, flat_cv1 | gaussian 13.08, **scored** / 0.0 / **8.16** | 8000; 60 / 37.5; 48.10 / 35.18; **1.471** | 65° / yes | **16.9182** |

`cfg` = first 16 hex of sha256(`config.yaml`). `run.json`'s `config_sha` is a separate 12-hex config identity (given per run below). Best J is the stored `total`, equal to `Σ w_k·term_k`.

---

## Run 1 — Klangfilm-Lame, v7 "smooth" brief

- **Run id:** `20261116T225543Z-screen-6acf41` (status `running` at snapshot; best design files complete and read-only)
- **Config:** `hl__klangfilm_lame_curved_v1`, family FREEFORM, `config.yaml` sha16 `edbe29bcd503eef5`, `run.json.config_sha` `3c41f512607b`
- **Brief:** `room_landscape_80x50_700_hf1440_v7_smooth`, brief_hash `89e7b98566b5`
- **Objective:** v7 · band 350–8000 Hz
- **Target as scored:** H80 × V50, `cov_v_weight = 0.5` (vertical half-weighted), `f0_h = f0_v = 700`
- **Onset / lower bound:** `h_lo = v_lo = 700 Hz`; **below-onset `mask`**; `cov_narrow_ratio = 1.0`
- **Tolerances:** cov 8.0, rip 1.0, di 0.4, dislope 9.0, flat 1.5, load 0.3, distd 2.0, diag 2.0, flat_cv 1.5
- **Weights:** cov 1.0, di **0.0**, dislope 1.0, distd 1.0, diag 1.0, rip 1.0, flat 0.5, load 1.0, flat_cv 1.0
- **DI:** level source `gaussian` = **13.08 dB**, `level_scored = false` (di weight 0; slope-only); target slope **+5.0 dB/dec**; measured fitted slope over scored band **+9.57 dB/dec**
- **8k floor:** sampled at **8000 Hz**; floor **60.0° H / 37.5° V**; best-design BW there **39.48° H / 33.85° V**; `penalty_raw = 4.344` (added to raw `cov`)
- **Diagonal:** reference **65°** = (80+50)/2, **weighted** (diag 1.0)
- **Best design:** `491efb2132b8`, **J = 8.92362**
- **Term contributions** (weight × stored normalized term): cov **1.41912**, di 0.0, dislope **2.31808**, distd **1.35609**, diag **3.75763**; also rip 0.02625, flat 0.03002, flat_cv 0.01643, load 0.0
- **distd:** normalized term 1.35609; raw `std(DI) = term × tol = 2.712 dB`. **>0 even for a perfectly linear DI rise (std, not residual roughness).**

## Run 2 — Le Cléac'h rollback, v6

- **Run id:** `20261112T113047Z-screen-24053e` (status `finished`)
- **Config:** `lecleach_rollback`, family FREEFORM, sha16 `91dbb8b56494a284`, `run.json.config_sha` `054ce9e0b9ae`
- **Brief:** `lecleach_rollback_1in_v6`, brief_hash `b3ccc26d382f`
- **Objective:** v6 · band 700–5500 Hz
- **Target as scored:** H90 × V60; `f0 = 1200`; `pattern_beta = 1.6`
- **Onset / lower bound:** DI/level-side window `h_lo = v_lo = 1200 Hz`; **coverage onset is `f_pattern = 1.6 × fc` = 1920 Hz for both planes**; **below-onset `one_sided`**; `cov_narrow_ratio = 1.0`
- **v6 per-design fc:** `resolve_fc_hz` reads `params.fc_hz → metrics.scalars['fc_hz'|'g_fc_hz'] → target.f0`. No stored `metrics.json`/row `scalars` contains `fc_hz`/`g_fc_hz`, and the scorer does **not** read generator knobs, so **fc = 1200 and f_pattern = 1920 for every design**.
  - Best `682732cd4ed9`: g_fc_hz 617.06 → fc 1200, f_pattern 1920.
  - Two distinct rows: g_fc_hz 652.68 and 665.97 → both fc 1200, f_pattern 1920. (Different g_fc_hz does **not** create a different scored onset in this run.)
- **Tolerances:** load_near 0.25, z_smooth 0.15, flat 1.5, rip 2.0, cov_pat 15.0, di_rise 4.0, distd 2.0, diag 4.5
- **Weights:** load_near 1.0, z_smooth 0.8, flat 0.5, rip 0.8, cov_pat 0.3, di_rise 0.4, distd 0.3, diag **0.0**
- **DI:** v6 scores **no DI level** (`level_db = level_source = null`, `level_scored = false`); target slope **+5.0 dB/dec** via `di_rise`; measured fitted slope over scored (`f ≥ 1200`) band **+8.42 dB/dec**
- **8k floor:** not applicable (v6 has no `bw8k_floor`)
- **Diagonal:** reference 75°, **not weighted** (diag 0.0)
- **Best design:** `682732cd4ed9`, **J = 1.52916**
- **Term contributions:** cov_pat **0.08638**, di_rise **1.16993**, distd **0.23924**, diag 0.0; also load_near 0.0, z_smooth 0.01234, flat 0.01510, rip 0.00616
- **distd:** normalized 0.79747; raw `std(DI) = 1.595 dB`. **>0 even for a perfectly linear DI rise (std, not residual roughness).**

## Run 3 — R-OSSE morph, v4

- **Run id:** `20261027T045054Z-screen-79f496` (status `finished`)
- **Config:** `b3a__rosse_morph_v4`, family R-OSSE, sha16 `45390148353efc4d`, `run.json.config_sha` `8f0895b42f47`
- **Brief:** `b3a_pa_90x90_400_square_v4`; **brief_hash not stored** in this older v4 run (no `generator.brief_hash` in `design.json`/rows)
- **Objective:** v4 · band 300–8000 Hz (solved grid starts at 500 Hz; n_in_band = 12)
- **Target as scored:** H90 × V90; `f0 = 400`; no `f0_v` (V falls back to H)
- **Onset / lower bound:** `h_lo = v_lo = 400 Hz`; **below-onset `one_sided`**; `cov_narrow_ratio = 2.0`
- **Tolerances:** cov 4.5, rip 2.0, di 0.4, dislope 36.0, flat 1.5, load 0.3, distd 3.0, diag 4.5
- **Weights:** cov 1.0, di 0.3, dislope 0.5, distd 0.3, diag 0.5, rip 1.0, flat 0.5, load **0.0**
- **DI:** level source `gaussian` = **10.33 dB**, `level_scored = true` (di 0.3); target slope **0.0 dB/dec**; measured fitted slope over scored (`f ≥ 400`) band **−0.56 dB/dec**
- **8k floor:** not applicable (v4 has no `bw8k_floor`)
- **Diagonal:** reference **90°**, **weighted** (diag 0.5)
- **Best design:** `931ea7f3b439`, **J = 8.29276**
- **Term contributions:** cov **3.80649**, di **0.94732**, dislope **0.00429**, distd **0.17148**, diag **2.75026**; also rip 0.18546, flat 0.42745, load 0.0
- **distd:** normalized 0.57161; raw `std(DI) = 1.715 dB`. **>0 even for a perfectly linear DI rise (std, not residual roughness).**

## Run 4 — Crowe ES-600 panel, v7 — **scored on the BASE CD brief**

- **Run id:** `20261115T205453Z-screen-32f7c4` (status `finished`)
- **Config:** `hl__crowe_panel_home_v7`, family FREEFORM (`crowe_panel` rows), sha16 `b836d0483bb0687f`, `run.json.config_sha` `6642f0af50bc`
- **Brief actually used:** **`room_landscape_80x50_700_hf1440_v7`** (the base CD brief), brief_hash `12462c62abcd` — **not** the `_v7_smooth` brief
- **Objective:** v7 · band 350–8000 Hz
- **Target as scored:** H80 × V50, `cov_v_weight = 0.5`; `f0_h = f0_v = 700`
- **Onset / lower bound:** `h_lo = v_lo = 700 Hz`; **below-onset `mask`**; `cov_narrow_ratio = 2.0` (base-brief asymmetry, wider than run 1's 1.0)
- **Tolerances:** cov **3.0**, rip 1.0, di 0.4, dislope 9.0, flat 1.5, load 0.3, distd 2.0, diag 2.0, flat_cv 1.5
- **Weights:** cov 1.0, di **0.3**, dislope 1.0, distd 0.5, diag 1.0, rip 1.0, flat 0.5, load 1.0, flat_cv 1.0
- **DI:** level source `gaussian` = **13.08 dB**, `level_scored = true` (di 0.3); target slope **0.0 dB/dec** (CD base, not +5); measured fitted slope over scored band **+8.16 dB/dec**
- **8k floor:** sampled at **8000 Hz**; floor **60.0° H / 37.5° V**; best-design BW there **48.10° H / 35.18° V**; `penalty_raw = 1.471` (added to raw `cov`)
- **Diagonal:** reference **65°**, **weighted** (diag 1.0)
- **Best design:** `22365b569be9`, **J = 16.91818**
- **Term contributions:** cov **3.37475**, di **1.29051**, dislope **7.40401**, distd **0.58909**, diag **3.71053**; also rip 0.06755, flat 0.18686, flat_cv 0.29487, load 0.0
- **distd:** normalized 1.17818; raw `std(DI) = 2.356 dB`. **>0 even for a perfectly linear DI rise (std, not residual roughness).**

---

## Method notes

### Helper calls (per run, on the best design)
Imported `hornlab_search.targets.scoring_view as sv` under `.venv\Scripts\python.exe`; inputs were the immutable `run.json["config"]` (`target`, `objective`, `weights`), `run.json["objective_version"]`, the best design's `metrics.json` (`freqs_hz`, `bw_h_deg`, `bw_v_deg`, `di_db`, `scalars`) and `design.json["params"]`:

- `sv.score_window(target, objective, version, design_scalars=scalars, design_params=params)` → `h_lo_hz`, `v_lo_hz`, `below_mode`, `narrow_ratio`, `fc_hz`, `f_pattern_hz`.
- `sv.di_summary(target, weights, version)` → `level_source`, `level_db`, `level_scored`, `slope_db_per_dec`, `slope_scored`, `anchor_hz`.
- `sv.bw8k_floor(target, objective, version, freqs_hz, bw_h_deg, bw_v_deg)` → `floor_hz`, `floor_h_deg`, `floor_v_deg`, `min_bw_h_deg`, `min_bw_v_deg`, `penalty_raw`.
- `sv.diag_summary(target, weights)` → `reference_deg`, `scored`.
- `sv.measured_di_slope(freqs_in_band, di_db_in_band, score_lo_hz)` with `freqs_in_band` restricted to `[band_lo, band_hi]` and `score_lo_hz = h_lo_hz` → measured fitted DI slope.

### Exact commands
- Read-only inspection: `Get-Content`/`Select-String` over `runs\<id>\config.yaml`, `run.json`, `best.json`, `designs\<hash>\{metrics,design}.json`, `search.ndjson`.
- `config.yaml` sha16 = first 16 hex of `hashlib.sha256(file).hexdigest()`.
- Analysis script (outside the repo, no repo mutation): `C:\Users\hunte\AppData\Local\Temp\opencode\analyze_noncd.py`, run as
  `& "C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe" "C:\Users\hunte\AppData\Local\Temp\opencode\analyze_noncd.py"`.
- Best term contributions computed as `weight[k] * terms[k]` from the lowest-objective `search.ndjson` row matching `best_hash` (or `best.json`); `Σ contributions = stored total` in all four runs (checked to <1e-5).
- Crowe/biradial search: `Get-ChildItem runs -Directory | Select-String -Path config.yaml -Pattern 'crowe|biradial'`; selected `20261115T205453Z-screen-32f7c4` (finished, resolvable `best.design_hash`, complete `metrics.json`). No active GPU run was touched; run 1's completed files were read only (its `run.json` still says `running`).

### Provenance: immutable files vs helper-computed
- **From immutable run files:** config name, `brief_file`/embedded brief name, `brief_hash` (from `generator.brief_hash`), `config.yaml` sha16, `run.json.config_sha`, objective version, `target`/`objective`/`weights` (and thus weights/tolerances lines), best hash and best J, and `terms` (normalized) from `search.ndjson`/`best.json`.
- **Computed by the read-only helper on those files:** scored onset `h_lo/v_lo`, `below_mode`, `narrow_ratio`, v6 `fc_hz`→`f_pattern_hz`, DI level/source/scored flag/target slope, measured DI slope, 8k floor fields, diagonal reference/weighted flag.
- **Computed here from helper + file values:** raw `std(DI) = distd_term × distd_tolerance`; term contributions = `weight × term`. No J was recomputed; the stored `total` was only checked against the contribution sum.

### Handoff predictions confirmed / corrected by the runs
- **Confirmed — run 2 below-onset `one_sided`:** v6 scores the full band below `f_pattern` with zero cost for widening and a penalty only for narrowing (mask/one_sided semantics as documented).
- **Confirmed — run 4 scored on the BASE CD brief:** the Crowe ES-600 (non-CD typology) uses `room_landscape_80x50_700_hf1440_v7` with `di_slope_target 0`, `di 0.3`, `narrow_ratio 2.0`, `cov tol 3.0`; the handoff's warning to audit actual captured config (not family/typology) is exactly borne out. Run 1's Klangfilm uses the `_v7_smooth` brief instead, so Crowe vs Klangfilm J is **not** like-for-like.
- **Confirmed — `distd` is `std(DI)`, not roughness:** every run shows positive `distd` even where the DI trend is strongly monotonic (e.g. run 1 measured +9.57 dB/dec). Raw spread 1.6–2.7 dB.
- **Corrected/refined — v6 "per-design onset" is latent here:** the handoff notes the threshold *can* be design-dependent via metric `fc_hz`/`g_fc_hz`. In run 2 no design stores either as a metric scalar; `g_fc_hz` exists only as a generator knob, which `resolve_fc_hz` does not read. Result: `fc = target.f0 = 1200`, `f_pattern = 1920 Hz` for **all** designs, despite g_fc_hz spanning ~617–666. Do not assume varying g_fc_hz changes the scored onset without a stored metric scalar.
- **Confirmed — feasibility conflict is explicit, not hidden in J:** run 1/4 `config.yaml` records `feasible_v: false` (required 725.7 mm vs 480 mm envelope) while still scoring flat V50; the 8k floor is a separate narrow-only constraint and the best designs sit below it (run 1 H 39.5° vs 60° floor).
