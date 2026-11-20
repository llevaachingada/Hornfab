# ACTIVE_STATE — current pointer

**This is a pointer, not authority.** It names where current state lives and what was verified when
it was last written. If it disagrees with the tools below, the tools win.

Last verified: **2026-11-18 evening**, after the Fable integration merges (PR #69, #67, #70).

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

- **GPU lane:** LIVE — `compact400_next10_2026-11-19` (the compact-slate lane; do not start anything).
  Its s2w lanes measured: fold **1.3738** (first v10 design below the published 1.4214, tie by floor),
  ext 1.5710 at 10 valid (inconclusive); morph 1.4243, twinray 1.4568 — three constructions inside one
  floor of the leader. The p11_s2w night was stopped at launch with zero GPU spent (full duplicate of
  their s2w lanes); its two configs remain in-tree as a fallback (narrower ext widen + relaxed
  refusal stop). Evidence: `docs/evidence/Q3_MORE_SOLVES_2026-11-19.md` addendum.
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
| Solve-data exports | `docs/top_designs/` (horn GPU) + `docs/system_data/` (system cases/screens) |
| Queue mechanics | `tools/night_status.py`, `runs/nights/`, queue logs in `runs/` |

Never load the living logs in full; they are hundreds of KB each. Any document over ~100 KB is
grep-only.

## Maintenance

Update this file in the same commit as any change to the active queue, the objective default, or the
canonical checkout path. Keep it under ~60 lines; if it grows, it has stopped being a pointer.
