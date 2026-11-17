# -*- coding: utf-8 -*-
"""Section 8 power calc: independent runs needed to detect a 5/10/20% best-J improvement
given the measured seed spread (26% relative SD from the 26-seed group).

Analytic only (no repo data). Two-sample, equal-n test, two-sided alpha=0.05, power 0.80.
Normal-approximation sample size:  n = 2*(z_alpha/2 + z_power)^2 * (sigma/delta)^2
(the standard formula, accurate to within one or two runs of the exact noncentral-t
value at these effect sizes).
"""
from scipy import stats

za = stats.norm.ppf(1 - 0.05 / 2)
zb = stats.norm.ppf(0.80)
print(f"z_(alpha/2)={za:.4f}, z_(power)={zb:.4f}; n = 2*(za+zb)^2*(sd/delta)^2")
for spread in (0.26, 0.59):
    for delta in (0.05, 0.10, 0.20):
        n = 2.0 * (za + zb) ** 2 * (spread / delta) ** 2
        print(f"  spread={spread:.2f} delta={delta:.2f}: n={n:8.0f} per group "
              f"(effect size d={delta / spread:.3f})")
