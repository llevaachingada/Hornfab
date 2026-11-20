# Fixed-angle spectral ripple audit (report-only)

REPORT-ONLY diagnostic: **never a score term**. Reads stored responses; zero solver calls. `detrend spread` = max-min of the fixed-angle RMS over the requested detrend orders.

Band 1065-4832.5 Hz; detrend orders [1, 2, 3]; V angles [25.0, 35.0]; wide [20.0, 30.0, 40.0, 45.0].

`J` is printed for context only. It is NEVER compared or ranked across objective versions. A rank column is present only when every row shares one objective version.

`rip(term)` is the objective's own weighted `rip` contribution from `best.json` (`terms.rip`), i.e. what `J` actually charged; it is an ANGULAR residual at fixed frequency. `rip(metrics)` is the stored angular `ripple_v_db` mean in band. Neither is directly comparable to the fixed-angle residual.

`(trend)` = residual about the exploratory log2(f) quadratic (order 2); `(band_mean)` = deviation from the in-band mean, the IEC 60268-5 section 20.6 / Klippel AN 40 smoothness definition. Neither is a hearing-weighted score.

| rank | design_hash | family | objective_version | J | rip(term) | rip(metrics) | V+25 (trend) | V+25 (band_mean) | V+35 (trend) | V+35 (band_mean) | V-25 | V-35 | detrend spread | identity_ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ee85bcd2ad67 | FREEFORM | v7 | 2.1492 | 0.426 | 1.662 | 1.104 | 1.188 | 1.313 | 1.679 | 1.104 | 1.313 | 0.226 | yes |
| 2 | ee85bcd2ad67 | FREEFORM | v7 | 2.1509 | 0.427 | 1.662 | 1.104 | 1.188 | 1.313 | 1.678 | 1.104 | 1.313 | 0.226 | yes |
