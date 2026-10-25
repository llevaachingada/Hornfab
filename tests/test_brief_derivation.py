"""S1a tests (2026-10-25, owner-approved full-repair pass): ``target.f0_hz`` + the K-law
feasibility record + the brief-derived seed/bounds (CLAMP-ONLY) + objective v3's
below-f0 mask / freq-weighted coverage.

Offline, CPU-only. The opt-in contract: briefs WITHOUT ``target.f0_hz`` are touched
nowhere (no feasibility key, no derivation, byte-identical raw / config_sha); the
embedded-brief resume path never derives (old runs reproduce bit-for-bit).
"""
from __future__ import annotations

import dataclasses
import tempfile
from pathlib import Path

import numpy as np
import pytest
import yaml

from hornlab_search.config import load_brief, load_config
from hornlab_search.constants import KEELE_K
from hornlab_search.objective import ALL_KEYS, DEFAULT_WEIGHTS, WEIGHTED_KEYS
from hornlab_search.objective.scalar_v2 import objective_v2, objective_v3
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet

W = dict(DEFAULT_WEIGHTS)
_T_DICT = {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0, "band_lo_hz": 300.0,
           "band_hi_hz": 12000.0, "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0}


def _target(f0=None) -> Target:
    return Target.from_dict({**_T_DICT, **({"f0_hz": f0} if f0 is not None else {})})


def _metrics(target: Target, below_f0_error: float = 0.0) -> MetricSet:
    """Synthetic metrics: the design holds the target exactly at every in-band freq >= f0;
    below f0 the beamwidths miss by ``below_f0_error`` degrees (the unattainable band).
    DI follows the Gaussian-beam reference (the v2 harness's own pattern, so a design at
    target scores ~0 on every term)."""
    from hornlab_search.metrics.di import target_di_gaussian_db

    f0 = target.f0_effective_hz()
    f = np.geomspace(target.band_lo_hz, target.band_hi_hz, 14)
    miss = np.where(f < f0, below_f0_error, 0.0)
    return MetricSet(freqs_hz=f,
                     bw_h_deg=np.full(f.size, target.coverage_h_deg) + miss,
                     bw_v_deg=np.full(f.size, target.coverage_v_deg) + miss,
                     di_db=np.full(f.size, target_di_gaussian_db(
                         target.coverage_h_deg, target.coverage_v_deg)),
                     di_source="balloon",
                     ripple_h_db=np.zeros(f.size), ripple_v_db=np.zeros(f.size),
                     on_axis_db=np.zeros(f.size), z_throat_real=np.full(f.size, 1.0),
                     scalars={})


# ------------------------------------------------------------- the f0_hz key

def test_target_f0_key_validation_and_effective_hz():
    t = _target(800.0)
    assert t.f0_hz == 800.0 and t.f0_effective_hz() == 800.0
    t2 = _target()
    assert t2.f0_hz is None and t2.f0_effective_hz() == 300.0   # absent = band_lo (v2 rule)
    with pytest.raises(ValueError, match="f0_hz"):
        _target(0.0)
    with pytest.raises(ValueError, match="f0_hz"):
        _target(13000.0)          # above band_hi = meaningless for this band
    with pytest.raises(ValueError, match="unknown key"):
        Target.from_dict({**_T_DICT, "f0": 100.0})   # a typo is an error, never silent


# ---------------------------------------------------------- objective v3

def test_v3_masks_the_below_f0_band_from_cov():
    """A design that holds the target above f0 but wildly misses below it: v2 pays the
    unattainable band's error; v3 masks it (f0 = 1000 masks 5 of the 14 freqs)."""
    t = _target(1000.0)
    bad_low = _metrics(t, below_f0_error=60.0)
    j2, t2 = objective_v2(bad_low, None, True, _target(), W)
    j3, t3 = objective_v3(bad_low, None, True, t, W)
    assert t2["cov"] > 1.0 and t3["cov"] < 1e-12
    assert j3 == pytest.approx(t3["total"], rel=1e-12)
    # 14 log-spaced freqs over 300-12000 Hz: five sit below f0 = 1000 (300/401/536/717/960)
    assert t3["n_in_band"] == 9
    # the perfect design still scores ~0 under v3
    j3p, t3p = objective_v3(_metrics(t), None, True, t, W)
    assert abs(t3p["cov"]) < 1e-12 and abs(j3p) < 1e-6


def test_v3_applies_freq_weights_to_cov():
    """WP4's vector used to touch only rip (v2); v3 weights the COVERAGE term too."""
    t = _target(300.0)                          # f0 = band_lo: no masking, weights only
    m = _metrics(t)
    m.bw_h_deg = m.bw_h_deg + np.linspace(0.0, 40.0, m.freqs_hz.size)   # a cov gradient
    t_uniform = dataclasses.replace(t, freq_weights={"band_hz": [[1.0, 1e9, 1.0]]})
    t_up = dataclasses.replace(t, freq_weights={"band_hz": [[4900.0, 20000.0, 8.0]]})
    j_uniform, _ = objective_v3(m, None, True, t_uniform, W)
    j_up, _ = objective_v3(m, None, True, t_up, W)
    assert j_up > j_uniform > 0.0


def test_v3_key_set_and_never_raise_match_v2():
    t = _target(800.0)
    m = _metrics(t)
    j, terms = objective_v3(m, None, True, t, W)
    assert set(terms) == set(ALL_KEYS) and j == pytest.approx(terms["total"], rel=1e-12)
    assert all(np.isfinite(v) for v in terms.values())
    assert j == pytest.approx(sum(W[k] * terms[k] for k in WEIGHTED_KEYS), rel=1e-12)
    for metrics, resp, weights in ((None, None, W), (m, object(), {"cov": "oops"}),
                                   (m, None, {"bogus": 1.0})):
        j2, t2 = objective_v3(metrics, resp, True, t, weights)
        assert np.isfinite(j2) and set(t2) == set(ALL_KEYS)


def test_v2_equals_v3_when_the_brief_has_no_f0():
    """The non-retroactive contract: without f0_hz, v3's numbers equal v2's exactly."""
    t = _target()
    m = _metrics(t, below_f0_error=12.0)
    j2, t2 = objective_v2(m, None, True, t, W)
    j3, t3 = objective_v3(m, None, True, t, W)
    assert j2 == pytest.approx(j3, rel=1e-12)
    assert t2["n_in_band"] == t3["n_in_band"] == 14
    assert t2["cov"] == pytest.approx(t3["cov"], rel=1e-12)


# ------------------------------------------------ the feasibility + derivation

def _tmpdir() -> Path:
    return Path(tempfile.mkdtemp(prefix="s1a_"))


def _typology_yaml(dir_path: Path) -> Path:
    """A minimal generator-typology config (hypex) with rm bounds to derive into."""
    return _yaml(dir_path, "typ.yaml", {
        "name": "typ", "family": "FREEFORM",
        "brief_file": "brief.yaml",
        "generator": {"name": "typology",
                      "profile_h": {"type": "hypex"}, "profile_v": {"type": "hypex"},
                      "n_anchors": 16, "max_wall_deg": 80.0, "mouth": "ellipse"},
        "seed_params": {"L_mm": 190.0, "h_rm_mm": 120.0, "v_rm_mm": 120.0,
                        "h_T": 0.7, "v_T": 0.7},
        "bounds": {"L_mm": {"lo": 140.0, "hi": 220.0},
                   "h_rm_mm": {"lo": 60.0, "hi": 150.0},
                   "v_rm_mm": {"lo": 60.0, "hi": 150.0},
                   "h_T": {"lo": 0.3, "hi": 1.0}, "v_T": {"lo": 0.3, "hi": 1.0}},
        "target": dict(_T_DICT),
        "weights": dict(W),
        "mesh": {"epw": 8.0, "quadrants": "1", "dof_cap_screen": 5000,
                 "dof_cap_verify": 7000, "dof_cap_final": 8900, "dof_per_triangle": 0.51},
        "solve": {"backend": "beat_cuda", "distance_m": 2.0, "angle_count": 73,
                  "balloon": True, "balloon_points_screen": 512,
                  "balloon_points_verify": 1024, "gmres_tol": 1.0e-05, "timeout_s": 900},
        "search": {"algorithm": "cma", "sigma0": 0.25, "seed": 1234, "budget": 100,
                   "popsize": None, "tolfun": 0.001},
    })


def _yaml(dir_path: Path, name: str, payload) -> Path:
    p = Path(dir_path) / name
    p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return p


def _brief(dir_path: Path, f0, cov=(90.0, 60.0), env=(400.0, 300.0, 220.0)) -> Path:
    target = dict(_T_DICT)
    target["coverage_h_deg"], target["coverage_v_deg"] = cov
    brief = {
        "name": "derivable", "description": "S1a test brief",
        "driver": {"exit_radius_mm": 12.7, "exit_angle_deg": 5.0},
        "envelope": {"max_mouth_w_mm": env[0], "max_mouth_h_mm": env[1],
                     "max_depth_mm": env[2]},
        "symmetry": "hv",
        "target": target,
        "weights": dict(W),
    }
    if f0 is not None:
        target["f0_hz"] = f0
        brief["objective"] = {"version": 3}          # top level, NOT inside target
    return _yaml(dir_path, "brief.yaml", brief)


def test_feasibility_record_is_k_law_exact():
    d1, d2 = _tmpdir(), _tmpdir()
    cfg = load_config(_typology_yaml(d1), brief=_brief(d2, f0=800.0,
                                                       cov=(90.0, 15.0),
                                                       env=(500.0, 400.0, 300.0)))
    feas = cfg.raw["feasibility"]
    # K-law EXACT: d = 25400e3/(f0*cov) mm
    assert feas["required_mouth_w_mm"] == pytest.approx(KEELE_K * 1000.0 / (800.0 * 90.0))
    assert feas["required_mouth_h_mm"] == pytest.approx(KEELE_K * 1000.0 / (800.0 * 15.0))
    # 15 deg vertical at 800 Hz needs a 2117 mm mouth: the envelope can't hold it; the
    # held coverage at 400 mm = 25400e3/(800*400)
    assert feas["feasible_w"] is True and feas["feasible_v"] is False
    assert feas["held_coverage_v_deg"] == pytest.approx(KEELE_K * 1000.0 / (800.0 * 400.0))
    # the screen grid's below-f0 count = the honest ledger of what v2 was chasing
    assert feas["screen_freqs_total"] == 12 and feas["screen_freqs_below_f0"] >= 1
    # the derivation CLAMPED h_rm to the bound (the derived d/2 = 176.5 > the bound hi 150)
    h_rm = cfg.raw["seed_params"]["h_rm_mm"]
    assert h_rm == pytest.approx(150.0)
    derive = feas["derivation"]
    assert any(n["knob"] == "h_rm_mm" and n["clamped_to_bound"] for n in derive)
    assert any(n["knob"] == "v_rm_mm" for n in derive)
    print(f"\nfeasibility: required {feas['required_mouth_w_mm']:.0f} x "
          f"{feas['required_mouth_h_mm']:.0f} mm vs envelope {feas['envelope_mouth_w_mm']:.0f} x "
          f"{feas['envelope_mouth_h_mm']:.0f}; derived/clamped notes: "
          f"{[(n['knob'], n['applied']) for n in derive]}")


def test_absent_f0_is_byte_for_byte_untouched():
    d1 = _tmpdir()
    typ = _typology_yaml(d1)                     # its own brief_file: brief.yaml (same dir)
    _brief(d1, f0=None)                          # the standalone load resolves it
    cfg = load_config(typ, brief=_brief(d1, f0=None))
    cfg_standalone = load_config(typ)
    # (the config_sha differs INTENTIONALLY: an applied brief embeds the brief dict -
    # test_design_generated pins that. The byte-identity contract is the DERIVED SURFACE
    # + the merged target/weights: no feasibility key, no derivation, same seed/bounds.)
    assert "feasibility" not in cfg.raw
    assert cfg.raw["seed_params"] == cfg_standalone.raw["seed_params"]
    assert cfg.raw["bounds"] == cfg_standalone.raw["bounds"]
    assert cfg.raw["target"] == cfg_standalone.raw["target"]
    assert cfg.raw["weights"] == cfg_standalone.raw["weights"]


def test_embedded_brief_never_derives():
    """Resume/verify/report paths (a run directory's embedded brief) skip re-derivation:
    the already-generated feasibility record RIDES ALONG unchanged (the embedded config's
    raw is reproduced verbatim - that is the byte-for-bit resume contract)."""
    d1, d2 = _tmpdir(), _tmpdir()
    cfg = load_config(_typology_yaml(d1), brief=_brief(d2, f0=800.0))
    assert "feasibility" in cfg.raw
    p = d1 / "embedded.yaml"
    p.write_text(yaml.safe_dump(cfg.raw, sort_keys=False), encoding="utf-8")
    again = load_config(p)
    assert again.raw.get("feasibility") == cfg.raw["feasibility"]
    assert again.raw["seed_params"] == cfg.raw["seed_params"]


def test_eval_score_dispatches_v3(tmp_path):
    """_score honors objective_version 3 (the ctx carries the version)."""
    from types import SimpleNamespace

    from hornlab_search.search import evaluate as E

    t = _target(1000.0)
    m = _metrics(t, below_f0_error=60.0)
    j, terms = E._score(m, None, SimpleNamespace(objective_version=3, target=t, weights=W))
    assert terms["cov"] < 1e-12 and set(terms) == set(ALL_KEYS)
    assert j == pytest.approx(terms["total"], rel=1e-12)