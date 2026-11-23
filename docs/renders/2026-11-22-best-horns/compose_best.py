"""Compose the eight best-screen horns of 2026-11-22 into A4-wide sheets (project venv, repo root).

Copy of 2026-11-19-last-day-horns/compose_last_day.py with these changes:
  * output goes to scratch/best22/sheets; PER stays 3 and RENDERED is this gallery's date;
  * rows keep targets.txt order (homes, compacts, v11) instead of sorting by brief;
  * the row header carries the gallery label, the short brief name and the brief id;
  * "solved" is the best row's created_utc from <run_dir>/search.ndjson (the row with this
    design_hash), converted to EST - NOT the run-dir prefix. Resume runs keep their old run id,
    so the prefix lies about when the winning design was actually solved;
  * each row gets its own header band, so a tall H/V cut panel can no longer push its column
    title into the row header (the 2-row sheet collided before);
  * the frequency axis keeps at most 6 labels (it printed every 100 Hz up to 1 kHz, unreadable).

Usage:
    .venv\\Scripts\\python.exe docs/renders/2026-11-22-best-horns/compose_best.py ^
        docs/renders/2026-11-22-best-horns/targets.txt best22 1 "best screen design of each family, solved 2026-11-22"
"""
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.ticker import NullFormatter

from hornlab_plots._heatmap import prepare_heatmap_data, render_single_heatmap

# usage: compose_best.py TARGETS PREFIX START_SHEET WINDOW_TEXT
HERE = Path(__file__).resolve().parent
TARGETS = Path(sys.argv[1])
PREFIX = sys.argv[2]
START = int(sys.argv[3])
WINDOW = sys.argv[4]
R = Path("scratch/best22/r")
OUT = Path("scratch/best22/sheets")
OUT.mkdir(parents=True, exist_ok=True)
RENDERED = "2026-11-22"

LABELS = {
    "6d9e8c874827": "home_fold",
    "026edbad538c": "home_twinray",
    "adf7e74388f0": "home_morph",
    "f4774d562aae": "c400_fold",
    "f05a5f9a2bbf": "c500_crowe",
    "b7ae23ef8caa": "c500_2in",
    "02f00c0e5542": "fav_v11",
    "f5b191713dac": "v11_fold",
}
BRIEFS = {
    "6d9e8c874827": "home v10",
    "026edbad538c": "home v10",
    "adf7e74388f0": "home v10",
    "f4774d562aae": "compact400 v10xo",
    "f05a5f9a2bbf": "compact500 v11cd",
    "b7ae23ef8caa": "compact500 2-inch v11cd",
    "02f00c0e5542": "v11 home",
    "f5b191713dac": "v11 home",
}

rows = [l.split() for l in TARGETS.read_text().splitlines() if l.strip()]


def to_est(ts: str) -> str:
    t = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ") - timedelta(hours=5)
    return t.strftime("%Y-%m-%d %H:%M EST")


def run_time_local(run_dir):
    """Fallback only: run dir name is UTC (YYYYMMDDTHHMMSSZ); return local EST text."""
    name = Path(run_dir).name
    m = re.match(r"(\d{8}T\d{6})Z", name)
    if not m:
        return ""
    t = datetime.strptime(m.group(1), "%Y%m%dT%H%M%S") - timedelta(hours=5)
    return t.strftime("%Y-%m-%d %H:%M EST")


def solved_time(run_dir, h):
    """created_utc of the successful search row for this design (the resume that solved it)."""
    found = None
    nd = Path(run_dir) / "search.ndjson"
    if nd.exists():
        for line in nd.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("design_hash") == h and r.get("ok") and r.get("created_utc"):
                found = r["created_utc"]
    if found:
        return to_est(found)
    print(f"WARN {h}: no search.ndjson row, falling back to run-dir time", flush=True)
    return run_time_local(run_dir)


def brief_id(r):
    """run.json config_name is present for every target; fall back to config stem."""
    name = r.get("config_name")
    if name:
        return name
    cfg = r.get("config_path") or ""
    return Path(cfg).stem if cfg else ""


def info(run_dir):
    b = json.loads((Path(run_dir) / "best.json").read_text(encoding="utf-8"))
    try:
        r = json.loads((Path(run_dir) / "run.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        r = {}
    return brief_id(r), b.get("family", "?"), b.get("objective", float("nan")), b.get("terms", {})


entries = []
for run_dir, h in rows:
    if not (R / f"{h}_iso.png").exists():
        print(f"SKIP {h} {run_dir}: no iso render in {R}", flush=True)
        continue
    brief, fam, J, terms = info(run_dir)
    z = np.load(Path(run_dir) / "designs" / h / "response.npz", allow_pickle=True)
    met = json.loads((Path(run_dir) / "designs" / h / "metrics.json").read_text(encoding="utf-8"))
    entries.append(dict(h=h, label=LABELS.get(h, h), brief=BRIEFS.get(h, brief), cfg=brief, fam=fam, J=J,
                        when=solved_time(run_dir, h), z=z, terms=terms, met=met))

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
    outer = fig.add_gridspec(len(chunk), 1, left=0.01, right=0.99, top=0.985, bottom=0.055, hspace=0.28)
    for i, e in enumerate(chunk):
        h = e["h"]
        z = e["z"]
        sub = outer[i, 0].subgridspec(2, 7, height_ratios=[0.10, 1.0], hspace=0.10,
                                      width_ratios=[1, 1, 1, 1, 1.2, 1.2, 1.75], wspace=0.07)
        hax = fig.add_subplot(sub[0, :])
        hax.set_axis_off()
        hax.text(0.0, 0.85,
                 f"{e['label']}   |   {e['brief']}   |   {e['fam']}   J = {e['J']:.5f}   |   "
                 f"{h}   |   solved {e['when']}",
                 transform=hax.transAxes, fontsize=BIG + 3, weight="bold", va="center", ha="left")
        for j, img in enumerate(["iso", "top"]):
            ax = fig.add_subplot(sub[1, j])
            ax.imshow(plt.imread(R / f"{h}_{img}.png"))
            ax.set_axis_off()
            if i == 0:
                ax.set_title("isometric" if j == 0 else "top-skew", fontsize=BIG + 5, weight="bold")
        sec = np.load(R / f"{h}_sec.npz")
        for j, (key, lab) in enumerate([("vseg", "V cut (x=0)"), ("hseg", "H cut (y=0)")]):
            ax = fig.add_subplot(sub[1, 2 + j])
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
            ax = fig.add_subplot(sub[1, 4 + j])
            ang = z[akey]
            s_ = z[key] - z[key][:, [int(np.argmin(np.abs(ang)))]]
            ia, fi, v = prepare_heatmap_data(ang, f, s_.T)
            render_single_heatmap(ax, fi, ia, v, name, theme="classic")
            ax.tick_params(labelsize=BIG - 3)
            ax.xaxis.set_minor_formatter(NullFormatter())   # stray "10^2 / 2x10^3" labels
            lo, hi = ax.get_xlim()
            nice = [t for t in (m * 10.0 ** e for e in range(1, 5) for m in (1, 2, 5))
                    if lo * 1.1 <= t <= hi * 0.96]
            if nice:                                  # 1-2-5 decades read evenly; the raw tick list
                ax.set_xticks(nice)                   # printed every 100 Hz up to 1 kHz, unreadable
            ax.xaxis.get_offset_text().set_visible(False)
            if i == 0:
                ax.set_title(name, fontsize=BIG + 5, weight="bold")
        axs = fig.add_subplot(sub[1, 6])
        axs.set_axis_off()
        axs.text(0.02, 0.98, "\n".join(score_lines(e)), transform=axs.transAxes,
                 fontsize=BIG - 2, family="monospace", va="top", ha="left", linespacing=1.15)
        if i == 0:
            axs.set_title("scores", fontsize=BIG + 5, weight="bold")
    fig.text(0.01, 0.012,
             f"Sheet {part}   |   {WINDOW}   |   rendered {RENDERED}   |   balloon DI   |   "
             "screen J comparable only within a brief",
             fontsize=BIG, va="bottom", ha="left", color="#333")
    fig.savefig(OUT / f"{PREFIX}_{part:02d}.png", dpi=200, facecolor="white")
    plt.close(fig)
    print(f"sheet {part}", [e["h"] for e in chunk], flush=True)
print("total", len(entries))
