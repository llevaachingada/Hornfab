# Parameter study (M1, bo-study-v1.1)

- task config: `examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml`
- resolved brief: `native_ath_core_2in_v4` (`e8b911dfc38471196cb46f0a7d85c89f28ca9e6b79f576de70cda92440d57e91`)
- objective v4; band 300.0-8000.0 Hz; f0 1280.0 Hz
- cohort: **200** scored rows, **192** unique geometries, run ids missing: **True**
- catalog native ok rows: **197**, fidelities `{'screen': 192, 'verify': 5}`
- experiment identity: **insufficient_evidence**

## Controls (B2 ledger)

| key | category | resolved | range | evidence |
|---|---|---:|---|---|
| `L_mm` | searched | 260 | 104.0 .. 520.0 (search) | confirmed_active_geometry |
| `a0_deg` | derived | 1.2 | 1.2 .. 1.2 (fixed) | static_source_only |
| `a_deg` | searched | 24.2 | 10.0 .. 80.0 (search) | confirmed_active_geometry |
| `aspect_ratio` | fixed | 1 | 1.0 .. 1.0 (fixed) | static_source_only |
| `exponent` | fixed | 2 | 2.0 .. 2.0 (fixed) | static_source_only |
| `k` | searched | 1 | 0.3 .. 5.0 (search) | confirmed_active_geometry |
| `morph_allow_shrinkage` | fixed | 1 | 1.0 .. 1.0 (fixed) | static_source_only |
| `morph_corner_mm` | conditional | 16.5 | 0.0 .. 80.0 (search) | conditional_active |
| `morph_exponent` | inactive | 4 | 2.0 .. 10.0 (search) | confirmed_inactive_conditional |
| `morph_fixed` | conditional | 0 | 0.0 .. 0.6 (search) | conditional_active |
| `morph_height_mm` | conditional | 397 | 238.2 .. 456.55 (search) | conditional_active |
| `morph_rate` | conditional | 3 | 0.5 .. 8.0 (search) | conditional_active |
| `morph_target` | fixed | 1 | 1.0 .. 1.0 (fixed) | confirmed_active_geometry |
| `morph_width_mm` | conditional | 397 | 238.2 .. 456.55 (search) | conditional_active |
| `n` | conditional | 6.75 | 1.0 .. 10.0 (search) | conditional_active |
| `q` | conditional | 0.996 | 0.9 .. 1.0 (search) | static_source_only |
| `r0_mm` | derived | 25.4 | 25.4 .. 25.4 (fixed) | static_source_only |
| `s` | searched | 0.715 | 0.0 .. 1.5 (search) | confirmed_active_geometry |
| `s1` | conditional | 1.14 | 1.0 .. 1.3 (search) | conditional_active |
| `s2` | conditional | 0.025 | 0.015 .. 0.035 (search) | conditional_active |

## Selected designs

Selection rule: seed = lowest frozen-J scored design; remaining slots = maximin normalized Euclidean spread within the better half (J <= median), ties by lower J then design hash; deterministic

| design | J | cov | rip | di | dislope | distd | flat | diag | depth mm | mouth WxH mm | geometry |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `21acc99ec60b` | 1.5968 | 0.39344 | 0.13598 | 0.4317 | 0.14421 | 0.13898 | 0.23285 | 0.1196 | 405 | 451.35x418.46 | ok |
| `81d9eda48b23` | 3.1066 | 0.50484 | 0.090801 | 0.62762 | 0.88836 | 0.27359 | 0.51887 | 0.20256 | 342.49 | 426.17x389.78 | ok |
| `f22413719d3f` | 2.8096 | 0.75265 | 0.24081 | 0.5583 | 0.47787 | 0.286 | 0.26342 | 0.23057 | 397.16 | 451.89x354.85 | ok |
| `c7abbe0ac3ae` | 3.0364 | 0.63057 | 0.15837 | 0.60365 | 0.070559 | 0.26673 | 0.85633 | 0.45023 | 344.63 | 452.6x395.78 | ok |
| `c74883258768` | 2.7542 | 0.70864 | 0.18438 | 0.4544 | 0.059743 | 0.25144 | 0.84891 | 0.24665 | 425.74 | 456.55x417.12 | ok |

## Evidence

- pilot parity: 197/200 compared, max |dJ| 0
- reconstruction parity: 197/200 compared, max |dJ| 0
- held-out frozen J: R2_oof 0.24838, RMSE 4.2029 vs training-mean baseline 4.9496; passed **True**
- recommendation: **allowed** (heldout_passed)
- effects: **produced**; screening policy **below_policy_descriptive_diagnostic**
- interactions: **produced** (produced)

### Held-out model summary

| output | n | R2 oof | RMSE model | RMSE mean baseline | beats |
|---|---:|---:|---:|---:|---|
| `j` | 200 | 0.24838 | 4.2029 | 4.9496 | True |
| `bw_h_mean_deg` | 200 | 0.78035 | 2.5873 | 5.5629 | True |
| `bw_v_mean_deg` | 200 | 0.74145 | 2.8924 | 5.6835 | True |
| `di_mean_db` | 200 | 0.71827 | 0.42552 | 0.81029 | True |
| `di_slope_db_per_dec` | 200 | 0.39934 | 1.248 | 1.6359 | True |
| `ripple_mean_db` | 200 | 0.73622 | 0.18297 | 0.36628 | True |
| `flatness_db` | 200 | 0.33107 | 0.59692 | 0.7379 | True |
| `spdi_mean_db` | 200 | 0.78736 | 0.2493 | 0.54406 | True |

### Held-out permutation importance (J; R2 loss, not dJ)

| group | mean R2 loss | std | n |
|---|---:|---:|---:|
| `morph_corner_mm, morph_fixed, morph_height_mm, morph_rate, morph_width_mm` | 0.1811 | 0.119 | 50 |
| `L_mm` | 0.1265 | 0.112 | 50 |
| `k` | 0.02046 | 0.0774 | 50 |
| `n, q, s` | 0.01554 | 0.0254 | 50 |
| `s1, s2` | -0.0004401 | 0.0126 | 50 |
| `a_deg` | -0.0004546 | 0.0159 | 50 |

### Interaction diagnostic (finite model nonadditivity)

- status: **produced**; anchors: 20; steps: [0.025, 0.05, 0.1]
- independent-group coverage: **insufficient_evidence**
- step-order stability (Spearman): `{'0.025_vs_0.05': 0.4739999795771008, '0.05_vs_0.1': 0.7186525043454878}`
- interpretation: local MODEL nonadditivity, not a derivative, causal acoustic interaction, fANOVA or p-value.

| pair | status | median abs D @0.05 | supported anchors @0.05 |
|---|---|---:|---:|
| `k, morph_width_mm` | estimable_model_nonadditivity | 0.02816 | 14/14 |
| `morph_rate, morph_width_mm` | unstable_nonadditivity | 0.01762 | 14/14 |
| `L_mm, morph_width_mm` | unstable_nonadditivity | 0.01621 | 14/14 |
| `morph_width_mm, q` | estimable_model_nonadditivity | 0.01514 | 8/8 |
| `k, morph_rate` | estimable_model_nonadditivity | 0.01124 | 20/20 |
| `morph_rate, q` | estimable_model_nonadditivity | 0.01071 | 13/13 |
| `L_mm, morph_rate` | estimable_model_nonadditivity | 0.00994 | 20/20 |
| `morph_fixed, morph_width_mm` | estimable_model_nonadditivity | 0.00777 | 14/14 |
| `L_mm, k` | estimable_model_nonadditivity | 0.00707 | 20/20 |
| `L_mm, q` | estimable_model_nonadditivity | 0.007017 | 13/13 |

## Limitations

- Source-piston caveat: the task uses a 2-inch uniform piston source with f11 ~= 3957 Hz; 300-8000 Hz results above the caveat are geometry comparisons under that excitation, not a universal validity boundary.
- Loading weight is 0.0: no loading, efficiency, distortion or maximum-SPL claims are made.
- No independent experiment identity: run_id/experiment_id are absent on every native row; rows are not five independent groups and design-level folds are not experimental replicates.
- ExtraTrees is discontinuous: permutation importance is held-out R2 loss, never delta-J; interaction D_ij are finite model changes, not physical derivatives or causal acoustic interactions.
- Exact normalized steps 0.025/0.05/0.10 are MODEL diagnostics only; unsupported or boundary-truncated pairs are reported as not_estimable, never clipped.
- Geometry descriptors are a canonical sampled-surface approximation through the installed hornlab_mesher API; they are not production cache keys and not a mesh / BEM convergence proof.
- The cohort is below the protocol's 100-per-group screening policy and historical search sampling is biased; effect curves and interaction rankings are descriptive.
- J is not comparable across objective versions; this report is v4 only and the three replay identities are reported separately.
