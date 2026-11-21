"""Replay the November 20 home-900 review cohort from immutable responses on CPU."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hornlab_search.objective.replay import load_brief_context, replay_run_dir
from hornlab_search.objective.scalar_v11 import resolve_v11_weights
from hornlab_search.report.preferred_pattern import impedance_diagnostics, preferred_pattern_diagnostics
from hornlab_search.solve.cache import load_response

BRIEFS = ROOT / "examples/briefs/home_xo900_2026-11-20"
HOME = BRIEFS / "room_landscape_80x50_900_hf1440_v11cd.yaml"
STAGED = BRIEFS / "room_landscape_80x50_900_hf1440_v11cd_staged_exp.yaml"
RUNS = ROOT / "runs"
COHORT = (
    ("Crowe-X FAV-001", "4140768780f0", "20261120T084006Z-screen-fc4e18", "20261120T185832Z-verify-e5de4a"),
    ("Extended-throat OSSE H/V", "e85cdd7c61f6", "20261120T075520Z-screen-a342b2", "20261120T185416Z-verify-9d392f"),
    ("OSSE morph", "0636d3f22d5c", "20261120T074140Z-screen-a65a29", "20261120T185618Z-verify-f4c824"),
    ("OSSE fold-warm", "68001408e339", "20261120T072543Z-screen-a8074a", "20261120T185520Z-verify-fec2a6"),
    ("ATH CORE petal", "2683984c802c", "20261120T090536Z-screen-6e83a9", "20261120T185717Z-verify-7fb1b5"),
)


def file_sha(path):
    return sha256(path.read_bytes()).hexdigest()


def replay(run, design, brief, *, config=None):
    result = replay_run_dir(run, design, brief=brief, config_path=config)
    if not result.complete or result.j is None or result.terms is None:
        raise ValueError(f"{run.name}/{design}: incomplete replay {result.reasons}")
    weights = resolve_v11_weights(brief.weights, brief.objective_params)
    keys = (*brief.objective_params.weighted_keys(),
            "cd_lw", "cd_di_std", "cd_nacc", "offaxis_smooth")
    contribution = {key: weights[key] * result.terms[key] for key in keys}
    if not math.isclose(sum(contribution.values()), result.j, abs_tol=1e-10):
        raise ValueError(f"{run.name}/{design}: score does not reconcile to weighted terms")
    return {"j": result.j, "weighted": contribution, "terms": result.terms,
            "score_id": result.score_id, "physical_id": result.physical_id}


def response_summary(run, design):
    path = run / "designs" / design / "response.npz"
    response = load_response(path)
    if response is None:
        raise FileNotFoundError(path)
    f = np.asarray(response.freqs_hz)
    z = np.asarray(response.z_throat, dtype=complex)
    if z.shape != f.shape:
        raise ValueError(f"{path}: expected a stored impedance value at each frequency")
    band = (f >= 900) & (f <= 2500)
    resistance = z.real[band]
    resistance = resistance[np.isfinite(resistance)]
    p95 = float(np.quantile(resistance, 0.95)) if len(resistance) >= 3 else None
    skirt = np.flatnonzero((f >= 650) & (f <= 2500) & np.isfinite(z.real))
    peak = None
    if len(skirt):
        i = skirt[np.argmax(z.real[skirt])]
        peak = {"frequency_hz": float(f[i]), "resistance": float(z.real[i])}
    return {
        "response_sha256": file_sha(path),
        "frequency_hz": f.tolist(),
        "pattern": preferred_pattern_diagnostics(response),
        "impedance": impedance_diagnostics(response, band_hz=(900., 2500.)),
        "near_xo_resistance_p95": p95,
        "filter_skirt_resistance_peak": peak,
        "impedance_trace": {
            name: [float(v) if np.isfinite(v) else None for v in values]
            for name, values in (("resistance", z.real), ("reactance", z.imag))
        },
    }


def audit():
    home, staged = load_brief_context(HOME), load_brief_context(STAGED)
    rows = []
    for label, design, screen_id, verify_id in COHORT:
        verify, screen = RUNS / verify_id, RUNS / screen_id
        base = replay(verify, design, home)
        coarse = replay(screen, design, home)
        measured = response_summary(verify, design)
        p95 = measured["near_xo_resistance_p95"]
        peak = measured["filter_skirt_resistance_peak"]
        robustness = {
            "load_weight_zero": base["j"] - base["weighted"]["load"],
            "add_upper_resistance_penalty": None if p95 is None else
                base["j"] + max(0.0, p95 - 1.5) / 0.3,
            "add_filter_skirt_peak_penalty": None if peak is None else
                base["j"] + max(0.0, peak["resistance"] - 1.5) / 0.3,
        }
        rows.append({"label": label, "design": design, "screen_run": screen_id, "verify_run": verify_id,
                     "home_verify": base, "home_screen": coarse, "staged_verify": replay(verify, design, staged),
                     "screen_to_verify_delta": base["j"] - coarse["j"],
                     "report_only_score_sensitivity": robustness, **measured})

    k_run = RUNS / "20261120T202339Z-screen-e4b845"
    ref_run = RUNS / "20261117T053153Z-screen-15f0e4"
    controls = []
    for label, design, run in (("Crowe k-home verify", "cd7e60025f70", k_run),
                               ("R-OSSE R0 verify", "823dc1721a76", ref_run)):
        controls.append({"label": label, "design": design, "run": run.name,
                         "home_verify": replay(run / "verify", design, home, config=run / "config.yaml"),
                         **response_summary(run / "verify", design)})
    return {"engine": "saved-response CPU replay", "briefs": {
                brief.name: {"path": path.relative_to(ROOT).as_posix(), "sha256": file_sha(path)}
                for brief, path in ((home, HOME), (staged, STAGED))},
            "loading_sensitivity_definition": {
                "load_weight_zero": "subtract the production load contribution",
                "add_upper_resistance_penalty":
                    "add max(0,p95(Re z / rho c) - 1.5) / 0.3 on stored 900-2500 Hz bins. "
                    "Exploratory influence check with a provisional threshold.",
                "add_filter_skirt_peak_penalty":
                    "add max(0,max(Re z / rho c) - 1.5) / 0.3 on stored 650-2500 Hz bins. "
                    "Deliberate stress test using unfiltered samples. Threshold is provisional."
            }, "cohort": rows, "auxiliary": controls}


def plot_diagnostics(stats, destination):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import NullFormatter

    rows = stats["cohort"][:2] + stats["auxiliary"]
    labels = ("FAV-001", "Extended-throat OSSE", "k-home verify", "R-OSSE R0")
    colors = ("#214f91", "#1b7b62", "#b45128", "#8e4f95")
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 7.4), layout="constrained")
    fig.suptitle("Home 900 Hz review   |   Stored verify samples",
                 fontsize=20, fontweight="bold", color="#142835")
    for row, color in zip(rows, colors):
        f = row["frequency_hz"]
        for axis, plane in zip(axes[0], ("h", "v")):
            axis.plot(f, row["pattern"]["planes"][plane]["width_deg"], ".-", ms=4, lw=1.25, color=color)
        for axis, term in zip(axes[1], ("resistance", "reactance")):
            axis.plot(f, row["impedance_trace"][term], ".-", ms=4, lw=1.25, color=color)
    titles = ("Horizontal beamwidth", "Vertical beamwidth", "Throat resistance", "Throat reactance")
    for i, (axis, title) in enumerate(zip(axes.flat, titles)):
        axis.set_title(title, loc="left", fontweight="bold")
        axis.axvline(900, color="#66676a", lw=1, ls=":")
        axis.set_xscale("log")
        axis.xaxis.set_minor_formatter(NullFormatter())
        axis.set_xlim(600, 8200 if i < 2 else 3100)
        axis.set_xlabel("Frequency (Hz)")
        axis.grid(alpha=.2)
        ticks = [600, 900, 1200, 1500, 2200, 3000] + ([5000, 8000] if i < 2 else [])
        axis.set_xticks(ticks, labels=[str(t) for t in ticks])
        if i < 2:
            left, lo, hi, pref = (900, 60, 90, 80) if i == 0 else (1000, 40, 60, 50)
            axis.fill_between([left, 8000], lo, hi, color="#7898da", alpha=.12)
            axis.hlines(pref, left, 8000, color="#505e78", linestyles="--", lw=.8)
            axis.set_ylim((50, 100) if i == 0 else (35, 115))
            axis.set_ylabel("Boresight-connected −6 dB width (°)")
        else:
            axis.set_ylabel("Normalized by ρc")
    axes[1, 0].axhline(.7, color="#505e78", linestyle="--", lw=.8)
    fig.legend(handles=[Line2D([0], [0], color=c, lw=2, label=l) for l, c in zip(labels, colors)],
               loc="outside lower center", ncol=4, frameon=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--plot", type=Path, help="write the comparative diagnostic PNG")
    args = parser.parse_args()
    stats = audit()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(stats, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if args.plot:
        plot_diagnostics(stats, args.plot)
    for row in stats["cohort"]:
        print(f'{row["design"]} home900={row["home_verify"]["j"]:.6f} '
              f'staged={row["staged_verify"]["j"]:.6f} '
              f'delta_verify_minus_screen={row["screen_to_verify_delta"]:+.6f}')
    for row in stats["auxiliary"]:
        print(f'{row["design"]} supplemental_home900={row["home_verify"]["j"]:.6f}')


if __name__ == "__main__":
    main()
