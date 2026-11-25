"""Candidate eligibility is pinned separately from acoustic and solve identity."""
from types import SimpleNamespace

import pytest

from hornlab_search.config import envelope_policy
from hornlab_search.studies.package import verify_candidate_policy
from hornlab_search.studies.service import Unavailable


def test_bound_policy_detects_changed_limits_and_stale_pool():
    env = {"max_mouth_w_mm": 500, "max_mouth_h_mm": 400, "max_depth_mm": 300,
           "enforce": False, "max_utilization": 1.1}
    cfg = SimpleNamespace(brief={"envelope": env})
    policy = envelope_policy(cfg.brief).as_dict()
    package = {"candidate_policy": policy}
    pool = {"candidate_policy": policy}
    verify_candidate_policy(package, cfg, pool=pool)
    env["max_utilization"] = 1.2
    with pytest.raises(Unavailable, match="changed"):
        verify_candidate_policy(package, cfg, pool=pool)
    updated = {"candidate_policy": envelope_policy(cfg.brief).as_dict()}
    with pytest.raises(Unavailable, match="pool"):
        verify_candidate_policy(updated, cfg, pool=pool)


def test_legacy_package_requires_binding_only_for_opt_in_modes():
    env = {"max_mouth_w_mm": 500, "max_mouth_h_mm": 400, "max_depth_mm": 300}
    cfg = SimpleNamespace(brief={"envelope": env})
    verify_candidate_policy({}, cfg)
    verify_candidate_policy({}, SimpleNamespace(brief={}))
    env["enforce"] = False
    with pytest.raises(Unavailable, match="requires a candidate-policy binding"):
        verify_candidate_policy({}, cfg)


@pytest.mark.parametrize("policy", ["metric_composite_v1", "pareto"])
def test_existing_unbound_open_package_keeps_its_admission_contract(policy):
    cfg = SimpleNamespace(brief={"envelope": {"max_mouth_w_mm": 500, "max_mouth_h_mm": 400,
                                             "max_depth_mm": 300, "enforce": False}})
    verify_candidate_policy({"proposal_policy": {"policy": policy}}, cfg, pool={})
