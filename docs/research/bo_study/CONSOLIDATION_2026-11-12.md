# Local consolidation into `main` (2026-11-12)

Status: **complete for reviewed/current work**, local only, not pushed. Owner-requested consolidation
before M1/M2/M3 resume. Live checkout and all solver/queue data preserved.

## Result

| Item | Value |
|---|---|
| Consolidated main | `7997259` (`merge(analysis): S3 cost/replicate accounting (M0)`) |
| Live checkout | `C:\Users\hunte\Hrns\hornlab-search` — branch **`main`**, clean; `cache_cpu/`, `dataset_cpu/` untracked and untouched |
| Relative to `origin/main` | 0 behind, 40 ahead (includes 3 second-parent commits from two ancestry-record merges) |
| Consolidated worktree | `C:\Users\hunte\Hrns\consolidation-backup-20261112-173934\integration` (branch `consolidation/local-main-2026-11-12`) |
| Prior local main | `3e4e690`; still preserved by `backup/pre-consolidation-main`; new main is a strict descendant |

## What was merged (in order)

1. Prior consolidation chain already in progress: `a825f8a`, `a7828fd`, `6d552c7`, `1e2256a` —
   `feat/gui-integration` working files (`25dfde6`), live queue `79edc8d`, plan `90b9a49`,
   DOCS working snapshot `426bd17`.
2. T's dirty v2 GUI plan + INDEX resolution + the worker checkout-policy edits in the prompt pack
   (`fc8d9cc`).
3. `origin/main` `d5c0b20` (#49 refusal research) — INDEX conflict resolved keeping the newer
   superseding rows plus the REFUSALS row (`5aa6d4a`).
4. `lane/L4-hygiene` — `.gitattributes`, EOL renormalise (3 files), priorities/history rotation
   (`58af775`); NOTES conflict resolved by keeping the current NOTES and the rotated history file.
5. `feat/gui-integration` `6534a69` (second visual-audit round, scroll hints, verify query routing)
   (`2ab94cf`); CONTINUITY kept current, acceptance doc took the newer second-round version.
6. `docs/refusals-handoff-2026-11-12` and `integ/2026-11-12` recorded with `-s ours` ancestry
   merges because their document content is byte-identical to what is already in main
   (`b1ba915`, `a01a182`).
7. S3 M0 cost/replicate accounting (`task/bo-m0-cost` `dabb5d1`) — attempt-inclusive cost
   ledgers, software/compatibility gating, replicate identity, paired bootstrap CIs, censoring
   ECDF/ERT, fixed-budget/cost views, power planning, `>=30` timing gate (reporting only), and
   20 new focused tests (`7997259`). Data/fixtures only; no model fitted, no live writes.

No deletions relative to `origin/main` (`git diff --name-status origin/main..main` has no `D` rows);
delta is 57 files, +12,349/−1,672, dominated by GUI verify/live-status features and the research docs.

## Verification run on the consolidated tree

- `python -m compileall -q hornlab_search tools` → exit 0.
- `node --check` on `app.js`, `verify.js`, `charts.js`, `balloon.js`, `evolution.js`,
  `glossary.js`, `umap.js` → all exit 0.
- `pytest tests/test_gui_views_l2.py test_gui_verify_contract.py test_gui_verify_data.py
  test_gui_verify_panel.py test_gui_verify_table.py test_gui_visual_audit_fixes.py test_config.py -q`
  → exit 0, 143 passed.
- `pytest tests/test_gui_shell_ux.py test_gui_run_identity.py test_gui_jobs_verify_designs.py
  test_tools_analysis_common.py test_tools_analysis_seed_variance.py test_tools_analysis_ab_compare.py
  test_dataset_record.py -q` → exit 0, 103 passed.
- `git diff --check` → clean.
- Import from the live tree resolves `C:\Users\hunte\Hrns\hornlab-search\hornlab_search\__init__.py`.
- After the S3 merge on live `main`: `pytest tests/test_tools_analysis_s3_cost.py
  test_tools_analysis_seed_variance.py test_tools_analysis_ab_compare.py
  test_tools_analysis_common.py -q` → exit 0, 51 passed; `compileall tools/analysis` → exit 0.
  S3's own claim was also independently rerun in its worktree before the commit.

## Deliberately not merged (preserved, not lost)

| Branch | Reason |
|---|---|
| `beta-fixes` | One Oct-30 docs commit editing frozen `docs/plan/12_RESEARCH_BASIS.md`; historical, not current work. |
| `dev/fused-cuda-pin` | Commit message says "DEV BRANCH ONLY - never main"; it pins a file:// fork and changes `pyproject.toml`/`TOOLCHAIN.md`. |
| `swarm/F-2026-10-31`, `swarm/H-2026-10-31` | `2026-11-12` rescue commits explicitly marked "not reviewed, not tested"; content assigned to L1/L5 by the integ handoff. |
| `backup/consolidation/*` | Preservation backups of every pre-consolidation branch/worktree. |
| `feat/gui-*`, `day/*`, `G2`, `V`, `A`, `fix/*`, `L1/L2/L3/L5` | Already ancestors of main (merged). |
| `gui-int` in-progress merge | Preserved to `bo-study/preserve/gui-int-20261112/` (status, combined diff, conflicted files); code is already in `25dfde6`/`6534a69`. Worktree left untouched. |
| Live `cache_cpu/`, `dataset_cpu/` | Untracked runtime data; not committed, not modified. |

## Risks / notes for the owner

1. **The live checkout was switched to `main` at 17:55:35 by a concurrent process**, then
   `git reset` at 17:56:05 cleared the carried GUI merge state. The GPU night queue
   (`run_campaign_night`, 3 processes) was already running and remains alive with no stderr errors.
   Jobs spawned after the switch run main's search code, which is **not identical** to the day
   branch: `config.py`, `search/cma*.py`, `evaluate.py`, `links.py`, `pin_from_cma.py`,
   `warmstart.py`, `scalar_v8.py` (defaults/registration unchanged; the B features are opt-in).
   The current job is meshing normally. No solve/queue files were touched by this consolidation.
2. `morph_fixed` resolved bound is 0–0.6 despite the campaign comment saying 0–0.1 — carried into
   the M0 control ledger; no bound was changed.
3. The three M0 lanes were dispatched before the owner's one-checkout amendment. **DATA and B2
   stopped without producing any file changes** (their worktrees are clean); they must be
   re-dispatched against canonical `main` if those slices are still wanted. **S3 completed and is
   merged** (`dabb5d1` / `7997259`). Do not create more worktrees.
