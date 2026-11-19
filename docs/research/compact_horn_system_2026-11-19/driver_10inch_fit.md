# Real 10-inch woofer fit for an assembled Boundary Lab case — 2026-11-19

CPU-only analysis. **No GPU, no BL solve, no queue, no git mutation.** The only file created or
edited by this pass is this document.

**Verdict:** a real 10-inch (FaitalPRO 10PR300 Sd-derived moving diameter 210.496 mm) is **LEGAL**
on the recorded 371.2 × 371.2 mm BL front panel **only with the 45 cm² port** (BL's 3 mm clearance):
required driver/port centre separation **157.10 mm < 175.10 mm available**, margin **+18.01 mm**.
The same panel remains **NOT legal** for a real 12-inch (required 182.10 mm > 150.10 mm available,
−32.00 mm), reproducing the parent's R2 refusal. This legal verdict covers the **front-panel
driver/port separation and wall checks only**; BL's moving-surface shape is still its demo defaults
because cone depth / surround / dust cap are `NOT_YET_AVAILABLE` (see §6).

**Acoustic-grounding applicability.** This is a mechanical panel-fit and centre-spacing task, not a
new construction law, typology or acoustic objective, so `hornlab-acoustic-grounding` adds no
formula here: the geometric rules reused are BL's own validator (mirrored in `woofer_seed.py`) and
the register's measured bboxes. No cross-typology formula is imported.

---

## 0. Provenance and data used

- Repo `C:/Users/hunte/Hrns/hornlab-search`, HEAD `868fb42127540679df04bb37dae57895ebfdbc67`.
- `hornlab_search/system/woofer_seed.py` sha256
  `37659317CF732DB081F585273F7F14C1B6558786891F23E35E68099ACEF02050`.
- `examples/systems/driver_ts/faitalpro_10pr300.yaml` sha256
  `64859593B713A569F43F0914BFFF53F4B23D0B01207B5D803E4BC055828C1C82`.
- `examples/systems/driver_geometry/faitalpro_10pr300.yaml` sha256
  `11F82EE31C0A0620EA0FDF4F2ED28B0C368D2AAD2769A14DAC139D38F124939A`.
- Inputs read, not re-derived: `docs/research/system_woofer_2026-11-18/SENIOR_REVIEW_HANDOFF_2026-11-19.md`
  §3–§5 (R2), `docs/research/compact_horn_system_2026-11-19/candidate_register.md` and `.json`.
- Commands were run with the project interpreter `.venv\Scripts\python.exe` (Python 3.12.10). No CLI
  flags were guessed: the real library signatures were called directly (Appendix A). No CLI wrapper
  was used, so no `--help` was needed.

**Correction to the candidate register.** `candidate_register.md` says the 10-inch frame radius is
`NOT_YET_AVAILABLE`, so its "10 in spacing" is a moving-diameter lower bound. That is now superseded
by `frame_od_mm: 261` in the committed geometry YAML (vendor-page value, machine-fetched
2026-11-18). The frame radius is therefore **130.5 mm `[derived = 261/2]`**, and the spacing table in
§5 is frame-based (and uses 10 mm clearance, not the register's 3 mm), so its numbers are larger
than the register's lower bounds by design.

---

## 1. What the implementation actually does

Read from source before quoting:

- `bl_panel_fit_separation(box, *, driver_moving_diameter_m, driver_y_m=None, port_y_m=None,
  port_wall_m=0.003, port_roundover_m=0.008, cone_depth_m=0.040, clearance_m=0.003)` returns
  `required_m`, `available_m`, the auto-placed `driver_y_m`/`port_y_m`, `port_length_m`,
  `port_length_checked` and the BL failure token.
- `bl_panel_fit_feasible(...)` is the boolean/token entry over the same arithmetic.
- `derive_min_center_spacing_mm(envelope, cabinet, *, layout="separate_above", clearance_mm=10.0,
  woofer_frame_radius_mm=None)`: for `layout="flush_baffle"` it returns
  `woofer_frame_radius_mm - envelope.y_min_mm + clearance_mm`.
- `system/boundarylab/clearance.py` is the separate two-body AABB/vertex gate (R16) for an assembled
  horn + enclosure; it does not model the front-panel driver+port layout, so it is not the number
  below.

The exact BL arithmetic (`_panel_fit_geometry` / `_panel_fit_rules`):

```
driver_r  = driver_moving_diameter_m / 2
throat    = sqrt(port_throat_area_cm2*1e-4 / pi)
mouth     = throat + port_roundover_m            # port_roundover_m = 0.008 default
port_outer= mouth + port_wall_m                  # port_wall_m = 0.003 default
required  = driver_r + port_outer + clearance    # clearance = 0.003 (BL hard-coded)
half_h    = external_height_mm/2*1e-3 - wall_mm*1e-3
driver_budget = half_h - driver_r - clearance
port_budget   = half_h - port_outer - clearance
available = driver_budget + port_budget
```

`bl_panel_fit_feasible` uses the **moving** radius only. The frame/flange is **not** in BL's
arithmetic (see §3).

---

## 2. Required vs available separation, 10-inch vs 12-inch

Documented BL front panel: **371.2 × 371.2 × 1080.7 mm**, 18 mm walls, 115 L, 45 cm² round-flared
port, derived fb 35.0 Hz, port effective length 95.193 mm → total length incl. 2 × 8 mm lips
46.853 mm (`[measured]` seed box, `SENIOR_REVIEW_HANDOFF_2026-11-19` §3 case 4; `[derived]` length
from the fixed `bassbox` model through `bass_reference.feasible_boxes`).

| Driver | Sd `[measured]` | moving Ø `[derived = 2√(Sd/π)]` | required `[derived]` | available `[derived]` | margin | twin verdict |
|---|---|---|---|---|---|---|
| 10PR300 | 348 cm² | 210.496 mm | **157.095 mm** | **175.105 mm** | **+18.010 mm** | `feasible=True`, reason `None` |
| 10PR320 | 347 cm² | 210.194 mm | 156.944 mm | 175.256 mm | +18.312 mm | `feasible=True`, reason `None` |
| 12PR300 (R2) | 533 cm² | 260.507 mm | **182.100 mm** | **150.100 mm** | **−32.000 mm** | `feasible=False`, `BL_PANEL_FIT_DRIVER_PORT_SEPARATION` |
| 10PR300 @ 170 cm² (R4 tower port) | 348 cm² | 210.496 mm | 192.810 mm | 139.391 mm | −53.419 mm | `feasible=False`, `BL_PANEL_FIT_DRIVER_PORT_SEPARATION` |

The handoff's rounded **0.1821 / 0.1501 m** for the 12PR300 reproduces exactly as
**182.100 / 150.100 mm**. The 10-inch changes the sign of the margin because its moving radius is
**25.005 mm smaller** (`130.253 − 105.248 = 25.005 mm`) while the port and panel budgets stay fixed.
**Port area is the other half of the lever**: the 10-inch is legal only at the contract-minimum
45 cm² port; the 170 cm² port used by the recorded R4 tower still fails by 53 mm.

### Frame/flange radius, stated separately from the moving diameter

- Moving radius used by BL: **105.248 mm** `[derived = 210.496/2]`.
- Frame/flange radius: **130.500 mm** `[derived = frame_od_mm 261 / 2]`; frame OD 261 mm `[measured]`
  (`examples/systems/driver_geometry/faitalpro_10pr300.yaml`, vendor page).
- On the 371.2 mm front with 18 mm walls the usable wall line is `371.2/2 − 18 = 167.60 mm`, so the
  real frame has **37.10 mm** of radial margin inside the wall line; cutout radius is
  `232/2 = 116.00 mm` `[measured]`.
- **Caveat:** BL's gate would accept a driver by its moving radius even if a real flange overhung the
  wall. The frame check above is our own added constraint, not a BL rule.

The BL auto-placement on this panel is driver `y = +59.352 mm`, port `y = −115.753 mm`
(centre separation 175.105 mm), i.e. exactly the `available_m` value.

---

## 3. Legal vertical centre spacing for the measured candidate bboxes

Same arithmetic as the actual `derive_min_center_spacing_mm(..., layout="flush_baffle")`:

```
spacing = frame_radius + bbox_H/2 + 10 mm        # y_min = -bbox_H/2 for the mirrored bbox
d/λ     = (spacing/1000) * f / 343               # c = 343 m/s
```

The bboxes are the register's **outer/build bbox** (`[measured]`, register §1). The horn body and the
woofer frame are assumed co-planar on one baffle (the `flush_baffle` layout); if the woofer is recessed
behind the baffle the moving radius applies and these numbers are conservative.

| ID | outer bbox W×H×D (mm) | spacing (mm) | d/λ @ 900 Hz | d/λ @ 1100 Hz | d/λ @ 1250 Hz | register verdict (cross-ref) |
|---|---|---|---|---|---|---|
| A1 | 567.9 × 379.3 × 322.3 | **330.150** | 0.8663 | 1.0588 | 1.2032 | register §2 A1 |
| A3 | 592.0 × 377.8 × 305.3 | **329.400** | 0.8643 | 1.0564 | 1.2004 | register §2 A3 |
| A2 | 590.0 × 464.4 × 346.9 | **372.700** | 0.9779 | 1.1952 | 1.3582 | register §2 A2 |
| K1 | 486.85 × 287.17 × 285.4 | **284.085** | 0.7454 | 0.9111 | 1.0353 | register §2 K1 |
| C2 | 461.4 × 460.5 × 231.4 | **370.750** | 0.9728 | 1.1890 | 1.3511 | register §2 C2 |

Only K1 stays inside one wavelength at 1250 Hz (1.035 at 1250 is 3.5 % over; it is the only row under
1.0 at 1100 Hz). Every row is inside one λ at 900 Hz. These are **spacing** numbers; they do not
re-open the register's crossover screen, which used a moving-diameter lower bound. The register's own
spacing values (e.g. A1 297.9 mm) are smaller because they used moving radius 105.25 mm and 3 mm
clearance; the values above add the real 261 mm flange and the task's 10 mm clearance.

---

## 4. What the frame adds to the assembled envelope (A1 example)

For A1 (mouth 567.9 × 379.3 mm) + 10PR300 frame Ø261, flush layout, 10 mm clearance:

- horn centre at `+379.3/2 = +189.65 mm`; woofer centre at `189.65 − 330.15 = −140.50 mm`;
- woofer frame bottom at `−140.50 − 130.5 = −271.00 mm`;
- **shared baffle envelope = 567.90 mm wide × 460.65 mm tall** (horn top edge to frame bottom edge).
- The horn mouth overhangs a 371.2 mm-wide box by `(567.9 − 371.2)/2 = 98.35 mm` each side. That is
  acceptable only because BL assembles the horn and the vented enclosure as **two separate closed
  bodies**; a shared monolithic front baffle would need the box front widened to the mouth width.

---

## 5. Missing maker dimensions and which ones bind

`[measured]` values are from the committed vendor-page YAML; `NOT_YET_AVAILABLE` means the vendor page
does not print it numerically and no maker CAD/measurement exists in the repo.

| Dimension | Value / status | Present in schema? | Binds the fit? |
|---|---|---|---|
| frame OD | **261 mm `[measured]`** | yes (`frame_od_mm`) | **Yes** — sets frame radius 130.5 mm for the horn/woofer centre spacing (register's lower bound is superseded) |
| frame/flange shape | circular `[assumed]` | no field | Yes if non-circular; a round OD is assumed, not proven |
| cutout | **232 mm `[measured]`** | yes (`cutout_mm`) | Yes — baffle hole and minimum front width |
| bolt circle / PCD | **246 mm `[measured]`**, notes string only | no numeric field | Screw access only; does not bind the acoustic panel fit |
| flange + gasket thickness | **12.2 mm `[measured]`**, notes string only | no | Recess/flush detail only |
| overall depth | **115.3 mm `[measured]`** | yes (`depth_mm`) | Rear clearance |
| cone depth | `NOT_YET_AVAILABLE` | yes (`cone_depth_mm`) | **Yes** — BL's `cone_depth + 3 mm >= d - t` rule and the installed moving-surface model |
| surround width | `NOT_YET_AVAILABLE` | yes (`surround_width_mm`) | **Yes** — moving-surface shape; BL currently stages its 12 mm default |
| dust-cap diameter | `NOT_YET_AVAILABLE` | yes (`dust_cap_diameter_mm`) | **Yes** — moving-surface shape; BL stages its 50 mm default |
| mounting depth behind baffle | `NOT_YET_AVAILABLE` | yes (`mounting_depth_behind_baffle_mm`) | **Yes** — rear wall / recess clearance |

Gate output for the catalog (raw in Appendix A):

```
faitalpro_10pr300: present=('cutout_mm', 'frame_od_mm', 'depth_mm') missing=('cone_depth_mm', 'surround_width_mm', 'dust_cap_diameter_mm', 'mounting_depth_behind_baffle_mm')
```

`motor_map.py` documents the same limitation: only `driver_diameter_m` is derived from `Sd`; cone
depth, surround and cap are refused with `GEOMETRY_FIELD_UNAVAILABLE` and BL keeps its provider
defaults (200 mm moving Ø, 40 mm cone depth, 50 mm cap, 12 mm surround) unless a maker drawing is
ingested. **Do not silently treat the demo cone as the 10PR300.**

---

## 6. One recommended minimal legal BL panel layout

**Reuse the exact recorded seed tower and change only the driver diameter to the real 10PR300 value.**
This is the smallest change that is proven legal by the committed arithmetic; it needs no invented
volume, tuning or port length.

| Parameter | Value | Source |
|---|---|---|
| external W × H × D | **371.2 × 371.2 × 1080.7 mm** | `[measured]` seed box, handoff §3 case 4 |
| wall | **18.0 mm** | `[measured]` |
| net volume | **115.0 L** | `[measured]` |
| port | **45 cm² round-flared, NFR 0**, derived fb **35.0 Hz**, effective length **95.193 mm**, total incl. lips **46.853 mm** | `[measured]` area / `[derived]` length via `bass_reference.feasible_boxes` |
| driver | **FaitalPRO 10PR300**, moving Ø **210.496 mm** `[derived]`, frame Ø **261 mm** `[measured]` | driver YAMLs |
| driver centre | `x = 0`, **y = +59.35 mm** | `[derived]` BL max-legal placement |
| port centre | `x = 0`, **y = −115.75 mm** | `[derived]` BL max-legal placement |
| required / available separation | **157.095 / 175.105 mm** (feasible) | §2 |
| frame on front | radius 130.5 mm vs wall line 167.6 mm, **37.1 mm margin** | §2 |
| horn mount | separate body above; A1 mouth 567.9 × 379.3, centre spacing **≥ 330.15 mm** | §3–§4 |

The critical hard floor, stated so the owner can see how small the slack is: the minimum legal front
**height** for this driver + port at BL's 3 mm clearance is
`2(r + r_port) + 3·3 mm + 2·18 mm = 353.19 mm` (Appendix A). The recorded 371.2 mm front clears it by
18.01 mm; a **317 mm** front (what the fixed `bassbox` dimension helper produces for a 10-inch in a
compact box) does **not** clear it. So a shallower/compact 371.2-front enclosure is *not* proven here
and would need a fresh `bassbox` volume/tuning/port derivation, not an invented one.

### Claims this layout would support

- The committed **CPU twin of BL's front-panel validator** says the real 10PR300 moving diameter and a
  45 cm² port coexist on the 371.2 mm front (`feasible=True`); the same call reproduces the 12PR300
  refusal. **This is a prediction from `woofer_seed.py`, not a BL-executed `validate`** (no BL run in
  this pass).
- Mechanically the real 261 mm frame fits inside the front-panel wall line, and the driver and port
  hold the required separation — so a T3 10-inch staging case can be specified now.
- The horn/woofer centre spacing for each register row at 10 mm clearance with the real flange (§3).

### Claims it would **not** support

- Any real-product winner or ordering claim: there is no real frame/cone drawing and BL still stages
  the demo moving-surface shape (cone depth, surround, cap unknown).
- Absolute SPL, installed/exterior directivity or a crossover verdict: no assembled BEM was run, no
  900–1250 Hz scoring exists (register §3), and the horn channel remains an ideal normal-velocity
  source.
- Port noise/turbulence or LF band behaviour (LF tier ignores NFR and has no <200 Hz data).
- The 170 cm² port tower (still fails by 53.4 mm) and the 12-inch on this panel (fails by 32.0 mm).

---

## 7. Printability consequence

- A1 + 10-inch flush layout needs a **567.9 × 460.65 mm** baffle envelope (§4). On a 300 mm-class bed
  that is not one part: it splits into **2 columns × 2 rows ≈ 284 × 230 mm tiles**, plus seams. The
  horn mouth alone (567.9 × 379.3) already needs 2 columns.
- The woofer enclosure front is **371.2 mm**, also over 300 mm in one axis, so the box needs its own
  split (or separate panels) independent of the horn.
- The 10-inch module itself is bed-friendly: cutout **232 mm** and frame **261 mm** both fit a
  300 mm bed, so the driver opening/port panel can be printed in one tile if the front is split at the
  horn boundary rather than through the frame.
- Because BL assembles horn and enclosure as two closed bodies, printing them separately is the
  natural route; the segmentation cost is driven by the 568 mm mouth and the 460 mm combined height,
  not by the 10-inch frame.

---

## Appendix A — exact commands and raw output

Command (from `C:/Users/hunte/Hrns/hornlab-search`):

```powershell
.venv\Scripts\python.exe C:\Users\hunte\AppData\Local\Temp\opencode\fit10_final.py
```

Script body (the same calculations, using the real library signatures; read-only):

```python
import math
from hornlab_search.system import contracts as C
from hornlab_search.system import woofer_seed as W

def P(w,h,d,area,wall=18.0,v=115.0,fb=35.0,l_eff=0.095193):
    return C.BoxPoint(kind="vented", external_width_mm=w, external_height_mm=h,
        external_depth_mm=d, net_volume_l=v, wall_mm=wall, port_type="round_flared",
        port_throat_area_cm2=area, port_nfr=0.0, requested_tuning_hz=fb,
        derived_effective_port_length_m=l_eff, derived_tuning_hz=fb)

tower = P(371.2,371.2,1080.7,45.0)
for name,sd in (("10PR300 Sd=348",348.0),("10PR320 Sd=347",347.0),("12PR300 Sd=533",533.0)):
    dia = 2.0*math.sqrt(sd*1e-4/math.pi)
    s = W.bl_panel_fit_separation(tower, driver_moving_diameter_m=dia)
    # ... print required/available/feasible (see output)

s = W.bl_panel_fit_separation(P(371.2,371.2,1080.7,170.0),
                              driver_moving_diameter_m=2.0*math.sqrt(348e-4/math.pi))

FRAME_R=261.0/2.0; GAP=10.0; c=343.0
for k,(w,h,d) in {"A1":(567.9,379.3,322.3),"A3":(592.0,377.8,305.3),"A2":(590.0,464.4,346.9),
                  "K1":(486.85,287.17,285.4),"C2":(461.4,460.5,231.4)}.items():
    env = W.envelope_from_bbox_m([-w/2e3,-h/2e3,0.0,w/2e3,h/2e3,d/1e3],source="register",design_hash=k)
    sp = W.derive_min_center_spacing_mm(env, P(w,h,d,45.0), layout="flush_baffle",
                                        clearance_mm=GAP, woofer_frame_radius_mm=FRAME_R)
```

Raw output (pasted, unedited):

```
=== BL front-panel driver/port separation, 371.2 x 371.2 mm front, 18 mm walls, 45 cm2 port ===
10PR300 Sd=348: d_moving=210.4964mm r=105.2482mm
   required=157.0952mm available=175.1048mm margin=+18.0096mm
   feasible=True reason=None driver_y=+59.3518 port_y=-115.7530 port_len=46.8531mm
10PR320 Sd=347: d_moving=210.1937mm r=105.0969mm
   required=156.9439mm available=175.2561mm margin=+18.3123mm
   feasible=True reason=None driver_y=+59.5031 port_y=-115.7530 port_len=46.8531mm
12PR300 Sd=533: d_moving=260.5066mm r=130.2533mm
   required=182.1003mm available=150.0997mm margin=-32.0005mm
   feasible=False reason=BL_PANEL_FIT_DRIVER_PORT_SEPARATION driver_y=+34.3467 port_y=-115.7530 port_len=46.8531mm

=== same front with the R4 tower's 170 cm2 port ===
10PR300 170cm2: required=192.8095mm available=139.3905mm margin=-53.4190mm feasible=False reason=BL_PANEL_FIT_DRIVER_PORT_SEPARATION

=== 10-inch legal vertical centre spacing, frame radius 130.5 mm, +10 mm clearance ===
A1: H=379.30 y_min=-189.6500 spacing=330.1500mm  d/lam900=0.8663 d/lam1100=1.0588 d/lam1250=1.2032
A3: H=377.80 y_min=-188.9000 spacing=329.4000mm  d/lam900=0.8643 d/lam1100=1.0564 d/lam1250=1.2004
A2: H=464.40 y_min=-232.2000 spacing=372.7000mm  d/lam900=0.9779 d/lam1100=1.1952 d/lam1250=1.3582
K1: H=287.17 y_min=-143.5850 spacing=284.0850mm  d/lam900=0.7454 d/lam1100=0.9111 d/lam1250=1.0353
C2: H=460.50 y_min=-230.2500 spacing=370.7500mm  d/lam900=0.9728 d/lam1100=1.1890 d/lam1250=1.3511

=== assembled shared-baffle envelope for A1 + 10PR300 (flush layout) ===
horn centre at +189.65, woofer centre at -140.50, woofer frame bottom at -271.00
shared baffle height = 460.65 mm, width = 567.90 mm

=== frame / front-panel wall checks on 371.2 front, 18 mm walls ===
half wall line = 371.2/2 - 18 = 167.60 mm; frame radius = 130.50 mm; margin = 37.10 mm
cutout radius = 232/2 = 116.00 mm

=== minimum legal front height for 10PR300 + 45 cm2 port (BL 3 mm clearance) ===
r=105.2482 rp=48.8470 -> h_min = 2*(r+rp)+3*3mm+2*wall18 = 353.19 mm
```

Catalog completeness (separate run, `load_driver_catalog`):

```
faitalpro_10pr300: present=('cutout_mm', 'frame_od_mm', 'depth_mm') missing=('cone_depth_mm', 'surround_width_mm', 'dust_cap_diameter_mm', 'mounting_depth_behind_baffle_mm')
faitalpro_10pr320: present=('cutout_mm', 'frame_od_mm', 'depth_mm') missing=('cone_depth_mm', 'surround_width_mm', 'dust_cap_diameter_mm', 'mounting_depth_behind_baffle_mm')
faitalpro_12pr300: present=('cutout_mm', 'frame_od_mm', 'depth_mm') missing=('cone_depth_mm', 'surround_width_mm', 'dust_cap_diameter_mm', 'mounting_depth_behind_baffle_mm')
```

No GPU job, BL solve, queue action or git mutation was performed.
