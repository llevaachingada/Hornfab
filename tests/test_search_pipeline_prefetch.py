"""WP2 (throughput packet): opt-in mesh prefetch. Fake mesher + fake solver with real delays.

Proves: (1) default 0 is inert, (2) prefetch gives the SAME rows in the SAME order as the serial
loop, (3) mesh builds really overlap solves, (4) the coordinator thread is the only ndjson writer,
(5) failures / interrupts / budget behave, (6) the build_mesh handoff hook works. No GPU, no mesher.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from hornlab_search.mesh import build as build_mod
from hornlab_search.mesh import prefetch as pf_mod
from hornlab_search.search import cma as cma_mod
from hornlab_search.search import evaluate as ev_mod
from hornlab_search.search.evaluate import read_ndjson
from hornlab_search.search.pipeline import CandidatePipeline
from hornlab_search.types import Design
from test_search_support import LIBS, SyntheticBackend, fake_build_mesh, fast_cfg

BUILD_S = 0.12
SOLVE_S = 0.12


class DelayBackend(SyntheticBackend):
    """Solves from the params the fake mesher wrote next to the mesh (no shared mutable state, so
    a mesh built early for another candidate can never confuse it)."""
    def __init__(self, solve_s=SOLVE_S):
        super().__init__()
        self.solve_s = solve_s
        self.intervals = []

    def _solve(self, mesh, spec):
        self._params = json.loads((Path(mesh.path).parent / "params.json").read_text())
        t0 = time.perf_counter()
        time.sleep(self.solve_s)
        out = super()._solve(mesh, spec)
        self.intervals.append((t0, time.perf_counter()))
        return out


class Mesher:
    def __init__(self, build_s=BUILD_S):
        self.inner = fake_build_mesh()
        self.build_s = build_s
        self.events = []                     # (thread name, t0, t1, design hash)
        self.calls = 0

    def __call__(self, design, mesh_spec, cfg, out_dir, *, mode=None, cache_dir=None):
        # same handoff the real build_mesh performs at its top
        pre = pf_mod.take(build_mod.prebuilt_key(design, mesh_spec, cfg, out_dir, mode))
        if pre is not None:
            return pre
        t0 = time.perf_counter()
        time.sleep(self.build_s)
        res = self.inner(design, mesh_spec, cfg, out_dir, mode=mode, cache_dir=cache_dir)
        (Path(out_dir) / "params.json").write_text(json.dumps(design.params))
        self.calls += 1
        self.events.append((threading.current_thread().name, t0, time.perf_counter(), design.hash()))
        return res


@pytest.fixture
def cfg(smoke_cfg):
    return fast_cfg(smoke_cfg)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    from hornlab_search.solve import worker
    worker.mark_cold()
    monkeypatch.delenv(ev_mod.PREFETCH_ENV, raising=False)
    pf_mod.clear()
    yield
    pf_mod.clear()
    worker.mark_cold()


def _run(cfg, run_dir, monkeypatch, *, depth, budget=12, backend=None, mesher=None):
    mesher = mesher or Mesher()
    backend = backend or DelayBackend()
    monkeypatch.setattr(ev_mod, "build_mesh", mesher)
    if depth:
        monkeypatch.setenv(ev_mod.PREFETCH_ENV, str(depth))
    t0 = time.perf_counter()
    cma_mod.search(cfg, run_dir, "screen", backend=backend, budget=budget, store=None,
                   lib_shas=LIBS)
    return time.perf_counter() - t0, mesher, backend


def _stable(rows):
    return [{k: r.get(k) for k in ("n", "design_hash", "objective", "terms", "cached", "ok",
                                   "mesh_hash", "solve_hash", "key")} for r in rows]


def test_depth_resolution_env_beats_config_and_default_is_zero(cfg, monkeypatch):
    assert ev_mod.prefetch_depth(cfg) == 0
    monkeypatch.setenv(ev_mod.PREFETCH_ENV, "2")
    assert ev_mod.prefetch_depth(cfg) == 2
    monkeypatch.setenv(ev_mod.PREFETCH_ENV, "junk")
    assert ev_mod.prefetch_depth(cfg) == 0


def test_config_field_is_validated_and_defaults_to_zero(smoke_cfg):
    assert smoke_cfg.search.pipeline_prefetch == 0
    import dataclasses
    from hornlab_search.config import load_config
    raw = json.loads(json.dumps(smoke_cfg.raw))
    raw["search"]["pipeline_prefetch"] = -1
    import yaml
    from pathlib import Path as P
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = P(d) / "c.yaml"
        p.write_text(yaml.safe_dump(raw))
        with pytest.raises(Exception, match="pipeline_prefetch"):
            load_config(p)
        raw["search"]["pipeline_prefetch"] = 2
        p.write_text(yaml.safe_dump(raw))
        assert load_config(p).search.pipeline_prefetch == 2
    assert dataclasses.replace(smoke_cfg.search).pipeline_prefetch == 0


def test_prefetch_0_is_inert(cfg, tmp_path, monkeypatch):
    _, mesher, _ = _run(cfg, tmp_path / "r", monkeypatch, depth=0, budget=5)
    assert {e[0] for e in mesher.events} == {threading.current_thread().name}
    assert "pipeline_prefetch" not in json.loads((tmp_path / "r" / "run.json").read_text())


def test_prefetch_gives_identical_rows_in_identical_order_and_overlaps(cfg, tmp_path, monkeypatch):
    t_serial, m0, b0 = _run(cfg, tmp_path / "serial", monkeypatch, depth=0)
    t_pipe, m1, b1 = _run(cfg, tmp_path / "pipe", monkeypatch, depth=2)

    rows0 = read_ndjson(tmp_path / "serial" / "search.ndjson")
    rows1 = read_ndjson(tmp_path / "pipe" / "search.ndjson")
    assert len(rows0) == len(rows1) == 12
    assert _stable(rows0) == _stable(rows1)                       # same designs, same order, same J
    assert [r["n"] for r in rows1] == list(range(12))             # ndjson row numbers contiguous
    assert b0.calls == b1.calls == 12                             # one solve per candidate, no extra

    # every candidate meshed once (no double builds; <= depth extra past the budget cut)
    hashes = [e[3] for e in m1.events]
    assert len(hashes) == len(set(hashes))
    assert {r["design_hash"] for r in rows1} <= set(hashes)
    assert len(hashes) <= 12 + 2                  # at most `depth` wasted past the budget cut
    worker_threads = {e[0] for e in m1.events} - {threading.current_thread().name}
    assert worker_threads and all("prefetch" in t for t in worker_threads)

    # real overlap: at least one prefetch build ran inside a solve window
    pre = [e for e in m1.events if "prefetch" in e[0]]
    assert any(s0 < e1 and e0 < s1 for (_, e0, e1, _) in pre for (s0, s1) in b1.intervals)
    assert t_pipe < t_serial - 0.4, (t_serial, t_pipe)            # and it shows in wall time

    rj = json.loads((tmp_path / "pipe" / "run.json").read_text())
    assert rj["pipeline_prefetch"]["depth"] == 2 and rj["pipeline_prefetch"]["built"] >= 6
    # nothing left parked after the run
    assert pf_mod.parked() == 0


def test_only_the_coordinator_thread_writes_ndjson(cfg, tmp_path, monkeypatch):
    writers = set()
    real = ev_mod.append_ndjson

    def spy(path, row):
        writers.add(threading.current_thread().name)
        return real(path, row)
    monkeypatch.setattr(ev_mod, "append_ndjson", spy)
    _run(cfg, tmp_path / "r", monkeypatch, depth=2, budget=8)
    assert writers == {threading.current_thread().name}


def test_budget_and_resume_with_prefetch_match_serial(cfg, tmp_path, monkeypatch):
    _run(cfg, tmp_path / "u", monkeypatch, depth=0, budget=10)
    _run(cfg, tmp_path / "r", monkeypatch, depth=2, budget=5)
    mesher = Mesher()
    monkeypatch.setattr(ev_mod, "build_mesh", mesher)
    monkeypatch.setenv(ev_mod.PREFETCH_ENV, "2")
    cma_mod.search(cfg, None, "screen", resume=tmp_path / "r", backend=DelayBackend(), budget=5,
                   store=None, lib_shas=LIBS)
    a = read_ndjson(tmp_path / "u" / "search.ndjson")
    b = read_ndjson(tmp_path / "r" / "search.ndjson")
    assert _stable(a) == _stable(b)
    assert not any(r["cached"] for r in b)


def test_mesh_failure_in_prefetch_is_reproduced_by_the_evaluator(cfg, tmp_path, monkeypatch):
    """An invalid geometry raised on the worker is swallowed; the evaluator hits the same error
    on the coordinator and scores the same penalty row as a serial run."""
    inner_invalid = fake_build_mesh(invalid_if=lambda p: float(p["a_deg"]) > 40.0)

    class FailingMesher(Mesher):
        def __init__(self):
            super().__init__()
            self.inner = inner_invalid

    _run(cfg, tmp_path / "s", monkeypatch, depth=0, budget=10, mesher=FailingMesher())
    _run(cfg, tmp_path / "p", monkeypatch, depth=2, budget=10, mesher=FailingMesher())
    a = read_ndjson(tmp_path / "s" / "search.ndjson")
    b = read_ndjson(tmp_path / "p" / "search.ndjson")
    assert any(not r["ok"] for r in a)                      # the scenario really hit failures
    assert _stable(a) == _stable(b)


def test_interrupt_cleans_up_and_leaves_run_resumable(cfg, tmp_path, monkeypatch):
    class Boom(DelayBackend):
        def _solve(self, mesh, spec):
            if self.calls == 3:
                raise KeyboardInterrupt
            return super()._solve(mesh, spec)

    with pytest.raises(KeyboardInterrupt):
        _run(cfg, tmp_path / "r", monkeypatch, depth=2, budget=12, backend=Boom())
    assert pf_mod.parked() == 0
    rj = json.loads((tmp_path / "r" / "run.json").read_text())
    assert rj["status"] == "interrupted"
    # every written ndjson line parses
    for line in (tmp_path / "r" / "search.ndjson").read_text().splitlines():
        json.loads(line)


def test_pipeline_unit_waits_before_evaluating_and_dedupes(cfg):
    order = []

    def fn(design, *_a):
        time.sleep(0.05)
        order.append(design.hash())
        return True

    ds = [Design("OSSE", {"a": i}) for i in range(3)]
    pipe = CandidatePipeline(cfg, "screen", ".", None, depth=2, prefetch_fn=fn)
    pipe.begin_generation(ds + [ds[1]])
    pipe.before(0)                      # queues 1 and 2
    pipe.before(1)                      # waits for 1
    assert ds[1].hash() in order
    pipe.before(2)
    pipe.close()
    assert order.count(ds[1].hash()) == 1 and pipe.stats()["built"] == 2


def test_main_thread_error_disables_the_prefetcher(cfg, caplog):
    def fn(*_a):
        raise ValueError("signal only works in main thread")
    pipe = CandidatePipeline(cfg, "screen", ".", None, depth=2, prefetch_fn=fn)
    pipe.begin_generation([Design("OSSE", {"a": i}) for i in range(3)])
    pipe.before(0)
    pipe.before(1)
    assert pipe.stats()["disabled"] is True
    pipe.close()


def test_real_build_mesh_returns_a_parked_mesh_before_touching_the_mesher(cfg):
    design = Design("OSSE", dict(cfg.seed_params))
    from hornlab_search import config as config_mod
    mspec = config_mod.mesh_spec("screen", cfg)
    sentinel = object()
    pf_mod.put(build_mod.prebuilt_key(design, mspec, cfg, "/tmp/x", "screen"), sentinel)
    assert build_mod.build_mesh(design, mspec, cfg, Path("/tmp/x"), mode="screen") is sentinel
    assert pf_mod.parked() == 0                                       # popped: single use
    # a different dir or mode never matches
    pf_mod.put(build_mod.prebuilt_key(design, mspec, cfg, "/tmp/x", "screen"), sentinel)
    assert pf_mod.take(build_mod.prebuilt_key(design, mspec, cfg, "/tmp/y", "screen")) is None
    assert pf_mod.take(build_mod.prebuilt_key(design, mspec, cfg, "/tmp/x", "verify")) is None


def test_cma_me_with_prefetch_matches_serial(smoke_cfg, tmp_path, monkeypatch):
    """CMA-ME is wired the same way; the stand-in evaluator never meshes, so every prefetch
    attempt fails harmlessly and the ask/tell order must still be identical."""
    pytest.importorskip("ribs", reason="ribs not installed")
    from test_search_cma_me import knob_eval, qd_block, qd_mod, run_qd, two_knob_cfg
    cfg_me = two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=6, bins_v=6))
    seen0, seen1 = [], []
    monkeypatch.setattr(qd_mod, "evaluate", knob_eval(cfg_me, seen0))
    run_qd(cfg_me, tmp_path / "a", 24)
    monkeypatch.setattr(qd_mod, "evaluate", knob_eval(cfg_me, seen1))
    monkeypatch.setenv(ev_mod.PREFETCH_ENV, "2")
    run_qd(cfg_me, tmp_path / "b", 24)
    assert seen0 == seen1 and len(seen0) == 24
