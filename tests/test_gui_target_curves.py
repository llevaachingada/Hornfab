"""Scored-target truthfulness overlays in charts.js (2026-11-16, Lane C).

Pins the optional, backward-compatible additions:

* ``chart()`` refLines gains a ``{pts:[[x,y],...]}`` polyline form (same neutral dotted style).
* ``isobarMap()`` gains ``targetLoHz`` (guides only where scored), ``belowMode`` ("mask" /
  "one_sided"), ``illustrativeCurve`` (display-only corridor, never a target) and ``floorRays``.
* ``globePlot()`` maps the same three concepts into polar: onset-limited rays, annular sectors,
  spiral display-only corridors, floor rays.
* ``isobarLegendHtml()`` gains the ``below`` / ``floor`` / ``illustrative`` keys.

The harness mirrors ``test_gui_globe_full.py``: an SVG element mock, a canvas mock, and a
``walk()`` helper that collects every descendant so assertions can read attributes.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHARTSJS = ROOT / "hornlab_search" / "gui" / "static" / "charts.js"


_SCRIPT = r'''
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";

const all = [];
class E {
  constructor(tag) { this.tag = tag; this.attrs = {}; this.children = []; this.style = {}; this.dataset = {};
    this.textContent = ""; this.innerHTML = ""; this.isConnected = true; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  appendChild(c) { this.children.push(c); c.parentElement = this; return c; }
  addEventListener() {} removeEventListener() {}
  getBoundingClientRect() { return { width: 460, height: 360, left: 0, top: 0 }; }
  querySelector() { return null; } querySelectorAll() { return []; }
  classList = { toggle() {}, add() {}, remove() {} };
}
const walk = (e, out = []) => { for (const c of e.children || []) { out.push(c); walk(c, out); } return out; };
const canvasMock = () => {
  const cv = new E("canvas");
  cv.getContext = () => ({
    createImageData(w, h) { return { data: new Uint8ClampedArray(w * h * 4) }; },
    putImageData() {}, setTransform() {}, clearRect() {},
  });
  cv.toDataURL = () => "data:image/png;base64,";
  return cv;
};
globalThis.document = {
  documentElement: { style: {} },
  createElementNS: (_ns, tag) => { const e = new E(tag); all.push(e); return e; },
  createElement: tag => tag === "canvas" ? canvasMock() : new E(tag),
  getElementById: () => null, querySelector: () => null, querySelectorAll: () => [],
};
globalThis.window = { devicePixelRatio: 1 };
globalThis.getComputedStyle = () => ({ getPropertyValue: () => "" });
globalThis.requestAnimationFrame = f => f();
globalThis.ResizeObserver = class { observe() {} unobserve() {} };

const { chart, isobarMap, globePlot, isobarLegendHtml } = await import(pathToFileURL(process.argv[2]).href);

const byClass = (nodes, cls) => nodes.filter(x => x.attrs && x.attrs.class === cls);
const badNodes = nodes => nodes.filter(x =>
  Object.values(x.attrs || {}).some(v => /NaN|undefined/.test(v)) || /NaN|undefined/.test(x.textContent));

// Parse an SVG path "M12.3,45.6L.." into [[cmd, x, y], ...]
const parseD = d => [...String(d).matchAll(/([ML])(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/g)]
  .map(m => [m[1], +m[2], +m[3]]);
const near = (a, b, eps = 0.05) => Math.abs(a - b) <= eps;

const freqs = [500, 1000, 2000, 4000];
const angles = [-90, -60, -30, 0, 30, 60, 90];
const rows = freqs.map((_, fi) => angles.map(a => Math.max(-30, Math.min(0, -Math.abs(a) / (30 + fi * 8)))));

// ── 1. chart() refLines {pts} polyline ──────────────────────────────────────────────────────
// chart layout: W = 460 (mock width), m.l=44, m.r=12, no ylabel => m.t=10, m.b=32, H=240.
const CH = 240, CT = 10, CB = 32, CL = 44, CR = 12, CW = 460;
const cyOf = v => CH - CB - (v - 0) / (100 - 0) * (CH - CT - CB);
{
  const svg = new E("svg");
  const refLines = [
    { pts: [[700, 60], [8000, 60]], label: "flat" },
    { pts: [[700, 80], [8000, 43.5]], label: "slope" },
  ];
  chart(svg, { xlim: [500, 8000], ylim: [0, 100],
    series: [{ pts: [[500, 50], [8000, 50]], color: "#123456" }], refLines });
  const paths = byClass(walk(svg), "ref-pts");
  assert.equal(paths.length, 2, "two pts polylines drawn");

  const flat = parseD(paths[0].attrs.d);
  assert.equal(flat.length, 2, "flat polyline has two points");
  assert.ok(near(flat[0][1], CL + (700 - 500) / (8000 - 500) * (CW - CL - CR)), "flat start x = X(700)");
  // The horizontal line's y must equal the y for 60.
  assert.ok(near(flat[0][2], cyOf(60)) && near(flat[1][2], cyOf(60)),
    `flat y should equal y(60)=${cyOf(60)} got ${flat[0][2]},${flat[1][2]}`);
  assert.ok(near(flat[0][2], flat[1][2]), "flat line is horizontal");

  const oblique = parseD(paths[1].attrs.d);
  assert.ok(near(oblique[0][2], cyOf(80)), "oblique start y = y(80)");
  assert.ok(near(oblique[1][2], cyOf(43.5)), "oblique end y = y(43.5)");
  assert.ok(Math.abs(oblique[0][2] - oblique[1][2]) > 10, "oblique endpoints differ in y");

  // dotted by default, long-dash when dash=true
  assert.equal(paths[0].attrs["stroke-dasharray"], "1 3", "pts default dotted");
  const svg2 = new E("svg");
  chart(svg2, { xlim: [500, 8000], ylim: [0, 100],
    series: [{ pts: [[500, 50], [8000, 50]], color: "#123456" }],
    refLines: [{ pts: [[700, 60], [8000, 60]], dash: true }] });
  assert.equal(byClass(walk(svg2), "ref-pts")[0].attrs["stroke-dasharray"], "5 4", "dash=true uses 5 4");
}

// ── 2. isobarMap backward compatibility + onset-limited guides ──────────────────────────────
const isoGuideSel = x => x.tag === "line" && x.attrs["stroke-dasharray"] === "4 3" && x.attrs["stroke-opacity"] === "0.95";
{
  // Old opts only (target: 90, f0: 700) -> full-width guides across the plot (regression).
  const svg = new E("svg");
  isobarMap(svg, rows, angles, freqs, { target: 90, f0: 700 });
  const guides = walk(svg).filter(isoGuideSel);
  assert.equal(guides.length, 2, "old-style target: exactly two guides");
  // legend=true default => m.r=64, pw=460-46-64=350; plot spans x=46..396.
  for (const g of guides) {
    assert.equal(+g.attrs.x1, 46, "old-style guide starts at the plot left edge");
    assert.equal(+g.attrs.x2, 396, "old-style guide ends at the plot right edge");
  }
  const nodes = walk(svg);
  assert.equal(badNodes(nodes).length, 0, "old-style isobar: no NaN/undefined");
}

const Xiso = f => 46 + (Math.log10(f) - Math.log10(500)) / (Math.log10(4000) - Math.log10(500)) * 350;

{
  // targetLoHz=700, mask: scored guides start at X(700); nothing drawn below it.
  const svg = new E("svg");
  isobarMap(svg, rows, angles, freqs, { target: 90, targetLoHz: 700, belowMode: "mask" });
  const nodes = walk(svg);
  const guides = nodes.filter(isoGuideSel);
  assert.equal(guides.length, 2, "onset guide pair");
  for (const g of guides) assert.ok(near(+g.attrs.x1, Xiso(700), 0.05),
    `guide left end at X(700)=${Xiso(700)} got ${g.attrs.x1}`);
  assert.equal(byClass(nodes, "iso-below-free").length, 0, "mask: no below-onset polygons");
  assert.equal(byClass(nodes, "iso-below-bound").length, 0, "mask: no below-onset bound dashes");
  assert.ok(!nodes.some(n => n.textContent === "wide free below f0"), "mask: no below-onset label");
}

{
  // one_sided: translucent polygon pair + lower-bound dashes + label.
  const svg = new E("svg");
  isobarMap(svg, rows, angles, freqs, { target: 90, targetLoHz: 700, belowMode: "one_sided" });
  const nodes = walk(svg);
  const free = byClass(nodes, "iso-below-free");
  assert.equal(free.length, 2, "one_sided: translucent wedge pair");
  for (const p of free) assert.equal(+p.attrs.opacity, 0.10, "wedge opacity ~0.10");
  assert.equal(byClass(nodes, "iso-below-bound").length, 2, "one_sided: lower-bound dashes both sides");
  assert.ok(nodes.some(n => n.textContent === "wide free below f0"), "one_sided: label present");
}

{
  // illustrativeCurve: two symmetric dashed curves whose mid y differs from the end y.
  const svg = new E("svg");
  isobarMap(svg, rows, angles, freqs, { target: 90,
    illustrativeCurve: [[700, 80], [2000, 61.5], [4000, 43.5]] });
  const illus = byClass(walk(svg), "iso-illustrative");
  assert.equal(illus.length, 2, "two symmetric illustrative curves");
  for (const p of illus) {
    const pts = parseD(p.attrs.d);
    assert.ok(pts.length >= 3, "illustrative curve has >= 3 points");
    assert.ok(Math.abs(pts[1][2] - pts[2][2]) > 0.5,
      `curve: mid y ${pts[1][2]} should differ from end y ${pts[2][2]}`);
    assert.equal(p.attrs["stroke-dasharray"], "2 3", "illustrative dash 2 3");
  }
  const html = isobarLegendHtml({ illustrative: true });
  assert.ok(html.includes("NOT scored"), "legend says illustrative corridor is NOT scored");
}

{
  // legend keys for the new concepts
  const html = isobarLegendHtml({ below: "one_sided", floor: true, illustrative: true });
  assert.ok(html.includes("wide free below f0 (one-sided)"), "legend below key");
  assert.ok(html.includes("8 kHz floor (narrow-only)"), "legend floor key");
  assert.ok(html.includes("hypothetical corridor — NOT scored"), "legend illustrative key");
}

// ── 3. globePlot: same concepts in polar ────────────────────────────────────────────────────
const mkrows = a => freqs.map((_, fi) => a.map(x => Math.max(-30, Math.min(0, -Math.abs(x) / (30 + fi * 8)))));
const a360 = Array.from({ length: 145 }, (_, i) => -180 + 360 * i / 144);
{
  const svg = new E("svg");
  globePlot(svg, mkrows(a360), a360, freqs, { title: "full", H: 360, f0: 700, target: 90,
    targetLoHz: 700, belowMode: "one_sided",
    illustrativeCurve: [[700, 80], [2000, 61.5], [4000, 43.5]],
    floorRays: { h_deg: 60, v_deg: 37.5 } });
  const nodes = walk(svg);
  const radii = nodes.filter(x => x.tag === "circle").map(x => +x.attrs.r);
  const texts = nodes.map(x => x.textContent).filter(Boolean);
  assert.ok(radii.length > 0, "full globe draws rings");
  assert.ok(texts.includes("±180°"), "one ±180° label at the top");
  assert.ok(texts.includes("+90°") && texts.includes("−90°") && texts.includes("0°"), "azimuth rim labels");
  assert.ok(!texts.includes("−180°"), "no duplicate −180° label");

  const illus = byClass(nodes, "globe-illustrative");
  assert.equal(illus.length, 2, "two symmetric globe illustrative spirals");
  for (const p of illus) {
    const pts = parseD(p.attrs.d);
    assert.ok(pts.length >= 3, "spiral has multiple r/angle points");
    assert.ok((String(p.attrs.d).match(/L/g) || []).length >= 2, "spiral is non-straight (>= 2 segments)");
    assert.equal(p.attrs["stroke-dasharray"], "2 3", "globe illustrative dash 2 3");
  }
  assert.equal(byClass(nodes, "globe-below-free").length, 2, "one_sided: two annular sectors");
  assert.ok(byClass(nodes, "globe-floor").length >= 2, "floor ray pair drawn");
  assert.equal(badNodes(nodes).length, 0, "full globe with overlays: no NaN/undefined");
}

{
  // Old-opts globe regression: rays still start at the centre (full radius).
  const a90 = Array.from({ length: 73 }, (_, i) => -90 + 180 * i / 72);
  const svg = new E("svg");
  globePlot(svg, mkrows(a90), a90, freqs, { title: "half", H: 320, f0: 700, target: 90 });
  const nodes = walk(svg);
  const guides = nodes.filter(x => x.tag === "line" && x.attrs["stroke-dasharray"] === "4 3" && x.attrs["stroke-opacity"] === "0.95");
  assert.equal(guides.length, 2, "old-style globe: exactly two target rays");
  const starts = new Set(guides.map(g => `${g.attrs.x1},${g.attrs.y1}`));
  assert.equal(starts.size, 1, "both old-style rays start at the same centre");
  for (const g of guides) assert.ok(g.attrs.x1 !== g.attrs.x2 || g.attrs.y1 !== g.attrs.y2,
    "old-style ray spans the radius");
  assert.equal(badNodes(nodes).length, 0, "old-style globe: no NaN");
}
console.log("TARGET CURVES OK");
'''


def test_target_curves_under_node(tmp_path: Path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "target_curves.mjs"
    script.write_text(_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(CHARTSJS)], capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    assert "TARGET CURVES OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"
