# A9 — separating the corridor's effect from v9's other changes

**Run:** 2026-11-16 23:36 ET, HEAD `207f97a`. Read-only, CPU, no solve. Scripts `.a9/a9.py`,
`.a9/report.py`; records `.a9/records.json`. All **3,414** valid landscape rows scored from stored
responses with parity-exact metrics. Parity check: regenerated v7 equals stored v7 exactly
(maximum difference 0.0 over the 2,595 constant-directivity rows).

## The four scores

| Name | What it is | Changes relative to the previous row |
|---|---|---|
| `v7` | Standard landscape v7 brief, point target 80 × 50 | — |
| `v9_pt` | v9 with a point coverage target (80 H from 700 Hz, 50 V from 1,000 Hz) | Term set only: `di`, `distd`, `diag` no longer weighted; `di_roughness` added; vertical scored from 1,000 Hz |
| `v9_swap` | `v9_pt` with only the coverage term replaced by the corridor's | Coverage: point → corridor (H 60–90, V 40–60) |
| `v9_cor` | v9 in corridor mode | Ripple window: v9 measures ripple inside the corridor width |

Weights and dividers as in `S1_RANGE_SCORING.md`. The corridor is the R3 placeholder.

## Result

| Step | Top 20 kept | Top 100 kept | Rank corr., all rows | Rank corr. within the first score's top 100 |
|---|---|---|---|---|
| `v7` → `v9_pt` (term set) | **6 / 20** | 66 / 100 | 0.974 | 0.441 |
| `v9_pt` → `v9_swap` (corridor coverage only) | **11 / 20** | 73 / 100 | 0.977 | 0.595 |
| `v9_swap` → `v9_cor` (ripple window) | 18 / 20 | 90 / 100 | 0.997 | 0.863 |
| `v7` → `v9_cor` (everything) | 3 / 20 | 60 / 100 | 0.945 | 0.250 |

Leading lanes (best design per lane):

| Score | First | Second | Third | Fourth |
|---|---|---|---|---|
| `v7` | ext_throat_hvlaw 3.10 | osse_rrect_fold_warm 3.62 | osse_rrect_morph_v8 3.92 | osse_rrect_morph_v7 3.99 |
| `v9_pt` | ext_throat_hvlaw 3.55 | osse_rrect_fold_warm 3.73 | osse_rrect_morph_v8 4.02 | osse_rrect_morph_v7 4.22 |
| `v9_swap` | osse_rrect_fold_warm 2.35 | osse_rrect_morph_v7 2.46 | ath_twinray380 2.80 | ext_throat_hvlaw 2.84 |
| `v9_cor` | osse_rrect_fold_warm 1.67 | osse_rrect_morph_v7 1.80 | ath_twinray380 2.14 | ext_throat_hvlaw 2.16 |

## Reading

1. **Both changes are first-order, and they do different things.**
   - The **term-set change alone** removes 14 of the top 20 designs, yet leaves the *order of lanes*
     unchanged. It reshuffles individual designs inside the leading lanes.
   - The **corridor coverage alone** removes a further 9 of 20 and **changes which lane leads**:
     `ext_throat_hvlaw` drops from first to fourth; the two `osse_rrect` lanes take the lead.
   So "which family is best" is decided by the coverage target; "which design within it" is
   sensitive to the secondary terms. R3's statement that the movement is driven by the term set,
   not the corridor, is half right: R3 varied only the corridor's onset, which indeed does little.
2. **Corridor mode nearly switches the ripple term off.** v9 measures ripple inside the corridor's
   width, here 30° in H and 20° in V (about ±15° and ±10°). The median normalised ripple term
   falls from 0.513 to 0.013, about 3 % of its point-mode value. Its effect on the top 20 is small
   (18 of 20 kept) only because ripple was a modest part of the total. If ripple across the
   listening window matters to the owner, corridor mode as implemented does not score it.
3. The coverage term's median falls from 2.05 to 0.17 under the corridor: most of what v7 charges
   as coverage error is distance from the exact 80 × 50 point.

## Limits

- One placeholder corridor and one set of weights. S1 showed top-20 membership is fairly stable to
  ±5° shifts; lane order under other corridors was not re-checked here.
- Historical pool: these are designs searched under v7. A search under the corridor would visit
  different designs.
- Differences smaller than about 0.13–0.17 J are within frequency-sampling error
  (`A4_GRID_INDEPENDENT_SCORE.md`). The lane-order change above is larger than that (0.4–0.5 J).
- No row scores exactly zero coverage error under this corridor.

**Next action enabled.** The owner's scoring decision can be taken in two independent parts:
(a) the coverage target (point, corridor, or ranges plus constancy), which decides the leading
family; (b) the secondary term set and the ripple window, which decide the design within it.
