"""Explicit entry point for the separate, versioned section-based H/V relief study.

Rebind the existing opt-in adapter in this process only; queued rolled-rectangle
jobs and the installed HornLab packages are unchanged. All four source inputs
participate in recipe identity, with line endings normalized for Git checkout.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.geometry import section_pucker as crowe_panel, rolled_rect, rolled_rect_cli as bridge


def implementation_digest():
    h = hashlib.sha256()
    for path in (Path(rolled_rect.__file__), Path(bridge.__file__), Path(crowe_panel.__file__), Path(__file__), crowe_panel.REFERENCE, Path(crowe_panel.base.__file__)):
        data = path.read_bytes().replace(b"\r\n", b"\n")
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def _points(spec, knobs, brief):
    bridge._check_rows(spec, brief)
    shape = bridge._shape(spec, knobs)
    try:
        inner, meta = crowe_panel.make_grid(shape, brief)
        outer = crowe_panel.outer_points(inner, shape)
        bridge.grid.check_self_approach(inner, outer, shape['wall_thickness_mm'])
        both = np.concatenate((inner.reshape(-1, 3), outer.reshape(-1, 3)))
        ext = [2*np.max(np.abs(both[:, 0])), 2*np.max(np.abs(both[:, 1])), np.ptp(both[:, 2])]
        for actual, key in zip(ext, ('max_mouth_w_mm','max_mouth_h_mm','max_depth_mm')):
            limit = (brief.get('envelope') or {}).get(key)
            if limit is not None and actual > limit:
                bridge._error(f'invalid_envelope: {key} {actual:.3f} exceeds {limit}')
        meta.update(mouth_w_mm=float(ext[0]), mouth_h_mm=float(ext[1]), x_span_mm=float(ext[2]),
                    implementation_sha256=implementation_digest())
        return inner, meta
    except (KeyError, TypeError, ValueError) as exc:
        bridge._error(f'section study: {exc}')


def install():
    if bridge._INSTALLED:
        if bridge.geometry is crowe_panel:
            return
        raise RuntimeError("cannot mix geometry entry points in the same process")
    bridge.geometry = crowe_panel
    bridge.KINDS = {"section_pucker"}
    bridge.SHAPE_KNOBS = crowe_panel.SHAPE_KEYS-{ "n_phi", "n_s", "wall_thickness_mm" }
    bridge.implementation_digest = implementation_digest
    bridge._points = _points
    bridge.install()
    # Supply the same reconstructed solid exterior in the existing mesher route.
    # Unrelated point grids delegate unchanged; installed packages are untouched.
    from hornlab_search.mesh import grid_build
    original_resolve = grid_build._resolve_grid
    def resolve(block, *, enclosure=None):
        meta = block.get('meta') or {}
        if meta.get('construction_label') == crowe_panel.SCHEMA:
            if enclosure is not None:
                raise ValueError('section-study solid body cannot be combined with an enclosure')
            block = {**block, 'outer_points': crowe_panel.outer_points(block['inner_points'], meta['shape'])}
        return original_resolve(block, enclosure=enclosure)
    grid_build._resolve_grid = resolve


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "verify-night":
        from tools.geometry import verify_rolled_rect_night as verifier
        verifier.WRAPPER = Path(__file__).resolve()
        return verifier.main(argv[1:])
    install()
    return bridge.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
