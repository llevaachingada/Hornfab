# Fixed-angle spectral ripple audit (report-only)

REPORT-ONLY diagnostic: **never a score term**. Reads stored responses; zero solver calls. `detrend spread` = max-min of the fixed-angle RMS over the requested detrend orders.

Band 1065-4832.5 Hz; detrend orders [1, 2, 3]; V angles [25.0, 35.0]; wide [20.0, 30.0, 40.0, 45.0].

`J` is printed for context only. It is NEVER compared or ranked across objective versions. A rank column is present only when every row shares one objective version.

`rip(term)` is the objective's own weighted `rip` contribution from `best.json` (`terms.rip`), i.e. what `J` actually charged; it is an ANGULAR residual at fixed frequency. `rip(metrics)` is the stored angular `ripple_v_db` mean in band. Neither is directly comparable to the fixed-angle residual.

`(trend)` = residual about the exploratory log2(f) quadratic (order 2); `(band_mean)` = deviation from the in-band mean, the IEC 60268-5 section 20.6 / Klippel AN 40 smoothness definition. Neither is a hearing-weighted score.

| rank | design_hash | family | objective_version | J | rip(term) | rip(metrics) | V+25 (trend) | V+25 (band_mean) | V+35 (trend) | V+35 (band_mean) | V-25 | V-35 | detrend spread | identity_ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ee85bcd2ad67 | FREEFORM | ? | 3.4992 | - | 1.725 | 1.173 | 1.246 | 1.908 | 1.911 | 1.173 | 1.908 | 0.410 | yes |
| 2 | e4d38596e2a8 | FREEFORM | ? | 3.7087 | - | 1.780 | 1.027 | 1.114 | 1.520 | 1.645 | 1.027 | 1.520 | 0.226 | yes |
| 3 | c1d088b8b92f | OSSE | ? | 3.8312 | - | 1.804 | 0.573 | 0.732 | 0.691 | 0.749 | 0.573 | 0.691 | 0.341 | yes |
| 4 | cf716e738ef8 | OSSE | ? | 3.9136 | - | 1.697 | 0.396 | 0.529 | 0.638 | 0.683 | 0.396 | 0.638 | 0.176 | yes |
| 5 | efe4a8959d85 | FREEFORM | ? | 5.0862 | - | 1.703 | 0.325 | 0.340 | 0.446 | 0.698 | 0.325 | 0.446 | 0.155 | yes |
| 6 | 9b5428e6dec8 | FREEFORM | ? | 5.5461 | - | 1.574 | 0.261 | 0.457 | 0.355 | 0.852 | 0.261 | 0.355 | 0.221 | yes |
| 7 | 2979e2d125ce | OSSE | ? | 5.8706 | - | 1.296 | 0.401 | 0.623 | 0.386 | 0.831 | 0.401 | 0.386 | 0.377 | yes |
| 8 | 5381c9cea1ec | FREEFORM | ? | 9.3585 | - | 1.263 | 0.065 | 1.342 | 0.056 | 2.143 | 0.065 | 0.056 | 0.129 | yes |
| 9 | f2054faaa9d4 | FREEFORM | ? | 9.3868 | - | 1.012 | 0.044 | 1.416 | 0.122 | 2.238 | 0.044 | 0.122 | 0.196 | yes |
| 10 | 14e53020adbe | FREEFORM | ? | 11.0940 | - | 2.502 | 0.606 | 2.744 | 2.188 | 3.784 | 0.606 | 2.188 | 0.957 | yes |
