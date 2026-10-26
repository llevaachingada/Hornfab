# Campaign 2026-10-26 - CPU dry-run / LHS evidence (Steps 2C, 3, 4, 5)

Date: 2026-10-26. Branch `unified-typologies`, base `e8d997e` (the campaign Phase-0 fixes
`935e560`, `35bb0ca`, `4e03835`, `8b1580b`, `27c4699`, `b2e88be` are in the history).
**No GPU, no Julia, no solver was launched.** Everything below is a real `hornlab_mesher`
build in a temporary directory (CPU), with the dof caps raised in memory only for the LHS
audit. Interpreter: `.venv\Scripts\python.exe`.

Inputs:

- Briefs: `examples/briefs/campaign_2026-10-26/` (14 files).
- Configs: `examples/typologies/campaign_2026-10-26/` (23 cells).
- Lane evidence: `docs/research/campaign_2026-10-26/` (six reports copied from the audit
  scratch dirs; no job `.json`/`.jsonl` outputs copied).

A cell id is its config file stem. PASS for Step 5.1 means: meshes, dofs <= 12,000, envelope
overshoot 0, and the mouth is within 10 % of the brief's K-law mouth per axis (tall/square) or
inside the brief envelope (wide). Depth is checked with the search layer's own 15 mm outer-shell
allowance (`search.evaluate.ENVELOPE_DEPTH_ALLOWANCE_MM`), and the mouth with
`search.evaluate.mouth_dims_m` (the same function the search scores with).

---

## 1. Commands used (verbatim)

Brief gate:

```powershell
.venv\Scripts\python.exe -c "import glob; from hornlab_search.config import load_brief; [load_brief(p) for p in sorted(glob.glob(r'examples/briefs/campaign_2026-10-26/*.yaml'))]; print('BRIEFS OK', len(glob.glob(r'examples/briefs/campaign_2026-10-26/*.yaml')))"
```

Config gate (load + `DesignSpace` seed validation, which also runs the generator's own
inner-mouth/envelope check):

```powershell
.venv\Scripts\python.exe -c "
import glob
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
for p in sorted(glob.glob(r'examples/typologies/campaign_2026-10-26/*.yaml')):
    c=load_config(p); DesignSpace.from_config(c); print('OK', c.name)
"
```

Step 5.1 dry-run, every cell (log: `runs/step3_5/dryrun_log.txt`):

```powershell
Get-ChildItem examples\typologies\campaign_2026-10-26\*.yaml | Sort-Object Name | ForEach-Object {
  & .venv\Scripts\hornlab-search.exe run --config $_.FullName --mode screen --dry-run
}
```

Step 5.2 LHS harness (scratch dir; not committed): `probe_campaign.py` mirrors
`cli._dry_run` (`DesignSpace.from_config` -> `mesh_spec('screen')` -> `build.build_mesh`) and
adds `mouth_dims_m` + `envelope_violation`. Each cell uses a deterministic per-cell Latin
hypercube (`np.random.default_rng(20261026 + crc32(cell))`, 16 strata; 32 for the rosse_morph
and salmon cells). The dof cap is raised to 1,000,000 **in memory only**, so the audit measures
geometry validity, not the campaign cap. A cell runs in its own subprocess in the final pass,
so a slow point cannot hide another cell's result.

```powershell
.venv\Scripts\python.exe -u <scratch>\probe_campaign.py seeds --out <scratch>\seeds.json
.venv\Scripts\python.exe -u <scratch>\run_lhs_all.py        # per-cell subprocess, 300 s each
```

Step 5.3 grid print:

```powershell
.venv\Scripts\python.exe -c "from hornlab_search.config import load_config, mode_freqs; c=load_config(r'examples/typologies/campaign_2026-10-26/b1t__rosse_morph.yaml'); [print(m, len(mode_freqs(m,c)), [round(x,2) for x in mode_freqs(m,c)]) for m in ('screen','verify','final')]"
```

---

## 2. Step 5.1 - per-cell dry-run (23/23 OK)

All 23 cells dry-run green. `env overshoot` is
`max(W/envW - 1, H/envH - 1, depth/(envD+15) - 1, 0)` from the meshed bbox; it is 0.00 % on
every row. `mesh s` is the real mesher wall time in the seed probe; the CLI dry-run log records
the same meshes.

| cell | status | tris | dofs | mouth W x H (mm) | depth (mm) | env overshoot | mesh s | K-law check |
|---|---|---|---|---|---|---|---|---|
| `b1t__lecleach_iwata_ar` | ok | 5036 | 2640 | 333.0 x 498.3 | 221.5 | 0.00% | 0.45 | W +0.3% / H +0.1% |
| `b1t__rosse_morph` | ok | 7405 | 3814 | 332.4 x 498.1 | 206.5 | 0.00% | 0.84 | W +0.1% / H +0.0% |
| `b1t__salmon_x_signed` | ok | 6599 | 3419 | 348.3 x 508.1 | 206.7 | 0.00% | 0.76 | W +4.9% / H +2.0% |
| `b1w__biradial_keele` | ok | 4464 | 2326 | 371.5 x 294.2 | 198.0 | 0.00% | 1.30 | inside envelope (True) |
| `b1w__osse_baseline` | ok | 3427 | 1796 | 335.0 x 291.3 | 146.0 | 0.00% | 0.41 | inside envelope (True) |
| `b2t__lecleach_iwata_ar` | ok | 5549 | 2904 | 352.6 x 528.6 | 239.0 | 0.00% | 0.37 | W -0.1% / H -0.1% |
| `b2t__rosse_morph` | ok | 9099 | 4691 | 353.2 x 529.1 | 302.9 | 0.00% | 1.00 | W +0.1% / H -0.0% |
| `b2t__salmon_elliptical` | ok | 5381 | 2792 | 354.0 x 529.9 | 166.5 | 0.00% | 0.62 | W +0.3% / H +0.1% |
| `b2w__hyb_osse_h_hypex_v` | ok | 3771 | 1985 | 334.5 x 294.3 | 218.0 | 0.00% | 2.36 | inside envelope (True) |
| `b2w__osse_baseline` | ok | 3794 | 1992 | 348.1 x 295.0 | 184.0 | 0.00% | 0.42 | inside envelope (True) |
| `b3a__ath_core_14in` | ok | 19332 | 9871 | 706.1 x 706.1 | 451.2 | 0.00% | 3.50 | W +0.1% / H +0.1% |
| `b3a__biradial_keele` | ok | 12010 | 6145 | 705.6 x 705.6 | 198.0 | 0.00% | 3.49 | W +0.0% / H +0.0% |
| `b3a__lecleach_rollback` | ok | 14380 | 7416 | 697.9 x 697.9 | 469.9 | 0.00% | 1.12 | W -1.1% / H -1.1% |
| `b3a__rosse_morph` | ok | 15106 | 7692 | 706.2 x 706.2 | 170.8 | 0.00% | 1.51 | W +0.1% / H +0.1% |
| `b3bt__lecleach_iwata_ar` | ok | 9747 | 5053 | 469.9 x 704.6 | 352.9 | 0.00% | 0.59 | W -0.1% / H -0.1% |
| `b3bt__rosse_morph` | ok | 13885 | 7096 | 477.5 x 706.1 | 291.7 | 0.00% | 1.51 | W +1.5% / H +0.1% |
| `b3bt__salmon_x_signed` | ok | 13139 | 6742 | 488.9 x 728.5 | 314.2 | 0.00% | 1.23 | W +3.9% / H +3.2% |
| `b3bw__biradial_keele` | ok | 6354 | 3285 | 470.4 x 442.0 | 198.0 | 0.00% | 1.42 | inside envelope (True) |
| `b3bw__hyb_osse_h_hypex_v` | ok | 6318 | 3271 | 485.3 x 442.0 | 206.0 | 0.00% | 3.50 | inside envelope (True) |
| `native__ath_core` | ok | 7240 | 3777 | 397.1 x 397.2 | 358.6 | 0.00% | 1.21 | no K-law (own recipe) |
| `native__ath_twinray_380` | ok | 4396 | 2295 | 380.0 x 303.3 | 197.0 | 0.00% | 14.25 | no K-law (own recipe) |
| `native__lecleach_asym_odd` | ok | 6574 | 3289 | 234.7 x 235.9 | 116.3 | 0.00% | 0.56 | W -0.2% / H +0.3% |
| `native__lecleach_rollback` | ok | 1706 | 921 | 234.7 x 234.7 | 116.3 | 0.00% | 0.21 | W -0.2% / H -0.2% |

Notes:

- **No cell was dropped.** No cell failed after the reseeds below.
- The widest K-law deviation is `b1t__salmon_x_signed` at W +4.9 % / H +2.0 % (inside the
  required 10 %) and `b3bt__salmon_x_signed` at W +3.9 % / H +3.2 %. They are rim-honest Salmon
  rows; the report's own measured seeds land at the same +2-5 %.
- `b3a__ath_core_14in` is the largest seed (9,871 dofs) and still under the 12,000 screen cap;
  it is the published-2-inch CORE recipe adapted to 1.4 in (labelled as such in the header).
- `native__ath_twinray_380` takes 14.3 s to mesh at epw 6; the lane measured the same
  8.8 s median / 28.2 s max class. It is a mesh-cost outlier, not a failure.
- Warnings printed by the mesher on the biradial/hypex rows (`FREEFORM H/V throat tangent
  angles differ by more than 5 degrees`) are pre-existing generator warnings; the meshes are
  valid and the dry-runs return OK.

### Reseeds (first pass failures, fixed by seeding, never by widening)

| cell | first seed | failure | reseed | result |
|---|---|---|---|---|
| `b1w__osse_baseline` | L 169 | 402 x 350 mm, over 380x300 | L 140 | 335 x 291, pass |
| `b2w__osse_baseline` | L 135 | 268 x 227 mm, undersized | L 178 | 348 x 295, pass |
| `b3bw__hyb_osse_h_hypex_v` | L 210 | generator refused 502 mm width | L 203 | 485 x 442, pass |

---

## 3. Step 5.2 - LHS mesh audit (23 cells, all complete)

16 points per cell; 32 for `rosse_morph` and the salmon cells. Caps raised to 1,000,000 in
memory. "invalid" = refused by the generator/mesher + pre-mesh envelope estimate + post-mesh
envelope check + >12,000 dofs (the search would grade all of these infeasible). No cell has a
timeout hole: the final pass ran each cell in its own process and each point in its own process
in the TwinRay case (150 s/point ceiling; no point hit it).

| cell | dims | n | ok | envelope | refused | >12k dofs | invalid % | dofs min-median-max | commonest failure |
|---|---|---|---|---|---|---|---|---|---|
| `b1t__lecleach_iwata_ar` | 5 | 16 | 14 | 2 | 0 | 0 | 12.5% | 2085-2457-2899 | envelope (2/16) |
| `b1t__rosse_morph` | 17 | 32 | 27 | 0 | 5 | 0 | 15.6% | 2883-3608-10325 | GeometryInvalidError (5/32) |
| `b1t__salmon_x_signed` | 6 | 32 | 23 | 9 | 0 | 0 | 28.1% | 1595-2093-3335 | envelope (9/32) |
| `b1w__biradial_keele` | 7 | 16 | 10 | 6 | 0 | 0 | 37.5% | 2201-2245-2304 | envelope (6/16) |
| `b1w__osse_baseline` | 9 | 16 | 13 | 3 | 0 | 0 | 18.8% | 1213-1910-3102 | envelope (3/16) |
| `b2t__lecleach_iwata_ar` | 5 | 16 | 13 | 3 | 0 | 0 | 18.8% | 2377-2756-3246 | envelope (3/16) |
| `b2t__rosse_morph` | 17 | 32 | 21 | 10 | 1 | 0 | 34.4% | 3641-4587-6333 | envelope (10/32) |
| `b2t__salmon_elliptical` | 4 | 32 | 22 | 10 | 0 | 0 | 31.2% | 2241-2586-2918 | envelope (10/32) |
| `b2w__hyb_osse_h_hypex_v` | 5 | 16 | 13 | 1 | 2 | 0 | 18.8% | 1650-1815-2016 | generator:GeneratorError (2/16) |
| `b2w__osse_baseline` | 9 | 16 | 16 | 0 | 0 | 0 | 0.0% | 615-1027-2215 | - (0/16) |
| `b3a__ath_core_14in` | 15 | 16 | 15 | 0 | 1 | 0 | 6.2% | 9329-9877-10982 | GeometryInvalidError (1/16) |
| `b3a__biradial_keele` | 7 | 16 | 16 | 0 | 0 | 0 | 0.0% | 5791-6125-6661 | - (0/16) |
| `b3a__lecleach_rollback` | 3 | 16 | 16 | 0 | 0 | 0 | 0.0% | 5223-6257-7614 | - (0/16) |
| `b3a__rosse_morph` | 17 | 32 | 31 | 1 | 0 | 0 | 3.1% | 7085-7961-9820 | envelope (1/32) |
| `b3bt__lecleach_iwata_ar` | 5 | 16 | 14 | 2 | 0 | 0 | 12.5% | 4567-5070-5739 | envelope (2/16) |
| `b3bt__rosse_morph` | 17 | 32 | 29 | 1 | 1 | 1 | 9.4% | 5794-7001-14001 | envelope (1/32) |
| `b3bt__salmon_x_signed` | 6 | 32 | 24 | 8 | 0 | 0 | 25.0% | 4308-4807-5456 | envelope (8/32) |
| `b3bw__biradial_keele` | 7 | 16 | 11 | 2 | 3 | 0 | 31.2% | 3083-3231-3379 | generator:GeneratorError (3/16) |
| `b3bw__hyb_osse_h_hypex_v` | 5 | 16 | 12 | 0 | 4 | 0 | 25.0% | 2430-2915-3047 | generator:GeneratorError (4/16) |
| `native__ath_core` | 14 | 16 | 16 | 0 | 0 | 0 | 0.0% | 3589-3884-4239 | - (0/16) |
| `native__ath_twinray_380` | 12 | 16 | 13 | 0 | 3 | 0 | 18.8% | 2222-2378-2570 | GeometryInvalidError (3/16) |
| `native__lecleach_asym_odd` | 5 | 16 | 16 | 0 | 0 | 0 | 0.0% | 2647-3214-3854 | - (0/16) |
| `native__lecleach_rollback` | 3 | 16 | 16 | 0 | 0 | 0 | 0.0% | 713-881-1073 | - (0/16) |

Failure types seen (verbatim samples):

- `invalid_envelope: estimated outside the brief envelope (max relative overshoot ...)` - the
  generator's pre-mesh outer-shell estimator; this is the dominant failure and is a physical
  size limit.
- `GeometryInvalidError: mesh build failed: ... free edges away from its symmetry cut planes`
  (`b1t__rosse_morph`) and `... non-sliver triangle(s) lie entirely in the y=0 symmetry plane`
  (`b1t__rosse_morph`) - real mesh-quality defects inside the box.
- `GeometryInvalidError: cannot fit the acoustic geometry to the requested mm resolution ...
  the axial chord is still Nx its ...` (`b3a__ath_core_14in`, `native__ath_twinray_380`) - the
  mesher's resolution guard at an extreme knob corner.
- `GeneratorError: mouth ... exceeds the brief envelope` (`b2w`/`b3bw` hypex, `b3bw` biradial) -
  the generator's inner-mouth size check.

### Narrowing (only where >40 % of the box was physically invalid)

The rule was applied strictly: a box was narrowed only when the completed audit showed >40 %
invalid, and only for a physical reason. Before/after (all at 16 or 32 points):

| cell | first audit | physical reason | narrow | re-audit |
|---|---|---|---|---|
| `b1w__biradial_keele` | 62.5 % (10/16) | v_rm hi 151 -> H 301-308 mm > 300 envelope; closure/size | v_rm [142,151] -> [142,147.5] | 37.5 % (6/16) |
| `b2w__hyb_osse_h_hypex_v` | 62.5 % (10/16) | V 302-308 > 300 (v_rm) and H 383-457 > 380 (L/h_a) | v_rm hi 147.5, L hi 215, h_a hi 32 (seed L 215) | 18.8 % (3/16) |
| `b3bw__hyb_osse_h_hypex_v` | 62.5 % (10/16) | V 450-462 (v_rm) and W 502-670 (L/h_a) | v_rm hi 222, L hi 208, h_a hi 48 | 25.0 % (4/16) |
| `b3bt__salmon_x_signed` | 59.4 % (19/32) | rim > 500x740 below fc_h 655 / fc_v 441; near-180 diagonal blow-up above stop 150 with x_amp | fc_h [655,700], fc_v [441,475], stop [140,150], x_amp [-0.16,0.10] | 25.0 % (8/32) |

No box was widened. Every remaining box is the lane report's recommendation minus these
physical reductions; the config headers record each change.

The three cells at 31-37 % (`b1w__biradial_keele`, `b2t__rosse_morph`, `b2t__salmon_elliptical`,
plus `b1t__salmon_x_signed` at 28 %) are below the 40 % narrowing trigger and are reported
as-is. Their failures are all envelope/geometry refusals, not crashes.

---

## 4. Step 5.3 - verify-grid point counts (verbatim)

`b1t__rosse_morph` (band 300-8000, `grid.verify_points_per_octave: 6`):

```
screen 12 [500.0, 643.33, 827.75, 1065.04, 1370.35, 1763.18, 2268.63, 2918.96, 3755.72, 4832.36, 6217.63, 8000.0]
verify 29 [300.0, 343.98, 394.41, 452.24, 518.54, 594.56, 681.73, 781.68, 896.28, 1027.68, 1178.35, 1351.11, 1549.19, 1776.32, 2036.74, 2335.35, 2677.73, 3070.31, 3520.45, 4036.58, 4628.37, 5000.0, 5306.94, 5623.41, 6084.98, 6324.56, 6977.09, 7113.12, 8000.0]
final 36 [250.0, 276.02, 304.75, 336.48, 371.5, 410.17, 452.86, 500.0, 552.04, 609.51, 672.95, 743.0, 820.34, 905.72, 1000.0, 1104.09, 1219.01, 1345.9, 1485.99, 1640.67, 1811.45, 2000.0, 2208.18, 2438.03, 2691.8, 2971.99, 3281.34, 3622.89, 4000.0, 4416.36, 4876.05, 5383.6, 5943.98, 6562.68, 7245.79, 8000.0]
```

Matches the plan's expected **12 / 29 / 36**. Screen starts at 500 Hz and never solves below
it; verify adds 300/344/394/452; final solves 250/276 unscored (the v3 band mask starts at
300). This is the frozen `mode_freqs` behaviour, not new code.

---

## 5. Rescale and seed notes (wide briefs)

Where a lane measured a portrait (tall) seed and the campaign cell is WIDE, the V-plane mouth
knob was rescaled to the wide envelope height (recorded in each config header):

- `b1w__biradial_keele`: biradial V mouth radius 249 -> 146.5 mm (H 498 -> 299 outer).
- `b3bw__biradial_keele`: 352.8 -> 221 mm (H 706 -> 448 outer); H-plane h_rm stays 235.2.
- `b2w__hyb_osse_h_hypex_v`: hypex v_rm 397 -> 146.5 mm (V 794 -> 299 outer); H L set to 215.
- `b3bw__hyb_osse_h_hypex_v`: v_rm 353 -> 221 mm (V 706 -> 448 outer); H L 203.
- `b2t__rosse_morph`: LANE_C's R 350 seed was measured at the old 529x794 mouth; scaled by H
  to R 233 for the b2t 353x529 mouth (header records it).
- `b1w`/`b2w`/`b3bw` are the plan's D-11 option (b) commercial-convention cells: the H axis
  keeps the strict K-law mouth and the V axis is allowed to narrow to the envelope, with
  `target.f0_v_hz` masking the V-plane coverage error below the frequency the envelope can
  actually hold (1411 / 2117 / 941 Hz respectively).
- `native__lecleach_rollback` / `native__lecleach_asym_odd` use the lane's native 1200 Hz
  seeds (fc 800, T 0.8, stop 170); the asym cell keeps `span: full` + `quadrants '1234'`
  because `beat_bem` rejects the xz native symmetry plane (ISSUES), so a GPU half model
  would be refused. The half_xz machinery from `935e560` is not used by this GPU campaign.
- `b3a__ath_core_14in` is an ADAPTATION of the published 2-inch CORE recipe (r0 18.0 mm,
  a 42-48, L 320-380, morph 680-730); the header says so outright.

---

## 6. Dropped cells

**None.** All 23 cells mesh, are under 12,000 dofs, and pass the envelope and K-law checks.
No cell needed a second honest reseed beyond the three listed in section 2.

## 7. Honest limits

- This is a **geometry/CPU audit**, not a BEM result. It proves the seeds mesh, fit the box and
  sit on the K-law mouth; it does not prove coverage, loading or DI. The portrait morph/rows
  cells still need the plan's one BEM verify seed before a long campaign.
- The LHS points are uniform in the **search box** (`DesignSpace`/`GeneratedSpace`), not in the
  mesher's own parameter space; a generator error or an envelope estimate is scored exactly as
  the search would score it (`_generator_error`), which is the intended comparison.
- `b3bt__rosse_morph` has one LHS point above 12,000 dofs (14,001); the campaign cap is
  12,000, so that corner is graded infeasible, not silent. All seed rows are under the cap.
- The mesher emits pre-existing H/V throat-tangent warnings on the biradial/hypex generator
  rows; every one of those seeds still meshes and the dry-run returns OK. The warning is
  recorded, not suppressed.

---

## 8. Box widening (2026-10-26 night)

*Handoff Section 6.*

The campaign lane narrowed boxes to keep the invalid rate under 40 %,
leaving searched knobs boxed at 1-10 % of their seed. Owner ruling: the box must not be the
binding constraint; the brief envelope and mesh validity are. `tools/widen_campaign_boxes.py`
widens every SEARCHED knob (a `bounds` entry without `search: false`) to the physical range,
intersects it with the `KeySpec` hard limits in `hornlab_search/design/families.py`, keeps the
seed inside the box, and never narrows an existing edge. Seeds are unchanged; pinned keys stay
pinned. `search.infeasible_penalty: graded` is now present in all 23 configs (it was already
present in 9 and was added to 14).

boxes widened to physical ranges per owner; NOT re-audited (no CPU time); invalid rates will show in tonight's mini-T1

The boxes are the physical table from the SUB-B brief, not a new audit: this section is text
only (no mesh, no solve), so per-cell invalid rates are still unknown and are the first thing
tonight's mini-T1 will show.

### 8.1 Full `--dry-run` table (verbatim, before `--write`)

```text
=== b1t__lecleach_iwata_ar  [FREEFORM]
  g_fc_hz                      430.0 .. 520.0  ->  323.4 .. 924.0           rows cutoff 0.7..2.0*seed
  g_T                             0.75 .. 0.9  ->  0.3 .. 1.0               rows T 0.3..1.0
  g_stop_deg                   150.0 .. 220.0  ->  90.0 .. 220.0            rows stop 90..175; hi kept at current 220.0 (never narrow)
  g_ar_m                         0.63 .. 0.72  ->  0.4 .. 1.2               aspect 0.4..1.2 (portrait envelope)
  - g_ar_p                           0.7 .. 1.4   kept: not in the brief's physical table
=== b1t__rosse_morph  [R-OSSE]
  a_deg                          28.0 .. 32.0  ->  10.0 .. 80.0             wall half-angle 10..80
  R_mm                         235.0 .. 260.0  ->  149.4 .. 286.35          mouth size 0.6..1.15*seed
  tmax                             0.9 .. 1.0  ->  0.6 .. 1.0               R-OSSE tmax 0.6..1.0
  k                                0.8 .. 1.2  ->  0.3 .. 5.0               OSSE k 0.3..5
  q                                0.8 .. 1.2  ->  0.5 .. 2.0               R-OSSE q 0.5..2
  m                                0.7 .. 1.0  ->  0.2 .. 1.5               R-OSSE m 0.2..1.5
  r                                0.3 .. 0.5  ->  0.05 .. 1.0              R-OSSE r 0.05..1.0
  b                              0.15 .. 0.25  ->  0.0 .. 0.6               R-OSSE b 0..0.6
  exponent                         2.0 .. 8.0  ->  2.0 .. 10.0              exponent 2..10
  aspect_ratio                    0.64 .. 0.7  ->  0.4 .. 1.2               aspect 0.4..1.2 (portrait envelope)
  morph_width_mm               320.0 .. 345.0  ->  199.2 .. 381.8           mouth size 0.6..1.15*seed
  morph_height_mm              480.0 .. 510.0  ->  298.8 .. 572.7           mouth size 0.6..1.15*seed
  morph_corner_mm                25.0 .. 60.0  ->  0.0 .. 80.0              morph corner 0..80 mm
  morph_exponent                   2.0 .. 8.0  ->  2.0 .. 10.0              exponent 2..10
  morph_rate                       2.0 .. 4.0  ->  0.5 .. 8.0               morph rate 0.5..8
  morph_fixed                      0.0 .. 0.1  ->  0.0 .. 0.6               morph fixed 0..0.6
  - a0_deg                           1.0 .. 4.0   kept: not in the brief's physical table
  pinned (search: false): r0_mm, morph_target, morph_allow_shrinkage
  search.infeasible_penalty: (absent) -> graded
=== b1t__salmon_x_signed  [FREEFORM]
  g_fc_h_hz                   880.0 .. 1050.0  ->  648.2 .. 1852.0          rows cutoff 0.7..2.0*seed
  g_fc_v_hz                    600.0 .. 720.0  ->  443.1 .. 1266.0          rows cutoff 0.7..2.0*seed
  g_T                              0.7 .. 1.0  ->  0.3 .. 1.0               rows T 0.3..1.0
  g_stop_deg                   125.0 .. 158.0  ->  90.0 .. 158.0            rows stop 90..175 (exception: hi 150); hi kept at current 158.0 (never narrow)
  g_x_amp                       -0.18 .. 0.18  ->  -0.4 .. 0.4              rows x_amp -0.4..0.4
  g_x_fc                         0.05 .. 0.18  ->  0.0 .. 0.3               rows x_fc 0..0.3
=== b1w__biradial_keele  [FREEFORM]
  L_mm                         185.0 .. 195.0  ->  78.0 .. 400.0            depth 0.4*seed..envelope 400
  h_a_deg                        36.0 .. 40.5  ->  10.0 .. 80.0             wall half-angle 10..80
  v_a_deg                        22.0 .. 32.0  ->  10.0 .. 80.0             wall half-angle 10..80
  h_rm_mm                      182.0 .. 190.0  ->  110.76 .. 212.29         mouth size 0.6..1.15*seed
  v_rm_mm                      142.0 .. 147.5  ->  87.9 .. 168.475          mouth size 0.6..1.15*seed
  h_n                              2.0 .. 8.0  ->  1.0 .. 10.0              OSSE n 1..10
  v_n                              2.0 .. 8.0  ->  1.0 .. 10.0              OSSE n 1..10
  search.infeasible_penalty: (absent) -> graded
=== b1w__osse_baseline  [OSSE]
  a_deg                          26.0 .. 34.0  ->  10.0 .. 80.0             wall half-angle 10..80
  L_mm                         140.0 .. 220.0  ->  56.0 .. 400.0            depth 0.4*seed..envelope 400
  n                                2.0 .. 8.0  ->  1.0 .. 10.0              OSSE n 1..10
  s                                0.0 .. 1.0  ->  0.0 .. 1.5               OSSE s 0..1.5
  k                                0.3 .. 2.5  ->  0.3 .. 5.0               OSSE k 0.3..5
  exponent                         2.0 .. 8.0  ->  2.0 .. 10.0              exponent 2..10
  aspect_ratio                     1.0 .. 1.3  ->  0.4 .. 2.5               aspect 0.4..2.5
  - a0_deg                           1.0 .. 4.0   kept: not in the brief's physical table
  - q                                0.9 .. 1.0   kept: current box already covers the physical range
  pinned (search: false): r0_mm
  search.infeasible_penalty: (absent) -> graded
=== b2t__lecleach_iwata_ar  [FREEFORM]
  g_fc_hz                      400.0 .. 480.0  ->  304.5 .. 870.0           rows cutoff 0.7..2.0*seed
  g_T                              0.8 .. 1.0  ->  0.3 .. 1.0               rows T 0.3..1.0
  g_stop_deg                   150.0 .. 200.0  ->  90.0 .. 200.0            rows stop 90..175; hi kept at current 200.0 (never narrow)
  g_ar_m                         0.63 .. 0.72  ->  0.4 .. 1.2               aspect 0.4..1.2 (portrait envelope)
  - g_ar_p                           0.7 .. 1.4   kept: not in the brief's physical table
=== b2t__rosse_morph  [R-OSSE]
  a_deg                          18.0 .. 22.0  ->  10.0 .. 80.0             wall half-angle 10..80
  R_mm                         220.0 .. 245.0  ->  139.8 .. 267.95          mouth size 0.6..1.15*seed
  tmax                             0.9 .. 1.0  ->  0.6 .. 1.0               R-OSSE tmax 0.6..1.0
  k                                0.8 .. 1.2  ->  0.3 .. 5.0               OSSE k 0.3..5
  q                                0.8 .. 1.2  ->  0.5 .. 2.0               R-OSSE q 0.5..2
  m                                0.7 .. 1.0  ->  0.2 .. 1.5               R-OSSE m 0.2..1.5
  r                                0.3 .. 0.5  ->  0.05 .. 1.0              R-OSSE r 0.05..1.0
  b                              0.15 .. 0.25  ->  0.0 .. 0.6               R-OSSE b 0..0.6
  exponent                         2.0 .. 8.0  ->  2.0 .. 10.0              exponent 2..10
  aspect_ratio                    0.64 .. 0.7  ->  0.4 .. 1.2               aspect 0.4..1.2 (portrait envelope)
  morph_width_mm               340.0 .. 365.0  ->  211.8 .. 405.95          mouth size 0.6..1.15*seed
  morph_height_mm              510.0 .. 545.0  ->  317.4 .. 608.35          mouth size 0.6..1.15*seed
  morph_corner_mm                25.0 .. 60.0  ->  0.0 .. 80.0              morph corner 0..80 mm
  morph_exponent                   2.0 .. 8.0  ->  2.0 .. 10.0              exponent 2..10
  morph_rate                       2.0 .. 4.0  ->  0.5 .. 8.0               morph rate 0.5..8
  morph_fixed                      0.0 .. 0.1  ->  0.0 .. 0.6               morph fixed 0..0.6
  - a0_deg                           1.0 .. 4.0   kept: not in the brief's physical table
  pinned (search: false): r0_mm, morph_target, morph_allow_shrinkage
  search.infeasible_penalty: (absent) -> graded
=== b2t__salmon_elliptical  [FREEFORM]
  g_fc_h_hz                    860.0 .. 970.0  ->  640.5 .. 1830.0          rows cutoff 0.7..2.0*seed
  g_fc_v_hz                    575.0 .. 650.0  ->  427.0 .. 1220.0          rows cutoff 0.7..2.0*seed
  g_T                            0.75 .. 0.95  ->  0.3 .. 1.0               rows T 0.3..1.0
  g_stop_deg                   140.0 .. 160.0  ->  90.0 .. 175.0            rows stop 90..175
=== b2w__hyb_osse_h_hypex_v  [FREEFORM]
  L_mm                         190.0 .. 215.0  ->  86.0 .. 300.0            depth 0.4*seed..envelope 300
  h_a_deg                        30.0 .. 32.0  ->  10.0 .. 80.0             wall half-angle 10..80
  h_s                              0.0 .. 0.6  ->  0.0 .. 1.5               OSSE s 0..1.5
  v_rm_mm                      142.0 .. 147.5  ->  87.9 .. 168.475          mouth size 0.6..1.15*seed
  - v_T                              0.0 .. 1.0   kept: current box already covers the physical range
  search.infeasible_penalty: (absent) -> graded
=== b2w__osse_baseline  [OSSE]
  a_deg                          16.0 .. 24.0  ->  10.0 .. 80.0             wall half-angle 10..80
  L_mm                         110.0 .. 190.0  ->  71.2 .. 300.0            depth 0.4*seed..envelope 300
  n                                2.0 .. 8.0  ->  1.0 .. 10.0              OSSE n 1..10
  s                                0.0 .. 1.0  ->  0.0 .. 1.5               OSSE s 0..1.5
  k                                0.3 .. 2.5  ->  0.3 .. 5.0               OSSE k 0.3..5
  exponent                         2.0 .. 8.0  ->  2.0 .. 10.0              exponent 2..10
  aspect_ratio                   1.05 .. 1.35  ->  0.4 .. 2.5               aspect 0.4..2.5
  - a0_deg                           1.0 .. 4.0   kept: not in the brief's physical table
  - q                                0.9 .. 1.0   kept: current box already covers the physical range
  pinned (search: false): r0_mm
  search.infeasible_penalty: (absent) -> graded
=== b3a__ath_core_14in  [OSSE]
  L_mm                         320.0 .. 380.0  ->  140.0 .. 650.0           depth 0.4*seed..envelope 650
  a_deg                          42.0 .. 48.0  ->  10.0 .. 80.0             wall half-angle 10..80
  n                                6.0 .. 7.5  ->  1.0 .. 10.0              OSSE n 1..10
  s                               0.6 .. 0.83  ->  0.0 .. 1.5               OSSE s 0..1.5
  q                               0.99 .. 1.0  ->  0.9 .. 1.0               OSSE q 0.90..1.0
  k                                0.9 .. 1.2  ->  0.3 .. 5.0               OSSE k 0.3..5
  morph_width_mm               680.0 .. 730.0  ->  423.6 .. 811.9           mouth size 0.6..1.15*seed
  morph_height_mm              680.0 .. 730.0  ->  423.6 .. 811.9           mouth size 0.6..1.15*seed
  morph_corner_mm                10.0 .. 30.0  ->  0.0 .. 80.0              morph corner 0..80 mm
  morph_exponent                   2.0 .. 8.0  ->  2.0 .. 10.0              exponent 2..10
  morph_rate                       2.0 .. 4.0  ->  0.5 .. 8.0               morph rate 0.5..8
  morph_fixed                      0.0 .. 0.1  ->  0.0 .. 0.6               morph fixed 0..0.6
  - a0_deg                           1.0 .. 3.0   kept: not in the brief's physical table
  - s1                               1.0 .. 1.3   kept: not in the brief's physical table
  - s2                           0.015 .. 0.035   kept: not in the brief's physical table
  pinned (search: false): r0_mm, exponent, aspect_ratio, morph_target, morph_allow_shrinkage
  search.infeasible_penalty: (absent) -> graded
=== b3a__biradial_keele  [FREEFORM]
  L_mm                         185.0 .. 205.0  ->  78.0 .. 650.0            depth 0.4*seed..envelope 650
  h_a_deg                        36.0 .. 44.0  ->  10.0 .. 80.0             wall half-angle 10..80
  v_a_deg                        28.0 .. 40.0  ->  10.0 .. 80.0             wall half-angle 10..80
  h_rm_mm                      340.0 .. 365.0  ->  211.68 .. 405.72         mouth size 0.6..1.15*seed
  v_rm_mm                      340.0 .. 365.0  ->  211.68 .. 405.72         mouth size 0.6..1.15*seed
  h_n                              2.0 .. 8.0  ->  1.0 .. 10.0              OSSE n 1..10
  v_n                              2.0 .. 8.0  ->  1.0 .. 10.0              OSSE n 1..10
  search.infeasible_penalty: (absent) -> graded
=== b3a__lecleach_rollback  [FREEFORM]
  g_fc_hz                      268.0 .. 320.0  ->  187.6 .. 536.0           rows cutoff 0.7..2.0*seed
  g_T                             0.98 .. 1.0  ->  0.3 .. 1.0               rows T 0.3..1.0
  g_stop_deg                   160.0 .. 200.0  ->  90.0 .. 200.0            rows stop 90..175; hi kept at current 200.0 (never narrow)
=== b3a__rosse_morph  [R-OSSE]
  a_deg                          42.0 .. 48.0  ->  10.0 .. 80.0             wall half-angle 10..80
  R_mm                         340.0 .. 370.0  ->  211.8 .. 405.95          mouth size 0.6..1.15*seed
  tmax                             0.9 .. 1.0  ->  0.6 .. 1.0               R-OSSE tmax 0.6..1.0
  k                                0.8 .. 1.2  ->  0.3 .. 5.0               OSSE k 0.3..5
  q                                0.8 .. 1.2  ->  0.5 .. 2.0               R-OSSE q 0.5..2
  m                                0.7 .. 1.0  ->  0.2 .. 1.5               R-OSSE m 0.2..1.5
  r                                0.3 .. 0.5  ->  0.05 .. 1.0              R-OSSE r 0.05..1.0
  b                              0.15 .. 0.25  ->  0.0 .. 0.6               R-OSSE b 0..0.6
  exponent                         2.0 .. 8.0  ->  2.0 .. 10.0              exponent 2..10
  aspect_ratio                   0.97 .. 1.03  ->  0.4 .. 2.5               aspect 0.4..2.5
  morph_width_mm               690.0 .. 730.0  ->  423.6 .. 811.9           mouth size 0.6..1.15*seed
  morph_height_mm              690.0 .. 730.0  ->  423.6 .. 811.9           mouth size 0.6..1.15*seed
  morph_corner_mm                25.0 .. 60.0  ->  0.0 .. 80.0              morph corner 0..80 mm
  morph_exponent                   2.0 .. 8.0  ->  2.0 .. 10.0              exponent 2..10
  morph_rate                       2.0 .. 4.0  ->  0.5 .. 8.0               morph rate 0.5..8
  morph_fixed                      0.0 .. 0.1  ->  0.0 .. 0.6               morph fixed 0..0.6
  - a0_deg                           1.0 .. 4.0   kept: not in the brief's physical table
  pinned (search: false): r0_mm, morph_target, morph_allow_shrinkage
  search.infeasible_penalty: (absent) -> graded
=== b3bt__lecleach_iwata_ar  [FREEFORM]
  g_fc_hz                      310.0 .. 340.0  ->  228.2 .. 652.0           rows cutoff 0.7..2.0*seed
  g_T                             0.95 .. 1.0  ->  0.3 .. 1.0               rows T 0.3..1.0
  g_stop_deg                   155.0 .. 200.0  ->  90.0 .. 200.0            rows stop 90..175; hi kept at current 200.0 (never narrow)
  g_ar_m                         0.63 .. 0.72  ->  0.4 .. 1.2               aspect 0.4..1.2 (portrait envelope)
  - g_ar_p                           0.8 .. 1.3   kept: not in the brief's physical table
=== b3bt__rosse_morph  [R-OSSE]
  a_deg                          28.0 .. 32.0  ->  10.0 .. 80.0             wall half-angle 10..80
  R_mm                         335.0 .. 365.0  ->  211.8 .. 405.95          mouth size 0.6..1.15*seed
  tmax                             0.9 .. 1.0  ->  0.6 .. 1.0               R-OSSE tmax 0.6..1.0
  k                                0.8 .. 1.2  ->  0.3 .. 5.0               OSSE k 0.3..5
  q                                0.8 .. 1.2  ->  0.5 .. 2.0               R-OSSE q 0.5..2
  m                                0.7 .. 1.0  ->  0.2 .. 1.5               R-OSSE m 0.2..1.5
  r                                0.3 .. 0.5  ->  0.05 .. 1.0              R-OSSE r 0.05..1.0
  b                              0.15 .. 0.25  ->  0.0 .. 0.6               R-OSSE b 0..0.6
  exponent                         2.0 .. 8.0  ->  2.0 .. 10.0              exponent 2..10
  aspect_ratio                    0.65 .. 0.7  ->  0.4 .. 1.2               aspect 0.4..1.2 (portrait envelope)
  morph_width_mm               450.0 .. 490.0  ->  282.0 .. 540.5           mouth size 0.6..1.15*seed
  morph_height_mm              680.0 .. 720.0  ->  423.6 .. 811.9           mouth size 0.6..1.15*seed
  morph_corner_mm                25.0 .. 60.0  ->  0.0 .. 80.0              morph corner 0..80 mm
  morph_exponent                   2.0 .. 8.0  ->  2.0 .. 10.0              exponent 2..10
  morph_rate                       2.0 .. 4.0  ->  0.5 .. 8.0               morph rate 0.5..8
  morph_fixed                      0.0 .. 0.1  ->  0.0 .. 0.6               morph fixed 0..0.6
  - a0_deg                           1.0 .. 4.0   kept: not in the brief's physical table
  pinned (search: false): r0_mm, morph_target, morph_allow_shrinkage
  search.infeasible_penalty: (absent) -> graded
=== b3bt__salmon_x_signed  [FREEFORM]
  g_fc_h_hz                    655.0 .. 700.0  ->  461.3 .. 1318.0          rows cutoff 0.7..2.0*seed
  g_fc_v_hz                    441.0 .. 475.0  ->  308.7 .. 882.0           rows cutoff 0.7..2.0*seed
  g_T                              0.7 .. 1.0  ->  0.3 .. 1.0               rows T 0.3..1.0
  g_stop_deg                   140.0 .. 150.0  ->  90.0 .. 150.0            rows stop 90..175 (exception: hi 150)
  g_x_amp                        -0.16 .. 0.1  ->  -0.4 .. 0.4              rows x_amp -0.4..0.4
  g_x_fc                         0.05 .. 0.15  ->  0.0 .. 0.3               rows x_fc 0..0.3
=== b3bw__biradial_keele  [FREEFORM]
  L_mm                         185.0 .. 205.0  ->  78.0 .. 600.0            depth 0.4*seed..envelope 600
  h_a_deg                        36.0 .. 44.0  ->  10.0 .. 80.0             wall half-angle 10..80
  v_a_deg                        22.0 .. 32.0  ->  10.0 .. 80.0             wall half-angle 10..80
  h_rm_mm                      225.0 .. 245.0  ->  141.12 .. 270.48         mouth size 0.6..1.15*seed
  v_rm_mm                      213.0 .. 227.0  ->  132.6 .. 254.15          mouth size 0.6..1.15*seed
  h_n                              2.0 .. 8.0  ->  1.0 .. 10.0              OSSE n 1..10
  v_n                              2.0 .. 8.0  ->  1.0 .. 10.0              OSSE n 1..10
  search.infeasible_penalty: (absent) -> graded
=== b3bw__hyb_osse_h_hypex_v  [FREEFORM]
  L_mm                         180.0 .. 208.0  ->  81.2 .. 600.0            depth 0.4*seed..envelope 600
  h_a_deg                        40.0 .. 48.0  ->  10.0 .. 80.0             wall half-angle 10..80
  h_s                              0.0 .. 0.6  ->  0.0 .. 1.5               OSSE s 0..1.5
  v_rm_mm                      213.0 .. 222.0  ->  132.6 .. 254.15          mouth size 0.6..1.15*seed
  - v_T                              0.0 .. 1.0   kept: current box already covers the physical range
  search.infeasible_penalty: (absent) -> graded
=== native__ath_core  [OSSE]
  L_mm                         230.0 .. 300.0  ->  104.0 .. 520.0           depth 0.4*seed..envelope 520
  a_deg                          22.0 .. 27.0  ->  10.0 .. 80.0             wall half-angle 10..80
  n                                6.0 .. 7.5  ->  1.0 .. 10.0              OSSE n 1..10
  s                               0.6 .. 0.83  ->  0.0 .. 1.5               OSSE s 0..1.5
  q                               0.99 .. 1.0  ->  0.9 .. 1.0               OSSE q 0.90..1.0
  k                                0.9 .. 1.2  ->  0.3 .. 5.0               OSSE k 0.3..5
  morph_width_mm               380.0 .. 430.0  ->  238.2 .. 456.55          mouth size 0.6..1.15*seed
  morph_height_mm              380.0 .. 430.0  ->  238.2 .. 456.55          mouth size 0.6..1.15*seed
  morph_corner_mm                10.0 .. 30.0  ->  0.0 .. 80.0              morph corner 0..80 mm
  morph_exponent                   2.0 .. 8.0  ->  2.0 .. 10.0              exponent 2..10
  morph_rate                       2.0 .. 4.0  ->  0.5 .. 8.0               morph rate 0.5..8
  morph_fixed                      0.0 .. 0.1  ->  0.0 .. 0.6               morph fixed 0..0.6
  - s1                               1.0 .. 1.3   kept: not in the brief's physical table
  - s2                           0.015 .. 0.035   kept: not in the brief's physical table
  pinned (search: false): r0_mm, a0_deg, exponent, aspect_ratio, morph_target, morph_allow_shrinkage
  search.infeasible_penalty: (absent) -> graded
=== native__ath_twinray_380  [FREEFORM]
  L_mm                         185.0 .. 200.0  ->  76.8 .. 320.0            depth 0.4*seed..envelope 320 v ATH originals 160..240
  h_a_deg                        33.0 .. 37.0  ->  10.0 .. 80.0             wall half-angle 10..80 v ATH originals 22..46
  v_a_deg                        24.0 .. 28.0  ->  10.0 .. 80.0             wall half-angle 10..80 v ATH originals 16..40
  h_s                            0.55 .. 0.65  ->  0.0 .. 1.5               OSSE s 0..1.5 v ATH originals 0.25..0.95
  v_s                            0.55 .. 0.65  ->  0.0 .. 1.5               OSSE s 0..1.5 v ATH originals 0.25..0.95
  h_n                              5.5 .. 6.5  ->  1.0 .. 10.0              OSSE n 1..10 v ATH originals 3.5..9
  v_n                              5.5 .. 6.5  ->  1.0 .. 10.0              OSSE n 1..10 v ATH originals 3.5..9
  h_q                             0.99 .. 1.0  ->  0.9 .. 1.0               OSSE q 0.90..1.0 v ATH originals 0.96..1
  v_q                             0.99 .. 1.0  ->  0.9 .. 1.0               OSSE q 0.90..1.0 v ATH originals 0.96..1
  h_k                              0.9 .. 1.1  ->  0.3 .. 5.0               OSSE k 0.3..5
  v_k                              0.9 .. 1.1  ->  0.3 .. 5.0               OSSE k 0.3..5
  mouth_exponent                   3.0 .. 6.0  ->  2.0 .. 12.0              exponent 2..10 v ATH originals 2..12
  search.infeasible_penalty: (absent) -> graded
=== native__lecleach_asym_odd  [FREEFORM]
  g_fc_hz                      740.0 .. 900.0  ->  560.0 .. 1600.0          rows cutoff 0.7..2.0*seed
  g_T                              0.6 .. 1.0  ->  0.3 .. 1.0               rows T 0.3..1.0
  g_stop_deg                   150.0 .. 200.0  ->  90.0 .. 200.0            rows stop 90..175; hi kept at current 200.0 (never narrow)
  - g_eps_m                         0.0 .. 0.15   kept: not in the brief's physical table
  - g_eps_start                      0.0 .. 0.4   kept: not in the brief's physical table
=== native__lecleach_rollback  [FREEFORM]
  g_fc_hz                      740.0 .. 900.0  ->  560.0 .. 1600.0          rows cutoff 0.7..2.0*seed
  g_T                              0.6 .. 1.0  ->  0.3 .. 1.0               rows T 0.3..1.0
  g_stop_deg                   150.0 .. 200.0  ->  90.0 .. 200.0            rows stop 90..175; hi kept at current 200.0 (never narrow)

cells: 23   files changed: 23   knobs changed: 180
dry run: nothing written
```

### 8.2 Knobs left unchanged, and why

**Not in the brief's physical table** (the brief names no range, so the current box is kept
rather than invented): `g_ar_p` in the three lecleach/iwata rows (0.7-1.4, 0.8-1.3);
`a0_deg` in the 7 OSSE/R-OSSE cells (1.0-4.0, 1-3); `s1` / `s2` in the two ATH cells
(1.0-1.3, 0.015-0.035); `g_eps_m` / `g_eps_start` in `native__lecleach_asym_odd`
(0-0.15, 0-0.4).

**Current box already covers the physical range** (never-narrow leaves them as they are):
`q` 0.9-1.0 in `b1w__osse_baseline` and `b2w__osse_baseline`; `v_T` 0.0-1.0 in
`b2w__hyb_osse_h_hypex_v` and `b3bw__hyb_osse_h_hypex_v`.

**Pinned `search: false`, kept verbatim** (25 entries in 8 configs): `r0_mm` (every R-OSSE and
OSSE cell), `morph_target` and `morph_allow_shrinkage` (every morph cell), and in
`b3a__ath_core_14in` / `native__ath_core` also `exponent` and `aspect_ratio` (plus `a0_deg` in
the native cell).

**Readings applied to ambiguous keys:**

- `a_deg` is treated as the wall half-angle (10-80), not the az-law base (0-40): no campaign
  cell searches an `az_*` knob, so the base-law row has no instance here.
- `q` in the four `*__rosse_morph` cells uses the R-OSSE row (0.5-2.0); in the OSSE cells it
  uses the OSSE row (0.90-1.0).
- `g_stop_deg` in `b1t__salmon_x_signed` / `b3bt__salmon_x_signed` keeps the 150 cap of the
  diagonal x_amp exception; never-narrow still holds `b1t`'s existing 158 hi and the other
  rows' existing 200/220 his.
- `native__ath_twinray_380` takes the widest of {current, table, ATH originals}, so
  `mouth_exponent` reaches 2-12 (ATH) instead of 2-10 (table).
- Mouth-size, depth and cutoff rows are seed-relative (0.6-1.15x, 0.4x-envelope, 0.7-2.0x),
  so they move with the seed and add no new absolute number.

### 8.3 Verification (text only)

- `yaml.safe_load` parses after the patch: 23/23.
- Raw `seed_params:` text block byte-identical before/after: `seeds unchanged: 23/23`.
- Every `search: false` entry still pinned: 25/25 entries (23/23 files).
- A second `--dry-run` reports `files changed: 0   knobs changed: 0` and
  `dry run: nothing written - no changes`; a second `--write` prints `written: 0/23 files`.
- `git diff -U0` over the campaign folder holds only `lo:` / `hi:` value lines plus one
  `infeasible_penalty: graded` insertion in each of the 14 configs that lacked it: 0 other
  changed lines. All hand-written header comments are intact.
- The write is the GUI `POST /api/save-bounds` pattern (targeted line regex over the `bounds`
  block, plus one block insertion); PyYAML is used to read and to verify only, never to
  round-trip.
- No pytest, no mesher, no geometry, no GPU ran for this section.

`seeds unchanged: 23/23`
