"""On-axis tilt (dB/octave) and ripple of best designs: how much of `flat` is drive-induced tilt."""
import glob, json, os, sys
import numpy as np

root = sys.argv[1]
seen = 0
for run in sorted(glob.glob(os.path.join(root, "runs", "*")))[-60:]:
    try:
        best = json.load(open(os.path.join(run, "best.json"), encoding="utf-8"))
    except Exception:
        continue
    h = best.get("design_hash")
    mp = os.path.join(run, "designs", str(h), "metrics.json")
    if not h or not os.path.exists(mp):
        continue
    m = json.load(open(mp, encoding="utf-8"))
    m = m.get("metrics", m)
    f = np.asarray(m.get("freqs_hz"), float)
    ax = np.asarray(m.get("on_axis_db"), float)
    rh = np.asarray(m.get("ripple_h_db"), float)
    rv = np.asarray(m.get("ripple_v_db"), float)
    tgt = (json.load(open(os.path.join(run, "run.json"), encoding="utf-8")).get("config") or {}).get("target") or {}
    lo, hi = float(tgt.get("band_lo_hz", 0)), float(tgt.get("band_hi_hz", 1e9))
    b = (f >= lo) & (f <= hi) & np.isfinite(ax)
    if b.sum() < 3:
        continue
    slope = np.polyfit(np.log2(f[b]), ax[b], 1)
    resid = ax[b] - np.polyval(slope, np.log2(f[b]))
    zr = m.get("z_throat_real")
    print(f"{os.path.basename(run)[:30]} tilt {slope[0]:+.2f} dB/oct  std raw {np.std(ax[b]):.2f}  "
          f"std detrended {np.std(resid):.2f}  vel-normalised std {np.std(ax[b] + 20*np.log10(f[b])):.2f}  "
          f"ripple h/v {np.nanmean(rh[b]):.2f}/{np.nanmean(rv[b]):.2f}")
    seen += 1
    if seen >= 12:
        break
print("rows:", seen)
