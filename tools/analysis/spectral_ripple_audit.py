"""Fixed-angle spectral ripple audit over stored designs (REPORT-ONLY).

This tool reads stored ``response.npz`` / ``metrics.json`` files and reports the residual spread of
a fixed-angle off-axis response about a polynomial in ``log2(f)``. It is a REPORT-ONLY diagnostic:
it is never a score term, it reads stored responses, and it makes ZERO solver calls. It never
ranks ``J`` across objective versions.

See ``hornlab_search.metrics.spectral`` for the metric definition and
``docs/research/ripple_hf_2026-11-19/HANDOFF_2026-11-19.md`` item 1 for the handoff.

Inputs may be design directories (``.../designs/<hash>`` holding ``response.npz``) or run
directories (the parent holding ``designs/<hash>/``; ``best.json`` selects the design). Outputs are
``audit.json`` (aggregate + provenance), one JSON per design, and ``disagreement.md`` (unless
``--json-only``). ``--out`` is refused when it exists and is not empty.

``--compare PATH_A PATH_B`` joins two stored ``audit.json`` files by ``design_hash`` and writes
``<out>/compare.md`` (deltas B-A, band means, Spearman); it cannot be combined with positional
design/run directories.

    python tools/analysis/spectral_ripple_audit.py <design-or-run-dir> [...] --out runs/analysis/<name>
    python tools/analysis/spectral_ripple_audit.py --compare A/audit.json B/audit.json --out runs/analysis/<name>
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from hornlab_search.metrics import spectral  # noqa: E402

#: Wider angle set always included in the sensitivity scan, per the handoff.
WIDE_ANGLES_V_DEG = (20.0, 30.0, 40.0, 45.0)


# ----------------------------------------------------------------------------- helpers

def _read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _run_dir_for(design_dir: Path):
    """Return the run directory for a ``.../designs/<hash>`` path, else ``None``."""
    if design_dir.parent.name == "designs":
        return design_dir.parent.parent
    return None


def _resolve_design(path) -> tuple[Path, Path | None]:
    """Resolve a design directory (and its run directory) from a design or run path."""
    p = Path(path)
    if (p / "response.npz").is_file():
        return p, _run_dir_for(p)
    designs = p / "designs"
    if designs.is_dir():
        best = _read_json(p / "best.json", {}) or {}
        h = best.get("design_hash")
        if h and (designs / h / "response.npz").is_file():
            return designs / h, p
        named = [q for q in designs.iterdir() if (q / "response.npz").is_file()]
        if len(named) == 1:
            return named[0], p
        raise SystemExit(f"cannot resolve a design in run dir {p}")
    raise SystemExit(f"{p} is neither a design dir (response.npz) nor a run dir (designs/)")


def _provenance(argv, band_hz, detrend_orders, angles_v, angles_wide):
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True,
            text=True, timeout=10, check=False).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        head = "unknown"
    return {
        "git_head": head,
        "utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "interpreter": sys.executable,
        "numpy_version": np.__version__,
        "argv": [str(x) for x in argv],
        "band_hz": [float(band_hz[0]), float(band_hz[1])],
        "detrend_orders": [int(o) for o in detrend_orders],
        "angles_v_deg": [float(x) for x in angles_v],
        "angles_wide_v_deg": [float(x) for x in angles_wide],
        "status": "REPORT-ONLY diagnostic; never a score term; zero solver calls",
    }


def _metrics_band_mean(metrics, band_hz):
    """Mean of the stored angular ``ripple_v_db`` over the reporting band (different definition)."""
    f = np.asarray(metrics.get("freqs_hz", []), dtype=float)
    r = np.asarray(metrics.get("ripple_v_db", []), dtype=float)
    if f.size == 0 or r.shape != f.shape:
        return None
    m = (f >= float(band_hz[0])) & (f <= float(band_hz[1])) & np.isfinite(r)
    return float(np.mean(r[m])) if int(m.sum()) else None


def _design_row(design_dir: Path, run_dir: Path | None, band_hz, detrend_orders,
                angles_v, angles_wide):
    """Compute all audit values for one design."""
    z = np.load(design_dir / "response.npz", allow_pickle=True)
    freqs = np.asarray(z["freqs_hz"], dtype=float)
    angles = np.asarray(z["v_angles_deg"], dtype=float)
    spl = np.asarray(z["spl_v_db"], dtype=float)
    metrics = _read_json(design_dir / "metrics.json", {}) or {}
    design = _read_json(design_dir / "design.json", {}) or {}

    best = (_read_json(run_dir / "best.json", {}) or {}) if run_dir else {}
    best = best if isinstance(best, dict) else {}
    status = _read_json(design_dir / "status.json", {}) or {}
    summary = (_read_json(run_dir / "summary.json", {}) or {}) if run_dir else {}

    design_hash = (design.get("design_hash") or best.get("design_hash")
                   or design_dir.name)
    family = design.get("family") or best.get("family") or summary.get("family")
    objective_version = summary.get("objective_version")
    if objective_version is None:
        objective_version = best.get("objective_version")
    if objective_version is None:
        # A `verify --verify-dir` directory has run.json (mode "verify") and no summary.json.
        run_meta = _read_json(run_dir / "run.json", {}) if run_dir else {}
        raw = (run_meta or {}).get("config") if isinstance(run_meta, dict) else None
        obj = (raw or {}).get("brief", {}).get("objective") if isinstance(raw, dict) else None
        if isinstance(obj, dict):
            objective_version = obj.get("version")

    best_is_this_design = best.get("design_hash") == design_hash
    terms = best.get("terms")
    terms = terms if isinstance(terms, dict) else {}
    objective_rip = (terms.get("rip")
                     if best_is_this_design and terms.get("rip") is not None else None)
    if best_is_this_design and best.get("objective") is not None:
        j_value = float(best["objective"])
    elif status.get("objective") is not None:
        j_value = float(status["objective"])
    elif best.get("objective") is not None:
        j_value = float(best["objective"])
    else:
        j_value = None

    primary = [float(x) for x in angles_v]
    wide = [float(x) for x in angles_wide]
    scan_angles = sorted(set(primary) | set(wide))

    fixed = {}
    for a in sorted(set(primary) | {-x for x in primary}):
        fixed[a] = spectral.fixed_angle_residual_curve(
            freqs, spl, angles, a, band_hz=band_hz, detrend_order=2)["rms_db"]

    fixed_band_mean = {}
    for a in sorted(set(primary) | {-x for x in primary}):
        fixed_band_mean[a] = spectral.fixed_angle_residual_db(
            freqs, spl, angles, a, band_hz=band_hz, reference="band_mean")

    detrend_spread = {}
    for a in primary:
        vals = [spectral.fixed_angle_residual_db(
                    freqs, spl, angles, a, band_hz=band_hz, detrend_order=o)
                for o in detrend_orders]
        finite = np.asarray([v for v in vals if np.isfinite(v)], dtype=float)
        detrend_spread[f"V{a:+g}"] = (float(np.max(finite) - np.min(finite))
                                      if finite.size else float("nan"))

    metrics_aug = dict(metrics)
    metrics_aug["n_balloon"] = int(np.asarray(z["balloon_dirs"]).shape[0])
    identity = spectral.cut_identity_check(freqs, spl, angles, metrics_aug, band_hz=band_hz)

    return {
        "design_dir": design_dir.as_posix(),
        "run_dir": run_dir.as_posix() if run_dir else None,
        "design_hash": design_hash,
        "family": family,
        "objective_version": objective_version,
        "J": j_value,
        "objective_rip": objective_rip,
        "ripple_v_metrics_mean_db": _metrics_band_mean(metrics, band_hz),
        "angles_v_deg": primary,
        "fixed_angle_rms_db": fixed,
        "fixed_angle_band_mean_db": fixed_band_mean,
        "detrend_spread_db": detrend_spread,
        "sensitivity_scan": spectral.sensitivity_scan(
            freqs, spl, angles, scan_angles, band_hz=band_hz,
            detrend_orders=detrend_orders),
        "symmetric_pairs": spectral.symmetric_pair_report(
            freqs, spl, angles, band_hz=band_hz, detrend_order=2),
        "identity": identity,
    }


# ----------------------------------------------------------------------------- compare

def _load_audit(path):
    """Load an ``audit.json`` (or a directory holding one). Returns ``(data, error)``."""
    p = Path(path)
    if p.is_dir():
        p = p / "audit.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, f"cannot read {p}: {exc}"
    except ValueError as exc:
        return None, f"cannot parse {p}: {exc}"
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        return None, f"{p} has no 'rows' list"
    return data, None


def _fixed_values(row, angle="35.0"):
    """Return ``(trend_rms, band_mean)`` for one fixed angle from an audit row."""
    trend = row.get("fixed_angle_rms_db") or {}
    band = row.get("fixed_angle_band_mean_db") or {}
    return trend.get(str(angle)), band.get(str(angle))


def _fmt_value(value, digits=3):
    if value is None:
        return "-"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    return "nan" if not np.isfinite(v) else f"{v:.{digits}f}"


def _spearman(xs, ys):
    """Spearman over the finite pairs; None with a reason below n=3."""
    pairs = [(float(x), float(y)) for x, y in zip(xs, ys)
             if x is not None and y is not None
             and np.isfinite(float(x)) and np.isfinite(float(y))]
    if len(pairs) < 3:
        return {"rho": None, "p": None, "n": len(pairs),
                "reason": f"need n>=3 finite joined pairs, have {len(pairs)}"}
    from scipy.stats import spearmanr

    result = spearmanr([x for x, _ in pairs], [y for _, y in pairs])
    rho, p = float(getattr(result, "statistic")), float(getattr(result, "pvalue"))
    if not np.isfinite(rho):
        return {"rho": None, "p": None, "n": len(pairs),
                "reason": "Spearman undefined (constant values)"}
    return {"rho": rho, "p": p, "n": len(pairs), "reason": None}


def _trend_summary(records, key):
    """Max/mean absolute B-A delta plus Spearman for one trend key."""
    a_vals = [r["A"][key][0] for r in records]
    b_vals = [r["B"][key][0] for r in records]
    deltas = [abs(float(r["delta"][key])) for r in records
              if r["delta"][key] is not None and np.isfinite(float(r["delta"][key]))]
    return {
        "n_joined": len(records),
        "n_delta": len(deltas),
        "max_abs": max(deltas) if deltas else None,
        "mean_abs": float(np.mean(deltas)) if deltas else None,
        "spearman": _spearman(a_vals, b_vals),
    }


def _compare_markdown(path_a, path_b, records, only_a, only_b, summary):
    n_joined = len(records)
    lines = [
        "# Spectral ripple audit comparison (report-only)",
        "",
        f"- A: `{Path(path_a).as_posix()}`",
        f"- B: `{Path(path_b).as_posix()}`",
        "- Rows joined by `design_hash`; delta is **B minus A**.",
        "",
        "**Absolute values are grid-dependent.** The same horn has been measured at "
        "**1.441 dB** (18-frequency screen), **1.908 dB** (verify) and **1.313 dB** "
        "(91-frequency dense) for V+35, so only rankings and deltas are quotable. "
        "A rank correlation is not accuracy.",
        "",
        "`(trend)` = residual about the exploratory log2(f) quadratic (order 2); "
        "`(band_mean)` = deviation from the in-band mean, the IEC 60268-5 section 20.6 / "
        "Klippel AN 40 smoothness definition. Neither is a hearing-weighted score.",
        "",
        "## Summary",
        "",
        "| trend | n joined | max abs delta (dB) | mean abs delta (dB) | Spearman rho | note |",
        "|---|---|---|---|---|---|",
    ]
    for label, key in (("V+35", "35.0"), ("V+25", "25.0")):
        s = summary[key]
        sp = s["spearman"]
        rho = _fmt_value(sp["rho"], 4) if sp["rho"] is not None else "null"
        note = sp["reason"] or f"p={_fmt_value(sp['p'], 4)}"
        lines.append(f"| {label} | {n_joined} | {_fmt_value(s['max_abs'])} | "
                     f"{_fmt_value(s['mean_abs'])} | {rho} | {note} |")
    lines += [
        "",
        "## Joined designs",
        "",
        "| design_hash | V+25 A | V+25 B | delta V+25 | V+25 A band_mean | "
        "V+25 B band_mean | V+35 A | V+35 B | delta V+35 | V+35 A band_mean | "
        "V+35 B band_mean |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        a25, b25 = r["A"]["25.0"], r["B"]["25.0"]
        a35, b35 = r["A"]["35.0"], r["B"]["35.0"]
        lines.append(
            f"| {r['design_hash']} | {_fmt_value(a25[0])} | {_fmt_value(b25[0])} | "
            f"{_fmt_value(r['delta']['25.0'])} | {_fmt_value(a25[1])} | "
            f"{_fmt_value(b25[1])} | {_fmt_value(a35[0])} | {_fmt_value(b35[0])} | "
            f"{_fmt_value(r['delta']['35.0'])} | {_fmt_value(a35[1])} | "
            f"{_fmt_value(b35[1])} |")
    lines += ["", "## Hashes present on only one side", ""]
    lines.append(f"A only ({len(only_a)}): " + (", ".join(f"`{h}`" for h in only_a) or "-"))
    lines.append("")
    lines.append(f"B only ({len(only_b)}): " + (", ".join(f"`{h}`" for h in only_b) or "-"))
    return "\n".join(lines) + "\n"


def _compare_main(path_a, path_b, out):
    data_a, err_a = _load_audit(path_a)
    if err_a:
        print(f"compare FAILED (A): {err_a}")
        return 2
    data_b, err_b = _load_audit(path_b)
    if err_b:
        print(f"compare FAILED (B): {err_b}")
        return 2
    assert data_a is not None and data_b is not None

    rows_a = {str(r.get("design_hash")): r for r in data_a["rows"] if r.get("design_hash")}
    rows_b = {str(r.get("design_hash")): r for r in data_b["rows"] if r.get("design_hash")}
    joined = sorted(set(rows_a) & set(rows_b))
    only_a = sorted(set(rows_a) - set(rows_b))
    only_b = sorted(set(rows_b) - set(rows_a))

    records = []
    for h in joined:
        a25, b25 = _fixed_values(rows_a[h], "25.0"), _fixed_values(rows_b[h], "25.0")
        a35, b35 = _fixed_values(rows_a[h], "35.0"), _fixed_values(rows_b[h], "35.0")

        def delta(x, y):
            if x is None or y is None:
                return None
            xf, yf = float(x), float(y)
            return yf - xf if np.isfinite(xf) and np.isfinite(yf) else None

        records.append({
            "design_hash": h,
            "A": {"25.0": a25, "35.0": a35},
            "B": {"25.0": b25, "35.0": b35},
            "delta": {"25.0": delta(a25[0], b25[0]), "35.0": delta(a35[0], b35[0])},
        })

    summary = {"35.0": _trend_summary(records, "35.0"),
               "25.0": _trend_summary(records, "25.0")}
    out.mkdir(parents=True, exist_ok=True)
    (out / "compare.md").write_text(
        _compare_markdown(path_a, path_b, records, only_a, only_b, summary),
        encoding="utf-8")
    s35, s25 = summary["35.0"], summary["25.0"]
    print(f"compare OK: {len(joined)} joined, {len(only_a)} A-only, {len(only_b)} B-only; "
          f"V+35 max|delta|={_fmt_value(s35['max_abs'])} mean|delta|={_fmt_value(s35['mean_abs'])} "
          f"rho={_fmt_value(s35['spearman']['rho'], 4) if s35['spearman']['rho'] is not None else 'null'}; "
          f"V+25 max|delta|={_fmt_value(s25['max_abs'])} mean|delta|={_fmt_value(s25['mean_abs'])} "
          f"rho={_fmt_value(s25['spearman']['rho'], 4) if s25['spearman']['rho'] is not None else 'null'}")
    print((out / "compare.md").as_posix())
    return 0


# ----------------------------------------------------------------------------- report

def _fmt(value, digits=3):
    if value is None:
        return "-"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    return "nan" if not np.isfinite(v) else f"{v:.{digits}f}"


def _md_table(rows, include_rank):
    header = ["design_hash", "family", "objective_version", "J", "rip(term)",
              "rip(metrics)", "V+25 (trend)", "V+25 (band_mean)", "V+35 (trend)",
              "V+35 (band_mean)", "V-25", "V-35", "detrend spread", "identity_ok"]
    if include_rank:
        header.insert(0, "rank")
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    ordered = sorted(rows, key=lambda r: (str(r.get("objective_version")),
                                          r["J"] if r["J"] is not None else float("inf")))
    for i, r in enumerate(ordered, start=1):
        fixed = r["fixed_angle_rms_db"]
        band_mean = r["fixed_angle_band_mean_db"]
        spread = r["detrend_spread_db"]
        finite_spread = [v for v in spread.values() if v is not None and np.isfinite(v)]
        cells = [
            str(r["design_hash"]),
            str(r["family"]),
            f"v{int(r['objective_version'])}" if r.get("objective_version") is not None else "?",
            _fmt(r["J"], 4),
            _fmt(r.get("objective_rip"), 3),
            _fmt(r["ripple_v_metrics_mean_db"], 3),
            _fmt(fixed.get(25.0), 3),
            _fmt(band_mean.get(25.0), 3),
            _fmt(fixed.get(35.0), 3),
            _fmt(band_mean.get(35.0), 3),
            _fmt(fixed.get(-25.0), 3),
            _fmt(fixed.get(-35.0), 3),
            _fmt(max(finite_spread) if finite_spread else None, 3),
            "yes" if r["identity"]["ok"] else "no",
        ]
        if include_rank:
            cells.insert(0, str(i))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _write_markdown(out: Path, rows, provenance):
    versions = {str(r.get("objective_version")) for r in rows}
    include_rank = len(versions) == 1
    header = [
        "# Fixed-angle spectral ripple audit (report-only)",
        "",
        "REPORT-ONLY diagnostic: **never a score term**. Reads stored responses; "
        "zero solver calls. `detrend spread` = max-min of the fixed-angle RMS over the "
        "requested detrend orders.",
        "",
        f"Band {provenance['band_hz'][0]:g}-{provenance['band_hz'][1]:g} Hz; "
        f"detrend orders {provenance['detrend_orders']}; "
        f"V angles {provenance['angles_v_deg']}; wide {provenance['angles_wide_v_deg']}.",
        "",
        "`J` is printed for context only. It is NEVER compared or ranked across objective "
        "versions. A rank column is present only when every row shares one objective version.",
        "",
        "`rip(term)` is the objective's own weighted `rip` contribution from `best.json` "
        "(`terms.rip`), i.e. what `J` actually charged; it is an ANGULAR residual at fixed "
        "frequency. `rip(metrics)` is the stored angular `ripple_v_db` mean in band. Neither is "
        "directly comparable to the fixed-angle residual.",
        "",
        "`(trend)` = residual about the exploratory log2(f) quadratic (order 2); "
        "`(band_mean)` = deviation from the in-band mean, the IEC 60268-5 section 20.6 / "
        "Klippel AN 40 smoothness definition. Neither is a hearing-weighted score.",
        "",
    ]
    body = _md_table(rows, include_rank)
    (out / "disagreement.md").write_text("\n".join(header) + "\n" + body + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------- CLI

def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("designs", nargs="*",
                    help="design dir (.../designs/<hash>) or run dir (holding designs/<hash>/)")
    ap.add_argument("--band-hz", nargs=2, type=float, default=[1065.0, 4832.5],
                    metavar=("LO", "HI"))
    ap.add_argument("--detrend-orders", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--angles-v", nargs="+", type=float, default=[25.0, 35.0])
    ap.add_argument("--out",
                    help="output directory (required; with --compare this holds compare.md)")
    ap.add_argument("--json-only", action="store_true",
                    help="write JSON only (no disagreement.md)")
    ap.add_argument("--compare", nargs=2, metavar=("PATH_A", "PATH_B"),
                    help="compare two audit.json files by design_hash (cannot be combined with "
                         "positional designs); writes <out>/compare.md")
    a = ap.parse_args(argv)

    if a.compare is not None:
        if a.designs:
            ap.error("--compare cannot be combined with positional design/run directories")
        if not a.out:
            ap.error("--compare requires --out for the report directory")
        out = Path(a.out)
        if out.exists() and any(out.iterdir()):
            raise SystemExit(f"refusing: {out} exists and is not empty")
        return _compare_main(a.compare[0], a.compare[1], out)

    if not a.designs:
        ap.error("the following arguments are required: designs")
    if not a.out:
        ap.error("the following arguments are required: --out")
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing: {out} exists and is not empty")
    out.mkdir(parents=True, exist_ok=True)

    band_hz = (float(a.band_hz[0]), float(a.band_hz[1]))
    primary = [float(x) for x in a.angles_v]
    wide = [float(x) for x in WIDE_ANGLES_V_DEG]
    rows = []
    used_names = set()
    for target in a.designs:
        design_dir, run_dir = _resolve_design(target)
        row = _design_row(design_dir, run_dir, band_hz, a.detrend_orders, primary, wide)
        rows.append(row)
        stem = str(row["design_hash"])
        name = f"design_{stem}.json"
        n = 2
        while name in used_names:
            name = f"design_{stem}_{n}.json"
            n += 1
        used_names.add(name)
        (out / name).write_text(json.dumps(row, indent=1, default=float, allow_nan=True),
                                encoding="utf-8")

    audit = {
        "provenance": _provenance(argv, band_hz, a.detrend_orders, primary, wide),
        "band_hz": [band_hz[0], band_hz[1]],
        "detrend_orders": [int(o) for o in a.detrend_orders],
        "angles_v_deg": primary,
        "angles_wide_v_deg": wide,
        "rows": rows,
    }
    (out / "audit.json").write_text(
        json.dumps(audit, indent=1, default=float, allow_nan=True), encoding="utf-8")
    if not a.json_only:
        _write_markdown(out, rows, audit["provenance"])
    print(out.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
