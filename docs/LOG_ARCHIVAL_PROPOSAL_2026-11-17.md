# Proposal — bounded living logs (rotation + manifest)

**Status:** proposal only, 2026-11-17. The owner has not approved it. Until approval, the push rule
in `AGENTS.md` stands unchanged: every pushed commit appends to `docs/CONTINUITY.md` and
`docs/ISSUES.md`.

## Problem

The two living logs have become read-hostile:

| File | Size | Lines | Entries |
|---|---|---|---|
| `docs/CONTINUITY.md` | ~845 KB | 5,930 | ~390 dated entries |
| `docs/ISSUES.md` | ~408 KB | — | — |
| `NOTES_FOR_SENIOR.md` | ~125 KB | — | append-only |

Reading either in full is ~100–210k tokens before any work starts. The 2026-11-17 read-budget
amendment in `AGENTS.md` stops that by reading only the newest entry, but the files keep growing, and
"search the log" gets slower every week.

## Precedent already in the repository

`docs/history/` already holds verbatim rotations:

- `CONTINUITY_2026-10-12_2026-10-22.md` — entries rotated on 2026-10-30.
- `ISSUES_closed.md` — closed issue rows rotated on 2026-10-30.
- `NOTES_FOR_SENIOR_resolved.md` — resolved blocks rotated on 2026-10-30.

So rotation is an established practice here; this proposal only makes it periodic and machine-checkable.

## Proposal

**Cadence:** monthly, or when `CONTINUITY.md` exceeds ~400 KB, whichever comes first.

**What moves:** entries older than the current month, **verbatim**, in date order, into
`docs/history/CONTINUITY_<first>_<last>.md`. Nothing is rewritten, summarised or deleted. The same
for resolved issue rows → `docs/history/ISSUES_closed.md`.

**What stays:** the newest month in the live file, preceded by a stable pointer block:

```markdown
## Archive

Entries before 2026-11-01 are in `docs/history/CONTINUITY_2026-10-12_2026-10-31.md`.
Machine-readable index: `docs/history/manifest.json`.
```

**Manifest:** `docs/history/manifest.json`, regenerated on each rotation and committed in the same
commit:

```json
{
  "version": 1,
  "generated": "2026-12-01",
  "archives": [
    {
      "file": "docs/history/CONTINUITY_2026-10-12_2026-10-31.md",
      "source": "docs/CONTINUITY.md",
      "date_first": "2026-10-12",
      "date_last": "2026-10-31",
      "entries": 214,
      "sha256": "<hash of the archived file>"
    }
  ]
}
```

The manifest is what makes rotation auditable: file, date range, entry count and hash. It is
append-only like the logs.

**Procedure (one commit):**

1. `git mv` is not needed; create the archive file, copy the block verbatim, delete it from the live
   file in the same edit.
2. Put the archive pointer block at the top of the live file.
3. Regenerate `manifest.json` (entry count = `grep -c '^## 20'`).
4. Update `docs/INDEX.md` with the archive line.
5. Commit with `docs(logs): rotate CONTINUITY ...` and the standard CONTINUITY/ISSUES update for the
   rotation commit itself.

**Safety rules:**

- Never edit an archived entry. Corrections go in a new live entry that references the old date.
- Never archive an entry that is still cited by an open issue or a running queue without copying the
  citation into the live file first.
- `NOTES_FOR_SENIOR.md` rotates only resolved blocks, and only with the resolving entry named.
- Keep `docs/plan/**` frozen; rotation never touches it.

## Why not collapse into a generated summary

A generated "current state" digest drifts the moment someone edits a queue. The pointer model keeps a
single authoritative log and a bounded read path (`ACTIVE_STATE` → newest entry → search), which is
what the 2026-11-17 amendment already relies on.

## Cost of not doing it

At the current rate the live files add roughly 10–20 KB per working day. Within a few months a
"first 60–80 lines" read is still cheap, but `grep` over a 1 MB log and a full-context accident become
more likely, and the push rule keeps appending to both.

## Approval

Owner decision. If approved, the first rotation should archive everything before 2026-11-01 and add
the pointer + manifest; if rejected, delete this proposal and keep the current rule.
