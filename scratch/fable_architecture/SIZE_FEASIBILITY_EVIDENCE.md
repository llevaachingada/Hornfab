# SIZE_FEASIBILITY_EVIDENCE

Investigator B — read-only. Traces every product-envelope enforcement point end-to-end.
No meshing, no BEM, no queue mutation. CPU-only parsing of extant NDJSON/YAML under
`scratch/fable_architecture/.tmp/`.

## Provenance

- Repo root `C:\Users\hunte\Hrns\hornlab-search`.
  **HEAD at dispatch-time check `3efe9be` @ 19:38:34; HEAD at final check `d187c06` @ 19:49:04**
  (2026-11-16, local). The tree advanced during the pass. The tree later advanced to `50f3d8c` @ 19:55:43 (test/docs only): `git diff --stat d187c06..50f3d8c` shows **none** of the traced files changed, so all citations remain valid at `50f3d8c`.
- At final HEAD `d187c06`: `design/generators/grid.py`, `mesh/build.py`, `registry.py`,
  `search/evaluate.py`, `bo/data.py` are **clean/committed** — their envelope/DOF lines are HEAD
  content. Of the files traced here, only `M design/generated.py` remains dirty: it adds a
  `crowe_hv_area_aspect_v1` dispatch
  (`generated.py:58-60`, `:64-72`, `:151-157`) but leaves the pre-mesh estimate block unchanged
  (now `:205-221`, shifted +16 lines). The new `generators/crowe_hv_area_aspect_v1.py` is untracked;
  its envelope routing is **not traced here** (actively being developed).
- Production brief under audit (do NOT edit):
  `examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml`,
  `envelope = {max_mouth_w_mm: 600, max_mouth_h_mm: 480, max_depth_mm: 480}`.

## 1. Enforcement points by route (stage → formula → surface → status → optimizer → acoustics)

| # | route / stage | exact formula (path:line) | surface tested | status returned | optimizer treatment | acoustic data saved? |
|---|---|---|---|---|---|---|
| 1 | **native** (OSSE/R-OSSE/ICW/FREEFORM), pre-mesh | **none** — `DesignSpace.from_config` returns plain `DesignSpace` when no `cfg.generator` (`design/space.py:158-170`) | — | — | — | — |
| 2 | native, post-mesh (authoritative) | `envelope_violation` (`search/evaluate.py:278-295`): `w = Δbbox_x·(2 if "yz" in symmetry)`; `h = Δbbox_y·(2 if "xz")`; `depth=(zmax−zmin)·1000`; fail if `w·1000 > W+0.5`, `h·1000 > H+0.5`, `depth > D+15.0` | meshed **outer** bbox incl. shell (`mouth_dims_m:262-270`) | `KIND_INVALID` = `invalid_geometry` (`evaluate.py:1577-1581`) | flat `PENALTY_INVALID=1e3` (`evaluate.py:1052`; `objective/terms.py:18`); `resample_strict` if opted in (`cma.py:80-83`) | only if admitted; refused rows carry no `metrics` |
| 3 | **generated FREEFORM** (typology anchors), pre-mesh | `registry.envelope_overshoot_estimate` (`design/generators/registry.py:431-484`): `W=2·(max profileH r + wt)`, `H=2·(max profileV r + wt)`, `depth=(max z − min z)+wt`; overshoot `max(W/limW−1, H/limH−1, D/limD−1, 0)` (`:478-481`) | materialized anchor lists, no mesh | positive overshoot → `invalid_envelope` + `_generator_overshoot` capped 10 (`generated.py:214-221`, `:35-37`) | flat 1000, or graded `1000+100·over` cap 2e3 when `search.infeasible_penalty: graded` (`evaluate.py:1046-1051`) | none (no mesh, no BEM) |
| 4 | **generic GRID radial**, pre-mesh | `grid.envelope_extents` generic branch (`design/generators/grid.py:2989-3020`): `r_h=interp(L,mh)`, `r_v=interp(L,mv)`, `radius=_radius_field(r_h,r_v,phi,…)`, **`outer=max(radius)+wt`**, `W=2·outer`, **`H=2·outer`**, `D=L+wt` (`:3015-3020`) | sampled superellipse radius field at the mouth | `invalid_envelope` (`registry._grid_overshoot_estimate:404-428` → `design_from_knobs`) | flat / graded as row 3 | none |
| 5 | generic GRID depth, materialize | `_meridians` (`grid.py:442-457`): if `check_envelope and env and L_knob > max_depth` → `GeneratorError` (`:455-457`) | knob `L_mm` | `GeneratorError` → `invalid_geometry` (`evaluate.py:1544-1548` for `_generator_error`; `:1567-1573` for build) | flat 1000 | none |
| 6 | **rows** route, pre-mesh | `_rows_envelope_extents` (`grid.py:2817-2842`): per azimuth `c=|cos φ|, s=|sin φ|`; `width=max(2·max(y·c))+2wt`; `height=max(2·max(y·s))+2wt`; `depth=(x_max−x_min)+wt+|bend|` (`:2835-2842`) | per-azimuth row marches (same used by mesher) | `invalid_envelope` | flat / graded | none |
| 7 | **rolled / family** routes, pre-mesh | `grid.envelope_extents` family branch (`grid.py:2997-3002`): returns `family.resolve_grid(block,brief)['meta']` `mouth_w_mm / mouth_h_mm / x_span_mm` | the family's own resolved grid/meta (per-plane) | `invalid_envelope` | flat / graded | none |
| 8 | **CAD plughorn**, materialize | `generated.plughorn_params` (`design/generated.py:99-104`): `outer_w/outer_h/depth_total > env+0.5` → `ValueError` | tool `derived()` outer dims (recipe, no mesh) | `_generator_error` → `invalid_geometry` (`evaluate.py:1546`, prefix is `ValueError:`) | flat 1000 | none |
| 9 | **CAD meh**, materialize | `generated.meh_params` (`generated.py:136-141`): `mouth_w/mouth_h/env_d_mm > env+0.5` → `ValueError`; layout `reasons` → `invalid_geometry` (`:133-135`) | tool `derived()` | `invalid_geometry` | flat 1000 | none |
| 10 | **BO candidate pool** (no solve) | `bo/data._envelope_ok` (`bo/data.py:1219-1236`): fail if `desc > limit+0.5` for w/h/depth — **0.5 mm on depth, no +15 allowance** | `_surface_descriptors` (`:1200-1216`): **inner** surface for native (no shell); rolled-family outer included (`:1262-1266`) | `schema_rejected` if `_generator_error` (`:1112-1114`), else `envelope_rejected` (`:1126-1133`) | pool admission only | no mesh/BEM; `bem_called:false` (`:1152-1153`) |
| 11 | all routes, post-mesh (redundant safety net) | same `envelope_violation` as row 2, runs after row 3/4/6/7 | meshed outer bbox | `invalid_geometry` (`:1577-1581`) | flat 1000 | only if admitted |

Tolerances are deliberately different: pre-mesh W/H use `_ENVELOPE_MOUTH_TOLERANCE_MM = 0.5`
(`registry.py:384`), depth uses `ENVELOPE_DEPTH_ALLOWANCE_MM = 15.0` (`evaluate.py:275`,
imported by `registry.py:418`, `:468`); the post-mesh gate uses literal `+0.5` for W/H
(`evaluate.py:289-291`) and `+15.0` for depth (`:293`). The BO pool uses `+0.5` for **all three**
(`bo/data.py:1234`). Status: **directly verified**.

## 2. The known suspicion — generic-grid envelope is conservative on the small axis

Claim under test: `design/generators/grid.py::envelope_extents()` sets **both W and H** from the
max-phi radius for the generic radial grid, and is therefore conservative on the **smaller axis**
of an asymmetric section.

- Code: `grid.py:3015-3020` computes one `phi` sweep, one `radius` array, then
  `outer_radius = float(np.max(radius)) + wt` and returns `(2·outer_radius, 2·outer_radius, L+wt)`.
  `np.max(radius)` over a full `phi∈[0, π/2]` sweep is ≥ the endpoint radius on either axis when
  `r_h ≠ r_v`, so both the reported width and height are ≥ the true half-axis-derived extents.
- **Confirmed: YES, the estimate is conservative on both axes and therefore on the smaller axis of
  an asymmetric section.** Status: **directly verified (code reading)**.
- It is **not** merely advisory: a positive estimate becomes a hard pre-mesh `invalid_envelope`
  (`generated.py:214-221`), so an over-estimate can refuse a candidate the post-mesh bbox would
  pass.
- Other routes use different methods and are **not** both-axis-max:
  - generated FREEFORM: per-axis `2·(max profileH r + wt)` and `2·(max profileV r + wt)`
    (`registry.py:478-479`) — correct per-plane.
  - rows: per-azimuth `cos φ` / `sin φ` weighted width/height (`grid.py:2836-2838`) — correct per-plane.
  - rolled/family: family `resolve_grid` meta `mouth_w_mm`/`mouth_h_mm` (`grid.py:3000-3002`) —
    the family's own per-plane geometry.
  - CAD: recipe `derived()` outer dims (`generated.py:99-104`, `:136-141`).
- Family dispatch at final HEAD `d187c06` includes `klangfilm_lame_hv_family` in `grid.py`
  (`:2893-2906`, `:2997-3002`), so klangfilm_hv goes through the family meta path, **not** the
  conservative generic branch. The working tree additionally adds `crowe_hv_area_aspect_v1` to the
  `generated.py` family tuple; its envelope route is untraced (new, in flight). Status: **directly
  verified for klangfilm_hv at HEAD; crowe_hv unverified**.

**Can I claim realised false refusals?** No. The code is conservative, but whether a given refused
candidate would have meshed inside the box is a measurement, not a corollary. I did **not** run a
CPU surface-vs-mesh comparison (see §7 for the exact check). Status: **plausible inference, not
verified**.

## 3. Historical refusal classification with correct denominators

From §A (FAILURE_AND_BOUNDARY_AUDIT) and the same parsed files. Denominators are explicit.

- **Recent window 2026-11-16** (`runs/20261116*`, 53 runs): 2,538 attempts → 2,288 `ok`
  (2,249 complete BEM + 39 cached), 81 pre-mesh `invalid_envelope`, 169 `invalid_geometry`
  of which **26 are post-mesh envelope** (width 21 / height 5, parsed) and 143 are other geometry.
  **0** `mesh_too_large`/`solve_failed`/`metrics_failed`/`exception`. Valid-geometry 90.15 %;
  complete-BEM 88.61 %.
- **QD run `20261112T110126Z-screen-c414b1`** (cma_me, `atlas__osse_ext_throat`, 300 mm brief):
  401 attempts → 281 `ok`; **120 envelope refusals, all `height > 300`**, all coded `invalid_geometry`.
  Height overshoot distribution (see `.tmp` measurement): 15 are ≤302 mm (≤0.7 % over),
  19 ≤305, 31 ≤310, **38 ≤315 (≤5 % over)**, 65 ≤330, median 329 mm, max 490 mm.
  → **~38/120 are near-miss oversize** (>0 but ≤5 %); the remainder are substantially oversized.
  This is the honest “otherwise geometrically plausible if the box moved ≤5 %” estimate; it makes
  **no acoustic-merit claim**.
- **Tritonia `20261116T044917Z-screen-12eb61`**: 74 attempts, 73 `ok`, exactly one refusal:
  `height 482 > 480.0 mm` (0.4 % over) — near-miss, single case.
- **Crowe-X CD `20261116T095336Z-screen-7fc9b7`**: 28 attempts, 19 `ok`, 9 pre-mesh
  `invalid_envelope` (32 % refusal; the refusal that triggered the watchdog).
- **Concave/old `salmon_saddle`** (7 runs, 202 attempts): 53 envelope + 46 `mesh_too_large`
  (old 5,000-dof cap) + 30 geometry + 14 exception. Mixed: oversize, DOF, area-law, and mesher
  self-approach — **not one boundary**.
- **`osse_baseline`** (9 runs, 3,925 attempts): 436 `mesh_too_large` at cap **5,000** and 21
  `solve_failed`. Under today's 24,000 cap this class is **not comparable**; the count is a
  historical resource-limit record, not a current refusal rate.

Distinguishing the classes (all with denominators above):
- **product oversize (brief)**: the envelope rows above (pre- and post-mesh).
- **flawed geometry**: `spherical_salmon` area-law, throat-shape failures, generator `reasons`.
- **throat mismatch**: `evaluate._refuse_if_throat_misfits` (`evaluate.py:343-359`), only when the
  round-throat gate is active (`:328-340`; v7 always, others opt-in).
- **DOF caps**: `mesh/build.py:250-257` pre/post; `:383-399` pre-mesh estimate vs `PREMESH_MARGIN`.
- **mesher bugs**: `exception: GeneratorError: grid self-approach …` before the S1b mapping
  (`evaluate.py:1567-1573`); now `invalid_geometry`.
- **transient worker**: `solve_failed` (`evaluate.py:1611-1614`), retried same-candidate only under
  `error_policy: retry_same_then_stop` (`cma_me.py:154-157`, `:499`).

## 4. BO eligibility audit, independent of size

- **Geometry adapter**: `materialize_geometry` resolves the canonical inner point grid without
  meshing (`bo/data.py:871-953`). It supports **only** native families and the versioned
  rolled-family recipe; **any other `grid`/`cad` design raises `UnsupportedGeometryError`**
  (`:908-910`). Therefore klangfilm/`osse_rollback`/rolled-rect grid rows are **not BO-encodable**
  — consistent with HANDOFF H7 (`docs/queue/HOME_18H_PLAN_2026-11-16.md:139-141`).
  Status: **directly verified**.
- **Active/discrete params & pool filter**: `build_candidate_pool` (`bo/data.py:1068-1164`) samples
  Sobol through `encoding.to_full`, calls `canonical_design` (`:1107`, which applies `links` +
  `_derive_throat_coupling`, `:861-868`), then filters: `_generator_error` → `schema_rejected`
  (`:1112-1114`); `families.validate` → `schema_rejected` (`:1115-1120`); `materialize_geometry`
  failure → `geometry_rejected` (`:1121-1125`); `geometry_checks` → `envelope_rejected` /
  `throat_rejected` (`:1126-1132`); duplicate/near-duplicate/known → dedup (`:1133-1144`).
  Note: a **pre-mesh envelope estimate** (a `_generator_error`) lands in `schema_rejected`, whereas
  a post-materialize `_envelope_ok` failure lands in `envelope_rejected` — two different counters
  for “size”. Status: **directly verified**.
- **Pool envelope is stricter on depth and looser on width/height than production**: `+0.5` on all
  axes, no `+15` depth allowance (`bo/data.py:1234`), and native descriptors use the **inner**
  surface (`:1210-1211`) so the shell offset is absent. A candidate can pass the pool but be
  refused post-mesh (depth), or pass post-mesh but be `envelope_rejected` in the pool (width/height
  near the limit). Status: **directly verified (code), no measured impact**.
- **Cohort eligibility is keyed by exact config name** (`tools/analysis/study_cohort.py:37`, cited
  by HANDOFF H2 `HOME_18H:126-129`), so a wider-bound v8 copy starts from zero BO rows even though
  every v7 row lies inside the v8 box. This is a **data-eligibility** limit, separate from size.
- **A refused geometry is never a measured acoustic datum**: refused rows have `ok:false` and no
  `metrics`; only `ok:true` rows train BO. So “wider bounds” enlarges the **pool** of *candidate*
  shapes and the **cohort** only by rows that actually solved. Refusals add no training data.
  Status: **directly verified** (evaluate `_persist`/row schema; `bo/data.py` training-set builder
  ingests `ok` observations).

## 5. Cost scaling with surface size (no new GPU work)

Historical measured numbers, treated as records, not fresh:
- `TOOLCHAIN.md:105`: dense operator is `8N²`; but the **footprint** is dominated by assembly
  intermediates/solve workspace, “20-40× the operator at 5k dofs”; measured ceiling on the 8 GB
  4060 ~5.5k–9.2k full-domain / 8.9k–15.7k quarter dofs.
- `TOOLCHAIN.md:126`: per-frequency cost (quarter, warm): **2,369 dofs 0.4 s; 5,140 2.8 s; 7,001
  7.5 s; 8,941 45 s** (memory pressure). `TOOLCHAIN.md:127`: ~**700 candidates/h at 2.4k** vs
  **~110/h at 5.1k**. So cost grows super-linearly well before the dense `8N²` operator alone would
  bite.
- `docs/status/2026-11-14/README.md:16`: cap raised **12k → 24k** at **5.8 GiB, zero spill** on the
  newer solver fork (`38e5b1f`). This **contradicts** the older `TOOLCHAIN.md:132` caps
  (5k/7k/8.9k); treat TOOLCHAIN as the 2026-10-12 measurement and the status brief as the later
  record. Status: **historical run record** for both; not re-measured here.
- Implication for size: a larger product envelope does not directly raise DOF, but it admits larger
  mouth area, which raises triangles at fixed `res_mm` (`sizing.py:40-46`, `94-101`); the measured
  curve above is the cost lever. The exact check for a proposed size is
  `sizing.f_max_for_dofs(dof_cap, area_m2, epw, quadrants, dof_per_triangle)` (`sizing.py:104-119`),
  not a new solve.

### 5b. Measured cost curve (historical records; no new GPU work)

| quarter-domain dofs | per-frequency wall (warm) | implied screen cost | source |
|---:|---:|---|---|
| 2,369 | **0.4 s** | ~700 candidates/h (12 freqs + balloon) | `TOOLCHAIN.md:126-127` |
| 5,140 | **2.8 s** | ~110 candidates/h | `TOOLCHAIN.md:126-127` |
| 7,001 | **7.5 s** | verify-like (25 freqs) ~3 min/candidate | `TOOLCHAIN.md:126`, `:130` |
| 8,941 | **45 s** | memory-pressure territory | `TOOLCHAIN.md:126` |
| cap 12k→24k | **5.8 GiB, zero spill** | newer solver fork `38e5b1f` | `docs/status/2026-11-14/README.md:16` |

The dense operator is `8N²` (`TOOLCHAIN.md:105`) but the *footprint* is 20–40× that at ~5k dofs
(assembly/workspace/pool), which is why the cost curve bends before the dense matrix would. The
current production cue is `sizing.f_max_for_dofs` (`sizing.py:104-119`) — use it to price a proposed
size, not a new solve. Status: **historical run record**.

### 5c. BO pool counter semantics (size-adjacent, no BEM)

| pool counter | trigger | path |
|---|---|---|
| `schema_rejected` | undecodable, `families.validate` fail, **or `_generator_error` (incl. pre-mesh envelope)** | `bo/data.py:1108-1120` |
| `geometry_rejected` | `materialize_geometry` unsupported/resolve failure (all `cad`, all non-rolled `grid`) | `:1121-1125`, `:908-910` |
| `envelope_rejected` | post-materialize `_envelope_ok` (0.5 mm all axes, no depth allowance) | `:1126-1129`, `:1219-1236` |
| `throat_rejected` | `_throat_ok` mismatch > max(0.5, 2 %·expected) | `:1130-1132`, `:1239-1247` |
| `geometry_duplicate`/`near_duplicate`/`known_duplicate` | dedup | `:1133-1144` |

Consequence: “how many candidates did size reject?” is **split** across `schema_rejected`
(pre-mesh estimate) and `envelope_rejected` (post-materialize), and it never includes a BEM datum —
`checks` records `bem_called: false` (`:1152-1153`). Status: **directly verified**.

## 6. The decision levers (the handoff's “Option A/B/C/D”)

The referenced handoff's literal “Option A/B/C/D” section is **not present in this checkout**
(searched `docs/**`, `examples/**`, `*.py` for a size-envelope option block; the Option A/B/C/D
docs found are about objective tolerances, CPU-lane topology, and queue planning, not the envelope).
Mapping to any external labels is therefore **UNKNOWN**. The four distinct levers the evidence
actually exposes are:

- **A — keep 600×480×480; fix the metres that are wrong, not the box.** Targets the conservative
  generic-grid estimate (`grid.py:3015-3020`), the envelope-as-geometry misclassification
  (`evaluate.py:1577-1581`), and the family-string mapping (`:1546`). No size change; no acoustic
  claim. Cheapest; does not recover genuinely oversized candidates.
- **B — widen the owner's product envelope.** Only justified by a measured surface-vs-mesh delta
  (§2) or a deliberate owner trade (e.g. allow the 38/120 ≤5 % near-misses). Changes the product,
  so it is an **owner** decision, not an optimizer one.
- **C — widen the search box only, keep the brief.** Reduces bound-pinning stops (watchdog
  `run_campaign_night.py:185-203`) but leaves envelope refusals untouched; effective only where the
  wall is the box, not the brief.
- **D — change the construction so the horn fits.** Per-plane section laws (R-OSSE / family meta),
  throat expansion, or `links`-style coupling — except `links` is blocked for generator configs
  (`links.py:36-37`), so D needs a generator-aware coupling first.

**The specific decision a later decision-maker would change** is whether to treat the
`600×480×480` brief as fixed product truth or as a negotiable search bound. That decision is
justified only by §2's CPU surface-vs-mesh measurement, which has not been run. If that measurement
shows the conservative estimate refuses shapes the mesher fits, the decision is A (fix the
estimator); if it shows the refusals are real oversize, the decision is an **owner** call between
B and D. Status: **proposed framing, no policy implemented, no solves run.**

## 7. The exact safety check (if a later lane is allowed to run it)

CPU-only, no BEM/GPU:
1. Sample N asymmetric generic-grid knob vectors spanning `r_h ≠ r_v` near the envelope.
2. For each: `grid.envelope_extents(spec, knobs, brief)` (pre-mesh) → `(w,h,d)`.
3. Mesh with `mesh/build.build_mesh` at a coarse `resolution_mm`, read `MeshResult.bbox_m`, and
   evaluate `evaluate.envelope_violation(mesh, brief)`.
4. Count `pre_mesh_refused AND post_mesh_admitted` = **false refusals**; report the small-axis
   overshoot ratio. This is the only safe way to convert the code-level conservatism into a
   realised-refusal number. Status: **not run; exact check specified.**

## Counterevidence / limits

- The recent window's complete-BEM rate (88.6 %) is high and its resource/fault count is zero, so
  the size/GPU story is not a live crisis on the 24k-cap home brief; the envelope story is.
- The 38/120 near-miss figure is an estimate of **geometric plausibility**, not acoustic merit; a
  horn that fits a wider box may still be a bad horn.
- The BO pool's mixed tolerance (strict depth, loose W/H) is code-verified but its realised effect
  on pool yield is unmeasured.
