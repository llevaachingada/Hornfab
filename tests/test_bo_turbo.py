"""turbo_pool_v1 trust-region policy (spec 3.6): state machine, box, candidates, resume.

Offline only: real cheap-check geometry through the installed mesher (no gmsh/BEM); the GP and
acquisition tests need the optional BoTorch engine and skip without it.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from conftest import requires_mesher
from hornlab_search.bo import turbo
from hornlab_search.bo.policy import (PROPOSAL_POLICIES, ProposalOutcome, capability_status,
                                      verification_mode)
from hornlab_search.bo.propose import ProposalHistory
from hornlab_search.bo.turbo import (L_INIT, L_MAX, L_MIN, OUTCOME_MEASURED, OUTCOME_REFUSAL,
                                     TurboState, box_bounds, initial_state, update_state)

NATIVE_CONFIG = (Path(__file__).resolve().parents[1] / "examples" / "typologies"
                 / "campaign_2026-10-26_v4" / "native__ath_core_v4.yaml")


def _state(d=2, best=10.0):
    return TurboState(center=tuple([0.5] * d), best_j=best)


# --------------------------------------------------------------------------- state machine


def test_policy_surface_and_verification_mode():
    assert "turbo" in PROPOSAL_POLICIES and verification_mode("turbo") == "scalar"
    assert capability_status("turbo")["reason"] == "training_set_required"
    assert "trust_region" not in ProposalOutcome("ok", "ok", "scalar").to_dict()


def test_initial_state_is_best_measured_design_ties_by_id():
    ts = type("T", (), {"X": np.array([[.1, .1], [.9, .9], [.4, .6]]),
                        "J": np.array([[3.], [1.], [1.]]), "ids": ("c", "b", "a")})
    state = initial_state(ts)
    assert state.center == (.4, .6) and state.best_j == 1.0 and state.length == L_INIT


def test_three_successes_double_up_to_max_and_reset_counter():
    state = _state()
    j = 10.0
    for _ in range(3):
        j -= 1.0
        state = update_state(state, outcome=OUTCOME_MEASURED, candidate=[.4, .6], J=j)
    assert state.length == pytest.approx(1.6) and state.success_counter == 0
    for _ in range(3):
        j -= 1.0
        state = update_state(state, outcome=OUTCOME_MEASURED, candidate=[.4, .6], J=j)
    assert state.length == L_MAX and state.center == (.4, .6) and state.best_j == j


def test_subthreshold_improvement_is_a_failure_and_failures_halve_at_max_4_d():
    state = _state(d=2, best=10.0)
    # improvement of 1e-3*10 = 0.01 is required; 0.005 is a non-improvement
    state = update_state(state, outcome=OUTCOME_MEASURED, candidate=[.6, .6], J=9.995)
    assert state.failure_counter == 1 and state.success_counter == 0
    for _ in range(3):
        state = update_state(state, outcome=OUTCOME_MEASURED, candidate=[.6, .6], J=11.0)
    assert state.length == pytest.approx(L_INIT / 2) and state.failure_counter == 0
    d6 = _state(d=6)
    for _ in range(5):
        d6 = update_state(d6, outcome=OUTCOME_REFUSAL)
    assert d6.length == L_INIT and d6.failure_counter == 5   # max(4, d) = 6
    d6 = update_state(d6, outcome=OUTCOME_REFUSAL)
    assert d6.length == pytest.approx(L_INIT / 2)


def test_success_resets_failures_and_vice_versa():
    state = _state()
    state = update_state(state, outcome=OUTCOME_REFUSAL)
    state = update_state(state, outcome=OUTCOME_MEASURED, candidate=[.5, .4], J=5.0)
    assert state.failure_counter == 0 and state.success_counter == 1
    state = update_state(state, outcome=OUTCOME_REFUSAL)
    assert state.success_counter == 0 and state.failure_counter == 1


def test_refusals_count_and_infrastructure_never_updates():
    state = _state()
    same = update_state(state, outcome="solver_failure")
    assert same is state
    assert update_state(state, outcome="unknown") is state
    assert update_state(state, outcome=OUTCOME_REFUSAL).failure_counter == 1


def test_collapse_is_terminal_no_restart():
    state = replace(_state(), length=L_MIN * 1.5)
    for _ in range(4):
        state = update_state(state, outcome=OUTCOME_REFUSAL)
    assert state.status == "collapsed"
    assert state.terminal_reason == turbo.REASON_TRUST_REGION_COLLAPSED
    assert update_state(state, outcome=OUTCOME_MEASURED, candidate=[.1, .1], J=0.) is state
    result, record = turbo.propose_turbo(None, None, ProposalHistory(), state,
                                         encoding=None, config=None)
    assert result.status == "pool_exhausted" and result.reason == "trust_region_collapsed"
    assert result.candidate is None and record["state_after"]["status"] == "collapsed"


def test_applied_solve_ids_make_replay_idempotent_and_dict_round_trips():
    state = update_state(_state(), outcome=OUTCOME_REFUSAL, solve_id="s1")
    again = update_state(state, outcome=OUTCOME_REFUSAL, solve_id="s1")
    assert again is state
    state = replace(state, lengthscales=(0.2, 0.8))
    assert TurboState.from_dict(state.to_dict()) == state
    with pytest.raises(ValueError):
        TurboState.from_dict({**state.to_dict(), "policy": "scalar_pool_v1"})


def test_box_uses_lengthscale_weights_and_clips():
    state = replace(_state(), length=0.8)
    lo, hi = box_bounds(state, [1.0, 4.0])
    # weights = ell / geomean(ell) = [0.5, 2]
    assert lo == pytest.approx([.3, 0.]) and hi == pytest.approx([.7, 1.])


def test_local_seed_is_deterministic_and_index_dependent():
    assert turbo.local_seed(7, 3, 0) == turbo.local_seed(7, 3, 0)
    assert len({turbo.local_seed(7, 3, a) for a in range(3)} | {turbo.local_seed(8, 3, 0)}) == 4


# --------------------------------------------------------------------------- real geometry


def _native():
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.studies.builders import _task_encoding
    cfg = load_config(NATIVE_CONFIG)
    space = DesignSpace.from_config(cfg)
    return cfg, _task_encoding(space)


@requires_mesher
def test_local_candidates_inside_box_cheap_checked_and_deterministic():
    cfg, enc = _native()
    lo, hi = np.full(enc.d, 0.3), np.full(enc.d, 0.6)
    first, report = turbo.local_candidates(enc, cfg, lo, hi, seed=11, n=16)
    second, _ = turbo.local_candidates(enc, cfg, lo, hi, seed=11, n=16)
    assert [c.geometry_hash for c in first] == [c.geometry_hash for c in second]
    assert report["counts"]["generated"] == 16 and first
    for c in first:
        assert np.all(c.active_vector >= lo) and np.all(c.active_vector <= hi)
        assert c.checks["mesh_built"] is False and c.checks["bem_called"] is False


def _training_from_pool(pool, n=32):
    from hornlab_search.bo.data import TrainingObservation, build_training_set
    rows = []
    for c in pool.candidates[:n]:
        x = np.asarray(c.active_vector, dtype=float)
        rows.append(TrainingObservation(observation_id=c.candidate_id, x=x,
                                        J=float(np.sum((x - 0.35) ** 2)),
                                        geometry_hash=c.geometry_hash, solve_hash="s"))
    return build_training_set(rows, d=len(rows[0].x), seed=0)


@requires_mesher
def test_turbo_proposal_inside_box_deterministic_and_records_state():
    pytest.importorskip("botorch")
    from hornlab_search.bo.data import build_candidate_pool
    from hornlab_search.bo.policy import fit_and_propose
    cfg, enc = _native()
    pool = build_candidate_pool(enc.space, enc, cfg, n=64, seed=5)
    training = _training_from_pool(pool)
    assert training.status == "ok", training.status
    rest = replace(pool, candidates=pool.candidates[32:])
    outs = [fit_and_propose("turbo", training_set=training, pool=rest, history=ProposalHistory(),
                            seed=3, encoding=enc, config=cfg) for _ in range(2)]
    out = outs[0]
    assert out.status == "ok", (out.reason, out.detail)
    assert out.proposal["geometry_hash"] == outs[1].proposal["geometry_hash"]
    box = out.trust_region["box"]
    v = np.asarray(out.proposal["active_vector"])
    assert np.all(v >= np.asarray(box["lo"]) - 1e-12) and np.all(v <= np.asarray(box["hi"]) + 1e-12)
    after = out.trust_region["state_after"]
    assert after["lengthscales"] and len(after["lengthscales"]) == enc.d
    assert out.selection_reason == "trust_region_acquisition"
    assert out.verification_mode == "scalar" and out.predicted is not None
    assert "trust_region" in out.to_dict()


# --------------------------------------------------------------------------- evaluator / resume


def _evaluator():
    from hornlab_search.bo.data import TrainingSet
    from hornlab_search.studies.evaluator import PipelineStudyEvaluator
    X = np.array([[.2, .2], [.5, .5], [.8, .8]])
    J = np.array([[3.], [1.], [2.]])
    ts = TrainingSet(status="ok", d=2, n=3, X=X, J=J, Y=-J, Y_phys=None, G=None,
                     ids=("a", "b", "c"), selected_ids=("a", "b", "c"), excluded_ids=(),
                     elite_ids=(), maximin_ids=(), n_eligible=3, n_unique=3, n_min=16,
                     n_max=256, active_keys=("x", "y"), projection_version=None,
                     preparation=None, meta={})
    package = {"budget": {"screen_calls": 18}}
    return PipelineStudyEvaluator(None, package, training_set=ts, policy="turbo",
                                  fit_fn=lambda *a: type("F", (), {"status": "ok"})())


def test_evaluator_updates_trust_region_and_ignores_infrastructure():
    ev = _evaluator()
    assert ev.turbo_state.center == (.5, .5)
    ev.observe({"kind": "screen", "solve_id": "r1", "outcome": "cheap_refusal"})
    assert ev.turbo_state.failure_counter == 1
    before = ev.turbo_state
    ev.observe({"kind": "screen", "solve_id": "r2", "outcome": "solver_failure"})
    ev.observe({"kind": "screen", "solve_id": "r3", "outcome": "unknown"})
    assert ev.turbo_state == before
    ev.observe({"kind": "screen", "solve_id": "m1", "outcome": "success", "eligible": True,
                "observed_j": 0.5, "physical_id": "p1", "x": [.4, .4]})
    assert ev.turbo_state.success_counter == 1 and ev.turbo_state.center == (.4, .4)
    ev.observe({"kind": "verify", "solve_id": "v", "outcome": "success", "observed_j": 0.1,
                "geometry_id": "g"})
    assert ev.turbo_state.iteration == 2


def test_resume_round_trips_trust_region_state_exactly():
    ev = _evaluator()
    r1 = {"kind": "screen", "solve_id": "r1", "outcome": "cheap_refusal"}
    m1 = {"kind": "screen", "solve_id": "m1", "outcome": "success", "eligible": True,
          "observed_j": 0.5, "physical_id": "p1", "x": [.4, .4]}
    ev.observe(r1)
    staged = ev.proposal_rng_state()      # staged before m1 was evaluated
    ev.observe(m1)
    live = ev.turbo_state
    resumed = _evaluator()
    resumed.restore_progress({"rng_state": staged, "proposal_index": None,
                              "observations": [{"result": r1, "candidate": {}},
                                               {"result": m1, "candidate": {}}]})
    assert resumed.turbo_state == live
    assert staged["rng_state"]["turbo_state"]["policy"] == "turbo_pool_v1"


def test_scalar_rng_state_has_no_turbo_or_pareto_keys():
    from hornlab_search.studies.evaluator import PipelineStudyEvaluator
    ev = PipelineStudyEvaluator(None, {"budget": {}})
    extra = ev.proposal_rng_state()["rng_state"]
    assert "turbo_state" not in extra and "pareto_excluded" not in extra
    assert ev.turbo_state is None
