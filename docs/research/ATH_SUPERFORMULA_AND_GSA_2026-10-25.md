# P6 IMPLEMENTATION PLAN — the superformula family (P6a) + the GSA-vs-CMA-ES bake-off (P6b)

v1.0 · 2026-10-25 · written by the orchestrator from three research passes (the §11 pass plus two deep web lanes
on 2026-10-25 — the Gielis/superformula-math-and-horn-theory lane and the bake-off-methodology-and-GSA lane).
This file **supersedes the research dossier that previously lived at this path**; that dossier's content is folded
into §2-§3 below, nothing was lost. Companion summary: `docs/plan/12_RESEARCH_BASIS.md` §11 and §11.5.

**Status: NOT STARTED — fully specified, owner-gated.** Execution begins only after **both** gates open:

- **GATE 1 — the senior-pass programme is complete**: WP1–WP17 landed through M5 (M4: WP9 generators, WP9b
  T1–T7 typologies, WP10 GRID, WP12 mounting; M5: WP11 restarts + CMA-ME atlas, WP16 non-uniform source velocity,
  WP17 near-singular correction, WP14 multicell), with real owner briefs in `examples/briefs/user/`.
- **GATE 2 — owner GO** on P6a and/or P6b (they are independently runnable; P6b may be declined and P6a still run).

Everything in here is written so a lower-reasoning agent can execute it by following steps literally. Where the
executor is unsure, the rule is the repo's own: **append the question to `NOTES_FOR_SENIOR.md` (append-only) and
stop that line of work. Never invent a key, a number, or a file.**

---

## 0. Read-me first — how to execute this plan

### 0.1 What you may and may not touch (file ownership)

| Lane owns (may create/edit) | Never touch |
|---|---|
| P6a lane: `examples/superformula_*.yaml`, `examples/catalog.yaml` (add entries), `hornlab_search/design/**` (the gcurve validity guard only), `tests/test_design_gcurve_guard.py`, `docs/evidence/P6_*.md` | `docs/plan/**` (all frozen), other lanes' files, any installed package, `.venv`, solver/mesher internals |
| P6b lane: `hornlab_search/search/gsa.py`, `hornlab_search/config.py` (algorithm switch only), `tests/test_search_gsa.py` | same frozen set; `search/cma.py` read-only |
| Harness lane: `tools/bakeoff/**`, `tests/test_bakeoff_harness.py` | everything under `hornlab_search/` |
| GUI lane: `hornlab_search/gui/data.py`, `hornlab_search/gui/server.py`, `static/bakeoff.js`, additions to `static/` shared files ONLY as specified in WP-P6-GUI-1/2, `tests/test_gui_bakeoff.py`, `tests/test_gui_gcurve.py` | Python outside `gui/` |
| Everyone: `docs/CONTINUITY.md`, `docs/ISSUES.md`, `NOTES_FOR_SENIOR.md` (append-only), `docs/INDEX.md`/`docs/CODE_MAP.md` (same-commit rule) | — |

Waves 1's lanes have **zero file overlap** — that is what makes the parallel dispatch safe. `config.py` is owned
exclusively by the P6b lane; `examples/**` exclusively by the P6a lane; `gui/**` + `static/**` exclusively by the
GUI lane.

### 0.2 Step 0 — seam checks before any wave (run all four, paste outputs into the run log)

| # | Command | Expected | If it differs |
|---|---|---|---|
| S1 | `grep -n "algorithm" hornlab_search/config.py` and `grep -n "restarts" hornlab_search/config.py` | a `search.algorithm` switch exists (WP11): choices include `cma` and `cma_me`; a `search.restarts` key exists | If absent: WP11 did not land as spec'd. Add the switch inside WP-P6b-1 with `choices: ("cma", "gsa")` and note the deviation in `NOTES_FOR_SENIOR.md` |
| S2 | `grep -n "gcurve" hornlab_search/design/families.py` | the `_GCURVE` key table incl. `gcurve_type`, `gcurve_sf_a/b/m1/m2/n1/n2/n3`, `gcurve_se_n`, `gcurve_dist`, `gcurve_width_mm` | If absent: STOP — append to `NOTES_FOR_SENIOR.md`; the whole P6a premise depends on these keys |
| S3 | `.venv\Scripts\python.exe -m hornlab_search.cli doctor` | green (backend cuda ready; expected `pinned-shas` state per the then-current FORKS.md regime) | Follow `hornlab-gpu-job` preflight expectations; never hand-fix pins |
| S4 | `ls examples/briefs/user/` (non-empty) + owner GO recorded in `NOTES_FOR_SENIOR.md` | ≥1 real owner brief | **Never spend GPU searching demo sheets** (owner directive 2026-10-24). No real brief → P6a GPU waves wait |

### 0.3 Sequencing map

```
WAVE P6-0   seam checks + measured-numbers refresh + mesh-only SF probes (CPU)        serial, one agent
WAVE P6-1   WP-P6a-1 | WP-P6b-1 | WP-P6b-2-harness | WP-P6-GUI-1+2                     3-4 agents, PARALLEL
WAVE P6-2   WP-P6a-2  superformula screen -> verify -> dense-net gate -> report/STEP   serial, GPU owner-approved
WAVE P6-3   WP-P6b-3  bake-off execution (Stage A/B branch, see the branch table)      serial, GPU
WAVE P6-4   WP-P6-4   senior verification + docs + decision recording                  senior agent, read-only verify
```
Parallelism means writing code in parallel. **One GPU, one solve at a time, forever** (GPU lock + `gpu-clean`
per `hornlab-gpu-job`; searches legitimately reuse their warm worker).

### 0.4 Verification recipe (every wave ends with it)

1. `python -m compileall hornlab_search/` (or the touched package) — zero errors.
2. Offline suite: `python -m pytest -m "not slow and not gpu and not crosscheck" -q` — use junitxml counters
   (the console count line can drop via `Tee`; read `suite.xml`).
3. GPU waves additionally: the `hornlab-gpu-job` recipe (clean state before/after, `doctor` preflight, verified
   host shutdown) and the `hornlab-evidence` byte-check for every quoted block of any evidence doc.
4. Every checkpoint in §6 needs **pasted terminal output** — a summary is not evidence.

---

## 1. What gets built (plain language, one page)

**P6a — a search campaign over the superformula mouth outline.** The "super equation" the collaborator named
(the Gielis superformula) is already in the mesher: OSSE's guiding curve can be a superellipse (type 1) or a
superformula (type 2). The knobs are already in the searchable design space — nobody has ever *used* them. P6a
adds three catalog families (superformula guiding curves with m = 4, 8, 12), one example config per m, and runs
screen → verify → the dense finalist resonance gate → report/STEP on the owner's real briefs. Verified claim:
**no public repo anywhere searches superformula horn parameters** — this is a genuine first, and every record it
produces joins the dataset (same screen grid group, so it trains together with everything else).

**P6b — a fair algorithm bake-off: CMA-ES vs GSA.** Two recipes for "which shape to try next": CMA-ES (the
current engine) and GSA (Gravitational Search Algorithm, Rashedi 2009 — agents with fitness-proportional mass
attracting each other under decayed simulated gravity). The bake-off runs both (+ a Latin-hypercube random
baseline) at **identical evaluation budgets** on three shape families with pre-registered statistics, and reports
the answer honestly either way. The literature audit found **no published head-to-head** and **no maintained
GSA implementation worth depending on** — so we write our own ~120-line GSA with an 8-test suite. Expected
outcome (stated up front, so nobody is disappointed): CMA-ES stays the default; GSA is unlikely to win at equal
budget unless the penalty landscape is unusually deceptive — but at our budgets *neither* algorithm is in its
published comfort zone, which is exactly why a fair measurement is worth having.

**GUI additions.** Two small features read straight from run folders (the GUI adds no physics): (a) a
**mouth-outline preview** on run pages — the guiding curve r(φ) drawn as a small polar SVG from the design's
parameters; (b) a **bake-off view** — race chart (best-so-far vs solves, median + spread band), ECDF of final
best, final-best box plots per budget, and a budget-normalized table with the statistics in a footnote.

---

## 2. Research basis (all labels: [verified] / [inferred] / [open])

### 2.1 Superformula math for meshing — the rules P6a is built on

- **Base form** [verified: Gielis 2003; HornLab schema `docs/config-schema.md` L45–46; Ath User Guide §4.1.1]:
  `r(φ) = (|cos(mφ/4)/a|^n2 + |sin(mφ/4)/b|^n3)^(−1/n1)`. HornLab's `sf(m,n1,n2,n3,a,b,p)` is exactly this.
  Gielis himself now prefers "Gielis curves" [verified: PLoS ONE 2012, doi:10.1371/journal.pone.0029324].
- **Extended form with separate m1/m2** [verified: Ath User Guide p.18 — array `GCurve.SF = a,b,m,n1,n2,n3`
  sets m1 = m2 = m; the item form has separate `GCurve.SF.m1`/`GCurve.SF.m2`]. Our mesher exposes
  `gcurve_sf_m1` (default 4) and `gcurve_sf_m2` (default none) [verified: schema.md].
- **m1 ≠ m2 destroys quarter-symmetry** [inferred, from the formula]: with one m the cos/sin terms swap under
  90° rotation (that is what creates m-fold symmetry); with m1 ≠ m2 the swap fails and only the mirror about
  φ = 0 survives. **P6a v1 fixes m1 = m2.**
- **Non-integer m is a different object, not a rounding accident** [verified: Gielis PLoS ONE 2012 defines
  m = p/q with p = symmetry number, q = self-intersection count; Symmetry 2022 (14:2475, doi:10.3390/sym14122475)
  proves `r(φ + 2qπ) = r(φ)` and that irrational m never closes]. **P6a uses integer m only.**
- **Quarter-domain (x≥0, y≥0) validity table** [inferred, derived from the absolute-value structure; consistent
  with the Symmetry 2022 proofs]:

  | condition | mirror x-axis (always true) | mirror y-axis | true 90° (D4) |
  |---|---|---|---|
  | m ≡ 0 (mod 4), e.g. 4, 8, 12, 16 | yes | yes, any a/b/n2/n3 | only m ≡ 0 (mod 8) |
  | m ≡ 4 (mod 8), e.g. 4, 12 | yes | yes | only if a = b and n2 = n3 |
  | m ≡ 2 (mod 4) | yes | only if a = b and n2 = n3 | no |
  | odd m | yes | no | no |

  Practical reading: **m ∈ {4, 8, 12, 16} are the only quarter-mesh-safe values**; m = 8/16 give D4 free;
  m = 4/12 give a D2 (rectangular-symmetric) mouth unless a = b and n2 = n3. The mesher mirrors the quadrant
  without checking — WAVE P6-1 adds the numeric assertion (WP-P6a-1 step 6) so an asymmetric curve can never
  silently produce the wrong horn.
- **Closure with a ≠ b / n2 ≠ n3** [inferred — odd m closes only if a = b and n2 = n3; even m closes for any
  combos]: covered by the integer-even-m rule above; a unit test pins it (WP-P6a-1 step 6).
- **Smoothness** [verified: Gielis PLoS ONE 2012 — cusps are the measure-zero exception]: C∞ except at tips
  (radius extrema) and self-intersections. **Star-tip sharpness is governed by n2/n3, not m** [verified:
  Symmetry 2022 §3 — small n2 rounds corners, large n2 sharpens them].
- **The degeneracy to guard** [verified: Symmetry 2022 §3/Figs 2+A1]: for small n1 and large n2 the shape
  degenerates to "lines radiating from the center". **Guard: reject any design with `n1 < 2 AND
  max(n2, n3) > 10`** (deterministic `invalid_gcurve` marker, WP-P6a-1 step 5).
- **Curvature guard** [inferred, meshing practicality]: minimum radius of curvature anywhere on the outline
  must exceed ~0.5 × mouth resolution (default 8 mm; Ath CORE uses 11 mm [verified defaults]). Polar-curve
  curvature: κ(φ) = (ρ² + 2ρ′² − ρρ″)/(ρ² + ρ′²)^{3/2}; numeric on a 720-point φ grid. Spec in WP-P6a-1 step 5.
- **a/b are degenerate** [inferred from Ath's own decomposition]: Ath scales by `GCurve.Width` and
  `GCurve.AspectRatio`, so only the a:b ratio changes shape once width is normalized. **P6a fixes a = 1 and
  searches `gcurve_sf_b ∈ [0.6, 1.6]`.**
- **The superellipse exponent cap [2, 16] matches practice** [verified: Ath documents only n ≥ 2 for
  `GCurve.SE.n`; observed Ath practice reaches exactly 16 (CORE) and 15] — above ~16 the outline is visually a
  rectangle and |cos|^n loses derivative resolution. Keep the cap.
- **Angular resolution** [verified: Ath User Guide §6.4.2 uses `Mesh.AngularSegments = 120` for a superformula
  guiding curve and calls 64-ish grids "a bit coarse"]: P6a configs use 100–120, subject to the dof-cap probe
  (WP-P6a-1 step 9).

**Quotable reference values [verified]:**

| Source | Values |
|---|---|
| Ath 4.8.2 User Guide §6.4.2 (canonical worked example) | `GCurve.SF = 0.95, 0.82, 4, 0.8, 7, 1.9`; `GCurve.Width = 68` mm; `GCurve.Dist = 0.5` |
| ATH CORE 2026 (wall-angle use) | `a = 5 + 35*sf(4,12,15,16,1,0.618,p) - 15*cos(p)^10` |
| HornLab fixture `sf1.cfg` | `sf(5,3,7,2,1.3,0.8,p)` |
| HornLab fixture `sf2.cfg` | `sf(3,1.5,4,9,0.7,1.2,p)` |
| HornLab guiding-curve defaults | a=1, b=1, m1=4, m2=none, n1=n2=n3=2 (circle) |
| Ath guiding-curve defaults | `SE.n = 3`, `AspectRatio = 1`, `Rot = 0` |

### 2.2 Horn mouth-shape theory — what the record supports

- **No published claim that non-elliptical mouths raise higher-order modes** [verified absence in the searched
  literature]. The defensible physics statement [inferred, adiabatic-invariance argument]: a duct of *constant*
  non-circular cross-section does not convert modes; a duct whose *shape changes along the axis* (circular
  throat → superformula mouth) does. Therefore P6a judges mouth shapes by how **gradually** the outline engages
  (`gcurve_dist` placement), not by "round vs not".
- **The community rule is smoothness, not circularity** [verified: Batík's OS-SE paper §5 — profile parameters
  "may vary around the device, i.e. not necessarily being axisymmetric"].
- **Mouth termination matters more than mouth outline** [verified: OS-SE paper §1/§6; R-OSSE paper intro; Ath
  User Guide §4.1.3 "Rollback — vital for free standing horns"]. P6a therefore never disables whatever
  termination/rollback the owner's brief family already uses — the superformula campaign is an *additive* mouth
  outline search on top of existing OSSE termination knobs.
- **Enclosure/baffle mounting masks mouth-outline effects at low frequency and lets them dominate at high
  frequency** [verified: Dong, Doc & Félix, JASA 155:2270, 2024, doi:10.1121/10.0025389]. Post-WP12, owner briefs
  may carry `mounting:`; the report should state which mounting a run used (existing provenance machinery).
- **Keele's mouth-size λ-rules are community practice; the exact 1973 coefficient is not retrievable** [the
  preprint is UNVERIFIED]. P6a does not hardcode any Keele constant; the brief's envelope does the size thinking.

### 2.3 Prior art — and why P6a is a genuine first

- **No public repo uses `GCurve.SF`, and zero repos combine horn + superformula at all** [verified: GitHub code
  search, Oct 2026 — `GCurve.SF` 0 hits; `horn+superformula`, `gielis+horn`, `waveguide+superformula` all 0].
  HornLab's mesher only *parses* Ath guiding-curve keys ("supported for OSSE only; R-OSSE rejected") and ships
  two superformula fixtures (`sf1`, `sf2`); it has no search.
- **The closest public loop is `rafaelst00/Waveguide_PSO`** [verified README]: PSO over OS-SE parameters driving
  Ath + ABEC, objective = weighted balance/ripple/angular smoothness. Not superformula — but it validates the
  loop shape and its warning ("values too wide → very long") matches our bounds philosophy.
- **Other fields' superformula optimizations** [all verified titles]: the QPSO-optimized 3-D-printed supershape
  antenna (IEEE TAP 2025, doi:10.1109/tap.2025.3616764) is the closest methodological analogue (derivative-free
  swarm on ~5–8 shape knobs); supershape FSS/metamaterial unit cells fix a/b and search the exponent pair + m;
  the lens-antenna design tool (IEEE JRFID 2024, doi:10.1109/jrfid.2024.3396333) mostly *draws*, not searches.
- **Fitting literature warns the parameter→shape map is badly behaved** [verified: PLoS ONE 2012 —
  evolutionary fitting converges to local minima in ~300 iterations with wrong symmetry; "for q > 4, all
  approaches systematically lead to convergence to local minima"]: the map is many-to-one and local-minimum-
  riddled. **Consequence: P6a starts every campaign from 3 hand-picked seed shapes, never one random start.**
- **If derivatives are ever wanted** [future note, not in v1]: Norato, Struct Multidisc Optim 2018
  (doi:10.1007/s00158-018-2034-z) — supershapes as differentiable geometry projections for gradient-based
  topology optimization.

### 2.4 Bake-off methodology — the protocol P6b is built on

- **Primary endpoint: fixed budget** ("best penalized objective after N evaluations") — that is the deliverable
  a GPU owner cares about; **secondary view: fixed-target ERT/PAR10** [verified: COCO methodology,
  arXiv:1605.03560 §4 — fixed-target is quantitatively interpretable; Bartz-Beielstein et al. arXiv:2007.03488
  legitimize both framings].
- **The anytime trick:** both algorithms are anytime optimizers — run each arm once to the max budget and **slice
  the same run at B ∈ {100, 200, 400}** [inferred, standard COCO practice]. No extra GPU.
- **Cross-family comparability: report gap-closed** = (f_start − f_best)/(f_start − f_ref), f_ref = best known
  design on that family [inferred; makes medians comparable across horns].
- **Seeds: 30 per (algo × family) where cheap, ≥10 where GPU-bound** [verified: COCO uses K = 15 and warns even
  4/15 vs 0/15 is not significant at 5% — small-N comparisons detect only near-total dominance; report effect
  sizes regardless]. Seeds are fixed in advance; our BEM is deterministic, so all arms start from **identical
  initial designs** [verified recommendation: same starting points across algorithms, arXiv:2007.03488].
- **Statistics: Wilcoxon rank-sum per family + Holm correction across the 3 families; report Vargha–Delaney Â12
  (0.56/0.64/0.71 ≈ small/medium/large); pre-register ONE primary endpoint** [verified: Carrasco et al. 2020,
  arXiv:2002.09227 — the standard toolkit and its misuse list; Derrac et al. 2011 tutorial
  doi:10.1016/j.swevo.2011.02.002]. Never report a single "best run"; never rely on mean-only curves.
- **Report feasible-best SEPARATELY from penalized best** [inferred — the graded penalty makes J always finite,
  which would hide "never found a manufacturable horn"].
- **The budget-arithmetic trap [the #1 fairness hazard]:** canonical GSA (N = 50 agents, T = 1000 generations =
  50,000 evaluations) at a 400-evaluation budget yields **8 generations with Kbest barely annealed** — a crippled
  GSA that proves nothing. **P6b pre-tunes N to the budget on offline toy problems** (WP-P6b-2) and reports the
  tuned values; CMA-ES gets its standard production configuration (post-WP11 restarts included).
- **Honesty in both directions** [verified]: "the choice of the best algorithm depends remarkably on the
  available budget" (BBOB-2009, 31 algorithms); nevergrad's own note that CMA is excellent "when the budget is
  large (e.g. 1000× the dimension)" — at 5–20 dims that is 5k–20k evaluations, i.e. **we are outside CMA-ES's
  comfort zone too**. Metaphor-skepticism citation if the collaborator over-claims: Sörensen, ITOR 2015
  (doi:10.1111/itor.12001).
- **Direct evidence for either side at 5–20 dims, expensive, simulation-in-the-loop: none published** [verified
  absence]. GSA appears in antenna arrays and truss optimization, compared against GA/PSO at unequal budgets
  [metadata verified: Swain 2016 doi:10.1109/aeeicb.2016.7538343; Khatibinia & Naseralavi 2014
  doi:10.1016/j.jsv.2014.07.027]; EM practitioners use surrogate-assisted optimization instead
  [verified: Koziel & Pietrenko-Dabrowska, Sci Rep 2022, doi:10.1038/s41598-022-24250-1].

### 2.5 GSA implementation audit — write our own ~120 lines

| Library | Has GSA? | Verdict |
|---|---|---|
| nevergrad (MIT, active) | **No** — 0 "gsa/gravitational" hits in 519 files; its CMA is a pycma wrapper | use only as a reference for benchmark CSV conventions; not as the harness (its benchmark module: custom imports broken on Windows [verified]; no GPU-queue concept) |
| mealpy v3.0.3 (MIT) | **No** — `physics_based/GRSA.py` is *General Relativity* Search | irrelevant |
| pygmo/pagmo 2.20 | **No** (verified algorithm list) | irrelevant |
| NiaPy 2.7.1 (MIT) | Yes, but a **retuned variant** (g0=2.467, G=g0/t, **no Kbest schedule**) | cross-reference only, not "the 2009 GSA" |
| PyPI `GSA` 1.0 | broken (uninitialized accumulators, double G-decay, fixed random coefficients) [verified code] | **do not use** |
| `pyGSA` 0.1 | not an optimizer (global *sensitivity analysis*; README literally says `your_name_here`) | name collision; ignore |
| himanshuRepo/Gravitational-Search-Algorithm | the canonical MATLAB port (G0=100, α=20, Kbest 100%→2%) | **no LICENSE file** — readable reference, not vendorable |

**Canonical loop (WP-P6b-1 implements exactly this)** [verified: Rashedi 2009 + the MATLAB port]:
`G(t) = G0·exp(−α·t/T)`; masses `m_i = (fit_i − worst)/(best − worst)` normalized; forces summed from the Kbest
heaviest agents with per-draw random coefficients; `a = F/M`; `v ← rand·v + a`; `x ← x + v`.

**Pitfalls → hard requirements** (each is a named unit test in WP-P6b-1) [verified individual bugs in real code]:

| Pitfall | Requirement in our implementation |
|---|---|
| `best == worst` → 0/0 NaN | uniform masses fallback |
| ε placement | scalar ε = 1e-10 on `‖xi − xj‖ + ε`; never per-coordinate |
| multiplicative G-decay bug | always compute G from absolute t, never `G ← G·exp(…)` |
| Kbest rounding to 0 | floor Kbest at 1; schedule 1.0 → 0.02 of N linearly |
| fixed random coefficients | redraw per agent/dimension/generation |
| division by M_i ≈ 0 | divide by `M_i + ε` |
| agents stick to bounds | clip position AND zero that velocity component |
| G0 scale-dependence | our box is the unit box [0,1]^k (cma.py convention); G0 exposed as `search.gsa.g0`, default **1.0**, tuned in WP-P6b-2 |
| graded penalty dominates masses when all-infeasible | J-based masses (J is always finite) + feasible-best logged separately; if the whole population is infeasible, fall back to uniform masses |
| non-reproducibility | `numpy.random.default_rng(seed)` per run, module-level seed from config |

**Named GSA variants** (for the report's related-work paragraph only; none is implemented in v1) [metadata
verified]: opposition-based GSA (Shaw et al., IJEPES 2012, doi:10.1016/j.ijepes.2011.08.012), disruption-GSA
(Sarafrazi et al., Scientia Iranica 2011, doi:10.1016/j.scient.2011.04.003), chaotic-G (Mirjalili & Gandomi,
ASOC 2017, doi:10.1016/j.asoc.2017.01.008), CKGSA (Mittal et al., IC3 2016, doi:10.1109/ic3.2016.7880252).
**"GSA-NGC" is UNVERIFIABLE** [verified absence in Crossref/OpenAlex] — do not put it in the protocol; if the
collaborator means a specific variant, get the exact reference first.

### 2.6 Sources

Superformula/math: doi:10.3732/ajb.90.3.333 · doi:10.1371/journal.pone.0029324 · doi:10.3390/sym14122475 ·
Ath 4.8.2 User Guide (https://at-horns.eu/release/Ath-4.8.2-UserGuide.pdf, §4.1.1, §4.1.3, §6.4.2, p.18) ·
at-horns.eu/core.html · HornLab mesher `docs/config-schema.md` + `tests/fixtures/ath_import/ath-v2026-09a/` ·
OS-SE paper (https://at-horns.eu/release/OS-SE%20Waveguide.pdf) · R-OSSE rev7
(https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf).
Mouth/theory: Geddes "What is a Waveguide?" (gedlee.com) · Makarski RWTH 2004 (HOMs at the driver mouth) ·
Kolbrek 2013 (rectangular-section modes, hdl.handle.net/11250/2370815) · Dong, Doc & Félix JASA 155:2270 (2024),
doi:10.1121/10.0025389 · Keele via Wikipedia "Horn loudspeaker" (coefficient UNVERIFIED).
Prior art: github.com/rafaelst00/Waveguide_PSO · doi:10.1109/tap.2025.3616764 (QPSO supershape antenna) ·
doi:10.1109/jrfid.2024.3396333 · doi:10.1007/s00158-018-2034-z (Norato).
Bake-off: arXiv:1605.03560 (COCO) · arXiv:2007.03488 (benchmarking best practice) · arXiv:2002.09227 (statistical
tests survey) · doi:10.1016/j.swevo.2011.02.002 (Derrac tutorial) · arXiv:1912.09237 (IOHprofiler) ·
iohprofiler.github.io/IOHanalyzer · facebookresearch/nevergrad (optimizerlib.py verified) ·
facebookresearch.github.io/nevergrad/benchmarking.html · doi:10.1111/itor.12001 (Sörensen).
GSA: doi:10.1016/j.ins.2009.03.004 · doi:10.1016/j.swevo.2018.02.018 · arXiv:2205.06770 ·
doi:10.1007/s12046-017-0674-0 · doi:10.1016/j.ins.2023.03.138 · arXiv:1706.03608 · arXiv:2101.06630 ·
himanshuRepo/Gravitational-Search-Algorithm (canonical port) · NiaOrg/NiaPy gsa.py ·
doi:10.1016/j.ijepes.2011.08.012 · doi:10.1016/j.scient.2011.04.003 · doi:10.1016/j.asoc.2017.01.008 ·
doi:10.1109/ic3.2016.7880252 · doi:10.1038/s41598-022-24250-1.
CMA-ES: doi:10.1162/106365601750190398 · arXiv:1604.00772 (§B.5) · doi:10.1162/evco_a_00244 (budgets) ·
doi:10.1145/1570256.1570333 (BBOB) · github.com/CMA-ES/pycma.

---

## 3. Design decisions this plan settles (the executor does NOT re-open these)

| # | Decision | Value/rule |
|---|---|---|
| D1 | Gcurve type | `gcurve_type: 2` (superformula). Superellipse (type 1) is already searched elsewhere — P6a is type 2 only |
| D2 | Symmetry count m | Fixed per catalog variant, integer only: **m ∈ {4, 8, 12}** (three variants); m1 = m2 = m (v1 never searches m1 ≠ m2) |
| D3 | a/b | `gcurve_sf_a` fixed at 1.0; search `gcurve_sf_b ∈ [0.6, 1.6]` |
| D4 | Exponents | search `gcurve_sf_n1 ∈ [0.8, 12]`, `gcurve_sf_n2 ∈ [1, 16]`, `gcurve_sf_n3 ∈ [1, 16]` |
| D5 | Position/scale | search `gcurve_dist ∈ [0.3, 0.8]` (fraction of L where the curve engages; canonical example 0.5); `gcurve_width_mm` anchored to the owner brief's envelope: lo = 0.7×, hi = 1.1× the envelope max width (filled in at config-authoring time from the brief — a formula, not a constant) |
| D6 | Degeneracy guard | deterministic rejection (**new marker kind `invalid_gcurve`**, same failure-cache mechanics as `invalid_envelope`) when `n1 < 2 AND max(n2, n3) > 10` |
| D7 | Curvature guard | reject when min radius of curvature (numeric, 720-point φ grid, polar formula κ = (ρ²+2ρ′²−ρρ″)/(ρ²+ρ′²)^{3/2}) < 0.5 × the config's mouth resolution |
| D8 | Mesher guard compliance | configs never combine gcurve with throat stretch (`s1`/`s2` = 0), never set `rot`/prefix with gcurve, never use gcurve on R-OSSE (all three are mesher refusals — encode in the template + a validation test) |
| D9 | Angular resolution | `angular_segments` 100–120 per Ath practice; the exact value inside that band is set by the dof-cap probe (step 9 of WP-P6a-1) — if the probe exceeds caps, first reduce mouth/thumb resolution within the epw rule, then fall back to 100, then STOP and log |
| D10 | Seeds | every campaign variant starts from 3 hand-picked seed shapes (canonical example, fixture-like, near-circle), i.e. 3 configs per m-variant → ≤9 configs total, all in `examples/superformula/` |
| D11 | Campaign tier | screen (existing 12-point grid group — no new named grid group needed) → owner brief verify → dense finalist resonance check (W2 machinery if landed; else the WP4 `verify_points_per_octave` grid as the in-band refinement) → compare + report + STEP |
| D12 | GSA implementation | our own module `hornlab_search/search/gsa.py` (~120 lines), mirroring `search/cma.py` seams: unit-box normalization via `DesignSpace.denormalize`, budget = non-cached evaluations only, seed counts, resume = cache replay, `MAX_CONSECUTIVE_SOLVE_FAILURES` semantics identical, same ndjson/run-dir writers |
| D13 | GSA config | switched on by `search: {algorithm: gsa}` + `search: {gsa: {n_agents, g0, alpha, kbest_start_frac, kbest_end_frac, eps}}`; defaults `n_agents: 20`, `g0: 1.0`, `alpha: 20.0`, `kbest_start_frac: 1.0`, `kbest_end_frac: 0.02`, `eps: 1.0e-10`; N and g0 re-picked by the WP-P6b-2 tuning stage and their values reported |
| D14 | Bake-off arms | `cma` (production config incl. post-WP11 restarts), `gsa`, and `lhs` (Latin-hypercube random sampler, ~30 lines inside the harness — not a `search.algorithm`); (1+1)-ES optional/out-of-scope v1 |
| D15 | Budgets | max budget 400 evals/run, sliced at {100, 200, 400} (anytime trick); production comparison budget = 200 |
| D16 | Matrix | 3 families (a 2-knob exponential config; an existing 5–8-knob owner-brief family, chosen at Wave 0; superformula m=4) × arms {cma, gsa, lhs}; seeds: 30 on surrogate-backed Stage B when valid, 10–15 on real-GPU Stage A (owner may trim; power honesty stated in the report either way) |
| D17 | Decision rule (pre-registered) | GSA replaces CMA-ES as default ONLY if ALL hold: higher median final gap-closed at B=200; Holm-corrected Wilcoxon rank-sum p < 0.05 across families; Â12 ≥ 0.64; feasible-best rate not worse; beats `lhs` at equal budget; on ≥ 2 of 3 families. Otherwise CMA-ES stays, and the outcome is recorded in `NEXT_DEV_PRIORITIES.md` + §2.5 addendum honestly ("competitive only at ≥N× budget" is a legitimate reported result) |
| D18 | Data model | one JSONL row per evaluation: `run_id, algo, algo_version, seed, shape_family, dim, eval_idx, objective, feasible, penalty_term, wall_s, x_vector_hash, params_json` — append-only, resumable, the single table every plot groups over |
| D19 | GUI, P6a | mouth-outline polar preview on run pages (pure math from the design's gcurve params — the GUI adds no physics); Typologies/Launch pick the new catalog entries up automatically; Evolution player untouched |
| D20 | GUI, P6b | `#/bakeoff/<id>` view reading the harness output: race chart (bold median + IQR ribbon + faint per-seed lines, log-x evals), final-best ECDF, box/violin per budget slice, the budget-normalized table; statistics as a footnote/table, never as dashboard headline |

---

## 4. Work packages (exact steps)

### WP-P6a-1 — design validity + configs + catalog (CPU only; P6a lane)

Steps:
1. Read `AGENTS.md`, `docs/plan/01_CONTRACTS.md` (contracts unchanged — verify), this §2.1 table, and
   `search/cma.py`'s normalization contract.
2. Add the D6 degeneracy guard + D7 curvature guard to the gcurve validation in `hornlab_search/design/`
   (where the FREEFORM envelope-overshoot estimate and `_GFX` validation live — read
   `families.py` first; the marker kind is `invalid_gcurve`, deterministic, failure-cached by design+mesh key,
   mirroring `invalid_envelope` mechanics). Both guards are pure functions of the params — no meshing.
3. Write `tests/test_design_gcurve_guard.py`: degeneracy rule, curvature rule, m-integer rule, m1 = m2 rule,
   mesher-guard combos (D8), and a numeric symmetry assertion: for m ∈ {4,8,12} the sampled outline
   r(φ) satisfies max|r(φ) − r(φ + π/2)| / max r < 1e-9 for m = 8 only with a=b,n2=n3 OR m ≡ 0 mod 8 — i.e.
   assert quarter-mirroring holds for every shipped seed config.
4. Author `examples/superformula/osse_sf_m4_a.yaml` … `_m12_c.yaml` (9 configs): family OSSE;
   `gcurve_type: 2`; all D2–D5 bounds; seed_params from the three reference shapes (canonical
   `a=1, b=0.863(=0.82/0.95), n1=0.8, n2=7, n3=1.9, dist=0.5`; fixture-like `n1=3, n2=7, n3=2`,
   `b=0.8/1.3×a`-style ratios from sf1/sf2; near-circle `n1=n2=n3=2, b=1`); `s1=s2=0`; `rot_deg=0`;
   `solve`/`mesh` blocks **copied verbatim from the owner-brief's existing family config** (same backend, caps,
   grid, balloon — this is what keeps record groups compatible); `distance_m` per the M3 decision state.
5. Add catalog entries for the three m-variants (`examples/catalog.yaml`) with screen/compare budgets from the
   existing `campaign.budget_for_tier` machinery.
6. Run the offline suite + compileall; paste counters.

Acceptance: guards test green; the 9 configs load via `hornlab-search families --brief <owner brief>`; all
seeds pass the guards (estimate-check: no seed is invalid_gcurve).

### WP-P6a-2 — GPU screen → verify → gate → exports (serial GPU; owner-approved)

Steps:
1. `hornlab-gpu-job` preflight (clean Julia, VRAM near idle, doctor green).
2. Mesh-only probes first (`--mesh-only` pattern): every seed config's dof count at the screen spec — record
   against the caps (D9 fallback ladder if over).
3. Screen campaigns: the three m-variants × the 3 seed configs each, budget 200, via the existing campaign
   mechanism; warm worker reuse is legitimate inside a campaign.
4. For each m-variant's best: `verify --brief <owner brief>`; then the D11 dense/resonance refinement; then
   `compare` (m-variant best vs the owner family's current best on the same brief) and `report`; STEP export of
   the top design per m.
5. Honest 12 kHz discipline: if band_hi > f11, the f11 = 7,914 Hz caveat line is printed with every number
   (existing machinery).
6. Evidence: `docs/evidence/P6A_SUPERFORMULA_2026-XX-XX.md` — every number byte-checked per `hornlab-evidence`.

Acceptance: screen runs finish (failures recorded, not hidden); best-so-far comparison table in the evidence
doc; whatever the J outcome, the run is a RESULT — the campaign fails only if the machinery does not run or the
numbers are not honest.

### WP-P6b-1 — `search/gsa.py` + config switch (no GPU; P6b lane)

Steps:
1. Read `AGENTS.md`, `search/cma.py` completely (normalization, budget, failure, resume semantics), `config.py`.
2. Implement `gsa.py` per D12/D13 + §2.5's canonical loop and all ten pitfall requirements. Same run-dir/ndjson
   writers as `cma.py` (reuse, do not fork). Add `algorithm: gsa` to the `search.algorithm` switch (S1 outcome
   decides whether the switch already exists).
3. `tests/test_search_gsa.py` — the 8 minimum tests (§2.5: equal-fitness masses; duplicate-agent finite force;
   Kbest schedule monotone with floor ≥ 1; G(t) = G0·e^(−αt/T) endpoints; 2-agent 1-D hand-calculated force;(
   bounds: inside box, velocity zeroed at walls; same-seed bitwise-identical trajectory; plus the guard
   behaviors) + 3 integration tests with a fake evaluator (offline, fast).
4. `config.py`: `search.gsa.*` keys with D13 defaults + validation (n_agents ≥ 2; 0 < kbest_end_frac ≤ kbest_start_frac ≤ 1).
5. Offline suite + compileall; paste counters.

Acceptance: all tests green; a 20-agent × 60-generation offline run on a toy quadratic converges and is
seed-reproducible.

### WP-P6b-2 — the bake-off harness `tools/bakeoff/` + offline tuning (no GPU; harness lane)

Steps:
1. Harness per D14/D15/D16/D18: CLI `tools/bakeoff/run_harness.py --config <bakeoff.yaml>`; executes
   (family, algo, seed) arms through the **normal evaluate path** (same failure cache, same GPU lock; the GPU
   lanes of Wave P6-3 are serialized by the existing lock); writes the D18 JSONL; resumable (append + skip
   existing (run_id, eval_idx) pairs).
2. The `lhs` baseline: NumPy-only Latin hypercube in the unit box (no new dependency).
3. Offline tuning stage (pre-registered, reported in the evidence doc): on two toy landscapes (a smooth
   ill-conditioned quadratic; a multimodal function), sweep `n_agents ∈ {10, 20, 40}` × `g0 ∈ {0.01, 0.1, 1, 10}`
   at B = 400, pick per the production criterion (median gap-closed), and FIX the values for the GPU stages.
4. `tests/test_bakeoff_harness.py`: fake-evaluator end-to-end; resume replay; JSONL schema; LHS coverage.
5. Output contract: `runs/bakeoff_<id>/bakeoff.jsonl` + `bakeoff_summary.json` (per algo×family×budget: median,
   IQR, feasible-best rate, ERT/PAR10 to the three thresholds) — the file the GUI reads.

Acceptance: harness offline-green; tuning stage produces a documented parameter table; summary JSON schema
locked by test.

### WP-P6-GUI-1 — mouth-outline preview (GUI lane)

1. `gui/data.py`: pure function `guiding_curve_points(params, n=128)` from the design's gcurve keys (superformula
   evaluator in plain Python — the mesher's `sf()` is the formula, do not import mesher internals); served in
   `/api/run/<id>` as `guiding_curve: {phi[], r[], m, dist}` (absent for non-gcurve runs).
2. `static/`: small polar SVG on the run page (reuse `charts.js` stroke conventions; label "mouth outline m = …");
   a second trace overlays the brief's envelope where available.
3. `tests/test_gui_gcurve.py` following the `test_gui.py` fixture pattern; `node --check` parametrize gains the
   new static file.

Acceptance: offline tests green; a fixture run renders the outline in both themes.

### WP-P6-GUI-2 — the bake-off view (GUI lane)

1. Route `#/bakeoff/<id>`; `gui/data.py` + `server.py` read `runs/bakeoff_<id>/` (allow-listed, GUI reads only);
   new endpoint `/api/bakeoff/<id>`.
2. `static/bakeoff.js`: four panels per D20. Reuse the chart()/SVG helpers; no new runtime dependencies; 2D and
   dark/light themes pixel-checked via the `?theme=` override.
3. `tests/test_gui_bakeoff.py` (fixture JSONL); `node --check` gains `bakeoff.js`.

Acceptance: renders fixture data in both themes; GUI test suite green; no file outside the GUI lane's ownership
changed (tested).

### WP-P6b-3 — bake-off execution (serial GPU; branch table)

| Branch | Condition | What runs |
|---|---|---|
| A | Phase-2 metric surrogate VALIDATED (its gates pass) | Stage B full matrix (30 seeds) surrogate-backed + Stage A real-GPU confirmation (10 seeds × 3 families × cma/gsa, B=200, `lhs` included) |
| B | Surrogate gates still failing (today's state) | Stage A real-GPU only: 3 families × {cma, gsa, lhs} × 10–15 seeds × B=400 sliced — sized with the WAVE P6-0 measured s/evals; owner may trim the matrix; report the power honestly |
| C | GPU budget unavailable | Stage B0 offline: the harness + tuning evidence exists; the GPU matrix is queued and the plan records the wait |

Execution rules: GPU lock serialization (`hornlab-gpu-job` recipe), fresh per-arm scratch cache dirs (the M2
lesson — caches are NOT lib-SHA-keyed), one measurement per process for anything quoted, verified shutdown,
evidence per `hornlab-evidence` (every quoted block byte-checked).

### WP-P6-4 — senior verification + decision recording

Independent senior pass: re-derive the guard math from §2.1; recompute the statistics from the JSONL; check the
decision rule was applied as pre-registered (D17); append the verdict to `NOTES_FOR_SENIOR.md`; update
`docs/CONTINUITY.md`, `docs/ISSUES.md`, `docs/INDEX.md`, `docs/CODE_MAP.md` (same-commit rule); record the D17
outcome in `docs/NEXT_DEV_PRIORITIES.md` P6 (checked off or annotated) and — if P6a produced record groups — in
the dataset notes. If GSA won anywhere, the change to a default STILL requires a second, explicit owner approval.

---

## 5. WAVE P6-1 dispatch prompts (verbatim; each executing agent begins by reading `AGENTS.md`, then its steps)

**Lane A (P6a):**
```
You own ONLY: examples/superformula/**, examples/catalog.yaml (append), hornlab_search/design/** (gcurve guards
only), tests/test_design_gcurve_guard.py, docs/evidence/P6A_*.md. Read AGENTS.md completely, then execute
docs/research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md §4 WP-P6a-1 steps 1-6 exactly. The design decisions
(D1-D11 in §3) are settled — do not re-derive or change them. Never invent a parameter name: the gcurve keys are
listed in §2.1 and must match hornlab_search/design/families.py and the mesher schema. Finish with compileall +
the offline suite (junitxml counters pasted). Blocked twice on the same error: stop, append NOTES_FOR_SENIOR.md.
```

**Lane B (P6b algo):**
```
You own ONLY: hornlab_search/search/gsa.py, hornlab_search/config.py (the algorithm switch + gsa keys),
tests/test_search_gsa.py. Read AGENTS.md completely, then search/cma.py completely — your budget, failure,
resume, and normalization semantics MUST mirror it. Execute §4 WP-P6b-1 steps 1-5. The ten pitfall requirements
of §2.5 are hard: each is a named test. Do not touch search/cma.py. Offline only; never start a GPU solve.
```

**Lane C (harness):**
```
You own ONLY: tools/bakeoff/**, tests/test_bakeoff_harness.py. Read AGENTS.md, then §4 WP-P6b-2. The data schema
is D18; the arms are D14; the tuning stage is pre-registered and its output table is part of the deliverable.
Offline only (fake evaluators). You do NOT execute the real bake-off — that is Wave P6-3.
```

**Lane D (GUI):**
```
You own ONLY: hornlab_search/gui/**, static/** (new files; edits to shared static files only where WP-P6-GUI-1/2
say exactly which lines), tests/test_gui_bakeoff.py, tests/test_gui_gcurve.py. Read AGENTS.md, GUI_PLAN.md
constraints (read-only data; no physics; 127.0.0.1 only; allow-listed endpoints), then WP-P6-GUI-1 and
WP-P6-GUI-2. Zero new runtime dependencies. Verify in both themes via ?theme= overrides. Offline tests only.
```
All four lanes background in parallel; zero file overlap (§0.1). Wave P6-2 starts only after Lane A's acceptance
pastes green; Wave P6-3 only after B+C are green and the owner has sized the matrix.

---

## 6. Checkpoints

| CP | Gate (pasted terminal output required) |
|---|---|
| CP-P6-0 | S1–S4 seam outputs pasted; measured s/eval table refreshed for the three bake-off families on the current card; guards/curve math reviewed |
| CP-P6-1 | Lanes A–D acceptances pasted (suites green; nothing outside owned files changed) |
| CP-P6-2 | Mesh-only dof table inside caps; three screen campaigns done; verify + dense-gate + compare outputs pasted; evidence doc byte-checked |
| CP-P6-3 | bake-off JSONL complete per the branch run; `bakeoff_summary.json` schema-locked; statistics computed and Holm-corrected; decision rule D17 applied verbatim |
| CP-P6-4 | Senior verdict appended; all docs updated in the same commit; D17 outcome recorded |

**Failing a physics expectation is a RESULT, not a failure.** The programme fails only if machinery does not run
or numbers are not honest.

---

## 7. Risks, failure modes, and what NOT to do

1. **Mesh refusals / dof blowups at high n2/n3** — expected; the guards (D6/D7) exist precisely so failures are
   deterministic and cheap; a high invalid rate per family is a finding to record, not a bounds change mid-run.
2. **The crippled-GSA trap** — never run GSA at canonical N=50/T=1000 on a 400-eval budget; the WP-P6b-2 tuning
   stage is mandatory before any GPU bake-off.
3. **Unequal budgets** — any comparison at unequal budgets is void; the anytime-slice trick is the only allowed
   budget accounting.
4. **Local-minima seeding trap** — never start a superformula campaign from a single random point (§2.3); the
   three hand-picked seeds are the mitigation.
5. **Quarter-symmetry hazard** — the numeric symmetry assertion (Lane A step 3) must be green for m = 8 before
   any m = 8 campaign; m = 4/12 (D2-symmetric) mouths are valid quarter candidates only because the symmetry
   planes hold — asserted, not assumed.
6. **Dataset hazards** — records use the EXISTING screen grid group (no new named group, no frozen-contract
   amendment); `objective_version`, excitation spec, traces-provenance machinery apply unchanged; never flip the
   objective version on a resume.
7. **Statistics traps** — no p-value without effect size (Â12); no Holm-free multiple comparisons; feasible-best
   reported separately from penalized best; pre-registration before the first GPU arm.
8. **Do NOT** implement a second GSA variant in v1; do not use NiaPy's variant as "the 2009 GSA"; do not name
   "GSA-NGC" in any config or doc (unverifiable); do not let the GUI imply a winner — it shows distributions and
   the stats table; do not put wall-clock time on any bake-off x-axis.
9. **Scope discipline** — if any step discovers a mesher gap (e.g. `gcurve_dist` interacting badly with the
   bisection), that is a `NOTES_FOR_SENIOR.md` finding and a possible mesher-fork item per `docs/FORKS.md` —
   never a silent local workaround in `.venv`.