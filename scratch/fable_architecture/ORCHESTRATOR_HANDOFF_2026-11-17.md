# ORCHESTRATOR HANDOFF (2026-11-17) - continue the senior plan locally

> **Who this is for:** the lower-cost orchestrator agent working on the owner's Windows checkout
> (`C:\Users\hunte\Hrns\hornlab-search`), with `runs/`, the GPU and `.venv`. **Written by** the
> senior (high-thinking) pass. **Authority:** `FABLE_SENIOR_REVIEW_2026-11-17.md` (decisions) and
> `ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md` (plan; §10 = status) govern; this file tells you
> what to do next and how. Branch `ccr-260b4b76-fi6b8j`, PR #67.

---

## 0. Ten rules (read twice)

1. **Never apply a recommendation automatically.** Cards, proposals and shadow reports are
   evidence; the owner approves every change to a config, brief, bound, envelope or queue (ADR D6).
2. **Never edit an original config.** Proposals are new files (`__space_v1.yaml`); the original stays.
3. **Never rank J across score identities**; a rank gap below the published floor is a tie.
4. **No family-name classification** in any scorer or gate (owner lock).
5. **Historical J, rows, `config_sha`, identities are immutable.** New behaviour = opt-in keys.
6. **GPU:** `hornlab-gpu-job` skill for every solve (clean hosts, baseline VRAM, one CUDA solve at
   a time, verified shutdown). **No solve without owner approval of the item (C6).**
7. **Every push** updates `docs/CONTINUITY.md` (new dated entry at top) and `docs/ISSUES.md`; a
   new module or doc gets a line in `docs/CODE_MAP.md` / `docs/INDEX.md`.
8. **Tests:** run the offline tests named in each task with `.venv\Scripts\python.exe -m pytest`;
   paste real output; never loosen a pass line set by a brief, never skip a failing test.
9. **Protected lanes** (`examples/protected_lanes.yaml`, status `proposed`) are never cut by you or
   by automation.
10. **When unsure, stop and write it in `NOTES_FOR_SENIOR.md`** (append only). A pass line that fails
    is a result, not a problem to tune away.

---

## 1. What already exists (do not rebuild)

| Area | Code | Use it via |
|---|---|---|
| Canonical record v2 | `hornlab_search/geometry/record.py` | `record_for_design(design, cfg)` |
| Record edits (U3) | `hornlab_search/geometry/edits.py` | `u3_variants(rec)`, `validity`, `record_to_grid` |
| Explicit record body | `hornlab_search/design/generators/record_body.py` | config seed `{"grid": spec_from_record(...)}` |
| **Parameter-space evidence** | `hornlab_search/geometry/sensitivity.py` | `analyze_space`, `box_feasibility`, `sigma_refusal_curve`, `margin_model` |
| **Shared-descriptor translation** | `hornlab_search/geometry/translate.py` | `match_descriptors(space, cfg, target)` |
| v9 constancy / dense grid | `objective/scalar_v9.py`, `metrics/dense_grid.py` | `objective.constancy`, `objective.score_grid` (opt-in) |
| Parity replay with v9 | `objective/replay.py` | `replay_run_dir(run, hash, brief=...)` |
| Tools | `tools/analysis/` | `space_card.py`, `space_propose.py`, `record_shadow.py`, `rescore_identity.py`, `u3_jobs.py`, `u3_authority.py`, `senior_plan_evidence.py` |
| Night runner | `tools/run_campaign_night.py` | restart idempotency, watchdog truth, protected lanes |
| Finalist tier | `config.py` | `mesh_spec("finalist", cfg)` (CLI wiring open) |

---

## 2. First session: verify on the real machine (no GPU, ~1-2 h CPU)

```powershell
cd C:\Users\hunte\Hrns\hornlab-search
git fetch origin ccr-260b4b76-fi6b8j; git checkout ccr-260b4b76-fi6b8j
.venv\Scripts\python.exe -m pytest -q tests\test_geometry_record.py tests\test_geometry_edits.py `
  tests\test_geometry_sensitivity.py tests\test_geometry_translate.py tests\test_objective_v9.py `
  tests\test_metrics_dense_grid.py tests\test_obj_replay_v9_parity.py tests\test_search_refusal_taxonomy.py `
  tests\test_search_links.py tests\test_config.py tests\test_config_fidelity_tiers.py `
  tests\test_bo_cohort_gate.py tests\test_night_runner_restart_and_stop_truth.py `
  tests\test_tools_analysis_record_shadow.py tests\test_tools_analysis_rescore_identity.py `
  tests\test_tools_analysis_u3_jobs.py tests\test_tools_analysis_u3_authority.py `
  tests\test_tools_analysis_senior_plan_evidence.py tests\test_design_recipe_meta.py
```
Expected: all pass (Linux container: 0 failures in these files). Known pre-existing failures
elsewhere, NOT caused by this branch (fail at `1d6ebc8` too):
`test_mesh_build_grid.py::test_grid_self_approach_classifies_invalid_geometry_and_is_memoized`,
two `test_gui_preview_shape.py` tests. Then run the full offline suite once and record the count.

Then the data-dependent evidence in one command (writes `scratch\fable_architecture\.evidence\<utc>\`):
```powershell
.venv\Scripts\python.exe tools\analysis\senior_plan_evidence.py --runs-glob "runs\2026111*" `
  --u3-lane hl__biradial_es_style_v7 --u3-lane hl__ext_throat_hvlaw_v7
```
Report: record-shadow counts (`record_inside_but_refused` / `record_outside_but_ok` /
`record_failed`), and U3 CPU validity on the best stored designs. Commit the SUMMARY.json and a
short evidence note (use the `hornlab-evidence` skill).

---

## 3. Parameter spaces (stage 5) - the main line of work

The senior pass built the instruments; your job is to run them on every active lane, turn the
evidence into owner-reviewable proposals, and wire the two missing pieces.

### 3.1 Cards for every active lane (CPU)

```powershell
.venv\Scripts\python.exe tools\analysis\space_card.py `
  --config <lane1.yaml> --config <lane2.yaml> ... `
  --run runs\<that lane's latest run>   # optional: adds walls/links data evidence
  --out scratch\fable_architecture\space_cards --points 8 --box 96 --sigma-n 48
```
- Lanes: every config in the current night YAMLs plus every protected lane. One `--run` applies
  to all configs in a call, so run per lane when you add `--run`.
- A config that fails to load is a finding (two legacy ones already fail: see ISSUES) - list it.
- Done when: one `.json` + `.md` per lane and `shared_map.md`; committed.

**How to read a card** (labels from `geometry/sensitivity.py`):

| Label / item | Meaning | Typical action (owner approves) |
|---|---|---|
| `inactive` | moves no surface point anywhere sampled | fix at seed |
| `weak` | whole range moves no point > 1 mm (mesher fit) | fix, or widen if the owner wants that freedom |
| `conditional` | active only at some points | split the lane by the condition or link it |
| `link` | surface direction parallel to another knob (weaker follows) | link, **only if** data links (`links.py`) or a 2-run A/B agree |
| `rebound` | edge slice mostly refused/outside | move that bound in |
| `sigma0` | largest sigma0 with predicted bad rate <= 15 % | cap sigma0 |
| `constraint` | envelope binds jointly (linear margin model) | see 3.3 |
| effective dimension << searched | CMA spends dimensions on redundancy | links / fixes |

### 3.2 Proposals and their review (CPU)

```powershell
.venv\Scripts\python.exe tools\analysis\space_propose.py --card scratch\fable_architecture\space_cards\<stem>.json `
  --out scratch\fable_architecture\space_cards\proposals [--fix-weak]
```
For each proposal, check in the report: `searched` before -> after, box and sigma before -> after,
and **`seed_shift_max_mm`**. If the seed moved by more than ~1 mm, the link offsets changed the
incumbent: either re-fit the offset so the seed is preserved, or tell the owner the seed changes.
Then `hornlab-shape-check` (meshes, dof cap, envelope) and `hornlab-search-economy` (is there room
to improve). Present each proposal to the owner as a table: change, evidence, risk. **Only after
approval** copy it into `examples/` under a new versioned name (never overwrite the original).

### 3.3 Missing piece A: constraint-aware candidate filtering (code, medium-hard)

The margin model (`sensitivity.margin_model`) shows the ext-throat envelope is one joint linear
constraint (R^2 0.89). Today CMA proposes, the pre-mesh estimate refuses, and in
`budget_counts: new` mode the refusal costs budget. Implement an **opt-in**
`search.record_gate: shadow | resample` (default absent = unchanged):
- `shadow`: compute record margins for each candidate (CPU, ~0.03-0.2 s) and log
  `record_margin_mm` + agree/disagree with the actual outcome into the ndjson row (new key only).
- `resample`: if the record is outside the envelope by > tol, draw a replacement candidate the way
  `resample_strict` already does (`tests/test_search_resample.py` shows the mechanism) instead of
  spending a refusal.
- Files: `search/evaluate.py` or the CMA loop in `search/cma.py` (read both; the resample path is
  the natural hook). Tests: default identical rows; shadow adds only new keys; resample never
  submits an outside candidate. Switch any lane to `resample` only after the shadow report (WP 3.3)
  shows zero `record_inside_but_refused` disagreements in its family.

### 3.4 Missing piece B: geometric links agreement gate (code, easy)

`space_card.py` already loads `walls`/`links` data when `--run` is given. Add to `recommend()` a
field `data_agrees: true|false|unknown` per link (true when `links.py` proposes the same pair with
the same sign of scale) and only emit `action: link` when not `false`. Test with a synthetic run
dir (see `tests/test_tools_analysis_record_shadow.py` for how to build one).

### 3.5 Missing piece C: categoricals (config work, needs owner)

`config.py` warns on searched categorical keys. The flagged shipped configs: `ath_core.yaml` and
four `examples/studies/rear_density_2026-11-13/ath_like_rear*.yaml` (`morph_target`). Propose one
config per category to the owner; do not edit the originals.

### 3.6 Cross-family seeding (CPU, owner-visible)

`geometry/translate.match_descriptors(space_B, cfg_B, descriptors_of_design(best_A, cfg_A))` gives
family B a seed matching A's mouth size, depth and wall angles. Use it to (a) seed a protected lane
that lacks a good start, (b) build matched-size comparisons for B6. Always report the residual; a
large residual means B's box cannot reach that geometry (a finding, e.g. fold-warm is 70 mm short
of the biradial seed's depth).

---

## 4. The rest of the plan, in order

| # | Task | Blocked by | How / acceptance |
|---|---|---|---|
| 1 | Commit the four missing reports A4, A5, A9, X1 addendum (+ `.a4/`, `.a9/`) from the Windows tree | nothing | `git add -f`; CONTINUITY/ISSUES |
| 2 | Stage 0 leftovers: reclassification report for 0.1 on real runs; watchdog `pin_*` exposed or documented; legacy-config load failures listed | nothing | evidence doc |
| 3 | WP 2.1 wiring: `--mode finalist` in `cli.py`, `SEARCH_MODES` in `gui/jobs.py`, evaluate/runner dispatch (`search/evaluate.py:~1277` is verify-only) | nothing | screen/verify/final byte-identical tests; finalist uses `mesh_spec("finalist")` |
| 4 | Frequency grids: the plan says screen 18 / verify 29; reality is 12 / 25 unless the brief sets `screen_extra_hz` / `verify_points_per_octave` | owner | record the actual counts in every floor/B1 report; ask owner whether the new home brief sets them |
| 5 | WP 1.3 home v9 brief(s) | owner C1-C3 | new file in `examples/briefs/home_landscape_2026-11-15/`; `objective.score_grid` 58 (116 with constancy); G13 GUI test passes |
| 6 | WP 1.4/1.5 rescore + floor under the new brief | 5 | `rescore_identity.py rescore/floor`; expected frequency floor ~0.11 J (v9) / ~0.2 J (v9 + constancy) at the top |
| 7 | WP 2.2 B1 (20 solves) | owner C6 | top 10 = union of v7 and v9 top fives; screen cap vs 2x cap; >= 29 freqs |
| 8 | WP 2.3 combined floor | 6, 7 | `sqrt(freq^2 + mesh^2)`; report marks ties |
| 9 | WP 3.3 shadow over all runs, then the switch decision | 2 | `record_shadow.py`; owner decides |
| 10 | WP 4.2 equivalence (2 solves), then 4.3 B2 (12-16) | owner C6 + host pick | `u3_jobs.py` -> solve -> `u3_authority.py`; STOP if equivalence fails |
| 11 | WP 4.4 build passing freedoms inside the hosting specialist | 10 | `hornlab-typology-research` first; new config version |
| 12 | WP 6.1 BoTorch on rescored history: extend `tools/analysis/offline_scores.py` beyond ATH/v4 via `replay_run_dir` | 5 | cohort gate by identity (done) accepts the rows |
| 13 | WP 6.2 B6 matched reruns | owner budget | equal valid-row budgets, 2-3 seeds, ties by floor |
| 14 | WP 7.2-7.4 advisory watchdog, lane ordering, deliverable (C4) | 8, owner C4 | advisory only |

---

## 5. Owner decisions you must ask for (do not decide)

C1 coverage target, C2 constancy, C3 dead bands + ripple window, C4 winner vs menu, C5 protected
list (incl. the 4 no-evidence lanes and whether refusal storms in protected lanes may still stop),
C6 solve budget, provenance rule, envelope convention (acoustic vs build box: the 480 mm vertical
variant fits one and not the other), the U3 host, and every config proposal from §3.2.

---

## 6. Findings to keep in mind

- ext-throat: 58 % of its box is outside the envelope; predicted bad rate 6 % at sigma0 0.10 vs
  34 % at 0.15+; one linear constraint explains it (width binds 65 %).
- fold-warm: 18 searched, ~12 effective; `a0_deg` weak (0.39 mm); OSSE `n` ~ `s`, `k` ~ `a_deg`.
- Crowe X OSSE CD: top 20 % of `g_L_mm` and `g_s` mostly refused.
- Klangfilm b3_soft: top 20 % of `g_theta_h1_deg` refused; several beak/lame knobs move < 3 mm.
- Biradial seed: all 8 knobs active, no coupling, box fully feasible.
- GRID extent: fixed per plane (3/3 -> 1/64 false refusals).
- Two legacy configs fail to load at HEAD (`hl__klangfilm_lame_curved_v1.yaml`,
  `hl__rolled_es_spiral_v7.yaml`: unknown rows type).

## 7. First proposals already generated (review with the owner; none applied)

`scratch/fable_architecture/space_cards/proposals/` (box counts use 64 points before, 32 after;
compare rates):

| Lane | Searched | Bad share of box | Predicted bad rate at sigma0 0.15 | Seed shift | Changes |
|---|---|---|---|---|---|
| Crowe X OSSE CD | 9 -> 8 | 23 % -> 6 % | 44 % -> 21 % | ~1e-6 mm | link `g_wrap_deg` to `g_r_lip_mm`; `g_L_mm.hi` 285 -> 268; `g_s.hi` 0.45 -> 0.40; sigma0 still needs review |
| ext-throat H/V law | 8 -> 8 | 58 % -> 56 % | 34 % -> 12.5 % | 0 | sigma0 0.20 -> 0.10; the joint envelope constraint needs §3.3 |
| OSSE rrect fold-warm | 18 -> 15 | 0 % -> 0 % | 0 % -> 0 % | 0 | fix `a0_deg`; link `n` to `s`, `k` to `a_deg` (confirm with data links first) |
| Klangfilm b3_soft | 12 -> 12 | 16 % -> 12.5 % | 6 % -> 0 % | 0 | `g_theta_h1_deg.hi` 60 -> 55.3 |

Geometric links are surface redundancy, not proof of acoustic redundancy: before an owner adopts a
link, run `tools/analysis/links.py --run <latest run>` (data agreement) or a short A/B.
