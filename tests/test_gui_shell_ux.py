"""WP5 + WP4 (GUI plan 2026-11-12): sidebar lane lines, runs-list mode/parent/activity, Compare filter, Home leaders window.

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
const { laneChipsHtml, runModeMatches, runModeBadgesHtml, runParentLineHtml, compareOptionsHtml, homeLeadersFilter, runIsLive, sortRunsForTable } = app;

// lane lines: both lanes always listed, busy marker, empty payload renders nothing
assert.equal(laneChipsHtml(null), "");
const lanes = { lanes: [
  { lane: "gpu", lock: { alive: true }, job: { name: "g2_core_law" }, run: { n: 996 } },
  { lane: "cpu", lock: null, job: null, last_job: { id: "c2b_verify" } } ] };
const lc = laneChipsHtml(lanes);
assert.ok(lc.includes("● GPU · g2_core_law · 996 evals"), lc);
assert.ok(lc.includes("○ CPU · idle · last c2b_verify"), lc);

// run mode filter + badges + parent line
const scr = { id: "a", mode: "screen", has_inline_verify: true }, ver = { id: "b", mode: "verify", verify_of_run_id: "a" },
      sol = { id: "c", mode: "verify" };
assert.ok(runModeMatches(scr, "screen") && !runModeMatches(scr, "verify") && runModeMatches(scr, "has_verify"));
assert.ok(runModeMatches(ver, "verify") && !runModeMatches(ver, "screen"));
assert.ok(runModeBadgesHtml(scr, false).includes("verified designs"));
assert.ok(runModeBadgesHtml(ver, true).includes("running") && runModeBadgesHtml(ver, true).includes("verify"));
assert.ok(runParentLineHtml(ver).includes("#/run/a"));
assert.ok(runParentLineHtml(sol).includes("single-design verification"));
assert.equal(runParentLineHtml(scr), "");

// live = recent row only; missing `last` is not live
assert.equal(runIsLive({}), false);
assert.equal(runIsLive({ last: new Date().toISOString() }), true);
// activity sort: newest row first even when the run id is older
const srt = sortRunsForTable([{ name: "old-id-live", started: "2026-10-30", last: "2026-11-12T20:00:00Z", objective_version: 7 },
                              { name: "new-id-idle", started: "2026-11-11", last: "2026-11-11T01:00:00Z", objective_version: 7 }], "activity");
assert.equal(srt[0].name, "old-id-live");

// compare options: text filter, brief restriction, selected run kept
const runs = [{ id: "r1", name: "osse_a", brief: "b1", best_j: 1 }, { id: "r2", name: "rosse_b", brief: "b2", best_j: 2 }];
assert.ok(compareOptionsHtml(runs, "rosse", "").includes("r2") && !compareOptionsHtml(runs, "rosse", "").includes('value="r1"'));
assert.ok(!compareOptionsHtml(runs, "", "b1").includes('value="r2"'));
assert.ok(compareOptionsHtml(runs, "zzz", "", "r1").includes('value="r1"'));

// home leaders: 30-day window, missing timestamps never hidden, show-all
const now = Date.parse("2026-11-12T00:00:00Z");
const L = [{ brief: "new", last_activity: "2026-11-10T00:00:00Z" }, { brief: "old", last_activity: "2026-09-01T00:00:00Z" }, { brief: "none" }];
let f = homeLeadersFilter(L, false, now);
assert.deepEqual(f.shown.map(x => x.brief), ["new", "none"]); assert.equal(f.hidden, 1);
f = homeLeadersFilter(L, true, now); assert.equal(f.shown.length, 3);
console.log("WP5 OK");
'''


def test_shell_helpers(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    js = tmp_path / "t.mjs"
    js.write_text(_JS, encoding="utf-8")
    r = subprocess.run([node, str(js), str(APPJS)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "WP5 OK" in r.stdout
