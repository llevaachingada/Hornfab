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

- **GPU lane:** live night `cd_rrect_2026-11-17` (backlog job running; B1 batch 1 = 5 fold-warm x2
  probe jobs appended AFTER the backlog, runner `--dry-run` exit 0). Do not start another GPU job.
- **CPU lane:** free (rescore evidence published; see `docs/evidence/v10_rescore_2026-11-18/results/README.md`).
- **Objective versions:** never rank J across versions; v7 = nights' score (R1), v10 = shipped
  second score, v10_slope5 = its own identity (floor 0.486 J published; diagnostic). Never edit
  `hornlab_search/objective/scalar_v9.py`.

## Where the rest lives (bounded reads)

| Need | Read |
|---|---|
| Newest status entry | `docs/CONTINUITY.md`, first 60–80 lines only |
| Open issues / TO-DO | `docs/ISSUES.md`, first 60–80 lines, then search by ID |
| Senior rulings, blockers | `NOTES_FOR_SENIOR.md`, last 60 lines, then search |
| Next-round priorities | `docs/NEXT_DEV_PRIORITIES.md`, current section only |
| Doc map / module map | `docs/INDEX.md` / `docs/CODE_MAP.md` — search, do not read whole |
| Queue mechanics | `tools/night_status.py`, `runs/nights/`, queue logs in `runs/` |

Never load the living logs in full; they are hundreds of KB each. Any document over ~100 KB is
grep-only.

## Maintenance

Update this file in the same commit as any change to the active queue, the objective default, or the
canonical checkout path. Keep it under ~60 lines; if it grows, it has stopped being a pointer.
