"""S8/S7 analysis-page panels (2026-11-13): geometry, hypothesis, QD/Pareto, surrogate.

The fixtures are literal copies of the four tools' JSON contracts
(``docs/HANDOFF_S8_S7_GUI_2026-11-13.md`` §3). No tool is executed, no solve runs and no
payload is inferred: the API passes stored fields through verbatim, and the node guard runs
the real pure HTML builders from ``app.js``. The keyed ``surrogate_validation-<hash>.json``
discovery is exercised separately because the S7 tool writes no fixed ``<tool>.json``.
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
GEN = "2026-11-13T18:00:00Z"

GEOMETRY = {
    "tool": "geometry_descriptors", "generated_utc": GEN,
    "schema_version": "geometry-descriptors-v1",
    "descriptor_keys": ["length_mm", "mouth_width_mm", "mouth_height_mm", "mouth_aspect_w_h",
                        "mouth_projected_area_mm2", "throat_projected_area_mm2",
                        "mouth_to_throat_area_ratio", "mouth_width_over_length",
                        "mouth_height_over_length"],
    "geometry_only": True,
    "designs": [
        {"schema_version": "geometry-descriptors-v1", "design_hash": "a" * 12, "family": "OSSE",
         "units": {"length": "mm", "area": "mm2", "ratio": "dimensionless"},
         "geometry": {"length_mm": 123.4, "mouth_width_mm": 400.0, "mouth_height_mm": 250.0,
                      "mouth_aspect_w_h": 1.6, "mouth_projected_area_mm2": 70000.0,
                      "throat_projected_area_mm2": 500.0,
                      "mouth_to_throat_area_ratio": 140.0,
                      "mouth_width_over_length": 3.241, "mouth_height_over_length": 2.026},
         "termination": {"kind": "osse", "n": 1.0, "s": 0.7, "q": 0.9},
         "provenance": {"api": "hornlab_mesher.config_builder.resolve_geometry",
                        "resolver_module": "hornlab_mesher.config_builder",
                        "resolver_source_sha256": "f" * 64, "formula": "stored-formula",
                        "resolution_mm": 8.0, "mesh_built": False,
                        "gmsh_called": False, "bem_called": False},
         "navigation_only": {"pca": "not computed", "kmeans": "not computed",
                             "note": "navigation only"}},
        {"schema_version": "geometry-descriptors-v1", "design_hash": "b" * 12, "family": "ICW",
         "units": {"length": "mm", "area": "mm2", "ratio": "dimensionless"},
         "geometry": {"length_mm": 98.75, "mouth_width_mm": 300.0, "mouth_height_mm": 300.0,
                      "mouth_aspect_w_h": 1.0, "mouth_projected_area_mm2": 60000.0,
                      "throat_projected_area_mm2": 480.0,
                      "mouth_to_throat_area_ratio": 125.0,
                      "mouth_width_over_length": 3.038, "mouth_height_over_length": 3.038},
         "termination": {"kind": "tractrix"},
         "provenance": {"api": "hornlab_mesher.config_builder.resolve_geometry",
                        "resolver_module": "hornlab_mesher.config_builder",
                        "resolver_source_sha256": "f" * 64, "formula": "stored-formula",
                        "resolution_mm": 8.0, "mesh_built": False,
                        "gmsh_called": False, "bem_called": False},
         "navigation_only": {"pca": "not computed", "kmeans": "not computed",
                             "note": "navigation only"}},
    ],
    "navigation": {
        "schema_version": "geometry-navigation-v1", "navigation_only": True, "ranking": False,
        "feature_keys": [
            "length_mm", "mouth_width_mm", "mouth_height_mm", "mouth_aspect_w_h",
            "mouth_projected_area_mm2", "throat_projected_area_mm2",
            "mouth_to_throat_area_ratio", "mouth_width_over_length", "mouth_height_over_length"],
        "standardization": {"mean": [0.0] * 9, "std": [1.0] * 9, "zero_variance_keys": []},
        "pca": {"explained_variance_ratio": [0.62, 0.21], "components": [[1.0] * 9, [0.5] * 9]},
        "kmeans": {"clusters": 2, "seed": 1030, "n_init": 8, "inertia": 0.5,
                   "centers_standardized": [[0.0] * 9, [1.0] * 9]},
        "rows": [{"design_hash": "a" * 12, "pc1": -1.2, "pc2": 0.4, "cluster": 0},
                 {"design_hash": "b" * 12, "pc1": 1.1, "pc2": -0.3, "cluster": 1}],
        "note": "PCA and k-means are navigation aids only; no quality ordering is implied.",
    },
}

HYPOTHESIS = {
    "tool": "hypothesis_cards", "schema_version": 1, "status": "proposed", "generated_utc": GEN,
    "identity": {"task_id": "task-athi", "scoring_context_id": "score-ctx-1",
                 "objective_version": 4, "physical_spec_id": "spec-1"},
    "resolved_context_sha256": "c" * 64,
    "parents": [
        {"id": "aaaaaaaaaaaa", "design_hash": "a" * 12, "source": "runs/parent_a.json",
         "source_sha256": "d" * 64, "family": "OSSE", "params": {"n": 1.0}},
        {"id": "bbbbbbbbbbbb", "design_hash": "b" * 12, "source": "runs/parent_b.json",
         "source_sha256": "e" * 64, "family": "ICW", "params": {"termination": "tractrix"}},
    ],
    "experiments": [
        {"role": role, "parent_ids": ["aaaaaaaaaaaa", "bbbbbbbbbbbb"],
         "config": f"configs/{role}.yaml", "config_sha256": "1" * 64,
         "design_hash": ("a" * 12 if role == "parent_a" else
                         "b" * 12 if role == "parent_b" else f"{i}" * 12),
         "family": "OSSE", "params": {"n": 1.0},
         "validation": "canonical_geometry_resolved",
         "geometry_descriptors": {"design_hash": "a" * 12},
         "physical_feasibility": "unverified_requires_normal_evaluator",
         **({"removed_feature": f"feature-{role[-1]}"} if role.startswith("ablate") else {})}
        for i, role in enumerate(("parent_a", "parent_b", "combination", "ablate_a",
                                  "ablate_b", "broad_control"), start=2)],
    "expected_band_hz": [500.0, 4000.0],
    "trade_off": "more mouth aspect for less low-frequency loading",
    "unknowns": ["driver exit wavefront"], "features": ["profile blend"],
    "constraints": ["max depth 300 mm"],
    "evidence": "hypothesis only; acoustic effects and mesh feasibility unmeasured",
    "card_id": "9" * 64,
}

QD = {
    "schema": "qd-compare-report-v1", "tool": "qd_compare", "generated_utc": GEN,
    "identity": {"objective_version": 4, "scoring_context_id": "score-ctx-1",
                 "task_id": "task-athi", "spec_id": "spec-1", "brief_id": "brief-1",
                 "family": "OSSE", "weights": {"cov": 1.0}, "tolerances": {"cov": 0.05}},
    "input_manifests": {"a": {"source": "scratch/arm_a.json", "sha256": "1" * 64},
                        "b": {"source": "scratch/arm_b.json", "sha256": "2" * 64}},
    "axes": [{"name": "coverage_error_deg", "unit": "deg", "direction": "minimize"},
             {"name": "ripple_db", "unit": "dB", "direction": "minimize"}],
    "frozen_reference": [30.0, 6.0],
    "descriptor_space": {"names": ["mouth_aspect", "area_ratio"],
                         "ranges": [[0.25, 4.0], [1.0, 500.0]],
                         "arm_reconstruction_hashes": {"cma_me": "3" * 64,
                                                       "nsga": "4" * 64}},
    "equal_cost": {"unit": "equivalent_evaluations", "total": 60,
                   "includes": ["successful", "failed", "refused", "training", "other"]},
    "arms": [
        {"arm_id": "cma_me", "algorithm": "cma_me",
         "cost": {"unit": "equivalent_evaluations", "successful": 30, "failed": 2,
                  "refused": 1, "training": 5, "other": 0, "total": 60, "checkpoints": []},
         "n_eligible": 2, "n_eligible_attempts": 2, "duplicate_eligible_attempt_ids": [],
         "n_excluded": 1, "excluded_ids": ["fail-1"],
         "outcome_categories": {"measured": 2, "solve_failed": 1},
         "front": [{"id": "a1", "design_hash": "a" * 12, "reconstruction_hash": "5" * 64,
                    "category": "measured", "objectives": [8.0, 1.5]},
                   {"id": "a2", "design_hash": "b" * 12, "reconstruction_hash": "6" * 64,
                    "category": "measured", "objectives": [10.0, 1.1]}],
         "hypervolume": 132.0},
        {"arm_id": "nsga", "algorithm": "nsga2",
         "cost": {"unit": "equivalent_evaluations", "successful": 28, "failed": 4,
                  "refused": 1, "training": 5, "other": 0, "total": 60, "checkpoints": []},
         "n_eligible": 3, "n_eligible_attempts": 3, "duplicate_eligible_attempt_ids": ["dup-1"],
         "n_excluded": 0, "excluded_ids": [],
         "outcome_categories": {"measured": 3, "solve_failed": 0},
         "front": [{"id": "n1", "design_hash": "c" * 12, "reconstruction_hash": "7" * 64,
                    "category": "measured", "objectives": [7.5, 1.8]}],
         "hypervolume": 141.5},
    ],
    "hypervolume_difference_a_minus_b": -9.5,
    "interpretation": "descriptive navigation comparison only; no statistical win claim, "
                      "and excluded failures contribute cost but never archive/front points",
}

SURROGATE = {
    "tool": "surrogate_validation", "schema_version": 1, "code_version": 2,
    "input_key": "a" * 64,
    "params": {"test_frac": 0.25, "k": 5, "topk": 5, "n_propose": 6,
               "advisory_stored_j": True},
    "advisory_only": True, "changes_defaults": False, "resumed": False,
    "stale_partial_replaced": False,
    "input": {"rows": "scratch/rows.jsonl", "pool": "scratch/pool.jsonl"},
    "status": "ok", "objective_version": 4, "metric_names": ["coverage_error_deg"],
    "validation_mode": "advisory_stored_j", "score_identity": "score-ctx-1",
    "split": {"kind": "chronological", "checks": {"no_future_train_row": True},
              "train_ids": ["r0", "r1"], "test_ids": ["r2"]},
    "evaluation": {
        "n_train": 12, "n_test": 4, "n_ood_fallback": 1, "support_radius": 0.42,
        "feasibility": {"brier": 0.12, "brier_baseline": 0.2,
                        "reliability_bins": [{"bin": [0.0, 0.2], "n": 2,
                                              "mean_pred": 0.1, "observed": 0.0}]},
        "regression": {"status": "ok", "n_eval": 3, "n_ood_fallback": 1, "targets": {
            "j": {"mae": 0.4, "mae_baseline": 0.9, "spearman": 0.8,
                  "interval_95_coverage": 0.67, "topk": 2, "topk_recall": 1.0,
                  "regret": 0.05, "direction": "minimize"},
            "coverage_error_deg": {"mae": 1.2, "mae_baseline": 2.0, "spearman": 0.6,
                                   "interval_95_coverage": 0.67}}},
    },
    "proposals": {"status": "ok", "proposals": [
        {"candidate_id": "near", "role": "exploit", "predicted_j": 1.25,
         "uncertainty": 0.1, "in_support": True, "measured": False, "status": "hypothesis"},
        {"candidate_id": "far", "role": "diversity", "predicted_j": None,
         "uncertainty": None, "in_support": False, "measured": False,
         "status": "hypothesis"}],
        "note": "predictions are hypotheses; validate with the normal evaluator (BEM) later"},
    "complete": True,
}

SURROGATE_REFUSED = {
    "tool": "surrogate_validation", "schema_version": 1, "code_version": 2,
    "input_key": "b" * 64, "status": "refused", "reason": "empty_chronological_split",
    "detail": "all rows share one timestamp", "complete": True, "advisory_only": True,
    "changes_defaults": False,
}

SURROGATE_INSUFFICIENT = {
    **SURROGATE,
    "evaluation": {**SURROGATE["evaluation"],
                   "regression": {"status": "insufficient_data", "n_ood_fallback": 3}},
    "proposals": {"status": "no_pool_or_data", "proposals": []},
}


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")


@pytest.fixture()
def s8_set(tmp_path: Path) -> Path:
    root = tmp_path / "s8"
    root.mkdir()
    for name, payload in (("geometry_descriptors", GEOMETRY),
                          ("hypothesis_cards", HYPOTHESIS),
                          ("qd_compare", QD),
                          ("surrogate_validation", SURROGATE)):
        _write(root / f"{name}.json", payload)
        (root / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")
    return root


def _keyed(root: Path, name: str, payload: dict) -> None:
    _write(root / name, payload)


def test_four_tools_are_registered_and_listed(s8_set: Path):
    for tool in ("geometry_descriptors", "hypothesis_cards", "qd_compare",
                 "surrogate_validation"):
        assert tool in D.ANALYSIS_TOOL_JSONS
    sets = {s["id"]: s for s in D.analysis_sets(s8_set)}
    assert sets["."]["tools"] == ["qd_compare", "geometry_descriptors", "hypothesis_cards",
                                  "surrogate_validation"]
    assert sets["."]["files"] == [
        "geometry_descriptors.json", "hypothesis_cards.json", "qd_compare.json",
        "surrogate_validation.json"]


def test_payloads_pass_through_verbatim_and_reports_are_linkable(s8_set: Path):
    d = D.analysis_report(s8_set, ".")
    assert d["tools"] == ["qd_compare", "geometry_descriptors", "hypothesis_cards",
                          "surrogate_validation"]
    assert d["geometry_descriptors"] == GEOMETRY
    assert d["hypothesis_cards"] == HYPOTHESIS
    assert d["qd_compare"] == QD
    assert d["surrogate_validation"] == SURROGATE
    assert d["tool_files"]["geometry_descriptors"] == [
        "geometry_descriptors.json", "geometry_descriptors.md"]
    assert d["tool_files"]["qd_compare"] == ["qd_compare.json", "qd_compare.md"]
    assert d["extra_tools"] == []                       # registered, not "extra"


def test_api_serves_the_four_payloads(s8_set: Path, tmp_path: Path):
    app = App(tmp_path, tmp_path, analysis_dir=s8_set)
    det = app.get("/api/analysis/.", {})
    assert isinstance(det, dict)
    assert det["qd_compare"] == QD
    assert det["surrogate_validation"] == SURROGATE
    assert det["tool_files"]["hypothesis_cards"] == [
        "hypothesis_cards.json", "hypothesis_cards.md"]


def test_keyed_surrogate_selects_newest_complete_and_lists_candidates(tmp_path: Path):
    root = tmp_path / "keyed"
    root.mkdir()
    _keyed(root, "surrogate_validation-0123456789abcdef.json", SURROGATE)
    newer_refused = {**SURROGATE_REFUSED, "complete": False,
                     "input_key": "c" * 64}
    _keyed(root, "surrogate_validation-fedcba9876543210.json", newer_refused)
    _write(root / "custom_extra.json", {"tool": "custom_extra"})
    d = D.analysis_report(root, ".")
    # A complete payload wins over a newer incomplete one; refusal is disclosed, never hidden.
    assert d["surrogate_validation"] == SURROGATE
    assert [c["name"] for c in d["surrogate_validation_candidates"]] == [
        "surrogate_validation-0123456789abcdef.json",
        "surrogate_validation-fedcba9876543210.json"]
    assert d["surrogate_validation_candidates"][1]["status"] == "refused"
    assert d["extra_tools"] == ["custom_extra"]         # keyed stems are not extra tools
    assert d["tool_files"]["surrogate_validation"] == [
        "surrogate_validation-0123456789abcdef.json"]
    sets = {s["id"]: s for s in D.analysis_sets(root)}
    assert sets["."]["tools"] == ["surrogate_validation"]


def test_fixed_surrogate_file_wins_over_keyed_candidates(tmp_path: Path):
    root = tmp_path / "fixed"
    root.mkdir()
    _write(root / "surrogate_validation.json", SURROGATE_INSUFFICIENT)
    _keyed(root, "surrogate_validation-0123456789abcdef.json", SURROGATE)
    d = D.analysis_report(root, ".")
    assert d["surrogate_validation"] == SURROGATE_INSUFFICIENT
    assert "surrogate_validation_candidates" not in d


def test_malformed_keyed_surrogate_never_raises(tmp_path: Path):
    root = tmp_path / "broken"
    root.mkdir()
    (root / "surrogate_validation-0123456789abcdef.json").write_text("{not json",
                                                                    encoding="utf-8")
    d = D.analysis_report(root, ".")
    assert "surrogate_validation" not in d
    assert d["surrogate_validation_candidates"][0]["readable"] is False
    assert d["extra_tools"] == []


def test_degraded_payloads_are_data_level_only(s8_set: Path):
    root = s8_set
    _write(root / "surrogate_validation.json", SURROGATE_REFUSED)
    d = D.analysis_report(root, ".")
    assert d["surrogate_validation"]["status"] == "refused"
    assert d["surrogate_validation"]["reason"] == "empty_chronological_split"
    # unknown fields ride along untouched
    _write(root / "qd_compare.json", {**QD, "_future": {"x": 1}})
    assert D.analysis_report(root, ".")["qd_compare"]["_future"] == {"x": 1}


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
const {
  analysisGeometrySectionHtml, analysisHypothesisSectionHtml, analysisQdSectionHtml,
  analysisSurrogateSectionHtml, analysisPageHtml,
} = app;
const dir = process.argv[3];
const load = async (name) => JSON.parse(await readFile(join(dir, name + ".json"), "utf8"));
const gd = await load("geometry_descriptors");
const hyp = await load("hypothesis_cards");
const qd = await load("qd_compare");
const sv = await load("surrogate_validation");

// ── geometry: real dimensions, resolver provenance, navigation-only wording ──
const g = analysisGeometrySectionHtml(gd);
assert.ok(g.includes('id="an-geometry-panel"'), g.slice(0, 300));
assert.ok(g.includes("Geometry descriptors"), "panel title");
assert.ok(g.includes("123.4") && g.includes("400.0") && g.includes("250.0"), "real dimensions");
assert.ok(g.includes("140.0"), "mouth/throat ratio");
assert.ok(g.includes(gd.designs[0].provenance.resolver_source_sha256.slice(0, 12)), "resolver sha prefix");
assert.ok(g.includes("not acoustic similarity"), "navigation honesty line");
assert.ok(g.includes("62.0%") && g.includes("21.0%"), "PCA variance in percent");
assert.ok(!g.includes("0.6%"), "variance is not mis-scaled as a fraction");
assert.ok(g.includes("1030"), "k-means seed");
assert.ok(g.includes('id="an-chart-'), "navigation chart registered");
assert.equal(analysisGeometrySectionHtml(null), "");
assert.equal(analysisGeometrySectionHtml({}), "");

// ── hypothesis: six roles, parent provenance, no score columns ──
const h = analysisHypothesisSectionHtml(hyp);
assert.ok(h.includes('id="an-hypothesis-panel"'), h.slice(0, 300));
assert.ok(h.includes("Hypothesis card"), "panel title");
assert.ok(h.includes("parent_a") && h.includes("broad_control"), "all roles");
assert.ok(h.includes("feature-a") && h.includes("feature-b"), "removed features named");
assert.ok(h.includes("unverified_requires_normal_evaluator"), "feasibility label");
assert.ok(h.includes("Hypothesis only"), "evidence disclaimer");
assert.ok(h.includes("500") && h.includes("4000"), "expected band");
assert.ok(!/\bJ decomposition\b|\bscore_terms\b/.test(h), "no score panel");
assert.equal(analysisHypothesisSectionHtml(undefined), "");

// ── QD: equal attempt-equivalent cost, frozen reference, excluded not plotted ──
const q = analysisQdSectionHtml(qd);
assert.ok(q.includes('id="an-qd-panel"'), q.slice(0, 300));
assert.ok(q.includes("Equal-cost QD / Pareto"), "panel title");
assert.ok(q.includes("attempt-equivalent"), "budget wording");
assert.ok(q.includes("not elapsed time"), "budget honesty");
assert.ok(q.includes("coverage_error_deg") && q.includes("ripple_db"), "axes");
assert.ok(q.includes("deg") && q.includes("dB"), "axis units");
assert.ok(q.includes("132.0") && q.includes("141.5"), "hypervolumes");
assert.ok(q.includes("fail-1"), "excluded id disclosed");
assert.ok(q.includes("dup-1"), "duplicate attempt disclosed");
assert.ok(q.includes("not a win claim"), "descriptive wording");
assert.ok(q.includes('id="an-chart-'), "front chart registered");
assert.equal(analysisQdSectionHtml(null), "");

// ── surrogate: split, feasibility, regression, OOD proposals, advisory wording ──
const s = analysisSurrogateSectionHtml(sv);
assert.ok(s.includes('id="an-surrogate-panel"'), s.slice(0, 300));
assert.ok(s.includes("Advisory surrogate validation"), "panel title");
assert.ok(s.includes("advisory_stored_j"), "mode");
assert.ok(s.includes("0.12") && s.includes("0.2"), "Brier and baseline");
assert.ok(s.includes("0.4") && s.includes("0.9"), "J MAE and baseline");
assert.ok(s.includes("1.0") || s.includes("100"), "top-k recall or percent");
assert.ok(s.includes("no prediction (outside training support)"), "OOD null stays null");
assert.ok(s.includes("Advisory only"), "advisory disclaimer");
assert.ok(s.includes("hypothesis"), "proposal status");
const refused = analysisSurrogateSectionHtml(JSON.parse(await readFile(join(dir, "refused.json"), "utf8")));
assert.ok(refused.includes("empty_chronological_split"), "refusal reason verbatim");
assert.ok(!refused.includes("Brier"), "no metric cards for a refusal");
assert.equal(analysisSurrogateSectionHtml(null), "");

// ── the page composes every panel through the real section list ──
const page = analysisPageHtml({
  id: ".", sections: [], extra_tools: [],
  geometry_descriptors: gd, hypothesis_cards: hyp, qd_compare: qd, surrogate_validation: sv,
  tool_files: {geometry_descriptors: ["geometry_descriptors.md"]},
});
assert.ok(page.includes("an-geometry-panel") && page.includes("an-hypothesis-panel")
  && page.includes("an-qd-panel") && page.includes("an-surrogate-panel"), "all four panels");
assert.ok(page.includes("geometry_descriptors.md"), "registered tool file link");
console.log("S8 GUARD OK");
'''


def test_s8_renderers_execute_under_node(s8_set: Path, tmp_path: Path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    _write(s8_set / "refused.json", SURROGATE_REFUSED)
    script = tmp_path / "guard_s8_under_test.mjs"
    script.write_text(_GUARD_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(APPJS), str(s8_set)],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert "S8 GUARD OK" in r.stdout, (
        f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}")


def test_app_js_parses_as_an_es_module(tmp_path: Path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    mjs = tmp_path / "app.mjs"
    mjs.write_text(APPJS.read_text(encoding="utf-8"), encoding="utf-8")
    r = subprocess.run([node, "--check", str(mjs)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
