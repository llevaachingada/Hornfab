"""S10/M1 analysis views: ``parameter_study`` + ``source_fidelity`` tool cards.

The two artifacts are the frozen M1 schema (PARENT_M0_FREEZE.md §8, bo-study-v1.1). Fixtures
live under ``scratch/bo_m0/s10/fixtures/`` as two static sets: ``full`` (schema v1, both tools)
and ``degraded`` (old ``schema_version`` that must not be interpreted). The renderers are pure
HTML functions executed for real through node (``test_gui_group_e_helpers.py`` pattern). No NPZ
is read in a list view and no solve action exists.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from hornlab_search.gui import data as D
from hornlab_search.gui.server import App

ROOT = Path(__file__).resolve().parents[1]
APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"
FIXTURES = ROOT / "scratch" / "bo_m0" / "s10" / "fixtures"
FULL = FIXTURES / "full"
DEGRADED = FIXTURES / "degraded"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def artifacts() -> tuple[dict, dict, dict, dict]:
    assert (FULL / "parameter_study.json").is_file(), "missing full parameter_study fixture"
    assert (FULL / "source_fidelity.json").is_file(), "missing full source_fidelity fixture"
    assert (DEGRADED / "parameter_study.json").is_file(), "missing degraded fixture"
    assert (DEGRADED / "source_fidelity.json").is_file(), "missing degraded fixture"
    return (
        _load(FULL / "parameter_study.json"),
        _load(FULL / "source_fidelity.json"),
        _load(DEGRADED / "parameter_study.json"),
        _load(DEGRADED / "source_fidelity.json"),
    )


def test_analysis_tool_jsons_include_both_m1_tools():
    assert "parameter_study" in D.ANALYSIS_TOOL_JSONS
    assert "source_fidelity" in D.ANALYSIS_TOOL_JSONS


def test_analysis_sets_discovers_both_m1_tools():
    sets = {s["id"]: s for s in D.analysis_sets(FULL)}
    assert set(sets) == {"."}
    assert sets["."]["tools"] == ["parameter_study", "source_fidelity"]


def test_full_artifacts_pass_through_verbatim(tmp_path: Path):
    d = D.analysis_report(FULL, ".")
    assert d["tools"] == ["parameter_study", "source_fidelity"]
    ps = d["parameter_study"]
    assert ps["schema_version"] == 1 and ps["protocol"] == "bo-study-v1.1"
    assert ps["task_identity"]["objective_version"] == 4
    assert ps["task_identity"]["resolved_target"]["band_lo_hz"] == 300.0
    assert ps["task_identity"]["resolved_target"]["band_hi_hz"] == 8000.0
    assert ps["cohort"]["run_ids_missing"] is True
    assert ps["cohort"]["experiment_identity"]["status"] == "insufficient_evidence"
    assert [c["category"] for c in ps["controls"]] == [
        "searched", "searched", "searched", "searched", "inactive", "fixed", "derived"]
    assert len(ps["designs"]) == 3
    assert ps["designs"][0]["score_terms"]["total"] == 2.55
    assert ps["designs"][0]["score_terms"]["total_matches_replay_j"] is True
    assert ps["designs"][0]["identities"]["physical_id"].startswith("phys-")
    assert ps["designs"][0]["provenance"]["row"] == 17
    assert ps["designs"][0]["provenance"]["run_id"] is None
    assert ps["designs"][0]["geometry_descriptors"]["descriptors"]["mouth_width_mm"] == 421.3
    sf = d["source_fidelity"]
    assert sf["schema_version"] == 1
    assert sf["source_assumption_context"]["f11_hz"] == 3957.0
    assert sf["designs"][0]["di_source"] == "balloon"
    assert sf["designs"][1]["di_source"] == "cuts_estimate"
    assert sf["designs"][0]["verify_pairing"]["status"] == "paired"
    assert sf["designs"][2]["verify_pairing"]["status"] == "pairing_unavailable"
    # unknown fields ride along untouched (the API path never interprets them)
    adir = tmp_path / "analysis"
    adir.mkdir()
    payload = _load(FULL / "parameter_study.json")
    payload["_unknown_field_from_a_future_tool"] = {"x": 1}
    (adir / "parameter_study.json").write_text(json.dumps(payload), encoding="utf-8")
    assert D.analysis_report(adir, ".")["parameter_study"]["_unknown_field_from_a_future_tool"] == {"x": 1}


def test_api_serves_m1_payloads_verbatim(tmp_path: Path, artifacts):
    full_ps, full_sf, _, _ = artifacts
    app = App(tmp_path, tmp_path, analysis_dir=FULL)
    idx = app.get("/api/analysis", {})
    assert isinstance(idx, list)
    assert [s["id"] for s in idx] == ["."]
    det = app.get("/api/analysis/.", {})
    assert isinstance(det, dict)
    assert det["parameter_study"] == full_ps
    assert det["source_fidelity"] == full_sf


_GUARD_SCRIPT = r'''
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

const fake = () => ({ className: "", id: "", style: {}, dataset: {}, innerHTML: "", textContent: "",
  setAttribute() {}, getAttribute: () => null, replaceWith() {}, appendChild() {},
  addEventListener() {}, removeEventListener() {}, closest: () => null,
  classList: { toggle() {}, add() {}, remove() {} }, querySelector: () => null, querySelectorAll: () => [] });
globalThis.document = {
  getElementById: () => fake(), createElement: () => fake(), createElementNS: () => fake(),
  querySelector: () => null, querySelectorAll: () => [], addEventListener() {},
  documentElement: { hasAttribute: () => true, setAttribute() {}, getAttribute: () => null, style: {} },
  body: { appendChild() {} },
};
globalThis.window = { innerWidth: 1280, addEventListener() {}, scrollTo() {} };
globalThis.matchMedia = () => ({ matches: true, addEventListener() {} });
globalThis.MutationObserver = class { observe() {} };
globalThis.location = { hash: "#/analysis" };
globalThis.requestAnimationFrame = () => 0;
globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
globalThis.fetch = () => Promise.reject(new Error("offline shim"));

const app = await import(pathToFileURL(process.argv[2]).href);
const { analysisParameterStudyHtml, analysisSourceFidelityHtml, studyCaveatHz } = app;
const fullPs = JSON.parse(await readFile(join(process.argv[3], "parameter_study.json"), "utf8"));
const fullSf = JSON.parse(await readFile(join(process.argv[3], "source_fidelity.json"), "utf8"));
const oldPs = JSON.parse(await readFile(join(process.argv[4], "parameter_study.json"), "utf8"));
const oldSf = JSON.parse(await readFile(join(process.argv[4], "source_fidelity.json"), "utf8"));

// ── full parameter study: observed-only values, units, decomposition, identities, links ──
const ps = analysisParameterStudyHtml(fullPs);
assert.ok(ps.includes("Parameter study") && ps.includes("bo-study-v1.1"), ps.slice(0, 400));
assert.ok(ps.includes("Task identity") && ps.includes("objective") && ps.includes("v4"));
assert.ok(ps.includes("Band") && ps.includes("300 – 8000") && ps.includes("Hz"));
assert.ok(ps.includes("Weights and tolerances") && ps.includes("unitless") && ps.includes("metric units"));
assert.ok(ps.includes("Controls — activity"), "controls table");
assert.ok(ps.includes("searched") && ps.includes("inactive") && ps.includes("fixed") && ps.includes("derived"));
assert.ok(ps.includes("L_mm") && ps.includes("mm"));
assert.ok(ps.includes("421.3") && ps.includes("mouth_width_mm"));
assert.ok(ps.includes("Designs (3) — observed"));
assert.ok(ps.includes("Design 1/3") && ps.includes("a1b2c3d4e5f6"));
assert.ok(ps.includes("Response bands (observed)") && ps.includes("300 Hz – 2,000 Hz"));
assert.ok(ps.includes("above source caveat geometry comparison") && ps.includes("di_db 4.90 dB"));
assert.ok(ps.includes("J decomposition") && ps.includes("raw (J)") && ps.includes("normalized (J)") && ps.includes("weighted (J)"));
assert.ok(ps.includes("total") && ps.includes("2.55") && ps.includes("total matches replay J"));
assert.ok(ps.includes("Identities (immutable)") && ps.includes("physical") && ps.includes("metric") && ps.includes("score"));
assert.ok(ps.includes("Selection reason") && ps.includes("lowest_j_then_maximin") && ps.includes("frozen_j 2.55 J"));
assert.ok(ps.includes("sampling converged"));
assert.ok(ps.includes("Parity — observed replay comparison") && ps.includes("max_abs_delta"));
assert.ok(ps.includes("Held-out — predictive error") && ps.includes("rmse_j"));
assert.ok(ps.includes("Limitations") && ps.includes("never be ranked across objective versions"));
assert.ok(ps.includes("3957 Hz"), "3957 Hz source caveat surfaced on the observed design");
// cohort.run_ids_missing is true in the full fixture -> a muted note, never a fabricated link
assert.ok(ps.includes("no run id recorded"), "absent run ids stay muted");
assert.ok(!ps.includes("#/run/"), "no run link without a recorded run id");
// no solve/action wording anywhere
assert.ok(!/\bsolve\b|\bqueue\b|\brun now\b/i.test(ps), "no solve action in a list view");

// a recorded run id turns provenance into an existing runs-tree deep link
const linked = JSON.parse(JSON.stringify(fullPs));
linked.designs[0].provenance.run_id = "20261111T000000Z-screen-aaaaaa";
const linkedHtml = analysisParameterStudyHtml(linked);
assert.ok(linkedHtml.includes('#/run/20261111T000000Z-screen-aaaaaa'), linkedHtml.slice(0, 500));
assert.ok(linkedHtml.includes("open run"));
assert.ok(linkedHtml.includes("no run id recorded"), "other designs still have no run id");

// ── full source & fidelity: DI source honesty, pairing, size, missingness, caveat ──
const sf = analysisSourceFidelityHtml(fullSf, studyCaveatHz(fullPs));
assert.ok(sf.includes("Source &amp; fidelity") && sf.includes("bo-study-v1.1"), sf.slice(0, 400));
assert.ok(sf.includes("Source caveat") && sf.includes("3957 Hz"));
assert.ok(sf.includes("DI source (observed)") && sf.includes("balloon"));
assert.ok(sf.includes("cuts estimate (not real DI)") && sf.includes("DI estimated term"));
assert.ok(sf.includes("DI evidence (observed)") && sf.includes("stored cuts_estimate"));
assert.ok(sf.includes("Verify pairing (observed)") && sf.includes("no_verify_row") && sf.includes("pairing_unavailable"));
assert.ok(sf.includes("paired verify row"));
assert.ok(sf.includes("Physical size (observed)") && sf.includes("421.3") && sf.includes("mm"));
assert.ok(sf.includes("B2 per-design descriptors: not joinable"));
assert.ok(sf.includes("Missingness (observed)") && sf.includes("balloon present")
  && sf.includes("npz readable") && sf.includes("6 stored arrays"));
assert.ok(sf.includes("balloon missing (balloon_dirs, spl_balloon_db)"));
assert.ok(sf.includes("unique design hashes (count)") && sf.includes("pairing status counts"));
assert.ok(sf.includes("Limitations"));
// only the design whose run provenance resolved gets a run link; ambiguity stays a note
assert.ok(sf.includes('#/run/20261111T000000Z-screen-aaaaaa'), "resolved run provenance links");
assert.ok(sf.includes("run provenance ambiguous"));
assert.ok(sf.includes("no run id recorded"), "unresolved provenance stays muted");

// ── degraded / old-schema artifacts: an explicit note, no interpreted values ──
const oldPsHtml = analysisParameterStudyHtml(oldPs);
assert.ok(oldPsHtml.includes("schema_version 0") && oldPsHtml.includes("not rendered"), oldPsHtml);
assert.ok(!oldPsHtml.includes("J decomposition") && !oldPsHtml.includes("raw (J)"));
assert.ok(!oldPsHtml.includes("Design 1/") && !oldPsHtml.includes("100"));
const oldSfHtml = analysisSourceFidelityHtml(oldSf, 3957);
assert.ok(oldSfHtml.includes("schema_version 0") && oldSfHtml.includes("not rendered"), oldSfHtml);
assert.ok(!oldSfHtml.includes("Physical size") && !oldSfHtml.includes("cuts_estimate"));
assert.ok(!oldSfHtml.includes("3957"), "the old payload's caveat is not invented into a render");

// ── absent payload behaves like the existing five sections: nothing rendered ──
assert.equal(analysisParameterStudyHtml(null), "");
assert.equal(analysisParameterStudyHtml({}), "");
assert.equal(analysisSourceFidelityHtml(undefined), "");
assert.equal(analysisSourceFidelityHtml({}), "");
assert.equal(analysisParameterStudyHtml({ tool: "some_future_tool", schema_version: 1 }).includes("some_future_tool"), true);

console.log("M1 GUARD OK");
'''


def test_m1_analysis_renderers_execute(tmp_path: Path, artifacts):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "guard_m1_under_test.mjs"
    script.write_text(_GUARD_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(APPJS), str(FULL), str(DEGRADED)],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert "M1 GUARD OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"


def test_app_js_parses_as_an_es_module(tmp_path: Path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    mjs = tmp_path / "app.mjs"
    mjs.write_text(APPJS.read_text(encoding="utf-8"), encoding="utf-8")
    r = subprocess.run([node, "--check", str(mjs)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
