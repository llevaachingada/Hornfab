# Gate A: the 650–900 Hz "loading hump" around the 700 Hz crossover

Fable senior, 2026-11-19. This is the follow-up to `../score_term_audit_2026-11-19/REPORT.md` and answers the senior direction of the same day.

- Everything here is a CPU, read-only replay of stored solves. No BEM solve was run, nothing was queued, no default was changed, nothing under `runs/` was rewritten, and nothing was committed.
- To reproduce: `.venv\Scripts\python.exe scratch\fable_architecture\xo_loading_gateA_2026-11-19\gate_a.py --out <new dir>`.
- Outputs from this session are in `runs/analysis/xo_loading_gateA_2026-11-19/`:
  - `summary.json`;
  - `per_frequency.csv` (6 designs × every stored grid);
  - `driver_bracket.csv`;
  - `duplicate_hashes.json`.

Labels used below: **VERIFIED** means recomputed here from stored arrays. **INFERRED** means a model or engineering reading.

## Verdict

**The diagnosis in my audit is withdrawn. The feature is mostly ordinary near-cutoff loading of a well-loaded horn. It is not a large resonance, and `load` is not rewarding a harmful one.**

Confidence: moderate to high on the magnitude, which is VERIFIED. The narrow-band shape between stored samples is still unresolved.

1. **My audit's dB figures were an artefact of how the source is normalised. VERIFIED.**
   - The solver drives the throat with unit normal **acceleration** (`meta.spl_reference`).
   - F6 quoted +8/+9 dB on-axis and +11/+10 dB power at 643/828 Hz relative to 2 kHz for fold_warm. Those numbers are exactly the acceleration-referenced levels (8.30/9.16 and 11.2/10.4).
   - Converted to unit throat **velocity** (+20 log10 ω), the same horn gives on-axis −1.6/+1.5 dB and power +1.3/+2.8 dB.
   - The power figure matches the resistance ratio: 10 log10(Re z₈₂₈ / Re z₂ₖ) = 10 log10(1.93 / 1.03) = **2.7 dB**.
   - The reviewer's challenge (that 1.8× in resistance cannot give +10 dB) was correct. The extra ~7.7 dB is the factor ω² between 828 Hz and 2 kHz.
2. **Energy balance closes, so the stored data are consistent. VERIFIED.**
   - The power radiated over the full balloon (512 directions, sin θ quadrature, 10 m) divided by the throat input power ½ρc·Re z·S·|v|² gives **0.96–1.00** for all six designs and both grids. The 0.97–0.99 values above 1 kHz are consistent with a coarse 16×32 quadrature.
   - Response normalisation, z, area and balloon all agree. This is not a provenance or normalisation fault in the data. The fault was in my reading of it.
3. **Mechanism: a single cutoff-region overshoot, not a standing-wave train. VERIFIED (shape on 3–5 samples) / INFERRED (physics).**
   - For fold_warm and morph, Re z rises from 0.2 at about 450 Hz to a single maximum of 1.8–1.9 near 830 Hz, then settles to 1.0–1.3 from 1 kHz up. The minimum from 700–5600 Hz is ≥ 1.0.
   - The engineering-convention reactance falls from +1.6 (mass-like) at 643 Hz to ≈0 at 1.07 kHz. Over the same span the plane-wave |Γ| falls from 0.58 to 0.13.
   - This is the textbook finite-horn behaviour just above flare cutoff (Kolbrek 2008). It shows one resistance maximum while the reactance crosses zero, with no repeated sign changes.
   - The screen grid (18 points) and the verify grid (29 points) agree within 0.15 in Re z and 0.5 dB in power.
4. **The one design with genuine ripple is ext_throat, not fold_warm. VERIFIED.**
   - ext_throat_v7 a23763f1c6fc has Re z of 1.98 at 643 Hz, falling to **0.59–0.60 at 1.18–1.37 kHz** and recovering to 1.18 at 2 kHz.
   - On the verify grid, its velocity-referenced power deviates up to **3.1 dB** from a straight-line fit over 600–3000 Hz. That is the largest deviation of the six designs.
   - It passes `load` only because 0.59 is above the 0.5 hinge. This is the standing-wave-like ripple the reviewer warned about, and it is the expected signature of an extended throat. It is a finalist check item, not a scorer bug.
5. **The corridor-compliant horns are under-loaded, not unfairly punished. VERIFIED (fixed velocity) / INFERRED (driver).**
   - rosse_rect_cd and tritonia_v9 are **5–8 dB down** in power at 643–828 Hz relative to 2 kHz at fixed velocity.
   - Through a lumped HF1440-class driver at 2.83 V (bracket below), on-axis at 828 Hz is a median **−4.6 dB (rosse) and −2.5 dB (tritonia)**, against +1.5 dB for fold_warm.
   - With an ideal 700 Hz 12 dB/oct high-pass, the 643 Hz level relative to 2 kHz is a median −12.4 dB (rosse), −9.8 dB (tritonia) and −4.7 dB (fold_warm). The filter alone accounts for about −3.6 dB of that.
   - So rosse would need roughly 6–9 dB of boost just below the crossover. That costs excursion and distortion headroom, which is exactly what `load` exists to price.
   - My audit's framing ("compliant horns lose 1.2–2.5 J on loading alone") was arithmetically true but physically backwards. The loss is earned.
6. **Does the overshoot help a real HF1440 + horn + 700 Hz crossover? On this evidence it helps or is neutral. INFERRED.**
   - Across the whole bracket, fold_warm's voltage-driven on-axis response has the smallest deviation from a straight-line fit over 600–3000 Hz of any non-ext design: median max residual 1.0 dB, against 2.3 dB (tritonia) and 2.75 dB (rosse).
   - Model limits:
     - lumped piston driver, no phase-plug modes;
     - Bl, Mmd, Sd, fs and Qms are not published by FaitalPRO, so a bracket is used (see the next section);
     - ideal voltage filter with no impedance interaction;
     - no woofer summation;
     - no time-domain check.

## The HF1440 bracket

FaitalPRO publishes Re 6.8 Ω, an 86 mm coil, a 35.8 mm exit, a 0.7 kHz minimum crossover at ≥ 12 dB/oct, and 109 dB at 1 W/1 m averaged over 0.5–20 kHz. It does not publish Bl, Mmd, Sd, fs, Qms or chamber volumes. The model therefore uses 32 combinations:

| Parameter | Values |
|---|---|
| Sd | 30, 45 cm² |
| Mmd | 1.5, 3 g |
| Bl | 12, 18 T·m |
| fs | 450, 700 Hz |
| Front chamber | 0, 3 cm³ |
| Re, Le, Qms (fixed) | 6.8 Ω, 0.05 mH, 3 |

The model is `hornlab_search/driver/compression.drive`, unchanged. Absolute levels are not meaningful. Horn-to-horn differences on one driver are the module's stated strength.

| design (stored grid) | Re z at 643 / 828 / 1065 Hz | power re 2 kHz, 643 / 828 Hz (velocity-ref) | on-axis 828 re 2 kHz, driver at 2.83 V (min / median / max) | 643 re 2 kHz with 700 Hz HP (median) | detrended on-axis bump, driver (median) |
|---|---|---|---|---|---|
| fold_warm best 00826f071b24 (screen) | 1.39 / 1.93 / 1.29 | +1.3 / +2.8 | +0.5 / +1.6 / +4.1 | −4.7 | 1.0 dB |
| fold_warm 688ffe811b6a (verify, 29 pts) | 1.17 / 1.79 / 1.34 | +0.2 / +2.4 | +0.3 / +1.3 / +3.8 | −5.6 | 0.8 dB |
| morph_v7 436a4d221328 (screen) | 1.42 / 1.80 / 1.30 | +1.5 / +2.5 | −0.8 / +0.2 / +2.6 | −6.0 | 1.1 dB |
| ext_throat_v7 a23763f1c6fc (verify) | 1.98 / 1.53 / 0.68 | +1.8 / +1.0 | −1.0 / +0.1 / +2.9 | −4.9 | 1.0 dB (power 1.6) |
| tritonia_v9 3050a4666f51 (screen) | 0.29 / 0.50 / 0.88 | −6.0 / −3.7 | −3.7 / −2.5 / −0.4 | −9.8 | 2.3 dB |
| rosse_rect_cd fd45d3b5e62f (screen) | 0.19 / 0.34 / 0.57 | −7.8 / −5.2 | −6.0 / −4.6 / −2.3 | −12.4 | 2.75 dB |

## What each earlier pass got right and wrong

- **The first review handoff.**
  - **Wrong** on dislope = 0. Audit F1 stands: removing dislope promotes beaming horns.
  - **Wrong** on side lobes (F3) and on `max_edge` (F4).
- **My audit.**
  - **Right** on F1–F5, on F7's attribution (`load` is most of the screen→verify spread) and on F8 provenance.
  - **Wrong** on F6's magnitude and on its implication. The owner question it posed is withdrawn.
  - Decision 3, the hold on J-only continuations, is lifted: the objective is not shown to be biased toward a harmful feature.
- **This senior direction.**
  - **Right** on 1.8× versus +10 dB, on energy balance, on hash ≠ field, and on 0.055 J not being a confidence interval (see below).
  - Its leading hypothesis ("plausible scoring failure") is **not supported**. fold_warm passes `load` through sustained loading (Re z ≥ 1.0 from 700 to 5600 Hz, lfp20 at 446 Hz), not through a peak that only helps the interpolated first crossing.

**What could still overturn this verdict**

1. A narrow, high-Q feature between the stored samples (643 → 828 → 1065 Hz, and 1065 → 1763 Hz for ext_throat).
2. Real HF1440 parameters outside the bracket.
3. Internal driver or phase-plug modes.
4. Woofer summation through the real filter.
5. Time-domain stored energy near cutoff. `docs/research/TIME_DOMAIN_RINGING.md`: impulse analysis is "only valid on a dense grid".

## Floors and identity (Gate A items 1, 2 and 4)

- **Parity.** `score_term_audit.py` recomputes J from the stored `response.npz` through `objective.replay`; it does not compare cached J fields to each other. It reproduces the published v10 column with max |ΔJ| = 0.0 on 271 designs. VERIFIED.
- **Duplicate hashes: 205 hashes sit in more than one design directory. VERIFIED.**

  | Count | What the copies are | How they differ |
  |---|---|---|
  | 95 | Screen and verify copies of the same run | Different frequency grids (18 vs 29), same mesh |
  | 99 | Repeated screen solves | Bit-identical |
  | 2 | Repeated screen solves | Within 7·10⁻⁷ (GPU repeat noise) |
  | 9 | Different meshes (`__refine_epw12` at ~4× DOF, or 4861 vs 8471 DOF) | Up to 0.019 in z and 0.21 dB SPL |

  - The 9 mesh cases are the "J moved by up to 0.011" seen in the audit. **The same hash is not the same acoustic field.**
  - The row's own run directory is authoritative. The leaf-name fallback is safe today only because all 4 leaf-name collisions are numerically identical copies.
- **Provenance fix (my lane, additive).**
  - `tools/analysis/rescore_identity.py` now writes `run_path` (the run relative to `runs/`, e.g. `study-x/screen`) next to the unchanged `run` field, in rescore and floor rows.
  - Covered by `test_run_path_keeps_nested_study_runs_locatable`. 13 tests pass.
  - Historical rescore files are not rewritten. The next rescore carries the field.
- **0.47 J vs 0.055 J.**
  - Both are screen→verify SDs over the same pairs, so they are frequency-sampling sensitivities only. Neither contains a mesh part (B1 owns that) or seed variance.
  - 0.055 J is the SD of the directivity subtotal (cov + rip + dislope + di_roughness) on the top 28. It is **not** the uncertainty of a redesigned objective and must not be used as one.
  - The 9 mesh-refined duplicates bound the mesh part for those designs at ≤ 0.011 J. That is only a small sample.

## Recommendation

1. **Keep v10 unchanged. No v11 is justified by this evidence.** Keep `dislope`. Keep historical identities.
2. **Add report-only finalist diagnostics. Do not add them as a score term.** The diagnostic set is what `gate_a.py` already computes:
   - velocity-referenced power and on-axis level re 2 kHz, plus their detrended residual, over 600–3000 Hz;
   - Re z, Im z and |Γ| at the crossover;
   - the energy-balance ratio;
   - the driver-bracket spread with a 700 Hz high-pass.

   It catches the ext_throat ripple and the rosse under-loading without charging fold_warm. Promoting any of it to a weighted term would need the Gate C counterexample pair (reject a false winner, keep an ATH-like extended throat), which this evidence does not yet supply.
3. **Shrink and reframe the dense solve.**
   - Replace the six-design 1/12-octave proposal with three designs at **1/24 octave over 450–1800 Hz** (about 48 points, the cheapest band, `HORNLAB_GPU_LOCK=refuse`): fold_warm 00826f071b24, ext_throat a23763f1c6fc, and rosse fd45d3b5e62f as the under-loaded control.
   - Purpose: resolve the overshoot Q and the ext_throat dip between samples, give the ringing check its dense input, and size the `load` sampling floor.
   - This is owner-gated GPU time and not urgent: nothing in the scorer waits on it.
4. **Lift audit decision 3.** v10 CMA continuations are fine at the integrator's discretion. Decision 2 still holds: equal-budget B6 reruns on the current grid cannot separate a tie whose spread is loading-edge sampling (F7).
5. **Gate D (V2 / PR #75) is integrator scope and is untouched here.** A mouth beak cannot be expected to move a throat-region feature. Use these diagnostics on V2 and its exact host control when it lands.

## Owner decisions actually required

1. **V corridor onset** (audit F5, still open). Is 40–60° V from 1 kHz reachable in a 480 mm height? Either accept about 63° at about 1 kHz, or move the onset to about 1.2 kHz.
2. **GPU time** for the three-design dense check in recommendation 3, when the queue is free.
3. ~~Real HF1440 data~~ **Resolved: the driver is open** (owner, 2026-11-19: "we can assume other drivers as well").
   - The horn conclusions do not depend on which driver is used. In **all 32** bracket drivers, each pair below is separated by at least the minimum shown:

     | Comparison | Minimum (range) |
     |---|---|
     | fold_warm over rosse, on-axis at 828 Hz re 2 kHz | 4.3 dB (4.3–7.4) |
     | fold_warm over rosse, at 643 Hz with a 700 Hz HP | 5.4 dB (5.4–9.2) |
     | fold_warm over tritonia, on-axis at 828 Hz | 2.6 dB |
     | morph over rosse, on-axis at 828 Hz | 3.0 dB |
     | fold_warm smoother than rosse (detrended max residual) | 1.3 dB (1.3–2.2) |

   - The bracket's Bl of 12–18 T·m covers the published 1.4" values of 18 Sound ND1460A/NSD1460N (13.5) and RCF ND950 1.4 (17.6).
   - No 1.4" pro driver checked publishes Mmd, Sd or fs. FaitalPRO HF1440, 18 Sound ND1460A/NSD1424BTN/NSD1460N, RCF ND950 1.4, Celestion CDX14-3040 and Beyma CD-1114Fe all leave them out. So any absolute level or headroom claim needs an impedance-curve fit or a measurement, whichever driver is chosen.
   - **The 700 Hz crossover narrows the driver field.** Published minimum crossovers are:

     | Rating | Drivers |
     |---|---|
     | 0.7 kHz | HF1440, CD-1114Fe |
     | 0.8 kHz | ND1460A |
     | 1.0 kHz | CDX14-3040 |
     | 1.2 kHz | NSD1424BTN |

     A 1" or 2" driver would need the throat re-meshed, because the stored solves are 35.8 mm.
