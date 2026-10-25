"""WP2 (brief pins the driver for native families) and WP4 config wiring — senior pass 2026-10-24.

Covers:
- osse_baseline refuses a 1-inch brief (pinned r0 17.78 mm conflicts; silent rescale is worse)
- rosse_baseline with an absent throat_angle_policy reproduces today (a0_deg keeps its range)
- throat_angle_policy: pin forces a0_deg (OSSE-family) to the driver exit angle
- native FREEFORM configs pin profileH/V.throatAngleDeg under pin, and the seed materializes
- brief objective: {version: 2} -> Config.objective_version == 2 (v1 default; unknown keys refused)
- brief grid: {verify_points_per_octave: N} extends ONLY the verify grid with log points in
  [5 kHz, band_hi] (a new grid group; the screen grid is untouched)
- search.infeasible_penalty (WP3 wiring) defaults to 'flat' and validates its value
- campaign.is_compatible SKIPs osse_baseline under a 1-inch brief with the reason printed
- Target.freq_weights under v1 warns once (WP4)
"""
import logging

import yaml
import pytest

from conftest import EXAMPLES

from hornlab_search.config import (ConfigError, load_brief, load_config, mode_freqs)
from hornlab_search.search.campaign import is_compatible
from hornlab_search.search.evaluate import warn_freq_weights_v1
from hornlab_search.targets.spec import Target

# ------------------------------------------------------------------ brief fixtures

BASE_1IN = {
    "name": "test_1in",
    "description": "1-inch brief for driver-pinning tests",
    "driver": {"exit_radius_mm": 12.7, "exit_angle_deg": 5.0},
    "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 400.0, "max_depth_mm": 300.0},
    "symmetry": "hv",
    "target": {"coverage_h_deg": 90.0, "coverage_v_deg": 90.0, "band_lo_hz": 700.0,
               "band_hi_hz": 5500.0, "di_target_db": None, "di_slope_target": 0.0},
    "weights": {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5, "load": 0.0},
}


def _write_brief(tmp_path, overrides: dict | None = None, name="brief_1in.yaml"):
    brief = {**BASE_1IN, **(overrides or {})}
    if overrides and "driver" in overrides:
        brief["driver"] = {**BASE_1IN["driver"], **overrides["driver"]}
    p = tmp_path / name
    p.write_text(yaml.safe_dump(brief), encoding="utf-8")
    return p


@pytest.fixture
def brief_1in(tmp_path):
    return _write_brief(tmp_path)


# ------------------------------------------------------------------ WP2 r0 / a0 pins

def test_osse_baseline_refused_under_1in_brief(tmp_path, brief_1in):
    """osse_baseline pins r0_mm at 17.78 (1.4-inch): a 12.7 mm brief must raise, not rescale."""
    with pytest.raises(ConfigError, match="pinned"):
        load_config(EXAMPLES / "osse_baseline.yaml", brief=brief_1in)


def test_osse_baseline_loads_under_matching_14in_brief(tmp_path):
    brief = _write_brief(tmp_path, {"driver": {"exit_radius_mm": 17.78, "exit_angle_deg": 15.5},
                                    "name": "brief_14in"})
    cfg = load_config(EXAMPLES / "osse_baseline.yaml", brief=brief)
    assert cfg.bounds_raw["r0_mm"] == {"lo": 17.78, "hi": 17.78, "search": False}
    assert cfg.seed_params["r0_mm"] == 17.78


def test_rosse_without_policy_key_reproduces_today(tmp_path, brief_1in):
    """Absent throat_angle_policy -> OLD behaviour: a0_deg keeps its searching range.
    (r0 was already pinned to 12.7 in the config, so that pin is a consistent no-op.)"""
    cfg = load_config(EXAMPLES / "rosse_baseline.yaml", brief=brief_1in)
    assert cfg.bounds_raw["r0_mm"] == {"lo": 12.7, "hi": 12.7, "search": False}
    assert cfg.bounds_raw["a0_deg"] == {"lo": 2.0, "hi": 30.0}
    assert cfg.seed_params["a0_deg"] == 5.0
    cfg_plain = load_config(EXAMPLES / "rosse_baseline.yaml")
    assert dict(cfg_plain.seed_params) == dict(cfg.seed_params)
    assert {k: dict(v) for k, v in cfg_plain.bounds_raw.items()} == \
           {k: dict(v) for k, v in cfg.bounds_raw.items()}


def test_rosse_a0_pinned_under_policy_pin(tmp_path):
    brief = _write_brief(tmp_path, {"driver": {"throat_angle_policy": "pin"}})
    cfg = load_config(EXAMPLES / "rosse_baseline.yaml", brief=brief)
    assert cfg.bounds_raw["a0_deg"] == {"lo": 5.0, "hi": 5.0, "search": False}
    assert cfg.seed_params["a0_deg"] == 5.0
    assert cfg.bounds_raw["r0_mm"] == {"lo": 12.7, "hi": 12.7, "search": False}


def test_rosse_searching_a0_conflicts_with_existing_pin_raises(tmp_path):
    """A config that already pins a0_deg at a different angle must raise, not rescale."""
    src = (EXAMPLES / "rosse_baseline.yaml").read_text(encoding="utf-8")
    src = src.replace("a0_deg:       {lo: 2.0,   hi: 30.0}",
                      "a0_deg:       {lo: 10.0, hi: 10.0, search: false}")
    p = tmp_path / "rosse_pinned_a0.yaml"
    p.write_text(src, encoding="utf-8")
    brief = _write_brief(tmp_path, {"driver": {"throat_angle_policy": "pin"}},
                         name="brief_pin.yaml")
    with pytest.raises(ConfigError, match="a0_deg"):
        load_config(p, brief=brief)


def test_brief_policy_value_validated(tmp_path):
    p = _write_brief(tmp_path, {"driver": {"throat_angle_policy": "auto"}})
    with pytest.raises(ConfigError, match="throat_angle_policy"):
        load_brief(p)


def test_old_embedded_brief_run_config_grandfathered(tmp_path):
    """Oracle M1 must-fix 1: a pre-WP2 run dir's config.yaml (embedded brief whose driver conflicts
    with the config's pinned throat) must STILL load for resume/verify/report — no pins are applied
    on the embedded path, and reload is byte-identical (0-sha-delta)."""
    from hornlab_search.search.rundir import config_sha
    raw = yaml.safe_load((EXAMPLES / "osse_baseline.yaml").read_text(encoding="utf-8"))
    raw["brief"] = {k: v for k, v in BASE_1IN.items()}       # embedded 12.7 mm brief, as runs hold it
    raw["target"] = dict(BASE_1IN["target"])
    raw["weights"] = dict(BASE_1IN["weights"])
    p = tmp_path / "run_config.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    cfg = load_config(p)                                     # must NOT raise (grandfathered)
    assert cfg.bounds_raw["r0_mm"] == {"lo": 17.78, "hi": 17.78, "search": False}
    assert cfg.seed_params["r0_mm"] == 17.78
    assert cfg.bounds_raw["a0_deg"] == {"lo": 2.0, "hi": 30.0}   # old behaviour preserved
    assert cfg.brief["name"] == "test_1in"
    again = load_config(p)
    assert config_sha(again.raw) == config_sha(cfg.raw) == config_sha(raw)  # no mutation at all


def test_fresh_brief_file_config_still_pins(tmp_path):
    """The grandfather only covers the embedded run-dir path: a config applied with a FRESH
    brief_file (or --brief) keeps WP2 enforcement."""
    brief = _write_brief(tmp_path)
    src = (EXAMPLES / "osse_baseline.yaml").read_text(encoding="utf-8")
    src = src.replace("family: OSSE", f"family: OSSE\nbrief_file: {brief.as_posix()}")
    p = tmp_path / "osse_brieffile.yaml"
    p.write_text(src, encoding="utf-8")
    with pytest.raises(ConfigError, match="pinned"):
        load_config(p)


# ------------------------------------------------------------------ WP2 native FREEFORM pin

def test_freeform_native_throat_angle_pin(tmp_path):
    brief = _write_brief(tmp_path, {"driver": {"throat_angle_policy": "pin"}})
    cfg = load_config(EXAMPLES / "freeform_sculpt.yaml", brief=brief)
    for plane in ("profileH", "profileV"):
        key = f"{plane}.throatAngleDeg"
        assert cfg.bounds_raw[key] == {"lo": 5.0, "hi": 5.0, "search": False}
        assert cfg.seed_params[plane]["throatAngleDeg"] == 5.0


def test_freeform_native_throat_angle_free_absent_key(tmp_path, brief_1in):
    """Without the policy key the FREEFORM seed keeps its own 10 deg throat angle."""
    cfg = load_config(EXAMPLES / "freeform_sculpt.yaml", brief=brief_1in)
    assert cfg.seed_params["profileH"]["throatAngleDeg"] == 10.0
    assert "profileH.throatAngleDeg" not in cfg.bounds_raw
    cfg_plain = load_config(EXAMPLES / "freeform_sculpt.yaml")
    assert {k: dict(v) for k, v in cfg_plain.bounds_raw.items()} == \
           {k: dict(v) for k, v in cfg.bounds_raw.items()}


def test_freeform_seed_space_carries_pinned_angle(tmp_path):
    """The pin must reach the native FREEFORM design space, not only the YAML dicts."""
    from hornlab_search.design.space import DesignSpace
    brief = _write_brief(tmp_path, {"driver": {"throat_angle_policy": "pin"}})
    cfg = load_config(EXAMPLES / "freeform_sculpt.yaml", brief=brief)
    space = DesignSpace.from_config(cfg)
    d = space.seed
    assert d.params["profileH"]["throatAngleDeg"] == 5.0
    assert d.params["profileV"]["throatAngleDeg"] == 5.0
    assert d.params["profileH"]["points"][0][1] == 12.7   # throat anchor = driver exit
    assert "profileH.throatAngleDeg" not in space.keys()  # pinned: not searched


# ------------------------------------------------------------------ WP1 objective version

def test_objective_version_from_brief(tmp_path):
    brief = _write_brief(tmp_path, {"objective": {"version": 2}})
    cfg = load_config(EXAMPLES / "rosse_baseline.yaml", brief=brief)
    assert cfg.objective_version == 2
    assert cfg.raw["objective"] == {"version": 2}


def test_objective_version_default_1(tmp_path, brief_1in):
    cfg = load_config(EXAMPLES / "rosse_baseline.yaml", brief=brief_1in)
    assert cfg.objective_version == 1


def test_objective_block_from_config_itself(tmp_path, brief_1in):
    """A config (not brief) may set objective: {version: 2}; config_sha covers it via raw."""
    src = (EXAMPLES / "rosse_baseline.yaml").read_text(encoding="utf-8")
    src = src.replace("family: R-OSSE", "family: R-OSSE\n\nobjective: {version: 2}")
    p = tmp_path / "rosse_v2.yaml"
    p.write_text(src, encoding="utf-8")
    cfg = load_config(p, brief=brief_1in)
    assert cfg.objective_version == 2


def test_objective_block_invalid(tmp_path):
    for bad in ({"version": 4}, {"version": "2"}, {"vresion": 2}):   # (S1a 2026-10-25: v3 is now a legal version)
        p = _write_brief(tmp_path, {"objective": bad}, name=f"brief_bad_{sorted(bad)[0]}.yaml")
        with pytest.raises(ConfigError):
            load_brief(p)


# ------------------------------------------------------------------ WP4 HF verify grid

def test_grid_verify_points_per_octave(tmp_path):
    brief = _write_brief(tmp_path, {"grid": {"verify_points_per_octave": 8}})
    cfg = load_config(EXAMPLES / "rosse_baseline.yaml", brief=brief)
    cfg_plain = load_config(EXAMPLES / "rosse_baseline.yaml")
    base = mode_freqs("verify", cfg_plain)
    ext = mode_freqs("verify", cfg)
    base_set = set(base)
    assert base_set <= set(ext)                       # the frozen grid survives unchanged
    extra = sorted(f for f in ext if f not in base_set)
    assert all(5000.0 <= f <= 5500.0 + 1e-9 for f in extra)     # [5 kHz, band_hi] only
    assert 5000.0 in set(ext)
    assert len(ext) > len(base) == 25
    # screen/final mode grids are untouched by the brief
    assert mode_freqs("screen", cfg) == mode_freqs("screen", cfg_plain)


def test_grid_below_5kHz_band_adds_nothing(tmp_path):
    brief = _write_brief(tmp_path, {"grid": {"verify_points_per_octave": 8},
                                    "target": dict(BASE_1IN["target"], band_hi_hz=4000.0)},
                         name="brief_4k.yaml")
    cfg = load_config(EXAMPLES / "rosse_baseline.yaml", brief=brief)
    freqs = mode_freqs("verify", cfg)
    assert all(f <= 4000.0 + 1e-9 for f in freqs)         # nothing above the 4 kHz band
    assert 5000.0 not in set(freqs)


def test_grid_block_invalid(tmp_path):
    p = _write_brief(tmp_path, {"grid": {"verify_points_per_octave": 0}}, name="brief_g0.yaml")
    with pytest.raises(ConfigError):
        load_brief(p)
    p = _write_brief(tmp_path, {"grid": {"screen_points_per_octave": 8}}, name="brief_gu.yaml")
    with pytest.raises(ConfigError):
        load_brief(p)


# ------------------------------------------------------------------ WP3 search setting wiring

def test_infeasible_penalty_default_and_value(tmp_path, brief_1in):
    cfg = load_config(EXAMPLES / "rosse_baseline.yaml", brief=brief_1in)
    assert cfg.search.infeasible_penalty == "flat"
    src = (EXAMPLES / "rosse_baseline.yaml").read_text(encoding="utf-8")
    src = src.replace("tolfun: 1.0e-3}", "tolfun: 1.0e-3, infeasible_penalty: graded}")
    p = tmp_path / "rosse_graded.yaml"
    p.write_text(src, encoding="utf-8")
    cfg = load_config(p, brief=brief_1in)
    assert cfg.search.infeasible_penalty == "graded"
    bad = src.replace("infeasible_penalty: graded", "infeasible_penalty: squishy")
    (tmp_path / "rosse_bad.yaml").write_text(bad, encoding="utf-8")
    with pytest.raises(ConfigError, match="infeasible_penalty"):
        load_config(tmp_path / "rosse_bad.yaml", brief=brief_1in)


# ------------------------------------------------------------------ WP2 campaign fairness

def test_campaign_skips_osse_baseline_under_1in_brief(tmp_path, brief_1in):
    from hornlab_search.search.campaign import load_catalog
    catalog = load_catalog()
    entry = next(e for e in catalog if e["name"] == "osse_baseline")
    brief_d = load_brief(brief_1in)
    ok, why = is_compatible(entry, brief_d)
    assert not ok
    assert "17.78" in why and "12.7" in why
    # under its own 1.4-inch brief it stays compatible
    brief14 = _write_brief(tmp_path, {"driver": {"exit_radius_mm": 17.78, "exit_angle_deg": 15.5},
                                      "name": "brief_14in"}, name="brief_14in.yaml")
    ok, why = is_compatible(entry, load_brief(brief14))
    assert ok and why == ""


def test_campaign_other_entries_unaffected(brief_1in):
    from hornlab_search.search.campaign import load_catalog
    catalog = load_catalog()
    brief_d = load_brief(brief_1in)
    entry = next(e for e in catalog if e["name"] == "freeform_hv")
    ok, why = is_compatible(entry, brief_d)
    assert ok and why == ""


# ------------------------------------------------------------------ WP4 v1 warning

def test_freq_weights_warn_once_under_v1(tmp_path, caplog):
    target = Target(coverage_h_deg=90.0, coverage_v_deg=90.0, band_lo_hz=700.0,
                    band_hi_hz=5500.0, di_target_db=None,
                    freq_weights={"band_hz": [[500.0, 1000.0, 0.5]]})
    cfg = load_config(EXAMPLES / "rosse_baseline.yaml", brief=_write_brief(tmp_path))
    import hornlab_search.search.evaluate as ev
    ev._FREQ_WEIGHTS_V1_WARNED = False
    with caplog.at_level(logging.WARNING, logger="hornlab_search.search.evaluate"):
        ev.warn_freq_weights_v1(cfg, target)
        ev.warn_freq_weights_v1(cfg, target)          # second call: silent
    assert caplog.text.count("freq_weights") == 1
    # v2 -> no warning
    cfg_v2 = load_config(EXAMPLES / "rosse_baseline.yaml",
                         brief=_write_brief(tmp_path, {"objective": {"version": 2}},
                                            name="brief_v2.yaml"))
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="hornlab_search.search.evaluate"):
        ev._FREQ_WEIGHTS_V1_WARNED = False
        ev.warn_freq_weights_v1(cfg_v2, target)
    assert caplog.text == ""