# Spiral pucker vs ATH-style radial ridges (2026-11-15)

**Status:** research note + one new shape-only config. No GPU solve was run; the 2026-11-15 17:15 owner pause still binds. The new config is uncommitted. This note records why the current rolled-spiral “pucker” bows the horizontal/vertical faces the wrong way, why the screenshot’s per-direction-law horn does the same with the visible slider values, and which existing radial-relief path is the correct ATH-like alternate.

## Plain-English summary

- **Two different mechanisms are being conflated.** The screenshot’s “Per-direction law (Ath CORE)” card changes the *wall angle by direction* (radial). The rolled ES spiral’s `pucker_h_mm` / `pucker_v_mm` move the wall *forward and backward along the horn axis* (axial). They are not the same shape control.
- **The rolled spiral’s pucker bows the wrong way.** Positive pucker pushes the horizontal and vertical faces toward the listener and pulls the diagonal back. That is exactly a fore-aft bulge of the H/V faces and a valley along the X. It is also left switched on through the 270-degree lip, so the rim goes wavy.
- **The screenshot’s per-direction values are vertically over-flared.** `az_sf_b = 1.2` widens the vertical; CORE uses `0.618` to narrow it. `az_a_sf_amp = 11.5` (CORE: 35) weakens the diagonal, and `az_a_cos_amp = -15` narrows the horizontal. The result is a horn whose vertical and diagonal angles are about 20 degrees above the horizontal: the vertical faces bow out, and the diagonal is not a distinct ridge.
- **ATH’s ridges are radial and intentional.** Tritonia and CORE open the diagonal 7–10 degrees wider than H/V because the rectangular mouth has a longer diagonal path. The four triangular panels are the integrated result of that per-direction flare, with the diagonal as the ridge. It is a smooth coverage law, not a decorative crease.
- **The correct spiral alternate already exists.** `hornlab_search/design/generators/rolled_family.py` has a radial mode: pull the H/V wall centres inward, leave the diagonal alone. That makes the diagonal a ridge and the four panels concave. The new `rf__rect_radial_wide_v7` exposes 0–30 / 0–40 mm inward on the same spiral base; it meshes and the existing rolled-family tests pass.
- **Outward is the sign flip.** Negative H/V push the axes out and leave the diagonal as a valley. The current v1 generator rejects negative values; exposing it in search should be a recipe-level `radial_direction` / `radial_outward` mode, not a signed numeric knob.
- **The spiral still narrows.** The base log spiral has no constant-angle section; the beam narrows with frequency by construction. Radial relief gives the ATH ridge look, but it does not turn the spiral into a constant-directivity horn. The CD ATH/R-OSSE cells remain the sound-first path.

## What was compared

| Geometry | What it is | Front-view result |
|---|---|---|
| `hl__rolled_es_spiral_v7` seed | 542 × 299 × 238 mm, decay 0.7, terminal 270°, axial pucker H 6 / V 8 | Four broad panels; H/V faces forward, diagonal valley; boomerang side view; slightly wavy rim |
| `rf__rect_radial_wide_v7` (new) | Same spiral base, radial inward H 12 / V 16, window 0.50/0.80/0.96 | Diagonal ridges and triangular facets; clean lip; slight waist at the relief peak |
| `hl__crowe_x_osse_cd_v7` seed | OSSE CD wall + superformula X + 130° rolled lip, 588 × 398 × 244 | Square-ish mouth, thick rim, four facets and X creases; closest saved cell to the screenshot |
| `hl__ath_core_petal_hvlaw_v7` seed | ATH CORE-style per-direction law, 80 × 50 landscape compromise, 545 × 360 × 353 | Smooth CD body with four gentle facets; no thick roll; the best 80 × 50 acoustic starting point of the set |
| Scratch inward/outward 16/22 mm | Same spiral base, signed radial relief | Inward: strong diagonal ridges/waist. Outward: H/V faces bulge, diagonal valley |

Contact sheet (durable): `docs/renders/2026-11-15-pucker/pucker_compare.png`.
Range sheet (durable): `docs/renders/2026-11-15-pucker/relief_versions.png` (control, 3/4, 6/8, 12/16, 16/22 inward, 16/22 outward).
Three-view card: `docs/renders/2026-11-15-pucker/rf__rect_radial_wide_v7_card.png`.
Scratch source images: `scratch/render_current/`, `scratch/render_crowex/`, `scratch/render_petal/`, `scratch/render_signed/`.

## Finding 1 — the rolled spiral’s axial pucker

In `tools/geometry/rolled_rect.py` and `hornlab_search/design/generators/_rolled_rect_v1.py`:

```text
zz += (pucker_h*cos^2(psi) + pucker_v*sin^2(psi)) * window * cos(4*psi)
window = smoothstep((t - pucker_start) / (pi - pucker_start))
```

- This is a **z-only** displacement. At `psi = 0` and `90` degrees it adds `+H` / `+V` (forward); at the normalized diagonal `psi = 45` degrees it adds `-amp` (backward). The x/y outline is unchanged.
- The window reaches 1 at 180 degrees and stays 1 to the 270-degree terminal. The entire back roll and lip are displaced, not just a local pucker. The audit already noted that high-pucker corners add visible rim ripples.
- The current search bounds are `0..+18` mm H and `0..+24` mm V. There is no negative side, so the current cell cannot ask for the inward direction.
- `knobs_rows.py` describes `pucker_h_mm` / `pucker_v_mm` as “inward pucker of the rolled-rectangle rim”, but the code moves z. That documentation/code mismatch should be corrected.
- The base log spiral adds its own bow: `z` peaks at 90 degrees, the radius keeps growing to about 180 degrees, then the wall rolls back to the 270-degree lip. The side view is the boomerang/trumpet shape. The wall angle is essentially the turning parameter, so there is no constant-angle conical section; the beam narrows with frequency by construction. This matches the stored 33-row rescore (smooth J 14.3–15.9, `diag` 7.0–7.7) and Crowe’s own narrowing ES polars.

**Conclusion:** the current spiral pucker is an axial corrugation, not an ATH radial ridge. Flipping its sign would move the diagonal forward in z, but it would still be an axial corrugation with the same saturating window and rim wave. It is not the correct ATH mechanism.

## Finding 2 — the screenshot’s per-direction law

The visible `az_*` card is the OSSE per-direction law from `ATH_CORE_TWINRAY_MORPH_2026-10-25.md` §5b:

```text
a(p) = a_deg + az_a_sf_amp*SF(p) + az_a_cos_amp*|cos p|^az_a_cos_pow
SF(p) = (|cos(m p/4)/a|^n2 + |sin(m p/4)/b|^n3)^(-1/n1)
```

The screenshot’s visible values are not the CORE preset:

| Knob | Screenshot | ATH CORE | Effect |
|---|---:|---:|---|
| `az_a_sf_amp` | 11.5 | 35 | Diagonal feature is much weaker |
| `az_sf_b` | 1.2 | 0.618 | **b > 1 widens the vertical; CORE uses b < 1 to narrow it** |
| `az_sf_n1` | 12 | 12 | Same overall sharpness |
| `az_sf_n2` | 27.1 | 15 | Flatter superformula |
| `az_sf_n3` | 26.4 | 16 | Flatter superformula |
| `az_a_cos_amp` | -15 | -15 | Trims the horizontal |

With the screenshot’s numbers, `SF(90) ≈ 1.2^(26.4/12) ≈ 1.49`, so the vertical gets a large SF term. A rough evaluation gives `a(0) ≈ a_deg - 3.5`, `a(90) ≈ a_deg + 17`, and `a(45) ≈ a_deg + 18–25` depending on `az_a_cos_pow`. The vertical and diagonal are about 20 degrees above the horizontal. That is a vertically over-flared horn: the vertical faces bow out, and the diagonal is only slightly above the vertical, so it does not read as a separate ATH ridge.

The 80 × 50 brief needs roughly `a(0) ≈ 40`, `a(90) ≈ 26`, and, if the ATH ridge is wanted, `a(45) ≈ 44`. The CORE preset is for a round, roughly 90-degree two-inch horn (25.0 / 33.8 / 23.4 degrees). The landscape petal cell is an 80 × 50 compromise (H ≈ 41, V ≈ 26, diagonal ≈ 35); it gives the landscape balance but gives up the diagonal ridge. The screenshot’s mix is the opposite H/V balance from the brief.

**Fixes, in order:**

1. Set `az_sf_b` below 1 (0.62 for CORE, 0.86 for the landscape petal).
2. Raise `az_a_sf_amp` toward 30–35 if the CORE ridge is wanted.
3. Keep `az_a_cos_amp` negative but not enough to starve the horizontal; set `a_deg` so `a(0)` reaches the 80-degree half-angle.
4. Bring `az_sf_n2` / `az_sf_n3` back toward 15 / 16.
5. Turn on the rectangle Morph if the mouth should be square. Without it, the mouth follows the wall angles and a V-dominant law looks tall/oval.
6. If both 80 × 50 coverage and a distinct diagonal ridge are required, add an explicit diagonal term such as `az_a_diag_amp * |sin(2p)|^pow` so H, V, and the 45-degree ridge are independent. The current SF + cos terms are entangled.

## Finding 3 — why ATH’s ridges exist

Published ATH constructions:

- **Tritonia:** `alpha(theta) = 48.5 - 7*cos(2*theta)^5 - 16*sin(theta)^12`. At H/45/V = **41.5 / 48.25 / 39.5 degrees**.
- **CORE:** `a(p) = 5 + 35*sf(4,12,15,16,1,0.618,p) - 15*cos(p)^10`. At H/45/V = **25.0 / 33.8 / 23.4 degrees**.

The diagonal opens about 7–10 degrees wider than the axes. The physical reason is the longer diagonal path of a rectangular mouth: if the diagonal flares at the same angle as H/V, the corner wavefront lags and the diagonal polar narrows or lobes. Opening the diagonal flare advances that part of the wavefront. The four triangular panels are the integrated shape of that law, with the diagonal as the ridge. ATH then morphs the mouth to a rounded rectangle, which pushes the corners out and adds the shifted diagonal.

This must stay smooth. Geddes’ rule is that diffraction scales with the second derivative of the surface; sharp X creases are a real HOM/diffraction risk. ATH’s corner radius and morph rate control how sharp the ridge looks.

Do not conflate the families:

- **JBL/Keele biradial:** two-plane power-series contours plus a narrow throat slot. The JBL 2380A holds horizontal pattern from about 500 Hz but vertical constant-directivity only above about 2 kHz. Its “X” is a throat/diffraction feature, not a per-azimuth mouth law.
- **Crowe ES:** a log-spiral flare with a claimed 270-degree wrap. No per-direction law is published; his own polars narrow with frequency. The X/bow-tie is a visual consequence of the wrap and rectangular mouth.
- **ATH OS-SE / R-OSSE:** the only one of the three with a published per-direction `a(phi)` law. It is the right reference for the ridge mechanism.

## Finding 4 — the correct alternate: radial relief

`hornlab_search/design/generators/rolled_family.py` already implements the radial version:

```text
rho_new = rho - (inward_h*cos^2(psi) + inward_v*sin^2(psi)) * cos^2(2*psi) * window
```

At `psi = 0` / `90` the axes move inward by H / V; at 45 degrees the diagonal is unchanged. Positive H/V therefore make the diagonal a ridge and the four panels concave. The window is explicit `start / peak / end`, and `end <= 0.96` keeps the returned lip untouched. The generator checks source tangency, no constriction before the roll, self-approach, envelope, and finite normals; `tests/test_rolled_family_geometry.py` asserts the radial displacement and the source/return invariants.

Existing cells:

- `rf__rect_radial_v7`: same spiral base, inward 3 / 4 mm (subtle).
- `rf__rect_radial_strong_v7`: inward 6 / 8 mm.
- `rf__section_radial_v7`: section-based Crowe panel.

New wide-range cell (uncommitted):

`examples/typologies/rolled_family_2026-11-15/rf__rect_radial_wide_v7.yaml`

- Same 542 × 299 × 238 mm spiral base as `hl__rolled_es_spiral_v7`.
- Inward H / V seed **12 / 16 mm**; bounds **0–30 / 0–40 mm** (the generator caps at 15% of height, 44.85 mm).
- Window fixed at 0.50 / 0.80 / 0.96.
- Five search keys: `g_decay`, `g_depth_mm`, `g_rect_exponent`, `g_inward_h_mm`, `g_inward_v_mm`.
- Shape check: **541 × 299 × 241 mm, 5,096 DOF**, envelope fits, round throat matches the driver.
- `DesignSpace.from_config` validates; `tests/test_rolled_family_geometry.py` **32 passed**.
- GUI: `examples/catalog.gui.yaml` lists it as `rf__rect_radial_wide_v7` (group `home`, `hv`, enabled). The parameter catalog was regenerated (`tools/gen_param_catalog.py --write`) so the sandbox shows the inward H/V, axial H/V and relief-window knobs with documented ranges. Suggested starts are in the typology description: **6/8 subtle, 12/16 clear, 16/22 dramatic**; bounds **0–30 H / 0–40 V mm**; window **0.50 / 0.80 / 0.96**.
- GUI preview verified: `preview_shape(root, "rf__rect_radial_wide_v7", {"detail": ["3d"]})` returns `available: true`, `shape3d.available: true`, measured dims **535.7 × 294.7 × 235.1 mm**. The preview branch now resolves `rolled_family` through its canonical `resolve_grid` instead of the generic rows march, which rejected the `mode` key.

**Inward vs outward:** positive is the ATH-like ridge. Negative is the outward/diagonal-valley experiment (the current bow-out look, but in-plane). The v1 generator rejects negative `inward_*`. The clean way to expose both in search is a recipe-level `radial_direction: inward | outward` (or a `radial_outward` mode), not a signed numeric knob: the master research treats categorical base/mode choices as recipe identity, not an optimizer dimension. A scratch render of the outward 16/22 mm case is in `scratch/render_signed/views/outward_c.png`.

**Honest limit:** this is a local radial approximation of ATH’s `a(phi)` law, not a reproduction. It gives the ridge look and a clean lip, but at high amplitudes it introduces a slight waist at the relief peak. It does not change the spiral’s narrowing flare. For the true ATH mechanism, use the OSSE/R-OSSE per-direction body.

## Correction — `sp__strong_v7` is not a separate typology

The owner’s read was right. The legacy section-pucker cell `sp__strong_v7`
(`examples/typologies/section_pucker_2026-11-15/sp__strong_v7.yaml`) is the canonical
section family with the **axial pucker strength set to 7/9 mm**. Verification on the same
grid:

- `sp__strong_v7` inner points vs `rf__section_axial_v7` with `g_axial_h_mm=7`,
  `g_axial_v_mm=9`, window `0.30/0.80/0.96`: **max absolute point difference 9.6e-7 mm**.
- Canonical `rf__section_axial_strong_v7` mesh: **417 × 203 × 210 mm, 3,142 DOF**, envelope
  fits, round throat matches the driver.
- GUI preview of the canonical cell: `available: true`, `shape3d.available: true`,
  measured **385.9 × 197.0 × 162.2 mm**.

The pucker is a parameter of the section family (`g_axial_h_mm`, `g_axial_v_mm`, and the
`g_relief_start_s` / `peak_s` / `end_s` window), not its own typology. The canonical
`rf__section_axial_strong_v7` is now the GUI cell; the three `sp__*` entries were removed
from `examples/catalog.gui.yaml`. The legacy config and its validation record stay on disk
as historical evidence, but they are no longer presented as separate typologies.

The canonical versus legacy comparison is in
`docs/renders/2026-11-15-pucker/strong_a_vs_canonical.png`; the canonical three-view card is
`rf__section_axial_strong_card.png`. They are the same shape.

The square X remains a genuinely separate family: `hl__crowe_x_square_v7` is a near-square
OSSE body with a strong superformula X and a smooth rolled rim, not the section pucker.

## Parameter alignment — the axial-strong box was a visual study, not an optimization cell

Owner correction, 2026-11-15: the first `rf__section_axial_strong_v7` inherited the
visual-study box. It fixed width/height at the ES-600 drawing (417 × 203), searched depth
only 194–202 mm, `h_depth_scale` 0.99–1.01, crown 18–22 mm, fixed the junction at 32, and
spent five active dimensions on that plus the pucker. Those are not the acoustic levers the
home/Crowe cells need:

| Parameter | Acoustic role | Old axial-strong box | Home/optimization box |
|---|---|---|---|
| `g_width_mm` | Mouth width → horizontal pattern control and coverage at the crossover | fixed 417 | **480–600** |
| `g_height_mm` | Mouth height → vertical pattern control; 50° at 700 Hz needs ~794 mm, impossible in 480 mm | fixed 203 | **220–420** |
| `g_depth_mm` | Axial length → flare rate and low-frequency loading | **194–202** (±2%) | **170–300** |
| `g_h_depth_scale` | H/V depth split → top/bottom vs side termination (the Crowe forward-lip look) | **0.99–1.01** (negligible) | **0.9–1.1** (kernel cap) |
| `g_crown_mm` | Transverse crown → section curvature and diffraction/second-derivative behaviour | **18–22** | **10–40** |
| `g_junction_power` | Section joint/corner curvature → local diffraction and HOM risk | fixed 32 | **16–48** |
| `g_axial_h_mm`, `g_axial_v_mm` | Mouth-rim/diagonal phase; a **secondary** local lever, not coverage or loading | 4–10 / 6–12 | **0–12 / 0–14** |
| `g_throat_blend_mm` | Source matching/HF loading; the section throat is digitized | fixed 20 | fixed 20 |
| relief window | Pucker placement; position search is dormant when strength can be zero | fixed | fixed 0.30/0.80/0.96 |

The latest `hl__crowe_panel_home_v7` runs confirm the useful dimensions. Seed 1234 reached
J ≈ 16.92 at eval 30 with width **579.7**, height **292.9**, depth **262.1**,
`h_depth_scale` **1.098**, crown **39.7**, junction **24.4**, throat 20 — i.e. the search
wanted a larger mouth, more H/V depth split and more crown, while the old axial-strong cell
had all three frozen or nearly frozen. That is why the old box could not optimize the sound.

The corrected optimization cell is **`rf__section_axial_home_v7`**:

- width 480–600, height 220–420, depth 170–300, `h_depth_scale` 0.9–1.1, crown 10–40,
  junction 16–48, axial pucker 0–12 / 0–14; throat and window fixed.
- Seed = the best home-panel design above + 7 / 9 pucker.
- Mesh: **580 × 290 × 274 mm, 3,988 DOF**; preview **536.5 × 284.0 × 199.4 mm**.
- Eight active dimensions. **25 evaluations is a coarse pilot, not a converged search**
  (the home-panel cell uses 96). Use 60–96 for a real optimization.

The fixed 417 × 203 `rf__section_axial_strong_v7` is retained as the exact `strong_a.png`
visual reference. It is not the optimization cell. GUI descriptions now say so.

## Optimization evidence and recommendation

Stored v7 rescore under the same brief (not a cross-version ranking):

| Family | Base J | Smooth J | Dominant residual |
|---|---:|---:|---|
| Rolled ES spiral | 27.4–29.4 | 14.3–15.9 | `diag` 7.0–7.7, `dislope` 2.7–3.1 |
| Crowe ES sections | 22.54 | 10.53 | `diag` 4.5 |
| ATH petal | 5.32 | 3.14 | balanced |
| R-OSSE rect CD | 3.99 | 2.32 | balanced |

The pucker is a weak lever: the spiral capability run with maximum pucker (18 / 24 mm) scored **28.84** vs the seed **29.91**, about a 1% change. The base flare law, not the pucker, decides the result.

Other limits:

- The 50-degree vertical target at 700 Hz needs roughly **794 mm** of mouth height; the 299 mm seed cannot hold it. The brief already half-weights vertical. Do not expect a 299 mm-tall horn to hold 50 degrees at 700 Hz.
- `diag` uses a fixed round 65-degree reference. A rectangular or creased mouth is penalized for being rectangular. Report it separately until real diagonal polars exist; do not let it pick the winner alone.

**Recommended next steps:**

1. **Look-first, spiral base:** use `rf__rect_radial_wide_v7`. Start at 6 / 8 mm for a subtle ridge, 12 / 16 for a clear one, 16 / 22 for a dramatic one. This is a separate experiment; it does **not** produce the `strong_a.png` mouth-rim fold.
1b. **Mouth-rim pucker (`strong_a`):** use `rf__section_axial_strong_v7` (canonical section family, axial 7 / 9 mm, window 0.30/0.80/0.96). This is the same geometry as legacy `sp__strong_v7` (max point difference 9.6e-7); the pucker is a parameter (`g_axial_h_mm`, `g_axial_v_mm`, relief window), not a separate typology. The legacy `sp__*` GUI entries are removed.
2. **Exact screenshot look:** stay on the OSSE per-direction body. Fix `az_sf_b`, `az_a_sf_amp`, `az_sf_n2/n3`, set `a_deg` for the 80-degree horizontal, and turn on the rectangle Morph. Add the explicit diagonal term if H, V, and the ridge must be independent.
3. **Sound-first:** optimize the CD ATH/R-OSSE family (`hl__ath_core_petal_hvlaw_v7`, `hl__rosse_rect_cd_v7`), not the spiral. The spiral is a look-first family with a narrowing flare.
4. **GUI:** add a relief card for the rolled family (mode, inward H/V, axial H/V, window start/peak/end). Fix the `pucker_*` docs to say “axial”. Keep the ATH per-direction card OSSE-only; it does not drive the spiral.

## Sources

Repo:

- `docs/research/typologies/BIRADIAL_CROWE_STUDY_2026-11-15.md` (spiral limits, fair rescore, cell checks).
- `docs/research/typologies/ROLLED_FAMILY_MASTER_RESEARCH_2026-11-15.md` (radial hybrid law and the explicit correction that z-only relief is not ATH radial).
- `docs/research/typologies/ROLLED_FAMILY_EVIDENCE_HANDOFF_2026-11-15.md` (readiness warning, don’t call z-only relief ATH-like).
- `docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md` §5b (published CORE expressions and measured angles).
- `docs/research/typologies/STARTING_SEEDS_PLAIN_2026-11-15.md` (X/waist/crease evidence status, 496/794 mm mouth rule, JBL vs ATH).
- `docs/research/typologies/SECTION_PUCKER_RESEARCH_2026-11-15.md` (section H/V pucker construction).
- `docs/research/typologies/HORN_WHITEPAPERS_2026-11-15.md` (annotated primary-source bibliography).

External (fetched 2026-11-15):

- ATH Tritonia: <https://at-horns.eu/tritonia.html> (published alpha/s formula).
- ATH CORE: <https://at-horns.eu/core.html> (published OSSE script, Morph and roundover).
- Joseph Crowe ES-600: <https://josephcrowe.com/blogs/news/es-600-biradial-horn> (270-degree wrap, golden-ratio claim; no formula).

Code:

- `tools/geometry/rolled_rect.py::surface_at` and `hornlab_search/design/generators/_rolled_rect_v1.py::surface_at` (axial pucker).
- `hornlab_search/design/generators/rolled_family.py::resolve_grid` (radial relief, windows, guards).
- `hornlab_search/design/generators/grid.py::_rows_osse_rollback_marches` (superformula X + rolled lip).
- `hornlab_search/design/params/knobs_rows.py` (`pucker_*` doc mismatch).
- `examples/typologies/rolled_family_2026-11-15/rf__rect_radial_wide_v7.yaml` (new cell).

## Evidence status

- Shape-only. No GPU solve for the new cell; no acoustic claim is made.
- The 12 / 16 mm render and the outward 16 / 22 mm render are scratch artifacts, regenerable from the config and the scratch script. Durable copies: `docs/renders/2026-11-15-pucker/pucker_compare.png` (six shapes), `relief_versions.png` (control, 3/4, 6/8, 12/16, 16/22 inward, 16/22 outward), `rf__rect_radial_wide_v7_card.png` (3/4, front, side).
- GUI preview is verified for this cell (`available: true`, `shape3d.available: true`, 535.7 x 294.7 x 235.1 mm). The typology is listed under group `home`; suggested starts are 6/8, 12/16, 16/22 mm.
- The X/crease acoustics remain unproven. The next real evidence is a diagonal polar (45/135 degrees) for the inward-radial and per-direction candidates.
