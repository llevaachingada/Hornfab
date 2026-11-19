"""The 2026-11-19 Fable night: every job's config loads, B6 arms share one identity and budget."""
import pathlib

import yaml

from hornlab_search.config import load_config

ROOT = pathlib.Path(__file__).resolve().parents[1]
NIGHT = ROOT / "docs/queue/fable_vt_b6_2026-11-19.yaml"


def test_night_configs_load_and_b6_arms_are_matched():
    jobs = yaml.safe_load(NIGHT.read_text(encoding="utf-8"))["jobs"]
    assert jobs[0]["id"] == "vt_v1__probe80"
    b6 = [j for j in jobs if j["id"].startswith("b6__")]
    assert len(b6) == 8 and len({j["config"] for j in b6}) == 8
    seen = set()
    for j in jobs:
        cfg = load_config(ROOT / j["config"])
        if j["id"].startswith("b6__"):
            assert cfg.objective_version == 10
            assert "v10" in str(cfg.raw.get("brief_file")) and "slope5" not in str(cfg.raw.get("brief_file"))
            assert (j["budget"], cfg.search.budget, cfg.search.budget_counts) == (120, 120, "valid")
            seen.add((j["id"].split("__")[1], cfg.search.seed))
    assert {s for _, s in seen} == {61901, 61902} and len(seen) == 8
