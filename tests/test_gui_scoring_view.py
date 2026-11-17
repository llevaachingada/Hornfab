"""P0 scoring-truth presentation (2026-11-16), read-only GUI reader layer.

``run_detail``, ``design_curves``, ``campaign_detail`` and the compare payload expose the ACTUAL
scored masks/constants/floors each immutable run config implies (target f0, below-f0 mode, active
weights, 8k floor, fitted DI slope). Additive only: J and every existing key must stay untouched.
Offline; no GPU, no CLI jobs, no real solver.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from hornlab_search.gui import data as D

ROOT = Path(__file__).resolve().parents[1]

RID = "20261116T000000Z-screen-abcd12"          # v7, f0 700 Hz
RID_B = "20261116T000001Z-screen-abcd13"        # v7, f0 900 Hz (per-side compare proof)
RID_C = "20261116T000002Z-screen-abcd14"        # brief without an objective block

BRIEF = "room_landscape_80x50_700_hf1440_v7"
BRIEF_B = "room_landscape_80x50_900_hf1440_v7"
BRIEF_C = "room_landscape_80x50_700_hf1440_v7_noobj"

HASH = "abc123abc123"
HASH_B = "def456def456"
HASH_C = "cab789cab789"

F = [350.0, 500.0, 700.0, 1000.0, 2000.0, 4000.0, 8000.0]
F_B = [350.0, 500.0, 700.0, 900.0, 2000.0, 4000.0, 8000.0]

TARGET = {
    "coverage_h_deg": 80.0, "coverage_v_deg": 50.0,
    "band_lo_hz": 350.0, "band_hi_hz": 8000.0,
    "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.5,
    "f0_hz": 700.0, "f0_v_hz": 700.0, "loaded_hi_hz": 5600.0,
}
TARGET_B = {**TARGET, "f0_hz": 900.0, "f0_v_hz": 900.0}
# di weight 0 and dislope weight 1: the LEVEL is not scored, the SLOPE is (handoff P0).
WEIGHTS = {"cov": 1.0, "rip": 1.0, "di": 0.0, "dislope": 1.0, "flat": 0.5,
           "load": 1.0, "distd": 0.5, "diag": 1.0, "flat_cv": 1.0}
OBJECTIVE = {
    "version": 7, "flat_band": "scored", "cov_v_weight": 0.5,
    "tolerances": {"cov": 3.0, "rip": 1.0, "di": 0.4, "dislope": 9.0, "flat": 1.5,
                   "load": 0.3, "distd": 2.0, "diag": 2.0, "flat_cv": 1.5},
    "cov_narrow_ratio": 2.0, "cov_below_f0": "mask", "loaded_re_z": 0.5,
    "lfp_re_z": 0.2, "lfp_crossover_ratio": 1.6, "bw8k_floor": 0.75,
}


def _metrics(freqs: list[float], anchor_hz: float) -> dict:
    """Flat 80 x 50 pattern + DI rising at exactly +5 dB/decade from ``anchor_hz``."""
    n = len(freqs)
    di = [12.0 + 5.0 * np.log10(f / anchor_hz) for f in freqs]
    return {"freqs_hz": freqs, "bw_h_deg": [80.0] * n, "bw_v_deg": [50.0] * n,
            "di_db": di, "di_source": "balloon",
            "on_axis_db": [0.0] * n, "ripple_h_db": [0.0] * n, "ripple_v_db": [0.0] * n,
            "z_throat_real": [0.5] * n,
            "scalars": {"fc_hz": anchor_hz, "g_fc_hz": anchor_hz}}


def _write_run(runs: Path, rid: str, brief_body: dict, *, hash_: str,
               metrics: dict, version: int = 7) -> Path:
    """One run whose target/objective/weights are sourced ONLY from the embedded brief block."""
    run = runs / rid
    run.mkdir(parents=True)
    cfg = {"name": brief_body["name"], "family": "FREEFORM", "brief": brief_body}
    (run / "config.yaml").write_text(yaml.safe_dump(cfg))
    (run / "run.json").write_text(json.dumps({"backend": "beat_cuda", "mode": "screen",
                                              "objective_version": version}))
    row = {"n": 0, "design_hash": hash_, "ok": True, "objective": 1.25, "mode": "screen",
           "family": "FREEFORM", "error": None}
    (run / "search.ndjson").write_text(json.dumps(row) + "\n")
    d = run / "designs" / hash_
    d.mkdir(parents=True)
    (d / "metrics.json").write_text(json.dumps(metrics))
    (d / "design.json").write_text(json.dumps({"family": "FREEFORM",
                                               "params": {"fc_hz": 700.0, "a": 1}}))
    return run


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    runs = root / "runs"
    brief_a = {"name": BRIEF, "target": copy.deepcopy(TARGET),
               "weights": copy.deepcopy(WEIGHTS), "objective": copy.deepcopy(OBJECTIVE)}
    brief_b = {"name": BRIEF_B, "target": copy.deepcopy(TARGET_B),
               "weights": copy.deepcopy(WEIGHTS), "objective": copy.deepcopy(OBJECTIVE)}
    brief_c = {"name": BRIEF_C, "target": copy.deepcopy(TARGET)}     # no objective / weights
    _write_run(runs, RID, brief_a, hash_=HASH, metrics=_metrics(F, 700.0))
    _write_run(runs, RID_B, brief_b, hash_=HASH_B, metrics=_metrics(F_B, 900.0))
    _write_run(runs, RID_C, brief_c, hash_=HASH_C, metrics=_metrics(F, 700.0), version=1)
    briefs = root / "examples" / "briefs"
    briefs.mkdir(parents=True)
    for body in (brief_a, brief_b, brief_c):
        (briefs / f"{body['name']}.yaml").write_text(yaml.safe_dump(body))
    (root / "examples" / "cfg.yaml").write_text("name: x\n")
    return root


# ------------------------------------------------------------------ run_detail


def test_run_detail_scoring_view_exposes_the_scored_truth(repo):
    d = D.run_detail(repo / "runs", RID)
    sv = d["scoring_view"]
    assert sv["objective_version"] == 7
    # target f0 700 -> the real scored band starts at 700 Hz; below it the mask ignores coverage.
    assert sv["coverage"]["h_lo_hz"] == pytest.approx(700.0)
    assert sv["coverage"]["below_mode"] == "mask"
    # di weight 0 -> level NOT scored; dislope weight 1 -> slope scored.
    assert sv["di"]["level_scored"] is False
    assert sv["di"]["slope_scored"] is True
    # v7 bw8k_floor resolves because the best design carries the scored arrays.
    assert sv["bw8k_floor"] is not None
    # J identity untouched by the additive view.
    assert d["objective_version"] == 7 and d["J"][0] == 1.25
    json.dumps(d, allow_nan=False)


def test_run_detail_omits_scoring_view_without_an_objective_block(repo):
    d = D.run_detail(repo / "runs", RID_C)
    assert "scoring_view" not in d          # omitted, never null-filled/invented
    json.dumps(d, allow_nan=False)


# ------------------------------------------------------------------ design_curves


def test_design_curves_carry_score_window_and_scored_di_slope(repo):
    best = D.design_curves(repo / "runs" / RID, HASH)
    assert best is not None
    win = best["score_window"]
    assert win["h_lo_hz"] == pytest.approx(700.0)
    assert win["below_mode"] == "mask"
    slope = best["di_slope_scored"]
    assert slope["band_lo_hz"] == pytest.approx(700.0)
    assert isinstance(slope["slope"], float) and np.isfinite(slope["slope"])


def test_design_curves_omit_scoring_keys_without_an_objective_block(repo):
    best = D.design_curves(repo / "runs" / RID_C, HASH_C)
    assert best is not None
    assert "score_window" not in best and "di_slope_scored" not in best


# ------------------------------------------------------------------ campaigns


def test_campaign_carries_scoring_view_weights_and_objective(repo):
    c = D.campaign_detail(repo / "runs", f"auto_{BRIEF}__screen")
    sv = c["scoring_view"]
    assert sv["objective_version"] == 7
    assert sv["coverage"]["h_lo_hz"] == pytest.approx(700.0)
    assert sv["coverage"]["below_mode"] == "mask"
    assert c["weights"] == WEIGHTS
    assert c["objective"] == OBJECTIVE


def test_campaign_keys_are_omitted_without_an_objective_block(repo):
    c = D.campaign_detail(repo / "runs", f"auto_{BRIEF_C}__screen")
    assert "scoring_view" not in c and "objective" not in c and "weights" not in c
    assert c["target"] == TARGET


# ------------------------------------------------------------------ compare payload


def test_compare_scoring_views_are_built_per_side_never_overlaid(repo):
    views = D.compare_scoring_views(repo / "runs", RID, RID_B)
    a, b = views["scoring_view_a"], views["scoring_view_b"]
    assert a["objective_version"] == 7 and b["objective_version"] == 7
    assert a["coverage"]["h_lo_hz"] == pytest.approx(700.0)   # each side's own f0
    assert b["coverage"]["h_lo_hz"] == pytest.approx(900.0)
    assert a is not b


def test_compare_omits_a_side_with_no_objective_block(repo):
    views = D.compare_scoring_views(repo / "runs", RID, RID_C)
    assert "scoring_view_a" in views and "scoring_view_b" not in views
