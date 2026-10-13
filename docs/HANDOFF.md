# HANDOFF — Waves 0-2 complete, Wave 3 (senior physics checkpoints) next

Written 2026-10-13 ~06:00 EDT by the orchestrator (Claude). Supersedes all earlier handoffs.
Repo: https://github.com/llevaachingada/Hornfab (local: `C:\Users\hunte\Hrns\hornlab-search`, branch `main`, CI green on `b5bc811`).
The Python package and CLI are still named `hornlab_search` / `hornlab-search` (issue #11 asks Collin about the name).

## Read first, in this order
1. `docs/CONTINUITY.md` (newest entry on top: state, numbers, open issues, next action).
2. `CLAUDE.md` and `AGENTS.md` (rules; includes the **GPU / Julia hygiene** section, mandatory).
3. `TOOLCHAIN.md` (every measured number and the real solver API).
4. `NOTES_FOR_SENIOR.md` (append-only; the task 04-08 blocks hold every contract deviation awaiting a ruling).
5. `docs/plan/01_CONTRACTS.md` (frozen) and `docs/plan/09_CHECKPOINTS.md` (your task).

**Standing rule:** every push updates `docs/CONTINUITY.md` and `docs/ISSUES.md` in the same commit. **Check the real pytest exit code before committing** (a `| tail` once hid a failure).

## Where things stand
| Wave | Tasks | Status |
|---|---|---|
| 0 | 02 env, 03 scaffold | done, CP-0 and CP-1 green |
| 1 | 04 design+mesh, 05 solve, 06 metrics, 07 dataset | done, CP-2..CP-5 green (issues #1-#4 closed) |
| 2 | 08 pipeline | done, CP-6 green (issue #5 closed) |
| 3 | 09 senior checkpoints CP-7a..f | **not started** (issue #6, open) |

Tests: 479 pass locally (462 offline, rest need the GPU/bempp). CI runs the offline set on Python 3.12 and installs the pinned `hornlab-plots`.

## What to do next (in order)
1. **Wave 3 / issue #6.** Run `docs/plan/09_CHECKPOINTS.md` CP-7a..CP-7f as a verifier (writes no code, per the plan). Use a high-reasoning model; this is the physics gate. Inputs already gathered:
   - CP-7a analytic sphere: `selftest --analytic` PASS, R(ka) spread 0.020 dB (limit 0.5), sub 3/4/5 convergence 0.0204 / 0.0051 / 0.0013 dB.
   - CP-7b two solvers: beat vs bempp 0.039-0.055 dB on the same quarter mesh.
   - CP-7d symmetry: full vs quarter 0.031 dB (<= 3 kHz), 0.058 dB (<= 4 kHz); quarter without the flag is ~11 dB wrong on axis, 29.9 dB max.
   - **CP-7c (epw=6 mesh convergence on a real horn) is NOT measured**, nor is CP-7e (plausibility vs published horn behaviour) or the discretization input of CP-7f. The report's noise floor (0.055 dB, "limited by beat vs bempp") is therefore a lower bound.
2. **Senior rulings** (all in `NOTES_FOR_SENIOR.md`):
   - Task 08 item 1: the analytic test multiplies by omega because beat drives unit *acceleration* (TOOLCHAIN C5); confirm that reading.
   - Task 08 items 4, 5, 6c, 7: raw terms + 30.0 for unmeasurable terms; DI from the theta-phi balloon with sin(theta) weights; budget counts non-cached evaluations only; dataset choices.
   - Task 06: -6 dB threshold implemented as half pressure (-6.0206 dB); `di_from_cuts` clamp at 180 deg; ripple uses ddof=1.
   - Task 07: one `.npz` per record in `shard-NNNN/` (not the contract's single shard npz); `traces.sample_fraction` field added; `lib_shas` needs 5 entries.
   - Task 04: sectioned mesher config dict (the mesher silently ignores a top-level `max_triangles`); `config.mesh_spec` ignores `dof_per_triangle` while `sizing.max_triangles_for` uses it (2% apart; task 03 file, fix pending).
3. **User actions:** send questions #7-#11 to Collin (Robin BC in BEAT; surface_traces ordering; `build_point_grid` public API; excitation on tag 2; package name). Confirm or override the band-edge caps below.
4. After Wave 3: widen `a_deg` and `exponent` bounds (the best design sat at their lower bounds), run the other four example configs to get a multi-family dataset, then `docs/plan/11_PHASE2_SURROGATE.md` if wanted.

## Decisions made that the user may override
- **dof caps (quarter domain): screen 5,000 / verify 7,000 / final 8,900; full domain (freeform_hv) 3,000 / 4,500 / 5,400.** The plan's 8,000 / 16,000 / 24,000 do not hold on this 8 GB RTX 4060 Laptop.
- **`band_hi_hz` lowered per example** so every config meshes within its cap: osse_baseline 5500, throat_adapter 6500, icw_termination 7000, freeform_hv 5500, search_smoke 4500. Consequence: verify and final meshes equal the screen mesh (they differ only in frequency count and balloon size). A higher band needs a smaller seed horn or fewer elements per wavelength, not a higher cap.
- GPU is an RTX 4060 Laptop (plan said 4070); approved deviation.

## Measured facts you will need (full tables in `TOOLCHAIN.md`)
- Real solver API: `hornlab_beat_bem` 0.2.0 returns `SolveResult` (not the plan's `Response`); dofs = `mesh_info.n_vertices`; dof/triangle 0.500 full, ~0.51 quarter.
- **A multi-frequency `solve_frequencies` call thrashes above ~2.4k dofs** (689 s at 5.1k; 1,151 s with pipelining off); one call per frequency takes 2.8 s. The CUDA adapter loops per frequency.
- Per-frequency warm cost (quarter, CUDA): 2.4k dofs 0.4-0.8 s, 5.1k 2.8 s, 7.0k 7.5 s, 8.9k 45 s. OOM: full-domain 9.2k, quarter 15.7k. CPU backend is slower at every size (1.8x at 2.4k, 2.3x at 5.1k, 1.3x at 8.9k) but has no memory ceiling.
- Throughput: `search_smoke` 4.25 s/candidate (~847/h); the `osse_baseline` seed ~18 s. Cold start 17-29 s, warm 0.6-0.8 s.
- Impedance (Robin) BCs exist only in bempp (`impedance_sources`), not in beat. Traces: 111 kB/frequency at 2.4k dofs. Balloon: theta 0-180, phi 0-348.75, theta-major, not equal-area. Structured point grid: `hornlab_mesher.config_builder.build_point_grid` (not stable API).
- `HORNLAB_BEAT_FORCE_CPU=1` does not redirect an explicit `beat_backend="cuda"`.

## Environment and how to run things
- Interpreter: always `C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe`. Tests: `.venv\Scripts\python.exe -m pytest -q -m "not slow and not gpu and not crosscheck"` (add `-o addopts="" -v` for names). Check `$?`.
- CLI: `.venv\Scripts\hornlab-search.exe doctor | version | selftest --analytic | selftest --crosscheck | run --config ... --mode screen | search --config examples/search_smoke.yaml --budget 60 | verify | report runs\<dir> --out report.html | dataset stats|verify|export`.
- `gh` is at `C:\Program Files\GitHub CLI\gh.exe` (logged in as llevaachingada; add it to PATH in bash). `runs/`, `cache/`, `dataset/`, `scratch/`, `report.html` are gitignored; `dataset/` is precious (back it up).
- **Hygiene (from AGENTS.md):** one GPU job at a time; `taskkill /F /IM julia.exe` and confirm VRAM ~0.15-0.45 GB before and after any solver run; `shutdown_workers()` does not reliably end the Julia host (a `hornlab_beat_bem.worker_host` Python process also lingers: kill it by command-line match on `python.exe`, never with a filter that matches your own shell). Do not run provisioning while measuring. Never leave a host running.
- Two agent sessions once collided on the GPU and the repo; keep to one orchestrator.

## Known loose ends
- The report HTML was never viewed in a browser (the pane refused `file://`); rendering is unchecked.
- `timeout_s` is checked between frequencies only; bempp makes one call.
- beat uses dense LU: `gmres_tol` is recorded as requested, not applied.
- Task 07's test `test_append_500_typical_records_is_fast` (5 s limit) passes in 1.4-1.7 s but can flake under heavy disk load; do not loosen it, investigate if it fails.
- `hornlab_search.egg-info/` and `.opencode/` are gitignored local artifacts.
- The mesher's `resolve_geometry` (used by task 04's pre-mesh estimate) is not stable API; the mesher is pinned at b922e80.
