"""Authored prose for the GENERATOR knobs (domain ``generators``).

The rule for every entry here: ANNOTATE, NEVER RESTATE. Prose is compressed from the
existing docstrings in ``design/generators/registry.py`` and ``profiles.py`` plus the
research docs named in each ``doc_ref``. Defaults and hard limits are READ at import from
``registry.DEFAULT_KNOBS`` and ``families.FAMILY_KEYS``; if a number appears in this file
as a stored value, that is a bug. (Numbers inside a formula string are the published
formula, not a config value.)

UNIT RULE
    The unit comes from the key suffix: ``_mm`` -> mm, ``_deg`` -> deg, ``_hz`` -> Hz.
    A name without a recognised suffix is dimensionless (``T``, ``k``, ``s``, ``n``, ``q``,
    ``w``, ``u``, ``zs_frac``, ``mouth_exponent``, ``exponent``).
    Explicit exceptions, all stated on the entry:
      * ``T`` is the Salmon hyperbolic-exponential factor (dimensionless);
      * ``n_anchors`` is an integer count, not a length;
      * ``mouth`` and ``perturb.mode`` are categorical;
      * ``L_mm`` is a SHARED depth for both meridians, not a per-plane radius.

CONTEXTS
    ``contexts`` keys are context ids. This lane authors the ``generator`` meaning (and
    the generator sub-meanings where one name is genuinely overloaded inside the generator
    domain). Native-family meanings are another lane's job: contexts that this lane does
    not own carry ``flags={"deferred"}`` and say so instead of inventing physics.
"""
from __future__ import annotations

from ..families import FAMILY_KEYS, KeySpec
from ..generators import registry
from .schema import KnobContext, KnobDoc

_OVL = frozenset({"overloaded"})
_DEF = frozenset({"deferred"})
_NOT_KNOB = frozenset({"not_a_knob"})


#: Longest prefixes first: splice parents, then blend parents, then the meridian prefix.
_PREFIXES = (
    "hb_first_", "vb_first_", "h_first_", "v_first_",
    "hb_second_", "vb_second_", "h_second_", "v_second_",
    "hb_", "vb_", "h_", "v_",
)


def split_knob(name: str) -> tuple[str, str]:
    """(base knob name, matched prefix without trailing underscore or '').

    The prefixes are the ones the registry docstring documents: ``h_`` / ``v_`` per
    meridian, ``hb_`` / ``vb_`` for blend parents, and ``{p}_first_`` / ``{p}_second_``
    for a splice's nested parents. A numbered perturbation knob (``h_u3``) resolves to
    the shared ``u`` documentation.
    """
    for prefix in _PREFIXES:
        if name.startswith(prefix):
            base = name[len(prefix):]
            if base[:1] == "u" and base[1:].isdigit():
                base = "u"
            return base, prefix[:-1]
    if name[:1] == "u" and name[1:].isdigit():
        return "u", ""
    return name, ""


def family_key_spec(name: str) -> dict | None:
    """The mesher ``KeySpec`` for ``name`` if it is a family key, else ``None``.

    The same name can appear in several families; the strictest numeric clamp wins. The
    returned dict is a plain copy so callers never touch the frozen authority.
    """
    found: list[tuple[str, KeySpec]] = []
    for fam in sorted(FAMILY_KEYS):
        spec = FAMILY_KEYS[fam].get(name)
        if spec is not None:
            found.append((fam, spec))
    if not found:
        return None
    los = [s.lo for _, s in found if s.lo is not None]
    his = [s.hi for _, s in found if s.hi is not None]
    fam, spec = found[0]
    return {
        "family": fam,
        "lo": max(los) if los else None,
        "hi": min(his) if his else None,
        "kind": spec.kind.__name__,
        "choices": list(spec.choices) if spec.choices is not None else None,
        "section": spec.section,
    }


def _make(knob: str, *, label: str, unit: str | None, summary: str, detail: str,
          formula: str | None, physical: str, code_ref: str, doc_ref: tuple[str, str],
          contexts: dict | None = None, flags: frozenset[str] = frozenset()) -> KnobDoc:
    spec = family_key_spec(knob)
    return KnobDoc(
        knob=knob,
        label=label,
        unit=unit,
        summary=summary,
        detail=detail,
        formula=formula,
        physical=physical,
        contexts=contexts or {},
        flags=flags,
        code_ref=code_ref,
        doc_ref=doc_ref,
        default=registry.DEFAULT_KNOBS.get(knob),
        hard_lo=None if spec is None else spec["lo"],
        hard_hi=None if spec is None else spec["hi"],
    )


def _ctx(label: str, summary: str, detail: str, *, formula: str | None = None,
         physical: str = "", flags: frozenset[str] = frozenset()) -> KnobContext:
    return KnobContext(label=label, summary=summary, detail=detail, formula=formula,
                       physical=physical, flags=flags)


_SENIOR = "docs/research/senior_pass_2026-10-24/04_IMPLEMENTATION_PLAN.md"
_WP9 = "docs/research/typologies/WP9_WP9B_GROUNDING_2026-10-25.md"
_MESHER = "docs/research/typologies/MESHER_TYPOLOGIES.md"
_BASIS = "docs/plan/12_RESEARCH_BASIS.md"
_BIRADIAL = "docs/research/typologies/BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md"
_QTW = "docs/research/typologies/SHAPE_DISCOVERY_SWEEP_2026-10-25.md"
_JMLC = "docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md"

_R = "hornlab_search.design.generators.registry."
_P = "hornlab_search.design.generators.profiles."
_PM = "hornlab_mesher.profile_morph."

GENERATOR_KNOBS: dict[str, KnobDoc] = {
    # ---------------------------------------------------------------- shared depth / size
    "L_mm": _make(
        "L_mm",
        label="Depth",
        unit="mm",
        summary="Axial depth shared by both meridians, throat to mouth.",
        detail=("The generator builds both meridians to one z span, so L_mm is shared "
                "rather than a per-plane length. It is the fixed-length dimension for "
                "conical, exponential, hypex and OSSE; length-derived types may only be "
                "shortened to it. The brief envelope still bounds the final depth."),
        formula="z = s L, with s the normalised axial fraction",
        physical="Moves the mouth plane in or out along the horn axis.",
        code_ref=_R + "materialize",
        doc_ref=(_MESHER, "## 4. FREEFORM"),
    ),
    "rm_mm": _make(
        "rm_mm",
        label="Mouth radius",
        unit="mm",
        summary="Per-plane target mouth radius for conical, exponential and hypex walls.",
        detail=("For the fixed-size classical walls this is the radius the meridian must "
                "reach at its end; the flare is solved from the throat radius to it. It "
                "is per meridian: the H and V planes carry their own value. The QTW arc "
                "rule derives its mouth radius instead of taking this knob."),
        formula="conical: r(z) = r0 + z tan(alpha); exponential: r = r0 exp(m z)",
        physical="Sets the mouth area and therefore the low-frequency loading for these walls.",
        code_ref=_R + "build_meridian",
        doc_ref=(_BASIS, "### 16.1 The typology map, dated and sourced"),
        contexts={
            "generator:qtw": _ctx(
                "Derived mouth radius",
                "Not an independent knob in the QTW arc rule: the mouth radius follows from the arc.",
                "The quadratic-throat construction ends the arc and continues a straight bell, "
                "so the mouth radius is a result of the arc radius, the angles and the depth.",
                flags=frozenset({"derived"}),
            ),
        },
    ),
    # ---------------------------------------------------------------- classical shape
    "T": _make(
        "T",
        label="Salmon T factor",
        unit=None,
        summary="Hyperbolic-exponential family factor: catenoidal at one end, exponential at the other.",
        detail=("The Salmon family interpolates between a catenoidal wall and the exponential "
                "horn; T selects the member. Hypex and the Le Cleac'h / spherical-salmon "
                "wavefront-area laws all read it. Its physical endpoint behavior is stated "
                "in the source docstrings, not re-derived here."),
        formula="r = r0 (cosh(m z) + T sinh(m z)) for the plane-wave hypex member",
        physical="Moves the wall between catenoidal loading and exponential expansion.",
        code_ref=_P + "hypex",
        doc_ref=(_BASIS, "### 13.3 Salmon lineage corrections + the X reading"),
        contexts={
            "generator": _ctx(
                "Hypex T factor",
                "Selects the hyperbolic-exponential member between catenoidal and exponential.",
                "Hypex reads T directly in its cosh/sinh wall law. The mesher-side T is a "
                "shape factor only; the generator solves the flare constant so the wall "
                "reaches the requested mouth radius.",
                formula="r = r0 (cosh(m z) + T sinh(m z))",
                physical="Changes how quickly the wall leaves the throat for a fixed mouth.",
            ),
            "generator:lecleach": _ctx(
                "Le Cleac'h area-law T",
                "T in the wavefront-area law of the verified Fourcade construction.",
                "The Le Cleac'h and spherical-salmon marches apply T inside the area law "
                "that advances the wavefront, not to a plane-wave radius formula. The same "
                "name therefore changes a different equation in this sub-context.",
                formula="S(l) = S0 (cosh(m l / 2) + T sinh(m l / 2))^2",
                physical="Changes the wavefront-area growth along the march.",
                flags=_OVL,
            ),
        },
        flags=_OVL,
    ),
    "fc_hz": _make(
        "fc_hz",
        label="Cutoff frequency",
        unit="Hz",
        summary="Plane-wave cutoff that fixes the flare constant or the tractrix mouth size.",
        detail=("Tractrix and the Le Cleac'h family size their mouth from this cutoff; the "
                "exponential family derives its flare constant from it. It is a frequency, "
                "not a wall angle, and it does not change the brief's analysis band."),
        formula="m = 4 pi fc / c (Le Cleac'h); a = c / (2 pi fc) (tractrix mouth radius)",
        physical="Raises or lowers the corner around which the horn stops loading.",
        code_ref=_R + "build_meridian",
        doc_ref=(_MESHER, "### 1a. Mathematical formula"),
    ),
    "a_deg": _make(
        "a_deg",
        label="Coverage half-angle",
        unit="deg",
        summary="OSSE far-field wall half-angle; overloaded by biradial and QTW.",
        detail=("In the OSSE meridian this is the far-field coverage half-angle that the wall "
                "approaches, while the throat angle still comes from the brief's driver. "
                "Biradial and quadratic-throat walls reuse the same key for a different "
                "angle, so a tooltip must resolve the context before it speaks."),
        formula="OSSE: a is the far-field wall half-angle",
        physical="Changes how wide the OSSE wall opens for a fixed depth.",
        code_ref=_R + "build_meridian",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
        contexts={
            "generator": _ctx(
                "OSSE coverage half-angle",
                "Far-field wall half-angle of the OSSE meridian; the throat angle is the driver exit.",
                "The OSSE wall starts at the brief's driver exit angle and approaches this "
                "coverage half-angle. It is a half-angle in the mesher's convention.",
                physical="Widens or narrows the OSSE mouth for a fixed depth.",
            ),
            "generator:biradial": _ctx(
                "Bi-radial initial wall half-angle",
                "Plain initial-wall half-angle of the Keele/JBL power-series contour.",
                "The bi-radial contour starts at this wall angle and bends toward the mouth "
                "radius through a power-series term. This type sets its own default because "
                "the OSSE default would turn a one-inch-scale contour inward at these depths.",
                formula="r(z) = r0 + tan(a) z + c z^n",
                physical="Sets the straight-cone slope the power-series term bends away from.",
                flags=_OVL,
            ),
            "generator:qtw": _ctx(
                "QTW half-dispersion angle",
                "Half the dispersion angle in the quadratic-throat arc rule.",
                "The circular arc turns through this angle and the straight bell continues "
                "at it. The published construction starts parallel to the axis; the brief's "
                "driver exit angle does not pin this start.",
                physical="Sets both the arc turn and the final bell wall angle.",
                flags=_OVL,
            ),
        },
        flags=_OVL,
    ),
    "k": _make(
        "k",
        label="OSSE k",
        unit=None,
        summary="OS-SE shape factor; the standard OS profile is the reference value.",
        detail=("The OS-SE wall law carries a shape factor k alongside the coverage and "
                "termination knobs. It is dimensionless and is passed straight to the "
                "mesher's own OSSE formula rather than reimplemented here."),
        formula="OS-SE wall law (hornlab_mesher.profile_formulas.profile_points)",
        physical="Reshapes the OS wall between the throat and the far-field angle.",
        code_ref=_R + "_osse",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
    ),
    "s": _make(
        "s",
        label="Termination amplitude",
        unit=None,
        summary="OSSE superellipse termination amplitude; zero disables the termination.",
        detail=("A nonzero s turns on the OSSE superellipse termination and makes n and q "
                "active. The mesher requires a positive n and q while s is nonzero. A zero "
                "value leaves the plain OS wall."),
        formula="OSSE superellipse termination (pkg/profile_formulas.py)",
        physical="Rolls the mouth toward a superellipse outline instead of a plain OS wall.",
        code_ref=_R + "_osse",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
    ),
    "n": _make(
        "n",
        label="Termination exponent",
        unit=None,
        summary="OSSE superellipse termination exponent; also the bi-radial flare exponent.",
        detail=("In the OSSE meridian n controls the superellipse termination and is only "
                "active while s is nonzero. The bi-radial wall reuses the name for its "
                "power-series flare exponent, so the meaning is context-dependent. The "
                "mesher requires n positive whenever s is nonzero."),
        formula="OSSE termination exponent; bi-radial: r(z) = r0 + tan(a) z + c z^n",
        physical="Sharpens or softens the mouth roll in OSSE; sets the bend profile in bi-radial.",
        code_ref=_R + "_osse",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
        contexts={
            "generator": _ctx(
                "OSSE termination exponent",
                "Superellipse termination exponent of the OSSE meridian, active while s is nonzero.",
                "It controls how sharply the OSSE wall transitions into the terminated "
                "cross-section. The mesher accepts it as a plain finite number and requires "
                "it positive while s is nonzero.",
                physical="Sharpens or softens the mouth roll of an OSSE termination.",
            ),
            "generator:biradial": _ctx(
                "Bi-radial flare exponent",
                "Power-series flare exponent of the Keele/JBL bi-radial wall contour.",
                "The exponent n bends the straight initial cone toward the requested mouth "
                "radius. The patent's claim 14 gives its legal range and the paper prefers "
                "larger values at larger coverage.",
                formula="r(z) = r0 + tan(a) z + c z^n",
                physical="Concentrates curvature near the mouth at larger values.",
                flags=_OVL,
            ),
        },
        flags=_OVL,
    ),
    "q": _make(
        "q",
        label="Termination saturation",
        unit=None,
        summary="OSSE superellipse termination saturation; must stay positive while s is nonzero.",
        detail=("q sets the saturation of the OSSE superellipse termination and is read "
                "alongside n while s is nonzero. In the native R-OSSE family the same name "
                "means a blend exponent; that native meaning belongs to another lane."),
        formula="OSSE superellipse termination (pkg/profile_formulas.py)",
        physical="Changes how quickly the terminated outline saturates toward its corner.",
        code_ref=_R + "_osse",
        doc_ref=(_MESHER, "### 1b. OSSE parameters"),
        contexts={
            "generator": _ctx(
                "OSSE termination saturation",
                "Saturation of the OSSE superellipse termination; positive while s is nonzero.",
                "The mesher requires q positive whenever s is nonzero. It works with n to "
                "place the terminated cross-section between the OS wall and its corner.",
                physical="Changes how quickly the terminated outline reaches its corner.",
            ),
            "rosse": _ctx(
                "R-OSSE blend exponent",
                "Not authored here: the native R-OSSE meaning is owned by the native-domain lane.",
                "Deferred to the native-family lane. This layer documents only the generator "
                "meaning of q and deliberately does not restate the R-OSSE law.",
                flags=_DEF,
            ),
        },
        flags=_OVL | _DEF,
    ),
    # ---------------------------------------------------------------- blend / splice / throat
    "w": _make(
        "w",
        label="Blend weight",
        unit=None,
        summary="Convex weight between the primary meridian and its second (blend) parent.",
        detail=("The blend parent is built from the same throat and depth, then mixed with "
                "the primary wall at normalised axial position. A weight of zero returns the "
                "primary wall and a weight of one returns the second parent."),
        formula="r(t) = (1 - w) r_a(t) + w r_b(t)",
        physical="Slides the composite wall between the two parent shapes.",
        code_ref=_P + "blend",
        doc_ref=(_BASIS, "### 16.1 The typology map, dated and sourced"),
    ),
    "zs_frac": _make(
        "zs_frac",
        label="Splice position",
        unit=None,
        summary="Splice location as a fraction of the first parent's meridian length.",
        detail=("A splice joins two parents built from the same throat. zs_frac places the "
                "joint along the first parent; the second parent is translated so its radius "
                "matches at that point, and a short bridge is used when the wall angles "
                "disagree."),
        formula="z_s = zs_frac * first.length_mm",
        physical="Moves the joint between the throat-side and mouth-side parent walls.",
        code_ref=_P + "splice",
        doc_ref=(_WP9, "### 2.1 `splice` (G2)"),
    ),
    "throat_blend_mm": _make(
        "throat_blend_mm",
        label="Throat blend length",
        unit="mm",
        summary="Length over which an OS throat is blended into a classical wall; zero skips it.",
        detail=("A nonzero length replaces the start of the classical meridian with an OS "
                "throat that starts at the driver exit angle. A smoothstep blend lands "
                "exactly on the classical radius and angle at the end of the blend. The "
                "default zero path leaves the parent bit-for-bit unchanged."),
        formula="r(z) = (1 - w) r_OS(z) + w r_classical(z), w = 3t^2 - 2t^3, t = z / L_b",
        physical="Trades a short OS throat transition against the parent's own throat shape.",
        code_ref=_P + "throat_blend",
        doc_ref=(_WP9, "### 2.2 `throat_blend_mm` (G3)"),
    ),
    "max_wall_deg": _make(
        "max_wall_deg",
        label="Maximum wall angle",
        unit="deg",
        summary="Wall-angle cap for anchors; on spherical_salmon it is the stop knob, not stop_deg.",
        detail=("The generator block caps every anchor's wall angle at this value. For the "
                "spherical-salmon march the SAME name is the knob that stops the march, so a "
                "tooltip must not describe it as stop_deg. The registry records this naming "
                "mismatch from the R9 audit."),
        formula=None,
        physical="Caps how vertical the wall may become before the anchors are cut.",
        code_ref=_R + "materialize",
        doc_ref=(_WP9, "### 2.3 `spherical_salmon` (G4)"),
        contexts={
            "generator": _ctx(
                "Generator wall-angle cap",
                "Upper bound applied to every selected anchor's wall angle.",
                "The materializer clamps anchor angles into this cap after selecting and "
                "perturbing them. The same block key also supplies the default stop for a "
                "spherical-salmon march.",
                physical="Caps how vertical the wall may become.",
            ),
            "generator:spherical_salmon": _ctx(
                "Spherical-salmon stop angle",
                "Stop angle of the spherical-salmon march; this type uses max_wall_deg, not stop_deg.",
                "The R9 audit recorded that spherical_salmon reads {p}_max_wall_deg and not "
                "{p}_stop_deg. Renaming it here would invent a knob; the layer records the "
                "existing name and its meaning.",
                physical="Stops the march earlier or later along the wall turn.",
                flags=_OVL,
            ),
        },
        flags=_OVL,
    ),
    "stop_deg": _make(
        "stop_deg",
        label="Stop angle",
        unit="deg",
        summary="Wall half-angle where the Le Cleac'h / spherical-wave march stops.",
        detail=("The march ends at the first sample whose wall angle reaches this value. "
                "Only a FREEFORM-representable stop below vertical is legal for the direct "
                "meridian; rollback stops belong to the grid rows route. Spherical salmon "
                "uses max_wall_deg instead."),
        formula="march stops when phi >= stop_deg",
        physical="Chooses how far around the rollback the wall is followed.",
        code_ref=_R + "build_meridian",
        doc_ref=(_JMLC, "## 2. Construction comparison"),
        contexts={
            "generator": _ctx(
                "FREEFORM stop angle",
                "Wall-angle stop for a Le Cleac'h or spherical-wave FREEFORM meridian.",
                "The FREEFORM wrapper refuses a stop at or beyond vertical because z must "
                "stay monotone. The registry truncates the resulting march to the shared "
                "depth afterwards.",
                physical="Chooses how far around the rollback the wall is followed.",
            ),
            "rows": _ctx(
                "Rows-route stop angle",
                "Not authored in this domain: the rows lane owns the rollback stop meaning.",
                "Deferred to the rows-domain lane. The direct FREEFORM stop and the rows "
                "rollback stop share the name but not the legal range.",
                flags=_DEF,
            ),
        },
        flags=_OVL | _DEF,
    ),
    "R_arc_mm": _make(
        "R_arc_mm",
        label="Throat arc radius",
        unit="mm",
        summary="Radius of the circular throat arc in the QTW arc rule; the mouth radius is derived.",
        detail=("The quadratic-throat construction starts with a circular arc parallel to "
                "the axis and tangent to a straight bell. This radius sets how much of the "
                "depth the arc consumes; the mouth radius is then a result, not a knob."),
        formula="z* = R sin(a); r* = r0 + R (1 - cos(a))",
        physical="Moves the arc-to-bell transition along the horn.",
        code_ref=_P + "qtw_waveguide",
        doc_ref=(_QTW, "### 3.4 S4 - Quadratic-Throat Waveguide (Hughes / Peavey)"),
    ),
    # ---------------------------------------------------------------- anchors / mouth / shell
    "n_anchors": _make(
        "n_anchors",
        label="Anchor count",
        unit=None,
        summary="Number of [z, r, wall-angle] anchors selected per meridian.",
        detail=("The generator reduces the dense march to this many anchors before the "
                "mesher sees it. Both endpoints are always kept and interior anchors are "
                "placed by equal arc length in the normalised z/angle plane, so curved "
                "regions get more anchors."),
        formula=None,
        physical="Raises mesh fidelity at the cost of more control points.",
        code_ref=_P + "select_anchors",
        doc_ref=(_MESHER, "### 4b. Profile representation"),
    ),
    "mouth": _make(
        "mouth",
        label="Mouth cross-section",
        unit=None,
        summary="Mouth cross-section family: ellipse, superellipse or rounded rectangle.",
        detail=("The generator emits two cross-section stations: a circular throat and the "
                "selected mouth shape. Superellipse and rounded-rectangle mouths read the "
                "mouth exponent and corner-radius knobs respectively."),
        formula=None,
        physical="Changes the mouth outline without changing the meridians.",
        code_ref=_R + "materialize",
        doc_ref=(_MESHER, "### 4d. Cross-section stations (crossSections)"),
    ),
    "mouth_exponent": _make(
        "mouth_exponent",
        label="Mouth superellipse exponent",
        unit=None,
        summary="Superellipse exponent of a superellipse mouth cross-section.",
        detail=("Used only when the mouth is a superellipse. The generator clamps the value "
                "into the mesher's legal superellipse range before it emits the station. "
                "It is not the cross-section exponent of the native FREEFORM family."),
        formula=None,
        physical="Squares off or rounds the mouth outline.",
        code_ref=_R + "materialize",
        doc_ref=(_MESHER, "### 4d. Cross-section stations (crossSections)"),
    ),
    "mouth_corner_mm": _make(
        "mouth_corner_mm",
        label="Mouth corner radius",
        unit="mm",
        summary="Corner radius of a rounded-rectangle mouth cross-section.",
        detail=("Used only when the mouth is a rounded rectangle. The generator keeps the "
                "radius positive before emitting the station. The meridians are unaffected; "
                "only the mouth outline changes."),
        formula=None,
        physical="Rounds the corners of a rectangular mouth.",
        code_ref=_R + "materialize",
        doc_ref=(_MESHER, "### 4d. Cross-section stations (crossSections)"),
    ),
    "morph_target": _make(
        "morph_target",
        label="Morph target shape",
        unit=None,
        summary="Native mouth morph target: off, rectangle, circle or superellipse.",
        detail=("An opt-in native Ath-style morph. Zero leaves the generated design "
                "byte-identical and emits no morph keys. Values 1-3 blend the raw outline "
                "toward the target through the mesher's own law; a generator mouth must "
                "stay elliptical so the two outline mechanisms cannot fight."),
        formula="r(t, phi) = r_base(t, phi) + factor * (r_target(phi) - r_mouth_base(phi))",
        physical="Blends the generated cross-section into a target mouth outline.",
        code_ref=_R + "materialize",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "morph_width_mm": _make(
        "morph_width_mm",
        label="Morph target width",
        unit="mm",
        summary="Full target width of a morphed mouth; zero keeps the raw mouth extent.",
        detail=("This is a full width, not a half-width. A zero value asks the mesher to "
                "use the raw mouth extent (Ath's implicit circumscribed target). It is "
                "independent of the raw meridian radii and is a search dimension when "
                "the config gives it a bound."),
        formula=None,
        physical="Sets the wide dimension of the target outline.",
        code_ref=_PM + "_resolve_morph_half_dimensions",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "morph_height_mm": _make(
        "morph_height_mm",
        label="Morph target height",
        unit="mm",
        summary="Full target height of a morphed mouth; zero keeps the raw mouth extent.",
        detail=("This is a full height, not a half-height. A zero value asks the mesher to "
                "use the raw mouth extent. It is independent of the raw meridian radii and "
                "is a search dimension when the config gives it a bound."),
        formula=None,
        physical="Sets the tall dimension of the target outline.",
        code_ref=_PM + "_resolve_morph_half_dimensions",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "morph_corner_mm": _make(
        "morph_corner_mm",
        label="Morph corner radius",
        unit="mm",
        summary="Corner radius of a rounded-rectangle morph target.",
        detail=("Used only by morph target 1. The mesher clamps the radius against the "
                "target half-dimensions at run time, so an over-large value cannot fold "
                "the outline. It is independent of the generator's cross-section corner."),
        formula=None,
        physical="Rounds the corners of the morphed mouth.",
        code_ref=_PM + "_resolve_morph_half_dimensions",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "morph_exponent": _make(
        "morph_exponent",
        label="Morph superellipse exponent",
        unit=None,
        summary="Superellipse exponent of morph target 3.",
        detail=("The mesher reads this only for morph target 3. It is clamped into the "
                "superellipse range before the target outline is built. Ath's guide only "
                "documents targets 0-2; target 3 is a mesher extension."),
        formula=None,
        physical="Squares off or rounds a superellipse morph target.",
        code_ref=_PM + "_morph_target_radius_at_angle",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "morph_rate": _make(
        "morph_rate",
        label="Morph rate",
        unit=None,
        summary="Power-law rate of the morph blend from the fixed part to the mouth.",
        detail=("The factor is the remapped axial fraction raised to this power, so larger "
                "values delay the outline change until nearer the mouth. Ath documents a "
                "minimum of 1; the mesher also accepts [0, 1) as an abrupt variant."),
        formula="factor = clamp((t - morph_fixed)/(1 - morph_fixed), 0, 1)^morph_rate",
        physical="Moves how quickly the outline changes along the horn.",
        code_ref=_PM + "_morph_factor",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "morph_fixed": _make(
        "morph_fixed",
        label="Morph fixed part",
        unit=None,
        summary="Axial fraction where the morph begins; zero starts at the throat.",
        detail=("The original profile is preserved up to this fraction and the remaining "
                "axial span is remapped before the rate power is applied. It is a fraction "
                "of horn length, not a distance in millimetres."),
        formula="factor = 0 for t <= morph_fixed",
        physical="Delays the start of the outline change along the horn.",
        code_ref=_PM + "_morph_factor",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "morph_allow_shrinkage": _make(
        "morph_allow_shrinkage",
        label="Allow morph shrinkage",
        unit=None,
        summary="0/1 flag that lets a morph target be smaller than the raw mouth extent.",
        detail=("Without the flag the mesher enlarges the target so the horn never narrows. "
                "With it the morph may pull the section inward. It is a discrete flag, not "
                "a continuous search dimension."),
        formula=None,
        physical="Allows or refuses a target outline smaller than the raw mouth.",
        code_ref=_PM + "_resolve_morph_half_dimensions",
        doc_ref=(_MESHER, "### 6a. Cross-section morphing (ALL formula families)"),
    ),
    "wall_thickness_mm": _make(
        "wall_thickness_mm",
        label="Shell thickness",
        unit="mm",
        summary="Freestanding outer-shell thickness the mesher offsets from the wall.",
        detail=("The generated horn is a printed shell, so the mesher builds an outer "
                "surface offset from the wall. The generator validates a practical range "
                "because a highly curved throat or mouth cannot take the mesher's default "
                "shell. It is a mechanical thickness, not an acoustic dimension."),
        formula=None,
        physical="Changes the printed wall thickness, not the acoustic inner surface.",
        code_ref=_R + "materialize",
        doc_ref=(_MESHER, "## 7. Geometric / cross-section model (all formulas)"),
    ),
    # ---------------------------------------------------------------- perturbation
    "u": _make(
        "u",
        label="Perturbation strength",
        unit=None,
        summary="Per-anchor log-increment perturbation applied to the anchor radii.",
        detail=("Each interior anchor increment is scaled by exp(u) before the radii are "
                "rebuilt from the throat. The legacy form moves the mouth size too, while "
                "the shape mode rescales the increments to preserve the parent mouth radius. "
                "A zero knob leaves the parent anchors untouched."),
        formula="new_r[i+1] = new_r[i] + d_i exp(clip(u_i, -u_max, u_max))",
        physical="Redistributes wall expansion between anchors.",
        code_ref=_P + "perturb_increments",
        doc_ref=(_SENIOR, "## WP3. Shape-only perturbations and graded infeasibility"),
    ),
    "perturb.u_max": _make(
        "perturb.u_max",
        label="Perturbation clip",
        unit=None,
        summary="Upper clip on each perturbation exponent before increments are scaled.",
        detail=("The generator clips every u knob into this symmetric limit before scaling "
                "the anchor increments. It is a generator-block value, not a searched knob, "
                "and it bounds how far a single anchor can move."),
        formula=None,
        physical="Bounds the strongest single-anchor redistribution.",
        code_ref=_P + "perturb_increments",
        doc_ref=(_SENIOR, "## WP3. Shape-only perturbations and graded infeasibility"),
    ),
    "perturb.mode": _make(
        "perturb.mode",
        label="Perturbation mode",
        unit=None,
        summary="Legacy moves mouth size with the perturbation; shape preserves the parent radius.",
        detail=("Legacy applies the exponential increments directly, which changes the mouth "
                "as well as the wall shape. Shape rescales the perturbed increments so the "
                "sum, and therefore the mouth radius, is unchanged. An absent mode behaves "
                "as legacy."),
        formula=None,
        physical="Chooses whether the perturbation also changes the mouth size.",
        code_ref=_R + "materialize",
        doc_ref=(_SENIOR, "## WP3. Shape-only perturbations and graded infeasibility"),
    ),
    # ---------------------------------------------------------------- cross-section alias
    "exponent": _make(
        "exponent",
        label="Cross-section exponent",
        unit=None,
        summary="Superellipse exponent of a FREEFORM cross-section station; prose and code disagree.",
        detail=("This is the native FREEFORM superellipse exponent, not the generator mouth "
                "exponent. The research basis states one default while the shipped generator "
                "default for the mouth is different; that mismatch is recorded, not resolved "
                "here. The generator domain only points at it."),
        formula=None,
        physical="Squares off or rounds a cross-section station.",
        code_ref="hornlab_search.design.families.FAMILY_KEYS",
        doc_ref=(_BASIS, "## 4. The geometry we would have written already exists"),
        contexts={
            "generator": _ctx(
                "Generator cross-section exponent",
                "The generator's mouth exponent is the same idea but a different key.",
                "Generator configs use mouth_exponent for a superellipse mouth. This entry "
                "exists so a tooltip can explain the overload without claiming the native "
                "key is a generator knob.",
                flags=_NOT_KNOB | _OVL,
            ),
            "native": _ctx(
                "Native FREEFORM cross-section exponent",
                "Not authored in this domain: the native lane owns the FREEFORM meaning.",
                "Deferred to the native-domain lane. The prose/code default disagreement is "
                "flagged as doc_mismatch on this entry and must not be silently resolved.",
                flags=_DEF | _NOT_KNOB,
            ),
        },
        flags=_OVL | _NOT_KNOB | frozenset({"doc_mismatch"}) | _DEF,
    ),
    # ---------------------------------------------------------------- nested-parent prefixes
    "{p}_first_{name}": _make(
        "{p}_first_{name}",
        label="First splice parent prefix",
        unit=None,
        summary="Prefix for a knob belonging to the FIRST parent of a splice.",
        detail=("A splice profile nests two parent specs under first and second. Their knobs "
                "carry the prefix {p}_first_ so both parents can use, for example, their own "
                "a_deg. The prefix is a namespace, not a standalone knob."),
        formula=None,
        physical="Selects which nested parent a knob controls.",
        code_ref=_R + "build_meridian",
        doc_ref=(_WP9, "### 2.1 `splice` (G2)"),
        flags=_NOT_KNOB,
    ),
    "{p}_second_{name}": _make(
        "{p}_second_{name}",
        label="Second splice parent prefix",
        unit=None,
        summary="Prefix for a knob belonging to the SECOND parent of a splice.",
        detail=("The second parent of a splice carries {p}_second_ on its knobs so it can "
                "differ from the first parent. The catalog strips this prefix to resolve the "
                "shared knob documentation. The prefix is a namespace, not a knob."),
        formula=None,
        physical="Selects which nested parent a knob controls.",
        code_ref=_R + "build_meridian",
        doc_ref=(_WP9, "### 2.1 `splice` (G2)"),
        flags=_NOT_KNOB,
    ),
}

__all__ = ["GENERATOR_KNOBS", "family_key_spec", "split_knob"]
