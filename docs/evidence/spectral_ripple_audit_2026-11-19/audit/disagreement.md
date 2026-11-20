# Fixed-angle spectral ripple audit (report-only)

REPORT-ONLY diagnostic: **never a score term**. Reads stored responses; zero solver calls. `detrend spread` = max-min of the fixed-angle RMS over the requested detrend orders.

Band 1065-4832.5 Hz; detrend orders [1, 2, 3]; V angles [25.0, 35.0]; wide [20.0, 30.0, 40.0, 45.0].

`J` is printed for context only. It is NEVER compared or ranked across objective versions. A rank column is present only when every row shares one objective version.

`rip(term)` is the objective's own weighted `rip` contribution from `best.json` (`terms.rip`), i.e. what `J` actually charged; it is an ANGULAR residual at fixed frequency. `rip(metrics)` is the stored angular `ripple_v_db` mean in band. Neither is directly comparable to the fixed-angle residual.

`(trend)` = residual about the exploratory log2(f) quadratic (order 2); `(band_mean)` = deviation from the in-band mean, the IEC 60268-5 section 20.6 / Klippel AN 40 smoothness definition. Neither is a hearing-weighted score.

| rank | design_hash | family | objective_version | J | rip(term) | rip(metrics) | V+25 (trend) | V+25 (band_mean) | V+35 (trend) | V+35 (band_mean) | V-25 | V-35 | detrend spread | identity_ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ee85bcd2ad67 | FREEFORM | v7 | 2.8002 | 0.408 | 1.647 | 1.151 | 1.285 | 1.441 | 1.711 | 1.151 | 1.441 | 0.402 | yes |
| 2 | 15a8c964d592 | FREEFORM | v7 | 2.8412 | 0.429 | 1.648 | 1.292 | 1.392 | 1.538 | 1.790 | 1.292 | 1.538 | 0.327 | yes |
| 3 | cf716e738ef8 | OSSE | v7 | 3.4016 | 0.246 | 1.609 | 0.497 | 0.704 | 0.822 | 0.903 | 0.497 | 0.822 | 0.265 | yes |
| 4 | e4d38596e2a8 | FREEFORM | v7 | 3.5400 | 0.455 | 1.689 | 0.950 | 0.997 | 1.947 | 2.097 | 0.950 | 1.947 | 0.137 | yes |
| 5 | c1d088b8b92f | OSSE | v7 | 3.5655 | 0.269 | 1.717 | 0.601 | 0.793 | 0.774 | 0.914 | 0.601 | 0.774 | 0.369 | yes |
| 6 | 58bde4024d87 | OSSE | v7 | 3.7537 | 0.236 | 1.685 | 0.460 | 0.835 | 0.299 | 0.489 | 0.460 | 0.299 | 0.559 | yes |
| 7 | efe4a8959d85 | FREEFORM | v7 | 4.5596 | 0.098 | 1.664 | 0.382 | 0.482 | 0.596 | 0.853 | 0.382 | 0.596 | 0.132 | yes |
| 8 | febde0373489 | FREEFORM | v7 | 4.8787 | 0.250 | 1.345 | 0.672 | 0.881 | 0.746 | 1.396 | 0.672 | 0.746 | 0.179 | yes |
| 9 | 4d2985321ccf | OSSE | v7 | 4.8925 | 0.222 | 1.365 | 0.779 | 1.011 | 0.831 | 0.920 | 0.779 | 0.831 | 0.480 | yes |
| 10 | 73cf78b059a5 | OSSE | v7 | 5.2889 | 0.197 | 1.434 | 0.431 | 0.474 | 0.257 | 0.641 | 0.431 | 0.257 | 0.210 | yes |
| 11 | 2979e2d125ce | OSSE | v7 | 5.3253 | 0.191 | 1.288 | 0.302 | 0.521 | 0.342 | 0.825 | 0.302 | 0.342 | 0.446 | yes |
| 12 | 9b5428e6dec8 | FREEFORM | v7 | 5.3454 | 0.118 | 1.583 | 0.266 | 0.552 | 0.351 | 0.905 | 0.266 | 0.351 | 0.062 | yes |
| 13 | 0705e7b08d4f | FREEFORM | v7 | 6.3271 | 0.339 | 1.436 | 0.989 | 1.022 | 1.052 | 1.282 | 0.989 | 1.052 | 0.093 | yes |
| 14 | 06a008612260 | FREEFORM | v7 | 6.6711 | 0.089 | 1.437 | 0.490 | 1.418 | 0.610 | 2.190 | 0.490 | 0.610 | 0.237 | yes |
| 15 | 04501fa6edc8 | FREEFORM | v7 | 6.7634 | 0.101 | 1.430 | 0.601 | 1.392 | 0.674 | 2.104 | 0.601 | 0.674 | 0.271 | yes |
| 16 | 3c5dae091e52 | FREEFORM | v7 | 7.9109 | 0.143 | 1.164 | 0.335 | 0.340 | 0.537 | 0.761 | 0.335 | 0.537 | 0.466 | yes |
| 17 | 1dab547b5a86 | FREEFORM | v7 | 8.0363 | 0.032 | 1.398 | 0.053 | 1.483 | 0.051 | 2.352 | 0.053 | 0.051 | 0.214 | yes |
| 18 | 5381c9cea1ec | FREEFORM | v7 | 8.0371 | 0.028 | 1.364 | 0.053 | 1.443 | 0.058 | 2.298 | 0.053 | 0.058 | 0.207 | yes |
| 19 | 7be037ff53c5 | FREEFORM | v7 | 8.3495 | 0.049 | 1.125 | 0.037 | 1.505 | 0.118 | 2.362 | 0.037 | 0.118 | 0.224 | yes |
| 20 | f2054faaa9d4 | FREEFORM | v7 | 8.3930 | 0.049 | 1.125 | 0.038 | 1.505 | 0.117 | 2.363 | 0.038 | 0.117 | 0.224 | yes |
| 21 | 00753b8200ac | FREEFORM | v7 | 10.0200 | 0.352 | 2.514 | 1.215 | 2.817 | 2.092 | 3.883 | 1.215 | 2.092 | 0.554 | yes |
| 22 | 14e53020adbe | FREEFORM | v7 | 10.1563 | 0.391 | 2.541 | 1.090 | 2.750 | 2.247 | 3.917 | 1.090 | 2.247 | 0.551 | yes |
| 23 | 9c39541262aa | FREEFORM | v7 | 19.7063 | 0.015 | 1.314 | 0.073 | 1.592 | 0.097 | 2.405 | 0.073 | 0.097 | 0.066 | yes |
| 24 | 8ba61395b295 | FREEFORM | v7 | 19.7214 | 0.014 | 1.286 | 0.077 | 1.554 | 0.125 | 2.362 | 0.077 | 0.125 | 0.053 | yes |
