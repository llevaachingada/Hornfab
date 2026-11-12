"""Pins for the 2026-11-12 GUI visual audit (D1/D3/D4).

Node-backed behaviour for D1/D2/D5 lives beside the views they exercise
(``test_gui_run_identity.py``, ``test_gui_verify_panel.py``); this file pins the reader-side
column alignment and the table-overflow CSS contract.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
APP_CSS = ROOT / "hornlab_search" / "gui" / "static" / "app.css"
CHARTS_JS = ROOT / "hornlab_search" / "gui" / "static" / "charts.js"
VERIFY_JS = ROOT / "hornlab_search" / "gui" / "static" / "verify.js"
APP_JS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"

_CONFIG = {
    "name": "t",
    "bounds": {
        "a_deg": {"lo": 10.0, "hi": 80.0},
        "L_mm": {"lo": 56.0, "hi": 400.0},
        "morph_fixed": {"lo": 0.0, "hi": 0.6},
    },
}


def _make_run(root: Path) -> Path:
    run = root / "runs" / "20261112T000000Z-screen-aaaaaa"
    (run / "cma").mkdir(parents=True)
    (run / "config.yaml").write_text(yaml.safe_dump(_CONFIG, sort_keys=False), encoding="utf-8")
    (run / "run.json").write_text("{}", encoding="utf-8")
    (run / "search.ndjson").write_text("", encoding="utf-8")
    (run / "cma" / "fit.dat").write_text(
        "% # columns=\"iteration, evaluation, sigma, axis ratio, bestever, best, median, worst, iqr, p25\"\n"
        "1 10 0.1 1.0 2.0 2.0 2.0 2.0 0.0 2.0\n",
        encoding="utf-8",
    )
    # One unparsable column in the middle. The reader must preserve the column position so the
    # values after it do not slide onto the wrong parameter (D1b).
    (run / "cma" / "stddev.dat").write_text(
        "% # columns=\"iteration, evaluation, sigma, void, void, stds\"\n"
        "1 10 0.1 0 0 0.2 x 0.4\n",
        encoding="utf-8",
    )
    return run


def test_cma_stddev_keeps_column_positions(tmp_path: Path):
    from hornlab_search.gui.data import cma_dynamics

    d = cma_dynamics(_make_run(tmp_path))
    assert d["available"] is True
    assert d["param_names"] == ["a_deg", "L_mm", "morph_fixed"]
    assert d["stddev"] == [[0.2, None, 0.4]], (
        "a missing per-parameter σ column must stay null in place, not shift later params"
    )


def test_verify_table_scrolls_and_pills_cannot_overlap_numbers():
    css = APP_CSS.read_text(encoding="utf-8")
    # real horizontal scrolling with a visible affordance, not silent clipping
    assert ".tbl-wrap" in css and "overflow-x: auto" in css
    assert "::-webkit-scrollbar" in css and "height: 10px" in css
    assert ".tbl-scroll-hint" in css and ".tbl-scroll.is-scrollable .tbl-scroll-hint" in css
    # per-column minimums for the verify table
    assert "#vfy-table { min-width:" in css
    assert "#vfy-table td.vfy-gates" in css
    gates_block = css.split("#vfy-table td.vfy-gates", 1)[1].split("}", 1)[0]
    assert "min-width: 220px" in gates_block
    assert "max-width: none" in gates_block
    # the design table lives inside the scroll affordance + clipping wrapper
    verify_src = VERIFY_JS.read_text(encoding="utf-8")
    assert 'class="tbl-scroll" id="vfy-table-scroll"' in verify_src
    assert 'id="vfy-table-wrap" class="tbl-wrap"' in verify_src
    assert "wireScrollHints(root)" in verify_src
    # the compare table gets the same wrapper + hint
    assert 'class="tbl-scroll"' in verify_src and 'id="vfy-cmp-tbl"' in verify_src
    assert "wireScrollHints(resultEl)" in verify_src


def test_gate_audit_table_gets_min_width_and_scroll():
    css = APP_CSS.read_text(encoding="utf-8")
    assert "#gate-audit-card .tbl-wrap { overflow-x: auto; }" in css
    block = css.split("#gate-audit-card table", 1)[1].split("}", 1)[0]
    assert "min-width: 760px" in block
    # gateAuditHtml wraps both the lead table and the folded "show all" table in .tbl-scroll >
    # .tbl-wrap and states that every audited gate column is shown (scroll, never silent absent).
    src = APP_JS.read_text(encoding="utf-8")
    gate_fn = src.split("function gateAuditHtml(audit)", 1)[1].split("\n}", 1)[0]
    assert gate_fn.count('class="tbl-wrap"') == 1  # one helper reused for lead + folded tables
    assert gate_fn.count('class="tbl-scroll"') == 1
    assert "scroll for all columns" in gate_fn
    assert "audited gate columns are shown" in gate_fn
    assert "${table(lead)}" in gate_fn and "${table(rest)}" in gate_fn
    assert "wireScrollHints(ROOT)" in src


def test_verify_routes_keep_their_query_string():
    """The verify routes own ?design/sort/show/a/b; route() must match them against the full hash.

    Without this the compare view never receives a/b and its table cannot be rendered (or audited).
    """
    src = APP_JS.read_text(encoding="utf-8")
    assert src.count("query: true") == 2, "both verify routes are query-aware"
    assert "(query ? hash : path).match(re)" in src


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_wire_scroll_hints_marks_only_real_overflow():
    script = r"""
import assert from "node:assert/strict";
const { wireScrollHints } = await import("CHARTS_URL");

const state = {};
const wrap = {
  scrollWidth: 1240, clientWidth: 624, scrollLeft: 0, dataset: {}, handlers: {},
  addEventListener(ev, fn) { this.handlers[ev] = fn; },
};
const box = {
  classList: {
    toggle(cls, on) { state[cls] = !!on; },
  },
  querySelector(sel) { return sel === ".tbl-wrap" ? wrap : null; },
  querySelectorAll() { return []; },
  matches() { return true; },
};
const root = {
  matches() { return false; },
  querySelectorAll(sel) { return sel === ".tbl-scroll" ? [box] : []; },
};
wireScrollHints(root);
assert.equal(state["is-scrollable"], true, "overflowing wrapper must be marked scrollable");
assert.equal(state["at-end"], false, "fresh table is not at the end");
wrap.scrollLeft = 800;
wrap.handlers.scroll();
assert.equal(state["at-end"], true, "reaching the last column clears the affordance");
console.log("SCROLL HINT OK");
"""
    r = subprocess.run(
        ["node", "--input-type=module", "-e", script.replace("CHARTS_URL", CHARTS_JS.as_uri())],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"stdout={r.stdout}\nstderr={r.stderr}"
    assert "SCROLL HINT OK" in r.stdout

