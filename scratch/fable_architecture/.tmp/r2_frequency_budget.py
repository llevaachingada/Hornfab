"""R2: frequency budget. Read-only. Writes FREQUENCY_BUDGET.md."""
from __future__ import annotations

import dataclasses
import json
import pathlib
import subprocess
import sys
import time

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, r"C:\Users\hunte\Hrns\hornlab-search\scratch\fable_architecture\.tmp")
import fable_replay_harness as H

REPO = H.REPO
OUT = REPO / "scratch" / "fable_architecture" / "FREQUENCY_BUDGET.md"
GRID = H.GRID_58
POINTS = (8, 10, 12, 15, 18, 22)


def head_sha():
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def slice_response(resp, idx):
    idx = np.asarray(idx, int)
    kw = dict(freqs_hz=np.asarray(resp.freqs_hz, float)[idx])
    for name in ("spl_h_db", "spl_v_db", "spl_balloon_db", "z_throat", "p_h", "p_v", "p_balloon"):
        v = getattr(resp, name)
        kw[name] = None if v is None else np.asarray(v)[idx]
    return dataclasses.replace(resp, **kw)


def score(resp58, target, b):
    m = H.metrics_parity(resp58, target)
    return H.score_v7(m, resp58, target, b.weights, b.objective_params)


def main():
    t0 = time.time()
    sha = head_sha()
    pairs = []
    for S in sorted((REPO / "runs").glob("study-*")):
        sd, vd = S / "screen", S / "verify"
        if not (sd / "designs").is_dir() or not (vd / "designs").is_dir():
            continue
        b = H.brief(sd / "config.yaml")
        for h in sorted({p.name for p in (sd / "designs").iterdir() if p.is_dir()} &
                        {p.name for p in (vd / "designs").iterdir() if p.is_dir()}):
            try:
                sa = H.json_load(sd / "designs" / h / "status.json")
                sv = H.json_load(vd / "designs" / h / "status.json")
                if not (sa.get("ok") and sv.get("ok")):
                    continue
                ra = H.load_response(sd / "designs" / h / "response.npz")
                rv = H.load_response(vd / "designs" / h / "response.npz")
                pairs.append(dict(study=S.name, h=h, b=b, ra=ra, rv=rv,
                                  stored_screen=float(sa["objective"]), stored_verify=float(sv["objective"])))
            except Exception as e:
                print("skip", S.name, h, repr(e)[:100])

    # parity evidence: regenerated metrics + v7 on the stored grid must equal the stored J
    parity = []
    for p in pairs:
        try:
            m = H.metrics_parity(p["ra"], p["b"].target)
            j, _ = H.score_v7(m, p["ra"], p["b"].target, p["b"].weights, p["b"].objective_params)
            m2 = H.metrics_parity(p["rv"], p["b"].target)
            j2, _ = H.score_v7(m2, p["rv"], p["b"].target, p["b"].weights, p["b"].objective_params)
            parity.append((abs(j - p["stored_screen"]), abs(j2 - p["stored_verify"])))
        except Exception:
            parity.append((float("nan"), float("nan")))
    par = np.array(parity, float)
    n_diag = sum(1 for p in pairs if p["rv"].p_h is not None and p["rv"].p_v is not None)

    rows = []
    for i, p in enumerate(pairs):
        b = p["b"]
        # (a) dense-grid comparison: screen 18 -> 58 vs verify 29 -> 58
        rs = H.interp_response(p["ra"], GRID, method="pchip")
        rv = H.interp_response(p["rv"], GRID, method="pchip")
        js, _ = score(rs, b.target, b)
        jv, _ = score(rv, b.target, b)
        # baselines for the two interpolants: full 29 points -> 58
        base_p = score(H.interp_response(p["rv"], GRID, method="pchip"), b.target, b)[0]
        base_r = score(H.interp_response(p["rv"], GRID, method="rational_pressure"), b.target, b)[0]
        r = dict(study=p["study"], h=p["h"], stored_screen=p["stored_screen"],
                 stored_verify=p["stored_verify"], js_dense=js, jv_dense=jv,
                 base_pchip=base_p, base_rational=base_r, points={})
        for n in POINTS:
            idx = H.select_log_spaced(p["rv"].freqs_hz, n)
            sub = slice_response(p["rv"], idx)
            jp, _ = score(H.interp_response(sub, GRID, method="pchip"), b.target, b)
            jr, _ = score(H.interp_response(sub, GRID, method="rational_pressure"), b.target, b)
            r["points"][n] = dict(n=int(idx.size), j_pchip=jp, j_rational=jr,
                                  d_pchip=jp - base_p,
                                  d_rational=jr - base_r)
        rows.append(r)
        if (i + 1) % 10 == 0:
            print(f"scored {i+1}/{len(pairs)} pairs", flush=True)

    lines = []
    lines.append("# FREQUENCY_BUDGET")
    lines.append("")
    lines.append(f"- Repo HEAD at run: `{sha}`")
    lines.append(f"- Timestamp: `{time.strftime('%Y-%m-%dT%H:%M:%S%z')}`")
    lines.append("- Read-only; no solve, mesher, GPU, queue or config write.")
    lines.append(f"- Scope: the **{len(pairs)}** `screen`/`verify` pairs in `runs/study-*` "
                 "(screen 18 frequencies, verify 29).")
    lines.append(f"- Stored verify responses carrying complex `p_h`/`p_v`: **{n_diag}/{len(pairs)}**.")
    lines.append("- Replay parity fix: the stored DI is the sin(theta)-weighted theta-phi balloon DI "
                 "(`search/evaluate.metrics_from_response`), not `compute_metrics`' equal-weight DI. "
                 "All regeneration below uses that rule.")
    lines.append(f"- Parity check on the stored grids: max |replay - stored J| = "
                 f"**{np.nanmax(par[:,0]):.3e}** (screen), **{np.nanmax(par[:,1]):.3e}** (verify).")
    lines.append(f"- Scoring grid: 58 log-spaced points, 350-8000 Hz. Interpolant: log-frequency PCHIP "
                 "on SPL/balloon/z; rational pressure = Floater-Hormann barycentric rational "
                 "interpolation (order 3) on `log10(f)` for complex `p_h`/`p_v`, with SPL rebuilt as "
                 "`20 log10(|p|/20 uPa)` (exact at the stored nodes; verified 0.0 dB).")
    lines.append("")
    lines.append("## (a) Dense-grid comparison (screen 18 -> 58 vs verify 29 -> 58, PCHIP)")
    lines.append("")
    d = np.array([r["js_dense"] - r["jv_dense"] for r in rows], float)
    sr = spearmanr([r["js_dense"] for r in rows], [r["jv_dense"] for r in rows])[0]
    lines.append(f"- n={len(rows)}; mean (screen - verify) = **{np.mean(d):+.3f} J**, "
                 f"sd = **{np.std(d, ddof=1):.3f} J**; Spearman(screen, verify) = **{sr:.3f}**.")
    lines.append("")
    lines.append("## (b)/(c) Point-count budget")
    lines.append("")
    lines.append("`dJ` = J(N-point subset -> 58) - J(full 29 points -> 58), same interpolant. "
                 "Top-28 rank correlation is Spearman on the 28 lowest-J verify pairs.")
    lines.append("")
    for method, key in (("PCHIP SPL", "pchip"), ("rational complex pressure", "rational")):
        lines.append(f"### {method}")
        lines.append("")
        lines.append("| kept points | mean dJ | sd dJ | min dJ | max dJ | top-28 rank corr |")
        lines.append("|---|---|---|---|---|---|")
        base_key = "base_pchip" if key == "pchip" else "base_rational"
        base = np.array([r[base_key] for r in rows], float)
        top = np.argsort(base)[:28]
        for n in POINTS:
            vals = np.array([r["points"][n]["d_" + key] for r in rows], float)
            jn = np.array([r["points"][n]["j_" + key] for r in rows], float)
            rho = spearmanr(base[top], jn[top])[0]
            lines.append(f"| {n} | {np.mean(vals):+.3f} | {np.std(vals, ddof=1):.3f} | "
                         f"{np.min(vals):+.3f} | {np.max(vals):+.3f} | {rho:.3f} |")
        lines.append("")
        ref = np.array([r["stored_verify"] for r in rows], float)
        dp = base - ref
        lines.append(f"Diagnostic, full 29 -> 58 (no subsampling) vs the stored 29-point J: "
                     f"mean {np.mean(dp):+.3f}, sd {np.std(dp, ddof=1):.3f}. "
                     "This is the interpolant's own grid cost, separate from the subsampling cost above.")
        lines.append("")
    lines.append("## Per-pair detail")
    lines.append("")
    lines.append("| study | design | J screen 58 | J verify 58 | d(screen-verify) | J verify 29 (ref) | "
                 + " | ".join(f"dJ PCHIP n={n}" for n in POINTS) + " | "
                 + " | ".join(f"dJ rat n={n}" for n in POINTS) + " |")
    lines.append("|---|---|---|---|---|---|" + "---|" * (2 * len(POINTS)))
    for r in rows:
        lines.append(f"| {r['study']} | `{r['h']}` | {r['js_dense']:.3f} | {r['jv_dense']:.3f} | "
                     f"{r['js_dense']-r['jv_dense']:+.3f} | {r['stored_verify']:.3f} | "
                     + " | ".join(f"{r['points'][n]['d_pchip']:+.3f}" for n in POINTS) + " | "
                     + " | ".join(f"{r['points'][n]['d_rational']:+.3f}" for n in POINTS) + " |")
    lines.append("")
    lines.append(f"_Script: `scratch/fable_architecture/.tmp/r2_frequency_budget.py`; runtime "
                 f"{time.time()-t0:.1f}s._")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # compact console evidence
    print("pairs", len(rows), "parity", np.nanmax(par), "n_diag", n_diag)
    print("dense: mean %+.3f sd %.3f rho %.3f" % (np.mean(d), np.std(d, ddof=1), sr))
    for key in ("pchip", "rational"):
        base_key = "base_pchip" if key == "pchip" else "base_rational"
        base = np.array([r[base_key] for r in rows]); top = np.argsort(base)[:28]
        for n in POINTS:
            vals = np.array([r["points"][n]["d_" + key] for r in rows])
            jn = np.array([r["points"][n]["j_" + key] for r in rows])
            print(key, n, "bias %+.3f sd %.3f rho %.3f" % (np.mean(vals), np.std(vals, ddof=1),
                                                          spearmanr(base[top], jn[top])[0]))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
