"""``study_cohort`` must select over the whole compatible corpus, not ``selected[:limit]``.

Synthetic, offline, no solver: a tiny v10 dataset whose best stored-J row is *last* and a small
``--limit`` prove the row is not discarded by dataset position.  The metric-aware selector is
exercised through the real ``prepare`` path (config/space/projection/replay are production code).
"""
from __future__ import annotations

import dataclasses
import json

import numpy as np

from conftest import REPO, make_fake_response
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.metrics.compute import compute_metrics
from hornlab_search.objective import replay
from tools.analysis.study_cohort import prepare

CONFIG = (REPO / "examples/typologies/b6_2026-11-19"
          / "hl__osse_rrect_morph_v7__b6_v10_s1.yaml")


def _write_dataset(tmp_path):
    cfg = load_config(CONFIG)
    space = DesignSpace.from_config(cfg)
    brief = replay.brief_from_config(CONFIG)
    response = make_fake_response()
    metrics = compute_metrics(response, brief.target)
    arrays = replay._arrays_from_response(response)
    arrays.update({k: np.asarray(getattr(metrics, k)) for k in
                   ("bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db", "ripple_v_db",
                    "on_axis_db")})

    dataset = tmp_path / "dataset"
    (dataset / "shard-0000").mkdir(parents=True)
    # The last row carries the best (lowest) stored J.
    stored_j = [10.0, 20.0, -5.0]
    designs = []
    lines = []
    n_keys = len(space.keys())
    for i, j in enumerate(stored_j):
        design = space.denormalize(np.full(n_keys, (i + 1) / (len(stored_j) + 1)))
        designs.append(design)
        meta = {
            "ok": True, "design_hash": design.hash(), "mesh_hash": "mesh", "solve_hash": "solve",
            "objective_version": cfg.objective_version, "objective": j, "terms": {},
            "metrics_scalars": {}, "target": dataclasses.asdict(brief.target),
            "config_name": cfg.name, "run_id": "run", "family": design.family,
            "params": design.params,
            "provenance": {"config": cfg.name, "brief_hash": "brief"},
            "solve": {"mode": "screen", "backend": cfg.solve.backend,
                      "freqs_hz": [500.0, 8000.0]},
            "lib_shas": {"hornlab_beat_bem": "a"},
        }
        lines.append(json.dumps(meta) + "\n")
        np.savez(dataset / "shard-0000" / f"rec-{i:04d}.npz", **arrays)
    (dataset / "shard-0000.jsonl").write_text("".join(lines), encoding="utf-8")
    return cfg, dataset, designs


def test_study_cohort_selects_best_last_row_before_limit(tmp_path):
    cfg, dataset, designs = _write_dataset(tmp_path)
    result = prepare(CONFIG, dataset, tmp_path / "out", limit=1)

    # ``limit`` is a training cap, not a raw-discovery cap: the best stored-J row is last in the
    # file yet is the one replayed.
    assert result["counts"] == {"exact_complete": 1}
    scores = json.loads((tmp_path / "out/offline_scores.json").read_text())
    assert len(scores["rows"]) == 1
    assert scores["rows"][0]["design_hash"] == designs[2].hash()

    selection = scores["selection"]
    assert selection["available"] == 3
    assert selection["limit"] == 1
    assert selection["metric_selection"]["status"] == "needs_initial_data"
    assert len(selection["selected_ids"]) == 1
    assert len(selection["excluded_ids"]) == 2
    reasons = {item["reasons"][0] for item in selection["excluded_reasons"]}
    assert reasons == {"not_selected:n_max_cap"}
    assert set(selection["excluded"]) == {"other_dependency_grid_brief_groups"}


def test_study_cohort_without_limit_still_ranks_the_whole_group(tmp_path):
    _cfg, dataset, designs = _write_dataset(tmp_path)
    result = prepare(CONFIG, dataset, tmp_path / "out", limit=256)
    # Below n_min the selector still publishes the lowest-J compatible observations (capped at
    # n_max), so all three rows are replayed and no positional slicing happened.
    assert result["counts"] == {"exact_complete": 3}
    scores = json.loads((tmp_path / "out/offline_scores.json").read_text())
    assert {row["design_hash"] for row in scores["rows"]} == {d.hash() for d in designs}
    selected = scores["selection"]["selected_ids"]
    assert len(selected) == 3 and len(set(selected)) == 3
