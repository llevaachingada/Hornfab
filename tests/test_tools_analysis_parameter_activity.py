"""Focused tests for tools/analysis/parameter_activity.py (B2 M0, offline).

The real resolved ATH v4 candidate is the fixture.  These tests assert the hardening decision's
required facts, not just field presence:
  * alphabetical 14-key search vector and the six fixed/derived controls;
  * morph_exponent inactive ONLY from source + target-1 invariance plus target-3 activity;
  * morph_fixed resolved bound 0.0-0.6 (the 0-0.1 comment is recorded, never applied);
  * s1/s2 stretch conditionality;
  * reversible active projection and the honest task-eligibility status.
"""
from __future__ import annotations

import json

import pytest

from conftest import REPO, requires_mesher
from test_tools_analysis_common import load_tool, run_cli

pa = load_tool("parameter_activity")

CONFIG = REPO / "examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml"


@pytest.fixture(scope="module")
def ledger():
    return pa.build_ledger(CONFIG, run_geometry=True, resolution_mm=12.0)


def _by_key(ledger):
    return {c["key"]: c for c in ledger["controls"]}


@requires_mesher
def test_ledger_has_all_controls_and_alphabetical_search(ledger):
    assert ledger["schema"] == "parameter-activity-v1"
    keys = ledger["search"]["keys"]
    assert keys == sorted(keys) and len(keys) == 14
    assert keys == ["L_mm", "a_deg", "k", "morph_corner_mm", "morph_exponent",
                    "morph_fixed", "morph_height_mm", "morph_rate", "morph_width_mm",
                    "n", "q", "s", "s1", "s2"]
    assert len(ledger["controls"]) == 20
    assert ledger["counts"] == {"searched": 4, "fixed": 4, "derived": 2,
                                "conditional": 9, "inactive": 1, "unresolved": 0}
    c = _by_key(ledger)
    assert c["r0_mm"]["category"] == "derived" and c["a0_deg"]["category"] == "derived"
    assert c["morph_target"]["category"] == "fixed"
    assert c["morph_target"]["resolved"]["bound"]["search"] is False
    assert ledger["task_eligibility"]["status"] == "insufficient_evidence"


@requires_mesher
def test_morph_exponent_inactivity_needs_source_and_geometry(ledger):
    c = _by_key(ledger)["morph_exponent"]
    assert c["category"] == "inactive"
    assert c["evidence"]["status"] == "confirmed_inactive_conditional"
    # Static source reference: the installed target-3 branch, not a comment or a flat local probe.
    refs = c["source_refs"]
    assert any(r["file"] == "hornlab_mesher/profile_morph.py" and r["line"] for r in refs)
    assert any(r["file"] == "hornlab_search/design/params/knobs_native.py" for r in refs)
    # Geometry test: target 1 invariant, target 3 active.
    g = c["evidence"]["geometry_test"]
    assert g["target_1"]["changed"] is False
    assert g["target_1"]["max_abs_delta_mm"] == 0.0
    assert g["target_3"]["changed"] is True
    assert g["target_3"]["max_abs_delta_mm"] > 1.0
    assert g["inactive"] is True and g["changed"] is True


@requires_mesher
def test_morph_fixed_bound_is_0_to_0_6_despite_comment(ledger):
    c = _by_key(ledger)["morph_fixed"]
    assert c["resolved"]["bound"]["lo"] == 0.0
    assert c["resolved"]["bound"]["hi"] == 0.6
    blob = json.dumps(c)
    assert "0.6" in blob
    assert any("0-0.1" in note for note in c["notes"])
    # The YAML comment is recorded as a source reference (not silently replaced by 0.6).
    yaml_lines = CONFIG.read_text(encoding="utf-8").splitlines()
    comment_refs = [r for r in c["source_refs"]
                    if r["file"].endswith(".yaml") and r["line"]
                    and "morph_fixed 0-0.1" in yaml_lines[r["line"] - 1]]
    assert comment_refs


@requires_mesher
def test_stretch_conditionality_is_geometry_tested(ledger):
    c = _by_key(ledger)
    for key, cond in (("s1", "s2 == 0"), ("s2", "s1 == 0")):
        g = c[key]["evidence"]["geometry_test"]
        assert g["changed"] is True
        assert g["condition_test"]["condition"] == cond
        assert g["condition_test"]["changed"] is False


@requires_mesher
def test_active_projection_is_versioned_reversible_noop_only(ledger):
    p = ledger["active_projection"]
    assert p["version"] == "active-projection-v1"
    assert p["full_keys"] == ledger["search"]["keys"]
    assert p["fixed_values"] == {"morph_exponent": 4.0}
    assert "morph_exponent" not in p["active_keys"]
    assert len(p["active_keys"]) == 13
    assert p["reversible"] is True
    assert p["conditions"] == {"morph_target": 1}
    assert pa.no_op_projection(ledger) == {"morph_exponent": 4.0}


def test_static_ledger_without_geometry_is_honest():
    p = pa.build_ledger(CONFIG, run_geometry=False)
    c = _by_key(p)["morph_exponent"]
    assert c["category"] == "inactive"
    assert c["evidence"]["geometry_test"] is None
    # Without the geometry proof the advisory projection must NOT be applied.
    assert p["active_projection"]["fixed_values"] == {}
    assert "not proven" in (p["active_projection"].get("refused") or "")
    assert p["geometry"]["mesh_built"] is False


@requires_mesher
def test_cli_writes_json_and_markdown(tmp_path):
    proc = run_cli("parameter_activity", ["--config", str(CONFIG), "--no-geometry",
                                          "--out", str(tmp_path / "out")], tmp_path)
    assert proc.returncode == 0, proc.stderr
    out = tmp_path / "out"
    doc = json.loads((out / "parameter_activity.json").read_text(encoding="utf-8"))
    assert doc["tool"] == "parameter_activity"
    assert doc["schema"] == "parameter-activity-v1"
    assert doc["counts"]["inactive"] == 1
    md = (out / "parameter_activity.md").read_text(encoding="utf-8")
    assert "Parameter activity ledger" in md
    assert "insufficient evidence" in md
