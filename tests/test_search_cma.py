"""Tests 12-18b of 08_TASK_PIPELINE: the CMA-ES loop with a mocked evaluator or a synthetic
backend. No GPU, no mesher, no solver."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.dataset.record import should_capture_traces
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.design.space import DesignSpace
from hornlab_search.search import cma as cma_mod
from hornlab_search.search.evaluate import read_ndjson
from hornlab_search.types import Design, Evaluation, SolveOutcome
from test_search_support import LIBS, SyntheticBackend, fast_cfg, install_fakes


def run(cfg, run_dir, backend, store, budget, **kw):
    return cma_mod.search(cfg, run_dir, "screen", backend=backend, budget=budget, store=store,
                          lib_shas=LIBS, **kw)


def analytic_eval(log=None):
    """A drop-in for ``evaluate``: J is a smooth bowl in the design parameters."""
    def fake(design, space, cfg, mode, run_dir, store, backend, **kw):
        p = design.params
        j = (((p["a_deg"] - 32.0) / 10.0) ** 2 + ((p["n"] - 5.0) / 3.0) ** 2
             + ((p["L_mm"] - 300.0) / 100.0) ** 2 + (p["aspect_ratio"] - 1.5) ** 2)
        if log is not None:
            log.append(design.hash())
        return Evaluation(design_hash=design.hash(), design=design, mesh_hash="m", solve_hash="s",
                          objective=float(j), terms={"total": float(j)}, metrics=None, mesh=None,
                          outcome=SolveOutcome(True, None, 0.0, None, ""), cached=False, error="")
    return fake


@pytest.fixture
def cfg(smoke_cfg):
    return fast_cfg(smoke_cfg)


@pytest.fixture(autouse=True)
def _cold_worker_state():
    """worker.warm() is idempotent per process; start every test cold so 'warmed once' is real."""
    from hornlab_search.solve import worker
    worker.mark_cold()
    yield
    worker.mark_cold()


# 12
def test_cma_reduces_the_objective_over_60_evaluations(cfg, tmp_path, monkeypatch):
    monkeypatch.setattr(cma_mod, "evaluate", analytic_eval())
    seen = []
    base = analytic_eval(seen)
    monkeypatch.setattr(cma_mod, "evaluate", base)
    be = SyntheticBackend()
    best = run(cfg, tmp_path / "r", be, None, 60)
    seed_j = base(Design("OSSE", dict(cfg.seed_params)), None, cfg, "screen", None, None, None).objective
    assert best.objective < 0.5 * seed_j
    assert len(seen) == 61                                  # seed + 59 candidates + the helper call above
    assert be.warmed == 1                                   # warm() once, before the seed
    bj = json.loads((tmp_path / "r" / "best.json").read_text())
    assert bj["objective"] == pytest.approx(best.objective)


# 13
def test_same_seed_gives_the_identical_sequence_of_designs(cfg, tmp_path, monkeypatch):
    seqs = []
    for i in range(2):
        seen = []
        monkeypatch.setattr(cma_mod, "evaluate", analytic_eval(seen))
        run(cfg, tmp_path / f"r{i}", SyntheticBackend(), None, 40)
        seqs.append(seen)
    assert seqs[0] == seqs[1] and len(seqs[0]) == 40 and len(set(seqs[0])) == 40
    seen = []
    monkeypatch.setattr(cma_mod, "evaluate", analytic_eval(seen))
    other = fast_cfg(cfg, seed=cfg.search.seed + 1)
    run(other, tmp_path / "r2", SyntheticBackend(), None, 40)
    assert seen != seqs[0]


# 14
def test_budget_25_gives_exactly_25_non_cached_evaluations(cfg, tmp_path, monkeypatch):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    store = DatasetStore(tmp_path / "ds")
    run(cfg, tmp_path / "r", be, store, 25)
    rows = read_ndjson(tmp_path / "r" / "search.ndjson")
    assert len(rows) == 25 and not any(r["cached"] for r in rows)
    assert be.calls == 25
    stats = json.loads((tmp_path / "r" / "run.json").read_text())["stats"]
    assert stats["non_cached"] == 25 and stats["evaluations"] == 25


def test_cached_hits_do_not_consume_budget(cfg, tmp_path, monkeypatch):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    store = DatasetStore(tmp_path / "ds")
    run(cfg, tmp_path / "r", be, store, 12)
    be2 = SyntheticBackend()
    install_fakes(monkeypatch, be2)
    run(cfg, tmp_path / "r", be2, store, 3)                 # resume: 12 replayed free + 3 new
    assert be2.calls == 3
    assert len(read_ndjson(tmp_path / "r" / "search.ndjson")) == 15
    assert len(store) == 15
    run_json = json.loads((tmp_path / "r" / "run.json").read_text())
    assert run_json["stats"]["evaluations"] == 15 and run_json["stats"]["non_cached"] == 15   # cumulative
    assert run_json["last_invocation"]["non_cached"] == 3 and run_json["last_invocation"]["cache_hits"] == 12
    assert len(run_json["resumes"]) == 1


def test_max_evals_counts_cached_hits_too(cfg, tmp_path, monkeypatch):
    """Campaign fairness: with max_evals, a replayed CMA seed cannot get its cached prefix for free."""
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    store = DatasetStore(tmp_path / "ds")
    run(cfg, tmp_path / "r", be, store, 12)
    be2 = SyntheticBackend()
    install_fakes(monkeypatch, be2)
    run(cfg, tmp_path / "r", be2, store, 10, max_evals=15)   # 12 replayed + at most 3 new
    assert be2.calls == 3
    run_json = json.loads((tmp_path / "r" / "run.json").read_text())
    assert run_json["last_invocation"]["evaluations"] == 15


# 15
def test_resume_performs_zero_solves_for_finished_work_and_matches_an_uninterrupted_run(
        cfg, tmp_path, monkeypatch):
    # uninterrupted 40
    be_u = SyntheticBackend()
    install_fakes(monkeypatch, be_u)
    best_u = run(cfg, tmp_path / "u", be_u, DatasetStore(tmp_path / "dsu"), 40)

    # 20, "kill", resume for 20 more
    be1 = SyntheticBackend()
    install_fakes(monkeypatch, be1)
    ds = DatasetStore(tmp_path / "ds")
    run(cfg, tmp_path / "r", be1, ds, 20)
    first = list(be1.designs)
    assert be1.calls == 20 and len(first) == 20

    be2 = SyntheticBackend()
    install_fakes(monkeypatch, be2)
    best_r = run(cfg, tmp_path / "r", be2, DatasetStore(tmp_path / "ds"), 20, resume=tmp_path / "r")
    assert not (set(first) & set(be2.designs)), "a finished evaluation was solved again"
    assert be2.calls == 20
    assert best_r.design_hash == best_u.design_hash
    assert best_r.objective == best_u.objective
    assert len(read_ndjson(tmp_path / "r" / "search.ndjson")) == 40
    # an uninterrupted continuation: the candidate sequence is the same one
    ru = [r["design_hash"] for r in read_ndjson(tmp_path / "u" / "search.ndjson")]
    rr = [r["design_hash"] for r in read_ndjson(tmp_path / "r" / "search.ndjson")]
    assert ru == rr


def test_rerunning_the_same_config_with_a_finished_budget_does_zero_new_work(
        cfg, tmp_path, monkeypatch):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    run(cfg, tmp_path / "r", be, DatasetStore(tmp_path / "ds"), 15)
    be2 = SyntheticBackend()
    install_fakes(monkeypatch, be2)
    run(cfg, tmp_path / "r", be2, DatasetStore(tmp_path / "ds"), 0)
    assert be2.calls == 0 and be2.designs == []


# 16
def test_one_candidate_raising_does_not_stop_the_loop(cfg, tmp_path, monkeypatch):
    be = SyntheticBackend(fail_on={4: RuntimeError("boom-from-the-solver"), 6: "fail"})
    install_fakes(monkeypatch, be)
    store = DatasetStore(tmp_path / "ds")
    run(cfg, tmp_path / "r", be, store, 15)
    rows = read_ndjson(tmp_path / "r" / "search.ndjson")
    assert len(rows) == 15 and be.calls == 15
    exc_rows = [r for r in rows if r["kind"] == "exception"]
    assert len(exc_rows) == 1
    assert "boom-from-the-solver" in exc_rows[0]["error"] and "Traceback" in exc_rows[0]["error"]
    assert exc_rows[0]["objective"] == 1000.0 and np.isfinite(exc_rows[0]["objective"])
    assert [r["kind"] for r in rows].count("solve_failed") == 1
    # the traceback also landed in the dataset record
    rec = [m for m, _ in store.iter_records() if m["design_hash"] == exc_rows[0]["design_hash"]][0]
    assert rec["ok"] is False and "boom-from-the-solver" in rec["error"]
    assert all(np.isfinite(r["objective"]) for r in rows)


def test_penalties_are_finite_for_invalid_and_oversize_designs(cfg, tmp_path, monkeypatch):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be, invalid_if=lambda p: p["a_deg"] > 40.0,
                  too_large_if=lambda p: p["L_mm"] > 330.0 and p["a_deg"] <= 40.0)
    store = DatasetStore(tmp_path / "ds")
    run(cfg, tmp_path / "r", be, store, 30)
    rows = read_ndjson(tmp_path / "r" / "search.ndjson")
    kinds = {r["kind"] for r in rows}
    assert {"invalid_geometry", "mesh_too_large"} <= kinds
    assert all(np.isfinite(r["objective"]) and r["objective"] <= 1000.0 + 1e-9 for r in rows)
    assert len(store) == len(rows)
    for m, _ in store.iter_records():
        assert m["ok"] or m["error"]


# 17
def test_hard_kill_leaves_every_ndjson_line_parseable(cfg, tmp_path, monkeypatch):
    be = SyntheticBackend(fail_on={9: KeyboardInterrupt()})
    install_fakes(monkeypatch, be)
    with pytest.raises(KeyboardInterrupt):
        run(cfg, tmp_path / "r", be, DatasetStore(tmp_path / "ds"), 30)
    p = tmp_path / "r" / "search.ndjson"
    raw = p.read_bytes()
    assert raw.endswith(b"\n")
    lines = raw.decode().splitlines()
    assert len(lines) == 8 and all(json.loads(l)["design_hash"] for l in lines)
    assert json.loads((tmp_path / "r" / "run.json").read_text())["status"] == "interrupted"
    # a torn tail (power cut mid-write) is skipped, not fatal, and the run can resume over it
    with open(p, "ab") as f:
        f.write(b'{"n": 8, "key": "abc", "design_h')
    assert len(read_ndjson(p)) == 8
    be2 = SyntheticBackend()
    install_fakes(monkeypatch, be2)
    run(cfg, tmp_path / "r", be2, DatasetStore(tmp_path / "ds"), 2)
    assert be2.calls == 2


# 18
def test_every_evaluation_including_failures_has_exactly_one_dataset_record(cfg, tmp_path, monkeypatch):
    be = SyntheticBackend(fail_on={3: "fail", 5: RuntimeError("x")})
    install_fakes(monkeypatch, be, invalid_if=lambda p: p["s"] > 0.95)
    store = DatasetStore(tmp_path / "ds")
    run(cfg, tmp_path / "r", be, store, 40)
    rows = read_ndjson(tmp_path / "r" / "search.ndjson")
    assert len(store) == len(rows) == 40
    assert len(set(e["design_hash"] for e in store.index)) == 40
    assert store.stats()["n_failed"] >= 2
    bad = store.index
    assert sum(1 for e in bad if not e["ok"]) == sum(1 for r in rows if not r["ok"])


# 18b
def test_trace_sampling_is_deterministic_and_close_to_the_configured_rate(cfg, tmp_path, monkeypatch):
    space = DesignSpace.from_config(cfg)
    rng = np.random.default_rng(0)
    hashes = [space.denormalize(rng.random(len(space.keys()))).hash() for _ in range(200)]
    a = [should_capture_traces(h, 0.05) for h in hashes]
    b = [should_capture_traces(h, 0.05) for h in hashes]
    assert a == b
    assert 0.7 * 10 <= sum(a) <= 1.3 * 10, sum(a)           # 5% of 200 = 10, within 30%
    # the same config run twice captures traces for the same designs
    caught = []
    for i in range(2):
        be = SyntheticBackend()
        install_fakes(monkeypatch, be)
        store = DatasetStore(tmp_path / f"ds{i}")
        run(cfg, tmp_path / f"r{i}", be, store, 30, trace_fraction=0.3)
        caught.append(sorted(m["design_hash"] for m, _ in store.iter_records()
                             if m["traces"]["captured"]))
        assert be.traced_calls >= len(caught[-1])              # failed solves are traced too
    assert caught[0] == caught[1] and len(caught[0]) >= 3
    for m, _ in store.iter_records():
        assert m["traces"]["sample_fraction"] == 0.3
        if m["traces"]["captured"]:
            assert (tmp_path / "ds1" / m["traces"]["path"]).exists()
    assert not any(m["traces"]["captured"] for m, _ in store.iter_records() if not m["ok"])


def test_a_zero_budget_resume_never_overwrites_best_json_with_something_worse(cfg, tmp_path, monkeypatch):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    store = DatasetStore(tmp_path / "ds")
    best = run(cfg, tmp_path / "r", be, store, 25)
    seed_j = read_ndjson(tmp_path / "r" / "search.ndjson")[0]["objective"]
    assert best.objective < seed_j
    be2 = SyntheticBackend()
    install_fakes(monkeypatch, be2)
    run(cfg, tmp_path / "r", be2, store, 0, resume=tmp_path / "r")
    bj = json.loads((tmp_path / "r" / "best.json").read_text())
    assert bj["objective"] == pytest.approx(best.objective) and bj["design_hash"] == best.design_hash
    rj = json.loads((tmp_path / "r" / "run.json").read_text())
    assert rj["best"]["objective"] == pytest.approx(best.objective)
