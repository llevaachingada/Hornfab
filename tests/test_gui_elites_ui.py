"""Elites tab redesign (owner ask, 2026-11-13): pure helpers executed through node.

Covers the client-side browse logic (filters/grouping/counts), the plain-language card text and
the isometric thumbnail builder. The same DOM-stub pattern as tests/test_gui_views_l2.py.
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
const { elitesFilter, eliteHeadline, eliteConstraintLine, eliteThumbSvg,
        eliteThumbPlaceholder, eliteCountsText, elitesNoteText, renderElitesHtml } = app;

// ── a small synthetic catalog: one failing row must never be browsable ────────────────
const cards = [
  { hash: "aaaaaaaa", run: "r1", brief: "b1", family: "OSSE", J: 1.0, pass_all: true,
    run_linked: true, objective_version: 7, has_mesh: true,
    brief_target: { h_deg: 90, v_deg: 60, f_lo_hz: 850, f_hi_hz: 18000, max_mm: 210 } },
  { hash: "bbbbbbbb", run: "r2", brief: "b1", family: "OSSE", J: 1.5, pass_all: true },
  { hash: "cccccccc", run: "r3", brief: "b1", family: "R-OSSE", J: 0.8, pass_all: true },
  { hash: "dddddddd", run: "r4", brief: "b2", family: "OSSE", J: 2.0, pass_all: true },
  { hash: "eeeeeeee", run: "r5", brief: "b2", family: "ICW", J: 0.5, pass_all: true },
  { hash: "ffffffff", run: "r6", brief: "b1", family: "OSSE", J: 0.1, pass_all: false },
];

// brief selected → one best design per typology for that brief, best first
const b1 = elitesFilter(cards, { brief: "b1", mode: "best" });
assert.deepEqual(b1.rows.map(c => c.hash), ["cccccccc", "aaaaaaaa"], JSON.stringify(b1.rows));
assert.equal(b1.group, "family");
assert.equal(b1.matched, 3);
assert.equal(b1.pool, 5);                 // the failing row is out of the browsable pool
assert.equal(b1.pass, 5);
assert.equal(b1.total, 6);
assert.deepEqual(b1.briefs, ["b1", "b2"]);
assert.deepEqual(b1.families, ["ICW", "OSSE", "R-OSSE"]);
assert.equal(b1.byBrief.b1, 3);
assert.equal(b1.byBrief.b2, 2);
assert.equal(b1.byFamily.OSSE, 3);          // a, b (b1) and d (b2); the failing row is out

// typology selected → one best design per brief for that typology
const osse = elitesFilter(cards, { family: "OSSE", mode: "best" });
assert.equal(osse.group, "brief");
assert.deepEqual(osse.rows.map(c => c.hash), ["aaaaaaaa", "dddddddd"]);
assert.equal(osse.matched, 3);

// "all passing" with a brief → every match, best first, no grouping
const allB1 = elitesFilter(cards, { brief: "b1", mode: "all" });
assert.equal(allB1.group, null);
assert.deepEqual(allB1.rows.map(c => c.hash), ["cccccccc", "aaaaaaaa", "bbbbbbbb"]);

// both filters (or neither) → the plain best-first list
const both = elitesFilter(cards, { brief: "b1", family: "OSSE", mode: "best" });
assert.equal(both.group, null);
assert.deepEqual(both.rows.map(c => c.hash), ["aaaaaaaa", "bbbbbbbb"]);
assert.equal(elitesFilter(cards, {}).group, null);

// empty catalog + a filter that matches nothing
const empty = elitesFilter([], {});
assert.deepEqual(empty.rows, []);
assert.equal(empty.total, 0);
assert.equal(empty.pool, 0);
const none = elitesFilter(cards, { brief: "nope" });
assert.equal(none.rows.length, 0);
assert.equal(none.matched, 0);
assert.equal(elitesFilter(cards, { brief: "b1" }).rows.length !== 0, true);

// briefs/families with no browsable design are not offered; the payload names are the
// fallback only when no design carries a count at all.
const extra = elitesFilter(cards, { knownBriefs: ["b3"], knownFamilies: ["FREEFORM"] });
assert.deepEqual(extra.briefs, ["b1", "b2"]);
assert.deepEqual(extra.families, ["ICW", "OSSE", "R-OSSE"]);
assert.equal(extra.catalogFamilies, 3);
assert.equal(extra.byBrief.b3, undefined);
const fallback = elitesFilter([], { knownBriefs: ["b3"], knownFamilies: ["FREEFORM"] });
assert.deepEqual(fallback.briefs, ["b3"]);
assert.deepEqual(fallback.families, ["FREEFORM"]);

// ── plain-language text ──────────────────────────────────────────────────────────────
assert.equal(eliteHeadline({ family: "OSSE", brief_target: { max_mm: 210 } }), "OSSE · ≤ 210 mm");
assert.equal(eliteHeadline({ family: "OSSE" }), "OSSE");
assert.equal(eliteHeadline({}), "Typology not recorded");
assert.equal(eliteHeadline({ family: "ICW", brief_target: { max_mm: null } }), "ICW");

assert.equal(
  eliteConstraintLine({ brief: "b1w_hifi_90x60_850_wide_v4",
                        brief_target: { h_deg: 90, v_deg: 60, f_lo_hz: 850, f_hi_hz: 18000 } }),
  "b1w_hifi_90x60_850_wide_v4 · 90°×60° H×V · 850 Hz–18 kHz");
assert.equal(eliteConstraintLine({ brief: "x" }), "x");
assert.equal(eliteConstraintLine({}), "No brief recorded");

assert.equal(eliteCountsText(elitesFilter(cards, {})),
             "5 passing designs · 6 audited across 3 typologies");
assert.equal(eliteCountsText(elitesFilter(cards, { brief: "b1" })),
             "5 passing designs · 6 audited across 3 typologies · showing 2");
assert.equal(elitesNoteText({ page: 24, brief: "b1" }, b1),
             "Best design in each typology for this brief — 2 typologies, chosen from 3 passing designs.");
assert.equal(elitesNoteText({ page: 24, family: "OSSE" }, osse),
             "Best design for each brief — 2 briefs, chosen from 3 passing designs.");
assert.equal(elitesNoteText({ page: 24 }, elitesFilter(cards, {})), "5 designs, best first.");

// ── isometric thumbnail builder ──────────────────────────────────────────────────────
const profile = {
  kind: "section",
  h: [[0, 8], [30, 20], [80, 60], [120, 110]],
  v: [[0, 8], [30, 18], [80, 50], [120, 90]],
};
const svg = eliteThumbSvg(profile, { w: 220, h: 140 });
assert.ok(svg.startsWith("<svg"), svg.slice(0, 80));
assert.ok(svg.includes('viewBox="0 0 220 140"'), svg);
assert.ok(svg.includes("<path") && svg.includes("elite-svg-body"), svg);
assert.ok(svg.includes("<ellipse") && svg.includes("elite-svg-mouth"), svg);
assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(svg), "thumbnail must not hardcode hex colours");
const mouthCx = Number((svg.match(/elite-svg-mouth" cx="([\d.]+)"/) || [])[1]);
assert.ok(Number.isFinite(mouthCx) && mouthCx > 110, `mouth sits on the mouth side: ${mouthCx}`);

// a bigger box is honoured
assert.ok(eliteThumbSvg(profile, { w: 320, h: 200 }).includes('viewBox="0 0 320 200"'));

// reversed z (mesh stored mouth→throat) still puts the wide mouth on the same side
const reversed = eliteThumbSvg({ h: profile.h.slice().reverse(), v: profile.v.slice().reverse() }, { w: 220, h: 140 });
const reversedCx = Number((reversed.match(/elite-svg-mouth" cx="([\d.]+)"/) || [])[1]);
assert.ok(Math.abs(reversedCx - mouthCx) < 0.2, `flip is orientation-safe: ${reversedCx} vs ${mouthCx}`);

// degenerate input → the honest placeholder, never a crash
assert.ok(eliteThumbSvg(null).includes("no geometry stored"));
assert.ok(eliteThumbSvg({ h: [], v: [] }).includes("no geometry stored"));
assert.ok(eliteThumbPlaceholder().includes('aria-hidden="true"'));

// ── whole-page builder: plain header, no CSV plumbing, cards first ───────────────────
const payload = {
  available: true,
  cards,
  labels: { throat: "round throat" },
  briefs: ["b1", "b2"],
  families: ["ICW", "OSSE", "R-OSSE"],
  sources: ["docs/data/gate_audit_x/gate_audit.csv"],
  n_pass: 5,
};
const html = renderElitesHtml(payload);
assert.ok(html.includes("Designs that passed every gate in the latest audits — best first."), html);
assert.ok(html.includes("5 passing designs · 6 audited across 3 typologies"), html);
assert.ok(html.includes('id="elites-brief"') && html.includes('id="elites-family"'), html);
assert.ok(html.includes("Best picks") && html.includes("All passing"), html);
assert.ok(html.includes('id="elites-refresh"'), html);
assert.ok(html.includes("Constraints") && html.includes("≤ 210 mm"), html);
assert.ok(!html.includes("docs/data"), "the raw audit CSV path must not be on the page");
assert.ok(!html.includes("gate_audit"), "no gate-audit paths on the page");
assert.ok(!html.includes("Source:"), "no per-card source line");
assert.ok(!html.includes("ffffffff"), "the failing design is not browsable");
assert.ok(html.includes('title="design id'), "the short hash keeps a design-id tooltip");

// unavailable payload keeps a plain, non-technical state
const off = renderElitesHtml({ available: false, note: "no gate-audit CSV under docs/data" });
assert.ok(off.includes("No gate audit has been recorded yet"), off);
assert.ok(!off.includes("docs/data"), off);
assert.equal(renderElitesHtml(null).includes("No gate audit has been recorded yet"), true);

console.log("ELITES UI GUARD OK");
'''


def test_elites_ui_helpers_guard(tmp_path: Path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "elites_ui_under_test.mjs"
    script.write_text(_GUARD_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(APPJS)],
                       capture_output=True, text=True, encoding="utf-8", cwd=str(tmp_path))
    assert "ELITES UI GUARD OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"

_3D_GUARD_SCRIPT = r'''
﻿import { pathToFileURL } from "node:url";
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
globalThis.window = { addEventListener() {}, matchMedia: () => ({ matches: false, addEventListener() {} }) };
globalThis.matchMedia = () => ({ matches: false, addEventListener() {} });
globalThis.MutationObserver = class { observe() {} disconnect() {} };
globalThis.location = { hash: "#/elites", search: "" };
globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
globalThis.fetch = () => Promise.reject(new Error("offline guard"));
globalThis.requestAnimationFrame = (f) => 0;

const app = await import(pathToFileURL(process.argv[2]).href);

const outline = [];
for (let i = 0; i <= 40; i++) outline.push([i * 10, 25 + i * 4]);
for (let i = 0; i <= 10; i++) outline.push([400 - i * 40, 9]);

const ax = app._eliteProfileAxis(outline, outline, 6);
assert.ok(ax, "axis profile resolves");
assert.ok(Math.abs(ax.z0) < 1e-9 && Math.abs(ax.z1 - 400) < 1e-9, JSON.stringify(ax && { z0: ax.z0, z1: ax.z1 }));
assert.ok(ax.rh[0] < ax.rh[ax.rh.length - 1], "oriented throat -> mouth");
assert.ok(Math.abs(ax.rh[ax.rh.length - 1] - 185) < 8, "mouth radius kept (outer wall)");
assert.ok(ax.rh.every((r) => r >= 0 && r <= 186), "outer wall, no invented radii");

const geom = app.eliteHornGeometry({ h: outline, v: outline }, { n: 8 }, { levels: 8, segments: 8 });
assert.ok(geom, "geometry resolves");
assert.equal(geom.positions.length, 8 * 8 * 3, "levels x segments vertices");
assert.equal(geom.indices.length, (8 - 1) * 8 * 6, "quad strip indices");
const L = 8, S = 8;
const ringR = (li) => {
  let m = 0;
  for (let si = 0; si < S; si++) {
    const x = geom.positions[(li * S + si) * 3], y = geom.positions[(li * S + si) * 3 + 1];
    m = Math.max(m, Math.hypot(x, y));
  }
  return m;
};
assert.ok(ringR(L - 1) > ringR(0) * 4, "mouth ring far wider than the throat ring");
const geom2 = app.eliteHornGeometry({ h: outline, v: outline }, { n: 2 }, { levels: 8, segments: 8 });
const diag = (g) => {
  const si = 1;
  const x = g.positions[si * 3], y = g.positions[si * 3 + 1];
  return Math.hypot(x, y);
};
assert.ok(diag(geom) > diag(geom2) * 1.15, "higher exponent -> squarer section (larger 45 deg radius)");
assert.equal(app.eliteHornGeometry(null, null), null, "no profile -> no geometry");
assert.equal(app.eliteHornGeometry({ h: [[0, 0]], v: [[0, 0]] }, null), null, "degenerate outline -> no geometry");
assert.ok(geom.zEye > 0, "mouth rim at +z for the camera");

console.log("ELITES 3D GUARD OK");
'''


def test_elites_3d_geometry_guard(tmp_path: Path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "elites_3d_under_test.mjs"
    script.write_text(_3D_GUARD_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(APPJS)],
                       capture_output=True, text=True, encoding="utf-8", cwd=str(tmp_path))
    assert "ELITES 3D GUARD OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"
