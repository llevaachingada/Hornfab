# X2 — module authority, stored-data and CPU geometry stage

**2026-11-16; HEAD `207f97a29e2f2f31a366da95e882f9b48761ab00`.** No BEM solve or mesh build. **Authority is not established.** Under strict held-out-engine prediction all three base designs and all 144 tested two-plane variants exceed the 95th-percentile nearest-training distance. The two-plane model cannot evaluate diagonal pull or lip roll. A CPU surface Jacobian indicates that one diagonal field has unexplained normal displacement above 0.5 on two bases, but this is geometric evidence only, and its acoustic effect and validity remain unknown. Neither the X2 success nor failure criterion is decided.

## Fields and method

The modeled angular weights are `sin²φ` for vertical squeeze, `cos²φ` for horizontal widening, one for mouth flare, and `sin²(2φ)` for diagonal pull. Along normalized meridian arc `s`, outer fields use `sin²(π(s−0.5))` for `s > 0.5`, inner squeeze uses `sin²(2πs)` for `s < 0.5`, and mouth flare uses `sin²(π(s−0.85)/0.30)` for `s > 0.85`; zero elsewhere. The 1-mm-weight displacement is along the outward surface normal, with squeeze sign reversed. All have zero throat displacement. Diagonal pull here is concentrated over the outer half; lip roll requires a termination-radius construction and remains undefined and untested, rather than being replaced by a flare.

For geometric redundancy, existing CPU surfaces for the exact historical full-J best in each lane were sampled and finite-differenced at 1% of each bound range (one-sided at a bound). Surfaces are interpolated to 33 azimuth-index and 80 normalized arc stations; each nonzero Jacobian column is normalized, SVD establishes its span, and `||field − projection|| / ||field||` is reported. This sampled-grid correspondence has not passed X1's mesh-agreement/refinement gates. It mixes tangential and normal surface movement in the existing-knob columns and should be treated as an exploratory geometric residual, not proof of independent physical control. Native and biradial rematerialized bases matched their stored recipe surfaces exactly on this sampling; R-OSSE's historical `rosse_rect` bridge is not supported by the current `grid_points` resolver.

For predicted beamwidth, the available 27-descriptor mesh dataset uses 12 radial samples each in H and V at normalized **depth**, not arc length; only meridian projections were perturbed. Thus this approximation is not the same full normal field used in the Jacobian, especially on swept/rolled surfaces, and the two results cannot be combined as a pass. ExtraTrees (100 trees, leaf 2) trains only on the other two engines; the base is compared to its own surrogate prediction. The raw perturbation approximates the two bounding half-width changes by the last meridian sample. A sensitivity variant rescales both entire meridians to restore the original bounding half-widths; neither is an envelope check. Each ±5, ±10 and ±20 mm prediction and its distance is in `.x2/results.json`.

## Geometric redundancy

| Field | Ext-throat OSSE | Biradial GEN-FF | R-OSSE GRID |
|---|---:|---:|---|
| Vertical squeeze, outer | 0.584 | 0.451 | unavailable |
| Vertical squeeze, inner | 0.613 | 0.481 | unavailable |
| Horizontal widening, outer | 0.557 | 0.476 | unavailable |
| Mouth flare | 0.492 | 0.488 | unavailable |
| Diagonal pull, outer | 0.633 | 0.601 | unavailable |
| Lip roll | unavailable | unavailable | unavailable |

All eight searched knobs for each supported base produced Jacobian columns; each matrix had rank eight at the stated numerical tolerance. The diagonal field is the sole tested field over 0.5 on both supported bases, but the response input has no diagonal section feature, so its acoustic authority is **unobservable**, not zero. `jacobian.json` contains column names, singular values and errors. The exact base identities are ext-throat `3a1038da45d0`, R-OSSE `a301d2543a96`, and biradial `d24016b7ab8a`.

## Surrogate-only changes at +10 mm

Each cell shows predicted **H / V** change in degrees for frequency bands 0.7–1.1, 1.1–2.5 and 2.5–5.5 kHz, respectively. These are model outputs on an approximate descriptor perturbation, **not acoustic results**. They are included to expose the model's behavior; all are extrapolations and none is a trusted nomination. Off-axis/axis ratios can be derived per band from each pair; where the intended-axis value is near zero, the ratio is unstable. Mouth flare has no single intended axis.

| Base | Field | Band 1 H/V | Band 2 H/V | Band 3 H/V |
|---|---|---:|---:|---:|
| ext | V outer | +0.94 / +2.26 | +1.18 / +1.28 | +0.70 / −0.03 |
| ext | V inner | +1.17 / +2.03 | +1.22 / +0.74 | +0.78 / +0.15 |
| ext | H outer | +0.17 / −0.12 | +0.23 / +0.02 | +0.38 / +0.16 |
| ext | mouth | +0.14 / −0.26 | +0.06 / −0.04 | +0.18 / +0.23 |
| R-OSSE | V outer | +0.65 / +2.50 | +0.70 / +0.22 | −0.29 / −1.54 |
| R-OSSE | V inner | +0.76 / −0.09 | +1.27 / +0.70 | +0.54 / +1.48 |
| R-OSSE | H outer | +0.85 / +0.23 | +3.05 / +0.48 | +0.73 / +0.32 |
| R-OSSE | mouth | +0.03 / −1.91 | +3.13 / +2.55 | +0.20 / +1.35 |
| biradial | V outer | −0.83 / +2.65 | −1.89 / −2.65 | −1.34 / −2.43 |
| biradial | V inner | +0.27 / +0.99 | −0.68 / −0.91 | −0.79 / −1.22 |
| biradial | H outer | +0.26 / −0.12 | +0.37 / +0.13 | +0.20 / −0.01 |
| biradial | mouth | +0.59 / −2.11 | +2.15 / +2.46 | +0.78 / +1.29 |

Prediction changes are nonlinear in weight: the −10 mm values are not the negatives of this table. For example R-OSSE H outer predicts −1.56° H at −10 mm in band 2, versus +3.05° at +10; with the approximate fixed-box control, +10 falls to +0.76°. This apparent threshold crossing is therefore particularly sensitive to size and outside-distribution input. Full values for both signs and all requested weights, fixed-box controls, and distance checks are in the JSON. The frequencies per band are the stored discrete bins, not continuous band integrals.

The Euclidean distance uses 27 training-standardized descriptors and nearest *unique* training point. The 95th percentile is computed on training-to-other-training nearest-neighbor distances. Base distance / 95th percentile: OSSE **2.952 / 1.055**, GRID **4.622 / 1.659**, GEN-FF **2.578 / 1.311**. All 144 ±weight / box-control cases exceed their respective threshold. The threshold is a diagnostic, not a calibrated confidence interval, and the historical optimizer trajectories are clustered.

## Validity and cross-engine constructions

All 144 perturbed two-plane sample radii remained positive. This is only a weak sanity check: it does not establish throat ring/source identity, full outer envelope, wall gap, non-self-intersection, mesh build or DOF cap. None of the three cross-engine combinations was built or meshed. Full-surface throat and shell metadata, a valid R-OSSE bridge sampler, and the explicit lip-roll operation are prerequisites. No full geometry or acoustic authority is inferred from positive meridian radii.

## Verdict and sibling control

- Success (≥3° intended-axis movement at ≤10 mm, cross-axis < half, plus ≥0.5 residual on two bases): **not demonstrated**. Extrapolation, incompatible two-plane/full-normal representations, missing R-OSSE projection and no validity prevent a pass.
- Failure (no module meets authority on two bases, or all that do are redundant): **not established**, because diagonal and lip cannot be scored and the predicted candidates are out of distribution. The backbone therefore does not move up on this evidence alone.
- The only acoustic nomination route remains a prospective, owner-approved matched solve after full-surface and validity checks. No prospective solves were run.

Cross-engine training excluded all lanes from the base engine. X3's provisional sibling grouping has no group crossing engines, so these predictions also exclude all named siblings; the name-based map still needs seed checks. Non-singleton groups are ext-throat v7/v8; OSSE rrect morph v7/v8; Tritonia v7/v8/v9; biradial CD/smooth; Le Cleac'h iwata CD/smooth; section axial CD/smooth; sp control/moderate/strong; rr reference/pucker moderate/pucker strong; and Klangfilm H/V axis variants. Other current configs are singletons. Full listing: `X3_TRANSFER.md`.

Reproduce with `.venv/Scripts/python.exe scratch/fable_architecture/.x2/authority.py`, `.x2/jacobian.py`, and `.x2/summarize.py`. Inputs and outputs remain under scratch except for read-only stored records and geometry code.
