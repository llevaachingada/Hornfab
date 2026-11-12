"""Group E.1 analysis-page tests: read-only rendering of the Group A tool outputs.

The fixtures write the exact JSON files `tools/analysis/*` produce (schema revision
2026-11-12, per `git show day/A-analysis:tools/analysis/schema.md`) under a synthetic
``runs/analysis/``, plus unknown-tool and malformed extras to prove defensive reading. No
analysis is ever executed and no solve runs.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hornlab_search.gui import data as D
from hornlab_search.gui.server import App

GEN = "2026-11-12T18:00:00Z"

CONVERGENCE = {
    "tool": "convergence", "generated_utc": GEN,
    "runs": [
        {"run_dir": "runs/20261111T000000Z-screen-aaaaaa", "brief": "seed1030", "family": "OSSE",
         "objective_version": 4, "n_new_valid": 3, "final_best": 12.34,
         "curve": [{"n": 1, "best": 22.5, "wall_s": 19.0},
                   {"n": 2, "best": 15.0, "wall_s": 38.0},
                   {"n": 3, "best": 12.34, "wall_s": 60.0}],
         "evals_to_5pct": 2, "evals_to_1pct": None, "last20_improvement": False,
         "brand_new_field_day_a_may_add": {"x": 1}},
        {"run_dir": "runs/20261111T000001Z-screen-bbbbbb", "brief": "seed1031", "family": "OSSE",
         "objective_version": 4, "n_new_valid": 2, "final_best": 18.0,
         "curve": [{"n": 1, "best": 30.0}, {"n": 2, "best": 18.0}],
         "evals_to_5pct": None, "last20_improvement": True},
    ],
}
SEED_VARIANCE = {
    "tool": "seed_variance", "generated_utc": GEN,
    "seed_rule": "A beats B only when medians differ by more than both spreads",
    "groups": {"g1": {"n_seeds": 2,
                      "seeds": [{"run_dir": "r1", "cma_seed": 1030, "best_j": 12.3},
                                {"run_dir": "r2", "cma_seed": 1031, "best_j": 14.5}],
                      "median_best": 13.4, "spread_best": 2.2, "ci95_median_best": [11.0, 15.9]},
               "g2": {"n_seeds": 1, "seeds": [{"run_dir": "r3", "best_j": 40.0}],
                      "median_best": 40.0, "spread_best": 0.0, "ci95_median_best": None}},
    "verdicts": [
        {"a": "g1", "b": "g2", "median_a": 13.4, "median_b": 40.0, "spread_a": 2.2,
         "spread_b": 0.5, "n_seeds": 2, "verdict": "indicative", "rule_holds": True},
    ],
}
SENSITIVITY = {
    "tool": "sensitivity", "generated_utc": GEN, "run_dir": "r1", "n_valid": 110,
    "spearman": [{"key": "a_deg", "rho": -0.41, "rho_abs": 0.41, "n": 110},
                 {"key": "L_mm", "rho": 0.2, "rho_abs": 0.2, "n": 110}],
    "top_decile_shift": [{"key": "a_deg", "mean_all": 41.2, "mean_top": 38.7,
                          "shift_norm": -0.03}],
    "surrogate": None,
}
LINKS = {
    "tool": "links", "generated_utc": GEN, "run_dir": "r1",
    "pairs": [{"a": "a_deg", "b": "n", "rho": -0.72,
               "fit": {"scale": 0.104, "offset": 1.88, "r2": 0.55}}],
    "cma_directions": [{"rank": 1, "eigenvalue": 0.42, "fraction": 0.61,
                        "keys": ["a_deg", "n"]}],
    "proposed_links": [{"knob_b": "n", "knob_a": "a_deg", "scale": 0.104, "offset": 1.88,
                        "r2": 0.55, "source": "rho_top_decile"}],
}
WALLS = {
    "tool": "walls", "generated_utc": GEN, "run_dir": "r1",
    "walls": [{"key": "L_mm", "lo": 140.0, "hi": 420.0, "frac_lo": 0.18, "frac_hi": 0.55,
               "wall_hi": True, "wall_lo": False}],
    "proposal": [{"key": "L_mm", "action": "widen_hi", "new_lo": 156.0, "new_hi": 462.0,
                  "reason": "55% of top-decile within 3% of hi; top-decile range padded 5%"}],
}
REPORT_MD = "# Day report\n\nSeed group g1: see tables.\n"


def _write(base: Path, name: str, payload) -> None:
    base.mkdir(parents=True, exist_ok=True)
    (base / name).write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture()
def analysis(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "repo"
    adir = root / "runs" / "analysis"
    day1 = adir / "day_2026-11-12"
    for name, payload in (("convergence.json", CONVERGENCE), ("seed_variance.json", SEED_VARIANCE),
                          ("sensitivity.json", SENSITIVITY), ("links.json", LINKS),
                          ("walls.json", WALLS)):
        _write(day1, name, payload)
    (day1 / "REPORT.md").write_text(REPORT_MD, encoding="utf-8")
    # a second set: one valid header-less tool + one malformed JSON + one unknown tool
    day2 = adir / "other_day"
    day2.mkdir(parents=True)
    (day2 / "convergence.json").write_text("{not json", encoding="utf-8")
    _write(day2, "custom_extra.json", {"anything": True})
    # top-level files belong to the "." set
    _write(adir, "convergence.json", {"tool": "convergence", "generated_utc": GEN, "runs": []})
    return root, root / "runs", adir


def test_analysis_sets_listing(analysis):
    root, _, adir = analysis
    sets = {s["id"]: s for s in D.analysis_sets(adir)}
    assert set(sets) == {".", "day_2026-11-12", "other_day"}
    assert sets["day_2026-11-12"]["tools"] == [
        "convergence", "seed_variance", "sensitivity", "links", "walls"]
    assert sets["day_2026-11-12"]["has_report_md"] is True
    assert sets["day_2026-11-12"]["generated_utc"] == GEN
    assert sets["other_day"]["tools"] == []            # malformed convergence: skipped, not crashed
    assert sets["."]["tools"] == ["convergence"]
    assert D.analysis_sets(root / "nowhere") == []


def test_analysis_report_passes_payloads_through(analysis):
    _, runs, adir = analysis
    d = D.analysis_report(adir, "day_2026-11-12")
    assert d["id"] == "day_2026-11-12" and d["generated_utc"] == GEN
    conv = d["convergence"]
    assert len(conv["runs"]) == 2
    assert [p["best"] for p in conv["runs"][0]["curve"]] == [22.5, 15.0, 12.34]
    assert conv["runs"][0]["brand_new_field_day_a_may_add"] == {"x": 1}   # unknown fields ride along
    assert d["seed_variance"]["verdicts"][0]["verdict"] == "indicative"
    assert d["links"]["proposed_links"][0]["r2"] == 0.55
    assert d["walls"]["walls"][0]["wall_hi"] is True
    assert d["report_md"] == REPORT_MD and d["report_md_truncated"] is False


def test_analysis_report_defensive_cases(analysis):
    _, runs, adir = analysis
    d = D.analysis_report(adir, "other_day")
    assert d["tools"] == [] and d["extra_tools"] == ["custom_extra"]
    assert "report_md" not in d and "convergence" not in d
    with pytest.raises(ValueError):
        D.analysis_report(adir, "../..")
    with pytest.raises(FileNotFoundError):
        D.analysis_report(adir, "no_such_set")
    with pytest.raises(ValueError):
        D.analysis_report(adir, "bad name")


def test_analysis_api_routes(analysis):
    root, runs, adir = analysis
    app = App(root, runs)
    idx = app.get("/api/analysis", {})
    assert {s["id"] for s in idx} == {".", "day_2026-11-12", "other_day"}
    det = app.get("/api/analysis/day_2026-11-12", {})
    assert det["seed_variance"]["groups"]["g1"]["n_seeds"] == 2
    # the analysis folder is configurable through the App constructor
    other = App(root, runs, analysis_dir=adir / "day_2026-11-12").get("/api/analysis", {})
    assert [(s["id"], s["tools"]) for s in other] == [
        (".", ["convergence", "seed_variance", "sensitivity", "links", "walls"])]
