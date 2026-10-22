# HANDOFF 6b — FREEFORM sculpt test plan (local GPU box, 2026-10-22)

Run on `main` at `f3704a3`. RTX 4060 8 GB, driver 610.62. GPU hygiene (CLAUDE.md) before and after every GPU step:
`Get-Process julia` → none before each step; the BEAT host left after each step was killed and the process list re-checked.
VRAM baselines before each GPU step: 546 / 627 / 625 MiB (desktop + OpenCode). After the last step: no julia, 613 MiB.

## Step 1 — offline suite: PASS

`pytest -m "not slow and not gpu and not crosscheck"` → **515 passed, 0 failed, 0 errors, 0 skipped, exit 0**
(cloud reference: 514 passed + 1 skipped; the one cloud skip needs the mesher, which is installed here).
Only warning: the upstream bempp_cl SciPy `LinearOperator` DeprecationWarning.

## Step 2 — doctor: PASS (10/10)

```
PASS  python-version    Python 3.12.10 in [3.11, 3.14)
PASS  core-imports      numpy, scipy, cma, yaml, jinja2
PASS  hornlab-imports   mesher, beat, plots; bempp yes
PASS  pinned-shas       all installed SHAs match pyproject.toml
PASS  toolchain         TOOLCHAIN.md present, dof_per_triangle=0.51
PASS  gpu               nvidia-smi exits 0
PASS  backend           beat_cuda functional (state=ready)
PASS  configs           all 5 example configs load
PASS  round-trip        seed meshed at 1.5 kHz: 846 tris, 468 nodes, largest extent 0.401 m (metres), source tag 2 present, quadrants '1' <-> symmetry 'yz+xz'
PASS  gpu-hygiene       0 BEAT host(s) alive, VRAM used 436.0 MiB
doctor OK: 10 checks, 0 failed
```
(The mesher printed one outer-shell wall-clearance WARNING; the acoustic surface is unaffected.)

## Step 3 — dry-runs: PASS (match the cloud)

| Config | Triangles | dofs / cap | Quadrants ↔ symmetry | Cloud expectation |
|---|---|---|---|---|
| `freeform_sculpt` | 2588 | 1362 / 5000 | '1' ↔ yz+xz | 1354 |
| `freeform_sculpt_symcheck_quarter` | 820 | 451 / 5000 | '1' ↔ yz+xz | ~452 |
| `freeform_sculpt_symcheck_full` | 3268 | 1636 / 5400 | '1234' ↔ None | ~1638 |

## Step 4 — FREEFORM full vs quarter symmetry check: PASS ("consistent")

| Run | Dir | dofs | J | Solve |
|---|---|---|---|---|
| quarter | `runs/20261022T141552Z-screen-616fcb` | 451 | 41.7813 | 7.8 s |
| full | `runs/20261022T141639Z-screen-8cc55e` | 1636 | 41.7537 | 6.0 s |

```
compare A=quarter B=full (design 892bb3551903), 12 frequencies 500..3000 Hz
  bw_h_deg     max |diff| 0.05114 deg  mean 0.01431
  bw_v_deg     max |diff| 0.04063 deg  mean 0.005846
  di_db        max |diff| 0.004262 dB  mean 0.0008984
  on_axis_db   max |diff| 0.004229 dB  mean 0.002313
  ripple_h_db  max |diff| 0.003705 dB  mean 0.001134
  ripple_v_db  max |diff| 0.004177 dB  mean 0.0006589
compare OK (report only; reference: OSSE full vs quarter 0.023 dB, CP-7d)
```
Bar (NOTES 2026-10-14, not frozen): every dB metric < 0.1 dB and beamwidth within 1 deg. Worst dB diff 0.0043 dB,
worst beamwidth 0.051 deg → **consistent**; the quarter domain is safe for FREEFORM searches.
Cosmetic: `compare` prints `quadrants None` for both runs although they ran 451 vs 1636 dofs (header reads the wrong field).

## Step 5 — 60-candidate `freeform_sculpt` search: PASS

`runs/20261022T141729Z-screen-babb6b`, `search --config examples/freeform_sculpt.yaml --budget 60`, CMA seed 12, config sha 57651bfd1ad8.

| Item | Value |
|---|---|
| Evaluations | 60 new, 0 cached, **0 failures** |
| Seed J → best J | 30.945 → **24.213 (−21.8 %)**, best at eval 26 (`f3b9e7f7b38c`) |
| Compare `freeform_hv` (3 knobs, 722 evals) | −8.3 % — sculpt beats it in 1/12 of the evaluations |
| Best terms (raw) | cov 5.79, rip 5.30, dislope 5.29, flat 3.46, di 1.00, penalty 0 |
| Throughput | GPU 343 s, mesh 55 s; **6.7 s/candidate**, 541/h (dry-run estimate said 2 s — it is a TOOLCHAIN M3 extrapolation) |
| DI provenance | balloon for all 60 |
| Dataset after | 3618 records (3494 ok, 124 failed), 596.8 MB; FREEFORM 784 |

Bounds report (top 6 within 2 % of a bound):

| Key | lo | hi | seed | best | at lo | at hi |
|---|---|---|---|---|---|---|
| exponent | 2 | 8 | 4 | 5.54 | 0/6 | 0/6 |
| profileH.mouthAngleDeg | 35 | 70 | 70 | 64.68 | 0/6 | **2/6** |
| profileH.points.1.1 | 22 | 55 | 38 | 42.91 | 0/6 | 0/6 |
| profileH.points.2.1 | 58 | 105 | 80 | 94.14 | 0/6 | 0/6 |
| profileH.points.3.1 | 108 | 160 | 130 | 148.83 | 0/6 | 0/6 |
| profileH.points.4.1 | 163 | 200 | 185 | 197.00 | 0/6 | 0/6 |
| profileV.mouthAngleDeg | 35 | 70 | 70 | 66.51 | 0/6 | 0/6 |
| profileV.points.1.1 | 22 | 55 | 38 | 28.88 | 1/6 | 0/6 |
| profileV.points.2.1 | 58 | 105 | 80 | 68.79 | 0/6 | 0/6 |
| profileV.points.3.1 | 108 | 160 | 130 | 108.75 | **2/6** | 0/6 |
| profileV.points.4.1 | 163 | 200 | 185 | 185.16 | 0/6 | 0/6 |

No key is pinned (max 2/6); watch `profileH.mouthAngleDeg` (hi) and `profileV.points.3.1` (lo) on a longer run.
Budget 400 was NOT run (needs the user's OK).

## Reports generated (gitignored, local only)

- `runs/20261013T123136Z-screen-ca15be/report.html` (CP-8c osse_baseline 1500)
- `runs/20261013T204408Z-screen-6bdcbd/report.html` (CP-8c icw_termination 800)
- `runs/20261013T234724Z-screen-ff569c/report.html` (CP-8c freeform_hv 722)
- `runs/20261014T025335Z-screen-852be3/report.html` (CP-8c throat_adapter 400)
- `runs/20261022T141729Z-screen-babb6b/report.html` (6b sculpt 60)

Summary layers of the three new runs are in `docs/evidence/runs/` (manifest appended).
