"""D8 continuation rule (WP 7.2 advisory): propose only when the last-100 gain beats the floor.

P0b: the floor is resolved from the run's full identity (brief sha256 + score identity), not
from ``(objective_version, "slope5")``.
"""
from __future__ import annotations

import yaml

from test_tools_analysis_common import REPO, load_tool, make_row, write_run

ca = load_tool("continuation_advice")

V7_BRIEF = "examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml"


def _curve(bests):
    return [{"n": i + 1, "best": b} for i, b in enumerate(bests)]


def _brief_run(tmp_path, brief_rel, rows, name, mode="screen"):
    """A synthetic run whose brief resolves through a real brief file (exact identity)."""
    brief_path = (REPO / brief_rel).resolve()
    cfg = dict(yaml.safe_load(brief_path.read_text(encoding="utf-8")))
    cfg["brief_file"] = str(brief_path)
    cfg["name"] = f"test_{name}"
    cfg["family"] = "OSSE"
    cfg["solve"] = {"backend": "beat_cuda", "angle_count": 73, "balloon": True,
                    "balloon_points_screen": 512}
    cfg["mesh"] = {"quadrants": "1", "epw": 6.0, "rear_res_factor": 1.5}
    return write_run(rows, tmp_path, name, config=cfg, family="OSSE")


def test_gain_above_the_v7_floor_proposes_and_below_does_not():
    flat = [5.0] * 50 + [5.0 - 0.004 * i for i in range(100)]   # last-100 gain 0.396
    assert ca.advise(_curve(flat), 0.3105)["advice"] == "propose continuation"
    small = [5.0] * 50 + [5.0 - 0.002 * i for i in range(100)]  # gain 0.198: below the band
    r = ca.advise(_curve(small), 0.3105)
    assert r["advice"] == "do not propose" and abs(r["improvement"] - 0.198) < 1e-9


def test_short_runs_and_pure_unknown_floor_refuse_to_advise():
    assert ca.advise(_curve([5.0] * 100), 0.3105)["advice"] == "too short"
    assert ca.advise(_curve([5.0] * 300), None)["advice"] == "no floor"


def test_borderline_gain_recommends_common_grid_verification():
    floor = 0.3104791983512361
    gain = 1.10 * floor
    curve = [{"n": i + 1, "best": 5.0}
             for i in range(50)]
    curve += [{"n": 50 + i + 1, "best": 5.0 - gain * (i + 1) / 100}
              for i in range(100)]
    r = ca.advise(curve, floor)
    assert r["borderline"] is True
    assert r["advice"] == "verify on common grid"
    assert "common grid" in r["why"]
    # the three uncertainty components are distinct output keys even without a registry source
    assert set(r["uncertainty"]) >= {"deterministic_fidelity_bias", "measured_uncertainty",
                                     "stochastic_variability"}


def test_v7_run_resolves_its_exact_identity_floor(tmp_path):
    rows = [make_row(i, 5.0 - (0.005 * max(0, i - 49)), version=7) for i in range(160)]
    r = ca.analyse(_brief_run(tmp_path, V7_BRIEF, rows, "v7"))
    assert r["resolution"]["status"] == "matched"
    assert r["resolution"]["matched_entry"] == "v7_home_landscape_this_pass"
    assert r["floor"] == 0.3104791983512361
    assert r["identity"]["objective_version"] == 7
    assert r["identity"]["brief"]["name"] == "room_landscape_80x50_700_hf1440_v7"
    assert r["identity"]["score_identity_hash"]
    assert r["advice"] == "propose continuation"


def test_unknown_identity_gets_no_applicable_published_floor(tmp_path):
    rows4 = [make_row(i, 5.0 - 0.01 * i, version=4) for i in range(160)]
    r = ca.analyse(write_run(rows4, tmp_path, "v4"))
    assert r["resolution"]["status"] == "no_applicable_floor"
    assert r["floor"] is None
    assert r["advice"] == "no applicable published floor"
    assert r["resolution"]["missing_fields"]
