# ACTIVE_STATE — current pointer

**This is a pointer, not authority.** It names where current state lives and what was verified when
it was last written. If it disagrees with the tools below, the tools win.

Last checked **2026-11-25** in the canonical checkout, branch `hornfab-all-2026-11-18` with local
changes. Older dated state moved to [`docs/history/ACTIVE_STATE_history_2026-11.md`](history/ACTIVE_STATE_history_2026-11.md).

## Verify first (never trust this file alone)

```powershell
.venv\Scripts\python.exe tools/night_status.py --since-hours 48
git log --oneline -5; git status --porcelain
```

## Workspace

- Canonical checkout: `C:/Users/hunte/Hrns/hornlab-search` (owner amendment 2026-11-12).
- Start OpenCode here. Umbrella sessions in `Hrns` get the `hornlab-*` skills through
  `Hrns/.opencode/opencode.jsonc` — see `docs/guides/AGENT_BOOTSTRAP_CONTAINER.md`.
- Current routing: `AGENTS.md`, `docs/START_HERE.md`, `docs/INDEX.md`.

## State at write time

- **GPU lane:** check `tools/night_status.py`. The `cd_bo_cohort_2026-11-25` night was live at
  2026-11-25 18:00; the favL 2-inch compact500 continuation best is 1.691470 (run
  `runs/20261125T204727Z-screen-02b4bf`). Evidence:
  [`docs/evidence/favL_2in_c500_continue_2026-11-25/`](evidence/favL_2in_c500_continue_2026-11-25/).
- **Metric-aware BO:** the Home v11 Fold loop is proven end-to-end; the adaptive 20-screen tranche
  and four native/900 Hz canaries are staged and HELD pending owner GPU authorization. Admission
  table: `docs/research/metric_bo_2026-11-22/12_HANDOFF_2026-11-24.md`.
- **Research snapshot (2026-11-27):** read-only, sourced research view — GUI Overview > Briefing >
  "Generate research snapshot" or `python -m hornlab_search.research build`; handback
  `docs/research/research_view_2026-11-27/README.md`.
- **Recent evidence:** CD wall-angle backbone best rolled bb_h 0.50, J 8.121 → 5.407
  ([readout](evidence/cd_backbone_2026-11-25/README.md)); directivity attribution readout
  ([2026-11-24](evidence/directivity_attribution_2026-11-24/README.md)).
- **Objective versions:** never rank J across versions; v7 is the nights' default, v10 is opt-in,
  v11 is the current CD identity (`hornlab_search/objective/versions.py`).

## Where the rest lives (bounded reads)

| Need | Read |
|---|---|
| Task → first file | `docs/START_HERE.md` |
| Topic catalog | `docs/INDEX.md` (search it) |
| Tool for a task | `docs/TOOLS.md` |
| Scoring / constancy | `docs/knowledge/SCORING_REFERENCE.md` |
| Family laws | `docs/knowledge/FAMILY_LAWS.md` |
| Evidence outcomes | `docs/evidence/CATALOG.md` |
| Research by topic | `docs/research/README.md` |
| Live vs committed nights | `docs/queue/README.md` |
| Newest status | `docs/CONTINUITY.md`, first 60–80 lines |
| Open issues / TO-DO | `docs/ISSUES.md`, first 60–80 lines, then search by ID |
| Senior rulings, blockers | `NOTES_FOR_SENIOR.md`, last 60 lines |
| Next-round priorities | `docs/NEXT_DEV_PRIORITIES.md`, current section only |
| Module map | `docs/CODE_MAP.md` (search it) |

Never load the living logs in full; they are hundreds of KB each. Any document over ~100 KB is
grep-only.

## Maintenance

Update this file in the same commit as any change to the active queue, the objective default, or the
canonical checkout path. Keep it under ~60 lines; if it grows, it has stopped being a pointer.
