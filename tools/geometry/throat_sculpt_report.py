"""Matched-pilot report for throat-sculpt cases: J deltas vs both controls, weighted terms, raw pattern
diagnostics, HF beamwidths, DI, throat resistance, and per-frequency figures. Reads ``pilot_<tag>.json``.

    .venv\\Scripts\\python.exe tools\\geometry\\throat_sculpt_report.py runs\\...\\pilot_verify_cpu.json \\
        --brief examples\\briefs\\cd_v11_2026-11-20\\room_landscape_80x50_700_hf1440_v11cd.yaml --out DIR
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SHOW_F = (2000.0, 4000.0, 5000.0, 6300.0, 8000.0)
TERM_KEYS = ("cov_profile", "load", "dislope", "di_roughness", "rip", "flat", "flat_cv",
             "cd_lw", "cd_di_std", "cd_nacc", "offaxis_smooth")


def _at(m, key, f):
    fr = np.asarray(m["freqs_hz"])
    return float(np.interp(math.log(f), np.log(fr), np.asarray(m[key], dtype=float)))


def _hf_diagnostics(metrics, target):
    from hornlab_search.targets.profile import profile_value

    frequencies = np.asarray(metrics["freqs_hz"])
    mask = (frequencies >= 4000.0) & (frequencies <= 8000.0)
    h = np.asarray(metrics["bw_h_deg"], dtype=float)[mask]
    v = np.asarray(metrics["bw_v_deg"], dtype=float)[mask]
    if not h.size:
        return dict.fromkeys(("hf_h_mae_deg", "hf_v_min_deg", "hf_v_max_deg", "hf_v_outside_samples"))
    preferred_h = [profile_value(target.coverage_profile_h, f)[0] if target.coverage_profile_h
                   else target.coverage_h_deg for f in frequencies[mask]]
    outside = None
    if target.coverage_profile_mode == "corridor" and target.coverage_profile_v:
        outside = 0
        for f, width in zip(frequencies[mask], v):
            _, lower, upper = profile_value(target.coverage_profile_v, f)
            outside += int(width < lower or width > upper)
    return {"hf_h_mae_deg": float(np.mean(np.abs(h - preferred_h))), "hf_v_min_deg": float(v.min()),
            "hf_v_max_deg": float(v.max()), "hf_v_outside_samples": outside}


def main(argv=None):
    from hornlab_search.objective.replay import load_brief_context
    from hornlab_search.objective.scalar_v11 import resolve_v11_weights
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pilot_json")
    ap.add_argument("--brief", required=True)
    ap.add_argument("--controls", nargs=2, default=("B0_parent", "B0s_station"))
    ap.add_argument("--plot", nargs="*", default=None, help="cases for the per-frequency figure")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    doc = json.loads(Path(a.pilot_json).read_text())
    rows = {k: v for k, v in doc["rows"].items() if v.get("ok")}
    failed = {k: v.get("error", "") for k, v in doc["rows"].items() if not v.get("ok")}
    bctx = load_brief_context(Path(a.brief))
    w = resolve_v11_weights(bctx.weights, bctx.objective_params)
    c0, c1 = (rows.get(c) for c in a.controls)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    table = []
    for name, r in rows.items():
        m = r["metrics"]
        wt = {k: r["terms"].get(k, 0.0) * w.get(k, 0.0) for k in TERM_KEYS if k in w}
        row = {"case": name, "J": r["J_v11"] if r["J_v11"] is not None else r["J_v11_extended_band_NOT_COMPARABLE"],
               "dJ_vs_parent": None if c0 is None or r["J_v11"] is None else r["J_v11"] - c0["J_v11"],
               "dJ_vs_station": None if c1 is None or r["J_v11"] is None else r["J_v11"] - c1["J_v11"],
               "n_dof": r["n_dof"], "z_mean_band": m["scalars"].get("z_mean_band"),
               "bw_h_mean": m["scalars"].get("bw_h_mean_deg"), "bw_v_mean": m["scalars"].get("bw_v_mean_deg"),
               "di_mean": m["scalars"].get("di_mean_db")}
        for f in SHOW_F:
            row[f"bwH_{int(f)}"] = _at(m, "bw_h_deg", f)
            row[f"bwV_{int(f)}"] = _at(m, "bw_v_deg", f)
        row["DI_8000"] = _at(m, "di_db", 8000.0)
        row["onaxis_8000"] = _at(m, "on_axis_db", 8000.0)
        row.update(_hf_diagnostics(m, bctx.target))
        row.update({key: r["terms"].get(key) for key in ("diag", "distd", "rez_min_from_fx", "lfp50_hz")})
        row.update({f"w_{k}": v for k, v in wt.items()})
        table.append(row)
    table.sort(key=lambda r: r["J"])
    keys = list(table[0].keys())
    with open(out / "pilot_table.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=keys)
        wr.writeheader()
        for r in table:
            wr.writerow({k: (f"{v:.5g}" if isinstance(v, float) else v) for k, v in r.items()})
    # markdown
    md = ["| case | J v11 | ΔJ vs parent | ΔJ vs station ctl | H bw 4k/6.3k/8k | V bw 4k/6.3k/8k | DI 8k | z̄ band | "
          "w·load | w·cov | diag (raw) | distd (raw) | w·dislope | w·offaxis |",
          "|---|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]

    for r in table:
        dp = "" if r["dJ_vs_parent"] is None else format(r["dJ_vs_parent"], "+.4f")
        md.append(f"| {r['case']} | {r['J']:.4f} | {dp} | "
                  f"{'' if r['dJ_vs_station'] is None else format(r['dJ_vs_station'], '+.4f')} | "
                  f"{r['bwH_4000']:.0f}/{r['bwH_6300']:.0f}/{r['bwH_8000']:.0f} | {r['bwV_4000']:.0f}/{r['bwV_6300']:.0f}/{r['bwV_8000']:.0f} | "
                  f"{r['DI_8000']:.2f} | {r['z_mean_band']:.3f} | {r.get('w_load', 0):.3f} | {r.get('w_cov_profile', 0):.3f} | "
                  f"{r['diag']:.3f} | {r['distd']:.3f} | {r.get('w_dislope', 0):.3f} | {r.get('w_offaxis_smooth', 0):.3f} |")
    if failed:
        md.append("")
        md += [f"- {k}: FAILED {v}" for k, v in failed.items()]
    (out / "pilot_table.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    sys.stdout.buffer.write(("\n".join(md) + "\n").encode("utf-8"))
    # figures
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sel = a.plot or [r["case"] for r in table[:5]] + [c for c in a.controls if c in rows]
    fig, axs = plt.subplots(2, 2, figsize=(13, 8.5))
    for name in dict.fromkeys(sel):
        if name not in rows:
            continue
        m = rows[name]["metrics"]
        ls = "--" if name in a.controls else "-"
        lw = 2.0 if name in a.controls else 1.1
        fr = np.asarray(m["freqs_hz"])
        axs[0, 0].semilogx(fr, m["bw_h_deg"], ls, lw=lw, label=name)
        axs[0, 1].semilogx(fr, m["bw_v_deg"], ls, lw=lw, label=name)
        axs[1, 0].semilogx(fr, m["di_db"], ls, lw=lw, label=name)
        axs[1, 1].semilogx(fr, m["z_throat_real"], ls, lw=lw, label=name)
    for ax, t in zip(axs.flat, ("-6 dB beamwidth H (deg)", "-6 dB beamwidth V (deg)", "DI (dB, balloon)",
                                "Re z_throat (normalised)")):
        ax.set_title(t, fontsize=9); ax.grid(alpha=0.3); ax.set_xlim(500, 8500)
    axs[0, 0].axhspan(60, 90, color="g", alpha=0.07); axs[0, 1].axhspan(40, 60, color="g", alpha=0.07)
    axs[0, 0].set_ylim(30, 140); axs[0, 1].set_ylim(20, 140)
    axs[0, 0].legend(fontsize=7)
    fig.suptitle(f"Throat-sculpt matched pilot ({Path(a.pilot_json).name}); dashed = controls; green = brief corridor")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out / "pilot_curves.png", dpi=110)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
