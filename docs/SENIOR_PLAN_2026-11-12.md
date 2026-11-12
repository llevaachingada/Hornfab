# Senior plan, 2026-11-12: one main, one truth, then speed and the GUI

Owner directive (2026-11-12 chat, summarised): merge the collaborator's (Collin's) open work and everything else
outstanding into one tested main; **pause new MEH work** (Collin's MEH path stays merged and maintained, no new
MEH work packages); then make the scoring, driver and data assumptions consistent with each other, with Collin's
work and with the outside research; speed up the solve; make the GUI show what is needed; clean up expired
issues, branches and docs. The senior lead (this document's author) decides order and scope.

Referenced from `docs/NEXT_DEV_PRIORITIES.md` (P14). Supersedes the ordering of P10's later items and of
`docs/HANDOFF_NEXT_RUNS_2026-10-30.md` section 4 where they conflict.

## 0. State at the start of this plan [measured 2026-11-12]

**Integration branch `integ/2026-11-12`** = `origin/main` (`0fb7d98`) plus, as real merge commits so authorship
and PR state are kept:

| Merged | What | Conflicts resolved |
|---|---|---|
| PR #19 `meh/integration` | MEH CPU-vs-CUDA bench scripts + catalog rows | docs only |
| `fix/cuda-fused-meh-bench-audit` | multi-channel fused CUDA (beat-bem pin `0850ef3`, fork branch pushed); withdraws "CPU is 6.4x faster" (VRAM spill) | docs; the withdrawn claims in ISSUES are marked |
| **PR #22 (Collin)** | Solana/SAWMOD bench, `mid_ports` MEH path (mesher pin `jamescollinharky/...@55da4f4`), **objective v6** `loading_smooth`, Design cloud (UMAP/PCA), RunPod tooling | pins: Collin's mesher + our beat-bem; docs |
| PR #23 | throughput packet (stage timer, mesh prefetch, freq-batch, curvature meshing; all opt-in, unmeasured) + Boundary Lab A/B check | `evaluate.py` (fc stamp + stage timer kept); bench scripts keep our spill-aware `_bench_common` + #23's `bench_solve_kwargs` |
| `feat/hardened-plan-2026-10-29` (13 commits, never PR'd) | hardened D cells, **its objective "v5" -> renumbered v7**, gate audit, data dedupe/doctor/keepers, atlas night, GUI perf, owner retargets of 10-29 | see section 1 |

Offline suite on the merge: **2,474 collected, 2,472 passed**, 2 stale version-tuple asserts fixed and rerun green.
Not yet merged: `swarm/B` (`verify --designs`), `swarm/C` (atlas v2 configs) - section 2 WP-A2.

## 1. The objective-number collision (fixed in the merge)

Main's v5 is the MEH system objective (PR #18). The hardened branch's loading/flat_cv/8 kHz-floor/signed-V
objective was also written as "5". Both were stored as a bare `5`.

- Code: hardened scorer is `objective/scalar_v7.py` (`V7Params`, `objective_v7`); dispatch, config validation and
  the penalty-ordering guard carry v7; `versions.py` = (1..7). The hardened round-throat refusal (C4) now applies
  to **v7 only** (it was `>= 5`, which would have switched it on for MEH and Collin's v6).
- Briefs: the nine `examples/briefs/{hardened,data}_2026-10-29_v5/*.yaml` say `version: 7` (folder names kept so
  run dirs' `brief_file` paths still resolve). Collin's Solana/SAWMOD briefs keep `version: 5` = MEH (correct).
- Data: `tools/data/renumber_objective_v5_to_v7.py --apply` relabelled **1,371 dataset rows** (shards 45-47,
  2026-10-29) and **26 run dirs** (2026-10-29); MEH's 126 rows (shards 53-54) untouched; originals in
  `runs/_backup_renumber_v5_v7/` (13 MB). Re-run = no-op. **The public HF dataset still has the old labels**
  (WP-E4).

| Version | Meaning | Use for |
|---|---|---|
| 4 | tolerance-normalised pattern objective (owner Option A, 10-27) | legacy comparisons only |
| 5 | MEH system objective | MEH briefs (Collin's Solana/SAWMOD + ours) |
| 6 | `loading_smooth` (Collin, 11-05) | Le Cléac'h / rollback class |
| 7 | hardened loading + flat_cv + 8 kHz floor + signed V + round-throat gate (10-29) | CD briefs (hi-fi and PA) |

WP-B1 decides whether 6 and 7 should become one objective.

## 2. Work packages

Order: A (done here) -> E (hygiene, small) -> B (scoring truth, needs research) and C (speed, needs GPU) and
D (GUI) in parallel lanes. One GPU job at a time; GPU work only from the night worktree (section 3).

### WP-A Integration [this session]
- A1 Push `integ/2026-11-12`, open the PR, merge into `main` with a merge commit (PRs #19, #22, #23 close as
  merged). **Done when** `main` = this branch and CI is green.
- A2 Merge `swarm/B` (`verify --designs/--designs-file`, CLI + test) and `swarm/C` (atlas v2 configs) in a follow-up
  PR after A1, run the suite, merge.
- A3 Close `beta-fixes` (its Solana note is superseded by `docs/IMPLEMENTATION_PLAN_2026-10-27.md` section 9).

### WP-E Hygiene (small, first after A)
- E1 Delete merged local branches and their worktrees: `meh/M*` (meh-wt/*), `swarm/*` (after A2), `task/*`,
  `unified-typologies`, `integ/pr17`, hf-wt/P11. Keep `dev/fused-cuda-pin` (dev-only). Delete merged remote
  branches only after their PR shows merged.
- E2 `docs/CONTINUITY.md` is no longer newest-first after the merges: re-order entries by date (newest first),
  move pre-2026-10-27 entries to `docs/history/` (the hardened branch's pattern). `docs/ISSUES.md`: resync to
  GitHub (one open issue, #13, fixes merged 2026-10-22 -> close it), collapse the "local-only" notes into a
  current-state table, drop superseded bench claims.
- E3 `docs/NEXT_DEV_PRIORITIES.md`: mark done items (P1 fused CUDA, P2 12 kHz, P3 Metal via PR #17, P10 1-3,
  P11, P13 MEH), park P13 follow-ups as "paused by owner 2026-11-12", put this plan's lanes at the top.
- E4 Re-pack and re-upload the HF dataset after the v7 relabel (`tools/hf_sync.py`, `HF_HUB_DISABLE_XET=1`);
  tell Collin in the runbook that v5 rows dated 10-29 are now v7.
- E5 Line endings: add `.gitattributes` (`* text=auto eol=lf`, `*.ps1 eol=crlf`) and renormalise once in its own
  commit; three docs flip CRLF/LF on every merge today.
- E6 Memory/notes: `NOTES_FOR_SENIOR.md` resolved items -> `docs/history/NOTES_FOR_SENIOR_resolved.md`.

### WP-B Scoring, drivers and data truth (research-grounded; `hornlab-typology-research` skill applies)
- B1 **One loading story.** v4 `load`, v6 `load_near`/`z_smooth` and v7 `load`/LFP all score throat Re z
  differently. Write `docs/research/LOADING_OBJECTIVES_RECONCILED_2026-11.md`: each definition (file:line), what
  the outside research says (`docs/research/SIM_VS_REAL_HORN_2026-10-27.md`, Collin's
  `LECLEACH_OBJECTIVE_V6_2026-11-05.md`), and a recommendation: keep v6 for the Le Cléac'h class and v7 for CD
  briefs, or merge them into v8. Owner approves before any brief changes.
- B2 **Re-score everything offline** (no GPU): every stored valid row under v6 and v7 with
  `tools/rescore/gate_audit.py`; report rank stability of today's winners and gate pass rates per brief. Free,
  CPU-only, the most useful single check of the scoring.
- B3 **Round-throat gate as a brief flag** (`gates.round_throat: true`) for every single-entry objective, not tied
  to v7 (the owner's 10-27 decision applies to all prints). Default on for new briefs, off for stored ones.
- B4 **Driver model check.** `hornlab_search/driver/compression.py` (hardened) vs `docs/DRIVER_MODEL.md` vs the
  driver YAMLs in `examples/drivers/` (filled from datasheets): validate predicted sensitivity against each
  datasheet's published sensitivity (P0 item 8); flag drivers missing `Mmd`/source URL.
- B5 **Scoring honesty gaps still open** (P12): screen grid starts at 500 Hz (big-PA loading never solved below
  it); 2 m vs 10 m; H/V-only scoring (diagonal term exists in v4, weight 0). Each gets a decision line.
- B6 **Measured reference.** P12b: one published measured horn through the pipeline (accept beamwidth +-5 deg,
  DI +-1 dB). Without it, no score is calibrated to reality.

### WP-F Data interop with the collaborator (audit 2026-11-12)
Every Collin commit is in `main` (PR #17's 72 functions/classes/constants all present after its squash;
PR #22 merged here). The DATA path is one-way: Collin's RunPod runs (Solana 4090 screen, CMA-300/1000) never
reached this box, the dataset has no MANIFEST (`docs/plan/07_TASK_DATASET.md`), and designs cannot be exported in
the mesher's own config (`docs/plan/12_RESEARCH_BASIS.md` line 332). Fix tonight, handoff lane L5: MANIFEST,
`export_config.py`, two-way HF (`labs/<name>/`), foreign-data ingest into `dataset_ext/<lab>/` with a 0.2 dB
parity gate, version/backend-grouped tables, HF re-pack with the v7 relabel. Owner: grant Collin HF write access.

### WP-C Solve speed (measure, then flip defaults)
- C1 **Measure PR #23's opt-ins** on the 4060 with `tools/bench/throughput_matrix.py`: stage timer on; fused
  CUDA on/off; mesh prefetch on/off; `freq_batch_size`; 3 reference designs (1k / 4k / 8k dofs). Every CUDA
  number carries the WDDM shared-usage reading (`_bench_common.GpuMemPeak`, CLAUDE.md rule 8). Night item N1.
- C2 **Flip defaults that win** (one PR, numbers in `docs/evidence/THROUGHPUT_<date>.md`); cache keys must not
  change unless the solve changes.
- C3 **Assembly is 73-96 % of per-frequency cost** (smoke night section 2). Validate and apply
  `docs/throughput/WP1_FUSED_IDENTITY_CACHE_PATCH.md` in the beat-bem fork (docs/FORKS.md ladder: CPU parity,
  CUDA parity, pin bump).
- C4 Budget counts valid solves only; successive halving per brief (P0 item 4) - search-side speed.
- C5 Owner action: NVIDIA Control Panel -> `julia.exe` -> CUDA Sysmem Fallback Policy -> Prefer No Sysmem
  Fallback (a spill otherwise runs 5-10x slower silently).

### WP-D GUI: correct and useful
- D1 **Version awareness everywhere.** The brief editor offers objective versions 1-3 only
  (`objectiveVersionOptionsHtml`, app.js ~1884): add 4-7 with one-line descriptions from section 1's table. Run
  lists, compare and the Design cloud show the objective version and refuse to rank J across versions.
- D2 **Gates visible.** Run explorer shows each design's gate results (round throat, loading, f11, CD) from the
  gate audit, not only J.
- D3 **Verify the three new views on real data:** Design cloud (#22), Boundary Lab A/B report (#23), the 3D
  evolution decimation fix (hardened). Screenshot evidence.
- D4 **Elites catalog page:** the verified atlas elites (`scratch/gate_audit_elites_2026-10-30/`) as a coverage
  map of cards (`hornlab-render` layouts), the 10-30 handoff's "catalog" deliverable.
- D5 Owner click-path check of D1-D4 (P9's sandbox stays a proposal).

### MEH: paused
No new MEH work packages. Keep the merged code green (CI) and Collin's `mid_ports` path working. Open MEH
readiness items (link 3 partial, link 4 fail, `docs/evidence/MEH_M8_2026-10-31.md`) are parked, not dropped.

## 3. GPU night and the CPU second lane (8-24 h unattended)

**Executable handoff: `docs/OPENCODE_HANDOFF_2026-11-12.md`** (OpenCode orchestrator + parallel workers).

- The night runs from the **main checkout**: the CLI keeps `runs/`, `cache/`, `dataset/` there, so a worktree
  night would lose every cache hit. Coding workers use their own worktrees under `C:\Users\hunte\Hrns\oc-wt\`
  (pytest in a worktree imports that worktree's code). Nobody touches the main checkout or `.venv` during a night.
- **DECIDED 2026-11-12: integrate the CPU second lane now** (`docs/research/CPU_SECOND_LANE_HARDENING_2026-10-28.md`;
  its section 12 is answered in the handoff, lane L1): Option B (shared `runs/`, CPU lane on `cache_cpu` /
  `dataset_cpu`), lane identity by BEAT worker dir, unknown hosts never killed, `solve.julia_threads` (12 for the
  CPU lane) outside the solve hash, `.cpu.lane.lock`, the night runner's `taskkill /IM julia.exe` removed. No
  separate pre-test: the night's per-lane logs are the measurement; hourly check-ins with GPU<->CPU failover.
- N2 (calibration) moves to the next night: it needs the n1 throughput defaults first.

| # | Job | Why | Est. |
|---|---|---|---|
| N0 | `gpu-clean`, VRAM baseline, `selftest` | hygiene | 10 min |
| N1 | Throughput matrix (WP-C1) | decides the speed defaults | 1.5-2 h |
| N2 | Calibration (P0 item 2): band-split vs single mesh, 10 m vs 2 m, epw 6 vs 9 in 2.5-5.5 kHz, on 6 stored finalists; verify grid on the top 5 per brief | does the screen ranking survive? gates every later night | 3-4 h |
| N3 | Atlas extend: resume ATH CORE atlas `runs/20261030T111108Z-screen-377bbe` +400 | fills the coverage map | ~2 h |
| N4 | New atlas: `osse_ext_throat` (v7 cells, 18-point grid, 10 m, budget 200) | 20 self-referenced passers in the old audits | ~2.5 h |
| N5 | Collin's v6 Le Cléac'h brief, CMA budget 150 | first real v6 search; feeds WP-B1 | ~1.5 h |
| N6 | Verify top elites of N3-N5 (`verify --top`) | verified scorecard | ~1 h |

Total about 11-13 h; extend N3/N4 budgets for a 24 h window. The skip list from the 10-30 handoff stands (b3a
80x80: its 827 Hz Re z dip is structural).

## 4. Owner decisions still needed (short list)
1. B1: one loading objective (v8) or keep v6 + v7 split by class.
2. B3: round-throat gate on by default for new briefs.
3. C5: the NVIDIA sysmem setting (a machine setting only the owner can change).
4. P0 items still open: gate levels per use case (sensitivity floor hi-fi, max SPL PA); woofer block per brief.
5. Print 1-2 candidates (10-30 handoff section 4.3) - a measured print outranks any further night.
