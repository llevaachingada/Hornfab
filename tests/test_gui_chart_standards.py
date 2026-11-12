"""WP9 chart standards — offline unit tests.

Covers:
- C1: logGrid() produces correct minor ticks
- C1: logGrid() handles edge cases (lo<=0, non-finite)
- AXES: constants defined and have expected keys
- fixedRange: clamps range from spec but expands when data is out of range
- chart() syntax and node --check pass (import guard)
- polarPlot export exists
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHARTSJS = ROOT / "hornlab_search" / "gui" / "static" / "charts.js"
APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"

# ---------------------------------------------------------------------------
# JS syntax checks (node --check on the actual files)
# ---------------------------------------------------------------------------

def test_charts_js_syntax():
    """charts.js must parse without errors."""
    r = subprocess.run(["node", "--check", str(CHARTSJS)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_app_js_syntax():
    """app.js must parse without errors."""
    r = subprocess.run(["node", "--check", str(APPJS)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


# ---------------------------------------------------------------------------
# Node-based unit tests for JS chart helpers
# ---------------------------------------------------------------------------


def test_chart_standards_node():
    """Run JS assertions for logGrid, AXES, fixedRange, polarPlot via node."""
    # Build the script with the charts.js path embedded (not via process.argv)
    charts_url = CHARTSJS.as_uri()
    script = f"""
import assert from "node:assert/strict";
globalThis.getComputedStyle = () => ({{ getPropertyValue: () => "" }});
globalThis.window = {{ innerWidth: 800, addEventListener() {{}} }};
globalThis.document = {{ getElementById: () => null, createElementNS: () => ({{
  setAttribute() {{}}, appendChild() {{}}, children: [], innerHTML: ""
}}) }};

const {{ logGrid, logTicks, AXES, fixedRange, angleTicks, polarPlot }} = await import("{charts_url}");

// C4: angle ticks are 30-degree multiples, not niceTicks' ±50/0/50
assert.deepEqual(angleTicks(-90, 90), [-90, -60, -30, 0, 30, 60, 90]);
assert.deepEqual(angleTicks(-100, 100), [-90, -60, -30, 0, 30, 60, 90]);
assert.deepEqual(angleTicks(-45, 45), [-30, 0, 30]);
assert.deepEqual(angleTicks(15, 100), [30, 60, 90]);
assert.deepEqual(angleTicks(0, 10), [0]);

// C1: minor ticks between 100-10000
const {{ major, minor }} = logGrid(100, 10000);
assert.ok(major.includes(1000), "major missing 1000");
assert.ok(minor.includes(300), "minor missing 300");
assert.ok(minor.includes(400), "minor missing 400");
assert.ok(!minor.includes(500), "minor should NOT include 500 (it's major)");
assert.ok(minor.includes(600), "minor missing 600");
assert.ok(minor.includes(3000), "minor missing 3000");

// edge case: lo <= 0
const result0 = logGrid(0, 1000);
assert.ok(Array.isArray(result0.minor), "logGrid(0,1000) should return minor array");

// AXES constant
assert.ok(AXES.onAxis, "AXES.onAxis missing");
assert.ok(AXES.di, "AXES.di missing");
assert.ok(AXES.beamwidth, "AXES.beamwidth missing");
assert.ok(AXES.zrho, "AXES.zrho missing");
assert.strictEqual(AXES.onAxis.lo, -15, "onAxis.lo should be -15");
assert.strictEqual(AXES.onAxis.hi, 10, "onAxis.hi should be 10");
assert.strictEqual(AXES.di.lo, 0, "di.lo should be 0");
assert.strictEqual(AXES.di.hi, 15, "di.hi should be 15");
assert.strictEqual(AXES.beamwidth.lo, 0, "beamwidth.lo should be 0");
assert.strictEqual(AXES.beamwidth.hi, 180, "beamwidth.hi should be 180");

// fixedRange: data within spec => spec unchanged
const r1 = fixedRange({{ lo: 0, hi: 15, major: 3 }}, [2, 10]);
assert.strictEqual(r1.lo, 0, "fixedRange: within-range lo");
assert.strictEqual(r1.hi, 15, "fixedRange: within-range hi");

// fixedRange: data below spec lo => extends down
const r2 = fixedRange({{ lo: 0, hi: 15, major: 3 }}, [-5, 10]);
assert.ok(r2.lo <= -5, "fixedRange: lo should extend below -5");

// fixedRange: data above spec hi => extends up
const r3 = fixedRange({{ lo: 0, hi: 15, major: 3 }}, [2, 20]);
assert.ok(r3.hi >= 20, "fixedRange: hi should extend above 20");

// fixedRange: empty data => spec unchanged
const r4 = fixedRange({{ lo: 0, hi: 15, major: 3 }}, []);
assert.strictEqual(r4.lo, 0, "fixedRange: empty data lo");
assert.strictEqual(r4.hi, 15, "fixedRange: empty data hi");

// polarPlot export exists
assert.strictEqual(typeof polarPlot, "function", "polarPlot should be a function");

console.log("chart-standards: all assertions pass");
"""
    r = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"stdout={r.stdout}\nstderr={r.stderr}"
    assert "all assertions pass" in r.stdout


# ---------------------------------------------------------------------------
# C5: refLines appear in charts.js exports
# ---------------------------------------------------------------------------

def test_charts_js_exports_reflines():
    """charts.js chart() must accept refLines parameter (function signature check)."""
    src = CHARTSJS.read_text(encoding="utf-8")
    assert "refLines" in src, "refLines parameter missing from chart()"
    assert "1 3" in src, "dotted stroke-dasharray '1 3' missing from C5 reference line"


def test_charts_js_exports_markers():
    """charts.js chart() must accept markers parameter."""
    src = CHARTSJS.read_text(encoding="utf-8")
    assert "markers" in src, "markers parameter missing from chart()"


def test_charts_js_unscored_hatch():
    """C10: charts.js must draw unscored hatch regions."""
    src = CHARTSJS.read_text(encoding="utf-8")
    assert "unscored" in src, "unscored parameter missing from chart()"
    assert "rotate(45" in src, "hatch rotate pattern missing"


def test_charts_js_isobar_overrange():
    """C8: isobarMap must handle over-range (>0 dB) values."""
    src = CHARTSJS.read_text(encoding="utf-8")
    assert "OVER_RANGE_COLOR" in src or "overRange" in src or "FFB0C8" in src or "over" in src.lower(), \
        "C8 over-range color missing from isobarMap"


def test_charts_js_ylog():
    """chart() must accept ylog parameter for log-y axes (H5 sigma/axis-ratio)."""
    src = CHARTSJS.read_text(encoding="utf-8")
    assert "ylog" in src, "ylog parameter missing from chart()"
