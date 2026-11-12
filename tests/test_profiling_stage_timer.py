"""WP0: the opt-in stage timer. Offline; no solver."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from hornlab_search import profiling


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv(profiling.ENV_FLAG, raising=False)
    profiling._CURRENT.set(None)
    yield
    profiling._CURRENT.set(None)


def test_disabled_by_default_writes_nothing(tmp_path):
    assert not profiling.enabled()
    tm = profiling.begin(tmp_path, "dh", "k")
    assert tm is None
    with profiling.stage("mesh_build"):
        pass
    profiling.record("x", 1.0)
    assert profiling.end(tm) is None
    assert not (tmp_path / profiling.FILE_NAME).exists()


def test_enabled_records_stages_to_ndjson(tmp_path, monkeypatch):
    monkeypatch.setenv(profiling.ENV_FLAG, "1")
    clock = iter([0.0, 2.5, 3.0, 3.75])
    tm = profiling.begin(tmp_path, "dh", "key")
    tm._clock = lambda: next(clock)
    with profiling.stage("mesh_build"):
        pass
    with profiling.stage("solve", traced=False):
        pass
    profiling.record("solver_path", 0.0, assembly_paths=["fused_cuda"])
    path = profiling.end(tm)
    rows = [json.loads(l) for l in path.read_text().splitlines()]
    assert [r["stage"] for r in rows] == ["mesh_build", "solve", "solver_path"]
    assert rows[0]["seconds"] == pytest.approx(2.5) and rows[1]["seconds"] == pytest.approx(0.75)
    assert rows[2]["assembly_paths"] == ["fused_cuda"] and rows[0]["design_hash"] == "dh"
    # a second candidate appends, never overwrites
    tm2 = profiling.begin(tmp_path, "dh2", "key2")
    profiling.record("candidate_total", 1.0)
    profiling.end(tm2)
    assert len(path.read_text().splitlines()) == 4


def test_stage_time_recorded_even_when_the_block_raises(tmp_path, monkeypatch):
    monkeypatch.setenv(profiling.ENV_FLAG, "true")
    tm = profiling.begin(tmp_path, "dh", "k")
    with pytest.raises(RuntimeError):
        with profiling.stage("solve"):
            raise RuntimeError("boom")
    assert tm.summary()["solve"] >= 0.0 and len(tm.rows) == 1


def test_solver_path_meta_reads_the_response_and_never_raises():
    resp = SimpleNamespace(backend="beat_cuda", n_dof=123, meta={
        "device": "cuda", "cuda_fused": True, "per_frequency_calls": True, "freq_batch_size": 4,
        "vram_baseline_mib": 500, "vram_peak_mib": 4000, "timings": {"assembly": 1.0},
        "native_diagnostics": [{"assembly_path": "fused_cuda"}, {"assembly_path": "fused_cuda"}, None]})
    m = profiling.solver_path_meta(resp)
    assert m["assembly_paths"] == ["fused_cuda"] and m["backend"] == "beat_cuda" and m["cuda_fused"]
    assert profiling.solver_path_meta(object())["assembly_paths"] == []
    assert isinstance(profiling.solver_path_meta(None), dict)


def test_evaluate_writes_stage_timing_when_enabled(smoke_cfg, tmp_path, monkeypatch):
    """End to end through the real evaluate() with the synthetic backend."""
    from test_search_support import LIBS, SyntheticBackend, install_fakes
    from hornlab_search.search import evaluate as ev_mod
    from hornlab_search.design.space import DesignSpace
    monkeypatch.setenv(profiling.ENV_FLAG, "1")
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    space = DesignSpace.from_config(smoke_cfg)
    ctx = ev_mod.make_context(smoke_cfg, None, lib_shas=LIBS)
    ev = ev_mod.evaluate(space.seed, space, smoke_cfg, "screen", tmp_path, None, be, ctx=ctx)
    f = tmp_path / "designs" / ev.design_hash / profiling.FILE_NAME
    stages = [json.loads(l)["stage"] for l in f.read_text().splitlines()]
    for want in ("mesh_build", "solve", "metrics", "score", "persist", "candidate_total"):
        assert want in stages, stages


def test_evaluate_writes_no_timing_file_by_default(smoke_cfg, tmp_path, monkeypatch):
    from test_search_support import LIBS, SyntheticBackend, install_fakes
    from hornlab_search.search import evaluate as ev_mod
    from hornlab_search.design.space import DesignSpace
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    space = DesignSpace.from_config(smoke_cfg)
    ctx = ev_mod.make_context(smoke_cfg, None, lib_shas=LIBS)
    ev = ev_mod.evaluate(space.seed, space, smoke_cfg, "screen", tmp_path, None, be, ctx=ctx)
    assert not (tmp_path / "designs" / ev.design_hash / profiling.FILE_NAME).exists()
