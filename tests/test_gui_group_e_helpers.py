"""Group E view pure-helper guards, executed for real through node (test_gui_views_l2.py style).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"

_GUARD_SCRIPT = r'''
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
globalThis.location = { hash: "#/elites" };
globalThis.requestAnimationFrame = () => 0;
globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
globalThis.fetch = () => Promise.reject(new Error("offline shim"));

const app = await import(pathToFileURL(process.argv[2]).href);
const { lanesPanelHtml, verdictChipHtml, eliteGateChips } = app;

// E.2 lanes panel: pure over /api/lanes, empty/absent payload renders nothing
assert.equal(lanesPanelHtml(null), "");
assert.equal(lanesPanelHtml({}), "");
const ok = lanesPanelHtml({ alert: false, lanes: [{
  lane: "gpu", lock: { pid: 1, alive: true },
  job: { name: "g1_running", started: "2026-11-11T09:00:06" },
  run: { id: "20261111T000000Z-screen-aaaaaa", n_rows: 12, best_j: 4.5, newest_row_age_min: 2.0 },
  alert: null, last_job: null }] });
assert.ok(ok.includes("GPU") && ok.includes("g1_running"), ok);
assert.ok(ok.includes("#/run/20261111T000000Z-screen-aaaaaa"), ok);
assert.ok(ok.includes("pill good"), "a fresh row lane is ok");
const alert = lanesPanelHtml({ alert: true, alert_lanes: ["gpu"], lanes: [{
  lane: "gpu", lock: null, job: { name: "g1_running" }, run: { n_rows: 12, newest_row_age_min: 34.1 },
  alert: { job: "g1_running", age_min: 34.1, reason: "newest row 34.1 min old while job g1_running is running" } }] });
assert.ok(alert.includes("alert error") && alert.includes("ALERT") && alert.includes("34.1 min"), alert);

// verdict chips per the seed-variance schema
assert.equal(verdictChipHtml("a-beats-b"), '<span class="pill good">A beats B</span>');
assert.equal(verdictChipHtml("b-beats-a"), '<span class="pill good">B beats A</span>');
assert.ok(verdictChipHtml("indicative").includes("indicative") && verdictChipHtml("indicative").includes("&lt; 5 seeds"));
assert.ok(verdictChipHtml(null).includes("muted"));
assert.ok(verdictChipHtml("no-verdict").includes("no-verdict"));

// elite gate chips: pass/fail strictly from the audit columns
const chips = eliteGateChips({ gates: { throat: true, load: false } },
                             { throat: "round throat", load: "loading" });
assert.ok(chips.includes("round throat") && chips.includes('pill good'), chips);
assert.ok(chips.includes("loading fail") && chips.includes('pill bad'), chips);
assert.equal(eliteGateChips({ gates: {} }, {}), "");

console.log("E GUARD OK");
'''


def test_group_e_view_helpers_guard(tmp_path: Path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "guard_under_test.mjs"
    script.write_text(_GUARD_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(APPJS)],
                       capture_output=True, text=True, cwd=str(tmp_path))
    assert "E GUARD OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"
