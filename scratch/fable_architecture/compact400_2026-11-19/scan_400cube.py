"""CPU scan (2026-11-19): every stored solved design whose OUTER bbox fits a 400 mm cube, with its
-6 dB beamwidths at 850/1000/1250/1600 Hz, first Re(z) >= 0.2 frequency and throat radius.
Read-only over runs/**/search.ndjson + designs/<hash>/metrics.json; no solve.

Usage: .venv\\Scripts\\python.exe scratch/fable_architecture/compact400_2026-11-19/scan_400cube.py OUT.json
Writes a summary (counts, percentiles, qualifying-design census by config and throat radius).
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
CUBE_MM = 400.5


def main(out: str) -> None:
    seen, rows = set(), []
    for nd in (ROOT / "runs").rglob("search.ndjson"):
        run = nd.parent
        for line in nd.open(encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            b = r.get("bbox_m")
            if not r.get("ok") or b is None or r["design_hash"] in seen:
                continue
            sym = r.get("symmetry_plane") or ""
            w = (b[3] - b[0]) * (2 if "yz" in sym else 1) * 1000
            h = (b[4] - b[1]) * (2 if "xz" in sym else 1) * 1000
            d = (b[5] - b[2]) * 1000
            if max(w, h, d) > CUBE_MM:
                continue
            m = run / "designs" / r["design_hash"] / "metrics.json"
            if not m.exists():
                continue
            try:
                M = json.loads(m.read_text())
            except ValueError:
                continue
            f = np.asarray(M["freqs_hz"], float)
            if f.min() > 800 or f.max() < 2000:
                continue
            seen.add(r["design_hash"])
            bh, bv = np.asarray(M["bw_h_deg"], float), np.asarray(M["bw_v_deg"], float)
            zr = np.asarray(M.get("z_throat_real") or [np.nan] * len(f), float)
            at = lambda x, y: float(np.interp(np.log(x), np.log(f), y))  # noqa: E731
            i = np.where(zr >= 0.2)[0]
            lfp = (r.get("terms") or {}).get("lfp20_hz") or (float(f[i[0]]) if len(i) else np.nan)
            p = r.get("params") or {}
            rows.append(dict(run=run.relative_to(ROOT / "runs").as_posix(), design=r["design_hash"],
                             w=w, h=h, d=d, r0=p.get("r0_mm"), lfp=lfp,
                             **{f"{pl}{fx}": at(fx, arr) for fx in (850, 1000, 1250, 1600)
                                for pl, arr in (("h", bh), ("v", bv))}))
    summ = {"n_designs_in_cube": len(rows), "percentiles_p10_p50_p90": {}, "corridor_counts": {}}
    for k in ("lfp", "h850", "v850", "h1000", "v1000", "h1250", "v1250", "v1600"):
        a = np.array([x[k] for x in rows], float)
        a = a[np.isfinite(a)]
        summ["percentiles_p10_p50_p90"][k] = [round(float(v), 1) for v in np.percentile(a, [10, 50, 90])]
    for fx in (850, 1000, 1250):
        summ["corridor_counts"][f"H60-100_and_V<=75_at_{fx}"] = sum(
            1 for x in rows if 60 <= x[f"h{fx}"] <= 100 and x[f"v{fx}"] <= 75)
    q = [x for x in rows if x["v1000"] <= 75 and x["v1250"] <= 70 and 60 <= x["h1000"] <= 100
         and x["lfp"] and x["lfp"] <= 625]
    by = collections.Counter()
    for x in q:
        cfg = json.loads((ROOT / "runs" / x["run"] / "run.json").read_text()).get("config_name")
        by[f"{cfg} | r0 {x['r0']}"] += 1
    summ["qualifying_rule"] = "V<=75 @1k, V<=70 @1.25k, H 60-100 @1k, lfp20<=625 Hz"
    summ["n_qualifying"] = len(q)
    summ["qualifying_by_config_and_r0"] = dict(by.most_common())
    Path(out).write_text(json.dumps(summ, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
