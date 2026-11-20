"""Horn + woofer GUI — control links (senior review 2026-11-20 §3.2/§3.3).

A case may DECLARE another case as a control; the server validates the declaration and never
infers one. These tests use a throwaway store whose solved runs are copies of the committed BL
headless fixture, so they are hermetic (no real store, no solver, no GPU).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.gui import data_hw as HW  # noqa: E402
from hornlab_search.system import provenance  # noqa: E402

FIXTURE_RUN = Path(__file__).resolve().parent / "fixtures" / "bl_results" / "reference_run"
PROJECT_SHA = "25e6bc51c585b2e9076592555967e96ed50248900015a9ea5d839b8498f3d47d"
PROBE = "observation:probe:on_axis"
SOURCE = "bl_src/20261119T000000Z-solved-1-aaaa"
LINK = "ev_lf/20261119T000001Z-lf-2-bbbb"
DENSE = "ev_dense/20261119T000005Z-dense-6-ffff"
WIDE = "ev_wide/20261119T000003Z-wide-4-dddd"
BAD = "ev_bad/20261119T000002Z-bad-3-cccc"
STAGED = "bl_stage/20261119T000004Z-stage-5-eeee"


def _case(store: Path, key: str, payload: dict, *, solved: bool) -> Path:
    d = store / "system" / key
    d.mkdir(parents=True)
    provenance.write_manifest(d, payload)
    if solved:
        shutil.copytree(FIXTURE_RUN, d / "run")
    return d


def _registry(root: Path, controls: dict[str, str], staged_controls: dict[str, str] | None = None) -> None:
    reg = root / HW.REGISTRY_REL
    reg.parent.mkdir(parents=True, exist_ok=True)
    cases = reg.parent / "cases.d"
    cases.mkdir(exist_ok=True)
    body = ["cases:"]
    for key, extra in ((SOURCE, controls), (STAGED, staged_controls or {})):
        body += [
            f"  - key: {key}",
            "    fidelity: COUPLED_VENTED_FEM_BEM_LEM",
            "    motor: demo",
            "    transducer_shape: demo",
            "    status: approved",
            "    approved_by: test",
        ]
        if extra:
            body.append("    controls:")
            body.extend(f"      {k}: {v}" for k, v in extra.items())
    (cases / "00_test.yaml").write_text("\n".join(body) + "\n", encoding="utf-8")
    reg.write_text(
        "schema: hw_readiness_v2\nupdated: 2026-11-20\ncase_files: [cases.d/*.yaml]\n"
        "risks: []\ndecisions: []\n", encoding="utf-8")
    HW._CACHE.clear()


@pytest.fixture()
def env(tmp_path: Path):
    root = tmp_path / "repo"
    store = root / "system_runs"
    spec = {"source": {"width_m": 0.32, "height_m": 0.5, "depth_m": 0.36,
                       "mesh_size_m": 0.04, "detail_size_m": 0.012},
            "horn": {"mesh_path": "horn/mesh.msh", "translation_mm": [0, 0, 20]}}
    _case(store, SOURCE, {"kind": "bl_motor_stage_project", "project_sha256": PROJECT_SHA,
                          "spec": spec, "result": {"ok": True}}, solved=True)
    _case(store, LINK, {"kind": "bl_evidence_case", "source_case": SOURCE}, solved=True)
    _case(store, DENSE, {"kind": "bl_evidence_case", "source_case": SOURCE}, solved=True)
    _case(store, WIDE, {"kind": "bl_evidence_case", "source_case": STAGED}, solved=True)
    _case(store, BAD, {"kind": "bl_evidence_case", "source_case": SOURCE}, solved=False)
    _case(store, STAGED, {"kind": "bl_stage_horn_project", "project_sha256": PROJECT_SHA,
                          "spec": spec, "result": {"ok": True}}, solved=False)
    return root, store


def _tokens(detail: dict) -> list[str]:
    return [p["token"] for p in detail["placeholders"]]


def test_valid_lf_link_changes_the_placeholder(env) -> None:
    root, store = env
    _registry(root, {"lf": LINK})
    d = HW.hw_case(root, store, SOURCE)
    tokens = _tokens(d)
    assert "LF_SOLVED_SEPARATELY" in tokens and "LF_NOT_SOLVED" not in tokens
    text = next(p["text"] for p in d["placeholders"] if p["token"] == "LF_SOLVED_SEPARATELY")
    assert LINK in text
    assert d["controls"]["valid"]["lf"]["key"] == LINK
    assert d["controls"]["invalid"] == []


def test_link_to_a_different_project_hash_is_invalid(env) -> None:
    root, store = env
    _registry(root, {"lf": LINK})
    manifest = store / "system" / LINK / "run" / "manifest.json"
    body = json.loads(manifest.read_text(encoding="utf-8"))
    body["project_sha256"] = "ff" * 32
    manifest.write_text(json.dumps(body), encoding="utf-8")
    d = HW.hw_case(root, store, SOURCE)
    tokens = _tokens(d)
    assert any(t.startswith("CONTROL_LINK_INVALID[different project_sha256]") for t in tokens)
    assert "LF_SOLVED_SEPARATELY" not in tokens and "LF_NOT_SOLVED" in tokens
    assert d["controls"]["valid"] == {}


def test_link_to_an_unsolved_case_is_invalid(env) -> None:
    root, store = env
    _registry(root, {"lf": BAD})
    d = HW.hw_case(root, store, SOURCE)
    tokens = _tokens(d)
    assert any(t.startswith("CONTROL_LINK_INVALID[linked case not solved") for t in tokens)
    assert "LF_SOLVED_SEPARATELY" not in tokens


def test_chart_payload_carries_two_separate_series(env) -> None:
    root, store = env
    _registry(root, {"lf": LINK})
    b = HW.hw_basis(root, store, SOURCE, PROBE)
    assert len(b["excitations"]) == 2                    # main (wide) series, per channel
    assert len(b["overlays"]) == 1
    overlay = b["overlays"][0]
    assert overlay["kind"] == "lf" and overlay["key"] == LINK
    assert overlay["refused"] is None
    assert overlay["frequencies_hz"] == b["frequencies_hz"]  # the fixture uses the same grid
    assert len(overlay["excitations"]) == 2               # LF series, per channel, separate
    for ex in overlay["excitations"]:
        assert ex["id"] in {e["id"] for e in b["excitations"]}
        assert isinstance(ex["spl_db"], list) and isinstance(ex["phase_deg"], list)
    # Nothing merges the two solves into one array or sums them.
    assert not any(k in b for k in ("sum", "combined", "merged", "series"))
    assert not any("sum" in k or "combin" in k or "merg" in k for k in overlay)


def test_wide_control_serves_a_staged_only_case(env) -> None:
    root, store = env
    _registry(root, {}, {"wide": WIDE})
    d = HW.hw_case(root, store, STAGED)
    assert d["run"] is None and d["control_run"] is not None
    assert d["controls"]["valid"]["wide"]["key"] == WIDE
    assert "WIDE_SOLVE_DECLARED" in _tokens(d)
    b = HW.hw_basis(root, store, STAGED, PROBE)
    assert b["source_control"] == {"kind": "wide", "key": WIDE}
    assert len(b["excitations"]) == 2


def test_dense_control_summary_is_python_computed(env) -> None:
    root, store = env
    _registry(root, {"dense": DENSE})
    summary = HW.hw_control_summary(root, store, SOURCE)
    assert summary["dense"]["key"] == DENSE
    assert summary["dense"]["max_abs_db"] == pytest.approx(0.0)   # byte-identical fixture runs
    assert summary["dense"]["shared_count"] == 2
    d = HW.hw_case(root, store, SOURCE)
    text = next(p["text"] for p in d["placeholders"] if p["token"] == "CONVERGENCE_SAMPLING")
    assert DENSE in text and "0.00 dB" in text and "2 shared points" in text
    assert "CONVERGENCE_MESH" in _tokens(d)
    mesh = next(p["text"] for p in d["placeholders"] if p["token"] == "CONVERGENCE_MESH")
    assert mesh == "Mesh refinement: not run."
