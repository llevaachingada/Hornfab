# Integrated solver-speed program (2026-11-13, Oracle-reviewed)

**Status:** approved design, **not launched**. Supersedes `docs/queue/SPEED_COMBINED_2026-11-13.md` (kept for history).
**Owner constraint:** nothing may reduce frequency, angular or mesh resolution, accuracy or coverage on numbers that
count as results.

## 1. Names — retire the old vocabulary

| Plain name | What it is | Old names | Status |
|---|---|---|---|
| **Solver upgrade (part one)** | The fused GPU route built two giant identity-matrix lookup tables per solve that nothing reads. One hunk stops building them. | "pin bump", "G2", "A3", "patch 1", "new pin" | written, measured (`9ec86b0`) |
| **Batching switch** | Today each frequency is a separate request, paying setup 12+ times. A switch hands the solver 12 frequencies per request. | "G1", "batch 12", "the env var" | exists, off in production |
| **Solver upgrade (part two)** | The same tables are also built in main memory on the fused route. Same one-hunk idea, host side. | "patch 2", "Lane C candidate B" | **not written** |
| **Mesher question** | No local edits exist. The question is whether our pinned mesher predates an upstream FREEFORM cost fix. | "the mesher unknown" | question, not a change |
| **Round A / Round B** | The two GPU sessions: today's solver, then the new solver. The solver is a venv install and cannot vary inside one night. | "block 1 / block 2" | planned |

## 2. The six steps

**Step 1 — finish the interrupted night on today's solver.** `search --resume runs/20261113T193536Z-screen-81c964
--budget 200` (~47 candidates left), current pin. **Why first:** `search/cma.py:702` refuses a strict resume after any
library-SHA change, so swapping the solver first would strand the 153 candidates already paid for. Its unstarted
third job relaunches **fresh after adoption**. ~30-60 GPU-min.

**Step 2 — write "solver upgrade part two" into the fork (no GPU).** Guard the two host-side dense identity builds
(`julia/BeatEngineDriver.jl:1534-1535`; they are never read on the fused route) **on top of** the existing upgrade
commit, so one new fork SHA means "new solver, both parts". Julia CPU testset green. Same step: refresh the stale
mesher checkout (`git fetch` the pin — housekeeping only, no install change). ~30-45 min, no GPU.

**Step 3 — Round A (GPU ~10 min).** Two arms, batch 1, `--budget 1` (seed geometry only): `docs/queue/
speed_round_a_2026-11-14.yaml`. These are the baselines everything is compared against.

**Step 4 — swap the solver (5 min, integrator, never inside a night job).** Install the new SHA from the GitHub URL,
`provision --backend cpu`, verify `direct_url.json` reports the SHA and the patched lines are present.

**Step 5 — Round B (GPU ~25-35 min).** Four arms: {batch 1, batch 12} x {D1, D2}: `docs/queue/
speed_round_b_2026-11-14.yaml`. Proves the upgrade effect (new b1 vs old b1, same design - this **is** the fused-path
parity check), the batching effect, and that the combination erodes neither. Then the **memory-ceiling sweep**
(commands in §5) to find how big a mesh now fits.

**Step 6 — the merge (one commit).** If the bars in §4 pass: solver pin lines (`pyproject.toml`, `TOOLCHAIN.md`),
`freq_batch_size: 12` as a real **config key** wired into the search path (visible in provenance, replacing the hidden
env var), A5 memory model re-based on the **measured** 20.2k point (repo rule 7 — not on arithmetic), docs. Then
production nights relaunch fresh under the adopted settings, absorbing the old night's deferred third job.

## 3. Merge decisions

| Change | Recommendation | Condition that flips it | Undo |
|---|---|---|---|
| Solver upgrade, part one | **merge fully** (becomes the pin) | fused-parity compare fails 0.039 dB / 1 deg, or shared spill, or peak VRAM not lower | ~2 min (reinstall old SHA + revert pin lines) |
| Solver upgrade, part two | **fold into the same new solver version** — do not measure as a third level | bundle slower than old-solver b1 on both designs → bisect the two fork commits | revert one fork commit |
| Batching | **merge behind a config key**, default 12 in CUDA examples; env var stays as fallback | ratio > 0.85 on either design, or shared spill > 512 MiB → fall back to batch 4, same night | one config line |
| Mesher | **out of this program** (pin unchanged) | ancestry check says the pin predates the FREEFORM fix **and** a live typology is FREEFORM → its own program | nothing changed today |

## 4. Test matrix and pre-declared bars

| arm | solver | batch | design | buys | cost |
|---|---|---|---|---|---|
| base-D1, base-D2 | today | 1 | osse_ext_throat, ath_core | baseline wall + VRAM | ~10 min |
| new-D1, new-D2 | new | 1 | same | upgrade wall + VRAM + **fused parity** | ~10 min |
| new-b12-D1, new-b12-D2 | new | 12 | same | batching + interaction + spill check | ~12 min |
| ceiling 3 pts x 2 reps | new | - | osse seed | new memory ceiling, A5 re-base | ~12 min |

**Bars (no threshold moves after the fact):**
- **Upgrade:** `wall(new,b1)/wall(old,b1) <= 0.85` on **both** designs; `compare <= 0.039 dB / 1 deg` on both; peak
  dedicated VRAM lower; shared peak < 512 MiB.
- **Batching:** `wall(new,b12)/wall(new,b1) <= 0.85` on both; compare within the same bar; shared peak < 512 MiB.
- **Both:** `wall(new,b12)` no worse than the best single arm on both designs.
- Every arm records frequency count and DOF, so a hidden mesh difference can never hide inside a timing win.
- A ceiling point that does not fit is a **result**, recorded, not a failure.

**Dropped as unnecessary:** old-solver batch-12 arms (N1 already covers batching at solver-only scope); a third
measured solver level for part two; batch-4 unless batch 12 trips a bar; MEH/non-fused control points (paused, and the
patches provably do not touch those paths).

## 5. Ceiling sweep (after Round B, new solver, fresh process per point)

Calibrated quarter-DOF: `--mouth-res 5.03` = 15,878; `4.46` = 20,152; `4.09` = 23,850. Run each twice, with
`hornlab-search gpu-clean` between, recording **dedicated and shared** memory:

```powershell
.venv\Scripts\hornlab-search.exe gpu-clean
.venv\Scripts\python.exe tools\measure_fused_ceiling.py --mouth-res 5.03 --flag on
.venv\Scripts\python.exe tools\measure_fused_ceiling.py --mouth-res 4.46 --flag on
.venv\Scripts\python.exe tools\measure_fused_ceiling.py --mouth-res 4.09 --flag on
```

The 12,000 verify/final caps and the "20k refuses" predicate were set on the old solver and are plausibly stale by
1.5-2x; do not raise either before this sweep.

## 6. Mesher check (0 GPU-minutes, 3 commands)

```powershell
git -C C:\Users\hunte\Hrns\forks\hornlab-waveguide-mesher fetch https://github.com/jamescollinharky/hornlab-waveguide-mesher.git hornlab-search/osse-midports
git -C C:\Users\hunte\Hrns\forks\hornlab-waveguide-mesher merge-base --is-ancestor d740c28 55da4f46
echo $LASTEXITCODE   # 0 = the upstream FREEFORM cost fix is already in the pin; question closed
```

Note the remotes differ: the local checkout's `origin` is upstream `m3gnus` (main `4573bc9`, contains `d740c28`), while
the pin lives on `jamescollinharky`'s fork (HEAD `55da4f46`). Fetch across both.

If the pin predates the fix **and** a live typology is FREEFORM: build that one design at the pin and at a
fix-containing build, compare DOF / triangles / edge stats / build seconds (`mesh_policy_study.py` + `mesh_fidelity.py`,
mesh-only). If the meshes differ, that is a fidelity-correctness question, and a mesher bump becomes its own program:
it invalidates every mesh hash, every solve cache, the dataset `lib_sha` and strict resumes.

## 7. Do not do

- No fidelity trades: quadrature order, rear-shell density, coarser epw/angles/frequencies, FP32 Krylov, reduced-order
  sweeps, UI fidelity selector. All excluded by the owner's rule.
- No `pip install` inside a night job; no editable installs; no hand-editing `.venv`.
- Never kill `julia.exe` by image name; never compare VRAM on a warm host.
- Never resume or start the paused run **after** the solver swap (the code refuses mixed-version resumes).
- Do not use `selftest --analytic` as fused-path parity — it never sets `cuda_fused`.
- Do not re-base the A5 20k refusal test on arithmetic; wait for the measured point.
- Do not bundle a mesher bump with the solver merge.
- Do not queue the GPU rerun night before adoption.

## 8. One page for the owner

**What we will do.** One evening, six small steps: finish the search we paused today (so its paid-for candidates are
not stranded); write one small second improvement into our copy of the solver (it stops building two giant lookup
tables on the main memory side too — same idea as part one); measure today's solver on two real horns as a baseline;
swap in the new solver; measure it with "12 frequencies at a time" on and off; then probe how big a mesh now fits.

**Expected gain.** Already measured for part one: 55-70 % less GPU memory and 20-30 % less time per frequency. Batching
history says 2-4x on the setup part. Realistically a **1.5-3x faster whole search**, and possibly a much larger model
ceiling - bigger, more trustworthy verify runs on the same 8 GB card, with no loss of resolution.

**What could go wrong.** The two changes could interact badly (batching keeps memory alive) - that is exactly what the
trial measures, and "4 at a time" is the built-in fallback. The new solver could produce slightly different audio
numbers - checked against a hard bar (0.039 dB / 1 degree); fail means no merge. The ceiling probe may find a low
limit - a result, still useful.

**Cost.** ~45-60 GPU-minutes, one evening of writing/testing for part two (no GPU), one adoption commit, and a
two-minute undo.

**The single decision:** approve the trial. If it passes the pre-declared bars, the merge happens as written, including
switching searches to 12 frequencies per request as a visible, recorded setting.
