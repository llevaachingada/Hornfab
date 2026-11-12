# Night report — PARTIAL (2026-11-12)

**STATUS: PARTIAL.** `gpu_day_2026-11-12_cont` has only `g1b`/`g1c` recorded; `g2`–`g9` are still
queued. `c2b_verify_core_law_top10` exited 1 after two BEAT worker `ConnectionResetError` failures
(designs `abca65c68a1a`, `8c42018fe94a`); the `blocked` status is the CPU lane's expected GPU-busy
pre-hygiene line, not a GPU problem. The final night report will supersede this after the queue
finishes. No GPU/solver was run for this report; it is read-only from summaries and run dirs.

---

# Night report: gpu_2026-11-12, gpu_day_2026-11-12, cpu_day_2026-11-12, gpu_day_2026-11-12_cont, cpu_day_2026-11-12_cont

Generated 2026-11-12T20:53:47Z by `tools/night_report.py` (read-only). [measured] = read from summary.jsonl / job logs / run dirs; [inferred] = derived from measured numbers. J is comparable only within a brief.

## Night `gpu_2026-11-12`

[measured] rows: 17 summary row(s) in `nights\gpu_2026-11-12\summary.jsonl` (C:\Users\hunte\Hrns\hornlab-search\runs\nights\gpu_2026-11-12).

| lane | id | kind | status | exit | attempts | evals | best J | wall s | run dir | valid/refused |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|
| gpu | `n1_1k_fusedon_prefetchoff` | ? | ok | 0 | 1 | 0 | n/a | 131 | n/a | n/a |
| gpu | `n1_1k_fusedoff_prefetchoff` | ? | ok | 0 | 1 | 0 | n/a | 142 | n/a | n/a |
| gpu | `n1_1k_fusedon_prefetchon` | ? | ok | 0 | 1 | 0 | n/a | 120 | n/a | n/a |
| gpu | `n1_1k_fusedoff_prefetchon` | ? | ok | 0 | 1 | 0 | n/a | 141 | n/a | n/a |
| gpu | `n1_4k_fusedon_prefetchoff` | ? | ok | 0 | 1 | 0 | n/a | 233 | n/a | n/a |
| gpu | `n1_4k_fusedoff_prefetchoff` | ? | ok | 0 | 1 | 0 | n/a | 281 | n/a | n/a |
| gpu | `n1_4k_fusedon_prefetchon` | ? | ok | 0 | 1 | 0 | n/a | 235 | n/a | n/a |
| gpu | `n1_4k_fusedoff_prefetchon` | ? | ok | 0 | 1 | 0 | n/a | 315 | n/a | n/a |
| gpu | `n1_8k_fusedon_prefetchoff` | ? | ok | 0 | 1 | 0 | n/a | 503 | n/a | n/a |
| gpu | `n1_8k_fusedoff_prefetchoff` | ? | ok | 0 | 1 | 0 | n/a | 318 | n/a | n/a |
| gpu | `n1_8k_fusedon_prefetchon` | ? | ok | 0 | 1 | 0 | n/a | 505 | n/a | n/a |
| gpu | `n1_8k_fusedoff_prefetchon` | ? | failed | 1 | 1 | 0 | n/a | 327 | n/a | n/a |
| gpu | `n3_core_atlas_resume` | ? | ok | 0 | 1 | 0 | n/a | 8249 | n/a | n/a |
| gpu | `n4_ext_throat_atlas` | ? | ok | 0 | 1 | 201 | 6.6361 | 1759 | C:\Users\hunte\Hrns\hornlab-search\runs\20261112T110126Z-screen-c414b1 | 140/61 |
| gpu | `n5_lecleach_v6` | ? | ok | 0 | 1 | 0 | n/a | 786 | n/a | n/a |
| gpu | `n7_staged_ab` | ? | failed | 1 | 1 | 0 | n/a | 2 | n/a | n/a |
| gpu | `n6_verify_core_atlas` | ? | ok | 0 | 1 | 0 | n/a | 213 | n/a | n/a |

### lane gpu

[measured] jobs: 17; exits: failed 2, ok 15
[measured] evals (from run dirs, not budgets): 201; wall time: 237.7 min; [measured] valid 140 / refused 61 rows; [measured] VRAM peak max 7731 MiB; after max 1119 MiB
[inferred] evals/hour: 50.7 (evals / wall time)

Blocked/failed jobs (2) with their first error line:
- `n1_8k_fusedoff_prefetchon` [~failed (inferred)]: beat solve failed [cuda_oom]: Traceback (most recent call last):
- `n7_staged_ab` [~failed (inferred)]: (no error line in log)

## Night `gpu_day_2026-11-12`

[measured] rows: 1 summary row(s) in `nights\gpu_day_2026-11-12\summary.jsonl` (C:\Users\hunte\Hrns\hornlab-search\runs\nights\gpu_day_2026-11-12).

| lane | id | kind | status | exit | attempts | evals | best J | wall s | run dir | valid/refused |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|
| gpu | `g0_xcheck_gpu` | ? | ok | 0 | 1 | 8 | n/a | 19 | C:\Users\hunte\Hrns\hornlab-search\runs\20261030T111108Z-screen-377bbe\verify | 18/0 |

### lane gpu

[measured] jobs: 1; exits: ok 1
[measured] evals (from run dirs, not budgets): 8; wall time: 0.3 min; [measured] valid 18 / refused 0 rows; [measured] VRAM peak max 647 MiB; after max 488 MiB
[inferred] evals/hour: 1519.5 (evals / wall time)

## Night `cpu_day_2026-11-12`

[measured] rows: 3 summary row(s) in `nights\cpu_day_2026-11-12\summary.jsonl` (C:\Users\hunte\Hrns\hornlab-search\runs\nights\cpu_day_2026-11-12).

| lane | id | kind | status | exit | attempts | evals | best J | wall s | run dir | valid/refused |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|
| cpu | `c1_xcheck_cpu` | ? | ok | 0 | 1 | 13 | n/a | 577 | C:\Users\hunte\Hrns\hornlab-search\runs\20261030T111108Z-screen-377bbe\verify | 18/0 |
| cpu | `c2_lecleach_v6_seed1236` | ? | ok | 0 | 1 | 200 | 0.831889 | 1232 | C:\Users\hunte\Hrns\hornlab-search\runs\20261112T144510Z-screen-00cf9c | 186/14 |
| cpu | `c3_verify_hypex_elites` | ? | ok | 0 | 1 | 34 | n/a | 3041 | C:\Users\hunte\Hrns\hornlab-search\runs\elites_20261030_hypex\verify | 34/0 |

### lane cpu

[measured] jobs: 3; exits: ok 3
[measured] evals (from run dirs, not budgets): 247; wall time: 80.8 min; [measured] valid 238 / refused 14 rows; [measured] VRAM peaks: none recorded
[inferred] evals/hour: 183.3 (evals / wall time)

## Night `gpu_day_2026-11-12_cont`

[measured] rows: 2 summary row(s) in `nights\gpu_day_2026-11-12_cont\summary.jsonl` (C:\Users\hunte\Hrns\hornlab-search\runs\nights\gpu_day_2026-11-12_cont).

| lane | id | kind | status | exit | attempts | evals | best J | wall s | run dir | valid/refused |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|
| gpu | `g1b_core_law_resume_tail` | ? | ok | 0 | 1 | 1001 | 2.12827 | 5229 | C:\Users\hunte\Hrns\hornlab-search\runs\20261030T170642Z-screen-fbab4f | 567/434 |
| gpu | `g1c_verify_core_law_top10` | ? | ok | 0 | 1 | 17 | n/a | 1299 | C:\Users\hunte\Hrns\hornlab-search\runs\20261030T170642Z-screen-fbab4f\verify | 17/3 |

### lane gpu

[measured] jobs: 2; exits: ok 2
[measured] evals (from run dirs, not budgets): 1018; wall time: 108.8 min; [measured] valid 584 / refused 437 rows; [measured] VRAM peak max 3665 MiB; after max 1109 MiB
[inferred] evals/hour: 561.4 (evals / wall time)

## Night `cpu_day_2026-11-12_cont`

[measured] rows: 2 summary row(s) in `nights\cpu_day_2026-11-12_cont\summary.jsonl` (C:\Users\hunte\Hrns\hornlab-search\runs\nights\cpu_day_2026-11-12_cont).

| lane | id | kind | status | exit | attempts | evals | best J | wall s | run dir | valid/refused |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|
| cpu | `c1b_verify_ath_core_top10` | ? | ok | 0 | 1 | 18 | n/a | 1473 | C:\Users\hunte\Hrns\hornlab-search\runs\20261030T111108Z-screen-377bbe\verify | 18/0 |
| cpu | `c2b_verify_core_law_top10` | ? | blocked | 1 | 1 | 20 | n/a | 5651 | C:\Users\hunte\Hrns\hornlab-search\runs\20261030T170642Z-screen-fbab4f\verify | 17/3 |

### lane cpu

[measured] jobs: 2; exits: blocked 1, ok 1
[measured] evals (from run dirs, not budgets): 38; wall time: 118.7 min; [measured] valid 35 / refused 3 rows; [measured] VRAM peaks: none recorded
[inferred] evals/hour: 19.2 (evals / wall time)

Blocked/failed jobs (1) with their first error line:
- `c2b_verify_core_law_top10` [~blocked (inferred)]: GPU busy: hunte running "hornlab-search search --resume runs/20261030T170642Z-screen-fbab4f --budget 117 --mode screen" (pid 14152) since 2026-11-12T13:13:20
