# Tools — a task-first catalog

> **Start here before writing a new tool.** This is the map of the 214 entry points the
> 2026-11-25 tools inventory found (`docs/handoffs/repo_findability_2026-11-25/inventory/I4_tools.csv`):
> **186 live, 24 one-off, 4 dead**. Every live row appears once below; dead and one-off tools are
> kept in [Historical tools](#historical-tools), never hidden.
>
> Run every command from the repository root with the project interpreter
> (`.venv\Scripts\python.exe`); `hornlab-search ...` means the console script from that same venv
> (`.venv\Scripts\hornlab-search.exe`). `GPU: y` means the tool can solve or touch CUDA; `n` means
> CPU-only/offline. A night may be running: read
> `.claude/skills/hornlab-night-queue/SKILL.md` and use `GPU: n` tools unless you own the GPU lane.
>
> **Confidence of the command column.** The ten *Start here* invocations below were re-read from
> each tool's `argparse` and/or module docstring for this pass. In the long tables, a command ending
> in `[--flag ...]` came from the inventory's first-flag-only extraction: the flag name is exact,
> but run `<command> --help` for the required value form before using it.

## Start here — verified invocations

| Task | Exact command | GPU | Source |
|---|---|---|---|
| Is this search config worth GPU time? | `.venv\Scripts\python.exe tools/search_preflight.py CONFIG [CONFIG ...] [--samples N] [--json]` — exit 1 on hard faults; add `--strict` to promote warnings | n | [`tools/search_preflight.py`](../tools/search_preflight.py) |
| Does the seed mesh, fit the cap/envelope and couple to the driver? | `.venv\Scripts\python.exe tools/shape_check.py examples/typologies/<folder>/*.yaml [--brief examples/briefs/<brief>.yaml] [--save-mesh <dir>]` | n | [`tools/shape_check.py`](../tools/shape_check.py) |
| Validate a night file without starting it | `.venv\Scripts\python.exe tools/run_campaign_night.py --night runs/nights/<night>.yaml --dry-run` | n | [`tools/run_campaign_night.py`](../tools/run_campaign_night.py) |
| What is the night doing right now? | `.venv\Scripts\python.exe tools/night_status.py [--since-hours 24] [--top 6]` | n | [`tools/night_status.py`](../tools/night_status.py) |
| Re-score one stored design under another brief (backend-free) | `.venv\Scripts\python.exe -c "from hornlab_search.objective.replay import replay_run_dir; r=replay_run_dir('runs/<run>', '<design_hash>', brief='examples/briefs/<brief>.yaml'); print(r.j, r.status)"` | n | [`hornlab_search/objective/replay.py`](../hornlab_search/objective/replay.py) |
| Re-score a whole run directory from the CLI | `.venv\Scripts\python.exe tools/analysis/rescore_identity.py rescore --brief <brief.yaml> --out <dir> runs/<run> ...` | n | [`tools/analysis/rescore_identity.py`](../tools/analysis/rescore_identity.py) |
| Re-solve a run's top designs at verify fidelity | `hornlab-search verify --run <dir> --top 5` | y | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| Did the run converge? | `.venv\Scripts\python.exe tools/analysis/convergence.py --run <dir> [--run <dir> ...] --out <dir>` | n | [`tools/analysis/convergence.py`](../tools/analysis/convergence.py) |
| Which knobs actually moved J? | `.venv\Scripts\python.exe tools/analysis/sensitivity.py --run <dir> [--runs-dir <base>] --out <dir>` | n | [`tools/analysis/sensitivity.py`](../tools/analysis/sensitivity.py) |
| What did the night produce? | `.venv\Scripts\python.exe tools/night_report.py --night <name> [--night <name> ...] --out <path>.md` | n | [`tools/night_report.py`](../tools/night_report.py) |

## Route the 2026-11-25 lessons

| Lesson (why it was hard to find) | Where it now lives |
|---|---|
| **Scorer semantics / offline re-score.** Corridor mode charges zero inside `[min,max]` and never uses `preferred_deg`; beamwidth flatness needs the opt-in `objective.constancy` term. | [`docs/knowledge/SCORING_REFERENCE.md`](knowledge/SCORING_REFERENCE.md); replay with `replay_run_dir` / `rescore_identity.py` above. |
| **Family laws.** Joint validity rules (rolled relief limits, Klangfilm inert knobs, OSSE throat coupling, beak/backbone limits) were only in code. | [`docs/knowledge/FAMILY_LAWS.md`](knowledge/FAMILY_LAWS.md), then `tools/shape_check.py` / `tools/search_preflight.py`. |
| **Generator identity.** Editing a family's implementation digest orphans every saved recipe; new behaviour goes in a new module, registered byte-wise (CRLF) in `grid.py`, `mesh/build.py`, `generated.py`. | `.claude/skills/hornlab-generator-family/SKILL.md`; `tools/analysis/classify_recipes.py` reports which stored recipes still rebuild. |
| **Watchdog exploration.** Default `no_gain_valid`/`stall_valid`/`pin_ignore`/`refusal_max` stops cut campaigns far below the rows metric-BO needs; exploration jobs must override them. | `.claude/skills/hornlab-night-queue/SKILL.md`; the night files under `docs/queue/` and `runs/nights/`. |
| **BO identity and snapped starts.** Identity = brief + bounds; scrambled/Sobol starts must be snapped so `ActiveProjection` round-trips the seed hash; one box per family so runs pool. | `.claude/skills/hornlab-search-economy/SKILL.md`; `hornlab_search/bo/metric_identity.py`, `bo/encoding.py`, `bo/data.py`. |
| **Live-night splice.** `runs/nights/<night>.yaml` is re-read before each job; splice after the running job, then validate. | `.claude/skills/hornlab-night-queue/SKILL.md`; `tools/run_campaign_night.py --night ... --dry-run`. |
| **Find anything else.** Search order: `START_HERE` → this file → `docs/knowledge/` → `docs/research/README.md` → `docs/evidence/CATALOG.md`. | `.claude/skills/hornlab-find/SKILL.md`. |

The tables below are the complete live inventory. Descriptions are the tools' own one-line purposes
(module docstrings), not guesses. Source links are repo-relative.

## Plan a search

25 live entry point(s).

| Command | What it does | GPU | Source |
|---|---|---|---|
| `.venv\Scripts\python.exe tools/agent/ping_agents.py` | Prove skill discovery, skill grants and skill loading actually work. | n | [`tools/agent/ping_agents.py`](../tools/agent/ping_agents.py) |
| `.venv\Scripts\python.exe tools/analysis/benchmark_orchestrator.py [--spec ...]` | Controlled, pre-registered matched-benchmark orchestrator (advisory, offline). | n | [`tools/analysis/benchmark_orchestrator.py`](../tools/analysis/benchmark_orchestrator.py) |
| `.venv\Scripts\python.exe tools/analysis/hypothesis_cards.py [--spec ...]` | Provenance-checked experiment cards. Offline preparation; no acoustic claims. | n | [`tools/analysis/hypothesis_cards.py`](../tools/analysis/hypothesis_cards.py) |
| `.venv\Scripts\python.exe tools\analysis\seed_pack.py` | Diverse, feasible seed packs from real catalog records | n | [`tools/analysis/seed_pack.py`](../tools/analysis/seed_pack.py) |
| `.venv\Scripts\python.exe tools/analysis/space_card.py [--config ...]` | Space cards: owner-reviewable parameter-space evidence per lane (senior plan stage 5, 2026-11-17). | n | [`tools/analysis/space_card.py`](../tools/analysis/space_card.py) |
| `.venv\Scripts\python.exe tools/analysis/space_propose.py [--card ...]` | Turn a space card into a PROPOSED config next to the original (senior plan WP 5.1, 2026-11-17). | n | [`tools/analysis/space_propose.py`](../tools/analysis/space_propose.py) |
| `.venv\Scripts\python.exe tools/bassbox.py [--driver ...]` | Lumped sealed / vented bass-box model with DSP and limit-based maximum SPL (work package M10). | n | [`tools/bassbox.py`](../tools/bassbox.py) |
| `.venv\Scripts\python.exe tools/bench/run_with_memwatch.py [--out ...]` | Record a job's peak DEDICATED + SHARED ("Windows WDDM spill") VRAM. | n | [`tools/bench/run_with_memwatch.py`](../tools/bench/run_with_memwatch.py) |
| `.venv\Scripts\python.exe tools/bench/screen_grid_ab.py [--cohorts ...]` | SCREEN-grid A/B: frequency resolution and 12 kHz cost for hornlab-search. | y | [`tools/bench/screen_grid_ab.py`](../tools/bench/screen_grid_ab.py) |
| `.venv\Scripts\python.exe tools\bench\throughput_matrix.py --config examples\osse_baseline_fusedcuda.yaml` | Throughput matrix: warm/cold solve timing over fixture meshes x frequency sets x batch sizes. | y | [`tools/bench/throughput_matrix.py`](../tools/bench/throughput_matrix.py) |
| `.venv\Scripts\python.exe tools\bench\timing_ledger.py manifest.json` | Offline S9 timing ledger from an explicitly prepared manifest, never a solver. | n | [`tools/bench/timing_ledger.py`](../tools/bench/timing_ledger.py) |
| `.venv\Scripts\python.exe tools\calibration\plan_calibration.py` | Plan the P0 calibration night (offline; never solves). | n | [`tools/calibration/plan_calibration.py`](../tools/calibration/plan_calibration.py) |
| `.venv\Scripts\python.exe tools/cloud/runpod_ctl.py <pod_id> <pod_id> [--name ...]` | Thin RunPod GraphQL client for hornlab-search cloud GPU pods. | n | [`tools/cloud/runpod_ctl.py`](../tools/cloud/runpod_ctl.py) |
| `.venv\Scripts\python.exe tools/measure_fused_ceiling.py --mouth-res 3.0 --throat-res 1.5 --flag on` | Single-shot VRAM-ceiling measurement for the WP15 fused CUDA path. | y | [`tools/measure_fused_ceiling.py`](../tools/measure_fused_ceiling.py) |
| `.venv\Scripts\python.exe tools/night_queue/resolve_warm_runs.py examples/typologies/scout40_2026-11-19 [--check]` | Resolve ``@design:<hash>`` warm-start placeholders to real run dirs, then check every warm start. | n | [`tools/night_queue/resolve_warm_runs.py`](../tools/night_queue/resolve_warm_runs.py) |
| `.venv\Scripts\python.exe tools/run_staged_search.py [--base ...]` | Equal-budget staged (macro → shape → joint polish) vs joint CMA-ES A/B harness. | y | [`tools/run_staged_search.py`](../tools/run_staged_search.py) |
| `.venv\Scripts\python.exe tools/search_preflight.py CONFIG [CONFIG ...]` | will this search config produce new in-basin hits, or is its best J its seed? | n | [`tools/search_preflight.py`](../tools/search_preflight.py) |
| `hornlab-search doctor` | is this checkout's stack installed, pinned and healthy? | n | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| `hornlab-search version` | what version is installed and which fork SHAs does it expect? | n | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| `hornlab-search run --config <yaml> [--mode screen] [--dry-run]` | evaluate one seed config once (dry-run = mesh+estimate, no solve) | y | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| `hornlab-search search --config <yaml> [--budget N] [--resume DIR]` | run or resume a CMA-ES search from a config | y | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| `hornlab-search pin-plan --run <dir\|id> [--write-config PATH]` | which knobs should be pinned from a run's CMA covariance? | n | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| `hornlab-search narrow --run <dir\|id> [--widen] [--out PATH]` | write a narrowed/widened config from a run's bound-wall analysis | n | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| `hornlab-search families [--brief <yaml>]` | list catalog family entries, key counts and brief compatibility | n | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| `hornlab-search campaign --brief <yaml> --families <spec> --tier screen` | run a multi-family typology comparison campaign under one brief | y | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |

## Check a config or shape

33 live entry point(s).

| Command | What it does | GPU | Source |
|---|---|---|---|
| `.venv\Scripts\python.exe tools/analysis/crowe_mesh_truth.py` | CROWE V2A analytic-law vs actual BEM-wall geometry truth (CPU only, read/build only). | n | [`tools/analysis/crowe_mesh_truth.py`](../tools/analysis/crowe_mesh_truth.py) |
| `.venv\Scripts\python.exe tools/analysis/mesh_acoustic_ab.py` | Frozen-grid acoustic A/B across saved-mesh policy arms (CPU backend by default). | n | [`tools/analysis/mesh_acoustic_ab.py`](../tools/analysis/mesh_acoustic_ab.py) |
| `.venv\Scripts\python.exe tools/analysis/mesh_fidelity.py <mesh.msh or design dir>` | Mesh fidelity report (read-only). | n | [`tools/analysis/mesh_fidelity.py`](../tools/analysis/mesh_fidelity.py) |
| `.venv\Scripts\python.exe tools/analysis/mesh_policy_ab.py` | Build mesh-only policy arms for one saved design, then audit each mesh (CPU only). | n | [`tools/analysis/mesh_policy_ab.py`](../tools/analysis/mesh_policy_ab.py) |
| `.venv\Scripts\python.exe tools/analysis/mesh_region_audit.py <design dir \| mesh.msh>` | Region-level mesh-resolution audit (read-only). | n | [`tools/analysis/mesh_region_audit.py`](../tools/analysis/mesh_region_audit.py) |
| `.venv\Scripts\python.exe tools/analysis/record_shadow.py <runs> [--out ...]` | Record shadow gate and history records (senior plan WP 3.3 + 3.4, 2026-11-17). | n | [`tools/analysis/record_shadow.py`](../tools/analysis/record_shadow.py) |
| `.venv\Scripts\python.exe tools\bench\mesh_policy_study.py --config examples\<meh config>.yaml` | Mesh-sizing study: baseline vs opt-in curvature policy, no solve required. | n | [`tools/bench/mesh_policy_study.py`](../tools/bench/mesh_policy_study.py) |
| `.venv\Scripts\python.exe tools/geometry/apply_cd_backbone.py --run runs/<run> --design <hash>` | Wrap a saved design in the CD wall-angle backbone (cd-backbone-v1) as fixed-candidate configs. CPU only. | n | [`tools/geometry/apply_cd_backbone.py`](../tools/geometry/apply_cd_backbone.py) |
| `.venv\Scripts\python.exe tools/geometry/audit_rolled_family.py <config> [--samples ...]` | Audit a master-family search box through the real CPU mesher, without BEM. | n | [`tools/geometry/audit_rolled_family.py`](../tools/geometry/audit_rolled_family.py) |
| `.venv\Scripts\python.exe tools/geometry/crowe_hv_area_aspect_jacobian.py` | Identifiability check for the CROWE-inspired V2A four-DOF family (CPU geometry only). | n | [`tools/geometry/crowe_hv_area_aspect_jacobian.py`](../tools/geometry/crowe_hv_area_aspect_jacobian.py) |
| `.venv\Scripts\python.exe tools/geometry/crowe_hv_area_aspect_sections.py` | Section cuts for the CROWE-inspired V2A forward area/aspect family (CPU geometry only). | n | [`tools/geometry/crowe_hv_area_aspect_sections.py`](../tools/geometry/crowe_hv_area_aspect_sections.py) |
| `.venv\Scripts\python.exe tools/geometry/crowe_panel_cli.py` | Explicit entry point for the separate, versioned Crowe panel visual study. | n | [`tools/geometry/crowe_panel_cli.py`](../tools/geometry/crowe_panel_cli.py) |
| `.venv\Scripts\python.exe tools/geometry/gui_preview.py --cli rosse_rect_cli --config hl__rosse_rect_cd_v7 --root . --detail 2d [--brief NAME] [--knobs '{...}']` | GUI preview helper for the opt-in bridge typologies. | n | [`tools/geometry/gui_preview.py`](../tools/geometry/gui_preview.py) |
| `.venv\Scripts\python.exe tools/geometry/klangfilm_ellipse_cli.py` | Explicit entry point for the rectangular elliptical Klangfilm (Ahlswede calculator) family (``rows.type: klangfilm_ellipse``). | n | [`tools/geometry/klangfilm_ellipse_cli.py`](../tools/geometry/klangfilm_ellipse_cli.py) |
| `.venv\Scripts\python.exe tools/geometry/klangfilm_hv_contact_sheet.py` | Klangfilm-Lame H/V Phase A contact sheet (matplotlib Agg only; CPU; no meshing/BEM). | n | [`tools/geometry/klangfilm_hv_contact_sheet.py`](../tools/geometry/klangfilm_hv_contact_sheet.py) |
| `.venv\Scripts\python.exe tools/geometry/klangfilm_hv_core_preflight.py` | Phase B geometry preflight and plots (CPU only, no mesh/solve). | n | [`tools/geometry/klangfilm_hv_core_preflight.py`](../tools/geometry/klangfilm_hv_core_preflight.py) |
| `.venv\Scripts\python.exe tools/geometry/klangfilm_hv_preflight.py` | Klangfilm-Lame H/V Phase A geometry preflight (CPU only; no meshing, no BEM, no GPU). | n | [`tools/geometry/klangfilm_hv_preflight.py`](../tools/geometry/klangfilm_hv_preflight.py) |
| `.venv\Scripts\python.exe tools/geometry/klangfilm_hv_search_box.py [--samples 200]` | Lawfulness probe for the Klangfilm-Lame H/V Phase A search box (CPU only, no solves). | n | [`tools/geometry/klangfilm_hv_search_box.py`](../tools/geometry/klangfilm_hv_search_box.py) |
| `.venv\Scripts\python.exe tools/geometry/klangfilm_lame_cli.py` | Explicit entry point for the Klangfilm-Lame (curved-cap, Lame section) family (``rows.type: klangfilm_lame``). | n | [`tools/geometry/klangfilm_lame_cli.py`](../tools/geometry/klangfilm_lame_cli.py) |
| `.venv\Scripts\python.exe tools/geometry/rolled_rect.py <recipes> [--out ...]` | Original rectangular rolled-mouth geometry; CPU only, not Crowe's ES equation. | n | [`tools/geometry/rolled_rect.py`](../tools/geometry/rolled_rect.py) |
| `.venv\Scripts\python.exe tools/geometry/rolled_rect_cli.py` | Opt-in CLI bridge for the original rolled-rectangle experiment. | n | [`tools/geometry/rolled_rect_cli.py`](../tools/geometry/rolled_rect_cli.py) |
| `.venv\Scripts\python.exe tools/geometry/rosse_rect_cli.py` | Explicit entry point for the rectangular R-OSSE rolled-mouth family (``rows.type: rosse_rect``). | n | [`tools/geometry/rosse_rect_cli.py`](../tools/geometry/rosse_rect_cli.py) |
| `.venv\Scripts\python.exe tools/geometry/section_pucker_cli.py` | Explicit entry point for the separate, versioned section-based H/V relief study. | n | [`tools/geometry/section_pucker_cli.py`](../tools/geometry/section_pucker_cli.py) |
| `.venv\Scripts\python.exe tools\make_shape_variants.py` | Generate Morph / guiding-curve SEARCH variants of every typology that can take them. | n | [`tools/make_shape_variants.py`](../tools/make_shape_variants.py) |
| `.venv\Scripts\python.exe tools/rescore/driver_check.py [--out scratch/driver_check]` | Driver-file readiness audit (report-only; NO code change to any driver model). | n | [`tools/rescore/driver_check.py`](../tools/rescore/driver_check.py) |
| `.venv\Scripts\python.exe tools/shape_check.py examples/typologies/<folder>/*.yaml [--brief <yaml>]` | does a config's seed mesh, fit the solver cap, fit the brief envelope and couple round to the driver? (CPU-only, safe during a night) | n | [`tools/shape_check.py`](../tools/shape_check.py) |
| `.venv\Scripts\python.exe tools/system/mesh_sensitivity.py [--level ...]` | Mesh-sensitivity comparison for one assembled horn+cabinet case at several mesh levels. | n | [`tools/system/mesh_sensitivity.py`](../tools/system/mesh_sensitivity.py) |
| `.venv\Scripts\python.exe tools\system\pose.py` | Resolve one horn-over-cabinet pose from real geometry and prove it is legal. | n | [`tools/system/pose.py`](../tools/system/pose.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.geometry.record import record_for_design; rec=record_for_design(design, cfg)"` | build the canonical surface record for a design (geometry layer) | n | [`hornlab_search/geometry/record.py`](../hornlab_search/geometry/record.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.geometry.record import descriptors; d=descriptors(rec)"` | describe a surface record (mouth, depth, curvature descriptors) | n | [`hornlab_search/geometry/record.py`](../hornlab_search/geometry/record.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.geometry.edits import apply_radial_edit; rec2=apply_radial_edit(rec, delta, name='edit')"` | apply a radial geometry edit and keep a named surface record | n | [`hornlab_search/geometry/edits.py`](../hornlab_search/geometry/edits.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.geometry.sensitivity import analyze_space; a=analyze_space(space, cfg)"` | measure per-knob geometry influence and refusal risk for a search space | n | [`hornlab_search/geometry/sensitivity.py`](../hornlab_search/geometry/sensitivity.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.geometry.translate import match_descriptors; x=match_descriptors(space, cfg, target)"` | translate target geometry descriptors back into a search vector | n | [`hornlab_search/geometry/translate.py`](../hornlab_search/geometry/translate.py) |

## Queue and monitor a night

12 live entry point(s).

| Command | What it does | GPU | Source |
|---|---|---|---|
| `.venv\Scripts\python.exe tools/night_queue/refresh_watchdog.py --night <night> [--once]` | Night refresher: every tick, look at the failed/watchdog-stopped jobs of a night and repair them. | y | [`tools/night_queue/refresh_watchdog.py`](../tools/night_queue/refresh_watchdog.py) |
| `.venv\Scripts\python.exe tools/night_queue/walls_continuations.py --night cd_rrect_2026-11-17 [--min-rows 30] [--days 3] [--max-items 12] [--samples 8] [--dry]` | Generate walls-relieved successor configs + queue jobs for recent runs that hit bound walls. | n | [`tools/night_queue/walls_continuations.py`](../tools/night_queue/walls_continuations.py) |
| `.venv\Scripts\python.exe tools/night_report.py --night <name> [--night <name> ...] --out <path>.md` | Morning report for night jobs, straight from ``summary.jsonl`` + the run dirs (D.4). | n | [`tools/night_report.py`](../tools/night_report.py) |
| `.venv\Scripts\python.exe tools/night_status.py [--since-hours 24] [--top 6]` | monitor a live night: running job per lane, row age, lock holder, stall alerts | n | [`tools/night_status.py`](../tools/night_status.py) |
| `.venv\Scripts\python.exe tools\observe_run.py --night smoke_2026-10-27` | Read-only observer for an overnight campaign night. | n | [`tools/observe_run.py`](../tools/observe_run.py) |
| `.venv\Scripts\python.exe tools/run_campaign_night.py --night runs/nights/<night>.yaml [--dry-run]` | run an overnight campaign night, one GPU job at a time, with hygiene and a summary per job | y | [`tools/run_campaign_night.py`](../tools/run_campaign_night.py) |
| `.\tools\meh\run_screen.ps1 -Tag t2 -Config examples\typologies\meh_2026-10-30\meh_t2a_search.yaml -Budget 40` | run one MEH brief as a GPU screen job then verify its top candidates | y | [`tools/meh/run_screen.ps1`](../tools/meh/run_screen.ps1) |
| `powershell -NoProfile -ExecutionPolicy Bypass -File tools\night_queue\launch_detached.ps1 -Script tools\night_queue\cut_jobs.ps1 -ScriptArgs "-WaitPid 25164 -Match crowe_panel_cli.py -Log runs\nights\cut_d.log"` | cut named jobs out of a night that is already running | n | [`tools/night_queue/cut_jobs.ps1`](../tools/night_queue/cut_jobs.ps1) |
| `powershell -NoProfile -ExecutionPolicy Bypass -File tools\night_queue\launch_detached.ps1 -Script tools\night_queue\queue.ps1 -ScriptArgs "-Nights my_night -Cutoff 18:00"` | start a PowerShell night script detached so closing the app cannot kill it | n | [`tools/night_queue/launch_detached.ps1`](../tools/night_queue/launch_detached.ps1) |
| `powershell -NoProfile -ExecutionPolicy Bypass -File tools\night_queue\launch_detached.ps1 -Script tools\night_queue\queue.ps1 -ScriptArgs "-Nights <night,...> -Cutoff 17:30 -WaitPid <pid> -WaitMatch <text> -Log runs\nights\queue.log"` | run several night files back to back unattended | y | [`tools/night_queue/queue.ps1`](../tools/night_queue/queue.ps1) |
| `powershell -NoProfile -ExecutionPolicy Bypass -File tools\overnight\watchdog.ps1 -QueuePid <pid> -StallMin 30 -PollSec 120` | kill a stalled GPU job tree so an unattended queue can continue | n | [`tools/overnight/watchdog.ps1`](../tools/overnight/watchdog.ps1) |
| `hornlab-search gpu-clean [--lane gpu\|cpu]` | kill stale Julia/BEAT hosts and report VRAM usage | n | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |

## Re-score and replay

12 live entry point(s).

| Command | What it does | GPU | Source |
|---|---|---|---|
| `.venv\Scripts\python.exe tools/analysis/brief_truth_replay.py identity --out <dir>` | Brief-truth replay and frequency-fidelity laboratory (master plan WP3, 2026-11-17). | n | [`tools/analysis/brief_truth_replay.py`](../tools/analysis/brief_truth_replay.py) |
| `.venv\Scripts\python.exe tools\analysis\hifi_rescore.py --run runs\<a> --run runs\<b> ...` | Offline DSP-aware / passive "hi-fi" re-score of stored designs (NO GPU, NO solver). | n | [`tools/analysis/hifi_rescore.py`](../tools/analysis/hifi_rescore.py) |
| `.venv\Scripts\python.exe tools/analysis/offline_scores.py` | Bounded, read-only offline re-scoring pilot (R0 / M0). | n | [`tools/analysis/offline_scores.py`](../tools/analysis/offline_scores.py) |
| `.venv\Scripts\python.exe tools/analysis/queue_score_audit.py <queue> [--out ...]` | Inventory queued scoring contracts without starting workers or solving acoustics. | n | [`tools/analysis/queue_score_audit.py`](../tools/analysis/queue_score_audit.py) |
| `.venv\Scripts\python.exe tools/analysis/rescore_identity.py rescore <run dir ...> --brief <yaml> --out <dir>` | re-score stored responses under one score identity and measure the frequency noise floor | n | [`tools/analysis/rescore_identity.py`](../tools/analysis/rescore_identity.py) |
| `.venv\Scripts\python.exe tools/analysis/v8_rescore.py` | Offline objective v8 re-score + per-class tolerance calibration over the stored dataset. | n | [`tools/analysis/v8_rescore.py`](../tools/analysis/v8_rescore.py) |
| `.venv\Scripts\python.exe tools/rescore/rescore_v2.py --runs runs --out docs/evidence/objective_v2_rescore --md docs/evidence/OBJECTIVE_V2_RESCORE.md` | Offline objective v1 vs v2 re-score over stored runs. NO GPU, NO solver solve. | n | [`tools/rescore/rescore_v2.py`](../tools/rescore/rescore_v2.py) |
| `.venv\Scripts\python.exe tools/rescore/rescore_v6_v7.py --dataset C:\path\to\hornlab-search\dataset --out scratch/rescore_2026-11-12 --md docs/evidence/RESCORE_V6_V7_2026-11-12.md` | Offline objective v6 vs v7 re-score over the stored dataset. NO GPU, NO solver. | n | [`tools/rescore/rescore_v6_v7.py`](../tools/rescore/rescore_v6_v7.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.objective.replay import load_brief_context; b=load_brief_context('examples/briefs/<brief>.yaml')"` | resolve a brief YAML into the validated scoring Brief context (real loader, no solver) | n | [`hornlab_search/objective/replay.py`](../hornlab_search/objective/replay.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.objective.replay import brief_from_config; b=brief_from_config('<config>.yaml')"` | resolve a full config YAML through the real brief-resolution path (parity-exact replay) | n | [`hornlab_search/objective/replay.py`](../hornlab_search/objective/replay.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.objective.replay import replay_record; r=replay_record(meta, arrays, brief='<brief>.yaml')"` | replay one stored dataset record under a chosen brief/target without a backend | n | [`hornlab_search/objective/replay.py`](../hornlab_search/objective/replay.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.objective.replay import replay_run_dir; r=replay_run_dir('runs/<run>', '<design_hash>', brief='examples/briefs/<brief>.yaml')"` | re-score a stored run design under another brief (canonical, backend-free, parity-checked) | n | [`hornlab_search/objective/replay.py`](../hornlab_search/objective/replay.py) |

## Analyse a cohort

19 live entry point(s).

| Command | What it does | GPU | Source |
|---|---|---|---|
| `.venv\Scripts\python.exe -m hornlab_search.research build [--cutoff ...]` | Frozen, sourced research snapshot (findings, cohort inventory, attribution); also the GUI Overview "Generate research snapshot" button | n | [`hornlab_search/research/build.py`](../hornlab_search/research/build.py) |
| `.venv\Scripts\python.exe tools\analysis\cohorts.py` | Operation-specific comparability and the ATH census | n | [`tools/analysis/cohorts.py`](../tools/analysis/cohorts.py) |
| `.venv\Scripts\python.exe tools/analysis/continuation_advice.py [--run ...]` | Continuation rule (Fable plan §10.1 D8, WP 7.2 advisory) — CPU, read-only, no action taken. | n | [`tools/analysis/continuation_advice.py`](../tools/analysis/continuation_advice.py) |
| `.venv\Scripts\python.exe tools/analysis/convergence.py --run <dir> [--run <dir> ...] --out <dir>` | Best-so-far J vs valid-evaluation index for search runs. | n | [`tools/analysis/convergence.py`](../tools/analysis/convergence.py) |
| `.venv\Scripts\python.exe tools/analysis/geometry_descriptors.py [--input ...]` | Deterministic, score-free geometry descriptors for S8 discovery. | n | [`tools/analysis/geometry_descriptors.py`](../tools/analysis/geometry_descriptors.py) |
| `.venv\Scripts\python.exe tools/analysis/links.py [--run ...]` | Candidate linked knobs for one search run (feeds Group B's `links:`). | n | [`tools/analysis/links.py`](../tools/analysis/links.py) |
| `.venv\Scripts\python.exe tools/analysis/optimizer_evidence.py [--run ...]` | Composed, read-only optimizer-evidence report (P1a) — advisory only. | n | [`tools/analysis/optimizer_evidence.py`](../tools/analysis/optimizer_evidence.py) |
| `.venv\Scripts\python.exe tools/analysis/optimizer_switch.py [--run ...]` | Advisory optimizer decision report for recorded search runs; never executes a search. | n | [`tools/analysis/optimizer_switch.py`](../tools/analysis/optimizer_switch.py) |
| `.venv\Scripts\python.exe tools/analysis/parameter_activity.py [--config ...]` | Parameter/control activity ledger for a resolved native configuration (B2, M0). | n | [`tools/analysis/parameter_activity.py`](../tools/analysis/parameter_activity.py) |
| `.venv\Scripts\python.exe tools\analysis\parameter_study.py` | Parameter study report for the frozen ATH v4 candidate (S4, bo-study-v1.1). | n | [`tools/analysis/parameter_study.py`](../tools/analysis/parameter_study.py) |
| `.venv\Scripts\python.exe tools\analysis\pattern_quality_report.py runs\<run> [runs\<run> ...]` | Report-only pattern-quality CLI over stored ``response.npz`` files. | n | [`tools/analysis/pattern_quality_report.py`](../tools/analysis/pattern_quality_report.py) |
| `.venv\Scripts\python.exe tools/analysis/seed_variance.py [--group ...]` | Seed noise and honest paired comparisons for search runs. | n | [`tools/analysis/seed_variance.py`](../tools/analysis/seed_variance.py) |
| `.venv\Scripts\python.exe tools/analysis/sensitivity.py --run <dir> [--runs-dir <base>] --out <dir>` | Per-knob influence on J for one search run. | n | [`tools/analysis/sensitivity.py`](../tools/analysis/sensitivity.py) |
| `.venv\Scripts\python.exe tools/analysis/source_fidelity.py` | Source-fidelity / source-context cards for the native ATH cohort (bo-study-v1.1). | n | [`tools/analysis/source_fidelity.py`](../tools/analysis/source_fidelity.py) |
| `.venv\Scripts\python.exe tools/analysis/spectral_corpus_sweep.py [--runs-root ...]` | Corpus-wide fixed-angle spectral ripple sweep over stored runs (REPORT-ONLY). | n | [`tools/analysis/spectral_corpus_sweep.py`](../tools/analysis/spectral_corpus_sweep.py) |
| `.venv\Scripts\python.exe tools/analysis/spectral_ripple_audit.py <designs> [--band-hz ...]` | Fixed-angle spectral ripple audit over stored designs (REPORT-ONLY). | n | [`tools/analysis/spectral_ripple_audit.py`](../tools/analysis/spectral_ripple_audit.py) |
| `.venv\Scripts\python.exe tools/analysis/term_balance.py [--run ...]` | Which objective term actually carries J, per brief? | n | [`tools/analysis/term_balance.py`](../tools/analysis/term_balance.py) |
| `.venv\Scripts\python.exe tools/analysis/walls.py [--run ...]` | Bound walls of one search run and a proposed narrowed/widened box. | n | [`tools/analysis/walls.py`](../tools/analysis/walls.py) |
| `.venv\Scripts\python.exe tools/analysis/xo_loading_report.py <targets> [--out ...]` | Crossover-region loading diagnostics for stored designs (REPORT-ONLY; never a score term). | n | [`tools/analysis/xo_loading_report.py`](../tools/analysis/xo_loading_report.py) |
| `.venv\Scripts\python.exe tools\lane_speed_report.py [--runs runs] [--since 2026-11-01] [--csv out.csv]` | Solo vs concurrent solve-speed report across lanes (GPU / CPU). | n | [`tools/lane_speed_report.py`](../tools/lane_speed_report.py) |

## BO identity, encoding and metric-BO

23 live entry point(s).

**Environment exception.** `tools/bo_compare/prepare_study.py` runs on the
BoTorch/Torch/GPyTorch interpreter named in its own header
(`..\oc-wt\bo-study\bayes-venv\Scripts\python.exe`), **not** `.venv`. For the
in-repo study path use `hornlab-search study` (see `docs/BAYESIAN_STUDIES_RUNBOOK.md`);
the table row shows the historical BoTorch-venv invocation so the existing night files
stay reproducible.

| Command | What it does | GPU | Source |
|---|---|---|---|
| `.venv\Scripts\python.exe tools/analysis/bo_sensitivity.py [--training-json ...]` | Offline M2 sensitivity harness; no solver, acquisition policy or data ingestion. | n | [`tools/analysis/bo_sensitivity.py`](../tools/analysis/bo_sensitivity.py) |
| `.venv\Scripts\python.exe tools/analysis/study_cohort.py --config <yaml> --dataset <dir> --out <json>` | prepare a task-specific scalar study cohort using canonical offline replay | n | [`tools/analysis/study_cohort.py`](../tools/analysis/study_cohort.py) |
| `.venv\Scripts\python.exe tools/analysis/surrogate_validation.py [--rows ...]` | Advisory surrogate validation (offline, numpy only, never changes a default). | n | [`tools/analysis/surrogate_validation.py`](../tools/analysis/surrogate_validation.py) |
| `.venv\Scripts\python.exe tools\bench\fake_harness.py --dry-run --seed 7` | Deterministic offline fake-evaluator harness for S9 / bo-study-v1.1. | n | [`tools/bench/fake_harness.py`](../tools/bench/fake_harness.py) |
| `.venv\Scripts\python.exe tools\bo_compare\preflight_arms.py` | Read-only preflight for staged BoTorch arms (no solves, no GPU, no study created). | n | [`tools/bo_compare/preflight_arms.py`](../tools/bo_compare/preflight_arms.py) |
| `..\oc-wt\bo-study\bayes-venv\Scripts\python.exe tools\bo_compare\prepare_study.py` | Prepare ONE BoTorch study package for the matched BO-vs-CMA comparison (no solves; CPU only). | n | [`tools/bo_compare/prepare_study.py`](../tools/bo_compare/prepare_study.py) |
| `.venv\Scripts\python.exe tools/experiments/manifest.py [--overlay ...]` | Build and validate bo-study-v1.1 M2 pilot manifests (S11). | n | [`tools/experiments/manifest.py`](../tools/experiments/manifest.py) |
| `.venv\Scripts\python.exe tools\night_queue\mirror_bo_studies.py` | Mirror BO/TuRBO study solves into ordinary run folders so every CMA view shows them. | n | [`tools/night_queue/mirror_bo_studies.py`](../tools/night_queue/mirror_bo_studies.py) |
| `.venv\Scripts\python.exe tools/night_queue/refine_study_cma.py [--study-root ...]` | Warm-start a sequential CMA search from a finished BO study (preflight first). | n | [`tools/night_queue/refine_study_cma.py`](../tools/night_queue/refine_study_cma.py) |
| `.venv\Scripts\python.exe tools/night_queue/run_bo_arm.py [--lane ...]` | Prepare and execute one BO arm, refusing changed cohort files and failed preflight. | y | [`tools/night_queue/run_bo_arm.py`](../tools/night_queue/run_bo_arm.py) |
| `hornlab-search surrogate train --config <yaml> [--out surrogate.pt]` | train/propose/round the phase-2 surrogate | n | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| `hornlab-search study validate --spec <study.json>` | validated bo-study-v1.1 workflow (validate/create/analyze/propose/package/run/diagnose/export) | n | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.bo.encoding import ActiveProjection; p=ActiveProjection.from_space(space)"` | build the active-dimension projection that gives a BO study its search-space identity | n | [`hornlab_search/bo/encoding.py`](../hornlab_search/bo/encoding.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.bo.data import build_training_set; ts=build_training_set(observations)"` | build the validated BO training set (rows, bounds identity, near-duplicate rejection) | n | [`hornlab_search/bo/data.py`](../hornlab_search/bo/data.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.bo.data import build_candidate_pool; pool=build_candidate_pool(space, enc, cfg)"` | build the finite BO candidate pool from a search space | n | [`hornlab_search/bo/data.py`](../hornlab_search/bo/data.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.bo.metric_training import build_metric_training_artifact; a=build_metric_training_artifact(selection, identity_metadata=md)"` | freeze the deterministic metric-training artifact (v10/v11 component contributions) | n | [`hornlab_search/bo/metric_training.py`](../hornlab_search/bo/metric_training.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.bo.metric_model import fit_metric_model; m=fit_metric_model(artifact)"` | fit the independent-output six-component GP for metric BO | n | [`hornlab_search/bo/metric_model.py`](../hornlab_search/bo/metric_model.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.bo.metric_objective import build_metric_acquisition; acq=build_metric_acquisition(m)"` | build the qLogNEI acquisition over -sum(components) | n | [`hornlab_search/bo/metric_objective.py`](../hornlab_search/bo/metric_objective.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.bo.metric_propose import propose_metric_candidate; c=propose_metric_candidate(m, pool)"` | select one metric-BO candidate from the finite pool | n | [`hornlab_search/bo/metric_propose.py`](../hornlab_search/bo/metric_propose.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.bo.metric_identity import bounds_identity, score_identity; h=bounds_identity(enc)"` | compute/check the bounds and score identities that pin a metric-BO study | n | [`hornlab_search/bo/metric_identity.py`](../hornlab_search/bo/metric_identity.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.bo.metric_artifact import load_artifact_file; a=load_artifact_file('<artifact.json>')"` | load and checksum-verify a metric-training artifact | n | [`hornlab_search/bo/metric_artifact.py`](../hornlab_search/bo/metric_artifact.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.bo.policy import fit_and_propose; o=fit_and_propose(policy, training_set=ts)"` | dispatch one BO proposal policy (scalar/Pareto/TuRBO/metric) end to end | n | [`hornlab_search/bo/policy.py`](../hornlab_search/bo/policy.py) |
| `.venv\Scripts\python.exe -c "from hornlab_search.bo.turbo import propose_turbo; c=propose_turbo(fitted, pool, hist, state, encoding=enc, config=cfg)"` | propose the next candidate under the TuRBO trust-region policy | n | [`hornlab_search/bo/turbo.py`](../hornlab_search/bo/turbo.py) |

## Verify and compare

22 live entry point(s).

| Command | What it does | GPU | Source |
|---|---|---|---|
| `.venv\Scripts\python.exe tools/analysis/ab_compare.py [--a ...]` | Equal-budget, fixed-cost and paired A/B of two treatments. | n | [`tools/analysis/ab_compare.py`](../tools/analysis/ab_compare.py) |
| `.venv\Scripts\python.exe tools/analysis/fidelity.py [--run ...]` | Screen-vs-verify bias and within-run rank agreement. | n | [`tools/analysis/fidelity.py`](../tools/analysis/fidelity.py) |
| `.venv\Scripts\python.exe tools/analysis/lane_parity.py [--gpu ...]` | GPU vs CPU parity of stored verify responses (gate CP-7b). | n | [`tools/analysis/lane_parity.py`](../tools/analysis/lane_parity.py) |
| `.venv\Scripts\python.exe tools/analysis/qd_compare.py [--a ...]` | Manifest-driven, equal-cost QD vs Pareto hypervolume comparison. | n | [`tools/analysis/qd_compare.py`](../tools/analysis/qd_compare.py) |
| `.venv\Scripts\python.exe tools\bench\compare_search_runs.py runs\serial_run runs\prefetch_run` | Compare two search run directories (e.g. pipeline_prefetch off vs on) for the WP2 gate. | n | [`tools/bench/compare_search_runs.py`](../tools/bench/compare_search_runs.py) |
| `.venv\Scripts\python.exe tools\bench\cpu_gpu_concurrent.py --config examples\osse_baseline_fusedcuda.yaml` | Pilot: one CPU-BEM lane and one CUDA lane solving DISTINCT candidates at the same time. | y | [`tools/bench/cpu_gpu_concurrent.py`](../tools/bench/cpu_gpu_concurrent.py) |
| `.venv\Scripts\python.exe tools\calibration\compare_calibration.py` | Compare the calibration night's verify runs per variant (offline). | n | [`tools/calibration/compare_calibration.py`](../tools/calibration/compare_calibration.py) |
| `.venv\Scripts\python.exe tools/geometry/klangfilm_hv_ab.py --check` | Stage A single-axis acoustic A/B: identity gate and sequential runner (no optimizer). | y | [`tools/geometry/klangfilm_hv_ab.py`](../tools/geometry/klangfilm_hv_ab.py) |
| `.venv\Scripts\python.exe tools/geometry/solve_sculpted_v11.py <case> [--import-measured ...]` | Register or solve admitted full-balloon home-900 V11 fixed meshes. | y | [`tools/geometry/solve_sculpted_v11.py`](../tools/geometry/solve_sculpted_v11.py) |
| `.venv\Scripts\python.exe tools/geometry/verify_rolled_rect_night.py [--night ...]` | Verify rolled-rectangle night results with their required opt-in geometry adapter. | n | [`tools/geometry/verify_rolled_rect_night.py`](../tools/geometry/verify_rolled_rect_night.py) |
| `.venv\Scripts\python.exe tools/m3_measurement_pack.py [--radii ...]` | GPU MEASUREMENT PACK on STORED designs (WP5a/b/c, WP7, WP8). | y | [`tools/m3_measurement_pack.py`](../tools/m3_measurement_pack.py) |
| `.venv\Scripts\python.exe tools/night_queue/fidelity_pairs.py` | Fixed-design fidelity checks for the acoustic-truth ladder. | y | [`tools/night_queue/fidelity_pairs.py`](../tools/night_queue/fidelity_pairs.py) |
| `.venv\Scripts\python.exe tools\night_queue\verify_night_jobs.py --night <night>` | Verify the top-N designs of search jobs that ran EARLIER IN THE SAME NIGHT. | y | [`tools/night_queue/verify_night_jobs.py`](../tools/night_queue/verify_night_jobs.py) |
| `.venv\Scripts\python.exe tools/rescore/gate_audit.py` | audit stored runs against the canonical owner gates (zero GPU, zero solver) | n | [`tools/rescore/gate_audit.py`](../tools/rescore/gate_audit.py) |
| `.venv\Scripts/python.exe tools/system/bl_smoke.py` | Boundary Lab machine smoke: read-only probe (default) or a real vented generation. | n | [`tools/system/bl_smoke.py`](../tools/system/bl_smoke.py) |
| `.venv\Scripts\python.exe tools/system/evidence_case.py` | Derive a fresh, provenance-recorded system case from an existing staged project. | y | [`tools/system/evidence_case.py`](../tools/system/evidence_case.py) |
| `.venv\Scripts\python.exe tools/system/placement_compare.py [--case ...]` | Compare the per-excitation Boundary Lab results of the three staged placements. | n | [`tools/system/placement_compare.py`](../tools/system/placement_compare.py) |
| `.venv\Scripts/python.exe tools/system/real_bl_lane.py --real` | One-command REAL Boundary Lab lane (CPU only): probe -> stage -> validate -> tiny solve. | n | [`tools/system/real_bl_lane.py`](../tools/system/real_bl_lane.py) |
| `hornlab-search selftest --analytic` | does the solver agree with closed-form physics or the CPU cross-check? | y | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| `hornlab-search verify --run <dir> [--top 5]` | re-solve a run's top designs at verify fidelity | y | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| `hornlab-search compare <run_a> <run_b>` | report metric differences between two solved runs | n | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| `hornlab-search ab-bl export\|solve\|import\|compare\|demo --fake` | A/B check a Hornfab design against Boundary Lab | y | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |

## Render and report

19 live entry point(s).

| Command | What it does | GPU | Source |
|---|---|---|---|
| `.venv\Scripts\python.exe tools\analysis\overview_snapshot_spec.py --days 14 --out runs\analysis\overview_spec.yaml` | A report_day spec built from the live Overview rollup (Overview phase 4, WP4.1). | n | [`tools/analysis/overview_snapshot_spec.py`](../tools/analysis/overview_snapshot_spec.py) |
| `.venv\Scripts\python.exe tools/analysis/report_day.py --spec <yaml> --out <dir>` | run every Group A analysis from one YAML spec into one REPORT.md | n | [`tools/analysis/report_day.py`](../tools/analysis/report_day.py) |
| `.venv\Scripts\python.exe tools/atlas/build_atlas.py --out docs/atlas` | Project atlas: one self-contained HTML report over every search the project has run. | n | [`tools/atlas/build_atlas.py`](../tools/atlas/build_atlas.py) |
| `.venv\Scripts\python.exe tools/cad/meh.py [--out ...]` | Multiple-entry horn (MEH) L1 CAD: horn + box + flush mid-port patches -> labelled STEP. | n | [`tools/cad/meh.py`](../tools/cad/meh.py) |
| `.venv\Scripts\python.exe tools\cad\multicell.py` | Multicell (WE/Altec-style) horn AIR volume -> STEP with named faces. | n | [`tools/cad/multicell.py`](../tools/cad/multicell.py) |
| `.venv\Scripts\python.exe tools/cad/plughorn.py [--out ...]` | Cone mid horn with a central axe-head plug (Funktion-One Evo SH style) -> labelled STEP. | n | [`tools/cad/plughorn.py`](../tools/cad/plughorn.py) |
| `.venv\Scripts\python.exe tools/cad/sat_dump.py reference/funktion-one/dxf2000/X.dxf out.json` | Read the ACIS body of a DXF 3DSOLID (text SAT, e.g. a DWG converted to DXF R2000), dump vertices/edges/faces to JSON for reference-CAD study. | n | [`tools/cad/sat_dump.py`](../tools/cad/sat_dump.py) |
| `.venv\Scripts\python.exe tools/gui/browser_check.py [--base ...]` | Browser check for the hornlab-search GUI (handoff GUI_COMPLETION_HANDOFF_2026-11-19 §8.6). | n | [`tools/gui/browser_check.py`](../tools/gui/browser_check.py) |
| `.venv\Scripts\python.exe tools/loudness_report.py --night runs/nights/v4_resume_2026-10-27` | Horn loudness and horn x driver sensitivity from STORED solves. NO GPU, NO solver. | n | [`tools/loudness_report.py`](../tools/loudness_report.py) |
| `.venv\Scripts\python.exe tools/render/cad_edges.py examples/typologies/cone_plughorn_2026-10-28/X.yaml out.npz` | Dump the true CAD edges of a ``plughorn`` design as polylines (mm) for drawing-style renders. | n | [`tools/render/cad_edges.py`](../tools/render/cad_edges.py) |
| `.venv\Scripts\python.exe tools/render/compose.py --renders scratch/r --layout stack --views a,b --loudness --out scratch/r/cards` | Compose rendered views (tools/render/render_views.py) into report images. Runs in the project venv. | n | [`tools/render/compose.py`](../tools/render/compose.py) |
| `.venv\Scripts\python.exe tools/render/render_lines.py` | Drawing-style renders: white faces of a mesh.msh + its true CAD edges (from ``cad_edges.py``). | n | [`tools/render/render_lines.py`](../tools/render/render_lines.py) |
| `.venv\Scripts\python.exe tools/render/render_views.py <targets> [--out ...]` | Render horn meshes to PNG views (pyvista, off-screen). Runs in the viz env, NOT the project venv. | n | [`tools/render/render_views.py`](../tools/render/render_views.py) |
| `.venv\Scripts\python.exe tools\system\assembly_render.py` | Render what Boundary Lab actually compiled for one staged horn+cabinet case. | n | [`tools/system/assembly_render.py`](../tools/system/assembly_render.py) |
| `.venv\Scripts\python.exe tools/visualizations/prepare_capture.py <repo> <out>` | Package saved solved meshes in HornLab's browser playback format. | n | [`tools/visualizations/prepare_capture.py`](../tools/visualizations/prepare_capture.py) |
| `.venv\Scripts\python.exe tools/visualizations/prepare_improvements.py <repo> <out>` | Package saved solved meshes in HornLab's browser playback format. | n | [`tools/visualizations/prepare_improvements.py`](../tools/visualizations/prepare_improvements.py) |
| `.venv\Scripts\python.exe tools/visualizations/verify_flash.py <video> [--improvements ...]` | Verify that only improvement frames flash lime in a HornLab evolution reel. | n | [`tools/visualizations/verify_flash.py`](../tools/visualizations/verify_flash.py) |
| `hornlab-search report <run_dir> [--out report.html] [--top 5]` | build the HTML report for a run directory | n | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| `hornlab-search gui [--port 8765]` | serve the local web GUI over runs, briefs and jobs | n | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |

## Data and archive

21 live entry point(s).

| Command | What it does | GPU | Source |
|---|---|---|---|
| `.venv\Scripts\python.exe tools/analysis/archive_run.py --out docs/evidence/runs/<bundle> runs/<id> ...` | Archive finished run directories under docs/evidence/runs for cloud/GitHub review. | n | [`tools/analysis/archive_run.py`](../tools/analysis/archive_run.py) |
| `.venv\Scripts\python.exe tools/analysis/cache_producer_audit.py [--cache-root ...]` | Read-only cache producer compatibility audit. | n | [`tools/analysis/cache_producer_audit.py`](../tools/analysis/cache_producer_audit.py) |
| `.venv\Scripts\python.exe tools\analysis\catalog.py` | Read-only experiment catalog over ``dataset/`` shards | n | [`tools/analysis/catalog.py`](../tools/analysis/catalog.py) |
| `.venv\Scripts\python.exe tools/analysis/classify_recipes.py [--runs-root runs] [--out <dir>]` | which stored legacy design recipes still rebuild? | n | [`tools/analysis/classify_recipes.py`](../tools/analysis/classify_recipes.py) |
| `.venv\Scripts\python.exe tools/data/dedupe_runs.py` | Replace byte-duplicate heavy run files with hardlinks to their cache entry. | n | [`tools/data/dedupe_runs.py`](../tools/data/dedupe_runs.py) |
| `.venv\Scripts\python.exe tools/data/doctor.py` | Read-only integrity report for hornlab-search's local data stores. | n | [`tools/data/doctor.py`](../tools/data/doctor.py) |
| `.venv\Scripts\python.exe tools\data\ingest_foreign.py --lab collin` | Ingest foreign rows from another lab: validate, tag, and write a CP-7b parity report. | n | [`tools/data/ingest_foreign.py`](../tools/data/ingest_foreign.py) |
| `.venv\Scripts\python.exe tools/data/keepers.py` | Derived, regenerable "keepers" index over the append-only dataset store. | n | [`tools/data/keepers.py`](../tools/data/keepers.py) |
| `.venv\Scripts\python.exe tools\data\merge_lane_dataset.py --src dataset_cpu --dst dataset` | Merge the CPU lane's dataset into the main dataset, gated on the lane-parity report (D.3). | n | [`tools/data/merge_lane_dataset.py`](../tools/data/merge_lane_dataset.py) |
| `.venv\Scripts\python.exe tools\data\system_cases.py` | Export the HORN + VENTED-WOOFER SYSTEM solve/screen data as a portable, regenerable bundle. | n | [`tools/data/system_cases.py`](../tools/data/system_cases.py) |
| `.venv\Scripts\python.exe tools/data/system_solve_results.py [--root ...]` | Export every stored horn+woofer solve result to portable CSV for cloud review. | n | [`tools/data/system_solve_results.py`](../tools/data/system_solve_results.py) |
| `.venv\Scripts\python.exe tools\data\top_designs.py` | Export the best GPU-solved horn designs per typology and score set. | n | [`tools/data/top_designs.py`](../tools/data/top_designs.py) |
| `.venv\Scripts\python.exe tools\export_campaign_tables.py --night runs/nights/v4_overnight_2026-10-27 --out docs/data/campaign_v4_2026-10-27` | Export compact, analysis-ready tables from a campaign's runs (no meshes, no raw acoustic responses). | n | [`tools/export_campaign_tables.py`](../tools/export_campaign_tables.py) |
| `.venv\Scripts\python.exe tools/export_config.py --run runs/<run_dir> --top 10` | Export the exact hornlab_mesher config for a run's top designs (no solves, no meshes). | n | [`tools/export_config.py`](../tools/export_config.py) |
| `.venv\Scripts\python.exe tools/gen_param_catalog.py --write` | Generate / check the parameter catalog artifacts. | n | [`tools/gen_param_catalog.py`](../tools/gen_param_catalog.py) |
| `.venv\Scripts\python.exe tools/hf_sync.py [--out ...]` | Two-way Hugging Face sync between labs: pack / push / pull (+ legacy whole-repo upload). | n | [`tools/hf_sync.py`](../tools/hf_sync.py) |
| `.venv\Scripts\python.exe tools/system/audit_saved_horns.py --limit 60 --json` | Read-only saved-horn audit CLI (``hornlab_search.system`` Tier 0). | n | [`tools/system/audit_saved_horns.py`](../tools/system/audit_saved_horns.py) |
| `.venv\Scripts\python.exe tools/system/gui_system_job.py <case> [--preset ...]` | Thin argv bridge for Horn + woofer GUI system jobs. | y | [`tools/system/gui_system_job.py`](../tools/system/gui_system_job.py) |
| `.venv\Scripts\python.exe tools/system/verify_evidence_quotes.py` | Verify quoted evidence blocks in a Markdown document against their source files. | n | [`tools/system/verify_evidence_quotes.py`](../tools/system/verify_evidence_quotes.py) |
| `hornlab-search dataset stats\|verify\|export` | inspect, verify or export the training dataset | n | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |
| `hornlab-search export-step --run <dir> [--top 3] [--out DIR]` | export STEP solids (mm) of a run's top designs or a config seed | n | [`hornlab_search/cli.py`](../hornlab_search/cli.py) |

## Historical tools

Kept for provenance. **Do not start here.** The four dead bench tools carry an explicit `LEGACY BENCH ... NON-production path` banner; the 24 one-offs answer a closed question but still run.

### Dead (4) — superseded benchmark path

| Command | What it did | GPU | Source |
|---|---|---|---|
| `.venv\Scripts\python.exe tools\bench\cpu_vs_cuda_meh.py [--budget 900]` | legacy CPU-vs-CUDA MEH benchmark (non-production historical path; superseded, see docs/throughput/RUNBOOK.md) | y | [`tools/bench/cpu_vs_cuda_meh.py`](../tools/bench/cpu_vs_cuda_meh.py) |
| `.venv\Scripts\python.exe tools\bench\cuda_cpu_40designs.py [--designs 40] [--max-seconds 2400]` | legacy 40-design CUDA-vs-CPU benchmark (non-production historical path; superseded) | y | [`tools/bench/cuda_cpu_40designs.py`](../tools/bench/cuda_cpu_40designs.py) |
| `.venv\Scripts\python.exe tools\bench\cuda_threads.py` | legacy CUDA thread-scaling benchmark (non-production historical path; superseded) | y | [`tools/bench/cuda_threads.py`](../tools/bench/cuda_threads.py) |
| `.venv\Scripts\python.exe tools\bench\full_range_cuda_cpu.py [--max-seconds 3600]` | legacy full-range CUDA-vs-CPU benchmark (non-production historical path; superseded) | y | [`tools/bench/full_range_cuda_cpu.py`](../tools/bench/full_range_cuda_cpu.py) |

### One-off (24) — dated/single-study tools

| Command | What it did | GPU | Source |
|---|---|---|---|
| `.venv\Scripts\python.exe tools/analysis/acoustic_v2_report.py [--night ...]` | Rev2 acoustic_v2 report: analyse stored responses (zero BEM) and decide the matched ablation. | n | [`tools/analysis/acoustic_v2_report.py`](../tools/analysis/acoustic_v2_report.py) |
| `.venv\Scripts\python.exe tools/analysis/home_900_review.py [--out ...]` | Replay the November 20 home-900 review cohort from immutable responses on CPU. | n | [`tools/analysis/home_900_review.py`](../tools/analysis/home_900_review.py) |
| `.venv\Scripts\python.exe tools/analysis/klangfilm_hv_ab_report.py [--cached-only]` | Stage A H/V A/B acoustic report: physical metrics, not just scores. | n | [`tools/analysis/klangfilm_hv_ab_report.py`](../tools/analysis/klangfilm_hv_ab_report.py) |
| `.venv\Scripts\python.exe tools/analysis/sculpted_v11_replay.py [--response ...]` | Replay a saved sculpted BEM response under the home-900 V11 briefs. | n | [`tools/analysis/sculpted_v11_replay.py`](../tools/analysis/sculpted_v11_replay.py) |
| `.venv\Scripts\python.exe tools/analysis/sculpted_v11_report.py [--native-run ...]` | Report matching measured home-900 V11 fixed-mesh BEM responses. | n | [`tools/analysis/sculpted_v11_report.py`](../tools/analysis/sculpted_v11_report.py) |
| `.venv\Scripts\python.exe tools\analysis\senior_plan_evidence.py --runs-glob "runs\2026111*"` | One command for every senior-plan step that needs the owner's ``runs/`` | n | [`tools/analysis/senior_plan_evidence.py`](../tools/analysis/senior_plan_evidence.py) |
| `.venv\Scripts\python.exe tools/analysis/u3_authority.py [--host ...]` | Apply the predeclared WP 4.2 equivalence and WP 4.3 authority rules (senior plan 2026-11-17). | n | [`tools/analysis/u3_authority.py`](../tools/analysis/u3_authority.py) |
| `.venv\Scripts\python.exe tools/analysis/u3_jobs.py <run> <design_hash> [--out ...]` | Write the WP 4.2 / 4.3 solve configs for one stored design (senior plan, 2026-11-17). | n | [`tools/analysis/u3_jobs.py`](../tools/analysis/u3_jobs.py) |
| `.venv\Scripts\python.exe tools\data\renumber_objective_v5_to_v7.py` | Renumber the hardened-branch objective "v5" to v7 in stored data | n | [`tools/data/renumber_objective_v5_to_v7.py`](../tools/data/renumber_objective_v5_to_v7.py) |
| `.venv\Scripts\python.exe tools/geometry/build_rolled_rect_page.py [--renders ...]` | Build the standalone rolled-rectangle geometry comparison page. | n | [`tools/geometry/build_rolled_rect_page.py`](../tools/geometry/build_rolled_rect_page.py) |
| `.venv\Scripts\python.exe tools/geometry/build_section_pucker_page.py` | Publish the section-based H/V relief seeds and measured feasibility evidence. | n | [`tools/geometry/build_section_pucker_page.py`](../tools/geometry/build_section_pucker_page.py) |
| `scratch\vizenv\Scripts\python.exe tools/geometry/check_sculpted_mesh_fidelity.py` | Measure sampled design-sheet distance to emitted wall triangles, on CPU. | n | [`tools/geometry/check_sculpted_mesh_fidelity.py`](../tools/geometry/check_sculpted_mesh_fidelity.py) |
| `.venv\Scripts\python.exe tools/geometry/hf1440_seed_gallery.py [--repo ...]` | HornFab HF1440 dual-family geometry gallery, intended for use IN Hornfab repo. | n | [`tools/geometry/hf1440_seed_gallery.py`](../tools/geometry/hf1440_seed_gallery.py) |
| `.venv\Scripts\python.exe tools/geometry/k_visual_seed_diagnostic_20261116.py [--seeds ...]` | Geometry-only diagnostic for the owner-supplied K seed pack; no meshing or solving. | n | [`tools/geometry/k_visual_seed_diagnostic_20261116.py`](../tools/geometry/k_visual_seed_diagnostic_20261116.py) |
| `.venv\Scripts\python.exe tools/geometry/plot_crowe_sections.py [--config ...]` | Plot reconstructed ES-600 section profiles and projected panel junctions. | n | [`tools/geometry/plot_crowe_sections.py`](../tools/geometry/plot_crowe_sections.py) |
| `.venv\Scripts\python.exe tools/geometry/plot_rolled_family.py` | Plot physical axis cuts and projected relief rings of the canonical family. | n | [`tools/geometry/plot_rolled_family.py`](../tools/geometry/plot_rolled_family.py) |
| `.venv\Scripts\python.exe tools/geometry/render_sculpted_meridians.py <manifest> [--out ...]` | Render CPU-only comparison sheets for sampled horn surfaces. | n | [`tools/geometry/render_sculpted_meridians.py`](../tools/geometry/render_sculpted_meridians.py) |
| `.venv\Scripts\python.exe tools/geometry/sculpted_meridians_study.py [--out ...]` | Build the CPU-only sculpted-meridian comparison and its manifests. | n | [`tools/geometry/sculpted_meridians_study.py`](../tools/geometry/sculpted_meridians_study.py) |
| `.venv\Scripts\python.exe tools/geometry/sculpted_roll_probe.py` | CPU-only R2 native truncation probe with matched-mesh source diagnostics. | n | [`tools/geometry/sculpted_roll_probe.py`](../tools/geometry/sculpted_roll_probe.py) |
| `.venv\Scripts\python.exe tools\make_v4_campaign.py [--check]` | Generate the objective-v4 copy of the 2026-10-26 campaign (briefs + typology configs). | n | [`tools/make_v4_campaign.py`](../tools/make_v4_campaign.py) |
| `.venv\Scripts\python.exe tools/night_queue/run_matched_home.py <action> [--root ...]` | Frozen-cohort home comparison. Prepare once, then run individual bounded arms. | y | [`tools/night_queue/run_matched_home.py`](../tools/night_queue/run_matched_home.py) |
| `.venv\Scripts\python.exe tools/night_queue/sculpted_cma_continue.py <lane>` | Verify the first CMA tranche and continue promising sculpted lanes to 60. | y | [`tools/night_queue/sculpted_cma_continue.py`](../tools/night_queue/sculpted_cma_continue.py) |
| `.venv\Scripts\python.exe tools/widen_campaign_boxes.py --dry-run` | Widen the 2026-10-26 campaign search boxes to physical ranges (owner ruling). | n | [`tools/widen_campaign_boxes.py`](../tools/widen_campaign_boxes.py) |
| `powershell -NoProfile -ExecutionPolicy Bypass -File tools\night_queue\refresh_loop.ps1 -Night <night> -EveryMinutes 90 -Cutoff 07:00` | keep repairing a live night's failed/stopped jobs until the cutoff | y | [`tools/night_queue/refresh_loop.ps1`](../tools/night_queue/refresh_loop.ps1) |

---

Inventory provenance: `docs/handoffs/repo_findability_2026-11-25/inventory/I4_tools.csv` (I4 report: `docs/handoffs/repo_findability_2026-11-25/reports/I4.md`). CODE_MAP additions for the 45 paths I4 found missing are in `docs/CODE_MAP.md`.
