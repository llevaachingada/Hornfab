# KH-002 Throat-region H/V asymmetry: how asymmetric coverage is established near the throat

Date: 2026-11-18. Scope: round 1"-1.4" exit, asymmetric brief (e.g. 90 x 40 deg).
Labels: [primary] fetched source text; [forum/real-world] forum/search-summary or trade article;
[inferred] my reasoning, not stated by a source; [disputed] sources conflict or evidence is thin.

Evidence limits (read first):
- Fetched in full and read: Batik "OS-SE Waveguide.pdf" (2020), Ath 4.7.0 User Guide, US7068805 (Geddes, via fetch summary),
  audioXpress "Understanding Horn Directivity Control" (via fetch summary).
- diyAudio pages returned a bot-check on direct fetch; forum claims below come from WebSearch result summaries only,
  not read in the original. Treat as weak.
- Keele AES 1038 PDF is a scan; text not extractable. Keele patent 4071112 fetch returned 403. Keele claims here are
  from search snippets only.
- R-OSSE equations were NOT retrieved (only forum snippets). Do not cite R-OSSE formulas from this note.
- Geddes AES papers (1989, 1993) not fetched; cited only as references listed in Batik's PDF.

## 1. Primary construction laws: what sets H != V near the throat

### 1.1 ATH OS-SE (Batik) [primary]
Profile, for each azimuth phi (Eq. 5 of the PDF; surface is r(z, phi)):
  r(z) = sqrt( k*r0^2 + 2*k*r0*z*tan(a0) + z^2*tan^2(a) ) + r0*(1-k)
         + (s*L/q) * [ 1 - (1 - (q*z/L)^n)^(1/n) ]
- r0 throat radius; a0 throat opening half-angle; a nominal coverage half-angle; k throat expansion factor
  (k=1 pure OS hyperbola, k=0 cone r0+z*tan(a)); s flare amount; n superellipse exponent (how far from throat the
  termination becomes effective); q truncation (0.99-1.00); L length.
- Batik states explicitly that "the OS-SE profile parameters may vary around the device, i.e. not necessarily being
  axisymmetric" and surface is general r(z, phi). [primary]
- User Guide 2.1.2: every "ex" (expression) parameter may depend on azimuth p (phi), e.g.
  `Coverage.Angle = 40 + 10*cos(p)^2`. Doc example: `Coverage.Angle = 45 - 10*sin(p)^2` "made the mouth elliptical by
  reducing the vertical coverage angle". Items of type ex include Throat.Angle, Coverage.Angle, OS.k, Term.s, Term.n,
  Term.q, Length. [primary]
- Key consequence for near-throat control [inferred, from the formula]: in Eq. 2/3 the hyperbola's asymptotic slope is
  tan(a), and the throat slope is tan(a0). If only a(phi) varies and a0, k are constant, all azimuths start with the
  SAME throat slope and diverge only through the z^2 tan^2(a) term. Near z=0 the z^2 term is negligible relative to
  2*k*r0*z*tan(a0), so H/V differences are second-order close to the throat and become visible only once
  z*tan(a) is comparable to r0*k*tan(a0)-scale terms. Hence a(phi)-only asymmetry is a "soft, gradual" divergence,
  not a throat-origin one. To make H and V differ at z~0 you must also vary a0(phi) and/or k(phi).
- Throat angle: a0 must equal driver exit half-angle (User Guide: Throat.Angle "half the included angle"). The OS-SE page
  says the formula sets throat opening angle to match a compression-driver exit. [primary]
- Zero-control identity [primary/inferred]: with a, a0, k, s, n, q independent of phi, the surface is axisymmetric;
  k=0 gives a cone; so H=V reduces to the round parent exactly.
- Caveat: the guide's own demo (a=45-10 sin^2 p, Term.s varied with sin(2p)^4) varies parameters smoothly in phi, but the
  guide gives no measurement of how well the resulting polar pattern tracks the nominal a(phi). [inferred] The nominal
  coverage is a design intent, not a guarantee.

### 1.2 Guiding curve (ATH) [primary]
User Guide 2.1.3: a closed "guiding curve" (superellipse or superformula) at distance GCurve.Dist from the throat
(fraction of L if in <0,1>, else mm); ATH solves the coverage angle per azimuth so each profile passes exactly through
the curve. GCurve.AspectRatio (height/width), GCurve.SE.n (>=2), GCurve.Width, GCurve.Rot. This is the nearest
shipped analogue of a "section exponent + aspect" control, but pinned at ONE axial station, not a ramp from the throat.
[inferred] Choosing GCurve.Dist small (near throat) gives near-throat divergence but the cross-section there is only a
few mm bigger than the driver exit, so the solved a(phi) becomes extreme.

### 1.3 ATH morph [primary]
Batik section 5 + User Guide 4.1.2:
  for z < zf: r_m = r(z,phi)    (fixed part, untouched)
  for z >= zf: r_m = r(z,phi) + ((z-zf)/(L-zf))^gamma * (rM(phi) - r(L,phi))
  gamma >= 1 (Morph.Rate; gamma=1 gives an abrupt slope change at zf; default 3).
- Properties: r_m(0,phi)=r0 and r_m(L,phi)=rM(phi). Morph.FixedPart = zf/L (0 = start at throat). Targets: rounded
  rectangle (Morph.CornerRadius default 35 mm) or circle; Morph.AllowShrinkage prevents the mouth shrinking.
- It is a radial blend of a raw axisymmetric-ish surface toward a target mouth outline: the added term is zero at zf and
  grows as a power of normalized length. With FixedPart=0 and gamma=3 the added displacement is ~(z/L)^3, so
  at z/L = 0.25 only ~1.6% of the mouth correction is applied. [inferred, arithmetic from the formula]
  So default morph is also a late departure from round, even though it "starts at the throat".
- User Guide demo: morph to rounded rectangle with FixedPart=0.0, Rate=3 on a superformula raw shape. [primary]
- Morph does not add a throat-slope term, so it cannot by itself set an H/V difference in the throat angle. [inferred]

### 1.4 Geddes OS and the Bi-Spheroidal patent [primary for patent text via fetch summary]
- Batik credits OS waveguide to Freehafer (JAES 1940) and Geddes (JAES 1989, 1993; Audio Transducers 2002). [primary]
- US7068805 (Geddes): "each cross section of a true OS waveguide would be round"; making the mouth elliptical is a
  workaround that gives only "a twenty to thirty degree difference in the radiated polar angles". [primary]
  This is the patent's own criticism of elliptical-mouth OS for wide aspect briefs (90 vs 40 is a 50 deg difference).
- Proposed fix: Bi-Spheroidal = elliptic-cylinder (EC) section at the throat (finite cylinder section from a rectangular
  source) joined to a prolate spheroidal (PS) section whose cross-sections are everywhere rectangular and whose two wall
  angles are uncoupled ("the two angles of the walls of a PS waveguide are uncoupled"). [primary]
- The patent says join precision "has never been determined" and is done graphically; round drivers feed the rectangular
  throat via a gradual transition "so long as the same cross sectional areas are maintained or grow at a slow rate".
  [primary] Implication: Geddes' own answer to "how do you get H != V" is a rectangular/slot throat region, i.e. H/V is
  established at the throat, not the mouth. [inferred]
- [disputed/unverified] The patent's claim of only 20-30 deg difference is Geddes' own assertion; no measurement set was
  read. Also a search summary says Geddes described an elliptic-cylindrical waveguide that "needs a planar rectangular
  section wave at its throat"; no commercial production was evident (as cited by another patent, US6581719). Not read in
  full.
- [forum/real-world] A search summary of the diyAudio Geddes thread says the OS equation takes only throat diameter,
  initial throat angle, coverage angle (page 155 not readable). Weak.

### 1.5 Keele / JBL / EV / Altec / Danley / Le Cleac'h [mostly unverified]
- Keele AES 1038 (1975, "What's so sacred about exponential horns?") and Keele patent 4,071,112 (rectangular cross-
  section giving wider horizontal than vertical beamwidth): existence and gist from search snippets only.
  [forum/real-world; not read]
- audioXpress trade article [forum/real-world, read via summary]: H and V difference comes from mouth dimension in each
  plane relative to coverage angle; loss frequency scales ~ inversely with coverage angle and mouth dimension;
  12" x 6" 90 x 45 horn loses vertical control ~3.7 kHz and flips below ~2 kHz.
  Says nothing about throat-region shaping.
- JBL Progressive Transition, Altec Mantaray, EV CD horns, Danley Synergy, Le Cleac'h: NOT retrieved. Do not
  claim specifics. [inferred] Commercial CD horns of this era commonly have rectangular/slot-like sections close to the
  throat (the diffraction slot lineage) but I did not verify with sources here.

### 1.6 R-OSSE [forum/real-world, unverified]
Search snippets: R-OSSE has parameters R, r0, a0, a, k, r, b, m, q; a poster says it is a complete analytic description
including rollback and that it is "tough to affect curvature quite near the throat with R-OSSE". Formula not read.
[disputed] one poster also says OSSE gives more control than R-OSSE for optimization. Action: fetch R-OSSE doc before
relying on it.

## 2. Round-to-ellipse / superellipse / rounded-rectangle transitions

What the sources say:
1. ATH has two distinct mechanisms [primary]: (a) per-azimuth profile parameters (the surface is a polar function
   r(z,phi), so the section shape at every z is whatever those parameters produce; it is naturally round at z=0 because
   r(0,phi)=r0 for all phi, see Eq. 5 at z=0 with k=1: r=r0); (b) morph to a rounded-rectangle mouth.
2. Throat continuity: r(0,phi)=r0 independent of phi is built in. Wall slope at z=0 is tan(a0) in every azimuth unless
   a0 is made azimuth dependent. Matching a driver exit: a0 = exit half-angle. Wavefront curvature matching (flat
   vs spherical) is determined by a0 and k; a0=0 is flat wavefront for the pure form. [primary]
3. Geddes patent: rectangular throat with area held constant or slowly growing when adapting from a round driver exit.
   [primary] This is the only fetched source that addresses the round-to-rectangular throat adapter explicitly.
4. [forum/real-world, search summary] A poster says a correct smooth round-to-rectangular transition is "a lot harder to
   build" than round-to-round; another says Mabat's older software allowed circular throat to square/ellipse/rectangle
   mouths. Weak, unattributed.

Where along the axis does the section depart from round?
- OS-SE, a(phi) only: departure ~ z^2 tan^2(a(phi)) term; with r0 = 12.7 mm (1" exit) and a0 ~ 7 deg, the
  cross-term 2 r0 z tan(a0) ~ 3.1 z; the z^2 tan^2(a) term at a=45 deg is z^2, at a=20 deg is 0.13 z^2.
  [inferred, arithmetic] The H-V difference grows as ~0.87 z^2 versus the common 3.1 z term: equal at z ~ 3.6 mm,
  dominant beyond. Verify numerically in the solver.
- Morph with gamma=3, FixedPart=0: departure is ~(z/L)^3 weighted (see 1.3). Late.
- Superellipse ramp (not in ATH): [inferred] section |x/a|^p + |y/b|^p = 1 with p ramped from 2 (ellipse) to
  target p~4-6 over z; common in generic loft tools, no source here.

## 3. What if H/V divergence starts only near the mouth

Sources and strength:
- Acoustic mechanism [forum/real-world, audioXpress]: pattern control is set by mouth dimension and wall angle in each
  plane; the narrow plane loses control at higher frequency (loss f ~ 1/(d * angle) style scaling per the article's Eq. 1-2).
  This is about mouth size, not about where the divergence starts. [inferred] They are not the same variable: you
  can have a mouth of correct size yet a wall that only reaches its final angle in the last few cm.
- [forum/real-world, search summary] a diyAudio poster: the wall angles of upper/lower walls make the vertical polar
  narrower toward the mouth of an elliptical or rectangular waveguide, with vertical control giving way first at lower
  frequencies. Another: "pattern flip" where V beamwidth exceeds H below a frequency; JBL PRX425 cited (H control down
  ~1350 Hz, V collapses ~3300 Hz). Unmeasured by me. [disputed: numbers not verified.]
- Geddes patent [primary]: a gradual (not late) match between EC and PS sections is necessary; "compromise between
  minimizing wall-angle discontinuities and letting the ellipse develop enough." Elliptical-mouth-only OS gives only
  20-30 deg H/V difference. Evidence that late/mouth-only asymmetry under-delivers, but it is the inventor's claim.
- [inferred, no direct source found] If the V wall is parallel to a round parent's wall until the late break, the
  waveguide is launching a ~H=V wavefront with the wide-angle parent pattern; the narrow plane then has to be narrowed
  by a short, steep late section. Late curvature change tends to cause (a) a pattern that narrows abruptly in the
  mid band (waist/"narrowing" at the frequency whose wavelength ~ the late-section length), (b) diffraction at a
  slope discontinuity or tight radius, (c) HOM excitation at the break. No measured/simulated dataset for this exact
  case was found in the fetched material.
- ATH guide note [primary]: Morph.Rate gamma=1 gives an abrupt slope change at zf, the guide's own warning against
  an abrupt break. Default 3 softens.
- Contrary evidence [forum/real-world, search summary]: one poster suggests elliptical-throat-to-flare with round mouth
  (varying mouth radius) could avoid pattern flip; another says elliptical beats rectangular. Opposite emphasis from
  Geddes, partly different goal (off-axis smoothness). [disputed]
- Pattern 3 limit [primary-inferred]: diffraction/size limits are fundamental. audioXpress: "Small horns simply can't yield
  small coverage angles at low frequencies"; a 40 deg V at 1 kHz needs a large V mouth regardless of throat shaping.
  Throat shaping fixes launch shape and onset, not the size-frequency law. [inferred from article]

Net: no source fetched quantifies waistbanding for late divergence. Mark as a gap; recommend a BEM sweep
(compare break start at z/L = 0.0, 0.25, 0.5, 0.75) before committing.

## 4. Recommended parameterization (inferred synthesis; verify with BEM)

Principle: keep ATH OS-SE as the axisymmetric parent and add azimuth dependence, because Batik's own formula supports
per-phi parameters and H=V collapses trivially to it.

Knobs, each with continuity/identity requirement:
1. Coverage half-angle a(phi) = a_V + (a_H - a_V) * cos^2(phi) (or a super-cosine, power m for flatter sides).
   Identity: a_H = a_V -> constant a. [primary form: guide examples use cos(p)^2 / sin(p)^2]
2. Throat half-angle a0(phi) = a0_V + (a0_H - a0_V) * cos^2(phi) (physically, a0 = driver exit angle, so a_H0 = a_V0
   unless a throat adapter is used). Identity: a0_H=a0_V. This is the knob that creates near-throat H/V difference;
   keep within what the driver/phase-plug exit tolerates. [inferred]
3. Throat expansion k(phi) (same cos^2 form). k<1 steepens early divergence; k=0 is conical. Identity: k_H=k_V.
   Use a small modulation only; large k(phi) shifts the throat curvature. [inferred]
4. Flare terms s(phi), n, q: s(phi) to fit the mouth outline; keep n and q constant to avoid discontinuities.
   Identity: s const -> axisymmetric flare. [primary examples vary s with sin(2p)^4]
5. Section exponent ramp (outside ATH): section |x/a|^e(z) + |y/b|^e(z) = 1, e(z) = 2 + (e_end-2)*S((z-z_s)/(L-z_s)),
   S a C1 smoothstep, aspect b/a ramped by the same schedule; z_s = ramp start. Identity: e_end=2 and b/a=1 -> circle.
   Continuity: S'(0)=0 so no slope kink at z_s. Throat: r(0,phi)=r0 for every phi. [inferred]
6. Aspect ramp start z_s as a fraction of L (analogue of Morph.FixedPart); gamma >= 2 (guide default 3); gamma=1 forbidden
   (abrupt slope change, per Batik). Identity: target outline = parent outline at L -> morph term zero. [primary form]
   Because (z/L)^gamma weights are tiny early, treat z_s=0, gamma~2 as "starts at throat"; larger gamma = late. [inferred]
7. Optional throat adapter: a short (3-8 mm) constant-area round-to-ellipse segment before the OS-SE profile
   (Geddes: constant or slowly growing area). Identity: adapter aspect=1 -> length 0. [inferred from the patent]

Suggested minimal set (5 numbers beyond the round parent): (a_H, a_V), (a0_H-a0_V) trim, aspect ramp start z_s, gamma.
Add section-exponent e_end only if a rounded-rectangle mouth is required.

Zero-control tests to implement: (i) a_H=a_V, a0 trim=0, k trim=0, e=2, aspect=1 reproduces r(z,phi)=r_OSSE(z) to
numerical tolerance; (ii) r(0,phi)=r0 for all phi; (iii) dr/dz at z=0 equals tan(a0(phi)) and equals driver exit
half-angle at phi=0 and 90; (iv) d2r/dz2 continuous at z_s.

Criticisms/risks:
- Azimuth interpolation between H and V (cos^2) is a convenience, not physics; diagonals (45 deg) are not
  guaranteed to behave. [inferred] Batik offers cos^12 etc. to reshape; no measurements of the effect cited.
- Geddes says the elliptic-OS type approach under-delivers for large H/V ratios. Do not assume a(phi) variation alone
  gives 90 x 40 patterns; expect need for the throat-region knobs or a rectangular-ish section. [primary claim, unverified]
- Wall-slope mismatch between H and V at the throat vs. a round driver exit: a larger V throat-angle difference means
  the section cannot be perfectly matched to the exit (a round exit has no preferred axis). [inferred]
- Whole point: mouth size still caps the V control frequency (audioXpress). Needed: V mouth dimension large enough;
  40 deg may need a 30 cm class height for ~1-2 kHz. [inferred from the article's scaling]

## Open items
- Fetch R-OSSE doc and read Geddes AES papers; OCR Keele 1038; read the Keele and Danley patents.
- Run BEM/Akabak/ABEC sweeps for late-break vs early-break to quantify waistbanding (no data found).

## Sources
OS-SE Waveguide (Marcel Batik, Oct 2020 PDF): https://at-horns.eu/release/OS-SE%20Waveguide.pdf
Ath 4.7.0 User Guide (PDF): https://at-horns.eu/release/Ath-4.7.0-UserGuide.pdf
Ath OS-SE page: https://at-horns.eu/osse.html
Ath download page: https://at-horns.eu/download.html
US7068805 Acoustic waveguide for controlled sound radiation (Geddes): https://patents.google.com/patent/US7068805
Wave shaping sound chamber (US6581719, cited via search result): https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6581719
Understanding Horn Directivity Control (audioXpress): https://audioxpress.com/article/Understanding-Horn-Directivity-Control
Keele Horn Design AES 1038 (scan; text unreadable): https://audioroundtable.com/misc/Keele_Horn_Design_AES_1038.pdf
US4071112 Keele patent (search result only; fetch 403): https://uspto.report/patent/grant/4071112
Acoustic Horn Design - The Easy Way (Ath4), diyAudio page 469 (search result only): https://diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/page-469
Acoustic Horn Design - The Easy Way (Ath4), diyAudio page 451 (search result only): https://diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/page-451
Geddes on Waveguides, diyAudio page 155 (search result only; fetch blocked): https://www.diyaudio.com/community/threads/geddes-on-waveguides.103872/page-155
When to use an asymmetric waveguide, diyAudio (search result only; fetch blocked): https://www.diyaudio.com/community/threads/when-to-use-an-asymmetric-waveguide.375799/
