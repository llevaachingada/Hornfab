// hw_new.js — hornlab-search GUI   AGPL-3.0-or-later
//
// Horn + woofer · the New system wizard and Quick launch (P5 —
// docs/research/system_woofer_2026-11-18/GUI_COMPLETION_HANDOFF_2026-11-19.md §4, §5.2, §5.2a, §8;
// GUI_SENIOR_REVIEW_2026-11-20.md §4 step 11):
//   #/hw/new      4-step guided wizard: horn → woofer drivers → box limits/targets → screen
//   #/hw/launch   quick launch from a saved spec, a saved horn and one or more drivers
//
// All data comes from the Python readers:
//   GET  /api/hw/assets?limit=200   saved-horn inventory (newest 200 run dirs; no meshing)
//   GET  /api/hw/drivers            sourced woofer catalog + geometry completeness + R15 provenance
//   GET  /api/hw/spec-defaults      the committed example spec, parsed by the frozen contract parser
//   GET  /api/hw/specs              saved specs under examples/systems/user/
//   POST /api/hw/spec/validate      the parser's own verdict, field by field
//   POST /api/hw/spec/save          the one sanctioned writer (explicit replace confirm here)
//   POST /api/preview               the exact command a launch would run (kind "hw-screen")
//   POST /api/jobs                  launch one CPU screen job (never used by this task)
//   GET  /api/jobs, /api/job/<id>   recorded screen time + job progress
//
// JS formats and lays out only: no acoustic arithmetic, no channel summing, no inferred labels.
// House rules kept here: eyebrow + h2 + mono id + pill-row (no <h1>); the newRunModeHtml-style
// Guided / Quick launch switch; .form-grid + .hint/role=status; <pre> command preview; glossary
// tips on technical labels; skeletons while loading; step and selection state in the URL query;
// visible reasons for every disabled action; Esc closes a disclosure and returns focus.

import { tip } from "./glossary.js";

// ── Helpers copied from hw_screen.js / hw.js / app.js (local there, not exported) ──

const MISSING = "—";

const esc = s => (s == null ? MISSING : String(s))
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

/** Same as app.js: break long ids at _ - . / instead of widening the page. */
function brk(s) {
  return esc(s).replace(/([_\-./])/g, "$1<wbr>");
}

const fmtHz = v => v == null || !isFinite(v) ? MISSING
  : v >= 1000 ? (v / 1000).toFixed(1) + " kHz" : Math.round(v) + " Hz";
const num = (v, d = 0) => (v == null || !isFinite(v)) ? MISSING : Number(v).toFixed(d);
/** Range endpoints keep integers clean (340–510) and show one decimal otherwise (0–0.2). */
const rangeVal = v => (v == null || !isFinite(Number(v))) ? MISSING
  : Number.isInteger(Number(v)) ? String(Number(v)) : Number(v).toFixed(1);

/** A number from an input; blank / non-finite becomes null (the parser owns the refusal). */
function readNum(el) {
  const raw = String(el && el.value != null ? el.value : "").trim();
  if (raw === "") return null;
  const n = Number(raw);
  return isFinite(n) ? n : null;
}

const inputValue = v => (v == null || v === "" || !isFinite(Number(v))) ? "" : String(v);

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

/** Query string after the hash (the router also hands one in for these two routes). */
const hashQuery = () => new URLSearchParams((location.hash.split("?")[1] || ""));
const readQuery = (q) => {
  if (typeof q !== "string" || !q) return hashQuery();
  return new URLSearchParams(q.replace(/^[#/]+/, "").replace(/^\?/, ""));
};

const ROUTE_NEW = "#/hw/new";
const ROUTE_LAUNCH = "#/hw/launch";

/** Replace the URL fragment without firing hashchange (so the view keeps its DOM/focus). */
function writeRoute(route, params) {
  const qs = params.toString();
  history.replaceState(null, "", route + (qs ? "?" + qs : ""));
}

const NAME_RE = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$/;
const isValidName = name => typeof name === "string" && NAME_RE.test(name) && name.indexOf("..") < 0;

/** The parser reports a field token (e.g. external_width_mm) and we render groups by full path. */
function fieldMatches(groupField, parserField) {
  const g = String(groupField || "").toLowerCase();
  const p = String(parserField || "").toLowerCase();
  if (!p || p === "spec") return false;
  const last = g.split(".").pop() || "";
  return g === p || last === p || last.replace(/_range$/, "") === p
    || g.endsWith("." + p) || last.replace(/_range$/, "").endsWith("." + p);
}

/** Median duration of completed hw-screen jobs (timing only; never an acoustic number). */
function completedScreenTimes(jobs) {
  const out = [];
  for (const j of (Array.isArray(jobs) ? jobs : [])) {
    if (!j || String(j.kind || "") !== "hw-screen" || j.status !== "done") continue;
    if (!j.started || !j.ended) continue;
    const s = (new Date(j.ended).getTime() - new Date(j.started).getTime()) / 1000;
    if (isFinite(s) && s > 0) out.push(s);
  }
  out.sort((a, b) => a - b);
  if (!out.length) return { seconds: null, samples: 0 };
  return { seconds: out[Math.floor(out.length / 2)], samples: out.length };
}

function secondsLabel(seconds) {
  if (seconds == null) return "";
  if (seconds < 120) return `${Math.round(seconds)} s`;
  return `${(seconds / 60).toFixed(1)} min`;
}

function laneNote(state) {
  const base = "CPU · one system job at a time";
  if (state.screenSeconds == null) {
    return `${base} · no screen timing recorded on this machine yet; seconds to a few minutes.`;
  }
  const n = state.screenSamples;
  return `${base} · about ${secondsLabel(state.screenSeconds)} on this machine `
    + `(median of ${n} recorded screen${n === 1 ? "" : "s"}).`;
}

const studyIdFromLog = text => {
  const m = String(text || "").match(/study_id:\s*([0-9a-f]{16})/i);
  return m ? m[1] : null;
};

const tailLines = (text, n = 20) => String(text || "").trim().split(/\r?\n/).slice(-n).join("\n");

// ── Header, mode switch, steps ──────────────────────────────────────────────

function pageHead({ eyebrow, title, id, pills = "" }) {
  return `<div>
    <div class="eyebrow">${esc(eyebrow)}</div>
    <h2>${esc(title)}</h2>
    <p id="hwn-head-id" class="mono muted" style="font-size:0.78rem;overflow-wrap:anywhere">${brk(id || "")}</p>
    ${pills ? `<div class="pill-row" style="margin:8px 0 0">${pills}</div>` : ""}
  </div>`;
}

/** The Guided / Quick launch switch. Buttons (not links) so aria-pressed is valid here. */
function modeSwitchHtml(active) {
  const b = (key, label, sub) => `<button type="button" class="run-tab-link hwn-mode"
    data-mode="${key}" aria-pressed="${active === key}">${esc(label)}
    <span class="muted" style="font-weight:400">${sub}</span></button>`;
  return `<nav class="run-tabs new-run-modes" aria-label="New system mode">
    ${b("guided", "Guided", "— step by step")}
    ${b("launch", "Quick launch", "— from a saved spec")}
  </nav>`;
}

const WIZARD_STEPS = [
  ["1", "Pick a horn"],
  ["2", "Pick woofer drivers"],
  ["3", "Box limits and targets"],
  ["4", "Screen"],
];

function stepperHtml(step) {
  return `<nav class="hwn-steps" aria-label="New system steps">
    ${WIZARD_STEPS.map(([n, label]) => `<button type="button" class="hwn-step" data-step="${n}"
      aria-controls="hwn-step-body"${Number(n) === step ? ' aria-current="step"' : ""}>
      <span class="hwn-step-n" aria-hidden="true">${n}</span>${esc(label)}</button>`).join("")}
  </nav>`;
}

// ── Scoped layout styles (this module only; app.css untouched) ──────────────

const STYLE_ID = "hw-new-style";
const NEW_CSS = `
#hw-new-view, #hw-launch-view { min-width:0; }
#hw-new-view [hidden], #hw-launch-view [hidden] { display:none !important; }
#hw-new-view .hwn-mode, #hw-launch-view .hwn-mode {
  background:none; border:0; border-bottom:2px solid transparent;
  font:inherit; color:var(--label); cursor:pointer; padding:8px 14px; text-align:left; }
#hw-new-view .hwn-mode[aria-pressed="true"], #hw-launch-view .hwn-mode[aria-pressed="true"] {
  color:var(--ink); font-weight:600; border-bottom-color:var(--accent); }
#hw-new-view .hwn-mode:focus-visible, #hw-launch-view .hwn-mode:focus-visible {
  outline:2px solid var(--accent); outline-offset:-2px; border-radius:4px; }
#hw-new-view .form-label, #hw-launch-view .form-label {
  font-family:var(--f-mono); font-size:0.8rem; color:var(--muted);
  padding-top:8px; white-space:nowrap; }
/* app.css only styles .hint inside .form-grid (no global rule): scope the house hint here. */
#hw-new-view .hint, #hw-launch-view .hint {
  font-size:0.8rem; color:var(--muted); line-height:1.45; }
#hw-new-view code, #hw-launch-view code { overflow-wrap:anywhere; }
#hw-new-view .form-grid > *, #hw-launch-view .form-grid > * { min-width:0; }
#hw-new-view .form-grid input, #hw-new-view .form-grid select, #hw-new-view .form-grid textarea,
#hw-launch-view .form-grid input, #hw-launch-view .form-grid select, #hw-launch-view .form-grid textarea {
  min-width:0; max-width:100%; }

.hwn-steps { display:flex; flex-wrap:wrap; gap:6px; min-width:0; }
.hwn-step {
  min-width:0; max-width:100%; font:inherit; font-size:0.84rem; line-height:1.25;
  padding:6px 10px; border:1px solid var(--rule); border-radius:999px;
  background:var(--surface); color:var(--label); cursor:pointer; text-align:left;
  white-space:normal; overflow-wrap:anywhere; }
.hwn-step:hover { border-color:var(--accent); color:var(--ink); }
.hwn-step[aria-current="step"] {
  border-color:var(--accent); color:var(--ink); font-weight:600;
  background:color-mix(in srgb, var(--accent) 10%, var(--surface)); }
.hwn-step:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.hwn-step-n { font-family:var(--f-mono); font-size:0.72rem; color:var(--accent); margin-right:6px; }

.hwn-filter { display:flex; flex-wrap:wrap; gap:8px 14px; align-items:center; min-width:0; }
.hwn-filter input[type="search"] {
  flex:1 1 220px; min-width:0; max-width:100%; font:inherit; font-size:0.9rem;
  background:var(--bg); color:var(--ink); border:1px solid var(--rule);
  border-radius:5px; padding:6px 10px; }
.hwn-filter input[type="search"]:focus { outline:2px solid var(--accent); border-color:var(--accent); }
.hwn-toggle { display:inline-flex; gap:6px; align-items:center; font-size:0.82rem;
  color:var(--muted); min-width:0; cursor:pointer; }
.hwn-toggle input { width:15px; height:15px; margin:0; accent-color:var(--accent); }

.hwn-grid {
  display:grid; grid-template-columns:repeat(auto-fill,minmax(min(100%,250px),1fr));
  gap:10px; min-width:0; }
#hw-new-view .hwn-asset, #hw-new-view .hwn-driver,
#hw-launch-view .hwn-asset, #hw-launch-view .hwn-driver {
  white-space:normal; }   /* .form-grid label sets nowrap; card text must wrap */
.hwn-asset {
  display:grid; grid-template-columns:auto minmax(0,1fr); gap:10px; align-items:start;
  border:1px solid var(--rule); border-radius:8px; background:var(--surface);
  padding:10px 12px; min-width:0; cursor:pointer; }
.hwn-asset:hover { border-color:var(--accent); }
.hwn-asset.is-picked {
  border-color:var(--accent);
  background:color-mix(in srgb, var(--accent) 8%, var(--surface)); }
.hwn-asset:focus-within { outline:2px solid var(--accent); outline-offset:-2px; }
.hwn-asset input[type="radio"], .hwn-driver input[type="checkbox"] {
  width:15px; height:15px; margin:2px 0 0; accent-color:var(--accent); }
.hwn-asset-body { min-width:0; overflow-wrap:anywhere; }
.hwn-name { display:block; font-weight:600; font-size:0.92rem; overflow-wrap:anywhere; }

.hwn-kv { display:grid; grid-template-columns:max-content minmax(0,1fr);
  gap:2px 8px; margin:8px 0 0; font-size:0.78rem; }
.hwn-kv dt { color:var(--label); font-family:var(--f-mono); font-size:0.66rem;
  text-transform:uppercase; letter-spacing:0.04em; }
.hwn-kv dd { margin:0; min-width:0; overflow-wrap:anywhere; }

.hwn-drivers {
  display:grid; grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr));
  gap:10px; min-width:0; }
.hwn-driver {
  display:grid; grid-template-columns:auto minmax(0,1fr); gap:10px; align-items:start;
  border:1px solid var(--rule); border-radius:8px; background:var(--surface);
  padding:10px 12px; min-width:0; cursor:pointer; }
.hwn-driver:hover { border-color:var(--accent); }
.hwn-driver.is-picked {
  border-color:var(--accent);
  background:color-mix(in srgb, var(--accent) 8%, var(--surface)); }
.hwn-driver:focus-within { outline:2px solid var(--accent); outline-offset:-2px; }

.hwn-range { display:flex; flex-wrap:wrap; gap:6px; align-items:center; min-width:0; }
.hwn-range input { width:7.5rem; max-width:100%; min-width:0; }
.hwn-range > span { font-size:0.78rem; color:var(--muted); }
.hwn-field { min-width:0; }
.hwn-field .hint { margin-top:4px; }
.hwn-field [data-error-for] { margin-top:4px; }
.hwn-field .alert { padding:8px 10px; font-size:0.8rem; }
.hwn-field input[aria-invalid="true"], .hwn-field select[aria-invalid="true"] {
  border-color:var(--bad); }

.hwn-save-row { display:flex; flex-wrap:wrap; gap:8px; align-items:center; min-width:0; }
.hwn-save-row input {
  flex:1 1 220px; min-width:0; max-width:100%; font:inherit; font-size:0.9rem;
  background:var(--bg); color:var(--ink); border:1px solid var(--rule);
  border-radius:5px; padding:6px 10px; }
.hwn-save-row input:focus { outline:2px solid var(--accent); border-color:var(--accent); }

.hwn-specs { display:grid; gap:6px; min-width:0; }
.hwn-spec-row {
  display:flex; flex-wrap:wrap; gap:4px 10px; align-items:baseline; min-width:0;
  padding:6px 0; border-bottom:1px solid var(--rule); font-size:0.84rem;
  overflow-wrap:anywhere; }
.hwn-spec-row:last-child { border-bottom:0; }
.hwn-spec-row > * { min-width:0; max-width:100%; }
.hwn-spec-row .mono { font-size:0.74rem; }

.hwn-cmd {
  white-space:pre-wrap; word-break:break-word; overflow-wrap:anywhere;
  max-width:100%; margin:0; font-size:0.82rem; background:var(--bg);
  border:1px solid var(--rule); border-radius:6px; padding:10px 12px; color:var(--ink); }
.hwn-summary { display:grid; grid-template-columns:max-content minmax(0,1fr);
  gap:4px 12px; font-size:0.86rem; margin:0; }
.hwn-summary dt { color:var(--label); font-family:var(--f-mono); font-size:0.7rem;
  text-transform:uppercase; letter-spacing:0.04em; padding-top:2px; }
.hwn-summary dd { margin:0; min-width:0; overflow-wrap:anywhere; }

.hwn-actions { display:flex; flex-wrap:wrap; gap:8px; align-items:center; min-width:0; }
.hwn-adv { border:1px solid var(--rule); border-radius:6px; padding:8px 12px; min-width:0; }
.hwn-adv > summary { cursor:pointer; font-family:var(--f-mono); font-size:0.78rem;
  color:var(--label); }
.hwn-adv > summary:focus-visible { outline:2px solid var(--accent); outline-offset:2px;
  border-radius:4px; }
.hwn-job-tail { margin:8px 0 0; max-height:13rem; overflow:auto; }

@media (max-width:700px) {
  .hwn-kv { grid-template-columns:minmax(0,1fr); }
  .hwn-kv dt { margin-top:4px; }
  .hwn-summary { grid-template-columns:minmax(0,1fr); }
  .hwn-summary dt { padding-top:4px; }
  .hwn-range input { width:100%; flex:1 1 6.5rem; }
}
`;

function ensureStyles() {
  if (typeof document === "undefined" || document.getElementById(STYLE_ID)) return;
  const s = document.createElement("style");
  s.id = STYLE_ID;
  s.textContent = NEW_CSS;
  document.head.appendChild(s);
}

// ── Shared asset + driver markup ────────────────────────────────────────────

const bandLabel = a => {
  const b = a && Array.isArray(a.band_hz) ? a.band_hz : null;
  return b && b.length >= 2 && b[0] != null && b[1] != null
    && isFinite(Number(b[0])) && isFinite(Number(b[1]))
    ? `${fmtHz(Number(b[0]))}–${fmtHz(Number(b[1]))}` : MISSING;
};

const qualityPill = a => {
  const q = (a && a.quality) || MISSING;
  const cls = q === "EXACT_COMPLEX" ? "good" : q === "MAGNITUDE_ONLY" ? "warn" : "";
  return `<span class="pill ${cls}">${tip("hw_fidelity", "Quality")}: <b>${esc(q)}</b></span>`;
};

const meshPill = a => {
  const have = !!(a && a.full_domain_mesh);
  const title = have
    ? "A ref_case/horn_full provenance document names this design hash and its recorded mesh.msh is on disk."
    : "No recorded full-domain mesh provenance for this design hash in the system store.";
  return `<span class="pill ${have ? "good" : ""}" title="${esc(title)}">`
    + `${have ? "full-domain mesh" : "no full-domain mesh"}</span>`;
};

function assetMatches(a, needle) {
  if (!needle) return true;
  const hay = [a.name, a.brief_id, a.asset_id, a.design_hash, a.quality]
    .filter(Boolean).join(" ").toLowerCase();
  return hay.indexOf(needle) >= 0;
}

function assetSummaryHtml(a) {
  if (!a) {
    return `<p class="hint" role="status">No horn picked yet. Pick one card above; the next step waits for it.</p>`;
  }
  return `<div class="alert info" role="status">
      <b>Picked:</b> ${esc(a.name || a.asset_id)}
      · <span class="mono">${esc(a.asset_id)}</span>
      · brief ${esc(a.brief_id || MISSING)}
      · design hash <span class="mono">${esc(a.design_hash || MISSING)}</span>
      · band ${bandLabel(a)}
      · ${a.full_domain_mesh ? "full-domain mesh available" : "no full-domain mesh"}
    </div>
    ${a.quality === "MAGNITUDE_ONLY"
      ? `<div class="alert warn" role="note">Screen only: no phase or delay claims for this horn.</div>`
      : ""}`;
}

function assetCardHtml(a, selected) {
  return `<label class="hwn-asset${selected ? " is-picked" : ""}" data-asset="${esc(a.asset_id)}">
    <input type="radio" name="hwn-asset" value="${esc(a.asset_id)}"${selected ? " checked" : ""}
      aria-label="Select ${esc(a.name || a.asset_id)}">
    <div class="hwn-asset-body">
      <span class="hwn-name">${esc(a.name || a.asset_id)}</span>
      <div class="pill-row" style="margin:6px 0 0">
        ${qualityPill(a)}
        ${meshPill(a)}
        ${a.quality === "MAGNITUDE_ONLY"
          ? `<span class="pill warn" title="Screen only: no phase or delay claims for a magnitude-only horn.">screen only — no phase/delay</span>`
          : ""}
      </div>
      <dl class="hwn-kv">
        <dt>Brief</dt><dd>${esc(a.brief_id || MISSING)}</dd>
        <dt>Design hash</dt><dd class="mono">${esc(a.design_hash || MISSING)}</dd>
        <dt>Band</dt><dd>${bandLabel(a)}</dd>
        <dt>Asset id</dt><dd class="mono">${esc(a.asset_id)}</dd>
      </dl>
    </div>
  </label>`;
}

function driverFieldTitle(d, key) {
  const src = (d.provenance && d.provenance.field_sources) || {};
  const source = src[key] || "not recorded";
  const file = d.provenance && d.provenance.ts_file ? d.provenance.ts_file : "the T/S file";
  return `${key}: ${source} (${file}, R15)`;
}

function driverSourceLine(d) {
  const src = (d.provenance && d.provenance.field_sources) || {};
  const parts = ["fs_hz", "vas_l", "qts", "sd_cm2", "xmax_mm"]
    .filter(k => src[k]).map(k => `${k} ${src[k]}`);
  const file = d.provenance && d.provenance.ts_file ? d.provenance.ts_file : "no T/S file recorded";
  return `Source: ${file} · ${parts.join(" · ") || "no field-source markers"} (R15).`;
}

function driverCardHtml(d, selected, compact = false) {
  const g = d.geometry || {};
  const missing = Array.isArray(g.missing_fields) ? g.missing_fields : [];
  return `<label class="hwn-driver${selected ? " is-picked" : ""}" data-driver="${esc(d.driver_id)}">
    <input type="checkbox" name="hwn-driver" value="${esc(d.driver_id)}"${selected ? " checked" : ""}
      aria-label="Select ${esc(d.name || d.driver_id)}">
    <div class="hwn-asset-body">
      <span class="hwn-name">${esc(d.name || d.driver_id)}
        <span class="mono muted" style="font-weight:400;font-size:0.74rem">${esc(d.driver_id)}</span></span>
      <div class="pill-row" style="margin:6px 0 0">
        ${d.ts_verified
          ? `<span class="pill good" title="${esc(d.ts_verified_note || "a vendor source URL is recorded")}">T/S verified</span>`
          : `<span class="pill warn" title="${esc(d.ts_verified_note || "no source URL recorded")}">T/S source missing</span>`}
        ${g.complete
          ? `<span class="pill good">real shape present</span>`
          : `<span class="pill warn" title="${esc(g.note || "installed-surface fields are missing")}">${tip("demo_shape", "Real shape")} missing${missing.length ? ` (${missing.length})` : ""}</span>`}
      </div>
      <dl class="hwn-kv">
        <dt>Size</dt><dd title="${esc(driverFieldTitle(d, "size_in"))}">${d.size_in == null ? MISSING : num(d.size_in, 1) + " in"}</dd>
        <dt>Fs</dt><dd title="${esc(driverFieldTitle(d, "fs_hz"))}">${fmtHz(d.fs_hz)}</dd>
        <dt>Vas</dt><dd title="${esc(driverFieldTitle(d, "vas_l"))}">${num(d.vas_l, 1)} L</dd>
        <dt>Qts</dt><dd title="${esc(driverFieldTitle(d, "qts"))}">${num(d.qts, 3)}</dd>
        <dt>Sd</dt><dd title="${esc(driverFieldTitle(d, "sd_cm2"))}">${num(d.sd_cm2, 0)} cm²</dd>
        <dt>Xmax</dt><dd title="${esc(driverFieldTitle(d, "xmax_mm"))}">${num(d.xmax_mm, 2)} mm</dd>
      </dl>
      ${compact ? "" : `<div class="hint" style="font-size:0.74rem">${esc(driverSourceLine(d))}</div>`}
      ${!g.complete && missing.length && !compact
        ? `<div class="hint" style="font-size:0.74rem"><span class="warn-text">Missing installed-surface fields:</span> ${esc(missing.join(", "))}</div>`
        : ""}
    </div>
  </label>`;
}

function driverSummaryHtml(drivers, selected) {
  const picked = (drivers || []).filter(d => selected.has(d.driver_id));
  if (!picked.length) {
    return `<span class="warn-text">⚠ Pick at least one woofer driver.</span>`;
  }
  return `<span class="good-text">✓ ${picked.length} driver${picked.length === 1 ? "" : "s"} picked:</span> `
    + picked.map(d => esc(d.name || d.driver_id)).join(", ");
}

// ════════════════════════════════════════════════════════════════════════════
// New system — guided wizard (#/hw/new)
// ════════════════════════════════════════════════════════════════════════════

export async function viewHwNew(root, query = "") {
  skel(root, "Loading saved horns, drivers and the committed example spec");
  // The newest 40 run dirs answer in about a second. The full 200-run inventory is a
  // user-triggered "Load all" action below (a cold 200 scan takes about 30 s).
  const [aR, dR, defR, spR, jR] = await Promise.allSettled([
    api("/api/hw/assets?limit=40"),
    api("/api/hw/drivers"),
    api("/api/hw/spec-defaults"),
    api("/api/hw/specs"),
    api("/api/jobs"),
  ]);
  busyDone(root);

  if (aR.status !== "fulfilled" || dR.status !== "fulfilled") {
    const msgs = [];
    if (aR.status !== "fulfilled") msgs.push("saved horns: " + aR.reason.message);
    if (dR.status !== "fulfilled") msgs.push("woofer drivers: " + dR.reason.message);
    root.innerHTML = `<div class="stack" style="gap:14px">
      ${errBanner("The wizard could not load its data — " + msgs.join("; "))}
      <div class="btn-row"><a class="btn" href="#/hw/new">Reload</a>
        <a class="btn" href="#/hw/cases">All cases</a></div>
    </div>`;
    return;
  }

  const assetsData = aR.value || {};
  const driversData = dR.value || {};
  let assets = Array.isArray(assetsData.assets) ? assetsData.assets : [];
  const drivers = Array.isArray(driversData.drivers) ? driversData.drivers : [];
  const defaults = defR.status === "fulfilled" ? defR.value : null;
  const defaultsError = defR.status === "rejected" ? defR.reason.message : null;
  const specsData = spR.status === "fulfilled" ? spR.value : null;
  const specsError = spR.status === "rejected" ? spR.reason.message : null;
  const jobs = jR.status === "fulfilled" ? jR.value : [];
  const timing = completedScreenTimes(jobs);

  const q = readQuery(query);
  const examplePath = defaults && defaults.source ? String(defaults.source) : null;
  const baseSpec = defaults && defaults.spec ? defaults.spec : null;

  const knownDrivers = new Set(drivers.map(d => d.driver_id));
  const wantedDrivers = String(q.get("drivers") || "").split(",").filter(Boolean);
  const droppedDrivers = wantedDrivers.filter(id => !knownDrivers.has(id));

  const state = {
    mode: "guided",
    step: Math.min(4, Math.max(1, Math.trunc(Number(q.get("step")) || 1))),
    assetId: String(q.get("asset") || ""),
    drivers: new Set(wantedDrivers.filter(id => knownDrivers.has(id))),
    spec: baseSpec ? JSON.parse(JSON.stringify(baseSpec)) : null,
    baseJson: baseSpec ? JSON.stringify(baseSpec) : null,
    examplePath,
    savedPath: null,
    savedSnapshot: null,
    specPath: examplePath,
    validation: null,
    specs: specsData && Array.isArray(specsData.specs) ? specsData.specs : [],
    specsError,
    specsNotes: specsData && Array.isArray(specsData.notes) ? specsData.notes : [],
    screenSeconds: timing.seconds,
    screenSamples: timing.samples,
    runningHw: (Array.isArray(jobs) ? jobs : []).find(
      j => j && String(j.kind || "").startsWith("hw-") && j.status === "running") || null,
    preview: { busy: false, ok: false, error: null, command: null },
    saving: false,
    saveConfirmOpen: false,
    assetFilter: "",
    assetMeshOnly: false,
    shown: 24,
    assetsFull: false,
    assetsLoadingAll: false,
    assetsError: null,
  };

  // Keep a URL-selected asset even when the fast 40-run page did not load its row:
  // "Load all saved horns" below can still confirm it.

  const selectedAsset = () => assets.find(a => a.asset_id === state.assetId) || null;
  const driverIds = () => drivers.filter(d => state.drivers.has(d.driver_id)).map(d => d.driver_id);

  function selectedSummaryHtml() {
    const sel = selectedAsset();
    if (sel) return assetSummaryHtml(sel);
    if (state.assetId) {
      return `<p class="hint" role="status"><span class="warn-text">Selected asset
        <code>${esc(state.assetId)}</code> is not in the loaded
        ${state.assetsFull ? "newest 200" : "first 40"} run dirs.</span>
        ${state.assetsFull ? "Pick another asset." : "Use “Load all saved horns (slower)” to see it."}</p>`;
    }
    return assetSummaryHtml(null);
  }

  function syncUrl() {
    const p = new URLSearchParams();
    p.set("step", String(state.step));
    if (state.assetId) p.set("asset", state.assetId);
    const ids = driverIds();
    if (ids.length) p.set("drivers", ids.join(","));
    writeRoute(ROUTE_NEW, p);
  }

  ensureStyles();
  const pills = [
    `<span class="pill">CPU · no GPU</span>`,
    `<span class="pill">${tip("hw_screen", "screen")} estimate · no winner</span>`,
  ].join("");
  root.innerHTML = `<div id="hw-new-view" class="stack" style="gap:18px">
    ${pageHead({
      eyebrow: "Horn + woofer · New system",
      title: "New system",
      id: `guided · step ${state.step} of 4`,
      pills,
    })}
    ${modeSwitchHtml("guided")}
    <p class="lede" style="max-width:76ch;margin:0">Design a two-way: a saved horn over a vented woofer.
      Steps 1–3 set the horn, drivers and box; step 4 runs the fast CPU screen. Nothing is solved here.</p>
    <div id="hwn-stepper">${stepperHtml(state.step)}</div>
    <div id="hwn-asset-missing"></div>
    ${droppedDrivers.length ? `<div class="alert warn" role="status">Ignored driver id(s) not in the
      catalog: ${esc(droppedDrivers.join(", "))}.</div>` : ""}
    ${defaultsError ? errBanner(`The committed example spec could not be loaded: ${defaultsError}`) : ""}
    <div id="hwn-step-body"></div>
  </div>`;

  const stepBody = root.querySelector("#hwn-step-body");
  const stepper = root.querySelector("#hwn-stepper");

  function updateAssetLoadUi() {
    const sel = selectedAsset();
    const btn = stepBody.querySelector("#hwn-load-all");
    const note = stepBody.querySelector("#hwn-load-all-note");
    const warn = root.querySelector("#hwn-asset-missing");
    if (btn) {
      btn.disabled = state.assetsLoadingAll || state.assetsFull;
      btn.textContent = state.assetsFull ? "All saved horns loaded"
        : state.assetsLoadingAll ? "Loading all saved horns…" : "Load all saved horns (slower)";
    }
    if (note) {
      note.innerHTML = state.assetsLoadingAll
        ? "Loading all saved horns… this can take about 30 seconds. The current list and your selection stay."
        : state.assetsError
          ? `<span class="warn-text">⚠ Could not load all saved horns: ${esc(state.assetsError)}</span>`
          : state.assetsFull
            ? "All saved horns are loaded (newest 200 run dirs)."
            : "The first page loads the newest 40 run dirs quickly. Load all for older designs such as 0062fb59fbf63eae (about 30 seconds).";
    }
    if (warn) {
      if (!state.assetId || sel) warn.innerHTML = "";
      else if (state.assetsLoadingAll) {
        warn.innerHTML = `<div class="alert info" role="status">Loading all saved horns to find the
          selected asset <code>${esc(state.assetId)}</code>…</div>`;
      } else {
        warn.innerHTML = `<div class="alert warn" role="status">The selected asset
          <code>${esc(state.assetId)}</code> is not in the ${state.assetsFull ? "newest 200" : "first 40"}
          saved-horn runs. ${state.assetsFull ? "Pick another asset." : "Use “Load all saved horns (slower)” in step 1 to find it."}</div>`;
      }
    }
  }

  async function loadAllAssets() {
    if (state.assetsLoadingAll || state.assetsFull) return;
    state.assetsLoadingAll = true;
    state.assetsError = null;
    updateAssetLoadUi();
    let data;
    try {
      data = await api("/api/hw/assets?limit=200");
    } catch (e) {
      state.assetsLoadingAll = false;
      state.assetsError = e.message;
      updateAssetLoadUi();
      return;
    }
    state.assetsLoadingAll = false;
    if (!stepBody.isConnected) return;
    assets = Array.isArray(data.assets) ? data.assets : assets;
    state.assetsFull = true;
    state.assetsError = null;
    if (state.step === 1) {
      renderStep1();
      const q = stepBody.querySelector("#hwn-asset-q");
      if (q) q.focus();
    } else {
      updateAssetLoadUi();
    }
  }

  // ── Esc: close the newest disclosure and return focus to its opener ───────
  root.addEventListener("keydown", e => {
    if (e.key !== "Escape") return;
    const confirm = root.querySelector("[data-hw-disclosure]:not([hidden])");
    if (confirm) {
      e.preventDefault();
      const opener = confirm._hwOpener;
      confirm.hidden = true;
      state.saveConfirmOpen = false;
      if (opener && opener.isConnected) opener.focus();
      if (state.step === 3) updateGate3();
      return;
    }
    const open = [...root.querySelectorAll("details[open]")].filter(d => root.contains(d));
    if (open.length) {
      e.preventDefault();
      const d = open[open.length - 1];
      d.open = false;
      const s = d.querySelector("summary");
      if (s) s.focus();
    }
  });

  // ── Mode switch ───────────────────────────────────────────────────────────
  root.querySelectorAll(".hwn-mode").forEach(btn => btn.addEventListener("click", () => {
    if (btn.dataset.mode === "guided") return;
    const p = new URLSearchParams();
    if (state.specPath) p.set("spec", state.specPath);
    if (state.assetId) p.set("asset", state.assetId);
    const ids = driverIds();
    if (ids.length) p.set("drivers", ids.join(","));
    location.hash = ROUTE_LAUNCH + (p.toString() ? "?" + p.toString() : "");
  }));

  function wireStepper() {
    stepper.querySelectorAll("[data-step]").forEach(btn => btn.addEventListener("click", () => {
      const n = Number(btn.dataset.step);
      if (!n || n === state.step) return;
      state.step = n;
      syncUrl();
      renderStep();
    }));
  }
  wireStepper();

  // ── Step rendering ────────────────────────────────────────────────────────
  function renderStep(focusHead = true) {
    const head = root.querySelector("#hwn-head-id");
    if (head) head.innerHTML = brk(`guided · step ${state.step} of 4`);
    stepper.innerHTML = stepperHtml(state.step);
    wireStepper();
    if (state.step === 1) renderStep1();
    else if (state.step === 2) renderStep2();
    else if (state.step === 3) renderStep3();
    else renderStep4();
    updateAssetLoadUi();
    if (focusHead) {
      const h = stepBody.querySelector("h3[tabindex='-1']");
      if (h) h.focus();
    }
  }

  function goStep(n) {
    state.step = n;
    syncUrl();
    renderStep();
  }

  // ── Step 1: pick a horn ───────────────────────────────────────────────────
  function renderStep1() {
    const page = 24;
    state.shown = state.shown || page;
    stepBody.innerHTML = `<section class="card stack" style="gap:12px">
      <h3 tabindex="-1" style="margin:0">1 · Pick a horn</h3>
      <p class="hint" role="status">Pick one saved horn design. The screen reads its stored response —
        nothing is re-meshed. A magnitude-only horn is allowed for a screen; it carries no phase or
        delay claims.</p>
      <div class="hwn-filter">
        <input id="hwn-asset-q" type="search" value="${esc(state.assetFilter || "")}"
          placeholder="Search name, brief, design hash or asset id" aria-label="Search saved horns">
        <label class="hwn-toggle"><input id="hwn-asset-mesh" type="checkbox"${state.assetMeshOnly ? " checked" : ""}>
          Has full-domain mesh</label>
      </div>
      <div class="hwn-actions">
        <button type="button" class="btn" id="hwn-load-all">Load all saved horns (slower)</button>
        <span class="hint" role="status" id="hwn-load-all-note"></span>
      </div>
      <div id="hwn-asset-summary"></div>
      <div class="hint" role="status" id="hwn-asset-count"></div>
      <div class="hwn-grid" id="hwn-assets" role="radiogroup" aria-label="Saved horns"></div>
      <div class="hwn-actions">
        <button type="button" class="btn" id="hwn-more">Show more</button>
        <span class="hint" role="status" id="hwn-more-note"></span>
      </div>
      <div class="hwn-actions">
        <button type="button" class="primary" id="hwn-next">Next: woofer drivers →</button>
        <span class="hint" role="status" id="hwn-next-why"></span>
      </div>
    </section>`;

    const grid = stepBody.querySelector("#hwn-assets");
    const count = stepBody.querySelector("#hwn-asset-count");
    const more = stepBody.querySelector("#hwn-more");
    const moreNote = stepBody.querySelector("#hwn-more-note");
    const summary = stepBody.querySelector("#hwn-asset-summary");
    const next = stepBody.querySelector("#hwn-next");
    const why = stepBody.querySelector("#hwn-next-why");

    function filtered() {
      const needle = String(state.assetFilter || "").trim().toLowerCase();
      return assets.filter(a => (!state.assetMeshOnly || a.full_domain_mesh) && assetMatches(a, needle));
    }
    function updateNext() {
      const sel = selectedAsset();
      if (sel) {
        next.disabled = false;
        next.title = "";
        why.innerHTML = `<span class="good-text">✓ Horn picked.</span>`;
      } else if (state.assetId) {
        next.disabled = true;
        next.title = "Load all saved horns to confirm the selected asset.";
        why.innerHTML = `<span class="warn-text">⚠ Selected asset
          <code>${esc(state.assetId)}</code> is not loaded — use “Load all saved horns (slower)”.</span>`;
      } else {
        next.disabled = true;
        next.title = "Pick a horn in step 1.";
        why.innerHTML = `<span class="warn-text">⚠ Pick a horn to continue.</span>`;
      }
    }
    function renderGrid() {
      const list = filtered();
      const shown = Math.max(page, state.shown || page);
      let slice = list.slice(0, shown);
      const sel = selectedAsset();
      if (sel && !slice.some(a => a.asset_id === sel.asset_id)) slice = [sel, ...slice];
      grid.innerHTML = slice.length
        ? slice.map(a => assetCardHtml(a, a.asset_id === state.assetId)).join("")
        : `<p class="hint" role="status">No saved horn matches this filter.</p>`;
      count.textContent = `Showing ${slice.length} of ${list.length} match${list.length === 1 ? "" : "es"}`
        + ` (${assets.length} asset${assets.length === 1 ? "" : "s"} loaded from the newest `
        + `${state.assetsFull ? 200 : 40} run dirs).`;
      const moreLeft = Math.max(0, list.length - shown);
      more.hidden = moreLeft === 0;
      moreNote.textContent = moreLeft ? `${moreLeft} more match${moreLeft === 1 ? "" : "es"}.` : "";
      summary.innerHTML = selectedSummaryHtml();
      updateNext();
      updateAssetLoadUi();
    }
    renderGrid();
    stepBody.querySelector("#hwn-asset-q").addEventListener("input", e => {
      state.assetFilter = e.target.value;
      state.shown = page;
      renderGrid();
    });
    stepBody.querySelector("#hwn-asset-mesh").addEventListener("change", e => {
      state.assetMeshOnly = !!e.target.checked;
      state.shown = page;
      renderGrid();
    });
    grid.addEventListener("change", e => {
      if (!e.target || e.target.name !== "hwn-asset") return;
      state.assetId = String(e.target.value || "");
      syncUrl();
      grid.querySelectorAll(".hwn-asset").forEach(el => {
        el.classList.toggle("is-picked", el.dataset.asset === state.assetId);
      });
      summary.innerHTML = selectedSummaryHtml();
      updateNext();
      updateAssetLoadUi();
    });
    more.addEventListener("click", () => {
      state.shown = (state.shown || page) + page;
      renderGrid();
    });
    stepBody.querySelector("#hwn-load-all").addEventListener("click", loadAllAssets);
    next.addEventListener("click", () => { if (!next.disabled) goStep(2); });
  }

  // ── Step 2: pick woofer drivers ───────────────────────────────────────────
  function renderStep2() {
    stepBody.innerHTML = `<section class="card stack" style="gap:12px">
      <h3 tabindex="-1" style="margin:0">2 · Pick woofer drivers</h3>
      <p class="hint" role="status">Pick at least one. Every number is the driver file's own value;
        the chips say whether a vendor source URL is recorded and whether the installed-surface
        fields are complete. Hover a number for its source and the R15 vendor/derived marker.</p>
      <div class="hwn-drivers" id="hwn-drivers" role="group" aria-label="Woofer drivers">
        ${drivers.length
          ? drivers.map(d => driverCardHtml(d, state.drivers.has(d.driver_id))).join("")
          : `<div class="alert warn" role="status">No driver T/S files were found in
             <code>examples/systems/driver_ts/</code>. Add a sourced driver YAML and reload.</div>`}
      </div>
      <div class="hint" role="status" id="hwn-driver-count">${driverSummaryHtml(drivers, state.drivers)}</div>
      <div class="hwn-actions">
        <button type="button" class="btn" id="hwn-back">← Back</button>
        <button type="button" class="primary" id="hwn-next">Next: box limits and targets →</button>
        <span class="hint" role="status" id="hwn-next-why"></span>
      </div>
    </section>`;

    const count = stepBody.querySelector("#hwn-driver-count");
    const next = stepBody.querySelector("#hwn-next");
    const why = stepBody.querySelector("#hwn-next-why");

    function update() {
      const n = state.drivers.size;
      count.innerHTML = driverSummaryHtml(drivers, state.drivers);
      next.disabled = n === 0 || drivers.length === 0;
      next.title = next.disabled ? "Pick at least one woofer driver." : "";
      why.innerHTML = next.disabled
        ? `<span class="warn-text">⚠ Pick at least one woofer driver to continue.</span>`
        : `<span class="good-text">✓ ${n} driver${n === 1 ? "" : "s"} picked.</span>`;
    }
    update();
    stepBody.querySelectorAll('input[name="hwn-driver"]').forEach(inp => {
      inp.addEventListener("change", () => {
        const id = String(inp.value || "");
        if (inp.checked) state.drivers.add(id); else state.drivers.delete(id);
        const card = inp.closest(".hwn-driver");
        if (card) card.classList.toggle("is-picked", !!inp.checked);
        syncUrl();
        update();
      });
    });
    stepBody.querySelector("#hwn-back").addEventListener("click", () => goStep(1));
    next.addEventListener("click", () => { if (!next.disabled) goStep(3); });
  }

  // ── Step 3 data: the frozen contract's own field names ────────────────────
  const SPEC_RANGES = [
    { group: "cabinet", key: "external_width_mm_range", label: "Width", unit: "mm", step: "1",
      help: "Search bound for the external width — not a claimed enclosure size." },
    { group: "cabinet", key: "external_height_mm_range", label: "Height", unit: "mm", step: "1",
      help: "Search bound for the external height." },
    { group: "cabinet", key: "external_depth_mm_range", label: "Depth", unit: "mm", step: "1",
      help: "Search bound for the external depth." },
    { group: "cabinet", key: "net_volume_l_range", label: "Net volume", unit: "L", step: "0.1",
      help: "Search bound for the net internal volume." },
    { group: "cabinet", key: "tuning_hz_range", label: "Tuning", unit: "Hz", step: "0.1", tip: "fb_tuning",
      help: "Requested tuning range; the port geometry decides the actual Fb." },
    { group: "cabinet", key: "port_throat_area_cm2_range", label: "Port area", unit: "cm²", step: "1",
      help: "Search bound for the port throat area." },
    { group: "cabinet", key: "port_nfr_range", label: "Port flare (NFR)", unit: "ratio", step: "0.01",
      help: "NFR search range. The LF screen carries it but records nfr_ignored_at_lf_tier." },
    { group: "target", key: "beamwidth_h_deg", label: "Coverage H", unit: "°", step: "1",
      help: "Target horizontal coverage range the screen reports against; not a promise." },
    { group: "target", key: "beamwidth_v_deg", label: "Coverage V", unit: "°", step: "1",
      help: "Target vertical coverage range the screen reports against; not a promise." },
    { group: "target", key: "listening_angle_h_deg", label: "Listening window H", unit: "°", step: "1",
      help: "Horizontal listening window the screen reports against." },
    { group: "target", key: "listening_angle_v_deg", label: "Listening window V", unit: "°", step: "1",
      help: "Vertical listening window the screen reports against." },
    { group: "assembly", key: "woofer_center_y_mm_range", label: "Woofer centre Y", unit: "mm", step: "1",
      help: "Vertical placement range on the front baffle." },
    { group: "assembly", key: "horn_mounting_offset_z_mm_range", label: "Horn offset Z", unit: "mm", step: "1",
      help: "Horn mounting offset range." },
  ];
  const SPEC_SINGLES = [
    { group: "cabinet", key: "wall_mm", label: "Wall thickness", unit: "mm", step: "0.1",
      help: "Wall thickness used by the box and panel checks." },
    { group: "target", key: "low_freq_f3_hz_max", label: "F3 max", unit: "Hz", step: "0.1", tip: "f3",
      help: "The spec's own F3 gate; the screen compares each box against it." },
  ];
  const SPEC_SELECTS = [
    { group: "cabinet", key: "port_type", label: "Port type",
      help: "The LF screen treats round flared and round straight as an area-equivalent round port.",
      options: [["round_flared", "Round, flared"], ["round_straight", "Round, straight"], ["slot", "Slot"]] },
    { group: "assembly", key: "horn_layout", label: "Horn layout",
      help: "How the horn sits on the enclosure.",
      options: [["separate_above", "Separate, above"], ["separate_side_baffle", "Separate, side baffle"],
                ["flush_baffle", "Flush baffle"]] },
  ];
  const SPEC_X_RANGE = { group: "assembly", key: "woofer_center_x_mm_range", label: "Woofer centre X",
    unit: "mm", step: "1", help: "Horizontal placement range (advanced)." };

  const fieldSlug = f => `${f.group}-${f.key}`.replace(/[^A-Za-z0-9_-]+/g, "-");
  const groupPath = f => f.group + "." + f.key;
  const specVal = f => (state.spec && state.spec[f.group]) ? state.spec[f.group][f.key] : null;

  function rangeFieldHtml(f) {
    const v = specVal(f);
    const pair = Array.isArray(v) ? v : [null, null];
    const slug = fieldSlug(f);
    const field = groupPath(f);
    const hint = `hwn-h-${slug}`;
    const err = `hwn-e-${slug}`;
    const label = f.tip ? tip(f.tip, f.label) : esc(f.label);
    return `<label for="hwn-f-${slug}-0">${label} (${esc(f.unit)})</label>
      <div class="hwn-field" data-field-group="${esc(field)}">
        <div class="hwn-range">
          <input id="hwn-f-${slug}-0" type="number" step="${esc(f.step)}" data-spec="${esc(field)}"
            data-end="0" value="${esc(inputValue(pair[0]))}" aria-describedby="${hint} ${err}">
          <span aria-hidden="true">to</span>
          <input id="hwn-f-${slug}-1" type="number" step="${esc(f.step)}" data-spec="${esc(field)}"
            data-end="1" value="${esc(inputValue(pair[1]))}" aria-describedby="${hint} ${err}"
            aria-label="${esc(f.label)} maximum (${esc(f.unit)})">
        </div>
        <div class="hint" role="status" id="${hint}">${esc(f.help)}</div>
        <div id="${err}" data-error-for="${esc(field)}"></div>
      </div>`;
  }

  function singleFieldHtml(f) {
    const slug = fieldSlug(f);
    const field = groupPath(f);
    const hint = `hwn-h-${slug}`;
    const err = `hwn-e-${slug}`;
    const label = f.tip ? tip(f.tip, f.label) : esc(f.label);
    return `<label for="hwn-f-${slug}">${label} (${esc(f.unit)})</label>
      <div class="hwn-field" data-field-group="${esc(field)}">
        <input id="hwn-f-${slug}" type="number" step="${esc(f.step)}" data-spec="${esc(field)}"
          value="${esc(inputValue(specVal(f)))}" aria-describedby="${hint} ${err}">
        <div class="hint" role="status" id="${hint}">${esc(f.help)}</div>
        <div id="${err}" data-error-for="${esc(field)}"></div>
      </div>`;
  }

  function selectFieldHtml(f) {
    const slug = fieldSlug(f);
    const field = groupPath(f);
    const hint = `hwn-h-${slug}`;
    const err = `hwn-e-${slug}`;
    const cur = specVal(f);
    return `<label for="hwn-f-${slug}">${esc(f.label)}</label>
      <div class="hwn-field" data-field-group="${esc(field)}">
        <select id="hwn-f-${slug}" data-spec="${esc(field)}" aria-describedby="${hint} ${err}">
          ${f.options.map(([val, text]) =>
            `<option value="${esc(val)}"${String(cur) === val ? " selected" : ""}>${esc(text)}</option>`).join("")}
        </select>
        <div class="hint" role="status" id="${hint}">${esc(f.help)}</div>
        <div id="${err}" data-error-for="${esc(field)}"></div>
      </div>`;
  }

  function readForm(card) {
    if (!state.spec) return;
    card.querySelectorAll("[data-spec]").forEach(el => {
      const bits = String(el.dataset.spec || "").split(".");
      if (bits.length !== 2) return;
      const group = bits[0], key = bits[1];
      if (!state.spec[group]) return;
      if (el.dataset.end != null && el.dataset.end !== "") {
        const cur = Array.isArray(state.spec[group][key]) ? state.spec[group][key] : [null, null];
        const next = [cur[0] == null ? null : cur[0], cur[1] == null ? null : cur[1]];
        next[Number(el.dataset.end)] = readNum(el);
        state.spec[group][key] = next;
      } else if (el.tagName === "SELECT") {
        state.spec[group][key] = String(el.value);
      } else {
        state.spec[group][key] = readNum(el);
      }
    });
  }

  function recomputeSpecPath() {
    if (!state.spec) { state.specPath = null; return; }
    const json = JSON.stringify(state.spec);
    if (state.savedPath && state.savedSnapshot && json === state.savedSnapshot) state.specPath = state.savedPath;
    else if (state.examplePath && state.baseJson && json === state.baseJson) state.specPath = state.examplePath;
    else state.specPath = null;
  }

  function sourceLineHtml() {
    if (!state.spec) {
      return `<div class="alert error" role="alert">The example spec is unavailable, so the box
        limits cannot be edited on this page.</div>`;
    }
    if (state.specPath && state.examplePath && state.specPath === state.examplePath) {
      return `<p class="hint" role="status">Source: the committed example
        <code>${esc(state.examplePath)}</code> (read-only). The screen can use it as-is.</p>`;
    }
    if (state.specPath) {
      return `<p class="hint" role="status">Source: the saved file
        <code>${esc(state.specPath)}</code>.</p>`;
    }
    return `<p class="hint" role="status"><span class="warn-text">⚠ Unsaved edits.</span>
      The screen only runs a real file — use “Save as…” below before screening.</p>`;
  }
  function updateSourceLine() {
    const host = stepBody.querySelector("#hwn-spec-source");
    if (host) host.innerHTML = sourceLineHtml();
  }

  let validateTimer = null;
  let validateSeq = 0;
  function scheduleValidate(delay = 250) {
    clearTimeout(validateTimer);
    validateSeq += 1;                  // invalidate any in-flight verdict for the old form
    const sum = stepBody.querySelector("#hwn-val-summary");
    if (sum) sum.innerHTML = `<span class="muted">Checking the spec…</span>`;
    validateTimer = setTimeout(runValidate, delay);
  }
  async function runValidate() {
    if (state.step !== 3 || !state.spec || !stepBody.isConnected) return;
    if (!stepBody.querySelector("#hwn-spec-card")) return;
    const seq = ++validateSeq;
    let res;
    try {
      res = await apiPost("/api/hw/spec/validate", { spec: state.spec });
    } catch (e) {
      if (seq !== validateSeq || state.step !== 3 || !stepBody.isConnected) return;
      state.validation = { ok: false, errors: [], transportError: e.message };
      const sum = stepBody.querySelector("#hwn-val-summary");
      if (sum) sum.innerHTML = errBanner("Could not validate the spec: " + e.message);
      updateGate3();
      return;
    }
    if (seq !== validateSeq || state.step !== 3 || !stepBody.isConnected) return;
    state.validation = res && typeof res === "object" ? res : { ok: false, errors: [] };
    applyValidation(state.validation);
    updateGate3();
  }

  function applyValidation(res) {
    const card = stepBody.querySelector("#hwn-spec-card");
    if (!card) return;
    card.querySelectorAll("[data-error-for]").forEach(el => { el.innerHTML = ""; });
    card.querySelectorAll('[aria-invalid="true"]').forEach(el => el.removeAttribute("aria-invalid"));
    const errors = Array.isArray(res.errors) ? res.errors : [];
    const unmatched = [];
    for (const err of errors) {
      const field = err && err.field;
      const group = [...card.querySelectorAll("[data-field-group]")]
        .find(g => fieldMatches(g.dataset.fieldGroup, field));
      if (!group) { unmatched.push(err); continue; }
      const slot = group.querySelector("[data-error-for]");
      if (slot) slot.innerHTML = `<div class="alert error" role="alert">${esc(err.message || "invalid value")}</div>`;
      group.querySelectorAll("input,select").forEach(el => el.setAttribute("aria-invalid", "true"));
      const details = group.closest("details");
      if (details && !details.open) details.open = true;
    }
    const sum = card.querySelector("#hwn-val-summary");
    if (sum) {
      if (res.ok) sum.innerHTML = `<span class="good-text">✓ Spec is valid.</span>`;
      else if (unmatched.length) {
        sum.innerHTML = `<div class="alert error" role="alert"><b>Spec error:</b>
          ${unmatched.map(e => esc(e.message || "invalid value")).join("<br>")}</div>`;
      } else {
        sum.innerHTML = `<span class="warn-text">⚠ Fix the highlighted field${errors.length === 1 ? "" : "s"}.</span>`;
      }
    }
  }

  function currentSaveName() {
    const el = stepBody.querySelector("#hwn-save-name");
    return el ? String(el.value || "").trim() : "";
  }

  function updateGate3() {
    const card = stepBody.querySelector("#hwn-spec-card");
    if (!card || !state.spec) return;
    const valid = !!(state.validation && state.validation.ok);
    const name = currentSaveName();
    const nameOk = isValidName(name);
    const saveBtn = card.querySelector("#hwn-save");
    const saveWhy = card.querySelector("#hwn-save-why");
    if (saveBtn) {
      const why = !state.validation ? "Waiting for the spec check."
        : !valid ? "Fix the spec field errors first."
        : !name ? "Type a name for the file."
        : !nameOk ? "Use letters, digits, _ . - and no path."
        : state.saving ? "Saving…"
        : state.saveConfirmOpen ? "Confirm or cancel the replacement below."
        : null;
      saveBtn.disabled = !!why;
      saveBtn.title = why || "";
      if (saveWhy) {
        saveWhy.innerHTML = why
          ? `<span class="warn-text">⚠ ${esc(why)}</span>`
          : `<span class="good-text">✓ Ready to save.</span>`;
      }
    }
    const nextBtn = card.querySelector("#hwn-next");
    const nextWhy = card.querySelector("#hwn-next-why");
    if (nextBtn) {
      const reasons = [];
      if (!state.validation) reasons.push("the spec check has not finished");
      else if (!valid) reasons.push("the spec is not valid");
      if (!state.specPath) reasons.push("save the spec first — the screen runs a real file");
      nextBtn.disabled = reasons.length > 0;
      nextBtn.title = reasons.length ? reasons.join("; ") : "";
      if (nextWhy) {
        nextWhy.innerHTML = reasons.length
          ? `<span class="warn-text">⚠ ${esc(reasons.join("; "))}.</span>`
          : `<span class="good-text">✓ Spec valid and ready.</span>`;
      }
    }
  }

  function renderSpecsList() {
    const host = stepBody.querySelector("#hwn-specs-list");
    if (!host) return;
    if (state.specsError) {
      host.innerHTML = errBanner("Could not read the saved specs: " + state.specsError);
      return;
    }
    const rows = Array.isArray(state.specs) ? state.specs : [];
    const note = (state.specsNotes && state.specsNotes.length)
      ? `<p class="hint" role="status">${esc(state.specsNotes.join(" · "))}</p>` : "";
    if (!rows.length) {
      host.innerHTML = `<p class="hint" role="status">No saved specs yet. “Save as…” puts one under
        <code>examples/systems/user/</code>.</p>${note}`;
      return;
    }
    host.innerHTML = rows.map(s => `<div class="hwn-spec-row">
      <b>${esc(s.name)}</b>
      <span class="pill ${s.ok ? "good" : "bad"}">${s.ok ? "valid" : "invalid"}</span>
      <span class="mono muted">${esc(s.path || "")}</span>
      ${s.experiment_id ? `<span class="muted">experiment: <code>${esc(s.experiment_id)}</code></span>` : ""}
      ${s.ok ? `<a href="#/hw/launch?spec=${encodeURIComponent(s.path || "")}">Quick launch this spec →</a>` : ""}
      ${!s.ok && s.error
        ? `<div class="alert error" role="alert" style="flex-basis:100%">${esc(s.error)}</div>` : ""}
    </div>`).join("") + note;
  }

  async function refreshSpecs() {
    try {
      const sp = await api("/api/hw/specs");
      if (!stepBody.isConnected) return;
      state.specs = sp && Array.isArray(sp.specs) ? sp.specs : [];
      state.specsError = null;
      state.specsNotes = sp && Array.isArray(sp.notes) ? sp.notes : [];
    } catch (e) {
      if (!stepBody.isConnected) return;
      state.specsError = e.message;
    }
    renderSpecsList();
  }

  function showReplaceConfirm(name) {
    const host = stepBody.querySelector("#hwn-save-confirm");
    const saveBtn = stepBody.querySelector("#hwn-save");
    if (!host) return;
    const existing = (state.specs || []).find(s => s.name === name);
    const path = (existing && existing.path) || `examples/systems/user/${name}.yaml`;
    host.innerHTML = `<div class="alert warn" data-hw-disclosure role="alert">
      <p style="margin:0 0 8px"><b>Replace <code>${esc(path)}</code>?</b>
        The existing file is overwritten with the values above.</p>
      <div class="btn-row">
        <button type="button" class="primary" id="hwn-replace">Replace</button>
        <button type="button" class="btn" id="hwn-cancel-replace">Cancel</button>
      </div>
    </div>`;
    state.saveConfirmOpen = true;
    const panel = host.querySelector("[data-hw-disclosure]");
    if (panel) panel._hwOpener = saveBtn || null;
    updateGate3();
    const replaceBtn = host.querySelector("#hwn-replace");
    if (replaceBtn) replaceBtn.focus();
    host.querySelector("#hwn-cancel-replace").addEventListener("click", closeReplaceConfirm);
    if (replaceBtn) {
      replaceBtn.addEventListener("click", () => {
        // Use the name the confirmation was shown for, even if the field changed meanwhile.
        closeReplaceConfirm(false);
        doSave(true, name);
      });
    }
  }

  function closeReplaceConfirm(refocus = true) {
    const host = stepBody.querySelector("#hwn-save-confirm");
    if (host) host.innerHTML = "";
    state.saveConfirmOpen = false;
    updateGate3();
    if (refocus) {
      const saveBtn = stepBody.querySelector("#hwn-save");
      if (saveBtn) saveBtn.focus();
    }
  }

  async function doSave(replace, nameOverride = "") {
    const name = nameOverride || currentSaveName();
    const errHost = stepBody.querySelector("#hwn-save-error");
    if (!state.spec || !isValidName(name)) return;
    const specAtSave = JSON.stringify(state.spec);
    state.saving = true;
    updateGate3();
    let res;
    try {
      res = await apiPost("/api/hw/spec/save", { name, spec: state.spec, replace: !!replace });
    } catch (e) {
      state.saving = false;
      if (!stepBody.isConnected) return;
      if (!replace && /already exists/i.test(e.message)) {
        showReplaceConfirm(name);
      } else if (errHost) {
        errHost.innerHTML = errBanner(e.message);
      }
      updateGate3();
      return;
    }
    state.saving = false;
    if (!stepBody.isConnected) return;
    const path = typeof res === "string" ? res
      : (res && typeof res.path === "string" ? res.path : null);
    if (!path) {
      if (errHost) errHost.innerHTML = errBanner("The server did not return the saved path.");
      updateGate3();
      return;
    }
    state.savedPath = path;
    state.savedSnapshot = specAtSave;
    recomputeSpecPath();
    state.saveConfirmOpen = false;
    const host = stepBody.querySelector("#hwn-save-confirm");
    if (host) host.innerHTML = "";
    if (errHost) {
      errHost.innerHTML = `<div class="alert info" role="status">Saved to
        <code>${esc(path)}</code>. The screen will use this file.</div>`;
    }
    updateSourceLine();
    updateGate3();
    refreshSpecs();
  }

  // ── Step 3: box limits and targets ────────────────────────────────────────
  function renderStep3() {
    state.saving = false;
    state.saveConfirmOpen = false;
    if (!state.spec) {
      stepBody.innerHTML = `<section class="card stack" style="gap:12px">
        <h3 tabindex="-1" style="margin:0">3 · Box limits and targets</h3>
        ${errBanner("The committed example spec is unavailable, so this step cannot start.")}
        <div class="hwn-actions"><button type="button" class="btn" id="hwn-back">← Back</button></div>
      </section>`;
      stepBody.querySelector("#hwn-back").addEventListener("click", () => goStep(2));
      return;
    }

    const dsp = state.spec.dsp || {};
    const hornRef = state.spec.horn || {};
    const wooferRef = state.spec.woofer || {};
    const pair = (v, unit = "") => Array.isArray(v) && v.length >= 2
      ? `${rangeVal(v[0])}–${rangeVal(v[1])}${unit ? " " + unit : ""}` : MISSING;
    const dspTypes = Array.isArray(dsp.crossover_types) ? dsp.crossover_types.join(", ") : MISSING;

    stepBody.innerHTML = `<section class="card stack" id="hwn-spec-card" style="gap:12px">
      <h3 tabindex="-1" style="margin:0">3 · Box limits and targets</h3>
      <p class="hint" role="status">Every range is a search bound, not a claimed optimum. Defaults come
        from the committed example below; every field is checked by the frozen contract parser as you
        type, and its own message is shown next to the field.</p>
      <div id="hwn-spec-source"></div>
      <div class="form-grid" id="hwn-spec-form">
        ${SPEC_RANGES.map(rangeFieldHtml).join("")}
        ${SPEC_SINGLES.map(singleFieldHtml).join("")}
        ${SPEC_SELECTS.map(selectFieldHtml).join("")}
      </div>
      <div class="hint" role="status" id="hwn-val-summary"></div>

      <details class="hwn-adv">
        <summary>Advanced — horizontal placement, experiment id and DSP ranges</summary>
        <div class="form-grid" style="margin-top:10px">${rangeFieldHtml(SPEC_X_RANGE)}</div>
        <dl class="hwn-summary" style="margin-top:10px">
          <dt>Experiment id</dt><dd><code>${esc(state.spec.experiment_id || MISSING)}</code></dd>
          <dt>${tip("hw_fidelity", "Fidelity")}</dt><dd>${esc(state.spec.fidelity || MISSING)}</dd>
          <dt>Horn ref</dt><dd class="mono">${esc(hornRef.asset_id || MISSING)}</dd>
          <dt>Woofer ref</dt><dd class="mono">${esc(wooferRef.driver_id || MISSING)}</dd>
          <dt>XO range</dt><dd>${pair(dsp.xo_hz_range, "Hz")} · ${esc(dspTypes)}</dd>
          <dt>PEQ bands</dt><dd>${dsp.peq_max_bands == null ? MISSING : esc(dsp.peq_max_bands)}</dd>
        </dl>
        <p class="hint" role="status">These stay at the committed spec's own values. The screen takes
          the horn and drivers from steps 1–2; the crossover is locked until a
          ${tip("calibration_policy", "calibration policy")} is set (owner decision 3).</p>
      </details>

      <div class="card" style="background:var(--bg)">
        <div class="eyebrow" style="margin-bottom:6px">Save this spec</div>
        <div class="hwn-save-row">
          <input id="hwn-save-name" type="text" maxlength="121" aria-label="Spec file name"
            placeholder="${esc(state.spec.experiment_id || "my_system")}_mine">
          <button type="button" class="btn" id="hwn-save">Save as…</button>
          <span class="hint" role="status" id="hwn-save-why"></span>
        </div>
        <p class="hint" role="status">Names use letters, digits, _ . - and must not contain a path.
          Saves under <code>examples/systems/user/</code>.</p>
        <div id="hwn-save-error"></div>
        <div id="hwn-save-confirm"></div>
      </div>

      <div class="card">
        <div class="fig-head"><h3 style="margin:0;font-size:1rem">Saved specs</h3>
          <span class="muted" style="font-size:0.78rem">examples/systems/user/</span></div>
        <div class="hwn-specs" id="hwn-specs-list"></div>
      </div>

      <div class="hwn-actions">
        <button type="button" class="btn" id="hwn-back">← Back</button>
        <button type="button" class="primary" id="hwn-next">Next: review the screen →</button>
        <span class="hint" role="status" id="hwn-next-why"></span>
      </div>
    </section>`;

    const card = stepBody.querySelector("#hwn-spec-card");
    const nameInput = stepBody.querySelector("#hwn-save-name");
    const saveBtn = stepBody.querySelector("#hwn-save");
    const nextBtn = stepBody.querySelector("#hwn-next");

    const onEdit = e => {
      if (!e.target || !e.target.matches("[data-spec]")) return;
      readForm(card);
      recomputeSpecPath();
      state.validation = null;
      updateSourceLine();
      updateGate3();
      scheduleValidate();
    };
    card.addEventListener("input", onEdit);
    card.addEventListener("change", onEdit);
    nameInput.addEventListener("input", updateGate3);
    saveBtn.addEventListener("click", () => {
      const name = currentSaveName();
      const errHost = stepBody.querySelector("#hwn-save-error");
      if (errHost) errHost.innerHTML = "";
      if (!isValidName(name)) {
        if (errHost) errHost.innerHTML = errBanner("Use letters, digits, _ . - and no path; start with a letter or digit.");
        return;
      }
      if ((state.specs || []).some(s => s.name === name)) {
        showReplaceConfirm(name);
        return;
      }
      doSave(false);
    });
    stepBody.querySelector("#hwn-back").addEventListener("click", () => goStep(2));
    nextBtn.addEventListener("click", () => { if (!nextBtn.disabled) goStep(4); });

    renderSpecsList();
    updateSourceLine();
    updateGate3();
    scheduleValidate(0);
  }

  // ── Step 4: screen summary + exact command ────────────────────────────────
  function previewJob() {
    const a = selectedAsset();
    const ids = driverIds();
    if (!state.specPath || !a || !ids.length) return null;
    return { kind: "hw-screen", args: { spec: state.specPath, asset_id: a.asset_id, drivers: ids } };
  }

  function missingReason() {
    if (!selectedAsset()) return "Pick a horn in step 1.";
    if (!driverIds().length) return "Pick at least one woofer driver in step 2.";
    if (!state.specPath) return "Save the spec in step 3 — the screen runs a real file.";
    return null;
  }

  function updateLaunchGate() {
    const btn = stepBody.querySelector("#hwn-launch");
    const why = stepBody.querySelector("#hwn-launch-why");
    if (!btn || !why) return;
    let reason = missingReason();
    if (!reason && state.preview.busy) reason = "Checking the exact command…";
    else if (!reason && state.preview.error) reason = "The preview refused: " + state.preview.error;
    else if (!reason && !state.preview.ok) reason = "Preview the command first.";
    else if (!reason && state.runningHw) reason = `A system job is already running (${state.runningHw.id}).`;
    btn.disabled = !!reason;
    btn.title = reason || "";
    why.innerHTML = reason
      ? `<span class="warn-text">⚠ ${esc(reason)}</span>`
      : `<span class="good-text">✓ The command above is ready to launch.</span>`;
  }

  let previewSeq = 0;
  async function refreshPreview() {
    const cmd = stepBody.querySelector("#hwn-cmd");
    const err = stepBody.querySelector("#hwn-preview-error");
    if (!cmd) return;
    const job = previewJob();
    if (!job) {
      state.preview = { busy: false, ok: false, error: null, command: null };
      cmd.textContent = "— " + (missingReason() || "complete steps 1–3 to see the exact command");
      if (err) err.innerHTML = "";
      updateLaunchGate();
      return;
    }
    const seq = ++previewSeq;
    state.preview = { busy: true, ok: false, error: null, command: null };
    cmd.textContent = "Asking the server for the exact command…";
    if (err) err.innerHTML = "";
    updateLaunchGate();
    let r;
    try { r = await apiPost("/api/preview", job); }
    catch (e) { r = { error: e.message }; }
    if (seq !== previewSeq || !stepBody.isConnected || state.step !== 4) return;
    if (r && r.error) {
      state.preview = { busy: false, ok: false, error: r.error, command: null };
      cmd.textContent = "— " + r.error;
      if (err) err.innerHTML = errBanner("Preview refused: " + r.error);
    } else {
      state.preview = { busy: false, ok: true, error: null, command: r.command };
      cmd.textContent = r.command;
    }
    updateLaunchGate();
  }

  async function launchScreen() {
    const job = previewJob();
    const errEl = stepBody.querySelector("#hwn-launch-error");
    const statusEl = stepBody.querySelector("#hwn-job-status");
    const why = missingReason();
    if (why || !job) {
      if (errEl) errEl.innerHTML = errBanner(why || "Nothing to launch.");
      return;
    }
    if (state.runningHw) {
      if (errEl) errEl.innerHTML = errBanner(`A system job is already running (${state.runningHw.id}).`);
      return;
    }
    if (!state.preview.ok) {
      if (errEl) errEl.innerHTML = errBanner("Preview the command first.");
      return;
    }
    const btn = stepBody.querySelector("#hwn-launch");
    if (btn) btn.disabled = true;
    if (errEl) errEl.innerHTML = "";
    let r;
    try { r = await apiPost("/api/jobs", job); }
    catch (e) { r = { error: e.message }; }
    if (!stepBody.isConnected) return;
    if (r && r.error) {
      if (errEl) errEl.innerHTML = errBanner("Launch refused: " + r.error);
      updateLaunchGate();
      return;
    }
    state.runningHw = { id: r.id };
    if (statusEl) {
      statusEl.innerHTML = `<div class="alert info" role="status">Screen started:
        <code>${esc(r.id)}</code>. One system job runs at a time; this page follows it.</div>`;
    }
    updateLaunchGate();
    watchJob(r.id);
  }

  async function watchJob(jobId) {
    const statusEl = stepBody.querySelector("#hwn-job-status");
    const sleep = ms => new Promise(res => setTimeout(res, ms));
    while (stepBody.isConnected) {
      await sleep(2000);
      if (!stepBody.isConnected) return;
      let j;
      try { j = await api("/api/job/" + encodeURIComponent(jobId)); }
      catch { return; }
      if (!stepBody.isConnected) return;
      if (j.status === "running" || j.status === "queued") {
        if (statusEl) {
          statusEl.innerHTML = `<div class="alert info" role="status">Screen
            <code>${esc(jobId)}</code> is ${esc(j.status)}… <a href="#/status">job log</a></div>`;
        }
        continue;
      }
      if (j.status === "done") {
        const sid = studyIdFromLog(j.log_tail);
        if (statusEl) {
          statusEl.innerHTML = `<div class="alert info" role="status">Screen finished.
            ${sid ? `<a href="#/hw/screen/${esc(sid)}">Open screen ${esc(sid)} →</a>`
                  : `<a href="#/hw/screens">Open the screens list →</a>`}</div>`;
        }
      } else if (statusEl) {
        statusEl.innerHTML = `<div class="alert error" role="alert">
          <b>Screen ${esc(j.status || "failed")}.</b> <a href="#/status">Open the job log</a>.
          ${j.log_tail ? `<pre class="hwn-cmd hwn-job-tail">${esc(tailLines(j.log_tail, 20))}</pre>` : ""}
        </div>`;
      }
      state.runningHw = null;
      updateLaunchGate();
      return;
    }
  }

  function renderStep4() {
    const a = selectedAsset();
    const pickedDrivers = drivers.filter(d => state.drivers.has(d.driver_id));
    const spec = state.spec;
    const cab = (spec && spec.cabinet) || {};
    const asm = (spec && spec.assembly) || {};
    const tgt = (spec && spec.target) || {};
    const pairText = (v, unit) => Array.isArray(v) && v.length >= 2
      ? `${rangeVal(v[0])}–${rangeVal(v[1])}${unit ? " " + unit : ""}` : MISSING;
    const layoutLabel = {
      separate_above: "separate, above",
      separate_side_baffle: "separate, side baffle",
      flush_baffle: "flush baffle",
    }[asm.horn_layout] || asm.horn_layout || MISSING;
    const missingShape = pickedDrivers.filter(d => d.geometry && !d.geometry.complete);

    stepBody.innerHTML = `<section class="card stack" style="gap:12px">
      <h3 tabindex="-1" style="margin:0">4 · ${tip("hw_screen", "Screen")}</h3>
      <p class="hint" role="status">The screen is a fast CPU estimate. It narrows the field and never
        names a single winner; the numbers are estimates, not results.</p>
      <dl class="hwn-summary">
        <dt>Horn</dt><dd>${a
          ? `${esc(a.name || a.asset_id)} · <span class="mono">${esc(a.asset_id)}</span>
             · quality ${esc(a.quality || MISSING)} · band ${bandLabel(a)}
             · ${a.full_domain_mesh ? "full-domain mesh" : "no full-domain mesh"}`
          : `<span class="warn-text">no horn picked — step 1</span>`}</dd>
        <dt>Drivers</dt><dd>${pickedDrivers.length
          ? pickedDrivers.map(d => esc(d.name || d.driver_id)).join(", ")
          : `<span class="warn-text">no drivers picked — step 2</span>`}</dd>
        <dt>Spec</dt><dd>${state.specPath
          ? `<code>${esc(state.specPath)}</code>`
          : `<span class="warn-text">unsaved — step 3</span>`}</dd>
        <dt>Box</dt><dd>W ${pairText(cab.external_width_mm_range, "mm")}
          · H ${pairText(cab.external_height_mm_range, "mm")}
          · D ${pairText(cab.external_depth_mm_range, "mm")}
          · net ${pairText(cab.net_volume_l_range, "L")}
          · tuning ${pairText(cab.tuning_hz_range, "Hz")}
          · port ${pairText(cab.port_throat_area_cm2_range, "cm²")}
          · wall ${num(cab.wall_mm, 1)} mm
          · ${esc(cab.port_type || MISSING)}</dd>
        <dt>Assembly</dt><dd>${esc(layoutLabel)}
          · woofer Y ${pairText(asm.woofer_center_y_mm_range, "mm")}
          · horn Z ${pairText(asm.horn_mounting_offset_z_mm_range, "mm")}</dd>
        <dt>Targets</dt><dd>coverage H ${pairText(tgt.beamwidth_h_deg, "°")}
          · V ${pairText(tgt.beamwidth_v_deg, "°")}
          · listening H ${pairText(tgt.listening_angle_h_deg, "°")}
          · V ${pairText(tgt.listening_angle_v_deg, "°")}
          · F3 max ${tgt.low_freq_f3_hz_max == null ? MISSING : num(tgt.low_freq_f3_hz_max, 1) + " Hz"}</dd>
        <dt>Study label</dt><dd><code>${esc((spec && spec.experiment_id) || MISSING)}</code>
          <span class="muted">(the output directory label)</span></dd>
      </dl>
      ${a && a.quality === "MAGNITUDE_ONLY"
        ? `<div class="alert warn" role="note">Screen only: no phase or delay claims for this horn.</div>`
        : ""}
      ${missingShape.length
        ? `<div class="alert warn" role="note">Real transducer shape fields are incomplete for
           ${esc(missingShape.map(d => d.name || d.driver_id).join(", "))}. The screen uses the fields
           that are present; the driver chips in step 2 list what is missing.</div>`
        : ""}
      <div class="card" style="background:var(--bg)">
        <div class="eyebrow" style="margin-bottom:6px">Command preview</div>
        <pre class="hwn-cmd" id="hwn-cmd">— complete steps 1–3 to see the exact command</pre>
        <div class="hint" role="status" id="hwn-lane">${esc(laneNote(state))}</div>
      </div>
      <div class="hwn-actions">
        <button type="button" class="btn" id="hwn-back">← Back to the spec</button>
        <button type="button" class="btn" id="hwn-refresh">Refresh preview</button>
        <button type="button" class="primary" id="hwn-launch">Launch screen</button>
        <span class="hint" role="status" id="hwn-launch-why"></span>
      </div>
      <div id="hwn-preview-error"></div>
      <div id="hwn-launch-error"></div>
      <div id="hwn-job-status"></div>
    </section>`;

    stepBody.querySelector("#hwn-back").addEventListener("click", () => goStep(3));
    stepBody.querySelector("#hwn-refresh").addEventListener("click", refreshPreview);
    stepBody.querySelector("#hwn-launch").addEventListener("click", launchScreen);
    refreshPreview();
    updateLaunchGate();
  }

  renderStep(false);
  syncUrl();
}

// ════════════════════════════════════════════════════════════════════════════
// Quick launch — #/hw/launch
// ════════════════════════════════════════════════════════════════════════════

export async function viewHwLaunch(root, query = "") {
  skel(root, "Loading saved specs, saved horns and woofer drivers");
  // The fast first page is the newest 40 run dirs (~1 s). "Load all saved horns" below is the
  // user-triggered 200-run scan (about 30 s cold).
  const [aR, dR, defR, spR, jR] = await Promise.allSettled([
    api("/api/hw/assets?limit=40"),
    api("/api/hw/drivers"),
    api("/api/hw/spec-defaults"),
    api("/api/hw/specs"),
    api("/api/jobs"),
  ]);
  busyDone(root);

  if (aR.status !== "fulfilled" || dR.status !== "fulfilled") {
    const msgs = [];
    if (aR.status !== "fulfilled") msgs.push("saved horns: " + aR.reason.message);
    if (dR.status !== "fulfilled") msgs.push("woofer drivers: " + dR.reason.message);
    root.innerHTML = `<div class="stack" style="gap:14px">
      ${errBanner("Quick launch could not load its data — " + msgs.join("; "))}
      <div class="btn-row"><a class="btn" href="#/hw/launch">Reload</a>
        <a class="btn" href="#/hw/new">Guided set-up</a></div>
    </div>`;
    return;
  }

  const assetsData = aR.value || {};
  const driversData = dR.value || {};
  let assets = Array.isArray(assetsData.assets) ? assetsData.assets : [];
  const drivers = Array.isArray(driversData.drivers) ? driversData.drivers : [];
  const defaults = defR.status === "fulfilled" ? defR.value : null;
  const examplePath = defaults && defaults.source ? String(defaults.source) : null;
  const specsData = spR.status === "fulfilled" ? spR.value : null;
  const specsError = spR.status === "rejected" ? spR.reason.message : null;
  const specs = specsData && Array.isArray(specsData.specs) ? specsData.specs : [];
  const jobs = jR.status === "fulfilled" ? jR.value : [];
  const timing = completedScreenTimes(jobs);

  const validSpecs = specs.filter(s => s && s.ok && s.path);
  const invalidSpecs = specs.filter(s => s && !s.ok);
  const options = [];
  if (examplePath) {
    options.push({ path: examplePath, label: `Committed example — ${examplePath} (read-only)` });
  }
  for (const s of validSpecs) options.push({ path: String(s.path), label: `${s.name} — ${s.path}` });

  const q = readQuery(query);
  const knownDrivers = new Set(drivers.map(d => d.driver_id));
  const wantedDrivers = String(q.get("drivers") || "").split(",").filter(Boolean);
  const droppedDrivers = wantedDrivers.filter(id => !knownDrivers.has(id));

  const fromUrl = String(q.get("spec") || "");
  const fallbackSpec = examplePath || (options.length ? options[0].path : "");
  const state = {
    mode: "launch",
    specPath: fromUrl || fallbackSpec,
    assetId: String(q.get("asset") || ""),
    drivers: new Set(wantedDrivers.filter(id => knownDrivers.has(id))),
    assetFilter: "",
    preview: { busy: false, ok: false, error: null, command: null },
    runningHw: (Array.isArray(jobs) ? jobs : []).find(
      j => j && String(j.kind || "").startsWith("hw-") && j.status === "running") || null,
    screenSeconds: timing.seconds,
    screenSamples: timing.samples,
    assetsFull: false,
    assetsLoadingAll: false,
    assetsError: null,
  };

  // Keep a URL-selected asset even when the fast 40-run page did not load its row.
  const specKnown = !state.specPath || options.some(o => o.path === state.specPath);
  const specUnknown = !!state.specPath && !specKnown;

  const selectedAsset = () => assets.find(a => a.asset_id === state.assetId) || null;
  const driverIds = () => drivers.filter(d => state.drivers.has(d.driver_id)).map(d => d.driver_id);

  function syncUrl() {
    const p = new URLSearchParams();
    if (state.specPath) p.set("spec", state.specPath);
    if (state.assetId) p.set("asset", state.assetId);
    const ids = driverIds();
    if (ids.length) p.set("drivers", ids.join(","));
    writeRoute(ROUTE_LAUNCH, p);
  }
  function setHeadId(text) {
    const el = root.querySelector("#hwn-head-id");
    if (el) el.innerHTML = brk(text || "quick launch");
  }

  ensureStyles();
  const pills = [
    `<span class="pill">CPU · no GPU</span>`,
    `<span class="pill">${tip("hw_screen", "screen")} estimate · no winner</span>`,
  ].join("");
  root.innerHTML = `<div id="hw-launch-view" class="stack" style="gap:18px">
    ${pageHead({
      eyebrow: "Horn + woofer · New system",
      title: "Quick launch",
      id: state.specPath || "quick launch",
      pills,
    })}
    ${modeSwitchHtml("launch")}
    <p class="lede" style="max-width:76ch;margin:0">Launch a screen from a saved system spec, a saved
      horn and one or more woofer drivers. The screen is a CPU estimate, not a result.</p>
    ${specsError ? errBanner("Could not read the saved specs: " + specsError) : ""}
    <div id="hnl-spec-warn">${specUnknown ? `<div class="alert warn" role="status">The spec path
      <code>${esc(state.specPath)}</code> is not in the saved list. The preview will refuse it if the
      file cannot be read.</div>` : ""}</div>
    ${invalidSpecs.length ? `<div class="alert warn" role="note"><b>Not selectable — invalid saved
      specs:</b><br>${invalidSpecs.map(s =>
        `${esc(s.name)}: ${esc(s.error || "the parser refused it")}`).join("<br>")}</div>` : ""}
    <div id="hnl-asset-warn"></div>
    ${droppedDrivers.length ? `<div class="alert warn" role="status">Ignored driver id(s) not in the
      catalog: ${esc(droppedDrivers.join(", "))}.</div>` : ""}

    <section class="card stack" style="gap:14px">
      <h3 style="margin:0">${tip("hw_screen", "Screen")} set-up</h3>
      <div class="form-grid">
        <label for="hnl-spec">System spec</label>
        <div>
          <select id="hnl-spec">${specSelectHtml()}</select>
          <div class="hint" role="status" id="hnl-spec-hint"></div>
        </div>
        <label for="hnl-asset-filter">Find a horn</label>
        <div>
          <input id="hnl-asset-filter" type="search" value="${esc(state.assetFilter || "")}"
            placeholder="Search name, brief, design hash or asset id" aria-label="Search saved horns">
          <select id="hnl-asset" style="margin-top:6px" aria-label="Saved horn asset">
            ${assetOptionsHtml("")}
          </select>
          <div class="hint" role="status" id="hnl-asset-hint"></div>
          <div class="hwn-actions">
            <button type="button" class="btn" id="hnl-load-all">Load all saved horns (slower)</button>
            <span class="hint" role="status" id="hnl-load-all-note"></span>
          </div>
        </div>
        <span class="form-label">Woofer drivers</span>
        <div>
          <div class="hwn-drivers" id="hnl-drivers" role="group" aria-label="Woofer drivers">
            ${drivers.length
              ? drivers.map(d => driverCardHtml(d, state.drivers.has(d.driver_id))).join("")
              : `<div class="alert warn" role="status">No driver T/S files were found in
                 <code>examples/systems/driver_ts/</code>.</div>`}
          </div>
          <div class="hint" role="status" id="hnl-driver-hint">${driverSummaryHtml(drivers, state.drivers)}</div>
        </div>
      </div>
    </section>

    <div id="hnl-asset-summary"></div>

    <section class="card stack" style="gap:12px">
      <div class="eyebrow">Command preview</div>
      <pre class="hwn-cmd" id="hnl-cmd">— pick a spec, a horn and at least one driver</pre>
      <div class="hint" role="status" id="hnl-lane">${esc(laneNote(state))}</div>
      <div class="btn-row">
        <button type="button" class="btn" id="hnl-preview">Preview</button>
        <button type="button" class="primary" id="hnl-launch">Launch screen</button>
        <span class="hint" role="status" id="hnl-why"></span>
      </div>
      <div id="hnl-error"></div>
      <div id="hnl-job-status"></div>
    </section>
  </div>`;

  function specSelectHtml() {
    const paths = new Set(options.map(o => o.path));
    const parts = [`<option value="">— pick a system spec —</option>`];
    if (!options.length) {
      parts.push(`<option value="" disabled>— no spec available —</option>`);
    }
    for (const o of options) {
      parts.push(`<option value="${esc(o.path)}"${o.path === state.specPath ? " selected" : ""}>${esc(o.label)}</option>`);
    }
    if (state.specPath && !paths.has(state.specPath)) {
      parts.push(`<option value="${esc(state.specPath)}" selected>${esc(state.specPath)} (from the URL; not in the saved list)</option>`);
    }
    return parts.join("");
  }

  function assetOptionsHtml(needle) {
    const filtered = assets.filter(a => assetMatches(a, String(needle || "").trim().toLowerCase()));
    const MAX = 200;
    let list = filtered.slice(0, MAX);
    const sel = selectedAsset();
    if (sel && !list.some(a => a.asset_id === sel.asset_id)) list = [sel, ...list];
    const parts = [`<option value="">— pick a saved horn —</option>`];
    if (state.assetId && !sel) {
      parts.push(`<option value="${esc(state.assetId)}" selected>${esc(state.assetId)} (not in the loaded list)</option>`);
    }
    if (!list.length) parts.push(`<option value="" disabled>— no matching saved horn —</option>`);
    for (const a of list) {
      parts.push(`<option value="${esc(a.asset_id)}"${a.asset_id === state.assetId ? " selected" : ""}>`
        + `${esc(a.name || a.asset_id)} — ${esc(a.asset_id)} · ${esc(a.quality || "?")}`
        + `${a.full_domain_mesh ? " · full-domain mesh" : ""}</option>`);
    }
    return parts.join("");
  }

  function updateAssetHint() {
    const hint = root.querySelector("#hnl-asset-hint");
    if (!hint) return;
    const needle = String((root.querySelector("#hnl-asset-filter") || {}).value || "").trim().toLowerCase();
    const n = assets.filter(a => assetMatches(a, needle)).length;
    hint.textContent = `Showing ${Math.min(200, n)} of ${n} match${n === 1 ? "" : "es"}`
      + ` (${assets.length} asset${assets.length === 1 ? "" : "s"} loaded from the newest `
      + `${state.assetsFull ? 200 : 40} run dirs).`;
  }

  function updateAssetLoadUi() {
    const sel = selectedAsset();
    const btn = root.querySelector("#hnl-load-all");
    const note = root.querySelector("#hnl-load-all-note");
    const warn = root.querySelector("#hnl-asset-warn");
    if (btn) {
      btn.disabled = state.assetsLoadingAll || state.assetsFull;
      btn.textContent = state.assetsFull ? "All saved horns loaded"
        : state.assetsLoadingAll ? "Loading all saved horns…" : "Load all saved horns (slower)";
    }
    if (note) {
      note.innerHTML = state.assetsLoadingAll
        ? "Loading all saved horns… this can take about 30 seconds. The current list and your selection stay."
        : state.assetsError
          ? `<span class="warn-text">⚠ Could not load all saved horns: ${esc(state.assetsError)}</span>`
          : state.assetsFull
            ? "All saved horns are loaded (newest 200 run dirs)."
            : "The first page loads the newest 40 run dirs quickly. Load all for older designs such as 0062fb59fbf63eae (about 30 seconds).";
    }
    if (warn) {
      if (!state.assetId || sel) warn.innerHTML = "";
      else if (state.assetsLoadingAll) {
        warn.innerHTML = `<div class="alert info" role="status">Loading all saved horns to find the
          selected asset <code>${esc(state.assetId)}</code>…</div>`;
      } else {
        warn.innerHTML = `<div class="alert warn" role="status">The selected asset
          <code>${esc(state.assetId)}</code> is not in the ${state.assetsFull ? "newest 200" : "first 40"}
          saved-horn runs. ${state.assetsFull ? "Pick another asset." : "Use “Load all saved horns (slower)” to find it."}</div>`;
      }
    }
  }

  async function loadAllAssets() {
    if (state.assetsLoadingAll || state.assetsFull) return;
    state.assetsLoadingAll = true;
    state.assetsError = null;
    updateAssetLoadUi();
    let data;
    try {
      data = await api("/api/hw/assets?limit=200");
    } catch (e) {
      state.assetsLoadingAll = false;
      state.assetsError = e.message;
      updateAssetLoadUi();
      return;
    }
    state.assetsLoadingAll = false;
    if (!root.isConnected) return;
    assets = Array.isArray(data.assets) ? data.assets : assets;
    state.assetsFull = true;
    state.assetsError = null;
    const select = root.querySelector("#hnl-asset");
    if (select) select.innerHTML = assetOptionsHtml(state.assetFilter);
    updateAssetHint();
    const summary = root.querySelector("#hnl-asset-summary");
    if (summary) summary.innerHTML = launchAssetSummaryHtml();
    updateAssetLoadUi();
    updateLaunchGate();
    if (previewJob()) schedulePreview();
  }

  function launchAssetSummaryHtml() {
    const a = selectedAsset();
    if (a) return assetSummaryHtml(a);
    if (state.assetId) {
      return `<p class="hint" role="status"><span class="warn-text">Selected asset
        <code>${esc(state.assetId)}</code> is not in the loaded
        ${state.assetsFull ? "newest 200" : "first 40"} run dirs.</span>
        ${state.assetsFull ? "Pick another asset." : "Use “Load all saved horns (slower)” to see it."}</p>`;
    }
    return `<p class="hint" role="status">Pick a saved horn above; the preview waits for it.</p>`;
  }

  function updateSpecHint() {
    const el = root.querySelector("#hnl-spec-hint");
    const warn = root.querySelector("#hnl-spec-warn");
    const unknown = !!state.specPath && !options.some(o => o.path === state.specPath);
    if (warn) {
      warn.innerHTML = unknown ? `<div class="alert warn" role="status">The spec path
        <code>${esc(state.specPath)}</code> is not in the saved list. The preview will refuse it if the
        file cannot be read.</div>` : "";
    }
    if (!el) return;
    if (!state.specPath) {
      el.innerHTML = `<span class="warn-text">⚠ Pick a system spec.</span>`;
    } else if (examplePath && state.specPath === examplePath) {
      el.innerHTML = `The committed example is read-only; the screen can use it as-is.`;
    } else if (unknown) {
      el.innerHTML = `<span class="warn-text">⚠ This path is not in the saved list.</span>`;
    } else {
      el.innerHTML = `Saved spec: <code>${esc(state.specPath)}</code>.`;
    }
  }

  function updateDriverHint() {
    const el = root.querySelector("#hnl-driver-hint");
    if (el) el.innerHTML = driverSummaryHtml(drivers, state.drivers);
  }

  // ── Preview / launch gate ─────────────────────────────────────────────────
  function previewJob() {
    const a = selectedAsset();
    const ids = driverIds();
    if (!state.specPath || !a || !ids.length) return null;
    return { kind: "hw-screen", args: { spec: state.specPath, asset_id: a.asset_id, drivers: ids } };
  }

  function missingReason() {
    if (!state.specPath) return "Pick a system spec.";
    if (state.assetId && !selectedAsset()) return "Load all saved horns to confirm the selected asset.";
    if (!selectedAsset()) return "Pick a horn asset.";
    if (!driverIds().length) return "Pick at least one woofer driver.";
    return null;
  }

  function updateLaunchGate() {
    const btn = root.querySelector("#hnl-launch");
    const why = root.querySelector("#hnl-why");
    if (!btn || !why) return;
    let reason = missingReason();
    if (!reason && state.preview.busy) reason = "Checking the exact command…";
    else if (!reason && state.preview.error) reason = "The preview refused: " + state.preview.error;
    else if (!reason && !state.preview.ok) reason = "Preview the command first.";
    else if (!reason && state.runningHw) reason = `A system job is already running (${state.runningHw.id}).`;
    btn.disabled = !!reason;
    btn.title = reason || "";
    why.innerHTML = reason
      ? `<span class="warn-text">⚠ ${esc(reason)}</span>`
      : `<span class="good-text">✓ The command above is ready to launch.</span>`;
  }

  let previewSeq = 0;
  async function refreshPreview() {
    const cmd = root.querySelector("#hnl-cmd");
    const err = root.querySelector("#hnl-error");
    if (!cmd) return;
    const job = previewJob();
    if (!job) {
      state.preview = { busy: false, ok: false, error: null, command: null };
      cmd.textContent = "— " + (missingReason() || "complete the three controls");
      if (err) err.innerHTML = "";
      updateLaunchGate();
      return;
    }
    const seq = ++previewSeq;
    state.preview = { busy: true, ok: false, error: null, command: null };
    cmd.textContent = "Asking the server for the exact command…";
    if (err) err.innerHTML = "";
    updateLaunchGate();
    let r;
    try { r = await apiPost("/api/preview", job); }
    catch (e) { r = { error: e.message }; }
    if (seq !== previewSeq || !root.isConnected) return;
    if (r && r.error) {
      state.preview = { busy: false, ok: false, error: r.error, command: null };
      cmd.textContent = "— " + r.error;
      if (err) err.innerHTML = errBanner("Preview refused: " + r.error);
    } else {
      state.preview = { busy: false, ok: true, error: null, command: r.command };
      cmd.textContent = r.command;
    }
    updateLaunchGate();
  }

  let previewTimer = null;
  function schedulePreview() {
    clearTimeout(previewTimer);
    previewSeq += 1;                       // invalidate any in-flight preview of the old controls
    state.preview = { busy: true, ok: false, error: null, command: null };
    updateLaunchGate();
    previewTimer = setTimeout(refreshPreview, 250);
  }

  async function launchScreen() {
    const job = previewJob();
    const errEl = root.querySelector("#hnl-error");
    const statusEl = root.querySelector("#hnl-job-status");
    const why = missingReason();
    if (why || !job) {
      if (errEl) errEl.innerHTML = errBanner(why || "Nothing to launch.");
      return;
    }
    if (state.runningHw) {
      if (errEl) errEl.innerHTML = errBanner(`A system job is already running (${state.runningHw.id}).`);
      return;
    }
    if (!state.preview.ok) {
      if (errEl) errEl.innerHTML = errBanner("Preview the command first.");
      return;
    }
    const btn = root.querySelector("#hnl-launch");
    if (btn) btn.disabled = true;
    if (errEl) errEl.innerHTML = "";
    let r;
    try { r = await apiPost("/api/jobs", job); }
    catch (e) { r = { error: e.message }; }
    if (!root.isConnected) return;
    if (r && r.error) {
      if (errEl) errEl.innerHTML = errBanner("Launch refused: " + r.error);
      updateLaunchGate();
      return;
    }
    state.runningHw = { id: r.id };
    if (statusEl) {
      statusEl.innerHTML = `<div class="alert info" role="status">Screen started:
        <code>${esc(r.id)}</code>. One system job runs at a time; this page follows it.</div>`;
    }
    updateLaunchGate();
    followJob(r.id);
  }

  async function followJob(jobId) {
    const statusEl = root.querySelector("#hnl-job-status");
    const sleep = ms => new Promise(res => setTimeout(res, ms));
    while (root.isConnected) {
      await sleep(2000);
      if (!root.isConnected) return;
      let j;
      try { j = await api("/api/job/" + encodeURIComponent(jobId)); }
      catch { return; }
      if (!root.isConnected) return;
      if (j.status === "running" || j.status === "queued") {
        if (statusEl) {
          statusEl.innerHTML = `<div class="alert info" role="status">Screen
            <code>${esc(jobId)}</code> is ${esc(j.status)}… <a href="#/status">job log</a></div>`;
        }
        continue;
      }
      if (j.status === "done") {
        const sid = studyIdFromLog(j.log_tail);
        if (statusEl) {
          statusEl.innerHTML = `<div class="alert info" role="status">Screen finished.
            ${sid ? `<a href="#/hw/screen/${esc(sid)}">Open screen ${esc(sid)} →</a>`
                  : `<a href="#/hw/screens">Open the screens list →</a>`}</div>`;
        }
      } else if (statusEl) {
        statusEl.innerHTML = `<div class="alert error" role="alert">
          <b>Screen ${esc(j.status || "failed")}.</b> <a href="#/status">Open the job log</a>.
          ${j.log_tail ? `<pre class="hwn-cmd hwn-job-tail">${esc(tailLines(j.log_tail, 20))}</pre>` : ""}
        </div>`;
      }
      state.runningHw = null;
      updateLaunchGate();
      return;
    }
  }

  // ── Wiring ────────────────────────────────────────────────────────────────
  const specSel = root.querySelector("#hnl-spec");
  const assetFilter = root.querySelector("#hnl-asset-filter");
  const assetSel = root.querySelector("#hnl-asset");
  const assetSummary = root.querySelector("#hnl-asset-summary");
  const driversHost = root.querySelector("#hnl-drivers");

  root.querySelectorAll(".hwn-mode").forEach(btn => btn.addEventListener("click", () => {
    if (btn.dataset.mode === "launch") return;
    const p = new URLSearchParams();
    p.set("step", "1");
    if (state.assetId) p.set("asset", state.assetId);
    const ids = driverIds();
    if (ids.length) p.set("drivers", ids.join(","));
    location.hash = ROUTE_NEW + "?" + p.toString();
  }));

  specSel.addEventListener("change", () => {
    state.specPath = String(specSel.value || "");
    setHeadId(state.specPath || "quick launch");
    syncUrl();
    updateSpecHint();
    schedulePreview();
  });
  assetFilter.addEventListener("input", () => {
    state.assetFilter = assetFilter.value;
    assetSel.innerHTML = assetOptionsHtml(state.assetFilter);
    updateAssetHint();
  });
  assetSel.addEventListener("change", () => {
    state.assetId = String(assetSel.value || "");
    syncUrl();
    assetSummary.innerHTML = launchAssetSummaryHtml();
    updateAssetLoadUi();
    schedulePreview();
  });
  driversHost.addEventListener("change", e => {
    if (!e.target || e.target.name !== "hwn-driver") return;
    const id = String(e.target.value || "");
    if (e.target.checked) state.drivers.add(id); else state.drivers.delete(id);
    const card = e.target.closest(".hwn-driver");
    if (card) card.classList.toggle("is-picked", !!e.target.checked);
    syncUrl();
    updateDriverHint();
    schedulePreview();
  });
  root.querySelector("#hnl-preview").addEventListener("click", refreshPreview);
  root.querySelector("#hnl-launch").addEventListener("click", launchScreen);
  root.querySelector("#hnl-load-all").addEventListener("click", loadAllAssets);

  assetSummary.innerHTML = launchAssetSummaryHtml();
  updateSpecHint();
  updateAssetHint();
  updateAssetLoadUi();
  updateDriverHint();
  syncUrl();
  refreshPreview();
}
