# Overview phases 2–4 — evidence (2026-11-20, CPU only)

Implementing pass for `docs/overview/OVERVIEW_IMPLEMENTATION_PLAN_2026-11-19.md` §4 WP2.1–WP4.3.
**No GPU, no solver.** `runs/` is read-only except the two GUI-written files the plan allows
(`runs/overview/index.json`, `runs/overview/finding_state.json`) and an explicit snapshot job.

All numbers below are **[measured]** on this machine (RTX 4060 box, desktop idle) with
`.venv\Scripts\python.exe`; quoted lines are verbatim terminal output.

## 1. Tests

```
> .venv\Scripts\python.exe -m pytest -o addopts="" -q tests/test_gui_overview.py tests/test_gui_overview_findings.py tests/test_gui_overview_index.py tests/test_gui_overview_states.py tests/test_gui_overview_registry.py tests/test_gui_overview_state.py tests/test_gui_overview_health.py tests/test_gui_overview_params.py tests/test_gui_overview_snapshot.py -p no:cacheprovider
79 passed in 1.37s
```

```
> .venv\Scripts\python.exe -m pytest -o addopts="" -q tests/test_gui_overview_api.py -p no:cacheprovider
4 passed in 0.31s
```

`-o addopts=""` neutralises the repo's `addopts = "-ra -q"`, which otherwise double-quiets pytest and
hides the summary line.

## 2. Live payload on the real `runs/` tree

```
> .venv\Scripts\python.exe -c "... O.overview(r, r/'runs', days=14) ..."
cold 9.98 s runs 305 identities 11
warm 2.16 s runs 305
states {'probe': 1, 'refusal_storm': 1, 'box_limited': 0, 'improving': 12, 'stale': 0, 'converged': 30}
findings-ready lines 43
```

After the index existed, the same calls split as:

```
records 0.06
full 0.82
states only 0.59
```

(Cold = first call on a tree with no `runs/overview/index.json`; it builds the index. Warm = index
present. The 0.59 s state pass re-reads the best run's ndjson for the 43 ranked lines; phase 1's warm
0.4–0.7 s did not include states.)

```
> ... F.findings(ov, r/'runs')
findings 19 in 1.57 s
Counter({'budget': 12, 'refusals': 4, 'tie_verify': 2, 'registry': 1})
Counter({'open': 13, 'resolved': 6})
Counter({'medium': 16, 'high': 3})
  high tie_verify home_landscape_v10 90.0 | 3 lines inside one floor
  high tie_verify compact400_v10xo 90.0 | 2 lines inside one floor
```

```
> ... RG.load_project_registry(Path('.'))
counts {'hw': 23, 'project': 22, 'total': 45, 'open': 44, 'by_level': {'CRITICAL': 3, 'HIGH': 5, 'MEDIUM': 15, 'LOW': 10}}
errors []
areas ['data', 'hw', 'search', 'software']
```

```
> ... App(r, r/'runs')._get_uncoalesced('/api/overview/findings', {'days': ['7']})
findings 30 Counter({'budget': 12, 'software': 11, 'refusals': 4, 'tie_verify': 2, 'registry': 1}) {'critical': 0, 'high': 3, 'medium': 27, 'low': 0}
```

```
> ... _get_uncoalesced('/api/overview/params', {'days': ['7']})
10 [('home_landscape_v7', 15, 5), ('room_80x60_v7', 2, 2), ('home_landscape_v7_smooth', 5, 0), ('lecleach_rollback_1in_v6', 1, 0), ('home_landscape_v10', 7, 2)]
```

Finding-state round trip through the POST route (real tree, then the smoke entry removed):

```
post True
after acknowledged
reopen True
final open
```

## 3. Snapshot (WP4.1 + WP4.2), end to end

Profile `gui-verify-8766` server was running; the snapshot itself is the new CPU job entry, run
directly with a one-day window so the smoke stays cheap:

```
> .venv\Scripts\python.exe hornlab_search/gui/data_overview_snapshot.py --days 1 --out-dir <temp>
wrote ...\overview_2026-11-20\spec.yaml (convergence 27, walls 27, term_balance 27, sensitivity 21)
report_day OK: 102 ok / 0 errored section(s) -> ...\overview_2026-11-20
overview snapshot: spec -> ...\overview_2026-11-20\spec.yaml
overview snapshot: report_day -> ...\overview_2026-11-20
overview snapshot: report_day exit 0
EXIT=0
```

27 lines of work → 27 section ids per tool (no per-run repetition); 102 of 102 sections ok.
`overview-snapshot` is not in `jobs.GPU_KINDS` and its `build_argv` returns `gpu=False`
(`tests/test_gui_overview_snapshot.py`), so it may launch while a solve holds the lock; no lock was
faked for this pass (a real solve was not run).

## 4. Browser check (plan WP-INT step 3)

`tools/gui/browser_check.py` with the Python 3.13 interpreter that has Playwright (the `.venv` does
not), against the **separate** `gui-verify-8766` server; the owner's 8765 server was untouched.

```
> ... tools/gui/browser_check.py --base http://127.0.0.1:8766 --out docs/evidence/overview_phase234_2026-11-20/main \
    --routes "/#/overview,/#/overview?tab=leaders,/#/overview?tab=typologies,/#/overview?tab=next,/#/overview?tab=decisions,/#/overview?tab=params" \
    --widths "1280,375" --themes "dark,light"
0 failing combination(s); report: docs\evidence\overview_phase234_2026-11-20\main\browser_report.json
```

24 combinations (6 tabs × 2 widths × 2 themes): zero console/page errors, zero page-level horizontal
scroll, URL state restored on reload. Re-run after the visual-QA fix pass (same result). Per-tab
passes also `0 failing combination(s)`: `next/` 4, `decisions/` 4, `params/` 4 (1280/375 × dark/light),
`briefing/` 1, `leaders/` 1, `typologies/` 1.

Screenshots kept: one representative per tab (1280 dark; params also 375 light for the narrow table),
plus every `browser_report.json`. Light/dark duplicates were dropped to keep the bundle at ~4 MB.

Known limit of the tool: screenshot names drop the URL query, so tabs share a filename in one run;
the per-tab folders exist for that reason, and `main/` keeps only its report.

## 5. Visual QA → fixes

An independent image review of the first pass found 16 issues; 2 were blockers (the Parameters table
losing BEST J / bound-hit columns at 375 px, and a dropped/duplicated expanded-group header) and the
rest were cosmetic bugs (`WP WP4`, a 50 px character-broken SOURCE column, a risk counter implying
missing rows, duplicated timestamp, severity ordering). All were fixed in the three `overview_*.js`
modules plus a severity tie-break in the findings sort key (`F.sort_key`: status, −score, severity);
the screenshots above are from the re-shot pass and the browser check was re-run clean.

## 6. What was not run

- A full 14-day snapshot (the smoke used `--days 1`); the snapshot is an owner action in the GUI.
- Any GPU solve, `gpu-clean`, or GPU-lock manipulation.
- `tests/test_gui_lanes.py`: the lane-log pick was phase 1 and is unchanged by this pass; the full
  targeted run above covers the Overview modules, and `test_gui_overview.py` still asserts the lane
  pick.
