"""Strict cohort-policy enforcement in ``bo.data.build_native_training_set`` (M2 gate audit).

The real native builder is the path the study builders and M2 diagnostics use, so it must
refuse the same shared-policy disagreements ``bo.cohort.validate_cohort`` refuses instead of
silently pooling them. Offline fixtures only: no mesh, solve or live dataset access.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from hornlab_search.bo.data import (NATIVE_POLICY_FIELDS, NATIVE_REFUSAL_REASONS,
                                    build_native_training_set)

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml"
CATALOG_HEADER = ("root,shard_index,row,config_name,objective_version,backend,brief_hash,"
                  "dependency_hash,task_identity,fidelity,grid_hash\n")
TARGET = {"band_lo_hz": 300.0, "band_hi_hz": 8000.0, "coverage_h_deg": 50.0}
WEIGHTS = {"cov": 1.0, "rip": 1.0}


def _seed_params():
    raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    return dict(raw["seed_params"])


def _write(tmp_path, n=3, *, score_overrides=None, catalog_overrides=None):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    base = _seed_params()
    lines, catalog, rows = [], [CATALOG_HEADER], []
    for i in range(n):
        params = dict(base)
        params["L_mm"] = float(base["L_mm"]) + 10.0 * i
        lines.append(json.dumps({"ok": True, "family": "OSSE", "params": params,
                                 "solve_hash": "s" if i else "s"}))
        cat = {"objective_version": "4", "backend": "beat_cuda", "brief_hash": "b1",
               "dependency_hash": "d1", "task_identity": "t1", "fidelity": "screen",
               "grid_hash": "g1"}
        cat.update((catalog_overrides or {}).get(i, {}))
        catalog.append(f"dataset,0,{i},native__ath_core_v4,{cat['objective_version']},"
                       f"{cat['backend']},{cat['brief_hash']},{cat['dependency_hash']},"
                       f"{cat['task_identity']},{cat['fidelity']},{cat['grid_hash']}\n")
        row = {"shard": 0, "row": i, "config_name": "native__ath_core_v4",
               "status": "exact_complete", "complete": True, "j": 2.0 + i,
               "physical_id": f"p{i}", "metric_id": f"m{i}", "score_id": f"s{i}",
               "objective_version": 4, "metric_source": "stored",
               "diagnostics": {"ripple_used_response": True},
               "target": dict(TARGET), "weights": dict(WEIGHTS)}
        row.update((score_overrides or {}).get(i, {}))
        rows.append(row)
    (dataset / "shard-0000.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (tmp_path / "catalog.csv").write_text("".join(catalog), encoding="utf-8")
    (tmp_path / "scores.json").write_text(json.dumps({
        "cohort": {"native_config": "native__ath_core_v4"},
        "brief": {"objective_version": 4}, "rows": rows}), encoding="utf-8")
    return dataset


def _build(tmp_path, **kwargs):
    return build_native_training_set(CONFIG, scores_json=tmp_path / "scores.json",
                                     catalog_csv=tmp_path / "catalog.csv",
                                     dataset_root=tmp_path / "dataset", **kwargs)


def test_homogeneous_policy_is_reported_ok(tmp_path):
    _write(tmp_path)
    ts = _build(tmp_path)
    policy = ts.meta["cohort_policy"]
    assert policy["status"] == "ok"
    assert policy["conflicts"] == [] and policy["missing"] == []
    assert ts.meta["n_observations"] == 3
    # Too few rows for a GP is still the ordinary data-sufficiency status.
    assert ts.status == "needs_initial_data"


def test_wrong_objective_version_and_missing_ripple_evidence_are_refused(tmp_path):
    _write(tmp_path, score_overrides={
        0: {"objective_version": 3},
        1: {"diagnostics": {"ripple_used_response": False}},
    })
    ts = _build(tmp_path)
    reasons = {r["id"]: r["reasons"] for r in ts.meta["refused"]}
    assert reasons == {"p0": ["objective_version_mismatch"],
                       "p1": ["metric_policy_unsupported"]}
    assert set(ts.meta["refusal_reasons"]) <= set(NATIVE_REFUSAL_REASONS)
    assert ts.meta["n_observations"] == 1


def test_catalog_version_disagreeing_with_brief_is_refused(tmp_path):
    _write(tmp_path, catalog_overrides={2: {"objective_version": "7"}})
    ts = _build(tmp_path)
    assert ts.meta["refusal_reasons"] == {"objective_version_mismatch": 1}


def test_policy_conflict_refuses_the_whole_cohort(tmp_path):
    _write(tmp_path, catalog_overrides={1: {"dependency_hash": "d2"}})
    ts = _build(tmp_path)
    assert ts.status == "incompatible_cohort"
    assert ts.meta["cohort_policy"]["conflicts"] == ["dependency_hash"]


def test_target_or_weight_disagreement_refuses(tmp_path):
    _write(tmp_path, score_overrides={2: {"weights": {"cov": 2.0, "rip": 1.0}}})
    ts = _build(tmp_path)
    assert ts.status == "incompatible_cohort"
    assert ts.meta["cohort_policy"]["conflicts"] == ["weights"]


def test_missing_policy_value_is_capability_missing(tmp_path):
    _write(tmp_path, catalog_overrides={0: {"backend": ""}})
    ts = _build(tmp_path)
    assert ts.status == "capability_missing"
    assert ts.meta["cohort_policy"]["missing"] == ["backend"]


def test_mixed_fidelity_is_declared_or_refused_on_request(tmp_path):
    _write(tmp_path, catalog_overrides={2: {"fidelity": "verify", "grid_hash": "g2"}})
    declared = _build(tmp_path)
    policy = declared.meta["cohort_policy"]
    assert policy["status"] == "ok_mixed_fidelity_declared"
    assert policy["mixed_fidelity_fields"] == ["fidelity", "grid_hash"]
    assert declared.status == "needs_initial_data"
    strict = _build(tmp_path, require_single_fidelity=True)
    assert strict.status == "incompatible_cohort"
    assert strict.meta["cohort_policy"]["status"] == "incompatible"


def test_policy_fields_cover_the_strict_gate_identity():
    assert {"backend", "dependency_hash", "objective_version", "target",
            "weights", "metric_source"} <= set(NATIVE_POLICY_FIELDS)


def test_home_space_without_morph_exponent_uses_identity_projection(tmp_path):
    """The home v7 task has six knobs and no ``morph_exponent``; the builder must not
    require the native no-op, and an empty replay stays the ordinary needs-initial-data."""
    home_config = (REPO / "examples/typologies/print_80x60_2026-11-13"
                   / "p80x60__osse_ext_throat_700_v7.yaml")
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    catalog = tmp_path / "catalog.csv"
    catalog.write_text(CATALOG_HEADER, encoding="utf-8")
    scores = tmp_path / "scores.json"
    scores.write_text(json.dumps({"cohort": {}, "brief": {"objective_version": 7},
                                  "rows": []}), encoding="utf-8")
    ts = build_native_training_set(home_config, scores_json=scores, catalog_csv=catalog,
                                   dataset_root=dataset)
    assert ts.d == 6
    assert ts.status == "needs_initial_data"
    assert ts.n == 0 and ts.n_min == 16


def test_home_historical_derived_throat_roundtrips_through_production_rules(tmp_path):
    import numpy as np
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.bo.data import canonical_design
    config = REPO / "examples/typologies/print_80x60_2026-11-13/p80x60__osse_ext_throat_700_v7_seed5678.yaml"
    cfg = load_config(config)
    space = DesignSpace.from_config(cfg)
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    metas, scores, catalog = [], [], [CATALOG_HEADER]
    for i in range(16):
        design = canonical_design(space.denormalize(np.full(len(space.keys()), (i + 1) / 18)),
                                  cfg, space=space)
        assert design.params["r0_mm"] != space.seed.params["r0_mm"]
        metas.append({"ok": True, "family": design.family, "params": design.params,
                      "design_hash": design.hash(), "solve_hash": "screen-spec"})
        scores.append({"shard": 0, "row": i, "config_name": cfg.name,
                       "status": "exact_complete", "complete": True, "j": i + 0.5,
                       "physical_id": f"p{i}", "metric_id": f"m{i}", "score_id": f"s{i}",
                       "design_hash": design.hash(), "objective_version": 7,
                       "metric_source": "stored", "diagnostics": {"ripple_used_response": True},
                       "target": TARGET, "weights": WEIGHTS})
        catalog.append(f"dataset,0,{i},{cfg.name},7,beat_cuda,b1,d1,t1,screen,g1\n")
    (dataset / "shard-0000.jsonl").write_text("\n".join(map(json.dumps, metas)), encoding="utf-8")
    (tmp_path / "catalog.csv").write_text("".join(catalog), encoding="utf-8")
    (tmp_path / "scores.json").write_text(json.dumps({"cohort": {"native_config": cfg.name},
        "brief": {"objective_version": 7}, "rows": scores}), encoding="utf-8")
    training = build_native_training_set(config, scores_json=tmp_path / "scores.json",
        catalog_csv=tmp_path / "catalog.csv", dataset_root=dataset, require_single_fidelity=True)
    assert training.status == "ok", training.meta
    assert training.n == 16 and training.meta["n_refused"] == 0


def test_home_pool_uses_same_canonical_design_as_actual_evaluation(monkeypatch):
    import numpy as np
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.bo.encoding import ActiveProjection
    from hornlab_search.bo import data
    from hornlab_search.bo.propose import validate_selected_candidate
    cfg = load_config(REPO / "examples/typologies/print_80x60_2026-11-13/p80x60__osse_ext_throat_700_v7_seed5678.yaml")
    space = DesignSpace.from_config(cfg)
    encoding = ActiveProjection.identity(space)
    seen = []
    def materialize(design, config, **kwargs):
        seen.append(design)
        # Fixture keeps geometry checks isolated from the installed mesher.
        return {"inner_points": np.ones((4, 3, 3)), "formula": "fixture"}
    monkeypatch.setattr(data, "materialize_geometry", materialize)
    monkeypatch.setattr(data, "_envelope_ok", lambda *args: True)
    monkeypatch.setattr(data, "_throat_ok", lambda *args: True)
    pool = data.build_candidate_pool(space, encoding, cfg, n=1, seed=13)
    candidate = pool.candidates[0]
    canonical = data.canonical_design(encoding.denormalize(candidate.active_vector), cfg, space=space)
    assert candidate.params == canonical.params
    assert candidate.design_hash == canonical.hash() == seen[0].hash()
    validate_selected_candidate(candidate, pool, encoding=encoding, config=cfg)
