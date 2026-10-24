# Report 1. Audit: bugs, objective assumptions, parameters, source model

Senior investigative pass, 2026-10-24 (Opus, read-only on code; nothing in `hornlab_search/` was changed).
Labels: **[measured]** computed here from repo data or a script in `evidence/`; **[verified]** read in source;
**[inferred]** reasoning or arithmetic shown; **[unverified]** not checked.

Implementation steps for every finding are in [`04_IMPLEMENTATION_PLAN.md`](04_IMPLEMENTATION_PLAN.md).

## 0. Bottom line

The solver chain is sound: DI quadrature, impedance sign, symmetry pairing, beamwidth threshold, budget/resume and
the classical-profile formulas all check out (section 6). **The weak part is the objective.** Three of the six terms
mostly measure things that are not horn quality, and between them they make up about 60–70 % of J for the current
best designs:

| Term | Share of J (best designs, measured) | What it mostly measures today | What it should measure |
|---|---|---|---|
| `rip` | ~40 % | the **shape of the beam taper** (an ideal smooth beam already scores ~3.8) | ripple about a smooth beam |
| `flat` | ~10–15 % | **drive-induced on-axis tilt** (−2 to −3.6 dB/oct from the unit-acceleration source) | on-axis roughness after an EQ-able tilt is removed |
| `di` | ~1–3 % | **a fixed 2.5 dB offset** between the target formula and any real beam | nothing it can't already get from `cov` + `dislope` |

So today's ranking of typologies and designs is partly a ranking of beam-top flatness and source tilt. The
existing campaign conclusions (for example, osse_axi beating blend_osse_tractrix) may survive a corrected objective,
but they **must be re-checked** before anyone quotes them as "typology A is better".

There is also a fairness bug: briefs fix the driver exit for generator typologies but **not for the native families**
(OSSE, R-OSSE, ICW, FREEFORM). R-OSSE winners use a 8–12° throat on a 5° driver.

## 1. Findings, ranked

### F1 (high). The ripple term rewards flat-top beams, not smooth ones

`metrics/smoothness.py:11` `ripple_db` is the sample std of normalized dB over ±coverage/2. A pattern that falls
smoothly from 0 dB on axis to −6 dB at the coverage edge has a large std even with **zero ripple**, because the taper
itself is variance.

**[measured]** (`evidence/objective_assumption_checks.py`): ideal smooth tapers on the 73-point grid score
1.98 dB (60° coverage), 1.92 dB (90°) and 1.89 dB (120°) per plane. Gaussian and cosⁿ give the same answer. So
`rip = ripple_h + ripple_v` has a **floor of about 3.8 for a perfect constant-directivity horn**.

**[measured]** (`evidence/on_axis_tilt_from_runs.py`): the last 12 freeform_sculpt best designs read 2.3–2.9 dB per
plane. Roughly 70–80 % of the ripple term is the taper, and only the rest is ripple.

**Consequence [inferred].** The only way to push `rip` below ~3.8 is a pattern that stays near 0 dB across the
coverage and then drops sharply (a flat-top beam). That fights `cov` (which wants −6 dB exactly at the edge) and
distorts the trade-off at every frequency. With weight 1.0 it is the largest single term in J.

**Fix.** Measure ripple about a smooth beam:
- `ripple_detrended_db`: fit `n(θ) ≈ a0 + a2·θ² + a4·θ⁴` (least squares, even in θ, over the same coverage
  samples and floor) and take the std of the residual. An ideal taper reads ~0; real lobing and notches still read
  high.
- Optional separate `beam_shape` term (flat-top vs taper preference) if a brief wants one; `metrics/beam_shape.py`
  already computes a shape exponent as a report-only value.

### F2 (high). The flatness term is mostly source tilt

`objective/terms.py:82` `flat_term` is the std of on-axis dB over the band. The solver drives **unit normal
acceleration** (`solve/beat.py:361`, `velocity_sources={2: 1.0}`; library docstring: results are converted to the unit-
acceleration convention). In a loaded horn (Re z ≈ const) constant acceleration gives volume velocity ∝ 1/f, so
on-axis SPL falls ~6 dB/oct at constant DI [inferred: W = Re(Z)|U|², U = aS/ω].

**[measured]** best designs (12 runs): on-axis tilt −2.0 to −3.6 dB/oct; on-axis std 2.6–4.3 dB raw, 1.6–2.9 dB after
removing a straight line in log f. About a third of `flat` is tilt.

Normalizing to velocity (+20·log10 f) is **not** the fix: it overcorrects (std 3.3–4.1 dB, tilt becomes positive).
A real compression driver is resistance-controlled (≈ constant velocity) below its mass corner (typically
3–5 kHz [unverified for specific drivers]) and mass-controlled (≈ constant acceleration) above it. Either way the
tilt is EQ'd in the crossover.

**Fix.** `flat_detrended`: std of the residual of on-axis dB after a linear fit in log2 f. It is drive-agnostic,
and it measures what EQ cannot cheaply remove. The absolute response belongs to a driver model (Report 3, section 6),
not to the geometry objective.

### F3 (high, fairness). Brief driver exit is not enforced on native families

`config.py:210-211`: a brief replaces only `target` and `weights`. For generator typologies `registry.materialize`
pins the throat to the brief driver (`r0`, `a0`), but native-family configs keep their own:
- `examples/rosse_baseline.yaml:34` and `osse_baseline.yaml:19` search `a0_deg` in [2, 30]°; the hifi brief says 5°.
- **[measured]** best R-OSSE designs (runs `…055352Z-screen-483828`, `…060407Z-screen-1de7e7`): `a0_deg` = 12.4° and 8.3°.
- `osse_baseline.yaml` has `r0_mm: 17.78` (1.4"), which matches no 1-inch brief.

The source cap is built from the horn's own throat angle (`source.cap: auto`, r = r0/sin θ_throat), so the BEM always
sees a matched source. A real 5° driver would see a throat-angle step that the model never pays for. Family-vs-family
leaderboards that include native families are therefore not on one objective.

**Fix.** When a brief is applied to a native family, pin `r0_mm` to `driver.exit_radius_mm`, and either pin `a0_deg`
to `driver.exit_angle_deg` or allow it and report `throat_angle_mismatch_deg`. Refuse a config whose pinned `r0_mm`
disagrees with the brief, as the envelope check does now.

### F4 (medium). Classical generators ignore the driver exit angle

`design/generators/profiles.py:75` and related: conical, exponential, hypex and tractrix start at their own formula
angle. For the axi brief a conical horn starts at about 37° on a 5° driver [inferred: atan((180−12.7)/220)]. That is a
throat discontinuity no designer would build, so the classical families lose partly for an avoidable reason.

**Fix.** Optional `throat_blend_mm` knob: over the first `L_b` mm, blend from an OS throat (angle = driver exit) into
the classical meridian with a C¹ smoothstep in z. With 0 it reproduces today's profiles exactly.

### F5 (medium). The DI target formula is ~2.5 dB below any real beam

`metrics/di.py:84` `target_di_db` uses the separable-rectangle formula on the target angles.
**[measured]** for ideal Gaussian beams with exactly the target −6 dB widths:

| coverage | formula target | ideal-beam DI | offset |
|---|---|---|---|
| 90×90 | 7.78 dB | 10.33 dB | 2.55 |
| 90×60 | 9.39 dB | 11.91 dB | 2.52 |
| 75×45 | 11.26 dB | 13.76 dB | 2.50 |

A horn that hits coverage exactly is still charged (2.5²/10)·0.3 ≈ 0.19 per frequency. The observed `di`
contribution of the best designs is 0.16–0.31, so **the term is measuring the formula offset** and nudging designs
slightly wider than the target. Small in J, but it acts against `cov` with no physical justification.

**Fix.** Either derive `di_target_db` from a beam model (numerical Gaussian-beam DI at the target widths), or set the
`di` weight to 0 and keep `dislope` (constant DI is what matters; its level follows from coverage).

### F6 (medium). `Target.freq_weights` is accepted and silently ignored

`targets/spec.py:16, 42-43` parse `freq_weights`, and nothing reads it (grep: no other use). This breaks the
codebase's own rule that a YAML typo must not be silent. A user who sets it believes the low band is down-weighted.

**Fix.** Implement it (a per-frequency weight vector applied in every `_mean`) or raise on the key. Implementing it
also gives a clean answer to F7.

### F7 (medium). Unavoidable low-band coverage error dominates `cov`

`cov` is a squared degree error with no tolerance. Below the mouth's pattern-control frequency
(Keele: f ≈ 25,000/(W_m·θ_deg); about 780 Hz for a 360 mm mouth at 90° [inferred]) no design can hold coverage, and
those frequencies are inside the 700 Hz band floor. One frequency at 60° error contributes 36/100 per term-frequency.
This is part of why the best designs ride the envelope (mouth size pinned at the bound in 3 of 5 pinned cases,
`docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md`).

**Fix (any of).** Set `band_lo_hz ≥ f_break(envelope)` in briefs; use per-frequency weights (F6); or use a Huber /
dead-band coverage error (`max(0, |e| − tol)²`, for example tol = 5°).

### F8 (medium). Polars at 2 m are near-field for large mouths at high frequency

`examples/osse_baseline.yaml:48` and all configs use `distance_m: 2.0`. **[measured]** Fraunhofer distance 2D²/λ:
400 mm mouth = 5.1 m at 5.5 kHz and 11.2 m at 12 kHz; 300 mm = 2.9 m and 6.3 m. A horn with a curved wavefront
converges sooner than a flat aperture does, so the bias may be small, but **it has never been measured**.

**Fix (measurement first).** Re-evaluate 3 finalists at 2, 10 and 50 m. Field evaluation from stored boundary
traces needs no new solve (`solve/traces.py`, `surface_traces=True`). If beamwidth moves by more than 1°, switch the
scored polars to 10 m or a true far-field kernel.

### F9 (medium). Balloon resolution is coarse for DI above ~5 kHz

`solve/base.py:84`: 512 points gives a 16×32 θ–φ grid (Δθ = 12°). At 12 kHz the 60° V beam is spanned by ~5 θ samples.
DI error at this resolution is unmeasured. Field points cost O(N_obs·N_dof), small next to the O(N²) assembly and
the O(N³) LU [inferred].

**Fix.** Measure DI at 512 / 1024 / 2600 points on two finalists. If the difference exceeds 0.1 dB, raise the screen
balloon (the grid is part of the record, so it is a new dataset group).

### F10 (medium). Frequency grid too coarse for mouth-reflection structure

`config.py:26` screen = 12 log points from 500 Hz to 10 kHz, clipped to band_hi, so about 3.2 points/octave.
**[measured]** throat-mouth resonance spacing c/2L = 660 Hz (L = 260 mm) to 1,430 Hz (L = 120 mm), about the same as
the grid spacing at 2–5 kHz (480–1,000 Hz). Ripple in frequency is aliased: two designs whose resonances fall on or
between grid points score differently by luck. CMA-ES sees that as landscape noise.

**Fix.** At least 6 points/octave for verify and finalist passes (cost is linear in the frequency count on CUDA,
which uses one call per frequency). Screen can stay coarse **if** finalists are re-ranked at verify density, which is
the existing practice. Make it explicit in the campaign tier rules.

### F11 (medium). Perturbation knobs move the mouth, and infeasible designs form a flat plateau

`profiles.py:371` `perturb_increments` scales every radius increment by exp(u). The mouth radius is the sum, so
shape knobs also change size. **[measured]** invalid-geometry rates: perturbed_osse_hv 30 %, rosse_baseline 31–40 %
(`runs/…/run.json` stats). Every infeasible design scores the same 1e3 (`search/evaluate.py:520`), so CMA-ES gets no
direction back toward feasibility.

**Fix.** (a) Renormalize increments so their sum is unchanged (pure shape knobs), and give mouth size its own knob.
(b) Graded penalty for envelope violations computed before meshing: `1e3 + 100·(relative overshoot)`, which stays
far above any valid J. (c) Optional pycma resampling of infeasible candidates.

### F12 (low–medium). Search hygiene

- No CMA restarts (`search/cma.py:157`). For compare-tier runs use BIPOP or IPOP restarts (pycma `cma.fmin2` with
  `restarts`, `bipop=True`). R-OSSE's two-seed spread (12.3 vs 14.3) is the signature of a multimodal landscape.
- `dislope` is one straight-line slope: a DI that wiggles ±2 dB around a flat line scores 0. Add
  `di_rough = std(detrended DI)`, report-only first.
- Throat-impedance ripple (`z_ripple`) is report-only on a 12-point grid. Fine as is; do not weight it until F10 is fixed.

### F13 (medium, physics scope). Free-standing only, although the mesher has an enclosure builder

`design/families.py:443` hard-codes `"mode": "freestanding"`. Magnus's mesher ships `builders/enclosure.py` (rounded
rectangle, ellipse and superellipse cabinets, fillet or chamfer edges) and `PointGridHornGeometry.enclosure`.
Hi-fi waveguides are used in a cabinet. Edge diffraction there changes polar ripple and DI below ~2 kHz, and the
free-standing shell's rear radiation is not what a listener hears. That changes which designs win (rollback mouths
are favoured in free space) [inferred].

**Fix.** A `mounting:` brief key (`freestanding` | `enclosure`, with a box size). First measure the dof cost; the
enclosure is mostly flat panels at the mouth resolution. Check that quarter symmetry is supported for the
rounded-rectangle sector path (the builder docstring says the open-domain sectors share it [verified]).

## 2. Source and driver assumptions

| Assumption | Status | Comment |
|---|---|---|
| Uniform normal-velocity spherical cap, r = r0/sin θ | fine below f11 | f11 = 7.9 kHz for a 1" exit (computed in every record). Above it, compare geometries only (already caveated). |
| Unit acceleration drive | wrong for **absolute** response, harmless for directivity | it drives F2. Directivity, DI and ripple are drive-independent ratios. |
| Rigid lossless walls, no air absorption | fine | Boundary layer at 12 kHz ≈ 0.02 mm vs a 12.7 mm throat [inferred]; air absorption is about 0.01–0.03 dB over horn length (Appendix B). |
| Free field, no baffle or cabinet | **limits realism** | F13. |
| Throat angle matched to source | **not enforced** | F3, F4. |
| One source tag | solver API limit | limits multi-source designs (multi-entry horns are deferred by the owner, Report 2 section 6). The Julia core supports several radiators and channels [verified, `BeatEngineDriver.jl:1145-1196`]; the Python `SolveConfig` refuses more than one tag [verified, `config.py`]. |

## 3. Parameter-by-parameter review (what makes sense for optimization)

| Config | Knob | Verdict | Recommendation |
|---|---|---|---|
| osse_baseline | `r0_mm` 17.78 pinned | mismatched to the 1" briefs | pin to the brief (F3) |
| osse_baseline, rosse_baseline | `a0_deg` [2, 30] | not physical for a fixed driver | pin to the exit angle, or search but report the mismatch (F3) |
| osse_baseline | `n` [2, 8], best at lo 2.0 (top-6 6/6) | bound binding | widen lo to about 1.2 after a mesher check (already recorded in ISSUES) |
| osse_baseline | `q` [0.90, 1.00] | fine | keep |
| osse/rosse | `aspect_ratio`, `exponent` | indirect V control | fine; the V coverage comes from the cross-section, so expect correlation with `a_deg` (CMA handles it) |
| rosse_baseline | `tmax`, `m`, `r`, `b`, `q` | 11 knobs, seed-sensitive | use restarts (F12); consider fixing `b` and `r` at defaults to cut the dimension |
| icw_termination | `hold_end` best at lo 0.55 | bound binding | widen per ISSUES note (respect hold_start < hold_end) |
| freeform_sculpt | per-anchor radius boxes | monotone by construction, good | keep; add angle-space parameterization as a separate family (Report 2, G6) |
| freeform_sculpt | throat angles pinned at 10° | should be the brief exit angle (5°) | pin to the brief, not to 10° |
| perturbed_* | `u_i` change shape **and** size | coupled | renormalize (F11) |
| perturbed_osse_hv | `L_mm` [90, 140], best at hi | bound binding | widen to 200 (already proposed in TYPOLOGY_COMPARE) |
| hypex/exponential | `L_mm` best at lo, `rm` at the envelope | the corner is the brief's | as recorded: the objective asks for a bigger, shorter horn |
| all briefs | `band_lo_hz` 700 | below f_break for the envelopes | raise, or use freq_weights (F6, F7) |
| all briefs | `dislope` target 0 | conventional | consider +1 dB/decade as an option (Geddes argues for slightly rising DI [unverified]) |

## 4. Bugs and smaller defects (code-level)

| # | Where | Defect | Severity |
|---|---|---|---|
| B1 | `targets/spec.py:16,42` | `freq_weights` parsed and unused (F6) | medium |
| B2 | `config.py:205-211` | brief does not pin the driver for native families (F3) | high (fairness) |
| B3 | `design/families.py:443` | mesher mode hard-coded `freestanding` | design limitation (F13) |
| B4 | `profiles.py:371` | perturbation couples size and shape (F11) | medium |
| B5 | `examples/freeform_sculpt.yaml` | throat angles pinned at 10°, not the brief's 5° | low–medium |
| B6 | `examples/briefs/*_12k.yaml` comment "never search at 12 kHz on 8 GB" | contradicted by measured 12 kHz dof counts for these sizes (Report 3, section 2) | doc |
| B7 | `examples/catalog.yaml` | `osse_baseline` (1.4", 75×45) is in group `magnus` and eligible under 1" briefs | low (F3) |

No bug was found in: `metrics/polar.py` beamwidth (−6.0206 dB threshold, outermost crossings), DI sin θ weighting
(`search/evaluate.py:208-240`), `z_throat` sign and normalization (`solve/beat.py`), symmetry pairing, CMA bounds
(pycma's BoundTransform returns in-bounds phenotypes, so the later clip is a no-op), hypex/exponential cutoff
conventions, the tractrix construction, or blend derivatives.

## 5. What the corrected objective changes, in one example [inferred]

A 90×60 design with perfect coverage, a smooth Gaussian taper, no ripple, constant DI and a −3 dB/oct tilt scores
today: rip ≈ 3.8, flat ≈ 0.5·3.0 = 1.5, di ≈ 0.19, so J ≈ 5.5 with zero real defects. Under the fixes it scores
J ≈ 0. The corrected objective spends its resolution on lobing, notches, HOM ripple and DI wiggles, the things that
actually separate good waveguides.

## 6. Verified-correct items (confidence)

- DI from the θ–φ balloon uses sin θ weights (`search/evaluate.py:208`), done correctly around a frozen function.
- `z = imp·(−iω)/(ρc)` is p/v in the e^(−iωt) convention; the sign is right.
- Quarter-domain symmetry flag derives from one table (`mesh/sizing.py`), and the solver adapter raises on mismatch.
- Budget, resume and cache semantics are consistent; 3-strike solver-unhealthy stop is sensible.
- Hypex m and f_c agree with the exponential limit; the tractrix uses the analytic sin θ = r/a.
- Evidence process (two seeds, spread rule, "not claimed" lists) is sound. The weakness is upstream of it, in J.

## 7. Evidence scripts

- `evidence/objective_assumption_checks.py`: ripple floor of ideal tapers, DI-target offset, Fraunhofer distances,
  grid density, resonance spacing. No solver; runs in seconds.
- `evidence/on_axis_tilt_from_runs.py`: tilt, raw vs detrended flatness and ripple of the latest best designs from `runs/`.
- `evidence/term_breakdown_from_runs.py`: weighted term shares of recent best designs.

Run with `.venv\Scripts\python.exe -I <script> .` from the repo root.
