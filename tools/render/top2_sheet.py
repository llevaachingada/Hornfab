import json, re
from pathlib import Path
import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
P = json.load(open("scratch/top2/picks.json"))
out = Path("scratch/top2/sheets"); out.mkdir(exist_ok=True)
groups = {}
for o in P: groups.setdefault(o["typ"], []).append(o)
for typ, items in groups.items():
    k = re.sub(r"[^a-z0-9]+", "_", typ.lower()).strip("_")
    cards = [Image.open(f"scratch/top2/cards/{k}_{i+1}.png") for i in range(len(items))]
    b = items[0]; d = Path(b["rd"]) / "designs" / b["h"]
    vz = Path(b["rd"]) / "verify" / "designs" / b["h"] / "response.npz"
    src = vz if vz.exists() else d / "response.npz"
    z = np.load(src, allow_pickle=True); f = z["freqs_hz"]
    W = sum(c.width for c in cards); H = max(c.height for c in cards)
    fig = plt.figure(figsize=(W / 100, H / 100 + 5), dpi=100)
    x = 0
    for c in cards:
        ax = fig.add_axes([x / W, 5 / (H / 100 + 5), c.width / W, H / 100 / (H / 100 + 5)]); ax.imshow(c); ax.axis("off"); x += c.width
    ax = fig.add_axes([0.07, 0.05 * 5 / (H/100+5) + 0.02, 0.88, 3.6 / (H / 100 + 5)])
    def line(key, akey, deg, lab, **kw):
        a = z[akey]; i = int(np.argmin(np.abs(a - deg)))
        ax.semilogx(f, 20 * np.log10(np.abs(z[key][:, i])) , label=lab, marker="o", ms=3, **kw)
    line("p_h", "h_angles_deg", 0, "on-axis", lw=2.4, color="k")
    for deg, c in ((15, "#1f77b4"), (30, "#2ca02c"), (45, "#d62728")):
        line("p_h", "h_angles_deg", deg, f"H {deg}°", color=c)
        line("p_v", "v_angles_deg", deg, f"V {deg}°", color=c, ls="--")
    ref = 20 * np.log10(np.abs(z["p_h"][:, int(np.argmin(np.abs(z["h_angles_deg"])))])).max()
    ax.set_ylim(ref - 30, ref + 4); ax.grid(True, which="both", alpha=.3)
    ax.set_xlabel("Hz"); ax.set_ylabel("dB (constant throat acceleration)")
    ax.set_title(f"#1 {typ} - frequency response ({'verify' if src == vz else 'screen'} solve, {len(f)} freqs; horn only, no driver)", fontsize=11)
    ax.legend(ncol=7, fontsize=8, loc="lower center")
    fig.savefig(out / f"{k}.png", dpi=100); plt.close(fig); print("ok", k, src.parent.parent.parent.name)
