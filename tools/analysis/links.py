"""A.4 links.py — candidate linked knobs for one search run (feeds Group B's `links:`).

Usage:  PY tools\\analysis\\links.py --run <dir> --out <dir>

Two independent evidence sources for knobs that move together:
1. data: Spearman |rho| >= 0.6 between knob pairs on the TOP-DECILE valid rows, with a
   least-squares proposal ``knob_b = scale * knob_a + offset`` (raw knob units) and its R²;
2. the CMA search-distribution covariance (``run.json`` ``cma_covariance`` or
   ``cma/covariance.json``): eigenpairs whose 2-3 largest |loadings| carry >= 0.85 of the
   eigenvector's abs-loadings norm — one dominant direction across a few knobs.
Schema: ``tools/analysis/schema.md`` § links.json.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

from _common import (add_out_arg, fail, load_run, knobs_shared, params_flat, spearman,
                     top_decile, valid_rows, write_report)

TOOL = "links"
RHO_MIN = 0.6          # pairs below this never get a proposal
DOMINANT_COVER = 0.85  # fraction of the eigenvector's abs-loadings norm carried by its top 2-3 knobs
MIN_TOP_ROWS = 5


def _fit(x: list[float], y: list[float]) -> dict | None:
    """Least squares ``y = scale * x + offset`` with R²."""
    xv = np.asarray(x, dtype=float)
    yv = np.asarray(y, dtype=float)
    good = np.isfinite(xv) & np.isfinite(yv)
    xv, yv = xv[good], yv[good]
    if xv.size < 3 or np.ptp(xv) == 0 or np.ptp(yv) == 0:
        return None
    scale, offset = np.polyfit(xv, yv, 1)
    pred = scale * xv + offset
    ss_res = float(np.sum((yv - pred) ** 2))
    ss_tot = float(np.sum((yv - yv.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None
    return {"scale": float(scale), "offset": float(offset), "r2": r2}


def analyse_run(run_dir: Path) -> dict:
    run = load_run(Path(run_dir))
    top = top_decile(run["rows"])
    out: dict = {"run_dir": str(run["run_dir"]), "family": run["meta"]["family"],
                 "top_decile_n": len(top) if top else 0,
                 "pairs": [], "cma_directions": [], "proposed_links": []}
    if not top or len(top) < MIN_TOP_ROWS:
        return out
    keys = knobs_shared(top)
    pmat = [params_flat(r) for r in top]

    def series(key):
        return [p[key] for p in pmat]

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            rho = spearman(series(keys[i]), series(keys[j]))
            if rho is None or abs(rho) < RHO_MIN:
                continue
            fit = _fit(series(keys[i]), series(keys[j]))
            pair = {"a": keys[i], "b": keys[j], "rho": rho, "fit": fit}
            out["pairs"].append(pair)
            if fit is not None and fit["r2"] is not None:
                out["proposed_links"].append({"knob_b": keys[j], "knob_a": keys[i],
                                              "scale": fit["scale"], "offset": fit["offset"],
                                              "r2": fit["r2"], "source": "rho_top_decile"})
    out["pairs"].sort(key=lambda p: -abs(p["rho"]))
    out["proposed_links"].sort(key=lambda p: -(p["r2"] or 0.0))
    out["cma_directions"] = _cma_directions(run)
    return out


def _cma_directions(run: dict) -> list[dict]:
    """Eigenpairs of the final CMA covariance with one dominant direction across 2-3 knobs."""
    from _common import read_json

    cov = None
    run_json = read_json(Path(run["run_dir"]) / "run.json")
    if isinstance(run_json, dict) and isinstance(run_json.get("cma_covariance"), dict):
        cov = run_json["cma_covariance"]
    else:
        side = Path(run["run_dir"]) / "cma" / "covariance.json"
        data = read_json(side)
        cov = data if isinstance(data, dict) else None
    if not isinstance(cov, dict):
        return []
    eigenpairs = cov.get("eigenpairs") or []
    out = []
    for ep in eigenpairs:
        if not isinstance(ep, dict):
            continue
        loadings = [l for l in (ep.get("top_loadings") or []) if isinstance(l, dict)
                    and isinstance(l.get("loading"), (int, float))]
        if len(loadings) < 2:
            continue
        norm = math.sqrt(sum(l["loading"] ** 2 for l in loadings))
        if norm <= 0:
            continue
        want, cover = None, 0.0
        for k in (2, 3):
            if k > len(loadings):
                break
            c = math.sqrt(sum(l["loading"] ** 2 for l in loadings[:k])) / norm
            if c >= DOMINANT_COVER:
                want, cover = k, c
                break
        if want is None:
            continue
        out.append({"rank": ep.get("rank"), "eigenvalue": ep.get("eigenvalue"),
                    "fraction": ep.get("fraction"),
                    "keys": [l["key"] for l in loadings[:want]],
                    "loadings": {l["key"]: l["loading"] for l in loadings[:want]}})
    return out


def _md(payload: dict) -> str:
    lines = ["# Link candidates", "",
             f"Run `{Path(payload['run_dir']).name}` — top-decile rows: {payload['top_decile_n']}.", ""]
    if payload["pairs"]:
        lines += [f"Knob pairs with |rho| >= {RHO_MIN} (top-decile), with the proposed"
                  " linear link:", "",
                  "| a | b | rho | scale | offset | R² |", "|---|---|---:|---:|---:|---:|"]
        for p in payload["pairs"]:
            f = p["fit"]
            lines.append(f"| `{p['a']}` | `{p['b']}` | {p['rho']:+.3f} | "
                         + (f"{f['scale']:.4g} | {f['offset']:.4g} | "
                            + (f"{f['r2']:.3f}" if f["r2"] is not None else "—") if f else "— | — | — |"))
        lines.append("")
    else:
        lines += [f"No knob pairs with |rho| >= {RHO_MIN} in the top decile.", ""]
    if payload["cma_directions"]:
        lines += ["### CMA covariance directions (2-3 knobs, one dominant direction)", "",
                  "| rank | eigenvalue | fraction | keys | loadings |", "|---|---:|---:|---|---|"]
        for d in payload["cma_directions"]:
            lo = ", ".join(f"{k}:{v:+.2f}" for k, v in d["loadings"].items())
            lines.append(f"| {d['rank']} | {d['eigenvalue']:.4g} | {d['fraction']:.3f} | "
                         f"{', '.join(f'`{k}`' for k in d['keys'])} | {lo} |")
        lines.append("")
    if payload["proposed_links"]:
        lines += ["### Proposed `links:` entries (Group B)", ""]
        for p in payload["proposed_links"]:
            lines.append(f"- `{p['knob_b']} = {p['scale']:.4g} * {p['knob_a']} + {p['offset']:.4g}"
                         f"` (R² {p['r2']:.3f})")
        lines.append("")
    return "\n".join(lines)


def charts(payload: dict) -> dict:
    """PNG charts for this report (used by main() and by report_day)."""
    def fn(plt):
        links = [p for p in payload["proposed_links"] if p["r2"] is not None]
        if not links:
            return None
        run = load_run(Path(payload["run_dir"]))
        top = top_decile(run["rows"]) or []
        link = links[0]
        xs = [params_flat(r)[link["knob_a"]] for r in top if link["knob_a"] in params_flat(r)]
        ys = [params_flat(r)[link["knob_b"]] for r in top if link["knob_b"] in params_flat(r)]
        if len(xs) != len(ys) or len(xs) < 3:
            return None
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.scatter(xs, ys, s=18)
        xg = np.linspace(min(xs), max(xs), 10)
        ax.plot(xg, link["scale"] * xg + link["offset"], "r--", lw=1)
        ax.set_xlabel(link["knob_a"])
        ax.set_ylabel(link["knob_b"])
        ax.set_title(f"{link['knob_b']} = {link['scale']:.3g}·{link['knob_a']} + {link['offset']:.3g}"
                     f"  (R² {link['r2']:.2f})")
        fig.tight_layout()
        return fig
    return {"links.png": fn}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=( __doc__ or "").splitlines()[0])
    ap.add_argument("--run", required=True, help="run dir")
    add_out_arg(ap)
    args = ap.parse_args(argv)
    try:
        payload = analyse_run(Path(args.run))
    except (FileNotFoundError, ValueError) as exc:
        raise fail(f"links: {exc}") from exc

    write_report(Path(args.out), TOOL, payload, _md(payload), charts(payload))
    print(f"links OK: {len(payload['proposed_links'])} proposal(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
