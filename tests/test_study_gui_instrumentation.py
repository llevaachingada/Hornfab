from hornlab_search.bo.policy import ProposalOutcome
from hornlab_search.studies.evaluator import PipelineStudyEvaluator


def test_outcome_carries_hyperparameters_to_dict():
    outcome = ProposalOutcome(
        status="ok", reason="ok", policy="scalar",
        proposal={"candidate_id": "c"}, predicted={"j_mean": 1.0},
        model_hyperparameters={"lengthscales": [0.1, 0.5]},
    )
    payload = outcome.to_dict()
    assert payload["model_hyperparameters"]["lengthscales"] == [0.1, 0.5]


def test_evaluator_persists_prediction_and_trust_region_on_the_candidate(monkeypatch):
    evaluator = PipelineStudyEvaluator(None, {}, policy="scalar")
    fake = ProposalOutcome(
        status="ok", reason="ok", policy="scalar",
        proposal={"candidate_id": "c1", "design_hash": "d1", "x": [0.1, 0.2],
                  "active_vector": [0.1, 0.2], "geometry_id": "g1"},
        predicted={"j_mean": 3.0, "j_lower": 2.0, "j_upper": 4.0},
        selection_reason="acquisition",
        acquisition={"value": 0.2},
        model_hyperparameters={"lengthscales": [0.1, 0.5]},
    )
    monkeypatch.setattr("hornlab_search.bo.policy.fit_and_propose",
                        lambda *args, **kwargs: fake)
    proposal = evaluator._propose_through_policy()
    assert proposal["predicted"]["j_mean"] == 3.0
    assert proposal["selection_reason"] == "acquisition"
    assert proposal["acquisition"]["value"] == 0.2
    normalized = evaluator._normalise(proposal, kind="screen")
    assert normalized["predicted"]["j_upper"] == 4.0
    assert normalized["selection_reason"] == "acquisition"


def test_evaluator_keeps_turbo_state_sequence_on_candidates(monkeypatch):
    evaluator = PipelineStudyEvaluator(None, {}, policy="turbo")
    record = {
        "policy": "turbo_pool_v1", "proposal_index": 2,
        "state_after": {"policy": "turbo_pool_v1", "center": [0.2, 0.2], "best_j": 2.5,
                        "length": 0.4, "length_bounds": {"init": 0.8, "min": 0.0078125,
                                                         "max": 1.6},
                        "success_counter": 1, "failure_counter": 1, "iteration": 2,
                        "lengthscales": [0.1, 0.5], "status": "active",
                        "terminal_reason": None, "applied": []},
        "box": {"lo": [0.0, 0.0], "hi": [0.5, 0.5], "weights": [1.0, 1.0]},
    }
    fake = ProposalOutcome(
        status="ok", reason="ok", policy="turbo",
        proposal={"candidate_id": "c2", "design_hash": "d2", "x": [0.2, 0.2],
                  "active_vector": [0.2, 0.2], "geometry_id": "g2"},
        predicted={"j_mean": 2.5, "j_lower": 1.5, "j_upper": 3.5},
        selection_reason="trust_region_acquisition",
        trust_region=record,
        model_hyperparameters={"lengthscales": [0.1, 0.5]},
    )
    monkeypatch.setattr("hornlab_search.bo.policy.fit_and_propose",
                        lambda *args, **kwargs: fake)
    proposal = evaluator._propose_through_policy()
    assert proposal["trust_region"]["state_after"]["length"] == 0.4
    normalized = evaluator._normalise(proposal, kind="screen")
    assert normalized["trust_region"]["proposal_index"] == 2
