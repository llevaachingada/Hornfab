# MESH_FIDELITY_PAIRS

> **Context refresh at `01560e5`:** These historical pairings do not isolate mesh convergence: frequency support and other solve conditions can co-vary, several rows share designs, and only two displayed pairs have either J below 5. Their 0.109 J sample SD is not a validated mesh-error distribution or noise floor. Screen and verify study pairs here use the same mesh, so frequency verification does not establish mesh convergence. No new calculations or solves were run for this refresh.

- Repo HEAD at run: `aa11b6268b02708ae9a270aa14e8fe877ce1d15a`
- Timestamp: `2026-11-16T21:37:30-0500`
- Read-only against `runs/` and `dataset/`; no solve, mesher, GPU, queue or config write.
- Common scorer: v7 landscape brief `room_landscape_80x50_700_hf1440_v7` (weights/objective block from the standard 80x50 brief; target from the stored record).
- Grid: one 58-point log grid, 350-8000 Hz (`np.geomspace(350, 8000, 58)`), PCHIP in log f.
- Metrics are regenerated with the parity-exact DI rule (sin-theta balloon quadrature, `search/evaluate.metrics_from_response` semantics).

## Pair count

- Dataset design hashes with more than one `mesh_hash`: **409**
- Same-target, both-ok, both-response, band-covering candidate pairs: **327**
- Candidate pairs scored (all candidates): **327**
- Candidate pairs with J below 5 (either mesh): **2**
- Pairs shown (stop at 30): **30** — the 2 low-J pairs plus the 28 next-lowest-J pairs.
- `runs/**/search.ndjson` multi-mesh design hashes: **0** (one response per design dir, so no run pair can be scored)
- Study `screen` vs `verify` pairs with a different `mesh_hash`: **0** (same mesh in every study pair)

## Delta table

| # | design | mesh A (dof) | mesh B (dof) | larger/smaller DOF | J A | J B | dJ (B-A) | d cov | d rip | d di | d dislope | d flat | d load | d distd | d diag | d flat_cv | target |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `3b41ac7d5589` | `4a225538d6a2` (1605) | `98ac8fae1f15` (1605) | 1.000 | 4.751 | 4.913 | +0.162 | +0.062 | +0.005 | +0.074 | +0.053 | +0.015 | +0.051 | +0.014 | -0.018 | -0.027 | 75x45 700-4500 |
| 2 | `5b7ada586de1` | `4a225538d6a2` (2191) | `98ac8fae1f15` (2191) | 1.000 | 4.910 | 4.918 | +0.008 | -0.025 | +0.007 | +0.077 | -0.012 | -0.005 | +0.001 | -0.018 | +0.038 | -0.013 | 75x45 700-4500 |
| 3 | `7d77eb2e8b82` | `4a225538d6a2` (1691) | `98ac8fae1f15` (1691) | 1.000 | 6.049 | 6.244 | +0.195 | +0.038 | +0.006 | +0.174 | -0.038 | +0.030 | -0.044 | +0.006 | +0.115 | +0.048 | 75x45 700-4500 |
| 4 | `6d26c65b37ea` | `1fbe5574ff16` (2694) | `1c5fe3339012` (5863) | 2.176 | 7.890 | 7.890 | -0.000 | -0.005 | -0.001 | -0.000 | +0.003 | -0.001 | +0.000 | +0.000 | +0.003 | -0.001 | 90x60 300-5500 |
| 5 | `85cd181c2426` | `1fbe5574ff16` (2927) | `1c5fe3339012` (6481) | 2.214 | 11.441 | 11.399 | -0.042 | -0.009 | -0.001 | -0.002 | -0.000 | -0.006 | -0.000 | -0.002 | -0.021 | -0.006 | 90x90 300-5500 |
| 6 | `fed761193da7` | `3dc3310baaa0` (6109) | `bdb877ecf94c` (4540) | 1.346 | 11.676 | 11.680 | +0.005 | +0.001 | +0.000 | -0.000 | -0.000 | +0.001 | +0.002 | +0.001 | +0.000 | +0.001 | 90x60 700-12000 |
| 7 | `6c796c1b4e70` | `0a83385780b0` (3875) | `8e789cd0deef` (3875) | 1.000 | 13.050 | 12.874 | -0.176 | +0.002 | +0.003 | +0.020 | -0.090 | +0.013 | +0.000 | -0.020 | -0.108 | +0.014 | 80x50 350-8000 |
| 8 | `91e434e0fe78` | `0a83385780b0` (3993) | `8e789cd0deef` (3993) | 1.000 | 13.107 | 12.885 | -0.222 | +0.002 | +0.001 | +0.013 | -0.102 | +0.005 | +0.000 | -0.022 | -0.126 | +0.007 | 80x50 350-8000 |
| 9 | `8fd082b5828d` | `27a5026635ca` (2826) | `6e4f33d96078` (4373) | 1.547 | 13.761 | 13.090 | -0.671 | -0.066 | +0.005 | +0.044 | -0.387 | +0.015 | +0.000 | -0.014 | -0.234 | -0.003 | 90x60 700-5500 |
| 10 | `8fd082b5828d` | `46aa891d1864` (1651) | `6e4f33d96078` (4373) | 2.649 | 13.157 | 13.090 | -0.067 | -0.011 | -0.001 | -0.002 | -0.042 | +0.006 | +0.000 | -0.002 | -0.014 | -0.001 | 90x60 700-5500 |
| 11 | `8fd082b5828d` | `6e4f33d96078` (4373) | `c71fc305d33a` (2826) | 1.547 | 13.090 | 14.181 | +1.091 | +0.041 | -0.001 | +0.376 | +0.479 | +0.007 | +0.000 | +0.020 | +0.428 | +0.018 | 90x60 700-5500 |
| 12 | `8fd082b5828d` | `6e4f33d96078` (4373) | `c71fc305d33a` (2826) | 1.547 | 13.090 | 13.108 | +0.018 | +0.006 | -0.002 | +0.002 | +0.010 | -0.002 | +0.000 | +0.000 | +0.006 | -0.001 | 90x60 700-5500 |
| 13 | `8fd082b5828d` | `c71fc305d33a` (2826) | `6e4f33d96078` (4373) | 1.547 | 13.111 | 13.090 | -0.021 | -0.006 | -0.000 | -0.002 | -0.010 | +0.002 | +0.000 | -0.000 | -0.006 | +0.001 | 90x60 700-5500 |
| 14 | `0f730f655e88` | `27a5026635ca` (2825) | `c71fc305d33a` (2825) | 1.000 | 13.776 | 13.099 | -0.677 | -0.058 | +0.006 | +0.046 | -0.397 | +0.011 | +0.000 | -0.015 | -0.237 | -0.003 | 90x60 700-5500 |
| 15 | `8fd082b5828d` | `27a5026635ca` (2826) | `c71fc305d33a` (2826) | 1.000 | 13.761 | 13.108 | -0.652 | -0.060 | +0.003 | +0.046 | -0.377 | +0.013 | +0.000 | -0.014 | -0.228 | -0.003 | 90x60 700-5500 |
| 16 | `8fd082b5828d` | `46aa891d1864` (1651) | `c71fc305d33a` (2826) | 1.712 | 13.157 | 13.108 | -0.049 | -0.005 | -0.003 | +0.000 | -0.032 | +0.004 | +0.000 | -0.001 | -0.008 | -0.002 | 90x60 700-5500 |
| 17 | `8fd082b5828d` | `27a5026635ca` (2826) | `c71fc305d33a` (2826) | 1.000 | 13.761 | 13.111 | -0.649 | -0.060 | +0.006 | +0.046 | -0.377 | +0.013 | +0.000 | -0.014 | -0.228 | -0.003 | 90x60 700-5500 |
| 18 | `8fd082b5828d` | `c71fc305d33a` (2826) | `46aa891d1864` (1651) | 1.712 | 13.111 | 13.157 | +0.046 | +0.005 | +0.001 | -0.000 | +0.032 | -0.004 | +0.000 | +0.001 | +0.008 | +0.002 | 90x60 700-5500 |
| 19 | `15c2f35b4235` | `27a5026635ca` (2852) | `c71fc305d33a` (2852) | 1.000 | 13.760 | 13.116 | -0.644 | -0.052 | +0.005 | +0.046 | -0.380 | +0.012 | +0.000 | -0.014 | -0.226 | -0.004 | 90x60 700-5500 |
| 20 | `a3baf8148887` | `27a5026635ca` (2859) | `c71fc305d33a` (2859) | 1.000 | 13.772 | 13.141 | -0.630 | -0.044 | +0.005 | +0.046 | -0.379 | +0.012 | +0.000 | -0.014 | -0.222 | -0.004 | 90x60 700-5500 |
| 21 | `59483a0c9cca` | `27a5026635ca` (2858) | `c71fc305d33a` (2858) | 1.000 | 13.794 | 13.143 | -0.652 | -0.046 | +0.005 | +0.045 | -0.392 | +0.011 | +0.000 | -0.015 | -0.226 | -0.004 | 90x60 700-5500 |
| 22 | `8fd082b5828d` | `27a5026635ca` (2826) | `46aa891d1864` (1651) | 1.712 | 13.761 | 13.157 | -0.603 | -0.055 | +0.007 | +0.046 | -0.345 | +0.009 | +0.000 | -0.012 | -0.221 | -0.001 | 90x60 700-5500 |
| 23 | `8fd082b5828d` | `46aa891d1864` (1651) | `c71fc305d33a` (2826) | 1.712 | 13.157 | 14.181 | +1.023 | +0.030 | -0.002 | +0.374 | +0.437 | +0.012 | +0.000 | +0.018 | +0.415 | +0.016 | 90x60 700-5500 |
| 24 | `8fd082b5828d` | `27a5026635ca` (2826) | `c71fc305d33a` (2826) | 1.000 | 13.761 | 14.181 | +0.420 | -0.025 | +0.004 | +0.420 | +0.092 | +0.021 | +0.000 | +0.005 | +0.194 | +0.015 | 90x60 700-5500 |
| 25 | `59f57bc457cb` | `bdb877ecf94c` (3527) | `27b99ae77cf8` (6049) | 1.715 | 13.811 | 13.775 | -0.037 | -0.008 | -0.003 | -0.004 | -0.001 | -0.005 | -0.004 | -0.003 | -0.016 | -0.000 | 90x90 700-12000 |
| 26 | `00b862146b27` | `1d1e55a3e822` (873) | `eabfc73b6767` (1468) | 1.682 | 15.119 | 15.058 | -0.061 | -0.008 | -0.001 | -0.008 | +0.002 | -0.005 | -0.021 | -0.004 | -0.023 | -0.004 | 90x90 700-5500 |
| 27 | `1bf2418275d5` | `1d1e55a3e822` (645) | `eabfc73b6767` (1084) | 1.681 | 15.233 | 15.186 | -0.047 | -0.010 | -0.003 | -0.010 | +0.018 | -0.015 | -0.026 | -0.003 | -0.018 | +0.004 | 90x90 700-5500 |
| 28 | `b3c4fcdf39b7` | `1d1e55a3e822` (656) | `eabfc73b6767` (1120) | 1.707 | 15.193 | 15.204 | +0.012 | +0.004 | +0.001 | -0.003 | +0.031 | -0.011 | -0.029 | +0.002 | +0.005 | +0.005 | 90x90 700-5500 |
| 29 | `f6830866a51f` | `1d1e55a3e822` (702) | `eabfc73b6767` (1202) | 1.712 | 15.305 | 15.210 | -0.094 | -0.022 | +0.000 | -0.007 | +0.000 | -0.008 | -0.030 | -0.004 | -0.042 | +0.008 | 90x90 700-5500 |
| 30 | `da8ae6187c87` | `1d1e55a3e822` (894) | `eabfc73b6767` (1502) | 1.680 | 15.375 | 15.323 | -0.052 | -0.005 | -0.000 | -0.007 | +0.005 | -0.006 | -0.025 | -0.003 | -0.016 | -0.004 | 90x90 700-5500 |

- **Standard deviation of dJ among designs with J below 5:** **0.109 J** (n=2; mean +0.085, min +0.008, max +0.162).
- Shown 30 pairs: mean dJ -0.102, sd 0.441, min -0.677, max +1.091.

## Decision reading

The J change is between the two thresholds or the low-J sample is too small (sd 0.109); neither lead is established by this table.

Caveat: the dataset pairs are historical records (2026-10-13 onward). Mesh and frequency support often co-vary; only same-target pairs whose two responses both cover the stored band are scored. The score is a common v7 re-score, not the historical J of either row.

## Verify/confirm mode differences

- Explicit `res_mm*` keys in any run config: **none**; mesh resolution is set by `mesh.epw` (no mode-specific res key exists).
- Modes present in run configs: `screen` and `verify` (no `confirm` mode config was found).
- Run configs whose verify/final DOF cap differs from the screen cap: **283**.

| config | epw | DOF screen | DOF verify | DOF final | n runs | run dirs |
|---|---|---|---|---|---|---|
| `freeform_sculpt` | 6.0 | 5000 | 7000 | 8900 | 42 | `20261022T141729Z-screen-babb6b`, `20261022T142919Z-screen-1db72d`, `20261022T162921Z-screen-6381b9`, `20261022T163620Z-screen-ce97e5`, `20261022T220442Z-screen-36634d`, `20261022T223949Z-screen-af083d`, `20261023T001032Z-screen-bbb2f4`, `20261023T002321Z-screen-630671`, `20261023T003119Z-screen-522f54`, `20261023T005624Z-screen-91f25c`, `20261023T010830Z-screen-4ddc5e`, `20261023T125814Z-screen-fcbcc7`, `20261023T131449Z-screen-a310f8`, `20261023T133154Z-screen-e740f2`, `20261023T134811Z-screen-abb61b`, `20261023T140504Z-screen-40e04b`, `20261023T142145Z-screen-fbef28`, `20261023T143900Z-screen-018aec`, `20261023T145539Z-screen-15bde6`, `20261023T151208Z-screen-3e726b`, `20261023T152813Z-screen-67bc6e`, `20261023T154500Z-screen-6cb76d`, `20261023T160205Z-screen-06ca7e`, `20261023T161840Z-screen-f10ebd`, `20261023T163427Z-screen-3fd710`, `20261023T165046Z-screen-98ac02`, `20261023T170728Z-screen-2b3556`, `20261023T172343Z-screen-569f29`, `20261023T173939Z-screen-093bbb`, `20261023T175444Z-screen-9b4402`, `20261023T181104Z-screen-deaf1a`, `20261023T182756Z-screen-333023`, `20261023T184435Z-screen-f92f90`, `20261023T190032Z-screen-2074e4`, `20261023T191742Z-screen-d75157`, `20261023T193311Z-screen-03d787`, `20261023T201245Z-screen-32f5b5`, `20261025T002443Z-screen-1f4a09`, `20261025T121022Z-screen-77a080`, `20261025T130021Z-screen-04a140`, `20261025T130119Z-screen-39f561`, `20261025T131632Z-screen-f7b156` |
| `salmon_x_shape` | 8.0 | 5000 | 7000 | 8900 | 11 | `20261025T054438Z-screen-35fb3f`, `20261025T054542Z-screen-cafcff`, `20261025T054817Z-screen-2ab09e`, `20261025T055452Z-screen-8dda2a`, `20261025T055711Z-screen-7bc01d`, `20261025T060214Z-screen-f7fbbb`, `20261025T061215Z-screen-8daeeb`, `20261025T110750Z-screen-bada08`, `20261025T113824Z-screen-caddd8`, `20261025T120048Z-screen-5dec69`, `20261025T142406Z-screen-9361bc` |
| `osse_baseline` | 6.0 | 5000 | 7000 | 8900 | 9 | `20261013T053716Z-screen-d627d9`, `20261013T123136Z-screen-ca15be`, `20261022T163420Z-screen-8eadb3`, `20261022T164002Z-screen-ccef24`, `20261022T225139Z-screen-1cdc1b`, `20261023T003954Z-screen-7f1abe`, `20261023T011119Z-screen-5c01bf`, `20261023T061921Z-screen-f6da55`, `20261023T075953Z-screen-a0de89` |
| `salmon_elliptical` | 8.0 | 5000 | 7000 | 8900 | 9 | `20261025T054416Z-screen-8ebfef`, `20261025T054520Z-screen-4b8c39`, `20261025T054743Z-screen-fd08c2`, `20261025T055416Z-screen-648a62`, `20261025T060137Z-screen-60f987`, `20261025T061141Z-screen-5fcbf2`, `20261025T105841Z-screen-7e8b47`, `20261025T141239Z-screen-132abd`, `20261025T200043Z-screen-65e4b9` |
| `osse_axi` | 8.0 | 5000 | 7000 | 8900 | 8 | `20261023T023004Z-screen-5fea80`, `20261023T024455Z-screen-bad7e6`, `20261023T025720Z-screen-2002c3`, `20261023T195300Z-verify-bdae12`, `20261025T002354Z-screen-bad518`, `20261025T120831Z-screen-c5e8e7`, `20261025T125750Z-screen-be9248`, `20261025T125911Z-screen-77e443` |
| `perturbed_osse_hv` | 6.0 | 5000 | 7000 | 8900 | 8 | `20261022T222158Z-screen-4f607e`, `20261023T010250Z-screen-e2bb20`, `20261023T043339Z-screen-d74ea3`, `20261023T045549Z-screen-95bf12`, `20261023T200104Z-verify-4fdec8`, `20261025T002540Z-screen-1e5d78`, `20261025T120929Z-screen-766e31`, `20261025T193523Z-screen-a6128e` |
| `grid_ellipse_mod` | 8.0 | 5000 | 7000 | 8900 | 7 | `20261025T054345Z-screen-791043`, `20261025T054716Z-screen-3febac`, `20261025T060109Z-screen-933e70`, `20261025T060850Z-screen-01740a`, `20261025T061105Z-screen-8ab2d7`, `20261025T181553Z-screen-ee59d0`, `20261025T191415Z-screen-335571` |
| `lecleach_rollback` | 8.0 | 5000 | 7000 | 8900 | 7 | `20261025T055544Z-screen-a69343`, `20261025T061432Z-screen-9f5ba9`, `20261025T105416Z-screen-14aaea`, `20261026T020452Z-screen-03ede0`, `20261112T113047Z-screen-24053e`, `20261112T144510Z-screen-00cf9c`, `20261113T024523Z-screen-c9e865` |
| `salmon_saddle` | 6.0 | 5000 | 7000 | 8900 | 7 | `20261025T060248Z-screen-0f8f5a`, `20261025T061256Z-screen-3644f6`, `20261025T110253Z-screen-53594b`, `20261025T114241Z-screen-877b4d`, `20261025T115234Z-screen-95b468`, `20261025T141938Z-screen-c6ae7e`, `20261025T202737Z-screen-7a057a` |
| `abl_s0_control` | 8.0 | 5000 | 7000 | 8900 | 6 | `20261113T052746Z-screen-0e0c52`, `20261113T052954Z-screen-e1e8a5`, `20261113T053413Z-screen-f5bb5f`, `20261113T062730Z-screen-090fa0`, `20261113T063628Z-verify-02a9c2`, `20261113T134523Z-verify-5c4a52` |
| `rosse_baseline` | 6.0 | 5000 | 7000 | 8900 | 6 | `20261022T223132Z-screen-ad2b6d`, `20261023T003053Z-screen-cbc195`, `20261023T010314Z-screen-f44538`, `20261023T055352Z-screen-483828`, `20261023T060407Z-screen-1de7e7`, `20261023T200406Z-verify-602ef1` |
| `conical` | 8.0 | 5000 | 7000 | 8900 | 5 | `20261023T021641Z-screen-edaf45`, `20261023T202234Z-screen-08ea3e`, `20261023T202502Z-screen-28114d`, `20261025T061611Z-screen-31fd98`, `20261025T061648Z-screen-c2c335` |
| `exponential` | 8.0 | 5000 | 7000 | 8900 | 5 | `20261023T022033Z-screen-1dd7e5`, `20261023T040524Z-screen-92c237`, `20261023T041728Z-screen-dc9e99`, `20261023T202300Z-screen-7307a0`, `20261023T202844Z-screen-5cf13f` |
| `grid_ellipse` | 8.0 | 5000 | 7000 | 8900 | 5 | `20261025T054317Z-screen-67811a`, `20261025T054648Z-screen-57c218`, `20261025T060041Z-screen-d73b3f`, `20261025T060823Z-screen-7a4942`, `20261025T061038Z-screen-65a21d` |
| `hyb_osse_h_hypex_v` | 6.0 | 5000 | 7000 | 8900 | 5 | `20261022T221612Z-screen-919f13`, `20261023T010226Z-screen-f4ec66`, `20261023T053410Z-screen-ff4ee1`, `20261023T054224Z-screen-f01e0e`, `20261025T192603Z-screen-16e4b4` |
| `icw_termination` | 6.0 | 5000 | 7000 | 8900 | 5 | `20261013T204408Z-screen-6bdcbd`, `20261022T215531Z-screen-b80d7b`, `20261023T001004Z-screen-72095c`, `20261023T001217Z-screen-3a3d1f`, `20261023T005314Z-screen-6d7452` |
| `lecleach_iwata_ar` | 8.0 | 5000 | 7000 | 8900 | 5 | `20261025T061505Z-screen-2c228d`, `20261025T105326Z-screen-e496a1`, `20261025T131559Z-screen-99f1f5`, `20261025T181031Z-screen-49eb83`, `20261025T203759Z-screen-07cd44` |
| `splice_osse_tractrix` | 8.0 | 5000 | 7000 | 8900 | 5 | `20261025T054145Z-screen-f326ee`, `20261025T055930Z-screen-a08e1d`, `20261025T060703Z-screen-40e448`, `20261025T060917Z-screen-be94f4`, `20261025T062407Z-screen-b2b6bf` |
| `abl_m_rate4` | 6.0 | 5000 | 12000 | 12000 | 4 | `20261113T052958Z-screen-b076e9`, `20261113T053519Z-screen-dcb9bc`, `20261113T063106Z-screen-4392cd`, `20261113T134334Z-verify-e55364` |
| `blend_osse_tractrix` | 8.0 | 5000 | 7000 | 8900 | 4 | `20261023T023306Z-screen-f2a371`, `20261023T031211Z-screen-40d275`, `20261023T032316Z-screen-93b364`, `20261023T195713Z-verify-b1f395` |
| `lecleach_f90` | 8.0 | 5000 | 7000 | 8900 | 4 | `20261025T055515Z-screen-81f615`, `20261025T060336Z-screen-3c3229`, `20261025T061355Z-screen-c4685a`, `20261025T111659Z-screen-b0491e` |
| `salmon_ripple12` | 8.0 | 5000 | 7000 | 8900 | 4 | `20261025T182557Z-screen-8a8752`, `20261025T183505Z-screen-8e3d77`, `20261025T184110Z-screen-b651b1`, `20261025T203725Z-screen-c0e92a` |
| `spherical_salmon` | 8.0 | 5000 | 7000 | 8900 | 4 | `20261025T054246Z-screen-fb25b2`, `20261025T060009Z-screen-9f0a67`, `20261025T060756Z-screen-c78372`, `20261025T061011Z-screen-c48ee7` |
| `throatblend_hypex` | 8.0 | 5000 | 7000 | 8900 | 4 | `20261025T054218Z-screen-b71769`, `20261025T055940Z-screen-230ad4`, `20261025T060729Z-screen-f5756d`, `20261025T060943Z-screen-f5cefd` |
| `abl_s1_lip12_a3` | 8.0 | 5000 | 7000 | 8900 | 3 | `20261113T062813Z-screen-b1e46c`, `20261113T134548Z-verify-9a25f5`, `20261113T161648Z-screen-1e0423` |
| `hypex` | 8.0 | 5000 | 7000 | 8900 | 3 | `20261023T022404Z-screen-9609e8`, `20261023T033737Z-screen-300a9f`, `20261023T034935Z-screen-c26af3` |
| `osse_axi` | 6.0 | 5000 | 7000 | 8900 | 3 | `20261022T214316Z-screen-14286f`, `20261023T005231Z-screen-14190e`, `20261023T195001Z-verify-0f395c` |
| `abl_m_rate2` | 6.0 | 5000 | 12000 | 12000 | 2 | `20261113T063141Z-screen-3d6318`, `20261113T134412Z-verify-b44ead` |
| `abl_m_rate8` | 6.0 | 5000 | 12000 | 12000 | 2 | `20261113T063216Z-screen-f84180`, `20261113T134446Z-verify-2df8ce` |
| `abl_s1_lip12_a6` | 8.0 | 5000 | 7000 | 8900 | 2 | `20261113T062942Z-screen-4b91ec`, `20261113T134720Z-verify-1b6b53` |
| `abl_s1_lip6_a3` | 8.0 | 5000 | 7000 | 8900 | 2 | `20261113T062857Z-screen-1dd580`, `20261113T134634Z-verify-7ba29d` |
| `abl_s2_wall12_a3` | 8.0 | 5000 | 7000 | 8900 | 2 | `20261113T063025Z-screen-4d0a61`, `20261113T134828Z-verify-733ea1` |
| `blend_conical_exponential` | 6.0 | 5000 | 7000 | 8900 | 2 | `20261022T214811Z-screen-54ec2d`, `20261023T005250Z-screen-7772eb` |
| `blend_osse_tractrix` | 6.0 | 5000 | 7000 | 8900 | 2 | `20261022T214555Z-screen-781f69`, `20261023T005241Z-screen-3ecc9d` |
| `conical` | 6.0 | 5000 | 7000 | 8900 | 2 | `20261022T213158Z-screen-047326`, `20261023T005135Z-screen-257598` |
| `exponential` | 6.0 | 5000 | 7000 | 8900 | 2 | `20261022T213509Z-screen-bdb81a`, `20261023T005201Z-screen-c2994f` |
| `freeform_sculpt_symcheck_full` | 6.0 | 5400 | 7000 | 8900 | 2 | `20261022T141639Z-screen-8cc55e`, `20261025T061759Z-screen-6e3c26` |
| `freeform_sculpt_symcheck_quarter` | 6.0 | 5000 | 7000 | 8900 | 2 | `20261022T141552Z-screen-616fcb`, `20261025T061719Z-screen-531251` |
| `hl__crowe_panel_home_v7` | 6.0 | 10000 | 24000 | 24000 | 2 | `20261115T205453Z-screen-32f7c4`, `20261115T213849Z-screen-c35ad4` |
| `hl__rolled_es_spiral_v7` | 6.0 | 10000 | 24000 | 24000 | 2 | `20261116T001222Z-screen-b25d61`, `20261116T003142Z-screen-981f59` |
| `hyb_osse_h_tractrix_v` | 6.0 | 5000 | 7000 | 8900 | 2 | `20261022T221939Z-screen-b18639`, `20261023T010239Z-screen-94b76e` |
| `hypex` | 6.0 | 5000 | 7000 | 8900 | 2 | `20261022T213800Z-screen-f60b48`, `20261023T005210Z-screen-afc0f5` |
| `icw_rollback` | 6.0 | 5000 | 7000 | 8900 | 2 | `20261023T002020Z-screen-62aa12`, `20261023T005613Z-screen-56d955` |
| `lecleach_toroidal` | 8.0 | 5000 | 7000 | 8900 | 2 | `20261025T061536Z-screen-6641c3`, `20261025T105809Z-screen-0145d9` |
| `osse_axi_fusedcuda` | 8.0 | 5000 | 12000 | 12000 | 2 | `20261025T012944Z-screen-f576b4`, `20261025T013051Z-verify-be4adb` |
| `perturbed_tractrix` | 6.0 | 5000 | 7000 | 8900 | 2 | `20261022T215059Z-screen-4d962e`, `20261023T005300Z-screen-3d291e` |
| `qtw_waveguide` | 8.0 | 5000 | 7000 | 8900 | 2 | `20261025T182237Z-screen-1e1d6e`, `20261025T204451Z-screen-ef3e35` |
| `rf__section_axial_home_v7` | 6.0 | 10000 | 24000 | 24000 | 2 | `20261116T015510Z-screen-e75ec8`, `20261116T020629Z-screen-0d29d7` |
| `rr__crowe_panel_es600_v7` | 6.0 | 6000 | 24000 | 24000 | 2 | `20261115T171150Z-screen-d66ffb`, `20261115T194455Z-screen-bf9fc8` |
| `sab__lecleach_ctrl` | 8.0 | 5000 | 7000 | 8900 | 2 | `20261114T203634Z-screen-5493b1`, `20261114T220720Z-screen-88d19c` |
| `sab__lecleach_fc540` | 8.0 | 5000 | 7000 | 8900 | 2 | `20261114T210521Z-screen-777f75`, `20261114T223630Z-screen-86e077` |
| `sab__lecleach_fc540_T_narrow` | 8.0 | 5000 | 7000 | 8900 | 2 | `20261114T213340Z-screen-e6bea6`, `20261114T230956Z-screen-20418d` |
| `salmon_x_signed` | 8.0 | 5000 | 7000 | 8900 | 2 | `20261025T182430Z-screen-643205`, `20261025T201017Z-screen-b9aa0c` |
| `search_smoke` | 6.0 | 3000 | 6000 | 6000 | 2 | `20261013T053757Z-screen-7e6e5b`, `20261013T121958Z-screen-9e5a5c` |
| `tractrix` | 6.0 | 5000 | 7000 | 8900 | 2 | `20261022T214049Z-screen-de03c4`, `20261023T005220Z-screen-a27c1f` |
| `biradial_keele` | 8.0 | 5000 | 7000 | 8900 | 1 | `20261025T182145Z-screen-fe609a` |
| `blend_conical_exponential` | 8.0 | 5000 | 7000 | 8900 | 1 | `20261023T023558Z-screen-fa928c` |
| `conical_a16` | 6.0 | 5000 | 7000 | 8900 | 1 | `20261022T213015Z-screen-7d52d3` |
| `conical_a48` | 6.0 | 5000 | 7000 | 8900 | 1 | `20261022T213046Z-screen-1c9004` |
| `exponential_a16` | 6.0 | 5000 | 7000 | 8900 | 1 | `20261022T212810Z-screen-aaf58a` |
| `exponential_a48` | 6.0 | 5000 | 7000 | 8900 | 1 | `20261022T212841Z-screen-43f0f7` |
| `fid_ang145` | 8.0 | 5000 | 7000 | 8900 | 1 | `20261113T064020Z-verify-ccd221` |
| `fid_dist8m` | 8.0 | 5000 | 7000 | 8900 | 1 | `20261113T063913Z-verify-157284` |
| `fid_epw10` | 10.0 | 5000 | 7000 | 8900 | 1 | `20261113T063805Z-verify-bd1e51` |
| `fid_epw6` | 6.0 | 5000 | 7000 | 8900 | 1 | `20261113T063717Z-verify-8e8395` |
| `freeform_hv` | 6.0 | 3000 | 4500 | 5400 | 1 | `20261013T234724Z-screen-ff569c` |
| `freeform_hv` | 6.0 | 5000 | 7000 | 8900 | 1 | `20261023T010836Z-screen-d65b56` |
| `freeform_narrow880` | 6.0 | 6500 | 7000 | 8900 | 1 | `20261026T021807Z-screen-61be0f` |
| `lecleach_asym_odd` | 8.0 | 5000 | 7000 | 8900 | 1 | `20261025T182334Z-screen-dc8b5d` |
| `meh_t1_search` | 4.05 | 8200 | 9000 | 9000 | 1 | `20261101T103120Z-screen-803d51` |
| `meh_t2a_search` | 4.05 | 8200 | 9000 | 9000 | 1 | `20261101T103020Z-screen-f3f123` |
| `osse_baseline_open40` | 6.0 | 5000 | 7000 | 8900 | 1 | `20261026T000826Z-screen-d4c9a4` |
| `osse_baseline_wide50` | 6.0 | 5000 | 7000 | 8900 | 1 | `20261026T004007Z-screen-541ec2` |
| `perturbed_osse_hv` | 7.0 | 5000 | 7000 | 8900 | 1 | `20261023T195059Z-verify-19ffe4` |
| `perturbed_tractrix` | 8.0 | 5000 | 7000 | 8900 | 1 | `20261023T023912Z-screen-0563e9` |
| `rf__rect_radial_wide_v7` | 6.0 | 6000 | 24000 | 24000 | 1 | `20261116T005943Z-screen-20db0d` |
| `rf__section_axial_home_smooth_v8` | 6.0 | 10000 | 24000 | 24000 | 1 | `20261116T043544Z-screen-dd15d8` |
| `rr__pucker_hv_moderate_v7` | 6.0 | 6000 | 24000 | 24000 | 1 | `20261115T164910Z-screen-f94955` |
| `rr__pucker_hv_strong_v7` | 6.0 | 6000 | 24000 | 24000 | 1 | `20261115T165937Z-screen-4d8a33` |
| `rr__reference_v7` | 6.0 | 6000 | 24000 | 24000 | 1 | `20261115T163824Z-screen-d4a7c4` |
| `sp__control_v7` | 6.0 | 6000 | 24000 | 24000 | 1 | `20261115T180109Z-screen-0f2ab5` |
| `sp__moderate_v7` | 6.0 | 6000 | 24000 | 24000 | 1 | `20261115T181250Z-screen-1e22a5` |
| `sp__strong_v7` | 6.0 | 6000 | 24000 | 24000 | 1 | `20261115T182340Z-screen-35c541` |
| `throat_adapter` | 6.0 | 5000 | 7000 | 8900 | 1 | `20261014T025335Z-screen-852be3` |
| `tractrix` | 8.0 | 5000 | 7000 | 8900 | 1 | `20261023T022723Z-screen-946f77` |
| `tractrix_a16` | 6.0 | 5000 | 7000 | 8900 | 1 | `20261022T212912Z-screen-f585e6` |
| `tractrix_a48` | 6.0 | 5000 | 7000 | 8900 | 1 | `20261022T212942Z-screen-0d6c35` |
| `wp11_gpu_bipop` | 6.0 | 3000 | 6000 | 6000 | 1 | `20261025T080130Z-screen-3f233c` |
| `wp11_gpu_bipop_fired` | 6.0 | 3000 | 6000 | 6000 | 1 | `20261025T081346Z-screen-30c0ae` |
| `wp11_gpu_cma_me` | 6.0 | 3000 | 6000 | 6000 | 1 | `20261025T080717Z-screen-fd13a7` |
| `wp11_gpu_ipop` | 6.0 | 3000 | 6000 | 6000 | 1 | `20261025T075549Z-screen-930b14` |
| `wp14_multicell_3x3_cpu_near` | 6.0 | 5000 | 7000 | 8900 | 1 | `20261025T112519Z-screen-c6b2d8` |
| `wp14_multicell_3x3_cpu_plain` | 6.0 | 5000 | 7000 | 8900 | 1 | `20261025T113355Z-screen-c705b3` |
| `wp14_multicell_3x3_cuda` | 6.0 | 5000 | 7000 | 8900 | 1 | `20261025T112316Z-screen-b22f31` |

_Script: `scratch/fable_architecture/.tmp/r1_mesh_pairs.py`; runtime 247.6s._
