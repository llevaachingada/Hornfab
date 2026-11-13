"""Focused tests for hornlab_search/bo/data.py (B2 M0).

Training-set selection is pure numpy/scipy.  The candidate-pool tests need the installed
``hornlab_mesher`` geometry resolve (no gmsh, no BEM); they are skipped without it.
"""
from __future__ import annotations

import copy
import json
import random

import numpy as np
import pytest

from conftest import REPO, requires_mesher
from hornlab_search.bo import (
    ActiveProjection,
    TrainingObservation,
    build_candidate_pool,
    build_training_set,
    is_near_duplicate,
    make_pure_observations,
    n_min_for,
)
from hornlab_search.bo.data import NATIVE_REFUSAL_REASONS, build_native_training_set
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace

CONFIG = REPO / "examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml"
NATIVE_SCORES = REPO / "scratch/bo_m0/r0/offline_scores_native_full/offline_scores.json"
NATIVE_CATALOG = REPO / "scratch/bo_m0/s0/catalog/catalog.csv"
NATIVE_DATASET = REPO / "dataset"

needs_native_archive = pytest.mark.skipif(
    not (NATIVE_SCORES.is_file() and NATIVE_CATALOG.is_file() and NATIVE_DATASET.is_dir()),
    reason="native scores/catalog/dataset artifacts are not present in this checkout")


# ------------------------------------------------------------------ training set


def test_n_min_formula():
    assert n_min_for(1) == 16
    assert n_min_for(3) == 16
    assert n_min_for(13) == 28
    assert n_min_for(14) == 30


def test_below_n_min_returns_needs_initial_data_with_sobol_manifest():
    obs = make_pure_observations(3, 15, seed=1)
    ts = build_training_set(obs, d=3)
    assert ts.status == "needs_initial_data"
    assert ts.n == 0 and ts.X is None and ts.Y is None
    assert ts.n_min == 16 and ts.n_unique == 15
    assert ts.preparation["method"] == "scrambled_sobol"
    assert ts.preparation["n_missing"] == 1
    assert len(ts.preparation["points"]) == 1
    assert all(len(row) == 3 for row in ts.preparation["points"])


def test_at_n_min_returns_arrays_and_y_is_minus_j():
    obs = make_pure_observations(3, 16, seed=1)
    ts = build_training_set(obs, d=3)
    assert ts.status == "ok" and ts.n == 16
    assert ts.X.shape == (16, 3) and ts.X.dtype == np.float64
    assert ts.Y.shape == (16, 1)
    assert np.allclose(ts.Y, -ts.J)
    assert len(ts.ids) == 16
    assert ts.maximin_ids == ()
    assert ts.preparation is None


def test_cap_is_64_lowest_plus_192_deterministic_maximin():
    obs = make_pure_observations(3, 300, seed=7)
    ts = build_training_set(obs, d=3)
    assert ts.status == "ok" and ts.n == 256
    assert len(ts.elite_ids) == 64 and len(ts.maximin_ids) == 192
    assert len(ts.excluded_ids) == 44
    assert set(ts.ids) == set(ts.elite_ids) | set(ts.maximin_ids)
    # The 64 lowest-J rows are exactly the elites.
    ordered = sorted(obs, key=lambda o: (o.J, o.observation_id))
    assert list(ts.elite_ids) == [o.observation_id for o in ordered[:64]]
    # Deterministic under input-order permutation, ties by ID.
    shuffled = list(obs)
    random.Random(3).shuffle(shuffled)
    ts2 = build_training_set(shuffled, d=3)
    assert ts2.ids == ts.ids
    assert ts2.elite_ids == ts.elite_ids
    assert ts2.maximin_ids == ts.maximin_ids


def test_geometry_dedup_keeps_one_comparable_observation():
    a = TrainingObservation("obs-a", np.array([0.1, 0.2, 0.3]), J=1.0, geometry_hash="g1")
    b = TrainingObservation("obs-b", np.array([0.1, 0.2, 0.3]), J=0.5, geometry_hash="g1")
    c = TrainingObservation("obs-c", np.array([0.9, 0.8, 0.7]), J=2.0, geometry_hash="g2")
    ts = build_training_set([a, b, c], d=3)
    # 16 n_min floor means this is needs_initial_data, but the dedup counts are still published.
    assert ts.n_unique == 2 and ts.n_eligible == 3
    assert "obs-a" in ts.excluded_ids
    assert ts.meta["n_duplicates_removed"] == 1


def test_physical_solve_identity_is_geometry_plus_solve():
    x = np.array([0.1, 0.2, 0.3])
    a = TrainingObservation("a", x, J=1.0, geometry_hash="g1", solve_hash="s1")
    b = TrainingObservation("b", x, J=0.5, geometry_hash="g1", solve_hash="s1")  # cache repeat
    c = TrainingObservation("c", x, J=2.0, geometry_hash="g1", solve_hash="s2")  # new solve
    d = TrainingObservation("d", x + 0.1, J=3.0, geometry_hash="g2", solve_hash="s1")
    ts = build_training_set([a, b, c, d], d=3)
    assert ts.n_unique == 3 and ts.n_eligible == 4
    assert ts.meta["n_duplicates_removed"] == 1
    # The lower-J duplicate survives; the cache repeat is the excluded alias.
    assert "a" in ts.excluded_ids and "b" not in ts.excluded_ids


def test_typed_failure_is_excluded_but_large_legitimate_j_is_not():
    obs = make_pure_observations(3, 16, seed=2)
    failed = TrainingObservation("bad", np.array([0.2, 0.2, 0.2]), J=1000.0,
                                 status="solve_failed")
    large = TrainingObservation("large", np.array([0.9, 0.9, 0.9]), J=1000.0,
                                status="ok")
    ts = build_training_set(obs + [failed, large], d=3)
    assert ts.status == "ok"
    assert "bad" not in ts.ids
    assert "large" in ts.ids
    assert float(np.max(ts.J)) == pytest.approx(1000.0)  # no sentinel filtering
    assert ts.n_eligible == 17


# ------------------------------------------------------------------ candidate pool


@pytest.fixture(scope="module")
def pool_ctx():
    cfg = load_config(CONFIG)
    space = DesignSpace.from_config(cfg)
    enc = ActiveProjection.from_space(space, no_ops={"morph_exponent": 4.0})
    return cfg, space, enc


@requires_mesher
def test_pool_is_deterministic_and_cheap_only(pool_ctx):
    cfg, space, enc = pool_ctx
    a = build_candidate_pool(space, enc, cfg, n=32, seed=1234)
    b = build_candidate_pool(space, enc, cfg, n=32, seed=1234)
    assert a.status == "ok"
    assert [c.design_hash for c in a.candidates] == [c.design_hash for c in b.candidates]
    assert a.counts == b.counts
    assert a.seed_reports == b.seed_reports
    assert a.intended_solve_hash and a.intended_solve_hash == b.intended_solve_hash
    for cand in a.candidates:
        assert cand.status == "cheap-check-passed; mesh/acoustic eligibility unknown"
        assert cand.checks["mesh_built"] is False
        assert cand.checks["bem_called"] is False
        assert cand.checks["schema"] == "passed"
        assert cand.geometry_hash and cand.intended_solve_hash
    c = build_candidate_pool(space, enc, cfg, n=32, seed=1235)
    assert [x.design_hash for x in c.candidates] != [x.design_hash for x in a.candidates]


@requires_mesher
def test_pool_counts_partition_generated_candidates(pool_ctx):
    cfg, space, enc = pool_ctx
    p = build_candidate_pool(space, enc, cfg, n=64, seed=1234)
    c = p.counts
    assert c["generated"] == 64
    rejected = (c["schema_rejected"] + c["envelope_rejected"] + c["throat_rejected"]
                + c["geometry_rejected"])
    duplicates = c["geometry_duplicate"] + c["near_duplicate"] + c["known_duplicate"]
    assert c["unique"] == len(p.candidates)
    assert c["novel"] == c["unique"]
    assert rejected + duplicates + c["unique"] == c["generated"]
    assert p.summary()["n_candidates"] == c["unique"]


@requires_mesher
def test_pool_dedup_and_exhaustion(pool_ctx):
    cfg, space, enc = pool_ctx
    first = build_candidate_pool(space, enc, cfg, n=16, seed=1234)
    known = {c.geometry_hash for c in first.candidates}
    again = build_candidate_pool(space, enc, cfg, n=16, seed=1234,
                                 known_geometry_hashes=known, max_extra_seeds=0)
    assert again.status == "pool_exhausted"
    assert again.candidates == ()
    assert again.counts["known_duplicate"] > 0
    # A deliberately impossible brief envelope rejects every candidate; after the recorded
    # seed budget the pool returns pool_exhausted rather than inventing candidates.
    tight = copy.deepcopy(cfg)
    tight.brief["envelope"] = {"max_mouth_w_mm": 1.0, "max_mouth_h_mm": 1.0,
                               "max_depth_mm": 1.0}
    empty = build_candidate_pool(space, enc, tight, n=8, seed=1234, max_extra_seeds=2)
    assert empty.status == "pool_exhausted"
    assert empty.seeds_tried == (1234, 1235, 1236)
    assert len(empty.seed_reports) == 3
    assert empty.counts["envelope_rejected"] == 24
    assert empty.candidates == ()


def test_near_duplicate_tolerance():
    base = np.zeros(4)
    assert is_near_duplicate(base + 1e-7, [base]) is True
    assert is_near_duplicate(base + 1e-4, [base]) is False
    assert is_near_duplicate(base, []) is False

# ------------------------------------------------------------------ native cohort builder


def _dataset_meta(shard: int, row: int):
    path = NATIVE_DATASET / f"shard-{shard:04d}.jsonl"
    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i == row:
                return json.loads(line)
    return None


def _native_training_set(**kwargs):
    return build_native_training_set(
        CONFIG, scores_json=NATIVE_SCORES, catalog_csv=NATIVE_CATALOG, **kwargs)


@needs_native_archive
def test_native_trainingset_from_archive_roundtrips_real_rows():
    ts = _native_training_set()
    assert ts.status == "ok"
    assert ts.d == 13
    assert ts.n >= 100
    assert ts.X is not None and ts.X.shape == (ts.n, 13)
    assert ts.Y is not None and ts.Y.shape == (ts.n, 1)
    assert np.allclose(ts.Y, -ts.J)
    assert ts.Y_phys is not None and ts.Y_phys.shape == (ts.n, 1)
    assert np.allclose(ts.Y_phys[:, 0], ts.J[:, 0])
    assert ts.n == min(ts.n_unique, ts.n_max)
    assert ts.n_min == n_min_for(13) == 28
    assert ts.n_max == 256

    artifact_rows = json.loads(NATIVE_SCORES.read_text(encoding="utf-8"))["rows"]
    by_id = {r["physical_id"]: r for r in artifact_rows}
    assert set(ts.ids) <= set(by_id)
    assert len(set(ts.ids)) == len(ts.ids)
    for observation_id, j in zip(ts.ids, ts.J[:, 0]):
        assert float(j) == pytest.approx(float(by_id[observation_id]["j"]), abs=1e-12)

    identities = ts.meta["identities"]
    assert len(identities) == ts.n_eligible
    for observation_id in ts.ids[:5]:
        rec = by_id[observation_id]
        ident = identities[observation_id]
        assert ident["physical_id"] == rec["physical_id"]
        assert ident["metric_id"] == rec["metric_id"]
        assert ident["score_id"] == rec["score_id"]
        assert ident["J"] == pytest.approx(float(rec["j"]))

    assert ts.meta["n_refused"] == len(ts.meta["refused"])
    assert sum(ts.meta["refusal_reasons"].values()) == ts.meta["n_refused"]
    assert set(ts.meta["refusal_reasons"]) <= set(NATIVE_REFUSAL_REASONS)
    assert ts.meta["n_unique_design_hashes"] <= ts.n_eligible


@needs_native_archive
def test_native_trainingset_from_archive_is_deterministic():
    a = _native_training_set()
    b = _native_training_set()
    assert a.ids == b.ids
    assert a.elite_ids == b.elite_ids
    assert a.maximin_ids == b.maximin_ids
    assert a.excluded_ids == b.excluded_ids
    assert a.X.tobytes() == b.X.tobytes()
    assert a.Y.tobytes() == b.Y.tobytes()
    # Retained + excluded ids partition the joined real observations exactly.
    assert set(a.ids) | set(a.excluded_ids) == set(a.meta["identities"])
    if a.n > a.n_max:
        assert len(a.elite_ids) == 64 and len(a.maximin_ids) == a.n_max - 64


@needs_native_archive
def test_native_trainingset_from_archive_encoding_roundtrip_real_params():
    from hornlab_search.types import Design

    cfg = load_config(CONFIG)
    space = DesignSpace.from_config(cfg)
    enc = ActiveProjection.from_space(space, no_ops={"morph_exponent": 4.0})
    assert enc.d == 13 and enc.full_d == 14
    assert enc.fixed_values == {"morph_exponent": 4.0}

    # The frozen seed row round-trips hash-exactly through the full vector.
    seed_meta = _dataset_meta(30, 420)
    assert seed_meta is not None
    seed = Design(seed_meta["family"], seed_meta["params"])
    x = enc.normalize_design(seed)
    assert x.shape == (13,)
    assert enc.denormalize(x).hash() == seed.hash()
    assert enc.denormalize(x).params["morph_exponent"] == 4.0

    # A real row whose inactive morph_exponent differs still reconstructs the fixed key at 4.0;
    # every other (active/fixed) parameter is unchanged.
    shifted_meta = _dataset_meta(33, 64)
    if shifted_meta is not None and shifted_meta["params"].get("morph_exponent") != 4.0:
        shifted = Design(shifted_meta["family"], shifted_meta["params"])
        xs = enc.normalize_design(shifted, verify_round_trip=False)
        rebuilt = enc.denormalize(xs)
        assert rebuilt.params["morph_exponent"] == 4.0
        for key, value in shifted.params.items():
            if key != "morph_exponent":
                assert rebuilt.params[key] == value


def test_native_trainingset_from_archive_refuses_missing_params(tmp_path):
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    (dataset / "shard-0000.jsonl").write_text(
        json.dumps({"ok": True, "family": "OSSE", "params": {}, "design_hash": "x"}) + "\n",
        encoding="utf-8")
    catalog = tmp_path / "catalog.csv"
    catalog.write_text(
        "root,shard_index,row,config_name\n"
        "dataset,0,0,native__ath_core_v4\n",
        encoding="utf-8")
    scores = tmp_path / "scores.json"
    scores.write_text(json.dumps({
        "cohort": {"native_config": "native__ath_core_v4"},
        "rows": [
            {"shard": 0, "row": 0, "config_name": "native__ath_core_v4",
             "status": "exact_complete", "complete": True, "j": 1.0,
             "physical_id": "p0", "metric_id": "m0", "score_id": "s0",
             "design_hash": "x"},
            {"shard": 0, "row": 1, "config_name": "native__ath_core_v4",
             "status": "exact_complete", "complete": True, "j": 2.0,
             "physical_id": "p1", "metric_id": "m1", "score_id": "s1"},
        ],
    }), encoding="utf-8")

    ts = build_native_training_set(CONFIG, scores_json=scores, catalog_csv=catalog,
                                   dataset_root=dataset)
    assert ts.status == "needs_initial_data"
    assert ts.n == 0 and ts.X is None and ts.Y is None
    assert ts.meta["n_observations"] == 0
    assert ts.meta["n_refused"] == 2
    assert ts.meta["refusal_reasons"] == {
        "catalog_row_missing": 1, "design_params_missing": 1}
    assert {r["id"] for r in ts.meta["refused"]} == {"p0", "p1"}
