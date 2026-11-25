"""Historical observations and current candidate limits are independent."""
import copy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from conftest import REPO
from hornlab_search.bo import data, fit_model, propose_one
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.types import Design


def test_rolled_observation_outside_product_box_is_retained(tmp_path, monkeypatch):
    path = REPO / "examples/typologies/rolled_family_2026-11-15/rf__rect_radial_v7.yaml"
    cfg = load_config(path)
    design = DesignSpace.from_config(cfg).seed
    mat = data.materialize_geometry(design, cfg)
    cfg = copy.deepcopy(cfg)
    cfg.brief["envelope"].update(max_mouth_w_mm=1.0, max_mouth_h_mm=1.0,
                                 max_depth_mm=1.0, enforce=True)
    monkeypatch.setattr("hornlab_search.config.load_config", lambda _: cfg)
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    meta = {"ok": True, "family": design.family, "params": design.params,
            "design_hash": design.hash(), "solve_hash": "solve"}
    (dataset / "shard-0000.jsonl").write_text(json.dumps(meta), encoding="utf-8")
    row = {"shard": 0, "row": 0, "config_name": cfg.name, "status": "exact_complete",
           "complete": True, "j": 2.5, "physical_id": "p", "metric_id": "m",
           "score_id": "s", "design_hash": design.hash(), "objective_version": 7,
           "metric_source": "stored", "diagnostics": {"ripple_used_response": True},
           "target": {"x": 1}, "weights": {"x": 1}}
    scores = tmp_path / "scores.json"
    scores.write_text(json.dumps({"cohort": {"native_config": cfg.name},
                                  "brief": {"objective_version": 7}, "rows": [row]}),
                      encoding="utf-8")
    catalog = tmp_path / "catalog.csv"
    catalog.write_text("root,shard_index,row,config_name,objective_version,backend,brief_hash,dependency_hash,task_identity,fidelity,grid_hash\n"
                       f"dataset,0,0,{cfg.name},7,beat_cuda,b1,d1,t1,screen,g1\n", encoding="utf-8")
    training = data.build_native_training_set(path, scores_json=scores, catalog_csv=catalog,
                                               dataset_root=dataset)
    assert training.meta["n_observations"] == 1, training.meta
    assert training.meta["outside_product_envelope_ids"] == ["p"]
    assert training.meta["identities"]["p"]["product_envelope_eligible"] is False
    assert training.meta["identities"]["p"]["J"] == 2.5
    assert not data.geometry_checks(mat, cfg, design.params)[1]


def test_fixed_pool_gp_keeps_oversized_observations_and_selects_near_boundary(monkeypatch):
    pytest.importorskip("botorch")
    space = SimpleNamespace(denormalize=lambda vector: Design("OSSE", {"x": float(vector[0])}))
    encoding = SimpleNamespace(d=1, space=space, to_full=lambda vector: vector)

    def analytic_surface(design, _config, *, resolution_mm):
        radius = 200.0 + 100.0 * design.params["x"]
        return {"formula": "synthetic-boundary", "inner_points": np.array([
            [[18, 0, 0], [radius, 0, 200]], [[0, 18, 0], [0, 150, 200]],
            [[-18, 0, 0], [-radius, 0, 200]], [[0, -18, 0], [0, -150, 200]],
        ])}

    monkeypatch.setattr(data, "materialize_geometry", analytic_surface)
    monkeypatch.setattr(data, "canonical_design", lambda design, *_args, **_kw: design)
    monkeypatch.setattr(data, "intended_solve_identity", lambda _cfg: "synthetic-solve")
    monkeypatch.setattr("hornlab_search.design.families.validate", lambda _design: None)

    # The analytic optimum sits beyond both admissible regions, so the best
    # admissible point is on each region's upper boundary.
    observations = [data.TrainingObservation(
        str(i), np.array([x]), J=float((x - 0.8) ** 2), geometry_hash=f"observed-{i}")
        for i, x in enumerate(np.linspace(0.01, 0.99, 24))]
    training = data.build_training_set(observations, d=1)
    assert training.n == 24
    assert training.X.min() < 0.5 < training.X.max()
    fit = fit_model(training, seed=0)
    assert fit.status == "ok", fit.reason

    dims = {"max_mouth_w_mm": 500, "max_mouth_h_mm": 500, "max_depth_mm": 500}
    for envelope, target_x in ((dims, 0.5), ({**dims, "enforce": False, "max_utilization": 1.05}, 0.625)):
        cfg = SimpleNamespace(brief={"envelope": envelope})
        pool = data.build_candidate_pool(space, encoding, cfg, n=256, seed=17)
        assert pool.status == "ok"
        assert all(row.active_vector[0] <= target_x + 0.0025 for row in pool.candidates)
        proposal = propose_one(fit, pool, encoding=encoding, config=cfg)
        assert proposal.status == "ok", proposal.reason
        chosen = next(row for row in pool.candidates if row.candidate_id == proposal.candidate_id)
        assert target_x - 0.05 <= chosen.active_vector[0] <= target_x + 0.0025
