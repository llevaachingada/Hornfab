# CANONICAL_SURFACE_CONTRACT — interface contract, not code

**Status:** proposed contract for a read-only geometry-analysis layer. Nothing here replaces a
generator, the mesher, or the dataset identity system (`dataset/identity_v2.py`). Field names are
suggestions; the content of each field is the contract. Items marked **TO CONFIRM** must be checked
against code by the X1 agent before anyone relies on them.

## 1. Purpose and non-goals

**Purpose.** One sampled description of the acoustic surface of any non-CAD horn, so that geometry
can be compared, constrained, differentiated and learned from across engines.

**Non-goals.** It is not a new way to generate horns. It is not the mesh. It is not an identity: a
design is still identified by its recipe and `physical_solve_id`. It is not lossless.

## 2. The four related objects

```
original geometry          (family + params, or generator spec + knobs, + brief)   EXACT, authoritative
      │  sample (deterministic, versioned)
      ▼
canonical surface record   (arrays + metadata, this contract)                       APPROXIMATE
      │  compute (deterministic, versioned)
      ▼
geometry descriptors       (fixed-length numbers and curves)                        DERIVED
      ┆  joined by design_hash, never computed from
      ▼
acoustic measurements      (response.npz, metrics; keyed by physical_solve_id)      MEASURED
```

Rules:
- The original geometry stays the only source of truth. A canonical record can always be
  regenerated; it is a cache.
- Each arrow carries a version string (`sampler_version`, `descriptor_version`). Changing either
  never changes a solve, analysis or score identity.
- Descriptors are joined to acoustic rows by `design_hash` plus the brief hash. One design may have
  several solves (different mesh or frequency grid); the surface is shared by all of them.

## 3. Coordinates and units

- Right-handed Cartesian, **millimetres**. (The mesher writes meshes in metres; point grids are in
  mm. The record is mm.) **[verified for point grids; mesh units verified]**
- **z** is the horn axis, pointing from throat to mouth. The throat plane is z = 0. **TO CONFIRM**
  for engines with an extended throat or slot, where the driven plane may sit at z < 0.
- **x** is horizontal, **y** is vertical. The H plane is y = 0; the V plane is x = 0.
- Azimuth φ is measured from +x toward +y. φ = 0 is the horizontal wall, φ = 90° the top wall.
- Angles in degrees. Wall angles are half-angles from the axis; coverage angles in briefs are total
  included angles. State which one in every field name.

## 4. Surface parameterization

`inner[n_phi, n_s, 3]`: the acoustic (inner) wall.

- **s index** runs from the throat ring (s = 0) to the last point of the acoustic wall at the lip.
  Stations are spaced by **normalized arc length** along each azimuth, not by depth. This is what
  allows rollback and re-entrant lips. The record also stores `arc_length_mm[n_phi, n_s]`.
- **φ index** covers the modelled sector only, at equal angle steps including both sector ends.
- **Sampling requirements (minimum):** `n_s ≥ 65`; φ step ≤ 3°; and the refinement test in §8 must
  pass. Features finer than the φ step (mouth ripple, flutes, petals) are flagged in `fine_features`
  with their count and amplitude; they are not guaranteed to be resolved.
- The throat ring `inner[:, 0, :]` is stored exactly as the generator produced it.

## 5. Required metadata

| Group | Fields | Fidelity |
|---|---|---|
| Provenance | `design_hash`, engine (`OSSE`, `R-OSSE`, `ICW`, `FREEFORM`, `grid`, `rows:<type>`, family adapter name), config name, brief hash, mesher and generator versions, `sampler_version` | Exact |
| Symmetry | Modelled sector: quarter, half (left-right), half (up-down) or full; the mesher `quadrants` string (`"1"`, `"14"`, `"12"`, `"1234"`); whether the full surface is mirror-symmetric in H and in V | Exact |
| Throat | Radius or section at s = 0, wall half-angle at the throat in H and V, extension and slot lengths if any, position of the driven plane | Exact |
| Source and driver | Driver exit radius and exit angle from the brief; source cap shape, radius, curvature and auto angle as passed to the mesher; `source.cap` setting | Exact (copied, not sampled) |
| Termination | Kind: `flat_cut`, `rollback`, `lip_arc`, `toroidal`, `baffle`; lip radius and wrap angle where defined; index in s where the forward-facing wall ends; whether any azimuth has non-monotone z | Kind exact, shape sampled |
| Outer shell | Present or not; wall thickness; `outer[n_phi, n_s2, 3]` if the generator builds an explicit outer surface; rear closure kind | Thickness exact, surface approximate |
| Mounting | None, freestanding, or enclosure; enclosure plan and dimensions if any; baffle size if any | Exact (copied) |
| Envelope | Outer bounding box W, H, D in mm computed from the sampled outer surface (or inner plus thickness if no outer array), with the method named | Approximate, within §8 tolerance |
| Topology flags | `star_shaped` (true if radius is single-valued in z at every azimuth), `closed_ring`, `has_ports` (must be false, see §9), `fine_features` | Exact |

## 6. Exact versus approximate

**Must be preserved exactly** (copied from the recipe or brief, never re-derived from samples):
design and brief identity; symmetry and sector; throat radius and angles; all source and driver
fields; wall thickness; mounting; termination kind; units.

**May be approximate** (within the tolerances of §8): the wall between samples; the lip shape; the
outer shell; the bounding box; anything finer than the sampling.

**Not represented at all:** mesh density and element sizes; material; anything inside the driver.

## 7. Descriptors computed from the record (minimum set)

- Size: mouth width and height (inner and outer), depth, bounding box.
- Along-wall curves on a fixed grid of 32 arc-length stations, for H and V planes and the 45°
  diagonal: half-width, depth z, wall angle from the axis.
- Section curves at the same stations: area A(s), aspect ratio R(s) = width/height, a shape index
  (area divided by the area of the bounding rectangle, which is π/4 for an ellipse and 1 for a
  rectangle).
- Termination: lip radius, wrap angle, rollback depth.
- Constraint margins, signed, in mm or degrees: envelope margin per axis, throat fit, minimum
  wall-to-wall gap, minimum curvature radius.

Wavelength-scaled copies (multiply lengths by 2π f / c) are derived on demand, not stored.

## 8. Acceptance tests for a sampler (per engine)

1. **Refinement:** doubling `n_s` and halving the φ step moves no descriptor by more than 0.5 %
   and no surface point by more than 0.2 mm.
2. **Agreement with the mesh:** the distance from stored mesh wall nodes to the sampled inner
   surface has median ≤ 0.3 mm and 99th percentile ≤ 1.0 mm (to be tightened or loosened by X1
   using the measured mesher fit error).
3. **Envelope:** bounding box agrees with the stored row's `bbox_m` (after symmetry doubling)
   within 1 mm.
4. **Metadata:** every exact field equals the value passed to the mesher for that design.
5. **Determinism:** same inputs give byte-identical arrays.

## 9. Geometries this representation cannot faithfully describe

- **Multi-entry horns and anything with ports or mid-wall openings** (MEH, `mid_ports`): the wall
  is not a single sheet and there is more than one source. Excluded; `has_ports` must be false.
- **CAD STEP bodies** (multicell, plughorn): topology comes from a solid model, cells or plugs
  divide the air volume. Excluded.
- **Septa, vanes, phase plugs, multicell dividers:** more than one surface between throat and mouth.
- **Sharp creases and fine periodic detail** (flutes, serrations, petals with folds): representable
  only up to the φ sampling; flagged, not guaranteed.
- **Enclosure and baffle geometry beyond simple parameters:** carried as metadata, not as surface.
- **Surfaces that self-intersect or whose rollback wraps behind the throat plane in ways the arc
  parameterization folds over:** the record must refuse rather than emit a wrong surface.

For excluded geometries the layer returns a typed refusal naming the reason. It never returns an
approximate surface silently.

## 10. What the contract enables

| Use | How |
|---|---|
| Geometry comparison | Distance between descriptor vectors, or between surfaces at matched (s, φ); works across engines |
| Transfer learning | Descriptors (optionally wavelength-scaled) as model inputs; response curves as outputs; joined by `design_hash` |
| Parameter sensitivity | Finite-difference Jacobian of the surface with respect to each knob; zero columns are inactive knobs, collinear columns are coupled knobs, rank is true dimension |
| Constraints and refusals | Signed margins replace binary refusals; one envelope and gap test for every route |
| Geometry modification | A deformation is a displacement field on (s, φ) added to the surface and handed to the mesher's point-grid input; the unmodified surface reproduces the original |
| Novelty and coverage | Distance to the nearest stored design in descriptor space |

## 11. Existing code the contract should reuse, not duplicate

- Mesher point-grid input: `.venv/Lib/site-packages/hornlab_mesher/geometry.py:214`
  (`PointGridHornGeometry`) and its caller `hornlab_search/mesh/grid_build.py:150-200`.
- Grid and rows evaluation: `hornlab_search/design/generators/grid.py` (`grid_points`,
  `rows_per_azimuth`, `envelope_extents`).
- Native surface resolution without meshing: `hornlab_search/bo/data.py:871-953`
  (`materialize_geometry`) and `tools/analysis/geometry_effects.py` (which refuses non-star-shaped
  and point-grid surfaces; the contract removes that limit by using arc length).
- Existing nine-number descriptors: `tools/analysis/geometry_descriptors.py` (native only).
- Parameter activity vocabulary: `tools/analysis/parameter_activity.py`.
