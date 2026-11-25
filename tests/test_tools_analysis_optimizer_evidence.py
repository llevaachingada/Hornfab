"""P1a composed optimizer-evidence report: read-only, advisory, never dispatches work."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
import yaml

from test_tools_analysis_common import (BASE_CONFIG, REPO, load_tool, make_row, run_cli,
                                        write_run)

oe = load_tool("optimizer_evidence")

V7_BRIEF = "examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml"
CONFIDENCES = {"measured", "strongly_indicated", "hypothesis"}
FLOOR_DEPENDENT_ACTIONS = {"extend_same_identity_lane", "common_grid_verification"}


def _brief_run(tmp_path, brief_rel, rows, name, bounds=None):
    brief_path = (REPO / brief_rel).resolve()
    cfg = dict(yaml.safe_load(brief_path.read_text(encoding="utf-8")))
    cfg["brief_file"] = str(brief_path)
    cfg["name"] = f"test_{name}"
    cfg["family"] = "OSSE"
    cfg["solve"] = {"backend": "beat_cuda", "angle_count": 73, "balloon": True,
                    "balloon_points_screen": 512}
    cfg["mesh"] = {"quadrants": "1", "epw": 6.0, "rear_res_factor": 1.5}
    if bounds is not None:
        cfg["bounds"] = bounds
    return write_run(rows, tmp_path, name, config=cfg, family="OSSE")


def _payload(tmp_path, name="out"):
    return json.loads((tmp_path / name / "optimizer_evidence.json").read_text(
        encoding="utf-8"))


# --------------------------------------------------------------------------- (a)


def test_compatible_run_card_alternatives_and_advisory_flags(tmp_path):
    valid = [make_row(i, 5.0 - 0.005 * i, version=7) for i in range(30)]
    refused = [make_row(100 + i, 1000.0, ok=False, kind="invalid_geometry", version=7)
               for i in range(30)]
    run = _brief_run(tmp_path, V7_BRIEF, valid + refused, "v7_failure")

    proc = run_cli("optimizer_evidence", ["--run", str(run)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    payload = _payload(tmp_path)

    assert payload["schema"] == "optimizer-evidence-v1"
    assert payload["advisory_only"] is True
    assert payload["dispatches_work"] is False
    assert payload["changes_defaults"] is False
    assert len(payload["run_cards"]) == 1

    card = payload["run_cards"][0]
    assert card["identity"]["objective_version"] == 7
    assert card["identity"]["brief"]["name"] == "room_landscape_80x50_700_hf1440_v7"
    assert card["outcome_counts"]["valid"] == 30
    assert card["outcome_counts"]["geometry_refusal"] == 30
    assert card["continuation"]["status"] == "matched"
    assert card["continuation"]["floor_J"] == 0.3104791983512361
    assert card["continuation"]["match_quality"] in ("exact", "exact_core")
    # every key number carries a source tool and field path
    fields = {p["field"] for p in card["provenance"]}
    assert {"best_j", "floor_J", "recorded_total_seconds"} <= fields
    assert all(p.get("source_tool") and p.get("source_field") for p in card["provenance"])

    assert 1 <= len(payload["alternatives"]) <= 2
    assert payload["alternatives"][0]["action"] == "investigate_geometry_envelope_resource"
    assert payload["alternatives"][0]["confidence"] in CONFIDENCES
    for ev in payload["alternatives"][0]["evidence"]:
        assert set(ev) == {"tool", "field", "value"}
    assert payload["decision"]["status"] == "ok"
    assert payload["cross_run"]["compatible_for_inference"] is True
    assert payload["opt_in"]["space_card"]["status"] == "skipped"
    assert payload["opt_in"]["geometry_activity"]["status"] == "skipped"
    assert "not requested" in payload["opt_in"]["space_card"]["reason"]


# --------------------------------------------------------------------------- (b)


def _continuation_rows(version=7):
    params = {"a_deg": 35.0, "a0_deg": 15.0, "n": 4.5, "t0_mm": 40.0}
    return [make_row(i, 5.0 - 0.005 * max(0, i - 49), version=version, params=params)
            for i in range(150)]


def test_above_floor_continuation_emits_one_same_identity_alternative(tmp_path):
    run = _brief_run(tmp_path, V7_BRIEF, _continuation_rows(), "v7_continue")

    proc = run_cli("optimizer_evidence", ["--run", str(run)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    payload = _payload(tmp_path)

    card = payload["run_cards"][0]
    assert card["continuation"]["advice"] == "propose continuation"
    assert card["continuation"]["floor_J"] == 0.3104791983512361
    assert card["continuation"]["match_quality"] in ("exact", "exact_core")
    assert len(payload["alternatives"]) == 1
    alt = payload["alternatives"][0]
    assert alt["action"] == "extend_same_identity_lane"
    assert alt["confidence"] == "strongly_indicated"
    fields = {ev["field"] for ev in alt["evidence"]}
    assert {"improvement", "resolution.floor_J", "resolution.match_quality",
            "identity.brief.name", "identity.brief.sha256",
            "identity.score_identity_hash"} <= fields
    assert payload["decision"]["status"] == "ok"


def test_alternative_cap_holds_when_three_signals_are_present(tmp_path):
    rows = _continuation_rows()
    for row in rows:
        row["params"] = {"a_deg": 60.0, "a0_deg": 15.0, "n": 4.5, "t0_mm": 40.0}
    rows += [make_row(200 + i, 1000.0, ok=False, kind="invalid_geometry", version=7)
             for i in range(30)]
    run = _brief_run(tmp_path, V7_BRIEF, rows, "v7_three_signals",
                     bounds=BASE_CONFIG["bounds"])

    proc = run_cli("optimizer_evidence", ["--run", str(run)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    payload = _payload(tmp_path)

    card = payload["run_cards"][0]
    assert card["continuation"]["advice"] == "propose continuation"
    assert any(w["key"] == "a_deg" and w["wall_hi"] for w in card["walls"])
    assert card["failure_signal"]["above_threshold"] is True
    assert len(payload["alternatives"]) == 2  # three candidates, capped at two
    assert [alt["action"] for alt in payload["alternatives"]] == [
        "investigate_geometry_envelope_resource", "review_limits_not_auto_widen"]


def test_no_floor_dependent_alternative_without_matched_floor(tmp_path):
    run = write_run(_continuation_rows(version=4), tmp_path, "v4_no_floor")

    proc = run_cli("optimizer_evidence", ["--run", str(run)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    payload = _payload(tmp_path)

    card = payload["run_cards"][0]
    assert card["continuation"]["floor_J"] is None
    assert card["continuation"]["advice"] == "no applicable published floor"
    actions = [alt["action"] for alt in payload["alternatives"]]
    assert not any(action in FLOOR_DEPENDENT_ACTIONS for action in actions)
    assert payload["decision"]["status"] == "insufficient_evidence"


# --------------------------------------------------------------------------- (b) unknown identity diagnostics


def test_unknown_identity_has_no_floor_and_insufficient_evidence(tmp_path):
    run = write_run([make_row(i, 5.0 - 0.01 * i, version=4) for i in range(30)],
                    tmp_path, "unknown")

    proc = run_cli("optimizer_evidence", ["--run", str(run)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    payload = _payload(tmp_path)

    card = payload["run_cards"][0]
    assert card["continuation"]["floor_J"] is None
    assert card["continuation"]["status"] == "no_applicable_floor"
    assert card["continuation"]["advice"] == "no applicable published floor"
    assert payload["decision"]["status"] == "insufficient_evidence"
    assert not any(alt["action"] in FLOOR_DEPENDENT_ACTIONS
                   for alt in payload["alternatives"])


def test_unknown_identity_failure_alternative_survives_missing_floor(tmp_path):
    rows = [make_row(i, 5.0 - 0.01 * i, version=4) for i in range(5)]
    rows += [make_row(100 + i, 1000.0, ok=False, kind="invalid_geometry", version=4)
             for i in range(25)]
    run = write_run(rows, tmp_path, "unknown_failure")

    proc = run_cli("optimizer_evidence", ["--run", str(run)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    payload = _payload(tmp_path)

    card = payload["run_cards"][0]
    assert card["continuation"]["floor_J"] is None
    assert payload["decision"]["status"] == "insufficient_evidence"
    assert card["run_id"] in payload["decision"]["missing_floor_runs"]
    actions = [alt["action"] for alt in payload["alternatives"]]
    assert "investigate_geometry_envelope_resource" in actions
    assert not any(action in FLOOR_DEPENDENT_ACTIONS for action in actions)


# --------------------------------------------------------------------------- (c)


def test_incompatible_objective_versions_block_and_never_rank_j(tmp_path):
    cfg_a = dict(yaml.safe_load(yaml.safe_dump({
        "name": "native__ath_core_v4", "family": "OSSE",
        "weights": {"cov": 1.0},
        "objective": {"version": 4, "tolerances": {"cov": 0.05}},
        "bounds": {"a_deg": {"lo": 10.0, "hi": 60.0}},
    })))
    cfg_b = dict(cfg_a)
    cfg_b["name"] = "native__ath_core_v5"
    cfg_b["objective"] = {"version": 5, "tolerances": {"cov": 0.05}}

    run_a = write_run([make_row(i, 5.0, version=4) for i in range(4)],
                      tmp_path, "a", config=cfg_a)
    run_b = write_run([make_row(i, 5.0, version=5) for i in range(4)],
                      tmp_path, "b", config=cfg_b)

    proc = run_cli("optimizer_evidence",
                   ["--run", str(run_a), "--run", str(run_b)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    payload = _payload(tmp_path)

    cross = payload["cross_run"]
    assert cross["compatible_for_inference"] is False
    assert "objective_version_mismatch" in cross["blocking"]
    assert cross["ranking"]["performed"] is False
    assert cross["ranking"]["raw_j_ranking"] is None
    assert "Never compare raw J" in cross["decision_rule"]
    assert payload["decision"]["status"] == "insufficient_evidence"
    assert payload["alternatives"] == []


# --------------------------------------------------------------------------- (d)


def test_out_inside_a_run_dir_is_refused(tmp_path):
    run = write_run([make_row(0, 1.0)], tmp_path, "run")
    with pytest.raises(SystemExit) as excinfo:
        oe.main(["--run", str(run), "--out", str(run / "nested" / "out")])
    assert excinfo.value.code == 2


# --------------------------------------------------------------------------- (e)


def test_missing_catalog_and_manifests_are_not_supplied(tmp_path):
    run = write_run([make_row(i, 5.0, version=4) for i in range(4)], tmp_path, "run")
    proc = run_cli("optimizer_evidence", ["--run", str(run)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    payload = _payload(tmp_path)
    assert payload["seed_pack"] == {"status": "not_supplied"}
    assert payload["qd_compare"] == {"status": "not_supplied"}


# --------------------------------------------------------------------------- (f)


def _reject_constant(value):
    raise AssertionError(f"non-finite JSON constant emitted: {value!r}")


def _assert_all_finite(node):
    if isinstance(node, dict):
        for value in node.values():
            _assert_all_finite(value)
    elif isinstance(node, list):
        for value in node:
            _assert_all_finite(value)
    elif isinstance(node, float):
        assert math.isfinite(node)


def test_output_json_has_no_non_finite_values(tmp_path):
    run = write_run([make_row(i, 5.0 - 0.01 * i) for i in range(8)], tmp_path, "run")
    # A torn/legacy row can carry non-finite JSON numbers; the report must still be strict JSON.
    with (run / "search.ndjson").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"n": 999, "ok": False, "kind": "solve_failed",
                             "objective": float("nan"), "cached": False,
                             "objective_version": 4,
                             "seconds": {"total": float("inf")}},
                            allow_nan=True) + "\n")

    proc = run_cli("optimizer_evidence", ["--run", str(run)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    text = (tmp_path / "out" / "optimizer_evidence.json").read_text(encoding="utf-8")
    parsed = json.loads(text, parse_constant=_reject_constant)
    _assert_all_finite(parsed)
