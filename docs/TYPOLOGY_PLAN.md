# Typology plan: classical horns, Magnus's families, hybrids, and family selection

Date 2026-10-22. Status: **PLAN, approved for implementation on the next turn.** Author: local senior (applied
maths / horn design). Grounding: `docs/research/typologies/MESHER_TYPOLOGIES.md` (what the mesher implements, file:line)
and `docs/research/typologies/SEARCH_LAYER_GAPS.md` (what our search layer exposes).

## 0. What we are trying to do

Find horn shapes that meet a directivity target (coverage, smooth DI, low ripple) better than the shapes we already
know, by searching **established typologies and principled hybrids of them**, with every surface built by Magnus's
mesher and solved by the verified BEM. We are not generating arbitrary blobs: every candidate is either a published
formula, Magnus's own family, or a bounded, documented combination of those.

## 1. Facts this plan rests on

| Fact | Source |
|---|---|
| The mesher implements exactly five profile formulas: `OSSE`, `R-OSSE`, `ICW`, `FREEFORM`, `LOOKUP` | `hornlab_mesher/config_parser.py` (type check), research doc s1 |
| No conical, exponential, tractrix, Le Cléac'h, hyperbolic-exponential, or spherical-wave family exists in the mesher | research doc s1 |
| `FREEFORM`: independent H and V cubic-Hermite meridians, 2–64 anchors each, anchors `[z, r]` or `[z, r, angleDeg]` (exact wall tangent), z strictly increasing, wall angle in [−90°, 90°], overshoot-free tangent speeds; 2–32 cross-section stations (ellipse/circle, superellipse, rounded rectangle) blended along t | `freeform.py:1-18, 524-913` |
| `LOOKUP`: exact `[z, r]` table, linear interpolation, axisymmetric only, no morph | `profile_formulas.py:1346-1392` |
| Morph system (`morphTarget` 1–3, `morphFixed`, `morphRate`, `morphCorner`, …) works for OSSE, R-OSSE, ICW, FREEFORM | `profile_morph.py:639-682` |
| OSSE/R-OSSE parameters may be azimuth expressions (`a = "60+10*cos(2*p)"`) | research doc s6 |
| The mesher can fit OSSE / R-OSSE / any polyline into an ICW curve (`seed_from_osse`, `seed_from_rosse`, `fit_from_points`) | `icw/seed.py:138-256` |
| No built-in OSSE/R-OSSE → FREEFORM conversion | research doc s3 |
| Solver verified today: GPU tests 18/18; analytic pulsating sphere PASS (0.020 dB); beat_cuda vs bempp 0.039 dB | `docs/evidence/SOLVER_VERIFY_2026-10-22.md` |

## 2. Classical typologies: realised as FREEFORM anchors from textbook formulas

New pure-maths module `hornlab_search/design/typologies.py` (no mesher import). Each function returns the
analytic meridian r(z) **and** its wall angle θ(z) = atan(dr/dz), sampled at N anchors; the anchors are passed to
Magnus's FREEFORM as `[z, r, angleDeg]`, so the mesher's Hermite spline reproduces both position and slope at every
anchor. The axisymmetric variants are also emitted as `LOOKUP` tables for verification (s7).

| Typology | Profile (radius r, axial z from throat, throat radius r₀) | Searched knobs | Defining property (unit test) |
|---|---|---|---|
| Conical | r = r₀ + z·tan α | α, L | constant wall angle α |
| Exponential | r = r₀·e^{mz}, m = 2π f_c / c | f_c, L | area S(z)/S₀ = e^{2mz} |
| Hyperbolic-exponential (hypex, Salmon) | r = r₀·(cosh mz + T·sinh mz) | f_c, T ∈ [0, 1], L | T = 1 reduces to exponential; T = 0 catenoidal |
| Tractrix (Voigt) | z(r) = a·ln((a + √(a²−r²))/r) − √(a²−r²) measured back from the mouth, a = c/(2π f_c) | f_c (sets mouth radius a) | tangent segment to the axis has constant length a |
| Le Cléac'h | spherical-wavefront construction: the area of the spherical cap normal to the wall follows the hypex law in f_c, T; wall built by marching along the cap arc length | f_c, T | cap area matches the hypex law at every step |
| Spherical-wave (Keele) | Le Cléac'h with T = 1 (exponential cap-area law); documented as that special case, not a separate formula | f_c | as Le Cléac'h |
| "Axisymmetric" | **not a family**: a cross-section mode. `axisymmetric: true` = one meridian for H and V and circular stations; otherwise H/V and stations are free | — | H == V meridians, circle stations |

Truncation rule (FREEFORM requires z strictly increasing and |wall angle| ≤ 90°): tractrix and Le Cléac'h profiles
are truncated where the wall angle reaches `max_wall_deg` (default 80°, configurable ≤ 85°). Their rollback beyond
90° cannot be represented by FREEFORM; R-OSSE and ICW-rollback remain the families that model rollback. This is
stated in each config and in the report.

Le Cléac'h gate: the construction is implemented from the published method and **must reproduce a published
reference profile** (to within 1 mm at the mouth) before its config is enabled; if no reference can be matched,
it ships disabled with an ISSUES entry, not with invented numbers.

Anchor placement: N = 12–24 anchors per meridian (≤ 64), placed by equal arc-length in (z, θ) so curvature is
resolved; a unit test bounds the max radial error of the Hermite reconstruction against the analytic curve
(target ≤ 0.2 mm, i.e. below the throat mesh resolution of ~5 mm by a factor of 25).

## 3. Magnus's families, used natively

| Family | Status today | Action |
|---|---|---|
| OSSE | searched (CP-8c) | keep; add one config exercising the morph to a rounded-rectangle mouth and one with azimuth-dependent `a` |
| R-OSSE | validator exists, **0 records, no config** | add `examples/rosse_baseline.yaml` (parameters and ranges from the mesher's own checks) |
| ICW | flat-baffle searched | add an ICW **rollback** config; `termination` is categorical, so it is a separate config, not a searched knob |
| FREEFORM | sculpt searched, anchors pinned by disjoint boxes | new monotone parametrisation (s4) |
| LOOKUP | unused | verification only (s7) |

## 4. Hybrids (all built by Magnus's mesher as FREEFORM)

1. **H/V hybrid**: `profileH` from typology A, `profileV` from typology B (e.g. OSSE horizontal for wide constant
   directivity, Le Cléac'h vertical). OSSE and R-OSSE meridians are sampled by calling the mesher's own profile
   functions, not by re-implementing them.
2. **Blend hybrid**: r(z) = (1 − w)·r_A(z) + w·r_B(z) on a common z grid, w ∈ [0, 1] searched. A convex blend of
   two monotone, increasing profiles is monotone and increasing, so every blend is a legal FREEFORM wall; the wall
   angle is blended consistently from the derivatives.
3. **Perturbed typology**: a typology profile plus a bounded perturbation in a **monotone increment**
   parametrisation, r_{i+1} = r_i + Δ_i with Δ_i = Δ_i^{base}·e^{u_i}, u_i ∈ [−u_max, u_max] searched. This replaces
   the disjoint per-anchor boxes that pinned three anchors in the sculpt runs, and it can never pinch the wall.
4. **Cross-section hybrid**: circle at the throat → superellipse or rounded rectangle at the mouth via FREEFORM
   stations, with the station t and exponent searched (the mesher blends stations with smootherstep).
5. **ICW seeded from OSSE/R-OSSE** via the mesher's `icw_seed` (already native).

One new design family `TYPOLOGY` in `hornlab_search/design/families.py` carries `typology_h`, `typology_v`
(fixed per run), the numeric knobs of s2, `blend_w`, the increments u_i, and the station knobs; `to_mesher_config`
emits a FREEFORM config. CMA-ES only ever sees numeric knobs.

## 5. Selecting what runs on the GPU

- `examples/targets/*.yaml`: shared targets (coverage, band, weights). Every family config can take
  `target_file:` so different typologies are scored on the **same** objective and their J values are comparable.
- `examples/typologies/*.yaml`: one config per typology and per hybrid, all on the same throat (25.4 mm exit) and
  size class so results compare.
- New CLI `hornlab-search campaign --families <list | all | classical | magnus | hybrids> --target <file>
  --budget N [--dry-run] [--seed S]`: runs one search per selected config, sequentially, with GPU/Julia hygiene
  before and after each (CLAUDE.md), then writes `campaign.json` and a cross-family leaderboard (best J, terms,
  failures, s/candidate, pinned bounds). `--dry-run` meshes the seed of every selected family and solves nothing.
- `hornlab-search families` lists every available typology/family/hybrid config with its knobs.

## 6. Search-quality fixes folded in

| Fix | Why |
|---|---|
| Failed evaluations are cached by design hash (or not counted against `--budget` on replay) | a re-run with the same seed spent its whole OSSE budget re-failing 40 designs (ISSUES) |
| `freeform_hv.yaml` to the quarter domain | FREEFORM symmetry verified (0.0043 dB); the full domain wastes ~4× dofs |
| Analytic pre-screen of mouth size vs dof cap | cheap rejection of `mesh_too_large` before calling the mesher |

## 7. Verification (before any result is trusted)

1. Unit tests: each formula's defining property (s2 table); Hermite-anchor reconstruction error ≤ 0.2 mm; blend
   monotonicity; increment parametrisation can never produce a decreasing radius; TYPOLOGY → FREEFORM config passes
   `families.validate` and the mesher's own validation.
2. Mesher acceptance: `campaign --families all --dry-run`, every seed meshes under the dof cap, topology checks pass.
3. Acoustic fit check (GPU): tractrix and exponential seeds solved as FREEFORM (Hermite anchors) and as LOOKUP (exact
   table), compared with `hornlab-search compare`; the shape approximation must not move metrics beyond the 0.039 dB
   noise floor by more than a reported margin.
4. Physics sanity (GPU): an exponential horn's beamwidth must narrow with frequency and a conical horn's must
   approach its wall angle at high frequency; an OSSE seed must hold its coverage. These are expected textbook
   behaviours; a violation is a bug.
5. Campaign at budget 40 per family on one shared target; leaderboard into the review page.

Expected outcome, stated in advance: classical axisymmetric horns (exponential, tractrix, Le Cléac'h) are
loading devices, not directivity controllers; their beamwidth narrows with frequency, so they will score worse than
OSSE/R-OSSE on a constant-directivity target. Their value here is as building blocks: the hybrids (OSSE horizontal
with a loading-optimised vertical, blends, perturbed typologies) are where new shapes can appear.

## 8. Work split for the implementation turn

| Lane | Who | Files |
|---|---|---|
| A. Formula library + tests (s2), anchor fit, LOOKUP emission | Sonnet subagent 1 | `design/typologies.py`, `tests/test_design_typologies.py` |
| B. `campaign` + `families` CLI, shared targets, budget/failure-cache fix, R-OSSE + ICW-rollback configs | Sonnet subagent 2 | `cli.py` (new subcommands), `search/cma.py`, `examples/targets/`, `examples/rosse_baseline.yaml`, `examples/icw_rollback.yaml`, tests |
| C. TYPOLOGY family, hybrids, increment parametrisation, OSSE/R-OSSE sampling via the mesher, configs, GPU verification (s7), review page | orchestrator (this agent) | `design/families.py`, `design/space.py`, `examples/typologies/`, evidence |

Every commit updates CONTINUITY and ISSUES. No gate threshold, plan file, or frozen contract changes. Bound
widening on existing configs remains the user's call; the new parametrisation is a new config, not a widening.
