"""WP6 tests: panel pure helpers in verify.js, plus node --check.

Executed through node --input-type=module (offline, no server, no GPU).
Tests cover: bandDeltaStats, nearestFreqIndex, checklistHtml,
compare query parse (via parseVerifyQuery), and JS syntax.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFY_JS = ROOT / "hornlab_search" / "gui" / "static" / "verify.js"
BALLOON_JS = ROOT / "hornlab_search" / "gui" / "static" / "balloon.js"


# ── Shared DOM/global stub ────────────────────────────────────────────────────

_DOM_STUB = r"""
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";

const fakeEl = () => ({
  className: "", id: "", style: {}, dataset: {}, innerHTML: "", textContent: "",
  setAttribute() {}, getAttribute: () => null, replaceWith() {}, appendChild() {},
  addEventListener() {}, removeEventListener() {}, closest: () => null,
  classList: { toggle() {}, add() {}, remove() {} },
  querySelector: () => null, querySelectorAll: () => [],
  isConnected: false, children: [],
});

globalThis.document = {
  getElementById: () => fakeEl(), createElement: () => fakeEl(),
  createElementNS: () => fakeEl(),
  querySelector: () => null, querySelectorAll: () => [], addEventListener() {},
  documentElement: {
    hasAttribute: () => true, setAttribute() {}, getAttribute: () => null,
    style: {}, getPropertyValue: () => "",
  },
  body: { appendChild() {} },
};
globalThis.window = { innerWidth: 1280, addEventListener() {}, scrollTo() {} };
globalThis.matchMedia = () => ({ matches: true, addEventListener() {} });
globalThis.MutationObserver = class { observe() {} };
globalThis.location = { hash: "#/" };
globalThis.requestAnimationFrame = () => 0;
globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
globalThis.fetch = () => Promise.reject(new Error("offline shim"));
globalThis.getComputedStyle = () => ({ getPropertyValue: () => "" });
"""


def _run_node_script(script_body: str, verify_js_path: Path) -> subprocess.CompletedProcess:
    full = _DOM_STUB + "\n" + script_body
    return subprocess.run(
        ["node", "--input-type=module"],
        input=full.replace("VERIFY_JS_PATH", str(verify_js_path).replace("\\", "/")),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@pytest.fixture(scope="module")
def _node():
    if shutil.which("node") is None:
        pytest.skip("node not installed")


# ── nearestFreqIndex ──────────────────────────────────────────────────────────

@pytest.mark.usefixtures("_node")
def test_nearest_freq_index_exact():
    r = _run_node_script(r"""
const { nearestFreqIndex } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const freqs = [300, 500, 1000, 2000, 5000, 8000];
assert.equal(nearestFreqIndex(freqs, 1000), 2);
assert.equal(nearestFreqIndex(freqs, 300),  0);
assert.equal(nearestFreqIndex(freqs, 8000), 5);
console.log("NEAREST EXACT OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "NEAREST EXACT OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_nearest_freq_index_snap_to_closest():
    r = _run_node_script(r"""
const { nearestFreqIndex } = await import(pathToFileURL("VERIFY_JS_PATH").href);

// 1300 Hz should snap to 1000 (distance 300) not 2000 (distance 700)
const freqs = [300, 500, 1000, 2000, 5000];
assert.equal(nearestFreqIndex(freqs, 1300), 2, "should snap to 1000");
// 1600 Hz snaps to 2000
assert.equal(nearestFreqIndex(freqs, 1600), 3, "should snap to 2000");
console.log("NEAREST SNAP OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "NEAREST SNAP OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_nearest_freq_index_null_safe():
    r = _run_node_script(r"""
const { nearestFreqIndex } = await import(pathToFileURL("VERIFY_JS_PATH").href);

assert.equal(nearestFreqIndex([], 1000), 0);
assert.equal(nearestFreqIndex(null, 1000), 0);
assert.equal(nearestFreqIndex([1000, 2000], null), 0);
assert.equal(nearestFreqIndex([1000, 2000], NaN), 0);
console.log("NEAREST NULL SAFE OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "NEAREST NULL SAFE OK" in r.stdout


# ── bandDeltaStats ────────────────────────────────────────────────────────────

@pytest.mark.usefixtures("_node")
def test_band_delta_stats_basic():
    r = _run_node_script(r"""
const { bandDeltaStats } = await import(pathToFileURL("VERIFY_JS_PATH").href);

// verify values, screen values at nearest screen frequency
const verifyVals  = [0, -3, -6, -9];
const screenVals  = [0, -4, -5, -10];  // deltas: |0-0|=0, 1, 1, 1
const verifyFreqs = [1000, 2000, 4000, 8000];
const screenFreqs = [1000, 2000, 4000, 8000];

const s = bandDeltaStats(verifyVals, screenVals, verifyFreqs, screenFreqs);
assert.ok(s !== null, "should return stats");
assert.ok(isFinite(s.meanAbsDelta), `meanAbsDelta should be finite: ${s.meanAbsDelta}`);
assert.ok(isFinite(s.maxAbsDelta),  `maxAbsDelta should be finite: ${s.maxAbsDelta}`);
assert.ok(isFinite(s.maxFreqHz),    `maxFreqHz should be finite: ${s.maxFreqHz}`);
// Mean absolute delta = (0 + 1 + 1 + 1) / 4 = 0.75
assert.ok(Math.abs(s.meanAbsDelta - 0.75) < 0.01, `expected mean 0.75, got ${s.meanAbsDelta}`);
console.log("BAND DELTA STATS OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "BAND DELTA STATS OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_band_delta_stats_null_safe():
    r = _run_node_script(r"""
const { bandDeltaStats } = await import(pathToFileURL("VERIFY_JS_PATH").href);

assert.equal(bandDeltaStats(null, [1, 2], [1000], [1000]), null);
assert.equal(bandDeltaStats([1, 2], null, [1000], [1000]), null);
assert.equal(bandDeltaStats([], [], [], []), null);
console.log("BAND DELTA NULL SAFE OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "BAND DELTA NULL SAFE OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_band_delta_stats_max_location():
    r = _run_node_script(r"""
const { bandDeltaStats } = await import(pathToFileURL("VERIFY_JS_PATH").href);

// Max delta at 4000 Hz (delta=5), mean < max
const verifyVals  = [-1, -2, -7];  // delta from screen: 1, 1, 5
const screenVals  = [-2, -3, -2];
const verifyFreqs = [1000, 2000, 4000];
const screenFreqs = [1000, 2000, 4000];

const s = bandDeltaStats(verifyVals, screenVals, verifyFreqs, screenFreqs);
assert.ok(s !== null);
assert.equal(s.maxFreqHz, 4000, `expected maxFreqHz 4000, got ${s.maxFreqHz}`);
assert.ok(Math.abs(s.maxAbsDelta - 5) < 0.01, `expected maxAbsDelta 5, got ${s.maxAbsDelta}`);
console.log("BAND DELTA MAX LOCATION OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "BAND DELTA MAX LOCATION OK" in r.stdout


# ── checklistHtml ─────────────────────────────────────────────────────────────

@pytest.mark.usefixtures("_node")
def test_checklist_html_all_pass():
    r = _run_node_script(r"""
const { checklistHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const row = { ok: true, error: null, hash: "abc123", gates: { round_throat: true, loading: true } };
const html = checklistHtml(row, null, null);
// verified = ok → pass
assert.ok(html.includes("pass"), `expected pass item in: ${html}`);
// gates all pass
assert.ok(!html.includes("fail"), `no fail expected when all gates pass: ${html}`);
console.log("CHECKLIST ALL PASS OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "CHECKLIST ALL PASS OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_checklist_html_gate_fail():
    r = _run_node_script(r"""
const { checklistHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const row = { ok: true, error: null, hash: "abc123", gates: { round_throat: true, loading: false } };
const html = checklistHtml(row, null, null);
// loading gate fails → fail item expected
assert.ok(html.includes("fail"), `expected fail item in: ${html}`);
// loading key should be mentioned
assert.ok(html.includes("loading"), `expected "loading" in: ${html}`);
console.log("CHECKLIST GATE FAIL OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "CHECKLIST GATE FAIL OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_checklist_html_not_audited():
    r = _run_node_script(r"""
const { checklistHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const row = { ok: true, error: null, hash: "abc123", gates: null };
const html = checklistHtml(row, null, null);
// gates null → not audited
assert.ok(html.includes("not audited") || html.includes("unknown"),
  `expected not-audited text in: ${html}`);
console.log("CHECKLIST NOT AUDITED OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "CHECKLIST NOT AUDITED OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_checklist_html_no_size_in_brief():
    r = _run_node_script(r"""
const { checklistHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

// No brief → "no size limit"
const row = { ok: true, error: null, hash: "abc123", gates: { round_throat: true } };
const html = checklistHtml(row, null, null);
assert.ok(html.includes("no size limit") || html.includes("no size"),
  `expected "no size limit" in: ${html}`);
console.log("CHECKLIST NO SIZE OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "CHECKLIST NO SIZE OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_checklist_html_null_row():
    r = _run_node_script(r"""
const { checklistHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

assert.equal(checklistHtml(null, null, null), "");
console.log("CHECKLIST NULL ROW OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "CHECKLIST NULL ROW OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_checklist_html_failed_design():
    r = _run_node_script(r"""
const { checklistHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const row = { ok: false, error: "mesh_too_large", hash: "fedcba", gates: null };
const html = checklistHtml(row, null, null);
// Not verified → fail item
assert.ok(html.includes("fail"), `expected fail in: ${html}`);
// Error text should appear
assert.ok(html.includes("mesh_too_large") || html.includes("failed"),
  `expected error text in: ${html}`);
console.log("CHECKLIST FAILED DESIGN OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "CHECKLIST FAILED DESIGN OK" in r.stdout


# ── Compare query parse (via parseVerifyQuery) ────────────────────────────────

@pytest.mark.usefixtures("_node")
def test_compare_query_parse():
    r = _run_node_script(r"""
const { parseVerifyQuery } = await import(pathToFileURL("VERIFY_JS_PATH").href);

// Compare mode uses ?a=<hash>&b=<hash>
const q = parseVerifyQuery("a=608eef092639&b=ad63b6311c33");
assert.equal(q.compareA, "608eef092639");
assert.equal(q.compareB, "ad63b6311c33");
// Without a/b → null
const q2 = parseVerifyQuery("");
assert.equal(q2.compareA, null);
assert.equal(q2.compareB, null);
console.log("COMPARE QUERY PARSE OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "COMPARE QUERY PARSE OK" in r.stdout


# ── polarPlot smoke (SVG written to fake element) ─────────────────────────────

@pytest.mark.usefixtures("_node")
def test_polar_plot_no_throw():
    r = _run_node_script(r"""
const { polarPlot } = await import(pathToFileURL("VERIFY_JS_PATH").href);

// Minimal stub SVG: should not throw
const fakeSvg = {
  setAttribute() {}, innerHTML: "",
  appendChild() {},
};

const angles = [-90, -60, -30, 0, 30, 60, 90];
const rowsH  = [[-5, -8, -15, 0, -15, -8, -5]];  // one frequency
const rowsV  = [[-6, -9, -16, 0, -16, -9, -6]];

polarPlot(fakeSvg, rowsH, rowsV, angles, 0, { W: 220, H: 220 });
console.log("POLAR PLOT OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "POLAR PLOT OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_polar_plot_null_safe():
    r = _run_node_script(r"""
const { polarPlot } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const fakeSvg = { setAttribute() {}, innerHTML: "", appendChild() {} };
// Should not throw when rowsH/V are null
polarPlot(fakeSvg, null, null, [-90, 0, 90], 0, {});
polarPlot(null, [[-5, 0, -5]], null, [-90, 0, 90], 0, {});
console.log("POLAR PLOT NULL SAFE OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "POLAR PLOT NULL SAFE OK" in r.stdout


# ── node --check ─────────────────────────────────────────────────────────────

@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_node_check_verify_js():
    r = subprocess.run(
        ["node", "--check", str(VERIFY_JS)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"node --check verify.js:\n{r.stderr}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_node_check_balloon_js():
    r = subprocess.run(
        ["node", "--check", str(BALLOON_JS)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"node --check balloon.js:\n{r.stderr}"
