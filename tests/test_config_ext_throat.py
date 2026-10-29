"""C0 (2026-10-28): the brief's r0/a0 pin must not flatten an extended-throat design.

A native OSSE/R-OSSE config that searches a POSITIVE ``throat_ext_length_mm`` gets its driven
coupling plane at ``r0 - L*tan(theta)``; the per-design derivation that puts that plane at the
brief's driver exit lives in ``search/evaluate.py`` (``_derive_throat_coupling``). These config
tests pin the other half: ``_apply_brief_driver_pins`` leaves ``r0_mm`` (and ``a0_deg``) alone
when the extension is positive, and pins them exactly as today when it is zero or absent.
"""
from __future__ import annotations

import yaml
import pytest

from hornlab_search.config import ConfigError, _apply_brief_driver_pins, load_config

DRIVER = {"exit_radius_mm": 18.0, "exit_angle_deg": 3.0}
BRIEF = {"driver": dict(DRIVER)}


def _raw(seed_ext=None, bounds_ext=None, r0=(18.0, 28.0)):
    seed = {"r0_mm": r0[0], "a0_deg": 3.0, "a_deg": 37.5, "L_mm": 260.0}
    bounds = {"r0_mm": {"lo": r0[0], "hi": r0[1]}, "a0_deg": {"lo": 2.0, "hi": 5.0}}
    if seed_ext is not None:
        seed["throat_ext_length_mm"] = seed_ext
        seed["throat_ext_angle_deg"] = 3.0
    if bounds_ext is not None:
        bounds["throat_ext_length_mm"] = bounds_ext
        bounds["throat_ext_angle_deg"] = {"lo": 2.0, "hi": 5.0}
    return {"family": "OSSE", "seed_params": seed, "bounds": bounds}


def test_positive_seeded_extension_skips_the_r0_pin():
    raw = _raw(seed_ext=160.0, bounds_ext={"lo": 120.0, "hi": 200.0})
    before = dict(raw["bounds"]["r0_mm"])
    _apply_brief_driver_pins(raw, BRIEF, "t")
    assert raw["bounds"]["r0_mm"] == before == {"lo": 18.0, "hi": 28.0}   # still searched
    assert raw["seed_params"]["r0_mm"] == 18.0
    assert raw["bounds"]["a0_deg"] == {"lo": 2.0, "hi": 5.0}              # no a0 pin either


def test_positive_hi_bound_alone_skips_the_r0_pin():
    """The seed may be a zero-length start: a positive ``hi`` bound can search it up."""
    raw = _raw(seed_ext=0.0, bounds_ext={"lo": 0.0, "hi": 40.0})
    _apply_brief_driver_pins(raw, BRIEF, "t")
    assert raw["bounds"]["r0_mm"] == {"lo": 18.0, "hi": 28.0}
    assert raw["seed_params"]["r0_mm"] == 18.0


def test_zero_length_extension_still_pins_r0_to_the_exit():
    raw = _raw(seed_ext=0.0, bounds_ext={"lo": 0.0, "hi": 0.0})
    _apply_brief_driver_pins(raw, BRIEF, "t")
    assert raw["bounds"]["r0_mm"] == {"lo": 18.0, "hi": 18.0, "search": False}
    assert raw["seed_params"]["r0_mm"] == 18.0


def test_absent_extension_still_pins_r0_to_the_exit():
    raw = _raw()
    _apply_brief_driver_pins(raw, BRIEF, "t")
    assert raw["bounds"]["r0_mm"] == {"lo": 18.0, "hi": 18.0, "search": False}
    assert raw["seed_params"]["r0_mm"] == 18.0


def test_a_pinned_main_throat_no_longer_conflicts_with_an_extended_design():
    """A 1.4-inch MAIN throat (the extension tapers back to the 18 mm brief exit) is legal:
    today's pin would raise 'pinned at 17.78 but the brief pins 18.0'."""
    raw = _raw(seed_ext=160.0, bounds_ext={"lo": 120.0, "hi": 200.0}, r0=(17.78, 17.78))
    raw["bounds"]["r0_mm"] = {"lo": 17.78, "hi": 17.78, "search": False}
    _apply_brief_driver_pins(raw, BRIEF, "t")
    assert raw["bounds"]["r0_mm"] == {"lo": 17.78, "hi": 17.78, "search": False}
    # the same raw without the extension keeps the refusal (silent rescale is worse)
    plain = {"family": "OSSE",
             "seed_params": {"r0_mm": 17.78, "a0_deg": 3.0},
             "bounds": {"r0_mm": {"lo": 17.78, "hi": 17.78, "search": False}}}
    with pytest.raises(ConfigError, match="pinned"):
        _apply_brief_driver_pins(plain, BRIEF, "t")


def test_rosse_with_a_positive_extension_skips_the_pin_too(tmp_path):
    raw = _raw(seed_ext=160.0, bounds_ext={"lo": 120.0, "hi": 200.0})
    raw["family"] = "R-OSSE"
    _apply_brief_driver_pins(raw, BRIEF, "t")
    assert raw["bounds"]["r0_mm"] == {"lo": 18.0, "hi": 28.0}


def test_throat_angle_policy_pin_does_not_pin_a0_when_extended():
    raw = _raw(seed_ext=160.0, bounds_ext={"lo": 120.0, "hi": 200.0})
    _apply_brief_driver_pins(raw, {"driver": {**DRIVER, "throat_angle_policy": "pin"}}, "t")
    assert raw["bounds"]["a0_deg"] == {"lo": 2.0, "hi": 5.0}
    assert raw["seed_params"]["a0_deg"] == 3.0


def test_load_config_accepts_an_extended_throat_under_a_mismatched_main_throat(tmp_path):
    """End-to-end through load_config: the 1.4-inch MAIN throat + extension loads under an
    18 mm brief (no r0 pin, so no 'pinned at' refusal)."""
    cfg_doc = {
        "name": "ext_load", "family": "OSSE",
        "seed_params": {"r0_mm": 17.78, "a0_deg": 3.0, "a_deg": 37.5, "L_mm": 260.0,
                        "n": 4.0, "s": 0.7, "q": 0.995, "k": 1.0, "exponent": 2.0,
                        "aspect_ratio": 1.0, "throat_ext_length_mm": 160.0,
                        "throat_ext_angle_deg": 3.0},
        "bounds": {"r0_mm": {"lo": 17.78, "hi": 17.78, "search": False},
                   "a0_deg": {"lo": 2.0, "hi": 5.0},
                   "a_deg": {"lo": 5.0, "hi": 55.0}, "L_mm": {"lo": 140.0, "hi": 420.0},
                   "n": {"lo": 2.0, "hi": 8.0}, "s": {"lo": 0.0, "hi": 1.0},
                   "q": {"lo": 0.90, "hi": 1.0}, "k": {"lo": 0.3, "hi": 2.5},
                   "exponent": {"lo": 1.0, "hi": 8.0}, "aspect_ratio": {"lo": 1.0, "hi": 2.0},
                   "throat_ext_length_mm": {"lo": 120.0, "hi": 200.0},
                   "throat_ext_angle_deg": {"lo": 2.0, "hi": 5.0}},
        "target": {"coverage_h_deg": 75.0, "coverage_v_deg": 45.0, "band_lo_hz": 700.0,
                   "band_hi_hz": 8000.0, "di_target_db": None, "di_slope_target": 0.0},
        "weights": {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5, "load": 0.0},
        "mesh": {"epw": 6.0, "quadrants": "1", "dof_cap_screen": 9000,
                 "dof_cap_verify": 9000, "dof_cap_final": 9000, "dof_per_triangle": 0.51},
        "solve": {"backend": "beat_cuda", "distance_m": 2.0, "angle_count": 73, "balloon": True,
                  "balloon_points_screen": 512, "balloon_points_verify": 1024,
                  "gmres_tol": 1e-5, "timeout_s": 900},
        "search": {"algorithm": "cma", "sigma0": 0.25, "seed": 1234, "budget": 200,
                   "popsize": None, "tolfun": 1e-3},
    }
    brief_doc = {
        "name": "ext_brief", "driver": dict(DRIVER),
        "envelope": {"max_mouth_w_mm": 700.0, "max_mouth_h_mm": 700.0, "max_depth_mm": 600.0},
        "symmetry": "hv", "target": cfg_doc["target"], "weights": cfg_doc["weights"],
    }
    cp = tmp_path / "ext.yaml"
    bp = tmp_path / "brief.yaml"
    cp.write_text(yaml.safe_dump(cfg_doc), encoding="utf-8")
    bp.write_text(yaml.safe_dump(brief_doc), encoding="utf-8")
    cfg = load_config(cp, brief=bp)
    assert cfg.seed_params["r0_mm"] == 17.78
    assert cfg.bounds_raw["r0_mm"] == {"lo": 17.78, "hi": 17.78, "search": False}
