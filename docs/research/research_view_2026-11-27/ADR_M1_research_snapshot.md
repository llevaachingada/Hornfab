# ADR — M1 research snapshot (read-only engineering research view)

Status: accepted, 2026-11-27; senior hardening pass same day. Scope: `00_OPUS_ENTRYPOINT.md` (owner
download, not committed) plus the mockup `research_dashboard.html` (reference SHA `898773d6`). The
"architecture package" and its tests named in the entrypoint were not in the hand-off folder, so the
acceptance tests are authored here.

## Reference vs local state (recorded, not assumed)

- `898773d6` is an ancestor of the build commit. The three cited evidence packets are byte-unchanged
  since then; `objective/size_penalty.py` was added later (opt-in). The breakdown size-penalty fix lives
  only on `claude/hungry-sinoussi-4bc609`, so a size-penalty run would show the penalty as an explicit
  residual here.
- Worktrees present, untouched. GPU lock `runs/.gpu.lock` is stale (2026-11-26); no GPU is used.

## Decisions

1. **Score attribution: reuse, do not copy.** `gui/data_breakdown.score_breakdown` (the objective
   package's own weight resolvers) × stored terms; exact residual = stored total − fsum.
2. **Strict grouping.** Cohort key = `(config_name, objective_version, brief_hash, mode, backend,
   fidelity_policy)`; `fidelity_policy` = sha256[:8] of the run's mesh + solve blocks. Config-SHA
   revisions inside a cohort are reported as `treatment_variants`, not split (they do not change J
   comparability). J is never compared across keys.
3. **Manifest cutoff.** `cutoff_utc` input (`now` by default). Runs/rows after it are excluded and
   counted; committed sources are read at a pinned commit; `runs/` logs are pinned on the lines used,
   so appends after the cutoff do not change the snapshot id. Admission artifacts are placed by mtime.
4. **Adapters (read-only).** Dose experiment (committed `results*.json` + committed configs; local run
   dirs corroborate J and config equality), cohort inventory (reproduces
   `v11_cohort_inventory.py` on all 200 configs), admission artifacts, handoff claims (reconciled, never
   used as values), variable-mesh CSVs, canary + replicate, and the **existing**
   `tools/analysis/optimizer_evidence.py` (optimizer-evidence-v1) for cost ledger, outcome buckets,
   failure signal, walls and cross-run compatibility — carded only when a run has no rows after the
   cutoff.
5. **Refined-mesh verdicts are fidelity-matched.** `analyze.py` scored epw-9 rows against the epw-6
   control; PREDECLARED's refined-mesh gate requires the mesh-delta rule AND the six rules at epw 9.
   The three control-relative rules are re-evaluated against the epw-9 control (labelled calc).
6. **Status vocabulary.** `ok`, `failed:<kind>`, `penalty`, `missing`, `unsupported`, `unknown`,
   `run_dir_missing`; cohort statuses `pilot_eligible` (PASS_FOR_EXPLORATORY_PILOT only — not full
   admission), `hold`, `replay_mismatch`, `needs_admission`, `not_evaluated`; an unrecognised PASS_* is
   `unknown`, never promoted.
7. **Three audiences, one artifact.** `snapshot.json` is the artifact. Findings carry observation /
   hypothesis / action (engineers), `plain` (non-technical readers) and structured `next_steps` with
   `needs_gpu` / `needs_owner_approval` (planning agents). `summary.json` (written last),
   `AGENT_GUIDE.md`, `rows.ndjson`, `findings.ndjson`, `manifest.json` and `index.html` are rendered from
   it. Nothing is dispatched.
8. **Front end.** Output in `runs/analysis/research_<date>_<id8>/`, served by the existing `/analysis/`
   route. GUI: Overview → Briefing → "Generate research snapshot" runs the CPU-only `research-snapshot`
   job kind (`gui/data_research.py`, not in `GPU_KINDS`); `GET /api/research/snapshots` lists complete
   snapshots. Additive changes to `gui/jobs.py`, `gui/server.py`, `gui/static/overview.js`; old report
   and routes unchanged.

## Acceptance tests

`tests/test_research_snapshot.py` (A1–A10 plus hardening: every committed `src` resolves mechanically;
derived values are calcs; fidelity-matched refined-mesh verdicts; corroboration of J and config;
fidelity-policy split; canonical brief-hash rule; audience fields; optimizer-evidence cutoff guard) and
`tests/test_gui_research_snapshot.py` (CPU kind, cutoff validation/refusal, listing only complete
snapshots, API route, preview command, button wiring).
