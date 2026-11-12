# Test-suite efficiency review — measured burden and low-risk reductions (2026-11-12)

**Status:** PROPOSAL (owner decides; nothing in this document was applied). **Author:** day-plan orchestration
session, senior research pass. **Related:** `docs/CONTINUITY.md` 2026-11-12 entries, `docs/ISSUES.md`
2026-11-12 block, `NOTES_FOR_SENIOR.md` 2026-11-12 block, `.github/workflows/ci.yml`,
`docs/plans`/day plan `IMPLEMENTATION_PLAN_2026-11-12_DAY.md` section 0 rule 3.

**Question.** Development throughput in the 2026-11-12 day plan was dominated by test churn, not coding:
every small change or merge appears to trigger a large amount of testing. Is the setup unnecessarily heavy,
where does the time go, and what can be reduced **without removing coverage or weakening assertions**?

**Answer (short).** The tests themselves are healthy; the **execution topology** is wasteful. Today the
same commit was tested twice (push + pull-request triggers), docs-only commits re-ran the full ~6-minute
suite, the merge protocol added a full local suite per branch on top of CI, and ~24 unmarked integration
tests carry half the suite's cost. Fixing the topology (not the tests) is worth a 5–7x reduction in
wall-clock and CI minutes at equal coverage. Details and exact diffs below.

---

## 1. Measured facts (all [measured] on this machine / this repo, 2026-11-12)

### 1.1 The suites

| Measurement | Value | Source |
|---|---|---|
| Local offline suite (`-m "not gpu and not slow"`, venv with mesher+solver installed) | **2706 collected, 2704 passed, 2 skipped, 588.3 s tests + collection ≈ 10 min wall** | `oc-wt\A\scratch\junit_dayA_full.xml` |
| CI suite (`ubuntu-latest`, py3.12, minimal deps) | ~2,455 passed, 225 skipped, 21 deselected, **test step 352.8 s ≈ 5.9 min**; job end-to-end **~8 min** (observed 4m48–8m36) | Actions runs 432583…/43278307808 logs |
| Marked tests | **4 `gpu`, 6 `slow`, 1 `crosscheck`** (~3,000 test files: 207) | `grep` over `tests/` |
| Cost concentration (local junit) | **24 tests ≥ 5 s = 300.7 s = 51.1 %** of all test time; **54 tests ≥ 2 s = 67.5 %** | `junit_dayA_full.xml` |

Top offenders (local, mesher/solver installed — these are the seconds that repeat every run):

| s | test |
|---:|---|
| 35.5 / 35.3 | `test_search_export_step` (two STEP-export tests) |
| 28.9 | `test_gui_preview_shape::…osse_axi…` |
| 26.3 | `test_bassbox::test_recommendation_meets_the_owner_targets` |
| 21.8 | `test_report_html::…under_10_mb_for_200_evaluations` |
| 13.0 / 12.8 / 12.8 | `test_search_campaign` CLI-family tests |
| 11.4 | `test_search_pipeline_prefetch::cma_me…` |
| 11.1 | `test_gui_preview_shape::plughorn 3d…` |
| 8.6 / 8.2 | `test_solve_traces` (real mesh), `test_mesh_build::test_export_step` |
| 6.1–6.9 | `test_mesh_plughorn` (×4), `test_mesh_mid_ports`, `test_search_restarts` (×2), `test_design_freeform_sculpt`, `test_search_cma::resume`, `test_search_pipeline_prefetch` (×2) |

None of these carry a marker — they run in **every** targeted test invocation that touches their module
and in every local full run (CI skips the mesher/solver ones via `requires_*`, but still pays the GUI/report/
prefetch/campaign ones).

### 1.2 The churn (2026-11-12)

| Measurement | Value |
|---|---|
| CI workflow triggers | `on: push` **and** `on: pull_request` → **two full runs per branch push** |
| CI runs today | **122** (85 push + 37 pull_request) |
| CI run-minutes today | **824 min ≈ 13.7 h** (avg 6.8 min/run) |
| Conclusions | 81 success / 41 failure (failures were the optional-dep/path issues fixed today in #39/#41 + B's two CI fixes) |
| Orchestrator extra full suites today | 3 (D, E, A) ≈ **30 min** of local machine time, duplicating what CI already ran |
| Merge-time docs commits | 6 lane merges each added a CONTINUITY/ISSUES/CODE_MAP commit → **each re-ran the full CI suite** (×2 due to dual triggers) |

Root cause of the "every change triggers too much testing" feeling: **the same code is verified 2–4 times**
(CI push run + CI PR run + orchestrator local full suite + re-run after the merge-time docs commit), while
~50 % of the suite's time is spent in two dozen integration tests unrelated to the change.

---

## 2. Recommended changes, ranked by saving/effort

### R1 — Trigger CI once per commit (biggest single win, 3-line diff)

Every branch push fires both the `push` and the `pull_request` run (~2.3 push runs per PR run today).
Run CI on PRs, and on `main` only:

```yaml
on:
  pull_request:
  push:
    branches: [main]
```

Expected: ~50–60 % fewer runs (today: 85 push → ~10). Risk: none for coverage; a branch without a PR is not
gated — acceptable (PRs are the merge path).

### R2 — Cache pip downloads (one line)

```yaml
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
```

Saves ~40–60 s per run (install step today re-downloads numpy/scipy/torch/plot deps every time).

### R3 — Split CI into a full `ci` job and a fast `docs` job (the merge-churn killer)

The push rule ("every pushed commit updates CONTINUITY and ISSUES") plus the merge-time docs commit means
**docs-only commits are a large share of pushes**, and each re-runs the 6-minute suite. Add a second
workflow for docs-only changes, and make the full CI ignore docs-only paths:

```yaml
# .github/workflows/ci.yml
on:
  pull_request:
    paths-ignore: ["docs/**", "**/*.md", "NOTES_FOR_SENIOR.md"]
  push:
    branches: [main]
```
```yaml
# .github/workflows/docs.yml (NEW)
name: Docs check
on:
  pull_request:
    paths: ["docs/**", "**/*.md", "NOTES_FOR_SENIOR.md"]
jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: "pip" }
      - run: python -m pip install numpy scipy pyyaml pytest
      - run: python -m pip install -e . --no-deps
      # docs are an SSOT: the param catalog is generated FROM code and byte-checked
      - run: python tools/gen_param_catalog.py --check
      - run: python -m pytest -q tests/test_param_catalog.py tests/test_config.py
```

Caution (why the docs job still runs real tests): `docs/reference/PARAMETERS.md` and
`docs/reference/TYPOLOGIES.md` are **generated and byte-checked** by `tools/gen_param_catalog.py --check`
and `tests/test_param_catalog.py`; a docs-only PR can therefore break CI legitimately. The docs job keeps
that guard at ~60 s instead of 6 min. Expected: every docs-only commit (incl. all merge-time commits)
drops from ~8 min to ~1 min.

### R4 — Mark the measured heavy integration tests `slow` (do not delete them)

From §1.1, mark `slow` the following (they already have `requires_*` where needed; `slow` additionally
excludes them from the routine lane):

- `tests/test_search_export_step.py` (both tests, 35 s each)
- `tests/test_gui_preview_shape.py` (osse_axi 29 s, plughorn 11 s)
- `tests/test_bassbox.py::test_recommendation_meets_the_owner_targets` (26 s)
- `tests/test_report_html.py::test_report_under_10_mb_for_200_evaluations` (22 s)
- `tests/test_search_campaign.py` CLI-family tests (13+13+13 s)
- `tests/test_search_pipeline_prefetch.py` (11+7+6 s)
- `tests/test_solve_traces.py::test_dof_permutations_are_one_to_one_on_a_real_mesh` (9 s)
- `tests/test_mesh_plughorn.py` (6 tests, ~30 s total)
- `tests/test_search_restarts.py` interrupt/resume test (7 s), `tests/test_search_cma.py::test_resume…` (7 s)

Then add a **nightly** (or manual) `slow` job that runs them (`pytest -m "slow or gpu"` stays out of PR CI
and is run before checkpoints/releases). Expected: routine CI test step 353 s → ~250 s; local full suite
~10 min → ~5–6 min. Nothing is skipped permanently; the coverage still runs — on a schedule instead of on
every keystroke. The existing `slow` marker machinery already exists (6 tests use it).

### R5 — Orchestrator protocol: CI is the merge gate; local full suites are for shared-core changes only

Current day-plan rule 3 says the orchestrator serialises full local suites per branch. Today that duplicated
CI three times. Proposed replacement (same coverage, less duplication):

- Every lane PR: **targeted tests in the lane + CI green** (CI already runs the portable full suite).
- Run a **local full suite only when the branch touches shared core** (`hornlab_search/config.py`,
  `hornlab_search/search/evaluate.py`, `search/cma*.py`, `objective/**`, `types.py`, `dataset/record.py`)
  or once per merge batch.
- Paste CI's counters into the merging commit/PR instead of the local ones (the day plan requires counters;
  it does not require them to be local).

Expected: ~30–40 min/day of local wall clock saved on days like today.

### R6 — Require the CI check on `main` (prevents expensive red merges)

Branch protection is currently off: PR **#38 merged with red CI**, which cost two follow-up fix PRs
(#39, #41) ≈ 6 extra runs (~40 min). Require the `ci` check (and the `docs` check once R3 exists) on `main`.
With R1–R4 the gate is cheap, so requiring it is affordable.

### R7 — Optional: parallelism (`pytest-xdist`)

CI (2-core ubuntu): `pytest -n 2 -m "not slow and not gpu and not crosscheck"`; locally `-n auto`.
Expect local ~10 min → ~5 min and CI ~6 → ~4 min. Medium risk (a few tests may assume global state); adopt
only after a green trial run. Cheap to test.

### R8 — GPU testing ladder (the GPU-kind slowness)

GPU tests are **not** what makes per-change testing heavy: only 4 tests carry `gpu` and CI deselects them.
The heavy GPU work is the **checkpoint ladder** (CP-3/CP-5/CP-7, hours) and the night queues. Keep them out
of routine flow, but formalise two profiles in the docs:

- **`gpu_smoke` (~10 min):** one small screen (budget 2–5) + one verify top-1 on a small design (≤2k dofs).
  Required for anything touching `solve/**`, `mesh/**`, `search/evaluate.py`, `objective/**`.
- **Full checkpoint ladder (hours):** unchanged, before pins/checkpoints/nights.

This is already the de-facto practice; writing it down stops accidental full-ladder runs during ordinary
changes.

---

## 3. Expected outcome (at today's volume, same coverage)

| Change | Runs/day | CI minutes/day | Local merge-verification |
|---|---|---|---|
| Today | 122 (85 push + 37 PR) | 824 | ~30 min (3 full suites) |
| + R1 (single trigger) | ~47 | ~320 | ~30 min |
| + R2 (pip cache) | ~47 | ~280 | ~30 min |
| + R3 (docs fast lane) | ~47 | ~200 | ~30 min |
| + R4 (`slow` lane) | ~47 | ~130–150 | ~15 min |
| + R5 (CI gate) | ~47 | ~130–150 | ~10–15 min |

Net: **~5–6x less CI time and ~2–3x less local waiting, with every existing test still running**
(PR lane, nightly slow lane, GPU ladder unchanged).

---

## 4. What NOT to do

- Do **not** delete or skip tests, weaken assertions, or lower coverage to buy speed.
- Do **not** drop the full job entirely; R3/R4 only shift *when* tests run (PR docs lane, nightly slow).
- Do **not** let the docs job skip `tools/gen_param_catalog.py --check` + `tests/test_param_catalog.py` —
  docs are a generated SSOT and can break CI legitimately.
- Do **not** rely on `[skip ci]` markers — silent breakage is worse than the saved minutes.
- Do **not** gate merges on GPU tests; keep the GPU ladder for checkpoints/nights (R8).
- Do **not** remove the push rule (CONTINUITY/ISSUES per push); make it cheap with R3 instead.

---

## 5. Appendix

### 5.1 Current workflow (verbatim, `.github/workflows/ci.yml`)

```yaml
name: CI
on:
  push:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install
        run: |
          python -m pip install --upgrade pip
          python -m pip install numpy scipy cma pyyaml jinja2 pytest pytest-timeout
          python -m pip install "hornlab-plots @ git+https://github.com/m3gnus/hornlab-plots.git@9e4a6d0dd2ccb6e735dd00233dccccb50d12ed44"
          python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
          python -m pip install -e . --no-deps
      - name: Test
        run: python -m pytest -m "not slow and not gpu and not crosscheck"
```

### 5.2 Top-25 local durations (junit, 2026-11-12)

See §1.1 table; full junit at `oc-wt\A\scratch\junit_dayA_full.xml` (local, not committed).

### 5.3 Marker reference (`tests/conftest.py`)

`requires_mesher`, `requires_beat`, `requires_bempp`, `requires_build123d` (dependency gates — CI skips
them via absence), `gpu`, `slow`, `crosscheck` (deselected in CI by `-m "not slow and not gpu and not
crosscheck"`).
