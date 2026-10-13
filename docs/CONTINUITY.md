# CONTINUITY

Newest entry first. Every push updates this file and `docs/ISSUES.md` in the same commit.

## Status
- **Wave:** 0 essentially complete (M4 CPU + final caps pending); Wave 1 in progress: 06 done, 04 and 07 running, 05 next.
- **Last checkpoints:** CP-1 GREEN (pytest, `doctor`, `version`). CP-0 PARTIAL: M1/M2/M3/M5/M6/M7 and C1-C5 measured clean; M4 pending. CP-4 (task 06) GREEN: 78 passed.
- **Next action:** see the newest entry below.
- **Blockers:** `gh` not authenticated (issues/labels); dof caps need replacing (plan caps unsafe on this 8 GB card).

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
