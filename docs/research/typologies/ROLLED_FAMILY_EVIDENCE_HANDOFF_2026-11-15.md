# Crowe / ATH / rolled-family evidence and readiness handoff

2026-11-15. **Documentation-only preservation pass, requested by the owner.** Read this before
changing these families, their bounds, briefs, optimization mappings, or readiness claims.
This is an evidence ledger and audit brief, not approval of a design or a new search night.

## 1. Current authority and scope

- Canonical checkout: `C:/Users/hunte/Hrns/hornlab-search`; observed branch
  `feat/sab-home-2026-11-14`, HEAD `7124902d5296c2943384068f2b740b433e6b2f01`.
  The working tree contains substantial concurrent, uncommitted work. HEAD alone does not
  describe the reviewed packet or current geometry. See the evidence manifest below.
- The latest owner hold recorded in `docs/CONTINUITY.md` (17:15 local) pauses **all new solves**
  until the brief/DI-slope question is investigated and settled. It records night E stopped
  near 62/96 rows, GPU cleanup, and no night F. Preserve that hold; refresh live state on pickup.
- The owner wants the old three designs and subsequent reference/pucker variants preserved.
  Do not replace or remove them to introduce a corrected typology. Preserve prior recipe/source
  identities, datasets, queue history, renders, and unique dirty work.
- This pass changed documentation/evidence only. No generators, bounds, briefs, optimizer
  settings, queues, solves, process state, or existing decision-packet content were changed.
- **Readiness conclusion: not established.** Sampled mesh feasibility and optimizer/replay
  integration have evidence. Adequate design freedoms, correct objective, faithful Crowe
  construction, robust complete-domain geometry, and converged acoustic performance do not.

### Read together, in this order

1. `docs/CONTINUITY.md`, `docs/ISSUES.md`, `NOTES_FOR_SENIOR.md` (latest owner instructions).
2. This ledger and its [saved evidence manifest](evidence_rolled_family_handoff_2026-11-15/manifest.json).
3. [Six-seed decision packet](STARTING_SEEDS_2026-11-15.html),
   [plain brief](STARTING_SEEDS_PLAIN_2026-11-15.md),
   [current study](BIRADIAL_CROWE_STUDY_2026-11-15.md),
   [source dossier](BIRADIAL_CROWE_SOURCES_2026-11-15.md),
   [white-paper notes](HORN_WHITEPAPERS_2026-11-15.md), and
   [scoring sources](SCORING_NON_CD_SOURCES_2026-11-15.md).
4. [Master correction](ROLLED_FAMILY_MASTER_RESEARCH_2026-11-15.md),
   [earlier construction research](ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md),
   [archived axial relief](SECTION_PUCKER_RESEARCH_2026-11-15.md), and
   `docs/research/CROWE_X_HORN_HANDOFF_2026-11-15.md` (historical, not current authority).

Labels below distinguish primary-source statements, our construction, saved execution evidence,
another agent's report, and unresolved hypotheses. An old document calling something
"validated" does not establish every later acceptance gate.

## 2. Primary research that must survive the handoff

| Source and scope | What it supports | What it does not establish |
|---|---|---|
| [Crowe ES-600 article](https://croweaudio.blogspot.com/2019/11/es-600-biradial-horn.html), [author CAD page](https://josephcrowe.com/products/es-600-bi-radial-horn-3d-cad-file), [drawing 1148-01-001](https://cdn.shopify.com/s/files/1/0142/2848/8292/products/1148-01-001.jpg?v=1586452428) | Author geometry/photos and distinct H/V sections; drawing-based reference approximately 417 W x 203 H x 198 D mm, 35.56 mm throat. Retain drawing/model identity. | A verified proprietary ES equation, independent acoustic validation, exact intermediate 3D surfaces, or permission to call our reconstruction exact CAD. |
| [ES-800 drawing](https://cdn.shopify.com/s/files/1/0142/2848/8292/files/ES-800.PDF?21=), [ES-250 partial/full wrap models](https://josephcrowe.com/products/es-250-biradial-no-2213-3d-cad-files-plans) | Other members and different termination constructions exist. ES-800 dimensions are a different reference from ES-600. | Interchangeable dimensions, common section laws, or superiority of a particular wrap angle. |
| [Crowe circular-baffle paper](https://cdn.shopify.com/s/files/1/0142/2848/8292/files/ES_Circular_Baffle_White_Paper.pdf?19=) | Author comparative measurements in that mounting context. | The ES bi-radial construction equation or an independent test of our free-standing hybrid. |
| [Batík Tritonia](https://at-horns.eu/tritonia.html) and [original public configuration](https://at-horns.eu/ext/Tritonia.txt) | Azimuth-dependent OS-SE parameters followed by rectangle morph; H/V/diagonal differences are deliberate. | A generic axial cosine displacement, a universal requirement for concave mouths, or an HF1440-compatible driver definition. |
| [OS-SE paper, sections 2–5 and conclusion](https://at-horns.eu/release/OS-SE%20Waveguide.pdf) | Radius r(z,phi), coverage parameter convention, smooth analytic flare/termination and radial mouth morph. Its conclusion distinguishes baffle termination from additional free-standing rollback. | Crowe replication, an arbitrary thick exterior body, or proof that any visually puckered shape improves sound. |
| [R-OSSE rev7](https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf) | A separate parametric construction for free-standing return geometry. | An interchangeable name/equation for OS-SE, a source-derived Crowe law, or a single-valued r(z) representation of a folded return. |
| [ATH 4.8.2 guide](https://at-horns.eu/release/Ath-4.8.2-UserGuide.pdf) | Morph fixed region, rate, target outline, no-shrink policy and sampling conventions must be traced to the actual implementation/version. | A guarantee that changing one nominal mouth control preserves every other acoustic property. |
| [Keele US4308932A, description around Fig. 2 and equations 1–6](https://patents.google.com/patent/US4308932A/en) | Separate wall-pair construction; included throat angle A approximately 0.9 times full beamwidth B; empirical mouth-size relationship; sidewall slope uses tan(A/2). | Proof Crowe uses this patent's law, a slot-free implementation's equivalence, or a universal hard diffraction limit. |

Sources were researched earlier in this work. This preservation pass re-opened the Tritonia
configuration, OS-SE paper, Crowe CAD page, and Keele patent. The drawing readings and other
links retain their prior-study provenance; they were not independently redigitized here.
The source files and original study documents, rather than a remembered product name, govern.
Keep copyrighted reference photos in their existing local research location; do not publish
them as our work. The manifest saves our own audit artifacts, not vendor image copies.

### Exact mechanisms, with limits

**ATH:** the public Tritonia configuration varies its nominal half-angle as
`alpha(phi) = 48.5 - 7*cos(2*phi)^5 - 16*sin(phi)^12` degrees, with
`s(phi) = 0.7 + 0.2*cos(phi)^2`, `k=1`, `n=3.7`, `q=.995`, then morphs to a rectangle.
At H / geometric 45-degree / V azimuths, alpha is 41.5 / 48.25 / 39.5 degrees.
These parameter values are not measured beamwidths. Its published diagonal polar setting is
42 degrees, so our normalized-coordinate diagonal must not silently be called its measured cut.
The script literally uses `r0=36` mm despite the page's 1.4-inch description. Resolve that
source discrepancy before copying a driver definition; our HF1440 study uses radius 18 mm.

The OS-SE morph is a radial displacement at fixed z, gradually approaching a target outline:
`r_m = r + ((z-z_f)/(L-z_f))^gamma * (r_M(phi)-r(L,phi))` after the fixed part.
The sign depends on the target and the no-shrink policy. The raw angular law may make axis
regions smaller relative to diagonals without every final wall moving inward. Therefore
"ATH means move the whole mouth inward" is too broad.

**Our original inward hybrid:** normalized `psi=atan2(y/v,x/h)` and window W(s) give
`rho_new = rho - W(s)*(H*cos(psi)^2 + V*sin(psi)^2)*cos(2*psi)^2`.
Positive H/V move the wall centres inward, leave the normalized diagonal unchanged, and leave
z unchanged. This was introduced to correct the axial/radial confusion. It is an original
hybrid applied to two existing bases, **not a reconstruction of Tritonia's complete surface**.
Its window coordinate is reference arc progress, not automatically percentage of axial depth.
The rolled-rectangle and section bases use different safe onset locations (.50 versus .30).

**Crowe:** separate axis cuts do not uniquely specify the 3D joining surfaces. Intermediate
azimuths, transverse crown, junction, visible occluding contours, body/underside and lip closure
need their own construction and evidence. An X/eye appearance cannot be recovered just by
scaling a rounded rectangle or averaging H/V curves at equal loft progress. ES means the
author's exponential-spiral family; it must not be silently equated to a Webster exponential
area law, our analytic spiral, Keele's bi-radial, Arai, OS-SE, or R-OSSE.

## 3. Error and correction ledger

| Earlier mistake or unsafe inference | Correction to preserve | Remaining limitation |
|---|---|---|
| Calling z-only mouth relief ATH-like radial puckering | Archived `tools/geometry/section_pucker.py` changes z while preserving x/y. Reversing its sign still does not make it radial. Keep those original studies under their own identities. | Their visual/acoustic value remains a hypothesis; do not erase them. |
| Treating raw axial amplitudes as total ridge relief | With H=4, V=6 at the window peak, axial centres are +4/+6 and diagonal -5 mm: centre-to-diagonal relief is 9/11 mm. | Document measurement frame and location whenever comparing amplitude. |
| Claiming a first rounded-rectangle/spiral render was an exact Crowe horn | Our independent analytic spiral and later manually digitized section reconstruction are different approximations. The public sections constrain the latter; inferred joining/body surfaces remain inferred. | Exact proprietary intermediate CAD was not available to this work. |
| One shared H/V contour or globally averaged loft | Preserve distinct section laws and test intermediate planes. Front view, sections, oblique view and underside must agree with the same model reference. | Our section sweep and reconstructed exterior are not established as Crowe's manufacturing construction. |
| Using appearance/mesh success as proof of useful optimization | A narrow shape pilot with fixed W/H is not broad control of coverage, loading, waist and termination. | Independent point-cloud Jacobian columns do not prove independent acoustic effects. |
| Cold worker depended on research scripts/wrapper patching | Canonical native family dispatch and packaged private kernels/data were added. A third-party installed `tools` package had shadowed the research namespace; canonical imports were isolated. | Verify every newer bridge/GUI/config path still resolves to the same master. GUI exposure alone is insufficient. |
| Treating family BO support as an existing valid acoustic cohort | Synthetic GP smoke used 16 artificial observations and eight candidates, no BEM. Older generic grid rejection and later morph-off encoder rejection were distinct integration issues. | Current owner production gate is >=100 usable matched solves; the synthetic demonstration does not meet it. |
| Missing rare inverse-curve NaN at the returned tail | Private `_crowe_section_v2._sweep` gained branch-specific clipping after physical-domain checks. Pre-fix control audit was 63/64; corrected saved audits are separate files. | Do not silently relabel failed historical artifacts as passing or change archived source identities. |
| Calling 18-to-29 frequency verification mesh convergence | The referenced pilot reused the same spatial mesh (section winner 3,084 DOFs) while adding frequency samples. | Both spatial refinement and frequency refinement must be examined separately. |
| Assuming more parameter motion means better horn design | Master controls move geometry reproducibly; that is a software property. | Coverage/loading/termination effectiveness and parameter interactions still require physical and acoustic evidence. |

The archived original three designs and later reference/axial/radial variants are different
experiments. Do not combine their datasets merely because images look similar or names share
"Crowe", "rolled", "pucker", "ES", or "ATH".

## 4. Audit the new packet too; do not promote it to ground truth

The six-seed HTML is a useful decision packet. Its issue log is a list of claims and leads,
not completion of their independent verification. These corrections/qualifications must accompany it:

1. **K-law convention now checked against the patent:** plain brief section 1 uses full beamwidth;
   section 2 calls A `0.9 * half-coverage`. The latter wording conflicts with the patent: A is
   included throat angle, B full beamwidth, `A=.9B`, and slope is `tan(A/2)`.
   `W=25000/(.9*B*f)` yields approximately 496/794 mm at 700 Hz for 80/50 degrees,
   and 1157 Hz for 480 mm / 50 degrees. These are predictions of an **empirical design
   relation**, not a universal impossibility theorem. Recheck each code parameter's half/full
   convention separately. Mouth size alone is not an exact polar prediction.
2. **Brief/DI slope:** 0 slope is a chosen design target, not inherently a software error.
   Smooth narrowing can be appropriate, but author-measured slopes are not universal listening
   optima. The reported 2.6/4.1 dB/oct need extraction method, fit band, DI source and units;
   dB/oct and dB/dec are different. No primary basis was established for "Harman prefers
   1–3 dB/oct". Do not substitute a guessed nonzero target for the old guessed target.
3. **Diagonal score:** the report says `_diag_term` uses the mean H/V target (65 degrees for
   80x50). Audit the formula and its intended geometric reference. A constant diagonal target
   may be inappropriate; it does not follow that all diagonal penalties are unfair or that
   a crease has no acoustic cost. Separate smoothness, lobing and target coverage using actual
   angular data. No independent measured diagonal validation was established by this work.
4. **"Shape-only" controls:** crown, pucker, waist, corner transition and junction change a
   physical boundary. They may alter area, modes, loading and diagonal response. Say
   "no demonstrated independent/monotone acoustic control" where that is the evidence.
   Absence of a published acoustic requirement for a waist is not evidence of zero acoustic effect.
5. **Return vocabulary:** distinguish a meridional curve turning back, a thick underside bead,
   and a valid exterior solid closure. Some analytic curves do return; that does not reproduce
   Crowe's thick body. A blanket "no true return" hides the actual construction gap.
   Our 270-degree curve parameter, a physical tangent rotation and an author's wrap claim
   are not interchangeable. No wrap angle was shown acoustically optimal.
6. **Fold report:** the current agent reports 153–176-degree outer-junction folds/inverted
   triangles. Treat the affected scores as provisional. Before diagnosing or rebuilding,
   retain original meshes and inspect triangle roles, winding, normal/dihedral convention,
   local clearance and intersections. This pass did not independently reproduce that test;
   centre-plane plots cannot certify every off-plane junction.
7. **Mesh/source assertions:** 6 EPW does not imply a universal 10% acoustic or frequency
   error; 8–12 EPW is not automatic validation. A 1.4-inch exit does not establish a sharp
   5.6 kHz validity cutoff for every metric. Driver phase, source boundary, mesh, quadrature,
   mounting, listening distance and measured quantity matter. Uniform-velocity drive is an
   assumption; distinguish normalized directivity from absolute level, loading and distortion.
8. **Lip radius:** quarter-wavelength reasoning is a design heuristic, not a sharp
   diffraction-free cutoff or proof of a best 40–50 mm horn lip. ATH TwinRay enclosure-edge
   treatment must not silently be transferred to a free-standing horn lip.
9. **Evidence independence:** no independent Crowe polar dataset found in the earlier work
   means "not established by this search", not "none exists anywhere". Author measurements
   are useful evidence with conditions, not automatic ground truth or grounds for dismissal.
10. **Reference arithmetic:** 417/203 is about 2.054 and 542/299 about 1.813; neither is the
    golden ratio. No universal golden-ratio construction law was established.

The section image inspected in this pass labels H cut depth 194 mm and V cut depth 273 mm
for the home Crowe seed. Preserve the per-plane depth convention and actual coordinates;
do not assume that one overall D label means identical H/V axial profiles.
Local browser navigation was blocked by tool policy, so this pass read the HTML and referenced
images directly. It did not complete an interactive Chrome review or reproduce the rendering pipeline.

## 5. What software evidence exists, and what it covers

Canonical master: `hornlab_search/design/generators/rolled_family.py`, private
`_rolled_rect_v1.py`, `_crowe_section_v2.py`, and
`data/crowe_section_reference_v1.yaml`. Native kinds `rolled_family_rect_v1` and
`rolled_family_section_v1` bind categorical base/mode, source, schema, driver and reference
hashes in saved recipes. Modes include control, inward radial, signed axial and hybrid.
The example batch is `examples/typologies/rolled_family_2026-11-15/`.
This is not automatically the same construction route as the newer six home cells.

The native implementation was wired to common geometry resolution, meshing, full inner/outer
envelope and geometry identity, cold replay, BO encoding/proposal, and CMA/ME/MAE paths.
Saved tests exercise inactive/fixed controls, explicit seeds, finite bounds, source matching,
source pinning and fresh-process reconstruction. Worker optimizer checks used mock evaluations;
they are not acoustic validation. See `tests/test_rolled_family_geometry.py`,
`tests/test_bo_rolled_family.py`, `tests/test_rolled_family_workers.py` and
`tools/geometry/audit_rolled_family.py`. No tests were rerun in this preservation pass.

| Saved batch inspected here | Seed | Bound corners | Uniform box samples | Local point-cloud rank |
|---|---:|---:|---:|---:|
| Rect control | 1/1 | 8/8 | 64/64 | 3/3 |
| Rect radial / strong radial / axial (each) | 1/1 | 32/32 | 64/64 | 5/5 |
| Corrected section control | 1/1 | 8/8 | 64/64 | 3/3 |
| Corrected section radial / strong radial / axial (each) | 1/1 | 32/32 | 64/64 | 5/5 |

These are historical saved executions at their recorded config/implementation digests, not
new executions against every current dirty file. Rect reports retain the earlier implementation
digest; section reports retain the later inverse-tail correction digest. Do not erase that
difference. All samples passing does not prove the entire continuous box, topology quality,
mesh convergence, meaningful independent acoustic freedoms, or applicability to the wider home box.

The saved real CPU BoTorch smoke fitted a GP and selected a candidate from synthetic data;
it also checked cold replay geometry identity. Its report explicitly says zero GPU/BEM calls
and flags a negative predicted synthetic J as nonphysical. This verifies an engine path,
not the availability/quality of horn training data. `tools/bo_compare/prepare_study.py` currently
defaults `--min-rows` to 100; preserve the owner gate and all identity/quality checks.

## 6. Map the families before editing anything

| Route | Main definition | Main question to resolve |
|---|---|---|
| Archived original rolled rectangle | `tools/geometry/rolled_rect.py` and its CLI | Shared contour lacks independently demonstrated H/V coverage control; preserve the old three studies. |
| Archived Crowe sections | `tools/geometry/crowe_panel.py` and reference readings | Manual axis sections plus inferred joining/body; inspect off-axis junction and actual return. |
| Archived section axial relief | `tools/geometry/section_pucker.py` | Signed z relief is a separate hypothesis, not native ATH radial morph. |
| Native bounded family | `hornlab_search/design/generators/rolled_family.py` and eight `rf__*` examples | Better shared optimizer/identity plumbing; still a narrow visual/geometry pilot, not broad acoustic readiness. |
| Current six home seeds | `examples/typologies/home_landscape_2026-11-15/`, packet and study | Audit each actual generator/bridge route independently, including uncommitted R-OSSE/Crowe-X/biradial work. Do not assume native-family tests cover them. |

## 7. Next-agent acceptance gates, in dependency order

1. **Freeze an honest inventory.** Record live owner instructions, branch/dirty state, each
   seed/config/brief, generator version, fixed/searched keys, dataset lineage and rendering path.
   Reconcile the pending GUI exposure audit; visible in a catalog is not master/replay parity.
2. **Re-research and compare actual geometry.** Source table with model, edition, figure/page,
   units, angle conventions, mounting and confidence. Compare front/oblique/underside views,
   H/V plus intermediate/diagonal cuts, derivatives/curvature, area progression, lip return and
   source connection. Separate reference constraints from inferred construction choices.
3. **Settle the objective before optimizing.** Trace coverage, DI and diagonal terms through
   brief -> response extraction -> normalization -> score. Verify balloon vs cuts-estimate DI,
   slope units/band, crossover handover, reflections/mounting and loading assumptions. Use
   offline stored-response ablations where valid, keeping score identities separate. Present
   justified alternatives and limitations; the latest owner hold remains until settled.
4. **Audit design capability, not just moving vertices.** Build a per-family parameter-to-
   geometry map for throat/tangent, H/V flare/coverage, size, loading, termination, body and
   pucker. Identify missing freedoms, coupled/duplicate controls, dead modes and confounding.
   Derive feasibility constraints in each family's own coordinates. Do not fix an inadequate
   law by merely widening a box, or freeze all useful acoustic controls to make meshes pass.
5. **Specify the optimization domain.** For each key give meaning, units, initial value,
   transform, range, physical initial step, fixed/activity rule and coupling. Prefer a
   continuously feasible mapping where justified; do not silently clip distinct candidates
   onto one geometry. Preserve full-body envelope, driver tangent, clearance, topology and
   deterministic replay. Record invalid attempts and failure regions honestly.
6. **Check the complete shared path.** Same physical geometry for render, preflight, mesher,
   CMA-ES, CMA-ME/MAE, BO encoder, candidate proposal and cold replay. Full inner/outer identity,
   source/recipe pinning, history/cohort separation, sampling stability and duplicate handling.
   Test boundaries/interactions and rejection before expensive evaluation; do not weaken guards.
7. **Acoustic validation only after the hold is resolved.** Separate geometry sampling,
   spatial-mesh, frequency, and angular/balloon convergence; assess representative extremes
   as well as winners. Compare H/V/diagonal response, loading and source assumptions. A
   render cannot establish acoustical correctness, and a low J cannot certify a defective body.
8. **Only then propose a bounded queue.** Preserve existing designs and queued history.
   BO requires the current >=100 valid matched acoustic rows and production identity gates;
   changing law/brief may invalidate eligibility. Report each family as ready/conditional/
   blocked, with direct evidence and unresolved decisions. Get the hold explicitly lifted
   before scheduling new solves. Publishing renders is a separate deliverable, not a physics gate.

The deliverable for the next thread should be a source-grounded readiness matrix, an exact
per-family domain proposal, and small independently reviewable implementation slices only
where the audit demonstrates a need. Use a senior parent for the physical/objective decisions;
Terra agents can research sources or audit disjoint code/test paths in parallel. Do not let
software completion language substitute for these acceptance gates.
