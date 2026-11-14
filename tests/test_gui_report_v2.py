"""Analysis report v2 (2026-11-14) + shared data-viz kit, executed for real under node.

The page is decision-first: rule-built next-solve actions from stored evidence, a per-run
scoreboard grouped by objective version, then evidence sections. These tests build a small
synthetic nested payload (no run data on disk) and check that each rule fires only from its
evidence, that J is grouped by objective version, and that nothing renders "undefined"/"NaN".
The shared kit in charts.js (catColor, fmtSmart, logNiceLimits, fmtLogTick, sparkline,
stackBarHtml) is checked directly.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "hornlab_search" / "gui" / "static"
APPJS = STATIC / "app.js"
CHARTSJS = STATIC / "charts.js"

_SCRIPT = r'''
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";

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

const charts = await import(pathToFileURL(process.argv[3]).href);
const app = await import(pathToFileURL(process.argv[2]).href);

// ── shared kit ──
const { catColor, CAT_N, CAT_LIGHT, fmtSmart, logNiceLimits, fmtLogTick, sparkline, stackBarHtml } = charts;
assert.equal(CAT_N, 8);
for (let i = 0; i < 8; i++) assert.equal(catColor(i), CAT_LIGHT[i], "no-CSS fallback is the light step");
assert.notEqual(catColor(8), catColor(0), "slot 9 must not cycle back to slot 1");
assert.equal(catColor(8), catColor(42), "everything past 8 folds to one neutral 'other'");
assert.equal(new Set(CAT_LIGHT).size, 8);
assert.equal(fmtSmart(600), "600"); assert.equal(fmtSmart(12.345), "12.3");
assert.equal(fmtSmart(2.1283), "2.13"); assert.equal(fmtSmart(0.68653), "0.687"); assert.equal(fmtSmart(null), "–");
assert.deepEqual(logNiceLimits(0.6, 1.84), [0.5, 2]);
assert.deepEqual(logNiceLimits(2.13, 8.47), [2, 10]);
assert.equal(fmtLogTick(0.5), "0.5"); assert.equal(fmtLogTick(20), "20"); assert.equal(fmtLogTick(2000), "2k");
const sp = sparkline([[1, 10], [2, 5], [3, 2]], { log: true });
assert.ok(sp.startsWith("<svg") && sp.includes("<path") && !sp.includes("NaN"));
assert.equal(sparkline([[1, 1]]), "", "one point is not a line");
const sb = stackBarHtml([{ value: 3, cls: "cat-1", label: "a 75%" }, { value: 1, cls: "cat-2", label: "b" }]);
assert.ok(sb.includes("width:75.00%") && sb.includes("width:25.00%") && sb.includes("a 75%"));
const thin = stackBarHtml([{ value: 95, label: "big" }, { value: 5, label: "tiny" }]);
assert.ok(thin.includes("big") && !thin.includes("tiny"), "labels hide in segments narrower than minLabelPct");
assert.equal(stackBarHtml([]), "");

// ── isobars: classic rainbow bands kept, shared legend, globe exported ──
const { ISOBAR_COLORS, OVER_RANGE_COLOR, OVER_MIN, isobarLegendHtml, globePlot, isobarMap } = charts;
assert.equal(ISOBAR_COLORS.length, 10, "ten 3 dB bands, -30..0");
assert.equal(ISOBAR_COLORS[9], "#8F0000", "loud end stays the classic dark red");
assert.equal(OVER_MIN, 1, "only lobes > +1 dB are flagged; sub-dB excess is an on-axis dip");
assert.ok(OVER_RANGE_COLOR);
assert.equal(typeof globePlot, "function"); assert.equal(typeof isobarMap, "function");
const leg = isobarLegendHtml({ target: true, f0: true, over: false });
assert.ok(leg.includes("−6 dB beamwidth edge") && leg.includes("coverage target") && leg.includes("f0 scoring floor"));
assert.ok(!leg.includes("off-axis lobe"), "lobe key only when a lobe exists");
assert.equal((leg.match(/<i style="background:/g) || []).length, 10, "one swatch per band");

// ── page ──
const run = (id) => `runs\\${id}`;
const curve = (n, seed, best) => Array.from({ length: n }, (_, i) => ({ n: i + 1,
  best: i < n / 4 ? seed - (seed - best) * (i / (n / 4)) : best, wall_s: (i + 1) * 30 }));
const conv = (rid, brief, ver, still, rows, refusals) => ({ run_dir: run(rid), brief, family: "OSSE",
  objective_version: ver, n_rows: rows, n_valid: 100, n_new_valid: 100, n_cached: 0,
  refusals, final_best: 2, curve: curve(100, 8, 2), evals_to_1pct: still ? 95 : 25,
  last20_improvement: still, last20_improvement_pct: still ? 6.5 : 0.1 });
const d = {
  id: "day_2026-11-12", generated_utc: "2026-11-12T23:30:10Z",
  sections: [
    { id: "convergence_g1", tool: "convergence", data: conv("A-screen-1", "brief_a", 4, true, 200, { invalid_geometry: 90, mesh_too_large: 10 }) },
    { id: "convergence_g8", tool: "convergence", data: conv("B-screen-2", "brief_b", 7, false, 110, { invalid_geometry: 10 }) },
    { id: "walls_g6", tool: "walls", data: { run_dir: run("C-screen-3"), family: "FREEFORM", top_decile_n: 15,
      walls: [{ key: "g_fc_hz", lo: 600, hi: 1200, frac_lo: 0.87, frac_hi: 0, wall_lo: true, wall_hi: false },
              { key: "g_T", lo: 0.3, hi: 1, frac_lo: 0, frac_hi: 0, wall_lo: false, wall_hi: false },
              { key: "quiet", lo: 0, hi: 1, frac_lo: 0, frac_hi: 0, wall_lo: false, wall_hi: false }],
      proposal: [{ key: "g_fc_hz", action: "widen_lo", new_lo: 540, new_hi: 1200, reason: "87% at lo" },
                 { key: "g_T", action: "narrow", new_lo: 0.68, new_hi: 0.78, reason: "top-decile span padded 5%" }] } },
    { id: "term_balance_g6", tool: "term_balance", data: { run_dir: run("C-screen-3"), brief: "brief_c", family: "FREEFORM",
      objective_version: 6, n_valid: 142, shares: { di_rise: { median: 0.76, mean: 0.75 }, rip: { median: 0.04, mean: 0.05 } },
      top_decile_raw: { di_rise: { median: 11.7, p10: 9, p90: 14 }, rip: { median: 0.01, p10: 0, p90: 0.02 } },
      weights: { di_rise: 0.4, rip: 0.8 }, tolerances: { di_rise: 4, rip: 2 } } },
    { id: "sensitivity_g6", tool: "sensitivity", data: { run_dir: run("C-screen-3"), family: "FREEFORM", objective_version: 6,
      n_valid: 142, spearman: [{ key: "g_fc_hz", rho: 0.35, rho_abs: 0.35, n: 142 }, { key: "g_T", rho: 0.01, rho_abs: 0.01, n: 142 }],
      top_decile_shift: [{ key: "g_fc_hz", mean_all: 634, mean_top: 615, shift_norm: -0.03 }],
      surrogate: { available: true, model: "RandomForestRegressor", r2: 0.97, n_train: 113, n_test: 29,
        importance: [{ key: "g_fc_hz", permutation_importance: 1.69, std: 0.08 }, { key: "g_T", permutation_importance: 0.05, std: 0.01 }] } } },
    { id: "fidelity_g1", tool: "fidelity", data: { run_dir: run("A-screen-1"), brief: "brief_a", family: "OSSE", objective_version: 4,
      n_screen: 100, n_verify: 3, n_pairs: 3, bias_median_pct: 29.2, spearman_all: 0.66, spearman_top5: 0.5,
      pairs: [{ design_hash: "h1", j_screen: 2.4, j_verify: 3.2, bias_pct: 33 }, { design_hash: "h2", j_screen: 2.6, j_verify: 3.1, bias_pct: 19 },
              { design_hash: "h3", j_screen: 2.9, j_verify: 2.95, bias_pct: 2 }] } },
  ],
  errors: [{ id: "v6_seeds", tool: "seed_variance", status: "error",
    error: "ValueError: group 'v6_seeds' is not one task/scoring identity: ['task_config_hash_mismatch']" }],
};
const html = app.analysisPageHtml(d);
assert.ok(!/undefined|NaN/.test(html), "no undefined/NaN: " + (html.match(/.{60}(undefined|NaN).{60}/) || [""])[0]);
assert.ok(html.includes("Day report · 12 Nov 2026"), "dated title");
assert.ok(html.includes("What to change before the next run"), "actions section");
assert.ok(html.includes("Widen <span class=\"mono\">g_fc_hz</span> lower limit"), "widen action from the wall");
assert.ok(html.includes("Give <b class=\"mono\">brief_a · OSSE</b> more evaluations"), "budget action from still-improving run");
assert.ok(html.includes("settled early"), "slack action from the early-settled run");
assert.ok(html.includes("Stop spending 50% of"), "refusal action: 100 of 200 refused");
assert.ok(!html.includes("Stop spending 9% of"), "9% refusals stay below the 25% bar");
assert.ok(html.includes("Narrow 1 FREEFORM knob"), "narrow action");
assert.ok(html.includes("Verify more than the screen"), "fidelity action");
assert.ok(html.includes("29.2% higher (worse)"), "bias direction: verify J above screen J is worse");
assert.ok(html.includes("is what holds") && html.includes("2.9× its tolerance"), "objective bottleneck");
assert.ok(!/rip<\/span> is what holds/.test(html), "a small, in-tolerance term is not a bottleneck");
assert.ok(html.includes("drives J in"), "dominant driver insight");
assert.ok(html.includes("Seed repeatability is still unknown"), "error becomes a knowledge gap");
assert.ok(html.includes("task_config_hash_mismatch"), "error message verbatim");
assert.ok(html.indexOf("Objective J v7") < html.indexOf("Objective J v4"), "scoreboard grouped by version, newest first");
assert.ok(html.includes("compare J only inside this group"), "no cross-version J comparison");
assert.ok(html.includes("No change suggested for 1 knob: quiet"), "quiet knobs collapsed");
assert.ok(html.includes("an-bx-wall"), "wall marker drawn");
assert.ok(html.includes('class="stackbar an-bud"'), "budget bar uses the shared stacked bar");
assert.ok(html.includes("cat-1") && html.includes("cat-2"), "term colours come from the shared palette");
assert.ok(html.includes('id="an-s-tech"'), "technical appendix kept");
// follow-through: budget/verify actions open the run; bounds open Quick launch with the brief, honestly
assert.ok(html.includes('href="#/run/A-screen-1">Open the run to continue it'), "still-improving -> run page");
assert.ok(html.includes('href="#/launch?brief=brief_c&amp;tier=screen"') || html.includes('href="#/launch?brief=brief_c&tier=screen"'), "bounds -> prefilled launch");
assert.ok(html.includes("launch does not change them"), "bounds link does not claim the edit is applied");
// degrade: no sections, no errors → no actions block, no crash
const empty = app.analysisPageHtml({ id: "x" });
assert.ok(!/undefined|NaN/.test(empty) && !empty.includes("What to change"));
console.log("REPORT V2 OK");
'''


def test_report_v2_and_shared_kit_execute_under_node(tmp_path: Path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "guard.mjs"
    script.write_text(_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(APPJS), str(CHARTSJS)], capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    assert "REPORT V2 OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"
