"""C.2 - compare the calibration night's verify runs per variant (offline).

    .venv\\Scripts\\python.exe tools\\calibration\\compare_calibration.py ^
        --night runs\\nights\\calibration_2026-11-12 --out scratch\\calibration_2026-11-12

Reads the night directory the runner produced (``summary.jsonl``; one row per
``hornlab-search verify --designs ...`` job) and pairs the variants per design:

* per acceptance threshold (Re z +-0.03, beamwidth +-2 deg, DI +-0.2 dB -- from the night's
  ``calibration:`` metadata block, written by ``plan_calibration.py``): max |delta| over the
  target band between the two variants of each aspect pair (band-split vs single mesh,
  2 m vs 10 m, epw 6 vs 9) -- PASS/FAIL per design per dimension;
* rank agreement: Spearman rho of J across variants, and of screen J vs verify J per variant
  ("does the screen ranking survive" -- the C.4 question);
* finalists re-ranked by verify J only (the C.4 amendment: rank by verify J, not screen J).

Writes ``compare.json`` (machine readable) + ``COMPARE.md`` (tables) into ``--out``. No solve is
ever launched; ``runs/`` and the night dir are only read.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Rank agreement at or above this rho counts as "the screen ranking survives". No measured
#: criterion was decided for this; 0.8 is the conventional strong-agreement floor, stated here so
#: the verdict is reproducible. The rho values themselves are always reported.
SCREEN_SURVIVES_RHO = 0.8

_JOB_PREFIX = "c_"

# Constants from the planner (variant table, thresholds, aspect pairs). Bound at import time so
# the two tools can never drift apart; plan_calibration is pure YAML/stdlib and imports safely.
_PLAN = None  # lazily imported plan_calibration module


def _plan_mod():
    global _PLAN
    if _PLAN is None:
        spec = importlib.util.spec_from_file_location(
            "plan_calibration", Path(__file__).with_name("plan_calibration.py"))
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("plan_calibration", module)
        spec.loader.exec_module(module)
        _PLAN = module
    return _PLAN


THRESHOLDS = _plan_mod().THRESHOLDS
ASPECT_PAIRS = _plan_mod().ASPECT_PAIRS
DEFAULT_TOP = _plan_mod().DEFAULT_TOP
VARIANT_ORDER = _plan_mod().VARIANT_ORDER


# ------------------------------------------------------------------ io helpers


def read_ndjson(path: Path) -> list[dict]:
    """Parseable rows only; torn final lines are skipped (same rule as search/evaluate.py)."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return rows


def _read_json(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _fmt(value: float | None, spec: str = ".4g") -> str:
    return "n/a" if value is None or (isinstance(value, float) and math.isnan(value)) \
        else format(value, spec)


# ------------------------------------------------------------------ statistics


def _ranks(values: list[float]) -> list[float]:
    """Average ranks (1-based), ties share the mean rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mean = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = mean
        i = j + 1
    return ranks


def spearman(a: list[float], b: list[float]) -> float | None:
    """Spearman rho (average ranks + Pearson on the ranks). None when undefined (n < 2, or a
    constant vector, or any NaN)."""
    n = len(a)
    if n != len(b) or n < 2:
        return None
    if any(math.isnan(x) or math.isnan(y) for x, y in zip(a, b)):
        return None
    ra, rb = _ranks(list(a)), _ranks(list(b))
    if len(set(ra)) < 2 or len(set(rb)) < 2:
        return None
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = math.sqrt(sum((x - ma) ** 2 for x in ra))
    vb = math.sqrt(sum((y - mb) ** 2 for y in rb))
    if va == 0 or vb == 0:
        return None
    return cov / (va * vb)


# ------------------------------------------------------------------ metric deltas


def _aligned_band(a_freqs, b_freqs, band_lo: float | None, band_hi: float | None):
    """Indices into (a, b) of frequency pairs that match within 0.05 Hz and lie in the band."""
    out = []
    b_list = [float(f) for f in (b_freqs or []) if isinstance(f, (int, float))]
    a_idx = -1
    for fa_raw in (a_freqs or []):
        a_idx += 1
        if not isinstance(fa_raw, (int, float)):
            continue
        fa = float(fa_raw)
        best_j, best_d = None, 0.06
        for j, fb in enumerate(b_list):
            d = abs(fb - fa)
            if d < best_d:
                best_j, best_d = j, d
        if best_j is None:
            continue
        if band_lo is not None and fa < band_lo - 1e-6:
            continue
        if band_hi is not None and fa > band_hi + 1e-6:
            continue
        out.append((a_idx, best_j))
    return out


def _max_delta(a, b, pairs) -> float | None:
    """max |a-b| over aligned pairs where both values are finite; None when no comparable pair."""
    worst = None
    for i, j in pairs:
        try:
            va, vb = float(a[i]), float(b[j])
        except (TypeError, ValueError, IndexError, KeyError):
            continue
        if math.isnan(va) or math.isnan(vb):
            continue
        d = abs(va - vb)
        worst = d if worst is None else max(worst, d)
    return worst


def _mean_delta(a, b, pairs) -> float | None:
    acc, n = 0.0, 0
    for i, j in pairs:
        try:
            va, vb = float(a[i]), float(b[j])
        except (TypeError, ValueError, IndexError, KeyError):
            continue
        if math.isnan(va) or math.isnan(vb):
            continue
        acc += abs(va - vb)
        n += 1
    return acc / n if n else None


def _metrics_of(row: dict) -> dict:
    m = row.get("metrics")
    return m if isinstance(m, dict) else {}


# ------------------------------------------------------------------ collection


def _split_job_id(job_id: str) -> tuple[str, str] | None:
    """``c_<variant>__<runname>`` -> (variant, runname); None when not a calibration job."""
    if not job_id.startswith(_JOB_PREFIX):
        return None
    body = job_id[len(_JOB_PREFIX):]
    sep = body.find("__")
    if sep <= 0:
        return None
    return body[:sep], body[sep + 2:]


def _find_plan(night_dir: Path, explicit: Path | str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.is_file() else None
    for candidate in (night_dir.parent / f"{night_dir.name}.yaml",
                      night_dir / "night.yaml", night_dir / "plan.yaml"):
        if candidate.is_file():
            return candidate
    return None


def collect(night_dir: Path, plan_path: Path | None = None) -> dict:
    """The comparison input: per (run, variant) the verify rows keyed by design hash."""
    night_dir = Path(night_dir)
    if not night_dir.is_dir():
        raise ValueError(f"--night {night_dir} is not a directory")
    plan_file = _find_plan(night_dir, plan_path)
    meta: dict = {}
    night_name = night_dir.name
    if plan_file is not None:
        raw = yaml.safe_load(plan_file.read_text(encoding="utf-8")) or {}
        meta = raw.get("calibration") or {}
        if isinstance(raw.get("night"), str):
            night_name = raw["night"]
    thresholds = dict(meta.get("thresholds") or THRESHOLDS)
    aspect_pairs = {k: tuple(v) for k, v in (meta.get("aspect_pairs") or ASPECT_PAIRS).items()}
    variants_dir = meta.get("variants_dir")
    runs_meta: dict = meta.get("runs") or {}
    designs_meta: list = meta.get("designs") or []

    runs: dict[str, dict] = {}          # run -> {variant -> {hash -> {row, screen_j}}}
    jobs_report: list[dict] = []
    for line_no, row in enumerate(read_ndjson(night_dir / "summary.jsonl"), 1):
        parsed = _split_job_id(str(row.get("id") or ""))
        if parsed is None:
            continue
        variant, run_name = parsed
        run_key = str(row.get("id"))
        run_path = None
        for entry in designs_meta:
            if entry.get("job_run") == run_name:
                run_path = entry.get("run")
                break
        vdir_name = f"{run_name}__{variant}"
        verify_dir = None
        raw_dir = row.get("run_dir")
        if raw_dir:
            verify_dir = Path(raw_dir)
        elif variants_dir:
            # Fallback: the planner's documented layout variants_dir/<run>__<variant>/verify.
            # A relative variants_dir is repo-root relative when the plan was written; try the
            # layout roots that make sense (this checkout, the night dir's parents) and keep the
            # first that actually holds the variant dir.
            for base in (REPO_ROOT, night_dir.parent, night_dir.parent.parent):
                cand = Path(variants_dir)
                if not cand.is_absolute():
                    cand = base / cand
                if (cand / vdir_name).is_dir():
                    verify_dir = cand / vdir_name / "verify"
                    break
            if verify_dir is None:
                verify_dir = REPO_ROOT / variants_dir / vdir_name / "verify"
        vhash: dict[str, dict] = {}
        if verify_dir is not None:
            for vrow in read_ndjson(verify_dir / "search.ndjson"):
                if not vrow.get("ok") or not vrow.get("design_hash"):
                    continue
                h = str(vrow["design_hash"])
                obj = vrow.get("objective")
                if not isinstance(obj, (int, float)):
                    continue
                j = float(obj)
                if h not in vhash or j < vhash[h]["J"]:
                    vhash[h] = {"J": j, "metrics": _metrics_of(vrow)}
        screen = {e.get("hash"): e.get("screen_j") for e in designs_meta
                  if entry_run(e) == run_name} if designs_meta else {}
        if not screen and run_path:
            # No metadata (plan file gone): fall back to the source run's own rows.
            screen = {str(r["design_hash"]): float(r["objective"]) for r in
                      read_ndjson(Path(run_path) / "search.ndjson")
                      if r.get("ok") and isinstance(r.get("design_hash"), str)
                      and isinstance(r.get("objective"), (int, float))}
        bucket = runs.setdefault(run_name, {})
        if run_path:
            bucket.setdefault("_run_path", run_path)
        bucket[variant] = {"hashes": vhash, "screen": screen}
        jobs_report.append({"line": line_no, "id": row.get("id"), "variant": variant,
                            "run": run_name, "verify_dir": str(verify_dir) if verify_dir else None,
                            "job_exit": row.get("exit_code"),
                            "designs_found": sorted(vhash)})
    return {"night": night_name, "night_dir": str(night_dir), "plan_file":
            str(plan_file) if plan_file else None, "thresholds": thresholds,
            "aspect_pairs": aspect_pairs, "runs_meta": runs_meta,
            "runs": runs, "jobs": jobs_report}


def entry_run(entry: dict) -> str:
    return str(entry.get("job_run") or "")


# ------------------------------------------------------------------ comparison


def compare(collected: dict) -> dict:
    """Per (run, aspect pair) per-design threshold verdicts + Spearman rank agreement."""
    thresholds = collected["thresholds"]
    aspect_pairs = collected["aspect_pairs"]
    runs_meta = collected["runs_meta"]
    report: dict = {"night": collected["night"], "plan_file": collected["plan_file"],
                    "thresholds": thresholds,
                    "screen_survives_rho": SCREEN_SURVIVES_RHO, "runs": {}, "jobs": collected["jobs"]}
    for run_name, bucket in sorted(collected["runs"].items()):
        run_path = bucket.get("_run_path")
        band_meta = runs_meta.get(str(run_path)) or runs_meta.get(run_name) or {}
        band_lo, band_hi = band_meta.get("band_lo_hz"), band_meta.get("band_hi_hz")
        variants = {k: v for k, v in bucket.items() if not k.startswith("_")}
        run_report: dict = {"run": str(run_path or run_name), "band_lo_hz": band_lo,
                            "band_hi_hz": band_hi, "variants": sorted(variants), "pairs": {},
                            "spearman": {}, "finalists_by_verify_j": []}
        # ---- threshold verdicts per aspect pair
        for aspect, (va, vb) in aspect_pairs.items():
            if va not in variants or vb not in variants:
                run_report["pairs"][aspect] = {"status": "missing_variants",
                                               "variants": [va, vb]}
                continue
            ha, hb = variants[va]["hashes"], variants[vb]["hashes"]
            shared = sorted(set(ha) & set(hb))
            per_design = []
            for h in shared:
                ma, mb = ha[h]["metrics"], hb[h]["metrics"]
                pairs = _aligned_band(ma.get("freqs_hz"), mb.get("freqs_hz"), band_lo, band_hi)
                if len(pairs) < 3:
                    per_design.append({"design": h, "status": "freq_grids_differ",
                                       "n_aligned": len(pairs)})
                    continue
                z = _max_delta(ma.get("z_throat_real"), mb.get("z_throat_real"), pairs)
                bw_h = _max_delta(ma.get("bw_h_deg"), mb.get("bw_h_deg"), pairs)
                bw_v = _max_delta(ma.get("bw_v_deg"), mb.get("bw_v_deg"), pairs)
                bw = None if bw_h is None and bw_v is None else max(
                    d for d in (bw_h, bw_v) if d is not None)
                di = _max_delta(ma.get("di_db"), mb.get("di_db"), pairs)
                dims = {"re_z": z, "beamwidth_deg": bw, "di_db": di}
                verdict = {}
                for name, limit in thresholds.items():
                    value = dims.get(name)
                    verdict[name] = {"max_delta": value, "limit": limit,
                                     "pass": value is not None and value <= limit}
                per_design.append({
                    "design": h, "status": "ok",
                    "J": {va: ha[h]["J"], vb: hb[h]["J"]},
                    "mean_delta_re_z": _mean_delta(ma.get("z_throat_real"),
                                                   mb.get("z_throat_real"), pairs),
                    **dims, "verdict": verdict,
                    "pass": all(v["pass"] for v in verdict.values())})
            missing = sorted((set(ha) | set(hb))
                             - set(shared))
            run_report["pairs"][aspect] = {
                "variants": [va, vb], "n_designs": len(shared),
                "designs": per_design,
                "missing_designs": missing,
                "pass_all": bool(per_design) and all(d.get("pass") for d in per_design
                                                     if d.get("status") == "ok")
                and not any(d.get("status") != "ok" for d in per_design)}
        # ---- Spearman rank agreement
        for va, vb in aspect_pairs.values():
            if va not in variants or vb not in variants:
                continue
            shared = sorted(set(variants[va]["hashes"]) & set(variants[vb]["hashes"]))
            ja = [variants[va]["hashes"][h]["J"] for h in shared]
            jb = [variants[vb]["hashes"][h]["J"] for h in shared]
            run_report["spearman"][f"{va}__vs__{vb}"] = {
                "n": len(shared), "rho": spearman(ja, jb)}
        for va, vdata in variants.items():
            shared = sorted(set(vdata["hashes"]) & set(vdata["screen"]))
            if not all(isinstance(vdata["screen"][h], (int, float)) for h in shared):
                shared = [h for h in shared if isinstance(vdata["screen"][h], (int, float))]
            js = [float(vdata["screen"][h]) for h in shared]
            jv = [vdata["hashes"][h]["J"] for h in shared]
            run_report["spearman"][f"screen__vs__{va}"] = {
                "n": len(shared), "rho": spearman(js, jv)}
        # ---- C.4: rank finalists by verify J only (control first when present)
        ranking_source = "single_mesh" if "single_mesh" in variants else (
            sorted(variants)[0] if variants else None)
        if ranking_source is not None:
            ranked = sorted(((v["J"], h) for h, v in variants[ranking_source]["hashes"].items()))
            run_report["finalists_by_verify_j"] = [
                {"rank": i + 1, "design": h, "verify_j": j,
                 "screen_j": variants[ranking_source]["screen"].get(h)}
                for i, (j, h) in enumerate(ranked)]
            run_report["ranked_by_variant"] = ranking_source
        # ---- overall verdicts
        survivors = [v for k, v in run_report["spearman"].items() if k.startswith("screen__vs__")
                     and v["rho"] is not None]
        # 1e-9 guards the exact-boundary case only (rho == SCREEN_SURVIVES_RHO, e.g. a single
        # adjacent-rank flip where Pearson-on-ranks yields 0.7999999999999998 in float); it cannot
        # mask a genuinely worse ranking (0.79..0.7999 fails by ~1e-3, far above 1e-9).
        run_report["screen_ranking"] = {
            "min_rho": min((v["rho"] for v in survivors), default=None),
            "survives": bool(survivors)
            and all(v["rho"] >= SCREEN_SURVIVES_RHO - 1e-9 for v in survivors),
            "criterion": f"every screen-vs-verify rho >= {SCREEN_SURVIVES_RHO}",
        }
        report["runs"][run_name] = run_report
    report["all_pairs_pass"] = all(
        r["pairs"].get(a, {}).get("pass_all", False)
        for r in report["runs"].values() for a in aspect_pairs) if report["runs"] else False
    return report


# ------------------------------------------------------------------ markdown


def write_md(path: Path, report: dict, thresholds: dict) -> None:  # noqa: C901 - one flat writer
    lines = [f"# Calibration comparison: night `{report['night']}`", "",
             f"Plan file: `{report['plan_file']}`. Verdict criterion for the screen ranking: "
             f"{report['screen_survives_rho']} (stated constant, not a measured threshold).", ""]
    lines += ["## Threshold verdicts", ""]
    for run_name, run in sorted(report["runs"].items()):
        band = (f"{_fmt(run['band_lo_hz'], '.0f')}-{_fmt(run['band_hi_hz'], '.0f')} Hz"
                if run.get("band_lo_hz") and run.get("band_hi_hz") else "whole grid")
        lines.append(f"### {run_name} ({band})")
        lines.append("")
        for aspect, pair in run["pairs"].items():
            va, vb = pair.get("variants", ("?", "?"))
            lines.append(f"#### {aspect}: `{va}` vs `{vb}`")
            lines.append("")
            if pair.get("status") == "missing_variants":
                lines.append("Missing verify dirs for one variant; pair not comparable.")
                lines.append("")
                continue
            lines.append("| design | max |d Re z| | max |d BW| deg | max |d DI| dB | J (both) | verdict |")
            lines.append("|---|---:|---:|---:|---|---|")
            for d in pair.get("designs", []):
                if d.get("status") != "ok":
                    lines.append(f"| `{d['design']}` | n/a | n/a | n/a | | {d['status']} |")
                    continue
                v = d["verdict"]
                js = ", ".join(f"{k}={_fmt(x)}" for k, x in sorted(d.get("J", {}).items()))
                lines.append(f"| `{d['design']}` | {_fmt(d['re_z'])} | {_fmt(d['beamwidth_deg'])} | "
                             f"{_fmt(d['di_db'])} | {js} | "
                             f"{'PASS' if d['pass'] else 'FAIL ' + ','.join(k for k, x in v.items() if not x['pass'])} |")
            lines.append("")
            if pair.get("missing_designs"):
                lines.append(f"Designs missing from one variant: "
                             f"{', '.join('`' + h + '`' for h in pair['missing_designs'])}")
                lines.append("")
        lines.append("### Rank agreement (Spearman rho of J)")
        lines.append("")
        lines.append("| comparison | n | rho |")
        lines.append("|---|---:|---:|")
        for key, s in sorted(run["spearman"].items()):
            lines.append(f"| {key.replace('__', ' ')} | {s['n']} | {_fmt(s['rho'])} |")
        sr = run["screen_ranking"]
        lines.append("")
        lines.append(f"Screen ranking survives: **{'YES' if sr['survives'] else 'NO'}** "
                     f"(min rho {_fmt(sr['min_rho'])}; criterion: {sr['criterion']}).")
        lines.append("")
        lines.append(f"### Finalists ranked by verify J (`{run.get('ranked_by_variant')}`)")
        lines.append("")
        lines.append("| rank | design | verify J | screen J |")
        lines.append("|---:|---|---:|---:|")
        for entry in run["finalists_by_verify_j"][:DEFAULT_TOP]:
            lines.append(f"| {entry['rank']} | `{entry['design']}` | {_fmt(entry['verify_j'])} | "
                         f"{_fmt(entry['screen_j'])} |")
        lines.append("")
    lines += ["## Overall", "",
              f"All threshold pairs pass: **{'YES' if report['all_pairs_pass'] else 'NO'}**.", ""]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


# ------------------------------------------------------------------ CLI


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare the calibration night's verify runs per variant (offline).")
    parser.add_argument("--night", required=True, metavar="DIR",
                        help="the night directory the runner produced (contains summary.jsonl)")
    parser.add_argument("--plan", default=None, metavar="YAML",
                        help="the night YAML (default: <night dir sibling>.yaml or night dir)")
    parser.add_argument("--out", required=True, metavar="DIR", help="output directory")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    out = Path(args.out)
    try:
        collected = collect(Path(args.night), args.plan)
        if not collected["jobs"]:
            print(f"compare_calibration: no calibration jobs found in {args.night}/summary.jsonl",
                  file=sys.stderr)
            return 2
        _plan_mod()  # touch: the variant/threshold table must import cleanly
        report = compare(collected)
        out.mkdir(parents=True, exist_ok=True)
        (out / "compare.json").write_text(
            json.dumps(report, indent=1, allow_nan=False, default=str) + "\n", encoding="utf-8")
        write_md(out / "COMPARE.md", report, report["thresholds"])
    except ValueError as exc:
        print(f"compare_calibration: {exc}", file=sys.stderr)
        return 2
    failed = []
    for run_name, run in sorted(report["runs"].items()):
        for aspect, pair in run["pairs"].items():
            if pair.get("pass_all"):
                continue
            if pair.get("status") == "missing_variants" or "pass_all" not in pair:
                failed.append(f"{run_name}/{aspect}: not comparable")
            else:
                failed.append(f"{run_name}/{aspect}: FAIL")
    print(f"compare_calibration: {len(collected['jobs'])} job(s), "
          f"{len(report['runs'])} run(s) compared -> {out / 'COMPARE.md'}")
    for line in failed:
        print(f"  {line}")
    if report["all_pairs_pass"]:
        print("all threshold pairs PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
