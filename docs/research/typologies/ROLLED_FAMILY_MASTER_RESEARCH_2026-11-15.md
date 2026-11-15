# Rolled-family parameter and optimizer correction

## Primary sources and correction

| Source | Established fact |
|---|---|
| [Batík Tritonia](https://at-horns.eu/tritonia.html) | Radial OS-SE angular coverage/termination variation followed by rounded-rectangle morph; not an axial cosine offset |
| [Original public script](https://at-horns.eu/ext/Tritonia.txt) | alpha(p)=48.5-7 cos(2p)^5-16 sin(p)^12; s(p)=.7+.2 cos(p)^2; k1,n3.7,q.995; morph rate3 |
| [OS-SE primary paper](https://at-horns.eu/release/OS-SE%20Waveguide.pdf) | r(z,phi) formula and radial morph, matching source and smooth termination |
| [ATH user guide](https://at-horns.eu/release/Ath-4.8.2-UserGuide.pdf) | No-shrink morph policy, fixed part, rate, rounded-rectangle dimensions and physical sampling |
| [R-OSSE primary paper](https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf) | Separate parametric axial/radial folded profile for freestanding horns |
| [BoTorch constraints](https://botorch.org/docs/next/constraints) | Input-domain constraints and expensive outcome constraints are distinct |

Correction: the earlier original 542x299 relief and later section relief vary only z. They are
valid archived axial-shape experiments, but do not implement the published radial ATH mechanism.
A sign reversal in z cannot make them radial. Keep them, their code identities and results intact.
At phi=0/45/90 degrees, published Tritonia coverage half-angles are 41.5/48.25/39.5 degrees;
wall-centre raw sections flare less than the diagonal. This supports inward-relative wall-centre
geometry, not a universal assertion that every ATH mouth must be concave. Its final rectangle
morph can enlarge radial positions, and its baffle optimization does not establish this hybrid's
freestanding performance. The original script's r0=36 differs from its page's 1.4-inch description;
do not silently use that as the HF1440 throat. Our driver remains radius18 mm / 2 degrees.

## New original hybrid law (not a Tritonia replica)

The canonical master retains each original unpuckered base: rolled rectangle or section-based
reconstruction. A categorical base/mode lives in the recipe, not a numeric optimization dimension.
For local axis radii h(s),v(s), psi=atan2(y/v,x/h). Positive inward controls H,V mm produce
rho_new=rho-W(s)*(H*cos(psi)^2+V*sin(psi)^2)*cos(2psi)^2. Thus axis H/V move inward H/V at the
window peak, and the normalized diagonal has zero radial offset. All directions are inward or
unchanged. At H4,V6 and W1: offsets -4 H, -6 V, 0 diagonal. z is unchanged by this operation.
An independently named signed axial mode is retained as an original experiment; never label
its cosine displacement as radial ATH behaviour. Zero relief must exactly recover each base.
Quintic onset/peak/end windows keep the source and returned attachment intact. A positive
radius, protected source tangent, monotone initial expansion, nondegenerate sheets, self-clearance,
full-body envelope and real assembled mesh tests are required. A box is a sampled feasibility
region, not proof that every candidate will mesh; invalid proposals are recorded before solves.

## Unified mapping and activity contract

Both types use stock DesignSpace/GeneratedSpace and grid dispatch, including fresh optimizer
worker processes. A saved recipe binds driver, schema, base/mode and all kernel/reference hashes.
One resolver computes inner and outer surfaces for envelope, meshing, BO identity and rendering.
BO checks/hash cover both surfaces for this family; old unsupported grids stay unsupported.
Only meaningful keys enter each optimization. Inactive mode amplitudes are zero and fixed;
placement keys are fixed when strength can be zero; ordered window bounds cannot overlap;
structural sampling, family and mode are fixed. Seeds must be present, finite and inside bounds,
including fixed keys. Cold replay rematerializes and requires an exact recipe hash match.
Canonical geometry identity is distinct from recipe identity, so geometry-identical inactive
settings cannot masquerade as independent BO samples. Historical axial results cannot train a
radial task unless exact surface, recipe, score and complete provenance checks establish identity.
