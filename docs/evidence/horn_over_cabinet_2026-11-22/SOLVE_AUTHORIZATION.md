# Solve authorization — horn-over-cabinet assembly, 2026-11-22

This is the scoped authorization record for the bounded CPU solves run after the
assembly-pose and collision seam repair. It exists because `reference.solve` refuses to
start without an explicit `authorized_by` string; it is not a blanket permission.

## Who / why

- **Requester:** owner, in the 2026-11-22 senior handoff *HornFab senior engineering
  handoff: Boundary Lab reuse, horn-over-cabinet assembly, and solve readiness*.
  Verbatim: "Proceed autonomously with safe inspection, targeted implementation and
  testing. Use the existing solve-authorization process for bounded simulations."
- **Scope approved there:** "ready to pursue bounded geometry and per-excitation research
  solves once the assembled coordinates and clearance are independently verified"
  (§ release decision); Stage C1 smoke and C2 placement control; **not** physical
  two-way system ranking.
- **Executing agent:** local senior engineering agent (this session).

## Cases

Experiment `hf_overhang_2026-11-22`, three staged and BL-validated cases:

| label | case id | translation (mm) | layout | support | exact clearance |
|---|---|---|---|---|---|
| P1 above | `20261122T212531Z-assembly-21700-98b4310e` | (0, 369.673, 0) | above | seated | PASS, AABB-separated |
| P2 overhang | `20261122T212619Z-assembly-32880-4bbd22ee` | (0, 268.674, 0) | seated_overhang | seated | PASS, 3.000 mm exact |
| P3 overhang forward | `20261122T212630Z-assembly-36576-7dee2536` | (0, 268.674, 40) | seated_overhang | unmodeled cantilever | PASS, 37.121 mm exact |

All three share the same cabinet, driver, port, horn mesh, source group and scale. Only
the pose differs.

## Backend, frequency and resource budget

- Backend: **`beat_cpu` only**. The GPU lane is held by another agent's live search night
  (`hornfab_round3_2026-11-22`); no GPU solve is authorized here and none is attempted.
- Smoke: 3 frequencies (700 / 1000 / 1400 Hz), 5 probes at 2 m. Measured reference cost
  for this mesh pair: ~27 s per 3 frequencies on `beat_cpu`.
- Placement: 21 log-spaced frequencies 400–2500 Hz, 5 probes, project observations
  included. Measured reference cost: ~224 s per 25 frequencies, so ~190 s per case.
- Hard stops: one case at a time, sequential; abort on non-finite complex results, port-id
  mismatch, or a clearance / geometry-hash mismatch.

## What the results may and may not be used for

- **May** be used for: per-excitation geometry and placement comparison; directivity and
  radiation changes caused by the mouth overhang; whether a mouth hanging in front of the
  cabinet changes the horn's own polar response.
- **May not** be used for: a physical combined two-way SPL curve, sensitivity, crossover
  ranking, or any "system score". The horn channel is a 1 m/s prescribed-velocity surface
  and the woofer channel is a 2.83 V electrical drive; combining them without a
  frequency-dependent complex horn transfer is illustrative only and must carry that
  label (`illustrative_mixed_reference`).

Signed by the executing agent against the owner directive above.

---

# C4 addendum — mesh sensitivity, 2026-11-22

Added under the same owner directive, §2 ("C4: run the bounded numerical confidence
experiment") and §6 ("Continue bounded CPU geometry and independent-excitation experiments
through the existing local solve-authorization process").

## Authorisation string

Every `reference.solve` call in this sub-campaign passes exactly:

```
owner directive 2026-11-22 C4 mesh-sensitivity: hf_overhang_2026-11-22 P2b pose fixed (dy 268.674 dz 13), beat_cpu, 3 mesh levels x 10 freqs, per-excitation only, no system ranking
```

## Fixed inputs (must be identical in all three cases)

| item | value |
|---|---|
| pose | `system_runs/poses_2026-11-22/p2b_overhang_dz013.json` (dy 268.674157, dz 13.0, frame at center_y 100 mm) |
| cabinet | 320 × 500 × 360 mm, wall 18 mm, all vented overrides as `vented_overrides.json` |
| driver | `driver_diameter_m` 0.200, `driver_y_m` 0.100, cone 40 mm, surround 12 mm, cap 50 mm |
| port | length 220 mm, area 0.002827433388 m², nfr 0.12, roundover 8 mm, wall 3 mm, y −130 mm |
| horn | `lecleach_rollback_1in_v6_9e02db06ecc3`, group `SD1D1001`, scale 1.0, mesh sha256 `9b4057c2…9815d` |
| backend | `beat_cpu` |
| probes | the five 2 m project-frame probes of `request_placement.json` |
| excitations | `vented/voltage`, `excitation:horn` |

## Varied inputs (the whole experiment)

Only the BL vented-generator mesh controls, at three levels:

| level | `mesh_size_m` | `detail_size_m` | ratio vs L0 |
|---|---|---|---|
| L0 | 0.030 | 0.0090 | 1.000 (the existing 21-frequency reference mesh) |
| L1 | 0.021 | 0.0063 | 1.429 |
| L2 | 0.015 | 0.0045 | 2.000 |

The **horn mesh is imported unchanged at every level**; refinement touches only the cabinet
FEM/BEM surface. This must be recorded (horn sha256 identical across levels).

## Frequency grid (10 points, 700–1600 Hz)

`700, 800, 900, 1000, 1050, 1100, 1150, 1250, 1400, 1600` Hz.

Rationale: the crossover-region null previously observed near **1077 Hz** is bracketed by
1050/1100 Hz samples; 1150/1250 Hz detect a null that moves upward under refinement. Points
inside a deep null are reported separately with amplitude gating and never dominate ordinary
phase RMS.

## Resource budget and hard stops

- Three cases, strictly sequential, one `blab project solve` at a time on `beat_cpu`.
- Estimated cost: L0 ≈ 220 s, L1 ≈ 350 s, L2 ≈ 600 s for 10 frequencies (baseline measured
  22 s/frequency at L0 for 21 frequencies, 460 s).
- Abort a level (record the partial run dir, do not delete it) if any single frequency
  exceeds 480 s, or if the run reports a non-finite complex result, a port-id mismatch, or a
  geometry/horn-sha mismatch against the values above.
- No GPU solve. GPU lane remains held by `hornfab_round3_2026-11-22`.

## What C4 may conclude

- A **mesh sensitivity** statement: which reported quantities (horn on-axis magnitude, horn
  polar, woofer on-axis magnitude, phase away from nulls, null location/depth) move by less
  than the observed inter-level change.
- With three levels, a **provisional convergence** label is allowed, but only where the
  level-to-level change decreases with refinement; otherwise the honest label is
  `MESH_SENSITIVITY_CHECK`.
- Still forbidden: physical combined SPL, sensitivity, crossover ranking or any system score.

---

# N-series addendum — placement control on the selected D cabinet (not yet executed)

Pre-authorized by the same owner directive (§6: "proceed with a small set of physically legal
placement alternatives using the same selected cabinet"), to be run only after a separate GO.

## Authorization string to pass

```
owner directive 2026-11-22 N-series placement control: D cabinet 420x620x420, P2b-class horn, beat_cpu, mesh L1 21/6.3, 10 freqs, per-excitation only, no system ranking
```

## Fixed inputs

| item | value |
|---|---|
| cabinet | 420 x 620 x 420 mm, wall 18 mm, 114 mm net 85.689 L (BL-generated, `hf_d2_cabinet_2026-11-22`) |
| driver | moving diameter 0.2605 m, cone 40 mm, surround 12 mm, cap 50 mm, `driver_y_m` 0.098 |
| port | length 220 mm, area 0.002827433388 m2, NFR 0.12, roundover 8 mm, wall 3 mm, `port_y_m` -0.130 |
| horn | `lecleach_rollback_1in_v6_9e02db06ecc3`, group SD1D1001, sha256 `9b4057c2...9815d` |
| mesh | L1: `mesh_size_m` 0.021, `detail_size_m` 0.0063 |
| backend | `beat_cpu` only |
| request | `request_c4_mesh_10f.json` (700/800/900/1000/1050/1100/1150/1250/1400/1600 Hz, 5 probes) |

## The three cases

| label | translation mm | exact clearance | support |
|---|---|---|---|
| N1 | (0, 328.674, 13) | 10.440 mm | `unmodeled_cantilever` |
| N2 | (0, 328.674, 40) | 37.121 mm | `unmodeled_cantilever` |
| N3 | (0, 334.674, 0) | 8.963 mm | `seated_on_cabinet_top` |

All three were pre-resolved with `resolve_pose(..., driver_frame={frame_od 315.2,
depth_behind_baffle 140.6, center_y 98})`. N3's closed-form minimum (`dy = 328.674157`) clears
by exactly 3.0000 mm and rounds to a 2.99984 mm refusal; `334.674` is the robust value.

## Budget and stops

- Sequential, one case at a time. L1 measured 331 s for 10 frequencies, so ~6 min per case plus
  staging; abort a case if any frequency exceeds 480 s (L3 at 10 mm cost 520-633 s per
  frequency, so do not go finer than L1 here).
- Report the horn channel as a placement effect (mesh-stable, §5.6) and the woofer channel as
  band median + gated RMS only; null bins are locations/depths, never placement deltas.
- Still forbidden: physical combined SPL, sensitivity, crossover ranking, any system score.
