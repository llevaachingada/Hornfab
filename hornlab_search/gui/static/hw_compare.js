// hw_compare.js — hornlab-search GUI   AGPL-3.0-or-later
//
// Horn + woofer · A/B compare and the 2×2 matrix (P4 —
// docs/research/system_woofer_2026-11-18/GUI_COMPLETION_HANDOFF_2026-11-19.md §5.8;
// GUI_SENIOR_REVIEW_2026-11-20.md §4 step 10):
//   #/hw/compare?a=<exp>/<case>&b=<exp>/<case>   two solved cases, per probe and per excitation
//   #/hw/compare?matrix=motor,box                 four README cases as a 2×2 grid with its edges
//
// GET /api/hw/compare and GET /api/hw/compare-matrix are the only compare data sources. Every
// number is the API's: JS formats, lays out and plots only. Channels are never summed. A refused
// pair is shown with its tokens and detail verbatim and no charts are drawn.
//
// The compare payload carries the ratio/phase series but (at this commit) no frequency array, so
// the x-axis is read from GET /api/hw/basis/<case A>?domain=<probe> — the same run and grid the
// compare used. When that call fails the maxima and band tables are still complete; only the
// curves are omitted, with the reason shown. A backend follow-up should add `frequencies_hz` to
// the compare payload.

import { chart, niceTicks, css, NS } from "./charts.js";
import { tip } from "./glossary.js";

const esc = s => (s == null ? "—" : String(s))
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

function brk(s) {
  return esc(s).replace(/([_\-./])/g, "$1<wbr>");
}

const fmtHz = v => v == null || !isFinite(v) ? "—"
  : v >= 1000 ? (v / 1000).toFixed(1) + " kHz" : Math.round(v) + " Hz";
/** A maxima frequency: the README values are Hz (1641), so keep Hz and one decimal under 1 kHz. */
const fmtHzAt = v => {
  if (v == null || !isFinite(v)) return "—";
  const n = Number(v);
  return Math.abs(n) >= 1000 ? Math.round(n) + " Hz" : n.toFixed(1).replace(/\.0$/, "") + " Hz";
};
const fmtDb = v => v == null || !isFinite(v) ? "—" : Number(v).toFixed(2) + " dB";
const fmtDeg = v => v == null || !isFinite(v) ? "—" : Number(v).toFixed(1) + "°";
const fmtPct = v => v == null || !isFinite(v) ? "—" : Number(v).toFixed(2) + " %";
const num = (v, d = 2) => (v == null || !isFinite(v)) ? "—" : Number(v).toFixed(d);

const encKey = key => String(key).split("/").map(encodeURIComponent).join("/");
const caseHref = key => "#/hw/case/" + encKey(key);
const compareHref = (a, b) => {
  const p = new URLSearchParams();
  if (a) p.set("a", a);
  if (b) p.set("b", b);
  return "#/hw/compare" + (p.toString() ? "?" + p.toString() : "");
};

const hashQuery = () => new URLSearchParams((location.hash.split("?")[1] || ""));
const readQuery = (q) => {
  if (typeof q !== "string" || !q) return hashQuery();
  return new URLSearchParams(q.replace(/^[#/]+/, "").replace(/^\?/, ""));
};

function skel(root, msg = "") {
  root.setAttribute("aria-busy", "true");
  root.innerHTML = `<div class="stack" style="gap:18px;opacity:0.6" aria-hidden="true">
    <div class="skeleton-block" style="height:2.2rem;width:min(260px,60%)"></div>
    <div class="skeleton-block" style="height:1rem;width:min(400px,80%)"></div>
    <div class="skeleton-block" style="height:180px"></div>
  </div>${msg ? `<p class="sr-only" role="status">${esc(msg)}…</p>` : ""}`;
}
const busyDone = root => root.removeAttribute("aria-busy");

const resultSkeleton = (msg = "Loading the comparison") =>
  `<div class="stack" style="gap:12px;opacity:0.65" aria-hidden="true">
    <div class="skeleton-block" style="height:1.2rem;width:min(320px,70%)"></div>
    <div class="skeleton-block" style="height:130px"></div>
    <div class="skeleton-block" style="height:240px"></div>
  </div><p class="sr-only" role="status">${esc(msg)}…</p>`;

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) {
    let msg = r.status + "";
    try { msg += " " + ((await r.json()).error || ""); } catch { /* not JSON */ }
    throw new Error(msg);
  }
  return r.json();
}

const errBanner = msg => `<div class="alert error" role="alert"><b>Error:</b> ${esc(msg)}</div>`;

function pageHead({ eyebrow, title, id, pills = "" }) {
  return `<div>
    <div class="eyebrow">${esc(eyebrow)}</div>
    <h2>${esc(title)}</h2>
    <p id="hwm-head-id" class="mono muted" style="font-size:0.78rem;overflow-wrap:anywhere">${brk(id || "")}</p>
    ${pills ? `<div class="pill-row" style="margin:8px 0 0">${pills}</div>` : ""}
  </div>`;
}

function modeSwitchHtml(matrix) {
  const b = (key, label, pressed) => `<button type="button" class="run-tab-link hwm-mode"
    data-mode="${key}" aria-pressed="${pressed}">${esc(label)}</button>`;
  return `<nav class="run-tabs new-run-modes" aria-label="Compare mode">
    ${b("ab", "A/B", !matrix)}
    ${b("matrix", "2×2 matrix", !!matrix)}
  </nav>`;
}

// The five README pairs. Keys are the recorded case directories, verbatim.
const PAIRS = [
  {
    id: "motor-seed", label: "Motor A/B · seed box",
    a: "bl_motor12pr/20261119T010548Z-motor12pr-17944-fa37ab5e",
    b: "bl_motor12pr_demo_twin/20261119T013209Z-ref_case-11372-452574f9",
  },
  {
    id: "motor-default", label: "Motor A/B · default box",
    a: "ev_wide_default_real/20261120T051740Z-wide_200_2500-46632-3de4e1d9",
    b: "ev_wide_default_demo/20261120T051840Z-wide_200_2500-36092-b530b722",
  },
  {
    id: "box-real", label: "Box A/B · real motor",
    a: "bl_motor12pr/20261119T010548Z-motor12pr-17944-fa37ab5e",
    b: "ev_wide_default_real/20261120T051740Z-wide_200_2500-46632-3de4e1d9",
  },
  {
    id: "box-demo", label: "Box A/B · demo motor",
    a: "bl_motor12pr_demo_twin/20261119T013209Z-ref_case-11372-452574f9",
    b: "ev_wide_default_demo/20261120T051840Z-wide_200_2500-36092-b530b722",
  },
  {
    id: "g6", label: "G6 · offset 30 vs wide",
    a: "bl_g6_offset30/20261118T235110Z-assembly-21668-c17f7cf6",
    b: "bl_smoke_wide/20261118T231115Z-g4wide-56836-b5d6490a",
  },
];

// A cycle over the four matrix cases: consecutive keys are the four README pairs.
// [real motor/seed, demo motor/seed, demo motor/default, real motor/default]
const MATRIX_KEYS = [PAIRS[0].a, PAIRS[0].b, PAIRS[3].b, PAIRS[1].a];

// Identity rows for "What changed"; paths match data_hw_compare._DIFF_PATHS.
const DIFF_ROWS = [
  { label: "Motor role", path: "motor.role", get: f => f && f.motor ? f.motor.role : null },
  { label: "Motor mapping", path: "motor.mapping_present",
    get: f => f && f.motor ? (f.motor.mapping_present ? "present" : "absent") : null },
  { label: "Motor driver", path: "motor.driver_id", get: f => f && f.motor ? f.motor.driver_id : null },
  { label: "Box width (mm)", path: "box.width_mm", get: f => f && f.box ? f.box.width_mm : null },
  { label: "Box height (mm)", path: "box.height_mm", get: f => f && f.box ? f.box.height_mm : null },
  { label: "Box depth (mm)", path: "box.depth_mm", get: f => f && f.box ? f.box.depth_mm : null },
  { label: "Horn offset (mm)", path: "horn_offset_mm", get: f => f ? f.horn_offset_mm : null },
  { label: "Horn scale", path: "scale", get: f => f ? f.scale : null },
  { label: "Source geometry hash", path: "source_geometry_hash", get: f => f ? f.source_geometry_hash : null },
  { label: "Project SHA-256", path: "project_sha256", get: f => f ? f.project_sha256 : null },
  { label: "Horn mesh", path: "mesh.horn_mesh_name", get: f => f && f.mesh ? f.mesh.horn_mesh_name : null },
  { label: "Mesh size (mm)", path: "mesh.mesh_size_mm", get: f => f && f.mesh ? f.mesh.mesh_size_mm : null },
  { label: "Detail size (mm)", path: "mesh.detail_size_mm", get: f => f && f.mesh ? f.mesh.detail_size_mm : null },
];

function factText(v) {
  if (v == null || v === "") return "—";
  if (Array.isArray(v)) return v.map(x => factText(x)).join(", ");
  return String(v);
}

// ── Scoped layout styles (this module only; app.css untouched) ──────────────

const STYLE_ID = "hw-compare-style";
const COMPARE_CSS = `
#hw-compare-view { min-width:0; }
#hw-compare-view [hidden] { display:none !important; }
#hw-compare-view .hint { font-size:0.8rem; color:var(--muted); line-height:1.45; }
#hw-compare-view .hwm-mode {
  background:none; border:0; border-bottom:2px solid transparent;
  font:inherit; color:var(--label); cursor:pointer; padding:8px 14px; text-align:left; }
#hw-compare-view .hwm-mode[aria-pressed="true"] {
  color:var(--ink); font-weight:600; border-bottom-color:var(--accent); }
#hw-compare-view .hwm-mode:focus-visible { outline:2px solid var(--accent); outline-offset:-2px; border-radius:4px; }
#hw-compare-view .form-grid > * { min-width:0; }
#hw-compare-view .form-grid select { min-width:0; max-width:100%; }
#hw-compare-view code { overflow-wrap:anywhere; }

.hwm-chip-row { display:flex; flex-wrap:wrap; gap:6px; min-width:0; }
.hwm-chip { min-width:0; max-width:100%; white-space:normal; text-align:left; }
.hwm-headline { display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin:6px 0; min-width:0; }
.hwm-headline .pill { font-size:0.72rem; white-space:normal; }

.hwm-series { display:grid; gap:10px; min-width:0; margin-top:10px; }
.hwm-series + .hwm-series { border-top:1px solid var(--rule); padding-top:12px; }
.hwm-series-head { display:flex; flex-wrap:wrap; gap:6px 10px; align-items:baseline; min-width:0; }
.hwm-series-head h4 { margin:0; font-size:0.92rem; font-weight:600; overflow-wrap:anywhere; }
.hwm-chart { min-width:0; }
.hwm-chart svg { max-width:100%; height:auto; }

.hwm-table { width:100%; border-collapse:collapse; font-size:0.79rem; min-width:620px; }
.hwm-table th, .hwm-table td {
  padding:4px 6px; border-bottom:1px solid var(--rule); text-align:left; vertical-align:top;
  overflow-wrap:anywhere; }
.hwm-table th { font-family:var(--f-mono); font-size:0.68rem; color:var(--label);
  text-transform:uppercase; letter-spacing:0.04em; background:var(--surface); position:sticky; top:0; z-index:1; }
.hwm-table td.n, .hwm-table th.n { text-align:right; font-variant-numeric:tabular-nums; }
.hwm-table .changed { color:var(--accent); font-weight:600; }

.hwm-matrix {
  display:grid; grid-template-columns:max-content minmax(0,1fr) minmax(7rem,auto) minmax(0,1fr);
  gap:8px; align-items:stretch; min-width:0; }
.hwm-rowhead, .hwm-colhead {
  font-family:var(--f-mono); font-size:0.72rem; color:var(--label);
  text-transform:uppercase; letter-spacing:0.04em; align-self:center; overflow-wrap:anywhere; }
.hwm-colhead { text-align:center; padding-bottom:2px; }
.hwm-colfill, .hwm-vfill { min-width:0; }
.hwm-cell {
  display:grid; gap:4px; min-width:0; border:1px solid var(--rule); border-radius:8px;
  padding:8px 10px; background:var(--surface); color:inherit; text-decoration:none; }
a.hwm-cell:hover { border-color:var(--accent); }
.hwm-cell.is-missing { border-style:dashed; opacity:0.75; }
.hwm-cell .hwm-cell-top { display:flex; flex-wrap:wrap; gap:4px 8px; align-items:center; min-width:0; }
.hwm-cell .mono { font-size:0.72rem; overflow-wrap:anywhere; }
.hwm-cell .muted { font-size:0.74rem; overflow-wrap:anywhere; }
.hwm-edge {
  display:grid; place-content:center; gap:2px; min-width:0; padding:6px 8px;
  border:1px dashed var(--rule); border-radius:8px; text-align:center;
  color:var(--label); text-decoration:none; overflow-wrap:anywhere; font-size:0.76rem; }
a.hwm-edge:hover { border-color:var(--accent); color:var(--accent); }
.hwm-edge .pill { font-size:0.66rem; white-space:normal; }
.hwm-edge.is-bad { border-color:var(--bad); }

@media (max-width:700px) {
  .hwm-matrix { grid-template-columns:minmax(0,1fr); }
  .hwm-colfill, .hwm-colhead, .hwm-vfill { display:none; }
  .hwm-rowhead { margin-top:8px; }
  .hwm-edge { text-align:left; place-content:start; }
}
`;

function ensureStyles() {
  if (typeof document === "undefined" || document.getElementById(STYLE_ID)) return;
  const s = document.createElement("style");
  s.id = STYLE_ID;
  s.textContent = COMPARE_CSS;
  document.head.appendChild(s);
}

// ── chart helpers (plot only; every value arrives from the API) ─────────────

function paddedRange(values, forceZero = false) {
  const nums = values.filter(v => v != null && isFinite(Number(v))).map(Number);
  if (!nums.length) return [-1, 1];
  let lo = Math.min(...nums), hi = Math.max(...nums);
  if (hi === lo) { hi = lo + 1; lo -= 1; }
  const pad = (hi - lo) * 0.1;
  lo -= pad; hi += pad;
  if (forceZero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
  return [lo, hi];
}

function drawChart(host, opts) {
  if (!host) return;
  host.innerHTML = "";
  const svg = document.createElementNS(NS, "svg");
  svg.style.width = "100%";
  host.appendChild(svg);
  chart(svg, opts);
}

function ratioChartOpts(freqs, values, label) {
  const pts = freqs.map((f, i) => [f, values[i] == null || !isFinite(values[i]) ? null : values[i]]);
  const [lo, hi] = paddedRange(values, true);
  return {
    H: 240, xlog: true,
    xlim: [freqs[0], freqs[freqs.length - 1]],
    ylim: [lo, hi], yticks: niceTicks(lo, hi, 5),
    xlabel: "Hz", ylabel: "ratio (dB)",
    series: [{ pts, color: css("--accent"), w: 2 }],
    hlines: [{ y: 0, color: css("--rule"), dash: true }],
    markers: pts.length <= 40,
    ariaLabel: `${label}: |B_a/B_b| magnitude ratio in dB per probe and excitation; not a channel sum.`,
  };
}

function phaseChartOpts(freqs, values, label) {
  const pts = freqs.map((f, i) => [f, values[i] == null || !isFinite(values[i]) ? null : values[i]]);
  return {
    H: 240, xlog: true,
    xlim: [freqs[0], freqs[freqs.length - 1]],
    ylim: [-180, 180], yticks: [-180, -90, 0, 90, 180],
    xlabel: "Hz", ylabel: "Δphase (deg)",
    series: [{ pts, color: css("--best"), w: 2 }],
    hlines: [{ y: 0, color: css("--rule"), dash: true }],
    markers: pts.length <= 40,
    ariaLabel: `${label}: wrapped phase of p_a × conj(p_b) in degrees per probe and excitation; not a channel sum.`,
  };
}

// ════════════════════════════════════════════════════════════════════════════
// Compare — #/hw/compare
// ════════════════════════════════════════════════════════════════════════════

export async function viewHwCompare(root, query = "") {
  skel(root, "Loading the solved-case list");
  let casesData = null;
  let casesError = null;
  try { casesData = await api("/api/hw/cases"); }
  catch (e) { casesError = e.message; }
  busyDone(root);

  const q = readQuery(query);
  const state = {
    a: String(q.get("a") || ""),
    b: String(q.get("b") || ""),
    matrix: !!q.get("matrix"),
  };
  const allCases = casesData && Array.isArray(casesData.cases) ? casesData.cases : [];
  const solved = allCases.filter(r => r && r.state === "solved");
  const solvedByKey = new Map(solved.map(r => [r.key, r]));

  function syncUrl() {
    const p = new URLSearchParams();
    if (state.a) p.set("a", state.a);
    if (state.b) p.set("b", state.b);
    if (state.matrix) p.set("matrix", "motor,box");
    history.replaceState(null, "", "#/hw/compare" + (p.toString() ? "?" + p.toString() : ""));
  }

  function setHeadId() {
    const el = root.querySelector("#hwm-head-id");
    if (!el) return;
    const text = state.matrix ? "matrix · motor × box"
      : (state.a || state.b ? `${state.a || "?"} ↔ ${state.b || "?"}` : "pick two solved cases");
    el.innerHTML = brk(text);
  }

  function caseLabel(r) {
    const ref = r.ref ? String(r.ref) + " — " : "";
    const band = r.solve && r.solve.fmin_hz != null && r.solve.fmax_hz != null
      ? ` · ${fmtHz(r.solve.fmin_hz)}–${fmtHz(r.solve.fmax_hz)}` : "";
    return `${ref}${r.key}${band}`;
  }

  function caseOptions(selected) {
    const rows = [`<option value="">— pick a solved case —</option>`];
    for (const r of solved) {
      rows.push(`<option value="${esc(r.key)}"${r.key === selected ? " selected" : ""}>${esc(caseLabel(r))}</option>`);
    }
    if (selected && !solvedByKey.has(selected)) {
      rows.push(`<option value="${esc(selected)}" selected>${esc(selected)} (not in the solved list)</option>`);
    }
    if (!solved.length && !selected) rows.push(`<option value="" disabled>— no solved cases loaded —</option>`);
    return rows.join("");
  }

  ensureStyles();
  const pills = [
    `<span class="pill">${casesError ? "case list unavailable" : `${solved.length} solved`}</span>`,
    `<span class="pill">${tip("per_input_ref", "per-input reference")} · never summed</span>`,
    `<span class="pill">1-D cuts / point probes only</span>`,
  ].join("");

  root.innerHTML = `<div id="hw-compare-view" class="stack" style="gap:18px">
    ${pageHead({
      eyebrow: "Horn + woofer · Compare",
      title: "Compare",
      id: state.matrix ? "matrix · motor × box"
        : (state.a || state.b ? `${state.a || "?"} ↔ ${state.b || "?"}` : "pick two solved cases"),
      pills,
    })}
    ${modeSwitchHtml(state.matrix)}
    <p class="lede" style="max-width:82ch;margin:0">Two solved cases, one probe and one excitation at a
      time. The woofer (Pa per 2.83 V) and the horn (Pa per 1 m/s) are separate references; they are
      never summed. No ${tip("calibration_policy", "calibration policy")} exists yet (risk R1).</p>
    ${casesError ? errBanner("Could not load the case list: " + casesError
      + " — the quick pairs below still compare through the server.") : ""}

    <section class="card stack" style="gap:10px">
      <div class="fig-head"><h3 style="margin:0;font-size:1rem">Quick pairs</h3>
        <span class="muted">four README matrix pairs + G6</span></div>
      <div class="hwm-chip-row" role="group" aria-label="Quick compare pairs">
        ${PAIRS.map(p => `<a class="btn btn-sm hwm-chip" href="${compareHref(p.a, p.b)}"
          data-a="${esc(p.a)}" data-b="${esc(p.b)}"
          title="${esc(p.a)} vs ${esc(p.b)}">${esc(p.label)}</a>`).join("")}
      </div>
      <p class="hint" role="status">Each chip opens the pair A/B; the pickers below list solved cases only.</p>
    </section>

    <div id="hwm-pickers-card" class="card stack" style="gap:12px"${state.matrix ? " hidden" : ""}>
      <div class="fig-head"><h3 style="margin:0;font-size:1rem">Choose two solved cases</h3>
        <span class="muted">${casesError ? "case list unavailable" : `${solved.length} solved`}</span></div>
      <div class="form-grid">
        <label for="hwm-a">Case A</label>
        <div>
          <select id="hwm-a">${caseOptions(state.a)}</select>
          <div class="hint" role="status" id="hwm-a-hint"></div>
        </div>
        <label for="hwm-b">Case B</label>
        <div>
          <select id="hwm-b">${caseOptions(state.b)}</select>
          <div class="hint" role="status" id="hwm-b-hint"></div>
        </div>
        <span class="form-label">Swap</span>
        <div class="btn-row">
          <button type="button" class="btn btn-sm" id="hwm-swap">⇄ Swap A and B</button>
          <span class="hint" role="status" id="hwm-pick-hint"></span>
        </div>
      </div>
    </div>

    <div id="hwm-results"></div>
  </div>`;

  const results = root.querySelector("#hwm-results");
  const pickers = root.querySelector("#hwm-pickers-card");
  const selA = root.querySelector("#hwm-a");
  const selB = root.querySelector("#hwm-b");

  function updatePickInputs() {
    if (selA) selA.innerHTML = caseOptions(state.a);
    if (selB) selB.innerHTML = caseOptions(state.b);
  }

  function updatePickHint() {
    const a = solvedByKey.get(state.a);
    const b = solvedByKey.get(state.b);
    const ah = root.querySelector("#hwm-a-hint");
    const bh = root.querySelector("#hwm-b-hint");
    const ph = root.querySelector("#hwm-pick-hint");
    const one = (key, row, side) => {
      if (!key) return `Pick case ${side}.`;
      if (row) {
        const band = row.solve && row.solve.fmin_hz != null
          ? `${fmtHz(row.solve.fmin_hz)}–${fmtHz(row.solve.fmax_hz)}` : "band not recorded";
        return `Solved · ${band}.`;
      }
      return casesError ? `<span class="warn-text">Case list unavailable; the server decides.</span>`
        : `<span class="warn-text">Not in the solved list.</span>`;
    };
    if (ah) ah.innerHTML = one(state.a, a, "A");
    if (bh) bh.innerHTML = one(state.b, b, "B");
    if (ph) {
      if (!state.a || !state.b) ph.innerHTML = `<span class="warn-text">Pick both sides, or a quick pair.</span>`;
      else if (a && b) ph.innerHTML = `<span class="good-text">✓ Ready to compare.</span>`;
      else ph.innerHTML = `<span class="warn-text">Compare needs two solved runs.</span>`;
    }
  }

  function updateModeUi() {
    root.querySelectorAll(".hwm-mode").forEach(btn => {
      const m = btn.dataset.mode === "matrix";
      btn.setAttribute("aria-pressed", String(m === state.matrix));
    });
    if (pickers) pickers.hidden = state.matrix;
    setHeadId();
  }

  // ── mode switch ───────────────────────────────────────────────────────────
  root.querySelectorAll(".hwm-mode").forEach(btn => btn.addEventListener("click", () => {
    const m = btn.dataset.mode === "matrix";
    if (m === state.matrix) return;
    state.matrix = m;
    syncUrl();
    updateModeUi();
    if (m) loadMatrix();
    else loadCompare();
  }));

  // ── quick pairs and matrix edges share this: open one A/B pair in place ──
  function wirePairLink(a) {
    if (!a) return;
    a.addEventListener("click", e => {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
      e.preventDefault();
      state.a = String(a.dataset.a || "");
      state.b = String(a.dataset.b || "");
      state.matrix = false;
      syncUrl();
      updateModeUi();
      updatePickInputs();
      updatePickHint();
      loadCompare();
    });
  }
  root.querySelectorAll(".hwm-chip").forEach(wirePairLink);

  // ── pickers ───────────────────────────────────────────────────────────────
  if (selA) selA.addEventListener("change", () => {
    state.a = String(selA.value || "");
    syncUrl(); updatePickInputs(); updatePickHint(); loadCompare();
  });
  if (selB) selB.addEventListener("change", () => {
    state.b = String(selB.value || "");
    syncUrl(); updatePickInputs(); updatePickHint(); loadCompare();
  });
  const swap = root.querySelector("#hwm-swap");
  if (swap) swap.addEventListener("click", () => {
    const t = state.a; state.a = state.b; state.b = t;
    syncUrl(); updatePickInputs(); updatePickHint(); loadCompare();
  });

  // ── compare load / render ─────────────────────────────────────────────────
  let loadSeq = 0;
  let seriesSpecs = [];

  async function loadCompare() {
    const seq = ++loadSeq;
    if (!state.a || !state.b) {
      const missing = !state.a ? "A" : "B";
      results.innerHTML = `<div class="alert info" role="status">Pick case ${missing} above, or use a quick
        pair. The compare is per probe and per excitation; it never sums the channels.</div>`;
      return;
    }
    const aKnown = solvedByKey.get(state.a);
    const bKnown = solvedByKey.get(state.b);
    if (solved.length && (!aKnown || !bKnown)) {
      const missing = [!aKnown ? "A" : null, !bKnown ? "B" : null].filter(Boolean).join(" and ");
      results.innerHTML = `<div class="alert warn" role="status">Case ${missing} is not in the solved list.
        Compare needs a solved run; pick another case.</div>`;
      return;
    }
    results.innerHTML = resultSkeleton("Loading the A/B comparison");
    let r;
    try {
      r = await api(`/api/hw/compare?a=${encodeURIComponent(state.a)}&b=${encodeURIComponent(state.b)}`);
    } catch (e) {
      if (seq === loadSeq && results.isConnected) results.innerHTML = errBanner(e.message);
      return;
    }
    if (seq !== loadSeq || !results.isConnected) return;
    if (!r || r.ok !== true) {
      if (r && r.ok === false) renderRefusal(r);
      else results.innerHTML = errBanner("The compare endpoint returned no verdict.");
      return;
    }
    renderCompare(r, seq);
  }

  function refusalHtml(r) {
    const mm = Array.isArray(r.mismatches) ? r.mismatches : [];
    return `<div class="alert error" role="alert">
      <b>These two runs cannot be compared at the input level.</b>
      <p class="hint" style="margin:6px 0 0;color:inherit">The tokens and detail are shown verbatim.
        No numbers are coerced, nothing is summed, and no charts are drawn.</p>
      ${mm.length ? `<ul style="margin:8px 0 0;padding-left:20px">${mm.map(m =>
        `<li><code>${esc(m.token)}</code> — <span style="overflow-wrap:anywhere">${esc(m.detail)}</span></li>`).join("")}</ul>`
        : `<p class="hint" style="margin:8px 0 0">The server returned no mismatch token.</p>`}
    </div>`;
  }

  function whatChangedHtml(w) {
    if (!w || !w.a || !w.b) return "";
    const differs = new Set(Array.isArray(w.differs) ? w.differs : []);
    const rows = DIFF_ROWS.map(row => {
      const av = factText(row.get(w.a));
      const bv = factText(row.get(w.b));
      const changed = differs.has(row.path);
      return `<tr><th scope="row">${esc(row.label)}</th><td>${esc(av)}</td><td>${esc(bv)}</td>
        <td>${changed ? `<span class="changed">changed</span>` : `<span class="muted">same</span>`}</td></tr>`;
    }).join("");
    return `<section class="card">
      <div class="fig-head"><h3>What changed</h3>
        <span class="muted">${differs.size} declared identity field${differs.size === 1 ? "" : "s"} differ</span></div>
      <div class="tbl-wrap" style="margin-top:8px"><table class="hwm-table">
        <thead><tr><th>Field</th><th>Case A</th><th>Case B</th><th></th></tr></thead>
        <tbody>${rows}</tbody></table></div>
      <p class="hint" style="margin:8px 0 0">Rows are the declared identity facts returned in
        <code>what_differs</code>; “changed” marks a path in <code>what_differs.differs</code>. A
        “same” here is limited to this list, not a claim that the runs are identical.</p>
    </section>`;
  }

  function renderRefusal(r) {
    results.innerHTML = `<div class="stack" style="gap:14px">
      ${refusalHtml(r)}
      ${whatChangedHtml(r.what_differs)}
    </div>`;
  }

  function bandTableHtml(bands) {
    if (!Array.isArray(bands) || !bands.length) return "";
    const rows = bands.map(b => `<tr>
      <td>${esc(b.band)}</td>
      <td class="n">${esc(b.n_freqs)}</td>
      <td class="n">${fmtDb(b.max_abs_ratio_db)}</td>
      <td class="n">${fmtHzAt(b.max_abs_ratio_at_hz)}</td>
      <td class="n">${fmtDeg(b.max_abs_delta_phase_deg)}</td>
      <td class="n">${fmtPct(b.max_relative_delta_percent)}</td>
      <td class="n">${fmtHzAt(b.max_relative_delta_at_hz)}</td>
    </tr>`).join("");
    return `<div class="tbl-wrap" style="margin-top:8px"><table class="hwm-table">
      <thead><tr><th>Band</th><th class="n">n</th><th class="n">Max |ratio| (dB)</th>
        <th class="n">at (Hz)</th><th class="n">Max Δphase (°)</th>
        <th class="n">Max relative delta (%)</th><th class="n">at (Hz)</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
  }

  function seriesHtml(probe, ex, pi, ei) {
    const perInput = ex.per_input == null ? "—" : ex.per_input;
    const points = Array.isArray(ex.points) && ex.points.length ? ex.points : null;
    const entries = points
      ? points.map(pt => ({ label: `${ex.id || "excitation"} · point ${Number(pt.point_index) + 1}`, data: pt }))
      : [{ label: ex.id || "excitation", data: ex }];
    return entries.map((entry, ki) => {
      const base = `hwm-c${pi}-${ei}-${ki}`;
      const ratioHost = base + "-r";
      const phaseHost = base + "-p";
      seriesSpecs.push({
        ratioHost, phaseHost,
        ratio: entry.data.ratio_db,
        phase: entry.data.delta_phase_deg,
        label: `${probe.probe_id || probe.domain || "probe"} · ${entry.label}`,
      });
      return `<div class="hwm-series">
        <div class="hwm-series-head">
          <h4>${esc(entry.label)}</h4>
          <span class="pill">per-input ${esc(perInput)}</span>
          <span class="pill">B excitation ${esc(ex.b_id || "—")}</span>
        </div>
        <div class="hwm-headline">
          <span class="pill">max |ratio| ${fmtDb(entry.data.max_abs_ratio_db)} @ ${fmtHzAt(entry.data.max_abs_ratio_at_hz)}</span>
          <span class="pill">max Δphase ${fmtDeg(entry.data.max_abs_delta_phase_deg)}</span>
          <span class="pill">max relative delta ${fmtPct(entry.data.max_relative_delta_percent)} @ ${fmtHzAt(entry.data.max_relative_delta_at_hz)}</span>
        </div>
        <div class="grid2">
          <div class="fig">
            <div class="fig-head"><h3>|B_a/B_b| (dB)</h3><span class="muted">per probe · per excitation</span></div>
            <div class="hwm-chart" data-chart-host="${ratioHost}">
              <div class="skeleton-block" style="height:150px"></div>
              <p class="sr-only" role="status">Loading the frequency axis…</p>
            </div>
            <p class="cap">20 log10(|p_a|/|p_b|) from the API; no channel sum.</p>
          </div>
          <div class="fig">
            <div class="fig-head"><h3>Δphase (wrapped, deg)</h3><span class="muted">per probe · per excitation</span></div>
            <div class="hwm-chart" data-chart-host="${phaseHost}">
              <div class="skeleton-block" style="height:150px"></div>
              <p class="sr-only" role="status">Loading the frequency axis…</p>
            </div>
            <p class="cap">angle(p_a × conj(p_b)) from the API; no channel sum.</p>
          </div>
        </div>
        ${bandTableHtml(entry.data.bands)}
      </div>`;
    }).join("");
  }

  function onAxisSummaryHtml(r) {
    const probes = Array.isArray(r.probes) ? r.probes : [];
    const p = probes.find(x => /on_axis/i.test(String((x && x.probe_id) || ""))) || null;
    if (!p) return "";
    const rows = [];
    for (const ex of (Array.isArray(p.excitations) ? p.excitations : [])) {
      const entries = Array.isArray(ex.points) && ex.points.length
        ? ex.points.map(pt => ({ label: `${ex.id || "excitation"} · point ${Number(pt.point_index) + 1}`, data: pt }))
        : [{ label: ex.id || "excitation", data: ex }];
      for (const e of entries) {
        rows.push(`<tr>
          <td>${esc(e.label)}</td>
          <td class="n">${fmtDb(e.data.max_abs_ratio_db)}</td>
          <td class="n">${fmtHzAt(e.data.max_abs_ratio_at_hz)}</td>
          <td class="n">${fmtDeg(e.data.max_abs_delta_phase_deg)}</td>
          <td class="n">${fmtPct(e.data.max_relative_delta_percent)}</td>
          <td class="n">${fmtHzAt(e.data.max_relative_delta_at_hz)}</td>
          <td>${esc(e.data.per_input || ex.per_input || "—")}</td>
        </tr>`);
      }
    }
    if (!rows.length) return "";
    return `<section class="card">
      <div class="fig-head"><h3>On-axis whole-grid maxima</h3>
        <span class="muted">${esc(p.probe_id || "on axis")} · the README pair values are these API fields</span></div>
      <div class="tbl-wrap" style="margin-top:8px"><table class="hwm-table">
        <thead><tr><th>Series</th><th class="n">max |ratio| (dB)</th><th class="n">at (Hz)</th>
          <th class="n">max Δphase (°)</th><th class="n">max relative delta (%)</th>
          <th class="n">at (Hz)</th><th>per-input</th></tr></thead>
        <tbody>${rows.join("")}</tbody></table></div>
      <p class="hint" style="margin:8px 0 0">These are the payload's whole-grid
        <code>max_abs_ratio_db</code> / <code>max_abs_ratio_at_hz</code> fields. The on-axis probe is
        listed first on this page; no JS maximum is taken.</p>
    </section>`;
  }

  function probesHtml(r) {
    const probes = Array.isArray(r.probes) ? r.probes : [];
    const ordered = [...probes].sort((x, y) => {
      const xo = /on_axis/i.test(String((x && x.probe_id) || ""));
      const yo = /on_axis/i.test(String((y && y.probe_id) || ""));
      return xo === yo ? 0 : xo ? -1 : 1;
    });
    return ordered.map((p, pi) => {
      const excs = Array.isArray(p.excitations) ? p.excitations : [];
      const dist = p.distance_m == null ? "distance not recorded" : num(p.distance_m, 2) + " m";
      return `<section class="card stack" style="gap:10px">
        <div class="fig-head"><h3 style="margin:0;font-size:1rem">Probe ${esc(p.probe_id || p.domain || "?")}</h3>
          <span class="muted">${esc(p.kind || "point_probe")} · ${esc(dist)} ·
            ${esc(p.n_points == null ? "?" : p.n_points)} point${Number(p.n_points) === 1 ? "" : "s"}</span></div>
        <p class="hint" role="status">Domain <code>${esc(p.domain || "—")}</code>. Each excitation is its
          own series; the ratio and wrapped phase are the API's values.</p>
        ${excs.length ? excs.map((ex, ei) => seriesHtml(p, ex, pi, ei)).join("")
          : `<div class="alert warn" role="status">No excitation series for this probe.</div>`}
      </section>`;
    }).join("");
  }

  async function loadFreqGrid(r) {
    const probes = Array.isArray(r.probes) ? r.probes : [];
    for (const p of probes) {
      if (!p || !p.domain) continue;
      try {
        const b = await api(`/api/hw/basis/${encKey(r.a)}?domain=${encodeURIComponent(p.domain)}`);
        if (b && Array.isArray(b.frequencies_hz) && b.frequencies_hz.length >= 2) return b.frequencies_hz;
      } catch { /* try the next probe domain */ }
    }
    return null;
  }

  function drawAllCharts(freqs) {
    for (const s of seriesSpecs) {
      const rh = results.querySelector(`[data-chart-host="${s.ratioHost}"]`);
      const ph = results.querySelector(`[data-chart-host="${s.phaseHost}"]`);
      if (rh) {
        if (Array.isArray(s.ratio) && s.ratio.length === freqs.length) {
          drawChart(rh, ratioChartOpts(freqs, s.ratio, s.label));
        } else {
          rh.innerHTML = `<p class="hint" role="status">The ratio series length does not match the frequency grid.</p>`;
        }
      }
      if (ph) {
        if (Array.isArray(s.phase) && s.phase.length === freqs.length) {
          drawChart(ph, phaseChartOpts(freqs, s.phase, s.label));
        } else {
          ph.innerHTML = `<p class="hint" role="status">The phase series length does not match the frequency grid.</p>`;
        }
      }
    }
  }

  async function renderCompare(r, seq) {
    seriesSpecs = [];
    results.innerHTML = `<div class="stack" style="gap:16px">
      ${onAxisSummaryHtml(r)}
      ${whatChangedHtml(r.what_differs)}
      ${r.caption ? `<div class="alert info" role="note">${esc(r.caption)}</div>` : ""}
      ${r.band_note ? `<p class="hint" role="status">${esc(r.band_note)}</p>` : ""}
      <p class="hint" role="status" id="hwm-axis-note">Loading the frequency axis…</p>
      <div id="hwm-probes" class="stack" style="gap:16px"></div>
    </div>`;
    const probesHost = results.querySelector("#hwm-probes");
    if (!probesHost) return;
    probesHost.innerHTML = probesHtml(r);
    const freqs = await loadFreqGrid(r);
    if (seq !== loadSeq || !results.isConnected) return;
    const note = results.querySelector("#hwm-axis-note");
    if (!Array.isArray(freqs) || !freqs.length) {
      if (note) note.innerHTML = `<div class="alert warn" role="alert">The compare payload carries the
        ratio/phase series but no frequency array, and /api/hw/basis could not supply one. The maxima
        and band tables above are complete; the curves are omitted. A backend follow-up should add
        <code>frequencies_hz</code> to <code>/api/hw/compare</code>.</div>`;
      results.querySelectorAll("[data-chart-host]").forEach(h => {
        h.innerHTML = `<p class="hint" role="status">No frequency axis; see the note above.</p>`;
      });
      return;
    }
    if (note) note.innerHTML = `Frequency axis: the same ${freqs.length}-point grid as the A run,
      read from <code>/api/hw/basis/${esc(encKey(r.a))}</code>.`;
    drawAllCharts(freqs);
  }

  // ── 2×2 matrix load / render ──────────────────────────────────────────────
  async function loadMatrix() {
    const seq = ++loadSeq;
    results.innerHTML = resultSkeleton("Loading the 2×2 matrix");
    const p = new URLSearchParams();
    p.set("keys", MATRIX_KEYS.join(","));
    let r;
    try {
      r = await api("/api/hw/compare-matrix?" + p);
    } catch (e) {
      if (seq === loadSeq && results.isConnected) results.innerHTML = errBanner(e.message);
      return;
    }
    if (seq !== loadSeq || !results.isConnected) return;
    renderMatrix(r);
    fillClosingEdge(r, seq);
  }

  /** hw_compare_matrix compares consecutive keys only (3 edges for 4 keys). The 2×2 grid
   *  also has a closing edge; fetch that one pair from /api/hw/compare rather than leaving a
   *  hole or inventing a verdict. */
  async function fillClosingEdge(r, seq) {
    const host = results.querySelector("#hwm-edge-box-real");
    if (!host) return;
    const edges = Array.isArray(r.edges) ? r.edges : [];
    if (edges[3]) {
      host.innerHTML = matrixEdgeHtml(edges[3], "Box A/B · real motor");
      host.querySelectorAll(".hwm-edge[data-a]").forEach(wirePairLink);
      return;
    }
    const a = MATRIX_KEYS[3];
    const b = MATRIX_KEYS[0];
    try {
      const cmp = await api(`/api/hw/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`);
      if (seq !== loadSeq || !results.isConnected) return;
      const edge = {
        from: a, to: b, ok: cmp && cmp.ok === true,
        mismatches: cmp && Array.isArray(cmp.mismatches) ? cmp.mismatches.map(m => m.token) : [],
        error: cmp ? null : "no verdict",
      };
      host.innerHTML = matrixEdgeHtml(edge, "Box A/B · real motor");
      host.querySelectorAll(".hwm-edge[data-a]").forEach(wirePairLink);
    } catch (e) {
      if (seq !== loadSeq || !results.isConnected) return;
      host.innerHTML = `<div class="hwm-edge is-bad"><b>Box A/B · real motor</b>
        <span class="pill bad">${esc(e.message)}</span></div>`;
    }
  }

  function matrixCellHtml(cell) {
    const st = String(cell.state || "missing");
    const cls = st === "solved" ? "good" : st === "staged" ? "warn" : "bad";
    const box = cell.box
      ? `${num(cell.box.width_mm, 0)}×${num(cell.box.height_mm, 0)}×${num(cell.box.depth_mm, 0)} mm`
      : "box not recorded";
    const dz = Array.isArray(cell.horn_offset_mm) && cell.horn_offset_mm.length >= 3
      ? ` · dz ${num(cell.horn_offset_mm[2], 1)} mm` : "";
    const inner = `<div class="hwm-cell-top"><b>${esc(cell.ref || "(no ref)")}</b>
        <span class="pill ${cls}">${esc(st)}</span></div>
      <span class="mono">${brk(cell.key)}</span>
      <span class="muted">motor ${esc(cell.motor || "UNDECLARED")} · ${esc(box)}${esc(dz)}</span>`;
    return st === "missing"
      ? `<div class="hwm-cell is-missing">${inner}</div>`
      : `<a class="hwm-cell" href="${caseHref(cell.key)}" title="Open ${esc(cell.key)}">${inner}</a>`;
  }

  function matrixEdgeHtml(edge, label) {
    if (!edge) {
      return `<div class="hwm-edge"><b>${esc(label)}</b><span class="pill bad">no edge</span></div>`;
    }
    const bad = edge.ok === false;
    const detail = bad
      ? (Array.isArray(edge.mismatches) && edge.mismatches.length
        ? edge.mismatches.join(", ") : (edge.error || "refused"))
      : "comparable";
    return `<a class="hwm-edge${bad ? " is-bad" : ""}"
      href="${compareHref(edge.from, edge.to)}"
      data-a="${esc(edge.from)}" data-b="${esc(edge.to)}"
      title="Open the A/B compare for this edge">
      <b>${esc(label)}</b><span class="pill ${bad ? "bad" : "good"}">${esc(detail)}</span></a>`;
  }

  function renderMatrix(r) {
    const cells = Array.isArray(r.cells) ? r.cells : [];
    const edges = Array.isArray(r.edges) ? r.edges : [];
    const cell = i => cells[i] || { key: MATRIX_KEYS[i], state: "missing", motor: "UNDECLARED" };
    const edge = i => edges[i] || null;
    results.innerHTML = `<div class="stack" style="gap:14px">
      <section class="card stack" style="gap:10px">
        <div class="fig-head"><h3 style="margin:0;font-size:1rem">2×2 matrix · motor × box</h3>
          <span class="muted">four README cases · pairwise edges</span></div>
        <p class="hint" role="status">Rows are the declared ${tip("demo_motor", "motor")} provenance;
          columns are the enclosure. Each edge opens the A/B compare in the API's from→to order; a
          missing cell is shown, never inferred.</p>
        <div class="hwm-matrix">
          <div class="hwm-colfill"></div><div class="hwm-colhead">Seed box</div>
          <div class="hwm-colfill"></div><div class="hwm-colhead">Default box</div>

          <div class="hwm-rowhead">Real motor</div>
          ${matrixCellHtml(cell(0))}
          <div id="hwm-edge-box-real">
            <div class="hwm-edge"><b>Box A/B · real motor</b><span class="pill">loading…</span></div>
          </div>
          ${matrixCellHtml(cell(3))}

          <div class="hwm-vfill"></div>
          ${matrixEdgeHtml(edge(0), "Motor A/B · seed box")}
          <div class="hwm-vfill"></div>
          ${matrixEdgeHtml(edge(2), "Motor A/B · default box")}

          <div class="hwm-rowhead">Demo motor</div>
          ${matrixCellHtml(cell(1))}
          ${matrixEdgeHtml(edge(1), "Box A/B · demo motor")}
          ${matrixCellHtml(cell(2))}
        </div>
      </section>
      <p class="hint" role="status">Cells come from the case ledger; each edge's verdict comes from
        <code>/api/hw/compare</code>. The matrix endpoint returns its consecutive edges; when it
        omits the closing box edge, this page fills that one from the same compare endpoint. No
        delta is recomputed in JS.</p>
    </div>`;
    results.querySelectorAll(".hwm-edge[data-a]").forEach(wirePairLink);
  }

  // ── initial state ─────────────────────────────────────────────────────────
  updateModeUi();
  updatePickInputs();
  updatePickHint();
  syncUrl();
  if (state.matrix) loadMatrix();
  else if (state.a && state.b) loadCompare();
  else {
    results.innerHTML = `<div class="alert info" role="status">Pick two solved cases above, or use a
      quick pair. The compare is per probe and per excitation; it never sums the channels.</div>`;
  }
}
