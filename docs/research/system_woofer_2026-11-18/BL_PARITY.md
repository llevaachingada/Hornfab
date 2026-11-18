# BL_PARITY — Stage 1 Boundary Lab adapter evidence (2026-11-18)

Written after lane C was completed by the parent orchestrator (owner directive: no worker
subagents for this work). Every command ran from the worktree with the worktree venv; BL ran in
its OWN environment. No GPU, no solver, no Julia process. Nothing in `C:\Users\hunte\Github\boundary-lab`
was modified (verified by clean `git status --porcelain` there and by SHA-256 pins below).

## 1. Pinned install identity (probe output)

- Root: `C:\Users\hunte\Github\boundary-lab` — checkout, version 0.5.0, git HEAD
  `15f9a89245a9adfec8c2f0006c164953ce381e58`, branch main, clean tree at handoff time.
- Python: `C:\Users\hunte\Github\boundary-lab\.venv\Scripts\python.exe` (3.12.10);
  CLI: `...\Scripts\blab.exe` ([project.scripts] `blab = "blab.cli:main"`).
- SHA-256 pins (from `tools/system/bl_smoke.py --probe-only`, verified `BL_CAPABILITY_OK`):

| file | sha256 (24 hex prefix) |
|---|---|
| enclosure/backend.py | `987683655a8fb804730c08f6` |
| enclosure/parameters.py | `51f8e82071ce9984ff651d126` |
| enclosure/worker.py | `2f4c950a186c80a33d47d999` |
| provider.json | `c23473653c1aa88ee4cc3bd0` |
| src/blab/headless.py | `8eed65739086d7d865c5296e` |
| src/blab/project_cli.py | `90edcdee6c80c907a9da0858` |
| src/blab/generators/base.py | `76912c07aa30df6549529490` |

## 2. Upstream-vs-installed delta (owner request, GitHub API)

Commits upstream NOT in the local clone: `80901922`/`2cea009a` (BEAT Engine pinned to 0.8.0,
Nov 7/9 — the master doc's verified snapshot), `797c5140`/`062f88ce` (ROCm exterior velocity/flow
fields, Nov 7), `a707d61c`/`10491569`/`12bef6ce` (solver ETA preservation, Nov 18). **`geometry_providers/vented_enclosure`
was last changed by `a56901f` #43 (2026-10-09)** — one commit total, already in the local clone.
Verdict: for vented geometry generation and project validation the installed copy equals current
upstream. The BEAT-0.8.0 pin matters only when a Stage 4 coupled solve is authorized; if the owner
updates the clone then, re-run the probe (hashes are recorded per generation in each manifest).

## 3. Real vented generations (SYS-03) — no solver, Gmsh meshing only

Runner: `hornlab_search/system/boundarylab/runner_vented.py` executed by
`C:\Users\hunte\Github\boundary-lab\.venv\Scripts\python.exe -I -B runner_vented.py <spec.json>`.
Adapter spec = provider.json `default_source` (verbatim, the plugin's own units) + overrides; BL's
own `parameters.validate` is the only geometry authority (no reimplementation).

| case dir (system_runs/system/bl_vented_gen/…) | spec | result |
|---|---|---|
| `20261118T205213Z-vented-31104-bd49dc6b` | manifest defaults (0.32×0.50×0.36 m) | OK — interior 3,176 nodes / 13,257 tets / 3,954 tris; exterior 1,007 / 2,010 tris; air 0.04216945 m³; port mouth ⌀ 0.087486 m; interior.msh 654,127 B sha256 `00b549b90a20dcf146eae`…; exterior.msh 123,810 B `a58f4afd4e3c9c3d08f45`…; mesh_info sha `2f474526376b8c0e`… |
| `20261118T205313Z-vented-10696-14c32e76` | 0.30×0.46×0.35, mesh 0.055, detail 0.025 | OK — interior 930 / 3,270 / 1,456; exterior 529 / 1,054; air 0.03462193 m³; interior.msh `7e2a0901a59f460bdfba6`…; exterior.msh `fbb02ce70dd961354571162a`… |
| `20261118T205247Z-vented-48540-0abd07c8` | width 0.28 m (infeasible) | BL's own validator refused: "Driver must fit inside the enclosure walls with 3 mm clearance." rc 3, adapter ok=False, NO artifacts accepted (SYS-04) |
| `20261118T205249Z-vented-19396-9d8993ea` | driver_y=port_y=0 (overlap) | BL refused: "Driver and port must not overlap; leave at least 3 mm clearance." rc 3, ok=False |
| `20261118T205430Z-vented-24120-eae6c238` | defaults again (reproducibility probe) | OK — see §4 |

Each ok run wrote an immutable `manifest.json` (self-checksummed by
`hornlab_search.system.provenance`) containing the BL root identity, the full spec, argv and the
runner's final JSON result including artifact SHA-256s. Output trees live inside
`system_runs/system/bl_vented_gen/<case>/bl_output/vented_enclosure_<uuid>/` with
`interior.msh`, `exterior.msh`, `source.json`, `meshing.log`, `mesh_info.json`.

## 4. Reproducibility property (SYS-16 seed truth, recorded as a finding)

Identical spec, two runs (`…205213Z` vs `…205430Z`): air volume equal to 8 decimals and identical
triangle counts, but different byte hashes and +4 nodes / +4 tets (0.13 %). Gmsh's 3D algorithm on
this install is not byte-deterministic. Consequences encoded in the adapter: assembly identity
hashes the SOURCE SPEC and pinned provider files (never the mesh bytes); mesh-convergence studies
(Stage 5) must include mesh-seed variance in their tolerances. No "identical bytes" claim is made.

## 5. Validate wrapper (SYS-03 extension)

`run.validate_project` on `examples/Simple_Sealed/simple_sealed.blab.json` (upstream example):

```
validate returncode: 0 | parsed keys: ['assumptions', 'backend_id', 'backend_requested',
  'excitation_port_ids', 'frequency_count', 'frequency_max_hz', 'frequency_min_hz', 'meshes',
  'output_ids', 'project', 'project_schema_version', 'solve_kind', 'symmetry', 'system_id',
  'system_name', 'valid']
valid flag: True
```

## 6. Solver gate proof (no GPU contact)

`run.solve_project(...)` — default: `BlockedByGate: BL solve refused by gate: environment flag
HORNLAB_BL_ALLOW_SOLVE=1 not set | keyword authorized_by … ; generate/validate only (Stage 1)`.
With env flag set but no authorization: refused (`authorized_by`). With both: refused again by
design ("intentionally inert in this stage"). Tested in `tests/system/test_boundarylab_geometry.py`.

## 7. License / provenance policy implemented (GPLv3 context)

External invocation ONLY: the adapter never imports blab in the HornLab venv (the runner is a
standalone file executed by BL's interpreter), nothing is copied out of the BL repository, and each
case manifest pins BL's root identity + file hashes. Attributed reuse of any BL source would be a
new, separately reviewed decision (master doc §3.1); none happened.
