# MOUTH RIPPLE / SERRATION ("the pleats") - research dossier (2026-10-25)

Owner question: the visible "little pleats/puckers - almost like mountains or ridges" inside the
mouths of modern optimized waveguides (the images on audiohorn.net's X-Shape pages) - how is that
area DEFINED, and how could we OPTIMIZE it? This dossier answers with sources and labels. Append-only;
later corrections go in a dated table at the end. Lane note: the librarian lane (lib-5) errored on
the provider outage; the orchestrator recovered it directly (fetched sources below). Companion
dossiers: SHAPE_DISCOVERY_SWEEP_2026-10-25.md (S7), X_SHAPE_AUDIOHORN_RESEARCH_2026-10-25.md,
SALMON_X_HORN_EXPANSION_2026-10-25.md.

## 1. Source table

| Source | What it gives us | Status |
|---|---|---|
| Batik's ATH CORE page, at-horns.eu/core.html (fetched in full 2026-10-25, incl. the complete CC-BY-4.0 script) | The ATH school's OWN account of where low diffraction comes from: "extremely low diffraction in the direct sound. It is achieved by using the smoothest profiles in every section of the horn - the true virtue of OS-SE" + the full parameter recipe (OSSE per-azimuth laws, s1/s2 throat extension, Morph.*, Mesh.Roundover {Radius = 42, Segments = 6}, CornerSegments, NAC = 10) | primary (author) |
| hornlab_search/docs/research/boundary_lab_0.5/bl_inventory.md:328 (committed) | The COMPLETE list of Ath cfg keys BL's shipped examples carry (no serration/ripple/corrugation key anywhere: Throat.*, Coverage.Angle, OS.k, Slot.Length, GCurve.*, Morph.TargetWidth/TargetHeight/TargetShape/FixedPart/Rate/CornerRadius/AllowShrinkage, Mesh.Roundover/CornerSegments/RearShape/..., NAC) | verified (in-repo, line-anchored) |
| Wikipedia, Horn antenna (fetched 2026-10-25) | The corrugated-horn class definition: "parallel slots or grooves, small compared with a wavelength, covering the inside surface of the horn, transverse to the axis"; invented by Kay 1962; used for widest bandwidth / smallest sidelobes in microwave feeds; the separate RIDGED horn class (fins) | secondary, cross-check |
| AudioHorn X-Shape page + roundover-kit images (fetched 2026-10-25) | The product render/kit source of the visible puckers: roundover sold as a printed kit; Ath's Mesh.Roundover is SEGMENTED (Radius 42 / Segments 6 in the CORE script) | primary (maker page); the pucker interpretation = ours (section 3) |
| Repo tiling study (M4-era evidence, docs/evidence/*) | The acoustic floor context: aperiodic tiling measured 0.12 dB spread vs a 2.63 dB irreducible diffraction floor; faceting 0.23 dB | verified (in-repo) |
| diyAudio Ath4 threads (338806/354772) | The community mouth-treatment discussions | NOT REACHED today (Cloudflare; same-day record in the biradial dossier) - unverified-today |

## 2. What the ATH/Boundary-Lab surface vocabulary ACTUALLY contains (the definable area)

Every surface-shaping key the BL examples + the Ath CORE script carry [verified]:

- `Throat.*` (Profile/Diameter/Angle), `Slot.Length`, `OS.k` - the throat region.
- `Morph.TargetShape/TargetWidth/TargetHeight/FixedPart/Rate/CornerRadius/AllowShrinkage` - the
  gradual round -> ("cut") rounded-rectangular mouth morph. `FixedPart = 0` starts the morph AT
  THE THROAT; `Rate = 3.0` is the morph-rate exponent (CORE verbatim); `CornerRadius = 16.5 mm`.
- `Mesh.Roundover = {Radius = 42 [mm], Segments = 6}` - the mouth-edge roundover, and NOTE: it is
  implemented as a SEGMENTED arc (6 segments) [verified in the script].
- `Mesh.CornerSegments = 4` + "This sets the angular index of the diagonal. It should match the
  final diagonal direction for the best results" (CORE verbatim) - mesh segmentation control.
- `NAC = 10` - present in the CORE script among the mesh-resolution items; its meaning is NOT
  defined in BL's guide [unverified-today: the Ath 4.8.2 User Guide PDF exceeds the fetch limit;
  the key name and its placement among mesh items are the verified record].
- NO key named Serration / Ripple / Pleat / Corrugation exists in the BL example key set
  [verified, bl_inventory.md:328] nor on the CORE page [verified].

## 3. The verdict: what the visible "pleats" are (three candidate readings, honestly weighted)

1. **MESH/SEGMENTATION FACETS, not an acoustic surface treatment [inferred, strongest].** The
   published kit/renders are built from a segmented mesh: the roundover ring is a 6-segment arc,
   the angular grid has CornerSegments set to a diagonal index, prints ship as segmented STL kits.
   Faceted renders of segmented roundovers look exactly like "little mountains/ridges" around a
   mouth. Consistent with Batik's own text: the design virtue is SMOOTHNESS - a deliberate
   corrugated surface would contradict his stated mechanism. The mesh preview in BL "displays...
   rigid surfaces gray" with visible elements [verified, BL User Guide].
2. **A deliberate print/render texture - marketing-adjacent**; no maker page claims the puckers are
   acoustic [verified absence on the fetched pages].
3. **A real physical corrugation, as in the microwave corrugated horn** - the class exists and is
   documented (Kay 1962; parallel grooves small vs the wavelength; surface-reactance edge-diffraction
   suppression), but NO audio maker's fetched page claims it, and Ath's feature set does not include
   it. If the owner sees deliberate deep ridges on a specific horn's photos, that specific horn's
   maker would have to be the source of the claim - currently none.

Acoustic reality of each: faceted rims ARE audible-relevant (the repo's own tiling study measured
faceting at ~0.23 dB on designs; segmented roundovers create periodic rim scatter at a fixed
spacing), which is why our search layer treats rim shape as a scored object rather than a fixed
constant. A rippled/serrated rim can deliberately DIFFUSE the coherent rim diffraction (the same
mechanism the microwave class exploits: break the single coherent aperture edge into multiple
incoherent edges); at our scales the effect is a scoring question, not a fixed recipe.

## 4. Construction math we can implement (ours, the rows route)

The definable surface feature in OUR vocabulary (labeled experiment, x_shape/T5 precedent):

    r(s, phi) *= 1 + amp * w(s) * cos(N * phi),     N EVEN (quarter-safe, C2 basis)

with `w(s)` a smoothstep window confined to the outer part of the profile
(`w(s) = 3t^2 - 2t^3` on `t = (s - s_start)/(1 - s_start)`, w(0)=0 at the throat end of the
window, 1 at the mouth); knobs: lobes N (even, 6..24), amp_mm (0.5..6), s_start (0.7..0.95).
This is the planned `salmon_ripple` rows extension (sweep dossier S7 / lib-3 section 3.4).
Constraints inherited from the repo: cross-row ridges are REPORT-ONLY in the self-approach meta
(rows meet only at the throat), so the guard does not police inter-ridge gaps - the mesher's
mouth_res_mm must resolve them (a ripple of lambda-scale spacing vs the mesh's 5-11 mm mouth
resolution is the honest feasibility check to run on the first ripple smoke).

## 5. Strengths / weaknesses / honest objectives (from sources + repo numbers)

- STRENGTHS: rim-diffraction diffusion (microwave class + general edge-scattering arguments);
  potential smoothing of the aperture-edge impedance step (the microwave corrugation reading).
- WEAKNESSES: mesh-resolution cost (the ridges must be meshed); the self-approach/facet numbers:
  faceting ~0.23 dB available; the diffraction floor is ~2.63 dB - a mouth ripple is worth 0.2-1 dB
  class effects, not miracles [inferred from the repo's own measured ladder].
- HONEST OBJECTIVE (how to score it): the rim-diffraction COHERENCE - in our stored data: the
  depth/shape of the azimuthal ripple structure in the directivity just outside the design band,
  and the diagonal cut (the maker's own measurement-hygiene argument - X dossier section 4).
  The repo's metric set + the planned diagonal-consistency term can carry this; no new solves.

## 6. Knob/scoring scheme for the campaign (proposal, ours)

1. geometry knobs as section 4 (N even, amp_mm, s_start);
2. score with the existing rip/dislope + a small window on the near-band edge; keep cov dominant;
3. the campaign question the run answers: does a rippled rim BUY beamwidth/DI stability over the
   un-rippled parent (a paired compare: salmon_x_signed as parent ± the ripple term).

## 7. Corrections

None (first dossier of the pleats question). The [unverified-today] items: the Ath NAC key's
documented meaning (manual PDF unreachable today); diyAudio community wording (Cloudflare).

## 8. Open items for the owner

1. If the puckers you see come from a SPECIFIC horn photo (e.g. an X-Shape print or another
   maker's), point me at the image/product: I can classify that specific instance (segmented
   roundover vs real corrugation) from the geometry it shows.
2. Whether the pleat-class experiment ships as `salmon_ripple` (the rows route) NOW with the
   signed-X batch (the owner-approved C2 set), or after the X signed-v1 compare.
3. The Ath NAC meaning: confirm when the User Guide PDF is fetchable (next lib lane with a
   working provider), or from the owner's own Ath install if any.