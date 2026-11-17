"""Shared-descriptor translation (2026-11-17)."""
from pathlib import Path

import pytest

from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.geometry import sensitivity as S
from hornlab_search.geometry import translate as T

GRID = Path(__file__).resolve().parents[1] / "examples" / "typologies" / "grid_ellipse_mod.yaml"


def test_recovers_a_known_point_of_the_same_space():
    cfg = load_config(GRID)
    sp = DesignSpace.from_config(cfg)
    x_true = [0.3, 0.7]
    rec, _ = S.record_at(sp, cfg, x_true)
    tgt = S.shared_descriptors(rec)
    r = T.match_descriptors(sp, cfg, tgt, keys=["mouth_width_mm", "depth_mm"], iters=10)
    assert r["ok"] and r["residual_rms_scaled"] < 0.5
    assert r["x"] == pytest.approx(x_true, abs=0.02)
    assert r["history"][-1] <= r["history"][0]


def test_unreachable_target_reports_a_residual_instead_of_failing():
    cfg = load_config(GRID)
    sp = DesignSpace.from_config(cfg)
    r = T.match_descriptors(sp, cfg, {"mouth_width_mm": 5000.0}, iters=4, require_inside=False)
    assert r["ok"] and r["residual_by_key"]["mouth_width_mm"] < -1000


def test_target_without_known_keys_is_refused():
    cfg = load_config(GRID)
    with pytest.raises(ValueError):
        T.match_descriptors(DesignSpace.from_config(cfg), cfg, {"nope": 1.0})
