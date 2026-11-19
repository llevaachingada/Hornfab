import json, re, sys
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from hornlab_plots._heatmap import prepare_heatmap_data, render_single_heatmap

# usage: compose_last_day.py TARGETS PREFIX START_SHEET WINDOW_TEXT
TARGETS = Path(sys.argv[1])
PREFIX = sys.argv[2]
START = int(sys.argv[3])
WINDOW = sys.argv[4]
R = Path("scratch/last_day/r")
OUT = Path("scratch/last_day/sheets")
OUT.mkdir(parents=True, exist_ok=True)
RENDERED = "2026-11-19 17:24 EST"

rows = [l.split() for l in TARGETS.read_text().splitlines() if l.strip()]


def run_time_local(run_dir):
    """Run dir name is UTC (YYYYMMDDTHHMMSSZ); return local EST text."""
    name = Path(run_dir).name
    m = re.match(r"(\d{8}T\d{6})Z", name)
    if not m:
        return ""
    t = datetime.strptime(m.group(1), "%Y%m%dT%H%M%S") - timedelta(hours=5)
    return t.strftime("%Y-%m-%d %H:%M EST")


def info(run_dir):
    b = json.loads((Path(run_dir) / "best.json").read_text(encoding="utf-8"))
    r = json.loads((Path(run_dir) / "run.json").read_text(encoding="utf-8"))
    cmd = r.get("command", "")
    cfg = cmd.split("--config")[-1].split()[0] if "--config" in cmd else ""
    brief = Path(cfg).stem if cfg else Path(run_dir).name
    return brief, b.get("family", "?"), b.get("objective", float("nan")), b.get("terms", {})


entries = []
for run_dir, h in rows:
    if not (R / f"{h}_iso.png").exists():
        continue
    brief, fam, J, terms = info(run_dir)
    z = np.load(Path(run_dir) / "designs" / h / "response.npz", allow_pickle=True)
    met = json.loads((Path(run_dir) / "designs" / h / "metrics.json").read_text(encoding="utf-8"))
    entries.append(dict(h=h, brief=brief, fam=fam, J=J, when=run_time_local(run_dir),
                        z=z, terms=terms, met=met))
entries.sort(key=lambda e: (e["brief"], e["J"]))

KEYS = ["diag", "distd", "dislope", "di_roughness", "flat", "rip", "flat_cv", "cov_profile", "load", "penalty"]


def score_lines(e):
    T, M = e["terms"], e["met"]
    fr = np.asarray(M["freqs_hz"])

    def at(arr, f0):
        return float(np.asarray(arr)[int(np.argmin(np.abs(fr - f0)))])

    out = [f"J (total) = {T.get('total', e['J']):.3f}", ""]
    out += [f"{k:<13}{T[k]:>8.3f}" for k in KEYS if isinstance(T.get(k), (int, float))]
    out += ["", f"f11   {T.get('f11_hz', float('nan')):.0f} Hz",
            f"lfp20 {T.get('lfp20_hz', float('nan')):.0f} Hz",
            f"n_in_band {int(T.get('n_in_band', 0))}", ""]
    for f0, lab in ((1065, "1.07 kHz"), (2269, "2.27 kHz")):
        out += [f"at {lab}",
                f"  -6dB cov H {at(M['bw_h_deg'], f0):.0f}  V {at(M['bw_v_deg'], f0):.0f} deg",
                f"  DI {at(M['di_db'], f0):.1f} dB",
                f"  ripple H {at(M['ripple_h_db'], f0):.1f}  V {at(M['ripple_v_db'], f0):.1f} dB"]
    return out


BIG = 17
PER = 3
sheets = [entries[s:s + PER] for s in range(0, len(entries), PER)]
for k, chunk in enumerate(sheets):
    part = START + k
    fig = plt.figure(figsize=(30, 7.2 * len(chunk) + 2.4), facecolor="white")
    gs = fig.add_gridspec(len(chunk), 7, left=0.01, right=0.99, top=0.93, bottom=0.07,
                          wspace=0.07, hspace=0.62, width_ratios=[1, 1, 1, 1, 1.2, 1.2, 1.75])
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
                ax.set_title("isometric" if j == 0 else "top-skew", fontsize=BIG + 5, weight="bold")
        sec = np.load(R / f"{h}_sec.npz")
        for j, (key, lab) in enumerate([("vseg", "V cut (x=0)"), ("hseg", "H cut (y=0)")]):
            ax = fig.add_subplot(gs[i, 2 + j])
            seg = sec[key]
            if len(seg):
                ax.add_collection(LineCollection(seg, colors="#222", linewidths=1.2))
            ax.autoscale()
            ax.set_aspect("equal")
            ax.grid(alpha=0.25)
            ax.tick_params(labelsize=BIG - 3)
            ax.set_xlabel("axial z (mm)", fontsize=BIG - 1)
            ax.set_ylabel("mm", fontsize=BIG - 1)
            if i == 0:
                ax.set_title(lab, fontsize=BIG + 5, weight="bold")
        f = z["freqs_hz"]
        for j, (key, akey, name) in enumerate([("spl_v_db", "v_angles_deg", "V dispersion"),
                                               ("spl_h_db", "h_angles_deg", "H dispersion")]):
            ax = fig.add_subplot(gs[i, 4 + j])
            ang = z[akey]
            s_ = z[key] - z[key][:, [int(np.argmin(np.abs(ang)))]]
            ia, fi, v = prepare_heatmap_data(ang, f, s_.T)
            render_single_heatmap(ax, fi, ia, v, name, theme="classic")
            ax.tick_params(labelsize=BIG - 3)
            ax.xaxis.get_offset_text().set_visible(False)
            if i == 0:
                ax.set_title(name, fontsize=BIG + 5, weight="bold")
        axs = fig.add_subplot(gs[i, 6])
        axs.set_axis_off()
        axs.text(0.02, 0.98, "\n".join(score_lines(e)), transform=axs.transAxes,
                 fontsize=BIG - 2, family="monospace", va="top", ha="left", linespacing=1.15)
        if i == 0:
            axs.set_title("scores", fontsize=BIG + 5, weight="bold")
        top = iso_ax.get_position().y1
        fig.text(0.01, top + (0.075 if i == 0 else 0.062),
                 f"{e['brief']}   |   {e['fam']}   J = {e['J']:.3f}   |   {h}   |   solved {e['when']}",
                 fontsize=BIG + 3, weight="bold", va="bottom", ha="left")
    fig.text(0.01, 0.012,
             f"Sheet {part}   |   {WINDOW}   |   rendered {RENDERED}   |   balloon DI   |   "
             "J comparable only within a brief",
             fontsize=BIG, va="bottom", ha="left", color="#333")
    fig.savefig(OUT / f"{PREFIX}_{part:02d}.png", dpi=200, facecolor="white")
    plt.close(fig)
    print(f"sheet {part}", [e["h"] for e in chunk], flush=True)
print("total", len(entries))
