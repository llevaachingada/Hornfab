# MESHER_TYPOLOGIES.md
# Exhaustive reference for hornlab_mesher (dist hornlab_waveguide_mesher-0.2.4)
# Generated 2026-10-22 from source inspection. All file paths are under
# .venv/Lib/site-packages/hornlab_mesher/ (abbreviated pkg/ below).

---

## 0. Formula registry

The canonical formula names and the normalisation function:

```python
# pkg/profile_common.py:463-472
def _normalise_formula(value):
    raw = str(value or "OSSE").strip().upper().replace("_", "-")
    if raw == "ROSSE":
        raw = "R-OSSE"
    if raw not in {"OSSE", "R-OSSE", "LOOKUP", "ICW", "FREEFORM"}:
        raise ValueError(...)
    return raw
```

**Valid formula strings (config key `type`):** `OSSE`, `R-OSSE` (alias `ROSSE`), `ICW`, `FREEFORM`, `LOOKUP`.
No conical, exponential, tractrix, Le Cléac'h, hyperbolic, spherical, or "axisymmetric" families exist.

---

## 1. OSSE (Oblique Spherical Surface Element + superellipse termination)

### 1a. Mathematical formula

Source: `pkg/profile_common.py:285-306` (`_osse_radius`) and `pkg/profile_formulas.py:359-428` (`calculate_osse`).

**Main OS-SE radius at axial station `z_main` and azimuth `p` (radians):**

```
base(z,p) = sqrt( (k*r0)^2 + 2*k*r0*z*tan(a0) + z^2 * tan(a)^2 ) + r0*(1-k)
```

where `a` is the coverage angle (deg, solved from guiding curve or taken from `a` param) and `a0` is the throat half-angle.

**Superellipse termination term (added to `base`):**

```
z_norm = q * z_main / L
if z_norm <= 1:
    term = (s*L/q) * (1 - (1 - z_norm^n)^(1/n))
else:
    term = s*L/q       # saturated
r(z_main) = base + term
```

This term is active only when `s != 0` and `n > 0` and `q > 0` and `L > 0`; otherwise `r = base`.

**Axial regions (composite meridian):**

```
z in [0, ext_len]:              r = r0_throat + z*tan(throatExtAngle)       (tapered extension)
z in [ext_len, ext_len+slot]:   r = r0_main                                 (cylindrical slot)
z in [ext_len+slot, total]:     r = base + term                              (OSSE main)
```

where `r0_throat = r0 - ext_len * tan(throatExtAngle)` (tapers back from main throat).

**Rotation (applies before throat stretch):**

```
rot_rad = radians(rot_deg)
x' = z*cos(rot) - (r-r0)*sin(rot)
r' = r0 + z*sin(rot) + (r-r0)*cos(rot)
```

**Throat stretch (applied to main section axial coordinate after Rot):**

```
x_stretched = x + s1 * degrees(atan(s2 * x))    # pkg/profile_formulas.py:283-288
```
Only active when `s1 != 0` and `s2 != 0`.

### 1b. OSSE parameters

| Config key | Aliases | Default | Units | Notes |
|---|---|---|---|---|
| `type` | | `OSSE` | str | formula selector |
| `r0` | `Throat.Diameter` | 12.7 | mm | main throat radius |
| `a` | `Coverage.Angle` | 60.0 | deg | coverage half-angle; overridden by guiding curve |
| `a0` | `Throat.Angle` | 15.5 | deg | throat half-angle |
| `L` | `Length` | 120.0 | mm | main horn length; > 0 required |
| `k` | | 1.0 | - | OS-SE shape factor (1=standard OS) |
| `n` | | 4.0 | - | superellipse exponent; > 0 required when s!=0 |
| `q` | | 0.995 | - | superellipse saturation; > 0 required when s!=0 |
| `s` | | 0.0 | - | superellipse amplitude; 0 = no termination |
| `rot` | `rot_deg` | 0.0 | deg | profile rotation |
| `s1` | | 0.0 | - | throat stretch coefficient 1; range [0, 10] |
| `s2` | | 0.0 | - | throat stretch coefficient 2; range [0, 10] |
| `throatExtLength` | | 0.0 | mm | throat extension length |
| `throatExtAngle` | | 0.0 | deg | throat extension taper angle |
| `slotLength` | | 0.0 | mm | cylindrical slot length |
| `throatProfile` | | 1 | int | 1=OSSE, 3=circular arc throat profile |
| `circArcRadius` | | inf | mm | circular arc radius (throatProfile=3) |
| `circArcTermAngle` | | 1.0 | deg | circular arc terminal angle (throatProfile=3) |
| `h` | | 0.0 | mm | h*sin(pi*t) bulge added to full composite profile |

**Length mode** (`_athLengthMode` / `lengthMode` / `athLengthMode`): default is that `L` is the main section length and total = L + ext + slot. With `mode="total"`: total=L+ext, slot carved out of L so main = L-slot.

**Guiding curve** (`gcurveType`, `gcurveWidth`, ...): when active, the coverage angle `a` is solved by bisection so the OSSE wall meets a superellipse (type=1) or superformula (type=2) cross-section at `gcurveDist * L` from the throat. See `pkg/profile_morph.py:10-72`.

### 1c. Validity guards

- `L > 0` (profile_formulas.py:517-521)
- `n > 0` and `q > 0` when `s != 0` (profile_formulas.py:272-281)
- `r0_throat >= 0`: extension cannot taper radius below zero (profile_common.py:579-585)
- `s1`, `s2` in `[0, 10]` (throat_stretch.py:37-46)
- throat stretch with `Slot.Length` in OSSE is refused (throat_stretch.py:127-128)
- throat stretch with `Rot` + prefix refused (throat_stretch.py:125-126)
- throat stretch + guiding curve + prefix/Rot refused (throat_stretch.py:129-130)

---

## 2. R-OSSE (Rollback OS-SE)

### 2a. Mathematical formula

Source: `pkg/profile_formulas.py:651-662` (`_calculate_rosse_main`).

The R-OSSE main curve is parameterised by `t in [0, tmax]` (not by axial `z`). It blends two
endpoint terms:

**Axial position:**

```
x(t) = L * (sqrt(r^2 + m^2) - sqrt(r^2 + (t-m)^2))
      + b*L * (sqrt(r^2 + (1-m)^2) - sqrt(r^2 + m^2)) * t^2
```

**Throat radius curve:**

```
throat_r(t) = sqrt(c1 + c2*L*t + c3*(L*t)^2) + r0*(1-k)
where c1=(k*r0)^2, c2=2*k*r0*tan(a0), c3=tan(a)^2
```

**Mouth radius curve:**

```
mouth_r(t) = max(0, R + L*(1 - sqrt(1 + c3*(t-1)^2)))
```

**Blended radius:**

```
r(t) = (1 - t^q) * throat_r(t) + t^q * mouth_r(t)
```

The derived axial length `L` is computed implicitly from the condition `throat_r(L_t)=R` at some `L_t` (see `_rosse_length` at profile_formulas.py:551-568).

**Throat stretch applied to x:**

```
x_stretched(t) = _stretch_x(x(t), s1, s2)   # same formula as OSSE
```

**Composite meridian (same extension/slot structure as OSSE):**
- Same ext_len/slot_len prefix structure with same `r0_throat` tapering.
- `tmax` truncates the main curve (default 1.0); for a truncated mouth set `tmax < 1`.

### 2b. R-OSSE parameters

| Config key | Default | Units | Notes |
|---|---|---|---|
| `type` | `R-OSSE` | str | formula selector |
| `r0` | 12.7 | mm | main throat radius |
| `a` | 60.0 | deg | coverage angle |
| `a0` | 15.5 | deg | throat half-angle |
| `R` | 150.0 | mm | nominal mouth/reference radius |
| `k` | 1.0 | - | shape factor |
| `q` | 1.0 | - | blend exponent (R-OSSE default is 1.0, not 0.995) |
| `m` | 0.85 | - | axial curve shape (default from `_DEFAULTS`) |
| `r` | 0.4 | - | axial curve shape |
| `b` | 0.2 | - | secondary axial blend weight |
| `tmax` | 1.0 | - | truncation limit; > 0 required |
| `s1`, `s2` | 0.0 | - | throat stretch; range [0, 10] |
| `throatExtLength`, `throatExtAngle` | 0/0 | mm/deg | same as OSSE |
| `slotLength` | 0.0 | mm | same as OSSE |

**Note:** R-OSSE has no `s`, `n`, `q`-termination in the OSSE sense; `q` here is the blend exponent, not the superellipse saturation. R-OSSE has no `L` input (it is derived). An explicit `L` with active stretch is refused (throat_stretch.py:131-132).

### 2c. R-OSSE validity guards

- `tmax > 0` (profile_formulas.py:867-869)
- `r0_throat >= 0` (same as OSSE)
- Self-contact / self-intersection checks on the composite meridian (profile_formulas.py:683-838)
- stretch with explicit `L` refused (throat_stretch.py:131-132)

---

## 3. ICW (Intrinsic-Curvature Waveguide)

### 3a. Description (from code)

Source: `pkg/icw/core.py:1-23`.

> "The canonical ICW geometry is an intrinsic (Cesaro/Whewell) plane curve: the meridian
> **curvature** `kappa` is a clamped cubic B-spline over normalised arc length
> `sigma = s/S in [0, 1]`; integrating it gives the tangent angle `theta(s)`;
> integrating again gives the meridian `(x(s), r(s))`:"

```
kappa(sigma) = sum_i a_i * B_i(sigma)    # clamped cubic B-spline
theta(s)     = theta0 + S * integral_0^sigma kappa dv
x(s)         = x0 + S * integral_0^sigma cos(theta) dv
r(s)         = r0 + S * integral_0^sigma sin(theta) dv
```

The solver builds an `ICWCurve` with: `coeffs` (curvature B-spline coefficients, units 1/mm),
`S` (arc length, mm), `r0` (throat radius, mm), `theta0` (throat tangent angle, rad),
optional `knots`, `degree` (default 3 = cubic), `x0` (default 0).

### 3b. ICW config parameters

Config key `type = "ICW"`. The ICW adapter lives in `pkg/profile_formulas.py:1009-1313`.

**Input modes (mutually exclusive, checked in order):**

1. **SEED mode** (`icw_seed`): a nested OSSE or R-OSSE param dict; curve is fit via
   `seed_from_osse` / `seed_from_rosse` (pkg/icw/seed.py:226-256).
2. **DIRECT mode** (`icw_coeffs` + `icw_S`): provide the B-spline coefficients directly
   (list of floats, units 1/mm) and the arc length `icw_S` (mm).
3. **TARGETS mode** (default): assemble `ICWTargets` and call `solve_icw`.

**Common parameters:**

| Key | Aliases | Default | Units | Notes |
|---|---|---|---|---|
| `r0` | | 12.7 | mm | throat radius |
| `a0` / `a0_deg` / `theta0_deg` | | 0.0 | deg | throat wall angle |
| `kappa0` | | 0.0 | 1/mm | throat curvature |
| `n_coeff` | | 12 (plain) / 16 (coverage) | int | number of B-spline coefficients |
| `termination` | | `flat_baffle` | str | `flat_baffle` or `rollback` |

**Flat-baffle targets:**

| Key | Default | Notes |
|---|---|---|
| `L` / `L_mm` | None | axial depth x(1), mm |
| `R` / `R_mm` | None | mouth radius r(1), mm |
| `coverage_angle` / `coverage_angle_deg` | None | CD plateau angle (deg); enables coverage mode |
| `hold_start` | 0.30 | arc-length fraction where plateau begins |
| `hold_end` | 0.70 | arc-length fraction where plateau ends |
| `pin_mouth_radius` | False | also pin r_mouth when in coverage mode |

**Rollback targets:**

| Key | Default | Notes |
|---|---|---|
| `theta1` / `theta1_deg` | 160 | terminal wall angle (deg) |
| `R` / `r_aperture` | None | radius at theta=90deg crossing (mm) |
| `x_aperture` | None | axial location of theta=90deg crossing (mm) |
| `depth` | None | total axial depth x(1) (mm) |
| `x_setback` | None | axial setback of tip behind aperture (mm) |

**Optional bounds (both modes):**

| Key | Notes |
|---|---|
| `kappa_abs_max` | cap on max|kappa| (1/mm) |
| `dkappa_ds_abs_max` | cap on max|dkappa/dsigma| |
| `theta_max_deg` | rollback only, cap on wall angle in (90, 180] deg |

### 3c. ICW solver logic (pkg/icw/solver.py)

The solver uses a **feasible-subspace** method:
- The boundary conditions (kappa at throat, endpoint tangent, terminal curvature = 0) are **linear in the B-spline coefficients** for fixed arc length S.
- A pseudoinverse gives the smoothest (least-norm) particular solution `a0 = pinv(C) d`.
- The nullspace of C (via SVD) gives shape modes that cannot disturb the BCs.
- The nonlinear size targets (x(1), r(1), or rollback aperture) are solved for S plus a few shape controls using `scipy.optimize.least_squares`.
- Coverage mode adds a constant-angle plateau in the B-spline knot structure (`coverage_knots`, core.py:117-158).

ICW is **phi-independent** in Phase 1: the same curve is used for all azimuths.

### 3d. ICW validity

- `r > 0` throughout sampled meridian (enforced in direct mode and by solver feasibility report)
- `coverage_angle_deg` must be in `(theta0_deg, 90)` deg
- `kappa_abs_max > 0`, `dkappa_ds_abs_max > 0` if set
- OSSE/R-OSSE shape keys `s1`, `s2` refused for ICW (throat_stretch.py:96-99)

---

## 4. FREEFORM

### 4a. Design contract

Source: `pkg/freeform.py:1-18`.

> "The design contract is that every cross-section outline hits the horizontal and
> vertical profile axes exactly, station joins are C1 or better (the shape blend is
> C2), and both meridians share one axial z span. The implementation follows
> `https://github.com/m3gnus/waveguide-generator/blob/v1/docs/plans/260801-freeform-hv-spline-profiles.md`
> (especially sections 2.1, 2.2, 2.3, and 2.5)."

### 4b. Profile representation

**Anchors:** Each meridian (H = horizontal, V = vertical) is specified as a list of 2D anchors
`[z_mm, r_mm]` or `[z_mm, r_mm, angleDeg]`. Count: **2 to 64** anchors per plane (freeform.py:547-549).

**Spline type:** Cubic Hermite spline built by `scipy.interpolate.CubicHermiteSpline`.
The knot parameter `u` is chordal arc-length fraction. The shape is NOT PCHIP — PCHIP
is used only to compute initial tangent *directions* (freeform.py:799-803); the actual
spline tangent *speeds* are solved to eliminate overshoot violations. Tangent angles set
the direction at throat and mouth (or per-anchor); tangent speeds are solved automatically.

**Endpoint angles:**
- `throatAngleDeg`: tangent angle from +z axis at the throat, in `[-90, 90]` deg (default: angle from first chord direction).
- `mouthAngleDeg`: tangent angle from +z at the mouth, in `[-90, 90]` deg (default: angle from last chord direction).
- Per-anchor angle: `[z, r, angleDeg]` syntax, interior anchors must be in `(-90, 90)` (strict); endpoints may equal ±90.

### 4c. Freeform config keys

| Key | Notes |
|---|---|
| `profileH` | dict with `points` (required), optional `throatAngleDeg`, `mouthAngleDeg` |
| `profileV` | same structure; may differ in anchor count from profileH |
| `crossSections` | list of 2–32 station dicts controlling cross-section shape evolution |
| `inflectionPolicy` | `'warn'` (default) or `'reject'` for reverse-curvature spans |
| `a0` | default throat angle if neither endpoint nor block-level angle is given |

**H and V anchor counts may differ** (different point arrays are valid).

### 4d. Cross-section stations (crossSections)

Each station: `{t: float, shape: str, ...}`. Rules:
- `t` must be in `[0, 1]`, strictly increasing (freeform.py:916-1006).
- First station: `t=0`, shape must be `circle` or `ellipse`.
- Last station: `t=1`.
- 2–32 stations total.
- Allowed shapes: `circle` (synonym for `ellipse`), `ellipse`, `superellipse`, `rounded_rectangle`.

**Superellipse station** adds `exponent` in `[2, 16]`.
**Rounded-rectangle station** adds `cornerRadiusMm > 0`; clamped to `min(a, b)` at runtime.

Between stations the blend uses **smootherstep** (6u^5 - 15u^4 + 10u^3), giving C2 joins.

### 4e. FREEFORM guards (from freeform.py)

- All anchor `r > 0` (line 586-587)
- Anchor `z` values strictly increasing (line 588-591)
- Per-anchor `angleDeg` in `(-90, 90)` for interior anchors; `[-90, 90]` for endpoints (line 573-585)
- `throatAngleDeg`, `mouthAngleDeg` in `[-90, 90]` (line 620-629)
- Spline overshoot guard: radius must not overshoot anchor range by more than `max(0.05, 0.001*max_r)` mm (line 762-775)
- `z'(u) >= 0` strictly: profile must not fold backward in z (line 711-718)
- Outer wall offset: normal flip and self-intersection checks (freeform.py:1245-1316)

### 4f. FREEFORM morph system

The FREEFORM formula supports the same morph system as OSSE/R-OSSE (via `morphTarget`, etc.). Morph keys accepted for FREEFORM are listed in `_FREEFORM_PARAM_KEYS` (freeform.py:46-60).

---

## 5. LOOKUP formula

Source: `pkg/profile_formulas.py:1346-1392`.

A simple tabular lookup: `lookupProfile` is an `(n≥2) × 2` array of `[z, r]` pairs, z strictly increasing, all finite. The sampler linearly interpolates at requested z stations.

No guiding curve, no morph, no extension/slot composite — purely tabular.

---

## 6. Hybrid / Morphing capabilities

### 6a. Cross-section morphing (ALL formula families)

All formulae (OSSE, R-OSSE, ICW, FREEFORM) support the **Morph system**, which blends the
circular/superellipse cross-section into a rectangular or superellipse target as a function of
normalized axial position `t` (pkg/profile_morph.py).

**morphTarget** values:
- `0`: no morph (circular/elliptical cross-sections throughout)
- `1`: blend toward **rounded rectangle** (`morphCorner`, `morphWidth`, `morphHeight`)
- `2`: blend toward **circle** (expands the smaller axis to the larger)
- `3`: blend toward **superellipse** (`morphExponent` in `[2, 16]`, `morphWidth`, `morphHeight`)

**Morph schedule parameters** (profile_morph.py):

| Key | Default | Notes |
|---|---|---|
| `morphTarget` | 0 | target shape (0=off, 1=rect, 2=circle, 3=superellipse) |
| `morphWidth` | 0 | target full width mm; 0 = implicit from mouth extent |
| `morphHeight` | 0 | target full height mm; 0 = implicit from mouth extent |
| `morphCorner` | 0 | corner radius mm for rounded-rectangle target |
| `morphExponent` | 2.0 | superellipse exponent `[2, 16]` for target=3 |
| `morphRate` | 3.0 | blend power (`t^rate`); must be >= 0 |
| `morphFixed` | 0.0 | axial `t` fraction where morph begins (0=throat) |
| `morphAllowShrinkage` | False | allow target smaller than mouth extent |

**Morph factor formula** (profile_morph.py:667-682):

```
if t <= morphFixed: factor = 0
else: factor = clamp((t - morphFixed) / (1 - morphFixed), 0, 1)^morphRate
```

Applied at every axial station and azimuth: `r(t,phi) = r_base(t,phi) + factor * (r_target(phi) - r_mouth_base(phi))`

All morph parameters can be p-dependent (expressions in azimuth `p`).

### 6b. H vs V profiles

For OSSE and R-OSSE: the profile formula is the same for all azimuths, but **all numeric parameters can be p-dependent expressions** (e.g. `a = "60 + 10*cos(2*p)"` gives different coverage in H and V). A guiding-curve solve runs independently per azimuth. This is the mechanism for creating elliptical-coverage horns.

For FREEFORM: **separate H and V profiles** (`profileH`, `profileV`) can be independently specified with different anchor arrays, enabling different profiles in each principal plane.

ICW: **phi-independent** in Phase 1 (same curve for all azimuths).

### 6c. Cross-section evolution (FREEFORM)

FREEFORM's `crossSections` list provides **multiple shape stations at different t values**,
allowing the cross-section to morph from `ellipse` at t=0 to `superellipse` or `rounded_rectangle`
at intermediate t values and back. Shapes between stations are blended via smootherstep.

This is distinct from the OSSE-family morph: FREEFORM cross-sections can change shape at arbitrary
intermediate positions, not just from a fixed start fraction to the mouth.

### 6d. Profile → ICW conversion (seed functions)

`pkg/icw/seed.py:226-256` provides:

```python
def seed_from_osse(params, n_coeff=20, n_axial=4000) -> ICWCurve
def seed_from_rosse(params, n_coeff=20, n_axial=4000) -> ICWCurve
```

These sample an OSSE or R-OSSE meridian using `profile_points`, then call `fit_from_points`
to fit a clamped cubic B-spline to the curvature of the sampled polyline. The fitted `ICWCurve`
can then be used as the starting point for an ICW optimisation. These are the **only** built-in
profile→ICW conversion functions; there is no analogous OSSE/R-OSSE → FREEFORM anchor extractor.

The ICW config's `icw_seed` key activates this path from within a config dict:
```yaml
type: ICW
icw_seed:
  type: OSSE
  r0: 12.7
  a: 60
  ...
```

### 6e. Throat extensions and slots (OSSE, R-OSSE)

Both OSSE and R-OSSE support:
- **Throat extension** (`throatExtLength`, `throatExtAngle`): a tapered tube prepended to the main horn. r tapers back from `r0` to `r0 - ext_len * tan(angle)`. Main horn throat remains at `r0`.
- **Slot** (`slotLength`): a straight cylindrical section at `r0` between extension and main horn. OSSE only: not supported with throat stretch.

### 6f. Throat stretch (OSSE, R-OSSE)

Axial nonlinear mapping applied to the main horn: `x_new = x + s1 * degrees(atan(s2 * x))`. Stretches the throat region while leaving large-z values near-linear. Both s1 and s2 must be in `[0, 10]` and must be plain numbers (not p-dependent expressions currently). Various combination restrictions (see Section 1c and 2c).

### 6g. Guiding curve (OSSE)

The `gcurveType` / `gcurveWidth` / `gcurveSF` / `gcurveSeN` keys define a **cross-sectional target shape** that the OSSE coverage angle is solved to match at a given axial station (`gcurveDist * L`). Two types: superellipse (type=1, `gcurveSeN`) and superformula (type=2, `gcurveSF.a/b/m1/m2/n1/n2/n3`). The coverage angle varies per azimuth, making H/V coverage different without a p-expression for `a`.

### 6h. Rollback / termination

- **OSSE**: The `s`, `n`, `q` termination parameters shape the mouth. No built-in rollback; the wall always terminates flat (unless the Morph wraps it to rectangular).
- **R-OSSE**: Natural rollback when the wall angle exceeds 90 deg at the mouth (controlled by `tmax`, `R`, `m`, `b`, `r`).
- **ICW rollback**: `termination="rollback"` with `theta1_deg > 90` target; solver brings the wall past 90 degrees.
- `throatProfile=3`: replaces the OSSE formula in the main section with a circular arc (profile_formulas.py:400-413).

### 6i. Mouth fitting to a rectangle (mouth_fit.py)

`refine_mouth_grid()` (pkg/mouth_fit.py:32-133) iteratively densifies the azimuthal sampling near corners of a rectangular morphed mouth until the cubic spline fit to the generated grid meets the outline tolerance (`_ROUNDED_TOLERANCE_MM = 0.15 mm` for rounded corners, `_SHARP_TOLERANCE_MM = 0.6 mm` for sharp corners). Active only for OSSE-family with `morphTarget=1` and plain numeric `morphWidth/Height/Corner`.

---

## 7. Geometric / cross-section model (all formulas)

The mesher builds a 3D surface by combining the meridian radius with a polar cross-section function:

```
r_3D(t, phi) = r_meridian(t, phi) * [shape factor from station outline] (for FREEFORM)
```

or for OSSE/R-OSSE/ICW:

```
r_3D(t, phi) = r_formula(t, phi)   [azimuthal wall]
then morphed: += morph_factor * (target_radius(phi) - mouth_base(phi))
```

**Cross-section shape at each station (FREEFORM):**

The `_station_radius(station, phi, a, b)` function (freeform.py:1061-1078) computes:
- **ellipse/circle**: `( (cos(phi)/a)^exp + (sin(phi)/b)^exp )^(-1/exp)` with `exp=2` (superellipse formula for circle = standard ellipse)
- **superellipse**: same formula with `exp in [2, 16]`
- **rounded_rectangle**: rectangular formula with circular corner arcs

Note: `a = r_H(z)` and `b = r_V(z)` from the respective meridian profiles; so the cross-section
is scaled anisotropically by the H and V meridian radii at each axial station.

---

## 8. External references cited in the code

1. `pkg/freeform.py:6-7`:
   > "The implementation follows `https://github.com/m3gnus/waveguide-generator/blob/v1/docs/plans/260801-freeform-hv-spline-profiles.md` (especially sections 2.1, 2.2, 2.3, and 2.5)."

2. `pkg/profile_common.py:239-247` (ATH a0 averaging):
   > "ATH matches an automatic source-cap radius to the "(average) throat opening angle" (Ath 4.8.2 User Guide p.22). Measured against ATH's own meshes for four designs with an azimuthally varying a0 (the 250906asro* family), that average is the plain arithmetic mean of a0 over one full turn..."

3. Multiple ATH references throughout (ATH = "Acoustic Tool for Horn designers", by Marcel Batík as implied by "ath.exe" and "ATH User Guide" mentions in config_parser.py and profile_common.py). The code matches ATH's own formula implementations (verified against ath.exe under Wine per config_parser.py:483).

4. `pkg/icw/seed.py:1` references:
   > "Cesaro/Whewell" (intrinsic curve representations) for the ICW parameterisation.

5. `pkg/mesh_repair.py:213`:
   > "It is deliberately NOT waveguide-generator's 0.9 bare-shell threshold"

6. No direct Geddes, Le Cléac'h, tractrix, or Boundary Lab citations found in the source.

---

## 9. What does NOT exist

The following profile types are NOT implemented:
- Conical horn
- Exponential horn
- Tractrix horn
- Le Cléac'h / Klipschorn / hyperbolic
- Spherical or "axisymmetric" as a named family
- Any type of spline-fitted horn other than FREEFORM and ICW-seed

There is NO built-in converter from OSSE/R-OSSE/ICW → FREEFORM anchors.
The only cross-formula conversion is OSSE/R-OSSE → ICW via `seed_from_osse` / `seed_from_rosse`.

---

## 10. Summary table

| Family | type= | Formula | p-dependent params | Rollback | Morph | H≠V |
|---|---|---|---|---|---|---|
| OSSE | `OSSE` | OS-SE + superellipse term | all params | No (only s/n/q mouth shaping) | Yes (1,2,3) | via p-exprs |
| R-OSSE | `R-OSSE` | blended throat/mouth + hyperbolic axial map | all params | Yes (natural) | Yes (1,2,3) | via p-exprs |
| ICW | `ICW` | curvature B-spline integral | no (phi-independent) | Yes (rollback mode) | Yes (1,2,3) | No |
| FREEFORM | `FREEFORM` | cubic Hermite H+V + cross-section stations | n/a | via mouthAngleDeg | Yes (1,2,3) | Yes (separate profiles) |
| LOOKUP | `LOOKUP` | linear interpolation table | n/a | n/a | No | No |
