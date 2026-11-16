"""CPU-only BO contract tests for the versioned rolled family."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from conftest import REPO
from hornlab_search.bo.data import (UnsupportedGeometryError, _geometry_hash,
                                    build_candidate_pool, geometry_checks,
                                    materialize_geometry, materialized_geometry_hash)
from hornlab_search.bo.encoding import ActiveProjection, HashMismatchError
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.types import Design


@pytest.fixture(params=["rect", "section"])
def task(request):
    path = REPO / "examples/typologies/rolled_family_2026-11-15" / f"rf__{request.param}_radial_v7.yaml"
    cfg = load_config(path)
    space = DesignSpace.from_config(cfg)
    return path, cfg, space, ActiveProjection.identity(space)


def test_surface_identity_includes_outer_and_preserves_native(task):
    _, cfg, space, _ = task
    mat = materialize_geometry(space.seed, cfg)
    assert mat["formula"] == "rolled-family-v1"
    assert mat["sampling_metadata"]["fixed_recipe_sampling"] is True
    assert mat["sampling_metadata"]["requested_resolution_mm"] == 20.0
    mounted = copy.copy(cfg)
    mounted.mounting = {"type": "enclosure"}
    with pytest.raises(UnsupportedGeometryError):
        materialize_geometry(space.seed, mounted)
    _, envelope, throat = geometry_checks(mat, cfg, space.seed.params)
    assert envelope and throat
    changed = dict(mat, outer_points=mat["outer_points"].copy())
    changed["outer_points"][0, -1, 2] += 1.0
    assert materialized_geometry_hash(changed) != materialized_geometry_hash(mat)
    native = {"formula": "native", "inner_points": mat["inner_points"]}
    assert materialized_geometry_hash(native) == _geometry_hash(native["inner_points"], "native")
    changed["outer_points"][0, -1, 0] = 10000
    assert not geometry_checks(changed, cfg, space.seed.params)[1]
    bad_throat = dict(mat, inner_points=mat["inner_points"].copy())
    bad_throat["inner_points"][0, 0, 0] += 5.0
    assert not geometry_checks(bad_throat, cfg, space.seed.params)[2]


def test_pool_and_cold_replay(task):
    path, cfg, space, encoding = task
    pool = build_candidate_pool(space, encoding, cfg, n=8, seed=13, max_extra_seeds=0)
    assert pool.status == "ok" and pool.candidates
    candidate = pool.candidates[0]
    design = encoding.denormalize(candidate.active_vector)
    assert materialized_geometry_hash(materialize_geometry(design, cfg)) == candidate.geometry_hash
    # New interpreter, no wrapper install or shared in-memory hash map.
    code = '''import json, sys
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.bo.encoding import ActiveProjection
from hornlab_search.bo.data import materialize_geometry, materialized_geometry_hash
from hornlab_search.types import Design
cfg = load_config(sys.argv[1]); space = DesignSpace.from_config(cfg)
d = Design("FREEFORM", json.loads(sys.stdin.read()))
enc = ActiveProjection.identity(space)
x = enc.normalize_design(d)
print(json.dumps({"hash": materialized_geometry_hash(materialize_geometry(d, cfg)), "x": x.tolist()}))
'''
    proc = subprocess.run([sys.executable, "-c", code, str(path)], input=json.dumps(design.params),
                          text=True, capture_output=True, cwd=REPO, timeout=120, check=True)
    replay = json.loads(proc.stdout.strip().splitlines()[-1])
    assert replay["hash"] == candidate.geometry_hash
    assert np.allclose(replay["x"], candidate.active_vector)
    assert all(v is not None for v in encoding.reference_values().values())


def test_persisted_recipe_changes_refuse(task):
    _, cfg, space, _ = task
    params = copy.deepcopy(space.seed.params)
    params["grid"]["rows"]["implementation_sha256"] = "changed"
    bad = Design("FREEFORM", params)
    with pytest.raises(UnsupportedGeometryError):
        materialize_geometry(bad, cfg)
    fresh = ActiveProjection.identity(DesignSpace.from_config(cfg))
    with pytest.raises(HashMismatchError):
        fresh.normalize_design(bad)
    params = copy.deepcopy(space.seed.params)
    params["grid"]["rows"]["driver"]["exit_radius_mm"] += 1.0
    with pytest.raises(UnsupportedGeometryError):
        materialize_geometry(Design("FREEFORM", params), cfg)
    with pytest.raises(HashMismatchError):
        fresh.normalize_design(Design("FREEFORM", params))
    params = copy.deepcopy(space.seed.params)
    params["grid"]["knobs"]["unexpected"] = 1.0
    with pytest.raises(HashMismatchError):
        fresh.normalize_design(Design("FREEFORM", params))


def test_untrusted_grid_stays_refused(task):
    _, cfg, _, _ = task
    d = Design("FREEFORM", {"grid": {"rows": {"type": "rolled_rect"}}})
    with pytest.raises(UnsupportedGeometryError):
        materialize_geometry(d, cfg)


def test_family_pool_receives_history_and_refuses_external(task, monkeypatch):
    from hornlab_search.bo import data
    from hornlab_search.studies import builders
    path, _, _, _ = task
    seen = {}
    def fake_pool(space, encoding, config, *, seed, known_geometry_hashes):
        seen.update(seed=seed, known=known_geometry_hashes)
        return "pool"
    monkeypatch.setattr(data, "build_candidate_pool", fake_pool)
    assert builders._load_pool(None, {}, path, root=REPO, seed=5,
                               known_geometry_hashes=["surface"], trusted_family=True) == "pool"
    assert seen == {"seed": 5, "known": ["surface"]}
    with pytest.raises(builders.Unavailable):
        builders._load_pool(object(), {}, path, root=REPO, trusted_family=True)


def test_pareto_uses_surface_identity_and_preserves_native_fallback():
    from hornlab_search.studies.builders import pareto_training_from_artifacts
    training = SimpleNamespace(
        ids=("family", "native"), X=np.array([[0.1], [0.2]]), J=np.array([1., 2.]),
        meta={"identities": {"family": {"design_hash": "recipe", "geometry_hash": "surface"},
                             "native": {"design_hash": "legacy"}}})
    metrics = {"observations": {"family": {"coverage_deg": 1., "ripple_db": 2.},
                                "native": {"coverage_deg": 2., "ripple_db": 3.}},
               "reference": {}, "metric_policy": {"physical_metric_spec_hash": "hash"}}
    assert pareto_training_from_artifacts(training, metrics).geometry_ids == ("surface", "legacy")
