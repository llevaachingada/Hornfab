"""Extract review data from hornlab-search run dirs into one JSON for the review page.

Usage (repo root):
    .venv\\Scripts\\python.exe tools\\review\\build_review_data.py tools\\review\\review_data.json [RUN_ID|NAME|LABEL ...]

    # With typology campaign files:
    .venv\\Scripts\\python.exe tools\\review\\build_review_data.py tools\\review\\review_data.json \\
        --campaign runs\\campaign_20261022T213156Z\\campaign.json \\
        --campaign runs\\campaign_20261022T221610Z\\campaign.json

    # Exclude entries scored with a bug (NAME@CAMPAIGN_DIRNAME, repeatable):
    .venv\\Scripts\\python.exe tools\\review\\build_review_data.py tools\\review\\review_data.json \\
        --campaign runs\\campaign_20261022T213156Z\\campaign.json \\
        --exclude-entry icw_termination@campaign_20261022T213156Z \\
        --exclude-entry freeform_sculpt@campaign_20261022T213156Z

    Then assemble:
    .venv\\Scripts\\python.exe tools\\review\\assemble.py tools\\review

Reads runs/<id>/{search.ndjson,config.yaml,best.json,designs/<hash>/} (local, gitignored) and
writes tools/review/hornlab_review.html. Extra runs are appended as "RUN_ID|NAME|LABEL".

Campaign files (runs/campaign_*/campaign.json) feed the Typology Campaigns section:
  per campaign: brief_name, tier, entries with per-family search stats, best-design curves,
  wall profiles, generator derived info, and loading scalars.  Missing run dirs are skipped
  gracefully without crashing the build.

--exclude-entry NAME@CAMPAIGN_DIRNAME drops an entry by its name and the campaign directory
  basename (not the full path).  Repeatable.  Use this to remove entries re-scored with a bug
  while the corrected campaign files are being rebuilt by the orchestrator.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("out")
parser.add_argument("extra", nargs="*")
parser.add_argument("--campaign", action="append", default=[], dest="campaigns",
                    metavar="PATH", help="Path to a campaign.json file (repeatable).")
parser.add_argument("--exclude-entry", action="append", default=[], dest="excludes",
                    metavar="NAME@CAMPAIGN_DIRNAME",
                    help="Drop an entry by NAME@campaign_dirname (repeatable).")
args = parser.parse_args()

OUT = Path(args.out)
RUNS = [
    ("20261013T123136Z-screen-ca15be", "osse_baseline", "CP-8c run 1"),
    ("20261013T204408Z-screen-6bdcbd", "icw_termination", "CP-8c run 2"),
    ("20261013T234724Z-screen-ff569c", "freeform_hv", "CP-8c run 3"),
    ("20261014T025335Z-screen-852be3", "throat_adapter", "CP-8c run 4"),
    ("20261022T141729Z-screen-babb6b", "freeform_sculpt", "6b, budget 60"),
] + [tuple(a.split("|")) for a in args.extra]

# Parse excludes into a set of (name, campaign_dirname) tuples
EXCLUDES = set()
for exc in args.excludes:
    if "@" in exc:
        n, cdirname = exc.split("@", 1)
        EXCLUDES.add((n.strip(), cdirname.strip()))
    else:
        print(f"[warn] --exclude-entry {exc!r} has no '@'; ignoring", file=sys.stderr)


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


def _freeform_profile(design_json_path):
    """Extract wall profile from FREEFORM design.json profileH/profileV.points ([z, r, angle])."""
    try:
        dj = json.loads(design_json_path.read_text())
        params = dj.get("params", {})
        prof = {}
        for key in ("profileH", "profileV"):
            pts_raw = params.get(key, {}).get("points", [])
            if pts_raw:
                # points can be [z, r] or [z, r, angle]; always mm
                out = []
                for pt in pts_raw:
                    if len(pt) >= 2:
                        out.append([round(float(pt[0]), 2), round(float(pt[1]), 2)])
                if out:
                    prof["h" if key == "profileH" else "v"] = out
        return prof
    except Exception:
        return {}


def design_view_campaign(run_dir, best_hash):
    """Like design_view but also tries FREEFORM design.json profileH/V for the wall profile."""
    d = run_dir / "designs" / best_hash
    z = np.load(d / "response.npz", allow_pickle=True)
    m = json.loads((d / "metrics.json").read_text())
    f = z["freqs_hz"]
    def norm(spl):
        c = spl.shape[1] // 2
        return np.maximum(spl - spl[:, c:c + 1], -40.0)

    # Wall profile: try design.json FREEFORM first, fall back to mesh.msh nodes
    dj_path = d / "design.json"
    prof = {}
    if dj_path.exists():
        prof = _freeform_profile(dj_path)
    if not prof:
        msh = d / "mesh.msh"
        if msh.exists():
            txt = msh.read_text(errors="ignore")
            mm2 = re.search(r"\$Nodes\s*\n(\d+)\n(.*?)\$EndNodes", txt, re.S)
            if mm2:
                pts = np.array([list(map(float, ln.split()[1:4])) for ln in mm2.group(2).strip().splitlines()])
                tol = 1e-4
                for key, ax in (("h", 0), ("v", 1)):
                    other = 1 - ax
                    sel = pts[np.abs(pts[:, other]) < tol]
                    prof[key] = [[round(float(a) * 1000, 2), round(float(zv) * 1000, 2)] for a, zv in zip(sel[:, ax], sel[:, 2])]

    scalars = m.get("scalars", {})
    return {
        "hash": best_hash,
        "freqs": r(f, 1),
        "bw_h": r(m["bw_h_deg"], 2),
        "bw_v": r(m["bw_v_deg"], 2),
        "di": r(m["di_db"], 3),
        "profile": prof,
        "loading": {
            "f_load_hz": scalars.get("f_load_hz"),
            "z_mean_band": scalars.get("z_mean_band"),
            "z_ripple": scalars.get("z_ripple"),
        },
    }


def load_campaign(campaign_path_str, excludes):
    """Load one campaign.json and return a dict suitable for the review page."""
    cp = Path(campaign_path_str)
    if not cp.is_absolute():
        cp = REPO / cp
    if not cp.exists():
        print(f"[warn] campaign file not found: {cp}", file=sys.stderr)
        return None

    campaign_dirname = cp.parent.name  # e.g. "campaign_20261022T213156Z"
    cdata = json.loads(cp.read_text())

    entries_out = []
    for entry in cdata.get("entries", []):
        ename = entry["name"]
        # Apply excludes
        if (ename, campaign_dirname) in excludes:
            print(f"[info] excluding {ename}@{campaign_dirname}", file=sys.stderr)
            continue

        if entry.get("skipped"):
            continue

        jobs = entry.get("jobs", [])
        if not jobs:
            continue

        # Take first (and usually only) job for screen tier
        job = jobs[0]
        run_dir_raw = job.get("run_dir", "")
        if not run_dir_raw:
            continue
        run_dir = Path(run_dir_raw)

        # Check run dir exists
        search_ndjson = run_dir / "search.ndjson"
        config_yaml = run_dir / "config.yaml"
        best_json = run_dir / "best.json"
        if not (search_ndjson.exists() and config_yaml.exists() and best_json.exists()):
            print(f"[warn] run dir incomplete, skipping entry {ename}: {run_dir}", file=sys.stderr)
            continue

        try:
            rows = [json.loads(l) for l in search_ndjson.read_text().splitlines() if l.strip()]
            cfg = yaml.safe_load(config_yaml.read_text())
            best = json.loads(best_json.read_text())
        except Exception as exc:
            print(f"[warn] failed to load run data for {ename}: {exc}", file=sys.stderr)
            continue

        seed_row = rows[0]
        ok_rows = [x for x in rows if x.get("ok")]
        n_total = len(rows)
        n_ok = len(ok_rows)

        # Failures by kind
        fails = {}
        for x in rows:
            if not x.get("ok"):
                k = x.get("kind") or "unknown"
                fails[k] = fails.get(k, 0) + 1

        # Number of searched knobs (from config.yaml bounds)
        bounds = cfg.get("bounds", {})
        searched_keys = [
            k for k, b in bounds.items()
            if isinstance(b, dict) and b.get("search", True) and b.get("lo") != b.get("hi")
        ]
        n_knobs = len(searched_keys)

        # best J, seed J
        best_j = round(float(best["objective"]), 4)
        seed_j = round(float(seed_row["objective"]), 4)

        # Weighted cost terms of the best design
        w = dict(cov=1, rip=1, di=0.3, dislope=0.5, flat=0.5, load=0)
        w.update(cfg.get("weights") or {})
        TERMS = ["cov", "rip", "di", "dislope", "flat", "load"]
        terms_best = {k: round(float(v * (best.get("terms") or {}).get(k, 0)), 4) for k, v in w.items() if k in TERMS}

        # Generator info from seed row
        gen = seed_row.get("generator") or {}
        knobs = gen.get("knobs") or {}
        derived = gen.get("derived") or {}

        # Extract f_c, T, truncation from derived (various key names)
        derived_info = {}
        for plane, pinfo in derived.items():
            if not isinstance(pinfo, dict):
                continue
            di = {}
            for fc_key in ("fc_hz", "f_c", "fc"):
                if fc_key in pinfo:
                    di["fc_hz"] = round(float(pinfo[fc_key]), 1)
                    break
            if "T" in pinfo:
                di["T"] = round(float(pinfo["T"]), 4)
            if "truncation" in pinfo:
                di["truncation"] = round(float(pinfo["truncation"]), 4)
            if "alpha_deg" in pinfo:
                di["alpha_deg"] = round(float(pinfo["alpha_deg"]), 2)
            if "type" in pinfo:
                di["type"] = pinfo["type"]
            if "length_mm" in pinfo:
                di["length_mm"] = round(float(pinfo["length_mm"]), 1)
            if "mouth_radius_mm" in pinfo:
                di["mouth_radius_mm"] = round(float(pinfo["mouth_radius_mm"]), 1)
            derived_info[plane] = di

        # Best design curves and profile
        best_view = None
        try:
            best_view = design_view_campaign(run_dir, best["design_hash"])
        except Exception as exc:
            print(f"[warn] failed to load best design for {ename}: {exc}", file=sys.stderr)

        # loading scalars from campaign.json (pre-computed by orchestrator)
        loading_scalars = job.get("loading_scalars") or {}

        # Target
        t = cfg.get("target", {})

        entries_out.append({
            "name": ename,
            "group": entry.get("group", ""),
            "symmetry": entry.get("symmetry", ""),
            "n_knobs": n_knobs,
            "n_evals": n_total,
            "n_ok": n_ok,
            "fails": fails,
            "best_j": best_j,
            "seed_j": seed_j,
            "terms_best": terms_best,
            "loading": loading_scalars,
            "run_dir": str(run_dir),
            "knobs": {k: round(float(v), 4) if isinstance(v, (int, float)) else v
                      for k, v in knobs.items()},
            "derived": derived_info,
            "best": best_view,
            "target": t,
        })

    entries_out.sort(key=lambda e: e["best_j"])

    return {
        "brief_name": cdata.get("brief_name", ""),
        "tier": cdata.get("tier", ""),
        "campaign_dirname": campaign_dirname,
        "timestamp_utc": cdata.get("timestamp_utc", ""),
        "entries": entries_out,
    }


# ---------------------------------------------------------------------------
# Run-explorer data (unchanged)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Campaign data
# ---------------------------------------------------------------------------
campaigns_out = []
for cp_path in args.campaigns:
    c = load_campaign(cp_path, EXCLUDES)
    if c is not None:
        campaigns_out.append(c)
        print(f"campaign {c['brief_name']} ({c['tier']}) {len(c['entries'])} entries")

OUT.write_text(json.dumps({"runs": runs_out, "campaigns": campaigns_out}, separators=(",", ":")))
print("bytes", OUT.stat().st_size)
