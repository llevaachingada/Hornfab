# Typology plan v2: classical horns, Magnus's families, hybrids, and family selection

Date 2026-10-22. Status: **PLAN v2 (hardened after a senior adversarial review), ready to implement.**
Grounding: `docs/research/typologies/MESHER_TYPOLOGIES.md` (mesher internals, file:line) and
`docs/research/typologies/SEARCH_LAYER_GAPS.md` (our search layer). v1 is superseded; section 2 lists what changed.

## 0. Goal and non-goals

**Goal.** Find horn shapes that meet a stated acoustic brief better than known shapes, by searching established
typologies and principled hybrids of them. Every surface is built by Magnus's mesher and solved by the verified BEM
(`docs/evidence/SOLVER_VERIFY_2026-10-22.md`: GPU tests 18/18, analytic sphere 0.020 dB, GPU vs CPU BEM 0.039 dB).

**Non-goals (this round).** No new solver, mesher or meshing code; no change to the frozen contract
(`docs/plan/01_CONTRACTS.md`), gates or thresholds; no rollback beyond 90° outside R-OSSE / ICW; no enclosure,
baffle, room or woofer-port modelling; no surrogate retraining; no widening of existing configs' bounds.

## 1. Facts the plan rests on

| Fact | Source |
|---|---|
| Mesher formulas: `OSSE`, `R-OSSE`, `ICW`, `FREEFORM`, `LOOKUP`. No conical, exponential, hypex, tractrix, Le Cléac'h or spherical-wave family | research s1 |
| `FREEFORM`: H and V cubic-Hermite meridians, 2–64 anchors `[z, r]` or `[z, r, angleDeg]`, z strictly increasing, both meridians share the z span and the throat radius, wall angle in [−90°, 90°], overshoot guard adjusts tangent speeds; 2–32 cross-section stations (circle/ellipse, superellipse 2–16, rounded rectangle) blended by smootherstep; outer-shell curvature guard near the mouth | `freeform.py`, research s3 |
| `LOOKUP`: exact `[z, r]` table, linear interpolation, axisymmetric, no morph | `profile_formulas.py:1346-1392` |
| **The contract freezes `Family = Literal["OSSE","R-OSSE","ICW","FREEFORM"]`**; `design/custom.py` is the reserved home for "geometry beyond this" | `01_CONTRACTS.md:168, 368`; `types.py:11` |
| Throat source is a **spherical cap**: radius `source_radius_mm`, or ATH-style auto radius r₀/sin(θ_throat), else 3.75·r₀ | `builders/point_grid_sources.py` (`_source_cap_radius`) |
| `z_throat_real` (Re p/(ρc·u) at the throat) is computed for every solve; OSSE seed: 0.08 at 500 Hz → 1.0 at 3.5 kHz (physical) | `metrics/impedance.py`; run `ccef24` |
| The objective has a `load` term (Re z below `z_min`), weight 0 in every config so far | `objective/terms.py` |
| Mesh is a free-standing horn with an outer shell (wall offset), not an infinite baffle | mesher shell/offset code; research s3 |

## 2. Adversarial review of v1 (what was wrong, and the fix)

| # | Finding | Severity | Resolution in v2 |
|---|---|---|---|
| R1 | A new `TYPOLOGY` family breaks the frozen `Family` literal and would ripple into the dataset and surrogate | blocker | Typologies become **generators** that materialise an ordinary `FREEFORM` (or `LOOKUP`-for-verification) design. The record's family stays `FREEFORM`; the generator spec is stored as provenance (s5) |
| R2 | v1 compared typologies at arbitrary sizes. Horn behaviour scales with mouth size and length relative to wavelength, so cross-typology J was meaningless | high | A shared **design brief** fixes the driver exit and the size envelope; every generator is parametrised **at fixed size** (s3, s4) |
| R3 | v1 scored only directivity. Exponential, tractrix and Le Cléac'h exist for **throat loading** and mouth-reflection control; directivity-only scoring biases the comparison | high | Loading metrics from `z_throat_real` reported for every design; the brief can weight the existing `load` term (s6) |
| R4 | Axisymmetric typologies cannot meet an asymmetric target (75×45); a shared target silently penalises them | high | Briefs declare their symmetry; campaign refuses incompatible family/brief pairs or routes them to H/V hybrids (s7) |
| R5 | The throat junction was uncontrolled: the source cap's curvature and the driver exit angle must agree with each typology's throat wall angle, or the junction diffraction differs per typology | high | Throat wall angle and source cap tied to the brief's driver exit angle for every generator (s3) |
| R6 | "Hermite anchors reproduce the formula" was asserted, but the mesher's overshoot guard may change tangent speeds | medium | Fidelity measured on the **mesher's own sampled profile**, not on our reconstruction; acceptance ≤ 0.2 mm (s9 V2) |
| R7 | 40 evaluations per family is a seed lottery: CMA-ES with λ≈10 gets 4 generations, and families have 2 to 11 knobs | high | Tiered protocol with budgets scaled by dimension and ≥ 2 CMA seeds for any family comparison (s7) |
| R8 | Shared dataset mixes objectives from different briefs | medium | Records carry the brief hash; leaderboards and any surrogate filter by it; metrics stay target-free as before (s5) |
| R9 | Le Cléac'h has no reference implementation here | medium | Gate: implement from the published construction, cross-check against an independent reference (a 1-D horn tool such as Hornresp, whose horn-type list must be confirmed to include Le Cléac'h before relying on it, or published profile tables); ship disabled otherwise (s4) |
| R10 | Blend hybrid needs a common axial coordinate; v1 implied equal z | low | Blend on normalised t = z/L at the brief's length; both parents generated at that length (s4) |
| R11 | Failure caching keyed only by design hash would cache `mesh_too_large`, which depends on mode and dof cap | low | Failure-cache key = design hash + mesh spec (mode, epw, cap, quadrants) |
| R12 | Webster-equation intuition (f_c, area flare) is a 1-D plane-wave model; BEM results will differ near and below cutoff | info | Used only for parametrisation and sanity bands, never as acceptance thresholds (s9 V5) |

## 3. The design brief (makes every comparison fair)

`examples/briefs/<name>.yaml`, referenced by every typology config:

| Field | Meaning | Example `hifi_90x60_1in` |
|---|---|---|
| `driver.exit_radius_mm`, `driver.exit_angle_deg` | compression driver exit; throat wall angle at z = 0 is tied to it | 12.7, 0–10 |
| `envelope.max_mouth_w_mm`, `max_mouth_h_mm`, `max_depth_mm` | size class; generators place the mouth inside it | 400, 300, 220 |
| `target.coverage_h_deg/v_deg`, band, DI slope, `weights` (incl. `load`) | acoustic objective, existing schema | 90, 60, 700–5500 Hz |
| `symmetry` | `axisymmetric` or `hv` | `hv` |
| `source.cap` | `auto` (r₀/sin θ_throat, ATH convention) or a radius | auto |

Three briefs to start: an axisymmetric 90×90 (fair to classical horns), an H/V 90×60 (hi-fi waveguide), and the
existing OSSE 75×45 (continuity with CP-8c).

## 4. Generators (typologies realised through Magnus's mesher)

Pure maths in `hornlab_search/design/custom.py` (the contract's reserved module) plus a `generators/` subpackage;
no mesher import except for sampling Magnus's own OSSE / R-OSSE formulas. Every generator takes the brief (r₀, throat
angle, length L, mouth limits) and a few shape knobs, and returns H and V meridians as `[z, r, angleDeg]` anchors.

| Typology | Profile at fixed size (r₀, r_m, L) | Shape knobs searched | Defining-property unit test |
|---|---|---|---|
| Conical | r = r₀ + z·tan α, α = atan((r_m − r₀)/L) | r_m | constant wall angle |
| Exponential | r = r₀·e^{mz}, m = ln(r_m/r₀)/L; report f_c = m·c/2π | r_m | S(z)/S₀ = e^{2mz} |
| Hypex (Salmon) | r = r₀(cosh mz + T sinh mz), m solved so r(L) = r_m | r_m, T ∈ [0, 1] | T = 1 → exponential; T = 0 → catenoidal |
| Tractrix (Voigt) | mouth radius a = c/2πf_c; z(r) from a·ln((a+√(a²−r²))/r) − √(a²−r²); truncated at wall angle `max_wall_deg` (default 80°), so L follows from f_c | f_c | constant tangent length a |
| Le Cléac'h | spherical-wavefront construction, cap area follows the hypex law (f_c, T); truncated at `max_wall_deg` | f_c, T | cap area matches the law at every step (gated, R9) |
| Spherical-wave | Le Cléac'h with T = 1 | f_c | as Le Cléac'h |
| OSSE, R-OSSE meridians | sampled from the mesher's own formula functions (pinned SHA, guard test), for use in hybrids | their native knobs | equals the mesher's OSSE/R-OSSE mesh within 0.2 mm |

Throat rule (R5): every generator's wall angle at z = 0 equals the brief's `driver.exit_angle_deg` where the formula
allows it (conical: α is the result, so the brief's exit angle is reported, and a mismatch is a recorded junction
angle; exponential/hypex: the throat slope r₀·m is reported). The source cap is set by the brief (`auto`) for every
design in a campaign.

Truncation is explicit: FREEFORM cannot roll back past 90°. Tractrix and Le Cléac'h stop at `max_wall_deg`; real
rollback stays with R-OSSE and ICW-rollback.

Anchors: 12–24 per meridian (≤ 64), placed by equal arc length in (z, θ); exact angle at each anchor.

### Hybrids (all FREEFORM)

| Hybrid | Construction | Rule that keeps it physical |
|---|---|---|
| H/V | `profileH` from typology A, `profileV` from typology B, same r₀ and L | brief symmetry `hv`; both meridians monotone |
| Blend | r(t) = (1 − w)·r_A(t) + w·r_B(t) on t = z/L; angle from the blended derivative | convex blend of increasing profiles is increasing; w ∈ [0, 1] |
| Perturbed typology | r_{i+1} = r_i + Δ_i^{base}·e^{u_i}, u_i ∈ [−u_max, u_max] | increments positive by construction; no disjoint boxes |
| Cross-section | stations circle → superellipse / rounded rectangle, station t and exponent searched | mesher's own station blending |
| ICW seeded from OSSE/R-OSSE | mesher's native `icw_seed` | native |

Curated hybrid list for the first campaign (each with a one-line rationale in its config): OSSE-H × Le Cléac'h-V,
OSSE-H × exponential-V, blend OSSE ↔ Le Cléac'h, blend conical ↔ exponential, perturbed OSSE, perturbed tractrix.
Not all 49 pairs.

## 5. Representation and provenance (R1, R8)

- The search vector maps to generator knobs; the generator materialises a `Design(family="FREEFORM", params=...)`.
  The design hash is the geometry, so identical shapes from different generators deduplicate.
- Each evaluation row and dataset record gains a `generator` block: `{name, version, knobs, brief_hash}`. No
  contract field changes (`params` stays the mesher's keys; provenance is an additional row key / record metadata).
- Leaderboards and any future surrogate select by `brief_hash`.

## 6. Metrics added (report-only first, R3)

From the existing `z_throat_real`: `f_load_hz` (lowest frequency with Re z ≥ 0.7 and staying above it), `z_ripple`
(std of Re z above `f_load_hz`), `z_mean_band`. Added to `MetricSet.scalars` (open dict, no contract change), shown in
the report and the review page. A brief may set `weights.load > 0` with `z_min`, using the existing term.

## 7. Choosing what runs, and how to compare fairly

- `hornlab-search families` lists generators, Magnus families, hybrids, and the briefs each is compatible with.
- `hornlab-search campaign --brief <file> --families <names | classical | magnus | hybrids | all> --tier screen|compare
  [--dry-run] [--seeds N]`, sequential, GPU hygiene before and after every search (CLAUDE.md), writes `campaign.json`
  and a leaderboard (best J, terms, loading metrics, failures, s/candidate, pinned bounds, CMA seed spread).
  - Incompatible family/brief pairs are refused with the reason (R4).
- Tiers (R7):
  - `dry-run`: mesh every seed, no solve.
  - `screen`: budget = max(40, 10·N_knobs) per family, 1 CMA seed. Ranks only coarsely.
  - `compare`: budget = max(150, 25·N_knobs), **2 CMA seeds**, report the median and spread of best J. Only this tier
    supports a claim that one typology beats another.
- Failure cache keyed by design hash + mesh spec, so a replay does not burn budget re-failing (R11, ISSUES).

## 8. Search-quality fixes folded in

`freeform_hv.yaml` to the quarter domain; R-OSSE example config (ranges from the mesher's own checks); ICW-rollback
config; analytic mouth-size pre-screen against the dof cap.

## 9. Verification ladder (nothing is trusted before it passes)

| Step | What | Acceptance |
|---|---|---|
| V1 | Unit tests: each formula's defining property; fixed-size parametrisation hits r(L) = r_m; blend and increments monotone; generator → FREEFORM passes `families.validate` | all pass, offline |
| V2 | Fidelity on the **mesher's own sampled profile** vs the analytic curve, every generator | max radial error ≤ 0.2 mm |
| V3 | Mesher acceptance: `campaign --families all --dry-run` per brief | every seed meshes under its dof cap; topology checks pass |
| V4 | FREEFORM vs LOOKUP (dense exact table) for exponential and tractrix seeds, GPU, `compare` | metric differences reported; expected well under 0.1 dB |
| V5 | Textbook physics sanity, GPU: exponential beamwidth narrows with frequency; conical beamwidth follows its included angle 2α over a mid band before narrowing; Re z of exponential and tractrix rises through ~f_c and approaches 1 | qualitative; a violation is a bug to investigate |
| V6 | Le Cléac'h gate (R9) | matches the reference profile within 1 mm at the mouth, else disabled |
| V7 | `screen` campaign on each brief, then `compare` on the top 3 families + top 2 hybrids | leaderboard in the review page |

Expected result, stated in advance: on directivity briefs, OSSE/R-OSSE should lead and pure classical horns should
trail (they beam at high frequency). On the axisymmetric brief with `load` weighted, tractrix / Le Cléac'h /
hypex should become competitive. New shapes are most likely among the hybrids. Any result that contradicts these
expectations is checked against V4–V5 before it is believed.

## 10. Risk register

| Risk | Mitigation |
|---|---|
| Mesher private sampling API changes on a pin bump | pin SHA; guard test like `build_point_grid` |
| Outer-shell curvature guard rejects high mouth angles (tractrix/Le Cléac'h at 80°) | `max_wall_deg` configurable; V3 measures the rejection rate; lower it if needed |
| Dimension mismatch makes CMA comparisons unfair | tiered budgets scaled by knob count; 2 seeds in `compare` |
| Briefs too large for the 8 GB dof cap at 5.5 kHz | envelope chosen against TOOLCHAIN M3; dry-run reports dofs |
| Loading metric misread | report-only until a brief explicitly weights it |

## 11. Implementation lanes and order

| Lane | Owner | Deliverable | Done when |
|---|---|---|---|
| A. Generators + tests (s4, V1, V2) | Sonnet subagent 1 | `design/custom.py` + `design/generators/`, `tests/test_design_generators.py` | V1, V2 pass |
| B. Campaign / families CLI, briefs, tiers, failure cache, R-OSSE + ICW-rollback configs, `freeform_hv` quarter | Sonnet subagent 2 | `cli.py`, `search/cma.py`, `examples/briefs/`, configs, tests | offline suite green; `campaign --dry-run` works |
| C. Wiring: search vector → generator → FREEFORM design, provenance block, loading metrics, hybrid configs, V3–V7, review page | orchestrator | `design/space.py`, `search/evaluate.py`, `examples/typologies/`, evidence | V3–V7 done, evidence committed |

Order: A and B in parallel → C wiring → V3 → V4/V5/V6 (GPU) → V7 screen → compare. Every commit updates CONTINUITY
and ISSUES. Ownership: edits to task-04/05/08 paths are user-authorised and listed in NOTES_FOR_SENIOR.
