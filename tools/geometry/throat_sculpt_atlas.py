"""Comparative section atlas: throat-sculpt bank cases vs the parent and the ST260-BLD reference CAD.

Reads the ``radii_<case>.npz`` files ``throat_sculpt_pilot.py bank`` writes (and any reference
``angular_radii.npz`` from ``throat_sections.py``) and draws, per case, the inner-wall sections at fixed z over
the source disk plus the H / 45 deg / V meridians against the parent. Report-only.

    .venv\\Scripts\\python.exe tools\\geometry\\throat_sculpt_atlas.py BANK_DIR --cases B0s_station S_h20 ... \\
        --reference runs\\...\\bld_step\\angular_radii.npz --r0 18 --ref-r0 12.7 --out atlas.png
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

Z_SHOW = (0.0, 5.0, 10.0, 15.0, 20.0, 30.0, 40.0)


def _load(npz):
    d = np.load(npz)
    return d["z_mm"], d["phi_rad"], d["r_mm"]


def _panel(ax_s, ax_m, z, ph, R, r0, title, parent=None, rotate_deg=0.0):
    import matplotlib.pyplot as plt
    cmap = plt.get_cmap("viridis")
    php = np.r_[ph, ph[:1]] + math.radians(rotate_deg)
    for i, zz in enumerate(Z_SHOW):
        j = int(np.argmin(np.abs(z - zz)))
        if abs(z[j] - zz) > 0.6:
            continue
        rr = np.r_[R[j], R[j][:1]] / r0
        ax_s.plot(rr * np.cos(php), rr * np.sin(php), color=cmap(i / (len(Z_SHOW) - 1)), lw=1.0,
                  label=f"z {zz:g}")
    t = np.linspace(0, 2 * math.pi, 200)
    ax_s.fill(np.cos(t), np.sin(t), color="red", alpha=0.08)
    ax_s.plot(np.cos(t), np.sin(t), "r--", lw=0.9)
    ax_s.set_aspect("equal"); ax_s.set_xlim(-2.4, 2.4); ax_s.set_ylim(-2.4, 2.4)
    ax_s.set_title(title, fontsize=8); ax_s.tick_params(labelsize=6)
    for deg, c in ((0, "C0"), (45, "C2"), (90, "C3")):
        k = int(round(((deg - rotate_deg) % 360) / 360 * ph.size)) % ph.size
        ax_m.plot(z, R[:, k] / r0, c, lw=1.1, label=f"{deg} deg")
        if parent is not None:
            pz, pph, pR = parent
            kk = int(round(deg / 360 * pph.size)) % pph.size
            ax_m.plot(pz, pR[:, kk] / r0, c, lw=0.7, ls=":")
    ax_m.axhline(1.0, color="r", lw=0.7, ls="--")
    ax_m.set_xlim(0, 60); ax_m.set_ylim(0.3, 3.5); ax_m.tick_params(labelsize=6)
    ax_m.set_xlabel("z mm", fontsize=7)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bank")
    ap.add_argument("--cases", nargs="+", required=True)
    ap.add_argument("--parent", default="B0s_station")
    ap.add_argument("--reference", default=None)
    ap.add_argument("--r0", type=float, required=True)
    ap.add_argument("--ref-r0", type=float, default=12.7)
    ap.add_argument("--ref-rotate-deg", type=float, default=90.0,
                    help="draw the reference rotated so its pinch plane matches the H-pinch cases")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    bank = Path(a.bank)
    panels = [(c, _load(bank / f"radii_{c}.npz"), a.r0, 0.0) for c in a.cases]
    if a.reference:
        panels.append((f"ST260-BLD CAD (rotated {a.ref_rotate_deg:g} deg)", _load(a.reference), a.ref_r0,
                       a.ref_rotate_deg))
    parent = _load(bank / f"radii_{a.parent}.npz") if (bank / f"radii_{a.parent}.npz").is_file() else None
    n = len(panels)
    cols = min(4, n)
    rows = math.ceil(n / cols)
    fig, axs = plt.subplots(rows * 2, cols, figsize=(3.4 * cols, 6.4 * rows),
                            gridspec_kw={"height_ratios": [1.6, 1.0] * rows})
    axs = np.atleast_2d(axs)
    for idx, (name, (z, ph, R), r0, rot) in enumerate(panels):
        r, c = divmod(idx, cols)
        _panel(axs[2 * r, c], axs[2 * r + 1, c], z, ph, R, r0, name,
               parent=None if rot else parent, rotate_deg=rot)
    for idx in range(n, rows * cols):
        r, c = divmod(idx, cols)
        axs[2 * r, c].axis("off"); axs[2 * r + 1, c].axis("off")
    axs[0, 0].legend(fontsize=5, loc="upper left")
    axs[1, 0].legend(fontsize=5)
    fig.suptitle("Inner-wall sections / r0 (red = projected source disk); meridians r/r0 (dotted = parent)", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    fig.savefig(a.out, dpi=120)
    print(a.out)


if __name__ == "__main__":
    raise SystemExit(main())
