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
const { budgetKpi, gateAuditSplit, gateAuditHtml } = app;

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
