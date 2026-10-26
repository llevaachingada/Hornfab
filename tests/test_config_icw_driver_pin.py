"""Campaign 2026-10-26 Phase 0 / Step 2C: WP2 driver pin for ICW's nested throat.

ICW keeps its throat at ``seed_params.icw_seed.r0_mm`` (with the flat dotted bound key
``icw_seed.r0_mm``). The original pin checked only the ROOT ``r0_mm`` and therefore
silently missed every ICW config. These tests pin the extended path and the unchanged
``_force_pin`` semantics (refuse a mismatching pin; force an unpinned parameter).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hornlab_search.config import ConfigError, load_config

REPO = Path(__file__).resolve().parents[1]
ICW = REPO / "examples" / "icw_rollback.yaml"

_BRIEF = {
    "name": "icw_pin_test",
    "description": "18 mm driver brief for the ICW nested pin",
    "driver": {"exit_radius_mm": 18.0, "exit_angle_deg": 5.0},
    "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 400.0, "max_depth_mm": 300.0},
    "symmetry": "hv",
    "target": {"coverage_h_deg": 90.0, "coverage_v_deg": 90.0, "band_lo_hz": 700.0,
               "band_hi_hz": 5500.0, "di_target_db": None, "di_slope_target": 0.0},
    "weights": {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5, "load": 0.0},
}


def _brief(tmp_path: Path, exit_radius_mm: float = 18.0) -> Path:
    raw = {**_BRIEF, "driver": {**_BRIEF["driver"], "exit_radius_mm": exit_radius_mm}}
    p = tmp_path / f"brief_{exit_radius_mm}.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return p


def _unpinned_config(tmp_path: Path) -> Path:
    """The shipped ICW config with the nested throat bound made searchable."""
    raw = yaml.safe_load(ICW.read_text(encoding="utf-8"))
    raw["bounds"]["icw_seed.r0_mm"] = {"lo": 10.0, "hi": 16.0}
    p = tmp_path / "icw_unpinned.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return p


def test_unpinned_nested_icw_throat_is_forced_to_the_brief_driver(tmp_path):
    cfg = load_config(_unpinned_config(tmp_path), brief=_brief(tmp_path, 18.0))
    assert cfg.seed_params["icw_seed"]["r0_mm"] == 18.0
    assert cfg.bounds_raw["icw_seed.r0_mm"] == {"lo": 18.0, "hi": 18.0, "search": False}
    # The pin reaches the effective design, not just the YAML dicts.
    from hornlab_search.design.space import DesignSpace
    seed = DesignSpace.from_config(cfg).seed
    assert seed.params["icw_seed"]["r0_mm"] == 18.0


def test_shipped_icw_pin_at_12_7_refuses_an_18_mm_brief(tmp_path):
    with pytest.raises(ConfigError, match=r"icw_seed\.r0_mm"):
        load_config(ICW, brief=_brief(tmp_path, 18.0))


def test_shipped_icw_matching_brief_is_unchanged(tmp_path):
    before = yaml.safe_load(ICW.read_text(encoding="utf-8"))
    cfg = load_config(ICW, brief=_brief(tmp_path, 12.7))
    assert cfg.seed_params["icw_seed"]["r0_mm"] == 12.7
    assert cfg.bounds_raw["icw_seed.r0_mm"] == before["bounds"]["icw_seed.r0_mm"]


def test_embedded_icw_brief_still_skips_the_pin(tmp_path):
    """Old run configs stay loadable (the embedded-brief grandfather is untouched)."""
    raw = yaml.safe_load(ICW.read_text(encoding="utf-8"))
    raw["brief"] = {k: v for k, v in _BRIEF.items()}
    raw["target"] = dict(_BRIEF["target"])
    raw["weights"] = dict(_BRIEF["weights"])
    p = tmp_path / "icw_embedded.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    cfg = load_config(p)                               # 18 mm embedded driver, 12.7 pin: grandfathered
    assert cfg.seed_params["icw_seed"]["r0_mm"] == 12.7
    assert cfg.bounds_raw["icw_seed.r0_mm"] == {"lo": 12.7, "hi": 12.7, "search": False}
