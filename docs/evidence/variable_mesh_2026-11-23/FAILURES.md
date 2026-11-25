# FAILURES — what did not work, what was fixed, what remains

This file is deliberately split into **defects fixed in this pass**, **route limitations that were
not “fixed” because the fix would be wrong**, and **measurement limitations**. Each item says what
was observed, the exact evidence, and the consequence for adoption.

---

## A. Defects fixed in this pass

### A1. Rear-cap triangles were folded into `throat_transition` (audit defect)

The flat rear cap sits at z = −6 mm, 6 mm behind the throat plane. A nearest-point rule alone
assigns those triangles to the inner throat ring because that ring is closer than the outer shell;
the first audit run therefore reported a throat-transition p95 of **7.92 mm** and max 11.2 mm on
class 1, which looked like a coarse throat.

**Evidence:** the pre-fix text output (class 1) had
`throat_transition 152 tris p50 3.634 p95 7.919 max 11.205`; the coarse rows were all at
`z = −6.0` (7 triangles). After deciding the rear plane before the inner/outer comparison:
`throat_transition 140 tris p50 3.553 p95 3.961 max 4.696`, plus a separate `rear_cap` row.

**Consequence:** the throats are fine; the earlier alarm was a diagnostic error. Fixed in
`tools/analysis/mesh_region_audit.py`; no solver or mesh change.

### A2. The mouth-plane fill was reported `unknown` (audit defect)

Meshes that do not carry tag 12 write the planar mouth fill as tag 1. At the mouth plane the
nearest inner and outer points are both ~3 mm away, so the ambiguity rule marked the fill
`unknown` (1.67% of class 3, 0.16% of class 1).

**Fix:** ambiguous triangles at the last producer station (`station_frac ≥ 0.98`) or at the mouth
plane are `mouth_aperture`; ambiguous triangles behind the throat plane are `rear_cap`; everything
else remains `unknown` rather than being labelled by guesswork. Unknown is now **0.00%** on the
formula classes.

**Consequence:** the aperture is visible and finer than requested (p50 4.65 mm vs 7.1 mm on
class 3) — a property of the fill, not a defect; adopters should not assume the aperture is at the
mouth size.

### A3. `mesh_meta.json` dropped the mesher's own provenance (provenance defect)

`mesh/build.py` wrote the search-side result and the mesher config but not the mesher's own
`MeshInfo.metadata` (clearance caps active, quality, facet validation, freeform deviation). The
GUI and this audit could not tell whether a clearance guard was active.

**Fix:** an additive `mesher` block with a JSON-safe subset of the known keys
(`mouthRimClearance`, `outerWallClearance`, `quality`, `freeformProfileDeviationMm`, etc.). Old
`mesh_meta.json` files simply lack the key; the mesh hash and every cache entry are unchanged.
Test: `tests/test_mesh_meta_provenance.py`.

### A4. The GRID route wrote no `mesh_meta.json` (provenance defect)

The point-grid route deliberately had no cache/meta. That made the GUI policy line, this audit and
any future convergence check impossible without re-deriving the recipe.

**Fix:** `mesh/grid_build.py` writes an additive sidecar with `mesh_route: "grid"`,
`grid.n_phi/n_s/wall_thickness/row_span`, `result`, `summary`, `rear_res_factor` and the mesher
metadata. No cache key or mesh hash depends on the sidecar. The existing test that asserted “no
meta” was updated to the new contract; `search/evaluate._grid_info` now reads the real area for
**new** rows (old rows stay `None`; no historical record is rewritten).

### A5. CAD ignored the rear factor but the record did not say so (honesty defect)

`mesh/step_build.py` resolves `res["rear"]` but only uses `res["throat"]` and `res["mouth"]` in its
single global size field. The mesh is literally identical for factor 1.0/1.5/2.0, while
`mesh_meta.result.res_mm.rear` shows the requested (larger) value.

**Evidence:** three CAE arms, same design and epw:

```text
rear1_epw1  11979 triangles, 6135 vertices
rear1.5_epw1 11979 triangles, 6135 vertices
rear2_epw1  11979 triangles, 6135 vertices
```

**Fix:** `mesh_route: "cad"` and
`rear_res_policy: {requested_rear_mm, applied_to_mesh: false, reason: "CAD route uses one global
wall size; no outer/rear surface label"}`. Test:
`tests/test_mesh_step_build.py::test_cad_rear_res_policy_is_recorded_as_not_applied`.
No attempt was made to coarsen the single wall tag: that would coarsen the acoustic bore too.

---

## B. Route limitations that are not bugs (and are not “fixed”)

### B1. CAD/STEP rear coarsening is unsupported

The STEP contract has one **wall** label and one **driver** label. The outer shell and rear cap are
not separately labelled. A rear size field would have to be applied to the whole wall, including
the acoustic bore, which violates the mandate's “do not coarsen where it matters” rule and would
change the acoustic surface. The honest policy is: **retain the working CAD policy; rear factor is
inert and recorded as such.**

### B2. The T2 MEH CAD mesh is under-resolved at 10 kHz by its own validator

Every CAD arm emits the mesher's frequency report:

```text
cad mesh: requested max frequency exceeds conservative global mesh limit (10000 Hz > 5023.38 Hz);
driver rigid walls within the transition distance are underresolved for 10000 Hz (wall valid
5348.31 Hz, patch valid 11796.8 Hz); entry_mid rigid walls ... (wall valid 5152.66 Hz, patch valid
11527.3 Hz); the mesh is written with the frequency report on its record
```

This is not a rear-factor issue (the factor is inert). It means the CAD/MEH class cannot be used to
claim 10 kHz acoustic convergence; its rank at 10 kHz should carry that flag. The existing
`mesh_meta.cad.frequency_validation.max_valid_frequency_hz = 5023.38` is the number to quote.

### B3. Point-grid factor 2.0 is inert because the wall-clearance guard binds

The point-grid class reduces 10069 → 9323 triangles at factor 1.5 (−7.4%) and 9321 at factor 2.0
(−7.44%, i.e. 2 triangles). The auxiliary producer-grid reconstruction shows why:

```text
rear1_epw1   outer_shell n=3885 p50 7.15 p95 8.38 max 11.02
rear1.5      outer_shell n=3153 p50 8.05 p95 10.26 max 15.60
rear2        outer_shell n=3153 p50 8.05 p95 10.26 max 15.60
```

The outer shell stops at ~8.05 mm even when the requested rear is 14.3 mm. This is the 3 mm wall's
self-intersection/clearance guard (chord budget), not a field that failed to evaluate. Disabling it
would risk a shell that chords through the acoustic surface; the mandate forbids that. Consequence:
the **15% DOF target is not available on this class**; 1.5 is still safe and should be kept.

### B5. Mounted / enclosure topology: the rear factor is inert (auxiliary probe)

The six audited designs are free-standing. A mounted probe (`examples/rosse_baseline.yaml` seed
with `examples/briefs/enclosure_1in.yaml`, the only WP12 enclosure brief) gives **4726 triangles at
factor 1.0, 1.5 and 2.0**, while `mesh_meta.result.res_mm.rear` changes 10.39 → 15.59 → 20.79 mm. The
enclosure builder replaces the outer shell/rear cap and sizes its walls from
`enc_front_res_mm`/`enc_back_res_mm`, so there is no rear surface for the factor to act on. The
record now carries `mounting.rear_res_policy.applied_to_mesh = false` with that reason. Do not
quote a DOF saving for mounted runs.

### B4. The point-grid production screen cap refuses a 1.5× finer reference

An early attempt with the original `grid_ellipse`-family config at `epw ×1.5` was refused:

```text
MeshTooLargeError: 6647 dofs (12941 triangles, 6647 vertices) exceeds the dof cap 6000 for
quadrants '1'; lower f_max or epw
```

The cap is an admission guard, not physics; a finer reference can be built by raising the cap in a
scratch config, but that is not a production-valid arm. The grid class therefore has no fine
acoustic reference and was excluded from the adoption decision.

---

## C. Measurement limitations (stated, not hidden)

### C1. Acoustic A/B ran on `beat_cpu`, not the production CUDA path

The live `v11_bo_day_core_2026-11-23` queue owned the GPU for the whole pass (one CUDA solve at a
time). The relative mesh comparison used the free CPU lane and the same BEAT formulation on a
different device. Acoustic differences are valid as a mesh comparison; **GPU wall times were not
measured** and no GPU performance number is claimed. `PERFORMANCE.csv` says `solver_backend =
beat_cpu` and carries the caveat in every solved row.

### C2. The acoustic reference is the finest feasible arm, not ground truth

The reference is `rear1.5_epw1.5` (epq 9): 7,693 / 8,621 / 7,770 DOF at 8 kHz, 11,813 DOF at 10 kHz and 14,720 DOF at
12 kHz. A still-finer epq 12 arm was not run (CPU budget and, at 12 kHz, the production cap). The
claim is “all candidate arms are within the criteria of the finest feasible reference”, not
“converged against an exact solution”. The fine arm itself moves on-axis by <0.03 dB, which bounds
the remaining uniform-refinement sensitivity on these designs.

### C3. The 12 kHz case uses a scratch brief, not a production identity

The class-6 design's own brief stops at 8 kHz. The 12 kHz case used a copy with
`target.band_hi_hz: 12000`, `grid.screen_extra_hz` removed, and an explicit 9-point list; the 10 kHz
case used the same construction at `target.band_hi_hz: 10000`. Both are mesh-convergence probes,
not a change to the SCREEN default and not new production identities. The separate 12 kHz
orchestrator owns that decision.

### C4. Deep nulls and balloon phase

The bounded complex-pressure error is ~0.004–0.011 (p95) and is the metric used for nulls. The
balloon **phase** at near-null directions rises to 19–61° depending on arm (worst for factor 2.0 at
12 kHz); that is a phase of a tiny amplitude, not a 60° error in the main lobe. Do not quote the
phase without the amplitude floor. Likewise the diagonal-cut SPL maximum reaches 0.2–4.0 dB, but
every maximum is at a rear null (reference −42 to −59 dB) where the bounded complex error is only
0.0043–0.0107; the diagonal p95 is 0.10–0.53 dB. Do not quote the diagonal max dB alone.

### C5. No real >60k-triangle design for a decimation screenshot

The largest recent solved designs are ~33k triangles; the GUI display-decimation path above 60k
was verified with a synthetic intercepted payload and is named
`renders/mesh_density_decimation_warning_synthetic.png`. The code path is exercised, but not on a
real solved mesh of that size.

### C6. CPU host restart during the class-1 reference arm

The `beat_cpu` worker host died once with `ConnectionResetError 10054` during the 683 s reference
solve; the harness re-warmed once and completed the arm. The solve result is present and the CSV
row is complete. This is a lane-stability note, not a mesh result. No other arm restarted.

### C7. Existing B1 limitation not reopened

The B1 pass (2026-11-18) recorded that the two most-referenced leaders could not be refined
(`mesher refuses epw 12`). This pass did not re-litigate those two designs; the class-6 leader is a
different current design that refined cleanly. Do not read this evidence as clearing the B1
leaders' mesh floor.

---

## D. Summary of what a reader must not conclude

* Do not conclude factor 2.0 is safe for every family from one 12 kHz leader; it is not adopted.
* Do not conclude CAD rear coarsening works; it is inert and recorded as such.
* Do not conclude the point-grid class reaches the 15% target; it does not, by design of the
  clearance guard.
* Do not conclude the acoustic reference is exact; it is the finest feasible arm.
* Do not conclude GPU wall-time savings were measured; they were not. The DOF reduction is measured;
  GPU time scaling is inferred.
