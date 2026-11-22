"""Versioned GRID adapter for the measured sculpted R/K meridians."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import math
from pathlib import Path

import numpy as np
from hornlab_mesher.icw.checks import meridian_self_intersects

from ...geometry import _sculpted_rosse_v1 as sculpt
from . import lame_shell
from .registry import GeneratorError

KIND = "sculpted_rosse_meridians_v1"
SCHEMA = "sculpted-rosse-pilot-v1"
SPEC_KEYS = {"rows", "n_phi", "n_s", "wall_thickness_mm", "span", "size_policy"}
R_KEYS = {"g_sweep", "g_diagonal_delta_deg", "g_aperture_scale"}
K_KEYS = {"g_h_setback_mm", "g_v_projection_mm"}


def is_family_spec(spec):
    return isinstance(spec, dict) and isinstance(spec.get("rows"), dict) and spec["rows"].get("type") == KIND


def implementation_digest():
    import hornlab_mesher.profile_formulas as formulas

    h = sha256()
    for module in (__file__, sculpt.__file__, lame_shell.__file__, formulas.__file__):
        data = Path(module).read_bytes().replace(b"\r\n", b"\n")
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def _inputs(block):
    if not is_family_spec(block) or set(block) - SPEC_KEYS - {"knobs"}:
        raise GeneratorError("invalid sculpted R-OSSE recipe")
    if (block.get("span") != "quarter" or block.get("size_policy") != "report_only"
            or block.get("n_phi") != 49 or block.get("n_s") != 96 or block.get("wall_thickness_mm") != 3.0):
        raise GeneratorError("sculpted pilot requires the recorded quarter 49 by 97 grid and 3 mm shell")
    rows = block["rows"]
    if set(rows) != {"type", "body", "finish_start", "schema", "implementation_sha256", "driver"}:
        raise GeneratorError("unexpected sculpted rows fields")
    if rows["schema"] != SCHEMA or rows["implementation_sha256"] != implementation_digest():
        raise GeneratorError("sculpted generator differs from saved recipe")
    try:
        body = dict(rows["body"])
        for key in ("angle_deg", "apex_shift", "apex_radius", "bend"):
            body[key] = sculpt.Planes(**body[key])
        body = sculpt.Body(**body)
        start = sculpt.Planes(**rows["finish_start"])
        knobs = block["knobs"]
        if set(knobs) not in (R_KEYS, K_KEYS) or not all(math.isfinite(v) for v in knobs.values()):
            raise ValueError("expected one finite R or K knob set")
        return body, start, knobs, rows["driver"]
    except (TypeError, ValueError, KeyError) as exc:
        raise GeneratorError(f"invalid sculpted recipe: {exc}") from exc


def _source(brief):
    driver = brief.get("driver", {})
    source = brief.get("source", {})
    if (brief.get("symmetry") != "hv" or driver.get("exit_radius_mm") != 18
            or driver.get("exit_angle_deg") != 2 or source.get("cap", "auto") != "auto"):
        raise GeneratorError("sculpted pilot requires the 36 mm, 2 degree auto-cap H/V source")
    return {"radius_mm": 18.0, "angle_deg": 2.0, "cap": "auto"}


def design_params(spec, knobs, brief):
    extra = set(spec) - SPEC_KEYS - {"name", "seed_policy"}
    if extra or not is_family_spec(spec):
        raise GeneratorError(f"invalid sculpted generator fields: {sorted(extra)}")
    recipe = {key: deepcopy(spec[key]) for key in SPEC_KEYS}
    recipe["rows"].update(schema=SCHEMA, implementation_sha256=implementation_digest(), driver=_source(brief))
    recipe["knobs"] = dict(knobs)
    resolve_grid(recipe, brief)
    return {"grid": recipe}


def validate_grid_params(block):
    _inputs(block)


def validate_search_config(spec, seed, bounds, brief):
    if set(seed) != set(bounds):
        raise GeneratorError("sculpted pilot bounds must match the explicit seed knobs")
    for key, bound in bounds.items():
        if bound.log or not bound.lo <= seed[key] <= bound.hi:
            raise GeneratorError(f"{key}: expected linear bounds containing the seed")
    design_params(spec, seed, brief)


def _shapes(body, start, knobs):
    if set(knobs) == K_KEYS:
        h, v = knobs["g_h_setback_mm"], knobs["g_v_projection_mm"]
        return body, sculpt.Finish(axial_mm=sculpt.Planes(-h, -0.375 * h, v), start_arc=start)

    sweep = knobs["g_sweep"]
    # A quadratic uses the measured R2, R3 and R4 offsets at -1, 0 and +1.
    a = body.angle_deg
    angle = sculpt.Planes(a.h + .5 * sweep,
                          a.d - .85 * sweep + .65 * sweep**2 + knobs["g_diagonal_delta_deg"],
                          a.v - 2.6 * sweep + .4 * sweep**2)
    scale = knobs["g_aperture_scale"]
    return replace(body, width_mm=body.width_mm * scale, height_mm=body.height_mm * scale,
                   angle_deg=angle), sculpt.Finish()


def _check_surface(inner, outer):
    from .grid import check_self_approach

    dz = np.diff(inner[:, :, 2], axis=1)
    forward = dz > 1e-8
    if (np.any(~forward[:, 0]) or np.any(forward[:, -1])
            or np.any((~forward[:, :-1]) & forward[:, 1:])):
        raise ValueError("expected one forward apex and no secondary turn")
    for sheet in (inner, outer):
        for meridian in sheet:
            if meridian_self_intersects(meridian[:, 2], np.linalg.norm(meridian[:, :2], axis=1)):
                raise ValueError("self-intersecting sculpted meridian")
    for side in (0, 1):
        normals = [np.cross(np.diff(sheet, axis=0)[:, side:side + inner.shape[1] - 1],
                            np.diff(sheet, axis=1)[side:side + inner.shape[0] - 1])
                   for sheet in (inner, outer)]
        if np.any(np.sum(normals[0] * normals[1], axis=-1) <= 0):
            raise ValueError("degenerate or reversed sculpted wall cell")
    return check_self_approach(inner, outer, 3.0)


def resolve_grid(block, brief):
    body, start, knobs, driver = _inputs(block)
    if driver != _source(brief):
        raise GeneratorError("sculpted source differs from saved recipe")
    try:
        body, finish = _shapes(body, start, knobs)
        inner, outer = sculpt.surface(body, finish, radius_mm=driver["radius_mm"],
                                      source_angle_deg=driver["angle_deg"], wall_mm=3.0,
                                      collar_mm=(8, 42), n_phi=block["n_phi"], n_s=block["n_s"] + 1)
        clearance = _check_surface(inner, outer)
    except (ValueError, FloatingPointError) as exc:
        raise GeneratorError(f"invalid sculpted meridian: {exc}") from exc
    combined = np.concatenate((inner.reshape(-1, 3), outer.reshape(-1, 3)))
    meta = {"quarter": True, "row_span": "quarter", "source_auto_angle_deg": driver["angle_deg"],
            "throat_radius_mm": driver["radius_mm"], "mouth_w_mm": 2 * float(combined[:, 0].max()),
            "mouth_h_mm": 2 * float(combined[:, 1].max()), "x_span_mm": float(np.ptp(combined[:, 2])),
            "sampled_clearance_mm": clearance, "construction_label": SCHEMA, "size_policy": "report_only"}
    return {"inner_points": inner, "outer_points": outer, "meta": meta}

