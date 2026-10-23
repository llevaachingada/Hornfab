# Handoff for the collaborator pulling `main` tonight (2026-10-23, ~15:15 EDT)

Written by the owner's orchestrator session. `main` is clean and pushed at the commit that adds this file; the
offline suite on it is **808 passed, 18 deselected, exit 0**.

## 1. Read first (10 minutes)

1. `CLAUDE.md`: binding rules (file ownership, GPU hygiene, the three silent killers).
2. `docs/CONTINUITY.md`: the Status block, then the newest entries (newest first).
3. `docs/INDEX.md` (every doc) and `docs/CODE_MAP.md` (every module). `docs/ISSUES.md` for open items.

## 2. Setup on your machine

- Install as in `README.md` (`pip install -e ".[dev,crosscheck]"` into `.venv`; Python 3.12 is what CI uses).
- Offline tests (no GPU, no solver needed; the project's addopts double `-q`, so override them to get a summary line):
  `python -m pytest -p no:cacheprovider -o addopts="" -q -m "not slow and not gpu and not crosscheck"`
  Expect 808 passed, 18 deselected. Check the exit code, not just the dots.
- `hornlab-search doctor` reports what your machine can do. GPU solves need the `beat_cuda` backend on an NVIDIA
  card; a Mac has no supported GPU backend yet (`beat_metal` is NEXT_DEV_PRIORITIES P3, not built). The GUI
  (`hornlab-search gui`) is pure stdlib + browser and is **untested on macOS**: reports of what breaks are welcome.
- `runs/`, `dataset/` and `cache/` are local and gitignored, so you will not get the owner's results by pulling.
  Committed summaries are in `docs/evidence/` (including `docs/evidence/campaigns/` and `docs/evidence/runs/`).

## 3. What is running on the owner's GPU box tonight (do not depend on it)

- The overnight queue (FREEFORM sculpt searches) finishes around 16:00, then the **P2 12 kHz finalist verify
  pass** runs (top 3 designs of osse_axi, blend_osse_tractrix, perturbed_osse_hv, rosse_baseline under
  `examples/briefs/*_12k.yaml`, plus an epw check). Then: surrogate retrain (CPU), a Ctrl-C test, a timed rehearsal.
- The owner will not pull your changes until those GPU jobs are finished. The queue starts a fresh process per job
  and imports the code on disk, so **nothing gets pulled into that checkout mid-run**.

## 4. Files the owner's session WILL edit tonight (expect conflicts there)

| File | Why |
|---|---|
| `docs/CONTINUITY.md`, `docs/ISSUES.md` | Updated on every push (project rule). If you edit them, **add** your own dated entry at the top; when merging keep both sides, never overwrite. |
| `docs/evidence/HF12K_VERIFY_2026-10-23.md` (new), `docs/evidence/BETA_READINESS.md` | 12 kHz results, epw check, rehearsal timings. |
| `docs/BETA_SESSION_PLAN.md`, `docs/BETA_QUICKSTART.md` | Rehearsal friction fixes and the 12 kHz numbers. |
| `hornlab_search/cli.py`, `hornlab_search/search/*`, `hornlab_search/gui/static/app.js` | Only if the Ctrl-C test or the rehearsal finds a bug (small fixes). |

Anything else is unlikely to change tonight. **Please work on a branch and open a PR** rather than pushing to
`main`, so the owner can merge after the GPU jobs.

## 5. Rules that apply to your edits too

- Never edit `docs/plan/**` (frozen), the `Family` contract, gate thresholds or test tolerances, and never loosen a
  test. Widening bounds, a mesher/solver version bump, Boundary Lab work, or enabling Le Cléac'h need the owner's OK.
- We never modify the installed HornLab / BEAT / Julia packages (Magnus's code); every horn number is a YAML default
  in `examples/`. Every physics claim must trace to the mesher, the verified BEM solver, or published horn theory.
- Every push updates `docs/CONTINUITY.md` and `docs/ISSUES.md` in the same commit; a new doc or module gets a line in
  `docs/INDEX.md` / `docs/CODE_MAP.md`.
- New briefs: add new files, never edit the shipped ones in `examples/briefs/`.

## 6. What changed today (so you are not surprised)

- **Dead worker host recovery** (`solve/worker.py`, `solve/beat.py`, `search/cma.py`): the library's cached client
  is dropped after a host crash, the candidate is retried once, and a search stops (resumably, status `aborted`)
  after 3 consecutive `solve_failed` instead of scoring them as penalties.
- `to_training_arrays` drops `solve_failed` records from surrogate labels (`meta.skipped_solve_failed`).
- `verify --brief` is now applied; with a brief its results go to their own `runs/<ts>-verify-<id>`.
- GUI Launch re-reads the GPU lock every ~6 s. `docs/BETA_SESSION_PLAN.md` is GUI-first.

## 7. Open questions where your view would help (the owner decides)

- The objective: hand-weighted sum of terms in different units (`objective/scalar.py`, briefs' `weights`); `load`
  uses an arbitrary z_min 0.7. Normalisation proposal welcome.
- Bound proposals and pinned parameters: `docs/evidence/TYPOLOGY_COMPARE_2026-10-23.md`; sculpt anchors
  (`profileH/V.points.3.1` pinned at lo in 14 of 20 sculpt runs): widen/overlap the boxes vs reparametrise as
  positive increments.
- Surrogate gates (`docs/plan/11_PHASE2_SURROGATE.md`, `docs/evidence/CP-8d.md`): the `monotonic_flips` semantics
  question in `NOTES_FOR_SENIOR.md` (cp-8d addendum).
