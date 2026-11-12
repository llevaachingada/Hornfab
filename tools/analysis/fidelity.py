"""A.10 fidelity.py — screen-vs-verify bias and within-run rank agreement.

Usage:  PY tools\\analysis\\fidelity.py --run <dir> --out <dir>

For every design that appears in BOTH the run's screen rows (``search.ndjson``) and its
verify rows (``verify/search.ndjson``): the verify-vs-screen J bias (the winner's curse —
the screen optimistically wins, 95% of pairs are worse on verify per the 2026-11-12
study) and the run-internal rank agreement (Spearman over all paired designs and over the
screen top 5 only). Schema: ``tools/analysis/schema.md`` § fidelity.json.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from _common import add_out_arg, fail, load_run, read_ndjson, spearman, valid_rows, write_report

TOOL = "fidelity"


def analyse_run(run_dir: Path) -> dict:
    run = load_run(Path(run_dir))
    meta = run["meta"]
    screen = valid_rows(run["rows"])
    verify = valid_rows(read_verify_rows(run_dir)) + \
        valid_rows([r for r in screen if str(r.get("mode", "")) == "verify"])
    by_design_screen = {}
    for r in screen:
        if str(r.get("mode", "")) == "verify":
            continue
        dh = r.get("design_hash")
        if dh is not None and (dh not in by_design_screen or
                               (r.get("n") or 0) > (by_design_screen[dh].get("n") or 0)):
            by_design_screen[str(dh)] = r
    by_design_verify = {}
    for r in verify:
        dh = r.get("design_hash")
        if dh is not None and (dh not in by_design_verify or
                               (r.get("n") or 0) > (by_design_verify[dh].get("n") or 0)):
            by_design_verify[str(dh)] = r
    pairs = []
    for dh in sorted(set(by_design_screen) & set(by_design_verify)):
        js = float(by_design_screen[dh]["objective"])
        jv = float(by_design_verify[dh]["objective"])
        pairs.append({"design_hash": dh, "j_screen": js, "j_verify": jv,
                      "bias_pct": (jv - js) / max(abs(js), 1e-12) * 100.0})
    bias_median = float(np.median([p["bias_pct"] for p in pairs])) if pairs else None
    rho_all = spearman([p["j_screen"] for p in pairs], [p["j_verify"] for p in pairs]) \
        if len(pairs) >= 3 else None
    top5 = sorted(pairs, key=lambda p: p["j_screen"])[:5]
    rho_top5 = spearman([p["j_screen"] for p in top5], [p["j_verify"] for p in top5]) \
        if len(top5) == 5 else None
    return {"run_dir": str(run["run_dir"]), "brief": meta["brief"],
            "objective_version": meta["objective_version"], "family": meta["family"],
            "n_screen": len(by_design_screen), "n_verify": len(by_design_verify),
            "n_pairs": len(pairs), "pairs": pairs,
            "bias_median_pct": bias_median, "spearman_all": rho_all, "spearman_top5": rho_top5,
            "note": "bias = (J_verify - J_screen)/J_screen * 100; top-5 agreement is the "
                    "screen's own ranking ability among its finalists"}


def read_verify_rows(run_dir: Path) -> list[dict]:
    return read_ndjson(Path(run_dir) / "verify" / "search.ndjson")


def _md(payload: dict) -> str:
    md_bias = (f"{payload['bias_median_pct']:.1f}%"
               if payload["bias_median_pct"] is not None else "—")
    lines = ["# Screen-vs-verify fidelity", "",
             f"Run `{Path(payload['run_dir']).name}` (brief `{payload['brief']}`, "
             f"objective v{payload['objective_version']}): "
             f"{payload['n_pairs']} paired design(s).", "",
             f"- median verify-vs-screen bias: **{md_bias}**",
             f"- Spearman (all paired designs): **{payload['spearman_all']}**",
             f"- Spearman (screen top 5 only): **{payload['spearman_top5']}**", ""]
    if payload["pairs"]:
        lines += ["| design | J screen | J verify | bias % |", "|---|---:|---:|---:|"]
        for p in payload["pairs"]:
            lines.append(f"| `{p['design_hash']}` | {p['j_screen']:.4f} | "
                         f"{p['j_verify']:.4f} | {p['bias_pct']:+.1f}% |")
        lines.append("")
    lines += [f"_{payload['note']}_", ""]
    return "\n".join(lines)


def charts(payload: dict) -> dict:
    """Chart factory for main() and report_day.py: J_screen vs J_verify scatter."""
    def fn(plt):
        pairs = payload["pairs"]
        if len(pairs) < 3:
            return None
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.scatter([p["j_screen"] for p in pairs], [p["j_verify"] for p in pairs], s=20)
        lo = min(min(p["j_screen"], p["j_verify"]) for p in pairs)
        hi = max(max(p["j_screen"], p["j_verify"]) for p in pairs)
        ax.plot([lo, hi], [lo, hi], "k--", lw=0.8)
        ax.set_xlabel("J screen")
        ax.set_ylabel("J verify")
        if payload["bias_median_pct"] is not None:
            ax.set_title(f"bias median {payload['bias_median_pct']:+.1f}%")
        fig.tight_layout()
        return fig
    return {"fidelity.png": fn}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=( __doc__ or "").splitlines()[0])
    ap.add_argument("--run", required=True, help="run dir holding the screen rows (and a verify/ subdir or verify rows)")
    add_out_arg(ap)
    args = ap.parse_args(argv)
    try:
        payload = analyse_run(Path(args.run))
    except (FileNotFoundError, ValueError) as exc:
        raise fail(f"fidelity: {exc}") from exc

    write_report(Path(args.out), TOOL, payload, _md(payload), charts(payload))
    print(f"fidelity OK: {payload['n_pairs']} pair(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
