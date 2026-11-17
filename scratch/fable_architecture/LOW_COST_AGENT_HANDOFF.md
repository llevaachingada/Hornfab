# LOW_COST_AGENT_HANDOFF — how to continue this research

**Written:** 2026-11-16. **Repository:** `C:\Users\hunte\Hrns\hornlab-search`.
**Code was read at** `main` @ `f0dd019`. **HEAD when this handoff closed:** `aa11b62` (equal to
`origin/main`). The diff `f0dd019..aa11b62` was not reviewed: before relying on a cited line number,
re-check it. All measurements below come from run artifacts under `runs/`, which code changes do
not alter.

## 1. Read these, in this order, and nothing else unless a brief sends you there

1. `ARCHITECTURE_SYNTHESIS.md` — the current architectural position and experiments E1–E3. It
   supersedes parts of the decision record.
2. `VALIDATION_EXPERIMENTS.md` — standalone briefs X1–X5 and the rules for every agent.
3. `CANONICAL_SURFACE_CONTRACT.md` — only if you work on X1, X2 or X4.
4. `ARCHITECTURE_DECISION_RECORD.md` — settled decisions D1–D10 and what stays open.

Upstream references, for derivations only: `FABLE_OPTIONS_REVIEW.md` (options, mathematics,
measurements M1–M6), `FABLE_DISCOVERY.md` (scoring findings), `INDEX.md` (the original evidence
dossier map).

## 2. Hard rules

- Read-only. No GPU or BEM solve, no solving CLI command, no pytest, no git mutation, no process
  control. A live solve queue may be running; do not touch it.
- No edits to tracked files, configs, queues or `runs/`. Write only under
  `scratch/fable_architecture/`.
- Interpreter: `.venv\Scripts\python.exe`. CPU only. Mesh builds only where a brief allows, into a
  scratch folder.
- Do not loosen a validation split, change a pass line after seeing results, or describe a
  surrogate prediction as an acoustic result.
- Any step marked "owner approval required" is a proposal. Write it up; do not run it.
- Owner-requested horn families are never to be recommended for cutting.

## 3. What produced the existing results

| Artifact | Made by | Contains |
|---|---|---|
| `.fable/rows.pkl` | `.fable/load.py` | All 3,802 attempts (3,414 valid) on the home landscape brief, runs `2026111[5-7]*-screen-*` |
| `.fable/desc.npz` | `.fable/an4.py` (via `an3.py`) | 27 mesh-derived geometry numbers, responses and lane labels for 1,715 designs |
| M1, M2 | `.fable/an1.py` | Response principal components; cross-engine response novelty |
| M5, M6 | `.fable/an2.py` | Per-lane knob importance and pinning; allocation replay |
| M4 | `.fable/an3.py`, `.fable/an5.py` | Cross-lane and cross-engine prediction; lane ranking; learning curves |
| M3 | `.fable/an4.py` | Shared shape modes and spline fits |
| Scoring results | `fable_zero_gpu_checks.py` (modes A, B) | Screen/verify gap; size sensitivity by similarity |

## 4. Measured versus inferred

**Measured (reproducible from the scripts above):**
- Six response components carry 95 % of beamwidth and DI variation (M1).
- 41–54 % of each engine group's sane designs lie far from other groups in response space (M2).
- Eight shape modes plus depth reproduce the H and V wall profiles of all lanes to 1.2 mm RMS (M3).
- Leave-one-lane-out beamwidth error about 4°; leave-one-engine-out skill R² 0.18–0.71 (M4).
- 2–7 of 5–18 knobs carry 90 % of importance; seven lanes have a pinned top-decile knob (M5).
- Best-of-first-16-rows predicts final lane rank at 0.90; campaign best reached at attempt 55 of
  2,853 (M6).
- Screen and verify use the same mesh; gap among the best 28 pairs is +0.19 J bias, 0.17 J spread.

**Known weaknesses of those measurements:**
- Sibling lanes (versions and brief twins of one construction) leak across "held-out" splits.
- M3 and M4 use two wall profiles, not the whole surface.
- M4 covers beamwidth and coverage error only, not loading, ripple or flatness.
- The M6 replay is flattered by a lane seeded with the best design; treat its saving as an upper
  bound.
- My replay harness mis-reproduces the `di` term; other terms replay exactly.

**Inferred, not measured:** that response-level selection beats scalar search; that the response is
locally invertible; that deformation modules add real control; that frequencies can be solved
incrementally at proportional cost.

## 5. Answered and open

**Answered:** the engines are worth keeping (M2); a shared geometric language is feasible in
principle (M3, mesher point-grid input); refusals are a second-order cost (about 10 % of attempts);
"verify" does not test mesh convergence; the 80 × 50 target is not met by any design in the 480 mm
envelope at 700–1,100 Hz vertically.

**Open:** see `ARCHITECTURE_SYNTHESIS.md` §6 and decision record §3. In one line each: which spine
(model-over-pool or construct-then-correct); which source of new shapes (modules or backbone);
whether transfer survives held-out engines; whether racing saves anything after corrections.

## 6. Recommended order of work

| Order | Task | Brief | Why here |
|---|---|---|---|
| 1 | E1: response-level versus scalar selection, replay | Synthesis §5 | Tests the core of the preferred architecture on stored data |
| 1 | X3: strict cross-engine transfer | `VALIDATION_EXPERIMENTS.md` | E1's cross-engine half depends on the same splits; do them together |
| 2 | E2 stage one: local invertibility from stored data | Synthesis §5 | Tests the alternative architecture; reuses `desc.npz` |
| 2 | X1: surface round trip | `VALIDATION_EXPERIMENTS.md` | Needed by X2 and X4; whole-surface descriptors also strengthen X3 |
| 3 | X2: module authority | `VALIDATION_EXPERIMENTS.md` | Needs X1 samplers and the X3 model |
| 3 | E3: frequency-sequential evaluation replay | Synthesis §5 | Independent throughput question |
| 4 | X4: parameter-space labels | `VALIDATION_EXPERIMENTS.md` | Needs X1 samplers |
| 4 | X5: corrected allocation replay | `VALIDATION_EXPERIMENTS.md` | Governance, not architecture |

R1–R4 (scoring) are with another agent; do not duplicate them. `MESH_FIDELITY_PAIRS.md` in this
folder is that agent's output.

For E1, E2 and E3 the synthesis gives the question, method, and deciding threshold. Write each
result as `E<n>_<NAME>.md` here, with scripts under `.e<n>/`, in the same format the X briefs use:
headline numbers, what failed, what is unknown, verdict against the stated threshold.

## 7. When to bring a high-thinking model back

After E1, E2 stage one, X2 and X3 have reported. The reserved decision is the choice of spine and
generative strategy together, plus the definition of the acquisition's value function
(`ARCHITECTURE_SYNTHESIS.md` §7). Also return early if X1 fails for two or more engines, or if R1
shows mesh error larger than the frequency-sampling error, because either invalidates assumptions
the other experiments rest on.
