# CP-8c — multi-family dataset (IN PROGRESS)

Plan (HANDOFF_LOCAL §5): one config at a time, bigger budgets, GPU hygiene before/after,
`dataset stats` + `dataset verify` at the end. Raw artifacts are local (gitignored); see
`README.md`.

## Run 1 of 4 — `osse_baseline` (budget 1500) — running

- Run id: `runs/20261013T123136Z-screen-ca15be` (gitignored)
- Command: `hornlab-search search --config examples\osse_baseline.yaml --budget 1500`
- Started 2026-10-13T12:31:55Z (08:31 local). Hygiene before: no julia, VRAM 419 MiB.
- `run.json` records the widened bounds (`a_deg lo 5`, `exponent lo 1`) and the lib SHAs;
  its `config_sha` = `830f2877c73d` (the committed `examples/osse_baseline.yaml`).

Snapshot at 13:11 local (988 rows, run still active):
```
rows=988 ok=893 failed=95 torn=0 kinds={'mesh_too_large': 93, 'invalid_geometry': 2}
ok-J: min=6.11 median=7.34 max=180.45 best=6.11        (seed J 22.07 -> best 72% lower)
median seconds: solve=18.05 mesh=1.81 total=18.89
rate=213 rows/h (4.65 h)   ok rows with metrics=null: 0
top design_hash dups: all count=1
last-ok: n=987 J=6.131 a_deg=14.39 exponent=2.56 a0_deg=22.49 L_mm=396.3 n_dof=4205
```
Best design is interior (`exponent 2.24–3.19`, `a_deg 7.2–14.4`), i.e. the CP-8b widening is
being used without re-pinning.

Dataset totals at 13:13 local (all families still pooled in one store):
```
records 1128 (ok 1018, failed 110), shards 3, 180.6 MB
families {'OSSE': 1128, 'R-OSSE': 0, 'ICW': 0, 'FREEFORM': 0}
traces 4.2% of records, gpu solve seconds 15671.7
WARNING: dataset is 100% OSSE (1128/1128)
```

## Live monitoring (this run)

- `logs/cp8c_watchdog.txt` — 5-minute snapshots (separate process): rows, last kind/J, VRAM,
  process counts. Append-only while runs are active.
- `logs/cp8c_ticks.txt` — 30-minute review ticks with STALL / JUNK / HYGIENE / PROGRESS verdicts.
- Ticks reviewed so far: 3, all clear (no stall, no junk, single `julia` host, VRAM ≤ 4.3 GiB).
- Health script: `health_check.py` (temp, read-only; summarises rows/ok/fail/kinds/J/timing/dups).

## Remaining runs (planned)

`icw_termination` 800 · `freeform_hv` 800 · `throat_adapter` 400, one GPU job at a time, each
with hygiene + `dataset stats` + a CONTINUITY entry. `dataset verify` runs at the end (CP-8c pass
= verify OK + all four families present).

Expected CP-8d effect: pooling `search_smoke` (500–4500 Hz grid) with `osse_baseline`
(500–5500 Hz) silently drops the search_smoke records (issue #13, M1), so the OSSE held-out
count comes from `osse_baseline` records alone (~15% × 1500 ≈ 225 < 500) → the gate refuses and
the Stage A result will be reported as **indicative only**.

Final numbers for this run are appended here when it completes.
