# E2 — stored-data local invertibility

2026-11-16; HEAD observed `207f97a29e2f2f31a366da95e882f9b48761ab00`. CPU only. Reproduce with `.venv/Scripts/python.exe scratch/fable_architecture/.e2/brief.py`; output `.e2/brief_results.json`. Earlier exploratory analysis: `E2_LOCAL_INVERTIBILITY.md`.

**Verdict:** the specified failure criterion is triggered for this retrospective minimum-norm inverse: its adjacent-pair geometry predictions are worse than no change. The success metrics for fit and inverse errors are also not met. This closes the proposed proportional-step alternative under the brief's stated decision rule, subject to the representation and identifiability limits below; it does not prove that a physically constrained, regularized corrector cannot converge. No stage-two solves were run.

## Basis and method

All 1,715 stored rows are used to fit eight profile PCA modes plus depth (99.775% profile variance) and six response PCs (93.049% of combined unscaled H/V beamwidth and DI variance). Coordinates are standardized by global standard deviation. Units and scaling affect distances, conditioning and pseudoinverse results. Global PCA deliberately follows the brief, but leaks unsupervised test-distribution information. Whole surfaces, loading and ripple are absent.

For 300 randomly selected centers (seed 2701), fit a no-intercept map to differences from the center on the nearest 40; test on the next 10, with R² relative to their own mean. For 500 separately selected centers, use a held-out nearest target and 40 other neighbors, or a target nearest two or four times the 40th-neighbor radius, and compare the minimum-norm pseudoinverse step with the actual geometry difference. Six zero-distance nearest pairs were excluded, leaving 494 adjacent pairs. Two/four-radius targets are outside the fit set; median actual radius ratios are 2.000 and 4.000. Individual pair inverse error is the geometry norm error divided by actual geometry change norm.

## A — local fit and conditioning

Median held-out R² is **0.558** (25th–75th: 0.231–0.753), below the ≥0.7 success metric but above the <0.4 fit-failure threshold. Median condition number is **48.7** (24.0–240.1; 90th percentile 1,148). Median singular values descending: **5.59, 2.35, 1.37, 0.745, 0.397, 0.112**. Of the 300 neighborhoods, 299 contain at least two lanes among the 50 neighbors; their median R² is 0.559. This does not rule out sibling or warm-start dependence.

An exploratory size check fits a depth-only response difference model on the training neighbors and subtracts its prediction from both test response and full-model prediction. Median residual R² falls to **0.481**. This is not a full refit after regressing out all size features and does not establish size-independent performance.

## B — response controllability

The 6-by-9 fitted maps have six nonzero numerical singular values, but practical weakness depends on scale and tolerance. Using an illustrative 1% of each map's largest singular value, the weakest direction falls below that level in **33%** of neighborhoods, the next weakest in 22%, and the fourth in 5%; the strongest three never do. This is not a prespecified physical controllability threshold. At least four directions exceed it in 95% of fitted neighborhoods, but the ≥4 controllable success metric cannot be established physically from statistical fits.

The weakest fitted response combination varies locally. In the exploratory sample, its median absolute weight on response PC1 is 0.793. PC1 has H/V/DI loading norms 0.528/0.847/0.056: it is dominated by a broad vertical-beamwidth pattern, with H contribution, rather than an identifiable single frequency. It is not proven uncontrollable. The 9-to-6 map necessarily leaves at least three geometry null directions; a response difference alone does not uniquely identify a true geometry change.

## C — retrospective correction

| Pair distance | Median relative geometry error | 25th–75th percentile | Pooled skill vs no change |
|---|---:|---:|---:|
| Nearest distinct | 1.129 | 0.890–1.787 | -0.636 |
| Two radii | 1.109 | 0.909–1.879 | -4.600 |
| Four radii | 1.810 | 1.129–4.648 | -17.973 |

The brief's ≤30% adjacent and ≤50% two-radius success thresholds are not met. Negative skill means pooled squared error exceeds that of a zero geometry update. This criterion tests recovery of the *same historical geometry*, not whether another geometry could produce the target response; the nullspace makes that distinction material. It also does not prove a pseudoinverse step is valid or manufacturable.

## D — other-engine neighbors

Restricting all 40 training and 10 test neighbors to engine groups different from the center gives median held-out R² **0.584** (0.406–0.702), median condition **13.2**, and median singular values **3.19, 2.18, 1.36, 0.876, 0.587, 0.324**. These are generally farther-away neighbors and are evaluated on a different distribution; a better condition number does not show stronger local physical control or extrapolation to an unseen center's engine.

## Limits and sibling map

Profiles are two-plane descriptors, not the full surface; PCA response components omit impedance and ripple and are dominated by degree-valued beamwidth. Clustering, design duplication, optimizer trajectories and sibling lanes can confound local differences with missing geometry. PCA and standardization are global. Results neither demonstrate a real response after a predicted move nor predict Newton convergence. Stage two remains an owner-approval proposal: three reachable targets, five constrained measured steps each, with the brief's 3° coverage criterion.

The full naming-based group map and seed checks for all lanes are in `.e2/sibling_seeds.txt`, generated from stored configs by `.e2/sibling_seeds.py`. Both biradial smooth twins and Le Cleach Iwata AR smooth twins have matching nonempty `seed_params`; the other grouped pairs do not have exact nonempty seed matches. Name-based sibling groups are conservative and warm-start/partial seed lineage was not audited.
