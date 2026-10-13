---
name: Task
about: One plan task, dispatched to one agent
title: "[NN] <task name>"
labels: ""
---

**Plan file:** `docs/plan/<NN_TASK_*.md>`
**Wave:** <0|1|2|3>
**Branch:** `task/<NN>-<slug>`

## Owned files
<!-- Copy from the task file / ownership table. Create and edit ONLY these. -->

## Checkpoint
<!-- CP-N from docs/plan/09_CHECKPOINTS.md and the task file. Paste output in the PR. -->

## Blocked by
<!-- #issue numbers, or "none" -->

## Dispatch prompt
Use the verbatim template in `docs/plan/00_ORCHESTRATOR.md` ("Dispatch prompt template"), with
`<path>` = `docs/plan` and `<repo>` = the repo root.
