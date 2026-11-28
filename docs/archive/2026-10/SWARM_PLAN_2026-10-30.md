# Swarm implementation plan — 2026-10-30 (runs while night `n2_gapfill_2026-10-30` is live)

For an orchestrator agent that dispatches sub-agents. Read `CLAUDE.md` first, then this file, then only your own
lane. Context: `docs/HANDOFF_NEXT_RUNS_2026-10-30.md` (coverage-atlas results) and `docs/DATA_CONSOLIDATION_PLAN_2026-10-29.md`.

## 0. Rules while the night runs (binding for every lane)

- Night `n2_gapfill_2026-10-30` is live (controller pid 13292, log `runs/nights/queue_2026-10-30_night2.log`).
  **No GPU work, no `hornlab-search run|search|verify`, no `run --dry-run`, no pytest with slow/gpu/crosscheck
  markers, never kill `julia.exe`.** CPU-only work: code, offline tests
  (`.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" <your tests>`),
  `tools/shape_check.py`, `tools/rescore/gate_audit.py`, docs.
- Do not edit any config or brief the night uses: everything under `examples/typologies/atlas_2026-10-30/`
  and `examples/briefs/atlas_2026-10-30/`. Copy them instead.
- **File ownership is exclusive per lane (table in §2).** If you need a file you don't own, write the request in
  `NOTES_FOR_SENIOR.md` and keep going.
- Each lane works on its own branch `swarm/<lane>-2026-10-30` from `feat/hardened-plan-2026-10-29`. The
  orchestrator merges, and every pushed commit updates `docs/CONTINUITY.md` and `docs/ISSUES.md`.
- Interpreter: `.venv\Scripts\python.exe` only.

## 1. What went wrong, and which lane fixes it

| # | Problem (measured 2026-10-29/30) | Lane |
|---|---|---|
| P1 | Gates judge every horn against the brief's angle. 45 stored designs pass that way, but 150 pass against their own natural coverage; 20 of 25 atlas elites "failed" verify only on angle | **A** |
| P2 | `verify` can only re-solve a run's top-N by J, so elites needed hand-built run dirs | **B** |
| P3 | The atlas cells (v4 briefs) screen at **12 frequencies** (only the v5 briefs carry the 18-point `grid.screen_extra_hz`). There are ~3 samples in 1.8–3 kHz, where the H waist lives, so J rose 2.75 → 3.79 at verify | **C** |
| P4 | The GPU is ~4% busy (~140 MB per solve); one search at a time. The CPU second lane is researched but not built | **D** (CPU lane), **E** (multi-candidate GPU) |
| P5 | Every objective generation copies every config (no `extends:`); fused-CUDA and debug variants are listed as typologies | **F** |
| P6 | Verify failures are now V lobing above 3 kHz and loading below F_X: a shape problem, with no family targeting it | **G** (research, no code) |
| P7 | The dataset doesn't record which run or typology produced a record, which blocks typology-level keepers and surrogate conditioning | **H** |

## 2. Lanes, ownership, dependencies

All lanes except D-tail and E-measure can start now, in parallel.

| Lane | Owns (exclusive) | Depends on | Size |
|---|---|---|---|
| **A** self-referenced gates | `tools/rescore/gate_audit.py`, `tests/test_tools_gate_audit.py`, new `tools/atlas/` (readout, promoted from `scratch/atlas_2026-10-30/readout.py`), `tests/test_tools_atlas_*.py` | none | S |
| **B** `verify --designs` | `hornlab_search/cli.py` (the verify parser and `_verify_body` only), `tests/test_cli_verify_designs.py` | none | S |
| **C** 18+4 screen grid | new `examples/briefs/atlas_v2_2026-10-31/`, new `examples/typologies/atlas_v2_2026-10-31/` | none (YAML only); uses F's `extends` if it lands first, otherwise plain copies | S |
| **D** CPU second lane | `hornlab_search/search/gpulock.py`, `hornlab_search/search/hygiene.py`, `tools/run_campaign_night.py`, `tools/night_queue/*`, `tests/test_search_gpulock*.py`, `tests/test_tools_night_runner.py`, `docs/research/CPU_SECOND_LANE_HARDENING_2026-10-28.md` (status line) | B (both touch `cli.py`): D's `gpu-clean` change goes in **after** B merges | M |
| **E** multi-candidate GPU (design spike) | new `docs/research/GPU_BATCH_EVAL_2026-10-30.md` only | none | S (doc) |
| **F** config `extends:` + profiles | `hornlab_search/config.py`, `tests/test_config*.py`, new `examples/profiles/` | none | M |
| **G** shape research | new `docs/research/V_LOBING_LOADING_2026-10-30.md` | none; runs the `hornlab-typology-research` skill | M (doc) |
| **H** record provenance | `hornlab_search/dataset/record.py`, `hornlab_search/search/evaluate.py` (the provenance block only), `tools/data/keepers.py`, `tests/test_dataset_*.py` | none | S |

Suggested swarm: wave 1 runs A, B, C, E, F, G and H in parallel (7 sub-agents). Wave 2 is D (after B) plus
the orchestrator's merge, offline full suite and launch prep.

## 3. Lane specs

### A — gate against each horn's own coverage (fixes P1)
- `gate_audit.py --nominal {brief,own}` (default `brief`, so today's output is byte-identical). With `own`:
  - nominal H is the median `bw_h` over `[F_X, BAND_HI]`;
  - nominal V is the median `bw_v` over `[max(1.5·F_X, f0_v), BAND_HI]`;
  - the H and V tolerances are unchanged (±20 %, 0.6–1.25);
  - BW8K uses the same nominals;
  - DI, Loading and Throat are unchanged.
  - Add CSV columns `nominal_h_deg`, `nominal_v_deg`, `nominal_mode`, and add the mode to the README header.
- Promote the readout to `tools/atlas/readout.py`: args `--audit <csv> --out <csv>`, a cell size option
  (default 10°), and preference "self-pass, then lower J". Use verify rows when present: gate_audit already
  replaces screen rows with verify rows.
- Tests: synthetic rows covering a 61×40 horn under a 60×40 brief (passes both), a 75×50 horn under 60×40
  (fails `brief`, passes `own`) and a horn with a waist (fails both); `--nominal brief` matches a golden CSV.
- Accept: re-run on `docs/data/gate_audit_2026-10-29*` with `own` and reproduce the
  45 → 150 count to within ±2. The scratch method differs slightly because BW8K now uses the nominals, so
  document any difference.

### B — `verify --designs` (fixes P2)
- `hornlab-search verify --run <dir> --designs h1,h2,...` (mutually exclusive with `--top`) re-solves exactly
  those design hashes from `search.ndjson` and writes to `<run>/verify/` as today. An unknown hash is a hard
  error that lists the missing hashes.
- Also add `--designs-file <csv>`, which reads a `design` column (so `atlas_elites.csv` feeds it directly).
- Tests: offline, with the backend stubbed the way the existing verify tests do. Check selection, the
  mutual-exclusion error and the unknown-hash error. No solver.

### C — denser screen grid for atlas v2 (fixes P3)
- Make copies of the three atlas briefs (b2w big, native_ath_core_2in_v4, and the core-law brief) under
  `examples/briefs/atlas_v2_2026-10-31/`. Add `grid.screen_extra_hz` to each, giving
  - the v5 18-point set's low-end points that fall inside the brief band, plus
  - **4 extra points across 1.8–3.2 kHz** (1850, 2150, 2500, 2900 Hz; skip any within 3 % of an existing sample).
- Make config copies under `examples/typologies/atlas_v2_2026-10-31/`: same knobs, `search` the same as the
  atlas, `seed` 1031, pointing at the v2 briefs.
- This changes the solve hash, so it is a new cache. Expect ~1.3–1.5× time per eval.
- Accept: `load_config` OK for each; `tools/shape_check.py` OK (CPU); a table in the PR of the screen grids
  before and after, listing each frequency.

### D — CPU second lane (fixes P4, part 1)
- Implement the research doc's Option B with its §12 defaults (owner approved "keep the GPU running" and "put
  way more solve on this machine" on 2026-10-30):
  - backend-aware lock: `beat_cuda` takes `runs/.gpu.lock`, CPU backends take `runs/.cpu.lane.lock`;
  - `.cpu.lane.lock` marker;
  - `gpu-clean` and night-runner hygiene kill only the Julia hosts of their own lane (lane identity through
    the registry dir, H1; unknown means never kill, D4);
  - `solve.julia_threads` knob kept out of the solve hash (H9);
  - drop `cuda_fused` for non-CUDA backends (H2);
  - separate `--cache-dir` and `--dataset-dir` for the CPU lane.
- Tests: offline lock/hygiene unit tests. Nothing starts Julia.
- **Measurement gate (after the night ends, not before):** run one 20-eval CPU search next to one 20-eval GPU
  search. Accept when neither crashes, GPU s/eval degrades by at most 15 %, and total evals per hour is at
  least 1.4× single-lane. Record it as evidence via the `hornlab-evidence` skill.

### E — multi-candidate GPU evaluation (fixes P4, part 2; design only now)
- Write `docs/research/GPU_BATCH_EVAL_2026-10-30.md`. Read `search/evaluate.py`, `solve/worker.py` and
  `solve/beat.py` (the persistent host), then propose either N concurrent hosts with a VRAM budget, or
  per-frequency batching inside one host. Give the expected speedup, using the measured ~140 MB/solve,
  ~1 GB/host and 8 GB card, plus the failure modes from CLAUDE.md GPU hygiene and a measurement ladder.
- No code until the owner picks an option.

### F — `extends:` and profiles (fixes P5)
- Add `extends: <path or list>` to configs and briefs: deep merge, child wins, paths relative to the file.
  It is resolved **before** `config_sha` and the solve hash. Goldens in `tests/test_config*.py` must not change.
- Add `examples/profiles/fused_cuda.yaml` (`solve.cuda_fused: true`, dof caps 12000) and
  `examples/profiles/objective_v4.yaml` / `objective_v5.yaml`, holding the objective block shared by the
  campaign briefs.
- Tests:
  - a config written with `extends:` loads to the same `Config` and `config_sha` as its flat copy, for
    3 real cells;
  - cycle detection;
  - a missing file gives an error with the chain.
- Do not migrate existing files in this lane. Migration is a follow-up.

### G — research: vertical lobing above 3 kHz and low-end loading (fixes P6)
- Run the `hornlab-typology-research` skill. Inputs:
  - the verify failures in `scratch/gate_audit_elites_2026-10-30/gate_audit.csv`;
  - the hybrid V maps (lobes and nulls above 3 kHz at −15 dB and below);
  - ATH CORE's 99 % loading pass rate against the hybrid's 51 %.
- Output: 2–3 concrete shape-law changes inside existing generators (e.g. V-profile throat-tangent matching,
  mouth roll-back on the V axis, `h_s`/`v_T` ranges), each with sources, the expected effect and knob ranges.
  Every one must be expressible as new atlas configs without generator code if possible.

### H — record provenance (fixes P7)
- Add optional record fields `run_id`, `config_name` and `typology` (the generator spec name, or the family for
  native). Absent keys are omitted, so schema v1 readers are unaffected.
- Make `tools/data/keepers.py` backfill those fields for old records by joining
  `runs/*/search.ndjson` (design_hash and solve key) with `runs/*/config.yaml` `name`.
- Tests: record round-trip with and without the fields; backfill on a synthetic two-run tree.

## 4. Orchestrator merge and verification (CPU, while the night still runs)

1. Merge in this order: A, B, H, F, C, then D. E and G are docs.
2. Run the offline suite (`-m "not slow and not gpu and not crosscheck"`). Its only expected failure is the
   known `test_mesh_pin` tripwire, if present.
3. Re-run `gate_audit --nominal own` on the atlas runs plus the elite dirs, and `tools/atlas/readout.py`.
   This becomes the real scorecard for the 20 elites that "failed" on angle.
4. Update CONTINUITY and ISSUES, then push.

## 5. Next run (launch when `n2_gapfill_2026-10-30` has finished; check its log)

Pre-flight per the `hornlab-night-queue` skill: no Julia, no live runner, `nvidia-smi` baseline. Then:

**Night `n3_atlas_v2` (GPU lane):**
1. `verify --designs-file` on the self-passing elites of every atlas run, using `atlas_elites.csv` filtered to
   `pass_self` and including the CORE-law, `osse_ext_throat` and extended runs (lane B).
2. Atlas v2 on the hybrid, budget 600, 18+4-point grid (lane C).
3. Atlas v2 on ATH CORE, budget 400.
4. Close-out: `gate_audit --nominal own` over the v2 runs and elites, `tools/atlas/readout.py`, and render cards
   of the verified self-passes (`hornlab-render` skill, stack layout with `--loudness`).

**CPU lane (only if lane D's measurement gate passed):** run, in parallel with n3,
`atlas_v2` on `osse_ext_throat` with `--backend beat_cpu`, budget 150, `--cache-dir cache_cpu`,
`--dataset-dir dataset_cpu`.

**If lane G produced shape-law proposals:** add one atlas per proposal (budget 300) at the end of n3, each
shape-checked first.

Launch detached (`tools\night_queue\launch_detached.ps1` + `queue.ps1`), with no cutoff or one set to the
owner's wake time. Verify within a minute: a Julia host is up and the run's `search.ndjson` is gaining rows.
Record it in CONTINUITY.
