# Queue plan from Senior Implementation Plan Rev2 (2026-11-13)

Source: owner-supplied `HORNFAB_SENIOR_IMPLEMENTATION_PLAN_REV2_2026-11-12.md` (used as a guide, not as truth).
Status: night files written and `--dry-run` clean on Linux; **not launched, not mesh-checked** (no gmsh here).

## What Rev2 asked for, and what this queue does

| Rev2 item | Taken? | Here |
|---|---|---|
| No new 300-400 eval product CMA yet | Yes | Nothing large queued |
| Matched geometry ablation, 6-12 geometries, same-core and same-mouth schemes (9.3 step 3) | Yes | 8 pinned budget-1 solves |
| One-factor fidelity ladder: mesh, radius, angles (3.5, F0) | Yes, minus frequency grid and backend in GPU night | 5 verify solves |
| CPU/GPU parity E8 before pooling | Yes, on two matched cases | CPU night, 2 solves |
| A-series metrics v2, identity layers, GUI unclip (P1, D0, V0) | Not in this queue | Code work, separate PR; results here are re-analysable later because raw arrays are cached |

## Deviations from Rev2 (senior call)

1. **Ablation before metrics_v2, not after.** The solves are cheap (about 13 GPU solves, under 1 h at measured 10-60 s/eval) and the raw balloon/cuts are cached, so v2 descriptors can be computed later with zero BEM. Waiting on P1 would idle the GPU.
2. **ATH arms added on owner call (2026-11-13).** Built from the atlas2 CORE-law seed (already researched for the atlas). Labeled 'ATH CORE-style', never a claimed ATH product (R9).
3. **Score J is NOT the readout.** Read raw H/V cuts, balloon, off-axis peak above axis, DI, and `z_throat` per pair. J is recorded only because the runner prints it.

## Experiment matrix (`examples/typologies/ablation_2026-11-13/`)

Scheme (b), same core contour (salmon_elliptical grid, 1 in, brief `organic_rollback_1in`, 90x60, 700-5500 Hz):

| Config | Lobes | Amp mm | Window start | Factor vs control |
|---|---|---|---|---|
| abl_s0_control | 12 | 0 | 0.8 | control |
| abl_s1_lip12_a3 | 12 | 3 | 0.8 | lip ripple (= salmon_ripple12 seed) |
| abl_s1_lip6_a3 | 6 | 3 | 0.8 | lobe count |
| abl_s1_lip12_a6 | 12 | 6 | 0.8 | amplitude |
| abl_s2_wall12_a3 | 12 | 3 | 0.5 | upstream wall relief (axial start) |

Scheme (a), same mouth outline (SAWMOD control OS-SE, 280x196 morph target, brief `sawmod_control_1in_100x70`):
`abl_m_rate4` (published control), `abl_m_rate2`, `abl_m_rate8`. Factor: morph evolution rate (Rev2 S3).
Backend forced to `beat_cuda` (the source config says `beat_metal`).

Scheme (a), ATH azimuth law, same 399x399 morph target (brief `native_ath_core_2in_v4_atlas2`, 2 in, full model, slower 40-60 s/eval):
`ath_a0_control` (all azimuth amplitudes 0), `ath_a1_core` (CORE law), `ath_a1_sf_only`, `ath_a1_cos_only`, `ath_a2_hex` (superformula m=6 petals).
Note: `morph_allow_shrinkage: 0`, so the smooth control's raw mouth may exceed 399 mm; check bbox in shape_check and report it.

Fidelity ladder on `abl_s0_control`, all `--mode verify`, one factor each: base epw 8 / 73 angles / 2 m;
`fid_epw6`, `fid_epw10`, `fid_dist8m` (Fraunhofer check, Rev2 3.2), `fid_ang145`.

## Night files (`docs/queue/`, copy to `runs/nights/` to launch)

- `rev2_gpu_ablation_2026-11-13.yaml`: 18 jobs, lane gpu, about 1.5-2 h.
- `rev2_cpu_parity_2026-11-13.yaml`: 2 jobs, lane cpu, `beat_cpu`, `cache_cpu`/`dataset_cpu`. Pairs with GPU `abl_s0_control` and `abl_m_rate4`.

## Launch checklist (owner machine)

1. `git pull`, then copy both yaml files into `runs\nights\`.
2. Mesh-check: `.venv\Scripts\python.exe tools/shape_check.py examples/typologies/ablation_2026-11-13/*.yaml`. Watch `abl_s1_lip12_a6` (6 mm ripple) and `fid_epw10` against dof caps (screen 5000, verify 7000). If one fails, drop that job, do not raise caps.
3. `--dry-run` each night file.
4. Pre-flight per hornlab-night-queue skill (no live runner, VRAM baseline, `runs/.gpu.lock`).
5. Launch GPU night via `launch_detached.ps1` + `queue.ps1`; CPU night only once the lane-aware runner is confirmed (no image-name julia kill in `run_campaign_night.py`).

## Decision rule (pre-declared)

- A ripple/morph arm "changes the field" only if, against its matched control, the change in largest off-axis peak or in-beam p95-p05 spread exceeds the fidelity-ladder spread for the same metric. Otherwise: record negative, stop that mechanism.
- If `fid_dist8m` beamwidth/DI differs materially from 2 m, all historical 2 m balloon claims for >400 mm mouths get a `far_field_validated: false` label.
- If CPU vs GPU |dJ| and cut differences are at the ~1e-4 level seen on 2026-11-12, close E8 for these geometries.
- Only then: a bounded BO/CMA pilot (Rev2 8, 24 new BEM max), separately authorized.

## Rev2 implementation status (2026-11-13)

| Rev2 item | Status | Where |
|---|---|---|
| 3.1 Keele as heuristic, not proof | Done (labels) | `acoustic_v2.keele_estimate` (method=heuristic, binding=false); GUI K-law card note + tooltip; report html wording. Legacy `feasible_w/v` and seed derivation unchanged. |
| 3.2 finite-radius / far field | Queued + labeled | `fid_dist8m` job; every v2 analysis carries `observation_kind=finite_radius_pressure`, `far_field_validated=false` until the 8 m check says otherwise. |
| 3.3 main-lobe vs outer beamwidth | Done | `acoustic_v2.main_lobe` (first crossings, per-side censored, off-axis and outside-main peaks). Legacy `beamwidth_deg` untouched. |
| 3.3 sphere DI quadrature | Done | `sphere_weights` / `balloon_di`: one sin(theta) trapezoid path, `invalid` status instead of 0 dB. Analytic omni 0 / cardioid / dipole 4.77 dB tests. |
| 3.3 3D lobes / islands / outside power | Done | `balloon_lobes`: connected boresight region on the theta-phi grid with phi wrap, island count, outside power fraction, max above axis. |
| 3.3 GUI clipping | Done | `gui/data.py::balloon` returns `max_above_axis_db` + `clip_count_above_axis`; `balloon.js` shows an above-axis warning line per frequency and states "magnitude, not wavefront". Range is still fixed at -30 dB. |
| 5 loading / pattern-control onset | Done | `loading_onset` (Re z sustained, bracket, `missing`), `pattern_control_onset` (target +/- tol + outside-lobe limit + dwell, `not_reached`/`censored_low`). |
| 6 identity layers | Done (additive) | `dataset/identity_v2.py`: physical_solve_id = the M0 catalog formula (reused), analysis_id, score_id, study_id, compatibility(), append-only jsonl. No cache/dataset rekey. |
| 6 analysis records + replay | Done for v2 | `tools/analysis/acoustic_v2_report.py` writes `analyses.jsonl` (ids + response sha256), `RESULTS.json`, `DECISION.md`. Legacy J replay is the owner's M0 `objective/replay.py` + `offline_scores.py`. |
| 4 sculpted tracks R0/A1/A2/S1/S2/S3 | Queued | 18-job GPU night (this doc). J1 (JBL PT) and L1 (loading-to-CD) need a new generator: not done. |
| 4 Solana / SAWMOD honesty | Done (labels) | header labels on every `solana_*.yaml` and `sawmod_control_osse.yaml`; comment only, config_sha unchanged. |
| 7 E0 manifest | Done | `docs/queue/rev2_E0_manifest_2026-11-13.json` |
| E8 CPU/GPU parity | Queued | CPU night + existing `tools/analysis/lane_parity.py`. |
| 8 BoTorch M0-M2 | Owner landed separately (main 41fc6d1) | untouched here |
| MEH | Owner-paused | untouched |

## Still open (named, not hidden)

- GUI balloon range selector (-30/-40/-60 dB); needs a `min_db` API param.
- Frequency-grid factor in the fidelity ladder (needs a brief copy with a denser grid).
- Mouth phase / aperture field: only where `p_h`/`p_balloon` are stored; reported as `available.phase`.
- J1 JBL-PT and L1 loading-to-CD generators (new geometry adapter; R9 research first).
- Physical-manifest sweep over the whole historical archive (the M0 catalog already covers physical ids).
