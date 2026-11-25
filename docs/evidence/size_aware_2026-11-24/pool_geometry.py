"""Same Sobol draws under three candidate regions, with no solve or GP fit."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import time

from hornlab_search.bo import ActiveProjection, build_candidate_pool
from hornlab_search.config import envelope_policy, load_config
from hornlab_search.design.space import DesignSpace

HOME_FOLD = Path("runs/20261123T204853Z-screen-fe8efb/config.yaml")


def main() -> None:
    original = load_config(HOME_FOLD)
    outputs = {}
    for label, limits in (
        ("production", {"enforce": True}),
        ("exploration_105", {"enforce": False, "max_utilization": 1.05}),
        ("exploration_125", {"enforce": False, "max_utilization": 1.25}),
        ("discovery", {"enforce": False}),
    ):
        config = replace(original, brief={**original.brief,
                                         "envelope": {**original.brief["envelope"], **limits}})
        space = DesignSpace.from_config(config)
        encoding = ActiveProjection.from_space(space)
        started = time.perf_counter()
        pool = build_candidate_pool(space, encoding, config, n=128, seed=4101, max_extra_seeds=0)
        policy = envelope_policy(config.brief)
        ratios = [
            max(float(candidate.descriptors[f"envelope_{axis}_mm"]) / limit
                for axis, limit in zip(("width", "height", "depth"), policy.product_limits_mm))
            for candidate in pool.candidates
        ]
        outputs[label] = {
            "policy": policy.as_dict(), "counts": pool.counts, "status": pool.status,
            "accepted_max_utilization": max(ratios, default=None),
            "in_final_five_percent_of_product_use": sum(0.95 <= r <= 1.0 for r in ratios),
            "elapsed_seconds": time.perf_counter() - started,
        }
    result = {"config": HOME_FOLD.as_posix(), "seed": 4101, "draws_per_arm": 128,
              "estimated_surface": "formula_inner", "arms": outputs}
    Path(__file__).with_name("pool_geometry.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
