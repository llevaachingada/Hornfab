// Study-page BO charts.  Pure view of bounded JSON from /api/studies/<id>/<phase>;
// no score math and no fetch here.  The page passes the panel's `data.bo` object.
import { chart, catColor, el, fmt, niceTicks } from "./charts.js";

const RUN_ID = /^study-[0-9a-f]{16}$/;
const HASH = /^[0-9a-f]{6,64}$/;

const css = name => {
  try { return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || null; }
  catch (_) { return null; }
};
const color = (name, fallback) => css(name) || fallback;
const finite = value => typeof value === "number" && Number.isFinite(value);
const padRange = (lo, hi, frac = 0.08, floor = 0.05) => {
  if (!finite(lo) || !finite(hi)) return null;
  const pad = Math.max(floor, Math.abs(hi - lo) * frac);
  return [lo - pad, hi + pad];
};

export function convergenceLimits(view) {
  const arms = Array.isArray(view?.arms) ? view.arms : [];
  const ys = [];
  let xmax = 1;
  for (const arm of arms) {
    // The plot is a best-so-far chart.  Individual solves (including the audit
    // outliers at J≈20) must not decide the y range, or the useful band becomes
    // a flat line at the bottom of a 0–25 axis.
    for (const point of arm?.points || []) {
      if (finite(point?.[1])) ys.push(point[1]);
      if (finite(point?.[0])) xmax = Math.max(xmax, point[0]);
    }
    for (const point of arm?.solves || []) {
      if (finite(point?.[0])) xmax = Math.max(xmax, point[0]);
    }
    for (const point of arm?.verify_points || []) {
      if (finite(point?.[0])) xmax = Math.max(xmax, point[0]);
    }
    for (const index of arm?.refusals || []) {
      if (finite(index)) xmax = Math.max(xmax, index);
    }
  }
  if (finite(view?.incumbent?.j)) ys.push(view.incumbent.j);
  if (!ys.length || !finite(xmax)) return null;
  const ylim = padRange(Math.min(...ys), Math.max(...ys), 0.12, 0.08);
  return ylim ? { xlim: [0, Math.max(1, xmax)], ylim } : null;
}

export function calibrationLimits(view) {
  const points = Array.isArray(view?.points) ? view.points : [];
  const values = [];
  for (const point of points) {
    for (const value of [point?.predicted, point?.measured, point?.lower, point?.upper]) {
      if (finite(value)) values.push(value);
    }
  }
  if (!values.length) return null;
  const range = padRange(Math.min(...values), Math.max(...values), 0.1, 0.2);
  return range ? { xlim: range.slice(), ylim: range.slice() } : null;
}

export function paretoLimits(view) {
  const points = Array.isArray(view?.points) ? view.points : [];
  const xs = [], ys = [];
  for (const point of points) {
    if (finite(point?.coverage_deg)) xs.push(point.coverage_deg);
    if (finite(point?.ripple_db)) ys.push(point.ripple_db);
  }
  for (const point of (Array.isArray(view?.excluded_points) ? view.excluded_points : [])) {
    if (finite(point?.coverage_deg)) xs.push(point.coverage_deg);
    if (finite(point?.ripple_db)) ys.push(point.ripple_db);
  }
  for (const point of (Array.isArray(view?.predicted) ? view.predicted : [])) {
    if (finite(point?.coverage_deg?.mean)) xs.push(point.coverage_deg.mean);
    if (finite(point?.ripple_db?.mean)) ys.push(point.ripple_db.mean);
  }
  if (finite(view?.reference?.limits?.[0])) xs.push(view.reference.limits[0]);
  if (finite(view?.reference?.limits?.[1])) ys.push(view.reference.limits[1]);
  if (!xs.length || !ys.length) return null;
  return {
    xlim: [0, Math.max(...xs) * 1.12 + 0.05],
    ylim: [0, Math.max(...ys) * 1.15 + 0.02],
  };
}

export function trustRegionPoints(view) {
  return (Array.isArray(view?.length_series) ? view.length_series : [])
    .filter(point => finite(point?.[0]) && finite(point?.[1]))
    .map(point => [Number(point[0]), Number(point[1])]);
}

export function designSpaceLimits(view) {
  const points = Array.isArray(view?.points) ? view.points : [];
  const xs = points.map(point => point?.x).filter(finite);
  const ys = points.map(point => point?.y).filter(finite);
  if (!xs.length || !ys.length) return null;
  return {
    xlim: padRange(Math.min(...xs), Math.max(...xs), 0.08, 0.02),
    ylim: padRange(Math.min(...ys), Math.max(...ys), 0.08, 0.02),
  };
}

/** Safe internal deep link for a selected design; never trust an arbitrary URL. */
export function designLink(runId, designHash) {
  if (typeof runId !== "string" || !RUN_ID.test(runId)) return null;
  if (typeof designHash !== "string" || !HASH.test(designHash)) return null;
  return `#/run/${encodeURIComponent(runId)}/balloon?design=${encodeURIComponent(designHash)}`;
}

export function formatSeconds(value) {
  if (!finite(value) || value < 0) return "—";
  const seconds = Math.round(value);
  if (seconds < 90) return `${seconds} s`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 120) return `${minutes} min`;
  return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

function legend(parent, arms) {
  if (!parent || !Array.isArray(arms) || !arms.length) return;
  let node = parent.querySelector(".study-chart-legend");
  if (!node) {
    node = document.createElement("div");
    node.className = "study-chart-legend";
    parent.appendChild(node);
  }
  node.innerHTML = arms.map((arm, index) => {
    const c = catColor(arm.color_slot ?? index);
    const dash = arm.method && arm.method !== "bo" ? " dashed" : "";
    return `<span><i class="swatch${dash}" style="background:${c}"></i>${escapeHtml(arm.label || arm.id || "arm")}</span>`;
  }).join("");
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[ch]));
}

function drawConvergence(svg, view) {
  if (!svg || !view || !["ready", "partial"].includes(view.status)) return;
  const limits = convergenceLimits(view);
  if (!limits) return;
  const arms = Array.isArray(view.arms) ? view.arms : [];
  const series = [];
  const muted = color("--muted", "#8a96a0");
  const label = color("--label", "#667");
  for (const arm of arms) {
    const c = catColor(arm.color_slot ?? 0);
    series.push({ pts: (arm.points || []).map(p => [p[0], p[1]]), color: c,
      w: arm.method === "bo" ? 2.4 : 1.8, dash: arm.method !== "bo" });
    const inRange = value => finite(value) && value >= limits.ylim[0] && value <= limits.ylim[1];
    for (const point of arm.solves || []) {
      if (!inRange(point[1])) continue;   // keep the best-so-far band readable
      series.push({ pts: [[point[0], point[1]]], dots: true, r: 1.7, opacity: 0.32, color: c });
    }
    for (const point of arm.verify_points || []) {
      if (!inRange(point[1])) continue;
      series.push({ pts: [[point[0], point[1]]], dots: true, r: 2.6, opacity: 0.95, color: c });
    }
    for (const point of arm.exploration_points || []) {
      if (!inRange(point[1])) continue;
      series.push({ pts: [[point[0], point[1]]], dots: true, r: 3.0, opacity: 0.95,
        color: color("--accent", "#2a78d6") });
    }
    for (const index of arm.refusals || []) {
      series.push({ pts: [[index, limits.ylim[0] + Math.max(0.02, (limits.ylim[1] - limits.ylim[0]) * 0.02)]],
        dots: true, r: 2.0, opacity: 0.65, color: muted });
    }
  }
  const hlines = finite(view.incumbent?.j)
    ? [{ y: view.incumbent.j, color: label, dash: true }] : [];
  const xticks = niceTicks(limits.xlim[0], limits.xlim[1], 6);
  const yticks = niceTicks(limits.ylim[0], limits.ylim[1], 5);
  chart(svg, {
    W: 620, H: 260, xlim: limits.xlim, ylim: limits.ylim,
    xticks, yticks, xlabel: "solve index", ylabel: "J (recorded)",
    series, hlines,
    ariaLabel: "Best recorded J by solve index for each optimiser arm",
  });
  legend(svg.parentElement, arms);
}

function drawCalibration(svg, view) {
  if (!svg || !view || !["ready", "partial"].includes(view.status)) return;
  const limits = calibrationLimits(view);
  if (!limits) return;
  const points = Array.isArray(view.points) ? view.points : [];
  const accent = color("--accent", "#2a78d6");
  const label = color("--label", "#667");
  const series = [
    { pts: [[limits.xlim[0], limits.ylim[0]], [limits.xlim[1], limits.ylim[1]]],
      color: label, w: 1, dash: true, opacity: 0.7 },
    { pts: points.map(p => [p.predicted, p.measured]), dots: true, r: 3.0, color: accent },
  ];
  chart(svg, {
    W: 460, H: 260, xlim: limits.xlim, ylim: limits.ylim,
    xticks: niceTicks(limits.xlim[0], limits.xlim[1], 5),
    yticks: niceTicks(limits.ylim[0], limits.ylim[1], 5),
    xlabel: "predicted J (model)", ylabel: "measured J (screen)", series,
    ariaLabel: "Predicted model J against measured screen J with the y equals x guide",
  });
}

function drawPareto(svg, view) {
  if (!svg || !view || !["ready", "partial"].includes(view.status)) return;
  const limits = paretoLimits(view);
  if (!limits) return;
  const points = Array.isArray(view.points) ? view.points : [];
  const finitePair = point => Number.isFinite(Number(point?.[0])) && Number.isFinite(Number(point?.[1]));
  const groups = [
    { source: "training", color: color("--muted", "#8a96a0"), r: 2.2, opacity: 0.6 },
    { source: "screen", color: color("--accent", "#2a78d6"), r: 3.0, opacity: 0.85 },
    { source: "nondominated", color: color("--best", "#1baf7a"), r: 3.4, opacity: 0.95 },
    { source: "finalist", color: color("--warn", "#eda100"), r: 4.4, opacity: 1 },
  ];
  const nondominated = (Array.isArray(view.nondominated) && view.nondominated.length)
    ? view.nondominated : points.filter(point => point.nondominated === true);
  const series = groups.map(group => ({
    pts: (group.source === "nondominated" ? nondominated : points).filter(point => {
      if (group.source === "nondominated") return true;
      if (group.source === "finalist") return point.finalist === true;
      return point.source === group.source && point.nondominated !== true;
    }).map(point => [point.coverage_deg, point.ripple_db]).filter(finitePair),
    dots: true, r: group.r, opacity: group.opacity, color: group.color,
  }));
  const excluded = (Array.isArray(view.excluded_points) ? view.excluded_points : [])
    .map(point => [point.coverage_deg, point.ripple_db]).filter(finitePair);
  if (excluded.length) {
    series.push({ pts: excluded, dots: true, r: 2.1, opacity: 0.55, color: color("--bad", "#b23a3a") });
  }
  const predicted = (Array.isArray(view.predicted) ? view.predicted : []).map(point => [
    point?.coverage_deg?.mean, point?.ripple_db?.mean,
  ]).filter(finitePair);
  if (predicted.length) {
    series.push({ pts: predicted, dots: true, r: 2.6, opacity: 0.55, color: color("--label", "#667") });
  }
  const reference = view.reference || {};
  const axes = view.frontier_axes && typeof view.frontier_axes === "object" ? view.frontier_axes : {};
  const xUnit = axes.units?.[0] || "deg";
  const yUnit = axes.units?.[1] || "dB";
  const vlines = finite(reference.limits?.[0])
    ? [{ x: reference.limits[0], color: color("--label", "#667"), dash: true }] : [];
  const hlines = finite(reference.limits?.[1])
    ? [{ y: reference.limits[1], color: color("--label", "#667"), dash: true }] : [];
  chart(svg, {
    W: 520, H: 300, xlim: limits.xlim, ylim: limits.ylim,
    xticks: niceTicks(limits.xlim[0], limits.xlim[1], 5),
    yticks: niceTicks(limits.ylim[0], limits.ylim[1], 5),
    xlabel: `coverage error (${xUnit})`, ylabel: `ripple (${yUnit})`,
    series, vlines, hlines,
    ariaLabel: "Measured coverage error against ripple; nondominated, finalist, excluded and predicted points are separate marks",
  });
}

/** Pure helper: readable [[training_row, prefix_hypervolume], ...] rows, or [] when unusable.
 *  A bounded-panel marker string can sit in the list, so every row is type-checked (a null or a
 *  string is rejected, never coerced to 0). */
export function hvTracePoints(trace) {
  const rows = (Array.isArray(trace) ? trace : [])
    .filter(row => Array.isArray(row)
      && typeof row[0] === "number" && Number.isFinite(row[0])
      && typeof row[1] === "number" && Number.isFinite(row[1]))
    .map(row => [row[0], row[1]]);
  return rows.length >= 2 ? rows : [];
}

/** Pure helper: axis limits for the diagnostics hypervolume trace (row order from 0). */
export function hvTraceLimits(trace) {
  const rows = hvTracePoints(trace);
  if (!rows.length) return null;
  const ys = rows.map(row => row[1]);
  const ylim = padRange(Math.min(...ys), Math.max(...ys), 0.12, 0.05);
  if (!ylim) return null;
  return { xlim: [0, Math.max(2, Math.max(...rows.map(row => row[0])))], ylim };
}

/** Step-after expansion of the trace: the value holds until a row raises it.  Derived from the
 *  recorded rows only, so a flat run stays visibly flat instead of sloping. */
function stepPoints(trace) {
  const out = [[trace[0][0], trace[0][1]]];
  for (let i = 1; i < trace.length; i += 1) {
    out.push([trace[i][0], trace[i - 1][1]], [trace[i][0], trace[i][1]]);
  }
  return out;
}

function drawParetoHv(svg, diag) {
  if (!svg || !diag || diag.available !== true) return;
  const trace = hvTracePoints(diag.hv_trace);
  const limits = hvTraceLimits(trace);
  if (!limits) return;
  const accent = color("--accent", "#2a78d6");
  chart(svg, {
    W: 520, H: 220, xlim: limits.xlim, ylim: limits.ylim,
    xticks: niceTicks(limits.xlim[0], limits.xlim[1], 5),
    yticks: niceTicks(limits.ylim[0], limits.ylim[1], 4),
    xlabel: "training rows (row order)", ylabel: "prefix hypervolume",
    series: [
      { pts: stepPoints(trace), color: accent, w: 2 },
      { pts: trace, dots: true, r: 2.4, color: accent, opacity: 0.95 },
    ],
    ariaLabel: "Prefix hypervolume of the model diagnostics training rows against training-row order; the value only rises when a row adds hypervolume",
  });
}

function drawTrustRegion(svg, view) {
  if (!svg || !view || !["ready", "partial"].includes(view.status)) return;
  const points = trustRegionPoints(view);
  if (!points.length) return;
  const ys = points.map(point => point[1]);
  const bounds = view.length_bounds || {};
  if (finite(bounds.min)) ys.push(bounds.min);
  if (finite(bounds.max)) ys.push(bounds.max);
  const ylim = padRange(Math.min(...ys), Math.max(...ys), 0.08, 0.02) || [0, 1.6];
  const hlines = [];
  if (finite(bounds.min)) hlines.push({ y: bounds.min, color: color("--bad", "#e34948"), dash: true });
  if (finite(bounds.max)) hlines.push({ y: bounds.max, color: color("--label", "#667"), dash: true });
  chart(svg, {
    W: 620, H: 220, xlim: [0, Math.max(1, ...points.map(p => p[0]))], ylim,
    xticks: niceTicks(0, Math.max(1, ...points.map(p => p[0])), 6),
    yticks: niceTicks(ylim[0], ylim[1], 5),
    xlabel: "proposal", ylabel: "trust-region length L",
    series: [{ pts: points, color: color("--accent", "#2a78d6"), w: 2 }],
    hlines,
    ariaLabel: "Trust-region length over proposals, with the collapse floor and maximum",
  });
}

function drawDesignSpace(svg, view) {
  if (!svg || !view || !["ready", "partial"].includes(view.status)) return;
  const limits = designSpaceLimits(view);
  if (!limits) return;
  const points = Array.isArray(view.points) ? view.points : [];
  const series = [
    { source: "training", color: color("--muted", "#8a96a0"), r: 2.0, opacity: 0.55 },
    { source: "screen", color: color("--accent", "#2a78d6"), r: 2.8, opacity: 0.9 },
  ].map(group => ({
    pts: points.filter(point => point.source === group.source).map(point => [point.x, point.y]),
    dots: true, r: group.r, opacity: group.opacity, color: group.color,
  }));
  chart(svg, {
    W: 520, H: 300, xlim: limits.xlim, ylim: limits.ylim,
    xticks: niceTicks(limits.xlim[0], limits.xlim[1], 5),
    yticks: niceTicks(limits.ylim[0], limits.ylim[1], 5),
    xlabel: "component 1", ylabel: "component 2", series,
    ariaLabel: "Two-dimensional projection of training and proposed designs",
  });
}


const finiteRow = (...v) => v.every(finite);

/** Pure helper (tested): limits for the LOO scatter including the +/-2 sd whiskers. */
export function looLimits(loo) {
  const rows = Array.isArray(loo?.rows) ? loo.rows.filter(r => finiteRow(r.j_obs, r.j_mean)) : [];
  if (!rows.length) return null;
  const vals = [];
  for (const r of rows) {
    const sd = finite(r.j_sd) ? r.j_sd : 0;
    vals.push(r.j_obs, r.j_mean - 2 * sd, r.j_mean + 2 * sd);
  }
  const [lo, hi] = padRange(Math.min(...vals), Math.max(...vals));
  return { lim: [lo, hi] };
}

function drawLoo(svg, loo) {
  if (!svg || !loo || loo.available !== true) return;
  const limits = looLimits(loo);
  if (!limits) return;
  const rows = loo.rows.filter(r => finiteRow(r.j_obs, r.j_mean));
  const accent = color("--accent", "#2a78d6");
  const label = color("--label", "#667");
  const series = [{ pts: [[limits.lim[0], limits.lim[0]], [limits.lim[1], limits.lim[1]]], color: label, w: 1, dash: true, opacity: 0.7 }];
  // Whiskers run along x (the model's +/-2 sd) at the observed y.  With ~200 training rows
  // stacked on a handful of measured J values, full-strength strokes fuse into a solid block:
  // keep every row but let the ensemble read as a light envelope, so the dots and the y=x guide
  // stay the foreground.
  const whiskers = rows.filter(r => finite(r.j_sd) && r.j_sd > 0)
    .map(r => ({ pts: [[r.j_mean - 2 * r.j_sd, r.j_obs], [r.j_mean + 2 * r.j_sd, r.j_obs]], color: accent, w: 1, opacity: 0.16 }));
  chart(svg, {
    W: 460, H: 260, xlim: limits.lim, ylim: limits.lim,
    xticks: niceTicks(limits.lim[0], limits.lim[1], 5), yticks: niceTicks(limits.lim[0], limits.lim[1], 5),
    xlabel: "LOO predicted J (+/-2 sd)", ylabel: "observed J (training)",
    series: [series[0], ...whiskers,
      { pts: rows.map(r => [r.j_mean, r.j_obs]), dots: true, r: 2.6, color: accent, opacity: 0.9 }],
    ariaLabel: "Leave-one-out predicted J with two standard deviation whiskers against observed J, with the y equals x guide",
  });
}

/** Pure helper (tested): chart limits for one 1-D slice (mean +/- 2 sd). */
export function sliceLimits(slice) {
  const xs = (slice?.x || []).filter(finite);
  if (xs.length < 2) return null;
  const ys = [];
  (slice.j_mean || []).forEach((m, i) => {
    const sd = finite(slice.j_sd?.[i]) ? slice.j_sd[i] : 0;
    if (finite(m)) ys.push(m - 2 * sd, m + 2 * sd);
  });
  if (!ys.length) return null;
  return { xlim: [Math.min(...xs), Math.max(...xs)], ylim: padRange(Math.min(...ys), Math.max(...ys)) };
}

function drawSlice(svg, slice) {
  const limits = sliceLimits(slice);
  if (!svg || !limits) return;
  const accent = color("--accent", "#2a78d6");
  const label = color("--label", "#667");
  const pairs = slice.x.map((x, i) => [x, slice.j_mean[i], slice.j_sd[i]]).filter(p => finiteRow(p[0], p[1]));
  const sd = p => (finite(p[2]) ? p[2] : 0);
  const chartOpts = {
    W: 300, H: 170, xlim: limits.xlim, ylim: limits.ylim,
    xticks: niceTicks(limits.xlim[0], limits.xlim[1], 4), yticks: niceTicks(limits.ylim[0], limits.ylim[1], 4),
    ylabel: "J",
    // The ±2σ envelope is an area mark, so chart() draws it under the mean and repaints it with
    // every resize redraw.  Its name lives in the figure caption, which also carries the SVG's
    // aria-label, so the plot prints no axis label for it.
    area: [{
      top: pairs.map(p => [p[0], p[1] + 2 * sd(p)]),
      bottom: pairs.map(p => [p[0], p[1] - 2 * sd(p)]),
      color: accent, opacity: 0.14,
    }],
    series: [
      { pts: pairs.map(p => [p[0], p[1] + 2 * sd(p)]), color: accent, w: 1, dash: true, opacity: 0.5 },
      { pts: pairs.map(p => [p[0], p[1] - 2 * sd(p)]), color: accent, w: 1, dash: true, opacity: 0.5 },
      { pts: pairs.map(p => [p[0], p[1]]), color: accent, w: 2 },
    ],
    vlines: finite(slice.anchor_x) ? [{ x: slice.anchor_x, color: label, dash: true }] : [],
  };
  chart(svg, chartOpts);
}

export function drawStudyCharts(root, panel) {
  if (!root || typeof root.querySelector !== "function") return;
  const bo = panel?.data?.bo;
  if (!bo || typeof bo !== "object") return;
  const find = name => root.querySelector(`svg[data-study-chart="${name}"]`);
  const convergence = find("convergence");
  if (convergence) drawConvergence(convergence, bo.convergence);
  const calibration = find("calibration");
  if (calibration) {
    const seq = bo.calibration?.sequential_validation;
    drawCalibration(calibration, seq
      ? { ...seq, status: bo.calibration?.status || "partial" }
      : bo.calibration);
  }
  const loo = find("calibration_loo");
  if (loo) drawLoo(loo, bo.calibration?.efficient_loo_cv || bo.calibration?.loo);
  const sliceList = Array.isArray(bo.sensitivity?.posterior_slices?.items)
    ? bo.sensitivity.posterior_slices.items
    : (Array.isArray(bo.sensitivity?.slices) ? bo.sensitivity.slices : []);
  root.querySelectorAll('svg[data-study-slice]').forEach(node => {
    const slice = sliceList.find(item => item.key === node.getAttribute("data-study-slice"));
    if (slice) drawSlice(node, slice);
  });
  const pareto = find("pareto");
  if (pareto) drawPareto(pareto, bo.pareto);
  const paretoHv = find("pareto_hv");
  if (paretoHv) {
    const diag = bo.pareto?.diagnostics;
    const trace = diag?.available === true ? diag.hv_trace
      : (Array.isArray(bo.pareto?.hypervolume_trace) ? bo.pareto.hypervolume_trace : null);
    drawParetoHv(paretoHv, trace ? { available: true, hv_trace: trace } : diag);
  }
  const trust = find("trust_region");
  if (trust) drawTrustRegion(trust, bo.trust_region);
  const space = find("design_space");
  if (space) drawDesignSpace(space, bo.design_space);
}

// ── Identity-based point picking (P1) ─────────────────────────────────────────────
// A plotted mark is actionable only when it carries a stable identity (design_hash or
// solve_id).  The click handler receives that identity, never the canvas pixel position, so
// a hit ring can move with the chart while the inspector opens the same physical design.

/** The data→viewBox transform `chart()` used for its most recent draw of `svg`, or null. */
function markerScale(svg) {
  const opts = svg?._chartOpts;
  if (!opts || !Array.isArray(opts.xlim) || !Array.isArray(opts.ylim)) return null;
  const W = svg._chartW || opts.W || 460;
  const H = opts.H || 240;
  const m = { l: 44, r: 12, t: opts.ylabel ? 20 : 10, b: 32 };
  const tx = opts.xlog ? v => Math.log10(v) : v => v;
  const ty = opts.ylog ? v => (v != null && v > 0 ? Math.log10(v) : null) : v => v;
  const x0 = tx(opts.xlim[0]), x1 = tx(opts.xlim[1]);
  const y0 = ty(opts.ylim[0]), y1 = ty(opts.ylim[1]);
  if (![x0, x1, y0, y1].every(v => typeof v === "number" && Number.isFinite(v))) return null;
  if (x1 === x0 || y1 === y0) return null;
  const X = v => m.l + (tx(v) - x0) / (x1 - x0) * (W - m.l - m.r);
  const Y = v => {
    const tv = ty(v);
    return tv == null ? null : H - m.b - (tv - y0) / (y1 - y0) * (H - m.t - m.b);
  };
  return { X, Y };
}

/**
 * Draw an identity-bearing hit layer over a chart already drawn by `chart()`.
 *
 * `points` are plot rows with `x`/`y` (or coverage/ripple) plus an optional `design_hash`
 * and/or `solve_id`.  Points with an identity get a focusable ring and call
 * `onSelect({designHash, solveId, point})`; points without one are drawn as a small hollow
 * marker and counted, so the caller can say "N training points have no resolvable design
 * hash" instead of silently making them un-clickable.  Pure DOM; no fetch and no score math.
 */
export function addIdentityMarkers(svg, points, onSelect, { r = 9 } = {}) {
  if (!svg || typeof svg.querySelector !== "function" || !Array.isArray(points)) {
    return { resolved: 0, unresolved: 0 };
  }
  const scale = markerScale(svg);
  if (!scale) return { resolved: 0, unresolved: 0 };
  const existing = svg.querySelector("g[data-res-point-layer]");
  if (existing) existing.remove();
  const layer = el("g", { "data-res-point-layer": "1", class: "res-point-layer" }, svg);
  const accent = color("--accent", "#0d6e7a");
  const muted = color("--muted", "#5a6873");
  let resolved = 0, unresolved = 0;
  for (const point of points) {
    if (!point || typeof point !== "object") continue;
    const x = Number(point.x ?? point.coverage_deg);
    const y = Number(point.y ?? point.ripple_db);
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    const cx = scale.X(x), cy = scale.Y(y);
    if (!Number.isFinite(cx) || !Number.isFinite(cy)) continue;
    const designHash = typeof point.designHash === "string" ? point.designHash
      : (typeof point.design_hash === "string" ? point.design_hash : null);
    const solveId = typeof point.solveId === "string" ? point.solveId
      : (typeof point.solve_id === "string" ? point.solve_id : null);
    if (!designHash && !solveId) {
      unresolved += 1;
      el("circle", {
        cx, cy, r: 3, fill: "none", stroke: muted, "stroke-width": 1,
        "stroke-dasharray": "2 2", "stroke-opacity": 0.8, "aria-hidden": "true",
      }, layer);
      continue;
    }
    resolved += 1;
    const identity = designHash ? `design ${designHash}` : `solve ${solveId}`;
    const group = el("g", {
      class: "res-point-hit", tabindex: "0", role: "button",
      "data-design-hash": designHash || "", "data-solve-id": solveId || "",
      "aria-label": `Open ${identity} in the horn inspector`,
      style: "cursor:pointer",
    }, layer);
    el("circle", { cx, cy, r: r + 4, fill: "transparent", stroke: "none" }, group);
    el("circle", {
      cx, cy, r, fill: "none", stroke: accent, "stroke-width": 1.2, "stroke-opacity": 0.55,
    }, group);
    const title = el("title", {}, group);
    title.textContent = `${identity}${finite(point.j) ? ` · J ${fmt(point.j)}` : ""}`;
    const choose = event => {
      if (event) { event.preventDefault(); event.stopPropagation(); }
      if (typeof onSelect === "function") onSelect({ designHash, solveId, point });
    };
    group.addEventListener("click", choose);
    group.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") choose(event);
    });
  }
  return { resolved, unresolved };
}
