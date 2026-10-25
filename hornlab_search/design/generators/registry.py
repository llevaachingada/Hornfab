"""Typology generator -> FREEFORM design params (docs/TYPOLOGY_PLAN.md s4-s5).

A generator config holds a ``generator:`` block (fixed per run) and numeric KNOBS (the config's
``seed_params`` / ``bounds``). ``materialize`` turns (block, knobs, brief) into the params of an
ordinary ``FREEFORM`` design, so Magnus's mesher builds every surface and the frozen ``Family``
contract is untouched. The record keeps the generator spec and knobs as provenance.

Generator block::

    generator:
      name: typology
      profile_h: {type: exponential}          # conical | exponential | hypex | tractrix |
                                              # lecleach | spherical_wave | osse
      profile_v: same                         # 'same' (axisymmetric meridian) or a spec
      blend_h: {type: conical}                # optional second parent for H; knob h_w in [0, 1]
      blend_v: ...                            # optional, V
      perturb: {u_max: 0.35, mode: legacy}    # optional monotone-increment perturbation; knobs
                                              # h_u0..h_u{n-2} (and v_u* when V differs).
                                              # mode 'legacy' (default) = exp(u) increments, which
                                              # move mouth size too; 'shape' rescales the
                                              # increments to keep the parent mouth radius
      n_anchors: 16
      max_wall_deg: 80.0
      mouth: ellipse                          # ellipse | superellipse (knob mouth_exponent) |
                                              # rounded_rectangle (knob mouth_corner_mm)

Knobs (mm, deg, Hz), per meridian prefix ``h_`` / ``v_`` (blend parents ``hb_`` / ``vb_``):
``L_mm`` (shared depth), ``{p}_rm_mm`` (conical / exponential / hypex mouth radius), ``{p}_T``
(hypex, lecleach), ``{p}_fc_hz`` (tractrix, lecleach, spherical_wave), ``{p}_a_deg``, ``{p}_k``,
``{p}_s``, ``{p}_n``, ``{p}_q`` (osse; the throat angle a0 is the brief's driver exit angle).

Throat: every meridian starts at the brief's driver exit radius r0. Depth: fixed-size typologies
use ``L_mm``; length-derived ones (tractrix, Le Cleac'h) end where the wall reaches
``max_wall_deg``; both meridians are then cut to the shorter common depth, because FREEFORM needs
one z span. The size envelope is enforced: a mouth or depth outside it is an invalid design.
"""
from __future__ import annotations

import math

import numpy as np

from . import profiles as P

TYPES = ("conical", "exponential", "hypex", "tractrix", "lecleach", "spherical_wave", "osse")
FIXED_SIZE = ("conical", "exponential", "hypex", "osse")
MOUTHS = ("ellipse", "superellipse", "rounded_rectangle")

#: Knob defaults used when a config does not set a knob (mm, Hz, deg). Values sit inside the
#: hi-fi brief's envelope and are typical of 1-inch compression-driver horns.
DEFAULT_KNOBS = {"L_mm": 190.0, "rm_mm": 150.0, "T": 0.7, "fc_hz": 800.0, "a_deg": 45.0,
                 "k": 1.0, "s": 0.6, "n": 4.0, "q": 0.995, "w": 0.5, "mouth_exponent": 4.0,
                 "mouth_corner_mm": 30.0, "u": 0.0}

_ROUND = 6


class GeneratorError(ValueError):
    """The knobs do not give a legal horn (envelope, r0 >= tractrix mouth, ...)."""


def _knob(knobs: dict, prefix: str, name: str):
    full = f"{prefix}_{name}" if prefix else name
    if full in knobs:
        return float(knobs[full])
    if name.startswith("u") and name[1:].isdigit():
        return float(DEFAULT_KNOBS["u"])
    return float(DEFAULT_KNOBS[name])


def _truncate(m: P.Meridian, L: float) -> P.Meridian:
    if L >= m.length_mm - 1e-9:
        return m
    keep = m.z_mm < L
    z = np.append(m.z_mm[keep], L)
    r = np.append(m.r_mm[keep], np.interp(L, m.z_mm, m.r_mm))
    th = np.append(m.theta_deg[keep], np.interp(L, m.z_mm, m.theta_deg))
    return P.Meridian(m.name, z, r, th, {**m.info, "truncated_to_mm": float(L)})


def _osse(spec: dict, knobs: dict, prefix: str, r0: float, a0: float, L: float, phi: float) -> P.Meridian:
    """OSSE meridian from Magnus's own formula (hornlab_mesher.profile_formulas.profile_points),
    not a re-implementation. ``a0`` is the brief's driver exit angle (throat rule R5)."""
    from hornlab_mesher.profile_formulas import profile_points
    prm = {"type": "OSSE", "r0": r0, "a0": a0, "L": L, "a": _knob(knobs, prefix, "a_deg"),
           "k": _knob(knobs, prefix, "k"), "s": _knob(knobs, prefix, "s"),
           "n": _knob(knobs, prefix, "n"), "q": _knob(knobs, prefix, "q")}
    pts = np.asarray(profile_points(prm, 600, phi), dtype=float)
    z, r = pts[:, 0], pts[:, 1]
    if not np.all(np.diff(z) > 0) or not np.all(r > 0):
        raise GeneratorError("OSSE meridian is not a single-valued r(z) for these knobs")
    th = np.degrees(np.arctan(np.gradient(r, z, edge_order=2)))
    return P.Meridian("osse", z - z[0], r, th, {"osse": prm})


def build_meridian(spec: dict, knobs: dict, prefix: str, *, r0: float, a0: float, L: float,
                   max_wall: float, phi: float) -> P.Meridian:
    t = spec.get("type")
    if t not in TYPES:
        raise GeneratorError(f"unknown typology {t!r} (known: {list(TYPES)})")
    if t == "conical":
        return P.conical(r0, _knob(knobs, prefix, "rm_mm"), L)
    if t == "exponential":
        return P.exponential(r0, _knob(knobs, prefix, "rm_mm"), L)
    if t == "hypex":
        return P.hypex(r0, _knob(knobs, prefix, "rm_mm"), L, _knob(knobs, prefix, "T"))
    if t == "tractrix":
        return P.tractrix(r0, _knob(knobs, prefix, "fc_hz"), max_wall_deg=max_wall)
    if t == "lecleach":
        return P.lecleach(r0, _knob(knobs, prefix, "fc_hz"), _knob(knobs, prefix, "T"), max_wall_deg=max_wall)
    if t == "spherical_wave":
        return P.spherical_wave(r0, _knob(knobs, prefix, "fc_hz"), max_wall_deg=max_wall)
    return _osse(spec, knobs, prefix, r0, a0, L, phi)


def _anchors_rounded(m: P.Meridian, n: int, max_wall: float) -> list[list[float]]:
    out = []
    for z, r, a in P.select_anchors(m, n):
        a = max(-max_wall, min(max_wall, float(a)))
        out.append([round(float(z), _ROUND), round(float(r), _ROUND), round(a, _ROUND)])
    return out


def materialize(gen: dict, knobs: dict, brief: dict) -> dict:
    """(generator block, knobs, brief) -> FREEFORM params. Raises GeneratorError."""
    r0 = float(brief["driver"]["exit_radius_mm"])
    a0 = float(brief["driver"]["exit_angle_deg"])
    env = brief["envelope"]
    max_wall = float(gen.get("max_wall_deg", 80.0))
    if not 10.0 <= max_wall < 90.0:
        raise GeneratorError(f"max_wall_deg must be in [10, 90), got {max_wall}")
    n_anchors = int(gen.get("n_anchors", 16))
    L = _knob(knobs, "", "L_mm")
    if L > float(env["max_depth_mm"]) + 1e-9:
        raise GeneratorError(f"depth L_mm={L:.1f} exceeds the brief envelope {env['max_depth_mm']} mm")

    def side(key: str, blend_key: str, prefix: str, phi: float) -> P.Meridian:
        m = build_meridian(gen[key], knobs, prefix, r0=r0, a0=a0, L=L, max_wall=max_wall, phi=phi)
        if gen.get(blend_key):
            mb = build_meridian(gen[blend_key], knobs, prefix + "b", r0=r0, a0=a0, L=L,
                                max_wall=max_wall, phi=phi)
            m = P.blend(m, mb, _knob(knobs, prefix, "w"))
        return m

    if "profile_h" not in gen:
        raise GeneratorError("generator needs profile_h")
    mh = side("profile_h", "blend_h", "h", 0.0)
    same = gen.get("profile_v", "same") == "same"
    if same:
        if gen.get("blend_v"):
            raise GeneratorError("blend_v needs an explicit profile_v (profile_v: same mirrors H)")
        mv = mh
    else:
        mv = side("profile_v", "blend_v", "v", math.pi / 2)
    # fixed-size meridians already end at L; length-derived ones end at max_wall. One z span.
    span = min(mh.length_mm, mv.length_mm, float(env["max_depth_mm"]))
    mh, mv = _truncate(mh, span), _truncate(mv, span)

    ah = _anchors_rounded(mh, n_anchors, max_wall)
    av = ah if same else _anchors_rounded(mv, n_anchors, max_wall)
    pert = gen.get("perturb")
    # Single place the perturbation is applied.  Absent ``mode`` (or 'legacy') is byte-for-byte
    # the previous behaviour; 'shape' keeps the parent mouth radius (see profiles.py).
    pert_mode = "legacy"
    if pert:
        pert_mode = str(pert.get("mode", "legacy"))
        if pert_mode not in ("legacy", "shape"):
            raise GeneratorError(f"perturb mode must be 'legacy' or 'shape', got {pert_mode!r}")
    if pert and any(abs(_knob(knobs, p, f"u{i}")) > 0 for p in ("h", "v") for i in range(len(ah) - 1)):
        # (all u == 0 leaves the parent typology's anchors and exact wall angles untouched)
        u_max = float(pert.get("u_max", 0.35))
        perturb = P.perturb_increments_shape if pert_mode == "shape" else P.perturb_increments
        uh = [_knob(knobs, "h", f"u{i}") for i in range(len(ah) - 1)]
        ah = [[round(float(x), _ROUND) for x in row] for row in perturb(ah, uh, u_max)]
        if same:
            av = ah
        else:
            uv = [_knob(knobs, "v", f"u{i}") for i in range(len(av) - 1)]
            av = [[round(float(x), _ROUND) for x in row] for row in perturb(av, uv, u_max)]
        for rows in (ah, av):
            for row in rows:
                row[2] = max(-max_wall, min(max_wall, row[2]))

    w_mouth, h_mouth = 2 * ah[-1][1], 2 * av[-1][1]
    if w_mouth > float(env["max_mouth_w_mm"]) + 1e-6 or h_mouth > float(env["max_mouth_h_mm"]) + 1e-6:
        raise GeneratorError(f"mouth {w_mouth:.0f} x {h_mouth:.0f} mm exceeds the brief envelope "
                             f"{env['max_mouth_w_mm']} x {env['max_mouth_h_mm']} mm")

    mouth = gen.get("mouth", "ellipse")
    if mouth not in MOUTHS:
        raise GeneratorError(f"mouth must be one of {list(MOUTHS)}, got {mouth!r}")
    if mouth == "ellipse":
        stations = [{"t": 0.0, "shape": "circle"}, {"t": 1.0, "shape": "ellipse"}]
    elif mouth == "superellipse":
        stations = [{"t": 0.0, "shape": "circle"},
                    {"t": 1.0, "shape": "superellipse",
                     "exponent": round(min(16.0, max(2.0, _knob(knobs, "", "mouth_exponent"))), _ROUND)}]
    else:
        stations = [{"t": 0.0, "shape": "circle"},
                    {"t": 1.0, "shape": "rounded_rectangle",
                     "cornerRadiusMm": round(max(1.0, _knob(knobs, "", "mouth_corner_mm")), _ROUND)}]

    def prof(rows):
        return {"points": rows, "throatAngleDeg": rows[0][2], "mouthAngleDeg": rows[-1][2]}

    # Outer shell thickness. The mesher's FREEFORM outer-offset guard rejects
    # thickness * |concave curvature| >= 0.4; an OS throat (5 deg -> 45 deg within ~13 mm) or a
    # tractrix mouth near 80 deg is too curved for the mesher default shell, so generated horns
    # use a 3 mm shell (typical of a printed horn) unless the generator block says otherwise.
    wt = float(gen.get("wall_thickness_mm", 3.0))
    if not 0.5 <= wt <= 12.0:
        raise GeneratorError(f"wall_thickness_mm must be in [0.5, 12], got {wt}")
    return {"profileH": prof(ah), "profileV": prof(av), "crossSections": stations,
            "wall_thickness_mm": round(wt, _ROUND)}


def info(gen: dict, knobs: dict, brief: dict) -> dict:
    """Derived quantities for the report (f_c, truncation, lengths), best effort."""
    out = {}
    try:
        r0 = float(brief["driver"]["exit_radius_mm"])
        a0 = float(brief["driver"]["exit_angle_deg"])
        L = _knob(knobs, "", "L_mm")
        for key, prefix, phi in (("profile_h", "h", 0.0), ("profile_v", "v", math.pi / 2)):
            spec = gen.get(key)
            if not isinstance(spec, dict):
                continue
            m = build_meridian(spec, knobs, prefix, r0=r0, a0=a0, L=L,
                               max_wall=float(gen.get("max_wall_deg", 80.0)), phi=phi)
            out[prefix] = {k: v for k, v in m.info.items() if isinstance(v, (int, float, str))}
            out[prefix].update(type=spec["type"], length_mm=m.length_mm, mouth_radius_mm=m.mouth_radius_mm)
    except Exception:  # noqa: BLE001 - report-only
        pass
    return out


#: Tolerance search/evaluate.py::envelope_violation applies to the mouth W/H (mm).
_ENVELOPE_MOUTH_TOLERANCE_MM = 0.5


def _profile_radii(params: dict, key: str) -> list[float] | None:
    """Anchor radii of ``profileH``/``profileV``; None if this is not the generated form."""
    prof = params.get(key)
    if not isinstance(prof, dict):
        return None
    pts = prof.get("points")
    if not isinstance(pts, (list, tuple)) or not pts:
        return None
    radii = []
    for row in pts:
        try:
            radii.append(float(row[1]))
        except (TypeError, ValueError, IndexError):
            return None
    return radii


def envelope_overshoot_estimate(params: dict, brief: dict | None) -> float | None:
    """Relative size-envelope overshoot of a generated FREEFORM design, before meshing.

    Mimics ``search/evaluate.py::envelope_violation`` on the materialized anchors so a
    candidate that will be rejected after meshing can be scored without meshing:

    * outer width  = 2 * (max ``profileH`` radius + ``wall_thickness_mm``)
    * outer height = 2 * (max ``profileV`` radius + ``wall_thickness_mm``)
    * depth        = anchor z span + ``wall_thickness_mm``

    The shell offset is included because the post-mesh bounding box includes the free-
    standing outer shell.  The limits are the post-mesh ones: brief ``max_mouth_w_mm``/
    ``max_mouth_h_mm`` plus the 0.5 mm meshing tolerance and ``max_depth_mm`` plus
    ``ENVELOPE_DEPTH_ALLOWANCE_MM`` (imported lazily from evaluate to keep the design
    layer import-free of the search layer at module load).

    Returns ``max(0, max(value/limit - 1))`` over the three dimensions: ``0.0`` when the
    estimate is inside, a positive relative overshoot when it is outside.  ``None`` when
    ``brief`` is None or ``params`` is not the generated-``profileH``/``profileV`` form.
    Conservative by construction (the radial shell offset is added in full); verified
    against every existing typology seed, which estimates 0.0.
    """
    if brief is None or not isinstance(params, dict):
        return None
    rad_h = _profile_radii(params, "profileH")
    rad_v = _profile_radii(params, "profileV")
    if rad_h is None or rad_v is None:
        return None
    env = brief.get("envelope") or {}
    if not env:
        return 0.0
    try:
        wt = float(params.get("wall_thickness_mm", 3.0))
        lim_w = float(env.get("max_mouth_w_mm", 1e9)) + _ENVELOPE_MOUTH_TOLERANCE_MM
        lim_h = float(env.get("max_mouth_h_mm", 1e9)) + _ENVELOPE_MOUTH_TOLERANCE_MM
        from ...search.evaluate import ENVELOPE_DEPTH_ALLOWANCE_MM
        lim_d = float(env.get("max_depth_mm", 1e9)) + float(ENVELOPE_DEPTH_ALLOWANCE_MM)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(wt) and wt >= 0.0
            and lim_w > 0.0 and lim_h > 0.0 and lim_d > 0.0):
        return None
    # profileH is the horizontal meridian (x), profileV the vertical one (y).
    z_h = [float(row[0]) for row in params["profileH"]["points"]]
    z_v = [float(row[0]) for row in params["profileV"]["points"]]
    w_mm = 2.0 * (max(rad_h) + wt)
    h_mm = 2.0 * (max(rad_v) + wt)
    depth_mm = (max(max(z_h), max(z_v)) - min(min(z_h), min(z_v))) + wt
    overshoot = max(w_mm / lim_w - 1.0, h_mm / lim_h - 1.0, depth_mm / lim_d - 1.0, 0.0)
    if not math.isfinite(overshoot):
        return None
    return float(overshoot)
