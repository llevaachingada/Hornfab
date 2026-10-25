"""Authored prose for the ROWS domain (GRID surface + per-azimuth rollback rows).

ANNOTATE, NEVER RESTATE. ``grid.py`` remains the authority for every default, bound and
legal value. This module holds prose only: ``default`` / ``hard_lo`` / ``hard_hi`` stay
``None`` here, and :mod:`hornlab_search.design.params.catalog` fills them by reading
``GRID_DEFAULTS`` / ``ROWS_*`` from ``grid.py`` at build time. A horn number typed into this
file would be a bug.

SPELLING
    A rows config searches ``g_``-prefixed names (``g_stop_deg``, ``g_x_amp``). The docs
    here are keyed by the UNPREFIXED name (``stop_deg``, ``x_amp``); the catalog strips the
    ``g_`` prefix. The G8 Fourier pair is ONE pattern entry per surface
    (``a{k}_throat`` / ``a{k}_mouth``), not one entry per k; the catalog normalises
    ``g_a1_mouth`` -> ``a{k}_mouth``.

CONTEXTS
    ``contexts["rows"]`` carries the rows meaning ONLY. Shared names (``T``, ``stop_deg``,
    ``L_mm``, ``h_rm_mm``, ``fc_hz``, ``wall_thickness_mm``) never claim the generator or
    native meaning here. Per-typology specialization lives in ``ROWS_TYPOLOGY_NOTES``.

R9 LABELS
    The dossiers' labels are kept in the prose of the knobs they qualify: the verified
    Fourcade march is "published/verified (R9-J)", the Salmon rows and the JMLC variants are
    "labeled hypothesis" / "labeled reconstruction", the GRID ellipse pair is a utility
    comparison, and the torus lip is "[inferred]".
"""
from __future__ import annotations

from .schema import KnobContext, KnobDoc

_WP9 = "docs/research/typologies/WP9_WP9B_GROUNDING_2026-10-25.md"
_SALMON_X = "docs/research/typologies/SALMON_X_HORN_EXPANSION_2026-10-25.md"
_RIPPLE = "docs/research/typologies/MOUTH_RIPPLE_SERRATION_RESEARCH_2026-10-25.md"
_JMLC_VAR = "docs/research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md"
_JMLC = "docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md"
_BIRADIAL = "docs/research/typologies/BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md"

_G = "hornlab_search.design.generators.grid."


def split_rows_knob(name: str) -> tuple[str, str]:
    """(base name keyed in ``ROWS_KNOBS``, matched prefix or '').

    Rows configs spell search keys with ``g_``. The G8 Fourier pair is documented as one
    pattern entry per surface, so ``g_a1_mouth`` / ``g_a2_mouth`` resolve to
    ``a{k}_mouth`` (and the throat equivalent) instead of needing one entry per mode.
    """
    rest = str(name)
    prefix = ""
    if rest.startswith("g_"):
        prefix = "g"
        rest = rest[2:]
    if rest.startswith("a"):
        num, sep, which = rest[1:].partition("_")
        if sep and which in ("throat", "mouth") and num.isdigit():
            rest = f"a{{k}}_{which}"
    return rest, prefix


def _ctx(label: str, summary: str, detail: str, *, formula: str | None = None,
         physical: str = "", flags: frozenset[str] = frozenset()) -> KnobContext:
    return KnobContext(label=label, summary=summary, detail=detail, formula=formula,
                       physical=physical, flags=flags)


def _doc(knob: str, *, label: str, unit: str | None, summary: str, detail: str,
         formula: str | None, physical: str, code_ref: str, doc_ref: tuple[str, str],
         contexts: dict[str, KnobContext] | None = None,
         flags: frozenset[str] = frozenset()) -> KnobDoc:
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
        default=None,
        hard_lo=None,
        hard_hi=None,
    )


_ROWS_CTX = _ctx(
    "Rows march stop",
    "Wall-angle stop of the per-azimuth rows march; the legal window depends on the kind.",
    "The verified Le Cleac'h rows use the published stop window and allow rollback past "
    "vertical. The Salmon rows stop below or above the cap-area asymptote, and modulated "
    "Salmon rows keep the plan's rollback window. A per-typology note narrows this.",
)


ROWS_KNOBS: dict[str, KnobDoc] = {
    # ---------------------------------------------------------------- shared depth / meridian
    "L_mm": _doc(
        "L_mm",
        label="Depth",
        unit="mm",
        summary="Shared axial depth of both meridians used by the GRID radius field.",
        detail=("The grid interpolates the horizontal and vertical meridians onto one common "
                "z grid, so the depth is shared rather than a per-plane length. It is not "
                "the march length of a rows kind; those derive depth from their stop. The "
                "brief envelope still bounds the final design."),
        formula="z = s L, with s the normalised axial fraction",
        physical="Moves the mouth plane in or out along the horn axis.",
        code_ref=_G + "_meridians",
        doc_ref=(_WP9, "### 2.4 organic/elliptical + X-shape (WP9b)"),
    ),
    "h_rm_mm": _doc(
        "h_rm_mm",
        label="Horizontal mouth radius",
        unit="mm",
        summary="Horizontal meridian's mouth radius fed into the GRID radius field.",
        detail=("The GRID surface uses the two meridian radii, not a single horn radius. "
                "This is the horizontal meridian's target mouth radius; the vertical one "
                "comes from its own profile. It is a meridian knob, not a mouth-outline "
                "knob."),
        formula="r_H(s) interpolated onto the common z grid",
        physical="Sets the horizontal half-width of the mouth.",
        code_ref=_G + "_meridians",
        doc_ref=(_WP9, "### 2.4 organic/elliptical + X-shape (WP9b)"),
    ),
    # ---------------------------------------------------------------- salmon shape
    "fc_h_hz": _doc(
        "fc_h_hz",
        label="Horizontal cutoff frequency",
        unit="Hz",
        summary="Horizontal-plane Salmon cutoff in the per-azimuth cutoff blend.",
        detail=("Each azimuth's Salmon march gets its own cutoff from a "
                "cosine-squared blend of the horizontal and vertical values. This is the "
                "horizontal endpoint. The pair must always be supplied together."),
        formula="1 / fc(phi) = cos^2(phi) / fc_h + sin^2(phi) / fc_v",
        physical="Changes the horizontal-plane rollback size and rate.",
        code_ref=_G + "_rows_shape_knobs",
        doc_ref=(_WP9, "### 2.4 organic/elliptical + X-shape (WP9b)"),
    ),
    "fc_v_hz": _doc(
        "fc_v_hz",
        label="Vertical cutoff frequency",
        unit="Hz",
        summary="Vertical-plane Salmon cutoff in the per-azimuth cutoff blend.",
        detail=("The vertical endpoint of the same cutoff blend. Supplying only one of the "
                "pair is refused, because the per-azimuth law would otherwise be "
                "undefined. It is the H/V split's vertical half."),
        formula="1 / fc(phi) = cos^2(phi) / fc_h + sin^2(phi) / fc_v",
        physical="Changes the vertical-plane rollback size and rate.",
        code_ref=_G + "_rows_shape_knobs",
        doc_ref=(_WP9, "### 2.4 organic/elliptical + X-shape (WP9b)"),
    ),
    "fc_hz": _doc(
        "fc_hz",
        label="Cutoff frequency",
        unit="Hz",
        summary="Axisymmetric march cutoff for the Le Cleac'h rows kinds.",
        detail=("The Le Cleac'h rows march the same verified construction on every azimuth, "
                "so there is no H/V split and this single cutoff sets the area-law scale. "
                "It is a frequency, not a wall angle."),
        formula="m = 4 pi fc / c in the Fourcade area law",
        physical="Raises or lowers the corner around which the rollback horn loads.",
        code_ref=_G + "_rows_lecleach_knobs",
        doc_ref=(_JMLC, "## 2. Construction comparison"),
        contexts={
            "rows": _ctx(
                "Axisymmetric rows cutoff",
                "Single cutoff of an axisymmetric Le Cleac'h rows march.",
                "The verified Fourcade march has no per-azimuth split, so fc_hz is the "
                "only cutoff. The iwata and AR stretch keep this axisymmetric base.",
                formula="m = 4 pi fc / c",
                physical="Sets the rollback size and loading corner.",
            ),
        },
        flags=frozenset({"overloaded"}),
    ),
    "T": _doc(
        "T",
        label="Salmon / Fourcade T",
        unit=None,
        summary="Family factor of the rows march; its meaning depends on the rows kind.",
        detail=("The Salmon rows read T as the hyperbolic-exponential family factor. The "
                "verified Le Cleac'h rows read the same name inside the Fourcade "
                "wavefront-area law. Both are dimensionless, but they are not the same "
                "equation; a per-typology note disambiguates."),
        formula="Salmon: area law with T; Fourcade: S(l) = S0 (cosh + T sinh)^2",
        physical="Changes the family member between catenoidal-like and exponential-like growth.",
        code_ref=_G + "_rows_shape_knobs",
        doc_ref=(_WP9, "### 2.4 organic/elliptical + X-shape (WP9b)"),
        contexts={
            "rows": _ctx(
                "Rows family factor",
                "Salmon family T on the Salmon rows; Fourcade area-law T on the Le Cleac'h rows.",
                "The two row families share the spelling but not the equation. The Salmon "
                "rows use it in the family area law; the verified Le Cleac'h rows use it "
                "in the Fourcade wavefront-area law.",
                formula="Salmon family law; Fourcade eq. 42",
                physical="Selects the family member and its expansion profile.",
                flags=frozenset({"overloaded"}),
            ),
        },
        flags=frozenset({"overloaded"}),
    ),
    "stop_deg": _doc(
        "stop_deg",
        label="Stop angle",
        unit="deg",
        summary="Wall-angle stop of the per-azimuth rows march; the legal window is kind-specific.",
        detail=("The march ends when the wall angle reaches this value. On the verified "
                "Le Cleac'h rows a stop above vertical is legal rollback; on the Salmon "
                "rows the stop must avoid the cap-area asymptote. A per-typology note gives "
                "the exact window."),
        formula="march stops when phi >= stop_deg",
        physical="Chooses how far around the rollback each row is followed.",
        code_ref=_G + "_rows_shape_knobs",
        doc_ref=(_WP9, "### 2.4 organic/elliptical + X-shape (WP9b)"),
        contexts={
            "rows": _ROWS_CTX,
        },
        flags=frozenset({"overloaded"}),
    ),
    "x_amp": _doc(
        "x_amp",
        label="X-shape amplitude",
        unit=None,
        summary="Signed amplitude of the diagonal X-shape term on the Salmon rows.",
        detail=("The X term modulates the per-azimuth mouth radius to open the diagonals. "
                "The owner-approved signed reading uses a negative value for the "
                "cardinal-in/corner-out form; the positive sign keeps the earlier "
                "diagonal-out reading. The magnitude is capped by the grid validator."),
        formula="mouth modulation about the diagonal; sign selects the reading",
        physical="Opens the mouth along the diagonals (positive) or the cardinals (negative).",
        code_ref=_G + "_rows_shape_knobs",
        doc_ref=(_SALMON_X, "### 3.1 X-shape v2 - signed, decoupled, and already half-implemented"),
    ),
    "x_fc": _doc(
        "x_fc",
        label="X-shape depth fraction",
        unit=None,
        summary="How far along the row the X-shape modulation grows.",
        detail=("The X term is not applied at the throat; it grows toward the mouth. This "
                "fraction sets where that growth is strongest. It is dimensionless and is "
                "capped by the grid validator."),
        formula="modulation weight grows with the arc fraction scaled by x_fc",
        physical="Moves the X-shape's influence toward or away from the mouth.",
        code_ref=_G + "_rows_shape_knobs",
        doc_ref=(_SALMON_X, "### 3.1 X-shape v2 - signed, decoupled, and already half-implemented"),
    ),
    "r_lip_mm": _doc(
        "r_lip_mm",
        label="Torus lip radius",
        unit="mm",
        summary="Tangent-continuous circular lip radius on the rollback rows; zero leaves the wall.",
        detail=("The lip continues the terminal wall tangent with a circular arc that curls "
                "back for half a turn. It is an [inferred] geometric analogue, not a "
                "published lip construction. A zero value is byte-identical to the plain "
                "march."),
        formula="circular arc tangent at the joint, wrap = half a turn",
        physical="Adds a rolled-back lip at the mouth.",
        code_ref=_G + "append_tangent_lip",
        doc_ref=(_JMLC_VAR, "### 2.3 Ferguson / toroidal roll"),
    ),
    # ---------------------------------------------------------------- harmonic stop / bend
    "stop_cos2k": _doc(
        "stop_cos2k",
        label="Harmonic stop cosines",
        unit=None,
        summary="Even-cosine stop-law coefficients as a LIST of additive fractions of stop0.",
        detail=("The list contract adds a2 cos(2 phi) and a4 cos(4 phi) terms to the stop "
                "law. Even cosines keep the left-right mirror, so they are legal on a "
                "quarter model. One entry per k, supplied as a list."),
        formula="stop(phi) = stop0 (1 + sum a_2k cos(2k phi))",
        physical="Makes the mouth rollback deeper on the cardinal or diagonal planes.",
        code_ref=_G + "rows_task_harmonics",
        doc_ref=(_WP9, "### 2.4 organic/elliptical + X-shape (WP9b)"),
    ),
    "stop_sin2k1": _doc(
        "stop_sin2k1",
        label="Harmonic stop sines",
        unit=None,
        summary="Odd-sine stop-law coefficients as a LIST of additive fractions of stop0.",
        detail=("The list contract adds b1 sin(phi) and b3 sin(3 phi) terms to the stop law. "
                "Odd sines are left-right symmetric but up/down antisymmetric, so their "
                "presence forces the half model. One entry per k, supplied as a list."),
        formula="stop(phi) = stop0 (1 + sum b_(2k+1) sin((2k+1) phi))",
        physical="Makes the top and bottom rollback differ from the sides.",
        code_ref=_G + "rows_task_harmonics",
        doc_ref=(_WP9, "### 2.4 organic/elliptical + X-shape (WP9b)"),
    ),
    "bend_sin1_mm": _doc(
        "bend_sin1_mm",
        label="Axial bend",
        unit="mm",
        summary="Odd-sine axial bend of the rows; its presence forces the half model.",
        detail=("The bend shifts the mouth axially with a sin(phi) law, so it is "
                "left-right symmetric but up/down antisymmetric. Presence of the knob "
                "forces the half model even when its value is zero. It is a length, not an "
                "angle."),
        formula="delta_x(phi) = bend sin(phi)",
        physical="Tilts the mouth plane up or down.",
        code_ref=_G + "rows_task_harmonics",
        doc_ref=(_JMLC_VAR, "### 2.5 Up/down-asymmetric saddle"),
    ),
    # ---------------------------------------------------------------- mouth ripple
    "ripple_lobes": _doc(
        "ripple_lobes",
        label="Ripple lobe count",
        unit=None,
        summary="Even lobe count of the mouth ripple; even cosines keep the left-right mirror.",
        detail=("The ripple is an even-lobe radius modulation confined to a mouth window. "
                "The count must be an even integer in the validator's range; odd counts "
                "break the mirror and are refused. Zero means no ripple."),
        formula="r *= 1 + amp w(s) cos(N phi), N even",
        physical="Sets how many pleats appear around the mouth.",
        code_ref=_G + "_rows_ripple_knobs",
        doc_ref=(_RIPPLE, "## 4. Construction math we can implement (ours, the rows route)"),
    ),
    "ripple_amp_mm": _doc(
        "ripple_amp_mm",
        label="Ripple amplitude",
        unit="mm",
        summary="Peak radius deviation of the mouth ripple, delivered at the widest station.",
        detail=("The amplitude is a physical radius offset in millimetres at the widest "
                "station, tapered by the opening window. It is not a fraction of the mouth "
                "radius. Zero leaves the rows geometry unchanged."),
        formula="delta_r = amp w(s) cos(N phi)",
        physical="Deepens or shallows the pleats.",
        code_ref=_G + "_rows_ripple_knobs",
        doc_ref=(_RIPPLE, "## 6. Knob/scoring scheme for the campaign (proposal, ours)"),
    ),
    "ripple_start": _doc(
        "ripple_start",
        label="Ripple window start",
        unit=None,
        summary="Arc fraction where the mouth ripple's opening window starts.",
        detail=("The ripple is confined to a smoothstep window that opens at this arc "
                "fraction. It is dimensionless and must be below the mouth end. Empty or "
                "zero means the window can reach the whole profile."),
        formula="w(s) opens at the arc fraction ripple_start",
        physical="Moves the pleats closer to the mouth or further back.",
        code_ref=_G + "_rows_ripple_knobs",
        doc_ref=(_RIPPLE, "## 4. Construction math we can implement (ours, the rows route)"),
    ),
    # ---------------------------------------------------------------- odd-cosine asymmetry
    "eps_m": _doc(
        "eps_m",
        label="Asymmetry amplitude",
        unit=None,
        summary="Odd-cosine single-sided asymmetry amplitude; nonzero forces the full ring.",
        detail=("The term is a cos(phi) radius modulation, so it breaks the left-right "
                "mirror. The code therefore refuses a quarter or half model when it is "
                "nonzero and requires the seam-free full ring. Zero reproduces the "
                "symmetric verified rows."),
        formula="r *= 1 + eps_m w(s) cos(phi)",
        physical="Widens one side of the horn and narrows the other.",
        code_ref=_G + "_rows_lecleach_asym_knobs",
        doc_ref=(_JMLC_VAR, "### 2.5 Up/down-asymmetric saddle"),
    ),
    "eps_start": _doc(
        "eps_start",
        label="Asymmetry window start",
        unit=None,
        summary="Arc fraction where the odd-cosine asymmetry window opens.",
        detail=("The asymmetry is confined to a smoothstep window that starts here, so the "
                "throat stays exact and every row still shares the driver exit. It is "
                "dimensionless and must stay below the mouth end."),
        formula="w(s) = smoothstep from eps_start to the mouth",
        physical="Moves the one-sided widening toward or away from the mouth.",
        code_ref=_G + "_rows_lecleach_asym_knobs",
        doc_ref=(_JMLC_VAR, "### 2.5 Up/down-asymmetric saddle"),
    ),
    # ---------------------------------------------------------------- lecleach_mod scalar law
    "stop0_deg": _doc(
        "stop0_deg",
        label="Nominal stop angle",
        unit="deg",
        summary="Nominal stop of the scalar harmonic stop law before its cosine/sine terms.",
        detail=("This is the axisymmetric stop the harmonic law modulates. The per-azimuth "
                "stop must stay inside the legal rows window after every harmonic term is "
                "applied. The scalar law is a labeled reconstruction."),
        formula="stop(phi) = stop0 + a2 cos 2phi + a4 cos 4phi + b1 sin phi + b3 sin 3phi",
        physical="Sets the mean rollback depth around the ring.",
        code_ref=_G + "_rows_lecleach_mod_knobs",
        doc_ref=(_JMLC_VAR, "## 3. Hybrid recipe and the knob surface for the GRID rows lane"),
    ),
    "stop_a2_deg": _doc(
        "stop_a2_deg",
        label="Stop cosine a2",
        unit="deg",
        summary="Scalar cos(2 phi) stop term of the harmonic law, in degrees.",
        detail=("The term adds or removes wall angle on the cardinal planes relative to the "
                "nominal stop. It is quarter-safe because cos(2 phi) survives both mirror "
                "planes. The scalar law is a labeled reconstruction."),
        formula="stop += a2 cos(2 phi)",
        physical="Makes the side rollback differ from the nominal stop.",
        code_ref=_G + "_rows_lecleach_mod_knobs",
        doc_ref=(_JMLC_VAR, "## 3. Hybrid recipe and the knob surface for the GRID rows lane"),
    ),
    "stop_a4_deg": _doc(
        "stop_a4_deg",
        label="Stop cosine a4",
        unit="deg",
        summary="Scalar cos(4 phi) stop term of the harmonic law, in degrees.",
        detail=("The higher-order even-cosine term shapes the corner regions of the stop "
                "law. It is also quarter-safe. The scalar law is a labeled reconstruction."),
        formula="stop += a4 cos(4 phi)",
        physical="Shapes the corner rollback between the cardinal planes.",
        code_ref=_G + "_rows_lecleach_mod_knobs",
        doc_ref=(_JMLC_VAR, "## 3. Hybrid recipe and the knob surface for the GRID rows lane"),
    ),
    "stop_b1_deg": _doc(
        "stop_b1_deg",
        label="Stop sine b1",
        unit="deg",
        summary="Scalar sin(phi) stop term; its presence selects the half model.",
        detail=("Odd-sine terms are up/down antisymmetric, so a present b-term forces the "
                "half model even when the value is zero. The scalar law is a labeled "
                "reconstruction."),
        formula="stop += b1 sin(phi)",
        physical="Makes the top and bottom rollback differ.",
        code_ref=_G + "_rows_lecleach_mod_knobs",
        doc_ref=(_JMLC_VAR, "## 3. Hybrid recipe and the knob surface for the GRID rows lane"),
    ),
    "stop_b3_deg": _doc(
        "stop_b3_deg",
        label="Stop sine b3",
        unit="deg",
        summary="Scalar sin(3 phi) stop term; its presence selects the half model.",
        detail=("The higher odd-sine term sharpens the up/down difference. Like every "
                "b-term it forces the half model by presence. The scalar law is a labeled "
                "reconstruction."),
        formula="stop += b3 sin(3 phi)",
        physical="Shapes the top/bottom rollback difference.",
        code_ref=_G + "_rows_lecleach_mod_knobs",
        doc_ref=(_JMLC_VAR, "## 3. Hybrid recipe and the knob surface for the GRID rows lane"),
    ),
    "bend_b1_mm": _doc(
        "bend_b1_mm",
        label="Axial bend b1",
        unit="mm",
        summary="Scalar sin(phi) axial bend; its presence selects the half model.",
        detail=("The bend shifts the mouth axially with an up/down antisymmetric law. Its "
                "presence forces the half model. It is a length, not an angle, and the "
                "scalar law is a labeled reconstruction."),
        formula="delta_x(phi) = bend_b1 sin(phi)",
        physical="Tilts the mouth plane up or down.",
        code_ref=_G + "_rows_lecleach_mod_knobs",
        doc_ref=(_JMLC_VAR, "## 3. Hybrid recipe and the knob surface for the GRID rows lane"),
    ),
    # ---------------------------------------------------------------- AR stretch
    "AR_m": _doc(
        "AR_m",
        label="Mouth aspect ratio",
        unit=None,
        summary="Mouth aspect ratio of the area-preserving AR stretch on the verified march.",
        detail=("The stretch evolves the aspect ratio from circular at the throat to this "
                "value at the mouth while preserving area. It is a labeled reconstruction "
                "of the published principle; no published AR construction exists."),
        formula="AR(l) = 1 + (AR_m - 1) (l / L0)^p",
        physical="Makes the mouth wider than tall (or the reverse) without changing area.",
        code_ref=_G + "_rows_lecleach_ar_knobs",
        doc_ref=(_JMLC_VAR, "### 2.2 Iwata / quasi-Iwata / \"FH-N2\""),
    ),
    "p": _doc(
        "p",
        label="AR evolution exponent",
        unit=None,
        summary="Exponent shaping how the aspect-ratio stretch grows along the march.",
        detail=("The aspect-ratio stretch follows a normalised arc length raised to this "
                "power. It controls where the stretch happens, not its final value. The "
                "construction is a labeled reconstruction."),
        formula="AR(l) = 1 + (AR_m - 1) (l / L0)^p",
        physical="Moves the aspect-ratio change toward the throat or the mouth.",
        code_ref=_G + "_rows_lecleach_ar_knobs",
        doc_ref=(_JMLC_VAR, "### 2.2 Iwata / quasi-Iwata / \"FH-N2\""),
    ),
    "ar_m": _doc(
        "ar_m",
        label="Iwata mouth aspect ratio",
        unit=None,
        summary="Mouth aspect ratio of the iwata_ar stretch on the verified march.",
        detail=("The iwata_ar kind applies an area-preserving aspect-ratio evolution to the "
                "verified Le Cleac'h march, with T pinned by its config. It is our "
                "reconstruction of the principle, never the Iwata product."),
        formula="AR evolution with ar_m at the mouth",
        physical="Makes the mouth wider than tall (or the reverse).",
        code_ref=_G + "_rows_iwata_ar_knobs",
        doc_ref=(_JMLC_VAR, "### 2.2 Iwata / quasi-Iwata / \"FH-N2\""),
    ),
    "ar_p": _doc(
        "ar_p",
        label="Iwata AR exponent",
        unit=None,
        summary="Exponent of the iwata_ar aspect-ratio evolution.",
        detail=("Shapes how quickly the aspect-ratio stretch develops along the normalized "
                "arc. The construction is our reconstruction, not a published Iwata "
                "recipe."),
        formula="AR(l) = 1 + (ar_m - 1) (l / L0)^ar_p",
        physical="Moves the aspect-ratio change toward the throat or the mouth.",
        code_ref=_G + "_rows_iwata_ar_knobs",
        doc_ref=(_JMLC_VAR, "### 2.2 Iwata / quasi-Iwata / \"FH-N2\""),
    ),
    # ---------------------------------------------------------------- GRID surface
    "pnorm": _doc(
        "pnorm",
        label="Cross-section exponent",
        unit=None,
        summary="Superellipse exponent of the GRID cross-section field.",
        detail=("The radius field blends the two meridian radii with a superellipse norm. "
                "The shipped pass uses a constant exponent, not a function of s. An "
                "exponent matching a pure ellipse reproduces the plain comparison grid."),
        formula="superellipse blend of r_H and r_V at each s",
        physical="Squares off or rounds the cross-section between the H and V planes.",
        code_ref=_G + "_shape_knobs",
        doc_ref=(_SALMON_X, "### 3.4 Rows-route shape modulation (G8 on rows) - corner fill, lobes, superellipse-ish"),
    ),
    "a{k}_throat": _doc(
        "a{k}_throat",
        label="G8 throat Fourier coefficient",
        unit=None,
        summary="Even-Fourier throat coefficient of G8 cross-section modulation at mode k.",
        detail=("The G8 law adds even cosines in azimuth to the radius field. This is the "
                "throat value of the coefficient for mode k; the mouth value is its own "
                "knob. Higher modes raise the number of active modes, not a separate K "
                "key."),
        formula="a_k(s) = (1 - s) a_k_throat + s a_k_mouth",
        physical="Modulates the throat cross-section away from a plain ellipse.",
        code_ref=_G + "_shape_knobs",
        doc_ref=(_SALMON_X, "### 3.4 Rows-route shape modulation (G8 on rows) - corner fill, lobes, superellipse-ish"),
    ),
    "a{k}_mouth": _doc(
        "a{k}_mouth",
        label="G8 mouth Fourier coefficient",
        unit=None,
        summary="Even-Fourier mouth coefficient of G8 cross-section modulation at mode k.",
        detail=("This is the mouth value of the same even-cosine coefficient. Mode 1 is the "
                "2-phi term and mode 2 the 4-phi term. The coefficient is dimensionless and "
                "is interpolated from throat to mouth."),
        formula="a_k(s) = (1 - s) a_k_throat + s a_k_mouth",
        physical="Adds lobes or corner fill to the mouth cross-section.",
        code_ref=_G + "_shape_knobs",
        doc_ref=(_SALMON_X, "### 3.4 Rows-route shape modulation (G8 on rows) - corner fill, lobes, superellipse-ish"),
    ),
    "term_side_mm": _doc(
        "term_side_mm",
        label="Side rollback depth",
        unit="mm",
        summary="G9 side rollback depth; a positive knob pulls the side mouth edge back.",
        detail=("The G9 term shifts the mouth axially with a cos-squared azimuth weight: "
                "strongest at the sides, zero at the top and bottom. The sign convention is "
                "positive knob equals rollback, and the implementation negates it. It is a "
                "length, not an angle."),
        formula="dz_mouth(phi) = -|term_side_mm| cos^2(phi)",
        physical="Rolls the side edges of the mouth backward.",
        code_ref=_G + "_shape_knobs",
        doc_ref=(_SALMON_X, "### 3.4 Rows-route shape modulation (G8 on rows) - corner fill, lobes, superellipse-ish"),
    ),
    # ---------------------------------------------------------------- rows spec keys
    "n_phi": _doc(
        "n_phi",
        label="Azimuth row count",
        unit=None,
        summary="Number of azimuth rows in the rows/grid model.",
        detail=("The row count sets the angular sampling of the point grid. The quarter "
                "model, half model and full ring each have their own minimum and parity "
                "rules in the generator. It is a count, not a length."),
        formula=None,
        physical="Raises angular fidelity at the cost of more grid rows.",
        code_ref=_G + "_rows_check_spec",
        doc_ref=(_WP9, "### 2.4 organic/elliptical + X-shape (WP9b)"),
    ),
    "n_s": _doc(
        "n_s",
        label="Axial station count",
        unit=None,
        summary="Number of axial stations along each row.",
        detail=("Each row is sampled at equal axial (or equal-arc, for the rows march) "
                "fractions. This count sets the longitudinal resolution. It is a count, "
                "not a length."),
        formula=None,
        physical="Raises longitudinal fidelity at the cost of more points.",
        code_ref=_G + "_rows_check_spec",
        doc_ref=(_WP9, "### 2.4 organic/elliptical + X-shape (WP9b)"),
    ),
    "span": _doc(
        "span",
        label="Row span",
        unit=None,
        summary="How much of the azimuth circle the rows model covers.",
        detail=("The legal spans are the ones the generator handles, and their names are "
                "read from the generator's own span constant rather than retyped here. A "
                "kind can force a span: an odd-cosine asymmetry forces the full ring and a "
                "b-term forces the half model."),
        formula=None,
        physical="Chooses whether the mesh uses mirror planes or a seam-free full ring.",
        code_ref=_G + "_rows_span_requested",
        doc_ref=(_JMLC_VAR, "### 2.5 Up/down-asymmetric saddle"),
    ),
    "wall_thickness_mm": _doc(
        "wall_thickness_mm",
        label="Shell thickness",
        unit="mm",
        summary="Outer-shell thickness of a freestanding rows model.",
        detail=("The point-grid route builds an explicit outer shell offset from each row's "
                "own profile. This is the printed shell thickness, not an acoustic "
                "dimension. The generator also uses it in its self-approach guard."),
        formula=None,
        physical="Changes the printed wall thickness, not the acoustic inner surface.",
        code_ref=_G + "_rows_check_spec",
        doc_ref=(_WP9, "### 2.4 organic/elliptical + X-shape (WP9b)"),
    ),
}


#: Hard-limit provenance for the names whose caps ARE named constants in ``grid.py``.
#: The catalog reads the values from ``grid``; this map only says where each cap lives.
ROWS_HARD_SOURCES: dict[str, dict[str, str]] = {
    "x_amp": {"file": "hornlab_search/design/generators/grid.py", "key": "ROWS_MAX_X_AMP"},
    "x_fc": {"file": "hornlab_search/design/generators/grid.py", "key": "ROWS_MAX_X_FC"},
    "r_lip_mm": {"file": "hornlab_search/design/generators/grid.py",
                 "key": "ROWS_MAX_R_LIP_MM"},
    "bend_b1_mm": {"file": "hornlab_search/design/generators/grid.py",
                   "key": "ROWS_MAX_BEND_MM"},
    "bend_sin1_mm": {"file": "hornlab_search/design/generators/grid.py",
                     "key": "ROWS_MAX_BEND_MM"},
    "eps_m": {"file": "hornlab_search/design/generators/grid.py", "key": "ROWS_MAX_EPS"},
    "ripple_lobes": {"file": "hornlab_search/design/generators/grid.py",
                     "key": "ROWS_RIPPLE_LOBES_RANGE"},
    "ripple_amp_mm": {"file": "hornlab_search/design/generators/grid.py",
                      "key": "ROWS_MAX_RIPPLE_AMP_MM"},
    "span": {"file": "hornlab_search/design/generators/grid.py", "key": "ROWS_SPANS"},
}


def _note(label: str, summary: str, detail: str, *, formula: str | None = None,
          physical: str = "") -> KnobContext:
    return _ctx(label, summary, detail, formula=formula, physical=physical)


#: Per-typology prose where the SAME base knob means something specific. Keyed by the
#: 11 rows typology ids, then by the unprefixed base knob name.
ROWS_TYPOLOGY_NOTES: dict[str, dict[str, KnobContext]] = {
    "grid_ellipse": {
        "L_mm": _note(
            "Utility comparison depth",
            "Shared depth of the zero-modulation GRID comparison grid.",
            "This typology is the plain-ellipse UTILITY comparison for the GRID route: it "
            "reuses the conical meridians and adds no modulation. The depth is therefore "
            "the same shared span the classical conical config uses.",
            physical="Moves the comparison grid's mouth plane along the axis.",
        ),
        "h_rm_mm": _note(
            "Utility comparison mouth radius",
            "Horizontal meridian mouth radius of the zero-modulation comparison grid.",
            "The grid radius field interpolates the conical meridians; this is the "
            "horizontal one. It is a UTILITY comparison, not a new published typology.",
            physical="Sets the comparison grid's horizontal half-width.",
        ),
    },
    "grid_ellipse_mod": {
        "pnorm": _note(
            "Utility comparison exponent",
            "Superellipse exponent of the G8/G9 modulated comparison grid.",
            "The shipped comparison keeps the constant-exponent simplification. This is "
            "the exponent that the plain grid leaves at its default.",
            physical="Rounds or squares the modulated comparison cross-section.",
        ),
        "a{k}_mouth": _note(
            "G8/G9 comparison mouth modulation",
            "Even-Fourier mouth coefficient of the G8/G9 modulated comparison grid.",
            "The shipped comparison pins one low-order pair: a1 is the 2-phi corner fill "
            "and a2 the 4-phi lobe. These are UTILITY comparison values, not a search.",
            physical="Adds the comparison grid's corner fill and mouth lobes.",
        ),
        "term_side_mm": _note(
            "G9 comparison side rollback",
            "Side rollback depth of the G8/G9 modulated comparison grid.",
            "The comparison pins a small positive side rollback. Positive still means "
            "rollback; the implementation negates the stored value.",
            physical="Rolls the comparison grid's side mouth edges back.",
        ),
    },
    "salmon_elliptical": {
        "stop_deg": _note(
            "Salmon rows rollback stop",
            "Stop of the per-azimuth Salmon march; the cap-area law has an asymptote near half a turn.",
            "LABELED HYPOTHESIS-SHAPE EXPERIMENT (WP9b dossier section 2.4): per-azimuth "
            "Salmon marches, not an attributed published construction. The shipped seed "
            "stops below the asymptote and the plan's modulated window stays a rollback.",
            physical="Follows the Salmon wall further or less far around the rollback.",
        ),
        "T": _note(
            "Salmon family factor",
            "Hyperbolic-exponential family T of the per-azimuth Salmon rows.",
            "This is the Salmon family factor used inside the rows area law. The rows are "
            "a LABELED HYPOTHESIS-SHAPE EXPERIMENT, not a published construction.",
            physical="Selects the Salmon family member used on every azimuth.",
        ),
        "fc_h_hz": _note(
            "Salmon H cutoff",
            "Horizontal endpoint of the per-azimuth Salmon cutoff blend.",
            "Each row's cutoff is a cosine-squared blend of this value and the vertical "
            "one, giving the row family its H/V split. The pair must be supplied together.",
            physical="Sets the horizontal rollback size.",
        ),
    },
    "salmon_x_shape": {
        "x_amp": _note(
            "Diagnostic-out X amplitude",
            "Positive X amplitude keeps the shipped diagonal-out reading.",
            "In this hypothesis config the positive sign opens the mouth along the "
            "diagonals. The signed variant records the opposite reading under a negative "
            "value; the sign is a reading switch, not a magnitude change.",
            physical="Opens the mouth along the diagonals.",
        ),
        "x_fc": _note(
            "X growth fraction",
            "How fast the diagonal X term grows toward the mouth in this hypothesis config.",
            "The X term is a rows shape hypothesis, not a published construction. This "
            "fraction moves its influence along the row.",
            physical="Moves the X-shape influence toward or away from the mouth.",
        ),
    },
    "salmon_x_signed": {
        "x_amp": _note(
            "Signed cardinal-in X amplitude",
            "Negative X amplitude opens the mouth along the cardinals (the signed reading).",
            "Signed-X v2 (owner-approved 2026-10-25): a negative value gives the "
            "cardinal-in / corner-out reading, while a positive value keeps the earlier "
            "diagonal-out reading. The magnitude cap is unchanged.",
            physical="Opens the mouth along the cardinals when negative.",
        ),
        "stop_deg": _note(
            "Signed-X rows stop",
            "Salmon rows stop under the signed-X reading; keep it away from the area asymptote.",
            "The signed-X config is still a LABELED HYPOTHESIS. Its seed was reseeded to "
            "stay clear of the cap-area asymptote; the plan's rollback window is unchanged.",
            physical="Controls how far the signed-X rows follow the rollback.",
        ),
    },
    "salmon_saddle": {
        "stop_cos2k": _note(
            "Saddle stop cosines",
            "Even-cosine stop terms that shape the saddle's cardinal/diagonal rollback.",
            "The LIST contract adds the cos-2k terms to the stop law. Even cosines are "
            "quarter-safe. The saddle is a LABELED HYPOTHESIS over the Salmon rows.",
            physical="Deepens the rollback on the cardinal or diagonal planes.",
        ),
        "stop_sin2k1": _note(
            "Saddle stop sines",
            "Odd-sine stop terms that make the saddle's top and bottom differ.",
            "The LIST contract adds the sin-(2k+1) terms. Their presence forces the half "
            "model. The saddle is a LABELED HYPOTHESIS over the Salmon rows.",
            physical="Makes the top and bottom rollback differ.",
        ),
    },
    "lecleach_rollback": {
        "stop_deg": _note(
            "Verified Fourcade rollback stop",
            "Stop of the published Fourcade march; above vertical is legal rollback here.",
            "The base march is the verified Fourcade 2015 construction (R9-J). The rows "
            "route permits a stop above vertical, which the FREEFORM meridian cannot "
            "represent. The grid's own stop window still applies.",
            physical="Follows the verified rollback further around the turn.",
        ),
        "T": _note(
            "Fourcade area-law T",
            "T inside the verified Fourcade wavefront-area law.",
            "This is the published construction's own T, not the Salmon family selector. "
            "The rows are the verified Fourcade march on every azimuth.",
            physical="Changes the wavefront-area growth of the verified rollback.",
        ),
    },
    "lecleach_toroidal": {
        "r_lip_mm": _note(
            "Inferred torus lip",
            "Tangent-continuous circular lip on the verified rollback; [inferred] analogue.",
            "No published torus-lip math exists for this class. The arc is tangent to the "
            "verified wall and curls back for half a turn. It is labeled [inferred], not a "
            "reproduction of a product.",
            physical="Adds a rolled-back lip at the mouth.",
        ),
        "stop_deg": _note(
            "Toroidal rollback stop",
            "Stop of the verified Fourcade march before the inferred lip is appended.",
            "The base march remains the published Fourcade construction (R9-J). Only the "
            "lip continuation is inferred. The grid's stop window applies.",
            physical="Sets how far the wall turns before the lip begins.",
        ),
    },
    "lecleach_iwata_ar": {
        "ar_m": _note(
            "Reconstructed mouth AR",
            "Mouth aspect ratio of our area-preserving stretch; a reconstruction, not the product.",
            "The base march is the verified Fourcade construction. The AR evolution is our "
            "reconstruction of the published principle and is explicitly not the Iwata "
            "product. T is pinned by this config.",
            physical="Makes the mouth wider than tall (or the reverse).",
        ),
        "ar_p": _note(
            "Reconstructed AR exponent",
            "Exponent of our area-preserving aspect-ratio stretch.",
            "This shapes where the reconstructed AR change happens. No published AR "
            "construction exists for this class; the label stays reconstruction.",
            physical="Moves the aspect-ratio change toward the throat or mouth.",
        ),
    },
    "lecleach_asym_odd": {
        "eps_m": _note(
            "Labeled one-sided asymmetry",
            "Odd-cosine asymmetry amplitude; nonzero forces the seam-free full ring.",
            "LABELED RECONSTRUCTION/HYPOTHESIS: the verified Fourcade march plus an "
            "odd-cosine single-sided term. No published asymmetric-per-azimuth JMLC "
            "construction exists. The odd cosine breaks the left-right mirror, so a "
            "nonzero value forces the full model.",
            physical="Widens one side and narrows the other.",
        ),
        "eps_start": _note(
            "Asymmetry window start",
            "Arc fraction where the one-sided asymmetry opens; the throat stays exact.",
            "The smoothstep window keeps the throat at the driver's exit radius and angle. "
            "This is part of the labeled reconstruction, not a published rule.",
            physical="Moves the one-sided widening toward or away from the mouth.",
        ),
    },
    "salmon_ripple12": {
        "ripple_amp_mm": _note(
            "Pleats amplitude",
            "Peak radius deviation of the even-lobe mouth ripple, in millimetres.",
            "LABELED EXPERIMENT (the owner's 'pleats' feature): no published audio "
            "mouth-ripple construction exists. The amplitude is delivered at the widest "
            "station inside the opening window.",
            physical="Deepens or shallows the twelve pleats.",
        ),
        "ripple_lobes": _note(
            "Pleats lobe count",
            "Even lobe count of the mouth ripple; even cosines keep the left-right mirror.",
            "The shipped experiment uses an even count so the quarter/half mirror stays "
            "valid. Odd counts are refused by the generator. This is a labeled experiment.",
            physical="Sets the number of pleats around the mouth.",
        ),
        "ripple_start": _note(
            "Pleats window start",
            "Arc fraction where the ripple's opening window starts.",
            "The shipped experiment keeps the ripple near the mouth. The window is a "
            "smoothstep, so the throat is untouched. This is a labeled experiment.",
            physical="Moves the pleats closer to the mouth or further back.",
        ),
    },
}

__all__ = ["ROWS_KNOBS", "ROWS_HARD_SOURCES", "ROWS_TYPOLOGY_NOTES", "split_rows_knob"]
