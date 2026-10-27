# Sim vs. real horn: does ideal-source BEM behave like a built horn? (P12 research)

Written 2026-10-27 by the research lane, answering the owner's P12 question:
*"I don't want to be running these simulations if it isn't going to behave like it would if we
built one and tested it."* This is a literature/method review only — no solves, no scoring changes.
Labels: **[measured]** our own repo numbers, **[published]** external source, **[inferred]** my reasoning.

**Bottom line up front:** ideal-source BEM is a *good relative-ranking tool for pattern shape above
cutoff* and this is well supported in the literature. It is *not* a predictor of level, efficiency,
low-frequency loading, cutoff peaks, or distortion, and our current J actively hides that gap by
weighting `load` at 0 on most briefs and by normalising polars to on-axis. The fixes are mostly
cheap (re-score with loading on, tighten tolerances, add an absolute-level term, add a lumped driver
over the BEM throat impedance) and one is essential before another build decision: validate against
one measured horn.

---

## 1. How well does ideal/velocity-source BEM predict real polars and DI?

The consensus across the horn-sim literature is consistent and matches our own CP-7 results:
**the far-field pattern (polars, DI, beamwidth) above the horn's cutoff is predicted well; level,
loading, and sub-cutoff behaviour are not**, and are usually hidden by on-axis normalisation.

- **Pattern accuracy is good.** Panzer & Macey's BERIM study reports good agreement between simulated
  and measured directivity for both axisymmetric and general 3-D horns [published]. Kolbrek's BEM
  pages show OS-waveguide polar maps that behave as measured waveguides do (conical horns show the
  expected mouth-diffraction narrowing/midrange flare; OS is "far more constant") [published].
  Multiple diyAudio builders who print an Ath/ABEC design and measure it report agreement "very good"
  and that ABEC at modest resolution "matched reality well enough" for the polar comparison
  [published, anecdotal]. This is the regime our objective lives in, so the core use is defensible.
- **Where it fails.** (a) *Level and LF loading*: Kolbrek's horn BEM uses a constant 1 m/s throat
  velocity and states plainly that no driver is involved [published]; the horn-simulation review of
  Boundary Lab (issue #78) states the sharpest version of our own problem — normalising to 0 dB
  on-axis *masks* level and low-frequency loading error [published]. (b) *Throat/driver exit*: ABEC
  users note the real wavefront leaving a compression-driver exit is unknown, so sims are "seldom
  done much above 10 kHz" [published] — above the throat's first cross-mode the ideal uniform cap is
  wrong (our own P2/CP-7e note: f11 ≈ 5.7 kHz on the 1.4″ seed [measured]). (c) *Discretisation*:
  "numerical dispersion"/phase error grows with coarse meshes [published]; issue #78 estimates a λ/6
  rule ≈ 10 % frequency error ("~1.6 semitone smear") and cites 17 elements/wavelength for 1 % modal
  error, 6 for 10 % [published]. Our epw=6 is the 10 %-class mesh, and our own residual-risk note
  already flags that epw=6 above 2.5 kHz is unmeasured [measured]. (d) *Enclosure/baffle diffraction,
  wall vibration, 3-D-print wall roughness/porosity* are simply absent from a rigid-wall exterior BEM.
- **Our standing.** CP-7b put beat_cuda vs bempp_cpu at 0.039 dB and CP-7c put epw-6-vs-18 beamwidth
  within 0.29° / DI within 0.028 dB on a reduced band [measured]. So the solver is self-consistent;
  the open question is not solver noise, it is the *physics we chose not to model*.

## 2. How other tools treat the driver and loading

Everyone who predicts *level* (not just pattern) couples a driver model to the acoustic load:

- **Hornresp** — 1-D Webster/TL horn driven by the measured Thiele-Small driver with a complex-
  inductance model; it reports SPL, throat impedance, excursion, efficiency [published].
- **Akabak** — combines LEM (lumped T/S, chambers, phase plug) with BEM for radiation; its docs state
  the acoustic output power is proportional to the *real part* of the throat radiation impedance
  [published] — exactly the quantity our `load` term reads and mostly ignores.
- **ABEC / Ath** — BEM for the field, with a driver/"throat" source option and the ability to couple a
  lumped element; the common practice is still velocity/ideal source for *pattern* studies, driver
  coupling when *level* matters [published].
- **Boundary Lab (JWSound)** — a monolithic per-frequency FEM-BEM-LEM block solve with the driver's
  *dry* moving mass Mmd, so radiation mass is not double-counted; issue #78 flags that post-hoc
  coupling with Mms introduces 10-20 % LF error [published]. This is the state of the art for the
  "does it behave like a real one" question and is the model to emulate for a driver add-on.
- **Compression-driver interior** — Dodd & Oclee-Brown (AES 2008/2009, US8121330B2) model the
  diaphragm → phase-plug annular/radial channels → conical throat with FEM/BEM to suppress
  radial/throat modes [published]; a recent CutFEM study shows narrow phase-plug channels *require*
  a viscothermal (boundary-layer loss) model and that a lossless target is only matched once losses
  are included [published]. This is why a full driver interior is a research project, not a term.
- **Fidelity judged adequate for optimisation.** The field routinely optimises *shape/pattern* on an
  ideal source (that is what ABEC/Ath/our tool do) and treats driver coupling as a separate 1-D/LEM
  stage for level and loading. So our split is normal — provided the loading/level stage is not
  simply dropped, which on most of our briefs it currently is.

## 3. Loading and cutoff: what Re(z) tells you, and is our `load` term sensible?

**What throat loading means.** The normalised specific throat resistance Re(z)=Re(Z)/ρc is the
fraction of the ideal matched load the horn presents. Above cutoff a well-behaved horn drives Re(z)
toward 1; below cutoff the throat goes reactive and Re(z) collapses, so the driver moves air
inefficiently and its excursion rises for the same SPL [published, Kolbrek horn theory]. Classic
criteria: the **mouth circumference must be ≳ one wavelength at cutoff** for good loading
[published]; **Keele's CD rule** d = K/(Θ·f_Θ) with K ≈ 2.54×10⁴ m·deg·Hz sets where pattern control
is lost — every octave lower in control doubles the mouth, and every halving of coverage angle
doubles it [published]. Designers typically want Re(z) comfortably above ~0.5-0.7 across the passband;
a horn that is unloaded (Re(z) ~ 0.04-0.12, our J-winner at 500-830 Hz [measured]) will still *look*
perfect in on-axis-normalised polars while being nearly silent and highly distorting there.

**Loading ↔ real driver output.** Output power ∝ Re(Z_throat) [published, Akabak]; so an unloaded
throat means low efficiency, high excursion, and rising distortion — compression-driver 2nd-harmonic
rises as the air in the throat/phase plug is driven hard with little radiation resistance to damp it
[published, DEGA/ICA2019 distortion work]. This is precisely the behaviour our ideal source cannot
show and our scoring does not penalise.

**Is `mean_f max(0, z_min − Re z)` sensible?** The *shape* is fine (a one-sided hinge that only
penalises under-loading). Two real problems: (a) averaging over the whole band **dilutes a deep
sub-cutoff deficit** among many well-loaded points — a horn that is dead at 500 Hz but loaded above
1 kHz scores almost as well as one loaded throughout; (b) with `weight 0` on most briefs it does
nothing at all. **Recommended weighting/band per class** [inferred, from the criteria above]:

| Horn class | `load` weight | `z_min` | Band / rule |
|---|---|---|---|
| CD hi-fi waveguide | 0.3-0.5 | 0.5 | score from f0 up; pattern dominates, loading a guard-rail |
| PA horn to 400-600 Hz | 0.8-1.0 | 0.7 | score from f0 **down to a report-only 300-200 Hz solve**; penalise the deficit per-point, not band-mean |
| Low-reach | 1.0 | 0.7-0.8 | hard; consider a min-over-band or sub-f0-integral form, not a mean |

I would also change the aggregation from a band-mean to **max or a sub-f0 integral below the target
corner**, so a narrow dead zone cannot be averaged away.

## 4. Scoring honesty: critique of J, and what the preference literature says

- **cov is generous.** `err²/100` with tolerances 2.0 (A)/4.5 (B,C) means a "1 unit" miss is ~14°/21°
  RMS [measured]; a twinray V of 120° at 500 Hz still scoring 3.0 under the class-A mask is the
  symptom. For CD briefs, tighten toward 1-2 units and keep `cov_narrow_ratio` ≥ 2 (narrowing is the
  defect you most want to catch).
- **Masking below f0 is physically right but must be one-sided.** v4 already offers
  `cov_below_f0: one_sided` — a *wide* pattern below f0 is physics (free), a *narrow* one is a defect
  (scored). Use it on the PA/low-reach classes rather than the full mask.
- **On-axis normalisation is the core honesty gap.** Every metric is pattern-only, so a horn can win
  while being inefficient and unloaded. The literature backs pattern-metrics for *preference* but not
  for *realisability*: Toole/Olive and the Harman work find smooth, wide, **constant-DI** speakers
  (DI ~5-7 dB) are preferred in blind tests, and that early reflections should share the direct-sound
  spectrum [published] — this validates our DI/flatness/constancy terms as *preference* predictors.
  But preference ≠ "it will measure and play as simulated"; for that you need level + loading, which
  pattern metrics never contain.
- **Constant-directivity metrics.** Sridhar, Tylka & Choueiri, *Metrics for Constant Directivity*,
  AES 140th Conv., 2016 [published], derive five metrics and find **#4 standard deviation of the DI**
  and **#5 polar cross-correlation** best capture *both* definitions of constant directivity (pattern
  invariance and DI invariance). Our v4 already added `distd` (std of DI) — good, keep it and give it
  real weight on CD briefs; `dislope` only sees a straight-line trend and fights a true CD target, so
  down-weight it where `distd` is on. Consider adding polar cross-correlation (#5) as a report metric;
  the balloon is already stored.
- **Concrete recommended changes.** (1) Turn `load` on for all PA/low-reach briefs, scored from f0,
  aggregated as max/integral not mean. (2) Add an **absolute-level / efficiency** term fed by a lumped
  driver over the BEM throat impedance (next section) so J stops being level-blind. (3) Tighten cov
  tolerances and use one-sided-below-f0 on PA. (4) On CD briefs weight `distd`, down-weight `dislope`.
  (5) Keep `diag` for crease/pucker shapes — it reads directions H/V cannot, consistent with metric #1
  (contour-line Fourier analysis).

## 5. Validation plan

**A. Calibrate against published measured horns (no build needed).** Pick 2-3 with geometry *and*
measured polars/impedance:

| Candidate | Why | Compare |
|---|---|---|
| An **Ath-generated waveguide with a builder's printed+measured polars** (diyAudio) | geometry is reproducible in our mesher family; many measured examples exist | H/V polars, DI, beamwidth vs freq |
| **JBL 2380/2380A** (published CD horn, measured polars widely available) | canonical CD horn, pattern-control corner known | beamwidth-vs-freq, f_Θ against Keele's d=K/(Θf) |
| A **Geddes OS/OSSE** design (our family already meshes OSSE) | our native family; Geddes published DI behaviour | DI constancy, throat impedance shape |

Procedure: mesh the published geometry, solve on our verify grid (to 300 Hz), compare **(i)** polars/
beamwidth, **(ii)** DI-vs-freq, **(iii)** throat Re(z) shape, **(iv)** on-axis FR *after* a driver
model is added. **Acceptance thresholds [inferred, aligned to our noise floor and issue #78]:**
beamwidth within ±5° (±3° in the presence band), DI within ±1 dB, pattern-control corner f_Θ within
~1/6 octave, Re(z) qualitatively tracking (loaded/unloaded transition within ~1/3 octave). If polars
pass but level/FR fail, that is the expected ideal-source signature and tells us exactly what the
driver model must add.

**B. Cheap driver model (the key addition).** Couple a **lumped compression-driver equivalent circuit
(Bl, Mmd, Cms, Rms, rear-cavity compliance, phase-plug/throat compliance) to the BEM throat
impedance** already computed per frequency — the Akabak/Hornresp/Boundary-Lab pattern. This predicts
on-axis level, sensitivity/efficiency, and excursion with *no new BEM cost* (it reuses `impedance`
from the SolveResult). Use **Mmd not Mms** (issue #78's double-counting warning). This alone converts
our normalised polars into a predicted FR and an absolute-level/efficiency term. A full phase-plug
interior (Dodd/Oclee-Brown FEM + viscothermal losses) is **out of scope** — it is a separate research
effort and not needed to rank shapes.

**C. Build-and-measure the finalists.** Print 1-2 finalists (PLA/PETG, 4-6 perimeters, gyroid infill,
resin-backed for wall stiffness) and measure: **(i)** H/V polars on a turntable (gated/outdoor or
large roundover baffle), **(ii)** throat/driver impedance and near-field FR, **(iii)** distortion vs
level. **Pitfalls [published]:** baffle-edge diffraction and mic-boom reflections corrupt the ≥60-90°
data — use a large roundover (sonotube + foam) and align the rotation axis to the baffle as in the
sim; keep the compression-driver exit-wavefront caveat in mind above ~8-10 kHz; thin printed walls
flex and buzz. **The decisive experiment:** print the "J-winner" *and* a "scoring-honest" winner
(loading on, level term on) and measure both — if J predicted reality, the J-winner wins; if the
honest winner measures better where the J-winner is unloaded, the scoring change is vindicated.

## 6. Bottom-line recommendation (ranked by value/effort)

**Is ideal-source BEM adequate for relative ranking of shapes?** Yes for *pattern/DI above cutoff*,
**only if loading and cutoff are scored properly and level is not ignored.** It is not adequate as-is,
because two of our winners are essentially unloaded yet top the board — the model and scoring, not the
solver, are the problem.

What must change before more large campaigns, ranked:

1. **(free, do first) P12a re-score** cached responses with `load` on (weight 0.5-1.0, `z_min` 0.7,
   scored f0-up, max/integral aggregation) and a stricter-cov variant; show the rank change. Zero GPU.
2. **(cheap, high value) Add the lumped driver over the BEM throat impedance** → predicted FR,
   efficiency, excursion, and an absolute-level term. Reuses stored `impedance`; no new solves.
3. **(cheap) Validate against one published measured horn** (§5A) to put an error bar on the pattern
   claim and confirm the driver model reproduces a real FR.
4. **(config) Turn `load`/level on for every PA and low-reach brief; weight `distd`, down-weight
   `dislope` on CD briefs; use one-sided-below-f0.**
5. **(moderate) A report-only 200-300 Hz solve** on finalists so cutoff peaks and loading are visible,
   not interpolated through (ties to P4a/W2).
6. **(when ready) Build-and-measure two contrasting finalists** (§5C) — the real decision gate.

Until #1-#3 are reviewed, the P12 gate should hold: no new multi-hour campaign whose J inherits the
level-blind, loading-0 caveats.

---

## Source table

| Title | Author(s) | Year | URL | Supports |
|---|---|---|---|---|
| BEM Simulations – Horns | B. Kolbrek | n.d. | https://kolbrek.hornspeakersystems.info/index.php/horns/bem | §1 constant-velocity source, no driver; throat-impedance numerical artifacts; LF measured "almost spot on" |
| Horn Theory: An Introduction (audioXpress) | B. Kolbrek | 2008 | https://www.grc.com/acoustics/an-introduction-to-horn-theory.pdf | §3 cutoff, mouth circumference ≥ λ, throat resistance→ρc |
| Simulation of the Acoustic Field of a Horn Loudspeaker by the BEM–Rayleigh Integral Method (BERIM) | J. Panzer, P. Macey | ~2009 | https://www.researchgate.net/publication/235788684 | §1 good sim-vs-measured directivity, axisymmetric and 3-D |
| Experimental and Theoretical Investigation of an Unusually Shaped Horn | J. Panzer, P. Macey | n.d. | https://audioxpress.com/article/development-design-experimental-and-theoretical-investigation-of-an-unusually-shaped-horn | §1/§2 driven-horn BEM/FEM vs measured SPL + radiation impedance |
| Evaluation of Boundary Lab vs horn-simulation (issue #78) | timini/horn-simulation | 2024 | https://github.com/timini/horn-simulation/issues/78 | §1/§2 on-axis normalisation hides level+LF loading; Mmd vs Mms; 17 el/λ (1%) / 6 (10%); monolithic FEM-BEM-LEM |
| Acoustic Horn Design the Easy Way (Ath4) thread | diyAudio (fluid, tmuikku, et al.) | 2019- | https://www.diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/ | §1 Ath/ABEC sim vs printed measured "very good"; seldom >10 kHz; numerical dispersion |
| 2-way waveguide build / ABEC modelling thread | diyAudio (fluid) | 2020- | https://www.diyaudio.com/community/threads/2-way-waveguide-speaker-build-abec-modelling.357792/ | §1 ABEC "matched reality well enough"; 5-10 mm element compromise |
| Designing a Three-Way Column Loudspeaker Using Akabak | audioXpress | n.d. | https://audioxpress.com/article/speakers-designing-a-three-way-column-loudspeaker-using-akabak | §2 LEM driver (T/S) + BEM; output power ∝ Re(Z_throat) |
| New Methodology for Phase Plugs with Concentric Annular Channels; Radial Channels | M. Dodd, J. Oclee-Brown | 2008/2009 | https://www.researchgate.net/publication/292662389 ; /355098042 | §2 compression-driver diaphragm/phase-plug FEM/BEM modelling |
| A better compression driver? CutFEM 3-D shape optimization with viscothermal losses | (arXiv 2403.17963) | 2024 | https://arxiv.org/abs/2403.17963 | §2 narrow phase-plug channels need thermoviscous loss model; lossless inadequate |
| Understanding Horn Directivity Control | C. Hughes (Excelsior Audio) | 2010 | http://excelsior-audio.com/Publications/Understanding_Horn_Directivity.pdf ; https://audioxpress.com/article/Understanding-Horn-Directivity-Control | §3 Keele d=K/(Θ·f_Θ), K=2.54×10⁴; octave↓ control = 2× mouth |
| Metrics for Constant Directivity | R. Sridhar, J. Tylka, E. Choueiri | 2016 | https://3d3a.princeton.edu/publications/metrics-constant-directivity | §4 five CD metrics; std-DI (#4) + polar cross-corr (#5) best |
| Directivity in Loudspeaker Systems | E. Geddes | n.d. | http://www.gedlee.com/Papers/directivity.pdf (cert issue; see gedlee.com) | §1/§4 OS waveguide constant DI rationale |
| Interpreting "Spinorama" Charts; Toole room-calibration | Sausalito Audio; F. Toole | 2018; — | https://www.sausalitoaudio.com/wp-content/uploads/2018/07/Interpreting-Spinorama-Charts.pdf ; https://www.linkwitzlab.com/Toole-Room%20calibration.pdf | §4 constant DI ~5-7 dB preferred; reflections share direct spectrum |
| Evaluation of Non-linear Distortion in Compression Drivers (ICA 2019) | DEGA/ICA | 2019 | https://pub.dega-akustik.de/ICA2019/data/articles/000129.pdf | §3 distortion sources vs loading/compression |
| 3-D printed waveguide measurement threads; MTG waveguide shootout | diyAudio; MTG Designs | — | https://techtalk.parts-express.com/forum/tech-talk-forum/1287600-3d-printed-waveguides ; https://www.mtg-designs.com/tips-tricks-tests/waveguide-shootout | §5C baffle diffraction, mic-boom reflections, roundover fixes |

**Not verified / not found:** gedlee.com directivity.pdf (TLS cert mismatch, not fetched this pass);
the Panzer/Macey IOA proceedings PDF (404); exact 2nd-harmonic numbers from the ICA2019 distortion
paper (PDF not machine-readable) — the distortion-vs-loading direction is from the title/abstract and
general horn theory, not a quoted figure.
