"""WP2 (GUI plan 2026-11-12): elites catalog reads each run once and caches by file mtimes.

Offline: a synthetic runs tree + gate-audit CSV; no solver.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import yaml

from hornlab_search.gui import data as D

RID = "20261112T120000Z-screen-abc111"
H1, H2 = "aaaaaaaaaaaa", "bbbbbbbbbbbb"


def _tree(tmp: Path) -> tuple[Path, Path]:
    root = tmp
    runs = root / "runs"
    rd = runs / RID
    rd.mkdir(parents=True)
    (rd / "search.ndjson").write_text(json.dumps({"n": 0, "design_hash": H1, "ok": True, "objective": 1.0}) + "\n")
    (rd / "config.yaml").write_text(yaml.safe_dump({"name": "x", "objective": {"version": 7}}))
    (rd / "archive_heatmap.json").write_text(json.dumps({
        "descriptors": {"h": "bw_h", "v": "bw_v"},
        "cells": [{"design_hash": H1, "objective": 2.0, "h_center": 1, "v_center": 1},
                  {"design_hash": H1, "objective": 1.0, "h_center": 2, "v_center": 3},
                  {"design_hash": H2, "objective": 5.0, "h_center": 9, "v_center": 9}]}))
    ad = root / "docs" / "data" / "gate_audit_2026-11-12"
    ad.mkdir(parents=True)
    rows = ["run,design,J,tier,throat,load,pass_all",
            f"{RID},{H1},1.0,screen,pass,fail,false",
            f"{RID},{H2},5.0,verify,pass,pass,true",
            f"20261111T000000Z-screen-gone00,{H1},3.0,screen,pass,pass,true"]
    (ad / "gate_audit.csv").write_text("\n".join(rows) + "\n")
    return root, runs


def test_elites_cards_use_best_cell_and_version(tmp_path):
    D._ELITES_CACHE.clear()
    root, runs = _tree(tmp_path)
    out = D.elites_catalog(runs, root)
    by = {(c["run"], c["hash"]): c for c in out["cards"]}
    c1 = by[(RID, H1)]
    assert c1["objective_version"] == 7 and c1["run_linked"] is True
    assert c1["coverage_cell"]["h_center"] == 2 and c1["coverage_cell"]["v_center"] == 3   # lowest objective
    assert c1["coverage_cell"]["descriptors"] == {"h": "bw_h", "v": "bw_v"}
    gone = by[("20261111T000000Z-screen-gone00", H1)]
    assert gone["run_linked"] is False and gone["objective_version"] is None and gone["coverage_cell"] is None
    assert out["n_pass"] == 2


def test_elites_reads_each_run_once(tmp_path, monkeypatch):
    D._ELITES_CACHE.clear()
    root, runs = _tree(tmp_path)
    calls = []
    real = D.run_objective_version
    monkeypatch.setattr(D, "run_objective_version", lambda d: calls.append(d) or real(d))
    D.elites_catalog(runs, root)
    assert len(calls) == 1          # two CSV rows on the same run -> one read


def test_elites_cache_invalidates_on_csv_change(tmp_path):
    D._ELITES_CACHE.clear()
    root, runs = _tree(tmp_path)
    a = D.elites_catalog(runs, root)
    assert D.elites_catalog(runs, root) is a                      # cached
    csv = next((root / "docs" / "data").glob("gate_audit_*/gate_audit.csv"))
    csv.write_text(csv.read_text() + f"{RID},cccccccccccc,9.0,screen,pass,pass,true\n")
    t = time.time() + 5
    os.utime(csv, (t, t))
    b = D.elites_catalog(runs, root)
    assert b is not a and len(b["cards"]) == len(a["cards"]) + 1
