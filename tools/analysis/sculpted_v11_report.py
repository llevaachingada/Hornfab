"""Report matching measured home-900 V11 fixed-mesh BEM responses."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hornlab_search.objective.replay import load_brief_context
from hornlab_search.objective.scalar_v11 import resolve_v11_weights
from hornlab_search.report.preferred_pattern import preferred_pattern_diagnostics, impedance_diagnostics
from hornlab_search.solve.cache import load_response

NIGHT = ROOT / "runs/nights/hornfab_gpu8_2026-11-21"
DEST = ROOT / "docs/evidence/sculpted_xo900_v11_2026-11-21"
BRIEF = ROOT / "examples/briefs/home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd.yaml"
CASES = ("R2_6", "R3_6", "K1_6", "K2_6", "R2_7", "R3_7", "K1_8", "K2_8", "FAV", "k-home", "ext-OSSE")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-run", type=Path, help="register the measured R2 native truncation probe in this report")
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    brief = load_brief_context(BRIEF)
    weights = resolve_v11_weights(brief.weights, brief.objective_params)
    keys = (*brief.objective_params.weighted_keys(), "cd_lw", "cd_di_std", "cd_nacc", "offaxis_smooth")
    brief_sha = hashlib.sha256(BRIEF.read_bytes()).hexdigest()
    rows, responses = {}, {}
    fig, axes = plt.subplots(3, 1, figsize=(10, 12), constrained_layout=True)
    names = CASES + (("R2_tmax_0.96",) if args.native_run else ())
    for name in names:
        if name == "R2_tmax_0.96":
            best = json.loads((args.native_run / "best.json").read_text(encoding="utf-8"))
            path = args.native_run / "designs" / best["design_hash"]
            record = json.loads((path / "fixed_mesh_provenance.json").read_text(encoding="utf-8"))
            if record["case"] != name or record["origin"] != "new GPU solve":
                raise ValueError("Expected measured R2 native probe")
            source_model = {"mounting": record["mounting"], "quarter": record["symmetry"] == "yz+xz",
                            "radius_mm": record["driver"]["exit_radius_mm"], "cap": record["source"]["cap"],
                            "nominal_exit_deg": record["driver"]["exit_angle_deg"]}
            result = dict(record, J=best["objective"], terms=best["terms"], epw=record["mesh_spec"]["epw"],
                          mesh_sha256=record["geometry"]["mesh_sha256"], lib_shas=record["libs"],
                          source_model=source_model,
                          experiment_id=record["geometry"]["experiment_id"])
        else:
            path = NIGHT / "fixed" / name
            result = json.loads((path / "result.json").read_text(encoding="utf-8"))
        if result["brief_sha256"] != brief_sha or result["solve_hash"] != "62842a4a021e":
            raise ValueError(f"{name} has an incompatible acoustic identity")
        response = load_response(path / "response.npz")
        if response.spl_balloon_db is None or response.balloon_dirs is None or result["terms"]["cd_status_code"] != 0:
            raise ValueError(f"{name} lacks valid CD balloon metrics")
        contributions = {k: weights[k] * result["terms"][k] for k in keys}
        if not math.isclose(sum(contributions.values()), result["J"], abs_tol=1e-9):
            raise ValueError(f"{name} weighted sum mismatch")
        pattern = preferred_pattern_diagnostics(response)
        freqs = np.asarray(response.freqs_hz)
        cuts = {}
        for nominal in (900, 1200, 1500, 2000, 4000, 8000):
            i = int(np.argmin(abs(freqs - nominal)))
            cuts[str(nominal)] = {
                "solved_hz": float(freqs[i]),
                "h_width_deg": pattern["planes"]["h"]["width_deg"][i],
                "v_width_deg": pattern["planes"]["v"]["width_deg"][i],
                "relative_cuts_db": {
                    plane: {str(angle): float(spl[i, np.argmin(abs(angles-angle))] - spl[i, np.argmin(abs(angles))])
                            for angle in (30, 45)}
                    for plane, spl, angles in (("h", response.spl_h_db, response.h_angles_deg),
                                               ("v", response.spl_v_db, response.v_angles_deg))}}
        rows[name] = {"J": result["J"], "weighted_terms": contributions, "raw_terms": result["terms"],
                      "brief_sha256": brief_sha, "solve_hash": result["solve_hash"], "epw": result["epw"],
                      "mesh_sha256": result["mesh_sha256"], "source_model": result["source_model"],
                      "experiment_id": result["experiment_id"], "lib_shas": result["lib_shas"],
                      "full_balloon": True, "pattern": pattern, "selected_frequencies": cuts,
                      "impedance": impedance_diagnostics(response), "complex_pressure": {
                          k: getattr(response, k) is not None for k in ("p_h", "p_v", "p_balloon")},
                      "mouth_pressure": "not retained by this fixed-mesh route",
                      "response_path": str(path / "response.npz")}
        responses[name] = response
        if name in ("R2_6", "R3_6", "K1_6", "K2_6", "R2_tmax_0.96"):
            for plane, ax in (("h", axes[0]), ("v", axes[1])):
                y = np.array([v if v is not None else np.nan for v in pattern["planes"][plane]["width_deg"]])
                ax.semilogx(freqs, y, label=name)
            axes[2].semilogx(freqs, np.real(response.z_throat), label=name)
    for ax, title in zip(axes, ("Horizontal -6 dB width (degrees)", "Vertical -6 dB width (degrees)", "Normalized throat resistance")):
        ax.set_title(title)
        ax.set_xlabel("Frequency (Hz)")
        ax.grid(True, which="both", alpha=.25)
        ax.legend()
    fig.savefig(DEST / "patterns_impedance.png", dpi=160)
    plt.close(fig)
    pairs = {}
    for pair in ("R2_6__R3_6", "R2_7__R3_7", "K1_6__K2_6", "K1_8__K2_8"):
        pairs[pair] = json.loads((NIGHT / "pairs" / pair / "summary.json").read_text(encoding="utf-8"))
    if args.native_run:
        control, probe = rows["R2_6"], rows["R2_tmax_0.96"]
        a, b = responses["R2_6"], responses["R2_tmax_0.96"]
        if control["source_model"] != probe["source_model"]:
            raise ValueError("Native R2 pair differs in source model")
        for axis in ("freqs_hz", "h_angles_deg", "v_angles_deg", "balloon_dirs"):
            if not np.array_equal(getattr(a, axis), getattr(b, axis)):
                raise ValueError(f"Native R2 pair differs in {axis}")
        pairs["R2_native_truncation"] = {
            "delta_j": probe["J"] - control["J"],
            "weighted_delta": {k: probe["weighted_terms"][k] - control["weighted_terms"][k] for k in keys},
            "balloon_rms_offset_db": float(np.sqrt(np.mean((b.spl_balloon_db - a.spl_balloon_db)**2))),
            "source_drift_mm": record["geometry"]["source_drift_mm"],
            "source_connectivity_equal": record["geometry"]["source_connectivity_equal"],
            "interpretation": "Native truncation also refits the body. Single matched mesh tier.",
        }
    report = {"scope": "Home 900 Hz V11, fixed 51-frequency observation grid, 36 mm source, freestanding quarter model",
              "excluded": "v7/v10 and 700 Hz or compact-brief results are excluded",
              "cases": rows, "matched_pairs": pairs,
              "sampling_limit": "6 to 7 or 8 epw changes mesh and source discretization. This single refinement comparison does not establish a general numerical floor."}
    (DEST / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    lines = ["# Sculpted home-900 V11 BEM readout", "", report["scope"], "",
             "| Case | epw | J | H RMS error | V RMS error | CD method |",
             "|---|---:|---:|---:|---:|---|"]
    for name, row in rows.items():
        p = row["pattern"]["planes"]
        lines.append(f"| {name} | {row['epw']} | {row['J']:.4f} | {p['h']['rms_error_deg']:.2f} | {p['v']['rms_error_deg']:.2f} | full balloon |")
    lines += ["", "R2/R3 and K1/K2 comparisons use the same frequency and observation grid. "
              "K2 changes both finishing and the projected mouth, so the pair assesses the complete finish.",
              "", report["sampling_limit"], "",
              "The JSON includes all weighted score terms, actual solved bins, preferred-pattern errors, "
              "30/45-degree H/V cuts, lobe checks, complex-impedance components and source identity. "
              "Complex far-field pressure is reported where stored. Mouth pressure was not captured.",
              "", "B3 v7 and Crowe 700 Hz v11 experiments have different identities and are excluded.",
              "", "![Width and impedance](patterns_impedance.png)"]
    (DEST / "measurements.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} cases to {DEST}")


if __name__ == "__main__":
    main()

