# ADR — M1 research snapshot (read-only engineering research view)

Status: accepted for M1, 2026-11-27. Scope: the brief in `00_OPUS_ENTRYPOINT.md` (owner download,
not committed) plus the design mockup `research_dashboard.html` (reference SHA `898773d6`).
The "architecture package" and its tests named in the entrypoint were **not** in the hand-off folder;
only the entrypoint and mockup were. Acceptance tests below are therefore authored here.

## Reference vs local state (recorded, not assumed)

- Mockup reference `898773d6` (2026-11-25T18:08-05:00) is an ancestor of local HEAD `bd5b769c`
  (branch `hornfab-all-2026-11-18`, 4 ahead of origin). Between them: 177 files, +15 740/−4 166.
  The three cited evidence packets are byte-unchanged except 10 restored metric-BO research docs;
  `objective/size_penalty.py` + `objective/replay.py` were added (soft size penalty, opt-in).
  The score-breakdown size-penalty fix lives only on `claude/hungry-sinoussi-4bc609` (not merged),
  so any size-penalty run would show its penalty as an explicit `unattributed` residual here.
- Worktrees present (not touched): `hornfab-metric-bo-wt`, `.claude/worktrees/hungry-sinoussi-4bc609`,
  `hornlab-woofer-system-wt` (locked). GPU lock `runs/.gpu.lock` is stale (pid 19072, 2026-11-26);
  M1 needs no GPU and does not touch it.

## Decisions

1. **Score attribution: reuse, do not copy.** Contributions come from
   `gui/data_breakdown.score_breakdown` (which calls the objective package's own weight resolvers).
   The snapshot stores per-term weight × stored raw term, the stored total, and the exact residual
   `total − Σ contributions` (printed with `repr` precision). No new scoring version.
2. **Strict grouping.** A cohort key is `(config_name, objective_version, brief_hash, mode, backend)`;
   a config name spanning more than one key is split and flagged `mixed_identity`, never pooled.
   J is never compared across keys; the Overview shows J only inside one key, and the
   screen/verify canary shows ranks, labelled as two score identities.
3. **Manifest cutoff.** `cutoff_utc` is an input. Run dirs whose `run.json.started_utc` is after it,
   and rows whose `created_utc` is after it, are excluded and **counted** in the manifest.
   Committed sources are read from a pinned git commit (`git show <sha>:<path>`); untracked
   `runs/` sources are read from disk and pinned by sha256. The snapshot id is the sha256 of the
   canonical manifest (sources + cutoff + generator version), so a changed input is a new snapshot.
4. **Artifact adapters (read-only, no solver imports).** `hornlab_search/research/sources.py`:
   dose experiment (`results.json` + the run dirs' `best.json`/`run.json`), cohort inventory
   (`runs/*/run.json` + `search.ndjson`, joined to the existing admission artifacts
   `runs/v11_bo_day_planning/cohort_*/{offline_scores,holdout_comparison}.json`), mesh fidelity
   (`MESH_POLICY_AB.csv`, `ACOUSTIC_CONVERGENCE.csv`), canary (`work_v4` study rows, with the
   rehearsal package as a replicate). Inherited handoff claims (the §3 table) are parsed as
   *claims* and reconciled against artifacts, never used as values.
5. **Status vocabulary.** Row/cohort states are distinct: `ok`, `failed:<kind>`, `penalty`,
   `missing` (artifact absent), `unsupported` (inert by construction, e.g. CAD rear coarsening),
   `unknown` (field absent in a present artifact). Missing evidence is listed, not hidden.
6. **Evidence grades.** Each finding carries `observation` (what rows show), `hypothesis` (what it
   may mean), `action` (what to do, never auto-dispatched), and `evidence` = row ids that resolve
   to `{source, sha256, pointer}`.
7. **Outputs from one artifact.** `snapshot.json` is the artifact; `rows.ndjson`,
   `findings.ndjson`, `manifest.json` and `index.html` are rendered from it (the HTML embeds the
   same JSON bytes and recomputes nothing).
8. **Front-end route: none added.** Output goes to `runs/analysis/research_<date>_<id8>/`, which
   the GUI already serves at `/analysis/<set>/index.html` (existing guarded route). `gui/server.py`,
   the old run report and all routes are unchanged; a live GUI needs no restart.

## Acceptance tests (`tests/test_research_snapshot.py`, offline, fixtures = the real 11-25 rows)

A1 every numeric leaf in the snapshot sits in a cell with a resolvable `src`; A2 attribution
residual of every dose row equals stored total − Σ contributions exactly, and |residual| < 1e-9
for the v11 rows; A3 the lowest-J fixed-throat dose (`h065`, 4.6755) is a predeclared FAIL and the
throat-0.25 run PASSES (finding derived, not hard-coded); A4 a cutoff before 2026-11-25T15:39Z drops
the batch-4 runs and records the exclusion; A5 the same inputs give a byte-identical snapshot;
A6 a changed input changes the snapshot id; A7 a config name with two brief hashes splits into two
cohorts; A8 missing holdout → `missing`, replay 1/180 → `replay_mismatch`; A9 rehearsal vs v4
canary replicate agree to < 1e-5 (negative control for solve noise); A10 HTML contains the
embedded snapshot bytes and no number absent from the JSON.
