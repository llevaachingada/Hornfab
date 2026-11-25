"""Tests for the mode-scoped SCREEN grid (``solve.screen_grid``, 2026-11-23 HF pass).

The contract:
  * absent -> every mode's grid, mesh spec and hash is byte-identical to before;
  * present -> ONLY ``screen`` changes (verify/final/finalist untouched);
  * a named profile requires a brief whose ``target.band_hi_hz`` reaches its top edge;
  * it is mutually exclusive with ``solve.freq_grid`` and ``grid.screen_extra_hz``;
  * the solved-frequency list (hence the solve hash and the mesh f_max) changes.
"""
from __future__ import annotations

import copy

import pytest
import yaml

from hornlab_search.config import (
    FREQ_GRIDS,
    SCREEN_GRID_PROFILES,
    ConfigError,
    load_config,
    mesh_spec,
    mode_freqs,
    solve_spec,
)
from conftest import REPO


BASE = REPO / "examples" / "osse_baseline.yaml"


def _raw(band_hi: float = 12000.0) -> dict:
    raw = yaml.safe_load(BASE.read_text(encoding="utf-8"))
    raw = copy.deepcopy(raw)
    raw["target"]["band_hi_hz"] = band_hi
    return raw


def _load(tmp_path, raw: dict, name: str = "cfg.yaml"):
    p = tmp_path / name
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_config(p)


def test_absent_screen_grid_keeps_every_mode_identical(tmp_path):
    raw = _raw(5500.0)
    cfg = _load(tmp_path, raw, "absent.yaml")
    for mode in ("screen", "verify", "final", "finalist"):
        lo, hi, n = FREQ_GRIDS[mode]
        hi = min(hi, 5500.0)
        assert mode_freqs(mode, cfg) == (
            tuple(round(float(f), 2) for f in __import__("numpy").geomspace(lo, hi, n)))


def test_profile_changes_only_screen(tmp_path):
    raw_plain = _raw()
    cfg_plain = _load(tmp_path, raw_plain, "plain.yaml")
    raw_prof = _raw()
    raw_prof["solve"]["screen_grid"] = {"profile": "hf12k_screen_v1"}
    cfg_prof = _load(tmp_path, raw_prof, "prof.yaml")

    freqs = mode_freqs("screen", cfg_prof)
    assert len(freqs) == 19
    assert freqs[0] == 500.0 and freqs[-1] == 12000.0
    assert freqs == tuple(SCREEN_GRID_PROFILES["hf12k_screen_v1"]["freqs_hz"])
    assert mesh_spec("screen", cfg_prof).f_max_hz == 12000.0

    for mode in ("verify", "final", "finalist"):
        assert mode_freqs(mode, cfg_prof) == mode_freqs(mode, cfg_plain), mode
        assert mesh_spec(mode, cfg_prof).hash() == mesh_spec(mode, cfg_plain).hash(), mode

    # identity: the solved frequencies enter the solve hash and the 10k/12k meshes differ
    assert solve_spec("screen", cfg_prof).hash() != solve_spec("screen", cfg_plain).hash()
    assert mesh_spec("screen", cfg_prof).hash() != mesh_spec("screen", cfg_plain).hash()
    assert mesh_spec("screen", cfg_prof).f_max_hz != mesh_spec("screen", cfg_plain).f_max_hz


def test_profile_refuses_short_band(tmp_path):
    raw = _raw(10000.0)
    raw["solve"]["screen_grid"] = {"profile": "hf12k_screen_v1"}
    with pytest.raises(ConfigError, match="band_hi_hz"):
        _load(tmp_path, raw)


def test_profile_must_be_known(tmp_path):
    raw = _raw()
    raw["solve"]["screen_grid"] = {"profile": "hf16k_nope"}
    with pytest.raises(ConfigError, match="not a known screen policy"):
        _load(tmp_path, raw)


def test_lo_hi_ppo_form_and_mesh_share(tmp_path):
    raw19 = _raw()
    raw19["solve"]["screen_grid"] = {"lo_hz": 500, "hi_hz": 12000, "points_per_octave": 4}
    cfg19 = _load(tmp_path, raw19, "a.yaml")
    raw29 = _raw()
    raw29["solve"]["screen_grid"] = {"lo_hz": 500, "hi_hz": 12000, "points_per_octave": 6}
    cfg29 = _load(tmp_path, raw29, "b.yaml")

    assert len(mode_freqs("screen", cfg19)) == 19
    assert len(mode_freqs("screen", cfg29)) == 29
    # same top edge -> same mesh, different solve -> the sampling experiment is not confounded by
    # a different discretisation
    assert mesh_spec("screen", cfg19).hash() == mesh_spec("screen", cfg29).hash()
    assert solve_spec("screen", cfg19).hash() != solve_spec("screen", cfg29).hash()


def test_explicit_freqs_validation(tmp_path):
    ok = _raw()
    ok["solve"]["screen_grid"] = {"freqs_hz": [500, 1000, 2000, 12000]}
    cfg = _load(tmp_path, ok, "ok.yaml")
    assert mode_freqs("screen", cfg) == (500.0, 1000.0, 2000.0, 12000.0)

    bad_cases = (
        ({"freqs_hz": [500]}, ">= 2"),
        ({"freqs_hz": [500, 500, 800]}, "duplicate"),
        ({"freqs_hz": [500, 800, 400]}, "ascending"),
        ({"freqs_hz": [500, 0]}, "positive"),
        ({"freqs_hz": [500, 13000]}, "band_hi_hz"),
    )
    for i, (block, match) in enumerate(bad_cases):
        raw = _raw()
        raw["solve"]["screen_grid"] = block
        with pytest.raises(ConfigError, match=match):
            _load(tmp_path, raw, f"bad{i}.yaml")


def test_mutually_exclusive_policies(tmp_path):
    raw = _raw()
    raw["solve"]["freq_grid"] = {"lo_hz": 500, "hi_hz": 12000, "points_per_octave": 4}
    raw["solve"]["screen_grid"] = {"profile": "hf12k_screen_v1"}
    with pytest.raises(ConfigError, match="cannot both be set"):
        _load(tmp_path, raw, "both.yaml")

    raw = _raw()
    raw["grid"] = {"screen_extra_hz": [250.0, 315.0]}
    raw["solve"]["screen_grid"] = {"profile": "hf12k_screen_v1"}
    with pytest.raises(ConfigError, match="screen_extra_hz"):
        _load(tmp_path, raw, "extra.yaml")


def test_screen_grid_survives_config_round_trip(tmp_path):
    raw = _raw()
    raw["solve"]["screen_grid"] = {"profile": "hf12k_screen_v1"}
    cfg = _load(tmp_path, raw, "rt.yaml")
    # the run directory embeds the resolved config; reloading it must give the same freqs
    pathlib = __import__("pathlib")
    emb = tmp_path / "embedded.yaml"
    emb.write_text(yaml.safe_dump(cfg.raw, sort_keys=False), encoding="utf-8")
    cfg2 = load_config(emb)
    assert mode_freqs("screen", cfg2) == mode_freqs("screen", cfg)
    assert solve_spec("screen", cfg2).hash() == solve_spec("screen", cfg).hash()
