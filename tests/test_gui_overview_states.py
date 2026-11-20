"""WP2.4 -- per-line work states (gui/data_overview_states.py).

Synthetic payloads plus tiny run folders; no solver, no GPU, no live runs/ tree.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
from pathlib import Path

from hornlab_search.gui import data_overview_states as S

_N = [0]
CARDS = ("osse_ath",)


def _ts(minutes_ago: float) -> str:
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _rid() -> str:
    _N[0] += 1
    return f"20261119T{_N[0]:06d}Z-screen-{_N[0]:06x}"


def _write_run(runs: Path, rid: str, js: list[float]) -> str:
    d = runs / rid
    d.mkdir(parents=True, exist_ok=True)
    rows = [{"n": i, "ok": True, "objective": j,
             "created_utc": _ts(60 + len(js) - i)} for i, j in enumerate(js)]
    (d / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                                     encoding="utf-8")
    return rid


def _flat_run(runs: Path) -> str:
    return _write_run(runs, _rid(), [1.0] * 12)


def _improving_run(runs: Path) -> str:
    return _write_run(runs, _rid(), [2.0] * 9 + [1.5, 1.2, 1.0])


def _line(**kw) -> dict:
    base = {"key": "osse_ath|morph", "card": "osse_ath", "construction": "morph", "rank": 1,
            "best_j": 1.0, "best_run_id": None, "evals": 12, "valid": 12, "refused": 0,
            "refused_pct": 0.0, "last": _ts(60), "probe_only": False, "tie": False}
    base.update(kw)
    return base


def _payload(lines: list[dict]) -> dict:
    ranked = [ln for ln in lines if ln.get("rank") is not None]
    cells: dict = {}
    if ranked:
        best = min(ranked, key=lambda ln: ln["rank"])
        cells["home_v10"] = {"rank": best["rank"], "of": len(ranked),
                             "best_j": best["best_j"], "tie": False,
                             "construction": best["construction"]}
    return {"registry": {"min_valid_for_leader": 3},
            "identities": [{"id": "home_v10", "status": "current", "lines": lines}],
            "typology": [{"card": "osse_ath", "label": "OSSE / R-OSSE / ATH", "doc": None,
                          "evals": 12,
                          "constructions": sorted({ln["construction"] for ln in lines}),
                          "cells": cells}]}


def _walls(runs: Path, run_id: str, actions=("widen_hi",)) -> Path:
    d = runs / "analysis" / "set_x" / "walls_g1"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "walls.json"
    p.write_text(json.dumps({"run_dir": f"runs\\{run_id}", "family": "OSSE",
                             "proposal": [{"key": "k", "action": a} for a in actions]}),
                 encoding="utf-8")
    return p


# ---------------------------------------------------------------------------- each state

def test_state_converged(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    line = _line(best_run_id=_flat_run(runs))
    S.annotate_states(_payload([line]), runs)
    assert line["state"] == "converged"


def test_state_improving(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    line = _line(best_run_id=_improving_run(runs))
    S.annotate_states(_payload([line]), runs)
    assert line["state"] == "improving"


def test_state_box_limited(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    rid = _flat_run(runs)
    _walls(runs, rid)
    line = _line(best_run_id=rid)
    S.annotate_states(_payload([line]), runs)
    assert line["state"] == "box_limited"


def test_narrow_only_walls_never_claim_box_limited(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    rid = _flat_run(runs)
    _walls(runs, rid, actions=("narrow",))
    line = _line(best_run_id=rid)
    S.annotate_states(_payload([line]), runs)
    assert line["state"] == "converged"


def test_state_refusal_storm(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    line = _line(refused_pct=40.0, best_run_id=_improving_run(runs))
    S.annotate_states(_payload([line]), runs)
    assert line["state"] == "refusal_storm"


def test_state_probe(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    line = _line(probe_only=True, rank=None)
    S.annotate_states(_payload([line]), runs)
    assert line["state"] == "probe"


def test_state_stale(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    line = _line(best_run_id=_flat_run(runs), last=_ts(8 * 1440))
    S.annotate_states(_payload([line]), runs)
    assert line["state"] == "stale"


# ---------------------------------------------------------------------------- precedence

def test_precedence_order(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    improving = _improving_run(runs)
    _walls(runs, improving)                       # box_limited applies to every line below
    plain_improving = _improving_run(runs)        # no walls: lets "improving" beat "stale"
    stale = _ts(8 * 1440)

    probe = _line(rank=1, construction="p", probe_only=True, refused_pct=90.0,
                  best_run_id=improving, last=stale)
    storm = _line(rank=2, construction="r", refused_pct=90.0, best_run_id=improving, last=stale)
    box = _line(rank=3, construction="b", best_run_id=improving, last=stale)
    imp = _line(rank=4, construction="i", best_run_id=plain_improving, last=stale)
    flat = _flat_run(runs)
    old = _line(rank=5, construction="s", best_run_id=flat, last=stale)
    lines = [probe, storm, box, imp, old]

    S.annotate_states(_payload(lines), runs)
    states = {ln["construction"]: ln["state"] for ln in lines}
    assert states == {"p": "probe", "r": "refusal_storm", "b": "box_limited",
                      "i": "improving", "s": "stale"}
    # the whole precedence chain is probe > refusal_storm > box_limited > improving > stale
    assert S.STATE_ORDER == ("probe", "refusal_storm", "box_limited", "improving", "stale",
                             "converged")


# ---------------------------------------------------------------------------- cells, counts

def test_cell_gets_best_line_state_not_a_worse_line(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    best = _line(rank=1, construction="morph", best_run_id=_flat_run(runs))       # converged
    worse = _line(rank=2, construction="fold", best_run_id=_flat_run(runs), last=_ts(8 * 1440))
    ov = _payload([best, worse])
    S.annotate_states(ov, runs)
    assert best["state"] == "converged" and worse["state"] == "stale"
    assert ov["typology"][0]["cells"]["home_v10"]["state"] == "converged"


def test_states_summary_and_idempotence(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    improving = _improving_run(runs)
    _walls(runs, improving)
    lines = [_line(rank=1, construction="b", best_run_id=improving),
             _line(rank=2, construction="m", best_run_id=_flat_run(runs)),
             _line(rank=None, construction="p", probe_only=True)]
    ov = _payload(lines)

    first = copy.deepcopy(S.annotate_states(ov, runs))
    second = S.annotate_states(ov, runs)
    assert second == first, "annotate_states must be idempotent"

    counts = second["states"]
    assert set(counts) == set(S.STATE_ORDER)
    assert sum(counts.values()) == len(lines)
    assert counts["box_limited"] == 1 and counts["converged"] == 1 and counts["probe"] == 1


def test_never_raises_on_missing_or_partial_payload(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    assert S.annotate_states({}, runs) == {}
    partial = {"identities": None}
    assert S.annotate_states(partial, runs) is partial
    partial2 = {"identities": [{"id": "x"}], "typology": "nope"}
    out = S.annotate_states(partial2, runs)
    assert out is partial2 and out["states"] == {s: 0 for s in S.STATE_ORDER}
