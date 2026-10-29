# Cone-driven mid horns with a central plug ("axe-head", Funktion-One / Turbosound school)

2026-10-28. Owner request: understand how Funktion-One mid horns with the central "waveguide" / phase plug
("axe heads") work, find published math, and plan how hornlab-search can model a large cone (8-15") loaded by
a horn with a plug in its throat. **Research + plan only. No GPU, no code yet.** Labels: [published] = patent
or author text; [practitioner] = DIY forum / builder reports; [inferred] = our physics reading; [verify] = a
formula we quote from memory of a paywalled paper and must check before code relies on it.

## 1. Source table

| Source | What it gives us | Status |
|---|---|---|
| US6557664B1 "Loudspeaker", A.J. Andrews + J. Newsham, priority 1992-09-15 (https://patents.google.com/patent/US6557664B1/en) | **The axe-head itself**: non-axisymmetric central member in front of a cone; vertical-plane profile tapers out along the cone then in to a point; horizontal-plane profile tapers out then runs nearly straight, then tapers abruptly; channel divergence "abruptly increases" at a transition whose position varies along the channel; rear surface sits within the voice-coil diameter, gap to the cone "substantially in excess of maximum displacement"; claims horn-like efficiency without horn colouration, better phase coherence | primary (patent, expired) |
| US6650760B1 "Loudspeaker", Andrews, Hunt, Newsham, assignee Funktion One, priority 1999-07-14 (https://patents.google.com/patent/US6650760B1/en) | **Loaded upper-bass / low-mid**: cone + circular central member in four parts (into the cone; reducing area; constant through the throat; hemispherical nose into the horn); ring channel that expands, then contracts (compression), then a slowly expanding ring throat, then a faster horn; rectangular housing with parallel top/bottom (constant height) and varying width; channel folded for size; "about 75 to about 750 Hz", 107 dB 1 W/1 m, wide uniform horizontal dispersion | primary (patent, expired) |
| US4836327A, Andrews, Hunt, Newsham, Turbosound, filed 1986 (https://patents.google.com/patent/US4836327A/en) | **Coaxial predecessor**: 15" cone (3" coil) with an annular central member whose rear surface is parallel to the cone; minimum cone gap ~0.25"; path-length increase < 4"; a constant-area "plane wave tube"; HF compression driver through the voice-coil opening; crossovers ~100-150 Hz and >= 2.4 kHz; the cone "radiates from progressively smaller regions centred around the voice coil" at HF | primary (patent, expired) |
| Jumble Blue, "What nobody tells you about Funktion One" (https://www.jumble.blue/en/what-nobody-tells-you-and-admits-about-funktion-one/) | F1 practice: paper cone across the vocal range (8" up to ~6.5 kHz in some boxes), high mid/HF crossover, "famous axe-head phaseplugs" from Andrews' 1970s work | secondary (practitioner/critic) |
| diyAudio search excerpts: "Cone midrange horn 101/201", Ax88 plug thread (https://www.diyaudio.com/community/threads/cone-midrange-horn-101.287154/, https://www.diyaudio.com/community/threads/back-of-10-mid-horn-phase-plug.387764/) | The axe-head makes "in essence a ring radiator": equalises path/time before the throat and reduces chamber volume; after the throat it is part of the horn expansion. Design order: pick the compression ratio Sd/St first; plug annulus just outside the dust cap (where the second front-cavity node sits); clearance > xmax. Thread bodies returned 403 today: only search excerpts read | secondary (practitioner reports), partly unread |
| Centauri Audio, phase plugs (http://www.centauriaudio.com.au/diy/plugs.html) | Builder geometry: a 12" cone has up to ~100 mm path difference (half a wavelength at 1.72 kHz); a small throat spread evenly over the cone, close to it; three plug types (cone, cone + ring, bullet + toroid) with prototype sizes | secondary (practitioner) |
| Keele, "Low-frequency horn design using Thiele/Small driver parameters", AES conv. 57 paper 1250, 1977 (https://www.aes.org/e-lib/browse.cfm?elib=3105) | Standard closed-form cone-horn design (upper mass corner, front-chamber corner, throat area, rear chamber) from T/S parameters | primary, **paywalled - formulas below are [verify]** |
| Hornresp (D. McBean, freeware) | The enthusiast reference 1-D model: driver + rear chamber + throat chamber (Vtc, Atc) + segmented horn; the de-facto cross-check DIY cone-horn builders publish | tool (cross-check target) |
| In-repo: `hornlab_search/driver/compression.py`, `docs/DRIVER_MODEL.md`, `hornlab_search/mesh/step_build.py`, `tools/cad/multicell.py` | We already have the lumped circuit (front + rear chamber) and a CAD -> labelled STEP -> BEM mesh route with one `driver` face | verified (in repo) |

## 2. What these horns are and why they work

**The problem they solve [published + inferred].** A 10-15" cone playing 300 Hz-4 kHz direct beams badly above
~1-1.5 kHz (the cone is wider than the wavelength) and different parts of the cone reach your ear at different
times (the edge is ~50-100 mm further back than the centre). A plain horn on a cone fixes efficiency but the
big front chamber between cone and throat resonates and "honks", and the path differences across the cone smear
the top of the band.

**The plug fixes both [published].** A solid body sits in front of the cone, close to it:
1. It **fills the front chamber**, so the compression chamber is small and its resonance moves above the band.
2. It **forces the sound through a ring (annulus)** near the voice coil, where the cone still moves as a whole
   at high frequencies (Turbosound: the cone radiates from ever-smaller regions around the coil). The ring has a
   smaller area than the cone - the compression ratio Sd/St (practitioners: decide it first) - which raises
   efficiency.
3. It **equalises path lengths**: every bit of the ring has the same distance to the horn, so the wavefront
   leaving the throat is coherent ("ring radiator").
4. Past the throat it **is part of the horn**: the gap between plug and walls is the horn's expanding area.

**The axe-head specifically [published, US6557664].** The plug is NOT round at the front. In one plane it closes
to a point (a knife edge); in the other it stays wide and flat, then closes abruptly. The channel around it
therefore opens at **different rates in the two planes**, and the point where it suddenly opens faster moves
along the channel. Result: a **wide horizontal, narrower vertical** pattern from a round cone, with lower
impedance in one plane than the other. The 1999 patent adds a constant-height, variable-width rectangular
housing (parallel top and bottom walls) - a horizontal-only flare, i.e. wide, even horizontal coverage.

**Why it sounds good (claims, [practitioner]).** A paper cone has far lower moving-mass-per-area stress than a
compression diaphragm at the same SPL, so lower distortion in the vocal band; one driver covers the whole
vocal range (no crossover through it); horn efficiency (F1 quotes 107 dB/1W for the loaded low-mid). These are
listening claims, not measured comparisons we have seen.

**Known weaknesses [inferred + practitioner].** Big boxes; the plug blocks the centre so the HF must go
elsewhere (a separate HF horn, or the HF driver through the plug as in the Turbosound coax); a fixed
compression ratio raises cone excursion and air-load nonlinearity at high level; the top of the band is still
limited by cone breakup; vertical lobing between stacked boxes.

## 3. Published / standard math (inputs for a first design)

| Quantity | Rule | Label |
|---|---|---|
| Compression ratio | Sd/St, chosen first; cone mids typically 2-5 (St = ring/throat area) | [practitioner] |
| Plug gap | > xmax at full power (Turbosound minimum ~6 mm on a 15") | [published] |
| Plug ring position | just outside the dust cap / within the voice-coil diameter | [published] + [practitioner] |
| Path difference | max cone-to-throat path difference < lambda/4 at the top of the band (Centauri's example: 100 mm = lambda/2 at 1.72 kHz) | [practitioner] + [inferred] |
| Front chamber corner | V1 between cone and plug acts as a compliance C = V1/(rho c^2) shunting the throat resistance rho c/St: f_c ~ c St / (2 pi V1) | [inferred] first-order (Keele's exact form [verify]) |
| Mass corner | f_HM ~ 2 fs / Qts (upper half-power from moving mass) | [verify] Keele 1977 |
| Horn lower limit | mouth circumference ~ wavelength at the lowest frequency; constant-directivity width by our K-law 25.4e6/(f0 * coverage) mm | [published] (K-law already in repo) |
| Loaded band (F1 1999) | ~75-750 Hz from a single cone, ~1 decade | [published] |

## 4. Can hornlab-search model it? (inventory)

- **Geometry:** the parametric generators build a horn from a round throat outward; they cannot place a solid
  body inside the horn or start from a cone. The **CAD route can**: `tools/cad/multicell.py` builds a build123d
  solid, writes a labelled STEP (`driver` + `wall` faces) and `mesh/step_build.py` meshes it with the driver
  face as tag 2. A plug + annulus + chamber + horn is one solid; the radiating face can be the cone itself.
  [verified: route exists; a plug geometry was never built]
- **Solver:** BEAT applies a uniform unit normal acceleration on tag 2. A flat annular/disc piston at the cone
  plane is exact rigid-piston motion; a true conical face gets normal (not axial) motion, i.e. a cos(cone
  angle) scale plus a small error - acceptable for v2 only. [inferred]
- **Driver:** `driver/compression.py` already has Bl, moving mass, Cms, front chamber V1 and rear chamber - the
  same circuit as Keele/Hornresp. A cone driver is a data file (Sd, Mms/Mmd, Cms or fs, Bl, Re, Le, rear box
  Vb). Mms includes the driver's own air load (flagged today; acceptable for cones with a note). [verified]
- **Size:** a 300 Hz-3 kHz mid horn with a ~600-900 mm mouth meshes at lambda/6 ~ 19 mm at 3 kHz; with two
  symmetry planes (the axe-head has both) a quarter model should land near the 12k dof cap. A 75-750 Hz loaded
  low-mid needs ~76 mm elements - cheap per frequency but huge mouths. [inferred; to measure]
- **Out of scope until the owner says so:** the coaxial HF-through-the-plug version (Turbosound 1986) is a
  two-source horn - the multi-entry class the owner deferred on 2026-10-24. The plan keeps the HF as a separate
  horn and the plug solid.

## 5. Implementation plan (zero GPU until step 5)

1. **WP-M0 1-D design calculator** (`tools/cone_horn_1d.py`, CPU): Hornresp-style chain - cone driver T/S +
   rear box + front chamber V1 + ring throat St + segmented horn (conical/exponential/OS sections, Webster) ->
   throat impedance, SPL, excursion, f_c, f_HM. Validate: reproduce a Hornresp example within 0.5 dB (owner or
   forum-published Hornresp inputs/outputs), and check Keele's formulas against it before we use them.
   Deliverable: starting dimensions for 10", 12", 15" cones.
2. **WP-M1 driver files**: cone T/S files in `examples/drivers/` (data-only, same loader; add `kind: cone`,
   `rear_box_l`). Candidates: horn-mid 10"/12" from B&C (e.g. 10MH/12MH series), Faital, 18 Sound, Beyma -
   to be researched like the compression library, published T/S only.
3. **WP-M2 CAD generator** `tools/cad/cone_midhorn.py` (build123d, optional `cad` extra), knobs:
   cone diameter + depth; plug gap g (> xmax); plug type `bullet` (US6650760: circular, 4-part) or `axehead`
   (US6557664: two plane profiles, knife-edge vertical, flat horizontal, abrupt nose); ring throat area via
   Sd/St; front chamber V1 reported; horn = constant-height H-flare (1999 patent) or OS walls with per-plane
   angles; mouth W x H; rollover radius. Faces labelled `driver` (flat annular piston at the cone plane in v1)
   and `wall`. Quarter-symmetric. Guards: gap > xmax, path difference < lambda/4 at f_top, V1 corner > f_top.
4. **WP-M3 brief + objective**: `cone_mid_10in_250_3k` style briefs: band ~250-3000 Hz, coverage 90x40 (F1
   style wide H) or 70x50, envelope, crossover to HF at ~3-4 kHz and to bass at ~150-250 Hz. Score: our v4
   terms + throat loading over the band + a coherence proxy (group-delay spread across angles at the top of the
   band) - the coherence term is a NEW priority and needs the owner's approval.
5. **WP-M4 first GPU** (later, owner go): mesh-only checks (CPU) for 3 seeds (bullet 12", axehead 10", axehead
   12"), then one screen solve each, compared with the 1-D calculator (loading and level must agree below the
   first cross-mode).
6. **WP-M5 print + measure**: 10" axehead prototype; measure SPL/impedance/polars against the model.

**Starting point (to be re-derived by WP-M0, not final):** 12" cone (Sd ~ 0.05 m^2), Sd/St 3 (ring area
~ 170 cm^2), plug gap 8 mm, ring centred just outside the dust cap, axe-head nose length ~ 1 cone radius,
constant-height H-flare 90 deg x ~40 deg, mouth ~ 700 x 300 mm, band 250-3000 Hz. [inferred from the patents'
proportions and the K-law; no published F1 dimensions were found]

## 5b. Corrections table: an owner-pasted description checked against the patents (2026-10-28 19:10)

The owner pasted an outside AI's description ("three-zone area function"). Checked against the US6650760 claims
(re-fetched in full) and the US6557664 description:

| Pasted claim | Verdict | What the patents say |
|---|---|---|
| The "Axhead" is a central solid of revolution, circular | **Wrong device** | The circular four-part member is US6650760 (1999, the 75-750 Hz loaded low-mid). The axe-head is US6557664 (1992) and is explicitly **not** circularly symmetric (knife-edge in one plane, flat in the other). Two topologies, two typologies. |
| Region 1 = "the nose inside the cone", hemispherical/ogive | **Inverted** | The part inside the cone is portion 1, whose area *increases* toward the front (it follows the cone). The **hemispherical end is portion 4, at the front, projecting into the horn**. |
| Channel: area increases (inside cone) -> decreases -> throat -> flare | **Correct** | Region 1 increases, region 2 decreases, throat increases at a first rate, horn at a second, greater rate. |
| "Horn rate greater than the first rate in Region 1" | **Wrong reference** | The "first rate" is the **throat's** slow expansion; the horn expands faster than the throat. The throat is a short slowly expanding ring, not a single minimum point. |
| Throat = minimum annular area | Partly | The minimum is at the end of region 2 / start of the throat; the member is constant-section through the throat (portion 3) while the channel grows slowly. |
| Independent H and V conical flare angles (examples 50x25 etc.) | **Not in the source** | US6650760's housing is rectangular with **parallel top and bottom (constant height)** and varying width: a horizontal-only flare. The example angles are not published. |
| "Fancy angles are dispersion control, not phase-plug maths" | Half right | For the 1992 axe-head the plug **itself** shapes dispersion: two plane profiles give "lower acoustic impedance in one plane than the other". |
| Plug "blocks the centre where HF would cross-cancel" | Imprecise | It does sit in front of the centre (inside the voice-coil diameter, gap > xmax), but the centre's output is not discarded; it leaves through the gap. The gain is a small chamber and one ring-shaped exit. |
| Equal-path equation with "extra path added by the nose", Delta(r) | **Not published; mechanism inverted** | Neither patent states an equal-path equation (US6650760: none found). A solid body cannot add path to the centre; equalisation comes from a thin gap that follows the cone and from where the ring exit sits. The formulation we will use is in 5c. |
| Forum quotes ("ring radiator", "eats compression chamber volume", "part of horn expansion") | Consistent | Matches the diyAudio excerpts read (section 1). "More a part of the horn than a phase plug" was not read by us (thread 403). |
| The channel is folded | Missing from the paste | US6650760: folded at the region 2 / throat transition, for size. |

## 5c. Parametric definition for hornlab-search (two typologies, labelled hypothesis shapes)

Axial coordinate z from the cone's voice-coil plane toward the mouth. All profiles are smooth (C1) splines
between named stations. Names stay neutral (R9 rename gate): `cone_plughorn_bullet` and `cone_plughorn_axe`.

**Common: the cone.** Cone radius Rc, depth dc (cone surface z_cone(r) linear from the coil radius r_vc to Rc),
dust-cap radius r_dc, xmax. Driver face (BEM tag 2): v1 a flat annulus at the cone mouth plane; v2 the conical
surface.

**`cone_plughorn_bullet` (US6650760 topology, circular member, rectangular housing):**
- Member radius r_c(z) through stations: S0 rear tip (inside the cone, at gap g >= 1.5 xmax from the cone
  surface) -> S1 max radius r_cmax (portion 1, area increasing, rear surface parallel to the cone at gap g) ->
  S2 throat start (portion 2, radius decreasing) -> S3 throat end (portion 3, constant radius r_ct) -> S4
  hemispherical nose of radius r_ct (portion 4).
- Housing: rectangular, constant height Hh, width w(z); region 2 contracts so that channel area A(z) =
  Hh*w(z) - pi*r_c(z)^2 falls to A_t at S2.
- Hard constraints (the patent's signs): dA/dz > 0 in region 1; dA/dz < 0 in region 2; throat expansion rate m1
  > 0 small; horn rate m2 > m1. Compression ratio Sd/A_t is a knob (box 1.5-5).
- Horn: width flare law beyond S3 (conical / exponential / OS, half-angle theta_h); height constant (patent) or
  an optional small vertical flare as a labelled extension. Optional fold: not modelled in v1 (BEM of the
  straight version first).

**`cone_plughorn_axe` (US6557664 topology, non-circular member):**
- The member is lofted through superellipse cross-sections whose half-width b_h(z) and half-height b_v(z) follow
  two separate plane profiles:
  - vertical plane: tapers out along the cone (gap g) to a transition z_tv, then tapers in progressively to a
    knife edge at the nose z_n;
  - horizontal plane: tapers out to z_th, runs almost straight (taper <= a few degrees), then closes abruptly
    over a short length L_ab near z_n.
- The channel wall gets a divergence break ("abruptly increases") whose position z_b(phi) varies with azimuth;
  parametrise z_b(phi) = z_b0 + dz_b * cos(2 phi).
- Corner fillets between member and channel (patent: fillets the corner portions).
- Horn beyond the nose: OS or conical walls with separate H/V angles; the axe-head sets which plane is wide.

**Path coherence objective (replaces the pasted Delta(r) equation).** For each radiating point on the cone at
radius r, the travel time to the ring exit is t(r) = (gap path from r along the cone/member gap to the ring
radius r_ring + straight distance from the ring to the throat plane) / c. Geometric guard: spread
max_r t - min_r t < 1 / (4 f_top). The real check is BEM: group-delay spread across angles at the top of the
band (WP-M3 term, owner approval).

**Seeds (inferred, to be re-derived by WP-M0):** 12" cone Rc 0.13 m, dc 0.045 m, r_vc 0.05 m, xmax 6 mm ->
g 9 mm; Sd/A_t 3; bullet: Hh 0.20 m, theta_h 45 deg, horn length 0.45 m; axe: z_n ~ Rc ahead of the cone
plane, knife-edge vertical, flat horizontal, horn 90 x 40 deg.

## 5d. From Funktion-One's CAD (2026-10-28 20:00, supersedes 5c's image-based reading)

The owner supplied the Evo 7SH and Evo 2SH 3D models. Read values (mm, depth behind the front face):

| | Evo 7SH (40 x 20) | Evo 2SH (50) |
|---|---|---|
| throat (driver plane) depth | 400 | 223 |
| throat octagon | (+-90, +-22.5), (+-15.6, +-90) | (+-73, +-15), (+-1.8, +-73) |
| wall end side / top | x 252.2 @ 18.3 / y 162.3 @ 24.3 | x 204.3 @ 9.3 / y 123.8 @ 13.2 |
| front opening | 559.6 x 383.6 | 431.8 x 274.0 |
| axe head nose / tips | 12.7 / +-203.2 @ 66.8 | 16.5 / +-154.8 @ 52.1 |
| ridge end / corner | +-67 @ 231.4 / (+-87.1, +-68.3) @ 258.8 | +-49.7 @ 134.7 / (+-59, +-50.6) @ 150.5 |
| axe-head base (throat plane) | (+-75, 0), (+-28.6, +-75) | (+-60, +-10.9), (+-18.8, +-55) |
| bowl | r 130 -> 114.7 @ +145, back r 65 @ +190 | r 105 to +88, back r 52.7 @ +136 |

Walls: one flat top plane and one flat side plane from the throat octagon to the wall end; corner panels are ruled
(twisted) quads; the roll-out is a circular (cone-surface) roundover. The axe head's four front faces are planar (corner
within 0.01 mm of the nose/tip/ridge plane). The axe-head base sits on the throat plate leaving ~2.4 mm at the throat
diagonals: the compression ring (5.0:1 and 7.5:1 against a 10-inch / 9-inch cone). The simplified 3D models carry no
driver: the cone size is an assumption. Section 5c's crease-point / ruled-top reading came from the Evo 7 EH drawing
and is superseded for the SH horns.

## 6. Open gaps

- No F1 production drawings or dimensions are published; the patents give shapes and relations, not numbers.
- Keele 1977 formulas are paywalled here; marked [verify].
- diyAudio thread bodies (Ax88 plug, cone horn 101/201) returned 403; only excerpts were read.
- Whether BEM with a flat piston at the cone plane captures the cone-to-plug chamber modes well enough must be
  measured (WP-M4 vs a conical driver face).
