# Speed-program adoption evidence — 2026-11-13/14 night

Campaign executed 2026-11-13 18:32Z → 2026-11-14 01:58Z on the RTX 4060 8 GB, canonical checkout
`C:\Users\hunte\Hrns\hornlab-search`. Design authority: `docs/queue/SPEED_ARCHITECTURE_PLAN_2026-11-13.md`
(§14 verdict) + `docs/queue/SPEED_IMPLEMENTATION_PROMPT_2026-11-13.md` (rev B). Every number below is pasted
from machine artifacts under `runs/` / `scratch/`; raw logs are archived as cited.

## 0. Result

**ADOPTED: solver `38e5b1f` (C1 `9ec86b0` + C2 `38e5b1f`), whole-candidate wall −24.7 % / −28.0 %, parity at
~1e-5 dB, zero spill anywhere, measured fused-CUDA memory ceiling beyond 25k quarter-DOF, A5 re-based on
measured anchors. NOT adopted: batching defaults (batch 12 and batch 4 both miss the pre-declared 0.85
whole-candidate bar; `solve.freq_batch_size` lands as a default-`None` provenance key, env var stays the
trial knob).**

## 1. E0 — interrupted run finished

`search --resume runs/20261113T193536Z-screen-81c964 --budget 45` → runner exit 0 at 2026-11-13T19:22:24Z,
**200/200 rows** (170 ok, 26 invalid_geometry, 3 mesh_too_large, **1 transient `solve_failed`** at n=187 —
10054 worker reset; the recovery re-warmed the host but did not re-attempt that design; the row stays an
honest failure per `error_policy: legacy`). Gate deviation recorded, not blocking.

## 2. E1b — fork validation evidence (rule 6: raw bytes archived)

- `docs/evidence/JULIA_CPU_SUITE_38e5b1f_2026-11-13.log` — **45 testsets, 3830 pass / 0 fail / 4 broken**
  (the four CUDA-gated testsets; CUDA is not a project dependency there), `SUITE_EXIT=0`. Matches the
  integrator's earlier attestation exactly. First attempt archived 0 bytes: julia.exe's Windows wrapper
  does not carry `Start-Process` redirections; re-run under `cmd /c` with inline exit stamps.
- `docs/evidence/ANALYTIC_EXTERIOR_38e5b1f_2026-11-13.log` — `ANALYTIC_EXTERIOR_VALIDATION_OK`,
  `ANALYTIC_EXIT=0`, controls failing as required.

## 3. E3/E5 — arms (both designs; `--budget 1` = seed candidate; per-arm cold caches)

Primary metric: `run.json.stats.mean_seconds_per_candidate` (whole-candidate wall). Configs identical per
design across rounds (`config_sha` osse `612cd342c8d4`, ath `7f2abdfa2c7a`); same mesh both
designs-of-record (dof 6,262 / 8,007; 18 screen frequencies 250–8,000 Hz).

| arm | pin | batch | mean s/cand | run dir |
|---|---|---|---:|---|
| base_b1_osse | 0850ef39 | 1 | 54.47 | `runs/20261114T011835Z-screen-5ca21d` |
| base_b1_ath | 0850ef39 | 1 | 83.77 | `runs/20261114T011952Z-screen-1f0638` |
| new_b1_osse | 38e5b1f | 1 | 41.03 | `runs/20261114T012458Z-screen-39178b` |
| new_b12_osse | 38e5b1f | 12 | 34.81 | `runs/20261114T012626Z-screen-b62d5e` |
| new_b1_ath | 38e5b1f | 1 | 60.32 | `runs/20261114T012724Z-screen-0a75f7` |
| new_b12_ath | 38e5b1f | 12 | 52.28 | `runs/20261114T012845Z-screen-8c7e61` |
| new_b1_osse_rep2 | 38e5b1f | 1 | 39.94 | `runs/20261114T013443Z-screen-e078ef` |
| new_b12_osse_rep2 | 38e5b1f | 12 | 34.11 | `runs/20261114T013348Z-screen-419d71` |
| new_b1_ath_rep2 | 38e5b1f | 1 | 61.74 | `runs/20261114T013700Z-screen-273477` |
| new_b12_ath_rep2 | 38e5b1f | 12 | 53.34 | `runs/20261114T013543Z-screen-75736b` |
| new_b4_osse | 38e5b1f | 4 | 35.51 | `runs/20261114T014113Z-screen-a8076a` |
| new_b4_ath | 38e5b1f | 4 | 55.72 | `runs/20261114T014210Z-screen-5be7f6` |

All arms `ok: true`, best J bit-consistent (osse 5.97654 / ath 17.6856), identical `solve_hash`
(`ca3243f60c10`) — the per-frequency results agree across pins, batches and repeats.

## 4. Parity (I1) — PASS with ~3 orders of margin

`hornlab-search compare <base> <new_b1>` (report-only; bars computed by hand; bar 0.039 dB / 1° from the
CP-7f noise floor, `docs/FORKS.md:49-51`):

| design | bw_h max | bw_v max | di_db max | on_axis max | ripple_h max | ripple_v max |
|---|---|---|---|---|---|---|
| osse | 3.575e-05° | 3.221e-05° | 1.74e-06 dB | 4.373e-05 dB | 7.476e-07 dB | 7.086e-07 dB |
| ath | 1.207e-05° | 6.282e-06° | 1.17e-06 dB | 4.22e-06 dB | 5.299e-07 dB | 4.663e-07 dB |

Nonzero-but-tiny diffs expected (metric reduction FP noise); consistent with untouched kernels.

## 5. Decision table (pre-declared bars; §3 of the implementation prompt)

| hypothesis | first-run ratio | in band [0.80,0.92]? | repeat (median of 3 arms) | verdict |
|---|---|---|---|---|
| **H1 upgrade** osse `new_b1/base_b1` | **0.7533** | no → decide | — | **PASS → ADOPT** |
| **H1 upgrade** ath | **0.7201** | no → decide | — | **PASS → ADOPT** |
| H2 batch12 osse `new_b12/new_b1` | 0.8483 | yes → repeat | medians 34.46/40.49 = **0.8512** | **REJECT** (median > 0.85) |
| H2 batch12 ath | 0.8667 | yes → repeat | medians 52.81/61.03 = **0.8653** | **REJECT** (median > 0.85) |
| H2 fallback batch4 osse | — | — | 35.51/40.49 = **0.8771** | **REJECT** |
| H2 fallback batch4 ath | — | — | 55.72/61.03 = **0.9131** | **REJECT** |
| H3 combined ≥ best single | combined arm was the best single arm on both designs | — | — | PASS (moot: H2 rejected the default) |
| **H4 ceiling 15,878 fits, zero spill** | — | — | — | **PASS — and 20,152 / 23,850 / 24,973 all fit** |

Peak dedicated VRAM (runner, nvidia-smi device): b1 arms 1,256–1,426 MiB; b12 arms 4,498–4,818 MiB (pool
across a candidate's frequency groups); b4 arms 2,098 / 2,866 MiB. Lane-wide watcher over Round B + rep2 +
b4 (1800 s window): dedicated peak 4,074 MiB, **shared peak 80 MiB, `spilled: false`**
(`scratch/speed_round_b/memwatch_round_b.json`; the shared counter is the one nvidia-smi cannot see).

Interpretation: N1's 1.9–4.7× solver-only batching win translates to only 13–15 % whole-candidate
(18 frequencies per screen candidate; host warm-up and mesh build dilute it) — exactly the conservative
bias the plan declared. The pre-declared whole-candidate bar did its job: batching is available via
`HORNLAB_FREQ_BATCH_SIZE` for owner trials but is not a default.

## 6. E6 — measured fused-CUDA ceiling (fresh process per point, gpu-clean between, memwatch-wrapped)

| mouth-res | quarter DOF | dedicated peak (×2 reps) | shared | verdict |
|---|---:|---|---|---|
| 5.03 mm | 15,878 | 2,186 / 2,108 MiB | 80 MiB | **fits** |
| 4.46 mm | 20,152 | 3,402 / 3,402 MiB | 80 MiB | **fits** |
| 4.09 mm | 23,850 | 4,682 / 4,682 MiB | 80 MiB | **fits** |
| 4.00 mm (exploratory — extension fired because 4.09 fit) | **24,973** | 5,822 MiB (device) / 5,098 MiB (pid-scoped) | 80 MiB | **fits** |

`RESULT` lines + wrapper JSONs archived under `scratch/ceiling_memwatch/` and the runs dirs. The 24,973
segment is steeper than quadratic — the A5 envelope extrapolates its slope, the conservative direction.

## 7. A5 re-base (E8)

`solve/feasibility.py`: the pin-A `FUSED_CUDA_FACTOR 4.0 × 8N²` model (refused 20,237) is replaced by the
measured piecewise-linear envelope `FUSED_CUDA_MEASURED_ANCHORS` (chord-from-origin below the first anchor,
last-segment extrapolation beyond 24,973). Verdicts (default budget 8 − 1.5 GiB, fit ≤ 0.8×budget):

| DOF | verdict | need GiB |
|---|---|---:|
| 12,000 (production caps) | fit | 1.77 |
| 20,237 (old refusal) | **fit** | 3.35 |
| 23,850 | fit | 4.57 |
| 24,973 (measured fit) | risky | 5.69 |
| 26,000 / 28,000 | refuse | 6.70 / 8.69 |

Tests re-based by fix in `tests/test_solve_feasibility.py` (20237 → fit; 24,973 → risky; 28,000 → refuse;
anchor pass-through + monotonicity). Cap values (`dof_cap_*` in profiles/configs) are owner decisions —
untouched here.

## 8. Deviations / notes

- **R6 (freeze)**: a second agent session committed to `main` during the campaign (arm `lib_shas` show
  hornlab_search `55fbf7f5` → `50b6f061` → `1671dee2`). Physics side is pinned by the beat SHA (recorded
  per arm); `hornlab_search` is not a cache-namespace lib (`solve/cache.py:46-49`). Provenance honest;
  no gate touched.
- E0's single transient `solve_failed` row (§1 above).
- The owner's GUI was open throughout (the baseline VRAM the plan subtracts).
- First E1b attempt lost output to the julia.exe wrapper redirect bug; archived 0-byte artifact removed,
  re-run archived complete.
- `hornlab-search compare` exit code is not a pass signal (report-only) — the tables above are the gates.

## 9. Rollback (unchanged, ~2 min)

`pip install --force-reinstall --no-deps "hornlab-beat-bem @ git+https://github.com/llevaachingada/hornlab-beat-bem.git@0850ef39b29d7c51f8fbb082184d3784d2ff8bef"`
+ `python -m hornlab_beat_bem.provision --backend cpu` + revert the adoption commit. A1 keeps all cache
entries; old runs keep their `lib_shas`.
