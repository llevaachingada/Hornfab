"""WP 2.1 fidelity ladder: screen / verify / finalist resolve in config; screen and verify are
unchanged; the finalist tier is >= 29 frequencies on a mesh at 2x the screen DOF cap."""
from __future__ import annotations

import dataclasses

import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.config import (FINALIST_DOF_FACTOR, FREQ_GRIDS, MODES, load_config, mesh_spec,
                                   mode_freqs, solve_spec)
from hornlab_search.studies.package import BUDGET_PROFILES, budget_caps

BASE = EXAMPLES / "typologies" / "meh_2026-10-30" / "meh_t2a_search.yaml"


def _cfg(tmp_path, mutate=None):
    raw = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    raw["brief_file"] = str((BASE.parent / raw["brief_file"]).resolve())
    if mutate:
        mutate(raw)
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_config(p)


def test_tier_names_resolve():
    assert {"screen", "verify", "finalist"} <= set(MODES)


def test_frozen_grids_unchanged():
    assert FREQ_GRIDS["screen"] == (500.0, 10_000.0, 12)
    assert FREQ_GRIDS["verify"] == (300.0, 16_000.0, 25)
    assert FREQ_GRIDS["final"] == (250.0, 20_000.0, 36)


def test_screen_and_verify_specs_do_not_depend_on_the_finalist_tier(tmp_path):
    cfg = _cfg(tmp_path)
    for mode in ("screen", "verify", "final"):
        before = (mesh_spec(mode, cfg), solve_spec(mode, cfg))
        bumped = dataclasses.replace(cfg, mesh=dataclasses.replace(cfg.mesh, dof_cap_finalist=99_000))
        assert (mesh_spec(mode, bumped), solve_spec(mode, bumped)) == before
    assert cfg.mesh.dof_cap("screen") == cfg.mesh.dof_cap_screen
    assert cfg.mesh.dof_cap("verify") == cfg.mesh.dof_cap_verify
    assert cfg.mesh.dof_cap("final") == cfg.mesh.dof_cap_final


def test_finalist_dof_cap_is_twice_screen_by_default(tmp_path):
    cfg = _cfg(tmp_path)
    assert cfg.mesh.dof_cap("finalist") == FINALIST_DOF_FACTOR * cfg.mesh.dof_cap_screen
    assert cfg.mesh.dof_cap("finalist") == 2 * cfg.mesh.dof_cap("screen")
    ms, mf = mesh_spec("screen", cfg), mesh_spec("finalist", cfg)
    assert mf.max_triangles > ms.max_triangles
    assert mf.max_triangles == pytest.approx(2 * ms.max_triangles, rel=1e-3)


def test_finalist_cap_can_be_set_in_yaml(tmp_path):
    cfg = _cfg(tmp_path, lambda r: r["mesh"].update(dof_cap_finalist=31_000))
    assert cfg.mesh.dof_cap("finalist") == 31_000
    assert cfg.mesh.dof_cap("screen") == cfg.mesh.dof_cap_screen


def test_finalist_has_at_least_29_frequencies_and_its_own_identity(tmp_path):
    cfg = _cfg(tmp_path)
    assert len(mode_freqs("finalist", cfg)) >= 29
    sf, sv, ss = (solve_spec(m, cfg) for m in ("finalist", "verify", "screen"))
    assert sf.mode == "finalist"
    assert sf != sv and sf != ss
    assert mesh_spec("finalist", cfg) != mesh_spec("verify", cfg)


def test_finalist_budget_profile_is_additive():
    assert budget_caps({"budget_profile": "fidelity-ladder-10"}) == BUDGET_PROFILES["fidelity-ladder-10"]
    assert BUDGET_PROFILES["comparison-100x2"] == {
        "screen_calls": 100, "verify_calls": 2, "total_calls": 102, "attempts": 500}
