// hw.js — hornlab-search GUI   AGPL-3.0-or-later
//
// Horn + woofer system views (G0, house style P1 —
// docs/research/system_woofer_2026-11-18/GUI_COMPLETION_HANDOFF_2026-11-19.md §4, §5.5, §5.6, §8):
//   #/hw/cases                 ledger of every staged / solved / refused Boundary Lab case
//   #/hw/case/<exp>/<case>     one case: overview, per-channel bases, polars, provenance
//   #/hw/readiness             risk register R1-R17 + open owner decisions
//
// Read-only. Every number comes from /api/hw/* (Python readers); JS only formats and plots.
// Channels are never summed here: the woofer basis is Pa per 2.83 V, the horn basis Pa per 1 m/s,
// and no calibration policy exists yet (risk R1).
//
// P1 rules kept in this file: eyebrow + h2 + mono id + provenance pill-row (no top-level heading
// level 1, no header band component); run-detail toolbar for the case tabs; tips from glossary.js
// TERMS; skeletons while loading; view state in the URL; clearance is shown once per surface.

import { chart, polarMap, niceTicks, logTicks, cmap, css, el, NS, wireScrollHints } from "./charts.js";
import { TERMS, tip } from "./glossary.js";
import { mountHw3D } from "./hw3d.js";

// ── Helpers copied from app.js / verify.js (they are local there, not exported) ──

// One missing-value glyph everywhere (handoff §8, P1 polish): the em dash.
const MISSING = "—";

const esc = s => (s == null ? MISSING : String(s))
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

/** Same as app.js: break long ids at _ - . / instead of widening the page. */
function brk(s) {
  return esc(s).replace(/([_\-./])/g, "$1<wbr>");
}

// Same formats as app.js's run pages (not exported from there).
const fmtHz = v => v == null || !isFinite(v) ? MISSING : v >= 1000 ? (v / 1000).toFixed(1) + " kHz" : Math.round(v) + " Hz";
const fmtDeg = v => v == null || !isFinite(v) ? MISSING : Number(v).toFixed(0) + "°";
const fmtMm = v => v == null || !isFinite(v) ? MISSING : Math.round(v) + " mm";
const fmtDb = v => v == null || !isFinite(v) ? MISSING : Number(v).toFixed(1) + " dB";

const num = (v, d = 0) => (v == null || !isFinite(v)) ? MISSING : Number(v).toFixed(d);
/** Readiness records use "-" for "none"; render that (and null) as the one missing glyph. */
const dash = v => (v == null || v === "" || v === "-" ? MISSING : String(v));

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

const errBanner = msg => `<div class="alert error" role="alert"><b>Error:</b> ${esc(msg)}</div>`;
const encKey = key => String(key).split("/").map(encodeURIComponent).join("/");
const caseHref = key => "#/hw/case/" + encKey(key);

// ── Tokens: verbatim text + a plain-English gloss next to it ─────────────────
//
// Tokens that map onto a glossary term take their user-visible text from TERMS; the rest keep a
// local gloss (handoff §1.4: refusal tokens are never hidden, never rephrased away).
const TOKEN_TERM = {
  DEMO_MOTOR: "demo_motor",
  DEMO_TRANSDUCER_SHAPE: "demo_shape",
  IDEAL_HORN_SOURCE: "ideal_horn_source",
  LF_NOT_SOLVED: "lf_not_solved",
  CONVERGENCE_UNCHECKED: "convergence",
  BODY_CLEARANCE_VIOLATION: "clearance",
  BODY_CLEARANCE_UNPROVEN: "clearance",
};
const GLOSS = {
  MANIFEST_INTEGRITY_FAILED: "The case's manifest no longer matches its own checksum.",
  UNDECLARED: "Not in the readiness registry, so no fidelity label is claimed.",
  NOT_CHECKED: "Clearance was not checked for this case.",
  BL_VALIDATE_FAILED: "Boundary Lab's own validate returned a non-zero exit code.",
  STAGE_FAILED: "The staging step recorded a failure (Boundary Lab refusal or adapter check). A separate solve may still exist for this case.",
};
const tokenKey = t => String(t).split(/[\[:]/)[0];
const isClearanceToken = t => tokenKey(t) === "BODY_CLEARANCE_VIOLATION" || tokenKey(t) === "BODY_CLEARANCE_UNPROVEN";
const termFor = t => TERMS[TOKEN_TERM[tokenKey(t)]];
const glossFor = t => (String(t).startsWith("STAGE_FAILED") ? GLOSS.STAGE_FAILED : (termFor(t) || {}).short
  || GLOSS[tokenKey(t)] || "");
const titleFor = t => (String(t).startsWith("STAGE_FAILED") ? GLOSS.STAGE_FAILED : (termFor(t) || {}).long
  || GLOSS[tokenKey(t)] || "");

/** Break an enum only BEFORE each underscore: a line can start with "_", never end with it. */
const enumText = s => esc(s).replace(/_/g, "<wbr>_");

// ── Shared markup helpers ───────────────────────────────────────────────────

/** House header (§4): eyebrow, h2, mono id, one compact story line, provenance pills. */
function pageHead({ eyebrow, title, id, pills = "", story = "", storyTitle = "" }) {
  return `<div>
    <div class="eyebrow">${esc(eyebrow)}</div>
    <h2>${esc(title)}</h2>
    ${id ? `<p class="mono muted" style="font-size:0.78rem;overflow-wrap:anywhere">${brk(id)}</p>` : ""}
    ${story ? `<p class="hw-story"${storyTitle ? ` title="${esc(storyTitle)}"` : ""}>${story}</p>` : ""}
    ${pills ? `<div class="pill-row" style="margin:8px 0 0">${pills}</div>` : ""}
  </div>`;
}

const kpi = (label, value, sub = "", cls = "") =>
  `<div class="kpi"><span>${label}</span><b class="${cls}">${esc(value)}</b>${sub
    ? `<small class="muted" style="font-size:0.72rem">${sub}</small>` : ""}</div>`;

const STATE_PILL = {
  solved: "good", staged: "", stage_failed: "bad", solve_failed: "bad", recorded: "", empty: "",
};
const STATE_LABEL = {
  solved: "solved", staged: "staged", stage_failed: "stage failed", solve_failed: "solve failed",
  recorded: "recorded", empty: "empty dir",
};

function statePill(r) {
  const s = r.state;
  let extra = "";
  if (s === "solved" && r.solve) extra = ` ${r.solve.done}/${r.solve.total}`;
  return `<span class="pill ${STATE_PILL[s] || ""}">${esc(STATE_LABEL[s] || s)}${esc(extra)}</span>`;
}

function fidelityBadge(f) {
  const cls = f === "UNDECLARED" ? "warn" : "";
  const title = f === "UNDECLARED" ? GLOSS.UNDECLARED : `${TERMS.hw_fidelity.label}: ${TERMS.hw_fidelity.long}`;
  return `<span class="pill ${cls}" title="${esc(title)}">${enumText(f)}</span>`;
}

function roleBadge(label, v) {
  if (!v) return "";
  const cls = v === "real" ? "good" : v === "demo" ? "warn" : "";
  const term = label === "motor" ? TERMS.demo_motor : TERMS.demo_shape;
  const title = term ? `${term.label}: ${term.long}` : label;
  return `<span class="pill ${cls}" title="${esc(title)}">${esc(label)}: ${esc(v)}</span>`;
}

function clearancePill(c) {
  if (!c) return `<span class="muted">${MISSING}</span>`;
  const cls = c.status === "PASS" ? "good" : c.status === "NOT_CHECKED" ? "" : "bad";
  const gap = c.aabb_gap_m != null ? ` ${num(c.aabb_gap_m * 1000, 1)} mm` : "";
  const src = c.source === "replay" ? " (replayed)" : c.source === "manifest" ? " (recorded)" : "";
  const title = c.status === "PASS"
    ? `Proven minimum gap (bounding-box lower bound)${src}. ${TERMS.clearance.long}`
    : `${GLOSS[c.status] || c.reason || TERMS.clearance.long}${src}`;
  return `<span class="pill ${cls}" title="${esc(title)}">${enumText(c.status === "PASS" ? "gap" : c.status)}${esc(c.status === "PASS" ? gap : "")}</span>`;
}

/** Token chips with the verbatim token, its plain-English gloss beside it, and no truncation. */
function tokenChips(tokens) {
  const list = (tokens || []).filter(t => !isClearanceToken(t));
  if (!list.length) return `<span class="muted">${MISSING}</span>`;
  return list.map(t => {
    const g = glossFor(t);
    return `<span class="hw-token"><span class="pill bad" title="${esc(titleFor(t))}">${esc(t)}</span>${g
      ? `<span class="muted">${esc(g)}</span>` : ""}</span>`;
  }).join("");
}

function boxText(b) {
  if (!b) return MISSING;
  return `${num(b.width_mm, 1)}×${num(b.height_mm, 1)}×${num(b.depth_mm, 1)} mm · port ${num(b.port_area_cm2, 0)} cm²`;
}

const bandText = f => (f && f.length ? `${fmtHz(Math.min(...f))}–${fmtHz(Math.max(...f))}` : MISSING);

// ── Cases ledger ────────────────────────────────────────────────────────────

const FILTERS = [
  ["bl", "Boundary Lab cases"], ["declared", "In registry"], ["solved", "Solved"],
  ["problems", "Problems"], ["all", "Everything"],
];
// Hidden by default (handoff §5.5): empty dirs and failed attempts are still counted in the KPIs.
const HIDDEN_STATES = new Set(["empty", "stage_failed", "solve_failed"]);

const matchFilter = (r, filter) =>
  filter === "all" ? true :
  filter === "bl" ? r.family === "bl_case" :
  filter === "declared" ? r.declared :
  filter === "solved" ? r.state === "solved" :
  filter === "problems" ? ((r.tokens || []).length > 0 || /failed/.test(r.state)) : true;

/** "20261119T013209Z-ref_case-11372-..." -> "ref_case-11372-...": the timestamp stays in the small id. */
const caseShort = name => String(name).replace(/^\d{8}T\d{6}Z-/, "");
/** A readable group name from the experiment id; the raw id is shown beside it in small mono. */
const expName = e => {
  const s = String(e).replace(/^bl_/, "").replace(/_/g, " ").trim();
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : String(e);
};

export async function viewHwCases(root, query = "") {
  skel(root, "Loading cases");
  let data;
  try { data = await api("/api/hw/cases"); } catch (e) { busyDone(root); root.innerHTML = errBanner(e.message); return; }
  const params = new URLSearchParams(query || "");
  let filter = FILTERS.some(([k]) => k === params.get("f")) ? params.get("f") : "bl";
  let showAll = params.get("show") === "all";
  const c = data.counts || {};
  const declared = data.cases.filter(r => r.declared).length;
  const missing = (data.declared_missing || []).length;
  const pills = [
    `<span class="pill">${esc(data.cases.length)} case dirs on disk</span>`,
    `<span class="pill">${esc(declared)} in registry</span>`,
    missing ? `<span class="pill bad">${esc(missing)} registry entries missing on disk</span>` : "",
  ].filter(Boolean).join("");

  root.innerHTML = `<div class="stack" style="gap:18px">
    ${pageHead({
      eyebrow: "Horn + woofer · Cases · Boundary Lab ledger",
      title: "Boundary Lab cases",
      id: data.store,
      pills,
      story: "Story step 5–7 · every staged, solved or refused case on disk, grouped by experiment.",
      storyTitle: "Status, box and gap are read from the case files. Fidelity, motor and shape are declared in readiness.yaml; a case missing from it shows UNDECLARED. Empty dirs and failed attempts stay counted in the KPIs but are hidden unless you show them.",
    })}
    ${data.registry_error ? errBanner(data.registry_error) : ""}
    ${missing ? `<div class="alert warn" role="alert">Registry cases missing on disk:
      ${data.declared_missing.map(m => `<code>${esc(m.key)}</code>`).join(", ")}</div>` : ""}
    <div class="kpis">
      ${kpi(esc("Solved"), c.solved ?? 0, "", "good")}
      ${kpi(esc("Staged"), c.staged ?? 0)}
      ${kpi(esc("Stage failed"), c.stage_failed ?? 0, "", c.stage_failed ? "bad" : "")}
      ${kpi(esc("Solve failed"), c.solve_failed ?? 0, "", c.solve_failed ? "bad" : "")}
      ${kpi(esc("Recorded"), c.recorded ?? 0)}
      ${kpi(esc("Empty"), c.empty ?? 0)}
    </div>
    <div class="run-toolbar" style="align-items:center">
      <div class="btn-row" role="group" aria-label="Filter cases">
        ${FILTERS.map(([k, l]) => `<button class="btn btn-sm${k === filter ? " primary" : ""}" data-f="${k}" aria-pressed="${k === filter}">${esc(l)}</button>`).join("")}
      </div>
      <div class="run-actions" style="padding-bottom:0">
        <button class="btn btn-sm" id="hw-show-all" aria-pressed="${showAll}"
          title="Empty dirs and failed attempts stay counted in the KPIs above">Show superseded / empty</button>
        <a class="btn btn-sm" href="#/hw/readiness">Readiness →</a>
      </div>
    </div>
    <p class="hint" role="status" id="hw-cases-status" style="font-size:0.8rem"></p>
    <div id="hw-groups"></div>
    ${data.fidelity_note ? `<p class="muted" style="max-width:76ch;font-size:0.82rem">${esc(data.fidelity_note)}</p>` : ""}
  </div>`;
  busyDone(root);

  const host = root.querySelector("#hw-groups");
  const status = root.querySelector("#hw-cases-status");
  const openGroups = new Set();
  const seenGroups = new Set();

  const syncUrl = () => {
    const p = new URLSearchParams();
    if (filter !== "bl") p.set("f", filter);
    if (showAll) p.set("show", "all");
    const q = p.toString();
    history.replaceState(null, "", "#/hw/cases" + (q ? "?" + q : ""));
  };
  const syncControls = () => {
    root.querySelectorAll("button[data-f]").forEach(b => {
      b.classList.toggle("primary", b.dataset.f === filter);
      b.setAttribute("aria-pressed", String(b.dataset.f === filter));
    });
    const t = root.querySelector("#hw-show-all");
    if (t) t.setAttribute("aria-pressed", String(showAll));
  };

  const groupHtml = (exp, rows) => {
    const hidden = data.cases.filter(r => r.experiment === exp && matchFilter(r, filter)
      && HIDDEN_STATES.has(r.state)).length;
    const solved = rows.filter(r => r.state === "solved").length;
    const open = openGroups.has(exp);
    const body = rows.map(r => {
      const solve = r.solve && r.solve.fmin_hz != null
        ? `<span class="hw-ledger-band ${r.state === "solved" ? "good-text" : "muted"}">${num(r.solve.fmin_hz)}–${num(r.solve.fmax_hz)} Hz</span>`
        : `<span class="muted">${MISSING}</span>`;
      const horn = r.horn
        ? `<div>${num((r.horn.translation_mm || [])[2], 1)} mm</div>${clearancePill(r.clearance)}`
        : `<span class="muted">vented only</span>`;
      const ref = r.ref && r.ref !== "-" ? `${esc(r.ref)} · ` : "";
      const title = ref + esc(r.gate || caseShort(r.case));
      const tokens = (r.tokens || []).filter(t => !isClearanceToken(t));
      const note = r.note ? `<div class="hw-row-note">${esc(r.note)}</div>` : "";
      const tokenRow = tokens.length || note
        ? `<tr class="hw-tokens-row"><td colspan="7">${note}${tokens.length ? tokenChips(tokens) : ""}</td></tr>`
        : "";
      return `<tr class="clickable" data-key="${esc(r.key)}" tabindex="0">
        <td class="hw-ledger-case">
          <div class="hw-ledger-title">${title}</div>
          <div class="hw-ledger-id">${brk(r.case)}</div>
        </td>
        <td>${statePill(r)}</td>
        <td>${roleBadge("motor", r.motor)}<br>${roleBadge("shape", r.transducer_shape)}</td>
        <td style="white-space:normal">${esc(boxText(r.box))}</td>
        <td style="white-space:normal">${horn}</td>
        <td>${solve}</td>
        <td>${fidelityBadge(r.fidelity)}</td>
      </tr>${tokenRow}`;
    }).join("");
    return `<details class="hw-group" data-exp="${esc(exp)}"${open ? " open" : ""}>
      <summary aria-expanded="${open}"><span class="hw-group-name">${esc(expName(exp))}</span>
        <span class="hw-group-sep" aria-hidden="true">·&nbsp;</span><code class="hw-group-id">${esc(exp)}</code>
        <span class="pill">${esc(rows.length)} shown</span>
        ${solved ? `<span class="pill good">${esc(solved)} solved</span>` : ""}
        ${hidden && !showAll ? `<span class="pill warn">${esc(hidden)} hidden</span>` : ""}
      </summary>
      <div class="tbl-scroll hw-tbl-scroll">
        <p class="tbl-scroll-hint">scroll for all columns →</p>
        <div class="tbl-wrap"><table class="hw-ledger" style="table-layout:fixed">
          <colgroup><col style="width:200px"><col style="width:108px"><col style="width:140px">
            <col style="width:150px"><col style="width:140px"><col style="width:100px">
            <col style="width:160px"></colgroup>
          <thead><tr><th>Case</th><th>State</th><th>Motor / shape</th>
            <th>Box</th><th>${tip("clearance", "Gap / offset")}</th><th>Solved band</th>
            <th>${tip("hw_fidelity", "Fidelity")}</th></tr></thead>
          <tbody>${body}</tbody></table></div>
      </div>
    </details>`;
  };

  const draw = () => {
    const matching = data.cases.filter(r => matchFilter(r, filter));
    const visible = matching.filter(r => showAll || !HIDDEN_STATES.has(r.state));
    const groups = [];
    const index = new Map();
    for (const r of visible) {
      if (!index.has(r.experiment)) { index.set(r.experiment, groups.length); groups.push({ exp: r.experiment, rows: [] }); }
      groups[index.get(r.experiment)].rows.push(r);
    }
    // Every experiment group is open by default (§5.5 polish); a group the viewer collapses
    // stays collapsed across filter changes because openGroups records the click.
    for (const g of groups) if (!seenGroups.has(g.exp)) { seenGroups.add(g.exp); openGroups.add(g.exp); }
    const hidden = matching.length - visible.length;

    host.innerHTML = groups.length
      ? groups.map(g => groupHtml(g.exp, g.rows)).join("")
      : `<div class="alert info" role="status">No cases match this filter${hidden ? `; ${hidden} superseded or empty case(s) are hidden` : ""}.</div>
        <div class="btn-row" style="margin-top:8px">
          ${hidden && !showAll ? `<button class="btn btn-sm primary" data-empty="show">Show superseded / empty</button>` : ""}
          <button class="btn btn-sm" data-empty="all">Show everything</button>
          <a class="btn btn-sm" href="#/hw/readiness">Readiness →</a>
        </div>`;

    status.textContent = `Showing ${visible.length} of ${matching.length} case${matching.length === 1 ? "" : "s"}`
      + (hidden ? ` · ${hidden} hidden (superseded / empty)` : "") + ".";

    host.querySelectorAll("details.hw-group").forEach(det => {
      const exp = det.dataset.exp;
      const sum = det.querySelector("summary");
      if (det.open) openGroups.add(exp); else openGroups.delete(exp);
      sum.setAttribute("aria-expanded", String(det.open));
      det.addEventListener("toggle", () => {
        if (det.open) openGroups.add(exp); else openGroups.delete(exp);
        sum.setAttribute("aria-expanded", String(det.open));
      });
    });
    host.querySelectorAll("tr[data-key]").forEach(tr => {
      const go = () => { location.hash = caseHref(tr.dataset.key); };
      tr.addEventListener("click", e => { if (!e.target.closest("a")) go(); });
      tr.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); go(); } });
    });
    host.querySelectorAll("button[data-empty]").forEach(b => b.addEventListener("click", () => {
      if (b.dataset.empty === "all") filter = "all";
      showAll = true;
      syncUrl(); syncControls(); draw();
    }));
    wireScrollHints(root);
  };

  root.querySelectorAll("button[data-f]").forEach(b => b.addEventListener("click", () => {
    filter = b.dataset.f;
    if (filter === "problems" && !showAll) showAll = true;   // Problems means the failed rows too
    syncUrl(); syncControls(); draw();
  }));
  root.querySelector("#hw-show-all").addEventListener("click", () => {
    showAll = !showAll;
    syncUrl(); syncControls(); draw();
  });
  syncControls();
  draw();
}

// ── Case detail ─────────────────────────────────────────────────────────────

const TABS = [["overview", "Overview"], ["geometry3d", "Geometry 3D"], ["response", "Response"],
  ["polars", "Polars"], ["provenance", "Provenance"]];

function tabHref(key, tab, probe, phase) {
  const p = new URLSearchParams();
  if (tab !== "overview") p.set("tab", tab);
  if (tab === "response") {
    if (probe) p.set("probe", probe);
    p.set("phase", phase === "unwrapped" ? "unwrapped" : "wrapped");
  }
  const q = p.toString();
  return caseHref(key) + (q ? "?" + q : "");
}

const hashQuery = () => new URLSearchParams((location.hash.split("?")[1] || ""));

const PH_KEY = "hw.placeholders.open";
const phOpen = () => {
  try { const v = localStorage.getItem(PH_KEY); return v === null ? true : v === "1"; } catch { return true; }
};
const phRemember = open => { try { localStorage.setItem(PH_KEY, open ? "1" : "0"); } catch { /* storage blocked */ } };

/** Collapsible but loud (handoff §5.6): open on first visit, choice remembered per viewer. */
function placeholderBlock(items) {
  if (!items || !items.length) return "";
  const open = phOpen();
  const lis = items.map(p => {
    const term = termFor(p.token);
    return `<li><code title="${esc(term ? term.long : "")}">${esc(p.token)}</code> ${esc(p.text)}</li>`;
  }).join("");
  return `<details id="hw-placeholders"${open ? " open" : ""}>
    <summary aria-expanded="${open}"><span class="pill warn">Placeholders</span> <b>${items.length}</b> limitation${items.length === 1 ? "" : "s"}
      qualify every number on this page — <span id="hw-ph-hint">${open ? "hide the list" : "open for the list"}</span></summary>
    <div class="alert warn" role="note" style="margin:8px 0 0">
      <b>These placeholders qualify every number below.</b>
      <ul style="margin:6px 0 0 18px;padding:0">${lis}</ul>
    </div>
  </details>`;
}

/** Recorded staging token, if any — kept verbatim wherever it is shown. */
const stageToken = r => (r.tokens || []).find(t => String(t).startsWith("STAGE_FAILED"));

/**
 * One reconciled status band above the KPIs (P1 fix): a solved case and a recorded staging
 * failure are both true facts and must not contradict each other in two red blocks. The error
 * itself is shown once, verbatim, inside <details>.
 */
function caseStatusBand(r, d) {
  const token = stageToken(r);
  const refusal = d.refusal;
  if (!token && !refusal) return "";
  const verbatim = token || `STAGE_FAILED[${(refusal && refusal.error_type) || "?"}]: ${(refusal && refusal.error) || ""}`;
  const validate = d.validate
    ? ` Boundary Lab validate: rc ${esc(d.validate.returncode)}, valid ${esc(d.validate.valid)}.` : "";
  const details = `<details class="hw-refusal"><summary>Recorded staging error — verbatim</summary><pre class="hw-verbatim mono">${esc(verbatim)}</pre></details>`;
  if (r.state === "solved" && r.solve) {
    return `<section class="alert info hw-status-band" role="status"><div>
      <b>Curves solved (${esc(r.solve.done)}/${esc(r.solve.total)}) from a separate run.</b>
      The staging step itself recorded a failure, so the project on disk is not a shippable stage.${validate}
      </div>${details}</section>`;
  }
  const runLine = r.solve
    ? "A run directory exists, but no complete solved run was produced for this case."
    : "No solved run was produced for this case.";
  return `<section class="alert error hw-status-band" role="alert"><div>
    <b>Staging failed${refusal && refusal.error_type ? ` (${esc(refusal.error_type)})` : ""}.</b>
    ${esc(runLine)}${validate}
    </div>${details}</section>`;
}

/** One plain line under the KPI strip when the run has no horn excitation (P1 fix). */
function channelNote(run) {
  if (!run || !run.excitations) return "";
  if (run.excitations.some(e => e.per_input === "normal_velocity_mps")) return "";
  return `<p class="muted hw-channel-note">horn channel: not in this run</p>`;
}

export async function viewHwCase(root, key) {
  skel(root, "Loading case");
  let d;
  try { d = await api("/api/hw/case/" + encKey(key)); }
  catch (e) { busyDone(root); root.innerHTML = `<p><a href="#/hw/cases">← All cases</a></p>` + errBanner(e.message); return; }
  busyDone(root);
  const r = d.row;
  const run = d.run && !d.run.error ? d.run : null;
  const q = hashQuery();
  const tab = TABS.some(([k]) => k === q.get("tab")) ? q.get("tab") : "overview";
  const probe = q.get("probe");
  let phaseMode = q.get("phase") === "unwrapped" ? "unwrapped" : "wrapped";
  let probeMode = probe;
  const title = `${r.ref && r.ref !== "-" ? r.ref + " · " : ""}${r.gate || r.experiment}`;

  const pills = [
    statePill(r), fidelityBadge(r.fidelity),
    roleBadge("motor", r.motor), roleBadge("shape", r.transducer_shape),
    r.horn ? clearancePill(r.clearance) : "",
    r.integrity !== "ok" ? `<span class="pill bad" title="${esc(r.integrity)}">manifest ${esc(r.integrity.split(":")[0])}</span>` : "",
    r.kind ? `<span class="pill">${esc(r.kind)}</span>` : `<span class="pill warn">no manifest</span>`,
  ].filter(Boolean).join(" ");

  // Tokens other than STAGE_FAILED (shown once inside the status band) keep their verbatim
  // chip + plain-English gloss; clearance has its own pill already.
  const otherTokens = (r.tokens || []).filter(t => !isClearanceToken(t) && !String(t).startsWith("STAGE_FAILED"));

  root.innerHTML = `<div class="stack" style="gap:14px">
    ${pageHead({
      eyebrow: `Horn + woofer · Case · ${r.experiment}`,
      title, id: r.key, pills,
      story: "Story step 7 · Read the results — geometry, per-channel curves, polars and provenance.",
      storyTitle: "The woofer (Pa per 2.83 V) and the horn (Pa per 1 m/s) are never summed: no channel-calibration policy exists yet (risk R1).",
    })}
    <div class="run-toolbar">
      <nav class="run-tabs" aria-label="Views of this case">
        ${TABS.map(([k, l]) => `<a class="run-tab-link" data-tab="${k}" href="${tabHref(key, k, probe, phaseMode)}"${k === tab ? ' aria-current="page"' : ""}>${esc(l)}</a>`).join("")}
      </nav>
      <div class="run-actions"><a class="btn btn-sm" href="#/hw/cases">← All cases</a></div>
    </div>
    ${d.run && d.run.error ? errBanner("Result reader refused: " + d.run.error) : ""}
    ${caseStatusBand(r, d)}
    ${r.note ? `<div class="alert warn" role="note">${esc(r.note)}</div>` : ""}
    <div class="kpis hw-kpis-slim" id="hw-case-kpis"></div>
    ${channelNote(run)}
    ${otherTokens.length ? `<div class="pill-row" role="group" aria-label="Recorded tokens">${tokenChips(otherTokens)}</div>` : ""}
    ${placeholderBlock(d.placeholders)}
    <div id="hw-tab-body"></div>
  </div>`;

  root.querySelector("#hw-case-kpis").innerHTML = caseKpis(r, run);
  if (run) fillCaseLevels(root.querySelector("#hw-case-kpis"), key, run, probe);

  const ph = root.querySelector("#hw-placeholders");
  if (ph) ph.addEventListener("toggle", () => {
    phRemember(ph.open);
    ph.querySelector("summary")?.setAttribute("aria-expanded", String(ph.open));
    const hint = ph.querySelector("#hw-ph-hint");
    if (hint) hint.textContent = ph.open ? "hide the list" : "open for the list";
  });

  const body = root.querySelector("#hw-tab-body");
  // Keep the URL and every tab link in step with the response-tab controls (probe + phase).
  const syncTabHrefs = () => root.querySelectorAll('nav.run-tabs a[data-tab]').forEach(a => {
    a.setAttribute("href", tabHref(key, a.dataset.tab, probeMode, phaseMode));
  });
  const syncResponseUrl = () => {
    const p = new URLSearchParams();
    p.set("tab", "response");
    if (probeMode) p.set("probe", probeMode);
    p.set("phase", phaseMode);
    history.replaceState(null, "", caseHref(key) + "?" + p.toString());
  };

  if (tab === "overview") {
    body.innerHTML = `<div class="stack" style="gap:18px">
      <section class="fig">
        <div class="fig-head"><h3>Geometry</h3></div>
        <div id="hw-geo"></div>
      </section>
      <div class="grid2" style="align-items:start">
        <section class="card"><h3>Box and horn</h3>${boxTable(r, d)}</section>
        <section class="card"><h3>Related</h3>${relatedBlock(r)}
          <p class="muted" style="font-size:0.8rem;margin-top:6px">Fidelity, motor and transducer shape are
            declared in <code>docs/research/system_woofer_2026-11-18/readiness.yaml</code>; a case missing from
            it shows UNDECLARED. Nothing on this page infers them.</p>
        </section>
      </div>
    </div>`;
    drawGeometry(body.querySelector("#hw-geo"), d.geometry, r);
    wireScrollHints(root);
  } else if (tab === "geometry3d") {
    body.innerHTML = `<section class="card" id="hw-geo3d">
      <div class="fig-head"><h3>Geometry 3D</h3></div>
      <div id="hw-geo3d-host" data-v3d></div>
    </section>`;
    // Lazy: three.js and both mesh payloads are fetched only on this tab. The returned dispose is
    // also installed on the [data-v3d] host, which app.js's route() sweep calls before it replaces
    // the view, so a tab switch or route change frees the renderer, geometries and rAF loop.
    await mountHw3D(body.querySelector("#hw-geo3d-host"), key, {
      caseData: d,
      drawGeometry: el => drawGeometry(el, d.geometry, r),
    });
    wireScrollHints(root);
  } else if (tab === "response") {
    body.innerHTML = `<section class="card" id="hw-bases"><h3>${tip("per_input_ref", "Per-channel response")}</h3></section>`;
    if (!run) {
      body.querySelector("#hw-bases").insertAdjacentHTML("beforeend", notSolvedHtml(r, d));
    } else {
      await drawBases(body.querySelector("#hw-bases"), key, run, d.observation_caption, probe, phaseMode,
        id => { probeMode = id; syncTabHrefs(); syncResponseUrl(); },
        mode => { phaseMode = mode; syncTabHrefs(); syncResponseUrl(); });
    }
    wireScrollHints(root);
  } else if (tab === "polars") {
    body.innerHTML = `<section class="card" id="hw-polars"><h3>${tip("polar", "Polar cuts")}</h3></section>`;
    if (!run) {
      body.querySelector("#hw-polars").insertAdjacentHTML("beforeend", notSolvedHtml(r, d));
    } else {
      await drawPolars(body.querySelector("#hw-polars"), key, run, d.observation_caption);
    }
    wireScrollHints(root);
  } else {
    body.innerHTML = `<section class="card"><h3>Provenance</h3>
      <p class="muted" style="font-size:0.82rem;max-width:76ch">Hashes are shown in full and in the record's
        own wording. Each has a Copy button; if the browser blocks the clipboard, the hash is placed in a
        selected field so it can be copied by hand.</p>
      <p class="hint" role="status" id="hw-copy-status" style="font-size:0.8rem;min-height:1.2em"></p>
      ${provenanceBlock(d)}</section>`;
    wireCopyButtons(body);
    wireScrollHints(root);
  }
}

/** What a not-yet-solved case can say, and the next action it needs (handoff §1.6, §5.7). */
function notSolvedHtml(r, d) {
  const text = r.state === "staged"
    ? "Staged and validated, not solved — this case has no per-channel data yet."
    : "No solved run in this case.";
  const validate = d && d.validate
    ? ` Boundary Lab validate: rc ${esc(d.validate.returncode)}, valid ${esc(d.validate.valid)}.`
    : "";
  return `<p class="muted">${esc(text)}</p>
    <p class="muted" style="font-size:0.82rem">Solve is the full simulation (CPU, about 2.5 minutes for 25
      frequencies on this machine) and needs an authorization record; owner decision 6 is still open.${validate}</p>`;
}

function relatedBlock(r) {
  const links = [];
  if (r.parent) links.push(`<a href="${caseHref(r.parent)}">Staged project ${brk(r.parent)}</a>`);
  if (r.pair_with) links.push(`<a href="${caseHref(r.pair_with)}">Paired case ${brk(r.pair_with)}</a>`);
  links.push(`<a href="#/hw/cases">All cases</a>`);
  return `<ul style="margin:6px 0 0 18px;padding:0">${links.map(l => `<li>${l}</li>`).join("")}</ul>`;
}

function caseKpis(r, run) {
  const out = [];
  if (run && run.frequencies_hz && run.frequencies_hz.length) {
    const exs = run.excitations || [];
    out.push(`<div class="kpi"><span>Frequencies</span><b>${esc(run.frequencies_hz.length)} freqs</b>
      <small class="muted" style="font-size:0.72rem">${esc(bandText(run.frequencies_hz))}</small></div>`);
    if (exs.some(e => e.per_input === "V_rms")) {
      out.push(`<div class="kpi" data-level="woofer"><span>${tip("per_input_ref", "On-axis woofer")}</span>
        <b>${MISSING}</b><small class="muted" style="font-size:0.72rem">loading…</small></div>`);
    }
    if (exs.some(e => e.per_input === "normal_velocity_mps")) {
      out.push(`<div class="kpi" data-level="horn"><span>${tip("per_input_ref", "On-axis horn")}</span>
        <b>${MISSING}</b><small class="muted" style="font-size:0.72rem">loading…</small></div>`);
    }
  } else {
    out.push(kpi(esc("State"), STATE_LABEL[r.state] || r.state,
      esc(r.validate_valid === true ? "Boundary Lab validate passed" : ""), STATE_PILL[r.state] || ""));
  }
  if (r.horn) {
    const c = r.clearance || {};
    const pass = c.status === "PASS" && c.aabb_gap_m != null;
    const value = pass ? `${num(c.aabb_gap_m * 1000, 1)} mm` : (c.status || "NOT_CHECKED");
    const src = c.source === "replay" ? "replayed by the GUI" : c.source === "manifest" ? "recorded at staging" : "";
    out.push(kpi(tip("clearance", "Gap"), value, esc(pass ? "bounding-box lower bound" : src),
      pass ? "good" : c.status && c.status !== "NOT_CHECKED" ? "bad" : ""));
  }
  const b = r.box;
  if (b) {
    // Same 0.1 mm precision as the Box table below (371.2 × 371.2 × 1078.8), never a second rounding.
    out.push(`<div class="kpi"><span>Box</span><b style="font-size:0.9rem">${esc(`${num(b.width_mm, 1)} × ${num(b.height_mm, 1)} × ${num(b.depth_mm, 1)}`)}</b>
      <small class="muted" style="font-size:0.72rem">mm W×H×D</small></div>`);
  }
  return out.join("");
}

/** The two channel levels at the sample nearest 1 kHz — a selected API sample, never an interpolation. */
async function fillCaseLevels(kpiEl, key, run, wantProbe) {
  const probes = run.domains.filter(x => x.kind === "point_probe");
  if (!probes.length) {
    kpiEl.querySelectorAll("[data-level]").forEach(cell => { cell.querySelector("small").textContent = "no point probe in this run"; });
    return;
  }
  const probe = probes.find(p => p.id === wantProbe) || probes[0];
  let b;
  try { b = await api(`/api/hw/basis/${encKey(key)}?domain=${encodeURIComponent(probe.id)}`); }
  catch {
    kpiEl.querySelectorAll("[data-level]").forEach(cell => { cell.querySelector("small").textContent = "level unavailable"; });
    return;
  }
  const f = b.frequencies_hz;
  if (!f || !f.length) return;
  let i = 0;
  for (let k = 1; k < f.length; k++) if (Math.abs(f[k] - 1000) < Math.abs(f[i] - 1000)) i = k;
  const where = `probe ${probe.probe_id || probe.id} · nearest solved ${fmtHz(f[i])}`;
  for (const ex of b.excitations || []) {
    const slot = ex.per_input === "V_rms" ? kpiEl.querySelector('[data-level="woofer"]')
      : ex.per_input === "normal_velocity_mps" ? kpiEl.querySelector('[data-level="horn"]') : null;
    if (!slot) continue;
    const v = (ex.spl_db || [])[i];
    slot.querySelector("b").textContent = v == null ? MISSING : fmtDb(v);
    slot.querySelector("small").textContent = `${unitLabel(ex)} · ${where}`;
  }
  kpiEl.querySelectorAll("[data-level]").forEach(cell => {
    const small = cell.querySelector("small");
    if (small.textContent === "loading…") small.textContent = "no matching channel in this run";
  });
}

function kvTable(pairs) {
  // Fixed layout + anywhere-wrapping: sha256 strings and file lists must never widen the page.
  return `<div class="tbl-wrap"><table style="table-layout:fixed"><tbody>${pairs.filter(([, v]) => v !== undefined).map(([k, v]) =>
    `<tr><th scope="row" style="width:34%;white-space:normal">${esc(k)}</th><td style="white-space:normal;overflow-wrap:anywhere">${v}</td></tr>`).join("")}</tbody></table></div>`;
}

function boxTable(r, d) {
  const b = r.box;
  const pairs = [];
  if (b) {
    pairs.push(["Box W×H×D", esc(`${num(b.width_mm, 1)} × ${num(b.height_mm, 1)} × ${num(b.depth_mm, 1)} mm (wall ${num(b.wall_mm)} mm)`)]);
    pairs.push(["Driver", esc(`Ø ${num(b.driver_diameter_mm)} mm at y ${num(b.driver_y_mm, 1)} mm`)]);
    pairs.push(["Port", esc(`${num(b.port_area_cm2, 1)} cm², length ${num(b.port_length_mm, 1)} mm, y ${num(b.port_y_mm, 1)} mm, flare ${b.port_nfr ?? MISSING}`)]);
    pairs.push(["Mesh size", esc(`${fmtMm(b.mesh_size_mm)} / detail ${fmtMm(b.detail_size_mm)}`)]);
  } else pairs.push(["Box", `<span class="muted">no source parameters recorded</span>`]);
  if (r.horn) {
    pairs.push(["Horn mesh", `<code>${esc(r.horn.mesh)}</code> (${esc(r.horn.mesh_role)})`]);
    pairs.push(["Horn offset", esc(`(${(r.horn.translation_mm || []).join(", ")}) mm`)]);
    pairs.push(["Horn source group", `<code>${esc(r.horn.source_group)}</code> driven at 1 m/s`]);
    const c = r.clearance || {};
    pairs.push(["Clearance", `${clearancePill(c)} <small class="muted">${esc(c.source === "replay"
      ? "replayed by the GUI from the stored meshes" : c.source === "manifest" ? "recorded at staging" : "")}${c.vertex_min_distance_m != null
      ? `; closest vertices ${num(c.vertex_min_distance_m * 1000, 2)} mm` : ""}</small>`]);
  }
  const h = d.highlights || {};
  if (h.motor_mapping) {
    const x = h.motor_mapping.cross_checks || {};
    pairs.push(["Motor", esc(`${h.motor_mapping.driver_id} · dry Mmd ${h.motor_mapping.dry_mass_kg} kg`)]);
    pairs.push(["Motor cross-checks", esc(`Fs ${num(x.fs_error_percent, 2)} % · Vas ${num(x.vas_error_percent, 2)} % · Mms ${num(x.mms_error_percent, 2)} %`)]);
  }
  if (h.transducer_geometry) {
    const g = h.transducer_geometry;
    pairs.push(["Real driver geometry", `${g.complete ? "complete" : `<span class="warn-text">incomplete</span>`}: ${esc(Object.keys(g.refusals || {}).join(", ") || MISSING)} unavailable`]);
  }
  return kvTable(pairs);
}

// Two to-scale elevations (front x-y, side z-y), stacked at one shared scale, mm, in one SVG.
// Each elevation gets its own 100 mm scale bar; the side view also marks the driver/port y
// positions with dashed depth ticks so a vented-only case is not an empty rectangle.
export function drawGeometry(host, g, r) {
  if (!g) { host.innerHTML = `<p class="muted">No staged meshes on disk for this case.</p>`; return; }
  const [blo, bhi] = g.box_bbox_mm;
  const hb = g.horn_bbox_mm;
  const lo = hb ? blo.map((v, i) => Math.min(v, hb[0][i])) : blo;
  const hi = hb ? bhi.map((v, i) => Math.max(v, hb[1][i])) : bhi;
  const W = Math.max(360, host.clientWidth || 720), pad = 22, gutter = 130;
  const frontW = hi[0] - lo[0], sideW = hi[2] - lo[2], tall = hi[1] - lo[1];
  // Same scale for both views; the right gutter holds the side-view labels (never on a stroke).
  const s = Math.min((W - 2 * pad - gutter) / Math.max(frontW, sideW), 320 / tall);
  const viewH = 20 + tall * s + 34;          // title band + box + scale-bar band
  const H = 2 * viewH + 6;
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("width", "100%");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Front and side elevations of the box and horn, to scale");
  const ink = css("--ink"), muted = css("--muted"), accent = css("--accent") || "currentColor";
  const bad = css("--bad"), good = css("--good");
  const frontTop = 20, sideTop = viewH + 20;
  const Yf = y => frontTop + (hi[1] - y) * s;
  const Ys = y => sideTop + (hi[1] - y) * s;
  const FX = x => (W - frontW * s) / 2 + (x - lo[0]) * s;
  const SX = z => pad + (z - lo[2]) * s;       // left-aligned: the right gutter belongs to labels
  const label = (x, y, t, anchor = "start", col = muted, size = 12) => {
    const e = el("text", { x, y, "text-anchor": anchor, style: `fill:${col};font-size:${size}px` }, svg);
    e.textContent = t;
  };
  label(pad, 12, "Front (x–y)");
  label(pad, sideTop - 8, "Side (z–y)");
  // box
  el("rect", { x: FX(blo[0]), y: Yf(bhi[1]), width: frontW * s, height: tall * s,
    fill: "none", stroke: ink, "stroke-width": 1.4 }, svg);
  el("rect", { x: SX(blo[2]), y: Ys(bhi[1]), width: sideW * s, height: tall * s,
    fill: "none", stroke: ink, "stroke-width": 1.4 }, svg);
  // driver + port cutouts on the front view (source parameters; centred at x = 0). Labels sit
  // outside the box with leader lines, never across a circle stroke.
  const b = r.box;
  const leader = (x1, y1, x2, y2) => el("line", { x1, y1, x2, y2, stroke: muted,
    "stroke-width": 1, "stroke-dasharray": "2 2" }, svg);
  if (b && b.driver_diameter_mm) {
    const r0 = b.driver_diameter_mm / 2 * s;
    el("circle", { cx: FX(0), cy: Yf(b.driver_y_mm), r: r0, fill: "none",
      stroke: muted, "stroke-dasharray": "4 3" }, svg);
    leader(FX(0) - r0, Yf(b.driver_y_mm), FX(blo[0]) - 12, Yf(b.driver_y_mm));
    label(FX(blo[0]) - 18, Yf(b.driver_y_mm) + 4, `driver Ø${num(b.driver_diameter_mm)} mm`, "end", ink);
  }
  if (b && b.port_area_cm2) {
    const pr = Math.sqrt(b.port_area_cm2 * 100 / Math.PI);
    el("circle", { cx: FX(0), cy: Yf(b.port_y_mm), r: pr * s, fill: "none", stroke: muted, "stroke-dasharray": "2 2" }, svg);
    leader(FX(0) - pr * s, Yf(b.port_y_mm), FX(blo[0]) - 12, Yf(b.port_y_mm));
    label(FX(blo[0]) - 18, Yf(b.port_y_mm) + 4, `port ${num(b.port_area_cm2)} cm²`, "end", ink);
  }
  const poly = (pts, X, Y, col) => el("polygon", { points: pts.map(p => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(" "),
    fill: col, "fill-opacity": 0.18, stroke: col, "stroke-width": 1.4 }, svg);
  if (g.horn_front) poly(g.horn_front, FX, Yf, accent);
  if (g.horn_side) poly(g.horn_side, SX, Ys, accent);
  // Side view depth markers: the front-face opening (vertical dashed span) plus a dashed depth tick
  // at the recorded y. Labels live in the right gutter, outside every stroke.
  const sideFront = SX(bhi[2]);
  const sideMark = (y, rmm, text) => {
    const yy = Ys(y);
    el("line", { x1: sideFront, x2: sideFront, y1: Ys(y - rmm), y2: Ys(y + rmm),
      stroke: muted, "stroke-width": 1.2, "stroke-dasharray": "4 3" }, svg);
    el("line", { x1: sideFront, x2: SX(bhi[2] - 45), y1: yy, y2: yy,
      stroke: muted, "stroke-width": 1, "stroke-dasharray": "2 3" }, svg);
    leader(sideFront, yy, sideFront + 10, yy);
    label(sideFront + 14, yy + 4, text, "start", ink);
  };
  if (b && b.driver_diameter_mm) sideMark(b.driver_y_mm, b.driver_diameter_mm / 2, `driver y ${num(b.driver_y_mm, 1)} mm`);
  if (b && b.port_area_cm2) sideMark(b.port_y_mm, Math.sqrt(b.port_area_cm2 * 100 / Math.PI), `port y ${num(b.port_y_mm, 1)} mm`);
  // gap dimension on the side view
  const c = r.clearance;
  if (hb && c && c.status) {
    const ok = c.status === "PASS";
    const z0 = bhi[2], z1 = hb[0][2], yy = Math.min(bhi[1], hb[1][1]);
    const x0 = SX(z0), x1 = SX(z1);
    el("line", { x1: x0, x2: x1, y1: Ys(yy) - 8, y2: Ys(yy) - 8, stroke: ok ? good : bad, "stroke-width": 2 }, svg);
    // Label to the left of the dimension line, not above the driver marker label in the gutter.
    label(Math.min(x0, x1) - 4, Ys(yy) - 12, ok ? `gap ${num(c.aabb_gap_m * 1000, 1)} mm` : `${c.status}`, "end", ok ? good : bad);
  }
  // Side view: name the front face (BL frame: z forward, front face at max z).
  const faceX = SX(bhi[2]), faceY = Ys(blo[1]);
  el("line", { x1: faceX, x2: faceX, y1: faceY + 3, y2: faceY + 12, stroke: muted, "stroke-width": 1 }, svg);
  label(faceX - 2, faceY + 24, "↑ front face", "end", ink);
  // 100 mm scale bar in BOTH views (same scale, so both are directly comparable).
  for (const bottom of [Yf(blo[1]), Ys(blo[1])]) {
    el("line", { x1: pad, x2: pad + 100 * s, y1: bottom + 18, y2: bottom + 18, stroke: muted, "stroke-width": 2 }, svg);
    label(pad + 100 * s + 4, bottom + 22, "100 mm", "start", muted, 11);
  }
  if (g.horn_missing) label(pad, H - 3, g.horn_missing);
  host.innerHTML = "";
  host.appendChild(svg);
  host.insertAdjacentHTML("beforeend", `<p class="cap" style="margin:6px 0 0">Front and side are drawn at the
    same scale, each with its own 100 mm bar. Dashed marks in the side view show the recorded driver and port
    y positions on the front face. Outlines are convex hulls of the stored meshes in the Boundary Lab project
    frame; driver and port circles come from the source parameters.</p>
    ${!r.horn ? `<p class="cap hw-geo-note">vented only: no horn body in this run</p>` : ""}`);
}

function unitLabel(ex) {
  return ex.per_input === "V_rms" ? "dB SPL per 2.83 V" : ex.per_input === "normal_velocity_mps" ? "dB SPL per 1 m/s" : "dB SPL per " + (ex.per_input || "?");
}
function channelName(ex) {
  return ex.per_input === "V_rms" ? "Woofer (voltage port)" : ex.per_input === "normal_velocity_mps" ? "Horn (ideal velocity source)" : ex.id;
}

/** Break a wrapped phase trace at the ±180° jump. No dots are emitted, so no stray point survives. */
function breakWrapped(raw) {
  const segs = [];
  let cur = [];
  for (const p of raw) {
    if (p[1] == null || !isFinite(p[1])) { if (cur.length) segs.push(cur); cur = []; continue; }
    const prev = cur.length ? cur[cur.length - 1] : null;
    if (prev && Math.abs(p[1] - prev[1]) > 180) { segs.push(cur); cur = []; }
    cur.push(p);
  }
  if (cur.length) segs.push(cur);
  return segs;
}

async function drawBases(host, key, run, caption, initialProbe, initialPhase, onProbe, onPhase) {
  const probes = run.domains.filter(x => x.kind === "point_probe");
  if (!probes.length) {
    host.insertAdjacentHTML("beforeend", `<p class="muted">No point probes in this run, so there is nothing per-channel to plot here.</p>`);
    return;
  }
  if (!run.frequencies_hz || !run.frequencies_hz.length) {
    host.insertAdjacentHTML("beforeend", `<p class="muted">This run records no solved frequencies.</p>`);
    return;
  }
  const fmin = Math.min(...run.frequencies_hz), fmax = Math.max(...run.frequencies_hz);
  const selected = probes.some(p => p.id === initialProbe) ? initialProbe : probes[0].id;
  let phaseMode = initialPhase === "unwrapped" ? "unwrapped" : "wrapped";
  // One shared x treatment for every panel: the solved band plus a fixed 25 % right margin, so no
  // dead decade opens after the last solved frequency. Below fmin stays visible and is tinted.
  const xlim = [Math.min(20, fmin), Math.max(fmax * 1.25, 25)];
  const showNotSolved = fmin > xlim[0] + 0.5;
  const bandOpt = showNotSolved ? [xlim[0], fmin] : undefined;
  // Ticks stop at the last solved frequency; the axis itself keeps its 25 % margin.
  const xticks = logTicks(xlim[0], xlim[1]).filter(t => t <= fmax + 0.5);
  host.insertAdjacentHTML("beforeend", `
    <p class="cap" style="max-width:80ch">Each channel is plotted on its own axis, per its own reference input. They are
      <b>not summed</b>: the woofer is referenced to 2.83 V and the horn to 1 m/s, and there is no calibration policy yet (R1).</p>
    <div class="hw-chart-controls">
      <label>Probe <select id="hw-probe">${probes.map(p =>
        `<option value="${esc(p.id)}"${p.id === selected ? " selected" : ""}>${esc(p.probe_id || p.id)} (${num(p.distance_m, 2)} m)</option>`).join("")}</select></label>
      <div class="hw-phase-toggle" role="group" aria-label="Phase display">
        <button type="button" class="btn btn-sm" data-phase="wrapped" aria-pressed="${phaseMode === "wrapped"}">Phase: wrapped</button>
        <button type="button" class="btn btn-sm" data-phase="unwrapped" aria-pressed="${phaseMode === "unwrapped"}">Phase: unwrapped</button>
      </div>
    </div>
    <div class="grid2" id="hw-basis-charts" style="gap:12px;margin-top:10px"></div>
    ${showNotSolved ? `<p class="legend hw-chart-legend"><span class="hw-swatch hw-swatch-band"></span>not solved below ${fmtHz(fmin)}</p>` : ""}
    <p class="cap" style="font-size:0.8rem">${esc(caption || "")}</p>`);
  host.querySelectorAll("button[data-phase]").forEach(btn => btn.addEventListener("click", () => {
    const mode = btn.dataset.phase === "unwrapped" ? "unwrapped" : "wrapped";
    if (mode === phaseMode) return;
    phaseMode = mode;
    host.querySelectorAll("button[data-phase]").forEach(b =>
      b.setAttribute("aria-pressed", String(b.dataset.phase === phaseMode)));
    if (onPhase) onPhase(phaseMode);
    draw();
  }));
  const sel = host.querySelector("#hw-probe"), box = host.querySelector("#hw-basis-charts");
  const draw = async () => {
    box.innerHTML = `<p class="muted" role="status">Loading…</p>`;
    let b;
    try { b = await api(`/api/hw/basis/${encKey(key)}?domain=${encodeURIComponent(sel.value)}`); }
    catch (e) { box.innerHTML = errBanner(e.message); return; }
    box.innerHTML = "";
    b.excitations.forEach((ex, i) => {
      const cell = document.createElement("div");
      cell.innerHTML = `<h3 style="margin:0 0 4px;font-size:0.95rem">${esc(channelName(ex))}</h3>
        <p class="muted" style="margin:0 0 4px;font-size:0.78rem">${esc(ex.reference || "")} · <code>${esc(ex.id)}</code></p>`;
      const mag = document.createElementNS(NS, "svg"), ph = document.createElementNS(NS, "svg");
      cell.append(mag, ph); box.appendChild(cell);
      const pts = b.frequencies_hz.map((f, k) => [f, ex.spl_db[k]]);
      const ys = pts.map(p => p[1]).filter(v => v != null);
      const ylo = Math.floor((Math.min(...ys) - 3) / 5) * 5, yhi = Math.ceil((Math.max(...ys) + 3) / 5) * 5;
      const color = i ? css("--best") : css("--accent");
      chart(mag, { W: 420, H: 260, xlog: true, xlim, ylim: [ylo, yhi], yticks: niceTicks(ylo, yhi, 5),
        xticks, xlabel: "Frequency (Hz)", ylabel: `SPL (${unitLabel(ex)})`,
        series: [{ pts, color, w: 2 }, { pts, color, dots: true, r: 2.2 }], band: bandOpt,
        ariaLabel: `${channelName(ex)} level at ${sel.value}` });
      // Phase is one connected line. Wrapped mode breaks the stroke at ±180°; no dots are drawn at
      // those breaks. Unwrapped mode uses the Python-computed continuous series and its own y range.
      const wrapped = b.frequencies_hz.map((f, k) => [f, ex.phase_deg[k]]);
      const unwrapped = Array.isArray(ex.phase_unwrapped_deg)
        ? b.frequencies_hz.map((f, k) => [f, ex.phase_unwrapped_deg[k]]) : null;
      const useUnwrapped = phaseMode === "unwrapped" && !!unwrapped;
      let series, ylim, yticks;
      if (useUnwrapped) {
        const vals = unwrapped.map(p => p[1]).filter(v => v != null && isFinite(v));
        let lo = Math.min(...vals), hi = Math.max(...vals);
        const span = hi - lo;
        const step = span <= 540 ? 90 : span <= 1080 ? 180 : 270;
        let p0 = Math.floor((lo - 20) / step) * step, p1 = Math.ceil((hi + 20) / step) * step;
        if (!isFinite(p0) || !isFinite(p1) || p1 - p0 < 180) { p0 = Math.min(p0, -180); p1 = Math.max(p1, 180); }
        ylim = [p0, p1]; yticks = [];
        for (let v = p0; v <= p1 + 1e-9; v += step) yticks.push(v);
        series = [{ pts: unwrapped, color, w: 2 }];
      } else {
        ylim = [-180, 180]; yticks = [-180, -90, 0, 90, 180];
        series = breakWrapped(wrapped).map(s => ({ pts: s, color, w: 2 }));
      }
      chart(ph, { W: 420, H: 190, xlog: true, xlim, ylim, yticks,
        xticks, xlabel: "Frequency (Hz)", ylabel: "Phase (°)",
        series, band: bandOpt,
        ariaLabel: `${channelName(ex)} phase, ${phaseMode}, at ${sel.value}` });
      if (phaseMode === "unwrapped" && !unwrapped) {
        cell.insertAdjacentHTML("beforeend",
          `<p class="muted" style="font-size:0.78rem">unwrapped phase is not in this run; showing wrapped.</p>`);
      }
    });
  };
  sel.addEventListener("change", () => { draw(); if (onProbe) onProbe(sel.value); });
  await draw();
}

/** Small colour scale for polarMap's fixed −40…0 dB ramp (cmap in charts.js; nothing redefined here). */
function dbLegendHtml() {
  const W = 180, H = 12, n = 60;
  const rects = Array.from({ length: n }, (_, i) => {
    const c = cmap(i / (n - 1)).join(",");
    return `<rect x="${(i * W / n).toFixed(1)}" y="0" width="${(W / n + 0.5).toFixed(1)}" height="${H}" fill="rgb(${c})"/>`;
  }).join("");
  return `<div class="hw-db-legend">
    <span class="muted">−40 dB</span>
    <svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img"
      aria-label="Colour scale: 0 dB is pale yellow, -40 dB is dark navy">${rects}</svg>
    <span class="muted">0 dB</span><span class="muted">level relative to on-axis</span>
  </div>`;
}

async function drawPolars(host, key, run, caption) {
  const cuts = run.domains.filter(x => x.kind === "polar_observation");
  if (!cuts.length) {
    host.insertAdjacentHTML("beforeend", `<p class="muted">No polar cuts in this run.</p>`);
    return;
  }
  host.insertAdjacentHTML("beforeend", `<p class="cap" style="max-width:80ch">Level relative to each channel's own 0° value at each
    frequency. Frequency (Hz) runs up the y axis; ${fmtDeg(-90)} to ${fmtDeg(90)} across. Low frequencies at the bottom. ${esc(caption || "")}</p>
    ${dbLegendHtml()}
    <div class="grid2" id="hw-polar-grid" style="gap:12px"></div>`);
  const grid = host.querySelector("#hw-polar-grid");
  const key2 = encKey(key);
  // First build EVERY cell + SVG, then draw. polarMap measures its container once and never
  // redraws on resize; measuring while the grid still had one child made the first panel ~2× wide
  // and its tick labels tiny (the G0 polar bug). Same H and same column width now align both axes.
  const pending = [];
  for (const cut of cuts) {
    let b;
    try { b = await api(`/api/hw/basis/${key2}?domain=${encodeURIComponent(cut.id)}`); }
    catch (e) { grid.insertAdjacentHTML("beforeend", errBanner(e.message)); continue; }
    const keep = b.angles_deg.map((a, i) => [a, i]).filter(([a]) => a >= -90 && a <= 90);
    const angles = keep.map(([a]) => a);
    for (const ex of b.excitations) {
      const cell = document.createElement("div");
      cell.innerHTML = `<h3 style="margin:0 0 4px;font-size:0.95rem">${esc(channelName(ex))} · ${esc(cut.plane || cut.id)}</h3>`;
      const svg = document.createElementNS(NS, "svg");
      svg.dataset.chart = "1"; svg.style.width = "100%";
      svg.setAttribute("role", "img");
      svg.setAttribute("aria-label", `${channelName(ex)} polar cut ${cut.plane || cut.id}, level relative to on-axis, in dB`);
      cell.appendChild(svg); grid.appendChild(cell);
      const rows = ex.rel_db.map(row => keep.map(([, i]) => row[i] == null ? null : Math.max(-40, Math.min(0, row[i]))));
      pending.push({ svg, rows, angles, freqs: b.frequencies_hz });
    }
  }
  for (const p of pending) {
    polarMap(p.svg, p.rows, p.angles, p.freqs, { H: 300 });
    // polarMap puts a standalone "Hz" at the top-left, where it collides with the top tick (Hz2.5k).
    // The unit is stated in the caption instead; drop the colliding text only.
    [...p.svg.querySelectorAll("text")].filter(t => t.textContent === "Hz").forEach(t => t.remove());
  }
}

// ── Provenance ──────────────────────────────────────────────────────────────

const hashCell = v => (v == null || v === ""
  ? `<span class="muted">${MISSING}</span>`
  : `<span class="hw-hash"><code>${esc(v)}</code><button type="button" class="btn btn-sm" data-copy="${esc(v)}">Copy</button></span>`);

function provenanceBlock(d) {
  const r = d.row, run = d.run, pairs = [];
  pairs.push(["Manifest integrity", r.integrity === "ok" ? `<span class="pill good">ok</span>` : `<span class="pill bad">${esc(r.integrity)}</span>`]);
  const h = d.highlights || {};
  if (h.authorized_by) pairs.push(["Authorized by", esc(h.authorized_by)]);
  if (h.project_sha256) pairs.push(["Project sha256", hashCell(h.project_sha256)]);
  if (h.configuration_patch_sha256) pairs.push(["Configuration patch sha256", hashCell(h.configuration_patch_sha256)]);
  if (h.spec_sha256) pairs.push(["Spec sha256", hashCell(h.spec_sha256)]);
  if (d.validate) pairs.push(["BL validate", esc(`rc ${d.validate.returncode} · valid ${d.validate.valid}`)]);
  if (d.bl_root) pairs.push(["Boundary Lab", esc(`${d.bl_root.version || "?"} @ ${(d.bl_root.git_head || "").slice(0, 12) || "?"} (${d.bl_root.path || ""})`)]);
  if (run && !run.error) {
    const p = run.provenance || {};
    pairs.push(["Solve", esc(`${p.backend_id} · ${p.solve_kind} · ${p.status} · ${(run.frequencies_hz || []).length} freqs`)]);
    pairs.push(["Phasor", esc(`${p.phasor_convention} → ${p.phasor_conversion}`)]);
    pairs.push(["Geometry identity", hashCell(p.source_geometry_hash)]);
    pairs.push(["Run manifest sha256", hashCell(p.manifest_sha256)]);
    if (run.solver_options) pairs.push(["Solver options", `<code style="white-space:pre-wrap">${esc(JSON.stringify(run.solver_options))}</code>`]);
    pairs.push(["Started / finished", esc(`${run.started_at_utc || "?"} → ${run.finished_at_utc || "?"}`)]);
    const dq = run.data_quality || {};
    pairs.push(["Claims allowed", esc((dq.claims_allowed || []).join(", "))]);
    pairs.push(["Claims refused", esc((dq.claims_refused || []).join(", "))]);
  }
  pairs.push(["Files", `<code style="white-space:normal">${esc((d.files || []).join("  "))}</code>`]);
  return kvTable(pairs);
}

function wireCopyButtons(host) {
  host.querySelectorAll("button[data-copy]").forEach(btn => btn.addEventListener("click", async () => {
    const status = document.getElementById("hw-copy-status");
    const text = btn.dataset.copy;
    try {
      if (!navigator.clipboard || !window.isSecureContext) throw new Error("clipboard unavailable");
      await navigator.clipboard.writeText(text);
      btn.textContent = "Copied";
      if (status) status.textContent = "Copied to the clipboard.";
      setTimeout(() => { btn.textContent = "Copy"; }, 1500);
    } catch {
      // Visible fallback (handoff §5.6): a selected, read-only field the user can copy by hand.
      const inp = document.createElement("input");
      inp.type = "text"; inp.value = text; inp.readOnly = true; inp.className = "mono";
      inp.style.cssText = "width:min(100%,28rem);padding:2px 6px;border:1px solid var(--control-border);border-radius:4px;background:var(--surface);color:var(--ink)";
      inp.setAttribute("aria-label", "Hash to copy by hand");
      btn.replaceWith(inp);
      inp.focus(); inp.select();
      if (status) status.textContent = "Copy is not available here — the hash is selected; press Ctrl+C.";
    }
  }));
}

// ── Readiness board ─────────────────────────────────────────────────────────

export async function viewHwReadiness(root) {
  skel(root, "Loading readiness");
  let d;
  try { d = await api("/api/hw/readiness"); } catch (e) { busyDone(root); root.innerHTML = errBanner(e.message); return; }
  busyDone(root);
  const risks = d.risks || [], decisions = d.decisions || [];
  const level = l => risks.filter(x => String(x.level || "").toUpperCase() === l).length;
  const openRisks = risks.filter(x => x.status !== "closed").length;
  const inProgress = risks.filter(x => x.status === "in_progress").length;
  const openDecisions = decisions.filter(x => x.status !== "closed").length;
  const c = d.counts || {};

  // Levels: CRITICAL bad, HIGH warn, MEDIUM accent, LOW muted — colour is never the only signal.
  const lvlClass = { CRITICAL: "bad", HIGH: "warn", MEDIUM: "hw-lvl-medium", LOW: "hw-lvl-low" };
  const statusBadge = x => {
    if (!x.status || x.status === "open") return "";
    const good = x.status === "closed";
    return `<span class="pill ${good ? "good" : "warn"}">${esc(String(x.status).replace(/_/g, " "))}</span>`;
  };
  // Evidence wraps at spaces; only a genuinely long identifier gets an anywhere-break span.
  const evidenceHtml = s => dash(s).split(/(\s+)/).map(part => {
    if (!part) return "";
    if (/^\s+$/.test(part)) return part;
    return part.length > 22 ? `<span class="hw-long-id">${esc(part)}</span>` : esc(part);
  }).join("");
  const caseLine = [
    `${c.solved ?? 0} solved`, `${c.staged ?? 0} staged`, `${c.stage_failed ?? 0} stage failed`,
    `${c.solve_failed ?? 0} solve failed`, `${c.recorded ?? 0} recorded`, `${c.empty ?? 0} empty`,
  ].join(" · ");

  root.innerHTML = `<div class="stack" style="gap:18px">
    ${pageHead({
      eyebrow: "Horn + woofer · Readiness · risk register",
      title: "Readiness",
      id: d.registry,
      story: "The risks and open owner decisions that gate steps 5–7 of the system story.",
      storyTitle: "Steps 5–7: Check in Boundary Lab → Solve → Read. Cases are counted live from disk; risks and decisions come from the readiness registry.",
      pills: `<span class="pill">updated ${esc(d.updated || MISSING)}</span>`,
    })}
    ${d.registry_error ? errBanner(d.registry_error) : ""}
    <div class="kpis">
      ${kpi(esc("Risks"), risks.length, esc(`${openRisks} open${inProgress ? ` · ${inProgress} in progress` : ""}`))}
      ${kpi(esc("Critical"), level("CRITICAL"), "", "bad")}
      ${kpi(esc("High"), level("HIGH"), "", "warn")}
      ${kpi(esc("Medium"), level("MEDIUM"), "", "hw-lvl-medium")}
      ${kpi(esc("Low"), level("LOW"), "", "hw-lvl-low")}
      ${kpi(esc("Open decisions"), openDecisions, esc(`of ${decisions.length} owner decisions`), openDecisions ? "warn" : "good")}
    </div>
    <p class="muted hw-case-count-line">Cases on disk: ${esc(caseLine)}.</p>
    <section class="card"><h3>Open owner decisions</h3>
      <div class="tbl-scroll hw-tbl-scroll">
        <p class="tbl-scroll-hint">scroll for all columns →</p>
        <div class="tbl-wrap"><table class="hw-readiness-table hw-decisions-table">
          <colgroup><col style="width:5%"><col style="width:40%"><col style="width:40%"><col style="width:15%"></colgroup>
          <thead><tr><th>#</th><th>Decision</th><th>Recommendation</th><th>Status</th></tr></thead><tbody>
          ${decisions.map(x => `<tr>
            <td>${esc(x.id)}</td>
            <td class="hw-wrap">${esc(x.question)}</td>
            <td class="hw-wrap">${esc(x.recommendation)}</td>
            <td>${x.status === "open" ? `<span class="muted">open</span>` : statusBadge(x)}</td></tr>`).join("")}
        </tbody></table></div>
      </div>
    </section>
    <section class="card"><h3>Risk register</h3>
      <div class="tbl-scroll hw-tbl-scroll">
        <p class="tbl-scroll-hint">scroll for all columns →</p>
        <div class="tbl-wrap"><table class="hw-readiness-table hw-risk-table">
          <colgroup><col style="width:12%"><col style="width:10%"><col style="width:28%">
            <col style="width:12%"><col style="width:16%"><col style="width:22%"></colgroup>
          <thead><tr><th>Risk</th><th>Level</th><th>What</th><th>Closes under</th><th>Blocked by</th><th>Evidence</th></tr></thead><tbody>
          ${risks.map(x => {
            const lv = String(x.level || "").toUpperCase();
            const st = statusBadge(x);
            return `<tr>
              <td class="hw-risk-id">${esc(x.id)}${st ? `<br>${st}` : ""}</td>
              <td><span class="pill ${lvlClass[lv] || ""}">${esc(lv || MISSING)}</span></td>
              <td class="hw-wrap">${esc(x.title)}</td>
              <td class="hw-nowrap">${esc(dash(x.wp))}</td>
              <td class="hw-wrap">${esc(dash(x.blocked_by))}</td>
              <td class="hw-wrap hw-evidence-cell">${evidenceHtml(x.evidence)}</td></tr>`;
          }).join("")}
        </tbody></table></div>
      </div>
    </section>
    <div class="btn-row"><a class="btn btn-sm" href="#/hw/cases">← All cases</a></div>
  </div>`;
  wireScrollHints(root);
}
