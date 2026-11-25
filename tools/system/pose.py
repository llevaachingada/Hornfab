"""Resolve one horn-over-cabinet pose from real geometry and prove it is legal.

Usage (HornLab venv)::

    .venv\\Scripts\\python.exe tools\\system\\pose.py ^
        --horn-mesh <full-domain horn .msh> ^
        --cabinet-mm 320 500 360 ^
        --layout seated_overhang --dz-mm 0 --clearance-mm 3 ^
        --out runs\\poses\\overhang_dz000.json

``--layout above`` keeps the older conservative rule (the whole envelope clears the top
face).  ``seated_overhang`` is the owner's arrangement: the horn sits on the cabinet and
its mouth may hang forward past the baffle plane, overlapping the box in the front view,
as long as the solids stay apart.  ``dy_mm=None`` derives the closest buildable height
for the requested ``dz_mm``.

The written JSON is the single source of the placement; pass it to::

    hornlab-search system reference prepare --pose <file> ...

Nothing here stages a project or starts a solve.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.system.assembly_pose import (  # noqa: E402
    LAYOUT_ABOVE,
    LAYOUT_SEATED_OVERHANG,
    PlacementIllegal,
    resolve_pose,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--horn-mesh", required=True)
    parser.add_argument("--cabinet-mm", required=True, nargs=3, type=float,
                        metavar=("W", "H", "D"))
    parser.add_argument("--layout", choices=(LAYOUT_ABOVE, LAYOUT_SEATED_OVERHANG),
                        default=LAYOUT_SEATED_OVERHANG)
    parser.add_argument("--dy-mm", type=float, default=None,
                        help="explicit vertical offset (default: derive the closest legal)")
    parser.add_argument("--dz-mm", type=float, default=0.0)
    parser.add_argument("--dx-mm", type=float, default=0.0)
    parser.add_argument("--clearance-mm", type=float, default=3.0)
    parser.add_argument("--design-hash", default="")
    parser.add_argument("--compiled-exterior", default=None,
                        help="optional BL exterior.msh to verify the box model against")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    width, height, depth = args.cabinet_mm
    try:
        pose = resolve_pose(
            args.horn_mesh,
            cabinet={"external_width_mm": width, "external_height_mm": height,
                     "external_depth_mm": depth},
            dz_mm=args.dz_mm, dy_mm=args.dy_mm, dx_mm=args.dx_mm,
            layout=args.layout, clearance_mm=args.clearance_mm,
            horn_design_hash=args.design_hash,
            compiled_exterior=args.compiled_exterior,
        )
    except (PlacementIllegal, FileNotFoundError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 1

    payload = pose.to_dict() | {"ok": True}
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print(json.dumps({
            "ok": True,
            "out": str(out),
            "geometry_id": pose.geometry_id,
            "translation_mm": list(pose.translation_mm),
            "support": pose.support,
            "min_distance_mm": (None if pose.clearance.get("min_distance_m") is None
                                else round(float(pose.clearance["min_distance_m"]) * 1e3, 3)),
            "front_view_y_overlap_mm": pose.silhouette.get("front_view_y_overlap_mm"),
        }, indent=2))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
