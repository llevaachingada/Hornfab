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
/** Pixel width an SVG will be drawn at (so text and strokes render 1:1, never scaled up). */
export function measuredWidth(svg, fallback) {
  const w = Math.round(svg.getBoundingClientRect().width || svg.parentElement?.getBoundingClientRect().width || 0);
  return w >= 120 ? w : fallback;
}

export function chart(svg, { W = 460, H = 240, xlog = false, xlim, ylim,
    xticks, yticks, xlabel, ylabel, band, hlines = [], series, fill }) {
  svg.innerHTML = "";
  W = measuredWidth(svg, W);
  const m = { l: 44, r: 12, t: ylabel ? 20 : 10, b: 32 };   // unit label sits above the plot, clear of the top tick
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("width", W); svg.setAttribute("height", H);
  svg.dataset.chart = "1";                      // re-drawn on resize (app.js)
  const tx = xlog ? v => Math.log10(v) : v => v;
  const [x0, x1] = xlim.map(tx), [y0, y1] = ylim;
  const X = v => m.l + (tx(v) - x0) / (x1 - x0) * (W - m.l - m.r);
  const Y = v => H - m.b - (v - y0) / (y1 - y0) * (H - m.t - m.b);
  if (fill) for (const f of fill)
    el("rect", { x: m.l, width: W - m.l - m.r, y: Y(Math.min(f.y1, ylim[1])), height: Math.max(0, Y(Math.max(f.y0, ylim[0])) - Y(Math.min(f.y1, ylim[1]))), fill: f.color, opacity: f.opacity ?? 0.12 }, svg);
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
  if (ylabel) { const t = el("text", { x: m.l - 6, y: 11, "text-anchor": "end" }, svg); t.textContent = ylabel; }
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


/** Find where a level is crossed walking outward from the centre column, per side; null if never.
 *  Linear interpolation between the two samples that bracket the level. */
function edgeAngle(row, angles, level, dir) {
  const c = Math.floor(row.length / 2);
  for (let i = c; i + dir >= 0 && i + dir < row.length; i += dir) {
    const a = row[i], b = row[i + dir];
    if (a == null || b == null) return null;
    if (a >= level && b < level) return angles[i] + (angles[i + dir] - angles[i]) * (a - level) / (a - b);
  }
  return null;
}

/** Polar map (directivity sonogram): level rel. on-axis vs angle (x) and frequency (y, rows low -> high),
 *  with angle / frequency axes and isobar lines at the given levels (default -3, -6, -10 dB).
 *  rows: [nf][na] dB (clipped at -40), angles: [na] deg, freqs: [nf] Hz. */
export function polarMap(svg, rows, angles, freqs, { H = 230, isobars = [-3, -6, -10], fmtF } = {}) {
  svg.innerHTML = "";
  if (!rows || !rows.length || !angles) return;
  const W = measuredWidth(svg, 320);
  const m = { l: 46, r: 8, t: 8, b: 30 };
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("width", W); svg.setAttribute("height", H);
  svg.dataset.chart = "1";
  const pw = W - m.l - m.r, ph = H - m.t - m.b, nf = rows.length, na = rows[0].length;
  const a0 = angles[0], a1 = angles[angles.length - 1];
  const X = a => m.l + (a - a0) / (a1 - a0) * pw;
  const Yrow = fi => m.t + ph - (fi + 0.5) / nf * ph;          // row centre, low frequency at the bottom
  // raster: one pixel per sample, scaled smoothly into the plot box
  const cv = document.createElement("canvas"); cv.width = na; cv.height = nf;
  const ctx = cv.getContext("2d"), img = ctx.createImageData(na, nf);
  for (let fi = 0; fi < nf; fi++) for (let a = 0; a < na; a++) {
    const v = rows[fi][a] == null ? -40 : rows[fi][a];
    const c = cmap((v + 40) / 40), o = ((nf - 1 - fi) * na + a) * 4;
    img.data[o] = c[0]; img.data[o + 1] = c[1]; img.data[o + 2] = c[2]; img.data[o + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  el("image", { href: cv.toDataURL(), x: m.l, y: m.t, width: pw, height: ph, preserveAspectRatio: "none",
                style: "image-rendering:auto" }, svg);
  // axes
  const g = el("g", { class: "grid" }, svg);
  for (const a of [-90, -60, -30, 0, 30, 60, 90]) {
    if (a < a0 || a > a1) continue;
    el("line", { x1: X(a), x2: X(a), y1: m.t + ph, y2: m.t + ph + 4, stroke: css("--muted") }, svg);
    const t = el("text", { x: X(a), y: m.t + ph + 15, "text-anchor": "middle" }, svg); t.textContent = a + "°";
  }
  const step = nf > 8 ? 2 : 1, f = fmtF || (v => v >= 1000 ? +(v / 1000).toFixed(1) + "k" : Math.round(v));
  for (let fi = 0; fi < nf; fi += step) {
    const t = el("text", { x: m.l - 5, y: Yrow(fi) + 3, "text-anchor": "end" }, svg); t.textContent = f(freqs[fi]);
  }
  const xl = el("text", { x: m.l + pw, y: H - 2, "text-anchor": "end" }, svg); xl.textContent = "angle";
  const yl = el("text", { x: 2, y: m.t + 2, "dominant-baseline": "hanging" }, svg); yl.textContent = "Hz";
  // isobars (directivity contours): the outermost crossing of each level, left and right of axis
  const styles = { "-3": "2 3", "-6": "none", "-10": "6 3" };
  for (const lev of isobars) {
    for (const dir of [-1, 1]) {
      const pts = [];
      for (let fi = 0; fi < nf; fi++) {
        const ang = edgeAngle(rows[fi], angles, lev, dir);
        if (ang != null) pts.push([X(ang), Yrow(fi)]);
        else if (pts.length) { drawIso(pts); pts.length = 0; }
      }
      drawIso(pts);
      function drawIso(p) {
        if (p.length < 2) return;
        const d = p.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + "," + q[1].toFixed(1)).join("");
        el("path", { d, fill: "none", stroke: "#000", "stroke-opacity": 0.35, "stroke-width": lev === -6 ? 3.2 : 2.4 }, svg);
        el("path", { d, fill: "none", stroke: "#fff", "stroke-width": lev === -6 ? 1.6 : 1.1,
                     "stroke-dasharray": styles[String(lev)] || "none" }, svg);
      }
    }
  }
  el("line", { x1: X(0), x2: X(0), y1: m.t, y2: m.t + ph, stroke: "#fff", "stroke-opacity": 0.25 }, svg);
}

/** Family palette: distinct hues by index (not by group), readable on light and dark backgrounds. */
export const FAMILY_COLORS = ["#2a9db0", "#d98a2b", "#7fb43a", "#c9566e", "#8b6fd1", "#3b7dd8", "#b8a23a", "#5fb8a0", "#d46a3c", "#9a9a9a"];
export function familyColor(i) { return FAMILY_COLORS[i % FAMILY_COLORS.length]; }

/** Wall cross-section, true aspect: H plane to the right (+r), V plane mirrored left (−r), depth z up.
 *  designs: [{profile: {h: [[z, r]...], v: [...], kind}, color, label, filled}]. Section outlines
 *  (kind 'section') are drawn as closed shapes; node clouds (kind 'nodes') as small dots. */
export function wallSection(svg, designs, { H = 300, compact = false, extent = null } = {}) {
  svg.innerHTML = "";
  const W = measuredWidth(svg, compact ? 150 : 460);
  const m = compact ? { l: 4, r: 4, t: 4, b: 4 } : { l: 40, r: 10, t: 10, b: 30 };
  let rmax = 1, z0 = Infinity, z1 = -Infinity;
  for (const d of designs) for (const k of ["h", "v"]) for (const [z, r] of (d.profile?.[k] || [])) {
    rmax = Math.max(rmax, Math.abs(r)); z0 = Math.min(z0, z); z1 = Math.max(z1, z);
  }
  if (extent) ({ rmax, z0, z1 } = extent);              // shared scale across several drawings
  if (!isFinite(z0)) { svg.setAttribute("viewBox", `0 0 ${W} ${H}`); return; }
  const pw = W - m.l - m.r, ph = H - m.t - m.b;
  const sc = Math.min(pw / (2 * rmax * 1.04), ph / ((z1 - z0) * 1.04));        // equal mm per pixel on both axes
  const cx = m.l + pw / 2, by = m.t + ph - (ph - (z1 - z0) * sc) / 2;
  const X = r => cx + r * sc, Y = z => by - (z - z0) * sc;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("width", W); svg.setAttribute("height", H);
  svg.dataset.chart = "1";
  if (!compact) {
    const g = el("g", { class: "grid" }, svg);
    for (const t of niceTicks(-rmax, rmax, 6)) {
      el("line", { x1: X(t), x2: X(t), y1: m.t, y2: m.t + ph }, g);
      const tt = el("text", { x: X(t), y: m.t + ph + 14, "text-anchor": "middle" }, svg); tt.textContent = Math.abs(t);
    }
    for (const t of niceTicks(z0, z1, 4)) {
      el("line", { x1: m.l, x2: m.l + pw, y1: Y(t), y2: Y(t) }, g);
      const tt = el("text", { x: m.l - 5, y: Y(t) + 3, "text-anchor": "end" }, svg); tt.textContent = t;
    }
    const a = el("text", { x: m.l + pw, y: H - 2, "text-anchor": "end" }, svg); a.textContent = "r mm (H →)";
    const b = el("text", { x: m.l, y: H - 2 }, svg); b.textContent = "(← V) r mm";
    const c = el("text", { x: 2, y: m.t + 2, "dominant-baseline": "hanging" }, svg); c.textContent = "z mm";
  }
  el("line", { x1: cx, x2: cx, y1: m.t, y2: m.t + ph, stroke: css("--muted"), "stroke-dasharray": "3 3", "stroke-opacity": 0.6 }, svg);
  for (const d of designs) {
    const p = d.profile || {};
    for (const [k, sgn] of [["h", 1], ["v", -1]]) {
      const pts = p[k] || [];
      if (!pts.length) continue;
      if (p.kind === "section") {
        const path = pts.map(([z, r], i) => (i ? "L" : "M") + X(sgn * r).toFixed(1) + "," + Y(z).toFixed(1)).join("") + "Z";
        el("path", { d: path, fill: d.filled ? d.color : "none", "fill-opacity": d.filled ? 0.35 : 0,
                     stroke: d.color, "stroke-width": compact ? 1 : 1.5, "stroke-dasharray": d.dash ? "4 3" : "none",
                     "stroke-linejoin": "round" }, svg);
      } else {
        for (const [z, r] of pts) el("circle", { cx: X(sgn * r), cy: Y(z), r: compact ? 0.8 : 1.4, fill: d.color, opacity: 0.7 }, svg);
      }
    }
  }
}
