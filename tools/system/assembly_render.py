"""Render what Boundary Lab actually compiled for one staged horn+cabinet case.

This is an *evidence* render, not a design card: it reads the staged case's own horn
surface (the imported mesh, transformed exactly as BL transforms it) and the compiled
``exterior.msh``, so the picture is the solver geometry, not a schematic.

    .venv\\Scripts\\python.exe tools\\system\\assembly_render.py ^
        --case system_runs\\system\\hf_overhang_2026-11-22\\<case> ^
        --out docs\\evidence\\horn_over_cabinet_2026-11-22\\<name>.png

Panels: front elevation (x-y, where the owner's photo lives), side elevation (z-y),
plan (x-z) and a perspective.  The drawing separates the *front-view silhouette overlap*
from the *solid clearance* on purpose: a mouth may overlap the cabinet outline while the
solids stay apart.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.system.boundarylab import collision  # noqa: E402


def _load(case_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray,
                                    dict, dict, dict]:
    manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))["payload"]

    def _json(value):
        return json.loads(value) if isinstance(value, str) else value

    spec = _json(manifest["spec"])
    clearance = _json(manifest["clearance"])
    pose = _json(spec.get("pose") or {})
    horn = spec["horn"]
    result = _json(manifest.get("result") or {})
    meshes = result.get("meshes") or [] if isinstance(result, dict) else []
    surfaces = [m["path"] for m in meshes if m.get("purpose") == "bem_surface"]
    exteriors = sorted(case_dir.glob("bl_output/*/exterior.msh"))
    body_path = Path(surfaces[0]) if surfaces else (exteriors[0] if exteriors else None)
    if body_path is None:
        raise FileNotFoundError("no compiled exterior mesh in this case")
    horn_surface = collision.transform_surface(
        collision.read_surface(horn["mesh_path"]),
        translation_mm=horn.get("translation_mm", (0.0, 0.0, 0.0)),
        scale_factor=float(horn.get("scale_factor", 1.0)))
    body_surface = collision.read_surface(body_path)
    return (horn_surface.points * 1e3, horn_surface.triangles,
            body_surface.points * 1e3, body_surface.triangles, pose, spec, clearance)


def _body_box(spec: dict) -> tuple[float, float, float, float, float, float]:
    source = spec["source"]
    w, h, d = float(source["width_m"]) * 1e3, float(source["height_m"]) * 1e3, \
        float(source["depth_m"]) * 1e3
    return (-w / 2, -h / 2, -d, w / 2, h / 2, 0.0)


def _poly(ax, pts, tris, axes, color, alpha, zorder, edge_alpha=0.20):
    from matplotlib.collections import PolyCollection

    i, j = axes
    corners = pts[tris][:, :, (i, j)]
    collection = PolyCollection(corners, facecolors=color, edgecolors=(0, 0, 0, edge_alpha),
                                linewidths=0.12, alpha=alpha, zorder=zorder)
    ax.add_collection(collection)


def _rect(ax, x0, y0, x1, y1, *, color="k", lw=1.4, ls="-", label=None, zorder=5):
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color=color, lw=lw, ls=ls,
            label=label, zorder=zorder)


def render(case_dir: Path, out: Path, *, title: str | None = None) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    (horn_pts, horn_tris, body_pts, body_tris, pose, spec,
     clearance) = _load(case_dir)
    x0, y0, z0, x1, y1, z1 = _body_box(spec)
    w, h, d = x1 - x0, y1 - y0, z1 - z0

    fig = plt.figure(figsize=(15.5, 11.0), dpi=130)
    grid = fig.add_gridspec(2, 2, hspace=0.18, wspace=0.14,
                            left=0.06, right=0.985, top=0.845, bottom=0.07)

    # ---- front elevation (the owner's photo): x-y
    ax = fig.add_subplot(grid[0, 0])
    _rect(ax, x0, y0, x1, y1, color="#222222", lw=1.6, label="cabinet")
    _poly(ax, body_pts, body_tris, (0, 1), "#cfd8e3", 0.30, 1)
    _poly(ax, horn_pts, horn_tris, (0, 1), "#2f6fb5", 0.42, 3)
    hb = pose.get("horn_world_bbox_mm") or [0, 0, 0, 0, 0, 0]
    ax.plot([hb[0], hb[3], hb[3], hb[0], hb[0]], [hb[1], hb[1], hb[4], hb[4], hb[1]],
            color="#0b3d75", lw=0.9, ls="--", label="horn bbox (world)", zorder=6)
    ax.axhline(y1, color="#c0392b", lw=0.6, ls=":", zorder=2)
    ax.set_title("Front elevation (x-y): silhouette overlap is not a collision", fontsize=10)
    ax.set_xlabel("x [mm]"); ax.set_ylabel("y [mm]"); ax.set_aspect("equal")

    # ---- side elevation: z-y
    ax = fig.add_subplot(grid[0, 1])
    _rect(ax, z0, y0, z1, y1, color="#222222", lw=1.6, label="cabinet")
    _poly(ax, body_pts, body_tris, (2, 1), "#cfd8e3", 0.30, 1)
    _poly(ax, horn_pts, horn_tris, (2, 1), "#2f6fb5", 0.42, 3)
    ax.plot([hb[2], hb[5], hb[5], hb[2], hb[2]], [hb[1], hb[1], hb[4], hb[4], hb[1]],
            color="#0b3d75", lw=0.9, ls="--", label="horn bbox (world)", zorder=6)
    ax.axvline(0.0, color="#c0392b", lw=0.7, ls=":", label="baffle plane z=0", zorder=2)
    ax.set_title("Side elevation (z-y): how far the mouth hangs forward", fontsize=10)
    ax.set_xlabel("z [mm] (forward +)"); ax.set_ylabel("y [mm]"); ax.set_aspect("equal")

    # ---- plan: x-z
    ax = fig.add_subplot(grid[1, 0])
    _rect(ax, x0, z0, x1, z1, color="#222222", lw=1.6, label="cabinet")
    _poly(ax, body_pts, body_tris, (0, 2), "#cfd8e3", 0.30, 1)
    _poly(ax, horn_pts, horn_tris, (0, 2), "#2f6fb5", 0.42, 3)
    ax.axhline(0.0, color="#c0392b", lw=0.7, ls=":")
    ax.set_title("Plan (x-z)", fontsize=10)
    ax.set_xlabel("x [mm]"); ax.set_ylabel("z [mm] (forward +)"); ax.set_aspect("equal")

    # ---- perspective
    ax = fig.add_subplot(grid[1, 1], projection="3d")
    _perspective(ax, horn_pts, horn_tris, "#2f6fb5")
    _perspective(ax, body_pts, body_tris, "#b8c2cf", alpha=0.30)
    ax.set_title("Perspective", fontsize=10)
    ax.set_xlabel("x"); ax.set_ylabel("z"); ax.set_zlabel("y")
    ax.view_init(elev=18, azim=-58)
    _equal_3d(ax, np.vstack([horn_pts, body_pts]))

    # ---- caption
    figure_title = title or case_dir.name
    plt.suptitle(f"HornFab / Boundary Lab compiled assembly — {figure_title}", fontsize=12,
                 y=0.978)
    txt = _caption(pose, clearance, w, h, d)
    fig.text(0.06, 0.945, txt, fontsize=9.0, family="DejaVu Sans Mono", va="top")
    handles, labels = fig.axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, frameon=False, fontsize=8.5,
               bbox_to_anchor=(0.5, 0.005))

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


def _perspective(ax, pts, tris, color, alpha=0.95):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    corners = pts[tris]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    ok = lengths > 1e-12
    normals[ok] /= lengths[ok, None]
    light = np.array([0.35, 0.55, -0.76])
    shade = np.clip(0.35 + 0.65 * np.abs(normals @ light), 0.0, 1.0)
    base = np.array(matplotlib_color(color))
    face = np.clip(base[None, :] * shade[:, None], 0.0, 1.0)
    collection = Poly3DCollection(corners[ok], facecolors=face[ok], edgecolors="none",
                                  alpha=alpha)
    ax.add_collection3d(collection)


def matplotlib_color(name: str) -> tuple[float, float, float]:
    import matplotlib.colors as mcolors

    return mcolors.to_rgb(name)


def _equal_3d(ax, pts: np.ndarray) -> None:
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    centre = (lo + hi) / 2.0
    span = max(float((hi - lo).max()) * 0.62, 1.0)
    ax.set_xlim(centre[0] - span, centre[0] + span)
    ax.set_ylim(centre[2] - span, centre[2] + span)
    ax.set_zlim(centre[1] - span, centre[1] + span)


def _caption(pose: dict, clearance: dict, w: float, h: float, d: float) -> str:
    t = pose.get("translation_mm") or [0, 0, 0]
    sil = pose.get("silhouette") or {}
    gap = clearance.get("min_distance_m")
    exact = clearance.get("distance_exact")
    gap_txt = "n/a" if gap is None else f"{float(gap) * 1e3:.3f} mm" + ("" if exact else " (>= cutoff)")
    return (
        f"cabinet  W x H x D = {w:.0f} x {h:.0f} x {d:.0f} mm   (baffle z=0, body z<0)\n"
        f"horn     translation (x,y,z) = ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f}) mm   "
        f"layout={pose.get('layout')}  support={pose.get('support')}\n"
        f"solid    clearance = {clearance.get('status')}  min surface distance = {gap_txt}  "
        f"method={clearance.get('method')}\n"
        f"drawing  front-view overlap = {sil.get('front_view_x_overlap_mm', 0):.1f} mm (x) x "
        f"{sil.get('front_view_y_overlap_mm', 0):.1f} mm (y)   "
        f"mouth lower lip below cabinet top = "
        f"{sil.get('mouth_lower_lip_below_top_mm', 0):.1f} mm"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--case", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--title", default=None)
    args = parser.parse_args(argv)
    case_dir = Path(args.case)
    out = render(case_dir, Path(args.out), title=args.title)
    print(json.dumps({"ok": True, "out": str(out)}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
