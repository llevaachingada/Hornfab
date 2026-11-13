"""M3 package gate: a capability/model/pool refusal is not a reviewable proposal."""
from __future__ import annotations

import pytest

from hornlab_search.studies.package import prepare_run_package
from hornlab_search.studies.schema import Unavailable, canonical
from hornlab_search.studies.service import StudyService


def _service(tmp_path):
    service = StudyService(tmp_path)
    study = service.create_study(
        {"protocol": "bo-study-v1.1", "name": "gate", "question": "gate",
         "task": {"name": "native__ath_core_v4"}, "cohort": "native__ath_core_v4",
         "policy": {"mode": "scalar"}, "pins": {"code_pins": {"fixture": "1"}}}, "create")
    sid = study["id"]
    service.attach_artifact(sid, 1, "snapshot", canonical({"status": "ok"}).encode(), {}, "s")
    service.attach_artifact(sid, 1, "model", canonical({"status": "ok"}).encode(), {}, "m")
    return service, sid


def test_package_refuses_capability_missing_proposal(tmp_path):
    service, sid = _service(tmp_path)
    service.attach_artifact(
        sid, 1, "proposal",
        canonical({"status": "capability_missing", "reason": "engine absent"}).encode(), {}, "p")
    with pytest.raises(Unavailable) as exc:
        prepare_run_package(service, sid, deadline="2099-01-01T00:00:00Z")
    assert "capability_missing" in str(exc.value)


def test_package_refuses_pool_exhausted_proposal(tmp_path):
    service, sid = _service(tmp_path)
    service.attach_artifact(
        sid, 1, "proposal",
        canonical({"status": "pool_exhausted", "reason": "no legal candidate"}).encode(), {}, "p")
    with pytest.raises(Unavailable):
        prepare_run_package(service, sid, deadline="2099-01-01T00:00:00Z")


def test_package_accepts_selected_candidate_or_labelled_fallback(tmp_path):
    service, sid = _service(tmp_path)
    service.attach_artifact(
        sid, 1, "proposal",
        canonical({"status": "ok", "candidate": {"solve_id": "screen-1"}}).encode(), {}, "p")
    package = prepare_run_package(service, sid, deadline="2099-01-01T00:00:00Z")
    assert package["package_id"]
    assert package["proposal_policy"]["policy"] == "scalar"


def test_package_accepts_labelled_exploration_fallback(tmp_path):
    service, sid = _service(tmp_path)
    service.attach_artifact(
        sid, 1, "proposal",
        canonical({"status": "model_unavailable", "fallback": True,
                   "candidate": {"solve_id": "explore-1"}}).encode(), {}, "p")
    package = prepare_run_package(service, sid, deadline="2099-01-01T00:00:00Z")
    assert package["package_id"]
