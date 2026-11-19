# B1 mesh convergence — first results (Fable WP 2.2/2.3, R5; owner box 2026-11-18)

**Status: 8/8 probes COMPLETE and clean (5 fold-warm batch 1 + 3 ext-throat batch 2); no Shared-Usage
spill on any probe; the two leaders (3a1038da45d0 v7, 9fcd21fc1904 v8) remain OUTSIDE the mesh floor
on this card (infeasible at epw 12, per the feasibility packet).**

## How it ran

Tool: `tools/night_queue/fidelity_pairs.py --refine-epw-factor 2 --teardown-per-design --record-vram
--gain-threshold 0.0057` (each design a fresh process, memwatch wrapper recording baseline/peak
VRAM + host shared/dedicated). Reference = the STORED screen row (no re-solve); refined = the same
screen grid, only `mesh.epw` 6 → 12. Queue mechanics: folded into the live night `cd_rrect_2026-11-17`
as `_rc2` ids (see the continuity entry for the queue-jump + the backend-object tool fix that burned
the first five ids), then `_batch2` ids for the ext-throat probes. One caveat from the runner's env:
the memwatch lines above quote the runner's post-hygiene view; per-probe peaks are recorded in the
memwatch JSONs (`runs/nights/b1_mesh_2026-11-18/memwatch/*.json`).

## Per-design results [measured; source runs/b1_mesh_2026-11-18/refine.json + b1_probes_table.json]

| probe | family | ref J | refined J | dJ | dof (x2) | mesh-sensitive (>0.0057) |
|---|---|---|---|---|---|---|
| 2f7307c06023 | fold-warm | 4.14130 | 4.12597 | −0.01533 | 14519 | **yes** |
| 507e7257c091 | fold-warm | 3.94852 | 3.92328 | −0.02523 | 14545 | **yes** |
| ced63c6a01a1 | fold-warm | 3.82511 | 3.80643 | −0.01868 | 14762 | **yes** |
| 688ffe811b6a | fold-warm | 3.89230 | 3.87310 | −0.01920 | 14881 | **yes** |
| 78f599e8a1d2 | fold-warm | 4.03174 | 4.02840 | −0.00334 | 14705 | no |
| 766c9b1ba8a9 | ext-throat | 3.29948 | 3.29136 | −0.00812 | 14270 | **yes** |
| 508f907726d3 | ext-throat | 3.30515 | 3.30225 | −0.00290 | 15388 | no |
| b996da551021 | ext-throat | 3.57428 | 3.56657 | −0.00770 | 15336 | **yes** |

All 8 `grid.same_grid = true` (frequency identity unchanged); every probe verified its teardown
(`teardown_verified` in the records); `exit 0` on all eight runner END lines
(`runs/overnight/queue_cd_rrect_2026-11-17.log`, UTF-8).

## VRAM (the spill gate / WP 2.2 verdict)

- Desktop baseline at each probe ≈ 729-787 MiB (`memory.used`, recorded per job in the memwatch JSON).
- Refined-solve peaks ≈ 2.6-3.0 GB dedicated; **host shared usage 80 MiB on every probe** — no probe
  spilled (the gate is ~512 MiB shared). **R5's conditional batch 2 therefore ran immediately after
  batch 1** (3 ext-throat probes, all clean).
- Conclusion for the card: the x2 mesh tier (~14.3-15.4 k quarter DOF) fits comfortably; the
  infeasibility of the two leaders is a *mesh-geometry* refusal (symmetry-plane slivers), not VRAM.

## WP 2.3 — the combined noise floor per identity

Record file: `floor_record.json` (this directory). Mesh part = sd of the 8 same-grid dJ values =
**0.00768 J** (max |dJ| 0.02523, median 0.01173; 6/8 mesh-sensitive at the predeclared 0.0057
threshold). Combined floors `sqrt(freq² + mesh²)`:

| identity | freq part | combined |
|---|---|---|
| v7 (published D8 floor) | 0.130 | **0.1302** |
| v7 (this pass's top-28-pair protocol) | 0.3104 | **0.3105** |
| v10 corridor preferred_edge | 0.4677 | **0.4677** |
| v10_slope5 | 0.4863 | **0.4863** |

**Reading:** the B1 mesh term is real but small (≤0.008 J sd; ≤0.025 J per-design) — every identity's
floor stays frequency-dominated, and the epw 6 → 12 mesh refinement moves J by up to 0.025 J, i.e.
~5-40× below either floor number. Practical consequences: (a) stored screen-J rankings at the floor
scale are mesh-robust; (b) per-design dJ claims smaller than 0.025 J must still carry the
mesh-sensitive flag; (c) the v7 0.310-vs-0.13 protocol tension (NOTES item 3) is unchanged by B1 —
both v7 rows are published so downstream callers pick per the senior ruling.

## What B1 does NOT do

- It does not cover the v7 leader `3a1038da45d0` or the v8 incumbent `9fcd21fc1904` (mesher refuses
  epw 12) — the two most-referenced designs still stand on the frequency floor alone [recorded].
- It does not re-measure the frequency floor (B1f was dropped, R5) and does not change any stored
  row, J or config_sha.
- Per-design records: `b1_probes_table.json` (compact) and `runs/b1_mesh_2026-11-18/refine.json`
  (full, incl. per-term deltas and memwatch JSON paths).
