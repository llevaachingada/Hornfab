// overview.js — hornlab-search GUI   AGPL-3.0-or-later
//
// #/overview — the live project briefing (Overview phase 1). Read-only; every number comes from
// GET /api/overview (hornlab_search/gui/data_overview.py). JS only formats, sorts and filters.
//
// Tabs: Briefing (KPIs, lanes, leader per current score identity, what changed since last visit),
// Leaders (per score identity: lines of work ranked by best J, floor tie band, runs inside each
// line), Typologies (knowledge-hub family card x score identity matrix), Next (ranked findings),
// Decisions (project readiness registry + software health).
// View state (tab, window, legacy, filters) lives in the URL. J is never compared across identities.

import { findingsTabHtml, wireFindings } from "./overview_findings.js";
import { paramsTabHtml, wireParams } from "./overview_params.js";
import { registryTabHtml, snapshotListHtml, wireRegistry } from "./overview_registry.js";

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
.ov-tabctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
@media (max-width:640px){.ov-tabs .sp{display:none}.ov-tabctl{flex-basis:100%;justify-content:flex-start}}
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
.ov-fam{display:grid;grid-template-columns:minmax(180px,260px) 1fr;gap:10px;padding:9px 0;border-top:1px solid var(--rule)}
.ov-fam:first-of-type{border-top:0}
@media (max-width:760px){.ov-fam{grid-template-columns:1fr}}
.ov-chips{display:flex;flex-wrap:wrap;gap:6px;align-content:flex-start}
.ov-chip{display:inline-flex;gap:5px;align-items:baseline;padding:3px 8px;border:1px solid var(--rule);border-radius:999px;font-size:.78rem;text-decoration:none;color:inherit}
.ov-chip:hover{border-color:var(--accent)}
.ov-chip.lead{border-color:var(--good)} .ov-chip.lead b{color:var(--good)} .ov-chip.tie b{color:var(--accent)}
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
const STATE_PILL = { converged: "good", improving: "warn", box_limited: "", refusal_storm: "bad",
  probe: "", stale: "" };
const STATE_TIP = {
  converged: "The budget rule is closed and the line is not box-limited or stale.",
  improving: "Still improving in the last 20% of its budget: more evals may pay.",
  box_limited: "A walls proposal says a bound is binding: widen before adding budget.",
  refusal_storm: "At least 40% of evaluations never reached the solver.",
  probe: "Every run had fewer valid evaluations than the leaderboard minimum.",
  stale: "Top-3 line with no row for more than 7 days.",
};
const STATUS_TIP = {
  current: "In active use; listed in examples/score_identities.yaml.",
  diagnostic: "Pilot / probe identity: read as diagnostic, not a leaderboard.",
  unregistered: "Not in examples/score_identities.yaml: no floor, so no tie band.",
  legacy: "Objective version below the current default; hidden unless 'show legacy' is on.",
};
const runLink = (id, label) => id ? `<a href="#/run/${encodeURIComponent(id)}">${label ?? brk(id)}</a>` : MISSING;

const TABS = ["briefing", "leaders", "typologies", "next", "decisions", "params"];

function parseQuery(q) {
  const p = new URLSearchParams(q || "");
  const days = Number(p.get("days"));
  return { tab: TABS.includes(p.get("tab")) ? p.get("tab") : "briefing",
           days: isFinite(days) && days > 0 ? days : 14, legacy: p.get("legacy") === "1",
           ident: p.get("ident") || "",
           kind: p.get("kind") || "", card: p.get("card") || "",
           status: ["open", "resolved", "all", "dismissed"].includes(p.get("status")) ? p.get("status") : "open",
           sort: ["priority", "newest", "identity"].includes(p.get("sort")) ? p.get("sort") : "priority",
           q: p.get("q") || "", view: p.get("view") === "matrix" ? "matrix" : "" };
}
function hashFor(s) {
  const p = new URLSearchParams({ tab: s.tab, days: String(s.days) });
  if (s.legacy) p.set("legacy", "1");
  if (s.ident) p.set("ident", s.ident);
  if (s.kind) p.set("kind", s.kind);
  if (s.card) p.set("card", s.card);
  if (s.status && s.status !== "open") p.set("status", s.status);
  if (s.sort && s.sort !== "priority") p.set("sort", s.sort);
  if (s.q) p.set("q", s.q);
  if (s.view) p.set("view", s.view);
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
  const badges = [l.state ? pill(esc(l.state), STATE_PILL[l.state] || "", STATE_TIP[l.state] || "") : "",
    l.tie ? pill("tie", "", "within the published floor of the leader") : "",
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

// Default: one row per family with its standings as wrapping chips (fits any width). The original
// family x identity matrix is one click away (?view=matrix); it scrolls sideways by design.
function typologiesTab(d, view = "") {
  const ids = (d.identities || []).filter(i => i.status !== "legacy");
  if (view !== "matrix") return typologiesList(d, ids);
  return typologiesMatrix(d, ids);
}

function typologiesList(d, ids) {
  const fams = (d.typology || []).map(c => {
    const cells = ids.map(i => ({ i, cell: c.cells[i.id] })).filter(x => x.cell)
      .sort((a, b) => a.cell.rank - b.cell.rank || a.cell.of - b.cell.of);
    const best = cells[0] ? cells[0].cell.rank : 99;
    return { c, cells, best, leads: cells.filter(x => x.cell.rank === 1).length };
  }).sort((a, b) => b.leads - a.leads || a.best - b.best || String(a.c.label).localeCompare(String(b.c.label)));
  const chip = ({ i, cell }) => {
    const tone = cell.rank === 1 ? "lead" : cell.tie ? "tie" : "";
    const tip = `${i.label}: rank ${cell.rank} of ${cell.of}, best J ${num(cell.best_j)} (${cell.construction})${cell.state ? `, ${cell.state}` : ""}. J is comparable only inside this score.`;
    return `<a class="ov-chip ${tone}" href="${hashFor({ tab: "leaders", days: d.days, legacy: d.show_legacy, ident: i.id })}" title="${esc(tip)}"><b>#${cell.rank}<small class="muted">/${cell.of}</small></b> ${esc(i.label)}${cell.state ? ` ${pill(esc(cell.state), STATE_PILL[cell.state] || "", STATE_TIP[cell.state] || "")}` : ""}</a>`;
  };
  const rows = fams.map(({ c, cells, leads }) => `<div class="ov-fam">
      <div class="ov-fam-h"><b>${esc(c.label)}</b> <span class="muted">· ${int(c.evals)} evals${leads ? ` · <span style="color:var(--good)">leads ${leads} score${leads === 1 ? "" : "s"}</span>` : ""}</span>
        <br><small class="muted">${c.constructions.map(esc).join(", ")}</small></div>
      <div class="ov-chips">${cells.length ? cells.map(chip).join("") : `<span class="muted">no runs in this window</span>`}</div></div>`).join("");
  return `<section class="card"><div class="eyebrow">Typologies · where each family stands</div>
    <p class="muted" style="font-size:.8rem">One row per design family, best first. Each chip is the family's rank inside one score (green = leads that score). Ranks compare designs within one score only, never across scores. Hover a chip for details; click it for that score's leaderboard.
      <a href="${hashFor({ tab: "typologies", days: d.days, legacy: d.show_legacy, view: "matrix" })}">Show full matrix →</a></p>
    ${rows || `<p class="muted">No runs in this window.</p>`}</section>`;
}

function typologiesMatrix(d, ids) {
  const rows = (d.typology || []).map(c => `<tr>
    <td class="l"><b>${esc(c.label)}</b><br><small class="muted">${c.constructions.map(esc).join(", ")}</small>${c.doc ? `<br><small class="muted mono" title="knowledge-hub family card">${brk(c.doc)}</small>` : ""}</td>
    <td class="r">${int(c.evals)}</td>
    ${ids.map(i => {
      const cell = c.cells[i.id];
      if (!cell) return `<td class="muted">${MISSING}</td>`;
      const cls = cell.rank === 1 ? "lead" : cell.tie ? "tie" : "";
      return `<td><a class="cell ${cls}" href="${hashFor({ tab: "leaders", days: d.days, legacy: d.show_legacy, ident: i.id })}"><b>#${cell.rank}<small class="muted"> / ${cell.of}</small></b><small class="mono">${num(cell.best_j)}</small><small class="muted">${esc(cell.construction)}</small>${cell.state ? `<small>${pill(esc(cell.state), STATE_PILL[cell.state] || "", STATE_TIP[cell.state] || "")}</small>` : ""}</a></td>`;
    }).join("")}</tr>`).join("");
  return `<section class="card"><div class="eyebrow">Typologies × score identities</div>
    <p style="font-size:.8rem"><a href="${hashFor({ tab: "typologies", days: d.days, legacy: d.show_legacy })}">← Back to the compact list</a> · this matrix scrolls sideways.</p>
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

// Research snapshot (M1): a read-only, sourced research view built by a CPU-only job.
function researchCardHtml(rs = []) {
  const latest = rs[0];
  const sev = h => h.severity === "decision" ? "good" : "warn";
  const latestHtml = latest ? `
    <p style="margin:6px 0"><a class="btn btn-sm" href="${esc(latest.href)}" target="_blank" rel="noopener">Open research report ↗</a>
      <span class="muted" style="font-size:.78rem">cutoff ${esc(latest.cutoff_utc)} · snapshot <span class="mono">${esc(latest.snapshot_id)}</span> · ${int(latest.counts.findings)} findings · ${int(latest.counts.cohorts)} cohorts · ${int(latest.counts.sources)} sources</span></p>
    <ul class="ov-chg">${(latest.headlines || []).map(h => `<li>${pill(h.severity === "decision" ? "decision" : "data quality", sev(h))} <b>${esc(h.title)}</b><br><span class="muted">${esc(h.plain)}</span></li>`).join("")}</ul>
    <p class="muted" style="font-size:.76rem">For agents: <a href="${esc(latest.files["summary.json"])}" target="_blank" rel="noopener">summary.json</a> · <a href="${esc(latest.files["AGENT_GUIDE.md"])}" target="_blank" rel="noopener">AGENT_GUIDE.md</a> · <a href="${esc(latest.files["snapshot.json"])}" target="_blank" rel="noopener">snapshot.json</a> · on disk: <span class="mono">runs/${esc(latest.path)}/</span> (also rows.ndjson, findings.ndjson). ${int(latest.n_next_steps)} suggested next steps, each labelled for GPU use and owner approval; none run automatically.</p>
    ${rs.length > 1 ? `<details><summary class="muted" style="font-size:.78rem">${rs.length - 1} earlier research snapshot${rs.length === 2 ? "" : "s"}</summary><ul class="ov-chg">${rs.slice(1, 8).map(x => `<li><a href="${esc(x.href)}" target="_blank" rel="noopener">${esc(x.id)}</a> <span class="muted">cutoff ${esc(x.cutoff_utc)} · ${int(x.counts.findings)} findings</span></li>`).join("")}</ul></details>` : ""}`
    : `<p class="muted">No research snapshot yet. "Generate research snapshot" builds one in about 10–20 s (CPU only, read-only).</p>`;
  return `<section class="card" id="ov-research"><div class="eyebrow">Research snapshot · decisions with sources</div>
    <p class="muted" style="font-size:.8rem;margin:4px 0">Freezes the committed evidence and the run archive at a cutoff, then explains it three ways: plain-language summary, engineering drilldowns where every number links to its source, and machine-readable files for planning agents. Never compares J across score identities; starts no work.</p>
    <div class="pill-row" style="margin:6px 0"><button class="btn btn-sm" id="ov-research-go">Generate research snapshot</button>
      <label class="ov-ctl" style="font-size:.78rem">cutoff <input id="ov-research-cutoff" type="text" placeholder="now" size="22" aria-label="Research snapshot cutoff (now or an ISO-8601 UTC time)"></label>
      <span class="muted" style="font-size:.76rem" id="ov-research-msg" role="status" aria-live="polite">CPU-only; never takes the GPU lock. Leave cutoff empty for now, or e.g. 2026-11-25T23:59:59Z to reproduce.</span></div>
    ${latestHtml}</section>`;
}

function wireResearch(root, onDone) {
  const btn = root.querySelector("#ov-research-go");
  if (!btn) return;
  const done = sessionStorage.getItem("ov-research-done");
  if (done) {                                       // survive the re-render that shows the new snapshot
    sessionStorage.removeItem("ov-research-done");
    const m = root.querySelector("#ov-research-msg");
    if (m) m.textContent = done;
  }
  btn.addEventListener("click", async () => {
    const msg = root.querySelector("#ov-research-msg");
    const cutoff = (root.querySelector("#ov-research-cutoff") || {}).value || "";
    const say = t => { if (msg) msg.textContent = t; };
    btn.disabled = true;
    say("Starting research snapshot job…");
    try {
      const r = await fetch("/api/jobs", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: "research-snapshot", args: cutoff.trim() ? { cutoff: cutoff.trim() } : {} }) });
      const out = await r.json().catch(() => ({}));
      if (!r.ok || out.error) { say(`Refused: ${out.error || r.status}`); btn.disabled = false; return; }
      say(`Research snapshot job ${out.id} ${out.status}…`);
      const t0 = Date.now();
      while (Date.now() - t0 < 180000) {
        await new Promise(res => setTimeout(res, 1500));
        const j = await fetch(`/api/job/${encodeURIComponent(out.id)}`).then(x => x.json()).catch(() => null);
        if (!j || j.error) continue;
        if (j.status === "done") {
          sessionStorage.setItem("ov-research-done", `Research snapshot ready (job ${out.id}, ${Math.round((Date.now() - t0) / 1000)} s). Newest shown below.`);
          onDone(); return;
        }
        if (j.status === "failed") {
          const tail = String(j.log_tail || "").trim().split("\n").slice(-2).join(" ");
          say(`Failed (exit ${j.returncode}): ${tail || "see the Jobs page"}`); btn.disabled = false; return;
        }
        say(`Research snapshot job ${out.id} ${j.status}… ${Math.round((Date.now() - t0) / 1000)} s`);
      }
      say(`Still running after 3 min; check the Jobs page for job ${out.id}.`);
    } catch (e) {
      say(`Refused: ${e.message}`);
    }
    btn.disabled = false;
  });
}

function briefingTab(d, lastVisit, snaps = [], rsnaps = []) {
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
      ${chg ? `<ul class="ov-chg">${chg}</ul>${changed.length > 12 ? `<p class="muted">${changed.length - 12} more lines updated — see Leaders.</p>` : ""}` : `<p class="muted">Nothing new.</p>`}</section>
    ${researchCardHtml(rsnaps)}
    <section class="card"><div class="eyebrow">Frozen snapshots</div>
      ${snapshotListHtml(snaps) || `<p class="muted">No snapshot yet. "Generate snapshot" writes one under <span class="mono">runs/analysis/overview_&lt;date&gt;/</span> (CPU only).</p>`}</section>`;
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
  let d, fd = null, reg = null, health = [], snaps = [], pd = null, rsnaps = [];
  const qs = `days=${encodeURIComponent(s.days)}${s.legacy ? "&legacy=1" : ""}`;
  const getJson = async url => {
    const r = await fetch(url);
    if (!r.ok) throw new Error(r.status + " " + ((await r.json().catch(() => ({}))).error || ""));
    return r.json();
  };
  try {
    d = await getJson(`/api/overview?${qs}`);
    if (s.tab === "next") {
      fd = await getJson(`/api/overview/findings?${qs}`);
    } else if (s.tab === "decisions") {
      [reg, health] = await Promise.all([
        getJson("/api/overview/registry"),
        getJson(`/api/overview/health?${qs}`).then(h => h.findings || []).catch(() => []),
      ]);
    } else if (s.tab === "params") {
      pd = await getJson(`/api/overview/params?${qs}`);
    }
    if (s.tab === "briefing") {
      [snaps, rsnaps] = await Promise.all([
        getJson("/api/overview/snapshots").then(x => x.snapshots || []).catch(() => []),
        getJson("/api/research/snapshots").then(x => x.snapshots || []).catch(() => []),
      ]);
    }
  } catch (e) {
    root.removeAttribute("aria-busy");
    root.innerHTML = `<div class="alert error" role="alert"><b>Error:</b> ${esc(e.message)}</div>`;
    return;
  }
  root.removeAttribute("aria-busy");
  if (s.tab === "briefing") store(false, String(Date.now()));
  const tabBtn = (t, label) => `<a class="btn btn-sm" href="${hashFor({ ...s, tab: t })}"${s.tab === t ? ` aria-current="page" style="border-color:var(--accent);color:var(--accent)"` : ""}>${label}</a>`;
  const dayOpts = [1, 3, 7, 14, 30, 90].map(n => `<option value="${n}"${n === s.days ? " selected" : ""}>last ${n} day${n === 1 ? "" : "s"}</option>`).join("");
  const body = s.tab === "leaders" ? leadersTab(d, s)
    : s.tab === "typologies" ? typologiesTab(d, s.view)
      : s.tab === "next" ? findingsTabHtml(fd, s)
        : s.tab === "decisions" ? registryTabHtml(reg, health)
          : s.tab === "params" ? paramsTabHtml(pd)
            : briefingTab(d, lastVisit, snaps, rsnaps);
  root.innerHTML = `<div class="stack" style="gap:18px">
    <div><div class="eyebrow">Overview · live from runs/</div><h2>Project overview</h2>
      <p class="hw-story">Where the search stands: leaders per score identity, families against each score, and what changed. Rolled up by line of work, not run folder.</p>
      <div class="pill-row" style="margin:8px 0 0">${pill(`generated ${esc(d.generated_utc)}`)} ${pill(`${int(d.kpis && d.kpis.runs)} runs since ${esc(String(d.since_utc).slice(0, 10))}`)} ${pill(`leaders need ≥ ${esc(d.registry.min_valid_for_leader)} valid evals`)} ${pill(`${esc(d.elapsed_s)} s`)}</div>
      ${s.tab === "briefing" ? `<div class="pill-row" style="margin:8px 0 0"><button class="btn btn-sm" id="ov-snap">Generate snapshot</button><span class="muted" style="font-size:.76rem" id="ov-snap-msg">CPU-only; writes runs/analysis/overview_&lt;date&gt;/ — it never takes the GPU lock.</span></div>` : ""}</div>
    ${d.registry.error ? `<div class="alert error" role="alert"><b>Score identity registry:</b> ${esc(d.registry.error)}</div>` : ""}
    <div class="ov-tabs" role="navigation" aria-label="Overview tabs">${tabBtn("briefing", "Briefing")}${tabBtn("leaders", "Leaders")}${tabBtn("typologies", "Typologies")}${tabBtn("next", "Next solves")}${tabBtn("decisions", "Decisions")}${tabBtn("params", "Parameters")}
      <span class="sp"></span>
      <div class="ov-tabctl"><label class="ov-ctl">Window <select id="ov-days">${dayOpts}</select></label>
      <label class="ov-ctl"><input type="checkbox" id="ov-legacy"${s.legacy ? " checked" : ""}> show legacy scores</label></div></div>
    ${body}
  </div>`;
  root.querySelector("#ov-days").addEventListener("change", e => { location.hash = hashFor({ ...s, days: Number(e.target.value) }); });
  root.querySelector("#ov-legacy").addEventListener("change", e => { location.hash = hashFor({ ...s, legacy: e.target.checked }); });
  const sel = root.querySelector("#ov-ident");
  if (sel) sel.addEventListener("change", e => { location.hash = hashFor({ ...s, ident: e.target.value }); });
  if (s.tab === "next") {
    wireFindings(root, s, patch => { location.hash = hashFor({ ...s, ...patch }); });
  }
  if (s.tab === "decisions") wireRegistry(root);
  if (s.tab === "params") wireParams(root);
  if (s.tab === "briefing") wireResearch(root, () => viewOverview(root, query));
  const snapBtn = root.querySelector("#ov-snap");
  if (snapBtn) snapBtn.addEventListener("click", async () => {
    const msg = root.querySelector("#ov-snap-msg");
    snapBtn.disabled = true;
    if (msg) msg.textContent = "Starting snapshot job…";
    try {
      const r = await fetch("/api/jobs", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: "overview-snapshot", args: { days: s.days } }) });
      const out = await r.json().catch(() => ({}));
      if (msg) msg.textContent = out.error ? `Refused: ${out.error}` : `Snapshot job ${out.id} started (${out.status}).`;
      if (!out.error) setTimeout(() => { location.hash = hashFor({ ...s, tab: "briefing" }); }, 1200);
    } catch (e) {
      if (msg) msg.textContent = `Refused: ${e.message}`;
    } finally { snapBtn.disabled = false; }
  });
}
