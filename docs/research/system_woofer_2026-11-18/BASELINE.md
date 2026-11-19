# BASELINE — stage 0 machine + repo truth (system-woofer workstream)

Written by the parent orchestrator, 2026-11-18, worktree `C:/Users/hunte/Hrns/hornlab-woofer-system-wt`,
branch `feat/woofer-system-v0`, base commit `1e9f71b` (canonical `cloud/fable-next-2026-11-18` HEAD).
Stage 0 core committed at `928488f` in the worktree. All numbers below were captured on this machine.

## Git / repo relation to the master handoff (2026-11-18)

- Handoff's verified remote HornFab snapshot: `1d6ebc8` (2026-11-17). Local HEAD `1e9f71b` is **71
  commits ahead** of it; `git merge-base --is-ancestor 1d6ebc8 HEAD` exit 0 (1d6ebc8 is an ancestor).
  Local work (R1–R25 owner decisions, Klangfilm H/V kernel file-bytes pin, throat parking, v10 lines)
  is preserved and is the base — nothing from the doc's claims was assumed over local HEAD.
- Canonical checkout has uncommitted owner files: `AGENTS.md` (+10/−4), `CLAUDE.md` (+6),
  `.opencode/oh-my-opencode-slim.json` (+11), untracked `.claude/worktrees/` and
  `examples/typologies/home_landscape_2026-11-15/hl__klangfilm_lame_curved_v1_c200w.yaml`.
  All untouched by this project.
- Canonical suite state (CONTINUITY newest entry, 2026-11-18): `cloud/fable-next-2026-11-18` →
  4861 passed / 4 failed (known 4: test_v8_key_set, test_b8_lanes, 2 × test_night_bo_arm_wrapper) /
  22 skipped. Not rerun here; the system lanes run only their focused tests.

## Worktree environment

- Worktree created with `git worktree add -b feat/woofer-system-v0 ... HEAD` at canonical `1e9f71b`.
- `.venv` built in the worktree from the machine base Python 3.12.10
  (`C:\Users\hunte\AppData\Local\Programs\Python\Python312`): `pip install -e <worktree>` resolved all
  pinned deps into the worktree venv (numpy 2.5.5, scipy 1.18.1, cma 4.6.0, gmsh 4.15.2,
  hornlab-beat-bem 0.2.0, hornlab-plots 0.1.3, hornlab-waveguide-mesher 0.2.4, matplotlib, meshio; dev:
  pytest/pytest-xdist/pytest-timeout). Canonical `.venv` untouched.
- Import-root verified: `hornlab_search.__file__`
  → `C:\Users\hunte\Hrns\hornlab-woofer-system-wt\hornlab_search\__init__.py`.

## GPU / queue state (live check at start)

- GPU lane **held** by pid 62432 running job `c_rrect_100w_rc3` (night `cd_rrect_2026-11-17`,
  started 2026-11-18T13:33:14). CPU lane lock free. This project is **CPU-only** in stages 0–1;
  no solve, no BL solve, no Julia process started by any lane.

## Boundary Lab — machine truth (found; upstream claims to verify per install)

- **Present**: `C:\Users\hunte\Github\boundary-lab`, editable install (`pip show boundary-lab` →
  version 0.5.0, GPL-3.0, requires beat-engine/gmsh/...), `.git` HEAD `15f9a89245a9adfec8c2f0006c164953ce381e58`
  ("Fix solver rejection of imported driver reference metadata (#68)", 2026-11-02), branch main, clean tree.
- Own interpreter: `C:\Users\hunte\Github\boundary-lab\.venv` (Python 3.12.10). Console script
  `blab = blab.cli:main`; `src/blab/headless.py` present;
  `geometry_providers/vented_enclosure/` present. GUI startup logs at
  `C:\Users\hunte\AppData\Local\Boundary Lab\logs\` (2026-11-02).
- **Deviation from the handoff**: the doc verifies upstream `2cea009` (2026-11-09); the installed copy
  is `15f9a89` (2026-11-02). Installed code wins; lane C verifies actual public APIs on the installed
  copy and must report `BL_CAPABILITY_MISSING` for anything the doc claims but the install lacks.
- Owner probe hint (AppData\Local\Boundary Lab log dir) confirmed by machine scan: no standalone
  install under `%LOCALAPPDATA%\Programs`; the runtime is the Github clone's venv.

## Saved-horn asset inventory (read-only audits)

- Layout: `runs/<run>/designs/<design_hash>/{design.json,mesh.msh,response.npz,metrics.json,status.json}`.
  836 top-level run dirs; **41,859 response.npz**; 48,207 status.json on machine (recon full scan).
- Lane A audit of the 60 newest run dirs (read-only, `tools/system/audit_saved_horns.py --limit 60`):
  3280 design dirs scanned, 3047 assets after dedupe (16 duplicates collapsed), **3003 carry complex
  `p_h`/`p_v`/`p_balloon`**, 6 GEOMETRY_ONLY, 38 STALE_SOURCE. Recon 80-newest sample: 80/80 complex-
  fielded, 250–8000 Hz, 12–18 solved frequencies, `balloon_dirs` everywhere.
- **Phase/normalization fact (decisive, stage-governing)**: as stored, every complex field is unit
  normal **acceleration**, exp(−iωt) (`solve/beat.py:55`, `solve/phasor.py:3-9`; meta written at
  `solve/beat.py:553-554`, `bempp.py:120-122`; `solve/cache.py:129-150` reloads without conversion).
  The system contract requires exp(+jωt) per-input Pa. Therefore **0 assets qualify EXACT_COMPLEX as
  stored**; conversion must happen at an import boundary via the in-repo tested seam
  `compare/hornfab_side.py::accel_to_canonical` (`np.conj(p·(−1j·ω))`, round-trip tested in
  `tests/test_solve_phasor.py`, `tests/test_compare_ab_model.py`), yielding **SCREEN_COMPLEX_APPROX
  only** claims. No phase is imputed anywhere in this project.
- Metadata weakness: newest-run `status.json` carries only
  `{cached,error,key,mode,objective,ok,seconds,terms}`; run.json/design.json carry family/seed/lib_shas
  but no identity-v2 fields (`physical_solve_id` exists only in the newer `hornlab_search/studies/`
  layer). `01_CONTRACTS.md` has **no** `p_*`/basis/identity-v2 sections — the system package is
  contract-gap-tolerant only by being strictly additive with its own versioned ids.
- Cache roots: `solve/cache.py` takes explicit `root` params; CLI resolves `--runs-dir/--cache-dir`
  (`cli.py:29,360`). No env var exists in hornlab_search. The system module adds its OWN env var
  `HORNLAB_SYSTEM_RUNS_ROOT` (new, system-scoped only; default canonical runs) — documented in
  `hornlab_search/system/horn_assets.py`. Historical `runs/` is read-only for all lanes; project
  writes go to the isolated store (`system_runs/`, or `$HORNLAB_SYSTEM_STORE`).

## Driver data provenance (lane B proposals; acceptance gate before adding YAML files)

- **FaitalPRO 12PR300 8Ω, 12PR320 8Ω — machine-verified**: fetched vendor pages match every proposed
  T/S and geometry value (Re/Le/Bl/Sd/Xmax/P_AES/Fs/Qms/Mms/Mmd/Cms/Vas/Rms, cutout/depth/OD), plus
  extra installed-tier fields: bolt circle 298.5 mm, flange+gasket 12.1/12.0 mm, net air volume filled
  by loudspeaker 1.9 dm³ both, Xdamage 14/17 mm.
- **EighteenSound 10NMB420/12NMB420 — NOT machine-verified this pass** (vendor `.com` TLS cert error;
  `.it` page renders only marketing text). Values stay lane B proposals with disclosed nulls
  (Mmd/Cms/Rms not printed by 18Sound → derived). Datasheet-PDF check required before acceptance.
- 12PR300 model-Fs check +0.4%, 12PR320 −0.4% (within repo's 8% spread rule).

## Stage 0 bug fix (parent-owned), red→green

- `tools/bassbox.py::evaluate`: `z_in_ohm` was `1.0/i` where `i` scales with drive volts — impedance
  changed inversely with non-unit volts (test at 2.83 V reported exactly 1/2.83 × the 1-V impedance).
  Fixed to `e / i` + `volts` validation (non-unity/negative drive refused). SYS-01 test
  (`tests/test_bassbox.py::test_z_in_ohm_is_voltage_invariant_non_unit_drive`) failed first
  (red output captured), passes after; full `tests/test_bassbox.py` green (67 passed, exit 0).

## Contract freeze decisions (parent, this branch)

- `hornlab_search/system/contracts.py` v1 frozen at `928488f`: exp(+jωt)/Pa/per-input bases only,
  domain-separated 16-hex system ids (assembly/physics/analysis/score/study), strict schema-v1 parser
  (unknown keys = errors), PEQ band order **(fc_hz, gain_db, Q)** adopted (verified consistent with
  lane D's implementation and `meh/dsp.peaking`).
- `HornAsset.require_complex` raises `PhaseUnavailable` with the tokens
  `MAGNITUDE_ONLY / PHASE_ALIGNMENT_UNAVAILABLE` for any phase-sensitive use of unverified assets.
- One-worktree exception recorded in canonical `NOTES_FOR_SENIOR.md` (2026-11-18, dated entry).

## Unknowns / open (for the senior gate)

- 18Sound datasheet verification (above).
- Whether any historical run dir can be re-solved as a phase-qualified reference (needs GPU lane +
  senior authorization; not this stage).
- `docs/research/system_woofer_2026-11-18/METHODS.md`, `PILOT_EVIDENCE.md` follow in their stages;
  BL_PARITY.md now carries the Stage 1 BL evidence.

## Stage 1 appendix: Boundary Lab adapter evidence (added after lane completion, 2026-11-18 late)

Lane C was completed by the parent orchestrator directly (owner directive — no worker subagents).
Results supersede the "lane C in flight" notes above; full command/output/hashes in `BL_PARITY.md`.

- **Upstream check (owner request)**: GitHub API + local clone comparison. Upstream tip after local
  `15f9a89` (2026-11-02): BEAT-Engine 0.8.0 pin (Nov 7/9, `2cea009a`), ROCm field gradients (Nov 7),
  solve-ETA merge (Nov 18). `geometry_providers/vented_enclosure` last touched by commit `a56901f`
  (#43, 2026-10-09) — **unchanged upstream; local == current for this work**. The BEAT pin delta
  affects only Stage 4 solves (record as a Stage 4 pre-gate: owner may upgrade the BL clone then).
- Installed verified probe: `BL_CAPABILITY_OK`, v0.5.0 @ `15f9a89245a9…`, own venv Python 3.12.10,
  `blab.exe` present, vented plugin + `src/blab/generators/` present; file SHA-256s pinned in probe
  output (see BL_PARITY.md).
- REAL generations through BL's own environment (no solver):
  1. manifest defaults (0.32×0.50×0.36): interior FEM 3,176 nodes / 13,257 tets / 3,954 tris; exterior
     BEM 1,007 nodes / 2,010 tris; air volume 0.04216945 m³; port mouth ⌀ 0.08749 m.
  2. smaller box (0.30×0.46×0.35): 930 nodes / 3,270 tets / 1,456 tris; air 0.03462193 m³.
  3. infeasible width 0.28 m: BL's own validator refused ("Driver must fit inside the enclosure
     walls with 3 mm clearance") — adapter returns structured failure, rc 3. Also a real
     driver/port-overlap refusal recorded. No partial artifact ever accepted.
  4. `blab project validate` on `examples/Simple_Sealed/simple_sealed.blab.json`: rc 0, parsed JSON
     `valid: true` with system_id/frequencies/meshes/symmetry/assumptions fields.
- **Reproducibility property (recorded, not hidden)**: the same default spec generated twice yields
  identical air volume and triangle count but DIFFERENT byte-level mesh SHAs and ±0.13 % node/tet
  counts (Gmsh 3D algorithm nondeterminism). Downstream assembly identity therefore hashes the
  source spec + pinned provider files (it does), and any future mesh-convergence study must treat
  mesh-seed variance as part of the measurement, not as a bug.
- Contracts fix found by these tests: `canonical_json` stringified booleans (`'True'`); fixed to pass
  bools through (affects manifest integrity + identity inputs consistently on both sides).
- Solve gate: `solve_project` refuses by default (`BlockedByGate`) even with `HORNLAB_BL_ALLOW_SOLVE=1`
  without a recorded `authorized_by`; with both it still stops (Stage 4 belongs to BL's own CLI behind
  the GPU gate). No solver, no Julia process, no GPU contact by this project.

