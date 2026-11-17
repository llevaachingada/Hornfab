# E2 — stored-data local invertibility

**Partial exploratory analysis:** a subsequently added detailed E2 brief calls for different held-out sampling, cross-engine neighborhoods, multiple radii and size-controlled checks. This report does not complete that brief or establish its success/failure verdict.

Run 2026-11-16 22:22 EST; HEAD `207f97a29e2f2f31a366da95e882f9b48761ab00`. Script: `.e2/e2.py`; input: `.fable/desc.npz`. CPU, no solves.

## Verdict

**The stored-data test does not establish a usable inverse or support choosing construct-then-correct as the spine.** Held-out local forward prediction has some skill, but geometry recovery is worse than the no-change baseline and local maps are often poorly conditioned. The synthesis specifies qualitative good linearity and actual convergence in about five steps, not a numerical stage-one pass line. Five-step convergence remains untested and requires owner approval; no solve was run. This is evidence against a naive local inverse in these coordinates, not proof that a constrained or regularized corrector cannot work.

## Method and results

The 1,715 designs cover 35 lanes. Shape is depth plus eight PCA modes of the two 12-point wall profiles; these eight modes explain 99.78% of profile variance. Response is six PCA components of all 54 stored H beamwidth, V beamwidth and DI values; they explain 93.05% of their combined unscaled variance. Standardize each shape and response coordinate by its global standard deviation. Global unsupervised PCA and scaling use all designs, including test designs, so this is a descriptive local test rather than a completely isolated prospective validation.

For each design, choose the nearest distinct design in standardized shape space as the held-out target and fit a no-intercept 6-by-9 linear Jacobian to differences from the center using the next 40 neighbors. Test forward response change on the held-out pair, and compute the minimum-norm pseudoinverse geometry change from the observed target response difference. No acoustic result is predicted by a solver here. The target is in the same lane for 75.1% of pairs; these are mostly local optimizer trajectories, not independent constructions.

| Measure | Result |
|---|---:|
| Forward squared-error skill versus predicting no change, pooled | 0.533 |
| Forward relative error, median (25th–75th percentile) | 0.649 (0.420–1.006) |
| Inverse geometry squared-error skill versus no change, pooled | -0.770 |
| Inverse relative geometry error, median (25th–75th) | 1.144 (0.890–1.759) |
| Jacobian condition number, median (25th–75th; 90th) | 48.2 (23.7–219.4; 1,149) |
| Singular values, median descending | 5.68, 2.40, 1.35, 0.748, 0.400, 0.116 |

Relative errors are Euclidean norms in standardized coordinates; skill is `1 - sum(error²)/sum(actual change²)`. Local design difference matrices all have numerical rank nine, but this does not establish sufficient independent physical perturbations or accurate derivatives. The 6-by-9 map necessarily has at least three geometry null directions: the true geometry change is not uniquely identifiable from six response numbers. The inverse's in-model response residual is essentially zero (median 7.3e-16), yet its recovered geometry is poor; matching a local linear prediction is not evidence of an achievable or correct physical step.

The weakest left singular response direction varies by neighborhood. Median absolute weights on response PCs 1–6 are 0.793, 0.140, 0.224, 0.147, 0.171, 0.208, respectively. Thus the weakest combination often involves PC1 heavily in this particular standardized basis; it cannot be named as one fixed frequency, plane, or completely uncontrollable acoustic direction. Full row rank of the fitted Jacobians does not prove real physical controllability. Conditioning and these weights depend on PCA, scaling, neighborhood and data sampling.

## Limitations and next step

Only two sampled profiles describe geometry; missing azimuthal, throat and termination features may confound the mapping. Beamwidth threshold crossings may be discontinuous. Mixed-unit unscaled response PCA weights beamwidth and DI by their numerical magnitudes; loading, ripple and impedance are not tested. The stored nearest pair need not be a feasible move from a given generator; PCA differences can leave its valid manifold. Local linear fits do not measure actual Newton steps, their constraints, or convergence, and this single neighborhood/basis choice does not establish robustness. The related sibling lanes are allowed in neighbors; no sibling-held-out generalization claim follows.

If the owner approves stage two, propose the specified three targets with five constrained, measured Newton-type steps each; predefine feasible geometry controls and safeguards and record response and geometry changes at every step. That is a proposal only, not an authorization or a conclusion that 15 solves will converge.

## Sibling map and seed checks

The complete naming-based lane grouping, including singleton lanes, is recorded in `.e2/sibling_seeds.txt`, generated from all valid-row run configs by `.e2/sibling_seeds.py`. It groups version and smooth twins and conservatively groups the sp, rr reference/pucker and Klangfilm axis variants. Exact nonempty `seed_params` dictionaries match for both biradial smooth twins and Le Cleach Iwata AR smooth twins. Other grouped pairs do not have exact nonempty seed matches. A different seed does not prove distinct construction or lack of lineage, and warm-start provenance and partially matching parameters were not checked. This map was not used as a holdout in the exploratory test.
