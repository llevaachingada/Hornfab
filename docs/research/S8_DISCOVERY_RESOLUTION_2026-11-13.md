# S8 discovery decisions and use

S8 is offline experiment preparation. It does not schedule a search, change an optimizer,
establish a new horn family, or claim an acoustic improvement. MEH remains paused.

## Decisions

- Geometry coordinates come solely from a `Design` and the existing geometry implementation.
  Absolute dimensions remain alongside dimensionless ratios. A larger copy of a horn has
  different behavior at a fixed frequency even when its normalized shape is identical.
  Opening areas describe projected geometric apertures, not spherical wavefront areas.
- Behavioral coordinates have their own measured-metric and frequency-band context.
  Scores cannot enter geometric novelty. PCA and k-means are reproducible navigation views;
  their labels and distances are not evidence of acoustic similarity or causal effects.
- QD coverage and Pareto trade-offs answer different questions. Compare their physical
  results under one scoring context and physical specification, matched cost limits and
  predeclared seeds. Retain failure/training/verification expense. Archive admission uses
  the production complete-outcome policy, with failures excluded from both archives.
- Hypervolume uses two explicitly oriented physical axes and a reference frozen in the
  input manifest. Never derive the reference from the observed front or pool objective
  versions. Out-of-reference points are reported rather than extending the reference.
- Hypothesis cards reconstruct two source-backed parents and six required experiment roles:
  parent A, parent B, combination, removal of A's feature, removal of B's feature, broad
  control. Expected band/trade-off, unknowns, construction configs, constraints and file
  digests are retained in JSON and Markdown. Schema validation is not mesh feasibility.

## S7 decision

Keep `surrogate/capability.py` restricted to the legacy surrogate's actual scoring capability.
It cannot synthesize measured impedance or missing response/target/tolerance inputs for v4.
The explicit `surrogate_validation.py --advisory-stored-j` mode can learn *stored complete*
v4 labels under an advisory contract requiring a common scoring-context identity (objective implementation,
brief, weights, tolerances and metric definitions), physical task/spec and completeness.
`objective/replay.py`'s `score_id` also includes `metric_id` and physical data: it is a
per-result provenance ID, **not** the common identity to require equal across designs.
Preserve it per row and compare the separately frozen scoring context. Widening the production
capability flag does not implement that contract. The S7 tool and tests from `pr55-local`
were brought into the canonical checkout and extended in this pass; its other PR55 files
have not been merged. Stored-label completeness evidence is checked as supplied, without
reconstructing raw arrays; no new v4 scoring capability or measured accuracy is implied.

## Research basis

| Source | Implementation consequence |
| --- | --- |
| [Keele, low-frequency horn mouth design](https://aes.org/publications/elibrary/elibrary-page/?id=1693) | Preserve physical mouth scale and explicitly distinguish geometry from response. |
| [pyribs CMA-MAE tutorial](https://docs.pyribs.org/en/stable/tutorials/cma_mae.html) | Result archive retains best encountered elites independently of annealing thresholds; fixed measure ranges and the existing F1 archive policy remain authoritative. |
| [Ishibuchi et al., hypervolume reference points](https://ci-labo-omu.github.io/assets/paper/pdf_file/multiobjective/ecj_gecco2017_hv.pdf) | Freeze reference, axis direction and units before comparison. |
| [ZDT1 reference problem](https://sop.tik.ee.ethz.ch/download/supplementary/testproblems/zdt1/index.html) | Known-front synthetic regression exercises nondominance and rectangle-sum hypervolume. |
| [Jolliffe and Cadima, PCA review](https://pubmed.ncbi.nlm.nih.gov/26953178/) | Data-dependent components are labelled navigation only. |

The hypothesis/ablation policy is our experimental-design inference, aligned with the existing
research plan; it is not a published loudspeaker performance standard. Actual acoustic adoption
still requires normal evaluator screening, independent verification and a prospective cost comparison.

## Interfaces

Read module CLI help for `geometry_descriptors.py`, `qd_compare.py` and `hypothesis_cards.py`.
Each writes JSON and Markdown beneath `--out`; use `scratch/<date>_s8/`. Input manifests are
explicit analysis contracts. Missing evidence produces a refusal instead of inferred compatibility.
No live runs, dataset, cache, queue or installed dependency is edited.
