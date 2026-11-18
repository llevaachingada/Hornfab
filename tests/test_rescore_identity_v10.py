"""Fable WP 1.4 / 1.5 (cloud senior 2026-11-18): the v10 rescore is one local command.

Before this fix ``objective/replay.py`` dispatched v10 but its version gate still refused it
(``objective_version_not_supported_by_replay``), so ``rescore_identity.py rescore`` under a v10
brief scored zero rows. These tests pin: v10 replays through the canonical scorer, its score
identity differs from v9's, the ``--run-brief`` filter keeps only that brief's runs, and the
``compare`` view never pools identities.
"""
import json
import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from conftest import make_fake_response
from hornlab_search.objective import replay
from hornlab_search.solve.cache import save_response
from tools.analysis import rescore_identity as RI

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "docs" / "evidence" / "v10_rescore_2026-11-18"
V9 = EV / "home_v9_corridor_rescore.yaml"
V10 = EV / "home_v10_corridor_preferred_edge_rescore.yaml"
V7 = ROOT / "examples" / "briefs" / "home_landscape_2026-11-15" / "room_landscape_80x50_700_hf1440_v7.yaml"


def _fake_run(root: Path, name: str, brief_file: str, lane: str = "lane_a") -> Path:
    run = root / name
    ddir = run / "designs" / "design-1"
    ddir.mkdir(parents=True)
    save_response(ddir / "response.npz", make_fake_response())
    (run / "config.yaml").write_text(yaml.safe_dump({"name": lane, "brief_file": brief_file}),
                                     encoding="utf-8")
    return run


def test_offline_briefs_load_and_differ_only_by_version_and_region():
    b9 = yaml.safe_load(V9.read_text(encoding="utf-8"))
    b10 = yaml.safe_load(V10.read_text(encoding="utf-8"))
    assert b10["objective"].pop("ripple_region") == "preferred_edge"
    assert b10["objective"].pop("version") == 10 and b9["objective"].pop("version") == 9
    assert b9["objective"] == b10["objective"] and b9["target"] == b10["target"]
    assert b9["weights"] == b10["weights"]
    assert "constancy" not in b10["objective"]          # owner: floor first, then it counts
    ctx = replay.load_brief_context(V10)
    assert ctx.objective_version == 10
    assert ctx.objective_params.ripple_region == {"mode": "preferred_edge"}


def test_replay_scores_v10_through_the_canonical_scorer(tmp_path):
    run = _fake_run(tmp_path, "r1", "../briefs/x.yaml")
    b = replay.load_brief_context(V10)
    res = replay.replay_run_dir(run, "design-1", brief=b)
    assert replay.R_REPLAY_VERSION_UNSUPPORTED not in res.reasons
    assert res.objective_version == 10 and res.j is not None and math.isfinite(res.j)
    # Same number as calling the v10 scorer directly on the production metric path.
    m = replay._parity_metrics(make_fake_response(), b.target)
    j, _terms = replay._dispatch(10, m, make_fake_response(), b.target, b.weights,
                                 b.objective_params)
    assert res.j == pytest.approx(float(j), rel=0, abs=1e-12)


def test_rescore_v10_and_v9_columns_have_distinct_identities(tmp_path):
    run = _fake_run(tmp_path, "r1", "../briefs/home.yaml")
    s10 = RI.rescore([run], str(V10), tmp_path / "d10")
    s9 = RI.rescore([run], str(V9), tmp_path / "d9")
    assert s10["scored"] == 1 and s9["scored"] == 1
    assert s10["objective_version"] == 10 and s9["objective_version"] == 9
    assert len(s10["score_ids"]) == 1 and set(s10["score_ids"]).isdisjoint(s9["score_ids"])


def test_run_brief_filter_keeps_only_that_briefs_runs(tmp_path):
    home = _fake_run(tmp_path, "home", "..\\..\\briefs\\home_landscape_2026-11-15\\room_landscape_80x50_700_hf1440_v7.yaml")
    other = _fake_run(tmp_path, "other", "../briefs/room_80x60_700_hf1440_v7.yaml", lane="lane_b")
    s = RI.rescore([home, other], str(V10), tmp_path / "d",
                   run_brief="room_landscape_80x50_700_hf1440_v7")
    assert s["n"] == 1 and s["runs_skipped_other_brief"] == 1
    assert list(s["lane_best"]) == ["lane_a"]


def test_compare_ranks_within_columns_and_never_pools(tmp_path):
    a = _fake_run(tmp_path, "ra", "../b.yaml", lane="lane_a")
    cols = {}
    for label, brief in (("v9", V9), ("v10", V10)):
        RI.rescore([a], str(brief), tmp_path / label)
        cols[label] = tmp_path / label
    # Hand-edit one column so the two disagree; compare must report both ranks untouched.
    summ = json.loads((cols["v9"] / "rescore_summary.json").read_text())
    summ["lane_best"]["lane_z"] = {"j": -1.0, "run": "x", "design_hash": "h"}
    (cols["v9"] / "rescore_summary.json").write_text(json.dumps(summ))
    res = RI.compare(cols, tmp_path / "cmp")
    assert res["lanes"]["lane_z"] == {"v9": {"j": -1.0, "rank": 1, "design_hash": "h", "run": "x"}}
    assert res["lanes"]["lane_a"]["v9"]["rank"] == 2 and res["lanes"]["lane_a"]["v10"]["rank"] == 1
    csv = (tmp_path / "cmp" / "lane_bests_side_by_side.csv").read_text().splitlines()
    assert csv[0] == "lane,rank_v9,j_v9,design_v9,rank_v10,j_v10,design_v10"
    assert not any(res["columns"][k]["mixed_identity"] for k in cols)


def test_v7_brief_still_rescores(tmp_path):
    run = _fake_run(tmp_path, "r7", "../b.yaml")
    s = RI.rescore([run], str(V7), tmp_path / "d7")
    assert s["objective_version"] == 7 and s["n"] == 1 and s["scored"] == 1
    assert np.isfinite(s["lane_best"]["lane_a"]["j"])


def test_runs_root_discovers_nested_run_dirs_and_skips_non_runs(tmp_path):
    _fake_run(tmp_path / "runs", "20261116T000000Z-screen-aaaaaa", "../b.yaml")
    _fake_run(tmp_path / "runs" / "night31_2026-11-17", "t_arm", "../b.yaml", lane="lane_n")
    (tmp_path / "runs" / "nights" / "x").mkdir(parents=True)       # no config.yaml: not a run
    found = RI.discover_runs(tmp_path / "runs")
    assert [p.name for p in found] == ["20261116T000000Z-screen-aaaaaa", "t_arm"]
    rc = RI.main(["rescore", "--brief", str(V10), "--runs-root", str(tmp_path / "runs"),
                  "--out", str(tmp_path / "o")])
    assert rc == 0
    s = json.loads((tmp_path / "o" / "rescore_summary.json").read_text())
    assert s["n"] == 2 and set(s["lane_best"]) == {"lane_a", "lane_n"}


def test_rows_carry_stored_j_and_parity_delta_for_the_v7_self_check(tmp_path):
    run = _fake_run(tmp_path, "r7", "../b.yaml")
    RI.rescore([run], str(V7), tmp_path / "d7")
    row = json.loads((tmp_path / "d7" / "rescore.jsonl").read_text().splitlines()[0])
    assert "stored_j" in row and "parity_delta" in row
