# SOURCE INDEX — exact paths, SHAs, hashes, timestamps

**Snapshot of record for this dossier:** local `main` at
`601be8ceeb48f1750bb4f3f6c1fdc682967c8b94` (`601be8c`), observed
**2026-11-16T20:43:51-05:00**. Working tree dirty (19 modified, 16 untracked = 35 entries),
because a concurrent lane was actively developing CROWE/KlangFilm geometry, the GUI and an
objective-v9 profile. Nothing in this list was modified by the research pass — the only writes
are the `.md` files in `scratch/fable_architecture/`.

## 1. Git provenance

| Fact | Value |
|---|---|
| Repo root | `C:\Users\hunte\Hrns\hornlab-search` (canonical checkout per `AGENTS.md` owner amendment 2026-11-12) |
| Remote | `https://github.com/llevaachingada/Hornfab.git` |
| Branch | `main` |
| Local HEAD at assembly | `601be8ceeb48f1750bb4f3f6c1fdc682967c8b94` |
| `origin/main` | `2c0e2928e932a47975fc284401eafa74ebfc5002` (the v3 handoff's referenced main) |
| Local main vs origin/main | **11 commits ahead** — local work has advanced past the handoff snapshot |
| Commits added after `2c0e2928` | `601be8c` 20:34, `b2a4210` 20:33, `9b8c5da` 20:32, `5cc83af` 20:19, `13b4763` 20:04, `667ffc8` 20:03, `50f3d8c` 19:55, `d187c06` 19:42, `3efe9be` 19:20, `ded9e62` 19:20, `659da48` 19:20 (all 2026-11-16 local) |
| HEAD movement during the research pass | `2c0e2928` → `3efe9be` → `d187c06` → `50f3d8c` → `13b4763` → `5cc83af` → `601be8c` |
| Traced-file stability | `git diff --stat d187c06..601be8c -- hornlab_search/{search,bo,targets,objective}/ hornlab_search/design/{space.py,families.py,generators/registry.py} tools/run_campaign_night.py tools/analysis/` = **empty**. All line citations in the lane reports were re-verified at `d187c06` and are byte-identical at `601be8c` |
| Working tree at assembly | 19 `M` + 16 `??`; none created by this pass. `hornlab_search/config.py`, `hornlab_search/objective/versions.py`, `hornlab_search/bo/diagnostics.py` are among the modified files (concurrent lane) |
| Live jobs | A `julia` host (PID 37208, started 20:07) and a night queue were present; observed read-only, never signalled, locked or killed |
| Ignore proof | `git check-ignore -v scratch/fable_architecture/INDEX.md` → `.gitignore:9:/scratch/` |
| Drift after assembly | At `2026-11-16T20:46:32-05:00`, HEAD advanced to `0750a3053875e9060e92af1a2b44f21a4efdc110` (one CROWE V2A timing-law commit; local main now 12 commits ahead of `origin/main`, 32 working-tree entries). `git diff --stat 601be8c..0750a30` over every cited path is **empty**, so all citations remain valid. |

**Citation rule used below.** `path:line` refers to `601be8c` committed content unless marked
`worktree`. Where a cited file is uncommitted, that is stated explicitly. Line numbers are
evidence timestamps, not a permanent API.

## 2. Source files read (hash = first 16 hex of SHA-256 of the file at snapshot)

| # | Path | Lines | SHA-256[0:16] | State |
|---|---|---:|---|---|
| 1 | `hornlab_search/design/space.py` | 147 | `6fd0c35c95edfb81` | clean |
| 2 | `hornlab_search/design/generated.py` | 265 | `a2908df722ab69b3` | clean at `601be8c`; contains the crowe dispatch now |
| 3 | `hornlab_search/design/families.py` | 649 | `2fb62dc9f730113f` | clean |
| 4 | `hornlab_search/design/generators/registry.py` | 430 | `1aaf5149296007dc` | clean |
| 5 | `hornlab_search/design/generators/grid.py` | 3020 | `b3351c57f771109b` | clean; `envelope_extents` at L2989, conservative rule at L3018–3020 |
| 6 | `hornlab_search/design/generators/profiles.py` | 1100 | `100a5e3ae023f673` | clean |
| 7 | `hornlab_search/design/generators/rolled_family.py` | 232 | `fe2b22f0b7dfc157` | clean |
| 8 | `hornlab_search/design/generators/klangfilm_lame_hv_family.py` | 158 | `f8647ae30bcf1609` | clean |
| 9 | `hornlab_search/design/generators/crowe_hv_area_aspect_v1.py` | — | — | **modified / in flight** (new family) |
| 10 | `hornlab_search/search/evaluate.py` | 1742 | `a6168d406d23c844` | clean |
| 11 | `hornlab_search/search/outcomes.py` | 149 | `391e228ee9fb438f` | clean |
| 12 | `hornlab_search/search/cma.py` | 1092 | `6f283a44f5d88cd9` | clean |
| 13 | `hornlab_search/search/cma_me.py` | 1005 | `24a4461ed9079af2` | clean |
| 14 | `hornlab_search/search/links.py` | 75 | `0652c8dac211bf73` | clean |
| 15 | `hornlab_search/targets/spec.py` | 167 | `513064af797dc984` | clean |
| 16 | `hornlab_search/objective/scalar_v7.py` | 493 | `30572b1641fc57e0` | clean |
| 17 | `hornlab_search/objective/scalar_v9.py` | 561 | — | **untracked, in flight**; imports `hornlab_search.targets.profile`, which **does not exist at this snapshot** → not importable |
| 18 | `hornlab_search/objective/versions.py` | — | — | **modified**; `SUPPORTED_OBJECTIVE_VERSIONS` now includes `9` in the working tree |
| 19 | `hornlab_search/metrics/polar.py` | 145 | `b86cf86df5f98f5c` | clean |
| 20 | `hornlab_search/bo/encoding.py` | 297 | `f5219d749b058ffe` | clean |
| 21 | `hornlab_search/bo/data.py` | 1165 | `5ce7150f4b83dfa2` | clean |
| 22 | `hornlab_search/bo/cohort.py` | 146 | `c91aa2de7c4985f7` | clean |
| 23 | `hornlab_search/bo/model.py` | 537 | `d6df4e45d97ed4cd` | clean |
| 24 | `hornlab_search/bo/policy.py` | 697 | `4e947c9ccac94488` | clean |
| 25 | `hornlab_search/bo/pareto.py` | 325 | `cc47ffcf3f78a197` | clean |
| 26 | `hornlab_search/bo/turbo.py` | 380 | `7a86146e5be13796` | clean |
| 27 | `hornlab_search/bo/diagnostics.py` | — | — | **modified**, not cited for any headline |
| 28 | `hornlab_search/dataset/identity_v2.py` | 61 | `790965ce634aa5c8` | clean |
| 29 | `hornlab_search/config.py` | — | — | **modified** (v9 registration path); cited only for stable envelope/family lines via lane reports |
| 30 | `tools/run_campaign_night.py` | 1522 | `978bff92331c7372` | clean |
| 31 | `tools/analysis/optimizer_switch.py` | 97 | `e2f0e74fc5966241` | clean |
| 32 | `tools/analysis/walls.py` | 124 | `dfa29c297f585c22` | clean |
| 33 | `tools/analysis/parameter_activity.py` | 700 | `06bd44a4c1ad5c03` | clean |
| 34 | `tools/analysis/geometry_effects.py` | 408 | `f77e723f4f80cc0d` | clean |
| 35 | `tools/analysis/geometry_descriptors.py` | 375 | `42edce91e3d93828` | clean |
| 36 | `tools/analysis/links.py` | 171 | `294b637cac548fcf` | clean |
| 37 | `tools/night_status.py` | 285 | `186456063c444ace` | clean |
| 38 | `tools/night_queue/queue.ps1` | 74 | `0e9884e6ceac7fc8` | clean |
| 39 | `examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml` | 73 | `7d7d2d0cf0480d41` | clean; envelope L21–23, target L28–29, owner range L8 |
| 40 | `docs/status/2026-11-14/README.md` | 109 | `281188b47e26db61` | historical report |
| 41 | `docs/queue/HOME_SCORE_AUDIT_2026-11-16.md` | 30 | `12610a356fdac232` | historical audit |
| 42 | `docs/queue/HOME_OPTIMIZER_COMPARISON_2026-11-16.md` | 70 | `b4466f3efc1386b4` | historical comparison |
| 43 | `docs/queue/MATCHED_HOME_PROTOCOL_2026-11-16.md` | 29 | `e15ec87391377d9d` | protocol |
| 44 | `docs/evidence/HOME_OSSE_HIFI_RERANK_2026-11-16.md` | 55 | `2319c959d67816b0` | historical rerank |
| 45 | `docs/queue/TRITONIA_V9_CMA_AUDIT_2026-11-16.md` | 24 | `b96b4141fe904ff7` | historical audit |
| 46 | `docs/research/typologies/NON_CD_OBJECTIVE_PROFILE_RFC_2026-11-16.md` | — | — | untracked/in-flight RFC (52 KB) |
| 47 | `docs/evidence/NON_CD_SCORE_TRUTH_TABLE_2026-11-16.md` | — | — | untracked/in-flight truth table |

Note: `grid.py`, `evaluate.py` and `generated.py` line counts above are `(Get-Content).Count`
(raw lines). PowerShell `Measure-Object -Line` skips blank lines and under-counts these files —
the difference is why an early count read `2813` for a 3020-line file.

## 3. Run/artifact evidence used read-only

| Evidence | What it is | Status |
|---|---|---|
| `runs/20261116*/search.ndjson` (53 run dirs) | Candidate attempts and outcomes for the 2026-11-16 window | historical run record; parsed by `scratch/fable_architecture/.tmp/` scripts |
| `runs/study-f269f257b24e00f2`, `runs/study-4e1a6a9cd4bb5201` | Scalar BO and TuRBO study runs | historical record |
| `runs/20261115T052416Z-screen-cdbc27` | CMA arm with 29/60 refusals | historical record |
| `runs/bo_multityp_2026-11-16/bo_cov_s71001/package.json` | Prepared BO package, 155 code pins, deadline | historical artifact; 18 pins differ at snapshot, deadline past |
| `runs/bo_multityp_2026-11-16/lecleach_iwata_ar/cohort/offline_scores.json` | 80 raw `exact_complete` rows, 1 strict | historical record |
| `runs/20261115T005614Z-screen-6d55fa/archive.json` | QD archive 10/324 cells after 200 solves | historical record |
| `runs/nights/*/summary.jsonl` | 38 watchdog-stopped rows, all `best_J: null` | historical record |
| `docs/queue/HOME_SCORE_AUDIT_2026-11-16.json` | Queue snapshot with `queue_sha256` | historical audit artifact |

## 4. External handoff package (read-only, outside the repo)

`C:\Users\hunte\Downloads\Hornfab_Fable_Architecture_Handoff_2026-11-16_v3\hornfab_fable_handoff\`

| File | Used for |
|---|---|
| `00_START_HERE.md` | scope and staged process |
| `01_CHEAP_AGENT_DISPATCH.md` | investigator A–D assignments and parent duties |
| `02_EVIDENCE_FORMAT.md` | output contract, mandatory distinctions, acceptance checklist |
| `06_REPO_FINDINGS_AND_SOURCE_MAP.md` | prior review claims to re-verify (several were stale) |
| `08_OPTION_EXPLORATORY_SIZE_AND_FEASIBILITY.md` | size/feasibility option and required checks |
| `09_OPTION_ADAPTIVE_SEARCH_SUPERVISOR.md` | supervisor option space and code map |
| `10_CHEAP_AGENT_SEARCH_SUPERVISOR_PASS.md` | the five v3 artifacts and their rules |
| `11_ACCEPTANCE_AND_EXPERIMENT_PROTOCOL.md` | evidence standards for adaptive-policy claims |

## 5. Dossier artifacts (this pass) — SHA-256[0:16] and size

| File | Bytes | SHA-256[0:16] |
|---|---:|---|
| `INDEX.md` | (written last) | — |
| `SOURCE_INDEX.md` | this file | — |
| `GEOMETRY_AND_PARAMETER_MAP.md` | 57,242 | `5c5032f199367d77` |
| `FAILURE_AND_BOUNDARY_AUDIT.md` | 19,553 | `b94f35a6dd8b0697` |
| `SIZE_FEASIBILITY_EVIDENCE.md` | 20,728 | `f410d48f4fff6b73` |
| `OPTIMIZATION_AND_BRIEF_AUDIT.md` | 25,103 | `a12115182a23e3b9` |
| `OPTIMIZER_AND_SWITCH_SECTION.md` | 22,915 | `08745f8867583765` |
| `EXTERNAL_EVIDENCE.md` | 21,620 | `e693ba31ac5ac854` |
| `SEARCH_CONTROL_MAP.md` | 17,582 | `2d74af4589a3d24a` |
| `WATCHDOG_REPLAY.md` | 16,628 | `76f926a31401c4bb` |
| `SWITCH_ADMISSION_MATRIX.md` | 15,784 | `4e7adfb703948671` |
| `SUPERVISOR_OPTIONS.md` | 16,098 | `058df7e364952b07` |
| `ADAPTIVE_UNKNOWNS.md` | 7,218 | `0cb979ac3f141d77` |
| `EVIDENCE_LEDGER.md` | (written) | — |
| `OPEN_QUESTIONS.md` | (written) | — |

`scratch/fable_architecture/.tmp/` holds the read-only parsers/replay helpers and intermediate
JSON written by Investigators B and D (`agg_20261116.py`, `run_scan.json`,
`run_agg_by_config.json`, `watchdog_replay.py`). They are analysis aids, not evidence by
themselves; every number is quoted with its source in the audit files.

## 6. Method and non-mutation statement

- Access was read-only for the repository, configs, caches, queues and processes. No `git`
  mutation, no `pytest`, no mesher/BEM/GPU call, no search/job start or stop, no lane/GPU lock
  taken.
- Counts were computed by parsing extant `search.ndjson`/`summary.jsonl`/`archive.json`/YAML
  with `.venv\Scripts\python.exe` (pure CPU, bounded, scratch-only writes).
- `WATCHDOG_REPLAY.md` imported the pure `watchdog_verdict` function; the kill path was never
  executed.
- External sources in `EXTERNAL_EVIDENCE.md` were fetched as metadata/abstracts; paywalls are
  marked.
- The concurrent lane's commits and edits are reported as observations, not attributed to this
  pass. Pre-existing dirt was neither reverted nor overwritten.
