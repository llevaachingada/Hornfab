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
2. **No ATH azimuth-law or petal arm yet.** Those need a reference audit (Rev2 4, R9 gate). The lip/wall ripple generator and the SAWMOD morph already exist and are pinned to published or documented seeds.
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

Fidelity ladder on `abl_s0_control`, all `--mode verify`, one factor each: base epw 8 / 73 angles / 2 m;
`fid_epw6`, `fid_epw10`, `fid_dist8m` (Fraunhofer check, Rev2 3.2), `fid_ang145`.

## Night files (`docs/queue/`, copy to `runs/nights/` to launch)

- `rev2_gpu_ablation_2026-11-13.yaml`: 13 jobs, lane gpu.
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
