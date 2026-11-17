# X3 — strict cross-engine transfer: partial result

Recorded 2026-11-16T22:23:40.738774-05:00 at HEAD `207f97a29e2f2f31a366da95e882f9b48761ab00`. This is a **partial experiment**, not the complete X3 brief. No solves were run. Source data: 1,715 stored designs, 27 mesh-derived two-plane descriptors, 18 frequencies; 537 OSSE, 1,038 GRID and 140 GEN-FF. The fixed model is 100-tree ExtraTrees, leaf size 2, seed 0, with per-frequency training-set mean as the skill baseline. Skills use frequencies >= 600 Hz and summed squared errors. The archived M4 used 200 trees; exact baseline reproduction is therefore not claimed.

## Split results

Columns are horizontal beamwidth / vertical beamwidth / DI skill. Lane and sibling rows pool held-out predictions, each with a training-only mean baseline. Engine rows show each held-out engine separately.

| Inputs | Split | H | V | DI |
|---|---|---:|---:|---:|
| Size | lane | .558 | .752 | .617 |
| Size | siblings | .486 | .735 | .582 |
| Size | GEN-FF | .288 | .498 | .271 |
| Size | GRID | .127 | .439 | .223 |
| Size | OSSE | .346 | .717 | .493 |
| Profiles | lane | .752 | .871 | .776 |
| Profiles | siblings | .696 | .845 | .720 |
| Profiles | GEN-FF | .527 | .715 | .461 |
| Profiles | GRID | .162 | .506 | .220 |
| Profiles | OSSE | .389 | .703 | .460 |

Median within-lane Spearman for coverage error across 29 lanes with at least 30 designs, using profile predictions: lane .761, sibling .720, engine .489. Coverage error uses the existing asymmetric 80 × 50 coverage proxy (frequencies >= 600 Hz), not complete J. Constant correlations are excluded. Sibling holdout drops skill compared with lane holdout; engine holdout falls much further. Different baseline denominators mean these scores are not directly the same test distribution.

## Size control

A linear size model is fit on each training set only and subtracted from both training and held-out targets; profile-only ExtraTrees predicts training residuals. Skill is relative to zero residual, not the ordinary test-set mean. H / V / DI residual skills: GEN-FF .382 / .122 / .179; GRID .166 / .235 / .164; OSSE −.292 / −.198 / −.106. A size-adjusted contribution appears in some cases, but does not consistently generalize across engines. It does not independently establish that response-space novelty is not a size artefact.

## Local learning curves

Randomly withhold the entire engine from the response prior, then for 10 seeded repetitions fit a local coverage-error model on n local designs and evaluate the remaining designs after holding out 64 for the largest training sample. `plus` adds the out-of-engine prior coverage prediction as one feature. Numbers are median Spearman across held-out designs, not median within-lane correlations; they are exploratory, sampled from existing clustered optimization trajectories, and are not a prospective solve-value estimate.

| Engine | prior n=0 | local n=8 / plus | n=16 local / plus | n=32 local / plus | n=64 local / plus |
|---|---:|---:|---:|---:|---:|
| GEN-FF | −.374 | .415 / .370 | .533 / .553 | .831 / .807 | .841 / .845 |
| GRID | .408 | .733 / .726 | .802 / .809 | .896 / .894 | .922 / .923 |
| OSSE | .471 | .561 / .562 | .714 / .693 | .720 / .712 | .803 / .797 |

No robust benefit approximating 15 local solves is visible; differences are small and inconsistent. A precise solve-equivalent value, and the explicit <5-solve failure criterion, are **not established** by these coarse, non-nested curves.

## Verdict and missing work

- Both-plane skill >= .6 on two engines: **not met for the tested two-plane inputs** (H < .6 for all). Whole-surface and frequency-scaled inputs remain untested.
- Median within-lane rank >= .6: **not met** (.489, 29 lanes).
- Prior worth >= 15 solves: **not demonstrated**; explicit <5 failure not established.
- Residual skill > .2: mixed by target and engine; **not established as a general cross-engine claim**.
- The separate brief's failure criterion requiring both planes < .3 in two engines is **not met** by these tested inputs. The above success failures do not by themselves trigger that particular failure criterion.
- Resistance, ripple, on-axis curves, augmentation with and without leakage control, whole-surface and frequency-scaled descriptors were not executed. The archive has no per-design identity: reconstructing and validating its exact selection against mesh descriptors is required before safely joining extra response curves or scaling copies. X1 whole-surface descriptors were not available in this run. Seed-parameter comparison for sibling map is not yet performed; groups below are conservative provisional name-based groups and could miss related constructions. The strict engine split does not depend on sibling group naming.
- Optional 20-solve prospective BEM test is a proposal requiring owner approval and was not run.

## Provisional sibling map

The map below includes singleton groups. Versions and smooth twins are merged; `sp` and `rr` variants and Klangfilm axis variants are grouped conservatively. Verify seed parameters before treating the sibling results as definitive.

| Group | Lanes |
|---|---|
| hl__ath_core_petal_hvlaw | hl__ath_core_petal_hvlaw_v7 |
| hl__ath_tritonia_landscape | hl__ath_tritonia_landscape_v7, hl__ath_tritonia_landscape_v8, hl__ath_tritonia_landscape_v9 |
| hl__ath_twinray380_landscape | hl__ath_twinray380_landscape_v8 |
| hl__biradial_es_style | hl__biradial_es_style_smooth_v7, hl__biradial_es_style_v7 |
| hl__crowe_panel_home | hl__crowe_panel_home_v7 |
| hl__crowe_x_osse_cd | hl__crowe_x_osse_cd_v7 |
| hl__crowe_x_square | hl__crowe_x_square_v7 |
| hl__es_style_rollback | hl__es_style_rollback_v7 |
| hl__ext_throat_hvlaw | hl__ext_throat_hvlaw_v7, hl__ext_throat_hvlaw_v8 |
| hl__klangfilm_lame_curved | hl__klangfilm_lame_curved_v1 |
| hl__lecleach_hv_landscape | hl__lecleach_hv_landscape_smooth_v7 |
| hl__lecleach_iwata_ar_landscape | hl__lecleach_iwata_ar_landscape_smooth_v7, hl__lecleach_iwata_ar_landscape_v7 |
| hl__osse_rrect_fold_warm | hl__osse_rrect_fold_warm_v7 |
| hl__osse_rrect_morph | hl__osse_rrect_morph_v7, hl__osse_rrect_morph_v8 |
| hl__rolled_es_spiral | hl__rolled_es_spiral_v7 |
| hl__rosse_rect_cd | hl__rosse_rect_cd_v7 |
| klangfilm_hv__axis_variants | klangfilm_hv__a0_exact_incumbent_control, klangfilm_hv__a1_h_only_single_axis, klangfilm_hv__a2_v_only_single_axis |
| rf__rect_radial_wide | rf__rect_radial_wide_v7 |
| rf__section_axial_home | rf__section_axial_home_smooth_v8, rf__section_axial_home_v7 |
| rr__crowe_panel_es600 | rr__crowe_panel_es600_v7 |
| rr__reference_pucker | rr__pucker_hv_moderate_v7, rr__pucker_hv_strong_v7, rr__reference_v7 |
| sp__control_moderate_strong | sp__control_v7, sp__moderate_v7, sp__strong_v7 |

Reproduce with `.venv/Scripts/python.exe scratch/fable_architecture/.x3/strict.py` and `.venv/Scripts/python.exe scratch/fable_architecture/.x3/learning.py`; captured output is `.x3/results.txt` and `.x3/learning.txt`.

## Completion ledger against X3 brief

- **A:** Three split schemes executed for existing inputs; sibling groups are provisional and seed checks remain outstanding. Exact published baseline reproduction remains outstanding.
- **B:** Size and two-plane profiles evaluated. Whole-surface and frequency-scaled inputs omitted.
- **C:** Beamwidth and DI evaluated. Resistance, in-coverage ripple and on-axis response omitted.
- **D:** Training-only linear size residualization and held-out evaluation completed for the available targets; alternative size model sensitivity not assessed.
- **E:** Similarity augmentation, including the leakage comparison, omitted.
- **F:** Exploratory held-out-engine learning curves completed; solve-equivalent value and within-lane learning curves remain unquantified.

Overall X3 is incomplete; no overall pass or failure is claimed.

## Follow-up: response targets, similarity augmentation and seed audit

These additions supersede the earlier statements that Parts C and E had not been attempted; the overall experiment remains incomplete. The E1 extraction `.e1/descriptors.pkl` re-ran the original 27-number mesh descriptor on 3,410 rows and retained run and design hash. Exact `(config, descriptor, 54-response)` matching found all 1,715 archive records: 1,675 have one run match, 38 have two, and two have three; each maps to exactly one design hash. All 1,715 joined to finite 18-point stored metrics without exclusions. There are 13 repeated design hashes; a fold removes every identical hash from training when any copy is in test. All source rows use the same 18-frequency grid.

### Part C: expanded targets

Stored `metrics.json` supplies Re(throat impedance), H/V in-coverage ripple, and on-axis SPL. These are actual archived metrics, not surrogate-generated acoustics. ExtraTrees uses 60 trees and the same split definition and scoring band >=600 Hz as above; its 7-output-curve multi-target fit differs from the earlier 3-curve 100-tree model. Curves are 18 points each; pooled skill uses the per-fold training-frequency mean baseline.

| Input | Split | H BW | V BW | DI | Re Z | H ripple | V ripple | On-axis |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Size | lane pooled | .551 | .747 | .611 | .328 | .514 | .423 | .462 |
| Size | sibling pooled | .490 | .733 | .582 | .243 | .445 | .374 | .401 |
| Size | GEN-FF held out | .288 | .492 | .265 | .524 | .292 | −.169 | .332 |
| Size | GRID held out | .136 | .440 | .233 | −.654 | −.079 | −.943 | −.003 |
| Size | OSSE held out | .332 | .713 | .489 | −.346 | .184 | .220 | .078 |
| Profiles | lane pooled | .751 | .871 | .774 | .732 | .692 | .629 | .762 |
| Profiles | sibling pooled | .689 | .847 | .716 | .651 | .600 | .517 | .685 |
| Profiles | GEN-FF held out | .524 | .722 | .467 | .741 | .463 | −.474 | .466 |
| Profiles | GRID held out | .170 | .501 | .212 | .089 | −.299 | −.800 | .260 |
| Profiles | OSSE held out | .369 | .694 | .447 | −.018 | .201 | .303 | .213 |

Thus Re Z transfers well for held-out GEN-FF but not GRID or OSSE; held-out GRID ripple is worse than the training-mean baseline. These are pooled frequency-point skills, not individual-frequency guarantees. Sibling results remain provisional pending complete construction/seed reconciliation.

### Part E: training-only similarity augmentation

A separate frequency-conditioned ExtraTrees model predicts H BW, V BW and DI simultaneously from the 27 physical lengths and log frequency. Its baseline and augmented version use the identical model (40 trees, leaf 3), original held-out designs and per-frequency training-mean denominator. Training-only copies at scales .8, .9, 1.1 and 1.25 multiply lengths by the scale and divide frequency by it. Only source frequencies <=4,000 Hz enter each copy, excluding its top octave. Held-out hashes are removed from training before making any copies. The driver/throat scaling caveat applies, and physical similarity here is an assumption of the construction, not a newly solved acoustic result.

| Held-out engine | Baseline H / V / DI | Augmented H / V / DI |
|---|---|---|
| GEN-FF | .490 / .674 / .341 | .527 / .700 / .378 |
| GRID | .257 / .587 / .354 | .313 / .631 / .528 |
| OSSE | .459 / .755 / .508 | .481 / .789 / .531 |

Augmentation improved all three aggregated skills in this fixed retrospective test. It still does not meet the >=.6 H and V criterion for two engines. A deliberately leaky train-copy test was **not run**: the hard rule forbids evaluating on a scaled copy of a training design, so the requested with-leakage comparison cannot be reported. Nor does this show prospective benefit with a matched physical driver. The frequency-conditioned model changes the input representation and training sample count versus Part B; compare augmentation only with its paired baseline.

### Sibling seed check

`.x3/seeds.json` records pairwise seed differences for the first observed config in each provisional group. The Le Cléac'h Iwata smooth/non-smooth pair has exactly matching `seed_params`; the other eight multi-lane groups have differences in 2–19 seed fields. These differences do **not** prove different constructions: versions may be reseeded and the named control/moderate/strong and reference/pucker variants intentionally differ. The recorded `grid` blocks compare equal within each group, but empty grid blocks compare equal too; a complete construction and all-run lineage check remains outstanding. For that reason the sibling map remains provisional. Raw check and scripts: `.x3/seeds.py`, `.x3/extended.py`, `.x3/augment.py`; outputs `.x3/seeds.json`, `.x3/extended.txt`, `.x3/augment.txt`.

**Revised completion ledger:** A remains provisional on sibling identification and exact baseline parity; B lacks whole-surface inputs and an explicitly wavelength-multiplied representation; C now covers the requested targets for size and profile inputs; D remains as above; E has a controlled test but no forbidden leaky comparison; F remains exploratory and has no precise local solve-value estimate. No overall X3 pass or failure is claimed.
