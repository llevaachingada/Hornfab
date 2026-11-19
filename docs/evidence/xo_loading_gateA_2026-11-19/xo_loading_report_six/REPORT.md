# XO loading diagnostics (report-only)

Probe frequencies 643, 828, 1065 Hz; reference 2000 Hz; F_X 700 Hz.

| design | Re z @ probes | power_vel rel ref (dB) | on-axis_vel rel ref (dB) | energy ratio | load_raw | driver on-axis rel ref, min/med/max @ 828 |
|---|---|---|---|---|---|---|
| fold_warm_best | 1.39/1.93/1.29 | +1.3/+2.8/+1.0 | -1.6/+1.5/+0.4 | 0.96-1.00 | 0.027 | +0.5/+1.6/+4.1 |
| fold_warm_688f_verify | 1.17/1.79/1.34 | +0.2/+2.3/+1.1 | -2.7/+1.1/+0.7 | 0.98-1.00 | 0.105 | +0.3/+1.3/+3.7 |
| morph_v7 | 1.42/1.80/1.30 | +1.5/+2.5/+1.0 | -2.9/-0.0/-0.2 | 0.95-1.00 | 0.002 | -0.8/+0.1/+2.6 |
| ext_throat_v7_verify | 1.98/1.53/0.68 | +1.8/+1.0/-2.4 | -1.3/-0.5/-2.8 | 0.98-1.00 | 0.000 | -1.0/+0.1/+2.8 |
| tritonia_v9 | 0.29/0.50/0.88 | -6.0/-3.7/-1.2 | -8.3/-4.3/-1.1 | 0.96-1.00 | 0.375 | -3.7/-2.5/-0.4 |
| rosse_rect_cd | 0.19/0.34/0.57 | -7.8/-5.2/-3.0 | -11.0/-6.7/-3.5 | 0.96-1.00 | 0.741 | -6.0/-4.6/-2.2 |

Conventions: see `summary.json` `_conventions`.
