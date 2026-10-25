# Le Cléac'h (JMLC) construction — implementation dossier

2026-10-25, research lane. Scope: find the best-verified **published construction**, test it against its own
published reference case, compare every reachable variant, and hand the winner to the implementation lane.
Status vocabulary is 9b.0's. One file only; nothing else in the repo was edited.

## 0. Bottom line

**RECOMMENDED: Fourcade 2015's exact construction (eqs 10–27), ported as `lecleach_exact`, driven with
`phi0 = (included exit angle)/2`.** It is the only reachable source that is at once a complete, self-contained
construction *and* ships a numerical reference case produced by the author's own program. With the angle
convention corrected here (§2.2, C1) it reproduces that case to **0.00 mm on the mouth width**, +0.44 mm on
overall length, +1 mm on L0 and 0.002° on the throat angle — better than the §9b.2 table. Validation bar: gate
R9-J in §3. **Nothing further is needed from the owner.**

## 1. Sources (all fetch attempts 2026-10-25; date = fetch date)

| Source | What it gives us | Status / fetch outcome |
|---|---|---|
| **J. Fourcade, "Calcul du Pavillon Le Cléac'h", 14 Apr 2015**, 16 pp., French (`unepassionaudiophile.fr/wp-content/uploads/2018/01/Pavillon-JMLC.pdf`) | Exact construction eqs 10–27; the JMLC-2007 spreadsheet recurrence eqs 1–8 + derivation; offset eqs 28–29; pétale construction 30–35; wavefront points 36–41; expansion law 42–43; **reference case fig. 7 + table p.13** | **primary/secondary, verifiable — FETCHED, full text + page images.** Satisfies R9. |
| Fourcade **fig. 7** (same PDF, p.12, screenshot) | The complete input set and the program's four outputs | **FETCHED as image; legible** (see §2.2). Load-bearing. |
| J.-M. Le Cléac'h, **ETF 2010 lecture**, 128 slides (129-page PDF; `rintelen.ch/download/JMMLC_horns_lecture_etf10.pdf`) | p.38 "isophase surfaces are parallel … perpendicular to horn wall"; p.70 family list; p.77 tractrix cap law; p.78 Kugelwellen double radius; **p.82 one sentence + figure, no equations**; pp.121–127 OS/min-phase; p.128 the 2007 horn | **primary (author); FETCHED** (12.7 MB via curl; webfetch refused >limit). Cross-check only — cannot satisfy R9. |
| J.-M. Le Cléac'h, **diyAudio thread 140190**, posts by "Jmmlc" | The two rules in his words; quasi-Iwata T = 0.5; included (double) exit angles; throat-mismatch ripples | **live forum BLOCKED** (Cloudflare "Validating browser…"); Wayback old page 40 = 25 Jul 2009 posts, no Jmmlc post; new-forum `/page-40` snapshot 404. **In-repo quotes only [unverified-today]**. |
| **sphericalhorns.net, "JMLC Inspired Horn Calculator"** (21 Dec 2020) | A different discretization; the explicit disclaimer; the "first outer element from P1 to P2" convention | **secondary; FETCHED, full text.** Cross-check only. |
| sphericalhorns.net, Kugelwellen (25 Aug 2019) | T2 cross-check (constant construction vector r_k, closed form) | **secondary; FETCHED.** Out of scope here. |
| **AxialHorn.zip** (the program that produced the reference numbers) | Would settle the internal first-step code | **NOT FOUND.** The PDF names `<AxialHorn.zip>` with no URL; site search and tag page return no JMLC article; no public mirror. **Reference numbers are published outputs, so the loss is not fatal [unverified-today: internals].** |
| **JMLC 2007 spreadsheet `<Pavillon JMLC.xls>`** | The recurrence's seed rows | **NOT FOUND.** Fourcade writes only "On pourra télécharger le fichier Excel … (version de 2007)" (p.4–5), no link. |
| GitHub / code search (`gh_grep` "JMLC", "lecleach") | Any public port | **none found** (only MJML and an unrelated robotics author). [verified empty 2026-10-25] |
| B. Kolbrek, audioXpress Part 2 | Principle (equidistant wavefronts normal to wall + Salmon law) | not fetched today; in-repo §9b.0 quote [unverified-today]. |

## 2. Construction comparison

### 2.1 What Fourcade actually publishes (byte quotes, French, page numbers)

Throat (p.6): "**R0 = D / (2 sin φ0)**" (11); "**h = R0(1 − cos φ0)**" (12); "**S0 = 2πR0²(1 − cos φ0)**" (13).
Per-station cap (p.7): "**S0i = 2π(R0 + li)²(1 − cos φ0)**" (15). Ring (p.7): "**Ski = 2π(li − lk−1)[(li − lk−1)
sin φk−1 + yk−1]dαk−1**" (20), with "la hauteur de cet élément soit tel que h = li − lk−1". Compensator (p.8):
"**Sii = Si − Σ(k=0..i−1) Ski**" (22); "**ri = dl sin φi−1 + yi−1**" (23); "**dαi−1 = Sii / (2π ri dl)**" (24);
"**φi = φi−1 + dαi−1**" (25); "**xp_i = xp_i−1 + dl cos φi**" (26); "**yp_i = yp_i−1 + dl sin φi**" (27).
Law (p.11): "**S(l) = S0 [cosh(m l/2) + T sinh(m l/2)]²**" (42); "**m = 4πfc/c**" (43) with "c la vitesse du son
dans l'air (**344 m/s**)". Stop rule (p.11): "le calcul prend fin quand l'angle que fait le profil avec l'axe X du
pavillon est supérieure ou égal à l'angle d'arrêt". Offset (p.8): "Notons **d** la distance de décalage …
**xd_i = xp_i + d cos(φi + π/2)**" (28) and "**yd_i = yp_i + d sin(φi + π/2)**" (29) — *the PDF prints `dl` in
28–29; the text defines `d`. Use the offset distance, not the step.* (Published typo.)

### 2.2 C1 — dated correction: the reference-case angle is INCLUDED, not a half-angle

Fig. 7 (p.12) reads: "Frequence de coupure **400.0** Hz / Facteur de forme **0.8** / Diametre de la gorge
**25.4** mm / **Angle de sortie de la compression 8.0 deg** / Pas de calcul **1.0** mm / Angle d'arrêt **360.0**
deg / Vitesse du son **344.0** m/s", and prints "Longueur du pavillon **321.35** / Largeur du pavillon
**467.30** / **Angle de la gorge 8.55** / Surface du front d'onde **0.7214**". The output label is defined on
p.12 as "**Angle du cône tangent au profil au niveau de la gorge (degrés)**", to be compared with "celle du cône
de sortie de la compression. Pour qu'il y ait continuité de la pente, il faut en théorie que ces angles soient
identiques". Both are **cone (included) angles**, consistent with JMLC's driver tables quoting double angles
(§9b.0). **[inferred from the wording, then verified numerically: only φ0 = 4.0° reproduces both 467.30 mm and
8.55°.]** Therefore the construction's half-angle is **φ0 = 4.0°**, not 8°.

Consequences (exact march, dl 1.0 mm, c 344): **width 467.30 mm (published 467.30)**, **2φ1 = 8.552° (published
8.55)**, L0 394/467/496/**512** (published 394/467/496/**511**), length **321.79** (321.35), S(L0)
0.1303/0.3784/0.5773/0.7294 (0.13/0.38/0.57/0.72). Driving φ0 = 8.0° instead — as `jmlc_reference.py` did in
its `__main__` — is what produced §9b.2's "0.9 % width gap" (471.31), its length 321.41, its "φ dips to 4.3°",
and the undefined 8.55° throat angle. **Both §9b.2 open items are closed by this single convention fix; no new
construction and no first-step variant is needed.** The 0.5 mm length residual is [inferred] AxialHorn's
reporting/resampling convention (it does not vanish with dl; 321.85 at dl 0.5, 321.88 at 0.25), not a profile
difference.

### 2.3 Canonical reference case (replaces §9b.2's table; fc 400 Hz, T 0.8, Ø 25.4 mm, exit 8.0° **included**,
dl 1.0 mm, c 344 m/s, stop 360°; 12 pétales and 10 mm offset are in fig. 7 but do not enter the meridian)

| quantity | published | exact march, φ0 = 4.0° | Δ |
|---|---|---|---|
| L0 at stop 90/180/270/360° | 394 / 467 / 496 / 511 mm | 394 / 467 / 496 / 512 mm | 0 / 0 / 0 / +1 mm |
| S(L0) at the same stops | 0.13 / 0.38 / 0.57 / 0.72 m² (fig. 7: 0.7214) | 0.1303 / 0.3784 / 0.5773 / 0.7294 m² | ≤ 1.3 % |
| overall length (max x) | 321.35 mm | 321.79 mm | +0.44 mm |
| overall width (2·max y) | 467.30 mm | **467.30 mm** | 0.00 mm |
| throat tangent cone, included | 8.55° | 8.552° | 0.002° |

S note: fig. 7's 0.7214 lies between the law at l = 511 mm (0.7188) and l = 512 mm (0.7294); [inferred] the
program reports the area of its finite-step constructed wavefront, not the closed-form S(L0). A ±2 % area
tolerance covers either reading. Width is achieved at dl 1.0 (467.22 at dl 0.5).

### 2.4 The other candidates, and why they are not the implementation of record

- **JMLC 2007 spreadsheet recurrence (eqs 1–8).** Published, but **not self-starting**: eq 1
  "**S*_i = (2√S_{i−1} − √S_{i−2})²**" needs two prior areas and eq 3 "**r*_i = 3r_{i−1} − 3r_{i−2} + r_{i−3}**"
  needs three prior radii; the PDF
  gives no seed rows (the .xls is not reachable). It is explicitly an approximation: Fig. 9 "l'erreur absolue est
  inférieur à 1 degré jusqu'à 50 degrés d'ouverture et … l'erreur relative reste inférieure à 7% jusqu'à 90
  degrés", and p.16 tabulates 0.5 / 2.6 / 2.7 % at 90/180/270°. Seeding rows 0/1 from the exact eq 24 (my
  check) drifts to L0 536 mm / width 481 mm — **not** usable as a validation target. [verified numerically
  2026-10-25]
- **ETF10.** p.82 is one sentence and a figure: "Le Cléac'h's method to calculate the profile of an horn knowing
  the relation between the area of the wavefront and its distance to throat." No equations, no numbers, no
  answer for a programmer. Confirms the 2026-10-25 ruling that the deck alone cannot satisfy R9. [verified]
- **sphericalhorns.net 2020 calculator.** Explicitly a different algorithm: "I don't want to claim that my
  algorithm delivers exactly the same results as the original JMLC spreadsheets … my approach is based on the
  actual numerical summation of a fixed growing conical mid element … The most outer element for each step is
  added to fulfil the given expansion law", with a Newton-solved start and a maximum angular sub-step. Its
  "the first outer element to be added arises from P1 to P2 and not from P0 to P1" was tested as the §9b.2
  width-gap hypothesis: at φ0 = 8° it moves width 471.31 → 469.08 mm (not 467.30) and makes the throat transient
  worse (φ → −3.15°); at φ0 = 4° no variant is needed. **Hypothesis rejected; use Fourcade's step order.** No
  reference table in the post. [verified numerically 2026-10-25]
- **Repo port `jmlc_reference.py`.** Exact eqs 10–27 and a faithful ring sum, but it takes `D_mm` (**diameter**,
  25.4) and its `__main__` passes φ0 = 8.0. With φ0 = 4.0 it is the recommended construction unchanged. [verified]

## 3. RECOMMENDATION

1. **Implement Fourcade's exact construction (eqs 10–27, 42–43) as `lecleach_exact`.** Not the 2007 recurrence,
   not the sphericalhorns variant, not a re-derived Salmon march.
2. **Make the canonical reference case a test fixture** (§2.3) with the corrected φ0 = 4.0° (numbers live in the
   test, not in production code — the repo's YAML rule still applies to shipped defaults).
3. **ONE gate, R9-J** — both prior wordings point "at the mouth"; adopt the stricter and retire the looser:
   **mouth width |Δ| ≤ 0.5 mm** (V6 said 1 mm, Report 2 §3 said 0.5 mm; we achieve 0.00 mm, so 0.5 mm costs
   nothing and is the bar the rename gate already used). The same test also asserts, as regression guards,
   |ΔL0| ≤ 1.0 mm at each stop, |Δ overall length| ≤ 1.0 mm, S(L0) within ±2 %, and the included throat cone
   angle within 0.1°. **Recommendation: 0.5 mm governs; the 1 mm wording is superseded** (it also passes, so the
   choice is not a risk).
4. **Nothing needs the owner.** The 2026-10-25 questions are answered by the sources: (a) Fourcade 2015 is a
   verifiable published construction with a numerical reference case (it is what 9b.0 scored as satisfying R9);
   (b) the 0.5 mm rename gate is met at 0.00 mm on the mouth width once the included-angle convention is used.
   Fourcade also records "les pavillons Le Cléac'h sont libre de droit" (p.3); attribution is moot per the owner.

## 4. Wiring plan (handoff to the implementation lane)

`design/generators/profiles.py::lecleach_exact(r0_mm, fc_hz, T, phi0_deg, stop_deg, dl_mm=1.0, c=344)`:
`r0_mm` is the **radius** (`driver.exit_radius_mm`, 12.7 for 1"); `phi0_deg` is the **half**-angle and the
repo's `driver.exit_angle_deg` is already a half-angle (see `osse_75x45.yaml`: "throat half-angle"), so **do not
halve it again** — halve only at the boundary where an operator pastes a JMLC driver-table included angle.
Compute R0 = r0/sin φ0, S0 = 2πR0²(1−cos φ0), m = 4πfc/c, S(l) per eq 42; seed (x0,y0,φ0) = (0, r0, φ0) and run
eqs 15/20/22/23/24/25–27 with l_i = i·dl until φ_i ≥ stop_deg (inclusive, per p.11); return mm samples (x, y, φ)
plus meta {L0, S(L0), max x, 2·max y, 2φ1, per-stop table}. Vectorize the eq-20 ring sum (O(n²), ms).

- **Route `lecleach()` to it only after R9-J passes**; until then the old stub keeps raising (§9b.5). On pass,
  `lecleach()` becomes an alias with the same knobs; configs carry `generator: {name: lecleach_exact}`.
- **Rollback > 90°** goes through the WP10 point-grid freestanding route with an explicit `outer_points` offset
  (eqs 28–29 with the offset distance, not `dl`). Per the 2026-10-24 curl probe (NOTES_FOR_SENIOR.md): BARE mode
  (`closed=False`, no `outer_points`) is not BEM-usable; `infinite_baffle` refuses rollback; freestanding +
  `outer_points` passes bbox/symmetry/topology at 200° and 240° (t = 3 mm; min self-distance 19.6 / 18.5 mm;
  budget a finer mouth resolution — 8 slivers at 12 mm). Rows are resampled at equal arc-length fraction l/L0
  (§9b.3). **FREEFORM remains the interim route for stop ≤ 90°**;
  if the GRID path is not yet wired, clamp and log rather than silently meshing a BARE shell.
- **Knobs/bounds**: `fc_hz` 600–1200 for 1" (§9b.4); `T` 0–1, default 0.8 (0.5 = Iwata analogue, 0.707 = hypex,
  1 = exponential); `stop_deg` default ≤ 240, bounds [90, 270] (at 360° the spiral nearly closes); `dl_mm` fixed
  1.0 (0.5 only in tests). Sizing sanity at r0 12.7 / φ0 5°: fc 800, T 0.8 → 114 mm long × 235 mm wide at stop
  180–240; fc 600 → 178 × 312 mm. [verified numerically 2026-10-25]
- **Throat/source**: JMLC's throat front is the cap of radius **R0 = r0/sin φ0**, exactly `source.cap: auto`
  (r0/sin θ_throat) — keep `auto`, with θ_throat = φ0. Report `throat_angle_mismatch_deg` in the brief's own
  convention (half-angle): φ1 − φ0 = +0.276° in the reference case (0.55° included).
- Keep every number in YAML (reference case, fc/T/stop/dl/c); provenance records the generator and its knobs.

## 5. Open items, labels, corrections

- **C1 (2026-10-25):** §9b.2's reference case says "exit half-angle 8°"; it is the **included** angle (fig. 7,
  p.12), so φ0 = 4.0°. This supersedes that row and the §9b.2 "0.9 % width" and "throat cone angle" open items.
  Do not edit the appendices or the implementation plan; this block plus a pointer is the correction.
- **C2 (2026-10-25):** §9b.2's "our φ dips to 4.3° in the first mm" is a symptom of C1, not a property of the
  construction; at φ0 = 4.0° the first step gives φ1 = 4.276° (8.552° included), matching the program.
- **Open [unverified-today]:** AxialHorn internals (zip not located); the 2007 .xls seed rows (not located);
  Jmmlc's own forum wording (live forum blocked; Wayback snapshot checked was 2009). None blocks implementation:
  the published equations and outputs are sufficient and reproduce.
- **Open [inferred]:** the +0.44 mm length and the 1.1 % area offset are AxialHorn reporting/resampling effects
  (they do not converge away with dl); guarded at 1 mm / 2 %, not used as a name gate.
- **Not in scope:** pétales (eqs 30–35; a faceted gramophone construction, not a smooth BEM surface) and the
  offset profile (only for the outer shell, eqs 28–29).
- **Caveat that survives:** 360° is a nearly closed spiral (thin gaps, self-approach); the ≤ 240° default and the
  self-approach refusal (≥ 2t + 2 mm) stand. 2007-recurrence reproduction is not attempted beyond §2.4.
