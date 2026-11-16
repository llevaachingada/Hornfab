"""GUI preview helper for the opt-in bridge typologies.

The GUI's normal preview path calls the stock ``grid`` generator. The three 2026-11-15 home
bridge cells (``rosse_rect``, ``rolled_rect_pucker``, ``crowe_panel``) only materialize after
their own CLI installs a process-local adapter. This helper runs in a fresh subprocess, installs
exactly one adapter, and then calls the normal GUI preview code. The parent GUI never mutates its
own ``grid`` module, and ``examples/catalog.yaml`` stays the stock runnable allowlist.

Usage (from the GUI data layer; JSON on stdout):
  .venv\\Scripts\\python.exe tools/geometry/gui_preview.py \
      --cli rosse_rect_cli --config hl__rosse_rect_cd_v7 --root . --detail 2d [--brief NAME] [--knobs '{...}']
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install(cli: str):
    module = importlib.import_module(f"tools.geometry.{cli}")
    module.install()
    return module


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", required=True,
                    choices=("rosse_rect_cli", "rolled_rect_cli", "crowe_panel_cli",
                             "section_pucker_cli"))
    ap.add_argument("--config", required=True)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--detail", default="2d", choices=("2d", "3d"))
    ap.add_argument("--brief", default=None)
    ap.add_argument("--knobs", default=None, help="JSON object of knob overrides")
    args = ap.parse_args(argv)

    bridge = _install(args.cli)
    from tools.geometry import rolled_rect_cli as base
    from hornlab_search.design.generators import grid

    original_points = grid.grid_points
    original_outer = grid.grid_outer_points
    cache: dict = {}

    def points(spec, knobs, brief, **kwargs):
        shape = base._shape(spec, knobs)
        if args.cli == "crowe_panel_cli":
            from tools.geometry import crowe_panel
            inner, meta = bridge._points(spec, knobs, brief)
            outer = crowe_panel.outer_points(inner, shape)
        elif args.cli == "section_pucker_cli":
            from tools.geometry import section_pucker
            inner, meta = bridge._points(spec, knobs, brief)
            outer = section_pucker.outer_points(inner, shape)
        else:
            inner, meta = base._points(spec, knobs, brief)
            outer = original_outer(inner, float(shape["wall_thickness_mm"]))
        cache.update(inner=inner, outer=outer, meta=meta)
        return inner, meta

    def outer(inner, wall_mm, **kwargs):
        if "outer" in cache:
            return cache["outer"]
        return original_outer(inner, wall_mm, **kwargs)

    grid.grid_points = points
    grid.grid_outer_points = outer

    # The normal preview code must not try to spawn this helper again.
    os.environ["HORNLAB_GUI_BRIDGE_PREVIEW"] = "1"
    from hornlab_search.gui import data as gui_data

    q = {"detail": [args.detail]}
    if args.brief:
        q["brief"] = args.brief
    if args.knobs:
        q["knobs"] = args.knobs
    try:
        payload = gui_data.preview_shape(Path(args.root).resolve(), args.config, q)
    except Exception as exc:  # noqa: BLE001 - return a readable preview error, never a traceback page
        payload = {
            "available": False,
            "reason": f"bridge preview failed: {type(exc).__name__}: {exc}",
            "notes": [f"bridge preview failed: {type(exc).__name__}: {exc}"],
            "section": {"h": {"inner": [], "outer": []}, "v": {"inner": [], "outer": []}},
            "mouth": {"inner": [], "outer": []},
            "envelope": {"available": False, "reason": "bridge preview failed"},
            "shape3d": {"available": False, "reason": "bridge preview failed"},
            "slow": True,
            "timings_ms": {},
        }
    print(json.dumps(payload, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
