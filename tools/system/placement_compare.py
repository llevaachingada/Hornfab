"""Compare the per-excitation Boundary Lab results of the three staged placements.

Reads three complete BL headless runs through the existing importer
(:func:`bl_results.read_bl_headless_result`) and writes:

* ``placement_compare.csv``  — per frequency, per case, per channel: on-axis level and
  relative phase, plus vertical-window spread;
* ``placement_compare.png``  — on-axis level per channel, relative phase, and the vertical
  polar at the crossover region;
* ``placement_compare.json`` — the scalar summary quoted in the evidence README.

Labels are part of the output: the horn channel is Pa per a 1 m/s prescribed normal
velocity, the woofer channel is Pa per the 2.83 V electrical reference. They are **not** a
calibrated two-way system and no combined SPL is written.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hornlab_search.system.boundarylab.bl_results import read_bl_headless_result  # noqa: E402

P_REF = 20e-6
CROSSOVER_HZ = 1000.0


def _db(p: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(p), 1e-30) / P_REF)


def _db1(value: complex) -> float:
    return float(20.0 * np.log10(max(abs(value), 1e-30) / P_REF))


def _wrap_deg(x: np.ndarray) -> np.ndarray:
    return (np.degrees(x) + 180.0) % 360.0 - 180.0


def _angles(result, domain: str) -> np.ndarray | None:
    obs = result.observation_sets.get(domain)
    if obs is None or obs.angles_deg is None:
        return None
    return np.asarray(obs.angles_deg, dtype=float).reshape(-1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--case", action="append", required=True,
                        help="LABEL=PATH_TO_RUN_DIR (repeatable)")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    cases: dict[str, Path] = {}
    for item in args.case:
        label, _, path = item.partition("=")
        cases[label.strip()] = Path(path.strip())
    results = {label: read_bl_headless_result(path) for label, path in cases.items()}
    freqs = next(iter(results.values())).frequencies_hz
    for label, result in results.items():
        if not np.allclose(result.frequencies_hz, freqs):
            raise SystemExit(f"{label}: frequency grid differs from the first case")

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    horn_id, woofer_id = "excitation:horn", "vented/voltage"

    rows: list[dict] = []
    summary: dict[str, dict] = {}
    for label, result in results.items():
        on_axis = result.per_excitation_bases("observation:probe:on_axis_2m")
        vertical = result.per_excitation_bases("observation:vertical-polar")
        ang = _angles(result, "observation:vertical-polar")
        window = np.abs(ang) <= 60.0 if ang is not None else slice(None)
        h = on_axis[horn_id][:, 0]
        w = on_axis[woofer_id][:, 0]
        rel_phase = _wrap_deg(np.angle(h / w))
        v_horn = _db(vertical[horn_id])
        v_woof = _db(vertical[woofer_id])
        # vertical-window spread: max-min over the +-60 deg window, per frequency
        spread_h = np.ptp(v_horn[:, window], axis=1) if ang is not None else np.full(len(freqs), np.nan)
        spread_w = np.ptp(v_woof[:, window], axis=1) if ang is not None else np.full(len(freqs), np.nan)
        for i, f in enumerate(freqs):
            rows.append({
                "case": label, "freq_hz": float(f),
                "horn_on_axis_dbc_1ms": _db1(h[i]),
                "woofer_on_axis_dbc_283v": _db1(w[i]),
                "relative_phase_deg": float(rel_phase[i]),
                "horn_vertical_spread_db_60deg": float(spread_h[i]),
                "woofer_vertical_spread_db_60deg": float(spread_w[i]),
            })
        near = int(np.argmin(np.abs(freqs - CROSSOVER_HZ)))
        summary[label] = {
            "n_freq": int(len(freqs)),
            "on_axis_horn_db_at_crossover": _db1(h[near]),
            "on_axis_woofer_db_at_crossover": _db1(w[near]),
            "relative_phase_deg_at_crossover": float(rel_phase[near]),
            "horn_vertical_spread_db_at_crossover": float(spread_h[near]),
            "woofer_vertical_spread_db_at_crossover": float(spread_w[near]),
            "crossover_frequency_used_hz": float(freqs[near]),
            "horn_vertical_polar_db_1khz": v_horn[near].tolist(),
            "woofer_vertical_polar_db_1khz": v_woof[near].tolist(),
            "vertical_angles_deg": None if ang is None else ang.tolist(),
        }

    # pairwise deltas, per frequency
    labels = list(results)
    deltas: dict[str, dict] = {}
    for a, b in zip(labels, labels[1:]):
        ra = [r for r in rows if r["case"] == a]
        rb = [r for r in rows if r["case"] == b]
        deltas[f"{b}-{a}"] = {
            "horn_on_axis_db_median": float(np.median(
                [x["horn_on_axis_dbc_1ms"] - y["horn_on_axis_dbc_1ms"] for x, y in zip(rb, ra)])),
            "horn_on_axis_db_max_abs": float(np.max(
                np.abs([x["horn_on_axis_dbc_1ms"] - y["horn_on_axis_dbc_1ms"] for x, y in zip(rb, ra)]))),
            "woofer_on_axis_db_median": float(np.median(
                [x["woofer_on_axis_dbc_283v"] - y["woofer_on_axis_dbc_283v"] for x, y in zip(rb, ra)])),
            "woofer_on_axis_db_max_abs": float(np.max(
                np.abs([x["woofer_on_axis_dbc_283v"] - y["woofer_on_axis_dbc_283v"] for x, y in zip(rb, ra)]))),
            "relative_phase_deg_median": float(np.median(_wrap_deg(
                np.radians([x["relative_phase_deg"] - y["relative_phase_deg"]
                            for x, y in zip(rb, ra)])))),
            "relative_phase_deg_over_freq": _wrap_deg(np.radians(
                [x["relative_phase_deg"] - y["relative_phase_deg"]
                 for x, y in zip(rb, ra)])).tolist(),
        }

    import csv
    with (out / "placement_compare.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "kind": "horn_over_cabinet_placement_compare_v1",
        "labels": {
            "on_axis_horn_dbc_1ms": "dB re 20 uPa for a 1 m/s prescribed normal velocity "
                                    "(per-excitation horn channel; NOT a calibrated SPL)",
            "on_axis_woofer_dbc_283v": "dB re 20 uPa for the 2.83 V electrical reference "
                                       "(per-excitation woofer channel)",
            "relative_phase_deg": "arg(p_horn / p_woofer) at the 2 m on-axis probe, with each "
                                  "channel at its own reference; a diagnostic, not a calibrated "
                                  "crossover phase",
            "combined_spl": "not computed: the two channels have different, uncalibrated bases",
        },
        "frequencies_hz": freqs.tolist(),
        "summary": summary,
        "deltas": deltas,
        "rows": rows,
    }
    (out / "placement_compare.json").write_text(json.dumps(payload, indent=2) + "\n",
                                                encoding="utf-8")
    _plot(out / "placement_compare.png", results, rows, freqs, summary)
    print(json.dumps({"ok": True, "out": str(out), "deltas": deltas,
                      "crossover": {k: {kk: v[kk] for kk in
                                        ("on_axis_horn_db_at_crossover",
                                         "on_axis_woofer_db_at_crossover",
                                         "relative_phase_deg_at_crossover",
                                         "horn_vertical_spread_db_at_crossover")}
                                    for k, v in summary.items()}}, indent=2))
    return 0


def _plot(path: Path, results, rows, freqs, summary) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(14.0, 9.0), dpi=130)
    colours = {"P1": "#4a4a4a", "P2": "#1f77b4", "P3": "#d62728"}

    ax = axes[0, 0]
    for label in results:
        sel = [r for r in rows if r["case"] == label]
        ax.semilogx(freqs, [r["horn_on_axis_dbc_1ms"] for r in sel], "-o", ms=3,
                    color=colours.get(label), label=label)
    ax.set_title("Horn channel, 2 m on-axis (dB re 20 uPa per 1 m/s)")
    ax.set_xlabel("frequency [Hz]"); ax.set_ylabel("dB"); ax.grid(alpha=0.3, which="both")
    ax.legend()

    ax = axes[0, 1]
    for label in results:
        sel = [r for r in rows if r["case"] == label]
        ax.semilogx(freqs, [r["woofer_on_axis_dbc_283v"] for r in sel], "-o", ms=3,
                    color=colours.get(label), label=label)
    ax.set_title("Woofer channel, 2 m on-axis (dB re 20 uPa per 2.83 V)")
    ax.set_xlabel("frequency [Hz]"); ax.set_ylabel("dB"); ax.grid(alpha=0.3, which="both")
    ax.legend()

    ax = axes[1, 0]
    # Phase change of each channel against the first case. This is the placement effect on
    # one transfer function and is free of the uncalibrated cross-channel level problem.
    reference = next(iter(results))
    ref_on = results[reference].per_excitation_bases("observation:probe:on_axis_2m")
    for label in results:
        on = results[label].per_excitation_bases("observation:probe:on_axis_2m")
        d_horn = _wrap_deg(np.angle(on["excitation:horn"][:, 0] / ref_on["excitation:horn"][:, 0]))
        d_woof = _wrap_deg(np.angle(on["vented/voltage"][:, 0] / ref_on["vented/voltage"][:, 0]))
        colour = colours.get(label)
        ax.semilogx(freqs, d_horn, "-o", ms=3, color=colour, label=f"{label} horn")
        ax.semilogx(freqs, d_woof, "--s", ms=2.5, color=colour, alpha=0.65,
                    label=f"{label} woofer")
    ax.axhline(0.0, color="k", lw=0.6)
    ax.set_title(f"Channel phase change vs {reference} at 2 m on-axis (wrapped)")
    ax.set_xlabel("frequency [Hz]"); ax.set_ylabel("deg"); ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=7, ncol=2)

    ax = axes[1, 1]
    for label in results:
        ang = summary[label]["vertical_angles_deg"]
        pol_h = np.asarray(summary[label]["horn_vertical_polar_db_1khz"])
        if ang is None:
            continue
        ax.plot(ang, pol_h - np.max(pol_h), "-", color=colours.get(label), label=f"{label} horn")
    ax.set_title("Horn channel vertical polar at the crossover sample (normalised)")
    ax.set_xlabel("vertical angle [deg]"); ax.set_ylabel("dB re own max")
    ax.set_xlim(-90, 90); ax.grid(alpha=0.3); ax.legend()

    fig.suptitle("Horn-over-cabinet placement comparison — per-excitation research "
                 "results, not a calibrated system", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
