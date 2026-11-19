import json, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from hornlab_plots._heatmap import prepare_heatmap_data, render_single_heatmap

R = Path("scratch/last_day/r"); OUT = Path("scratch/last_day/sheets"); OUT.mkdir(parents=True, exist_ok=True)
rows = [l.split() for l in Path("scratch/last_day/targets.txt").read_text().splitlines() if l.strip()]

def info(run_dir, h):
    b = json.loads((Path(run_dir) / "best.json").read_text(encoding="utf-8"))
    r = json.loads((Path(run_dir) / "run.json").read_text(encoding="utf-8"))
    cmd = r.get("command", "")
    cfg = cmd.split("--config")[-1].split()[0] if "--config" in cmd else ""
    brief = Path(cfg).stem if cfg else Path(run_dir).name
    return f"{brief}", b.get("family", "?"), b.get("objective", float("nan")), Path(run_dir).name

entries = []
for run_dir, h in rows:
    if not (R / f"{h}_iso.png").exists():
        continue
    brief, fam, J, runname = info(run_dir, h)
    z = np.load(Path(run_dir) / "designs" / h / "response.npz", allow_pickle=True)
    entries.append(dict(h=h, brief=brief, fam=fam, J=J, run=runname, z=z))

entries.sort(key=lambda e: (e["brief"], e["J"]))
PER = 3
for s in range(0, len(entries), PER):
    chunk = entries[s:s + PER]
    fig = plt.figure(figsize=(26, 4.8 * len(chunk) + 1.6), facecolor="white")
    gs = fig.add_gridspec(len(chunk), 6, left=0.01, right=0.99, top=0.97, bottom=0.04, wspace=0.06, hspace=0.22)
    for i, e in enumerate(chunk):
        h = e["h"]; z = e["z"]
        for j, (img, title) in enumerate([("iso", "isometric"), ("top", "top-skew")]):
            ax = fig.add_subplot(gs[i, j]); ax.imshow(plt.imread(R / f"{h}_{img}.png")); ax.set_axis_off()
            if j == 0: iso_ax = ax
            if i == 0: ax.set_title(title, fontsize=16)
        sec = np.load(R / f"{h}_sec.npz")
        for j, (key, lab, xl) in enumerate([("vseg", "V cut (x=0)", "axial z (mm)"), ("hseg", "H cut (y=0)", "axial z (mm)")]):
            ax = fig.add_subplot(gs[i, 2 + j])
            seg = sec[key]
            if len(seg): ax.add_collection(LineCollection(seg, colors="#222", linewidths=0.9))
            ax.autoscale(); ax.set_aspect("equal"); ax.grid(alpha=0.25)
            ax.tick_params(labelsize=11); ax.set_xlabel(xl, fontsize=11); ax.set_ylabel("mm", fontsize=11)
            if i == 0: ax.set_title(lab, fontsize=16)
        f = z["freqs_hz"]
        for j, (key, akey, name) in enumerate([("spl_v_db", "v_angles_deg", "V dispersion"), ("spl_h_db", "h_angles_deg", "H dispersion")]):
            ax = fig.add_subplot(gs[i, 4 + j])
            ang = z[akey]; s_ = z[key] - z[key][:, [int(np.argmin(np.abs(ang)))]]
            ia, fi, v = prepare_heatmap_data(ang, f, s_.T)
            render_single_heatmap(ax, fi, ia, v, name, theme="classic")
            ax.tick_params(labelsize=11)
            try:
                ax.ticklabel_format(axis="y", style="plain", useOffset=False)
            except AttributeError:
                pass
            ax.xaxis.get_offset_text().set_visible(False)
        fig.text(0.01, 0.955 - i * (0.94 / len(chunk)) , "", fontsize=1)
        # row label placed on the isometric panel's top-left
        axl = iso_ax
        axl.text(0.01, 0.99, f"{e['brief']} | {e['fam']} J={e['J']:.3f} | {h}", transform=axl.transAxes,
                 fontsize=14, weight="bold", va="top", ha="left",
                 bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=2))
    part = s // PER + 1
    fig.savefig(OUT / f"last_day_sheet_{part:02d}.png", dpi=200, facecolor="white")
    plt.close(fig)
    print("sheet", part, [e["h"] for e in chunk], flush=True)
print("total", len(entries))
