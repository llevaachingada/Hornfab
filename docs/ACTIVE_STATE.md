# ACTIVE_STATE — current pointer

**This is a pointer, not authority.** It names where current state lives and what was verified when
it was last written. If it disagrees with the tools below, the tools win.

Last verified: **2026-11-20** against HEAD `1dd8053` (+ local commits ahead of origin). The GPU lock
was stale-held (holder pid gone) at this check; run `gpu-clean` before any solve.

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
  screen replay, census. **9 solves complete**; census now **47 cases / 14 solved / 29 staged /
  3 refused / 2 invalid**. Readout: `docs/evidence/system_evidence_2026-11-19/README.md`. The #4
  LF first attempt failed on the wrong port and was retained; corrected retry completed 12/12.
- **System layer:** 37 case dirs = **5 solved / 27 staged / 3 refused / 2 invalid** (the 9 readiness
  cases are 5 solved + 2 staged + 1 refused + the 62864 clearance case). The pilot fidelity/Pareto
  contract is fixed and tested (`pilot --geometry` now works; `score.validate_axes` rejects nested
  axes/list feasibility). Full `tests/system` passes with 7 real-BL env gates.
- **GUI:** Overview is the landing page; P2/P3 views exist (some modules still untracked); P4/P5/P6/P8
  are backend-only; P7/P9 absent. Do not commit another lane's untracked GUI work blindly.
- **Objective versions:** never rank J across versions; v7 = nights' default (R1), v10 = shipped
  second score and OPT-IN ONLY (this night runs it by owner handoff), v10_slope5 = its own identity
  (floor 0.486 J published; diagnostic). Never edit `hornlab_search/objective/scalar_v9.py`.

## Where the rest lives (bounded reads)

| Need | Read |
|---|---|
| Newest status entry | `docs/CONTINUITY.md`, first 60–80 lines only |
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
