"""WP 2.1 wiring: the config-resolved ``finalist`` tier is reachable from the CLI parsers whose
``--mode`` reaches ``mesh_spec``/``solve_spec``, while ``screen``/``verify``/``final`` stay as they
were. The tier itself lives in ``config.py``; these tests only pin the entry points.

Deliberately NOT wired here: ``surrogate --mode``. It feeds ``surrogate.round.run_round`` (which owns
a frozen ``screen|verify|final`` triple outside this task's files) and ``mode_freqs`` for the
propose/train grid check; accepting ``finalist`` in that parser would advertise a value that
``round`` rejects at runtime.
"""
from __future__ import annotations

import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search import cli
from hornlab_search.config import (
    FREQ_GRIDS,
    load_config,
    mesh_spec,
    mode_freqs,
    solve_spec,
)
from hornlab_search.mesh import sizing

BASE = EXAMPLES / "typologies" / "meh_2026-10-30" / "meh_t2a_search.yaml"

TIER_PARSERS = (
    ("run", ["run", "--config", "x.yaml"]),
    ("search", ["search", "--config", "x.yaml"]),
    ("export-step", ["export-step", "--run", "some/run"]),
)


def _cfg(tmp_path):
    raw = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    raw["brief_file"] = str((BASE.parent / raw["brief_file"]).resolve())
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_config(p)


# ------------------------------------------------------------------ parse level


@pytest.mark.parametrize("name,argv", TIER_PARSERS, ids=[n for n, _ in TIER_PARSERS])
def test_finalist_is_accepted(name, argv):
    args = cli.build_parser().parse_args([*argv, "--mode", "finalist"])
    assert args.mode == "finalist"


@pytest.mark.parametrize("name,argv", TIER_PARSERS, ids=[n for n, _ in TIER_PARSERS])
def test_old_tiers_still_parse(name, argv):
    for mode in ("screen", "verify", "final"):
        assert cli.build_parser().parse_args([*argv, "--mode", mode]).mode == mode


@pytest.mark.parametrize("name,argv", TIER_PARSERS, ids=[n for n, _ in TIER_PARSERS])
def test_default_is_still_screen(name, argv):
    assert cli.build_parser().parse_args(argv).mode == "screen"


@pytest.mark.parametrize("name,argv", TIER_PARSERS, ids=[n for n, _ in TIER_PARSERS])
def test_an_invalid_tier_still_fails(name, argv):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args([*argv, "--mode", "finalists"])
    assert exc.value.code == 2


# ------------------------------------------------------------------ spec level


def test_finalist_specs_are_the_config_resolved_tier(tmp_path):
    cfg = _cfg(tmp_path)
    mf = mesh_spec("finalist", cfg)
    # The triangle ceiling is resolved from the config's own finalist DOF cap.
    assert mf.max_triangles == sizing.max_triangles_for(
        cfg.mesh.dof_cap("finalist"), cfg.mesh.quadrants, cfg.mesh.dof_per_triangle,
        cfg.mesh.max_triangle_slack)
    assert mf.max_triangles > mesh_spec("verify", cfg).max_triangles   # 2x the screen DOF cap
    assert solve_spec("finalist", cfg).mode == "finalist"
    assert solve_spec("finalist", cfg) != solve_spec("verify", cfg)


def test_finalist_spec_follows_the_configs_own_cap(tmp_path):
    cfg = _cfg(tmp_path)
    raw = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    raw["brief_file"] = str((BASE.parent / raw["brief_file"]).resolve())
    raw["mesh"]["dof_cap_finalist"] = 31_000
    p = tmp_path / "c31.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    bumped = load_config(p)
    assert bumped.mesh.dof_cap("finalist") == 31_000
    assert mesh_spec("finalist", bumped).max_triangles > mesh_spec("finalist", cfg).max_triangles
    assert mesh_spec("verify", bumped) == mesh_spec("verify", cfg)


def test_screen_verify_final_spec_values_are_unchanged(tmp_path):
    # One assertion only: tests/test_config_fidelity_tiers.py already pins the rest.
    # The example config sets solve.freq_grid {120..12000 Hz, 6 ppo}: 41 points for every tier,
    # and all three DOF caps are 12000 => 108236 triangles.
    cfg = _cfg(tmp_path)
    assert [(mesh_spec(m, cfg).max_triangles, solve_spec(m, cfg).mode,
             len(solve_spec(m, cfg).freqs_hz), mesh_spec(m, cfg).f_max_hz)
            for m in ("screen", "verify", "final")] == [
        (108236, "screen", 41, 12000.0),
        (108236, "verify", 41, 12000.0),
        (108236, "final", 41, 12000.0),
    ]


def test_freq_grids_are_still_the_frozen_ones():
    assert FREQ_GRIDS["screen"] == (500.0, 10_000.0, 12)
    assert FREQ_GRIDS["verify"] == (300.0, 16_000.0, 25)
    assert FREQ_GRIDS["final"] == (250.0, 20_000.0, 36)


def test_finalist_grid_differs_from_verify_when_no_override(tmp_path):
    # Without a solve.freq_grid override the finalist grid is its own 36-point band. (The pinned
    # example config overrides every tier to the same grid, so strip it here.)
    raw = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    raw["brief_file"] = str((BASE.parent / raw["brief_file"]).resolve())
    raw.setdefault("solve", {}).pop("freq_grid", None)
    p = tmp_path / "no_override.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    cfg = load_config(p)
    assert len(mode_freqs("finalist", cfg)) >= 29
    assert mode_freqs("finalist", cfg) != mode_freqs("verify", cfg)
