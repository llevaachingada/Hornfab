# Offline objective evidence

Diagnostic leave-term-out scores are not approved objectives or new solves. Original terms are normalized; ablations multiply by the recorded weights. Response checks recompute the original objective through the current code.

| Config/run | Stored best | Omit slope | Omit diagonal | Omit DI priors+diagonal | Original winner slope dB/dec (dB/oct) |
|---|---:|---:|---:|---:|---:|
| hl__ext_throat_hvlaw_v7 / d3a1bb | 3.1028 | 3.0676 | 2.7880 | 2.0034 | 0.415 (0.125) |
| hl__ext_throat_hvlaw_v7 / d1ebf6 | 3.9678 | 3.3648 | 3.5003 | 1.8950 | -0.326 (-0.098) |
| hl__ath_core_petal_hvlaw_v7 / a504f6 | 5.3218 | 5.0112 | 4.4295 | 2.5603 | 1.672 (0.503) |
| hl__osse_rrect_morph_v7 / 07bea2 | 3.9918 | 3.4517 | 3.5709 | 2.4202 | 2.205 (0.664) |
| hl__es_style_rollback_v7 / 1b1b6e | 20.8551 | 12.2052 | 16.1114 | 5.4450 | 8.788 (2.645) |
| hl__lecleach_iwata_ar_landscape_v7 / e31b23 | 19.4184 | 11.6577 | 15.5218 | 5.5556 | 8.357 (2.516) |
| rr__reference_v7 / d4a7c4 | 29.4230 | 18.4560 | 20.6176 | 7.4996 | 9.706 (2.922) |
| rr__pucker_hv_moderate_v7 / f94955 | 28.4341 | 17.2691 | 20.0352 | 6.7972 | 9.577 (2.883) |
| rr__pucker_hv_strong_v7 / 4d8a33 | 27.4071 | 16.9343 | 19.3626 | 6.7966 | 9.347 (2.814) |
| rr__crowe_panel_es600_v7 / d66ffb | 22.7563 | 14.0869 | 17.4861 | 6.5610 | 8.833 (2.659) |
| sp__control_v7 / 0f2ab5 | 22.7652 | 14.1145 | 17.5675 | 6.5547 | 8.824 (2.656) |
| sp__moderate_v7 / 1e22a5 | 22.9382 | 14.3057 | 17.6545 | 6.5981 | 8.811 (2.653) |
| sp__strong_v7 / 35c541 | 23.7944 | 14.6796 | 18.3854 | 6.8730 | 9.018 (2.715) |
| rr__crowe_panel_es600_v7 / bf9fc8 | 22.5418 | 13.9307 | 17.4861 | 6.5096 | 8.802 (2.650) |
| hl__crowe_panel_home_v7 / 32f7c4 | 16.9182 | 9.5142 | 12.9947 | 3.8845 | 8.163 (2.457) |
| hl__crowe_panel_home_v7 / c35ad4 | 17.0615 | 9.5662 | 13.2722 | 3.9518 | 8.213 (2.472) |

Full numeric evidence, actual fit bands, winner changes, response SHA256 and source conventions: objective_ablation.json. No fabricated 700 Hz sample is added; actual score-band endpoints are recorded.

Synthetic checks:
```json
{
  "reference_round_deg": 65.0,
  "models": [
    {
      "contour_power": 2,
      "true_diagonal_deg": 59.92082242941692,
      "round_reference_raw_error": 0.5159608958702843,
      "note": "Same80x50 H/V crossings; model choice is illustrative, not a new target."
    },
    {
      "contour_power": 4,
      "true_diagonal_deg": 65.6124379846107,
      "round_reference_raw_error": 0.007501605699880156,
      "note": "Same80x50 H/V crossings; model choice is illustrative, not a new target."
    },
    {
      "contour_power": 8,
      "true_diagonal_deg": 66.74679828215936,
      "round_reference_raw_error": 0.06102608477109788,
      "note": "Same80x50 H/V crossings; model choice is illustrative, not a new target."
    },
    {
      "contour_power": 32,
      "true_diagonal_deg": 66.8063974572156,
      "round_reference_raw_error": 0.06526143546869939,
      "note": "Same80x50 H/V crossings; model choice is illustrative, not a new target."
    }
  ],
  "estimator_checks": [
    {
      "theta_phi": [
        17,
        32
      ],
      "estimated_diagonal_deg": [
        58.731096004640655,
        58.731096004640655
      ]
    },
    {
      "theta_phi": [
        23,
        46
      ],
      "estimated_diagonal_deg": [
        59.11405767249167,
        58.96204278733032
      ]
    },
    {
      "theta_phi": [
        45,
        90
      ],
      "estimated_diagonal_deg": [
        59.73560992678061,
        59.73548284536217
      ]
    },
    {
      "theta_phi": [
        91,
        180
      ],
      "estimated_diagonal_deg": [
        59.885849582020086,
        59.88584746434329
      ]
    }
  ],
  "linear_di_checks": [
    {
      "slope_db_per_decade": 0,
      "std_di_db": 0.0,
      "std_fit_residual_db": 0.0
    },
    {
      "slope_db_per_decade": 5,
      "std_di_db": 1.6494347431485028,
      "std_fit_residual_db": 1.6282872879512866e-15
    },
    {
      "slope_db_per_decade": 8.6,
      "std_di_db": 2.8370277582154246,
      "std_fit_residual_db": 2.0722911780555665e-15
    }
  ],
  "gaussian_target_di_80x50_db": 13.079574383820045
}
```
