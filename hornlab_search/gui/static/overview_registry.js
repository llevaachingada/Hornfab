// overview_registry.js — hornlab-search GUI   AGPL-3.0-or-later
//
// #/overview?tab=decisions — project readiness registry (WP3.2) plus the software-health section
// (WP3.3), and the compact snapshot list for the Overview header (WP4.2 UI hook). Read-only: every
// row, level, status and count comes from GET /api/overview/registry (and the snapshots list). This
// module only renders and filters; it copies the Readiness table design but imports nothing from hw.js.
//
// Exports:
//   registryTabHtml(reg, healthFindings) -> HTML fragment for the Decisions tab body
//   healthHtml(healthFindings)           -> one section, used inside registryTabHtml and standalone
//   snapshotListHtml(snaps)              -> compact list; returns "" when there is nothing to show
//   wireRegistry(root)                   -> binds the level/area filters (client-side, DOM-local)

const MISSING = "—";
const esc = s => (s == null ? MISSING : String(s))
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
const brk = s => esc(s).replace(/([_\-./|])/g, "$1<wbr>");
const int = v => (v == null || !isFinite(v)) ? MISSING : Math.round(v).toLocaleString("en-US");
const dash = v => (v == null || v === "" || v === "-" ? MISSING : String(v));

const LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const LVL_CLASS = { CRITICAL: "bad", HIGH: "warn", MEDIUM: "hw-lvl-medium", LOW: "hw-lvl-low" };
const lvlOf = x => String((x && x.level) || "").toUpperCase();
const areaOf = x => String((x && x.area) || "").trim();
const pill = (t, cls = "", title = "") =>
  `<span class="pill ${cls}"${title ? ` title="${esc(title)}"` : ""}>${esc(t)}</span>`;

const STYLE = `
.ovr-head{display:grid;gap:2px;min-width:0}
.ovr-bar{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;font-size:.8rem;min-width:0}
.ovr-bar>label{display:inline-flex;align-items:center;gap:6px;min-width:0}
.ovr-bar select{font:inherit;font-size:.82rem;min-height:32px;max-width:100%;padding:4px 8px;
  border:1px solid var(--rule);border-radius:5px;background:var(--surface);color:var(--ink)}
.ovr-bar select:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.ovr-count{font-size:.74rem}
.ovr-risk-table{min-width:720px}
.ovr-dec-table{min-width:760px}
.ovr-dec-src{font-size:.72rem;margin:2px 0 0;overflow-wrap:anywhere}
.ovr-health-table{min-width:620px}
.ovr-sub{margin:2px 0 0;font-size:.78rem;overflow-wrap:anywhere}
.ovr-ev{list-style:none;margin:2px 0 0;padding:0;display:grid;gap:1px;font-size:.74rem;overflow-wrap:anywhere}
.ovr-src{font-size:.72rem;overflow-wrap:anywhere}
.ovr-snap-list{list-style:none;margin:2px 0 0;padding:0;display:grid;gap:4px;font-size:.84rem}
.ovr-snap-list li{display:flex;flex-wrap:wrap;gap:2px 10px;align-items:baseline;min-width:0}
.ovr-snap-list a,.ovr-snap-list b{min-width:0;overflow-wrap:anywhere}
.hw-readiness-table tr[hidden]{display:none}
.hw-readiness-table .ovr-dec-nowrap{white-space:nowrap}
@media (max-width:700px){
  .ovr-bar{font-size:.78rem}
  .ovr-scroll .tbl-scroll-hint{display:block}
}
`;

function ensureStyle() {
  if (document.getElementById("ovr-style")) return;
  const s = document.createElement("style"); s.id = "ovr-style"; s.textContent = STYLE;
  document.head.appendChild(s);
}

// Copy of the Readiness status badge: open is stated plainly, closed is good, anything else warns.
function statusPill(x) {
  const st = String((x && x.status) || "open");
  const cls = st === "closed" ? "good" : st === "open" ? "" : "warn";
  return pill(st.replace(/_/g, " "), cls);
}

// Evidence wraps at spaces; only a genuinely long identifier gets an anywhere-break span.
function evidenceHtml(s) {
  return dash(s).split(/(\s+)/).map(part => {
    if (!part) return "";
    if (/^\s+$/.test(part)) return part;
    return part.length > 22 ? `<span class="hw-long-id">${esc(part)}</span>` : esc(part);
  }).join("");
}

function errText(e) {
  if (e == null) return "unreadable registry entry";
  if (typeof e === "string") return e;
  if (typeof e === "object") {
    if (e.message) return String(e.message);
    if (e.error) return String(e.error);
    if (e.source) return String(e.source);
  }
  return "unreadable registry entry";
}

function errorsHtml(errors) {
  const list = Array.isArray(errors) ? errors.filter(e => e != null && e !== "") : [];
  if (!list.length) return "";
  const items = list.map(e => `<li>${esc(errText(e))}</li>`).join("");
  return `<div class="alert error" role="alert"><b>Registry:</b> ${list.length === 1
    ? esc(errText(list[0]))
    : `<ul style="margin:4px 0 0;padding-left:18px">${items}</ul>`}</div>`;
}

function decidedText(v) {
  if (v == null || v === "" || v === false) return MISSING;
  if (v === true) return "yes";
  return String(v);
}

// A wp/blocked_by value is printed only when it exists; "-", "—" and "" mean "not set".
function presentText(v) {
  const t = v == null ? "" : String(v).trim();
  return (t && t !== "-" && t !== "—") ? t : "";
}
function wpText(v) {
  const t = presentText(v);
  if (!t) return "";
  return /^wp(\b|\d)/i.test(t) ? t : `WP ${t}`;
}
function blockedText(v) {
  const t = presentText(v);
  if (!t) return "";
  return /^blocked\s+by\b/i.test(t) ? t : `blocked by ${t}`;
}

// Software-health evidence often restates the detail ("Top failure kinds: …" / "top failures: …").
// Keep an evidence item only when it is not fully contained in, or mostly a token repeat of, detail.
function uniqueEvidence(detail, evidence) {
  const norm = s => String(s == null ? "" : s).toLowerCase().replace(/[^a-z0-9.]+/g, " ").trim();
  const dNorm = norm(detail);
  const dTokens = new Set(dNorm.split(" ").filter(Boolean));
  return (Array.isArray(evidence) ? evidence : []).filter(e => {
    const n = norm(e);
    if (!n) return false;
    if (dNorm && dNorm.includes(n)) return false;
    const toks = n.split(" ").filter(Boolean);
    if (!toks.length) return false;
    if (!dTokens.size) return true;
    const hit = toks.filter(t => dTokens.has(t)).length;
    return hit / toks.length < 0.7;
  });
}

function risksTable(risks) {
  const levels = [...new Set(risks.map(lvlOf).filter(Boolean))];
  const levelOpts = LEVELS.filter(l => levels.includes(l))
    .concat(levels.filter(l => !LEVELS.includes(l)).sort());
  const areas = [...new Set(risks.map(areaOf).filter(Boolean))].sort();
  const lvlSel = `<label>Level <select id="ovr-lvl"><option value="">all levels (${levels.length})</option>`
    + levelOpts.map(l => `<option value="${esc(l)}">${esc(l)}</option>`).join("") + "</select></label>";
  const areaSel = `<label>Area <select id="ovr-area"><option value="">all areas (${areas.length})</option>`
    + areas.map(a => `<option value="${esc(a)}">${esc(a)}</option>`).join("") + "</select></label>";

  const body = risks.length ? risks.map(x => {
    const lv = lvlOf(x);
    const second = [wpText(x.wp), blockedText(x.blocked_by)].filter(Boolean).join(" · ");
    return `<tr data-level="${esc(lv)}" data-area="${esc(areaOf(x))}">
      <td class="hw-risk-id">${esc(x.id)}<br>${statusPill(x)}</td>
      <td><span class="pill ${LVL_CLASS[lv] || ""}">${esc(lv || MISSING)}</span></td>
      <td class="hw-wrap"><b>${esc(x.title)}</b>${second ? `<p class="ovr-sub muted">${esc(second)}</p>` : ""}
        ${x.evidence ? `<p class="ovr-sub hw-evidence-cell">${evidenceHtml(x.evidence)}</p>` : ""}</td>
      <td class="hw-wrap">${esc(dash(x.area))}</td>
      <td class="hw-wrap ovr-src mono muted">${brk(x.source)}</td></tr>`;
  }).join("") : `<tr><td colspan="5" class="muted">No risks registered.</td></tr>`;

  return `<section class="card">
    <h3>Risk register</h3>
    <div class="ovr-bar" role="group" aria-label="Risk filters">${lvlSel}${areaSel}
      <span class="muted ovr-count" id="ovr-risk-count" aria-live="polite">${int(risks.length)} of ${int(risks.length)} risk rows</span></div>
    <div class="tbl-scroll ovr-scroll">
      <p class="tbl-scroll-hint">scroll for all columns →</p>
      <div class="tbl-wrap"><table class="hw-readiness-table hw-risk-table ovr-risk-table">
        <colgroup><col style="width:12%"><col style="width:8%"><col style="width:52%">
          <col style="width:10%"><col style="width:18%"></colgroup>
        <thead><tr><th>Risk</th><th>Level</th><th>What</th><th>Area</th><th>Source</th></tr></thead>
        <tbody id="ovr-risk-body">${body}
          <tr id="ovr-no-rows" hidden><td colspan="5" class="muted">No risks match these filters.</td></tr>
        </tbody></table></div>
    </div>
  </section>`;
}

function decisionsTable(decisions) {
  const hasDecided = decisions.some(x => decidedText(x && x.decided) !== MISSING);
  // The source path is a second muted line under the recommendation: a 12-row table was paying for
  // a ~50 px column that broke every path at single characters.
  const cols = hasDecided
    ? `<col style="width:6%"><col style="width:8%"><col style="width:34%"><col style="width:34%">
       <col style="width:10%"><col style="width:8%">`
    : `<col style="width:6%"><col style="width:9%"><col style="width:40%"><col style="width:35%">
       <col style="width:10%">`;
  const body = decisions.length ? decisions.map(x => `<tr>
    <td>${esc(x.id)}</td>
    <td class="hw-wrap">${esc(dash(x.area))}</td>
    <td class="hw-wrap">${esc(x.question)}</td>
    <td class="hw-wrap">${esc(x.recommendation)}${x.source
      ? `<p class="ovr-sub ovr-dec-src mono muted">source: ${brk(x.source)}</p>` : ""}</td>
    <td>${statusPill(x)}</td>
    ${hasDecided ? `<td class="ovr-dec-nowrap">${esc(decidedText(x.decided))}</td>` : ""}</tr>`).join("")
    : `<tr><td colspan="${hasDecided ? 6 : 5}" class="muted">No decisions registered.</td></tr>`;
  const thead = hasDecided
    ? "<tr><th>#</th><th>Area</th><th>Decision</th><th>Recommendation</th><th>Status</th><th>Decided</th></tr>"
    : "<tr><th>#</th><th>Area</th><th>Decision</th><th>Recommendation</th><th>Status</th></tr>";
  return `<section class="card">
    <h3>Owner decisions</h3>
    <div class="tbl-scroll ovr-scroll">
      <p class="tbl-scroll-hint">scroll for all columns →</p>
      <div class="tbl-wrap"><table class="hw-readiness-table hw-decisions-table ovr-dec-table">
        <colgroup>${cols}</colgroup>
        <thead>${thead}</thead>
        <tbody>${body}</tbody></table></div>
    </div>
  </section>`;
}

export function healthHtml(healthFindings) {
  ensureStyle();
  const list = Array.isArray(healthFindings) ? healthFindings.filter(Boolean) : [];
  const body = list.length ? `<div class="tbl-scroll ovr-scroll">
      <p class="tbl-scroll-hint">scroll for all columns →</p>
      <div class="tbl-wrap"><table class="hw-readiness-table ovr-health-table">
        <colgroup><col style="width:12%"><col style="width:30%"><col style="width:58%"></colgroup>
        <thead><tr><th>Level</th><th>Problem</th><th>Detail</th></tr></thead><tbody>
        ${list.map(f => {
          const sev = String((f && f.severity) || "").toLowerCase();
          const st = String((f && f.status) || "open");
          const badge = st === "open" ? "" : pill(st.replace(/_/g, " "), st === "resolved" ? "good" : "warn");
          const ev = uniqueEvidence(f && f.detail, f && f.evidence)
            .map(e => `<li class="muted">${brk(e)}</li>`).join("");
          return `<tr>
            <td><span class="pill ${LVL_CLASS[sev.toUpperCase()] || ""}">${esc(sev ? sev.toUpperCase() : MISSING)}</span>${badge ? ` ${badge}` : ""}</td>
            <td class="hw-wrap"><b>${esc(f && f.title)}</b><br><span class="muted" style="font-size:.74rem">${esc((f && f.kind) || "software")}</span></td>
            <td class="hw-wrap">${f && f.detail ? `<p class="ovr-sub">${esc(f.detail)}</p>` : ""}
              ${ev ? `<ul class="ovr-ev">${ev}</ul>` : ""}</td></tr>`;
        }).join("")}
        </tbody></table></div>
    </div>`
    : `<p class="muted">No software problems detected.</p>`;
  return `<section class="card"><div class="eyebrow">Software health</div>${body}</section>`;
}

export function registryTabHtml(reg, healthFindings) {
  ensureStyle();
  const r = reg || {};
  const risks = Array.isArray(r.risks) ? r.risks.filter(Boolean) : [];
  const decisions = Array.isArray(r.decisions) ? r.decisions.filter(Boolean) : [];
  const c = r.counts || {};
  const byLevel = (c && typeof c.by_level === "object" && c.by_level) ? c.by_level : {};
  const levelPills = LEVELS.filter(l => byLevel[l] != null)
    .map(l => pill(`${l} ${int(byLevel[l])}`, LVL_CLASS[l])).join(" ");
  const riskRows = risks.length;
  const decisionRows = decisions.length;
  const countsLine = `${int(riskRows)} risks + ${int(decisionRows)} decisions = ${int(riskRows + decisionRows)} rows`;
  const origin = [];
  if (isFinite(Number(c.hw))) origin.push(`${int(c.hw)} hw`);
  if (isFinite(Number(c.project))) origin.push(`${int(c.project)} project`);
  const originLine = origin.join(" + ")
    + (c.open != null && isFinite(Number(c.open)) ? `${origin.length ? " · " : ""}${int(c.open)} open` : "");
  const head = `<div class="ovr-head">
    <div class="eyebrow">Project readiness${r.schema ? ` · ${esc(r.schema)}` : ""}</div>
    <p class="muted" style="font-size:.8rem;margin:0">Risks and owner decisions that gate the search, hardware and software work. Hardware rows are merged from the readiness registry, not duplicated.</p>
    <div class="pill-row" style="margin:4px 0 0">${pill(countsLine)}${originLine ? ` ${pill(originLine)}` : ""}${levelPills ? ` ${levelPills}` : ""}</div>
  </div>`;
  const sources = Array.isArray(r.sources) && r.sources.length
    ? `<p class="muted" style="font-size:.72rem;margin:0">sources: <span class="mono">${r.sources.map(s => brk(s)).join(" · ")}</span></p>`
    : "";
  return `${head}${errorsHtml(r.errors)}${risksTable(risks)}${decisionsTable(decisions)}${healthHtml(healthFindings)}${sources}`;
}

// Compact list for a caller-owned card/section in the Overview header, so the section heading and
// its empty-state copy stay with the page. Returns "" when there is nothing to show.
export function snapshotListHtml(snaps) {
  const list = Array.isArray(snaps) ? snaps.filter(Boolean) : [];
  if (!list.length) return "";
  ensureStyle();
  const rows = list.map(s => {
    const id = String(s.id || s.label || "");
    const href = s.href || (id ? `#/analysis/${encodeURIComponent(id)}` : "");
    const nErr = Number(s.n_errors || 0);
    const ok = nErr > 0 ? pill(`${int(nErr)} errors`, "bad") : pill("ok", "good");
    const label = esc(s.label || id || MISSING);
    const link = href ? `<a href="${esc(href)}">${label}</a>` : `<b>${label}</b>`;
    return `<li>${link}<span class="muted">generated ${esc(dash(s.generated_utc))} · ${int(s.n_sections)} sections · ${int(nErr)} errors</span>${ok}</li>`;
  }).join("");
  return `<ul class="ovr-snap-list">${rows}</ul>`;
}

export function wireRegistry(root) {
  if (!root) return;
  const lvl = root.querySelector("#ovr-lvl");
  const area = root.querySelector("#ovr-area");
  const counter = root.querySelector("#ovr-risk-count");
  const noRows = root.querySelector("#ovr-no-rows");
  const rows = [...root.querySelectorAll("#ovr-risk-body tr[data-level]")];
  const total = rows.length;
  const apply = () => {
    const L = (lvl && lvl.value ? lvl.value : "").toUpperCase();
    const A = (area && area.value ? area.value : "").toLowerCase();
    let shown = 0;
    for (const row of rows) {
      const ok = (!L || String(row.dataset.level || "").toUpperCase() === L)
        && (!A || String(row.dataset.area || "").toLowerCase() === A);
      row.hidden = !ok;
      if (ok) shown++;
    }
    if (counter) counter.textContent = `${shown.toLocaleString("en-US")} of ${total.toLocaleString("en-US")} risk rows`;
    if (noRows) noRows.hidden = !(total > 0 && shown === 0);
  };
  lvl?.addEventListener("change", apply);
  area?.addEventListener("change", apply);
  apply();
}
