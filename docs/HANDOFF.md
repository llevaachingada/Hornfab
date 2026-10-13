# HANDOFF — Wave 0 bootstrap, session 3, 2026-10-12

Supersedes the two earlier handoffs. Repo: `C:\Users\hunte\Hrns\hornlab-search` (git on `main`, **still no commits, no remote**).

**Stop after Wave 0. Do not start Wave 1 modules.**

## ⚠️ READ THIS FIRST — a second agent is working the same repo

While this session ran, **a separate Claude session** (process tree rooted at a `.claude/shell-snapshots` bash, running `m2_driver2.py` / `m2_one.py` / `m2_driver3.py`) was doing the **same Wave 0 task** in the same scratch dir (`C:\Users\hunte\AppData\Local\Temp\opencode\hornlab-scratch`) and editing the same repo files. Consequences:

- It **updated `examples/*.yaml` `dof_per_triangle`** to 0.51/0.50 (matching this session's M1 numbers) and **drafted `.github/issues/*.md`** (04–09 + question issues).
- It ran **concurrent BEM solves on the single GPU**, which **invalidated every M2/M3/M4 number** and caused `Out of GPU memory` and `ConnectionResetError`.
- **Two agents editing the same files will collide.** Before continuing, decide which session owns the repo; kill the other, or serialize. **One GPU, one BEM solve at a time** (`docs/plan/00_ORCHESTRATOR.md`).

## FIRST ACTIONS FOR THE NEXT AGENT

1. **Ask the user to run `gh auth login`.** `gh` is installed (v2.102.0) but not authenticated; `GITHUB_TOKEN`/`GH_TOKEN` are unset. Repo creation + push are blocked on this.
2. **Ensure exclusive GPU access** (no other agent solving) before any M2–M5 measurement.
3. To recover from the orphaned workers this session hit: kill stray `julia.exe` / `julia_beat` worker hosts, delete `%LOCALAPPDATA%\HornLab\BEAT\workers`, or set `HORNLAB_BEAT_WORKER_DIR` to a fresh dir.

## Environment (verified)

- venv interpreter: `C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe` (Python 3.12.10).
- `pip install -e ".[dev,crosscheck]"` succeeds. Machine: Win 11 Pro build 26200, i7-14650HX (16c/24t), 31.7 GB, **RTX 4060 Laptop 8 GB**, driver 610.62, CUDA 13.3.
- CUDA `ready` (beat 0.2.0). **cpu backend unprovisioned**; rocm/metal n/a. bempp available (bempp-cl 0.4.2).
- Installed SHAs (= `pyproject.toml`): mesher `b922e807…`, beat `38544d21…`, plots `9e4a6d0d…`, bempp `8e691060…`.
- Mesher CLI: `hornlab-waveguide <config.toml> -o <out.msh>`. Examples are NOT in site-packages; use the source clone
  `C:\Users\hunte\AppData\Local\Temp\claude\C--Users-hunte-Hrns\a6d40e1e-5753-40e0-bc82-45dfdc35e6c1\scratchpad\src\`.
- Scratch: `C:\Users\hunte\AppData\Local\Temp\opencode\hornlab-scratch` (contains M1 meshes + probe scripts, but is shared with the other agent — use a fresh dir).

## Agent routing reality

- **@fixer works.** **@explorer is broken**: configured to `deepseek/deepseek-v4-flash`, which does not exist → `Model not found`. @librarian likely same. Fix `.opencode/oh-my-opencode-slim.json` or do recon yourself.
- @fixer has file tools but **no shell/GPU**; all measurements must be run by the orchestrator.
- Parallelizable: GPU measurements (orchestrator, serial) **‖** @fixer writing lanes.

## DONE (this session)

- gh installed (not authed).
- Owner-03 scaffold: `pyproject.toml`, `.gitignore`, `README.md`, `hornlab_search/__init__.py`, `hornlab_search/cli.py`, `examples/{icw_termination,freeform_hv,search_smoke}.yaml`, `.github/workflows/ci.yml`.
- `pip install -e ".[dev,crosscheck]"`.
- First mesh + solve; real schema is **`SolveResult`** (not `Response`; dof = `mesh_info.n_vertices`).
- **CP-1 is green:** `pytest -q` → **18 passed**; **`doctor` → exit 0, all 9 PASS**; `version` → `0.1.0`; CI selection `-m "not slow and not gpu and not crosscheck"` → 18 passed.
- **`TOOLCHAIN.md` written** (partial; M2/M3/M4 UNRESOLVED — see below).
- **`docs/CONTINUITY.md`** and **`docs/ISSUES.md`** written; `docs/HANDOFF.md` (this file) refreshed.
- **M1** (dof/tri: 0.500 full, ~0.51 quarter), **M6** (≤0.26 dB at 1/2/4 kHz; 8 kHz under-resolved), **M7** (18k is a default; 200k built 70460 tri) measured.
- **C1–C5 answered:** C1 balloon via `ObservationConfig.sphere_grid` (theta-major, full sphere), C2 complex pressure `pressure_complex` on both, C2b traces on both + `evaluate_exterior_from_traces(...)` signature recorded, **C3 impedance/Robin BCs = bempp YES / beat NO**, C4 point grid reachable via public API (phi-major, `(grid_n_phi, grid_n_length+1, 3)`), C5 source tag 2 = `SD1D1001`, single unit normal-acceleration source.

## NOT DONE — next agent

1. **CP-0 GPU measurements** on an exclusive GPU: **M2** (VRAM vs dofs at ~2k/6k/9k/13k/17k + the 8 GB dof ceiling), **M3** (s per screening candidate + mesh fraction), **M4** (cuda vs cpu; provision cpu or record UNRESOLVED), **M5** (after-detach sample). Then update `TOOLCHAIN.md` (replace the UNRESOLVED entries) and the dof caps.
   - Known: dense **8·N²** storage confirmed (N=20193 → exactly 3.038 GiB). Caps `verify 16000`/`final 24000` must be validated; the true ceiling is between ~9k and ~20k dofs and is **unmeasured**.
2. **GitHub**: after `gh auth login`, `gh repo create hornlab-search --private --source . --push`; labels `wave-1, wave-2, senior-review, phase-2, blocked, question`; issues 04/05/06/07 (wave-1), 08 (wave-2 blocked by 04–07), 09 (review blocked by 08) + question issues. Drafts for all of these already exist in `.github/issues/` (written by the other session) — review and use them.
3. **Push everything** (CommitBot: conventional commits ending `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`); CONTINUITY.md + ISSUES.md in every pushed commit.

## Key deviations (also in `NOTES_FOR_SENIOR.md`)

1. GPU is RTX 4060 Laptop, not 4070 (approved).
2. Solver API drift: `SolveResult` / `mesh_info.n_vertices`, no `p1_dof_count`/`native_diagnostics`.
3. M2/M6 OOM observations are **contaminated by the concurrent session** — re-measure. The 20k-dof OOM in particular may be contention, not a hard limit.
4. ICW `termination` categorical; `coverage_angle` half-vs-total unconfirmed.
5. CP-1 angle test (0.01° step) and cardioid −6.0206 dB deviations.
