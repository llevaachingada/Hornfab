// overview_params.js — hornlab-search GUI   AGPL-3.0-or-later
//
// #/overview?tab=params — "Parameters" (Overview phase 4, WP4.3). Read-only: every knob, bound,
// bound-hit flag and best J comes from GET /api/overview/params (data_overview_params.py). This
// module only formats and counts array lengths; it never re-derives which knob is at a bound and
// never compares J across score identities.
//
// Exports: paramsTabHtml(pd), wireParams(root) — the latter only syncs aria-expanded on the
// per-line <details>; there is no navigation or URL state in this tab.

const MISSING = "—";
const esc = s => (s == null ? MISSING : String(s))
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
const brk = s => esc(s).replace(/([_\-./|])/g, "$1<wbr>");
const num = (v, d = 3) => (v == null || !isFinite(v)) ? MISSING : Number(v).toFixed(d);
const int = v => (v == null || !isFinite(v)) ? MISSING : Math.round(v).toLocaleString("en-US");

// Plain number formatting for knob values: keep integers crisp, trim long floats. Escaped at use.
function val(v) {
  if (v == null || v === "") return MISSING;
  if (typeof v === "number" && isFinite(v)) {
    return Number.isInteger(v) ? String(v) : String(Number(v.toFixed(4)));
  }
  return String(v);
}

const STATUS_PILL = { current: "good", diagnostic: "warn", unregistered: "warn", legacy: "" };
const STATUS_TIP = {
  current: "In active use; listed in examples/score_identities.yaml.",
  diagnostic: "Pilot / probe identity: read as diagnostic, not a leaderboard.",
  unregistered: "Not in examples/score_identities.yaml: no floor, so no tie band.",
  legacy: "Objective version below the current default; hidden unless 'show legacy' is on.",
};

const STYLE = `
.ovp-id h3{margin:0 0 2px;font-size:1rem;overflow-wrap:anywhere}
.ovp-id .ovp-meta{font-size:.76rem;margin:0 0 6px;overflow-wrap:anywhere}
.ovp-tbl th,.ovp-tbl td{padding:6px 8px;vertical-align:top}
.ovp-tbl th.r,.ovp-tbl td.r{white-space:nowrap}
.ovp-linecell{white-space:normal;min-width:0}
.ovp-narrow{display:none;font-size:.76rem}
.ovp-narrow .pill{font-size:.68rem}
.ovp-line>summary{cursor:pointer;padding:2px 0;overflow-wrap:anywhere}
.ovp-line>summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.ovp-line>summary a{overflow-wrap:anywhere}
.ovp-knobs{font-size:.72rem;margin-left:8px}
.ovp-body{display:grid;gap:8px;margin:8px 0 2px;min-width:0}
.ovp-sub{display:grid;gap:3px;min-width:0}
.ovp-chips .pill{font-size:.7rem;white-space:normal;overflow-wrap:anywhere}
.ovp-none{margin:0;font-size:.76rem}
.ovp-free{min-width:340px}
.ovp-free td,.ovp-free th{padding:3px 8px;font-size:.76rem}
.ovp-free tr.ovp-hit td:first-child{box-shadow:inset 3px 0 0 var(--bad)}
.ovp-err{margin:4px 0 0;font-size:.78rem;overflow-wrap:anywhere}
.ovp-scroll{max-width:100%}
@media (min-width:701px){
  .ovp-tbl{min-width:520px}
}
@media (max-width:700px){
  /* Best J and the hit count move into the line cell; the table never clips a header to one letter. */
  .ovp-tbl .ovp-num{display:none}
  .ovp-tbl{min-width:0}
  .ovp-narrow{display:inline}
  .ovp-free-scroll .tbl-scroll-hint{display:block}
}
@media (max-width:640px){
  .kpis.ovp-kpis{grid-template-columns:repeat(2,minmax(0,1fr)) !important}
}
@media (max-width:520px){
  .ovp-free{min-width:300px}
}
`;

function ensureStyle() {
  if (document.getElementById("ovp-style")) return;
  const s = document.createElement("style"); s.id = "ovp-style"; s.textContent = STYLE;
  document.head.appendChild(s);
}

const pill = (t, cls = "", title = "") =>
  `<span class="pill ${cls}"${title ? ` title="${esc(title)}"` : ""}>${esc(t)}</span>`;
const kpi = (label, value, sub = "", cls = "") =>
  `<div class="kpi"><span>${esc(label)}</span><b class="${cls}">${esc(value)}</b>${sub ? `<small class="muted" style="font-size:.72rem">${esc(sub)}</small>` : ""}</div>`;

const boundLineCount = ident => {
  const n = Number(ident && ident.n_bound_lines);
  if (isFinite(n)) return n;
  return (ident && Array.isArray(ident.lines) ? ident.lines : [])
    .filter(l => l && Array.isArray(l.at_bound) && l.at_bound.length).length;
};

function fixedBlock(fixed) {
  if (!fixed.length) return `<p class="muted ovp-none">No fixed knobs.</p>`;
  const chips = fixed.filter(k => k && typeof k === "object").map(k => {
    const hasRange = k.lo != null && k.hi != null;
    const title = hasRange ? `fixed at [${val(k.lo)}, ${val(k.hi)}]` : "fixed (search: false)";
    return `<span class="pill ovp-chip" title="${esc(title)}">${esc(k.key)} = ${esc(val(k.value))}</span>`;
  }).join(" ");
  return `<div class="ovp-sub"><div class="eyebrow">Fixed</div>
    <div class="pill-row ovp-chips">${chips}</div></div>`;
}

function freeBlock(free) {
  if (!free.length) return `<p class="muted ovp-none">No free knobs.</p>`;
  const rows = free.filter(k => k && typeof k === "object").map(k => {
    const at = (k.at_bound === "lo" || k.at_bound === "hi") ? k.at_bound : "";
    return `<tr${at ? ' class="ovp-hit"' : ""}>
      <td class="mono">${esc(k.key)}</td>
      <td class="r mono">${esc(val(k.value))}</td>
      <td class="r mono muted">[${esc(val(k.lo))}, ${esc(val(k.hi))}]</td>
      <td>${at ? pill(at, "bad", "within 2% of this bound (decided by the server)") : `<span class="muted">${MISSING}</span>`}</td></tr>`;
  }).join("");
  return `<div class="ovp-sub"><div class="eyebrow">Free knobs</div>
    <div class="tbl-scroll ovp-free-scroll">
      <p class="tbl-scroll-hint">scroll for all columns →</p>
      <div class="tbl-wrap"><table class="ov-tbl ovp-free">
        <thead><tr><th>Knob</th><th class="r">best</th><th class="r">range</th><th>at bound</th></tr></thead>
        <tbody>${rows}</tbody></table></div>
    </div></div>`;
}

function lineRow(l) {
  const fixed = Array.isArray(l.fixed) ? l.fixed : [];
  const free = Array.isArray(l.free) ? l.free : [];
  const hits = Array.isArray(l.at_bound) ? l.at_bound.length : 0;
  const err = l.error ? String(l.error) : "";
  const label = `<b>${esc(l.construction || MISSING)}</b>${l.card ? ` <span class="muted">· ${esc(l.card)}</span>` : ""}`;
  const linked = l.best_run_id
    ? `<a href="#/run/${encodeURIComponent(String(l.best_run_id))}">${label}</a>`
    : label;
  const hasKnobs = !err && (fixed.length > 0 || free.length > 0);
  const hitText = hits
    ? pill(`${int(hits)} hit${hits === 1 ? "" : "s"}`, "bad", "free knobs within 2% of their own bound")
    : `<span class="muted">0 hits</span>`;
  // Narrow layout hides the numeric columns, so J and the hit count stay in the row header itself.
  const narrow = `<span class="ovp-narrow muted">J <span class="mono">${num(l.best_j)}</span> · ${hitText}</span>`;
  const summary = `<summary>${linked}${narrow}<span class="ovp-knobs muted">${int(fixed.length)} fixed · ${int(free.length)} free${hits ? ` · ${int(hits)} at a bound` : ""}</span></summary>`;
  const cell = hasKnobs
    ? `<details class="ovp-line">${summary}<div class="ovp-body">${fixedBlock(fixed)}${freeBlock(free)}</div></details>`
    : `<div class="ovp-lineflat">${linked}${narrow}</div>`;
  return `<tr>
    <td class="ovp-linecell">${cell}${err ? `<p class="muted ovp-err">${esc(err)}</p>` : ""}</td>
    <td class="r mono ovp-num">${num(l.best_j)}</td>
    <td class="r ovp-num">${hitText}</td></tr>`;
}

function identityCard(ident, first = false) {
  const lines = (Array.isArray(ident.lines) ? ident.lines : []).filter(l => l && typeof l === "object");
  if (!lines.length) return "";
  const nBound = boundLineCount(ident);
  const status = String(ident.status || "");
  const statusPill = status ? pill(status, STATUS_PILL[status] || "", STATUS_TIP[status]) : "";
  const head = `<div class="eyebrow">score identity${ident.objective_version != null ? ` · v${esc(ident.objective_version)}` : ""}</div>
    <h3>${esc(ident.label || ident.id || MISSING)} ${statusPill} ${pill(`${int(nBound)} line${nBound === 1 ? "" : "s"} at a bound`, nBound ? "warn" : "", "lines with at least one free knob within 2% of its bound")}</h3>
    <p class="muted mono ovp-meta">${brk(ident.id || MISSING)} · ${int(lines.length)} line${lines.length === 1 ? "" : "s"}</p>`;
  // One visible header row for the whole page; later tables keep a hidden caption for screen readers.
  const caption = first ? "" : `<caption class="sr-only">Line of work, best J, bound hits</caption>`;
  const thead = first ? `<thead><tr><th>Line of work</th><th class="r ovp-num">best J</th><th class="r ovp-num">bound hits</th></tr></thead>` : "";
  const table = `<div class="tbl-scroll ovp-scroll">
    <div class="tbl-wrap"><table class="ov-tbl ovp-tbl">
    ${caption}${thead}
    <tbody>${lines.map(lineRow).join("")}</tbody></table></div></div>`;
  return `<section class="card ovp-id">${head}${table}</section>`;
}

export function paramsTabHtml(pd) {
  ensureStyle();
  const identities = (pd && Array.isArray(pd.identities)) ? pd.identities.filter(i => i && typeof i === "object") : [];
  const shown = identities.filter(i => Array.isArray(i.lines) && i.lines.some(l => l && typeof l === "object"));
  if (!shown.length) return `<p class="muted">No parameter sets to show — no ranked line in this window has a readable config.</p>`;

  const lines = shown.flatMap(i => i.lines.filter(l => l && typeof l === "object"));
  const boundTotal = shown.reduce((n, i) => n + boundLineCount(i), 0);
  const fixedTotal = lines.reduce((n, l) => n + (Array.isArray(l.fixed) ? l.fixed.length : 0), 0);
  const windowPills = [
    pd.days != null ? pill(`last ${int(pd.days)} day${Number(pd.days) === 1 ? "" : "s"}`) : "",
    pd.generated_utc ? pill(`generated ${pd.generated_utc}`) : "",
    pd.show_legacy ? pill("includes legacy scores", "warn") : "",
  ].filter(Boolean).join(" ");

  const head = `<div>
    <div class="eyebrow">Parameters · best run of each ranked line</div>
    <p class="muted" style="font-size:.8rem;margin:2px 0 0">The bounds from the run's config and the parameters it settled on. Fixed knobs do not search. A free knob marked lo or hi sits within 2% of its own bound — the server decides that, this page only reports it.</p>
    ${windowPills ? `<div class="pill-row" style="margin:6px 0 0">${windowPills}</div>` : ""}
  </div>`;
  const kpis = `<div class="kpis ovp-kpis">
    ${kpi("Identities", int(shown.length), "with a ranked line")}
    ${kpi("Lines", int(lines.length), "one row each")}
    ${kpi("Lines at a bound", int(boundTotal), "one knob within 2% of a bound", boundTotal ? "warn" : "")}
    ${kpi("Fixed knobs", int(fixedTotal), "do not search")}
  </div>`;
  return `${head}${kpis}${shown.map((ident, i) => identityCard(ident, i === 0)).join("")}`;
}

export function wireParams(root) {
  if (!root) return;
  for (const det of root.querySelectorAll("details.ovp-line")) {
    const sum = det.querySelector("summary");
    if (!sum) continue;
    sum.setAttribute("aria-expanded", String(det.open));
    det.addEventListener("toggle", () => sum.setAttribute("aria-expanded", String(det.open)));
  }
}
