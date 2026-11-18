"""Handoff §3.4 (2026-11-17): geometric link proposals carry the empirical links verdict.

``space_card.recommend`` must attach ``data_agrees`` (true / false / unknown) to every link
proposal and must not emit ``action: link`` when the ``links`` tool evidence disagrees.
"""
from __future__ import annotations

import types
from pathlib import Path

from tools.analysis import space_card as SC

LINK = {"from": "a", "follower": "b", "scale": 2.0, "offset": 1.0, "median_abs_cos": 0.99}
GEO = {"keys": ["a", "b"], "knobs": {}, "links": [dict(LINK)],
       "legal_points": 8, "n_points": 8, "effective_dimension": 2,
       "feasible_from_seed": {}}
BOX = {"per_knob": {}, "counts": {}, "ok_frac": 1.0}
SIGMA = {"0.10": {"bad_rate": 0.05}}
MARGIN = {"available": False}
SPACE = types.SimpleNamespace(keys=lambda: ["a", "b"])


def _link_recs(data=None):
    recs = SC.recommend(GEO, BOX, SIGMA, MARGIN, data)
    links = [r for r in recs if r["knob"] == "b"]
    assert len(links) == 1
    return links[0]


def _payload(*proposals):
    return {"run_dir": "runs/x", "family": "OSSE", "top_decile_n": 12,
            "pairs": [], "cma_directions": [], "proposed_links": list(proposals)}


def _proposal(knob_a, knob_b, scale):
    return {"knob_a": knob_a, "knob_b": knob_b, "scale": scale, "offset": 0.0,
            "r2": 0.9, "source": "rho_top_decile"}


# ------------------------------------------------------------------ data_agrees verdicts

def test_true_same_pair_same_sign():
    r = _link_recs({"links": _payload(_proposal("a", "b", 3.0))})
    assert r["action"] == "link"
    assert r["data_agrees"] is True


def test_true_reversed_orientation_uses_reciprocal_sign():
    # proposal is b = a form stored backwards: a = 0.5 * b  =>  b = 2 * a (same + sign)
    r = _link_recs({"links": _payload(_proposal("b", "a", 0.5))})
    assert r["action"] == "link"
    assert r["data_agrees"] is True


def test_false_pair_absent():
    r = _link_recs({"links": _payload(_proposal("a", "c", 3.0))})
    assert r["action"] == "link_rejected_by_data"
    assert r["data_agrees"] is False
    assert r["knob"] == "b" and r["proposal"]["from"] == "a"


def test_false_pair_present_opposite_sign():
    r = _link_recs({"links": _payload(_proposal("a", "b", -3.0))})
    assert r["action"] == "link_rejected_by_data"
    assert r["data_agrees"] is False


def test_false_reversed_orientation_opposite_sign():
    # reversed proposal with a negative scale: sign(1 / -0.5) = -1 != +1
    r = _link_recs({"links": _payload(_proposal("b", "a", -0.5))})
    assert r["action"] == "link_rejected_by_data"
    assert r["data_agrees"] is False


def test_false_when_analysed_but_no_proposals():
    r = _link_recs({"links": _payload()})
    assert r["action"] == "link_rejected_by_data"
    assert r["data_agrees"] is False


def test_unknown_without_data():
    r = _link_recs(None)
    assert r["action"] == "link"
    assert r["data_agrees"] == "unknown"


def test_unknown_with_error_payload():
    r = _link_recs({"links": {"error": "FileNotFoundError: no run.json"}})
    assert r["action"] == "link"
    assert r["data_agrees"] == "unknown"


def test_unknown_when_run_analysed_only_walls():
    r = _link_recs({"walls": {"counts": {}}})
    assert r["action"] == "link"
    assert r["data_agrees"] == "unknown"


# ------------------------------------------------------------------ card wiring + render

def test_card_for_passes_data_into_recommendations_and_md(monkeypatch):
    from hornlab_search.geometry import sensitivity as S

    cfg = types.SimpleNamespace(name="synthetic", family="OSSE", generator=False)
    monkeypatch.setattr("hornlab_search.config.load_config", lambda p: cfg)
    monkeypatch.setattr("hornlab_search.design.space.DesignSpace.from_config",
                        classmethod(lambda cls, c: SPACE))
    monkeypatch.setattr(S, "analyze_space", lambda space, c, n_points: GEO)
    monkeypatch.setattr(S, "box_feasibility", lambda space, c, n: BOX)
    monkeypatch.setattr(S, "sigma_refusal_curve", lambda space, c, n: SIGMA)
    monkeypatch.setattr(S, "margin_model", lambda space, c, n: MARGIN)
    monkeypatch.setattr(SC, "_data_evidence", lambda run: {
        "links": _payload(_proposal("a", "b", 3.0))})

    card = SC.card_for(Path("synthetic.yaml"), run=Path("runs/x"),
                       points=8, box_n=8, sigma_n=8)
    rec = [r for r in card["recommendations"] if r["knob"] == "b"][0]
    assert "data_agrees" in rec and rec["data_agrees"] is True
    assert rec["action"] == "link"
    assert "data_agrees=true" in SC._md(card)


def test_card_for_no_run_keeps_link_and_unknown(monkeypatch):
    from hornlab_search.geometry import sensitivity as S

    cfg = types.SimpleNamespace(name="synthetic", family="OSSE", generator=False)
    monkeypatch.setattr("hornlab_search.config.load_config", lambda p: cfg)
    monkeypatch.setattr("hornlab_search.design.space.DesignSpace.from_config",
                        classmethod(lambda cls, c: SPACE))
    monkeypatch.setattr(S, "analyze_space", lambda space, c, n_points: GEO)
    monkeypatch.setattr(S, "box_feasibility", lambda space, c, n: BOX)
    monkeypatch.setattr(S, "sigma_refusal_curve", lambda space, c, n: SIGMA)
    monkeypatch.setattr(S, "margin_model", lambda space, c, n: MARGIN)
    monkeypatch.setattr(SC, "_data_evidence", lambda run: {})

    card = SC.card_for(Path("synthetic.yaml"), run=None, points=8, box_n=8, sigma_n=8)
    rec = [r for r in card["recommendations"] if r["knob"] == "b"][0]
    assert rec["action"] == "link"
    assert rec["data_agrees"] == "unknown"
    assert "data_agrees=unknown" in SC._md(card)
