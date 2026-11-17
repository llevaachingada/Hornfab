# ACTIVE_STATE — current pointer

**This is a pointer, not authority.** It names where current state lives and what was verified when
it was last written. If it disagrees with the tools below, the tools win.

Last verified: **2026-11-17**, against HEAD of `main` at write time.

## Verify first (never trust this file alone)

```powershell
.venv\Scripts\python.exe tools\night_status.py --since-hours 48
git log --oneline -5; git status --porcelain
```

## Workspace

- Canonical checkout: `C:/Users/hunte/Hrns/hornlab-search` (owner amendment 2026-11-12).
- Start OpenCode here. Umbrella sessions in `Hrns` get the eight `hornlab-*` skills only through
  `Hrns/.opencode/opencode.jsonc` — see `docs/AGENT_BOOTSTRAP_CONTAINER.md`.

## State, at write time

- **GPU lane:** held by night `home18_a_2026-11-16`; running job `r120_rosse_s5678` (night
  `rosse_r120_2026-11-16`). Do not start another GPU job until it clears.
- **CPU lane:** free.
- **BoTorch round 2** (`bo_multityp_r2_2026-11-16`): 7/7 jobs done; readout open.
- **BoTorch vs CMA** (`bo_vs_cma_2026-11-15`): 14/14 done; CMA arms report J 3.23278, BoTorch arms
  report no scored best in the status view — treat the readout, not this line, as the record.
- **v9 objective:** CLOSED, gates G0–G13 green; production default unchanged (opt-in).
- **Objective versions:** never rank J across versions (4, 5, 6, 7 defined in `AGENTS.md`).

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
