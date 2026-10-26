# ATH CORE / TwinRay and the Ath Morph system

2026-10-25 · owner-directed framework pass. This dossier grounds the `ath_core` and
`ath_twinray_380` typologies and the native morph search surface. It is not a claim
that either config is an exact product replica.

## 1. Sources

| Source | What it contributes | Status |
|---|---|---|
| Ath 4.8.2 User Guide, `https://at-horns.eu/release/Ath-4.8.2-UserGuide.pdf` §4.1.2 p.19, §6.4.3 p.39 | `Morph.TargetShape`, `TargetWidth/Height`, `CornerRadius`, `FixedPart`, `Rate`, `AllowShrinkage`; implicit target = circumscribed rectangle; rate minimum 1; rollback/roundover vocabulary | primary (author) |
| OS-SE Waveguide, M. Batík, 2020, `https://at-horns.eu/release/OS-SE%20Waveguide.pdf` §5 | Exact morph law; `γ >= 1`; `zf`; target radius `rM(φ)` | primary (author) |
| `https://at-horns.eu/core.html` (CC-BY-4.0) | Full CORE 2-inch script: `L=260, r0=25.0, a0=1.2`, `a(p)`, `n(p)`, `s(p)`, `q=.996`, `s1=1.14`, `s2=.025`, `Morph.*`, roundover 42 | primary (author) |
| `https://at-horns.eu/twinray.html#twinray36-380` | Published dimensions for 36-10-380 and 38-00-380 | primary (manufacturer); no script |
| `docs/research/typologies/MESHER_TYPOLOGIES.md` §6a/§6g/§6h | Our mesher's morph implementation, guiding curve, rollback | in-repo verified |
| `docs/plan/12_RESEARCH_BASIS.md` §11, §13 | Prior ATH/OS-SE research; the absent `a(φ)` class | in-repo |

## 2. The morph law

For `z < zf` the raw profile is unchanged. For `z >= zf`:

```
rm(z, φ) = r(z, φ) + ((z - zf)/(L - zf))^γ * (rM(φ) - r(L, φ))
```

`zf` is `Morph.FixedPart` (fraction of horn length), `γ` is `Morph.Rate`, `rM` is the
target outline. At `z=L` the surface is exactly the target. The mesher's
`profile_morph.py` implements the same law, including:

- target 0 off, 1 rounded rectangle, 2 circle, 3 superellipse (mesher extension);
- full-width `Morph.TargetWidth/Height`; zero means the raw mouth extent (the guide's
  circumscribed target);
- `Morph.AllowShrinkage=0` floors the target at the raw extent, so the horn never
  narrows; `1` permits a smaller target;
- `Morph.Rate` >= 0 in the mesher (Ath documents >= 1); our typology bounds use >= 1.

## 3. What our search layer had

Before this pass:

- `families._MORPH` existed for **OSSE only**; no config used it.
- `families._REFUSED_HINTS["FREEFORM"]` rejected `morph_target`, even though the
  mesher supports FREEFORM morph. R-OSSE and ICW also omitted the keys.
- `morph_exponent` was missing while `morph_target=3` was accepted, so target 3
  silently used the mesher default 2.0.
- The only rounded-rectangle typology, `perturbed_osse_hv`, used a FREEFORM
  `crossSections` station (smootherstep), not Ath's morph law.

## 4. What changed

- `morph_*` (including `morph_exponent`) are legal for OSSE, R-OSSE, ICW and FREEFORM.
- Generated typologies can opt into native morph through the `morph_*` knobs; absent
  `morph_target` leaves the generated params byte-identical. The generator refuses a
  second outline mechanism (`mouth` must stay `ellipse` when native morph is active).
- `ath_core` is the first config that searches native morph: target shape (1-3),
  superellipse exponent, target widths, corner, rate and fixed part are search
  dimensions.
- `ath_twinray_380` uses the searchable superellipse cross-section instead. Measured:
  the mesher's FREEFORM morph guard rejects a rectangle target on this elliptical
  H/V base ("non-convex outline near t=0.75") for every corner radius tried; target 2
  (circle) and target 3 with exponent 2 mesh, but do not produce the published
  rounded rectangle. The superellipse station is the honest working route.
- Native morph remains available to generated typologies whose base outline is
  compatible (e.g. circle). This is a mesher guard, not a search-layer refusal.

## 4b. Opting an existing generated typology into native morph

No existing config was changed silently (that would move its design hash). To opt a
generated typology in, add to its `generator:` block and its knob space:

```yaml
generator:
  mouth: ellipse              # native morph owns the outline
seed_params:
  morph_target: 1             # 1 rectangle, 2 circle, 3 superellipse
  morph_width_mm: 380.0       # full width; 0 = raw mouth extent
  morph_height_mm: 303.0      # full height
  morph_corner_mm: 35.0
  morph_exponent: 4.0         # only for target 3
  morph_rate: 3.0
  morph_fixed: 0.0
  morph_allow_shrinkage: 1
bounds:
  morph_width_mm: {lo: 300.0, hi: 600.0}
  # ... the other morph knobs as search dimensions
```

`morph_target` and `morph_exponent` are discrete/conditional; they can be pinned
(`search: false`) or searched (the CMA-ES vector rounds the int). The mesher's
non-convex guard still applies: a rectangle target on an elliptical H/V base can be
refused (measured on TwinRay), so verify with a mesh-only probe before a campaign.

## 5. CORE reconstruction

Published law is azimuth-dependent. Our search layer has no numeric `a(φ)` generator
(the gap recorded in `12_RESEARCH_BASIS.md:530`). The config therefore uses the H/V
midpoints:

| Parameter | Published H / V | Seed |
|---|---|---|
| `a_deg` | 25.0 / 23.4 | 24.2 |
| `n` | 7.5 / 6.0 | 6.75 |
| `s` | 0.83 / 0.60 | 0.715 |
| `q` | 0.996 / 0.996 | 0.996 |
| `L_mm` | 260 | 260 |
| `s1`, `s2` | 1.14, 0.025 | same |
| morph | rect, fixed 0, rate 3, corner 16.5 | same |

`ath_core` searches L, a, n, s, q, k, s1, s2 and the seven morph knobs (target shape,
exponent, width, height, corner, rate, fixed). The
boxes are deliberately wider than the published recipe. `morph_allow_shrinkage=1`
because the published target is explicit and the optimiser must be allowed to explore
smaller mouths. Not modelled: the azimuth law, `Mesh.Roundover=42`, rear shape,
enclosure.

Seed mesh (screen, CPU, epw 8): 6,174 triangles / 3,232 dofs; bbox mouth 0.1986 m
radius; `s1/s2` stretch the axial span to ~0.353 m.

## 6. TwinRay reconstruction

Published 36-10-380: 36 mm throat, 10° total throat angle, 380×303 mm mouth, 192 mm
depth, LF point 580 Hz. Seed: `h_a 34.7`, `v_a 25.9`, `s .60`, `n 6.0`, `q .996`,
`k 1.0`, `L 192`, `mouth: superellipse`, `mouth_exponent 4.0` (inferred).

Seed mesh (screen, CPU, epw 8): 3,796 triangles / 1,987 dofs; bbox mouth
0.190×0.1517 m = 380×303.4 mm, depth 0.192 m. Not modelled: enclosure/mounting,
planar rim frame, rollback.

The brief deliberately omits `f0_hz`: the published 380×303 mouth at 580 Hz does not
satisfy the repo's K-law for a 90×60 target, and attaching `f0_hz` would both flag the
design infeasible and override the published seed through the brief derivation. The
LF point remains documented here and in the brief header.

## 7. Search-range policy

The owner's direction was explicit: the framework must solve, not reproduce a fixed
recipe. Both configs therefore use wide boxes with the published value near the
middle, not a bound. The brief envelope is the outer constraint. Mesh-only checks are
the validity gate; an over-cap or invalid point is a graded result, not a reason to
silently narrow a bound.

## 8. Open items

- Exact CORE `a(φ)` law: needs a rows/generator extension; not in this pass.
- Native FREEFORM morph to a rounded rectangle: blocked by the mesher's non-convex
  guard on elliptical bases; a fork change or a different base outline would be needed.
- `Mesh.Roundover`, Ath `Rollback`, rear shape and enclosure fidelity.
- GPU smoke evidence for the two new seeds.
