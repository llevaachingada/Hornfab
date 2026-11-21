"""Render CPU-only comparison sheets for sampled horn surfaces.

Manifest: {"cases": [{"id": "R0", "label": "Reference", "surface":
"path/to/surface.npz", "mesh": null}, ...]}. Paths are relative to the
repository root. NPZ contains inner and outer [phi, station, xyz] in mm;
phi runs H to V. The first case, or the case with id R0, is the reference.
Views use ASCII MSH 2.x meshes in metres when supplied, mirroring axes on
which the mesh occupies only one side of the origin. Other plots use samples.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hornlab_search.mesh.build import read_msh_summary

COLORS = tuple(plt.get_cmap("tab20").colors[::2]) + ("#6b491b",)


def read_cases(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = []
    for row in data["cases"]:
        if not row.get("surface"):
            print(f"Skipping {row['id']}: no sampled surface", file=sys.stderr)
            continue
        with np.load(ROOT / row["surface"], allow_pickle=False) as f:
            inner, outer = (np.array(f[k], dtype=float) for k in ("inner", "outer"))
        if (
            inner.ndim != 3
            or inner.shape[-1] != 3
            or inner.shape != outer.shape
            or min(inner.shape[:2]) < 3
            or not np.isfinite(inner).all()
            or not np.isfinite(outer).all()
        ):
            raise ValueError(
                f"{row['id']}: expected finite inner and outer arrays [phi, station, 3], matching and at least 3x3"
            )
        cases.append((row, inner, outer))
    if not cases:
        raise ValueError("No cases with sampled surfaces")
    return cases


def section(grid, angle):
    # Interpolate by each station's actual polar angle; grids can be nonuniform.
    phi = np.unwrap(np.arctan2(grid[:, :, 1], grid[:, :, 0]), axis=0)
    result = []
    for j in range(grid.shape[1]):
        order = np.argsort(phi[:, j])
        result.append([np.interp(angle, phi[order, j], grid[order, j, k]) for k in range(3)])
    return np.array(result)


def sample_arc_sections(grid, fractions):
    """Give every meridian the same normalized arc fractions for section plots."""
    arc = np.column_stack(
        (np.zeros(len(grid)), np.cumsum(np.linalg.norm(np.diff(grid, axis=1), axis=2), axis=1))
    )
    arc /= arc[:, -1:]
    return np.array(
        [
            np.column_stack([np.interp(fractions, u, row[:, k]) for k in range(3)])
            for u, row in zip(arc, grid)
        ]
    )


def faces(grid):
    quads = np.stack((grid[:-1, :-1], grid[1:, :-1], grid[1:, 1:], grid[:-1, 1:]), axis=2).reshape(
        -1, 4, 3
    )
    return np.concatenate([quads * [sx, sy, 1] for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))])


def mesh_faces(path):
    _, points, triangles = read_msh_summary(path, return_arrays=True)
    points = points * 1000.0  # HornLab meshes are in metres.
    points = points[triangles]
    # A symmetry mesh lies wholly on one side of an axis. Full meshes retain
    # both sides; reflection does not depend on triangle winding for shading.
    for axis in (0, 1):
        values = points[..., axis]
        tolerance = max(np.max(np.abs(values)) * 1e-8, 1e-7)
        if values.min() >= -tolerance or values.max() <= tolerance:
            reflected = points.copy()
            reflected[..., axis] *= -1
            points = np.concatenate((points, reflected))
    return points


def draw_surface(ax, polygons, limits, elev, azim):
    # Plot coordinates x, axial z, vertical y, matching the existing render tool.
    polygons = polygons[..., [0, 2, 1]]
    normals = np.cross(polygons[:, 1] - polygons[:, 0], polygons[:, 2] - polygons[:, 0])
    norm = np.linalg.norm(normals, axis=1)
    normals /= np.maximum(norm[:, None], 1e-12)
    light = np.array([0.25, 0.53, 0.81])
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.abs(normals @ light)
    ax.add_collection3d(
        Poly3DCollection(
            polygons, facecolors=shade[:, None] * np.array([0.28, 0.64, 0.70]), linewidths=0
        )
    )
    ax.set(xlim=limits[0], ylim=limits[1], zlim=limits[2])
    ax.set_box_aspect([b - a for a, b in limits])
    ax.set_proj_type("ortho")
    ax.view_init(elev, azim)
    ax.axis("off")


def run(manifest, out):
    cases = read_cases(manifest)
    out.mkdir(parents=True, exist_ok=True)
    reference = next((c for c in cases if c[0]["id"] == "R0"), cases[0])
    view_faces = []
    for row, inner, outer in cases:
        if row.get("mesh"):
            polygons = mesh_faces(ROOT / row["mesh"])
            source = "mesh"
        else:
            polygons = np.concatenate((faces(inner), faces(outer)))
            source = "sampled surface (no mesh)"
        view_faces.append((polygons, source))
    allp = np.concatenate(
        [g.reshape(-1, 3) for _, i, o in cases for g in (i, o)]
        + [p.reshape(-1, 3) for p, _ in view_faces]
    )
    x = np.max(np.abs(allp[:, 0]))
    y = np.max(np.abs(allp[:, 1]))
    z0, z1 = allp[:, 2].min(), allp[:, 2].max()
    pad = max(x, y, z1 - z0) * 0.05
    limits = ((-x - pad, x + pad), (z0 - pad, z1 + pad), (-y - pad, y + pad))
    fig = plt.figure(figsize=(14, 3.2 * len(cases)), layout="constrained")
    for i, (row, inner, outer) in enumerate(cases):
        for j, (title, elev, azim) in enumerate(
            (
                ("Front isometric", 35.2643897, 45),
                ("Mouth / front", 0, 90),
                ("Top", 90, -90),
                ("Side", 0, 0),
            )
        ):
            ax = fig.add_subplot(len(cases), 4, i * 4 + j + 1, projection="3d")
            draw_surface(ax, view_faces[i][0], limits, elev, azim)
            if i == 0:
                ax.set_title(title)
            if j == 0:
                ax.text2D(
                    0.5,
                    0.02,
                    f"{row['id']} · {row.get('label', '')}\n{view_faces[i][1]}",
                    transform=ax.transAxes,
                    ha="center",
                )
    fig.suptitle("Orthographic geometry | shared physical scale and lighting")
    fig.savefig(out / "views.png", dpi=150)
    plt.close(fig)
    angles = (0, 22.5, 45, 67.5, 90)
    fig, axes = plt.subplots(2, len(angles), figsize=(20, 9), layout="constrained")
    for idx, (row, inner, outer) in enumerate(cases):
        color = COLORS[idx % len(COLORS)]
        label = row["id"]
        for j, deg in enumerate(angles):
            m = section(inner, np.deg2rad(deg))
            o = section(outer, np.deg2rad(deg))
            r = np.hypot(m[:, 0], m[:, 1])
            ro = np.hypot(o[:, 0], o[:, 1])
            axes[0, j].plot(r, m[:, 2], color=color, label=label)
            axes[0, j].plot(ro, o[:, 2], color=color, ls="--", alpha=0.6)
            ds = np.linalg.norm(np.diff(m, axis=0), axis=1)
            tangent = np.diff(m, axis=0) / np.maximum(ds[:, None], 1e-12)
            turn = np.arctan2(
                np.linalg.norm(np.cross(tangent[1:], tangent[:-1]), axis=1),
                np.sum(tangent[1:] * tangent[:-1], axis=1),
            )
            s = np.r_[0, np.cumsum(ds)]
            axes[1, j].plot(
                s[1:-1] / s[-1], turn / np.maximum((ds[:-1] + ds[1:]) / 2, 1e-12), color=color
            )
    # Equal limits across meridian panels, including shared aspect and equal data scale.
    xl = (min(a.get_xlim()[0] for a in axes[0]), max(a.get_xlim()[1] for a in axes[0]))
    yl = (min(a.get_ylim()[0] for a in axes[0]), max(a.get_ylim()[1] for a in axes[0]))
    for j, deg in enumerate(angles):
        axes[0, j].set(
            xlim=xl,
            ylim=yl,
            title=f"{deg}° meridian",
            xlabel="Radial distance (mm)",
            ylabel="Axial z (mm)",
        )
        axes[0, j].set_aspect("equal", adjustable="box")
        axes[1, j].set(
            title=f"{deg}° sampled curvature",
            xlabel="Arc length fraction",
            ylabel="Unsigned curvature (1/mm)",
        )
    for ax in axes.flat:
        ax.grid(alpha=0.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Meridians: inner solid, outer dashed")
    fig.savefig(out / "meridians.png", dpi=150)
    plt.close(fig)
    fig = plt.figure(figsize=(22, 5), layout="constrained")
    ax = fig.add_subplot(141, projection="3d")
    ax.set_proj_type("ortho")
    ax2 = fig.add_subplot(142)
    ax3 = fig.add_subplot(143)
    ax4 = fig.add_subplot(144)
    for idx, (row, inner, _) in enumerate(cases):
        color = COLORS[idx % len(COLORS)]
        label = row["id"]
        lip = inner[:, -1]
        phi = np.degrees(np.arctan2(lip[:, 1], lip[:, 0]))
        ax.plot(lip[:, 0], lip[:, 2], lip[:, 1], color=color, label=label)
        ref = reference[1][:, -1]
        rp = np.degrees(np.arctan2(ref[:, 1], ref[:, 0]))
        order = np.argsort(rp)
        ax2.plot(
            phi, lip[:, 2] - np.interp(phi, rp[order], ref[order, 2]), color=color, label=label
        )
        ax3.plot(phi, np.max(inner[:, :, 2], axis=1) - lip[:, 2], color=color, label=label)
        ax4.plot(phi, np.max(inner[:, :, 2], axis=1), color=color, label=label)
    ax.set(xlabel="x (mm)", ylabel="z (mm)", zlabel="y (mm)", title="Quarter lip overlay")
    ax.set_box_aspect((x, z1 - z0, y))
    ax.view_init(23, 61)
    ax2.axhline(0, color="black", lw=0.7)
    ax2.set(
        xlabel="Mouth polar angle (degrees)",
        ylabel="Lip z minus reference (mm)",
        title="Lip setback vs reference",
    )
    ax2.grid(alpha=0.2)
    ax2.legend(fontsize=8)
    ax3.set(
        xlabel="Mouth polar angle (degrees)",
        ylabel="Maximum z minus lip z (mm)",
        title="Sampled rollback depth",
    )
    ax3.grid(alpha=0.2)
    ax3.legend(fontsize=8)
    ax4.set(
        xlabel="Mouth polar angle (degrees)",
        ylabel="Maximum z (mm)",
        title="Sampled absolute forward reach",
    )
    ax4.grid(alpha=0.2)
    ax4.legend(fontsize=8)
    fig.savefig(out / "lip_overlay.png", dpi=150)
    plt.close(fig)
    cols = 4
    rows = int(np.ceil(len(cases) / cols))
    fig, axes = plt.subplots(
        rows, cols, figsize=(16, 4 * rows), squeeze=False, layout="constrained"
    )
    arc_fractions = np.linspace(0, 1, 101)
    for ax, (row, inner, _) in zip(axes.flat, cases):
        sections = sample_arc_sections(inner, arc_fractions)
        normals = np.cross(np.gradient(sections, axis=0), np.gradient(sections, axis=1))
        normals /= np.maximum(np.linalg.norm(normals, axis=2)[..., None], 1e-12)
        for j in (0, 25, 50, 75, 100):
            section_pts, normal = sections[:, j], normals[:, j]
            ax.plot(section_pts[:, 0], section_pts[:, 1], color="0.6", lw=0.8)
            stride = max(1, len(section_pts) // 8)
            xq, yq = section_pts[::stride, :2].T
            nx, ny, nz = normal[::stride].T
            ax.quiver(
                xq,
                yq,
                nx,
                ny,
                nz,
                cmap="coolwarm",
                norm=plt.Normalize(-1, 1),
                angles="xy",
                scale_units="xy",
                scale=0.05,
                width=0.005,
            )
        ax.set(
            title=f"{row['id']} · {row.get('label', '')}",
            xlabel="x (mm)",
            ylabel="y (mm)",
            xlim=(-10, x + pad),
            ylim=(-10, y + pad),
        )
        ax.set_aspect("equal")
        ax.grid(alpha=0.2)
    for ax in list(axes.flat)[len(cases) :]:
        ax.axis("off")
    colorbar = plt.cm.ScalarMappable(norm=plt.Normalize(-1, 1), cmap="coolwarm")
    fig.colorbar(
        colorbar,
        ax=axes.ravel().tolist(),
        shrink=0.65,
        label="Axial component of unit surface normal",
    )
    fig.suptitle("Quarter sections at 0%, 25%, 50%, 75%, 100% meridian arc")
    fig.savefig(out / "sections_normals.png", dpi=150)
    plt.close(fig)
    print(f"Rendered {len(cases)} cases to {out}; reference {reference[0]['id']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    run(args.manifest, args.out)
