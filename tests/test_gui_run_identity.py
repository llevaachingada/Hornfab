"""WP4 (GUI plan 2026-11-12), first slice: resume-aware budget KPI and gate-audit folding.

Executed for real through node (pattern: tests/test_gui_views_l2.py); skipped without node.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"

_JS = r'''
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
globalThis.location = { hash: "#/glossary" };
globalThis.requestAnimationFrame = () => 0;
globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
globalThis.fetch = () => Promise.reject(new Error("offline shim"));
const app = await import(pathToFileURL(process.argv[2]).href);
const { budgetKpi, gateAuditSplit, gateAuditHtml, convergenceCounts, stddevBars, fitSvgLabel } = app;

// resumed run: --budget is the resume increment, never "over budget"
let b = budgetKpi(996, 117, "hornlab-search search --resume runs/x --budget 117 --mode screen");
assert.equal(b.text, "996 evals total · this resume +117"); assert.equal(b.cls, "");
// fresh run over budget keeps the warning
b = budgetKpi(201, 100, "hornlab-search search --config a.yaml --budget 100");
assert.ok(b.text.includes("over budget")); assert.equal(b.cls, "bad");
b = budgetKpi(95, 100, ""); assert.equal(b.cls, "warn");
b = budgetKpi(5, null, ""); assert.equal(b.text, "5");

// gate audit: 10 best + every verify row up front, the rest folded
const entries = Array.from({ length: 30 }, (_, i) => [`h${String(i).padStart(2, "0")}`, { J: i, tier: i === 25 ? "verify" : "screen", gates: {} }]);
const { lead, rest } = gateAuditSplit(entries);
assert.equal(lead.length, 11); assert.equal(rest.length, 19);
assert.ok(lead.some(e => e[0] === "h25"));
const html = gateAuditHtml({ available: true, source: "s.csv", gates: ["throat"], labels: {},
  designs: Object.fromEntries(entries.map(([h, e]) => [h, { ...e, gates: { throat: true } }])) });
assert.ok(html.includes("Show all 30 audited designs (19 more)"), html);
assert.ok(html.includes("Audit tier"));
// short audits do not fold
const small = gateAuditHtml({ available: true, source: "s.csv", gates: ["throat"], labels: {},
  designs: { a: { J: 1, tier: "screen", gates: { throat: true } } } });
assert.ok(!small.includes("<details"));

// D5 (2026-11-12 audit): data.py writes null for a failed row, so the convergence footer must
// count nulls as failures over the FULL (resumed) history, matching the KPI strip.
const cc = convergenceCounts([5.0, null, 1000.0, 3.0, null]);
assert.equal(cc.ok.length, 2, "two scored evals");
assert.equal(cc.failed.length, 3, "null rows and >=999 rows are failures");
assert.deepEqual(cc.ok.map(p => p[1]), [5.0, 3.0]);
// 139 ok + 62 failed of 201 is exactly the ed1da9 history.
const ed = convergenceCounts([...Array(139).fill(4), ...Array(62).fill(null)]);
assert.equal(ed.ok.length, 139);
assert.equal(ed.failed.length, 62);

// D1: every parameter gets a row; a null column stays scored as "no data" for that parameter
// only (it must not shift the values of the parameters after it).
const names = ["a_deg", "L_mm", "gcurve_dist", "morph_fixed"];
const sens = [
  { key: "a_deg", lo: 10, hi: 80 }, { key: "L_mm", lo: 56, hi: 400 },
  { key: "gcurve_dist", lo: 0.2, hi: 1.0 }, { key: "morph_fixed", lo: 0, hi: 0.6 },
];
const bars = stddevBars([[0.7, 0.4, null, 0.3], [0.35, null, 0.2, 0.15]], names, sens);
assert.equal(bars.length, 4);
assert.equal(bars.find(b => b.key === "a_deg").final, 0.35 / 70);
assert.equal(bars.find(b => b.key === "gcurve_dist").final, 0.2 / 0.8);
assert.equal(bars.find(b => b.key === "morph_fixed").final, 0.15 / 0.6);
assert.ok(bars.find(b => b.key === "L_mm").final != null, "L_mm data is present in gen 1");
// a truly empty parameter is surfaced, not silently blank
const empty = stddevBars([[0.5, null]], ["a_deg", "L_mm"], sens);
assert.equal(empty.find(b => b.key === "L_mm").final, null);
assert.equal(empty.find(b => b.key === "L_mm").n, 0);
// label fitting keeps long parameter names inside the reserved margin
assert.equal(fitSvgLabel("morph_allow_shrinkage", 90), "morph_allow_sh…");
assert.equal(fitSvgLabel("a_deg", 90), "a_deg");
console.log("WP4 OK");
'''


def test_budget_and_gate_fold(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    js = tmp_path / "t.mjs"
    js.write_text(_JS, encoding="utf-8")
    r = subprocess.run([node, str(js), str(APPJS)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "WP4 OK" in r.stdout
