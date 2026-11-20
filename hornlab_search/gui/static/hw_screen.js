// hw_screen.js — hornlab-search GUI   AGPL-3.0-or-later
//
// Horn + woofer · the fixed-horn CPU **screen** (P2 —
// docs/research/system_woofer_2026-11-18/GUI_COMPLETION_HANDOFF_2026-11-19.md §4, §5.3, §5.4, §8):
//   #/hw/screens              one row per recorded woofer_seed.json, replays grouped by study id
//   #/hw/screen/<study_id>    shortlist, trade-off scatter, rejection ledger, panel-fit pre-check
//
// Read-only against /api/hw/screens, /api/hw/screen/<id> and POST /api/hw/panel-fit. Every number
// is the API's; JS only formats (Hz / mm / L / cm² / dB / dB² / m²) and draws. A screen narrows the
// field and never names a single winner, and the woofer/horn channels are never summed here.
//
// House rules kept in this file: eyebrow + h2 + mono id + provenance pill-row (no <h1>); the run
// toolbar for tabs; glossary tips on technical labels; skeletons while loading; view state in the
// URL (?tab=, ?row=, ?x=, ?y=, ?cols=); a screen-estimate fidelity label is never invented —
// SCREEN_MAGNITUDE is rendered because the study *is* a screen, with its title pointing at the
// recorded claim. The shortlist table shows seven reading columns by default under grouped headers
// (Box | Low end | Crossover | Match | Build); every remaining field lives in the Columns chooser.

import { chart, niceTicks, css, el, NS, wireScrollHints } from "./charts.js";
import { tip } from "./glossary.js";

// ── Helpers copied from hw.js / app.js / verify.js (local there, not exported) ──

const esc = s => (s == null ? "–" : String(s))
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

/** Same as app.js: break long ids at _ - . / instead of widening the page. */
function brk(s) {
  return esc(s).replace(/([_\-./])/g, "$1<wbr>");
}

const fmtHz = v => v == null || !isFinite(v) ? "–" : v >= 1000 ? (v / 1000).toFixed(1) + " kHz" : Math.round(v) + " Hz";
const num = (v, d = 0) => (v == null || !isFinite(v)) ? "–" : Number(v).toFixed(d);

/** Skeleton while loading (same markup as verify.js's skel(), rooted on the view element). */
function skel(root, msg = "") {
  root.setAttribute("aria-busy", "true");
  root.innerHTML = `<div class="stack" style="gap:18px;opacity:0.6" aria-hidden="true">
    <div class="skeleton-block" style="height:2.2rem;width:min(260px,60%)"></div>
    <div class="skeleton-block" style="height:1rem;width:min(400px,80%)"></div>
    <div class="skeleton-block" style="height:180px"></div>
  </div>${msg ? `<p class="sr-only" role="status">${esc(msg)}…</p>` : ""}`;
}
const busyDone = root => root.removeAttribute("aria-busy");

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) {
    let msg = r.status + "";
    try { msg += " " + ((await r.json()).error || ""); } catch { /* not JSON */ }
    throw new Error(msg);
  }
  return r.json();
}

async function apiPost(path, body) {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let msg = r.status + "";
    try { msg += " " + ((await r.json()).error || ""); } catch { /* not JSON */ }
    throw new Error(msg);
  }
  return r.json();
}

const errBanner = msg => `<div class="alert error" role="alert"><b>Error:</b> ${esc(msg)}</div>`;

/** House header (§4): eyebrow, h2, mono id, provenance pills. */
function pageHead({ eyebrow, title, id, pills = "" }) {
  return `<div>
    <div class="eyebrow">${esc(eyebrow)}</div>
    <h2>${esc(title)}</h2>
    ${id ? `<p class="mono muted" style="font-size:0.78rem;overflow-wrap:anywhere">${brk(id)}</p>` : ""}
    ${pills ? `<div class="pill-row" style="margin:8px 0 0">${pills}</div>` : ""}
  </div>`;
}

const kpi = (label, value, sub = "", cls = "") =>
  `<div class="kpi"><span>${label}</span><b class="${cls}">${esc(value)}</b>${sub
    ? `<small class="muted" style="font-size:0.72rem">${sub}</small>` : ""}</div>`;

function kvTable(pairs) {
  // Fixed layout + anywhere-wrapping: long tokens and file lists must never widen the page.
  return `<div class="tbl-wrap"><table style="table-layout:fixed"><tbody>${pairs.filter(([, v]) => v !== undefined).map(([k, v]) =>
    `<tr><th scope="row" style="width:38%;white-space:normal">${esc(k)}</th><td style="white-space:normal;overflow-wrap:anywhere">${v}</td></tr>`).join("")}</tbody></table></div>`;
}

// ── Formatting that is not acoustics ────────────────────────────────────────

/** mtime from the API is an ISO instant; the page labels it "file mtime" everywhere. */
function fmtWhen(iso) {
  if (!iso) return "–";
  const t = new Date(iso);
  if (isNaN(t.getTime())) return String(iso);
  return t.toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

const isNum = v => typeof v === "number" && isFinite(v);
const numOrNull = v => (v == null || v === "" || !isFinite(Number(v)) ? null : Number(v));
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/** Query string after the hash (used when the router does not hand one in). */
const hashQuery = () => new URLSearchParams((location.hash.split("?")[1] || ""));
const readQuery = (q) => {
  if (typeof q !== "string" || !q) return hashQuery();
  return new URLSearchParams(q.replace(/^[#/]+/, "").replace(/^\?/, ""));
};

/** The eight numeric axes, with the study's own direction (from axis_directions) on top. */
const AXIS_META = {
  match_error_h_db2: { label: "Match error H", unit: "dB²" },
  match_error_v_db2: { label: "Match error V", unit: "dB²" },
  lf_f3_hz: { label: "F3", unit: "Hz" },
  port_velocity_ratio: { label: "Port velocity", unit: "× limit" },
  excursion_margin_db: { label: "Excursion margin", unit: "dB" },
  cabinet_footprint_m2: { label: "Cabinet footprint", unit: "m²" },
  mounting_distance_mm: { label: "Mounting distance", unit: "mm" },
};
const DEFAULT_X = "match_error_h_db2";
const DEFAULT_Y = "lf_f3_hz";
const AXIS_SHORT = {
  match_error_h_db2: "Match H", match_error_v_db2: "Match V", lf_f3_hz: "F3",
  port_velocity_ratio: "Port vel", excursion_margin_db: "Excursion",
  cabinet_footprint_m2: "Footprint", mounting_distance_mm: "Mount",
};
const axisShort = k => AXIS_SHORT[k] || (AXIS_META[k] && AXIS_META[k].label) || String(k);

const dirArrow = (key, dirs) => dirs && dirs[key] === "+" ? "↑" : dirs && dirs[key] === "-" ? "↓" : "";
const dirWord = (key, dirs) => dirs && dirs[key] === "+" ? "higher is better" : dirs && dirs[key] === "-" ? "lower is better" : "";
const axisLabel = (key, dirs) => {
  const m = AXIS_META[key];
  if (!m) return String(key);
  const arrow = dirArrow(key, dirs);
  return `${m.label} (${m.unit})${arrow ? " " + arrow : ""}`;
};
const axisOptionLabel = axisLabel;

// ── Shortlist columns (senior review 2026-11-20 §4 step 8, F9) ──────────────
// Seven reading columns by default; every other recorded shortlist field lives in the
// "Columns" chooser and the choice is carried in the URL (?cols=a,b,c).
const DEFAULT_COLS = ["driver", "box", "lowend", "xo", "match", "feasible", "pick"];
const COL_ORDER = ["driver", "why", "box", "net", "foot", "lowend", "f3", "port",
  "exc", "pv", "xo", "match", "matchh", "matchv", "feasible", "gates", "pick"];

function parseCols(raw) {
  const want = new Set(String(raw == null ? "" : raw).split(",").map(s => s.trim()).filter(Boolean));
  const picked = COL_ORDER.filter(k => want.has(k));
  return picked.length ? picked : DEFAULT_COLS.slice();
}
const colsParam = list => list.join(",");

/** Plain-axis number formatting; unit stays in the header/axis label. */
function fmtAxis(v, key) {
  if (v == null || !isFinite(v)) return "–";
  const n = Number(v);
  if (key === "match_error_h_db2" || key === "match_error_v_db2") {
    return Math.abs(n) >= 1 ? n.toFixed(2) : n.toFixed(3);
  }
  if (key === "lf_f3_hz" || key === "mounting_distance_mm") return String(Math.round(n));
  if (key === "cabinet_footprint_m2") return n.toFixed(3);
  return n.toFixed(2);
}

const FEAS_LABEL = {
  port_fits: "port fits",
  wall: "walls",
  driver_clearance: "driver clearance",
  f3_gate: "F3 gate",
  bl_panel_fit: "BL panel fit",
  placement_legal: "placement legal",
  xo_data: "XO data",
};

// Row identity helpers shared by the table, the cards and the trade-off tab.
const modelOf = id => {
  const s = String(id || "");
  return (s.includes("_") ? s.slice(s.lastIndexOf("_") + 1) : s).toUpperCase();
};
const shortIdOf = r => String(r.candidate_id == null ? "" : r.candidate_id).slice(0, 8);
const dzMmOf = r => r.placement && r.placement.dz_mm != null ? num(r.placement.dz_mm, 0) : "–";
const xoBandOf = r => (Array.isArray(r.xo_band_hz) && r.xo_band_hz.length >= 2)
  ? [Math.min(...r.xo_band_hz), Math.max(...r.xo_band_hz)] : null;

/** Every feasibility key as a text chip (colour is never the only signal). */
function feasChips(f) {
  if (!f || typeof f !== "object") return `<span class="muted">–</span>`;
  const keys = Object.keys(f);
  if (!keys.length) return `<span class="muted">–</span>`;
  return keys.map(k => {
    const ok = !!f[k];
    return `<span class="pill ${ok ? "good" : "bad"}" title="${esc(k)}: ${ok ? "pass" : "fail"}">${ok ? "✓" : "✗"} ${esc(FEAS_LABEL[k] || k)}</span>`;
  }).join(" ");
}

/** Row reasons are either a string or a list of strings; both are rendered verbatim. */
function rowReasons(row) {
  if (Array.isArray(row.reasons)) return row.reasons.map(String);
  if (row.reason != null && row.reason !== "") return [String(row.reason)];
  return [];
}
const reasonPrefix = r => String(r).split(/[\s:]/)[0] || "(empty)";
const cel = v => Array.isArray(v) ? `[${v.map(String).join(", ")}]`
  : (v && typeof v === "object" ? JSON.stringify(v) : String(v));

// ── Scoped layout styles (this module only; app.css untouched) ─────────────
// Compact data tables, sticky headers, a real radio column, and the <700 px card
// reflow cannot be expressed with per-element inline styles. Every selector is
// scoped to ids/classes this file owns.
const SCREEN_STYLE_ID = "hw-screen-style";
const SCREEN_CSS = `
#hw-shortlist-card .fig-head { align-items:flex-start; }
#hw-shortlist-title { display:flex; flex-wrap:wrap; align-items:baseline; gap:4px 10px; min-width:0; }
#hw-shortlist { font-size:0.82rem; }
#hw-shortlist th, #hw-shortlist td { padding:5px 8px; vertical-align:middle; }
#hw-shortlist thead th { background:var(--surface); font-size:0.74rem; white-space:nowrap; }
#hw-shortlist thead tr.hw-groups th.hw-group {
  font-size:0.66rem; text-transform:uppercase; letter-spacing:0.07em; color:var(--label);
  font-weight:600; text-align:left; padding:6px 8px 2px; border-bottom:1px solid var(--rule); }
#hw-shortlist thead tr.hw-groups th:not(.hw-group) { padding-bottom:3px; }
#hw-shortlist thead tr.hw-head th { padding-top:2px; }
#hw-shortlist .hw-num, #hw-shortlist th.hw-num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
#hw-shortlist .hw-wrap { white-space:normal; overflow-wrap:break-word; }
#hw-shortlist .hw-box { white-space:nowrap; font-variant-numeric:tabular-nums; }
#hw-shortlist .hw-gate { white-space:normal; }
#hw-shortlist .hw-gate .pill { white-space:normal; }
#hw-shortlist .hw-pick, #hw-shortlist th.hw-pick { width:1%; text-align:center; }
#hw-shortlist th[data-col="driver"] { min-width:8.5rem; }
#hw-shortlist th[data-col="why"] { min-width:8rem; }
#hw-shortlist th[data-col="box"] { min-width:10.5rem; }
#hw-shortlist th[data-col="lowend"] { min-width:7.5rem; }
#hw-shortlist input[type="radio"], .hw-card input[type="radio"] {
  width:15px; height:15px; margin:0; accent-color:var(--accent); }
#hw-shortlist tbody tr[aria-selected="true"] {
  background:color-mix(in srgb, var(--accent) 10%, var(--surface)); }
#hw-shortlist tbody tr:focus-visible { outline:2px solid var(--accent); outline-offset:-2px; }

/* Column chooser: a native <details> popover that never widens the page. */
#hw-shortlist-card .hw-cols { position:relative; }
#hw-shortlist-card .hw-cols > summary {
  cursor:pointer; list-style:none; display:inline-flex; align-items:center; gap:6px;
  min-height:28px; padding:4px 10px; border:1px solid var(--control-border); border-radius:6px;
  background:var(--surface); color:var(--ink); font-size:0.8rem; }
#hw-shortlist-card .hw-cols > summary::-webkit-details-marker { display:none; }
#hw-shortlist-card .hw-cols > summary::after { content:"▾"; font-size:0.7em; color:var(--muted); }
#hw-shortlist-card .hw-cols[open] > summary { border-color:var(--accent); color:var(--accent); }
#hw-shortlist-card .hw-cols[open] > summary::after { content:"▴"; }
#hw-shortlist-card .hw-cols-panel {
  position:absolute; right:0; top:calc(100% + 6px); z-index:30; width:min(440px, calc(100vw - 40px));
  box-sizing:border-box; background:var(--surface); border:1px solid var(--rule); border-radius:8px;
  padding:12px 14px; box-shadow:0 12px 28px rgba(0,0,0,0.22); text-align:left; }
#hw-shortlist-card .hw-cols-hint { margin:0 0 8px; font-size:0.76rem; color:var(--muted); }
#hw-shortlist-card .hw-cols-grid {
  border:0; margin:0; padding:0; display:grid;
  grid-template-columns:repeat(auto-fit, minmax(10.5rem, 1fr)); gap:4px 16px; }
#hw-shortlist-card .hw-cols-grid label {
  display:flex; align-items:flex-start; gap:6px; font-size:0.8rem;
  text-transform:none; letter-spacing:0; color:var(--ink); font-weight:400; }
#hw-shortlist-card .hw-cols-grid input { margin-top:2px; }

#hw-screens { font-size:0.8rem; }
#hw-screens th, #hw-screens td { padding:5px 7px; vertical-align:middle; }
#hw-screens thead th { position:sticky; top:0; z-index:2; background:var(--surface); font-size:0.74rem; }
#hw-screens tbody tr { height:56px; }
#hw-screens .hw-num, #hw-screens th.hw-num { text-align:right; font-variant-numeric:tabular-nums; }
#hw-screens td.hw-wrap { white-space:normal; overflow-wrap:break-word; }
#hw-screens .hw-open, .hw-card .hw-open {
  color:var(--accent); font-weight:600; font-family:var(--f-mono);
  text-decoration:underline; text-underline-offset:2px; }
#hw-screens .hw-open:hover { color:var(--ink); }

#hw-screens-scroll .tbl-scroll-hint,
#hw-shortlist-scroll .tbl-scroll-hint { font-size:0.8rem; color:var(--label); }

/* At desktop width the screens list fits; let the page be the scroll container so the
   sticky header really sticks. The shortlist keeps its own .tbl-wrap scroll at every
   width, because a custom column set must never widen the page. */
@media (min-width:1280px) {
  #hw-screens-scroll .tbl-wrap { overflow:visible; }
}
/* Below the desktop table width the tables scroll inside .tbl-wrap with a visible cue. */
@media (max-width:1279px) {
  #hw-screens { min-width:720px; }
}

.hw-cards { display:none; }
@media (max-width:700px) {
  .hw-table-view { display:none !important; }
  .hw-cards { display:grid; gap:10px; }
  /* The card layout carries every field, so the table's column chooser would be a dead control. */
  #hw-shortlist-card .hw-cols { display:none; }
}
.hw-card {
  border:1px solid var(--rule); border-radius:8px; background:var(--surface);
  padding:10px 12px; min-width:0; }
.hw-card[aria-selected="true"] {
  border-color:var(--accent);
  background:color-mix(in srgb, var(--accent) 8%, var(--surface)); }
.hw-card:focus-visible { outline:2px solid var(--accent); outline-offset:-2px; }
.hw-card-head { display:flex; gap:8px; align-items:flex-start; }
.hw-card-head > div { min-width:0; }
.hw-card-grid {
  display:grid; grid-template-columns:minmax(0,9.5rem) minmax(0,1fr);
  gap:2px 10px; margin:8px 0 0; font-size:0.8rem; }
.hw-card-grid dt {
  margin:0; color:var(--label); font-family:var(--f-mono); font-size:0.68rem;
  text-transform:uppercase; letter-spacing:0.04em; }
.hw-card-grid dd { margin:0; min-width:0; overflow-wrap:anywhere; }
.hw-card-gates { display:flex; flex-wrap:wrap; gap:4px; margin-top:8px; }
.hw-card-gates .pill { white-space:normal; }
`;

function ensureScreenStyles() {
  if (typeof document === "undefined" || document.getElementById(SCREEN_STYLE_ID)) return;
  const s = document.createElement("style");
  s.id = SCREEN_STYLE_ID;
  s.textContent = SCREEN_CSS;
  document.head.appendChild(s);
}

// ════════════════════════════════════════════════════════════════════════════
// Screens list — #/hw/screens
// ════════════════════════════════════════════════════════════════════════════

export async function viewHwScreens(root, query = "") {
  void query;
  skel(root, "Loading screens");
  let data;
  try { data = await api("/api/hw/screens"); }
  catch (e) { busyDone(root); root.innerHTML = errBanner(e.message); return; }
  busyDone(root);

  const studies = Array.isArray(data.studies) ? data.studies : [];
  const errors = Array.isArray(data.errors) ? data.errors : [];
  const files = studies.reduce((n, s) => n + (Number(s.replay_count) || 1), 0);
  const schemas = [...new Set(studies.map(s => s.schema).filter(Boolean))];

  const pills = [
    `<span class="pill">${esc(studies.length)} stud${studies.length === 1 ? "y" : "ies"}</span>`,
    `<span class="pill">${esc(files)} study file${files === 1 ? "" : "s"} on disk</span>`,
    ...schemas.map(s => `<span class="pill mono">${esc(s)}</span>`),
    errors.length ? `<span class="pill bad">${esc(errors.length)} unreadable file${errors.length === 1 ? "" : "s"}</span>` : "",
  ].filter(Boolean).join("");

  const cnt = (study, key) => {
    const miss = new Set(study.counts_missing || []);
    const c = study.counts || {};
    return (miss.has(key) || c[key] == null) ? "—" : String(c[key]);
  };

  let rows = "";
  let cards = "";
  if (studies.length) {
    const parts = studies.map(s => {
      const horn = s.horn || {};
      const drivers = Array.isArray(s.drivers) ? s.drivers : [];
      const names = drivers.map(d => d.driver_name || d.driver_id).filter(Boolean);
      const hash = horn.design_hash ? String(horn.design_hash) : "";
      const hash8 = hash ? hash.slice(0, 8) : "–";
      const replay = Number(s.replay_count) || 1;
      const replayChip = replay > 1
        ? (s.byte_identical
          ? `<span class="pill good">byte-identical replay ×${esc(replay)}</span>`
          : `<span class="pill warn">replays differ — investigate</span>`)
        : "";
      const href = "#/hw/screen/" + encodeURIComponent(s.study_id);
      const when = fmtWhen(s.mtime_utc);
      const count = s.driver_count ?? names.length;
      const driverSummary = names.length
        ? `${count} driver${count === 1 ? "" : "s"} · ${names[0]}${names.length > 1 ? ` +${names.length - 1}` : ""}`
        : "–";
      const driverTitle = names.length ? names.join(", ") : "";
      const claimChip = `<span class="pill" title="${esc(s.claim || "")}">heuristic · no winner</span>`;
      const openLink = `<a class="hw-open" href="${href}" title="Open study ${esc(s.study_id)}">${esc(s.study_id)} →</a>`;
      const hornHtml = `<b>${esc(horn.brief_id || "–")}</b><br><span class="mono" title="${esc(hash)}">${esc(hash8)}</span>${horn.quality ? ` <span class="pill">${esc(horn.quality)}</span>` : ""}`;
      const row = `<tr class="clickable" data-id="${esc(s.study_id)}" tabindex="0">
        <td class="hw-wrap">${openLink}<br><small class="muted">${esc(s.dir || "")}</small></td>
        <td><span class="num">${esc(when)}</span><br><small class="muted">file mtime</small></td>
        <td class="hw-wrap">${hornHtml}</td>
        <td class="hw-wrap" title="${esc(driverTitle)}">${esc(driverSummary)}</td>
        <td class="hw-num">${esc(cnt(s, "shortlist_rows"))}</td>
        <td class="hw-num">${esc(cnt(s, "bl_panel_fit_rejected"))}</td>
        <td class="hw-wrap">${claimChip}${replayChip ? ` ${replayChip}` : ""}</td>
      </tr>`;
      const card = `<article class="hw-card">
        ${openLink}
        <div class="mono muted" style="font-size:0.7rem;overflow-wrap:anywhere">${esc(s.dir || "")}</div>
        <dl class="hw-card-grid">
          <dt>When</dt><dd>${esc(when)} · file mtime</dd>
          <dt>Horn</dt><dd>${esc(horn.brief_id || "–")} · <span class="mono">${esc(hash8)}</span>${horn.quality ? ` · ${esc(horn.quality)}` : ""}</dd>
          <dt>Drivers</dt><dd>${names.length ? names.map(n => esc(n)).join(", ") : "–"}</dd>
          <dt>Shortlist</dt><dd>${esc(cnt(s, "shortlist_rows"))}</dd>
          <dt>Panel-fit rejected</dt><dd>${esc(cnt(s, "bl_panel_fit_rejected"))}</dd>
          <dt>Claim</dt><dd>${claimChip}${replayChip ? `<br>${replayChip}` : ""}</dd>
        </dl>
      </article>`;
      return { row, card };
    });
    rows = parts.map(p => p.row).join("");
    cards = parts.map(p => p.card).join("");
  }

  ensureScreenStyles();
  root.innerHTML = `<div class="stack" style="gap:18px">
    ${pageHead({
      eyebrow: "Horn + woofer · Screens · CPU screen studies",
      title: "Screens",
      id: data.store,
      pills,
    })}
    <p class="lede" style="max-width:76ch">Step 4 (Screen) of the system story: the fast CPU screen
      narrows a horn + driver set to a shortlist and never names a single winner; the numbers are
      estimates, not results.</p>
    ${errors.map(e => `<div class="alert warn" role="alert"><b>Unreadable study file:</b>
      <code style="overflow-wrap:anywhere">${esc(e.path)}</code> — ${esc(e.error)}</div>`).join("")}
    ${studies.length ? `<div class="tbl-scroll hw-table-view" id="hw-screens-scroll">
      <div class="tbl-scroll-hint" aria-hidden="true">scroll for all columns →</div>
      <div class="tbl-wrap"><table id="hw-screens">
        <thead><tr><th>Study</th><th>When</th><th>Horn</th><th>Drivers</th>
          <th class="hw-num">Shortlist</th><th class="hw-num">Panel-fit rejected</th><th>Claim</th></tr></thead>
        <tbody>${rows}</tbody></table></div>
    </div>
    <div class="hw-cards">${cards}</div>` : `<div class="alert info" role="status">No screens yet. A screen is step 4 of the system
      story: pick a horn, drivers and box limits, then run the CPU screen.</div>
      <div class="btn-row"><a class="btn primary" href="#/hw/new">Start a new system →</a></div>`}
  </div>`;

  root.querySelectorAll("tr[data-id]").forEach(tr => {
    const go = () => { location.hash = "#/hw/screen/" + encodeURIComponent(tr.dataset.id); };
    tr.addEventListener("click", e => { if (!e.target.closest("a")) go(); });
    tr.addEventListener("keydown", e => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); }
    });
  });
  wireScrollHints(root);
}

// ════════════════════════════════════════════════════════════════════════════
// Screen detail — #/hw/screen/<study_id>
// ════════════════════════════════════════════════════════════════════════════

export async function viewHwScreen(root, studyId, query = "") {
  const sid = String(studyId == null ? "" : studyId).trim();
  skel(root, `Loading screen ${sid}`);
  let d;
  try { d = await api("/api/hw/screen/" + encodeURIComponent(sid)); }
  catch (e) {
    busyDone(root);
    root.innerHTML = `<p><a href="#/hw/screens">← All screens</a></p>` + errBanner(e.message);
    return;
  }
  busyDone(root);

  const route = "#/hw/screen/" + encodeURIComponent(String(d.study_id || sid));
  const TABS = [["shortlist", "Shortlist"], ["tradeoffs", "Trade-offs"], ["rejected", "Rejected"], ["panel", "Panel fit"]];
  const tabKeys = new Set(TABS.map(([k]) => k));
  const q = readQuery(query);

  const kept = Array.isArray(d.kept_rows) ? d.kept_rows : [];
  const shortlist = Array.isArray(d.shortlist) ? d.shortlist : [];
  const byId = new Map();
  for (const r of kept) if (r && r.candidate_id != null) byId.set(String(r.candidate_id), r);
  for (const r of shortlist) if (r && r.candidate_id != null) byId.set(String(r.candidate_id), r);

  let tab = tabKeys.has(q.get("tab")) ? q.get("tab") : "shortlist";
  const wantedRow = q.get("row");
  let selected = wantedRow && byId.has(String(wantedRow)) ? String(wantedRow) : null;

  const axisDirs = (d.axis_directions && typeof d.axis_directions === "object") ? d.axis_directions : {};
  const numericAxes = (Array.isArray(d.numeric_axes) && d.numeric_axes.length)
    ? d.numeric_axes.filter(k => k in AXIS_META)
    : Object.keys(axisDirs).filter(k => k in AXIS_META);
  const validAxis = k => (k && numericAxes.includes(k) ? k : null);
  let xKey = validAxis(q.get("x")) || validAxis(DEFAULT_X) || numericAxes[0] || null;
  let yKey = validAxis(q.get("y")) || validAxis(DEFAULT_Y) || numericAxes[1] || numericAxes[0] || null;
  // Which shortlist columns are shown (?cols=). Default = the seven reading columns.
  let colSel = parseCols(q.get("cols"));

  const counts = d.counts || {};
  const missing = new Set(d.counts_missing || []);
  const cnt = key => (missing.has(key) || counts[key] == null) ? "—" : String(counts[key]);

  const asset = d.asset || {};
  const blFit = (d.metric_spec && d.metric_spec.bl_panel_fit) || null;
  const demoD = blFit && isNum(Number(blFit.driver_moving_diameter_m))
    ? Number(blFit.driver_moving_diameter_m) : 0.2;                  // BL's documented demo default
  const roundoverMm = blFit && isNum(Number(blFit.port_roundover_m)) ? Number(blFit.port_roundover_m) * 1000 : null;

  const nDrivers = (counts.drivers_loaded != null && Number.isFinite(Number(counts.drivers_loaded)))
    ? Number(counts.drivers_loaded)
    : (Array.isArray(d.catalog) ? d.catalog.length : "–");
  const title = `Shortlist for ${asset.brief_id || "–"} × ${nDrivers} driver${nDrivers === 1 ? "" : "s"}`;
  const fidelityTitle = d.claim || `study schema ${d.schema || "?"} carries no fidelity label; this study is a screen`;
  const panelApplied = blFit && blFit.applied
    ? `Boundary Lab panel-fit gate applied by the screen (metric_spec.bl_panel_fit): driver Ø ${num(Number(blFit.driver_moving_diameter_m) * 1000)} mm, clearance ${num(Number(blFit.clearance_m) * 1000, 1)} mm. The Panel fit tab recomputes it.`
    : "Boundary Lab panel-fit gate applied by the screen (metric_spec.bl_panel_fit). The Panel fit tab recomputes it.";

  // ── URL state ────────────────────────────────────────────────────────────
  function tabHref(t) {
    const p = new URLSearchParams();
    if (t !== "shortlist") p.set("tab", t);
    if (selected) p.set("row", selected);
    if (xKey && xKey !== DEFAULT_X) p.set("x", xKey);
    if (yKey && yKey !== DEFAULT_Y) p.set("y", yKey);
    if (colsParam(colSel) !== colsParam(DEFAULT_COLS)) p.set("cols", colsParam(colSel));
    const qs = p.toString().replace(/%2C/g, ",");       // keep ?cols=a,b,c readable
    return route + (qs ? "?" + qs : "");
  }
  function updateTabHrefs() {
    root.querySelectorAll("nav.run-tabs a[data-tab]").forEach(a => {
      a.setAttribute("href", tabHref(a.dataset.tab));
    });
  }
  function syncUrl() {
    history.replaceState(null, "", tabHref(tab));    // selection / axes never spam history
    updateTabHrefs();
  }

  // ── Header, claim, KPIs, toolbar ─────────────────────────────────────────
  const pills = [
    `<span class="pill" title="${esc(fidelityTitle)}">SCREEN_MAGNITUDE</span>`,
    `<span class="pill">no phase/delay claims</span>`,
    `<span class="pill" title="${esc(panelApplied)}">panel-fit applied (demo transducer dims)</span>`,
  ].join("");

  const panelRejected = cnt("bl_panel_fit_rejected");

  ensureScreenStyles();
  root.innerHTML = `<div class="stack" style="gap:18px">
    <div>
      <div class="eyebrow">Horn + woofer · Screen · study
        <span class="mono" style="text-transform:none;letter-spacing:0.04em">${esc(d.study_id || sid)}</span></div>
      <h2>${esc(title)}</h2>
      <p class="mono muted" style="font-size:0.78rem;overflow-wrap:anywhere">${brk(d.dir || "")}</p>
      <div class="pill-row" style="margin:8px 0 0">${pills}</div>
    </div>
    ${d.claim ? `<div class="alert warn" role="note">${esc(d.claim)}</div>` : ""}
    <div class="kpis">
      ${kpi("Drivers", cnt("drivers_loaded"))}
      ${kpi("Boxes considered", cnt("boxes_considered"))}
      ${kpi("Kept", cnt("candidates_kept"))}
      ${kpi("Pareto front", cnt("pareto_front_rows"))}
      ${kpi("Shortlist", cnt("shortlist_rows"))}
      ${kpi("Panel-fit rejected", panelRejected, "", panelRejected !== "—" && Number(panelRejected) ? "warn" : "")}
    </div>
    <div class="run-toolbar">
      <nav class="run-tabs" aria-label="Views of this screen">
        ${TABS.map(([k, l]) => `<a class="run-tab-link" data-tab="${k}" href="${tabHref(k)}"${k === tab ? ' aria-current="page"' : ""}>${esc(l)}</a>`).join("")}
      </nav>
      <div class="run-actions">
        <button class="btn btn-sm" type="button" disabled aria-disabled="true"
          title="Boundary Lab actions arrive in a later phase">Check in Boundary Lab…</button>
        <span class="hint" role="status" style="font-size:0.78rem">Boundary Lab actions arrive in a later phase</span>
      </div>
    </div>
    <div id="hw-screen-body"></div>
  </div>`;

  const body = root.querySelector("#hw-screen-body");
  if (!body) return;

  // ── Shortlist tab ────────────────────────────────────────────────────────
  let sort = null;                                   // {key, dir} · dir 1 = ascending

  function shortlistStatus() {
    const row = selected ? byId.get(selected) : null;
    if (row) {
      const onShort = shortlist.some(r => String(r.candidate_id) === String(row.candidate_id));
      return `Picked ${row.driver_name || row.driver_id || "row"} (${selected})`
        + `${onShort ? "" : " — a kept row from the trade-off scatter, not on this shortlist"}. `
        + "The Panel fit tab uses this row.";
    }
    return "No row picked. Pick one with the radio (or Enter on a row); the Panel fit tab then uses it.";
  }

  /** The seven reading columns, plus every remaining recorded field behind the chooser. */
  function columnDefs() {
    const whyCell = r => {
      const raw = r.shortlist_reason == null ? "" : String(r.shortlist_reason);
      if (!raw) return `<td class="hw-wrap"><span class="muted">–</span></td>`;
      const idx = raw.indexOf(":");
      const head = idx < 0 ? raw : raw.slice(0, idx);
      const tail = idx < 0 ? "" : raw.slice(idx + 1);
      const sub = head === "driver_best" ? modelOf(tail)
        : head === "axis_best" ? axisShort(tail)
        : head === "pareto_fill" ? "Pareto front"
        : tail;
      return `<td class="hw-wrap"><code title="${esc(raw)}">${esc(head)}</code>${sub
        ? `<br><small class="muted">${esc(sub)}</small>` : ""}</td>`;
    };

    const gatesCell = r => {
      const f = r.feasibility;
      if (!f || typeof f !== "object" || !Object.keys(f).length) {
        return `<td class="hw-gate"><span class="muted">–</span></td>`;
      }
      const keys = Object.keys(f);
      const fails = keys.filter(k => !f[k]);
      const title = keys.map(k => `${FEAS_LABEL[k] || k}: ${f[k] ? "pass" : "fail"}`).join(" · ");
      return fails.length
        ? `<td class="hw-gate"><span class="pill bad" title="${esc(title)}">${fails.length} failing</span></td>`
        : `<td class="hw-gate"><span class="pill good" title="${esc(title)}">all pass</span></td>`;
    };

    const numTd = (v, d = 0) =>
      `<td class="hw-num" title="${v == null ? "" : esc(String(v))}">${num(v, d)}</td>`;
    const fmtTd = (v, key) =>
      `<td class="hw-num" title="${v == null ? "" : esc(String(v))}">${fmtAxis(v, key)}</td>`;

    const boxCell = r => {
      const b = r.box || {};
      const dims = `${num(b.external_width_mm)} × ${num(b.external_height_mm)} × ${num(b.external_depth_mm)}`;
      const title = `${dims} mm · net ${num(b.net_volume_l, 1)} L · wall ${num(b.wall_mm)} mm`;
      return `<td class="hw-box" title="${esc(title)}"><span class="num">${dims} mm</span><br>
        <span class="muted">${num(b.net_volume_l, 1)} L net</span></td>`;
    };
    const lowendCell = r => {
      const b = r.box || {};
      const title = `Tuning ${num(b.derived_tuning_hz, 1)} Hz · F3 ${num(b.f3_hz, 1)} Hz`;
      return `<td class="hw-num" title="${esc(title)}"><span class="num">${num(b.derived_tuning_hz, 1)}</span> / ${num(b.f3_hz, 1)}</td>`;
    };
    const xoCell = r => {
      const band = xoBandOf(r);
      const text = `${num(r.xo_hz, 0)}${band ? ` (${num(band[0], 0)}–${num(band[1], 0)})` : ""}`;
      const title = `${r.xo_hz == null ? "–" : String(r.xo_hz)} Hz${band ? ` · overlap band ${String(band[0])}–${String(band[1])} Hz` : ""}`;
      return `<td class="hw-num" title="${esc(title)}">${text}</td>`;
    };
    const matchCell = r => {
      const na = r.numeric_axes || {};
      const title = `Match error H ${fmtAxis(na.match_error_h_db2, "match_error_h_db2")} dB² · `
        + `V ${fmtAxis(na.match_error_v_db2, "match_error_v_db2")} dB²`;
      return `<td class="hw-num" title="${esc(title)}">${fmtAxis(na.match_error_h_db2, "match_error_h_db2")} / ${fmtAxis(na.match_error_v_db2, "match_error_v_db2")}</td>`;
    };

    return [
      { key: "driver", group: null, name: "Driver", sort: "driver", title: "Woofer driver",
        head: () => "Driver",
        cell: r => `<td class="hw-wrap"><b title="${esc(r.driver_name || r.driver_id || "")}">${esc(modelOf(r.driver_id) || r.driver_name || "–")}</b><br>
          <span class="mono muted" style="font-size:0.68rem">dz ${esc(dzMmOf(r))} mm · ${esc(shortIdOf(r))}</span></td>` },
      { key: "why", group: "Screen", name: "Why shortlisted", sort: "why", title: "Why the screen kept this row",
        head: () => "Why shortlisted", cell: whyCell },
      { key: "box", group: "Box", name: "Box (W×H×D, L)", sort: "box",
        title: "External width × height × depth (mm) and net volume (L)",
        head: () => "Box (W×H×D, L)", cell: boxCell },
      { key: "net", group: "Box", name: "Net volume (L)", sort: "net", title: "Net internal volume (L)",
        head: () => "Net volume (L)",
        cell: r => numTd(r.box && r.box.net_volume_l, 1) },
      { key: "foot", group: "Box", name: "Cabinet footprint (m²)", sort: "foot",
        title: "Cabinet footprint (m²)", head: () => "Cabinet footprint (m²)",
        cell: r => numTd(r.numeric_axes && r.numeric_axes.cabinet_footprint_m2, 3) },
      { key: "lowend", group: "Low end", name: "Tuning / F3 (Hz)", sort: "tuning",
        title: "Ported-box tuning and the box model's F3 (Hz)",
        head: () => `${tip("fb_tuning", "Tuning")} / ${tip("f3", "F3")} (Hz)`, cell: lowendCell },
      { key: "f3", group: "Low end", name: "F3 (Hz)", sort: "f3", axisKey: "lf_f3_hz",
        title: "F3 (Hz)", head: () => `${tip("f3", "F3")} (Hz)`,
        cell: r => numTd(r.box && r.box.f3_hz, 1) },
      { key: "port", group: "Low end", name: "Port area (cm²)", sort: "port",
        title: "Port throat area (cm²)", head: () => "Port area (cm²)",
        cell: r => numTd(r.box && r.box.port_throat_area_cm2, 0) },
      { key: "exc", group: "Low end", name: "Excursion margin (dB)", sort: "exc",
        axisKey: "excursion_margin_db", title: "Excursion margin (dB)",
        head: () => `${tip("excursion_margin", "Excursion margin")} (dB)`,
        cell: r => numTd(r.numeric_axes && r.numeric_axes.excursion_margin_db, 1) },
      { key: "pv", group: "Low end", name: "Port velocity (× limit)", sort: "pv",
        axisKey: "port_velocity_ratio", title: "Port velocity as a ratio of the limit",
        head: () => `${tip("port_velocity", "Port velocity")} (× limit)`,
        cell: r => numTd(r.numeric_axes && r.numeric_axes.port_velocity_ratio, 2) },
      { key: "xo", group: "Crossover", name: "Crossover (Hz)", sort: "xo",
        title: "Crossover frequency and overlap band (Hz)",
        head: () => `${tip("xo_band", "Crossover")} (Hz)`, cell: xoCell },
      { key: "match", group: "Match", name: "Match error H / V (dB²)", sort: "mr_h",
        axisKey: "match_error_h_db2", title: "Shape match error H and V (dB²)",
        head: () => `${tip("e_shape", "Match H / V")} (dB²)`, cell: matchCell },
      { key: "matchh", group: "Match", name: "Match error H (dB²)", sort: "mr_h",
        axisKey: "match_error_h_db2", title: "Shape match error H (dB²)",
        head: () => `${tip("e_shape", "Match error H")} (dB²)`,
        cell: r => fmtTd(r.numeric_axes && r.numeric_axes.match_error_h_db2, "match_error_h_db2") },
      { key: "matchv", group: "Match", name: "Match error V (dB²)", sort: "mr_v",
        axisKey: "match_error_v_db2", title: "Shape match error V (dB²)",
        head: () => `${tip("e_shape", "Match error V")} (dB²)`,
        cell: r => fmtTd(r.numeric_axes && r.numeric_axes.match_error_v_db2, "match_error_v_db2") },
      { key: "feasible", group: "Build", name: "Feasible", sort: "feasible",
        title: "Every recorded feasibility gate", head: () => "Feasible", cell: gatesCell },
      { key: "gates", group: "Build", name: "Feasibility gates (words)", sort: "feasible",
        title: "Every recorded feasibility gate, written out", head: () => "Feasibility gates",
        cell: r => `<td class="hw-gate">${feasChips(r.feasibility)}</td>` },
      { key: "pick", group: null, name: "Pick", sort: null, title: "Pick the row the Panel fit tab uses",
        head: () => "Pick",
        cell: r => {
          const cid = String(r.candidate_id);
          const on = selected === cid;
          return `<td class="hw-pick"><input type="radio" name="hw-pick-table" value="${esc(cid)}" data-cid="${esc(cid)}"${on ? " checked" : ""}
            aria-label="Select ${esc(r.driver_name || r.driver_id || "row")} ${esc(cid)}"></td>`;
        } },
    ];
  }

  function renderShortlist() {
    if (!shortlist.length) {
      body.innerHTML = `<section class="card"><h3>Shortlist</h3>
        <div class="alert info" role="status">This study recorded no shortlist rows (counts: shortlist
          ${esc(cnt("shortlist_rows"))}, Pareto ${esc(cnt("pareto_front_rows"))}). Nothing is named a winner
          on an empty shortlist.</div></section>`;
      return;
    }

    const defs = columnDefs();
    const visible = () => defs.filter(d => colSel.includes(d.key));
    const NUMERIC = new Set(["net", "foot", "lowend", "f3", "port", "exc", "pv", "xo",
      "match", "matchh", "matchv"]);
    const thClass = d => d.key === "pick" ? "hw-pick" : NUMERIC.has(d.key) ? "hw-num" : "";

    const SORTERS = {
      driver: r => String(r.driver_name || r.driver_id || ""),
      why: r => String(r.shortlist_reason || ""),
      box: r => numOrNull(r.box && r.box.net_volume_l),
      net: r => numOrNull(r.box && r.box.net_volume_l),
      tuning: r => numOrNull(r.box && r.box.derived_tuning_hz),
      port: r => numOrNull(r.box && r.box.port_throat_area_cm2),
      f3: r => numOrNull(r.box && r.box.f3_hz),
      xo: r => numOrNull(r.xo_hz),
      mr_h: r => numOrNull(r.numeric_axes && r.numeric_axes.match_error_h_db2),
      mr_v: r => numOrNull(r.numeric_axes && r.numeric_axes.match_error_v_db2),
      exc: r => numOrNull(r.numeric_axes && r.numeric_axes.excursion_margin_db),
      pv: r => numOrNull(r.numeric_axes && r.numeric_axes.port_velocity_ratio),
      foot: r => numOrNull(r.numeric_axes && r.numeric_axes.cabinet_footprint_m2),
      feasible: r => Object.keys(r.feasibility || {}).filter(k => !r.feasibility[k]).length,
    };
    const compare = (a, b) => {
      const an = isNum(a), bn = isNum(b);
      if (an && bn) return a - b;
      return String(a == null ? "" : a).localeCompare(String(b == null ? "" : b), "en");
    };

    const cardHtml = r => {
      const b = r.box || {};
      const na = r.numeric_axes || {};
      const cid = String(r.candidate_id);
      const on = selected === cid;
      const band = xoBandOf(r);
      return `<article class="hw-card" data-cid="${esc(cid)}" tabindex="0" aria-selected="${on}">
        <div class="hw-card-head">
          <input type="radio" name="hw-pick-card" value="${esc(cid)}" data-cid="${esc(cid)}"${on ? " checked" : ""}
            aria-label="Select ${esc(r.driver_name || r.driver_id || "row")} ${esc(cid)}">
          <div>
            <b>${esc(r.driver_name || r.driver_id || "–")}</b>
            <span class="mono muted">dz ${esc(dzMmOf(r))} mm · ${esc(shortIdOf(r))}</span>
            <div class="muted" style="font-size:0.76rem;white-space:normal;overflow-wrap:break-word">
              <code>${esc(r.shortlist_reason || "–")}</code></div>
          </div>
        </div>
        <dl class="hw-card-grid">
          <dt>Box W×H×D</dt><dd>${num(b.external_width_mm)}×${num(b.external_height_mm)}×${num(b.external_depth_mm)} mm</dd>
          <dt>Net volume</dt><dd>${num(b.net_volume_l, 1)} L</dd>
          <dt>Tuning</dt><dd>${num(b.derived_tuning_hz, 1)} Hz</dd>
          <dt>Port area</dt><dd>${num(b.port_throat_area_cm2, 0)} cm²</dd>
          <dt>F3</dt><dd>${num(b.f3_hz, 1)} Hz</dd>
          <dt>XO</dt><dd>${num(r.xo_hz, 0)} Hz${band ? ` (${num(band[0], 0)}–${num(band[1], 0)})` : ""}</dd>
          <dt>Match H</dt><dd>${fmtAxis(na.match_error_h_db2, "match_error_h_db2")} dB²</dd>
          <dt>Match V</dt><dd>${fmtAxis(na.match_error_v_db2, "match_error_v_db2")} dB²</dd>
          <dt>Excursion margin</dt><dd>${num(na.excursion_margin_db, 1)} dB</dd>
          <dt>Port velocity</dt><dd>${num(na.port_velocity_ratio, 2)} × limit</dd>
          <dt>Footprint</dt><dd>${num(na.cabinet_footprint_m2, 3)} m²</dd>
        </dl>
        <div class="hw-card-gates">${feasChips(r.feasibility)}</div>
      </article>`;
    };

    const headInner = d => {
      const active = sort && d.sort && sort.key === d.sort;
      const arrow = d.axisKey ? dirArrow(d.axisKey, axisDirs) : "";
      const dirText = d.axisKey ? dirWord(d.axisKey, axisDirs) : "";
      const ind = active ? (sort.dir > 0 ? "▲" : "▼") : "↕";
      const title = d.title || d.name;
      return `${d.head()}${arrow ? ` <span class="muted" aria-hidden="true" title="${esc(dirText)}">${arrow}</span>` : ""}${d.sort
        ? ` <button type="button" class="linkish" data-sort="${esc(d.sort)}"
            title="Sort by ${esc(title)}${dirText ? " (" + esc(dirText) + ")" : ""}"
            aria-label="Sort by ${esc(title)}${dirText ? ", " + esc(dirText) : ""}">${ind}</button>` : ""}`;
    };

    function tableHtml(list) {
      const vis = visible();
      let groupRow = "", headRow = "";
      for (let i = 0; i < vis.length;) {
        const d = vis[i];
        if (!d.group) {
          groupRow += `<th scope="col" rowspan="2" data-col="${esc(d.key)}" class="${thClass(d)}"
            data-sort-th="${d.sort ? esc(d.sort) : ""}"${d.sort ? ` aria-sort="${sort && sort.key === d.sort ? (sort.dir > 0 ? "ascending" : "descending") : "none"}"` : ""}
            ${d.title ? `title="${esc(d.title)}"` : ""}>${headInner(d)}</th>`;
          i += 1;
          continue;
        }
        let j = i;
        while (j < vis.length && vis[j].group === d.group) j += 1;
        groupRow += `<th scope="colgroup" colspan="${j - i}" class="hw-group">${esc(d.group)}</th>`;
        for (let k = i; k < j; k++) {
          const c = vis[k];
          headRow += `<th scope="col" data-col="${esc(c.key)}" class="${thClass(c)}"
            data-sort-th="${esc(c.sort || "")}"${c.sort ? ` aria-sort="${sort && sort.key === c.sort ? (sort.dir > 0 ? "ascending" : "descending") : "none"}"` : ""}
            ${c.title ? `title="${esc(c.title)}"` : ""}>${headInner(c)}</th>`;
        }
        i = j;
      }
      const rowsHtml = list.map(r => {
        const cid = String(r.candidate_id);
        return `<tr class="clickable" data-cid="${esc(cid)}" tabindex="0" aria-selected="${cid === selected}">${vis.map(d => d.cell(r)).join("")}</tr>`;
      }).join("");
      return `<table id="hw-shortlist" aria-label="Shortlist rows">
        <thead><tr class="hw-groups">${groupRow}</tr><tr class="hw-head">${headRow}</tr></thead>
        <tbody>${rowsHtml}</tbody></table>`;
    }

    const paint = () => {
      body.querySelectorAll('input[type="radio"][data-cid]').forEach(r => {
        r.checked = r.dataset.cid === selected;
      });
      body.querySelectorAll("tr[data-cid], .hw-card[data-cid]").forEach(el => {
        el.setAttribute("aria-selected", String(el.dataset.cid === selected));
      });
      const status = body.querySelector("#hw-pick-status");
      if (status) status.textContent = shortlistStatus();
    };
    const pick = cid => {
      selected = String(cid);
      syncUrl();
      paint();
    };

    function paintTable(refocusSort = false) {
      const wrap = body.querySelector("#hw-shortlist-wrap");
      if (!wrap) return;
      const list = shortlist.slice();
      if (sort && SORTERS[sort.key]) {
        list.sort((a, b) => sort.dir * compare(SORTERS[sort.key](a), SORTERS[sort.key](b)));
      }
      wrap.innerHTML = tableHtml(list);

      body.querySelectorAll("#hw-shortlist th[data-sort-th]").forEach(th => th.addEventListener("click", e => {
        if (e.target.closest("button")) return;        // the button handler below owns that path
        const key = th.dataset.sortTh;
        if (!key) return;
        if (sort && sort.key === key) sort.dir = -sort.dir; else sort = { key, dir: 1 };
        paintTable(true);
      }));
      body.querySelectorAll("#hw-shortlist button[data-sort]").forEach(btn => btn.addEventListener("click", e => {
        e.stopPropagation();
        const key = btn.dataset.sort;
        if (sort && sort.key === key) sort.dir = -sort.dir; else sort = { key, dir: 1 };
        paintTable(true);
      }));
      body.querySelectorAll("#hw-shortlist tr[data-cid]").forEach(tr => {
        const cid = tr.dataset.cid;
        tr.addEventListener("click", e => { if (!e.target.closest("input")) pick(cid); });
        tr.addEventListener("keydown", e => {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(cid); }
        });
        const radio = tr.querySelector('input[type="radio"]');
        if (radio) radio.addEventListener("change", () => pick(cid));
      });
      paint();
      wireScrollHints(root);
      // Keep keyboard focus on the sort control that just re-rendered the table.
      if (refocusSort && sort) {
        const again = body.querySelector(`#hw-shortlist button[data-sort="${sort.key}"]`);
        if (again) again.focus({ preventScroll: true });
      }
    }

    body.innerHTML = `<section class="card" id="hw-shortlist-card">
      <div class="fig-head">
        <div class="hw-shortlist-title">
          <h3>${tip("hw_screen", "Shortlist")}</h3>
          <span class="muted">${esc(shortlist.length)} rows · no single winner</span>
        </div>
        <details class="hw-cols" id="hw-cols">
          <summary class="btn btn-sm" aria-label="Choose which shortlist columns are shown">Columns <span class="muted" data-cols-count>${colSel.length}/${defs.length}</span></summary>
          <div class="hw-cols-panel">
            <p class="hw-cols-hint">Shown in the table. The choice is saved in the page address, so a reload keeps it.</p>
            <fieldset class="hw-cols-grid">
              <legend class="sr-only">Shortlist columns</legend>
              ${defs.map(d => `<label><input type="checkbox" value="${esc(d.key)}"${colSel.includes(d.key) ? " checked" : ""}> <span>${esc(d.name)}</span></label>`).join("")}
            </fieldset>
            <div class="btn-row" style="margin-top:8px">
              <button type="button" class="btn btn-sm" data-cols-reset>Default columns</button>
            </div>
          </div>
        </details>
      </div>
      <p class="hint" role="status" id="hw-pick-status" style="font-size:0.8rem">${esc(shortlistStatus())}</p>
      <div class="tbl-scroll hw-table-view" id="hw-shortlist-scroll">
        <div class="tbl-scroll-hint" aria-hidden="true">scroll for all columns →</div>
        <div class="tbl-wrap" id="hw-shortlist-wrap"></div>
      </div>
      <div class="hw-cards">${shortlist.map(cardHtml).join("")}</div>
      <p class="cap" style="font-size:0.78rem">The header groups the columns
        (Box | Low end | Crossover | Match | Build); hover any label for its definition. Arrows are the
        study's own <code>axis_directions</code>: ↓ lower is better, ↑ higher is better. Sort with the
        header control; use <b>Columns</b> to show more fields. The radio (or Enter on a row) picks the
        row the Panel fit tab pre-checks. Below 700 px each row becomes a card.</p>
    </section>`;

    const colsBox = body.querySelector("#hw-cols");
    const colsSummary = colsBox ? colsBox.querySelector("summary") : null;
    const colsCount = body.querySelector("[data-cols-count]");
    const syncChecks = () => {
      if (!colsBox) return;
      colsBox.querySelectorAll('input[type="checkbox"]').forEach(cb => { cb.checked = colSel.includes(cb.value); });
      if (colsCount) colsCount.textContent = `${colSel.length}/${defs.length}`;
    };
    const applyCols = next => {
      const keys = defs.filter(d => next.includes(d.key)).map(d => d.key);
      colSel = keys.length ? COL_ORDER.filter(k => keys.includes(k)) : DEFAULT_COLS.slice();
      if (sort && !visible().some(d => d.sort === sort.key)) sort = null;
      syncChecks();
      syncUrl();
      paintTable();
    };
    if (colsBox) {
      colsBox.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.addEventListener("change", () => {
        const picked = [...colsBox.querySelectorAll('input[type="checkbox"]:checked')].map(i => i.value);
        applyCols(picked);
      }));
      const reset = colsBox.querySelector("[data-cols-reset]");
      if (reset) reset.addEventListener("click", () => applyCols(DEFAULT_COLS.slice()));
      colsBox.addEventListener("keydown", e => {
        if (e.key !== "Escape" || !colsBox.open) return;
        e.preventDefault();
        e.stopPropagation();
        colsBox.open = false;
        if (colsSummary) colsSummary.focus();
      });
      colsBox.addEventListener("focusout", e => {
        if (!colsBox.open) return;
        const to = e.relatedTarget;
        if (to && colsBox.contains(to)) return;
        setTimeout(() => {
          if (colsBox.open && !colsBox.contains(document.activeElement)) colsBox.open = false;
        }, 0);
      });
    }

    paintTable();
  }

  // ── Trade-offs tab ───────────────────────────────────────────────────────
  function padRange(values) {
    let lo = Math.min(...values), hi = Math.max(...values);
    if (!isFinite(lo) || !isFinite(hi)) return [0, 1];
    const pad = hi > lo ? (hi - lo) * 0.08 : Math.max(Math.abs(hi) * 0.1, 0.5);
    lo -= pad; hi += pad;
    if (Math.min(...values) >= 0 && lo < 0) lo = 0;
    if (!(hi > lo)) hi = lo + 1;
    return [lo, hi];
  }

  function renderTradeoffs() {
    if (!xKey || !yKey) {
      body.innerHTML = `<section class="card"><h3>Trade-offs</h3>
        <div class="alert info" role="status">This study records no numeric axes to plot.</div></section>`;
      return;
    }
    const opts = (cur) => numericAxes.map(k =>
      `<option value="${esc(k)}"${k === cur ? " selected" : ""}>${esc(axisOptionLabel(k, axisDirs))}</option>`).join("");
    const glyph = kind => {
      const fill = kind === "kept" ? css("--muted") : kind === "filled" ? css("--accent") : "none";
      const stroke = kind === "ring" ? css("--ink") : kind === "picked" ? css("--best") : "none";
      const r = kind === "picked" ? 5.4 : kind === "ring" ? 4.6 : 3;
      const sw = kind === "picked" ? 2 : 1.3;
      return `<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"
        style="vertical-align:-2px;margin-right:4px"><circle cx="7" cy="7" r="${r}" fill="${fill}"
        ${stroke !== "none" ? `stroke="${stroke}" stroke-width="${sw}"` : ""}
        opacity="${kind === "kept" ? 0.55 : 1}"/></svg>`;
    };

    body.innerHTML = `<div class="stack" style="gap:14px">
      <section class="fig">
        <div class="fig-head">
          <h3>Trade-offs · kept rows</h3>
          <div class="btn-row" style="gap:8px">
            <label class="muted" style="display:flex;flex-wrap:wrap;gap:4px;align-items:center;min-width:0;max-width:100%;font-size:0.78rem">X <select id="hw-x-axis" style="max-width:100%;min-width:0;width:auto">${opts(xKey)}</select></label>
            <label class="muted" style="display:flex;flex-wrap:wrap;gap:4px;align-items:center;min-width:0;max-width:100%;font-size:0.78rem">Y <select id="hw-y-axis" style="max-width:100%;min-width:0;width:auto">${opts(yKey)}</select></label>
          </div>
        </div>
        <div id="hw-scatter"></div>
        <div class="legend" style="font-size:0.8rem;gap:6px 18px;align-items:center">
          <span>${glyph("kept")}kept row</span>
          <span>${glyph("ring")}Pareto front</span>
          <span>${glyph("filled")}shortlisted</span>
          <span>${glyph("picked")}picked</span>
          <span class="muted">↓ = lower is better · ↑ = higher is better</span>
        </div>
        <p class="cap" style="max-width:88ch">Each dot is a kept candidate, plotted on the study's own
          numeric axes; a row missing either chosen axis is not plotted. Identical points are jittered
          deterministically so every row can be clicked. Panel-fit rejected cells are not plotted: they
          have no numeric axes, so they cannot be placed on this chart.</p>
      </section>
      <section class="card"><h3>Selected row</h3><div id="hw-sel-block"></div></section>
    </div>`;

    const host = body.querySelector("#hw-scatter");
    const xSel = body.querySelector("#hw-x-axis");
    const ySel = body.querySelector("#hw-y-axis");

    const drawSel = () => {
      const slot = body.querySelector("#hw-sel-block");
      if (!slot) return;
      const row = selected ? byId.get(selected) : null;
      if (!row) {
        slot.innerHTML = `<p class="muted">No row picked yet. Click a dot, or pick one in the
          <a href="${tabHref("shortlist")}">Shortlist tab</a>.</p>`;
        return;
      }
      const cid = String(row.candidate_id);
      const isShort = shortlist.some(r => String(r.candidate_id) === cid);
      const isPareto = (d.pareto_ids || []).some(id => String(id) === cid);
      const b = row.box || {};
      slot.innerHTML = `<p style="margin:0 0 6px"><b>${esc(row.driver_name || row.driver_id || "–")}</b>
          <span class="mono muted">${esc(cid)}</span></p>
        <div class="pill-row" style="margin:0 0 8px">
          ${isShort ? `<span class="pill good">shortlisted</span>` : `<span class="pill">kept, not shortlisted</span>`}
          ${isPareto ? `<span class="pill">Pareto front</span>` : ""}
          ${row.shortlist_reason ? `<span class="pill" title="shortlist_reason">${esc(row.shortlist_reason)}</span>` : ""}
        </div>
        ${kvTable([
          [AXIS_META[xKey].label, esc(`${fmtAxis(row.numeric_axes && row.numeric_axes[xKey], xKey)} ${AXIS_META[xKey].unit}`)],
          [AXIS_META[yKey].label, esc(`${fmtAxis(row.numeric_axes && row.numeric_axes[yKey], yKey)} ${AXIS_META[yKey].unit}`)],
          ["Box W×H×D", esc(`${num(b.external_width_mm)}×${num(b.external_height_mm)}×${num(b.external_depth_mm)} mm`)],
          ["Net volume", esc(`${num(b.net_volume_l, 1)} L · wall ${num(b.wall_mm)} mm`)],
          ["XO", esc(`${num(row.xo_hz, 0)} Hz`)],
        ])}
        <p style="margin:8px 0 0"><a href="${tabHref("panel")}">Open this row in Panel fit →</a></p>`;
    };

    const drawScatter = () => {
      if (!host) return;
      const pts = kept.map(r => ({
        row: r,
        x: numOrNull(r.numeric_axes && r.numeric_axes[xKey]),
        y: numOrNull(r.numeric_axes && r.numeric_axes[yKey]),
      })).filter(p => p.x != null && p.y != null);
      if (pts.length < 2) {
        host.innerHTML = `<p class="muted" role="status">Fewer than two kept rows carry both chosen
          axes, so there is nothing to scatter.</p>`;
        return;
      }
      const xr = padRange(pts.map(p => p.x));
      const yr = padRange(pts.map(p => p.y));
      const H = 360;
      // Deterministic jitter in pixel space (16 px) for identical coordinates: every row stays
      // individually clickable even when the hit circles overlap on the chart.
      const Wpx = Math.max(320, host.clientWidth || 460);
      const jitterX = 16 * (xr[1] - xr[0]) / Math.max(80, Wpx - 56);
      const jitterY = 16 * (yr[1] - yr[0]) / Math.max(80, H - 52);
      const groups = new Map();
      for (const p of pts) {
        const key = `${p.x.toFixed(9)}|${p.y.toFixed(9)}`;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(p);
      }
      for (const [key, group] of groups) {
        group.sort((a, b) => String(a.row.candidate_id).localeCompare(String(b.row.candidate_id)));
        const n = group.length;
        let h = 0;
        for (const ch of key) h = (h * 31 + ch.charCodeAt(0)) | 0;
        const base = (Math.abs(h) % 360) * Math.PI / 180;
        group.forEach((p, i) => {
          p.count = n;
          if (n > 1) {
            const ang = base + (2 * Math.PI * i) / n;
            p.jx = p.x + jitterX * Math.cos(ang);
            p.jy = p.y + jitterY * Math.sin(ang);
          } else {
            p.jx = p.x;
            p.jy = p.y;
          }
        });
      }

      host.innerHTML = "";
      const svg = document.createElementNS(NS, "svg");
      svg.dataset.chart = "1";
      svg.style.width = "100%";
      host.appendChild(svg);
      chart(svg, {
        H, xlim: xr, ylim: yr,
        xticks: niceTicks(xr[0], xr[1], 6), yticks: niceTicks(yr[0], yr[1], 5),
        xlabel: axisLabel(xKey, axisDirs), ylabel: axisLabel(yKey, axisDirs),
        series: [{ pts: pts.map(p => [p.jx, p.jy]), color: css("--muted"), dots: true, r: 2.2, opacity: 0.45 }],
        ariaLabel: `Trade-off scatter: ${AXIS_META[xKey].label} against ${AXIS_META[yKey].label} for ${pts.length} kept rows; rings mark the Pareto front and filled dots the shortlist.`,
      });

      // Overlay marks share chart()'s linear scale: margins l=44 r=12 t=20 (ylabel set) b=32.
      const W = Number(svg.getAttribute("width")) || 460;
      const m = { l: 44, r: 12, t: 20, b: 32 };
      const X = v => m.l + (v - xr[0]) / (xr[1] - xr[0]) * (W - m.l - m.r);
      const Y = v => H - m.b - (v - yr[0]) / (yr[1] - yr[0]) * (H - m.t - m.b);
      const plot = svg.querySelector("g[clip-path]") || svg;
      const pareto = new Set((d.pareto_ids || []).map(String));
      const shortSet = new Set(shortlist.map(r => String(r.candidate_id)));

      for (const p of pts) {
        if (pareto.has(String(p.row.candidate_id))) {
          el("circle", { cx: X(p.jx), cy: Y(p.jy), r: 5.2, fill: "none", stroke: css("--ink"), "stroke-width": 1.3 }, plot);
        }
      }
      for (const p of pts) {
        if (shortSet.has(String(p.row.candidate_id))) {
          el("circle", { cx: X(p.jx), cy: Y(p.jy), r: 3.2, fill: css("--accent") }, plot);
        }
      }
      const selPt = pts.find(p => String(p.row.candidate_id) === selected);
      if (selPt) {
        el("circle", { cx: X(selPt.jx), cy: Y(selPt.jy), r: 8.5, fill: "none", stroke: css("--best"), "stroke-width": 2.4 }, plot);
      }
      for (const p of pts) {
        const hit = el("circle", { cx: X(p.jx), cy: Y(p.jy), r: 8, fill: "transparent", style: "cursor:pointer" }, plot);
        const t = el("title", {}, hit);
        t.textContent = `${p.row.driver_name || p.row.driver_id} · ${p.row.candidate_id} · `
          + `${AXIS_META[xKey].label} ${fmtAxis(p.x, xKey)} ${AXIS_META[xKey].unit} · `
          + `${AXIS_META[yKey].label} ${fmtAxis(p.y, yKey)} ${AXIS_META[yKey].unit}`
          + (p.count > 1 ? ` · ${p.count} rows at this point` : "");
        hit.addEventListener("click", () => {
          selected = String(p.row.candidate_id);
          syncUrl();
          drawScatter();
          drawSel();
        });
      }
      if (typeof ResizeObserver !== "undefined") {
        const ro = new ResizeObserver(() => {
          if (!svg.isConnected) { ro.disconnect(); return; }
          requestAnimationFrame(() => { if (svg.isConnected) drawScatter(); });
        });
        ro.observe(svg);
      }
    };

    xSel.addEventListener("change", () => {
      xKey = validAxis(xSel.value) || xKey;
      syncUrl(); drawScatter(); drawSel();
    });
    ySel.addEventListener("change", () => {
      yKey = validAxis(ySel.value) || yKey;
      syncUrl(); drawScatter(); drawSel();
    });

    drawScatter();
    drawSel();
    wireScrollHints(root);
  }

  // ── Rejected tab ─────────────────────────────────────────────────────────
  function renderRejected() {
    const stages = Array.isArray(d.rejected) ? d.rejected : [];
    if (!stages.length) {
      body.innerHTML = `<section class="card"><h3>Rejected cells</h3>
        <div class="alert info" role="status">This study recorded no rejected cells.</div></section>`;
      return;
    }

    const driverName = id => {
      const e = catalogEntry(id);
      return e && e.name ? e.name : String(id);
    };
    const filterStyle = "display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:0.82rem;min-width:0;max-width:100%";
    const selectStyle = "max-width:100%;min-width:0;width:auto";

    body.innerHTML = `<section class="card">
      <div class="fig-head"><h3>Rejected cells</h3>
        <span class="muted">${esc(stages.reduce((n, s) => n + (Array.isArray(s.rows) ? s.rows.length : (s.count || 0)), 0))} rows in ${esc(stages.length)} stages</span></div>
      <p class="cap" style="max-width:78ch">Every reason is printed exactly as the screen recorded it,
        never shortened. The filters narrow by the reason's first token and by driver, and combine.</p>
      <div class="stack" style="gap:16px" id="hw-rej-stages"></div>
    </section>`;

    const host = body.querySelector("#hw-rej-stages");
    host.innerHTML = stages.map((s, i) => {
      const rows = Array.isArray(s.rows) ? s.rows : [];
      const prefixes = [...new Set(rows.flatMap(r => rowReasons(r).map(reasonPrefix)))].sort();
      const drivers = [...new Set(rows.map(r => String(r.driver_id || "?")))].sort();
      const prefixCount = p => rows.filter(r => rowReasons(r).some(x => reasonPrefix(x) === p)).length;
      const driverCount = d => rows.filter(r => String(r.driver_id || "?") === d).length;
      return `<div class="card" data-rej-stage="${i}">
        <div class="fig-head"><h3>${esc(s.stage || "?")}
          <span class="pill">${esc(rows.length)}</span></h3>
          <span class="muted" data-shown>${esc(rows.length)} rows</span></div>
        <div style="display:flex;flex-wrap:wrap;gap:8px 16px;align-items:flex-end;margin:4px 0 8px">
          <label style="${filterStyle}">
            Reason prefix
            <select data-rej-filter="${i}" style="${selectStyle}">
              <option value="">All reasons (${esc(rows.length)})</option>
              ${prefixes.map(p => `<option value="${esc(p)}">${esc(p)} (${esc(prefixCount(p))})</option>`).join("")}
            </select>
          </label>
          <label style="${filterStyle}">
            Driver
            <select data-rej-driver="${i}" style="${selectStyle}">
              <option value="">All drivers (${esc(drivers.length)})</option>
              ${drivers.map(d => `<option value="${esc(d)}">${esc(driverName(d))} (${esc(driverCount(d))})</option>`).join("")}
            </select>
          </label>
        </div>
        <div class="tbl-wrap"><table>
          <thead><tr><th>Driver</th><th>Reasons (verbatim)</th></tr></thead>
          <tbody>${rows.map(r => {
            const reasons = rowReasons(r);
            const extra = Object.entries(r)
              .filter(([k]) => k !== "stage" && k !== "driver_id" && k !== "reason" && k !== "reasons")
              .map(([k, v]) => `${k} ${cel(v)}`).join(" · ");
            return `<tr data-prefixes="${esc(reasons.map(reasonPrefix).join(" "))}" data-driver="${esc(String(r.driver_id || "?"))}">
              <td><code>${esc(r.driver_id || "–")}</code></td>
              <td style="white-space:normal;overflow-wrap:break-word">
                ${reasons.length ? reasons.map(x => `<code style="white-space:normal;overflow-wrap:break-word">${esc(x)}</code>`).join("<br>") : `<span class="muted">no reason recorded</span>`}
                ${extra ? `<br><small class="muted">${esc(extra)}</small>` : ""}
              </td></tr>`;
          }).join("")}</tbody>
        </table></div>
      </div>`;
    }).join("");

    host.querySelectorAll("[data-rej-stage]").forEach(card => {
      const reasonSel = card.querySelector("select[data-rej-filter]");
      const driverSel = card.querySelector("select[data-rej-driver]");
      const apply = () => {
        const wantPrefix = reasonSel ? reasonSel.value : "";
        const wantDriver = driverSel ? driverSel.value : "";
        let shown = 0;
        card.querySelectorAll("tbody tr[data-prefixes]").forEach(tr => {
          const hit = (!wantPrefix || tr.dataset.prefixes.split(" ").includes(wantPrefix))
            && (!wantDriver || tr.dataset.driver === wantDriver);
          tr.hidden = !hit;
          if (hit) shown++;
        });
        const total = card.querySelectorAll("tbody tr[data-prefixes]").length;
        const out = card.querySelector("[data-shown]");
        if (out) {
          out.textContent = (wantPrefix || wantDriver)
            ? `${shown} of ${total} rows`
            : `${total} rows`;
        }
      };
      if (reasonSel) reasonSel.addEventListener("change", apply);
      if (driverSel) driverSel.addEventListener("change", apply);
    });
    wireScrollHints(root);
  }

  // ── Panel fit tab ────────────────────────────────────────────────────────
  function catalogEntry(driverId) {
    const list = Array.isArray(d.catalog) ? d.catalog : [];
    return list.find(e => e && String(e.driver_id) === String(driverId)) || null;
  }
  function realDiameterM(row) {
    const e = catalogEntry(row.driver_id);
    const r = e ? Number(e.effective_piston_radius_m) : NaN;
    return isFinite(r) && r > 0 ? r * 2 : null;
  }

  /** Three-state reading of the panel-fit response.
   *  BL_PANEL_FIT_PORT_LENGTH_UNAVAILABLE is a geometry pass with an un-checkable port length,
   *  not a separation failure; only wall/separation/area reasons get the red verdict. */
  function panelVerdict(fit) {
    const reason = fit.reason == null ? "" : String(fit.reason);
    const req = Number(fit.required_m);
    const avail = Number(fit.available_m);
    const sepOk = isFinite(req) && isFinite(avail) ? avail >= req : null;
    if (fit.feasible) {
      return { kind: "good", chip: "feasible", color: css("--good"), detail: "" };
    }
    if (reason === "BL_PANEL_FIT_PORT_LENGTH_UNAVAILABLE") {
      return {
        kind: "warn",
        chip: "panel geometry fits; port-length check needs the staged box",
        color: css("--warn"),
        detail: sepOk === true
          ? `separation OK: available ${num(avail, 4)} m >= required ${num(req, 4)} m`
          : "",
      };
    }
    return { kind: "bad", chip: "not feasible", color: css("--bad"), detail: "" };
  }

  function renderPanel() {
    const row = (selected && byId.get(selected)) || shortlist[0] || null;
    if (!row) {
      body.innerHTML = `<section class="card"><h3>Panel fit</h3>
        <div class="alert info" role="status">This study has no row to pre-check. Open the Shortlist tab
          and pick a row once one exists.</div></section>`;
      return;
    }
    const b = row.box || {};
    const need = ["net_volume_l", "wall_mm", "port_throat_area_cm2", "external_height_mm"]
      .every(k => b[k] != null && isFinite(Number(b[k])));
    if (!need) {
      body.innerHTML = `<section class="card"><h3>Panel fit</h3>
        <div class="alert info" role="status">The selected row carries no complete box dimensions, so the
          panel-fit pre-check cannot run on it.</div></section>`;
      return;
    }

    const demoMm = Math.round(demoD * 1000);
    const realM = realDiameterM(row);
    let useReal = false;
    let hMm = clamp(Number(b.external_height_mm), 100, 2000);
    let aCm2 = clamp(Number(b.port_throat_area_cm2), 5, 600);
    const fmtLen = v => Number.isInteger(Number(v)) ? num(v) : Number(v).toFixed(1);

    // The panel tab must not be a one-row dead end: every shortlist row is selectable here, and the
    // picker drives the same ?row= state the Shortlist radio and the scatter dots write.
    const currentId = String(row.candidate_id);
    const shortIds = new Set(shortlist.map(r => String(r.candidate_id)));
    const pickerRows = shortlist.slice();
    if (!shortIds.has(currentId)) pickerRows.unshift(row);   // a kept (scatter-picked) row stays visible
    const pickerOptions = pickerRows.map(r => {
      const bb = r.box || {};
      const cid = String(r.candidate_id || "");
      const tuning = bb.derived_tuning_hz != null && isFinite(Number(bb.derived_tuning_hz))
        ? `${num(bb.derived_tuning_hz, 0)} Hz` : "–";
      const f3 = bb.f3_hz != null && isFinite(Number(bb.f3_hz)) ? `${num(bb.f3_hz, 1)} Hz` : "–";
      const label = `${r.driver_name || r.driver_id || "–"} · Fb ${tuning} · F3 ${f3} · ${cid.slice(0, 8)}`
        + (shortIds.has(cid) ? "" : " · kept, not shortlisted");
      return `<option value="${esc(cid)}"${cid === currentId ? " selected" : ""}>${esc(label)}</option>`;
    }).join("");

    body.innerHTML = `<div class="form-grid" style="margin:0 0 14px">
        <label for="hw-panel-row">Shortlist row (driver · tuning · F3 · id)</label>
        <div style="min-width:0">
          <select id="hw-panel-row" style="max-width:100%;min-width:0;width:auto">${pickerOptions}</select>
          <span class="hint" style="display:block;margin-top:2px">Picking a row here updates
            the selection and every tab.</span>
        </div>
      </div>
      <div class="grid2">
      <section class="fig">
        <div class="fig-head"><h3>${tip("panel_fit", "Front baffle · to scale")}</h3>
          <div class="seg-toggle" role="group" aria-label="Transducer size for the pre-check" style="flex-wrap:wrap">
            <button type="button" data-real="0" aria-pressed="true"
              title="Boundary Lab's demo transducer: Ø ${esc(demoMm)} mm moving diameter">BL demo transducer (${esc(demoMm)} mm)</button>
            <button type="button" data-real="1" aria-pressed="false"${realM == null ? " disabled" : ""}
              title="${realM == null
                ? "This study's catalog carries no effective piston radius for this driver"
                : `Sd-derived from the study catalog: Ø ${esc(num(realM, 4))} m (effective_piston_radius_m)`}">real driver (Sd-derived Ø ${realM == null ? "unavailable" : esc(num(realM, 4)) + " m"})</button>
          </div>
        </div>
        <div id="hw-baffle"><p class="muted" role="status">Waiting for the first check…</p></div>
        <div id="hw-fit-verdict"></div>
        <p class="cap" style="max-width:78ch">Pre-check that mirrors Boundary Lab's validator; Boundary Lab's
          own validate is the authority.</p>
        <p class="cap" style="max-width:78ch">A panel that passes the geometric rules still returns
          <code>BL_PANEL_FIT_PORT_LENGTH_UNAVAILABLE</code>, because this payload carries no tuning —
          it never assumes a port length.</p>
      </section>
      <section class="card">
        <h3>What-if</h3>
        <p class="muted" style="font-size:0.82rem;margin:0 0 10px">Row
          <b>${esc(row.driver_name || row.driver_id || "–")}</b>
          <span class="mono">${esc(row.candidate_id || "")}</span>${selected ? " (picked)" : " (first shortlist row)"}.</p>
        <div class="form-grid">
          <label for="hw-height">Front height</label>
          <div>
            <span class="mono muted" id="hw-height-val">${esc(fmtLen(hMm))} mm</span>
            <input id="hw-height" type="range" min="100" max="2000" step="0.1" value="${esc(hMm)}"
              title="Front-panel height sent as height_mm">
            <span class="hint" style="display:block">100–2000 mm. The check re-runs at this height.</span>
          </div>
          <label for="hw-port-area">Port area</label>
          <div>
            <span class="mono muted" id="hw-port-val">${esc(num(aCm2))} cm²</span>
            <input id="hw-port-area" type="range" min="5" max="600" step="1" value="${esc(aCm2)}"
              title="Port throat area sent as port_throat_area_cm2">
            <span class="hint" style="display:block">5–600 cm². The port radius is drawn from this area.</span>
          </div>
        </div>
        <p class="hint" role="status" id="hw-fit-status" style="font-size:0.8rem;margin:10px 0 0">Checking…
          </p>
        <div style="margin-top:12px">
          ${kvTable([
            ["Box W×H×D", esc(`${num(b.external_width_mm)} × ${num(b.external_height_mm)} × ${num(b.external_depth_mm)} mm`)],
            ["Net volume", esc(`${num(b.net_volume_l, 1)} L`)],
            ["Wall", esc(`${num(b.wall_mm)} mm`)],
            ["Port throat area", esc(`${num(b.port_throat_area_cm2, 0)} cm² (${esc(b.port_type || "–")})`)],
            ["Tuning (derived)", esc(`${num(b.derived_tuning_hz, 1)} Hz`)],
            ["Driver", esc(`${row.driver_id || "–"} · ${row.driver_name || ""}`)],
          ])}
        </div>
      </section>
    </div>`;

    const baffle = body.querySelector("#hw-baffle");
    const verdict = body.querySelector("#hw-fit-verdict");
    const status = body.querySelector("#hw-fit-status");
    const height = body.querySelector("#hw-height");
    const heightVal = body.querySelector("#hw-height-val");
    const portArea = body.querySelector("#hw-port-area");
    const portVal = body.querySelector("#hw-port-val");
    const toggles = [...body.querySelectorAll(".seg-toggle button[data-real]")];
    const picker = body.querySelector("#hw-panel-row");
    if (picker) picker.addEventListener("change", () => {
      const cid = String(picker.value);
      if (!byId.has(cid)) return;
      selected = cid;
      syncUrl();                                     // replaceState: no history spam
      renderPanel();                                 // rebuild for the new row's box and sliders
      const again = body.querySelector("#hw-panel-row");
      if (again) again.focus();
    });

    let timer = null;
    let seq = 0;
    const setStatus = t => { if (status) status.textContent = t; };
    const schedule = (delay = 200) => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(runFit, delay);
    };

    const paintToggle = () => toggles.forEach(btn => {
      btn.setAttribute("aria-pressed", String((btn.dataset.real === "1") === useReal));
    });

    async function runFit() {
      const my = ++seq;
      setStatus("Checking the front panel…");
      const payload = {
        height_mm: hMm,
        port_throat_area_cm2: aCm2,
        net_volume_l: Number(b.net_volume_l),
        wall_mm: Number(b.wall_mm),
        driver_moving_diameter_m: useReal && realM != null ? realM : demoD,
      };
      // The row's own front width/depth are optional to the API; send them when recorded so the
      // drawing matches the box instead of the API's demo default.
      if (isNum(Number(b.external_width_mm))) payload.width_mm = Number(b.external_width_mm);
      if (isNum(Number(b.external_depth_mm))) payload.depth_mm = Number(b.external_depth_mm);
      try {
        const fit = await apiPost("/api/hw/panel-fit", payload);
        if (my !== seq) return;
        const v = panelVerdict(fit);
        const wrapChip = v.chip.length > 30
          ? "white-space:normal;text-align:left;max-width:100%;overflow-wrap:break-word"
          : "";
        verdict.innerHTML = `<div class="pill-row" style="margin:8px 0 6px">
            <span class="pill ${v.kind}" style="${wrapChip}">${esc(v.chip)}</span>
            <span class="pill">port length checked: ${fit.port_length_checked ? "yes" : "no"}</span>
          </div>
          <p class="mono" style="margin:4px 0">required ${esc(num(fit.required_m, 4))} m / available ${esc(num(fit.available_m, 4))} m</p>
          ${v.detail ? `<p class="mono" style="margin:4px 0">${esc(v.detail)}</p>` : ""}
          <p style="margin:4px 0 0">Reason <code style="white-space:normal;overflow-wrap:break-word">${esc(fit.reason == null ? "—" : fit.reason)}</code></p>`;
        drawBaffle(baffle, fit);
        setStatus(`Checked at ${num(hMm)} mm front height and ${num(aCm2)} cm² port area with the ${useReal ? "real" : "BL demo"} transducer.`);
      } catch (e) {
        if (my !== seq) return;
        verdict.innerHTML = errBanner(e.message);
        baffle.innerHTML = `<p class="muted">The drawing needs a successful panel-fit response.</p>`;
        setStatus("The pre-check was refused; the server message is shown above.");
      }
    }

    height.addEventListener("input", () => {
      hMm = clamp(Number(height.value), 100, 2000);
      heightVal.textContent = `${fmtLen(hMm)} mm`;
      schedule();
    });
    portArea.addEventListener("input", () => {
      aCm2 = clamp(Number(portArea.value), 5, 600);
      portVal.textContent = `${num(aCm2)} cm²`;
      schedule();
    });
    toggles.forEach(btn => btn.addEventListener("click", () => {
      if (btn.disabled) return;
      useReal = btn.dataset.real === "1";
      paintToggle();
      schedule();
    }));

    paintToggle();
    schedule(0);
    wireScrollHints(root);
  }

  /** The to-scale front baffle: outer panel, walls, driver and flared port, plus the API's
   *  required/available separation as two to-scale arrows. Every dimension is from the response. */
  function drawBaffle(host, fit) {
    if (!host) return;
    const inp = fit.inputs || {};
    const wmm = Number(inp.width_mm), hmm = Number(inp.height_mm), wall = Number(inp.wall_mm);
    const driverD = Number(inp.driver_moving_diameter_m) * 1000;
    const area = Number(inp.port_throat_area_cm2);
    const portR = Math.sqrt(area * 100 / Math.PI);          // mm, from the port throat area
    const W = Math.max(380, host.clientWidth || 480);
    const stripW = 174, padL = 16, padT = 58, padB = 66;
    const s = Math.min((W - padL - stripW - 18) / wmm, 300 / hmm);
    const panelW = wmm * s, panelH = hmm * s;
    const panelTop = padT, panelBottom = padT + panelH;
    const H = Math.max(panelH + padT + padB, 240);
    const px = mm => padL + mm * s;
    const py = mm => panelTop + panelH - mm * s;
    const cx = px(wmm / 2);
    const dyMm = Number(fit.driver_y_m) * 1000;
    const portYmm = Number(fit.port_y_m) * 1000;
    const dCy = py(hmm / 2 + dyMm);
    const pCy = py(hmm / 2 + portYmm);
    const dr = driverD / 2 * s;
    const pr = portR * s;
    const v = panelVerdict(fit);

    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("width", W);
    svg.setAttribute("height", H);
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", `Front baffle ${num(wmm)} by ${num(hmm)} mm with ${num(wall)} mm walls; driver ${num(driverD)} mm at y ${num(dyMm, 1)} mm; port ${num(area)} square centimetres at y ${num(portYmm, 1)} mm; required separation ${num(fit.required_m, 4)} m, available ${num(fit.available_m, 4)} m; ${v.chip}.`);
    const ink = css("--ink"), muted = css("--muted"), rule = css("--rule"), accent = css("--accent");
    const label = (x, y, t, anchor = "start", col = muted, size = 11, weight = "") => {
      const e = el("text", { x, y, "text-anchor": anchor, style: `fill:${col};font-size:${size}px;${weight ? `font-weight:${weight};` : ""}` }, svg);
      e.textContent = t;
      return e;
    };
    const leader = (x1, y1, x2, y2, col) =>
      el("line", { x1, y1, x2, y2, stroke: col, "stroke-width": 1, "stroke-dasharray": "2 2" }, svg);
    const arrowRight = (x, y, col) => {
      el("path", { d: `M${x - 5},${y - 4} L${x},${y} L${x - 5},${y + 4} Z`, fill: col }, svg);
    };
    const arrowVertical = (x, y, dir, col) => {
      // dir -1 points up (tip at y), +1 points down
      el("path", { d: `M${x - 4},${y - dir * 5} L${x},${y} L${x + 4},${y - dir * 5} Z`, fill: col }, svg);
    };

    // Header above the panel, on the margin.
    label(px(0), 14, `front baffle · ${num(wmm)} × ${num(hmm)} mm · wall ${num(wall)} mm`, "start", muted);

    // Panel + walls (outer edge solid, wall inner edge dashed).
    el("rect", { x: px(0), y: panelTop, width: panelW, height: panelH, fill: css("--viz-canvas"), stroke: ink, "stroke-width": 1.6 }, svg);
    el("rect", {
      x: px(wall), y: panelTop + wall * s,
      width: Math.max(0, panelW - 2 * wall * s), height: Math.max(0, panelH - 2 * wall * s),
      fill: css("--surface"), stroke: rule, "stroke-width": 1, "stroke-dasharray": "3 3",
    }, svg);
    el("line", { x1: cx, x2: cx, y1: panelTop, y2: panelBottom, stroke: rule, "stroke-dasharray": "2 4", "stroke-width": 1 }, svg);

    // Driver cutout, with its label and leader in the top margin (outside the panel stroke).
    el("circle", { cx, cy: dCy, r: dr, fill: accent, "fill-opacity": 0.15, stroke: accent, "stroke-width": 2 }, svg);
    el("circle", { cx, cy: dCy, r: 1.6, fill: accent }, svg);
    const driverLabelY = panelTop - 22;
    label(cx, driverLabelY, `driver Ø ${num(driverD)} mm`, "middle", accent, 11, "600");
    leader(cx, driverLabelY + 7, cx, Math.max(panelTop + 3, dCy - dr), accent);

    // Port cutout + the BL port roundover, with its label in the bottom margin.
    el("circle", { cx, cy: pCy, r: pr, fill: "none", stroke: ink, "stroke-width": 1.8 }, svg);
    if (roundoverMm != null && roundoverMm > 0) {
      el("circle", { cx, cy: pCy, r: pr + roundoverMm * s, fill: "none", stroke: muted, "stroke-width": 1, "stroke-dasharray": "3 3" }, svg);
    }
    const portLabelY = panelBottom + 30;
    label(cx, portLabelY,
      `port Ø ${num(portR * 2)} mm (${num(area)} cm²)${roundoverMm != null ? ` · flare ${num(roundoverMm)} mm` : ""}`,
      "middle", ink);
    leader(cx, Math.min(panelBottom - 3, pCy + pr), cx, portLabelY - 9, muted);

    // Centre-to-centre dimension between the two cutout edges (no text on the drawing itself).
    const gapTop = dCy + dr, gapBot = pCy - pr;
    if (gapBot > gapTop + 6) {
      el("line", { x1: cx, x2: cx, y1: gapTop, y2: gapBot, stroke: css("--label"), "stroke-width": 1, "stroke-dasharray": "4 3" }, svg);
      arrowVertical(cx, gapTop, -1, css("--label"));
      arrowVertical(cx, gapBot, 1, css("--label"));
    }

    // Verdict strip: two to-scale arrows for the API's required and available separation.
    const sx = W - stripW + 2;
    label(sx, 14, "separation (API)", "start", muted);
    const maxM = Math.max(Number(fit.required_m), Number(fit.available_m), 1e-6);
    const barMax = stripW - 66;
    const reqLen = Math.max(2, Number(fit.required_m) / maxM * barMax);
    const avLen = Math.max(2, Number(fit.available_m) / maxM * barMax);
    const yReq = 54, yAv = 104;
    label(sx, yReq - 8, `required ${num(fit.required_m, 4)} m`, "start", css("--bad"), 10, "600");
    el("line", { x1: sx, x2: sx + reqLen, y1: yReq, y2: yReq, stroke: css("--bad"), "stroke-width": 3 }, svg);
    arrowRight(sx + reqLen, yReq, css("--bad"));
    label(sx, yAv - 8, `available ${num(fit.available_m, 4)} m`, "start", css("--good"), 10, "600");
    el("line", { x1: sx, x2: sx + avLen, y1: yAv, y2: yAv, stroke: css("--good"), "stroke-width": 3 }, svg);
    arrowRight(sx + avLen, yAv, css("--good"));
    label(sx, yAv + 34, v.kind === "warn" ? "panel fits · port length?" : v.chip, "start", v.color, 12, "600");
    label(sx, yAv + 58, `driver y ${num(dyMm, 1)} mm`, "start", muted, 10);
    label(sx, yAv + 74, `port y ${num(portYmm, 1)} mm`, "start", muted, 10);
    label(sx, yAv + 90, `driver Ø ${num(driverD)} mm`, "start", muted, 10);
    if (roundoverMm != null) label(sx, yAv + 106, `port flare ${num(roundoverMm)} mm`, "start", muted, 10);

    // Scale bar (100 mm) under the baffle, below the port callout.
    const sy = panelBottom + 54;
    el("line", { x1: padL, x2: padL + 100 * s, y1: sy, y2: sy, stroke: muted, "stroke-width": 2 }, svg);
    label(padL + 100 * s + 4, sy + 4, "100 mm");

    host.innerHTML = "";
    host.appendChild(svg);
    host.insertAdjacentHTML("beforeend", `<p class="cap" style="margin:6px 0 0">Outer panel, walls, driver
      cutout and port opening are drawn at one scale; the dashed port ring is the recorded flare. The two
      arrows at the right compare the API's required and available centre separation.</p>`);
  }

  function renderTab() {
    if (tab === "tradeoffs") renderTradeoffs();
    else if (tab === "rejected") renderRejected();
    else if (tab === "panel") renderPanel();
    else renderShortlist();
  }

  renderTab();
}
