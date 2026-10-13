---
title: "[09] Physics checkpoints CP-7a to CP-7f"
labels: [senior-review, blocked]
blocked_by: [08]
---

**Plan file:** [`docs/plan/09_CHECKPOINTS.md`](../../docs/plan/09_CHECKPOINTS.md)
**Wave:** 3 (senior agent, verification only, writes no code)
**Branch:** none (no code is written; results go in a PR comment or `NOTES_FOR_SENIOR.md`)

## Owned files
None. Verification only. Append findings to `NOTES_FOR_SENIOR.md`.

## Checkpoint
**CP-7, the physics gate**, in six parts:

- CP-7a: analytic pulsating sphere
- CP-7b: two independent solvers on the same mesh
- CP-7c: mesh convergence on a real horn
- CP-7d: symmetry
- CP-7e: plausibility against published horn behavior (only on balloon DI, never `cuts_estimate`)
- CP-7f: noise floor and what it permits

See "What the senior agent must refuse" in the plan file before waiving anything.

## Blocked by
Issue [08] (CP-6 must pass first).

## Dispatch
Use the "Verification dispatch prompt" at the bottom of [`docs/plan/09_CHECKPOINTS.md`](../../docs/plan/09_CHECKPOINTS.md); the general template is in [`docs/plan/00_ORCHESTRATOR.md`](../../docs/plan/00_ORCHESTRATOR.md).

## Wave 0 findings that affect this task
- **GPU/Julia hygiene.** Stale persistent Julia hosts hold ~1 GB VRAM each and cause false OOMs/crashes; follow the "GPU / Julia hygiene" section in AGENTS.md. A crash or OOM is only a finding once it reproduces from a clean state.
- **Symmetry.** Quarter vs full symmetry agree to 0.04-0.06 dB up to 4 kHz on a resolved mesh; use this as the expected scale for CP-7d.
