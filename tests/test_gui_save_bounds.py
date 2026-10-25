"""Bounds writer: POST /api/save-bounds (owner ruling 2026-10-25).

Every test runs on a Temp copy of the examples tree -- the shipped YAMLs are never touched.
The round-trip test proves the write is a TARGETED line patch: only the two numeric lines of
the edited bounds block change, every other line (comments included) stays byte-identical, and
``load_config`` reads the edited bounds back.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from hornlab_search.config import load_config
from hornlab_search.gui import data as D

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def examples_root(tmp_path: Path) -> Path:
    """A Temp examples/ tree: two typology configs, the root-level control, and briefs."""
    examples = tmp_path / "examples"
    (examples / "typologies").mkdir(parents=True)
    for name in ("salmon_elliptical.yaml", "salmon_x_shape.yaml"):
        shutil.copy2(ROOT / "examples" / "typologies" / name, examples / "typologies" / name)
    shutil.copy2(ROOT / "examples" / "osse_baseline.yaml", examples / "osse_baseline.yaml")
    shutil.copytree(ROOT / "examples" / "briefs", examples / "briefs")
    (examples / "catalog.yaml").write_text("entries: []\n", encoding="utf-8")
    return tmp_path


def _config_path(root: Path, name: str) -> Path:
    return root / "examples" / "typologies" / name


# ------------------------------------------------------------------ round trip

def test_round_trip_patches_only_the_two_bounds_lines(examples_root: Path):
    path = _config_path(examples_root, "salmon_elliptical.yaml")
    before = path.read_text(encoding="utf-8")
    out = D.save_bounds(examples_root, {
        "config": "salmon_elliptical",
        "bounds": {"g_fc_h_hz": {"lo": 650.0, "hi": 1150.0}},
    })
    assert out["ok"] is True
    assert out["file"] == "examples/typologies/salmon_elliptical.yaml"
    assert out["applied"] == [{
        "key": "g_fc_h_hz",
        "from": {"lo": 600.0, "hi": 1200.0},
        "to": {"lo": 650.0, "hi": 1150.0},
    }]
    assert any("config_sha changes" in note for note in out["notes"])
    assert any("RUNNING search" in note for note in out["notes"])

    after = path.read_text(encoding="utf-8")
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    assert len(before_lines) == len(after_lines)
    changed = [(old, new) for old, new in zip(before_lines, after_lines) if old != new]
    assert len(changed) == 2
    assert [old.strip().split(":")[0] for old, _ in changed] == ["lo", "hi"]
    assert [new.strip() for _, new in changed] == ["lo: 650.0", "hi: 1150.0"]

    # Comments survive word for word (the comment on the edited key included).
    assert before.count("#") == after.count("#")
    assert "# band starts at 700 Hz (9b.4: fc 600-1200 for 1-inch)" in after

    # The real reader sees the edit; every other bounds entry is unchanged.
    reloaded = load_config(path)
    assert reloaded.bounds_raw["g_fc_h_hz"]["lo"] == 650.0
    assert reloaded.bounds_raw["g_fc_h_hz"]["hi"] == 1150.0
    old_bounds = yaml.safe_load(before)["bounds"]
    new_bounds = yaml.safe_load(after)["bounds"]
    for key in old_bounds:
        if key != "g_fc_h_hz":
            assert new_bounds[key] == old_bounds[key]


def test_multiple_keys_write_together(examples_root: Path):
    path = _config_path(examples_root, "salmon_elliptical.yaml")
    out = D.save_bounds(examples_root, {
        "config": "salmon_elliptical",
        "bounds": {
            "g_fc_h_hz": {"lo": 700.0, "hi": 1100.0},
            "g_T": {"lo": 0.4, "hi": 0.9},
        },
    })
    assert out["ok"] is True
    assert {entry["key"] for entry in out["applied"]} == {"g_fc_h_hz", "g_T"}
    reloaded = load_config(path)
    assert reloaded.bounds_raw["g_T"]["lo"] == 0.4
    assert reloaded.bounds_raw["g_T"]["hi"] == 0.9


# ------------------------------------------------------------------ rejections (all-or-nothing)

def test_unknown_key_rejects_and_writes_nothing(examples_root: Path):
    path = _config_path(examples_root, "salmon_elliptical.yaml")
    before = path.read_text(encoding="utf-8")
    out = D.save_bounds(examples_root, {
        "config": "salmon_elliptical",
        "bounds": {"not_a_knob": {"lo": 1.0, "hi": 2.0}},
    })
    assert out["ok"] is False
    assert out["applied"] == []
    assert out["rejected"] == [{"key": "not_a_knob", "reason": "unknown_key"}]
    assert path.read_text(encoding="utf-8") == before


def test_lo_above_hi_rejects(examples_root: Path):
    out = D.save_bounds(examples_root, {
        "config": "salmon_elliptical",
        "bounds": {"g_T": {"lo": 1.2, "hi": 0.4}},
    })
    assert out["ok"] is False
    assert out["rejected"][0]["reason"] == "lo_above_hi"


def test_non_finite_rejects(examples_root: Path):
    out = D.save_bounds(examples_root, {
        "config": "salmon_elliptical",
        "bounds": {"g_T": {"lo": "not-a-number", "hi": 1.0}},
    })
    assert out["ok"] is False
    assert out["rejected"][0]["reason"] == "not_a_finite_number"


def test_hard_limit_from_the_parameter_catalog_rejects(examples_root: Path):
    # g_x_amp's hard schema window is -0.4 .. 0.4 (the parameter catalog's KeySpec).
    out = D.save_bounds(examples_root, {
        "config": "salmon_x_shape",
        "bounds": {"g_x_amp": {"lo": -0.2, "hi": 0.5}},
    })
    assert out["ok"] is False
    assert out["applied"] == []
    assert out["rejected"] == [{"key": "g_x_amp", "reason": "exceeds_hard_limit -0.4..0.4"}]
    path = _config_path(examples_root, "salmon_x_shape.yaml")
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["bounds"]["g_x_amp"]["hi"] == 0.35


def test_one_rejected_key_writes_nothing_even_when_others_are_valid(examples_root: Path):
    path = _config_path(examples_root, "salmon_elliptical.yaml")
    before = path.read_text(encoding="utf-8")
    out = D.save_bounds(examples_root, {
        "config": "salmon_elliptical",
        "bounds": {
            "g_T": {"lo": 0.4, "hi": 0.9},
            "not_a_knob": {"lo": 1.0, "hi": 2.0},
        },
    })
    assert out["ok"] is False
    assert out["applied"] == []
    assert [entry["key"] for entry in out["rejected"]] == ["not_a_knob"]
    assert path.read_text(encoding="utf-8") == before


def test_root_level_examples_are_refused(examples_root: Path):
    path = examples_root / "examples" / "osse_baseline.yaml"
    before = path.read_text(encoding="utf-8")
    out = D.save_bounds(examples_root, {
        "config": "osse_baseline",
        "bounds": {"a_deg": {"lo": 30.0, "hi": 40.0}},
    })
    assert out["ok"] is False
    assert out["applied"] == []
    assert "config_not_writable" in out["rejected"][0]["reason"]
    assert path.read_text(encoding="utf-8") == before


def test_malformed_body_and_unknown_config(examples_root: Path):
    with pytest.raises(ValueError):
        D.save_bounds(examples_root, {"config": "salmon_elliptical"})
    with pytest.raises(ValueError):
        D.save_bounds(examples_root, {"config": "salmon_elliptical", "bounds": {}})
    with pytest.raises(FileNotFoundError):
        D.save_bounds(examples_root, {"config": "no_such_config",
                                      "bounds": {"x": {"lo": 0.0, "hi": 1.0}}})
