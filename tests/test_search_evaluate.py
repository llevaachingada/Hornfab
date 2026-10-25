"""evaluate(): hard failures propagate, everything else becomes a penalty row; DI weights; caches."""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from conftest import EXAMPLES, requires_build123d, requires_mesher
from hornlab_search.config import load_config, mode_freqs
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh.build import MeshUnitsError, SymmetryMismatchError
from hornlab_search.search import evaluate as ev_mod
from hornlab_search.search.evaluate import (evaluate, make_context, metrics_from_response,
                                            mouth_dims_m, read_ndjson, row_to_evaluation)
from hornlab_search.solve.base import balloon_dirs_from_angles
from hornlab_search.targets.spec import Target
from hornlab_search.types import Design, MeshResult, Response
from test_mesh_step_build import TINY
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
    assert "mesh_policy" not in row
    (meta, arrays) = next(store.iter_records(with_arrays=True))
    assert meta["ok"] and meta["objective_version"] == 1
    assert "mesh_policy" not in (meta.get("provenance") or {})
    assert "cad" not in row and "cad" not in (meta.get("provenance") or {})
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

# ---- WP8 band-split meshing

class _BandRecorder(SyntheticBackend):
    def __init__(self):
        super().__init__()
        self.specs = []

    def _solve(self, mesh, spec):
        self.specs.append(spec)
        return super()._solve(mesh, spec)


def _install_recording(monkeypatch, backend, mesh_specs):
    """Like test_search_support.install_fakes, but also records each mesh's f_max."""
    from hornlab_search.search import evaluate as ev_mod
    from test_search_support import fake_build_mesh
    inner = fake_build_mesh()

    def build_mesh(design, mesh_spec, cfg, out_dir, **kw):
        backend._params = dict(design.params)
        backend.designs.append(design.hash())
        mesh_specs.append(mesh_spec.f_max_hz)
        return inner(design, mesh_spec, cfg, out_dir, **kw)

    monkeypatch.setattr(ev_mod, "build_mesh", build_mesh)


def test_split_freq_bands_covers_the_whole_grid_exactly_once():
    from hornlab_search.search.evaluate import split_freq_bands

    freqs = (500.0, 1000.0, 2000.0, 3000.0, 4000.0)
    bands = split_freq_bands(freqs, [2000.0, 3000.0])
    # bounds are (lo, hi]: an edge frequency belongs to the band BELOW it
    assert bands == [(500.0, 1000.0, 2000.0), (3000.0,), (4000.0,)]
    assert [f for b in bands for f in b] == list(freqs)
    with pytest.raises(ValueError, match="strictly increasing"):
        split_freq_bands(freqs, [3000.0, 2000.0])


def test_band_split_meshes_and_solves_each_band_and_matches_the_single_mesh(
        monkeypatch, smoke_cfg, tmp_path):
    from hornlab_search.search.evaluate import split_freq_bands
    from hornlab_search.solve.cache import load_response

    base = fast_cfg(smoke_cfg)
    cfg = dataclasses.replace(
        base, mesh=dataclasses.replace(base.mesh, band_split={"edges_hz": [3000.0]}))
    space = DesignSpace.from_config(base)

    flat = _BandRecorder()
    flat_specs = []
    _install_recording(monkeypatch, flat, flat_specs)
    flat_store = DatasetStore(tmp_path / "flat_ds")
    ev_flat = evaluate(space.seed, space, base, "screen", tmp_path / "flat", flat_store, flat,
                       ctx=_ctx(base, flat_store))
    assert not ev_flat.error

    band = _BandRecorder()
    band_specs = []
    _install_recording(monkeypatch, band, band_specs)
    store = DatasetStore(tmp_path / "band_ds")
    ev = evaluate(space.seed, space, cfg, "screen", tmp_path / "band", store, band,
                  ctx=_ctx(cfg, store))
    assert not ev.error

    bands = split_freq_bands(mode_freqs("screen", cfg), [3000.0])
    assert len(bands) == 2
    assert band_specs == [3000.0, 4500.0]          # one mesh per band, f_max == each band's top
    assert len(band.specs) == len(bands)
    assert [f for s in band.specs for f in s.freqs_hz] == list(mode_freqs("screen", cfg))
    for s in band.specs:
        assert s.extra["mesh_policy"] == "band_split_v1"
        assert s.extra["band_edges_hz"] == [3000.0]

    # stacking is bit-identical to one solve on the whole grid: same J, same curves
    assert ev.objective == ev_flat.objective
    for name in ("freqs_hz", "bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db", "ripple_v_db",
                 "on_axis_db"):
        assert np.array_equal(getattr(ev.metrics, name), getattr(ev_flat.metrics, name)), name

    meta, _ = next(store.iter_records(with_arrays=True))
    assert meta["solve"]["freqs_hz"] == list(mode_freqs("screen", cfg))
    assert meta["provenance"]["mesh_policy"] == "band_split_v1"
    (band_row,) = read_ndjson(tmp_path / "band" / "search.ndjson")
    assert band_row["mesh_policy"] == "band_split_v1"
    resp = load_response(tmp_path / "band" / "designs" / ev.design_hash / "response.npz")
    assert np.array_equal(resp.freqs_hz, ev_flat.metrics.freqs_hz)
    assert "seam_check" not in resp.meta


def test_band_split_seam_check_runs_only_in_verify(monkeypatch, smoke_cfg, tmp_path):
    from hornlab_search.search.evaluate import split_freq_bands
    from hornlab_search.solve.cache import load_response

    base = fast_cfg(smoke_cfg)
    cfg = dataclasses.replace(
        base, mesh=dataclasses.replace(base.mesh, band_split={"edges_hz": [3000.0]}))
    space = DesignSpace.from_config(base)

    verify = _BandRecorder()
    verify_specs = []
    _install_recording(monkeypatch, verify, verify_specs)
    ev = evaluate(space.seed, space, cfg, "verify", tmp_path / "verify", None, verify,
                  ctx=_ctx(cfg, None))
    assert not ev.error
    resp = load_response(tmp_path / "verify" / "designs" / ev.design_hash / "response.npz")
    seam = resp.meta["seam_check"]["3000"]
    f_seam = next(f for f in mode_freqs("verify", cfg) if f > 3000.0)
    assert seam["freq_hz"] == f_seam
    assert seam["on_axis_delta_db"] == pytest.approx(0.0, abs=1e-12)
    assert seam["bw_h_delta_deg"] == pytest.approx(0.0, abs=1e-12)
    assert seam["bw_v_delta_deg"] == pytest.approx(0.0, abs=1e-12)
    assert len(verify.specs) == len(split_freq_bands(mode_freqs("verify", cfg), [3000.0])) + 1

    screen = _BandRecorder()
    screen_specs = []
    _install_recording(monkeypatch, screen, screen_specs)
    ev2 = evaluate(space.seed, space, cfg, "screen", tmp_path / "screen", None, screen,
                   ctx=_ctx(cfg, None))
    resp2 = load_response(tmp_path / "screen" / "designs" / ev2.design_hash / "response.npz")
    assert "seam_check" not in resp2.meta


# ---- WP14: a cad-route mesh has no grid recipe; the honest echo is `cad`


def test_grid_info_is_honest_about_cad_versus_formula_meta(tmp_path):
    """No mesher/GPU: the meta shape alone decides the grid block and the cad echo."""
    formula = tmp_path / "formula"
    formula.mkdir()
    (formula / "mesh_meta.json").write_text(json.dumps({
        "summary": {"area_m2": 0.25},
        "mesher_config": {"mesh": {"angular_segments": 48, "length_segments": 24}}}))
    area, grid = ev_mod._grid_info(formula)
    assert area == 0.25
    assert grid == {"angular_segments": 48, "length_segments": 24, "available": True}
    assert ev_mod._cad_info(formula) is None

    cad = tmp_path / "cad"
    cad.mkdir()
    (cad / "mesh_meta.json").write_text(json.dumps({
        "summary": {"area_m2": 0.5},
        "cad": {"tool": "multicell", "tool_sha256": "a" * 64, "recipe": {"n_h": 2},
                "step_sha256": "b" * 64, "face_inventory": {"driver": 1, "wall": 9},
                "frequency_validation": {"status": "valid"}}}))
    area, grid = ev_mod._grid_info(cad)
    assert area == 0.5
    assert grid == {"angular_segments": None, "length_segments": None, "available": False}
    assert ev_mod._cad_info(cad) == {
        "tool": "multicell", "tool_sha256": "a" * 64, "recipe": {"n_h": 2},
        "step_sha256": "b" * 64, "face_inventory": {"driver": 1, "wall": 9}}


def _cad_cfg():
    """The WP14 example config at the STEP lane's cheap 2x2 / 2 kHz fixture point."""
    base = load_config(EXAMPLES / "typologies" / "multicell_3x3.yaml")
    return dataclasses.replace(
        base, mesh=dataclasses.replace(base.mesh, epw=10.0),
        target_raw={**base.target_raw, "band_hi_hz": 2000.0})


@requires_build123d
@requires_mesher
def test_cad_row_reports_no_grid_and_carries_the_small_cad_echo(tmp_path):
    """Real CAD + real gmsh mesh (offline, CPU); the solve is the synthetic backend."""
    cfg = _cad_cfg()
    be = SyntheticBackend()
    store = DatasetStore(tmp_path / "ds")
    design = Design("FREEFORM", {"cad": dict(TINY)})
    run = tmp_path / "run"
    ev = evaluate(design, None, cfg, "screen", run, store, be,
                  ctx=_ctx(cfg, store, ndjson=run / "search.ndjson"))
    assert not ev.error, ev.error
    (meta, _arrays) = next(store.iter_records(with_arrays=True))

    grid = meta["mesh"]["grid"]
    assert grid["available"] is False
    assert grid["angular_segments"] is None and grid["length_segments"] is None
    assert meta["mesh"]["area_m2"] > 0.0             # the area still comes from the same meta

    cad = meta["provenance"]["cad"]
    assert set(cad) == set(ev_mod.CAD_ECHO_KEYS)
    assert cad["tool"] == "tools/cad/multicell.py"
    tool = Path(__file__).resolve().parents[1] / "tools" / "cad" / "multicell.py"
    assert cad["tool_sha256"] == hashlib.sha256(tool.read_bytes()).hexdigest()
    assert cad["recipe"] == TINY
    assert len(cad["step_sha256"]) == 64
    assert cad["face_inventory"]["driver"] == 1 and cad["face_inventory"]["wall"] > 0

    disk = json.loads((run / "designs" / ev.design_hash / "mesh_meta.json").read_text(encoding="utf-8"))
    assert cad["step_sha256"] == disk["cad"]["step_sha256"]
    assert cad["face_inventory"] == disk["cad"]["face_inventory"]
    # SMALL: the rest of the block (derived geometry, frequency report) stays on disk
    assert not {"derived", "solid", "frequency_validation"} & set(cad)

    (row,) = read_ndjson(run / "search.ndjson")
    assert row["cad"] == cad

