"""P0a — CMA-MAE dual-archive semantics (``cma-me-archive-v3``).

CMA-MAE needs a *soft* search archive (finite ``threshold_min``, ``learning_rate < 1``) so the
emitter keeps receiving improvements, but that archive's cell occupant is NOT the best design ever
seen in the cell: once the threshold has decayed, a slightly worse objective can still be admitted
and replaces the better elite. The exported atlas must therefore come from a second, *hard*
best-in-cell archive (``learning_rate=1.0``, ``threshold_min=-inf``), exactly as plain CMA-ME.

These regressions pin that split:
* direct ribs pair — same cell, archive objectives 10 then 9 (J = -10 then -9 under
  ``objective=-J``): the soft archive stores 9, the hard result archive keeps 10;
* a deterministic fake-evaluation run — ``archive.json``/``archive_heatmap.json`` describe the hard
  result archive, while the soft search archive is only a labelled ``archive_learning.json``
  diagnostic (never the atlas source);
* run.json records the split (and plain CMA-ME still has no ``maes`` key and exports the hard
  archive).
"""
from __future__ import annotations

import dataclasses
import json

import numpy as np
import pytest

from hornlab_search.search import cma_me as qd_mod
from hornlab_search.search.evaluate import append_ndjson, evaluation_to_row, row_to_evaluation
from hornlab_search.types import Evaluation, MetricSet, SolveOutcome
from test_search_cma_mae import MAES
from test_search_cma_me import knob_eval, qd_block, run_json, run_qd, two_knob_cfg


# ---------------------------------------------------------------- helpers


def record_archives(monkeypatch):
    """Capture the two ``FailureExcludingGridArchive`` instances production constructs.

    The module-level factory resolves the symbol at call time, so patching the module attribute
    records both archives without changing the threshold policy under test.
    """
    made = []
    base = qd_mod.FailureExcludingGridArchive

    class Recording(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            made.append(self)

    monkeypatch.setattr(qd_mod, "FailureExcludingGridArchive", Recording)
    return made


def constant_cell_eval(cfg, log):
    """A deterministic stand-in for ``evaluate`` that puts every candidate in ONE cell.

    Both descriptors are a constant 90 deg. The archive objective (``-J``) decreases with each new
    evaluation: 10, 9, 8, ... So a hard archive keeps the seed (10) while a soft one admits the
    later, worse-in-J points and ends on the maximum of the last told batch. Cache hits are
    honoured and every new evaluation writes its real ndjson row.
    """
    freqs = np.linspace(float(cfg.target_raw["band_lo_hz"]), float(cfg.target_raw["band_hi_hz"]), 9)

    def fake(design, space, cfg_, mode, run_dir, store, backend, *, ctx=None, **kw):
        key = f"{design.hash()}-fake-mesh-fake-solve"
        if ctx is not None and key in ctx.known:
            return dataclasses.replace(ctx.known[key], design=design)
        archive_objective = 10.0 - float(len(log))     # decreasing -> a soft archive regresses
        j = -archive_objective
        n = freqs.size
        metrics = MetricSet(
            freqs_hz=freqs.copy(), bw_h_deg=np.full(n, 90.0), bw_v_deg=np.full(n, 90.0),
            di_db=np.zeros(n), di_source="cuts_estimate", ripple_h_db=np.zeros(n),
            ripple_v_db=np.zeros(n), on_axis_db=np.zeros(n), z_throat_real=None, scalars={})
        ev = Evaluation(design_hash=design.hash(), design=design, mesh_hash="fake-mesh",
                        solve_hash="fake-solve", objective=j, terms={"total": j}, metrics=metrics,
                        mesh=None, outcome=SolveOutcome(True, None, 0.0, None, ""), cached=False,
                        error="")
        log.append(design.hash())
        if ctx is not None and run_dir is not None:
            row = evaluation_to_row(ev, mode, ctx.n_rows, {"mesh": 0.0, "solve": 0.0, "total": 0.0})
            append_ndjson(run_dir / "search.ndjson", row)
            ctx.n_rows += 1
            ctx.known[key] = row_to_evaluation(row)
        return ev

    return fake


def _load(run_dir, name):
    return json.loads((run_dir / name).read_text(encoding="utf-8"))


def _seed_objective(run_dir):
    return float(run_json(run_dir)["seed"]["objective"])


# ---------------------------------------------------------------- (a) direct archive pair


def test_soft_learning_archive_admits_a_worse_elite_but_hard_result_archive_keeps_the_best():
    pytest.importorskip("ribs", reason="ribs not installed")
    soft = qd_mod.make_qd_archive(soft=True, solution_dim=2, bins=(2, 2), seed=1234,
                                  maes=dict(MAES))
    hard = qd_mod.make_qd_archive(soft=False, solution_dim=2, bins=(2, 2), seed=1234)

    assert soft.learning_rate == pytest.approx(0.05) and soft.learning_rate < 1.0
    assert np.isfinite(soft.threshold_min) and soft.threshold_min == pytest.approx(-999.0)
    assert hard.learning_rate == 1.0 and hard.threshold_min == -np.inf

    sol = np.asarray([[0.2, 0.3]], dtype=float)
    meas = np.asarray([[90.0, 90.0]], dtype=float)      # same cell for both adds
    for arc in (soft, hard):
        arc.add(solution=sol, objective=np.asarray([10.0]), measures=meas)
    for arc in (soft, hard):
        arc.add(solution=sol, objective=np.asarray([9.0]), measures=meas)

    # Archive objectives 10 then 9 are J = -10 then J = -9: the soft threshold accepted the worse
    # (higher J) design — the exact regression this split removes from the exported atlas.
    assert float(np.asarray(soft.data()["objective"]).reshape(-1)[0]) == pytest.approx(9.0)
    assert float(np.asarray(hard.data()["objective"]).reshape(-1)[0]) == pytest.approx(10.0)


# ---------------------------------------------------------------- (b)/(d) MAE export source


def test_mae_exports_the_hard_result_archive_and_labels_the_learning_diagnostic(
        smoke_cfg, tmp_path, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = two_knob_cfg(smoke_cfg, qd=qd_block(maes=dict(MAES), bins_h=2, bins_v=2))
    cfg = dataclasses.replace(cfg, search=dataclasses.replace(cfg.search, popsize=2))
    made = record_archives(monkeypatch)
    log = []
    monkeypatch.setattr(qd_mod, "evaluate", constant_cell_eval(cfg, log))
    rd = tmp_path / "r"
    run_qd(cfg, rd, 5)                                   # seed + two full generations of 2

    assert len(made) == 2
    search_arc, result_arc = made
    assert search_arc.learning_rate == pytest.approx(0.05)
    assert np.isfinite(search_arc.threshold_min)
    assert result_arc.learning_rate == 1.0 and result_arc.threshold_min == -np.inf
    assert result_arc is not search_arc

    # Hard result archive keeps the seed's archive objective 10; the soft search archive regresses.
    hard_obj = float(np.asarray(result_arc.data()["objective"]).reshape(-1)[0])
    soft_obj = float(np.asarray(search_arc.data()["objective"]).reshape(-1)[0])
    assert hard_obj == pytest.approx(10.0)
    assert soft_obj < hard_obj

    export = _load(rd, "archive.json")
    assert len(export["cells"]) == 1
    cell = export["cells"][0]
    # Export is the hard result archive: the seed (archive objective 10 -> J -10), not the soft
    # archive's later, worse shape.
    assert cell["design_hash"] == run_json(rd)["seed"]["design_hash"]
    assert cell["design_hash"] != log[-2] and cell["design_hash"] != log[-1]
    assert cell["objective"] == pytest.approx(-hard_obj)
    assert cell["objective"] == pytest.approx(_seed_objective(rd))

    heat = _load(rd, "archive_heatmap.json")
    assert set(heat) == {"bins", "ranges", "cells", "descriptors"}   # GUI schema unchanged
    assert len(heat["cells"]) == 1
    assert heat["cells"][0]["design_hash"] == cell["design_hash"]
    assert heat["cells"][0]["objective"] == pytest.approx(cell["objective"])

    learning = _load(rd, "archive_learning.json")
    assert learning["role"] == "learning_archive_diagnostic"
    assert learning["diagnostic"] is True
    assert learning["learning_rate"] == pytest.approx(0.05)
    assert learning["threshold_min"] == pytest.approx(-999.0)
    assert "result archive" in learning["note"]
    assert len(learning["cells"]) == 1
    lcell = learning["cells"][0]
    assert lcell["objective"] == pytest.approx(-soft_obj)
    assert lcell["objective"] > cell["objective"]            # worse J than the exported elite
    assert lcell["design_hash"] != cell["design_hash"]

    qd = run_json(rd)["qd"]
    assert qd["protocol"] == "cma-me-archive-v3"
    assert qd["search_archive"] == {"role": "search", "kind": "cma_mae_soft",
                                    "learning_rate": 0.05, "threshold_min": -999.0}
    assert qd["result_archive"] == {"role": "best_in_cell", "learning_rate": 1.0,
                                    "threshold_min": "-inf",
                                    "export": ["archive.json", "archive_heatmap.json"]}
    assert qd["learning_archive"]["role"] == "learning_archive_diagnostic"
    assert qd["learning_archive"]["file"] == "archive_learning.json"
    assert qd["maes"] == dict(MAES)
    assert qd["failure_exclusion"]["shared_mae_thresholds"] is False
    note = qd["failure_exclusion"]["note"]
    assert "Each archive keeps its own threshold semantics" in note
    assert "always hard" in note


def test_plain_cma_me_has_no_maes_key_and_exports_the_hard_archive(smoke_cfg, tmp_path,
                                                                   monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    cfg = two_knob_cfg(smoke_cfg, qd=qd_block(bins_h=4, bins_v=4))
    made = record_archives(monkeypatch)
    monkeypatch.setattr(qd_mod, "evaluate", knob_eval(cfg))
    rd = tmp_path / "plain"
    run_qd(cfg, rd, 30)

    assert len(made) == 2
    for arc in made:                                     # both are hard in plain CMA-ME
        assert arc.learning_rate == 1.0 and arc.threshold_min == -np.inf

    qd = run_json(rd)["qd"]
    assert "maes" not in qd
    assert "learning_archive" not in qd
    assert qd["search_archive"] == {"role": "search", "kind": "cma_me_hard",
                                    "learning_rate": 1.0, "threshold_min": "-inf"}
    assert qd["result_archive"]["role"] == "best_in_cell"
    assert not (rd / "archive_learning.json").exists()

    export = _load(rd, "archive.json")
    expected = sorted(-float(o) for o in np.asarray(made[1].data()["objective"]).reshape(-1))
    assert sorted(c["objective"] for c in export["cells"]) == pytest.approx(expected)
    heat = _load(rd, "archive_heatmap.json")
    assert len(heat["cells"]) == len(export["cells"])
