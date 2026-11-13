# CLOUD COMPLETION KICKOFF — bo-study-v1.1 (2026-11-13)

Owner-authorized handoff: complete the remaining implementation in full, offline, parallel
lanes (<=3 + you as parent). Real solves/pilots, production adoption, v8 registration and
further defaults remain owner-gated.

## 0. Identity

- Repo: `llevaachingada/hornlab-search`, branch `main` (single canonical checkout rule —
  `AGENTS.md` owner amendment).
- Protocol: **bo-study-v1.1** (`docs/research/BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md`).
  Governing: `docs/research/HORN_OPTIMIZATION_HARDENING_2026-11-12.md`.
- Parent records committed under `docs/research/bo_study/` (PARENT_M0_FREEZE — the frozen task,
  identities, encoding `active-projection-v1` d=13, metric policy, §8 artifact schemas —
  PARENT_DEPENDENCY_DECISION, AGENT_HANDOFF, SPLIT_OWNERSHIP, CONSOLIDATION, PARENT_M0_ASSESSMENT/RESUME/CONTRACT).
- Curated analysis evidence committed under `docs/evidence/bo_study_2026-11-12/`
  (r0 offline rescores, s0 catalog/cohort, b2 pool/ledger/trainingset, s3 statistics,
  s4 parameter_study artifact, s6 source_fidelity, s9 matrix/baselines, s11 pilot manifests).

## 1. Environment

- Project interpreter: `.venv\Scripts\python.exe` (Windows paths; Python 3.12.10).
- The Linux/cloud box must reproduce: Python >=3.11, torch (CPU), numpy/scipy; install
  `botorch==0.18.1 gpytorch==1.15.2 linear_operator==0.6.1` in an ISOLATED venv for `bo/` engine
  work (never in the solving env). `hornlab-waveguide-mesher` (pinned fork per `TOOLCHAIN.md`)
  is required for pool/cohort geometry tests; tests without it skip honestly
  (`conftest.requires_mesher`).
- Offline tests only: no GPU/BEM solves (the local GPU night queue is not yours), no dataset/
  cache/runs writes, no config/default/objective-registration changes (v8 stays unregistered),
  never `V8Params.for_class("A")`, never weaken tests, never rank J across objective versions.

## 2. Done (committed on main)

- **M0**: replay/rescore with brief-target scoring + three identity layers; experiment catalog/
  cohort (native-only census); parameter-activity ledger + geometry fixtures (target-1
  exponent invariance, target-3 activity); S3 honest cost/replicate accounting (merged).
- **M1**: `parameter_study` (200-row join, 5 designs, held-out passed, effects/interactions
  diagnostic; recommendations suppressed where independent-group support is insufficient) and
  `source_fidelity` artifacts; GUI: full analysis page visual overhaul + two study-artifact
  renderers; renderer fixtures committed (`scratch/bo_m0/s10/fixtures/**`, force-added).
- **M2 engines**: locked scalar GP/qNEI proposal engine (pending/revalidation/tie-breaks/
  fixed-noise; lazy botorch, CPU-only); `pareto_pool_v1`, contract/cost/TR components;
  canonical v4 `bo/metrics.py` policy; real native TrainingSet builder (197 rows, d=13).
- **M3 foundations**: `studies/` registry (SQLite, revisions/idempotency/crash tests), CPU job
  bridge, serial runner foundations, six-page study UI wired into Analysis.
- **S9**: dry-run timing harness + A/B matrix plan + measured baselines.

## 3. Remaining (in order; parallel lanes A–C + you)

- **A (M2 evidence)**: run subset/noise/pool sensitivity diagnostics + space-filling/CMA-vs-BO
  comparisons over the real 197-row TrainingSet; publish immutable
  `pool_manifest.json`/`proposal.json` ("cheap-check-passed; mesh/acoustic eligibility unknown").
- **B (execution package)**: finish study actions + execution-package authorization; produce
  the pilot package per spec §4 (18 screen/6 verify/24 total/120 attempts, deadline required,
  lane ownership) and `study package --dry-run` clean; wire the runner's production evaluator
  adapter so the S9 A/B matrix becomes executable.
- **C (B8 adversarial)**: full fake-evaluator loop through service/CLI/API/GUI (create →
  snapshot → analyze → propose → package → dry-run → fake screen → verify/audit → refit →
  decide/export/child); crash injection at every persistence boundary; duplicate-launch/
  revision attacks; dry-run spawns zero solves/writes zero acoustic records.
- **D**: complete the two S11 pilot manifests' executor-facing fields (deadline placeholder is
  intentional; wall deadline must be chosen from measured logs at scheduling time).
- **E (parent)**: reconcile per-slice commits; full offline suite in both venvs; push-rule docs
  (CONTINUITY+ISSUES same commit as any push); update `docs/INDEX.md`/`CODE_MAP.md` rows.

## 4. Known open items (also in `docs/ISSUES.md`)

- Runner's production evaluator adapter (blocks the S9 A/B matrix execution).
- 3 native rows (shard 57 row 276-278) uncatalogued at snapshot time (future catalog regen).
- `pyproject.toml` optional `bayes` extra not yet registered (isolated venv is the sanctioned engine).
- Pilot manifests are execution-authorized=false by design.

## 5. Verification quickstart

```
.venv/Scripts/python.exe -m pytest tests -q -p no:cacheprovider -m "not gpu and not crosscheck and not slow"
# engine-only:
bayes-venv python -m pytest tests/test_bo_model.py tests/test_bo_acquisition.py tests/test_bo_propose.py -q
# JS:
node --check hornlab_search/gui/static/app.js hornlab_search/gui/static/studies.js
python -m compileall -q hornlab_search tools
```
Focused suites are listed in `CONTINUITY.md` (top entry of this push).
