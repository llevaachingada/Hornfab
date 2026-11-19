# SENIOR REVIEW HANDOFF — horn + vented-woofer system (2026-11-19)

Audience: senior reviewing agent. Purpose: review the architecture and assumptions below, then
design the next round of implementation/improvements. You are NOT expected to re-derive this
session; everything cited here is on disk with hashes/paths. Read bounded, verify claims
independently, then decide.

Binding project rules while you work: worktree `C:/Users/hunte/Hrns/hornlab-woofer-system-wt`
(branch `feat/woofer-system-v0`, tip `fecb2d36fedd7a187644b09ad30ba462856a690a`, 11 commits this
session on top of `51179b9`); installed Boundary Lab (`C:\Users\hunte\Github\boundary-lab`, v0.5.0 @
`15f9a89245a9…`) / BEAT / Julia are READ-ONLY and invoked only through BL's own interpreter;
never write a solver/mesher; frozen contracts (`docs/plan/01_CONTRACTS.md`) untouched; the
orchestrator is the only committer; one GPU solve at a time (the GPU lane is currently held by an
unrelated night queue — CPU `beat_cpu` work is allowed and was used for every solve here).
Read `docs/research/system_woofer_2026-11-18/{BASELINE_CONTINUATION,FIRST_REFERENCE_CASE.json,
FIRST_BEM_EVIDENCE,SCREENING_EVIDENCE,BL_PARITY}.md*` before judging.

## 1. Verifiable state (run these)

```
git -C C:/Users/hunte/Hrns/hornlab-woofer-system-wt status --porcelain      # clean
git log --oneline 51179b9..HEAD                                            # 11 commits
.venv\Scripts\python.exe -m pytest tests\system -q --junitxml=<tmp>.xml   # 261 tests: 0 fail/0 err, 7 skipped
```

7 skips = the pre-existing real-BL env gates (`HORNLAB_BL_REAL_TESTS=1` enables them). Real-BL
variants were exercised manually this session (staging, validate, solve A/Bs), not in CI order.
Boundary Lab identity/pins: `FIRST_REFERENCE_CASE.json → engine_baseline` +
`BL_PARITY.md §1` (file SHA-256 pins). Solve engine provenance (recorded per run): BEAT Engine
0.7.0, Julia 1.12.7, `float32`, quadrature 2, static condensation on, symmetry off,
`transducer_reference_voltage_v: 2.83`, phasor `exp(+i omega t)`.

## 2. Architecture as built (review this)

Three fidelities, one provenance discipline:

```
(A) CPU screen (no solver)                        (B) installed BL reference                (C) DSP replay
horn_assets ─┐                                    stage.py / runner_stage.py  ── BL host ──  bl_results (per-excitation
compatibility (E_shape) ─┤  woofer_seed  ──→      (generate→stage_generation→          complex bases, schema pinned)
piston (rigid prior)     ├→ Pareto shortlist      component_parameters patch→compile→   ── dsp.filter_bank (LR/PEQ/
bass_reference (bassbox)─┘  + BL panel-fit gate   write_project_file→blab validate)        delay/polarity)
drivers (vendor YAMLs)                            BL CLI solve → run/ manifest+npz       ── combine.combine (refuses
                                                     (independent ports, exp(+iωt))          mixed per-input refs)
```

Provenance: `contracts.py` v1 (domain-separated ids, strict schema); `provenance.py` (immutable
case dirs, sha-self-checked manifests); deterministic screen replays are byte-identical (study
ids `65f6db3e8c8e8f86` pre-panel-fit → `27616eedee09009f` post-fit); `bl_results.py` pins BL
source SHA-256s; `reference.py` CLI = prepare/validate/solve/report; `run.solve_project` stays
inert, `reference.solve` requires an `authorized_by` token.

Fidelity labels are enforced, not aspirational: `SCREEN_MAGNITUDE | SCREEN_COMPLEX_APPROX |
INSTALLED_EXTERIOR_BEM | COUPLED_VENTED_FEM_BEM_LEM | MEASURED_VALIDATED`; phase uses refuse
`MAGNITUDE_ONLY / PHASE_ALIGNMENT_UNAVAILABLE`; cross-reference mixing refuses
`SENSITIVITY_REFERENCE_MISMATCH` (reader) and `combine()` refusal (same semantics, duplication —
see R13).

## 3. Evidence ledger (what has actually been solved; all CPU `beat_cpu`)

| # | Case (immutable dir under `system_runs/system/`) | Content | Result |
|---|---|---|---|
| 1 | `bl_smoke/20261118T225108Z-smoke-42536-01d15001` | assembled horn+vented, 3 freqs (250/700/1100) | complete 3/3; polarity/recomposition residuals 0.0; 0.1 ms delay rotation exactly −ωτ (−9.00/−25.20/−39.60°); woofer 700 Hz vertical asymmetry up30 −6.02 dB / down30 +1.49 dB |
| 2 | `bl_smoke_wide/20261118T231115Z-g4wide-56836-b5d6490a` | same assembly, 25 log freqs 200–2500 Hz | complete 25/25; H/V polars 37 pts each; 5 probes |
| 3 | `bl_g6_offset30/20261118T235110Z-assembly-21668-c17f7cf6` | same, horn +10 mm forward (assembly id `06ff56a5a1938ec9` vs `e16869cc3fa7dbfa`) | complete 25/25; paired deltas max rel 0.356–0.575 (max at 2.25–2.5 kHz), XO band 0.064–0.371; woofer channel changed although only the horn moved |
| 4 | `bl_motor12pr/20261119T010548Z-motor12pr-17944-fa37ab5e` | vented-only; REAL 12PR300 T/S via BL `component_parameters` patch; seed box 115 L / 371.2×371.2×1078.79 / 45 cm² | validate rc 0; complete 25/25 |
| 5 | `bl_motor12pr_demo_twin/20261119T013209Z-ref_case-11372-452574f9` | identical geometry, demo motor | validate rc 0; complete 25/25; A/B vs #4: pressure basis differs 120–144 % per 2.83 V (LF 120 %, XO 140–149 %), I_vc@200 Hz 0.366 A vs 0.477 A, velocity 102 % |
| 6 | `bl_motor12pr/20261119T010537Z-real_driver-48792-9d89b3df` | real motor + DEFAULT box (0.32×0.50×0.36); `case.demo_motor.blab.json` preserved | validate rc 0 — STAGED, NOT SOLVED |
| — | `bl_ref_case/20261118T223335Z-ref_case-61644-32976a2a` | vented-only R0, demo motor, default box | validate rc 0 — STAGED, NOT SOLVED |
| — | `bl_r4_tower_box/20261119T001041Z-ref_case-40216-b32bb5a2` | screen top cell attempt | REFUSED by BL: "Driver must fit inside the enclosure walls with 3 mm clearance." (recorded) |

Panel-fit learning (committed gate in `woofer_seed.py::bl_panel_fit_feasible`, mirrors BL
`parameters.py` lines 100–109): on a 371.2 mm front with 18 mm walls, BL's demo 200 mm
transducer + a 170 cm² port cannot coexist (max separation 0.1446 m < 0.1876 m required). The
re-ranked screen (study `27616eedee09009f`) now drops such cells with visible ledger tokens;
its top rows are 45 cm²-port 12-inch variants. NOTE the pre-check defaults to the DEMO
transducer dimensions (see R2).

## 4. What is authoritative vs placeholder

- AUTHORITATIVE: per-excitation complex bases, phasor/units, geometry/identity hashes, engine
  provenance, the superposition/polarity/delay algebra, BL's own validate verdicts, the motor
  mapping and its Fs/Vas/Mms cross-checks (0.41/0.05/0.67 %).
- PLACEHOLDER / LIMITED: (i) the transducer acoustic SHAPE in every installed case is BL's
  provider default (200 mm moving dia, 40 mm cone depth, 50 mm cap, 12 mm surround) — the
  committed geometry YAMLs lack those fields (`MOTOR_GEOMETRY_INCOMPLETE` recorded); (ii) the
  demo motor was used for all horn-assembly solves (#1–3) — the motor A/B (#4/#5) shows the demo
  motor is NOT harmless; (iii) no LF band (< 200 Hz) data exists yet; (iv) the horn channel is an
  ideal normal-velocity source per 1 m/s — not a compression driver; (v) DSP uses analog
  prototypes, not digital biquads.

## 5. Risk register — assumptions to interrogate (priority order)

R1 (CRITICAL) Mixed per-input references and the channel-calibration policy. Woofer bases are Pa
per 2.83 V; horn bases Pa per 1 m/s. `combine()` refuses to sum them; G5 recomposed with the
IDENTICAL arithmetic plus an explicit recorded per-channel dimensionless calibration. Decide the
standing policy: (a) explicit-calibration opt-in API carrying per-channel reference records,
(b) re-solve the woofer driven as normal velocity (loses the electrodynamic model), or (c) the
electrodynamic conversion of B_w to per-velocity. Without a policy, every cross-channel number is
manual. Evidence: `FIRST_BEM_EVIDENCE` G5 section; `combine.py::_require_compatible`.

R2 (CRITICAL) Every "BL-buildable" box today is DEMO-SHAPE-conditional. The panel-fit pre-check
defaults to the demo 200 mm diameter; the real 12PR300 Sd-derived moving diameter (0.2605 m)
needs 0.1821 m separation vs 0.1501 m available on the 371.2 mm front. Real-geometry staging
needs (i) maker CAD/measurement (cone depth, surround, cap), (ii) parameterising the screen's
panel-fit by the real driver geometry, (iii) a taller-front-panel re-screen. FaitalPRO publishes
drawings for 12PR300 — this is procurement/ingest work, not physics.

R3 (CRITICAL) LF band never solved. All grids start at 200 Hz; the box tuning (~30–53 Hz) is
invisible; the review's 20–250 Hz LEM-vs-BL comparison has no data. Cheap fix: a 20–200 Hz
request overlay (e.g. 12–16 log points) on existing cases #4/#5 (and one default-box cell), then
compare bassbox LF trends and check the port-interface velocity peak against the intended Fb.
Beware: BL's meshed port (NFR 0 here) vs bassbox-derived length is an approximation, not truth.

R4 (HIGH) Incomplete motor×box matrix. Solved: seed-box column (#4/#5). Staged-unsolved:
default-box column (#6 real, R0 demo). Two ~2.5 min CPU solves close the 2×2 and give the first
box-axis calibration pair. Also missing: the ASSEMBLED R2 case with the real motor (staging +
solve) — every horn+woofer result so far runs the demo motor.

R5 (HIGH) Observation geometry limits. 2 m probes at 200 Hz are not far field (λ≈1.7 m); H/V
polars are 37-point 1-D cuts at BL project defaults; no sphere → no DI/sound-power claims. Define
a declared far-field policy (distance, angular grid, seat window) and label simulated
"listening-window" curves accordingly (never CTA-certified).

R6 (HIGH) Convergence never checked. One mesh per case; no refinement delta; 25 frequencies
(≈1/4.5 octave) is coarse for interference nulls (G5's example dip ≈23.5 dB is
calibration-dependent anyway). Do one refinement solve (BL `mesh_size_m`/`detail_size_m`) and a
frequency densification near the crossover; predeclare tolerances; record deltas.

R7 (MEDIUM) Screen metric assumptions uncalibrated. E_shape (uniform weights, 1/3-octave
overlap window of STORED samples only, min 3 freqs × 3 dirs, −120 dB floor/−40 dB null flag,
9 dB² good-match label) is heuristic per the review; calibration exists only for the geometry
and motor axes. No box-axis or driver-family calibration, no false-negative audit (G7 partial).

R8 (MEDIUM) DSP model is analog-prototype only. LR4/PEQ/delay/polarity are complex analog
responses; digital realization (sample rate, biquads, latency, coefficient quantization) is
unstarted; "electrical LR4 ≠ acoustic LR4" caveat must survive every report. Excursion/thermal
limits live in bassbox gates but are not yet wired into `dsp.validate_dsp_point` as a joint
constraint.

R9 (MEDIUM) Solver precision/derivation limits. `float32` CPU solves; deep-null depths and fine
interference structure may be precision-limited; one `float64` control run on a settled case
would bound that. BL assumptions already exclude nonlinear/thermal/port-turbulence/structural
radiation — never claim them.

R10 (MEDIUM) BL/BEAT provenance drift. Installed 0.5.0 @ `15f9a89`; upstream tilt has a BEAT
0.8.0 pin and newer solver commits (BL_PARITY §2). Manifests pin hashes, so upgrades are
auditable; policy today is "record, don't upgrade mid-study". Re-validate on any upgrade.

R11 (MEDIUM) Real-path test coverage. Two real `reference.solve` bugs (relative argv paths;
pre-created output dir) were caught ONLY by a real run and are now regression-tested. The motor
patch path has one real staging test but no scheduled real-BL lane. Recommend a documented
one-command "real-BL lane" (staging + validate + a tiny solve) to run before pushes that touch
BL-facing code.

R12 (MEDIUM) Evidence tooling. The evidence skill demands scripted byte-checks; this session did
them manually plus the UTF-16/Tee decode dance. Add `tools/system/verify_evidence_quotes.py`
(decode logs, assert quoted blocks byte-identically) so evidence docs are machine-checked.

R13 (LOW/MEDIUM) Duplicate reference guards: `combine._require_compatible` and
`bl_results.assert_shared_sensitivity_reference` enforce overlapping semantics with different
messages. Unify (one guard, one token family) when R1's policy lands.

R14 (LOW) Authorization ergonomics. `authorized_by` is a free string checked non-empty; no shape
or registry. If batch runs are intended, define an authorization record (who/why/scope) written
into the case manifest; keep the refusal-by-default behaviour.

R15 (LOW) Catalog provenance audit. 10PR300/10PR320 YAMLs were vendor-fetched by the screen lane;
18Sound was dropped (TLS/prose-only); SB Acoustics not added. Re-verify the 10-inch YAML fields
against vendor pages (and record which fields are manufacturer vs derived) before any real-geometry
work relies on them.

R16 (LOW) Mesh-geometry safety. Separate closed bodies are accepted by BL's compiler; the horn's
17 mm standoff is inferred from bboxes, not an explicit clearance assertion in `assemble.py`.
Add a min-distance assertion (e.g. ≥1 mm) so a future offset edit cannot silently intersect.

R17 (LOW) Port/box physics bookkeeping. `mmd_kg` dry vs bassbox `Mms` is handled at the mapping
boundary, but the BL port profile (NFR 0 here) and bassbox's end-correction derivation are
different models; document the intended comparison band and never treat BL's meshed tuning as
validated until R3's check passes.

## 6. Proposed next-round work packages (design these into a plan; adjust as you see fit)

- WP1 LF-band calibration (R3): 20–200 Hz overlay on #4/#5 (+ one default-box cell after R4);
  port-velocity-peak vs intended Fb; bassbox-vs-BL trends with model-difference notes.
  Acceptance: complete low-freq manifest; explicit deltas; no claim beyond the band.
- WP2 2×2 motor×box matrix (R4): solve #6 + demo-default case; record paired deltas per probe;
  update the calibration ledger. Acceptance: 4/4 cells solved on identical geometry columns.
- WP3 Real-motor assembled reference: patch the R2 project's woofer component to the real T/S
  (same sanctioned `component_parameters` route), stage+validate+solve, A/B vs demo R2.
  Acceptance: rc-0 validate; complete 25/25; deltas recorded; identity new.
- WP4 Calibration policy + guard unification (R1, R13): typed per-channel reference records and
  a single explicit-cross-reference API; tests for polarity/delay/relative-gain semantics; then
  a DSP ranking pass with the declared policy. Acceptance: no manual recomposition; refusal
  tokens tested; report labels carry the calibration record.
- WP5 Convergence (R6): one mesh-refinement + frequency-densification control on the R2 assembly;
  predeclared tolerances; complex-pressure delta at the crossover documented.
- WP6 Funnel wiring + G7 (R7): screen shortlist → stage/validate/solve top-N → DSP replay →
  Pareto with fidelity labels and a calibration ledger; false-negative audit vs the installed
  references. Acceptance: one deterministic command produces the ledger; screens retained
  worthwhile classes on the observed cases.
- WP7 Real-shape geometry (R2, R15): ingest maker drawings (12PR300; optionally 10-inch),
  parameterise the screen's panel-fit by real dimensions, re-screen, stage one real-shape case
  (taller panel allowed) and solve. Acceptance: BL validate rc 0 with real geometry;
  pre-check reproduces BL's verdict on the refused cell for real dimensions.
- WP8 Tooling hardening (R11, R12, R14, R16): evidence byte-check tool; real-BL lane script;
  authorization record; clearance assertion. Acceptance: scripted checks committed + exercised.

## 7. Decision points for the owner (get answers before WP7-scale work)

1. Accept demo transducer SHAPE as a declared limitation for v0 studies, or procure maker CAD
   now? (Recommend: procure for 12PR300 — it gates all real box-axis work.)
2. Panel/box policy: allow taller fronts (e.g. 560 mm) and re-screen, or constrain to 371 mm and
   select drivers whose real geometry fits? (Both need real geometry.)
3. R1 calibration policy choice (explicit-calibration API vs velocity-driven re-solves).
4. Digital DSP target: keep analog prototypes for research and add a biquad realization later,
   or make digital realization part of this round?
5. Far-field/observation standard for declared curves (distance, angular grid, seat window).
6. Authorization policy for BL solves (per-case token registry vs free-form token).

## 8. Do not relitigate / non-goals
BEAT/BL compatibility (accepted), dependency pins (recorded, not a gate), solver or mesher
rewrites, new BEM codes, Fable surrogate/backbone, GUI purchase/port, nonlinear/thermal/port-
turbulence claims from the linear model, ranking DSP settings on magnitude-only data, CTA-2034
certification claims from simulation.

## 9. Artifact index (start here)
- `docs/research/system_woofer_2026-11-18/BASELINE_CONTINUATION.md` — W0 verified state.
- `…/FIRST_REFERENCE_CASE.json` — case freeze, solved-case registry, calibration status.
- `…/FIRST_BEM_EVIDENCE.md` — smoke + G4 + G5 + G6 + motor A/B, with byte-checked quotes.
- `…/SCREENING_EVIDENCE.md` — screen spec, study ids, panel-fit refusal, re-rank.
- `…/BL_PARITY.md` — BL install pins, upstream delta, generation reproducibility.
- Code: CPU screen + contracts + DSP in `hornlab_search/system/` (`reference.py`, `woofer_seed.py`,
  `compatibility.py`, `piston.py`, `horn_full_domain.py`, `contracts.py`, `combine.py`, `dsp.py`);
  BL-facing adapters in `hornlab_search/system/boundarylab/` (`stage.py`, `runner_stage.py`,
  `bl_results.py`, `import_results.py`, `motor_map.py`, `runner_motor_stage.py`, `run.py`,
  `probe.py`); tests under `tests/system/`.
- Raw runs: the case dirs in §3 (gitignored; immutable, sha-pinned manifests).

Hand this to the senior with `git -C <worktree> log --oneline -16` and the test command from §1;
ask for (i) an architecture verdict, (ii) a prioritized next-round plan consistent with §5/§6,
(iii) explicit calls on §7.
