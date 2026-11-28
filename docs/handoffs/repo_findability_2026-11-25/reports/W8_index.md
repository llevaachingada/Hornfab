# W8 — Wave-3 index integration

**Workstream:** Wave 3 of `docs/handoffs/REPO_FINDABILITY_HANDOFF_2026-11-25.md` (index part only)
**Date:** 2026-11-25
**Scope:** `docs/history/INDEX_feed_through_2026-11-25.md`, `docs/INDEX.md`,
`docs/START_HERE.md`, this report. No code/config/brief/queue edits, no deletions, no commit/push,
no GPU.

---

## 1. Summary

| File | Action | Size | Lines | Links | Status |
|---|---|---:|---:|---:|---|
| `docs/history/INDEX_feed_through_2026-11-25.md` | Copied **first**, verbatim | 128,491 B | 555 | — | byte-identical |
| `docs/INDEX.md` | Rewritten as a 14-section topic catalog | 22,616 B | 210 | 153 | 0 broken |
| `docs/START_HERE.md` | New task → first-file router | — | 74 | 42 | 0 broken |
| `docs/handoffs/repo_findability_2026-11-25/reports/W8_index.md` | This report | — | — | — | — |

- History copy SHA-256: `9F225971554A7A041A0D09590E08770643A12248093068E0E2182D2F35718241`
  (matches the pre-rewrite `docs/INDEX.md`, verified before the rewrite and re-verified after).
- New `docs/INDEX.md` SHA-256: `9356D260EC0D9560A6FC5B69F249993A4DA8692C8CACA7F284A94759A4E0D77C`.
- `docs/INDEX.md` is CRLF: 210 CRLF, 210 LF, no BOM. The history copy keeps its original
  567 CRLF / 567 LF, no BOM.

---

## 2. History copy (done before anything else)

`Copy-Item` was run as the first mutating action, before reading any other input or writing the new
index. Verification:

```
SRC=9F225971554A7A041A0D09590E08770643A12248093068E0E2182D2F35718241
DST=9F225971554A7A041A0D09590E08770643A12248093068E0E2182D2F35718241
MATCH=yes
```

Post-work re-check:

```
history_sha=9F225971554A7A041A0D09590E08770643A12248093068E0E2182D2F35718241
expected=9F225971554A7A041A0D09590E08770643A12248093068E0E2182D2F35718241
history_bytes=128491
```

Because the copy is byte-identical, its relative targets still resolve as if the file were at
`docs/INDEX.md`; from `docs/history/` they do not. That is the unavoidable price of the explicit
byte-for-byte rule, not a link rewrite failure. See §5.

---

## 3. `docs/INDEX.md` — topic catalog

Fourteen sections, exactly one occurrence each: Start · Acoustic knowledge · Scoring & briefs ·
Families · Search & BO · Nights/GPU · Tools · Evidence by family · Research by topic · Guides ·
Handoffs · GUI · Data/archive · Historical.

Every entry is `link — one line — **STATUS**`; a script check found **0** entries without a status
tag. Descriptions are the linked file's H1 (or first non-empty line when there is no H1); group
headings use the target catalog's own section headings. No description was invented.

**Catalog-first rule.** Tools, evidence, research, nights, scoring and BO link their catalog (or a
catalog section anchor) instead of re-listing rows. Only Guides, Handoffs and Archive are listed per
file, because they have no separate catalog in the target layout.

**Coverage of the required directories** (machine-checked, not eyeballed):

```
sections: all 14 present (count 1 each)
missing: 0
dups: 0
entries without status: 0
```

- `docs/guides/` — 8/8 files, once each.
- `docs/handoffs/` — 8/8 files, once each (including `REPO_FINDABILITY_HANDOFF_2026-11-25.md`).
- `docs/archive/2026-10/` — 23/23 files, once each.
- `docs/archive/2026-11/` — 13/13 files, once each.

Status assignment follows `I1_docs_top.csv`; the full family cards (`rolled`, `klangfilm_lame`,
`sculpted_rosse_crowe`, `cd_backbone`, `rim_beak`, `favl_canonical`) are CURRENT and the short/starter
cards are REFERENCE. The `BRIEF_AND_SCORING_GUIDE_2026-10-25.md` keeps the REFERENCE status W1/W3
gave it; scoring semantics point to `knowledge/SCORING_REFERENCE.md` instead.

Also listed, from concurrent W7 output that appeared during this pass:
`history/AGENTS_historical_2026-11.md` and `history/ACTIVE_STATE_history_2026-11.md`
(refreshed `ACTIVE_STATE` / slimmed AGENTS work by the orchestrator-owned branch).

---

## 4. `docs/START_HERE.md`

74 lines (≤ 80). One task table plus the traps that caused the 2026-11-25 rework:

- scoring/flatness and the **corridor-vs-constancy** trap (corridor charges exactly 0 inside
  `[min,max]`, `preferred_deg` unused; `objective.constancy` is opt-in and does not pull toward
  `preferred_deg`);
- **family laws before bounds** (rolled 10 %/15 %, disjoint non-dormant windows,
  `width_lo > height_hi`, throat-turn < rect-turn, per-mode inert knobs);
- **night watchdog / exit 75** and the **live-night splice**
  (`runs/nights/<night>.yaml`, `--dry-run`);
- **offline re-score** (`replay_run_dir` / `rescore_identity.py`; only `exact_complete` ranks);
- **BO identity = brief + bounds**, snapped starts and the `ActiveProjection` round-trip;
- generator identity (implementation digest, new module + CRLF registration);
- current state (`ACTIVE_STATE.md`, `night_status.py`, no cross-version J ranking).

Required links are present: `INDEX.md`, `TOOLS.md`, `knowledge/README.md`,
`knowledge/SCORING_REFERENCE.md`, `knowledge/FAMILY_LAWS.md`, `knowledge/typologies/`,
`research/README.md`, `evidence/CATALOG.md`, `queue/README.md`.

---

## 5. Link verification

Official checker, run in the repo root with the project interpreter:

```
.venv\Scripts\python.exe docs/handoffs/repo_findability_2026-11-25/check_links.py .
```

| Stage | Output |
|---|---|
| Before the rewrite (history copy already present) | `checked 2693 relative links; broken=434` |
| After the rewrite | `checked 2496 relative links; broken=429` |

Set difference of the two broken-link reports:

```
NEW (after not before): 0
GONE (before not after): 5
  docs/INDEX.md:5:  research/metric_bo_2026-11-22/ADR_metric_composite_v1.md
  docs/INDEX.md:5:  research/metric_bo_2026-11-22/09_IMPLEMENTATION_STATUS.md
  docs/INDEX.md:5:  research/metric_bo_2026-11-22/07_DEFERRED_REAL_DATA_PLAN.md
  docs/INDEX.md:324: HANDOFF.md
  docs/INDEX.md:324: HANDOFF_LOCAL.md
```

**0 new broken links; 5 pre-existing broken links removed** with the old feed. The 429 remainder
are all outside the files I own:

| Bucket | Count | Note |
|---|---:|---|
| `docs/history/` | 406 | 391 are the preserved `INDEX_feed_through_2026-11-25.md` (byte-identical, so targets now resolve from the wrong directory); 15 are rotated living logs (pre-existing W7 rotation, also visible in the before-snapshot). |
| `.claude/worktrees/hungry-sinoussi-4bc609/` | 12 | Provenance worktree; pre-existing, unchanged. |
| main tree, other files | 11 | `NOTES_FOR_SENIOR.md:67`, `docs/archive/2026-10/SOLVE_CAMPAIGN_PLAN...:4`, `docs/handoffs/REPO_FINDABILITY...:110`, I1/I3 reports, 6 `docs/research/**` lines; all pre-existing. |

Targeted check of just the two live files:

```
docs/INDEX.md      links 153  broken 0
docs/START_HERE.md links  42  broken 0
```

**Links I could not resolve:** none in `docs/INDEX.md` or `docs/START_HERE.md`. The only unresolved
targets the checker reports in my output are the 391 in the mandated byte-identical history copy and
the pre-existing buckets above. The W1-noted
`docs/evidence/throat_sculpting_2026-11-25/README.md` was not written here (not my file); the new
Families entry points at the typology card, and no live-index line cites the missing README.

---

## 6. What was left / open questions

- **History-copy links.** The 391 broken entries under
  `docs/history/INDEX_feed_through_2026-11-25.md` are inherent to the byte-for-byte requirement. If
  the owner later wants a browsable archive, a separate relocated-and-rewritten copy would be a new
  decision; the preserved copy must not be edited.
- **Concurrent writers.** `docs/history/AGENTS_historical_2026-11.md` and
  `docs/history/ACTIVE_STATE_history_2026-11.md` appeared during this pass; I linked them in
  Historical without reading them in full.
- **Not touched:** `AGENTS.md`, `CLAUDE.md`, `ACTIVE_STATE.md`, `docs/CONTINUITY.md`,
  `docs/ISSUES.md`, skills, catalogs, code, configs, briefs, queue, evidence. No deletions, no
  commit, no push, no GPU.
