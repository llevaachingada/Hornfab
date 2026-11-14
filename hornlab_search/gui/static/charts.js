// charts.js — hornlab-search GUI
// AGPL-3.0-or-later.  Adapted from tools/review/review_template.html (same author).
// Exports: el, chart, heat, cmap, niceTicks, angleTicks, diFromCuts, logGrid, AXES, fixedRange, polarPlot,
//          catColor/CAT_N (validated categorical palette), fmtSmart, fmtLogTick, sparkline, stackBarHtml

export const NS = "http://www.w3.org/2000/svg";

/** Monotonic id source for per-instance SVG clip paths (one counter per module load). */
let _clipSeq = 0;

/** CSS variable helper */
export const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

/** SVG element factory */
export function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

/**
 * Wire a visible scroll affordance onto `.tbl-scroll` blocks. The inner `.tbl-wrap` is the
 * clipping ancestor; when its content is wider than its scrollport we mark the outer box
 * `is-scrollable` (which reveals the "scroll for all columns" hint and the right-edge shadow)
 * and `at-end` once the user has reached the last column. Safe to call repeatedly.
 */
export function wireScrollHints(root) {
  if (!root || typeof root.querySelectorAll !== "function") return;
  const boxes = [];
  if (typeof root.matches === "function" && root.matches(".tbl-scroll")) boxes.push(root);
  root.querySelectorAll(".tbl-scroll").forEach(b => boxes.push(b));
  boxes.forEach(box => {
    const wrap = box.querySelector(".tbl-wrap");
    if (!wrap) return;
    const update = () => {
      const overflow = wrap.scrollWidth > wrap.clientWidth + 1;
      box.classList.toggle("is-scrollable", overflow);
      box.classList.toggle("at-end",
        overflow && wrap.scrollLeft + wrap.clientWidth >= wrap.scrollWidth - 2);
    };
    update();
    if (!wrap.dataset.scrollHintWired) {
      wrap.dataset.scrollHintWired = "1";
      wrap.addEventListener("scroll", update, { passive: true });
      if (typeof ResizeObserver !== "undefined") {
        try {
          const ro = new ResizeObserver(update);
          ro.observe(wrap);
          box._scrollHintRO = ro;   // keep a handle; the table outlives transient redraws
        } catch (_) { /* older engines: the initial + scroll updates still work */ }
      }
    }
  });
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
 * Angle ticks on a 30° grid (C4): the 30° multiples inside [lo, hi].
 * Cut charts used niceTicks, which produced ±50/0/50 for a ±90° cut; audio readers expect
 * −90, −60, −30, 0, 30, 60, 90. Falls back to the endpoint when the span holds no multiple.
 */
export function angleTicks(lo, hi, step = 30) {
  lo = Number(lo); hi = Number(hi);
  if (!isFinite(lo) || !isFinite(hi)) return [];
  if (hi < lo) { const t = lo; lo = hi; hi = t; }
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(v === 0 ? 0 : v);
  return out.length ? out : [lo, hi];
}

/**
 * Log-frequency ticks: the 1/2/5 x decade values strictly inside [lo, hi], plus the exact
 * endpoints when neither is already within ~2 % of an included tick. Sorted, deduped, finite.
 * logTicks(120, 12000) -> [120, 200, 500, 1000, 2000, 5000, 10000, 12000]
 */
export function logTicks(lo, hi) {
  lo = Number(lo); hi = Number(hi);
  if (!isFinite(lo) || !isFinite(hi) || lo <= 0 || hi <= 0) return [];
  if (hi < lo) { const t = lo; lo = hi; hi = t; }
  if (hi === lo) return [lo];
  const out = [];
  for (let d = Math.floor(Math.log10(lo)); d <= Math.ceil(Math.log10(hi)); d++) {
    for (const m of [1, 2, 5]) {
      const v = m * Math.pow(10, d);
      if (v > lo && v < hi) out.push(v);
    }
  }
  const near = v => out.some(t => Math.abs(t - v) <= 0.02 * v);
  if (!near(lo)) out.push(lo);
  if (!near(hi)) out.push(hi);
  return [...new Set(out.filter(v => isFinite(v) && v > 0).map(v => +v.toFixed(6)))]
    .sort((a, b) => a - b);
}

/**
 * Log-frequency minor grid: returns {major, minor} where major = logTicks(lo, hi)
 * (1-2-5 × decade + endpoints), minor = all integer-multiple gridlines not in major
 * (3,4,6,7,8,9 × 10^d).  Used to give the semi-log-paper look that every audio tool uses.
 * C1 fix: unlabelled minor gridlines at every integer × decade.
 */
export function logGrid(lo, hi) {
  const major = logTicks(lo, hi);
  const minor = [];
  lo = Number(lo); hi = Number(hi);
  if (!isFinite(lo) || !isFinite(hi) || lo <= 0 || hi <= 0) return { major, minor };
  const lo10 = Math.floor(Math.log10(lo)), hi10 = Math.ceil(Math.log10(hi));
  for (let d = lo10; d <= hi10; d++) {
    for (let m = 2; m <= 9; m++) {
      if (m === 2 || m === 5) continue;    // 2 and 5 are already major (via logTicks)
      const v = m * Math.pow(10, d);
      if (v > lo && v < hi) minor.push(+v.toFixed(6));
    }
  }
  return { major, minor: minor.sort((a, b) => a - b) };
}

/**
 * Fixed-axis specifications for the standard acoustic-analysis charts (C2–C4).
 * Each spec has { lo, hi, major } and optionally { minor }.
 * Pass to fixedRange() with the data to get an expanded-only range.
 */
export const AXES = {
  onAxis:   { lo: -15, hi: 10,  major: 5,    minor: 1  },   // dB, on-axis response
  di:       { lo:   0, hi: 15,  major: 3             },   // dB, directivity index
  beamwidth:{ lo:   0, hi: 180, major: 30,   minor: 15 },   // degrees
  zrho:     { lo:   0, hi: 1.5, major: 0.25           },   // × ρc
};

/**
 * Expand a fixed-axis spec outward ONLY to contain all finite data values.
 * Expansion is in whole major steps so tick positions stay clean.
 * Returns { lo, hi } (numbers).  spec must have { lo, hi, major }.
 */
export function fixedRange(spec, data) {
  const finite = (data || []).filter(v => v != null && isFinite(v));
  if (!finite.length) return { lo: spec.lo, hi: spec.hi };
  const dMin = Math.min(...finite), dMax = Math.max(...finite);
  let { lo, hi, major } = spec;
  while (lo > dMin) lo -= major;
  while (hi < dMax) hi += major;
  return { lo, hi };
}

/**
 * Generic 2-D SVG chart.
 * series: [{pts:[[x,y],...], color, dash, dots, r, w, opacity}]
 * hlines: [{y, color, dash}]
 * vlines: [{x, color, dash, label}]  — full-height marker lines with a top label
 * band: [x0, x1] — filled background strip
 * NEW options (all optional; defaults preserve existing behaviour):
 *   yMinor:    array of y values for unlabelled minor gridlines
 *   refLines:  [{y|x, label, dash?}] — C5 neutral reference lines (dotted "1 3", --label,
 *              with right-edge text label); y= horizontal, x= vertical
 *   markers:   true — draw r=2 circles at every finite data point (C7)
 *   unscored:  [{x0, x1, label}] — grey-hatch regions outside the scored band (C10)
 *   ariaLabel: string — aria-label for the SVG element
 */
/** Pixel width an SVG will be drawn at (so text and strokes render 1:1, never scaled up). */
export function measuredWidth(svg, fallback) {
  const w = Math.round(svg.getBoundingClientRect().width || svg.parentElement?.getBoundingClientRect().width || 0);
  return w >= 120 ? w : fallback;
}

/** One shared observer: a chart whose own box changes width (grid reflow, late font load, a
 *  details panel opening, the nav collapsing) is redrawn 1:1 at the new width with the options it
 *  was last drawn with, instead of being stretched or squashed by CSS. */
const _chartRO = (typeof ResizeObserver !== "undefined") ? new ResizeObserver(entries => {
  for (const e of entries) {
    const svg = e.target;
    if (!svg.isConnected || !svg._chartOpts) { _chartRO.unobserve(svg); continue; }
    const w = Math.round(e.contentRect.width);
    if (w >= 120 && Math.abs(w - (svg._chartW || 0)) > 2) {
      requestAnimationFrame(() => { if (svg.isConnected && svg._chartOpts) chart(svg, svg._chartOpts); });
    }
  }
}) : null;

export function chart(svg, opts) {
  let { W = 460, H = 240, xlog = false, ylog = false, xlim, ylim,
    xticks, yticks, xlabel, ylabel, band, hlines = [], vlines = [], series, fill,
    yMinor, refLines = [], markers = false, unscored = [], ariaLabel, square = false } = opts;
  svg.innerHTML = "";
  W = measuredWidth(svg, W);
  const m = { l: 44, r: 12, t: ylabel ? 20 : 10, b: 32 };   // unit label sits above the plot, clear of the top tick
  if (square) H = W - m.l - m.r + m.t + m.b;                 // equal-scale axes stay visually equal
  svg._chartOpts = opts; svg._chartW = W;
  if (_chartRO) { try { _chartRO.observe(svg); } catch (_) { /* non-element shims in tests */ } }
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("width", W); svg.setAttribute("height", H);
  if (ariaLabel) { svg.setAttribute("role", "img"); svg.setAttribute("aria-label", ariaLabel); }
  svg.dataset.chart = "1";                      // re-drawn on resize (app.js)
  const tx = xlog ? v => Math.log10(v) : v => v;
  const ty = ylog ? v => (v != null && v > 0 ? Math.log10(v) : null) : v => v;
  const [x0, x1] = xlim.map(tx);
  const [y0raw, y1raw] = ylim;
  const y0 = ty(y0raw) ?? 0, y1 = ty(y1raw) ?? 1;
  const X = v => m.l + (tx(v) - x0) / (x1 - x0) * (W - m.l - m.r);
  const Y = v => { const tv = ty(v); return tv == null ? null : H - m.b - (tv - y0) / (y1 - y0) * (H - m.t - m.b); };
  if (xlog && !xticks) xticks = logTicks(xlim[0], xlim[1]);   // span-derived; explicit callers win
  if (ylog && !yticks) yticks = logTicks(ylim[0], ylim[1]);
  // Clip every plot mark (band, fills, series, marker lines) so nothing draws past the domain
  // into the margins — the old band-rect bleed is gone.
  const clipId = "hl-clip-" + (++_clipSeq);
  const defs = el("defs", {}, svg);
  el("rect", { x: m.l, y: m.t, width: Math.max(0, W - m.l - m.r), height: Math.max(0, H - m.t - m.b) },
     el("clipPath", { id: clipId }, defs));
  // C10: unscored-region hatch pattern
  if (unscored && unscored.length) {
    const hatchId = "hl-hatch-" + _clipSeq;
    const pat = el("pattern", { id: hatchId, x: 0, y: 0, width: 6, height: 6,
      patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" }, defs);
    el("line", { x1: 0, y1: 0, x2: 0, y2: 6, stroke: css("--muted"), "stroke-width": 2, "stroke-opacity": 0.35 }, pat);
    for (const u of unscored) {
      const x0u = Math.max(m.l, X(u.x0)), x1u = Math.min(W - m.r, X(u.x1));
      if (x1u > x0u) {
        el("rect", { x: x0u, y: m.t, width: x1u - x0u, height: H - m.t - m.b,
          fill: `url(#${hatchId})`, "pointer-events": "none" }, svg);
        if (u.label) {
          const lx = (x0u + x1u) / 2;
          const tt = el("text", { x: lx, y: m.t + 11, "text-anchor": "middle",
            style: `fill:${css("--muted")};font-size:9px` }, svg);
          tt.textContent = u.label;
        }
      }
    }
  }
  const plot = el("g", { "clip-path": `url(#${clipId})` }, svg);
  if (fill) for (const f of fill) {
    const fy0 = Y(Math.max(f.y0, y0raw)), fy1 = Y(Math.min(f.y1, y1raw));
    if (fy0 == null || fy1 == null) continue;
    el("rect", { x: m.l, width: W - m.l - m.r, y: Math.min(fy0, fy1), height: Math.max(0, Math.abs(fy0 - fy1)), fill: f.color, opacity: f.opacity ?? 0.12 }, plot);
  }
  if (band) el("rect", { x: X(band[0]), y: m.t, width: Math.max(0, X(band[1]) - X(band[0])), height: H - m.t - m.b, fill: css("--band") }, plot);
  const g = el("g", { class: "grid" }, svg);
  // C1: minor y gridlines (lighter, unlabelled)
  for (const t of (yMinor || [])) {
    if (t > y0raw && t < y1raw) {
      const yt = Y(t); if (yt == null) continue;
      el("line", { x1: m.l, x2: W - m.r, y1: yt, y2: yt, "stroke-opacity": 0.45 }, g);
    }
  }
  for (const t of (yticks || [])) {
    const yt = Y(t); if (yt == null) continue;
    el("line", { x1: m.l, x2: W - m.r, y1: yt, y2: yt }, g);
    const tt = el("text", { x: m.l - 6, y: yt + 3, "text-anchor": "end" }, svg);
    tt.textContent = ylog ? fmtLogTick(t) : t;
  }
  // C1: minor x gridlines for log axis (lighter, unlabelled)
  if (xlog) {
    const { minor: xMinor } = logGrid(xlim[0], xlim[1]);
    for (const t of xMinor) {
      if (t > xlim[0] && t < xlim[1])
        el("line", { x1: X(t), x2: X(t), y1: m.t, y2: H - m.b, "stroke-opacity": 0.3 }, g);
    }
  }
  for (const t of (xticks || [])) {
    el("line", { x1: X(t), x2: X(t), y1: m.t, y2: H - m.b }, g);
    const tt = el("text", { x: X(t), y: H - m.b + 13, "text-anchor": "middle" }, svg);
    tt.textContent = t >= 1000 ? (t / 1000) + "k" : t;
  }
  if (xlabel) { const t = el("text", { x: W - m.r, y: H - 3, "text-anchor": "end" }, svg); t.textContent = xlabel; }
  // Unit label sits above the y axis, left-aligned to the chart edge so long labels never clip.
  if (ylabel) {
    const short = String(ylabel).length * 6.6 <= m.l - 8;     // fits beside the axis: original placement
    const t = el("text", short ? { x: m.l - 6, y: 11, "text-anchor": "end" } : { x: 2, y: 11, "text-anchor": "start" }, svg);
    t.textContent = ylabel;
  }
  for (const h of hlines) {
    const hy = Y(h.y); if (hy == null) continue;
    el("line", { x1: m.l, x2: W - m.r, y1: hy, y2: hy, stroke: h.color, "stroke-width": 1.5, "stroke-dasharray": h.dash ? "5 4" : "none" }, svg);
  }
  // C5: reference lines — dotted "1 3", --label colour, with right-edge text label
  const pw = W - m.l - m.r;
  for (const rl of refLines) {
    if (rl.y != null && isFinite(rl.y)) {
      const rly = Y(rl.y); if (rly == null) continue;
      el("line", { x1: m.l, x2: W - m.r, y1: rly, y2: rly,
        stroke: css("--label"), "stroke-width": 1, "stroke-dasharray": "1 3" }, svg);
      if (rl.label) {
        const tt = el("text", { x: W - m.r - 2, y: rly - 2, "text-anchor": "end",
          style: `fill:${css("--label")};font-size:9px` }, svg);
        tt.textContent = rl.label;
      }
    } else if (rl.x != null && isFinite(rl.x)) {
      const lx = X(rl.x);
      el("line", { x1: lx, x2: lx, y1: m.t, y2: H - m.b,
        stroke: css("--label"), "stroke-width": 1, "stroke-dasharray": "1 3" }, svg);
      if (rl.label) {
        const anchor = (lx - m.l) < 0.12 * pw ? "start" : (lx > W - m.r - 0.12 * pw) ? "end" : "middle";
        const dx = anchor === "start" ? 4 : anchor === "end" ? -4 : 0;
        const tt = el("text", { x: lx + dx, y: m.t + 9, "text-anchor": anchor,
          style: `fill:${css("--label")};font-size:9px` }, svg);
        tt.textContent = rl.label;
      }
    }
  }
  const vlineColor = v => v.color || css("--label");
  for (const v of vlines) {
    if (!isFinite(v.x)) continue;
    const lx = X(v.x);
    el("line", { x1: lx, x2: lx, y1: m.t, y2: H - m.b, stroke: vlineColor(v),
                 "stroke-width": 1.5, "stroke-dasharray": v.dash ? "5 4" : "none" }, plot);
  }
  // clipY clamps in data space (before log transform); y0raw/y1raw are the original ylim values
  const clipY = v => Math.min(Math.max(v, y0raw), y1raw);
  for (const s of series) {
    const pts = s.pts.filter(p => p[1] != null && isFinite(p[1]) && (!ylog || p[1] > 0));
    if (!pts.length) continue;
    if (s.dots) {
      for (const p of pts) {
        const cy = Y(clipY(p[1])); if (cy == null) continue;
        el("circle", { cx: X(p[0]), cy, r: s.r || 2.0, fill: s.color, opacity: s.opacity ?? 0.8 }, plot);
      }
    } else {
      const ppath = pts.map((p, i) => { const cy = Y(clipY(p[1])); return cy == null ? null : (i ? "L" : "M") + X(p[0]).toFixed(1) + "," + cy.toFixed(1); }).filter(Boolean);
      if (ppath.length) el("path", { d: ppath.join(""),
        fill: "none", stroke: s.color, "stroke-width": s.w || 1.8,
        "stroke-dasharray": s.dash ? "5 4" : "none", "stroke-linejoin": "round" }, plot);
      // C7: markers at each solved frequency (r=2 circles above the line)
      if (markers) {
        for (const p of pts) {
          const cy = Y(clipY(p[1])); if (cy == null) continue;
          el("circle", { cx: X(p[0]), cy, r: 2, fill: s.color, opacity: 0.75 }, plot);
        }
      }
    }
  }
  // marker labels sit at the top of the plot; switch anchor near an edge so they never clip
  for (const v of vlines) {
    if (!isFinite(v.x) || !v.label) continue;
    const lx = X(v.x);
    const anchor = (lx - m.l) < 0.12 * pw ? "start" : (lx > W - m.r - 0.12 * pw) ? "end" : "middle";
    const dx = anchor === "start" ? 4 : anchor === "end" ? -4 : 0;
    const col = vlineColor(v);
    const tt = el("text", { x: lx + dx, y: m.t + 11, "text-anchor": anchor,
      style: `fill:${col};paint-order:stroke;stroke:${css("--surface")};stroke-width:3px;stroke-linejoin:round` }, svg);
    tt.textContent = v.label;
  }
}

// ── Shared data-viz kit (2026-11-14) ────────────────────────────────
// One validated categorical palette, one number formatter, and small HTML/SVG marks that any
// view can drop in (sparklines, 100% stacked bars). Colours resolve from app.css tokens so light
// and dark themes each get their own validated steps.

/** Validated categorical order (dataviz validator, 2026-11-14: worst adjacent CVD ΔE 9.1 light on
 *  #ffffff / 8.4 dark on #151d23; normal-vision ≥ 19.3). Light steps double as the no-CSS fallback. */
export const CAT_N = 8;
export const CAT_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];
const _cssSafe = (n) => { try { return css(n); } catch (_) { return ""; } };

/** Categorical colour for slot i (0-based). Never cycles: slots past 8 get the neutral "other". */
export function catColor(i) {
  const k = Number(i);
  if (!Number.isInteger(k) || k < 0 || k >= CAT_N) return _cssSafe("--cat-other") || "#8a96a0";
  return _cssSafe(`--cat-${k + 1}`) || CAT_LIGHT[k];
}

/** Expand [lo, hi] (> 0) outward to the nearest 1-2-5 decade steps, so log-axis end ticks are
 *  round numbers and never collide with an interior tick. */
export function logNiceLimits(lo, hi) {
  lo = Number(lo); hi = Number(hi);
  if (!(lo > 0) || !(hi > 0)) return [lo, hi];
  if (hi < lo) { const t = lo; lo = hi; hi = t; }
  const steps = (e) => [1, 2, 5].map(m => m * Math.pow(10, e));
  let a = lo, b = hi;
  for (let e = Math.floor(Math.log10(lo)); e >= Math.floor(Math.log10(lo)) - 1; e--) {
    const c = steps(e).filter(v => v <= lo * 0.98); if (c.length) { a = +Math.max(...c).toPrecision(3); break; }
  }
  for (let e = Math.floor(Math.log10(hi)); e <= Math.floor(Math.log10(hi)) + 1; e++) {
    const c = steps(e).filter(v => v >= hi * 1.02); if (c.length) { b = +Math.min(...c).toPrecision(3); break; }
  }
  return [a, b];
}

/** Log-axis tick label: 2 significant digits, plain notation (0.5 not 5e-1). */
export function fmtLogTick(t) {
  const n = Number(t);
  if (!isFinite(n)) return "";
  if (n !== 0 && Math.abs(n) < 0.001) return n.toExponential(0);
  const v = +n.toPrecision(2);
  return v >= 1000 ? `${+(v / 1000).toPrecision(2)}k` : String(v);
}

/** Display number with sensible precision for its size: 600 · 12.3 · 2.13 · 0.687. */
export function fmtSmart(v) {
  const n = Number(v);
  if (v == null || v === "" || !isFinite(n)) return "–";
  const a = Math.abs(n);
  const d = a >= 100 ? 0 : a >= 10 ? 1 : a >= 1 ? 2 : 3;
  return fmt(n, d);
}

const _escAttr = (s) => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/** Inline SVG sparkline (string). pts: [[x, y], ...]. log: log10 y (for J-style curves whose
 *  first drop would flatten a linear axis). Ends with a dot on the last value. */
export function sparkline(pts, { W = 140, H = 36, log = false, color = "var(--best)", label = "" } = {}) {
  const P = (pts || []).filter(p => p && isFinite(Number(p[0])) && isFinite(Number(p[1])) && (!log || Number(p[1]) > 0))
    .map(p => [Number(p[0]), log ? Math.log10(Number(p[1])) : Number(p[1])]);
  if (P.length < 2) return "";
  const pad = 3;
  const xs = P.map(p => p[0]), ys = P.map(p => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const X = v => pad + (x1 > x0 ? (v - x0) / (x1 - x0) : 0) * (W - 2 * pad);
  const Y = v => pad + (y1 > y0 ? (y1 - v) / (y1 - y0) : 0.5) * (H - 2 * pad);
  const d = P.map((p, i) => `${i ? "L" : "M"}${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join("");
  const lp = P[P.length - 1];
  const aria = label ? `role="img" aria-label="${_escAttr(label)}"` : `aria-hidden="true"`;
  return `<svg class="spark" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" ${aria}>`
    + `<path d="${d}" fill="none" stroke="${color}" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>`
    + `<circle cx="${X(lp[0]).toFixed(1)}" cy="${Y(lp[1]).toFixed(1)}" r="2.6" fill="${color}"/></svg>`;
}

/** 100% stacked horizontal bar (HTML string). segs: [{value, cls?, color?, title?, label?}].
 *  Widths are value / total (total defaults to the sum). Segments are separated by a 2px surface
 *  gap (.stackbar CSS); a label prints inside a segment only when it is at least minLabelPct wide. */
export function stackBarHtml(segs, { total, cls = "", ariaLabel = "", minLabelPct = 9 } = {}) {
  const S = (segs || []).filter(s => s && isFinite(Number(s.value)) && Number(s.value) > 0);
  const T = isFinite(Number(total)) && Number(total) > 0 ? Number(total) : S.reduce((a, s) => a + Number(s.value), 0);
  if (!(T > 0) || !S.length) return "";
  const body = S.map(s => {
    const w = Math.max(0, Math.min(100, Number(s.value) / T * 100));
    const style = `width:${w.toFixed(2)}%${s.color ? `;background:${s.color}` : ""}`;
    const lab = s.label && w >= minLabelPct ? `<span class="stackbar-lab">${_escAttr(s.label)}</span>` : "";
    return `<span class="stackbar-seg${s.cls ? " " + s.cls : ""}" style="${style}"${s.title ? ` title="${_escAttr(s.title)}"` : ""}>${lab}</span>`;
  }).join("");
  return `<div class="stackbar${cls ? " " + cls : ""}" role="img"${ariaLabel ? ` aria-label="${_escAttr(ariaLabel)}"` : ""}>${body}</div>`;
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
const _gidx = {};
/** Stable colour per group name, in first-seen order (colour follows the entity, never its rank). */
export function groupColor(g) {
  if (!(g in _gidx)) _gidx[g] = Object.keys(_gidx).length;
  return catColor(_gidx[g]);
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
/** Families / design entries share the validated categorical palette (catColor). Past slot 8 an
 *  entry folds to the neutral "other" colour instead of re-using a hue (legends carry the name). */
export const FAMILY_COLORS = CAT_LIGHT;
export function familyColor(i) { return catColor(i); }

/** Wall cross-section, true aspect: H plane to the right (+r), V plane mirrored left (−r), depth z up.
 *  designs: [{profile: {h: [[z, r]...], v: [...], kind}, color, label, filled}]. Section outlines
 *  (kind 'section') are drawn as closed shapes; node clouds (kind 'nodes') as small dots. */
/**
 * Complete a symmetry-reduced mouth ring for display. The mesh payload is a QUARTER (quadrants
 * "1"), a HALF, or already FULL, and the frames payload does not always say which — so decide
 * from the points themselves: an arc living in one quadrant is mirrored into all four (order
 * preserved, so the drawn ring never self-intersects); a ring spanning one axis is mirrored
 * across that axis; a ring already spanning both axes is returned untouched. Pure. Used by the
 * evolution front view and the typology sandbox.
 */
export function mirrorRing(pts) {
  const p = (pts || []).filter(q => Array.isArray(q) && q.length >= 2 && isFinite(q[0]) && isFinite(q[1]));
  if (p.length < 2) return p;
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const [x, y] of p) {
    minX = Math.min(minX, x); maxX = Math.max(maxX, x);
    minY = Math.min(minY, y); maxY = Math.max(maxY, y);
  }
  const eps = 1e-6 * Math.max(1, Math.abs(maxX), Math.abs(minX), Math.abs(maxY), Math.abs(minY));
  const spansX = minX < -eps && maxX > eps, spansY = minY < -eps && maxY > eps;
  if (spansX && spansY) return p;                                        // already a full ring
  const rev = a => a.slice().reverse();
  if (spansX) return p.concat(rev(p).map(([x, y]) => [x, -y]));          // half: mirror across x
  if (spansY) return p.concat(rev(p).map(([x, y]) => [-x, y]));          // half: mirror across y
  // quarter arc -> closed ring around all four quadrants, traversed CCW
  return p
    .concat(rev(p).map(([x, y]) => [-x, y]))
    .concat(p.map(([x, y]) => [-x, -y]))
    .concat(rev(p).map(([x, y]) => [x, -y]));
}

export function wallSection(svg, designs, { H = 300, compact = false, extent = null } = {}) {
  svg.innerHTML = "";
  const W = measuredWidth(svg, compact ? 150 : 460);
  const m = compact ? { l: 4, r: 4, t: 4, b: 4 } : { l: 46, r: 10, t: 10, b: 34 };
  let rmax = 1, z0 = Infinity, z1 = -Infinity;
  for (const d of designs) for (const k of ["h", "v"]) for (const [z, r] of (d.profile?.[k] || [])) {
    rmax = Math.max(rmax, Math.abs(r)); z0 = Math.min(z0, z); z1 = Math.max(z1, z);
  }
  if (extent) ({ rmax, z0, z1 } = extent);              // shared scale across several drawings
  if (!isFinite(z0)) { svg.setAttribute("viewBox", `0 0 ${W} ${H}`); return; }
  const pw = W - m.l - m.r, ph = H - m.t - m.b;
  const noDash = W < 260;                               // dashed strokes read as texture mush below 260px
  const sc = Math.min(pw / (2 * rmax * 1.02), ph / ((z1 - z0) * 1.02));        // equal mm per pixel, true aspect
  const cx = m.l + pw / 2, by = m.t + ph - (ph - (z1 - z0) * sc) / 2;
  const X = r => cx + r * sc, Y = z => by - (z - z0) * sc;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("width", W); svg.setAttribute("height", H);
  svg.dataset.chart = "1";
  const outline = (d, k, sgn) => {
    const pts = (d.profile || {})[k] || [];
    if (pts.length < 3) return null;
    return pts.map(([z, r], i) => (i ? "L" : "M") + X(sgn * r).toFixed(1) + "," + Y(z).toFixed(1)).join("") + "Z";
  };

  // pass 1: grid, ticks, axis labels, centerline
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
    // plane labels live in the true-aspect slack beside the drawing, at mid-height
    const a = el("text", { x: W - m.r, y: m.t + ph / 2, "text-anchor": "end" }, svg); a.textContent = "horizontal plane →";
    const b = el("text", { x: m.l + 2, y: m.t + ph / 2, "text-anchor": "start" }, svg); b.textContent = "← vertical plane";
    const c = el("text", { x: 2, y: m.t + 2, "dominant-baseline": "hanging" }, svg); c.textContent = "depth z (mm)";
  }
  if (W >= 200) el("line", { x1: cx, x2: cx, y1: m.t, y2: m.t + ph, stroke: css("--label"),
                             "stroke-dasharray": "3 3", "stroke-opacity": 0.6, "stroke-width": 1 }, svg);

  // pass 2: ALL fills beneath every stroke; even-odd fills the wall band, bore stays background
  for (const d of designs) {
    if (!d.filled || (d.profile || {}).kind !== "section") continue;
    for (const [k, sgn] of [["h", 1], ["v", -1]]) {
      const path = outline(d, k, sgn);
      if (!path) continue;
      el("path", { d: path, fill: d.color, "fill-rule": "evenodd", "fill-opacity": compact ? 0.32 : 0.30, stroke: "none" }, svg);
    }
  }

  // pass 3: strokes, with the dashed (start) outline LAST so it reads over any fill
  const drawStroke = d => {
    const p = d.profile || {};
    for (const [k, sgn] of [["h", 1], ["v", -1]]) {
      const pts = p[k] || [];
      if (!pts.length) continue;
      if (p.kind === "section") {
        const path = outline(d, k, sgn);
        if (!path) continue;
        // H solid / V dashed on the drawing itself; a design-level dash (start) dashes both planes
        const dash = (!noDash && (d.dash || k === "v")) ? "6 4" : "none";
        el("path", { d: path, fill: "none", stroke: d.color,
                     "stroke-width": compact ? 1.6 : (k === "h" ? 2.25 : 2.0),
                     "stroke-dasharray": dash, "stroke-linejoin": "round" }, svg);
      } else {
        for (const [z, r] of pts) el("circle", { cx: X(sgn * r), cy: Y(z), r: compact ? 0.8 : 1.4, fill: d.color, opacity: 0.7 }, svg);
      }
    }
  };
  const dashed = designs.filter(d => d.dash), solid = designs.filter(d => !d.dash);
  for (const d of solid) drawStroke(d);
  for (const d of dashed) drawStroke(d);

  // throat landmark: the outline's min-z point with |r| > 0 (the aperture's axis end); else min z
  for (const d of designs) {
    const p = d.profile || {};
    for (const [k, sgn] of [["h", 1], ["v", -1]]) {
      const pts = p[k] || [];
      if (!pts.length) continue;
      const withR = pts.filter(pt => pt[1] != null && Math.abs(pt[1]) > 1e-9);
      const pool = withR.length ? withR : pts;
      let tz = pool[0][0], tr = pool[0][1];
      for (const [z, r] of pool) if (z < tz) { tz = z; tr = r; }
      el("circle", { cx: X(sgn * Math.abs(tr)), cy: Y(tz), r: compact ? 1.5 : 2.5, fill: d.color, stroke: "none" }, svg);
    }
  }
}

// ── Isobar (directivity) plot in the Boundary Lab style ───────────────────────────────────────────
// Frequency on a log x-axis, angle on y, level relative to on-axis in DISCRETE 3 dB colour bands from
// -30 to 0 dB (10 bands, navy -> dark red), white contour lines every 3 dB (-6 dB drawn heavier: the
// beamwidth edge), a labelled colour bar, and a hover crosshair that reads frequency / angle / dB.
// ── Directivity isobar map (v3, 2026-11-14) ─────────────────────────────────────────────────
// Classic 3 dB rainbow bands (the convention of ARTA / CLIO / VituixCAD maps, kept at the owner's
// request) with a hairline contour between every band and a slightly heavier −6 dB beamwidth edge.
// Clean frame: ticks sit outside, no grid over the data, one shared scale for a set of maps.

export const ISOBAR_MIN = -30, ISOBAR_MAX = 0, ISOBAR_STEP = 3;
const _N_BANDS = (ISOBAR_MAX - ISOBAR_MIN) / ISOBAR_STEP;
/** The ten 3 dB band colours, quietest first (also the 3D balloon's ramp: one scale, two views). */
export const ISOBAR_COLORS = ["#00008F", "#0000FF", "#006FFF", "#00DFFF", "#4FFFBF",
                              "#BFFF4F", "#FFDF00", "#FF6F00", "#FF0000", "#8F0000"];
const _BAND_RGB = ISOBAR_COLORS.map(h => { const n = parseInt(h.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; });
// C8 over-range: an off-axis lobe more than OVER_MIN dB louder than on-axis. 0..+1 dB stays in the
// top band: the map is normalised to 0° per frequency, so a sub-dB excess is a tiny on-axis dip.
export const OVER_RANGE_COLOR = "#FFB0C8", OVER_MIN = 1;

function isoRGB(v) {
  if (v > OVER_MIN) return [255, 176, 200];
  if (v < ISOBAR_MIN) return _BAND_RGB[0];
  return _BAND_RGB[Math.min(_N_BANDS - 1, Math.floor((Math.min(v, ISOBAR_MAX - 1e-9) - ISOBAR_MIN) / ISOBAR_STEP))];
}

/** Bilinear sample of rows[fi][ai] at fractional indices (fi, ai). */
function sample(rows, fi, ai) {
  const f0 = Math.max(0, Math.min(rows.length - 1, Math.floor(fi))), f1 = Math.min(rows.length - 1, f0 + 1);
  const a0 = Math.max(0, Math.min(rows[0].length - 1, Math.floor(ai))), a1 = Math.min(rows[0].length - 1, a0 + 1);
  const tf = fi - f0, ta = ai - a0;
  const g = (f, a) => { const v = rows[f][a]; return v == null ? ISOBAR_MIN - 10 : v; };
  return (g(f0, a0) * (1 - ta) + g(f0, a1) * ta) * (1 - tf) + (g(f1, a0) * (1 - ta) + g(f1, a1) * ta) * tf;
}

// Marching-squares segment table: which cell edges a contour crosses for each corner pattern.
const MS = { 1: ["l", "t"], 2: ["t", "r"], 3: ["l", "r"], 4: ["r", "b"], 5: ["l", "t", "r", "b"], 6: ["t", "b"], 7: ["l", "b"],
             8: ["l", "b"], 9: ["t", "b"], 10: ["t", "r", "l", "b"], 11: ["r", "b"], 12: ["l", "r"], 13: ["t", "r"], 14: ["l", "t"] };

/** Marching-squares contour of a regular grid (row-major vals, NaN = no data) at level L, as an
 *  SVG path. Cell (px, py) centre maps to (ox + (px + 0.5) * sx, oy + (py + 0.5) * sy). Shared by
 *  isobarMap and globePlot so both draw the same −6 dB edge. */
function _msPath(vals, cw, chh, L, ox, oy, sx, sy) {
  let d = "";
  for (let py = 0; py < chh - 1; py++) for (let px = 0; px < cw - 1; px++) {
    const v0 = vals[py * cw + px], v1 = vals[py * cw + px + 1], v2 = vals[(py + 1) * cw + px + 1], v3 = vals[(py + 1) * cw + px];
    if (!isFinite(v0) || !isFinite(v1) || !isFinite(v2) || !isFinite(v3)) continue;
    const c = (v0 > L) | ((v1 > L) << 1) | ((v2 > L) << 2) | ((v3 > L) << 3);
    if (c === 0 || c === 15) continue;
    const it = (va, vb) => (L - va) / (vb - va);
    const P = { t: () => [px + it(v0, v1), py], r: () => [px + 1, py + it(v1, v2)],
                b: () => [px + it(v3, v2), py + 1], l: () => [px, py + it(v0, v3)] };
    const segs = MS[c];
    for (let k = 0; k < segs.length; k += 2) {
      const p1 = P[segs[k]](), p2 = P[segs[k + 1]]();
      d += "M" + (ox + (p1[0] + 0.5) * sx).toFixed(1) + "," + (oy + (p1[1] + 0.5) * sy).toFixed(1) +
           "L" + (ox + (p2[0] + 0.5) * sx).toFixed(1) + "," + (oy + (p2[1] + 0.5) * sy).toFixed(1);
    }
  }
  return d;
}

/** Draw the isobar contour set into `parent`: a white hairline between every 3 dB band, the −6 dB
 *  beamwidth edge a little heavier, and a dotted outline round any lobe above +1 dB. */
function _isoContours(parent, vals, cw, chh, vmax, ox, oy, sx, sy) {
  for (let L = ISOBAR_MIN + ISOBAR_STEP; L < ISOBAR_MAX; L += ISOBAR_STEP) {
    const d = _msPath(vals, cw, chh, L, ox, oy, sx, sy);
    if (!d) continue;
    const edge = L === -6;
    el("path", { d, fill: "none", stroke: "#ffffff", "stroke-opacity": edge ? 0.95 : 0.6,
                 "stroke-width": edge ? 1.1 : 0.5, "stroke-linejoin": "round" }, parent);
  }
  if (vmax > OVER_MIN) {
    const d = _msPath(vals, cw, chh, OVER_MIN, ox, oy, sx, sy);
    if (d) el("path", { d, fill: "none", stroke: "#ffffff", "stroke-opacity": 0.9, "stroke-width": 0.7, "stroke-dasharray": "1.5 1.5" }, parent);
  }
}

/** Shared legend for a set of isobar maps (HTML string): the band scale once, plus the line keys.
 *  Use with isobarMap(..., { legend: false }) so small multiples do not each repeat a colour bar. */
export function isobarLegendHtml({ target = false, f0 = false, over = false } = {}) {
  const sw = ISOBAR_COLORS.slice().reverse();          // loud → quiet, left → right
  const ticks = [];
  for (let L = ISOBAR_MAX; L >= ISOBAR_MIN; L -= 6) ticks.push(L);
  const bar = `<span class="iso-scale">${sw.map(c => `<i style="background:${c}"></i>`).join("")}</span>`;
  const lab = `<span class="iso-scale-lab">${ticks.map(L => `<span>${L === 0 ? "0" : "−" + Math.abs(L)}</span>`).join("")}</span>`;
  const keys = [
    `<span class="iso-key"><svg width="22" height="8" aria-hidden="true"><line x1="0" x2="22" y1="4" y2="4" stroke="currentColor" stroke-width="1.1"/></svg>−6 dB beamwidth edge (thin lines: every 3 dB)</span>`,
    target ? `<span class="iso-key"><svg width="22" height="8" aria-hidden="true"><line x1="0" x2="22" y1="4" y2="4" stroke="currentColor" stroke-width="0.9" stroke-dasharray="4 3"/></svg>coverage target</span>` : "",
    f0 ? `<span class="iso-key iso-key-f0"><svg width="22" height="8" aria-hidden="true"><line x1="11" x2="11" y1="0" y2="8" stroke="currentColor" stroke-width="1" stroke-dasharray="2 2"/></svg>f0 scoring floor</span>` : "",
    over ? `<span class="iso-key"><i class="iso-over" style="background:${OVER_RANGE_COLOR}"></i>off-axis lobe &gt; +1 dB</span>` : "",
  ].filter(Boolean).join("");
  return `<div class="iso-legend"><div class="iso-scale-wrap"><span class="iso-unit">dB re on-axis</span>${bar}${lab}</div><div class="iso-keys">${keys}</div></div>`;
}

/** Directivity isobar map (sonogram): level re on-axis vs log frequency (x) and angle (y).
 *  Options: title; H; angleTicks (default ±90 in 30° steps); xlim (axis domain, colour only over the
 *  solved grid); f0 (scoring floor, Hz); target (full coverage angle, deg → ±target/2 guides);
 *  legend (default true: a slim per-map scale; false when a shared isobarLegendHtml() is shown). */
export function isobarMap(svg, rows, angles, freqs, { H = 300, title = "", angleTicks = null, xlim, f0, target, legend = true } = {}) {
  svg.innerHTML = "";
  if (!rows || !rows.length || !angles || !angles.length || !freqs || freqs.length < 2) return;
  const W = measuredWidth(svg, 520);
  const ink = css("--ink") || "#15202a", muted = css("--muted") || "#5a6873", rule = css("--rule") || "#a9b4bb";
  const tg = Number(target), hasTarget = isFinite(tg) && tg > 0;
  const hasF0 = isFinite(Number(f0)) && Number(f0) > 0;
  const m = { l: 46, r: legend ? 64 : (hasTarget ? 34 : 12), t: (title ? 22 : 10) + (hasF0 ? 12 : 0), b: 34 };
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("width", W); svg.setAttribute("height", H);
  svg.dataset.chart = "1";
  const pw = W - m.l - m.r, ph = H - m.t - m.b;
  // Axis domain: the brief-band union when supplied; otherwise the solved grid. Invalid/zero
  // values fall back to the data domain, never to a guessed range.
  const dataLo = Number(freqs[0]), dataHi = Number(freqs[freqs.length - 1]);
  let dLo = dataLo, dHi = dataHi;
  if (Array.isArray(xlim) && xlim.length >= 2) {
    const a = Number(xlim[0]), b = Number(xlim[1]);
    if (isFinite(a) && isFinite(b) && a > 0 && b > 0 && b > a) { dLo = a; dHi = b; }
  }
  if (!(isFinite(dataLo) && isFinite(dataHi) && dataLo > 0 && dataHi > dataLo)) return;
  if (!(isFinite(dLo) && isFinite(dHi) && dLo > 0 && dHi > dLo)) { dLo = dataLo; dHi = dataHi; }
  const lf = freqs.map(Math.log10), lf0 = lf[0], lf1 = lf[lf.length - 1];
  const xlo = Math.log10(dLo), xhi = Math.log10(dHi);
  const a0 = angles[0], a1 = angles[angles.length - 1];
  const X = f => m.l + (Math.log10(f) - xlo) / (xhi - xlo) * pw;
  const Y = a => m.t + (a1 - a) / (a1 - a0) * ph;                     // +90 at the top
  const fIndex = l => { let i = 0; while (i < lf.length - 2 && l > lf[i + 1]) i++; return i + Math.max(0, Math.min(1, (l - lf[i]) / (lf[i + 1] - lf[i]))); };
  const aIndex = a => (a - a0) / (a1 - a0) * (angles.length - 1);
  const tol = 1e-9 * Math.max(1, Math.abs(lf0), Math.abs(lf1));
  const solvedAt = lg => lg >= lf0 - tol && lg <= lf1 + tol;

  // contour grid (~2 screen px per cell) for the −6 dB edge and the over-range outline
  const cw = Math.max(80, Math.round(pw / 2)), chh = Math.max(60, Math.round(ph / 2));
  const vals = new Float32Array(cw * chh);
  let vmax = -Infinity;
  for (let py = 0; py < chh; py++) {
    const ai = aIndex(a1 - (py + 0.5) / chh * (a1 - a0));
    for (let px = 0; px < cw; px++) {
      const lg = xlo + (px + 0.5) / cw * (xhi - xlo);
      const v = solvedAt(lg) ? sample(rows, fIndex(lg), ai) : NaN;   // unsolved margin: NaN, skipped
      vals[py * cw + px] = v;
      if (v > vmax) vmax = v;
    }
  }
  // filled bands at device resolution (smooth edges); the unsolved margin stays transparent
  const dpr = Math.max(1, Math.min(2, (typeof window !== "undefined" && window.devicePixelRatio) || 1));
  const fw = Math.max(80, Math.min(1800, Math.round(pw * dpr))), fh = Math.max(60, Math.min(1000, Math.round(ph * dpr)));
  const cv = document.createElement("canvas"); cv.width = fw; cv.height = fh;
  const ctx = cv.getContext("2d"), img = ctx.createImageData(fw, fh);
  for (let py = 0; py < fh; py++) {
    const ai = aIndex(a1 - (py + 0.5) / fh * (a1 - a0));
    for (let px = 0; px < fw; px++) {
      const lg = xlo + (px + 0.5) / fw * (xhi - xlo);
      if (!solvedAt(lg)) continue;
      const c = isoRGB(sample(rows, fIndex(lg), ai)), o = (py * fw + px) * 4;
      img.data[o] = c[0]; img.data[o + 1] = c[1]; img.data[o + 2] = c[2]; img.data[o + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  const clipId = "hl-iso-clip-" + (++_clipSeq);
  const defs = el("defs", {}, svg);
  el("rect", { x: m.l, y: m.t, width: pw, height: ph }, el("clipPath", { id: clipId }, defs));
  const clipped = el("g", { "clip-path": `url(#${clipId})` }, svg);
  el("image", { href: cv.toDataURL(), x: m.l, y: m.t, width: pw, height: ph, preserveAspectRatio: "none" }, clipped);

  // contours: hairline between every band, −6 dB heavier, dotted > +1 dB outline
  _isoContours(clipped, vals, cw, chh, vmax, m.l, m.t, pw / cw, ph / chh);
  // coverage target: thin dashed guides the −6 dB edge should follow; labelled in the right margin
  if (hasTarget) {
    for (const a of [tg / 2, -tg / 2]) {
      if (a < a0 || a > a1) continue;
      el("line", { x1: m.l, x2: m.l + pw, y1: Y(a), y2: Y(a), stroke: "#ffffff", "stroke-opacity": 0.95,
                   "stroke-width": 0.9, "stroke-dasharray": "4 3" }, clipped);
      if (!legend) el("text", { x: m.l + pw + 4, y: Y(a) + 3, style: `fill:${muted};font-size:9px` }, svg).textContent =
        `${a > 0 ? "+" : "−"}${+Math.abs(a).toFixed(1)}°`;
    }
  }

  // Boundary Lab frame: grey grid over the data, labels outside, solved frequencies ticked below
  const g = el("g", {}, svg);
  const { minor: xMinorIso } = logGrid(dLo, dHi);
  for (const t of xMinorIso) {
    if (t <= dLo || t >= dHi) continue;
    el("line", { x1: X(t), x2: X(t), y1: m.t, y2: m.t + ph, stroke: "#808080", "stroke-opacity": 0.3, "stroke-width": 0.6 }, g);
  }
  for (const t of logTicks(dLo, dHi)) {
    el("line", { x1: X(t), x2: X(t), y1: m.t, y2: m.t + ph, stroke: "#808080", "stroke-opacity": 0.6, "stroke-width": 0.8 }, g);
    el("text", { x: X(t), y: m.t + ph + 14, "text-anchor": "middle" }, svg).textContent = t >= 1000 ? t / 1000 + "k" : t;
  }
  for (const a of (angleTicks || [-90, -60, -30, 0, 30, 60, 90])) {
    if (a < a0 || a > a1) continue;
    el("line", { x1: m.l, x2: m.l + pw, y1: Y(a), y2: Y(a), stroke: "#808080", "stroke-opacity": a === 0 ? 0.8 : 0.6, "stroke-width": 0.8 }, g);
    el("text", { x: m.l - 6, y: Y(a) + 3, "text-anchor": "end" }, svg).textContent = (a > 0 ? "+" : "") + a + "°";
  }
  el("rect", { x: m.l, y: m.t, width: pw, height: ph, fill: "none", stroke: rule }, svg);
  el("text", { x: m.l + pw / 2, y: H - 4, "text-anchor": "middle" }, svg).textContent = "Frequency (Hz)";
  // C9: solved-frequency tick marks below the x axis
  for (const f of freqs) {
    if (f <= dLo || f >= dHi) continue;
    el("line", { x1: X(f), x2: X(f), y1: m.t + ph, y2: m.t + ph + 4, stroke: muted, "stroke-width": 1 }, svg);
  }
  // scoring floor: thin dashed marker, label in the top margin
  const f0n = Number(f0);
  if (hasF0 && f0n >= dLo && f0n <= dHi) {
    const lx = X(f0n);
    el("line", { x1: lx, x2: lx, y1: m.t, y2: m.t + ph, stroke: "#ffffff", "stroke-opacity": 0.8,
                 "stroke-width": 0.8, "stroke-dasharray": "2 2" }, clipped);
    const anchor = (lx - m.l) < 0.12 * pw ? "start" : (lx > m.l + pw - 0.12 * pw) ? "end" : "middle";
    el("text", { x: lx + (anchor === "start" ? -2 : anchor === "end" ? 2 : 0), y: m.t - 3, "text-anchor": anchor,
      style: `fill:${muted};font-size:9px` }, svg).textContent = `f0 ${Number.isInteger(f0n) ? f0n : +f0n.toFixed(1)} Hz`;
  }
  if (title) el("text", { x: m.l, y: 13, class: "iso-title" }, svg).textContent = title;

  // slim per-map scale (omitted when a shared isobarLegendHtml() sits above a set of maps)
  if (legend) {
    const bx = m.l + pw + 12, bw = 12, bandH = ph / _N_BANDS;
    ISOBAR_COLORS.forEach((c, i) => el("rect", { x: bx, y: m.t + ph - (i + 1) * bandH, width: bw, height: bandH + 0.4, fill: c }, svg));
    for (let L = ISOBAR_MIN; L <= ISOBAR_MAX; L += ISOBAR_STEP) {
      const y = m.t + ph - (L - ISOBAR_MIN) / (ISOBAR_MAX - ISOBAR_MIN) * ph;
      el("line", { x1: bx + bw, x2: bx + bw + 3, y1: y, y2: y, stroke: muted }, svg);
      el("text", { x: bx + bw + 5, y: y + 3 }, svg).textContent = String(L);
    }
    el("text", { x: bx, y: m.t - 4, style: `fill:${muted};font-size:9px` }, svg).textContent = "dB";
    if (vmax > OVER_MIN) {
      el("rect", { x: bx, y: m.t - 16, width: bw, height: 6, fill: OVER_RANGE_COLOR }, svg);
      el("text", { x: bx + bw + 5, y: m.t - 10, style: `fill:${muted};font-size:9px` }, svg).textContent = ">+1";
    }
  }

  // hover crosshair with a frequency / angle / level readout
  const cross = el("g", { style: "pointer-events:none;display:none" }, svg);
  const vl = el("line", { stroke: "#fff", "stroke-opacity": 0.8, "stroke-width": 0.75 }, cross);
  const hl = el("line", { stroke: "#fff", "stroke-opacity": 0.8, "stroke-width": 0.75 }, cross);
  const box = el("rect", { rx: 3, fill: "rgba(11,15,20,0.85)" }, cross);
  const txt = el("text", { style: "fill:#fff;font-size:10.5px" }, cross);
  const hit = el("rect", { x: m.l, y: m.t, width: pw, height: ph, fill: "transparent", style: "cursor:crosshair" }, svg);
  const move = ev => {
    const r = svg.getBoundingClientRect(), k = W / r.width;
    const x = (ev.clientX - r.left) * k, y = (ev.clientY - r.top) * k;
    if (x < m.l || x > m.l + pw || y < m.t || y > m.t + ph) { cross.style.display = "none"; return; }
    const f = Math.pow(10, xlo + (x - m.l) / pw * (xhi - xlo)), a = a1 - (y - m.t) / ph * (a1 - a0);
    const lg = Math.log10(f), solved = solvedAt(lg);
    const v = solved ? sample(rows, fIndex(lg), aIndex(a)) : null;
    vl.setAttribute("x1", x); vl.setAttribute("x2", x); vl.setAttribute("y1", m.t); vl.setAttribute("y2", m.t + ph);
    hl.setAttribute("x1", m.l); hl.setAttribute("x2", m.l + pw); hl.setAttribute("y1", y); hl.setAttribute("y2", y);
    txt.textContent = (f >= 1000 ? (f / 1000).toFixed(2) + " kHz" : Math.round(f) + " Hz") + " · " +
      (a >= 0 ? "+" : "") + a.toFixed(0) + "° · " +
      (solved ? (v < ISOBAR_MIN ? "below " + ISOBAR_MIN : v.toFixed(1)) + " dB" : "no solved data");
    const tx = x + 180 > m.l + pw ? x - 176 : x + 10, ty = y < m.t + 24 ? y + 22 : y - 8;
    txt.setAttribute("x", tx + 6); txt.setAttribute("y", ty);
    box.setAttribute("x", tx); box.setAttribute("y", ty - 12); box.setAttribute("width", 166); box.setAttribute("height", 17);
    cross.style.display = "";
  };
  hit.addEventListener("mousemove", move);
  hit.addEventListener("mouseleave", () => { cross.style.display = "none"; });
}

/** ── Globe plot (polar sonogram), 2026-11-14 ─────────────────────────────────────────────────
 *  The same level-vs-angle-vs-frequency data as isobarMap, wrapped into a circle: direction around
 *  the circle (0° = front, pointing down; +90° to the right; ±180° = back at the top), log frequency
 *  along the radius (lowest solved frequency at the centre, highest at the rim), level as the same
 *  3 dB isobar bands. Data spanning ±90° draws as the front half-globe; wider data fills more of
 *  the circle. Same lines as the rectangular map: −6 dB edge, coverage-target rays, f0 ring.
 *  Options: title, H (max height), target (full coverage angle, deg), f0 (Hz), legend (slim scale).
 */
export function globePlot(svg, rows, angles, freqs, { H = 360, title = "", target, f0, legend = true } = {}) {
  svg.innerHTML = "";
  if (!rows || !rows.length || !angles || angles.length < 2 || !freqs || freqs.length < 2) return;
  const W = measuredWidth(svg, 420);
  const muted = css("--muted") || "#5a6873", rule = css("--rule") || "#a9b4bb";
  const a0 = Number(angles[0]), a1 = Number(angles[angles.length - 1]);
  const lf = freqs.map(Number).map(Math.log10), lf0 = lf[0], lf1 = lf[lf.length - 1];
  if (!(isFinite(lf0) && isFinite(lf1) && lf1 > lf0 && a1 > a0)) return;
  const half = a0 >= -90 - 1e-6 && a1 <= 90 + 1e-6;           // front hemisphere only
  const top = (title ? 20 : 6), labPad = 18;                     // rim labels need room
  const sideR = (W - (legend ? 48 : 8) - 2 * labPad) / 2;
  const R = Math.max(60, Math.min(sideR, half ? H - top - 2 * labPad : (H - top - 2 * labPad) / 2));
  const cx = labPad + R + 4, cy = top + labPad + (half ? 0 : R);
  const Ht = Math.round(cy + R + labPad + 4);
  svg.setAttribute("viewBox", `0 0 ${W} ${Ht}`); svg.setAttribute("width", W); svg.setAttribute("height", Ht);
  svg.dataset.chart = "1";
  // screen direction of an angle: 0° down, +90° right, ±180° up
  const dir = a => { const t = a * Math.PI / 180; return [Math.sin(t), Math.cos(t)]; };
  const rOf = f => (Math.log10(f) - lf0) / (lf1 - lf0) * R;
  const fIndex = l => { let i = 0; while (i < lf.length - 2 && l > lf[i + 1]) i++; return i + Math.max(0, Math.min(1, (l - lf[i]) / (lf[i + 1] - lf[i]))); };
  const aIndex = a => (a - a0) / (a1 - a0) * (angles.length - 1);
  // pixel → (angle, log f), or null outside the solved wedge/disc
  const polarAt = (x, y) => {
    const dx = x - cx, dy = y - cy, r = Math.hypot(dx, dy);
    if (r > R) return null;
    const a = Math.atan2(dx, dy) * 180 / Math.PI;             // 0 at +y (down), +90 at +x
    if (a < a0 - 1e-6 || a > a1 + 1e-6) return null;
    return { a, lg: lf0 + r / R * (lf1 - lf0) };
  };
  const bx0 = cx - R, by0 = half ? cy : cy - R, bw = 2 * R, bh = half ? R : 2 * R;

  // contour grid (~2 px per cell) and level maximum
  const cw = Math.max(60, Math.round(bw / 2)), chh = Math.max(30, Math.round(bh / 2));
  const vals = new Float32Array(cw * chh);
  let vmax = -Infinity;
  for (let py = 0; py < chh; py++) for (let px = 0; px < cw; px++) {
    const p = polarAt(bx0 + (px + 0.5) * bw / cw, by0 + (py + 0.5) * bh / chh);
    const v = p ? sample(rows, fIndex(p.lg), aIndex(p.a)) : NaN;
    vals[py * cw + px] = v;
    if (v > vmax) vmax = v;
  }
  // filled bands at device resolution
  const dpr = Math.max(1, Math.min(2, (typeof window !== "undefined" && window.devicePixelRatio) || 1));
  const fw = Math.max(60, Math.min(1600, Math.round(bw * dpr))), fh = Math.max(30, Math.min(1600, Math.round(bh * dpr)));
  const cv = document.createElement("canvas"); cv.width = fw; cv.height = fh;
  const ctx = cv.getContext("2d"), img = ctx.createImageData(fw, fh);
  for (let py = 0; py < fh; py++) for (let px = 0; px < fw; px++) {
    const p = polarAt(bx0 + (px + 0.5) * bw / fw, by0 + (py + 0.5) * bh / fh);
    if (!p) continue;
    const c = isoRGB(sample(rows, fIndex(p.lg), aIndex(p.a))), o = (py * fw + px) * 4;
    img.data[o] = c[0]; img.data[o + 1] = c[1]; img.data[o + 2] = c[2]; img.data[o + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  el("image", { href: cv.toDataURL(), x: bx0, y: by0, width: bw, height: bh, preserveAspectRatio: "none" }, svg);
  const g = el("g", {}, svg);

  // frequency rings (faint) at the 1-2-5 ticks, labelled along the +90° edge
  for (const t of logTicks(Math.pow(10, lf0), Math.pow(10, lf1))) {
    const r = rOf(t);
    if (!(r > 2 && r < R - 2)) continue;
    const [sx0, sy0] = dir(a0), [sx1, sy1] = dir(a1);
    const large = (a1 - a0) > 180 ? 1 : 0;
    el("path", { d: `M${(cx + r * sx0).toFixed(1)},${(cy + r * sy0).toFixed(1)}A${r.toFixed(1)},${r.toFixed(1)} 0 ${large} 0 ${(cx + r * sx1).toFixed(1)},${(cy + r * sy1).toFixed(1)}`,
      fill: "none", stroke: "#ffffff", "stroke-opacity": 0.28, "stroke-width": 0.6 }, g);
    if (half) el("text", { x: cx + r, y: cy - 4, "text-anchor": "middle", style: `fill:${muted};font-size:9px` }, svg).textContent = fmtLogTick(t);
  }
  if (half) el("text", { x: cx, y: cy - 4, "text-anchor": "middle", style: `fill:${muted};font-size:9px` }, svg).textContent = fmtLogTick(Math.pow(10, lf0));
  // spokes every 30° (faint) with rim labels
  for (let a = Math.ceil(a0 / 30) * 30; a <= a1 + 1e-6; a += 30) {
    const [sx, sy] = dir(a);
    if (a !== a0 && a !== a1) el("line", { x1: cx, y1: cy, x2: cx + R * sx, y2: cy + R * sy, stroke: "#ffffff", "stroke-opacity": 0.22, "stroke-width": 0.6 }, g);
    const lx = cx + (R + 10) * sx, ly = cy + (R + 10) * sy + 3;
    el("text", { x: lx, y: ly, "text-anchor": Math.abs(sx) < 0.2 ? "middle" : sx > 0 ? "start" : "end",
      style: `fill:${muted};font-size:9.5px` }, svg).textContent = (a > 0 ? "+" : a < 0 ? "−" : "") + Math.abs(a) + "°";
  }
  // rim and (half-globe) diameter
  const [rx0, ry0] = dir(a0), [rx1, ry1] = dir(a1);
  el("path", { d: half
      ? `M${cx - R},${cy}A${R},${R} 0 0 0 ${cx + R},${cy}Z`
      : `M${(cx + R * rx0).toFixed(1)},${(cy + R * ry0).toFixed(1)}A${R},${R} 0 ${(a1 - a0) > 180 ? 1 : 0} 0 ${(cx + R * rx1).toFixed(1)},${(cy + R * ry1).toFixed(1)}`,
    fill: "none", stroke: rule, "stroke-width": 0.75 }, svg);

  // −6 dB edge, over-range outline, f0 ring, target rays
  const sxC = bw / cw, syC = bh / chh;
  _isoContours(svg, vals, cw, chh, vmax, bx0, by0, sxC, syC);
  const f0n = Number(f0);
  if (isFinite(f0n) && f0n > 0 && Math.log10(f0n) > lf0 && Math.log10(f0n) < lf1) {
    const r = rOf(f0n), [sx0, sy0] = dir(a0), [sx1, sy1] = dir(a1);
    el("path", { d: `M${(cx + r * sx0).toFixed(1)},${(cy + r * sy0).toFixed(1)}A${r.toFixed(1)},${r.toFixed(1)} 0 ${(a1 - a0) > 180 ? 1 : 0} 0 ${(cx + r * sx1).toFixed(1)},${(cy + r * sy1).toFixed(1)}`,
      fill: "none", stroke: "#ffffff", "stroke-opacity": 0.8, "stroke-width": 0.8, "stroke-dasharray": "2 2" }, svg);
  }
  const tg = Number(target);
  if (isFinite(tg) && tg > 0) {
    for (const a of [tg / 2, -tg / 2]) {
      if (a < a0 || a > a1) continue;
      const [sx, sy] = dir(a);
      el("line", { x1: cx, y1: cy, x2: cx + R * sx, y2: cy + R * sy, stroke: "#ffffff", "stroke-opacity": 0.95,
                   "stroke-width": 0.9, "stroke-dasharray": "4 3" }, svg);
    }
  }
  if (title) el("text", { x: 4, y: 13, class: "iso-title" }, svg).textContent = title;
  if (legend) {
    const lx = W - 40, bwid = 7, lh = Math.min(R, 160), ly = top + labPad, bandH = lh / ISOBAR_COLORS.length;
    ISOBAR_COLORS.forEach((c, i) => el("rect", { x: lx, y: ly + lh - (i + 1) * bandH, width: bwid, height: bandH + 0.4, fill: c }, svg));
    for (let L = ISOBAR_MIN; L <= ISOBAR_MAX; L += 6) {
      const y = ly + lh - (L - ISOBAR_MIN) / (ISOBAR_MAX - ISOBAR_MIN) * lh;
      el("text", { x: lx + bwid + 4, y: y + 3, style: `fill:${muted};font-size:9px` }, svg).textContent = L === 0 ? "0" : "−" + Math.abs(L);
    }
    el("text", { x: lx, y: ly - 5, style: `fill:${muted};font-size:9px` }, svg).textContent = "dB";
  }

  // hover readout
  const cross = el("g", { style: "pointer-events:none;display:none" }, svg);
  const box = el("rect", { rx: 3, fill: "rgba(11,15,20,0.85)" }, cross);
  const txt = el("text", { style: "fill:#fff;font-size:10.5px" }, cross);
  const hit = el("rect", { x: bx0, y: by0, width: bw, height: bh, fill: "transparent", style: "cursor:crosshair" }, svg);
  hit.addEventListener("mousemove", ev => {
    const r = svg.getBoundingClientRect(), k = W / r.width;
    const x = (ev.clientX - r.left) * k, y = (ev.clientY - r.top) * k;
    const p = polarAt(x, y);
    if (!p) { cross.style.display = "none"; return; }
    const f = Math.pow(10, p.lg), v = sample(rows, fIndex(p.lg), aIndex(p.a));
    txt.textContent = (f >= 1000 ? (f / 1000).toFixed(2) + " kHz" : Math.round(f) + " Hz") + " · " +
      (p.a >= 0 ? "+" : "") + p.a.toFixed(0) + "° · " + (v < ISOBAR_MIN ? "below " + ISOBAR_MIN : v.toFixed(1)) + " dB";
    const tx = x + 176 > W ? x - 172 : x + 10, ty = y < 24 ? y + 22 : y - 8;
    txt.setAttribute("x", tx + 6); txt.setAttribute("y", ty);
    box.setAttribute("x", tx); box.setAttribute("y", ty - 12); box.setAttribute("width", 162); box.setAttribute("height", 17);
    cross.style.display = "";
  });
  hit.addEventListener("mouseleave", () => { cross.style.display = "none"; });
}

/** ── Circular polar plot (C12) ─────────────────────────────────────────────────────────────────
 * Classic polar diagram for a single frequency slice: half or full circle, rings every 6 dB,
 * spokes every 15° labelled every 30°.  For WP6 to place inside the per-design panel.
 *
 * @param svg      SVG element to draw into.
 * @param rowsH    H-plane polar data: array [na_h] of dB values (relative to on-axis).
 * @param rowsV    V-plane polar data: array [na_v] of dB values; null = omit.
 * @param anglesH  Angles for H rows (degrees, symmetric about 0).
 * @param anglesV  Angles for V rows (degrees).
 * @param opts     { H=240, dBmin=-30, ghost_h=null, ghost_v=null }
 *                 ghost_* are prior-design arrays for a dashed screen ghost.
 */
export function polarPlot(svg, rowsH, rowsV, anglesH, anglesV, { H = 240, dBmin = -30, ghost_h = null, ghost_v = null } = {}) {
  svg.innerHTML = "";
  if (!rowsH || !rowsH.length) return;
  const W = measuredWidth(svg, H);
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("width", W); svg.setAttribute("height", H);
  svg.dataset.chart = "1";

  const cx = W / 2, cy = H / 2, R = Math.min(W, H) / 2 - 20;
  // rings every 6 dB from dBmin to 0
  const nRings = Math.ceil(-dBmin / 6);
  for (let i = 0; i <= nRings; i++) {
    const r = R * (i / nRings);
    el("circle", { cx, cy, r, fill: "none", stroke: css("--rule"), "stroke-width": i === nRings ? 1.2 : 0.7 }, svg);
    if (i > 0) {
      const lab = el("text", { x: cx + 2, y: cy - r - 2, "font-size": "8", style: "fill:var(--muted)" }, svg);
      lab.textContent = String((i - nRings) * 6) + "dB";
    }
  }
  // spokes every 15°, labelled every 30°
  for (let a = 0; a < 360; a += 15) {
    const rad = (a - 90) * Math.PI / 180;
    el("line", { x1: cx, y1: cy, x2: cx + R * Math.cos(rad), y2: cy + R * Math.sin(rad),
                 stroke: css("--rule"), "stroke-width": a % 30 === 0 ? 0.8 : 0.4, "stroke-dasharray": "2 2" }, svg);
    if (a % 30 === 0) {
      const tx2 = cx + (R + 10) * Math.cos(rad), ty2 = cy + (R + 10) * Math.sin(rad);
      const lab = el("text", { x: tx2, y: ty2 + 3, "font-size": "8", "text-anchor": "middle", style: "fill:var(--muted)" }, svg);
      lab.textContent = String(a) + "°";
    }
  }
  // plot one polar curve: data[i] is dB at angles[i]
  function drawPolar(data, angles, color, dash) {
    if (!data || !data.length) return;
    const pts = angles.map((a, i) => {
      const v = data[i];
      if (v == null || !isFinite(v)) return null;
      const r = R * Math.max(0, (Math.max(dBmin, v) - dBmin) / (-dBmin));
      const rad = (a - 90) * Math.PI / 180;
      return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
    }).filter(Boolean);
    if (pts.length < 2) return;
    el("path", { d: pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + "," + p[1].toFixed(1)).join("") + "Z",
      fill: "none", stroke: color, "stroke-width": 1.6, "stroke-dasharray": dash || "none", "stroke-linejoin": "round" }, svg);
  }

  if (ghost_h) drawPolar(ghost_h, anglesH, css("--seed"), "4 3");
  if (ghost_v && anglesV) drawPolar(ghost_v, anglesV, css("--seed"), "4 3");
  drawPolar(rowsH, anglesH, css("--best"), "none");
  if (rowsV && anglesV) drawPolar(rowsV, anglesV, css("--best"), "5 3");
}
