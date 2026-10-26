"""Campaign 2026-10-26 Phase 0 / Step 2A: ``generator.seed_policy``.

``derive`` (the default when the key is ABSENT) is today's f0-driven seed derivation.
``explicit`` skips it so a campaign copy can carry hand-measured seeds. The opt-in
contract is byte-identical when absent: same seed_params, same bounds, same config_sha,
same derivation notes as the pre-change tree (both goldens below were captured from the
tree immediately before this key was introduced).
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from hornlab_search.config import ConfigError, load_config
from hornlab_search.search.rundir import config_sha

REPO = Path(__file__).resolve().parents[1]
BRIEF = REPO / "examples" / "briefs" / "organic_rollback_14in.yaml"

# Captured before the seed_policy edit (organic_rollback_14in applied fresh).
GOLDEN = {
    "salmon_elliptical": {
        "config_sha": "9b5cc34de453",
        "seed_params": {
            "g_T": 0.8,
            "g_fc_h_hz": 1199.0551181102362,
            "g_fc_v_hz": 799.3700787401575,
            "g_stop_deg": 150.0,
        },
        "derivation": [
            {"knob": "g_fc_h_hz", "note": "K-law inverse of the W*fc invariant",
             "derived_mm": 1199.0551181102362, "applied": 1199.0551181102362,
             "clamped_to_bound": False},
            {"knob": "g_fc_v_hz", "note": "K-law inverse of the H*fc invariant",
             "derived_mm": 799.3700787401575, "applied": 799.3700787401575,
             "clamped_to_bound": False},
        ],
    },
    "lecleach_rollback": {
        "config_sha": "f2e29be7c418",
        "seed_params": {"g_T": 0.8, "g_fc_hz": 979.0244042808987, "g_stop_deg": 170.0},
        "derivation": [
            {"knob": "g_fc_hz", "note": "K-law inverse at the geometric-mean mouth",
             "derived_mm": 979.0244042808987, "applied": 979.0244042808987,
             "clamped_to_bound": False},
        ],
    },
}


def _config_path(name: str) -> Path:
    return REPO / "examples" / "typologies" / f"{name}.yaml"


def _copy_with_policy(tmp_path: Path, name: str, policy: str) -> Path:
    """A byte-faithful copy of the shipped config with ``generator.seed_policy`` added."""
    raw = yaml.safe_load(_config_path(name).read_text(encoding="utf-8"))
    raw["generator"]["seed_policy"] = policy
    out = tmp_path / f"{name}_{policy}.yaml"
    out.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return out


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_absent_seed_policy_is_byte_identical_to_the_pre_change_tree(name):
    cfg = load_config(_config_path(name), brief=BRIEF)
    assert cfg.generator is not None
    golden = GOLDEN[name]
    # No key inserted, no surface moved.
    assert "seed_policy" not in cfg.generator
    assert cfg.raw["seed_params"] == golden["seed_params"]
    assert cfg.raw["feasibility"]["derivation"] == golden["derivation"]
    assert config_sha(cfg.raw) == golden["config_sha"]


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_explicit_seed_policy_keeps_the_yaml_seed_and_bounds(tmp_path, name):
    raw = yaml.safe_load(_config_path(name).read_text(encoding="utf-8"))
    cfg = load_config(_copy_with_policy(tmp_path, name, "explicit"), brief=BRIEF)
    # The hand-measured seeds and every bound are exactly the YAML values (nothing derived,
    # nothing clamped, no bound widened).
    assert cfg.raw["seed_params"] == raw["seed_params"]
    assert cfg.raw["bounds"] == raw["bounds"]
    # The K-law feasibility record is still present; only derivation is skipped.
    feas = cfg.raw["feasibility"]
    assert feas["f0_hz"] == 1800.0
    assert feas["required_mouth_w_mm"] > 0.0
    assert feas["derivation"] == [
        {"knob": "-", "note": "seed_policy explicit: derivation skipped"}]


@pytest.mark.parametrize("policy", ["derive ", "explicit-ish", "", None, 1])
def test_invalid_seed_policy_is_refused(tmp_path, policy):
    raw = yaml.safe_load(_config_path("salmon_elliptical").read_text(encoding="utf-8"))
    raw["generator"]["seed_policy"] = policy
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    with pytest.raises(ConfigError, match=r"generator\.seed_policy"):
        load_config(p, brief=BRIEF)


def test_seed_policy_never_reaches_the_materializer(tmp_path, monkeypatch):
    """The directive stays in raw (config_sha/provenance) but is never handed downstream."""
    from hornlab_search.design import generated

    cfg = load_config(_copy_with_policy(tmp_path, "conical", "explicit"), brief=BRIEF)
    assert cfg.raw["generator"]["seed_policy"] == "explicit"   # still covered by config_sha
    assert cfg.generator is not None and "seed_policy" not in cfg.generator

    seen = {}

    def fake_materialize(gen, knobs, brief):
        seen["gen"] = copy.deepcopy(gen)
        return {}

    monkeypatch.setattr(generated.registry, "materialize", fake_materialize)
    assert cfg.brief is not None
    generated.materialize(cfg.generator, {"L_mm": 180.0, "h_rm_mm": 120.0}, cfg.brief)
    assert "seed_policy" not in seen["gen"]
    assert seen["gen"]["name"] == "typology"
