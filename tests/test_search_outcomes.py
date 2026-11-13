"""F0 (day 2026-11-12): typed outcome classification + the new strict config schema.

Outcome tests pin the invariant from hardening section 8.2: a legitimate large objective is never
a failure, a fully measured acoustic gate is tell-eligible, and only the typed category (never
``J >= 1000``) decides. Config tests pin the opt-in strict enum and its contradictory combinations.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.config import ConfigError, load_config
from hornlab_search.search import outcomes
from hornlab_search.types import Design, Evaluation, SolveOutcome


def _ev(error: str = "", *, objective: float = 1.0, terms: dict | None = None,
        cached: bool = False) -> Evaluation:
    return Evaluation(design_hash="d", design=Design("OSSE", {}), mesh_hash="m", solve_hash="s",
                      objective=float(objective), terms=dict(terms or {}), metrics=None, mesh=None,
                      outcome=SolveOutcome(not error, None, 0.0, None, error), cached=cached,
                      error=error)


# ------------------------------------------------------------------ classification

def test_complete_score_is_eligible():
    out = outcomes.classify(_ev(objective=12.5))
    assert out.category == outcomes.CATEGORY_COMPLETE
    assert out.strict_tell_eligible and out.complete and not out.deterministic_refusal


def test_measured_acoustic_gate_is_a_complete_eligible_score():
    out = outcomes.classify(_ev(objective=1000.0,
                                terms={"gate_failed": True, "gate_measured": True}))
    assert out.category == outcomes.CATEGORY_MEASURED_GATE
    assert out.complete and out.measured_gate
    assert out.strict_tell_eligible, "a fully measured gate penalty is the declared objective"
    assert not out.deterministic_refusal and not out.infrastructure


def test_unmeasured_gate_penalty_is_not_eligible():
    """A 1e3 gate penalty with a missing input must never look like a measured observation."""
    out = outcomes.classify(_ev(objective=1000.0, terms={"gate_failed": True}))
    assert out.category == outcomes.CATEGORY_METRIC
    assert not out.complete and not out.measured_gate
    assert not out.strict_tell_eligible and out.infrastructure


def test_legitimate_large_objective_is_complete_never_a_failure():
    out = outcomes.classify(_ev(objective=5000.0))
    assert out.category == outcomes.CATEGORY_COMPLETE
    assert out.complete and out.strict_tell_eligible
    assert not out.deterministic_refusal and not out.infrastructure


@pytest.mark.parametrize("kind,category,det", [
    ("invalid_geometry", outcomes.CATEGORY_GEOMETRY, True),
    ("invalid_envelope", outcomes.CATEGORY_ENVELOPE, True),
    ("mesh_too_large", outcomes.CATEGORY_RESOURCE, True),
])
def test_each_deterministic_refusal_kind(kind, category, det):
    out = outcomes.classify(_ev(f"{kind}: synthetic refusal", objective=1000.0))
    assert out.category == category and out.deterministic_refusal is det
    assert not out.strict_tell_eligible and not out.infrastructure
    assert category in outcomes.DETERMINISTIC_CATEGORIES


def test_solve_failed_is_transient_and_same_candidate_retryable():
    out = outcomes.classify(_ev("solve_failed: worker exited"))
    assert out.category == outcomes.CATEGORY_TRANSIENT
    assert out.infrastructure and out.retry_same_candidate
    assert not out.strict_tell_eligible and not out.deterministic_refusal


def test_metrics_failed_is_infrastructure_but_not_retryable():
    out = outcomes.classify(_ev("metrics_failed: missing balloon"))
    assert out.category == outcomes.CATEGORY_METRIC
    assert out.infrastructure and not out.retry_same_candidate
    assert not out.strict_tell_eligible


def test_exception_is_unknown_not_a_feasibility_label():
    out = outcomes.classify(_ev("exception: RuntimeError: boom", objective=1000.0))
    assert out.category == outcomes.CATEGORY_UNKNOWN
    assert out.infrastructure and not out.retry_same_candidate
    assert not out.strict_tell_eligible


def test_strict_tell_eligible_predicate():
    assert outcomes.strict_tell_eligible(_ev(objective=2000.0))
    assert not outcomes.strict_tell_eligible(_ev("invalid_geometry: x"))


# ------------------------------------------------------------------ config schema

def _write_cfg(tmp_path, **search_patch):
    raw = yaml.safe_load((EXAMPLES / "search_smoke.yaml").read_text(encoding="utf-8"))
    raw["search"].update(search_patch)
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return p


STRICT = {"infeasible_penalty": "resample_strict",
          "error_policy": "retry_same_then_stop", "budget_counts": "valid"}


def _qd(**maes):
    block = {"descriptor_h": "mean_bw_h_deg", "descriptor_v": "mean_bw_v_deg",
             "bins_h": 6, "bins_v": 6}
    if maes:
        block["maes"] = maes
    return block


def test_default_config_has_legacy_error_policy(tmp_path):
    cfg = load_config(_write_cfg(tmp_path))
    assert cfg.search.error_policy == "legacy"
    assert cfg.search.infeasible_penalty == "flat"


def test_resample_strict_loads_for_plain_cma(tmp_path):
    cfg = load_config(_write_cfg(tmp_path, **STRICT))
    assert cfg.search.infeasible_penalty == "resample_strict"
    assert cfg.search.error_policy == "retry_same_then_stop"
    assert cfg.search.budget_counts == "valid"


def test_resample_strict_is_refused_for_cma_me(tmp_path):
    with pytest.raises(ConfigError, match="cma_me"):
        load_config(_write_cfg(tmp_path, algorithm="cma_me", qd=_qd(), **STRICT))


def test_resample_strict_requires_the_error_policy(tmp_path):
    patch = dict(STRICT)
    patch.pop("error_policy")
    with pytest.raises(ConfigError, match="error_policy"):
        load_config(_write_cfg(tmp_path, **patch))


def test_resample_strict_requires_valid_budget_counts(tmp_path):
    patch = dict(STRICT, budget_counts="new")
    with pytest.raises(ConfigError, match="budget_counts"):
        load_config(_write_cfg(tmp_path, **patch))


def test_resample_strict_rejects_restarts(tmp_path):
    with pytest.raises(ConfigError, match="restarts"):
        load_config(_write_cfg(tmp_path, restarts={"mode": "ipop", "max": 2}, **STRICT))


def test_resample_strict_rejects_lq(tmp_path):
    with pytest.raises(ConfigError, match="lq"):
        load_config(_write_cfg(tmp_path, surrogate="lq", **STRICT))


def test_resample_strict_rejects_prefetch(tmp_path):
    with pytest.raises(ConfigError, match="pipeline_prefetch"):
        load_config(_write_cfg(tmp_path, pipeline_prefetch=2, **STRICT))


def test_error_policy_rejects_restarts_lq_and_prefetch(tmp_path):
    retry = {"error_policy": "retry_same_then_stop", "budget_counts": "valid"}
    with pytest.raises(ConfigError, match="restarts"):
        load_config(_write_cfg(tmp_path, restarts={"mode": "ipop", "max": 1}, **retry))
    with pytest.raises(ConfigError, match="lq"):
        load_config(_write_cfg(tmp_path, surrogate="lq", **retry))
    with pytest.raises(ConfigError, match="pipeline_prefetch"):
        load_config(_write_cfg(tmp_path, pipeline_prefetch=1, **retry))


def test_error_policy_requires_a_bounded_policy(tmp_path):
    # budget_counts: new and no max_attempts => no resolvable draw cap.
    with pytest.raises(ConfigError, match="bounded"):
        load_config(_write_cfg(tmp_path, error_policy="retry_same_then_stop"))


def test_error_policy_bad_token_is_refused(tmp_path):
    with pytest.raises(ConfigError, match="error_policy"):
        load_config(_write_cfg(tmp_path, error_policy="retry_forever"))


def test_error_policy_allows_qd_infrastructure_retry(tmp_path):
    # QD may opt into infrastructure retry WITHOUT strict deterministic resampling (F1 owns it).
    cfg = load_config(_write_cfg(tmp_path, algorithm="cma_me", qd=_qd(),
                                 error_policy="retry_same_then_stop", budget_counts="valid"))
    assert cfg.search.error_policy == "retry_same_then_stop"
    assert cfg.search.infeasible_penalty == "flat"


@pytest.mark.parametrize("jt", [999, 1.0, 500.0])
def test_mae_threshold_below_penalty_loads(tmp_path, jt):
    cfg = load_config(_write_cfg(tmp_path, algorithm="cma_me",
                                 qd=_qd(learning_rate=0.05, j_threshold=jt)))
    assert cfg.search.qd["maes"]["j_threshold"] == float(jt)


@pytest.mark.parametrize("jt", [1000.0, float("nan"), float("inf"), -1.0, 0.0])
def test_mae_threshold_safety_cap_is_refused(tmp_path, jt):
    with pytest.raises(ConfigError, match="j_threshold"):
        load_config(_write_cfg(tmp_path, algorithm="cma_me",
                               qd=_qd(learning_rate=0.05, j_threshold=jt)))
