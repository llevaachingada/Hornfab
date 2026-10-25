# Typology smoke matrix (S1a expansion configs) — 2026-10-25

The five NEW typology configs `abcbebf` shipped (all uncatalogued; C4 pending backend-side) had
ZERO GPU evidence — this pass ran one `run --mode screen` seed smoke each, M4 pattern: fresh
`--cache-dir scratch\gsmoke_cache_<lane>` per job, `hornlab-search gpu-clean` before/after every
job, ONE GPU job at a time (CLI lock; no `--force`), external-process VRAM poll (2 s spacing,
`nvidia-smi --query-gpu=memory.used`) into `scratch\gsmoke_2026-10-25\vram_<name>.csv`,
logs via `cmd /c "> log 2>&1"` capture, interpreter `.venv\Scripts\hornlab-search.exe`.
**Suite at this tree: offline 1448/0/0/0** (`runs/gui_pass2_baseline/suite.xml`).

## The matrix (honest rows; a refusal is a result, not a machinery failure)

| # | Config | Result | dofs / tris | Seed J (screen 12 pts) | Solve wall | VRAM baseline → peak (MiB) | Run dir |
|---|---|---|---|---|---|---|---|
| 1 | `biradial_keele` | **OK** | 2086 dofs | 22.9837 (cov 13.21, rip 6.007, di 1.122, dislope 3.632, flat 3.23; n_nan 0; balloon DI) | 13.1 s | 1301 → 2427 | `runs/20261025T182145Z-screen-fe609a` |
| 2 | `qtw_waveguide` | **OK** | 1616 dofs | 37.4656 (cov 15.88, rip 5.799, di 1.009, dislope 27.33, flat 3.633; n_nan 0; balloon DI) | 11.5 s | 1334 → 2104 | `runs/20261025T182237Z-screen-1e1d6e` |
| 3 | `lecleach_asym_odd` (full ring) | **OK** | 2815 dofs | 60.1446 (cov 23.16, rip 3.339, di 0.486, dislope 64.33, flat 2.612, load 0.05997; n_nan 0; balloon DI) | 10.6 s | 1337 → 3147 | `runs/20261025T182334Z-screen-dc8b5d` |
| 4 | `salmon_x_signed` | **RUN FAILED — mesh_too_large (seed)** | 14,414 tris vs effective limit 11,275 | J 1000 (penalty; nothing solved) | — | 1345 → 1605 | `runs/20261025T182430Z-screen-643205` |
| 5 | `salmon_ripple12` | **RUN FAILED — mesh_too_large (seed)** | 5358 dofs (10,504 tris) vs the 5,000 screen cap for quadrants '14' | J 1000 (penalty; nothing solved) | — | 1388 → 1716 | `runs/20261025T182557Z-screen-8a8752` |

Every row's VRAM baseline is quoted from the pre-job `nvidia-smi`; the full sample series is in
`scratch\gsmoke_2026-10-25\vram_*.csv`; every job's full log sits in `scratch\gsmoke_2026-10-25\<name>_a.log`.
Final `gpu-clean` pass after the matrix: project processes killed (2 stale), VRAM 1489 MiB (desktop
residual, no julia alive).

## Findings (all owner-gated — nothing altered)

1. **The three meshing-capable kinds are seed-solvable under the screen caps**: biradial_keele
   (2086 dofs), qtw_waveguide (1616), lecleach_asym_odd (2815, full ring well under 5,000). The
   lecleach_asym full-span ring bills ~4× the quarter as predicted and still fits — the S1a
   capability claim measured on the GPU.
2. **`salmon_x_signed`'s shipped SIGN-DEMO seed is not buildable under its brief**: the corner-in
   seed (g_x_amp −0.25) overshoots the organic_rollback_1in envelope depth (z-span 332.47 mm vs
   260 + 15 = 275 mm allowance; overshoot estimate 0.2201 — pinned by
   `tests/test_design_generators_grid_signed_and_ripple_configs.py::test_x_signed_seed_pins_the_real_envelope_truth`)
   and the freestanding shell refines past the mesh limit
   (14,414 tris > 11,275; wall-clearance guard warns). The SIGNED x-amp machinery itself is
   test-proven (the full-ring/rows tests march −0.25 exactly as recorded); **PROPOSAL**: reseed the
   demo config (smaller |x_amp|, larger g_stop, or a wider brief) so the demo materializes — owner's
   call; the config header already self-declares as a sign demo.
3. **`salmon_ripple12`'s shipped seed exceeds the screen dof cap**: 5,358 dofs > 5,000 for
   quadrants '14' (half-span, 12 lobes at the ripple window). The kind passes offline (march +
   resolution guard, 8/8). **PROPOSAL**: a lower-seed variant (e.g. fewer lobes or a wider stop /
   coarser n_phi honoring the ≥4-samples-per-lobe bar) or run the ripple on the verify tier
   (7,000 cap) as its smoke — owner's call.
4. **No mesher/solver change accompanied any row** — pin discipline held (the mesher's own
   cap/remap decisions produced every number above).

## Bytecheck

`tools/evidence_bytecheck_typology_smoke.py` re-derives every cell of the matrix from the run
dirs + logs + VRAM csvs — **24 checks** (12 success-row: name/J/dofs/config ×3; 6 failure-row:
run.json failure/J + ndjson detail + quoted log line ×2; 5 VRAM: ≥5 samples + exact peak + exact
baseline; 1 J-format) — run output quoted in CONTINUITY. `BYTE-CHECK: 24/24 PASS` (exit 0;
negative control verified failing). Driver-pass extension (2026-10-25 later): +5 checks covering
the 15 dry-run-matrix cells (config × 3 brief classes, exact dofs pins + cap guard) —
**`BYTE-CHECK: 29/29 PASS`** on the post-driver-pass tree.

## Driver-pass re-verification (2026-10-25, later — oracle-decided, owner-directed)

The S1a driver pass (decision record:
`docs/research/typologies/S1A_DRIVER_PASS_ORACLE_FINAL_2026-10-25.md`) re-anchored the five
configs and landed the brief family; the matrix above is preserved as the dated record of the
PRE-repair state (its two mesh_too_large findings + the envelope overshoot are exactly what the
driver pass fixed). Re-verification evidence, all offline except the owner's live campaign:

- **Offline suite: 1509/0/0/0** (`runs/driver_pass/suite2.xml`; the four premise-failures the
  first driver-pass run exposed — the salmon family's revised f0 briefs made three test
  fixtures' premises derivation-active and `salmon_elliptical`'s derived seed graded 4.2% over
  — were fixed, not weakened: the elliptical seed got the same measured stop-150 reseed as its
  two siblings, two saddle-invariant tests got derivation-inert fixture briefs with their
  original assertions intact, and the self-approach fixture strips the new f0 keys — all dated
  in-file). fixer-side verification: 126/0/0 across the touched test files.
- **The 15× gmsh dry-run matrix** (`scratch/gsmoke_2026-10-25/dryruns.log`, screen tier,
  `--dry-run --mode screen`, no solver launched): every combination the brief family supports
  is under the 5,000-dof screen cap —

| Config | 1in brief | 14in brief | 2in brief |
|---|---|---|---|
| biradial_keele (L 195 seed) | 1,846 dofs / 3,522 tris | 2,023 / 3,873 | 2,532 / 4,873 |
| qtw_waveguide (unchanged) | 1,616 / 3,065 | 1,764 / 3,359 | 1,990 / 3,805 |
| salmon_x_signed (stop 150, amp −0.15) | 1,792 / 3,407 | 1,887 / 3,601 | 2,504 / 4,811 |
| salmon_ripple12 (stop 150) | 2,567 / 4,966 | 2,751 / 5,334 | 3,636 / 7,084 |
| lecleach_asym_odd (eps 0.20, full ring) | 4,190 / 8,376 | 4,152 / 8,300 | 4,141 / 8,278 |

- **Solve-side**: the owner launched their own screen campaign at 16:00:41 EDT
  (`--brief user/7040use.yaml --families salmon_elliptical,salmon_x_signed,salmon_saddle,
  salmon_ripple12,lecleach_iwata_ar`, pid 14484) against the repaired tree — the one-GPU rule
  held (gpu-clean refused while the owner's lock is held; the GPU re-smoke matrix rides AFTER
  it or is superseded by the campaign's own run evidence). The pre-repair matrix's refusal
  rows are superseded by this campaign for the salmon family: all five repaired configs
  materialize and mesh (the dry-run matrix; the seeds march envelope-true under all nine
  family briefs — probe + `tests/test_s1a_driver_briefs.py`).