# Combined solver-speed campaign (2026-11-13/14)

**SUPERSEDED 2026-11-13** by `docs/queue/SPEED_PROGRAM_2026-11-13.md` (Oracle-reviewed). Kept for history: the
program changes the arm set (old-solver batch-12 arms dropped, part two folded into the new solver SHA) and fixes
the ordering (finish the interrupted night before the solver swap - strict resume refuses after a library-SHA change).
Do not launch the night files this document names; they are deleted.

**Purpose.** Adopt more than one speedup at once, and prove the combination, instead of adopting G2 in isolation and
discovering later that the wins overlap.

**Owner constraint (binding):** nothing here may reduce frequency, angular or mesh resolution on any number that
counts as a result. Items that trade fidelity are listed in §7 and are **not** in the campaign.

## 1. What is in the bundle

| # | Change | Resolution impact | Evidence today | Code needed |
|---|---|---|---|---|
| P | Solver pin `0850ef39` → `9ec86b0` (A3: skip the unused fused identity cache) | none | G2: −55/−66/−70 % peak VRAM, −20/−30 % per-frequency wall; parity unmeasured on the fused path | none (install + pin lines) |
| B | Frequency batching `HORNLAB_FREQ_BATCH_SIZE=12` (G1) | none — same frequencies, mesh, quadrature, angles | N1: 1.9–4.7× solver-only warm; never worse; **never validated whole-candidate**; not used in production (`cma._prepare` never passes it) | none (env var) |

Together they attack different halves of the same per-request cost, and they **overlap**: the identity-cache build
that A3 removes is part of the per-request setup that batching amortises. Sequential adoption would double-count that
overlap, which is exactly why this is a factorial.

## 2. Why a factorial and not two A/Bs

Four arms per pin block — `{batch 1, batch 12} × {design 1, design 2}` — measured once on the old pin and once on the
new pin. That yields the two single effects, the interaction term, and the Oracle's outstanding fused-path parity
check as a by-product (`old,b1` vs `new,b1` on identical configs).

## 3. Designs (frozen, real next-round cells)

Both are already fused-CUDA (`solve.cuda_fused: true`, `backend: beat_cuda`), caps 12,000, 73 angles, balloon on,
band 350–8,000 Hz, screen mode; each arm states its own frequency count in `run.json`.

- **D1** `examples/typologies/print_80x60_2026-11-13/p80x60__osse_ext_throat_700_v7.yaml` (large OSSE)
- **D2** `examples/typologies/print_80x60_2026-11-13/p80x60__ath_core_14in_700_v7.yaml` (ATH-like morph)

`--budget 1`: the seed candidate only. Deterministic, no CMA exploration, so all arms solve the same geometry and the
comparison is about the engine, not about which candidate the optimizer happened to draw.

## 4. Arms and files

Block 1 (pin `0850ef39`, currently installed): `docs/queue/speed_combo_2026-11-14_oldpin.yaml`
Block 2 (pin `9ec86b0`, after the swap): `docs/queue/speed_combo_2026-11-14_newpin.yaml`

| arm | pin | batch | design |
|---|---|---|---|
| ctrl | old | 1 | D1 |
| b12 | old | 12 | D1 |
| ctrl | old | 1 | D2 |
| b12 | old | 12 | D2 |
| … same four repeated on the new pin | | | |

Copy both files to `runs/nights/` to launch. The pin swap between blocks is an integrator step (below), not a job.

## 5. Metrics recorded per arm

1. **Whole-candidate wall** — the number that matters; from the run's timings, not solver-only.
2. **Per-frequency wall** (`s_per_freq`) if present.
3. **Peak dedicated VRAM** — the night runner polls it; recorded next to the arm.
4. **Peak shared (WDDM) VRAM** — mandatory zero-spill check, **not** recorded by the night runner. Run one batch-12
   arm through `tools/bench/_bench_common.GpuMemPeak` (or an equivalent host counter) and record it; a non-zero spill
   invalidates that arm.
5. **Acoustic parity** — `hornlab-search compare <ctrl run> <arm run>`; bar **0.039 dB / 1° beamwidth** (`docs/FORKS.md`
   step 6.3). Batch arms should compare as identical; the pin arm is the Oracle's outstanding fused-path parity.
6. **Frequency count and DOF** per arm, so a hidden mesh difference can never hide behind a timing win.

## 6. Pre-declared decision rules

Adopt the **pin** if `wall(new,b1) / wall(old,b1) ≤ 0.85` on **both** designs **and** `compare ≤ 0.039 dB / 1°`
**and** peak dedicated VRAM is lower.

Adopt **batching** if `wall(·,b12) / wall(·,b1) ≤ 0.85` on **both** designs **and** `compare ≤ 0.039 dB / 1°`
**and** shared spill is zero.

Adopt **both** only if `wall(new,b12)` is at least as good as the best single arm on both designs, i.e. the
combination does not erode either gain. If it does, adopt the better single arm and record the interaction.

Reject any arm on a parity failure or any shared spill, regardless of speed. No threshold moves after the fact.

## 7. Deliberately excluded (fidelity or resolution)

- **Rear-shell density `rear_res_factor` 1.5/2.0 (G4)** — 16–21 % fewer DOF, but it coarsens the outer shell, which is
  acoustically coupled. It needs the G4 acoustic gate (beamwidth ≤ 2°, DI ≤ 0.2 dB, ReZ ≤ 0.03) and, per C1, a
  **verify-mode** mesh audit first (C1 measured screen mode only). Not in this campaign; a separate decision.
- **Quadrature order 4→2 (D1/plan)** — 1.5–2.5× on assembly, but it changes integration accuracy. Needs its own
  acceptance bar (0.05/0.10 dB, 0.3°).
- **Screen-fidelity decomposition (G3)** — ranking-only by design; does not touch verified numbers, but it is a
  fidelity-policy question, not a speedup to bundle here.
- **Reduced-order sweeps, coarser epw, fewer angles, FP32 Krylov, UI fidelity selector** — all reduce resolution,
  accuracy or coverage. Excluded by the owner's rule.

## 8. Budget and sequence

| block | content | GPU time |
|---|---|---|
| 1 | 4 arms on the current pin | ~15–20 min |
| swap | integrator: `pip install --force-reinstall --no-deps "hornlab-beat-bem @ git+https://github.com/llevaachingada/hornlab-beat-bem.git@9ec86b0…"` + `provision --backend cpu` | ~2 min |
| 2 | the same 4 arms on the new pin | ~10–15 min (should be faster) |
| 5 | ceiling sweep on the new pin, 15.9k / 20.2k / ~24k DOF, 2 reps, dedicated + shared | ~15 min |
| 6 | rollback or adopt the pin + A5 model update + docs | ~5 min |

Total ≈ **45–55 GPU-minutes**. Run it **before** resuming the paused print night, so the print night runs with the
adopted settings instead of being re-run afterwards.

## 9. Blockers / risks

- The pin cannot vary inside one night file (it is a venv install), hence two blocks and an operator step. Do not put
  `pip install` inside a night job.
- Batch 12 keeps the CUDA pool alive across frequencies; that is the point, but it is also the one thing that could
  raise peak VRAM. The per-arm peak record is the guard, and `worker_restart_every` exists if the pool grows.
- `HORNLAB_FREQ_BATCH_SIZE` is an env var, not a config key. If batching is adopted, add `solve.freq_batch_size` so
  the value is recorded in `config_sha`; until then the night's `env:` mapping is the audit trail.
- D1/D2 are the print cells; if their screen DOF approaches 12,000, batch 12 may be the arm that finds the memory
  ceiling. That is a result, not a failure — record it and fall back to batch 4.

## 10. A second fork commit worth doing before block 2 (optional, +30 min)

Lane C found the host-side twin of A3: `assemble_l2_identity_matrix` builds **two dense host N×N matrices** per
request (`BeatEngineDriver.jl:1534-1535`, `BeatEngineCore.jl:1187`) and the fused CUDA path never reads them. On
batch 1 that is paid per frequency — at 8k DOF, ~0.5 GB of host RAM and an O(N²) host assembly each time. Guarding
them the same way as A3 is a one-hunk change to the fork plus CPU tests. If it is done before the campaign, it becomes
a third pin level in block 2; if not, it is a follow-up with its own A/B.
