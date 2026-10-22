"""Extract review data from hornlab-search run dirs into one JSON for the review page.

Usage (repo root):
    .venv\\Scripts\\python.exe tools\\review\\build_review_data.py tools\\review\\review_data.json [RUN_ID|NAME|LABEL ...]
    .venv\\Scripts\\python.exe tools\\review\\assemble.py tools\\review
Reads runs/<id>/{search.ndjson,config.yaml,best.json,designs/<hash>/} (local, gitignored) and
writes tools/review/hornlab_review.html. Extra runs are appended as "RUN_ID|NAME|LABEL".
"""
import json, sys, re
from pathlib import Path
import numpy as np
import yaml
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1])
RUNS = [
    ("20261013T123136Z-screen-ca15be", "osse_baseline", "CP-8c run 1"),
    ("20261013T204408Z-screen-6bdcbd", "icw_termination", "CP-8c run 2"),
    ("20261013T234724Z-screen-ff569c", "freeform_hv", "CP-8c run 3"),
    ("20261014T025335Z-screen-852be3", "throat_adapter", "CP-8c run 4"),
    ("20261022T141729Z-screen-babb6b", "freeform_sculpt", "6b, budget 60"),
] + [tuple(a.split("|")) for a in sys.argv[2:]]


def flat_params(p, prefix=""):
    out = {}
    if isinstance(p, dict):
        for k, v in p.items():
            out.update(flat_params(v, f"{prefix}{k}."))
    elif isinstance(p, list):
        for i, v in enumerate(p):
            out.update(flat_params(v, f"{prefix}{i}."))
    elif isinstance(p, (int, float)) and not isinstance(p, bool):
        out[prefix[:-1]] = float(p)
    return out


def r(x, n=3):
    a = np.asarray(x, dtype=float)
    return [None if not np.isfinite(v) else round(float(v), n) for v in a.ravel()]


def design_view(run_dir, h):
    d = run_dir / "designs" / h
    z = np.load(d / "response.npz", allow_pickle=True)
    m = json.loads((d / "metrics.json").read_text())
    f = z["freqs_hz"]
    def norm(spl):
        c = spl.shape[1] // 2
        return np.maximum(spl - spl[:, c:c + 1], -40.0)
    prof = {}
    msh = d / "mesh.msh"
    if msh.exists():
        txt = msh.read_text(errors="ignore")
        mm = re.search(r"\$Nodes\s*\n(\d+)\n(.*?)\$EndNodes", txt, re.S)
        if mm:
            pts = np.array([list(map(float, ln.split()[1:4])) for ln in mm.group(2).strip().splitlines()])
            tol = 1e-4
            for key, ax in (("h", 0), ("v", 1)):
                other = 1 - ax
                sel = pts[np.abs(pts[:, other]) < tol]
                prof[key] = [[round(float(a) * 1000, 2), round(float(zv) * 1000, 2)] for a, zv in zip(sel[:, ax], sel[:, 2])]
    return {
        "hash": h,
        "freqs": r(f, 1),
        "angles": r(z["h_angles_deg"], 1),
        "polar_h": [r(row, 2) for row in norm(z["spl_h_db"])],
        "polar_v": [r(row, 2) for row in norm(z["spl_v_db"])],
        "bw_h": r(m["bw_h_deg"], 2), "bw_v": r(m["bw_v_deg"], 2),
        "di": r(m["di_db"], 3), "on_axis": r(np.asarray(m["on_axis_db"]) - np.nanmean(m["on_axis_db"]), 3),
        "rip_h": r(m["ripple_h_db"], 3), "rip_v": r(m["ripple_v_db"], 3),
        "z_re": r(m["z_throat_real"], 3) if m.get("z_throat_real") is not None else None,
        "profile": prof,
    }


runs_out = []
for rid, name, label in RUNS:
    rd = REPO / "runs" / rid
    rows = [json.loads(l) for l in (rd / "search.ndjson").read_text().splitlines() if l.strip()]
    cfg = yaml.safe_load((rd / "config.yaml").read_text())
    best = json.loads((rd / "best.json").read_text())
    seed = rows[0]
    ok = [x for x in rows if x["ok"]]
    J = [round(float(x["objective"]), 4) if x["ok"] else None for x in rows]
    fails = {}
    for x in rows:
        if not x["ok"]:
            fails[x.get("kind") or "unknown"] = fails.get(x.get("kind") or "unknown", 0) + 1
    secs = [x["seconds"]["total"] for x in rows if x.get("seconds") and not x.get("cached")]
    # sensitivity: searched keys only
    bounds = cfg.get("bounds", {})
    searched = [k for k, b in bounds.items() if isinstance(b, dict) and b.get("search", True) and b.get("lo") != b.get("hi")]
    sens = []
    Jok = np.array([x["objective"] for x in ok])
    fp = [flat_params(x["params"]) for x in ok]
    alias = {"exponent": None}
    for k in searched:
        vals = []
        for p in fp:
            v = p.get(k)
            if v is None and k == "exponent":
                v = next((vv for kk, vv in p.items() if kk.endswith(".exponent")), None)
            vals.append(np.nan if v is None else v)
        vals = np.array(vals, float)
        good = np.isfinite(vals)
        if good.sum() > 10 and np.ptp(vals[good]) > 0:
            rho = spearmanr(vals[good], Jok[good]).correlation
            top = np.argsort(Jok)[:6]
            b = bounds[k]
            span = b["hi"] - b["lo"]
            sens.append({"key": k, "rho": round(float(rho), 3), "lo": b["lo"], "hi": b["hi"],
                         "best": round(float(flat_params(best["params"]).get(k, next((vv for kk, vv in flat_params(best["params"]).items() if kk.endswith(".exponent")), np.nan) if k == "exponent" else np.nan)), 4),
                         "at_lo": int(sum(vals[i] <= b["lo"] + 0.02 * span for i in top)),
                         "at_hi": int(sum(vals[i] >= b["hi"] - 0.02 * span for i in top))})
    t = cfg["target"]
    runs_out.append({
        "id": rid, "name": name, "label": label, "family": seed["family"],
        "n": len(rows), "n_ok": len(ok), "fails": fails,
        "seed_J": round(float(seed["objective"]), 4), "best_J": round(float(best["objective"]), 4),
        "best_eval": best.get("eval_no"),
        "s_per": round(float(np.median(secs)), 2) if secs else None,
        "target": t, "weights": cfg.get("weights"),
        "dofs_med": int(np.median([x["n_dof"] for x in ok if x.get("n_dof")])) if ok else None,
        "J": J,
        "terms_seed": {k: round(float(v), 4) for k, v in seed["terms"].items() if k in ("cov", "rip", "di", "dislope", "flat", "load")},
        "terms_best": {k: round(float(v), 4) for k, v in best["terms"].items() if k in ("cov", "rip", "di", "dislope", "flat", "load")},
        "sens": sorted(sens, key=lambda s: -abs(s["rho"])),
        "seed": design_view(rd, seed["design_hash"]),
        "best": design_view(rd, best["design_hash"]),
        "searched": len(searched),
    })
    print(rid, name, len(rows), seed["objective"], best["objective"])

OUT.write_text(json.dumps({"runs": runs_out}, separators=(",", ":")))
print("bytes", OUT.stat().st_size)
