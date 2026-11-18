# ST260 anchor source check — outcome (local orchestrator, 2026-11-18; D6 step 1 / R4)

Status line: **config corrected; NO admissible measured build; R4 fallback recorded; ST260 not solved.**

## 1. What was checked, with which sources

| Source | How fetched | Key facts |
|---|---|---|
| https://www.at-horns.eu/ST260.html (fetched live) | direct HTTP | ST260: "Free standing axisymmetric OS-SE waveguide w/ roll back", "⌀260 mm x 82 mm / 1\" throat (19° opening angle)"; ST260/B baffle version 83 mm; six linked builds "including acoustic measurements" |
| https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf (via r.jina.ai; direct Cloudflare-blocked) | proxy | Example block p.7: "R=130 mm k=1.8 r0=12.7 mm r=0.3 a0=7.5 deg b=0.3 a=39 deg m=0.8 q=3.7"; "260 mm (~10\") wide and slightly less than 80 mm (~3\") long"; BEM: "free standing with a 5 mm thick wall" |
| https://www.at-horns.eu/release/ST260.zip (fetched live) | direct HTTP | STL/STEP for the device; `ST260-19.stl` (1,507,384 bytes) parsed below; kit + baffle variants also present |

## 2. Device STL parse (`measured/ST260-19.stl`, binary, 30146 triangles)

- axis +x; bbox x 0..83.23 mm, y,z ±130.21 mm → mouth Ø260.4, total solid depth 83.2 mm (page: 82)
- throat radius 12.700 mm at x=0 (matches 1" throat); throat wall slope dr/dx ≈ 0.174 → opening ≈ 19–20° full (page: 19°)
- acoustic bore throat→front rim exit: r 12.70 → 105.78 mm (Ø211.6 at x=83.23); outer rolled lip Ø260.4 at x=63.9
- 65 axial tessellation rings; 4 bolt holes do not perturb the median/axisymmetric profile

## 3. Config correction (committed together with this evidence)

The pinned values were the rev7 **paper example** (a0 7.5, k 1.8, m 0.8, q 3.7). Re-fitting the STL
bore+rim to the same rev7 meridian formulas (`hornlab_mesher.profile_formulas.calculate_rosse_curve`,
scipy `least_squares`, z(r) residual, 6 free params, r0 fixed 12.7):

| Param | Old (rev7 example) | Refit to device | Note |
|---|---|---|---|
| a0_deg | 7.5 | **9.45** | 19° total — agrees with the ST260 page |
| k | 1.8 | **2.13** | |
| m | 0.8 | **0.86** | |
| q | 3.7 | **5.05** | R-OSSE blend exponent |
| r0_mm | 12.7 | 12.7 | unchanged |
| R_mm | 130.0 | 130.0 | weakly identified (R≈133 fits equally well; 130 kept) |
| r, b | 0.3 | 0.3 | unchanged (weakly identified) |
| tmax / wall | 1.0 / 5.0 | unchanged | wall relabelled [published] (rev7 BEM states 5 mm) |

Deviation of old vs STL (matched x, median radial): **RMS 1.33 mm, max 3.46 mm** — fails the
dossier's 0.5 mm meridian rule. Refit curve vs STL: **RMS 0.08 mm, max 0.17 mm** — passes.
The old curve ends its profile at x=57.5 mm/r=130; the device bore continues to x=83.2 mm.

## 4. Admissibility of the six linked measured builds (dossier §4 rule)

None is admissible. Each fails: mounting modelable AND distance stated AND gating stated AND polar
step ≤ 10° — all four required. Direct diyAudio fetch was Cloudflare-blocked; builds were read from
Wayback Machine archived pages (URLs as listed on the ST260 page).

| # | URL (as linked by the author) | Build | Verdict |
|---|---|---|---|
| 1 | .../338806-...-post6737942.html | (page snapshot) | no measurement text retrievable |
| 2 | .../338806-...-post6498359.html | Dkalsi, Peerless DFM-2535R00-08, polars normalised to 10° + raw | fails: no distance/gating stated; drivers "taped together" (mounting not modelable as-is) |
| 3 | .../338806-...-post6500843.html | VituixCAD simulation from traced SPL | **not a measurement** |
| 4 | .../354772-...-post6458832.html | pelanj, B&C DE500 | fails: images only, no distance/gating/step |
| 5 | .../354772-...-post6558650.html | WT, Denovo DNA360, "gated response with 4.6 mS" | fails: gating stated, but no distance, no mounting, no polar step |
| 6 | .../338806-...-post6497649.html | mabat relaying Pet007's three-driver measurements | fails: distance/gating/step unstated; DI "calculated from the front polars only" |

Closest set: #6 and #5 — neither is admissible under the predeclared rule. No REW/text/CSV data
available; only plot attachments. **Recorded for the senior pass:** if either build is later
re-measured properly (or the author publishes data), ST260 returns to anchor candidacy with the
corrected config already in place.

## 5. Consequences (predeclared rule applied unchanged)

- ST260 anchor verdict (STEP 4b): **fail — "not measurable against a published measurement"**;
  the +/-5°/+/-1 dB pass rule stays as written, unscored.
- **R4 fallback route (recorded, not executed this pass):** ATH CORE / Tritonia with published
  config + measured polars (per `OWNER_DECISIONS_RESOLVED_2026-11-18.md` R4 reversal clause).
  Needs its own typology-research dossier + admissibility check before any GPU slot is spent.
- The v7-vs-v10 "which score tracks the measurement" note (STEP 4b) is **deferred** with the anchor.
- The 2 GPU solves approved for the anchor (R4) are **not spent**; they stay available for the
  fallback or B6 at the owner's discretion.