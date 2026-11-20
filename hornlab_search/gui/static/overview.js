// overview.js — hornlab-search GUI   AGPL-3.0-or-later
//
// #/overview — the live project briefing (Overview phase 1). Read-only; every number comes from
// GET /api/overview (hornlab_search/gui/data_overview.py). JS only formats, sorts and filters.
//
// Tabs: Briefing (KPIs, lanes, leader per current score identity, what changed since last visit),
// Leaders (per score identity: lines of work ranked by best J, floor tie band, runs inside each
// line), Typologies (knowledge-hub family card x score identity matrix).
// View state (tab, window, legacy) lives in the URL. J is never compared across identities.

const MISSING = "—";
const esc = s => (s == null ? MISSING : String(s))
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
const brk = s => esc(s).replace(/([_\-./])/g, "$1<wbr>");
const num = (v, d = 3) => (v == null || !isFinite(v)) ? MISSING : Number(v).toFixed(d);
const int = v => (v == null || !isFinite(v)) ? MISSING : Math.round(v).toLocaleString("en-US");
const LAST_VISIT_KEY = "hornlab.overview.lastVisit";

function ago(iso) {
  if (!iso) return MISSING;
  const t = Date.parse(String(iso).endsWith("Z") || /[+-]\d\d:\d\d$/.test(iso) ? iso : iso + "Z");
  if (!isFinite(t)) return esc(iso);
  const m = (Date.now() - t) / 60000;
  if (m < 1) return "just now";
  if (m < 60) return `${Math.round(m)} min ago`;
  if (m < 48 * 60) return `${Math.round(m / 60)} h ago`;
  return `${Math.round(m / 1440)} d ago`;
}
const tsOf = iso => { const t = Date.parse(iso && !/Z$|[+-]\d\d:\d\d$/.test(iso) ? iso + "Z" : iso); return isFinite(t) ? t : 0; };

function store(get, val) {
  try { if (get) return localStorage.getItem(LAST_VISIT_KEY); localStorage.setItem(LAST_VISIT_KEY, val); }
  catch { /* private window / blocked storage: the page works without it */ }
  return null;
}

const STYLE = `
.ov-tabs{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.ov-tabs .sp{flex:1}
.ov-ctl{display:flex;gap:8px;align-items:center;font-size:.8rem}
.ov-ctl select{font:inherit}
.ov-grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.ov-ident h3{margin:0 0 2px;font-size:1rem}
.ov-ident .meta{font-size:.76rem}
.ov-lead{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;margin-top:8px}
.ov-lead b{font-family:var(--f-display);font-size:1.4rem;font-weight:500}
.ov-tbl td,.ov-tbl th{padding:5px 8px;font-size:.82rem;vertical-align:top}
.ov-tbl td.r,.ov-tbl th.r{text-align:right;font-variant-numeric:tabular-nums}
.ov-tbl tr.tie td:first-child{box-shadow:inset 3px 0 0 var(--accent)}
.ov-tbl tr.probe td{color:var(--muted)}
.ov-runs{margin:4px 0 0;padding-left:16px;font-size:.76rem}
.ov-runs li{margin:2px 0}
.ov-dots{width:100%;height:auto;display:block;margin:6px 0 4px}
.ov-dots .band{fill:var(--accent-soft)}
.ov-dots .dot{fill:var(--muted)} .ov-dots .dot.tie{fill:var(--accent)}
.ov-dots text{font-size:10px;fill:var(--muted);font-family:var(--f-mono)}
.ov-dots .axis{stroke:var(--rule)}
.ov-mx td{text-align:center} .ov-mx td.l,.ov-mx th.l{text-align:left}
.ov-mx .cell{display:inline-grid;gap:1px;min-width:64px}
.ov-mx .cell b{font-size:.9rem} .ov-mx .cell small{font-size:.7rem}
.ov-mx .lead b{color:var(--good)} .ov-mx .tie b{color:var(--accent)}
.ov-chg li{margin:3px 0}
details.ov-line summary{cursor:pointer}
`;

function ensureStyle() {
  if (document.getElementById("ov-style")) return;
  const s = document.createElement("style"); s.id = "ov-style"; s.textContent = STYLE;
  document.head.appendChild(s);
}

const pill = (t, cls = "", title = "") => `<span class="pill ${cls}"${title ? ` title="${esc(title)}"` : ""}>${t}</span>`;
const kpi = (label, value, sub = "", cls = "") =>
  `<div class="kpi"><span>${esc(label)}</span><b class="${cls}">${esc(value)}</b>${sub ? `<small class="muted" style="font-size:.72rem">${sub}</small>` : ""}</div>`;
const STATUS_PILL = { current: "good", diagnostic: "warn", unregistered: "warn", legacy: "" };
const STATUS_TIP = {
  current: "In active use; listed in examples/score_identities.yaml.",
  diagnostic: "Pilot / probe identity: read as diagnostic, not a leaderboard.",
  unregistered: "Not in examples/score_identities.yaml: no floor, so no tie band.",
  legacy: "Objective version below the current default; hidden unless 'show legacy' is on.",
};
const runLink = (id, label) => id ? `<a href="#/run/${encodeURIComponent(id)}">${label ?? brk(id)}</a>` : MISSING;

function parseQuery(q) {
  const p = new URLSearchParams(q || "");
  const days = Number(p.get("days"));
  return { tab: ["briefing", "leaders", "typologies"].includes(p.get("tab")) ? p.get("tab") : "briefing",
           days: isFinite(days) && days > 0 ? days : 14, legacy: p.get("legacy") === "1",
           ident: p.get("ident") || "" };
}
function hashFor(s) {
  const p = new URLSearchParams({ tab: s.tab, days: String(s.days) });
  if (s.legacy) p.set("legacy", "1");
  if (s.ident) p.set("ident", s.ident);
  return "#/overview?" + p.toString();
}

// ── Leaders ────────────────────────────────────────────────────────────────

/** Dot strip of ranked lines' best J, leader at left, floor band shaded. Same-identity only. */
function dotsSvg(ident) {
  const ranked = (ident.lines || []).filter(l => l.rank);
  if (ranked.length < 2) return "";
  const W = 560, H = 54, L = 12, R = 12;
  const lo = ranked[0].best_j, hi = ranked[ranked.length - 1].best_j;
  const span = Math.max(hi - lo, ident.floor_j || 0, 1e-9);
  const x = v => L + (v - lo) / span * (W - L - R);
  const band = ident.floor_j != null ? `<rect class="band" x="${x(lo)}" y="8" width="${Math.max(2, x(lo + ident.floor_j) - x(lo))}" height="26"><title>tie band: within ${num(ident.floor_j, 4)} J (published floor) of the leader</title></rect>` : "";
  const dots = ranked.map((l, i) => `<circle class="dot${l.tie ? " tie" : ""}" cx="${x(l.best_j)}" cy="${21 + ((i % 3) - 1) * 7}" r="5"><title>#${l.rank} ${esc(l.construction)} · J ${num(l.best_j)}</title></circle>`).join("");
  return `<svg class="ov-dots" viewBox="0 0 ${W} ${H}" role="img" aria-label="best J of each line of work, lower is better">
    ${band}<line class="axis" x1="${L}" x2="${W - R}" y1="40" y2="40"/>${dots}
    <text x="${L}" y="52">${num(lo)} (lead)</text><text x="${W - R}" y="52" text-anchor="end">${num(lo + span)}</text></svg>`;
}

function lineRow(l, ident) {
  const badges = [l.tie ? pill("tie", "", "within the published floor of the leader") : "",
    l.active ? pill("running", "warn") : "", l.verified ? pill("verified", "good") : "",
    l.probe_only ? pill("probes only", "", "every run had fewer valid evaluations than the leaderboard minimum") : ""].join(" ");
  const runs = l.runs.map(r => `<li>${runLink(r.id, brk(r.name || r.id))} · J ${num(r.best_j)} · ${int(r.n_ok)}/${int(r.n)} valid${r.refused ? ` · ${int(r.refused)} refused` : ""} · ${ago(r.last)}${r.probe ? " · probe" : ""}${r.mode === "verify" ? " · verify" : ""}</li>`).join("");
  return `<tr class="${l.tie ? "tie" : ""}${l.probe_only ? " probe" : ""}">
    <td class="r">${l.rank ?? MISSING}</td>
    <td><details class="ov-line"><summary><b>${esc(l.construction)}</b> <span class="muted">· ${esc(l.card_label)}</span> ${badges}</summary>
      <ul class="ov-runs">${runs}</ul></details></td>
    <td class="r mono">${num(l.best_j)}</td>
    <td class="r mono">${l.gap == null ? MISSING : l.rank === 1 ? "lead" : "+" + num(l.gap)}</td>
    <td class="r">${int(l.valid)}</td>
    <td class="r">${l.refused_pct == null ? MISSING : l.refused_pct + "%"}</td>
    <td class="r">${l.runs.length}</td>
    <td>${ago(l.last)}</td>
    <td>${runLink(l.best_run_id, "best run →")}</td></tr>`;
}

function identityCard(ident) {
  const lead = (ident.lines || []).find(l => l.rank === 1);
  return `<section class="card ov-ident" id="ov-${esc(ident.id)}">
    <div class="eyebrow">score identity · v${esc(ident.objective_version)}</div>
    <h3>${esc(ident.label)} ${pill(esc(ident.status), STATUS_PILL[ident.status] || "", STATUS_TIP[ident.status])}</h3>
    <p class="meta muted mono">${brk(ident.brief)} · ${int(ident.runs)} runs · ${int(ident.evals)} evals${ident.probes ? ` · ${int(ident.probes)} probe runs` : ""} · floor ${ident.floor_j == null ? "not published" : num(ident.floor_j, 4) + " J"}${ident.bar_j != null ? ` · bar ${num(ident.bar_j, 4)}` : ""}</p>
    ${lead ? `<div class="ov-lead"><span class="muted">leader</span><b class="mono">${num(lead.best_j)}</b><span>${esc(lead.construction)}</span>
      ${ident.n_tied != null ? `<span class="muted">${ident.n_tied} line${ident.n_tied === 1 ? "" : "s"} inside one floor${ident.n_tied > 1 ? " — a tie: ranking them needs verify solves, not more screen evals" : ""}</span>` : ""}</div>` : `<p class="muted">No line has ${"≥"} the minimum valid evaluations yet.</p>`}
    ${dotsSvg(ident)}
    <div class="tbl-wrap"><table class="ov-tbl"><thead><tr><th class="r">#</th><th>Line of work (construction · family card)</th><th class="r">best J</th><th class="r">gap</th><th class="r">valid</th><th class="r">refused</th><th class="r">runs</th><th>last</th><th></th></tr></thead>
      <tbody>${(ident.lines || []).map(l => lineRow(l, ident)).join("")}</tbody></table></div>
    ${ident.source ? `<p class="muted" style="font-size:.72rem;margin:6px 0 0">source: <span class="mono">${brk(ident.source)}</span></p>` : ""}
  </section>`;
}

function leadersTab(d, s) {
  const ids = d.identities || [];
  const sel = s.ident ? ids.filter(i => i.id === s.ident) : ids;
  const opts = [`<option value="">all identities (${ids.length})</option>`].concat(ids.map(i =>
    `<option value="${esc(i.id)}"${i.id === s.ident ? " selected" : ""}>${esc(i.label)}</option>`)).join("");
  return `<div class="ov-ctl"><label>Show <select id="ov-ident">${opts}</select></label>
      <span class="muted">Lines of work = every run of one construction under one score. Rows with a left bar are ties with the leader. Click a line to see its runs.</span></div>
    ${sel.length ? sel.map(identityCard).join("") : `<p class="muted">No runs in this window.</p>`}`;
}

// ── Typologies ─────────────────────────────────────────────────────────────

function typologiesTab(d) {
  const ids = (d.identities || []).filter(i => i.status !== "legacy");
  const rows = (d.typology || []).map(c => `<tr>
    <td class="l"><b>${esc(c.label)}</b><br><small class="muted">${c.constructions.map(esc).join(", ")}</small>${c.doc ? `<br><small class="muted mono" title="knowledge-hub family card">${brk(c.doc)}</small>` : ""}</td>
    <td class="r">${int(c.evals)}</td>
    ${ids.map(i => {
      const cell = c.cells[i.id];
      if (!cell) return `<td class="muted">${MISSING}</td>`;
      const cls = cell.rank === 1 ? "lead" : cell.tie ? "tie" : "";
      return `<td><a class="cell ${cls}" href="${hashFor({ tab: "leaders", days: d.days, legacy: d.show_legacy, ident: i.id })}"><b>#${cell.rank}<small class="muted"> / ${cell.of}</small></b><small class="mono">${num(cell.best_j)}</small><small class="muted">${esc(cell.construction)}</small></a></td>`;
    }).join("")}</tr>`).join("");
  return `<section class="card"><div class="eyebrow">Typologies × score identities</div>
    <p class="muted" style="font-size:.8rem">Best rank of each knowledge-hub family inside each score identity (green = leads, accent = inside the leader's floor). Ranks compare lines within one column only — never across columns. Family targets differ: read the family card before applying one family's heuristics to another.</p>
    <div class="tbl-wrap"><table class="ov-tbl ov-mx"><thead><tr><th class="l">Family card</th><th class="r">evals</th>${ids.map(i => `<th title="${esc(i.brief)}">${esc(i.label)}</th>`).join("")}</tr></thead>
    <tbody>${rows || `<tr><td class="muted">No runs in this window.</td></tr>`}</tbody></table></div></section>`;
}

// ── Briefing ───────────────────────────────────────────────────────────────

function lanesHtml(lanes) {
  if (!lanes || lanes.error) return `<p class="muted">Lane status unavailable${lanes && lanes.error ? `: ${esc(lanes.error)}` : ""}.</p>`;
  return `<div class="tbl-wrap"><table class="ov-tbl"><thead><tr><th>Lane</th><th>Lock</th><th>Job</th><th class="r">rows</th><th class="r">best J</th><th>newest row</th><th></th></tr></thead><tbody>
    ${(lanes.lanes || []).map(l => {
      const run = l.run || {};
      return `<tr><td class="mono">${esc(String(l.lane).toUpperCase())}</td>
        <td>${l.lock ? (l.lock.alive ? pill("live", "warn") : pill("stale", "bad")) : pill("free", "good")}</td>
        <td>${l.job ? `<b>${brk(l.job.name)}</b><br><small class="muted">${l.queue_log ? brk(l.queue_log.name) : ""}</small>` : `<span class="muted">idle</span>`}</td>
        <td class="r">${l.job ? int(run.n_rows) : MISSING}</td><td class="r mono">${l.job ? num(run.best_j) : MISSING}</td>
        <td>${l.job && run.newest_row_age_min != null ? `${num(run.newest_row_age_min, 0)} min ago` : MISSING}${l.alert ? ` ${pill("alert", "bad", l.alert.reason)}` : ""}</td>
        <td>${run.id ? runLink(run.id, "open run →") : ""}</td></tr>`;
    }).join("")}</tbody></table></div>`;
}

function briefingTab(d, lastVisit) {
  const k = d.kpis || {}, rd = d.readiness || {};
  const cur = (d.identities || []).filter(i => i.status === "current");
  const leaderRows = cur.map(i => {
    const lead = (i.lines || []).find(l => l.rank === 1);
    return `<tr><td><a href="${hashFor({ tab: "leaders", days: d.days, legacy: d.show_legacy, ident: i.id })}">${esc(i.label)}</a></td>
      <td>${lead ? `<b>${esc(lead.construction)}</b> <span class="muted">· ${esc(lead.card_label)}</span>` : MISSING}</td>
      <td class="r mono">${lead ? num(lead.best_j) : MISSING}</td>
      <td>${i.n_tied == null ? `<span class="muted" title="no published floor">no floor</span>` : i.n_tied > 1 ? pill(`${i.n_tied}-way tie`, "warn", "several lines within one floor: verify before ranking") : pill("clear lead", "good")}</td>
      <td class="r">${int(i.evals)}</td><td>${ago(i.last)}</td></tr>`;
  }).join("");
  // What changed since the viewer's last visit (browser-local; no visit = last 24 h).
  const since = lastVisit ? Number(lastVisit) : Date.now() - 86400000;
  const changed = [];
  for (const i of d.identities || []) for (const l of i.lines || []) {
    const fresh = (l.runs || []).filter(r => tsOf(r.last) > since);
    if (!fresh.length) continue;
    const newBest = fresh.some(r => r.id === l.best_run_id);
    changed.push({ i, l, fresh, newBest, t: Math.max(...fresh.map(r => tsOf(r.last))) });
  }
  changed.sort((a, b) => (b.newBest - a.newBest) || (b.t - a.t));
  const chg = changed.slice(0, 12).map(({ i, l, fresh, newBest }) =>
    `<li>${fresh.length === l.runs.length ? pill("new line", "good", "every run of this line is new") : newBest ? pill("new best", "good", "the line's best run is new") : pill("updated")} <b>${esc(l.construction)}</b> in <a href="${hashFor({ tab: "leaders", days: d.days, legacy: d.show_legacy, ident: i.id })}">${esc(i.label)}</a> — best ${num(l.best_j)}${l.rank ? ` (#${l.rank}${l.tie ? ", tie" : ""})` : ""} · ${fresh.length} run${fresh.length === 1 ? "" : "s"}</li>`).join("");
  return `<div class="kpis">
      ${kpi("Runs in window", int(k.runs), `${int(k.runs_24h)} in the last 24 h`)}
      ${kpi("Evaluations", int(k.evals), `${int(k.evals_24h)} in the last 24 h`)}
      ${kpi("Refused", k.refused_pct == null ? MISSING : k.refused_pct + "%", `${int(k.refused)} never reached the solver`, k.refused_pct >= 25 ? "warn" : "")}
      ${kpi("Running now", int(k.active_runs), "runs with a row in the last 2 min")}
      ${kpi("Open decisions", rd.open_decisions ?? MISSING, `<a href="#/hw/readiness">readiness →</a>`, rd.open_decisions ? "warn" : "good")}
      ${kpi("Critical risks", rd.risks_critical ?? MISSING, `${rd.risks_open ?? MISSING} open risks`, rd.risks_critical ? "bad" : "good")}
    </div>
    <section class="card"><div class="eyebrow">Solve lanes</div>${lanesHtml(d.lanes)}</section>
    <section class="card"><div class="eyebrow">Leader per current score identity</div>
      <p class="muted" style="font-size:.8rem">One row per score; J is comparable only within a row's own leaderboard.</p>
      <div class="tbl-wrap"><table class="ov-tbl"><thead><tr><th>Score identity</th><th>Leading line</th><th class="r">best J</th><th>standing</th><th class="r">evals</th><th>last</th></tr></thead>
      <tbody>${leaderRows || `<tr><td class="muted" colspan="6">No current identity has runs in this window.</td></tr>`}</tbody></table></div></section>
    <section class="card"><div class="eyebrow">What changed ${lastVisit ? `since your last visit (${ago(new Date(since).toISOString())})` : "in the last 24 h"}</div>
      ${chg ? `<ul class="ov-chg">${chg}</ul>${changed.length > 12 ? `<p class="muted">${changed.length - 12} more lines updated — see Leaders.</p>` : ""}` : `<p class="muted">Nothing new.</p>`}</section>`;
}

// ── View ───────────────────────────────────────────────────────────────────

export async function viewOverview(root, query = "") {
  ensureStyle();
  const s = parseQuery(query);
  const lastVisit = store(true);
  root.setAttribute("aria-busy", "true");
  root.innerHTML = `<div class="stack" style="gap:18px;opacity:.6" aria-hidden="true">
    <div class="skeleton-block" style="height:2.2rem;width:min(260px,60%)"></div>
    <div class="skeleton-block" style="height:180px"></div></div><p class="sr-only" role="status">Loading overview…</p>`;
  let d;
  try {
    const r = await fetch(`/api/overview?days=${encodeURIComponent(s.days)}${s.legacy ? "&legacy=1" : ""}`);
    if (!r.ok) throw new Error(r.status + " " + ((await r.json().catch(() => ({}))).error || ""));
    d = await r.json();
  } catch (e) {
    root.removeAttribute("aria-busy");
    root.innerHTML = `<div class="alert error" role="alert"><b>Error:</b> ${esc(e.message)}</div>`;
    return;
  }
  root.removeAttribute("aria-busy");
  if (s.tab === "briefing") store(false, String(Date.now()));
  const tabBtn = (t, label) => `<a class="btn btn-sm" href="${hashFor({ ...s, tab: t })}"${s.tab === t ? ` aria-current="page" style="border-color:var(--accent);color:var(--accent)"` : ""}>${label}</a>`;
  const dayOpts = [1, 3, 7, 14, 30, 90].map(n => `<option value="${n}"${n === s.days ? " selected" : ""}>last ${n} day${n === 1 ? "" : "s"}</option>`).join("");
  const body = s.tab === "leaders" ? leadersTab(d, s) : s.tab === "typologies" ? typologiesTab(d) : briefingTab(d, lastVisit);
  root.innerHTML = `<div class="stack" style="gap:18px">
    <div><div class="eyebrow">Overview · live from runs/</div><h2>Project overview</h2>
      <p class="hw-story">Where the search stands: leaders per score identity, families against each score, and what changed. Rolled up by line of work, not run folder.</p>
      <div class="pill-row" style="margin:8px 0 0">${pill(`generated ${esc(d.generated_utc)}`)} ${pill(`${int(d.kpis && d.kpis.runs)} runs since ${esc(String(d.since_utc).slice(0, 10))}`)} ${pill(`leaders need ≥ ${esc(d.registry.min_valid_for_leader)} valid evals`)} ${pill(`${esc(d.elapsed_s)} s`)}</div></div>
    ${d.registry.error ? `<div class="alert error" role="alert"><b>Score identity registry:</b> ${esc(d.registry.error)}</div>` : ""}
    <div class="ov-tabs" role="navigation" aria-label="Overview tabs">${tabBtn("briefing", "Briefing")}${tabBtn("leaders", "Leaders")}${tabBtn("typologies", "Typologies")}
      <span class="sp"></span>
      <label class="ov-ctl">Window <select id="ov-days">${dayOpts}</select></label>
      <label class="ov-ctl"><input type="checkbox" id="ov-legacy"${s.legacy ? " checked" : ""}> show legacy scores</label></div>
    ${body}
  </div>`;
  root.querySelector("#ov-days").addEventListener("change", e => { location.hash = hashFor({ ...s, days: Number(e.target.value) }); });
  root.querySelector("#ov-legacy").addEventListener("change", e => { location.hash = hashFor({ ...s, legacy: e.target.checked }); });
  const sel = root.querySelector("#ov-ident");
  if (sel) sel.addEventListener("change", e => { location.hash = hashFor({ ...s, ident: e.target.value }); });
}
