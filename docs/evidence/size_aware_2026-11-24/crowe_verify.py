"""Read the three matched Compact500 verify results. Run from HornFab's root."""
from __future__ import annotations

import json
from pathlib import Path

from hornlab_search.search.evaluate import read_ndjson

NIGHT = "size_aware_crowe_verify_2026-11-24"
SCREEN_RUN = "20261122T223153Z-screen-98b41d"
EXPECTED = {"product": "fbaa37e52eb9", "epsilon_125": "7d0caa63b55c",
            "discovery": "138f09ce5472"}


def main() -> None:
    summaries = read_ndjson(Path("runs/nights") / NIGHT / "summary.jsonl")
    by_id = {row["id"]: row for row in summaries}
    archived = read_ndjson(Path("runs") / NIGHT / "dataset" / "shard-0000.jsonl")
    records = {row["design_hash"]: row for row in archived}
    source = json.loads((Path("runs") / SCREEN_RUN / "run.json").read_text(encoding="utf-8"))
    config = source["config"]
    result = {}
    identity = None
    for label, design in EXPECTED.items():
        job = by_id[f"crowe_{label}"]
        directory = Path(job["run_dir"])
        row, = read_ndjson(directory / "search.ndjson")
        if not row["ok"] or row["mode"] != "verify" or row["design_hash"] != design:
            raise ValueError(f"{label} did not verify the expected design {design}")
        metrics = row["metrics"]
        record = records[design]
        observed_identity = {
            "backend": record["solve"]["backend"], "lib_shas": record["lib_shas"],
            "brief": config["brief"], "target": config["target"], "weights": config["weights"],
            "brief_hash": record["provenance"]["brief_hash"],
            "mesh": config["mesh"], "solve": config["solve"],
            "res_mm": row["res_mm"], "objective_version": row["objective_version"],
            "solve_hash": row["solve_hash"], "freqs_hz": metrics["freqs_hz"],
            "di_source": metrics["di_source"],
        }
        if identity is None:
            identity = observed_identity
        elif identity != observed_identity:
            changed = [key for key in identity if identity[key] != observed_identity[key]]
            raise ValueError(f"{label} has a different verify identity: {changed}")
        size = row["size_feasibility"]
        result[label] = {
            "verify_run": str(directory.relative_to(Path.cwd())), "design_hash": design,
            "verify_j": row["objective"],
            "whd_mm": [size[k] for k in ("width_mm", "height_mm", "depth_mm")],
            "utilization": size["max_utilization"], "product_fit": size["product_fit"],
            "terminal_rim": size["mouth_aperture"], "policy_id": size["policy_id"],
            "n_dof": row["n_dof"], "solve_seconds": row["seconds"]["solve"],
            "wall_seconds": job["seconds"], "vram_baseline_mib": job["vram_baseline_mb"],
            "vram_after_mib": job["vram_after_mb"], "status": job["status"],
        }
    output = {"screen_run": SCREEN_RUN, "verify_identity": identity, "finalists": result}
    Path(__file__).with_name("crowe_verify.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
