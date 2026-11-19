import json, re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from hornlab_plots._heatmap import prepare_heatmap_data, render_single_heatmap

R = Path("scratch/last_day/r")
OUT = Path("scratch/last_day/sheets")
OUT.mkdir(parents=True, exist_ok=True)
rows = [l.split() for l in Path("scratch/last_day/targets.txt").read_text().splitlines() if l.strip()]


def info(run_dir):
    b = json.loads((Path(run_dir) / "best.json").read_text(encoding="utf-8"))
    r = json.loads((Path(run_dir) / "run.json").read_text(encoding="utf-8"))
    cmd = r.get("command", "")
    cfg = cmd.split("--config")[-1].split()[0] if "--config" in cmd else ""
    brief = Path(cfg).stem if cfg else Path(run_dir).name
    return brief, b.get("family", "?"), b.get("objective", float("nan")), Path(run_dir).name, b.get("terms", {})


entries = []
for run_dir, h in rows:
    if not (R / f"{h}_iso.png").exists():
        continue
    brief, fam, J, runname, terms = info(run_dir)
    z = np.load(Path(run_dir) / "designs" / h / "response.npz", allow_pickle=True)
    met = json.loads((Path(run_dir) / "designs" / h / "metrics.json").read_text(encoding="utf-8"))
    entries.append(dict(h=h, brief=brief, fam=fam, J=J, run=runname, z=z, terms=terms, met=met))

entries.sort(key=lambda e: (e["brief"], e["J"]))

KEYS = ["diag", "distd", "dislope", "di_roughness", "flat", "rip", "flat_cv", "cov_profile", "load", "penalty"]


def score_lines(e):
    T, M = e["terms"], e["met"]
    fr = np.asarray(M["freqs_hz"])

    def at(arr, f0):
        return float(np.asarray(arr)[int(np.argmin(np.abs(fr - f0)))])

    out = [f"J (total) = {T.get('total', e['J']):.3f}", ""]
    out += [f"{k:<14}{T[k]:>9.3f}" for k in KEYS if isinstance(T.get(k), (int, float))]
    out += ["", f"f11 {T.get('f11_hz', float('nan')):.0f} Hz   lfp20 {T.get('lfp20_hz', float('nan')):.0f} Hz",
            f"n_in_band {int(T.get('n_in_band', 0))}", ""]
    for f0, lab in ((1065, "1.07 kHz"), (2269, "2.27 kHz")):
        out += [f"at {lab}:",
                f"  -6 dB cov H {at(M['bw_h_deg'], f0):.0f} deg  V {at(M['bw_v_deg'], f0):.0f} deg",
                f"  DI {at(M['di_db'], f0):.1f} dB  ripple H {at(M['ripple_h_db'], f0):.1f} V {at(M['ripple_v_db'], f0):.1f} dB"]
    return out


PER = 3
for s in range(0, len(entries), PER):
    chunk = entries[s:s + PER]
    fig = plt.figure(figsize=(30, 4.8 * len(chunk) + 1.6), facecolor="white")
    gs = fig.add_gridspec(len(chunk), 7, left=0.01, right=0.99, top=0.97, bottom=0.04,
                          wspace=0.06, hspace=0.22, width_ratios=[1, 1, 1, 1, 1.25, 1.25, 1.45])
    for i, e in enumerate(chunk):
        h = e["h"]
        z = e["z"]
        for j, img in enumerate(["iso", "top"]):
            ax = fig.add_subplot(gs[i, j])
            ax.imshow(plt.imread(R / f"{h}_{img}.png"))
            ax.set_axis_off()
            if j == 0:
                iso_ax = ax
            if i == 0:
                ax.set_title("isometric" if j == 0 else "top-skew", fontsize=16)
        sec = np.load(R / f"{h}_sec.npz")
        for j, (key, lab) in enumerate([("vseg", "V cut (x=0)"), ("hseg", "H cut (y=0)")]):
            ax = fig.add_subplot(gs[i, 2 + j])
            seg = sec[key]
            if len(seg):
                ax.add_collection(LineCollection(seg, colors="#222", linewidths=0.9))
            ax.autoscale()
            ax.set_aspect("equal")
            ax.grid(alpha=0.25)
            ax.tick_params(labelsize=11)
            ax.set_xlabel("axial z (mm)", fontsize=11)
            ax.set_ylabel("mm", fontsize=11)
            if i == 0:
                ax.set_title(lab, fontsize=16)
        f = z["freqs_hz"]
        for j, (key, akey, name) in enumerate([("spl_v_db", "v_angles_deg", "V dispersion"),
                                               ("spl_h_db", "h_angles_deg", "H dispersion")]):
            ax = fig.add_subplot(gs[i, 4 + j])
            ang = z[akey]
            s_ = z[key] - z[key][:, [int(np.argmin(np.abs(ang)))]]
            ia, fi, v = prepare_heatmap_data(ang, f, s_.T)
            render_single_heatmap(ax, fi, ia, v, name, theme="classic")
            ax.tick_params(labelsize=11)
            try:
                ax.ticklabel_format(axis="y", style="plain", useOffset=False)
            except AttributeError:
                pass
            ax.xaxis.get_offset_text().set_visible(False)
            if i == 0:
                ax.set_title(name, fontsize=16)
        axs = fig.add_subplot(gs[i, 6])
        axs.set_axis_off()
        axs.text(0.02, 0.98, "\n".join(score_lines(e)), transform=axs.transAxes,
                 fontsize=11, family="monospace", va="top", ha="left")
        if i == 0:
            axs.set_title("scores", fontsize=16)
        row_top = iso_ax.get_position().y1
        fig.text(0.01, row_top + 0.012, f"{e['brief']}  |  {e['fam']}  J={e['J']:.3f}  |  {h}",
                 fontsize=14, weight="bold", va="bottom", ha="left")
    part = s // PER + 1
    fig.savefig(OUT / f"last_day_sheet_{part:02d}.png", dpi=200, facecolor="white")
    plt.close(fig)
    print("sheet", part, [e["h"] for e in chunk], flush=True)
print("total", len(entries))
