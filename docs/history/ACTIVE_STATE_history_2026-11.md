# ACTIVE_STATE — current pointer

**This is a pointer, not authority.** It names where current state lives and what was verified when
it was last written. If it disagrees with the tools below, the tools win.

Last checked **2026-11-25** in the canonical checkout, branch `hornfab-all-2026-11-18` at `626a7c65` with local changes.
Size-aware constraints and the two body experiments are indexed in the [current handoff](evidence/size_aware_2026-11-24/HANDOFF.md).
The bounded GPU queues are [exact anchors](queue/rolled_lame_anchor_verify_2026-11-24.yaml),
[body variants](queue/rolled_lame_body_verify_2026-11-24.yaml) and
[Compact500 size finalists](queue/size_aware_crowe_verify_2026-11-24.yaml). Use live status for GPU readiness.
Directivity attribution (2026-11-24/25): [readout](evidence/directivity_attribution_2026-11-24/README.md), queues
[batch 1](queue/directivity_attribution_2026-11-24.yaml) and [batch 2](queue/directivity_attribution_b2_2026-11-24.yaml) (finished).
CD wall-angle backbone (2026-11-25): [readout](evidence/cd_backbone_2026-11-25/README.md), queues
[batch 1](queue/cd_backbone_2026-11-25.yaml), [batch 2](queue/cd_backbone_b2_2026-11-25.yaml) and [dose bracket](queue/cd_backbone_b3_2026-11-25.yaml) (finished; passing band rolled bb_h 0.45-0.50, 0.50 best, J 8.121 -> 5.407).

Metric-aware BO (2026-11-25): the Home v11 Fold loop is proven end-to-end (clean 8+2 canary, two refits, post-refit proposals, verify 4.791516). The adaptive 20-screen tranche and four native/900 Hz canaries are staged but held; release requires owner GPU authorization. Admission table and handoff: `docs/research/metric_bo_2026-11-22/12_HANDOFF_2026-11-24.md`. Regression 512 passed / 0 failed / 0 skipped.

## Verify first (never trust this file alone)

```powershell
.venv\Scripts\python.exe tools\night_status.py --since-hours 48
git log --oneline -5; git status --porcelain
```

## Workspace

- Canonical checkout: `C:/Users/hunte/Hrns/hornlab-search` (owner amendment 2026-11-12).
- Start OpenCode here. Umbrella sessions in `Hrns` get the eight `hornlab-*` skills only through
  `Hrns/.opencode/opencode.jsonc` - see `docs/AGENT_BOOTSTRAP_CONTAINER.md`.

## Branches (D10/R21 integration, 2026-11-18 evening)

- **Integration is DONE:** PR #69 (cloud->hornfab-all, `382c682`), #67 (plan->main, `63c23a8`),
  #70 (hornfab-all->main, `fbbf4236`); #68 closed superseded. `hornfab-all-2026-11-18` carries the
  newest work and `main` is kept current (see HEADs at read time).
- **A resuming cloud (Fable senior) session must NOT reuse** `cloud/fable-next-2026-11-18`
  (stale, provenance at `1e9f71b`): branch from `hornfab-all-2026-11-18` (or `main` after merge)
  and send work as PRs into `hornfab-all-*` (R21; the local orchestrator is the single integrator).
- Owner decisions R1-R25: `scratch/fable_architecture/OWNER_DECISIONS_RESOLVED_2026-11-18.md`;
  local execution state: `HANDOFF_2026-11-18.md` evening section.

## State, at write time

- **2026-11-25 15:50 EST (favL__2in_c500 continuation live):** owner asked to open the wall-pinned
  knobs, narrow the inert ones and continue the 2-inch compact500 run for 150 valid screens.
  Built `examples/briefs/hf2in_2026-11-20/compact500_xo900_80x50_hf2in_v11cd_open115.yaml` (envelope
  `enforce: false`, `max_utilization: 1.15`, no soft size term in J) and
  `examples/typologies/favL_2026-11-20/favL__2in_c500_open115.yaml` (seed = parent best
  `0ae816f04c06`, J 1.870458; g_k/a_v/throat opened off their walls; inert sf_amt/sf_ab/n/a_h/L/
  wrap/r_lip narrowed; warm start from `runs/20261121T003823Z-screen-75c147`, sigma0 0.12).
  Preflight: 64/64 meshed samples valid, shape check 4117 DOF, BO encoding d=11 round-trip, 6/6
  dataset rows replay into one metric-cohort group. Job `favl_c500_open115_150` runs first in
  `cd_bo_cohort_2026-11-25` (run `runs/20261125T204727Z-screen-02b4bf`); best 1.691470 by n=4.
  Evidence `docs/evidence/favL_2in_c500_continue_2026-11-25/`.

- **2026-11-23 13:31 EST (BO-250 review + queue):** reviewed 443 runs (2026-11-09..23). The
  metric-aware BO gate needs >=100 usable screen rows per frozen identity and a widened box or a
  changed brief is a NEW identity, so 250 solves buys two identities at the gate. `hornfab_bo250_2026-11-23`
  is live (pid 57016, cutoff 17:30): (A) compact400 v11 open, the v10 fleet best 0.96787 ported onto
  the v11 CD scorer (same target 80/50, 350-8000, f0 1000), 150 valid, pins opened `a_deg` hi,
  `morph_rate` lo, `morph_corner` lo; (B) room w90x50 v11 open, +10.6% over its last 40 valid with
  `g_a_h_deg` pinned low and `g_s` pinned high, 100 valid. Both v11, open envelope, best-seeded.
  Configs `examples/typologies/round4_2026-11-23/`, briefs `*_open_2026-11-23`. Not queued:
  compact500 2-inch (4 pins), room w90x60 (`g_s` hi), a9 (`g_sf_ab` hi), compact400 w90x50 (+9.1%).

- **2026-11-22 16:00 EST (open envelope + round 3 live):** owner decision: the brief size envelope no
  longer refuses search candidates. `envelope.enforce: false` + `envelope.sanity_max_mm` (default
  1200 mm per dimension) is implemented in `config.effective_envelope_limits` and used by the
  post-mesh `envelope_violation`, both pre-mesh registry estimators and `tools/shape_check.py`;
  default (absent/true) is byte-identical. Four `*_open` briefs and seven round-3 configs are in
  `examples/briefs/*_open_2026-11-22.yaml` / `examples/typologies/round3_2026-11-22/`; these are NEW
  identities and their J is not comparable to closed-envelope runs or published floors. All
  watchdog-pinned/near-limit knobs were opened (home Fold k/q/az_a_cos_amp/L/morph W,H; compact400
  morph_rate/az_fold_v_deg/az_a_cos_amp; compact500 g_a_h low 4/6; v11 Fold a0_deg low 5/6). Night
  `hornfab_round3_2026-11-22` is live (pid 7460, cutoff 20:00, 7 jobs, `no_gain_valid`/`stall_valid`
  60). Preflight on the opened boxes: zero envelope refusals, 0-37.5 % `invalid_geometry`. Record:
  `NOTES_FOR_SENIOR.md` 2026-11-22 block.

- **2026-11-22 11:50 EST (round 2 closed):** `hornfab_round2_2026-11-22` recorded 7/7 in ~1 h,
  again every job via the watchdog. Screen bests: c400_open_b 1.0742 -> **1.0243** (pinned
  az_fold_v_deg high), c500_local_cont 2.8392 -> **2.7579** (refusal 50 %, 18 valid), fav_crowe_wrap
  4.4305 -> **4.1990** (refusal 47 %, 32 valid), v11 fold corner 3.6930 -> **3.6172** (pinned a0_deg
  low 5/6); h_fold_kq a/b and c400_open_a stopped at 30 with no gain over the seed. All refusals in
  play are `invalid_envelope` from the FREEFORM grid generator's pre-mesh estimate (zero
  tolerance), driven by `g_L_mm`: c500 refused 6 % below 260 mm, 50 % at 260-280, 100 % at >=280.
  Nothing verified this round yet. `examples/typologies/round2_2026-11-22/`; lane free.

- **2026-11-22 10:48 EST (verify done, round 2 launched):** `hornfab_verify_2026-11-22` ran 8/8
  (`run --mode verify`, 8 new configs under `examples/typologies/verify_2026-11-22/`). Verify J:
  home v10 fold_s **1.4727**, fold_k 1.5551, morph 1.7484, twinray 2.1593 (reference: fold s2w
  1.4867, published 1.6704, floor 0.4677 -> fold_s/fold_k TIE the leader; morph/twinray do not
  beat it). compact400 s2 **1.1532**, s1 1.2293 (previous best 1.1864, floor 0.1293 -> TIE).
  compact500 crowe 2.8570 (first verify row for this identity); v11 FAV 4.5828 (prior 4.6493).
  Screen J is a poor cross-family predictor (gap +0.6 % c500 to +25 % morph). Round 2
  `hornfab_round2_2026-11-22` followed (see above): home Fold k<=3.0/q<=1.0 box x2
  seeds, compact400 morph_rate/az_a_cos_amp opened x2 seeds, c500 resume with refusal_max 0.45,
  v11 Fold corner<=15, FAV g_wrap>=25. Configs in `examples/typologies/round2_2026-11-22/`.
  TwinRay and Morph get no further GPU time this round.

- **2026-11-22 10:07 EST (queue closed):** `hornfab_12h_2026-11-22` recorded 10/10 at 04:32, NOT at the
  14:50 cutoff: every job ended via the watchdog (exit 75) after 25-204 evals, 110 min total. Real
  best-J moves (screen grid, unverified): TwinRay 2.5748 -> 1.7356 (+33%, stopped at the brief
  envelope morph_height 480), compact400 Fold s2 1.1891 -> 1.0742 and s1 1.1501, Morph 1.5769 ->
  1.3973 (stalled 204/219), home Fold k 1.3738 -> 1.3176 (pin: q high) and s 1.3087 (pin: k high),
  c500 Crowe 2.9901 -> 2.8392 (refusal 33% @27 attempts), FAV 4.4527 -> 4.4305, v11 Fold no gain,
  2-inch 1.8705 -> 1.9330 (refusal 64% @25). Job 9 (verify) did not run and no common-grid
  confirmation exists yet. Lane free, no julia; `runs/.gpu.lock` holds dead pid 56760 (next runner
  takes it over - do not delete by hand). Per-job reasons: `runs/nights/hornfab_12h_2026-11-22/`.
  Next: verify the improved finalists, then round 2 that widens the pinned knobs (q, k,
  morph_rate, az_a_cos_amp) and sets pin_ignore on envelope-capped knobs.

- **2026-11-22 02:42 EST:** `hornfab_12h_2026-11-22` launched as a detached controller (pid 54452,
  parent WmiPrvSE), cutoff 14:50. Ten sequential GPU jobs reconciled from the 12-hour advisor queue:
  Morph resume (cap 120->340), v11 Fold resume (50->270), compact500 Crowe local (new box), TwinRay
  resume (120->320), home-v10 Fold k- and s-expansions, compact400 Fold 2x80 independent seeds, FAV
  resume (60->220), 2-inch bounded follow-up. Two resume jobs carry explicit watchdog overrides
  (TwinRay `pin_ignore: morph_rate/morph_width_mm`; FAV `refusal_max: 0.55`) because the pure
  `watchdog_verdict` replay over the historical rows stops them on the first poll. The advisor's
  job 8 (resume 75c147) was replaced by the pre-staged `favL__2in_c500_unbound_followup` config.
  Live state: `runs/nights/hornfab_12h_2026-11-22/queue_state.json`; log
  `runs/nights/queue_hornfab_12h_2026-11-22.log`. Verified after launch: julia host up, Morph
  `search.ndjson` 121 -> 125 rows. Verification job 9 is to be inserted by live edit once finalists
  exist. Five new configs are untracked under `examples/typologies/` (not yet committed).

- **2026-11-21 (local, no GPU):** optimizer audit P0/P1 implemented as opt-in/offline code: CMA-MAE v3 split archives, full-identity floor registry, v10/v11 study admission, covariance-transfer warm start, composed advisory report and matched-benchmark plan/report. No queue, default or score version changed; P2 needs matched real-BEM authorization and owner GPU approval. [Status](research/optimizer_audit_2026-11-21/IMPLEMENTATION_STATUS.md).

- **2026-11-21 08:57 EST:** `sculpted_xo900_cma_pilot_2026-11-21` launched as detached controller PID 12984. Three V11 screen tranches precede matched verification and conditional 60-valid extensions. Read `runs/nights/sculpted_xo900_cma_pilot_2026-11-21/queue_state.json` for live state. [Queue recipe](queue/sculpted_xo900_cma_pilot_2026-11-21.yaml).

- **2026-11-21 08:30 EST:** `sculpted_xo900_acoustic_discovery_2026-11-21` finished 7/7. The queue registered six existing observations and measured one new native R2 truncation probe under home-900 V11. The GPU lock was free at close. [Matched acoustic readout](evidence/sculpted_xo900_v11_2026-11-21/README.md).

- **2026-11-21 04:21 EST:** `hornfab_gpu8_2026-11-21` launched detached as controller PID 16772. Seven sequential blocks reserve six hours for new geometry and two for proven-horn follow-up. Pending jobs use nonbinding packaging limits by owner direction. Live state is `runs/nights/hornfab_gpu8_2026-11-21/queue_state.json`; per-block results are indexed in its `readout.json`. Wall-clock admission closes about 12:21 EST and the queue can finish earlier. Recheck the live GPU lock before any solve.

- **2026-11-20 afternoon:** night `fav_crowe_2026-11-20` queued behind `cd_v11_verify_and_expand_2026-11-20`
  (FAV-001 k-variants + compact500_xo900); see CONTINUITY.

- **GPU lane:** FREE. `p12_verify_2026-11-19` ran 6/6 (~20 min): compact400 trio is a 3-way verify
  tie (morph 1.1864 > fold 1.2763 > twinray 1.3734, gaps < floor 0.1293); home v10 fold s2w beats the
  published best by 0.184 J on the same verify grid (1.4867 vs 1.6704); **ext-throat v10 closed**.
  Evidence: `docs/evidence/P12_VERIFY_2026-11-19.md`. Next GPU move (owner): full polars on the trio.
- **Q3 (done, ~45 min):** v10 leaders are **box-limited** (fold L_mm high, ext-throat az_a_cos_pow
  low), crowe v2a closed at 6.4779 (tie), first-ever solves of Le Cleach H/V 7.8865 and Crowe ES
  biradial 9.2355, new rows type `lecleach_ar` storm-limited.
- **Staged, NOT launched (owner GPU approval needed):** `docs/queue/compact400_next10_2026-11-19.yaml`
  - 8 lanes for horns inside a 400 mm cube under the new `compact400` identity: floor 0.1293 J, stored bar 1.7302.
  - 2 home v10 s2w warm starts.
  - Readout: `docs/research/compact400_2026-11-19/README.md`.
- **CPU lane:** free. Compact-horn candidate register (10 rows, measured geometry/config_sha) is in
  `docs/research/compact_horn_system_2026-11-19/`; its one conditional GPU ask FAILED its own gate
  (A1 v10 1.9858 vs 1.4214+0.4677), so no GPU was authorised.
- **System evidence queue:** RAN (CPU lane, no GPU) — LF 20-200 Hz, 2x2 wide, 10 m, 49-freq,
  screen replay, census; then real-motor assembled (25/25 + LF 12/12) and two refined-mesh
  49-freq cases. Census now **54 cases / 19 solved / 29 staged / 3 refused / 3 invalid**. Readout:
  `docs/evidence/system_evidence_2026-11-19/README.md`. The #4 LF first attempt failed on the wrong
  port and was retained; corrected retry completed 12/12. **Mesh convergence is NOT established**
  (nulls move up to ~16 dB between meshes); do not rank small system differences yet.
- **System layer:** 37 case dirs = **5 solved / 27 staged / 3 refused / 2 invalid** (the 9 readiness
  cases are 5 solved + 2 staged + 1 refused + the 62864 clearance case). The pilot fidelity/Pareto
  contract is fixed and tested (`pilot --geometry` now works; `score.validate_axes` rejects nested
  axes/list feasibility). Full `tests/system` passes with 7 real-BL env gates.
- **GUI:** Horn + woofer complete through the 2026-11-20 senior review: Overview landing,
  wizard/Quick launch, screens + readable shortlist, cases + 3D, compare + 2x2, locked crossover,
  stage/validate/solve dialogs (solve disabled, decision 6), readiness. Registry v2: 20 approved /
  5 proposed. Tests 1,117 / 1 pre-existing failure; final browser sweep 104/104; keyboard 14/14;
  handback `docs/research/system_woofer_2026-11-18/GUI_HANDBACK_2026-11-20.md`. Other lanes'
  uncommitted edits still exist; stage only your own hunks.
- **Objective versions:** never rank J across versions; v7 = nights' default (R1), v10 = shipped
  second score and OPT-IN ONLY (this night runs it by owner handoff), v10_slope5 = its own identity
  (floor 0.486 J published; diagnostic). Never edit `hornlab_search/objective/scalar_v9.py`.

## Where the rest lives (bounded reads)

| Need | Read |
|---|---|
| Newest status entry | `docs/CONTINUITY.md`, first 60–80 lines only |
| Owner's favorite horns (seeds, renders) | `docs/favorites/FAVORITES.yaml` (FAV-001 Crowe-X; research `docs/research/favorites_2026-11-20/`) |
| Open issues / TO-DO | `docs/ISSUES.md`, first 60–80 lines, then search by ID |
| Senior rulings, blockers | `NOTES_FOR_SENIOR.md`, last 60 lines, then search |
| Next-round priorities | `docs/NEXT_DEV_PRIORITIES.md`, current section only |
| Doc map / module map | `docs/INDEX.md` / `docs/CODE_MAP.md` — search, do not read whole |
| Horn + woofer system + GUI handoff | `docs/HORN_WOOFER_SYSTEM_HANDBOOK_2026-11-19.md` (one-file senior packet) |
| Senior engineering decision (this round) | `docs/HORNFAB_SENIOR_DECISION_2026-11-19.md` (fidelity, source normalization, evidence plan, search/GUI) |
| Solve-data exports | `docs/top_designs/` (horn GPU) + `docs/system_data/` (system cases/screens) |
| Queue mechanics | `tools/night_status.py`, `runs/nights/`, queue logs in `runs/` |

Never load the living logs in full; they are hundreds of KB each. Any document over ~100 KB is
grep-only.

## Maintenance

Update this file in the same commit as any change to the active queue, the objective default, or the
canonical checkout path. Keep it under ~60 lines; if it grows, it has stopped being a pointer.
