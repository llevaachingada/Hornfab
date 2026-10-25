# Typology grounding dossier — WP9 (G2 splice, G3 throat_blend, G4 spherical_salmon) + WP9b (organic/elliptical, X-shape)

2026-10-25, M4 pass. Produced under the `hornlab-typology-research` protocol (project skill, loaded by the
orchestrator; lane sessions could not load it, so its sections §2/§3/§5/§7 are embedded verbatim in the work-order
dispatches). **Outcome: CITATION of the existing senior-pass research** (skill §2 "inventory before fetch": the
senior-pass research already covers every family in this pass; no new web fetch was made, consistent with the M4
"zero new searches" directive for optimization searches; nothing here fetches anything).

Deliverable per skill §6: this file. INDEX gets a line in the same commit. Validation tests in the WP9/WP9b lanes
cite this dossier's reference case and checkable properties.

## 1. Source table (9b.0-style; status vocabulary from 9b.0)

| Source | What it gives us | Status |
|---|---|---|
| Senior-pass Report 2 §3 (`docs/research/senior_pass_2026-10-24/02_TYPOLOGIES_AND_MULTICELL.md` §3) | The `spherical_salmon` march (equations 1–3, start/stop rules, Δx 0.25 mm, resample via `select_anchors`), its validation gates, and the neutral-name rename gate. | primary/construction, in-repo |
| Senior-pass Report 4 WP9 steps 1–3 (`04_IMPLEMENTATION_PLAN.md` WP9) | `splice` (G2), `throat_blend_mm` (G3), `spherical_salmon` (G4) exact spec: signatures, knobs, tolerances (C1 ≤ 0.5°, Hermite bridge ≤ 2° fallback, bit-for-bit G3 baseline). | primary, in-repo |
| Senior-pass Report 4 §9b.0–9b.5 (same doc) | The family source table (Fourcade 2015 PDF, ETF10 lecture, Kolbrek 2008, Jmmlc diyAudio thread, sphericalhorns.net, audiohorn.net), the T1–T7 constructions with labels, the GRID row-pipeline (9b.3), limits (9b.4), files/tests/bounds (9b.5). | primary, in-repo (source-checked 2026-10-24) |
| Raw appendices A and B + corrections | Practitioner-survey raw text (appendix A §§2, 14, 22.3: JMLC = Salmon law on spherical wavefronts; Salmon T-family; catenoidal = hypex T 0) with the dated corrections table in Report 2 §7 (authoritative where they conflict). | secondary (survey), raw kept byte-for-byte; corrections live in Report 2 §7 |
| NOTES_FOR_SENIOR.md "2026-10-24 (orchestrator, senior pass M4 recon / exp-1)" | The point-grid curl verdict: self-turning profiles build with NO fork-mesher change; BARE mode not BEM-usable; infinite-baffle refuses rollback; freestanding + explicit `outer_points` is the route; the measured caller contract. | measured probe, in-repo |
| Owner ruling 2026-10-25 (pass order) | `lecleach` BLOCKED under R9 (no human-supplied verifiable published construction reference; ETF PDF/threads not usable); organic/elliptical + X-shapes ship as labeled hypothesis-shape experiments; candidate-source findings go to NOTES_FOR_SENIOR.md. | owner directive |

No new claims in this dossier; corrections culture untouched (raw appendices stay byte-for-byte; any future
correction is a dated table in the consuming doc per skill §4).

## 2. Constructions → checkable properties (skill §5; "math → testable properties BEFORE code")

### 2.1 `splice` (G2) — Report 4 WP9 step 1 + Report 2 §2 row G2

Construction: profile_h splice of two parents both built from r0; second parent translated in z so its radius
meets the first's at z_s, matched by wall angle (search θ along the second meridian); C1 Hermite bridge over 10 %
of L only if no match within 2°. Knob `{p}_zs_frac` ∈ [0.2, 0.8].

Checkable properties (ship bar):
- P1 C¹ continuity at the joint: |Δθ| < 0.5° between the matched wall angles of the two parents at z_s.
- P2 both parents built from the same r0 = driver exit radius (WP2-anchored).
- P3 knob determinism: zs_frac → z_s mapping is monotone; bounds not widened.
- P4 an unmatched joint (angle gap > 2°) takes the Hermite bridge and still passes P1 (bridge over 10 % of L).

### 2.2 `throat_blend_mm` (G3) — Report 4 WP9 step 2 (Report 1 F4)

Construction: for conical, exponential, hypex, tractrix: over [0, L_b],
`r = (1−w)·r_OS(z) + w·r_cls(z)` with `w = smoothstep(z/L_b)`; r_OS = the OS meridian with a0 = driver exit and
the classical profile's far-field angle at L_b. Knob `throat_blend_mm`, default 0.

Checkable properties (ship bar):
- P1 DEFAULT 0 reproduces today's bit-for-bit profile on a stored design (regression test).
- P2 blend endpoints: w(0) = 0 ⇒ r(0) = r_OS(0) (throat untouched); at L_b the classical profile continues
  unchanged beyond L_b.
- P3 smoothness: w is C¹ (smoothstep); no kink at either end of [0, L_b].

### 2.3 `spherical_salmon` (G4) — Report 2 §3 march

Construction: spherical-wavefront Salmon march in the apex position x. Wavefront orthogonal to the wall at
(z, r, θ): centre `z_c = z − r/tan θ`, radius `R = r/sin θ`, cap area `A = 2π R²(1 − cos θ)` → π r² as θ → 0.
March, with unknowns (z, r, θ), apex steps x_{i+1} = x_i + Δx:
1. `2π (r/sin θ)² (1 − cos θ) = A(x_{i+1})` (area law, Salmon 1946 applied to wavefront areas)
2. `z − r/tan θ + r/sin θ = z_a0 + x_{i+1}`
3. `r − r_i = tan(½(θ + θ_i)) · (z − z_i)` (trapezoidal wall continuity)
Eliminate z and r via (2) and (3), root-find θ by brentq on [θ_i, max_wall]. Start (0, r0, θ0 = driver exit
angle); stop at max_wall_deg or the envelope; Δx = 0.25 mm; resample to 16–32 FREEFORM anchors with the existing
`select_anchors`. Target signature: `profiles.spherical_salmon(r0_mm, fc_hz, T, theta0_deg, max_wall_deg,
dx_mm=0.25)`. Area law with x0 = c/(2π f_c): `A(x) = A0·[cosh(x/x0) + T·sinh(x/x0)]²`.

Checkable properties (ship bar, Report 2 §3 + WP9 step 3):
- P1 area law satisfied at every step (rel. error < 1e-6).
- P2 z strictly increasing along the march (before/without the rollback of later WP9b work — the FREEFORM
  surface stops at max_wall ≤ 90° for the G4 preset; rollback is the GRID/WP9b route).
- P3 θ monotone non-decreasing.
- P4 plane-wave limit: as θ0 → 0 (small angle) and T → 1 with small fc, the early march approaches plane-wave
  Salmon behavior; cap area → π r² as θ → 0 (reported as a limit check to loose bar 1e-3).
- P5 knob determinism + refusals: brentq bracket violations and self-approach (< 2t + 2 mm) raise
  `GeneratorError` (graded infeasible per WP3), never silently clamp.

**Neutral name (rename gate, Report 2 §3):** ships as `spherical_salmon`. The `lecleach` name is gated on
matching the published JMLC table (Fourcade 2015, fig. 7) within 0.5 mm — an OWNER task; per ruling
2026-10-25 `lecleach` stays BLOCKED and old `lecleach()` keeps raising (see §5).

### 2.4 organic/elliptical + X-shape (WP9b) — Report 4 §9b.2 T3/T4/T5 as LABELED hypothesis-shape experiments

Per the owner ruling 2026-10-25 and the x_shape/T5 precedent: **shipped under neutral, non-attributed names with
hypothesis labels** (config comments + provenance), because the per-azimuth elliptical construction reuses the
salmon/spherical-wavefront march (not the blocked exact-Fourcade construction) and the Iwata-style AR law is
"our reconstruction of the published principle" (Report 4 §9b.2 T4 wording), and audiohorn.net X-shape publishes
no geometry ("marketing; geometry below is OUR hypothesis" — 9b.0).

- `salmon_elliptical` (= T3 analogue): one spherical_salmon march per azimuth φ with
  `1/fc(φ) = cos²φ/fc_h + sin²φ/fc_v` (same T, same throat); rows equal-l (same arc-length fraction l/L0(φ));
  mouth edge = the saddle (each row's last point at its own (x, y)). Stop rule per φ: `stop_deg` all around.
  Report the Level-1 approximation honestly ("JMLC-type" wording is NOT used in shipped names; catalog says what
  it is).
- X-shape modulation on the elliptical rows: `stop(φ) = stop_deg·(1 + x_amp·cos 4φ')` with φ' = φ − 45°;
  optionally `fc(φ) × (1 − x_fc·cos 4φ')`; x_amp ∈ [0, 0.4], x_fc ∈ [0, 0.3]; x_amp = 0 must reproduce the
  elliptical exactly. cos 4φ is even about both mirror planes → quarter model stays valid.
- GRID route (9b.3): rows resampled to equal n_s by arc-length fraction; 3-D points P = (y·cos φ, y·sin φ, x)
  (x = the march's axial abscissa; non-monotone x is representable — verified by the curl probe); wall offset
  via explicit `outer_points` (Fourcade eqs 28–29 form, applied in-plane normal), since point-grid freestanding
  requires outer_points and infinite_baffle refuses rollback (NOTES probe); self-approach refusal ≥ 2t + 2 mm.

Checkable properties (ship bar):
- P1 fc_h = fc_v ⇒ the per-azimuth march equals the axisymmetric spherical_salmon at every φ and station
  (≤ 1e-9 mm).
- P2 x_amp = 0 ⇒ X-shape equals `salmon_elliptical` exactly (≤ 1e-9 mm).
- P3 quarter symmetry: mirror rows (φ vs 90°−φ) match within 1e-9 mm.
- P4 self-approach refusal (9b.4): rows/offsets with min non-adjacent gap < 2t + 2 mm raise GeneratorError.
- P5 resampling: arc-length resampling keeps endpoints exactly (9b.5 test list).

## 3. Numerical reference case (skill §6 "one numerical reference case or cross-check")

**Published reference case of the family (Fourcade 2015 fig. 7 — quoted verbatim from Report 4 §9b.2's
validation table; scope label): fc 400 Hz, T 0.8, throat Ø25.4 mm, exit half-angle 8°, dl 1 mm, c 344 m/s,
stop 360°.**

| quantity | published | senior-pass reference implementation (2026-10-24) |
|---|---|---|
| L0 arc length, stop 90/180/270/360° | 394 / 467 / 496 / 511 mm | 394 / 467 / 496 / 512 mm |
| mouth wavefront area S(L0) | 0.13 / 0.38 / 0.57 / 0.72 m² | 0.131 / 0.379 / 0.579 / 0.732 m² |
| overall length (max x) | 321.35 mm | 321.41 mm (dl 0.5: 321.46) |
| overall width (2·max y) | 467.30 mm | 471.31 mm (0.9 % gap, open item in 9b.2) |

**Honest scope label:** these numbers validate the EXACT Fourcade iterative construction (Report 4 §9b.2 T1,
which is BLOCKED under R9 by the owner ruling 2026-10-25 — not implemented in this pass). The G4
`spherical_salmon` march shares the Salmon area law and start/stop conventions but is a different
discretization (Report 2 §3, kept in-repo "for history only" as the construction of record for the neutral
name). Therefore the §2.3 checkable properties — NOT a 0.5 mm table match — are the G4 ship bar; the table match
remains the rename gate to `lecleach` and stays an owner task. Kugelwellen (T2) was NOT in this pass's scope
("organic/elliptical + X-shapes" only).

Cross-checks available offline for the march itself: T = 1 spherical-exponential area closed form, the
plane-wave limit (§2.3 P4), and the curl-probe mesher acceptance facts in NOTES_FOR_SENIOR.md.

## 4. Knobs and ranges (no bound widening; plan/dossier-named keys only)

- splice: `{p}_zs_frac` ∈ [0.2, 0.8] (Report 4 WP9 step 1).
- throat_blend_mm: `throat_blend_mm` default 0 (bit-for-bit baseline; Report 4 WP9 step 2). Typical range 0–30 mm
  for 1" drivers per Report 1 F4 fairness intent; tests use plan examples only.
- spherical_salmon: `fc_hz`, `T`, `theta0_deg` (= driver exit), `max_wall_deg`; for 1" briefs fc 600–1200 Hz
  (band starts at 700 Hz; Report 4 §9b.4), stop ≤ 240 default, bounds [90, 270] (§9b.4); dx fixed 0.25 mm.
- salmon_elliptical/x_shape: `fc_h_hz`, `fc_v_hz` (fc_v/fc_h 1.0–2.0; §9b.5), T 0.3–1.0, stop 120–240°,
  x_amp 0–0.35 (plan ceiling 0.4; §9b.5), x_fc 0–0.3 (§9b.2 T5).
- No invented keys beyond plan/dossier-named ones (pass constraint). Every bound here is a STARTING point for
  configs; knob-range PROPOSALS land as labeled proposals only (owner gates).

## 5. R9 status and stop conditions (skill §7)

- `lecleach`: BLOCKED (owner ruling 2026-10-25). Candidate source on record: Fourcade 2015 construction guide
  (`Pavillon-JMLC.pdf`, appendix A line ~71; primary/secondary, verifiable per Report 4 §9b.0 — the senior pass
  scored it as satisfying R9). Dated NOTES_FOR_SENIOR.md block written 2026-10-25 per the pass order; the owner
  supplies/confirms the verifiable reference in a future pass; nothing improvised.
- The neutral names shipped in this pass (`spherical_salmon`, per-azimuth elliptical + X-shape under
  hypothesis labels) follow Report 2 §3's rename-gate pattern: nothing ships under a published name without the
  verified published reference.
- `Keep lecleach() disabled`: the existing raising stub stays raising (Report 4 WP9 step 3 + §9b.5).
- Two unresolved source conflicts → NOTES_FOR_SENIOR.md + stop that line (not triggered; zero conflicts).

## 6. SUPERSESSION (dated append; not an edit of the above)

**2026-10-25, later the same day:** the owner directed in chat to integrate the Le Cléac'h typology anyway
("I don't really care about the authorship I just wanted to be right ... I want to integrate this"), accepting
the Fourcade 2015 PDF as the verified construction. The librarian verification (see
`JMLC_LECLEACH_RESEARCH_2026-10-25.md` §3–5) found the §9b.2 premise bug (fig-7's 8.0 deg is the
INCLUDED exit angle → phi0 = 4.0°) and the exact march then PASSED the R9-J gate at 0.00 mm width
discrepancy. `lecleach` therefore went live in the M4 pass (the "Keep lecleach() disabled" lines above are
the pre-directive state, kept for the record), `lecleach_exact` routes it, and `spherical_salmon` (the
neutral march) ships as a separate distinct generator. Dated record in NOTES_FOR_SENIOR.md 2026-10-25.