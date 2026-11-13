"""Elites catalog brief/family/target enrichment: readable cards, computed once per run.

Offline: a synthetic runs tree (config.yaml + search.ndjson) and a committed gate-audit CSV
under ``docs/data/gate_audit_x/``, the same tree shape ``tests/test_gui_views_elites.py`` uses.
The brief keys mirror the real ``examples/briefs/*.yaml`` nesting: ``target.coverage_h_deg``,
``target.coverage_v_deg``, ``target.band_lo_hz``, ``target.band_hi_hz`` and
``envelope.max_mouth_w_mm`` / ``max_mouth_h_mm`` / ``max_depth_mm``.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from hornlab_search.gui import data as D

RID = "20261112T120000Z-screen-abc111"
RID_FALLBACK = "20261112T130000Z-screen-def222"
RID_GONE = "20261111T000000Z-screen-gone00"
H1, H2, H3, H4 = "aaaaaaaaaaaa", "bbbbbbbbbbbb", "cccccccccccc", "dddddddddddd"


def _run(runs: Path, rid: str, cfg: dict, first_row: dict) -> Path:
    rd = runs / rid
    rd.mkdir(parents=True)
    (rd / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    (rd / "search.ndjson").write_text(json.dumps(first_row) + "\n", encoding="utf-8")
    return rd


def _tree(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    runs = root / "runs"
    runs.mkdir(parents=True)
    _run(runs, RID, {
        "name": "hifi_native",
        "family": "OSSE",
        "brief": {
            "name": "hifi_90x60_1in",
            "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 300.0,
                         "max_depth_mm": 220.0},
            "target": {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0,
                       "band_lo_hz": 700.0, "band_hi_hz": 5500.0},
        },
    }, {"family": "IGNORED", "ok": True})
    # No config family: the first ndjson row supplies it, exactly like _run_summary.
    _run(runs, RID_FALLBACK, {
        "name": "rollback",
        "brief": {
            "name": "osse_75x45",
            "envelope": {"max_mouth_w_mm": 750.0, "max_mouth_h_mm": 600.0},
            "target": {"coverage_h_deg": 75.0, "coverage_v_deg": 45.0, "band_lo_hz": 700.0},
        },
    }, {"family": "R-OSSE", "ok": True})
    audit = root / "docs" / "data" / "gate_audit_x"
    audit.mkdir(parents=True)
    (audit / "gate_audit.csv").write_text(
        "run,tier,design,J,throat,load,h,v,di,bw8k,pass_all\n"
        f"{RID},verify,{H1},4.0,True,False,True,False,True,False,True\n"
        f"{RID},screen,{H2},5.0,False,True,False,False,True,True,False\n"
        f"{RID_FALLBACK},verify,{H3},1.0,True,True,True,True,True,True,True\n"
        f"{RID_GONE},verify,{H4},2.0,True,True,True,True,True,True,True\n",
        encoding="utf-8")
    return root, runs


def _by_hash(out: dict) -> dict[str, dict]:
    return {c["hash"]: c for c in out["cards"]}


def test_card_carries_brief_family_and_brief_target(tmp_path: Path):
    D._ELITES_CACHE.clear()
    root, runs = _tree(tmp_path)
    card = _by_hash(D.elites_catalog(runs, root))[H1]
    assert card["brief"] == "hifi_90x60_1in"
    assert card["family"] == "OSSE"
    assert card["brief_target"] == {
        "h_deg": 90.0, "v_deg": 60.0, "f_lo_hz": 700.0, "f_hi_hz": 5500.0,
        "max_mm": 400.0,                      # largest envelope dimension
    }
    # Existing card facts are unchanged alongside the new fields.
    assert card["pass_all"] is True and card["J"] == 4.0 and card["run_linked"] is True


def test_family_falls_back_to_first_ndjson_row_and_absent_keys_are_none(tmp_path: Path):
    D._ELITES_CACHE.clear()
    root, runs = _tree(tmp_path)
    card = _by_hash(D.elites_catalog(runs, root))[H3]
    assert card["brief"] == "osse_75x45"
    assert card["family"] == "R-OSSE"          # config had no family
    assert card["brief_target"] == {
        "h_deg": 75.0, "v_deg": 45.0, "f_lo_hz": 700.0,
        "f_hi_hz": None,               # absent in this brief
        "max_mm": 750.0,               # max_depth_mm absent; largest remaining dimension
    }


def test_missing_run_gets_nulls(tmp_path: Path):
    D._ELITES_CACHE.clear()
    root, runs = _tree(tmp_path)
    card = _by_hash(D.elites_catalog(runs, root))[H4]
    assert card["run_linked"] is False
    assert card["brief"] is None and card["family"] is None and card["brief_target"] is None


def test_top_level_briefs_and_families_sorted_and_distinct(tmp_path: Path):
    D._ELITES_CACHE.clear()
    root, runs = _tree(tmp_path)
    out = D.elites_catalog(runs, root)
    assert out["briefs"] == ["hifi_90x60_1in", "osse_75x45"]
    assert out["families"] == ["OSSE", "R-OSSE"]       # sorted, not first-seen order
    # Two cards share RID/brief -> one distinct brief for that run, and the missing run adds none.
    assert [c["hash"] for c in out["cards"]] == [H3, H4, H1, H2]   # existing sort order pinned
    assert out["n_pass"] == 3

    api = D.elites_catalog(runs, root)
    assert api is out                                       # per-run config reads stay cached
