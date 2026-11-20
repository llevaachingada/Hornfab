// overview_findings.js — hornlab-search GUI   AGPL-3.0-or-later
//
// #/overview?tab=next — "Next solves" (Overview phase 2, WP2.2). Read-only: every number, label and
// priority score comes from GET /api/overview/findings (data_overview_findings.py). This module only
// formats, filters and sorts by values Python already computed; it never derives a ranking and never
// compares J across score identities.
//
// Exports:
//   findingsTabHtml(fd, state)          -> HTML fragment for the tab body
//   wireFindings(root, state, onChange) -> binds the filter bar; onChange(patch) lets the caller
//                                          rewrite the URL (no reload, no navigation here)
//
// state = {kind, card, ident, status, sort, q}. `kind` is a comma-separated list of rule kinds
// ("" = every kind). `status` is open | resolved | all; `sort` is priority | newest | identity.

const MISSING = "—";
const esc = s => (s == null ? MISSING : String(s))
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
const brk = s => esc(s).replace(/([_\-./|])/g, "$1<wbr>");
const num = (v, d = 3) => (v == null || !isFinite(v)) ? MISSING : Number(v).toFixed(d);
const int = v => (v == null || !isFinite(v)) ? MISSING : Math.round(v).toLocaleString("en-US");

function ago(iso) {
  if (!iso) return MISSING;
  const t = Date.parse(String(iso).endsWith("Z") || /[+-]\d\d:\d\d$/.test(iso) ? iso : iso + "Z");
  if (!isFinite(t)) return String(iso);
  const m = (Date.now() - t) / 60000;
  if (m < 1) return "just now";
  if (m < 60) return `${Math.round(m)} min ago`;
  if (m < 48 * 60) return `${Math.round(m / 60)} h ago`;
  return `${Math.round(m / 1440)} d ago`;
}
const tsOf = iso => { const t = Date.parse(iso && !/Z$|[+-]\d\d:\d\d$/.test(iso) ? iso + "Z" : iso); return isFinite(t) ? t : 0; };

// Severity vocabulary and colours mirror the Readiness board (bad / warn / medium / low).
const SEV = ["critical", "high", "medium", "low"];
const SEV_LABEL = { critical: "Critical", high: "High", medium: "Medium", low: "Low" };
const SEV_CLASS = { critical: "bad", high: "warn", medium: "hw-lvl-medium", low: "hw-lvl-low" };
const SEV_RANK = { critical: 0, high: 1, medium: 2, low: 3 };
// Kind vocabulary is fixed by the findings engine; order here is render order, nothing more.
const KINDS = [
  ["budget", "budget left"], ["refusals", "refusals"], ["bounds", "bounds"],
  ["tie_verify", "tie / verify"], ["stale_line", "stale line"], ["probe_only", "probes only"],
  ["registry", "registry"], ["software", "software"],
];
const KIND_LABEL = Object.fromEntries(KINDS);

const STYLE = `
.ovf-body{display:grid;gap:10px;min-width:0}
.ovf-bar{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;font-size:.8rem;min-width:0}
.ovf-bar>label{display:inline-flex;align-items:center;gap:6px;min-width:0}
.ovf-bar select,.ovf-bar input[type="search"]{font:inherit;font-size:.82rem;min-height:32px;max-width:100%;
  padding:4px 8px;border:1px solid var(--rule);border-radius:5px;background:var(--surface);color:var(--ink)}
.ovf-bar input[type="search"]{width:min(100%,18rem)}
.ovf-bar select:focus-visible,.ovf-bar input[type="search"]:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.ovf-kinds{border:1px solid var(--rule);border-radius:6px;padding:3px 10px 5px;background:var(--surface);max-width:100%}
.ovf-kinds>summary{cursor:pointer;font-size:.8rem;padding:1px 0}
.ovf-kinds>summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
.ovf-kindrow{display:flex;flex-wrap:wrap;gap:2px 12px;padding-top:4px}
.ovf-kindrow label{display:inline-flex;align-items:center;gap:5px;font-size:.8rem;white-space:nowrap}
.ovf-groups{display:grid;gap:10px;min-width:0}
.ovf-groups[hidden]{display:none}
.ovf-grp{background:var(--surface);border:1px solid var(--rule);border-radius:8px;padding:0;min-width:0}
.ovf-grp[hidden]{display:none}
.ovf-grp>summary{cursor:pointer;padding:9px 12px;display:flex;flex-wrap:wrap;gap:4px 8px;
  align-items:baseline;min-width:0}
.ovf-grp>summary:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.ovf-grp[open]>summary{border-bottom:1px solid var(--rule)}
.ovf-gtitle{min-width:0;overflow-wrap:anywhere;font-size:.88rem}
.ovf-gmeta{font-size:.72rem;min-width:0;overflow-wrap:anywhere}
.ovf-find{padding:10px 12px;border-top:1px solid var(--rule);display:grid;gap:5px;min-width:0}
.ovf-find[hidden]{display:none}
.ovf-find:first-child{border-top:0}
.ovf-fhead{display:flex;flex-wrap:wrap;gap:4px 8px;align-items:baseline;min-width:0}
.ovf-ftitle{font-size:.88rem;min-width:0;overflow-wrap:anywhere}
.ovf-detail{margin:0;font-size:.82rem;color:var(--label);max-width:78ch;overflow-wrap:anywhere}
.ovf-why .pill{color:var(--muted)}
.ovf-ev{list-style:none;margin:0;padding:0;display:grid;gap:1px;font-size:.74rem;overflow-wrap:anywhere}
.ovf-foot{margin:0;font-size:.74rem;display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline;min-width:0}
.ovf-by{font-size:.74rem}
.ovf-empty{margin:0}
.ovf-more{align-self:start}
.ovf-more[hidden]{display:none}
.ovf-kpihead{display:flex;flex-wrap:wrap;gap:2px 10px;align-items:baseline;margin:0 0 4px}
.ovf-kpihead .muted{font-size:.74rem}
/* Four severity tiles: two full columns at phone width; no empty tinted track. */
@media (max-width:640px){
  .kpis.ovf-kpis{grid-template-columns:repeat(2,minmax(0,1fr)) !important}
}
@media (max-width:520px){
  .ovf-grp>summary{padding:8px 10px}
  .ovf-find{padding:9px 10px}
  .ovf-bar input[type="search"]{width:100%}
}
`;

function ensureStyle() {
  if (document.getElementById("ovf-style")) return;
  const s = document.createElement("style"); s.id = "ovf-style"; s.textContent = STYLE;
  document.head.appendChild(s);
}

const pill = (t, cls = "", title = "") =>
  `<span class="pill ${cls}"${title ? ` title="${esc(title)}"` : ""}>${esc(t)}</span>`;
const kpi = (label, value, sub = "", cls = "") =>
  `<div class="kpi"><span>${esc(label)}</span><b class="${cls}">${esc(value)}</b>${sub ? `<small class="muted" style="font-size:.72rem">${esc(sub)}</small>` : ""}</div>`;

const sevOf = f => {
  const k = String((f && f.severity) || "").toLowerCase();
  return SEV_RANK[k] == null ? SEV.length : SEV_RANK[k];
};
const sevName = f => {
  const k = String((f && f.severity) || "").toLowerCase();
  return SEV_RANK[k] == null ? ((f && f.severity) || MISSING) : k;
};
const scoreOf = f => { const n = Number(f && f.score); return isFinite(n) ? n : -1; };
const isOpen = f => {
  const st = String((f && f.status) || "open");
  return st === "open" || st === "acknowledged";
};
const cardOf = f => {
  const k = String((f && f.line_key) || "");
  return k.includes("|") ? k.slice(0, k.indexOf("|")) : "";
};
const hrefOf = f => (f && f.href) ? String(f.href)
  : "#/overview?tab=leaders&ident=" + encodeURIComponent(String((f && f.identity_id) || ""));

function normState(state) {
  const st = state || {};
  const kind = Array.isArray(st.kind) ? st.kind.join(",") : (st.kind == null ? "" : String(st.kind));
  const one = (v, allowed, d) => (allowed.includes(v) ? v : d);
  return {
    kind: kind.trim(),
    card: st.card == null ? "" : String(st.card),
    ident: st.ident == null ? "" : String(st.ident),
    status: one(st.status, ["open", "resolved", "all", "dismissed"], "open"),
    sort: one(st.sort, ["priority", "newest", "identity"], "priority"),
    q: st.q == null ? "" : String(st.q),
  };
}

function compareFindings(a, b, s, idx) {
  if (s.sort === "newest") {
    const d = tsOf(b.first_seen_utc) - tsOf(a.first_seen_utc);
    if (d) return d;
  }
  if (isOpen(a) !== isOpen(b)) return isOpen(a) ? -1 : 1;
  const sc = scoreOf(b) - scoreOf(a);
  if (sc) return sc;
  const sv = sevOf(a) - sevOf(b);
  if (sv) return sv;
  return (idx.get(a.id) ?? 0) - (idx.get(b.id) ?? 0);
}

function groupFindings(list, s) {
  const idx = new Map();
  list.forEach((f, i) => idx.set(f.id, i));
  const by = new Map();
  let seq = 0;
  for (const f of list) {
    const key = String(f.identity_id || "") + "\u0000" + String(f.line_key || "");
    let g = by.get(key);
    if (!g) {
      // first finding in payload order fixes the group's place; Map keeps that insertion order.
      g = { key, identity_id: String(f.identity_id || ""), line_key: String(f.line_key || ""), findings: [], first: seq++ };
      by.set(key, g);
    }
    g.findings.push(f);
  }
  const groups = [...by.values()];
  for (const g of groups) {
    // Priority order is the payload's order (server sorts status, score, severity). Only the
    // explicit sort controls reorder findings/groups; priority never re-sorts by score.
    if (s.sort !== "priority") g.findings.sort((a, b) => compareFindings(a, b, s, idx));
    g.top = [...g.findings].sort((a, b) => (sevOf(a) - sevOf(b)) || (scoreOf(b) - scoreOf(a)))[0];
    g.score = Math.max(...g.findings.map(scoreOf));
    g.open = g.findings.some(isOpen);
    g.newest = Math.max(...g.findings.map(f => tsOf(f.first_seen_utc)));
  }
  if (s.sort === "newest") {
    groups.sort((a, b) => (b.newest - a.newest) || (a.first - b.first));
  } else if (s.sort === "identity") {
    groups.sort((a, b) => a.identity_id.localeCompare(b.identity_id) || (a.first - b.first));
  }
  return groups;
}

function statusHtml(f) {
  const st = String((f && f.status) || "open");
  if (st === "open") return "";
  const cls = st === "resolved" ? "good" : st === "acknowledged" ? "warn" : "";
  const by = f && f.resolved_by
    ? `<span class="muted ovf-by">by <a class="mono" href="#/run/${encodeURIComponent(String(f.resolved_by))}">${brk(f.resolved_by)}</a></span>`
    : "";
  return `${pill(st.replace(/_/g, " "), cls)}${by}`;
}

function findingHtml(f, isLead = false) {
  const sev = sevName(f);
  const why = (Array.isArray(f.why) ? f.why : []).map(w => `<span class="pill">${esc(w)}</span>`).join(" ");
  const ev = (Array.isArray(f.evidence) ? f.evidence : []).map(e => `<li class="muted">${brk(e)}</li>`).join("");
  // The group summary already states the lead finding's severity and title; do not repeat them.
  const head = isLead
    ? `<div class="ovf-fhead"><span class="pill">${esc(KIND_LABEL[f.kind] || f.kind || MISSING)}</span>${statusHtml(f)}</div>`
    : `<div class="ovf-fhead">
      <span class="pill ${SEV_CLASS[sev] || ""}">${esc(sev)}</span>
      <span class="pill">${esc(KIND_LABEL[f.kind] || f.kind || MISSING)}</span>
      <b class="ovf-ftitle">${esc(f.title)}</b>
      ${statusHtml(f)}
    </div>`;
  return `<article class="ovf-find" data-sev="${esc(sev)}">
    ${head}
    ${f.detail ? `<p class="ovf-detail">${esc(f.detail)}</p>` : ""}
    ${why ? `<div class="pill-row ovf-why">${why}</div>` : ""}
    ${ev ? `<ul class="ovf-ev">${ev}</ul>` : ""}
    <p class="ovf-foot muted">
      <span title="priority score computed by the findings engine">priority ${f.score == null ? MISSING : num(f.score, 1)}</span>
      <span>first seen ${esc(ago(f.first_seen_utc))}</span>
      <a href="${esc(hrefOf(f))}">${f.line_key ? "open line" : "open identity"} →</a>
    </p>
  </article>`;
}

function groupHtml(g, open) {
  const top = g.top;
  const sev = sevName(top);
  const present = new Set(g.findings.map(f => f.kind));
  const others = KINDS.map(([k]) => k).filter(k => present.has(k) && k !== top.kind);
  const chips = others.map(k => `<span class="pill">${esc(KIND_LABEL[k] || k)}</span>`).join(" ");
  // Join only non-empty segments: identity-less findings (software) must not print a bare dash.
  const segs = [];
  if (g.identity_id) segs.push(`<span class="mono">${brk(g.identity_id)}</span>`);
  if (g.line_key) {
    const [card, construction] = String(g.line_key).split("|");
    const parts = [card, construction].filter(Boolean).map(esc);
    if (parts.length) segs.push(`<span>${parts.join(" · ")}</span>`);
  } else {
    segs.push(`<span>identity-level</span>`);
  }
  const where = segs.join(' <span aria-hidden="true">·</span> ');
  return `<details class="ovf-grp"${open ? " open" : ""}>
    <summary>
      <span class="pill ${SEV_CLASS[sev] || ""}">${esc(sev)}</span>
      <span class="ovf-gtitle"><b>${esc(top.title)}</b></span>
      ${chips ? `<span class="pill-row">${chips}</span>` : ""}
      <span class="muted ovf-gmeta">${where}</span>
      <span class="muted ovf-gmeta">${g.findings.length} finding${g.findings.length === 1 ? "" : "s"}</span>
    </summary>
    <div class="ovf-gbody">${g.findings.map(f => findingHtml(f, !!top && f.id != null && f.id === top.id)).join("")}</div>
  </details>`;
}

function matches(f, s, kindSet) {
  if (kindSet.size && !kindSet.has(String(f.kind || ""))) return false;
  if (s.card && cardOf(f) !== s.card) return false;
  if (s.ident && String(f.identity_id || "") !== s.ident) return false;
  const st = String(f.status || "open");
  if (s.status === "open" && st !== "open" && st !== "acknowledged") return false;
  if (s.status === "resolved" && (st === "open" || st === "acknowledged")) return false;
  if (s.status === "dismissed" && st !== "dismissed") return false;
  return true;
}

const option = (value, label, selected) =>
  `<option value="${esc(value)}"${selected ? " selected" : ""}>${esc(label)}</option>`;

export function findingsTabHtml(fd, state) {
  ensureStyle();
  if (!fd || typeof fd !== "object") return `<p class="muted">No findings data available.</p>`;
  const s = normState(state);
  const all = (fd && Array.isArray(fd.findings)) ? fd.findings.filter(Boolean) : [];
  const head = `<div>
    <div class="eyebrow">Next solves · findings engine</div>
    <p class="muted" style="font-size:.8rem;margin:2px 0 0">Ranked, explainable recommendations: one finding per line of work, never one per run. Priority is computed by the findings engine; this page only filters and sorts it.</p>
  </div>`;

  const kindSet = new Set(s.kind.split(",").map(x => x.trim()).filter(Boolean));
  const cards = [...new Set(all.map(cardOf).filter(Boolean))].sort();
  const idents = [...new Set(all.map(f => String(f.identity_id || "")).filter(Boolean))].sort();
  const list = all.filter(f => matches(f, s, kindSet));
  // Tiles count what the list predicate matches (wireFindings refines them for the local search),
  // so the strip, the counter and the groups always add up.
  const matchCounts = {};
  for (const sv of SEV) matchCounts[sv] = list.filter(f => sevName(f) === sv).length;
  const kpis = `<div class="kpis ovf-kpis">${SEV.map(sv =>
      `<div class="kpi"><span>${esc(SEV_LABEL[sv])}</span><b class="${SEV_CLASS[sv]}" data-ovf-sev="${sv}">${int(matchCounts[sv])}</b></div>`).join("")}</div>
    <p class="muted" style="font-size:.74rem;margin:4px 0 0">Severity tiles count the findings that match the filters below; the payload holds ${int(all.length)}.</p>`;
  if (!all.length) {
    return `${head}${kpis}<p class="muted ovf-empty">${s.status === "open"
      ? "Nothing open — every line has room to run" : "No findings match"}</p>`;
  }

  const groups = groupFindings(list, s);
  const top = groups.slice(0, 10);
  const rest = groups.slice(10);

  const kindBoxes = KINDS.map(([k, label]) =>
    `<label><input type="checkbox" data-kind="${esc(k)}"${kindSet.has(k) ? " checked" : ""}> ${esc(label)}</label>`).join("");
  const bar = `<div class="ovf-bar" role="group" aria-label="Finding filters">
    <details class="ovf-kinds"><summary>Kind: ${kindSet.size ? esc(`${kindSet.size} selected`) : "all"}</summary>
      <div class="ovf-kindrow">${kindBoxes}</div></details>
    <label>Card <select id="ovf-card">${option("", `all cards (${cards.length})`, !s.card)}${cards.map(c => option(c, c, c === s.card)).join("")}</select></label>
    <label>Identity <select id="ovf-ident">${option("", `all identities (${idents.length})`, !s.ident)}${idents.map(i => option(i, i, i === s.ident)).join("")}</select></label>
    <label>Status <select id="ovf-status">${option("open", "open", s.status === "open")}${option("resolved", "resolved / closed", s.status === "resolved")}${option("all", "all", s.status === "all")}${s.status === "dismissed" ? option("dismissed", "dismissed", true) : ""}</select></label>
    <label>Sort <select id="ovf-sort">${option("priority", "priority", s.sort === "priority")}${option("newest", "newest", s.sort === "newest")}${option("identity", "identity", s.sort === "identity")}</select></label>
    <label>Search <input type="search" id="ovf-q" value="${esc(s.q)}" placeholder="title, subject, evidence" autocomplete="off" aria-label="Search findings"></label>
    <button type="button" class="btn btn-sm" id="ovf-reset">Reset</button>
    <span class="muted" id="ovf-shown" aria-live="polite">${int(top.length)} of ${int(groups.length)} groups · ${int(top.reduce((n, g) => n + g.findings.length, 0))} of ${int(list.length)} findings shown</span>
  </div>`;

  const body = `<div class="ovf-body">
    ${bar}
    <div class="ovf-groups" id="ovf-groups">${top.map((g, i) => groupHtml(g, i === 0)).join("")}</div>
    ${rest.length ? `<div class="ovf-groups" id="ovf-rest" hidden>${rest.map(g => groupHtml(g, false)).join("")}</div>` : ""}
    ${groups.length > 10 ? `<button type="button" class="btn btn-sm ovf-more" id="ovf-more" aria-expanded="false">Show all ${groups.length} groups</button>` : ""}
    <p class="muted ovf-empty" id="ovf-nomatch"${list.length ? " hidden" : ""}>No findings match</p>
  </div>`;
  return `${head}${kpis}${body}`;
}

export function wireFindings(root, state, onChange) {
  if (!root) return;
  const s = normState(state);
  const emit = patch => { if (typeof onChange === "function") onChange({ ...s, ...patch }); };
  const qs = sel => root.querySelector(sel);

  const boxes = [...root.querySelectorAll("input[data-kind]")];
  for (const box of boxes) {
    box.addEventListener("change", () => {
      const chosen = boxes.filter(b => b.checked).map(b => b.dataset.kind);
      emit({ kind: chosen.join(",") });
    });
  }
  qs("#ovf-card")?.addEventListener("change", e => emit({ card: e.target.value }));
  qs("#ovf-ident")?.addEventListener("change", e => emit({ ident: e.target.value }));
  qs("#ovf-status")?.addEventListener("change", e => emit({ status: e.target.value }));
  qs("#ovf-sort")?.addEventListener("change", e => emit({ sort: e.target.value }));
  qs("#ovf-reset")?.addEventListener("click", () =>
    emit({ kind: "", card: "", ident: "", status: "open", sort: "priority", q: "" }));

  // Text search runs locally (no re-render, so the caret never jumps) and is written to the URL
  // only when committed (Enter or blur), which keeps the filter round-trippable without reloads.
  const q = qs("#ovf-q");
  const restBox = qs("#ovf-rest");
  const more = qs("#ovf-more");
  const nomatch = qs("#ovf-nomatch");
  const counter = qs("#ovf-shown");
  const sevValues = [...root.querySelectorAll("[data-ovf-sev]")];
  const allGroups = [...root.querySelectorAll("details.ovf-grp")];
  const totalGroups = allGroups.length;
  const totalRows = root.querySelectorAll(".ovf-find").length;
  let restOpen = false;

  // Tiles follow the filter predicate (kind/card/identity/status, plus the local search). The
  // 10-group paging is a display choice and must not change the matching totals.
  const updateCounts = () => {
    if (!sevValues.length) return;
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const f of root.querySelectorAll(".ovf-find")) {
      if (f.hidden) continue;
      const sv = String(f.dataset.sev || "").toLowerCase();
      if (sv in counts) counts[sv]++;
    }
    for (const b of sevValues) {
      const sv = b.dataset.ovfSev;
      b.textContent = (counts[sv] || 0).toLocaleString("en-US");
    }
  };

  // Group count and finding count are different units: always label both.
  const updateCounter = () => {
    if (!counter) return;
    let gvis = 0;
    let fvis = 0;
    for (const g of allGroups) {
      const inRest = !!(restBox && restBox.contains(g));
      if (g.hidden || (inRest && restBox.hidden)) continue;
      gvis++;
      for (const f of g.querySelectorAll(".ovf-find")) if (!f.hidden) fvis++;
    }
    counter.textContent = `${int(gvis)} of ${int(totalGroups)} groups · ${int(fvis)} of ${int(totalRows)} findings shown`;
  };

  const applyQ = () => {
    const needle = (q && q.value ? q.value : "").trim().toLowerCase();
    if (restBox) restBox.hidden = needle ? false : !restOpen;
    if (more) more.hidden = !!needle;
    let vis = 0;
    for (const g of allGroups) {
      let gvis = 0;
      for (const f of g.querySelectorAll(".ovf-find")) {
        const hit = !needle || f.textContent.toLowerCase().includes(needle);
        f.hidden = !hit;
        if (hit) gvis++;
      }
      g.hidden = gvis === 0;
      vis += gvis;
    }
    if (nomatch) nomatch.hidden = vis !== 0;
    updateCounter();
    updateCounts();
  };

  q?.addEventListener("input", applyQ);
  q?.addEventListener("change", () => {
    applyQ();
    const v = q.value.trim();
    if (v !== s.q) emit({ q: v });
  });

  more?.addEventListener("click", () => {
    if (!restBox) return;
    restOpen = !restOpen;
    restBox.hidden = !restOpen;
    more.setAttribute("aria-expanded", restOpen ? "true" : "false");
    more.textContent = restOpen ? "Show top 10 groups" : `Show all ${topCount(root)} groups`;
    updateCounter();
    updateCounts();
  });

  applyQ();
}

function topCount(root) {
  return root.querySelectorAll("#ovf-groups > details.ovf-grp").length
    + root.querySelectorAll("#ovf-rest > details.ovf-grp").length;
}
