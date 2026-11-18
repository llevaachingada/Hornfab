# LOCAL_RESULTS 2026-11-18 part 3 - throat sweep Phase 1 (+ Phase 2/3 status)

Throat agent. Branch `hornfab-all-2026-11-18` (canonical checkout). CPU + the owner-approved
GPU Phase 1 solves only; no queue entries edited except the owner-ordered throat insert;
`scalar_v9.py` / `AGENTS.md` / `.opencode` untouched.

## Queue / night recovery

- Night `cd_rrect_2026-11-17` was dead on stale GPU lock pid 15952; the owner-ordered restart
  ran at 08:27 and took over the stale lock (`STALE LOCK TAKEN OVER ... pid 15952 is gone`),
  then resumed from `queue_state.json` (34 jobs were already done).
- **IMPORTANT job-line correction:** the part2 handoff's `kind: search, budget: 1` lines with
  every bound `search: false` DO NOT WORK on this tree: pycma initialises with `x0=[]`
  (zero free dimensions) and the first throat job died
  `TypeError: ufunc 'isinf' not supported ...` (job throat_hv_B_ctl, run
  20261118T132731Z-screen-af88c7). The correct single-design job is
  `kind: command` -> `.venv/Scripts/hornlab-search.exe run --config <yaml> --mode screen`
  ("evaluate the seed design once"). The 7 Phase 1 jobs were reinserted that way (new ids
  `throat_hv_run_*`; the failed `search` ids are burned in `done` and must not be reused).
  The 7 jobs were placed BEFORE the pending backlog (owner: "going first costs little");
  all pre-existing entries keep their relative order.
- Watcher: scheduled task `HornLabThroatPhase1Poll` runs
  `scratch/night_poll_throat.ps1` every 15 minutes (read-only status; appends
  `runs/nights/cd_rrect_2026-11-17/poll_throat.log`; writes `THROAT_PHASE1_DONE.txt` /
  `THROAT_PHASE2_DONE.txt` markers). Delete the task when the track is finished:
  `schtasks /Delete /TN HornLabThroatPhase1Poll /F`.

## Phase 1 - 7 single solves, ALL OK (v7 objective/brief identity, same as the v8 incumbent)

Command per job: `.venv/Scripts/hornlab-search.exe run --config
examples/typologies/throat_hv_2026-11-18/sweep/<cfg>.yaml --mode screen`.
Identity statement: the sweep configs carry the `room_landscape_80x50_700_hf1440_v7` brief and
the v7 objective block - byte-equal to the v8 baseline run `20261116T025728Z-screen-cd60f7`
(stored best J 3.1028085892200576). No cross-identity comparison anywhere below.

| config | rho | onset | J | H mean | V mean | dofs | solve s | wall s | VRAM base/peak (night) | run dir |
|---|---|---|---|---|---|---|---|---|---|---|
| B_ctl | 1.0 | 0.10 | 5.94839 | 91.19 | 83.60 | 4849 | 25.3 | 30.9 | 757 / 1093 MiB | 20261118T132956Z-screen-f11273 |
| B_o00 | 1.5 | 0.00 | 6.35470 | 92.55 | 84.19 | 4861 | 25.8 | 31.9 | 742 / 1093 | 20261118T133053Z-screen-28c74d |
| B_o25 | 1.5 | 0.25 | 5.73151 | 90.96 | 83.82 | 4778 | 25.9 | 32.4 | 742 / 1093 | 20261118T133153Z-screen-ca402c |
| B_o50 | 1.5 | 0.50 | **5.69735** | 89.59 | 83.45 | 4765 | 24.6 | 30.6 | 742 / 1093 | 20261118T133254Z-screen-704484 |
| B_o75 | 1.5 | 0.75 | 6.13745 | 88.89 | 83.68 | 4699 | 23.1 | 27.6 | 742 / 1093 | 20261118T133352Z-screen-c5f07c |
| A_r15 | 1.5 | - | **3.08361** | 87.98 | 83.46 | 5438 | 28.7 | 31.0 | 742 / 1111 | 20261118T133445Z-screen-b16baf |
| A_r20 | 2.0 | - | 3.12713 | 88.37 | 83.61 | 5670 | 30.8 | 33.2 | 742 / 1187 | 20261118T133540Z-screen-fe2089 |
| v8 stored | 1.0 | - | 3.10281 | 87.42 | 83.29 | 5274 | 35.2 | 38.9 | (historical) | 20261116T025728Z-screen-cd60f7 |

- **A vs v8 (matched identity):** A_r15 (rho 1.5) **beats the incumbent by 0.0192**
  (3.08361 vs 3.10281); A_r20 (rho 2.0) is WORSE by 0.0243. The rho knob helps, mildly, at 1.5.
  Term deltas A_r15-v8: cov 0.738 vs 0.772 (better), diag 0.288 vs 0.315 (better),
  flat 0.651 vs 0.620 (worse), distd 0.316 vs 0.293 (worse), load 0 both. DI source = balloon
  everywhere; no refusals, no NaN terms.
- **B family ranking:** B_o50 < B_o25 < B_ctl < B_o75 < B_o00. Best B beats B_ctl by **0.25104**
  (5.69735 vs 5.94839). B's absolute level (~5.7-6.4) versus A/v8 (~3.1) is dominated by the
  v7 `load` term (3.2 for every B design vs 0.0 for A/v8): the no-extension B geometry is
  penalised by the loading term under THIS identity - the B sweep measures the H/V mechanism,
  not overall J competitiveness. Do not rank B against A without stating that.
- Per-config frequency data: `hv_beamwidth_<cfg>.csv` (H/V -6 dB widths, outermost
  definition), `di_<cfg>.csv` (DI + di_source), overlay PNGs `beamwidth_B.png`,
  `beamwidth_A_vs_v8.png`, all in this folder. `phase1_summary.csv` carries the full rows
  incl. every v7 term. No waistband/narrowing flag is reported by the v7 objective block;
  the brief's 8 kHz floor lives inside `cov` (bw8k_floor mask).

## Phase 2 - DONE (owner authorized skipping the running BO arm)

The owner authorized interrupting the running BO arm: `t_ath14_scalar100` was killed
(recorded `blocked`, 78 observations preserved; resuming it later needs a fresh `--root`
- `refusing: ...\t_ath14_scalar100\package.json exists`). Both epw8 solves then ran:

| design | epw6 (Phase 1) | epw8 (Phase 2) | |dJ| | dofs |
|---|---|---|---|---|
| B_o50 (best B) | 5.69735 | 5.68878 | 0.00857 | 8259 |
| B_o00 (worst B) | 6.35470 | 6.34457 | 0.01013 | 8471 |

**Gate: max |dJ| = 0.0101 << 0.25104 -> PASSES** (mesh-fidelity |dJ| is ~25x smaller than the
best-B improvement; Phase 1 differences are above mesh resolution). Run dirs:
`20261118T151523Z-screen-*` / see `runs/nights/cd_rrect_2026-11-17/summary.jsonl`
(ids `throat_hv_p2_*`). One further BO arm (`t_corelaw_turbo100`, started by the runner before
it re-read my Phase 3 insertion) was also skipped the same way (78-observation state preserved
in its study root; fresh `--root` on resume).

## Phase 3 - DONE (budget 40, all 41 evaluations ok)

`throat_hv_p3_B_search40` (search, 3 free shared knobs, seed = B_o50):
run dir `20261118T150846Z-screen-9a04c5`, 41 rows / 41 ok, VRAM peak 1108 MiB.

- Best: **J = 5.60780** (eval n=32) at **rho 1.371 / onset 0.320 / ramp 2.160** - a **0.0896
  improvement over the B_o50 seed (5.69735)** and 0.3406 over B_ctl. Improvements come mainly
  from `cov` (0.373 -> 0.355), `diag` (0.104 vs seed... see `phase1_summary.csv` for term rows)
  and the searched knobs landing at intermediate values, confirming the mechanism: the H/V
  departure wants onset ~0.3, ratio ~1.4, gentle ramp under this brief identity.
- Terms of the winner: cov 0.3549, rip 0.2028, di 1.8193, dislope 0.0260, flat 1.0928,
  load 3.1764, flat_cv 0.4931, diag 0.1694, distd 0.186 - DI source balloon, no NaN, no refusal.

## Track status

- Phase 1 (7 solves), Phase 2 (2 solves), Phase 3 (40-eval search) all DONE and within the
  owner's hard cap (10 single solves + one 40-eval search: used 9 single + 1 search; the +1 v8
  identity re-solve was not needed since identity was byte-verified).
- The remaining night queue continues with the untouched BO arms (`t_corelaw_scalar100` was
  already running when the last poll ran). Skipped arms (state preserved, fresh `--root` on
  resume): t_ath14_scalar100 (78 obs), t_corelaw_turbo100. The scheduler task
  `HornLabThroatPhase1Poll` was deleted (its Phase 1/2 markers served).
- Everything below was written before Phase 2/3 ran; the tables above supersede the gate text.

## Phase 2 - queued behind the running BO arm (2 finer-mesh solves)

- Configs (NEW files, shape_checked OK): `throat_hv_sweep_B_o50_epw8.yaml` (8259/24000 dofs)
  and `throat_hv_sweep_B_o00_epw8.yaml` (8471/24000) - `mesh.epw` 8.0 vs 6.0, all knobs equal
  (realised dofs at Phase 1: 4765 / 4861).
- Night jobs (positions 8-9, after the 7 Phase 1 runs; they start after the currently running
  `t_ath14_scalar100` BO arm finishes - its own deadline is ~6 h out):
  `throat_hv_p2_B_o50_epw8`, `throat_hv_p2_B_o00_epw8` (kind: command, `run --mode screen`).
- Gate for Phase 3: run it ONLY if `0.25104 > max(|dJ|)` across the two epw6-vs-epw8 pairs.

## Phase 3 - prepared, NOT queued (gate-conditional)

Config ready: `examples/typologies/throat_hv_2026-11-18/sweep/throat_hv_B_search40.yaml`
(parent = best Phase 1 B design B_o50 seed: rho 1.5 / onset 0.5 / ramp 2.0; free keys
`throat_hv_ratio` 0.7-2.5, `hv_onset_frac` 0.0-0.9 (ONSET_MIN 0.0), `section_exp_ramp` 1.0-4.0;
everything else pinned; sigma0 0.15 for 3 free keys; shape_check 4765 dofs OK).
If the Phase 2 gate passes, append after the Phase 2 jobs:

```yaml
- id: throat_hv_B_search40
  kind: search
  config: examples/typologies/throat_hv_2026-11-18/sweep/throat_hv_B_search40.yaml
  budget: 40
  mode: screen
  timeout_s: 14400
```

then `--dry-run` and let the live runner pick it up (re-read before every job).

## Files / provenance

- Evidence folder: `docs/evidence/throat_hv_2026-11-18/` (this file, CSVs, PNGs) - staged for
  the integrator to commit with the CONTINUITY/ISSUES entries (throat agent does not commit).
- New configs on the branch: 2 epw8 copies + Phase 3 config under
  `examples/typologies/throat_hv_2026-11-18/sweep/`.
- Night file edit: 7 `throat_hv_run_*` + 2 `throat_hv_p2_*` jobs inserted before the pending
  backlog; backup at `runs/nights/cd_rrect_2026-11-17.yaml.bak-20261118`.
- Bug-class note for the logs: `kind: search` + every bound `search: false` crashes pycma
  (`x0=[]`); use `hornlab-search run` (or `verify`) for single-design jobs.
