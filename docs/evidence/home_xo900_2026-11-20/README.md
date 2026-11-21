# Senior engineering decision — home 900 Hz, 80° H × 50° V

**November 20, 2026 · GO for a small matched BEM study after the GPU and geometry gates · NO-GO for full optimization.**

Keep FAV-001 as the protected reference. The saved responses support 900 Hz as the design crossover and show meaningful differences in loading, pattern and consistency. They leave geometry authority for the new sculptures open. Prioritize R2/R3 for meridian development and K1/K2 for termination. Hold C2 for source and exterior fidelity.

[Verify-sample plots](verify_diagnostics.png) · [All weighted score terms, per-frequency width and lobe diagnostics, and impedance data](replay.json) · [Rechecked source and mesh pairs](sculpted_mesh_check.json)

## 1. Live checkout and queues

The canonical checkout was on `hornfab-all-2026-11-18` at `5c5f6f616023cbc04bc328105894628f62aa96b5` after fetch, eight commits ahead of the pushed integration branch. Local and pushed `main` matched `243136d026c9dcb59015c5d1fd322909c6079e01`. Pushed integration was `08728b5b1e4e3073a3324d54430ffdce9cbecb61`. GitHub reported PR #75 (Klangfilm/rolled h12) and #77 (system foundations) open against integration. The working tree already contained the uncommitted sculpted modules, study tools and prior evidence, plus favorites, GUI and score-registry edits. Those concurrent edits were retained. [PR #75](https://github.com/llevaachingada/Hornfab/pull/75) · [PR #77](https://github.com/llevaachingada/Hornfab/pull/77).

The `fav_crowe` k-attribution, k-home search, compact-900 search and verify jobs completed. The existing `fav8` queue already lists two home-900 search lanes, compact variants and the radial-ridge/beak experiments. At the initial audit, `favA9__core_fav` held the GPU lock (PID 1124). The runner subsequently advanced to `favA9_verify_top3`, with both `fav8__x900` jobs still pending. A9 assumes a different driver exit angle, so its rows require their own interpretation. The `source_sensitivity4` status entry showed zero parsed rows. This pass used saved responses and CPU mesh checks. [Existing favorite queue](../../queue/fav_crowe_2026-11-20.yaml) · [Current favorite queue](../../queue/fav8_2026-11-20.yaml).

## 2. Lock three score identities

| Identity | Envelope (mm) | Crossover and coverage | Use |
|---|---|---|---|
| `room_landscape_80x50_900_hf1440_v11cd` | 600 × 480 × 480 | f0 H/V 900. H corridor 60–90° from 900. V corridor 40–60° from 1,000. CD band 900–8,000 Hz. | Primary repeatable home diagnostic |
| `room_landscape_80x50_900_hf1440_v11cd_staged_exp` | 600 × 480 × 480 | Same loading f0. At 900/1,200/1,500 Hz H maxima 110/100/90°, V maxima 90/75/60°. Original high-band corridors at 1,500 and above. CD band 1,500–8,000 Hz. | Experimental coverage and onset sensitivity |
| `compact500_xo900_80x50_hf1440_v11cd` | 500 × 500 × 500 | Existing compact-900 brief and its established replay settings. | Separate packaging study |

The named primary YAML already existed. Its exact replay agrees with the original CPU rescore script: same loaded target, score architecture, round 18 mm radius, assumed 2° exit, auto cap and freestanding symmetry. Each response has its own physical and score IDs. The mini-cohort comparisons share the resolved brief. The canonical registry was already dirty and was left to its owner. The staged YAML loads via the normal runtime and uses log-frequency interpolation. Its provisional preferred widths also affect preferred-edge ripple sampling where applicable. The separate off-axis smoothness term retains its 2.5–8 kHz band. Production v11 and the primary and compact files remain untouched. [Primary YAML](../../../examples/briefs/home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd.yaml) · [Staged experimental YAML](../../../examples/briefs/home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd_staged_exp.yaml) · [Compact YAML](../../../examples/briefs/compact500_xo900_2026-11-20/compact500_xo900_80x50_hf1440_v11cd.yaml).

## 3. Saved-response ranking and preferred pattern

The home and staged columns are independent replays of the same stored verify responses. Read rankings within columns. Signed and RMS widths use solved bins from 1.5 to 8 kHz, with equal sample weighting.

| Design | Home J | Loading contribution | Staged J | Signed H / V error (°) | RMS H / V error (°) |
|---|---:|---:|---:|---:|---:|
| Crowe-X FAV-001 `4140768780f0` | 2.607618 | 0.853783 | 2.538909 | −8.48 / +9.49 | 9.35 / 9.99 |
| Extended-throat OSSE H/V `e85cdd7c61f6` | 2.774414 | 0 | 2.645677 | −10.51 / +3.78 | 10.81 / 4.55 |
| OSSE morph `0636d3f22d5c` | 2.997050 | 0 | 2.930930 | −18.55 / +2.41 | 19.65 / 3.06 |
| OSSE fold-warm `68001408e339` | 3.215633 | 0 | 3.253759 | −16.80 / +3.42 | 18.41 / 4.30 |
| ATH CORE petal `2683984c802c` | 3.326666 | 0 | 3.190781 | −23.32 / −0.91 | 23.63 / 2.51 |

The 0.166796 J FAV-to-extended separation is a provisional ordering. Rescoring each **same design** on stored screen and verify responses under the primary 900 identity gave paired verify-minus-screen shifts of −0.108, −0.049, −0.359, −0.110 and −0.160 J respectively. The top-two gap moved from about 0.108 to 0.167, and morph and fold changed order. Frequency/angle sampling and discretization effects are bundled in these pairs. They establish sensitivity, with same-grid repeatability still to be measured. The older v10/compact repeatability floors apply to other identities.

FAV's weighted listening-window, DI standard deviation, NACC and off-axis contributions are 0.296/0.282/0.130/0.419 J. Extended throat's are 0.678/0.295/0.303/0.641. FAV pays +0.854 J in loading, partly offsetting the pattern advantage. FAV's coverage term is only 0.007 J despite its −8.48° H / +9.49° V mean offset. The report-only module stores bore-axis-connected −6 dB widths, censored or disconnected-lobe flags, and sustained corridor onset with the adjacent frequency bracket. Sampled H sustained onset was 595 Hz for FAV and 1,549 Hz for extended throat. V was 2,678 and 1,351 Hz respectively. These are sampled width diagnostics with coverage through the last valid band bin. Angular/frequency sampling limits the lobe and onset evidence.

The completed 700 Hz held-mouth experiment changed k and compensated depth. At k=1/2/3/4, weighted loading fell from 2.645 to 1.508/1.039/0.792 while non-load grew from 2.352 to 3.292/4.138/4.812. The completed k-home winner `cd7e60025f70` rescored to **2.604181** on the home-900 verify response, only **0.003437 J** from FAV. It saves 0.526 J in loading and about 0.120 J in flatness, but costs 0.414 J in off-axis smoothness and has 15.17° H RMS error versus FAV's 9.35°. Retain both as different controls. The original compact 60-valid search had 25 envelope refusals. Its two strongest verify results were `746d33134776` 2.809 and `c6f0d22ff2b0` 2.824. They inform compact packaging. [Measured k and compact results](../../research/favorites_2026-11-20/CROWE_X_FAVORITE_RESEARCH.md) · [Five original verify sources](../cd_v11_2026-11-20/VERIFY.md) · [Replay and terms](replay.json).

## 4. Physical interpretation and loading decision

Use three separate acceptance measurements:

- **Horn loading.** Check complex radiation impedance and its variation through the filter skirt and operating band. FaitalPRO specifies a 700 Hz minimum crossover with a minimum 12 dB/octave high-pass, using its LTH142 setup. The 900 Hz target adds frequency margin in that context. The ideal 36 mm source and assumed 2° exit leave out phase-plug velocity variation, output compression and distortion in this custom horn. [HF1440 specification](https://faitalpro.com/en/products/HF_Drivers/product_details/index.php?id=502020185).
- **Standalone directivity.** Near crossover, the closest stored bin is 896.28 Hz and the five finalists span 60.7–66.6° H and 72.9–79.3° V. At 1.55 kHz, some are near 50° V while FAV is still around 65°. A scoped Keele Bi-Radial estimate using 25,000/(0.9 × full angle × frequency) gives about 386 mm H and 617 mm V at 900 Hz. The 480 mm V constraint motivates a broader lower-band corridor. It does not establish what these OSSE, R-OSSE or sculpted surfaces can achieve. A wider H radiation target generally motivates a more open H flare. Low-frequency control of the narrower V target can call for a larger effective V aperture. Neither relationship fixes the ordering of axial reach or the return. [Keele sizing claim and scope](../../knowledge/claims/KH-001_keele_mouth_heuristic.md) · [Batík OS-SE and rollback](https://at-horns.eu/osse.html).
- **Assembled system.** Evaluate the selected woofer's actual radiation, centre-to-centre spacing, horn and woofer complex responses, filters/delay, rear or baffle boundary, and 900 Hz vertical lobe. Use measured horizontal, vertical and spatially averaged responses on the assembled prototype. JBL describes matching its M2 waveguide to its own woofer at 800 Hz. The prior HornFab compact study likewise shows why system coverage around crossover deserves a separate decision. [JBL M2](https://jblpro.com/en-US/products/m2.html) · [Dong, Doc and Félix on finite enclosures](https://pubs.aip.org/asa/jasa/article-abstract/155/3/2270/3279896/Directivity-of-horns-mounted-in-finite-enclosures) · [CTA-2034-B public scope](https://www.cta.tech/standards/ansicta-2034-b/) · [HornFab compact crossover study](../../research/compact_horn_system_2026-11-19/compact_xo900_identity.md).

The report-only impedance assessment uses stored normalized Re/Im Z and shows measured-bin means, extrema, peak-to-trough range and a threshold onset with sample bracket. Near crossover, 900–2,500 Hz sampled mean Re Z is 0.932 for FAV and 0.841 for extended throat. Their R ranges are 0.516–1.205 and 0.579–1.209. Before 900 Hz the picture changes: extended throat reaches Re Z **3.234 at 681.73 Hz**, fold **1.949 at 781.68 Hz**, morph **1.710 at 896.28 Hz**. Linear acoustic impedance alone does not predict audible ringing, motor stress or transfer efficiency. Confirm the peaks at more frequencies and combine with the actual driver/filter model.

Two report-only sensitivities illustrate why to keep J stable. A provisional upper-tail limit Re Z=1.5 using p95 in 900–2,500 Hz changes none of the five scores. Using the peak instead over 650–2,500 Hz drives extended throat from 2.774 to 8.555, with FAV unchanged. This hypothetical rank reversal depends on an arbitrary threshold and an unfiltered below-XO sample. Log it as a reason to measure and use a filter-aware power/response assessment. Zeroing load makes FAV 1.754 and leaves extended throat at 2.774, quantifying the current loading trade. Keep M2/M4/M5 and off-axis smoothness as complementary axes while evaluating acoustic efficiency and shape separately. [Replay sensitivity and complex traces](replay.json) · [Constant-directivity metrics](https://3d3a.princeton.edu/publications/generalized-metrics-constant-directivity) · [Gu, You and Shen](https://pubmed.ncbi.nlm.nih.gov/40928147/) · [Dong et al.](https://pubmed.ncbi.nlm.nih.gov/33765791/).

## 5. Sculpted geometry and mechanism authority

The study is a CPU fixture pipeline using explicit sheets. The derivatives are outside the current optimizer and lack stored BEM responses. References remain immutable. This review verified actual saved 6 epw mesh hashes and compared source triangle connectivity under a nearest-node map. Connectivity parity and submicron geometric drift support a controlled experiment. They leave the acoustic numerical residual to be measured.

| Contrast | Verified physical change and admission status |
|---|---|
| R0 → R2 | Sweep −136.88 mm, and 573.30 × 441.39 × 480.07 → 575.46 × 442.95 × 360.32 mm. Source node drift 0.000140 mm, same mapped source connectivity. R0's legacy entrance and shell also differ. Use as a historical benchmark. R0's saved verify field replays to 2.908808 on home-900. |
| R2 → R3 | Sweep +61.42 mm at fixed projected opening and shared entrance/offset construction. Source drift 0.0000557 mm and same mapped connectivity. Intended first body contrast. |
| K1 → K2 | Same core, finish changes sweep +12.93 mm and mouth 579 × 401 → 571 × 399 mm. Source drift 0.00000681 mm and same mapped connectivity. Tests the complete finish, including its aperture change. |
| C0 → C2 | Sweep +121.27 mm and depth 263.47 → 327.10 mm. Source drift 1.75 mm and changed mapped connectivity despite equal tag-face counts. C2's near-lip outer sample-to-facet gap is 2.596 mm. Hold for source and shell correction. |

R2/R3 and K1/K2 demonstrate geometric authority and no established acoustic result. C0/C2 combine core and termination, so after repairing the actual wall/source pair the smaller causal Crowe sequence is C0/C1 for moderate core change and C0/C3 for a terminal-only control. Repeat C2 if both comparisons motivate it. A V-only throat/core lever has existing evidence on a different lane and should retain a fixed H control. Study V aperture changes only if standalone and two-way evidence show the deficit remains near crossover. Retain 80° as the H preference above transition because high-frequency H narrowing is a measured problem in several candidates. [Original geometry, curvature and shell checkpoint](../sculpted_meridians_2026-11-20/README.md) · [Pair measurements](sculpted_mesh_check.json).

**Radial ridge.** A diagonal-only perturbation is justified as a controlled measurement. Batík's published Tritonia shape combines azimuth-varying opening angle, termination and morph. The local ridge single retunes depth to fit the envelope, so record that confound when the existing run completes. Keep terminal beak and ridge separate until matched balloon improvements and sidewall regressions are known. **Knuckles.** Sprinkle's patent describes a multi-plane horn construction, and JBL presents system integration evidence. Neither establishes transferable knobs or performance on these hosts. Put a localized sidewall feature behind a measured H defect and a smooth, reproducible variant after the core and ridge controls. [Tritonia construction](https://at-horns.eu/tritonia.html) · [Sprinkle patent](https://patents.google.com/patent/US9924249B2/en) · [HornFab ridge research and queued singles](../../research/typologies/FAV_SPLIT_PLANE_PROPOSALS_2026-11-20.md).

## 6. Smallest next implementation and conditional solve budget

Keep the standalone analysis separate from the optimizer. Add one fixed-candidate solver adapter that binds the archived or explicit inner/outer sheet digests to the emitted mesh hash, source boundary fingerprint, solver build, objective brief and observation grid. Prefer reusing existing mesh evaluation and response/score storage. Avoid a silent remesh on a different route. Bind zero controls to the original route. Recheck clearance, normal thickness, fitted lip and exact CAD/mesh parity for any eventual release. The geometry checkpoint has sampled derivatives, topology and VTU parity, with manufacturing STEP still open.

Authorize no duplicate jobs. After the existing GPU owner releases the lane, reconcile completed `fav8` identities and use `HORNLAB_GPU_LOCK=refuse` through the existing runner. Reserve **up to 18 solves**, with admission after each batch:

| Batch | Maximum | Matched work |
|---|---:|---|
| First compare | 6 | R2/R3, K1/K2, and fresh FAV/extended-throat controls only where the common dense observation cannot be reused. |
| Numerical credibility | 6 | Two identical reruns across the most informative pairs or source-control variants, plus both arms of each of two finer-mesh comparisons. |
| Conditional authority | 6 | C0, C1 and C3 after source and shell parity. Reserve two slots for a geometrically matched ridge pair after reviewing queued ridge outputs, and one repeat or finer arm only when its matching control is already available. |

Lock a near-XO frequency set with extra **solved** points from 700–3,000 Hz and anchors at the observed transitions. Predeclare one common mesh/observation, cap, excitation and v11 identity. Use the staged brief only for parallel offline scoring. Report all weighted contributions and raw H/V and diagonal polars, disconnected lobes, full-balloon metrics, on/off-axis spectra, complex impedance and phase. Add a separate 8–16 kHz assessment only with suitable mesh resolution and paired source curvature, using an uncontaminated cache. Saved source sensitivity showed the danger of pre-fix cap cache entries. Compare each control's change with both repeat and mesh resolution, and keep the existing search bounds frozen until a real acoustic lever is demonstrated. [Source-cap evidence](../ripple_program_2026-11-20/README.md).

**Decision:** 900 Hz home scoring is reproducible and FAV-001 remains the protected directivity benchmark. The staged brief is useful for sensitivity analysis. The main optimization campaign remains **NO-GO** pending a reproducible acoustic gain or useful trade-off beyond matched numerical variation, followed by the 900 Hz woofer/enclosure comparison.

## Reproduce

```powershell
.venv\Scripts\python.exe tools/analysis/home_900_review.py --out docs/evidence/home_xo900_2026-11-20/replay.json --plot docs/evidence/home_xo900_2026-11-20/verify_diagnostics.png
.venv\Scripts\python.exe -m pytest tests/test_preferred_pattern_report.py tests/test_obj_replay.py tests/test_objective_v11.py tests/test_target_profile.py -q -s -p no:cacheprovider -o addopts=
```

```text
4140768780f0 home900=2.607618 staged=2.538909 delta_verify_minus_screen=-0.108077
e85cdd7c61f6 home900=2.774414 staged=2.645677 delta_verify_minus_screen=-0.049230
0636d3f22d5c home900=2.997050 staged=2.930930 delta_verify_minus_screen=-0.359437
68001408e339 home900=3.215633 staged=3.253759 delta_verify_minus_screen=-0.110437
2683984c802c home900=3.326666 staged=3.190781 delta_verify_minus_screen=-0.159680
cd7e60025f70 supplemental_home900=2.604181
823dc1721a76 supplemental_home900=2.908808
48 passed in 4.04s
```
