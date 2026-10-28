"""Compose rendered views (tools/render/render_views.py) into report images. Runs in the project venv.

Layouts:
  * ``stack`` (owner's preferred design card): views side by side on top, then the horizontal and the vertical
    dispersion maps full width below, one above the other. Needs a solved design (run dir / design dir target).
  * ``card``: views side by side on top, H and V maps side by side below (the older gallery style).
  * ``sheet``: a contact sheet - one row per design, one column per view. Geometry only.

The title line carries J (from best.json / search.ndjson), the brief coverage and f0; ``--loudness`` adds the
output gap at f0, the loaded-from frequency and the driver-coupling check (metrics/loudness.py,
mesh/throat_check.py).

Usage (repo root)::

    .venv\\Scripts\\python.exe tools/render/compose.py --renders scratch/r --layout stack --views a,b --loudness --out scratch/r/cards
    .venv\\Scripts\\python.exe tools/render/compose.py --renders scratch/r --layout sheet --views c,a,b,s --title "..." --out scratch/r/sheet.png
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

VIEW_NAMES = {"a": "front 3/4", "b": "behind", "c": "front", "s": "side", "u": "below"}


def trim(img, pad=12):
    m = (img[:, :, :3] < 0.97).any(2)
    ys, xs = np.nonzero(m)
    if ys.size == 0:
        return img
    return img[max(ys.min() - pad, 0):ys.max() + pad, max(xs.min() - pad, 0):xs.max() + pad]


def objective_of(t: dict):
    rd, h = t.get("run_dir"), t.get("design_hash")
    if not rd or not h:
        return None
    for line in (Path(rd) / "search.ndjson").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("design_hash") == h and r.get("ok"):
            return float(r["objective"])
    return None


def subtitle(t: dict) -> tuple[str, str]:
    rd = t.get("run_dir")
    if not rd:
        return "", ""
    cfg = yaml.safe_load((Path(rd) / "config.yaml").read_text(encoding="utf-8")) or {}
    tg = cfg.get("target") or {}
    f0 = float(tg.get("f0_hz") or tg.get("band_lo_hz") or float("nan"))
    J = objective_of(t)
    head = (f"J = {J:.2f}   " if J is not None else "") + \
        f"(brief {tg.get('coverage_h_deg', 0):.0f}x{tg.get('coverage_v_deg', 0):.0f}, f0 {f0:.0f} Hz)"
    return head, f"{f0}"


def loudness_line(t: dict) -> str:
    from hornlab_search.mesh.throat_check import fits_exit, throat_shape
    from hornlab_search.metrics.loudness import horn_loudness
    from hornlab_search.solve.cache import load_response
    rd, h = Path(t["run_dir"]), t["design_hash"]
    cfg = yaml.safe_load((rd / "config.yaml").read_text(encoding="utf-8")) or {}
    tg = cfg.get("target") or {}
    f0 = float(tg.get("f0_hz") or tg.get("band_lo_hz"))
    ld = horn_loudness(load_response(rd / "designs" / h / "response.npz"), f0_hz=f0)
    exit_r = ((cfg.get("brief") or {}).get("driver") or {}).get("exit_radius_mm")
    ok, why = fits_exit(throat_shape(t["mesh"]), 2.0 * float(exit_r) if exit_r else None)
    return (f"output gap at f0 {ld['output_gap_at_f0_db']:.1f} dB  |  loaded (Re z >= 0.5) from {ld['f_loaded_hz']:.0f} Hz  |  "
            f"driver coupling: {why}")


def heatmaps(fig, t: dict, boxes):
    from hornlab_plots._heatmap import prepare_heatmap_data, render_single_heatmap
    z = np.load(Path(t["run_dir"]) / "designs" / t["design_hash"] / "response.npz", allow_pickle=True)
    f = z["freqs_hz"]
    for box, (key, akey, name) in zip(boxes, (("spl_h_db", "h_angles_deg", "Horizontal dispersion"),
                                              ("spl_v_db", "v_angles_deg", "Vertical dispersion"))):
        ang = z[akey]
        s = z[key] - z[key][:, [int(np.argmin(np.abs(ang)))]]
        ax = fig.add_axes(box)
        ia, fi, v = prepare_heatmap_data(ang, f, s.T)
        render_single_heatmap(ax, fi, ia, v, name, theme="classic")


def card(t: dict, renders: Path, views: list[str], layout: str, loud: bool, out: Path) -> None:
    solved = bool(t.get("run_dir")) and (Path(t["run_dir"]) / "designs" / str(t["design_hash"]) / "response.npz").exists()
    tall = layout == "stack" and solved
    fig = plt.figure(figsize=(11, 15 if tall else (11 if solved else 5.5)), facecolor="white")
    top, h_views = (0.66, 0.29) if tall else ((0.5, 0.41) if solved else (0.05, 0.8))
    n = len(views)
    for i, v in enumerate(views):
        ax = fig.add_axes([0.01 + i / n, top, 0.98 / n, h_views])
        ax.imshow(trim(plt.imread(renders / f"{t['label']}_{v}.png")))
        ax.set_axis_off()
    head, _ = subtitle(t)
    fig.suptitle(f"{t['label']}      {head}", fontsize=15, y=0.99)
    if loud and solved:
        fig.text(0.5, 0.955, loudness_line(t), ha="center", fontsize=10, color="#444")
    if solved:
        boxes = ([0.08, 0.35, 0.80, 0.24], [0.08, 0.04, 0.80, 0.24]) if tall else \
            ([0.06, 0.07, 0.36, 0.34], [0.56, 0.07, 0.36, 0.34])
        heatmaps(fig, t, boxes)
    fig.savefig(out, dpi=85, facecolor="white")
    plt.close(fig)


def sheet(targets: list[dict], renders: Path, views: list[str], title: str, out: Path) -> None:
    fig, axs = plt.subplots(len(targets), len(views), figsize=(4.2 * len(views), 4.0 * len(targets)), facecolor="white",
                            squeeze=False)
    for i, t in enumerate(targets):
        for j, v in enumerate(views):
            ax = axs[i, j]
            ax.imshow(trim(plt.imread(renders / f"{t['label']}_{v}.png")))
            ax.set_axis_off()
            if i == 0:
                ax.set_title(VIEW_NAMES.get(v, v), fontsize=12, color="#555")
        axs[i, 0].text(-0.05, 0.5, t["label"], transform=axs[i, 0].transAxes, rotation=90, va="center", ha="right",
                       fontsize=13)
    if title:
        fig.suptitle(title, fontsize=15)
    fig.tight_layout(rect=(0.02, 0, 1, 0.97 if title else 1))
    fig.savefig(out, dpi=60, facecolor="white")
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--renders", required=True, help="the --out dir of render_views.py (has targets.json)")
    ap.add_argument("--layout", default="stack", choices=("stack", "card", "sheet"))
    ap.add_argument("--views", default="a,b")
    ap.add_argument("--labels", help="comma list (default: every target in targets.json)")
    ap.add_argument("--loudness", action="store_true", help="add the loudness/coupling line (solved designs)")
    ap.add_argument("--title", default="")
    ap.add_argument("--out", required=True, help="a dir for stack/card, a .png for sheet")
    args = ap.parse_args(argv)
    renders = Path(args.renders)
    targets = json.loads((renders / "targets.json").read_text(encoding="utf-8"))
    labels = args.labels.split(",") if args.labels else list(targets)
    chosen = [targets[k] for k in labels]
    views = args.views.split(",")
    if args.layout == "sheet":
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        sheet(chosen, renders, views, args.title, Path(args.out))
        print("ok", args.out)
        return 0
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for t in chosen:
        dest = out / f"{t['label']}.png"
        card(t, renders, views, args.layout, args.loudness, dest)
        print("ok", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
