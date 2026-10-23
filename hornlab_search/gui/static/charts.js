// charts.js — hornlab-search GUI
// AGPL-3.0-or-later.  Adapted from tools/review/review_template.html (same author).
// Exports: el, chart, heat, cmap, niceTicks, diFromCuts

export const NS = "http://www.w3.org/2000/svg";

/** CSS variable helper */
export const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

/** SVG element factory */
export function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

/** Compute ideal tick positions */
export function niceTicks(lo, hi, n = 5) {
  const step0 = (hi - lo) / n;
  const p = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 2.5, 5, 10].map(k => k * p).find(s => s >= step0);
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(6));
  return out;
}

/**
 * Generic 2-D SVG chart.
 * series: [{pts:[[x,y],...], color, dash, dots, r, w, opacity}]
 * hlines: [{y, color, dash}]
 * band: [x0, x1] — filled background strip
 */
export function chart(svg, { W = 460, H = 240, xlog = false, xlim, ylim,
    xticks, yticks, xlabel, ylabel, band, hlines = [], series }) {
  svg.innerHTML = "";
  const m = { l: 44, r: 10, t: 8, b: 32 };
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const tx = xlog ? v => Math.log10(v) : v => v;
  const [x0, x1] = xlim.map(tx), [y0, y1] = ylim;
  const X = v => m.l + (tx(v) - x0) / (x1 - x0) * (W - m.l - m.r);
  const Y = v => H - m.b - (v - y0) / (y1 - y0) * (H - m.t - m.b);
  if (band) el("rect", { x: X(band[0]), y: m.t, width: Math.max(0, X(band[1]) - X(band[0])), height: H - m.t - m.b, fill: css("--band") }, svg);
  const g = el("g", { class: "grid" }, svg);
  for (const t of (yticks || [])) {
    el("line", { x1: m.l, x2: W - m.r, y1: Y(t), y2: Y(t) }, g);
    const tt = el("text", { x: m.l - 6, y: Y(t) + 3, "text-anchor": "end" }, svg);
    tt.textContent = t;
  }
  for (const t of (xticks || [])) {
    el("line", { x1: X(t), x2: X(t), y1: m.t, y2: H - m.b }, g);
    const tt = el("text", { x: X(t), y: H - m.b + 13, "text-anchor": "middle" }, svg);
    tt.textContent = t >= 1000 ? (t / 1000) + "k" : t;
  }
  if (xlabel) { const t = el("text", { x: W - m.r, y: H - 3, "text-anchor": "end" }, svg); t.textContent = xlabel; }
  if (ylabel) { const t = el("text", { x: 4, y: m.t + 2, "dominant-baseline": "hanging" }, svg); t.textContent = ylabel; }
  for (const h of hlines)
    el("line", { x1: m.l, x2: W - m.r, y1: Y(h.y), y2: Y(h.y), stroke: h.color, "stroke-width": 1.2, "stroke-dasharray": h.dash ? "5 4" : "none" }, svg);
  const clipY = v => Math.min(Math.max(v, y0), y1);
  for (const s of series) {
    const pts = s.pts.filter(p => p[1] != null && isFinite(p[1]));
    if (!pts.length) continue;
    if (s.dots) {
      for (const p of pts)
        el("circle", { cx: X(p[0]), cy: Y(clipY(p[1])), r: s.r || 1.6, fill: s.color, opacity: s.opacity ?? 0.45 }, svg);
    } else {
      el("path", { d: pts.map((p, i) => (i ? "L" : "M") + X(p[0]).toFixed(1) + "," + Y(clipY(p[1])).toFixed(1)).join(""),
        fill: "none", stroke: s.color, "stroke-width": s.w || 1.8,
        "stroke-dasharray": s.dash ? "5 4" : "none", "stroke-linejoin": "round" }, svg);
    }
  }
}

/** Perceptual colour ramp: dark navy → teal → pale yellow. -6 dB lands in yellow-green. */
const STOPS = [[0,[18,22,48]],[0.35,[36,70,120]],[0.6,[24,134,140]],[0.85,[120,196,120]],[0.95,[230,220,110]],[1,[255,248,200]]];
export function cmap(t) {
  t = Math.min(1, Math.max(0, t));
  for (let i = 1; i < STOPS.length; i++) {
    if (t <= STOPS[i][0]) {
      const [a, ca] = STOPS[i - 1], [b, cb] = STOPS[i], u = (t - a) / (b - a);
      return ca.map((c, k) => Math.round(c + (cb[k] - c) * u));
    }
  }
  return STOPS[STOPS.length - 1][1];
}

/**
 * Draw polar heatmap on canvas.
 * rows: freq×angle dB matrix (null → −40 dB).  Scale: −40..0 dB.
 */
export function heat(canvas, rows) {
  if (!rows || !rows.length) return;
  const nf = rows.length, na = rows[0].length;
  canvas.width = na; canvas.height = nf;
  const ctx = canvas.getContext("2d"), img = ctx.createImageData(na, nf);
  for (let fi = 0; fi < nf; fi++) for (let a = 0; a < na; a++) {
    const v = rows[fi][a] == null ? -40 : rows[fi][a];
    const c = cmap((v + 40) / 40), o = ((nf - 1 - fi) * na + a) * 4;
    img.data[o] = c[0]; img.data[o + 1] = c[1]; img.data[o + 2] = c[2]; img.data[o + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
}

/** Draw the colorbar into a canvas. */
export function drawCbar(canvas) {
  canvas.width = 400; canvas.height = 10;
  const ctx = canvas.getContext("2d");
  for (let i = 0; i < 400; i++) { const c = cmap(i / 399); ctx.fillStyle = `rgb(${c})`; ctx.fillRect(i, 0, 1, 10); }
}

/** Estimate DI* from target coverage angles. */
export function diFromCuts(h, v) {
  if (h >= 180 && v >= 180) return 0;
  const sh = Math.sin(Math.min(h, 180) * Math.PI / 360), sv = Math.sin(Math.min(v, 180) * Math.PI / 360);
  const om = 4 * Math.asin(Math.min(Math.max(sh * sv, 1e-12), 1));
  return 10 * Math.log10(4 * Math.PI / om);
}

/** Format number with d decimals; show "–" for null/NaN. */
export const fmt = (v, d = 2) => (v == null || !isFinite(v)) ? "–" : Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

/** Common log-x frequency tick positions */
export const FT = [500, 1000, 2000, 5000];

/** Standard objective terms */
export const TERMS = ["cov", "rip", "di", "dislope", "flat", "load"];
export const DEFW  = { cov: 1, rip: 1, di: 0.3, dislope: 0.5, flat: 0.5, load: 0 };

/** Deterministic group colour palette (8 slots). */
const GROUP_COLORS = ["#0d6e7a","#a3713a","#2f7d3b","#b23a3a","#7a4a9a","#2a6d9a","#9a6a2a","#5a7a3a"];
const _gidx = {};
export function groupColor(g) {
  if (!(g in _gidx)) _gidx[g] = Object.keys(_gidx).length % GROUP_COLORS.length;
  return GROUP_COLORS[_gidx[g]];
}
