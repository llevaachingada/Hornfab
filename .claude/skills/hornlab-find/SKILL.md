---
name: hornlab-find
description: Find an existing hornlab-search tool, command, doc, research answer or evidence result before writing a new tool or repeating research. Use at the start of any task that feels like it should already be solved ("re-score a run", "why is J flat", "what did we measure for X", "is there a tool for Y"), or when unsure where a fact lives. This is the routing order; it is not a research, GPU or evidence-writing skill.
---

# hornlab find (routing)

**Before writing a tool or doing fresh research, search for what already exists.** Search in this order
and stop at the first hit that answers the task. Only when all five are empty is a new tool/experiment
justified — and say so in the plan.

## 1. Task → where to start

`docs/START_HERE.md` — the one-screen task → first-file table. Open it first.

```powershell
Get-Content docs\START_HERE.md
rg -n -i "re-?score|replay|queue|evidence|brief" docs\START_HERE.md
```

## 2. Task → tool/command

`docs/TOOLS.md` — task → exact command, GPU y/n, source link.

```powershell
rg -n -i "re-?score|sensitivity|convergence|cohort|night" docs\TOOLS.md
```

Then confirm the script/doc still exists before quoting it: `Test-Path <path>`.

## 3. Acoustic knowledge and family truth

`docs/knowledge/` — the acoustic hub, family cards, `FAMILY_LAWS.md`, `SCORING_REFERENCE.md`.

```powershell
rg -n -i "constancy|corridor|relief|rolling|throat" docs\knowledge\*.md docs\knowledge\typologies docs\knowledge\claims
Get-Content docs\knowledge\README.md -TotalCount 60
```

## 4. Research by topic

`docs/research/README.md` — topic → current dossier → superseded ones. Use it before opening the ~525
files under `docs/research/`.

```powershell
rg -n -i "rolled|klangfilm|biradial|meh|cover" docs\research\README.md
rg -l -i "<term>" docs\research --glob "*.md"        # only if the README misses
```

## 5. Evidence: what was already measured

`docs/evidence/CATALOG.md` — family/topic → folder + one-line outcome, newest first.

```powershell
rg -n -i "cohort|constancy|pm5|ceiling|negative" docs\evidence\CATALOG.md
Get-ChildItem docs\evidence -Directory | Where-Object Name -match "<topic>"
```

## Fallbacks (not the first stop)

- **Code entry points / modules:** `docs/CODE_MAP.md`; then `rg -n "class |def " <package>\`.
- **Everything-doc feed:** `docs/INDEX.md` (a feed, not a lookup — grep it, do not read it).
- **Current state / open work:** bounded reads only — `docs/ACTIVE_STATE.md`, first 60-80 lines of
  `docs/CONTINUITY.md` then grep, `docs/ISSUES.md` by ID/subject.
- **When was this last touched:** `git log -1 --format=%cs -- <path>`.

## Reporting a gap

If nothing in steps 1-5 answers the task, record that in your report/plan (which five you searched, what
was missing) before building. That record is what makes the next agent's `rg` succeed.
