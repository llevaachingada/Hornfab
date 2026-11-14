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
const { laneChipsHtml, runModeMatches, runModeBadgesHtml, runParentLineHtml, compareOptionsHtml, homeLeadersFilter, runIsLive, sortRunsForTable, runIsVerify } = app;

// lane lines: both lanes always listed, busy marker, empty payload renders nothing
assert.equal(laneChipsHtml(null), "");
const lanes = { lanes: [
  { lane: "gpu", lock: { alive: true }, job: { name: "g2_core_law" }, run: { n_rows: 996 } },
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

// home leaders: 31-day window (owner decision 2026-11-12; was 14), missing timestamps never hidden, show-all
const now = Date.parse("2026-11-12T00:00:00Z");
const L = [{ brief: "new", last_activity: "2026-11-10T00:00:00Z" }, { brief: "old", last_activity: "2026-09-01T00:00:00Z" }, { brief: "none" }];
let f = homeLeadersFilter(L, false, now);
assert.deepEqual(f.shown.map(x => x.brief), ["new", "none"]); assert.equal(f.hidden, 1);
f = homeLeadersFilter(L, true, now); assert.equal(f.shown.length, 3);
// exact boundary: 30 days old shown, 32 days old hidden
const dayMs = 86400000;
const L31 = [{ brief: "d30", last_activity: new Date(now - 30 * dayMs).toISOString() },
             { brief: "d32", last_activity: new Date(now - 32 * dayMs).toISOString() }];
const f31 = homeLeadersFilter(L31, false, now);
assert.deepEqual(f31.shown.map(x => x.brief), ["d30"]); assert.equal(f31.hidden, 1);

// verify-run detection (WP4 item 5): summary mode wins, d.mode is the fallback, search never hidden
assert.equal(runIsVerify({ mode: "verify" }, {}), true);
assert.equal(runIsVerify({}, { mode: "verify" }), true);
assert.equal(runIsVerify({ mode: "screen" }, { mode: "verify" }), false);
assert.equal(runIsVerify({ mode: "screen" }, {}), false);
assert.equal(runIsVerify({}, null), false);
assert.equal(runIsVerify(null, null), false);
// verification card states
const { verificationCardHtml } = app;
assert.equal(verificationCardHtml(null, "r"), "");
assert.ok(verificationCardHtml({ kind: "none", summary: {} }, "R1").includes('verify --run &quot;runs/R1&quot; --top 5'));
assert.ok(verificationCardHtml({ kind: "redirect", redirect_to: null }, "R2").includes("not in this runs folder"));
assert.ok(verificationCardHtml({ kind: "redirect", redirect_to: "P" }, "R2").includes("#/run/P/verify"));
assert.ok(verificationCardHtml({ kind: "standalone", summary: { best_verify_j: 3 } }, "R3").includes("Single-design verification"));
const ok = verificationCardHtml({ kind: "pairs", comparable: true, summary: { n_verified: 5, best_verify_j: 4.62, best_verify_hash: "608eef092639", screen1_verify_rank: 2, bias_median_pct: 19.1 } }, "R4");
assert.ok(ok.includes("5 designs verified") && ok.includes("screen #1 is verify #2") && ok.includes("19.1% optimistic") && ok.includes("#/run/R4/verify"), ok);
const nc = verificationCardHtml({ kind: "pairs", comparable: false, comparable_reason: "different bands", summary: { n_verified: 3 } }, "R5");
assert.ok(nc.includes("no ranking across them"), nc);
console.log("WP5 OK");
'''


def test_shell_helpers(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    js = tmp_path / "t.mjs"
    js.write_text(_JS, encoding="utf-8")
    r = subprocess.run([node, str(js), str(APPJS)], capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "WP5 OK" in r.stdout


def test_verify_runs_omit_search_history_panels():
    """WP4 item 5: viewRunDetail detects a verify run once and omits every search-history panel
    (actions, Continue run, Change/Budget KPIs, Convergence, score breakdown, CMA dynamics,
    CMA covariance, Pin plan). The Verification card and the gate audit stay outside the gate."""
    src = APPJS.read_text(encoding="utf-8")
    assert "const isVerify = runIsVerify(sum, d);" in src
    # Evolution / Design cloud / QD atlas are one gated actions block
    assert '${isVerify ? "" : `<a class="run-tab-link" href="#/run/${esc(id)}/evolution">' in src
    assert '${isVerify ? "" : continueRunCardHtml(d, sum)}' in src
    # Convergence + score breakdown + H5 search dynamics
    assert '${isVerify ? "" : `<!-- Search history -->' in src
    assert '<!-- Search history -->' in src and 'id="cma-dynamics-block"' in src
    # CMA covariance + Pin plan
    assert '${isVerify ? "" : `<!-- CMA covariance' in src
    assert 'id="pin-plan-wrap"' in src and "Pin plan" in src
    # KPI strip omits Change vs start / Budget used for verify runs
    assert "...(isVerify ? [] : [" in src
    assert '["Change vs start", ch,' in src     # emphasised as a key KPI since 2026-11-14
    # not gated: the Verification card fetch and the gate audit
    assert 'api(`/api/verify/${encodeURIComponent(id)}`)' in src
    assert "${gateAuditHtml(d.gate_audit)}" in src
