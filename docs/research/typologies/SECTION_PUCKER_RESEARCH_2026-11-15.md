# Section-based horn with H/V mouth relief

2026-11-15. Original hypothesis extending the validated section study; not the ATH formula.
Grounding: [previous section research](ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md).

| Primary source | What it supports |
|---|---|
| [Batík Tritonia](https://at-horns.eu/tritonia.html) | Mirror-symmetric H/V surfaces, azimuth-dependent design, measured/simulated diagonal response matters; original baffle-dependent design, not an arbitrary decorative ridge |
| [OS-SE paper](https://at-horns.eu/release/OS-SE%20Waveguide.pdf) | Smooth termination and azimuth-dependent parameters; morphology does not establish acoustic quality |
| [R-OSSE rev7](https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf) | Parametric return geometry, source matching, impedance and directivity validation; cannot represent rollback with a single-valued r(z) |

The following displacement is ours [inferred], not a published ATH construction. Preserve the
entire reference x/y surface. For nominal local half extents h(s),v(s), define
psi=atan2(y/v,x/h), A=H*cos(psi)^2+V*sin(psi)^2, and dz=A*cos(4*psi)*W(s).
W is a product of quintic ramps: S((s-start)/(peak-start))*S((end-s)/(end-peak)).
S is clamped quintic smoothstep. Station s is the reference vertical-meridian arc fraction;
it is not a percentage of axial depth. Initial fixed onset .30, peak .80, end .96.
Throat blend ends at s=.071-.077 over the original common bounds; onset is well after it.
W and its first two derivatives vanish at onset/end, leaving the rear returned edge untouched.
At peak: H=4,V=6 produces centre offsets +4 H, +6 V, diagonal -5 mm. Centre-to-diagonal
relief is therefore 9 H and 11 V mm, not the raw input amplitudes. The units are millimetres.
Zero H/V must reproduce the reference points and body exactly; prior recipe bytes stay frozen.

Validation before queue: exact zero control; unchanged throat radius and slope; H/V and diagonal
reference values; finite derivatives, mirror planes, no row degeneracy, real return retained;
reference outerbody agreement; actual assembled BEM mesh clearance/topology/cap/envelope/source;
64 uniform box points per arm plus all bound corners. Ranges are provisional until this evidence.
No caps, mesh density or refusal tolerances are widened to accept a new seed.

A matched fresh visual-seed control and two nonzero relief strengths use the same reference
417 x203 profile proportions and common geometry box, seed1234, objective7, brief, mesh policy
and attempted evaluation budget. This is not warm-starting from the previous acoustic winner.
Prior search rows supply headroom/boundary context, not an imported optimizer mean.
Before launch record explicit ranges, initial physical step sizes and measured refusal rate.

## Final recipe and feasibility evidence

Common geometry box: depth192..204 mm, H depth scale .98..1.02, crown18..22 mm. Seed198/1/20.
The narrower common box keeps this visual study close to the measured sections. It is not an
expansion of the prior acoustic winner's near-boundary H depth scale. Width417 and height203 mm,
2 degree driver exit, radius18 mm, wall3 mm and power32 remain fixed. Pucker location .30/.80/.96
is fixed in all arms. Grids are65 azimuth rows and128 stations; stock meshing epw6, quadrants1,
screen cap6000 and verify/final caps24000 are unchanged. This is not a mesh-convergence study.

| Arm | H seed / bounds mm | V seed / bounds mm | Seed DOFs | Uniform boxes | All corners |
|---|---|---|---:|---:|---:|
| control | 0 / fixed0 | 0 / fixed0 | 3306 | 63/64 | 8/8 |
| moderate | 3 / 0..6 | 4 / 0..8 | 3152 | 62/64 | 32/32 |
| strong | 7 / 4..10 | 9 / 6..12 | 3134 | 62/64 | 32/32 |

The random refusals are invalid_geometry, not unvalidated samples. They are explicitly charged
as flat penalties to the48-attempt budgets; predicted valid attempts47.25/46.5/46.5 are estimates,
not guaranteed counts. Maximum corner4055 DOFs. Seeds couple round36 mm and fit the envelope.
Exact JSON including configuration hashes and tested corner coordinates lives at
`docs/queue/section_pucker_validation_2026-11-15.json`.

All arms use seed1234, population8, budget48, sigma0 .15. Physical initial standard steps are
1.8 mm depth, .006 H depth scale, .6 mm crown; moderate H/V .9/1.2 mm, strong H/V .9/.9 mm.
All searched seeds are mid-box. Historical control common-knob spread recommends sigma .15;
new five-dimensional treatment basin widths are unknown. The history tool correctly refuses
warm-start comparison across the new knob set. We do not import that mean or claim a measured
five-dimensional basin. Fresh reference seeds and separate nonzero relief add new hypotheses.
Predictions to test: best-at >0 and first improvement within n1..8, not promises of improvement.

145 focused CPU geometry/grid/meshing/catalog/replay tests passed in48.378 seconds, including
19 new relief checks. All parent source bytes and old saved recipes remain unchanged. Zero
pucker is point-for-point identical to the parent at the matching grid sampling. The separate
entry point is `tools/geometry/section_pucker_cli.py`; its identity includes both new source
files, both parent surface files, the shared adapter and the reference table. Use it for all
search, shape-check, preflight, saved replay and verify-night operations.
