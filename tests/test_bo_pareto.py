from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.bo.pareto import frozen_reference, nondominated, select_subset, _fit_pareto_numeric, acquisition_scores, fit_constrained_pareto


def test_front_and_frozen_reference_use_original_units():
    e = np.array([[1., 5.], [2., 3.], [3., 4.], [4., 1.]])
    assert nondominated(e).tolist() == [True, True, False, True]
    ref = frozen_reference(e)
    assert ref["limits"] == pytest.approx([4.3, 5.4])
    assert ref["ref_point"] == pytest.approx([-4.3, -5.4])
    assert frozen_reference([[2, 3]])["limits"] == pytest.approx([2.1, 3.01])


def test_subset_reference_from_full_data_and_deterministic():
    x = np.linspace(0, 1, 100).reshape(-1, 1)
    e = np.column_stack((x[:, 0], 1-x[:, 0]))
    ids = [f"g{i:03d}" for i in range(100)]
    result = select_subset(x, e, np.arange(100), ids, cap=20)
    assert result == select_subset(x, e, np.arange(100), ids, cap=20)
    assert len(result["indices"]) == 20
    assert result["reference"]["limits"] == pytest.approx([1.1, 1.1])
    assert "g000" in result["ids"] and "g099" in result["ids"]
    with pytest.raises(ValueError):
        select_subset(x, e, np.arange(100), ["same"]*100)


def test_optional_model_fails_closed_and_invalid_reference_refuses():
    x = np.linspace(0, 1, 16).reshape(-1, 1)
    e = np.column_stack((1+x[:, 0], 2+x[:, 0]**2))
    bad = _fit_pareto_numeric(x, e, list(range(16)), reference={"ref_point": [0, 0]})
    assert bad.status == "unavailable" and bad.reason == "invalid_reference"
    assert acquisition_scores(SimpleNamespace(status="unavailable", reason="missing"), x)["status"] == "unavailable"


def test_pinned_engine_pareto_acquisition():
    x = np.linspace(0, 1, 16).reshape(-1, 1)
    e = np.column_stack((1+x[:, 0], 2+(1-x[:, 0])**2))
    result = _fit_pareto_numeric(x, e, [str(i) for i in range(16)], reference=frozen_reference(e))
    if result.reason == "capability_missing":
        assert result.status == "unavailable"
        return
    assert result.status == "ok", result.reason
    scores = acquisition_scores(result, np.array([[.2], [.8]]), seed=5)
    assert scores["status"] == "ok", scores
    assert np.isfinite(scores["values"]).all()
    assert fit_constrained_pareto(result, np.ones((16, 3)), ids=list(range(16))).reason == "constraint_model_unavailable"
    g = np.column_stack((x[:, 0]-.6, .1-x[:, 0], .2-x[:, 0]))
    margins = {str(i): {"status": "ok", "names": ["g_lfp", "g_hold", "g_window"],
                        "margins": row.tolist()} for i, row in enumerate(g)}
    constrained = fit_constrained_pareto(result, margins, ids=list(range(16)))
    assert constrained.status == "ok", constrained.reason
    assert acquisition_scores(constrained, np.array([[.3], [.7]]), seed=5)["status"] == "ok"


def test_proposal_revalidates_and_breaks_acquisition_ties_by_geometry(monkeypatch):
    from hornlab_search.bo import pareto, propose, model
    from hornlab_search.bo.propose import ProposalHistory
    def candidate(geometry, x):
        return SimpleNamespace(candidate_id=geometry, geometry_hash=geometry, design_hash=geometry,
                               intended_solve_hash="s", active_vector=np.array([x]),
                               as_dict=lambda **kw: {"geometry_hash": geometry})
    fit = SimpleNamespace(status="ok", train_X=np.array([[0.0]]), outputs=[1, 2],
                          reference={"ref_point": [-2, -2]})
    pool = SimpleNamespace(status="ok", candidates=[candidate("z", .3), candidate("a", .8)])
    monkeypatch.setattr(pareto, "acquisition_scores", lambda *a, **kw: {"status": "ok", "values": np.array([1., 1.])})
    checked = []
    monkeypatch.setattr(propose, "validate_selected_candidate", lambda c, *a, **kw: checked.append(c.geometry_hash))
    p = SimpleNamespace(status="ok", j_mean=[1.], j_lower=[.5], j_upper=[1.5], interval_label="model interval")
    monkeypatch.setattr(model, "predict_j", lambda *a: p)
    result = pareto.propose_pareto(fit, pool, ProposalHistory(), encoding=object(), config=object())
    assert result["status"] == "ok" and result["candidate"]["geometry_hash"] == "a"
    assert checked == ["a"]
    monkeypatch.setattr(propose, "validate_selected_candidate", lambda *a, **kw: (_ for _ in ()).throw(ValueError("tampered")))
    assert pareto.propose_pareto(fit, pool, ProposalHistory(), encoding=object(), config=object())["status"] == "unavailable"
