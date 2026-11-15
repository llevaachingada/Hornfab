# How on-axis response is scored, and how it should be (2026-11-14)

The owner asked whether the search weights on-axis / frequency response enough for a home hi-fi horn that will be
used with DSP EQ. They also asked how this differs for the no-DSP (passive / tube) school. This note covers the
current scoring (code), the outside evidence, an offline probe on the home runs (no GPU), and recommendations.
Status: **analysis only, no objective changed.**

## 1. What objective v7 scores today (home brief `room_80x60_700_hf1440_v7`)

| Term | What it measures | Band | Weight / tol | Share of J (home ext-throat / ATH-core top runs) |
|---|---|---|---|---|
| `flat` | 0° on-axis, residual std about ONE straight line vs log f (unit acceleration) | **350**-8000 Hz | 0.5 / 1.5 dB | 14 % / 13 % |
| `flat_cv` | 0° on-axis, same but unit velocity (driver-like) | 700-**3000** Hz | 1.0 / 1.5 dB | 25 % / 6 % |
| `rip` | angular ripple inside the coverage window about a smooth beam, H + V | band | 1.0 / 1.0 dB | 6 % / 4 % |
| `diag` | off-plane (45°) pattern vs the H/V planes | ≥ f0 | 1.0 / 2.0 | 6 % / 28 % |
| `dislope`, `distd`, `di` | DI slope, DI steadiness, DI level | ≥ f0 | | ~10 % |

So on-axis is not ignored: `flat` + `flat_cv` carry ~40 % of J on the ext-throat family and ~20 % on ATH-core.
It is mis-measured in three ways:

1. **`flat` scores the region below the crossover.** Its band starts at 350 Hz and the XO is 700 Hz. On the ATH-core
   best design the "3.5 dB on-axis roughness" is mostly the horn's natural roll-off at 400-650 Hz (−17 to −5 dB),
   which the woofer covers. `flat_cv` already starts at F_X. `flat` should too.
2. **Only the 0° line is scored.** Nothing scores a listening window, and nothing separates deviations that are the
   same at every angle (EQ fixes them) from deviations that change with angle (EQ cannot fix them).
3. **Resolution.** Screens solve 18 frequencies (~3.5 per octave in band). Narrow ripple from diffraction or higher-order
   modes (1/6-1/3 octave wide) falls between samples. Verify uses 6 per octave.

Example, the home incumbent (ext-throat, J 3.2325), constant-velocity on-axis: −3.7 dB at 643 Hz and −4.2 dB at 828 Hz,
while the H beamwidth pinches to 62° and then widens to 76° at 1065 Hz. That is a directivity wobble right at the
700 Hz crossover, and it is the kind of flaw an on-axis EQ cannot fix at every seat. Above 1 kHz it is within ±1.5 dB.

## 2. Outside evidence

- **Listener preference is predicted by more than on-axis.** Olive's 2004 model (70 loudspeakers, 19 double-blind
  tests, r ≈ 0.86-0.99 across studies) uses on-axis narrow-band deviation (NBD_ON), the predicted in-room response's
  deviation and smoothness (NBD_PIR, SM_PIR) and bass extension. The formula is widely reproduced as
  Pref = 12.69 − 2.49·NBD_ON − 2.99·NBD_PIR − 4.31·LFX + 2.32·SM_PIR. NBD is the deviation inside ½-octave bands, i.e.
  local roughness, not overall tilt. The in-room curve is 12 % listening window + 44 % early reflections
  + 44 % sound power (CTA-2034), so off-axis behaviour outweighs the single on-axis line.
- **Broad bumps matter more than narrow ones.** Toole & Olive 1988 (JAES 36(3)): low-Q resonances are more audible
  than high-Q ones (doubling Q raises the threshold ~3 dB), and peaks are more audible than dips.
- **What DSP can and cannot fix.** A deviation that appears on all axes (driver or throat resonance, overall tilt) is
  EQ-able. Waveguide flaws (diffraction, HOMs, directivity wobble) differ by angle and are not (Geddes; the ATH
  thread's practice). A true CD horn is not flat on-axis unequalised: it needs a rising HF EQ ("CDEQ", Keele; plus the
  compression driver's ~6 dB/oct mass roll-off).
- **The no-DSP school.** Passive / tube builds must reach the target response from the horn plus a simple network.
  They either (a) accept a CD horn with a passive CDEQ network (costs efficiency), or (b) let the horn narrow with
  frequency so on-axis rises to offset the driver roll-off (tractrix-style "beaming"), giving up a constant power
  response. For that school, broad on-axis shape is a real design target. For the DSP school it mostly is not.

## 3. Offline probe (no GPU): would a hi-fi score rank the home designs differently?

Script: `scratch/onaxis_2026-11-14/hifi_rescore.py`, run over 573 stored designs of runs `51328c`, `18985d` (ext-throat) and
`db8e2f` (ATH-core). Each design's `response.npz` holds 73-angle H/V cuts (±90°) and a 512-point balloon at the
18 screen frequencies. Unit-velocity levels, XO-8 kHz. CTA-2034-style listening window (0°, ±10° V, ±10/20/30° H),
early reflections approximated from the cuts (rear wall = ±90° only), sound power from the balloon.

| run | LW deviation (median) | non-EQ-able angle spread* | PIR−LW shape dev | ρ(J, spread) | ρ(J, PIR−LW) | top-10 overlap, J vs illustrative DSP-hi-fi score |
|---|---|---|---|---|---|---|
| 51328c ext | 1.14 dB | 0.32 dB | 0.10 | +0.31 | +0.61 | 4/10 |
| 18985d ext | 1.12 dB | 0.31 dB | 0.09 | +0.19 | +0.79 | 0/10 |
| db8e2f ATH-core | 0.69 dB | 0.60 dB | 0.14 | +0.85 | +0.50 | 3/10 |

\* std across the 9 listening-window curves after removing each angle's fixed offset and the common EQ, averaged over
frequency: the coloration that differs from seat to seat.

First reading (superseded below): this table's "top-10 overlap" used an uncalibrated ad-hoc score with 0.5 dB scales,
so it overstated the disagreement. The calibrated tool in section 3b replaces it.

## 3b. Calibrated offline re-score (`tools/analysis/hifi_rescore.py`, 2026-11-14)

The tool re-scores every stored valid design: J_dsp = J_v7 − (v7's `flat` + `flat_cv` contributions) + 1.0·`seat_spread`
+ 0.5·`xo_spread` + 1.0·`pir_shape` + 0.5·`lw_rough`. J_passive adds 1.0·`lw_shape`. Tolerances are calibrated as in
v8 (top-decile median). The run covered 870 designs on the home brief: ext-throat seeds 1234 and 5678, the live H1
petal run, the ATH-core runs and the ATH-core CPU partial. Output is in `scratch/hifi_rescore_2026-11-14/`. Tests:
`tests/test_tools_analysis_hifi_rescore.py` (10, offline).

| family / run | n | best J_v7 | median seat spread | median XO spread | median PIR−LW shape | median LW roughness |
|---|---:|---:|---:|---:|---:|---:|
| ext-throat s1234 | 221 | 3.233 | 0.32 dB | 0.17 | 0.10 | 0.85 |
| ext-throat s5678 | 185 | 3.233 | 0.31 | 0.20 | 0.09 | 0.83 |
| ext-throat + petal (live, 13 rows) | 13 | 3.233 | 0.42 | 0.21 | 0.16 | 0.60 |
| ATH-core (cohort / relaunch) | 225 / 171 | 5.374 / 5.387 | 0.59 / 0.60 | 0.20 / 0.23 | 0.13 / 0.14 | 0.24 / 0.24 |

Findings:

- **The DSP-aware score agrees with v7.** Spearman is +0.99 pooled and +0.95 inside the ext-throat family. Top-15
  overlap is 9 (dsp) and 5 (passive). v7's #1 ranks 12th under dsp. The ext-throat top 50 differ by only
  0.28-0.34 dB in seat spread, 0.18-0.25 dB in XO spread and 0.06-0.09 dB in PIR shape. These are near-twins whose
  differences are far below audibility thresholds for broad deviations, so changing the on-axis scoring would not
  change which horn gets built today.
- **The two families trade the two kinds of flaw.** Ext-throat has half the seat-to-seat coloration of ATH-core
  (0.3 vs 0.6 dB, the part DSP cannot fix) but about 3x the fine LW roughness (0.8 vs 0.24 dB, much of it the
  640-830 Hz dip at the crossover). With DSP the ext-throat family is the better hi-fi base. A no-EQ build would
  weigh ATH-core's smoother listening window more.
- **Resolution is the main limit.** All numbers use the 18-point screen grid. Re-run the tool with `--verify` on
  tonight's verify results (6 points/octave) before deciding any objective change.

## 4. Recommendations

1. **Do not just raise the on-axis weight.** With DSP, the horn's job is what EQ cannot do: seat-to-seat consistency
   inside the listening window, a smooth in-room / sound-power shape relative to the listening window, a clean
   directivity hand-off at the XO, and no narrow diffraction / HOM ripple. Broad on-axis shape is cheap to EQ.
2. **Fix the mis-scoring (small, low risk):** start `flat` at F_X (the XO), as `flat_cv` does, and extend `flat_cv` to
   the band top (3 kHz → 8-10 kHz).
   **Prepared 2026-11-14, not merged:** worktree `C:\Users\hunte\Hrns\flatfix-wt`, branch `feat/v7-flat-band`, uncommitted.
   - Code: opt-in objective v7 key `flat_band: band | scored`. `band` is the legacy default and is never written to the
     config, so every existing v7 config keeps its config_sha (`d15f2c0e0a19` checked under the old code, the new code
     and the live H1 run).
   - Tests: 5 new in `tests/test_objective_v7.py`. The objective, config and BO suites pass with no failures.
   - Brief: `room_80x60_700_hf1440_v7b.yaml` (= v7 + `flat_band: scored`).
   - Offline effect on 878 stored home designs:
     - Spearman 0.998, top-20 overlap 17/20, and the ext-throat winner is unchanged.
     - ATH-core median `flat` falls 3.46 → 1.21 dB, so roughly two-thirds of its old "roughness" was roll-off below
       the crossover.
     - Best ATH-core J 5.37 → 4.59, and the ATH-core vs ext-throat gap shrinks 2.14 → 1.39.
   - Merge after `sab_home_gpu_2026-11-14` finishes: the night's later jobs import this checkout's code.
   - `flat_cv`'s 3 kHz edge is not changed.
3. **Score the listening window, not 0°,** and split it into an EQ-able part (broad LW deviation, ignored or lightly
   weighted in DSP mode) and a non-EQ-able part (the angle spread above, plus LW narrow-band deviation in ½-octave
   bands, Olive-style).
4. **Make the playback chain a brief setting:** `eq: dsp` (score only the non-EQ-able parts) vs `eq: passive` (also score
   broad LW shape against what a simple passive CDEQ can deliver, plus efficiency / loading). The owner says DSP, so
   `dsp` is the default for the home brief.
5. **Raise the scoring resolution in XO-10 kHz** to ~6 points/octave (18 → ~28 frequencies, ~+50 % per eval before
   batch-12), or at minimum re-rank finalists on verify-grid data.
6. **Validate offline before any GPU:** done at screen resolution (section 3b): no material re-ranking. Next, run
   `hifi_rescore.py --verify` on the `sab_home_gpu_2026-11-14` verify output. Adopt the terms into a scored objective
   only if verify-grid data shows they separate designs by audible amounts. Until then, report them next to J for
   finalists. Item 2 (start `flat` at the XO) is a correctness fix worth making regardless.

Caveat that applies to every on-axis number here: the solver drives a uniform-velocity throat, not a real compression
driver. The driver's own response (breakups, phase plug) is absent, so an absolute "flat without EQ" claim cannot be
validated in simulation. The horn-only, angle-dependent behaviour can.

## Sources

- Olive, "A Multiple Regression Model for Predicting Loudspeaker Preference Using Objective Measurements", AES 116th
  conv. 2004 (parts I/II): https://aes2.org/publications/elibrary-page/?id=12794 ,
  https://aes2.org/publications/elibrary-page/?id=12847 ; patent https://uspto.report/patent/app/20050195982 ;
  Toole, *Sound Reproduction* ch. 20 https://www.oreilly.com/library/view/sound-reproduction/9780240520094/28_chapter20.xhtml
- Toole & Olive, "The Modification of Timbre by Resonances", JAES 36(3) 1988: https://www.aes.org/e-lib/browse.cfm?elib=5163
- CTA-2034 summary: https://cinemaconfig.com/reference/spinorama-cta-2034
- Geddes on waveguides (HOMs, CD needs EQ): https://www.diyaudio.com/community/threads/geddes-on-waveguides.103872/page-75 ;
  interview https://www.tnt-audio.com/intervis/geddes_e.html
- ATH thread (all-axis dips = driver, EQ-able): https://www.diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/page-637
- CD horn EQ (Keele / CDEQ): https://t-linespeakers.org/tech/crossover/frequency_response.html ; https://pispeakers.com/AES_v31_n6_p408.pdf
- Passive / SET horn practice: https://www.diyaudio.com/community/threads/beyond-the-ariel.100392/post-3502087 ;
  https://www.stereophile.com/content/odeon-la-traviata-loudspeaker
