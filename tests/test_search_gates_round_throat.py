"""B.5 (day 2026-11-12): brief ``gates: {round_throat: true}`` opts any single-entry objective
version into the C4 round-throat refusal that v7 always applies. Default: off for every existing
brief (a stretched throat with no gates key evaluates exactly as before); v7 keeps the gate on
regardless (pinned by tests/test_search_v7_throat_refusal.py).
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from hornlab_search.config import ConfigError, load_brief, load_config
from test_search_support import SyntheticBackend
from test_search_v7_throat_refusal import BRIEF, EXIT_RADIUS_MM, _evaluate, _install_mesh

GATED = {**BRIEF, "gates": {"round_throat": True}}


def _run_gate_case(smoke_cfg, tmp_path, monkeypatch, brief, rx_mm, ry_mm):
    """One evaluate() on a stretched/round synthetic quarter mesh with the given brief."""
    be = SyntheticBackend()
    _install_mesh(monkeypatch, tmp_path, rx_mm, ry_mm, be)
    cfg = dataclasses.replace(smoke_cfg, brief=brief)
    return be, _evaluate(cfg, tmp_path, be)


def test_gated_non_v7_version_refuses_a_stretched_throat(smoke_cfg, tmp_path, monkeypatch):
    """The objective stays at its DEFAULT version (1): the gate must work for ANY single-entry
    objective, not only v7. A 26 x 36 mm ellipse cannot round-match the 36 mm exit."""
    be, ev = _run_gate_case(smoke_cfg, tmp_path, monkeypatch, GATED, 13.0, 18.0)
    assert ev.error.startswith("invalid_geometry") and "driver exit" in ev.error
    assert ev.objective == 1000.0 and ev.mesh is not None
    assert be.calls == 0, "the solver must never be asked to run for a refused candidate"


def test_absent_gates_key_keeps_todays_behaviour(smoke_cfg, tmp_path, monkeypatch):
    """Invariance: a brief WITHOUT the gates block must NOT apply the refusal."""
    be, ev = _run_gate_case(smoke_cfg, tmp_path, monkeypatch, BRIEF, 13.0, 18.0)
    assert ev.error == "" and be.calls == 1, "the stretched throat evaluates exactly as today"


def test_explicit_false_round_throat_keeps_the_gate_off(smoke_cfg, tmp_path, monkeypatch):
    be, ev = _run_gate_case(smoke_cfg, tmp_path, monkeypatch,
                            {**BRIEF, "gates": {"round_throat": False}}, 13.0, 18.0)
    assert ev.error == "" and be.calls == 1


def test_gated_run_round_throat_passes(smoke_cfg, tmp_path, monkeypatch):
    be, ev = _run_gate_case(smoke_cfg, tmp_path, monkeypatch, GATED, 18.0, 18.0)
    assert ev.error == "" and be.calls == 1


# --- brief-level config validation ---------------------------------------------------

BRIEF_YAML_WITH_GATES = f"""name: gated
driver:
  exit_radius_mm: {EXIT_RADIUS_MM}
  exit_angle_deg: 5.0
envelope:
  max_mouth_w_mm: 10000.0
  max_mouth_h_mm: 10000.0
  max_depth_mm: 10000.0
symmetry: axisymmetric
target:
  coverage_h_deg: 90.0
  coverage_v_deg: 90.0
  band_lo_hz: 250.0
  band_hi_hz: 5500.0
weights:
  cov: 1.0
  rip: 1.0
  di: 0.3
  dislope: 0.5
  flat: 0.5
  load: 0.0
gates:
  round_throat: true
"""

BRIEF_YAML_BASE = BRIEF_YAML_WITH_GATES.replace("gates:\n  round_throat: true\n", "").rstrip() + "\n"


def _write(tmp_path, text: str) -> Path:
    p = tmp_path / "brief.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_brief_accepts_gates_and_preserves_the_bool(tmp_path):
    b = load_brief(_write(tmp_path, BRIEF_YAML_WITH_GATES))
    assert b["gates"] == {"round_throat": True}


def test_load_brief_refuses_a_non_boolean_round_throat(tmp_path):
    import yaml
    raw = yaml.safe_load(BRIEF_YAML_WITH_GATES)
    raw["gates"]["round_throat"] = "yes"
    with pytest.raises(ConfigError, match="round_throat must be true or false"):
        load_brief(_write(tmp_path, yaml.safe_dump(raw, sort_keys=False)))


def test_load_brief_refuses_unknown_gate_keys(tmp_path):
    import yaml
    raw = yaml.safe_load(BRIEF_YAML_WITH_GATES)
    raw["gates"]["magic"] = 1
    with pytest.raises(ConfigError, match="unknown key"):
        load_brief(_write(tmp_path, yaml.safe_dump(raw, sort_keys=False)))


def test_load_brief_refuses_a_non_mapping_gates_block(tmp_path):
    import yaml
    raw = yaml.safe_load(BRIEF_YAML_BASE)
    raw["gates"] = 5
    with pytest.raises(ConfigError, match="mapping"):
        load_brief(_write(tmp_path, yaml.safe_dump(raw, sort_keys=False)))


def test_load_config_embedded_brief_gates_are_revalidated(tmp_path):
    """A run-directory config embedding a brief with an unvalidated gate is refused on resume."""
    import copy
    import yaml
    base = yaml.safe_load(BRIEF_YAML_BASE)
    base["target"] = {"coverage_h_deg": 90.0, "coverage_v_deg": 90.0,
                      "band_lo_hz": 250.0, "band_hi_hz": 5500.0}
    base["weights"] = {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5,
                       "load": 0.0}
    bad = copy.deepcopy(base)
    bad["gates"] = {"round_throat": "yes"}
    cfg_p = _embedded_cfg(tmp_path, bad)
    with pytest.raises(ConfigError, match="round_throat"):
        load_config(cfg_p)
    # A well-formed embedded gates block loads fine.
    good = copy.deepcopy(base)
    good["gates"] = {"round_throat": True}
    assert load_config(_embedded_cfg(tmp_path, good)).brief["gates"] == {"round_throat": True}


def _embedded_cfg(tmp_path, brief_raw) -> Path:
    """A run-directory config whose embedded brief carries the (in)valid gates block."""
    import yaml
    p = tmp_path / "cfg.yaml"
    raw = yaml.safe_load((Path(__file__).resolve().parents[1] / "examples" / "search_smoke.yaml")
                         .read_text(encoding="utf-8"))
    raw["brief"] = brief_raw
    raw.pop("brief_file", None)
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return p
