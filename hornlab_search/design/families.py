"""Legal keys per family, validation, and the Design -> hornlab_mesher config dict.

The mesher's parameter names ARE the contract (01_CONTRACTS section 5); nothing here renames
them. A Design carries the family and a dict in the mesher's own keys and units (mm / deg).

Tables below were populated from 01_CONTRACTS section 5 and checked against the on-disk
``hornlab_mesher`` ``docs/config-schema.md``. The file on disk wins. A key that is not in a
family's table is REJECTED, not passed through: the mesher itself silently ignores unknown
profile keys (measured: ``bogus_key`` builds fine), which is exactly why we must not.

Adding a key is a one-line table edit. ``lo`` / ``hi`` are HARD schema limits only (for example
``s1`` in 0..10, a superellipse exponent in 2..16), never rule-of-thumb plausibility limits:
nothing in the optimizer may refuse a design on a rule of thumb (contracts section 3).
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from pathlib import Path

from ..types import Design, GeometryInvalidError, MeshSpec

# ------------------------------------------------------------------ key tables


@dataclass(frozen=True)
class KeySpec:
    kind: type                 # float | int | str | list | dict | bool
    lo: float | None = None    # hard schema limit, inclusive; None = unbounded
    hi: float | None = None
    note: str = ""
    section: str = "profile"   # where the mesher config wants it: top | profile | cross_section |
    #                            mesh | morph | gcurve | enclosure | source
    choices: tuple | None = None   # legal values for str keys


def _f(lo=None, hi=None, note="", section="profile") -> KeySpec:
    return KeySpec(float, lo, hi, note, section)


def _i(lo=None, hi=None, note="", section="profile") -> KeySpec:
    return KeySpec(int, lo, hi, note, section)


MODES = ("freestanding", "free-standing", "free", "bare", "inner", "open",
         "infinite-baffle", "ib", "baffle", "enclosure", "enclosed")

# -- keys shared by every OSSE-like family (OSSE, R-OSSE): throat + cross section
_THROAT = {
    "r0_mm": _f(note="throat radius, mm"),
    "a_deg": _f(note="coverage half-angle, deg (mesher convention)"),
    "a0_deg": _f(note="throat half-angle, deg"),
    "k": _f(note="OS/R-OSSE k"),
    "q": _f(note="termination q (> 0 while s != 0 for OSSE)"),
    "s1": _f(0.0, 10.0, "throat stretch, mm/deg; plain finite number only"),
    "s2": _f(0.0, 10.0, "throat stretch, 1/mm; plain finite number only"),
    "throat_ext_length_mm": _f(note="throat extension length, mm"),
    "throat_ext_angle_deg": _f(note="throat extension angle, deg"),
    "slot_length_mm": _f(note="slot length, mm"),
}
_CROSS = {
    "exponent": _f(note="superellipse exponent of the cross section", section="cross_section"),
    "aspect_ratio": _f(note="width-to-height scaling", section="cross_section"),
}
_COMMON = {
    "mode": KeySpec(str, note="mesher build mode", section="top", choices=MODES),
    "wall_thickness_mm": _f(0.0, None, "freestanding shell thickness, mm", section="mesh"),
}
_MORPH = {
    "morph_target": _i(note="0 none, 1 rectangle, 2 circle", section="morph"),
    "morph_width_mm": _f(note="full target width, mm", section="morph"),
    "morph_height_mm": _f(note="full target height, mm", section="morph"),
    "morph_corner_mm": _f(note="target corner radius, mm", section="morph"),
    "morph_rate": _f(0.0, None, "morph rate, >= 0", section="morph"),
    "morph_fixed": _f(note="fixed part, 0..1", section="morph"),
    "morph_allow_shrinkage": _i(note="0/1", section="morph"),
}
_GCURVE = {
    "gcurve_type": _i(note="0 off, 1 superellipse, 2 superformula", section="gcurve"),
    "gcurve_width_mm": _f(section="gcurve"),
    "gcurve_aspect_ratio": _f(section="gcurve"),
    "gcurve_dist": _f(section="gcurve"),
    "gcurve_rot_deg": _f(section="gcurve"),
    "gcurve_sf": KeySpec(str, section="gcurve", note="superformula expression string"),
    "gcurve_se_n": _f(section="gcurve"),
    "gcurve_sf_a": _f(section="gcurve"),
    "gcurve_sf_b": _f(section="gcurve"),
    "gcurve_sf_m1": _f(section="gcurve"),
    "gcurve_sf_m2": _f(section="gcurve"),
    "gcurve_sf_n1": _f(section="gcurve"),
    "gcurve_sf_n2": _f(section="gcurve"),
    "gcurve_sf_n3": _f(section="gcurve"),
}

_OSSE = {
    **_THROAT, **_CROSS, **_COMMON, **_MORPH, **_GCURVE,
    "L_mm": _f(note="axial length, mm (OSSE only)"),
    "n": _f(note="termination n (> 0 while s != 0)"),
    "s": _f(note="termination s"),
    "rot_deg": _f(note="rotation, deg (OSSE only)"),
    "h": _f(note="half-sine bulge, mm"),
}

_ROSSE = {
    **_THROAT, **_CROSS, **_COMMON,
    "R_mm": _f(note="mouth radius, mm (R-OSSE only)"),
    "tmax": _f(note="truncation parameter, > 0"),
    "m": _f(note="R-OSSE m"),
    "r": _f(note="R-OSSE r"),
    "b": _f(note="R-OSSE b"),
}

_ICW = {
    **_COMMON,
    "termination": KeySpec(str, note="categorical; cannot take a lo/hi bound", section="profile",
                           choices=("flat_baffle", "rollback")),
    "r0_mm": _f(note="throat radius, mm"),
    "a0_deg": _f(note="throat half-angle, deg"),
    "L_mm": _f(note="axial length, mm"),
    "R_mm": _f(note="mouth radius, mm"),
    "coverage_angle_deg": _f(0.0, None, "ICW wall half-angle (mesher enforces theta0_deg < coverage_angle_deg < 90.0); target coverage_*_deg is the TOTAL included angle"),
    "hold_start": _f(0.0, 1.0),
    "hold_end": _f(0.0, 1.0),
    "kappa0": _f(note="initial curvature, 1/mm"),
    "theta1_deg": _f(note="theta1, deg"),
    "n_coeff": _i(note="ICW basis size"),
    "kappa_abs_max": _f(),
    "dkappa_ds_abs_max": _f(),
    "theta_max_deg": _f(),
    "pin_mouth_radius": KeySpec(bool),
    "icw_seed": KeySpec(dict, note="seed formula the ICW curve is fitted to"),
    "icw_coeffs": KeySpec(list),
    "icw_S": _f(),
}

_FREEFORM = {
    **_COMMON,
    "profileH": KeySpec(dict, note="{points, throatAngleDeg, mouthAngleDeg}, horizontal meridian"),
    "profileV": KeySpec(dict, note="{points, throatAngleDeg, mouthAngleDeg}, vertical meridian"),
    "crossSections": KeySpec(list, note="2..32 stations {t, shape, [exponent|cornerRadiusMm]}"),
    "inflectionPolicy": KeySpec(str, choices=("warn", "reject")),
}

FAMILY_KEYS: dict[str, dict[str, KeySpec]] = {
    "OSSE": _OSSE,
    "R-OSSE": _ROSSE,
    "ICW": _ICW,
    "FREEFORM": _FREEFORM,
}

# Keys the mesher refuses for a family, with the reason the schema gives. Checked BEFORE the
# generic "unknown key" rejection so the user gets the real explanation.
_REFUSED_HINTS: dict[str, dict[str, str]] = {
    "R-OSSE": {
        "rot_deg": "R-OSSE does not support rot_deg (OSSE only)",
        "L_mm": "R-OSSE does not support an explicit L_mm (use R_mm; OSSE only)",
        "n": "n is an OSSE-only key",
        "s": "s is an OSSE-only key",
        "h": "h is an OSSE-only key",
    },
    "OSSE": {
        "R_mm": "R_mm is an R-OSSE-only key",
        "tmax": "tmax is an R-OSSE-only key",
        "m": "m is an R-OSSE-only key",
        "r": "r is an R-OSSE-only key",
        "b": "b is an R-OSSE-only key",
    },
}
_ICW_OSSE_SHAPE = ("a_deg", "n", "s", "q", "k", "h", "rot_deg", "s1", "s2", "tmax", "m", "r", "b",
                   "exponent", "aspect_ratio", "throat_ext_length_mm", "throat_ext_angle_deg",
                   "slot_length_mm")
for _k in _ICW_OSSE_SHAPE:
    _REFUSED_HINTS.setdefault("ICW", {})[_k] = (
        f"ICW rejects the OSSE/R-OSSE shape key '{_k}' at the top level "
        "(put an OSSE/R-OSSE seed inside icw_seed instead)")
for _k in ("sampling_mode", "z_map_points", "zmap"):
    _REFUSED_HINTS["ICW"][_k] = f"ICW rejects zmap sampling ('{_k}'); it samples uniformly in arc length"
_REFUSED_HINTS["FREEFORM"] = {
    k: f"FREEFORM refuses '{k}': crossSections / the two meridians own the outline"
    for k in ("exponent", "aspect_ratio", "rot_deg", "h", "s1", "s2", "throat_ext_length_mm",
              "throat_ext_angle_deg", "slot_length_mm", "morph_target", "gcurve_type")
}

# FREEFORM bare-key aliases. The shipped examples/freeform_hv.yaml bounds a bare ``exponent``;
# the value lives in the superellipse station of ``crossSections`` (task 04 owns this mapping).
FREEFORM_ALIASES = {"exponent"}

_FF_PROFILE_KEYS = {"points", "throatAngleDeg", "mouthAngleDeg"}
_FF_SHAPES = ("circle", "ellipse", "superellipse", "rounded_rectangle")

# ------------------------------------------------------------------ small helpers


def _isnum(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))


def _bad(family: str, key: str, why: str) -> GeometryInvalidError:
    return GeometryInvalidError(f"{family}: key '{key}': {why}")


def legal_roots(family: str) -> set[str]:
    return set(FAMILY_KEYS[family])


# ------------------------------------------------------------------ param paths


def resolve_path(family: str, params: dict, key: str) -> tuple:
    """Turn a search key into a path of dict keys / list indices into ``params``.

    - a key present at the top level is itself;
    - ``a.b.0.c`` walks dicts by name and lists by integer index;
    - for FREEFORM, a bare ``exponent`` is the first superellipse station in ``crossSections``.
    Raises KeyError if the path does not exist (the caller decides what that means).
    """
    if key in params:
        return (key,)
    if family == "FREEFORM" and key in FREEFORM_ALIASES:
        for i, st in enumerate(params.get("crossSections", [])):
            if isinstance(st, dict) and st.get("shape") == "superellipse":
                return ("crossSections", i, key)
        raise KeyError(f"no superellipse station in crossSections for '{key}'")
    if "." in key:
        parts = []
        node = params
        for tok in key.split("."):
            if isinstance(node, dict):
                if tok not in node:
                    raise KeyError(key)
                parts.append(tok)
                node = node[tok]
            elif isinstance(node, (list, tuple)):
                try:
                    i = int(tok)
                    node = node[i]
                except (ValueError, IndexError):
                    raise KeyError(key) from None
                parts.append(i)
            else:
                raise KeyError(key)
        return tuple(parts)
    raise KeyError(key)


def param_get(family: str, params: dict, key: str):
    node = params
    for step in resolve_path(family, params, key):
        node = node[step]
    return node


def param_set(family: str, params: dict, key: str, value) -> None:
    """In-place set along the same path ``param_get`` reads."""
    path = resolve_path(family, params, key)
    node = params
    for step in path[:-1]:
        node = node[step]
    node[path[-1]] = value


def root_key(key: str) -> str:
    return key.split(".", 1)[0]


# ------------------------------------------------------------------ validation


def _check_value(family: str, key: str, spec: KeySpec, v) -> None:
    if spec.kind is float:
        if not _isnum(v):
            raise _bad(family, key, f"must be a finite number, got {v!r}")
    elif spec.kind is int:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or float(v) != int(v):
            raise _bad(family, key, f"must be an integer, got {v!r}")
    elif spec.kind is str:
        if not isinstance(v, str):
            raise _bad(family, key, f"must be a string, got {v!r}")
        if spec.choices is not None and v.strip().lower() not in spec.choices:
            raise _bad(family, key, f"must be one of {list(spec.choices)}, got {v!r}")
    elif spec.kind is bool:
        if not isinstance(v, bool):
            raise _bad(family, key, f"must be a bool, got {v!r}")
    elif spec.kind is list:
        if not isinstance(v, (list, tuple)):
            raise _bad(family, key, f"must be a list, got {type(v).__name__}")
    elif spec.kind is dict:
        if not isinstance(v, dict):
            raise _bad(family, key, f"must be a mapping, got {type(v).__name__}")
    if spec.kind in (float, int):
        if spec.lo is not None and float(v) < spec.lo:
            raise _bad(family, key, f"{v!r} is below the schema minimum {spec.lo}")
        if spec.hi is not None and float(v) > spec.hi:
            raise _bad(family, key, f"{v!r} is above the schema maximum {spec.hi}")


def _validate_osse_like(design: Design) -> None:
    p = design.params
    fam = design.family
    if fam == "OSSE":
        s = p.get("s", 0.0)
        if s != 0:
            n = p.get("n", 4.0)
            q = p.get("q", 0.995)
            if n <= 0:
                raise _bad(fam, "n", f"must be > 0 while s != 0, got {n!r}")
            if q <= 0:
                raise _bad(fam, "q", f"must be > 0 while s != 0, got {q!r}")
        if "L_mm" in p and p["L_mm"] <= 0:
            raise _bad(fam, "L_mm", f"must be > 0, got {p['L_mm']!r}")
    if fam == "R-OSSE":
        if "tmax" in p and p["tmax"] <= 0:
            raise _bad(fam, "tmax", f"must be > 0, got {p['tmax']!r}")
        if "R_mm" in p and p["R_mm"] <= 0:
            raise _bad(fam, "R_mm", f"must be > 0, got {p['R_mm']!r}")
    if "r0_mm" in p and p["r0_mm"] <= 0:
        raise _bad(fam, "r0_mm", f"must be > 0, got {p['r0_mm']!r}")


def _validate_icw(design: Design) -> None:
    p = design.params
    hs, he = p.get("hold_start"), p.get("hold_end")
    if hs is not None and he is not None and not hs < he:
        raise _bad("ICW", "hold_start", f"must be < hold_end ({hs!r} vs {he!r})")


def _validate_profile(name: str, prof) -> list:
    fam = "FREEFORM"
    if not isinstance(prof, dict):
        raise _bad(fam, name, "must be a mapping with 'points'")
    unknown = set(prof) - _FF_PROFILE_KEYS
    if unknown:
        raise _bad(fam, name, f"unknown profile key(s) {sorted(unknown)} "
                              f"(legal: {sorted(_FF_PROFILE_KEYS)})")
    pts = prof.get("points")
    if not isinstance(pts, (list, tuple)) or not 2 <= len(pts) <= 64:
        raise _bad(fam, f"{name}.points", "must be a list of 2 to 64 rows")
    last_z = -math.inf
    for i, row in enumerate(pts):
        if not isinstance(row, (list, tuple)) or len(row) not in (2, 3) \
                or not all(_isnum(x) for x in row):
            raise _bad(fam, f"{name}.points[{i}]", f"row must be [z, r] or [z, r, angleDeg], got {row!r}")
        z, r = float(row[0]), float(row[1])
        if r <= 0:
            raise _bad(fam, f"{name}.points[{i}]", f"radius must be positive, got {r!r}")
        if not z > last_z:
            raise _bad(fam, f"{name}.points[{i}]",
                       f"z must be strictly increasing (z={z!r} follows {last_z!r})")
        last_z = z
    for ak in ("throatAngleDeg", "mouthAngleDeg"):
        if ak in prof:
            if not _isnum(prof[ak]) or not -90.0 <= float(prof[ak]) <= 90.0:
                raise _bad(fam, f"{name}.{ak}", f"must be in [-90, 90], got {prof[ak]!r}")
    return pts


def _validate_freeform(design: Design) -> None:
    fam = "FREEFORM"
    p = design.params
    for name in ("profileH", "profileV"):
        if name not in p:
            raise _bad(fam, name, "required")
    ptsH = _validate_profile("profileH", p["profileH"])
    ptsV = _validate_profile("profileV", p["profileV"])
    if abs(float(ptsH[0][0]) - float(ptsV[0][0])) > 1e-9 or abs(float(ptsH[-1][0]) - float(ptsV[-1][0])) > 1e-9:
        raise _bad(fam, "profileV", "first and last z must match profileH")
    if abs(float(ptsH[0][1]) - float(ptsV[0][1])) > 1e-6:
        raise _bad(fam, "profileV", "first radius must match profileH (shared throat)")
    cs = p.get("crossSections")
    if cs is None:
        return
    if not 2 <= len(cs) <= 32:
        raise _bad(fam, "crossSections", f"needs 2 to 32 stations, got {len(cs)}")
    last_t = -math.inf
    for i, st in enumerate(cs):
        where = f"crossSections[{i}]"
        if not isinstance(st, dict) or "t" not in st or "shape" not in st:
            raise _bad(fam, where, "station must be a mapping with 't' and 'shape'")
        t = st["t"]
        if not _isnum(t) or not 0.0 <= float(t) <= 1.0:
            raise _bad(fam, f"{where}.t", f"must be in [0, 1], got {t!r}")
        if not float(t) > last_t:
            raise _bad(fam, f"{where}.t", f"must be strictly increasing (t={t!r} follows {last_t!r})")
        last_t = float(t)
        shape = st["shape"]
        if shape not in _FF_SHAPES:
            raise _bad(fam, f"{where}.shape", f"must be one of {list(_FF_SHAPES)}, got {shape!r}")
        if shape == "superellipse" and "exponent" in st:
            e = st["exponent"]
            if not _isnum(e) or not 2.0 <= float(e) <= 16.0:
                raise _bad(fam, f"{where}.exponent", f"superellipse exponent must be in [2, 16], got {e!r}")
        if shape == "rounded_rectangle":
            c = st.get("cornerRadiusMm")
            if not _isnum(c) or float(c) <= 0:
                raise _bad(fam, f"{where}.cornerRadiusMm", f"required and positive, got {c!r}")
    if float(cs[0]["t"]) != 0.0 or float(cs[-1]["t"]) != 1.0:
        raise _bad(fam, "crossSections", "first station must be t=0 and last t=1")
    if cs[0]["shape"] not in ("circle", "ellipse"):
        raise _bad(fam, "crossSections[0].shape", "first shape must be circle or ellipse")


def validate(design: Design) -> None:
    """Raise GeometryInvalidError naming the offending key. No guessing: a key not in the
    family's table is rejected, not passed through."""
    fam = design.family
    if fam not in FAMILY_KEYS:
        raise GeometryInvalidError(f"unknown family {fam!r}; legal: {list(FAMILY_KEYS)}")
    table = FAMILY_KEYS[fam]
    if not isinstance(design.params, dict):
        raise GeometryInvalidError(f"{fam}: params must be a dict")
    hints = _REFUSED_HINTS.get(fam, {})
    for key in design.params:
        if key in table:
            continue
        if key in hints:
            raise _bad(fam, key, hints[key])
        raise _bad(fam, key, f"not a legal {fam} key (legal: {sorted(table)})")
    for key, v in design.params.items():
        _check_value(fam, key, table[key], v)
    if fam in ("OSSE", "R-OSSE"):
        _validate_osse_like(design)
    elif fam == "ICW":
        _validate_icw(design)
    elif fam == "FREEFORM":
        _validate_freeform(design)


# ------------------------------------------------------------------ mesher config


def to_mesher_config(design: Design, mesh: MeshSpec, res_mm: dict, out_path: Path) -> dict:
    """Build the dict ``hornlab_mesher.build_from_config`` consumes.

    DEVIATION FROM THE TASK FILE'S SKETCH (see NOTES_FOR_SENIOR 2026-10-12 task-04): the
    sketch is a flat dict. Measured against hornlab-waveguide-mesher 0.2.4, a TOP-LEVEL
    ``max_triangles`` is silently ignored (the default 18000 applies and a quarter mesh is
    then refused at 4500). Keys must live in their natural section, so this returns the
    sectioned form the mesher's own examples use. Each key's section comes from its KeySpec.
    """
    validate(design)
    table = FAMILY_KEYS[design.family]
    cfg: dict = {"formula": design.family, "mode": "freestanding"}
    sections: dict[str, dict] = {"profile": {}, "cross_section": {}, "mesh": {}, "morph": {},
                                 "gcurve": {}}
    for key, value in design.params.items():
        sec = table[key].section
        value = copy.deepcopy(value)
        if sec == "top":
            cfg[key] = value
        else:
            sections.setdefault(sec, {})[key] = value
    sections["mesh"].update({
        "quadrants": mesh.quadrants,
        "throat_res_mm": res_mm["throat"],
        "mouth_res_mm": res_mm["mouth"],
        "rear_res_mm": res_mm["rear"],
        "max_triangles": int(mesh.max_triangles),
        "allow_large_mesh": bool(mesh.allow_large_mesh),   # False
        "scale_to_metres": True,                           # EXPLICIT, never implicit
    })
    for name, body in sections.items():
        if body:
            cfg[name] = body
    cfg["output"] = {"path": str(out_path)}
    return cfg


def wrap_mesher_error(exc: BaseException) -> GeometryInvalidError:
    """Map a mesher ConfigError / ValueError / MesherError onto GeometryInvalidError, message
    preserved verbatim. Per-azimuth throat stretch gets a pointer at design/custom.py."""
    msg = str(exc)
    if "per-azimuth" in msg or "not supported yet" in msg:
        return GeometryInvalidError(
            f"{msg}  [hornlab_mesher refuses per-azimuth geometry; that gap is the reserved "
            "extension point hornlab_search/design/custom.py]")
    return GeometryInvalidError(msg)
