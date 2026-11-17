# HornFab acoustic truth, typology and optimization

Master research + architecture + implementation handoff
Date: 2026-11-17
Status: Proposed engineering implementation plan, ready for local AI integration. This file does not authorize new GPU solves, queued jobs, a new production objective, an owner scoring decision, or rewriting historical research.
Repository: llevaachingada/Hornfab, canonical local checkout C:\Users\hunte\Hrns\hornlab-search; remote main inspected on 2026-11-17, most recent observed commit 1d6ebc8ebd1a3fd9f67facf800d920e0dbc3f254. The local agent must recheck current HEAD, working tree, owner instructions, and live jobs; remote state is a snapshot, not a lock.
Source document integrated: HornFab_Current_Typology_Acoustic_Grounding_Senior_Review_2026-11-17(1).md, provided by the owner. It is supplemented by the repo's CROWE V2/V2A, non-CD scoring dossiers, FABLE measured reports, the exact pinned mesher schema, and primary acoustic research linked below.
One-sentence decision: Stop spending scarce solves optimizing poorly resolved goals. First make the actual solver-bound surface measurable, make scoring choices and frequency fidelity explicit, and expose report-only physical pattern-quality diagnostics. Preserve the existing four-DOF CROWE area/aspect model. Implement the CPU-safe high-value packages now; prepare, but do not run, a small owner-approved acoustic pilot.

## 0. LOCAL AGENT: EXECUTE THIS HANDOFF, NOT ANOTHER OPEN-ENDED AUDIT

Immediate assignment

Work in the existing consolidated checkout. Read AGENTS.md, CLAUDE.md, docs/ACTIVE_STATE.md, the first 60–80 lines only of docs/CONTINUITY.md and docs/ISSUES.md, docs/knowledge/README.md, and relevant family cards. Search, do not wholesale ingest, large reports. Inspect git status --porcelain, HEAD, running jobs, pending ownership before editing. Respect the single-parent-integrator rule for git mutations and the current prohibition on extra worktrees.

Save this document to docs/research/HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md (new file; avoid replacing a differently authored version). Add brief navigation links to docs/INDEX.md and docs/knowledge/README.md if they are not already present; don't duplicate the research hub or the existing skill instructions. Update docs/CODE_MAP.md only when code is added, and current status logs according to repository rules.

Implement WP1, WP2 and WP3 below as self-contained CPU/read-only features, insofar as existing code does not already cover them. If a task is substantively implemented, test and reuse it, then mark it DONE instead of producing a second implementation. WP4 is optional if the first three finish cleanly. Each work package needs code, tests, an example invocation and a measured evidence artifact, not merely design notes.

Keep WP5/WP6 as owner-gated. Creating an offline candidate YAML or a non-runnable proposed command is allowed; do not enqueue CMA/BoTorch, mutate live queue files, change installed solver/mesher packages, silently switch briefs, or modify historical J.

Finish with a docs/evidence/ report containing commands, actual stdout/test exit codes, paths, HEAD SHAs, files changed, DONE/PARTIAL/BLOCKED tasks, measured values, and explicit decisions requiring the owner. The local integrator commits and pushes only per repo rules, preserving concurrent work.

### Scope boundary, non-negotiable

- Do not edit docs/plan/01_CONTRACTS.md or rewrite v6/v7 historical scoring behavior.
- Do not widen physical throat diameter as an optimizer variable. The installed HF1440 modeled radius is 18.0 mm (36.0 mm modeled diameter); the manufacturer's stated exit is 35.8 mm. That small engineering mismatch and the model's assumed 2-degree exit tangent are source-study questions, not licenses to choose arbitrary driver exits.
- Do not invent a universal horn grammar, surrogate, or geometry API. FABLE's U1 universal-backbone and full-J response-model tests did not justify those architectures. A canonical, sampled analysis record is useful; it is not a replacement generator.
- Do not assume historical verify means a finer mesh. In the measured 58-pair cohort it meant the same mesh and more solved frequencies.
- Do not compare different objective versions/briefs by scalar J, or call a +5 dB/dec DI slope a universally preferred home target.
- Do not promote the zero-round-hold version, the 20 mm hold A/B, the p=2.2 variant, an X crease, or a rolled lip to a universal construction rule.
- Do not alter or interrupt running jobs or concurrent lanes; read-only investigation is allowed if it cannot contend with them.

## 1. Why these are the highest-value tasks

### 1.1 Verified implementation and evidence state

| Topic | Confirmed in current code or measured repo report | Engineering consequence |
|---|---|---|
| CROWE V2A geometry | crowe_hv_area_aspect_v1.py exposes four continuous search dimensions: height_v_active_mm, L_forward_mm, area_mid_bias, aspect_timing_u50. Warped-quintic timing law was corrected; the old endpoint bug is closed. | Preserve four dimensions. No new knobs until mesh/acoustic authority is demonstrated. |
| Four fixed choices | width_h_active_mm=580, p_mouth=3.25, throat_round_hold_mm=0; fixed c2 20-mm circular hold and c3 p_mouth=2.2 are A/B configurations. | Leave fixed in initial search. A/B comparisons are not extra CMA axes. |
| New CROWE mesh | V2A evidence: 8,318-triangle 8 kHz quarter mesh; zero reported bad open/nonmanifold edges, proper 36 mm driven section. No acoustic solve. | Mesh topology is necessary but does not certify acoustic or analytic surface fidelity. |
| Exact mesher pin | pyproject.toml pins jamescollinharky/hornlab-waveguide-mesher@55da4f46...; the pinned mesher schema states surface_fit=auto uses OCC approximate for FREEFORM. Its input points are B-spline control poles, not necessarily interpolated points. Refining triangles does not remove the fit bias. | Build an analytic-to-actual-BEM-wall comparison. The error magnitude for the new CROWE area/aspect family is still unknown. |
| Existing geometry evidence | FABLE X1_ACCEPTANCE_TABLE.md and X4_COMPLETION.md already sampled five families on 65 stations × 61 azimuths. 55/55 selected designs pass their v2 relative-to-native-fit surface test; CROWE-X OSSE's recorded worst p99 was 1.646 mm against a 1.712 mm relative allowance. | Reuse the sampler and fit-floor method. Passing a relative sampler test does not establish high-frequency acoustic sufficiency, especially for a different new CROWE generator. |
| Metadata gaps | FABLE X1 could not pass the proposed exact metadata test for every family: e.g. termination kind, resolved source cap, wall thickness and implementation digest absent in older recipes. Some historical versions cannot be rebuilt byte-for-byte. | Do not manufacture missing provenance or rewrite old designs. Build a truthful completeness report; optionally add non-breaking metadata for future recipes after schema/owner review. |
| Historical score mismatch | CROWE_KLANGFILM_BRIEF_RESCORE_2026-11-17.md: unchanged Crowe ES-600 response J=16.918 base v7 vs 6.836 smooth v7; unchanged Klangfilm response 22.782 vs 8.924. | Different scales and trade-offs. Use the actual captured objective and a matched offline rescore to compare. |
| New v9 scoring | objective/scalar_v9.py, targets/profile.py, tests and dispatch exist and are registered. v9 supports H/V per-frequency corridors, DI detrended roughness and explicit optional HF floor; v9 diag and distd are unweighted diagnostics. | Do not reimplement v9. Create experimental configs and deterministic replay/readouts. The CROWE four-DOF config still points to the v7 smooth brief at this snapshot. |
| v9 owner decisions | scratch/fable_architecture/OWNER_DECISIONS_2026-11-17.md explicitly leaves C1–C4 open: point vs corridor/onset, constancy behavior, dead bands, one winner vs menu. | Compare proposals and report trade-offs. Do not silently adopt a v9 target or scoring weights for production. |
| Feasibility | FABLE_DISCOVERY.md surveyed ~3,414 valid rows across 35 configs; observed low-frequency V beamwidth not below roughly 66 degrees around 700–1,100 Hz in that cohort vs nominal V50. | A difficult target in a 480 mm-high envelope, not a proof of impossibility. Test onset and full-system intent before pursuing more exotic walls. |
| Score-grid uncertainty | 58 screen/verify same-mesh pairs, best-28 mean score shift ~+0.19 J, SD ~0.17 J, rank correlation ~0.81. N3_GRID_INDEPENDENCE_V9.md finds better interpolated grid consistency but residual 18-to-29 solved frequency error among top designs ~0.113 J SD. | Need independent frequency-sampling stability and genuine mesh convergence. A 0.05-J improvement by itself is not proven. |
| Source/installation | FaitalPRO states HF1440 physical throat 35.8 mm and recommended minimum crossover 0.7 kHz under specified conditions. HornFab uses a simplified uniform acceleration source and assumed 2-degree tangent. | Keep source fixed for geometry experiments; driver-specific and baffle experiments come later. A datasheet minimum is not a guarantee of every horn's 700-Hz headroom. |
| Optimization economy | SIGMA0_ANALYSIS_2026-11-17.md observed a 56% improvement when both sigma0 and bounds were changed in a comparison. | Use existing tools/search_preflight.py, not a global sigma0 recipe; improvement is not individually attributable to sigma0. |

### 1.2 Why geometry truth and score truth precede more generator code

A superior continuous shape law can be systematically transformed into a materially different OCC surface before the solver. Conversely, even the exact intended geometry can be incorrectly ranked if the objective rewards an unattainable V50 at 700 Hz, measures disconnected outer lobes as useful beamwidth, or gives a smooth rising DI curve an unintended penalty. Increasing optimizer dimensions or budget amplifies both problems. The aim of this plan is to close measurability, physical intent, and provenance before scaling up.

## 2. Scientific architecture: what each layer must mean

```
Owner acoustic brief / intended loudspeaker system
    |  explicit family, driver, baffle, frequency windows, target corridor
    v
Geometry generator (versioned equation + exact source interface)
    |  A(z), R(z), p(z); or family-specific OSSE / Keele / JMLC / rolled laws
    v
Mesher materialization (pinned fork, OCC fit, physical source, shell, mesh.msh)
    |  actual INNER ACOUSTIC SURFACE, not only generator's intended points
    +-------> CPU GEOMETRY TRUTH [WP1] (actual wall, section, shell, residual)
    v
Physical acoustic solve (source + mounting + mesh + solved frequency grid)
    |  response.npz with correct direction/solid-angle quadrature
    +-------> MEASUREMENT TRUTH [WP2, WP3]
    |           main lobe, secondary islands, DI, loading, diagnostics, grid sensitivity
    v
Versioned objective (v6 / v7 / v9; captured target, tolerance, weights)
    |  objective identity and diagnostic decomposition
    +-------> OFFLINE BRIEF EXPERIMENTS [WP3] (same physical response, different declared goals)
    v
Optimizer / BO / CMA, *only after the above is credible*
    |  no hidden change of source, geometry law, target or budget
    v
Verified candidates --> baffle / woofer XO / real driver / measurements
```

Rule: The generator is truth for intended geometry, the materialized BEM mesh for what was actually solved, the stored acoustic response for what was computed, and the captured brief/version for what was scored. A derived canonical surface or interpolated frequency grid is an analysis representation, never a substitute for one of these primary facts.

### 2.1 Family-specific construction, not a common equation

| Family | Scientifically supportable description | What not to claim | Appropriate acoustic research objective |
|---|---|---|---|
| Historic CROWE ES panel | Digitized model-specific H/V sections, inferred sweep/junction/exterior, drawing-inspired reconstruction. | Original Crowe proprietary ES internal 3D CAD or guaranteed 270-degree edge treatment. | Measured pattern and geometry against its own physical size and mounting; historical aesthetic/reference. |
| New crowe_hv_area_aspect_v1 | Original, smooth, independent cross-sectional area and aspect evolution with p-morph. Forward-only v1. | An exact Crowe, Keele or ATH horn; no X crease, no rolled return at present. | V/H pattern authority versus size, loading, off-axis quality, true solved-wall fit. |
| Keele-style biradial | Patent-inspired separate H/V trajectories, blend and a 3D joining implementation. | Proof that the numerical 3D joined surface is exactly patented construction or objectively constant-DI by name. | If owner's brief is CD, coverage and loading over the specified valid band. |
| ATH OS-SE | Equation-driven oblique spherical surface family with possible distinct H/V/morph/termination. | Equivalence of independent radial morph, axial pucker, and mouth lip. | Radiation, specified H/V coverage, measured physical source/mounting effects. |
| ATH R-OSSE / rolled families | Returned/free-standing termination can be a distinct acoustic boundary construction. | A mere circular lip appended to OSSE is the published R-OSSE formulation. | Compare correct physical rollback and freestanding vs flush/baffled context. |
| Le Cléac'h / Iwata / Klangfilm | Loading/contour-focused families with original elliptical/round transitions and their extensions. | Universal DI-slope preference, CD behavior solely because it is desirable for a different family. | Bandwidth/impedance smoothness, broad radiation shape, ripple, chosen non-CD profile. |
| MEH | Coupled multi-source, port/chamber/crossover geometry. | Valid MEH acoustic design from a single-source BEM model. | Combined source phase, ports, chambers, crossover summation and directivity. Exclude from the simple canonical-single-wall sampler. |

Scientific qualification: published waveguide work supports intentional H/V freedom, smooth geometric laws and multi-objective control of radiation efficiency/directivity. It does not prescribe HornFab's exact four variables or prove that A(z) and R(z) independently determine acoustic fields. They are efficient design coordinates, not independent physical responses.

### 2.2 CROWE forward equation and locked controls

For the current new family, with forward normalized distance u=z/L:

```
A0 = pi * r0^2                       [r0 from driver brief, fixed]
A1 = C(p_mouth)*(W/2)*(H/2)
C(p) = 4*Gamma(1+1/p)^2/Gamma(1+2/p)
log A(u) = log A0 + log(A1/A0)*[m0*u+(1-m0)*u^2] + area_mid_bias*B_A(u)
m0 = L*2*tan(exit_angle) / [r0*log(A1/A0)]
q = u50 / (1-u50)
w(u) = u / (u + q*(1-u))
S(u) = 6*w^5 - 15*w^4 + 10*w^3
log R(u) = log(W/H)*S(u)
p(u) = 2 + (p_mouth-2)*S(u)
a(u) = sqrt(A*R/C(p)); b(u) = sqrt(A/[R*C(p)])
```

Preserve a(0)=b(0)=r0, p(0)=2, R(0)=1, the modeled source tangent, monotonic forward wall radii, and the exact mouth dimensions of the continuous law.

Current continuous search: H 300–474 mm, L 220–340 mm, area bias ±0.15, u50 0.35–0.65, with W fixed 580 mm. These are the configured experimental bounds, not physics-given optimum bounds. Full-body envelope and viability need verification.

Keep p_mouth=3.25, throat_round_hold_mm=0 fixed for the initial analysis. p=2.2 and expanding-circular hold 20 mm remain paired categorical experiments, not added CMA dimensions.

The old smootherstep(u/a)/smootherstep(1/a) endpoint defect has been fixed; no work package here is allowed to 'fix' it a second time.

The 474-mm active height in a 480-mm total envelope leaves just 6 mm overall before an exterior roll/baffle. With 3-mm nominal wall each side this has virtually no room for a new physical bead. Measure actual full body before declaring that candidate manufacturable; do not equate active aperture with outer envelope.

Do not add ridge_start, p_mid, round_hold, independent late-area/late-aspect or lip radius to the optimizer until acoustic ablation proves a missing independent control axis.

### 2.3 What's actually measured; what's merely inferred

- The stored BEM uses an idealized source and existing observation distance/balloon. It predicts a horn model under that source and mounting; it does not predict the HF1440's phase-plug field, distortion or thermal limits.
- metrics/polar.py::beamwidth_deg uses outermost on-axis-referenced -6.0206 dB crossings; disconnected lobes can artificially enlarge a single beamwidth scalar. The diagonal function uses first crossing. Both can be valid definitions yet answer different coverage questions.
- Proper DI comes from 3D radiated power, weighted by spherical solid angle; theta/phi-grid balloon points are not equal-area, and applying compute_metrics without the canonical weighting path can bias DI. For replay use search/evaluate.py::metrics_from_response and verify parity with immutable J.
- v7 smooth DI slope +5 dB/decade is a hypothesis, not an accepted psychoacoustic standard. v9 is more expressive but must have an explicit target and reviewer-approved weights.
- Low-frequency V control is linked to active aperture, horn geometry, mounting and source field; a Keele sizing heuristic is one construction-specific guide, not an impossibility theorem. A 700-Hz electrical crossover does not logically require 50-degree V control at that exact frequency. The actual woofer/horn handoff matters.

## 3. WORK PACKAGES: IMPLEMENT NOW (no GPU / no new optimizer jobs)

### WP0. Integrate research without duplicating the knowledge hub

Value: Preserve reasoning and make it discoverable by local agents.

Implementation

- Create docs/research/HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md using this file.
- Link to existing docs/research/typologies/CROWE_HV_AREA_ASPECT_RESEARCH_V2_2026-11-16.md, CROWE_V2A_THROAT_TRANSITION_ADDENDUM_2026-11-16.md, docs/research/typologies/BIRADIAL_CROWE_STUDY_2026-11-15.md, docs/knowledge/README.md, and FABLE findings.
- Small index links in docs/INDEX.md and docs/knowledge/README.md; do not rewrite every typology card, frozen contracts or agent skill.
- Add a short top note distinguishing THIS prioritized proposal from the now-implemented v9 code and the still-open FABLE scoring menu.

Done when: master renders as Markdown, all internal repo links resolve, source links remain intact, no duplicated canonical guidance, index changed only as needed.

### WP1. Actual BEM-wall geometry-truth tool (highest engineering value)

Purpose: Quantify the mismatch between crowe_hv_area_aspect_v1's analytic law and the true meshed interior acoustic wall, for the c0 seed and representative search points. Existing 8-kHz mesh topology and law-level rank-4 test are not enough.

Reuse rather than rebuild

- tools/geometry/crowe_hv_area_aspect_sections.py and its generator evaluate() for intended law.
- FABLE scratch/fable_architecture/CANONICAL_SURFACE_CONTRACT.md v2, X1_ACCEPTANCE_TABLE.md, X4_COMPLETION.md, the .n1/.n1b/.x4c native-versus-mesh sampling routines where stable. Read code before porting; if an existing production utility can do this, use it rather than creating a second sampler. The canonical sampler is analysis, not an alternate mesher or generator.
- hornlab_search/mesh/build.py, existing mesh readers (compare/mshio.py), mesh physical-tag roles and topology validation. Record actual pinned mesher SHA and surface_fit result from built manifest, not only the YAML default.

Suggested standalone wrapper (new if not already present): tools/analysis/crowe_mesh_truth.py. It should accept --config, --out, optional --samples, and --existing-mesh/cached-artifact mode if the mesh exists. A global --no-solve safeguard must prevent acoustic execution; this tool builds/reads CPU meshes only.

Sample set: c0 at W580,H474,L300; 2–3 interior points (especially H~375–430 mm rather than solely the seed on its H upper bound); single-variable low/high points for all four knobs; 1–2 coupled feasible corners. Start with 8–12 geometrically admitted cases, and report invalid corners rather than patching bounds. Do not insist on an expensive 2^4 factorial if the first mesh check already isolates a repeatable systematic issue.

Actual comparisons, all in mm unless stated

- Generate native analytic cross-sections from evaluate() at 0,5,10,20,40,80,100 mm and at normalized 0,0.2,0.4,0.6,0.8,1.0. Sample azimuths 0,22.5,45,67.5,90 degrees. Use actual triangle-surface intersections/projected 3D distances for BEM inner surface, not nearest-vertex-only shortcuts.
- Compare radial half-span H/V, area(z), effective aspect ratio, normalized squareness/shape index, realized throat section, terminal mouth W/H, terminal z, wall slopes and accessible curvature. If mesh section reconstruction is unreliable at a station, mark that metric unmeasurable, not 0.0.
- For each case calculate mean, median, RMS, p95, p99, max and signed bias of inner-wall deviations. Compare against native mesher-fit floor and report both absolute error and FABLE v2's p99 <= max(1 mm, 1.25*native_floor) diagnostic. Passing this relative rule is not permission to ignore a 1.6-mm high-frequency wall deviation.
- Check loaded source face physical tag, 36-mm modeled source section, role-aware symmetry plane/winding/open edges, inner/outer non-intersection, minimum shell clearance, built outer bounding box W/H/D and depth including closure. Do not infer wall thickness and rolled-bead clearance from an inner-only bbox.
- If bias is persistent, determine whether it originates in FREEFORM control-pole fit, generator station density, angular samples, lip/corner approximation, remeshing chord error, or source closure. Repeat a small mesher resolution/station study to distinguish sampling error from triangle discretization. Test an alternative fit or geometry realization offline and only within fork-compatible support. Changing the pinned mesher or solution identity requires a separate explicit change decision.
- Geometry rank: reuse the current law-level Jacobian, then estimate normalized mesh-surface displacement columns for the four knobs using common canonical surface samples. For a seed at an upper bound use inward one-sided steps or an interior reference, not invalid central differences. Report singular values, column norms, pairwise cosine and rank with clear normalization. Distinguish geometry rank from acoustic independence.

Output artifacts: docs/evidence/CROWE_V2A_SOLVER_SURFACE_TRUTH_2026-11-17.md; machine-readable JSON/CSV in docs/evidence/crowe_v2a_geometry_truth/ or repository-accepted evidence location; one plot optional. Include exact config SHA, generator digest, mesher pin, mesh hashes, materialization spec, physical-tag extraction method, units, sampling method, rejection reasons.

Tests: analytic sphere/cylinder/known smooth superellipse cross-section fixtures; reflection/quarter-domain check; exact ring and area at generator level; intentionally offset mesh with a known signed error; correct classification of source and shell tags; deterministic repeatability; regression on existing c0 topology. Run real CPU mesher test only if permitted by current local contention.

Acceptance: all assessed configs produce a reproducible measured surface comparison or typed refusal; no silent omission, no fake analytic parity from mesher metadata, no mutations to stored BEM artifacts. A material geometric deviation is a measured finding and should block the acoustic pilot until characterized. Prefer fixing representation over adding search dimensions.

STOP condition: If the pinned mesher will not expose an accurate or role-selectable acoustic surface, produce the smallest failing reproduction and evidence, not a replacement mesher.

### WP2. Report-only physically meaningful pattern-quality measurements

Purpose: Existing -6 dB beamwidth collapses discontinuous/multi-lobed energy into a possibly misleading width. Add extra diagnostic output without altering objective or legacy metrics.

Suggested module: hornlab_search/metrics/pattern_quality.py plus a standalone read-only CLI under tools/analysis/ when no equivalent module already exists. Before coding inspect metrics/polar.py, metrics/diagonal.py, metrics/compute.py, targets/scoring_view.py, objective/scalar_v7.py H12 _oa_excess_term, and v9 scalar_v9.py. Reuse H12's already implemented opt-in off-axis excess where appropriate; do not add a second incompatible definition.

Report per frequency and separately by H/V cut

- Legacy outermost -6-dB width, untouched, for comparability.
- Boresight-connected -6-dB width: interval containing θ=0 until first crossing in each direction, plus number and angular extent of disconnected above-threshold islands.
- Positive off-axis excess relative to boresight (largest dB and angle), and mean excess exceeding the existing H12 threshold if desired. Clearly distinguish whole-cut and in-coverage regions.
- H/V signed upper and lower main-lobe edge; optional count of nonmonotonic threshold transitions. Report unmeasurable/censored (e.g. no -6 dB crossing) rather than interpreting 180 degrees as a measured exact beam.
- Where a full balloon exists: spherical energy/DI using the canonical sin(theta) quadrature, a coarse 3D concentration/lobe-island map with sampling-density warning, and H/V/diagonal coverage overlay. Do not use a 512-point balloon to claim angular resolution of features finer than the grid.
- Optional pattern_quality_flags for anomalous islands (> +0.5 or +1 dB off axis) are diagnostic flags only, not new weighted costs or user-independent pass/fail physics standards.

Synthetic fixtures: single Gaussian-like lobe; centered plateau; centered lobe plus disconnected outer lobe (legacy width grows but connected width does not); off-axis peak > on-axis; no crossing/censored; one-sided crossing; nonfinite angles and corrupted balloon; uniform omni with properly zero DI; equal-area vs theta/phi unequal-area weighting; quarter-domain H/V symmetry. Check zero angle exists and interpolation is angularly consistent.

Deliverable: machine-readable per-frequency quality report and a compact CLI report for 2–4 existing stored Crowe/Klangfilm/OSSE winners, using only immutable response.npz (no new solves); docs/evidence/PATTERN_QUALITY_READONLY_2026-11-17.md. If no full balloon or too sparse, annotate unavailable.

Acceptance: v1-v7 and v9 raw scoring/term identity unchanged bit-for-bit; no new default penalty; fixtures distinguish connected from outermost width; no off-axis metrics claimed when missing observations. This task is done independently of selecting a new objective.

### WP3. Objective/brief-truth replay and frequency-fidelity laboratory

Purpose: Make it trivial to see why a candidate wins within a specific captured brief and what happens under a separately declared experimental target, without pretending the run changed physically.

Reuse: docs/evidence/CROWE_KLANGFILM_BRIEF_RESCORE_2026-11-17.md, scratch/rescore_crowe_klangfilm_20261117.py, hornlab_search/search/evaluate.py::metrics_from_response, hornlab_search/objective/scalar_v9.py, hornlab_search/targets/profile.py, hornlab_search/targets/scoring_view.py, FABLE N3_GRID_INDEPENDENCE_V9.md and existing scoring tests. Do not fork a second scorer or directly call compute_metrics on theta/phi observations without the canonical weighting pipeline.

Suggested tool only if missing: tools/analysis/brief_truth_replay.py with input (run_dir/design_hash, brief yaml(s), --out) and output a clear paired within-brief comparison table. The tool must refuse to call cross-version raw-J a common ranking.

Implement these three cleanly separated uses:

1. Legacy identity replay. Load one CROWE and one Klangfilm stored response.npz; compute metrics through the same canonical run pathway; prove the originally captured J/weighted terms match stored values at floating precision. This should reproduce the existing November 17 report; if it doesn't, stop and diagnose sources/provenance.
2. Experimental v9 scoring view. Create optional OFFLINE/NOT-QUEUED v9 corridor candidates for H in an owner-interesting ~70–90/60–90 range, and V onset at 700 / 1000 / 1250 Hz. These are scenarios for decision, not an adopted target. Use the implemented schema (coverage_profile.mode: corridor or target, interpolation: log_frequency, per-anchor (hz,preferred_deg,min_deg,max_deg)) and validated v9 tolerance names. The 2026-11-16 RFC's early mode: frequency_envelope example is historical proposal syntax: it is not the current accepted v9 enum. Include the same physical source and nominal 80×50 descriptive target, but explicitly note that the scored corridor may differ.
3. Frequency-grid stability. Compare stored screen/verify on identical solved designs and meshes; report score differences on the original discrete grids and a common, clearly marked interpolated analysis grid (58 and 116 samples if reusing FABLE method). Do not claim a dense interpolated grid increases acoustic frequency resolution. Provide near-best rank stability and per-term sensitivity, plus the actual number/frequency locations of solved samples. Only a future denser solved pass can confirm missing narrow resonances.

Scoring rules:

- v9 uses cov_profile and di_roughness, not v7 cov and distd; diag and distd are raw, unweighted v9 diagnostics. objective.bw8k_floor is refused under v9; an optional explicit hf_floor may be declared separately. Always load through config.py / Target.from_dict instead of hand-waving YAML validity.
- v9 retains dislope; for a sensitivity experiment test a documented slope weight (including 0 if comparing a corridor-only goal) rather than implicitly adopting +5 dB/decade.
- Report cov_v_weight, flat_band, below-onset behavior (mask vs one_sided), onset H and V, DI source, actual DI slope, target profile at sampled frequencies, raw term values, normalized term values, weighted contributions, full J, observed H/V pattern, and any 8-kHz-related condition.
- Cross-target rescoring must recompute target-dependent metrics and use that new target's actual score implementation. Do not reuse source-run ripple/diag/floor values under a changed target. Raw J across different profile scenarios is a separate objective, not a single common leaderboard. Prefer the same-brief column for every comparison.

Deliverables: docs/evidence/HOME_CROWE_V9_OFFLINE_CANDIDATES_2026-11-17.md, source YAML candidate configs in a clearly named offline/research location, a CSV/JSON replay matrix and tests proving exact same-brief identity and refusal of unsupported cross-version pooled comparisons.

Acceptance: no stored run/result mutation; reproducible zero-GPU comparisons; scenario definitions and provenance explicit; original v7 stored J remains unchanged; no unapproved v9 production default.

### WP4. Source/geometry/provenance and envelope preflight (optional after WP1–WP3)

Purpose: Prevent repeated campaigns for designs whose materialized shape exceeds the intended product envelope or whose implementation is not reconstructible.

Implement the smallest useful piece, not a new subsystem:

- Create a report of intended active aperture, meshed acoustic mouth, physical outer shell, rollback/baffle margins, source matching, and actual mesh effective extent. Flag 474-H active in a 480-total envelope as near-no-margin, not universally invalid when no exterior roll exists. Treat lip and shell extension as categorical construction requirements.
- Produce a read-only provenance-completeness matrix for new vs archived designs: source driver exit, source cap details, generator identity/digest, actual mesher revision, mesh hash, grid, mounting, termination, physical tags, solver version, objective and brief identity.
- Record missing fields as UNKNOWN with source path, not fabricated null-is-zero or inferred measurements. If a stable preflight can catch invalid outer-envelope cases without changing existing admissions, add it behind an opt-in read-only check. Any change to which surface counts against the official envelope needs owner approval because FABLE C6 explicitly leaves that convention open.
- Do not retroactively rewrite historical identity digests, silently bypass historical mismatches, modify installed forks or require a new mandatory recipe schema without a compatibility decision. Proposed future metadata should be additive and tested against old recipes.

Deliverable: docs/evidence/HORNFAB_SOURCE_ENVELOPE_PROVENANCE_GAPS_2026-11-17.md, plus lightweight code/tests only if no duplicate exists.

## 4. OWNER-GATED WORK (PREPARE, DO NOT EXECUTE WITHOUT APPROVAL)

### WP5. Decide what the home 700-Hz/80×50 objective actually means

This is a physical loudspeaker design choice, not a code defect. The owner wants approximately 700-Hz crossover to a ported woofer system, horizontal pattern around 70–90° and desirable V control, while accepting size and smooth directivity trade-offs. Do not automatically turn that into exactly 80×50 at 700 Hz.

Compare on immutable stored responses (WP3 first):

- A. v7 point CD 80×50 from 700 Hz. Reference benchmark only; scientifically legitimate if that is the owner's explicit constant-directivity goal.
- B. v9 soft H/V corridor with V onset 700 Hz and explicitly broad lower-frequency V allowance.
- C. same v9 corridor with V onset 1000 Hz, then 1250 Hz. Below-onset should remain separately reported and potentially controlled only on its narrow side if chosen. Both mask and one_sided must be shown in the decision table; neither is silently assumed.
- D. optionally assess an independent beamwidth constancy descriptor (strict constant, slope-limited, or none). FABLE C2 remains open; adding it as a default weighted term without owner choice is disallowed. The repository's measured evidence says corridor-only may permit large internal swings.
- E. investigate dead bands per FABLE C3 but do not zero all smoothness terms: an objective that is flat over everything may erase any useful optimizer gradient.

Show actual 700, 900, 1200, 1600, 2500 and 8000-Hz beamwidth; loading/headroom around XO; W/H envelope; midband H/V; DI and whole-balloon behavior; off-axis islands. Judge ability to match the woofer, not just the horn standalone. Present 2–4 acoustically meaningful options and let the owner approve the production brief. Do not pick weights by making the incumbent look good.

### WP6. Small acoustic pilot only after WP1–WP5 and scheduling approval

Geometry: preserve four-DOF CROWE; use c1 box and fixed W580, p3.25, hold0, no X, no return. Use space-filling 12–24-candidate design set (including an interior seed, single-key effects and corners) rather than immediately activating the 200-CMA campaign.

Controls: at least one Keele-style and one OSSE/reference of matched effective active H/W and same source/mounting/score grid, plus a height-only contrast. Historical 417×203 Crowe panel is an aesthetic/reference condition, not a matched size reference for V700.

Independent measurements: beamwidth and connected-main-lobe H/V, off-axis excess and diagonal at 700/900/1200/1600/2500 Hz; impedance/loading, on-axis response, angular ripple, higher-frequency artifacts. Actual 8–20 kHz claim requires appropriately resolved meshes and solved frequencies; an 8-kHz mesh is not a 20-kHz validation.

Verification: top 3–5 candidates on meaningfully denser solved frequency grids, then a genuinely finer mesh; preserve source/solve identities, changed specs and paired term/rank comparisons. Report screen vs verify as frequency-grid differences if DOF is identical.

Search economy: only if pilot shows usable acoustic authority, decide whether CMA, BoTorch or a second DOE is warranted. Use tools/search_preflight.py with bounds/sigma coupling, refusal rate and known incumbent position; don't assume a universal sigma0. Search budgets are owner-authorized resources.

Feature ablations: only if the basic forward shape wins under matched size and physical metrics: hold0/20, p3.25/2.2, one vetted return/lip, and later a bounded X-ridge. Every feature must show a distinct mesh-level and acoustic effect before becoming a continuous knob.

Final physical system: test actual HF1440 exit/driver field sensitivity, intended baffle and woofer enclosure, crossover summation and listening-region radiation. Use measured impedance/driver data, not ideal piston BEM alone, before declaring a finished loudspeaker.

## 5. Architecture and code integration without widening the maintenance surface

Strong recommendation: Implement three reusable analyzers, not a second optimizer or a common all-typology horn generator.

| Layer | Prefer existing module | Proposed additive layer | Forbidden shortcut |
|---|---|---|---|
| Geometric law | design/generators/crowe_hv_area_aspect_v1.py | thin tools/analysis/crowe_mesh_truth.py wrapper, using canonical sampler/mesh utilities | Accepting generator analytic points as proof of BEM-wall geometry |
| Mesh & source | mesh/build.py, compare/mshio.py, pinned fork | sampled inner-wall/role/tag comparison, mesh and generator manifest | Editing installed .venv fork, writing new mesher, mixing outer wall with radiating surface |
| Physical pattern | metrics/polar.py, metrics/diagonal.py, objective/scalar_v7.py H12 | independent metrics/pattern_quality.py report-only metrics | Redefining historical beamwidth or silently adding an unapproved weighted term |
| Score/target | search/evaluate.py, targets/profile.py, objective/scalar_v9.py, targets/scoring_view.py | read-only tools/analysis/brief_truth_replay.py; versioned offline briefs | Applying v7 raw J to v9; v7 std(DI) as DI roughness |
| Data/provenance | original captured run/response files, FABLE canonical surface | additive analysis JSON/CSV with hashes and uncertainty labels | Replacing dataset identity, retroactively inventing missing source fields |
| Optimizer | existing CMA/BoTorch/CMA-ME and search_preflight.py | none until approved pilot | Launching 200 solves from unvalidated c1 or optimizing ~12 overlapping knobs |
| GUI | current scoring truth and 3D mesh view | later read-only diagnostic overlays if code and screens merit it | Mistaking view3d.js 'ridges' display edge overlay for a physical X-ridge |

Identity and provenance requirements for every new analysis row

Record: repo_HEAD, config_sha256, generator code/implementation digest if present, mesher git pin, actual mesher surface-fit mode, design_hash, mesh_hash, physical_solve_id if available, source-radius+assumed-angle, mounting mode, brief_hash, objective_version, target and weighted/tolerance identities, solved_freqs_hz, mesh_epw, balloon_grid and quadrature type, units and symmetry, tool version, output timestamp, and whether values are [measured], [derived], [interpolated], [proposed], or [unavailable].

Do not let analytic, sampled and meshed measurements share a field name without source qualifiers such as A_law_mm2, A_sampled_mm2, A_mesh_mm2. Do not call a stored /verify/ result a finer mesh unless the mesh hash/DOFs actually differ.

### Suggested end-to-end acceptance matrix

| Test | Pass/readout requirement | Why it matters |
|---|---|---|
| Law identity | A = C(p)ab; R=a/b; source tangent; warped S(u) endpoints; all source vars fixed | Preserve current good V2A math |
| Actual surface | Same triangle-domain/tag mapping, sections and absolute plus native-relative surface error, no hidden omitted cases | Prevent optimizing an imagined wall |
| Full geometry | Throat fit, outer wall, rollback, aperture-to-envelope margins; topology and clearance | Real printable horn, not just clean indexed triangles |
| Sensitivity | Each free knob moves actual wall; mesh-level SVD reported; not merely law-level rank | Four useful DOFs, not redundant sliders |
| Metric anatomy | Legacy outermost vs connected beamwidth differ on synthetic disconnected-lobe fixture | Avoid rewarding lobed coverage |
| v7 replay | Stored run J/terms exactly reproduced by canonical response-to-metrics pipeline | Parity and correct DI quadrature |
| v9 replay | Valid load of sample experimental briefs; raw/weighted terms and flags correct | Actual scorer semantics, not DOC speculation |
| Frequency fidelity | Report discrete/denser-interpolated/denser-solved distinctly; no fake resolution gain | False small wins avoided |
| Historical immutability | No changes to v6/v7 code, run files, old metrics, objective schema defaults | Reproducibility, trust |
| Work isolation | No active queues changed, no unrelated local edits overwritten, source reports indexed | Safe concurrent implementation |

## 6. Finish-line sequencing and exact handoff contract

Release A: close fully executable CPU tasks first

- A0: master research/index update.
- A1: WP1 geometric truth tool, tests, representative real CPU meshes and evidence. If a mesher fitting defect is measurable, report and characterize it, then stop geometry optimization work.
- A2: WP2 independent main-lobe/secondary-lobe and off-axis diagnostics, with fixtures and saved-response demonstrations.
- A3: WP3 offline v7 exact identity / optional v9 scenario / common-grid replay report; frozen-run invariants pass.
- A4 (optional): WP4 bounded provenance/outer-envelope report.

Each may land as a small committed unit under the authorized parent integrator. If concurrent files are owned by another lane, don't stomp them; document the exact dependency and complete independent pieces.

Release B: owner decision + small pilot, not yet authorized

Get an explicit decision on the v9 H/V corridor/onsets, constancy, DI weighting/dead band, enclosure convention, list of protected typologies, and whether the pilot should produce one winner or a shortlist. Then get separate scheduling authorization for GPU runs. Only then run WP6. A researched proposal is not authorization to change active studies.

### Completion report template (local agent must fill with real output)

```
HORNFAB ACOUSTIC TRUTH IMPLEMENTATION REPORT
HEAD before / HEAD after:
Working tree initial state:
Active GPU/CPU/night jobs when checked:
Files created:
Files modified:
WP0 research integrated: DONE/PARTIAL/BLOCKED + link
WP1 measured solver-wall fidelity: DONE/PARTIAL/BLOCKED + sample count + p99 + native fit floor
WP2 pattern-quality diagnostics: DONE/PARTIAL/BLOCKED + synthetic fixture result + saved-run IDs
WP3 offline scoring: DONE/PARTIAL/BLOCKED + exact identity J residual + v9 scenarios + grid error
WP4 provenance/envelope: DONE/PARTIAL/BLOCKED + unknown fields
Actual commands and full exit codes:
Tests passed/failed/skipped (explain all skips):
Historical data/objectives changed? MUST BE NO
GPU queue/start/interrupt performed? MUST BE NO unless separately approved
Unresolved factual uncertainties / decisions reserved to owner:
Commit(s) / push result, or explanation why integrator did not commit:
```

If time is limited, complete WP1 and WP3 with tests and evidence, then do a smaller WP2. Do not replace implementation with another 20-page abstract strategy essay. If the task is blocked twice on the same error, follow AGENTS.md and hand off the precise blocker rather than improvising a new architecture.

## 7. Specific claims not to overstate

- Area/aspect separation is mathematical, not acoustic decoupling. 3D wavefronts, modal excitation and directivity remain coupled.
- The pinned FREEFORM approximation is a proven mechanism, but new-CROWE acoustic harm is not measured. No implication that all FREEFORM geometry is unusable; existing Crowe-X relative sampling tests passed while showing measurable corner mismatch.
- The 700-Hz V50 degree target was unachieved in sampled histories, not proven forbidden. Mounting/baffle and source matter, and the installed speaker is a different problem from a freestanding horn.
- Screen/verify sampling difference is deterministic, not stochastic numerical noise. Adding interpolation does not create missing wave interference information.
- Objective v9 exists, but its adoption is owner-controlled. The prior 2026-11-16 RFC is historically tagged PROPOSED and contains an early example syntax that changed during implementation. Read actual targets/profile.py for current schema.
- The canonical sampler is already validated on its measured family set. X1 exact-provenance acceptance is still incomplete; the existing tests cannot automatically transfer their result to the newly introduced area/aspect family or absent source fields.
- Driver throat diameter is fixed to a published driver family, not an optimization variable. The modeled r0=18 mm is a historical 36-mm idealization of the published 35.8-mm HF1440 exit, and exit_angle=2° is an assumption.
- No proposed geometric tolerance is an acoustics standard. Absolute/relative fit thresholds in this document are diagnostic engineering gates; the final acceptable geometric error depends on frequency, local curvature and measured acoustic sensitivity.
- No rank is comparable across different mounting, source, brief, objective version or solved-grid identities without a deliberately controlled common comparison.
- No-X forward-only horn success validates a later X/roll final product. Each added physical termination/crease requires fresh 3D checks and acoustic verification.

## 8. Research and reproducibility references

### Repo-local, most useful reading order

- docs/knowledge/README.md and relevant family cards (canonical navigation and applicability guidance, not a replacement for raw evidence).
- docs/research/typologies/CROWE_HV_AREA_ASPECT_RESEARCH_V2_2026-11-16.md and CROWE_V2A_THROAT_TRANSITION_ADDENDUM_2026-11-16.md (family construction and final four-DOF decisions).
- docs/evidence/CROWE_HV_AREA_ASPECT_V2A_2026-11-16.md (actual sections, rank, 8k mesh, no acoustic solve).
- docs/research/typologies/BIRADIAL_CROWE_STUDY_2026-11-15.md and audit_2026-11-15/READINESS.md (history, real distinctions and correction labels).
- docs/evidence/NON_CD_SCORE_TRUTH_TABLE_2026-11-16.md and CROWE_KLANGFILM_BRIEF_RESCORE_2026-11-17.md (exact scoring audit).
- docs/research/typologies/NON_CD_OBJECTIVE_PROFILE_RFC_2026-11-16.md, hornlab_search/objective/scalar_v9.py, targets/profile.py and tests (separate historical proposal from implemented API).
- scratch/fable_architecture/FABLE_DISCOVERY.md, N3_GRID_INDEPENDENCE_V9.md (measured score resolution and feasibility).
- scratch/fable_architecture/CANONICAL_SURFACE_CONTRACT.md, X1_ACCEPTANCE_TABLE.md, X4_COMPLETION.md (reuse validated sampler; preserve provenance caveats).
- scratch/fable_architecture/OWNER_DECISIONS_2026-11-17.md and docs/ISSUES.md first bounded section (the decisions that are not approved).
- docs/evidence/SIGMA0_ANALYSIS_2026-11-17.md (measured search economy), plus tools/search_preflight.py.

### Primary/public technical references and relevance

- Keele, US4308932A, “Loudspeaker Horn” (1982): paired H/V Bi-Radial implementation and scoped CD geometry. https://patents.google.com/patent/US4308932A/en
- Crowe ES-600 product/reconstruction reference: named commercial design, approximate dimensions/return, not a public exact full-CAD law. https://josephcrowe.com/blogs/news/es-600-biradial-horn
- Crowe with TAD TD-2001 (2026): driver-specific revision of the flare/exit. https://josephcrowe.com/blogs/news/es-600-biradial-with-tad-td-2001
- Batík, OS-SE Waveguide (2020), original mathematical paper: radial/equation-based waveguide profile/morph. https://at-horns.eu/release/OS-SE%20Waveguide.pdf
- Batík, R-OSSE Waveguide rev7: returned/free-standing surface construction. https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf
- ATH CORE: explicit example of smooth round-to-rectangular morph with no required long constant-round transition. https://www.at-horns.eu/core.html
- Cinanni, Hybrid Constant Directivity Horn, AES 148 paper 10336 (2020): source/form/coverage geometry and 3D prototype approach. https://aes.org/publications/elibrary-page/?id=20753; open poster https://www.speakerlab.it/resources/AES-148_35_Poster.pdf
- Gu, You & Shen, JASA 158 (2025), Multimodal-based shape optimization of rectangular horns: coupled radiation efficiency, distinct H/V directivity and smoothness terms, not a mandate for one universal flare. https://pubmed.ncbi.nlm.nih.gov/40928147/
- Gu/You/Shen-related JASA (2021), Shape optimization of acoustic horns for improved directivity control and radiation efficiency: performance tradeoffs from modal optimization. https://pubs.aip.org/asa/jasa/article-abstract/149/3/1411/973064/Shape-optimization-of-acoustic-horns-for-improved
- Schmidt, Wadbro & Berggren, Large-Scale Three-Dimensional Acoustic Horn Optimization (2016): 3D computational shape optimization and gradient approaches; not automatically economical on this GPU. https://epubs.siam.org/doi/10.1137/15M1021131
- JASA (2024), Directivity of horns mounted in finite enclosures: baffle/enclosure changes low-frequency beamwidth; axisymmetric analytical study, not a validated exact prediction for rectangular CROWE. Full article: https://univ-lemans.hal.science/hal-04798282/document; abstract https://pubmed.ncbi.nlm.nih.gov/38546169/
- Makarski, AES 116, On the Velocity Distribution at the Interface of Horn Driver and Horn (2004): nonuniform exit boundary/source field. https://aes.org/publications/elibrary/elibrary-page/?id=12743
- Makarski, AES 117, Do Higher Order Modes ... Contribute ...? (2004): higher-order modal excitation at horn mouth/source. https://aes.org/publications/elibrary-page/?id=12845
- FaitalPRO HF1440 manufacturer page: 35.8-mm nominal exit, published crossover conditions. https://faitalpro.com/en/products/HF_Drivers/product_details/index.php?id=502020185
- Exact HornFab pinned mesher fork + schema: jamescollinharky/hornlab-waveguide-mesher@55da4f46d662d8dcd7a9f94a609eeea4009fcd62, docs/config-schema.md, mesh.surface_fit. https://github.com/jamescollinharky/hornlab-waveguide-mesher/blob/55da4f46d662d8dcd7a9f94a609eeea4009fcd62/docs/config-schema.md
- CMA-ES, Hansen tutorial: step-size, normalized variables and local search. https://arxiv.org/abs/1604.00772
- CTA-2034 standard resource: use full-speaker directivity/measurement concepts only after source+cabinet+woofer+crossover modeling, not on horn-only ideal-source solves. https://www.cta.tech/Resources/Standards

### Evidence quality labels to preserve

- [Verified implementation]: read in current GitHub code / pinned fork, still requires local HEAD check.
- [Measured prior]: real run files, stored tests, BEM comparisons, scores or CPU geometry logs from named repo evidence; not re-executed here.
- [Published]: manufacturer specification or peer-reviewed/professional source, within that source's actual scope.
- [Proposed]: decision, implementation route or experiment recommended here; NOT an existing code feature or an externally established numeric optimum.

### Commands (local agent adapts using actual --help, never guesses flags)

```
Set-Location 'C:\Users\hunte\Hrns\hornlab-search'
git rev-parse --short HEAD
git status --porcelain
.venv\Scripts\python.exe tools\night_status.py --since-hours 48
.venv\Scripts\python.exe -m pytest tests\test_design_generators_crowe_hv_area_aspect.py -q
.venv\Scripts\python.exe -m pytest tests\test_target_profile.py tests\test_objective_v9.py -q
.venv\Scripts\python.exe tools\geometry\crowe_hv_area_aspect_sections.py --config examples\typologies\crowe_hv_area_aspect_2026-11-16\configs\c0_four_dof_seed.yaml
.venv\Scripts\python.exe tools\geometry\crowe_hv_area_aspect_jacobian.py --config examples\typologies\crowe_hv_area_aspect_2026-11-16\configs\c1_four_dof_bounds.yaml
```

The existing commands shown above are grounded by current repository paths; any newly proposed analyzer's flags and file paths must be implemented and tested before citing runnable commands.

## 9. One-paragraph senior decision to carry into implementation reviews

Retain the four-dimensional forward area/aspect family and all historically supported physical typologies, but treat the physical response as a product of realized mesher surface, excitation, mounting, frequency sampling and declared objective rather than the generator law alone. The newest FABLE findings argue strongly for reusing canonical sampling and focusing on objective/profile choice and measurement fidelity, not constructing a universal generator/surrogate. Complete the geometry-truth, pattern-quality and offline v9 scenario tools now, with tests and saved evidence; preserve every old score. A fresh acoustic optimization campaign, new physical source model or new continuous shape knob must be justified by verified improvements at matched aperture/source and by explicit owner approval of goal, limits and GPU budget.
