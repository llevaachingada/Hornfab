# Hardened D campaign — stop-and-report (2026-10-29)

**Status: complete. Four cells x 100 non-cached evaluations, plus a b3a second seed at 100, post-D verify and A1 audit. Result: 0 gate-passing designs in 489 audited rows.** No code or solver change; the run configs and the v5 objective were already committed. This is the reassessment point before any new search.

Labels: **[measured]** from the runs; **[derived]** arithmetic; **[inferred]** judgement.

## 1. Campaign

| Cell (brief) | Seed | Budget (new) | Run dir | Screen best J | Verify top J | GPU time | Peak VRAM |
|---|---|---:|---|---:|---:|---:|---:|
| b3bt 90x60 / 600 load | 1234 | 100 | `runs/20261029T030445Z-screen-7a1e70` | **5.515** | 5.990 | 1.10 h | 2132 MiB |
| b3a 90x90 / 480 | 1234 | 100 | `runs/20261029T041046Z-screen-54280b` | **4.035** | 4.756 | 1.52 h | 2999 MiB |
| b1w 90x60 / 850 wide | 1234 | 100 | `runs/20261029T054210Z-screen-219b47` | **6.744** | 7.404 | 0.21 h | 645 MiB |
| room 90x60 / 800 shelf | 1234 | 100 | `runs/20261029T055455Z-screen-0b7917` | **7.361** | 7.292 | 0.24 h | 645 MiB |
| b3a 90x90 / 480 | **5678** | 100 | `runs/20261029T064341Z-screen-9f9c98` | **4.025** | not run | 1.34 h | 2832 MiB |

- D night: 2026-10-29 03:04:42Z → 06:09:11Z (**3.07 h**).
- b3a second seed: 06:43:39Z → 08:03:58Z (**1.34 h**).
- Post-D verify + A1: 02:09:13Z → 02:42:43Z (**0.55 h**).
- Total campaign: **~4.96 h** GPU.

## 2. Canonical A1 gate audit

D campaign (`docs/data/gate_audit_2026-10-29-d/gate_audit.csv`): **389 rows, 0 pass-all.**

| Brief | Rows | H | V | DI | BW8K | Loading | Throat | **pass-all** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| b3bt 90x60 / 600 | 114 | **0** | **0** | 105 | 39 | **0** | 114 | **0** |
| b3a 90x90 / 480 | 96 | **0** | 96 | 93 | 72 | **0** | 96 | **0** |
| b1w 90x60 / 850 | 85 | **0** | 2 | 78 | 48 | 39 | 85 | **0** |
| room 90x60 / 800 | 89 | **0** | **0** | 51 | 38 | 1 | 89 | **0** |
| b3a calib 5.5k | 2 | 0 | 2 | 2 | 2 | 0 | 2 | 0 |
| b3bt calib 5.5k | 2 | 0 | 0 | 2 | 2 | 0 | 2 | 0 |
| native TwinRay 380 | 1 | 0 | 1 | 1 | 0 | 0 | 1 | 0 |

b3a second seed (`scratch/gate_audit_seed2/gate_audit.csv`): **100 rows, 0 pass-all**; H **2**, V **100**, DI 92, BW8K 83, loading **0**, throat 100.

**H is 0 in every D cell.** Loading is 0 in b3a, b3bt and room; 39/85 in b1w. The throat is universally clean (93–114 pass); the mesh/throat work is not the problem.

## 3. The H/V asymmetry is the key result

b3a is a symmetric 90x90 design. Its A1 result is **H 0/96, V 96/96**. That is not a better vertical pattern — it is the gate difference:

- H gate: **±20%** of 90° → 72–108° required.
- V gate: **−40%/+25%** of 60/90° → 54–112.5° allowed for 90.
- The b3a patterns are about **64° at 8 kHz in both planes**: 64/90 = 0.71.
  - H: 0.71 < 0.80 → **fail**.
  - V: 0.71 > 0.60 → **pass**.

The V "pass" is the looser commercial-CD gate, not a better horn. For a 90x90 target, **H is the truth**, and the current family is beaming in H at 8 kHz. This also answers the earlier "are we scoring vertical the same as horizontal" question with data: at the gate level, no — vertical is deliberately more forgiving.

## 4. Seed A/B (b3a, same brief/box/grid, only the seed differs)

| | seed 1234 | seed 5678 |
|---|---:|---:|
| Screen best J | 4.035 | 4.025 |
| Verify top J | 4.756 | not run |
| A1 rows / pass-all | 96 / **0** | 100 / **0** |
| H / V / load pass | 0 / 96 / 0 | 2 / 100 / 0 |

The best-J difference is **0.01 J** — noise. Both seeds produce **zero gate-passing designs**, both have loading 0, and both fail H almost everywhere. **The seed is not the lever; the family/box/gate is.** A second seed at 100 solves did not buy a pass.

## 5. Pass rate before vs after v5 + extended throat

- Old A1 (2026-10-27/28, 5,933 rows): **45 pass-all** — 42 in `native_ath_core_2in_v4`, 3 in `b2w`; **b3a and b3bt 0**.
- New D (389 rows + 100 seed2): **0 pass-all**.
- What the v5/extended-throat pass changed: the b3a **V gate** now passes (96/96) and the seed2 finds 2 H passes; the **H and loading** failures remain. It did not create a gate-passing horn on any D brief.
- Best J fell (b3bt 6.46 → 5.515; b3a 8.29 → 4.035) while the gate pass stayed 0: **J is still not the gate.**

## 6. Verify vs screen

| Cell | Screen best | Verify top | Δ |
|---|---:|---:|---:|
| b3bt | 5.515 | 5.990 | +0.475 |
| b3a | 4.035 | 4.756 | +0.721 |
| b1w | 6.744 | 7.404 | +0.660 |
| room | 7.361 | 7.292 | −0.069 |

Screen-J is optimistic by ~0.5–0.7 on three cells; the room is flat. The screen ranking is a filter, not a build decision.

## 7. Cost and refusal

| Cell | Rows (run) | A1 rows | Approx. refusals | GPU time |
|---|---:|---:|---:|---:|
| b3bt | 118 (18 cached + 100 new) | 114 | ~4 | 1.10 h |
| b3a | 100 | 96 | ~4 | 1.52 h |
| b1w | 100 | 85 | ~15 | 0.21 h |
| room | 100 | 89 | ~11 | 0.24 h |
| b3a seed2 | 101 | 100 | ~1 | 1.34 h |

Refusals are a budget-slot/quality issue, not GPU time: the envelope check is sub-second; the GPU is solving. The b1w/room refusal rates are the highest of the four.

## 8. Findings

1. **The D family is not gate-passing.** The OS-SE + extended-throat + morph family holds V on b3a but beams in H at 8 kHz; b3bt fails H and V; b1w and room fail H. No cell produced a buildable horn.
2. **H is the universal blocker; loading is second.** The H gate ±20% to 8 kHz is strict; the V gate is looser by design. The H failure is a real 8 kHz pattern failure (about 64° vs 90°), not a metric bug.
3. **The seed is not the problem.** 1234 vs 5678: 0.01 J, both 0 pass, loading 0. More seeds will not fix H/loading.
4. **J is not the gate.** Best J improved substantially while pass-all stayed 0. The search is polishing the pattern outside the gate.
5. **The native ATH core 2" family was the only family with a meaningful pass set** in the old A1 (42 designs). The D ext-throat family has none.
6. **The speed work is separate.** The fast-BEM report (`docs/research/MATRIX_FREE_GPU_GMRES_FMM_2026-10-29.md`) says quadrature order 4→2 is the cheapest 2×, GMRES on CUDA is 1.0–1.4×, and FMM is 14k+ only. None of it fixes 0/489.

## 9. What next

1. **Stop the D/seed loop.** It has answered its question: 0 gate-passing designs; the seed is not the lever.
2. **Run a gate-aware, feasible search**, not another J-polishing pass:
   - H hard constraint/pre-filter from f_x to 8 kHz;
   - loading LFP20/Re z hard pre-filter;
   - envelope/box feasibility;
   - 4–6 knobs, two stages, successive halving.
3. **Make the family/brief decision** (owner):
   - keep 90x90/480 and change the family/flare so H holds 72–108° at 8 kHz (the native ATH core family is the only known gate-pass family; test it at this brief);
   - or move to 90x60/600 where the vertical may narrow (b3bt) — but the current b3bt also H 0;
   - or accept a narrower H at 8 kHz and change the gate/target deliberately;
   - or change the driver/mouth size (a 1.4" 90x90 at 480 with a 588 mm mouth may be over-constrained in H).
4. **Fast-BEM:** run the quadrature order 4→2 A/B (Phase 1 of the report) only after/alongside the gate-aware search. It is the cheapest 2× and does not compromise the 8 kHz finalist measurement; it will not create a gate-passing horn.
5. **No more 100-eval passes** of the same family/box. The next solve budget should target the gate, not J.

## 10. References

- D A1 CSV: `docs/data/gate_audit_2026-10-29-d/gate_audit.csv`
- Seed2 A1 CSV: `scratch/gate_audit_seed2/gate_audit.csv`
- D run dirs: `runs/20261029T030445Z-screen-7a1e70`, `runs/20261029T041046Z-screen-54280b`, `runs/20261029T054210Z-screen-219b47`, `runs/20261029T055455Z-screen-0b7917`, `runs/20261029T064341Z-screen-9f9c98`
- Verify outputs: each run's `verify/`; post-D summary `runs/nights/post_D_verify_2026-10-29/SUMMARY.md`
- Fast-BEM research: `docs/research/MATRIX_FREE_GPU_GMRES_FMM_2026-10-29.md`; `NEXT_DEV_PRIORITIES.md` P13
- Gate constants: `tools/rescore/gate_audit.py`; owner decisions: `docs/CONTINUITY.md` 2026-10-29 entry

## 11. Post-report retarget (2026-10-29 12:00Z)

**Owner decision:** retarget the b3a cell to **72 x 72 at 600 Hz** and hold the loading gate's
`Re z >= 0.50` from `f_x` to the design's **f11**, not to 8 kHz. Implemented in
`tools/rescore/gate_audit.py` and `hornlab_search/objective/scalar_v5.py`; LFP20/LFP50 and every
other gate unchanged. `f11_hz` comes from the stored `metrics.scalars.f11_hz`, `BAND_HI` fallback.
New brief/config: `examples/briefs/hardened_2026-10-29_v5/b3a_pa_72x72_600_square_v5.yaml`,
`examples/typologies/hardened_2026-10-29_v5/b3a__osse_ext_throat_72x72_600_v5.yaml`. No solver,
Julia or fork change; nothing committed.

**Seed A1 (cache hit, 0 new / 1 cached, GPU 0.0 s; run `20261029T115645Z-screen-567db8`):**
`J = 3.43861`, **pass_all = false**.

| Gate | Result | Value |
|---|---|---|
| H | **FAIL** | 1 of 14 samples outside +/-20 %; worst at 1.07 kHz, bw_h 89.65 vs 72 (+24.5 %) |
| V | pass | all ratios inside [0.60, 1.25] |
| DI | pass | di_rise 2.097 dB |
| BW8K | pass | bw_h 69.30 / bw_v 69.52 at 8 kHz |
| Loading | **FAIL** | Re z 0.291 at 827.75 Hz inside [600, 3809.38] |
| Throat | pass | 36.0 x 36.0 mm, round 0.994 |

**Premise correction [measured].** The seed's stored f11 is **3,809 Hz**, not 5,584 Hz:
`compute_metrics` takes f11 from the design `r0_mm` (26.385 mm, the extended throat), not the 18 mm
driver exit (18 mm -> 5,582 Hz). The `Re z 0.291` dip is at **827.75 Hz** (8 kHz Re z = 0.981), so it
is a genuine low-mid loading dip inside the loaded window, not the above-f11 artifact the retarget
assumed. The H failure is at 1.07 kHz, not at 8 kHz (8 kHz H 69.30/72 = 0.963 passes). The gate
change itself is correct and continues to score the seed honestly; this seed does not pass.

**Next:** the first 100-eval search on this cell should be gate-aware (H and loading pre-filters,
feasible box) rather than another J-polishing pass; it is not queued here.

## 12. Post-report retarget 2 (2026-10-29 12:20Z): 80x80/600 + driver-exit f11

**Owner decision:** retarget the b3a cell to **80 x 80 at 600 Hz** and source the loading hold's
`f11` from the **18 mm driver exit (5,653 Hz)**, not the design's main throat. The stored
`scalars.f11_hz` 3,809 Hz is the 26.385 mm extended-throat cross-mode, not the driver coupling plane.
Then run the gate-aware 100-eval search on this cell.

**Why 80x80 [measured]:** the 588 x 588 seed reads H 89.65 at 1.07 kHz and V 89.65; against 80 that
is 1.121 / 1.121 (H inside +/-20 %, V inside [0.60, 1.25]); at 8 kHz H/V 69.3 -> 0.866. The previous
72x72 retarget **failed H at 1.07 kHz** (89.65/72 = 1.245 > 1.20); 75x60 failed V (90/60 = 1.50).

**Gate/objective change.** The loading hold's upper bound now resolves
`target.loaded_hi_hz` > driver-exit f11 (`1.8412*c/(2*pi*a)` from `driver.exit_radius_mm`) > stored
`scalars.f11_hz` > `BAND_HI`. The Re z hold is `[F_X, min(BAND_HI, loaded_hi_hz)]`; LFP20/LFP50 and
every other gate unchanged. `loaded_hi_hz`/`f11_hz` are unweighted diagnostics. `config.py` surfaces
the driver radius on the typed target only, so `config_sha` stays stable for existing brief runs.

**New files:** `examples/briefs/hardened_2026-10-29_v5/b3a_pa_80x80_600_square_v5.yaml` (80x80, f0 600,
K-law 529x529, 588x588 seed retained, 740x740x650, band 300-8000, 18-point grid, v5 class C,
`loaded_hi_hz: 5653.0`); `examples/typologies/hardened_2026-10-29_v5/b3a__osse_ext_throat_80x80_600_v5.yaml`
(budget 100, distance 10, seed 588x588). No solver, Julia or fork change; nothing committed.

**Seed A1 (cache hit, 0 new / 1 cached, GPU 0.0 s; run `20261029T121930Z-screen-10b954`):**
`J = 3.24955`, **pass_all = false**.

| Gate | Result | Value |
|---|---|---|
| H | pass | 80x80 window; seed natural H 89.65/80 = 1.121 |
| V | pass | ratios inside [0.60, 1.25] |
| DI | pass | di_rise 2.097 dB |
| BW8K | pass | bw_h 69.30 / bw_v 69.52 at 8 kHz (0.866 x 80) |
| Loading | **FAIL** | Re z 0.291 at 827.75 Hz inside [600, 5653]; LFP20 329.9 Hz passes |
| Throat | pass | 36.0 x 36.0 mm, round 0.994 |

**The 827 Hz dip is the search target [measured].** It is inside every candidate loaded window
(explicit 5653, driver-exit 5583.5, stored 3809, and BAND_HI), so it is a genuine driver-loading
failure, **not** an above-f11 artifact. The 8 kHz reading in the seed is H/V 69.3 (passes 80x80),
not a failure.

**Search launched:** detached `runs/nights/b3a80x80_search.ps1` (wrapper pid 36992), run
`runs/20261029T122018Z-screen-9766f0`, log `runs/nights/b3a80x80_search.log`; v5 objective (load 1.0),
80x80 brief, 588 seed, 18-point grid, distance 10, budget 100. Post-search A1 controller pid 16056
writes `runs/nights/b3a80x80_search_a1.log` and `scratch/gate_audit_b3a80x80_search/`.

## 13. 80x80 gate-aware search result (2026-10-29 13:42Z)

**Owner decision executed:** 100-eval gate-aware search on the 80x80/600 cell. Run
`runs/20261029T122018Z-screen-9766f0`; 100 new + 10 cached; best screen J **2.9053** (seed 3.2495).
Post-search A1: `scratch/gate_audit_b3a80x80_search/` (`README.md`, `gate_audit.csv`); 110 rows,
**0 pass-all**.

| Gate | Pass / 110 | Note |
|---|---:|---|
| H | 68 | 42 fail; target fixed the D-era 0/96 |
| V | 108 | 2 fail |
| DI | 109 | 1 fail |
| BW8K | 96 | 14 fail |
| Loading | **0** | the universal blocker |
| Throat | 110 | clean |

**Loading detail [measured].** LFP20 passes 110/110 (min 282.3 Hz; the 1.6x bar is 375 Hz). The
failure is the Re z dip: the best-J row is **0.2763**, the best loading row in the whole run is
**0.3767**, and the seed was **0.291 at 827.75 Hz**; the floor is 0.50. The 100-eval search moved J
(3.2495 -> 2.9053) but not the dip. The 827 Hz dip is inside [600, 5653] and is structural in the
b3a extended-throat family, not a seed/target artifact.

**Conclusion.** The 80x80 retarget fixed H/V (H 68/110, V 108/110), so the target choice was right;
loading is now the sole universal failure. Do not run another b3a 80x80/seed/target. Change family
or throat; the native ATH core 2" family is the only prior all-gate pass set (42 designs in the old
A1). No code, solver, Julia or fork change; nothing committed.
