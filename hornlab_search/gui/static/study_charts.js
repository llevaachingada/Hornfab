// Study-page BO charts.  Pure view of bounded JSON from /api/studies/<id>/<phase>;
// no score math and no fetch here.  The page passes the panel's `data.bo` object.
import { chart, catColor, fmt, niceTicks } from "./charts.js";

const SVG = "http://www.w3.org/2000/svg";
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
  const groups = [
    { source: "training", color: color("--muted", "#8a96a0"), r: 2.2, opacity: 0.6 },
    { source: "screen", color: color("--accent", "#2a78d6"), r: 3.0, opacity: 0.85 },
    { source: "nondominated", color: color("--best", "#1baf7a"), r: 3.4, opacity: 0.95 },
    { source: "finalist", color: color("--warn", "#eda100"), r: 4.4, opacity: 1 },
  ];
  const series = groups.map(group => ({
    pts: points.filter(point => {
      if (group.source === "nondominated") return point.nondominated === true;
      if (group.source === "finalist") return point.finalist === true;
      return point.source === group.source && point.nondominated !== true;
    }).map(point => [point.coverage_deg, point.ripple_db]),
    dots: true, r: group.r, opacity: group.opacity, color: group.color,
  }));
  const reference = view.reference || {};
  const vlines = finite(reference.limits?.[0])
    ? [{ x: reference.limits[0], color: color("--label", "#667"), dash: true }] : [];
  const hlines = finite(reference.limits?.[1])
    ? [{ y: reference.limits[1], color: color("--label", "#667"), dash: true }] : [];
  chart(svg, {
    W: 520, H: 300, xlim: limits.xlim, ylim: limits.ylim,
    xticks: niceTicks(limits.xlim[0], limits.xlim[1], 5),
    yticks: niceTicks(limits.ylim[0], limits.ylim[1], 5),
    xlabel: "coverage error (deg)", ylabel: "ripple error (dB)",
    series, vlines, hlines,
    ariaLabel: "Measured coverage error against ripple error; nondominated and finalist points highlighted",
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

export function drawStudyCharts(root, panel) {
  if (!root || typeof root.querySelector !== "function") return;
  const bo = panel?.data?.bo;
  if (!bo || typeof bo !== "object") return;
  const find = name => root.querySelector(`svg[data-study-chart="${name}"]`);
  const convergence = find("convergence");
  if (convergence) drawConvergence(convergence, bo.convergence);
  const calibration = find("calibration");
  if (calibration) drawCalibration(calibration, bo.calibration);
  const pareto = find("pareto");
  if (pareto) drawPareto(pareto, bo.pareto);
  const trust = find("trust_region");
  if (trust) drawTrustRegion(trust, bo.trust_region);
  const space = find("design_space");
  if (space) drawDesignSpace(space, bo.design_space);
}
