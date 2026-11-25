"""``study_cohort`` replay safety for metric (v10/v11) cohorts (Pass 2).

Synthetic tmp_path datasets only -- never the real dataset or a real run directory.  Proves that a
metric-version group with zero encodable / score-identified candidates is a typed refusal (no rows
replayed), that only an explicit ``allow_unranked_replay`` may replay it (recorded as such), and
that the legacy non-metric path is unchanged.
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


def _arrays_for(config):
    cfg = load_config(config)
    brief = replay.brief_from_config(config)
    response = make_fake_response()
    metrics = compute_metrics(response, brief.target)
    arrays = replay._arrays_from_response(response)
    arrays.update({k: np.asarray(getattr(metrics, k)) for k in
                   ("bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db", "ripple_v_db",
                    "on_axis_db")})
    return cfg, brief, arrays


def _write_metric_dataset(tmp_path, rows):
    """``rows`` are per-record overrides: ``params``, ``brief_hash``, ``terms``, ``objective``."""
    cfg, brief, arrays = _arrays_for(CONFIG)
    space = DesignSpace.from_config(cfg)
    dataset = tmp_path / "dataset"
    (dataset / "shard-0000").mkdir(parents=True)
    lines, designs = [], []
    n_keys = len(space.keys())
    for i, spec in enumerate(rows):
        spec = dict(spec)
        design = space.denormalize(np.full(n_keys, (i + 1) / (len(rows) + 1)))
        designs.append(design)
        meta = {
            "ok": True, "design_hash": design.hash(), "mesh_hash": "mesh",
            "solve_hash": "solve", "objective_version": cfg.objective_version,
            "objective": float(spec.pop("objective", 10.0 + i)),
            "terms": spec.pop("terms", {}), "metrics_scalars": {},
            "target": dataclasses.asdict(brief.target), "config_name": cfg.name,
            "run_id": "run", "family": design.family,
            "params": spec.pop("params", design.params),
            "provenance": {"config": cfg.name,
                           "brief_hash": spec.pop("brief_hash", "brief")},
            "solve": {"mode": "screen", "backend": cfg.solve.backend,
                      "freqs_hz": [500.0, 8000.0]},
            "lib_shas": {"hornlab_beat_bem": "a"},
        }
        meta.update(spec)
        lines.append(json.dumps(meta) + "\n")
        np.savez(dataset / "shard-0000" / f"rec-{i:04d}.npz", **arrays)
    (dataset / "shard-0000.jsonl").write_text("".join(lines), encoding="utf-8")
    return cfg, dataset, designs


def _scores(out):
    return json.loads((out / "offline_scores.json").read_text())


def test_uncodable_metric_group_is_a_typed_refusal_with_no_replay(tmp_path):
    _cfg, dataset, _designs = _write_metric_dataset(
        tmp_path, [{"params": None}, {"params": None}])
    result = prepare(CONFIG, dataset, tmp_path / "out", limit=8)
    scores = _scores(tmp_path / "out")
    selection = scores["selection"]

    assert result["counts"] == {}
    assert scores["rows"] == []
    assert selection["selected_ids"] == []

    metric = selection["metric_selection"]
    assert metric["status"] == "refused"
    assert metric["reason"] == "metric_selection_unavailable"
    assert metric["n_records_considered"] == 2
    assert metric["n_replayed"] == 0
    assert metric["allow_unranked_replay"] is False

    reasons = {reason for entry in selection["excluded_reasons"]
               for reason in entry["reasons"]}
    assert "design_params_missing" in reasons
    assert len(metric["excluded"]) == 2
    assert {entry["observation_id"] for entry in metric["excluded"]} == set(
        selection["excluded_ids"])


def test_unranked_replay_requires_and_records_explicit_authorization(tmp_path):
    _cfg, dataset, _designs = _write_metric_dataset(
        tmp_path, [{"params": None}, {"params": None}])
    prepare(CONFIG, dataset, tmp_path / "out", limit=8, allow_unranked_replay=True)
    scores = _scores(tmp_path / "out")
    metric = scores["selection"]["metric_selection"]

    assert metric["status"] == "replay_authorized"
    assert metric["reason"] == "metric_selection_unavailable"
    assert metric["basis"] == "allow_unranked_replay"
    assert metric["allow_unranked_replay"] is True
    assert metric["n_replayed"] == 2
    assert len(scores["rows"]) == 2
    assert len(scores["selection"]["selected_ids"]) == 2


def test_one_encodable_record_still_uses_the_ranked_path(tmp_path):
    _cfg, dataset, _designs = _write_metric_dataset(
        tmp_path, [{"params": None, "objective": 1.0}, {"objective": 5.0}])
    prepare(CONFIG, dataset, tmp_path / "out", limit=8)
    scores = _scores(tmp_path / "out")
    metric = scores["selection"]["metric_selection"]

    assert metric["status"] == "needs_initial_data"
    assert len(metric["selected_ids"]) == 1
    assert len(scores["rows"]) == 1
    reasons = {reason for entry in scores["selection"]["excluded_reasons"]
               for reason in entry["reasons"]}
    assert "design_params_missing" in reasons


def test_missing_score_identity_is_excluded_not_ranked(tmp_path):
    _cfg, dataset, _designs = _write_metric_dataset(
        tmp_path, [{"brief_hash": ""}, {"brief_hash": ""}])
    prepare(CONFIG, dataset, tmp_path / "out", limit=8)
    scores = _scores(tmp_path / "out")
    metric = scores["selection"]["metric_selection"]

    assert metric["status"] == "refused"
    assert metric["reason"] == "metric_selection_unavailable"
    assert metric["n_records_considered"] == 2
    assert scores["rows"] == []
    reasons = {reason for entry in scores["selection"]["excluded_reasons"]
               for reason in entry["reasons"]}
    assert reasons == {"score_identity_unavailable"}


def test_ambiguous_score_identity_is_excluded_not_ranked(tmp_path):
    _cfg, dataset, _designs = _write_metric_dataset(
        tmp_path, [{}, {"terms": {"load": 1.0}}])
    prepare(CONFIG, dataset, tmp_path / "out", limit=8)
    scores = _scores(tmp_path / "out")
    metric = scores["selection"]["metric_selection"]

    assert metric["status"] == "refused"
    assert metric["reason"] == "metric_selection_unavailable"
    assert scores["rows"] == []
    assert metric["n_identity_excluded"] == 2
    assert all("score_identity_unavailable" in entry["reasons"]
               for entry in metric["identity_excluded"])


def test_expected_identity_mismatch_excludes_every_record(tmp_path):
    _cfg, dataset, _designs = _write_metric_dataset(
        tmp_path, [{}, {"objective": 5.0}])
    prepare(CONFIG, dataset, tmp_path / "out", limit=8,
            expected_brief_hash="not-the-brief")
    scores = _scores(tmp_path / "out")
    metric = scores["selection"]["metric_selection"]
    assert metric["status"] == "refused"
    assert scores["rows"] == []
    reasons = {reason for entry in scores["selection"]["excluded_reasons"]
               for reason in entry["reasons"]}
    assert reasons == {"score_identity_unavailable"}


def test_expected_score_identity_mismatch_excludes_every_record(tmp_path):
    _cfg, dataset, _designs = _write_metric_dataset(
        tmp_path, [{}, {"objective": 5.0}])
    prepare(CONFIG, dataset, tmp_path / "out", limit=8,
            expected_score_identity="0" * 16)
    scores = _scores(tmp_path / "out")
    assert scores["selection"]["metric_selection"]["status"] == "refused"
    assert scores["rows"] == []


def test_legacy_non_metric_path_is_unchanged(tmp_path):
    from test_replay_v7_study import CONFIG as V7_CONFIG, record

    cfg = load_config(V7_CONFIG)
    dataset = tmp_path / "dataset"
    (dataset / "shard-0000").mkdir(parents=True)
    lines = []
    for i in range(3):
        _, meta, arrays, _ = record()
        meta.update(config_name=cfg.name, run_id="run", family="OSSE",
                    lib_shas={"hornlab_beat_bem": "a"},
                    provenance={"config": cfg.name, "brief_hash": "brief"},
                    solve={"mode": "screen", "backend": cfg.solve.backend,
                           "freqs_hz": [500, 8000]})
        lines.append(json.dumps(meta) + "\n")
        np.savez(dataset / "shard-0000" / f"rec-{i:04d}.npz", **arrays)
    (dataset / "shard-0000.jsonl").write_text("".join(lines), encoding="utf-8")

    result = prepare(V7_CONFIG, dataset, tmp_path / "out")
    scores = _scores(tmp_path / "out")
    assert result["counts"] == {"exact_complete": 3}
    assert scores["selection"]["metric_selection"] == {"status": "not_applicable"}
    assert len(scores["rows"]) == 3
