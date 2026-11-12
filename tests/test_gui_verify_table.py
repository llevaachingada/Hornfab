"""WP3 tests: pure helpers in verify.js, executed through node.

These tests run offline (no server, no solver, no GPU) using the
node --input-type=module technique.  Every assertion exercises a pure
exported function from verify.js.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VERIFY_JS = ROOT / "hornlab_search" / "gui" / "static" / "verify.js"


# ── Shared DOM/global stub used by all node scripts ─────────────────────────

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
    """Execute a node ES-module script that imports verify.js from argv[2]."""
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
    """Skip all tests if node is not installed."""
    if shutil.which("node") is None:
        pytest.skip("node not installed")


# ── parseVerifyQuery ─────────────────────────────────────────────────────────

@pytest.mark.usefixtures("_node")
def test_parse_verify_query_defaults():
    r = _run_node_script(r"""
const { parseVerifyQuery } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const q = parseVerifyQuery("");
assert.equal(q.design, null);
assert.equal(q.sort, "verify_j");
assert.equal(q.dir, "asc");
assert.equal(q.ghost, true);
assert.equal(q.show, "all");
assert.equal(q.fHz, null);
assert.equal(q.compareA, null);
assert.equal(q.compareB, null);
console.log("PARSE DEFAULTS OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "PARSE DEFAULTS OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_parse_verify_query_all_params():
    r = _run_node_script(r"""
const { parseVerifyQuery } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const q = parseVerifyQuery("design=abc123&sort=screen_j&dir=desc&ghost=0&show=gate-pass&f=2000&a=aaa&b=bbb");
assert.equal(q.design, "abc123");
assert.equal(q.sort, "screen_j");
assert.equal(q.dir, "desc");
assert.equal(q.ghost, false);
assert.equal(q.show, "gate-pass");
assert.equal(q.fHz, 2000);
assert.equal(q.compareA, "aaa");
assert.equal(q.compareB, "bbb");
console.log("PARSE ALL PARAMS OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "PARSE ALL PARAMS OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_parse_verify_query_invalid_show_defaults_all():
    r = _run_node_script(r"""
const { parseVerifyQuery } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const q = parseVerifyQuery("show=nonsense");
assert.equal(q.show, "all");
console.log("INVALID SHOW OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "INVALID SHOW OK" in r.stdout


# ── buildVerifyQuery / round-trip ────────────────────────────────────────────

@pytest.mark.usefixtures("_node")
def test_build_verify_query_round_trip():
    r = _run_node_script(r"""
const { parseVerifyQuery, buildVerifyQuery } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const state = { design: "abc123", sort: "delta_j", dir: "desc", ghost: false,
                show: "failed", fHz: 3000.5, compareA: null, compareB: null };
const qs = buildVerifyQuery(state);
const q  = parseVerifyQuery(qs);
assert.equal(q.design, "abc123");
assert.equal(q.sort, "delta_j");
assert.equal(q.dir, "desc");
assert.equal(q.ghost, false);
assert.equal(q.show, "failed");
// fHz may have minor floating-point shift; allow 1 Hz tolerance
assert.ok(Math.abs(q.fHz - 3000.5) < 1, `fHz mismatch: ${q.fHz}`);
console.log("ROUND TRIP OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "ROUND TRIP OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_build_verify_query_defaults_omitted():
    r = _run_node_script(r"""
const { buildVerifyQuery } = await import(pathToFileURL("VERIFY_JS_PATH").href);

// Default values should not appear in the query string
const qs = buildVerifyQuery({ sort: "verify_j", dir: "asc", ghost: true, show: "all" });
assert.ok(!qs.includes("sort"), `unexpected sort in: ${qs}`);
assert.ok(!qs.includes("dir"), `unexpected dir in: ${qs}`);
assert.ok(!qs.includes("ghost"), `unexpected ghost in: ${qs}`);
assert.ok(!qs.includes("show"), `unexpected show in: ${qs}`);
console.log("DEFAULTS OMITTED OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "DEFAULTS OMITTED OK" in r.stdout


# ── deltaCellHtml ────────────────────────────────────────────────────────────

@pytest.mark.usefixtures("_node")
def test_delta_cell_html_null_inputs():
    r = _run_node_script(r"""
const { deltaCellHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

// Both null
assert.ok(deltaCellHtml(null, null).includes("–"), "both null should produce dash");
// One null
assert.ok(deltaCellHtml(4.5, null).includes("–"), "verify null should produce dash");
assert.ok(deltaCellHtml(null, 4.5).includes("–"), "screen null should produce dash");
console.log("DELTA NULL OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "DELTA NULL OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_delta_cell_html_positive_is_bad():
    r = _run_node_script(r"""
const { deltaCellHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

// Positive delta (verify > screen) → bad-text class (verify worse)
const html = deltaCellHtml(4.0, 4.5);
assert.ok(html.includes("bad-text"), `expected bad-text in: ${html}`);
assert.ok(html.includes("+"), `expected + sign in: ${html}`);
// screen-tier wording appears in title
assert.ok(html.includes("screen"), `expected word screen in title: ${html}`);
assert.ok(html.includes("verify"), `expected word verify in title: ${html}`);
console.log("DELTA POSITIVE BAD OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "DELTA POSITIVE BAD OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_delta_cell_html_negative_is_good():
    r = _run_node_script(r"""
const { deltaCellHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

// Negative delta (verify < screen) → good-text class
const html = deltaCellHtml(5.0, 4.0);
assert.ok(html.includes("good-text"), `expected good-text in: ${html}`);
assert.ok(html.includes("−"), `expected minus sign in: ${html}`);
console.log("DELTA NEGATIVE GOOD OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "DELTA NEGATIVE GOOD OK" in r.stdout


# ── sortRows ─────────────────────────────────────────────────────────────────

@pytest.mark.usefixtures("_node")
def test_sort_rows_ascending():
    r = _run_node_script(r"""
const { sortRows } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const rows = [{ id: "c", verify_j: 5.0 }, { id: "a", verify_j: 3.0 }, { id: "b", verify_j: 4.0 }];
const sorted = sortRows(rows, "verify_j", "asc");
assert.deepEqual(sorted.map(r => r.id), ["a", "b", "c"]);
console.log("SORT ASC OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "SORT ASC OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_sort_rows_descending():
    r = _run_node_script(r"""
const { sortRows } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const rows = [{ id: "a", verify_j: 3.0 }, { id: "b", verify_j: 5.0 }, { id: "c", verify_j: 4.0 }];
const sorted = sortRows(rows, "verify_j", "desc");
assert.deepEqual(sorted.map(r => r.id), ["b", "c", "a"]);
console.log("SORT DESC OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "SORT DESC OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_sort_rows_nulls_last():
    r = _run_node_script(r"""
const { sortRows } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const rows = [
  { id: "null1", verify_j: null },
  { id: "low",  verify_j: 2.0  },
  { id: "null2", verify_j: null },
  { id: "high", verify_j: 5.0  },
];
const sorted = sortRows(rows, "verify_j", "asc");
// Non-null values first, then nulls
assert.ok(sorted[0].verify_j !== null, "first should be non-null");
assert.ok(sorted[1].verify_j !== null, "second should be non-null");
assert.ok(sorted[2].verify_j === null, "third should be null");
assert.ok(sorted[3].verify_j === null, "fourth should be null");
console.log("NULLS LAST OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "NULLS LAST OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_sort_rows_stable():
    r = _run_node_script(r"""
const { sortRows } = await import(pathToFileURL("VERIFY_JS_PATH").href);

// Equal values should preserve insertion order (stable sort)
const rows = [
  { id: "first",  verify_j: 4.0 },
  { id: "second", verify_j: 4.0 },
  { id: "third",  verify_j: 4.0 },
];
const sorted = sortRows(rows, "verify_j", "asc");
assert.deepEqual(sorted.map(r => r.id), ["first", "second", "third"]);
console.log("STABLE SORT OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "STABLE SORT OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_sort_rows_empty():
    r = _run_node_script(r"""
const { sortRows } = await import(pathToFileURL("VERIFY_JS_PATH").href);

assert.deepEqual(sortRows([], "verify_j", "asc"), []);
assert.deepEqual(sortRows(null, "verify_j", "asc"), []);
console.log("EMPTY SORT OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "EMPTY SORT OK" in r.stdout


# ── fidelityPillsHtml ────────────────────────────────────────────────────────

@pytest.mark.usefixtures("_node")
def test_fidelity_pills_html_contains_tiers():
    r = _run_node_script(r"""
const { fidelityPillsHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const report = {
  fidelity: {
    verify: { n_freqs: [29], balloon_grid: [[23, 45]], n_points: [1035], dof_range: [2203, 6912] },
    screen: { n_freqs: [12], balloon_grid: [[16, 32]], n_points: [512],  dof_range: [1980, 5004] },
  }
};
const html = fidelityPillsHtml(report);
assert.ok(html.includes("verify"), `missing "verify" in: ${html}`);
assert.ok(html.includes("screen"), `missing "screen" in: ${html}`);
// Numbers must come from data, not hardcoded
assert.ok(html.includes("29"), `missing freq count 29 in: ${html}`);
assert.ok(html.includes("12"), `missing freq count 12 in: ${html}`);
assert.ok(html.includes("23×45"), `missing balloon grid 23x45 in: ${html}`);
assert.ok(html.includes("16×32"), `missing balloon grid 16x32 in: ${html}`);
console.log("FIDELITY PILLS OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "FIDELITY PILLS OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_fidelity_pills_html_null_safe():
    r = _run_node_script(r"""
const { fidelityPillsHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

assert.equal(fidelityPillsHtml(null), "");
assert.equal(fidelityPillsHtml({}), "");
console.log("FIDELITY NULL SAFE OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "FIDELITY NULL SAFE OK" in r.stdout


# ── summaryHtml ──────────────────────────────────────────────────────────────

@pytest.mark.usefixtures("_node")
def test_summary_html_null_safe():
    r = _run_node_script(r"""
const { summaryHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

// Should not throw on null/minimal input
const html = summaryHtml(null);
assert.equal(html, "");
const html2 = summaryHtml({});
assert.ok(typeof html2 === "string", "should return a string");
console.log("SUMMARY NULL SAFE OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "SUMMARY NULL SAFE OK" in r.stdout


@pytest.mark.usefixtures("_node")
def test_summary_html_contains_counts_from_data():
    r = _run_node_script(r"""
const { summaryHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const summary = {
  n_verified: 5, n_failed: 1, n_pairs: 5, n_worse: 4,
  bias_median_pct: 18.2, spearman_all: 0.30, spearman_top5: 0.30, top5_overlap: 3,
  best_verify_hash: "608eef", best_verify_j: 4.622,
  screen1_hash: "ad63b6", screen1_verify_rank: 2,
};
const html = summaryHtml(summary);
// All counts must come from data
assert.ok(html.includes("5"), `missing n_verified=5 in: ${html}`);
assert.ok(html.includes("18.2") || html.includes("18"), `missing bias 18.2% in: ${html}`);
// tier label (screen or verify) must appear
assert.ok(html.includes("verify") || html.includes("screen"), `missing tier label in: ${html}`);
console.log("SUMMARY COUNTS OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "SUMMARY COUNTS OK" in r.stdout


# ── emptyStateHtml ───────────────────────────────────────────────────────────

@pytest.mark.usefixtures("_node")
def test_empty_state_html_contains_command_and_tier_words():
    r = _run_node_script(r"""
const { emptyStateHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const html = emptyStateHtml("20261027T051600Z-screen-ed1da9");
assert.ok(html.includes("verify"), `missing "verify" in: ${html}`);
assert.ok(html.includes("screen"), `missing "screen" in: ${html}`);
// must contain a copyable hornlab-search command
assert.ok(html.includes("hornlab-search verify --run"), `missing command in: ${html}`);
// must reference the run id
assert.ok(html.includes("20261027T051600Z-screen-ed1da9"), `missing run id in: ${html}`);
console.log("EMPTY STATE OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "EMPTY STATE OK" in r.stdout


# ── standaloneHeaderHtml ─────────────────────────────────────────────────────

@pytest.mark.usefixtures("_node")
def test_standalone_header_html_tier_words():
    r = _run_node_script(r"""
const { standaloneHeaderHtml } = await import(pathToFileURL("VERIFY_JS_PATH").href);

const html = standaloneHeaderHtml();
assert.ok(html.includes("verify") || html.includes("screen"),
  `missing tier word in: ${html}`);
// single-design phrasing
assert.ok(html.toLowerCase().includes("single") || html.toLowerCase().includes("standalone"),
  `missing single/standalone in: ${html}`);
console.log("STANDALONE HEADER OK");
""", VERIFY_JS)
    assert r.returncode == 0, f"stdout: {r.stdout}\nstderr: {r.stderr}"
    assert "STANDALONE HEADER OK" in r.stdout


# ── node --check ─────────────────────────────────────────────────────────────

@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_node_check_verify_js():
    r = subprocess.run(
        ["node", "--check", str(VERIFY_JS)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"node --check verify.js:\n{r.stderr}"
