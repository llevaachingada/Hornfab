# Klangfilm and Le Cléac'h Lamé integration: research and current gate

The supplied 2026-11-16 senior handoff and versioned API contract propose two
separate families. The existing research dossier is
[`klangfilm_lame_handoff_2026-11-16/01_IMPLEMENTATION_HANDOFF.md`](klangfilm_lame_handoff_2026-11-16/01_IMPLEMENTATION_HANDOFF.md),
including its source table and throat addendum. The proposed H/V Le Cléac'h
surface is a derived geometry, not a published Fourcade construction.

| Source | Contribution | Status |
| --- | --- | --- |
| [Fourcade, Calcul du Pavillon Le Cléac'h (2015)](https://unepassionaudiophile.fr/wp-content/uploads/2018/01/Pavillon-JMLC.pdf) | Axisymmetric parent and reference calculation | Primary mathematical source; parent, not H/V extension |
| [Le Cléac'h, horn profiles](https://pearl-hifi.com/06_Lit_Archive/14_Books_Tech_Papers/LeCleac%27h_Jean-Michel/Horn_Profiles.pdf) | Original construction presentation | Primary author; full document not independently examined in this pass |
| [University of Maryland, Superellipse](https://physics.umd.edu/hep/drew/Math/superellipse.html) | Planar superellipse equation and area | Mathematical cross-check; not acoustic evidence |
| Existing Klangfilm dossier | Ahlswede/Kolbrek source trail and curved-cap derivation | Existing senior research, generalized shape remains derived |

Fourcade's parent is implemented in `profiles.lecleach_exact`. Its existing
reference test reports 467.30 mm published and calculated width, and
321.35 mm published versus 321.79 mm calculated length. The planar section
extension uses `C(p) = 4 Gamma(1+1/p)^2 / Gamma(1+2/p)` and axes whose
product is `pi*r^2/C(p)`; this preserves planar section area only. It does
not establish preservation of the parent's curved wavefront or acoustic
coverage. The proposed seed domains and lip, sweep, and warp meanings are in
the supplied API contract; all are geometric hypotheses pending validation.

The existing Klangfilm kernel is a curved-cap-area model, distinct from this
flat-area extension. Seed `rim_sweep` maps to `rim_sweep_ratio`: its physical
setback is the ratio times the maximum horizontal semi-axis. Seed aspect is
the section ratio, not a promised final envelope or beamwidth. The existing
CLI hashes its own file, the bridge and the kernel but omits the imported
`lame_cap.py`; do not treat that digest as complete geometry identity. It is
a process-local bridge, not the requested canonical registration. Changing it
in place could disrupt existing recipes or live work; a new versioned route
must include all geometry dependencies and preserve historical replay.

The modeled 36.0 mm throat and 2-degree input are legacy assumptions. The
manufacturer's stated 35.8 mm outlet and unknown physical outlet angle must
not be conflated with them. Surface validity, mesh topology, real shell
thickness, fidelity and acoustic performance require independent checks.
No result from a render alone establishes 80-by-50-degree coverage or
700-Hz loading. The 16 K and 12 L source seeds remain unvalidated and
unsolved until individually screened; never silently repair or queue them.

The supplied handoff's empirical aperture heuristic estimates roughly
726 mm for 50-degree vertical control at 700 Hz, larger than the 480 mm
height limit. At 480 mm it estimates control onset near 1.06 kHz. This is a
class-dependent heuristic, not a bound or a prediction for these designs;
only matched polar and loading measurements can establish their performance.

## Initial sampled-surface diagnostics

The reproducible [K results](dual_lame_2026-11-16/k_visual_seed_diagnostic.json)
and [L results](dual_lame_2026-11-16/L/results.jsonl) use the supplied seed
manifests. K uses the existing cohort defaults; L uses an experimental
45-degree lip tangent to the discrete parent march and a pre-lip, pre-sweep
axial-depth target. These are implementation choices, not validated
published constructions. Sampled inner surfaces generated for all 28 cases.
K's 16 and L's first 11 sampled inner bounding boxes fit the requested
envelope; L12's corrected sampled width is about 633 mm. The sampled inner/outer
shell adapter checks in [screen](dual_lame_2026-11-16/screen/geometry_metrics.csv)
pass 27 cases and reject L12 for width. They do not certify global geometry.

Both families now have separate, digest-bound GRID routes, fixed geometry-only
examples, and preview-only GUI entries. The [contact sheets](dual_lame_2026-11-16/render)
show all 28 original inner surfaces at a fixed scale, without shell. The
[mesh audit](dual_lame_2026-11-16/mesh_audit/README.md) preserves the two
first-seed meshes and source-tag evidence. The [K meshes](dual_lame_2026-11-16/all_seed_mesh/README.md)
and [corrected L meshes](dual_lame_2026-11-16/l_corrected_mesh/README.md)
record all 27 meshable seeds. Independent [CGAL checks](dual_lame_2026-11-16/cgal_audit/README.md)
found no self-intersections in those sampled meshes; the original L meshes
were superseded after the lip tangent correction. The source is a 36 mm
modeled, curved cap, not a verified physical HF1440 field.

**Hold:** The local shell and independent intersection checks are sampled;
they do not prove intersection freedom of the continuous surface, closed mirrored volume,
curvature convergence, or suitability for acoustic solving. The L lip uses
a fixed 45-degree continuation tangent to the discrete parent interpolant,
not proven C1/C2 against an exact continuous Fourcade wall. The axial factor
applies before lip and sweep. VTK and PyMeshLab collision tests missed
coplanar overlaps; CGAL passed the controlled fixtures, but its result is
limited to the saved mesh. No automatic queue admission or
acoustic evaluation follows from these results. The historical Klangfilm
ellipse progression also remains a distinct construction; `p=2` alone does
not recover it. The separate flat-area L transformation does not preserve the
parent's curved wavefront area.
