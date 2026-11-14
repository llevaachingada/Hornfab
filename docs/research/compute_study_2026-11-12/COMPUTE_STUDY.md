# Compute-allocation study — 2026-11-12

**Repo (read-only):** `C:\Users\hunte\Hrns\hornlab-search`
**Study outputs:** `C:\Users\hunte\Hrns\study_2026-11-12\`
**Script interpreter:** `.venv\Scripts\python.exe -I`
**Hardware:** one RTX 4060 8 GB (beat_cuda, dof_cap_screen 12000) + one CPU BEM lane (beat_cpu,
12 Julia threads; approved 2026-11-12, integration pending)

---

## 1. Run inventory (runs_inventory.csv)

Script: `analyze_runs.py`. Reads every `runs/*/search.ndjson` + `run.json` for 414 runs.
Key counts:

| Family | Runs | Valid evals | Best J | Still-improving |
|---|---|---|---|---|
| FREEFORM | 296 | 17,553 | 1.1131 | 95 |
| OSSE | 88 | 8,697 | 1.5968 | 29 |
| R-OSSE | 23 | 1,360 | 1.0343 | 8 |
| ICW | 7 | 1,856 | 12.2009 | 4 |

**Still-improving count caveats:** 136 runs flagged still-improving in total; 46 of those have
campaign-era objective versions (v4/v6/v7) and known briefs. The majority of the 136 are
pre-v4 runs (objective v1-v3) with no brief — not worth resuming.

### Atlas (CMA-ME) runs

| Config | Brief | Obj | Valid | Bins / 324 | Best J |
|---|---|---|---|---|---|
| atlas__ath_core | native_ath_core_2in_v4 | 4 | 1,141 | 31 | 2.0987 |
| atlas__core_law | native_ath_core_2in_v4 | 4 | 347 | 15 | 2.2953 |
| atlas__hyb_osse_h_hypex_v | b2w_pa_60x40_1200_big_v4 | 4 | 1,102 | 19 | 2.7538 |
| atlas__osse_ext_throat | b1w_hifi_90x60_850_wide_v5 | 7 | 140 | 5 | 6.6361 |
| lecleach_rollback (v6) | lecleach_rollback_1in_v6 | 6 | 142 | — | 1.5357 |

Note: `atlas__osse_ext_throat` is a v7 (hardened CD) objective cell. Per HARDENED_D_2026-10-29.md,
0 gate-passing designs in 489 rows — this atlas is very early-stage exploration.

### Best single-objective (CMA) cells (top 10 by J, v4 objective)

| Config | Brief | J | n_valid | Dir |
|---|---|---|---|---|
| b3a__rosse_morph_round_v4 | b3a_pa_90x90_400_square_v4 | 1.5968 | — | 20261028T200311Z |
| native__ath_core_v4 | native_ath_core_2in_v4 | 1.6180 | 192 | 20261027T070736Z |
| b1t__lecleach_iwata_ar_v4 | b1t_hifi_90x60_850_tall_rows_v4 | 1.6252 | — | 20261027T061958Z |
| crease__core_law_v4 | native_ath_core_2in_v4 | 1.7079 | 172 | 20261027T052720Z |

---

## 2. Convergence and landscape analysis

### 2a. Tonight's throughput matrix (n1, 12/12 arms complete)

| dofs | fused-on prefetch-off | fused-off | fused-on prefetch-on | fused-off prefetch-on |
|---|---|---|---|---|
| ~1k | 131 s / 1,334 MiB peak | 141 s / 1,835 MiB | 119 s / 1,410 MiB | 140 s / 2,485 MiB |
| ~4k | 232 s / 3,167 MiB | 281 s / 5,261 MiB | 234 s / 2,872 MiB | 315 s / 5,547 MiB |
| ~8k | 503 s / 4,900 MiB | 318 s / 7,499 MiB | 504 s / 4,202 MiB | OOM at 7,731 MiB |

**Recommendation:** keep `cuda_fused: true, prefetch: false` for 8k dof searches (503 s, 4.9 GiB).
Fused-off at 8k is 1.6x faster but uses 7.5 GiB (93% VRAM) — risky on 8 GB card. Fused-off +
prefetch-on OOMs. For search runs at screen mode, 4-6k dofs are common and fused-on is safe.

### 2b. Knob sensitivity analysis (Spearman rank-correlation, run sensitivities)

**atlas__core_law** (n=347 valid, still-improving, seed 1030):
- `L_mm` rho = -0.704 (longest horn → lowest J; strongest signal in any v4 atlas cell)
- `a_deg` rho = -0.222 (wider opening → lower J)
- `az_sf_n1`, `az_sf_n2`: rho ~ -0.11 (shape law exponents help modestly)
- No bound walls in top decile. L_mm range [104, 520]; best designs cluster at high L.

**atlas__ath_core** (n=1,141 valid, seed 1030):
- `a_deg` rho = +0.264 (search prefers lower a_deg; counterintuitive — the coverage law adds azimuthal spread)
- All other knobs rho < 0.18. No strong single dominating dimension.
- No bound walls. Well-explored landscape after 1,141 evals.

**native__ath_core_v4** (n=192 valid, still-improving, seed 1234):
- `morph_corner_mm` rho = -0.326 (rounder corners → better)
- `n` rho = -0.315 (lower exponential rate → better)
- `morph_rate` rho = +0.296 (higher morph rate → better)
- **Bound walls in top decile (n=19 designs):**
  - `morph_fixed` lo wall: 8/19 designs at [0.0, 0.03], range [0.0, 0.6]
  - `morph_width_mm` hi wall: 8/19 designs at [445, 456.55], range [238.2, 456.55]
  - `q` hi wall: 7/19 designs at [0.99, 1.0], range [0.9, 1.0]
  - **Action:** narrow-bounds follow-up (proposed_configs/native__ath_core_v4_narrow.yaml)

**crease__core_law_v4** (n=172, NOT still-improving, seed 1234):
- `n` rho = +0.385, `a_deg` rho = -0.356 (strong opposing signals; bifurcated landscape?)
- `k` lo wall: 7/17; `morph_rate` lo wall: 9/17
- Not scheduled for resume (converged).

**b2w__osse_baseline_v4** (n=127, still-improving, seed 1234):
- `k` rho = +0.450 (k near lo bound of [0.3, 5.0] preferred; hi flare rate)
- `k` lo wall: 6/12 designs in top decile
- Recommended: narrow-bounds follow-up if GPU budget allows in a later night.

**atlas__osse_ext_throat** (n=140, NOT still-improving):
- `L_mm` rho = -0.874 (dominant signal; same as atlas__core_law — longer horns win)
- Only 5 bins / 324; this is an empty-atlas result, not a converged one.

**lecleach_rollback v6** (n=142, NOT still-improving):
- 3-knob space; no clear dominant knob in the sensitivity (all rho < 0.1 for the 3 knobs)
- Fast (~5 s/eval); need more evals and seed variance to characterize the v6 landscape.

### 2c. CMA-ME coverage status

| Atlas | Bins occ. | Coverage | Last budget | Still runs | Priority |
|---|---|---|---|---|---|
| atlas__ath_core | 31 / 324 | 0.096 | 1,141 + ~400 tonight | Yes (inventory) | Medium — extend further |
| atlas__core_law | 15 / 324 | 0.046 | 347 | Yes (sensitivity) | HIGH — L_mm signal strong |
| atlas__hyb_osse_h_hypex_v | 19 / 324 | 0.059 | 1,102 | Yes (inventory) | Low — 1k+ evals, low yield |
| atlas__osse_ext_throat | 5 / 324 | 0.015 | 201 | No (sensitivity) | Medium — first run only |

Coverage is low across all v4 atlas cells (<10%). The atlas at this budget level is sampling, not
converging. Longer runs (1k+ evals/cell) are needed before coverage maps are reliable for
gap analysis. This is expected at the current scale; a 3,000-eval atlas run per cell would be
needed for a 50% coverage target.

### 2d. Under-sampled vs converged cells

Under-sampled (< 300 valid evals, objective version ≥ 4): 42 cells
Most-converged (> 500 valid evals, v4+): atlas__ath_core, atlas__hyb_osse_h_hypex_v
Still-improving (high value, v4+): atlas__core_law, native__ath_core_v4, b2w__osse_baseline_v4

### 2e. n7 staged_ab failure analysis

**Failure:** `tools/run_staged_search.py --out runs/staged_ab_2026-11-12 --both` exited in 2.2 s
with "Stage A produced no best.json; stopping staged chain."

**Root cause:** `run_staged_search.py` reads the stage A template from
`examples/typologies/staged_ab_2026-10-31/stageA_macro__crease_core_law.yaml` (which has
`brief_file: ../../briefs/campaign_2026-10-26/native_ath_core_2in.yaml` — correct from that dir),
copies it verbatim to `runs/staged_ab_2026-11-12/configs/stageA_macro__crease_core_law.yaml`,
then calls `hornlab-search search --config <generated>`. The CLI resolves `brief_file` relative
to the generated config dir, so it looks for `runs/staged_ab_2026-11-12/../../briefs/...` =
`runs/briefs/...` which does not exist.

**The brief EXISTS** at `examples/briefs/campaign_2026-10-26/native_ath_core_2in.yaml`.

**Fix options:**
1. **Workaround (tonight's queue):** pass `--stage-a` pointing to
   `proposed_configs/stageA_macro__crease_core_law_abs.yaml` (absolute brief_file path).
   Owner must copy this file to `examples/typologies/staged_ab_2026-10-31/` before the night.
2. **Permanent code fix** (3 lines in `tools/run_staged_search.py` near the config-write loop):
   ```python
   src_cfg_dir = Path(DEFAULT_STAGE_A).parent
   if 'brief_file' in generated_cfg and not Path(generated_cfg['brief_file']).is_absolute():
       generated_cfg['brief_file'] = str((src_cfg_dir / generated_cfg['brief_file']).resolve())
   ```
3. **CLI workaround** (alternative to fix 1): pass `--brief examples/briefs/.../native_ath_core_2in.yaml`
   to override the broken relative path at CLI level (but `run_staged_search.py` calls the CLI
   internally — the `--brief` override can't reach internal calls this way).

---

## 3. Compute plan (~20 h GPU + CPU second lane)

### GPU queue (gpu_day.yaml)

| Job | Config / Run | Brief | Mode | Budget | Est. h | Rationale |
|---|---|---|---|---|---|---|
| n0_hygiene | gpu-clean | — | — | — | 0.2 | VRAM baseline, kill stale workers |
| n2_calibration | tools/evidence_bytecheck_m5.py --top 5 | v4 finalists | verify | 6 designs | 3-4 | Gates every future night; band-split, 10 m vs 2 m, epw 6 vs 9 |
| n3_core_law_resume | atlas_2026-10-30/atlas__core_law.yaml --resume 20261030T170642Z | native_ath_core_2in_v4 | screen | +400 | 2.2 | Highest-value still-improving atlas cell; L_mm dominates |
| n4_core_law_seed1031 | atlas__core_law_seed1031.yaml (proposed) | native_ath_core_2in_v4 | screen | 300 | 1.7 | Seed variance for algorithm analysis |
| n5_lecleach_v6_resume | lecleach_rollback.yaml --resume 20261112T113047Z | (merged, v6) | screen | +300 | 0.4 | 142 valid evals only; first v6 search |
| n6_lecleach_v6_seed1235 | lecleach_rollback.yaml --brief lecleach_rollback_1in_v6.yaml | v6 | screen | 300 | 0.4 | Seed variance for v6 objective |
| n7_ext_throat_resume | atlas_2026-10-30/atlas__osse_ext_throat.yaml --resume 20261112T110126Z | b1w_hifi | screen | +200 | 0.5 | First ext-throat atlas, 5/324 bins only |
| n8_staged_ab_retry | run_staged_search.py --stage-a stageA_abs.yaml --both | native_ath_core_2in | screen | 400 chain | 2.2 | n7 failed in 2.2 s; fix = absolute brief_file; staged vs joint A/B comparison |
| n9_ath_core_narrow | native__ath_core_v4_narrow.yaml (proposed) | native_ath_core_2in_v4 | screen | 200 | 1.1 | 3 bound walls; narrowed morph_fixed/morph_width_mm/q |
| n10_ath_core_resume | atlas_2026-10-30/atlas__ath_core.yaml --resume 20261030T111108Z | native_ath_core_2in_v4 | screen | +400 | 2.2 | Coverage fill; 31/324 bins after tonight |
| **Total** | | | | | **~14-17 h** | (N2 calibration can overrun; 20 h gives ~3-6 h slack) |

**Skipped:** any v5 (MEH) objective. v7 (hardened CD) further atlas expansion — HARDENED_D evidence
shows 0 gate-passing designs in 489 rows; atlas__osse_ext_throat got its single budget (200 evals)
tonight. Do not schedule further v7 atlas expansions until the CD gate analysis is revisited.

**Prerequisites before the night:**
- Copy `proposed_configs/stageA_macro__crease_core_law_abs.yaml` to
  `examples/typologies/staged_ab_2026-10-31/stageA_macro__crease_core_law_abs.yaml` (owner action)
- Copy `proposed_configs/atlas__core_law_seed1031.yaml` to
  `examples/typologies/atlas_2026-10-30/atlas__core_law_seed1031.yaml`
- Copy `proposed_configs/native__ath_core_v4_narrow.yaml` to
  `examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4_narrow.yaml`
- Then n4, n9 can use `kind: search` with the config paths above

### CPU queue (cpu_day.yaml) — when second lane is live

| Job | Description | Mode | Budget | Est. h | Rationale |
|---|---|---|---|---|---|
| c1_verify_ath_core_top10 | Verify top-10 atlas__ath_core elites (CPU) | verify | 10 | 0.5 | CPU excels at single re-solves; no VRAM |
| c2_verify_core_law_top10 | Verify top-10 atlas__core_law elites (CPU) | verify | 10 | 0.5 | Confirm screen ranking stability for the still-improving cell |
| c3_cpu_cuda_crosscheck | beat_cpu vs beat_cuda dB delta on 5 elites | verify | 5+5 | 0.25 | E8 from CPU_SECOND_LANE: not yet measured; needed before cross-lane J comparisons |
| c4_lecleach_v6_cpu_seed1236 | lecleach_rollback v6, screen, seed 1236 (CPU) | screen | 200 | 0.4 | Third seed for v6 variance; runs in parallel while GPU does atlas expansions |
| **Total** | | | | **~1.65 h** | Active CPU time; zero net cost (GPU idle 43%) |

**CPU lane constraints:** beat_cpu must be re-provisioned first (fingerprint drift, E9).
CPU lane only for: verify re-solves, <1.5k dof new searches. Do NOT use for v5 (MEH paused) or
v7 (hardened CD) or any run requiring CUDA-specific features.

---

## 4. Data and analysis outputs

| File | Description |
|---|---|
| `runs_inventory.csv` | 414 rows × 23 cols: per-run stats, convergence, QD coverage |
| `sensitivity_analysis.txt` | Spearman rho and bound-wall analysis for 9 key run dirs |
| `COMPUTE_STUDY.md` | This document |
| `proposed_configs/atlas__core_law_seed1031.yaml` | Multi-seed replicate of atlas__core_law |
| `proposed_configs/lecleach_rollback_v6_seed1235.yaml` | Multi-seed replicate v6 |
| `proposed_configs/native__ath_core_v4_narrow.yaml` | Narrowed-bounds follow-up (3 bound walls) |
| `proposed_configs/stageA_macro__crease_core_law_abs.yaml` | Staged-AB fix (absolute brief_file) |
| `gpu_day.yaml` | Night runner format, 10 jobs, ~15-17 h GPU |
| `cpu_day.yaml` | CPU lane format, 4 jobs, ~1.7 h (runs in parallel) |

**Analysis tools:** `analyze_runs.py` (inventory, by-family summary, atlas summary, top cells),
`sensitivity_analysis.py` (Spearman rank-correlation, bound-wall detection).

**Next analysis steps (not done in this study):**
- CMA covariance dump reading (`runs/*/cma/restart_0/`) for sigma evolution plots
- atlas coverage heat-maps (occupied bins plotted on 18×18 grid)
- Calibration result parsing after N2 runs (band-split vs single-mesh delta-J)
- beat_cpu vs beat_cuda dB delta after C3 runs (prerequisite for cross-lane J comparison)

---

## 5. Key findings and recommendations

1. **atlas__core_law is the highest-priority resume** (sensitivity L_mm rho=-0.704, still-improving,
   only 15/324 bins at 347 valid evals). One 400-eval night gives it comparable depth to
   atlas__ath_core.

2. **atlas__ath_core is approaching convergence** (1,141 evals + 400 tonight, a_deg weakly
   dominant at rho=+0.26, no bound walls). Further budget yields coverage fills, not algorithm gain.

3. **Seed variance data is missing for all v4 atlas cells.** Both atlas__core_law and lecleach
   rollback v6 have only single-seed runs. Seed variance is required before claiming convergence
   or comparing cells.

4. **n7 staged_ab failure is a 3-line code fix** in `tools/run_staged_search.py` (brief_file path
   resolution). Workaround for tonight: `--stage-a` pointing to the abs-path config.

5. **Three bound walls in native__ath_core_v4** (192 evals, still-improving): morph_fixed low,
   morph_width_mm high, q high. Narrow-bounds follow-up (native__ath_core_v4_narrow.yaml) is
   likely to find J improvements in 200 evals.

6. **CPU second lane: proceed with integration** (DECIDED 2026-11-12). Highest value:
   parallel verify re-solves (no VRAM, 12-thread BEM) and lecleach v6 seeds. The beat_cpu vs
   beat_cuda cross-check (C3) must run before any cross-lane J comparison.

7. **v7 (hardened CD) objective:** do not expand atlas__osse_ext_throat further until the
   HARDENED_D evidence is re-evaluated. 0 gate-passing designs in 489 rows is a show-stopper.

8. **Calibration N2 is a gate for all further nights.** It was deferred from tonight (needs n1
   throughput defaults, now available). Schedule it first in the next GPU night.
