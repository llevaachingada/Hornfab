# HANDOFF — Brief design & baseline-settings pass (owner goals → real briefs)

Written 2026-10-24 (late evening) by the M2 orchestrator. **Owner's own words, verbatim intent:** "the current
briefs we've done this far are kind of generic and not really honestly good or what I'm trying to build in the
first place." This pass exists to fix exactly that: study the physics + our machinery + real compression
drivers, INTERVIEW the owner about their actual project, and design briefs/baseline settings that encode it —
with at most ONE small GPU proof-of-concept search, owner-approved, at the very end.

## 0. Sequencing (updated 2026-10-24 late: M3 is IN FLIGHT — another session is executing it)

The M3 handoff was issued in chat (owner holds it) and the carry-over fixes are ALREADY LANDED
(`1dda493`: dataset-record `objective_version` + the brief_hash-scoped `invalid_envelope` marker, 6 offline
tests). You share the machine with that session: **start the STUDY phase (section 1) immediately; do NOT
begin the interview, write briefs, or push ANY commit until M3's GPU chain has ended** — check
`git log --oneline` for its carry-over/WP5/WP7/WP8 commits + `docs/evidence/MEASUREMENT_PACK_<date>.md`
existence + an idle GPU (no julia, no lock). Only then interview the owner, so the baseline settings can
adopt M3's WP5 calibration proposals. Run the two passes' pushes strictly one at a time.

## 1. REQUIRED READING (the study list — read completely before the interview)

**Frozen plan / physics basis**
- `docs/plan/12_RESEARCH_BASIS.md` — the research basis the frozen plan claims.
- `docs/plan/01_CONTRACTS.md` — **completely**: the frozen metric/objective definitions, `MetricSet`,
  `Response`, the brief/config schema. You may not change its meaning; every brief key you must use is here.
- `AGENTS.md` + `CLAUDE.md` — the 8 hard rules, GPU hygiene rules 1–7, the owner fork amendment (fork
  changes only via `docs/FORKS.md`; never hand-edit `.venv`).

**Current project state**
- `docs/CONTINUITY.md` (top entry + Status) and `docs/ISSUES.md` (2026-10-24 blocks).
- `docs/evidence/FUSED_CUDA_2026-10-24.md` — THE machine card: fused CUDA fits ≤15,984 quarter dofs
  (peak−baseline 7,637 MiB; assembly memory-pressured 437 s/freq there), dies at 20,237 (provisional), SAFE
  caps 12,000/12,000 (verify/final). dofs ∝ f²: a 1″ OSSE design at 12 kHz is ~4.4k–6k dofs → fast zone;
  screens at 14 kHz would blow the 5,000 screen cap and double per-candidate cost. **f11 = 7,914 Hz for the
  1″ exit (printed in every record): above it the source is an ideal rigid cap, so 8–12 kHz+ compares
  GEOMETRIES, not drivers.**
- `docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md` + `docs/evidence/OBJECTIVE_V2_RESCORE.md` — how the families
  actually ranked (osse_axi and perturbed_osse_hv lead their tiers with J medians ~5.8–7.2 under v2) and what
  v2 changed (Spearman ρ 0.989; v2 = detrended ripple/flatness + Gaussian-beam DI target).

**Typologies + mesher reality** (what geometry is expressible at all)
- `docs/TYPOLOGY_PLAN.md` (briefs, tiers, budget rules, the verified-verification ladder V1–V7).
- `docs/research/typologies/MESHER_TYPOLOGIES.md` (Magnus's mesher formulas: OSSE/R-OSSE/ICW/FREEFORM/LOOKUP;
  morph, guiding curve, throat stretch; NO classical profiles natively — they are generated FREEFORM anchors)
  + `SEARCH_LAYER_GAPS.md` (what the search layer does/doesn't reach).
- Boundary/size constraints: `mesh/build.py` asserts bbox metres 0.02–5 m (NOT the plan's 0.1–1 m wording),
  symmetry planes from quadrant count, mesher curvature guard (FREEFORM shells → 3 mm; thin-OS throats may
  trip it), `export-step` exists for CAD.

**White papers / horn-design theory** (the raw surveys + corrections)
- `docs/research/senior_pass_2026-10-24/01_AUDIT_BUGS_AND_ASSUMPTIONS.md` (what our v1 score got wrong),
  `02_TYPOLOGIES_AND_MULTICELL.md` (+ multicell/point-grid door), `03_HIGH_FREQUENCY_12KHZ.md` (footprint
  math + 12 kHz routes), `04_IMPLEMENTATION_PLAN.md` WP list (esp. WP9b — the JMLC/Kugelwellen/Iwata/x-shape
  constructions with Fourcade's tables).
- `appendix_A_typology_survey_raw.md` + `appendix_B_methods_survey_raw.md` — the white-paper summaries WITH
  corrections (trust the corrections, not the raw text): Kolbrek horn theory (part 1–2), Le Cléac'h ETF 2010
  slides, Fourcade's 2015 JMLC calculation (exact construction + reference case), Kugelwellen spherical-wave
  horns, mouth-reflection/ripple theory, directivity/target-curve literature.
- External primaries to fetch if needed (URLs inside `02`/appendices): Fourcade PDF (unepassionaudiophile),
  Kolbrek audioXpress 2008, ETF slides (rintelen.ch). Use them for the interview's physics answers, with the
  appendices' caveats.

**Boundary Lab (the professional BEM app we borrowed renderer/engineering conventions from)**
- Committed knowledge NOW ON MAIN: `docs/research/boundary_lab_0.5/bl_inventory.md` + `beat_compat.md`,
  `docs/BOUNDARY_LAB_INTEGRATION_PLAN.md`, `docs/BL_LEARNINGS_IMPLEMENTATION.md` +
  `docs/evidence/BL_LEARNINGS_GPU.md`. What BL teaches: isobar-style polar rendering, sidechain, qualification
  screens, per-frequency per-plane conventions, QSS of a real BEM workflow.
- NOTE: the BL source checkout previously used (`JWSound/boundary-lab`) is NO LONGER on disk at that path —
  if you need BL source lines, ASK THE OWNER where it lives or clone it (owner action).

**Magnus's packages (read-only sources on disk)**
- `C:\Users\hunte\Hrns\forks\hornlab-waveguide-mesher` (checkout = installed pin b922e807): start at
  `docs/public-api.md` + `examples/` + `geometry.py::MeshDensity`/`PointGridHornGeometry` — learn every
  geometry key that EXISTS (never invent one; hard rule 3), the wall-clearance/curvature guards, symmetry
  modes, source cap (`auto` = r0/sin θ), freestanding vs baffle closures.
- `C:\Users\hunte\Hrns\forks\hornlab-beat-bem` (our WP15 fork of BEAT): `hornlab_beat_bem/config.py` +
  `docs/*.md` — what the solver models: rigid walls, ONE velocity source tag (spherical cap, unit-
  acceleration), Burton-Miller exterior; no impedance BCs; surface_traces available; our
  `HORNLAB_BEAT_FUSED_BM_CUDA` fused path (M2).

**Our software** — `docs/CODE_MAP.md` + `docs/INDEX.md` (every module/doc), then the CLI itself:
`.venv\Scripts\hornlab-search.exe --help` and the subcommands' help (run/search/campaign/verify/compare/
report/families/doctor/gpu-clean/export-step). The brief YAML schema lives in `config.py::load_brief`
(accepted keys; unknown keys are refused BY DESIGN).

## 2. The machinery in one page (plain language — say it to the owner like this)

| Brief line | Meaning | Typical values / notes |
|---|---|---|
| `driver.exit_radius_mm` | The round hole the compression driver bolts to; fixes the throat. OSSE/R-OSSE/ICW designs are PINNED to it (WP2 fairness; conflicting pinned value = refuse). | 1″ = 12.7; 1.4″ = 17.78 |
| `driver.exit_angle_deg` (+ `throat_angle_policy: pin`) | The driver's own flare angle; `pin` = horn throat must match (no near-throat mismatch ripples). | 5–10° for 1″ drivers |
| `envelope` | Max box W×H×D (mm) the finished horn may occupy (outer incl. shell). | 400×300×250 … 520×420×260 |
| `target.coverage_h/v_deg` | Beam edges (horizontal/vertical), held across the band. | 90×90 (room), 90×60 (studio) |
| `target.band_lo_hz / band_hi_hz` | Simulated/scored span. Band_lo is where the horn takes over from the woofer. | 700–12,000 (12k = the fused sweet spot; screens just fit the cap) |
| `weights` | What the score rewards: `cov` = hold the coverage angles; `rip` = no ragged beam/response dips; `di` = match a smooth DI ideal; `dislope` = how GENTLY the beam narrows with rising frequency; `flat` = on-axis loudness flat across band; `load` = how hard the throat loads the driver (0 = measured but ignored today; report-only scalar `z_ripple`, throat resistance). | 1.0 normal, 0 ignore |
| `objective: {version: 2}` | The fairer scoring (v1 rewarded beam taper + source tilt — audit). v2 opt-in; brief DEFAULT flip = owner decision. | v2 for NEW briefs |
| `grid: {verify_points_per_octave: N}` | Denser HF verification above 5 kHz (WP4). | 8 |
| `verify_only` | Scoring-only sheet; searches refuse it. | off for design briefs |
| mesh policy | `epw` (elements per wavelength; axi typologies 8, H/V 6), `dof_cap_screen/verify/final` = 5000/12,000/12,000 on the `*_fusedcuda` copies; `solve: {cuda_fused: true}` (fused path, 1 GHz… no: 1 kHz ceilings measured at; the flag rides meta). | NEW copies only; never edit old caps |
| `campaign` tiers | `dry-run`/`screen` (coarse, budget max(40, 10·knobs), 1 CMA seed) / `compare` (max(150, 25·knobs), 2 seeds) + `families` selection with compatibility reasons. | screen first ALWAYS |
| mounting | Enclosure mounting = WP12 (LATER; not in briefs yet). | — |

Three silent killers + one physics caveat to restate to the owner: mesh_scale (metres!), quadrants ↔
symmetry pairing, DI provenance (`balloon` vs `cuts_estimate`); and the f11 driver-realism ceiling above.

## 2b. Where the machinery will be as the remaining plan lands — design briefs FORWARD-COMPATIBLE

The repo you are briefing is NOT the repo the owner will optimize in. Per the implementation plan
(`04_IMPLEMENTATION_PLAN.md`), the parameter and typology space grows through M3–M5:

| Pass | WPs | The machine gains | What briefs must anticipate NOW |
|---|---|---|---|
| M3 (IN FLIGHT: carry-overs landed @ `1dda493`) | carry-overs, WP5, WP7, WP8 | WP5 far-field/balloon/source-motion calibration PROPOSALS (distance_m 2→10?; screen balloon 512→1024?; `solve.source_motion` new optional key); WP7 `mesh.rear_res_factor` (opt-in, default = today); WP8 `mesh.band_split: {edges_hz}` (opt-in, per-band meshes + seam checks, wall-time report) | the baseline-settings doc ADOPTS M3's proposals only with owner sign-off; band-split edge choices depend on the owner's band; none of these keys enter the brief YAML (they are config/solve keys) |
| M4 | WP9 (NEW generators: `splice`, `throat_blend_mm`, `spherical_salmon`, `angle_space`, presets `os_conical`/`qt_rect`/`catenoidal`), WP9b (T1 `lecleach_exact`, T2 `kugelwellen`, T3 `jmlc_elliptical`, T4 `jmlc_iwata`, T5 `x_shape`, T6 `min_phase`, T7 `toroidal_rollback`), WP10 (GRID: point-grid family — G8 even-Fourier cross-sections, G9 φ-varying termination), WP12 (enclosure mounting) | curled-lip JMLC horns; organic/saddle mouths; X-shapes; arbitrary Fourier cross-sections; horns mounted in boxes | **Briefs are family-agnostic**: the family allow-list lives in the LAUNCH/campaign command, not the brief — new typologies do NOT invalidate briefs; only the allow-list choice changes. Curled-lip/organic/multicell horns need a WIDE+SHALLOW envelope (the plan's `organic_rollback_1in` sketch: ~520×420×260) + freestanding closure — if the interview reveals curl appetite, design a variant brief NOW (`organic_rollback`-style). Enclosure mounting later adds a `brief.mounting` key (note appetite; do not hand-write the key — it does not exist yet and unknown keys are refused) |
| M5 | WP11 (BIPOP restarts + QD archive), WP16 (non-uniform source velocity — phase-plug above f11), WP17 (near-singular CUDA correction), WP14 (multicell prototype, CPU-first validation) | stronger search restarts; REAL driver exit behavior above f11 (lifting part of the 8–12 kHz geometry-only caveat for non-uniform-velocity exits); multicells/vanes on GPU (only after CPU near-correction validation) | band_hi beyond 12 kHz only becomes PHYSICALLY meaningful to score after WP16 — until then keep the owner's band at 12 kHz in briefs regardless of appetite; multicell briefs wait for WP14's CPU validation verdict |

**Forward-compatibility rules (hard for this pass):**
1. Briefs use ONLY keys that exist in `config.load_brief` TODAY (rule 3 — never invent). Capabilities that
   land later (mounting, >12 kHz realism, multicell) enter the SESSION FILE as owner appetite notes, and the
   pass that lands them updates the briefs (briefs are cheap files; designs are not).
2. The owner briefs state their family allow-list ASSUMPTION explicitly (which families the first campaign
   will mix) so M4's new typologies plug in without surprise.
3. If the interview exposes appetite for shapes the plan delivers later (JMLC curls, multicell, boxes),
   design the VARIANT briefs ahead (envelope shape, band realism, source cap) so each future pass finds its
   brief ready; mark them "awaiting WPxx" in the baseline doc.
4. Re-ground EVERY numeric claim in this file against the evidence of the moment (the ceilings/f11 numbers
   cite M2; M3's evidence supersedes where it measured more).

## 3. Why the current briefs are "generic" (state of the world you inherit)

`examples/briefs/` holds three demo sheets chosen to make the MACHINERY runnable during the beta: the axi
90×90 sheet, the hifi 90×60 sheet (+ the `*_12k` verify-only copies). No owner interview was ever run; the
weights and envelopes were defaults, not a design goal. The campaign results over them (compare tier,
2026-10-23) ranked typology families — that was tool validation, not design intent. Your job: replace the
intent, not re-litigate the numbers.

## 4. STEP 1 — THE OWNER INTERVIEW (the core of this pass; conversation, not a form)

Interview hygiene: plain language; render examples to anchor abstract questions (GUI: `#/typologies` + 3D +
Evolution; `report` HTML with polar maps); every number that enters a brief must be OWNER-GIVEN or
OWNER-CONFIRMED (do not silently default); capture answers verbatim into `docs/BRIEF_SESSION_<date>.md`.

Questions (probe the WHY behind each; skip if already answered):
1. **Purpose**: what is this horn FOR — home two-way with sub? studio mid-high? something bigger? Room size,
   listening distance, one per side, stereo pairing?
2. **Driver**: which compression driver(s) do you OWN or plan (make + model)? If undecided, have us shortlist
   2–3 real 1″ drivers as design targets (e.g. B&C DE12-8 / Faital HF200 / RCF ND1050 — pick by band,
   power, price with the owner). Pull the REAL spec sheet of each candidate.
3. **Coverage**: where should music point — sweet-spot width? symmetric or deliberately asymmetric (H≠V)?
   How much does wall/ceiling interaction matter to them?
4. **Band**: planned crossover frequency (band_lo) + how high the horn still controls the beam.
   Cross-check: is band_lo feasible given the box (mouth-area law vs coverage at f_lo)?
5. **Size envelope**: real physical limits — shelf, soffit, open floor? A firm W×H×D box they will not cross?
6. **Priorities**: force a rough RANKING of what "better" means to them (coverage vs smoothness vs
   constant-DI vs on-axis flatness vs driver loading). No ties allowed; map the ranking to weights.
7. **Shape appetite**: classical/OSSE/curled-lip JMLC/multicell/X — which families may the search mix?
   (family allow-list; WP9b organic types are future capability, note appetite now.)
8. **Loading/efficiency**: does loudness-per-watt matter (load weight > 0) or is response shape king?
9. **Success criterion**: what makes THIS brief a success — a measurement, a listen, a printed part? (Sets
   how many candidates to trust and what evidence to collect.)
10. **Compute appetite**: minutes per candidate acceptable now; overnight runs OK?

## 5. STEP 2 — REAL-WORLD DRIVER GROUNDING (web research; offline, no GPU)

- For each named/planned driver: fetch the actual spec sheet (diaphragm/exit diameter, included exit angle,
  recommended band + crossover, power). Map to brief keys: exit_radius_mm, exit_angle_deg, realistic
  band_lo/hi, loading expectations. Compute each driver's own f11-style cap (throat first-mode ≈ c/2a
  scaled by the actual aperture; anchor: 1″ ⇒ 7,914 Hz) — the horn can only honestly score where the source
  model holds; above it, note the geometry-only caveat.
- Collect 2–3 published reference builds for that driver/coverage (JMLC spreadsheets, OS waveguide papers,
  commercial 1″ waveguides) as QUALITATIVE sanity targets (bandwidth of control, on-axis behavior) — never
  as optimization targets copied into constraints.
- Deliverable: `docs/DRIVERS_<date>.md` — table: driver → exit r/angle → published band → f11 → physically
  reasonable coverage for its size → suggested crossover.

## 6. STEP 3 — THE DELIVERABLE: briefs + baseline settings

- **2–4 briefs** under `examples/briefs/<owner-brief-name>.yaml`: a PRIMARY (the interview's consensus) +
  variants ONLY if the owner named trade-offs (e.g., conservative-size vs ambitious-size; symmetric vs H≠V).
  Each file carries a RATIONALE BLOCK: every key traced to an interview answer, a driver-sheet fact, or a
  physical rule (band_lo vs mouth-size feasibility — flag any conflict instead of hiding it).
- **Baseline settings doc** (`docs/BASELINE_SETTINGS_<date>.md`): recommended family allow-list (with the
  campaign-compatibility reasons), tier budgets (screen first, then compare; `budget_for_tier`), CMA seeds,
  grid/weights choices + why, `*_fusedcuda` config-copy pattern (solve.cuda_fused: true; caps 5000/12,000/
  12,000; screen 5000 stays), and the M3 measurement-pack recommendations adopted as DEFAULTS ONLY with
  owner sign-off (distance_m, screen balloon).
- **Future-capability appendix** (part of the baseline doc, per section 2b): for each owner appetite exposed
  in the interview — planned typologies (WP9 generators; WP9b JMLC/Kugelwellen/organic/X; WP10 GRID Fourier
  sections; WP12 mounting; WP14 multicell; WP16 >f11 realism) — record (a) whether it plugs into the designed
  briefs UNCHANGED (briefs are family-agnostic; allow-lists live at launch), or (b) which variant brief /
  brief-update the future pass must bring (e.g. the wide-shallow `organic_rollback`-style envelope for curls,
  a `mounting:` key from WP12, band_hi realism from WP16). Each future-dependent item marked "awaiting WPxx".
- **Offline validation ladder** (no GPU): (1) `load_brief` clean; (2) campaign compatibility per family;
  (3) `run --dry-run` per brief (estimate printed); (4) 1–2 sample mesh builds CPU-only (bbox/symmetry checks);
  (5) the exact OWNER APPROVAL SHEET: the POC command card (family list, `--budget 20`, seed, expected
  wall-clock from measured s/candidate) for signature.
- **STEP 4 — GPU (the pass's only GPU): the POC run, ONLY after the owner approves the brief text**: one
  `search --budget 20` (seed 1234) on the primary brief + ONE fused 12 kHz verify of the top design. Paste
  everything (J per eval, s/candidate, dofs, peak VRAM, f11 caveat) into `docs/evidence/OWNER_POC_<date>.md`.

## 7. Rules, gates, push

- Hard rules 1–8 (never invent keys/unit/parameter names — brief schema is `config.load_brief`'s, frozen;
  blocked twice on the same error → `NOTES_FOR_SENIOR.md` + stop).
- GPU: only the owner-approved POC (2 jobs). The GPU lock (`runs/.gpu.lock`), `gpu-clean` before AND after,
  fresh process per measurement, baseline next to every peak, one job at a time — as every pass.
- NEVER: edit existing briefs/caps; run searches without the owner's signed approval sheet; loosen any
  tolerance; start M4+ (GRID/multicell/enclosure) — note the owner's appetite for them in the session file instead.
- Push: `docs/CONTINUITY.md` (dated entry on top + Status) + `docs/ISSUES.md` in the SAME commit;
  `CODE_MAP`/`INDEX` lines for every new doc/module; conventional commit, scope(s); offline suite green first
  (pin-tree baseline 938 passed / 20 deselected; while the fork pin stays owner-hosting-gated, the
  unpinned-main tree shows the expected single `test_mesh_pin` tripwire — document it exactly like M2 did).