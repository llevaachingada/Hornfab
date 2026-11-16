"""Full-globe directivity view (2026-11-15): the balloon re-sliced around 360°.

The existing globe wraps the ±90° cuts into a half-circle. The stored balloon already holds
the whole sphere, so the H/V planes can be sampled right around a full circle with no new
solves. These tests pin the two halves of that path:

* ``data._balloon_full_circles`` — a synthetic balloon whose front is 0 dB and whose back is
  −20 dB must read 0 dB at 0° and −20 dB at ±180°, front and back for both planes.
* ``charts.globePlot`` — a closed ±180° span must draw a full rim circle and a single ±180°
  label with no NaN, while the ±90° half globe still draws its closed half-disc path.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CHARTSJS = ROOT / "hornlab_search" / "gui" / "static" / "charts.js"

FRONT_BACK_DB = 20.0


def _synthetic_balloon(tmp_path: Path) -> Path:
    n_t, n_p, n_f = 16, 32, 3
    theta = np.linspace(0.0, 180.0, n_t)
    spl = np.zeros((n_f, n_t * n_p), dtype=float)
    back = np.abs(theta - 180.0) < 1e-6
    spl[:, np.repeat(back, n_p)] = -FRONT_BACK_DB         # back pole row, every phi
    p = tmp_path / "response.npz"
    np.savez(p, freqs_hz=np.array([500.0, 1000.0, 2000.0]),
             spl_balloon_db=spl,
             meta=np.array(json.dumps({"balloon_grid": [n_t, n_p]})))
    return p


def test_full_circles_read_front_and_back(tmp_path: Path):
    from hornlab_search.gui.data import _balloon_full_circles

    p = _synthetic_balloon(tmp_path)
    with np.load(p, allow_pickle=False) as z:
        out = _balloon_full_circles(z)
    ang = out["angles360"]
    assert ang[0] == -180.0 and ang[-1] == 180.0 and len(ang) == 145
    c = len(ang) // 2                                      # a = 0 (front)
    for key in ("polar_h360", "polar_v360"):
        row = out[key][0]
        assert row[c] == pytest.approx(0.0), f"{key}: front must be on-axis"
        assert row[0] == pytest.approx(-FRONT_BACK_DB), f"{key}: −180° is the back pole"
        assert row[-1] == pytest.approx(-FRONT_BACK_DB), f"{key}: +180° is the back pole"
    assert len(out["polar_h360"]) == 3 and len(out["polar_h360"][0]) == 145


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

const { globePlot } = await import(pathToFileURL(process.argv[2]).href);
const freqs = [500, 1000, 2000, 4000];
const mkrows = (angles) => freqs.map((_, fi) => angles.map(a =>
  Math.max(-30, Math.min(0, -Math.abs(a) / (30 + fi * 8)))));

const a360 = Array.from({ length: 145 }, (_, i) => -180 + 360 * i / 144);
const svg = new E("svg");
globePlot(svg, mkrows(a360), a360, freqs, { title: "full", H: 360, f0: 700, target: 90 });
const n = walk(svg), texts = n.map(x => x.textContent).filter(Boolean);
const radii = n.filter(x => x.tag === "circle").map(x => +x.attrs.r);
assert.ok(radii.length > 0, "full globe draws rings");
assert.ok(texts.includes("±180°"), "one ±180° label at the top");
assert.ok(texts.includes("+90°") && texts.includes("−90°") && texts.includes("0°"), "azimuth rim labels");
assert.ok(!texts.includes("−180°"), "no duplicate −180° label");
const bad = n.filter(x => Object.values(x.attrs).some(v => /NaN|undefined/.test(v)) || /NaN|undefined/.test(x.textContent));
assert.equal(bad.length, 0, "no NaN/undefined in the full globe");

all.length = 0;
const a90 = Array.from({ length: 73 }, (_, i) => -90 + 180 * i / 72);
const svg2 = new E("svg");
globePlot(svg2, mkrows(a90), a90, freqs, { title: "half", H: 320, f0: 700, target: 90 });
const n2 = walk(svg2);
assert.ok(!n2.map(x => x.textContent).includes("±180°"), "half globe has no ±180° label");
assert.ok(n2.some(x => x.tag === "path" && (x.attrs.d || "").includes("Z")), "half globe still closes its disc");
assert.equal(n2.filter(x => Object.values(x.attrs).some(v => /NaN|undefined/.test(v))).length, 0, "half: no NaN");
console.log("FULL GLOBE OK");
'''


def test_globe_plot_full_circle_under_node(tmp_path: Path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    script = tmp_path / "globe_guard.mjs"
    script.write_text(_SCRIPT, encoding="utf-8")
    r = subprocess.run([node, str(script), str(CHARTSJS)], capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    assert "FULL GLOBE OK" in r.stdout, f"node test failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"
