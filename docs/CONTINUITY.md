# CONTINUITY

Newest entry first. Every push updates this file and `docs/ISSUES.md` in the same commit.

## Status
- **Wave:** 0 and 1 complete (04, 05, 06, 07 done, CP-2..CP-5 green). Wave 2 (task 08) next.
- **Last checkpoints:** CP-1 GREEN (pytest, `doctor`, `version`). CP-0 COMPLETE (all measurements clean). CP-2 (task 04) GREEN. CP-4 (task 06) GREEN: 78 passed.
- **Next action:** see the newest entry below.
- **Blockers:** none for task 08. Open decisions: senior review of 06/07 conventions; questions #7-#11 for Collin.

## 2026-10-13 (01:10) — GitHub live (orchestrator: Claude)

- `gh` authenticated (account llevaachingada). Repo: https://github.com/llevaachingada/Hornfab. Labels created (wave-1, wave-2, senior-review, phase-2, blocked, question).
- Issues created: #1-#4 (tasks 04-07, closed with CP results), #5 (task 08, open, in progress), #6 (task 09, blocked by #5), #7-#11 (questions for Collin). Mirror in `docs/ISSUES.md`.
- CI: green on the latest commit (0a96c58). Two earlier red runs were my broken commits (missing `hornlab_search/dataset` because of an unanchored `.gitignore`; a test tied to the old frequency grid), both fixed. Lesson: always check the pytest exit code before committing (a `| tail` hid a failure once).
- Task 08 dispatched with exclusive GPU use; no solver jobs run by the orchestrator meanwhile.

**Next action:** when task 08 reports, commit it, run/verify CP-6 numbers, then hand CP-7a-f (issue #6) to the senior verifier. Questions #7-#11 are for the user to send to Collin.

## 2026-10-13 (01:00) — task 05 done, example bands capped (orchestrator: Claude)

**Done**
- Task 05 (solve) DONE, CP-3 green. 86 offline + 28 worker tests; slow (10), crosscheck (2) and trace (5) tests pass on the RTX 4060. Backends: `beat_cuda` (loops ONE frequency per `solve_frequencies` call because of the multi-frequency cliff), `beat_cpu` (single multi-frequency call; no cliff seen at 4.5k dofs), `bempp_cpu` (gated; Burton-Miller is refused with native symmetry, so it runs STANDARD formulation). Worker hygiene (stale Julia host detection/clear, verified release, SIGINT/atexit) implemented and tested in `solve/worker.py`.
- Numbers: cold 17.6 s / warm 0.80 s / post-detach 0.63 s; full vs quarter 0.031 dB (<= 3 kHz); beat vs bempp <= 0.055 dB; boundary-trace recovery 8e-5 dB; idempotence 3.6e-5 dB; mismatch (quarter without flag) 29.9 dB max, ~11 dB on axis; asymmetry sign check 100%.
- Resolved the "seed horn too large for the cap" decision (flagged by 04 and 05): all five `examples/*.yaml` failed at screen resolution (seed horn 0.80 x 0.64 x 0.27 m). Set `band_hi_hz` per config from the measured caps: osse_baseline 5500, throat_adapter 6500, icw_termination 7000, freeform_hv 5500, search_smoke 4500. All 15 config x mode combinations now build (2.5k-3.8k est. dofs). **User may override**: raising a band edge requires a smaller seed or fewer elements per wavelength, not a higher cap.
  Consequence: verify/final grids are also clipped to band_hi, so verify and final meshes equal the screen mesh; they differ only in frequency count and balloon size until a larger cap or a smaller seed is chosen.
- Fixed `.gitignore`: `dataset/` ignored the source package; anchored to `/dataset/` (commit d70ba06).

**Open issues**
1. Task 08 must call `solve.worker.install_handlers()` and `worker.warm(backend)` from the CLI.
2. Balloon is a theta-phi grid: DI needs `weights=sin_theta_weights(...)` (grid shape in `Response.meta['balloon_grid']`); not equal-area.
3. `timeout_s` is checked between frequencies only (CPU makes one call).
4. beat uses direct dense LU; `gmres_tol` recorded as requested, not applied.
5. The `gh`-gated GitHub labels/issues are still not created.
6. Senior-review items: tasks 04, 05, 06, 07 `NOTES_FOR_SENIOR.md` blocks.

**Next action:** dispatch task 08 (pipeline) with the verbatim template; then CP-6/7 live runs (`selftest`, `run`, `search`) one GPU job at a time.

## 2026-10-13 (00:25) — task 07 done (orchestrator: Claude)

**Done**
- Task 07 (dataset) DONE: 64 tests pass (CP-5). Files: `dataset/record.py` (415), `dataset/store.py` (694), 3 test files. Layout: one uncompressed `.npz` per record in `shard-NNNN/` + `shard-NNNN.jsonl` + `index.jsonl` (deviates from contract section 13's single `shard-NNNN.npz`; the phase-2 loader must go through `DatasetStore`). Crash recovery tested (torn index line, torn shard line, uncommitted row).
- Disk projection for 10,000 screen records: 0.78 GB without traces, 1.40 GB with traces at 1 in 20.
- Contract gaps to rule on (NOTES_FOR_SENIOR): added `traces.sample_fraction`; `lib_shas` requires 5 entries; NaN written as JSON null.
- Test `test_append_500_typical_records_is_fast` (5 s limit) measured 1.4-1.7 s on a quiet disk but failed at 6-9 s when the disk was loaded. Not loosened; may flake under load (recorded).
- Wiring for task 08: pass `solve_spec=`, `area_m2=`, `grid=` to `build_record`; catch `ValueError` from `append`; call `reset_warning_state()` at startup; subcommand hooks `stats_report`, `verify_store`, `export_training_npz`.

**Next action:** task 05 (solve) running; when it lands, dispatch task 08 (pipeline) using the verbatim template.

## 2026-10-13 (00:15) — task 04 done, caps set, CPU provisioned (orchestrator: Claude)

**Done**
- Task 04 (design + mesh) DONE: 87 offline tests + 27 mesher-gated tests pass (CP-2). Files: `design/{families,space,custom}.py`, `mesh/{sizing,build}.py` + 4 test files. Contract deviations (all in NOTES_FOR_SENIOR): `to_mesher_config` returns a *sectioned* dict (the mesher silently ignores a top-level `max_triangles`); pre-mesh dof estimate added so over-cap designs are refused in <100 ms; new exceptions `MeshConsistencyError/MeshUnitsError/SymmetryMismatchError` that task 08 must not swallow.
- I edited one task-04 test (`test_over_cap_but_inside_mesher_slack_is_caught_after_meshing`) so it reads the screen cap from the config instead of the hard-coded plan value 8000; same intent, no tolerance loosened.
- **dof caps replaced** (quarter domain): screen 5,000 / verify 7,000 / final 8,900; full-domain (`freeform_hv`) 3,000 / 4,500 / 5,400. Basis: per-frequency cost 0.4 s @2.4k, 2.8 s @5.1k, 7.5 s @7.0k, 45 s @8.9k; 15.7k quarter and 9.2k full OOM.
- **Finding for task 05**: one multi-frequency `solve_frequencies` call falls off a cliff above ~2.4k dofs (689 s at 5.1k; 1,151 s with pipelining off) while 12 separate single-frequency calls take 33 s. The CUDA adapter must loop one frequency per call.
- M4 done: cuda 0.8 s vs cpu 1.45 s per frequency at 2.4k dofs; CPU cold start 3.7 s vs CUDA 29 s. `HORNLAB_BEAT_FORCE_CPU` does not redirect an explicit cuda request.
- First push done: https://github.com/llevaachingada/Hornfab (commit ef30d36).

**Open issues**
1. **Decision needed (task 04 finding):** the baseline seed horn is large (quarter area 0.282 m^2, bbox 0.40 x 0.32 x 0.26 m, vs the plan's 0.125 m^2 assumption). With a 5,000-dof cap, `screen` at f_max 10 kHz is refused (`MeshTooLargeError`); 5,000 quarter dofs buys roughly 6 kHz for this horn. Options: lower `band_hi_hz`/screen grid top, use fewer elements per wavelength in screen (epw 4), or a smaller seed. Not decided; `osse_baseline.yaml` unchanged beyond caps.
2. `config.mesh_spec` uses `ceil(2*cap*qf*slack)` and ignores `dof_per_triangle`, while `sizing.max_triangles_for` uses it (2% apart at 0.51). Task 03 file; fix pending.
4. Task 06 conventions awaiting senior review (half-pressure -6 dB threshold; `di_from_cuts` clamp; ddof=1 ripple).
6. Mesh time: 0.3 s -> 12 s over the f_max range for the baseline horn (task 04 table); mesh fraction of a screening candidate is small versus solve above 5k dofs.

**Next action:** collect task 07; dispatch task 05 (solve) now that the GPU is free of measurements; then task 08 once 04-07 are in.

## 2026-10-12 (night) — clean GPU measurements, Wave 1 started (orchestrator: Claude)

**Done**
- Single session now (a duplicate session had collided on the GPU; it stood down). Added "GPU / Julia hygiene" rules to `AGENTS.md` and `CLAUDE.md` after finding that stale persistent Julia hosts (~1 GB VRAM each) cause false OOMs and worker crashes.
- Clean-state M2/M3/M5/M6 and C1/C2b/C3/C4/C5 measured; `TOOLCHAIN.md` rewritten (see it for every table).
- Remote set: `origin` = https://github.com/llevaachingada/hornfab.git (package/CLI keep the names `hornlab_search` / `hornlab-search`).
- Per user instruction (23:47), Wave 1 started in parallel with the last GPU measurements. Interpretation: "task one" = Wave 1 task 04 and onward. CP-0 gate waived in part: M4 (cpu) and the dof caps are still being settled; recorded as a deviation.
- Task 06 (metrics + targets): DONE, 78 tests pass, CP-4 analytic tables in agent report. Decisions needing senior review (also in `NOTES_FOR_SENIOR.md`): -6 dB threshold implemented as half pressure (-6.0206 dB); `di_from_cuts` clamps sin(bw/2) at 1 and treats saturated cuts as omni; `ripple_db` uses ddof=1.
- Tasks 04 (design+mesh) and 07 (dataset) dispatched; 05 (solve) waits for the GPU job to finish.

**Key measured numbers**
- dof/triangle 0.500 full, ~0.51 quarter.
- Symmetry pairing (clean): full vs quarter max 0.058 dB up to 4 kHz, 0.497 dB at 6 kHz; mismatched run is 12 dB wrong on axis, 54.9 dB max.
- VRAM: operator is dense 8N^2 but the real footprint is 20-40x that. Clean OOM ceilings on the 8 GB RTX 4060 Laptop: full domain 5.5k ok / 9.2k OOM; quarter 8.9k ok (74 s) / 15.7k OOM. **The plan's dof caps (8000/16000/24000) do not hold.**
- Throughput (warm worker, quarter): 2,369 dofs, 12 frequencies + 512-point balloon = **5.0 s**; 5,140 dofs same job = **689 s** (assembly 672 s), and 1,151 s with `BLAB_METAL_PIPELINE=0`; one warm frequency at 5,140 dofs is 3.2 s. A cliff, not a smooth curve. Per-frequency looping test in progress.
- Worker: cold 27 s, warm 1.4 s, after detach 0.84 s.
- Traces: 111,280 bytes per frequency at 2,369 dofs. Balloon grid theta 0-180, phi 0-348.75, shape (F, 512).
- Impedance BC: bempp only.

**Open issues / blockers**
1. `gh` is not authenticated: labels and GitHub issues cannot be created yet. Issue bodies are drafted in `.github/issues/`. (`git push` may work through the credential manager.)
2. M4 (CPU vs CUDA): CPU backend unprovisioned; to attempt once the GPU is free.
3. dof caps in the YAMLs (8000/16000/24000) are unsafe; provisional replacement pending the per-frequency loop result.
4. Plan drift: `SolveResult` (not `Response`) and `mesh_info.n_vertices` (not `p1_dof_count`): task 05 must adapt.
5. Mesh time and mesh fraction of a candidate not yet measured.

**Next action:** collect agent reports for 04 and 07; run M4 CPU provisioning; dispatch task 05 (solve) when the GPU is free; set dof caps; commit and push.

## 2026-10-12 — Wave 0 scaffold + CP-1 green (session 2)

**Done**
- `gh` installed (v2.102.0); **not** authenticated.
- Wrote owner-03 files: `pyproject.toml` (real SHAs, `pythonpath=["."]`), `.gitignore`, `README.md`, `hornlab_search/__init__.py`, `hornlab_search/cli.py` (`doctor`+`version`), `examples/icw_termination.yaml`, `examples/freeform_hv.yaml`, `examples/search_smoke.yaml`, `.github/workflows/ci.yml`.
- `pip install -e ".[dev,crosscheck]"` succeeds (pytest 9.1.1, pyyaml, cma, jinja2 present).
- First mesh + solve: 1419 verts / 2834 tris; cold 24.618 s, warm 0.494 s. Real schema is `SolveResult` (not the plan's `Response`).
- M1 calibration, M6 symmetry, M7 max_triangles measured (see `TOOLCHAIN.md`). C1–C5 answered from source.

**Pasted CP-1 output**

`pytest -q`:
```
..................                                                       [100%]
```

`hornlab-search doctor`:
```
PASS  python-version    Python 3.12.10 in [3.11, 3.14)
PASS  core-imports      numpy, scipy, cma, yaml, jinja2
PASS  hornlab-imports   mesher, beat, plots; bempp yes
PASS  pinned-shas       all installed SHAs match pyproject.toml
PASS  toolchain         TOOLCHAIN.md present, dof_per_triangle=0.51
PASS  gpu               nvidia-smi exits 0
PASS  backend           beat_cuda functional (state=ready)
PASS  configs           all 5 example configs load
PASS  round-trip        reserved for task 04
```

`hornlab-search version`:
```
0.1.0
```

**Open CP-0 items:** M2 (VRAM vs dofs + dof ceiling), M3 (s/person-candidate), M4 (cuda vs cpu), M5 (after-detach). All blocked on exclusive GPU access.

**Next action:** dispatch the Wave 1 issues in parallel using the prompt template in `docs/plan/00_ORCHESTRATOR.md` — **only after** CP-0 is completed on a clean GPU and the repo is pushed.
