"""Create a child study from a parent spec.

The child inherits the parent's source/cohort and task, then changes only the question and (when
requested) the proposal policy.  It does **not** silently copy the parent run's new measured rows;
the owner adds those to the cohort explicitly, which keeps the dataset identity honest.
"""
from __future__ import annotations

import copy

from hornlab_search.bo.policy import PROPOSAL_POLICIES
from hornlab_search.studies.schema import StudyError
from hornlab_search.studies.service import StudyService


def create_child(service: StudyService, study_id: str, *, question: str, policy: str | None,
                 idempotency_key: str) -> dict:
    if not isinstance(idempotency_key, str) or not idempotency_key:
        raise StudyError("idempotency_key is required")
    if not isinstance(question, str) or not question.strip() or len(question) > 500:
        raise StudyError("child study needs a question (1-500 characters)")
    if policy is not None and policy not in PROPOSAL_POLICIES:
        raise StudyError(f"unknown child policy {policy!r}")
    parent = service.get_study(study_id)
    spec = copy.deepcopy(parent.get("spec") or {})
    spec["question"] = question.strip()
    if policy is not None:
        policy_spec = spec.get("policy")
        if not isinstance(policy_spec, dict):
            policy_spec = {}
        policy_spec["proposal_policy"] = policy
        spec["policy"] = policy_spec
    created = service.create_study(spec, idempotency_key, parent_id=study_id)
    return {**created, "parent_id": study_id}


__all__ = ["create_child"]
