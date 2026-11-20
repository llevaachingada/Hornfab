"""Overview phase 1 (gui/data_overview.py + /api/overview) and the GPU lane queue-log pick.

Headless and offline: a synthetic repo with examples/score_identities.yaml and a few run folders.
No solver, no GPU, no live runs/ tree.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import yaml

from hornlab_search.gui import data as D
from hornlab_search.gui import data_overview as O

REPO = Path(__file__).resolve().parents[1]


def _ts(minutes_ago: float) -> str:
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _repo(tmp_path: Path, identities: list[dict] | None = None) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    runs = root / "runs"
    runs.mkdir(parents=True)
    (root / "examples").mkdir()
    reg = {"schema": "score_identities_v1", "updated": "2026-11-19",
           "defaults": {"min_valid_for_leader": 3, "legacy_below_version": 7},
           "identities": identities if identities is not None else [
               {"id": "home_v10", "label": "Home v10", "brief": "home_v10", "objective_version": 10,
                "floor_j": 0.5, "status": "current"}]}
    (root / "examples" / "score_identities.yaml").write_text(yaml.safe_dump(reg), encoding="utf-8")
    return root, runs


_N = [0]


def _run(runs: Path, name: str, brief: str, version: int, js: list[float], minutes_ago: float = 5,
         family: str = "OSSE", ok: bool = True) -> str:
    _N[0] += 1
    rid = f"20261119T{_N[0]:06d}Z-screen-{_N[0]:06x}"
    d = runs / rid
    d.mkdir()
    cfg = {"name": name, "family": family, "brief": {"name": brief},
           "objective": {"version": version}}
    (d / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    rows = [{"n": i, "design_hash": f"{i:012x}", "ok": ok, "objective": j if ok else None,
             "mode": "screen", "family": family, "created_utc": _ts(minutes_ago + len(js) - i)}
            for i, j in enumerate(js)]
    (d / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return rid


# ---------------------------------------------------------------------------- typology

def test_typology_resolves_names_to_knowledge_cards():
    cases = {
        "c4_02_morph__hl__osse_rrect_morph_v7__b6_v10_s1": ("osse_ath", "morph"),
        "hl__crowe_x_osse_cd_v7": ("experimental_morphs", "crowe"),
        "scout40w2__klangfilm_b3_soft": ("experimental_morphs", "klangfilm"),
        "hl__rosse_rect_cd_v7_r100w": ("osse_ath", "r-osse"),
        "b2t__salmon_elliptical_v4": ("salmon", "salmon"),
        "sab__lecleach_ctrl_w1": ("lecleach_iwata", "lecleach"),
        "hl__biradial_es_style_smooth_v7": ("biradial", "biradial"),
        "freeform_sculpt": ("unclassified", "freeform"),
    }
    for name, (card, cons) in cases.items():
        t = O.typology_of(name)
        assert (t["card"], t["construction"]) == (card, cons), name


def test_typology_family_fallback_and_cards_exist():
    assert O.typology_of("mystery", "R-OSSE")["construction"] == "r-osse"
    assert O.typology_of("mystery", "FREEFORM")["card"] == "unclassified"
    for card in O.FAMILY_CARDS:
        if card != "unclassified":
            assert (REPO / O.KNOWLEDGE_CARD_REL.format(card=card)).is_file(), card


# ---------------------------------------------------------------------------- registry

def test_shipped_registry_is_valid():
    reg = O.load_identities(REPO)
    assert reg["error"] is None
    assert reg["identities"], "examples/score_identities.yaml lists no identity"
    for e in reg["identities"]:
        assert e["status"] in ("current", "diagnostic", "legacy")


def test_registry_errors_are_reported(tmp_path):
    root, _ = _repo(tmp_path)
    (root / "examples" / "score_identities.yaml").write_text("schema: nope\n", encoding="utf-8")
    assert "schema" in O.load_identities(root)["error"]
    (root / "examples" / "score_identities.yaml").unlink()
    assert O.load_identities(root)["error"]


# ---------------------------------------------------------------------------- overview

def test_lines_rank_ties_and_probes(tmp_path):
    root, runs = _repo(tmp_path)
    _run(runs, "c4_morph_a", "home_v10", 10, [3.0, 2.0, 1.2])
    _run(runs, "c4x_morph_cont", "home_v10", 10, [1.2, 1.1, 1.0])          # same line, better
    _run(runs, "hl__fold_warm", "home_v10", 10, [2.0, 1.6, 1.4])           # inside floor 0.5
    _run(runs, "hl__ext_throat", "home_v10", 10, [4.0, 3.0, 2.5])          # outside floor
    _run(runs, "probe_twinray", "home_v10", 10, [0.1])                     # probe: never leads
    d = O.overview(root, runs, days=1)
    ident = next(i for i in d["identities"] if i["id"] == "home_v10")
    ranked = [l for l in ident["lines"] if l.get("rank")]
    assert [l["construction"] for l in ranked] == ["morph", "fold", "ext_throat"]
    assert ranked[0]["best_j"] == 1.0 and len(ranked[0]["runs"]) == 2
    assert [l["tie"] for l in ranked] == [True, True, False]
    assert ident["n_tied"] == 2 and ident["leader_j"] == 1.0
    probe = next(l for l in ident["lines"] if l["construction"] == "twinray")
    assert probe["probe_only"] and probe.get("rank") is None
    assert d["kpis"]["runs"] == 5


def test_identities_never_mix_and_legacy_hidden(tmp_path):
    root, runs = _repo(tmp_path)
    _run(runs, "hl__fold_warm", "home_v10", 10, [1.5, 1.4, 1.3])
    _run(runs, "hl__fold_warm", "home_v10", 7, [0.2, 0.2, 0.1])            # unregistered v7
    _run(runs, "hl__fold_warm", "old_brief", 4, [0.1, 0.1, 0.1])           # legacy v4
    d = O.overview(root, runs, days=1)
    by = {i["id"]: i for i in d["identities"]}
    assert by["home_v10"]["leader_j"] == 1.3
    assert by["home_v10__v7"]["status"] == "unregistered" and by["home_v10__v7"]["floor_j"] is None
    assert "old_brief__v4" not in by
    assert "old_brief__v4" in {i["id"] for i in O.overview(root, runs, days=1, show_legacy=True)["identities"]}


def test_window_excludes_old_runs(tmp_path):
    root, runs = _repo(tmp_path)
    old = _run(runs, "hl__fold_warm", "home_v10", 10, [1.0, 1.0, 1.0], minutes_ago=3 * 1440)
    os.utime(runs / old / "search.ndjson", (0, 0))
    _run(runs, "hl__morph", "home_v10", 10, [2.0, 2.0, 2.0])
    d = O.overview(root, runs, days=1)
    assert d["kpis"]["runs"] == 1
    assert d["identities"][0]["lines"][0]["construction"] == "morph"


def test_api_route(tmp_path):
    from hornlab_search.gui.server import App
    root, runs = _repo(tmp_path)
    _run(runs, "hl__morph", "home_v10", 10, [2.0, 1.0, 1.5])
    out = App(root, runs)._get_uncoalesced("/api/overview", {"days": ["2"]})
    assert out["days"] == 2.0 and out["identities"][0]["leader_j"] == 1.0


# ---------------------------------------------------------------------------- GPU lane log pick

def test_gpu_lane_reads_newest_night_log_not_stale_gpu_named_log(tmp_path):
    _, runs = _repo(tmp_path)
    stale = runs / "overnight" / "queue_home_gpu_rest_2026-11-15.log"
    stale.parent.mkdir(parents=True)
    stale.write_text("=== 2026-11-15T08:00:00 START old_never_ended : hornlab-search search --config a.yaml\n",
                     encoding="utf-8")
    os.utime(stale, (1_000_000, 1_000_000))
    night = runs / "overnight" / "queue_compact400_next10_2026-11-19.log"
    night.write_text("=== 2026-11-19T17:00:00 START c4_done : x\n=== 2026-11-19T17:05:00 END c4_done exit 0\n"
                     "=== 2026-11-19T17:05:01 START c4_live : hornlab-search search --config b.yaml\n",
                     encoding="utf-8")
    cpu = runs / "overnight" / "queue_bo_cpu_2026-11-17.log"
    cpu.write_text("=== 2026-11-17T10:00:00 START cpu_job : y\n", encoding="utf-8")
    assert D._lane_queue_log(runs, "gpu") == night
    assert D._lane_queue_log(runs, "cpu") == cpu
    gpu = next(l for l in D.lane_status(runs)["lanes"] if l["lane"] == "gpu")
    assert gpu["job"]["name"] == "c4_live"
