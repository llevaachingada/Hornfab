# Parameter activity ledger

Config: `examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml`  
Resolved brief: `../../briefs/campaign_2026-10-26_v4/native_ath_core_2in_v4.yaml`  
Family: `OSSE` · objective v4 · search d = 14  
Native context; geometry sampled through the installed `hornlab_mesher` API (no mesh/BEM).

## Activity counts

| category | count |
|---|---:|
| searched | 4 |
| fixed | 4 |
| derived | 2 |
| conditional | 9 |
| inactive | 1 |
| unresolved | 0 |

## Controls

| key | category | resolved value | range | predicate | evidence |
|---|---|---:|---|---|---|
| `L_mm` | searched | 260 | 104 .. 520 (search) | always | confirmed_active_geometry |
| `a0_deg` | derived | 1.2 | 1.2 .. 1.2 (fixed) | brief driver exit angle (pinned because throat_angle_policy: pin) | static_source_only |
| `a_deg` | searched | 24.2 | 10 .. 80 (search) | always | confirmed_active_geometry |
| `aspect_ratio` | fixed | 1 | 1 .. 1 (fixed) | always (fixed cross-section aspect) | static_source_only |
| `exponent` | fixed | 2 | 2 .. 2 (fixed) | always (fixed cross-section outline) | static_source_only |
| `k` | searched | 1 | 0.3 .. 5 (search) | always | confirmed_active_geometry |
| `morph_allow_shrinkage` | fixed | 1 | 1 .. 1 (fixed) | morph_target in {1, 2, 3} and the target is smaller than the base mouth extent | static_source_only |
| `morph_corner_mm` | conditional | 16.5 | 0 .. 80 (search) | morph_target == 1  (rounded-rectangle target only) | conditional_active |
| `morph_exponent` | inactive | 4 | 2 .. 10 (search) | morph_target == 3  (superellipse target only) | confirmed_inactive_conditional |
| `morph_fixed` | conditional | 0 | 0 .. 0.6 (search) | morph_target in {1, 2, 3} and t > morph_fixed for some sampled t | conditional_active |
| `morph_height_mm` | conditional | 397 | 238.2 .. 456.55 (search) | morph_target in {1, 2, 3} | conditional_active |
| `morph_rate` | conditional | 3 | 0.5 .. 8 (search) | morph_target in {1, 2, 3} and t > morph_fixed for some sampled t | conditional_active |
| `morph_target` | fixed | 1 | 1 .. 1 (fixed) | always (fixed in this task) | confirmed_active_geometry |
| `morph_width_mm` | conditional | 397 | 238.2 .. 456.55 (search) | morph_target in {1, 2, 3} | conditional_active |
| `n` | conditional | 6.75 | 1 .. 10 (search) | s != 0  (OSSE termination term is skipped when s == 0) | conditional_active |
| `q` | conditional | 0.996 | 0.9 .. 1 (search) | s != 0  (OSSE termination term is skipped when s == 0) | static_source_only |
| `r0_mm` | derived | 25.4 | 25.4 .. 25.4 (fixed) | brief driver exit radius (pinned) | static_source_only |
| `s` | searched | 0.715 | 0 .. 1.5 (search) | always contributes the termination amplitude; s == 0 is a no-op for n/q | confirmed_active_geometry |
| `s1` | conditional | 1.14 | 1 .. 1.3 (search) | s1 != 0 and s2 != 0  (the axial-stretch map is inactive if either is zero) | conditional_active |
| `s2` | conditional | 0.025 | 0.015 .. 0.035 (search) | s1 != 0 and s2 != 0  (the axial-stretch map is inactive if either is zero) | conditional_active |

## Advisory active projection

Version `active-projection-v1`; active d = 13 of 14.

Held fixed while decoding: `morph_exponent` = 4.

## Geometry sampling

API: `hornlab_mesher.config_builder.resolve_geometry` · units: `mm` · resolution 12.0 mm.
Convergence: True (max |Δr| 0.16772851889624008 mm; geometry-sampling convergence only; not mesh, acoustic or BEM convergence).

ATH eligibility: **insufficient evidence** in this B2 audit; S0/R0 own archive counts and comparability.
