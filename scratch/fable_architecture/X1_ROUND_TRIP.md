# X1 — surface round trip: partial CPU study

2026-11-16; HEAD observed `207f97a29e2f2f31a366da95e882f9b48761ab00`. CPU-only; script `.x1/probe.py`. This is **incomplete**, not an acceptance-test result. No meshes or solves were generated.

The first ten distinct valid stored designs with an available `design.json` were selected from each specified lane. Loading the stored design and its run config and resolving an inner grid succeeded for 10/10 each of native azimuthal OSSE, native morph OSSE, generic OSSE rollback rows, rolled family and generated freeform. The outputs have different native sampling resolutions; they are not yet contract-compliant arc-length records. The generic rollback example has 25 × 41 points and so is below the contract's minimum station and azimuth sampling requirements before resampling.

For 10/10 Klangfilm examples the current generic grid path rejected stored bound recipe metadata (`driver`, `implementation_sha256`, `schema`). The saved schema is `klangfilm-lame-v1`, whereas the current canonical family adapter identifies `klangfilm-lame-canonical-v1`. The script did not establish whether another compatible historical adapter can reconstruct them; this observation is **not** an engine failure or evidence the surface cannot be recovered.

Further investigation found the matching-named legacy kernel `_klangfilm_lame_v1.py`. `.x1/legacy_k.py` directly reconstructs 19×65 candidate grids for all ten recipes and repeats them byte-identically (`.x1/legacy_k_results.txt`). This bypasses the saved implementation digest verification and any historical adapter behavior; therefore these candidate grids are not verified reconstructions and are excluded from the acceptance and PCA tables. Their source driver metadata and shell still need verification.

## Sampling and acceptance checks

For the 50 materializable designs, `.x1/probe.py` produces `.x1/<hash>.npz`: 31 azimuth rows by 65 stations with per-row arc-length resampling, inner coordinates and cumulative chord lengths. Interpolation uses measured polar angle at each station: the native morph rows are not uniformly spaced in polar angle. These are **experimental partial records**, not complete contract records; azimuth interpolation can perturb exact throat values, arc length after angular interpolation is approximate, and self-intersection, topology and all required metadata have not been verified. It is unsafe to treat them as production samplers.

| Lane | Surface materialized | Refinement | Mesh agreement | Envelope | Exact metadata | Determinism |
|---|---:|---|---|---|---|---|
| OSSE azimuth | 10/10 | surface-only check below | unknown | unknown | incomplete | 10/10 raw reruns identical |
| OSSE morph | 10/10 | surface-only check below | unknown | unknown | incomplete | 10/10 raw reruns identical |
| Grid rollback | 10/10 | native recipe is fixed resolution | unknown | unknown | incomplete | resolver rerun not tested |
| Rolled | 10/10 | native recipe is fixed resolution | unknown | unknown | incomplete | resolver rerun not tested |
| Klangfilm | 0/10 | unknown | unknown | unknown | incomplete | unknown |
| Freeform | 10/10 | surface-only check below | unknown | unknown | incomplete | 10/10 raw reruns identical |

For native and freeform routes, independently resolve geometry at 10 mm and 5 mm and compare on the same experimental 31×65 grid. Maximum point displacement is under 0.2 mm for all 30 tested; morph results range 0.118–0.198 mm. This is **not** contract test 1: descriptors were not checked and the contract requires simultaneously refining both arc and azimuth sampling. The doubled-grid resampling comparison is identically zero at shared coordinates by construction, not evidence of geometric convergence.

The script also queries stored physical-tag-1 nodes against a 61×129 point cloud and records median and 99th-percentile distances. Those are upper bounds to grid-surface distance, not distances to bilinear patches. A separate `.x1/patch_distance.py` approximates nearest bilinear-patch distances using 12 nearby patch centers and bounded iterative projection, with per-elementary-entity results in `.x1/patch_results.jsonl`. It does not certify a global minimum. All 50 meshes expose just one elementary entity for physical tag 1, so these files do not identify inner wall separately from exterior and closure. Median across the ten per-design median / p99 distances in mm was: OSSE azimuth **0.067 / 5.114**, OSSE morph **0.035 / 6.673**, grid rollback **0.515 / 3.990**, rolled **0.326 / 146.500**, freeform **0.021 / 3.069**. These are distances from the *whole rigid-wall tag* to the inner sampled patch, not inner-wall fit errors. Neither an inner-wall pass nor failure follows. In particular the rolled explicit exterior extends well beyond its acoustic inner wall.

For rolled surfaces only, `.x1/envelope.py` compares the exact-resolver inner-plus-outer sampled point bounding box against the stored mesh bbox after quarter symmetry doubling. All ten width and height discrepancies are within 0.38 mm, but sampled surface depth is 2.92–3.00 mm smaller. The source cap or rear closure may contribute to the stored extent; its identity was not verified. These values **do not** pass the full 1 mm envelope check and do not establish a geometry failure. For other routes, bounding only the sampled inner wall is not a valid shell/envelope test. Exact source-cap, driver, termination, outer shell, mounting, symmetry and topology fields have not been fully assembled and checked against mesher inputs.

## Part C: whole-surface modes

The following are in-sample PCA fits to all 50 experimental sampled grids, using XYZ and RMS Euclidean point deviation in mm; median / worst per lane. This is not a held-out reconstruction test, does not include Klangfilm, and the five-lane sample is much smaller than the earlier two-plane study.

| Lane | 8 modes | 12 modes | 16 modes |
|---|---:|---:|---:|
| OSSE azimuth | 2.183 / 2.952 | 1.122 / 1.581 | 0.702 / 0.814 |
| OSSE morph | 1.528 / 2.417 | 0.833 / 1.355 | 0.529 / 0.720 |
| Grid rollback | 1.629 / 2.472 | 0.790 / 1.477 | 0.481 / 0.767 |
| Rolled | 2.343 / 3.817 | 1.252 / 1.811 | 0.640 / 0.825 |
| Freeform | 1.382 / 2.989 | 0.697 / 1.181 | 0.328 / 0.703 |

The constrained area–aspect–section backbone fit is not implemented; independent per-station section fits would not satisfy its monotone law and termination constraints. Mesher fit error and an evidence-based tolerance revision are unknown. Consequently neither X1 success nor its two-engine failure condition has been evaluated. Continue by verifying historic Klangfilm recipe provenance, preserving exact throat and shell metadata, distinguishing inner and shell mesh surfaces, validating patch-distance minimization and full convergence checks, and fitting the actual constrained backbone.

The provisional sibling map and seed comparisons are in `.e2/sibling_seeds.txt`; those groupings are not used in this route probe. They are naming-based, with exact seed equality checked but warm-start lineage not audited.
