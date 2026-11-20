"""GUI discovery (2026-10-26, owner: "if anything runs and saves in the folder it should show up"):
configs and briefs are found at any depth, the run list has no cap, and runs that no campaign.json
claims still get a per-brief leaderboard (auto campaigns). Offline, no GPU."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from hornlab_search.gui import data as D
from test_gui import _design, _row

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import run_campaign_night as N  # noqa: E402


def _run(runs: Path, rid: str, brief: str | None, name: str, best: float) -> Path:
    run = runs / rid
    run.mkdir(parents=True)
    cfg = {"name": name, "family": "FREEFORM", "bounds": {"L_mm": {"lo": 90.0, "hi": 140.0}}}
    if brief:
        cfg["brief"] = {"name": brief}
    (run / "config.yaml").write_text(yaml.safe_dump(cfg))
    rows = [_row(0, "aaaaaaaaaaaa", True, best + 5.0, 100.0), _row(1, "bbbbbbbbbbbb", True, best, 110.0)]
    (run / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    _design(run, "bbbbbbbbbbbb", 0.0)
    return run


def test_configs_and_briefs_are_found_in_subfolders(tmp_path):
    ex = tmp_path / "examples"
    (ex / "typologies" / "campaign_x").mkdir(parents=True)
    (ex / "typologies" / "campaign_x" / "cell.yaml").write_text("name: cell_one\nfamily: OSSE\n")
    (ex / "top.yaml").write_text("name: top\n")
    (ex / "catalog.yaml").write_text("entries: []\n")
    (ex / "briefs" / "campaign_x").mkdir(parents=True)
    (ex / "briefs" / "user").mkdir()
    (ex / "briefs" / "shipped_b.yaml").write_text("name: shipped_b\n")
    (ex / "briefs" / "user" / "mine.yaml").write_text("name: mine\n")
    (ex / "briefs" / "campaign_x" / "camp_b.yaml").write_text("name: camp_b\n")

    names = {c["name"]: c["path"] for c in D.list_configs(tmp_path)}
    assert names["cell_one"] == "examples/typologies/campaign_x/cell.yaml"
    assert "top" in names
    assert not any("briefs/" in p for p in names.values())          # briefs are never configs
    assert D._preview_config(tmp_path, "cell_one")["path"].endswith("campaign_x/cell.yaml")

    kinds = {b["name"]: b["kind"] for b in D.list_briefs(tmp_path)}
    assert kinds == {"shipped_b": "shipped", "mine": "user", "camp_b": "campaign_x"}


def test_preview_config_index_sees_a_new_subfolder_file(tmp_path):
    sub = tmp_path / "examples" / "typologies" / "later"
    sub.mkdir(parents=True)
    (tmp_path / "examples" / "a.yaml").write_text("name: a\n")
    D._preview_config(tmp_path, "a")                                # builds the cached index
    (sub / "b.yaml").write_text("name: b\n")                        # added after the index
    assert D._preview_config(tmp_path, "b")["path"].endswith("later/b.yaml")


def test_run_list_has_no_cap(tmp_path):
    runs = tmp_path / "runs"
    for i in range(305):
        (runs / f"20261026T{i // 60:02d}{i % 60:02d}00Z-screen-{i:06x}").mkdir(parents=True)
    assert len(D.list_runs(runs)) == 305


def test_tool_written_runs_at_depth_are_listed_and_routable(tmp_path):
    """`verify --verify-dir runs/<topic>/<id>` and a night's `<night>/<run>` are runs too.

    Owner rule (see module docstring): anything that runs and saves in the folder shows up. Their
    ids are the run-relative path joined with ``~`` (one URL segment); a run's own inline
    ``verify/`` tree and the BO study source tree are not independent runs (BO study sources are
    mirrored into top-level run folders, so listing them again would double-count)."""
    runs = tmp_path / "runs"
    top = _run(runs, "20261026T010000Z-screen-aaaaaa", "b", "top", 9.0)
    ss = runs / "source_sensitivity" / "ss_a"          # ndjson only: no run.json, no config
    ss.mkdir(parents=True)
    (ss / "search.ndjson").write_text(json.dumps(_row(0, "cccccccccccc", True, 4.0, 100.0)) + "\n")
    nr = runs / "night_2026-11-18" / "20261026T020000Z-screen-bbbbbb__refine"
    nr.mkdir(parents=True)
    (nr / "run.json").write_text(json.dumps({"mode": "screen"}))
    (nr / "search.ndjson").write_text(json.dumps(_row(1, "dddddddddddd", True, 7.0, 110.0)) + "\n")
    inline = top / "verify"
    inline.mkdir()
    (inline / "search.ndjson").write_text(json.dumps(_row(2, "eeeeeeeeeeee", True, 9.0, 100.0)) + "\n")
    study = runs / "study-0123456789abcdef" / "screen"
    study.mkdir(parents=True)
    (study / "run.json").write_text(json.dumps({"mode": "screen"}))
    # A hand-named top-level run (the committed `elites_<date>_<topic>` evidence dirs) is a run
    # too — named by its folder, not by the CLI's timestamp pattern.
    elite = runs / "elites_20261030_topic"
    elite.mkdir()
    (elite / "run.json").write_text(json.dumps({"mode": "screen"}))
    (elite / "search.ndjson").write_text(json.dumps(_row(3, "ffffffffffff", True, 8.0, 100.0)) + "\n")

    runs_by_id = {s["id"]: s for s in D.list_runs(runs)}
    assert "20261026T010000Z-screen-aaaaaa" in runs_by_id
    assert D._resolve_run(runs, "elites_20261030_topic") == elite
    assert runs_by_id["source_sensitivity~ss_a"]["n"] == 1
    assert runs_by_id["night_2026-11-18~20261026T020000Z-screen-bbbbbb__refine"]["best_j"] == 7.0
    assert not any(i.endswith("~verify") for i in runs_by_id)
    assert not any(i.startswith("study-") for i in runs_by_id)
    assert D._resolve_run(runs, "source_sensitivity~ss_a") == ss
    assert D.run_detail(runs, "source_sensitivity~ss_a")["summary"]["id"] == "source_sensitivity~ss_a"
    with pytest.raises(FileNotFoundError):
        D._resolve_run(runs, "source_sensitivity~nope")
    with pytest.raises(ValueError):
        D._resolve_run(runs, "..")


def test_started_run_without_rows_is_listed_and_opens(tmp_path):
    """A run killed between `new_run_dir` and its first row used to 404 on its own page; the Runs
    list showed it with blank cells and clicking it errored. It is a real run: list and open it."""
    runs = tmp_path / "runs"
    rid = "20261026T030000Z-screen-cccccc"
    rd = runs / rid
    rd.mkdir(parents=True)
    (rd / "run.json").write_text(json.dumps({"mode": "screen", "status": "running"}))
    (rd / "config.yaml").write_text("name: started\nfamily: OSSE\n")
    [s] = [x for x in D.list_runs(runs) if x["id"] == rid]
    assert s["n"] == 0 and s["last"] is None
    d = D.run_detail(runs, rid)
    assert d["summary"]["id"] == rid and d["J"] == [] and d["best"] is None


def test_unclaimed_runs_get_an_auto_campaign_per_brief_and_mode(tmp_path):
    runs = tmp_path / "runs"
    _run(runs, "20261026T010000Z-screen-aaaaaa", "camp_b", "cell_one", 12.0)
    _run(runs, "20261026T020000Z-screen-bbbbbb", "camp_b", "cell_two", 9.0)
    claimed = _run(runs, "20261026T030000Z-screen-cccccc", "camp_b", "cell_three", 1.0)
    _run(runs, "20261026T040000Z-screen-dddddd", None, "no_brief", 3.0)
    cdir = runs / "campaign_20261026T050000Z"
    cdir.mkdir()
    (cdir / "campaign.json").write_text(json.dumps({"tier": "screen", "brief_name": "camp_b", "entries": [
        {"name": "cell_three", "jobs": [{"seed": 1, "best_j": 1.0, "run_dir": str(claimed)}]}]}))

    camps = D.list_campaigns(runs)
    assert camps[0]["id"] == "campaign_20261026T050000Z"           # real campaigns first
    [auto] = [c for c in camps if c.get("auto")]
    assert auto["id"] == "auto_camp_b__screen" and auto["tier"] == "screen"
    assert auto["families"] == ["cell_one", "cell_two"]             # claimed + brief-less runs excluded
    assert not D.superseded(runs, auto["id"])

    d = D.campaign_detail(runs, auto["id"])
    assert [e["name"] for e in d["entries"]] == ["cell_two", "cell_one"]      # ranked by J
    assert d["entries"][0]["best_j"] == 9.0
    assert d["entries"][0]["best_run_id"] == "20261026T020000Z-screen-bbbbbb"
    assert d["entries"][0]["jobs"][0]["seed"] == "bbbbbb"           # never "None" in the UI


def test_night_runner_queue_lines_parse_on_the_status_page(tmp_path):
    log = tmp_path / "overnight" / "queue_smoke.log"
    N.write_queue_line(log, "START t0__cell : hornlab-search.exe search --config x.yaml --budget 1")
    N.write_queue_line(log, "END t0__cell exit 0")
    N.write_queue_line(log, "QUEUE DONE")
    [step] = [s for s in D.queue_steps(log) if s["name"] == "t0__cell"]
    assert step["started"] and step["ended"] and step["exit"] == 0
    assert step["command"].startswith("hornlab-search.exe search")
