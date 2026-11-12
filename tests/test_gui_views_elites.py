"""Group E.3 elites-catalog tests: cards over a committed gate-audit CSV.

Headless and offline: the same fixture shape as ``tests/test_gui_views_l2.py`` (synthetic run
folder + committed gate-audit CSV under ``docs/data/gate_audit_*/`` and ``scratch/gate_audit_*/``).
No audit = empty catalog. No solve runs and no real data is read.
"""
from __future__ import annotations

import json
from pathlib import Path

from hornlab_search.gui import data as D
from hornlab_search.gui.server import App

RID = "20261111T000000Z-screen-aaaaaa"
RID2 = "20260101T000000Z-screen-ffffff"
HASHES = ["aaaaaaaaaaaa", "bbbbbbbbbbbb", "deadbeef0001"]

# The run's own committed archive: two occupied coverage cells.
ARCHIVE = {
    "bins": [8, 8], "ranges": {"h": [20, 120], "v": [10, 100]},
    "descriptors": {"h": "mean_bw_h_deg", "v": "mean_bw_v_deg"},
    "cells": [{"h_center": 48.0, "v_center": 34.0, "objective": 4.0, "design_hash": HASHES[0]},
              {"h_center": 30.0, "v_center": 22.0, "objective": 5.0, "design_hash": HASHES[1]}],
}

AUDIT = (
    "run,tier,design,J,throat,load,h,v,di,bw8k,pass_all\n"
    f"{RID},verify,{HASHES[0]},4.0,True,False,True,False,True,False,True\n"
    f"{RID},screen,{HASHES[1]},5.0,False,True,False,False,True,True,False\n"
    f"{RID2},verify,{HASHES[2]},1.0,True,True,True,True,True,True,True\n"
)


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    runs = root / "runs"
    runs.mkdir(parents=True)
    return root, runs


def _audit_row(run: str, h: str, j: float, extra: str) -> str:
    return f"{run},verify,{h},{j},True,False,True,False,True,False,{extra}\n"


def test_elites_absent_audit(tmp_path: Path):
    """No audit anywhere -> an honest empty catalog (never invented data)."""
    root, runs = _repo(tmp_path)
    out = D.elites_catalog(runs, root)
    assert out["available"] is False and out["cards"] == [] and out["sources"] == []
    api = App(root, runs).get("/api/elites", {})
    assert api["available"] is False


AUDIT_HEADER = AUDIT.splitlines()[0] + "\n"


def test_elites_cards_from_committed_audit(tmp_path: Path):
    root, runs = _repo(tmp_path)
    audit = root / "docs" / "data" / "gate_audit_elites_smoke"
    audit.mkdir(parents=True)
    (audit / "gate_audit.csv").write_text(AUDIT, encoding="utf-8")
    run = runs / RID
    (run / "designs" / HASHES[1] / "mesh.msh").parent.mkdir(parents=True, exist_ok=True)
    (run / "designs" / HASHES[1] / "mesh.msh").write_text("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n",
                                                         encoding="utf-8")
    (run / "search.ndjson").write_text("", encoding="utf-8")
    (run / "run.json").write_text(json.dumps({"objective_version": 7}), encoding="utf-8")
    (run / "archive_heatmap.json").write_text(json.dumps(ARCHIVE), encoding="utf-8")

    out = D.elites_catalog(runs, root)
    assert out["available"] is True
    assert out["sources"] == ["docs/data/gate_audit_elites_smoke/gate_audit.csv"]
    assert out["n_pass"] == 2
    cards = {(c["run"], c["hash"]): c for c in out["cards"]}
    assert set(cards) == {(RID, HASHES[0]), (RID, HASHES[1]), (RID2, HASHES[2])}
    a, b, dead = cards[(RID, HASHES[0])], cards[(RID, HASHES[1])], cards[(RID2, HASHES[2])]
    # gate chips exist ONLY for the columns the CSV carries, and a fail never becomes a pass
    assert a["gates"] == {"throat": True, "load": False, "h": True, "v": False,
                          "di": True, "bw8k": False}
    assert a["pass_all"] is True and a["J"] == 4.0
    # run enrichment: J vN label, coverage cell from the run's own atlas, mesh presence
    assert a["run_linked"] is True and a["objective_version"] == 7
    assert a["coverage_cell"]["h_center"] == 48.0 and a["coverage_cell"]["v_center"] == 34.0
    assert a["coverage_cell"]["descriptors"]["h"] == "mean_bw_h_deg"
    assert a["has_mesh"] is False
    assert b["coverage_cell"]["h_center"] == 30.0 and b["has_mesh"] is True
    # a run that no longer exists: link + cell + version are absent, never guessed
    assert dead["run_linked"] is False and dead["coverage_cell"] is None \
        and dead["objective_version"] is None
    assert out["labels"]["throat"] == "round throat" and out["labels"]["bw8k"] == "8 kHz BW"
    # display order: passing rows first (lower J first), failing rows last
    assert [c["pass_all"] for c in out["cards"]] == [True, True, False]
    assert [c["J"] for c in out["cards"]] == [1.0, 4.0, 5.0]

    api = App(root, runs).get("/api/elites", {})
    assert api["available"] is True and len(api["cards"]) == 3


def test_elites_newest_audit_wins_and_dedupes(tmp_path: Path):
    """A design seen in two audits keeps its FIRST (newest-directory) entry, never doubles up."""
    root, runs = _repo(tmp_path)
    newer = root / "docs" / "data" / "gate_audit_elites_b"
    newer.mkdir(parents=True)
    (newer / "gate_audit.csv").write_text(
        AUDIT + _audit_row(RID, HASHES[1], 9.0, "True"), encoding="utf-8")
    older = root / "scratch" / "gate_audit_elites_a"
    older.mkdir(parents=True)
    (older / "gate_audit.csv").write_text(
        AUDIT_HEADER
        + _audit_row(RID, HASHES[0], 3.0, "True")
        + _audit_row(RID2, HASHES[2], 2.0, "True")
        + _audit_row(RID2, "cafe00000001", 2.5, "True"), encoding="utf-8")
    out = D.elites_catalog(runs, root)
    # deduped across both sources; the older audit keeps only its unique design
    assert {c["hash"] for c in out["cards"]} == set(HASHES) | {"cafe00000001"}
    assert out["sources"] == ["docs/data/gate_audit_elites_b/gate_audit.csv",
                              "scratch/gate_audit_elites_a/gate_audit.csv"]
    assert [c["source"] for c in out["cards"] if c["hash"] in HASHES] == \
        ["docs/data/gate_audit_elites_b/gate_audit.csv"] * 3   # newest audit won the dupes


def test_elites_newer_audit_passes_after_older_fail(tmp_path: Path):
    """A design the newest audit passes shows PASS even though an older audit failed it."""
    root, runs = _repo(tmp_path)
    newer = root / "docs" / "data" / "gate_audit_elites_c"
    newer.mkdir(parents=True)
    (newer / "gate_audit.csv").write_text(AUDIT_HEADER
                                          + _audit_row(RID, HASHES[0], 4.0, "False"),
                                          encoding="utf-8")
    older = root / "scratch" / "gate_audit_elites_d"
    older.mkdir(parents=True)
    (older / "gate_audit.csv").write_text(AUDIT_HEADER
                                          + _audit_row(RID, HASHES[0], 9.0, "True"),
                                          encoding="utf-8")
    out = D.elites_catalog(runs, root)
    assert len(out["cards"]) == 1
    assert out["cards"][0]["pass_all"] is False and out["cards"][0]["J"] == 4.0
