# Tritonia v9 CMA data-building audit — 2026-11-16

The v9 config is a separate experimental identity based on the two Tritonia v8 screen runs below. It retains the vertical fold and its width, the fixed horizontal fold and tilt, the 10 mm corner floor and other v8 hygiene. Relative to the **run snapshots**, `morph_rate` is widened from 1.2–2.1 to 1.0–2.1 and `az_a_cos_amp` from -16–-13.5 to -18–-13.5 degrees. The family parameter description notes that ATH documents morph rates >=1. The current v8 file had already been edited to 0.6–2.1 and -22–-13.5; v9 does not modify it. This modest extension is a new hypothesis, not a published Tritonia formula.

| Source run | Valid / attempts | Seed J | Best J (evaluation) | Top-ten evidence within 3% of original bound |
|---|---:|---:|---:|---|
| `runs/20261116T044917Z-screen-12eb61` | 73 / 74 | 26.903 | 5.692 (62) | morph_rate 3 at low |
| `runs/20261116T054705Z-screen-570bc6` | 39 / 39 | 26.903 | 6.603 (35) | az_a_cos_amp 4 at low |

Counts are screen rows with `ok` and finite objective below the failure penalty; these are not verified finalists. The v9 seed records the first run's best, and `search.warm_start` uses both runs, top 10, with `sigma_from_spread: true`. Warm-start performs its own family, searched-knob and brief checks and records clipping and chosen sigma. The v9 box may clip other historical rows; inspect the resulting warm-start record.

CPU preflight used the project `.venv` interpreter. The 24-sample real-mesher/envelope pass reported `N=24; valid=24 refused=0`, no WARN/HARD findings and `Result: ok`; this sampling pass omitted `--from-runs`. The mesher also printed that one outer-wall clearance request was finer than the 3.573 mm mesh resolution and that its outer shell might chord through the wall; it reported the acoustic inner surface unaffected. This is not a clearance verification for fabrication. The initial history-aware pass at sigma 0.2 warned `low_hits` (2.17 expected versus 3). The initial step was then reduced to 0.18; with both source runs, the repeated check returned `mean J 5.6919; mean hash cf99fdeab801; sigma0 0.18; spread 0.458519; sources 2` and `expected hits 5.68 (min 3)`. Its remaining `no_headroom` warning correctly identifies that the starting seed is the prior optimum; the wider bounds add unexplored territory but do not resolve that warning. The geometry-sampling pass was not repeated because the bounds and seed did not change. CPU preflight does not establish acoustic readiness.

Proposed sequence: two independent CMA seeds, each targeting 120 valid screen rows with `max_attempts: 260` and a two-hour job timeout; build a v9-only cohort and enforce the >=100 usable matched-row gate before any BO. Run an 80-screen BO arm with two finalist verifications only after the gate passes, then assess its results and bounds before another CMA/BO cycle. The distinct v9 name means old v8 rows are not automatically v9 cohort rows. Two searches do not guarantee 240 eligible rows: refusals, duplicates, caching, timeout and cohort identity gates matter.

For these two explicitly data-building jobs the parent has selected `watchdog: false`, because the live runner's pin rule is not separately configurable and otherwise stops at 30 valid rows. This disables the refusal watchdog too. `max_attempts` and timeout bound work, but do not replace a refusal-rate guard; inspect results and abort the campaign if the box is unhealthy. No such exception applies to other jobs.

The v7 objective has a known off-axis-excess blind spot. A lower screen J is not proof of improved isobars; compare actual responses and verify finalists. No GPU solve or acoustic convergence assessment is implied by the CPU preflight.

## Other recent candidates

The following numbers are observations from run-local `search.ndjson` and config snapshots, not comparable rankings across different briefs or objective variants.

| Candidate | Evidence | Disposition |
|---|---|---|
| 80x60 ext-throat core law | Three core-law runs `6d2e52`, `22c213`, `2f40b6` and comparison run `4a6c2b`: best J 3.233 at evaluation 0; valid/attempts were 78/100, 65/101, 65/101 and 47/61 respectively. | Same-box restart offers little evidence of new benefit. |
| Landscape ext-throat H/V | v7 `d3a1bb`: 68/100 valid, 6.827 to 3.103 at 54, six of top ten within 3% of `az_a_cos_pow` low. v8 `cd60f7`: 24/46 valid, best 3.103 at seed. | Owner removed this family from the live queue over published-horn grounding and refusals. Do not reinstate solely on J. |
| OSSE rounded-rect morph | v7 `07bea2`: 75/80 valid, J 8.275 to 3.992. v8 `5d1082`: 32/40 valid, 3.992 to 3.924. | Owner rejected its lower-J isobars; documented v7 scoring misses off-axis excess. Review response and rescoring before additional optimization. |
| OSSE fold warm | `0a228d`: 31/31 valid, 4.289 to 3.762; vertical fold pinned high. Two subsequent runs `ab4fb9` and `f1a263` each 30/30 but retained the 3.762 seed as best. | Do not add another same-box restart solely for improvement. Review pending BO and visual fold identity. |
| TwinRay v8 | `44001e`: 50/52 valid, 11.400 to 5.517; `679c6f`: 30/31 valid, 11.400 to 6.035. Top-ten points cluster at the 8 mm corner hygiene floor and -6 degree vertical-fold limit. | Do not cross the corner floor or remove reference fold based on pinning alone. Existing day queue includes another pass. |
| Bi-radial smooth | `63158a`: 107/107 valid, 6.130 to 5.114 at evaluation 105. | Late improvement supports another short CMA pass, but bridge/list geometry is not encoded by current BO tooling; preserve smooth-brief identity. |
| R-OSSE rectangular CD | `56681d`: 55/55 valid, 9.695 to 4.892 at 29; later `e4c778`: 30/32 valid, 4.891 seed remained best. `0e777a` was still growing when sampled: 14/14, best 4.859. | Enlarged-box day runs are already underway; let them finish and verify. Bridge rows require BO-encoding work first. |
| Crowe-X CD | `620f81`: 64/78 valid, 6.064 to 5.344 at 73; `7fc9b7`: 19/28 valid, 6.064 to 5.691 at 24. | Late progress but material refusals. Day queue already contains a pass; inspect its enlarged bounds and outcomes before adding work. Grid rows are not currently BO-encodable. |
| Rolled ES spiral | Two 30-ish screen runs `b25d61` and `981f59` improved, but the recorded family-admission hold remains distinct from these results. | Do not infer release from low J or successful meshes. Resolve source/objective/acoustic readiness and owner hold. |
