"""The 2026-11-19 SCOUT40 night: every job names an existing config, 40-eval budget, 1 h timeout,
warm starts only from same-brief runs, smooth-brief constructions kept on their own brief."""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
NIGHT = ROOT / "docs/queue/fable_scout40_2026-11-19.yaml"


def _cfg_path(job):
    if job["kind"] == "search":
        return ROOT / job["config"]
    argv = job["argv"]
    return ROOT / argv[argv.index("--config") + 1]


def test_scout40_jobs_are_budgeted_and_grouped():
    jobs = yaml.safe_load(NIGHT.read_text(encoding="utf-8"))["jobs"]
    assert len(jobs) == 18 and len({j["id"] for j in jobs}) == 18
    smooth = 0
    for j in jobs:
        p = _cfg_path(j)
        assert p.is_file(), p
        assert j["timeout_s"] == 3600
        budget = j["budget"] if j["kind"] == "search" else int(j["argv"][j["argv"].index("--budget") + 1])
        assert budget == 40
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
        brief = str(raw["brief_file"])
        assert "home_landscape_2026-11-15" in brief
        if "smooth" in brief:
            smooth += 1
            assert "warm_start" not in raw["search"]      # no cross-brief warm starts
        ws = raw["search"].get("warm_start")
        if ws:
            assert ws["top_k"] == 10 and not ws.get("allow_cross_brief", False)
    assert smooth == 4
