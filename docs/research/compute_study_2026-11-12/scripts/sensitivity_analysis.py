"""
Knob sensitivity and convergence analysis for the highest-value runs.
Reads from search.ndjson files.
Run as: python -I sensitivity_analysis.py <repo_root>
"""
import sys, json, csv, math, pathlib

REPO = pathlib.Path(sys.argv[1])
RUNS = REPO / "runs"
STUDY = pathlib.Path(__file__).parent


def read_ndjson(path):
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def rank_corr(x, y):
    """Spearman rank correlation between lists x and y."""
    n = len(x)
    if n < 3:
        return 0.0
    rx = sorted(range(n), key=lambda i: x[i])
    ry = sorted(range(n), key=lambda i: y[i])
    rank_x = [0]*n
    rank_y = [0]*n
    for rank, i in enumerate(rx):
        rank_x[i] = rank
    for rank, i in enumerate(ry):
        rank_y[i] = rank
    d2 = sum((rank_x[i] - rank_y[i])**2 for i in range(n))
    return 1.0 - 6.0 * d2 / (n * (n*n - 1))


def analyze_sensitivity(run_dir, run_id):
    """Rank-correlate each knob's value with J for the top 50% of valid evals."""
    ndjson = run_dir / "search.ndjson"
    if not ndjson.exists():
        return None, None, None, None

    rows = read_ndjson(ndjson)
    valid = [r for r in rows if r.get("ok") is True]
    if len(valid) < 10:
        return None, None, None, None

    # Get J values and params
    jvals = []
    params_list = []
    for r in valid:
        j = r.get("objective")
        p = r.get("params")
        if j is None or not isinstance(p, dict):
            continue
        jvals.append(float(j))
        params_list.append(p)

    if len(jvals) < 10:
        return None, None, None, None

    # Rank-correlation of each knob with J
    all_keys = sorted(set(k for p in params_list for k in p.keys()))
    correlations = {}
    for key in all_keys:
        kvals = [p.get(key) for p in params_list]
        if any(v is None for v in kvals):
            continue
        try:
            kvals_f = [float(v) for v in kvals]
        except (TypeError, ValueError):
            continue
        # Skip constant knobs
        if max(kvals_f) == min(kvals_f):
            continue
        rho = rank_corr(kvals_f, jvals)
        correlations[key] = rho

    # Sort by absolute correlation
    sorted_keys = sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)

    # Convergence: running minimum J
    j_sorted = sorted(jvals)
    running_min = []
    cur_min = float('inf')
    for j in jvals:
        cur_min = min(cur_min, j)
        running_min.append(cur_min)

    # Is it still improving in last 20%?
    n = len(jvals)
    n_tail = max(2, n // 5)
    improving = False
    if len(running_min) >= 10:
        tail_improvement = running_min[-1] - running_min[-n_tail]
        total_improvement = running_min[-1] - running_min[0]
        if total_improvement < 0 and tail_improvement < 0:
            improving = abs(tail_improvement / total_improvement) > 0.03

    # Bound walls: check top decile knobs
    top_n = max(5, n // 10)
    top_j_thresh = j_sorted[top_n - 1]
    top_rows = [(jvals[i], params_list[i]) for i in range(len(jvals)) if jvals[i] <= top_j_thresh]

    # Find knob bounds from run.json
    rj_path = run_dir / "run.json"
    bounds = {}
    if rj_path.exists():
        try:
            rj = json.loads(rj_path.read_text(encoding="utf-8"))
            bounds = rj.get("config", {}).get("bounds", {})
        except Exception:
            pass

    at_bound = {}
    for j, p in top_rows:
        for key, val in p.items():
            if key not in bounds:
                continue
            b = bounds[key]
            lo = b.get("lo")
            hi = b.get("hi")
            if lo is None or hi is None or lo == hi:
                continue
            try:
                v = float(val)
                width = float(hi) - float(lo)
                if width <= 0:
                    continue
                frac = (v - float(lo)) / width
                if frac < 0.05:
                    at_bound[key] = at_bound.get(key, [])
                    at_bound[key].append(("lo", v, lo, hi))
                elif frac > 0.95:
                    at_bound[key] = at_bound.get(key, [])
                    at_bound[key].append(("hi", v, lo, hi))
            except (TypeError, ValueError):
                pass

    # Count designs at each bound
    bound_hits = {}
    for key, hits in at_bound.items():
        lo_count = sum(1 for h in hits if h[0] == "lo")
        hi_count = sum(1 for h in hits if h[0] == "hi")
        if lo_count > len(top_rows) // 3 or hi_count > len(top_rows) // 3:
            bound_side = "lo" if lo_count > hi_count else "hi"
            bound_hits[key] = (bound_side, lo_count, hi_count, len(top_rows),
                               float(bounds[key]["lo"]), float(bounds[key]["hi"]))

    return sorted_keys[:8], bound_hits, len(valid), improving


def main():
    # Key runs to analyze (highest-value cells)
    key_runs = [
        # (run_id, description)
        ("20261030T111108Z-screen-377bbe", "atlas__ath_core (CMA-ME, v4, 1301 evals)"),
        ("20261030T064105Z-screen-1206a5", "atlas__hyb_osse_h_hypex_v (CMA-ME, v4, 981 evals)"),
        ("20261030T170642Z-screen-fbab4f", "atlas__core_law (CMA-ME, v4, 647 evals)"),
        ("20261112T110126Z-screen-c414b1", "atlas__osse_ext_throat (CMA-ME, v5, 201 evals)"),
        ("20261112T113047Z-screen-24053e", "lecleach_rollback v6 (CMA, v6, 150 evals)"),
        ("20261027T070736Z-screen-d37d64", "native__ath_core_v4 (CMA, v4, 192 evals)"),
        ("20261027T052720Z-screen-e7f4f8", "crease__core_law_v4 (CMA, v4, 172 evals)"),
        ("20261027T062650Z-screen-36d858", "b1t__salmon_x_signed_v4 (CMA, v4, 172 evals)"),
        ("20261027T073751Z-screen-c7a1db", "b2w__osse_baseline_v4 (CMA, v4, 127 evals)"),
    ]

    out_lines = []
    for run_id, desc in key_runs:
        rd = RUNS / run_id
        if not rd.exists():
            print(f"  SKIP {run_id} (not found)")
            continue
        sorted_keys, bound_hits, n_valid, improving = analyze_sensitivity(rd, run_id)
        if sorted_keys is None:
            print(f"  SKIP {run_id} (no data)")
            continue

        out_lines.append(f"\n### {run_id} — {desc}")
        out_lines.append(f"  n_valid={n_valid}, still_improving={improving}")
        out_lines.append("  Top knob sensitivities (Spearman |rho|, negative=lower J at higher value):")
        for key, rho in sorted_keys:
            out_lines.append(f"    {key:35s}  rho={rho:+.3f}")
        if bound_hits:
            out_lines.append("  Knobs hitting bounds in top decile:")
            for key, (side, lo_c, hi_c, top_n, blo, bhi) in sorted(bound_hits.items()):
                out_lines.append(f"    {key:35s}  {side} (lo:{lo_c}/{top_n}  hi:{hi_c}/{top_n})  range=[{blo},{bhi}]")
        else:
            out_lines.append("  No knobs consistently hitting bounds in top decile.")

    out_text = "\n".join(out_lines)
    print(out_text)
    out_path = STUDY / "sensitivity_analysis.txt"
    out_path.write_text(out_text, encoding="utf-8")
    print(f"\nWritten to {out_path}")


if __name__ == "__main__":
    main()
