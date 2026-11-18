"""Phase 1 harvest: per-config hv_beamwidth / di CSVs + summary table + overlay PNGs.

Reads the 7 throat run dirs from the night summary and the canonical v8 stored baseline
(runs/20261116T025728Z-screen-cd60f7, row n=0) for the A-family comparison. Identity: the 7
sweep configs carry the v7 objective/brief identity (same as the v8 incumbent) - never mixed.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

import numpy as np

REPO = Path(r"C:\Users\hunte\Hrns\hornlab-search")
OUT = REPO / "docs" / "evidence" / "throat_hv_2026-11-18"
OUT.mkdir(parents=True, exist_ok=True)
NIGHT = REPO / "runs" / "nights" / "cd_rrect_2026-11-17"
IDS = ["throat_hv_run_B_ctl", "throat_hv_run_B_o00", "throat_hv_run_B_o25",
       "throat_hv_run_B_o50", "throat_hv_run_B_o75",
       "throat_hv_run_A_r15", "throat_hv_run_A_r20"]
V8_RUN = REPO / "runs" / "20261116T025728Z-screen-cd60f7"


def ndjson_rows(run_dir: Path):
    p = run_dir / "search.ndjson"
    if not p.exists():
        return []
    rows = []
    for ln in io.open(p, encoding="utf-8"):
        if ln.strip():
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return rows


def main() -> None:
    summary = {}
    for ln in io.open(NIGHT / "summary.jsonl", encoding="utf-8"):
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r.get("id") in IDS:
            summary[r["id"]] = r

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    curves = {}
    table = []
    for jid in IDS:
        s = summary.get(jid)
        if not s or not s.get("run_dir"):
            print("missing", jid)
            continue
        run_dir = Path(s["run_dir"])
        row = (ndjson_rows(run_dir) or [None])[-1]
        if row is None:
            print("no ndjson row", jid)
            continue
        met = row.get("metrics") or {}
        f = np.asarray(met["freqs_hz"], float)
        bwh = np.asarray(met["bw_h_deg"], float)
        bwv = np.asarray(met["bw_v_deg"], float)
        di = np.asarray(met.get("di_db", []), float) if met.get("di_db") else np.full(f.size, np.nan)
        di_source = met.get("di_source") or (row.get("scalars") or {}).get("di_source")
        cfg = jid.replace("throat_hv_run_", "")
        with (OUT / f"hv_beamwidth_{cfg}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["freq_hz", "bw_h_deg_outermost", "bw_v_deg_outermost"])
            for a, b, c in zip(f, bwh, bwv):
                w.writerow([a, b, c])
        with (OUT / f"di_{cfg}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["freq_hz", "di_db", "di_source"])
            for a, b in zip(f, di):
                w.writerow([a, b, di_source])
        curves[cfg] = (f, bwh, bwv)
        terms = row.get("terms") or {}
        table.append({
            "config": cfg, "J": row.get("objective"),
            "bws_h_mean": float(np.nanmean(bwh)), "bws_v_mean": float(np.nanmean(bwv)),
            "dofs": row.get("n_dof"), "solve_s": (row.get("seconds") or {}).get("solve"),
            "wall_s": (row.get("seconds") or {}).get("total"),
            "peak_mib": row.get("peak_vram_mb"), "vram_base_mib": s.get("vram_baseline_mb"),
            "night_peak_mib": (re.search(r"peak (\d+) MiB", s.get("note") or "") or [None, None])[1],
            "di_source": di_source, "run_dir": run_dir.name,
            "terms": {k: terms.get(k) for k in
                      ("cov", "rip", "flat", "load", "dislope", "diag", "distd", "flat_cv")},
        })

    # v8 stored baseline (same v7 identity)
    v8_rows = ndjson_rows(V8_RUN)
    v8 = min([r for r in v8_rows if r.get("ok")], key=lambda r: r["objective"]) if v8_rows else None
    if v8:
        m = v8["metrics"]
        curves["v8_stored(rho1.0)"] = (np.asarray(m["freqs_hz"], float),
                                       np.asarray(m["bw_h_deg"], float),
                                       np.asarray(m["bw_v_deg"], float))
        table.append({
            "config": "v8_stored(rho1.0)", "J": v8["objective"],
            "bws_h_mean": float(np.nanmean(m["bw_h_deg"])),
            "bws_v_mean": float(np.nanmean(m["bw_v_deg"])),
            "dofs": v8.get("n_dof"), "solve_s": (v8.get("seconds") or {}).get("solve"),
            "wall_s": (v8.get("seconds") or {}).get("total"),
            "peak_mib": v8.get("peak_vram_mb"), "vram_base_mib": None,
            "di_source": m.get("di_source"), "run_dir": V8_RUN.name,
            "terms": {k: (v8.get("terms") or {}).get(k) for k in
                      ("cov", "rip", "flat", "load", "dislope", "diag", "distd", "flat_cv")},
        })

    with (OUT / "phase1_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["config", "J", "bw_h_mean_deg", "bw_v_mean_deg", "dofs", "solve_s",
                    "wall_s", "peak_vram_mib", "night_peak_mib", "vram_baseline_mib",
                    "di_source", "run_dir", "terms"])
        for r in table:
            w.writerow([r["config"], r["J"], round(r["bws_h_mean"], 2),
                        round(r["bws_v_mean"], 2), r["dofs"],
                        round(r["solve_s"], 1) if r["solve_s"] else "",
                        round(r["wall_s"], 1) if r["wall_s"] else "",
                        r["peak_mib"], r.get("night_peak_mib", ""), r["vram_base_mib"],
                        r["di_source"], r["run_dir"],
                        json.dumps(r["terms"], sort_keys=True)])

    # overlay PNGs (H and V vs frequency), two panels per family
    for group, names, png in (
            ("B family", ["B_ctl", "B_o00", "B_o25", "B_o50", "B_o75"], "beamwidth_B.png"),
            ("A family vs v8", ["A_r15", "A_r20", "v8_stored(rho1.0)"], "beamwidth_A_vs_v8.png")):
        fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharex=True)
        for cfg in names:
            if cfg not in curves:
                continue
            f, bwh, bwv = curves[cfg]
            axes[0].plot(f, bwh, label=cfg, lw=1.6)
            axes[1].plot(f, bwv, label=cfg, lw=1.6)
        for ax, plane in zip(axes, ("H (horizontal)", "V (vertical)")):
            ax.set_xscale("log")
            ax.set_xlabel("frequency Hz")
            ax.set_ylabel("-6 dB width deg")
            ax.set_title(f"{group} - {plane}")
            ax.grid(alpha=0.3, which="both")
            ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(OUT / png, dpi=120, bbox_inches="tight")
        plt.close(fig)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
