"""Horn loudness and horn x driver sensitivity from STORED solves. NO GPU, NO solver.

The horn solve does not depend on the driver, so every stored horn can be paired with any driver
file here (examples/drivers/*.yaml) at zero solve cost. Two tables:

* horn-only (always): throat diameter actually solved, output gap at f0 (dB short of a loaded throat),
  lowest loaded frequency (Re z >= 0.5), and the on-axis level at 1 m per 1 m/s throat velocity
  (compare horns on the SAME driver by the difference);
* per driver (``--driver``, repeatable): sensitivity at 2.83 V and 1 W / 1 m (power-averaged over the
  sensitivity band), level, excursion and efficiency at f0, maximum SPL at f0 (rated power or xmax),
  and the throat/exit mismatch to check before printing.

The sealed rear bowl of a ``kind: cone`` driver belongs to the HORN, not to the driver file, so
``--rear-box-l <litres>`` overrides it for every cone driver (the NET volume: motor subtracted).

Model and caveats: hornlab_search/metrics/loudness.py, hornlab_search/driver/compression.py,
docs/DRIVER_MODEL.md.

Usage (repo root)::

    .venv\\Scripts\\python.exe tools/loudness_report.py --night runs/nights/v4_resume_2026-10-27
    .venv\\Scripts\\python.exe tools/loudness_report.py --cells-csv docs/data/campaign_v4_2026-10-27/cells_summary.csv \
        --driver examples/drivers/<driver>.yaml --csv scratch/loudness.csv --md scratch/loudness.md
    .venv\\Scripts\\python.exe tools/loudness_report.py --run runs/<run_dir> --top 5 --driver a.yaml --driver b.yaml
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hornlab_search.driver.compression import (CompressionDriver, band_mean_db, drive,  # noqa: E402
                                               max_spl_db)
from hornlab_search.mesh.throat_check import fits_exit, throat_shape  # noqa: E402
from hornlab_search.metrics.loudness import horn_loudness  # noqa: E402
from hornlab_search.solve.cache import load_response  # noqa: E402

#: Upper edge of the default sensitivity band: above it the lumped driver model is not trusted.
SENS_HI_HZ = 4000.0


def _interp_db(f, y, at):
    f = np.asarray(f, float)
    y = np.asarray(y, float)
    ok = np.isfinite(y)
    if ok.sum() < 2 or not (f[ok].min() <= at <= f[ok].max()):
        return float("nan")
    return float(np.interp(math.log(at), np.log(f[ok]), y[ok]))


def _fmt(x, nd=1):
    return "-" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{x:.{nd}f}"


def run_dirs_from(args) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for r in args.run or []:
        out.append((Path(r).name, Path(r)))
    for n in args.night or []:
        p = Path(n)
        p = p / "summary.jsonl" if p.is_dir() else p
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                j = json.loads(line)
                out.append((j["id"].split("__", 1)[-1], Path(j["run_dir"])))
    if args.cells_csv:
        for row in csv.DictReader(open(args.cells_csv, encoding="utf-8")):
            out.append((row["cell"], REPO_ROOT / "runs" / row["run_dir"]))
    seen, uniq = set(), []
    for label, rd in out:                      # later entries (e.g. a resumed night) win per label
        if label in seen:
            uniq = [(lab, d) for lab, d in uniq if lab != label]
        seen.add(label)
        uniq.append((label, rd))
    return uniq


def designs_of(run_dir: Path, top: int) -> list[dict]:
    rows = []
    for line in (run_dir / "search.ndjson").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("ok") and (run_dir / "designs" / r["design_hash"] / "response.npz").exists():
                rows.append(r)
    best: dict[str, dict] = {}
    for r in rows:
        if r["design_hash"] not in best or r["objective"] < best[r["design_hash"]]["objective"]:
            best[r["design_hash"]] = r
    return sorted(best.values(), key=lambda r: r["objective"])[:top]


def config_of(run_dir: Path) -> dict:
    return yaml.safe_load((run_dir / "config.yaml").read_text(encoding="utf-8")) or {}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", action="append", help="a run directory (repeatable)")
    ap.add_argument("--night", action="append", help="a night folder or its summary.jsonl (repeatable)")
    ap.add_argument("--cells-csv", help="a campaign cells_summary.csv (run_dir relative to runs/)")
    ap.add_argument("--top", type=int, default=1, help="designs per run, best J first (default 1)")
    ap.add_argument("--driver", action="append", default=[], help="driver YAML (repeatable)")
    ap.add_argument("--rear-box-l", type=float,
                    help="sealed rear volume in litres for kind: cone drivers (NET, motor subtracted); "
                         "the bowl belongs to the horn, so this overrides the driver file")
    ap.add_argument("--volts", type=float, default=2.83, help="drive voltage rms (default 2.83)")
    ap.add_argument("--csv", help="write the per-frequency long table here")
    ap.add_argument("--md", help="write the markdown tables here (also printed)")
    args = ap.parse_args(argv)

    drivers = [CompressionDriver.from_yaml(p) for p in args.driver]
    if args.rear_box_l is not None:
        if args.rear_box_l <= 0.0:
            ap.error("--rear-box-l must be > 0 L")
        overridden = []
        for d in drivers:
            if d.kind == "cone":
                overridden.append(replace(d, rear_box_m3=args.rear_box_l * 1e-3))
            else:
                print(f"--rear-box-l ignored for {d.name}: only kind: cone has a sealed rear bowl",
                      file=sys.stderr)
                overridden.append(d)
        drivers = overridden
    horn_lines = ["| horn | design | J | f0 Hz | throat W x H mm (brief exit; round?) | output gap at f0 dB | loaded from Hz | "
                  "on-axis dB/(m/s) @1 m: f0 / 1 kHz / 2 kHz / 4 kHz |", "|---|---|---|---|---|---|---|---|"]
    drv_lines = ["| horn | design | driver | sens band Hz | sens 2.83 V dB | sens 1 W dB | SPL @f0 dB | "
                 "excursion @f0 mm pk | max SPL @f0 dB (limit) | eff. @f0 % | throat fits driver exit |",
                 "|---|---|---|---|---|---|---|---|---|---|---|"]
    long_rows = []
    for label, rd in run_dirs_from(args):
        try:
            cfg = config_of(rd)
            t = cfg.get("target") or {}
            exit_r = ((cfg.get("brief") or {}).get("driver") or {}).get("exit_radius_mm")
            brief_exit = 2.0 * float(exit_r) if exit_r else float("nan")
            ds = designs_of(rd, args.top)
        except Exception as exc:  # noqa: BLE001 - one bad run must not stop the table
            print(f"skip {label}: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        f0 = float(t.get("f0_hz") or t.get("band_lo_hz") or float("nan"))
        band_hi = float(t.get("band_hi_hz") or SENS_HI_HZ)
        for r in ds:
            resp = load_response(rd / "designs" / r["design_hash"] / "response.npz")
            h = horn_loudness(resp, f0_hz=f0)
            shape = throat_shape(rd / "designs" / r["design_hash"] / "mesh.msh")
            tw, th = shape["width_mm"], shape["height_mm"]
            ok_b, why_b = fits_exit(shape, brief_exit)
            f = h["freqs_hz"]
            lv = [_interp_db(f, h["onaxis_db_per_mps"], x) for x in (max(f0, f.min()), 1000, 2000, 4000)]
            horn_lines.append(
                f"| {label} | {r['design_hash']} | {r['objective']:.2f} | {f0:.0f} | "
                f"{_fmt(tw)} x {_fmt(th)} ({_fmt(brief_exit)}; {'ok' if ok_b else ('NO' if ok_b is False else '?')}) | "
                f"{_fmt(h['output_gap_at_f0_db'])} | "
                f"{_fmt(h['f_loaded_hz'], 0)} | {' / '.join(_fmt(x) for x in lv)} |")
            for i, fi in enumerate(f):
                long_rows.append({"horn": label, "design": r["design_hash"], "driver": "", "freq_hz": fi,
                                  "re_z": h["re_z"][i], "loading_db": h["loading_db"][i],
                                  "onaxis_db_per_mps": h["onaxis_db_per_mps"][i]})
            for d in drivers:
                out = drive(d, resp, volts_rms=args.volts)
                w1 = drive(d, resp, volts_rms=d.volts_for_watts(1.0))
                mx = max_spl_db(d, resp)
                lo = max(f0, d.min_crossover_hz or 0.0, float(f.min()))
                hi = min(band_hi, SENS_HI_HZ)
                at = max(f0, float(f.min()))
                i0 = int(np.argmin(np.abs(np.log(f / at))))
                lim = mx["limit"][i0] or "-"
                ok_d, why_d = fits_exit(shape, d.exit_diameter_mm)
                fits = "?" if ok_d is None else ("yes" if ok_d else f"NO: {why_d}")
                tag = d.name
                if d.kind == "cone":
                    tag += (f" (cone, bowl {d.rear_box_m3 * 1e3:.2f} L)" if d.rear_box_m3
                            else " (cone, no bowl)")
                if d.mass_may_include_air_load:
                    tag += " (Mms! air-load split missing)"
                if out["breakup_applied"]:
                    tag += f" (breakup [inferred] >{d.f_breakup_hz:.0f} Hz)"
                drv_lines.append(
                    f"| {label} | {r['design_hash']} | {tag} | "
                    f"{lo:.0f}-{hi:.0f} | {_fmt(band_mean_db(f, out['spl_onaxis_db'], lo, hi))} | "
                    f"{_fmt(band_mean_db(f, w1['spl_onaxis_db'], lo, hi))} | "
                    f"{_fmt(_interp_db(f, out['spl_onaxis_db'], at))} | "
                    f"{_fmt(out['excursion_mm_peak'][i0], 3)} @{f[i0]:.0f} | "
                    f"{_fmt(mx['max_spl_db'][i0])} ({lim}) | {_fmt(out['efficiency_pct'][i0])} | {fits} |")
                for i, fi in enumerate(f):
                    long_rows.append({"horn": label, "design": r["design_hash"], "driver": d.name, "freq_hz": fi,
                                      "re_z": h["re_z"][i], "loading_db": h["loading_db"][i],
                                      "onaxis_db_per_mps": h["onaxis_db_per_mps"][i],
                                      "spl_volts_db": out["spl_onaxis_db"][i], "spl_1w_db": w1["spl_onaxis_db"][i],
                                      "excursion_mm_peak": out["excursion_mm_peak"][i],
                                      "z_in_mag_ohm": abs(out["z_in_ohm"][i]),
                                      "efficiency_pct": out["efficiency_pct"][i],
                                      "sd_eff_m2": out["sd_eff_m2"][i],
                                      "max_spl_db": mx["max_spl_db"][i], "max_spl_limit": mx["limit"][i]})
    text = "## Horn only (same driver: compare by difference)\n\n" + "\n".join(horn_lines) + "\n"
    if drivers:
        text += (f"\n## Horn x driver ({args.volts:g} V rms; 1 W = into the nominal impedance; "
                 f"levels at 1 m on axis; sensitivity band = f0 (or the driver's min crossover) to "
                 f"min(band top, {SENS_HI_HZ:.0f} Hz))\n\n" + "\n".join(drv_lines) + "\n")
    print(text)
    if args.md:
        Path(args.md).write_text(text, encoding="utf-8")
    if args.csv and long_rows:
        keys = sorted({k for r in long_rows for k in r}, key=lambda k: list(long_rows[-1]).index(k)
                      if k in long_rows[-1] else 99)
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(long_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
