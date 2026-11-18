# HANDBACK (cloud senior, 2026-11-18): G1-G6 done; what the local orchestrator runs next

Branch `cloud/fable-next-2026-11-18`, based on `origin/hornfab-all-2026-11-18` @ `18ec991`.
Draft PR into `hornfab-all-2026-11-18`. Nothing merged, no GPU, no queue or night file touched,
`scalar_v9.py` untouched, no objective default changed, no historical J / row / config_sha changed.

Labels: **[verified]** re-run in the cloud · **[code-verified]** read in code · **[primary]** cited
evidence doc · **[inferred]** reasoning · **[disputed]**.

---

## 1. Bottom line

- **v10 rescore was silently broken; now one command set.** `objective/replay.py` dispatched v10
  but its version gate still refused it, so a v10 rescore would have scored zero rows [verified].
  Fixed, tested, commands written (WP 1.4 / 1.5).
- **The part3 pycma `x0=[]` crash can no longer happen.** A search with zero free dimensions is
  refused by `search()`, the CLI and the night runner's `--dry-run`, with the `run` command named
  (WP 2.2 / D7). The B1 / B1f lines were already safe (`kind: command`) [verified].
- **Throat block: A is inert, B has H authority but loses under v7.** "A_r15 beats v8 by 0.0192"
  is a tie under the 0.13 floor. Recommendation: park on A (G5).
- **Anchor pick: R-OSSE ST260.** Published geometry plus linked measured builds; Geddes OS has no
  published exact dimensions. Config + predeclared pass rule written; source re-read is local.
- **B1 packet ready**, with one finding: the feasibility doc excluded three ext-throat designs its
  own table says are buildable. And B1 cannot measure the two leaders (v7 3a1038, v8 9fcd21) on
  the 8 GB card.

---

## 2. G1 status table (summary; full table in plan §10.2)

| Stage | Done | Tool-done-not-run | Blocked on owner | Not started |
|---|---|---|---|---|
| 0 truth fixes | 0.1-0.8 (0.4 v10 gate fixed today) | | 0.9 digest rule | |
| 1 scoring | 1.1 (off), 1.2 | **1.4, 1.5** (commands ready) | 1.3 (partly answered: v7 nights + v10 second score) | |
| 2 fidelity | 2.1 | | **2.2 B1** (packet ready) | 2.3 |
| 3 record | 3.1, 3.2 | 3.3, 3.4 | module ownership | 3.5 |
| 4 freedoms | 4.1 (biradial seed) | 4.2, 4.3 | host pick, C6 | 4.4 via record route; throat block built ahead of gate |
| 5 spaces | 5.1, 5.3; 5.2 warning | | 5.2 config split | 5.4 |
| 6 search | | | | 6.1-6.3 |
| 7 campaign | 7.1 (list proposed) | | C4, C5 | 7.2-7.4 |
| D6 anchor | step 1 research | | step 1 solves | step 2 |

Placement of the 11-18 work: throat block = stage-4 freedom built ahead of its gate (owner
request); v10 = the §10.1 new-identity fix; `agent_bench` + construction contracts + KH-002/003 =
off-plan knowledge track.

**Throat authority (U3 rule, re-derived from the part3 CSVs with `u3_authority.authority()`):**

| Comparison | Max band move (intended / other) | U3 | ΔJ | vs 0.13 floor |
|---|---|---|---|---|
| A: rho 1.5 → 2.0 | H 1.28° / V 0.26° | no | +0.044 | tie |
| A: v8 → A_r15 | whole-band H 0.56°, V 0.17° (no v8 CSV) | no [inferred] | −0.019 | tie |
| B: onset 0 → 0.5 (rho 1.5) | H −8.79° / V −3.89° (2.5-5.5 kHz) | **yes, H** | −0.657 | real |
| B: B_ctl → B_o50 | H −3.99° / V +1.10° (1.1-2.5 kHz) | **yes, H** | −0.251 | real |
| B Phase 3 best vs its seed | no CSV | not judged | −0.090 | tie |
| best B vs A_r15 | | | +2.52 | B not competitive (`load` ≈ 3.2) |

**Critical path:** v10/v9/v7 rescore + floors (CPU) → B1 batch 1 → WP 2.3 floor → D6 anchor →
D6 print-and-measure → owner picks the nights' score → B6 → finalists → deliverable. Geometry path
in parallel: 4.1 host pick → 4.2 → 4.3.

---

## 3. Commits and senior verdicts

Each diff was re-read cold, its named tests re-run, its WP citation checked against the plan, and
checked for changed historical J / rows / config_sha / defaults (none).

| Commit | WP | What | Tests re-run | Verdict |
|---|---|---|---|---|
| `ed1b2a5` | 1.4 / 1.5 | replay v10 gate; rescore `--run-brief`, `--runs-root`, `compare`, parity fields; offline v9/v10 briefs + README | `test_rescore_identity_v10.py` (8), `test_tools_analysis_rescore_identity.py`, `test_obj_replay*.py`, `test_objective_v10.py`: pass | **approve** |
| `681e429` | 2.2 / D7 | zero-dim refusal in `search()`, CLI, night `--dry-run`; B1 readiness packet + optional ext-throat probe file | `test_search_zero_dimensions.py` (7), `test_tools_night_runner.py`, `test_night_admission_gate.py`, `test_search_cma*.py`, `test_search_links*.py`: pass | **approve** (note: the guard itself is a stage-0-style truth fix cited under 2.2 because B1 readiness was its trigger) |
| `c5ccb44` | D6 step 1 | ST260 anchor dossier + pinned config + pass rule | config loads + validates, 0 free dims [verified] | **approve**, with the source re-read open (at-horns.eu blocked in the cloud) |
| `8983c28` | plan §10.2 | per-WP status, authority table, critical path | numbers re-derived from CSVs; every ΔJ re-computed by hand | **approve** |
| `cd79b68` | 4.4 | G5: park the throat block on A | the A-key legality check re-run in the cloud | **approve** |
| (G6, this commit) | D10 | HANDOFF refresh + PR plan + this handback | docs only | **approve** |

Dropped: none.

---

## 4. Tests: failure sets before and after

**Cloud environment caveat.** This container has no `torch` (blocked host), no gmsh mesher stack
and no Windows paths, so its baseline is larger than the local 4. The rule applied: same set
before and after = no new failures.

- Baseline at `18ec991` (`hornfab-all` head): 4803 collected, **20 failed + 19 errors**, 308 skipped.
  - 19 errors: `test_gui_study_designs_resolver.py` (all fixtures; environment).
  - 20 failed: the known local four (`test_objective_v8::test_v8_key_set…`,
    `test_b8_lanes_bounded_gui::test_study_modules…`, 2 × `test_night_bo_arm_wrapper`) plus 16
    environment failures (`test_gui_bridge_preview` ×6, `test_geometry_record` real-generator,
    `test_study_production[current]`, `test_tools_analysis_{qd_compare, record_shadow, report_day,
    senior_plan_evidence, term_balance ×2, u3_jobs}`, `test_tools_rosse_rect_b`).
- After `681e429` (all code changes): the **same set**, no new failure. One
  `test_night_bo_arm_wrapper` test passed in that run only (order-dependent; it fails alone in both
  trees, as known).
- Final run on the G5 head `cd79b68`: see section 4a.

**Local agent: run the real suite on this branch** (expected: the known 4 only, plus 15 new passing
tests):
```powershell
$env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"
.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" -n 6 --dist loadscope -p no:cacheprovider
```

### 4a. Final run

On `cd79b68` (all code + the new example config), same command as the baseline
(`pytest -m "not slow and not gpu and not crosscheck" -n 4`):

| Run | Collected | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| baseline `18ec991` | 4803 | 20 | 19 | 308 |
| final `cd79b68` | 4818 | 20 | 19 | 308 |

Failure set: **identical** (set difference empty both ways) [verified]. **New failures: none.**
+15 tests = the 8 + 7 new tests, all passing. The G6 commit after it is docs only.

---

## 5. Owner decisions needed (numbered, most urgent first)

1. **B1 GPU slots (C6, D7).** Approve batch 1: 5 fold-warm x2 probes
   (`scratch/fable_architecture/.b1/b1_mesh_night_insert.yaml`), after the BO arms. Optional:
   batch 2, 3 ext_throat_v7 probes (`docs/evidence/b1_readiness_2026-11-18/b1_mesh_ext_throat_probes.yaml`);
   B1f frequency check (`.b1/b1_night_insert.yaml`). Accept that B1 cannot cover the v7 leader
   and the v8 incumbent on this card.
2. **PR plan (D10).** #67 → main; cloud draft → `hornfab-all`; one PR `hornfab-all` → main; close
   #68 (byte-identical code, verified file by file). Nights move to `main` at a night boundary.
3. **D6 step 1 anchor.** Accept R-OSSE ST260 and the predeclared pass rule (beamwidth ±5°,
   ±3° in 2-5 kHz; DI ±1 dB; 1-8 kHz). 1-2 solves after the local source check.
4. **Throat block (G5).** Accept "park on A, inert in this envelope"; B recorded as "H authority,
   not competitive under v7".
5. **b06a938** (Klangfilm H/V comment fix that changes family digests): land or revert before the
   `hornfab-all` → main PR.
6. **v10 rip tolerance / weight.** The offline brief uses the v9 values; changing them later is a new
   identity. Decide before any v10 number is used for a ranking.
7. Carried over, unchanged: C4 (winner vs menu), C5 (protected list), WP 0.9 provenance rule,
   envelope convention, WP 4.1 host pick, uncommitted `scalar_v9.py` / `AGENTS.md` / `.opencode`
   edits, Le Cléac'h YAML "published" wording, Crowe-X `g_L_mm` 285 vs 320.

---

## 6. Local orchestrator work list (in order; CPU unless marked GPU)

Every item: one commit, CONTINUITY + ISSUES entry, INDEX/CODE_MAP line if a doc/module is new,
WP number in the message.

**A. Verify this branch (first, 10 min).**
1. `git fetch origin cloud/fable-next-2026-11-18 && git checkout cloud/fable-next-2026-11-18`
2. Full offline suite (command in section 4). Expected failures: the known 4 only. If anything new
   fails, stop and record it in `NOTES_FOR_SENIOR.md`.
3. Quick check of the guard on the real tree:
   `.venv\Scripts\python.exe tools\run_campaign_night.py --night runs\nights\cd_rrect_2026-11-17.yaml --dry-run`
   must still exit 0 for the live night (if it now names a ZERO-DIM job, that job would have
   crashed anyway: move it to `kind: command` + `run`).

**B. WP 1.4 / 1.5 rescore (CPU, ~minutes to an hour).** Exact commands:
`docs/evidence/v10_rescore_2026-11-18/README.md` §"Exact local commands" (three `rescore`, one
`compare`, two `floor`). Acceptance checks are in that README (v7 parity ≈ 0, no
`mixed_identity`, floor before ranks). Commit the summaries under
`docs/evidence/v10_rescore_<date>/results/`. Cite WP 1.4 / 1.5. Also read the throat runs' rows
in the v10 column (G5 follow-up).

**C. Throat A-vs-v8 per-band authority (CPU, 1 min).** Command in plan §10.2 (`u3_authority.py`
with `--host`/`control` = `runs\20261116T025728Z-screen-cd60f7\designs\9fcd21fc1904`; first
confirm that hash equals that run's `best.json` design). Save to
`docs/evidence/throat_hv_2026-11-18/authority_A_vs_v8.json`. Expected: `authority: false` for
both arms. Optionally add the Phase 3 winner as an arm against `B_o50` (run
`20261118T150846Z-screen-9a04c5`, design from its `best.json`) to fill the "not judged" row.
Cite WP 4.3 rule / 4.4.

**D. ST260 anchor source check (CPU + browser, before any GPU).** Steps 1-3 of
`docs/research/typologies/ANCHOR_ST260_RESEARCH_2026-11-18.md` §6: re-read rev7 + the ST260
page, fix the config if needed, pick an admissible measured build, save it, then
`.venv\Scripts\python.exe tools\shape_check.py examples\typologies\anchor_2026-11-18\anchor__rosse_st260_v1.yaml`
and the mouth 260 mm / throat 12.7 mm checks. Cite D6 step 1. Then ask the owner for the 1-2
solves (GPU, owner-gated): `.venv\Scripts\hornlab-search.exe run --config examples\typologies\anchor_2026-11-18\anchor__rosse_st260_v1.yaml --mode screen`
then `--mode verify`, via `hornlab-gpu-job` hygiene.

**E. B1 insertion (only after owner decision 1; GPU via the night).** Use `hornlab-night-queue`:
copy the approved job blocks after the last BO arm, keep every existing entry's order, back up
the night file, `--dry-run` must exit 0. Batch 2 only if the first fold-warm probe did not spill.
Then write the B1 evidence with `hornlab-evidence` (baseline + peak VRAM + Shared Usage per
design; state that 3a1038 / 9fcd21 are outside the floor).

**F. Small doc fix (CPU, 5 min).** In `scratch/fable_architecture/.b1/b1_mesh_feasibility.md`
§Recommendation, change "The five ext-throat designs are excluded" to name only `3a1038da45d0`
and `9fcd21fc1904` as infeasible and point to the optional probe file. Append-only note style
(dated line) if you prefer not to edit the original paragraph. Cite WP 2.2.

**G. Carried from the 11-18 handoff (owner-approved GPU).** Resume `t_ath14_scalar100` and
`t_corelaw_turbo100` with a FRESH `--root` (their `package.json` makes the stock resume refuse).
Unchanged from `HANDOFF_2026-11-18.md`.

**I. Night record causes (CPU, 15 min).** Review §8 of `docs/evidence/night_cd_rrect_2026-11-17_REVIEW_2026-11-18.md`.

**H. After the owner approves the PR plan.** Mark #68 closed-as-superseded (owner action or with
explicit approval), retarget nothing else; after #67 merges, open `hornfab-all-2026-11-18` → `main`
with the full suite pasted.

---

## 7. Queue lines (all PROPOSED, none inserted)

| Batch | File | Jobs | `--dry-run` in the cloud |
|---|---|---|---|
| B1 fold-warm x2 | `scratch/fable_architecture/.b1/b1_mesh_night_insert.yaml` | 5 | exit 0 [verified] |
| B1 ext_throat_v7 x2 (optional) | `docs/evidence/b1_readiness_2026-11-18/b1_mesh_ext_throat_probes.yaml` | 3 | exit 0 [verified] |
| B1f (optional, not mesh) | `scratch/fable_architecture/.b1/b1_night_insert.yaml` | 1 | exit 0 [verified] |
| ST260 anchor (after D) | `kind: command`, argv `.venv/Scripts/hornlab-search.exe run --config examples/typologies/anchor_2026-11-18/anchor__rosse_st260_v1.yaml --mode screen` | 1 (+1 verify) | not a night job yet |

Single-design rule, now enforced in code: **never `kind: search` for one design**; use
`kind: command` + `hornlab-search run --mode screen|finalist`.

---

## 8. Proposed off-plan (no WP number; not done)

1. Derive the replay version gate from `_dispatch` (one list, not two) so the next objective
   version cannot repeat the v10 gate bug. Small; would fit WP 0.4 if the owner wants it there.
2. A tiny export tool that writes `hv_beamwidth_<cfg>.csv` from any run's best design (the
   part3 CSVs were hand-made), so authority tables never depend on whoever ran the sweep.
   Extend `u3_authority.py` with `--csv-out` rather than writing a new tool.
3. The agent benchmark A/B run (`tests/agent_bench/`, ISSUES 11-18) stays off-plan.

---

## 9. Addendum: review of the pushed night record (`2b35194`)

Full review: `docs/evidence/night_cd_rrect_2026-11-17_REVIEW_2026-11-18.md`. The push contained
the night's ledger and logs, not CSVs. Short version:

- **Throat rows match the evidence exactly** [verified]; the §10.2 authority table stands.
- **GPU hours:** 14.7 h ok, 3.5 h failed, 2.1 h blocked (≈ 50 min of it a stale-lock episode on 11-17).
- **BO arms: 0 of 9 finished.** Two were owner skips; `t_hvlaw` ×2 were refused by design (too few
  training rows: build a CMA cohort first) [code-verified]; `t_ath14_turbo100` refused at launch;
  `t_klame` ×2 failed. The handoff's "two skipped" undercounts this.
- **`t_trit80_rc2` is recorded `ok` after 2 h with 0 evals and no J**: a night-truth gap (WP 0.7);
  proposal: an `ok_no_result` status for new rows.
- **Pending queue is clean under the new zero-dimension guard**; no live-night edit is needed.
  Three `w_lecleach_*` jobs run `beat_cpu` inside the GPU lane (legal, slow; maybe meant for the CPU lane).
- **Local action (new item I in §6):** pull the cause lines from the nine job logs listed in the
  review §8 (UTF-16; `-Encoding Unicode`), append them to the review, then decide BO re-queues.

Owner decision added: **8. BO arms** — re-queue only after the causes are read; `t_hvlaw` needs a
CMA cohort before BoTorch (owner rule 2026-11-15).
