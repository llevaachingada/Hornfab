# Admission decisions — senior pass 2026-11-15 (priority: hl__rolled_es_spiral_v7)

This document records the senior decisions that close the pre-pilot gates from
[HANDOFF.md](HANDOFF.md) / [READINESS.md](READINESS.md), the reconciled retry/verification
accounting from the queue-audit lane, and the exact release protocol for the owner.

It supersedes the stale paste-block prompts in HANDOFF.md for the spiral cell only. No commit,
reset, or original-recipe edit was made; all original configs/briefs/recipes are untouched, and
concurrent dirty work is preserved. Evidence artifacts created by this pass:

- [SPIRAL_CAPABILITY.json](SPIRAL_CAPABILITY.json) — three isolated single-design acoustic solves
  (scratch/2026-11-15_readiness/spiral_capability/), memwatched, hosts cleared, authorization "a few
  isolated diagnostic solves" honored (3 solves; seed + prior EPW6/8 rows reused as reference).
- [spiral_body_witness.json](spiral_body_witness.json) + spiral_body_witness.py — read-only witness
  audit on the EXACT BEM meshes (seed sha 4f6d7f41bad77a11233b2b9f82091f91c45170f391c068845a3ff542d8e897a0
  byte-identical to the topology-audited es_spiral_seed) plus the three extreme-design meshes.
- admission.json — spiral cell updated: status approved with gate ledger and accounting; master
  `full_search_released` stays **false** (owner act).

## 1. Driver/source decision (gate: source_interface — RESOLVED, idealized)

Retained: brief `driver.exit_radius_mm: 18.0` + `exit_angle_deg: 2.0` as the historical modeling
interface, byte-preserved in brief `7d7d2d0cf0…`. The FaitalPRO HF1440 is a 35.8 mm combined exit
with a radial phase plug; the exit field, local tangent/curvature and the interface to the owner's
physical unit remain unestablished (DRIVER_SOURCE.md). Inventing a replacement cone is prohibited
by the prior audit and is not done.

Decision: the pilot's optimization target is an **explicitly labeled idealized-source landscape**:
the acoustic model is the rigid-wall BEM body with unit normal acceleration on the throat cap
(tag 2 "SD1D1001"), evaluated at 10 m on a full balloon with sin(theta) weighting. Every J, DI,
beamwidth and loading number in the pilot is a property of that idealized model — not an HF1440
prediction. Any future real-driver match requires measured or manufacturer polar data of the
physical interface and a NEW identity (source model version, new brief lineage); existing recipes,
responses and cohorts are never relabeled. The spiral kernel's 2-degree source term stays as the
prescribed throat blend; "leaves the throat axially" remains an inexact statement, which the brief
itself declares (narrowing horn by design).

Why not option (a) (model the real driver now): no field data exists on disk or in the audited
sources; a reconstructed phase-plug cap would be an invented boundary condition — the exact failure
mode the audit's source-validation gate exists to prevent. Why not postpone the pilot until a real
interface exists: the pilot's questions (control sensitivity, landscape usefulness, objective
behavior under the owner's stated coverage priorities) do not depend on the driver identity; they
depend on consistent identity, which the frozen brief bytes provide.

## 2. Objective decision (gate: objective — RESOLVED, brief frozen)

Frozen for the pilot: brief bytes `7d7d2d0cf0480d41f81e1b4970d17e05a4da66bb94dc0ce496d6726185910fe9`
(the owner-authored HOME LANDSCAPE 80Hx50V brief). No term is added, removed, reweighted, or
relabeled. Rationale, from the completed primary-source audit (PRIMARY_OBJECTIVE_SOURCES.md,
OBJECTIVE_OFFLINE.md):

- `di_slope_target: 0.0` is the chosen **constancy** design goal; zero slope is legitimate when
  constancy itself is the objective. No universal DI-slope preference exists in the audited
  sources (0 and 5 dB/dec are both unsupported as universal targets; the smooth brief stays a
  historical experiment and is NOT promoted).
- `distd` (w 0.5) penalizes std(DI) — including a perfectly smooth rise. This legacy double-count
  is documented, replayed exactly (32 replays, zero delta), and retained unchanged for pilot
  comparability. `flat` is detrended residual roughness, not raw SPL std; scored from the 700 Hz
  crossover per `flat_band: scored`.
- Diagonal `65 deg` is a **shape prior** with first-crossing semantics, distinct from H/V
  outermost crossings; same 80x50 axis crossings permit 59.92–66.81 deg diagonals. Retained as a
  prior, not evidence of preference.
- The owner's room/system priorities are already explicit in the brief: coverage 80/50 deg with
  `cov_v_weight 0.5`, coverage weight 1.0 tol 3.0, loading at the 700 Hz XO (`loaded_hi_hz 5600`),
  band 350–8000 Hz. These stay.
- Pilot winners will additionally be reported OFFLINE with the separate-metrics table the audit
  prescribed (unweighted slope dB/dec and dB/oct, absolute DI, DI spread, diagonal target error,
  coverage/loading) before any brief copy is ever approved. The omit-term ablations are
  diagnostics, not approved scores.

## 3. Body/clearance and control-capability gates (gates: full_body, domain_capability — PASSED at witness/sensitivity level)

**full_body (witness).** On the exact solved seed mesh and the three extreme-design meshes:

- Zero transversal triangle-triangle intersections among nonadjacent facets (exact interval
  predicate, pruned candidates, near-coincident-vertex welding at 1e-6 m; fixtures: known crossing
  → cross, duplicated sharp fold → not a crossing, parallel sheets 3 mm → none).
- Minimum sampled nonadjacent clearance ≈ **0.000733–0.000745 m** across all four designs,
  consistently in the wrap/rollback-lip regions — an intrinsic, design-stable property of the
  rolled spiral (thin, but separating; no crossings touch or cross). Report value is an
  upper… i.e. the true clearance is <= the sampled value at probe resolution; this is a
  resolution-bounded witness, not a manufacturing report.
- Topology (from the prior audit, byte-identical mesh): zero nonmanifold edges, zero degenerate /
  duplicate faces, boundaries only on symmetry planes; worst shared-edge normal angle 118.58 deg
  — acute junctions exist in the Crowe family sense but nothing approaching inverted winding.
- Source cap: rim junction with the body throat ring is a designed contact (distance 0 there is
  the junction itself); f11/loaded_hi 5600 Hz unchanged.
- True fixed-z aperture sections (quarter-contours closed through the x=0/y=0 symmetry planes,
  area semantics labeled quarter vs full): seed aperture progresses 4·2.5209e-4 → 4·5.9865e-3 m²
  (full-body) across the sampled span with non-monotone rebounds (wrap + pucker), dA/dz max
  ≈ 4·0.209 m²/m near the mouth — the aperture is a real rising-law section series, and the prior
  audit's "nonplanar projected ring area is not axial aperture area" gap is now closed for this
  mesh by actual constant-z sections.

Not claimed: watertightness proofs, manufacturing clearance, EPW8-mesh topology (accepted
limitation: same design, finer sampling, same policy), or role separation inside the mesh (roles
are resolver-side; the mesh has only body + source-cap tags — documented in the witness JSON).

**domain_capability (sensitivity).** Three isolated single-design solves at box extremes vs the
seed row (same EPW6 identity, same brief bytes, fresh caches):

| variant | change | design | J (vs seed 29.915059) | ΔJ | ×mesh-noise |
|---|---|---|---|---|---|
| terminal_low | terminal 270→200 deg | eebccb4bfc13 | 29.803910 | −0.111149 | 76× |
| pucker_max | puckers 6/8→18/24 mm | 917bbbf7fd5f | 28.843675 | −1.071384 | 734× |
| depth_high | depth 238→380 mm | 9f9d46dbf404 | 33.389940 | +3.474880 | 2380× |

Same-design two-mesh noise is ΔJ −0.00146 (SPIRAL_ACOUSTICS.json). Searched controls are
acoustically active in graded directions, and the seed is not on a boundary plateau (pucker
direction improves, depth direction degrades — a real gradient exists). The 10-dim box has real
refusals (62/64 preflight; 2 invalid_geometry) and CMA concentrates near the seed, so the
30-evaluation budget is spent on informative motion, not on a flat landscape. These are 4-point
sensitivity observations at one mesh policy — not a landscape map and not convergence.

Open risk (accepted, accounted): sigma0 0.2 initial steps are large (nominal 36 mm depth, 15 deg
terminal angle); the pilot itself is the experiment that measures the basin; the draw cap and
retry policy bound the cost of an unproductive basin.

## 4. Convergence gate (OPEN — carried by the pilot's validation, not claimed)

Only two same-design meshes exist (EPW6/EPW8): sensitivity-scale evidence, not established
convergence. No convergence claim is recorded for admission. Validation is carried explicitly by
the pilot plan below (winner verify solves at verify identity), in addition to — not instead of —
the discovery budget. Geometry sampling / frequency / angular refinement remain unrun
(`spiral_epw8_angular.yaml` stays unsolved by choice).

## 5. Queue accounting (reconciled; queue-audit lane findings incorporated)

Strict-mode semantics (verified at code level by the disjoint audit lane; cma.py:56-96, 764-887,
808-919): budget 30 counts **non-cached, tell-eligible evaluations**; strict draw cap 45
**includes the seed** and every resample-replacement; cache hits consume draws but not budget;
`retry_same_then_stop` gives at most ONE same-candidate retry per transient `solve_failed`
(incrementing `backend_calls`, not draws); refusals consume draws and are separately counted;
draws exhausted before 30 valid → resumable stop `strict_draw_cap`; a failed retry → resumable
stop `strict_infrastructure`; 3 consecutive non-cached `solve_failed` → hard abort (exit 1).
**All strict stops exit 0**: the morning review MUST read run.json `stop_reason` /
`budget_counts` / `strict` block — exit 0 + row count is not proof of completion.

Per seed (2 seeds, 1234/5678 only):

- ≤ 30 fresh valid acoustic evaluations (discovery). Verified: default cache/runs/dataset contain
  no historical spiral entries; the seed row will be a fresh solve. Do **not** link the scratch
  diagnostic caches into the default cache — namespace `p2-b4bfdad98ff1` would match and hand the
  seed a free budget row silently. In-run duplicate-candidate cache hits cost only draws.
- ≤ 45 draws = 1 seed + ≤ 44 CMA proposals/replacements (refusal-heavy slot can burn up to 11
  draws: 1 original + 10 replacements). Preflight predicts ~31 draws per 30 valid at the uniform
  3.1% refusal rate; 45 also covers the historical 22-36% refusal regime at reduced yield.
- popsize resolves to 10 (pycma default 4+3·ln10 for 10 dims) → seed + 2 complete told
  generations + partial third at budget stop.
- Wall expectation ≈ 30 × 40–55 s ≈ 20–30 min nominal; worst case 45 × 54 s ≈ 40.5 min; job
  timeout 3600 s holds ~1.5–2× headroom under measured conditions. Residual risks: a hung solve
  burns ≤ 900 s (25% of budget); a WDDM spill can inflate every solve 5-10× — the night runner's
  per-job gpu-clean pre-hygiene and the recorded memwatch gates are the mitigations; a timeout
  truncates mid-flight (run.json status "running") and is resumable ONLY by explicit `--resume`
  (the pilot never auto-resumes; job 2 remains independently guarded).

Verification (EXPLICIT, outside the 30/45 accounting — exposed, not hidden):

- Route: `tools/geometry/verify_rolled_rect_night.py --night <night> --top 1` per seed job
  (rolled_rect_cli has no verify-night subcommand; its pinned bytes must NOT be patched — the
  digest guard would invalidate the recipes). Nonzero-exit or timeout jobs are skipped by the
  helper (verify_night_jobs.py).
- Cost: +1 winner solve per seed at verify identity (~29-30 freqs vs 18, 1024-point balloon vs
  512, same f_max → same ~4500-dof mesh; ≈ 3-4× a screen solve, 2-5 min warm). These are fresh
  cache-namespace solves.
- Night total: 2×30 discovery + 2×1 winner verification = **64 fresh acoustic solves planned**,
  bounded by draw caps; retries and refusals consume only draws/time, not budget rows. Third seed
  9012 stays deferred (conditional on informative first-two results). No Bayesian jobs; no resume
  of the old E tail; the other 25 cells remain held and excluded from the solve list.

## 6. Release protocol (owner act; nothing launches from this pass)

```powershell
# 1. release switch (owner only; admission.json is the unpinned authority)
#    edit "full_search_released": false -> true in docs/queue/rolled_readiness_2026-11-15/admission.json
# 2. launch the reviewed night (two guarded jobs, one GPU solve at a time by construction)
.venv\Scripts\python.exe tools/run_campaign_night.py --night docs/queue/rolled_readiness_2026-11-15/pilot_HELD.yaml
# 3. morning reconciliation (REQUIRED; exit 0 is not evidence)
#    per run dir: read run.json stop_reason (require "budget"), budget_counts.valid == 30,
#    strict.draws <= 45, retries, refusals; then winner verification:
.venv\Scripts\python.exe tools/geometry/verify_rolled_rect_night.py --night <night> --top 1
# 4. report winners with the separate-metrics objective table (offline, from stored responses)
```

Guard behavior (verified): every job re-reads admission.json and re-hashes all pins in a fresh
process; pin mismatch, non-approved cell, unreleased master, or seed outside {1234,5678} exits
before any launch — a failing first job cannot expose the second.

## 7. Remaining (explicitly NOT part of this admission)

Section-kernel (`sp__*`) and other families' own full-body/capability evidence; role-separated
mesh re-tagging; frequency/angular refinement; real-driver interface work; GUI catalog exposure
reconciliation; slices C/D/E for remaining cells. These follow the audit's slices when the owner
releases them; nothing in this pass pre-authorizes them.
