# GUI verify-view + UX pass: handoff (2026-11-12, 16:00 EST)

You are finishing a multi-branch GUI implementation in `hornlab-search`. Read this whole file first, then
`docs/GUI_VERIFY_VIEW_PLAN_2026-11-12.md` (the plan; work packages WP0–WP10, Appendix B = acceptance checklist).
Repo rules: `CLAUDE.md` (every pushed commit updates `docs/CONTINUITY.md` + `docs/ISSUES.md`; new docs/modules
get lines in `docs/INDEX.md` / `docs/CODE_MAP.md`).

## Machine facts you need

- Python: `C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe` (the worktrees have no venv).
  Run tests from a worktree root with `PYTHONPATH=.` so the worktree's code is imported:
  `PYTHONPATH=. /c/Users/hunte/Hrns/hornlab-search/.venv/Scripts/python.exe -m pytest tests -k gui -q -p no:cacheprovider`
- Real data (READ-ONLY): `C:\Users\hunte\Hrns\hornlab-search\runs` (425 runs). A GPU and a CPU search queue are
  usually running: never run solves, `gpu-clean`, Kill/Stop/Launch/Continue buttons, or POST to `/api/jobs`.
- Review server (port 8799, the owner's own GUI uses 8765 — leave it alone). Config:
  `C:\Users\hunte\Hrns\.claude\launch.json` entry `gui-review`; it currently serves `oc-wt/gui-int`. Equivalent
  command: `PYTHONPATH=<worktree> <python> -c "from pathlib import Path; from hornlab_search.gui.server import serve;
  serve(Path(r'C:/Users/hunte/Hrns/hornlab-search'), 8799, False, runs=Path(r'C:/Users/hunte/Hrns/hornlab-search/runs'))"`
- JS check: `node --check <file>`. JS unit tests run app.js under node with a DOM stub (copy the stub from
  `tests/test_gui_views_l2.py` ~lines 170–188; a thinner stub crashes because app.js routes on import). Pass
  `encoding="utf-8"` to `subprocess.run` (Windows cp1252 mangles × and ✓).
- Shell gotcha: Python heredocs that write JS turned `\b`/`\s` into control chars once. Edit regexes with the
  Edit tool, or check with `grep -c $'\b' app.js` (must be 0).

## Branches / worktrees (all local, NOTHING pushed)

Base: `docs/gui-verify-view-plan` (worktree `oc-wt/T`, = origin, commit a886538).

| Worktree | Branch | State |
|---|---|---|
| `oc-wt/gui-int` | `feat/gui-integration` | **Integration branch.** Contains: WP0+WP1 (`feat/gui-verify-wp0-wp1`), WP2+WP4 slice (`feat/gui-perf-wp2`), plan v2 doc, WP5/WP4/WP2b (`feat/gui-shell`), WP3+WP6 (`feat/gui-verify-ui`, merged in f0d80b6). Full `-k gui` suite green after the last merge. |
| `oc-wt/gui-b` | `feat/gui-charts-history` | **WP9 + WP10, a Sonnet agent was still working when this was written.** Not merged. |
| `oc-wt/gui-wp01`, `gui-wp2`, `gui-a`, `gui-c` | merged branches | Can be removed after the final merge (`git worktree remove`). |
| `oc-wt/T` | `docs/gui-verify-view-plan` | Has uncommitted plan edits identical to the copy committed in gui-int. Discard them there (`git -C oc-wt/T checkout -- docs`) once gui-int is pushed. |

## Step 1 — finish and merge WP9 + WP10 (branch `feat/gui-charts-history`)

1. `git -C oc-wt/gui-b log --oneline -5` and `git -C oc-wt/gui-b status`. If the agent left uncommitted work,
   review the diff and commit it (or finish it) there. Its scope: plan §5 WP9 (C1–C15) and WP10 (H1–H10).
2. In `oc-wt/gui-int`: `git merge feat/gui-charts-history`. Expected conflicts:
   - `app.css` (each branch appended a block at the end): keep all blocks.
   - `app.js` `viewRunDetail`: gui-b rewrote the acoustic-chart block and the "How the search went" block; gui-int
     moved `${gateAuditHtml(...)}` to just above `<!-- Search history -->` and added
     `<div id="verify-card">` under `#kpi-strip` plus a fetch after the KPI strip render. Keep BOTH sides.
   - `docs/CONTINUITY.md` / `docs/ISSUES.md` (agents may have edited): keep both entries, newest first.
   - `data.py`: gui-b adds `cma_dynamics` + one `run_detail` key; gui-int changed `elites_catalog`, `typologies`
     helpers, `list_runs`, `leaders`, `status` (queue log mtime), `list_configs` (disk cache). Should auto-merge.
3. Run the full GUI suite (must be green) and `node --check` on app.js, charts.js, verify.js, balloon.js, evolution.js.
4. If WP9/WP10 is incomplete, finish the missing C#/H# items per the plan (they are written as step lists).

## Step 2 — fix the known defects found in live review (all small)

1. **Verify table gate chips are colour-only** (`verify.js`, table Gates column): pills show the gate name in
   green/red with no word. Add "pass"/"fail" text or ✓/✗ like the panel checklist does (plan rule 5).
2. **Verify view header** shows the run id as the title and `–` for brief/band: use `report.name` (present in
   `/api/verify`) and the band (`report.band_hz`); if the brief name is needed, add `brief` to `verify_report`
   (data_verify.py) from the run's config.
3. **Cut charts in the verify panel use −50/0/50° ticks**: use 30° multiples (±90, ±60, ±30, 0) per WP9 C4.
4. **`fidelity.screen.dof_range` equals the verify range** on run `…ed1da9` ([2006, 2380] for both). Check in
   `data_verify.py` whether the screen range is computed from verify rows by mistake (screen row dof for
   608eef is 2203 = same mesh, so it may be legitimate; confirm by comparing all 5 screen rows' `n_dof`).
5. **Search-history panels on verify runs** (WP4 item 5 — not done): for `mode:"verify"` runs hide Change vs start,
   Budget used, Evolution/Design cloud/QD links, Continue run, Convergence, Score breakdown, CMA panels, Pin plan.
   Do this AFTER merging gui-b because gui-b owns those blocks. The run-page Verification card already says
   "search-history panels below do not apply".
6. **WP7 not started**: "Verify selected" (plan §5 WP7). First check whether `hornlab-search verify` already has
   `--designs`; if not, add it in `cli.py` with a test, then `jobs.py` validation, then a disabled-while-GPU-busy
   button via `renderVerifySelected` at the end of verify.js.

## Step 3 — acceptance (plan Appendix B, items 1–16) in the built-in browser

Use port 8799 against the real runs. Pages/runs to use: Home; Runs (Mode filter = Verify should list 16 rows,
7 with a parent link); run `20261027T051600Z-screen-ed1da9` (Verification card: 5 verified, +19.1% screen bias;
Verify view; select a design → balloon/cuts/polar/isobar/curves move with the frequency slider);
`20261029T013620Z-verify-3f4992` (standalone verify); `20261023T195300Z-verify-bdae12` (linked → parent
`20261023T025720Z-screen-2002c3`, which is "not comparable": different bands); `20261023T195001Z-verify-0f395c`
(parent missing); Elites (< 6 s); Launch (form visible; the first visit after a server start is about 40 s
unless the disk cache is warm); Compare (filter box). Check dark + light theme and a 900 px width. Write
results to `docs/GUI_VERIFY_ACCEPTANCE_2026-11-12.md` (pass/fail per item), and add it to `docs/INDEX.md`.

## Step 4 — ship

1. Update `docs/CONTINUITY.md` (new dated entry at top + status block) and `docs/ISSUES.md` in the same commit.
2. Add a "Status" section to the top of the plan doc listing what is done.
3. Ask the owner before pushing. Then push `feat/gui-integration` and open a PR to `main`. The PR body lists
   measured numbers below and the acceptance file. End it with
   `🤖 Generated with [Claude Code](https://claude.com/claude-code)`; commits end with
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## What is already done and measured (for the PR and CONTINUITY entry)

- **Verify backend (WP0/WP1):** `hornlab_search/gui/data_verify.py`; `/api/verify/<run>`,
  `/api/design/<run>/<hash>?tier=`, `?tier=verify` on balloon/mesh. Handles three verify layouts (inline
  `<run>/verify/`, linked `verify_of`, standalone `search --mode verify`), missing parents, latest-n dedupe,
  cross-band "not comparable" (ranks/bias nulled), gates merged from audits. Under 200 ms per report on real
  runs. Orchestrator review fixed two agent bugs (gates never filled; ranks reported when not comparable).
- **Speed (WP2/WP2b):** Elites 60–109 s → 3.5 s cold / 2 ms cached; Typologies warm 16–29 s → 0.9 s (cold
  177 → 38 s); `/api/configs` in a fresh process 29 s → 0.2 s through a per-user disk cache
  (`%LOCALAPPDATA%\hornlab-search\gui_seed_gate_cache.json`, keyed on file stamps + design/mesh code fingerprint;
  `HORNLAB_GUI_NO_DISK_CACHE=1` disables; never written during pytest unless a test opts in). Launch no longer
  waits for Typologies.
- **Run page (WP4):** "Best/Start screen score" labels; resumed runs read "N evals total · this resume +B";
  gate audit folds to the top 10 + verified rows and sits below the charts; Verification card / next step
  from `/api/verify` (five real states checked).
- **Shell (WP5):** nav grouped Results / Start work / System; sidebar lane lines for GPU and CPU; "Kill GPU run"
  label; Runs list Mode filter, verify/verified/running badges, parent links, default sort "Last activity" with
  live runs pinned; Compare search + same-brief filter; Home leaders show "verified designs / not verified yet"
  and only briefs active in 14 days (15 of 56 on the real tree; "Show all briefs"); Status picks today's queue
  log by mtime (it was alphabetical); Compose marked recommended, Launch for experienced users; Analysis empty
  state shows the `report_day.py` command.
- **Verify UI (WP3/WP6, agent):** `verify.js` table, KPIs, scatter, states, per-design panel (3D balloon, H/V cuts,
  circular polar, isobar map, curves with screen ghost, frequency slider with aria text, Ready-to-print checklist),
  compare-two route. Live-checked on `…ed1da9`.

## Open questions for the owner (do not decide alone)

- Is a 14-day window right for Home's "Best horn per brief"?
- Push as one PR, or split (verify view vs UX/perf)?
