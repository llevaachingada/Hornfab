# Integration handback — 12 kHz SCREEN pass (2026-11-23)

For the shared integrator. Nothing here is committed; the working tree already carried other
agents' uncommitted changes, so stage per-hunk.

## Files this pass changed

| File | Nature | Notes |
|---|---|---|
| `hornlab_search/config.py` | **feature** | `SCREEN_GRID_PROFILES` + `solve.screen_grid` (screen-only), loader validation and mutual-exclusion refusals. Absent key → every existing grid/hash byte-identical. |
| `hornlab_search/search/warmstart.py` | **bug fix** | `_grid_key` guard: warm start now refuses a source run whose `solve.screen_grid`/`solve.freq_grid` differs (the brief payload never carried them, so J from a different grid could seed a run). Both-absent stays byte-identical. |
| `tests/test_config_screen_grid.py` | new | 8 tests: identity, screen-only scope, band refusal, forms, mutual exclusion, round-trip. |
| `tests/test_bench_screen_grid_ab.py` | new | 7 tests: arm nesting/HF coverage, Spearman, HF flags, CSV contract, synthetic end-to-end measure, analysis tables. |
| `tests/test_search_warmstart.py` | +2 tests | `_grid_key` unit + mismatch refusal/override. |
| `tools/bench/screen_grid_ab.py` | new tool | `baseline` / `plan` / `preflight` / `measure` / `measure-epw` / `analyze` / `report` / `identity`. |
| `docs/evidence/screen_12k_2026-11-23/**` | new evidence | README, ADOPTION_DECISION, baseline CSV, experiment configs/manifest, and the CSVs the queued jobs write. |

Not touched: `hornlab_search/mesh/**`, `hornlab_search/design/families.py`, the mesher's sizing
algorithms, `FREQ_GRIDS`, `solve.freq_grid` semantics, any objective formula/weight.

## Verification (offline, run before staging)

```powershell
.venv\Scripts\python.exe -m pytest tests/test_config_screen_grid.py tests/test_bench_screen_grid_ab.py `
  tests/test_search_warmstart.py tests/test_config.py -q
# expected: 75 passed
.venv\Scripts\python.exe tools\bench\screen_grid_ab.py baseline --dataset dataset --since-days 10 `
  --out docs\evidence\screen_12k_2026-11-23\SCREEN_BASELINE.csv
```

## What to write into the shared living docs (I do not edit them)

**`docs/ACTIVE_STATE.md`** — new top block:

> **2026-11-23 (HF screen pass):** `solve.screen_grid` (new, screen-only) + `hf12k_screen_v1`
> profile (500–12000, 19 pts) implemented; warm-start grid-identity guard added. Audit: no SCREEN
> row in the last 10 days solved above 10 kHz — the active v11 briefs clip the screen to 8 kHz
> (17 101 of 17 509 screen rows). The deployed top is 8 kHz, not 10 kHz. 168-eval 10k-vs-12k A/B
> (4 cohorts × 6 designs × 7 arms + epw 5/6/8) is queued after `v11_bo_day_core_2026-11-23`;
> decision rule pre-registered in `docs/evidence/screen_12k_2026-11-23/ADOPTION_DECISION.md`.

**`docs/ISSUES.md`** — new entry:

> HF screen policy: `solve.freq_grid` replaces EVERY mode's grid (legacy; `meh_*` depends on it),
> which is why a screen-only key exists. `FREQ_GRIDS["screen"]` still tops out at 10 kHz and
> `band_hi` is only ever clipped downward, so `band_hi_hz: 12000` alone is a no-op for screen.
> v11 CD bands must be extended explicitly or ~47 % of J weight ignores 8–12 kHz. Warm start
> previously ignored `solve.*grid` (fixed). MEH walls at a 12 kHz request validate only ~6 kHz —
> MEH is not eligible for the 12 kHz screen class until mesh diagnostics say otherwise.

## Promoting the result (only after ADOPTION_DECISION says so)

1. Add the winning frozen list to `SCREEN_GRID_PROFILES` (data-only change).
2. Make eligibility explicit at the brief or run config:
   `solve: {screen_grid: {profile: <winner>}}` — never edit `FREQ_GRIDS["screen"]`.
3. If the winner is an additive/hybrid list, name it for its band, not its point count.
4. Record the resolved `solve.freqs_hz` + `mesh_hash` in the handback; the dataset already stores
   them per row, so a re-ranking audit needs no new fields.
5. Rollback is deleting the `screen_grid` block: no stored grid, hash or score changes.

## Coordination notes

* **Timing lesson from the first pass (2026-11-24):** a per-cohort job needs ~2 h, not 20 min.
  The sampled designs reach 18.4 k quarter DOF at 12 kHz (the old cohorts were ~4 k), so a single
  12 kHz evaluation is 39–255 s and a 42-evaluation cohort exceeds a 3600 s timeout. The
  completion jobs use 5400–7200 s. Any future suite should size timeouts from the measured
  `wall_s` in `measurements.csv`, not from the baseline screen.
* The live night file `runs/nights/v11_bo_day_core_2026-11-23.yaml` is edited by more than one
  writer; my jobs (`screen12k_*`, appended at the end) can be dropped by a concurrent rewrite.
  If they are missing, re-append the block (backups: `...yaml.bak_pre_screen12k`,
  `...yaml.bak2_pre_completion`).
* The measurement jobs take `runs/.gpu.lock` with `HORNLAB_GPU_LOCK=refuse` (exit 3 if busy) and
  use their own cache/dataset under `docs/evidence/screen_12k_2026-11-23/experiment/`, so they
  cannot contaminate the production dataset or cohorts.
