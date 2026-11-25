# Rolled and Lamé directivity attribution, early-wall levers and source angle

2026-11-24/25, canonical checkout, v11 frozen. Simulated matched verifies (BEAT CUDA, 29 frequencies, 1024-point
balloon DI, freestanding quarter model, 36 mm / 2° assumed source unless stated). Not physical-driver measurements.
Predictions and pass rules were written first: [PREDECLARED.md](PREDECLARED.md).

## What the evidence says

- **The rolled 2 kHz H overshoot comes from the H amplitude.** H-only +10° reproduces it (+9.1° at 2037 Hz) with V
  unchanged within 1.6°. **The V gain is separable in V** (V-only +6° gives −4.7° at 2 kHz and +2.9° at 8 kHz) and it
  carries the **whole J gain** of the combined variant (7.713 vs 7.709), but it is not perfectly clean: it also widens
  H by +3.1° at 2 kHz, outside my predeclared ±2° clause.
- **6–8 kHz H is governed by the wall angle at roughly 20–40 % of the pre-roll arc (≈ 55–110 mm of H wall from the throat
  on both bodies), not by the late body or the return.** Moving the same existing law earlier (window 0.12/0.40/0.65, H +10°) widened
  H by +7.6…+8.4° at every 6–8 kHz bin, put 8 kHz H inside the corridor (54.8 → 63.1°), pulled 2 kHz H back from the
  90° edge to 79.4°, and cut J 8.121 → 6.533. The late window (0.55/0.75/0.94) slightly narrowed 6–8 kHz (−1.5…−2.1°)
  and widened 1.3–1.8 kHz; it has no useful HF authority.
- **Lamé: both a body schedule and the transition timing widen 6–8 kHz H with the throat, rim and return held.**
  Earlier round→Lamé transition (`morph_frac` 0.60 → 0.40): H +5.3…+5.6°, V +3.7…+5.1°, J 11.221 → 9.084, but H at
  2.3–3.5 kHz narrows to 60–64°. H mid-gain −2 mm (sign mirror of the rejected +2 mm): H +3.9…+4.4°, H below
  3.5 kHz moves ≤ 0.4°, V −0.7…−1.1°, J → 10.736. The later transition (0.85) behaves as predicted: worse H (−4.1…−4.4°).
  Neither lever brings Lamé 8 kHz H to 60° (best 51.6°) or 8 kHz V to 40° (best 37.8°).
- **A simple geometric heuristic predicted the HF direction and size.** Width(f) ≈ 2 × the wall angle at a fixed
  station, taken half an octave toward the throat, with a gain fitted on the two earlier solves. With gains frozen
  before this batch, mean 6–8 kHz H errors were ≤ 2° on all eight candidates; its 2 kHz calls are unreliable for the
  broad Lamé morph changes. It is a screening device, not evidence.
- **The gains survive one mesh refinement.** Re-solved at epw 9 (6.6–7.8k DOF), every candidate-minus-anchor delta
  at the predeclared bins stays within 0.3° of its epw-6 value for rolled early +10°/+20° and Lamé `morph_frac`
  0.40; the anchors themselves move ≤ 0.25°. Lamé H mid −2 mm was not re-solved at epw 9.
- **A wider source exit angle is not a lever by itself in this model.** Changing the Lamé anchor's assumed exit
  2° → 10° curved the source-cap patch (sag 0.31 → 1.58 mm, confirmed in the mesh) and moved no H, V or diagonal
  width by more than 0.05° (J 11.2206 → 11.2205). A wider-exit driver can matter only through a horn entrance that
  continues its angle. Beyma states exit angles of 7–29.5° for its 1", 1.4" and 2" drivers without saying half or
  included; the CP-850Nd datasheet gives neither an angle nor the outlet section.

## Rolled hybrid `fa5b207bca6d`

Anchor: [anchor_rolled_neutral.yaml](../size_aware_2026-11-24/anchor_rolled_neutral.yaml) (law `rolled_family_rect_cd_v1`,
neutral amplitudes). Every candidate changes only the knobs shown. Geometry ([controls_geometry.json](controls_geometry.json)):
throat station, lip, final 10 % of stations, both returns and the rim are **bit-identical** to the anchor for all
rolled candidates (max deltas 0.0000 mm); extents stay 581.1 × 365.9 × 214.4 mm; pre-roll z monotone; no constriction.
The H-only and V-only displacements superpose to the combined variant within 6e-14 mm (geometry is exactly
additive; the acoustics need not be).

| Candidate | Change | J | H 2037 | H 4037 | H 6085 / 6977 / 8000 | V 2037 | V 8000 | Diag 8000 | DI 8k | min Re z | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| anchor | — | 8.121 | 90.1 | 70.4 | 62.5 / 59.0 / 54.8 | 74.0 | 47.7 | 47.8 | 14.54 | 0.991 | H misses 6977–8000 |
| H+10/V+6 (prior) | window .30/.60/.88 | 7.709 | 102.2 | 76.7 | 63.8 / 58.5 / 53.9 | 69.2 | 51.6 | 51.9 | 14.18 | 1.002 | partial |
| `rolled_h10_v0` | H +10 | 8.135 | 99.2 | 78.0 | 64.8 / 59.7 / 54.8 | 73.7 | 48.7 | 46.3 | 14.63 | 1.000 | **causes 2 kHz overshoot** (pass) |
| `rolled_h0_v6` | V +6 | 7.713 | 93.3 | 69.7 | 61.7 / 57.8 / 54.1 | 69.3 | 50.6 | 53.2 | 14.11 | 1.002 | V separable; H +3.1 at 2 kHz (fails ±2 clause) |
| `rolled_h10_early` | H +10, window .12/.40/.65 | **6.533** | 79.4 | 72.0 | 70.1 / 67.3 / **63.1** | 74.0 | 46.2 | 54.7 | 13.71 | 0.952 | **HF authority** (pass) |
| `rolled_h20_early` | H +20, same window | 6.001 | 70.8 | 83.0 | 78.2 / 76.2 / 70.5 | 74.1 | 46.9 | 60.0 | 12.63 | 0.907 | pass on HF; 2.7 kHz dip to 61.1°, ripple ×3.9 |
| `rolled_h10_late` | H +10, window .55/.75/.94 | 8.802 | 93.3 | 70.8 | 60.4 / 57.5 / 53.1 | 75.1 | 46.7 | 47.6 | 14.49 | 0.996 | no HF authority (−1.5…−2.1) |

Raw v11 terms (not weighted contributions): `dislope` anchor 5.84 → early10 4.12 / early20 2.20; `diag` 6.75 →
5.30 / 4.65; `offaxis_smooth` 1.43 → 1.00 / 1.07; `rip` 0.044 → 0.075 / 0.170; `di_roughness` 0.23 → 0.46 / 0.76;
`flat` 0.187 → 0.150 / 0.274. No H/V multilobe bins anywhere; loading penalty zero for all. On-axis 1–8 kHz
residual about a log fit: anchor 0.27 dB, early10 0.21, early20 0.39.

The early-window candidate holds H inside 60–90° from 1.78 to 8 kHz; its remaining H misses (896–1549 Hz) and all
V misses (≤ 4 kHz, V too wide) are the mouth-limited low band and are unchanged. It narrows V by 0.8–1.6° at 6–8 kHz
(still 46–51°, in corridor). Its H curve dips to 69–70° at 3–3.5 kHz, between 74.8° at 2.3 kHz and 73.2° at 4.6 kHz.

**Return onset was not solved.** It is a separate variable (`rolled_terminal_family`, H-only C-return). Its one
solve (2026-11-20, a related parent, screen tier) moved 8 kHz H by 0.4° and raised ripple 0.029 → 0.159, and the
late-window result here points the same way: the returned section does not control 6–8 kHz on this body. Radial
relief (`g_inward_*`) and axial relief (`g_axial_*`) were held at the anchor values in every candidate.

## Klangfilm–Lamé V4 `0782945027ae`

Anchor: [anchor_lame_neutral.yaml](../size_aware_2026-11-24/anchor_lame_neutral.yaml) (`klangfilm_lame_hv_cd`, blend 0
= exact parent). Throat station and lip delta 0.0000 mm and rim unchanged for all three. Return, measured as distance
from the candidate's sampled return to the anchor's return curve: morph 0.40 ≤ 0.0045 mm, H mid −2 mm ≤ 0.075 mm,
morph 0.85 ≤ 0.72 mm (the late gate shifts arc-length resampling by up to 3.1 mm along the same curve).

| Candidate | Change | J | H 2037 | H 3070 | H 6085 / 6977 / 8000 | V 2037 | V 6085 / 8000 | Diag 8000 | DI 8k | min Re z | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| anchor | — | 11.221 | 75.5 | 68.4 | 52.7 / 49.2 / 46.0 | 81.0 | 40.0 / 34.1 | 35.6 | 16.39 | 0.688 | H misses 4.6–8 kHz |
| H mid +2 mm (prior) | blend 1 | 12.028 | 75.6 | 68.9 | 48.9 / 45.8 / 43.1 | 81.0 | 40.9 / 34.7 | 34.6 | 16.59 | 0.637 | rejected |
| `lame_morph_040` | `morph_frac` 0.40 | **9.084** | 69.5 | 60.7 | 58.0 / 54.8 / 51.6 | 82.4 | 45.1 / 37.8 | 43.6 | 15.41 | 0.717 | **pass**; H 2.3–3.5 kHz 60–64° |
| `lame_hmid_m2` | blend 1, H mid −2 mm | 10.736 | 75.3 | 68.0 | 56.7 / 53.6 / 49.9 | 81.0 | 39.3 / 33.1 | 36.7 | 16.12 | 0.747 | **pass**; clean H-only |
| `lame_morph_085` | `morph_frac` 0.85 | 12.294 | 79.0 | 66.3 | 48.3 / 45.0 / 41.9 | 76.0 | 41.2 / 37.3 | 36.3 | 16.40 | 0.689 | fail (as predicted) |

Raw terms: `dislope` 9.51 → 6.84 (morph 0.40) / 8.77 (H −2); `diag` 10.55 → 7.23 / 9.96; `rip` 0.017 → 0.044 /
0.015; `offaxis_smooth` 2.04 → 1.78 / 2.18. No multilobe bins; loading penalty zero; min Re(z) from 900 Hz improves
in both passing candidates. On-axis residual 0.18 dB anchor, 0.32 morph 0.40, 0.20 H −2.

The +2 mm and −2 mm arms are close to antisymmetric (HF −2.9…−3.9° vs +3.9…+4.4°), so this Phase A interior term is a
near-linear H-only lever over ±2 mm. The entrance angles (`theta_h0/v0`) were not changed, because they alter the
throat slope.

## Figures

- [rolled_curves.png](rolled_curves.png), [lame_curves.png](lame_curves.png): H, V, diagonal −6 dB widths and DI,
  anchor in grey, corridor band shaded.
- [rolled_isobars.png](rolled_isobars.png), [lame_isobars.png](lame_isobars.png): H and V isobars, red = −6 dB.
- [profiles_same_scale.png](profiles_same_scale.png): H and V sections and mouth rim at one scale, plus wall angle
  against arc fraction.
- [renders/views_same_scale.png](renders/views_same_scale.png): meshed 3D views (front, 3/4, side) at one scale,
  anchors vs `rolled_h10_early`, `rolled_h20_early`, `lame_morph_040`, `lame_hmid_m2`.
- `renders/card_*.png`: the owner's design card (two views, full-width H and V dispersion maps, J within the brief,
  loading line) for the same six designs.

## Refined-mesh gate (predeclared)

Same configs with `mesh.epw` 6 → 9 only. Entries are candidate − anchor at epw 6 / at epw 9 (degrees). Pass = HF
deltas keep sign and at least half their size and the 2 kHz H change keeps its sign.

| Pair | J epw 6 / 9 | ΔH 2037 | ΔH 6085 | ΔH 6977 | ΔH 8000 | ΔV 6085 | ΔV 8000 | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| rolled anchor | 8.121 / 8.082 | anchor H moves −0.05 / +0.05 / +0.12 / +0.25 (2037/6085/6977/8000) | | | | | | control |
| `rolled_h10_early` | 6.533 / 6.497 | −10.7 / −10.7 | +7.6 / +7.7 | +8.3 / +8.4 | +8.3 / +8.2 | −0.8 / −0.8 | −1.4 / −1.2 | **pass** |
| `rolled_h20_early` | 6.001 / 6.001 | −19.4 / −19.4 | +15.7 / +16.0 | +17.2 / +17.2 | +15.6 / +15.3 | −1.8 / −1.8 | −0.7 / −0.8 | **pass** |
| Lamé anchor | 11.221 / 11.203 | anchor H moves −0.03 / +0.11 / +0.16 / −0.11 | | | | | | control |
| `lame_morph_040` | 9.084 / 9.059 | −6.0 / −6.0 | +5.3 / +5.1 | +5.6 / +5.7 | +5.6 / +5.9 | +5.1 / +5.1 | +3.7 / +3.7 | **pass** |

This is one refinement step of the element size on the same generated surface grid (rolled 65 × 129, Lamé 19 × 65
stations), not a convergence study, and the same BEAT backend. Full values: `results.json` → `mesh_gate`.

## Wider-exit compression drivers and the 2-inch option (separate source identities)

**What the exit angle does in this model.** For grid horns the brief's `driver.exit_angle_deg` sets the curvature
of the assumed throat source cap (radius 18 mm / sin θ). For the rolled family it is also the wall tangent at the
coupling plane (`rolled_family._source_check`). For the Lamé it changes **no wall**; that horn already enters at a
~9.94° chord, so the 2° source is a mismatch there.

- **Rolled anchor:** accepts 3–9° and refuses 10° (`relief or throat_hv_ratio creates a constriction before the
  mouth roll`). At 8° only the throat blend (u < 0.3) changes (max 2.28 mm): the H wall rises to 8.4° at the throat
  and then dips, and the V wall dips to 1.6° near u 0.2 before rejoining the same body. The station map sees no
  2–8 kHz lever there, so it was not solved. A wide-exit rolled horn needs the early wall to continue the driver's
  angle, which is the early-window law above, not a source swap.
- **Lamé anchor at 10°:** wall arrays bit-identical; only the source cap changes. Solved as `lame_src10` (new source identity, same mesh
  spec hash, different mesh bytes): the source-cap patch sag went 0.31 → 1.58 mm, the predicted values, and every H,
  V and diagonal width at all 29 frequencies moved by ≤ 0.05°; min Re(z) 0.688 → 0.686; J 11.2206 → 11.2205. The
  predeclared ±1.5° band holds with room to spare. In this model the cap curvature at a 36 mm throat does not steer
  directivity, so a wider-exit driver helps only if the horn's entrance continues its angle. The cap is an assumed
  spherical patch, not a measured driver wavefront; a real phase-plug exit can differ.

**Manufacturer-stated exit angles (36 mm and 50.8 mm unless noted).** Beyma's product pages list an "Exit angle" row;
none says whether it is a half-angle (from the axis) or an included angle, and no datasheet drawing I could read
shows the outlet section. Read 2026-11-24:

| Driver | Exit | Stated "Exit angle" | Range / crossover | If half-angle | If included |
|---|---|---:|---|---:|---:|
| Beyma CD-2514Nd (/PK, /PT, /Ti) | 1.4" | 29.53° | 600 Hz–20 kHz / ≥ 800 Hz | 29.5° | 14.8° |
| Beyma CD-2514Fe (/PK, /PT, /Ti) | 1.4" | 18.12° | 600 Hz–20 kHz / ≥ 800 Hz | 18.1° | 9.1° |
| Beyma CD-14Fe | 1.4" | 16.32° | 500 Hz–16 kHz / ≥ 800 Hz | 16.3° | 8.2° |
| Beyma SMC-65Nd | 1.4" | 15° | 600 Hz–20 kHz / ≥ 800 Hz | 15° | 7.5° |
| Beyma CP-755Nd | 1.4" | "12º 60´" (12.6° or 13°) | 600 Hz–20 kHz / ≥ 800 Hz | 12.6–13° | 6.3–6.5° |
| Beyma CP-755Ti | 1.4" | 8° | 600 Hz–20 kHz / ≥ 800 Hz | 8° | 4° |
| Beyma CP-385Nd | 1" | 16°30´ | 800 Hz–20 kHz / ≥ 1.5 kHz | 16.5° | 8.3° |
| Beyma CP-850Nd | 2" (50.8 mm) | 7° | 500 Hz–20 kHz / ≥ 500 Hz, 12 dB/oct | 7° | 3.5° |

Nd and Fe versions of one family differ (29.53° vs 18.12°), so an angle never carries across versions. No angle is
published for the HF1440 this brief assumes, for BMS 4554 (datasheet read: none), or for B&C models found. A
community table on diyAudio (thread 200340) lists BMS and B&C angles, but the site blocked automated reading, so
none of its numbers are used here.

**CP-850Nd status (unchanged blocker).** The 02/14 datasheet gives the 50.8 mm throat, four M6 holes on a 101.6 mm
circle, 165 × 114 mm body, 0.5–20 kHz, ≥ 500 Hz crossover at ≥ 12 dB/oct, and a response measured on the TD-460/N
horn. It does **not** list an exit angle; the drawing shows only the outer body and a 50 mm bore. The 7° exists
only on the product page. Beyma sends 2D drawings through a request form on that page; the outlet section (bore
length and cone) and the angle convention must come from that drawing or from measuring a unit before a 2" source
is modelled. Use a new source identity (driver id, 50.8 mm, angle with its convention, cap model, any adapter) and
compare only inside it.

**How to study a wider-exit driver here (proposed, not run).** Because the cap alone is inert, the test is a
*matched entrance*: one source identity per driver (`driver.exit_angle_deg` = its stated angle under one declared
convention, 36 mm), and the horn's entrance wall set to the same angle. The Lamé is the natural first case: its
Phase A entrance angles `g_theta_h0_deg`/`g_theta_v0_deg` (anchor chords 9.94°) can be set to 12.6° (CP-755Nd read as
a half-angle) or 15° (SMC-65Nd), with `g_cd_core_blend` 1, mid gains 0, and everything else at the anchor. Controls:
the Lamé anchor and `lame_src10` (cap-only change, already shown inert). This changes the throat slope, so it is a
separate experiment from the body levers, with the same geometry checks (rim, return, monotone radius) and
the same HF promotion rule. CPU check: both settings resolve, with maximum wall displacement 0.55 mm (12.6°) and
1.06 mm (15°), lip unchanged, final 10 % ≤ 0.007 mm, extents 489.7 × 281.0 × ≤ 208 mm. Those displacements are small
and sit near the throat, ahead of the 55–110 mm region that carried the HF effect here, so expect a modest result.
The rolled anchor cannot take more than 9° without a relief change, so a wide-exit rolled horn needs its own
construction.

Sources: [Beyma CP-850Nd page](https://www.beyma.com/en/products/c/compression-driver/1CP85ND8/motor-cp-850nd-8-oh/),
[CP-850Nd datasheet](https://www.beyma.com/speakers/Fichas_Tecnicas/beyma-speakers-data-sheet-compression-driver-CP850Nd.pdf),
[CP-755Nd](https://www.beyma.com/en/products/c/compression-driver/1CP755ND8/motor-cp-755nd-8-oh/),
[CP-755Ti](https://www.beyma.com/en/products/c/compression-driver/1CP755TI8/motor-cp-755-ti-8-oh/),
[SMC-65Nd](https://www.beyma.com/en/products/c/compression-driver/1SMC65ND8R/motor-smc-65-nd-8-oh/),
[CD-14Fe](https://www.beyma.com/en/products/c/compression-driver/1CD14FE8/motor-cd-14fe-8-oh/),
[CD-2514Nd/Ti](https://www.beyma.com/en/products/c/compression-driver/1CD2514NDTI8/motor-cd-2514nd-ti-8-oh/),
[CD-2514Fe/Ti](https://www.beyma.com/en/products/c/compression-driver/1CD2514FETI8/motor-cd-2514fe-ti-8-oh/),
[CP-385Nd](https://www.beyma.com/en/products/c/compression-driver/1CP385N8/motor-cp-385nd-8-oh/),
[BMS 4554 datasheet](https://www.Lautsprechershop.de/pdf/bms/bms-4554.pdf),
[diyAudio thread 200340 (not read)](https://www.diyaudio.com/community/threads/waveguides-and-compression-driver-exit-angles.200340/).

## Geometry limit found after this batch (2026-11-25)

The levers above are small perturbations of non-CD parents, and that is now the binding limit for H. Both mouths
already sit where a straight wall would give roughly the target (rolled roll-on chords 41.5° H / 27.5° V, Lamé
38.5° / 24.8°), but the parents hold 5–23° through the first 30–45 % of the wall, where 6–8 kHz is decided. A CPU
prototype that blends each row's wall angle toward a solved CD backbone, keeping the roll-on station, return and
rim bit-identical, resolves on both anchors ([backbone_homotopy_proto.py](backbone_homotopy_proto.py),
[backbone_vs_parent.png](backbone_vs_parent.png)). V is limited separately by where each mouth starts to roll.
Research, sources and the proposed construction:
[RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md](../../research/typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md).
The fixed-candidate brackets below remain valid tests of the existing laws; the backbone kernel is the larger step.

## Next experiment, one per family (fixed candidates, no search yet)

### Rolled: dose bracket of the early H window

- **Anchor:** `fa5b207bca6d`, [anchor_rolled_neutral.yaml](../size_aware_2026-11-24/anchor_rolled_neutral.yaml),
  unchanged brief/source/mesh/solve.
- **Changed knobs:** `g_cd_start_s` 0.12, `g_cd_peak_s` 0.40, `g_cd_end_s` 0.65, `g_cd_v_deg` 0, and
  `g_cd_h_deg` ∈ {12.5, 15, 17.5}. Radial relief, axial relief, the return and every parent knob stay at the
  anchor values.
- **Controls already solved:** anchor (epw 6 and 9), `rolled_h10_early` and `rolled_h20_early` (epw 6 and 9) bracket
  the dose: 10° is steady but leaves 8 kHz at 63°; 20° reaches 70–78° above 4 kHz but dips to 61° at 2.7 kHz and
  roughly triples ripple and DI roughness.
- **Geometry acceptance (CPU, before any solve):** `controls_geometry.py` reports throat, lip, final 10 %, both
  returns and the rim at 0.0000 mm; extents 581.1 × 365.9 × 214.4 mm; pre-roll z monotone; no constriction; DOF
  under the verify cap with `tools/shape_check.py --mode verify`.
- **Budget:** three epw-6 verifies (~50 s each, 3.5–4.0k DOF) and one epw-9 re-solve of the best (~95 s): about
  five minutes of GPU with hygiene.
- **Promotion:** H ≥ 62° at all five 6–8 kHz bins; H between 65° and 85° at every bin from 2 to 4 kHz (no mid dip);
  V at 8 kHz ≥ 45°; raw `rip` ≤ 0.10 and `di_roughness` ≤ 0.50; min Re(z) from 900 Hz ≥ 0.90; J ≤ 6.53; no
  multilobe bins; the epw-9 deltas keep sign and at least half their size.
- **After that, not before:** the V +6° gain lives in the original window (0.30/0.60/0.88) and the kernel shares
  one window between H and V, so "early H + original V" needs a versioned kernel with per-plane windows. That is a
  construction-law change: cite [ROLLED_CD_WALL_ANGLE_RESEARCH_2026-11-20.md](../../research/typologies/ROLLED_CD_WALL_ANGLE_RESEARCH_2026-11-20.md)
  and add the per-plane extension under the typology-research protocol, with a zero-control identity test.

### Lamé: additivity of the two body levers

- **Anchor:** `0782945027ae`, [anchor_lame_neutral.yaml](../size_aware_2026-11-24/anchor_lame_neutral.yaml).
- **Changed knobs:** (A) `g_morph_frac` 0.40 + `g_cd_core_blend` 1 + `g_h_mid_gain_mm` −2; (B) the same with
  `g_h_mid_gain_mm` −3; (C) `g_morph_frac` 0.50 + `g_cd_core_blend` 1 + `g_h_mid_gain_mm` −2 (to recover the
  2.3–3.5 kHz H narrowing that 0.40 causes). Throat entrance angles stay at the parent chords (9.94°/9.94°), V mid
  gain 0, join 0.65, `end_frac`, `aspect`, `lame_p`, `rim_sweep_ratio` unchanged.
- **Predictions (station map, H gain 0.72, V gain refit 0.44 on `lame_morph_040`):** A: H 6–8 kHz +7.9…+8.9°,
  V +1.9…+4.0°; B: H +9.2…+10.5°; C: H +4.7…+6.0°, V −0.3…+0.8°. Simple addition of the two measured single levers
  gives about +9.2…+10.0° for A. Even then 8 kHz H stays near 55–56°, below the 60° corridor floor.
- **Controls already solved:** anchor, `lame_morph_040`, `lame_hmid_m2`, and the +2 mm arm.
- **Geometry acceptance:** throat-station and lip delta 0.0000 mm, rim unchanged, return within 0.1 mm of the anchor
  curve, Phase A monotone-radius checks, extents 489.7 × 281.0 × ≤ 208 mm.
- **Budget:** three epw-6 verifies plus one epw-9 re-solve of the best, about five minutes.
- **Promotion:** H gain ≥ +8° at all five 6–8 kHz bins; H ≥ 62° at every bin from 2 to 4 kHz; V at 8 kHz not below
  `lame_morph_040` (37.8°); min Re(z) ≥ 0.70; J < 9.08; epw-9 deltas keep sign and half size.
- **If the body levers saturate below 60° at 8 kHz**, the remaining lever is the throat: either the Phase A
  entrance angle (changes the throat slope, so it needs its own control) or a matched wider-exit source (below).
  The Phase B core is still excluded because it removes the return.

## Ruled in, unresolved, and GPU jobs actually run

**Ruled in (simulated, matched, refined-mesh checked where stated):** the H amplitude causes the rolled 2 kHz
overshoot; the V amplitude alone carries the combined variant's J gain; on both bodies, 6–8 kHz H follows the wall
angle at about 20–40 % of the pre-roll arc (≈ 55–110 mm of H wall); the rolled early window gives the corridor from 1.8 to 8 kHz in H;
moving the Lamé transition earlier or relaxing its H interior both widen 6–8 kHz H without touching throat, rim or
return.

**Ruled out for 6–8 kHz H on these anchors:** later wall development (rolled late window, Lamé `morph_frac` 0.85),
the positive Lamé H mid gain, and an 8° source on the rolled anchor (geometry predicts no HF lever).

**Unresolved:** spatial convergence beyond one refinement step (epw 6 → 9, same surface grid); an independent
backend (bempp) cross-check; per-plane windows for the rolled kernel; whether the Lamé can reach 60° H at 8 kHz
without changing its throat; real-driver wavefronts for every source angle (the cap is an assumption); the CP-850Nd
outlet geometry and angle convention; low-band V control (mouth-limited, unchanged by every body change here).

| Batch | Job | Run dir | DOF | Wall s | VRAM baseline → peak MiB |
|---|---|---|---:|---:|---|
| launch attempt | 8 jobs, all `LAUNCH FAILED` (WinError 2), **no solve** | `runs/nights/directivity_attribution_2026-11-24_launchfail/` | — | 0 | 1621 (no change) |
| batch 1 | `rolled_h10_v0` | `runs/20261124T234947Z-verify-f6bdc5` | 3537 | 49.9 | 1623 → 1885 |
| batch 1 | `rolled_h0_v6` | `runs/20261124T235039Z-verify-79f596` | 3516 | 48.0 | 1622 → 1877 |
| batch 1 | `rolled_h10_early` | `runs/20261124T235127Z-verify-faa19b` | 3668 | 48.5 | 1637 → 1898 |
| batch 1 | `rolled_h20_early` | `runs/20261124T235217Z-verify-81748c` | 3960 | 51.6 | 1612 → 1925 |
| batch 1 | `rolled_h10_late` | `runs/20261124T235310Z-verify-17ca66` | 3482 | 44.9 | 1625 → 1894 |
| batch 1 | `lame_morph_040` | `runs/20261124T235357Z-verify-dd210e` | 3529 | 46.4 | 1621 → 1920 |
| batch 1 | `lame_morph_085` | `runs/20261124T235445Z-verify-34b4f3` | 3542 | 46.0 | 1648 → 1892 |
| batch 1 | `lame_hmid_m2` | `runs/20261124T235533Z-verify-295ac0` | 3541 | 48.6 | 1638 → 1891 |
| batch 2 | `rolled_anchor_epw9` | `runs/20261124T235806Z-verify-390ff2` | 6603 | 93.7 | 1619 → 2193 |
| batch 2 | `rolled_h10_early_epw9` | `runs/20261124T235942Z-verify-78be76` | 6732 | 90.8 | 1652 → 2209 |
| batch 2 | `rolled_h20_early_epw9` | `runs/20261125T000116Z-verify-47bbc9` | 7048 | 98.0 | 1640 → 2229 |
| batch 2 | `lame_anchor_epw9` | `runs/20261125T000255Z-verify-fe67fc` | 7773 | 114.2 | 1642 → 2309 |
| batch 2 | `lame_morph_040_epw9` | `runs/20261125T000451Z-verify-c93e49` | 7789 | 114.3 | 1618 → 2310 |
| batch 2 | `lame_src10` | `runs/20261125T000649Z-verify-986c59` | 3536 | 48.2 | 1619 → 1863 |

14 solves, 944 s of recorded job wall time (batch 1 385 s, batch 2 559 s). Each solved job ran with `HORNLAB_GPU_LOCK=refuse`, one at a time, with the runner's `gpu-clean --lane gpu`
before and after; VRAM returned to its pre-job level each time. The baseline includes the desktop and the running
GUI (~1.6 GiB). These are single observations on this machine, not guaranteed costs.

## Reproduce

```powershell
.venv\Scripts\python.exe docs/evidence/directivity_attribution_2026-11-24/controls_geometry.py
.venv\Scripts\python.exe docs/evidence/directivity_attribution_2026-11-24/station_map.py
.venv\Scripts\python.exe tools/run_campaign_night.py --night docs/queue/directivity_attribution_2026-11-24.yaml
.venv\Scripts\python.exe tools/run_campaign_night.py --night docs/queue/directivity_attribution_b2_2026-11-24.yaml
.venv\Scripts\python.exe docs/evidence/directivity_attribution_2026-11-24/analyze.py
```

The two queue commands solve on the GPU; check the lock with `tools/night_status.py` first. `analyze.py` reads the
nights' `summary.jsonl` for run directories, so a re-run produces new run IDs.
