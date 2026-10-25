"""WP11a: CMA-ES restarts (IPOP/BIPOP) — ``search.restarts: {mode, max}``.

Offline, no GPU, no mesher, no solver: the same fakes as ``test_search_cma.py`` (a synthetic backend
whose Response depends smoothly on the design, or an analytic bowl dropped in for ``evaluate``).

The absent-key test is the bit-for-bit regression net for the single-ES path; the restart tests pin
the budget semantics (``n_new`` counts NON-CACHED evaluations across ALL restarts, so a run always
stops at exactly the budget), the per-restart pycma log prefixes, and the deterministic resume.
"""
from __future__ import annotations

import ast
import dataclasses
import json

import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.config import ConfigError, load_config, solve_spec
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.search import cma as cma_mod
from hornlab_search.search.evaluate import read_ndjson
from hornlab_search.types import Evaluation, SolveOutcome
from test_search_support import LIBS, SyntheticBackend, fast_cfg, install_fakes

# pycma's tolfun stops an ES when both the current and the historic fitness range are below it.
# On the analytic bowl every generation's range is O(1), so this forces a natural stop after ONE
# generation: each restart then costs exactly one population, which makes the budgets predictable.
TOLFUN_FORCES_STOP = 1e9


def restart_cfg(smoke, restarts, tolfun=TOLFUN_FORCES_STOP):
    """The smoke config with a ``search.restarts`` block (and no explicit popsize)."""
    s = dataclasses.replace(smoke.search, tolfun=tolfun, popsize=None, restarts=restarts)
    return dataclasses.replace(smoke, search=s)


def bowl_eval(log=None):
    """A drop-in for ``evaluate``: J is a smooth bowl in the design parameters (as in test 12)."""
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


def run(cfg, run_dir, backend, store, budget, **kw):
    return cma_mod.search(cfg, run_dir, "screen", backend=backend, budget=budget, store=store,
                          lib_shas=LIBS, **kw)


def run_json(run_dir):
    return json.loads((run_dir / "run.json").read_text(encoding="utf-8"))


def restart_dirs(run_dir):
    cma_dir = run_dir / "cma"
    return sorted(p.name for p in cma_dir.iterdir() if p.is_dir())


# ------------------------------------------------------------------ a. absent key = today


def test_absent_restarts_key_is_todays_single_es_run(smoke_cfg, tmp_path, monkeypatch):
    """No ``search.restarts`` => one ES, budget exactness, no restart dirs, no restart run.json key."""
    cfg = fast_cfg(smoke_cfg)
    assert cfg.search.restarts is None
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    store = DatasetStore(tmp_path / "ds")
    run(cfg, tmp_path / "r", be, store, 25)
    rows = read_ndjson(tmp_path / "r" / "search.ndjson")
    assert len(rows) == 25 and not any(r["cached"] for r in rows)
    assert be.calls == 25                                    # non-cached == exactly the budget
    assert restart_dirs(tmp_path / "r") == []                 # no cma/restart_* subdirectories
    assert (tmp_path / "r" / "cma" / "fit.dat").exists()      # the single ES logs into cma/ itself
    rj = run_json(tmp_path / "r")
    assert "restarts" not in rj                              # run.json schema is exactly today's
    assert rj["stop_reason"] == "budget"
    assert rj["stats"]["non_cached"] == 25 and rj["stats"]["evaluations"] == 25


# ------------------------------------------------------------------ b. IPOP restarts + budget


def test_ipop_restarts_spend_exactly_the_budget_across_all_instances(smoke_cfg, tmp_path, monkeypatch):
    """ipop/max 2 at budget 45: seed + 10 + 20 new, then 14 of the 40-population restart.

    The initial attempt and the first restart stop naturally after one generation (huge tolfun);
    the third is cut by the budget mid-generation, so it is NOT told and writes no generation log.
    """
    cfg = restart_cfg(smoke_cfg, {"mode": "ipop", "max": 2})
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    store = DatasetStore(tmp_path / "ds")
    best = run(cfg, tmp_path / "r", be, store, 45)

    rows = read_ndjson(tmp_path / "r" / "search.ndjson")
    assert len(rows) == 45 and not any(r["cached"] for r in rows)
    assert be.calls == 45
    rj = run_json(tmp_path / "r")
    assert rj["stop_reason"] == "budget"
    assert rj["stats"]["non_cached"] == 45 and rj["stats"]["evaluations"] == 45

    entries = rj["restarts"]
    assert [e["index"] for e in entries] == [0, 1, 2]         # initial attempt + max restarts
    assert all(e["stop"].startswith("cma: ") for e in entries[:-1])
    assert entries[-1]["stop"] == "budget"
    assert sum(e["n_new_in_restart"] for e in entries) + 1 == 45     # + the seed, run once
    assert sum(e["evals_in_restart"] for e in entries) + 1 == 45

    dirs = restart_dirs(tmp_path / "r")
    assert len(dirs) >= 2 and dirs == ["restart_0", "restart_1"]
    assert (tmp_path / "r" / "cma" / "restart_0" / "fit.dat").exists()
    assert (tmp_path / "r" / "cma" / "restart_1" / "fit.dat").exists()

    bj = json.loads((tmp_path / "r" / "best.json").read_text(encoding="utf-8"))
    assert bj["design_hash"] == best.design_hash
    assert bj["objective"] == pytest.approx(best.objective)
    assert rj["best"]["design_hash"] == best.design_hash


def test_all_restarts_stopping_naturally_ends_on_restarts_exhausted(smoke_cfg, tmp_path, monkeypatch):
    """max 2 but a budget larger than the three one-generation attempts needs (10 + 20 + 40)."""
    cfg = restart_cfg(smoke_cfg, {"mode": "ipop", "max": 2})
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    run(cfg, tmp_path / "r", be, DatasetStore(tmp_path / "ds"), 200)
    rj = run_json(tmp_path / "r")
    assert rj["stop_reason"] == "restarts_exhausted"
    entries = rj["restarts"]
    assert len(entries) == 3 and all(e["stop"].startswith("cma: ") for e in entries)
    assert be.calls == 1 + sum(e["n_new_in_restart"] for e in entries) == 1 + 10 + 20 + 40
    assert restart_dirs(tmp_path / "r") == ["restart_0", "restart_1", "restart_2"]


# ------------------------------------------------------------------ c. the pycma schedule


def test_ipop_restart_doubles_popsize_via_pycma_parameters(smoke_cfg, tmp_path, monkeypatch):
    """The lambda schedule is pycma's: popsize0 * 2**k, sigma0 unchanged (see _RestartSchedule)."""
    cfg = restart_cfg(smoke_cfg, {"mode": "ipop", "max": 2})
    monkeypatch.setattr(cma_mod, "evaluate", bowl_eval())
    run(cfg, tmp_path / "r", SyntheticBackend(), None, 45)
    entries = run_json(tmp_path / "r")["restarts"]
    p0, p1, p2 = (e["popsize"] for e in entries)
    assert p1 == 2 * p0 and p2 == 2 * p1
    assert [e["sigma0"] for e in entries] == [cfg.search.sigma0] * 3
    # the per-restart pycma log carries that popsize too (parameters.json2 = es.sp.__dict__)
    params = ast.literal_eval(
        (tmp_path / "r" / "cma" / "restart_1" / "parameters.json2").read_text(encoding="utf-8"))
    assert int(params["popsize"]) == p1


def test_bipop_small_restart_shrinks_sigma_then_large_restart_doubles_popsize(
        smoke_cfg, tmp_path, monkeypatch):
    """BIPOP: restart 1 is a SMALL run (sigma0 * 0.01**U, popsize <= popsize0), restart 2 large."""
    cfg = restart_cfg(smoke_cfg, {"mode": "bipop", "max": 2})
    monkeypatch.setattr(cma_mod, "evaluate", bowl_eval())
    run(cfg, tmp_path / "r", SyntheticBackend(), None, 60)
    rj = run_json(tmp_path / "r")
    assert rj["stop_reason"] == "restarts_exhausted"
    e0, e1, e2 = rj["restarts"]
    assert e1["popsize"] <= e0["popsize"]                  # small-population branch
    assert e1["sigma0"] < e0["sigma0"]                     # 0.01**U shrinks sigma0
    assert e2["popsize"] == 2 * e0["popsize"]              # then a large run: IPOP doubling
    assert e2["sigma0"] == pytest.approx(cfg.search.sigma0)


# ------------------------------------------------------------------ d. resume


def test_interrupt_and_resume_matches_the_uninterrupted_run_with_no_double_spend(
        smoke_cfg, tmp_path, monkeypatch):
    """Half the budget, "kill", resume: the replayed restarts are cache hits (zero budget spend)."""
    cfg = restart_cfg(smoke_cfg, {"mode": "ipop", "max": 2})

    be_u = SyntheticBackend()
    install_fakes(monkeypatch, be_u)
    best_u = run(cfg, tmp_path / "u", be_u, DatasetStore(tmp_path / "dsu"), 40)

    be1 = SyntheticBackend()
    install_fakes(monkeypatch, be1)
    run(cfg, tmp_path / "r", be1, DatasetStore(tmp_path / "ds"), 20)
    first = list(be1.designs)
    assert be1.calls == 20 and len(first) == 20

    be2 = SyntheticBackend()
    install_fakes(monkeypatch, be2)
    best_r = run(cfg, None, be2, DatasetStore(tmp_path / "ds"), 20, resume=tmp_path / "r")
    assert not (set(first) & set(be2.designs)), "a finished evaluation was solved again"
    assert be2.calls == 20

    assert best_r.design_hash == best_u.design_hash
    assert best_r.objective == best_u.objective
    rows = read_ndjson(tmp_path / "r" / "search.ndjson")
    assert len(rows) == 40 and not any(r["cached"] for r in rows)
    assert run_json(tmp_path / "r")["stats"]["non_cached"] == 40   # exactly the 2x20 budget, once
    assert [r["design_hash"] for r in rows] == \
        [r["design_hash"] for r in read_ndjson(tmp_path / "u" / "search.ndjson")]
    # the restart sequence itself replayed identically (same schedule decisions, same populations)
    ru = run_json(tmp_path / "u")["restarts"]
    rr = run_json(tmp_path / "r")["restarts"]
    assert [(e["index"], e["popsize"], e["sigma0"]) for e in rr] == \
        [(e["index"], e["popsize"], e["sigma0"]) for e in ru]


# ------------------------------------------------------------------ e. config validation


def _config_with_restarts(tmp_path, restarts, name="restarts.yaml"):
    raw = yaml.safe_load((EXAMPLES / "search_smoke.yaml").read_text(encoding="utf-8"))
    if restarts is not None:
        raw["search"]["restarts"] = restarts
    path = tmp_path / name
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def test_restarts_key_is_parsed_and_validated(tmp_path):
    cfg = load_config(_config_with_restarts(tmp_path, {"mode": "bipop", "max": 3}))
    assert cfg.search.restarts == {"mode": "bipop", "max": 3}
    cfg0 = load_config(_config_with_restarts(tmp_path, {"mode": "ipop", "max": 0}, "zero.yaml"))
    assert cfg0.search.restarts == {"mode": "ipop", "max": 0}
    absent = load_config(_config_with_restarts(tmp_path, None, "absent.yaml"))
    assert absent.search.restarts is None


@pytest.mark.parametrize("block", [
    {"mode": "ipop", "max": 2, "extra": 1},     # unknown sub-key
    {"mode": "cma", "max": 2},                  # bad mode
    {"mode": "IPOP", "max": 2},                 # mode is exact
    {"mode": "ipop"},                           # missing max
    {"max": 2},                                 # missing mode
    "ipop",                                     # not a mapping
    {"mode": "ipop", "max": "2"},               # not an int
    {"mode": "ipop", "max": 2.5},
    {"mode": "ipop", "max": True},
    {"mode": "ipop", "max": 65},                # out of range
    {"mode": "ipop", "max": -1},
])
def test_bad_restarts_blocks_raise_config_error_with_the_search_restarts_prefix(tmp_path, block):
    path = _config_with_restarts(tmp_path, block)
    with pytest.raises(ConfigError, match=r"search\.restarts"):
        load_config(path)


def test_restarts_do_not_touch_the_solve_spec(tmp_path):
    """Search-only key: the solve-spec hash (cache + provenance) must not change."""
    plain = load_config(_config_with_restarts(tmp_path, None, "plain.yaml"))
    restarts = load_config(_config_with_restarts(tmp_path, {"mode": "bipop", "max": 2}, "r.yaml"))
    assert solve_spec("screen", plain) == solve_spec("screen", restarts)
