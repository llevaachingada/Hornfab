"""3D views of the throat region of throat-sculpt cases (inner wall, mirrored to the full circle).

Per case: an axial view from the mouth (source disk in red: any wall drawn INSIDE it is a true pinch that
occludes the driver) and an oblique view of the first ``--zmax`` mm.  Report-only.

    .venv\\Scripts\\python.exe tools\\geometry\\throat_sculpt_render.py CASES.yaml --cases B0s_station PA30_h ... \\
        --out throat_3d.png
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "geometry"))


def full_surface(inner, zmax):
    """(n_phi_full, n_s, 3) for stations with z <= zmax on every row (quarter mirrored)."""
    k = int(np.min([np.searchsorted(row[:, 2], zmax) for row in inner]))
    q = inner[:, : max(k, 2), :]
    parts = [q, q[::-1] * np.array([-1, 1, 1]), q * np.array([-1, -1, 1]), q[::-1] * np.array([1, -1, 1])]
    return np.concatenate([parts[0], parts[1][1:], parts[2][1:], parts[3][1:]], axis=0)


def main(argv=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import throat_sculpt_pilot as P

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cases")
    ap.add_argument("--cases", dest="ids", nargs="+", required=True)
    ap.add_argument("--zmax", type=float, default=60.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    doc = P.load_cases(Path(a.cases))
    cfg = P._cfg(doc)
    r0 = float(cfg.brief["driver"]["exit_radius_mm"])
    by_id = {c["id"]: c for c in doc["cases"]}
    n = len(a.ids)
    fig = plt.figure(figsize=(3.3 * n, 6.6))
    t = np.linspace(0, 2 * math.pi, 200)
    for i, cid in enumerate(a.ids):
        _block, geo, _ts = P.build(by_id[cid], doc, cfg)
        S = full_surface(np.asarray(geo["inner_points"]), a.zmax)
        ax = fig.add_subplot(2, n, i + 1)
        z = S[..., 2]
        for j in range(S.shape[1]):
            ax.plot(S[:, j, 0], S[:, j, 1], color=plt.get_cmap("viridis")(z[0, j] / a.zmax), lw=0.8)
        ax.fill(r0 * np.cos(t), r0 * np.sin(t), color="red", alpha=0.25)
        ax.set_aspect("equal"); ax.set_title(f"{cid}\nmouth-on, z<= {a.zmax:g} mm", fontsize=8)
        lim = 2.2 * r0
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.tick_params(labelsize=6)
        ax3 = fig.add_subplot(2, n, n + i + 1, projection="3d")
        ax3.plot_surface(S[..., 0], S[..., 1], S[..., 2], cmap="viridis", linewidth=0.15, edgecolor="k",
                         alpha=0.95, rstride=1, cstride=1)
        ax3.plot(r0 * np.cos(t), r0 * np.sin(t), 0 * t, "r-", lw=1.5)
        ax3.view_init(elev=-62, azim=-60)
        ax3.set_box_aspect((1, 1, 1.2)); ax3.tick_params(labelsize=5)
        ax3.set_xlabel("x (H)", fontsize=6); ax3.set_ylabel("y (V)", fontsize=6)
    fig.suptitle("Throat region, inner wall (red = 18 mm source disk / ring)", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(a.out, dpi=120)
    print(a.out)


if __name__ == "__main__":
    raise SystemExit(main())
