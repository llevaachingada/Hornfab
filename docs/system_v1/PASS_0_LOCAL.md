# Pass 0: local prerequisites (Windows canonical checkout, no GPU, no BL solve)

**Who:** the local orchestrator (single lane, serial). **Where:** `C:/Users/hunte/Hrns/hornlab-search`.
**Why first:** cloud lanes cannot see the untracked GUI trio or `system_runs/`. Until this pass lands,
cloud GUI work would conflict (finding N3) and cloud readers have no real case bytes to test against.
**Can run in parallel with Pass A** (Pass A touches no GUI file).

## Steps (checklist)

- [ ] **0.1 Land the untracked GUI trio as one commit.** `hornlab_search/gui/static/hw3d.js`,
      `hornlab_search/gui/static/hw_screen.js`, `hornlab_search/gui/data_hw_stage.py`, plus the
      `hw.js`/`app.js` edits that import them and their tests. Run the GUI offline tests
      (`tests/system/test_gui_hw*.py`, `tests/test_gui*.py`) and paste counters. Known red baseline:
      `test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_or_process_kill_paths`
      (do not grow it). Leave other lanes' unrelated files (budget-driver audit,
      `examples/score_identities.yaml`, scratch) unstaged.
- [ ] **0.2 Browser checklist** (handbook Appendix C) at 1280/1009/768/375 for `#/hw/*`. Record
      pass/fail per page in the CONTINUITY entry. Do not fix here; log failures as F-issues for Pass C.
- [ ] **0.3 Capture the fixture pack** (after lane A6 has merged its tool; if it has not, skip and
      do this at the start of Pass B):
      ```powershell
      .venv\Scripts\python.exe tools\system\capture_fixture_cases.py --store system_runs --out tests\system\fixtures\case_store --per-kind 2
      ```
      Review the copied bytes (manifests + small JSON only, no `.npz`/`.msh` over 256 KB). Commit.
- [ ] **0.4 Regenerate exports** on the current store:
      `tools\data\system_cases.py --root . --out docs\system_data --pretty` and
      `tools\data\top_designs.py` (only if the live night has appended since `9714b39`).
- [ ] **0.5 Fix doc drift D3/D4/F18:** `docs/ACTIVE_STATE.md` (system GUI + gates B/C + pointer to
      `docs/system_v1/`), `docs/CODE_MAP.md` rows for files that do not exist (`hw_compare.js`).
- [ ] **0.6 Owner answers (shape only, values later).** Ask the owner to confirm the three schema
      shapes in `docs/system_v1/01_CONTRACTS.md` §3 (calibration, method caps fidelity), §4
      (authorization), §5 (observation). Record answers in `readiness.yaml` decisions block. If the
      owner changes a shape, amend `01_CONTRACTS.md` before Pass B starts.
- [ ] **0.7 Commit + push** with CONTINUITY/ISSUES entries; PR into `hornfab-all-*`.

## Done when

- `git status` shows no untracked `hw*.js` / `data_hw*.py`; GUI boots from a clean clone.
- Browser checklist results recorded.
- Fixture pack committed (or explicitly deferred to Pass B start).
- Owner shape answers recorded.

## Paste-ready brief

```
You are the local orchestrator for HornFab System v1 Pass 0. Read docs/system_v1/README.md
(sections 1-6) and docs/system_v1/PASS_0_LOCAL.md, then do steps 0.1-0.7 in order in the canonical
checkout. No GPU, no BL solve. Do not stage unrelated lanes' files. Commit once at the end with
CONTINUITY and ISSUES entries and open a draft PR into hornfab-all-*. Report: commit sha, test
counters, browser checklist table, owner answers, anything deferred.
```
