# WATCHDOG_REPLAY

Investigator B — read-only. Replays the committed search watchdog
(`tools/run_campaign_night.py::watchdog_verdict`) against historical `search.ndjson` prefixes.
No solve, no queue mutation. The pure verdict function is imported and called; the kill path is
never executed. Helper: `scratch/fable_architecture/.tmp/watchdog_replay.py` (writes only `.tmp/`).

## Provenance

- Repo root `C:\Users\hunte\Hrns\hornlab-search`.
  **HEAD at dispatch-time check `3efe9be` @ 19:38:34; HEAD at final check `d187c06` @ 19:49:04**
  (2026-11-16, local). `tools/run_campaign_night.py` is **clean at the final HEAD** (no
  working-tree diff), so the verdict logic below is committed, not local-only. The tree advanced
  during the pass; all `run_campaign_night.py` line numbers were re-verified at `d187c06`. The tree
  later advanced to `50f3d8c` @ 19:55:43 (test/docs only): `git diff --stat d187c06..50f3d8c` shows
  **none** of the traced files changed, so all citations remain valid at `50f3d8c`.
- A live `home_day2_2026-11-16` queue and a live CUDA solve were running; nothing was started,
  stopped, killed, or locked. All rows are historical records.
- Method: for each run, pass prefixes `rows[base:i]` to `watchdog_verdict(..., cfg, _run_bounds(run))`
  and record the first prefix that returns a non-empty reason. `base = 0` except the resumed leg
  (§5), reproducing the runner's `wd_base` (`run_campaign_night.py:1028-1035`). Because the deployed
  runner polls every 30 s (`WATCHDOG_POLL_S`, `:107`), the **row index at which the pure function
  first triggers can be 1–2 rows earlier** than the row the live poll actually observed; that gap is
  flagged per run.
- Status taxonomy: **reproduction** = my replay reason matches the runner's own
  `=== WATCHDOG …` log line; **historical run record** = taken from `search.ndjson`/`summary.jsonl`;
  **UNKNOWN** = not recoverable from extant files.

## 1. Known-then at each checkpoint (only rows available at that timestamp)

### 1a. Normal completion — `20261116T081139Z-screen-63158a` (`hl__biradial_es_style_smooth_v7`)

| rows | timestamp (UTC) | ok | complete-BEM (solved here) | best J then | verdict then |
|---:|---|---:|---:|---:|---|
| 20 | 08:15:10 | 20 | 9 | 5.583 | — |
| 40 | 08:21:32 | 40 | 29 | 5.583 | — |
| 60 | 08:27:55 | 60 | 49 | 5.479 | — |
| 80 | 08:33:57 | 80 | 69 | 5.145 | — |
| 100 | 08:40:17 | 100 | 89 | 5.145 | — |
| 107 | 08:42:34 | 107 | 96 | 5.114 | **none (no trigger)** |

Seed J = 6.130; final best 5.114 (−16.6 %); 11 of 107 `ok` rows were cache replays
(`ok AND cached`), so 96 were solves performed here. The last improvement (5.145 → 5.114) arrived in
rows 101–107, i.e. **after** the 30/40-valid windows that would trigger a no-gain/stall stop on a
flat run. On this run the watchdog correctly left it alone (it kept improving). Status: **historical
run record + reproduction (no trigger)**.

## 2. First trigger per representative run

All replay reasons match the runner's recorded log line unless noted.

| run id | config | total rows | **first-trigger row** | recorded trigger (log) | attempts@trigger | ok / solved@trigger | seed J | best J then | final best | elapsed to trigger (s) | cache (ok∧cached) |
|---|---|---:|---:|---|---:|---|---:|---:|---:|---:|---:|
| `20261116T095336Z-screen-7fc9b7` | `hl__crowe_x_osse_cd_v7` | 28 | 28 | refusal rate 32 % / last 28 | 28 | 19 / 18 | 6.064 | 5.691 | 5.691 | 416 | 1 |
| `20261116T044917Z-screen-12eb61` | `hl__ath_tritonia_landscape_v8` | 74 | 74 | bound-pinned `morph_rate` low | 74 | 73 / 73 | 26.903 | 5.692 | 5.692 | 2256 | 0 |
| `20261116T071520Z-screen-1c8608` | `hl__biradial_es_style_v7` | 71 | 71 | stalled (best J 6.482) | 71 | 71 / 70 | 7.776 | 6.482 | 6.482 | 1377 | 1 |
| `20261116T145634Z-screen-e4c778` | `hl__osse_rrect_fold_warm_v7` | 76 | 32 | no gain (seed J 4.891) | 32 | 30 / 30 | 4.891 | 4.891 | **4.661** | 717 | 0 |
| `20261112T110126Z-screen-c414b1` | `atlas__osse_ext_throat` (cma_me/QD) | 401 | 25 | refusal rate 36 % / last 25 | 25 | 16 / 15 | 12.440 | 7.442 | **6.636** | 198 | 1 |
| `20261116T130335Z-screen-ab4fb9` (leg 1) | `hl__osse_rrect_fold_warm_v7` | 77 | 30 | no gain (seed J 3.762) | 30 | 30 / 30 | 3.762 | 3.762 | **3.673** | 750 | 0 |

Reproduction detail: 5 of 6 match the exact logged reason. The QD run was **not** watched in 2026-11
(the watchdog did not exist); its line is a **replay counterfactual**, not a recorded stop.
Status: **reproduction / historical run record** as marked.

## 3. Progression at proposed stop points, "known then" only

### 3a. `20261116T044917Z-screen-12eb61` (tritonia; bound-pin at 74)

| rows then | timestamp | attempts | ok | solved | best J then | verdict then |
|---:|---|---:|---:|---:|---:|---|
| 10 | 04:54:38 | 10 | 10 | 10 | 12.618 | — |
| 20 | 04:59:22 | 20 | 20 | 20 | 8.115 | — |
| 30 | 05:04:27 | 30 | 30 | 30 | 6.470 | — (pin gate opens at 30 valid) |
| 40 | 05:09:05 | 40 | 40 | 40 | 5.936 | — |
| 50 | 05:14:09 | 50 | 50 | 50 | 5.936 | — |
| 60 | 05:19:32 | 60 | 60 | 60 | 5.936 | — |
| 70 | 05:25:14 | 70 | 69 | 69 | 5.692 | — |
| **74** | **05:27:53** | **74** | **73** | **73** | **5.692** | **bound-pinned `morph_rate` low** |

The run gained 26.903 → 5.692 (79 %), almost all of it by row 40; the pin rule then fired. This is a
**search-box** stop: `morph_rate` sits at `[1.2, 2.1]` low, and the TRITONIA audit widened exactly
that knob for v9 (`docs/queue/TRITONIA_V9_CMA_AUDIT_2026-11-16.md:3`). It is **not** a physical or
acoustic limit. Status: **reproduction**.

### 3b. `20261112T110126Z-screen-c414b1` (QD refusal; replay counterfactual)

| rows then | timestamp | attempts | ok | solved | best J then | verdict then |
|---:|---|---:|---:|---:|---:|---|
| 10 | 11:03:14 | 10 | 8 | 7 | 7.442 | — |
| 20 | 11:04:28 | 20 | 13 | 12 | 7.442 | — |
| **25** | **11:05:06** | **25** | **16** | **15** | **7.442** | **refusal rate 36 % / last 25 > 30 %** |
| 40 | 11:07:23 | 40 | 29 | 28 | 7.442 | — (window cleared) |
| 60 | 11:10:38 | 60 | 45 | 44 | 7.161 | — |

The 2026-11-16 watchdog would have killed this QD run at row 25. It actually continued to 401 rows,
reached best 6.636, and left a final archive of **5 / 324 bins, best 6.636 at eval 60** (`archive.json`
in the run dir). The refusal-rate rule is structurally hostile to a MAP-Elites emitter that
deliberately probes a wide box: 120 / 401 rows are deterministic envelope refusals
(`height > 300 mm`, coded `invalid_geometry`). Status: **reproduction of the rule + counterfactual
(the run was not watched)**.

## 4. Gain accounting (verified vs screen vs archive)

- **Verified gain**: none of the six run dirs contains a `verify`-mode solve of the same designs, so
  a *verified* acoustic improvement at the stop point is **UNKNOWN** for every row above. The screen
  J deltas below are **screen scores only**, not verified acoustics.
- **Screen gain at trigger**: tritonia 26.903 → 5.692 (79 %); crowex 6.064 → 5.691 (6 %);
  biradial-stall 7.776 → 6.482 (17 %); rosse-no-gain 4.891 → 4.891 (**0 % at trigger**);
  QD 12.440 → 7.442 (40 %); resume-leg1 3.762 → 3.762 (**0 % at trigger**).
- **Archive gain (QD only)**: final `archive.json` = 5 occupied bins of 324 (coverage 1.54 %),
  best 6.636 at eval 60. **Archive state at the trigger (row 25) is UNKNOWN**: the earliest
  surviving cell records `eval_no 38`, and the archive keeps only the best per cell, so a cell first
  filled before row 25 may have been overwritten. A kill at 25 would certainly exclude the eval-60
  best cell as recorded. Status: **historical run record + plausible inference**.

## 5. Resume: judgement only on new rows

`20261116T130335Z-screen-ab4fb9` was stopped by `no gain` at 30 rows, then resumed as
`c_warm_s9012` with `watchdog: {stall_valid: 60}` and `--resume` (night files
`runs/nights/home_day_2026-11-16.yaml:259-270`, `runs/nights/home_day2_2026-11-16.yaml:29-40`).
The runner sets `wd_base = len(existing rows) = 30` and judges only `rows[30:]`
(`run_campaign_night.py:1028-1035`, `:1076`).

| leg | rows then | timestamp | attempts in slice | ok | solved | best in slice | overall best then | verdict |
|---|---:|---|---:|---:|---:|---:|---:|---|
| leg 1 | 30 | 13:16:46 | 30 | 30 | 30 | 3.762 | 3.762 | **no gain (seed still best)** |
| leg 2 | 40 | 20:15:46 | 10 | 10 | 10 | 3.888 | 3.762 | — |
| leg 2 | 60 | 20:22:09 | 30 | 30 | 30 | 3.762 | 3.762 | — |
| leg 2 | 70 | 20:25:31 | 40 | 40 | 40 | 3.673 | **3.673** | — |
| leg 2 | 76 | 20:27:32 | 46 | 46 | 46 | 3.673 | 3.673 | **bound-pinned `az_s_cos2_amp` high** |
| leg 2 | 77 | 20:27:51 | 47 | 47 | 47 | 3.673 | 3.673 | bound-pinned `az_fold_v_width_deg` low |

**Fidelity note:** the pure function first triggers at row **76** with `az_s_cos2_amp`; the runner's
log records row **77** with `az_fold_v_width_deg`
(`runs/nights/home_day2_2026-11-16/c_warm_s9012.log:13`). One extra row changed the top-6 membership
and the first-pinned key; the deployed 30 s poll sampled at 77. Both are the same mechanism; the
exact key is sensitive to the last row. Status: **reproduction with a 1-row key-order caveat**.

**Counterfactual:** at the leg-1 stop the best was the seed (3.762). Rows 31–77 (the resume) reached
**3.673**, a 2.4 % improvement. The no-gain rule stopped the run *before* the gain it was watching
for. This is the concrete cost of the rule on this run. Status: **historical run record**.

The rosse run `e4c778` shows the same shape with a much larger gap: rows 30–32 at 15:08–15:09, then
rows 33+ reappear at **20:49** after a later resume; final best 4.661 vs 4.891 at the leg-1 stop
(4.7 % gain discarded by the stop). Status: **historical run record**.

### 3c. `20261116T095336Z-screen-7fc9b7` (crowex; refusal at 28)

| rows then | timestamp | attempts | ok | solved | best J then | verdict then |
|---:|---|---:|---:|---:|---:|---|
| 10 | 09:56:35 | 10 | 8 | 7 | 5.879 | — (below min_attempts 25) |
| 20 | 09:59:19 | 20 | 15 | 14 | 5.742 | — |
| **28** | **10:00:52** | **28** | **19** | **18** | **5.691** | **refusal rate 32 % / last 28** |

This is the smallest run in the set; it stopped after 416 s with 9 envelope refusals in 28 attempts.
The best (5.691) equals the final best — there was no discarded continuation here. Status:
**reproduction**.

### 3d. `20261116T071520Z-screen-1c8608` (biradial; stall at 71)

| rows then | timestamp | attempts | ok | solved | best J then | verdict then |
|---:|---|---:|---:|---:|---:|---|
| 10 | 07:18:35 | 10 | 10 | 9 | 6.979 | — |
| 20 | 07:21:50 | 20 | 20 | 19 | 6.835 | — |
| 30 | 07:24:58 | 30 | 30 | 29 | 6.769 | — |
| 40 | 07:28:26 | 40 | 40 | 39 | 6.482 | — |
| 50 | 07:31:45 | 50 | 50 | 49 | 6.482 | — |
| 60 | 07:35:03 | 60 | 60 | 59 | 6.482 | — |
| **71** | **07:38:36** | **71** | **71** | **70** | **6.482** | **stalled (<0.5 % over 40 valid)** |

The stall rule is doing what it says: the last real gain was by row 40, and rows 41–71 (31 valid,
~10 min) did not beat 6.482. Unlike the no-gain cases (§5), this stop did not obviously discard a
later gain — final best = 6.482. Status: **reproduction**.

### 3e. Cache/fidelity ledger for the replay set

| run | rows | ok | `ok∧cached` | solved here | notes |
|---|---:|---:|---:|---:|---|
| `63158a` normal | 107 | 107 | 11 | 96 | 11 replayed Responses (resume/solve-cache) |
| `7fc9b7` crowex | 28 | 19 | 1 | 18 | one cached score |
| `12eb61` tritonia | 74 | 73 | 0 | 73 | no cache |
| `1c8608` biradial | 71 | 71 | 1 | 70 | one cached |
| `e4c778` rosse | 76 | 74 | 0 | 74 | resumed later (timestamp gap) |
| `c414b1` QD | 401 | 281 | 1 | 280 | final archive 5/324 |
| `ab4fb9` resume | 77 | 77 | 0 | 77 | `wd_base=30` on resume |

“solved here” is the only column that cost BEM in this run. Status: **historical run record**.

## 6. Code-review hypothesis — `not ok` / `objective >= 900` conflation

**Verify in code:** the watchdog's bad-outcome predicate is
`bad(r) = (not r.get("ok")) or not finite(objective) or objective >= 900`
(`tools/run_campaign_night.py:166-168`). The in-code comment itself calls these
"refusals/failures (objective >= 900 or not ok)" (`:90-91`). Status: **directly verified**.

**What it obscures.** This single boolean merges five distinct outcome classes that `outcomes.py`
deliberately separates (`hornlab_search/search/outcomes.py:6-19`, `classify:80-136`):
1. deterministic geometry refusal (`invalid_geometry`) — bad:true;
2. deterministic envelope refusal (`invalid_envelope`) — bad:true;
3. resource refusal (`mesh_too_large`) — bad:true;
4. transient infrastructure (`solve_failed`) — bad:true;
5. metric/pipeline failure (`metrics_failed`, `exception`) — bad:true;
6. a **fully measured** hard-gate penalty that `outcomes` would admit as `measured_gate` with
   `strict_tell_eligible == True` (`outcomes.py:66-78`, `:94-100`) — also bad:true if J ≥ 900.

Consequences, all code-verified:
- A transient worker storm (`solve_failed` only) raises the "refusal rate" and the only logged remedy
  is the refusal text, i.e. it is indistinguishable from a bad box. The runner does not say
  "infrastructure"; it says "refusal rate X %".
- A QD/exploratory run with a legitimately high refusal fraction is killed (proved at
  `c414b1`, §3b) even though its archive was filling.
- The `PENALTY_INVALID = PENALTY_FAILED = 1.0e3` constants (`objective/terms.py:18-19`) and the
  graded cap `2.0e3` (`:104`) mean every deterministic refusal is ≥ 1000, so the `>= 900` test
  catches all of them — but it also catches any measured-gate penalty and any unusually large real
  objective. `outcomes.classify` already encodes the correct rule (`strict_tell_eligible`), and the
  watchdog ignores it.
- Counterevidence: the watchdog's refusal rule is *intended* to catch deterministic refusals, and
  for plain CMA on a fixed brief it does so correctly (the 5 reproductions in §2). The defect is the
  **conflation**, not the arithmetic.

**`pin_*` exposure (second half of the hypothesis).** `WATCHDOG_DEFAULTS` (`:99-106`) contains only
`min_attempts`, `refusal_window`, `refusal_max`, `no_gain_valid`, `stall_valid`, `min_rel_improve`.
The bound-pin rule reads `pin_min_valid` (30), `pin_frac` (0.03), `pin_count` (3) via
`cfg.get(...)` (`:186`, `:196`, `:199`), but `_resolve_watchdog` rejects any key not in
`WATCHDOG_DEFAULTS` **except** `pin_ignore` (`:122-131`). Therefore `pin_min_valid` / `pin_frac` /
`pin_count` are **hard-coded and not exposed in the public YAML schema**; only `pin_ignore` is
tunable. Status: **directly verified**, and corroborated by the TRITONIA audit
(`docs/queue/TRITONIA_V9_CMA_AUDIT_2026-11-16.md:16`: "the live runner's pin rule is not separately
configurable"). No test exercises supplying `pin_count`/`pin_frac`/`pin_min_valid`; the only pin
test is `test_pin_ignore_skips_hard_limit_knobs` (`tests/test_night_runner_watchdog.py:166-172`).

## 7. Proposed (not run) replay/guard experiments

1. **Candidate-vs-distinct outcome split.** Factor `watchdog_verdict`'s `bad()` into
   `outcomes.classify` categories and require the refusal-rate rule to count only
   `geometry/envelope/resource`, with transient/metric routed to a retry/abort channel. Re-run the
   replay above read-only and compare stop points (expected: QD `c414b1` no longer "refusal-stopped").
2. **Resume-aware gain seed.** Feed the pre-resume best into the resumed verdict so `no gain` can be
   judged against the true archive best, not just the new slice (today it cannot fire on a resume
   because the first new row is not `n==0`, `:183`; but the pin/stall checks also ignore pre-resume
   rows). Not implemented.
3. **Expose `pin_min_valid`/`pin_frac`/`pin_count`** in `WATCHDOG_DEFAULTS` + schema and add the
   missing test. Not implemented.
4. **Archive-aware QD rule.** For `algorithm: cma_me`, judge by archive coverage delta, not raw
   refusal rate. Not implemented.

## Counterevidence / limits

- The exact stop *row* is poll-timing dependent (±1–2 rows); §5 shows one case where the pinned key
  differs by one row. This does not change the first-trigger classification, only the precise key.
- `summary.jsonl` reports `best_J: null` for all 38 watchdog rows because the kill precedes the
  search's own summary print; every "best J then" above is recomputed from `search.ndjson`, not read
  from the summary.
- The QD stop is a **counterfactual replay** (the watchdog postdates the run); it is not evidence
  that the real run was stopped.
- No verify-mode row exists in these dirs, so no **verified** acoustic gain is claimed anywhere.
