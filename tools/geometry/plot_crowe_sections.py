#!/usr/bin/env python3
"""Plot reconstructed ES-600 section profiles and projected panel junctions.

Source landmarks are approximate readings of Crowe drawing 1148-01-001, not
original CAD. The plotted sweep, crown, and body are our own reconstruction.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml

from tools.geometry import crowe_panel
from tools.geometry.build_rolled_rect_page import BRIEF, CONFIGS, DEFAULT_OUT, load_yaml

REFERENCE = ROOT / "examples/prototypes/rolled_rect_2026-11-15/crowe_section_reference.yaml"
DEFAULT_CONFIG = CONFIGS / "rr__crowe_panel_es600_v7.yaml"
DEFAULT_PLOT = DEFAULT_OUT / "images/crowe_sections.png"


def plot(config: Path, output: Path) -> None:
    cfg, brief = load_yaml(config), load_yaml(BRIEF)
    ref = yaml.safe_load(REFERENCE.read_text(encoding="utf-8"))
    generator = cfg["generator"]
    shape = {k: cfg["seed_params"]["g_" + k]
             for k in crowe_panel.SHAPE_KEYS - {"n_phi", "n_s", "wall_thickness_mm"}}
    shape.update({k: generator[k] for k in ("n_phi", "n_s", "wall_thickness_mm")})
    points, meta = crowe_panel.make_grid(shape, brief)
    # Plot generated sections, including the throat blend and rear body. Plotting
    # the interpolation input alone would conceal a faulty surface construction.
    fine = {**shape, 'n_phi': 97, 'n_s': 512}
    dense, _ = crowe_panel.make_grid(fine, brief)
    outer = crowe_panel.outer_points(dense, fine)
    junction = meta["junction"]
    jx, jy = np.asarray(junction["x"]), np.asarray(junction["y"])
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5), constrained_layout=True)
    for ax, name, row, radial, key in zip(axes[:2], ("Horizontal cut B–B", "Vertical cut C–C"),
                                     (0, -1), (0, 1), ("horizontal_mm", "vertical_mm")):
        model, body = dense[row][:, [radial, 2]], outer[row][:, [radial, 2]]
        samples = np.asarray(ref[key])
        polygon = np.concatenate((model, body[::-1]))
        for sign in (-1, 1):
            ax.fill(sign*polygon[:, 0], polygon[:, 1], color="#e4d7c9", alpha=.8)
            ax.plot(sign*model[:, 0], model[:, 1], color="#94512f", lw=2,
                    label="Generated surface" if sign == 1 else None)
            ax.plot(sign*body[:, 0], body[:, 1], color="#7a7c7c", lw=1)
        ax.scatter(samples[:, 0], samples[:, 1], color="#243e50", s=19, zorder=3,
                   label="Approximate drawing readings")
        ax.set(title=name, xlabel="Position across centreline (mm)", ylabel="Forward depth from driver face (mm)")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(alpha=.2)
        ax.legend(fontsize=8, loc="best")
    ax = axes[2]
    # Show selected projected grid lines, not a claimed exact exterior silhouette.
    points = np.asarray(points)
    for row in points[::max(1, len(points)//12)]:
        for sx in (-1, 1):
            for sy in (-1, 1):
                ax.plot(sx*row[:, 0], sy*row[:, 1], color="#b9c5c3", lw=.45, alpha=.7)
    for sx in (-1, 1):
        for sy in (-1, 1):
            ax.plot(sx*points[:, -1, 0], sy*points[:, -1, 1], color="#243e50", lw=1.2, label="Returned edge" if sx == sy == 1 else None)
            ax.plot(sx*jx, sy*jy, color="#94512f", lw=2, label="Ideal sweep intersection" if sx == sy == 1 else None)
    ax.set(title="Front projection of model", xlabel="Horizontal position (mm)", ylabel="Vertical position (mm)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=.2)
    ax.legend(fontsize=8, loc="best")
    fig.suptitle("Section-based ES-600 visual study", fontsize=16, fontweight="bold")
    fig.text(.5, -.025, "Source: Joseph Crowe drawing 1148-01-001 · sparse manual readings, not CAD · custom sweep, crown and exterior body; acoustic performance unmeasured",
             ha="center", va="top", fontsize=9, color="#485b5b")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path, default=DEFAULT_PLOT)
    args = parser.parse_args()
    plot(args.config, args.out)
