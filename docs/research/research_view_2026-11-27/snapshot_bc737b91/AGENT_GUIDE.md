# Agent guide — research snapshot bc737b910572690c

Cutoff `2026-11-25T23:59:59Z` · source commit `d2273848d5af3898727c70354e0360cce0483ebb` · generator `research-snapshot-m1/3`.
460 sources, 49 exclusions, 9 findings.

## Files

- `snapshot.json` — the artifact (every other file is derived from it).
- `summary.json` — headline counts, plain summary and next steps (small; read first).
- `findings.ndjson` — one finding per line: observation / hypothesis / action / plain / next_steps / evidence / cells.
- `rows.ndjson` — one evidence row per line, `section` in {dose, cohort, reconciliation, mesh, canary, canary_replicate}.
- `manifest.json` — sources with sha256/origin, cutoff, exclusions.
- `index.html` — the human view of the same bytes.

## Invariants (must hold for any plan built on this snapshot)

1. Never compare or rank J across different cohort ids or score identities (brief_hash, objective_version, mode, backend, fidelity_policy, mesh epw).
2. A predeclared verdict (pass/fail) outranks J; select by rules first, then by J inside the passing set.
3. Every value is a cell. {v, src}: src is '<repo path>#<pointer>' where pointer is a JSON pointer (/a/b/0) for JSON; 'line:N/<field>' for ndjson (1-based line N, then the JSON field); 'line:N/col:<header>' for a markdown table cell; 'line:N/text:<phrase>' for a phrase on a markdown line; 'row:N/<column>' for CSV (1-based data row, header not counted). {v, calc, calc_version, inputs} is a deterministic calculation over the listed inputs.
4. Committed sources are read at manifest.source_commit via `git show <sha>:<path>`; runs/ sources are pinned by sha256 in manifest.sources.
5. missing / unknown / unsupported / run_dir_missing are distinct states; never treat them as zero or pass.
6. Findings are suggestions. next_steps with needs_gpu or needs_owner_approval must not be executed without the owner's explicit approval; GPU work also needs `hornlab-search gpu-clean` first (AGENTS.md).
7. Values are simulated BEM results, not physical measurements.
8. Respect the cutoff: evidence after manifest.cutoff_utc is out of scope for this snapshot; build a new snapshot instead of mixing.

## Suggested next steps (none are dispatched)

| Step | Needs GPU | Owner approval | From finding |
|---|---|---|---|
| Correct the handoff table row for r3_c500. | no | no | `claim_conflict` `b5eb8f2ec8008924` |
| Keep c400_v11_open out of metric-BO admission. | no | no | `count_not_admission` `1dac280e5348308d` |
| Keep photo_osse_morph_xo900_v11 out of metric-BO admission. | no | no | `count_not_admission` `1dac280e5348308d` |
| Recover the original box/config for home_ext_throat_v11_open so its rows re-encode exactly (3 config revisions in this cohort). | no | no | `count_not_admission` `1dac280e5348308d` |
| Show the predeclared verdict beside J wherever candidates are ranked. | no | no | `matched_pair` `960c75bf36ecd0d9` |
| Keep rear_res_factor 1.5 explicit in new formula-class configs. | no | no | `mesh_scope` `952b10fbefb9bd1c` |
| Filter candidates by the predeclared rules before ranking by J. | no | no | `scalar_not_gate` `3c624f7396c2208b` |
| Compare r3_c500's admission dependency group with its run lib_shas. | no | no | `software_drift` `b09e20a1decb46f7` |
| Compare r3_fav's admission dependency group with its run lib_shas. | no | no | `software_drift` `b09e20a1decb46f7` |
| Compare r3_v11_fold's admission dependency group with its run lib_shas. | no | no | `software_drift` `b09e20a1decb46f7` |
| Use rolled_bb_h065_th025 as the reference candidate for this body. | no | yes | `matched_pair` `960c75bf36ecd0d9` |
| Verify more screen leaders before using screen gaps as evidence. | yes | yes | `canary_rank` `91e174c0855c0e0a` |
| Time one factor-1.5 vs 1.0 solve pair on the GPU lane. | yes | yes | `mesh_scope` `952b10fbefb9bd1c` |

## Findings

### One knob, two verdicts: rolled_bb_h065 fails, rolled_bb_h065_th025 passes at +0.0032 J

- severity: `decision` · id `960c75bf36ecd0d9` · strength: 6 matched pairs; simulated verify fidelity
- scope: CD wall-angle backbone fixed-candidate verifies, one score identity per comparison; predeclared rules of that experiment only
- observation: Same family, brief, objective version and mesh; only g_bb_throat_frac differs (0.15 -> 0.25). rolled_bb_h065: J 4.6755, fails min_re_z_ok, min Re(z) 0.864. rolled_bb_h065_th025: J 4.6787, passes all six rules, min Re(z) 0.993. 6 single-knob fail/pass pairs exist in this snapshot.
- hypothesis: g_bb_throat_frac fixes the failing rule at almost no scalar cost; the scalar J barely registers the defect.
- action: Prefer rolled_bb_h065_th025 over rolled_bb_h065; record the predeclared verdict next to J in every ranking.
- evidence: `dose:rolled:rolled_bb_h065`, `dose:rolled:rolled_bb_h065_th025`

### Sample count is not admission

- severity: `decision` · id `1dac280e5348308d` · strength: frozen chronological holdout / exact replay counts
- scope: v11 screen cohorts with an admission artifact
- observation: c400_v11_open: 181 unique designs, status hold; home_ext_throat_v11_open: 180 unique designs, status replay_mismatch; photo_osse_morph_xo900_v11: 170 unique designs, status hold (row floor 150 from the handoff).
- hypothesis: These cohorts clear the row floor but fail the frozen holdout or cannot be replayed under the current config, so more rows of the same kind would not make them admissible.
- action: Do not promote by count. Repair the replay contract (replay_mismatch) or keep held (hold).
- evidence: `cohort:c400_v11_open|v11|e9a250f498df|screen|beat_cuda|d41fcf20`, `cohort:home_ext_throat_v11_open|v11|c6bc496e7b4f|screen|beat_cuda|a94ee4a4`, `cohort:photo_osse_morph_xo900_v11|v11|205eb1c8efbb|screen|beat_cuda|d41fcf20`

### Rear coarsening pays off on the tested formula classes, not on CAD

- severity: `decision` · id `952b10fbefb9bd1c` · strength: 5 acoustic cases, one design each
- scope: variable-mesh audit 2026-11-23; CPU acoustic A/B on frozen grids
- observation: 5 acoustic cases: 21.7–22.1% fewer solved DOF at factor 1.5, worst beamwidth deviation 0.155° (ATH / ridged petal (OSSE + H/V superformula)). point-grid FREEFORM (rolled rectangle): 7.3% (mesh_only); CAD / STEP MEH (T2 large multicell): 0.0% (unsupported).
- hypothesis: The saving is real where the outer shell is meshed separately; CAD is inert and the point-grid class has mesh evidence only.
- action: Keep 1.5 explicit for the tested formula classes; no universal factor; GPU timing still unmeasured.
- evidence: `mesh:class1_8k`, `mesh:class2_8k`, `mesh:class3_8k`, `mesh:class6_12k`, `mesh:class1_10k`, `mesh:class4`, `mesh:class5`

### Lowest J in rolled fails a predeclared rule; the nearest passing candidate is 0.3299 J higher

- severity: `decision` · id `3c624f7396c2208b` · strength: 11 candidates in one identity
- scope: CD wall-angle backbone fixed-candidate verifies, one score identity per comparison; predeclared rules of that experiment only
- observation: rolled_bb_h065_ri022 (g_bb_h=0.65, g_bb_throat_frac=0.15, g_bb_rollin_frac=0.22) has the lowest J 4.3488 of 11 non-control candidates in one score identity (brief 205eb1c8efbb, v11, epw 6.0) and fails min_re_z_ok. rolled_bb_h065_th025 (g_bb_h=0.65, g_bb_throat_frac=0.25, g_bb_rollin_frac=0.3) passes all six rules at J 4.6787; min Re(z) 0.835 -> 0.993.
- hypothesis: The scalar objective does not encode the loading rule; picking by J alone selects a failing design.
- action: Select by the predeclared rules first, then by J inside the passing set.
- evidence: `dose:rolled:rolled_bb_h065_ri022`, `dose:rolled:rolled_bb_h065_th025`

### Handoff status disagrees with the admission artifact

- severity: `data_quality` · id `b5eb8f2ec8008924` · strength: artifact file vs prose claim
- scope: metric-BO handoff section 3 vs runs/v11_bo_day_planning artifacts
- observation: r3_c500: handoff says needs_admission (line 136), artifact says pilot_eligible.
- hypothesis: The handoff table was not updated after the admission run; the artifact is the newer evidence. pilot_eligible means PASS_FOR_EXPLORATORY_PILOT: a held canary may be considered, not full admission.
- action: Treat the artifact as authoritative for this status and correct the handoff table.
- evidence: `cohort:r3_c500|v11|99a1d837354d|screen|beat_cuda|a94ee4a4`

### Cohorts whose runs span different software pins

- severity: `data_quality` · id `b09e20a1decb46f7` · strength: optimizer_evidence.py cross_run.compare_compatibility
- scope: admission-relevant v11 cohorts with optimizer-evidence cards
- observation: r3_v11_fold: software_drift across 6 runs (admission status confirmation_pass_for_exploratory_pilot); r3_c500: software_drift across 2 runs (admission status pilot_eligible); r3_fav: software_drift across 2 runs (admission status needs_admission).
- hypothesis: Rows were solved under different dependency/software versions, so the existing optimizer-evidence tool marks the pooled runs descriptive-only, not compatible for inference.
- action: Before using these cohorts for model training, confirm the admission artifact's dependency group covers the rows it used, or re-admit per software version.
- evidence: `cohort:r3_v11_fold|v11|c6bc496e7b4f|screen|beat_cuda|d41fcf20`, `cohort:r3_c500|v11|99a1d837354d|screen|beat_cuda|a94ee4a4`, `cohort:r3_fav|v11|c6bc496e7b4f|screen|beat_cuda|a94ee4a4`

### Negative control: repeated solves of the same designs agree

- severity: `control` · id `a0ca5d4f9b1eb61f` · strength: 7 repeats
- scope: canary rehearsal vs clean package
- observation: 7 design/fidelity pairs solved in two independent study packages; max |ΔJ| 2.71e-06.
- hypothesis: Differences far below any reported J gap are solver/process noise, not design effects.
- action: None.
- evidence: `canary:screen:1797afbe4d5f`, `canary:screen:30e9fc43aa80`, `canary:screen:4ec9ff677643`, `canary:screen:8c6334cd08b3`, `canary:screen:eacf30131429`, `canary:verify:1797afbe4d5f`, `canary:verify:30e9fc43aa80`

### Score attribution reconciles to the stored J

- severity: `info` · id `e4e613ccd1a044c4` · strength: exact to floating-point rounding
- scope: dose rows with a committed config
- observation: 24 dose rows: weighted stored terms sum to the stored total; worst |residual| 1.776e-15 (dose:lame:lame_bb_h100_m040_t25_r15).
- hypothesis: Per-term contributions are the objective's own (its weight resolvers on stored terms), not a re-score.
- action: None.
- evidence: `dose:rolled:control`, `dose:rolled:rolled_bb_h050`, `dose:rolled:rolled_bb_h100`, `dose:rolled:rolled_bb_h050_epw9`, `dose:rolled:rolled_bb_h035`, `dose:rolled:rolled_bb_h045`, `dose:rolled:rolled_bb_h065`, `dose:rolled:rolled_bb_h065_th025`, `dose:rolled:rolled_bb_h065_th030`, `dose:rolled:rolled_bb_h065_ri022`, `dose:rolled:rolled_bb_h065_ri038`, `dose:rolled:rolled_bb_h050_th025` …

### Canary: screen order survives verify (n = 2)

- severity: `info` · id `91e174c0855c0e0a` · strength: n = 2
- scope: metric-BO Fold canary package
- observation: 30e9fc43aa80: screen 5.1213, verify 4.7915; 1797afbe4d5f: screen 5.3827, verify 5.5142. Rank preserved: True.
- hypothesis: Two designs cannot calibrate screen-to-verify rank in general.
- action: No calibration claim; verify more designs before trusting screen gaps.
- evidence: `canary:30e9fc43aa80`, `canary:1797afbe4d5f`

## Known gaps

- GPU wall time and VRAM at factor 1.5 (not measured: the 12 kHz queue owned the GPU)
- physical-driver measurements: none in scope (all values are simulated BEM)
- GPU telemetry for the cohort inventory rows: not aggregated (peak_vram_mb exists per row)
- 155 missing/unknown cells (see `snapshot.json` → `missing_evidence.cells`).
