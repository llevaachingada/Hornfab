# Solver speed and fidelity: implementation plan (2026-11-13, rev 2, senior-reviewed)

**Status:** ready to execute. Rev 2 checks the plan against the current code at `a783b88`: exact functions,
corrected targets, and one package (replay) dropped because the code already does it.
**Sources (detail, evidence, rationale):** [HANDOFF_LOCAL_AGENT_IMPLEMENTATION_2026-11-13.md](HANDOFF_LOCAL_AGENT_IMPLEMENTATION_2026-11-13.md) ("LA")
and [HANDOFF_HUYGENS_SOLVER_SPEED_2026-11-13.md](HANDOFF_HUYGENS_SOLVER_SPEED_2026-11-13.md) ("HY").
This file is the one to follow. Read a source handoff only when a package below points you to a section of it.

**Goal:** more verified acoustic results per wall-clock hour at the same physics. Out of scope here: new score
versions, new optimizers, new UI controls.

---

## 0. Senior review: what changed from rev 1 (and why)

| Rev 1 said | Code says (checked) | Rev 2 decision |
|---|---|---|
| A1: compare SHAs on cache lookup | `solve/cache.py::store()` writes to `<root>/<key>/`, the same directory for a given key. A new-pin entry would **overwrite** the legacy entry. Comparing on lookup alone breaks "keep old data intact". | Use **namespaced cache roots** instead: `<cache_dir>/solve/<ns>/<key>` with `ns` built from the library SHAs. Legacy entries stay byte-for-byte where they are. The diff stays small: two `EvalContext` properties plus one helper. |
| A1: key on "solver and mesher SHA" | `collect_lib_shas()` also returns `hornlab_search` (this repo's HEAD), which changes on every commit. | `hornlab_search` and `hornlab_plots` are **excluded** from the namespace; otherwise every commit would empty the cache. |
| A1: failure markers need the guard too | `evaluate.py` already checks `rec["lib_shas"] == ctx.lib_shas` on failure markers. | No change needed. |
| A6: replay silently mis-scores v5-v7 | `objective/replay.py` already refuses v5+ with `R_REPLAY_VERSION_UNSUPPORTED` ("dispatches only objective versions 1-4"). | **A6 dropped.** The concern is already covered. |
| A2: seam fix is blocked by A1 because both edit `evaluate.py` | A1 edits `EvalContext` (~line 200); A2 edits `_seam_check` / `_compute_band_split` (~lines 800-1240). The regions don't overlap. | A1 and A2 run **in parallel**. The integrator merges A1 first. |
| A5: a new estimator from scratch | `cli.py::estimate_seconds_per_frequency` and `mesh/sizing.py::estimate_dofs` already exist. | A5 adds memory only, reuses `estimate_dofs`, and is calibrated on measured evidence (see A5). |
| Orchestrator 2 can run in the cloud | The BEAT fork and mesher live on the owner's Windows machine (`C:\Users\hunte\Hrns\forks\`); C1 needs the installed mesher + gmsh. | Orchestrator 2 runs **on the owner's machine** (or adds the fork repo for A3 code only). |
| GPU Wave B can start now | Night `home80x60_day_2026-11-13` holds the GPU until 23:30. | Wave B starts after that night ends, through the night queue. |

---

## 1. Rules for every agent (short, binding)

1. Edit **only** the files in your package row, plus the new test file named there. If you need another file, stop
   and append the request to `NOTES_FOR_SENIOR.md`.
2. Only the integrator runs git (`AGENTS.md` amendment of 2026-11-12). Agents edit files and report back.
3. Wave A uses no GPU: no `gpu-clean`, no killing hosts, no queue edits, no solves. Offline `pytest` only.
4. Never move, rewrite or delete an existing cache entry, run dir or dataset row.
5. Never edit `.venv` or `.julia`. Fork changes go through `docs/FORKS.md`.
6. Interpreter: `.venv\Scripts\python.exe` (Windows) or the repo venv. Run only the tests for your package plus
   `tests/test_solve_cache.py tests/test_search_evaluate.py` as the regression check.
7. Report back in this form: files changed, tests run with the pass/fail count line, anything you could not do and why.

---

## 2. Wave A: offline code, parallel, start now

### Orchestrator 1: HornFab Python (cloud or local)

Spawn **A1, A2, A4, A5 at the same time**, one subagent each. Integrator merge order: **A1 → A2 → A4 → A5**,
then one commit that wires A5 into `evaluate.py` (step A5.4).

---

#### A1. Cache provenance namespaces (blocker for any fork pin change)

**Files:** `hornlab_search/solve/cache.py`, `hornlab_search/search/evaluate.py` (only the `EvalContext` class
properties `solve_cache_root` / `mesh_cache_root`), `hornlab_search/dataset/identity_v2.py`,
new `tests/test_solve_cache_namespace.py`.

**Steps:**

1. In `solve/cache.py` add:
   ```python
   CACHE_SCHEMA = 2
   #: libraries whose code changes physics; hornlab_search/hornlab_plots excluded on purpose
   PHYSICS_LIBS = {"solve": ("hornlab_beat_bem", "hornlab_bempp_bem", "hornlab_mesher"),
                   "mesh": ("hornlab_mesher",)}

   def namespace(lib_shas: dict, kind: str) -> str | None:
       """'p<schema>-<sha12>' for this set of physics library SHAs, or None when any of
       them is missing/'unknown' (then the caller must not use a shared cache)."""
   ```
   `sha12` = first 12 hex chars of sha256 over the canonical JSON of `{"schema": CACHE_SCHEMA, "kind": kind,
   lib: lib_shas[lib] for lib in PHYSICS_LIBS[kind]}`. If any of those values is missing or `"unknown"`, return `None`.
   Also add the gmsh version to the `"mesh"` and `"solve"` dicts if `gmsh.__version__` imports cleanly; leave it out
   silently if it doesn't import (never raise).
2. In `search/evaluate.py` `EvalContext`, change only the two properties:
   - `solve_cache_root` → `Path(cache_dir)/"solve"/ns` where `ns = solve_cache.namespace(self.lib_shas, "solve")`.
     Return `None` when `cache_dir` is None **or** `ns` is None, and log one warning per process:
     `"shared solve cache disabled: physics library SHA unknown"`.
   - `mesh_cache_root` → same pattern with `kind="mesh"` under `Path(cache_dir)/"mesh"/ns`.
   Do not touch anything else in `evaluate.py`. Every lookup path (single mesh, band split, seam, MEH) already
   reads these two properties, so all of them are covered.
3. In `solve/cache.py::store()`, add `"cache_schema": CACHE_SCHEMA` to the status dict through `st.setdefault`, so new
   entries say what they are. Do not change `lookup()`, `key()` or the file layout inside an entry.
4. In `dataset/identity_v2.py` add:
   ```python
   def implementation_solve_id(physical_id: str, solve_ns: str | None) -> str:
       """physical_solve_id qualified by the physics-library namespace. physical_solve_id stays the join key."""
       return sha16([physical_id, solve_ns])
   ```
   Wire it nowhere else in this package.
5. Run `grep -rn "solve_cache\.\(lookup\|store\)\|cache_dir=" hornlab_search tools`. Callers that use `ctx.*_cache_root`
   are already covered. List every caller that builds its own root (expected: `compare/hornfab_side.py`,
   `compare/fake.py`, `tools/m3_measurement_pack.py`) in your report, **without editing them**. The integrator files
   these in NOTES_FOR_SENIOR as follow-up A1b.

**Tests (`tests/test_solve_cache_namespace.py`, 4 tests):**
- same `lib_shas` → same namespace, and a store-then-lookup through `ctx.solve_cache_root` hits;
- changing only `hornlab_beat_bem` (or only `hornlab_mesher`) → different namespace → miss;
- changing only `hornlab_search` → **same** namespace (still hits);
- a legacy entry at `<cache>/solve/<key>/` keeps byte-identical files (sha256 before and after) through a
  store under the new namespace, and `"unknown"` in a physics lib → `solve_cache_root is None`.

**Done when:** the 4 new tests pass and `tests/test_solve_cache.py tests/test_search_evaluate.py` still pass.
**Known cost (accepted):** the first run after A1 re-solves designs that already have cached solves; old entries stay
on disk for analysis tools (`load_response` still reads them).

---

#### A2. Band-split seam check at a valid frequency

**Files:** `hornlab_search/search/evaluate.py`: only `_first_above`, `_seam_check`, and the `_seam_check` call
inside `_compute_band_split`. New `tests/test_search_band_seam.py`.

**What is wrong now:** `_seam_check` solves the first frequency **above** each edge on the **lower** band's mesh,
which is beyond that mesh's rated top. Its result is diagnostic only.

**Steps:**

1. Change the probe: for edge `i`, `f = max(bands[i])`, the last frequency of the lower band, which is at or below
   that band's rated top. Pass `bands` into `_seam_check` from `_compute_band_split`, which already has it. Delete
   `_first_above` if nothing else uses it (check with grep).
2. Solve `f` on the **upper** band's mesh: `meshes[i+1]`, cache key from `mesh_specs[i+1].hash()`. Compare it to
   `merged` at index `resp_freqs.index(f)`, which came from the lower mesh. Keep the existing on-axis and H/V
   beamwidth deltas.
3. Add module constants `SEAM_MAX_AXIS_DB = 0.5` and `SEAM_MAX_BW_DEG = 2.0`. These are provisional and come from
   LA §4. Per edge, record `"pass": abs(axis) <= ... and abs(bw_h) <= ... and abs(bw_v) <= ...`. A probe solve
   that fails records `"pass": False` with the error.
4. In `_compute_band_split`, after the seam check, set `merged.meta["seam_ok"] = all(e["pass"] for e in seam.values())`
   and also `merged.meta["band_meshes"] = [{"mesh_hash": ms.hash(), "n_dof": r.n_dof} for ms, r in zip(mesh_specs, responses)]`.
   If `seam_ok` is False in verify mode, log a warning with the edge and deltas. Do **not** fail the candidate:
   enforcement is a reporting decision for G5.

**Tests (fake backend, 3 tests):** the probe frequency is `<=` the lower band's top for every edge; the probe is solved
on the upper mesh (assert on the fake backend's received mesh); a large fake delta gives `seam_ok False`.
Model the setup on the existing band-split tests in `tests/test_search_evaluate.py`.

**Done when:** the 3 tests pass and `tests/test_search_evaluate.py` still passes.

---

#### A4. Mesh fidelity report tool (read-only)

**Files:** new `tools/analysis/mesh_fidelity.py`, new `tests/test_tools_analysis_mesh_fidelity.py`.

**Steps:**

1. CLI: `mesh_fidelity.py <mesh.msh or design dir> [--fmax HZ] [--epw 6] [--out json]`. Parse the `.msh` with
   `meshio`, or with the small `$PhysicalNames` parser pattern already in `mesh/build.py` (~line 94). Import it; do not copy it.
2. Per **physical tag**: triangle count, edge length p50/p95/max (mm), and `k*h_max` at `--fmax` (`k = 2*pi*f/343`).
   Name the region from `$PhysicalNames` when present, otherwise `"tag_<n>"`. Do **not** guess regions from geometry.
3. `mesh_fidelity_status`, one of:
   `source_valid_only` | `global_max_edge_valid` | `not_assessed`. "Valid" means `h_max <= c/(epw*fmax)`.
   The source tag passes and some wall fails → `source_valid_only`; every tag passes → `global_max_edge_valid`;
   no `--fmax` → `not_assessed`. CAD-checked and converged-vs-reference are added later (G4/G5); define them as
   names in the enum but never emit them.
4. Read `mesh_meta.json` beside the mesh if it exists (requested res, `rear_res_factor`) and echo it. Write nothing next to the mesh.

**Tests (2):** a tiny hand-written `.msh` fixture (2 tags, known edges) → correct p95/max and status; no `--fmax` → `not_assessed`.
**Done when:** both pass. Add one line to `docs/CODE_MAP.md` under tools/analysis (integrator commits it).

---

#### A5. Dense-memory feasibility preflight

**Files:** new `hornlab_search/solve/feasibility.py`, new `tests/test_solve_feasibility.py`.
Step A5.4 (wiring) is done by the integrator after A2 merges.

**Steps:**

1. `dense_bytes_lower_bound(n_dof, dtype_bytes=8) -> int` returns `dtype_bytes * n_dof**2` (one complex64 N×N).
2. `assess(n_dof, backend, *, cuda_fused, vram_gib=8.0, vram_baseline_gib=1.5, ram_gib=32.0, ram_reserve_gib=8.0) -> dict`
   returns `{"verdict": "fit"|"risky"|"refuse", "need_gib": ..., "budget_gib": ..., "reason": str, "basis": "calibrated"|"provisional"}`.
   - Fused CUDA: `need = 4.0 * dense_bytes_lower_bound(n)`. The factor 4 is calibrated from
     `docs/evidence/FUSED_CUDA_2026-10-24.md`: 12,183 DOF measured ~4.7 GB incremental; 15,984 DOF hit the
     pressure cliff. Budget = `vram_gib - vram_baseline_gib`. `fit` if need <= 0.8·budget, `risky` if <= budget,
     else `refuse`. `basis="calibrated"`.
   - CPU backends: `need = 3.0 * 16 * n**2` (complex128, LU in place plus workspace), budget = `ram_gib - ram_reserve_gib`,
     same thresholds, `basis="provisional"`.
   - Non-fused CUDA: same as fused but factor 6.0, `basis="provisional"`.
   - All constants are module-level and named, so G2 can recalibrate them in one place.
3. Pure function; no imports from `solve/beat.py` or anything that loads Julia.
4. **(Integrator, after A2 merges)** In `evaluate.py`, right after `build_mesh` on the single-mesh path and per
   band in `_compute_band_split`, record `st["feasibility"] = feasibility.assess(...)` into the record meta.
   **Warning only, never a refusal** in this wave.

**Tests (3):** 12,183 DOF fused → `fit` or `risky` (not refuse); 20,237 fused → `refuse` (it failed in the evidence);
34,000 CPU → `refuse` with need ≈ 3×16×34000² bytes (≈ 51.7 GiB, more than 24 GiB).
**Done when:** the 3 tests pass.

---

### Orchestrator 2: owner's machine (fork + mesher present)

#### A3. BEAT fork: skip the unused fused-CUDA identity cache

**Where:** `C:\Users\hunte\Hrns\forks\hornlab-beat-bem`, a new branch `perf/skip-fused-identity-cache` from the pinned SHA
`0850ef39...` (confirm it with `TOOLCHAIN.md` / `pyproject.toml` first).

**Steps:**

1. In `hornlab_beat_bem/julia/BeatEngineDriver.jl`, find every read of `cuda_solve_identity_cache`
   (`grep -n cuda_solve_identity_cache` across `julia/`). Write the list in your report. The handoff says the only
   build is ~lines 1631-1667 and the only read is in the non-fused route ~line 2049. **If you find another reader
   on the fused path, stop and report it. Do not patch.**
2. Confirm the fused flag is final before line ~1631, meaning nothing later can flip a run into the non-fused path.
3. Wrap the build in `if !<fused flag>` and leave the cache variable as `nothing` otherwise. Make the release at
   ~`BeatEngineCore.jl:2251` tolerate `nothing`. **That is the entire diff.**
4. Run the fork's CPU-runnable tests / analytic selftest (see `docs/FORKS.md` ladder, CPU rungs only). No GPU.
5. Commit on the fork branch and report the new SHA. **Do not change HornFab's pin.** That happens in G2.

**Done when:** the fork SHA exists, the diff covers only steps 3's lines, and the CPU tests pass.
Use the patch text in `docs/throughput/WP1_FUSED_IDENTITY_CACHE_PATCH.md` as a draft; verify every line against the source.

#### C1. Rear-shell density mesh audit (CPU, mesh only)

**Needs:** A4's tool (use the draft if it hasn't merged yet).

1. Pick 4 seed designs from existing configs: one modest OSSE, one R-OSSE, one ATH-like, and the T2 large horn
   (skip T2 if the mesh build takes more than 10 min). Copy their configs to `examples/studies/rear_density_2026-11-13/`
   with `mesh.rear_res_factor` set to 1.0, 1.5, 2.0 and 2.5 (16 configs). Change nothing else.
2. Mesh each one with the existing mesh-only path (`tools/bench/mesh_policy_study.py --help` first, or
   `hornlab-search run --dry-run`, whichever builds the mesh without solving). Use a scratch cache dir.
3. Run `mesh_fidelity.py` on each. Write one table to `docs/evidence/REAR_DENSITY_MESH_AUDIT_2026-11-13.md`:
   design, factor, total DOF, rear-tag triangles, rear h_max, and DOF saved vs 1.0. Use the `hornlab-evidence` skill rules for labels.
4. Recommend 1-2 factors for G4: the largest saving on the horns where the outer-wall clearance guard did not
   cancel the reduction.

**Done when:** the table exists with measured numbers and a one-line recommendation.

---

## 3. Wave B: GPU, one job at a time, through the night queue

**Starts:** after night `home80x60_day_2026-11-13` ends (23:30). Every job follows the `hornlab-gpu-job` skill
(hygiene, VRAM baseline, Windows **shared** GPU memory recorded, verified shutdown). Results go in
`docs/evidence/` per `hornlab-evidence`. Don't duplicate jobs already in `docs/research/QUEUE_PLAN_REV2_2026-11-13.md`.
A job whose shared-memory spill is above zero is invalid; rerun it smaller.

| # | ID | Needs | Job | Adopt if | If not |
|---|---|---|---|---|---|
| 1 | **G1** batching | nothing | `HORNLAB_FREQ_BATCH_SIZE` = 1, 4, 12 on 3 frozen designs (~1k / ~4k / ~8k DOF) × a 12-freq and a 25-freq grid, `tools/bench/throughput_matrix.py` (check `--help`). Record whole-candidate wall. | The whole-candidate wall improves at least 1.2× with identical outputs (on-axis complex pressure within 0.05 dB) and zero spill. Set the env var in the night runner for that job class. | Keep batch 1; write up the negative result. |
| 2 | **G2** fork A/B | A1 merged, A3 SHA | The old pin vs the A3 SHA on the same mesh at ~4k, ~8k and ~12k DOF, fresh process each, cold + 2 warm. Record dedicated + shared peak, wall, and analytic selftest. | Peak VRAM drops, or a larger DOF now fits, with parity inside the `docs/FORKS.md` tolerances. Then bump the pin in one commit (rollback = old SHA) and recalibrate A5's factor. | Leave the pin; document the negative result. |
| 3 | **G3** screen fidelity | nothing (uses cached finalists) | 2×2 on 8 diverse cached finalists: (screen mesh, verify mesh) × (screen grid, dense grid), same scorer. Use `tools/calibration/plan_calibration.py` + `compare_calibration.py`. Report Spearman + top-5 recall per cell. | The cell that best restores ranking at the lowest cost becomes the new screen proposal (owner decides). | Verify 15-20 diverse finalists instead of the top 5 until fixed. |
| 4 | **G4** rear density | C1 | The C1 factor(s) vs 1.0 vs a finer reference on 2 horns: H/V/diagonal polars + throat impedance. | Beamwidth within 2°, DI within 0.2 dB, ReZ within 0.03 (normalized) at every frequency, and wall time saved. Then make the factor a per-config default in the examples (not a global code default). | Keep 1.0. |
| 5 | **G5** band split | A2 merged | 1 vs 2 vs 3 bands on 2 designs, same frequency list, verify mode, plus A2's `seam_ok`. | Whole-candidate wall improves, `seam_ok` is true, and the response matches the single-mesh run within G4's tolerances. | Keep a single mesh. |

G1 and G3 need no new code. Run them first, the first night the GPU is free.

---

## 4. Wave C: only after its trigger

| ID | Build | Trigger |
|---|---|---|
| **D1** | `solve.quadrature_order` (CUDA regular integration, 4 vs 2), part of `SolveSpec.extra` so the solve hash changes. | G2 done and assembly is still above 50% of solve time. |
| **D2** | `verify --freq-range LO:HI` reusing `evaluate.py`, its own record identity, backend chosen by A5's verdict. First 8-12 kHz on 3-5 finalists. | A2, A5 merged; G5 done. |
| **D3** | Keep per-band boundary traces for a few finalists; offline re-evaluation of the field at new angles/distances. | D2 running. |

---

## 5. Deferred (logged in NOTES_FOR_SENIOR.md, not scheduled)

A1b (route `compare/` and `tools/m3_measurement_pack.py` cache roots through `namespace()`), an opt-in legacy-cache
adopt tool (only if the owner confirms that pins didn't change for a date range), dense GMRES, assembly/solve
pipelining, persistent GPU context, direct-device field path, smoothing, adjoint/adaptive BEM, BEMAO/curved elements,
FMM/NumCalc/Bempp OSRC spike, axisymmetric solver, reduced-order sweeps, half-space baffle formulation, Huygens/Mac
head-to-head, geometric rear simplification, `curvature_npts` as a DOF saver, UI fidelity selector.

---

## 6. Launch prompts (paste as is)

**Orchestrator 1 (HornFab Python):**
> Execute Wave A, Orchestrator 1, of `docs/throughput/SOLVER_SPEED_IMPLEMENTATION_PLAN_2026-11-13.md` (rev 2).
> Read §1 rules. Spawn four subagents in parallel, one each for A1, A2, A4 and A5, and give each its package
> section verbatim plus §1. You are the only git writer. Merge in the order A1, A2, A4, A5, then do step A5.4 yourself.
> Each commit updates `docs/CONTINUITY.md` and `docs/ISSUES.md` (and `docs/CODE_MAP.md` for new modules). Offline tests
> only, no GPU. Report the per-package pass/fail against its "Done when", with the pytest count line.

**Orchestrator 2 (owner's machine):**
> Execute Wave A, Orchestrator 2, of `docs/throughput/SOLVER_SPEED_IMPLEMENTATION_PLAN_2026-11-13.md` (rev 2).
> Read §1 rules. Spawn two subagents: A3 (BEAT fork only; do not change HornFab's pin) and C1 (CPU mesh only,
> start once A4's tool exists or use its draft). No GPU and no queue edits. Report the fork SHA and exact diff,
> and the C1 evidence table and recommendation.

**Wave B (after the night ends):**
> Using the `hornlab-night-queue` and `hornlab-gpu-job` skills, queue G1 then G3 from §3 of
> `docs/throughput/SOLVER_SPEED_IMPLEMENTATION_PLAN_2026-11-13.md`. Queue G2, G4 and G5 only when their "Needs"
> column is met. Write each result to `docs/evidence/` with the adopt/not decision from the table.
