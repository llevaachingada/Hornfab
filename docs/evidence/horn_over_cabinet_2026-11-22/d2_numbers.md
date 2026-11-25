# D2 cabinet reconciliation — numbers only, 2026-11-22

**Status:** numbers-gathering lane for the D2 cabinet decision. This document does **not**
select a cabinet and makes no recommendation. **No BEM/FEM solve and no GPU job were run.**
The only generation calls were Boundary Lab's own CPU vented-enclosure generator through the
existing adapter. Every number below carries a source tag and a label:
**[measured]** = BL-generated artifact; **[computed]** = analytic/derived from the stated
source; **[assumed]** = a chosen input.

Working tree: `C:/Users/hunte/Hrns/hornlab-search`. Boundary Lab: `0.5.0`,
`v0.5.0-10-g15f9a89`, HEAD `15f9a89245a9adfec8c2f0006c164953ce381e58`
(`C:/Users/hunte/Github/boundary-lab`). Machine-readable companion:
`d2_cabinet_reconciliation.json` (same directory).

---

## 1. Scope, candidates and driver

18 mm walls, 3 mm clearance. Candidates are the four given:

| Cand | External W × H × D (mm) | Internal W × H × D (mm) | Nominal alignment |
|---|---|---|---|
| A | 320 × 500 × 360 | 284 × 464 × 324 | 42 L (current reference) |
| B | 360 × 420 × 374 | 324 × 384 × 338 | 42 L, depth-packed |
| C | 540 × 700 × 380 | 504 × 664 × 344 | 115 L |
| D | 420 × 620 × 420 | 384 × 584 × 384 | none (gross 86.1 L) |

Driver data from `examples/systems/driver_ts/faitalpro_12pr300.yaml` and
`examples/systems/driver_geometry/faitalpro_12pr300.yaml`:

| Quantity | Value | Use |
|---|---|---|
| Frame OD (mounting flange) | **315.2 mm** | real-frame panel fit only |
| Cutout | 283 mm | reference |
| Mounting depth behind baffle | 140.6 mm | rear-clearance reference |
| Sd | 533 cm² | T/S model |
| Area-equivalent moving diameter | sqrt(4·Sd/π) = **260.5 mm** | BL `driver_diameter_m` proxy only |
| Fs / Re / P_AES / Xmax | 50 Hz / 5.4 Ω / 300 W / 4.92 mm | LF screen |

Frame and moving diaphragm are kept distinct everywhere. The radial difference between them
is (315.2 − 260.5)/2 = **27.35 mm** per side. BL's own panel validator uses only the 260.5 mm
moving diameter (`parameters.py:100-105`); the real frame is checked separately in §5.

**Acoustic-grounding check:** the horn is the rollback Le Cléac'h morph
`lecleach_rollback_1in_v6` (`docs/knowledge/typologies/lecleach_iwata.md`). It enters this
document only as its measured SD1D1001 surface; no horn acoustic formula, Keele mouth
heuristic or CD directivity target is applied. The LF numbers are the fixed lumped vented-box
model, which is independent of horn typology. No family formula is transferred across
typologies.

**Port choice [assumed]:** `port_y_m = −0.130 m` — the value in `vented_overrides.json:16` —
was retained for every candidate. It is inside BL's port-wall budget for all four heights and
gives 228 mm driver/port separation, above BL's 179.99 mm requirement for A, C and D. B's
refusal is the driver wall rule, not the port (§3). All other port parameters are the base
`vented_overrides.json` values: total length 0.220 m, throat area 0.002827433388 m² (60 mm
diameter), NFR 0.12, lip roundover 8 mm, wall 3 mm. The derived tuning is an **outcome** of
this fixed port in the achieved volume, not an independent choice:

BL `port_length_m` is the total length **including both lips**; the repo mapping is
neck = 0.220 − 2×0.008 = **0.204 m**, then bassbox `L_eff` = neck + `N_END`·0.85·`r_eq`
= 0.204 + 2·0.85·0.030 = **0.255 m** (`boundarylab/assemble.py:250-261`;
`bass_reference.py:103-118`; `bassbox.py:203-204`; `N_END=2` at `bassbox.py:115`).

---

## 2. Volume reconciliation

Empty internal volume = `(W−2t)(H−2t)(D−2t)`, t = 18 mm **[computed]**. BL's `air_volume_m3`
is read from the generated `mesh_info.json` **[measured]** (`generate.py:144-226`,
`runner_vented.py:94-107`). BL subtracts the cone/port solids; it does not model the rear
magnet/basket volume (see §9.3).

| Cand | Empty internal [computed] | BL air volume [measured] | Δ BL − empty [computed] | Δ vs named alignment [computed] |
|---|---|---|---|---|
| A | 42.695 L | **42.270 L** | −0.425 L (−1.00 %) | +0.270 L vs 42 L |
| B | 42.053 L | **refused** (no mesh) | — | — |
| C | 115.122 L | **114.697 L** | −0.425 L (−0.37 %) | −0.303 L vs 115 L |
| D | 86.114 L | **85.689 L** | −0.425 L (−0.49 %) | — (no named alignment) |

The displacement subtracted is exactly **0.425 L** on every generated candidate, as expected
from one driver + one port model. B has no BL air volume: BL refused before meshing.

---

## 3. BL generation result

Call shape (per candidate, `store_root="system_runs"`,
`experiment_id="hf_d2_cabinet_2026-11-22"`):

```python
generate_vented(probe_boundarylab().verified_root, overrides,
                store_root="system_runs",
                experiment_id="hf_d2_cabinet_2026-11-22")
```

Overrides: candidate W/H/D, wall 0.018, `driver_diameter_m=0.2605`, `driver_y_m=0.098`,
`port_y_m=−0.130`, all other keys from `vented_overrides.json`. Case directories:

| Cand | Case directory | Result |
|---|---|---|
| A | `system_runs/system/hf_d2_cabinet_2026-11-22/20261123T012301Z-vented-29388-7f8129cc` | ok |
| B | `system_runs/system/hf_d2_cabinet_2026-11-22/20261123T012303Z-vented-29388-56532ec8` | **refused** |
| C | `system_runs/system/hf_d2_cabinet_2026-11-22/20261123T012304Z-vented-29388-b6d4b2fd` | ok |
| D | `system_runs/system/hf_d2_cabinet_2026-11-22/20261123T012306Z-vented-29388-4c3be5b0` | ok |

B's exact BL error **[measured, BL]**:

```
ValueError: Driver must fit inside the enclosure walls with 3 mm clearance.
```

That is BL's driver-height rule at `driver_y=0.098`, `driver_diameter=0.2605`, 18 mm walls:
`|0.098| + 0.13025 + 0.003 = 0.23125 m > 0.210 − 0.018 = 0.192 m` for the 420 mm front
(`parameters.py:100-103`). It is a driver-wall refusal, not a port refusal — the port alone
has 12.26 mm of height headroom on B. No B air volume is guessed or inferred here.

`system_runs` is an NTFS junction to the shared store; all four case directories are visible
under the paths above. The manifest strings record the junction target's absolute path.

---

## 4. LF extension and port velocity

LF numbers use the achieved BL net volume, the fixed port above, and the real 12PR300 T/S via
`woofer_seed.evaluate_box` / `bass_reference.lf_report_row` **[computed]**. `f3` is
`bassbox._f3_hz`: −3 dB below the **63–120 Hz mean**. `f10` is the same curve and reference at
−10 dB (a −10 dB crossing of `bassbox.evaluate`'s SPL; there is no `f10` function in
`bassbox.py`). Port velocity is at the AES ceiling `sqrt(P_AES·Re) = 40.25 V rms`; the limit
is `PORT_AIR_MPS_MAX = 17 m/s` (`bassbox.py:112`).

| Cand | Net Vb [L] | Tuning [Hz] | f3 [Hz] | f10 [Hz] | v40 [m/s] | v63 [m/s] | ratio @40 | ratio @63 | max ratio | > 1.0? |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 42.270 | 27.96 | 64.34 | 38.02 | 26.11 | 13.40 | **1.536** | 0.788 | **1.536** | **YES** |
| B | — | — | — | — | — | — | — | — | — | unavailable |
| C | 114.697 | 16.97 | 58.69 | 29.85 | 12.60 | 5.39 | 0.741 | 0.317 | 0.741 | no |
| D | 85.689 | 19.64 | 59.68 | 31.39 | 16.27 | 7.20 | 0.957 | 0.423 | 0.957 | no (marginal) |

The fixed 0.22 m port gives a very low tuning in every box: 28.0 Hz at 42 L, 19.6 Hz at 86 L,
17.0 Hz at 115 L. In this model the SPL rises monotonically from 20 Hz to 150 Hz (A samples,
dB re 1 V @ 1 m half space: 20 Hz 66.93, 30 Hz 72.32, 40 Hz 76.24, 63 Hz 82.29, 100 Hz 86.91,
150 Hz 88.98), so `f3` sits just below the 63–120 Hz reference band rather than at a classic
shelf corner. Read `f3` as the model's band-relative −3 dB point, not as a measured knee.

**Port geometry rule** (`geometry/rules.py:53-85`, called with `clearance_mm=3` — the default
there is 10 mm at line 36): required = neck 204.0 + flare radius 30.0 + 3.0 = **237.0 mm**
against internal depths 324/338/344/384 mm. **All four PASS**, with 87.0–147.0 mm to spare.
Note that `rules.py`'s “flare radius” is the **throat-equivalent** radius
`sqrt(S_port/π) = 30.0 mm`, not the actual flared mouth radius (43.74 mm from BL's
`port_mouth_diameter_m = 0.087486 m`). Substituting the actual mouth radius gives
204.0 + 43.74 + 3.0 = **250.74 mm**, still below every internal depth; BL's own rear-wall rule
(total 220 mm + one mouth diameter 87.49 mm) is the stricter check and is satisfied by
16.5/30.5/36.5/76.5 mm for A/B/C/D. The port geometry is not a binding constraint anywhere.
B's rule was evaluated even though its generation was refused: the rule reads only the port
area and the derived length, not the box volume, so the 338 mm internal-depth verdict is
valid without an achieved net volume. No B air volume is used anywhere.

---

## 5. Real-frame panel fit (315.2 mm frame)

Check **[computed]**: `frame_radius (157.6) + 3 mm` against the internal panel half-extent
`external/2 − 18`, with `|driver_y|` added on the height axis and the real-frame separation
`|driver_y − port_y| > frame_radius + port_outer (46.743) + 3 = 207.343 mm`. The internal
half-extent convention reproduces the README §5.5 minimum 360 × 400 mm front for this frame
(`315.2 + 2·3 + 2·18 = 357.2 → 360`). A secondary external-face check
(`frame_radius + 3 ≤ external/2`) is also reported so the verdict is not convention-dependent.

| Cand | Width headroom (internal) | Height headroom @ centre line | Height headroom @ y = 98 | Frame pass @ CL | Frame pass @ y = 98 | Overall @ CL | Overall @ y = 98 |
|---|---|---|---|---|---|---|---|
| A | **−18.6 mm** | +71.4 mm | **−26.6 mm** | FAIL (width) | FAIL (height) | **FAIL** | **FAIL** |
| B | +1.4 mm | +31.4 mm | **−66.6 mm** | pass | FAIL (height) | **FAIL** (port sep) | **FAIL** |
| C | +91.4 mm | +171.4 mm | +73.4 mm | pass | pass | **FAIL** (port sep) | **PASS** |
| D | +31.4 mm | +131.4 mm | +33.4 mm | pass | pass | **FAIL** (port sep) | **PASS** |

"Overall" includes the real-frame driver/port separation. At the chosen port y = −130 mm the
separation is 130.0 mm at the centre line vs 207.343 mm required, so **every** centre-line
variant fails separation by **77.3 mm**; at y = 98 mm it is 228 mm and passes.

The secondary external-face check gives width headroom A **−0.6 mm**, B +19.4, C +109.4,
D +49.4, and height-at-98 headroom A **−8.6**, B **−48.6**, C +91.4, D +51.4. The A/B verdicts
do not depend on the internal/external convention; only the margins change.

**Legal driver-y windows** at the chosen port y = −130 mm (lower bound from the 207.343 mm
real-frame separation, upper bound from the frame height):

| Cand | Window (mm) | Status | Window with port at its bottom legal limit | Status |
|---|---|---|---|---|
| A | 77.34 … 71.4 | **empty** (short 5.94 mm) | 25.09 … 71.4 | legal |
| B | 77.34 … 31.4 | **empty** (short 45.94 mm) | 65.09 … 31.4 | **still empty** (short 33.69 mm) |
| C | 77.34 … 171.4 | legal; 98 inside | −74.91 … 171.4 | legal |
| D | 77.34 … 131.4 | legal; 98 inside | −34.91 … 131.4 | legal |

So at the specified `driver_y = 98 mm`, C and D have a real-frame-legal placement, A and B do
not. B has no legal driver height for the real frame at **any** port y; A could be made legal in
height/separation only by lowering the port to its bottom limit, and would still fail the frame
width (−18.6 mm internal, −0.6 mm external).

---

## 6. Horn minimum dy and implied centre spacing

`min_legal_dy_mm` **[computed]** on the real SD1D1001 surface
(`system_runs/system/ref_case/horn_full/lecleach_rollback_1in_v6_9e02db06ecc3/mesh.msh`,
2937 points; physical tag 1; bbox x/y ±116.673 mm, z −3.000 … +139.874 mm), at `dz = 13 mm`,
3 mm clearance (`assembly_pose.py:206-228`):

| Cand | Cabinet H | min dy @ dz = 13 [computed] | min dy @ dz = 0 | Implied horn/woofer spacing @ dz = 0 (driver y = 98) |
|---|---|---|---|---|
| A | 500 mm | **None (cantilever)** | 268.674 mm | 170.674 mm |
| B | 420 mm | **None (cantilever)** | 228.674 mm | 130.674 mm |
| C | 700 mm | **None (cantilever)** | 368.674 mm | 270.674 mm |
| D | 620 mm | **None (cantilever)** | 328.674 mm | 230.674 mm |

This is a real result, not a missing value: at `dz = 13 mm` every SD1D1001 point has
`z + 13 ≥ 10 mm > 3 mm` (the baffle-plane threshold), so no horn geometry remains over the
cabinet top and the seated-overhang policy returns `None`. The policy can only derive a height
while `dz < 6.000 mm` (`gap − z_min = 3 − (−3)`). The README's resolved p2b pose is exactly
this case: `translation_mm = (0, 268.674, 13.000)`, `support = unmodeled_cantilever`
(`system_runs/poses_2026-11-22/p2b_overhang_dz013.json`). The dz = 0 values above are the
policy reference and, for A, match that pose's 268.674 mm dy; the spacing column is the horn
axis offset minus the 98 mm driver height.

---

## 7. Baffle step and cabinet size

| Cand | Baffle step c/(πW) [computed] | Largest external dimension | c/(πL) | c/(2L) |
|---|---|---|---|---|
| A | **341.2 Hz** | 500 mm (height) | 218.4 Hz | 343.0 Hz |
| B | **303.3 Hz** | 420 mm (height) | 260.0 Hz | 408.3 Hz |
| C | **202.2 Hz** | 700 mm (height) | 156.0 Hz | 245.0 Hz |
| D | **260.0 Hz** | 620 mm (height) | 176.1 Hz | 276.6 Hz |

c = 343 m/s **[assumed]**. All baffle-step frequencies (202–341 Hz) and all largest-dimension
characteristic frequencies (156–260 Hz quarter-wave; 245–408 Hz half-wave) lie **below** the
700–1600 Hz band of interest. C has both the lowest baffle-step frequency and the lowest
largest-dimension resonance (700 mm height); no candidate places either characteristic
frequency inside the band.

---

## 8. Which constraints actually bind

**A** binds on three independent things: the real-frame **width** (18.6 mm short on the
internal-panel convention, 0.6 mm short even on the external face), the real-frame **height at
y = 98** (26.6 mm short), and **port velocity** (1.536 × the 17 m/s limit at 40 Hz; 26.11 m/s).
BL's moving-diameter validator passes A with only 0.75 mm to spare, so the failure is entirely
the real frame and the port, not BL's diaphragm model. **B** binds on the real-frame **height
at y = 98** (66.6 mm short) and has **no legal driver-y window** with the chosen port (short by
45.94 mm; still 33.69 mm short with the port at its bottom limit); BL also refuses generation
outright on the moving-diaphragm wall rule, so no air volume exists. **C** has no real-frame
constraint binding at y = 98 (73.4 mm height and 91.4 mm width headroom; separation 228 vs
207.3 mm), and its port rules pass; its port-velocity ratio 0.741 is the lowest. Its remaining
issues are LF-shape and size: the fixed port tunes it to 17.0 Hz, `f3` is 58.7 Hz in the
band-relative sense, and its 700 mm height is the largest dimension. **D** likewise has no
real-frame constraint binding at y = 98 (33.4 mm height, 31.4 mm width; separation passes) and
its port rules pass, but its port-velocity ratio 0.957 is only 4.3 % under the limit. For every
candidate the centre-line placement is non-buildable with the port at y = −130 mm because the
real-frame driver/port separation is 77.3 mm short; the y = 98 placement is what makes C and D
work. The port neck/flare/rear-wall geometry binds nowhere (237 mm required vs ≥ 324 mm
available), and the dz = 13 mm horn pose is a cantilever for every cabinet.

---

## 9. Findings and caveats

1. **B is a hard generation refusal, not a marginal fit.** BL's moving-diameter validator
   refuses the 420 mm front at `driver_y = 98` with the exact message quoted in §3. Moving the
   port does not change the frame height at 98 mm, and even at the bottom legal port position
   B's real-frame legal-y window stays empty by 33.69 mm, so the real 315.2 mm frame cannot be
   mounted at the specified height.
2. **The moving diaphragm hides the frame.** A passes BL with 0.75 mm of height headroom;
   the real frame is 27.35 mm larger in radius per side, so A is infeasible. Any decision that
   uses BL's pass/fail alone will accept an unbuildable front. The two checks must stay
   separate.
3. **BL's subtractions are 0.425 L; the datasheet note lists 1.9 dm³.** The FaitalPRO T/S file
   says “net air volume filled by loudspeaker 1.9 dm3 (Vad)”. If that figure is the physical
   volume occupied by the driver, BL's net volume overstates the true net by ≈ 1.47 L, because
   BL models only the cone/port solids and not the rear magnet/basket volume. This is
   **[inferred]** and the “Vad” label should be source-checked before it is used as a
   correction; no number in §2 or §4 has been adjusted for it. Separately, BL's
   `air_volume_m3` is the FEM interior air volume, which includes the air inside the port duct
   (`worker.py:75-104`); the lumped Vb here follows the task convention (BL air = net). The
   duct's air is of order 1 L by the profile dimensions (≈ 2 % of A, < 1 % of C); no
   duct-air correction is applied either.
4. **The fixed port dominates the LF result.** The same 0.22 m / 28.27 cm² port tunes A to
   28.0 Hz, D to 19.6 Hz and C to 17.0 Hz. `f3` stays at 58.7–64.3 Hz because the model's SPL
   rises monotonically into the 63–120 Hz reference band. These are outcomes of holding the
   port fixed across four very different volumes, not four independently tuned alignments.
5. **Port velocity:** A is over the 17 m/s limit at 40 Hz (1.536); D is just under (0.957);
   C is comfortably under (0.741). B is untested because it did not generate.
6. **Horn pose:** at `dz = 13 mm` the seated-overhang policy is a cantilever for every height;
   `min_legal_dy_mm` is undefined there. The dz = 0 policy heights (and A's resolved p2b pose)
   are reported for the implied spacing, not as a dz = 13 solution.
7. **No fifth candidate was added.** A–D are not all unsuitable: C and D pass the real-frame
   panel fit at y = 98 and the port geometry rules (D marginally on port velocity), so the
   condition for adding a fifth candidate is not met.
8. **No solves and no ranking.** The BL air volumes are geometry artifacts, not acoustic
   results. f3/f10/port velocity are the fixed lumped-element bassbox screening model at
   1 m half space; no BEM, no calibration, no combined-system level.

---

## 10. Sources

| Tag | Number(s) | Source |
|---|---|---|
| S1 | Empty internal volumes, deltas, percentages | Arithmetic on the candidate external dims and 18 mm wall (`vented_overrides.json:5`) |
| S2 | BL air volumes, mesh counts, mouth diameter | `hornlab_search/system/boundarylab/generate.py:144-226`; `.../runner_vented.py:94-107`; each case's `bl_output/.../mesh_info.json` `air_volume_m3` |
| S3 | BL generation error for B | BL `geometry_providers/vented_enclosure/enclosure/parameters.py:100-103`, executed by `generate_vented` |
| S4 | Port neck / effective length / tuning mapping | `hornlab_search/system/bass_reference.py:103-118`; `tools/bassbox.py:203-204,115`; `hornlab_search/system/boundarylab/assemble.py:250-261` |
| S5 | Tuning | `tools/bassbox.py` `port_tuning_hz` (inverse of `port_effective_length`) |
| S6 | f3 | `hornlab_search/system/bass_reference.py:285-331` → `tools/bassbox.py:457` `_f3_hz` |
| S7 | f10 | `tools/bassbox.py` `evaluate` SPL curve, 63–120 Hz mean reference, −10 dB crossing (this lane) |
| S8 | Port velocities and ratios | `hornlab_search/system/bass_reference.py:306-328`; limit `tools/bassbox.py:112` (17 m/s) |
| S9 | Port neck + flare + 3 mm rule | `hornlab_search/system/geometry/rules.py:53-85`; default clearance 10 mm at `:36` overridden to 3 mm |
| S10 | BL panel validator (moving diameter) | BL `parameters.py:100-105`; CPU mirror `hornlab_search/system/woofer_seed.py:790-965` |
| S11 | Real-frame panel fit and legal-y windows | This lane: frame radius 157.6 + 3 mm vs internal half-extents; convention from `docs/evidence/horn_over_cabinet_2026-11-22/README.md` §5.5 and `cabinet_fit.json` |
| S12 | Horn min dy | `hornlab_search/system/assembly_pose.py:206-228`; mesh `system_runs/system/ref_case/horn_full/lecleach_rollback_1in_v6_9e02db06ecc3/mesh.msh`, group SD1D1001 |
| S13 | Baffle step / characteristic frequencies | c/(πW), c/(πL), c/(2L), c = 343 m/s **[assumed]** |
| S14 | Driver T/S and geometry | `examples/systems/driver_ts/faitalpro_12pr300.yaml`; `examples/systems/driver_geometry/faitalpro_12pr300.yaml` |

---

## 11. Verification

- **No GPU, no solve.** No `hornlab-search` solve/search/verify command was invoked; no BEAT
  or Julia host was started. The GPU lane was left untouched.
- **Generation:** four `generate_vented` calls, one per candidate, each returning in ~2 s.
  A/C/D returned `ok=True`; B returned `ok=False` with the quoted BL `ValueError`. The four
  case directories and their `mesh_info.json` files are the artifacts.
- **Horn surface:** 5950 triangles, physical tags 1 (5848, SD1D1001) and 2 (102, SD1G0);
  2937 points used from tag 1. The group-1 bbox equals the all-points bbox
  (−116.673 … +116.673 mm in x/y; −3.000 … +139.874 mm in z).
- **Numeric replay:** the JSON file contains every value, the full candidate overrides, the
  mesh-info SHA-256 values, and the LF SPL samples needed to re-check f3/f10 without rerunning
  BL.
