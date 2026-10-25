# Next development round: priorities (after the beta)

Written 2026-10-22 22:35 EDT by the local orchestrator, at the user's request. **Read this before planning any work
after the beta session.** Items are in priority order. Background: `docs/HIGH_FREQUENCY_OPTIONS.md` (2026-10-13),
`docs/CLOUD_GPU_REPORT.md`, `TOOLCHAIN.md` M2/M3.

## P1 (top priority). Fused / direct CUDA Burton-Miller assembly in the exterior driver

**Why it matters.** The 8 GB RTX 4060 runs out of memory between 8.9k (works, 74 s per frequency under memory
pressure) and 15.7k (OOM) quarter-domain dofs (`TOOLCHAIN.md` M2). That ceiling, not the card, is what holds screening
at 5.5 kHz for large horns. The solver already has a memory-saving path that forms the Burton-Miller combination in
one matrix (about 6x less operator memory), but it is switched off for CUDA. Turning on an equivalent for CUDA should
lift the ceiling to about 20k quarter dofs [inferred], i.e. about 12.6 kHz at epw 6 even on the large OSSE seed, and
make 7k–9k-dof solves much faster (less memory pressure).

**Evidence (pinned `hornlab_beat_bem` 0.2.0, installed under `.venv\Lib\site-packages\hornlab_beat_bem`).**
- `julia/BeatEngineDriver.jl` ~line 1215: `fused_burton_miller = beat_backend in (:cpu, :metal) && near_selection
  === nothing && ...` — the fused path is CPU and Metal only.
- A CUDA single-matrix assembler exists: `julia/src/BeatEngineCudaBurtonMiller.jl:350`,
  `assemble_burton_miller_neumann_system_cuda` (re-exported in `julia/src/BeatEngineCore.jl:85, 1357`). Only
  `julia/tests/runtests.jl` (lines ~1214, ~1300) calls it; the exterior driver never does.
- The package states its CUDA path was never run by its authors (no NVIDIA hardware); our 4060 is its only
  real-world validation. `hornlab_beat_bem/config.py` also documents a CUDA-specific silent-error hazard (single
  image-near cache under multi-image symmetry), so CUDA changes need extra care.

**It is NOT a flag flip.** Adding `:cuda` to that condition routes into the fused pair-kernel path, which is not the
CUDA assembler. The work is to call the CUDA direct-system assembler from the exterior driver and make sure it:
1. handles our quarter-domain symmetry images (`yz+xz`) exactly as the current CUDA path does;
2. applies the same singular corrections (near-correction stays refused on CUDA, as today);
3. keeps the same excitation (unit acceleration on tag 2) and output conventions (exp(−iωt));
4. keeps the per-frequency call pattern our adapter uses (`solve/beat.py`, TOOLCHAIN M3).

**Ownership (updated 2026-10-24, owner decision).** We do this ourselves in our pinned fork of `hornlab-beat-bem`
(`C:\Users\hunte\Hrns\forks\hornlab-beat-bem`, branch `hornlab-search/fused-cuda`), following `docs/FORKS.md`;
`doctor`'s pin check already accepts fork URLs. Offering the change upstream to Magnus is still welcome, but we do not
wait for it. Exact patch plan: `docs/research/senior_pass_2026-10-24/04_IMPLEMENTATION_PLAN.md` WP15. Finding from
the 2026-10-24 read: the CUDA direct assembler already handles symmetry images (`symmetry_image_transforms`, image
singular cache, orbit row weights) and is tested against the 4-operator path on `sample_quarter.msh` in
`julia/tests/runtests.jl`, so the work is mostly driver wiring.
~~(a) ask Magnus … (b) with his OK, a pinned fork …~~ (superseded).

**Validation before any data from it counts (all on the GPU, from a clean state).**
1. `hornlab-search selftest --analytic`: spread ≤ 0.5 dB (today 0.020 dB).
2. `hornlab-search selftest --crosscheck` vs `bempp_cpu`: < 0.2 dB (frozen CP-7b rule; today 0.039 dB).
3. A/B against today's CUDA path on the same meshes (osse_axi seed, perturbed_osse_hv best, freeform_sculpt seed):
   `hornlab-search compare` within the 0.039 dB noise floor and ≤ 1° beamwidth.
4. Memory ceiling re-measured as in `TOOLCHAIN.md` M2 (VRAM baseline recorded, one solve per fresh process).
5. Records carry the new library SHA, so old and new solver data never mix silently (`lib_shas` filter).

**Decision recorded 2026-10-22.** The overnight queue of 2026-10-22/23 (epw-8 screen, compare tier, OSSE top-up,
sculpt searches) stays on the current verified CUDA path, so the compare tier and the surrogate data come from one
solver. Do not enable P1 mid-campaign.

## P2. High-frequency finalist pass at 12 kHz on the 4060 (no solver change)

Typology horns are small: measured 700–1,400 quarter dofs at 5.5 kHz, so about 3.3k–6.8k at 12 kHz (dofs scale with
f²), inside the 8.9k ceiling. Add 12 kHz briefs and a `verify` pass for the top designs only (about 1–5 min per
design). Prerequisite: the epw-convergence check above 2.5 kHz (`docs/HANDOFF_BETA.md` item C2; the overnight queue's
epw-8 screen feeds it). Physics caveat for every report: above the throat's first cross mode (about 7.9 kHz for a
1-inch exit) a real compression driver is not a uniform cap, so 8–12 kHz results compare geometries, not drivers.
A 12 kHz brief is a separate frequency grid: its records form their own group (already kept apart by the grid check).

## P3. Apple Silicon (Metal) backend for the collaborator's MacBook

`hornlab_beat_bem` supports `metal` (`config.py` `BEAT_BACKENDS`), with the fused path ON, and unified memory holds
dense systems far beyond 8 GB. Our layer only exposes `beat_cuda`, `beat_cpu`, `bempp_cpu`: add a `beat_metal`
backend option, macOS process hygiene (`search/hygiene.py` POSIX branch), then on the Mac: `doctor`, both selftests,
and the same 3-design A/B against the 4060 (< 0.2 dB) before mixing data. Metal has no near-correction (same as CUDA
under symmetry).

## P4 (IDEA, recorded 2026-10-24, owner decision required — not approved for work). Frequency-grid density and a narrow-resonance "safety net"

**Why it matters.** The screen grid is 12 log-spaced points from 500 Hz to the brief's band top (~5.5 kHz on this
card); verify is 25 log points (300 Hz–12 kHz). A narrow-band horn defect (a mouth-reflection resonance, an
organ-pipe/quarter-wave mode, a narrow cancellation or dispersion spike — e.g. a collapse at 550 Hz) that is
NARROWER than the grid gap (about 1/3 octave on screen) can fall entirely BETWEEN two solved frequencies. Nothing
is simulated between grid points: the plotted polar/beamwidth curves are interpolations that render smoothly
straight through the defect, and the objective cannot score what was never solved. A horn whose narrow defect
hides between grid points can therefore OUTRANK an equally good clean horn whose defect happens to land on a grid
point. This is the one accuracy hazard a designer most plausibly cares about.

**Existing partial mitigations (already in the repo; do not re-derive):** WP4 (landed 2026-10-24) added
`grid: {verify_points_per_octave: N}` (denser VERIFY grid above 5 kHz only) and objective-v2 `freq_weights`
(rewrites the importance of points the grid already solves — neither adds new solved frequencies on screen);
`f11` and `z_ripple` markers exist but are sampled at the same sparse points; `docs/research/
TIME_DOMAIN_RINGING.md` covers the time-domain alternative.

**Sub-idea P4a — dense finalist resonance net (recommended first; no contract change).** After screen/verify,
take the short-listed finalists ONLY and re-solve each on a dense uniform in-band grid (e.g. 24–48 in-band
points, or the WP4 8-points-per-octave pattern extended over the whole band) as a flagged resonance check. Diff
the dense-grid beamwidth/ripple/on-axis/DI against the sparse-grid values: a large diff means a narrow feature
the coarse grid missed. Cost is bounded (seconds-to-a-minute per design, a handful of designs). Could also auto-
flag horn FAMILIES whose dense J degrades vs their screen J, so the search brief for that family can be weighted
or the grid refined locally. Fits the existing `verify --brief`-style run-dir seam.

**Sub-idea P4b — perceptually weighted non-uniform frequencies (idea only; FROZEN-CONTRACT matter).** Instead of
even log spacing, add extra solved points in the regions most problematic to human hearing — roughly 2–3 kHz
(maximum hearing sensitivity / harshness region), the 4–5.5 kHz transition where beamwidth and harshness
concentrate, and possibly the 0.5–1 kHz mouth-reflection onset region — at the cost of points somewhere broad and
predictable. IMPORTANT constraint (01_CONTRACTS §8 is FROZEN; senior ruling 2026-10-13 declined per-user YAML
grid keys): a changed grid changes the solve hash and creates a RECORD GROUP that cannot train or cache with the
existing grids (`to_training_arrays` drops grid mismatches). The only clean path is a owner-approved contract
amendment that defines the non-uniform grid as a NEW NAMED grid group (the `*_12k` brief / WP4 `verify_hf`
pattern), with its exact point list fixed in the contract so every record in the group shares it.

Both sub-ideas are recorded so they are not lost; neither is scheduled. P4a is cheap and self-contained; P4b
should ride the next contract revision window if wanted at all.

## P5 (added 2026-10-24 late, owner-approved after the M2 pass): easy wins for BUILD-DECISION accuracy/value — NOT in the WP plan

**The lens (owner):** "less concerned about outright speed — the tool should actually guide which horn designs to
build in real life." Ranked by value per effort. None of these exist in `04_IMPLEMENTATION_PLAN.md`; none
replace it. GPU cost is small everywhere; W1 is free.

- [ ] **W1 — screen-vs-verify rank-consistency audit (offline, ZERO GPU; do first).** The search loop trusts the
  12-point screen tier to pick finalists; verify (25 points, more dofs) re-scores survivors. Every stored campaign
  already holds BOTH scores (dataset + runs/) — compute per campaign/family the rank agreement (winner agreement +
  the dB/dof gap at every rank flip). Deliverable: `tools/rank_audit/` (the rescore_v2 pattern) + a small evidence
  doc. Answers: how much to trust a screen ranking before spending verify GPU, and where search budget is
  misallocated.
- [ ] **W2 — the dense finalist resonance net = P4a above (tiny GPU).** Before committing to BUILD: re-solve the
  top 3–5 finalists only, on a dense uniform in-band grid (~24–48 points), and diff beamwidth/ripple/on-axis/DI
  vs the sparse-grid values — a large diff means a narrow feature the grid missed (the plotting interpolates
  straight through it). Minutes per design on the fused path. Scheduling note: fold into the brief-design pass as
  the build-gate on its POC winner (its handoff already plans one fused 12 kHz verify; this rides the same job
  family with the owner's go).
- [ ] **W3 — denser screen grid as a NEW NAMED grid group (small code; OWNER-GATED contract matter).** +4 screen
  points (12→16) ≈ +33 % screen time (small at today's sizes) with better beamwidth/ripple fidelity on exactly
  the decision-bearing frequencies. Frozen-contract rule (P4b's reasoning applies to screen too): a changed grid
  must land as a NEW NAMED grid group (the `*_12k`-brief / WP4 `verify_hf` pattern) with its exact point list
  fixed in the contract; needs the owner's OK in a contract-revision window.
- [ ] **W4 — `compare --bar` judge mode (mechanical, ~20 lines).** `hornlab-search compare` prints diff tables but
  never judges; every fork validation ladder eyeballs them. A `--bar` flag that exits nonzero when the CP-7f bars
  (0.039 dB / 1 deg) are crossed removes a recurring human-error surface (hit three times in the M2 pass); offline
  tests only.
- [ ] **W5 — perceptual/frequency emphasis via the LANDED v2 `freq_weights` (configuration only, zero code).** When
  real owner briefs exist (the brief-design pass), set weight where perception lives (roughly 2–5 kHz: beamwidth
  and harshness) and down-weight broad, predictable regions — the machinery is already built for exactly this
  (WP4). Also record the M3/WP5 calibration outcomes (distance_m, screen balloon, source_motion) as adopted
  baseline defaults with owner sign-off (`docs/HANDOFF_BRIEF_DESIGN_2026-10-24.md` plans this).

Suggested homes: W1 + W2 + W5 → the brief-design pass (its deliverables are exactly the baseline-settings doc and
the POC build-gate); W4 → any small offline commit (e.g. alongside the in-flight M3/M4 lanes); W3 → the next
contract-revision window or skip.

- [ ] **W6 — a Boundary Lab-class balloon view in the GUI (designer lane, no GPU).** Owner showed BL's Balloon
  Plot (2026-10-24): a smooth continuously-shaded 3D sphere colored by normalized SPL (0 → −30 dB) with white
  isobar rings ON the surface, labeled On-Axis/Horizontal/Vertical axes + a measurement-domain wireframe; a
  "radar slicer" (angle slider → polar cut at any azimuth/frequency); and a smooth log-frequency × angle
  (±180°) filled-contour slice. **Recon of BL's actual source (GitHub, done 2026-10-24):** the balloon is NOT a
  textured sphere — it is a **dB-to-radius BLOB** (radius = max(spl − floor, 0); shape AND color both encode
  level), PyVista/VTK `smooth_shading` + turbo, isobars = tubed white contour rings offset ~0.2 % of extent,
  radar slicer = barycentric interpolation along a great-circle meridian, isobar slice = fractional-octave
  smoothed + resampled freq×angle heatmap. Port of the DESIGN into our web GUI (three.js r160, vanilla JS) is
  the implementation (designer lane dispatched); GPL attribution carried. We solve and STORE the full balloon
  per design already (`response.npz`: `spl_balloon_db` + `balloon_grid`/`balloon_layout` + the sin-θ weighting
  note) — a viewer is a rendering feature, not new computation. Prerequisite chain: data density first —
  M3/WP5's running 512→1024→2592 ΔDI check decides the verify-balloon upgrade; note the sin(θ) unequal-area
  layout when shading (interpolate on the sphere, not the index grid).

## P6 (added 2026-10-25, PROPOSALS from the collaborator conversation — owner decision required; **FULL IMPLEMENTATION PLAN v1.0 written 2026-10-25: `docs/research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md`** — research basis §2, settled decisions §3 (D1–D20), work packages §4, waves + verbatim dispatch prompts §5, checkpoints §6; execution gates: WP1–WP17 complete + owner GO; research basis summarized in `docs/plan/12_RESEARCH_BASIS.md` §11)

- [ ] **P6a — featured superformula (guiding-curve) search campaign (config-only; realizes the plan README's frozen quick-fork #2).** The OSSE guiding-curve superformula keys (`gcurve_type: 2`, `gcurve_sf_a/b/m1/m2/n1..n3`, `gcurve_se_n`) are mesher-native AND already searchable design-space rows (`design/families.py` gcurve section; `tests/test_design_families.py` "table rows"); superellipse exponents are searched today (`rosse_baseline` 2–8, `freeform_sculpt`). Missing: a catalog family + `examples/` config that SEARCHES the SF knobs, bounds anchored to a verified Ath reference case (a User Guide `GCurve.SF` example or the ATH CORE `sf()` wall-angle script), then one screen-tier campaign. Grounding (typology-research minimum bar): Gielis 2003 + the Ath User Guide — R9 satisfied; `12_RESEARCH_BASIS.md` §11 is the dossier. Cost: config + one screen campaign. Value: star/organic/azimuthally-varying mouth shapes no current config expresses.
- [ ] **P6b — GSA vs CMA-ES bake-off (owner-gated experiment; NOT scheduled, NOT in any WP).** No published head-to-head exists (`12_RESEARCH_BASIS.md` §11.5); CMA-ES stays the default regardless of outcome; WP11 restarts + CMA-ME atlas remain the scheduled search upgrades. If run: fixed EVALUATION budget (200–400 sims, NOT iterations), identical bounds/graded penalties/initial seed, 5–10 repeats, Latin-hypercube/random baseline, report best-so-far + median per budget; cheapest on the 2-knob exponential family, or after the metric surrogate makes evaluations ~ms (§11.5 protocol).

## Not recommended (recorded so nobody re-proposes it without new evidence)
- Half precision or other "quantization" of the BEM system: the solver is Float32 with a Float64 Krylov space; dense
  high-frequency BEM systems are poorly conditioned.
- Lowering epw below 6 without a measured convergence check.
- GPU memory oversubscription to system RAM: Linux-only, and a dense factorisation over PCIe crawls.
- Fewer high-frequency sample points: saves time, not peak memory.

## Fallback
Cloud RTX 4090 (24 GB, about $0.34–0.69/h) or L40S (48 GB, about $0.79/h): `docs/CLOUD_GPU_REPORT.md` CP-9a pod proof
first (Linux CUDA never run with this solver).
