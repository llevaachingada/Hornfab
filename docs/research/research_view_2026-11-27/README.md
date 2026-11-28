# M1 research snapshot — handback (2026-11-27)

ADR: [ADR_M1_research_snapshot.md](ADR_M1_research_snapshot.md). Code: `hornlab_search/research/`
(`provenance.py`, `sources.py`, `findings.py`, `build.py`, `template.html`). Tests:
`tests/test_research_snapshot.py`. Nothing in production scoring, optimizers, caches, mesh defaults,
`gui/server.py` or the old report/routes changed. No GPU, no solver, no BEM.

```powershell
.venv\Scripts\python.exe -m hornlab_search.research build --cutoff 2026-11-25T23:59:59Z
```

Output: `runs/analysis/research_<date>_<id8>/` (`snapshot.json`, `manifest.json`, `rows.ndjson`,
`findings.ndjson`, `index.html`). The GUI's existing route serves it at
`/analysis/research_2026-11-25_08a6d477/index.html`. The HTML embeds the exact `snapshot.json` bytes.

## Fresh snapshot (measured in this pass)

`snapshot 08a6d477803f510e`, cutoff `2026-11-25T23:59:59Z`, commit `bd5b769cffee`, 455 sources,
50 exclusions (49 runs after cutoff, 1 row without timestamp: `dose:rolled:control_epw9`), 8 findings,
150 missing/unknown cells. Committed copy: [snapshot_08a6d477/](snapshot_08a6d477/) (manifest, findings,
build logs). Two consecutive builds gave byte-identical `snapshot.json` (sha256 checked).

## Source / data coverage

| Area | Source | Coverage |
|---|---|---|
| Dose experiment | `cd_backbone_2026-11-25/results*.json` + 23 committed configs (git) | 24 rows (rolled 14, Lamé 7, second rolled body 3); 22 corroborated `match` against local `best.json` (Δ 0); 2 controls have no job record (`run_dir_missing`) |
| Cohort inventory | `runs/*/run.json` + `search.ndjson` | 1043 run dirs scanned; 803 other objective versions, 8 without run.json; 152 v11 cohorts (strict key) |
| Admission | `runs/v11_bo_day_planning/cohort_*` + `acquisition_confirmation_2026-11-23/confirmation.json` | 10 cohort dirs + Fold confirmation (linked by persisted `eval_run_id`) |
| Claims | metric-BO handoff §3 table | 29 rows: 9 agree, 1 conflict, 19 not comparable (no admission artifact) |
| Mesh fidelity | `MESH_POLICY_AB.csv`, `ACOUSTIC_CONVERGENCE.csv` | 5 acoustic cases, 1 mesh-only class, 1 inert (CAD) |
| Canary | `runs/metric_bo_canary_2026-11-23/work_v4` + rehearsal `work` | 2 screen/verify pairs, 7 replicate pairs |

Unavailable telemetry (recorded, not inferred): GPU wall time/VRAM at rear factor 1.5; physical
measurements (none; all simulated BEM); per-row GPU telemetry in the inventory (not aggregated).

## Example agent finding resolved to source

`matched_pair` (id `960c75bf36ecd0d9`): `rolled_bb_h065` J 4.6755 fails `min_re_z_ok`;
`rolled_bb_h065_th025` J 4.6787 passes; only `g_bb_throat_frac` differs (0.15 → 0.25). Every cell resolves:
`results.json#/rolled/runs/rolled_bb_h065/J`, `…/min_re_z_from_900` (0.8638 → 0.9928),
`results.json#/rolled/checks/rolled_bb_h065/min_re_z_ok` = false,
`rolled_bb_h065.yaml#/bounds/g_bb_throat_frac/lo`. ΔJ = calc `J(pass) - J(fail)` = 0.003167.

The data also show what the mockup did not: the true lowest J in that identity is
`rolled_bb_h065_ri022` (4.3488, roll-in 0.22), which also fails loading (`scalar_not_gate`).

## Residual reconciliation (exact)

Attribution = `gui/data_breakdown.score_breakdown` weights × stored terms; residual = stored total − fsum.
All 24 dose rows: residual ∈ {0, ±8.88e-16, 1.78e-15} (worst `lame_bb_h100_m040_t25_r15`
1.7763568394002505e-15). No unattributed term. Stored total equals stored J on every row.

## Replay and negative controls

- Replay at cutoff `2026-11-24T23:59:59Z` → snapshot `561b1d1a46120c3c`: 0 dose rows (all 11-25), so no
  dose findings; the cohort counts equal the handoff table, and the c500 conflict persists.
- Solve replicate: 7 designs solved in two independent canary packages, max |ΔJ| 2.71e-06.
- Appending a row after the cutoff leaves the snapshot id unchanged; changing a row before it changes
  the id (test A5/A6).

## Reconciliation finding (data quality)

Handoff §3 (line 136) says `r3_c500` "needs strict artifact + holdout/B4"; the artifact
`cohort_c500_2026-11-24/holdout_comparison.json` (written 2026-11-24 19:21Z) says
`PASS_FOR_EXPLORATORY_PILOT`. The handoff was committed 2026-11-25 23:08Z, so the table was stale when
committed. CONTINUITY 11-25 already records c500 holdout PASS.

## Tests (run in this pass)

`tests/test_research_snapshot.py` 14 + neighbours (`test_gui_score_breakdown`, `test_gui_views_analysis*`):
**45 tests, 0 failures, 0 errors, 0 skipped** (junitxml). The full suite was not run here (another
session's full run was in progress).

## Blockers / limits

- The "architecture package" and its tests named in the entrypoint were not in the hand-off folder.
- Admission artifacts are placed against the cutoff by file mtime (they carry no timestamp).
- Fold canary ↔ cohort link is a handoff claim (canary run.json has no `config_name`).
- Inherited claim statuses are parsed from markdown by keyword; 19 rows have no comparable artifact.
- Score attribution for size-penalty runs would show the penalty as residual until the
  `hungry-sinoussi` breakdown fix is merged.

## Proposed next milestone (M2, only now that M1 runs)

Add curve-level drilldown from saved `response.npz` (H/V/Re(z) vs frequency per dose row), extend the
inventory to v7/v10 identities with the same strict key, and a GUI nav link to the latest snapshot.
