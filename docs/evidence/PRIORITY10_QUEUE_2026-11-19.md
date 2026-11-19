# PRIORITY10 — ten-horn queue: reconciliation, registry, and staged plan (2026-11-19)

Owner handoff: "HornFab: prioritized ten-horn GPU queue handoff" (2026-11-19). This document is the
local orchestrator's answer. The night it describes is `docs/queue/fable_priority10_2026-11-19.yaml`
(admission packet beside it). **Nothing here was launched while `fable_scout40w2_2026-11-19` owned the
GPU**; the launcher waits for that runner's PID (see §6).

Labels: **[measured]** = read from a run/cache/command in this tree; **[inferred]** = a reading, not a
measurement; **[planned]** = not yet executed.

## 1. State at reconciliation (measured)

| Item | Value |
|---|---|
| Working tree | `hornlab-search`, branch `hornfab-all-2026-11-18`, HEAD `138d88a` = `origin/main` |
| Local `main` | `296238d`, **22 commits ahead** of HEAD (GUI P2/P3 + SCOUT40 preflight docs); not checked out |
| Uncommitted, unrelated | GUI files (`hornlab_search/gui/*`, `tools/gui/*`, `tools/system/gui_system_job.py`) — left untouched |
| Fable v2 branch | `origin/claude/adoring-ramanujan-1m4b3g`, tip `d902a33` = merge-base `3a3a4ee` + exactly 2 commits (`a93ac18`, `d902a33`) |
| Live GPU night | `fable_scout40w2_2026-11-19`, runner pid 57376, lock held; see §2 |
| GPU | one solve at a time; `runs/.gpu.lock` is the ownership signal |
| Objective policy | nights default v7; **v10 is opt-in and only this night** (owner handoff; v10 brief header) |

Physical-solve identity (the dedupe key) is **not** the config name: it is
`design_hash-mesh_hash-solve_hash` (`hornlab_search/search/evaluate.py:979-983`), cached under
`cache/solve/p2-<physics-sha12>/<triple>/` (`hornlab_search/solve/cache.py:46-78`). `config_sha` =
sha256 of the canonical effective-config JSON, truncated to 12 hex (`search/rundir.py:40`), and is the
secondary key. Both were used below.

## 2. Live night truth (measured, `runs/nights/fable_scout40w2_2026-11-19/`)

The W2/W3 night has **15 jobs, not 16** (there is no `s40x3__crowe_x_osse_cd_v7`).

| Job | Best J (v7) | Valid/attempts | Note |
|---|---|---|---|
| s40x__fold_warm | 3.6818 | 31/31 | |
| s40x__morph_v8 | 3.2325 | 14/25 | storm |
| s40x__tritonia_v8 | 5.3728 | 30/33 | |
| s40x__tritonia_v9 | 4.8785 | 30/30 | |
| s40x__petal_hvlaw_v7 | **4.1960** | 30/40 | +0.70 vs SCOUT40 |
| s40x__crowe_x_osse_cd_v7 | 5.3454 | 30/38 | |
| s40x__crowe_x_square_v7 | 7.6183 | 16/26 | storm |
| s40x__rosse_rect_cd_v7 | 4.5596 | 32/33 | |
| s40x3__fold_warm | 3.6945 | 30/30 | tie |
| s40x3__morph_v8 | 3.7574 | 13/25 | tie / storm |
| s40x3__tritonia_v8 | **4.8911** | 30/30 | +0.48 real |
| s40x3__tritonia_v9 | 5.0032 | 30/36 | worse than v9 W2 |
| s40x3__petal_hvlaw_v7 | **4.16163** | 41/55 | +0.03 → **tie, no promotion** |
| s40x3__crowe_x_square_v7 | running at recon | | |
| s40x3__rosse_rect_cd_v7 | pending at recon | | |

**Promotion decisions.** ATH petal's W3 continuation is a tie (4.1960 → 4.1616, below the 0.31 J v7
floor), so it is **not** promoted to a v10 campaign on screen rows. Tritonia v8's +0.48 is real;
tritonia v9's W3 point is worse than its W2 point. Both stay held until a `verify` pass produces
complete polars — screen rows alone are not promotion evidence.

## 3. Registry (deduplicated; `config_sha` computed with the real loader)

| # | Candidate | config (`config_sha`) | Score identity | Existing physical history | State for this night |
|---|---|---|---|---|---|
| 1 | Klangfilm-Lame c200 record + V-timing + beak | `fv2/…vbeak_v10_v1` (`d4421ce593df`) | shipped v10 | parent `517217` best `88973b1e44e9` v7-smooth 7.4458 (200/201); seed is a **cache hit** | **new**, after 1-solve control (`e4a84ddb505e`) |
| 2 | Rolled h12 record + V-timing + beak | `fv2/…rolled_rect_record_vbeak_v10_v1` (`8e86f248fb42`) | shipped v10 | parent `643de7` 15/15, v9 J 92.6 (discarded metric, never compared to v10) | **new** |
| 3 | Rolled h12 whole-family hybrid | `fv2/…rolled_rect_hybrid_vbeak_v10_v1` (`18d3919e93bc`) | shipped v10 | seed = `643de7` design `445dafb7e760` | **new** |
| 4 | OSSE rrect fold-warm | `b6/…fold_warm_v7__b6_v10_s1` (`7ede3a202469`) | shipped v10 | no v10 run exists; v7 bases `c221aa` 3.7352, `ab4fb9` 3.6608 | B6 s1 verbatim |
| 5 | Ext-throat H/V law | `b6/…ext_throat_hvlaw_v7__b6_v10_s1` (`5426f5e4ec95`) | shipped v10 | v7 archive leader 2.4976 (`d3a1bb` 3.1028 in another seed) | B6 s1 verbatim |
| 6 | OSSE rrect morph | `b6/…osse_rrect_morph_v7__b6_v10_s1` (`bd75996d25b0`) | shipped v10 | v7 base `07bea2` 3.9918 | B6 s1 verbatim |
| 7 | ATH TwinRay380 v8 | `b6/…ath_twinray380_landscape_v8__b6_v10_s1` (`62ada8396d7f`) | shipped v10 | only aborted v8 runs — no best | B6 s1 verbatim |
| 8 | Bi-Radial searched V-terminal | `u3_biradial_es_style_v7/vt_v1` (**`52628637b069`**) | **v7** (unchanged) | `13c866`, 40/40, J 6.3271, design `0705e7b08d4f` | **same config, budget 80** — first 40 replay deterministically → cache hits, 40 new evals |
| 9 | Klangfilm b3_soft re-homed | `priority10/…b3_soft_v10__p10_s1` (`00a380061d1c`) | shipped v10 | `723756` 41/41 v7-smooth 2.8002 (design `ee85bcd2ad67`) | **new versioned config**, 40 valid |
| 10 | CROWE v2a four-DOF | `priority10/…crowe_v2a_c1_v10__p10_s1` (`09f29d0c187c`) | shipped v10 | `54878f` 40/40, v7-smooth 4.8787 (design `febde0373489`) | **new versioned config**, 40 valid, last |

**Do not re-run:** the exact configs of #8/#9/#10 at their recorded budgets (`526286…`, `7fb61f64dcc8`,
`806e6474b008`), the 15-eval rolled-control pilot (`643de7`; its config no longer loads — drifted v9
keys `oa_excess_tol`, `ripple_window`), and every job id already in the live W2/W3 night.

## 4. CPU-first v10 re-scoring (measured, no GPU)

`tools/analysis/rescore_identity.py rescore <run> --brief …v10.yaml --out runs/analysis/v10_priority10_2026-11-19/<lane>`
replays the stored `response.npz` of every exact-complete design through the canonical
`objective.replay.replay_run_dir`. All three columns carry one score identity
(`8892be0f4d36…`), `mixed_identity: false`, and every row is `exact_complete`.
**Scale check:** re-scoring `54878f` with the *published* column brief
(`docs/evidence/v10_rescore_2026-11-18/home_v10_corridor_preferred_edge_rescore.yaml`) gives
byte-identical J (7.068547250549901 on `febde0373489`), so these numbers sit on the published v10 scale
(the published brief differs only by name; the 166-design parity check is reproduced).

| Lane | designs | v10 best | design | v7-run-best design → v10 | gap to v10 leader 1.4214 |
|---|---|---|---|---|---|
| #9 Klangfilm b3_soft | 41 | **3.7428** | `3545b3e078ac` | `ee85bcd2ad67` → 4.1322 | +2.32 J |
| #10 CROWE v2a | 40 | **7.0685** | `febde0373489` | seed `1c206df9912f` → **10.4104** | +5.65 J |
| #8 Bi-Radial vt_v1 | 40 | 5.2808 | `b62ee8cad5c9` | `0705e7b08d4f` → 5.2973 | +3.86 J (v7 lane; context only) |

Readings **[measured, applied]**:
- #9 is seeded at its **own v10 best** (3.7428), not at its v7 best (4.1322) — v10 prefers a different
  member of the same run. It is 2.32 J behind the v10 leaders at its seed, so it is queued as a
  **construction test** ("beats its own seed by > 0.4677 J"), not as a leaderboard candidate.
- #10's seed is 10.41 under v10 and the family's best stored point is 7.07. It cannot reach the v10
  leaders with 40 evals; it is queued **last** and is expected to be dropped by the cutoff. Its only
  justification is that the v7-smooth run was still improving at its last eval (8.58 → 4.88 at row 39
  of 40), i.e. the four-DOF box is not exhausted.
- v10 rank differences below **0.4677 J** are ties at the current frequency floor (v7: 0.3105 J).
  Small screen gains are not verified improvement; only same brief/source/mesh/grid comparisons count.

## 5. Preflight / fidelity gates (measured, CPU only)

- `compileall` + `tests/test_design_record_body_beak.py`: **7 passed**; `-k "record_body or
  vertical_timing or edits"`: **29 passed, 1 skipped** (botorch absent). No mesh/solve/objective/brief
  file is touched by the Fable v2 commits.
- `shape_check.py --mode screen` — all 4 Fable v2 configs and both new configs build, fit the brief
  envelope, and couple the round driver:

| config | dofs/cap | mouth W×H mm | depth mm |
|---|---|---|---|
| fv2 c200 record control | 4835/24000 | 585×255 | 196 |
| fv2 c200 vbeak v10 | 4835/24000 | 585×255 | 196 |
| fv2 rolled record vbeak | 4952/6000 | 542×299 | 236 |
| fv2 rolled hybrid | 4959/6000 | 542×299 | 236 |
| p10 b3_soft v10 | 2960/24000 | 487×287 | 285 |
| p10 crowe v2a v10 | 4311/24000 | 580×474 | 303 |

- `search_preflight.py --samples 48` (uniform box, upper bound away from the seed):
  - c200 vbeak: **0/48 refused**, no hards/warnings.
  - rolled record: **20/48 mesh_too_large** (42%) — the 6000-dof cap is the limiter; refusals are cheap
    meshes, `max_attempts: 400` covers 40 valid. The night relaxes the refusal-storm stop to 0.55 for
    **this job only**.
  - rolled hybrid: 2/48 refused (4%).
  - B6 morph and B6 twinray: 3/48 `invalid_geometry` each (93.75% valid) — no storm gate.
- `run_campaign_night.py --dry-run --admission …`: **admission accepted, 11 jobs**, every argv valid,
  no zero-free-dimension search.

### 5b. Control gate result (measured at launch, 2026-11-19T11:57 local)

`p10__fv2_kl_record_control` — `hornlab-search run --mode screen`, 1 solve, run
`runs/20261119T165650Z-screen-f30e50`:

```
terms (raw): cov=1.09  rip=0.04333  di=0  dislope=0.7269  flat=0.3433  load=0.7171  penalty=0  total J=7.44663  n_nan=0  DI source=balloon
run OK: seed J=7.44663, 4835 dofs, solve 23.5 s
```

Stored parent J is 7.4458 → **|ΔJ| = 0.0008**, inside the predeclared 0.05 J tolerance. The
canonical-record route replays the c200 parent acoustically, so lane #1 was allowed to start
(`p10__fv2_klangfilm_vbeak`, run `20261119T165732Z-screen-3ebb94`).

## 6. Staged execution order

`p10__fv2_kl_record_control` → `fv2_klangfilm_vbeak` (#1) → `fv2_rolled_record_vbeak` (#2) →
`fv2_rolled_hybrid` (#3) → `b6_fold_warm_s1` (#4) → `b6_ext_throat_s1` (#5) → `vt_v1_probe80` (#8) →
`b6_twinray_s1` (#7) → `b6_morph_s1` (#6) → `klangfilm_b3_soft_v10` (#9) → `crowe_v2a_v10` (#10).

- #4–#7 are the **s1** seeds only; s2 is added after s1 is read, never before.
- Estimated [inferred, from the W2/W3 timings of 15–25 min per 40 valid]: ~7–9 h for all 11 jobs.
  The tail (#9, #10) is expected to fall to a cutoff.
- Launch is **serialized behind the live night**: `queue.ps1 -WaitPid 57376 -WaitMatch fable_scout40w2`
  — the runner's own pre-hygiene kills stale Julia hosts, so a second concurrent runner is forbidden.
- Per-job `HORNLAB_GPU_LOCK: refuse` for unattended operation. `queue_state.json` job ids are never
  re-run, so re-reading the night file cannot duplicate work.

## 7. Known risks / open items

1. **B6 fold_warm carries the pin that stopped its v7 chain** (`az_fold_h_deg` high 0). The config is
   run verbatim to preserve the B6 protocol; if it pins, that is the measured answer and the widen
   (to +10, as in W2) belongs in s2. `sigma0 0.25` with ~30 free keys is above the repo's 8-key rule
   for both OSSE B6 lanes — left as authored; the watchdog and `budget_counts: valid` contain it.
2. **HF1440 is modelled** (36 mm exit, chosen 2° entrance tangent). The 2° outlet wavefront is not a
   manufacturer certification; all comparisons hold the source fixed and say nothing about real-driver
   performance.
3. **Rolled record mesh cap** (6000 dof) is the reason for the 42% refusal rate; raising it would change
   the lane's cost model, so it was not changed.
4. Petal/tritonia promotions are **held** pending `verify` polars; the W3 night's screen rows are not
   enough.
5. The Fable v2 queue edit (`docs/queue/fable_scout40_2026-11-19.yaml`, 4 jobs above a completed night)
   was **deliberately not integrated** — only the new jobs were extracted into this night, so the old
   night cannot be rerun wholesale.

## 8. Manifest of what this night buys

| # | New BEM time? | Control | Success test |
|---|---|---|---|
| 1 | yes (control + 60 valid) | 1-solve smooth replay, must be within 0.05 J of 7.446 | beat own v10 seed by > 0.4677 |
| 2 | yes (40 valid) | own seed = host | beat own seed by > 0.4677 |
| 3 | yes (80 valid) | own seed = h12 best | beat own seed by > 0.4677; compare with #2 |
| 4 | yes (120 valid) | lane seed only | matched v10 lane; floor-aware tie |
| 5 | yes (120 valid) | lane seed only | matched v10 lane |
| 6 | yes (120 valid) | lane seed only | matched v10 lane; storm-contained |
| 7 | yes (120 valid) | lane seed only | matched v10 lane |
| 8 | yes (80 valid, 40 new) | existing 40 valid replay | beat the WP4.3 control by > 0.3105 J |
| 9 | yes (40 valid) | own v10 best (3.7428) | beat own seed by > 0.4677 |
| 10 | conditional (40 valid) | own seed (10.4104) | beat own seed by > 0.4677; cutoff-droppable |

Post-run, this table is completed with run ids, valid/refused counts, and the next best measured
action; nothing is promoted without `verify` (complete polars, same source/mesh/grid).

## 9. Rolling results (measured; night still running at the time of this entry)

Read-out command: `.venv\Scripts\python.exe tools\night_status.py --since-hours 12`, plus
`runs/nights/fable_priority10_2026-11-19/summary.jsonl`. Job ids in `queue_state.json` are never re-run.

| Job | Run | Valid/rows | Seed J (v10) | Best J | Gain | Verdict |
|---|---|---|---|---|---|---|
| p10__fv2_kl_record_control | `20261119T165650Z-screen-f30e50` | 1/1 | — | 7.44663 (v7) | | **gate passed** (parent 7.4458, \|Δ\| 0.0008) |
| p10__fv2_klangfilm_vbeak (#1) | `20261119T165732Z-screen-3ebb94` | 30/30, 0 refusals | **8.4198** | **8.3910** (n 13, `2edf3ea06d10`) | **+0.029** | **fails** the >0.4677 bar; watchdog `no_gain_valid` |
| p10__fv2_rolled_record_vbeak (#2) | `20261119T170937Z-screen-ba0f14` | 30/30, 0 refusals | **15.547** | **15.320** (n 27, `d16ae26ca974`) | **+0.227** | **fails** the >0.4677 bar; watchdog `no_gain_valid` |

**Why both record lanes stalled (measured term split, seed → best).**

- c200 (#1): `cov_profile 0.703 → ~0.70`, `rip 0.043`, `flat 0.343 → 0.338`, `load 0.717`,
  **`dislope 6.347 → 6.334`**, `flat_cv 0.176 → 0.180`, `di_roughness 0.262`. Total 8.42 → 8.39.
- rolled (#2): `cov_profile 1.844 → 1.810`, `flat 0.849 → 0.853`, `load 0.659 → 0.654`,
  **`dislope 11.114 → 10.922`**, `di_roughness 0.627 → 0.620`, `flat_cv 0.834 → 0.843`. Total 15.55 → 15.32.

Both hosts' v10 cost is **dominated by `dislope`** (75 % and 71 % of total J respectively). The two
searched freedoms — record-level V timing and the V-lip beak — move the V plane, not the DI-vs-frequency
slope, so they cannot pay on this score at this budget. This is a **construction/score mismatch finding,
not a mesh or solver problem** [measured]: 0 refusals, 30/30 valid, 5-6 GHz-cap-free solves, VRAM
689 → 690 MiB, and the control replayed the parent exactly.

Consequences applied to the plan (no new GPU time spent to learn them):
1. #1/#2 are not continued. Their s2 slot stays empty; a c200/rolled rescue would have to search a
   *DI-slope-relevant* freedom (mouth area law / H-wall turn), i.e. a new construction, not more of these
   knobs — that is a senior-plan decision, not a silent retune.
2. #3 (rolled hybrid, 80 valid) is now the lane that matters for this family: its 13 knobs include mouth
   width/height, corner exponent, throat/rect turn and terminal angle, which are the terms that can move
   `dislope`.
3. The v10 leader comparison is unchanged: fold_warm 1.4214 / morph 1.4305 / ext_throat 1.5710 remain the
   only lanes inside one floor of each other.

Remaining jobs at this entry: #3 running, then #4, #5, #8, #7, #6, #9, #10 (see §6 for order).

### 9b. #3 rolling-rect whole-family hybrid — closed, big gain, still far from the leaders

Run `20261119T172313Z-screen-081506`, **closed by watchdog at 30 valid / 80 budget** (`no_gain_valid`,
34 rows, 4 `mesh_too_large` refusals, 0 invalid geometry/envelope):

| | seed (h12 host) | best (n 16) | Δ |
|---|---|---|---|
| total J (v10) | 15.549 | **9.305** | **−6.24** |
| dislope | 11.114 | 7.322 | −3.79 |
| cov_profile | 1.844 | 0.631 | −1.21 |
| flat_cv | 0.834 | 0.410 | −0.42 |
| load | 0.659 | 0.523 | −0.14 |

Reading [measured]: the family box passes the predeclared bar by 13× (6.24 vs 0.4677 J), and it does so
by moving exactly the terms the record lanes could not — `dislope` −3.79 and `cov_profile` −1.21. It
still sits **7.88 J behind the v10 leader (fold_warm 1.4214)**, so it is a construction answer, not a
leaderboard contender. The watchdog ended it early because the last 30 valid evals produced no gain —
the basin, not the budget, was the limit.

**Protocol consequence [measured]:** a night job's `budget` is a cap, not a guaranteed eval count. The
no-gain watchdog ends a stalled lane at ~30 valid, so the B6 lanes' "120 valid" will often close near
30–45. That is the expected behaviour and it is what saves the tail; read `valid_rows_window` in
`summary.jsonl`, never the requested budget.

### 9c. #4 OSSE rrect fold-warm, v10 matched rerun — reproduces the rank, does not improve it

Run `20261119T173516Z-screen-c6a93f`, watchdog at **45 valid**:

| | value |
|---|---|
| seed J (v10) | 1.8693 |
| best J (n 40, `cfc32f70f7b8`) | **1.5433** |
| gain | **0.326** — *below* the 0.4677 floor ⇒ noise-level |
| published offline v10 rescore of the old fold-warm design | 1.4214 |
| best design's free knobs | `az_fold_h_deg −0.048`, `az_fold_v_deg 1.470`, `az_fold_h_width 13.0`, `az_fold_v_width 8.35` |
| best terms | cov 0.016, flat 0.418, load 0.101, dislope 0.413, di_roughness 0.443, flat_cv 0.152 |

Readings [measured]: (a) the **known v7 pin did not recur** — the authored `az_fold_h_deg` box
`[-15, 0]` was not the limiter under v10 (the optimum sits at −0.05); (b) the fresh search lands 0.12 J
*worse* than the offline-rescored old design, i.e. **inside the floor = a tie**, so the matched rerun
confirms the v10 rank but buys no verified improvement; (c) the family's remaining cost is flat 0.42 +
di_roughness 0.44 + dislope 0.41 — no single dominant term, which is why further evals stalled.

### 9d. #5 ext-throat H/V law, v10 — real gain from its seed, still a tie with the old best

Run `20261119T174850Z-screen-2d9f2a`, watchdog at **31 valid / 39 rows** (8 `invalid_envelope`):

| | value |
|---|---|
| seed J (v10) | 2.8692 |
| best J (n 36, `925868ab64d9`) | **1.7919** |
| gain | **1.077** — above the floor (real), but… |
| published offline v10 rescore of the v7 archive leader | 1.5710 |
| delta to that | +0.22 ⇒ **inside the floor = tie** |
| best terms | cov 0.010, **flat 0.636**, load 0.000, dislope 0.000, **di_roughness 0.510**, **flat_cv 0.726** |

Reading [measured]: the ext-throat lane is now fully inside the corridor and the DI-slope terms
(`load 0`, `dislope 0`), and pays only for spectral flatness/roughness. It **does not** beat the old
design on the same score — the matched rerun reproduces the family's position (tie), it does not advance
it.

### 9e. #8 Bi-Radial searched V-terminal — the freedom cannot pay, and the reason is loading

Run (same config as the 40-valid `13c866`, budget 80), watchdog at **42 valid / 42 rows, 0 refusals**:

| | value |
|---|---|
| seed J (v10) | 6.3374 |
| best J (n 40, `ed00e69fb0a6`) | **6.3221** |
| gain over 40 extra evals | **0.015** ⇒ nothing |
| best terms | **load 3.487**, flat 0.645, flat_cv 0.384, dislope 0.269 |

Reading [measured]: 52 % of this host's v10 cost is **throat loading** (`load 3.487`). The searched
V-terminal width/hold changes the radiation plane, not the throat impedance, so the freedom that showed
+32° of V authority at a fixed V=460 mm buys **0.015 J** on a complete horn. This is the handoff's
"beamwidth movement is not a horn improvement" concern, confirmed at the score level: the first 40 evals
replayed as cache hits and the 40 new ones found nothing.

### 9f. #7 ATH TwinRay380 v10 — real gain from its seed, but it never had the 1.7726 design

Run `20261119T175926Z-screen-8454e6`, watchdog at **31 valid / 31 rows, 0 refusals**:

| | value |
|---|---|
| seed J (v10) | 3.5212 |
| best J (n 25, `bff6107b01a1`) | **2.5748** |
| gain | 0.946 (above floor) |
| published offline v10 best for this lane | 1.7726 (`20261117T001240Z-screen-7b664f`, design `85c59331e4a3`) |
| delta to it | **+0.80 ⇒ outside the floor** |
| best terms | cov 0.018, flat 0.486, **load 0.747**, dislope 0.388, di_roughness 0.495, flat_cv 0.465 |

**Seeding audit (measured) — this is the important part.** The B6 s1 configs are seeded from the lane's
*original* seed, not from the design that produced the published v10 lane best. Verified parameter-by-
parameter against `search.ndjson` rows:

| B6 s1 config | seed vs published-best design | seed J_v10 | published best J_v10 |
|---|---|---|---|
| twinray380 v8 | 13 of 27 shared knobs differ (e.g. `L_mm` 203.4 vs 311.6, `morph_height_mm` 357 vs 440) | 3.5212 | 1.7726 |
| osse_rrect morph v7 | 14 of 31 differ (`L_mm` 250 vs 282, `n` 6.90 vs 8.21, `morph_rate` 3.0 vs 3.67) | 3.0570 | 1.4305 |
| fold_warm / ext_throat | published `lane_best.run` is the dataset shard `"screen"` (no run dir), so the comparison is by J only | 1.8693 / 2.8692 | 1.4214 / 1.5710 |

Consequence [measured, applied]: the 0.12–0.80 J shortfalls of the B6 s1 lanes are **not** evidence that
the offline v10 numbers are wrong, and **not** a capability verdict on those constructions. The s1 runs
re-found the basin from a different start. A genuine "matched continuation" for s2 must warm-start each
lane at the **published best design's run + design hash**, not at the lane seed. Until that is run, the
published v10 lane bests (fold 1.4214, morph 1.4305, ext 1.5710, twinray 1.7726) remain the ranking
evidence and the PRIORITY10 s1 numbers are reproduction checks only.

## 10. Reconciliation for the compact-horn / woofer-crossover handoff (2026-11-19, later same day)

The owner's second handoff (compact sculptural horns + woofer crossover) says to reconcile commit and
queue status before acting. Measured now:

| Item | Status |
|---|---|
| `origin/main` | `138d88a2163c` — unchanged, so **PR #75 is not merged upstream** (the Fable branch tip `d902a33b1db` is still the only delta) |
| `gh pr view 75` | **unavailable from this session** — `gh` cannot resolve `llevachingada/Hornfab` (auth/visibility), so PR metadata is UNVERIFIED; `git ls-remote` confirms the refs above |
| Our tree | commits `627b880` + evidence commits are **local only** (not pushed): they contain the PR's four configs + record-edit code + tests, deliberately **without** its SCOUT40 queue prepend |
| SCOUT40 / W2 / W3 | **finished**; results in `runs/nights/*/summary.jsonl`. Nothing from them is re-queued |
| PRIORITY10 night | running (`#6 morph` at the time of writing, then `#9`, `#10`); it owns the GPU lane |
| New GPU work | **not authorised by this session** — the compact-horn handoff's T2 allowance (0–4 isolated + ≤2 verify) stays unspent until its shortlist exists and the lane is free |
| Shared-tree hazard | another lane currently has uncommitted edits to `tools/analysis/rescore_identity.py` and its test; the CPU sub-agent was told not to touch them |

The compact-horn candidate register itself is owned by the CPU sub-agent
(`docs/research/compact_horn_system_2026-11-19/`), not by this document.







