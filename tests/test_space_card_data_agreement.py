"""Senior F8 (2026-11-17): an underpowered/absent links payload is "unknown", never "disagrees".

``space_card._data_agreement`` used to return ``False`` whenever ``links.py`` produced no
``proposed_links``.  That includes the degraded cases: no top decile at all (< 10 valid rows)
and a top decile with fewer than ``MIN_LINK_ROWS`` rows (``links.py`` stops below 5 rows).
Three lanes were therefore labelled "data disagrees" on **zero** rows.  Senior rule: never
claim a link disagrees with the data when n < 10.

Fixtures are synthetic run dirs (``search.ndjson`` + ``config.yaml`` + ``run.json``) built in
``tmp_path`` with the shared ``tests/test_tools_analysis_common`` helpers --- the same
synthetic-run-dir shape ``tests/test_tools_analysis_record_shadow.py`` writes --- and the
payloads come from the real ``links.analyse_run`` so ``top_decile_n`` matches what the tool
actually emits.
"""
from __future__ import annotations

from test_tools_analysis_common import load_tool, make_row, write_run

from tools.analysis import space_card as SC

links = load_tool("links")

# Geometric proposal: b = 2*a, a positive scale.  The synthetic runs below put
# b = 2*a on their low-objective rows, so ``links.py`` emits the same +2 sign.
LINK_AB = {"from": "a", "follower": "b", "scale": 2.0, "offset": 0.0, "median_abs_cos": 0.99}
LINK_AB_NEG = dict(LINK_AB, scale=-2.0)
BOX = {"per_knob": {}, "counts": {}, "ok_frac": 1.0}
SIGMA = {"0.10": {"bad_rate": 0.05}}
MARGIN = {"available": False}


def _geo(link):
    return {"keys": ["a", "b"], "knobs": {}, "links": [dict(link)],
            "legal_points": 8, "n_points": 8, "effective_dimension": 2,
            "feasible_from_seed": {}}


def _rec(link, data):
    recs = SC.recommend(_geo(link), BOX, SIGMA, MARGIN, data)
    hit = [r for r in recs if r["knob"] == link["follower"]]
    assert len(hit) == 1
    return hit[0], recs


def _card(link, data):
    geo = _geo(link)
    recs = SC.recommend(geo, BOX, SIGMA, MARGIN, data)
    return {"name": "synthetic", "config": "synthetic.yaml", "family": "OSSE",
            "generator": False, "geometry": geo, "box": BOX, "sigma": SIGMA,
            "margin_model": MARGIN, "recommendations": recs}


def _linked_run(tmp_path, n_valid, name):
    """Synthetic run with ``n_valid`` valid rows; ``b = 2*a`` on the low-objective rows."""
    rows = [make_row(i, float(i), params={"a": float(i), "b": 2.0 * float(i)})
            for i in range(n_valid)]
    return write_run(rows, tmp_path, name)


def _links_data(run):
    return {"links": links.analyse_run(run)}


def _payload(n, *proposals):
    payload = {"run_dir": "runs/x", "family": "OSSE", "top_decile_n": n,
               "pairs": [], "cma_directions": [], "proposed_links": list(proposals)}
    return {"links": payload}


def _proposal(knob_a, knob_b, scale):
    return {"knob_a": knob_a, "knob_b": knob_b, "scale": scale, "offset": 0.0,
            "r2": 0.9, "source": "rho_top_decile"}


# ------------------------------------------------------- absent / underpowered -> unknown

def test_no_top_decile_is_unknown_not_false(tmp_path):
    # 9 valid rows -> _common.top_decile() returns None -> links.py reports top_decile_n 0
    run = _linked_run(tmp_path, 9, "tiny")
    payload = links.analyse_run(run)
    assert payload["top_decile_n"] == 0
    assert payload["proposed_links"] == []

    data = {"links": payload}
    assert SC._data_n(data) == 0
    assert SC._data_agreement(LINK_AB, data) == "unknown"

    rec, recs = _rec(LINK_AB, data)
    assert rec["action"] == "link"            # geometric proposal survives
    assert rec["data_agrees"] == "unknown"    # but the data makes no claim
    assert rec["data_n"] == 0
    assert rec["data_verdict"] == "unknown (no top-decile rows)"
    assert all(r["action"] != "link_rejected_by_data" for r in recs)
    assert "data_agrees=false" not in SC._md(_card(LINK_AB, data))
    assert "link_rejected_by_data" not in SC._md(_card(LINK_AB, data))


def test_small_top_decile_is_unknown_with_n_shown(tmp_path):
    # 20 valid rows -> top decile = max(3, ceil(2)) = 3 rows; links.py degrades (< 5)
    run = _linked_run(tmp_path, 20, "small")
    payload = links.analyse_run(run)
    assert payload["top_decile_n"] == 3
    assert payload["proposed_links"] == []

    data = {"links": payload}
    assert SC._data_agreement(LINK_AB, data) == "unknown"

    rec, _ = _rec(LINK_AB, data)
    assert rec["action"] == "link"
    assert rec["data_agrees"] == "unknown"
    assert rec["data_n"] == 3
    assert rec["data_verdict"] == "unconfirmed (n=3)"
    md = SC._md(_card(LINK_AB, data))
    assert "unconfirmed (n=3)" in md
    assert "data_agrees=false" not in md


def test_low_n_ignores_a_matching_proposal():
    # The n gate, not the presence of a proposal, decides: n < 10 stays unknown even when
    # the payload happens to carry a same-sign pair.
    data = _payload(4, _proposal("a", "b", 3.0))
    assert SC._data_agreement(LINK_AB, data) == "unknown"
    rec, _ = _rec(LINK_AB, data)
    assert rec["action"] == "link"
    assert rec["data_agrees"] == "unknown"
    assert rec["data_verdict"] == "unconfirmed (n=4)"


def test_missing_top_decile_count_is_unknown():
    # No row count -> power cannot be established -> do not claim agreement or disagreement.
    data = {"links": {"run_dir": "runs/x", "family": "OSSE", "pairs": [],
                      "cma_directions": [], "proposed_links": [_proposal("a", "b", 3.0)]}}
    assert SC._data_n(data) is None
    assert SC._data_agreement(LINK_AB, data) == "unknown"


# ---------------------------------------------------------------- powered: n >= 10 only

def test_powered_agreement_is_true(tmp_path):
    # 100 valid rows -> top decile = floor-decile 10 rows; b = 2*a there -> same-sign link
    run = _linked_run(tmp_path, 100, "powered")
    payload = links.analyse_run(run)
    assert payload["top_decile_n"] == 10
    assert [(p["knob_a"], p["knob_b"]) for p in payload["proposed_links"]] == [("a", "b")]

    data = {"links": payload}
    assert SC._data_agreement(LINK_AB, data) is True
    rec, _ = _rec(LINK_AB, data)
    assert rec["action"] == "link"
    assert rec["data_agrees"] is True
    assert rec["data_n"] == 10
    assert rec["data_verdict"] == "agrees (n=10)"
    assert "data_agrees=true" in SC._md(_card(LINK_AB, data))


def test_powered_disagreement_is_false(tmp_path):
    # Same powered run, but the geometric proposal has the opposite scale sign -> False.
    run = _linked_run(tmp_path, 100, "powered")
    data = {"links": links.analyse_run(run)}
    assert SC._data_agreement(LINK_AB_NEG, data) is False
    rec, _ = _rec(LINK_AB_NEG, data)
    assert rec["action"] == "link_rejected_by_data"
    assert rec["data_agrees"] is False
    assert rec["data_n"] == 10
    assert rec["data_verdict"] == "disagrees (n=10)"
    md = SC._md(_card(LINK_AB_NEG, data))
    assert "data_agrees=false" in md and "disagrees (n=10)" in md


# --------------------------------------------------- recommend() claim on unknown verdict

def test_recommend_emits_no_data_justified_link_on_unknown(tmp_path):
    run = _linked_run(tmp_path, 20, "small")
    data = {"links": links.analyse_run(run)}          # n = 3, underpowered
    rec, recs = _rec(LINK_AB, data)

    # A geometric link may still be proposed ...
    assert rec["action"] == "link"
    assert rec["proposal"] == {"from": "a", "scale": 2.0, "offset": 0.0}
    # ... but nothing in it claims the data agreed, and no data rejection is emitted.
    assert rec["data_agrees"] == "unknown"
    assert rec["data_verdict"] == "unconfirmed (n=3)"
    assert "rejected" not in rec["why"]
    assert "data" not in rec["why"].lower()
    assert all(r["action"] != "link_rejected_by_data" for r in recs)
