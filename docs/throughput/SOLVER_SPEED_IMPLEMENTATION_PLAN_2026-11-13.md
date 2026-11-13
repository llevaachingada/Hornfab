# Solver speed and fidelity: consolidated implementation plan (2026-11-13)

**Status:** plan, owner-approved for implementation. No code shipped by this document.
**Merges:** [HANDOFF_LOCAL_AGENT_IMPLEMENTATION_2026-11-13.md](HANDOFF_LOCAL_AGENT_IMPLEMENTATION_2026-11-13.md) ("LA", P0a-P8)
and [HANDOFF_HUYGENS_SOLVER_SPEED_2026-11-13.md](HANDOFF_HUYGENS_SOLVER_SPEED_2026-11-13.md) ("HY", P0-P5).
Both handoffs stay in the repo as the source of detail, evidence and gates. This file decides **order, owners and file locks**.
Claims in the handoffs were not re-verified for this plan; each package re-reads current code before editing (current code wins).

**Objective (both handoffs agree):** more verified acoustic information per wall-clock hour at fixed physics. No new
score versions, no new optimizer, no new UI controls in this effort.

---

## 1. What the two handoffs map to (dedupe)

| Topic | LA | HY | Merged package |
|---|---|---|---|
| Cache/provenance can silently reuse old-pin solves | P0a | P0 audit, §6 | **A1** (blocker for every pin change) |
| Seam check solves above the lower mesh's limit | P5 fix | P2-B | **A2** |
| Skip unused fused-CUDA identity cache | P2 | (implicit) | **A3** code, **G2** GPU validation |
| Per-region mesh fidelity status | P4 | P2-C | **A4** |
| Dense-memory feasibility preflight (refuse before OOM) | P6 preflight | §2, UI "feasible" | **A5** |
| Replay version support honest (v5-v7) | §1 table | §6 | **A6** |
| Frequency batching rollout (env knob exists) | P1 | P4 (bounded) | **G1** |
| Screen vs verify rank reliability | P0b | P1 harness | **G3** |
| Rear shell density (`rear_res_factor`) | P3 | P2-C | **C1** (CPU mesh) then **G4** |
| Band-split A/B | P5 A/B | P2-B | **G5** |
| CUDA quadrature order | P8 row 1 | P2-D | **D1** (after G2) |
| 8-20 kHz finalist verify path | P6 | UI Level 2 | **D2** (after A2, A5, G5) |
| Boundary-trace reuse for new angles | P7 | — | **D3** |
| Dense GMRES, pipelining, FMM, BEMAO, axisymmetric, Huygens/Metal | P8 | P3-P5 | **Deferred** (§5) |

---

## 2. Wave A: offline code, start now, fully parallel (no GPU, no queue touch)

Two orchestrators run at once. Each spawns subagents on **disjoint files**. Per `AGENTS.md` (2026-11-12 amendment)
only the parent integrator does git; agents edit only their locked files.

### Orchestrator 1: HornFab Python (one repo, file-locked lanes)

| ID | Package | Files locked (edit only these + own new tests) | Done when |
|---|---|---|---|
| **A1** | Cache provenance guard. Add `solver_sha`, `mesher_sha`, cache schema version to solve-cache store/lookup; mesher SHA into the formula mesh-cache key. Lookup: exact match = hit; mismatch or missing provenance = miss (legacy entry left in place, readable, never relabeled). Append an implementation-qualified ID next to `physical_solve_id`, do not rewrite it. Cover single solve, band split, MEH, formula mesh; record GRID/CAD as "no shared cache" in the audit note. | `solve/cache.py`, `mesh/build.py` (cache key lines only), `dataset/identity_v2.py`, `tests/test_solve_cache*.py`, `tests/test_mesh_cache_provenance.py` | Simulated pin change misses; same pin hits; legacy file bytes unchanged (hash before/after in test). |
| **A2** | Seam check fix. Probe at the last lower-band frequency (inside its rated limit), solve that same frequency on the upper mesh, compare on-axis complex pressure, beamwidth, DI, impedance. Fail is enforceable in verify mode, metadata-only in screen. Record per-band mesh hash, DOFs, backend, validator status. | `search/evaluate.py` (`_seam_check`, `_compute_band_split` only), `tests/test_search_band_split*.py` | Unit test with fake solver proves probe frequency is <= lower band max; verify-mode failure surfaces. **Starts after A1 merges** (A1 touches evaluate.py lookup paths). |
| **A4** | Mesh fidelity report. New offline tool: per-physical-region triangle count, edge p50/p95/max, kh at target fmax, and `mesh_fidelity_status` enum (source-valid / global-max-edge-valid / CAD-checked / converged-vs-ref / not-assessed). Read-only on meshes. | new `tools/analysis/mesh_fidelity.py`, new `tests/test_tools_analysis_mesh_fidelity.py` | Runs on a cached mesh fixture; status never claims more than the evidence. |
| **A5** | Feasibility preflight. Pure function: DOFs, symmetry, backend, dtype -> dense matrix lower bound + LU workspace estimate vs measured VRAM/RAM headroom; returns fit / risky / refuse with reason. Wire as a warning only (no refusal yet) in verify. | new `hornlab_search/solve/feasibility.py`, new `tests/test_solve_feasibility.py`; one call site added by A2's agent after A2 lands | Matches the handoff arithmetic (34k DOF ~8.6 GiB per complex64 matrix). |
| **A6** | Replay support honesty. Report per objective version whether replay is supported; unsupported versions return an explicit "not replayable" status, never a silent wrong score. | `objective/replay.py`, `tests/test_obj_replay.py` | Test enumerates v1-v7 and asserts supported/unsupported explicitly. |

Parallel now: **A1, A4, A5, A6**. Then **A2** after A1. Merge order: A1 -> A6 -> A4 -> A5 -> A2.

### Orchestrator 2: BEAT fork + mesh study prep (different repo, no HornFab file overlap)

| ID | Package | Files | Done when |
|---|---|---|---|
| **A3** | Fork patch: build `cuda_solve_identity_cache` only when non-fused CUDA needs it. Re-grep every reader first (driver `:1631-1667`, `:2049`, core `:1417-1423`, `:2251`) and confirm the fused flag is settled before the skip. Nothing else in the diff. New branch in `forks/hornlab-beat-bem`, new SHA, per `docs/FORKS.md`. **Do not change the HornFab pin** until A1 merged and G2 passes. | fork `BeatEngineDriver.jl` + fork test | Fork offline tests/analytic selftest on CPU pass; diff is one guarded allocation. |
| **C1** | Rear density mesh audit, CPU only. Copy configs for 4 seed horns (modest OSSE, rolled R-OSSE, ATH-like, T2 if it fits) at `rear_res_factor` 1.0/1.5/2.0/2.5; mesh only; run A4's tool on each. Report realized per-region DOFs and whether the clearance guard ate the saving. | copied configs under `examples/studies/rear_density_2026-11-13/`, results under `docs/evidence/` | Table of realized DOF reduction per horn. Picks which factor(s) G4 solves. Needs A4 (or use its draft). |

---

## 3. Wave B: GPU lane, serial, one job at a time (after Gate 0)

Run through `hornlab-gpu-job` hygiene and the night queue. Do not preempt jobs already in
`docs/research/QUEUE_PLAN_REV2_2026-11-13.md` (`fid_dist8m`, `fid_ang145` etc. count as their own evidence, not ours).
Order is by value per GPU hour:

| Order | ID | What | Gate |
|---|---|---|---|
| 1 | **G1** | `HORNLAB_FREQ_BATCH_SIZE` 1/4/12, 2-3 frozen designs, 12 and 25 freq grids, whole-candidate wall + Windows shared memory. | Repeatable whole-run gain, identical outputs, zero spill. Adopt per job class via env, no new config knob. |
| 2 | **G2** | A3 fork vs current pin, same mesh at ~4k / ~8k / near current ceiling. Dedicated + shared peak, CUDA.jl live/reserved, wall, parity. | Gate 2 in LA. Gain -> pin bump (one commit, rollback = old SHA). No gain -> revert, document negative. |
| 3 | **G3** | Screen fidelity 2x2 (screen/verify mesh x sparse/dense grid) on 6-10 cached diverse finalists, same scorer. Spearman/Kendall, top-k recall. Until done, verify 15-20 diverse finalists, not top 5. | Gate 1 in LA. Only then change the screen policy. |
| 4 | **G4** | Solve C1's winning rear factor(s) vs 1.0 vs a finer reference, H/V/diag + impedance. | Gate 3 in LA. |
| 5 | **G5** | Band split 1 vs 2 vs 3 bands on 2-4 designs, identical freq list, with A2's seam. | Gate 4 in LA. |

G1 can start as soon as the queue gives a slot (no code dependency). G2 needs A1 merged + A3. G5 needs A2.

---

## 4. Wave C: build on proven results (start only when its gate passes)

| ID | What | Trigger |
|---|---|---|
| **D1** | Hashed `solve.quadrature_order` for CUDA regular integration, fixed 4 vs 2 A/B against higher-order reference. Must enter the solve hash (A1). | G2 done and assembly still dominates. |
| **D2** | High-band finalist verify: `verify --freq-range` reusing `evaluate.py`, own record identity, backend chosen by A5 preflight + measured threshold, not a hardcoded 8 kHz switch. 8-12 kHz on 3-5 horns first. | A2, A5, G5 pass. |
| **D3** | Keep full per-band boundary traces for a few finalists; offline field re-evaluation at new angles/distances. | D2 running; parity test reproduces same-solve cuts incl. phase. |

---

## 5. Deferred (not in this effort; logged in NOTES_FOR_SENIOR.md)

Dense GMRES on CUDA/CPU (HY P3), assembly/solve pipelining (HY P4), persistent GPU context, direct-device field
evaluation, smoothing/edge swap, adjoint/adaptive BEM, BEMAO/curved elements, FMM/NumCalc/Bempp OSRC spike,
axisymmetric solver, reduced-order sweeps, half-space baffle formulation, Huygens/hornlab-metal-bem head-to-head on
the Mac, geometric (not density) rear simplification, `curvature_npts` as a DOF saver, UI fidelity selector
(HY §7 Level 2). Each needs its own proposal once Waves A-C show the dense path cannot meet the target.

---

## 6. Rules every agent in this effort follows

1. Read current code first; report and follow it where it contradicts a handoff.
2. One package = one small reviewable change set. No bundling solver + mesher + scorer changes.
3. Never edit `.venv` or `.julia`; fork changes only via `docs/FORKS.md`.
4. No GPU, no `gpu-clean`, no host kills, no queue edits in Wave A. Respect CPU/GPU lane locks.
5. Old responses, caches and datasets are immutable. Add side-by-side, never overwrite.
6. Any speed number states scope (solver-only / mesh+solve / whole candidate), warm/cold, and shared-memory spill.
7. Every pushed commit updates `docs/CONTINUITY.md` and `docs/ISSUES.md`; new docs/modules get `docs/INDEX.md` / `docs/CODE_MAP.md` lines.

## 7. Launch prompts (copy into each orchestrator)

**Orchestrator 1:** "Execute Wave A, Orchestrator 1 of `docs/throughput/SOLVER_SPEED_IMPLEMENTATION_PLAN_2026-11-13.md`.
Spawn one subagent each for A1, A4, A5, A6 with only the files in their row; start A2 after A1 is merged. You are the
only git writer. Offline tests only. Report pass/fail per package against its 'Done when'."

**Orchestrator 2:** "Execute Wave A, Orchestrator 2 of `docs/throughput/SOLVER_SPEED_IMPLEMENTATION_PLAN_2026-11-13.md`.
A3 in the BEAT fork (do not change HornFab's pin) and C1 CPU-only mesh audit. No GPU. Report the fork SHA, the exact
diff and the C1 DOF table."
