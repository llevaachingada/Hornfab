// verify.js — hornlab-search GUI   AGPL-3.0-or-later
//
// Verify view: table, KPIs, scatter, per-design panel, compare-two.
// Entered from #/run/<id>/verify and #/run/<id>/verify/compare.
//
// WP3 (table/KPIs/scatter) + WP6 (panel/compare)
// Develop against tests/fixtures/gui/verify_report_example.json.

import { chart, isobarMap, logTicks, css, fmt, el, NS, niceTicks } from "./charts.js";
import { initBalloon3d } from "./balloon.js";

// ── XSS helper (local copy, same as app.js) ────────────────────────────────
const esc = s => (s == null ? "–" : String(s))
  .replace(/&/g, "&amp;")
  .replace(/</g, "&lt;")
  .replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;")
  .replace(/'/g, "&#39;");

function errBanner(msg) {
  return `<div class="alert error" role="alert"><b>Error:</b> ${esc(msg)}</div>`;
}

function skel(root, msg = "") {
  root.innerHTML = `<div class="stack vfy-skel" style="gap:18px;opacity:0.6">
    <div class="skeleton-block" style="height:2.2rem;width:min(260px,60%)"></div>
    <div class="skeleton-block" style="height:1rem;width:min(400px,80%)"></div>
    <div class="skeleton-block" style="height:180px"></div>
    ${msg ? `<p class="muted" style="opacity:0.5;font-size:0.82rem">${esc(msg)}</p>` : ""}
  </div>`;
}

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(r.status + " " + (await r.text().catch(() => "")));
  return r.json();
}

const fmtHz = v => v == null || !isFinite(v) ? "–"
  : v >= 1000 ? (v / 1000).toFixed(1) + " kHz" : Math.round(v) + " Hz";

// ── WP3: Pure helpers (exported, tested in node) ───────────────────────────

/**
 * Parse the query string from a verify URL.
 * Returns { design, sort, dir, ghost, show, fHz, compareA, compareB }.
 */
export function parseVerifyQuery(q) {
  const p = new URLSearchParams(q || "");
  return {
    design:   p.get("design") || null,
    sort:     p.get("sort") || "verify_j",
    dir:      p.get("dir") === "desc" ? "desc" : "asc",
    ghost:    p.get("ghost") !== "0",    // default on
    show:     (["all", "gate-pass", "failed"].includes(p.get("show")) ? p.get("show") : "all"),
    fHz:      p.has("f") ? Number(p.get("f")) : null,
    compareA: p.get("a") || null,
    compareB: p.get("b") || null,
  };
}

/**
 * Build a verify URL query string from state.
 */
export function buildVerifyQuery(state) {
  const p = new URLSearchParams();
  if (state.design)                           p.set("design", state.design);
  if (state.sort && state.sort !== "verify_j") p.set("sort",   state.sort);
  if (state.dir === "desc")                   p.set("dir",    "desc");
  if (state.ghost === false)                  p.set("ghost",  "0");
  if (state.show && state.show !== "all")     p.set("show",   state.show);
  if (state.fHz != null && isFinite(state.fHz)) p.set("f",   String(state.fHz));
  if (state.compareA)                         p.set("a", state.compareA);
  if (state.compareB)                         p.set("b", state.compareB);
  return p.toString();
}

/**
 * HTML for a Δ (verify − screen) table cell.
 * Positive delta = verify worse than screen → class bad-text.
 * Negative delta = verify better than screen → class good-text.
 * Either null → dash.
 */
export function deltaCellHtml(screenJ, verifyJ) {
  if (screenJ == null || verifyJ == null || !isFinite(+screenJ) || !isFinite(+verifyJ)) {
    return '<span class="mono muted">–</span>';
  }
  const delta = verifyJ - screenJ;
  const sign  = delta >= 0 ? "+" : "−";
  const cls   = delta > 0.001 ? " bad-text" : delta < -0.001 ? " good-text" : "";
  return `<span class="mono${cls}" title="verify J − screen J (verify ${esc(fmt(verifyJ))} − screen ${esc(fmt(screenJ))})">${sign}${Math.abs(delta).toFixed(2)}</span>`;
}

/**
 * Stable sort (preserves original order for equal values). Nulls last regardless of direction.
 */
export function sortRows(rows, key, dir) {
  if (!Array.isArray(rows)) return [];
  const asc = dir !== "desc";
  return rows.map((r, i) => ({ r, i })).sort(({ r: a, i: ai }, { r: b, i: bi }) => {
    const av = a[key], bv = b[key];
    if (av == null && bv == null) return ai - bi;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (av < bv) return asc ? -1 : 1;
    if (av > bv) return asc ? 1 : -1;
    return ai - bi;    // stable tie-break
  }).map(({ r }) => r);
}

/** Fidelity pills from report data (never hardcoded). */
export function fidelityPillsHtml(report) {
  const f = report && report.fidelity;
  if (!f) return "";
  const pill = (tier, fi) => {
    const nf  = (fi.n_freqs   || []).join(" / ");
    const bg  = (fi.balloon_grid || []).map(g => Array.isArray(g) ? g.join("×") : g).join(" / ");
    const pt  = (fi.n_points  || []).map(n => n.toLocaleString()).join(" / ");
    const dof = fi.dof_range  ? fi.dof_range.map(d => d.toLocaleString()).join("–") : null;
    return `<span class="pill ${esc(tier)}-fidelity-pill" title="${esc(tier)} fidelity">` +
      `${esc(tier)} · ${esc(nf)} freq · ${esc(bg)} (${esc(pt)} pt)` +
      (dof ? ` · ${esc(dof)} dof` : "") + `</span>`;
  };
  const parts = [];
  if (f.verify) parts.push(pill("verify", f.verify));
  if (f.screen) parts.push(pill("screen", f.screen));
  return `<div class="pill-row vfy-fidelity-pills" role="list">${parts.join("")}</div>`;
}

/** KPI strip HTML from summary (never hardcoded counts). */
export function summaryHtml(summary) {
  if (!summary) return "";
  const s = summary;
  const kpi = (label, val) =>
    `<div class="vfy-kpi"><div class="vfy-kpi-val">${esc(val)}</div><div class="vfy-kpi-label">${esc(label)}</div></div>`;
  const pct = s.bias_median_pct != null ? (s.bias_median_pct > 0 ? "+" : "") + fmt(s.bias_median_pct, 1) + "%" : "–";
  const rho = s.spearman_all != null ? "ρ=" + fmt(s.spearman_all, 2) : "–";
  const n   = (s.n_verified || 0);
  const top5ov = s.top5_overlap != null
    ? `${s.top5_overlap}/${Math.min(5, n)}`
    : "–";
  const screen1 = s.screen1_hash && s.screen1_verify_rank != null
    ? `screen #1 → verify #${s.screen1_verify_rank}`
    : "–";
  return `<div class="vfy-kpi-strip" role="group" aria-label="Verification summary">
    ${kpi("Verified designs", String(s.n_verified ?? 0))}
    ${kpi("Failed", String(s.n_failed ?? 0))}
    ${kpi("Screen bias median", pct)}
    ${kpi("Worse on verify", s.n_worse != null ? `${s.n_worse}/${n}` : "–")}
    ${kpi("Best verify J v" + esc(String(s.objective_version || "?")), s.best_verify_j != null ? fmt(s.best_verify_j) : "–")}
    ${kpi("Rank shift", screen1)}
    ${kpi("Top-5 overlap", top5ov)}
    ${kpi("Rank agreement", n >= 3 ? rho + " (n=" + n + ")" : "–")}
  </div>`;
}

/** Empty-state HTML for a run with no verify rows yet. */
export function emptyStateHtml(runId) {
  const cmd  = `hornlab-search verify --run "runs/${runId}" --top 5`;
  const cmd2 = `hornlab-search verify --run "runs/${runId}" --designs h1,h2,h3`;
  return `<div class="vfy-empty stack" style="gap:14px">
    <p class="muted">No designs have been verified for this run yet.</p>
    <p>Verify the top 5 screen designs:</p>
    <pre class="mono vfy-copyable" role="note" aria-label="verify command">${esc(cmd)}</pre>
    <p class="hint">Or select specific screen designs (use their hash prefixes):</p>
    <pre class="mono vfy-copyable" role="note">${esc(cmd2)}</pre>
    <p class="hint">Screen scores are a first pass at coarser fidelity. The verify step uses
      more frequencies and a finer balloon grid.</p>
  </div>`;
}

/** Header for a standalone verify run (no screen counterpart). */
export function standaloneHeaderHtml() {
  return `<p class="pill vfy-standalone-pill">Single-design verification · no screen run to compare against</p>`;
}

// ── WP6: Pure helpers (exported, tested in node) ───────────────────────────

/**
 * Snap to the nearest frequency in freqs array; return the index.
 */
export function nearestFreqIndex(freqs, targetHz) {
  if (!freqs || !freqs.length) return 0;
  if (targetHz == null || !isFinite(+targetHz)) return 0;
  let best = 0, bestDist = Infinity;
  for (let i = 0; i < freqs.length; i++) {
    const d = Math.abs(freqs[i] - targetHz);
    if (d < bestDist) { bestDist = d; best = i; }
  }
  return best;
}

/**
 * Per-curve band-delta statistics: compare verify values to the nearest screen frequency.
 * Returns { meanAbsDelta, maxAbsDelta, maxFreqHz } or null if data insufficient.
 * verifyVals: array of dB values at verifyFreqs.
 * screenVals: array of dB values at screenFreqs.
 */
export function bandDeltaStats(verifyVals, screenVals, verifyFreqs, screenFreqs) {
  if (!verifyVals || !screenVals || !verifyFreqs || !screenFreqs) return null;
  if (!verifyVals.length || !screenVals.length) return null;
  const deltas = [];
  for (let i = 0; i < verifyVals.length; i++) {
    if (verifyVals[i] == null || !isFinite(verifyVals[i])) continue;
    // find nearest screen frequency
    const fi = nearestFreqIndex(screenFreqs, verifyFreqs[i]);
    if (screenVals[fi] == null || !isFinite(screenVals[fi])) continue;
    deltas.push({ d: Math.abs(verifyVals[i] - screenVals[fi]), f: verifyFreqs[i] });
  }
  if (!deltas.length) return null;
  const mean = deltas.reduce((s, x) => s + x.d, 0) / deltas.length;
  const max  = deltas.reduce((m, x) => x.d > m.d ? x : m, deltas[0]);
  return { meanAbsDelta: mean, maxAbsDelta: max.d, maxFreqHz: max.f };
}

/**
 * "Ready to print?" checklist HTML.
 * @param {object} row       - The verify row (from report.rows).
 * @param {object|null} brief - Optional brief object with envelope fields.
 * @param {object|null} density - Density info.
 */
export function checklistHtml(row, brief, density) {
  if (!row) return "";
  const item = (icon, label, text, cls = "") =>
    `<li class="vfy-checklist-item${cls ? " " + cls : ""}">` +
    `<span class="vfy-check-icon" aria-hidden="true">${icon}</span>` +
    `<span><b>${esc(label)}</b>${text ? " — " + text : ""}</span></li>`;

  // Verified
  const verifiedOk = row.ok === true;
  const verifiedItem = verifiedOk
    ? item("✓", "Verified", "this design has a verify-tier solve", "pass")
    : item("✗", "Verified", row.error ? esc("failed: " + row.error) : "not verified", "fail");

  // Gates
  let gateItem;
  if (row.gates == null) {
    gateItem = item("?", "Gates", "not audited — run a gate audit to check", "unknown");
  } else {
    const failing = Object.entries(row.gates).filter(([, v]) => v === false).map(([k]) => k);
    if (failing.length === 0) {
      gateItem = item("✓", "Gates", "all audited gates pass", "pass");
    } else {
      gateItem = item("✗", "Gates", "fails: " + failing.map(esc).join(", "), "fail");
    }
  }

  // Fits size
  let sizeItem;
  if (!brief || (!brief.mouth_w_mm && !brief.envelope_w_mm)) {
    sizeItem = item("·", "Fits size", "no size limit in brief", "na");
  } else {
    const ew = brief.envelope_w_mm || brief.mouth_w_mm;
    const eh = brief.envelope_h_mm || brief.mouth_h_mm;
    const ed = brief.envelope_d_mm || brief.depth_mm;
    if (row.dims && ew && eh && ed) {
      const fits = row.dims.mouth_w_mm <= ew && row.dims.mouth_h_mm <= eh && row.dims.depth_mm <= ed;
      sizeItem = fits
        ? item("✓", "Fits size", "within brief envelope", "pass")
        : item("✗", "Fits size", "exceeds brief envelope", "fail");
    } else {
      sizeItem = item("·", "Fits size", "no size limit in brief", "na");
    }
  }

  // Export
  const exportItem = `<li class="vfy-checklist-item na"><span class="vfy-check-icon" aria-hidden="true">→</span><span><b>Export</b> — ` +
    `<code class="vfy-copyable">hornlab-search export-step --designs ${esc(row.hash || "")}</code>` +
    ` <span class="hint">(caveat: export-step ranks by screen J; verify --designs once job WP7 lands)</span></span></li>`;

  return `<ul class="vfy-checklist" aria-label="Ready to print checklist">
    ${verifiedItem}${gateItem}${sizeItem}${exportItem}
  </ul>`;
}

// ── WP6: Circular polar plot ───────────────────────────────────────────────

/**
 * Draw a circular polar directivity plot onto an SVG element.
 * C12 convention: half-circle for ±90°, full circle for ±180°.
 * Rings every 6 dB from 0 to −30 dB, spokes every 15° (labelled every 30°).
 * H solid (verify colour), V dashed; screen ghost optional.
 *
 * @param {SVGElement} svg
 * @param {number[][]|null} rowsH   2D [freq][angle], or null
 * @param {number[][]|null} rowsV   2D [freq][angle], or null
 * @param {number[]} angles         angle values in degrees (symmetric about 0°, e.g. −90..+90)
 * @param {number}   fIndex         frequency index to display
 * @param {object}   opts           { W, H, minDb, ghostH, ghostV, ghostFIndex }
 */
export function polarPlot(svg, rowsH, rowsV, angles, fIndex, opts) {
  if (!svg) return;
  const W      = opts && opts.W ? opts.W : 220;
  const H      = opts && opts.H ? opts.H : 220;
  const floor  = (opts && opts.minDb != null) ? opts.minDb : -30;
  const ghostH = (opts && opts.ghostH) || null;
  const ghostV = (opts && opts.ghostV) || null;
  const ghostFI = (opts && opts.ghostFIndex != null) ? opts.ghostFIndex : fIndex;

  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("width", W);
  svg.setAttribute("height", H);
  svg.innerHTML = "";

  if (!angles || !angles.length) return;

  const maxAbs = Math.max(...angles.map(a => Math.abs(a)));
  const isHalf = maxAbs <= 90.5;
  const pad    = 28;

  // Centre and radius
  const R  = isHalf ? Math.min(W - 2 * pad, H - pad - 10) : Math.min(W - 2 * pad, H - 2 * pad) / 2;
  const cx = W / 2;
  const cy = isHalf ? pad + R : H / 2;

  // Polar → SVG coords (0° = top, positive clockwise)
  const toXY = (angleDeg, r) => {
    const a = angleDeg * Math.PI / 180;
    return [cx + Math.sin(a) * r, cy - Math.cos(a) * r];
  };

  // Level → radius (0 dB = R, floor dB = 0)
  const lToR = lvl => {
    const v = lvl == null || !isFinite(lvl) ? floor : Math.min(0, lvl);
    return R * Math.max(0, (v - floor) / (0 - floor));
  };

  const ringCol  = css("--rule")  || "#a9b4bb";
  const tickCol  = css("--label") || "#46535e";
  const hCol     = css("--best")  || "#2277cc";
  const vCol     = css("--accent")|| "#c2417d";
  const ghostCol = css("--seed")  || "#e09028";

  // Helper: draw circle arc from -maxAbs to +maxAbs (or full)
  const arc = (r) => {
    if (isHalf) {
      const [x0, y0] = toXY(-maxAbs, r);
      const [x1, y1] = toXY(maxAbs, r);
      return `M${x0.toFixed(1)},${y0.toFixed(1)} A${r.toFixed(1)},${r.toFixed(1)} 0 0,1 ${x1.toFixed(1)},${y1.toFixed(1)}`;
    } else {
      return `M${cx},${(cy - r).toFixed(1)} A${r.toFixed(1)},${r.toFixed(1)} 0 1,1 ${cx},${(cy + r).toFixed(1)} A${r.toFixed(1)},${r.toFixed(1)} 0 1,1 ${cx},${(cy - r).toFixed(1)}`;
    }
  };

  // ── Rings (every 6 dB) ──
  for (let L = 0; L >= floor; L -= 6) {
    const r = lToR(L);
    if (r < 1) continue;
    const p = el("path", {
      d: arc(r), fill: "none",
      stroke: ringCol,
      "stroke-width": L === 0 ? 1.4 : 0.8,
      opacity: L === 0 ? "0.9" : "0.5"
    }, svg);
    // dB label on the left side of each ring
    if (L < 0) {
      const tx = el("text", {
        x: String((cx - r - 4).toFixed(1)), y: String((cy + 3).toFixed(1)),
        "text-anchor": "end", "font-size": "9", fill: tickCol, opacity: "0.7"
      }, svg);
      tx.textContent = String(L);
    }
  }

  // ── Spokes (every 15°, labelled every 30°) ──
  for (let a = -maxAbs; a <= maxAbs; a += 15) {
    const [sx, sy] = toXY(a, R * 0.05);
    const [ex, ey] = toXY(a, R);
    el("line", {
      x1: sx.toFixed(1), y1: sy.toFixed(1), x2: ex.toFixed(1), y2: ey.toFixed(1),
      stroke: ringCol, "stroke-width": "0.7", opacity: "0.4"
    }, svg);
    if (a % 30 === 0) {
      const [lx, ly] = toXY(a, R + 11);
      const anchor = a < -5 ? "end" : a > 5 ? "start" : "middle";
      const tx = el("text", {
        x: lx.toFixed(1), y: ly.toFixed(1),
        "text-anchor": anchor, "font-size": "9", fill: tickCol
      }, svg);
      tx.textContent = a === 0 ? "0°" : (a > 0 ? "+" : "") + a + "°";
    }
  }

  // ── Data curve helper ──
  const drawPolar = (vals, strokeColor, dash, opacity) => {
    if (!vals || !vals.length) return;
    const pts = angles.map((a, i) => {
      const r = lToR(vals[i]);
      return toXY(a, r);
    });
    // close for full circle
    const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + "," + p[1].toFixed(1)).join("") +
      (isHalf ? "" : " Z");
    el("path", {
      d, fill: "none", stroke: strokeColor,
      "stroke-width": "1.8", "stroke-linejoin": "round",
      "stroke-dasharray": dash || "none",
      opacity: opacity || "0.9"
    }, svg);
  };

  // Ghost (screen) curves first (behind verify)
  if (ghostH && ghostH[ghostFI]) drawPolar(ghostH[ghostFI], ghostCol, "4 3", "0.6");
  if (ghostV && ghostV[ghostFI]) drawPolar(ghostV[ghostFI], ghostCol, "2 2", "0.5");

  // Verify H (solid) and V (dashed)
  if (rowsH && rowsH[fIndex]) drawPolar(rowsH[fIndex], hCol, null, "0.9");
  if (rowsV && rowsV[fIndex]) drawPolar(rowsV[fIndex], vCol, "5 3", "0.9");

  // 0° label at top
  const [lx0, ly0] = toXY(0, R + 14);
  const tLabel = el("text", {
    x: lx0.toFixed(1), y: ly0.toFixed(1),
    "text-anchor": "middle", "font-size": "9", fill: tickCol
  }, svg);
  tLabel.textContent = "on-axis";
}

// ── Verify table HTML helpers ──────────────────────────────────────────────

function _hashShort(h) { return h ? h.slice(0, 8) : "–"; }

function _gateChips(gates, labels) {
  if (!gates) return '<span class="muted" style="font-size:0.8rem">not audited</span>';
  return Object.entries(gates).map(([k, v]) => {
    const lbl = (labels && labels[k]) || k;
    return `<span class="pill ${v ? "good" : "bad"}" style="font-size:0.72rem" title="${esc(k)}">${esc(lbl)}</span>`;
  }).join(" ");
}

function _laneText(lane, backend) {
  if (lane == null && backend == null) return "–";
  const parts = [];
  if (lane) parts.push(esc(lane));
  if (backend) parts.push(esc(backend));
  return parts.join(" / ") || "–";
}

function _densityText(d) {
  if (!d) return "–";
  const bg = d.balloon_grid ? d.balloon_grid.join("×") : "–";
  const pt = d.n_points != null ? d.n_points.toLocaleString() : "–";
  return `${esc(String(d.n_freqs || "–"))} f · ${esc(bg)} (${esc(pt)} pt)`;
}

function _tableRowHtml(row, selected, hasGates, gateLabels, objVersion) {
  const sel  = row.hash === selected;
  const hash = _hashShort(row.hash);
  const sj   = row.screen_j != null && isFinite(row.screen_j) ? fmt(row.screen_j) + " screen J v" + (objVersion || "?") : "–";
  const vj   = row.ok && row.verify_j != null && isFinite(row.verify_j) ? fmt(row.verify_j) + " verify J v" + (objVersion || "?") : (row.ok ? "–" : "failed");
  const delta = row.ok ? deltaCellHtml(row.screen_j, row.verify_j) : '<span class="pill bad" style="font-size:0.76rem">' + esc(row.error || "failed") + '</span>';
  const sr   = row.screen_rank != null ? String(row.screen_rank) : "–";
  const vr   = row.verify_rank != null ? String(row.verify_rank) : "–";
  const dof  = row.n_dof != null ? row.n_dof.toLocaleString() : "–";
  const tris = row.n_triangles != null ? row.n_triangles.toLocaleString() : "–";
  const gate = hasGates ? `<td class="vfy-gates">${_gateChips(row.gates, gateLabels)}</td>` : "";
  const lane = _laneText(row.lane, row.backend);
  return `<tr class="vfy-row${sel ? " vfy-row-selected" : ""}" data-hash="${esc(row.hash || "")}" tabindex="0"
      role="row" aria-selected="${sel ? "true" : "false"}">
    <td class="vfy-hash mono">${esc(hash)}</td>
    <td class="vfy-sj r">${esc(sj)}</td>
    <td class="vfy-vj r">${esc(vj)}</td>
    <td class="r">${delta}</td>
    <td class="r">${esc(sr)}</td>
    <td class="r">${esc(vr)}</td>
    ${gate}
    <td class="r"><span class="mono" style="font-size:0.76rem">${esc(dof)} / ${esc(tris)}</span></td>
    <td style="font-size:0.76rem">${esc(lane)}</td>
    <td class="vfy-actions"><button class="btn vfy-open-btn" data-hash="${esc(row.hash || "")}" aria-label="Open design ${esc(hash)}">${sel ? "open ✓" : "open"}</button></td>
  </tr>`;
}

// ── Scatter chart for screen J vs verify J ─────────────────────────────────

function _renderScatter(svgEl, rows, selectedHash, objVersion) {
  if (!svgEl) return;
  const pairs = rows.filter(r => r.ok && r.screen_j != null && r.verify_j != null
    && isFinite(r.screen_j) && isFinite(r.verify_j));
  if (!pairs.length) { svgEl.textContent = ""; return; }

  const xs = pairs.map(r => r.screen_j), ys = pairs.map(r => r.verify_j);
  const alo = Math.min(...xs, ...ys) * 0.98, ahi = Math.max(...xs, ...ys) * 1.02;
  const margin = (ahi - alo) * 0.08;
  const lo = alo - margin, hi = ahi + margin;
  const W = 280, H = 220;

  chart(svgEl, {
    W, H,
    xlim: [lo, hi], ylim: [lo, hi],
    xlabel: `screen J v${objVersion || "?"}`,
    ylabel: `verify J v${objVersion || "?"}`,
    hlines: [],
    vlines: [],
    series: [
      // diagonal y=x reference line
      { pts: [[lo, lo], [hi, hi]], color: css("--rule") || "#aaa", w: 1, dash: true },
      // dots
      { pts: pairs.map(r => [r.screen_j, r.verify_j]), color: css("--accent") || "#2277cc", dots: true, r: 4 },
    ],
  });

  // Add short-hash labels after chart() renders
  // Replicate chart()'s coordinate transforms for label placement:
  // m = { l: 44, r: 12, t: 20, b: 32 }   (ylabel present → t=20)
  const ml = 44, mr = 12, mt = 20, mb = 32;
  const X = v => ml + (v - lo) / (hi - lo) * (W - ml - mr);
  const Y = v => H - mb - (v - lo) / (hi - lo) * (H - mt - mb);

  for (const r of pairs) {
    const px = X(r.screen_j), py = Y(r.verify_j);
    const isSelected = r.hash === selectedHash;
    const tx = el("text", {
      x: (px + 6).toFixed(1), y: (py - 3).toFixed(1),
      "font-size": "9", fill: isSelected ? (css("--best") || "#2277cc") : (css("--label") || "#46535e"),
      "font-weight": isSelected ? "600" : "400",
    }, svgEl);
    tx.textContent = _hashShort(r.hash);
  }
}

// ── Per-design panel (WP6) ─────────────────────────────────────────────────

// Module-level panel state (one panel at a time per page)
const _ps = {
  runId:        null,
  hash:         null,
  fIndex:       0,
  ghost:        true,
  payload:      null,   // verify design_curves + extras
  ghostPayload: null,   // screen design_curves
  balloon:      null,   // { payload, ctrl }
  pendingRaf:   null,
  report:       null,   // the full verify report
};

// Cache: { 'run|tier|hash': payload }
const _designCache = {};

async function _fetchDesign(runId, hash, tier) {
  const key = `${runId}|${tier}|${hash}`;
  if (_designCache[key]) return _designCache[key];
  const p = await api(`/api/design/${encodeURIComponent(runId)}/${encodeURIComponent(hash)}?tier=${encodeURIComponent(tier)}`);
  _designCache[key] = p;
  return p;
}

// Cache for balloon payloads
const _balloonCache = {};
async function _fetchBalloon(runId, hash, tier) {
  const key = `${runId}|${tier}|${hash}`;
  if (_balloonCache[key]) return _balloonCache[key];
  const p = await api(`/api/balloon/${encodeURIComponent(runId)}/${encodeURIComponent(hash)}?tier=${encodeURIComponent(tier)}`);
  _balloonCache[key] = p;
  return p;
}

function _coalesceRaf(fn) {
  if (_ps.pendingRaf) cancelAnimationFrame(_ps.pendingRaf);
  _ps.pendingRaf = requestAnimationFrame(() => { _ps.pendingRaf = null; fn(); });
}

function _fmtFreqAriaText(freqs, fIndex) {
  if (!freqs || fIndex >= freqs.length) return "unknown";
  return `${fmtHz(freqs[fIndex])}, verify frequency ${fIndex + 1} of ${freqs.length}`;
}

/** Redraw all 2D charts and update the scrubber display — RAF-coalesced. */
function _redraw2d(panelEl) {
  _coalesceRaf(() => {
    if (!panelEl || !panelEl.isConnected || !_ps.payload) return;
    const P = _ps.payload, fi = _ps.fIndex;
    const freqs = P.freqs || [];

    // Update scrubber value label
    const fLbl = panelEl.querySelector("#vfy-freq-val");
    if (fLbl) fLbl.textContent = `${fmtHz(freqs[fi])} · ${fi + 1}/${freqs.length}`;
    const fIn = panelEl.querySelector("#vfy-freq-in");
    if (fIn) {
      fIn.value = String(fi);
      fIn.setAttribute("aria-valuetext", _fmtFreqAriaText(freqs, fi));
    }

    // ── H/V cut charts ──
    const hSvg = panelEl.querySelector("#vfy-hcut");
    const vSvg = panelEl.querySelector("#vfy-vcut");
    const angles = P.angles || [];
    const ghostFreqs = _ps.ghostPayload ? (_ps.ghostPayload.freqs || []) : null;
    const ghostFI = ghostFreqs ? nearestFreqIndex(ghostFreqs, freqs[fi]) : 0;

    if (hSvg && angles.length && P.polar_h) {
      const hVals = P.polar_h[fi] || [];
      const ghostH = (_ps.ghost && _ps.ghostPayload && _ps.ghostPayload.polar_h)
        ? _ps.ghostPayload.polar_h[ghostFI] : null;
      const series = [
        { pts: angles.map((a, i) => [a, hVals[i] ?? null]), color: css("--best") || "#2277cc", w: 2 },
        ...(ghostH ? [{ pts: angles.map((a, i) => [a, ghostH[i] ?? null]),
                       color: css("--seed") || "#e09028", w: 1.4, dash: true }] : []),
      ];
      chart(hSvg, {
        W: 220, H: 160,
        xlim: [Math.min(...angles), Math.max(...angles)],
        ylim: [-30, 0],
        xticks: niceTicks(Math.min(...angles), Math.max(...angles), 5),
        yticks: [-30, -24, -18, -12, -6, 0],
        xlabel: "deg", ylabel: "dB rel",
        series,
      });
    }

    if (vSvg && angles.length && P.polar_v) {
      const vVals = P.polar_v[fi] || [];
      const ghostV = (_ps.ghost && _ps.ghostPayload && _ps.ghostPayload.polar_v)
        ? _ps.ghostPayload.polar_v[ghostFI] : null;
      const series = [
        { pts: angles.map((a, i) => [a, vVals[i] ?? null]), color: css("--accent") || "#c2417d", w: 2 },
        ...(ghostV ? [{ pts: angles.map((a, i) => [a, ghostV[i] ?? null]),
                       color: css("--seed") || "#e09028", w: 1.4, dash: true }] : []),
      ];
      chart(vSvg, {
        W: 220, H: 160,
        xlim: [Math.min(...angles), Math.max(...angles)],
        ylim: [-30, 0],
        xticks: niceTicks(Math.min(...angles), Math.max(...angles), 5),
        yticks: [-30, -24, -18, -12, -6, 0],
        xlabel: "deg", ylabel: "dB rel",
        series,
      });
    }

    // ── Circular polar plot ──
    const polSvg = panelEl.querySelector("#vfy-polar");
    if (polSvg) {
      const ghostRows = (_ps.ghost && _ps.ghostPayload) ? {
        h: _ps.ghostPayload.polar_h,
        v: _ps.ghostPayload.polar_v,
      } : null;
      polarPlot(polSvg,
        P.polar_h, P.polar_v, angles, fi,
        {
          W: 220, H: 220,
          ghostH: ghostRows && ghostRows.h,
          ghostV: ghostRows && ghostRows.v,
          ghostFIndex: ghostFI,
        }
      );
    }

    // ── Curves (on-axis, DI, beamwidth) — vlines at current frequency ──
    _redrawCurves(panelEl, fi);

    // ── Update 3D balloon ──
    if (_ps.balloon && _ps.balloon.ctrl) {
      _ps.balloon.ctrl.setFreq(fi);
    }
  });
}

function _redrawCurves(panelEl, fi) {
  const P = _ps.payload, GP = _ps.ghost ? _ps.ghostPayload : null;
  if (!P) return;
  const freqs = P.freqs || [], gFreqs = GP ? (GP.freqs || []) : [];
  if (!freqs.length) return;
  const fLo = freqs[0], fHi = freqs[freqs.length - 1];
  const vMarker = { x: freqs[fi], color: css("--accent") || "#c2417d", dash: false };

  const curveChart = (svgId, verifyVals, ghostVals, ylim, yticks, lbl) => {
    const sv = panelEl.querySelector("#" + svgId);
    if (!sv || !verifyVals) return;
    const xt = logTicks(fLo, fHi);
    const series = [
      { pts: freqs.map((f, i) => [f, verifyVals[i] ?? null]),
        color: css("--best") || "#2277cc", w: 2 },
      ...(ghostVals && gFreqs.length ? [{
        pts: gFreqs.map((f, i) => [f, ghostVals[i] ?? null]),
        color: css("--seed") || "#e09028", w: 1.4, dash: true
      }] : []),
    ];
    chart(sv, {
      W: 320, H: 160,
      xlog: true, xlim: [fLo, fHi],
      ylim, xticks: xt, yticks,
      ylabel: lbl,
      vlines: [vMarker],
      series,
    });
  };

  if (P.on_axis) {
    const finiteVals = P.on_axis.filter(v => v != null && isFinite(v));
    const lo = finiteVals.length ? Math.min(-15, Math.floor(Math.min(...finiteVals))) : -15;
    const hi = finiteVals.length ? Math.max(10, Math.ceil(Math.max(...finiteVals))) : 10;
    curveChart("vfy-axis", P.on_axis, GP && GP.on_axis,
      [Math.min(-15, lo), Math.max(10, hi)],
      niceTicks(Math.min(-15, lo), Math.max(10, hi), 5), "dB");
  }
  if (P.di) {
    curveChart("vfy-di", P.di, GP && GP.di,
      [0, 15], [0, 3, 6, 9, 12, 15], "DI dB");
  }
  if (P.bw_h) {
    curveChart("vfy-bwh", P.bw_h, GP && GP.bw_h,
      [0, 180], [0, 30, 60, 90, 120, 150, 180], "bw H °");
  }
  if (P.bw_v) {
    curveChart("vfy-bwv", P.bw_v, GP && GP.bw_v,
      [0, 180], [0, 30, 60, 90, 120, 150, 180], "bw V °");
  }
}

/** Dispose the 3D balloon if one is running. */
function _disposeBalloon() {
  if (_ps.balloon && _ps.balloon.ctrl) {
    _ps.balloon.ctrl.dispose();
  }
  _ps.balloon = null;
}

function _ghostLabelText(ghostFreqs, verifyFreqHz) {
  if (!ghostFreqs || !ghostFreqs.length) return "screen";
  const fi = nearestFreqIndex(ghostFreqs, verifyFreqHz);
  const gf = ghostFreqs[fi];
  if (gf == null || !isFinite(gf)) return "screen";
  if (Math.abs(gf - verifyFreqHz) < verifyFreqHz * 0.03) return "screen";
  return `screen @ ${fmtHz(gf)}`;
}

/** Build the per-design panel HTML. */
function _panelHtml(hash, row, report) {
  const shortHash = _hashShort(hash);
  const gates = row && row.gates;
  const density = row && row.density;
  const gateAudit = report && report.gate_audit;
  const objV = report && report.objective_version;

  const gateHtml = gates == null
    ? `<span class="muted">Gates: not audited</span>`
    : Object.entries(gates).map(([k, v]) => {
        const lbl = (gateAudit && gateAudit.labels && gateAudit.labels[k]) || k;
        return `<span class="pill ${v ? "good" : "bad"}" title="${esc(k)}">${esc(lbl)} ${v ? "✓" : "✗"}</span>`;
      }).join(" ");

  const densityLine = density
    ? `verify ${esc(String(density.n_freqs))} f · ${esc(String(density.n_points != null ? density.n_points.toLocaleString() : "–"))} pt · ${row && row.n_dof != null ? row.n_dof.toLocaleString() : "–"} dof`
    : "density unavailable";

  return `<div class="vfy-panel stack" id="vfy-panel-inner" role="region" aria-label="Design ${esc(shortHash)} detail">
    <div class="vfy-panel-head">
      <div>
        <span class="eyebrow">Design ${esc(shortHash)}</span>
        <span class="pill verify-tier-pill">verify</span>
        ${objV != null ? `<span class="pill">J v${esc(String(objV))}</span>` : ""}
      </div>
      <div class="vfy-panel-actions">
        <button class="btn" id="vfy-compare-btn" aria-label="Compare two designs">Compare…</button>
        <button class="btn" id="vfy-copy-hash-btn" data-copy="${esc(hash || "")}" aria-label="Copy hash">Copy hash</button>
      </div>
    </div>

    <div class="vfy-freq-row card" role="group" aria-label="Frequency scrubber">
      <label for="vfy-freq-in">Frequency</label>
      <input id="vfy-freq-in" type="range" min="0" max="0" value="0" step="1"
        aria-label="Frequency" aria-valuetext="unknown" class="vfy-freq-slider">
      <span id="vfy-freq-val" class="mono" aria-live="polite">–</span>
      <label class="vfy-ghost-label">
        <input type="checkbox" id="vfy-ghost-chk" ${_ps.ghost ? "checked" : ""}>
        screen ghost
      </label>
      <span id="vfy-ghost-label-txt" class="muted" style="font-size:0.8rem"></span>
    </div>

    <div class="vfy-charts-row grid2" style="gap:12px">
      <div class="fig">
        <h3>3D balloon (verify)</h3>
        <div class="cap">verify-tier only; shape = level, colour = directivity palette, −30…0 dB.</div>
        <div id="vfy-balloon-wrap" data-v3d style="height:280px;position:relative">
          <div class="view3d-fallback">Loading 3D…</div>
        </div>
        <div id="vfy-balloon-hover" class="mono" aria-live="polite" style="font-size:0.76rem;min-height:1.2em"></div>
      </div>
      <div class="stack" style="gap:10px">
        <div class="fig">
          <h3>H cut</h3>
          <div class="cap">Horizontal polar cut at the scrubbed frequency. Normalised to on-axis.</div>
          <svg id="vfy-hcut" role="img" aria-label="Horizontal polar cut"></svg>
        </div>
        <div class="fig">
          <h3>V cut</h3>
          <div class="cap">Vertical polar cut. Normalised to on-axis.</div>
          <svg id="vfy-vcut" role="img" aria-label="Vertical polar cut"></svg>
        </div>
      </div>
    </div>

    <div class="grid2" style="gap:12px">
      <div class="fig">
        <h3>Circular polar (verify)</h3>
        <div class="cap">Classic audio polar at the scrubbed frequency. H solid, V dashed. 0 dB = outer ring; rings every 6 dB.</div>
        <svg id="vfy-polar" role="img" aria-label="Circular polar directivity plot"></svg>
      </div>
      <div class="fig">
        <h3>H isobar map (verify)</h3>
        <div class="cap">Directivity level vs frequency × angle. Normalised to on-axis per frequency. Same palette as the 3D balloon.</div>
        <svg id="vfy-isobar-h" role="img" aria-label="H isobar map"></svg>
      </div>
    </div>

    <div class="vfy-curves-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
      <div class="fig"><h3>On-axis response (verify)</h3>
        <div class="cap">Mean removed. verify solid${_ps.ghost ? ", screen dashed" : ""}. Marker at current frequency.</div>
        <svg id="vfy-axis" role="img" aria-label="On-axis response"></svg>
      </div>
      <div class="fig"><h3>Directivity index</h3>
        <div class="cap">verify solid${_ps.ghost ? ", screen dashed" : ""}. Fixed 0–15 dB.</div>
        <svg id="vfy-di" role="img" aria-label="Directivity index"></svg>
      </div>
      <div class="fig"><h3>Beamwidth H</h3>
        <svg id="vfy-bwh" role="img" aria-label="Beamwidth H"></svg>
      </div>
      <div class="fig"><h3>Beamwidth V</h3>
        <svg id="vfy-bwv" role="img" aria-label="Beamwidth V"></svg>
      </div>
    </div>

    <div class="card vfy-gates-card">
      <div class="vfy-gates-row">${gateHtml}</div>
      ${gateAudit && gateAudit.source ? `<p class="muted" style="font-size:0.76rem;margin:4px 0 0">audit: ${esc(gateAudit.source)}</p>` : ""}
    </div>

    <div class="card vfy-density-card">
      <span class="muted">Density: </span>${esc(densityLine)}
    </div>

    <details class="card vfy-checklist-card" open>
      <summary><b>Ready to print?</b></summary>
      <div id="vfy-checklist-wrap">${checklistHtml(row, null, density)}</div>
    </details>
  </div>`;
}

/** Load a design into the panel. */
async function _loadPanel(panelEl, runId, hash) {
  if (!hash || !panelEl || !panelEl.isConnected) return;

  // Dispose previous 3D
  _disposeBalloon();

  // Show loading state
  const inner = panelEl.querySelector("#vfy-panel-inner");
  if (inner) inner.style.opacity = "0.5";

  let payload;
  try {
    payload = await _fetchDesign(runId, hash, "verify");
  } catch (e) {
    if (panelEl.isConnected)
      panelEl.innerHTML = errBanner("Could not load design " + hash + ": " + e.message);
    return;
  }
  if (!panelEl.isConnected) return;

  _ps.hash    = hash;
  _ps.payload = payload;

  // Fetch ghost (screen) in background if enabled
  if (_ps.ghost) {
    _fetchDesign(runId, hash, "screen").then(gp => {
      _ps.ghostPayload = gp;
      _redraw2d(panelEl);
    }).catch(() => { /* screen design may not exist */ });
  } else {
    _ps.ghostPayload = null;
  }

  // Find the row in the report
  const row = _ps.report && _ps.report.rows
    ? _ps.report.rows.find(r => r.hash === hash) : null;

  // Replace panel content
  panelEl.innerHTML = _panelHtml(hash, row, _ps.report);

  // Wire scrubber
  const freqIn = panelEl.querySelector("#vfy-freq-in");
  const freqs  = payload.freqs || [];
  if (freqIn && freqs.length) {
    freqIn.max   = String(freqs.length - 1);
    freqIn.value = String(_ps.fIndex);
    freqIn.setAttribute("aria-valuetext", _fmtFreqAriaText(freqs, _ps.fIndex));
    freqIn.addEventListener("input", () => {
      _ps.fIndex = Math.max(0, Math.min(freqs.length - 1, +freqIn.value | 0));
      _redraw2d(panelEl);
    });
    freqIn.addEventListener("keydown", e => {
      let d = 0;
      if (e.key === "ArrowLeft" || e.key === "ArrowDown") d = -1;
      if (e.key === "ArrowRight" || e.key === "ArrowUp") d = 1;
      if (!d) return;
      e.preventDefault();
      _ps.fIndex = Math.max(0, Math.min(freqs.length - 1, _ps.fIndex + d));
      freqIn.value = String(_ps.fIndex);
      _redraw2d(panelEl);
    });
  }

  // Wire ghost checkbox
  const ghostChk = panelEl.querySelector("#vfy-ghost-chk");
  if (ghostChk) {
    ghostChk.addEventListener("change", () => {
      _ps.ghost = ghostChk.checked;
      try { localStorage.setItem("vfy-ghost", _ps.ghost ? "1" : "0"); } catch (_) {}
      if (_ps.ghost && !_ps.ghostPayload) {
        _fetchDesign(runId, hash, "screen").then(gp => {
          _ps.ghostPayload = gp;
          _redraw2d(panelEl);
        }).catch(() => {});
      } else {
        _redraw2d(panelEl);
      }
    });
  }

  // Wire copy-hash button
  const copyBtn = panelEl.querySelector("#vfy-copy-hash-btn");
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      navigator.clipboard && navigator.clipboard.writeText(hash).catch(() => {});
    });
  }

  // Wire compare button
  const compareBtn = panelEl.querySelector("#vfy-compare-btn");
  if (compareBtn) {
    compareBtn.addEventListener("click", () => {
      location.hash = `#/run/${encodeURIComponent(runId)}/verify/compare?a=${encodeURIComponent(hash)}`;
    });
  }

  // Start 2D charts immediately
  _redraw2d(panelEl);

  // Render isobar map
  const isoH = panelEl.querySelector("#vfy-isobar-h");
  if (isoH && payload.polar_h && freqs.length && payload.angles) {
    isobarMap(isoH, payload.polar_h, payload.angles, freqs, {
      H: 220,
      title: "H horizontal",
      angleTicks: (payload.angles || []).filter((_, i) => i % Math.max(1, Math.floor((payload.angles.length - 1) / 6)) === 0),
    });
  }

  // Start 3D balloon
  const balloonWrap = panelEl.querySelector("#vfy-balloon-wrap");
  if (balloonWrap) {
    _fetchBalloon(runId, hash, "verify").then(async bp => {
      if (!balloonWrap.isConnected) return;
      const hoverEl = panelEl.querySelector("#vfy-balloon-hover");
      const ctrl = await initBalloon3d(balloonWrap, bp, {
        hover: t => { if (hoverEl) hoverEl.textContent = t; }
      });
      _ps.balloon = { payload: bp, ctrl };
      if (ctrl) ctrl.setFreq(_ps.fIndex);
    }).catch(() => {
      if (balloonWrap.isConnected)
        balloonWrap.innerHTML = `<div class="view3d-fallback">Balloon unavailable.</div>`;
    });
  }
}

// ── Compare two verified (WP6) ─────────────────────────────────────────────

async function _renderCompare(ROOT, runId, query) {
  skel(ROOT, "Loading verify report for compare view…");
  let report;
  try {
    report = await api(`/api/verify/${encodeURIComponent(runId)}`);
  } catch (e) {
    if (ROOT.isConnected) ROOT.innerHTML = errBanner("Could not load verify report: " + e.message);
    return;
  }
  if (!ROOT.isConnected) return;

  const q   = parseVerifyQuery(query);
  const verified = (report.rows || []).filter(r => r.ok);
  const opts = verified.map(r =>
    `<option value="${esc(r.hash || "")}">${esc(_hashShort(r.hash))} · verify J ${esc(r.verify_j != null ? fmt(r.verify_j) : "–")}</option>`
  ).join("");

  if (!verified.length) {
    ROOT.innerHTML = `<div class="stack" style="max-width:860px">
      <p class="muted">← <a href="#/run/${esc(runId)}/verify">back to verify view</a></p>
      <h2>Compare two verified designs</h2>
      <p class="muted">No successfully verified designs to compare yet.</p>
    </div>`;
    return;
  }

  ROOT.innerHTML = `<div class="stack" style="max-width:1100px;gap:18px">
    <p class="muted">← <a href="#/run/${esc(runId)}/verify">back to verify view</a></p>
    <div class="eyebrow">VERIFY · compare two · run ${esc(runId)}</div>
    <h2>Compare verified designs</h2>
    <p class="muted">Differences only, no verdict. Both designs from run ${esc(runId)} at verify tier.</p>
    <div class="card vfy-compare-sel" role="group" aria-label="Select designs">
      <label for="vfy-cmp-a">Design A</label>
      <select id="vfy-cmp-a" aria-label="Design A">${opts}</select>
      <label for="vfy-cmp-b">Design B</label>
      <select id="vfy-cmp-b" aria-label="Design B">${opts}</select>
      <button class="btn primary" id="vfy-cmp-go">Compare</button>
    </div>
    <div id="vfy-cmp-result"></div>
  </div>`;

  // Pre-select from URL
  const selA = ROOT.querySelector("#vfy-cmp-a");
  const selB = ROOT.querySelector("#vfy-cmp-b");
  if (q.compareA && selA) selA.value = q.compareA;
  if (q.compareB && selB) selB.value = q.compareB;
  // Default B to second verified design if not specified
  if (!q.compareB && verified.length > 1 && selB) selB.value = verified[1].hash;

  const goBtn = ROOT.querySelector("#vfy-cmp-go");
  if (goBtn) {
    goBtn.addEventListener("click", () => {
      const ha = selA && selA.value, hb = selB && selB.value;
      if (!ha || !hb) return;
      location.hash = `#/run/${encodeURIComponent(runId)}/verify/compare?a=${encodeURIComponent(ha)}&b=${encodeURIComponent(hb)}`;
    });
  }

  // Auto-compare if both hashes in URL
  if (q.compareA && q.compareB && q.compareA !== q.compareB) {
    _runCompare(ROOT, runId, q.compareA, q.compareB, report);
  }
}

async function _runCompare(ROOT, runId, hashA, hashB, report) {
  const resultEl = ROOT && ROOT.querySelector("#vfy-cmp-result");
  if (!resultEl) return;
  resultEl.innerHTML = `<p class="muted">Loading…</p>`;
  let pA, pB;
  try {
    [pA, pB] = await Promise.all([
      _fetchDesign(runId, hashA, "verify"),
      _fetchDesign(runId, hashB, "verify"),
    ]);
  } catch (e) {
    resultEl.innerHTML = errBanner("Could not load designs: " + e.message);
    return;
  }
  if (!resultEl.isConnected) return;

  // Check for comparable bands/objective versions
  const rA = report.rows && report.rows.find(r => r.hash === hashA);
  const rB = report.rows && report.rows.find(r => r.hash === hashB);

  const freqs = pA.freqs || [], freqsB = pB.freqs || [];
  const angles = pA.angles || [];
  let cmpFi = 0;

  resultEl.innerHTML = `<div class="stack" style="gap:14px">
    <h3>A: ${esc(_hashShort(hashA))} vs B: ${esc(_hashShort(hashB))}</h3>
    <div class="card vfy-compare-sel" role="group" aria-label="Shared frequency">
      <label for="vfy-cmp-freq">Frequency</label>
      <input id="vfy-cmp-freq" type="range" min="0" max="${esc(String(Math.max(0, freqs.length - 1)))}" value="0" step="1" aria-label="Frequency">
      <span id="vfy-cmp-freq-val" class="mono">${fmtHz(freqs[0])}</span>
    </div>
    <div class="grid2">
      <div class="fig"><h3>H cut</h3>
        <svg id="vfy-cmp-hcut" role="img" aria-label="H cut comparison"></svg>
      </div>
      <div class="fig"><h3>V cut</h3>
        <svg id="vfy-cmp-vcut" role="img" aria-label="V cut comparison"></svg>
      </div>
    </div>
    <div class="grid2">
      <div class="fig"><h3>On-axis</h3>
        <svg id="vfy-cmp-axis" role="img" aria-label="On-axis comparison"></svg>
      </div>
      <div class="fig"><h3>DI</h3>
        <svg id="vfy-cmp-di" role="img" aria-label="DI comparison"></svg>
      </div>
    </div>
    <div class="tbl-wrap"><table class="compact" id="vfy-cmp-tbl">
      <thead><tr><th>Hash</th><th>screen J</th><th>verify J</th><th>gates</th><th>dof</th></tr></thead>
      <tbody>
        <tr><td class="mono">${esc(_hashShort(hashA))}</td><td class="r">${rA && rA.screen_j != null ? fmt(rA.screen_j) : "–"}</td><td class="r">${rA && rA.verify_j != null ? fmt(rA.verify_j) : "–"}</td><td>${_gateChips(rA && rA.gates, report.gate_audit && report.gate_audit.labels)}</td><td class="r">${rA && rA.n_dof != null ? rA.n_dof.toLocaleString() : "–"}</td></tr>
        <tr><td class="mono">${esc(_hashShort(hashB))}</td><td class="r">${rB && rB.screen_j != null ? fmt(rB.screen_j) : "–"}</td><td class="r">${rB && rB.verify_j != null ? fmt(rB.verify_j) : "–"}</td><td>${_gateChips(rB && rB.gates, report.gate_audit && report.gate_audit.labels)}</td><td class="r">${rB && rB.n_dof != null ? rB.n_dof.toLocaleString() : "–"}</td></tr>
      </tbody>
    </table></div>
  </div>`;

  const drawCmpCharts = (fi) => {
    const fLo = freqs[0], fHi = freqs[freqs.length - 1];
    const xt = logTicks(fLo, fHi);
    const fiBv = nearestFreqIndex(freqsB, freqs[fi]);
    const vMark = { x: freqs[fi], color: css("--accent") || "#c2417d" };

    // H cut
    const hcv = resultEl.querySelector("#vfy-cmp-hcut");
    if (hcv && pA.polar_h && pB.polar_h && angles.length) {
      chart(hcv, {
        W: 240, H: 160, xlim: [Math.min(...angles), Math.max(...angles)],
        ylim: [-30, 0], xticks: niceTicks(Math.min(...angles), Math.max(...angles), 5),
        yticks: [-30, -24, -18, -12, -6, 0], xlabel: "deg", ylabel: "dB",
        series: [
          { pts: angles.map((a, i) => [a, pA.polar_h[fi] && pA.polar_h[fi][i] != null ? pA.polar_h[fi][i] : null]), color: css("--best") || "#2277cc", w: 2 },
          { pts: angles.map((a, i) => [a, pB.polar_h[fiBv] && pB.polar_h[fiBv][i] != null ? pB.polar_h[fiBv][i] : null]), color: css("--accent") || "#c2417d", w: 2, dash: true },
        ],
      });
    }
    // V cut
    const vcv = resultEl.querySelector("#vfy-cmp-vcut");
    if (vcv && pA.polar_v && pB.polar_v && angles.length) {
      chart(vcv, {
        W: 240, H: 160, xlim: [Math.min(...angles), Math.max(...angles)],
        ylim: [-30, 0], xticks: niceTicks(Math.min(...angles), Math.max(...angles), 5),
        yticks: [-30, -24, -18, -12, -6, 0], xlabel: "deg", ylabel: "dB",
        series: [
          { pts: angles.map((a, i) => [a, pA.polar_v[fi] && pA.polar_v[fi][i] != null ? pA.polar_v[fi][i] : null]), color: css("--best") || "#2277cc", w: 2 },
          { pts: angles.map((a, i) => [a, pB.polar_v[fiBv] && pB.polar_v[fiBv][i] != null ? pB.polar_v[fiBv][i] : null]), color: css("--accent") || "#c2417d", w: 2, dash: true },
        ],
      });
    }
    // On-axis
    const axv = resultEl.querySelector("#vfy-cmp-axis");
    if (axv && pA.on_axis && pB.on_axis && freqs.length) {
      chart(axv, {
        W: 320, H: 160, xlog: true, xlim: [fLo, fHi], ylim: [-15, 10],
        xticks: xt, yticks: niceTicks(-15, 10, 5), ylabel: "dB", vlines: [vMark],
        series: [
          { pts: freqs.map((f, i) => [f, pA.on_axis[i] ?? null]), color: css("--best") || "#2277cc", w: 2 },
          { pts: freqsB.map((f, i) => [f, pB.on_axis[i] ?? null]), color: css("--accent") || "#c2417d", w: 2, dash: true },
        ],
      });
    }
    // DI
    const div = resultEl.querySelector("#vfy-cmp-di");
    if (div && pA.di && pB.di && freqs.length) {
      chart(div, {
        W: 320, H: 160, xlog: true, xlim: [fLo, fHi], ylim: [0, 15],
        xticks: xt, yticks: [0, 3, 6, 9, 12, 15], ylabel: "DI dB", vlines: [vMark],
        series: [
          { pts: freqs.map((f, i) => [f, pA.di[i] ?? null]), color: css("--best") || "#2277cc", w: 2 },
          { pts: freqsB.map((f, i) => [f, pB.di[i] ?? null]), color: css("--accent") || "#c2417d", w: 2, dash: true },
        ],
      });
    }
  };

  drawCmpCharts(cmpFi);

  const freqInC = resultEl.querySelector("#vfy-cmp-freq");
  const freqValC = resultEl.querySelector("#vfy-cmp-freq-val");
  if (freqInC) {
    freqInC.addEventListener("input", () => {
      cmpFi = Math.max(0, Math.min(freqs.length - 1, +freqInC.value | 0));
      if (freqValC) freqValC.textContent = fmtHz(freqs[cmpFi]);
      drawCmpCharts(cmpFi);
    });
  }
}

// ── Main entry point ───────────────────────────────────────────────────────

/**
 * Render the verify view for a run.
 *
 * @param {HTMLElement} root   - The view-root element (replaced on every navigation).
 * @param {string}      runId  - Run id string.
 * @param {string}      mode   - "table" or "compare".
 * @param {string}      query  - Query string (without leading "?").
 */
export async function viewVerify(root, runId, mode, query) {
  if (mode === "compare") {
    await _renderCompare(root, runId, query);
    return;
  }

  // ── mode === "table" ──────────────────────────────────────────────
  skel(root, "Loading verify data…");

  // Read ghost preference from localStorage
  try {
    const stored = localStorage.getItem("vfy-ghost");
    if (stored === "0") _ps.ghost = false;
    else _ps.ghost = true;
  } catch (_) { _ps.ghost = true; }

  let report;
  try {
    report = await api(`/api/verify/${encodeURIComponent(runId)}`);
  } catch (e) {
    if (root.isConnected) root.innerHTML = errBanner("Could not load verify data: " + e.message);
    return;
  }
  if (!root.isConnected) return;

  _ps.report = report;

  const q   = parseVerifyQuery(query);
  const rows = report.rows || [];
  const hasGates = !!(report.gate_audit && report.gate_audit.available);
  const labels = hasGates ? (report.gate_audit.labels || {}) : {};
  const objV = report.objective_version;

  // ── Handle redirect (linked verify run → show parent) ──
  if (report.redirect_to || (report.kind === "redirect")) {
    const parentId = report.redirect_to;
    const missing  = report.parent_missing;
    root.innerHTML = `<div class="stack" style="max-width:860px;gap:16px">
      <p class="muted">← <a href="#/run/${esc(runId)}">${esc(runId)}</a></p>
      <div class="alert warn" role="alert">
        <b>This is a linked verify run.</b>
        ${missing
          ? " Its parent run is not in this runs folder."
          : (parentId
            ? ` It is paired with <a href="#/run/${esc(parentId)}/verify">the parent run's verify view →</a>`
            : " Parent run information unavailable.")}
      </div>
      ${parentId && !missing ? `<p><a class="btn primary" href="#/run/${esc(parentId)}/verify">Open parent verify view →</a></p>` : ""}
    </div>`;
    return;
  }

  // ── Build table state ──
  let sortKey  = q.sort || "verify_j";
  let sortDir  = q.dir  || "asc";
  let showMode = q.show || "all";
  let selectedHash = q.design || null;

  const getFilteredRows = () => {
    let r = rows;
    if (showMode === "gate-pass") r = r.filter(row => row.gates && Object.values(row.gates).every(Boolean));
    if (showMode === "failed")    r = r.filter(row => !row.ok);
    return sortRows(r, sortKey, sortDir);
  };

  const pushUrl = () => {
    const qs = buildVerifyQuery({ design: selectedHash, sort: sortKey, dir: sortDir, show: showMode, ghost: _ps.ghost });
    history.replaceState(null, "", location.pathname + location.search + "#/run/" + encodeURIComponent(runId) + "/verify" + (qs ? "?" + qs : ""));
  };

  // ── Render page ──
  const isStandalone = report.kind === "standalone";
  const bandText = report.band_hz ? `${fmtHz(report.band_hz[0])}–${fmtHz(report.band_hz[1])}` : "–";

  root.innerHTML = `<div class="stack" style="max-width:1100px;gap:18px">
    <p class="muted">← <a href="#/run/${esc(runId)}">${esc(runId)}</a></p>
    <div class="eyebrow">VERIFY · J v${esc(String(objV || "?"))} · ${esc(bandText)}</div>
    <h2>Verification of ${esc(report.name || runId)}</h2>
    ${isStandalone ? standaloneHeaderHtml() : ""}
    <p class="muted" style="font-size:0.85rem">The verify tier uses more frequencies and a finer balloon grid than the screen tier. J scores from different tiers are not directly comparable — they measure the same design at different fidelity.</p>
    ${fidelityPillsHtml(report)}
    ${!report.comparable
      ? `<div class="alert warn" role="alert">Screen and verify results are not comparable: ${esc(report.comparable_reason || "unknown reason")}. Delta, rank, and bias values are unavailable.</div>`
      : ""}
    ${report.state === "possibly_running"
      ? `<div class="alert warn" role="alert">Verify may still be running (last row was recent).</div>`
      : ""}
    ${report.latest_only
      ? `<p class="hint">Some hashes were verified more than once; only the latest result per hash is shown.</p>`
      : ""}

    <div id="vfy-summary">${summaryHtml({ ...report.summary, objective_version: objV })}</div>

    <div class="fig" id="vfy-scatter-wrap" style="max-width:340px">
      <h3>Screen J vs verify J</h3>
      <div class="cap">Diagonal = no change. Points above the diagonal → verify worse than screen (common: coarser screen underestimates cost). Screen J = J v${esc(String(objV || "?"))} screen, verify J = J v${esc(String(objV || "?"))} verify.</div>
      <svg id="vfy-scatter" role="img" aria-label="Screen J vs verify J scatter"></svg>
    </div>

    ${!rows.length ? `<div id="vfy-empty">${emptyStateHtml(runId)}</div>` : ""}

    <div id="vfy-toolbar" class="filter-bar" role="toolbar" aria-label="Table controls">
      <span class="filter-label">Sort</span>
      <select id="vfy-sort-sel" aria-label="Sort column">
        <option value="verify_j" ${sortKey === "verify_j" ? "selected" : ""}>Verify J</option>
        <option value="screen_j" ${sortKey === "screen_j" ? "selected" : ""}>Screen J</option>
        <option value="delta_j"  ${sortKey === "delta_j"  ? "selected" : ""}>Δ J</option>
        <option value="screen_rank" ${sortKey === "screen_rank" ? "selected" : ""}>Screen rank</option>
        <option value="verify_rank" ${sortKey === "verify_rank" ? "selected" : ""}>Verify rank</option>
      </select>
      <select id="vfy-dir-sel" aria-label="Sort direction">
        <option value="asc"  ${sortDir === "asc"  ? "selected" : ""}>Ascending</option>
        <option value="desc" ${sortDir === "desc" ? "selected" : ""}>Descending</option>
      </select>
      <span class="filter-label">Show</span>
      <select id="vfy-show-sel" aria-label="Filter rows">
        <option value="all"       ${showMode === "all"       ? "selected" : ""}>All</option>
        <option value="gate-pass" ${showMode === "gate-pass" ? "selected" : ""}>Gate-pass</option>
        <option value="failed"    ${showMode === "failed"    ? "selected" : ""}>Failed only</option>
      </select>
      <label class="filter-label">
        <input type="checkbox" id="vfy-ghost-toolbar" ${_ps.ghost ? "checked" : ""}>
        Screen ghost
      </label>
      ${rows.length ? `<a class="btn" href="#/run/${esc(runId)}/verify/compare">Compare two…</a>` : ""}
    </div>

    <div id="vfy-table-wrap" class="tbl-wrap" role="region" aria-label="Verified designs table">
      <table id="vfy-table" class="compact" role="grid">
        <thead>
          <tr>
            <th scope="col">Design</th>
            <th scope="col" aria-sort="${sortKey === "screen_j" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}">Screen J</th>
            <th scope="col" aria-sort="${sortKey === "verify_j" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}">Verify J</th>
            <th scope="col" aria-sort="${sortKey === "delta_j"  ? (sortDir === "asc" ? "ascending" : "descending") : "none"}">Δ (v−s)</th>
            <th scope="col" aria-sort="${sortKey === "screen_rank" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}">Screen rank</th>
            <th scope="col" aria-sort="${sortKey === "verify_rank" ? (sortDir === "asc" ? "ascending" : "descending") : "none"}">Verify rank</th>
            ${hasGates ? `<th scope="col">Gates</th>` : ""}
            <th scope="col">dof / tris</th>
            <th scope="col">lane</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody id="vfy-tbody"></tbody>
      </table>
      <p class="cap" style="margin:6px 0 0">Ranked by verify J (ascending). Screen J is context only — coarser grid. Δ is a fidelity diagnostic: positive = verify sees higher cost (worse) than screen predicted.</p>
    </div>

    <div id="vfy-panel" class="card" aria-live="polite" role="region" aria-label="Selected design detail">
      <p class="muted" style="padding:16px">Select a row above to open the design detail panel.</p>
    </div>
    <div id="vfy-announce" class="sr-only" aria-live="polite" aria-atomic="true"></div>
  </div>`;

  // ── Render scatter ──
  const scatterSvg = root.querySelector("#vfy-scatter");
  if (scatterSvg) _renderScatter(scatterSvg, rows, selectedHash, objV);

  // ── Render table ──
  const tbody = root.querySelector("#vfy-tbody");
  const rebuildTable = () => {
    if (!tbody || !tbody.isConnected) return;
    const filtered = getFilteredRows();
    tbody.innerHTML = filtered.map(r => _tableRowHtml(r, selectedHash, hasGates, labels, objV)).join("");
    // Wire row clicks and keyboard
    tbody.querySelectorAll(".vfy-row").forEach(tr => {
      const h = tr.dataset.hash;
      const openPanel = () => {
        selectedHash = h;
        pushUrl();
        // Update aria-selected on all rows
        tbody.querySelectorAll(".vfy-row").forEach(r => r.setAttribute("aria-selected", String(r.dataset.hash === h)));
        // Announce
        const ann = root.querySelector("#vfy-announce");
        if (ann) ann.textContent = `Design ${_hashShort(h)} selected`;
        // Update scatter
        if (scatterSvg) _renderScatter(scatterSvg, rows, selectedHash, objV);
        // Load panel
        const panelEl = root.querySelector("#vfy-panel");
        if (panelEl) _loadPanel(panelEl, runId, h);
      };
      tr.addEventListener("click", openPanel);
      tr.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); openPanel(); } });
    });

    // Wire open buttons
    tbody.querySelectorAll(".vfy-open-btn").forEach(btn => {
      btn.addEventListener("click", e => { e.stopPropagation(); });
    });
  };
  rebuildTable();

  // Wire toolbar controls
  const sortSel  = root.querySelector("#vfy-sort-sel");
  const dirSel   = root.querySelector("#vfy-dir-sel");
  const showSel  = root.querySelector("#vfy-show-sel");
  const ghostChk = root.querySelector("#vfy-ghost-toolbar");

  if (sortSel) sortSel.addEventListener("change", () => {
    sortKey = sortSel.value; rebuildTable(); pushUrl();
    // Update aria-sort on table headers
    const ths = root.querySelectorAll("#vfy-table th[aria-sort]");
    ths.forEach(th => { th.setAttribute("aria-sort", "none"); });
    const targetTh = root.querySelector(`#vfy-table th[aria-sort]:not([aria-sort="none"])`);
    // Minimal aria-sort update: set on current col
    root.querySelectorAll("#vfy-table thead th").forEach(th => {
      const lbl = th.textContent.trim().toLowerCase().replace(/ /g, "_").replace("δ", "delta").replace("(v−s)", "");
      const col = { "screen_j": "screen_j", "verify_j": "verify_j", "δ_": "delta_j", "screen_rank": "screen_rank", "verify_rank": "verify_rank" }[lbl.trim()];
      if (col && col === sortKey) th.setAttribute("aria-sort", sortDir === "asc" ? "ascending" : "descending");
      else if (col) th.setAttribute("aria-sort", "none");
    });
  });
  if (dirSel)  dirSel.addEventListener("change",  () => { sortDir  = dirSel.value;  rebuildTable(); pushUrl(); });
  if (showSel) showSel.addEventListener("change", () => { showMode = showSel.value; rebuildTable(); pushUrl(); });
  if (ghostChk) ghostChk.addEventListener("change", () => {
    _ps.ghost = ghostChk.checked;
    try { localStorage.setItem("vfy-ghost", _ps.ghost ? "1" : "0"); } catch (_) {}
    pushUrl();
  });

  // Auto-open selected design from URL
  if (selectedHash && rows.some(r => r.hash === selectedHash)) {
    const panelEl = root.querySelector("#vfy-panel");
    if (panelEl) _loadPanel(panelEl, runId, selectedHash);
  }
}
