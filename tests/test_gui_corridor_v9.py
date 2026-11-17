"""v9 coverage-profile corridor display (2026-11-17 amendment §F, G13).

The GUI may only draw what the scorer actually sees.  These tests pin the additive surface:

* ``charts.js chart()`` — ``corridorBand`` (a separate filled band option, default --best/0.10)
  and ``refLines`` polyline styling (``style: "preferred"`` => dotted "1 2"; a string ``dash``).
* ``charts.js isobarMap()/globePlot()`` — ``corridorEdgeCurves`` (min/max dashed "4 3", preferred
  dotted "1 2") and the two new ``isobarLegendHtml`` keys.
* ``app.js`` — the BW chart / isobar wiring fed from the SAME payload arrays, with null samples
  below a plane's onset dropped, so the geometry equals ``scoring_view.profile`` exactly.
* v9 DI payloads carry no scored level, so ``drawDiChart`` must not draw a level line.

The node harness mirrors ``tests/test_gui_target_curves.py``.  The payload is produced by the
real ``hornlab_search.targets.scoring_view._profile_view`` in a subprocess and compared against
the drawn SVG geometry *exactly* (same ``toFixed(1)`` pixel strings, not a tolerance).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APPJS = ROOT / "hornlab_search" / "gui" / "static" / "app.js"
CHARTSJS = ROOT / "hornlab_search" / "gui" / "static" / "charts.js"

# The exact profile from tests/test_scoring_view_profiles.py (same anchors 700 -> 8000).
CORRIDOR_PROFILE = {
    "mode": "corridor", "interpolation": "log_frequency",
    "h": [{"hz": 700.0, "preferred_deg": 80.0, "min_deg": 70.0, "max_deg": 90.0},
          {"hz": 8000.0, "preferred_deg": 43.5, "min_deg": 35.0, "max_deg": 52.0}],
    "v": [{"hz": 700.0, "preferred_deg": 50.0, "min_deg": 40.0, "max_deg": 60.0},
          {"hz": 8000.0, "preferred_deg": 27.0, "min_deg": 20.0, "max_deg": 34.0}],
}
# A corridor whose H onset (1000 Hz) sits above the shared grid start (V onset 700 Hz):
# the H arrays are then null for the first grid samples, which must produce no geometry.
LATE_H_PROFILE = {
    **CORRIDOR_PROFILE,
    "h": [{"hz": 1000.0, "preferred_deg": 80.0, "min_deg": 70.0, "max_deg": 90.0},
          {"hz": 8000.0, "preferred_deg": 43.5, "min_deg": 35.0, "max_deg": 52.0}],
}
TARGET_BASE = {"coverage_h_deg": 80.0, "coverage_v_deg": 50.0,
               "band_lo_hz": 350.0, "band_hi_hz": 8000.0, "f0_hz": 700.0}


def _brief_target(profile: dict) -> dict:
    return {**TARGET_BASE, "coverage_profile": profile}


_SCRIPT = r'''
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";
import fs from "node:fs";

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

const { chart, isobarMap, globePlot, isobarLegendHtml } =
  await import(pathToFileURL(process.argv[2]).href);
const payload = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));

const byClass = (nodes, cls) => nodes.filter(x => x.attrs && x.attrs.class === cls);
const badNodes = nodes => nodes.filter(x =>
  Object.values(x.attrs || {}).some(v => /NaN|undefined/.test(v)) || /NaN|undefined/.test(x.textContent));
const parseD = d => [...String(d).matchAll(/([ML])(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/g)]
  .map(m => [m[1], +m[2], +m[3]]);

// Build corridor geometry exactly as app.js::drawBwCharts does: null (below-onset) indices skipped.
const corridorFor = (p, plane) => {
  const fr = p.freqs_hz;
  const pref = p[plane + "_pref"], mn = p[plane + "_min"], mx = p[plane + "_max"];
  const top = [], bottom = [], maxPts = [], minPts = [], prefPts = [];
  fr.forEach((f, i) => {
    if (mn[i] != null) {
      const topV = mx[i] != null ? mx[i] : pref[i];
      if (topV != null) { top.push([f, topV]); bottom.push([f, mn[i]]); }
    }
    if (mx[i] != null) maxPts.push([f, mx[i]]);
    if (mn[i] != null) minPts.push([f, mn[i]]);
    if (pref[i] != null) prefPts.push([f, pref[i]]);
  });
  return { top, bottom, maxPts, minPts, prefPts };
};

// chart layout used below: W=460, m.l=44, m.r=12, m.t=10 (no ylabel), m.b=32, H=240.
const CH = 240, CT = 10, CB = 32, CL = 44, CR = 12, CW = 460, YLO = 0, YHI = 100;
const mkXform = (xlo, xhi) => {
  const xl = Math.log10(xlo), xh = Math.log10(xhi);
  const X = f => CL + (Math.log10(f) - xl) / (xh - xl) * (CW - CL - CR);
  const Y = v => CH - CB - (v - YLO) / (YHI - YLO) * (CH - CT - CB);
  return { X, Y };
};
const pathD = (pts, X, Y) => pts
  .map((p, i) => `${i ? "L" : "M"}${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join("");

// ---- G13: corridor band and refLines equal the scorer arrays at every sampled grid index ----
{
  const prof = payload.corridor;
  assert.ok(prof, "scoring_view.profile present for a v9 corridor target");
  assert.equal(prof.mode, "corridor");
  assert.equal(prof.freqs_hz.length, 32);
  assert.equal(prof.freqs_hz[0], 700);
  assert.equal(prof.freqs_hz[prof.freqs_hz.length - 1], 8000);

  const c = corridorFor(prof, "h");
  const fr = prof.freqs_hz;
  assert.equal(c.top.length, fr.length, "700 Hz onset: every grid index is scored");
  c.top.forEach((p, i) => {
    assert.deepEqual(p, [fr[i], prof.h_max[i]], `corridor top[${i}] equals h_max[${i}]`);
  });
  c.bottom.forEach((p, i) => {
    assert.deepEqual(p, [fr[i], prof.h_min[i]], `corridor bottom[${i}] equals h_min[${i}]`);
  });
  c.prefPts.forEach((p, i) => {
    assert.deepEqual(p, [fr[i], prof.h_pref[i]], `preferred[${i}] equals h_pref[${i}]`);
  });

  const xlim = [fr[0], fr[fr.length - 1]];
  const svg = new E("svg");
  chart(svg, {
    xlog: true, xlim, ylim: [YLO, YHI], series: [],
    corridorBand: { top: c.top, bottom: c.bottom, color: "#123456", opacity: 0.10 },
    refLines: [
      { pts: c.maxPts, label: "corridor max", dash: "4 3" },
      { pts: c.minPts, label: "corridor min", dash: "4 3" },
      { pts: c.prefPts, label: "preferred — not penalized inside corridor", style: "preferred" },
    ],
  });
  const { X, Y } = mkXform(xlim[0], xlim[1]);
  const nodes = walk(svg);

  const bands = byClass(nodes, "corridor-band");
  assert.equal(bands.length, 1, "one corridor band path");
  const merged = [...c.top, ...c.bottom.slice().reverse()];
  assert.equal(bands[0].attrs.d, merged.map((p, i) =>
    `${i ? "L" : "M"}${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join("") + "Z",
    "band polygon vertices equal the payload arrays exactly");
  assert.equal(parseD(bands[0].attrs.d).length, merged.length, "no extra/omitted band vertex");
  assert.equal(bands[0].attrs.fill, "#123456");
  assert.equal(bands[0].attrs.opacity, "0.1");

  const refs = byClass(nodes, "ref-pts");
  assert.equal(refs.length, 3, "max/min/preferred polylines");
  assert.equal(refs[0].attrs.d, pathD(c.maxPts, X, Y), "corridor max geometry exact");
  assert.equal(refs[1].attrs.d, pathD(c.minPts, X, Y), "corridor min geometry exact");
  assert.equal(refs[2].attrs.d, pathD(c.prefPts, X, Y), "preferred geometry exact");
  assert.equal(refs[0].attrs["stroke-dasharray"], "4 3", "corridor max dashed");
  assert.equal(refs[1].attrs["stroke-dasharray"], "4 3", "corridor min dashed");
  assert.equal(refs[2].attrs["stroke-dasharray"], "1 2", "preferred dotted");
  assert.deepEqual([c.maxPts[0][0], c.maxPts[0][1]], [fr[0], prof.h_max[0]],
    "max endpoint = payload start");
  assert.deepEqual([c.maxPts[c.maxPts.length - 1][0], c.maxPts[c.maxPts.length - 1][1]],
    [fr[fr.length - 1], prof.h_max[prof.h_max.length - 1]], "max endpoint = payload end");
  assert.equal(badNodes(nodes).length, 0, "corridor chart: no NaN/undefined");
}

// ---- null below the plane onset produces no geometry ----
{
  const prof = payload.late_h;
  assert.ok(prof && prof.onset_h_hz > prof.freqs_hz[0], "H onset above the shared grid start");
  const fr = prof.freqs_hz;
  const nullN = fr.filter(f => f < prof.onset_h_hz).length;
  assert.ok(nullN > 0, "below-onset samples exist");
  const c = corridorFor(prof, "h");
  assert.equal(c.top.length, fr.length - nullN, "only scored indices got band vertices");
  assert.ok(c.maxPts.every(p => p[0] >= prof.onset_h_hz), "no max point below the onset");

  const xlim = [fr[0], fr[fr.length - 1]];
  const svg = new E("svg");
  chart(svg, {
    xlog: true, xlim, ylim: [YLO, YHI], series: [],
    corridorBand: { top: c.top, bottom: c.bottom },
    refLines: [
      { pts: c.maxPts, label: "corridor max", dash: "4 3" },
      { pts: c.minPts, label: "corridor min", dash: "4 3" },
      { pts: c.prefPts, label: "preferred", style: "preferred" },
    ],
  });
  const { X } = mkXform(xlim[0], xlim[1]);
  const nodes = walk(svg);
  const verts = parseD(byClass(nodes, "corridor-band")[0].attrs.d);
  assert.equal(verts.length, 2 * c.top.length, "band covers onset..band_hi only");
  const forbidden = new Set(fr.filter(f => f < prof.onset_h_hz).map(f => +X(f).toFixed(1)));
  assert.ok(verts.every(v => !forbidden.has(v[1])), "no vertex on a null (below-onset) grid column");
  assert.equal(badNodes(nodes).length, 0, "late-onset chart: no NaN/undefined");
}

// ---- legacy v7 payload: today's scored-range target + ±10% area, NO corridor geometry ----
{
  const fr = [500, 1000, 2000, 4000, 8000];
  const xlim = [500, 9000], tgt = 80, scoreLo = 700;
  const area = [{ top: [[scoreLo, tgt * 1.1], [xlim[1], tgt * 1.1]],
                  bottom: [[scoreLo, tgt * 0.9], [xlim[1], tgt * 0.9]],
                  color: "#008300", opacity: 0.10 }];
  const refLines = [
    { pts: [[scoreLo, tgt], [xlim[1], tgt]], label: "target H 80°" },
    { y: 60, label: "8k floor 60°" },
  ];
  const svg = new E("svg");
  chart(svg, { xlog: true, xlim, ylim: [YLO, YHI], series: [], area, refLines });
  const nodes = walk(svg);
  assert.equal(byClass(nodes, "corridor-band").length, 0, "legacy: no corridor band");
  const areas = nodes.filter(n => n.tag === "path" && n.attrs.fill && n.attrs.fill !== "none"
    && n.attrs.opacity === "0.1");
  assert.ok(areas.length >= 1, "legacy: ±10% area still drawn");
  assert.equal(byClass(nodes, "ref-pts").length, 1, "legacy: scored-range target polyline");
  assert.ok(!nodes.some(n => /corridor/i.test(n.textContent || "")), "legacy: no corridor label");
  assert.equal(badNodes(nodes).length, 0, "legacy chart: no NaN/undefined");
}

// ---- isobar / globe corridor edge curves + legend keys ----
const freqs = [700, 1000, 2000, 4000, 8000];
const angles = [-90, -60, -30, 0, 30, 60, 90];
const rows = freqs.map((_, fi) => angles.map(a => Math.max(-30, Math.min(0, -Math.abs(a) / (30 + fi * 8)))));
const prof = payload.corridor;
const halfCurve = arr => prof.freqs_hz.map((f, i) => arr[i] == null ? null : [f, arr[i] / 2]).filter(Boolean);
const edges = {
  pref_plus: halfCurve(prof.h_pref), pref_minus: halfCurve(prof.h_pref),
  min_plus: halfCurve(prof.h_min), max_plus: halfCurve(prof.h_max),
};
{
  const svg = new E("svg");
  isobarMap(svg, rows, angles, freqs, { target: 90, f0: 700, corridorEdgeCurves: edges });
  const nodes = walk(svg);
  const prefs = byClass(nodes, "iso-corridor-pref");
  const mins = byClass(nodes, "iso-corridor-min");
  const maxs = byClass(nodes, "iso-corridor-max");
  assert.equal(prefs.length, 2, "preferred pair (both sides)");
  assert.equal(mins.length, 2, "min edge mirrored pair");
  assert.equal(maxs.length, 2, "max edge mirrored pair");
  for (const p of prefs) assert.equal(p.attrs["stroke-dasharray"], "1 2", "preferred dotted");
  for (const p of mins.concat(maxs)) assert.equal(p.attrs["stroke-dasharray"], "4 3", "edges dashed");
  assert.notEqual(prefs[0].attrs["stroke-dasharray"], mins[0].attrs["stroke-dasharray"],
    "corridor edges are visually distinct from the preferred centre");
  assert.equal(badNodes(nodes).length, 0, "isobar corridor: no NaN/undefined");

  const html = isobarLegendHtml({ corridor: true, preferred: true });
  assert.ok(html.includes("coverage profile corridor"), "legend has the corridor key");
  assert.ok(html.includes("scored (min/max edges)"), "corridor key names the scored edges");
  assert.ok(html.includes("preferred line"), "legend has the preferred key");
  assert.ok(html.includes("not penalized inside the corridor"), "preferred key states not penalized");
}

// ---- full globe: same semantics, no NaN anywhere ----
{
  const a360 = Array.from({ length: 145 }, (_, i) => -180 + 360 * i / 144);
  const rows360 = freqs.map((_, fi) => a360.map(a => Math.max(-30, Math.min(0, -Math.abs(a) / (30 + fi * 8)))));
  const svg = new E("svg");
  globePlot(svg, rows360, a360, freqs, {
    title: "full", H: 360, f0: 700, target: 90, corridorEdgeCurves: edges,
  });
  const nodes = walk(svg);
  assert.ok(byClass(nodes, "globe-corridor-pref").length >= 2, "preferred spirals present");
  assert.ok(byClass(nodes, "globe-corridor-min").length >= 2, "min spirals present");
  assert.ok(byClass(nodes, "globe-corridor-max").length >= 2, "max spirals present");
  for (const p of byClass(nodes, "globe-corridor-pref"))
    assert.equal(p.attrs["stroke-dasharray"], "1 2");
  assert.equal(badNodes(nodes).length, 0, "full globe with corridor: no NaN/undefined");
}
console.log("CORRIDOR V9 OK");
'''


def _profile_payload(tmp_path: Path) -> Path:
    """Run the real ``_profile_view`` in a subprocess and write its JSON for the node test."""
    blob = {
        "corridor": _brief_target(CORRIDOR_PROFILE),
        "late_h": _brief_target(LATE_H_PROFILE),
    }
    src = tmp_path / "target.json"
    dst = tmp_path / "profile.json"
    src.write_text(json.dumps(blob), encoding="utf-8")
    code = (
        "import json, sys\n"
        "from hornlab_search.targets.scoring_view import _profile_view\n"
        "blob = json.load(open(sys.argv[1], encoding='utf-8'))\n"
        "out = {k: _profile_view(v) for k, v in blob.items()}\n"
        "json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'))\n"
    )
    r = subprocess.run([sys.executable, "-c", code, str(src), str(dst)],
                       cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, f"profile dump failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"
    return dst


def test_corridor_chart_equals_scoring_view_payload(tmp_path: Path):
    """G13: drawn corridor band/edges equal the scorer arrays at every sampled grid index."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    payload = _profile_payload(tmp_path)
    script = tmp_path / "corridor_v9.mjs"
    script.write_text(_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(CHARTSJS), str(payload)],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert "CORRIDOR V9 OK" in r.stdout, \
        f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"


def test_v9_di_payload_has_no_level_line():
    """v9 levels are profile-driven: the payload carries no level, and the chart stays gated."""
    from hornlab_search.targets.scoring_view import build_scoring_view

    weights = {"cov_profile": 1.0, "dislope": 1.0, "di": 1.0}
    objective = {"version": 9, "cov_below_f0": "mask", "cov_narrow_ratio": 1.0}
    view = build_scoring_view(_brief_target(CORRIDOR_PROFILE), objective, weights, 9)
    assert view is not None
    di = view["di"]
    assert di["level_db"] is None and di["level_scored"] is False, \
        "v9 scores no DI level (its level truth is the per-plane profile)"
    assert di["slope_scored"] is True, "the slope stays a separate slope-only term"
    src = APPJS.read_text(encoding="utf-8")
    assert "svDi.level_scored && svDi.level_db != null" in src, \
        "drawDiChart must keep the level line gated on both level_scored and a non-null level"


def test_app_wires_the_profile_corridor_payload():
    """The app-side mapping consumes scoring_view.profile and emits the additive options/legend."""
    src = APPJS.read_text(encoding="utf-8")
    charts = CHARTSJS.read_text(encoding="utf-8")
    # BW chart: the profile path is gated on pointer presence; legacy runs keep the old branch.
    assert "sv && sv.profile ? sv.profile : null" in src
    assert "corridorBand" in src and "corridor-band" in charts
    assert '"corridor max"' in src and '"corridor min"' in src
    assert 'style: "preferred"' in src and 'style === "preferred" ? "1 2"' in charts
    assert "Shaded: the scored corridor (min..max). Dotted: preferred line (not penalized inside the corridor)." in src
    assert "hf floor ${fdv}° (w ${hf.weight})" in src
    # isobar/globe wiring + legend keys
    assert "corridorEdgeCurves" in src and "corridorEdgeCurves" in charts
    assert "coverage profile corridor — scored (min/max edges)" in charts
    assert "preferred line — not penalized inside the corridor" in charts
    # brief-editor hint: the v9 envelope is separate from the DI slope term.
    assert "v9 briefs use target.coverage_profile (corridor or target mode)" in src
