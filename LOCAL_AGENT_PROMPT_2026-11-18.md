# LOCAL AGENT PROMPT — finish the Fable plan (written by the cloud senior, 2026-11-18)

Paste everything below the line into the local orchestrator session on the Windows box.

---

ROLE: HornFab local orchestrator and single integrator (decision R21). You run CPU work, GPU jobs and
merges on the owner's Windows machine. You do not re-decide anything in
`scratch/fable_architecture/OWNER_DECISIONS_RESOLVED_2026-11-18.md` (R1-R25): the owner delegated those
to the senior pass. If a step's evidence contradicts a decision, stop that step, write what you found
into `NOTES_FOR_SENIOR.md`, and continue with the next independent step.

READ FIRST (in this order, nothing else in full):
1. `CLAUDE.md`, `AGENTS.md` (hard rules, GPU hygiene rules 1-8, two lanes).
2. `scratch/fable_architecture/OWNER_DECISIONS_RESOLVED_2026-11-18.md` (the decisions; R-numbers below).
3. `HANDBACK_CLOUD_2026-11-18.md` (§3 verdicts, §6 work list, §9 night review).
4. `scratch/fable_architecture/ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md` §10.2 (status per WP).
5. The newest 3 entries of `docs/CONTINUITY.md` and `docs/ISSUES.md` only.

RULES THAT BIND EVERY STEP:
- Interpreter `.venv\Scripts\python.exe`. GPU jobs only through `hornlab-gpu-job` (clean state, baseline +
  peak VRAM, Shared Usage near zero, one CUDA solve at a time) or the night runner (`hornlab-night-queue`).
- Single-design solves are `kind: command` + `hornlab-search run --mode screen|verify|finalist`. Never
  `kind: search` for one design (now refused by code, `681e429`).
- Compare J only inside one score identity; a gap below that identity's published floor is a TIE
  (v7 ≈ 0.13 J until B1). Label claims [measured] / [verified] / [inferred].
- Every commit cites its WP / R number and adds a CONTINUITY entry and an ISSUES entry; a new doc or
  module also gets an INDEX / CODE_MAP line. Push after each step that produced a commit.
- Never edit `hornlab_search/objective/scalar_v9.py`. Never rewrite stored rows, J, config_sha.
- Evidence docs follow `hornlab-evidence` (UTF-16 log decoding, byte-checks).

## STEP 1 — Integrate (R21). CPU, ~30 min.

1. `git fetch origin` ; `git checkout cloud/fable-next-2026-11-18` ; `git pull`.
2. Full offline suite:
   ```powershell
   $env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"
   .venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" -n 6 --dist loadscope -p no:cacheprovider
   ```
   Expected failures: exactly the known 4 (`test_v8_key_set…`, `test_b8_lanes…`, 2 × `test_night_bo_arm_wrapper`).
   Any other failure: fix it if it is in a file this branch changed (see `git diff --stat origin/hornfab-all-2026-11-18`),
   else record it and stop STEP 1.
3. Confirm the cloud-run counts locally: the suite collects 23 more tests than `hornfab-all` @ `18ec991` (cloud: 4826 vs 4803, failure set identical)
   (new files: `test_rescore_identity_v10.py`, `test_search_zero_dimensions.py`, `test_klangfilm_hv_digest_pin.py`,
   `test_replay_versions_single_source.py`, plus added tests in `test_night_runner_restart_and_stop_truth.py` and
   `test_tools_analysis_u3_authority.py`).
4. Merge on GitHub in this order, pasting the suite result into each PR: **PR #69** (cloud branch →
   `hornfab-all-2026-11-18`); **PR #67** (→ `main`); open ONE PR `hornfab-all-2026-11-18` → `main`, merge it;
   **close PR #68** with the comment "superseded: its v10 code is byte-identical on hornfab-all (verified
   file by file 2026-11-18), plus the replay gate fix ed1b2a5". Use merge commits, never force-push.
5. Add this row to `CLAUDE.md` above "Need a file you do not own?" (R21; the cloud session was not allowed to
   edit CLAUDE.md):
   > **Fable plan (owner delegation, 2026-11-18, R21):** `hornlab_search/geometry/**`, `tools/analysis/**`,
   > `tools/night_queue/fidelity_pairs.py`, `examples/protected_lanes.yaml` and `scratch/fable_architecture/**`
   > are owned by the Fable senior lane; the local orchestrator is the single integrator of `hornfab-all-*`
   > and `main` (cloud work arrives only as PRs into `hornfab-all-*`). Decisions:
   > `scratch/fable_architecture/OWNER_DECISIONS_RESOLVED_2026-11-18.md`.
6. R22: `git diff -- hornlab_search/objective/scalar_v9.py AGENTS.md .opencode` on the owner box. Discard any
   `scalar_v9.py` change (`git checkout -- hornlab_search/objective/scalar_v9.py`); commit AGENTS.md / .opencode
   only if doc-only; commit or delete `tests/test_v9_polar_window.py` and the c200w yaml after reading them
   (keep only if their tests pass and they change no v9 math).
7. From the next night boundary on, nights run from `main` (D10). Do not switch a live night.

## STEP 2 — CPU evidence that unblocks decisions. No GPU. ~2-3 h total.

2a. **v10 rescore + floors (WP 1.4/1.5).** Run every command in `docs/evidence/v10_rescore_2026-11-18/README.md`,
    then the same three for the shipped briefs and the constancy variant:
    ```powershell
    $T="tools\analysis\rescore_identity.py"; $STEM="room_landscape_80x50_700_hf1440_v7"; $O="runs\analysis\v10_rescore_2026-11-18"
    $B10S="examples\briefs\home_landscape_2026-11-18_v10\room_landscape_80x50_700_hf1440_v10.yaml"
    $B10C="examples\briefs\home_landscape_2026-11-18_v10\room_landscape_80x50_700_hf1440_v10_slope5.yaml"
    .venv\Scripts\python.exe $T rescore --brief $B10S --run-brief $STEM --runs-root runs --out "$O\v10_shipped"
    .venv\Scripts\python.exe $T rescore --brief $B10C --run-brief $STEM --runs-root runs --out "$O\v10_slope5"
    .venv\Scripts\python.exe $T floor   --brief $B10C --runs-root runs --top 28 --out "$O\floor_v10_slope5"
    .venv\Scripts\python.exe $T compare --out "$O\compare_all" v7="$O\v7" v10="$O\v10_shipped" v10_slope5="$O\v10_slope5"
    ```
    Acceptance (README): v7 parity ≈ 0, `mixed_identity: false`, floors published. The offline `v10` brief
    and the shipped one differ only by name and grid block, so their score ids differ (the id includes the
    brief name) while every J should be identical; check that J agree to 1e-12 and then use the shipped column. Commit summaries to
    `docs/evidence/v10_rescore_<date>/results/` + one-page reading: per-lane bests per identity, ties
    marked by each identity's own floor, and the throat runs' B vs A rows in the v10 column (R9 check).
2b. **Throat A-vs-v8 per-band authority (R9).** Confirm that `9fcd21fc1904` is `best.json`'s design in
    `runs\20261116T025728Z-screen-cd60f7`, then:
    ```powershell
    .venv\Scripts\python.exe tools\analysis\u3_authority.py --host runs\20261116T025728Z-screen-cd60f7\designs\9fcd21fc1904 `
      --config examples\typologies\throat_hv_2026-11-18\sweep\throat_hv_sweep_A_r15.yaml `
      --arm control=runs\20261116T025728Z-screen-cd60f7\designs\9fcd21fc1904 `
      --arm rho15=(Get-ChildItem runs\20261118T133445Z-screen-b16baf\designs -Directory)[0].FullName `
      --arm rho20=(Get-ChildItem runs\20261118T133540Z-screen-fe2089\designs -Directory)[0].FullName `
      --csv-dir docs\evidence\throat_hv_2026-11-18\authority_A_vs_v8 --out docs\evidence\throat_hv_2026-11-18\authority_A_vs_v8.json
    ```
    Same for the Phase 3 winner against B_o50 (host/control = the B_o50 run's design, arm = the design in
    `runs\20261118T150846Z-screen-9a04c5\best.json`, config `throat_hv_B_search40.yaml`). Expected: A no
    authority. Update the two "inferred / not judged" rows of plan §10.2.
2c. **Night failure causes (R15).** For each id in `docs/evidence/night_cd_rrect_2026-11-17_REVIEW_2026-11-18.md` §8:
    `Get-Content runs\nights\cd_rrect_2026-11-17\<id>.log -Encoding Unicode | Select-String 'refusing|Error|Traceback|ABORTED|training rows' | Select-Object -Last 5`.
    Append a dated "causes" section to that review. A code fault in a tool → fix it (owner file rules apply)
    with a test, cite WP 0.7. Record the t_hvlaw training-row count N.
2d. **ST260 anchor source check (R4).** Do §6 steps 1-3 of `docs/research/typologies/ANCHOR_ST260_RESEARCH_2026-11-18.md`:
    re-read R-OSSE rev7 + https://www.at-horns.eu/ST260.html; correct `examples/typologies/anchor_2026-11-18/anchor__rosse_st260_v1.yaml`
    if a value differs (a changed value = edit before any solve, note it); pick ONE admissible measured build
    (mounting modelable, distance and gating stated, polar step ≤ 10°), save its data or a digitised copy to
    `docs/evidence/anchor_st260_<date>/measured/` with the URL and conditions; run
    `.venv\Scripts\python.exe tools\shape_check.py examples\typologies\anchor_2026-11-18\anchor__rosse_st260_v1.yaml`
    and check mouth 260 ± 1 mm, throat r 12.7 mm, depth ≈ 80 mm; if the ST260 STL is downloadable, compare
    meridians (≤ 0.5 mm RMS). If the build was boxed, add `brief.mounting` as `_v2`. If no admissible
    measurement exists: R4 fallback (ATH CORE / Tritonia with published config + measured polars) and
    record it; do not solve ST260.
2e. **B1 doc fix (WP 2.2).** Append a dated line to `scratch/fable_architecture/.b1/b1_mesh_feasibility.md`
    §Recommendation: only `3a1038da45d0` and `9fcd21fc1904` are infeasible; `766c…`, `508f…`, `b996…` are
    probe-grade (batch 2, R5).
2f. **U3 host jobs (R8).** Find the best stored `hl__biradial_es_style_v7` design (lowest J in its runs under
    the v7 home brief), then
    `.venv\Scripts\python.exe tools\analysis\u3_jobs.py runs\<run> <hash> --out examples\studies\u3_biradial_es_style_v7`.
    Commit the configs (control + 7 variants) with their validity table; shape_check the control.

## STEP 3 — GPU, in this order (R6). Each batch: copy job blocks into the live/next night AFTER existing work,
keep every existing entry's order, back up the night file, `run_campaign_night.py --dry-run` must exit 0.

| # | Batch | File / how | Solves | Gate |
|---|---|---|---|---|
| 1 | B1 fold-warm x2 probes | `scratch/fable_architecture/.b1/b1_mesh_night_insert.yaml` | 5 | none (R5 approved). After probe 1: if Shared Usage > ~512 MiB → stop B1, write "not measurable on this card" |
| 2 | ST260 anchor | `docs/evidence/gpu_queue_resolved_2026-11-18/anchor_st260.yaml` | 2 | STEP 2d passed |
| 3 | B1 ext_throat_v7 x2 probes | `docs/evidence/b1_readiness_2026-11-18/b1_mesh_ext_throat_probes.yaml` | 3 | batch 1 probe 1 did not spill |
| 4 | WP 4.2 equivalence | `hornlab-search run --config examples\studies\u3_biradial_es_style_v7\<control>.yaml --mode verify` | 1-2 | STEP 2f done |
| 5 | WP 4.3 B2 variants | the 7 variant configs, `--mode verify`, one job each | 7-14 | 4.2 passes its predeclared rule (`u3_authority.py` equivalence); else STOP B2 (record route invalid) |
| 6 | BO arms `_r2` | `docs/evidence/gpu_queue_resolved_2026-11-18/bo_arms_r2.yaml` | 2 arms × ≤ 200 | after 1-5, or in an otherwise idle night |
| 7 | B6 matched reruns | write after STEP 4b | owner's B6 budget, 2-3 seeds per lane, equal valid budgets | v10 floors published |

## STEP 4 — Evidence and closing.

4a. B1 evidence (`hornlab-evidence`): per design ΔJ + per-term deltas + baseline/peak VRAM + Shared Usage;
    state that 3a1038 / 9fcd21 (and A_r15) are outside the mesh floor. Publish the combined floor
    `sqrt(freq² + mesh²)` per identity (WP 2.3) into a noise-floor record file next to the evidence.
4b. Anchor evidence: apply the predeclared pass rule unchanged; verdict pass / partial / fail. Then rescore the
    anchor's response under v7 and v10 and record which score's terms track the measurement better (this is the
    input to the nights'-score decision, R1).
4c. U3 authority: `u3_authority.py --host … --arm control=… --arm <variant>=… --floor <combined floor> --dj <ΔJ>
    --csv-dir …`; publish the authority table; WP 4.4 proposals only for passing freedoms.
4d. D6 step 2 (R10): pick the two print candidates by the R10 rule; check both against the build box; write
    the print/measure plan (measurement conditions = the anchor's admissibility rule).
4e. B6 plan: lanes = the leading constructions from STEP 2a under v10 (ties by floor), approved space_v1
    configs per R19 (apply as new `__space_v1` files now), categoricals split per R20 if any appear,
    `record_gate: shadow` on ext_throat (R20b).
4f. WP 0.9 / D9 implementation (code, one work item, R12/R12b): `record_digest` (65×61 record, float64, fixed
    byte order) written into new recipes and checked on rebuild (gates); `implementation_sha256` kept as
    information; legacy recipes classified rebuildable / bridge / unverified by a CPU tool over `runs/`;
    `mesh_meta.json` echoes the mesher `surfaceFit` mode (`hornlab_search/mesh/build.py:440-458`) and
    flags the interpolating→approximating fallback; record both the acoustic box and the build box per
    design. Tests offline; no historical row rewritten.
4g. Update plan §10.2 rows you moved, `HANDOFF_2026-11-18.md` "Next steps", and close the ISSUES entries you
    resolved.

DEFINITION OF DONE (the Fable plan is "complete through stage 4" when all are true):
- [ ] PRs merged per STEP 1; nights run `main`; CLAUDE.md row added.
- [ ] v7 / v10 / v10_slope5 rescore + floors published; throat B/A read in v10.
- [ ] B1 published (or "not measurable on this card"), combined floor record exists.
- [ ] ST260 anchor verdict published, plus the v7-vs-v10 tracking note.
- [ ] WP 4.2 verdict, and if it passed, the B2 authority table; WP 4.4 proposals or "inert".
- [ ] Night failure causes recorded; BO `_r2` arms run or explicitly deferred.
- [ ] WP 0.9 / D9 provenance package merged with tests.
- [ ] D6 step 2 print plan written; B6 queued under the owner's budget.
- [ ] HANDOFF, plan §10.2, CONTINUITY, ISSUES current; no ISSUES entry left without an owner/step.
