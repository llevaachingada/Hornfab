# M1 research snapshot — handback (2026-11-27, after senior hardening)

ADR: [ADR_M1_research_snapshot.md](ADR_M1_research_snapshot.md). Code: `hornlab_search/research/`
(`provenance.py`, `sources.py`, `findings.py`, `guide.py`, `build.py`, `template.html`) and
`hornlab_search/gui/data_research.py`. Tests: `tests/test_research_snapshot.py`,
`tests/test_gui_research_snapshot.py`. No production scoring, optimizer, cache, mesh default or GPU change.

## How to run

- GUI: Overview → Briefing → **Generate research snapshot** (empty cutoff = now; or an ISO instant to
  reproduce). CPU-only job, ~5–10 s; the card then shows the newest snapshot with an "Open research
  report" link and the agent files.
- CLI: `.venv\Scripts\python.exe -m hornlab_search.research build [--cutoff 2026-11-25T23:59:59Z]`.
- Output: `runs/analysis/research_<date>_<id8>/` — `index.html` (people), `summary.json` +
  `AGENT_GUIDE.md` + `findings.ndjson` + `rows.ndjson` (agents), `snapshot.json`, `manifest.json`.

## Fresh snapshot [measured]

`bc737b910572690c`, cutoff 2026-11-25T23:59:59Z, commit `d2273848`: 460 sources, 49 exclusions,
9 findings, 155 missing/unknown cells listed. Built through the GUI entry script and the CLI with
byte-identical digests ([build.log](snapshot_bc737b91/build.log)). Replay at 2026-11-24 → `851c572d`,
0 dose rows (all solved 11-25), 6 findings ([log](snapshot_bc737b91/build_replay_cutoff_2026-11-24.log)).
Committed copy: [snapshot_bc737b91/](snapshot_bc737b91/). Screens: [desktop](m1_desktop_1440.png),
[narrow](m1_narrow_500.png), [GUI card](gui_overview_research_card.png).

## Verification [measured]

- Every `{v, src}` cell resolves mechanically to its pinned source: **1210 ok, 0 bad** (898 committed via
  git, 312 `runs/` from disk) — [resolve_all_cells.log](snapshot_bc737b91/resolve_all_cells.log).
- Independent adversarial check (separate agent): 27/30 sampled cells exact, all 8 findings supported,
  both cohort recounts exact, c500 conflict confirmed. Its 4 issues (derived time cited as raw, markdown
  pointers not mechanical, "holdout pass" overstating PASS_FOR_EXPLORATORY_PILOT, implicit control
  exclusion) are fixed and now covered by tests.
- Cohort inventory reproduces `runs/v11_bo_day_planning/v11_cohort_inventory.py` on all 200 configs
  (valid rows, runs, best J); the extra `lcl_beak_cohort` is the dead 11-26 job with no rows.
- All 22 committed dose configs equal the configs the runs recorded (`config_equal: true`).
- Attribution residual on all 24 dose rows with stored terms ≤ 1.78e-15.
- Canary replicate (two packages): max |ΔJ| 2.71e-06.
- GUI button clicked end to end on a test server: job `done`, exit 0, `gpu: false`, ~5 s.

## Assumptions corrected in the hardening pass

1. Refined-mesh (epw 9) verdicts: `analyze.py` compared them with the epw-6 control; now the mesh-delta
   rule plus the six rules vs the epw-9 control (both rows still pass). The epw-9 control is now a row.
2. Hard-coded markdown line numbers replaced by searched, mechanically resolvable anchors.
3. `PASS_FOR_EXPLORATORY_PILOT` is `pilot_eligible`, not "holdout pass"; unknown PASS_* is `unknown`.
4. The existing `optimizer_evidence.py` is now the cost/fidelity adapter for 13 admission-relevant
   cohorts (36 run cards) — it surfaced `software_drift` in Fold, c500 and FAV (new finding).
5. Cohort key gained a mesh+solve digest; config revisions shown as treatment variants.
6. The 150-row floor and the rule thresholds are cited from their documents, not hard-coded.

## Blockers / limits

- Architecture package and its tests were not provided. Admission artifacts are placed by mtime.
- Fold canary ↔ cohort link is a handoff claim. 139 small cohorts have no optimizer-evidence card
  (below floor, no admission artifact) — stated per cohort.
- GPU timing at rear factor 1.5 and physical measurements remain unmeasured.

## Next milestone (M2)

Curve-level drilldown from `response.npz`, v7/v10 inventories under the same key, and per-version
re-admission for the software-drift cohorts.
