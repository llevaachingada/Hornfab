"""GRID family: radius-field point grid for the mesher's point-grid adapter (WP10).

The surface is the radius field of
``docs/research/senior_pass_2026-10-24/02_TYPOLOGIES_AND_MULTICELL.md`` section 4,
sampled on the common axial grid ``z_i = s_i * L`` (``s_i = i / n_s``)::

    r(s, phi) = r_H(s) * r_V(s)
                / ( (|r_V(s) cos phi|^p(s) + |r_H(s) sin phi|^p(s))^(1/p(s)) )   # superellipse
                * (1 + sum_k a_k(s) cos(2k phi))                                    # G8
    z(s, phi) = s * L + dz_mouth(phi) * w_mouth(s)                                  # G9
    P         = (r cos phi, r sin phi, z)                                           # MILLIMETRES

``r_H`` / ``r_V`` are the two meridians, built by
:func:`hornlab_search.design.generators.registry.build_meridian` (imported, never copied) from
``spec["profile_h"]`` / ``spec["profile_v"]`` and interpolated onto the shared z grid.

The superellipse field ships the quarter-symmetric subset only (no twist G12, no up/down
asymmetry G11): ``phi`` runs over ``[0, 90] deg`` with ``n_phi >= 13`` rows including both
endpoint rows, so the first row lies on ``y = 0`` and the last on ``x = 0`` and the mesh can use
``symmetry_planes=("x", "y")``. ``full_circle=True`` is a geometry-only helper (test / later full
models): it mirrors the quarter grid four times and closes the ring without repeating the seam
rows. The WP9b rows machinery adds a HALF model (``phi`` in ``[-90, +90]``, mirror plane yz,
``quadrants "14"``) for the lecleach_mod b-terms / axial bend; see the C2 symmetry block below.
``build_grid_mesh`` in ``mesh/grid_build.py`` accepts the quarter or that half.

Knobs (``prefix`` is ``"g"`` for the future ``generator: {name: grid}`` configs, exactly like
``build_meridian``'s ``h_`` / ``v_``):

* ``{p}_pnorm`` -- superellipse exponent, default 2.0 (pure ellipse). ``p(s)`` is plan-named as a
  function; **this pass ships the constant** ``p`` (labelled limitation, no hidden knob).
* ``{p}_a{k}_throat`` / ``{p}_a{k}_mouth`` -- G8 even Fourier coefficients, default 0.0
  (zero modulation). ``a_k(s) = (1 - s) a_k_throat + s a_k_mouth``. ``K = 2`` modes by default;
  setting knobs for a higher ``k`` raises ``K`` (no separate K key is invented).
* ``{p}_term_side_mm`` -- G9 side rollback depth, default 0.0 (flat mouth).
  ``dz_mouth(phi) = -|term_side_mm| * cos^2(phi)``: a NEGATIVE z shift at the sides (H plane
  ``phi = 0/180``), zero at the top/bottom (``phi = 90``), so the sign convention is "positive
  knob = rollback" and the mouth edge stays mirror-safe. ``w_mouth(s) = 3 s^2 - 2 s^3``
  (smoothstep; the plan names ``w_mouth(s)`` without a form -- **[inferred]** monotone C1 choice,
  0 at the throat and 1 at the mouth).

``grid_outer_points`` builds the explicit outer shell the point-grid freestanding mode REQUIRES
(an in-plane normal offset of each row's own ``(rho, z)`` profile by the wall thickness). The
self-approach guard refuses a row whose parts farther than ``2 t + 2 mm`` apart ALONG the surface
come closer than that in space (the fold the 2026-10-24 curl probe measured)
(``docs/research/typologies/WP9_WP9B_GROUNDING_2026-10-25.md`` section 2.4 P4) via
``registry.GeneratorError`` -- graded infeasible travels through the generator error path.

Units: mm in, mm out (``build_mesh_with_info(..., scale_to_metres=True)`` converts at the mesher).
"""
from __future__ import annotations

import copy
import math

import numpy as np

from . import profiles as profiles_mod
from . import registry

#: Grid knobs whose defaults are NOT registry.DEFAULT_KNOBS (the GRID-only shape freedoms).
GRID_DEFAULTS: dict[str, float] = {
    "pnorm": 2.0,
    "term_side_mm": 0.0,
    "a_throat": 0.0,
    "a_mouth": 0.0,
}

#: Plan 9b.3: a quarter model needs at least 13 phi rows.
MIN_PHI_QUARTER = 13
#: Largest G8 mode index the generator scans for in the knobs.
MAX_FOURIER_K = 16
#: Dossier 2.4 P4: refuse a grid with min non-adjacent gap below 2 t + this margin.
SELF_APPROACH_MARGIN_MM = 2.0

#: The PERSISTED spec fields of a grid Design (``design.params["grid"]``). Knobs are carried
#: alongside them under ``"knobs"`` because ``mesh/build.py`` receives only (design, mesh, cfg):
#: the compact spec alone cannot be re-derived, and designs that differ only in ``L_mm``/``rm_mm``
#: must not share a design hash (dedup/cache/failure-marker keys are design hashes).
GRID_SPEC_KEYS = ("profile_h", "profile_v", "n_phi", "n_s", "max_wall_deg", "wall_thickness_mm")
GRID_BLOCK_KEYS = (*GRID_SPEC_KEYS, "knobs")

# ------------------------------------------------------------------ WP9b rows kind
#
# The rows machinery is an OPTIONAL alternative surface definition inside the same GRID
# generator block: ``rows: {type: ...}`` replaces the superellipse radius field with one
# march per azimuth.  FINAL PER-KIND CONTRACT (reconciled 2026-10-25: ONE knob convention
# per kind; validation, ``design_params`` persistence, mesh re-derivation, the envelope
# estimator and the row meta all follow this table):
#
#   * salmon_elliptical / salmon_axisym -- SCALAR Salmon shape knobs ``fc_h_hz`` (and
#     ``fc_v_hz``; axisym marches at fc_h), ``T``, ``stop_deg``, plus the T5
#     ``x_amp``/``x_fc`` modulation; harmonic stop/bend is the LIST contract
#     ``stop_cos2k`` / ``stop_sin2k1`` / ``bend_sin1_mm`` (dimensionless fractions of
#     ``stop_deg``).  The SHIPPED salmon harmonic config (salmon_saddle.yaml) uses the
#     list contract; the duplicate SCALAR salmon a2/a4/b1/b3 law was deleted.
#   * lecleach -- the verified Fourcade axisymmetric march: ``fc_hz``, ``T``,
#     ``stop_deg``, optional ``fc_h_hz``+``fc_v_hz`` pair, ``r_lip_mm``, and the same
#     LIST harmonic stop/bend contract.
#   * lecleach_mod -- verified march + the SCALAR harmonic law ``stop0_deg`` /
#     ``stop_a2_deg`` / ``stop_a4_deg`` / ``stop_b1_deg`` / ``stop_b3_deg`` /
#     ``bend_b1_mm`` (the scalar lane's kind; no shipped config, tests target it).
#   * lecleach_ar -- verified march + scalar area-preserving AR stretch ``AR_m`` / ``p``.
#   * iwata_ar -- verified march + AR stretch ``ar_m`` / ``ar_p`` (T pinned 0.5 in config).
#   * toroidal_rollback -- verified march + tangent-continuous ``r_lip_mm`` lip + the
#     LIST harmonic stop/bend contract.
#
# Row span (WP9b C2): ``span: quarter`` (default; phi 0..90, quadrants "1", both cardinal
# mirror planes) or ``span: half`` (phi -90..+90 inclusive, mirror plane yz, x >= 0,
# quadrants "14", 2x the quarter dofs), or ``span: half_xz`` (phi 0..180 inclusive, mirror
# plane xz, y >= 0, quadrants "12", 2x the quarter dofs; 2026-10-26 Phase 0 item 2D), or
# ``span: full`` (phi 0..360 EXCLUSIVE of the
# seam row, n_phi >= 25, quadrants "1234", NO mirror planes: a closed full-ring point
# grid - the mesher's PointGridHornGeometry default mode (closed=True, symmetry planes
# unused); 4x the quarter dofs).  The phi origin is pinned at the HORIZONTAL (+x)
# axis in every span.  The LIST contract selects half EXPLICITLY with ``span: half``; the
# scalar ``lecleach_mod`` b-term/bend PRESENCE also forces half (its landed rule); the
# odd-cosine asymmetry (lecleach_asym with eps_m != 0) FORCES a FULL model by default, but
# is legal on ``span: half_xz`` because cos(phi) is EVEN under the up/down mirror
# phi -> -phi (the left-right asymmetry is intact; only a vertical mirror is used).
#
# Owner ruling 2026-10-25: the Salmon rows are LABELED HYPOTHESIS-SHAPE EXPERIMENTS under
# neutral names; nothing there is an attributed published construction (R9).  The
# ``lecleach`` rows ARE the attributed Fourcade 2015 construction (R9-J gate passed).
#
# C2 SYMMETRY BASIS (lib-2 section 2.5, binding): phi is measured FROM THE HORIZONTAL
# mouth-plane axis (+x), point = (r cos phi, r sin phi).  Left-right mirror is x -> -x,
# i.e. phi -> pi - phi.  The functions invariant under that mirror are
# {cos(2k phi), sin((2k+1) phi)}:
#   * cos(2 phi) / cos(4 phi) are also even under phi -> -phi (up/down), so the QUARTER
#     model (phi 0..90, mirror planes xz+yz) stays valid;
#   * sin(phi) / sin(3 phi) are left-right symmetric but up/down ANTISYMMETRIC, and the
#     axial bend delta-x(phi) = bend*sin(phi) likewise, so those rules require the HALF
#     model (phi -90..+90, mirror plane yz, x >= 0, quadrants "14");
#   * a cos(phi) (odd cosine) term is NOT invariant under phi -> pi - phi: it breaks the
#     left-right mirror, but it IS even under phi -> -phi, so it is representable on the
#     UPPER half (phi 0..180, mirror plane xz, y >= 0, quadrants "12", span: half_xz).
# The PHI ORIGIN IS PINNED here and in every rows meta's ``sign_conventions``: phi = 0 is
# the horizontal (+x) axis.  (If phi were measured from vertical the roles swap.)
ROWS_TYPES = ("salmon_elliptical", "salmon_axisym", "lecleach", "iwata_ar",
              "toroidal_rollback", "lecleach_mod", "lecleach_ar", "lecleach_asym",
              "osse_rollback")
#: The persisted spec fields of a rows Design (``design.params["grid"]``).  ``span`` is
#: accepted everywhere but PERSISTED ONLY FOR A NON-QUARTER model (kept out of the keys so
#: the quarter recipe -- and its design hash -- stays byte-identical to before this pass).
ROWS_SPEC_KEYS = ("rows", "n_phi", "n_s", "wall_thickness_mm")
ROWS_BLOCK_KEYS = (*ROWS_SPEC_KEYS, "knobs")
ROWS_ALLOWED_SPEC_KEYS = (*ROWS_SPEC_KEYS, "span")
ROWS_ALLOWED_BLOCK_KEYS = (*ROWS_BLOCK_KEYS, "span")
#: The four legal row spans (phi from the HORIZONTAL axis in all of them).
ROWS_SPANS = ("quarter", "half", "half_xz", "full")
#: Honest minimum row count for a half model when modulation is on (plan 9b.3).
MIN_PHI_HALF = 25
#: Honest minimum row count for a full ring (the mesher's AngularSegments scale; a
#: full ring at n_phi 25 = the half-model resolution rotated to the whole circle).
MIN_PHI_FULL = 25
#: Row knobs whose zero value is geometry-identical to absent (design-hash canonicalisation).
#: The lecleach_mod b-term / bend keys are deliberately NOT here: their PRESENCE is the
#: implicit half-model flag, so an explicit zero must survive into the recipe.
ROWS_DEFAULTS: dict[str, float] = {"x_amp": 0.0, "x_fc": 0.0, "bend_sin1_mm": 0.0,
                                   "eps_m": 0.0, "eps_start": 0.0,
                                   "ripple_lobes": 0.0, "ripple_amp_mm": 0.0,
                                   "ripple_start": 0.0, "fc_fold": 2.0, "fc_union": 0.0}
#: Hard caps from dossier section 2.4 / plan 9b.2 T5 (search bounds are YAML defaults).
#: 2026-10-25 (owner-approved signed-X v2): x_amp is SIGNED - negative amp opens the mouth
#: along the CARDINAL axes (the "corners-in" reading); positive keeps today's diagonal-out
#: reading. The magnitude cap is unchanged.
ROWS_MAX_X_AMP = 0.4
ROWS_MAX_X_FC = 0.3
#: Sanity caps for the lib-2 inferred torus lip and axial bend (search bounds are YAML).
ROWS_MAX_R_LIP_MM = 100.0
ROWS_MAX_BEND_MM = 100.0
#: The odd-cosine single-sided asymmetry amplitude cap (sweep S3) + the window start.
ROWS_MAX_EPS = 0.3
#: The even-lobe mouth ripple (owner's "pleats" feature; MOUTH_RIPPLE_SERRATION dossier):
#: lobes N even in [6, 24], amp in mm, window start as an arc fraction.
ROWS_RIPPLE_LOBES_RANGE = (6.0, 24.0)
ROWS_MAX_RIPPLE_AMP_MM = 50.0   # 2026-10-27 owner: Solana-depth flutes (30-50 mm, IMPLEMENTATION_PLAN s9); was 6
#: Honest ripple resolution bar: >= 4 phi samples per lobe period
#: (samples_per_period = (2 pi / N) / d_phi over the row's own span).
ROWS_RIPPLE_SAMPLES_PER_LOBE = 4.0
ROWS_HYPOTHESIS_LABEL = (
    "LABELED HYPOTHESIS-SHAPE EXPERIMENT (WP9b, dossier section 2.4 / Report 4 9b.2 "
    "T3/T5): per-azimuth spherical_salmon marches; not an attributed published "
    "construction (R9 gate). Published-family names are intentionally not used.")
ROWS_ASYM_LABEL = (
    "LABELED RECONSTRUCTION/HYPOTHESIS (owner-approved 2026-10-25): the verified "
    "Fourcade march (lecleach_exact, R9-J) per azimuth + an odd-cosine single-sided "
    "asymmetry term; NO published asymmetric-per-azimuth JMLC construction exists "
    "(docs/research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md searched: "
    "none). The base march is verified; the eps term is ours.")
ROWS_RIPPLE_LABEL = (
    "LABELED EXPERIMENT (owner-directed 'pleats' feature, "
    "docs/research/typologies/MOUTH_RIPPLE_SERRATION_RESEARCH_2026-10-25.md): an "
    "even-lobe radius ripple r *= 1 + amp*w(s)*cos(N phi) confined to a mouth window; "
    "no published audio mouth-ripple construction exists (the microwave corrugated-horn "
    "class is the theoretical neighbour).")
#: Defaults used when a salmon shape knob is absent (configs set every number explicitly).
#: Salmon harmonic stop/bend defaults live in ``rows_task_harmonics`` (list contract).
#: 2026-10-25: the signed-x pair + the lecleach_asym eps pair + the pleats ripple trio.
ROWS_KNOB_DEFAULTS = {"fc_h_hz": 800.0, "fc_v_hz": 1100.0, "T": 0.8, "stop_deg": 170.0,
                      "x_amp": 0.0, "x_fc": 0.0,
                      "eps_m": 0.0, "eps_start": 0.0,
                      "ripple_lobes": 0.0, "ripple_amp_mm": 0.0, "ripple_start": 0.0,
                      "fc_fold": 2.0, "fc_union": 0.0}
#: Salmon fc law fold (owner 2026-10-28, "copy, rotate 90 deg, join"): 2 = today's two-fold law
#: 1/fc = cos^2 phi / fc_h + sin^2 phi / fc_v; 4 = the same law in 2 phi, so the AXES (H and V) get
#: fc_h and the DIAGONALS get fc_v - four petals on the axes meeting on the diagonals.
ROWS_FC_FOLDS = (2.0, 4.0)
#: fc_union 1 (owner 2026-10-28, literal "copy, rotate 90 deg, join"): the UNION of the shape and its 90 deg
#: copy - each azimuth takes the fc law at psi_eff = max(psi, 90 deg - psi) (psi folded into the first
#: quadrant), so the axes carry the petal row and the diagonal joins carry the original 45 deg row (its
#: X humps); the join is a crease along the diagonal (C0 in phi by construction).
#: A salmon saddle stop law is a labeled reconstruction; keep every modulated row inside the
#: plan's Salmon stop window so the march stays a rollback, not a near-closed spiral.
ROWS_SALMON_MOD_STOP_RANGE = (120.0, 240.0)
#: ``rows: {type: lecleach}`` is the verified Fourcade construction on the GRID route
#: (rollback = stop above 90 deg).  Its knobs are axisymmetric and carry no H/V split,
#: no X-shape term and no ``L_mm`` (the march derives the depth).
ROWS_LECLEACH_KNOB_DEFAULTS = {"fc_hz": 800.0, "T": 0.8, "stop_deg": 170.0, "r_lip_mm": 0.0}
#: Legal lecleach-rows stop range (the FREEFORM meridian covers <= 88 deg).
ROWS_LECLEACH_STOP_RANGE = (90.0, 240.0)
ROWS_LECLEACH_CONSTRUCTION_LABEL = (
    "Fourcade 2015 Le Cleac'h exact construction (eqs 10-27, 42-43), verified against "
    "fig. 7 (R9-J); docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md")
#: ``lecleach_mod`` = the verified Fourcade meridian with a per-azimuth harmonic
#: stop/cutoff law.  NO published per-azimuth JMLC math exists; every variant is a
#: LABELED RECONSTRUCTION (lib-2 sections 2.1/2.5, 3).
ROWS_MOD_RECONSTRUCTION_LABEL = (
    "LABELED RECONSTRUCTION/HYPOTHESIS (lib-2 sections 2.1/2.5/3): per-azimuth harmonic "
    "stop/cutoff law over the verified Fourcade meridian; no published per-azimuth JMLC "
    "math exists. docs/research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md")
ROWS_MOD_KNOB_DEFAULTS = {"fc_hz": 800.0, "T": 0.8, "stop0_deg": 170.0,
                          "stop_a2_deg": 0.0, "stop_a4_deg": 0.0,
                          "stop_b1_deg": 0.0, "stop_b3_deg": 0.0,
                          "bend_b1_mm": 0.0, "r_lip_mm": 0.0}
#: ``lecleach_ar`` = an area-preserving aspect-ratio stretch of the verified march.
#: The label is quoted verbatim in provenance (task spec / lib-2 section 2.2).
ROWS_AR_CONSTRUCTION_LABEL = (
    "reconstruction of the published principle (AR evolution + T = 0.5); "
    "no published construction for this class exists")
ROWS_AR_KNOB_DEFAULTS = {"fc_hz": 800.0, "T": 0.5, "stop_deg": 170.0,
                         "AR_m": 2.0, "p": 1.0, "r_lip_mm": 0.0}
#: AR_t is pinned (the throat is circular); only AR_m and p are knobs.
ROWS_AR_THROAT_RATIO = 1.0

# ------------------------------------------------------------------ fix-6 contract
#: Harmonic stop-law LIST knobs (lib-2 C2, additive fractions of stop0).  These are the
#: shipped hybridization surface: ``stop(phi) = stop0 * (1 + sum a_2k cos(2k phi)
#: + sum b_(2k+1) sin((2k+1) phi))`` with phi from the HORIZONTAL axis.
ROWS_TASK_HARMONIC_LIST_KEYS = ("g_stop_cos2k", "g_stop_sin2k1")
MAX_TASK_STOP_HARMONIC_TERMS = 2      # k <= 2 is enough: [a2, a4] / [b1, b3]
#: A cos(phi) / other odd-cosine or even-sine stop key is not in the C2 basis: refused.
ROWS_TASK_LR_BREAKING_PREFIXES = ("g_stop_cos", "g_stop_sin")
#: iwata_ar: task knob names (g_ar_m / g_ar_p) over the existing AR profile helper.
ROWS_IWATA_KNOB_DEFAULTS = {"fc_hz": 800.0, "T": 0.5, "stop_deg": 180.0,
                            "ar_m": 2.0, "ar_p": 1.0}
IWATA_AR_P_EXP = 2.0     # ellipse section (the radius-field superellipse at p = 2)
IWATA_AR_LABEL = (
    "our reconstruction of the published principle (AR evolution + T=0.5); "
    "no published construction for this class exists "
    "(docs/research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md sections 2.2/3)")
#: toroidal_rollback: tangent-continuous circular lip arc (fixed 180 deg of wrap).
ROWS_TOROIDAL_KNOB_DEFAULTS = {"fc_hz": 800.0, "T": 0.8, "stop_deg": 170.0,
                               "r_lip_mm": 30.0}
TOROIDAL_WRAP_DEG = 180.0
TOROIDAL_LIP_SAMPLES = 181
TOROIDAL_LABEL = (
    "T1 verified Fourcade meridian + tangent-continuous circular lip arc [inferred "
    "geometric analogue, plan 9b.2 T7 / JMLC_FAMILY_VARIANTS_2026-10-25.md sections "
    "2.3-2.4]; not a reproduction of any published product and no published lip math "
    "exists")


def _spec_int(spec: dict, key: str, default: int, minimum: int) -> int:
    value = spec.get(key, default)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise registry.GeneratorError(f"{key} must be an integer, got {value!r}") from None
    if isinstance(value, bool) or not math.isfinite(number) or number != int(number):
        raise registry.GeneratorError(f"{key} must be an integer, got {value!r}")
    if int(number) < minimum:
        raise registry.GeneratorError(f"{key} must be >= {minimum}, got {int(number)}")
    return int(number)


def _check_spec(spec: dict) -> None:
    """Structurally validate a grid generator block / persisted spec (NO knobs, NO brief).

    Mirrors the ranges ``grid_points`` enforces, so ``families.validate`` and the mesh route
    reject the same blocks. Raises ``registry.GeneratorError``.
    """
    if not isinstance(spec, dict):
        raise registry.GeneratorError(f"grid spec must be a mapping, got {type(spec).__name__}")
    _spec_int(spec, "n_phi", MIN_PHI_QUARTER, MIN_PHI_QUARTER)
    _spec_int(spec, "n_s", 32, 8)
    max_wall = float(spec.get("max_wall_deg", 80.0))
    if not 10.0 <= max_wall < 90.0:
        raise registry.GeneratorError(f"max_wall_deg must be in [10, 90), got {max_wall}")
    wt = float(spec.get("wall_thickness_mm", 3.0))
    if not 0.5 <= wt <= 12.0:
        raise registry.GeneratorError(f"wall_thickness_mm must be in [0.5, 12], got {wt}")
    profile_h = spec.get("profile_h")
    if not isinstance(profile_h, dict):
        raise registry.GeneratorError(f"profile_h must be a mapping, got {profile_h!r}")
    if profile_h.get("type") not in registry.TYPES:
        raise registry.GeneratorError(
            f"unknown typology {profile_h.get('type')!r} (known: {list(registry.TYPES)})")
    profile_v = spec.get("profile_v", "same")
    if profile_v != "same":
        if not isinstance(profile_v, dict):
            raise registry.GeneratorError(
                f"profile_v must be 'same' or a mapping, got {profile_v!r}")
        if profile_v.get("type") not in registry.TYPES:
            raise registry.GeneratorError(
                f"unknown typology {profile_v.get('type')!r} (known: {list(registry.TYPES)})")
    if profile_v == "same" and spec.get("blend_v"):
        raise registry.GeneratorError(
            "blend_v needs an explicit profile_v (profile_v: same mirrors H)")


def _knob_map(knobs: dict) -> dict:
    """Flat knobs -> ``{str: finite float}`` (the only form stored in a Design)."""
    if knobs is None:
        return {}
    if not isinstance(knobs, dict):
        raise registry.GeneratorError(f"knobs must be a mapping, got {type(knobs).__name__}")
    out: dict = {}
    for key, value in knobs.items():
        k = str(key)
        if k in ROWS_TASK_HARMONIC_LIST_KEYS:
            if not isinstance(value, (list, tuple)):
                raise registry.GeneratorError(
                    f"knob {k!r} must be a list of numbers, got {value!r}")
            if len(value) > MAX_TASK_STOP_HARMONIC_TERMS:
                raise registry.GeneratorError(
                    f"knob {k!r} accepts at most {MAX_TASK_STOP_HARMONIC_TERMS} terms, "
                    f"got {len(value)}")
            terms = []
            for term in value:
                try:
                    number = float(term)
                except (TypeError, ValueError):
                    raise registry.GeneratorError(
                        f"knob {k!r} terms must be numbers, got {term!r}") from None
                if isinstance(term, bool) or not math.isfinite(number):
                    raise registry.GeneratorError(
                        f"knob {k!r} terms must be finite, got {term!r}")
                terms.append(number)
            out[k] = terms
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise registry.GeneratorError(f"knob {key!r} must be a number, got {value!r}") from None
        if isinstance(value, bool) or not math.isfinite(number):
            raise registry.GeneratorError(f"knob {key!r} must be finite, got {value!r}")
        out[k] = number
    return dict(sorted(out.items()))


def _shape_knobs(spec: dict, knobs: dict, prefix: str = "g"):
    """``(p, term_mm, k_modes, a_throat, a_mouth)`` with all GRID shape knobs validated."""
    p = _knob(knobs, prefix, "pnorm", GRID_DEFAULTS["pnorm"])
    if not math.isfinite(p) or p < 1.0:
        raise registry.GeneratorError(f"pnorm must be finite and >= 1, got {p}")
    term_knob = _knob(knobs, prefix, "term_side_mm", GRID_DEFAULTS["term_side_mm"])
    if not math.isfinite(term_knob):
        raise registry.GeneratorError(f"term_side_mm must be finite, got {term_knob}")
    term = abs(term_knob)
    k_modes = _fourier_k(knobs, prefix)
    if k_modes > MAX_FOURIER_K:
        raise registry.GeneratorError(
            f"G8 mode {k_modes} is beyond the supported maximum {MAX_FOURIER_K}")
    a_throat, a_mouth = [], []
    for k in range(1, k_modes + 1):
        a_throat.append(_knob(knobs, prefix, f"a{k}_throat", GRID_DEFAULTS["a_throat"]))
        a_mouth.append(_knob(knobs, prefix, f"a{k}_mouth", GRID_DEFAULTS["a_mouth"]))
    for a in (*a_throat, *a_mouth):
        if not math.isfinite(a):
            raise registry.GeneratorError("G8 a_k coefficients must be finite")
    return p, term, k_modes, np.asarray(a_throat), np.asarray(a_mouth)



def _knob(knobs: dict, prefix: str, name: str, default: float) -> float:
    full = f"{prefix}_{name}" if prefix else name
    return float(knobs.get(full, default))


def _fourier_k(knobs: dict, prefix: str) -> int:
    """Highest k with any ``{p}_a{k}_*`` knob; 2 when none is set (plan default)."""
    k_max = 0
    for name in knobs:
        head = f"{prefix}_a" if prefix else "a"
        if not str(name).startswith(head):
            continue
        tail = str(name)[len(head):]
        num, sep, which = tail.partition("_")
        if sep and which in ("throat", "mouth") and num.isdigit():
            k_max = max(k_max, int(num))
    return max(2, k_max)


def _meridians(spec: dict, knobs: dict, brief: dict, *, check_envelope: bool = True):
    """``(meridian_h, meridian_v, L_mm, source_angle_deg)`` on the shared depth.

    ``check_envelope=False`` is for the WP3 pre-mesh estimate only: it must be able to price a
    design that is over the brief depth instead of refusing it.
    """
    r0 = float(brief["driver"]["exit_radius_mm"])
    a0 = float(brief["driver"]["exit_angle_deg"])
    env = brief.get("envelope") or {}
    max_wall = float(spec.get("max_wall_deg", 80.0))
    if not 10.0 <= max_wall < 90.0:
        raise registry.GeneratorError(f"max_wall_deg must be in [10, 90), got {max_wall}")
    L_knob = float(knobs.get("L_mm", registry.DEFAULT_KNOBS["L_mm"]))
    if check_envelope and env and L_knob > float(env["max_depth_mm"]) + 1e-9:
        raise registry.GeneratorError(
            f"depth L_mm={L_knob:.1f} exceeds the brief envelope {env['max_depth_mm']} mm")

    if "profile_h" not in spec:
        raise registry.GeneratorError("grid generator needs profile_h")
    mh = registry.build_meridian(spec["profile_h"], knobs, "h", r0=r0, a0=a0, L=L_knob,
                                 max_wall=max_wall, phi=0.0)
    if spec.get("profile_v", "same") == "same":
        if spec.get("blend_v"):
            raise registry.GeneratorError(
                "blend_v needs an explicit profile_v (profile_v: same mirrors H)")
        mv = mh
    else:
        mv = registry.build_meridian(spec["profile_v"], knobs, "v", r0=r0, a0=a0, L=L_knob,
                                     max_wall=max_wall, phi=math.pi / 2)
    span = min(mh.length_mm, mv.length_mm)
    if check_envelope and env:
        span = min(span, float(env["max_depth_mm"]))
    if not span > 0.0:
        raise registry.GeneratorError(f"grid depth must be positive, got {span}")
    # The rounded source cap needs a nonzero throat wall angle; fall back to the brief's
    # driver exit angle when a meridian reports 0 (source_auto_angle_deg=0 would remove the cap).
    angle = float(mh.theta_deg[0])
    if not math.isfinite(angle) or abs(angle) < 1e-12:
        angle = a0
    if abs(angle) < 1e-12:
        raise registry.GeneratorError(
            "throat wall angle is 0 deg; a nonzero source_auto_angle_deg is required for the "
            "rounded source cap")
    return mh, mv, float(span), angle


def _radius_field(r_h: np.ndarray, r_v: np.ndarray, phi: np.ndarray, p: float,
                  a_throat: np.ndarray, a_mouth: np.ndarray, s: np.ndarray) -> np.ndarray:
    """``r(s, phi)`` in mm, shape ``(n_phi, n_s)``."""
    p = float(p)
    if not math.isfinite(p) or p < 1.0:
        raise registry.GeneratorError(f"pnorm must be finite and >= 1, got {p}")
    cP, sP = np.cos(phi)[:, None], np.sin(phi)[:, None]
    rV, rH = r_v[None, :], r_h[None, :]
    denom = (np.abs(rV * cP) ** p + np.abs(rH * sP) ** p) ** (1.0 / p)
    if not np.all(denom > 0.0):
        raise registry.GeneratorError("superellipse radius field has a zero denominator")
    r = (rH * rV) / denom
    # G8: a_k(s) linear in s; the modulation factor must stay positive (a physical radius).
    a_s = (1.0 - s)[None, :] * a_throat[:, None] + s[None, :] * a_mouth[:, None]  # (K, n_s)
    factor = 1.0 + sum(a_s[k, :][None, :] * np.cos(2.0 * (k + 1) * phi)[:, None]
                       for k in range(len(a_throat)))
    if float(np.min(factor)) <= 1e-9:
        raise registry.GeneratorError(
            f"G8 modulation makes the radius non-positive "
            f"(min factor {float(np.min(factor)):.6g}); reduce a_k")
    return r * factor


def _row_min_nonadjacent_gap(row: np.ndarray, limit_mm: float) -> float:
    """Min 3-D distance between points of ONE meridian row that are not neighbours ON it (mm).

    Two stations are "non-adjacent" when the arc length between them along the row is at least
    ``pi/2 * limit_mm``: the arc of a U-turn whose two legs sit exactly ``limit_mm`` apart. A
    smooth bend gentler than that U-turn therefore never reads as self-approach, while a fold
    tighter than it does. (2026-10-26 fix: the old ``>= limit_mm`` arc rule compared a CHORD
    against an equal ARC, and a chord is always shorter than its arc on any curved wall, so
    ordinary lip curvature was refused at 7.998 / 8.000 mm against an 8 mm limit.) That is the
    quantity the 2026-10-24 curl probe
    measured (``NOTES_FOR_SENIOR.md``: the profile folding back onto its own earlier part, "min
    true distance 19.6 / 18.5 mm"). An index-offset rule is NOT used: with a dense station grid
    it would call ordinary sampling "self-approach". Distances between DIFFERENT phi rows are
    not self-approach either -- all rows meet at the throat by construction -- so rows are
    checked one at a time.
    """
    pts = np.asarray(row, dtype=float)
    arc = np.concatenate(([0.0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))))
    separation = np.abs(arc[:, None] - arc[None, :])
    far = separation >= float(limit_mm) * (math.pi / 2.0)
    if not np.any(far):
        return math.inf
    delta = pts[:, None, :] - pts[None, :, :]
    return float(np.min(np.linalg.norm(delta, axis=-1)[far]))


def _sheet_min_nonadjacent_gap(grid: np.ndarray, limit_mm: float) -> float:
    g = np.asarray(grid, dtype=float)
    return min(_row_min_nonadjacent_gap(g[i], limit_mm) for i in range(g.shape[0]))


def min_self_approach_mm(inner: np.ndarray, outer: np.ndarray | None = None, *,
                         limit_mm: float) -> float:
    """Min per-row non-adjacent gap (mm) over the inner sheet and, when given, the outer shell.

    ``limit_mm`` is the arc-length separation above which two stations count as non-adjacent
    (callers pass ``2 t + 2``). The shell thickness between corresponding inner and outer points
    is a designed connection, so the two sheets are compared against themselves only.
    """
    gap = _sheet_min_nonadjacent_gap(inner, limit_mm)
    if outer is not None:
        gap = min(gap, _sheet_min_nonadjacent_gap(outer, limit_mm))
    return float(gap)


def _self_approach_limit(spec: dict) -> float:
    """``2 t + 2`` for the generator block's wall thickness (the dossier 2.4 P4 line)."""
    return 2.0 * float(spec.get("wall_thickness_mm", 3.0)) + SELF_APPROACH_MARGIN_MM


def grid_points(spec: dict, knobs: dict, brief: dict, *, prefix: str = "g",
                full_circle: bool = False) -> tuple[np.ndarray, dict]:
    """GRID radius field -> ``(inner_points (n_phi, n_s + 1, 3) mm, meta)``.

    ``spec`` is the generator block (``profile_h`` / ``profile_v`` / ``n_phi`` / ``n_s`` /
    ``max_wall_deg``); ``knobs`` are the search knobs; ``brief`` supplies the driver exit and
    the envelope. ``phi`` is measured from +x, so row 0 is the H plane (``y = 0``) and the last
    quarter row is the V plane (``x = 0``).

    WP9b: a spec carrying ``rows`` dispatches to :func:`rows_per_azimuth` (the per-azimuth
    Salmon rows); the superellipse field below is then unused.  ``full_circle`` is a
    superellipse-only helper and is refused for rows.
    """
    if isinstance(spec, dict) and "rows" in spec:
        if full_circle:
            raise registry.GeneratorError(
                "the rows kind is quarter/half only (use n_phi / the mesher's mirror "
                "planes; a full/free model needs the twist/asymmetry pass)")
        return rows_per_azimuth(spec, knobs, brief, prefix=prefix)
    n_phi = _spec_int(spec, "n_phi", MIN_PHI_QUARTER, MIN_PHI_QUARTER)
    n_s = _spec_int(spec, "n_s", 32, 8)
    _check_spec(spec)

    mh, mv, L, angle = _meridians(spec, knobs, brief)
    p, term, k_modes, a_throat, a_mouth = _shape_knobs(spec, knobs, prefix)

    s = np.linspace(0.0, 1.0, n_s + 1)
    z_base = s * L
    r_h = np.interp(z_base, mh.z_mm, mh.r_mm)
    r_v = np.interp(z_base, mv.z_mm, mv.r_mm)
    if not (np.all(r_h > 0.0) and np.all(r_v > 0.0)):
        raise registry.GeneratorError("meridian radius must stay positive on the common z grid")

    phi = np.linspace(0.0, 0.5 * math.pi, n_phi)
    radius = _radius_field(r_h, r_v, phi, p, a_throat, a_mouth, s)
    # G9: smoothstep weight, negative (rollback) side depth, cos^2 phi is mirror-safe.
    w_mouth = 3.0 * s ** 2 - 2.0 * s ** 3
    dz = -term * np.cos(phi) ** 2
    z = z_base[None, :] + dz[:, None] * w_mouth[None, :]

    grid = np.stack((radius * np.cos(phi)[:, None],
                     radius * np.sin(phi)[:, None],
                     z), axis=-1)
    # Exact mirror planes: row 0 on y=0, last quarter row on x=0 (float cos/sin noise removed).
    grid[0, :, 1] = 0.0
    grid[-1, :, 0] = 0.0

    meta: dict = {
        "family": "grid",
        "quarter": not full_circle,
        "n_phi": int(n_phi if not full_circle else 4 * (n_phi - 1)),
        "n_phi_quarter": int(n_phi),
        "n_s": int(n_s),
        "phi_span_deg": 360.0 if full_circle else 90.0,
        "source_auto_angle_deg": float(angle),
        "L_mm": float(L),
        "pnorm": float(p),
        "pnorm_note": "constant p(s) in this pass (plan names a function)",
        "fourier_k": int(k_modes),
        "a_k": {k: {"throat": float(a_throat[k - 1]), "mouth": float(a_mouth[k - 1])}
                for k in range(1, k_modes + 1)},
        "term_side_mm": float(-term),
        "w_mouth": "smoothstep(s) = 3s^2 - 2s^3 [inferred]",
        "mouth_radius_h_mm": float(radius[0, -1]),
        "mouth_radius_v_mm": float(radius[-1, -1]),
        "throat_radius_mm": float(radius[0, 0]),
        "sign_conventions": {
            "phi": "measured from +x; row 0 = H plane (y=0), last quarter row = V plane (x=0)",
            "term_side_mm": "positive knob = side rollback; applied dz = -|knob| * cos^2(phi)",
            "outer_offset": "outward in-plane normal, +rho at the throat (see grid_outer_points)",
        },
        "min_self_approach_mm": float(_sheet_min_nonadjacent_gap(grid, _self_approach_limit(spec))),
        "min_self_approach_scope": ("inner sheet only; grid_outer_points also guards the shell"),
        "min_self_approach_limit_mm": float(_self_approach_limit(spec)),
    }
    if not full_circle:
        return grid, meta
    full = _full_circle(grid)
    meta["min_self_approach_mm"] = float(
        _sheet_min_nonadjacent_gap(full, _self_approach_limit(spec)))
    meta["min_self_approach_scope"] = "inner sheet only, full-circle rows"
    return full, meta


def _full_circle(quarter: np.ndarray) -> np.ndarray:
    """Mirror a quarter grid four times, dropping repeated seam rows.

    Row ``k`` of the quarter is at ``phi = k * 90 / (n_phi - 1)`` degrees, so the result is the
    same rows at ``phi = m * 90 / (n_phi - 1)``, ``m = 0 .. 4 (n_phi - 1) - 1`` (a uniform
    endpoint-excluded full circle). The first ``n_phi`` rows are the quarter grid unchanged.
    """
    mirror_x = quarter * np.array([-1.0, 1.0, 1.0])       # x -> -x, phi -> 180 - phi
    mirror_xy = quarter * np.array([-1.0, -1.0, 1.0])     # phi -> 180 + phi
    mirror_y = quarter * np.array([1.0, -1.0, 1.0])       # phi -> -phi (360 - phi)
    return np.concatenate([quarter,
                           mirror_x[::-1][1:],
                           mirror_xy[1:],
                           mirror_y[::-1][1:-1]], axis=0)


def check_self_approach(inner: np.ndarray, outer: np.ndarray, wall_thickness_mm: float) -> float:
    """Raise ``GeneratorError`` unless the min non-adjacent gap is >= ``2 t + 2 mm``.

    Returns the measured gap (mm) so callers can record it. This is the dossier section 2.4 P4
    refusal; it is the one place the threshold lives.
    """
    t = float(wall_thickness_mm)
    if not math.isfinite(t) or t <= 0.0:
        raise registry.GeneratorError(f"wall_thickness_mm must be positive, got {t}")
    limit = 2.0 * t + SELF_APPROACH_MARGIN_MM
    gap = min_self_approach_mm(inner, outer, limit_mm=limit)
    if gap < limit:
        raise registry.GeneratorError(
            f"grid self-approach: min non-adjacent gap {gap:.3f} mm is below 2t + 2 mm = "
            f"{limit:.3f} mm (wall_thickness_mm={t:g}); graded infeasible")
    return gap


def grid_outer_points(inner: np.ndarray, wall_thickness_mm: float, *,
                      half: bool = False, half_xz: bool = False,
                      full: bool = False, check: bool = True) -> np.ndarray:
    """Explicit outer shell: in-plane normal offset of each row's ``(rho, z)`` profile.

    Fourcade 2015 eqs 28-29 form applied in the row's own meridian half-plane
    (``docs/research/typologies/WP9_WP9B_GROUNDING_2026-10-25.md`` section 2.4): the outward
    normal is the tangent ``(drho, dz)`` rotated by -90 deg, ``n = (dz, -drho) / |(drho, dz)|``,
    which is continuous through a rollback (it is just the tangent rotated with the profile).
    ``phi`` is unchanged, so the symmetry-plane rows stay on their plane: quarter row 0 on
    ``y = 0`` and last on ``x = 0``; half BOTH endpoint rows on ``x = 0`` (``half=True``);
    half_xz BOTH endpoint rows on ``y = 0`` (``half_xz=True``).

    Raises ``GeneratorError`` when a min non-adjacent gap (inner or outer, mm) is below
    ``2 * wall_thickness_mm + 2 mm`` (dossier 2.4 P4).
    """
    grid = np.asarray(inner, dtype=float)
    t = float(wall_thickness_mm)
    if grid.ndim != 3 or grid.shape[2] != 3 or grid.shape[0] < 2 or grid.shape[1] < 2:
        raise registry.GeneratorError(
            f"inner grid must be (n_phi, n_s + 1, 3), got {grid.shape}")
    if not np.all(np.isfinite(grid)):
        raise registry.GeneratorError("inner grid contains non-finite values")
    if not math.isfinite(t) or t <= 0.0:
        raise registry.GeneratorError(f"wall_thickness_mm must be positive, got {t}")

    rho = np.hypot(grid[..., 0], grid[..., 1])
    phi = np.arctan2(grid[..., 1], grid[..., 0])
    d_rho = np.gradient(rho, axis=1)
    d_z = np.gradient(grid[..., 2], axis=1)
    norm = np.hypot(d_rho, d_z)
    if not np.all(norm > 0.0):
        raise registry.GeneratorError("degenerate grid row: zero tangent in the (rho, z) plane")
    n_rho = d_z / norm
    n_z = -d_rho / norm
    outer = np.empty_like(grid)
    outer[..., 0] = (rho + t * n_rho) * np.cos(phi)
    outer[..., 1] = (rho + t * n_rho) * np.sin(phi)
    outer[..., 2] = grid[..., 2] + t * n_z
    if full:
        pass                       # a closed full ring: no mirror planes, the shell as-is
    elif half:
        outer[0, :, 0] = 0.0
        outer[-1, :, 0] = 0.0
    elif half_xz:
        outer[0, :, 1] = 0.0       # phi = 0 -> y = 0 (xz plane)
        outer[-1, :, 1] = 0.0      # phi = 180 -> y = 0
    else:
        outer[0, :, 1] = 0.0
        outer[-1, :, 0] = 0.0

    if check:                      # the sandbox draws a refused shape: it checks separately
        check_self_approach(grid, outer, t)
    return outer

# ------------------------------------------------------------------ WP9b rows machinery


def _rows_declared_span(spec: dict) -> str | None:
    """The EXPLICIT ``span`` field (``quarter``/``half``/``half_xz``/``full``), or None."""
    span = spec.get("span")
    if span is None:
        return None
    if span not in ROWS_SPANS:
        raise registry.GeneratorError(
            f"grid rows span must be one of {list(ROWS_SPANS)}, got {span!r}")
    return str(span)


def _rows_lecleach_asym_knobs(knob_map: dict, prefix: str = "g") -> dict:
    """Validated ``rows: {type: lecleach_asym}`` knobs (owner-approved 2026-10-25).

    The verified Fourcade march per azimuth + the odd-cosine single-sided asymmetry
        r(phi, s) *= 1 + eps_m * w(s) * cos(phi)
    with ``w`` the smoothstep window opening at the arc fraction ``eps_start``
    (0 stays a legal value: it produces the SYMMETRIC verified rows exactly; only
    ``eps_m != 0`` forces a non-quarter model).  The asymmetry is even under the up/down
    mirror ``phi -> -phi``, so ``eps_m != 0`` is representable on the seam-free FULL ring
    OR on the UPPER-HALF model (``span: half_xz``, phi 0..180, mirror plane xz); a plain
    ``span: half`` (x >= 0) is not a symmetry half for it.  The list harmonic stop/bend
    contract rides along (on a full model ANY phi basis is representable, so the
    quarter/half basis restrictions do not bind).  The throat stays EXACT (w(0) = 0 at
    the window start: every row still shares the driver's exit radius/angle).
    """
    allowed = {f"{prefix}_fc_hz", f"{prefix}_T", f"{prefix}_stop_deg",
               f"{prefix}_r_lip_mm", f"{prefix}_eps_m", f"{prefix}_eps_start",
               f"{prefix}_stop_cos2k", f"{prefix}_stop_sin2k1",
               f"{prefix}_bend_sin1_mm"}
    foreign = sorted(str(k) for k in knob_map
                     if str(k).startswith(f"{prefix}_") and k not in allowed)
    if foreign:
        raise registry.GeneratorError(
            f"lecleach_asym rows accept only {prefix}_fc_hz / {prefix}_T / "
            f"{prefix}_stop_deg / {prefix}_eps_m / {prefix}_eps_start / "
            f"{prefix}_r_lip_mm (+ the list harmonic/bend contract stop_cos2k / "
            f"stop_sin2k1 / bend_sin1_mm); got foreign knob(s) {foreign}")
    out = {}
    for name, default in (("fc_hz", ROWS_LECLEACH_KNOB_DEFAULTS["fc_hz"]),
                          ("T", ROWS_LECLEACH_KNOB_DEFAULTS["T"]),
                          ("stop_deg", ROWS_LECLEACH_KNOB_DEFAULTS["stop_deg"]),
                          ("eps_m", ROWS_KNOB_DEFAULTS["eps_m"]),
                          ("eps_start", ROWS_KNOB_DEFAULTS["eps_start"])):
        out[name] = float(knob_map.get(f"{prefix}_{name}", default))
    for name, value in out.items():
        if not math.isfinite(value):
            raise registry.GeneratorError(
                f"lecleach_asym rows: {name} must be finite, got {value!r}")
    if out["fc_hz"] <= 0.0:
        raise registry.GeneratorError(
            f"lecleach_asym rows: fc_hz must be > 0, got {out['fc_hz']}")
    if out["T"] < 0.0:
        raise registry.GeneratorError(f"lecleach_asym rows: T must be >= 0, got {out['T']}")
    lo, hi = ROWS_LECLEACH_STOP_RANGE
    if not lo <= out["stop_deg"] <= hi:
        raise registry.GeneratorError(
            f"lecleach_asym rows: stop_deg must be in [{lo:g}, {hi:g}], got {out['stop_deg']}")
    if not -ROWS_MAX_EPS <= out["eps_m"] <= ROWS_MAX_EPS:
        raise registry.GeneratorError(
            f"lecleach_asym rows: eps_m must be in [-{ROWS_MAX_EPS:g}, "
            f"{ROWS_MAX_EPS:g}] (signed; the sign picks which side widens), got {out['eps_m']}")
    if not 0.0 <= out["eps_start"] < 1.0:
        raise registry.GeneratorError(
            f"lecleach_asym rows: eps_start must be in [0, 1) (the window's opening arc "
            f"fraction), got {out['eps_start']}")
    out["r_lip_mm"] = _rows_lip_mm(knob_map, prefix)
    return out


def _rows_eps_window(s_frac: np.ndarray, start: float) -> np.ndarray:
    """Smoothstep window on the arc fraction, opening at ``start`` (0 -> 0, 1 -> 1)."""
    t = np.clip((np.asarray(s_frac, dtype=float) - float(start))
                / (1.0 - float(start)), 0.0, 1.0)
    return 3.0 * t ** 2 - 2.0 * t ** 3


def _rows_span_phis(n_phi: int, span: str) -> np.ndarray:
    """Azimuths for a rows kind: ``quarter`` -> [0, 90]; ``half`` -> [-90, +90];

    ``half_xz`` -> [0, 180]; ``full`` -> ``[0, 360)`` (n_phi rows, endpoint EXCLUDED - the
    seam row at 360 deg would duplicate row 0's phi = 0).  The phi ORIGIN is pinned to the
    horizontal (+x) axis in every span; the span only decides how much of the circle is
    present.  A half or half_xz model needs an ODD n_phi >= MIN_PHI_HALF (the half span so
    phi = 0 and both +/-90 deg rows exist; half_xz so the phi = 0 and 180 deg endpoint rows
    and the phi = 90 deg vertical row exist); a full model needs n_phi >= MIN_PHI_FULL.
    """
    if span == "half":
        if n_phi < MIN_PHI_HALF:
            raise registry.GeneratorError(
                f"half-model rows need n_phi >= {MIN_PHI_HALF} (honest half-span "
                f"resolution); got n_phi={n_phi}")
        if n_phi % 2 == 0:
            raise registry.GeneratorError(
                "half-model rows need an ODD n_phi (the phi = 0 horizontal row and both "
                f"+/-90 deg endpoint rows must exist); got n_phi={n_phi}")
        return np.linspace(-0.5 * math.pi, 0.5 * math.pi, n_phi)
    if span == "half_xz":
        if n_phi < MIN_PHI_HALF:
            raise registry.GeneratorError(
                f"half_xz-model rows need n_phi >= {MIN_PHI_HALF} (honest half-span "
                f"resolution); got n_phi={n_phi}")
        if n_phi % 2 == 0:
            raise registry.GeneratorError(
                "half_xz-model rows need an ODD n_phi (the phi = 0 and 180 deg endpoint "
                f"rows on the xz mirror plane, plus the phi = 90 deg vertical row); got "
                f"n_phi={n_phi}")
        return np.linspace(0.0, math.pi, n_phi)
    if span == "full":
        if n_phi < MIN_PHI_FULL:
            raise registry.GeneratorError(
                f"full-ring rows need n_phi >= {MIN_PHI_FULL} (honest full-circle "
                f"resolution); got n_phi={n_phi}")
        return np.linspace(0.0, 2.0 * math.pi, n_phi, endpoint=False)
    return np.linspace(0.0, 0.5 * math.pi, n_phi)


def _rows_span_requested(kind: str, spec: dict, knob_map: dict, prefix: str = "g") -> str:
    """Resolve the row span: explicit ``span`` OR the kind's forcing rules (C2, binding).

    Forcing rules (each refuses a contradictory explicit declaration loudly instead of
    silently mis-meshing):
    * ``lecleach_mod`` with a b-term / bend knob PRESENT forces ``half``;
    * ``lecleach_asym`` keeps the left-right asymmetry on a ``half_xz`` (upper-half) or
      ``full`` ring; a plain ``half`` (x >= 0) is refused because it is not a symmetry
      half for the odd cosine.  With eps_m == 0 the same spans plus ``quarter`` are legal.
    * ``span: half_xz`` is implemented for ``lecleach_asym`` only in this pass; another
      rows kind that declares it is refused loudly rather than silently mis-meshed.
    """
    declared = _rows_declared_span(spec)
    if kind == "lecleach_mod" and _rows_mod_half(knob_map, prefix):
        if declared in ("quarter", "half_xz"):
            raise registry.GeneratorError(
                "grid rows: a b-term / axial-bend knob is present, which forces the HALF "
                "model (phi -90..+90, symmetry plane yz, quadrants '14'); remove "
                "span: quarter / span: half_xz or set span: half")
        return "half"
    if kind == "lecleach_asym":
        eps = float(knob_map.get(f"{prefix}_eps_m", 0.0))
        if eps != 0.0:
            if declared in ("quarter", "half"):
                raise registry.GeneratorError(
                    "grid rows: the odd-cosine asymmetry (eps_m != 0) breaks the "
                    "left-right mirror; it needs the seam-free FULL ring (phi 0..360, "
                    "quadrants '1234') or the UPPER-HALF model (span: half_xz, phi "
                    "0..180, quadrants '12'); remove span or set span: full / span: half_xz")
            return "full" if declared is None else declared
        if declared == "half":
            raise registry.GeneratorError(
                "grid rows: lecleach_asym does not use the x >= 0 half model; use span: "
                "half_xz (upper half, quadrants '12'), span: quarter or span: full")
        return declared or "quarter"
    if declared == "half_xz":
        raise registry.GeneratorError(
            f"grid rows: span: half_xz is implemented for lecleach_asym rows only; "
            f"{kind} must use quarter/half/full")
    if declared is None:
        return "half" if (kind == "lecleach_mod" and False) else "quarter"
    return declared


def _rows_half_requested(kind: str, spec: dict, knobs: dict, prefix: str = "g") -> bool:
    """Legacy half-flag = ``_rows_span_requested(...) == 'half'`` (kept for callers)."""
    return _rows_span_requested(kind, spec, _knob_map(knobs), prefix) == "half"


def _rows_check_spec(spec: dict) -> str:
    """Validate a rows-kind grid spec; return the rows type. Raises ``GeneratorError``."""
    if not isinstance(spec, dict):
        raise registry.GeneratorError(f"grid spec must be a mapping, got {type(spec).__name__}")
    rows = spec.get("rows")
    if not isinstance(rows, dict):
        raise registry.GeneratorError(f"grid rows must be a mapping, got {rows!r}")
    unknown = sorted(set(rows) - {"type"})
    if unknown:
        raise registry.GeneratorError(f"grid rows: unknown key(s) {unknown}")
    kind = rows.get("type")
    if kind not in ROWS_TYPES:
        raise registry.GeneratorError(
            f"unknown rows type {kind!r} (known: {list(ROWS_TYPES)})")
    allowed = {"name", "knobs", *ROWS_ALLOWED_SPEC_KEYS}
    foreign = sorted(set(spec) - allowed)
    if foreign:
        raise registry.GeneratorError(
            f"rows grid spec: foreign key(s) {foreign} (allowed: {sorted(allowed)})")
    _rows_declared_span(spec)
    _spec_int(spec, "n_phi", MIN_PHI_QUARTER, MIN_PHI_QUARTER)
    _spec_int(spec, "n_s", 32, 8)
    wt = float(spec.get("wall_thickness_mm", 3.0))
    if not 0.5 <= wt <= 12.0:
        raise registry.GeneratorError(f"wall_thickness_mm must be in [0.5, 12], got {wt}")
    return str(kind)


def _rows_knob(knobs: dict, prefix: str, name: str) -> float:
    full = f"{prefix}_{name}" if prefix else name
    return float(knobs.get(full, ROWS_KNOB_DEFAULTS[name]))


def _rows_shape_knobs(knobs: dict, prefix: str = "g") -> dict:
    """Validated salmon shape knobs (fc_h/fc_v, T, stop, x_amp, x_fc) in base units.

    Salmon harmonics are the LIST contract (``stop_cos2k`` / ``stop_sin2k1`` /
    ``bend_sin1_mm``); the deleted scalar a2/a4/b1/b3 keys are refused as foreign so a
    typed-but-ignored knob can never silently change nothing.
    2026-10-25 additions (owner-approved): the even-lobe mouth ripple
    (``ripple_lobes``/``ripple_amp_mm``/``ripple_start`` - the pleats feature,
    MOUTH_RIPPLE_SERRATION dossier) on this kind; the odd-cosine asymmetry keys
    (``eps_m``/``eps_start``) are lecleach_asym-only and refused here.
    """
    allowed = {f"{prefix}_fc_h_hz", f"{prefix}_fc_v_hz", f"{prefix}_T",
               f"{prefix}_stop_deg", f"{prefix}_x_amp", f"{prefix}_x_fc",
               f"{prefix}_r_lip_mm", f"{prefix}_stop_cos2k",
               f"{prefix}_stop_sin2k1", f"{prefix}_bend_sin1_mm",
               f"{prefix}_ripple_lobes", f"{prefix}_ripple_amp_mm",
               f"{prefix}_ripple_start", f"{prefix}_fc_fold", f"{prefix}_fc_union"}
    foreign = sorted(str(k) for k in knobs
                     if str(k).startswith(f"{prefix}_") and k not in allowed)
    if foreign:
        raise registry.GeneratorError(
            f"salmon rows accept only {prefix}_fc_h_hz / {prefix}_fc_v_hz / {prefix}_T / "
            f"{prefix}_stop_deg / {prefix}_x_amp / {prefix}_x_fc / {prefix}_r_lip_mm / "
            f"{prefix}_stop_cos2k / {prefix}_stop_sin2k1 / {prefix}_bend_sin1_mm "
            "(salmon kinds + the even-lobe mouth ripple g_ripple_lobes / g_ripple_amp_mm / "
            "g_ripple_start; the odd-cosine eps keys are lecleach_asym-only); "
            f"got foreign knob(s) {foreign}")
    fc_h = _rows_knob(knobs, prefix, "fc_h_hz")
    fc_v = _rows_knob(knobs, prefix, "fc_v_hz")
    T = _rows_knob(knobs, prefix, "T")
    stop = _rows_knob(knobs, prefix, "stop_deg")
    x_amp = _rows_knob(knobs, prefix, "x_amp")
    x_fc = _rows_knob(knobs, prefix, "x_fc")
    for name, value in (("fc_h_hz", fc_h), ("fc_v_hz", fc_v), ("T", T),
                        ("stop_deg", stop), ("x_amp", x_amp), ("x_fc", x_fc)):
        if not math.isfinite(value):
            raise registry.GeneratorError(f"{name} must be finite, got {value!r}")
    if fc_h <= 0.0 or fc_v <= 0.0:
        raise registry.GeneratorError(
            f"fc_h_hz / fc_v_hz must be > 0, got {fc_h} / {fc_v}")
    if T < 0.0:
        raise registry.GeneratorError(f"T must be >= 0, got {T}")
    if not 0.0 < stop < 360.0:
        raise registry.GeneratorError(f"stop_deg must be in (0, 360), got {stop}")
    if abs(stop - 180.0) < 1e-9:
        raise registry.GeneratorError(
            "stop_deg=180 is the cap-area asymptote; use a stop below or above 180 deg")
    if not -ROWS_MAX_X_AMP <= x_amp <= ROWS_MAX_X_AMP:
        raise registry.GeneratorError(
            f"x_amp must be in [-{ROWS_MAX_X_AMP}, {ROWS_MAX_X_AMP}] (signed), got {x_amp}")
    if not 0.0 <= x_fc <= ROWS_MAX_X_FC:
        raise registry.GeneratorError(
            f"x_fc must be in [0, {ROWS_MAX_X_FC}], got {x_fc}")
    fold = _rows_knob(knobs, prefix, "fc_fold")
    if fold not in ROWS_FC_FOLDS:
        raise registry.GeneratorError(
            f"fc_fold must be one of {list(ROWS_FC_FOLDS)} (2 = two petals, 4 = four petals on the "
            f"axes joined on the diagonals), got {fold!r}")
    union = _rows_knob(knobs, prefix, "fc_union")
    if union not in (0.0, 1.0):
        raise registry.GeneratorError(f"fc_union must be 0 or 1, got {union!r}")
    if union and fold != 2.0:
        raise registry.GeneratorError("fc_union and fc_fold 4 are alternatives; use one")
    ripple = _rows_ripple_knobs(knobs, prefix)
    return {"fc_h_hz": fc_h, "fc_v_hz": fc_v, "T": T, "stop_deg": stop,
            "x_amp": x_amp, "x_fc": x_fc, "fc_fold": fold, "fc_union": union, **ripple}


def _rows_ripple_knobs(knobs: dict, prefix: str = "g") -> dict:
    """Validated even-lobe mouth ripple knobs (the pleats feature) in base units.

    ``r *= 1 + ripple_amp_mm * w(s) * cos(ripple_lobes * phi)`` with the smoothstep
    window ``w`` opening at the arc fraction ``ripple_start`` (0.7-0.95 shipped range;
    empty = the window is the whole profile, as for the x_amp modulation). The lobe
    count must be an EVEN integer in [6, 24] (a C2-quarter-safe even cosine; odd counts
    break the left-right mirror and stay refused). Zero/absent knobs = no ripple
    (geometry identical to today's rows). Rows also get an honest-resolution check
    against the kind's row span (>= 4 phi samples per lobe period) - enforced by the
    callers once the span is resolved (see _rows_ripple_resolution_guard).
    """
    allowed = {f"{prefix}_ripple_lobes", f"{prefix}_ripple_amp_mm", f"{prefix}_ripple_start"}
    foreign = sorted(str(k) for k in knobs
                     if str(k).startswith(f"{prefix}_ripple") and k not in allowed)
    if foreign:
        raise registry.GeneratorError(
            f"ripple knobs accept {prefix}_ripple_lobes / {prefix}_ripple_amp_mm / "
            f"{prefix}_ripple_start; got foreign knob(s) {foreign}")
    amp = _rows_knob(knobs, prefix, "ripple_amp_mm")
    if not math.isfinite(amp) or amp < 0.0 or amp > ROWS_MAX_RIPPLE_AMP_MM:
        raise registry.GeneratorError(
            f"ripple_amp_mm must be in [0, {ROWS_MAX_RIPPLE_AMP_MM:g}] mm, got {amp!r}")
    lobes = _rows_knob(knobs, prefix, "ripple_lobes")
    if not math.isfinite(lobes) or lobes != int(lobes) or lobes < 0:
        raise registry.GeneratorError(
            f"ripple_lobes must be a non-negative integer, got {lobes!r}")
    lobes = int(lobes)
    if lobes == 0:
        if amp > 0.0:
            raise registry.GeneratorError(
                "ripple_amp_mm > 0 needs ripple_lobes set (an even integer in "
                f"[{ROWS_RIPPLE_LOBES_RANGE[0]:g}, {ROWS_RIPPLE_LOBES_RANGE[1]:g}])")
        return {"ripple_lobes": 0, "ripple_amp_mm": 0.0, "ripple_start": 0.0}
    lo_n, hi_n = ROWS_RIPPLE_LOBES_RANGE
    if not (lo_n <= lobes <= hi_n and lobes % 2 == 0):
        raise registry.GeneratorError(
            f"ripple_lobes must be an EVEN integer in [{lo_n:g}, {hi_n:g}] "
            "(even cosines keep the left-right mirror; odd counts are refused), "
            f"got {lobes}")
    start = _rows_knob(knobs, prefix, "ripple_start")
    if not math.isfinite(start) or not 0.0 <= start < 1.0:
        raise registry.GeneratorError(
            f"ripple_start must be in [0, 1) (the window's opening arc fraction), got {start!r}")
    return {"ripple_lobes": lobes, "ripple_amp_mm": float(amp), "ripple_start": float(start)}


def _rows_ripple_resolution_guard(lobes: int, span_rad: float, n_phi: int) -> None:
    """Refuse a ripple the row grid cannot honestly represent (>= 4 samples per lobe)."""
    if lobes <= 0:
        return
    d_phi = span_rad / (n_phi - 1)
    per_period = (2.0 * math.pi / lobes) / d_phi
    if per_period < ROWS_RIPPLE_SAMPLES_PER_LOBE:
        raise registry.GeneratorError(
            f"the mouth ripple with {lobes} lobes needs >= "
            f"{ROWS_RIPPLE_SAMPLES_PER_LOBE:g} phi samples per lobe period on this row "
            f"span (d_phi = {np.degrees(d_phi):.3g} deg over "
            f"{np.degrees(span_rad):.0f} deg x n_phi {n_phi}); raise n_phi or drop the "
            "ripple lobes")


def _rows_lip_mm(knobs: dict, prefix: str, name: str = "r_lip_mm") -> float:
    """Validated torus-lip tube radius (mm); 0 = today's geometry exactly."""
    full = f"{prefix}_{name}" if prefix else name
    r = float(knobs.get(full, 0.0))
    if not math.isfinite(r):
        raise registry.GeneratorError(f"{name} must be finite, got {r!r}")
    if r < 0.0 or r > ROWS_MAX_R_LIP_MM:
        raise registry.GeneratorError(
            f"{name} must be in [0, {ROWS_MAX_R_LIP_MM:g}] mm, got {r}")
    return r


def _rows_lecleach_knobs(knobs: dict, prefix: str = "g") -> dict:
    """Validated ``rows: {type: lecleach}`` knobs: ``fc_hz``, ``T``, ``stop_deg``, lip.

    The rows are axisymmetric, so there is deliberately no ``fc_v_hz`` and no
    ``x_amp``/``x_fc``; a knob outside this set under the ``g_`` prefix is refused
    (a typed-but-ignored knob would silently change nothing).  ``g_r_lip_mm`` is the
    lib-2 torus-lip option (default 0 = byte-identical to the plain verified march).
    """
    allowed = {f"{prefix}_fc_hz", f"{prefix}_T", f"{prefix}_stop_deg", f"{prefix}_r_lip_mm",
               f"{prefix}_fc_h_hz", f"{prefix}_fc_v_hz",
               f"{prefix}_stop_cos2k", f"{prefix}_stop_sin2k1",
               f"{prefix}_bend_sin1_mm"}
    foreign = sorted(str(k) for k in knobs
                     if str(k).startswith(f"{prefix}_") and k not in allowed)
    if foreign:
        raise registry.GeneratorError(
            f"lecleach rows accept only {prefix}_fc_hz / {prefix}_T / {prefix}_stop_deg / "
            f"{prefix}_r_lip_mm (+ optional fc_h_hz/fc_v_hz pair, stop_cos2k, "
            f"stop_sin2k1, bend_sin1_mm); got foreign knob(s) {foreign}")
    has_h = f"{prefix}_fc_h_hz" in knobs
    has_v = f"{prefix}_fc_v_hz" in knobs
    if has_h != has_v:
        present = f"{prefix}_fc_h_hz" if has_h else f"{prefix}_fc_v_hz"
        raise registry.GeneratorError(
            f"foreign knob(s) [{present!r}]: the per-azimuth fc pair needs "
            f"{prefix}_fc_h_hz and {prefix}_fc_v_hz together (1/fc(phi) = "
            "cos^2 phi / fc_h + sin^2 phi / fc_v)")
    fc = float(knobs.get(f"{prefix}_fc_hz", ROWS_LECLEACH_KNOB_DEFAULTS["fc_hz"]))
    T = float(knobs.get(f"{prefix}_T", ROWS_LECLEACH_KNOB_DEFAULTS["T"]))
    stop = float(knobs.get(f"{prefix}_stop_deg", ROWS_LECLEACH_KNOB_DEFAULTS["stop_deg"]))
    for name, value in (("fc_hz", fc), ("T", T), ("stop_deg", stop)):
        if not math.isfinite(value):
            raise registry.GeneratorError(f"lecleach rows: {name} must be finite, got {value!r}")
    if fc <= 0.0:
        raise registry.GeneratorError(f"lecleach rows: fc_hz must be > 0, got {fc}")
    if T < 0.0:
        raise registry.GeneratorError(f"lecleach rows: T must be >= 0, got {T}")
    lo, hi = ROWS_LECLEACH_STOP_RANGE
    if not lo <= stop <= hi:
        raise registry.GeneratorError(
            f"lecleach rows: stop_deg must be in [{lo:g}, {hi:g}], got {stop}")
    fc_h_hz = float(knobs[f"{prefix}_fc_h_hz"]) if has_h else None
    fc_v_hz = float(knobs[f"{prefix}_fc_v_hz"]) if has_v else None
    if fc_h_hz is not None and (fc_h_hz <= 0.0 or fc_v_hz is None or fc_v_hz <= 0.0):
        raise registry.GeneratorError(
            f"lecleach rows: fc_h_hz / fc_v_hz must be > 0, got {fc_h_hz} / {fc_v_hz}")
    return {"fc_hz": fc, "T": T, "stop_deg": stop,
            "fc_h_hz": fc_h_hz, "fc_v_hz": fc_v_hz,
            "r_lip_mm": _rows_lip_mm(knobs, prefix)}


#: A cos(phi) (odd cosine) term breaks the left-right mirror; the rows model is only
#: quarter/half, so it is refused rather than silently mis-meshed (lib-2 section 2.5).
ROWS_LR_BREAKING_KNOBS = (
    "stop_a1_deg", "stop_a3_deg", "stop_b2_deg", "stop_b4_deg",
    "bend_cos1_mm", "bend_a1_mm")


def _rows_mod_half(knobs: dict, prefix: str) -> bool:
    """True when the scalar ``lecleach_mod`` b-term/bend keys are PRESENT.

    Presence, not value: an explicit ``g_stop_b1_deg: 0`` is a legal half-model request
    (geometry identical to the quarter, but quadrants "14"), which is what makes the
    "quarter == half when all b-terms are 0" regression checkable.  Absent b keys (the
    normal quarter recipe) keep today's quarter model.  This presence rule belongs ONLY
    to the scalar ``lecleach_mod`` kind; the salmon/lecleach list contract selects half
    explicitly with ``span: half``.
    """
    keys = (f"{prefix}_stop_b1_deg", f"{prefix}_stop_b3_deg", f"{prefix}_bend_b1_mm")
    return any(k in knobs for k in keys)


def _rows_lecleach_mod_knobs(knobs: dict, prefix: str = "g") -> dict:
    """Validated ``rows: {type: lecleach_mod}`` harmonic-law knobs (lib-2 section 2.5).

    ``stop(phi) = stop0 + a2 cos(2 phi) + a4 cos(4 phi) + b1 sin(phi) + b3 sin(3 phi)``
    with phi measured FROM THE HORIZONTAL (+x) axis (pinned).  The cos-2k terms are
    quarter-safe; the sin-(2k+1) terms and the axial bend force the half model.  An
    odd-cosine (cos phi / cos 3 phi) or even-sine (sin 2 phi / sin 4 phi) knob would
    break the left-right mirror and is refused with a clear message.
    """
    breaking = [f"{prefix}_{name}" for name in ROWS_LR_BREAKING_KNOBS
                if f"{prefix}_{name}" in knobs]
    if breaking:
        raise registry.GeneratorError(
            f"lecleach_mod: {breaking} breaks the left-right mirror (x -> -x is "
            "phi -> pi - phi; only even cosines and odd sines are invariant). The GRID "
            "rows route ships quarter/half models only, so an LR-breaking term is refused "
            "instead of being silently mis-meshed (lib-2 section 2.5)")
    allowed = {f"{prefix}_fc_hz", f"{prefix}_fc_v_hz", f"{prefix}_T",
               f"{prefix}_stop0_deg", f"{prefix}_stop_a2_deg", f"{prefix}_stop_a4_deg",
               f"{prefix}_stop_b1_deg", f"{prefix}_stop_b3_deg",
               f"{prefix}_bend_b1_mm", f"{prefix}_r_lip_mm"}
    foreign = sorted(str(k) for k in knobs
                     if str(k).startswith(f"{prefix}_") and k not in allowed)
    if foreign:
        raise registry.GeneratorError(
            f"lecleach_mod rows: unknown knob(s) {foreign}; accepted: "
            "fc_hz, fc_v_hz, T, stop0_deg, stop_a2_deg, stop_a4_deg, stop_b1_deg, "
            "stop_b3_deg, bend_b1_mm, r_lip_mm")
    out = {}
    for name, default in (("fc_hz", ROWS_MOD_KNOB_DEFAULTS["fc_hz"]),
                          ("T", ROWS_MOD_KNOB_DEFAULTS["T"]),
                          ("stop0_deg", ROWS_MOD_KNOB_DEFAULTS["stop0_deg"]),
                          ("stop_a2_deg", ROWS_MOD_KNOB_DEFAULTS["stop_a2_deg"]),
                          ("stop_a4_deg", ROWS_MOD_KNOB_DEFAULTS["stop_a4_deg"]),
                          ("stop_b1_deg", ROWS_MOD_KNOB_DEFAULTS["stop_b1_deg"]),
                          ("stop_b3_deg", ROWS_MOD_KNOB_DEFAULTS["stop_b3_deg"]),
                          ("bend_b1_mm", ROWS_MOD_KNOB_DEFAULTS["bend_b1_mm"])):
        out[name] = float(knobs.get(f"{prefix}_{name}", default))
    fc_v_key = f"{prefix}_fc_v_hz"
    out["fc_v_hz"] = float(knobs[fc_v_key]) if fc_v_key in knobs else None
    for name, value in out.items():
        if value is None:
            continue
        if not math.isfinite(value):
            raise registry.GeneratorError(
                f"lecleach_mod rows: {name} must be finite, got {value!r}")
    if out["fc_hz"] <= 0.0 or (out["fc_v_hz"] is not None and out["fc_v_hz"] <= 0.0):
        raise registry.GeneratorError(
            f"lecleach_mod rows: fc_hz / fc_v_hz must be > 0, got "
            f"{out['fc_hz']} / {out['fc_v_hz']}")
    if out["T"] < 0.0:
        raise registry.GeneratorError(f"lecleach_mod rows: T must be >= 0, got {out['T']}")
    lo, hi = ROWS_LECLEACH_STOP_RANGE
    if not lo <= out["stop0_deg"] <= hi:
        raise registry.GeneratorError(
            f"lecleach_mod rows: stop0_deg must be in [{lo:g}, {hi:g}], got "
            f"{out['stop0_deg']}")
    if abs(out["bend_b1_mm"]) > ROWS_MAX_BEND_MM:
        raise registry.GeneratorError(
            f"lecleach_mod rows: bend_b1_mm must be in "
            f"[-{ROWS_MAX_BEND_MM:g}, {ROWS_MAX_BEND_MM:g}], got {out['bend_b1_mm']}")
    out["r_lip_mm"] = _rows_lip_mm(knobs, prefix)
    out["half_model"] = _rows_mod_half(knobs, prefix)
    return out


def _rows_lecleach_ar_knobs(knobs: dict, prefix: str = "g") -> dict:
    """Validated ``rows: {type: lecleach_ar}`` knobs (lib-2 section 2.2 reconstruction).

    ``AR(l) = 1 + (AR_m - 1) (l/L0)^p`` with the throat ratio pinned at 1.  The AR
    stretch is doubly even in phi (the horizontal and vertical semi-axes swap under
    both mirrors), so this kind is quarter-only by construction.
    """
    allowed = {f"{prefix}_fc_hz", f"{prefix}_T", f"{prefix}_stop_deg",
               f"{prefix}_AR_m", f"{prefix}_p", f"{prefix}_r_lip_mm"}
    foreign = sorted(str(k) for k in knobs
                     if str(k).startswith(f"{prefix}_") and k not in allowed)
    if foreign:
        raise registry.GeneratorError(
            f"lecleach_ar rows accept only {prefix}_fc_hz / {prefix}_T / "
            f"{prefix}_stop_deg / {prefix}_AR_m / {prefix}_p / {prefix}_r_lip_mm; "
            f"got foreign knob(s) {foreign}")
    out = {}
    for name, default in (("fc_hz", ROWS_AR_KNOB_DEFAULTS["fc_hz"]),
                          ("T", ROWS_AR_KNOB_DEFAULTS["T"]),
                          ("stop_deg", ROWS_AR_KNOB_DEFAULTS["stop_deg"]),
                          ("AR_m", ROWS_AR_KNOB_DEFAULTS["AR_m"]),
                          ("p", ROWS_AR_KNOB_DEFAULTS["p"])):
        out[name] = float(knobs.get(f"{prefix}_{name}", default))
    for name, value in out.items():
        if not math.isfinite(value):
            raise registry.GeneratorError(
                f"lecleach_ar rows: {name} must be finite, got {value!r}")
    if out["fc_hz"] <= 0.0:
        raise registry.GeneratorError(f"lecleach_ar rows: fc_hz must be > 0, got {out['fc_hz']}")
    if out["T"] < 0.0:
        raise registry.GeneratorError(f"lecleach_ar rows: T must be >= 0, got {out['T']}")
    if out["AR_m"] <= 0.0:
        raise registry.GeneratorError(f"lecleach_ar rows: AR_m must be > 0, got {out['AR_m']}")
    if out["p"] <= 0.0:
        raise registry.GeneratorError(f"lecleach_ar rows: p must be > 0, got {out['p']}")
    lo, hi = ROWS_LECLEACH_STOP_RANGE
    if not lo <= out["stop_deg"] <= hi:
        raise registry.GeneratorError(
            f"lecleach_ar rows: stop_deg must be in [{lo:g}, {hi:g}], got {out['stop_deg']}")
    out["AR_t"] = ROWS_AR_THROAT_RATIO
    out["r_lip_mm"] = _rows_lip_mm(knobs, prefix)
    return out


def rows_harmonic_law(phi, stop0_deg: float, a2_deg: float = 0.0, a4_deg: float = 0.0,
                      b1_deg: float = 0.0, b3_deg: float = 0.0):
    """``stop(phi)`` of the ``lecleach_mod`` law, phi in RADIANS from the HORIZONTAL.

    ``stop0 + a2 cos(2 phi) + a4 cos(4 phi) + b1 sin(phi) + b3 sin(3 phi)`` in degrees.
    ``cos(2k phi)`` is even under both mirrors; ``sin((2k+1) phi)`` is left-right
    symmetric but up/down antisymmetric (hence HALF-only).  Returns a float for scalar
    ``phi`` and an array otherwise.
    """
    p = np.asarray(phi, dtype=float)
    stop = (float(stop0_deg)
            + float(a2_deg) * np.cos(2.0 * p)
            + float(a4_deg) * np.cos(4.0 * p)
            + float(b1_deg) * np.sin(p)
            + float(b3_deg) * np.sin(3.0 * p))
    return float(stop) if np.ndim(phi) == 0 else stop


def rows_fc_law(phi, fc_h_hz: float, fc_v_hz: float | None):
    """T3 per-azimuth cutoff: ``1/fc(phi) = cos^2 phi / fc_h + sin^2 phi / fc_v``.

    The SAME law ``rows_per_azimuth`` already ships for the Salmon rows, but stated in
    the pinned phi-from-horizontal convention.  ``fc_v_hz is None`` means no H/V split
    (``fc(phi) == fc_h``), which keeps the lecleach_mod rows axisymmetric.
    """
    p = np.asarray(phi, dtype=float)
    if fc_v_hz is None:
        out = np.full_like(p, float(fc_h_hz), dtype=float)
    else:
        c, s = np.cos(p), np.sin(p)
        out = 1.0 / (c * c / float(fc_h_hz) + s * s / float(fc_v_hz))
    return float(out) if np.ndim(phi) == 0 else out


def lecleach_ar_profile(x, y, AR_m: float, p: float,
                        AR_t: float = ROWS_AR_THROAT_RATIO) -> tuple[np.ndarray, ...]:
    """Area-preserving AR stretch of a ``(x, y)`` meridian (lib-2 section 2.2 reconstruction).

    ``AR(l) = AR_t + (AR_m - AR_t) (l / L0)^p`` (``l`` = normalised arc fraction, so a
    uniform-``dl`` march uses ``i / (n - 1)``).  Returns ``(AR, y_h, y_v)`` with
    ``y_h = y sqrt(AR)`` (horizontal semi-axis, wide at the mouth) and
    ``y_v = y / sqrt(AR)`` (vertical).  ``y_h * y_v == y^2`` exactly, so the section
    area ``pi y_h y_v == pi y^2`` is preserved; ``x`` is shared (the march length is
    untouched).  ``AR_t`` is pinned at 1.0 by the caller (circular throat).
    """
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    if x.size != y.size or x.size < 2:
        raise registry.GeneratorError("lecleach_ar: need >= 2 matching x/y samples")
    AR_m = float(AR_m)
    p = float(p)
    AR_t = float(AR_t)
    if not (math.isfinite(AR_m) and math.isfinite(p) and math.isfinite(AR_t)):
        raise registry.GeneratorError("lecleach_ar: AR_m / p / AR_t must be finite")
    if AR_m <= 0.0 or AR_t <= 0.0 or p <= 0.0:
        raise registry.GeneratorError(
            f"lecleach_ar: AR_m / AR_t / p must be > 0, got {AR_m} / {AR_t} / {p}")
    l = _arc_length(x, y)
    L0 = float(l[-1])
    if not (math.isfinite(L0) and L0 > 0.0):
        raise registry.GeneratorError("lecleach_ar: zero-length meridian")
    s = l / L0
    AR = AR_t + (AR_m - AR_t) * np.power(s, p)
    y_h = y * np.sqrt(AR)
    y_v = y / np.sqrt(AR)
    return AR, y_h, y_v


_LIP_MODEL_NOTE = (
    "[inferred approximation, lib-2 section 2.3] torus of tube radius r_lip centred on "
    "the mouth rim; the row ends at the torus' outermost equator, so total width = "
    "width(wall) + 2 r_lip. Not a wall-tangent fillet (a wall-tangent torus at stop > 90 "
    "deg reaches ~2 r_lip beyond the rim); the junction is a small flare.")


def _append_lip_torus(x, y, r_lip: float, n_lip: int = 10):
    """Extend a row's lip END with the inferred torus lip of tube radius ``r_lip`` (mm).

    Construction implemented [inferred approximation, lib-2 section 2.3]: the tube is
    CENTRED ON THE MOUTH RIM (the lib-2 "torus centred on the mouth rim", whose outer
    diameter is ``2 (max y + r_lip)``), and the row is extended with the quarter arc

        x(t) = x_end + r (1 - cos t),   y(t) = y_end + r sin t,   t in [0, pi/2]

    which starts at the rim and ends exactly at the torus' outermost equator
    ``(x_end + r, y_end + r)``.  The endpoint survives equal-arc resampling bit-exactly,
    so the mouth's widest station is the analytic ``y_end + r_lip``: the lip adds
    ``2 r_lip`` to the total width (``r_lip`` per side).  This is deliberately NOT a
    wall-tangent fillet: a torus tangent to a wall that is already rolled past 90 deg
    reaches ~``2 r_lip`` beyond the rim (its centre sits on the outward normal).  The
    lib-2 datasheet cross-check uses the centred-on-rim convention, so this is the
    self-consistent approximation; the junction is a small flare, not a C1 fillet.
    ``r_lip <= 0`` returns the row untouched (byte-identical default).
    """
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    r = float(r_lip)
    if not (math.isfinite(r) and r > 0.0):
        return x, y
    x_end, y_end = float(x[-1]), float(y[-1])
    t = np.linspace(0.0, 0.5 * math.pi, max(2, int(n_lip)) + 1)[1:]
    x_lip = x_end + r * (1.0 - np.cos(t))
    y_lip = y_end + r * np.sin(t)
    return np.concatenate((x, x_lip)), np.concatenate((y, y_lip))


def x_shape_modulation(stop_deg, x_amp, x_fc, phi):
    """T5 modulation of the stop angle (and optionally fc) at azimuth ``phi`` (radians).

    ``stop(phi) = stop_deg * (1 + x_amp * cos 4 phi')`` with ``phi' = phi - 45 deg``, so
    the maxima sit on the quarter diagonals (plan 9b.2 T5 verbatim).  ``cos 4 phi'`` is
    even about both cardinal mirror planes, so the quarter model stays valid.
    SIGNED X (owner-approved v2, 2026-10-25): a negative ``x_amp`` flips the sign of the
    stop/width excursions - relative to the positive (literally-X, "corner-out") reading,
    the negative reading opens the CARDINAL planes instead ("corner-in"); the two signs
    sample the same knob family. The magnitude cap is unchanged.
    ``fc_scale = 1 - x_fc * cos 4 phi'`` is applied whenever ``x_amp != 0``; this makes
    ``x_amp = 0`` reproduce the plain elliptical rows EXACTLY (property P2) regardless
    of the ``x_fc`` seed.

    Returns ``(stop_deg_phi, fc_scale)``; numpy arrays for array input, floats for a
    scalar.
    """
    s = float(stop_deg)
    amp = float(x_amp)
    fcm = float(x_fc)
    if not math.isfinite(s) or s <= 0.0:
        raise registry.GeneratorError(f"stop_deg must be finite and > 0, got {stop_deg!r}")
    if not -ROWS_MAX_X_AMP <= amp <= ROWS_MAX_X_AMP:
        raise registry.GeneratorError(
            f"x_amp must be in [-{ROWS_MAX_X_AMP}, {ROWS_MAX_X_AMP}] (signed), got {x_amp!r}")
    if not 0.0 <= fcm <= ROWS_MAX_X_FC:
        raise registry.GeneratorError(f"x_fc must be in [0, {ROWS_MAX_X_FC}], got {x_fc!r}")
    arr = np.asarray(phi, dtype=float)
    cos4 = np.cos(4.0 * (arr - 0.25 * math.pi))
    stop = s * (1.0 + amp * cos4)
    scale = 1.0 - fcm * cos4 if amp != 0.0 else np.ones_like(cos4)
    if np.ndim(phi) == 0:
        return float(stop), float(scale)
    return stop, scale


def _xy_samples(samples) -> tuple[np.ndarray, np.ndarray]:
    """``(x, y)`` millimetres from a march tuple / dict / Meridian."""
    if hasattr(samples, "z_mm") and hasattr(samples, "r_mm"):
        x, y = samples.z_mm, samples.r_mm
    elif isinstance(samples, dict):
        for kx, ky in (("x_mm", "y_mm"), ("xs", "ys"), ("z_mm", "r_mm")):
            if kx in samples and ky in samples:
                x, y = samples[kx], samples[ky]
                break
        else:
            raise registry.GeneratorError(
                "row samples need x_mm/y_mm, xs/ys or z_mm/r_mm arrays")
    elif isinstance(samples, (tuple, list)) and len(samples) >= 2:
        x, y = samples[0], samples[1]
    else:
        raise registry.GeneratorError(
            "row samples must be a Meridian, a dict of x/y arrays, or an (x, y) pair")
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    if x.size != y.size or x.size < 2:
        raise registry.GeneratorError(
            f"row samples need >= 2 matching x/y values, got {x.size} / {y.size}")
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        raise registry.GeneratorError("row samples contain non-finite values")
    return x, y


def _arc_length(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    d = np.hypot(np.diff(x), np.diff(y))
    return np.concatenate(([0.0], np.cumsum(d)))


def _resample_arc(x, y, n_s: int) -> tuple[np.ndarray, np.ndarray, float]:
    """Resample ``(x, y)`` to ``n_s + 1`` equal normalized-arc stations; endpoints exact."""
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    n_s = int(n_s)
    if n_s < 1:
        raise registry.GeneratorError(f"n_s must be >= 1, got {n_s}")
    l = _arc_length(x, y)
    L0 = float(l[-1])
    if not (math.isfinite(L0) and L0 > 0.0):
        raise registry.GeneratorError("row has zero arc length; refuse instead of clamping")
    target = np.linspace(0.0, L0, n_s + 1)
    xr = np.interp(target, l, x)
    yr = np.interp(target, l, y)
    # P5: endpoints are the march's own endpoints, bit-exact (no interpolation round trip).
    xr[0], yr[0] = float(x[0]), float(y[0])
    xr[-1], yr[-1] = float(x[-1]), float(y[-1])
    return xr, yr, L0


def _truncate_arc(x, y, fraction: float) -> tuple[np.ndarray, np.ndarray]:
    """Trim a row to its first ``fraction`` of total arc length (x modulation helper)."""
    frac = float(fraction)
    if not (math.isfinite(frac) and 0.0 < frac <= 1.0):
        raise registry.GeneratorError(f"row arc fraction must be in (0, 1], got {fraction!r}")
    if frac >= 1.0:
        return np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    l = _arc_length(x, y)
    target = frac * float(l[-1])
    j = int(np.searchsorted(l, target, side="right")) - 1
    j = min(max(j, 0), len(l) - 2)
    t = (target - l[j]) / (l[j + 1] - l[j]) if l[j + 1] > l[j] else 0.0
    xe = float(x[j]) + t * (float(x[j + 1]) - float(x[j]))
    ye = float(y[j]) + t * (float(y[j + 1]) - float(y[j]))
    return (np.concatenate((np.asarray(x[: j + 1], dtype=float), [xe])),
            np.concatenate((np.asarray(y[: j + 1], dtype=float), [ye])))


def _cross_row_min_distance(grid: np.ndarray, min_station: int) -> float:
    """Report-only min distance between points of DIFFERENT rows (mm).

    Rows share the throat by construction, so the metric excludes the first
    ``min_station`` stations (10-25 % of the arc) where the fan necessarily converges.
    Its scope is stated in the meta: it is NOT a refusal criterion.
    """
    g = np.asarray(grid, dtype=float)
    if g.shape[0] < 2:
        return math.inf
    pts = g[:, min_station:, :].reshape(-1, 3)
    rows = np.repeat(np.arange(g.shape[0]), g.shape[1] - min_station)
    delta = pts[:, None, :] - pts[None, :, :]
    dist = np.linalg.norm(delta, axis=-1)
    cross = rows[:, None] != rows[None, :]
    if not np.any(cross):
        return math.inf
    return float(np.min(dist[cross]))


def _build_rows_grid(profiles_xy: list[tuple[np.ndarray, np.ndarray]], phis: np.ndarray,
                     n_s: int, meta: dict, *, resample: bool = True) -> tuple[np.ndarray, dict]:
    """Assemble ``P = (y cos phi, y sin phi, x)`` mm from per-azimuth ``(x, y)`` rows.

    Row span (TASK B1 / lib-2 C2): the phis decide the model.  A quarter spans
    ``[0, 90]`` (row 0 on the H plane ``y = 0``, last row on ``x = 0``; quadrants "1").
    A half spans ``[-90, +90]`` with both endpoint rows on ``x = 0`` (symmetry plane
    ``yz``; quadrants "14").  A half_xz spans ``[0, 180]`` with both endpoint rows on
    ``y = 0`` (symmetry plane ``xz``; quadrants "12"; the phi = 90 deg vertical row is
    pinned to ``x = 0``).  ``phi = 0`` is the horizontal axis in EVERY span (the phi
    origin is pinned, never inferred).  A FULL ring spans ``[0, 360)``
    (endpoint excluded; no mirror planes; quadrants "1234"; the mesher's native
    closed/full-ring mode).
    """
    n_phi = len(profiles_xy)
    if phis.size != n_phi:
        raise registry.GeneratorError(
            f"rows: {n_phi} profiles but {phis.size} azimuths")
    phis = np.asarray(phis, dtype=float).reshape(-1)
    half = bool(phis[0] < -1e-9)
    full = (not half) and bool(float(phis[-1]) > math.pi + 1e-9)
    half_xz = (not half) and (not full) and bool(
        abs(float(phis[-1]) - math.pi) <= 1e-9)
    if half:
        if n_phi % 2 == 0:
            raise registry.GeneratorError(
                "half-model rows need an ODD n_phi so the phi = 0 (horizontal) row and "
                f"both +/-90 deg endpoint rows exist; got n_phi={n_phi}")
        if abs(float(phis[0]) + 0.5 * math.pi) > 1e-9 \
                or abs(float(phis[-1]) - 0.5 * math.pi) > 1e-9:
            raise registry.GeneratorError(
                "half-model phi must span -90 .. +90 deg inclusive")
    elif half_xz:
        if n_phi % 2 == 0:
            raise registry.GeneratorError(
                "half_xz-model rows need an ODD n_phi so the phi = 0 / 180 deg endpoint "
                f"rows and the phi = 90 deg vertical row exist; got n_phi={n_phi}")
        if abs(float(phis[0])) > 1e-9 or abs(float(phis[-1]) - math.pi) > 1e-9:
            raise registry.GeneratorError(
                "half_xz-model phi must span 0 .. 180 deg inclusive")
    elif n_phi < 2:
        raise registry.GeneratorError("quarter rows need n_phi >= 2")
    grid = np.empty((n_phi, n_s + 1, 3), dtype=float)
    rows_meta = []
    bend = float(meta.get("bend_sin1_mm", 0.0))
    s_frac = np.linspace(0.0, 1.0, n_s + 1)
    w_mouth = 3.0 * s_frac ** 2 - 2.0 * s_frac ** 3      # same G9 smoothstep window
    for i, ((x, y), phi) in enumerate(zip(profiles_xy, phis)):
        if resample:
            xr, yr, L0 = _resample_arc(x, y, n_s)
        else:
            xr = np.asarray(x, dtype=float).reshape(-1)
            yr = np.asarray(y, dtype=float).reshape(-1)
            if xr.size != n_s + 1 or yr.size != n_s + 1:
                raise registry.GeneratorError(
                    f"pre-sampled row needs {n_s + 1} stations, got {xr.size} / {yr.size}")
            L0 = float(_arc_length(xr, yr)[-1])
        if bend != 0.0:
            xr = xr + bend * math.sin(float(phi)) * w_mouth
        grid[i, :, 0] = yr * math.cos(float(phi))
        grid[i, :, 1] = yr * math.sin(float(phi))
        grid[i, :, 2] = xr
        rows_meta.append({
            "phi_deg": float(np.degrees(phi)),
            "length_mm": float(L0),
            "mouth_x_mm": float(xr[-1]),
            "mouth_y_mm": float(yr[-1]),
            "x_min_mm": float(np.min(xr)),
            "x_max_mm": float(np.max(xr)),
            "y_max_mm": float(np.max(yr)),
        })
    # Exact mirror planes: float cos/sin noise removed on the symmetry-plane rows.
    if full:
        pass                       # closed full ring: no mirror-plane rows to clean
    elif half:
        grid[0, :, 0] = 0.0        # phi = -90 -> x = 0 (yz plane)
        grid[-1, :, 0] = 0.0       # phi = +90 -> x = 0
    elif half_xz:
        grid[0, :, 1] = 0.0        # phi = 0 -> y = 0 (xz plane)
        grid[-1, :, 1] = 0.0       # phi = 180 -> y = 0
        i_v = int(np.argmin(np.abs(phis - 0.5 * math.pi)))
        grid[i_v, :, 0] = 0.0      # phi = 90 -> x = 0 (V plane)
    else:
        grid[0, :, 1] = 0.0        # phi = 0 -> y = 0 (H plane)
        grid[-1, :, 0] = 0.0       # phi = 90 -> x = 0 (V plane)
    t = float(meta.get("wall_thickness_mm", 3.0))
    min_station = max(1, n_s // 4)
    meta = dict(meta)
    meta.update({
        "n_phi": int(n_phi),
        "n_phi_quarter": int((n_phi + 1) // 2) if (half or half_xz) else int(n_phi),
        "n_s": int(n_s),
        "phi_span_deg": 360.0 if full else (180.0 if (half or half_xz) else 90.0),
        "phi_origin_deg": 0.0,
        "quarter": not (half or half_xz or full),
        "half_model": half,
        "row_span": ("full" if full else ("half" if half else
                                          ("half_xz" if half_xz else "quarter"))),
        "span": ("full" if full else ("half" if half else
                                      ("half_xz" if half_xz else "quarter"))),
        "symmetry_plane": (None if full else
                           ("yz" if half else ("xz" if half_xz else "yz+xz"))),
        "quadrants": ("1234" if full else
                      ("14" if half else ("12" if half_xz else "1"))),
        "rows": list(rows_meta),
        "min_self_approach_mm": float(
            _sheet_min_nonadjacent_gap(grid, _self_approach_limit(meta))),
        "min_self_approach_scope": (
            "inner sheet only, per row; grid_outer_points also guards the inner+outer shell"),
        "min_self_approach_limit_mm": float(_self_approach_limit(meta)),
        "min_cross_row_distance_mm": float(_cross_row_min_distance(grid, min_station)),
        "min_cross_row_distance_scope": (
            f"REPORT ONLY: different-row stations at or beyond station {min_station} "
            f"(~{100.0 * min_station / max(n_s, 1):.0f}% arc); rows share the throat by "
            "construction, so the fan near the throat is excluded"),
        "min_cross_row_distance_limit_mm": float(2.0 * t + SELF_APPROACH_MARGIN_MM),
    })
    return grid, meta


def rows_axisym(march_or_meridian_samples, n_phi: int, x_modulation=None, *,
                n_s: int = 32, phi=None,
                source_auto_angle_deg: float | None = None) -> tuple[np.ndarray, dict]:
    """Axisymmetric rows from ONE ``(x, y)`` sample set, resampled by normalized arc length.

    ``march_or_meridian_samples`` is a :class:`profiles.Meridian`, a dict with
    ``x_mm``/``y_mm`` (or ``xs``/``ys``), or an ``(x, y)`` pair.  Every azimuth gets the
    SAME meridian, resampled to ``n_s + 1`` stations at ``l/L0 = k/n_s`` (property P5:
    endpoints exact).  ``x_modulation`` (optional) trims each row to a fraction of the
    base march's arc length: a callable ``phi_rad -> fraction`` or one fraction per
    quarter row.  Points are ``P = (y cos phi, y sin phi, x)``, quarter ``phi`` in
    ``[0, 90]`` with both endpoint rows included (mirror-safe).
    """
    x, y = _xy_samples(march_or_meridian_samples)
    n_phi = _spec_int({"n_phi": n_phi}, "n_phi", MIN_PHI_QUARTER, MIN_PHI_QUARTER)
    n_s = _spec_int({"n_s": n_s}, "n_s", 32, 8)
    phis = (np.linspace(0.0, 0.5 * math.pi, n_phi) if phi is None
            else np.asarray(phi, dtype=float).reshape(-1))
    if phis.size != n_phi or abs(float(phis[0])) > 1e-12 \
            or abs(float(phis[-1]) - 0.5 * math.pi) > 1e-9:
        raise registry.GeneratorError(
            "phi must have n_phi rows from 0 to 90 deg inclusive")
    if x_modulation is None:
        fractions = np.ones(n_phi)
    elif callable(x_modulation):
        fractions = np.asarray([float(x_modulation(float(p))) for p in phis],  # type: ignore[operator]
                               dtype=float)
    else:
        fractions = np.asarray(x_modulation, dtype=float).reshape(-1)
    if fractions.size != n_phi:
        raise registry.GeneratorError(
            f"x_modulation needs {n_phi} fractions, got {fractions.size}")
    profiles_xy = [_truncate_arc(x, y, float(f)) for f in fractions]
    angle = (float(source_auto_angle_deg) if source_auto_angle_deg is not None
             else (float(getattr(march_or_meridian_samples, "theta_deg", [0.0])[0])
                   if hasattr(march_or_meridian_samples, "theta_deg") else 0.0))
    meta = {
        "family": "grid",
        "rows_type": "axisym",
        "hypothesis_label": ROWS_HYPOTHESIS_LABEL,
        "source_auto_angle_deg": float(angle),
        "x_modulation": ("none" if x_modulation is None
                         else [float(f) for f in fractions]),
    }
    return _build_rows_grid(profiles_xy, phis, n_s, meta)


def rows_task_harmonics(knobs: dict, prefix: str = "g", *, half: bool) -> dict:
    """Validated fix-6 harmonic stop law: ``g_stop_cos2k`` / ``g_stop_sin2k1`` / bend.

    ``stop(phi) = stop0 (1 + sum_i a_i cos(2(i+1) phi) + sum_i b_i sin((2i+1) phi))``
    with phi from the HORIZONTAL axis.  Coefficients are dimensionless fractions of the
    base stop (``[0.25]`` = +/-25 %).  The even cosines are quarter-safe; a nonzero odd
    sine or the bend ``delta-x = bend sin(phi) w(l)`` is left-right symmetric but up/down
    antisymmetric and REQUIRES ``span: half`` (otherwise ``GeneratorError``).  Any other
    ``g_stop_cos*`` / ``g_stop_sin*`` key (e.g. ``g_stop_cos1k`` = a cos(phi) term) breaks
    the left-right mirror and is refused with a mirror message.
    """
    cos_key = f"{prefix}_stop_cos2k"
    sin_key = f"{prefix}_stop_sin2k1"
    bend_key = f"{prefix}_bend_sin1_mm"
    for key in knobs:
        k = str(key)
        if not k.startswith(f"{prefix}_stop_"):
            continue
        if k in (cos_key, sin_key):
            continue
        if "cos" in k or "sin" in k:
            raise registry.GeneratorError(
                f"{k!r} is not in the left-right-mirror basis: cos(phi) (and other odd "
                "cosines) break the mirror, and even sines break it too. Use "
                f"{cos_key} (even cosines) or {sin_key} (odd sines). (lib-2 C2)")
    cos2k = list(knobs.get(cos_key, []))
    sin2k1 = list(knobs.get(sin_key, []))
    for name, terms in ((cos_key, cos2k), (sin_key, sin2k1)):
        if len(terms) > MAX_TASK_STOP_HARMONIC_TERMS:
            raise registry.GeneratorError(
                f"{name} accepts at most {MAX_TASK_STOP_HARMONIC_TERMS} terms, got {len(terms)}")
        for term in terms:
            if not math.isfinite(float(term)) or abs(float(term)) > 1.0:
                raise registry.GeneratorError(
                    f"{name} terms must be finite fractions in [-1, 1], got {term!r}")
    bend = float(knobs.get(bend_key, 0.0))
    if not math.isfinite(bend) or abs(bend) > ROWS_MAX_BEND_MM:
        raise registry.GeneratorError(
            f"{bend_key} must be finite and in [-{ROWS_MAX_BEND_MM:g}, "
            f"{ROWS_MAX_BEND_MM:g}] mm, got {bend}")
    if not half and any(abs(float(v)) > 0.0 for v in sin2k1):
        raise registry.GeneratorError(
            f"{sin_key} nonzero terms are left-right symmetric but up/down antisymmetric: "
            "they require span: half (quadrants '14'). Remove the term or set span: half.")
    if not half and bend != 0.0:
        raise registry.GeneratorError(
            f"{bend_key} != 0 shifts the mouth plane by bend*sin(phi) (up/down asymmetric): "
            "it requires span: half (quadrants '14'). Remove the bend or set span: half.")
    active = any(abs(float(v)) > 0.0 for v in cos2k) \
        or any(abs(float(v)) > 0.0 for v in sin2k1) or bend != 0.0
    return {"stop_cos2k": [float(v) for v in cos2k],
            "stop_sin2k1": [float(v) for v in sin2k1],
            "bend_sin1_mm": float(bend), "active": active}


def rows_stop_multiplier(phi, cos2k, sin2k1):
    """``1 + sum a cos(2k phi) + sum b sin((2k+1) phi)``; phi from horizontal (radians)."""
    p = np.asarray(phi, dtype=float)
    mult = np.ones_like(p, dtype=float)
    for i, a in enumerate(cos2k):
        mult = mult + float(a) * np.cos(2.0 * (i + 1) * p)
    for i, b in enumerate(sin2k1):
        mult = mult + float(b) * np.sin((2.0 * i + 1.0) * p)
    return float(mult) if np.ndim(phi) == 0 else mult


def rows_task_stop(stop0_deg: float, harm: dict, phi, *, lo: float, hi: float) -> float:
    """``stop0 * multiplier(phi)`` validated into ``[lo, hi]`` degrees (row stop)."""
    stop = float(stop0_deg) * float(rows_stop_multiplier(
        phi, harm["stop_cos2k"], harm["stop_sin2k1"]))
    if not (math.isfinite(stop) and lo <= stop <= hi):
        raise registry.GeneratorError(
            f"rows stop {stop:.3f} deg at phi {np.degrees(phi):.2f} deg is outside "
            f"[{lo:g}, {hi:g}] (stop0/harmonic combination)")
    return stop


def _rows_iwata_ar_knobs(knobs: dict, prefix: str = "g") -> dict:
    """Validated ``rows: {type: iwata_ar}`` knobs (our reconstruction, lib-2 2.2)."""
    allowed = {f"{prefix}_fc_hz", f"{prefix}_T", f"{prefix}_stop_deg",
               f"{prefix}_ar_m", f"{prefix}_ar_p"}
    foreign = sorted(str(k) for k in knobs
                     if str(k).startswith(f"{prefix}_") and k not in allowed)
    if foreign:
        raise registry.GeneratorError(
            f"iwata_ar rows accept only {prefix}_fc_hz / {prefix}_T / {prefix}_stop_deg / "
            f"{prefix}_ar_m / {prefix}_ar_p; got foreign knob(s) {foreign}")
    out = {}
    for name, default in (("fc_hz", ROWS_IWATA_KNOB_DEFAULTS["fc_hz"]),
                          ("T", ROWS_IWATA_KNOB_DEFAULTS["T"]),
                          ("stop_deg", ROWS_IWATA_KNOB_DEFAULTS["stop_deg"]),
                          ("ar_m", ROWS_IWATA_KNOB_DEFAULTS["ar_m"]),
                          ("ar_p", ROWS_IWATA_KNOB_DEFAULTS["ar_p"])):
        out[name] = float(knobs.get(f"{prefix}_{name}", default))
    for name, value in out.items():
        if not math.isfinite(value):
            raise registry.GeneratorError(f"iwata_ar rows: {name} must be finite, got {value!r}")
    if out["fc_hz"] <= 0.0:
        raise registry.GeneratorError(f"iwata_ar rows: fc_hz must be > 0, got {out['fc_hz']}")
    if out["T"] < 0.0:
        raise registry.GeneratorError(f"iwata_ar rows: T must be >= 0, got {out['T']}")
    if not 0.0 < out["ar_m"] <= 4.0:
        raise registry.GeneratorError(f"iwata_ar rows: ar_m must be in (0, 4], got {out['ar_m']}")
    if not 0.0 < out["ar_p"] <= 8.0:
        raise registry.GeneratorError(f"iwata_ar rows: ar_p must be in (0, 8], got {out['ar_p']}")
    lo, hi = ROWS_LECLEACH_STOP_RANGE
    if not lo <= out["stop_deg"] <= hi:
        raise registry.GeneratorError(
            f"iwata_ar rows: stop_deg must be in [{lo:g}, {hi:g}], got {out['stop_deg']}")
    return out


#: osse_rollback (owner-directed hybrid, 2026-10-28): a constant-directivity OS/OSSE throat wall per
#: azimuth, the even-lobe flute ripple, and the tangent-continuous curled lip. Coverage half-angle
#: per azimuth a(phi) = a_h cos^2 phi + a_v sin^2 phi (mirror-safe); the lip wrap may follow the
#: flutes, wrap(phi) = wrap_deg (1 + wrap_cos_amp cos(N phi)), for a ruffled curled margin.
ROWS_OSSE_ROLL_KNOB_DEFAULTS = {"a_h_deg": 45.0, "a_v_deg": 45.0, "k": 1.0, "L_mm": 120.0,
                                "s": 0.0, "n": 4.0, "q": 0.996, "r_lip_mm": 30.0,
                                "wrap_deg": 120.0, "wrap_cos_amp": 0.0,
                                "sf_m": 0.0, "sf_n1": 2.0, "sf_n2": 2.0, "sf_ab": 1.0,
                                "sf_amt": 0.0, "sf_start": 0.0,
                                "a_fold": 2.0, "a_union": 0.0, "union_blend_deg": 0.0}
#: Angle-law options (owner 2026-10-28, four-petal shapes on the CD throat): a(phi) = a_h cos^2(ang) + a_v sin^2(ang)
#: with ang = phi (a_fold 2), 2 phi (a_fold 4: a_h on both axes, a_v on the diagonals) or, with a_union 1, the
#: union with the 90 deg copy: ang = 45 deg + |psi - 45 deg| (axes take a_v, the diagonal joins the mid law). A
#: union_blend_deg > 0 replaces |x| by a smooth |x| so the diagonal join is a rounded hump, not a crease.
ROWS_OSSE_ROLL_MAX_BLEND_DEG = 30.0
#: Superformula mouth morph (owner 2026-10-28): r *= 1 + sf_amt * w(s) * (sf(phi) / mean(sf) - 1) with
#: sf(phi) = (|cos(m phi/4)|^n2 + |sin(m phi/4) / ab|^n2)^(-1/n1) (Gielis; n2 = n3, a = 1). Any EVEN m keeps
#: both mirror planes when ab = 1; ab != 1 (a stretched mouth) needs m a multiple of 4.
ROWS_OSSE_ROLL_SF_M_RANGE = (2, 16)
ROWS_OSSE_ROLL_MAX_SF_AMT = 1.5
ROWS_OSSE_ROLL_A_RANGE = (5.0, 85.0)
ROWS_OSSE_ROLL_MAX_WRAP_DEG = 200.0
ROWS_OSSE_ROLL_MAX_WRAP_COS_AMP = 0.9
ROWS_OSSE_ROLL_SAMPLES = 400
OSSE_ROLL_LABEL = (
    "LABELED HYPOTHESIS-SHAPE EXPERIMENT (owner-directed hybrid 2026-10-28): per-azimuth OS/OSSE "
    "wall from Magnus's profile_points formula (the constant-directivity throat), the even-lobe "
    "flute ripple, and the [inferred] tangent-continuous curled lip. Not a published "
    "construction; no published name is used.")


def _rows_osse_rollback_knobs(knobs: dict, prefix: str = "g") -> dict:
    """Validated ``rows: {type: osse_rollback}`` knobs (OS wall + flutes + curled lip)."""
    names = tuple(ROWS_OSSE_ROLL_KNOB_DEFAULTS)
    allowed = ({f"{prefix}_{n}" for n in names}
               | {f"{prefix}_ripple_lobes", f"{prefix}_ripple_amp_mm", f"{prefix}_ripple_start"})
    foreign = sorted(str(k) for k in knobs
                     if str(k).startswith(f"{prefix}_") and k not in allowed)
    if foreign:
        raise registry.GeneratorError(
            f"osse_rollback rows accept {sorted(allowed)}; got foreign knob(s) {foreign}")
    out = {n: float(knobs.get(f"{prefix}_{n}", d)) for n, d in ROWS_OSSE_ROLL_KNOB_DEFAULTS.items()}
    for n, v in out.items():
        if not math.isfinite(v):
            raise registry.GeneratorError(f"osse_rollback rows: {n} must be finite, got {v!r}")
    lo, hi = ROWS_OSSE_ROLL_A_RANGE
    for n in ("a_h_deg", "a_v_deg"):
        if not lo <= out[n] <= hi:
            raise registry.GeneratorError(
                f"osse_rollback rows: {n} must be in [{lo:g}, {hi:g}] deg, got {out[n]}")
    if out["k"] <= 0.0 or out["n"] <= 0.0 or out["s"] < 0.0 or not 0.0 < out["q"] <= 1.0:
        raise registry.GeneratorError(
            "osse_rollback rows: need k > 0, n > 0, s >= 0 and 0 < q <= 1, got "
            f"k={out['k']} n={out['n']} s={out['s']} q={out['q']}")
    if not 10.0 <= out["L_mm"] <= 1000.0:
        raise registry.GeneratorError(
            f"osse_rollback rows: L_mm must be in [10, 1000], got {out['L_mm']}")
    out["r_lip_mm"] = _rows_lip_mm(knobs, prefix)
    if not 0.0 <= out["wrap_deg"] <= ROWS_OSSE_ROLL_MAX_WRAP_DEG:
        raise registry.GeneratorError(
            f"osse_rollback rows: wrap_deg must be in [0, {ROWS_OSSE_ROLL_MAX_WRAP_DEG:g}], "
            f"got {out['wrap_deg']}")
    if not 0.0 <= out["wrap_cos_amp"] <= ROWS_OSSE_ROLL_MAX_WRAP_COS_AMP:
        raise registry.GeneratorError(
            "osse_rollback rows: wrap_cos_amp must be in "
            f"[0, {ROWS_OSSE_ROLL_MAX_WRAP_COS_AMP:g}], got {out['wrap_cos_amp']}")
    m = out["sf_m"]
    if m != 0.0:
        lo_m, hi_m = ROWS_OSSE_ROLL_SF_M_RANGE
        if m != int(m) or int(m) % 2 or not lo_m <= m <= hi_m:
            raise registry.GeneratorError(
                f"osse_rollback rows: sf_m must be an EVEN integer in [{lo_m}, {hi_m}] (or 0 = off), "
                f"got {m}")
        if out["sf_n1"] <= 0.0 or out["sf_n2"] <= 0.0 or out["sf_ab"] <= 0.0:
            raise registry.GeneratorError(
                "osse_rollback rows: sf_n1, sf_n2 and sf_ab must be > 0")
        if out["sf_ab"] != 1.0 and int(m) % 4:
            raise registry.GeneratorError(
                "osse_rollback rows: sf_ab != 1 keeps the mirror planes only when sf_m is a "
                f"multiple of 4, got sf_m {int(m)}")
        if not 0.0 <= out["sf_amt"] <= ROWS_OSSE_ROLL_MAX_SF_AMT or not 0.0 <= out["sf_start"] < 1.0:
            raise registry.GeneratorError(
                f"osse_rollback rows: sf_amt must be in [0, {ROWS_OSSE_ROLL_MAX_SF_AMT:g}] and "
                f"sf_start in [0, 1), got {out['sf_amt']} / {out['sf_start']}")
    elif out["sf_amt"] != 0.0:
        raise registry.GeneratorError("osse_rollback rows: sf_amt > 0 needs sf_m set")
    if out["a_fold"] not in (2.0, 4.0) or out["a_union"] not in (0.0, 1.0):
        raise registry.GeneratorError(
            f"osse_rollback rows: a_fold must be 2 or 4 and a_union 0 or 1, got {out['a_fold']} / {out['a_union']}")
    if out["a_union"] and out["a_fold"] != 2.0:
        raise registry.GeneratorError("osse_rollback rows: a_union and a_fold 4 are alternatives; use one")
    if not 0.0 <= out["union_blend_deg"] <= ROWS_OSSE_ROLL_MAX_BLEND_DEG:
        raise registry.GeneratorError(
            f"osse_rollback rows: union_blend_deg must be in [0, {ROWS_OSSE_ROLL_MAX_BLEND_DEG:g}], "
            f"got {out['union_blend_deg']}")
    out.update(_rows_ripple_knobs(knobs, prefix))
    if out["wrap_cos_amp"] > 0.0 and not out["ripple_lobes"]:
        raise registry.GeneratorError(
            "osse_rollback rows: wrap_cos_amp follows the flute count; set ripple_lobes")
    return out


def _rows_osse_rollback_marches(ok: dict, phis, r0: float, a0: float) -> list[dict]:
    """One OS/OSSE wall per azimuth, flutes in the ripple window, then the curled lip."""
    from hornlab_mesher.profile_formulas import profile_points
    out = []
    lobes = int(ok["ripple_lobes"])
    sf_m = int(ok["sf_m"])

    def superformula(ph):
        q = np.asarray(ph, dtype=float) * sf_m / 4.0
        s_term = (np.abs(np.cos(q)) ** ok["sf_n2"]
                  + np.abs(np.sin(q) / ok["sf_ab"]) ** ok["sf_n2"])
        return s_term ** (-1.0 / ok["sf_n1"])

    sf_mean = (float(np.mean(superformula(np.linspace(0.0, 2.0 * math.pi, 4096, endpoint=False))))
               if sf_m else 1.0)
    for phi in phis:
        ang = float(phi) * (ok["a_fold"] / 2.0)
        if ok["a_union"]:
            psi = abs(math.atan2(math.sin(float(phi)), math.cos(float(phi))))
            psi = min(psi, math.pi - psi)                      # fold into [0, 90 deg]
            x = psi - 0.25 * math.pi
            k = math.radians(ok["union_blend_deg"])
            if k > 0.0:                                        # smooth |x|, exact at the axes
                ang = 0.25 * math.pi + math.sqrt(x * x + k * k) * (0.25 * math.pi) / math.hypot(0.25 * math.pi, k)
            else:
                ang = 0.25 * math.pi + abs(x)
        c2, s2 = math.cos(ang) ** 2, math.sin(ang) ** 2
        a_phi = ok["a_h_deg"] * c2 + ok["a_v_deg"] * s2
        prm = {"type": "OSSE", "r0": r0, "a0": a0, "L": ok["L_mm"], "a": a_phi, "k": ok["k"],
               "s": ok["s"], "n": ok["n"], "q": ok["q"]}
        try:
            pts = np.asarray(profile_points(prm, ROWS_OSSE_ROLL_SAMPLES, float(phi)), dtype=float)
        except Exception as exc:  # noqa: BLE001 - an illegal knob combination is a refusal
            raise registry.GeneratorError(f"osse_rollback: OSSE wall failed: {exc}") from exc
        xs, ys = pts[:, 0] - pts[0, 0], pts[:, 1]
        if (not np.all(np.isfinite(pts)) or not np.all(np.diff(xs) > 0.0)
                or not np.all(ys > 0.0)):
            raise registry.GeneratorError(
                f"osse_rollback: the OSSE wall is not a single-valued r(z) at phi "
                f"{np.degrees(phi):.1f} deg for these knobs")
        if sf_m and ok["sf_amt"] > 0.0:
            l_arc = _arc_length(xs, ys)
            w_sf = _rows_eps_window(l_arc / float(l_arc[-1]), ok["sf_start"])
            ys = ys * (1.0 + ok["sf_amt"] * w_sf * (float(superformula(float(phi))) / sf_mean - 1.0))
            if not np.all(ys > 0.0):
                raise registry.GeneratorError(
                    "osse_rollback: the superformula morph pinches the wall to zero radius")
        if lobes:
            l_arc = _arc_length(xs, ys)
            w = _rows_eps_window(l_arc / float(l_arc[-1]), ok["ripple_start"])
            ys = ys * (1.0 + (ok["ripple_amp_mm"] / max(float(np.max(ys)), 1e-9))
                       * w * np.cos(lobes * float(phi)))
        end_deg = math.degrees(math.atan2(float(ys[-1] - ys[-2]), float(xs[-1] - xs[-2])))
        wrap = ok["wrap_deg"] * ((1.0 + ok["wrap_cos_amp"] * math.cos(lobes * float(phi)))
                                 if lobes else 1.0)
        xs, ys, lip = append_tangent_lip(xs, ys, ok["r_lip_mm"], end_deg, wrap_deg=wrap)
        stop = end_deg + (wrap if ok["r_lip_mm"] > 0.0 else 0.0)
        out.append({"phi": float(phi), "phi_deg": float(np.degrees(phi)), "a_deg": float(a_phi),
                    "stop_deg": float(stop), "x": xs, "y": ys,
                    "march": {"stop_deg": float(stop), "wall_end_deg": float(end_deg)},
                    "lip": lip})
    return out


def _rows_toroidal_knobs(knobs: dict, prefix: str = "g") -> dict:
    """Validated ``rows: {type: toroidal_rollback}`` knobs (T1 + tangent lip, inferred)."""
    allowed = {f"{prefix}_fc_hz", f"{prefix}_T", f"{prefix}_stop_deg", f"{prefix}_r_lip_mm",
               f"{prefix}_stop_cos2k", f"{prefix}_stop_sin2k1", f"{prefix}_bend_sin1_mm"}
    foreign = sorted(str(k) for k in knobs
                     if str(k).startswith(f"{prefix}_") and k not in allowed)
    if foreign:
        raise registry.GeneratorError(
            f"toroidal_rollback rows accept only {prefix}_fc_hz / {prefix}_T / "
            f"{prefix}_stop_deg / {prefix}_r_lip_mm; got foreign knob(s) {foreign}")
    out = {}
    for name, default in (("fc_hz", ROWS_TOROIDAL_KNOB_DEFAULTS["fc_hz"]),
                          ("T", ROWS_TOROIDAL_KNOB_DEFAULTS["T"]),
                          ("stop_deg", ROWS_TOROIDAL_KNOB_DEFAULTS["stop_deg"])):
        out[name] = float(knobs.get(f"{prefix}_{name}", default))
    for name, value in out.items():
        if not math.isfinite(value):
            raise registry.GeneratorError(
                f"toroidal_rollback rows: {name} must be finite, got {value!r}")
    if out["fc_hz"] <= 0.0:
        raise registry.GeneratorError(
            f"toroidal_rollback rows: fc_hz must be > 0, got {out['fc_hz']}")
    if out["T"] < 0.0:
        raise registry.GeneratorError(
            f"toroidal_rollback rows: T must be >= 0, got {out['T']}")
    lo, hi = ROWS_LECLEACH_STOP_RANGE
    if not lo <= out["stop_deg"] <= hi:
        raise registry.GeneratorError(
            f"toroidal_rollback rows: stop_deg must be in [{lo:g}, {hi:g}], "
            f"got {out['stop_deg']}")
    out["r_lip_mm"] = _rows_lip_mm(knobs, prefix)
    return out


def append_tangent_lip(x, y, r_lip: float, phi_end_deg: float,
                       wrap_deg: float = TOROIDAL_WRAP_DEG,
                       n_lip: int = TOROIDAL_LIP_SAMPLES):
    """Continue a ``(x, y)`` wall with a tangent-continuous circular lip arc (mm).

    The arc has radius ``r_lip`` and its centre sits on the inward normal at the joint, so
    the arc's tangent at t = 0 equals the wall's terminal tangent ``phi_end_deg`` (C1 by
    construction).  The wall angle then keeps increasing (the lip curls BACK, as in the
    photos) for ``wrap_deg`` (default 180).  Returns ``(x_full, y_full, meta)`` with the
    joint point not repeated.  ``r_lip <= 0`` returns the row untouched (byte-identical).
    """
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    r = float(r_lip)
    if not (math.isfinite(r) and r > 0.0):
        return x, y, {"applied": False, "r_lip_mm": r}
    ph = math.radians(float(phi_end_deg))
    x0, y0 = float(x[-1]), float(y[-1])
    cx, cy = x0 - r * math.sin(ph), y0 + r * math.cos(ph)
    t = np.radians(np.linspace(0.0, float(wrap_deg), max(3, int(n_lip))))[1:]
    psi = ph - 0.5 * math.pi + t
    x_lip = cx + r * np.cos(psi)
    y_lip = cy + r * np.sin(psi)
    meta = {"applied": True, "r_lip_mm": r, "wrap_deg": float(wrap_deg),
            "joint_tangent_deg": float(phi_end_deg),
            "centre_mm": [float(cx), float(cy)],
            "label": ("[inferred] tangent-continuous circular lip continuation; not a "
                      "published lip construction")}
    return np.concatenate((x, x_lip)), np.concatenate((y, y_lip)), meta


def _rows_marches(spec: dict, knobs: dict, brief: dict, prefix: str = "g") -> list[dict]:
    """Per-azimuth marches for a rows spec (validated; used by grid + estimator).

    ``lecleach`` rows are axisymmetric: the SAME verified Fourcade march on every
    azimuth (no fc split, no shape modulation).  ``lecleach_mod`` adds the lib-2
    harmonic stop/cutoff law (and the optional axial bend); ``lecleach_ar`` adds the
    area-preserving AR stretch; ``lecleach_asym`` adds the owner-approved odd-cosine
    single-sided asymmetry (forces the FULL ring when eps_m != 0).  The Salmon rows keep
    their per-azimuth ``fc`` / T5 modulation + the even-lobe mouth ripple (the pleats).
    ``g_r_lip_mm`` appends the inferred torus lip to every kind.
    """
    kind = _rows_check_spec(spec)
    r0 = float(brief["driver"]["exit_radius_mm"])
    a0 = float(brief["driver"]["exit_angle_deg"])
    knob_map = _knob_map(knobs)
    n_phi = _spec_int(spec, "n_phi", MIN_PHI_QUARTER, MIN_PHI_QUARTER)
    mod = _rows_lecleach_mod_knobs(knob_map, prefix) if kind == "lecleach_mod" else None
    ar = _rows_lecleach_ar_knobs(knob_map, prefix) if kind == "lecleach_ar" else None
    asym = _rows_lecleach_asym_knobs(knob_map, prefix) if kind == "lecleach_asym" else None
    span = _rows_span_requested(kind, spec, knob_map, prefix)
    half = span == "half"
    full = span == "full"
    phis = _rows_span_phis(n_phi, span)
    span_rad = {"quarter": 0.5 * math.pi, "half": math.pi, "half_xz": math.pi,
                "full": 2.0 * math.pi}[span]
    if full and kind in ("iwata_ar", "toroidal_rollback", "lecleach_ar", "lecleach_mod"):
        raise registry.GeneratorError(
            f"{kind} is axisymmetric by construction (or b-term-half-forced): span: full "
            "would spend 4x the dofs on the same geometry - use quarter")
    # Harmonic basis: a FULL model has no mirror to violate, so the half-only terms
    # (odd sines / bend) are representable there; the validation takes half=True for full.
    harm_half = half or full
    if kind == "osse_rollback":
        ok = _rows_osse_rollback_knobs(knob_map, prefix)
        if ok["ripple_lobes"]:
            _rows_ripple_resolution_guard(ok["ripple_lobes"], span_rad, n_phi)
        return _rows_osse_rollback_marches(ok, phis, r0, a0)
    if kind == "lecleach":
        lk = _rows_lecleach_knobs(knob_map, prefix)
        harm = rows_task_harmonics(knob_map, prefix, half=harm_half)
        lo, hi = ROWS_LECLEACH_STOP_RANGE
        out = []
        for phi in phis:
            fc = (lk["fc_hz"] if lk["fc_v_hz"] is None
                  else float(rows_fc_law(phi, lk["fc_h_hz"], lk["fc_v_hz"])))
            stop = rows_task_stop(lk["stop_deg"], harm, phi, lo=lo, hi=hi)
            xs, ys, _phi_deg, march_meta = profiles_mod.lecleach_exact(
                r0, fc, lk["T"], a0, stop, dl_mm=1.0)
            xs, ys = _append_lip_torus(xs, ys, lk["r_lip_mm"])
            out.append({
                "phi": float(phi),
                "phi_deg": float(np.degrees(phi)),
                "fc_hz": float(fc),
                "stop_deg": float(stop),
                "x": xs,
                "y": ys,
                "march": march_meta,
            })
        return out
    if kind == "lecleach_asym":
        assert asym is not None
        harm = rows_task_harmonics(knob_map, prefix, half=harm_half)
        lo, hi = ROWS_LECLEACH_STOP_RANGE
        out = []
        for phi in phis:
            stop = rows_task_stop(asym["stop_deg"], harm, phi, lo=lo, hi=hi)
            xs, ys, _phi_deg, march_meta = profiles_mod.lecleach_exact(
                r0, asym["fc_hz"], asym["T"], a0, stop, dl_mm=1.0)
            if asym["eps_m"] != 0.0:
                # The single-sided asymmetry scales the row's radius:
                # r(phi, s) *= 1 + eps_m * w(s) * cos(phi).  The window keeps the throat
                # exact (w(0) = 0), so every row still shares the driver's exit; the lip
                # portion saturates the window (s_frac > 1 clips to 1 inside the helper).
                s_frac = np.arange(xs.size, dtype=float) * float(march_meta["dl_mm"]) \
                    / float(march_meta["L0_mm"])
                w = _rows_eps_window(s_frac, asym["eps_start"])
                ys = ys * (1.0 + asym["eps_m"] * w * math.cos(float(phi)))
            xs, ys = _append_lip_torus(xs, ys, asym["r_lip_mm"])
            out.append({
                "phi": float(phi),
                "phi_deg": float(np.degrees(phi)),
                "fc_hz": float(asym["fc_hz"]),
                "stop_deg": float(stop),
                "x": xs,
                "y": ys,
                "march": march_meta,
                "eps_m": float(asym["eps_m"]),
                "eps_start": float(asym["eps_start"]),
            })
        return out
    if kind == "lecleach_mod":
        assert mod is not None
        lo, hi = ROWS_LECLEACH_STOP_RANGE
        out = []
        for phi in phis:
            fc = float(rows_fc_law(phi, mod["fc_hz"], mod["fc_v_hz"]))
            stop = float(rows_harmonic_law(
                phi, mod["stop0_deg"], mod["stop_a2_deg"], mod["stop_a4_deg"],
                mod["stop_b1_deg"], mod["stop_b3_deg"]))
            if not lo <= stop <= hi:
                raise registry.GeneratorError(
                    f"lecleach_mod: row stop {stop:.3f} deg at phi {np.degrees(phi):.2f} "
                    f"deg is outside [{lo:g}, {hi:g}] (stop0/a2/a4/b1/b3 combination)")
            xs, ys, _phi_deg, march_meta = profiles_mod.lecleach_exact(
                r0, fc, mod["T"], a0, stop, dl_mm=1.0)
            if mod["bend_b1_mm"] != 0.0:
                # delta-x(l, phi) = bend sin(phi) * w(l/L0); w is a linear throat-anchored
                # ramp so the fan still meets at the throat (the source cap stays a point).
                L0 = float(march_meta["L0_mm"])
                w = np.arange(xs.size, dtype=float) * float(march_meta["dl_mm"]) / L0
                xs = xs + mod["bend_b1_mm"] * math.sin(float(phi)) * w
            xs, ys = _append_lip_torus(xs, ys, mod["r_lip_mm"])
            out.append({
                "phi": float(phi),
                "phi_deg": float(np.degrees(phi)),
                "fc_hz": fc,
                "stop_deg": stop,
                "x": xs,
                "y": ys,
                "march": march_meta,
            })
        return out
    if kind == "iwata_ar":
        ik = _rows_iwata_ar_knobs(knob_map, prefix)
        if half:
            raise registry.GeneratorError(
                "iwata_ar keeps BOTH mirror planes by construction (the same x(l) grid and "
                "an ellipse section with axes y_h/y_v), so span: quarter is the honest "
                "model; a half span would double the dofs without adding geometry")
        xs, ys, _phi_deg, march_meta = profiles_mod.lecleach_exact(
            r0, ik["fc_hz"], ik["T"], a0, ik["stop_deg"], dl_mm=1.0)
        xr, yr, L0 = _resample_arc(xs, ys, _spec_int(spec, "n_s", 32, 8))
        _AR, y_h, y_v = lecleach_ar_profile(xr, yr, ik["ar_m"], ik["ar_p"],
                                            AR_t=ROWS_AR_THROAT_RATIO)
        march_meta = {**march_meta, "ar_m": float(ik["ar_m"]), "ar_p": float(ik["ar_p"]),
                      "ar_t": float(ROWS_AR_THROAT_RATIO), "L0_mm": float(L0)}
        out = []
        for phi in phis:
            c, s = math.cos(float(phi)), math.sin(float(phi))
            denom = np.sqrt((y_v * c) ** 2 + (y_h * s) ** 2)
            if np.any(denom <= 0.0):
                raise registry.GeneratorError("iwata_ar: zero ellipse radius")
            radius = (y_h * y_v) / denom
            out.append({
                "phi": float(phi),
                "phi_deg": float(np.degrees(phi)),
                "fc_hz": float(ik["fc_hz"]),
                "stop_deg": float(ik["stop_deg"]),
                "x": xr,
                "y": np.asarray(radius, dtype=float),
                "resample": False,          # rows already share the SAME l stations
                "march": march_meta,
            })
        return out
    if kind == "toroidal_rollback":
        tk = _rows_toroidal_knobs(knob_map, prefix)
        harm = rows_task_harmonics(knob_map, prefix, half=harm_half)
        if half:
            raise registry.GeneratorError(
                "toroidal_rollback is axisymmetric (the same torus on every azimuth); use "
                "span: quarter")
        lo, hi = ROWS_LECLEACH_STOP_RANGE
        out = []
        for phi in phis:
            stop = rows_task_stop(tk["stop_deg"], harm, phi, lo=lo, hi=hi)
            xs, ys, _phi_deg, march_meta = profiles_mod.lecleach_exact(
                r0, tk["fc_hz"], tk["T"], a0, stop, dl_mm=1.0)
            xs, ys, lip_meta = append_tangent_lip(
                xs, ys, tk["r_lip_mm"], float(march_meta["stop_deg"]))
            out.append({
                "phi": float(phi),
                "phi_deg": float(np.degrees(phi)),
                "fc_hz": float(tk["fc_hz"]),
                "stop_deg": float(stop),
                "x": xs,
                "y": ys,
                "march": march_meta,
                "lip": lip_meta,
            })
        return out
    if kind == "lecleach_ar":
        assert ar is not None
        xs, ys, _phi_deg, march_meta = profiles_mod.lecleach_exact(
            r0, ar["fc_hz"], ar["T"], a0, ar["stop_deg"], dl_mm=1.0)
        _AR, y_h, y_v = lecleach_ar_profile(xs, ys, ar["AR_m"], ar["p"], ar["AR_t"])
        out = []
        for phi in phis:
            c, s = math.cos(float(phi)), math.sin(float(phi))
            denom = np.sqrt((y_v * c) ** 2 + (y_h * s) ** 2)
            if np.any(denom <= 0.0):
                raise registry.GeneratorError("lecleach_ar: zero ellipse radius")
            radius = (y_h * y_v) / denom
            xr, yr = _append_lip_torus(xs, radius, ar["r_lip_mm"])
            out.append({
                "phi": float(phi),
                "phi_deg": float(np.degrees(phi)),
                "fc_hz": float(ar["fc_hz"]),
                "stop_deg": float(ar["stop_deg"]),
                "x": xr,
                "y": yr,
                "march": march_meta,
            })
        return out
    pk = _rows_shape_knobs(knob_map, prefix)
    r_lip = _rows_lip_mm(knob_map, prefix)
    if pk["ripple_lobes"]:
        # The pleats: refuse a ripple the row grid cannot honestly represent.
        _rows_ripple_resolution_guard(pk["ripple_lobes"], span_rad, n_phi)
    breaking = [f"{prefix}_{name}" for name in ROWS_LR_BREAKING_KNOBS
                if f"{prefix}_{name}" in knob_map]
    if breaking:
        raise registry.GeneratorError(
            f"salmon rows: {breaking} breaks the left-right mirror (x -> -x is "
            "phi -> pi - phi; only even cosines and odd sines are invariant). The GRID "
            "rows route ships quarter/half/full models only, so an LR-breaking term is refused "
            "instead of being silently mis-meshed (lib-2 section 2.5; the odd-cosine "
            "asymmetry lives on the lecleach_asym kind, which forces the full ring)")
    task_harm = rows_task_harmonics(knob_map, prefix, half=harm_half)
    stops, fc_scales = x_shape_modulation(pk["stop_deg"], pk["x_amp"], pk["x_fc"], phis)
    stops = np.atleast_1d(stops).astype(float)
    if task_harm["active"]:
        stops = stops * np.asarray(rows_stop_multiplier(
            phis, task_harm["stop_cos2k"], task_harm["stop_sin2k1"]), dtype=float)
        # The base stop_deg is validated in (0, 360); the list harmonic law may take rows
        # BELOW the plan's 120 deg window (the saddle's short bottom) or above it (the
        # deep side), which is exactly the photographed asymmetry.  The Salmon core is
        # the authority on legality (it refuses 180 deg and non-monotone marches).
        for phi, stop in zip(phis, stops):
            if not (0.0 < float(stop) < 360.0) or abs(float(stop) - 180.0) < 1e-9:
                raise registry.GeneratorError(
                    f"salmon rows: modulated stop {float(stop):.3f} deg at phi "
                    f"{np.degrees(phi):.2f} deg is outside (0, 360) or is the 180 deg "
                    "cap-area asymptote (stop/harmonic combination)")
    out = []
    for phi, stop, fc_scale in zip(phis, stops, np.atleast_1d(fc_scales)):
        if kind == "salmon_axisym":
            fc = pk["fc_h_hz"]
        else:
            ang = float(phi) * (pk["fc_fold"] / 2.0)       # fold 4: the same law in 2 phi
            if pk["fc_union"]:                               # union with the 90 deg copy
                psi = abs(math.atan2(math.sin(float(phi)), math.cos(float(phi))))
                psi = min(psi, math.pi - psi)
                ang = max(psi, 0.5 * math.pi - psi)
            c, s = math.cos(ang), math.sin(ang)
            fc = 1.0 / (c * c / pk["fc_h_hz"] + s * s / pk["fc_v_hz"])
        fc *= float(fc_scale)
        try:
            xs, ys, _thetas, _areas, march_meta = profiles_mod.salmon_march_core(
                r0, fc, pk["T"], a0, float(stop))
        except ValueError as exc:
            raise registry.GeneratorError(str(exc)) from exc
        if pk["ripple_lobes"]:
            # The pleats: r *= 1 + (amp/narrowest) * w(s) * cos(N phi) with an even lobe
            # count. The absolute amp_mm is delivered at the row's widest station (the
            # ridge height in mm is constant across azimuths); w opens at ripple_start.
            l_arc = _arc_length(xs, ys)
            s_frac = l_arc / float(l_arc[-1])
            w = _rows_eps_window(s_frac, pk["ripple_start"])
            ys = ys * (1.0 + (pk["ripple_amp_mm"] / max(float(np.max(ys)), 1e-9))
                       * w * np.cos(pk["ripple_lobes"] * float(phi)))
        xs, ys = _append_lip_torus(xs, ys, r_lip)
        out.append({
            "phi": float(phi),
            "phi_deg": float(np.degrees(phi)),
            "fc_hz": float(fc),
            "stop_deg": float(stop),
            "x": xs,
            "y": ys,
            "march": march_meta,
            "harmonic": task_harm if task_harm["active"] else None,
        })
    return out


def _rows_mouth_radii(grid: np.ndarray, phis: np.ndarray) -> tuple[float, float]:
    """Mouth half-axes ``(horizontal, vertical)`` from the phi = 0 / |phi| = 90 rows.

    In a half model row 0 is ``-90`` (vertical), not the horizontal plane, so indexing
    blindly by row 0 would swap the axes.  Horizontal = the row nearest phi = 0;
    vertical = the larger of the two ``|phi| = 90`` endpoint rows (the envelope-relevant
    top/bottom extent when a sin term makes them differ).  A FULL ring has no exact
    +/-90 deg endpoint rows (and argmax |phi| points near 180 deg, an H-axis row): there
    the V radius is the largest y-projection over the ring's mouth stations, labelled
    accordingly (report consistency, not a new construction).
    """
    p = np.asarray(phis, dtype=float)
    i_h = int(np.argmin(np.abs(p)))
    if float(p[-1]) > math.pi + 1e-9:                 # a full ring
        mouth_x = grid[:, -1, 0]
        mouth_y = np.abs(grid[:, -1, 1])
        return float(np.max(mouth_x)), float(np.max(mouth_y))
    r_h = float(np.hypot(grid[i_h, -1, 0], grid[i_h, -1, 1]))
    ends = [i for i, phi in enumerate(p) if abs(abs(float(phi)) - 0.5 * math.pi) <= 1e-9]
    if not ends:
        ends = [int(np.argmax(np.abs(p)))]
    r_v = max(float(np.hypot(grid[i, -1, 0], grid[i, -1, 1])) for i in ends)
    return r_h, r_v


def rows_per_azimuth(base_spec_with_rows: dict, knobs: dict, brief: dict,
                     prefix: str = "g") -> tuple[np.ndarray, dict]:
    """Per-azimuth rows -> grid + meta (mm).

    Salmon rows (``salmon_elliptical`` / ``salmon_axisym``): ``1/fc(phi) = cos^2 phi /
    fc_h + sin^2 phi / fc_v`` (plan 9b.2 T3 verbatim), same ``T``, throat radius ``r0``
    and driver exit angle ``theta0``, the :func:`profiles.salmon_march_core` march to
    ``stop(phi)`` (which may exceed 90 deg).  ``lecleach`` rows: the SAME verified
    Fourcade march on every azimuth (axisymmetric real rollback; no fc split, no T5
    modulation, and no hypothesis label -- it is an attributed published construction).
    ``lecleach_mod``: the same meridian with the lib-2 harmonic stop/cutoff law (a
    LABELED RECONSTRUCTION; a b-term forces the half model).  ``lecleach_ar``: the
    area-preserving AR stretch (also a labeled reconstruction).  Every row is resampled
    to the same ``n_s`` by normalized arc length.  The mouth edge is each row's endpoint
    (the saddle).
    """
    kind = _rows_check_spec(base_spec_with_rows)
    n_s = _spec_int(base_spec_with_rows, "n_s", 32, 8)
    knob_map = _knob_map(knobs)
    mod = _rows_lecleach_mod_knobs(knob_map, prefix) if kind == "lecleach_mod" else None
    ar = _rows_lecleach_ar_knobs(knob_map, prefix) if kind == "lecleach_ar" else None
    asym = _rows_lecleach_asym_knobs(knob_map, prefix) if kind == "lecleach_asym" else None
    marches = _rows_marches(base_spec_with_rows, knobs, brief, prefix)
    phis = np.asarray([m["phi"] for m in marches], dtype=float)
    span = _rows_span_requested(kind, base_spec_with_rows, knob_map, prefix)
    half = span == "half"
    half_xz = span == "half_xz"
    full = span == "full"
    resample_flags = [bool(m.get("resample", True)) for m in marches]
    if len(set(resample_flags)) != 1:
        raise registry.GeneratorError(
            "rows: a kind must either pre-sample every row at the shared l stations or "
            "none; mixed resampling is not supported")
    resample = resample_flags[0]
    task_harm = (rows_task_harmonics(_knob_map(knobs), prefix, half=(half or full))
                 if kind in ("lecleach", "lecleach_asym", "toroidal_rollback",
                             "salmon_elliptical", "salmon_axisym") else
                 {"stop_cos2k": [], "stop_sin2k1": [], "bend_sin1_mm": 0.0,
                  "active": False})
    profiles_xy = [(m["x"], m["y"]) for m in marches]
    a0 = float(brief["driver"]["exit_angle_deg"])
    wt = float(base_spec_with_rows.get("wall_thickness_mm", 3.0))
    if full:
        phi_note = ("measured from the HORIZONTAL +x axis; FULL ring phi = 0 .. 360 deg "
                    "exclusive of the seam row (no mirror planes, quadrants '1234')")
    elif half:
        phi_note = ("measured from the HORIZONTAL +x axis; HALF model phi = -90 .. +90 "
                    "deg inclusive (phi = 0 row is horizontal, both +/-90 rows lie on "
                    "x = 0 / the yz symmetry plane)")
    elif half_xz:
        phi_note = ("measured from the HORIZONTAL +x axis; HALF_XZ model phi = 0 .. 180 "
                    "deg inclusive (phi = 0 and 180 rows lie on y = 0 / the xz symmetry "
                    "plane, phi = 90 is the vertical row)")
    else:
        phi_note = ("measured from the HORIZONTAL +x axis; QUARTER model phi = 0 .. 90 "
                    "deg inclusive (row 0 = H plane y = 0, last row = V plane x = 0)")
    sign_conventions = {
        "phi": phi_note,
        "phi_origin": "phi = 0 is the horizontal (+x) mouth-plane axis (pinned)",
        "x": "wall axial abscissa from the throat; NON-MONOTONE past 90 deg (rollback)",
        "outer_offset": "outward in-plane normal, +y at the throat (grid_outer_points)",
    }
    if kind == "lecleach":
        lk = _rows_lecleach_knobs(knob_map, prefix)
        march0 = marches[0]["march"]
        meta = {
            "family": "grid",
            "rows_type": kind,
            "construction_label": ROWS_LECLEACH_CONSTRUCTION_LABEL,
            "source_auto_angle_deg": a0,
            "wall_thickness_mm": wt,
            "fc_hz": float(lk["fc_hz"]),
            "fc_h_hz": None if lk["fc_h_hz"] is None else float(lk["fc_h_hz"]),
            "fc_v_hz": None if lk["fc_v_hz"] is None else float(lk["fc_v_hz"]),
            "T": float(lk["T"]),
            "stop_deg": float(lk["stop_deg"]),
            "stop_cos2k": [float(v) for v in task_harm["stop_cos2k"]],
            "stop_sin2k1": [float(v) for v in task_harm["stop_sin2k1"]],
            "bend_sin1_mm": float(task_harm["bend_sin1_mm"]),
            "r_lip_mm": float(lk["r_lip_mm"]),
            "lip_model": _LIP_MODEL_NOTE,
            "phi1_included_deg": float(march0["phi1_included_deg"]),
            "L0_mm": float(march0["L0_mm"]),
            "row_fc_hz": [float(m["fc_hz"]) for m in marches],
            "row_stop_deg": [float(m["stop_deg"]) for m in marches],
            "row_stop_actual_deg": [float(m["march"]["stop_deg"]) for m in marches],
            "sign_conventions": sign_conventions,
        }
        if task_harm["active"]:
            meta.update({
                "reconstruction_label": ROWS_MOD_RECONSTRUCTION_LABEL,
                "harmonic_law": ("stop(phi) = stop0 (1 + sum a_2k cos(2k phi) + "
                                 "sum b_(2k+1) sin((2k+1) phi)), phi from horizontal"),
            })
    elif kind == "lecleach_mod":
        assert mod is not None
        march0 = marches[0]["march"]
        meta = {
            "family": "grid",
            "rows_type": kind,
            "construction_label": ROWS_LECLEACH_CONSTRUCTION_LABEL,
            "reconstruction_label": ROWS_MOD_RECONSTRUCTION_LABEL,
            "source_auto_angle_deg": a0,
            "wall_thickness_mm": wt,
            "fc_hz": float(mod["fc_hz"]),
            "fc_v_hz": None if mod["fc_v_hz"] is None else float(mod["fc_v_hz"]),
            "T": float(mod["T"]),
            "stop0_deg": float(mod["stop0_deg"]),
            "stop_a2_deg": float(mod["stop_a2_deg"]),
            "stop_a4_deg": float(mod["stop_a4_deg"]),
            "stop_b1_deg": float(mod["stop_b1_deg"]),
            "stop_b3_deg": float(mod["stop_b3_deg"]),
            "bend_b1_mm": float(mod["bend_b1_mm"]),
            "r_lip_mm": float(mod["r_lip_mm"]),
            "lip_model": _LIP_MODEL_NOTE,
            "harmonic_law": ("stop(phi) = stop0 + a2 cos2phi + a4 cos4phi + "
                             "b1 sinphi + b3 sin3phi, phi from the horizontal axis"),
            "fc_law": ("1/fc(phi) = cos^2 phi / fc_h + sin^2 phi / fc_v (T3 law, phi "
                       "from the horizontal axis)"),
            "phi1_included_deg": float(march0["phi1_included_deg"]),
            "L0_mm": float(march0["L0_mm"]),
            "row_fc_hz": [float(m["fc_hz"]) for m in marches],
            "row_stop_deg": [float(m["stop_deg"]) for m in marches],
            "row_stop_actual_deg": [float(m["march"]["stop_deg"]) for m in marches],
            "sign_conventions": sign_conventions,
        }
    elif kind == "lecleach_ar":
        assert ar is not None
        march0 = marches[0]["march"]
        meta = {
            "family": "grid",
            "rows_type": kind,
            "construction_label": ROWS_AR_CONSTRUCTION_LABEL,
            "base_construction_label": ROWS_LECLEACH_CONSTRUCTION_LABEL,
            "source_auto_angle_deg": a0,
            "wall_thickness_mm": wt,
            "fc_hz": float(ar["fc_hz"]),
            "T": float(ar["T"]),
            "stop_deg": float(ar["stop_deg"]),
            "AR_m": float(ar["AR_m"]),
            "AR_t": float(ar["AR_t"]),
            "p": float(ar["p"]),
            "AR_law": ("AR(l) = AR_t + (AR_m - AR_t) (l/L0)^p; y_h = y sqrt(AR), "
                       "y_v = y / sqrt(AR), x shared; pi y_h y_v = pi y^2"),
            "r_lip_mm": float(ar["r_lip_mm"]),
            "lip_model": _LIP_MODEL_NOTE,
            "phi1_included_deg": float(march0["phi1_included_deg"]),
            "L0_mm": float(march0["L0_mm"]),
            "row_fc_hz": [float(m["fc_hz"]) for m in marches],
            "row_stop_deg": [float(m["stop_deg"]) for m in marches],
            "row_stop_actual_deg": [float(m["march"]["stop_deg"]) for m in marches],
            "sign_conventions": sign_conventions,
        }
    elif kind == "iwata_ar":
        ik = _rows_iwata_ar_knobs(knob_map, prefix)
        march0 = marches[0]["march"]
        meta = {
            "family": "grid",
            "rows_type": kind,
            "construction_label": IWATA_AR_LABEL,
            "base_construction_label": ROWS_LECLEACH_CONSTRUCTION_LABEL,
            "source_auto_angle_deg": a0,
            "wall_thickness_mm": wt,
            "fc_hz": float(ik["fc_hz"]),
            "T": float(ik["T"]),
            "stop_deg": float(ik["stop_deg"]),
            "ar_m": float(ik["ar_m"]),
            "ar_p": float(ik["ar_p"]),
            "ar_t": float(ROWS_AR_THROAT_RATIO),
            "p_exp": float(IWATA_AR_P_EXP),
            "AR_law": ("AR(l) = AR_t + (AR_m - AR_t)(l/L0)^p; y_h = y sqrt(AR), "
                       "y_v = y / sqrt(AR), x shared; y_h y_v = y^2; the section is the "
                       "radius-field superellipse at p_exp = 2 (ellipse)"),
            "bend_sin1_mm": 0.0,
            "phi1_included_deg": float(march0["phi1_included_deg"]),
            "L0_mm": float(march0["L0_mm"]),
            "row_fc_hz": [float(m["fc_hz"]) for m in marches],
            "row_stop_deg": [float(m["stop_deg"]) for m in marches],
            "row_stop_actual_deg": [float(m["march"]["stop_deg"]) for m in marches],
            "sign_conventions": sign_conventions,
        }
    elif kind == "toroidal_rollback":
        tk = _rows_toroidal_knobs(knob_map, prefix)
        march0 = marches[0]["march"]
        lip0 = marches[0].get("lip") or {}
        meta = {
            "family": "grid",
            "rows_type": kind,
            "construction_label": TOROIDAL_LABEL,
            "base_construction_label": ROWS_LECLEACH_CONSTRUCTION_LABEL,
            "source_auto_angle_deg": a0,
            "wall_thickness_mm": wt,
            "fc_hz": float(tk["fc_hz"]),
            "T": float(tk["T"]),
            "stop_deg": float(tk["stop_deg"]),
            "stop_cos2k": [float(v) for v in task_harm["stop_cos2k"]],
            "stop_sin2k1": [float(v) for v in task_harm["stop_sin2k1"]],
            "bend_sin1_mm": float(task_harm["bend_sin1_mm"]),
            "r_lip_mm": float(tk["r_lip_mm"]),
            "lip_wrap_deg": float(lip0.get("wrap_deg", TOROIDAL_WRAP_DEG)),
            "lip_joint_tangent_deg": float(lip0.get("joint_tangent_deg",
                                                    march0["stop_deg"])),
            "lip_model": ("[inferred] tangent-continuous circular lip arc (C1 at the "
                          "joint) curling back; no published lip construction exists"),
            "phi1_included_deg": float(march0["phi1_included_deg"]),
            "L0_mm": float(march0["L0_mm"]),
            "row_fc_hz": [float(m["fc_hz"]) for m in marches],
            "row_stop_deg": [float(m["stop_deg"]) for m in marches],
            "row_stop_actual_deg": [float(m["march"]["stop_deg"]) for m in marches],
            "sign_conventions": sign_conventions,
        }
    elif kind == "osse_rollback":
        ok = _rows_osse_rollback_knobs(knob_map, prefix)
        meta = {
            "family": "grid",
            "rows_type": kind,
            "construction_label": OSSE_ROLL_LABEL,
            "source_auto_angle_deg": a0,
            "wall_thickness_mm": wt,
            **{k: float(v) for k, v in ok.items() if k != "ripple_lobes"},
            "ripple_lobes": int(ok["ripple_lobes"]),
            "lip_model": ("[inferred] tangent-continuous circular lip arc (C1 at the joint) "
                          "curling back; wrap(phi) = wrap_deg (1 + wrap_cos_amp cos(N phi))"),
            "row_a_deg": [float(m["a_deg"]) for m in marches],
            "row_wall_end_deg": [float(m["march"]["wall_end_deg"]) for m in marches],
            "row_stop_deg": [float(m["march"]["stop_deg"]) for m in marches],
            "sign_conventions": sign_conventions,
        }
        if ok["ripple_lobes"]:
            meta["ripple_label"] = ROWS_RIPPLE_LABEL
    elif kind == "lecleach_asym":
        assert asym is not None
        march0 = marches[0]["march"]
        meta = {
            "family": "grid",
            "rows_type": kind,
            "construction_label": ROWS_ASYM_LABEL,
            "base_construction_label": ROWS_LECLEACH_CONSTRUCTION_LABEL,
            "source_auto_angle_deg": a0,
            "wall_thickness_mm": wt,
            "fc_hz": float(asym["fc_hz"]),
            "T": float(asym["T"]),
            "stop_deg": float(asym["stop_deg"]),
            "eps_m": float(asym["eps_m"]),
            "eps_start": float(asym["eps_start"]),
            "eps_law": ("r(phi, s) *= 1 + eps_m * w(s) * cos(phi); w = the smoothstep "
                        "window on the arc fraction opening at eps_start; the throat "
                        "stays exact (w(0) = 0)"),
            "r_lip_mm": float(asym["r_lip_mm"]),
            "lip_model": _LIP_MODEL_NOTE,
            "phi1_included_deg": float(march0["phi1_included_deg"]),
            "L0_mm": float(march0["L0_mm"]),
            "row_fc_hz": [float(m["fc_hz"]) for m in marches],
            "row_stop_deg": [float(m["stop_deg"]) for m in marches],
            "row_stop_actual_deg": [float(m["march"]["stop_deg"]) for m in marches],
            "sign_conventions": sign_conventions,
        }
        if asym["eps_m"] != 0.0 and full:
            meta["full_ring_reason"] = ("the odd cos(phi) term breaks the left-right "
                                        "mirror; the seam-free full ring represents it (C2)")
        if asym["eps_m"] != 0.0 and half_xz:
            meta["half_xz_reason"] = ("the odd cos(phi) term is EVEN under the up/down "
                                      "mirror phi -> -phi, so the upper half (phi 0..180, "
                                      "mirror plane xz, quadrants '12') represents it while "
                                      "keeping the left-right asymmetry")
        if task_harm["active"]:
            meta.update({
                "reconstruction_label": ROWS_MOD_RECONSTRUCTION_LABEL,
                "harmonic_law": ("stop(phi) = stop0 (1 + sum a_2k cos(2k phi) + "
                                 "sum b_(2k+1) sin((2k+1) phi)), phi from horizontal"),
            })
    else:
        pk = _rows_shape_knobs(knob_map, prefix)
        meta = {
            "family": "grid",
            "rows_type": kind,
            "hypothesis_label": ROWS_HYPOTHESIS_LABEL,
            "source_auto_angle_deg": a0,
            "wall_thickness_mm": wt,
            "fc_h_hz": float(pk["fc_h_hz"]),
            "fc_v_hz": float(pk["fc_v_hz"]),
            "T": float(pk["T"]),
            "stop_deg": float(pk["stop_deg"]),
            "x_amp": float(pk["x_amp"]),
            "x_fc": float(pk["x_fc"]),
            "fc_fold": float(pk["fc_fold"]),
            "fc_union": float(pk["fc_union"]),
            "ripple_lobes": int(pk["ripple_lobes"]),
            "ripple_amp_mm": float(pk["ripple_amp_mm"]),
            "ripple_start": float(pk["ripple_start"]),
            "r_lip_mm": float(_rows_lip_mm(knob_map, prefix)),
            "lip_model": _LIP_MODEL_NOTE,
            "row_fc_hz": [float(m["fc_hz"]) for m in marches],
            "row_stop_deg": [float(m["stop_deg"]) for m in marches],
            "row_stop_actual_deg": [float(m["march"]["stop_deg"]) for m in marches],
            "stop_cos2k": [float(v) for v in task_harm["stop_cos2k"]],
            "stop_sin2k1": [float(v) for v in task_harm["stop_sin2k1"]],
            "bend_sin1_mm": float(task_harm["bend_sin1_mm"]),
            "sign_conventions": sign_conventions,
        }
        if pk["ripple_lobes"]:
            meta["ripple_label"] = ROWS_RIPPLE_LABEL
            meta["ripple_law"] = ("r *= 1 + (ripple_amp_mm / row_max) * w(s) * "
                                  "cos(ripple_lobes * phi); w opens at ripple_start; "
                                  "the ridge height in mm is constant across azimuths")
        if task_harm["active"]:
            # A salmon list stop/bend law is a C2 reconstruction: label it so the recipe is
            # never mistaken for a verified construction.
            meta.update({
                "reconstruction_label": ROWS_MOD_RECONSTRUCTION_LABEL,
                "harmonic_law": ("stop(phi) = stop_deg (1 + x_amp cos4phi') * "
                                 "(1 + sum a_2k cos(2k phi) + sum b_(2k+1) "
                                 "sin((2k+1) phi)), phi from the horizontal axis"),
            })
    grid, meta = _build_rows_grid(profiles_xy, phis, n_s, meta, resample=resample)
    r_h, r_v = _rows_mouth_radii(grid, phis)
    meta["mouth_radius_h_mm"] = r_h
    meta["mouth_radius_v_mm"] = r_v
    # Overall mouth extents (the widest station anywhere on the rows), NOT the lip's
    # terminal station: a rolled lip curls back inside its own max-y bearing.
    meta["mouth_w_mm"] = 2.0 * float(np.max(grid[..., 0]))
    meta["mouth_h_mm"] = 2.0 * float(np.max(np.abs(grid[..., 1])))
    # lib-2 section 4.3 datasheet invariant: the mouth W/H ratio tracks the cutoff ratio,
    # W fc_h ~= H fc_v (~1.87e5 mm Hz at 2", ~1.88-1.90e5 at 1").  Report-only; the test
    # checks it at 2 % when the H/V split is actually defined.
    if kind == "lecleach_mod" and meta.get("fc_v_hz") is not None:
        meta["mouth_fc_product_mm_hz"] = {
            "width_x_fc_h": float(2.0 * r_h * meta["fc_hz"]),
            "height_x_fc_v": float(2.0 * r_v * meta["fc_v_hz"]),
        }
    elif kind == "salmon_elliptical":
        meta["mouth_fc_product_mm_hz"] = {
            "width_x_fc_h": float(2.0 * r_h * meta["fc_h_hz"]),
            "height_x_fc_v": float(2.0 * r_v * meta["fc_v_hz"]),
        }
        meta["w_times_fc_h"] = float(meta["mouth_w_mm"] * meta["fc_h_hz"])
        meta["h_times_fc_v"] = float(meta["mouth_h_mm"] * meta["fc_v_hz"])
        meta["wfc_over_hfc"] = (meta["w_times_fc_h"] / meta["h_times_fc_v"]
                                if meta["h_times_fc_v"] else None)
    meta["throat_radius_mm"] = float(np.hypot(grid[0, 0, 0], grid[0, 0, 1]))
    x_min = float(np.min(grid[..., 2]))
    x_max = float(np.max(grid[..., 2]))
    meta["L_mm"] = x_max
    meta["x_min_mm"] = x_min
    meta["x_max_mm"] = x_max
    meta["x_span_mm"] = x_max - x_min
    return grid, meta


def rows_grid_points(spec: dict, knobs: dict, brief: dict,
                     prefix: str = "g") -> tuple[np.ndarray, dict]:
    """Public rows-route entry used by ``mesh/build.py`` and ``design_params``."""
    return rows_per_azimuth(spec, knobs, brief, prefix=prefix)


def _rows_envelope_extents(spec: dict, knobs: dict, brief: dict,
                           prefix: str = "g") -> tuple[float, float, float]:
    """Conservative OUTER ``(width, height, depth)`` from the rows marches, no meshing.

    The LIST axial bend is applied in :func:`_build_rows_grid` (single source), so add its
    magnitude to the depth here or the pre-mesh estimate would under-report the mouth-plane
    shift.  The scalar ``lecleach_mod`` bend is already inside each march's ``x``.
    """
    kind = _rows_check_spec(spec)
    knob_map = _knob_map(knobs)
    span = _rows_span_requested(kind, spec, knob_map, prefix)
    bend = abs(float(rows_task_harmonics(knob_map, prefix,
                                         half=(span in ("half", "full")))
                     ["bend_sin1_mm"]))
    marches = _rows_marches(spec, knobs, brief, prefix)
    width = height = 0.0
    x_min = math.inf
    x_max = -math.inf
    for m in marches:
        c, s = abs(math.cos(m["phi"])), abs(math.sin(m["phi"]))
        width = max(width, 2.0 * float(np.max(m["y"] * c)))
        height = max(height, 2.0 * float(np.max(m["y"] * s)))
        x_min = min(x_min, float(np.min(m["x"])))
        x_max = max(x_max, float(np.max(m["x"])))
    wt = float(spec.get("wall_thickness_mm", 3.0))
    return (width + 2.0 * wt, height + 2.0 * wt, (x_max - x_min) + wt + bend)


# ------------------------------------------------------------------ design / validate


def _recipe_knobs(knob_map: dict, prefix: str = "g", *, rows: bool = False) -> dict:
    """Drop knobs that are exactly the geometry-identical defaults (absent == explicit).

    ``g_pnorm: 2.0``, ``g_term_side_mm: 0.0`` and every ``g_a{k}_*: 0.0`` are the geometry-
    identical defaults, so a recipe that spells them out and one that omits them share a design
    hash (dedup).  Rows knobs that equal ``ROWS_DEFAULTS`` (``x_amp = x_fc = 0``) get the same
    treatment.  Non-default values are always kept.
    """
    head = f"{prefix}_"
    out = dict(knob_map)
    exact = {f"{head}pnorm": GRID_DEFAULTS["pnorm"],
             f"{head}term_side_mm": GRID_DEFAULTS["term_side_mm"]}
    if rows:
        exact.update({f"{head}{k}": v for k, v in ROWS_DEFAULTS.items()})
        # Empty / all-zero harmonic lists are geometry-identical to absent.
        for key in list(out):
            if key not in ROWS_TASK_HARMONIC_LIST_KEYS:
                continue
            value = out.get(key)
            if isinstance(value, (list, tuple)) and (
                    not value or all(float(v) == 0.0 for v in value)):
                out.pop(key)
    for key in list(out):
        if key in exact and out[key] == exact[key]:
            out.pop(key)
        elif not rows and key.startswith(f"{head}a") and out[key] == GRID_DEFAULTS["a_throat"]:
            tail = key[len(head) + 1:]
            num, sep, which = tail.partition("_")
            if sep and num.isdigit() and which in ("throat", "mouth"):
                out.pop(key)
    return out


def design_params(spec: dict, knobs: dict, brief: dict) -> dict:
    """Generator block + knobs -> the compact JSON-safe ``Design.params``: ``{"grid": {...}}``.

    The persisted block is the spec (only the fields that define the surface) plus the flat knob
    dict under ``"knobs"``. The knobs are part of the RECIPE, not provenance sugar:
    ``mesh/build.py`` receives only ``(design, mesh, cfg)``, so without them the grid could not be
    re-derived, and two designs differing only in ``L_mm`` / ``h_rm_mm`` would share a design hash
    (breaking dedup, failure markers and any future mesh cache). Nothing stored here is an array.

    The knob prefix is always ``"g"`` (the wire-in contract); knobs equal to the GRID defaults are
    canonicalised away so an explicit zero and an absent zero hash identically.
    """
    knob_map = _knob_map(knobs)
    if isinstance(spec, dict) and "rows" in spec:
        # Rows kind: the depth comes from each row's march, so ``L_mm`` is NOT part of the
        # recipe and is never demanded.  ``rows`` + ``knobs`` carry the hypothesis labels.
        rows_grid_points(spec, knob_map, brief)     # full march + knob validation
        kind = _rows_check_spec(spec)
        span = _rows_span_requested(kind, spec, knob_map)
        block = {
            "rows": copy.deepcopy(spec["rows"]),
            "n_phi": _spec_int(spec, "n_phi", MIN_PHI_QUARTER, MIN_PHI_QUARTER),
            "n_s": _spec_int(spec, "n_s", 32, 8),
            "wall_thickness_mm": float(spec.get("wall_thickness_mm", 3.0)),
            "knobs": _recipe_knobs(knob_map, rows=True),
        }
        if span != "quarter":
            # Persisted only for a non-quarter model, so the quarter recipe (and its design
            # hash) stays byte-identical to the pre-span-route recipe.
            block["span"] = span
        return {"grid": block}

    grid_points(spec, knob_map, brief)          # full knob + meridian + envelope validation
    block = {
        "profile_h": copy.deepcopy(spec["profile_h"]),
        "profile_v": copy.deepcopy(spec.get("profile_v", "same")),
        "n_phi": _spec_int(spec, "n_phi", MIN_PHI_QUARTER, MIN_PHI_QUARTER),
        "n_s": _spec_int(spec, "n_s", 32, 8),
        "max_wall_deg": float(spec.get("max_wall_deg", 80.0)),
        "wall_thickness_mm": float(spec.get("wall_thickness_mm", 3.0)),
        "knobs": _recipe_knobs(knob_map),
    }
    return {"grid": block}


def validate_grid_params(block: dict) -> None:
    """Validate a persisted ``design.params["grid"]`` block (no brief available).

    Same structural ranges as :func:`grid_points`; meridian/brief-dependent legality was already
    enforced when the design was materialised. Raises ``registry.GeneratorError``.
    """
    if not isinstance(block, dict):
        raise registry.GeneratorError(
            f"grid params must be a mapping, got {type(block).__name__}")
    if "rows" in block:
        unknown = sorted(set(block) - set(ROWS_ALLOWED_BLOCK_KEYS))
        if unknown:
            raise registry.GeneratorError(f"grid: unknown key(s) {unknown}")
        if "knobs" not in block:
            raise registry.GeneratorError(
                "grid: knobs are required (the design must carry its generation recipe)")
        kind = _rows_check_spec(block)
        knob_map = _knob_map(block.get("knobs") or {})
        span = _rows_span_requested(kind, block, knob_map)   # span / forcing consistency
        half = span == "half"
        if kind == "lecleach":
            _rows_lecleach_knobs(knob_map)
            rows_task_harmonics(knob_map, half=(half or span == "full"))
        elif kind == "lecleach_asym":
            _rows_lecleach_asym_knobs(knob_map)
            rows_task_harmonics(knob_map, half=(half or span == "full"))
        elif kind == "iwata_ar":
            _rows_iwata_ar_knobs(knob_map)
        elif kind == "toroidal_rollback":
            _rows_toroidal_knobs(knob_map)
            rows_task_harmonics(knob_map, half=(half or span == "full"))
        elif kind == "lecleach_mod":
            _rows_lecleach_mod_knobs(knob_map)
        elif kind == "lecleach_ar":
            _rows_lecleach_ar_knobs(knob_map)
        elif kind == "osse_rollback":
            _rows_osse_rollback_knobs(knob_map)
        else:
            _rows_shape_knobs(knob_map)
            rows_task_harmonics(knob_map, half=(half or span == "full"))
        return
    unknown = sorted(set(block) - set(GRID_BLOCK_KEYS))
    if unknown:
        raise registry.GeneratorError(f"grid: unknown key(s) {unknown}")
    if "profile_h" not in block:
        raise registry.GeneratorError("grid: profile_h is required")
    if "knobs" not in block:
        raise registry.GeneratorError(
            "grid: knobs are required (the design must carry its generation recipe)")
    _check_spec(block)
    knob_map = _knob_map(block.get("knobs") or {})
    _shape_knobs(block, knob_map)


def envelope_extents(spec: dict, knobs: dict, brief: dict) -> tuple[float, float, float]:
    """Conservative OUTER ``(width, height, depth)`` in mm, without meshing (WP3 estimate).

    Uses the same meridians and radius field as :func:`grid_points` at the mouth, plus the wall
    thickness, so the estimate cannot under-report what the freestanding bbox will include. The
    radial envelope of the modulated section is taken as ``max_phi r(1, phi)`` for both width and
    height (conservative; mirrors ``registry.envelope_overshoot_estimate``'s max-radius rule).
    """
    if isinstance(spec, dict) and "rows" in spec:
        # WP9b rows: extents come from the same per-azimuth marches the mesher will use
        # (no superellipse radius field, no meshing).  Conservative outer shell included.
        return _rows_envelope_extents(spec, knobs, brief)
    _check_spec(spec)
    knob_map = _knob_map(knobs)
    mh, mv, L, _angle = _meridians(spec, knob_map, brief, check_envelope=False)
    p, _term, _k, a_throat, a_mouth = _shape_knobs(spec, knob_map)
    r_h = float(np.interp(L, mh.z_mm, mh.r_mm))
    r_v = float(np.interp(L, mv.z_mm, mv.r_mm))
    if not (r_h > 0.0 and r_v > 0.0):
        raise registry.GeneratorError("meridian radius must stay positive at the mouth")
    phi = np.linspace(0.0, 0.5 * math.pi, 91)
    radius = _radius_field(np.array([r_h]), np.array([r_v]), phi, p, a_throat, a_mouth,
                           np.array([1.0]))
    wt = float(spec.get("wall_thickness_mm", 3.0))
    outer_radius = float(np.max(radius)) + wt
    return 2.0 * outer_radius, 2.0 * outer_radius, float(L) + wt