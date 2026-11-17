"""Read-only watchdog replay over historical search.ndjson prefixes.
Pure CPU. Imports only tools.run_campaign_night.watchdog_verdict (no GPU/mesh/solve).
Writes only under scratch/fable_architecture/.tmp/."""
import json, os, sys, importlib.util
from pathlib import Path

REPO = Path(r"C:\Users\hunte\Hrns\hornlab-search")
spec = importlib.util.spec_from_file_location("rcn", REPO / "tools" / "run_campaign_night.py")
night = importlib.util.module_from_spec(spec); sys.modules["rcn"] = night
spec.loader.exec_module(night)

WD = dict(night.WATCHDOG_DEFAULTS)

def load_rows(nd):
    out = []
    for line in nd.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out

def stats(rows):
    ok = [r for r in rows if r.get("ok")]
    cached = [r for r in ok if r.get("cached")]
    solved = [r for r in ok if not r.get("cached")]
    uniq = {r.get("design_hash") for r in rows}
    uniq_ok = {r.get("design_hash") for r in ok}
    finest = min((float(r["objective"]) for r in ok if isinstance(r.get("objective"), (int, float))), default=None)
    return {"attempts": len(rows), "unique": len(uniq), "ok": len(ok), "ok_unique": len(uniq_ok),
            "cached": len(cached), "solved_here": len(solved), "best": finest}

def replay(run_dir, base=0, wd=None, bounds=None, checkpoints=None, label=""):
    rows = load_rows(Path(run_dir) / "search.ndjson")
    wd = dict(wd or WD)
    bounds = bounds if bounds is not None else night._run_bounds(Path(run_dir))
    covered = rows[:base]
    out = {"run": Path(run_dir).name, "label": label, "total_rows": len(rows), "base": base,
           "wd": wd, "bounds": list(bounds.keys()), "first_trigger": None, "checkpoints": []}
    trigger_at = None
    for i in range(base + 1, len(rows) + 1):
        verdict = night.watchdog_verdict(rows[base:i], wd, bounds)
        if verdict:
            trigger_at = i
            out["first_trigger"] = {"row_index": i - 1, "verdict": verdict,
                                    "ts": rows[i - 1].get("created_utc"),
                                    "stats": stats(rows[:i])}
            break
    marks = set(checkpoints or [])
    if trigger_at:
        marks.add(trigger_at)
    for c in sorted(m for m in marks if base < m <= len(rows)):
        out["checkpoints"].append({"row_count": c, "ts": rows[c - 1].get("created_utc"),
                                   "verdict": night.watchdog_verdict(rows[base:c], wd, bounds),
                                   "stats": stats(rows[:c])})
    out["final_stats"] = stats(rows)
    return out

if __name__ == "__main__":
    targets = [
        # label, run dir, base, wd overrides
        ("normal_complete_biradial_smooth", "20261116T081139Z-screen-63158a", 0, {}),
        ("watchdog_refusal_crowex", "20261116T095336Z-screen-7fc9b7", 0, {}),
        ("watchdog_boundpin_tritonia", "20261116T044917Z-screen-12eb61", 0, {}),
        ("watchdog_stall_biradial", "20261116T071520Z-screen-1c8608", 0, {}),
        ("watchdog_nogain_rosse", "20261116T145634Z-screen-e4c778", 0, {}),
        ("heavily_refusing_salmon_saddle", "20261116T054705Z-screen-570bc6", 0, {}),
        ("qd_cma_me_osse", "20261112T110126Z-screen-c414b1", 0, {}),
    ]
    results = []
    for label, rd, base, over in targets:
        wd = dict(WD); wd.update(over)
        results.append(replay(REPO / "runs" / rd, base=base, wd=wd, label=label,
                              checkpoints=[10, 20, 30, 40, 50, 60, 80, 100, 120]))
    # resume case: first leg base=0, second leg base=30 with stall_valid 60
    wd2 = dict(WD); wd2.update({"stall_valid": 60})
    results.append(replay(REPO / "runs" / "20261116T130335Z-screen-ab4fb9", base=0,
                          label="resume_leg1_nogain", checkpoints=[10, 20, 30]))
    results.append(replay(REPO / "runs" / "20261116T130335Z-screen-ab4fb9", base=30, wd=wd2,
                          label="resume_leg2_new_rows", checkpoints=[10, 20, 30, 40, 47]))
    out = Path(__file__).parent / "watchdog_replay.json"
    out.write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    for r in results:
        print("="*70)
        print(r["label"], r["run"], "rows", r["total_rows"], "base", r["base"])
        print("  final", r["final_stats"])
        ft = r["first_trigger"]
        if ft:
            print("  FIRST TRIGGER row_index", ft["row_index"], "ts", ft["ts"])
            print("   verdict:", ft["verdict"])
            print("   stats@trigger:", ft["stats"])
        else:
            print("  NO TRIGGER")
