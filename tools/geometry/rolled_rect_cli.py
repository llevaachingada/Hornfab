"""Opt-in CLI bridge for the original rolled-rectangle experiment.

The installed search/meshing pipeline remains unchanged. Saved recipes carry a
source digest and are intentionally rejected by the unmodified stock CLI.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.geometry import rolled_rect as geometry
from hornlab_search.design.generators import grid

KINDS = {"rolled_rect", "rolled_rect_pucker"}
SPEC_KEYS = {"name", "rows", "n_phi", "n_s", "wall_thickness_mm", "span", "knobs"}
SHAPE_KNOBS = geometry.SHAPE_KEYS - {"n_phi", "n_s", "wall_thickness_mm"}
_INSTALLED = False


def implementation_digest():
    h = hashlib.sha256()
    for path in (Path(geometry.__file__), Path(__file__)):
        # Git may normalize Windows CRLF on checkout; that does not change geometry.
        data = path.read_bytes().replace(b"\r\n", b"\n")
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def _custom(spec):
    return isinstance(spec, dict) and isinstance(spec.get("rows"), dict) and spec["rows"].get("type") in KINDS


def _error(message):
    raise grid.registry.GeneratorError(message)


def _shape(spec, knobs):
    extra = set(spec) - SPEC_KEYS
    if extra:
        _error(f"rolled_rect: unknown spec keys: {sorted(extra)}")
    if spec.get("span", "quarter") != "quarter":
        _error("rolled_rect requires quarter span")
    expected = {"g_" + k for k in SHAPE_KNOBS}
    if set(knobs) != expected:
        _error(f"rolled_rect knobs: missing={sorted(expected-set(knobs))}, unknown={sorted(set(knobs)-expected)}")
    try:
        shape = {key: knobs["g_" + key] for key in SHAPE_KNOBS}
        shape.update({key: spec[key] for key in ("n_phi", "n_s", "wall_thickness_mm")})
        geometry.validate_shape(shape)
        if spec["rows"]["type"] == "rolled_rect" and (shape["pucker_h_mm"] or shape["pucker_v_mm"]):
            _error("rolled_rect base requires zero pucker; use rolled_rect_pucker")
        return shape
    except (KeyError, TypeError, ValueError) as exc:
        _error(f"rolled_rect shape: {exc}")


def _check_rows(spec, brief=None, *, require_digest=False):
    rows = spec["rows"]
    if set(rows) - {"type", "schema", "implementation_sha256", "driver"}:
        _error("rolled_rect: unexpected rows metadata")
    digest = rows.get("implementation_sha256")
    if require_digest and not digest:
        _error("rolled_rect: persisted recipe lacks implementation digest")
    if digest is not None and (digest != implementation_digest() or rows.get("schema") != geometry.SCHEMA):
        _error("rolled_rect: implementation digest or schema differs from persisted recipe")
    if brief is not None and "driver" in rows:
        driver = brief.get("driver") or {}
        expected = {k: driver.get(k) for k in ("exit_radius_mm", "exit_angle_deg")}
        if rows["driver"] != expected:
            _error("rolled_rect: driver differs from persisted recipe")
    if require_digest and "driver" not in rows:
        _error("rolled_rect: persisted recipe lacks driver")


def _points(spec, knobs, brief):
    _check_rows(spec, brief)
    shape = _shape(spec, knobs)
    try:
        points, meta = geometry.make_grid(shape, brief)
        outer = grid.grid_outer_points(points, shape["wall_thickness_mm"])
        import numpy as np
        both = np.concatenate((points.reshape(-1, 3), outer.reshape(-1, 3)))
        ext = (2 * float(np.max(np.abs(both[:, 0]))),
               2 * float(np.max(np.abs(both[:, 1]))),
               float(np.max(both[:, 2]) - np.min(both[:, 2])))
        envelope = brief.get("envelope") or {}
        for actual, key in zip(ext, ("max_mouth_w_mm", "max_mouth_h_mm", "max_depth_mm")):
            limit = envelope.get(key)
            if limit is not None and actual > float(limit):
                _error(f"invalid_envelope: {key} {actual:.3f} exceeds {limit}")
        meta.update(mouth_w_mm=ext[0], mouth_h_mm=ext[1], x_span_mm=ext[2],
                    implementation_sha256=implementation_digest())
        return points, meta
    except grid.registry.GeneratorError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        _error(f"rolled_rect: {exc}")


def install():
    global _INSTALLED
    if _INSTALLED:
        return
    original_design = grid.design_params
    original_validate = grid.validate_grid_params
    original_points = grid.rows_grid_points
    original_extents = grid.envelope_extents

    def design_params(spec, knobs, brief):
        if not _custom(spec):
            return original_design(spec, knobs, brief)
        _points(spec, knobs, brief)
        driver = brief["driver"]
        rows = {"type": spec["rows"]["type"], "schema": geometry.SCHEMA,
                "implementation_sha256": implementation_digest(),
                "driver": {k: driver[k] for k in ("exit_radius_mm", "exit_angle_deg")}}
        return {"grid": {"rows": rows, "n_phi": spec["n_phi"], "n_s": spec["n_s"],
                         "wall_thickness_mm": spec["wall_thickness_mm"], "knobs": dict(knobs)}}

    def validate_grid_params(block):
        if not _custom(block):
            return original_validate(block)
        _check_rows(block, require_digest=True)
        _shape(block, block.get("knobs") or {})

    def rows_grid_points(spec, knobs, brief, prefix="g"):
        if not _custom(spec):
            return original_points(spec, knobs, brief, prefix=prefix)
        if prefix != "g":
            _error("rolled_rect requires g knob prefix")
        return _points(spec, knobs, brief)

    def envelope_extents(spec, knobs, brief):
        if not _custom(spec):
            return original_extents(spec, knobs, brief)
        _, meta = _points(spec, knobs, brief)
        return meta["mouth_w_mm"], meta["mouth_h_mm"], meta["x_span_mm"]

    grid.design_params = design_params
    grid.validate_grid_params = validate_grid_params
    grid.rows_grid_points = rows_grid_points
    grid.envelope_extents = envelope_extents
    _INSTALLED = True


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    install()
    if argv and argv[0] == "shape-check":
        from tools import shape_check
        return shape_check.main(argv[1:])
    if argv and argv[0] == "preflight":
        from tools import search_preflight
        return search_preflight.main(argv[1:])
    from hornlab_search import cli
    return cli.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
