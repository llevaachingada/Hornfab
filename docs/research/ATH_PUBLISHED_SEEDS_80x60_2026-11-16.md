# ATH Published Seeds for 80 × 60 / 80 × 50 Home Hi-Fi Brief

2026-11-16 · Research pass by agent (read-only). Goal: map published ATH waveguide designs
to our OSSE knob set as seeds for the 80H × 60V (room_80x60_700_hf1440_v7) and
80H × 50V (room_landscape_80x50_700_hf1440_v7) home hi-fi briefs.

---

## 0. Existing state (what we already have — not re-researched)

| File | Status |
|---|---|
| `examples/typologies/ath_core.yaml` | ATH CORE 2-inch OSSE, brief ath_core_2in (~50°×47°, narrow) |
| `examples/typologies/ath_twinray_380.yaml` | TwinRay 36-10-380 FREEFORM reconstruction (dimension-based, 90°×60° target) |
| `examples/typologies/print_80x60_2026-11-13/p80x60__ath_core_14in_700_v7.yaml` | CORE adapted to 1.4-inch, 80H×60V portrait brief — the STARTING POINT for this research |
| `docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md` | CORE and TwinRay reconstruction; morph law; az_* knobs |
| `docs/research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md` | Superformula guiding-curve research; CORE 2026 script quoted |

The existing `p80x60__ath_core_14in_700_v7.yaml` seed (a_deg=45, L=350, morph portrait 500×660) is
the baseline; these seeds are ALTERNATIVES from published designs with different parameter spaces.

---

## 1. Source table

| ID | Design | URL | License | Throat (mm) | Mouth (W × H mm) | Depth (mm) | LF point | Coverage |
|---|---|---|---|---|---|---|---|---|
| A | ATH CORE (2-inch) | https://at-horns.eu/core.html | CC-BY-4.0 | r0=25 (radius), 50mm dia | ~400×400 (est. from roundover 42mm) | ~260 | not stated | ~50°×47° |
| B | Tritonia original (1.4-inch) | https://at-horns.eu/ext/Tritonia.txt | CC BY-NC-SA 4.0 | r0=36 (diameter), 18mm radius | ~422×364 (Tritonia-F full scale) | ~135 | ~400 Hz (sim floor) | **~83°×79°** |
| C | Tritonia-S (1-inch, 100°×90°) | https://at-horns.eu/ext/Tritonia-S.txt | CC BY-NC-SA 4.0 | 25.4mm dia | 206×178 | ~65 (scaled) | ~1500 Hz | 100°×90° |
| D | Tritonia-M (1-inch, same shape) | https://at-horns.eu/ext/Tritonia-M.txt | CC BY-NC-SA 4.0 | 25.4mm dia | 294×254 | ~95 (scaled) | ~1000 Hz | ~100°×90° |
| E | TwinRay 36-04-266 (1.4-inch) | https://at-horns.eu/twinray.html | commercial STL | 36mm dia | 266×212 | 130 | 680 Hz | image only; H constant CD |
| F | TwinRay 36-10-380 (1.4-inch) | https://at-horns.eu/twinray.html | commercial STL | 36mm dia | 380×303 | 192 | 580 Hz | image only; H constant CD |
| G | R-OSSE example "ST260" | R-OSSE paper Fig 4 (https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf) | CC BY-NC-SA 4.0 | 25.4mm dia (1-inch) | ~260mm dia (round) | ~80 | n/a (round) | ~78° (round, axi) |

Sources E and F have no published ATH config scripts; all parameter data is from dimension tables only.
Source G is axisymmetric; included for the R-OSSE parameter example only.

---

## 2. Per-design parameter table

### Design A — ATH CORE (2-inch, CC-BY-4.0)

Source: https://at-horns.eu/core.html (fetched 2026-11-16)

```
OSSE = {
  L = 260               ; [mm]
  r0 = 25.0             ; [mm] RADIUS (confirmed by label "throat radius"; 2" = 50mm dia)
  a0 = 1.2              ; [deg] half-angle
  a = 5 + 35*sf(4,12,15,16,1,0.618,p) - 15*cos(p)^10   ; [deg] half-angle
  n = 6.0 + 1.5*cos(p)^2
  q = 0.996
  s = 0.6 + 0.23*cos(p)^2
  s1 = 1.14
  s2 = 0.025
}
Morph.TargetShape = 1
Morph.FixedPart = 0.0
Morph.Rate = 3.0
Morph.CornerRadius = 16.5   ; [mm]
```

Coverage at principal azimuths (from BIRADIAL_CROWE_STUDY_2026-11-15, verified against formula):
- H (p=0): a = 5+35-0 = 25.0° half-angle → full H ≈ 50°
- Diagonal (p=π/4): a ≈ 5+35·sf(44°)-15·cos(45°)^10 ≈ 33.8°
- V (p=π/2): a = 5+0-0 = 5+0-0 = 5+35·sf(π/2)-15·0 ≈ 23.4° half-angle → full V ≈ 47°

**Verdict: too narrow for our brief. Useful only as a termination-quality reference (n, s, q, s1, s2 values).**

---

### Design B — Tritonia original (1.4-inch, CC BY-NC-SA 4.0)

Source: https://at-horns.eu/ext/Tritonia.txt (fetched 2026-11-16)

```
OSSE = {
  L = 135.0             ; [mm]
  r0 = 36.0             ; [mm] DIAMETER in this script (1.4" = 35.56mm ≈ 36mm)
  a0 = 4.2              ; [deg] half-angle
  a = 48.5 - 7.0*cos(2.0*p)^5.0 - 16.0*sin(p)^12.0  ; [deg] half-angle
  s = 0.7 + 0.2*cos(p)^2
  n = 3.7
  q = 0.995
  k = 1.0
}
Morph.TargetShape = 1
Morph.FixedPart = 0.0
Morph.Rate = 3.0
Morph.CornerRadius = 18   ; [mm]
```

**r0 convention note**: In this OSSE block script, r0=36 equals the throat DIAMETER (1.4" = 35.56mm).
The ATH CORE (Design A) uses r0 as RADIUS. This inconsistency appears to be an ATH version difference
(older OSSE block scripts used diameter; CORE 2026 uses radius with explicit label). Our knob r0_mm
is always a RADIUS, so: **r0_mm = ATH_r0 / 2 = 36 / 2 = 18.0 mm**.

Coverage evaluation (p is azimuth, 0=H, π/2=V):
- H (p=0): a = 48.5 - 7·cos(0)^5 - 16·sin(0)^12 = 48.5 - 7 - 0 = **41.5°** → full H ≈ 83°
- Diagonal (p=π/4): a = 48.5 - 7·cos(π/2)^5 - 16·sin(π/4)^12 ≈ 48.5 - 0 - 0.1 ≈ 48.4°
- V (p=π/2): a = 48.5 - 7·cos(π)^5 - 16·sin(π/2)^12 = 48.5 + 7 - 16 = **39.5°** → full V ≈ 79°

The design is nearly symmetric (H=83°, V=79°), not asymmetric. The stated "100°×90°" for the
Tritonia-S/M kits (1" throat) reflects that those designs are wider due to smaller physical throat
(the Tritonia-F full-scale equivalent is the 1.4"-throat original, which gives ~83°×79°).

**Verdict: good H (83° close to 80° target), V too wide (79° vs 60V target). Use as seed with
morph providing H>V asymmetry via landscape-oriented rectangular morph (wider W than H).**

---

### Design C — Tritonia-S (1-inch, CC BY-NC-SA 4.0)

Source: https://at-horns.eu/ext/Tritonia-S.txt (fetched 2026-11-16)

```
Scale = 0.48
Throat.Profile = 1              ; OS-SE
Throat.Diameter = 52.917        ; pre-scale; actual = 52.917×0.48 = 25.4mm (1-inch)
Throat.Angle = 10               ; [deg] TOTAL throat angle → half-angle = 5°
Length = 135                    ; [mm] pre-scale; actual = 64.8mm
Coverage.Angle = 48.5 - 7*cos(2*p)^5 - 16*sin(p)^12   ; [deg] half-angle (same formula)
Term.s = 0.7 + 0.2*cos(p)^2
Term.n = 3.7
Term.q = 0.992
Morph.TargetShape = 1
Morph.FixedPart = 0.0
Morph.Rate = 3
Morph.CornerRadius = 18         ; [mm]
```

Same shape formula as Design B; different scale and 1" throat. Nominal stated coverage: 100°×90°.
The larger nominal angle vs the 1.4" original reflects the 1" throat's lower area ratio.

**Verdict: not directly applicable (1-inch throat, too small mouth for 700 Hz). Useful as confirmation
that the Tritonia formula gives consistent performance; Scale=0.48 tells us the 1" version is 48% of
the 1.4" full-scale design.**

---

### Design D — Tritonia-M (1-inch, CC BY-NC-SA 4.0)

Source: https://at-horns.eu/ext/Tritonia-M.txt (fetched 2026-11-16)

Identical formula to Tritonia-S; Scale=0.702, Throat.Diameter=36.182. Front 294×254mm, ~1kHz use.
Nothing new for our 1.4-inch brief. See Design C notes.

---

### Design E — TwinRay 36-04-266 (1.4-inch, dimensions only)

Source: https://at-horns.eu/twinray.html (fetched 2026-11-16). No ATH config published.

| Dimension | Value |
|---|---|
| Throat diameter | 36 mm (1.4") |
| Throat angle (total) | 4° → half-angle a0 = 2° |
| Mouth (W × H) | 266 × 212 mm |
| Depth | 130 mm |
| LF point | 680 Hz |
| Mouth aspect ratio | 1.26:1 (wider than tall) |

Described as "constant directivity in the horizontal plane, gradually narrowing beamwidth in the vertical
plane." No ATH config script is public; the kit is sold on Cults3D. Coverage angles are only available
as polar map images; not stated as degrees in the text.

For the 700 Hz home brief: 266mm mouth width is below the K-law (~454mm for 80° at 700 Hz), so it
would not control fully at 700 Hz. Use as an upper-bound seed for a compact/aggressive cell.

---

### Design F — TwinRay 36-10-380 (1.4-inch, dimensions only)

Source: https://at-horns.eu/twinray.html (fetched 2026-11-16). No ATH config published. Already
reconstructed as `ath_twinray_380.yaml` in this repo (FREEFORM, 90°×60° target).

| Dimension | Value |
|---|---|
| Throat diameter | 36 mm (1.4") |
| Throat angle (total) | 10° → half-angle a0 = 5° |
| Mouth (W × H) | 380 × 303 mm |
| Depth | 192 mm |
| LF point | 580 Hz |
| Mouth aspect ratio | 1.25:1 |

This is what `ath_twinray_380.yaml` is based on. 580 Hz LF is well below the 700 Hz crossover.
Fits inside the landscape envelope (600W × 480H × 480D): 380mm W ✓, 303mm H ✓, 192mm D ✓.

---

### Design G — R-OSSE "ST260" example (1-inch, axisymmetric)

Source: R-OSSE Acoustic Waveguide paper §"Practical design example", Marcel Batik Dec 2022.

```
R = 130 mm      ; outer radius (mouth)
r0 = 12.7 mm    ; throat radius (1" = 25.4mm dia → radius = 12.7mm)
a0 = 7.5 deg    ; throat half-angle
a = 39 deg      ; nominal coverage half-angle → full coverage ~78°
k = 1.8         ; throat expansion factor
r = 0.3         ; apex radius factor
b = 0.3         ; bending factor
m = 0.8         ; apex shift factor
q = 3.7         ; throat shape factor (NOTE: R-OSSE q is a blend exponent, different from OSSE q)
```

Result: 260 mm wide, ~80 mm long. Axisymmetric only; not applicable to our rectangular OSSE family.
Included only to show R-OSSE parameter values in the mid-coverage range.

---

## 3. Mapping to our knob set

### 3.1 Conversion table

| ATH parameter | ATH context | Our knob | Conversion |
|---|---|---|---|
| `L` / `Length` | OSSE block / flat | `L_mm` | 1:1 (mm) |
| `r0` (OSSE block, old — Tritonia) | diameter | `r0_mm` | `r0_mm = ATH_r0 / 2` |
| `r0` (OSSE block, new — CORE 2026) | radius | `r0_mm` | 1:1 |
| `Throat.Diameter` (flat syntax) | diameter | `r0_mm` | `r0_mm = Throat.Diameter × Scale / 2` |
| `a0` / `Throat.Angle` (block half) | half-angle | `a0_deg` | 1:1 |
| `Throat.Angle` (flat syntax, TOTAL) | total → half | `a0_deg` | `a0_deg = Throat.Angle / 2` |
| `a` (constant scalar) | half-angle | `a_deg` | 1:1 |
| `a = expr(p)` (formula at p=0) | H half-angle | `a_deg` | use H value (p=0); V asymmetry via morph |
| `a = expr(p)` (formula mean) | H+V mean | `a_deg` | (H+V)/2 for a first seed; H seed preferred |
| `n` / `Term.n` | | `n` | 1:1 |
| `s` (scalar) / `Term.s` (scalar) | | `s` | 1:1 |
| `s = expr(p)` (formula mean) | | `s` | (H+V)/2 for constant-azimuth approx |
| `q` / `Term.q` (OSSE) | OSSE saturation | `q` | 1:1 |
| `q` (R-OSSE) | blend exponent | `q` (R-OSSE family) | 1:1; DO NOT confuse with OSSE q |
| `k` / `OS.k` | | `k` | 1:1 |
| `s1`, `s2` | | `s1`, `s2` | 1:1 (absent in Tritonia → use small/off-values) |
| `Morph.TargetShape` | 1=rect, 2=circle | `morph_target` | 1:1 |
| `Morph.FixedPart` | fraction | `morph_fixed` | 1:1 |
| `Morph.Rate` | exponent | `morph_rate` | 1:1 |
| `Morph.CornerRadius` | mm | `morph_corner_mm` | 1:1 |
| `Morph.TargetWidth` / mouth W | mm | `morph_width_mm` | 1:1 (or derived from dimension) |
| `Morph.TargetHeight` / mouth H | mm | `morph_height_mm` | 1:1 (or derived from dimension) |

**Morph.AllowShrinkage**: always set to 1 (the config already pins this); it allows the optimizer to explore
morph targets smaller than the raw mouth extent (required for landscape).

**s1/s2 when absent (Tritonia)**: The Tritonia does not use throat extension. In our config these are
searched in bounds [1.0, 1.3] × [0.015, 0.035]. Seed at s1=1.0, s2=0.015 (minimum stretch = smallest
extension, closest to no-extension). The optimizer can find the right level.

### 3.2 Seed parameter tables

Bounds references are from `p80x60__ath_core_14in_700_v7.yaml`. Where a seed value falls OUTSIDE the
bounds, the flag "⚠ OOB" is shown with the minimum needed bound.

#### Seed T1 — Tritonia-H80 (from Design B, scaled for 700 Hz, landscape-oriented)

Rationale: Tritonia formula gives H=83° which is on-target. Scale up from 135 mm to ~350 mm for 700 Hz
mouth size. Use landscape-oriented rectangular morph (wider than tall) to steer V below H.

| Knob | ATH source | Seed value | In bounds [lo, hi]? |
|---|---|---|---|
| `r0_mm` | Tritonia r0=36 (diameter) → radius=18 | 18.0 | Fixed [18,18] ✓ |
| `a0_deg` | Tritonia a0=4.2 (half-angle) | 2.0 | [1.0, 3.0] ✓ (brief matches 2°; 4.2 ⚠ OOB, needs hi=5) |
| `L_mm` | Scaled up from 135→350 for LF | 350.0 | [140, 650] ✓ |
| `a_deg` | Tritonia H half-angle 41.5° | 42.0 | [10, 80] ✓ |
| `n` | Tritonia Term.n=3.7 | 3.7 | [1.0, 10.0] ✓ |
| `s` | Tritonia s mean (0.9+0.7)/2=0.8 | 0.80 | [0.0, 1.5] ✓ |
| `q` | Tritonia Term.q=0.995 | 0.995 | [0.9, 1.0] ✓ |
| `k` | Tritonia k=1.0 | 1.0 | [0.3, 5.0] ✓ |
| `s1` | Not in Tritonia → minimum stretch | 1.0 | [1.0, 1.3] ✓ (at lo) |
| `s2` | Not in Tritonia → minimum stretch | 0.015 | [0.015, 0.035] ✓ (at lo) |
| `morph_target` | Tritonia Morph.TargetShape=1 | 1 | [1, 1] fixed ✓ |
| `morph_width_mm` | Landscape: wider W, targeting ~480mm | 480.0 | [410, 590] ✓ |
| `morph_height_mm` | Landscape: shorter H, targeting ~380mm | 380.0 | ⚠ OOB — bounds [540,770] are portrait! Need hi→480 |
| `morph_corner_mm` | Tritonia Morph.CornerRadius=18 | 18.0 | [0.0, 80.0] ✓ |
| `morph_exponent` | n/a (morph_target=1) | 4.0 | [2.0, 10.0] ✓ |
| `morph_rate` | Tritonia Morph.Rate=3.0 | 3.0 | [0.5, 8.0] ✓ |
| `morph_fixed` | Tritonia Morph.FixedPart=0.0 | 0.0 | [0.0, 0.6] ✓ |

**Bounds to widen for a landscape cell:**
- `a0_deg` hi: 1→3 is fine for the brief's exit_angle=2.0, but Tritonia's native 4.2° is OOB; a hi=5 would accommodate it
- `morph_height_mm` lo/hi: current [540, 770] is portrait-biased; for landscape brief needs lo=200, hi=480
- `morph_width_mm` lo/hi: current [410, 590] is acceptable for landscape

**NOT representable in our constant-azimuth OSSE knob set**: The Tritonia formula's azimuthal variation
(a varies with p from 41.5° at H to 39.5° at V) is not captured by a single `a_deg`. The H/V asymmetry
must come from the rectangular morph (wider W than H) rather than from the per-azimuth wall law. If the
per-azimuth law is desired, the `az_*` knob family (az_a_sf_amp, az_sf_m, etc.) can represent it. Seed T1
approximates it with constant a_deg = H value + morph asymmetry.

---

#### Seed T2 — TwinRay-266-landscape (from Design E, dimension reconstruction)

Rationale: TwinRay 36-04-266 is the smallest commercial ATH design that hits 680 Hz with a 1.4-inch
throat. Its 266×212 mouth and 130mm depth match a compact landscape cell. No config published; this is
a dimension-based reconstruction (similar to what `ath_twinray_380.yaml` does for Design F).

The TwinRay constant-H design is approximated by a constant-a_deg OSSE with wide a_deg + rectangular
morph providing H>V. The TwinRay description ("constant DI horizontal, narrowing vertical") suggests the
design behaves like our landscape morph approach.

| Knob | Source / derivation | Seed value | In bounds? |
|---|---|---|---|
| `r0_mm` | 36mm dia → radius=18mm | 18.0 | Fixed ✓ |
| `a0_deg` | TwinRay 36-04-266 total angle=4°, half=2° | 2.0 | [1,3] ✓ |
| `L_mm` | Depth 130mm + ~20mm extension headroom = 150mm | 170.0 | [140, 650] ✓ |
| `a_deg` | Targeting 80H: 40° half-angle | 42.0 | [10, 80] ✓ |
| `n` | CORE-class termination (from ath_core_14in) | 6.75 | [1, 10] ✓ |
| `s` | CORE-class termination | 0.715 | [0, 1.5] ✓ |
| `q` | CORE-class | 0.996 | [0.9, 1.0] ✓ |
| `k` | CORE-class | 1.0 | [0.3, 5] ✓ |
| `s1` | CORE-class throat stretch | 1.14 | [1.0, 1.3] ✓ |
| `s2` | CORE-class | 0.025 | [0.015, 0.035] ✓ |
| `morph_target` | 1 (rounded rectangle like TwinRay) | 1 | fixed ✓ |
| `morph_width_mm` | TwinRay 266mm × (350/130 scale) ≈ 450mm; keep at 420 (conservative) | 420.0 | [410, 590] ✓ (at lo) |
| `morph_height_mm` | TwinRay 212mm × scale ≈ 340mm landscape | 340.0 | ⚠ OOB [540,770]; needs lo=200 |
| `morph_corner_mm` | CORE value 16.5mm | 16.5 | [0, 80] ✓ |
| `morph_rate` | CORE/Tritonia 3.0 | 3.0 | [0.5, 8] ✓ |
| `morph_fixed` | CORE/Tritonia 0.0 | 0.0 | [0, 0.6] ✓ |

**Limitation**: TwinRay's actual profile formula is proprietary; this seed uses our OSSE family
as an approximation of TwinRay's geometry. The TwinRay might actually use R-OSSE; `ath_twinray_380.yaml`
uses FREEFORM but notes this route. This OSSE version is a fresh approximation, not a reconstruction.

---

#### Seed T3 — TwinRay-380-landscape (from Design F / ath_twinray_380 dimensions, OSSE route)

Rationale: TwinRay 36-10-380 is already the basis for `ath_twinray_380.yaml` (FREEFORM route). This seed
takes the same dimensions but via the OSSE family, giving the optimizer a different profile basis.
The 380×303mm mouth at 192mm depth is well-sized for 700 Hz control. 580 Hz LF point is below target.

| Knob | Source | Seed value | In bounds? |
|---|---|---|---|
| `r0_mm` | 36mm dia → radius=18mm | 18.0 | Fixed ✓ |
| `a0_deg` | TwinRay 36-10-380 total 10°, half=5° | 2.0 | [1,3] ✓ (5° is OOB; seed at brief value 2°) |
| `L_mm` | TwinRay depth 192mm | 200.0 | [140, 650] ✓ |
| `a_deg` | 80H target: 40-45° | 45.0 | [10, 80] ✓ |
| `n` | CORE-class | 6.75 | [1, 10] ✓ |
| `s` | CORE-class | 0.715 | [0, 1.5] ✓ |
| `q` | CORE-class | 0.996 | [0.9, 1.0] ✓ |
| `k` | CORE-class | 1.0 | [0.3, 5] ✓ |
| `s1` | CORE | 1.14 | [1.0, 1.3] ✓ |
| `s2` | CORE | 0.025 | [0.015, 0.035] ✓ |
| `morph_target` | 1 | 1 | fixed ✓ |
| `morph_width_mm` | TwinRay W=380mm; targeting ~460mm for landscape | 460.0 | [410, 590] ✓ |
| `morph_height_mm` | TwinRay H=303mm for landscape | 320.0 | ⚠ OOB [540,770]; needs lo=200 |
| `morph_corner_mm` | CORE 16.5 | 16.5 | [0, 80] ✓ |
| `morph_rate` | CORE 3.0 | 3.0 | [0.5, 8] ✓ |
| `morph_fixed` | 0.0 | 0.0 | [0, 0.6] ✓ |

Note: `a0_deg = 5°` (TwinRay's native half-angle) is outside the current bounds [1, 3]. Seeding at 2.0
(brief exit angle). If a0_deg bounds were widened to [1, 6], the optimizer could explore TwinRay's
steeper throat geometry.

---

#### Seed T4 — Tritonia-softer-80H (Tritonia formula with OSSE termination softened for V reduction)

Rationale: The Tritonia formula gives 83°×79° (nearly symmetric). To target 80H×60V, reduce n to soften
termination and reduce the morph height to steer V narrower than H. This seed pairs the Tritonia wall
angle with our existing morph-driven H/V asymmetry approach.

| Knob | Value | Note |
|---|---|---|
| `r0_mm` | 18.0 | 1.4" throat |
| `a0_deg` | 2.0 | Brief exit angle |
| `L_mm` | 300.0 | Between 266-depth and 380-depth, targeting ~700 Hz |
| `a_deg` | 41.0 | Tritonia H half-angle (41.5°), rounded |
| `n` | 3.7 | Tritonia value (softer than CORE 6.75) |
| `s` | 0.70 | Tritonia V value (lower = more asymmetric termination) |
| `q` | 0.995 | Tritonia value |
| `k` | 1.0 | Tritonia value |
| `s1` | 1.0 | Minimum stretch (not in Tritonia) |
| `s2` | 0.015 | Minimum stretch |
| `morph_target` | 1 | Rounded rectangle |
| `morph_width_mm` | 500.0 | Wider for H control |
| `morph_height_mm` | 360.0 | Shorter for V reduction; ⚠ OOB, needs lo=200 |
| `morph_corner_mm` | 18.0 | Tritonia value |
| `morph_rate` | 3.0 | Tritonia value |
| `morph_fixed` | 0.0 | Tritonia value |

---

## 4. Bounds requiring widening for landscape brief cells

The existing config `p80x60__ath_core_14in_700_v7.yaml` was designed for the portrait brief
(600W × 780H × 480D envelope). The landscape brief (600W × 480H × 480D) requires different morph bounds.
A new landscape config template should update:

| Knob | Current portrait bounds | Needed landscape bounds | Reason |
|---|---|---|---|
| `morph_height_mm` | lo=540, hi=770 | lo=200, hi=480 | Envelope height is 480mm; portrait bounds exceed it |
| `morph_width_mm` | lo=410, hi=590 | lo=300, hi=590 | Allow compact TwinRay-style mouths |
| `a0_deg` | lo=1.0, hi=3.0 | lo=1.0, hi=5.0 | Tritonia 4.2° and TwinRay-380 5° throat angles are useful |
| `L_mm` | lo=140, hi=650 | lo=120, hi=400 | TwinRay depths are 130-192mm; shorter L appropriate for landscape |
| `morph_fixed` | lo=0.0, hi=0.6 | lo=0.0, hi=0.4 | Same or slightly narrower |

All other bounds (a_deg, n, s, q, k, s1, s2, morph_rate, morph_corner_mm) are compatible.

---

## 5. Ranked seeds

### 5a. For 80H × 60V (room_80x60_700_hf1440_v7)

| Rank | Seed | Reason |
|---|---|---|
| 1 | **T1 (Tritonia-H80)** | Only published ATH 1.4" script; H coverage nearly on-target (83°); proven OSSE formula from Batik; distinctive soft termination (n=3.7) gives a genuinely different parameter space from existing CORE seed |
| 2 | **T4 (Tritonia-softer)** | Same proven formula with morph biased harder to H>V asymmetry; L=300 explores shallower but wider-mouth region |
| 3 | **T3 (TwinRay-380)** | Dimensions are well-validated (580 Hz LF on a 380mm mouth fits 700 Hz xo with margin); CORE-class termination; different depth regime from T1 |
| 4 | **T2 (TwinRay-266)** | Compact depth (170mm), different from other seeds; risk is mouth too small for 700 Hz control |

### 5b. For 80H × 50V (room_landscape_80x50_700_hf1440_v7)

| Rank | Seed | Reason |
|---|---|---|
| 1 | **T3 (TwinRay-380 landscape)** | 380×303mm mouth well-sized for 700 Hz; morph_height=320 naturally forces V narrower than H; 192mm depth matches envelope |
| 2 | **T1 (Tritonia-H80 landscape)** | Broad OSSE H combined with morph asymmetry; L=350 gives larger mouth than TwinRay-266 |
| 3 | **T2 (TwinRay-266 landscape)** | Compact; morph_height=340 provides moderate H>V asymmetry; risk remains mouth size |

---

## 6. What ATH's home designs tend to target

Based on published data:
- **Tritonia family** (Batik's main home hi-fi design): 100° × 90° for the 1" kits; ~83° × 79° at
  1.4" (nearly constant-directivity, symmetric). The natural published ATH home target is **90–100° symmetric**.
- **TwinRay family**: constant H, narrowing V; no explicit angles published but the description and mouth
  aspect (266:212 ≈ 1.26:1, 380:303 ≈ 1.25:1) suggests perhaps 90–100° H constant with 70–80° V at
  midrange narrowing to 50–60° V at HF.
- **CORE (Batik's professional reference)**: ~50° × 47° (narrow CD horn, more typical of studio monitors
  or PA-nearfield than home hi-fi).

**Is 80° × 60° or 90° × 60° a more natural published target?**
- 90° symmetric (Tritonia-class) is the most natural published ATH home target.
- 80° × 60° is a valid but *non-native* choice — no published ATH design targets exactly 80H × 60V.
- 90° × 60° is closer to the TwinRay published character (wider H, constant; narrower V). It is also
  more natural for a living-room horn (wider H coverage helps fill a wide room, narrower V reduces ceiling
  and floor reflections).
- **Recommendation**: use 80° × 60° as the brief but accept 85–90° H in practice; the landscape brief
  (80H × 50V) has a tighter V requirement that is more distinctive and aligns with TwinRay's character.

---

## 7. Open questions

1. **TwinRay config scripts**: Not public. If Batik ever releases them (the diyAudio thread at
   https://www.diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/ was
   inaccessible, HTTP 403), direct parameter seeds would be available. The dimension-based reconstructions
   (Seeds T2/T3) are the best available without those scripts.
2. **Tritonia's native throat geometry**: a0=4.2° (Tritonia) and a0=5° (TwinRay-380) are both outside
   our current bounds hi=3°. Whether these larger throat angles improve 700 Hz loading is worth testing;
   widening a0_deg bounds to [1, 6] would allow it.
3. **ATH's undocumented features**: The at-horns.eu site explicitly states that many features are only
   documented in the diyAudio thread. This thread is inaccessible without authentication. Any extended-throat
   (`s1`, `s2`) interaction with wide-coverage profiles is not documented in public HTML.
4. **TwinRay LF control mechanism**: Whether TwinRay achieves its 680 Hz / 580 Hz LF point through the
   OSSE profile alone or through enclosure integration (the design is explicitly "designed with enclosure
   BEM from the start") is unclear. Our freestanding model may differ.
5. **Throat r0 convention across ATH versions**: The inconsistency between Tritonia (r0=diameter) and CORE
   (r0=radius) means any user-shared ATH config must be checked against the actual throat size before seeding.

---

## Appendix: ATH ↔ our config parameter glossary

| ATH name | Our knob name | Notes |
|---|---|---|
| `Coverage.Angle` / `a` | `a_deg` | Both are half-angles in degrees |
| `Throat.Angle` (flat, total) | `a0_deg` | Divide by 2 for half-angle |
| `a0` (OSSE block, half) | `a0_deg` | 1:1 |
| `Length` / `L` | `L_mm` | 1:1 (mm) |
| `r0` (Tritonia-era OSSE block) | `r0_mm` | Divide by 2 (diameter→radius) |
| `r0` (CORE 2026 OSSE block) | `r0_mm` | 1:1 (already radius) |
| `Throat.Diameter` × Scale | `r0_mm` | Divide by 2 (diameter→radius) |
| `Term.n` / `n` | `n` | 1:1 |
| `Term.s` / `s` (scalar or mean) | `s` | 1:1 |
| `Term.q` / `q` (OSSE) | `q` | 1:1 |
| `OS.k` / `k` | `k` | 1:1 |
| `s1`, `s2` | `s1`, `s2` | 1:1; absent in Tritonia → seed at minimum |
| `Morph.TargetShape` | `morph_target` | 1:1 (0=off, 1=rect, 2=circle, 3=supellipse) |
| `Morph.FixedPart` | `morph_fixed` | 1:1 (fraction) |
| `Morph.Rate` | `morph_rate` | 1:1 |
| `Morph.CornerRadius` | `morph_corner_mm` | 1:1 (mm) |
| `Morph.TargetWidth` | `morph_width_mm` | 1:1 (mm) |
| `Morph.TargetHeight` | `morph_height_mm` | 1:1 (mm) |
| `Morph.AllowShrinkage` | `morph_allow_shrinkage` | 1:1 (0/1 flag) |
