"""A.5 walls.py — bound walls of one search run and a proposed narrowed/widened box.

Usage:  PY tools\\analysis\\walls.py --run <dir> --out <dir>

A knob is AT A WALL when a large fraction of the TOP-DECILE valid rows sits within 3% of
the bound's width of lo (or hi). The proposal (input for Group B's ``narrow``, never an
automatic change): clamp the box to the top-decile span padded 5% ("narrow"); when more
than half the top decile is within 3% of a bound, widen that side by 10% and mark the
knob as a widen candidate — applying it is gated by physical safety (Group B's --wall-frac
and the owner sign-off). Schema: ``tools/analysis/schema.md`` § walls.json.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

from _common import (add_out_arg, fail, load_run, knobs_shared, params_flat, top_decile,
                     write_report)

TOOL = "walls"
WALL_REL = 0.03    # within 3% of the bound's width
WALL_FRAC = 0.5    # >= 50% of the top decile at a bound -> widen candidate (B.3 flags >50% for pinning)


def _near(v, b: float, width: float):
    """True where ``v`` is within WALL_REL of bound ``b`` (array or scalar)."""
    return np.abs(v - b) <= WALL_REL * width


def analyse_run(run_dir: Path) -> dict:
    run = load_run(Path(run_dir))
    top = top_decile(run["rows"], n_min=3)
    walls: list[dict] = []
    proposal: list[dict] = []
    if not top:
        return {"run_dir": str(run["run_dir"]), "family": run["meta"]["family"],
                "top_decile_n": 0, "walls": [], "proposal": [],
                "note": "fewer than 10 valid rows: no top decile (schema.md)"}
    keys = knobs_shared(top)
    pmat = [params_flat(r) for r in top]
    bounds = run["bounds"]
    for key in keys:
        if key not in bounds:
            continue
        lo, hi = bounds[key]
        width = hi - lo
        vals = np.array([p.get(key, np.nan) for p in pmat], dtype=float)
        good = vals[np.isfinite(vals)]
        if good.size == 0:
            continue
        frac_lo = float(np.mean(_near(good, lo, width)))
        frac_hi = float(np.mean(_near(good, hi, width)))
        entry = {"key": key, "lo": lo, "hi": hi, "frac_lo": frac_lo, "frac_hi": frac_hi,
                 "wall_lo": frac_lo >= WALL_FRAC, "wall_hi": frac_hi >= WALL_FRAC}
        walls.append(entry)
        v_lo, v_hi = float(np.min(good)), float(np.max(good))
        if entry["wall_hi"]:
            proposal.append({"key": key, "action": "widen_hi", "new_lo": lo,
                             "new_hi": hi * 1.1 if hi > 0 else hi * 0.9,
                             "reason": f"{frac_hi:.0%} of the top decile within "
                                       f"{WALL_REL:.0%} of hi; widen candidate (+10%), "
                                       "gated by physical safety"})
        elif entry["wall_lo"]:
            proposal.append({"key": key, "action": "widen_lo", "new_lo": lo * 0.9 if lo > 0 else lo * 1.1,
                             "new_hi": hi,
                             "reason": f"{frac_lo:.0%} of the top decile within "
                                       f"{WALL_REL:.0%} of lo; widen candidate (-10%), "
                                       "gated by physical safety"})
        else:
            pad = 0.05 * width
            new_lo, new_hi = max(lo, v_lo - pad), min(hi, v_hi + pad)
            if new_hi - new_lo < width * 0.98:  # only when the clamp actually narrows something
                proposal.append({"key": key, "action": "narrow", "new_lo": new_lo, "new_hi": new_hi,
                                 "reason": "top-decile span padded 5%"})
    walls.sort(key=lambda w: -(w["frac_lo"] + w["frac_hi"]))
    return {"run_dir": str(run["run_dir"]), "family": run["meta"]["family"],
            "top_decile_n": len(top), "walls": walls, "proposal": proposal,
            "wall_rel": WALL_REL, "wall_frac": WALL_FRAC,
            "note": "proposals are inputs for Group B 'narrow', never automatic config changes"}


def _md(payload: dict) -> str:
    lines = ["# Bound walls", "",
             f"Run `{Path(payload['run_dir']).name}` — {payload['top_decile_n']} top-decile rows; "
             f"a knob is a wall at {payload.get('wall_frac', WALL_FRAC):.0%} of the top decile"
             f" within {payload.get('wall_rel', WALL_REL):.0%} of a bound.", ""]
    if payload["walls"]:
        lines += ["| knob | lo | hi | frac at lo | frac at hi | wall |", "|---|---:|---:|---:|---:|---|"]
        for w in payload["walls"]:
            flag = "lo" if w["wall_lo"] else ("hi" if w["wall_hi"] else "")
            lines.append(f"| `{w['key']}` | {w['lo']} | {w['hi']} | {w['frac_lo']:.2f} | "
                         f"{w['frac_hi']:.2f} | {flag} |")
        lines.append("")
    if payload["proposal"]:
        lines += ["### Proposed box changes (Group B `narrow` inputs)", ""]
        for p in payload["proposal"]:
            lines.append(f"- **{p['action']}** `{p['key']}` -> [{p['new_lo']}, {p['new_hi']}]: {p['reason']}")
        lines.append("")
    if payload.get("note"):
        lines += [f"_{payload['note']}_", ""]
    return "\n".join(lines)


def charts(payload: dict) -> dict:
    """PNG charts for this report (used by main() and by report_day)."""
    def fn(plt):
        walls = payload["walls"]
        if not walls:
            return None
        fig, ax = plt.subplots(figsize=(7, 0.35 * len(walls) + 1.5))
        ys = list(range(len(walls)))[::-1]
        ax.scatter([w["frac_lo"] for w in walls], ys, label="frac at lo", marker="<")
        ax.scatter([w["frac_hi"] for w in walls], ys, label="frac at hi", marker=">")
        ax.axvline(WALL_FRAC, color="r", ls="--", lw=1, label=f"{WALL_FRAC:.0%} wall line")
        ax.set_yticks(ys, [w["key"] for w in walls])
        ax.set_xlabel(f"top-decile fraction within {WALL_REL:.0%} of the bound")
        ax.legend(loc="lower right", fontsize=8)
        fig.tight_layout()
        return fig
    return {"walls.png": fn}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=( __doc__ or "").splitlines()[0])
    ap.add_argument("--run", required=True, help="run dir")
    add_out_arg(ap)
    args = ap.parse_args(argv)
    try:
        payload = analyse_run(Path(args.run))
    except (FileNotFoundError, ValueError) as exc:
        raise fail(f"walls: {exc}") from exc

    write_report(Path(args.out), TOOL, payload, _md(payload), charts(payload))
    print(f"walls OK: {len(payload['walls'])} knob(s) checked, {len(payload['proposal'])} proposal(s)"
          f" -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
