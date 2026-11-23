# ACTIVE_STATE — current pointer

**This is a pointer, not authority.** It names where current state lives and what was verified when
it was last written. If it disagrees with the tools below, the tools win.

Last verified: **2026-11-20** against HEAD `cfa7846` (+ the docs/handback commit). The GPU lock was
stale-held (holder pid gone) at this check; run `gpu-clean` before any solve.

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

- **2026-11-23 09:05 EST (overnight top-up closed):** `bo_data_topup_2026-11-22` (other lane)
  6/6; it resumed the round-3 open run dirs in place. New screen bests: compact500 Crowe
  **1.70512** (770x548x393, `138f09ce5472`), FAV **3.30792** (720x608x418, `5987a94e99c0`),
  v11 Fold **3.42866** (522x445x423, `606abb301970`); the other five leaders unchanged. The
  `docs/renders/2026-11-22-best-horns` gallery was re-rendered on 2026-11-23 and republished.
  None verify-grid confirmed. Lane free.


- **2026-11-22 20:10 EST (round 3 closed, open envelope):** `hornfab_round3_2026-11-22` 7/7 with
  `envelope.enforce: false` (sanity 1200 mm). Screen bests: home Fold 1.3087 -> **1.1932** (k=3.36,
  past the old 2.81 cap; still inside the old 600x480 box), compact400 1.0243 -> **0.9679**
  (474x350 mm, outside the old 400 cube), compact500 Crowe 2.7579 -> **1.8150** (719x538x386; g_L
  pinned at the new 400), FAV 4.1990 -> **3.3848** (730x577x403), v11 Fold no gain. Zero envelope
  refusals; 0-37.5 % `invalid_geometry` at the opened extremes. None verify-grid confirmed.
- **2026-11-22 (verify + round 2):** verify 8/8: home fold_s **1.4727**, fold_k 1.5551, morph 1.7484,
  twinray 2.1593 (leader 1.4867, floor 0.4677 -> tie/worse); compact400 s2 **1.1532**, s1 1.2293
  (best 1.1864, floor 0.1293 -> tie); c500 2.8570; FAV 4.5828. Round 2 lifted c400 1.0243, c500
  2.7579, FAV 4.1990, v11 fold 3.6172.
- **2026-11-22 (decision + renders):** owner: the brief envelope no longer refuses candidates;
  `config.effective_envelope_limits` is the one source (default byte-identical) for the post-mesh
  gate, both pre-mesh estimators and `tools/shape_check.py`; 84 focused tests. Eight leaders
  rendered at 200 dpi: `docs/renders/2026-11-22-best-horns/` (gallery `index.html`, Pages).
- **2026-11-22 (queue 1):** `hornfab_12h_2026-11-22` 10/10, all watchdog-stopped: TwinRay
  2.5748->1.7356, Morph 1.5769->1.3973, c400 1.1891->1.0742, home Fold 1.3738->1.3176/1.3087,
  c500 2.9901->2.8392, FAV 4.4527->4.4305; v11 Fold no gain.

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
