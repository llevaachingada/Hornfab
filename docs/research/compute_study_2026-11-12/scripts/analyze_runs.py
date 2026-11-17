"""
Read-only run inventory and analysis script for hornlab-search.
Run as: python -I analyze_runs.py <repo_root>
"""
import sys, json, csv, math, pathlib

REPO = pathlib.Path(sys.argv[1])
RUNS = REPO / "runs"
STUDY = pathlib.Path(__file__).parent
OUT_CSV = STUDY / "runs_inventory.csv"


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


def analyze_run(run_dir):
    """Return a dict of stats for one run directory."""
    ndjson = run_dir / "search.ndjson"
    if not ndjson.exists():
        return None

    # Read run.json for metadata
    run_json = run_dir / "run.json"
    rj = {}
    if run_json.exists():
        try:
            rj = json.loads(run_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    cfg = rj.get("config", {})
    name = rj.get("config_name") or cfg.get("name") or run_dir.name
    family = rj.get("family") or cfg.get("family", "")
    obj_version = rj.get("objective_version", "")
    if not obj_version:
        obj_cfg = cfg.get("objective", {})
        obj_version = obj_cfg.get("version", "")

    # brief name
    brief = ""
    brief_cfg = cfg.get("brief", {})
    if isinstance(brief_cfg, dict):
        brief = brief_cfg.get("name", "")
    if not brief:
        bfile = cfg.get("brief_file", "")
        if bfile:
            brief = pathlib.Path(bfile).stem

    # algorithm
    srch_cfg = cfg.get("search", {})
    algorithm = srch_cfg.get("algorithm", "cma")
    cma_seed = rj.get("cma_seed") or srch_cfg.get("seed", "")
    dof_cap = cfg.get("mesh", {}).get("dof_cap_screen", cfg.get("mesh", {}).get("dof_cap_verify", ""))

    # stats from run.json
    stats = rj.get("stats", {}) or {}
    failures_by_reason = stats.get("failures_by_reason", {})
    s_per_cand_rj = stats.get("mean_seconds_per_candidate", None)

    # Parse ndjson rows
    rows = read_ndjson(ndjson)
    if not rows:
        return None

    n_total = len(rows)
    refusals = {}
    valid_rows = []
    j_values = []
    dofs_list = []
    solve_times = []

    for r in rows:
        ok = r.get("ok")
        err = r.get("error", "")
        if ok is True:
            valid_rows.append(r)
            j = r.get("objective")
            if j is not None:
                try:
                    j_values.append(float(j))
                except:
                    pass
            d = r.get("n_dof")
            if d is not None:
                try:
                    dofs_list.append(int(d))
                except:
                    pass
            secs = r.get("seconds", {})
            if isinstance(secs, dict):
                st = secs.get("solve") or secs.get("total")
                if st:
                    try:
                        solve_times.append(float(st))
                    except:
                        pass
        elif ok is False or (ok is None and err):
            # Failed row
            if err:
                kind = err.split(":")[0].strip() if ":" in err else err[:30]
            else:
                kind = "unknown"
            refusals[kind] = refusals.get(kind, 0) + 1

    n_valid = len(valid_rows)
    n_refused = n_total - n_valid

    # Seed J from run.json
    seed_j = None
    seed_info = rj.get("seed", {})
    if seed_info:
        seed_j = seed_info.get("objective")
    if seed_j is None and valid_rows:
        j0 = valid_rows[0].get("objective")
        if j0 is not None:
            try:
                seed_j = float(j0)
            except:
                pass

    best_j = rj.get("best", {}).get("objective")
    if best_j is None:
        best_j = min(j_values) if j_values else None

    # Evals to reach within 5% of best
    evals_to_near_best = ""
    if best_j is not None and j_values:
        threshold = best_j * 1.05
        # Count total rows, not just valid, to track eval number
        ok_count = 0
        for r in rows:
            if r.get("ok") is True:
                ok_count += 1
                j = r.get("objective")
                if j is not None and float(j) <= threshold:
                    evals_to_near_best = ok_count
                    break

    # Last 20% improvement (is it still improving?)
    still_improving = False
    if len(j_values) >= 10:
        n_last = max(2, len(j_values) // 5)
        last_portion = j_values[-n_last:]
        prev_portion = j_values[-2*n_last:-n_last]
        if prev_portion and last_portion:
            if min(last_portion) < min(prev_portion) * 0.995:
                still_improving = True

    # Median dofs and s/eval
    med_dofs = ""
    med_s = ""
    if dofs_list:
        dofs_list.sort()
        med_dofs = dofs_list[len(dofs_list) // 2]
    if solve_times:
        solve_times.sort()
        med_s = round(solve_times[len(solve_times) // 2], 1)
    elif s_per_cand_rj:
        med_s = round(s_per_cand_rj, 1)

    # Refusal breakdown: use run.json stats if ndjson didn't parse them
    if not refusals and failures_by_reason:
        refusals = failures_by_reason
    refusal_detail = "; ".join(f"{k}:{v}" for k, v in sorted(refusals.items()))

    # QD info if atlas
    qd_info = rj.get("qd", {})
    occupied_bins = qd_info.get("occupied_bins", "") if qd_info else ""
    total_bins = qd_info.get("total_bins", "") if qd_info else ""
    qd_coverage = ""
    if qd_info:
        c = qd_info.get("coverage", "")
        if c:
            qd_coverage = f"{float(c):.3f}"

    started = rj.get("started_utc", "")[:10] if rj.get("started_utc") else ""
    finished = rj.get("finished_utc", "")[:10] if rj.get("finished_utc") else ""

    return {
        "run_dir": run_dir.name,
        "config_name": name,
        "family": family,
        "brief": brief,
        "obj_version": obj_version,
        "algorithm": algorithm,
        "cma_seed": cma_seed,
        "n_total": n_total,
        "n_valid": n_valid,
        "n_refused": n_refused,
        "refusal_detail": refusal_detail,
        "seed_J": f"{seed_j:.4f}" if seed_j is not None else "",
        "best_J": f"{best_j:.5f}" if best_j is not None else "",
        "evals_to_5pct": evals_to_near_best,
        "still_improving": still_improving,
        "med_dofs": med_dofs,
        "med_s_per_eval": med_s,
        "dof_cap": dof_cap,
        "occupied_bins": occupied_bins,
        "total_bins": total_bins,
        "qd_coverage": qd_coverage,
        "started": started,
        "finished": finished,
    }


def main():
    results = []
    run_dirs = sorted([d for d in RUNS.iterdir() if d.is_dir() and (d / "search.ndjson").exists()])
    print(f"Found {len(run_dirs)} runs with search.ndjson under runs/")

    for rd in run_dirs:
        try:
            r = analyze_run(rd)
            if r:
                results.append(r)
        except Exception as e:
            print(f"  ERROR in {rd.name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nInventoried {len(results)} runs")

    # By family
    by_family = {}
    for r in results:
        fam = r["family"] or "(unknown)"
        by_family.setdefault(fam, []).append(r)

    print("\n--- Summary by family ---")
    for fam in sorted(by_family):
        runs_f = by_family[fam]
        best_js = [float(r["best_J"]) for r in runs_f if r["best_J"]]
        n_valid_total = sum(int(r["n_valid"]) for r in runs_f if r["n_valid"])
        improving = [r for r in runs_f if r["still_improving"]]
        print(f"  {fam}: {len(runs_f)} runs, {n_valid_total} valid evals, " +
              (f"best J = {min(best_js):.4f}" if best_js else "no J") +
              (f", {len(improving)} still-improving" if improving else ""))

    print("\n--- CMA-ME (atlas) runs ---")
    atlas_runs = [r for r in results if r["algorithm"] == "cma_me"]
    for r in atlas_runs:
        print(f"  {r['run_dir']}: {r['config_name']} brief={r['brief']} "
              f"best_J={r['best_J']} n_valid={r['n_valid']} "
              f"bins={r['occupied_bins']}/{r['total_bins']} cov={r['qd_coverage']}")

    print("\n--- Still-improving runs ---")
    for r in results:
        if r["still_improving"]:
            print(f"  {r['run_dir']}: {r['config_name']} brief={r['brief']} "
                  f"best_J={r['best_J']} n_valid={r['n_valid']}")

    print("\n--- Top runs by cell (best brief/config combinations, v4+ objective only) ---")
    # group by (brief, config_name) for v4+
    cells = {}
    for r in results:
        ov = str(r.get("obj_version",""))
        if ov not in ("4","5","6","7"):
            continue
        key = (r["brief"], r["config_name"])
        if key not in cells or (r["best_J"] and (not cells[key]["best_J"] or float(r["best_J"]) < float(cells[key]["best_J"]))):
            cells[key] = r
    for key in sorted(cells, key=lambda k: float(cells[k]["best_J"]) if cells[k]["best_J"] else 999):
        r = cells[key]
        print(f"  {r['brief']} | {r['config_name']}: J={r['best_J']} n={r['n_valid']} dir={r['run_dir']}")

    fieldnames = [
        "run_dir", "config_name", "family", "brief", "obj_version", "algorithm", "cma_seed",
        "n_total", "n_valid", "n_refused", "refusal_detail",
        "seed_J", "best_J", "evals_to_5pct", "still_improving",
        "med_dofs", "med_s_per_eval", "dof_cap",
        "occupied_bins", "total_bins", "qd_coverage",
        "started", "finished"
    ]

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)

    print(f"\nWritten {len(results)} rows to {OUT_CSV}")
    return results


if __name__ == "__main__":
    results = main()
