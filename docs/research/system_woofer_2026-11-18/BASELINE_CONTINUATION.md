# BASELINE_CONTINUATION — W0 verification record (2026-11-18, second session)

Written by the parent orchestrator continuing the handoff "HornFab Woofer Systems:
Continue the Existing Worktree to a Real BEM Reference" (consolidated edition 2).
Everything below was executed on this machine from the existing worktree
`C:/Users/hunte/Hrns/hornlab-woofer-system-wt` (branch `feat/woofer-system-v0`, HEAD `51179b9`
at session start, clean `git status --porcelain`). No new worktree, no resets; canonical
checkout only read.

## 1. Worktree / commit verification (observed commands)

```
git worktree list           # → C:/Users/hunte/Hrns/hornlab-woofer-system-wt  51179b9 [feat/woofer-system-v0]
git log --oneline -8        # 51179b9 stage 4 CPU pre-work … 928488f stage 0 … (6 feature commits confirmed)
git show --stat 51179b9     # assemble.py 307+, import_results.py 77+, test_assemble.py 187+, BL_PARITY.md 30+
```

## 2. Test baseline (observed, this session)

```
.venv\Scripts\python.exe -m pytest tests\system -p no:cacheprovider --timeout=300
→ 149 passed, 1 skipped in 3.99s
skipped: tests\system\test_boundarylab_geometry.py:217 — real Boundary Lab generation gated off
(set HORNLAB_BL_REAL_TESTS=1)   # pre-existing env gate, not a new skip
```

Wider sweep also green (same session): `pytest tests/system tests/test_bassbox.py
tests/test_solve_phasor.py tests/test_compare_ab_model.py` → all passed, same single skip.
The stage-4 commit message's "159 system tests" predates this session; observed truth on
this box is **149 passed + 1 skipped** (collect-only lists 150 including the gated one).
Recorded as-is; nothing was weakened to make it fit.

## 3. Machine/job state (observed)

- GPU lane: HELD by active night job `w_ext_throat_hvlaw_cov_v7_200w1`
  (`tools/night_status.py`, night `cd_rrect_2026-11-17`, running since 16:27 local).
  CPU lane lock free. → This project stays CPU-only (as staged); the planned smoke solve
  uses BL's `beat_cpu`, which is not the hornlab CUDA lane and does not touch the hornlab
  Julia host or GPU lane locks.
- Do not kill any night job or Julia host; do not write to `runs/`.

## 4. Confirmations against the handoff's baseline table (§1)

| Claim | Observed | Verdict |
|---|---|---|
| Six feature commits, latest 51179b9 | git log shows exactly 6 on top of `1e9f71b` | confirmed |
| 159 tests + 1 env skip | observed 149 passed + 1 skipped (149+1 gated = 150 collected) | recorded, see §2 |
| Quarter mesh QA: 162 free edges on symmetry planes | BL_PARITY.md §8 + `horn_mesh_qa` code | confirmed in code + evidence |
| Draft BL validate: `Unsupported physical model_version 0.` | BL_PARITY.md §8, verbatim, returncode 1 | confirmed |
| No assembled BEM solve yet | no solve manifest under `system_runs/system/` (checked) | confirmed |

## 5. Case freeze (also see FIRST_REFERENCE_CASE.json, same directory)

- Horn asset: `0062fb59fbf63eae` (FREEFORM, brief `lecleach_rollback_1in_v6`, design
  `9e02db06ecc3`, run `20261118T200653Z-screen-31495a` in canonical `runs/`, 1-inch throat,
  complex `p_h/p_v/p_balloon` as stored → converted basis is SCREEN_COMPLEX_APPROX only).
- Woofer: FaitalPRO 12PR300 8Ω (vendor-verified T/S + geometry; see BASELINE.md driver
  section; `examples/systems/driver_ts/` + `driver_geometry/` YAMLs committed).
- R0 control box: BL provider defaults (already generated twice, air 0.04216945 m³).
- R2 assembly box candidate: 371.2 × 371.2 × 1080.7 mm ext, net 115 L, tune 53.3 Hz,
  port 170 cm² from pilot study `783043edcbecf2fe` (PASS rows; provisional until BL's own
  geometry validator accepts the driver/port fit).
- First smoke request: frequencies [250, 700, 1100] Hz, backend `beat_cpu`, modest probes,
  strictly AFTER `blab project validate` success + graph assertions.

## 6. Live gates and lane plan (this session)

1. **BLOCKED_BY_FULL_DOMAIN_HORN_MESH** → Lane A (in flight, background): rebuild the saved
   design full-domain via the existing `mesh.build` path with `sizing.py` quadrants
   `"1234"` (QUADRANT_FACTOR confirmed: `{"1234": 1, "12": 2, "14": 2, "1": 4}`), with the
   original-quarter regeneration parity gate first (REF-02).
2. **BLOCKED_BY_BL_HOST_ASSEMBLY_ASSIGNMENTS** → Lane B (in flight, background): reproduce
   the upstream vented staging fixture through BL's own host (`stage_generation` →
   `PhysicalSystemCompiler` → `physical_system_to_dict` → `write_project_file` → real
   `blab project validate --json`), then add the full horn as an imported BEM mesh with a
   rigid wall assignment and an independent ideal source port. R0 (vented-only) proceeds
   first and is independent of the horn.
3. Lane C (in flight, background): canonical reader for BL headless result manifests /
   per-excitation complex bases, grounded in the installed BL 0.5.0 output schema only.
4. Lane D (after B): no-GUI reference CLI (prepare → validate → solve → report) + case runner.
5. W3 smoke solve and FIRST_BEM_EVIDENCE.md strictly after lane B validates.

Divergence note (recorded, not silently assumed): the handoff's baseline table says
"159 tests"; observed 149 + 1 skipped. And the handoff's asset preference for an OSSE/ATH
candidate from the 80×50 program is respected by keeping the r-OSSE/OSSE assets on lane A's
fallback ladder — the primary asset is the project's already-verified, fully instrumented
pilot asset (FREEFORM), chosen because the handoff's own gate (reproducible recipe + provenance)
outranks family preference and its stop condition explicitly permits the next asset only if
rebuild fails.
