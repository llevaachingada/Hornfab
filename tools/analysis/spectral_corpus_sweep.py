"""Corpus-wide fixed-angle spectral ripple sweep over stored runs (REPORT-ONLY).

Walks a runs root, finds every run directory that holds ``best.json`` and the selected
``designs/<design_hash>/response.npz``, and reports the fixed-angle residual spread for a fixed set
of cuts (V+/-25, V+/-35, V+45 and H+25, H+35). All math is delegated to
:mod:`hornlab_search.metrics.spectral`; this tool only aggregates.

This is a REPORT-ONLY diagnostic. It is never a score term, it reads stored responses, and it makes
ZERO solver, mesher or GPU calls. ``J`` is carried for context only: it is NEVER compared or ranked
across identities, and a fixed-angle residual is comparative-only because its absolute value is
grid-dependent.

Outputs ``sweep.json`` (rows, per-identity stats, refusals, provenance) and ``sweep.md`` (header,
per-identity table, pooled diagnostic line). ``--out`` is refused when it exists and is not empty.

    python tools/analysis/spectral_corpus_sweep.py --runs-root runs \
        --out runs/analysis/corpus_sweep_2026-11-20
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from hornlab_search.metrics import spectral  # noqa: E402

#: Reporting band from the 2026-11-19 handoff.
DEFAULT_BAND_HZ = (1065.0, 4832.5)

#: ``name -> (axis, target angle)``. ``v`` uses ``v_angles_deg``/``spl_v_db``.
CUTS = {
    "V+25": ("v", 25.0),
    "V+35": ("v", 35.0),
    "V+45": ("v", 45.0),
    "V-25": ("v", -25.0),
    "V-35": ("v", -35.0),
    "H+25": ("h", 25.0),
    "H+35": ("h", 35.0),
}

#: Cuts that additionally get the IEC/Klippel ``band_mean`` reference.
BAND_MEAN_CUTS = ("V+25", "V+35")

#: Required keys in ``response.npz``.
REQUIRED_KEYS = ("freqs_hz", "v_angles_deg", "spl_v_db", "h_angles_deg", "spl_h_db")

#: The one primary metric a run must produce to count as usable.
PRIMARY = "V+35"


# ----------------------------------------------------------------------------- helpers

def _read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _load_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError):
        return None


def _identity(run_dir: Path, config) -> str:
    """``brief.name`` -> ``config.name`` -> run dir name, recorded verbatim."""
    if isinstance(config, dict):
        brief = config.get("brief")
        if isinstance(brief, dict) and brief.get("name") not in (None, ""):
            return str(brief["name"])
        if config.get("name") not in (None, ""):
            return str(config["name"])
    return run_dir.name


def _reason_code(reason: str | None) -> str | None:
    """Collapse a spectral refusal string into a stable counter key."""
    if not reason:
        return None
    text = str(reason)
    if "no reference sample" in text or "0-degree" in text:
        return "missing zero-degree reference"
    if "no angle sample" in text:
        return "missing target angle"
    if "insufficient degrees of freedom" in text:
        return "band too short"
    if "non-finite" in text:
        return "non-finite level"
    if "no samples in band" in text:
        return "no samples in band"
    if "non-positive or non-finite frequency" in text:
        return "bad frequency grid"
    if "missing key" in text:
        return "missing key"
    if "unreadable" in text or "cannot read" in text:
        return "unreadable npz"
    if "shape" in text:
        return "shape error"
    return "other"


def _finite_or_none(value):
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def _spearman(x, y, label: str, min_n: int = 5) -> dict:
    """Spearman rho over finite pairs; ``null`` (with a reason) when it is not meaningful."""
    xs_list: list[float] = []
    ys_list: list[float] = []
    for a, b in zip(x, y):
        if a is None or b is None:
            continue
        fa = float(a)
        fb = float(b)
        if np.isfinite(fa) and np.isfinite(fb):
            xs_list.append(fa)
            ys_list.append(fb)
    n = len(xs_list)
    if n < min_n:
        return {"label": label, "n": n, "rho": None, "p": None,
                "reason": f"n<{min_n} ({n} finite pairs)"}
    xs = np.asarray(xs_list, dtype=float)
    ys = np.asarray(ys_list, dtype=float)
    if np.all(xs == xs[0]):
        return {"label": label, "n": n, "rho": None, "p": None,
                "reason": "constant vector: " + label.split(",")[0].strip("() ")}
    if np.all(ys == ys[0]):
        return {"label": label, "n": n, "rho": None, "p": None,
                "reason": "constant vector: " + label.split(",")[1].strip("() ")}
    result = spearmanr(xs, ys)
    rho = float(result.statistic)
    p = float(result.pvalue)
    if not np.isfinite(rho):
        return {"label": label, "n": n, "rho": None, "p": None,
                "reason": "spearman returned non-finite rho"}
    return {"label": label, "n": n, "rho": rho, "p": p, "reason": None}


def _percentile(values, q):
    vals = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    return float(np.percentile(vals, q)) if vals.size else None


def _median(values):
    return _percentile(values, 50.0)


# ----------------------------------------------------------------------------- per-run row

def compute_run_row(run_dir, band_hz=DEFAULT_BAND_HZ) -> dict:
    """Compute one row for a run directory. Never raises for malformed stored data."""
    run_dir = Path(run_dir)
    config = _load_yaml(run_dir / "config.yaml")
    row = {
        "run": run_dir.name,
        "run_dir": run_dir.as_posix(),
        "identity": _identity(run_dir, config),
        "design_hash": None,
        "family": None,
        "J": None,
        "rip": None,
        "refused": False,
        "refusal_reason": None,
        "refusal_code": None,
        "refusals": {},
        "metrics": {},
    }

    best = _read_json(run_dir / "best.json", None)
    if not isinstance(best, dict):
        row.update(refused=True, refusal_reason="best.json missing or unreadable",
                   refusal_code="unreadable best.json")
        return row

    row["design_hash"] = best.get("design_hash")
    row["family"] = best.get("family")
    row["J"] = _finite_or_none(best.get("objective"))
    terms = best.get("terms")
    if isinstance(terms, dict):
        row["rip"] = _finite_or_none(terms.get("rip"))

    design_hash = row["design_hash"]
    if not design_hash:
        row.update(refused=True, refusal_reason="best.json has no design_hash",
                   refusal_code="missing design_hash")
        return row
    npz_path = run_dir / "designs" / str(design_hash) / "response.npz"
    if not npz_path.is_file():
        row.update(refused=True,
                   refusal_reason=f"missing response.npz at {npz_path.as_posix()}",
                   refusal_code="missing npz")
        return row

    try:
        with np.load(npz_path, allow_pickle=True) as z:
            missing = [k for k in REQUIRED_KEYS if k not in z.files]
            if missing:
                row.update(refused=True,
                           refusal_reason="missing key(s): " + ", ".join(missing),
                           refusal_code="missing key")
                return row
            arrays = {
                "f": np.asarray(z["freqs_hz"], dtype=float),
                "va": np.asarray(z["v_angles_deg"], dtype=float),
                "vs": np.asarray(z["spl_v_db"], dtype=float),
                "ha": np.asarray(z["h_angles_deg"], dtype=float),
                "hs": np.asarray(z["spl_h_db"], dtype=float),
            }
    except Exception as exc:  # noqa: BLE001 - stored file may be truncated/corrupt
        row.update(refused=True, refusal_reason=f"unreadable npz: {exc}",
                   refusal_code="unreadable npz")
        return row

    axes = {
        "v": (arrays["f"], arrays["va"], arrays["vs"]),
        "h": (arrays["f"], arrays["ha"], arrays["hs"]),
    }
    metrics = {}
    refusals = {}
    for name, (axis, angle) in CUTS.items():
        freqs, angles, spl = axes[axis]
        try:
            trend = spectral.fixed_angle_residual_curve(
                freqs, spl, angles, angle, band_hz=band_hz, detrend_order=2,
                reference="trend")
        except ValueError as exc:
            trend = {"rms_db": float("nan"), "reason": f"shape error: {exc}"}
        entry = {
            "trend": _finite_or_none(trend["rms_db"]),
            "trend_reason": trend.get("reason"),
        }
        if entry["trend"] is None:
            refusals[f"{name} trend"] = entry["trend_reason"] or "refused without reason"
        if name in BAND_MEAN_CUTS:
            try:
                band_mean = spectral.fixed_angle_residual_curve(
                    freqs, spl, angles, angle, band_hz=band_hz, reference="band_mean")
            except ValueError as exc:
                band_mean = {"rms_db": float("nan"), "reason": f"shape error: {exc}"}
            entry["band_mean"] = _finite_or_none(band_mean["rms_db"])
            entry["band_mean_reason"] = band_mean.get("reason")
            if entry["band_mean"] is None:
                refusals[f"{name} band_mean"] = (
                    entry["band_mean_reason"] or "refused without reason")
        metrics[name] = entry

    row["metrics"] = metrics
    row["refusals"] = refusals
    if metrics[PRIMARY]["trend"] is None:
        reason = metrics[PRIMARY]["trend_reason"] or "refused without reason"
        row.update(refused=True, refusal_reason=f"{PRIMARY} trend: {reason}",
                   refusal_code=_reason_code(reason))
    return row


# ----------------------------------------------------------------------------- discovery

def discover_runs(runs_root) -> tuple[list[Path], int]:
    """Return ``(run_dirs, skipped_without_design)`` under ``runs_root``, sorted deterministically.

    A candidate is a directory holding ``best.json`` whose ``design_hash`` selects an existing
    ``designs/<hash>/response.npz``. Sorted by run dir name, then relative path.
    """
    root = Path(runs_root)
    found: list[Path] = []
    skipped = 0
    for best_path in root.rglob("best.json"):
        run_dir = best_path.parent
        best = _read_json(best_path, None)
        design_hash = best.get("design_hash") if isinstance(best, dict) else None
        if not design_hash or not (run_dir / "designs" / str(design_hash) / "response.npz").is_file():
            skipped += 1
            continue
        found.append(run_dir)
    found.sort(key=lambda p: (p.name, p.relative_to(root).as_posix()))
    return found, skipped


# ----------------------------------------------------------------------------- stats

def identity_stats(identity: str, rows) -> dict:
    """Aggregate a list of rows (one identity, or the pooled diagnostic) into one record."""
    usable = [r for r in rows if not r["refused"]]
    v35 = [r["metrics"][PRIMARY]["trend"] for r in usable]
    v35_bm = [r["metrics"][PRIMARY].get("band_mean") for r in usable]
    v25 = [r["metrics"]["V+25"]["trend"] for r in usable]
    rip = [r["rip"] for r in usable]
    jvals = [r["J"] for r in usable]
    return {
        "identity": identity,
        "n": len(usable),
        "median_v35_trend": _median(v35),
        "p90_v35_trend": _percentile(v35, 90.0),
        "median_v35_band_mean": _median(v35_bm),
        "spearman_rip_v35": _spearman(rip, v35, "rip, V+35 trend"),
        "spearman_v25_v35": _spearman(v25, v35, "V+25 trend, V+35 trend"),
        "spearman_trend_bandmean": _spearman(v35, v35_bm, "V+35 trend, V+35 band_mean"),
        "spearman_j_v35": _spearman(jvals, v35, "J, V+35 trend"),
    }


def _count_codes(codes) -> dict:
    counts: dict[str, int] = {}
    for code in codes:
        if code is None:
            continue
        counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items()))


# ----------------------------------------------------------------------------- report

def _fmt(value, digits=3):
    if value is None:
        return "-"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    return "nan" if not np.isfinite(v) else f"{v:.{digits}f}"


def _rho_cell(stat):
    return _fmt(stat["rho"], 3) if stat["rho"] is not None else "null"


def _md_table(stats) -> str:
    header = [
        "identity", "n", "median V+35 trend (dB)", "p90 V+35 trend (dB)",
        "median V+35 band_mean (dB)", "rho(rip, V+35)", "rho(V+25, V+35)",
        "rho(V+35 trend, band_mean)", "rho(J, V+35)",
    ]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for s in stats:
        cells = [
            str(s["identity"]),
            str(s["n"]),
            _fmt(s["median_v35_trend"]),
            _fmt(s["p90_v35_trend"]),
            _fmt(s["median_v35_band_mean"]),
            _rho_cell(s["spearman_rip_v35"]),
            _rho_cell(s["spearman_v25_v35"]),
            _rho_cell(s["spearman_trend_bandmean"]),
            _rho_cell(s["spearman_j_v35"]),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _write_markdown(out: Path, stats, pooled, pooled_excluded, counts, refusal_counts,
                    metric_refusal_counts, provenance):
    lo, hi = provenance["band_hz"]
    header = [
        "# Corpus-wide fixed-angle spectral ripple sweep (REPORT-ONLY)",
        "",
        "**REPORT-ONLY.** This is never a score term. It reads stored responses and makes zero "
        "solver, mesher or GPU calls.",
        "",
        f"Band {lo:g}-{hi:g} Hz; `trend` = residual about the order-2 polynomial in `log2(f)`; "
        "`band_mean` = deviation from the in-band mean (IEC 60268-5 section 20.6 / Klippel AN 40). "
        "The fixed-angle residual is **comparative-only**: its absolute value is grid-dependent. "
        "Measured on the same horn: 1.441 on the 18-freq screen grid, 1.908 on verify, 1.313 on a "
        "91-freq dense grid.",
        "",
        "`J` is printed for context only. It is **NEVER compared or ranked across identities**; "
        "identities are different briefs, so their `J` values are not on a common scale.",
        "",
        f"Runs scanned: {counts['scanned']}; usable: {counts['usable']}; "
        f"refused: {counts['refused']}; skipped (no resolvable design): "
        f"{counts['skipped_no_design']}.",
        "",
    ]
    body = [
        "## Per-identity table",
        "",
        f"Only identities with n >= {counts['identity_min']} usable runs are listed "
        f"({counts['identities_below_min']} identit"
        f"{'y' if counts['identities_below_min'] == 1 else 'ies'} below the threshold omitted). "
        "`null` means the correlation was not computed; see the notes below.",
        "",
        _md_table(stats) if stats else "_No identity met the minimum run count._",
        "",
    ]
    notes = []
    for s in stats:
        for key in ("spearman_rip_v35", "spearman_v25_v35",
                    "spearman_trend_bandmean", "spearman_j_v35"):
            stat = s[key]
            if stat["rho"] is None:
                notes.append(f"- `{s['identity']}` / {stat['label']}: null - {stat['reason']}")
    if notes:
        body += ["### Correlation notes", ""] + notes + [""]

    body += [
        "## Pooled (diagnostic only)",
        "",
        "**WARNING: pooling across briefs is INVALID.** Different identities have different "
        "targets, bands and objectives; the pooled line below is a machinery sanity check only and "
        "must never be read as a population result.",
        "",
    ]
    if pooled["n"]:
        body.append(
            f"Pooled n={pooled['n']}; median V+35 trend={_fmt(pooled['median_v35_trend'])} dB; "
            f"p90={_fmt(pooled['p90_v35_trend'])} dB; "
            f"rho(rip, V+35)={_fmt(pooled['spearman_rip_v35']['rho'], 3)}. "
            f"Excluded: {pooled_excluded['refused']} refused run(s), "
            f"{pooled_excluded['below_identity_min']} usable run(s) in identities below the "
            f"n>={counts['identity_min']} threshold.")
    else:
        body.append("_No usable runs; pooled diagnostic not computed._")
    body.append("")

    body += ["## Refusals", ""]
    if refusal_counts:
        body.append("Run-level refusal codes:")
        body.append("")
        body += [f"- {code}: {n}" for code, n in refusal_counts.items()]
    else:
        body.append("No run-level refusals.")
    body.append("")
    if metric_refusal_counts:
        body.append("Metric-level refusal codes (a run can be usable for V+35 while another cut "
                    "refuses):")
        body.append("")
        body += [f"- {code}: {n}" for code, n in metric_refusal_counts.items()]
        body.append("")

    (out / "sweep.md").write_text("\n".join(header + body) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------- provenance

def _provenance(argv, band_hz, identity_min, identities):
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True,
            text=True, timeout=10, check=False).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        head = "unknown"
    try:
        import scipy
        scipy_version = scipy.__version__
    except Exception:  # noqa: BLE001
        scipy_version = "unknown"
    return {
        "git_head": head,
        "utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "interpreter": sys.executable,
        "numpy_version": np.__version__,
        "scipy_version": scipy_version,
        "argv": [str(x) for x in argv],
        "band_hz": [float(band_hz[0]), float(band_hz[1])],
        "detrend_order": 2,
        "cuts": {name: {"axis": axis, "angle_deg": angle}
                 for name, (axis, angle) in CUTS.items()},
        "band_mean_cuts": list(BAND_MEAN_CUTS),
        "identity_min": int(identity_min),
        "identities_filter": identities,
        "status": "REPORT-ONLY diagnostic; never a score term; zero solver/mesher/GPU calls",
    }


# ----------------------------------------------------------------------------- CLI

def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--runs-root", default="runs", help="root to walk for run directories")
    ap.add_argument("--out", required=True, help="output directory (must be empty or absent)")
    ap.add_argument("--identity-min", type=int, default=5,
                    help="minimum usable runs before an identity is tabulated")
    ap.add_argument("--identities", default=None,
                    help="comma-separated identity allow-list (exact match)")
    ap.add_argument("--limit", type=int, default=None,
                    help="only the first N runs in deterministic run-dir-name order")
    ap.add_argument("--band-hz", nargs=2, type=float, default=list(DEFAULT_BAND_HZ),
                    metavar=("LO", "HI"))
    a = ap.parse_args(argv)

    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing: {out} exists and is not empty")
    out.mkdir(parents=True, exist_ok=True)

    band_hz = (float(a.band_hz[0]), float(a.band_hz[1]))
    identities = None
    if a.identities:
        identities = [s.strip() for s in a.identities.split(",") if s.strip()]

    run_dirs, skipped_no_design = discover_runs(a.runs_root)
    if a.limit is not None:
        run_dirs = run_dirs[: max(0, int(a.limit))]

    rows = []
    with np.errstate(invalid="ignore", divide="ignore"):
        for i, run_dir in enumerate(run_dirs, start=1):
            rows.append(compute_run_row(run_dir, band_hz=band_hz))
            if i % 200 == 0:
                print(f"sweep: {i}/{len(run_dirs)} runs", file=sys.stderr)

    if identities is not None:
        rows = [r for r in rows if r["identity"] in identities]

    usable = [r for r in rows if not r["refused"]]
    refused = [r for r in rows if r["refused"]]

    by_identity: dict[str, list] = {}
    for r in rows:
        by_identity.setdefault(r["identity"], []).append(r)
    all_stats = [identity_stats(name, group) for name, group in by_identity.items()]
    all_stats.sort(key=lambda s: s["identity"])
    stats = [s for s in all_stats if s["n"] >= int(a.identity_min)]
    below_min = [s for s in all_stats if s["n"] < int(a.identity_min)]
    below_min_runs = sum(s["n"] for s in below_min)

    pooled = identity_stats("__pooled__", usable)
    pooled_excluded = {"refused": len(refused), "below_identity_min": below_min_runs}

    refusal_counts = _count_codes(r["refusal_code"] for r in refused)
    metric_codes = []
    for r in rows:
        for key, reason in r.get("refusals", {}).items():
            metric_codes.append(_reason_code(reason))
    metric_refusal_counts = _count_codes(metric_codes)

    counts = {
        "discovered": len(run_dirs),
        "scanned": len(rows),
        "usable": len(usable),
        "refused": len(refused),
        "skipped_no_design": int(skipped_no_design),
        "identity_min": int(a.identity_min),
        "identities_listed": len(stats),
        "identities_below_min": len(below_min),
    }
    provenance = _provenance(argv, band_hz, a.identity_min, identities)
    payload = {
        "provenance": provenance,
        "counts": counts,
        "refusal_counts": refusal_counts,
        "metric_refusal_counts": metric_refusal_counts,
        "identities_below_min": [
            {"identity": s["identity"], "n": s["n"],
             "reason": f"n<{int(a.identity_min)}"}
            for s in below_min
        ],
        "identity_stats": stats,
        "pooled": {k: v for k, v in pooled.items() if k != "identity"},
        "pooled_excluded": pooled_excluded,
        "rows": rows,
    }
    (out / "sweep.json").write_text(
        json.dumps(payload, indent=1, allow_nan=False), encoding="utf-8")
    _write_markdown(out, stats, pooled, pooled_excluded, counts, refusal_counts,
                    metric_refusal_counts, provenance)
    print(out.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
