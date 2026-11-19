# WP 4.3 B2 authority table + WP 4.4 proposal (Fable, 2026-11-18; R8 host = hl__biradial_es_style_v7)

Predeclared rules applied unchanged: WP 4.2 equivalence (|ΔBW| ≤ 1° per band, both planes) had to
pass first — it did (see `../wp42_u3_biradial/equivalence.json`, pass: true). WP 4.3 authority:
≥ 3 deg in the INTENDED plane within one band, other plane < half. All solves verify tier, same v7
brief/target, same identity → J comparable within this table only. Source:
`authority.json` (+ hv_beamwidth CSV sets beside it), tool `tools/analysis/u3_authority.py`.

| variant (what it changes) | J (verify) | dJ vs control | max band move | authority | via |
|---|---|---|---|---|---|
| **vt_460** (V terminal/mouth width) | 8.80404 | +2.3046 | **+32.32° V** (1100-2500) | **YES (V plane)** | 1100-2500 V +32.32 (also 700-1100 H −5.10, V secondary < half) |
| term_topbottom (terminal top/bottom shift) | 6.33518 | −0.16425 | 2.66° | no | — |
| steer_early | 6.44034 | −0.05909 | 2.42° | no | — |
| steer_late | 6.50368 | +0.00425 | 1.55° | no | — |
| diag_pull | 6.58741 | +0.08798 | 2.05° | no | — |
| control (record route, unedited record) | 6.49943 | — | — | — | — |

Notes [measured]:
- vt_460's authority is a REAL, large freedom — 32° of V-coverage motion in the 1.1-2.5 kHz band
  with the H plane moving −5.1° (< half) — but it COSTS +2.30 J at this fixed design (the wider
  V mouth breaks the v7 flat/coverage cost at this shape). Authority ≠ a better design: it proves
  the knob moves the acoustic response; the search decides whether it can be spent profitably.
- The four other freedoms are INERT in this envelope (all max moves < 3°) — WP 4.4 records them
  as inert rather than proposing builds.
- vt_480 and term_sides were excluded BEFORE any solve by the u3_jobs validity table (invalid
  reach); they are not authority rows. An owner-approved dedicated probe could still measure them.
- The stored row J identity vs verify-tier J: v7 floor 0.13 J published; verify tier is a denser
  frequency grid, so the J here is compareable ONLY inside this table (same tier).

## WP 4.4 proposal (only for the passing freedom; senior review + owner approval required)

**Proposal — open the V terminal-width freedom on the biradial lane (`vt`) as a searched knob.**
Rationale: the vt knob has demonstrated 3×-threshold authority in its intended plane (V, mid band),
which the fixed-value variants could only hint at. Form: a NEW config version
(`hl__biradial_es_style_v7__vt_v1` per the never-retrofit rule), `bounds: vt_mm in [~440, ~465]`
(bracketing the authoritative 460 and the invalid 480), sigma0 per the R19 default ladder, verified
against the 480 mm depth box with shape_check before any GPU, then a budget-80 CMA probe on the v7
brief; the J reference is the v7-lane stored best (6.3364 screen / 6.4994 verify control). Success
criterion: beat the control by more than the v7 combined floor (0.1302 J) at screen tier.
Owner decisions needed: bounds consent and one CMA slot (B6-adjacent).
