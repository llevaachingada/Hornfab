# Pass B: cloud integration onto the contracts (5 parallel lanes)

**Depends on:** Pass A merged into the working branch. **B2 additionally needs Pass 0 step 0.1**
(GUI trio committed). If the fixture pack (Pass 0 step 0.3) has landed, every lane adds one test
against `tests/system/fixtures/case_store/`; if not, synthetic stores only and say so in the report.

## Shared rules

Same as Pass A (contracts, ownership, offline tests, lane reports at
`docs/system_v1/lane_reports/B-<lane>.md`, no shared-doc edits, no commits by lanes).
Regression command: `python3 -m pytest -q tests/system tests/test_tools_data_system_cases.py tests/test_gui*.py`.
The integrator records the Pass-A-merged baseline before launching lanes.

---

## B1 - Export delegates to `read_case`

**Owns:** `tools/data/system_cases.py`, `tests/test_tools_data_system_cases.py`, `docs/system_data/README.md`.
**Steps:** replace the tool's own discovery/status/metadata/integrity code with `iter_cases` +
`SystemCase.to_dict()` mapped onto the existing 53 columns (column names and order unchanged).
Keep the CLI flags and the screens export as is. N1 is fixed by `paths.leaf_dir_name`.
**Done when:** all 16 export tests pass on Linux; a golden test asserts the CSV header is unchanged;
README notes "rows come from `hornlab_search.system.read_case`". Do **not** regenerate
`docs/system_data/*.json|csv` in the cloud (no store); the local orchestrator regenerates.

## B2 - GUI readers on the read model (needs Pass 0.1)

**Owns:** `hornlab_search/gui/data_hw.py`, `data_hw_compare.py`, `data_hw_screen.py`,
`data_hw_new.py`, `data_hw_stage.py`; `tests/system/test_gui_hw*.py`.
**Steps:**
1. Case list and case detail come from `iter_cases` / `read_case`; add `CaseReadModel` (contract §8)
   under each existing payload. Keep URLs and existing keys.
2. Remove writer-specific payload branches that `read_case` now covers; keep anything it does not
   (polars, mesh endpoints) and list those in the report.
3. F19: guard the `meshio` import; mesh endpoints return a refusal token `MESHIO_UNAVAILABLE`
   instead of a 500 when it is missing.
4. F20: job preview text comes from `system.jobs.preview(build_job(...))`.
**Done when:** existing GUI hw tests pass unchanged plus new read-model tests.

## B3 - Funnel command (WP6, dry-run first)

**Owns:** `hornlab_search/system/funnel.py`, the `funnel` subcommand in
`hornlab_search/system/cli.py`; `tests/system/test_funnel.py`.
**Read:** contract §7; handbook §4.3-§4.5, §7.4 step 9; `woofer_seed.run_seed_screen`.
**Steps:** `plan_funnel` reads a spec, calls nothing heavy, emits `JobSpec`s for screen -> top-N
stage -> validate -> solve -> dsp, each with `inputs_sha256`. `run_funnel(execute=False)` writes the
plan ledger JSON (deterministic). `execute=True` runs CPU screen jobs via `subprocess` with the
JobSpec argv and stops at the first BL step unless `--allow-bl` is passed (local only); solve rows
need an `AuthorizationRecord` else `refused/AUTH_MISSING`. Tests: plan determinism (byte-identical
twice), refusal without auth, ledger schema, `execute=True` with BL steps mocked.

## B4 - Store relocation (D6), dry-run first

**Owns:** `hornlab_search/system/store_migrate.py`, `migrate-store` subcommand in
`hornlab_search/system/cli.py` (coordinate: B3 adds `funnel`, B4 adds `migrate-store`; each lane
adds its own `add_parser` block only, in separate functions, and the integrator resolves the merge);
`tests/system/test_store_migrate.py`.
**Behaviour:** `--dry-run` (default) lists every absolute path found in every manifest/JSON under the
store and its store-relative rewrite (via `paths.to_store_relative`); unmatched paths are reported,
never guessed. `--apply --backup-dir DIR` copies each file to the backup first, rewrites to a new
temp file, keeps the absolute value in `original_abs_path`, **re-seals** the manifest hash through
`provenance.write_manifest` semantics, and writes `MIGRATION_LEDGER.json`. Refuse to run on a store
whose path contains `runs/` (horn runs are out of scope). Tests on a synthetic store with Windows
paths: dry-run report, apply + backup, re-sealed hashes verify, idempotence (second run = no-op).
**Never run `--apply` on the real store in this pass.**

## B5 - DSP preview read model (P7 backend)

**Owns:** `hornlab_search/gui/data_hw_dsp.py`, its route registration in `hornlab_search/gui/server.py`
(one dispatch entry only); `tests/system/test_gui_hw_dsp.py`.
**Behaviour:** `POST /api/hw/dsp-preview` with `{case_key, xo_hz, order, polarity, delay_s,
calibration_id|null}` returns per-channel filtered curves always (Python `dsp.filter_bank`), and
`sum` only when a calibration record with that id exists under
`docs/research/system_woofer_2026-11-18/calibration/` and passes `apply_calibration`; otherwise
`sum: null, refusal: "CAL_REQUIRED"` (or the record's own token). Validate inputs with
`validate_dsp_point`. Observation label from `observation.label_for`. Tests use the committed
`tests/system/fixtures/bl_results/reference_run` and a synthetic record in `tmp_path`.

---

## Integrator checklist (Pass B)

- [ ] `cli.py` merge of B3 + B4 subcommands; run `python3 -m hornlab_search.system.cli --help`.
- [ ] Regression command no worse than baseline; paste counters.
- [ ] One commit + shared docs; draft PR into `hornfab-all-*`.
- [ ] Tell the local orchestrator: regenerate `docs/system_data/` with the new export and diff it
      against the previous commit (expected change: `horn_mesh` column only, N1).

## Paste-ready lane brief (fill LANE)

```
You are lane <LANE> of HornFab System v1 Pass B (cloud, offline). Pass A is merged. Read
docs/system_v1/README.md sections 1, 2 and 4, docs/system_v1/01_CONTRACTS.md, and only the
"<LANE>" section plus "Shared rules" of docs/system_v1/PASS_B_CLOUD.md. Edit only your lane's
paths. Run your tests and the pass regression command with python3 -m pytest -q. Do not commit,
push, or edit CONTINUITY, ISSUES, INDEX or CODE_MAP. Write docs/system_v1/lane_reports/B-<LANE>.md
with files changed, exact test commands and counters, and requests for other lanes. Stop and report
on any contract misfit.
```
