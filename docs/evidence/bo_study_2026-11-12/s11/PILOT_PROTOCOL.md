# S11 / M2 pilot manifests — protocol and validation record

**Status: PREPARE ONLY (2026-11-12).** This lane builds and validates two pilot
experiment manifests for `bo-study-v1.1` M2. It does **not** run a BEM solve,
start a job, edit a live queue, apply a dataset/config overlay, flip a default,
or touch GPU/CPU solver state. Nothing here authorizes execution.

Canonical checkout: `C:/Users/hunte/Hrns/hornlab-search` (branch `main`).
Interpreter used for every command below:
`C:/Users/hunte/Hrns/hornlab-search/.venv/Scripts/python.exe`.

---

## 1. Artifacts

| Path | Role |
|---|---|
| `tools/experiments/__init__.py` | package marker (offline experiment prep) |
| `tools/experiments/manifest.py` | manifest builder + validator + S3-style results/cost parser |
| `tests/test_tools_experiments_manifest.py` | focused offline tests (29) |
| `scratch/bo_m0/s11/pilot1_cold_vs_warm_native_ath_core_v4.yaml` | pilot 1 overlay |
| `scratch/bo_m0/s11/pilot2_verify_allocation_crease_core_law_v4.yaml` | pilot 2 overlay |
| `scratch/bo_m0/s11/built/pilot1_cold_vs_warm_native_ath_core_v4.json` | built/validated pilot 1 manifest |
| `scratch/bo_m0/s11/built/pilot2_verify_allocation_crease_core_law_v4.json` | built/validated pilot 2 manifest |

The overlays are manifest inputs, not runnable jobs and not applied configs.
`scratch/` is gitignored; these are local evidence artifacts, not commits.

### Commands

```powershell
$PY = "C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe"
& $PY tools\experiments\manifest.py build `
    --overlay scratch\bo_m0\s11\pilot1_cold_vs_warm_native_ath_core_v4.yaml `
    --out scratch\bo_m0\s11\built\pilot1_cold_vs_warm_native_ath_core_v4.json --strict
& $PY tools\experiments\manifest.py validate `
    --manifest scratch\bo_m0\s11\built\pilot1_cold_vs_warm_native_ath_core_v4.json --strict

& $PY tools\experiments\manifest.py build `
    --overlay scratch\bo_m0\s11\pilot2_verify_allocation_crease_core_law_v4.yaml `
    --out scratch\bo_m0\s11\built\pilot2_verify_allocation_crease_core_law_v4.json --strict
& $PY tools\experiments\manifest.py validate `
    --manifest scratch\bo_m0\s11\built\pilot2_verify_allocation_crease_core_law_v4.json --strict
```

All four commands returned `SUMMARY errors=0 warnings=0 ok=true`.

---

## 2. What the tool validates

`validate` reads configs/briefs through the normal `hornlab_search.config`
loader (read-only), re-hashes each input file, and checks:

1. **Schema/authorization** — `schema_version: 1`, `protocol: bo-study-v1.1`,
   `mode: prepare_only`, `execution_authorized: false`.
2. **Resolved primary physical target** — the real config + brief, config/brief
   SHA-256, config name/family/objective version, resolved target band/coverage/
   f0/frequency weights, objective tolerances, `cov_narrow_ratio 2.0`,
   `cov_below_f0 mask`, `diag_reference round`, weights, `task_config_hash`.
3. **Input hashes** — config path/content, brief path/content, seed schedule,
   budget block, arm policies and warm-source run files. A tampered or stale
   manifest fails.
4. **Budget arithmetic and protocol caps** — per arm/replicate
   `screen 18 + verify 6 = total 24`, `attempts 120`; aggregate arithmetic;
   planning-only/unauthorized aggregate.
5. **Explicit replicates and S3 pairing semantics** — seed schedule, pairing by
   seed index, `d = A - B` (negative => A better), "same seed is not shared
   candidates", resume segments are one replicate, and an alternate/randomize
   run-order note.
6. **Verification allocation** — six verify calls per arm, at most four
   finalists, reserved audit RNG seed, no duplicate/already-verified specs,
   shortfall means "verify fewer", never substitute predicted designs.
7. **Stop rules** — budget, deadline (`deadline_required: true`; null allowed
   only as an explicit placeholder), cancellation, pool exhaustion, and three
   consecutive infrastructure/solver-host failures.
8. **Lane ownership** — GPU `beat_cuda` lane is serial and never cleans another
   lane; a CPU `beat_cpu` lane must explicitly hold `runs/.cpu.lane.lock`
   (the CLI `_solve_lock` is a null context for CPU because the night runner
   owns the CPU lock).
9. **No default/objective/registration changes** — explicit false flags and a
   statement; `speedup_claimed: false`.
10. **Output reservation** — reserved paths stay under
    `scratch/bo_m0/s11/`; no live `runs/`, `cache/`, `dataset/` or `examples/`
    path; `creates_nothing: true`.
11. **CLI commands** — every command template is parsed against the *current*
    `hornlab_search.cli.build_parser()`; unknown subcommands/flags, bad choices,
    missing required flags, multiple mutually exclusive flags, shell
    metacharacters and unknown placeholders are rejected.
12. **Analysis plan** — primary endpoint, declared practical threshold labeled
    `declared_practical_threshold_not_a_speedup_claim`, paired CI/censoring
    stopping rule, hypotheses labeled `hypothesis` with falsifiers, and a
    results parser that keeps `valid`, `cheap_refusal`, `solver_failure`,
    `pipeline_failure` and `unknown` distinct and never maps failure to an
    objective value.
13. **Runtime evidence** — at least one measured local run ledger; caveats
    required; no speedup claim.
14. **Rollback/adoption** — fail/no-gain rollback list and owner adoption
    decisions with `adopt_if` and `otherwise`.

The results parser (`parse_run_outcomes`, `measure_run_cost`) mirrors the
S3 concepts in `tools/analysis/_common.py` without importing or editing that
S3-owned module. A solver failure or unclassified row remains a failure/unknown,
never `J = 1000` or a silent pass.

---

## 3. Budget interpretation (important)

The orchestration spec's baseline prepared package is: **18 new screen BEM
calls, up to 6 verification candidates, 120 total candidate attempts, total
24 new BEM calls including failures/retries.**

These numbers are encoded **per arm and per seed replicate**, because both
manifests also predeclare a 25-seed paired schedule. The built manifests make
the expansion explicit:

- per arm/replicate: 18 screen + 6 verify = 24 new BEM, 120 attempts;
- pilot aggregate (25 pairs x 2 arms): 900 screen + 300 verify = 1,200 new BEM,
  6,000 attempts, marked `planning_only: true` and
  `execution_authorized: false`.

If the owner intended **24 total BEM calls for the whole pilot**, the 25-seed
schedule must be reduced; that is a parent decision, not a worker choice. No
aggregate is authorized by this manifest.

**Existing config schema used (not invented):**

- `search.budget_counts: valid` — B.4 semantics: the 18 budget units count
  *valid* evaluations; deterministic geometry/envelope/resource refusals do not
  consume the 18-valid budget.
- `search.max_attempts: 120` — hard ceiling on new (non-cached) attempts,
  including cheap refusals. This is how "120 attempts" is enforced without
  inventing a CLI flag.
- `search.warm_start: {from_runs, top_k, sigma_from_spread, allow_cross_brief}`
  — pilot 1's warm arm only. The normal loader refuses family/objective/brief/
  knob-name mismatches.
- `search.links` is unrelated and not used.

No `--max-evals` is set in the command templates: that cap counts *all*
evaluations (including cache hits) and would defeat the 120-attempt ceiling.
The CLI `--budget 18` sets the valid-evaluation budget; `budget_counts` comes
from the reviewed config overlay.

---

## 4. Pilot 1 — broad cold CMA vs diverse warm-start CMA

**Task:** frozen `native__ath_core_v4`, resolved through
`examples/briefs/campaign_2026-10-26_v4/native_ath_core_2in_v4.yaml`.
Objective v4, band 300-8000 Hz, 50°/50°, f0 1280 Hz, `cov_narrow_ratio 2.0`,
`cov_below_f0 mask`, `diag_reference round`; weights cov 1, rip 1, di 0.3,
dislope 0.5, flat 0.5, load 0.0, distd 0.5, diag 0.5; the 2.5-5.5 kHz band is
weighted x2. Source caveat: 2-inch uniform-piston f11 ≈ 3957 Hz; above it
results are geometry comparisons under that excitation, not real driver
behavior. Loading weight 0: no loading/efficiency/distortion claim.

**Cohort:** native-only (`config_name == native__ath_core_v4`). The four-config
brief family is descriptive only and is never pooled for GP/advisory
comparisons. `run_id` is absent on native rows, so independent-experiment
identity is `insufficient_evidence`.

**Arms (same task/brief/scoring/grid/backend/budget):**

| Arm | Treatment |
|---|---|
| `broad_cold_cma` | config seed only; no warm start |
| `diverse_warm_cma` | `search.warm_start` from two local native screen runs: `20261027T070736Z-screen-d37d64` and `20261113T004133Z-screen-46b68c`; `top_k 16`, `sigma_from_spread: true`, `allow_cross_brief: false` |

Both warm sources are read-only and match the task's family/objective v4/brief/
searched-knob names at build time. The warm arm is a **hypothesis**, not a
promise: a shared warm start changes only the CMA mean/sigma, not the solve hash.

**Seeds and pairing:** explicit 5101-5125 in both arms; seed *i* in cold is
paired with seed *i* in warm. Pairing is valid only because it is predeclared;
a shared seed is not proof of shared candidates. Resume segments/restarts inside
one run dir are one replicate. Run order is alternate-by-seed-index or a
predeclared fixed random permutation recorded before first dispatch; never run
both arms concurrently on the GPU lane.

**Verification:** both arms use the protocol allocation: up to 4 distinct screen
finalists by frozen J + 2 uniformly selected remaining eligible screened
designs from the reserved audit RNG seed (6 calls total).

**Decision rule:** paired `d = A - B`; bootstrap 95% CI of the mean paired
difference with right-censoring at the budget/attempt cap; declare `a_better`
only if the CI upper bound < -0.5 J, `b_better` only if the CI lower bound >
+0.5 J, else `inconclusive`. Fewer than five complete pairs is `pilot_only`.
The 0.5 J threshold is a declared pilot planning threshold (~5% of the R0
native replay median ~10 J), not a protocol constant or a speedup claim.

---

## 5. Pilot 2 — current vs enriched verification allocation

**Task:** `crease__core_law_v4` (published per-direction a/n/s law, 399x399
mouth, 17 searched knobs), resolved through the **same** brief
`native_ath_core_2in_v4.yaml`. Objective v4 identity is the same as pilot 1.

**Comparability caveat (explicit):**

- It is a **different physical task**: different geometry/bounds and more
  searched knobs (`az_*` law). Its results are never pooled with pilot 1.
- The S0 primary screen group contains `native__ath_core_v4`,
  `atlas__ath_core`, `atlas__core_law` and `crease__core_law_v4` at the same
  grid hash `7bd5a9d5825df12e`, dependency hash `e3614d0ba5956ded` and target
  hash `add33bc8c5127916`, but the census reports **pooled group counts**
  (1,499 complete replayable rows), not config-specific counts for crease.
- `run_id` is missing on all rows of that group; independent-experiment identity
  is `insufficient_evidence`. Local crease run dirs are used only as read-only
  runtime-timing evidence.
- Pilot 2 compares two verification allocations on the same second task; it does
  not compare across tasks.

**Arms (same screen policy/budget, different verify split):**

| Arm | Verify allocation |
|---|---|
| `current_fidelity_allocation` | up to 4 finalists + 2 audit (protocol default) |
| `enriched_audit_verification` | up to 2 finalists + 4 audit |

Both spend exactly 6 verify calls. A larger audit budget would be a new study
revision, not a silent change. Seeds are explicit 5201-5225 (distinct from pilot
1's 5101-5125) and paired by seed index. Run order alternates or uses a
predeclared permutation; the GPU lane is serial.

**Decision rule:** paired by seed; report the proportion of complete pairs whose
verified top-3 set or accept/reject decision changes, the mean absolute rank
shift, and a bootstrap 95% CI with right-censoring at the six-call verify
budget. The declared practical criterion is: enriched audit changes the verified
top-3 set/decision in at least 20% of complete pairs, or reduces the mean
absolute rank shift by at least one position, with no increase in new BEM cost.
Fewer than five complete pairs is `pilot_only`. This is decision support, not an
optimizer claim.

---

## 6. Cost accounting (both pilots)

Both manifests carry the same explicit ledger contract:

- attempts include cheap pre-BEM refusals (`invalid_geometry`,
  `invalid_envelope`, `mesh_too_large`);
- a cheap refusal is an attempt, **not** a BEM call;
- new screen BEM calls, verify calls and retries are counted separately;
- a retry reserves another unit; an unknown in-flight attempt retains its
  reservation until reconciled; cache hits add elapsed cost but no new BEM call;
- total cap is 24 new BEM calls including failures/retries;
- no attempt is turned into `J = 1000`.

The results parser reports `valid`, `cached_replay`, `cheap_refusal`,
`solver_failure`, `pipeline_failure`, `unknown_failure` and `unknown`
separately. `verify_calls` is reported only when `mode == "verify"` is recorded;
otherwise it is `null` with `verify_calls_unknown: true`.

---

## 7. Stop rules and lane ownership

Both manifests stop on: budget cap, wall deadline (required; left as an explicit
placeholder), explicit cancellation, legal-pool exhaustion, invalid/stale
package, and three consecutive infrastructure/solver-host failures. Partial
results and the attempt journal are preserved.

Lane ownership is explicit: GPU `beat_cuda` lane, one CUDA solve at a time, no
cross-lane cleanup. If the owner selects `beat_cpu`/`bempp_cpu`, the runner must
explicitly hold `runs/.cpu.lane.lock`; the current CLI `_solve_lock` is a null
context for CPU because the night runner owns the CPU lock. CPU analysis/
proposal work never invokes GPU cleanup.

---

## 8. Runtime estimates (measured logs only, with caveats)

Primary estimates are measured local screen-run ledgers (S3 `cost_ledger`
semantics; wall span is not used when it reflects pauses):

| Task | Source run | Attempts | Valid | BEM calls | BEM seconds | s/BEM | s/attempt | Wall span |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `native__ath_core_v4` | `20261027T070736Z-screen-d37d64` | 200 | 190 | 190 | 3,303.5 | 17.39 | 18.49 | 29,216 s (paused) |
| `native__ath_core_v4` | `20261113T004133Z-screen-46b68c` | 200 | 196 | 196 | 3,656.9 | 18.66 | 20.22 | 4,047 s |
| `crease__core_law_v4` | `20261027T052720Z-screen-e7f4f8` | 200 | 162 | 162 | 3,622.4 | 22.36 | 21.99 | 28,125 s (paused) |

Arithmetic extrapolation to one 24-call block (not a speedup claim):

| Pilot | Screen 18 BEM | Verify 6 BEM | Block | Attempt-cap upper bound |
|---|---:|---:|---:|---:|
| 1 (native) | 313-336 s | 104-224 s (assumed 1x-2x) | 417-560 s (6.96-9.33 min) | ~40.5 min/arm |
| 2 (crease) | 402 s (single source) | 134-268 s (assumed 1x-2x) | 537-671 s (8.94-11.18 min) | ~44.0 min/arm |

25-pair x 2-arm planning aggregate: pilot 1 ≈ 5.8-7.8 h (attempt-cap bound
≈ 33.7 h); pilot 2 ≈ 7.5-9.3 h (attempt-cap bound ≈ 36.7 h). These are
arithmetic bounds, not schedules.

Caveats, repeated in both manifests:

- historical runs, not this pilot; host/cache state is not controlled;
- `d37d64` and `e7f4f8` have long wall spans from pauses; accumulated candidate
  cost is the honest basis (~3,697 s and ~4,399 s);
- verify-fidelity cost is **unmeasured**; the 1x-2x multiplier is an assumption
  (verify uses 1024 balloon points vs 512 screen);
- pilot 2 has only one measured source (no timing spread) and a ~19% cheap-
  refusal rate, so reaching 18 valid evaluations may take ~22 attempts;
- warm-start timing may differ from cold; no warm-start timing was measured;
- no speedup or improvement is claimed.

A secondary cross-check (not used for the block estimate) is the S3 freeform
25-seed seed-variance table: ~148-150 BEM calls and ~881-1,010 s accumulated
candidate cost per run. It is a **different physical task/family**, so it is
only a sanity check, not a comparable timing source.

---

## 9. Hypotheses, rollback and adoption

Both manifests label expected outcomes as hypotheses:

- Pilot 1: `H1` warm start lowers J at equal budget; `H0` cold/warm are
  indistinguishable at this budget. Each has an explicit falsifier.
- Pilot 2: `H2` enriched audit changes verified rank/decision; `H0` the
  allocations agree. Each has an explicit falsifier.

Fail/no-gain rollback (enumerated in both manifests):

- no production default, objective version, tolerance/weight, registration,
  cache/dataset or GUI/CLI change is made or implied;
- if not scheduled, discard the scratch overlay; no live file was written;
- if warm start does not beat cold at the declared threshold, do not adopt it;
  keep `search.warm_start` absent;
- if enriched audit adds no decision-relevant information, keep the current
  4-finalist + 2-audit allocation;
- if inconclusive, do not silently enlarge the budget; a larger study is a new
  revision;
- cancellation/crash preserves partial results; unknown attempts are reconciled,
  never relaunched automatically.

Owner adoption decisions are enumerated per manifest with `adopt_if` and
`otherwise` (e.g. adopt warm start only on prospective paired evidence with CI
upper < -0.5 J and no cost increase; adopt enriched audit only if it meets the
declared decision-change criterion; otherwise keep the current policy).

---

## 10. Validation record

```
=== BUILD P1 ===
SUMMARY errors=0 warnings=0 ok=true
WROTE scratch\bo_m0\s11\built\pilot1_cold_vs_warm_native_ath_core_v4.json
=== VALIDATE P1 ===
SUMMARY errors=0 warnings=0 ok=true
=== BUILD P2 ===
SUMMARY errors=0 warnings=0 ok=true
WROTE scratch\bo_m0\s11\built\pilot2_verify_allocation_crease_core_law_v4.json
=== VALIDATE P2 ===
SUMMARY errors=0 warnings=0 ok=true
```

Focused tests:

```
tests/test_tools_experiments_manifest.py ............................ [100%]
29 passed
```

`python -m compileall -q tools/experiments` → OK.

---

## 11. Untested limits / explicit gaps

- **No solve ran.** No GPU/CPU BEM, mesh, lane lock or job was started.
- **No executor/runner exists here.** Command templates are validated against
  the current CLI parser but never executed; the manifests are not runnable
  jobs.
- **Config overlays are not applied.** `search.budget_counts`,
  `search.max_attempts` and `search.warm_start` are existing config-schema keys,
  but a reviewed runner must materialize the overlay; this tool deliberately
  never writes `examples/` or a live config.
- **Warm sources are read-only resolved.** Their identity matches at build time;
  an actual warm-start mean/sigma selection was not run.
- **Verify-fidelity timing is unmeasured.** The 1x-2x verify-cost multiplier is
  an assumption.
- **No pilot results exist.** The results parser is tested on synthetic run
  dirs only; it has not parsed pilot data.
- **No power guarantee.** The 25-pair schedules are predeclared plans; a pilot
  with fewer than five complete pairs is labeled `pilot_only`.
- **Comparability is descriptive.** The crease config-specific independent-
  experiment count is not established by the pooled S0 group, and `run_id` is
  missing on group rows.
- **Scratch artifacts are not committed.** `scratch/` is gitignored; the built
  JSON and this protocol are local evidence, not repository history.
