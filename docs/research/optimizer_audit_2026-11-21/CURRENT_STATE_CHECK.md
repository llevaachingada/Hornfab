# Current-state check for the 2026-11-21 optimizer audit

The audit's §7 requires checking the live tree before treating any item as outstanding. This page
records that check at local HEAD `bdc3f037` on branch `hornfab-all-2026-11-18` (2026-11-21).
Read-only: no run, dataset, queue or GPU lane was touched.

## Commands and bytes

```text
PS> git status --porcelain
(no output: clean worktree)
PS> git branch --show-current
hornfab-all-2026-11-18
PS> git rev-parse --short HEAD
bdc3f037
PS> git rev-list --left-right --count origin/main...HEAD
0       18
PS> git worktree list
C:/Users/hunte/Hrns/hornlab-search                                           bdc3f037 [hornfab-all-2026-11-18]
C:/Users/hunte/Hrns/hornlab-search/.claude/worktrees/hungry-sinousse-4bc609  f20360f2 [claude/hungry-sinousse-4bc609]
C:/Users/hunte/Hrns/hornlab-woofer-system-wt                                 d7453a13 [feat/woofer-system-v0] locked
```

`tools/night_status.py` at the same moment: GPU lock **free**, CPU lock free, and

```text
- lane gpu: lock ...\runs\.gpu.lock free
  - running job room__w90x60_home (night fav8_2026-11-20, since 2026-11-20T23:29:38): ... - 97 rows, newest 1388 min old
  - ALERT lane gpu: newest row is 1388 min old (> 30) while job room__w90x60_home runs; ...
Running now (search processes)
  no hornlab-search search process
```

The alert is a stale ledger entry, not a live solve: the lock is free and no search process exists.
This pass starts no GPU job and modifies no `runs/` directory.

Pinned engine versions in `.venv`:

```text
ribs==0.12.0
cma==4.5.0
numpy==2.5.4
scipy==1.18.1
torch==2.14.1
botorch: NOT INSTALLED
gpytorch: NOT INSTALLED
hornlab_beat_bem==0.2.0
hornlab_bempp_bem==0.2.0
pytest==9.1.1
pytest-xdist==3.8.0
```

`botorch`/`gpytorch` absence means production-study changes must be import-lazy and validated with
monkeypatched unit tests, not a live GP fit.

## Audit items checked against this tree

| Audit item | State at `bdc3f037` | Evidence |
|---|---|---|
| P0a CMA-MAE search/result archives | **Outstanding.** Both archives are built by the same `make_archive()` closure, so MAE soft thresholds apply to `result_archive` too; `archive_payload()` reads the search archive. | `hornlab_search/search/cma_me.py:384-397`, `:528-542` |
| P0b continuation floor identity | **Outstanding.** Floors are keyed only by `(objective_version, "slope5" if "slope5" in brief else "")`; no brief hash, grid, backend or method identity. | `tools/analysis/continuation_advice.py:27-33` |
| P0b typed switch outcomes | **Partially present.** `optimizer_switch` records a single aggregate non-valid fraction plus the shared cost ledger; it does not quantify per-kind refusal/failure counts in the recommendation path. | `tools/analysis/optimizer_switch.py:21-34`, `:67-69` |
| P0c production BO versions | **Outstanding.** Production admission hard-refuses any objective outside `(4, 7)`; the task registry has no v10/v11 task. | `hornlab_search/studies/production.py:143-146`, `hornlab_search/studies/builders.py:123-166` |
| P0c v10 metric helper | **Present, separate.** `freeze_metric_policy_v10` / `measure_metrics_v10` exist with a distinct schema and hash; v4/v7 `freeze_metric_policy` still refuses v10. | `hornlab_search/bo/metrics.py:636-746` |
| P0c v11 metric helper | **Absent.** `objective/scalar_v11.py` is registered and scorable, but `bo/metrics.py` has no v11 policy and `_EXCLUSIVE_OBJECTIVE_LABELS` stops at 10. | `hornlab_search/objective/versions.py:29`, `hornlab_search/bo/metrics.py:644` |
| P1a composed advisory | **Absent.** The individual tools exist; there is no single report that composes them with typed evidence and provenance. | `tools/analysis/` (space_card, parameter_activity, seed_pack, walls, optimizer_switch, continuation_advice, qd_compare) |
| P1b covariance transfer | **Absent.** Warm start imports the best mean and a top-k spread sigma only; full `C` is captured for non-restart CMA with `n_dim <= 16`. | `hornlab_search/search/warmstart.py:110-127`, `hornlab_search/search/cma.py:313-314`, `:1170` |
| P1c benchmark orchestration | **Partial.** `ab_compare.py` already supports predeclared pairs, fixed budget/cost, censoring and paired inference; `study_cohort.py` filters a compatible cohort. No pre-registered matched-arm manifest links arms, identities, information parity and real BEM+wall cost in one place. | `tools/analysis/ab_compare.py`, `tools/analysis/study_cohort.py` |
| P2 QD descriptor study | **Gated.** `qd_compare.py` exists; a second emitter/descriptor study needs real BEM evidence. | audit §6, §7 |
| P2 cost-aware BO pilot | **Gated.** `bo/extensions.py` exists; a pilot needs real solve timing and owner GPU authorization. | audit §6, §7 |

## Scope of this implementation pass

Implemented here: P0a, P0b, P0c, P1a, P1b and the P1c orchestration/compare layer, all offline.
The audit's own gate — "Only after that authorize matched physical experiments" — keeps P2 (QD
descriptor study, cost-aware BO pilot) and any matched real-BEM A/B **unrun**. No J is ranked
across briefs or objective versions.
