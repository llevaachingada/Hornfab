"""Recipe metadata v2 (WP 0.9): facts a recipe needs that the stored design never named.

ADDITIVE and NON-IDENTITY. ``recipe_metadata`` returns a plain JSON dict that is written inside
a design's generator provenance (``design.json["generator"]["recipe_meta"]``). It is never an
input of ``Design.hash()``, the mesh hash, the solve hash or ``config_sha``; those are computed
from ``family`` + ``params``, the mesh spec and the config ``raw`` only, so adding or changing
this block cannot move any identity (tested in ``tests/test_design_recipe_meta.py``).

What it records, each with how it was resolved (``source``), because a recipe that omits a
mesher-default knob silently depends on the installed mesher's default:

* ``termination``: ``{"kind", "source"}`` where knowable from the family or generator spec;
  otherwise ``kind: None, source: "not_recorded"`` (never guessed).
* ``wall_thickness_mm``: ``{"value", "source"}``, the shell thickness the mesher actually
  receives (mesher default 6.0 mm freestanding, 0 for enclosure / bare / infinite-baffle; the
  point-grid route defaults to 3.0 mm and is 0 under an enclosure).
* ``source_cap``: ``{"shape", "radius_param", "radius_mm", "curvature", "angle_deg", "source"}``.
  ``shape`` 1 is the mesher's rounded cap, ``curvature`` its ``source_curv`` (0 = default sign).
  ``radius_mm`` is the RESOLVED cap radius only on the point-grid route
  (``mean ring-0 radius / sin(angle)``, as ``hornlab_mesher`` computes it); on the formula route
  it is ``None`` (``radius_param`` -1 means automatic) because the mesher resolves it internally.

The digest rule for the whole record (``record_digest``, ``kernel_sha256``) is an owner decision
and is deliberately NOT here.
"""
from __future__ import annotations

import math
from typing import Any

SCHEMA = "recipe_meta_v2"

#: hornlab_mesher defaults, read from the installed package (config_builder.py / geometry.py).
MESHER_FREESTANDING_WALL_MM = 6.0
MESHER_DEFAULT_A0_DEG = 15.5
MESHER_SOURCE_SHAPE = 1
MESHER_SOURCE_CURV = 0
MESHER_SOURCE_RADIUS_PARAM = -1.0       # automatic
GRID_DEFAULT_WALL_MM = 3.0               # mesh/grid_build.DEFAULT_WALL_THICKNESS_MM
_NO_WALL_MODES = {"bare", "enclosure", "infinite-baffle"}
_MODE_ALIASES = {"ib": "infinite-baffle", "baffle": "infinite-baffle", "enclosed": "enclosure",
                 "inner": "bare", "open": "bare", "free": "freestanding",
                 "free-standing": "freestanding"}


def _num(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if math.isfinite(v) else None


def _termination(design, gen: dict | None) -> dict:
    p = design.params or {}
    fam = getattr(design, "family", None)
    if fam == "ICW" and isinstance(p.get("termination"), str):
        return {"kind": p["termination"], "source": "family_param"}
    if fam == "OSSE":
        s = _num(p.get("s"))
        if s is not None:
            return {"kind": "osse_qns_rounded" if s != 0.0 else "osse_plain_flare",
                    "source": "family_param(s)"}
    if gen:
        spec = gen.get("spec") if isinstance(gen.get("spec"), dict) else gen
        for key in ("termination", "termination_kind"):
            if isinstance(spec.get(key), str):
                return {"kind": spec[key], "source": f"generator_spec.{key}"}
    return {"kind": None, "source": "not_recorded"}


def _mode(design, mounting) -> str:
    raw = "enclosure" if mounting is not None else str(
        (design.params or {}).get("mode", "freestanding"))
    return _MODE_ALIASES.get(raw, raw)


def recipe_metadata(design, *, mounting: dict | None = None, gen: dict | None = None,
                    grid_inner=None, grid_meta: dict | None = None) -> dict:
    """The WP 0.9 metadata block for one design. Never raises; unknowns are explicit ``None``.

    ``grid_inner`` / ``grid_meta`` (optional) are the point-grid ``inner_points`` (mm) and meta
    the mesher will receive; with them the grid source-cap radius is resolved exactly as the
    mesher does.
    """
    try:
        params = design.params or {}
        mode = _mode(design, mounting)
        meta: dict[str, Any] = {"schema": SCHEMA, "mode": mode,
                                "termination": _termination(design, gen)}
        if "grid" in params:
            block = params["grid"] if isinstance(params["grid"], dict) else {}
            wv = _num(block.get("wall_thickness_mm"))
            if mode == "enclosure":
                wall = {"value": 0.0, "source": "enclosure_topology"}
            elif wv is not None:
                wall = {"value": wv, "source": "recipe"}
            else:
                wall = {"value": GRID_DEFAULT_WALL_MM, "source": "grid_build_default"}
            angle = _num((grid_meta or {}).get("source_auto_angle_deg"))
            cap = {"shape": MESHER_SOURCE_SHAPE, "radius_param": MESHER_SOURCE_RADIUS_PARAM,
                   "curvature": MESHER_SOURCE_CURV, "angle_deg": angle, "radius_mm": None,
                   "source": "point_grid_meta" if angle is not None else "unresolved"}
            if grid_inner is not None and angle:
                import numpy as np
                ring = np.asarray(grid_inner, dtype=float)[:, 0, :]
                gm = grid_meta or {}
                span = str(gm.get("row_span") or gm.get("span") or "quarter")
                closed = (not bool(gm.get("quarter", True))) and not bool(
                    gm.get("half_model", False)) and span != "half_xz"
                center = ring.mean(axis=0)
                if not closed:               # mesher: an open grid is centred on the axis
                    center[:2] = 0.0
                rad = np.linalg.norm((ring - center)[:, :2], axis=1)
                rad = rad[rad > 1e-9]
                s = abs(math.sin(math.radians(angle)))
                if rad.size and s > 1e-9:
                    cap["radius_mm"] = float(rad.mean() / s)
                    cap["source"] = "point_grid_resolved"
        else:
            wv = _num(params.get("wall_thickness_mm"))
            if mode in _NO_WALL_MODES:
                wall = {"value": 0.0, "source": f"mesher_forces_zero({mode})"}
            elif wv is not None:
                wall = {"value": wv, "source": "recipe"}
            else:
                wall = {"value": MESHER_FREESTANDING_WALL_MM, "source": "mesher_default"}
            a0 = _num(params.get("a0_deg"))
            has_default = design.family not in ("ICW", "FREEFORM")
            cap = {"shape": MESHER_SOURCE_SHAPE, "radius_param": MESHER_SOURCE_RADIUS_PARAM,
                   "curvature": MESHER_SOURCE_CURV, "radius_mm": None,
                   "angle_deg": a0 if a0 is not None else
                   (MESHER_DEFAULT_A0_DEG if has_default else None),
                   "source": "recipe(a0_deg)" if a0 is not None else
                   ("mesher_default(a0)" if has_default else "unresolved")}
        meta["wall_thickness_mm"] = wall
        meta["source_cap"] = cap
        return meta
    except Exception as exc:  # noqa: BLE001 - metadata is bookkeeping, never a failure
        return {"schema": SCHEMA, "error": f"{type(exc).__name__}: {exc}"}
