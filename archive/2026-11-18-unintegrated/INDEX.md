# ARCHIVE: un-integrated / deletable-candidates (2026-11-18)

Purpose: preserve everything that was at risk of deletion during the `hornfab-all-2026-11-18`
cleanup, BEFORE any removal. Nothing in this folder affects the branch's code: it is provenance.

## 1. Worktree snapshots (5 worktrees; all verified OLDER than this branch by content)

| worktree | branch | unique commits (see unique-commits.txt) | contents |
|---|---|---|---|
| final-v10-319003c | verify/final-v10-319003c | 2 (1 unique: e49b5a5 v10 draft) | patches/, tree-diff-vs-hornfab-all.patch, dirty-test_dataset_manifest.patch (the worktree's uncommitted test edit) |
| v10-319003c | verify/v10-319003c | 2 (1 unique: b7cec5c v10 draft) | likewise; scalar_v10.py differs by 13 lines from the branch's final (PR #68) |
| landing-v10 | feat/objective-v10 | 3 (v10, BO policy, max_edge) | scalar_v10.py is IDENTICAL to the branch's (max_edge already on branch); tree simply behind |
| thv-319003c | verify/thv-319003c | 5 (2 unique: WIP rolled rho/iwata + Klangfilm docstrings) | WIP superseded by the finished c9423c8 / b06a938 on the branch |
| w6-319003c | verify/w6-319003c | none | w6_untracked_agent_bench/: the worktree's UNTRACKED 20-file tests/agent_bench draft (the committed version has 28 files; drafts differ) |

Restore a worktree's commits: `git am <file>.patch` from its patches/ dir (applies cleanly onto
any base with the same content; conflicts resolve with `git am --abort` and the tree-diff patch
as reference). Restore the w6 draft: copy `w6_untracked_agent_bench/` back under `tests/`.

## 2. Night operational record: `night_cd_rrect_2026-11-17/` (runs/nights is not committed by policy)

- `cd_rrect_2026-11-17.yaml` + `.bak`: the live night file WITH the 9 throat jobs inserted,
  and its pre-edit backup.
- `queue_state.json`, `summary.jsonl`: the night's progress ledger incl. all 9 throat jobs'
  rows (exit/J/evals/VRAM).
- `poll_throat.log`: the 15-minute watcher's full log.
- `THROAT_PHASE1_DONE.txt`, `THROAT_PHASE2_DONE.txt`: the completion markers.
- `held_and_edited_2026-11-18.md`, `night_poll_throat.ps1`, `phase1_harvest.py`: the queue
  agent's night-edit notes and the two analysis scripts (scratch/ is gitignored, so these
  copies make the scripts durable).

## 3. What was already removed before this archive (for the record)

- worktree `baseline-319003c`: detached at 319003c (ancestor), empty range, clean.
- worktree `final-thv-319003c`: all 8 commits patch-identical (git cherry, all '-') to
  hornfab-all; clean. Nothing on it exists anywhere else.

The locked worktree `agent-a527a7d28dc77734a` was NEVER touched.
