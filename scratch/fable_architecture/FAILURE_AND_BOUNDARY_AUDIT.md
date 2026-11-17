# FAILURE_AND_BOUNDARY_AUDIT

Investigator B — read-only architecture research pass. No solves, no meshing, no queue mutation.
All counts below are parsed from extant `runs/*/search.ndjson` with `.venv\Scripts\python.exe`
(pure CPU, bounded, writes only under `scratch/fable_architecture/.tmp/`).

## Provenance / state this document describes

- Repo root: `C:\Users\hunte\Hrns\hornlab-search` (canonical checkout; `*-wt` worktrees ignored).
- **HEAD at dispatch-time check: `3efe9bef00d6889b4ae31120e9fcaba00b6a087e` @ 2026-11-16T19:38:34-05:00.**
  **HEAD at final check: `d187c0677948bf70673ecb5038a5d242f100a5d1` @ 2026-11-16T19:49:04-05:00.**
  The tree advanced **twice** during this read-only pass (concurrent lane). The tree later advanced to `50f3d8c` @ 19:55:43 (test/docs only): `git diff --stat d187c06..50f3d8c` shows **none** of the traced files changed, so all citations remain valid at `50f3d8c`. All line numbers below
  were re-verified against `d187c06` at the final check.
- State at final HEAD `d187c06`: `evaluate.py`, `outcomes.py`, `links.py`, `sizing.py`,
  `objective/terms.py`, `bo/data.py`, `tools/run_campaign_night.py`, `tools/night_status.py`,
  `design/generators/grid.py`, `mesh/build.py` are **clean/committed**. Of the search-path files
  traced here, only `M hornlab_search/design/generated.py` remains modified (plus the untracked new
  `generators/crowe_hv_area_aspect_v1.py`); the concurrent lane also has unrelated test/tool edits.
- The `generated.py` working-tree diff adds a `crowe_hv_area_aspect_v1` dispatch
  (`generated.py:58-60`, `:64-72`) and adds it to the family tuple (`:151-157`); the pre-mesh
  envelope-estimate block itself is **unchanged from HEAD** (now at `:205-221`, shifted +16 lines
  from the earlier read). `grid.py` and `mesh/build.py` are **already committed at `d187c06`**, so
  their envelope/DOF lines are HEAD content, not working-tree-only.
- A live CUDA solve (julia pid started 19:31) and a live night queue were present; nothing was
  touched, killed, or locked. No metric below is a fresh solve.

## 1. Denominators (defined once, used everywhere)

- **candidate-attempt**: one `search.ndjson` row. Cached rows are attempts too.
- **unique-candidate**: distinct `design_hash` within a run (summed per-run where noted; not a
  global dedup).
- **valid-geometry**: attempt whose `kind` is neither `invalid_geometry` nor `invalid_envelope`.
  (This is geometry/envelope admission, not acoustic merit.)
- **complete-BEM-solve**: `ok == true AND cached == false` — a BEM solve actually performed in
  this run. `ok == true AND cached == true` is a replayed stored Response and costs no solve.
- Acoustic data exist only for `ok == true` rows (`metrics` populated). A refused geometry
  (`ok == false`) carries **no** `metrics`; it is never a measured acoustic datum.

Two classification traps, both directly verified in code:
1. A **post-mesh** envelope violation is returned as `kind = invalid_geometry`
   (`evaluate.py:1577-1581`: `st["kind"], st["err"], st["no_marker"] = KIND_INVALID, why, True`),
   NOT `invalid_envelope`. Only the **pre-mesh** generator estimate is `invalid_envelope`
   (`generated.py:214-221`; `evaluate.py:1544-1548`).
2. The generator-error mapper checks `gerr.startswith("invalid_envelope")` (`evaluate.py:1546`).
   A family `GeneratorError` whose message is `"GeneratorError: invalid_envelope: ..."` does NOT
   start with that token, so it is mapped to `invalid_geometry` (run-level evidence in §3,
   `20261116T222251Z-screen-91ddfb`).
Consequence: the `geometry_refusal` vs `envelope_refusal` split in `outcomes.py:114-119` is
route-dependent and **cannot be trusted as an envelope count** for native or family routes.

## 2. Recent window (2026-11-16 only): the live home-brief boundary

53 runs with `search.ndjson` under `runs/20261116*`; parsed by
`scratch/fable_architecture/.tmp/agg_20261116.py` (source: `run_scan.json`, `run_agg_by_config.json`).

| bucket | count | note |
|---|---:|---|
| candidate-attempts | 2,538 | 53 runs |
| unique-candidate (sum of per-run distinct hashes) | 2,538 | no within-run duplicates |
| `ok == true` (valid-geometry + completed) | 2,288 | |
| `ok AND cached` (replayed Response) | 39 | no BEM cost |
| complete-BEM-solve (`ok AND !cached`) | 2,249 | **88.61 % of attempts** |
| `invalid_envelope` (pre-mesh estimate) | 81 | |
| `invalid_geometry` (all) | 169 | |
| …of which post-mesh envelope (error contains “outside the brief envelope”) | 26 | mislabelled as geometry |
| …other geometry (throat, generator laws, grid self-approach) | 143 | |
| `mesh_too_large` | **0** | current 24,000-dof cap; these families are small |
| `solve_failed` / `metrics_failed` / `exception` | **0** | clean window |
| valid-geometry rate | 90.15 % | (attempts − geometry − envelope)/attempts |
| complete-BEM rate | 88.61 % | solved-here/attempts |

Status: **directly verified** (extant NDJSON). Key reading: on the current home brief the live
boundary is **geometry/envelope, not GPU/DOF** — resource refusals are zero in this window. The
2026-11-14 status brief's "25 % never reached the solver (694 of 2,728)" (`docs/status/2026-11-14/README.md:18`)
is a *historical* 2026-11-12 record and is consistent with a lower DOF cap era, not a fresh number.

## 2b. Per-config aggregate (HISTORICAL rollup, all dates — not a same-brief comparison)

From `scratch/fable_architecture/.tmp/run_agg_by_config.json`, grouped by config name across every
dated run in `runs/`. Use only to contrast *constraint types*, never to compare J. Status:
**historical run record**.

| config | runs | attempts | ok | refusal mix (attempts) |
|---|---:|---:|---:|---|
| `freeform_sculpt` | 42 | 7,416 | 7,351 | 65 geometry |
| `osse_baseline` | 9 | 3,925 | 3,438 | 436 `mesh_too_large` (old 5k cap), 30 geom, 21 solve |
| `icw_termination` | 5 | 1,827 | 1,756 | 47 geom, 24 too_large |
| `atlas__ath_core` | 1 | 1,726 | 1,438 | 173 geom, 114 too_large |
| `atlas__hyb_osse_h_hypex_v` | 2 | 1,425 | 1,121 | 298 geom, 6 envelope |
| `perturbed_osse_hv` | 9 | 1,366 | 938 | 428 geom |
| `atlas__core_law` | 2 | 1,302 | 766 | 397 geom, 137 too_large |
| `lecleach_rollback` | 7 | 1,126 | 1,082 | 39 geom, 5 exception |
| `rosse_baseline` | 6 | 883 | 636 | 219 geom, 28 too_large |
| `freeform_hv` | 2 | 762 | 760 | 2 geom |
| `hl__klangfilm_lame_curved_v1` | 14 | 538 | 417 | 121 geom |
| `p80x60__ath_core_14in_home700_v7` | 9 | 532 | 457 | 63 geom, 11 too_large, 1 solve |
| `exponential` | 7 | 501 | 501 | none |
| `hyb_osse_h_hypex_v` | 5 | 450 | 396 | 54 geom |
| `osse_axi` | 11 | 428 | 411 | 17 geom |
| `blend_osse_tractrix` | 6 | 423 | 354 | 69 geom |

Reading: the **transition from resource to geometry/envelope** as the dof cap rose is visible across
the table (old `osse_baseline` is 11 % `mesh_too_large`; the 2026-11-16 window in §2 is 0 %). The
config names are not brief-comparable, so this table **cannot** rank families.

## 3. Selected contrasting runs (denominators explicit)

Parsed by `scratch/fable_architecture/.tmp/agg_20261116.py` / direct read.

| run id | config | att | unique | ok | solved-here | refused kinds | dominant refusal text |
|---|---|---:|---:|---:|---:|---|---|
| `20261116T095336Z-screen-7fc9b7` | `hl__crowe_x_osse_cd_v7` | 28 | 28 | 19 | 18 | 9 `invalid_envelope` | pre-mesh estimate |
| `20261116T044917Z-screen-12eb61` | `hl__ath_tritonia_landscape_v8` | 74 | 74 | 73 | 73 | 1 `invalid_geometry` | `outside the brief envelope (height 482 > 480.0 mm)` |
| `20261116T222251Z-screen-91ddfb` | `k_lame_E3_s11041` (klangfilm lame) | 26 | 26 | ~24 | ~24 | `invalid_geometry` | `generator: GeneratorError: invalid_envelope: max_mouth_w_mm 623… > 600` |
| `20261112T110126Z-screen-c414b1` | `atlas__osse_ext_throat` (cma_me/QD) | 401 | 401 | 281 | 280 | 120 `invalid_geometry` | all `outside the brief envelope (height …>300)` |
| `20261025T110253Z-screen-53594b` | `salmon_saddle` | 27 | 27 | ~2 | ~2 | 14 env, 7 geometry, ~4 exception | area-law + grid self-approach |
| aggregate `salmon_saddle` (7 runs) | — | 202 | — | 59 | — | 53 env, 46 too_large, 30 geom, 14 exc | see `run_agg_by_config.json` |
| aggregate `osse_baseline` (9 runs) | — | 3,925 | — | 3,438 | — | 436 too_large, 30 geom, 21 solve | old 5,000-dof cap era |

Status: **directly verified** (NDJSON) except the klangfilm `ok` count, which is **historical run
record** rounded from the run scan; `53594b` per-kind split is **directly verified**.
The QD run is the sharpest contrast: **120/120 of its refusals are post-mesh envelope**, coded as
`invalid_geometry` under a 300 mm height brief — i.e. the brief/envelope boundary, not a physical
or mesher impossibility.

## 4. The five distinct boundaries (do not conflate)

1. **Search boundary** — the CMA/QD box (`examples/**/*.yaml` `bounds:`). A knob pinned at a limit
   is *not* a physical limit; the watchdog reports it as “bound-pinned … widen the box”
   (`tools/run_campaign_night.py:185-203`). Evidence: `a_tritonia2_s1234` stopped with
   `morph_rate` at `[1.2, 2.1]` low (`runs/nights/home18_a_2026-11-16/a_tritonia2_s1234.log:15`);
   TRITONIA audit widened exactly that knob (`docs/queue/TRITONIA_V9_CMA_AUDIT_2026-11-16.md:3`).
2. **Mesher hard validity** — `MeshConsistencyError` (units / symmetry) is the ONE exception that
   stops a run (`evaluate.py:1-4`, `926-928`); `MeshUnitsError` fires when bbox extent leaves
   `[0.02, 5.0] m` (`mesh/build.py:38-41`, `261-268`). This is a correctness gate, not a tuning knob.
3. **Physical / manufacturing limit** — throat must be the driver's round exit when the gate is on
   (`evaluate.py:343-359`); grid self-approach requires `min gap >= 2t + 2 mm`
   (`grid.py:662-673`, `692-703`); plughorn/meh layout `reasons` (`generated.py:133-135`); wall
   thickness floor. These are grounded in printability/driver reality.
4. **Brief / envelope requirement** — owner-chosen box `600 × 480 × 480 mm` in
   `examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml`
   (`max_mouth_w_mm: 600, max_mouth_h_mm: 480, max_depth_mm: 480`). Enforced pre-mesh (estimate)
   and post-mesh (`evaluate.py:278-295`). It is an owner requirement, not a law of acoustics.
5. **GPU / resource limit** — DOF cap per mode (`examples/.../hl__ath_tritonia_landscape_v8.yaml:136-139`
   `dof_cap_* = 24000`, `dof_per_triangle 0.51`), enforced pre-mesh and post-mesh
   (`mesh/build.py:250-257`, `383-399`). This is hardware/budget, movable by cap or by shrinking the
   surface (which is itself an envelope/brief question).

## 5. Constraint classification of the frequent failures

| observed failure | class | evidence | status |
|---|---|---|---|
| post-mesh `height > 480` / `width > 600` (brief box) | fixed **owner requirement** | `evaluate.py:289-295`; brief yaml | directly verified |
| pre-mesh estimate refuses an **asymmetric** generic-grid section | **software-mesher limitation** (conservative estimate) | `grid.py:3015-3020` uses `max(radius)` for BOTH W and H | code directly verified; *realization* unverified (§7) |
| family `GeneratorError` with `invalid_envelope` in text → geometry | **software classification bug** | `evaluate.py:1546` startswith test; `91ddfb` evidence | directly verified |
| `grid self-approach: min gap < 2t+2` | **manufacturability** (+ mesher guard) | `grid.py:662-703` | directly verified |
| `spherical_salmon: area law grows slower than throat` | **hard math for that law** (generator identity) | salmon_saddle errors; `grid.py` salmon rows | plausible inference (law-specific) |
| `mesh_too_large … exceeds dof cap 5000` | **GPU/resource limit**, historical cap | `mesh/build.py:250-257`; osse_baseline aggregate | historical run record |
| `morph_rate` / `g_fc_hz` / `g_height_mm` pinned at box edge | **arbitrarily tight search bound** | watchdog logs; `docs/queue/HOME_18H_PLAN_2026-11-16.md:41-58` | directly verified |
| throat does not fit driver round exit | **fixed owner requirement / manufacturability** | `evaluate.py:343-359`; round throat is print default (`docs/status/2026-11-14/README.md:147`) | directly verified |
| `exception: GeneratorError …` (grid self-approach outside mapper) | **software bug**, since mapped | `evaluate.py:1567-1573` (S1b); `53594b` old rows | historical run record |
| `invalid_geometry` with unknown generator message | **unknown** | e.g. 143 “other geometry” in §2 are unbroken-down at scale | unverified |

Symmetry convention: `QUADRANT_FACTOR` / `SYMMETRY_PLANE` are single-sourced
(`sizing.py:16-17`) and a disagreement is a hard `SymmetryMismatchError` (`mesh/build.py:406-416`),
so a quarter/full mismatch is **not** a soft failure; no live run in §2 shows it.

## 6. Cheap feasibility prediction vs legitimate acoustic simulation

**Pre-mesh feasibility (cheap, no BEM) exists only for the generated/knob space.**
`GeneratedSpace.design_from_knobs` calls `registry.envelope_overshoot_estimate`
(`generated.py:205-221`) after `materialize`; that function (`registry.py:431-484`) mirrors the
post-mesh bbox and stores the relative overshoot capped at `_MAX_STORED_OVERSHOOT = 10`
(`generated.py:35-37`). The estimate is advisory by construction — any internal exception returns
`None` (`registry.py:423-424`; `generated.py:209-213`) — but a *positive* estimate becomes a hard
`invalid_envelope` (`generated.py:214-221`), so a wrong estimate is not merely cosmetic; it refuses
before meshing.

**Native families have no pre-mesh envelope prediction.** `DesignSpace.from_config` returns a plain
`DesignSpace` unless `cfg.generator` is set (`space.py:158-170`); native OSSE/R-OSSE/ICW/FREEFORM
configs have no `generator:` block (verified: `atlas__core_law.yaml`, `hl__ath_tritonia_landscape_v8.yaml`
both `generator: False`). Their only envelope gate is post-mesh `evaluate.envelope_violation`
(`evaluate.py:1577-1581`), mapped to `invalid_geometry`.

**Flat vs graded penalty.**
- Flat default: `_failure_penalty` returns `PENALTY_INVALID = 1e3` for deterministic kinds
  (`evaluate.py:1052`; `objective/terms.py:18-19`).
- Graded: only when `search.infeasible_penalty: graded` AND `kind == invalid_envelope`, it reads
  `_generator_overshoot` and returns `PENALTY_INVALID + 100·overshoot` capped at `2e3`
  (`evaluate.py:1046-1051`; `objective/terms.py:101-115`).
- **Directly verified consequence:** native families can never reach the graded branch (their
  envelope refusal is `invalid_geometry`, not `invalid_envelope`; and only generated designs carry
  `_generator_overshoot` — `generated.py:30-34`). This confirms the HOME_18H handoff's H4 claim
  “graded is inert for native families” (`docs/queue/HOME_18H_PLAN_2026-11-16.md:132-134`).
  The tritonia config does set `infeasible_penalty: graded` (`run_20261116T044917.../config.yaml`
  search block), yet observed its only refusal as flat 1000 — consistent with the branch being
  unreachable there.

**Strict resampling.** Opt-in only (`infeasible_penalty: resample_strict` or
`error_policy: retry_same_then_stop`, `cma.py:64-96`): deterministic refusals are redrawn from the
current distribution up to `RESAMPLE_CAP = 10` and **never told**
(`cma.py:62`, `73`, `179-181`); a transient is retried at most `STRICT_BACKEND_ATTEMPTS = 2`
(`cma.py:74`). This is the only path where the optimizer learns *nothing* from a refusal (it is
replaced, not scored).

**What the default optimizers actually learn from a refusal.**
- Legacy CMA: the refusal is told as the flat 1000 penalty — the in-code comment says so
  (`cma.py:538-544`), so pycma's fitness-range stops are neutralised in valid-budget mode but the
  covariance still sees a uniform wall at 1000.
- `budget_counts: valid`: deterministic refusals (`DETERMINISTIC_KINDS`) do not consume budget
  (`cma.py:56-60`); solved-but-failed still consumes it. So the search re-draws refusals up to
  `max_attempts` (default `4 × budget`, `cma.py:61`).
- QD (cma_me): docs say it uses a legacy finite penalty for QD refusals
  (`QD_DETERMINISTIC_REFUSAL_POLICY`, `cma_me.py:86`) and can exclude them from the archive
  (`cma_me.py:375`), so a refusal is ranked last in a batch rather than teaching a gradient.

**`search.links` cannot rescue generator refusals.** `reduce_space` raises
`ValueError("search.links is not supported with a generator block")` (`links.py:36-37`). Every
recent home family (`grid` / rolled / klangfilm / lecleach rows) is a generator block, so the
H5 remedy “couple L / lip / wrap with search.links” (`docs/queue/HOME_18H_PLAN_2026-11-16.md:135-136`)
is **blocked by code** for exactly the families that need it. Status: directly verified.

## 7. Proposed experiments — NOT run (before/after, read-only-safe where noted)

Marked as proposals; none were executed in this pass.

1. **Generic-grid false-refusal surface-vs-mesh check (the only way to settle §5 row 2).**
   For N asymmetric knob vectors near the envelope (`r_h ≠ r_v`), compare
   `grid.envelope_extents(...)` (pre-mesh; `grid.py:2989-3020`) against the actual meshed bbox from
   `build_mesh` (`mesh/build.py`) and `evaluate.mouth_dims_m` (`evaluate.py:262-270`). Count:
   (a) pre-mesh `invalid_envelope` that would pass post-mesh `envelope_violation` = **false
   refusals**; (b) the overshoot ratio on the smaller axis. CPU-only meshing, no BEM.
   *Do not assume false refusals are realized without this measurement.* Status: **unverified**.
2. **Reclassify post-mesh envelope and re-score a read-only window.** Split recent
   `invalid_geometry` by the error substring “outside the brief envelope” (already 26/169 in §2)
   and report geometry-valid vs envelope-valid denominators per config. No code change, NDJSON-only.
   Status: **partially measured** (the 26/169 count); full per-config split proposed.
3. **Native pre-mesh envelope estimator + graded penalty (A/B).** Build a native envelope predictor
   (mirror `envelope_overshoot_estimate` on native anchors), route it to `invalid_envelope`, and
   measure how many of the 120/401 QD envelope refusals become cheap-shaped validity without a
   mesher call. No solves. Status: **proposed; needs a design decision, out of scope here.**
4. **Generator-aware `links`.** Remove the `generator` guard in `links.py:36-37` behind a validated
   generator-link schema; measure refusal recovery on square-X / Crowe-X. Status: **proposed;
   blocked today by the guard.**
5. **Separate watchdog “bad” from deterministic refusal** (see WATCHDOG_REPLAY §“hypothesis”) so a
   QD run is not killed for a high refusal rate that is the algorithm working. Status: **proposed.**

## Counterevidence / limits

- The 2026-11-16 window has **zero** resource/solver faults, so it cannot by itself justify any
  GPU-limit narrative; the historical `osse_baseline` 436 `mesh_too_large` rows are from an older
  5,000-dof cap and are **not** comparable to today's 24,000 cap.
- The generic-grid conservative estimate is confirmed **in code**, but no measurement in this pass
  shows a *realized* false refusal. The suspicion is plausible, not proven.
- `run_agg_by_config.json` groups by config name across dates; it is a historical rollup, not a
  same-brief comparison. J is not comparable across briefs/objective versions.
