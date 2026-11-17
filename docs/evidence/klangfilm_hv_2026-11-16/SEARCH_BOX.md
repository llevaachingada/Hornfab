# Klangfilm-Lame H/V Phase A - Stage A search-box lawfulness

**CPU geometry only.** No meshing, BEM, queue admission or acoustic claim. Config `examples\typologies\klangfilm_hv_2026-11-16\configs\stage_a_search.yaml` (sha256 `2ce424a682d5a611...`), kernel `cbb23cc02d9b5d13...`.

- Samples: **200** Latin-hypercube points over the four searched knobs.
- Lawful: **200**; refused: **0**; verdict: **LAWFUL**.
- Box corners (2^4 extreme combinations): **16/16** lawful.
- Seed materialised: shape (19, 65, 3), mode `hv_throat_phase_a`, envelope_ok=True, digest `a032f66049882c87...`.

## Declared box

| knob | lo | hi | searched | largest lawful value above the seed (probe ceiling) |
|---|---|---|---|---|
| `g_theta_h0_deg` | 6 | 17 | True | none up to 25 |
| `g_theta_v0_deg` | 3 | 13 | True | 17.113 |
| `g_h_mid_gain_mm` | 0 | 20 | True | 21.623 |
| `g_v_mid_gain_mm` | 0 | 3.75 | True | 5.392 |

## Lawful range inside the box

- W 541.26-541.28 mm, H 260.73-260.74 mm, D 233.67-233.69 mm (envelope 600 x 480 x 480).

No refusal: every sampled point produced a finite, non-decreasing forward radius on a round 18 mm throat, with the join before the parent's axial turn.

## Why these bounds and not the handoff's first guesses

The 2026-11-16 handoff proposed `h_mid_gain_mm -12..+35` and `v_mid_gain_mm -20..+15`. Negative gains are not merely aggressive here, they are **infeasible**: the B2 basis ramps as t^3, so a negative mm gain locally dominates the wall slope. Measured at the canonical incumbent (join 0.65): the V radius falls below the 18 mm throat at about -5.2 mm and stops being non-decreasing at about -0.04 mm; the handoff's -8 mm seed reaches 15.02 mm at z ~ 61.8 mm. The kernel refuses instead of clamping, so the Stage A box must be the positive quadrant. Measured positive walls are 20.5-21.5 mm (H) and 4.0-5.5 mm (V) depending on the throat angle; 20.0 and 3.75 keep margin. A genuinely tighter interior needs the Phase B integrated-slope core, where a lower-but-positive wall slope is monotone by construction.

Three positive walls are real too, from the same slope budget: the H gain (~21.6 mm), the V gain (~5.4 mm at theta_V 5 deg, falling to ~4.0 mm at 13 deg), and theta_V itself at about 17.1 deg. The last one is worth stating because it is counter-intuitive: a steeper early V slope overshoots and then the aspect gate pulls b back, so b stops being non-decreasing. Every declared bound sits inside its wall, and all 2^4 box corners are lawful.

Re-run: `.venv\Scripts\python.exe tools/geometry/klangfilm_hv_search_box.py --samples 200`
