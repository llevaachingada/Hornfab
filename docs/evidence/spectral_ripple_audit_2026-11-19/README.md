# Fixed-angle spectral ripple audit of the SCOUT40 archive (2026-11-19)

Mandate item 1 of [`docs/research/ripple_hf_2026-11-19/HANDOFF_2026-11-19.md`](../../research/ripple_hf_2026-11-19/HANDOFF_2026-11-19.md):
reproduce and check the handoff's data audit. **Report-only diagnostic — never a score term.
Zero solver calls. No new BEM. No stored `J` changed.**

Tool: `tools/analysis/spectral_ripple_audit.py` (metric functions in
`hornlab_search/metrics/spectral.py`). Data: the 24 committed runs under
`docs/evidence/runs/scout40_2026-11-19/`, one best design each (`best.json` → `designs/<hash>`).

## Reproduction command

```powershell
.venv\Scripts\python.exe tools/analysis/spectral_ripple_audit.py `
    docs/evidence/runs/scout40_2026-11-19/* `
    --out docs/evidence/spectral_ripple_audit_2026-11-19/audit
```

Raw output committed beside this file: `audit/audit.json` (all rows, provenance, sensitivity scans,
symmetric pairs, identity checks) and `audit/disagreement.md` (the table below plus its legend).
The per-design `design_<hash>.json` files the tool also writes were regenerable duplicates of
`audit.json` rows and are not committed; re-running the command above recreates them.

Provenance recorded by the tool: `git_head`, UTC timestamp, interpreter, numpy version, argv, band,
detrend orders and angle sets. Every row carries `design_hash`, `family` and `objective_version`;
a rank column appears only when all rows share one version (**all 24 are v7**, verified — no SCOUT40
run is v10).

## 1. The handoff's table reproduces exactly

`V+25` / `V+35` = RMS residual in dB after a quadratic in `log2 f` over the 10 stored samples in
1,065–4,832 Hz, on the vertical cut normalised to 0°. Every value the handoff published matches to
≤ 0.002 dB:

| design (`design_hash`) | handoff V+25 / V+35 | audit V+25 / V+35 | `J` | 8 kHz H/V |
|---|---|---:|---:|---:|
| Klangfilm C200 (`14e53020adbe`) | 1.090 / 2.247 | **1.090 / 2.247** | 10.156 | 38.7° / 31.7° |
| Klangfilm B3 current (`ee85bcd2ad67`) | 1.151 / 1.441 | **1.151 / 1.441** | 2.800 | 42.4° / 41.1° |
| Klangfilm B3 previous (`e4d38596e2a8`) | 0.950 / 1.947 | **0.950 / 1.947** | 3.540 | 41.7° / 40.2° |
| OSSE morph (`cf716e738ef8`) | 0.497 / 0.822 | **0.497 / 0.822** | 3.402 | 59.9° / 50.4° |
| Extended throat (`c1d088b8b92f`) | 0.601 / 0.774 | **0.601 / 0.774** | 3.565 | 61.7° / 56.1° |
| R-OSSE rectangular (`efe4a8959d85`) | 0.382 / 0.596 | **0.382 / 0.596** | 4.560 | 64.4° / 46.8° |
| Crowe X OSSE (`9b5428e6dec8`) | 0.266 / 0.351 | **0.266 / 0.351** | 5.345 | 74.0° / 53.9° |
| Le Cléac'h smooth (`5381c9cea1ec`) | 0.053 / 0.058 | **0.053 / 0.058** | 8.037 | — |
| Klangfilm Lame (`f2054faaa9d4`) | 0.038 / 0.117 | **0.038 / 0.117** | 8.393 | 60.4° / 44.0° |
| Tritonia v8 (`2979e2d125ce`) | 0.302 / 0.342 | **0.302 / 0.342** | 5.325 | 56.6° / 49.5° |
| Tritonia v9 (`73cf78b059a5`) | 0.431 / 0.257 | **0.431 / 0.257** | 5.289 | 56.5° / 48.5° |

Also reproduced from `best.json` / `metrics.json`: `J`, `lfp50_hz`, `rez_min_from_fx`, the weighted
`load` term and the 8 kHz H/V beamwidth for all five designs the handoff discussed. Its specific B3
defect claim also holds in the stored arrays — `spl_v(+25°) − spl_v(0°)` reads −6.88 dB at
1,763 Hz, −6.74 at 2,269, −3.61 at 2,573, −3.64 at 2,919 and −4.88 at 3,311 Hz, while the complex
normalised throat impedance there is 0.966 − 0.122j, 1.016 − 0.135j and 0.983 − 0.136j, i.e. **no
large impedance feature at the sampled frequencies**, exactly as the handoff says.

## 2. The full 24-design table (all `objective_version` 7)

`rip(term)` = the objective's own weighted `rip` contribution (`best.json` `terms.rip`), i.e. what
`J` charged; it is an **angular** residual at fixed frequency. `BM+35` = deviation from the in-band
mean (IEC 60268-5 §20.6 / Klippel AN 40 definition). `spread` = max − min of the +25/+35 trend
residual over detrend orders 1–3.

| `design_hash` | family | `J` | `rip(term)` | V+25 | V+35 | BM+35 | spread |
|---|---|---:|---:|---:|---:|---:|---:|
| `ee85bcd2ad67` | FREEFORM (B3 current) | 2.800 | 0.408 | 1.151 | 1.441 | 1.711 | 0.402 |
| `15a8c964d592` | FREEFORM (B3 w) | 2.841 | 0.429 | 1.292 | 1.538 | 1.790 | 0.327 |
| `cf716e738ef8` | OSSE (morph) | 3.402 | 0.246 | 0.497 | 0.822 | 0.903 | 0.265 |
| `e4d38596e2a8` | FREEFORM (B3 prev) | 3.540 | 0.455 | 0.950 | 1.947 | 2.097 | 0.137 |
| `c1d088b8b92f` | OSSE (ext throat) | 3.565 | 0.269 | 0.601 | 0.774 | 0.914 | 0.369 |
| `58bde4024d87` | OSSE (fold) | 3.754 | 0.236 | 0.460 | 0.299 | 0.489 | 0.559 |
| `efe4a8959d85` | FREEFORM (R-OSSE rect) | 4.560 | 0.098 | 0.382 | 0.596 | 0.853 | 0.132 |
| `febde0373489` | FREEFORM (crowe v2a) | 4.879 | 0.250 | 0.672 | 0.746 | 1.396 | 0.179 |
| `4d2985321ccf` | OSSE (ath core petal) | 4.892 | 0.222 | 0.779 | 0.831 | 0.920 | 0.480 |
| `73cf78b059a5` | OSSE (tritonia v9) | 5.289 | 0.197 | 0.431 | 0.257 | 0.641 | 0.210 |
| `2979e2d125ce` | OSSE (tritonia v8) | 5.325 | 0.191 | 0.302 | 0.342 | 0.825 | 0.446 |
| `9b5428e6dec8` | FREEFORM (Crowe X OSSE) | 5.345 | 0.118 | 0.266 | 0.351 | 0.905 | 0.062 |
| `0705e7b08d4f` | FREEFORM (biradial ES) | 6.327 | 0.339 | 0.989 | 1.052 | 1.282 | 0.093 |
| `06a008612260` | FREEFORM (lecleach iwata ar w) | 6.671 | 0.089 | 0.490 | 0.610 | 2.190 | 0.237 |
| `04501fa6edc8` | FREEFORM (lecleach iwata ar) | 6.763 | 0.101 | 0.601 | 0.674 | 2.104 | 0.271 |
| `3c5dae091e52` | FREEFORM (crowe x square) | 7.911 | 0.143 | 0.335 | 0.537 | 0.761 | 0.466 |
| `1dab547b5a86` | FREEFORM (lecleach hv w) | 8.036 | 0.032 | 0.053 | 0.051 | 2.352 | 0.214 |
| `5381c9cea1ec` | FREEFORM (lecleach hv) | 8.037 | 0.028 | 0.053 | 0.058 | 2.298 | 0.207 |
| `7be037ff53c5` | FREEFORM (lame w) | 8.350 | 0.049 | 0.037 | 0.118 | 2.362 | 0.224 |
| `f2054faaa9d4` | FREEFORM (lame) | 8.393 | 0.049 | 0.038 | 0.117 | 2.363 | 0.224 |
| `00753b8200ac` | FREEFORM (C200 w) | 10.020 | 0.352 | 1.215 | 2.092 | 3.883 | 0.554 |
| `14e53020adbe` | FREEFORM (C200) | 10.156 | 0.391 | 1.090 | 2.247 | 3.917 | 0.551 |
| `9c39541262aa` | FREEFORM (rf rect control270) | 19.706 | 0.015 | 0.073 | 0.097 | 2.405 | 0.066 |
| `8ba61395b295` | FREEFORM (rf rect cap225) | 19.721 | 0.014 | 0.077 | 0.125 | 2.362 | 0.053 |

## 3. What the audit changes about the handoff's argument

These are the results of the checks the mandate asked for (cut/identity validation, symmetric ±,
metrics-vs-npz comparison, detrend and angle sensitivity, identity preservation). Two of them
**qualify** the handoff.

**(a) The reference choice flips the ranking — so neither number is a target yet.**
Spearman ρ between the trend residual and the band-mean residual at +35° is **−0.018** across the 24
designs: the two references are effectively orthogonal. The cause is visible in the table — the
band-mean reference charges the *smooth taper itself*, which is why the four Le Cléac'h / Iwata /
Lame designs sit at the bottom on `BM+35` (2.10–2.36 dB) while being the smoothest designs of all on
the trend residual (0.04–0.12 dB). That is exactly the failure mode
[`MEASUREMENT_TAXONOMY.md`](../../research/ripple_hf_2026-11-19/MEASUREMENT_TAXONOMY.md) §4 warns
about: a CD-shaped smoothness target would forbid a legitimately narrowing horn. **Consequence: the
trend variant is the only defensible cross-family number, it must be labelled exploratory, and a
band-mean number may only be quoted within one family.** The handoff's choice was right for the wrong
reason — it is not merely a detrending convention, it decides the verdict.

**(b) The number is largely redundant with `rip` on this sample.**
Spearman ρ(`rip(term)`, trend V+35) = **0.885** (p ≈ 9 × 10⁻⁹), Kendall τ = 0.68, 44 discordant pairs
of 276 (16 %). So across these 24 bests the fixed-angle residual mostly re-orders the same designs
`rip` already ranks. What it adds is *degree* and *location* (the B3 notch band), not a new axis.
This is evidence **against** promoting a weighted term now, and it is the honest answer to the
handoff's "J is missing this": J is not blind to it, it is under-charging a defect it partly sees.

**(c) Detrend order is stable; absolute values are not.**
ρ(order 1, order 2) = 0.955; ρ(order 2, order 3) = 0.959. Ranks are robust to the fit order, but the
per-design spread over orders 1–3 reaches **0.559 dB** (median 0.231, minimum 0.053). Any *absolute*
threshold ("worse than 1 dB") is therefore an artefact of the order; only comparative statements
survive.

**(d) The symmetric ± check is not an independent check here.**
All 864 ± pairs agree to **≤ 1.1 × 10⁻⁶ dB**. These runs are `symmetry: hv`, so `−θ` is the mirrored
`+θ` from one solve — the equality is a property of the mesher, not a validation of the metric.
A genuine asymmetry test needs an unsymmetric build (e.g. `symmetry: none`) or the `h` vs `v` planes,
not ± on the same cut.

**(e) Cut/metrics identity holds, with one stored convention to remember.**
Across all 24: `metrics.json["on_axis_db"]` equals the npz 0° cut to **1.8 × 10⁻¹⁵ dB** after a
constant offset of 11.6–15.5 dB, because the stored `on_axis_db` is **band-mean-normalised**
(`types.py`). The frequency arrays match exactly (`max_freq_rel_err = 0`). The tool reports both the
raw offset and the mean-removed shape difference so the convention cannot be mistaken for a defect.

## 4. What this evidence does *not* establish

- Not that the B3 feature is a resonance, a mode, or diffraction. An 18-point log frequency grid
  (≈1/3 octave there) cannot separate those, and cannot establish ringing
  ([`docs/research/TIME_DOMAIN_RINGING.md`](../../research/TIME_DOMAIN_RINGING.md)).
- Not that Crowe X OSSE is better. Its trend residual is the best of the *loaded* designs, but its
  `lfp50 ≈ 986 Hz` and `rez_min_from_fx ≈ 0.342` make it a poor 700 Hz horn, and the uniform-velocity
  source above the 5.61 kHz throat cut-on limits any 8–16 kHz claim.
- Not a scoring change. No term, no weight, no version, no stored `J` was touched.

## 5. Verification

```
.venv\Scripts\python.exe -m pytest -o addopts="" -q -p no:cacheprovider ^
    tests/test_metrics_spectral.py tests/test_tools_analysis_spectral_ripple_audit.py
-> 14 passed in 0.27s   (exit 0)

.venv\Scripts\python.exe tools/analysis/spectral_ripple_audit.py docs/evidence/runs/scout40_2026-11-19/* ^
    --out docs/evidence/spectral_ripple_audit_2026-11-19/audit
-> docs/evidence/spectral_ripple_audit_2026-11-19/audit   (exit 0; 24 rows, 26 files)

.venv\Scripts\python.exe -m compileall -q hornlab_search\metrics\spectral.py tools\analysis\spectral_ripple_audit.py
-> exit 0
```

The four archive reproduction values are asserted in `tests/test_metrics_spectral.py`, so a future
change to the metric definition cannot silently break parity with the published audit.
