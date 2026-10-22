# Early-Rejection Replay — Item 4 of BL_LEARNINGS_IMPLEMENTATION.md §2

**Date:** 2026-10-22  
**Method:** offline replay; no GPU job, no solver invocation, no writes to the repo.  
**Script:** `early_rejection_replay.py` (scratchpad only)

---

## 1. Sanity check: J recomputation

Objective J was recomputed for every `ok` row using
`hornlab_search.objective.scalar.objective` (via `metrics_from_json`).

| Run | n\_band | n\_ok | max \|J\_recomp − J\_stored\| |
|---|---|---|---|
| osse\_baseline | 10 | 1405 | 0.00e+00 |
| icw | 10 | 787 | 0.00e+00 |
| freeform\_hv | 10 | 721 | 0.00e+00 |
| throat\_adapter | 6 | 400 | 0.00e+00 |
| freeform\_sculpt | 10 | 399 | 0.00e+00 |

Exact match (floating-point exact) in all runs. The `metrics` blob
round-trips losslessly through JSON.

---

## 2. Setup

**Popsize** (CMA default 4 + floor(3·ln(N)), N = searched bounds):

| Run | N (searched) | popsize (λ) | μ = λ//2 | n\_total (non-cached) | n\_band |
|---|---|---|---|---|---|
| osse\_baseline | 9 | 10 | 5 | 1499 | 10 |
| icw | 6 | 9 | 4 | 799 | 10 |
| freeform\_hv | 3 | 7 | 3 | 721 | 10 |
| throat\_adapter | 5 | 8 | 4 | 399 | 6 |
| freeform\_sculpt | 11 | 11 | 5 | 400\* | 10 |

\*freeform\_sculpt ndjson has 460 total lines (60 cached, 400 non-cached, max n=459);
cached rows are excluded from all counts and from generation membership.

**Coarse-first order (n\_band = 10):** `[0, 9, 5, 3, 6, 2, 4, 7, 8, 1]`  
**Coarse-first order (n\_band = 6):** `[0, 5, 3, 2, 4, 1]`

After K = 4 solved in-band frequencies the solved set is
`{0, 9, 5, 3}` (10-freq case) or `{0, 5, 3, 2}` (6-freq case).

**Lower bound formula:**  
Only `cov`, `rip`, `di`, and `load` terms can be bounded from a subset
(all are means of per-frequency non-negative quantities). `dislope`
(polyfit over the full band) and `flat` (std over the full band) cannot
be bounded — their lower bound is 0.

For K solved in-band indices S, with n = n\_band total in-band frequencies:

```
LB = [w_cov * Σ_{i∈S} cov_i + w_rip * Σ_{i∈S} rip_i
      + w_di * Σ_{i∈S} di_i + w_load * Σ_{i∈S} load_i] / n
```

where `cov_i = ((bw_h_i − tgt_h)² + (bw_v_i − tgt_v)²) / 100`,
`rip_i = ripple_h_i + ripple_v_i`,
`di_i = (di_i − di_tgt)² / 10`,
`load_i = max(0, z_min − z_i)`.

With K = 4, n = 10: LB ≤ (4/10) × true J × (fraction captured by these 4
terms). Because `dislope` and `flat` together carry weight 0.5+0.5 = 1.0 out
of a total weighted sum that is typically dominated by `cov` (weight 1–2)
and `rip` (weight 1–1.5), the effective LB is even looser than the raw 40%
frequency fraction suggests.

**Generation threshold:** generation g uses as its reference the worst J
among the best μ designs of generation g−1. Generation 0 has no threshold
(no rejection possible). If fewer than μ ok rows exist in generation g−1,
no threshold is applied.

---

## 3. Rejection statistics (K = 4, various margins)

Margin definition: reject candidate if `LB > threshold × (1 + margin)`.

| Run | n\_total | margin | n\_rejected | GPU % saved (count) | GPU % saved (time-wtd) |
|---|---|---|---|---|---|
| osse\_baseline | 1499 | 0 % | 4 | 0.2 % | 0.1 % |
| | | 10 % | 2 | 0.1 % | 0.0 % |
| | | 25 % | 1 | 0.0 % | 0.0 % |
| | | 50 % | 1 | 0.0 % | 0.0 % |
| icw | 799 | 0 % | 3 | 0.2 % | 0.3 % |
| | | 10 % | 1 | 0.1 % | 0.1 % |
| | | 25 % | 0 | 0.0 % | 0.0 % |
| | | 50 % | 0 | 0.0 % | 0.0 % |
| freeform\_hv | 721 | 0 % | 0 | 0.0 % | 0.0 % |
| | | 10–50 % | 0 | 0.0 % | 0.0 % |
| throat\_adapter | 399 | 0 % | 0 | 0.0 % | 0.0 % |
| | | 10–50 % | 0 | 0.0 % | 0.0 % |
| freeform\_sculpt | 400 | 0 % | 1 | 0.1 % | 0.2 % |
| | | 10–50 % | 0 | 0.0 % | 0.0 % |

GPU % saved (count) = `n_rejected × (1 − K/n_band) / n_total`.  
GPU % saved (time-weighted) = `Σ_rejected [solve_s × (1 − K/n_band)] / Σ_all solve_s`.

---

## 4. Top-20 safety

**No top-20 design (by objective, distinct design\_hash) was rejected under any margin
tested (0 %, 10 %, 25 %, 50 %) in any run.**

The rule is completely safe in the sense that it never discards a design
that would have entered the final top-20.

---

## 5. K sensitivity at 25 % margin

| Run | K = 3 | K = 4 | K = 6 | n\_total |
|---|---|---|---|---|
| osse\_baseline | 1 | 1 | **8** | 1499 |
| icw | 0 | 0 | **5** | 799 |
| freeform\_hv | 0 | 0 | 0 | 721 |
| throat\_adapter | 0 | 0 | 0 | 399 |
| freeform\_sculpt | 0 | 0 | 1 | 400 |

The rule is essentially useless at K = 3 and K = 4 at 25 % margin.
It first becomes "non-trivially applicable" (more than 1 rejection in the
largest run) at **K = 6** — but even then only 8 out of 1499 rows
(0.53 %) are caught for osse\_baseline, and fewer for all other runs.

---

## 6. Interpretation and limitations

**Why rejection rates are so low.**  
With K = 4 out of n\_band = 10 in-band frequencies, we sum only 40 % of
the per-frequency contributions to the lower bound. Furthermore, the
`dislope` and `flat` terms (combined weight ≥ 1.0 in all runs) contribute
0 to LB regardless of how bad the partial metrics look. As a result, LB is
roughly ≤ 25–35 % of the true J for a typical candidate. The rejection
threshold is near the best J in the previous CMA generation. For LB to
exceed the threshold at 0 % margin the candidate's partial 4-frequency
contributions already have to sum to more than a good design's full J —
this only happens for truly catastrophic (penalty-class) designs, and
those are already caught by the mesh/geometry checks before any solve.

**throat\_adapter** has only 6 in-band frequencies; K = 4 covers 67 % of
them, but still 0 rejections because both `di` (weight 0) and `dislope`
(weight 0) are zero-weighted, and the run converges quickly.

**freeform\_hv** has 3 searched parameters and popsize = 7; the CMA
explores a very narrow design space that converges rapidly, so even the
strictest (0 %) threshold never catches any candidate.

**Practical verdict (no ruling on implementation yet).**  
This replay answers ruling (c): across five runs totalling ~3300
non-cached candidates, the K = 4 rule with a 25 % margin would have
rejected **1–0** candidates per run, saving < 0.1 % of GPU time. No
eventual top-20 design is threatened. The bound is too loose to be
operationally useful at K = 4. At K = 6 the saving rises to ~0.5 % for
the largest run, which is still marginal. The rule would not save
meaningful GPU time under any of the tested configurations.

**What would make the rule useful:**  
- A tighter bound on `flat` and `dislope` (requires full-band data)
- A much larger population / many-objective search where many candidates
  are truly poor
- A different early-rejection signal (e.g. mesh DOF count, on-axis level
  at 2–3 frequencies)

**Stated limitation (mandatory per spec):**  
This replay is static — it evaluates the rejection rule against the
historical trajectory. In a live run, every rejection changes which
designs CMA-ES `tell`s, altering the covariance update and all subsequent
candidates. The numbers above are therefore a conservative lower bound on
savings (a live run might generate more rejectable candidates) and also a
potentially optimistic estimate of quality (the top-20 under the altered
trajectory might differ). The static replay cannot resolve this ambiguity.

---

*Generated offline; no GPU was used; no repo file was modified.*
