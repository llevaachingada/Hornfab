# Std conventions in the objective terms (WP 0.8, 2026-11-17)

Documentation only. No math was changed; historical J values are immutable.

| Term | Where | Residual | Std |
|---|---|---|---|
| `flat` | `metrics/smoothness.py` `band_flatness_detrended_db` (called by `objective/scalar_v2.py` `_v2_flat_value`) | on-axis dB minus a straight line vs log2 f | **sample, `ddof=2`** (two fitted parameters) |
| `flat_cv` | `objective/scalar_v7.py` `_flat_cv_term` (reused by v8 and v9) | unit-velocity level minus a line vs log2 f, F_X..3000 Hz | **population, `ddof=0`** |
| `di_roughness` | `objective/scalar_v9.py` | DI minus a line vs log10 f | population, `ddof=0` |
| `distd` | `objective/scalar_v4.py`, `scalar_v9.py` | the `good` DI-deviation array (see source) | population, `ddof=0` |

Consequence: the two flatness terms are not on one scale. For N points the sample value is larger
by `sqrt(N / (N - 2))`, so a `flat` weight and a `flat_cv` weight of equal size do not weight equal
roughness. Anything that compares or combines them (weights review, replay, surrogate features) must
use the term as stored, never recompute it with a different `ddof`. A future objective version may
unify them under a new objective version number; v7, v8 and v9 stay as they are.

Also recorded here (WP 0.8): `search.budget_counts` rules are in `reference/SEARCH_CONFIG_KEYS.md`;
the `mode` design-key overwrite hazard (EVIDENCE_LEDGER E-012) is now guarded in
`design/families.py` `to_mesher_config` and tested in `tests/test_design_recipe_meta.py`.
