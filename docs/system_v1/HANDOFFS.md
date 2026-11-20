# System v1 handoffs (self-contained, paste one per session)

Each block below is complete on its own: repo, branches, files, rules, steps, and what "done" means.
Paste the whole block into a fresh session. The pass docs (`PASS_*.md`) hold the lane detail the
block points to.

## Locations used by every handoff

| What | Where |
|---|---|
| Repo | `llevaachingada/Hornfab` (GitHub) |
| Local canonical checkout | `C:/Users/hunte/Hrns/hornlab-search` (Windows; the only local checkout, no new worktrees) |
| Integration branch (PR base) | `hornfab-all-2026-11-18` |
| Plan branch (until PR #76 merges) | `claude/gracious-einstein-fwf5uq`; PR https://github.com/llevaachingada/Hornfab/pull/76 |
| Plan folder | `docs/system_v1/` (`README.md`, `01_CONTRACTS.md`, `PASS_0_LOCAL.md`, `PASS_A_CLOUD.md`, `PASS_B_CLOUD.md`, `PASS_C_GUI.md`, `PASS_D_LOCAL_MEASURE.md`, `PASS_E_GATED.md`) |
| Lane reports | `docs/system_v1/lane_reports/<PASS>-<LANE>.md` |
| Source handbook | `docs/HORN_WOOFER_SYSTEM_HANDBOOK_2026-11-19.md` (read only the sections a pass cites) |
| System code | `hornlab_search/system/` and `hornlab_search/system/boundarylab/` |
| System tests | `tests/system/` (fixtures: `tests/system/fixtures/`) |
| GUI code | `hornlab_search/gui/` (`server.py`, `data_hw*.py`, `static/app.js`, `static/hw*.js`) |
| Export tool + data | `tools/data/system_cases.py`, `tests/test_tools_data_system_cases.py`, `docs/system_data/` |
| Readiness registry (fidelity declarations, owner decisions) | `docs/research/system_woofer_2026-11-18/readiness.yaml` |
| System evidence + reviews | `docs/research/system_woofer_2026-11-18/` |
| Shared logs (integrator only) | `docs/CONTINUITY.md`, `docs/ISSUES.md`, `docs/INDEX.md`, `docs/CODE_MAP.md` |
| Local-only stores (never in git, never in cloud) | `system_runs/`, `runs/`, `dataset/` |

## Rules every session follows

1. **Precedence:** `AGENTS.md` > `CLAUDE.md` > `CONTRIBUTING.md` > `docs/system_v1/*`. Read the
   `CLAUDE.md` sections "RULE FOR EVERY PUSH", "File ownership" and "three silent killers".
2. **Push rule:** every pushed commit updates `docs/CONTINUITY.md` (new dated entry at top) and
   `docs/ISSUES.md` in the same commit. Files are UTF-8 with BOM and CRLF; keep that.
3. **Ownership:** edit only the paths your lane owns (listed in the pass doc). Need another file
   changed? Write the exact change in your lane report. Never edit `docs/plan/**`,
   `hornlab_search/system/contracts.py`, `hornlab_search/objective/scalar_v9.py`, or `.venv`.
4. **Git:** only the pass integrator commits/pushes. Lanes never commit. Never force-push, never
   rewrite another branch, never push to `main` or directly to `hornfab-all-*`; open a **draft PR into
   `hornfab-all-2026-11-18`**. Leave other lanes' uncommitted files unstaged. No model names in
   commits or PR text.
5. **Contracts:** implement `docs/system_v1/01_CONTRACTS.md` exactly. If it does not fit the code,
   stop and report; do not improvise.
6. **Physics rules:** never sum horn and woofer channels without a `CalibrationRecord`; fidelity is
   declared in `readiness.yaml`, never inferred; no system score; no ranking against horn J; no new
   solver, mesher or gmsh writer; no acoustics computed in JS.
7. **Compute:** no GPU anywhere in this effort. Boundary Lab and `system_runs/` are local only. One BL
   CPU job at a time, holding `runs\.cpu.lane.lock`. Never `taskkill /IM julia.exe`.
8. **Interpreter:** local `.venv\Scripts\python.exe`; cloud `python3`. Tests offline only in cloud.
9. **Evidence:** quote real terminal counters; label claims `[measured]` / `[inferred]`; never round
   or summarize a test result.
10. **Stop and ask** instead of guessing when: a test outside your lane breaks, a contract misfits, or
    a step needs BL, GPU, `system_runs/` or an owner decision you do not have.

---

## Handoff: Pass 0 (local, your machine)

```
ROLE: Local orchestrator, HornFab System v1 Pass 0. Single lane, serial. No GPU, no BL solve.
REPO: llevaachingada/Hornfab, checkout C:/Users/hunte/Hrns/hornlab-search (only checkout; no worktrees).
BRANCHES: git fetch origin hornfab-all-2026-11-18 claude/gracious-einstein-fwf5uq. Plan docs are on
  claude/gracious-einstein-fwf5uq (PR #76) until merged: read them with
  git show origin/claude/gracious-einstein-fwf5uq:docs/system_v1/<file>.
  Work on a new branch local/system-v1-pass0 cut from hornfab-all-2026-11-18.
READ FIRST: docs/system_v1/HANDOFFS.md (Locations + Rules), docs/system_v1/README.md sections 1-6,
  docs/system_v1/PASS_0_LOCAL.md, AGENTS.md "Precedence", CLAUDE.md "RULE FOR EVERY PUSH".
DO, in order (details in PASS_0_LOCAL.md):
  0.1 Commit the untracked GUI trio hornlab_search/gui/static/hw3d.js, hornlab_search/gui/static/hw_screen.js,
      hornlab_search/gui/data_hw_stage.py plus the hw.js/app.js edits that import them and their tests.
      Run tests/system/test_gui_hw*.py and tests/test_gui*.py; paste counters. Known red baseline:
      tests/test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_or_process_kill_paths.
      Do NOT stage the budget-driver audit, examples/score_identities.yaml, or scratch files.
  0.2 Browser checklist (handbook Appendix C) for #/hw/* at 1280/1009/768/375; record a pass/fail table.
  0.3 If tools/system/capture_fixture_cases.py exists (Pass A lane A6), run
      .venv\Scripts\python.exe tools\system\capture_fixture_cases.py --store system_runs --out tests\system\fixtures\case_store --per-kind 2
      review the bytes, commit. Otherwise mark deferred.
  0.4 Regenerate .venv\Scripts\python.exe tools\data\system_cases.py --root . --out docs\system_data --pretty
  0.5 Fix doc drift in docs/ACTIVE_STATE.md (system GUI, gates B/C, pointer to docs/system_v1/) and
      docs/CODE_MAP.md rows naming files that do not exist (hw_compare.js).
  0.6 Ask the owner to confirm the record SHAPES in docs/system_v1/01_CONTRACTS.md sections 3, 4, 5.
      Record answers in the decisions block of docs/research/system_woofer_2026-11-18/readiness.yaml.
  0.7 One commit with CONTINUITY + ISSUES entries; push local/system-v1-pass0; draft PR into
      hornfab-all-2026-11-18.
RULES: all ten rules in docs/system_v1/HANDOFFS.md.
DONE WHEN: no untracked hw*.js / data_hw*.py; GUI boots from a clean clone; checklist table recorded;
  owner shape answers recorded; PR open.
REPORT: commit sha, PR link, test counters, checklist table, owner answers, deferrals.
```

## Handoff: Pass A (cloud, 6 parallel lanes)

```
ROLE: Integrator, HornFab System v1 Pass A (cloud, offline). You launch 6 lanes as parallel subagents.
REPO: llevaachingada/Hornfab. BRANCH: create claude/system-v1-pass-a from origin/hornfab-all-2026-11-18,
  then git merge origin/claude/gracious-einstein-fwf5uq if PR #76 is not merged yet (it holds docs/system_v1/).
READ FIRST: docs/system_v1/HANDOFFS.md, docs/system_v1/README.md, docs/system_v1/01_CONTRACTS.md,
  docs/system_v1/PASS_A_CLOUD.md.
BASELINE: python3 -m pytest -q tests/system tests/test_tools_data_system_cases.py ; record counters.
  Expected known failure: test_metadata_is_extracted_by_key_not_position (finding N1).
LANES (owned files listed in PASS_A_CLOUD.md):
  A1 hornlab_search/system/{paths,case_schema,read_case}.py + tests/system/test_{paths,case_schema,read_case}.py
  A2 hornlab_search/system/calibration.py + calibration= param in hornlab_search/system/combine.py + tests/system/test_calibration.py
  A3 hornlab_search/system/{authorization,observation}.py + reference.py (auth param, B24, B25) + tests
  A4 fixes B18/B19/B21/B22/B23/B26 in optimize.py, score.py, dsp.py, boundarylab/stage.py, woofer_seed.py + tests
  A5 hornlab_search/system/jobs.py + tools/evidence/verify_evidence_quotes.py + tests
  A6 tools/system/capture_fixture_cases.py + tests/test_tools_capture_fixture_cases.py
  Give each lane the "Paste-ready lane brief" at the bottom of PASS_A_CLOUD.md with LANE filled in,
  plus: "Rules: docs/system_v1/HANDOFFS.md section 'Rules every session follows'."
  No lane touches hornlab_search/gui/** or hornlab_search/system/contracts.py.
INTEGRATE: read every docs/system_v1/lane_reports/A-*.md; resolve cross-lane requests; rerun baseline
  command; nothing may get worse. One commit: code + tests + lane reports + docs/CONTINUITY.md,
  docs/ISSUES.md, docs/INDEX.md, docs/CODE_MAP.md rows for every new module/tool.
  Push claude/system-v1-pass-a; draft PR into hornfab-all-2026-11-18 using .github/pull_request_template.md.
RULES: all ten rules in docs/system_v1/HANDOFFS.md.
DONE WHEN: six lane reports, regression no worse than baseline, PR open.
REPORT: PR link, before/after counters, lanes done/not done, deferrals.
```

## Handoff: Pass B (cloud, 5 parallel lanes; after Pass A merges)

```
ROLE: Integrator, HornFab System v1 Pass B (cloud, offline).
REPO: llevaachingada/Hornfab. BRANCH: claude/system-v1-pass-b from origin/hornfab-all-2026-11-18
  (must already contain Pass A: check hornlab_search/system/read_case.py exists; if not, stop).
READ FIRST: docs/system_v1/HANDOFFS.md, README.md, 01_CONTRACTS.md (sections 6-8), PASS_B_CLOUD.md.
PRECHECK: hornlab_search/gui/data_hw_stage.py and hornlab_search/gui/static/hw_screen.js tracked in git?
  If not, Pass 0 has not landed: skip lane B2 and say so. Fixture pack at tests/system/fixtures/case_store/?
  If yes, every lane adds one test on it.
BASELINE: python3 -m pytest -q tests/system tests/test_tools_data_system_cases.py tests/test_gui*.py
LANES:
  B1 tools/data/system_cases.py delegates to read_case (53 columns unchanged) + tests/test_tools_data_system_cases.py + docs/system_data/README.md
  B2 hornlab_search/gui/data_hw.py, data_hw_compare.py, data_hw_screen.py, data_hw_new.py, data_hw_stage.py on CaseReadModel; F19 meshio guard; F20 preview via jobs.preview
  B3 hornlab_search/system/funnel.py + funnel subcommand in hornlab_search/system/cli.py + tests/system/test_funnel.py
  B4 hornlab_search/system/store_migrate.py + migrate-store subcommand in cli.py + tests/system/test_store_migrate.py (never --apply on a real store)
  B5 hornlab_search/gui/data_hw_dsp.py + one route in hornlab_search/gui/server.py + tests/system/test_gui_hw_dsp.py
  Use the paste-ready lane brief at the bottom of PASS_B_CLOUD.md, plus the HANDOFFS.md rules line.
INTEGRATE: merge the B3/B4 cli.py blocks yourself; run python3 -m hornlab_search.system.cli --help;
  rerun baseline; one commit with shared docs; push; draft PR into hornfab-all-2026-11-18.
  Do NOT regenerate docs/system_data/*.csv|json in cloud (no store). Tell the owner to regenerate locally.
RULES: all ten rules in docs/system_v1/HANDOFFS.md.
DONE WHEN: lane reports present, regression no worse, PR open.
REPORT: PR link, counters, skipped lanes and why.
```

## Handoff: Pass C (GUI; after Pass 0, B2, B5)

```
ROLE: Integrator, HornFab System v1 Pass C (GUI). Cloud is fine (Chromium + Playwright installed).
REPO: llevaachingada/Hornfab. BRANCH: claude/system-v1-pass-c from origin/hornfab-all-2026-11-18
  (must contain Pass 0 GUI trio, hornlab_search/gui/data_hw_dsp.py, and the B2 read models; else stop).
READ FIRST: docs/system_v1/HANDOFFS.md, README.md, 01_CONTRACTS.md section 8, PASS_C_GUI.md.
RUN GUI ON FIXTURES: python3 -c "from hornlab_search.gui.server import main; main(['--system-store','tests/system/fixtures/case_store','--no-browser'])"
ORDER: lane C0 alone first (owns hornlab_search/gui/static/app.js routes/nav, static/glossary.js,
  gui/server.py route table, hornlab_search/cli.py gui --system-store pass-through,
  tests/system/gui_hw_lifecycle.mjs; splits static/hw.js into hw_cases.js, hw_case.js, hw_readiness.js
  with no behaviour change). Then in parallel, each in hornlab_search/gui/static/:
  C1 hw_overview.js  C2 hw_new.js  C3 hw_screen.js  C4 hw_cases.js + hw_case.js
  C5 hw_compare.js   C6 hw_crossover.js + hw_actions.js (Solve stays disabled: "AUTH_REQUIRED (decision 6)")
  Issue IDs each lane closes are in the PASS_C_GUI.md table (F1-F22 from handbook section 8.2).
  Use the paste-ready lane brief at the bottom of PASS_C_GUI.md, plus the HANDOFFS.md rules line.
GUI RULES: no acoustics or status logic in JS; every view exports mount(el, params) and dispose();
  reuse charts.js / view3d.js / glossary.js and existing CSS tokens; no new dependency or build step;
  eyebrow + <h2> headings; disabled controls show a visible reason.
ACCEPT: lifecycle harness green on every route; checklist at 1280/1009/768/375 (console clean, no
  horizontal scroll, charts sized, keyboard reachable, reload-safe); tests/system/test_gui_hw*.py and
  tests/test_gui*.py no worse. Screenshots at 1x to the scratch dir, paths in lane reports.
INTEGRATE: one commit with shared docs; push; draft PR into hornfab-all-2026-11-18. Ask the owner to
  repeat the checklist on the real store locally.
RULES: all ten rules in docs/system_v1/HANDOFFS.md.
REPORT: PR link, checklist table, counters, deferrals.
```

## Handoff: Pass D (local, your machine; after Pass 0, A, B3)

```
ROLE: Local operator, HornFab System v1 Pass D. Boundary Lab beat_cpu only. NO GPU.
REPO: C:/Users/hunte/Hrns/hornlab-search. BRANCH: local/system-v1-pass-d from hornfab-all-2026-11-18
  (must contain hornlab_search/system/funnel.py and authorization.py; else stop).
READ FIRST: docs/system_v1/HANDOFFS.md, README.md sections 1, 3, 6, PASS_D_LOCAL_MEASURE.md;
  docs/research/system_woofer_2026-11-18/SENIOR_REVIEW_HANDOFF_2026-11-19.md sections 3-4 (case refs #1-#6);
  skills hornlab-gpu-job (lock + hygiene only) and hornlab-evidence.
PRECHECK: no live CPU-lane search (runs\.cpu.lane.lock), hold the lock for the whole pass.
STEPS (one BL job at a time):
  D1 WP2 matrix: solve #6 + demo-motor x default box -> 2x2 complex delta table.
  D2 WP1 LF band: 20-200 Hz log-spaced overlay on #4, #5 (+ D1 default-box cell); Fb + port-velocity check.
  D3 WP3 real-motor assembled R2 vs demo A/B.
  D4 WP5 convergence on R2: one mesh refinement, frequency densification near XO, one float64 control.
     Write tolerances in the evidence doc BEFORE solving.
  For each: .venv\Scripts\python.exe -m hornlab_search.system.cli funnel --plan ... ; owner signs an
  AuthorizationRecord for exactly those case keys; funnel --execute --allow-bl --authorization <file>;
  evidence doc in docs/research/system_woofer_2026-11-18/; tools\evidence\verify_evidence_quotes.py on it;
  regenerate docs\system_data; add case declarations to readiness.yaml; one commit with CONTINUITY + ISSUES.
STOP on: BL refusal, validate rc != 0, a result contradicting the 2x2 expectation.
RULES: all ten rules in docs/system_v1/HANDOFFS.md.
REPORT: commits, case keys, delta tables, PR link (draft into hornfab-all-2026-11-18).
```

## Pass E

Not schedulable until you answer each gate with values. Item list and gates:
`docs/system_v1/PASS_E_GATED.md`. When a gate opens, write a handoff in the same format as above.
