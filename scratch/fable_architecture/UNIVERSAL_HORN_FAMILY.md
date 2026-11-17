# UNIVERSAL_HORN_FAMILY — what it would be, what it could make, and whether to build it

**Written:** 2026-11-16/17. **Code read at** `main` @ `207f97a`. **Status:** architectural explanation
and conceptual design. Not an implementation plan. No tracked file changed, no agent launched, no
mesh built, no solve run.

> **Results update, 2026-11-16 23:15.** Written before I had read the other agents' result files.
> Two statements below need qualifying. The "about 1 mm on two profiles" shape-mode figure does not
> extend to whole surfaces (X1: 8 modes give 1.4–2.3 mm). The "transfer experiment" cited in §4.1
> misses the specified strict held-out-engine success lines for the tested inputs (X3 remains incomplete), so the claim that one generator makes learned
> relationships reusable is an expectation, not a finding. Experiments U1–U3 are now briefed in
> full in `VALIDATION_EXPERIMENTS.md` Part 3. Status of everything: `LOW_COST_AGENT_HANDOFF.md`.

**Labels.** **[research]** stated in the repo's research library or its primary sources;
**[code]** read in the generator or mesher code; **[measured]** from stored Hornfab runs;
**[reasoning]** my physical or mathematical argument, not verified by any solve.

---

## 0. What I read, and what it changed

Read for this pass: `docs/plan/12_RESEARCH_BASIS.md` (sections 4, 6–11, 13, 16, 17 and the Crowe
addendum), `docs/plan/11_PHASE2_SURROGATE.md` (input representation, inversion),
`senior_pass_2026-10-24/02_TYPOLOGIES_AND_MULTICELL.md` (all), `typologies/MESHER_TYPOLOGIES.md`
(R-OSSE, ICW, FREEFORM, morph, section model, "what does not exist"), the knowledge hub and the
imported knowledge base (findings F01–F17, the typology atlas, the corrections table), the Crowe
area–aspect research V2, the Le Cléac'h construction and H/V ellipsoid dossiers, the Klangfilm
ellipse hand-off, the Klangfilm Stage A decision, and the headers of the generators concerned.
Not read in full: the X-shape, Salmon, biradial-sources, rolled-family and MEH dossiers; I relied
on their summaries in the research basis and the knowledge base.

Four things in that library change my earlier analysis:

1. **The backbone I proposed already exists in Hornfab, three times, under three names.**
   - The October `GRID` family is a radius field: two meridians from *any* meridian generator, a
     superellipse section with exponent p, even Fourier terms in azimuth, and an azimuth-dependent
     mouth offset **[code, `generators/grid.py` header; research, Report 2 §4]**.
   - `crowe_hv_area_aspect_v1` is exactly the area–aspect–section construction, with the same
     area inversion I wrote down, deliberately cut to four search dimensions **[code]**.
   - The Klangfilm Phase B core builds the wall from independent H and V *slope laws*, with its own
     section exponent law and a swept "beak" at the mouth **[code]**.
   Each was written as one more family. Nobody has factored out what they share.
2. **The particular Klangfilm Stage A throat-angle tweaks did not meet the stated authority threshold.** The Klangfilm
   Stage A test changed the throat-region wall angle by 4–5° in one plane at a time. The beam moved
   by at most 2.74°, in the wrong direction, and scores got worse. The recorded conclusion: "the
   pattern is set by the mouth and the rollback, not by the entrance tangent, and no additive
   offset can change the flare law itself" **[measured, `STAGE_A_VS_B_DECISION.md`]**. That is
   evidence about these tested adjustments, not a general test of other deformation modules; X2 remains inconclusive.
3. **Joining independent per-plane constructions does not make one horn.** The first H/V
   Le Cléac'h attempt marched a complete horn at each azimuth and lofted them. The result was
   "lobed, bulbous": the rim up to 118 mm off the ellipse and 319 mm out of plane at a box corner.
   The fix was one round core march providing shared stations, with per-plane expansions supplying
   the section axes **[research, `LECLEACH_HV_ELLIPSOID` C1]**. A universal generator must have a
   shared station structure; it cannot be a bundle of unrelated ribs.
4. **The library already warns against the shortcuts I took.** Two wall profiles do not determine
   the surface between them (Crowe addendum). Equal section area does not ensure equal impedance or
   wavefront shape (Cinanni caveat, Crowe V2 §1.3). A full-rank geometry Jacobian does not make a
   family optimization-ready (Crowe addendum). An H/V variant of a published horn is a new, derived
   geometry, not the published one (F15). I carry these through below.

---

## 1. What a "universal horn family" would actually be

### 1.1 Five different things that get called by similar names

Think of a workshop that makes horns.

| Idea | Workshop analogy | Can it produce a horn that did not exist before? |
|---|---|---|
| **Shared representation** | A measuring jig. Any finished horn can be put on it and measured the same way. | **No.** It only measures. This is the "canonical surface" of my earlier reports. |
| **Universal parametric generator** | One adjustable former with a fixed set of levers. Every setting of the levers gives a horn. | **Yes**, anything its levers can reach, including settings between and beyond known designs. Nothing its levers cannot reach. |
| **Composable grammar** | A kit of interchangeable parts: throats, bodies, section shapers, lips. You choose parts, then adjust each. | **Yes**, including combinations no one has assembled. The choice of parts is a discrete decision on top of the adjustments. |
| **Existing families plus universal deformation controls** | Take a finished horn and press on it with shaped tools. | **Yes, locally.** It makes neighbours of existing horns. It does not change how the horn was laid out. |
| **Learned low-dimensional shape space** | Average and blend the horns already on the shelf. | **Only blends.** It finds in-betweens and mild extrapolations of what exists; it cannot invent a feature that no shelf horn has. |

Only the second, third and fourth generate geometry. The first is necessary plumbing for
comparing and learning; the fifth is a way to *search* compactly, not a way to *create*.

### 1.2 The mental picture, throat to mouth

A single-throat horn's inner wall is one sheet of material from a ring at the throat to a rim at
the lip. There are three classical ways to lay that sheet out, and every horn in Hornfab uses one
of them **[research + code]**:

1. **Section-first (slices).** Stand planes across the axis like bread slices. On each slice draw a
   closed outline: circle, ellipse, squircle, rounded rectangle. Say how the outline's width,
   height and shape change from slice to slice. *FREEFORM, the generic GRID, Crowe area–aspect and
   the Klangfilm Phase B core work this way.*
2. **Meridian-first (ribs).** Stand planes *through* the axis like the ribs of an umbrella. On each
   rib draw the wall profile from throat to lip. Say how the profile changes from rib to rib.
   *OSSE with its azimuth-dependent parameters (ATH CORE, Tritonia), R-OSSE and ICW work this way.
   A rib can curl backwards, so rollback is natural.*
3. **Wavefront-first.** Decide what the sound wave is supposed to look like as it travels (flat,
   a spherical cap, an ellipsoidal cap) and how fast its area should grow. The wall is whatever
   surface stays perpendicular to those wavefronts. *Le Cléac'h, Kugelwellen/Klangfilm and the
   Salmon family work this way. The lip curls back because the wavefront law says so, not because
   a lip was added.*

A universal generator, properly understood, is **not** one formula. It is one *sheet* (a grid of
points from throat to lip and around the axis, which the mesher already accepts) with **a fixed
sequence of decisions along the horn**, each of which can be filled by a simple law or by a
specialist's mathematics:

```
THROAT          BODY                          MOUTH
 ring  →  how fast it opens  →  how H and V  →  what the outline  →  how it ends
 (driver)   (expansion law)      part company     looks like          (lip, roll, rim)
                                  (split law)      (section law)       (termination law)
                                                       + optional extras: local features, asymmetry, twist
```

Walking it once:

- **At the throat** the ring is the driver's exit and the wall leaves at the driver's exit angle.
  Nothing here is free except an optional short adapter.
- **The expansion law** says how quickly the horn opens overall. This is where "exponential",
  "hypex with T = 0.7", "oblate spheroid" or "Le Cléac'h at 400 Hz" lives.
- **The split law** says when and how strongly horizontal and vertical stop being the same: early
  or late, gently or abruptly, and to what final ratio.
- **The section law** says what the outline between the horizontal and vertical walls looks like:
  elliptical, squarer, with the diagonals pushed out or pulled in.
- **The termination law** says where the working flare hands over to the lip, how tightly the lip
  curves, how far it wraps, and whether that differs between the sides and the top and bottom.
- **Extras** are switched on only when wanted: a local bulge or pinch, up/down asymmetry, a
  non-planar rim, a twist.

Existing families are particular choices at each step. OSSE chooses an oblate-spheroid expansion,
lets the split follow an azimuth law on the wall angle, takes whatever section results, and ends
with a superellipse flare and no roll. Le Cléac'h chooses a wavefront-area expansion, no split,
round sections, and a roll that is part of the expansion law itself.

---

## 2. The geometry concept in detail

### 2.1 The carrier: a sheet with shared stations

Write the wall as points `P(s, φ)`: `s` runs from 0 at the throat to 1 at the lip, measured
**along the wall** (so a wall that curls back is no problem), and `φ` is the angle round the axis.
Every azimuth uses the *same* `s` stations. This shared-station rule is the lesson of the failed
per-azimuth Le Cléac'h loft. It is also exactly the array the mesher's point-grid input takes
(`n_phi × n_s × 3`, millimetres) **[code]**.

### 2.2 The most useful single coordinate: wall angle

At each point the wall makes an angle `ψ` with the horn axis. `ψ = 0` is a straight pipe, `ψ = 35°`
is a wall of a 70° cone, `ψ = 90°` is a flat flange, `ψ > 90°` is a wall that has turned back.
Given `ψ` along a rib, the rib's shape follows by adding up small steps:

```
radius at s  =  throat radius + sum of  sin ψ · (step along wall)
depth  at s  =                  sum of  cos ψ · (step along wall)
```

*Physical meaning.* The wall angle is the quantity the acoustics respond to most directly:
- In the middle of the band, coverage in a plane follows the wall angle in that plane. Keele's
  patent uses a wall included angle of about 0.9 of the wanted beamwidth **[research]**.
- How quickly `ψ` changes along the wall (the curvature) governs how much the horn disturbs the
  wave: abrupt changes radiate diffraction and excite higher-order modes; ICW was built on this
  idea and Report 2 says it in so many words: "wall *angle* is what governs diffraction"
  **[research]**.
- Where `ψ` passes 90° the horn has a rolled lip.

So a horn can be described as **a map of wall angle over the sheet**, `ψ(s, φ)`. A map that is
smooth gives a wall that is smooth and cannot fold on itself along a rib. Every family has a
recognizable map:

| Family | Its wall-angle map |
|---|---|
| Conical | One constant value |
| Oblate spheroid (OS) | Rises smoothly from the throat angle and levels off at the coverage angle |
| OS-SE (ATH) | The OS map, then a further rise near the mouth (the superellipse flare) |
| Exponential, tractrix | Rises continuously, slowly then quickly; tractrix ends at 90° |
| Le Cléac'h, Kugelwellen, R-OSSE | Keeps rising through 90° to 180° or more: the roll |
| ATH CORE / Tritonia | An OS-SE map whose level differs round the axis by a published azimuth law |
| Biradial | Two different maps on the horizontal and vertical ribs |

This is my main refinement of the earlier proposal. **The universal coordinates should be wall
angle (and through it, curvature) along shared stations, not section width and height.** Widths,
heights and areas are then *results* that can be reported, constrained or targeted.

### 2.3 The layers, what each controls, and how

"Fundamental" means the horn is undefined without it. "Module" means it defaults to off and the
horn is unchanged when it is off.

| Layer | What it physically changes | Natural mathematical control | Kind | Typical number of knobs |
|---|---|---|---|---|
| **Throat** | Ring size, exit angle, optional straight or tapered adapter, flat or domed source face | Fixed by driver and brief; adapter length and angle | Fundamental, mostly not searched | 0–2 |
| **Expansion** | How fast the horn opens overall, hence loading and depth | Mean wall-angle law along `s`, **or** a specialist law (hypex `fc`, `T`; OS `a0`, `a`, `k`; Le Cléac'h march) | Fundamental; the slot for specialist mathematics | 2–4 |
| **H/V split** | When and how far horizontal and vertical walls diverge | Difference of wall angle between the two principal ribs as a law along `s`: final difference, where half of it has happened, how abruptly | Fundamental for non-round horns | 2–3 |
| **Section** | Outline between the principal walls: round, squarer, diagonals out or in | Shape exponent along `s` (2 = ellipse, larger = squarer); one diagonal term (a third rib at 45°, or a `cos 4φ` term) | Fundamental at minimum (one exponent); diagonal control is a module | 1–3 |
| **Termination** | Where the flare ends, lip radius, wrap, and their difference between sides and top/bottom | Hand-over station; lip curvature; wrap angle; each with an optional side-versus-top difference | Fundamental (a horn must end somehow) | 2–5 |
| **Rim plane** | Whether the mouth is flat, saddle-shaped or beaked | Depth offset round the rim (sides back, top forward, diagonals scooped) | Module | 0–3 |
| **Local feature** | A bulge, pinch or change of rate in one place | A smooth window along `s` (position, width, sharpness) times a shape round `φ`, added to the wall-angle map. Batík's published "meander" function is exactly this **[research, 12 §13.7]** | Module | 3–5 each |
| **Asymmetry** | Up differs from down (floor, ceiling, listening axis) | Odd terms round the axis (`cos φ`); needs a half model | Module, doubles solve size | 1–3 |
| **Twist** | Section rotates along the horn | Rotation angle along `s`; needs a full model | Module, quadruples solve size | 1–2 |

**Things you asked about specifically.**

- *Throat shape, entry angle, wavefront transition.* The ring and angle are given. What is
  designable is how gently the wall angle leaves the throat value. A fast change close to the
  throat is where higher-order modes are born **[research, OS/Geddes motivation; reasoning]**, so
  the expansion law should be constrained to start tangent to the driver and change curvature
  slowly at first. The source face can be flat or a spherical cap in the mesher **[code]**; that is
  a modelling assumption about the driver, not a horn shape.
- *Axial expansion and area growth.* Not an independent control once wall angles are chosen: area
  at a station is the outline's area, which follows from the radii, which follow from the angles.
  You can instead *prescribe* area (from a hypex or Le Cléac'h law) and let one wall angle be the
  result; see example E. You cannot freely set area, both wall angles and the section shape at
  once: any three determine the fourth.
- *Different wall-angle progressions.* This is the heart of it. "Straight then flared" (Keele
  three-section), "continuously opening" (exponential), "levelling off" (OS) and "rolling over"
  (Le Cléac'h) are different shapes of the same curve of `ψ` against `s`. A spline with four or
  five control values, forced to be non-decreasing where a fold would otherwise occur, reaches all
  of them approximately.
- *Changing section shapes.* A single exponent that grows along the horn takes a circle to an
  ellipse to a squircle to a near-rectangle. Rounded rectangles with a specified corner radius and
  true creases need either the mesher's own rounded-rectangle outline or many azimuth terms; a
  smooth backbone approximates them.
- *Diagonal and X ridges.* A term that is zero on the horizontal and vertical ribs and largest at
  45° (`sin² 2φ`) pushes the diagonals out (a star or X rim) or in (a pinched, "smoothed diagonal"
  mouth). The Crowe research gives exactly this form and notes it changes area and diagonal
  lobing, so it must be scored on the diagonals **[research]**.
- *Mouth termination.* Treat the lip as a continuation of the wall-angle map past the hand-over
  station: curvature and wrap angle are its two controls. Making either depend on azimuth gives
  "roll the sides, keep the top and bottom short".
- *Asymmetry and non-planar mouths.* Both are natural on the sheet. A non-planar rim appears
  automatically whenever ribs have different lengths or wraps; it can also be imposed directly as
  a depth offset round the rim (the Klangfilm "beak").
- *Local bulges and transitions.* A windowed bump added to the wall-angle map. Because it is added
  to the *angle*, not to the radius, everything downstream of the bump moves with it, which is what
  distinguishes changing the flare law from pressing a dent into a finished horn.

### 2.4 What is coupled, whatever the parameterization

| Coupling | Why | Consequence |
|---|---|---|
| Wall angle, length and mouth size | Mouth half-width = throat radius + sum of `sin ψ` along the wall | Fix two and the third follows. Inside a fixed envelope, a narrow wall angle and a large mouth need depth or a late flare |
| Area, the two wall angles and the section shape | Area is the outline's area | Any three fix the fourth |
| Lip size and working aperture | A lip of radius ρ uses about 2ρ of the envelope in that direction | A big roll is paid for in active mouth size. Crowe research: "do not allow the exterior bead to masquerade as a larger active aperture" |
| Mouth dimension and the low-frequency limit of pattern control | Diffraction: an aperture a wavelength or so across cannot hold a narrow beam | No shape freedom moves this much. For 480 mm height and 50°, Keele's heuristic gives about 1 kHz; it is a heuristic, not a hard bound **[research KH-001]** |
| Rate of change near the throat and high-frequency cleanliness | Rapid angle or section change near the throat excites higher-order modes | The split and section laws should start late and gently. Crowe V2A fixed the throat transition for this reason |
| Section corners and diagonal behaviour | A squarer outline changes the 45° cut | Section shape cannot be judged from H and V polars alone |
| Symmetry and solve cost | Quarter model for H and V mirror symmetry; half model for up/down asymmetry (2× unknowns); full model for twist (4×) | Asymmetry and twist are expensive modules on an 8 GB card |

### 2.5 Is 10–14 dimensions enough?

It depends on what is being claimed, and my earlier number blurred two claims.

- **A compact, useful family: yes.** Expansion 3, split 3, section 1–2, termination 3–4 gives
  10–12 knobs. That spans round and H/V horns, constant-directivity and loading-first intents, flat
  and rolled mouths, in one continuous space. Hornfab's own area–aspect family was cut to **four**
  searched knobs on purpose, with the rest fixed, so that each knob has a distinct, testable
  effect **[code, research V2A]**. That discipline is right: switch layers on in stages.
- **Reproducing published families exactly: no, not with generic splines.** A Le Cléac'h profile
  is the output of a wavefront march, an OS-SE profile is a specific closed form. Five spline
  values approximate them; they do not equal them. The honest way to keep them exact is to let the
  *expansion layer accept the specialist's law as it is*.
- **A truly general single-duct shape space: no.** Free laws in every layer with several azimuth
  terms each is 25–40 dimensions before modules. That is beyond what CMA-ES or a GP can explore
  with a few hundred solves, and most of it would be acoustically meaningless.

So: 10–14 for a compact family that is searched; specialist laws plugged in for exactness; a large
general space only as something a model samples from, never as something an optimizer wanders in.

---

## 3. Five horns it could make

For each: defining choices, appearance, relatives, what is new, expected acoustics with its
evidence status, and whether the present point-grid mesher could carry it. All are single-duct
sheets, so all are representable; cost notes say which symmetry they need.

### A. OSSE-derived constant-directivity horn with independent H/V development and a worked mouth

1. **Defined by.** Expansion: oblate-spheroid law (throat angle from the driver, expansion factor
   `k`). Split: horizontal wall levelling at about 36° from the axis, vertical at about 22°, with
   the vertical allowed its own timing. Section: ellipse at the throat growing to a mild squircle.
   Termination: superellipse flare whose amount and onset differ between sides and top/bottom, plus
   a small rolled edge.
2. **Looks like.** A smooth landscape waveguide: round throat, walls opening quickly then
   straightening, a softly squared mouth with rounded lips, wider than tall.
3. **Resembles.** `hl__ext_throat_hvlaw_v7` (the current best lane), ATH CORE, Tritonia.
4. **New.** The OSSE lane already varies wall angle round the axis, and the mesher lets the
   termination terms `s` and `n` vary too; the winning lane left those at zero **[code, measured
   row]**. What no OSSE config can do: give the vertical plane a *different schedule along the
   horn* (narrow for most of the length, then open late into a tall mouth), choose the section
   outline independently of the angle law, or end in a true roll (that needs R-OSSE, whose
   parameters mean different things).
5. **Expected acoustics.** Mid-band coverage near the wall angles in each plane **[reasoning from
   Keele]**. The late vertical flare into a taller mouth is the Manta-Ray argument for holding
   vertical pattern lower **[research, Henricksen and Ureda]**; the best stored designs use about
   400 mm of the 480 mm height **[measured]**, so there is unused aperture. Whether this recovers
   vertical control near 1 kHz is **unverified**.
6. **Mesher.** Yes, quarter model.

### B. Le Cléac'h-style horn that stays non-constant-directivity

1. **Defined by.** Expansion: the exact Fourcade wavefront march at a cutoff `fc` and shape factor
   `T` (wavefront-first, plugged in unchanged). Split: the published equal-area ellipsoidal stretch,
   1 at the throat rising to perhaps 1.6 at the mouth. Section: ellipse. Termination: none added;
   the roll is the continuation of the march to a stop angle of 180° or more, optionally deeper at
   the sides.
2. **Looks like.** A long slim round throat opening into a large trumpet bell that curls right
   back on itself, oval when seen from the front.
3. **Resembles.** `lecleach_rollback` (round, validated against Fourcade's table to 0.00 mm on
   mouth width), the shipped H/V ellipsoidal construction, the Klangfilm ellipse.
4. **New.** In one space with horn A, so `T`, the stretch timing and the stop angle are continuous
   knobs alongside everything else; a section exponent slightly above 2; side-only extra wrap. Not
   new in kind: Hornfab already builds this family.
5. **Expected acoustics.** Beam narrows steadily with frequency, DI rises; smooth throat loading
   down toward `fc`; low mouth ripple from the roll **[research; these are the family's design
   intent]**. It must be scored against a sloped beamwidth corridor and a loading target, not a
   constant-coverage target (F01). The round case reproduces *published geometry*; nothing here
   reproduces *published acoustics*, and the H/V version is a derived shape (F15).
6. **Mesher.** Yes, quarter model. The roll needs wall-length stations and the existing
   self-approach guard (lip parts closer than twice the wall thickness plus 2 mm are refused)
   **[code]**.

### C. Biradial / ATH-style hybrid with diagonal mouth shaping

1. **Defined by.** Expansion: short exponential-area connector from the round throat. Split: two
   *different* wall laws. Horizontal: nearly straight, then a power-law flare near the mouth
   (Keele's `y = a + b·x + c·xⁿ`, n about 5). Vertical: straighter and narrower, flaring later
   with a different exponent. Section: squircle with a diagonal term pulling the 45° walls in
   toward the mouth. Termination: moderate roundover; rim allowed to be non-planar.
2. **Looks like.** A classic "butt-cheek" biradial softened: straight side walls that bell out at
   the mouth, flatter top and bottom, and corners that are drawn in so the mouth reads as a
   rounded X or bow-tie rather than a rectangle.
3. **Resembles.** `biradial_keele`, `hl__biradial_es_style`, ATH Tritonia's morph to a rounded
   rectangle, AudioHorn's X-shape (their published claim is that the diagonal measures as cleanly
   as the horizontal; geometry unpublished) **[research]**.
4. **New.** The generator route gives two profiles but only two section stations, so the section
   cannot be steered along the horn; the diagonal cannot be controlled separately from H and V;
   the lip is not a shared option. All three become available together.
5. **Expected acoustics.** Coverage set per plane by the straight-wall angles; mouth flare easing
   the low end of each plane's control; diagonal shaping aimed at making the 45° cut resemble the
   H and V cuts **[reasoning]**. The research is explicit that X creases may be styling or a
   by-product, and that squared corners can worsen diagonals (Cinanni) — **unverified either way**;
   needs the diagonal score.
6. **Mesher.** Yes, quarter model. Caveats: Keele's real horizontal walls are a surface of
   revolution about a vertex in a swept frame, which slices or ribs only approximate; and the
   patent's thin diffraction slot is a narrow passage where the solver's accuracy is a known
   risk **[research]**.

### D. Klangfilm / rolled-mouth horn with curved wavefronts and evolving sections

1. **Defined by.** Expansion: the Kugelwellen law (wavefronts are spherical caps of constant
   radius `c/(π·fc)`; cap height grows exponentially). Split: Ahlswede's equal-area ellipsoid
   stretch. Section: Lamé exponent starting at 2 and rising late (the "dual Lamé" idea).
   Termination: the profile's own roll, stopped at a chosen fraction; rim plane bowed so the
   centre leads and the sides trail.
2. **Looks like.** A deep oval bowl whose wall turns outward and then back toward the driver, with
   a softly squared front outline and a front edge that is curved when seen from above.
3. **Resembles.** `hl__klangfilm_lame_curved_v1`, the Klangfilm ellipse tool, the rolled family.
4. **New.** Today's Phase B core gains independent H and V slope laws but gives up the wavefront
   area law ("does not satisfy Ahlswede's area law", its own header says) **[code]**. In a layered
   generator the area law can stay as the expansion while the split layer decides how the area is
   shared between width and height. So "keep the loading design, change the coverage split" becomes
   a clean, separate experiment.
5. **Expected acoustics.** Loading-first behaviour with rising DI; the roll is the main
   diffraction control **[research]**. The measured Stage A lesson applies: changes near the throat
   do little; the flare law and mouth decide the pattern **[measured]**.
6. **Mesher.** Yes; this family already runs through the rows route of the point grid, quarter
   model. A lip that returns into the body needs stations normal to a curved spine, which the
   Phase B notes list as not yet built.

### E. A new hybrid: loading by an area law, constant coverage in one plane, termination spent where it helps

1. **Defined by.** Expansion: *prescribed area* from a hypex or Le Cléac'h law (a loading-first
   choice). Split: horizontal wall prescribed as an OS-then-straight constant-directivity wall;
   the **vertical dimension is not designed, it is solved** so that each station has the prescribed
   area. Section: ellipse to squircle. Termination: a generous roll on the top and bottom rims,
   where the solved vertical wall is already steepening, and a compact flare on the sides where
   width is at the envelope limit.
2. **Looks like.** From the side, the long graceful curve of an exponential-type horn; from above,
   the straight walls of a constant-directivity waveguide; from the front, an oval mouth with
   thick rolled upper and lower lips and thinner side lips.
3. **Resembles.** Nothing in Hornfab. The idea is Cinanni's Hybrid Constant Directivity horn
   (constant directivity in one plane while preserving the expansion's acoustic load), which the
   research basis lists as absent **[research, 12 §16.1]**.
4. **New.** No current generator ties a prescribed area law to a prescribed wall in one plane and
   derives the other. It also uses azimuth-dependent termination as a design budget.
5. **Expected acoustics.** Horizontal: constant coverage above the frequency the 600 mm width can
   control. Vertical: deliberately *not* constant; it narrows with frequency like a loading horn,
   to be scored against a sloped vertical corridor. Loading: near the parent law's, to the extent
   one-dimensional theory holds **[reasoning]**. The research warns precisely here: equal area does
   not guarantee equal impedance or wavefront shape in a non-round horn, and Cinanni's own
   simulations show corner and diagonal irregularities **[research]**. Entirely **unverified**.
   It fits the owner's stated preference that vertical matters less.
6. **Mesher.** Yes, quarter model. Geometric validity needs a check that the solved vertical
   dimension never shrinks and never drops below the throat radius.

---

## 4. Is one universal family actually better?

### 4.1 The case for it (which I under-weighted)

- **It makes discrete choices continuous.** Today "no roll" and "roll" are different engines with
  different parameter meanings. In a layered generator the wrap angle is one knob from 0° to 270°.
  Likewise hypex `T` runs continuously from catenoidal to exponential, `k` from cone to oblate
  spheroid, the section exponent from ellipse to rectangle. An optimizer can only find "a little
  roll on the sides only" if that is a point in its space. **CMA-ES and BoTorch cannot cross from
  one family to another today; in a shared space they can.**
- **It ends the fragmentation.** The stored campaign spread 3,414 solves over 35 lanes, median
  about 50 each **[measured]**. One generator means one search space, one dataset, one model, and
  no lanes that are the same construction under different names.
- **It may make learned relationships easier to reuse, subject to validation.** My transfer experiment needed
  shape measurements as a translation layer between families. If every horn is described by the
  same layer parameters, "vertical split timing" means the same thing everywhere and a model's
  knowledge of it applies to every design.
- **The team keeps building it anyway.** Three near-backbones in a month is the strongest
  practical argument: the need is real, and each rebuild currently costs a new adapter, new
  validity rules, a new BO geometry adapter and a new lane.
- **The freedoms that matter are structural.** Stage A shows that pressing on a finished horn
  barely moves the beam. The useful freedoms — when the vertical opens, how the lip differs round
  the mouth, what the outline does along the horn — are properties of the layout, which only a
  generator, not a deformation, can change.

### 4.2 The case against it

- **Generic laws lose specialist mathematics.** The Le Cléac'h march embodies a physical
  hypothesis; a five-point spline that looks similar does not, and "looks similar" is not a
  claim the repo's naming rule (nothing ships under a published name without a verifiable
  reference) allows.
- **One landscape, many valleys.** A space containing both a compact waveguide and a rolled trumpet
  has separate good regions with poor shapes between them. A single CMA-ES run settles in one
  valley; a GP over the whole space needs far more data than a GP over one lane.
- **Valid surface is not sensible horn.** Smooth wall-angle maps cannot fold along a rib, but a
  roll can still collide with itself or the body, a solved dimension can shrink, and combinations
  of layers can produce shapes with no acoustic rationale. The library's phrase is "arbitrary
  surface distortion".
- **History does not map over for free.** Old runs are stored against old knobs. Unless the new
  generator reproduces an old design's surface exactly, its stored response belongs to a slightly
  different horn.
- **Dimension creeps.** Every "just one more layer option" is another axis. The area–aspect
  family's retreat from nine proposed knobs to four is the right instinct and a warning.

### 4.3 The four architectures compared

| | One universal parametric generator | Modular grammar | Specialist generators + shared deformations | **Layered backbone with pluggable specialist laws** |
|---|---|---|---|---|
| What it is | One fixed set of generic laws for every layer | Choose a part per layer, any part with any part | Today's engines, plus tools that press on the result | Fixed layers on shared stations; each layer takes either a generic law or a registered specialist law |
| New combinations | Yes, continuous | Yes, including discrete swaps | Neighbours only | Yes, continuous within a layer choice and across layers |
| Exact published families | No, approximations | Yes | Yes | Yes, when the specialist law is plugged in and the other layers are neutral |
| Transitions between types | Smooth | By swapping parts (a jump) | None | Smooth in the generic laws; a jump only when the expansion law is swapped |
| Search dimension | 10–14 compact, 25–40 general | 10–25 plus discrete choices | Lane's own + 2–6 | 10–14 active at a time, staged |
| Historical data | Approximate at best | Preserved | Preserved | Preserved for any old design the backbone reproduces exactly; importable through surface matching otherwise |
| Measured support | M3: shapes share a small space | — | Against: Stage A, additive changes have little authority | For: three partial instances already built; Stage A; the Le Cléac'h shared-station fix |
| Main risk | Too generic; loses provenance; unusable history | Mixed discrete-continuous search, which the BO encoding refuses today; silent no-ops | Cannot change the flare law, so limited reach | Design discipline: keeping layers genuinely separable and the neutral settings exact |

The fourth column is not a compromise for its own sake. It is what Report 2 already sketched for
the GRID family ("`r_H`, `r_V` come from any existing meridian generator, so every classical
typology automatically gets the new cross-section freedoms") **[research]**, carried through to
all five layers and to wall-length stations so that rolls are included.

**Could it keep existing parameterizations and data?** For families that are already "a meridian
law with parameters that vary round the axis" (OSSE and its ATH variants) and for "slices with two
profiles" (FREEFORM, GRID, area–aspect), yes in principle: they are exactly a specialist expansion
law with a particular split and section, so the backbone with those plugged in and everything else
neutral should return the same surface. That is a testable claim, not an assumption (experiment
U1). For families built from fixed digitized contours (the Crowe section reconstruction) or CAD,
no.

---

## 5. The acoustic theory, examined critically

### 5.1 What one-dimensional horn theory gives, and where it stops

One-dimensional (Webster) theory treats the wave as having a known shape at each station and asks
only how its area grows. It is useful for:

- throat loading and cutoff of slowly flaring horns at low frequency;
- comparing expansion laws (exponential, hypex, tractrix) as *loading* devices;
- a cheap feature for a model: it needs only the area along the horn.

It says **nothing about directivity**, and it stops being trustworthy when:

- **the flare is fast or the angles are wide**, because the wave is then far from the assumed
  shape (this is why Le Cléac'h and Kugelwellen replace flat wavefronts with curved ones, and why
  those are still hypotheses about the wave);
- **the section is wide enough for cross-modes.** With a symmetric source, the first symmetric
  cross-mode of a passage of width `w` can propagate above roughly `c/w`. At 200 mm width that is
  about 1.7 kHz; at a 600 mm mouth, under 600 Hz **[reasoning, standard duct acoustics]**. Over
  most of this horn's band the outer part of the horn carries several modes, and the pattern *is*
  their mixture. Area cannot describe that;
- **the section changes shape.** Round to rectangular redistributes energy between modes even at
  constant area (the Cinanni caveat);
- **the wave reaches the mouth.** Radiation and edge diffraction depend on the rim's shape and
  curvature and on what the horn is mounted in; a free-standing roll, a flange and a cabinet are
  different problems (F08).

So "area sets loading, aspect sets directivity" is a first sketch, not a law. More accurate:
**wall angle sets mid-band coverage; mouth dimension sets how low coverage can be held;
termination sets ripple and how the low end rolls off; the throat region sets the top octave;
section outline sets the diagonals; area growth sets loading at the low end.** These overlap.

### 5.2 Three levels of "valid"

| Level | Meaning | Who checks |
|---|---|---|
| Geometrically valid | Closed, non-intersecting, meshable, fits the throat and the envelope, printable | CPU, exactly, before any solve |
| Physically meaningful | The shape embodies some intent: a wavefront law, a coverage law, a diffraction control | The designer and the construction law; partly by reduced physics |
| Acoustically successful | The solved response meets the brief | BEM only, then measurement |

A universal generator makes level 1 cheap and should refuse failures exactly. It makes level 2
*optional*, which is its danger. Level 3 is unchanged: every claim still needs a solve, and the
solve itself assumes an ideal uniform source at the throat, which is not the HF1440 (F06), so even
level 3 is "successful under the standard source".

### 5.3 Specific cautions

- **Throat matching.** The exit angle is a modelling assumption for this driver (the 2° is not a
  published figure) and the first cross-mode of a 36 mm throat is near 5.6 kHz. Layers that act
  near the throat should be few and constrained; searching them risks optimizing against an
  invented boundary (Crowe V2 §4).
- **Mesh validity.** Rolled lips with tight radii, squared corners and thin passages raise element
  counts and local error. The existing self-approach guard and DOF caps must apply to the whole
  generator, not per family.
- **Manufacturability.** Minimum lip radius, wall gap and overhang are constraints on the sheet,
  the same for every horn.
- **Unnecessary degrees of freedom.** Before any knob is searched it should be shown to move the
  surface in a distinct way *and* to move the response; the area–aspect V2A process is the model.
- **Two profiles are not a surface.** Whatever fills the space between the principal ribs is a
  design decision with acoustic consequences. It needs its own layer and its own score (the
  diagonals), which is why the section layer is fundamental, not cosmetic.

### 5.4 What cannot be unified

| Geometry | Why not |
|---|---|
| Multiple-entry horns (Synergy, Unity, Solana) | Extra sources, ports and chambers; a coupled system of drivers, not one sheet with one source (F16) |
| Phase plugs, shaping plugs, ring adapters | Several channels between throat and horn; the air space has holes through it |
| Multicell horns, vanes, lenses | Septa divide the duct; needs the CAD route and thin-body solver care |
| Cone-driver horns | The source is a moving cone with its own geometry |
| Cabinets and baffles | Boundary conditions around the horn, to be fixed per comparison, not horn shape |
| Diffraction slots | Representable as a very narrow section, but numerically risky; treat as its own study |

These share the solver, the dataset and the reporting. They should not share a generator.

---

## 6. Compact comparison and decisive experiments

| | Shared representation | Universal generator | Grammar | Families + deformations | Learned shape space | Layered backbone + specialist laws |
|---|---|---|---|---|---|---|
| Meaningful parameters | none (measures) | 10–14 compact | 10–25 + choices | lane + 2–6 | 6–10 | 10–14 active, staged |
| Represents exactly | every single-duct horn, as samples | only its own shapes | every included part | every existing family | nothing; all approximate | existing law-based families |
| Represents approximately | fine detail below the sampling | published families | — | — | existing horns to about 1 mm on two profiles **[measured]** | digitized or CAD-derived shapes |
| New feature combinations | no | yes | yes | local only | blends only | yes |
| Keeps historical solves usable | yes | weakly | yes | yes | as training data | yes where reproduction is exact |
| Works with present mesher and BEM | yes | yes (point grid) | yes for single-duct parts | yes | yes via decoding | yes (point grid) |
| CMA-ES | n/a | good if compact | poor (discrete) | good | good | good, layer by layer |
| BoTorch | n/a | good; one model for all | needs mixed encoding | per lane | good | good; one model for all |
| Response-level modelling | essential input | natural | awkward | per lane | natural | natural |
| Research and build effort | small | medium | large | small to medium | medium | medium to large |
| Principal risk | does nothing alone | generic, history lost | search and no-ops | little authority **[measured]** | cannot invent | keeping layers separable |

### Three experiments that would decide it

**U1. Exact reproduction (CPU only).** Take the best stored design from four law-based lanes
(OSSE with azimuth law, generic GRID or biradial, area–aspect, Le Cléac'h H/V). Express each as
"specialist expansion law + its split + its section + its termination, other layers neutral" on
shared wall-length stations. Compare the whole surface with the stored mesh. *Pass:* worst
deviation under about 0.5 mm for at least three of four. *Decides:* whether the layered backbone
can inherit history. Also record how badly a purely generic law (five spline values) reproduces
each: that number is what the specialist mathematics is worth.

**U2. Are the families islands or one continent? (zero GPU, then about 30 solves with approval)**
Pick two good solved designs from different families. Generate the straight-line path between them
in layer-parameter space, ten steps. First check geometric validity at every step on CPU and
predict responses with the existing transfer model. Then, with approval, solve the intermediate
shapes for two or three such paths. *Decides:* if intermediates are valid and their responses move
smoothly, one shared space is searchable and lanes are an artefact; if there is a wall of bad or
invalid shapes between, families are separate valleys and the search needs a lane-like outer
choice even inside a common generator.

**U3. Do the new structural freedoms have authority? (about 12–16 solves with approval)**
Around the best stored design, change only what no current family can: (a) vertical flare timing
with a taller mouth at fixed depth; (b) side-versus-top termination. One change at a time, paired
with an unchanged control, judged by a pre-declared rule (the Klangfilm study's 3° on the intended
axis without harming the other). *Decides:* whether the backbone's extra reach is acoustically
real. Stage A is the cautionary precedent: a freedom can be geometrically real and acoustically
inert.

---

## 7. My conclusion

**I now choose D: a hybrid — specifically, a layered backbone on shared wall-length stations, in
which each layer accepts either a simple generic law or a registered specialist construction law,
with wall angle as the primary coordinate.** This is a change from my earlier position (keep the
specialist families and add common modifiers, option A).

Why I changed:

1. **Measured evidence went against modifiers.** Additive changes to a finished Klangfilm horn had
   almost no authority. The freedoms that matter are in the layout.
2. **The backbone is not speculative here.** Hornfab has written most of it three times. The
   architectural act is to recognize one object and stop re-deriving it as new families, each with
   its own adapters, validity rules and data silo.
3. **It is the only option that gives both things the owner asked for.** A pure universal generator
   gives continuous transitions but discards the specialists' mathematics and the history. Keeping
   only specialists preserves both but can never cross between them. Layers with pluggable laws
   keep a Le Cléac'h march exactly a Le Cléac'h march, while letting the split, section and
   termination around it be searched in the same terms as every other horn.
4. **It makes the search engine I recommended stronger.** Response-level modelling over a
   multi-generator candidate pool needed shape measurements as a translator between families. With
   one generator the inputs are already common, the pool is one space, and "which family" becomes
   mostly "which expansion law", a single discrete choice instead of thirty-five lanes.

What I would **not** do: build it as one superellipse-with-harmonics formula; expose more than a
handful of knobs at once; search throat-region freedoms; treat equal area as equal loading; or
claim any published name for a generic approximation.

What I am **not** sure of, and what would change my mind:

- If U1 shows the layered form cannot reproduce existing designs closely, the backbone becomes a
  new family beside the others and loses the argument about history and unification.
- If U2 shows families are islands, most of the "one space" benefit goes, and a grammar-like outer
  choice over lanes is the honest structure.
- If U3 shows the new freedoms are acoustically inert in this envelope, the binding limit is size
  and diffraction, and no generator will find much more than the current best.

**For a system whose goal is the best possible horns, including novel ones, on an expensive
solver:** the generator decides what can exist, the model decides where to look, and the solver
decides what is true. Today the generator is thirty-five small, separate vocabularies. I would
replace that with one layered vocabulary that still speaks each specialist's dialect, keep the
canonical surface as the bridge to history and to the excluded topologies, and put the
response-level model and a single value-per-cost rule on top. What this makes possible that is not
possible today is every horn in section 3 that needs a decision no current family exposes: a
vertical wall on its own schedule, a lip that differs round the mouth, an outline steered along
the horn, a loading law combined with a coverage law, and continuous movement between a waveguide
and a rolled horn.

---

## 8. Continuation guide: what must be proved before unification

**Status at the 2026-11-16 handoff:** the layered backbone is an architectural hypothesis, not a working replacement or an established way to reuse historical responses. U1–U3 have not run. Read this section with `LOW_COST_AGENT_HANDOFF.md` and the detailed, predeclared procedures in `VALIDATION_EXPERIMENTS.md`; result reports take precedence over the optimistic comparative claims in §§4–7 above. In particular, exact specialist reproduction, shared searchability, response authority, and a single cross-family model remain unproven. E1 did not show an advantage for response modelling over a scalar model on its tested proxy; X3 did not establish reliable transfer. Do not implement a unified search or relabel approximations as historical families on this basis.

### Architecture and evidence boundary

The proposed object describes a single-duct inner wall on common wall-length stations. Throat/source, expansion law, H/V split, section between ribs, and termination are distinct responsibilities; a specialist law should retain its own mathematics and exact neutral settings, while generic laws offer new combinations. Wall length matters because depth alone can reverse through a rolled lip. Shared stations and a section law do not by themselves guarantee correct correspondence, preserved throat/source position, a valid outer shell, or a faithful reproduction of the original construction. A canonical sampled surface is the comparison and interchange layer; it is not itself a generator or proof that a new parameterization has inherited a solve.

X1 materialized 50 of 60 sampled designs across five routes; the current generic Klangfilm adapter rejected all ten saved recipes. The legacy kernel produced repeatable *candidate* grids while bypassing digest verification, so neither recovery nor impossibility is established. Experimental 31 × 65 records omit required metadata and have unvalidated throat interpolation and arc correspondence. The physical wall tag includes more than the inner wall, so its reported patch distances are not inner-wall fit errors. Rolled bbox depth differs by roughly 3 mm with closure identity unresolved. In-sample PCA of those 50 grids is exploratory, not a held-out fit or a contract pass. X2 is likewise undetermined: all 144 two-plane surrogate variants were outside its distance diagnostic; diagonal and lip acoustic effects were unobservable. A geometric Jacobian residual is not evidence of response authority. Klangfilm Stage A is a caution about its tested additive adjustments, not a general verdict on structural freedoms.

### Execution order and decision gates

1. **Finish X1 first (A1).** Reconstruct each of the six routes from its stored `design.json` and run `config.yaml`; investigate historical Klangfilm adapter, driver and implementation digest before comparing to its stored mesh. Establish inner-wall versus exterior/closure identity, source plane, throat, termination, shell, mounting, symmetry and topology. Run all five `CANONICAL_SURFACE_CONTRACT.md` §8 tests, including simultaneous arc/azimuth refinement, validated patch distances, full envelope and exact metadata. Report per-lane pass/fail and tolerances, including unresolved routes; do not upgrade the existing sample files into accepted records by assertion.
2. **U1 follows usable X1 targets.** Use the four named lanes and own-law reconstruction specified in the brief, then independently compare generic wall-angle splines with 4, 6 and 8 controls per rib. Record median, p95, worst and location on the whole surface. The predeclared pass is worst ≤ 0.5 mm in at least three of four lanes; two or more above 2 mm is the failure criterion, with the middle region explicitly inconclusive. Exact-looking principal ribs or a low average do not establish the worst-point gate, preserve metadata, or authorize reuse of an old acoustic response. A later four-surface solve confirmation is proposed separately and needs owner approval.
3. **U2 depends on U1 endpoint descriptions.** Interpolate three distinct cross-family pairs in ten equal steps and report each validity check and overlay at every step. Two of three fully valid paths meet the *CPU geometry* success line; two paths with invalid stretches longer than two steps meet the failure line. Neither result proves acoustic continuity or that a single optimizer can traverse the space. Mark surrogate predictions outside the training-distance diagnostic and treat even inside predictions as indicative. The proposed two paths of eleven BEM solves each require owner approval.
4. **U3 depends on the U1 best-design description.** Construct the seven individually paired variants in the brief: two vertical-timing strengths, two termination splits, two section-steering variants and one diagonal pull. Apply the U2 validity checks and report dimensions and minimum lip radius; the CPU success line additionally requires each variant to change the surface by at least 5 mm RMS somewhere outside the last 5% of the wall. This establishes geometric reach only. The proposed control, variants and repeats need owner-approved solves; the prespecified ≥3° intended-plane rule and cross-plane limit decide acoustic authority under that test, not across all horns.

### Practical starting points and traps

Start with `X1_ROUND_TRIP.md` and `.x1/probe.py`, `.x1/legacy_k.py`, `.x1/patch_distance.py` and `.x1/envelope.py` as *investigative artifacts*, preserving existing outputs before any rerun. Follow `VALIDATION_EXPERIMENTS.md` X1 and U1 for the six routes, four U1 lane identifiers, acceptance criteria and source locations. Compare the existing partial constructions in `hornlab_search/design/generators/grid.py`, `crowe_hv_area_aspect_v1.py`, and `tools/geometry/klangfilm_lame_hv_core.py`; read the Le Cléac’h shared-station research cited by U1 before selecting correspondence. Scripts and reports belong under `scratch/fable_architecture/` in task-specific dot-folders. Do not run solves, pytest, process control or git mutations, and do not modify source, configs, queues, `runs/`, or `examples/`.

Preserve counterexamples: extended throats whose driven plane is not the first station; unequal rib lengths and rollback lips; nonuniform polar sampling; corners and morphs that a single section exponent plus diagonal term cannot represent; shells that set the envelope; and interpolation paths that appear smooth only because a surrogate averages. Check whether a claimed neutral layer actually reproduces the original surface and metadata. Keep geometric validity, intended physical construction and solved acoustic success separate; equal area does not prove equal loading or directivity. Do not change a split or threshold after seeing results, and report partial or inconclusive outcomes instead of substituting a more favorable test.
