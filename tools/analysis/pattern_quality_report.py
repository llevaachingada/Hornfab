"""WP2 report-only pattern-quality CLI over stored ``response.npz`` files.

Zero BEM, zero GPU, zero solver: this tool only reads immutable response arrays.  It requires an
explicit ``--out`` directory (never a default inside ``docs/evidence/``), writes a machine-readable
per-frequency JSON report and a wide CSV there, and prints a compact console summary.

``--parity`` instead compares the legacy outermost H/V widths and the balloon DI against the
stored ``metrics.json`` of each design (180-degree sentinel cells excluded), prints the per-design
max |delta| and comparable-cell count, and exits 2 if any delta exceeds 1e-9 deg / 1e-12 dB.

Definitions (reused, never forked):

* legacy - ``metrics.polar.beamwidth_deg`` outermost on-axis-referenced -6.0206 dB crossings;
* connected - ``metrics.acoustic_v2.main_lobe`` first crossing each side from boresight;
* off-axis excess - the existing H12 threshold from ``objective.scalar_v7``;
* spherical DI - ``di_from_balloon`` with ``sin_theta_weights`` (``evaluate.metrics_from_response``
  path), and the connected-lobe map from ``metrics.acoustic_v2.balloon_lobes``.

A missing / malformed / too-sparse balloon is a typed refusal in the report: no spherical value is
invented.  ``--require-balloon`` turns that annotation into a non-zero exit.

Usage (repo root):
    .venv\\Scripts\\python.exe tools\\analysis\\pattern_quality_report.py runs\\<run> [runs\\<run> ...]
    .venv\\Scripts\\python.exe tools\\analysis\\pattern_quality_report.py runs\\<run>\\designs\\<hash> \\
        --out docs\\evidence\\pattern_quality_readonly --verbose
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from hornlab_search.metrics.pattern_quality import (  # noqa: E402
    LEGACY_SENTINEL_DEG,
    METHOD_VERSION,
    PatternQualityInputError,
    pattern_quality_from_response,
)
from hornlab_search.solve.cache import load_response  # noqa: E402

TOOL = "pattern_quality_report"
SCHEMA = "pattern_quality.report.v1"

#: Parity tolerances: the legacy width is the stored scalar once the sentinel is excluded; the
#: spherical DI is the canonical scoring-path quadrature.  Anything above these floors is a real
#: divergence, not print rounding.
PARITY_ANGLE_TOL_DEG = 1.0e-9
PARITY_DI_TOL_DB = 1.0e-12

CSV_FIELDS = (
    "input_label", "input_path", "run_dir", "design_hash", "family", "freq_hz", "plane",
    "legacy_width_deg", "legacy_status", "legacy_n_crossings",
    "connected_width_deg", "connected_status",
    "lower_edge_deg", "lower_edge_status", "upper_edge_deg", "upper_edge_status",
    "island_count", "island_total_extent_deg", "n_threshold_transitions", "n_reentries",
    "offaxis_max_db", "offaxis_max_angle_deg", "mean_excess_db", "mean_excess_in_coverage_db",
    "di_db", "di_status", "di_weighting", "balloon_island_count", "balloon_max_above_axis_db",
    "diagonal_bw45_deg", "diagonal_bw135_deg", "pattern_quality_flags",
)


# --------------------------------------------------------------------------- input resolution


def _run_dir_for(design_dir: Path) -> Path | None:
    """The run directory for a design dir, handling ``verify/designs/<hash>`` too."""
    if design_dir.parent.name != "designs":
        return None
    grand = design_dir.parent.parent
    return grand.parent if grand.name == "verify" else grand


def _read_json(path: Path) -> dict:
    try:
        out = json.loads(path.read_text(encoding="utf-8"))
        return out if isinstance(out, dict) else {}
    except (OSError, ValueError):
        return {}


def resolve_response(path: Path, design_hash: str | None) -> tuple[Path, Path | None, str, str]:
    """Resolve one CLI input to (response.npz, run_dir, design_hash, family)."""
    p = Path(path)
    if p.is_file():
        if p.suffix.lower() != ".npz":
            raise PatternQualityInputError(f"{p}: expected a directory or a response.npz file")
        ddir = p.parent
        run_dir = _run_dir_for(ddir)
        meta = _read_json(ddir / "design.json")
        return p, run_dir, str(meta.get("design_hash") or ddir.name), str(meta.get("family") or "")

    if not p.is_dir():
        raise PatternQualityInputError(f"{p}: not a file or directory")

    if (p / "response.npz").is_file():
        run_dir = _run_dir_for(p)
        meta = _read_json(p / "design.json")
        return p / "response.npz", run_dir, str(meta.get("design_hash") or p.name), str(
            meta.get("family") or "")

    subs = [p / "designs", p / "verify" / "designs"]
    if design_hash:
        for sub in subs:
            q = sub / design_hash / "response.npz"
            if q.is_file():
                meta = _read_json(q.parent / "design.json")
                return q, p, design_hash, str(meta.get("family") or "")
        raise PatternQualityInputError(
            f"{p}: no response.npz for design_hash {design_hash!r} in designs/ or verify/designs/")

    best = _read_json(p / "best.json")
    dh = best.get("design_hash")
    if isinstance(dh, str) and dh:
        for sub in subs:
            q = sub / dh / "response.npz"
            if q.is_file():
                meta = _read_json(q.parent / "design.json")
                return q, p, dh, str(meta.get("family") or "")

    found: list[tuple[Path, str, str]] = []
    for sub in subs:
        if not sub.is_dir():
            continue
        for dd in sorted(sub.iterdir()):
            if (dd / "response.npz").is_file():
                meta = _read_json(dd / "design.json")
                found.append((dd / "response.npz", dd.name, str(meta.get("family") or "")))
    if len(found) == 1:
        q, dh2, fam = found[0]
        return q, p, dh2, fam
    if not found:
        raise PatternQualityInputError(
            f"{p}: no response.npz found (not a run dir, design dir, or response.npz path)")
    raise PatternQualityInputError(
        f"{p}: {len(found)} designs carry response.npz; pass --design-hash to choose one")


def _coverage_and_name(run_dir: Path | None) -> tuple[float | None, float | None, str | None]:
    """Coverage angles / config name from a run's config.yaml, when available."""
    if run_dir is None:
        return None, None, None
    try:
        import yaml  # noqa: PLC0415 - read-only, optional

        cfg = yaml.safe_load((run_dir / "config.yaml").read_text(encoding="utf-8"))
        if not isinstance(cfg, dict):
            return None, None, None
        target = cfg.get("target") or {}
        h = target.get("coverage_h_deg")
        v = target.get("coverage_v_deg")
        return (
            None if h is None else float(h),
            None if v is None else float(v),
            cfg.get("name"),
        )
    except Exception:  # noqa: BLE001 - metadata is best effort; the cut report still runs
        return None, None, None


# --------------------------------------------------------------------------- CSV / JSON helpers


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, (float, np.floating)):
        return "" if not math.isfinite(float(value)) else float(value)
    if isinstance(value, (list, tuple)):
        return ";".join(str(v) for v in value)
    return str(value)


def _json_default(obj):
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def _finite(values):
    out = []
    for v in values:
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v)):
            out.append(float(v))
    return out


def _mean(values):
    vals = _finite(values)
    return None if not vals else float(sum(vals) / len(vals))


def _max(values):
    vals = _finite(values)
    return None if not vals else float(max(vals))


def _fmt(value, spec: str = ".1f") -> str:
    if value is None:
        return "-"
    if isinstance(value, float) and not math.isfinite(value):
        return "-"
    return format(value, spec)


def _rows_for_csv(record: dict) -> list[dict]:
    input_meta = record["input"]
    rows: list[dict] = []
    for fr in record["report"]["per_frequency"]:
        for plane in ("H", "V"):
            cut = fr[plane]
            rows.append({
                "input_label": input_meta["label"],
                "input_path": input_meta["response_path"],
                "run_dir": input_meta.get("run_dir") or "",
                "design_hash": input_meta["design_hash"],
                "family": input_meta.get("family") or "",
                "freq_hz": fr["freq_hz"],
                "plane": plane,
                "legacy_width_deg": cut["legacy"]["width_deg"],
                "legacy_status": cut["legacy"]["status"],
                "legacy_n_crossings": cut["legacy"]["n_crossings"],
                "connected_width_deg": cut["connected"]["width_deg"],
                "connected_status": cut["connected"]["status"],
                "lower_edge_deg": cut["connected"]["lower_edge_deg"],
                "lower_edge_status": cut["connected"]["lower_edge_status"],
                "upper_edge_deg": cut["connected"]["upper_edge_deg"],
                "upper_edge_status": cut["connected"]["upper_edge_status"],
                "island_count": cut["connected"]["island_count"],
                "island_total_extent_deg": cut["connected"]["island_total_extent_deg"],
                "n_threshold_transitions": cut["connected"]["n_threshold_transitions"],
                "n_reentries": cut["connected"]["n_reentries"],
                "offaxis_max_db": cut["off_axis"]["max_offaxis_db"],
                "offaxis_max_angle_deg": cut["off_axis"]["max_offaxis_angle_deg"],
                "mean_excess_db": cut["off_axis"]["mean_excess_db"],
                "mean_excess_in_coverage_db": cut["off_axis"]["mean_excess_in_coverage_db"],
                "pattern_quality_flags": cut.get("pattern_quality_flags") or [],
            })
        balloon = fr["balloon"]
        lobes = balloon.get("lobe_map") or {}
        diag = balloon.get("diagonal") or {}
        rows.append({
            "input_label": input_meta["label"],
            "input_path": input_meta["response_path"],
            "run_dir": input_meta.get("run_dir") or "",
            "design_hash": input_meta["design_hash"],
            "family": input_meta.get("family") or "",
            "freq_hz": fr["freq_hz"],
            "plane": "SPHERE",
            "di_db": balloon.get("di_db"),
            "di_status": balloon.get("status"),
            "di_weighting": balloon.get("weighting"),
            "balloon_island_count": lobes.get("island_count"),
            "balloon_max_above_axis_db": lobes.get("max_above_axis_db"),
            "diagonal_bw45_deg": diag.get("diagonal_bw45_deg"),
            "diagonal_bw135_deg": diag.get("diagonal_bw135_deg"),
            "pattern_quality_flags": balloon.get("pattern_quality_flags") or [],
        })
    return rows


# --------------------------------------------------------------------------- console


def _summary_line(record: dict) -> str:
    report = record["report"]
    rows = report["per_frequency"]
    legacy_h = _mean([r["H"]["legacy"]["width_deg"] for r in rows])
    legacy_v = _mean([r["V"]["legacy"]["width_deg"] for r in rows])
    conn_h = _mean([r["H"]["connected"]["width_deg"] for r in rows])
    conn_v = _mean([r["V"]["connected"]["width_deg"] for r in rows])
    cens_h = sum(1 for r in rows if r["H"]["connected"]["status"] != "valid")
    cens_v = sum(1 for r in rows if r["V"]["connected"]["status"] != "valid")
    islands = _max([r["H"]["connected"]["island_count"] for r in rows]
                   + [r["V"]["connected"]["island_count"] for r in rows])
    offaxis = _max([r["H"]["off_axis"]["max_offaxis_db"] for r in rows]
                   + [r["V"]["off_axis"]["max_offaxis_db"] for r in rows])
    di = _mean([r["balloon"].get("di_db") for r in rows])
    meta = record["input"]
    return (
        f"{meta['label']:<34} {meta.get('family') or '-':<10} {len(rows):>4} "
        f"{_fmt(legacy_h, '.1f'):>8} {_fmt(legacy_v, '.1f'):>8} "
        f"{_fmt(conn_h, '.1f'):>8} {_fmt(conn_v, '.1f'):>8} "
        f"{cens_h:>3}/{cens_v:<3} {_fmt(islands, '.0f'):>4} "
        f"{_fmt(offaxis, '+.2f'):>7} {_fmt(di, '.2f'):>6} {report['balloon']['status']}"
    )


SUMMARY_HEADER = (
    f"{'label':<34} {'family':<10} {'nf':>4} "
    f"{'legacyH':>8} {'legacyV':>8} {'connH':>8} {'connV':>8} "
    f"{'cenH/V':>7} {'isl':>4} {'offax':>7} {'DI':>6} balloon"
)


def _verbose_lines(record: dict) -> list[str]:
    meta = record["input"]
    lines = [f"-- {meta['label']} ({meta['response_path']})"]
    for fr in record["report"]["per_frequency"]:
        h, v, b = fr["H"], fr["V"], fr["balloon"]
        lines.append(
            f"  {fr['freq_hz']:8.1f} Hz  "
            f"H leg/conn {_fmt(h['legacy']['width_deg'], '6.1f')}/{_fmt(h['connected']['width_deg'], '6.1f')}"
            f" ({h['connected']['status']:<9})  "
            f"V leg/conn {_fmt(v['legacy']['width_deg'], '6.1f')}/{_fmt(v['connected']['width_deg'], '6.1f')}"
            f" ({v['connected']['status']:<9})  "
            f"isl {_fmt(h['connected']['island_count'], '2.0f')}/{_fmt(v['connected']['island_count'], '2.0f')}  "
            f"DI {_fmt(b.get('di_db'), '.2f'):>6}  "
            f"flags {','.join(fr['pattern_quality_flags']) or '-'}"
        )
    return lines


# --------------------------------------------------------------------------- parity


def parity_comparison(report: dict, stored: dict) -> dict:
    """Compare a report against the stored ``metrics.json`` arrays for one design.

    Legacy outermost widths are compared cell-by-cell (H and V), excluding the stored
    180.0-degree "no crossing" sentinel.  Spherical DI is compared against ``di_db``.  Any missing
    or wrongly sized stored array is a typed refusal, never a silent skip.
    """
    rows = report["per_frequency"]
    freqs = np.asarray([r["freq_hz"] for r in rows], dtype=float)
    stored_freqs = np.asarray(stored.get("freqs_hz") or [], dtype=float)
    if stored_freqs.size != freqs.size or not np.allclose(
            stored_freqs, freqs, rtol=1.0e-12, atol=1.0e-9):
        raise PatternQualityInputError(
            f"stored metrics.json does not match the response grid "
            f"({stored_freqs.size} vs {freqs.size} frequencies)")

    legacy: list[float] = []
    per_plane = {"H": 0, "V": 0}
    for plane, key, plane_key in (("H", "bw_h_deg", "H"), ("V", "bw_v_deg", "V")):
        arr = np.asarray(stored.get(key) or [], dtype=float)
        if arr.size != freqs.size:
            raise PatternQualityInputError(f"stored metrics.json {key} has {arr.size} cells, "
                                           f"expected {freqs.size}")
        for i, row in enumerate(rows):
            stored_width = arr[i]
            report_width = row[plane]["legacy"]["width_deg"]
            if stored_width is None or not math.isfinite(float(stored_width)):
                continue
            if abs(float(stored_width) - float(LEGACY_SENTINEL_DEG)) <= 1.0e-12:
                continue                    # the legacy no-crossing sentinel is not a measurement
            if report_width is None:
                continue
            legacy.append(abs(float(report_width) - float(stored_width)))
            per_plane[plane_key] += 1

    di_cells: list[float] = []
    di_arr = np.asarray(stored.get("di_db") or [], dtype=float)
    if di_arr.size != freqs.size:
        raise PatternQualityInputError(f"stored metrics.json di_db has {di_arr.size} cells, "
                                       f"expected {freqs.size}")
    for i, row in enumerate(rows):
        stored_di = di_arr[i]
        report_di = row["balloon"].get("di_db")
        if stored_di is None or not math.isfinite(float(stored_di)) or report_di is None:
            continue
        di_cells.append(abs(float(report_di) - float(stored_di)))
    if not di_cells:
        raise PatternQualityInputError(
            f"no comparable DI cell (balloon status {report['balloon']['status']}); parity "
            "cannot be established")

    legacy_max = None if not legacy else float(max(legacy))
    di_max = None if not di_cells else float(max(di_cells))
    failed = ((legacy_max is not None and legacy_max > PARITY_ANGLE_TOL_DEG)
              or (di_max is not None and di_max > PARITY_DI_TOL_DB))
    return {
        "legacy_comparable_cells": int(len(legacy)),
        "legacy_h_cells": int(per_plane["H"]),
        "legacy_v_cells": int(per_plane["V"]),
        "legacy_max_abs_delta_deg": legacy_max,
        "di_comparable_cells": int(len(di_cells)),
        "di_max_abs_delta_db": di_max,
        "angle_tolerance_deg": PARITY_ANGLE_TOL_DEG,
        "di_tolerance_db": PARITY_DI_TOL_DB,
        "failed": bool(failed),
    }


def _print_parity(label: str, comp: dict) -> None:
    legacy = ("n/a" if comp["legacy_max_abs_delta_deg"] is None
              else f"{comp['legacy_max_abs_delta_deg']:.3e}")
    di = ("n/a" if comp["di_max_abs_delta_db"] is None
          else f"{comp['di_max_abs_delta_db']:.3e}")
    print(f"{label} comparable legacy cells= {comp['legacy_comparable_cells']} "
          f"max|report_legacy - stored_bw| = {legacy} deg")
    print(f"{label} n={comp['di_comparable_cells']} "
          f"max|diag_di - stored_metrics_di| = {di} dB")


# --------------------------------------------------------------------------- main


class _ToolArgumentParser(argparse.ArgumentParser):
    """Argparse parser that prints a typed, tool-prefixed error instead of a bare traceback."""

    def error(self, message):
        print(f"{TOOL}: argument error: {message}", file=sys.stderr)
        raise SystemExit(2)


def main(argv=None) -> int:
    ap = _ToolArgumentParser(
        description="Report-only WP2 pattern-quality diagnostics over stored response.npz files.")
    ap.add_argument("inputs", nargs="+",
                    help="run directories, design directories, or response.npz paths")
    ap.add_argument("--out", required=True,
                    help="output dir for the report JSON/CSV; never runs/ (required)")
    ap.add_argument("--design-hash", default=None,
                    help="pick this design when a run directory contains more than one")
    ap.add_argument("--require-balloon", action="store_true",
                    help="exit 2 when an input's full balloon is missing/refused")
    ap.add_argument("--parity", action="store_true",
                    help="compare legacy H/V widths and balloon DI with the stored metrics.json; "
                         "exit 2 if any delta exceeds 1e-9 deg / 1e-12 dB")
    ap.add_argument("--verbose", action="store_true", help="also print per-frequency rows")
    ns = ap.parse_args(argv)

    out_dir = Path(ns.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    parity_rows: list[dict] = []
    refusals: list[str] = []
    balloon_refusals: list[str] = []

    for raw in ns.inputs:
        path = Path(raw)
        comp = None
        try:
            response_path, run_dir, design_hash, family = resolve_response(path, ns.design_hash)
            coverage_h, coverage_v, config_name = _coverage_and_name(run_dir)
            resp = load_response(response_path)
            report = pattern_quality_from_response(
                resp, coverage_h_deg=coverage_h, coverage_v_deg=coverage_v)
            if ns.parity:
                comp = parity_comparison(
                    report, _read_json(response_path.parent / "metrics.json"))
        except (PatternQualityInputError, OSError, ValueError) as exc:
            # Expected input/config problems are typed refusals.  Anything else re-raises so a
            # tool bug fails loudly instead of looking like bad data.
            refusals.append(f"{raw}: {type(exc).__name__}: {exc}")
            continue

        label = str(config_name or (run_dir.name if run_dir is not None else response_path.parent.name))
        label = f"{label}:{design_hash}"
        if ns.parity:
            assert comp is not None
            parity_rows.append({"input": raw, "label": label, "comparison": comp})
        record = {
            "input": {
                "label": label,
                "response_path": str(response_path),
                "run_dir": None if run_dir is None else str(run_dir),
                "design_hash": design_hash,
                "family": family or None,
                "coverage_h_deg": coverage_h,
                "coverage_v_deg": coverage_v,
            },
            "report": report,
        }
        records.append(record)

        bstatus = report["balloon"]["status"]
        if bstatus != "valid":
            balloon_refusals.append(
                f"{label}: {bstatus} "
                f"({report['balloon'].get('error_type', '-')}: {report['balloon'].get('error', '-')})")

    if refusals:
        for line in refusals:
            print(f"[refused] {line}", file=sys.stderr)
        return 2
    if ns.require_balloon and balloon_refusals:
        for line in balloon_refusals:
            print(f"[refused-balloon] {line}", file=sys.stderr)
        return 2
    if not records:
        print("[refused] no usable inputs", file=sys.stderr)
        return 2

    for line in balloon_refusals:
        print(f"[balloon-refused] {line}", file=sys.stderr)

    if ns.parity:
        for row in parity_rows:
            _print_parity(row["label"], row["comparison"])
        failed = any(row["comparison"]["failed"] for row in parity_rows)
        parity_path = out_dir / "parity_check.json"
        parity_path.write_text(json.dumps(
            {"schema": "pattern_quality.parity.v1", "rows": parity_rows},
            indent=1, allow_nan=False, default=_json_default) + "\n", encoding="utf-8")
        print(f"\nwrote {parity_path}")
        return 2 if failed else 0

    payload = {
        "schema": SCHEMA,
        "method": METHOD_VERSION,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "definitions": records[0]["report"]["definitions"],
        "reports": records,
    }
    json_path = out_dir / "pattern_quality_reports.json"
    json_path.write_text(json.dumps(payload, indent=1, allow_nan=False, default=_json_default)
                         + "\n", encoding="utf-8")

    csv_path = out_dir / "pattern_quality_by_frequency.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            for row in _rows_for_csv(record):
                writer.writerow({k: _cell(row.get(k)) for k in CSV_FIELDS})

    print(SUMMARY_HEADER)
    for record in records:
        print(_summary_line(record))
    if ns.verbose:
        for record in records:
            for line in _verbose_lines(record):
                print(line)
    print(f"\nwrote {json_path}")
    print(f"wrote {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
