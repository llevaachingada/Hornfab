"""Mesh-sensitivity comparison for one assembled horn+cabinet case at several mesh levels.

Purpose (senior directive 2026-11-22, C4): decide which *reported* quantities are stable
enough to compare between placements, rather than declaring the solver converged.  The tool
compares recorded BL headless runs level-to-level in **absolute complex pressure**, per
excitation, and keeps nulls out of ordinary phase statistics.

Rules implemented
-----------------
* Both excitation bases are read from each run; magnitudes are absolute dB re 20 uPa.
* A sample enters the RMS/phase statistics only when the reference level's magnitude is within
  ``--gate-db`` of that domain's band maximum.  Nulls are therefore excluded from phase RMS
  and reported separately (frequency, depth, level-to-level movement).
* Phase differences use circular statistics (``sqrt(-2 ln|mean e^{i dphi}|)``), never a plain
  average of wrapped angles.
* Only mesh resolution may differ between levels; the tool refuses runs whose frequency grids
  differ and prints each run's mesh statistics when ``--levels-json`` is supplied.

Outputs: ``mesh_sensitivity.json``, ``mesh_sensitivity.csv`` and ``mesh_sensitivity.png``.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.system.boundarylab.bl_results import read_bl_headless_result  # noqa: E402

P_REF = 20e-6
HORN = "excitation:horn"
WOOFER = "vented/voltage"
DOMAINS = (
    "observation:probe:on_axis_2m",
    "observation:horizontal-polar",
    "observation:vertical-polar",
)


def _db(mag: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(mag, dtype=float), 1e-300) / P_REF)


def _wrap_deg(rad: np.ndarray) -> np.ndarray:
    return (np.degrees(rad) + 180.0) % 360.0 - 180.0


def _circular_rms_deg(delta_rad: np.ndarray) -> float:
    if delta_rad.size == 0:
        return float("nan")
    resultant = abs(np.mean(np.exp(1j * delta_rad)))
    if resultant <= 0.0:
        return float("nan")
    return float(math.degrees(math.sqrt(max(-2.0 * math.log(min(resultant, 1.0)), 0.0))))


def _gated_mask(reference: np.ndarray, null_gate_db: float, floor_db: float) -> np.ndarray:
    """Two documented gates, both must pass.

    * null gate: at each frequency a sample must be within ``null_gate_db`` of that
      frequency's own peak magnitude, which is what excludes a null from phase statistics;
    * absolute floor: the frequency's own peak must be within ``floor_db`` of the domain's
      band peak, so a globally negligible frequency cannot supply phase samples.
    """
    mag = np.asarray(reference, dtype=float)
    if mag.size == 0:
        return np.zeros_like(mag, dtype=bool)
    local_peak = np.max(mag, axis=1, keepdims=True)
    band_peak = float(np.max(mag)) if mag.size else 0.0
    if band_peak <= 0.0:
        return np.zeros_like(mag, dtype=bool)
    above_null = mag >= local_peak * 10.0 ** (null_gate_db / 20.0)
    band_ok = (local_peak >= band_peak * 10.0 ** (floor_db / 20.0))
    return above_null & band_ok


def _summary(delta_db: np.ndarray, phase_deg: np.ndarray, used: np.ndarray) -> dict[str, Any]:
    if used.sum() == 0:
        return {"n_used": 0, "rms_db": None, "median_db": None, "p90_abs_db": None,
                "max_abs_db": None, "phase_rms_deg": None, "phase_median_deg": None}
    d = delta_db[used]
    ph = phase_deg[used]
    return {
        "n_used": int(used.sum()),
        "rms_db": float(np.sqrt(np.mean(np.square(d)))),
        "median_db": float(np.median(d)),
        "p90_abs_db": float(np.percentile(np.abs(d), 90.0)),
        "max_abs_db": float(np.max(np.abs(d))),
        "phase_rms_deg": _circular_rms_deg(np.radians(ph)),
        "phase_median_deg": float(np.median(ph)),
    }


def _nulls(freqs: np.ndarray, mag_db: np.ndarray) -> list[dict[str, Any]]:
    """Local magnitude minima at least 1 dB below both neighbours (on-axis across frequency)."""
    found: list[dict[str, Any]] = []
    peak = float(np.max(mag_db)) if mag_db.size else float("nan")
    for i in range(1, len(freqs) - 1):
        if mag_db[i] < mag_db[i - 1] - 1.0 and mag_db[i] < mag_db[i + 1] - 1.0:
            found.append({
                "freq_hz": float(freqs[i]),
                "magnitude_dbc": float(mag_db[i]),
                "depth_below_band_peak_db": float(peak - mag_db[i]),
            })
    return found


def _compare_pair(label: str, lab, ref, ref_label: str, null_gate_db: float, floor_db: float,
                  window_deg: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    freqs = ref.frequencies_hz
    report: dict[str, Any] = {f"{ref_label}->{label}": {"frequencies_hz": freqs.tolist()}}
    rows: list[dict[str, Any]] = []
    for excitation in (HORN, WOOFER):
        exc: dict[str, Any] = {}
        for domain in DOMAINS:
            a = ref.per_excitation_bases(domain)[excitation]
            b = lab.per_excitation_bases(domain)[excitation]
            if a.shape != b.shape:
                raise SystemExit(f"{label}: {domain}/{excitation} shapes differ: {a.shape} vs {b.shape}")
            mag_a = np.abs(a)
            mag_b = np.abs(b)
            delta_db = _db(mag_b) - _db(mag_a)
            phase_deg = _wrap_deg(np.angle(b / np.where(a == 0, 1e-300, a)))
            gate = _gated_mask(mag_a, null_gate_db, floor_db)
            if domain in ("observation:horizontal-polar", "observation:vertical-polar"):
                angles = ref.observation_sets[domain].angles_deg
                if angles is None:
                    raise SystemExit(f"{domain}: no angle grid recorded")
                window = np.abs(np.asarray(angles, dtype=float).reshape(-1)) <= window_deg
                gate = gate & window[None, :]
            exc[domain] = _summary(delta_db, phase_deg, gate)
            exc[domain]["gated_out"] = int((~gate).sum())
            for i, f in enumerate(freqs):
                for j in range(a.shape[1]):
                    rows.append({
                        "pair": f"{ref_label}->{label}", "excitation": excitation,
                        "domain": domain, "freq_hz": float(f), "sample": int(j),
                        "angle_deg": _angle_of(ref, domain, j),
                        "mag_ref_dbc": float(_db(mag_a[i, j])),
                        "mag_dbc": float(_db(mag_b[i, j])),
                        "delta_db": float(delta_db[i, j]),
                        "phase_delta_deg": float(phase_deg[i, j]),
                        "used": bool(gate[i, j]),
                    })
        on_axis_a = np.abs(ref.per_excitation_bases("observation:probe:on_axis_2m")[excitation])[:, 0]
        on_axis_b = np.abs(lab.per_excitation_bases("observation:probe:on_axis_2m")[excitation])[:, 0]
        exc["on_axis"] = {
            "freq_hz": freqs.tolist(),
            "ref_db": _db(on_axis_a).tolist(),
            "level_db": _db(on_axis_b).tolist(),
            "nulls_ref": _nulls(freqs, _db(on_axis_a)),
            "nulls_level": _nulls(freqs, _db(on_axis_b)),
        }
        report[f"{ref_label}->{label}"][excitation] = exc
    return report, rows


class _Sliced:
    """A read-only frequency-subset view of a BL headless result."""

    def __init__(self, result, index: np.ndarray) -> None:
        self._result = result
        self._index = np.asarray(index, dtype=int)
        self.frequencies_hz = np.asarray(result.frequencies_hz)[self._index]
        self.observation_sets = result.observation_sets

    def per_excitation_bases(self, domain: str):
        return {key: value[self._index]
                for key, value in self._result.per_excitation_bases(domain).items()}


def _angle_of(result, domain: str, index: int) -> float | None:
    obs = result.observation_sets.get(domain)
    if obs is None or obs.angles_deg is None:
        return None
    angles = np.asarray(obs.angles_deg, dtype=float).reshape(-1)
    return float(angles[index]) if index < angles.size else None


def _plot(path: Path, pairs: list[str], report: dict[str, Any]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(len(pairs), 2, figsize=(11.5, 3.1 * len(pairs)), squeeze=False)
    for row, pair in enumerate(pairs):
        block = report[pair]
        for col, excitation in enumerate((HORN, WOOFER)):
            ax = axes[row][col]
            on = block[excitation]["on_axis"]
            freqs = np.asarray(on["freq_hz"])
            ax.plot(freqs, on["ref_db"], "o-", color="#444444", ms=3, label="reference level")
            ax.plot(freqs, on["level_db"], "s--", color="#c0392b", ms=3, label="this level")
            for null in on["nulls_level"]:
                ax.annotate("null", (null["freq_hz"], null["magnitude_dbc"]),
                            textcoords="offset points", xytext=(0, -12),
                            ha="center", fontsize=7, color="#c0392b")
            ax.set_title(f"{pair} · {excitation}", fontsize=9)
            ax.set_xlabel("frequency [Hz]")
            ax.set_ylabel("on-axis |p| [dB re 20 µPa]")
            ax.grid(alpha=0.3)
            ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mesh-sensitivity comparison of assembled BL runs (C4).")
    parser.add_argument("--level", action="append", required=True,
                        help="LABEL=PATH_TO_RUN_DIR (repeatable, ordered coarse->fine)")
    parser.add_argument("--levels-json", default=None,
                        help="optional c4/levels.json to copy mesh statistics into the report")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--null-gate-db", type=float, default=-20.0,
                        help="a sample must be within this many dB of its own frequency's peak "
                             "to enter phase/magnitude statistics (default -20, excludes nulls)")
    parser.add_argument("--floor-db", type=float, default=-40.0,
                        help="a frequency's peak must be within this many dB of the domain band "
                             "peak to supply samples at all (default -40)")
    parser.add_argument("--window-deg", type=float, default=60.0,
                        help="half-window for polar statistics (default 60 deg)")
    parser.add_argument("--subset-hz", type=float, nargs="*", default=None,
                        help="restrict every level to these frequencies (each must exist in "
                             "every level); used for a targeted convergence probe")
    args = parser.parse_args(argv)

    levels: list[tuple[str, Path]] = []
    for item in args.level:
        label, _, path = item.partition("=")
        levels.append((label.strip(), Path(path.strip())))
    if len(levels) < 2:
        raise SystemExit("need at least two --level entries")

    results = {label: read_bl_headless_result(path) for label, path in levels}
    ref_label, _ = levels[0]
    if args.subset_hz:
        # Subset mode: each level only has to contain the requested frequencies.  This is the
        # targeted-probe path, where a fine level is solved at a handful of bins only.
        trimmed = {}
        for label, result in results.items():
            missing = [f for f in args.subset_hz
                       if not np.any(np.isclose(result.frequencies_hz, float(f)))]
            if missing:
                raise SystemExit(f"{label}: missing requested frequencies {missing}")
            index = np.array([int(np.argmin(np.abs(result.frequencies_hz - float(f))))
                              for f in args.subset_hz], dtype=int)
            trimmed[label] = _Sliced(result, index)
        results = trimmed
    else:
        reference_grid = results[ref_label].frequencies_hz
        for label, result in results.items():
            if not np.allclose(result.frequencies_hz, reference_grid):
                raise SystemExit(f"{label}: frequency grid differs from {ref_label}")

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "kind": "mesh_sensitivity_v1",
        "null_gate_db": args.null_gate_db,
        "floor_db": args.floor_db,
        "window_deg": args.window_deg,
        "levels": [label for label, _ in levels],
        "reference_level": ref_label,
    }
    if args.levels_json:
        report["mesh_levels"] = json.loads(Path(args.levels_json).read_text(encoding="utf-8"))

    pairs: list[str] = []
    all_rows: list[dict[str, Any]] = []
    for (prev_label, _), (label, _) in zip(levels, levels[1:]):
        block, rows = _compare_pair(label, results[label], results[prev_label], prev_label,
                                    args.null_gate_db, args.floor_db, args.window_deg)
        report.update(block)
        pairs.append(f"{prev_label}->{label}")
        all_rows.extend(rows)
    # also report fine vs coarse directly
    if len(levels) > 2:
        block, rows = _compare_pair(levels[-1][0], results[levels[-1][0]], results[ref_label],
                                    ref_label, args.null_gate_db, args.floor_db,
                                    args.window_deg)
        report.update(block)
        pairs.append(f"{ref_label}->{levels[-1][0]}")
        all_rows.extend(rows)

    (out / "mesh_sensitivity.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if all_rows:
        with (out / "mesh_sensitivity.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(all_rows[0]))
            writer.writeheader()
            writer.writerows(all_rows)
    _plot(out / "mesh_sensitivity.png", pairs, report)

    for pair in pairs:
        print(f"[{pair}]")
        for excitation in (HORN, WOOFER):
            exc = report[pair][excitation]
            on = exc["observation:probe:on_axis_2m"]
            polar_h = exc["observation:horizontal-polar"]
            polar_v = exc["observation:vertical-polar"]
            print(f"  {excitation:16s} on-axis rms={on['rms_db']} dB p90={on['p90_abs_db']} "
                  f"phase_rms={on['phase_rms_deg']} deg")
            print(f"  {'':16s} H-window rms={polar_h['rms_db']} dB  V-window rms="
                  f"{polar_v['rms_db']} dB  gated_out={polar_v['gated_out']}")
            if exc["on_axis"]["nulls_level"]:
                print(f"  {'':16s} nulls(level)={exc['on_axis']['nulls_level']}")
    print(f"wrote {out / 'mesh_sensitivity.json'}, .csv, .png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
