# E1 — response versus score replay

**2026-11-16 22:29 ET. HEAD at start:** `207f97a29e2f2f31a366da95e882f9b48761ab00`. Stored data only, CPU, no solves. **This tests the revised E1 brief's coverage-plus-DI proxy, not full J.** The response model was not twice as fast as the scalar model: the median of lane-median reveals was 10 versus 9.5. Cross-engine recall passed the specified numerical screen for GRID and OSSE but failed completely for GEN-FF. Cross-engine assistance did not deliver the required 20% median reduction. This is evidence against the stipulated proxy-level success criterion, not a full-J or prospective conclusion.

## Method and checks

Recovered descriptors by applying the original `an3.py` mesh-reading descriptor function to all stored valid 18-frequency rows: 3,410 extracted, four incomplete. Ten constant-directivity lanes retained at least 100 rows. Per lane, ten random eight-design initial sets are shared across selectors. ExtraTrees uses 32 trees, minimum leaf 2, seed 0; refit after each batch of eight selections. Scores use the lane's v7 coverage and DI terms, tolerances and weights. Proxy parity versus the corresponding stored weighted terms was within 1.78e-15 across extracted rows. No unrevealed outcomes enter selector fits. Actual order is the historical order after the same eight-design initial set; random has the same start. A hit is within 0.1 proxy units of the best available in that lane.

Every initial set costs all eight reveals even when it contains a hit. The first execution saved the position of a hit within that initial set; `summarize.py` correctly applies a floor of eight to saved counts, and `replay.py` now implements the same floor directly. The table reports corrected counts. This is a finite historical candidate-pool replay; actual CMA generated candidates adaptively in reality, and the replay selectors cannot create new ones. Failed/refused attempts are not charged, so comparisons are in valid-design reveals, not full campaign cost.

| Lane | n | Scalar | Response | Actual order | Random | Other-engine prior | Proxy best in full-J top decile? |
|---|---:|---:|---:|---:|---:|---:|---|
| ath tritonia v8 | 112 | 13.5 | 16 | 31.5 | 37 | 17 | yes |
| ath tritonia v9 | 120 | 8.5 | 8.5 | 28.5 | 8.5 | 8.5 | yes |
| ath twinray v8 | 161 | 20.5 | 21.5 | 116.5 | 50 | 13 | yes |
| biradial v7 | 309 | 8 | 8 | 8 | 8 | 8 | no |
| crowe panel home | 158 | 10.5 | 11.5 | 31 | 16 | 11 | no |
| crowe x osse | 202 | 8.5 | 8.5 | 9 | 8.5 | 8.5 | yes |
| ext throat hvlaw v7 | 137 | 29.5 | 22.5 | 38.5 | 73.5 | 24 | yes |
| osse rrect fold warm | 248 | 8 | 8 | 8 | 8 | 8 | no |
| rosse rect cd | 254 | 8 | 8 | 8 | 8 | 8 | no |
| rr crowe panel es600 | 160 | 14 | 16.5 | 122 | 17 | 21 | yes |
| **Median of lanes** | | **9.5** | **10** | **29.75** | **12.25** | **9.75** | **6/10** |

The proxy-best design is in the full-J top decile in only six of ten lanes. Several lanes have a high concentration of designs within 0.1 of their proxy best, so the eight-design initial budget creates a floor that prevents a twofold reduction. Full-J winners and loading, ripple, flatness, and other terms are not evaluated by the response selector. Direct regenerated-score parity using the standard metrics routine was poor (80 campaign rows: median absolute discrepancy 2.882 J, maximum 8.504 J); a theta-weighted DI correction exactly reproduced all 80, as did stored-metrics replay. The proxy parity check above is independent of that full-response regeneration issue.

## Held-out engine discovery

The prior trains on all available designs from the other engine groups, including other briefs, and uses no rows from the held-out engine. Percentages below are the fraction of the held-out CD group's true proxy-best decile recovered in the indicated prediction rank. The held-out pools include all eligible descriptor rows, not only the ten lanes above.

| Held-out engine | n | Recovered in predicted top 10% | Recovered in predicted top 25% |
|---|---:|---:|---:|
| GEN-FF | 309 | 0.0% | 0.0% |
| GRID | 1,316 | 36.4% | 71.2% |
| OSSE | 970 | 51.5% | 73.2% |

The GEN-FF CD pool is dominated by a single lane; clustered trajectories and unequal lane sizes weight these pooled results. Per-config score settings can affect pooled rankings. The 40%-in-top-25% screen is met for two engines and missed for GEN-FF. This is retrospective ranking of solved designs, not an acoustic discovery or evidence of prospective gains.

## Siblings, verdicts and limitations

X3's provisional name-based sibling map groups versions, smooth twins, sp controls, rr reference/pucker and Klangfilm axis variants. In the expanded data, no such sibling group spans engine groups, so the strictly other-engine training used in Parts B and C already excludes those named siblings; the sibling-excluded numbers are therefore the same. Seed-parameter verification of that map remains outstanding. Part A trains on the target lane alone and has no sibling training data.

- Part A: **not met**. Median response 10 versus scalar 9.5 and actual 29.75; it is not at most half both.
- Part B: **not met**. Median decreases from 10 to 9.75, 2.5%, below 20%.
- Part C: **numerical screen met** in two of three engines; GEN-FF is at zero, below chance. The composite failure criterion requiring both no clear Part A advantage and chance-level Part C is therefore not fully met.
- The earlier synthesis's full-J, one-noise-unit E1 remains **unresolved**. The revised proxy replaces that threshold; neither result should be called a full-J comparison.
- No prospective BEM stage was run. A new pool and owner-approved matched solves would be needed to test selection outside historical trajectories.

Reproduce: `.venv/Scripts/python.exe scratch/fable_architecture/.e1/extract.py`, then `.e1/replay.py`, then `.e1/summarize.py` from the repository root. `results.json` records individual starts; `descriptors.pkl` contains original row metadata and descriptors; `parity.py` checks complete-score replay. Sibling groups and mapping are described in `X3_TRANSFER.md` and `.x3/strict.py`.
