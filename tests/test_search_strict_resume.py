"""F0 (day 2026-11-12): strict plain-CMA refusal isolation, same-candidate retry and checkpoint.

All fake-backend/no-GPU. Tell is spied on the real pycma ES instance; assertions are on the actual
told vectors/scores and on the ``cma/strict_state.json`` artifact, not on module comments.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.config import ConfigError
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.search import cma as cma_mod
from hornlab_search.search import evaluate as ev_mod
from hornlab_search.search.evaluate import read_ndjson
from test_search_support import LIBS, SyntheticBackend, fast_cfg, install_fakes

STRICT = {"infeasible_penalty": "resample_strict",
          "error_policy": "retry_same_then_stop", "budget_counts": "valid"}


@pytest.fixture
def es_spy(monkeypatch):
    rec = SimpleNamespace(instances=[])
    real = cma_mod.cma_lib.CMAEvolutionStrategy

    class Spy(real):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.tell_calls = []
            inner = self.tell

            def tell(X, F):
                self.tell_calls.append(([np.asarray(x, dtype=float).copy() for x in X],
                                        [float(v) for v in F]))
                return inner(X, F)

            self.tell = tell
            rec.instances.append(self)

    monkeypatch.setattr(cma_mod.cma_lib, "CMAEvolutionStrategy", Spy)
    return rec


def _run(cfg, rd, be, *, budget, resume=None, cache_dir=None):
    return cma_mod.search(cfg, rd, "screen", resume=resume, backend=be, budget=budget,
                          store=DatasetStore(rd / "ds"), lib_shas=LIBS, cache_dir=cache_dir)


def _run_json(rd):
    return json.loads((rd / "run.json").read_text())


def _strict_json(rd):
    return json.loads((rd / "cma" / "strict_state.json").read_text())


# ------------------------------------------------------------------ deterministic refusals

def test_strict_replaces_refusals_and_never_tells_a_penalty(smoke_cfg, tmp_path, monkeypatch,
                                                            es_spy):
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=40, **STRICT)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be, invalid_if=lambda p: p["a_deg"] > 45)
    rd = tmp_path / "r"
    cma_mod.search(cfg, rd, "screen", backend=be, budget=1000,
                   store=DatasetStore(rd / "ds"), lib_shas=LIBS)
    rj = _run_json(rd)
    st = rj["strict"]
    assert st["refusals"] > 0, "deterministic refusals were evaluated (and logged) but replaced"
    assert st["replacements"] == st["refusals"], "each told slot came from a replacement draw"
    assert st["told"] > 0 and es_spy.instances[-1].tell_calls
    assert all(f < 1000.0 for _, F in es_spy.instances[-1].tell_calls for f in F), \
        "a strict tell must never carry the refusal penalty"
    assert st["stop_reason"] in ("strict_draw_cap", "budget")


def test_all_refusing_slot_stops_without_telling(smoke_cfg, tmp_path, monkeypatch, es_spy):
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=3, **STRICT)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be, invalid_if=lambda p: True)
    rd = tmp_path / "r"
    best = _run(cfg, rd, be, budget=1000)
    rj = _run_json(rd)
    rows = read_ndjson(rd / "search.ndjson")
    assert best is None, "no eligible score exists"
    assert es_spy.instances[-1].tell_calls == [], "an all-refused/partial batch must not be told"
    assert "best" not in rj
    assert rj["strict"]["stop_reason"] in ("strict_refused_slot", "strict_draw_cap")
    assert all(r["kind"] == "invalid_geometry" for r in rows)
    assert rj["strict"]["draws"] == 3


def test_final_valid_slot_cap_tells_the_complete_batch_once(smoke_cfg, tmp_path, monkeypatch,
                                                            es_spy):
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=9, **STRICT)   # seed + two full gens
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / "r"
    _run(cfg, rd, be, budget=1000)
    rj = _run_json(rd)
    tells = es_spy.instances[-1].tell_calls
    assert len(tells) == 2 and all(len(F) == 4 for _, F in tells)
    assert all(f < 1000.0 for _, F in tells for f in F)
    assert rj["strict"]["draws"] == 9 and rj["strict"]["told"] == 8
    assert rj["strict"]["stop_reason"] == "strict_draw_cap"
    assert rj["best"] is not None


def test_cached_seed_does_not_consume_strict_budget(smoke_cfg, tmp_path, monkeypatch, es_spy):
    """A cache hit is free: it consumes a draw but not n_new/n_valid/attempts."""
    cache = tmp_path / "cache"
    warm = SyntheticBackend()
    install_fakes(monkeypatch, warm)
    warm_rd = tmp_path / "warm"
    cma_mod.search(smoke_cfg, warm_rd, "screen", backend=warm, budget=1,
                   store=DatasetStore(warm_rd / "ds"), lib_shas=LIBS, cache_dir=cache)
    assert warm.calls == 1

    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=4, **STRICT)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / "strict"
    _run(cfg, rd, be, budget=1, cache_dir=cache)
    rj = _run_json(rd)
    st = rj["strict"]
    assert st["draws"] == 2, "the cached seed still consumes one draw, plus the new candidate"
    assert st["attempts"] == 1, "only the non-cached candidate is a new attempt"
    assert st["valid"] == 1, "the cached seed must not consume the valid budget"
    assert st["told"] == 0
    assert be.calls == 1, "the cached seed is free; only the new candidate reaches the backend"


def test_cached_refusal_loop_is_counted_and_capped(smoke_cfg, tmp_path, monkeypatch, es_spy):
    cache = tmp_path / "cache"
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=2, **STRICT)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be, invalid_if=lambda p: True)
    rd = tmp_path / "r"
    _run(cfg, rd, be, budget=1000, cache_dir=cache)
    assert es_spy.instances[-1].tell_calls == []

    cfg2 = fast_cfg(smoke_cfg, popsize=4, max_attempts=3, **STRICT)   # explicit extension
    be2 = SyntheticBackend()
    install_fakes(monkeypatch, be2, invalid_if=lambda p: True)
    _run(cfg2, rd, be2, budget=1000, resume=rd, cache_dir=cache)
    rj = _run_json(rd)
    st = rj["strict"]
    assert [e["cap"] for e in st["extensions"]] == ["draws"]
    assert st["cached_refusals"] >= 1, "a cached refusal still consumes a strict draw"
    assert st["draws"] == 3
    assert st["stop_reason"] in ("strict_refused_slot", "strict_draw_cap")
    assert es_spy.instances[-1].tell_calls == []


# ------------------------------------------------------------------ infrastructure retry/stop

def test_transient_failure_retries_the_same_candidate_then_succeeds(smoke_cfg, tmp_path,
                                                                   monkeypatch, es_spy):
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=5, **STRICT)
    be = SyntheticBackend(fail_on={2: "fail"})      # call 2 = first gen slot 0
    install_fakes(monkeypatch, be)
    rd = tmp_path / "r"
    _run(cfg, rd, be, budget=1000)
    rj = _run_json(rd)
    tells = es_spy.instances[-1].tell_calls
    assert len(tells) == 1 and len(tells[0][1]) == 4, "told only when the batch is complete"
    assert rj["strict"]["retries"] == 1
    assert rj["strict"]["backend_calls"] == 6          # seed + 2 for slot0 + 3 others
    assert be.calls == 6
    # the retry re-solved the SAME design (the fake records each build's design hash)
    assert be.designs[1] == be.designs[2]


def test_persistent_transient_stops_before_tell(smoke_cfg, tmp_path, monkeypatch, es_spy):
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=5, **STRICT)
    be = SyntheticBackend(fail_on={2: "fail", 3: "fail"})
    install_fakes(monkeypatch, be)
    rd = tmp_path / "r"
    best = _run(cfg, rd, be, budget=1000)
    rj = _run_json(rd)
    assert es_spy.instances[-1].tell_calls == [], "no tell, so covariance is untouched"
    assert rj["strict"]["stop_reason"] == "strict_infrastructure"
    assert rj["strict"]["retries"] == 1 and rj["strict"]["backend_calls"] == 3
    assert be.calls == 3
    assert best is not None and best.design_hash == rj["seed"]["design_hash"], \
        "the valid seed remains best; the failure is not promoted"


def test_unknown_error_stops_diagnostically(smoke_cfg, tmp_path, monkeypatch, es_spy):
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=5, **STRICT)
    be = SyntheticBackend(fail_on={2: ValueError("boom")})
    install_fakes(monkeypatch, be)
    rd = tmp_path / "r"
    _run(cfg, rd, be, budget=1000)
    rj = _run_json(rd)
    assert rj["strict"]["stop_reason"] == "strict_unknown_error"
    assert rj["strict"]["unknown_attempts"] == 1
    assert es_spy.instances[-1].tell_calls == []


def test_metric_error_stops_diagnostically(smoke_cfg, tmp_path, monkeypatch, es_spy):
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=5, **STRICT)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)

    def _boom(*a, **k):
        raise RuntimeError("metric pipeline exploded")

    monkeypatch.setattr(ev_mod, "metrics_from_response", _boom)
    rd = tmp_path / "r"
    _run(cfg, rd, be, budget=1000)
    rj = _run_json(rd)
    assert rj["strict"]["stop_reason"] == "strict_metric_error"
    assert rj["strict"]["seed"]["category"] == "metric_error"
    assert es_spy.instances[-1].tell_calls == []


def test_seed_refusal_is_the_failed_baseline(smoke_cfg, tmp_path, monkeypatch, es_spy):
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=3, **STRICT)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be, invalid_if=lambda p: True)
    rd = tmp_path / "r"
    _run(cfg, rd, be, budget=1000)
    rj = _run_json(rd)
    rows = read_ndjson(rd / "search.ndjson")
    assert rj["strict"]["seed"]["eligible"] is False
    assert rj["strict"]["seed"]["category"] == "geometry_refusal"
    assert rj["strict"]["seed"]["design_hash"] == rows[0]["design_hash"], \
        "the refused seed is recorded, not replaced by another baseline"
    assert "best" not in rj


def test_error_policy_only_retries_infrastructure_with_legacy_budget(smoke_cfg, tmp_path,
                                                                     monkeypatch, es_spy):
    # ``error_policy`` is allowed without strict deterministic resampling; budget_counts stays new.
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=6, budget_counts="new",
                   error_policy="retry_same_then_stop")
    be = SyntheticBackend(fail_on={2: "fail"})
    install_fakes(monkeypatch, be)
    rd = tmp_path / "r"
    _run(cfg, rd, be, budget=1000)
    rj = _run_json(rd)
    assert rj["strict"]["retries"] == 1
    # seed + 2 for slot0 (fail + same-candidate retry) + 3 others + 1 into the partial next gen
    assert rj["strict"]["backend_calls"] == 7
    assert rj["strict"]["stop_reason"] == "strict_draw_cap"
    assert rj["strict"]["told"] == 4


def test_final_refused_slot_in_a_mixed_batch_is_not_told(smoke_cfg, tmp_path, monkeypatch,
                                                         es_spy):
    # seed + slots 0..3 consume the cap; the LAST slot is the one refused, so the mixed batch is
    # incomplete and must not be told (distinct from the final-valid-slot cap above).
    calls = {"n": 0}

    def invalid_on_fifth(params):
        calls["n"] += 1
        return calls["n"] == 5          # seed=1; slots 2,3,4 ok; slot index 3 (5th) refused

    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=5, **STRICT)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be, invalid_if=invalid_on_fifth)
    rd = tmp_path / "r"
    _run(cfg, rd, be, budget=1000)
    rj = _run_json(rd)
    assert es_spy.instances[-1].tell_calls == []
    assert rj["strict"]["stop_reason"] in ("strict_refused_slot", "strict_draw_cap")
    assert rj["strict"]["told"] == 0


def test_healthy_and_transient_runs_tell_the_same_vectors(smoke_cfg, tmp_path, monkeypatch,
                                                          es_spy):
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=9, **STRICT)
    rd_ok = tmp_path / "ok"
    be_ok = SyntheticBackend()
    install_fakes(monkeypatch, be_ok)
    _run(cfg, rd_ok, be_ok, budget=1000)
    ok_tells = es_spy.instances[-1].tell_calls

    rd_bad = tmp_path / "bad"
    be_bad = SyntheticBackend(fail_on={2: "fail"})     # one recovery, same protocol
    install_fakes(monkeypatch, be_bad)
    _run(cfg, rd_bad, be_bad, budget=1000)
    bad_tells = es_spy.instances[-1].tell_calls

    assert len(ok_tells) == len(bad_tells) == 2
    for (xv_ok, f_ok), (xv_bad, f_bad) in zip(ok_tells, bad_tells):
        assert f_ok == f_bad
        for a, b in zip(xv_ok, xv_bad):
            assert np.allclose(a, b)
    assert be_ok.calls == 9 and be_bad.calls == 10      # different cost ledger, same learning
    assert _run_json(rd_bad)["strict"]["retries"] == 1


# ------------------------------------------------------------------ checkpoint / resume

def test_resume_preserves_counters_and_records_an_explicit_extension(smoke_cfg, tmp_path,
                                                                     monkeypatch, es_spy):
    cfg1 = fast_cfg(smoke_cfg, popsize=4, max_attempts=9, **STRICT)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / "r"
    _run(cfg1, rd, be, budget=1000)
    st1 = _strict_json(rd)
    assert st1["boundary"]["draws"] == 9 and st1["boundary"]["told"] == 8
    calls_before = be.calls

    cfg2 = fast_cfg(smoke_cfg, popsize=4, max_attempts=17, **STRICT)   # explicit extension
    be2 = SyntheticBackend()
    install_fakes(monkeypatch, be2)
    _run(cfg2, rd, be2, budget=1000, resume=rd)
    st2 = _strict_json(rd)
    assert st2["boundary"]["draws"] == 17 and st2["boundary"]["told"] == 16
    assert st2["extensions"] == [{"cap": "draws", "from": 9, "to": 17}]
    assert be2.calls == 8, "the cached prefix replays free; only the 8 new candidates solve"
    assert calls_before == 9
    # The resume re-asks/tells the already-counted prefix (needed to rebuild the ES covariance) and
    # then tells the 2 new generations. Counters must stay at 16 told, not 24.
    assert len(es_spy.instances) == 2
    assert len(es_spy.instances[0].tell_calls) == 2
    assert len(es_spy.instances[1].tell_calls) == 4


def test_resume_without_extension_stops_at_the_preserved_cap(smoke_cfg, tmp_path, monkeypatch,
                                                             es_spy):
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=5, **STRICT)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / "r"
    _run(cfg, rd, be, budget=1000)
    st1 = _strict_json(rd)
    be2 = SyntheticBackend()
    install_fakes(monkeypatch, be2)
    _run(cfg, rd, be2, budget=1000, resume=rd)
    st2 = _strict_json(rd)
    assert st2["boundary"]["draws"] == st1["boundary"]["draws"] == 5
    assert st2["boundary"]["told"] == st1["boundary"]["told"]
    assert be2.calls == 0, "a capped resume solves nothing"
    # The one replayed generation is re-told ONLY to rebuild the fresh ES covariance; the told
    # counter is preserved (not reset, not doubled) and no additional batch is told after the cap.
    assert len(es_spy.instances[-1].tell_calls) == 1
    assert st2["boundary"]["told"] == 4


def test_incompatible_protocol_refuses_resume(smoke_cfg, tmp_path, monkeypatch, es_spy):
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=5, **STRICT)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / "r"
    _run(cfg, rd, be, budget=1000)
    p = rd / "cma" / "strict_state.json"
    data = json.loads(p.read_text())
    data["identity"]["protocol"] = "other-protocol"
    data["protocol"] = "other-protocol"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ConfigError, match="strict resume"):
        _run(cfg, rd, SyntheticBackend(), budget=1000, resume=rd)


def test_missing_strict_artifact_refuses_resume_on_a_run_with_history(smoke_cfg, tmp_path,
                                                                      monkeypatch, es_spy):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / "legacy"
    # a legacy (non-strict) run leaves search.ndjson but no cma/strict_state.json
    cma_mod.search(smoke_cfg, rd, "screen", backend=be, budget=3,
                   store=DatasetStore(rd / "ds"), lib_shas=LIBS)
    assert read_ndjson(rd / "search.ndjson")
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=5, **STRICT)
    with pytest.raises(ConfigError, match="strict_state.json"):
        _run(cfg, rd, SyntheticBackend(), budget=1000, resume=rd)


def test_shrinking_a_cumulative_cap_refuses_resume(smoke_cfg, tmp_path, monkeypatch, es_spy):
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=9, **STRICT)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / "r"
    _run(cfg, rd, be, budget=1000)
    cfg2 = fast_cfg(smoke_cfg, popsize=4, max_attempts=5, **STRICT)
    with pytest.raises(ConfigError, match="shrink"):
        _run(cfg2, rd, SyntheticBackend(), budget=1000, resume=rd)


def test_strict_stop_closes_the_pipeline_and_never_dispatches(smoke_cfg, tmp_path, monkeypatch,
                                                              es_spy):
    class FakePipe:
        instances: list = []

        def __init__(self, *a, **k):
            self.enabled = False
            self.closed = 0
            self.before_calls = 0
            FakePipe.instances.append(self)

        def begin_generation(self, designs):
            pass

        def before(self, i):
            self.before_calls += 1

        def stats(self):
            return {}

        def close(self):
            self.closed += 1

    monkeypatch.setattr(cma_mod, "CandidatePipeline", FakePipe)
    cfg = fast_cfg(smoke_cfg, popsize=4, max_attempts=3, **STRICT)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be, invalid_if=lambda p: True)
    rd = tmp_path / "r"
    _run(cfg, rd, be, budget=1000)
    assert FakePipe.instances[-1].closed == 1
    assert FakePipe.instances[-1].before_calls == 0
    assert es_spy.instances[-1].tell_calls == []
