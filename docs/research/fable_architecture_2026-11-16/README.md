# Fable architecture evidence dossier (2026-11-16)

This folder holds **both** the v3 handoff source documents and the full 15-file read-only evidence
dossier prepared for a later Fable discovery/decision pass. The dossier was mirrored verbatim from
the local working copy (`scratch/fable_architecture/`); internal references to
`scratch/fable_architecture/…` in those files refer to that working copy, and the file names here
are identical. That working copy is **no longer git-ignored**: the expanded 25-report corpus and its
`.fable/` + `.tmp/` harnesses were committed to `main` in `207f97a` (`__pycache__` excluded). Reach
for it when you need the fuller reports; this folder remains the original 15-file dossier plus the
handoff text as the curated reading set.

## Handoff source documents (v3 package)

The 12 source documents of the v3 handoff package were **moved here** from
`C:\Users\hunte\Downloads\Hornfab_Fable_Architecture_Handoff_2026-11-16_v3\hornfab_fable_handoff\`
on 2026-11-16 so the brief and its evidence live in one tracked folder:

- [`00_START_HERE.md`](00_START_HERE.md) — process and scope; start here for the handoff.
- [`01_CHEAP_AGENT_DISPATCH.md`](01_CHEAP_AGENT_DISPATCH.md) — the investigator assignments used.
- [`02_EVIDENCE_FORMAT.md`](02_EVIDENCE_FORMAT.md) — output contract and acceptance checklist.
- [`03_FABLE_DISCOVERY.md`](03_FABLE_DISCOVERY.md) — first Fable pass (broad discovery).
- [`04_TARGETED_RESEARCH_LOOP.md`](04_TARGETED_RESEARCH_LOOP.md) — optional gap-closure loop.
- [`05_FABLE_FINAL_SPEC.md`](05_FABLE_FINAL_SPEC.md) — second Fable pass (decision + tickets).
- [`06_REPO_FINDINGS_AND_SOURCE_MAP.md`](06_REPO_FINDINGS_AND_SOURCE_MAP.md) — prior review; verify
  against the live tree (several claims were stale).
- [`07_IMPLEMENT_AND_VALIDATE.md`](07_IMPLEMENT_AND_VALIDATE.md) — implementation/integration brief.
- [`08_OPTION_EXPLORATORY_SIZE_AND_FEASIBILITY.md`](08_OPTION_EXPLORATORY_SIZE_AND_FEASIBILITY.md)
- [`09_OPTION_ADAPTIVE_SEARCH_SUPERVISOR.md`](09_OPTION_ADAPTIVE_SEARCH_SUPERVISOR.md)
- [`10_CHEAP_AGENT_SEARCH_SUPERVISOR_PASS.md`](10_CHEAP_AGENT_SEARCH_SUPERVISOR_PASS.md)
- [`11_ACCEPTANCE_AND_EXPERIMENT_PROTOCOL.md`](11_ACCEPTANCE_AND_EXPERIMENT_PROTOCOL.md)

Internal relative references between those documents remain valid inside this folder. Their
"current repo" claims are historical relative to the snapshot bullets below.

- **Snapshot of record:** `main` @ `601be8ceeb48f1750bb4f3f6c1fdc682967c8b94`, observed
  2026-11-16T20:43:51-05:00.
- **Drift check:** the tree later advanced to `0750a30`; `git diff --stat 601be8c..0750a30` over
  every cited path is empty, so the dossier's `path:line` citations remain valid. Re-read the tree
  before acting; this is timestamped evidence, not a permanent API.
- **Handoff context:** the v3 package named `origin/main = 2c0e2928…`. The local checkout is 12
  commits ahead of that commit, so the package's "current" file/line claims were re-checked against
  the local snapshot.
- **Tracked digest:** [`FABLE_DISCOVERY_EVIDENCE_HANDOFF_2026-11-16.md`](../FABLE_DISCOVERY_EVIDENCE_HANDOFF_2026-11-16.md)
  is the short, scannable version committed first (`3ad8b1d`).

## Reading order

0. [`00_START_HERE.md`](00_START_HERE.md) → [`03_FABLE_DISCOVERY.md`](03_FABLE_DISCOVERY.md) for
   the discovery pass, then [`05_FABLE_FINAL_SPEC.md`](05_FABLE_FINAL_SPEC.md) when the evidence is
   sufficient.
1. [`INDEX.md`](INDEX.md) — read first: question, snapshot, top findings, contradictions, six
   unranked routes, v3 supervisor section.
2. [`SOURCE_INDEX.md`](SOURCE_INDEX.md) — paths, SHAs, hashes, run artifacts, method, non-mutation
   statement.
3. [`EVIDENCE_LEDGER.md`](EVIDENCE_LEDGER.md) — 59 atomic status-labelled claims.
4. [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) — 10 architecture-changing questions, cheap tests,
   original-thought questions.
5. Domain reports: [`GEOMETRY_AND_PARAMETER_MAP.md`](GEOMETRY_AND_PARAMETER_MAP.md),
   [`FAILURE_AND_BOUNDARY_AUDIT.md`](FAILURE_AND_BOUNDARY_AUDIT.md),
   [`SIZE_FEASIBILITY_EVIDENCE.md`](SIZE_FEASIBILITY_EVIDENCE.md),
   [`OPTIMIZATION_AND_BRIEF_AUDIT.md`](OPTIMIZATION_AND_BRIEF_AUDIT.md),
   [`OPTIMIZER_AND_SWITCH_SECTION.md`](OPTIMIZER_AND_SWITCH_SECTION.md),
   [`EXTERNAL_EVIDENCE.md`](EXTERNAL_EVIDENCE.md).
6. Search-supervision pass: [`SEARCH_CONTROL_MAP.md`](SEARCH_CONTROL_MAP.md),
   [`WATCHDOG_REPLAY.md`](WATCHDOG_REPLAY.md),
   [`SWITCH_ADMISSION_MATRIX.md`](SWITCH_ADMISSION_MATRIX.md),
   [`SUPERVISOR_OPTIONS.md`](SUPERVISOR_OPTIONS.md),
   [`ADAPTIVE_UNKNOWNS.md`](ADAPTIVE_UNKNOWNS.md).

## How the evidence was produced (and what it does not claim)

- Source was read at the snapshot; two NDJSON aggregations over extant `runs/` artifacts and one
  import of the pure `watchdog_verdict` function were the only executions. Historical report
  numbers are labelled as records, not fresh measurements.
- **No GPU/BEM solve, mesher run, pytest, queue edit, threshold change, process signal, lock or git
  mutation** was performed by the research pass. A concurrent lane's work was observed and
  preserved.
- Read-only parser/replay helpers and intermediate JSON lived in the working copy's
  `scratch/fable_architecture/.tmp/`; they are not mirrored into this folder, but that working copy
  is now tracked on `main` (`207f97a`), so the harnesses and intermediate JSON are reproducible from
  the repo. The procedures and every cited path are also described in the reports.
- Nothing here is an architecture decision or an implementation authorization. The deliverable is
  evidence for a later decision-maker, who may reject any or all of the candidate routes.
