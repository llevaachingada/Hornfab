from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "hornlab_search/gui/static"


def test_study_chart_helpers_and_compare_board_render(tmp_path):
    script = tmp_path / "bo_module_test.mjs"
    script.write_text(r'''
import assert from "node:assert/strict";
import {pathToFileURL} from "node:url";
const charts = await import(pathToFileURL(process.argv[2]).href);
const compare = await import(pathToFileURL(process.argv[3]).href);

const convergence = {
  status: "partial",
  incumbent: {j: 3.2},
  arms: [
    {id: "bo", label: "BO", method: "bo", color_slot: 0,
     points: [[0, 4.0], [1, 3.5], [2, 3.2]], solves: [[0, 4.0], [1, 3.5], [2, 3.2]],
     refusals: [], exploration_points: [[1, 3.5]], verify_points: [[4, 3.0]]},
    {id: "cma", label: "CMA", method: "cma", color_slot: 1,
     points: [[0, 4.2], [1, 3.8]], solves: [[0, 4.2], [1, 3.8]], refusals: [3]},
  ],
};
const limits = charts.convergenceLimits(convergence);
assert.ok(limits && limits.xlim[0] === 0 && limits.xlim[1] >= 4);
assert.ok(limits.ylim[0] <= 3.2 && limits.ylim[1] >= 4.2);
assert.equal(charts.designLink("study-f269f257b24e00f2", "d15ace0dca72"),
  "#/run/study-f269f257b24e00f2/balloon?design=d15ace0dca72");
assert.equal(charts.designLink("javascript:alert", "d15ace0dca72"), null);
assert.equal(charts.designLink("study-f269f257b24e00f2", "../x"), null);
assert.equal(charts.formatSeconds(95), "2 min");
assert.deepEqual(charts.trustRegionPoints({length_series: [[0, 0.8], [1, 0.4]]}), [[0, 0.8], [1, 0.4]]);
assert.ok(charts.paretoLimits({points: [{coverage_deg: 1.2, ripple_db: 0.4}], reference: {limits: [2, 1]}}));

const board = compare.renderMethodBoard({
  name: "BO vs CMA", objective_version: 7, target_j: 3.2,
  methods: {bo: {n: 3, n_verified: 3, median_verify_j: 3.1, seed_spread: 0.2, median_screens_to_target: 5},
            cma: {n: 3, n_verified: 3, median_verify_j: 3.4, seed_spread: 0.1, median_screens_to_target: 12}},
  arms: [{id: "bo_s31001", method: "bo", screens: 60, verify: 6, best_screen_j: 3.1,
          best_verify_j: 3.05, screens_to_target: 5, complete: true}],
  comparisons: [{id: "bo-vs-cma", rule: "verify_median_gap_exceeds_spread", status: "ready",
                 verdict: "bo", gap: 0.3, spread: 0.2, reason: "gap exceeds the larger seed spread"}],
  notes: ["Screen J does not decide."],
});
assert.ok(board.includes("BO vs CMA") && board.includes("bo wins") && board.includes("bo_s31001"));
assert.ok(board.includes("Screen J does not decide"));
const escaped = compare.renderMethodBoard({name: "<script>x</script>", methods: {}, arms: [], comparisons: []});
assert.ok(escaped.includes("&lt;script&gt;") && !escaped.includes("<script>"));
assert.ok(compare.renderComparisonList([{name: "a", label: "A"}], "a").includes('value="a"'));
console.log("bo module ok");
''', encoding="utf-8")
    result = subprocess.run(
        ["node", str(script), str(STATIC / "study_charts.js"), str(STATIC / "compare_methods.js")],
        capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "bo module ok" in result.stdout


def test_studies_js_renders_bo_panels_without_imports(tmp_path):
    script = tmp_path / "bo_panel_test.mjs"
    script.write_text(r'''
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const src = await readFile(process.argv[2], "utf8");
const m = await import("data:text/javascript;base64," + Buffer.from(src).toString("base64"));
const study = {id: "study1", revision: 1, name: "BO study", root: "c9d390ce"};
const base = {phase: "execute", status: "partial", revision: 1, provenance: {}, reasons: []};
const panel = {...base, data: {bo: {
  phase: "execute",
  run: {status: "ready", run_id: "study-f269f257b24e00f2", budget: {screen_calls: 60, verify_calls: 6, total_calls: 66},
        budget_profile: "comparison-60", lane: "gpu"},
  convergence: {status: "partial", objective_version: 7,
    arms: [{id: "bo", label: "BO", method: "bo", screens: 60, best_j: 3.1, best_verify_j: 3.05,
            screens_to_target: 5, points: [[0, 3.1]], solves: [], refusals: [], exploration_points: [], verify_points: []}],
    eta: {screen_seconds: 100, verify_seconds: 600}},
  trust_region: {status: "ready", length_series: [[0, 0.8], [1, 0.4]], success_counter: 1, failure_counter: 0,
                 terminal: {collapsed: false}, box: {lo: [0, 0.1], hi: [0.4, 0.5]}, active_keys: ["L_mm", "a_deg"]},
  pareto: {status: "not_applicable", reason: "scalar"},
}}};
const html = m.renderStudyPanel(study, panel);
for (const text of ["Run budget", "Convergence", "Best J", "Trust region", "study-chart"]) assert.ok(html.includes(text));
const explain = m.renderStudyPanel(study, {...base, phase: "explain", data: {bo: {
  phase: "explain", calibration: {status: "partial", n: 1, points: [], interval_label: "model credible interval",
    reason: "Only 1 predicted screen is recorded"},
  sensitivity: {status: "ready", knobs: [{key: "L_mm", lengthscale: 0.2, importance: 0.8}], engine: {engine: "botorch"}},
  design_space: {status: "ready", points: [], explained: [0.3, 0.2], active_keys: []},
}}});
for (const text of ["Predicted vs measured", "How strongly J reacts", "Design-space map", "L_mm"]) assert.ok(explain.includes(text));
const data = m.renderStudyPanel(study, {...base, phase: "data", data: {bo: {
  phase: "data", data_summary: {status: "ready", objective_version: 7,
    training: {n: 185, n_min: 16, active_keys: ["L_mm"], sources: {scores_json: "scores.json"}}}}}});
for (const text of ["Training data", "objective v7", "scores.json"]) assert.ok(data.includes(text));
const link = m.studyDesignLink("study-f269f257b24e00f2", "d15ace0dca72", "study1", "execute", "c9d390ce");
assert.ok(link.startsWith("#/run/study-f269f257b24e00f2/balloon?") && link.includes("design=d15ace0dca72") && link.includes("root=c9d390ce"));
assert.ok(m.renderStudyList([{id: "study1", root: "c9d390ce", root_label: "runs/night/arm"}]).includes("root=c9d390ce"));
console.log("bo panels ok");
''', encoding="utf-8")
    result = subprocess.run(["node", str(script), str(STATIC / "studies.js")],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "bo panels ok" in result.stdout
