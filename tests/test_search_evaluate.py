"""evaluate(): hard failures propagate, everything else becomes a penalty row; DI weights; caches."""
from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.config import mode_freqs
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh.build import MeshUnitsError, SymmetryMismatchError
from hornlab_search.search import evaluate as ev_mod
from hornlab_search.search.evaluate import (evaluate, make_context, metrics_from_response,
                                            mouth_dims_m, read_ndjson, row_to_evaluation)
from hornlab_search.solve.base import balloon_dirs_from_angles
from hornlab_search.targets.spec import Target
from hornlab_search.types import MeshResult, Response
from test_search_support import LIBS, SyntheticBackend, fast_cfg, install_fakes, synthetic_response


@pytest.fixture
def cfg(smoke_cfg):
    return fast_cfg(smoke_cfg)


def _ctx(cfg, store, **kw):
    return make_context(cfg, store, lib_shas=LIBS, **kw)


def test_mesh_consistency_errors_propagate_and_are_not_penalty_rows(cfg, tmp_path, monkeypatch):
    for exc in (MeshUnitsError("bbox 1000x"), SymmetryMismatchError("flag")):
        def boom(*a, **k):
            raise exc
        monkeypatch.setattr(ev_mod, "build_mesh", boom)
        space = DesignSpace.from_config(cfg)
        with pytest.raises(type(exc)):
            evaluate(space.seed, space, cfg, "screen", tmp_path, DatasetStore(tmp_path / "ds"),
                     SyntheticBackend(), ctx=_ctx(cfg, None))
        assert not (tmp_path / "search.ndjson").exists()


def test_evaluate_happy_path_writes_every_artifact(cfg, tmp_path, monkeypatch):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    store = DatasetStore(tmp_path / "ds")
    space = DesignSpace.from_config(cfg)
    ev = evaluate(space.seed, space, cfg, "screen", tmp_path / "run", store, be,
                  ctx=_ctx(cfg, store, ndjson=tmp_path / "run" / "search.ndjson"))
    assert not ev.error and np.isfinite(ev.objective) and ev.metrics.di_source == "balloon"
    assert ev.mesh.n_dof == 1234                           # taken from the solve
    d = tmp_path / "run" / "designs" / ev.design_hash
    for f in ("design.json", "status.json", "metrics.json", "response.npz", "mesh.msh"):
        assert (d / f).exists(), f
    (row,) = read_ndjson(tmp_path / "run" / "search.ndjson")
    assert row["design_hash"] == ev.design_hash and row["objective"] == ev.objective
    (meta, arrays) = next(store.iter_records(with_arrays=True))
    assert meta["ok"] and meta["objective_version"] == 1
    assert meta["mesh"]["area_m2"] == 0.1 and meta["mesh"]["grid"]["available"]
    assert meta["mesh"]["grid"]["angular_segments"] == 64 and meta["solve"]["mode"] == "screen"
    assert "spl_h_db" in arrays and meta["solve"]["freqs_hz"] == list(mode_freqs("screen", cfg))


def test_row_roundtrip_preserves_the_objective_exactly(cfg, tmp_path, monkeypatch):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    space = DesignSpace.from_config(cfg)
    ev = evaluate(space.seed, space, cfg, "screen", tmp_path, None, be, ctx=_ctx(cfg, None))
    (row,) = read_ndjson(tmp_path / "search.ndjson")
    lite = row_to_evaluation(row)
    assert lite.objective == ev.objective and lite.terms == ev.terms and lite.cached
    assert lite.design.hash() == ev.design.hash()
    assert np.array_equal(lite.metrics.bw_h_deg, ev.metrics.bw_h_deg)
    assert lite.metrics.di_source == ev.metrics.di_source


def test_cross_run_solve_cache_hit_does_not_touch_the_backend_or_duplicate_the_record(
        cfg, tmp_path, monkeypatch):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    store = DatasetStore(tmp_path / "ds")
    space = DesignSpace.from_config(cfg)
    cache = tmp_path / "cache"
    ev1 = evaluate(space.seed, space, cfg, "screen", tmp_path / "a", store, be,
                   ctx=_ctx(cfg, store, cache_dir=cache))
    assert be.calls == 1 and not ev1.cached
    ev2 = evaluate(space.seed, space, cfg, "screen", tmp_path / "b", store, be,
                   ctx=_ctx(cfg, store, cache_dir=cache))
    assert be.calls == 1, "a cache hit must not touch the GPU"
    assert ev2.cached and ev2.objective == ev1.objective
    assert len(store) == 1
    (row,) = read_ndjson(tmp_path / "b" / "search.ndjson")
    assert row["cached"] is True
    # a changed weight re-scores the stored Response (the cache stores the solve, not the score)
    cfg2 = dataclasses.replace(cfg, weights={**cfg.weights, "rip": 5.0})
    ev3 = evaluate(space.seed, space, cfg2, "screen", tmp_path / "c", store, be,
                   ctx=_ctx(cfg2, store, cache_dir=cache))
    assert be.calls == 1 and ev3.cached and ev3.objective != ev1.objective


def test_a_failed_solve_is_not_served_from_the_cache(cfg, tmp_path, monkeypatch):
    be = SyntheticBackend(fail_on={1: "fail"})
    install_fakes(monkeypatch, be)
    space = DesignSpace.from_config(cfg)
    cache = tmp_path / "cache"
    ev1 = evaluate(space.seed, space, cfg, "screen", tmp_path / "a", None, be,
                   ctx=_ctx(cfg, None, cache_dir=cache))
    assert ev1.error.startswith("solve_failed") and ev1.objective == 1000.0
    ev2 = evaluate(space.seed, space, cfg, "screen", tmp_path / "b", None, be,
                   ctx=_ctx(cfg, None, cache_dir=cache))
    assert be.calls == 2 and not ev2.error                # retried, and this time it worked


def test_dataset_write_failure_is_logged_not_raised(cfg, tmp_path, monkeypatch, caplog):
    class BrokenStore(DatasetStore):
        def append(self, meta, arrays=None):
            raise ValueError("synthetic invalid record")
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    store = BrokenStore(tmp_path / "ds")
    space = DesignSpace.from_config(cfg)
    with caplog.at_level("ERROR"):
        ev = evaluate(space.seed, space, cfg, "screen", tmp_path / "r", store, be, ctx=_ctx(cfg, store))
    assert not ev.error and "was NOT written" in caplog.text
    assert len(read_ndjson(tmp_path / "r" / "search.ndjson")) == 1


# ---- DI from the solver's theta-phi balloon

def _theta_phi_cardioid(n_theta=16, n_phi=32):
    th = np.repeat(np.linspace(0.0, 180.0, n_theta), n_phi)
    ph = np.tile(np.linspace(0.0, 360.0, n_phi, endpoint=False), n_theta)
    dirs = balloon_dirs_from_angles(th, ph)
    mag = np.maximum((1 + dirs[:, 2]) / 2, 1e-3)
    return dirs, 94.0 + 20 * np.log10(mag)


def test_balloon_di_uses_sin_theta_weights_for_a_theta_phi_grid():
    base = synthetic_response({}, [1000.0, 2000.0], 73, 8)
    dirs, bal = _theta_phi_cardioid()
    t = Target(75, 45, 500, 5000, None)
    kw = dict(balloon_dirs=dirs, spl_balloon_db=np.tile(bal, (2, 1)))
    weighted = dataclasses.replace(base, **kw, meta={"balloon_grid": [16, 32]})
    naive = dataclasses.replace(base, **kw, meta={})
    dw = metrics_from_response(weighted, t)
    dn = metrics_from_response(naive, t)
    assert dw.di_source == "balloon"
    true_di = 10 * np.log10(3.0)                         # cardioid, exact
    assert np.allclose(dw.di_db, true_di, atol=0.15), dw.di_db
    assert np.all(np.abs(dn.di_db - true_di) > 0.25)     # equal weights over-count the poles
    # every other scalar is still the one compute_metrics produces
    assert dw.scalars["di_source"] == "balloon" and np.isfinite(dw.scalars["di_slope_db_per_dec"])


def test_response_without_balloon_is_flagged_cuts_estimate():
    r = dataclasses.replace(synthetic_response({}, [1000.0, 2000.0], 73, 8), balloon_dirs=None,
                            spl_balloon_db=None)
    m = metrics_from_response(r, Target(75, 45, 500, 5000, None))
    assert m.di_source == "cuts_estimate"


def test_mouth_dims_double_the_reduced_axes():
    m = MeshResult("x", 1, None, "1", "yz+xz", {}, (0.0, 0.0, 0.0, 0.2, 0.15, 0.3), 0.0)
    assert mouth_dims_m(m) == (0.4, 0.3)
    m = dataclasses.replace(m, symmetry_plane="xz", quadrants="12", bbox_m=(-0.2, 0.0, 0.0, 0.2, 0.15, 0.3))
    assert mouth_dims_m(m) == (0.4, 0.3)
    m = dataclasses.replace(m, symmetry_plane=None, quadrants="1234", bbox_m=(-0.2, -0.15, 0, 0.2, 0.15, 0.3))
    assert mouth_dims_m(m) == (0.4, 0.3)


def test_a_relative_run_dir_still_gives_the_solver_an_absolute_mesh_path(cfg, tmp_path, monkeypatch):
    """Live bug: the Julia host resolves a relative mesh path against ITS cwd, not ours."""
    seen = []

    class Spy(SyntheticBackend):
        def solve(self, mesh, spec):
            seen.append(mesh.path)
            return super().solve(mesh, spec)
    be = Spy()
    install_fakes(monkeypatch, be)
    monkeypatch.chdir(tmp_path)
    space = DesignSpace.from_config(cfg)
    ev = evaluate(space.seed, space, cfg, "screen", Path("rel_run"), None, be, ctx=_ctx(cfg, None))
    assert not ev.error and seen and Path(seen[0]).is_absolute()
    assert (tmp_path / "rel_run" / "search.ndjson").exists()


# ---- invalid_envelope failure marker: replay only under the brief that produced the verdict

def test_invalid_envelope_failure_marker_is_scoped_to_the_brief(tmp_path):
    import json

    from conftest import EXAMPLES
    from hornlab_search.config import load_config
    from hornlab_search.design.generated import GENERATOR_ERROR_KEY, GeneratedSpace, brief_hash

    cfg = load_config(EXAMPLES / "typologies" / "conical.yaml")
    space = GeneratedSpace.from_config(cfg)
    bad = space.design_from_knobs({**space.seed_knobs, "h_rm_mm": 180.0})
    assert bad.params[GENERATOR_ERROR_KEY].startswith("invalid_envelope:")
    cache = tmp_path / "cache"

    # 1. first evaluation writes the marker
    ev1 = evaluate(bad, space, cfg, "screen", tmp_path / "r1", None, None,
                   ctx=make_context(cfg, None, lib_shas=LIBS, cache_dir=cache))
    assert ev1.error.startswith("invalid_envelope") and not ev1.cached

    # 2. the same brief replays the memoized verdict
    ev2 = evaluate(bad, space, cfg, "screen", tmp_path / "r2", None, None,
                   ctx=make_context(cfg, None, lib_shas=LIBS, cache_dir=cache))
    assert ev2.cached and ev2.error == ev1.error

    # 3. a different brief envelope on the SAME design must NOT replay the old verdict
    assert cfg.brief is not None
    tight = dict(cfg.brief)
    tight["envelope"] = dict(tight["envelope"], max_depth_mm=100.0)
    cfg2 = dataclasses.replace(cfg, brief=tight,
                               raw={**cfg.raw, "brief": {k: v for k, v in tight.items()
                                                          if k != "path"}})
    ev3 = evaluate(bad, space, cfg2, "screen", tmp_path / "r3", None, None,
                   ctx=make_context(cfg2, None, lib_shas=LIBS, cache_dir=cache))
    assert not ev3.cached and ev3.error.startswith("invalid_envelope")
    marker = next((cache / "solve" / "failures").glob("*.json"))
    rec = json.loads(marker.read_text(encoding="utf-8"))
    assert rec["kind"] == "invalid_envelope"
    assert rec["brief_hash"] == brief_hash(tight)      # re-evaluated and rewritten under cfg2
