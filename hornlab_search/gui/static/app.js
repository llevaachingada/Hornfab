// app.js — hornlab-search GUI   AGPL-3.0-or-later
// Single-page app with hash routing. No build step, vanilla ES modules.

import { chart, heat, cmap, drawCbar, niceTicks, diFromCuts, groupColor,
         el, NS, css, fmt, FT, DEFW, polarMap, wallSection, familyColor, measuredWidth, isobarMap } from "./charts.js";
import { TERMS as GLOSSARY, TERM_ORDER, tip } from "./glossary.js";
import { init3d } from "./view3d.js";
import { viewEvolution } from "./evolution.js";

// ── XSS helper ─────────────────────────────────────────────────────
function esc(s) {
  return (s == null ? "–" : String(s))
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ── Number / unit helpers ───────────────────────────────────────────
// fmt(v, d) is imported from charts.js (2 decimals default)
const fmtHz  = v => v == null ? "–" : v >= 1000 ? (v/1000).toFixed(1) + " kHz" : Math.round(v) + " Hz";
const fmtDeg = v => v == null ? "–" : Number(v).toFixed(0) + "°";
const fmtMm  = v => v == null ? "–" : Math.round(v) + " mm";
const fmtDb  = v => v == null ? "–" : Number(v).toFixed(1) + " dB";
const fmtPct = v => v == null ? "–" : Number(v).toFixed(0) + "%";

// ── API helpers ────────────────────────────────────────────────────

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) { const t = await r.text().catch(() => ""); throw new Error(`${r.status} ${t}`); }
  return r.json();
}

async function post(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({ error: "invalid response" }));
  return j;
}

// ── Routing ────────────────────────────────────────────────────────

// The view container is REPLACED on every navigation: a slow view that finishes after the user has
// moved on then writes into a detached element instead of painting over the current page.
let ROOT = document.getElementById("view-root");
const currentRoot = () => ROOT;

const ROUTES = [
  { re: /^#\/$|^#\/home$/,              fn: () => viewHome() },
  { re: /^#\/status$/,                  fn: () => viewStatus() },
  { re: /^#\/campaigns$/,               fn: () => viewCampaignsList() },
  { re: /^#\/campaign\/(.+)$/,          fn: m => viewCampaignDetail(m[1]) },
  { re: /^#\/runs$/,                    fn: () => viewRunsList() },
  { re: /^#\/run\/(.+)\/3d$/,           fn: m => viewRun3D(m[1]) },
  { re: /^#\/run\/(.+)\/evolution$/,    fn: m => viewEvolution(ROOT, m[1]) },
  { re: /^#\/run\/(.+)\/archive$/,      fn: m => viewRunArchive(m[1]) },
  { re: /^#\/run\/(.+)$/,               fn: m => viewRunDetail(m[1]) },
  { re: /^#\/compare$/,                 fn: () => viewCompare() },
  { re: /^#\/briefs$/,                  fn: () => viewBriefs() },
  { re: /^#\/launch$/,                  fn: () => viewLaunch() },
  { re: /^#\/typologies$/,              fn: () => viewTypologies() },
  { re: /^#\/glossary$/,                fn: () => viewGlossary() },
];

function route() {
  // Dispose any 3D scene
  const old = document.getElementById("view3d-wrap");
  if (old?._dispose3d) old._dispose3d();
  // Clear status timer if navigating away
  if (!location.hash.startsWith("#/status") && location.hash !== "" && location.hash !== "#/") {
    clearStatusTimer();
  }

  const fresh = document.createElement("div");
  fresh.id = "view-root"; fresh.className = ROOT.className; fresh.setAttribute("role", "main");
  ROOT.replaceWith(fresh); ROOT = fresh;
  const hash = location.hash || "#/home";
  const path = hash.split("?")[0];
  for (const { re, fn } of ROUTES) {
    const m = path.match(re);
    if (m) { updateNav(path); return fn(m); }
  }
  ROOT.innerHTML = "";
  const p = document.createElement("p"); p.className = "muted";
  p.textContent = "Unknown view: " + hash;  // textContent: never inject URL as HTML
  ROOT.appendChild(p);
}

function updateNav(hash) {
  document.querySelectorAll("#app-nav ul li a").forEach(a => {
    const h = a.getAttribute("href");
    const isActive =
      (h === "#/home" && (hash === "#/" || hash === "#/home")) ||
      (h === "#/status" && hash === "#/status") ||
      (h === "#/campaigns" && (hash === "#/campaigns" || hash.startsWith("#/campaign/"))) ||
      (h === "#/runs" && (hash === "#/runs" || (hash.startsWith("#/run/") && !hash.endsWith("/3d")))) ||
      (h === "#/compare" && hash === "#/compare") ||
      (h === "#/briefs" && hash === "#/briefs") ||
      (h === "#/launch" && hash === "#/launch") ||
      (h === "#/glossary" && hash === "#/glossary");
    a.classList.toggle("active", isActive);
  });
}

window.addEventListener("hashchange", route);

// ── Shared helpers ─────────────────────────────────────────────────

function skel(msg = "") {
  ROOT.innerHTML = `<div class="stack skeleton" style="gap:18px;opacity:0.6">
    <div class="skeleton-block" style="height:2.2rem;width:min(260px,60%)"></div>
    <div class="skeleton-block" style="height:1rem;width:min(400px,80%)"></div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--rule);border:1px solid var(--rule);border-radius:6px;overflow:hidden">
      ${[0,0,0,0].map(()=>`<div class="skeleton-block" style="height:64px"></div>`).join("")}
    </div>
    <div class="skeleton-block" style="height:180px"></div>
    ${msg ? `<p class="muted" style="opacity:0.5;font-size:0.82rem">${esc(msg)}</p>` : ""}
  </div>`;
}

function errBanner(msg) {
  return `<div class="alert error" role="alert"><b>Error:</b> ${esc(msg)}</div>`;
}

/** "40 % better" / "3 % worse" / "–": score change from the starting design (lower score = better).
 *  A start that failed (1000 penalty) has no meaningful percentage. */
const CMP_LABEL = {
  bw_h_deg: "Beamwidth, horizontal", bw_v_deg: "Beamwidth, vertical", di_db: "Directivity index",
  on_axis_db: "On-axis response", ripple_h_db: "Polar ripple, horizontal", ripple_v_db: "Polar ripple, vertical",
};

function betterPct(seed, best) {
  if (best == null || !seed || seed >= 900) return "–";
  const p = (1 - best / seed) * 100;
  if (Math.abs(p) < 0.05) return "no change";
  return `${Math.abs(p).toFixed(0)} % ${p > 0 ? "better" : "worse"}`;
}

/** Brief, non-blocking message in the corner (replaces alert()). */
function showToast(msg, kind = "info") {
  let box = document.getElementById("toasts");
  if (!box) { box = document.createElement("div"); box.id = "toasts"; box.setAttribute("aria-live", "polite"); document.body.appendChild(box); }
  const t = document.createElement("div"); t.className = "toast " + kind; t.textContent = msg;
  box.appendChild(t); setTimeout(() => t.remove(), kind === "error" ? 9000 : 4500);
}

function pill(text, cls) {
  return `<span class="pill ${cls}">${esc(text)}</span>`;
}

function timeSince(iso) {
  if (!iso) return "–";
  const s = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function failurePills(obj) {
  return Object.entries(obj || {})
    .filter(([, v]) => v > 0)
    .map(([k, v]) => `<span class="pill bad">${esc(v + "× " + k.replace(/_/g, " "))}</span>`)
    .join(" ") || pill("none", "good");
}

function dimStr(dims) {
  if (!dims) return "–";
  return `${fmtMm(dims.mouth_w_mm)} × ${fmtMm(dims.mouth_h_mm)} × ${fmtMm(dims.depth_mm)}`;
}

// ── View HOME ──────────────────────────────────────────────────────

async function viewHome() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel("Loading dashboard…");
  let statusData, campaigns, runs, leaders;
  try {
    [statusData, campaigns, runs, leaders] = await Promise.all([
      api("/api/status"),
      api("/api/campaigns").catch(() => []),
      api("/api/runs").catch(() => []),
      api("/api/leaders").catch(() => []),
    ]);
  } catch (e) {
    ROOT.innerHTML = errBanner("Could not load home: " + e.message);
    return;
  }

  const cur = statusData.current;
  const lock = statusData.gpu_lock;
  const steps = (statusData.queue_log || {}).steps || [];

  // GPU / running card
  let gpuCard;
  if (cur && lock && lock.alive) {
    const budget = cur.budget || 1;
    const pct = Math.min(100, Math.round((cur.n / budget) * 100));
    const over = !!(cur.budget && cur.n > cur.budget);
    const budgetCls = over ? "bad" : pct >= 90 ? "warn" : "";
    const nFail = Object.values(cur.failures || {}).reduce((a, v) => a + v, 0);
    const barCls = over ? "bad" : nFail / Math.max(cur.n, 1) > 0.3 ? "warn" : "";
    const eta = cur.eta_min != null ? `~${Math.round(cur.eta_min)} min left` : "";
    const rate = cur.rate_per_h != null ? `${cur.rate_per_h.toFixed(0)}/h` : "";
    gpuCard = `<div class="card status-card running-card">
      <div class="label">▶ Running: ${esc(cur.name || cur.id)}</div>
      <div style="margin:6px 0">
        <div class="progress-wrap"><div class="progress-bar ${barCls}" style="width:${pct}%"></div></div>
        <div style="display:flex;justify-content:space-between;margin-top:4px;font-size:0.8rem;color:var(--muted)">
          <span><b class="${budgetCls}">${cur.n.toLocaleString()} / ${budget.toLocaleString()} evals (${pct}%)${over ? " over budget" : ""}</b></span>
          <span>${eta}</span>
        </div>
      </div>
      <div class="kpis" style="margin-top:4px">
        <div class="kpi"><span>Best score</span><b>${fmt(cur.best_j)}</b></div>
        <div class="kpi"><span>Started score</span><b>${fmt(cur.seed_j && cur.seed_j < 900 ? cur.seed_j : null)}</b></div>
        <div class="kpi"><span>Rate</span><b>${rate || "–"}</b></div>
        <div class="kpi"><span>Failures</span><b>${esc(Object.values(cur.failures || {}).reduce((a, v) => a + v, 0))}</b></div>
      </div>
      <div class="btn-row" style="margin-top:8px">
        <a class="btn primary" href="#/run/${esc(cur.id)}">Open run →</a>
        <a class="btn" href="#/status">Status</a>
      </div>
    </div>`;
  } else {
    gpuCard = `<div class="card status-card gpu-idle-card">
      <div class="label">GPU</div>
      <div class="value">Idle</div>
      <div class="btn-row" style="margin-top:8px">
        <a class="btn primary" href="#/launch">Launch a dry-run →</a>
        <a class="btn" href="#/status">Status</a>
      </div>
    </div>`;
  }

  // Queue timeline
  let timelineHtml = "";
  if (steps.length) {
    timelineHtml = `<div class="card" style="min-width:0">
      <div class="eyebrow" style="margin-bottom:10px">Overnight queue — ${esc((statusData.queue_log || {}).name || "")}</div>
      <div class="timeline">
        ${steps.slice(-20).map(s => {
          const dot = s.skipped ? "skip" : s.exit == null ? "run" : s.exit === 0 ? "done" : "failed";
          const dur = (s.started && s.ended)
            ? (() => { const ms = new Date(s.ended) - new Date(s.started); return ms > 60000 ? (ms/60000).toFixed(1)+"m" : (ms/1000).toFixed(0)+"s"; })()
            : s.skipped ? "skipped" : s.started ? "running" : "";
          const exitNote = s.exit != null && s.exit !== 0 ? `<span class="tl-exit-bad">exit ${s.exit}</span>` : "";
          return `<div class="tl-row">
            <div class="tl-dot ${dot}" title="${dot}"></div>
            <span class="tl-name">${esc(s.name)}</span>
            <span class="tl-time">${esc(dur)} ${exitNote}</span>
          </div>`;
        }).join("")}
      </div>
    </div>`;
  }

  // Best horn per brief: from /api/leaders (latest campaign of the strongest tier per brief, ranked by
  // median score; never from raw runs, which include superseded and out-of-envelope designs)
  let bestBriefHtml = "";
  if (leaders.length) {
    const rows = leaders.map(l => {
      const verdict = l.tier === "compare"
        ? (l.clearly_ahead ? pill("clearly ahead", "good") : pill("not separated", "warn"))
        : pill("screen only", "warn");
      const link = l.best_run_id ? `href="#/run/${esc(l.best_run_id)}"` : "";
      return `<a class="best-brief-row" ${link}>
        <div>
          <div class="bbr-name">${esc(l.brief)}</div>
          <div class="bbr-meta">${esc(l.family)} · ${esc(l.dims ? dimStr(l.dims) : "–")} · ${verdict}</div>
          <div class="bbr-meta muted">${esc(l.tier)} campaign, ${esc(l.n_families)} families${l.runner_up ? `; next: ${esc(l.runner_up)} (+${fmt(l.gap)})` : ""}</div>
        </div>
        <div class="bbr-score" title="median score over repeats (lower is better)">${fmt(l.median_j)}</div>
      </a>`;
    }).join("");
    bestBriefHtml = `<div class="card">
      <div class="eyebrow" style="margin-bottom:10px">Best horn per brief</div>
      <p class="muted" style="margin:0 0 8px;font-size:0.82rem">Median score of the leading family in the latest campaign for each brief (lower is better). Size is the outer mouth width × height × depth of its best design.</p>
      <div class="best-brief-grid">${rows}</div>
    </div>`;
  } else {
    bestBriefHtml = `<div class="card"><div class="eyebrow">Best horn per brief</div><p class="muted">No scored campaigns yet. Run a screen campaign from Launch.</p></div>`;
  }

  const guideHtml = `<details class="card guide" ${(() => { try { return localStorage.getItem("hl-guide-seen") ? "" : "open"; } catch { return "open"; } })()} id="guide">
    <summary><b>How to use this</b> <span class="muted">— four steps from a target to a printable horn</span></summary>
    <ol class="guide-steps">
      <li><b>Pick a brief</b> (<a href="#/briefs">Briefs</a>): the target coverage, frequency band and maximum size. Save a copy to change it.</li>
      <li><b>Choose horn families</b> (<a href="#/typologies">Typologies</a>): classical horns, hybrids and mesher families. Families that cannot meet the brief are greyed out.</li>
      <li><b>Run a search</b> (<a href="#/launch">Launch</a>): start with <i>dry-run</i> (checks the shapes mesh, seconds), then <i>screen</i> (minutes per family). Only one GPU job runs at a time.</li>
      <li><b>Read the results</b> (<a href="#/campaigns">Campaigns</a> → a family → its run): beamwidth and directivity against the target, the horn's size and cross-section, the time-lapse of the search, then <i>Export STEP for CAD</i>.</li>
    </ol>
    <p class="muted" style="margin:6px 0 0">Lower score = closer to the brief. Hover any underlined label for what it means, or open the <a href="#/glossary">Glossary</a>.</p>
  </details>`;

  const quickLinks = `<div class="btn-row">
    <a class="btn" href="#/runs">Browse runs</a>
    <a class="btn" href="#/campaigns">Campaigns</a>
    <a class="btn" href="#/briefs">Briefs</a>
  </div>`;

  ROOT.innerHTML = `<div class="stack" style="gap:22px">
    <div>
      <div class="eyebrow">Dashboard</div>
      <h2>Home</h2>
    </div>
    ${guideHtml}
    ${gpuCard}
    ${bestBriefHtml}
    ${timelineHtml}
    ${quickLinks}
  </div>`;
  document.getElementById("guide")?.addEventListener("toggle", e => {
    try { if (!e.target.open) localStorage.setItem("hl-guide-seen", "1"); else localStorage.removeItem("hl-guide-seen"); } catch {}
  });
}

// ── View 1: Status ─────────────────────────────────────────────────

let _statusTimer = null;
let _statusRendered = false;

function clearStatusTimer() {
  if (_statusTimer) { clearInterval(_statusTimer); _statusTimer = null; }
  _statusRendered = false;
}

async function viewStatus() {
  const ROOT = currentRoot();     // this view's own container (see route())
  if (!_statusRendered) skel("Loading status…");
  let data;
  try { data = await api("/api/status"); }
  catch (e) {
    if (!_statusRendered) ROOT.innerHTML = errBanner("Could not load status: " + e.message);
    return;
  }

  if (!_statusRendered) {
    if (ROOT !== currentRoot()) return;   // the user navigated away while this loaded
  renderStatus(data);
    _statusRendered = true;
  } else {
    updateStatusInPlace(data);
  }

  if (!_statusTimer) {
    _statusTimer = setInterval(() => {
      const h = location.hash;
      if (h !== "#/status" && h !== "" && h !== "#/") { clearStatusTimer(); return; }
      if (document.hidden) return;
      viewStatus();
    }, 10000);
  }
}

function renderStatus(data) {
  const lock = data.gpu_lock;
  const disk = data.disk || {};
  const ql = data.queue_log || {};
  const wl = data.watchdog_log || [];
  const steps = ql.steps || [];
  const cur = data.current;

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">System</div>
        <h2>Status</h2>
      </div>
      <div class="status-grid" id="st-cards">
        <div id="st-lock">${lockCardHtml(lock)}</div>
        <div class="status-card">
          <div class="label">${tip("dims", "VRAM used")}</div>
          <div class="value num" id="st-vram">${data.vram_mib != null ? data.vram_mib.toFixed(0) : "–"} <small style="font-size:1rem">MiB</small></div>
        </div>
        <div class="status-card">
          <div class="label">${tip("julia", "Solver hosts")}</div>
          <div class="value num" id="st-julia">${data.julia_procs ?? "–"}</div>
        </div>
        <div class="status-card">
          <div class="label">Disk free</div>
          <div class="value num" id="st-disk-val">${disk.free_gb != null ? disk.free_gb.toFixed(1) : "–"} <small style="font-size:1rem">GB</small></div>
          <div class="sub" id="st-disk-sub">${disk.total_gb != null ? disk.total_gb.toFixed(0) + " GB total · " + (100 - disk.free_gb / disk.total_gb * 100).toFixed(0) + "% used" : ""}</div>
        </div>
      </div>
      ${cur ? currentRunCard(cur) : ""}
      <div class="btn-row">
        <button id="btn-refresh">↻ Refresh</button>
        <button id="btn-gpuclean" class="danger" ${lock && lock.alive ? "disabled title='A live job holds the GPU lock'" : ""}>gpu-clean</button>
      </div>
      <div class="stack" style="gap:8px">
        <div class="eyebrow">Queue log — ${esc(ql.name || "")}</div>
        ${steps.length ? queueTimelineHtml(steps) : ""}
        <div class="log-tail" id="queue-tail" aria-label="queue log">${esc((ql.tail || []).join("\n"))}</div>
      </div>
      <div class="stack" style="gap:8px">
        <div class="eyebrow">Watchdog log</div>
        <div class="log-tail" id="watchdog-tail" aria-label="watchdog log">${esc(wl.join("\n"))}</div>
      </div>
    </div>`;

  document.getElementById("btn-refresh").onclick = () => { _statusRendered = false; viewStatus(); };
  document.getElementById("btn-gpuclean").onclick = async () => {
    if (!confirm("Run gpu-clean? This kills stale Julia/BEAT processes.")) return;
    const r = await post("/api/gpu-clean", {});
    if (r.error) showToast(r.error, "error");
    else showToast("gpu-clean: " + (r.text || "done").trim().split(String.fromCharCode(10)).slice(-1)[0], "good");
    _statusRendered = false;
    viewStatus();
  };
}

function lockCardHtml(lock) {
  if (lock) {
    const ago = timeSince(lock.start_time);
    const alivePill = lock.alive ? pill("alive", "good") : pill("stale", "warn");
    return `<div class="status-card gpu-lock-card" aria-label="GPU lock">
      <div class="label">${tip("lock", "GPU lock")}</div>
      <div class="value">${esc(lock.user || "–")}</div>
      <div class="sub" title="${esc(lock.command)}" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:30ch">${esc(lock.command || "–")}</div>
      <div class="sub">PID ${esc(lock.pid)} · started ${esc(ago)} ${alivePill}</div>
    </div>`;
  }
  return `<div class="status-card gpu-idle-card" aria-label="GPU lock">
    <div class="label">${tip("lock", "GPU lock")}</div>
    <div class="value good-text">Free</div>
  </div>`;
}

function currentRunCard(cur) {
  if (!cur) return "";
  const budget = cur.budget || 1;
  const pct = Math.min(100, Math.round((cur.n / budget) * 100));
  const over = !!(cur.budget && cur.n > cur.budget);
  const budgetCls = over ? "bad" : pct >= 90 ? "warn" : "";
  const eta = cur.eta_min != null ? `~${Math.round(cur.eta_min)} min left` : "";
  return `<div class="card running-card" style="margin-top:-4px">
    <div class="eyebrow" style="margin-bottom:6px">Running now</div>
    <div style="font-weight:500">${esc(cur.name || cur.id)}</div>
    <div class="progress-wrap" style="margin:8px 0 4px"><div class="progress-bar ${over ? "bad" : ""}" style="width:${pct}%"></div></div>
    <div style="display:flex;justify-content:space-between;font-size:0.8rem;color:var(--muted)">
      <span><b class="${budgetCls}">${cur.n.toLocaleString()} / ${budget.toLocaleString()} (${pct}%)${over ? " over budget" : ""}</b></span>
      <span>${eta}</span>
    </div>
    <div class="kpis" style="margin-top:8px">
      <div class="kpi"><span>Score: best</span><b>${fmt(cur.best_j)}</b></div>
      <div class="kpi"><span>Score: start</span><b>${fmt(cur.seed_j && cur.seed_j < 900 ? cur.seed_j : null)}</b></div>
      <div class="kpi"><span>Rate</span><b>${cur.rate_per_h ? cur.rate_per_h.toFixed(0) + "/h" : "–"}</b></div>
    </div>
  </div>`;
}

function queueTimelineHtml(steps) {
  const shown = steps.slice(-15);
  return `<div class="timeline" style="margin-bottom:8px">
    ${shown.map(s => {
      const dot = s.skipped ? "skip" : s.exit == null ? "run" : s.exit === 0 ? "done" : "failed";
      let dur = "";
      if (s.started && s.ended) {
        const ms = new Date(s.ended) - new Date(s.started);
        dur = ms > 60000 ? (ms / 60000).toFixed(1) + "m" : (ms / 1000).toFixed(0) + "s";
      } else if (s.skipped) { dur = "skipped"; } else if (s.started) { dur = "running"; }
      const exitNote = s.exit != null && s.exit !== 0 ? ` <span class="tl-exit-bad">exit ${s.exit}</span>` : "";
      return `<div class="tl-row">
        <div class="tl-dot ${dot}" title="${dot}"></div>
        <span class="tl-name">${esc(s.name)}</span>
        <span class="tl-time">${esc(dur)}${exitNote}</span>
      </div>`;
    }).join("")}
  </div>`;
}

function updateStatusInPlace(data) {
  const lock = data.gpu_lock;
  const disk = data.disk || {};
  const ql = data.queue_log || {};
  const wl = data.watchdog_log || [];

  const sl = document.getElementById("st-lock");
  if (sl) sl.innerHTML = lockCardHtml(lock);

  const sv = document.getElementById("st-vram");
  if (sv) sv.innerHTML = `${data.vram_mib != null ? data.vram_mib.toFixed(0) : "–"} <small style="font-size:1rem">MiB</small>`;

  const sj = document.getElementById("st-julia");
  if (sj) sj.textContent = data.julia_procs ?? "–";

  const sd = document.getElementById("st-disk-val");
  if (sd) sd.innerHTML = `${disk.free_gb != null ? disk.free_gb.toFixed(1) : "–"} <small style="font-size:1rem">GB</small>`;

  const ss = document.getElementById("st-disk-sub");
  if (ss) ss.textContent = disk.total_gb != null ? `${disk.total_gb.toFixed(0)} GB total · ${(100 - disk.free_gb / disk.total_gb * 100).toFixed(0)}% used` : "";

  const qt = document.getElementById("queue-tail");
  if (qt) qt.textContent = (ql.tail || []).join("\n");

  const wt = document.getElementById("watchdog-tail");
  if (wt) wt.textContent = wl.join("\n");

  const gc = document.getElementById("btn-gpuclean");
  if (gc) gc.disabled = !!(lock && lock.alive);
}

// ── View 2: Campaigns list ─────────────────────────────────────────

async function viewCampaignsList() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let camps;
  try { camps = await api("/api/campaigns"); }
  catch (e) { ROOT.innerHTML = errBanner(e.message); return; }

  if (!camps.length) {
    ROOT.innerHTML = `<div class="stack" style="gap:20px">
      <div><div class="eyebrow">All campaigns</div><h2>Campaigns</h2></div>
      <p class="muted">No campaigns found. <a href="#/launch">Launch a campaign →</a></p>
    </div>`;
    return;
  }

  let rows = camps.map(c => `<tr class="clickable ${c.superseded ? "superseded" : ""}" onclick="location.hash='#/campaign/${esc(c.id)}'">
    <td><b>${esc(c.id)}</b>${c.superseded ? ` ${pill("superseded", "warn")}` : ""}</td>
    <td>${pill(c.tier || "–", c.tier === "compare" ? "warn" : c.tier === "screen" ? "info" : "good")}</td>
    <td>${esc(c.brief || "–")}</td>
    <td class="r">${esc(c.n_entries)}</td>
    <td class="r">${esc((c.seeds || []).join(", "))}</td>
    <td class="muted" style="font-size:0.82rem">${esc((c.families || []).slice(0, 4).join(", ")) + (c.families && c.families.length > 4 ? " …" : "")}</td>
  </tr>`).join("");

  ROOT.innerHTML = `
    <div class="stack" style="gap:20px">
      <div>
        <div class="eyebrow">All campaigns</div>
        <h2>Campaigns</h2>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead><tr><th>ID</th><th>Tier</th><th>Brief</th><th class="r">Entries</th><th class="r">Seeds</th><th>Families</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
}

// ── View 2 detail: Campaign detail ────────────────────────────────

const TIER_DESC = {
  "dry-run": "Meshes each starting design only — no solving. Takes seconds. Checks the geometry is valid.",
  "screen":  "One search per family, budget max(40, 10 × parameters). A coarse first ranking in minutes per family. Enough to pick the top 2–3 families.",
  "compare": "Two repeats, budget max(150, 25 × parameters). The minimum to claim one family beats another. Takes hours — never run during a live search.",
};

async function viewCampaignDetail(id) {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let camp;
  try { camp = await api("/api/campaign/" + id); }
  catch (e) { ROOT.innerHTML = errBanner(e.message); return; }

  const entries = camp.entries || [];

  // Compute common scale for wall profiles
  let allR = [], allZ = [];
  entries.forEach(e => {
    const p = ((e.best || {}).profile) || {};
    [["h", 1], ["v", -1]].forEach(([k]) => {
      (p[k] || []).forEach(pt => { allR.push(Math.abs(pt[1])); allZ.push(pt[0]); });
    });
  });
  const sharedRmax = allR.length ? Math.max(...allR) * 1.1 : 200;
  const sharedZmin = allZ.length ? Math.min(...allZ) - 5 : 0;
  const sharedZmax = allZ.length ? Math.max(...allZ) + 5 : 220;

  // Separation analysis
  function isSeparated(a, b) {
    if (a.median_j == null || b.median_j == null) return null;
    const diff = b.median_j - a.median_j;
    const thresh = Math.max(a.spread || 0, b.spread || 0);
    return diff > thresh;
  }

  // Leaderboard rows
  let lbRows = entries.map((e, i) => {
    const gc = groupColor(e.group || "");
    const gpill = `<span class="pill" style="border-color:${gc};box-shadow:inset 3px 0 0 ${gc}">${esc(e.group || "–")}</span>`;
    const pinnedPills = (e.pinned || []).map(k => `<span class="pill bad">${esc(k)}</span>`).join(" ") || "";
    const failCount = Object.values(e.failures || {}).reduce((a, v) => a + v, 0);
    const seedLinks = (e.jobs || []).map(j => j.run_id
      ? `<a href="#/run/${esc(j.run_id)}">${esc("s" + j.seed)}</a>` : `s${esc(j.seed)}`).join(" ");

    // Use best_run_id if available (new API field)
    const bestLink = e.best_run_id
      ? `onclick="location.hash='#/run/${esc(e.best_run_id)}'" style="cursor:pointer"`
      : "";
    const dimCell = e.dims ? dimStr(e.dims) : "–";

    // Separation from next: row tint stays, plus a text badge (state not by colour alone)
    let rowCls = "", rankNote = "";
    if (i < entries.length - 1) {
      const next = entries[i + 1];
      const sep = isSeparated(e, next);
      if (sep === true) {
        rowCls = "row-ahead";
        const pctDelta = e.median_j ? ((next.median_j - e.median_j) / e.median_j) * 100 : null;
        rankNote = (pctDelta != null && isFinite(pctDelta) && pctDelta > 0)
          ? `+${Math.round(pctDelta)} %` : "leader";
      } else if (sep === false) {
        rowCls = "row-not-sep";
        rankNote = "within noise";
      }
    }

    return `<tr class="${rowCls}" ${bestLink}>
      <td class="r mono">${i + 1}${rankNote ? ` <small class="muted">${esc(rankNote)}</small>` : ""}</td>
      <td><b>${esc(e.name)}</b></td>
      <td>${gpill}</td>
      <td class="r">${fmt(e.best_j)}</td>
      <td class="r">${fmt(e.median_j)}</td>
      <td class="r">${fmt(e.spread)}</td>
      <td class="muted" style="font-size:0.8rem;white-space:normal">${esc(dimCell)}</td>
      <td class="r">${esc(e.evals || "–")}</td>
      <td class="r">${failCount > 0 ? `<span class="warn-text">${failCount}</span>` : "0"}</td>
      <td>${pinnedPills}</td>
      <td style="font-size:0.8rem">${seedLinks}</td>
    </tr>`;
  }).join("");

  const tierDesc = TIER_DESC[camp.tier] || "";

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Campaign · ${esc(camp.tier || "")}</div>
        <h2>${esc(camp.id)}</h2>
        <p class="muted" style="font-size:0.85rem">Brief: ${esc(camp.brief || "–")} · Seeds: ${esc((camp.seeds || []).join(", "))}</p>
        ${tierDesc ? `<p class="muted" style="font-size:0.82rem;margin-top:4px">${esc(tierDesc)}</p>` : ""}
        ${camp.superseded ? `<div class="alert warn" style="margin-top:8px"><b>Superseded.</b> This campaign ran before the 22 Oct fixes (native configs were scored on their own targets and the brief's size envelope was not enforced). Kept for the record; it is excluded from Home, Typologies and rankings.</div>` : ""}
      </div>
      <div>
        <p class="muted" style="font-size:0.78rem;margin-bottom:8px">
          <span style="display:inline-flex;align-items:center;gap:5px"><span style="width:10px;height:10px;background:var(--good);border-radius:50%;display:inline-block"></span> Green left border = clearly ahead of next rank</span> ·
          <span style="display:inline-flex;align-items:center;gap:5px"><span style="width:10px;height:10px;background:var(--warn);border-radius:50%;display:inline-block"></span> Orange = not separated from next</span>
        </p>
        <div class="tbl-wrap">
          <table>
            <thead><tr>
              <th class="r">#</th><th>Name</th><th>Group</th>
              <th class="r">${tip("J", "Best score")}</th>
              <th class="r">${tip("median", "Median")}</th>
              <th class="r">${tip("spread", "Spread")}</th>
              <th>${tip("dims", "Horn size W×H×D")}</th>
              <th class="r">Evals</th>
              <th class="r">${tip("failures", "Failures")}</th>
              <th>${tip("pinned", "At limit")}</th>
              <th>Seeds</th>
            </tr></thead>
            <tbody>${lbRows}</tbody>
          </table>
        </div>
      </div>
      <div>
        <h3 style="margin-bottom:10px">Wall profiles — best design per family</h3>
        <p class="muted" style="font-size:0.82rem">H right (positive r), V mirrored left. Shared mm scale. Click a card to open the run.</p>
        <div class="camp-grid" id="wall-profiles"></div>
      </div>
      <div>
        <h3 style="margin-bottom:8px">Best design of each family</h3>
        <div class="legend" id="bw-legend" style="margin-bottom:8px"></div>
        <div class="grid2">
          <div class="fig">
            <div class="fig-head"><h3>Beamwidth (−6 dB) vs target</h3>
              <div class="toggle-row" id="bw-toggle">
                <button aria-pressed="true" id="btn-bw-h">Horizontal</button>
                <button aria-pressed="false" id="btn-bw-v">Vertical</button>
              </div></div>
            <div class="cap">Shaded: target ±10 %. Lighter panel: scored band.</div>
            <svg id="bw-chart"></svg>
          </div>
          <div class="fig">
            <h3>Directivity index vs target</h3>
            <div class="cap">Dashed: target DI from the brief's coverage angles.</div>
            <svg id="di-overlay"></svg>
          </div>
        </div>
      </div>
    </div>`;

  // Wall cross-sections, one card per family, all on ONE shared mm scale so sizes compare directly
  const profGrid = document.getElementById("wall-profiles");
  let ext = { rmax: 1, z0: Infinity, z1: -Infinity };
  entries.forEach(e => { const p = (e.best || {}).profile || {};
    for (const k of ["h", "v"]) for (const [z, r] of (p[k] || [])) {
      ext.rmax = Math.max(ext.rmax, Math.abs(r)); ext.z0 = Math.min(ext.z0, z); ext.z1 = Math.max(ext.z1, z); } });
  entries.forEach((e, idx) => {
    const cell = document.createElement("div"); cell.className = "camp-prof";
    if (e.best_run_id) { cell.onclick = () => { location.hash = "#/run/" + e.best_run_id; }; cell.tabIndex = 0; cell.setAttribute("role", "link"); }
    const col = familyColor(idx);
    cell.innerHTML = `<h4><span class="swatch" style="background:${col}"></span>${esc(e.name)}</h4>`;
    const sv = document.createElementNS(NS, "svg"); sv.setAttribute("class", "camp-sec");
    cell.appendChild(sv);
    const cap = document.createElement("div"); cap.className = "camp-dims";
    cap.textContent = e.dims ? `${Math.round(e.dims.mouth_w_mm)} × ${Math.round(e.dims.mouth_h_mm)} × ${Math.round(e.dims.depth_mm)} mm` : "no solved design";
    cell.appendChild(cap);
    profGrid.appendChild(cell);
    requestAnimationFrame(() => wallSection(sv, (e.best && e.best.profile) ? [{ profile: e.best.profile, color: col, filled: true }] : [],
                                            { H: 130, compact: true, extent: isFinite(ext.z0) ? ext : null }));
  });

  // Overlays of each family's best design: beamwidth (H or V) and DI, one colour per family
  const target = camp.target || (entries.find(e => e.best && e.best.target) || {}).target || {};
  let bwPlane = "h";
  function drawBW() {
    const bwSvg = document.getElementById("bw-chart"), diSvg = document.getElementById("di-overlay");
    const legDiv = document.getElementById("bw-legend");
    if (!bwSvg) return;
    const freqsRef = (entries.find(e => e.best && e.best.freqs) || { best: { freqs: [] } }).best.freqs || [];
    if (!freqsRef.length) { bwSvg.innerHTML = "<text x='10' y='20'>No frequency data</text>"; return; }
    const tgtH = target.coverage_h_deg, tgtV = target.coverage_v_deg;
    const tgt = bwPlane === "h" ? tgtH : tgtV;
    const allBW = [];
    entries.forEach(e => { const b = e.best || {}; (bwPlane === "h" ? (b.bw_h || []) : (b.bw_v || [])).forEach(v => v != null && allBW.push(v)); });
    if (tgt) allBW.push(tgt);
    const bwmax = Math.min(200, Math.ceil(Math.max(...allBW) * 1.08 / 10) * 10) || 180;
    const band = [target.band_lo_hz || freqsRef[0], target.band_hi_hz || freqsRef[freqsRef.length - 1]];
    const xlim = [freqsRef[0], freqsRef[freqsRef.length - 1]];
    chart(bwSvg, {
      H: 260, xlog: true, xlim, ylim: [0, bwmax], xticks: FT, yticks: niceTicks(0, bwmax, 5),
      xlabel: "Hz", ylabel: "deg", band,
      fill: tgt ? [{ y0: tgt * 0.9, y1: tgt * 1.1, color: css("--best"), opacity: 0.10 }] : [],
      hlines: tgt ? [{ y: tgt, color: css("--label"), dash: true }] : [],
      series: entries.map((e, idx) => { const b = e.best || {}, F2 = b.freqs || freqsRef;
        const arr = bwPlane === "h" ? (b.bw_h || []) : (b.bw_v || []);
        return { pts: F2.map((f, i) => [f, arr[i] ?? null]), color: familyColor(idx), w: idx === 0 ? 2.4 : 1.6 }; }),
    });
    if (diSvg) {
      const dit = target.di_target_db ?? (tgtH && tgtV ? diFromCuts(tgtH, tgtV) : null);
      const dall = []; entries.forEach(e => ((e.best || {}).di || []).forEach(v => v != null && dall.push(v)));
      if (dit != null) dall.push(dit);
      const dlo = Math.floor(Math.min(...dall) - 1), dhi = Math.ceil(Math.max(...dall) + 1);
      chart(diSvg, {
        H: 260, xlog: true, xlim, ylim: [dlo, dhi], xticks: FT, yticks: niceTicks(dlo, dhi, 5),
        xlabel: "Hz", ylabel: "dB", band,
        hlines: dit != null ? [{ y: dit, color: css("--label"), dash: true }] : [],
        series: entries.map((e, idx) => { const b = e.best || {}, F2 = b.freqs || freqsRef;
          return { pts: F2.map((f, i) => [f, (b.di || [])[i] ?? null]), color: familyColor(idx), w: idx === 0 ? 2.4 : 1.6 }; }),
      });
    }
    legDiv.innerHTML = entries.map((e, idx) => `<span><i style="color:${familyColor(idx)};border-top-color:${familyColor(idx)}"></i>${esc(e.name)}${idx === 0 ? " (rank 1)" : ""}</span>`).join("")
      + `<span><i style="color:var(--label)" class="dash"></i>target</span>`;
  }
  drawBW();
  document.getElementById("btn-bw-h").onclick = () => {
    bwPlane = "h";
    document.getElementById("btn-bw-h").setAttribute("aria-pressed", "true");
    document.getElementById("btn-bw-v").setAttribute("aria-pressed", "false");
    drawBW();
  };
  document.getElementById("btn-bw-v").onclick = () => {
    bwPlane = "v";
    document.getElementById("btn-bw-h").setAttribute("aria-pressed", "false");
    document.getElementById("btn-bw-v").setAttribute("aria-pressed", "true");
    drawBW();
  };
}

// ── View 3: Runs list ──────────────────────────────────────────────

async function viewRunsList() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let runs;
  try { runs = await api("/api/runs"); }
  catch (e) { ROOT.innerHTML = errBanner(e.message); return; }
  if (ROOT !== currentRoot()) return;   // the user navigated away while this loaded
  renderRunsList(runs);
}

function renderRunsList(allRuns) {
  // Collect unique briefs and families for filter dropdowns
  const briefs = [...new Set(allRuns.map(r => r.brief).filter(Boolean))].sort();
  const families = [...new Set(allRuns.map(r => r.family).filter(Boolean))].sort();

  ROOT.innerHTML = `
    <div class="stack" style="gap:20px">
      <div>
        <div class="eyebrow">All runs</div>
        <h2>Runs</h2>
        <p class="muted" style="font-size:0.85rem">${allRuns.length} total · newest first</p>
      </div>
      <div class="filter-bar">
        <input id="run-filter" type="search" placeholder="Filter by name / family / brief…" aria-label="filter runs">
        <select id="run-filter-brief" aria-label="filter by brief">
          <option value="">All briefs</option>
          ${briefs.map(b => `<option value="${esc(b)}">${esc(b)}</option>`).join("")}
        </select>
        <select id="run-filter-family" aria-label="filter by family">
          <option value="">All families</option>
          ${families.map(f => `<option value="${esc(f)}">${esc(f)}</option>`).join("")}
        </select>
        <select id="run-sort" class="sort-sel" aria-label="sort runs">
          <option value="date">Newest first</option>
          <option value="best_j">${tip("J", "Score")} (best first)</option>
          <option value="name">Name</option>
        </select>
      </div>
      <div class="tbl-wrap">
        <table id="runs-table">
          <thead><tr>
            <th>Date</th><th>Name</th><th>Family</th><th>Brief</th>
            <th class="r">${tip("J", "Score start → best")}</th>
            <th class="r">Change</th>
            <th>${tip("dims", "Horn size W×H×D")}</th>
            <th class="r">Evals</th>
            <th class="r">${tip("failures", "Fail %")}</th>
          </tr></thead>
          <tbody id="runs-tbody"></tbody>
        </table>
      </div>
    </div>`;

  function render() {
    const q = document.getElementById("run-filter").value.toLowerCase();
    const bf = document.getElementById("run-filter-brief").value;
    const ff = document.getElementById("run-filter-family").value;
    const sort = document.getElementById("run-sort").value;
    let filtered = allRuns.filter(r =>
      (!bf || r.brief === bf) &&
      (!ff || r.family === ff) &&
      (!q || (r.name || "").toLowerCase().includes(q) ||
             (r.family || "").toLowerCase().includes(q) ||
             (r.brief || "").toLowerCase().includes(q))
    );
    if (sort === "best_j") filtered.sort((a, b) => (a.best_j ?? 999) - (b.best_j ?? 999));
    else if (sort === "name") filtered.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
    else filtered.sort((a, b) => (b.started || "").localeCompare(a.started || ""));

    const tbody = document.getElementById("runs-tbody");
    if (!filtered.length) {
      tbody.innerHTML = `<tr><td colspan="9" class="muted" style="text-align:center;padding:24px">No matching runs. <a href="#/launch">Launch a search →</a></td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map(r => {
      const nf = r.n - r.n_ok;
      const ch = betterPct(r.seed_j, r.best_j);
      const chCls = ch.endsWith("better") ? "good-text" : "";
      const failPct = r.n > 0 ? ((nf / r.n) * 100).toFixed(0) + "%" : "–";
      const isRunning = !r.last || (Date.now() - new Date(r.last).getTime()) < 120000;
      return `<tr class="clickable" onclick="location.hash='#/run/${esc(r.id)}'" ${isRunning ? 'style="background:var(--accent-soft)"' : ""}>
        <td class="muted mono" style="font-size:0.76rem;white-space:nowrap">${timeSince(r.started)}</td>
        <td><b>${esc(r.name)}</b><br><span class="mono muted" style="font-size:0.72rem">${esc(r.id)}</span></td>
        <td>${esc(r.family || "–")}</td>
        <td>${esc(r.brief || "–")}</td>
        <td class="r num">${r.seed_j != null && r.seed_j < 900 ? fmt(r.seed_j) : "–"} → <b>${fmt(r.best_j)}</b></td>
        <td class="r ${chCls}">${ch}</td>
        <td style="font-size:0.82rem">${r.dims ? esc(dimStr(r.dims)) : "–"}</td>
        <td class="r">${r.n.toLocaleString()}</td>
        <td class="r">${nf > 0 ? `<span class="warn-text">${esc(failPct)}</span>` : failPct}</td>
      </tr>`;
    }).join("");
  }

  render();
  document.getElementById("run-filter").addEventListener("input", render);
  document.getElementById("run-filter-brief").addEventListener("change", render);
  document.getElementById("run-filter-family").addEventListener("change", render);
  document.getElementById("run-sort").addEventListener("change", render);
}

// ── View 3 detail: Run detail ──────────────────────────────────────

// -- WP11b: CMA-ME quality-diversity atlas (read-only, plain canvas) -----------
// Data: GET /api/archive/<run> (data.py::run_archive) over the pinned archive_heatmap.json:
//   {bins: [bins_h, bins_v], ranges: {h: [lo, hi], v: [lo, hi]},
//    cells: [{h_center, v_center, objective, design_hash}],
//    descriptors: {h: name, v: name}}   (occupied bins only; descriptors may be absent)
// A plain cma run has no such file: the endpoint reports available:false and this view says so.
async function viewRunArchive(id) {
  const ROOT = currentRoot();     // this view's own container (see route())
  ROOT.innerHTML = `<p class="muted">Loading the quality-diversity atlas…</p>`;
  let A;
  try { A = await api("/api/archive/" + encodeURIComponent(id)); }
  catch (e) { ROOT.innerHTML = errBanner(e.message); return; }
  if (!A.available) {
    ROOT.innerHTML = `<div class="stack" style="gap:12px">
      <div class="eyebrow">Quality-diversity atlas</div><h2>${esc(id)}</h2>
      <p class="muted">This run has no atlas. Only a CMA-ME search (<code>search.algorithm: cma_me</code>)
        writes <code>archive_heatmap.json</code>; a plain cma run never does.</p>
      <p><a href="#/run/${esc(id)}">← back to the run</a></p></div>`;
    return;
  }
  const bins = A.bins || [1, 1], rng = A.ranges || {};
  const nbH = Math.max(1, Math.trunc(bins[0]) || 1), nbV = Math.max(1, Math.trunc(bins[1]) || 1);
  const axH = Array.isArray(rng.h) ? rng.h.map(Number) : [0, 180];
  const axV = Array.isArray(rng.v) ? rng.v.map(Number) : [0, 180];
  const cells = (A.cells || []).filter(c => c && isFinite(c.h_center) && isFinite(c.v_center)
                                            && isFinite(c.objective));
  if (!cells.length) {
    ROOT.innerHTML = `<div class="stack" style="gap:12px">
      <div class="eyebrow">Quality-diversity atlas</div><h2>${esc(id)}</h2>
      <p class="muted">The archive has no occupied bins yet.</p>
      <p><a href="#/run/${esc(id)}">← back to the run</a></p></div>`;
    return;
  }
  const totalBins = nbH * nbV, coverage = totalBins ? cells.length / totalBins : 0;
  const evals = A.stats && A.stats.total_evals != null ? A.stats.total_evals : null;
  const jmin = Math.min(...cells.map(c => c.objective)), jmax = Math.max(...cells.map(c => c.objective));
  const labH = (A.descriptors && A.descriptors.h) || "descriptor (h)";
  const labV = (A.descriptors && A.descriptors.v) || "descriptor (v)";
  ROOT.innerHTML = `<div class="stack" style="gap:16px">
    <div><div class="eyebrow">Quality-diversity atlas · CMA-ME</div><h2>${esc(id)}</h2>
      <p class="muted" style="margin:2px 0 0">${cells.length} of ${totalBins} bins occupied
        (${fmtPct(coverage * 100)}${evals != null ? ", " + esc(evals) + " evaluations" : ""}).
        Axes: <code>${esc(labH)}</code> (horizontal) × <code>${esc(labV)}</code> (vertical), degrees.
        Hollow cells never held an evaluated design.
        <a href="#/run/${esc(id)}">← back to the run</a></p></div>
    <div class="fig"><h3>Archive: best objective per descriptor bin</h3>
      <div class="cap">Colour: objective J (lower is better, brightest). Hover a cell for its descriptor
        centre, objective and design hash.</div>
      <canvas id="qd-canvas" width="720" height="540" style="max-width:100%"></canvas>
      <div class="legend" style="align-items:center">
        <span class="mono">worst J ${fmt(jmax, 3)}</span>
        <canvas id="qd-cbar" style="width:180px;height:10px;border:1px solid var(--rule)"></canvas>
        <span class="mono">best J ${fmt(jmin, 3)}</span>
      </div>
      <div id="qd-hover" class="mono muted" style="min-height:1.2em"></div></div>
  </div>`;
  drawCbar(document.getElementById("qd-cbar"));
  const cv = document.getElementById("qd-canvas"), g = cv.getContext("2d");
  const padL = 78, padB = 58, padT = 16, padR = 20;
  const W = cv.width - padL - padR, H = cv.height - padT - padB;
  const cw = W / nbH, ch = H / nbV;
  // descriptor value -> bin index, clamped: a cell centre at the top edge lands in the last bin
  const binOf = (v, ax, n) => {
    if (!(ax[1] > ax[0])) return 0;
    return Math.max(0, Math.min(n - 1, Math.floor((v - ax[0]) / (ax[1] - ax[0]) * n)));
  };
  const byBin = new Map();
  for (const c of cells) {
    const key = binOf(c.h_center, axH, nbH) + "," + binOf(c.v_center, axV, nbV);
    const old = byBin.get(key);                       // one elite per bin by contract; keep the best anyway
    if (!old || c.objective < old.objective) byBin.set(key, c);
  }
  g.fillStyle = css("--surface") || "#15181c"; g.fillRect(padL, padT, W, H);
  g.strokeStyle = css("--rule") || "#333"; g.lineWidth = 1;
  for (let i = 0; i <= nbH; i++) {
    const x = padL + i * cw; g.beginPath(); g.moveTo(x, padT); g.lineTo(x, padT + H); g.stroke();
  }
  for (let j = 0; j <= nbV; j++) {
    const y = padT + j * ch; g.beginPath(); g.moveTo(padL, y); g.lineTo(padL + W, y); g.stroke();
  }
  for (const [key, c] of byBin) {
    const [i, j] = key.split(",").map(Number);
    const t = jmax > jmin ? (c.objective - jmin) / (jmax - jmin) : 0.5;
    const [rr, gg, bb] = cmap(1 - t);                 // t = 0 (best objective) -> bright/warm end
    g.fillStyle = `rgb(${rr},${gg},${bb})`;
    g.fillRect(padL + i * cw + 1, padT + H - (j + 1) * ch + 1, cw - 2, ch - 2);
  }
  g.fillStyle = css("--label") || "#aaa"; g.font = "11px monospace";
  g.textAlign = "center"; g.textBaseline = "top";
  const stepH = Math.max(1, Math.round(nbH / 6)), stepV = Math.max(1, Math.round(nbV / 5));
  for (let i = 0; i < nbH; i += stepH) {
    const c = axH[0] + (i + 0.5) * (axH[1] - axH[0]) / nbH;
    g.fillText(fmtDeg(c), padL + (i + 0.5) * cw, padT + H + 6);
  }
  g.textAlign = "right"; g.textBaseline = "middle";
  for (let j = 0; j < nbV; j += stepV) {
    const c = axV[0] + (j + 0.5) * (axV[1] - axV[0]) / nbV;
    g.fillText(fmtDeg(c), padL - 6, padT + H - (j + 0.5) * ch);
  }
  g.textAlign = "center"; g.textBaseline = "alphabetic";
  g.fillText(labH, padL + W / 2, cv.height - 10);
  g.save(); g.translate(14, padT + H / 2); g.rotate(-Math.PI / 2);
  g.fillText(labV, 0, 0); g.restore();
  const hover = document.getElementById("qd-hover");
  cv.onmousemove = ev => {
    const b = cv.getBoundingClientRect();
    const x = (ev.clientX - b.left) * cv.width / b.width - padL;
    const y = padT + H - (ev.clientY - b.top) * cv.height / b.height;
    const i = Math.floor(x / cw), j = Math.floor(y / ch);
    if (i < 0 || j < 0 || i >= nbH || j >= nbV) { hover.textContent = ""; return; }
    const c = byBin.get(i + "," + j);
    hover.textContent = c
      ? `bin [${i}, ${j}] · ${labH} ${fmtDeg(c.h_center)} · ${labV} ${fmtDeg(c.v_center)} · J ${fmt(c.objective, 4)} · design ${String(c.design_hash || "").slice(0, 12)}`
      : `bin [${i}, ${j}] · empty`;
  };
  cv.onmouseleave = () => { hover.textContent = ""; };
}

async function viewRunDetail(id) {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let d;
  try { d = await api("/api/run/" + id); }
  catch (e) { ROOT.innerHTML = errBanner(e.message); return; }

  const sum = d.summary || d;
  const t = d.target || {};
  const S = d.seed || {};
  const B = d.best || {};
  const w = Object.assign({}, DEFW, d.weights || {});

  const nf = sum.n - sum.n_ok;
  const failPct = sum.n > 0 ? ((nf / sum.n) * 100).toFixed(1) : "–";
  const ch = betterPct(sum.seed_j, sum.best_j);
  const pinnedSens = (d.sens || []).filter(s => Math.max(s.at_lo, s.at_hi) >= 4);
  const coverTarget = `${fmtDeg(t.coverage_h_deg)} × ${fmtDeg(t.coverage_v_deg)}`;
  const bandStr = `${fmtHz(t.band_lo_hz)} – ${fmtHz(t.band_hi_hz)}`;
  const dimsStr = sum.dims ? dimStr(sum.dims) : "–";

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Run · ${esc(sum.generator ? "typology generator" : "mesher family")} · ${esc(sum.family || "")} mesh · ${esc(sum.mode || "")} fidelity${sum.brief ? " · brief " + esc(sum.brief) : ""}${sum.cma_seed != null ? " · random seed " + esc(sum.cma_seed) : ""}</div>
        <h2>${esc(sum.name || id)}</h2>
        <p class="mono muted" style="font-size:0.78rem">${esc(id)}</p>
      </div>

      <!-- Designer header: key facts -->
      <div class="kpis" id="kpi-strip"></div>

      <!-- Actions -->
      <div class="btn-row">
        <a class="btn primary" href="#/run/${esc(id)}/evolution">▶ Evolution time-lapse</a>
        <a class="btn" href="#/run/${esc(id)}/archive" title="Quality-diversity atlas: objective per descriptor bin (CMA-ME runs only)">QD atlas</a>
        <a class="btn" href="#/run/${esc(id)}/3d">3D view</a>
        <a class="btn" href="#/compare?a=${esc(id)}">Compare with…</a>
        <span id="report-slot">${sum.has_report
          ? `<a class="btn" href="/runs/${esc(id)}/report.html" target="_blank" rel="noopener">Open full report ↗</a>`
          : `<button id="btn-gen-report" title="Builds the detailed HTML report (about 30 s)">Make full report</button>`}</span>
        <button id="btn-step" title="Writes closed STEP solids (mm) of the 3 best designs for CAD or 3D printing">Export STEP for CAD (top 3)</button>
      </div>
      <div id="run-files" class="run-files"></div>

      <!-- Acoustic performance charts (designer order) -->
      <div class="grid2">
        <div class="fig">
          <h3>${tip("bw", "Beamwidth (−6 dB)")} vs target</h3>
          <div class="cap">Total angle between the −6 dB points. Shaded: target ±10 %; lighter panel: the scored band.</div>
          <div class="legend">
            <span><i style="color:var(--best)"></i>best, horizontal</span>
            <span><i style="color:var(--best)" class="dash"></i>best, vertical</span>
            <span><i style="color:var(--seed)"></i>start H</span>
            <span><i style="color:var(--seed)" class="dash"></i>start V</span>
            <span><i style="color:var(--label)"></i>target H</span>
            <span><i style="color:var(--label)" class="dash"></i>target V</span>
          </div>
          <svg id="c-bw"></svg>
        </div>
        <div class="fig">
          <h3>${tip("di_db", "Directivity index")} vs target</h3>
          <div class="legend">
            <span><i style="color:var(--seed)"></i>start</span>
            <span><i style="color:var(--best)"></i>best</span>
            <span><i style="color:var(--label)" class="dash"></i>DI target</span>
          </div>
          <svg id="c-di"></svg>
        </div>
        <div class="fig">
          <h3>${tip("on_axis", "On-axis response")} (mean removed)</h3>
          <div class="legend">
            <span><i style="color:var(--seed)"></i>start</span>
            <span><i style="color:var(--best)"></i>best</span>
          </div>
          <svg id="c-axis"></svg>
        </div>
        <div class="fig">
          <h3>${tip("z_re", "Throat impedance")}</h3>
          <div class="cap">Normalised to ρc. Resistance near 1 = the horn loads the driver well; below 0.7 counts as poor loading. Reactance: + = mass-like.</div>
          <div class="legend">
            <span><i style="color:var(--best)"></i>resistance (best)</span>
            <span><i style="color:var(--best)" class="dash"></i>reactance (best)</span>
            <span><i style="color:var(--seed)"></i>start</span>
            <span><i style="color:var(--warn)" class="dash"></i>0.7 threshold</span>
          </div>
          <svg id="c-zre"></svg>
        </div>
      </div>

      <!-- Polar maps -->
      <div class="fig">
        <div class="fig-head"><h3>${tip("polar", "Directivity (isobars)")}</h3>
          <label class="evo-opt" style="color:var(--ink)"><input type="checkbox" id="iso-start"> also show the starting design</label></div>
        <div class="cap">Level relative to on-axis at 2 m, in 3 dB colour bands from −30 to 0 dB, with white contour lines every 3 dB (the heavier line is −6 dB: the beamwidth edge). Frequency across, angle up. Hover for a readout. Interpolated between the ${((d.best || {}).freqs || []).length} solved frequencies.</div>
        <div class="maps iso-maps" id="polar-maps"></div>
      </div>

      <!-- Wall profile -->
      <div class="fig">
        <h3>Wall cross-section</h3>
        <div class="cap">Section through the solved mesh, true scale in mm: horizontal plane to the right, vertical plane mirrored to the left, throat at the bottom. Includes the outer shell and rear. Band = horn wall, interior = sound bore; dashed amber = starting design; dot = throat.</div>
        <div class="legend">
          <span><i style="color:var(--best)"></i>best (filled)</span>
          <span><i style="color:var(--seed)" class="dash"></i>start</span>
        </div>
        <svg id="c-prof"></svg>
      </div>

      <hr class="sep">

      <!-- Search history -->
      <h3>How the search went</h3>
      <div class="grid2">
        <div class="fig"><h3>Convergence</h3>
          <div class="cap">Every eval (dots) and running best (line). Failures excluded.</div>
          <svg id="c-conv"></svg>
        </div>
        <div class="fig"><h3>${tip("J", "Score")} breakdown: start vs best</h3>
          <div class="cap">Weighted contribution per term. Upper bar = start, lower = best.</div>
          <svg id="c-terms"></svg>
        </div>
      </div>

      <!-- Sensitivity -->
      <div class="fig">
        <h3>${tip("knob", "Shape parameters")}</h3>
        <div class="cap">${tip("rho", "Influence")} = Spearman ρ. ${tip("pinned", "At-limit")} = of the 6 best designs how many sit at each bound.</div>
        <div class="tbl-wrap"><table id="sens-table"></table></div>
      </div>

      <!-- Failures -->
      <div class="stack" style="gap:6px">
        <h3>${tip("failures", "Failures")}</h3>
        <div class="pill-row">${failurePills(sum.failures)}</div>
      </div>

      ${d.command ? `<div class="stack" style="gap:6px"><h3>Command</h3><div class="log-tail" style="max-height:60px">${esc(d.command)}</div></div>` : ""}
    </div>`;

  // KPI strip (designer-first order)
  const budgetPct = sum.budget ? Math.round(((sum.n || 0) / sum.budget) * 100) : 0;
  const overBudget = !!(sum.budget && sum.n > sum.budget);
  document.getElementById("kpi-strip").innerHTML = [
    [`${tip("bw", "Coverage target")}`, coverTarget],
    [`${tip("band", "Band")}`, bandStr],
    [`${tip("dims", "Horn size")} <small style="font-family:var(--f-mono);font-size:0.6rem;color:var(--muted)">W×H×D outer</small>`, dimsStr],
    [`${tip("J", "Score: start")}`, fmt(sum.seed_j && sum.seed_j < 900 ? sum.seed_j : null)],
    [`${tip("J", "Score: best")}`, fmt(sum.best_j)],
    ["Change vs start", ch],
    [`${tip("budget", "Budget used")}`,
     `${(sum.n || 0).toLocaleString()}${sum.budget ? " / " + sum.budget.toLocaleString() : ""}${overBudget ? " over budget" : ""}`,
     overBudget ? "bad" : budgetPct >= 90 ? "warn" : ""],
    [`${tip("failures", "Failures")}`, `${nf} (${failPct}%)`],
    [`${tip("pinned", "At limit")}`, pinnedSens.length > 0 ? `<b class="bad">${pinnedSens.length}</b>` : pill("0", "good")],
  ].map(([k, v, cls]) => `<div class="kpi"><span>${k}</span><b${cls ? ` class="${cls}"` : ""}>${v}</b></div>`).join("");

  const F = S.freqs || B.freqs || [];
  const band = [t.band_lo_hz || 700, t.band_hi_hz || 5500];

  // One convention on every chart: horizontal plane solid, vertical plane dashed; start amber, best teal.
  const series2 = (key, w) => [
    ...(S[key + "_h"] ? [{ pts: F.map((f, i) => [f, S[key + "_h"][i] ?? null]), color: css("--seed"), w: 1.7 }] : []),
    ...(S[key + "_v"] ? [{ pts: F.map((f, i) => [f, S[key + "_v"][i] ?? null]), color: css("--seed"), w: 1.7, dash: true }] : []),
    ...(B[key + "_h"] ? [{ pts: F.map((f, i) => [f, B[key + "_h"][i] ?? null]), color: css("--best"), w }] : []),
    ...(B[key + "_v"] ? [{ pts: F.map((f, i) => [f, B[key + "_v"][i] ?? null]), color: css("--best"), w, dash: true }] : []),
  ];

  // Beamwidth vs target, target ±10 % shaded per plane
  if (F.length && (S.bw_h || B.bw_h)) {
    const th = t.coverage_h_deg, tv = t.coverage_v_deg;
    const bwAll = [...(S.bw_h || []), ...(S.bw_v || []), ...(B.bw_h || []), ...(B.bw_v || []), th, tv].filter(v => v != null);
    const bmax = Math.min(200, Math.ceil(Math.max(...bwAll) * 1.08 / 10) * 10) || 180;
    const fill = [], hlines = [];
    if (th) { fill.push({ y0: th * 0.9, y1: th * 1.1, color: css("--best"), opacity: 0.10 }); hlines.push({ y: th, color: css("--label") }); }
    if (tv && tv !== th) { fill.push({ y0: tv * 0.9, y1: tv * 1.1, color: css("--best"), opacity: 0.07 }); hlines.push({ y: tv, color: css("--label"), dash: true }); }
    chart(document.getElementById("c-bw"), {
      xlog: true, xlim: [F[0], F[F.length - 1]], ylim: [0, bmax], fill,
      xticks: FT, yticks: niceTicks(0, bmax, 5), xlabel: "Hz", ylabel: "deg", band, hlines,
      series: series2("bw", 2.2),
    });
  }

  // DI vs target
  if (F.length && (S.di || B.di)) {
    const dit = t.di_target_db ?? diFromCuts(t.coverage_h_deg || 90, t.coverage_v_deg || 90);
    const dall = [...(S.di || []), ...(B.di || []), dit].filter(v => v != null);
    const dlo = Math.floor(Math.min(...dall) - 1), dhi = Math.ceil(Math.max(...dall) + 1);
    chart(document.getElementById("c-di"), {
      xlog: true, xlim: [F[0], F[F.length - 1]], ylim: [dlo, dhi],
      xticks: FT, yticks: niceTicks(dlo, dhi, 5), xlabel: "Hz", ylabel: "dB", band,
      hlines: [{ y: dit, color: css("--label"), dash: true }],
      series: [
        { pts: F.map((f, i) => [f, (S.di || [])[i] ?? null]), color: css("--seed"), w: 1.7 },
        { pts: F.map((f, i) => [f, (B.di || [])[i] ?? null]), color: css("--best"), w: 2.2 },
      ],
    });
  }

  // On-axis (relative, mean removed)
  if (F.length && (S.on_axis || B.on_axis)) {
    const aall = [...(S.on_axis || []), ...(B.on_axis || [])].filter(v => v != null);
    const alo = Math.floor(Math.min(...aall, -3) - 1), ahi = Math.ceil(Math.max(...aall, 3) + 1);
    chart(document.getElementById("c-axis"), {
      xlog: true, xlim: [F[0], F[F.length - 1]], ylim: [alo, ahi],
      xticks: FT, yticks: niceTicks(alo, ahi, 5), xlabel: "Hz", ylabel: "dB", band,
      hlines: [{ y: 0, color: css("--label") }],
      series: [
        { pts: F.map((f, i) => [f, (S.on_axis || [])[i] ?? null]), color: css("--seed"), w: 1.7 },
        { pts: F.map((f, i) => [f, (B.on_axis || [])[i] ?? null]), color: css("--best"), w: 2.2 },
      ],
    });
  }

  // Throat impedance, normalised to rho*c: resistance (solid) and reactance (dashed, engineering sign:
  // + = mass-like). The solver works in exp(-i w t), so reactance X = -Im Z here.
  if (F.length && (S.z_re || B.z_re)) {
    const X = d => (d.z_im || []).map(v => v == null ? null : -v);
    const zall = [...(S.z_re || []), ...(B.z_re || []), ...X(B), ...X(S)].filter(v => v != null);
    const zlo = Math.min(0, Math.floor(Math.min(...zall) * 10) / 10), zhi = Math.max(1.2, Math.ceil(Math.max(...zall) * 10) / 10);
    chart(document.getElementById("c-zre"), {
      xlog: true, xlim: [F[0], F[F.length - 1]], ylim: [zlo, zhi],
      xticks: FT, yticks: niceTicks(zlo, zhi, 5), xlabel: "Hz", ylabel: "×ρc", band,
      hlines: [{ y: 1.0, color: css("--label"), dash: true }, { y: 0.7, color: css("--warn"), dash: true }, { y: 0, color: css("--label") }],
      series: [
        { pts: F.map((f, i) => [f, (S.z_re || [])[i] ?? null]), color: css("--seed"), w: 1.7 },
        { pts: F.map((f, i) => [f, X(S)[i] ?? null]), color: css("--seed"), w: 1.7, dash: true },
        { pts: F.map((f, i) => [f, (B.z_re || [])[i] ?? null]), color: css("--best"), w: 2.2 },
        { pts: F.map((f, i) => [f, X(B)[i] ?? null]), color: css("--best"), w: 1.8, dash: true },
      ],
    });
  }

  // Wall cross-section (true aspect): best filled, start as an outline
  wallSection(document.getElementById("c-prof"), [
    ...(S.profile ? [{ profile: S.profile, color: css("--seed"), dash: true }] : []),
    ...(B.profile ? [{ profile: B.profile, color: css("--best"), filled: true }] : []),
  ], { H: 320 });

  // Directivity isobars (Boundary Lab style): best design H and V; the start design on request
  const mapsEl = document.getElementById("polar-maps");
  function drawIsobars() {
    mapsEl.innerHTML = "";
    const withStart = document.getElementById("iso-start")?.checked && S.polar_h;
    const plots = [["Best design · horizontal", B.polar_h, B], ["Best design · vertical", B.polar_v, B]];
    if (withStart) plots.push(["Starting design · horizontal", S.polar_h, S], ["Starting design · vertical", S.polar_v, S]);
    for (const [lbl, rows, D2] of plots) {
      if (!rows) continue;
      const sv = document.createElementNS(NS, "svg"); sv.setAttribute("class", "polar");
      sv.setAttribute("role", "img"); sv.setAttribute("aria-label", lbl + " isobar plot");
      mapsEl.appendChild(sv);
      // drawn after layout, so each plot is measured at its real width
      requestAnimationFrame(() => isobarMap(sv, rows, D2.angles || [], D2.freqs || F, { title: lbl, H: 300 }));
    }
  }
  drawIsobars();
  document.getElementById("iso-start").onchange = drawIsobars;

  // Convergence
  if (d.J && F.length) {
    const Js = (d.J || []).map((j, i) => [i, j]).filter(p => p[1] != null);
    let rb = Infinity; const runBest = Js.map(p => [p[0], (rb = Math.min(rb, p[1]))]);
    const ymax = Math.max((sum.seed_j || 0) * 1.6, (sum.best_j || 0) * 2, 1);
    const svg = document.getElementById("c-conv");
    chart(svg, {
      xlim: [0, sum.n || Js.length], ylim: [0, ymax],
      xticks: niceTicks(0, sum.n || Js.length, 5), yticks: niceTicks(0, ymax, 5),
      xlabel: "evaluation", ylabel: "score",
      series: [
        { pts: Js, color: css("--muted"), dots: true, opacity: 0.8 },
        { pts: runBest, color: css("--best"), w: 2.2 },
      ],
      hlines: [{ y: sum.seed_j, color: css("--seed"), dash: true }],
    });
  }

  // Terms bar chart
  if (d.terms_seed && d.terms_best) {
    const svgT = document.getElementById("c-terms");
    svgT.innerHTML = "";
    const W = 460, rowH = 32, H = TERM_ORDER.length * rowH + 30;
    svgT.setAttribute("viewBox", `0 0 ${W} ${H}`);
    const vals = TERM_ORDER.map(k => [w[k] * (d.terms_seed[k] || 0), w[k] * (d.terms_best[k] || 0)]);
    const vmax = Math.max(...vals.flat(), 1e-9);
    const L = 90, R = 54, X = v => L + v / vmax * (W - L - R);
    TERM_ORDER.forEach((k, i) => {
      const y = 6 + i * rowH;
      const gEntry = GLOSSARY[k];
      const label = gEntry ? gEntry.label : k;
      const lab = el("text", { x: L - 8, y: y + 15, "text-anchor": "end" }, svgT);
      lab.textContent = label + (w[k] ? "" : " (w=0)");
      [[vals[i][0], "--seed", 0], [vals[i][1], "--best", 12]].forEach(([v, c, dy]) => {
        el("rect", { x: L, y: y + dy, width: Math.max(0.5, X(v) - L), height: 10, rx: 2, fill: css(c) }, svgT);
        const tv = el("text", { x: X(v) + 4, y: y + dy + 9 }, svgT); tv.textContent = v.toFixed(3);
      });
    });
    const lg = el("text", { x: L, y: H - 4 }, svgT); lg.textContent = "upper = start · lower = best · weighted";
  }

  // Sensitivity table
  const sensT = document.getElementById("sens-table");
  if (d.sens && d.sens.length) {
    let s = `<thead><tr>
      <th>Parameter</th><th class="r">Low limit</th><th class="r">High limit</th>
      <th class="r">Best value</th><th class="r">${tip("rho", "Influence ρ")}</th><th></th>
      <th class="r">${tip("pinned", "Top-6 at low")}</th><th class="r">at high</th></tr></thead><tbody>`;
    for (const p of d.sens) {
      const bar = `<svg width="90" height="10" viewBox="0 0 90 10" aria-hidden="true">
        <rect x="45" y="0" width="0.8" height="10" fill="${css("--muted")}"/>
        <rect x="${p.rho < 0 ? 45 + p.rho * 45 : 45}" y="2" width="${Math.abs(p.rho || 0) * 45}" height="6" rx="1"
          fill="${css(p.rho > 0 ? "--seed" : "--best")}"/></svg>`;
      const flag = v => v >= 4 ? `<span class="pill bad">${v}/6</span>` : v >= 2 ? `<span class="pill warn">${v}/6</span>` : `${v}/6`;
      const atHi = p.at_hi != null ? p.at_hi : 0;
      s += `<tr><td class="mono">${esc(p.key)}</td>
        <td class="r">${fmt(p.lo, 3)}</td><td class="r">${fmt(p.hi, 3)}</td>
        <td class="r">${fmt(p.best, 3)}</td>
        <td class="r">${p.rho != null ? p.rho.toFixed(2) : "–"}</td>
        <td>${bar}</td><td class="r">${flag(p.at_lo || 0)}</td><td class="r">${flag(atHi)}</td></tr>`;
    }
    sensT.innerHTML = s + "</tbody>";
  } else {
    sensT.innerHTML = "<tr><td class='muted'>No sensitivity data.</td></tr>";
  }

  // Files the user can take away: STEP downloads (after an export) and the full report.
  function renderFiles(files) {
    const box = document.getElementById("run-files");
    if (!box) return;
    box.innerHTML = files && files.length
      ? `<span class="muted">STEP solids (mm, full horn, throat open; add the driver flange in CAD):</span> ` +
        files.map(f => `<a class="pill" href="/runs/${esc(id)}/step/${encodeURIComponent(f)}" download>↓ ${esc(f.replace(/^.*_(rank\d+)_.*$/, "$1"))}</a>`).join(" ")
      : "";
  }
  renderFiles(d.step_files);

  // Run a CPU job (report / STEP export) in place: progress on the button, result on this page.
  async function runInline(btn, kind, args, busyLabel, onDone) {
    const label = btn.textContent;
    btn.disabled = true;
    const r = await post("/api/jobs", { kind, args });
    if (r.error) { btn.disabled = false; btn.textContent = label; showToast("Could not start: " + r.error, "error"); return; }
    const t0 = Date.now();
    while (ROOT === currentRoot()) {
      btn.textContent = `${busyLabel} ${Math.round((Date.now() - t0) / 1000)} s`;
      await new Promise(res => setTimeout(res, 1500));
      let j; try { j = await api("/api/job/" + r.id); } catch { continue; }
      if (j.status === "running") continue;
      btn.disabled = false; btn.textContent = label;
      if (j.status === "done") onDone(j); else showToast(`${kind} failed: ` + ((j.log_tail || []).slice(-1)[0] || j.status), "error");
      return;
    }
  }
  document.getElementById("btn-step").onclick = e => runInline(e.currentTarget, "export-step", { run: id, top: 3 }, "Exporting…",
    async () => { const dd = await api("/api/run/" + id); renderFiles(dd.step_files); showToast("STEP files ready: download them below the buttons.", "good"); });
  const rBtn = document.getElementById("btn-gen-report");
  if (rBtn) rBtn.onclick = e => runInline(e.currentTarget, "report", { run: id }, "Building report…", () => {
    document.getElementById("report-slot").innerHTML = `<a class="btn" href="/runs/${esc(id)}/report.html" target="_blank" rel="noopener">Open full report ↗</a>`;
    showToast("Report ready.", "good");
  });
}

// ── View 3 / 7: 3D view ────────────────────────────────────────────

async function viewRun3D(id) {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let runD, meshD;
  try { runD = await api("/api/run/" + id); }
  catch (e) { ROOT.innerHTML = errBanner("Could not load run: " + e.message); return; }
  const hash = (runD.summary || runD).best_hash || ((runD.best || {}).hash);
  if (!hash) { ROOT.innerHTML = errBanner("No best design hash for this run."); return; }
  try { meshD = await api("/api/mesh/" + id + "/" + hash); }
  catch (e) { ROOT.innerHTML = errBanner("Could not load mesh: " + e.message); return; }

  const sum = runD.summary || runD;
  const qNote = (() => { const q = String(meshD.quadrants || "1234");
    if (q === "1") return "quarter model mirrored to the full horn";
    if (q === "14" || q === "12") return "half model mirrored to the full horn";
    return "full model, no mirroring"; })();
  ROOT.innerHTML = `
    <div class="stack" style="gap:16px">
      <div>
        <div class="eyebrow">3D view</div>
        <h2>${esc(sum.name || id)}</h2>
        <p class="muted" style="font-size:0.82rem">Hash: <span class="mono">${esc(hash)}</span> · ${esc(meshD.n_tris || "?")} triangles in the meshed domain (${esc(qNote)})</p>
      </div>
      <div class="btn-row">
        <a class="btn" href="#/run/${esc(id)}">← Back to run</a>
      </div>
      <div class="fig-head">
        <label class="evo-opt" style="color:var(--ink)"><input type="checkbox" id="v3d-shadows" ${(() => { try { return localStorage.getItem("hl-v3d-shadows") === "0" ? "" : "checked"; } catch { return "checked"; } })()}> wall shadows</label>
      </div>
      <div id="view3d-wrap"><div class="view3d-fallback">Loading 3D…</div></div>
      <p class="muted" style="font-size:0.8rem">Drag to orbit · scroll to zoom · right-drag to pan.</p>
    </div>`;

  const wrap = document.getElementById("view3d-wrap");
  const profile = (runD.best || {}).profile;
  const seedProfile = (runD.seed || {}).profile;      // dashed under best in the 2D fallback
  const shadowsBox = document.getElementById("v3d-shadows");
  let shadows = true;
  try { shadows = localStorage.getItem("hl-v3d-shadows") !== "0"; } catch {}
  if (shadowsBox) shadowsBox.checked = shadows;
  await init3d(wrap, meshD, profile, seedProfile, shadows);
  if (shadowsBox) shadowsBox.onchange = () => {
    try { localStorage.setItem("hl-v3d-shadows", shadowsBox.checked ? "1" : "0"); } catch {}
    if (wrap._dispose3d) wrap._dispose3d();
    init3d(wrap, meshD, profile, seedProfile, shadowsBox.checked).catch(() => {});
  };
}

// ── View 4: Compare ────────────────────────────────────────────────

async function viewCompare() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let allRuns = [];
  try { allRuns = await api("/api/runs"); } catch {}

  const hash = location.hash;
  const qaMatch = hash.match(/[?&]a=([^&]+)/);
  const qbMatch = hash.match(/[?&]b=([^&]+)/);
  const preA = qaMatch ? qaMatch[1] : "";
  const preB = qbMatch ? qbMatch[1] : "";

  const opts = allRuns.map(r =>
    `<option value="${esc(r.id)}">${esc(r.name)} — ${esc(r.id.slice(0, 20))}… (Score=${fmt(r.best_j)})</option>`
  ).join("");

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Compare two runs</div>
        <h2>Compare</h2>
      </div>
      <div class="compare-pickers">
        <div class="form-group">
          <label for="cmp-a">Run A</label>
          <select id="cmp-a" aria-label="run A">
            <option value="">— select —</option>${opts}
          </select>
        </div>
        <div class="form-group">
          <label for="cmp-b">Run B</label>
          <select id="cmp-b" aria-label="run B">
            <option value="">— select —</option>${opts}
          </select>
        </div>
      </div>
      <div><button id="btn-compare" class="primary">Compare</button></div>
      <div id="compare-result"></div>
    </div>`;

  if (preA) document.getElementById("cmp-a").value = preA;
  if (preB) document.getElementById("cmp-b").value = preB;

  async function doCompare() {
    const a = document.getElementById("cmp-a").value;
    const b = document.getElementById("cmp-b").value;
    const res = document.getElementById("compare-result");
    if (!a || !b) { res.innerHTML = `<div class="alert warn">Select both runs.</div>`; return; }
    if (a === b) { res.innerHTML = `<div class="alert warn">Select two different runs.</div>`; return; }
    res.innerHTML = `<p class="muted">Loading…</p>`;
    let cmp;
    try { cmp = await api(`/api/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`); }
    catch (e) { res.innerHTML = errBanner(e.message); return; }
    if (cmp.error) { res.innerHTML = errBanner(cmp.error); return; }

    const rowData = Object.entries(cmp.rows || {});
    const metricTable = rowData.length ? `
      <div class="tbl-wrap">
        <table>
          <thead><tr><th>Metric</th><th>Unit</th>
            <th class="r">max |A − B|</th><th class="r">mean |A − B|</th><th class="r">n freqs</th></tr></thead>
          <tbody>${rowData.map(([k, v]) => `<tr>
            <td>${esc(CMP_LABEL[k] || k)} <small class="mono muted">${esc(k)}</small></td><td class="mono muted">${esc(v.unit || "")}</td>
            <td class="r">${fmt(v.max, 3)}</td><td class="r">${fmt(v.mean, 3)}</td><td class="r">${esc(v.n ?? "")}</td>
          </tr>`).join("")}</tbody>
        </table>
      </div>` : "<p class='muted'>No metric data.</p>";

    const dA = cmp.a || {}, dB = cmp.b || {};
    const FA = dA.freqs || [], FB = dB.freqs || [];
    const F = FA.length ? FA : FB;
    const band = [700, 5500];

    res.innerHTML = `
      <div class="stack" style="gap:20px">
        <h3>Metric comparison</h3>
        <p class="muted" style="font-size:0.83rem">Per-frequency |A − B| on the shared grid.</p>
        ${metricTable}
        <div class="grid2">
          <div class="fig"><h3>${tip("bw", "Beamwidth")} H</h3>
            <div class="legend"><span><i style="color:var(--seed)"></i>A</span><span><i style="color:var(--best)"></i>B</span></div>
            <svg id="cmp-bwh"></svg></div>
          <div class="fig"><h3>${tip("bw", "Beamwidth")} V</h3>
            <div class="legend"><span><i style="color:var(--seed)"></i>A</span><span><i style="color:var(--best)"></i>B</span></div>
            <svg id="cmp-bwv"></svg></div>
          <div class="fig"><h3>${tip("di_db", "DI")}</h3>
            <div class="legend"><span><i style="color:var(--seed)"></i>A</span><span><i style="color:var(--best)"></i>B</span></div>
            <svg id="cmp-di"></svg></div>
          <div class="fig"><h3>${tip("on_axis", "On-axis")}</h3>
            <div class="legend"><span><i style="color:var(--seed)"></i>A</span><span><i style="color:var(--best)"></i>B</span></div>
            <svg id="cmp-axis"></svg></div>
        </div>
      </div>`;

    if (!F.length) return;

    function cmpChart(svgId, keyA, keyB, ylabel) {
      const svg = document.getElementById(svgId);
      if (!svg) return;
      const allV = [...(dA[keyA] || []), ...(dB[keyB] || [])].filter(v => v != null);
      if (!allV.length) return;
      const lo = Math.floor(Math.min(...allV) - 1), hi = Math.ceil(Math.max(...allV) + 1);
      chart(svg, {
        xlog: true, xlim: [F[0], F[F.length - 1]], ylim: [lo, hi],
        xticks: FT, yticks: niceTicks(lo, hi, 5), xlabel: "Hz", ylabel, band,
        series: [
          { pts: F.map((f, i) => [f, (dA[keyA] || [])[i] ?? null]), color: css("--seed"), w: 1.8 },
          { pts: F.map((f, i) => [f, (dB[keyB] || [])[i] ?? null]), color: css("--best"), w: 1.8 },
        ],
      });
    }
    cmpChart("cmp-bwh", "bw_h", "bw_h", "°");
    cmpChart("cmp-bwv", "bw_v", "bw_v", "°");
    cmpChart("cmp-di", "di", "di", "dB");
    cmpChart("cmp-axis", "on_axis", "on_axis", "dB");
  }

  document.getElementById("btn-compare").onclick = doCompare;
  if (preA && preB) doCompare();
}

// ── View 5: Briefs ─────────────────────────────────────────────────

// Starting values for a brand-new brief. They mirror the shipped brief
// examples/briefs/axi_90x90_1in.yaml (coverage angles, scoring weights, 1-inch driver) with a
// wider-than-tall envelope; everything else is the schema default in config.py::load_brief.
const NEW_BRIEF_DEFAULTS = {
  target: { coverage_h_deg: 90, coverage_v_deg: 90, band_lo_hz: 500, band_hi_hz: 5500,
            di_target_db: null, di_slope_target: 0, z_min: 0 },
  weights: { cov: 1.0, rip: 1.0, di: 0.3, dislope: 0.5, flat: 0.5, load: 0.5 },
  envelope: { max_mouth_w_mm: 500, max_mouth_h_mm: 400, max_depth_mm: 250 },
  driver: { exit_radius_mm: 12.7, exit_angle_deg: 0, throat_angle_policy: "free" },
  symmetry: "hv", objective_version: 1, verify_only: false,
};

function newBriefDraft() {
  return { name: "", kind: "new", path: "", brief: {
    name: "", description: "",
    driver: { ...NEW_BRIEF_DEFAULTS.driver },
    envelope: { ...NEW_BRIEF_DEFAULTS.envelope },
    symmetry: NEW_BRIEF_DEFAULTS.symmetry,
    source: {},
    target: { ...NEW_BRIEF_DEFAULTS.target },
    weights: { ...NEW_BRIEF_DEFAULTS.weights },
    verify_only: NEW_BRIEF_DEFAULTS.verify_only,
    objective: { version: NEW_BRIEF_DEFAULTS.objective_version },
  } };
}

async function viewBriefs() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let briefs, configs = [];
  try {
    [briefs, configs] = await Promise.all([
      api("/api/briefs"),
      api("/api/configs").catch(() => []),   // the typology picker; its absence must not kill the page
    ]);
  } catch (e) { ROOT.innerHTML = errBanner(e.message); return; }

  if (!briefs.length) {
    ROOT.innerHTML = `<div class="stack" style="gap:20px">
      <div><div class="eyebrow">Briefs &amp; families</div><h2>Briefs</h2></div>
      <p class="muted">No briefs found.</p>
    </div>`;
    return;
  }

  // Typology picker options: grouped by catalog group, captioned with the family, disabled
  // entries kept visible (marker + disabled attribute) so their existence is never hidden.
  const GROUP_LABEL = { classical: "Classical horns", hybrid: "Hybrids", organic: "Organic horns",
                        magnus: "Magnus mesher families", legacy: "Utility / legacy" };
  const byGroup = {};
  for (const c of configs) (byGroup[c.group || "Other"] = byGroup[c.group || "Other"] || []).push(c);
  let pickOpts = `<option value="">— pick a typology's brief —</option>`;
  for (const [grp, list] of Object.entries(byGroup)) {
    pickOpts += `<optgroup label="${esc(GROUP_LABEL[grp] || grp)}">`;
    for (const c of list) {
      const desc = c.description ? ` — ${c.description.slice(0, 60)}` : "";
      pickOpts += `<option value="${esc(c.path)}" ${c.disabled ? "disabled" : ""}>${esc(c.catalog_name || c.name)} · ${esc(c.family || "—")}${esc(desc)}${c.disabled ? " (disabled)" : ""}</option>`;
    }
    pickOpts += `</optgroup>`;
  }

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Briefs &amp; families</div>
        <h2>Briefs</h2>
        <p class="muted" style="font-size:0.85rem">Select a brief to view or edit its parameters. Save a modified copy under a new name, start a new brief from scratch, or start from a typology's brief.</p>
      </div>
      <div style="display:flex;align-items:center;flex-wrap:wrap;gap:10px" role="toolbar" aria-label="Brief authoring">
        <button id="btn-new-brief" title="Open the editor with schema-safe defaults">New brief</button>
        <label for="typo-pick" class="form-label" style="font-family:var(--f-mono);font-size:0.8rem;color:var(--muted)">Start from typology</label>
        <select id="typo-pick" style="font:inherit;font-size:0.88rem;background:var(--bg);color:var(--ink);border:1px solid var(--rule);border-radius:5px;padding:6px 10px;min-width:260px;max-width:100%">${pickOpts}</select>
        <span id="typo-pick-msg" class="hint" role="status"></span>
      </div>
      ${configs.length ? "" : `<p class="hint">Typology list unavailable — New brief still works.</p>`}
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px" id="briefs-list"></div>
      <div id="brief-detail"></div>
    </div>`;

  const listEl = document.getElementById("briefs-list");
  briefs.forEach(b => {
    const btn = document.createElement("button");
    btn.className = "card";
    btn.style.cssText = "text-align:left;cursor:pointer;";
    btn.innerHTML = `<div style="font-weight:500">${esc(b.name)}</div>
      <div class="muted mono" style="font-size:0.75rem">${esc(b.kind)}</div>`;
    btn.onclick = () => showBriefDetail(b, briefs);
    listEl.appendChild(btn);
  });

  document.getElementById("btn-new-brief").onclick = async () => {
    await showBriefDetail(newBriefDraft(), briefs, { mode: "new", scroll: true });
  };

  const pickSel = document.getElementById("typo-pick");
  const pickMsg = document.getElementById("typo-pick-msg");
  pickSel.onchange = async e => {
    pickMsg.textContent = "";
    const c = configs.find(c => c.path === e.target.value);
    if (!c) return;
    if (!c.brief_file) {
      pickMsg.textContent = `${c.catalog_name || c.name} has no brief_file configured — use New brief instead.`;
      e.target.value = "";
      return;
    }
    const stem = String(c.brief_file).replace(/\\/g, "/").split("/").pop().replace(/\.(yaml|yml)$/, "");
    const br = briefs.find(x => x.name === stem) ||
               briefs.find(x => x.path === String(c.brief_file).replace(/\\/g, "/"));
    if (!br) {
      pickMsg.textContent = `Brief file ${c.brief_file} was not found among the briefs on this page.`;
      e.target.value = "";
      return;
    }
    await showBriefDetail(br, briefs, { mode: "typology", origin: c, scroll: true });
  };

  if (briefs.length) showBriefDetail(briefs[0], briefs);
}

async function showBriefDetail(b, allBriefs, opts = {}) {
  const isNew = opts.mode === "new";
  const det = document.getElementById("brief-detail");
  det.innerHTML = `<p class="muted">Loading…</p>`;
  const br = b.brief || {};
  const tgt = br.target || {};
  const wt = br.weights || {};
  const env = br.envelope || {};
  const drv = br.driver || {};

  // 5500 Hz is the search ceiling on the 8 GB RTX 4060 (mesh dof cap, TOOLCHAIN.md) — a practical
  // hardware note, NOT a schema rule: the schema accepts any band_hi above band_lo, and the
  // verify-only *_12k briefs run at 12000. Values are saved as typed, never clamped.
  const bandHiOver = (tgt.band_hi_hz || 0) > 5500;
  const bandHiWarn = bandHiOver
    ? `<span class="warn-text">⚠ band_hi above 5500 Hz — beyond the 8 GB GPU dof cap: verify-only territory (like the *_12k briefs), not search</span>` : "";

  const pol = drv.throat_angle_policy;                    // "pin" | "free" | absent
  const objVer = (br.objective || {}).version ?? 1;
  // band_hz must be an array of rows; a hand-edited brief may carry anything (list_briefs does no
  // validation) — a non-array is disclosed, never allowed to break the form mid-render.
  const fwRaw = (tgt.freq_weights || {}).band_hz;
  const fwRows = Array.isArray(fwRaw) ? fwRaw.filter(r => Array.isArray(r) && r.length >= 1).map(r => r.map(v => v == null ? "" : String(v))) : [];
  const fwBadNote = !Array.isArray(fwRaw) ? `<div class="hint" style="margin-bottom:6px"><span class="warn-text">⚠ this brief's target.freq_weights.band_hz is not a list of rows — not editable here (fix the YAML)</span></div>` : "";

  const headTitle = isNew ? "New brief" : esc(b.name);
  const kindLabel = isNew ? "new (unsaved)" : b.kind;
  const provenance = (opts.mode === "typology" && opts.origin)
    ? `<p class="hint" style="font-size:0.8rem;margin:4px 0 0" role="note">Starting point loaded: <b>${esc(opts.origin.catalog_name || opts.origin.name)}</b> names this brief as its brief_file — catalog group ${esc(opts.origin.group || "—")}, family ${esc(opts.origin.family || "—")}. The typology itself is unchanged; saving below writes your own copy.</p>`
    : "";

  const INPUT_CSS = "font:inherit;font-size:0.88rem;background:var(--bg);color:var(--ink);border:1px solid var(--rule);border-radius:5px;padding:6px 10px;max-width:100%";

  det.innerHTML = `
    <div class="stack" style="gap:20px">
      <hr class="sep">
      <div>
        <h3>${headTitle} <span class="pill" style="font-size:0.7rem;border-color:var(--muted);color:var(--muted)">${esc(kindLabel)}</span></h3>
        ${isNew ? "" : `<p class="muted" style="font-size:0.85rem">${esc(br.description || "")}</p>`}
        ${isNew ? "" : `<p class="muted mono" style="font-size:0.75rem">${esc(b.path || "")}</p>`}
        ${provenance}
      </div>
      <form id="brief-form" class="stack" style="gap:20px">

        <fieldset>
          <legend>Identity &amp; symmetry</legend>
          <div class="form-grid">
            <label for="brf-desc">Description</label>
            <div><input id="brf-desc" type="text" value="${esc(br.description || "")}" placeholder="what this brief is for"
              style="${INPUT_CSS};width:min(420px,100%)">
              <div class="hint">Stored in the brief YAML (free text, may be empty)</div></div>
            <label for="brf-sym">Symmetry</label>
            <div><select id="brf-sym" style="${INPUT_CSS};width:220px">
                <option value="hv" ${br.symmetry !== "axisymmetric" ? "selected" : ""}>hv — H and V may differ</option>
                <option value="axisymmetric" ${br.symmetry === "axisymmetric" ? "selected" : ""}>axisymmetric — body of revolution</option>
              </select>
              <div class="hint">The server refuses axisymmetric briefs with unequal coverage: "an axisymmetric brief needs coverage_h_deg == coverage_v_deg"</div></div>
            <label for="brf-verify-only">verify_only</label>
            <div><input id="brf-verify-only" type="checkbox" ${br.verify_only ? "checked" : ""}>
              <div class="hint">verify_only briefs are refused by search/run/campaign — only <code>verify --brief</code> uses them (the 12 kHz briefs work this way)</div></div>
            <label for="brf-obj">Objective version</label>
            <div><select id="brf-obj" style="${INPUT_CSS};width:220px">
                <option value="1" ${objVer === 1 ? "selected" : ""}>1 — default scoring</option>
                <option value="2" ${objVer === 2 ? "selected" : ""}>2 — opt-in updated scoring</option>
              </select>
              <div class="hint">Every shipped brief scores with version 1; version 2 is the opt-in update</div></div>
          </div>
        </fieldset>

        <fieldset>
          <legend>Target</legend>
          <div class="form-grid">
            <label for="brf-cov-h">${tip("bw", "Coverage H")} °</label>
            <div><input id="brf-cov-h" type="number" step="1" min="5" max="180" value="${tgt.coverage_h_deg ?? 90}">
              <div class="hint">Horizontal −6 dB coverage angle in degrees (5–180)</div></div>
            <label for="brf-cov-v">${tip("bw", "Coverage V")} °</label>
            <div><input id="brf-cov-v" type="number" step="1" min="5" max="180" value="${tgt.coverage_v_deg ?? 90}">
              <div class="hint">Vertical −6 dB coverage angle in degrees</div></div>
            <label for="brf-blo">${tip("band", "Band low")} Hz</label>
            <div><input id="brf-blo" type="number" step="10" min="100" value="${tgt.band_lo_hz ?? 700}">
              <div class="hint">Lowest scored frequency</div></div>
            <label for="brf-bhi">${tip("band", "Band high")} Hz</label>
            <div>
              <input id="brf-bhi" type="number" step="100" value="${tgt.band_hi_hz ?? 5500}">
              <div class="hint" id="bhi-warn">${bandHiWarn || "5500 Hz is the practical search ceiling on the 8 GB RTX 4060; higher values are saved as typed and belong to verify-only passes"}</div>
            </div>
            <label for="brf-di">${tip("di_db", "DI target")} dB</label>
            <div><input id="brf-di" type="number" step="0.1" value="${tgt.di_target_db ?? ""}" placeholder="auto from coverage">
              <div class="hint">Leave blank to derive from coverage angles</div></div>
            <label for="brf-dislope">${tip("dislope", "DI slope target")}</label>
            <div><input id="brf-dislope" type="number" step="0.01" value="${tgt.di_slope_target ?? 0}">
              <div class="hint">0 = constant directivity</div></div>
            <label for="brf-zmin">${tip("load", "Loading threshold")} z_min</label>
            <div><input id="brf-zmin" type="number" step="0.05" min="0" max="1" value="${tgt.z_min ?? 0}">
              <div class="hint">Lowest scored frequency loading threshold — the throat-impedance floor the load term scores below (classical briefs use 0.7, default 0)</div></div>
          </div>
        </fieldset>

        <fieldset>
          <legend>Weights <span class="muted" style="font-size:0.72rem;font-weight:400;text-transform:none;letter-spacing:0">(relative importance — 0 turns a term off)</span></legend>
          <div class="form-grid">
            ${TERM_ORDER.map(k => `<label for="brf-w-${k}">${tip(k)}</label>
              <div><input id="brf-w-${k}" type="number" step="0.1" min="0" value="${wt[k] ?? DEFW[k]}">
                <div class="hint" style="font-size:0.72rem">${GLOSSARY[k]?.short || ""}</div></div>`).join("")}
          </div>
        </fieldset>

        <fieldset>
          <legend>Size envelope</legend>
          <div class="form-grid">
            <label for="brf-mw">Max mouth width mm</label>
            <input id="brf-mw" type="number" step="1" value="${env.max_mouth_w_mm ?? 360}">
            <label for="brf-mh">Max mouth height mm</label>
            <input id="brf-mh" type="number" step="1" value="${env.max_mouth_h_mm ?? 360}">
            <label for="brf-md">Max depth mm</label>
            <input id="brf-md" type="number" step="1" value="${env.max_depth_mm ?? 220}">
            <span class="form-label" style="color:var(--muted)">Note</span>
            <div class="hint">Width and height are independent — a wider-than-tall mouth is legal for every symmetry value</div>
          </div>
        </fieldset>

        <fieldset>
          <legend>Driver</legend>
          <div class="form-grid">
            <label for="brf-er">Exit radius mm</label>
            <div><input id="brf-er" type="number" step="0.1" value="${drv.exit_radius_mm ?? 12.7}">
              <div class="hint">Radius of the driver's throat exit</div></div>
            <label for="brf-ea">Exit angle °</label>
            <div><input id="brf-ea" type="number" step="0.1" value="${drv.exit_angle_deg ?? 5.0}">
              <div class="hint">Half-angle of the exit cone</div></div>
            <label for="brf-pol">Throat angle policy</label>
            <div><select id="brf-pol" style="${INPUT_CSS};width:340px;max-width:100%">
                <option value="" ${pol == null ? "selected" : ""}>— not set (each family keeps its own throat behaviour) —</option>
                <option value="free" ${pol === "free" ? "selected" : ""}>free — throat angle stays searchable</option>
                <option value="pin" ${pol === "pin" ? "selected" : ""}>pin — throat angle pinned to the driver exit angle</option>
              </select>
              <div class="hint">pin exists so every family competes on the same throat; absent key = exactly the pre-pin behaviour</div></div>
          </div>
        </fieldset>

        <details id="brf-advanced" style="border:1px solid var(--rule);border-radius:6px;padding:10px 14px">
          <summary style="cursor:pointer;font-family:var(--f-mono);font-size:0.78rem;color:var(--accent)">Advanced — frequency weights${br.grid ? " · grid carried through" : ""}</summary>
          <div class="stack" style="gap:8px;margin-top:10px">
            <div>
              ${fwBadNote}
              <div class="hint" style="margin-bottom:6px"><code>target.freq_weights</code> — one row per frequency slice: lo_hz, hi_hz, weight. A frequency gets the product of every slice containing it; empty means no weighting. Checked here (non-negative numbers, lo &lt; hi), then re-validated by the server on save.</div>
              <div id="brf-fw-rows" class="stack" style="gap:6px"></div>
              <button type="button" id="brf-fw-add" style="margin-top:8px">+ Add frequency-weight row</button>
              <div id="brf-fw-msg" style="margin-top:6px"></div>
            </div>
            ${br.grid ? `<div class="hint">grid: verify_points_per_octave ${esc(String(br.grid.verify_points_per_octave ?? "—"))} — carried through unchanged (edit the YAML for another value)</div>` : ""}
            <div class="hint">source: cap ${esc(String((br.source || {}).cap ?? "auto"))} — carried through unchanged</div>
          </div>
        </details>

        <div>
          <div style="display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
            <input id="brf-save-name" type="text" placeholder="new-brief-name"
              pattern="[A-Za-z0-9_-]{1,64}" title="Letters, digits, _ and - only (max 64)"
              aria-label="save as name"
              style="${INPUT_CSS};width:180px">
            <button type="button" id="btn-save-brief" class="primary">Save as new brief</button>
          </div>
          <div class="hint">Name: letters, digits, _ and - only (max 64 characters)</div>
          <div id="brief-save-msg" style="margin-top:8px"></div>
        </div>

        ${isNew ? `<p class="hint" style="margin:0" role="note">Starting values follow the shipped brief <code>examples/briefs/axi_90x90_1in.yaml</code> (coverage angles, scoring weights, band top 5500); the 500 × 400 × 250 mm envelope is wider than tall like your own briefs and band low 500 Hz is the compose default; every other field is the schema default. All of it is editable.</p>` : ""}

      </form>

      ${isNew ? "" : `
      <div>
        <h4 style="margin-bottom:8px">Families compatible with this brief</h4>
        <button id="btn-families">Show compatible families</button>
        <pre class="families-out" id="families-out" style="display:none"></pre>
      </div>`}
    </div>`;

  // Frequency-weight rows (target.freq_weights). Collapsed by default; values persist as typed.
  const fwBox = document.getElementById("brf-fw-rows");
  function addFwRow(r = ["", "", ""]) {
    const div = document.createElement("div");
    div.className = "fw-row";
    div.style.cssText = "display:flex;gap:8px;align-items:center;flex-wrap:wrap";
    div.innerHTML = `
      <input type="number" class="fw-lo" min="0" step="1" aria-label="freq weight lo_hz" placeholder="lo_hz" style="${INPUT_CSS};width:104px" value="${esc(r[0] ?? "")}">
      <span class="muted" aria-hidden="true">–</span>
      <input type="number" class="fw-hi" min="0" step="1" aria-label="freq weight hi_hz" placeholder="hi_hz" style="${INPUT_CSS};width:104px" value="${esc(r[1] ?? "")}">
      <span class="muted" aria-hidden="true">×</span>
      <input type="number" class="fw-w" min="0" step="0.1" aria-label="freq weight weight" placeholder="weight" style="${INPUT_CSS};width:84px" value="${esc(r[2] ?? "")}">
      <button type="button" class="fw-del" aria-label="Remove this frequency-weight row" title="Remove this row">✕</button>`;
    div.querySelector(".fw-del").onclick = () => div.remove();
    fwBox.appendChild(div);
  }
  fwRows.forEach(r => addFwRow(r));
  document.getElementById("brf-fw-add").onclick = () => addFwRow();

  // Band-hi note (honest, no clamp): the value is saved exactly as typed.
  document.getElementById("brf-bhi").addEventListener("input", e => {
    const v = +e.target.value;
    const warnEl = document.getElementById("bhi-warn");
    if (v > 5500) {
      warnEl.innerHTML = `<span class="warn-text">⚠ band_hi above 5500 Hz — beyond the 8 GB GPU dof cap (verify-only territory); saved as typed, no clamp</span>`;
    } else {
      warnEl.textContent = "5500 Hz is the practical search ceiling on the 8 GB RTX 4060; higher values are saved as typed and belong to verify-only passes";
    }
  });

  // Save brief
  document.getElementById("btn-save-brief").onclick = async () => {
    const name = document.getElementById("brf-save-name").value.trim();
    const msg = document.getElementById("brief-save-msg");
    if (!name) { msg.innerHTML = `<div class="alert warn">Enter a brief name.</div>`; return; }
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(name)) {
      msg.innerHTML = `<div class="alert error">Name must be letters, digits, _ and - only (max 64).</div>`; return;
    }
    // Frequency-weight rows: numbers, non-negative, lo < hi — client-side only; the server
    // (config.load_brief) re-validates for real and its error is shown verbatim below.
    const fw = [];
    let fwErr = "";
    for (const row of document.querySelectorAll("#brf-fw-rows .fw-row")) {
      const lo = row.querySelector(".fw-lo").value.trim(),
            hi = row.querySelector(".fw-hi").value.trim(),
            w  = row.querySelector(".fw-w").value.trim();
      if (lo === "" && hi === "" && w === "") continue;
      const L = +lo, H = +hi, W = +w;
      if (lo === "" || hi === "" || w === "" || !Number.isFinite(L) || !Number.isFinite(H) || !Number.isFinite(W))
        fwErr = "Every frequency-weight row needs numbers for lo_hz, hi_hz and weight.";
      else if (L < 0 || H < 0 || W < 0)
        fwErr = "Frequency-weight rows must be non-negative.";
      else if (L >= H)
        fwErr = "lo_hz must be below hi_hz in every frequency-weight row.";
      else fw.push([L, H, W]);
    }
    const fwMsg = document.getElementById("brf-fw-msg");
    if (fwErr) {
      fwMsg.innerHTML = `<span class="warn-text">⚠ ${esc(fwErr)}</span>`;
      msg.innerHTML = `<div class="alert warn">Fix the advanced frequency-weight rows before saving.</div>`;
      document.getElementById("brf-advanced").open = true;
      return;
    }
    fwMsg.textContent = "";
    const newBrief = {
      name,
      description: document.getElementById("brf-desc").value.trim(),
      driver: { exit_radius_mm: +document.getElementById("brf-er").value,
                exit_angle_deg: +document.getElementById("brf-ea").value,
                throat_angle_policy: document.getElementById("brf-pol").value || null },
      envelope: { max_mouth_w_mm: +document.getElementById("brf-mw").value,
                  max_mouth_h_mm: +document.getElementById("brf-mh").value,
                  max_depth_mm: +document.getElementById("brf-md").value },
      symmetry: document.getElementById("brf-sym").value,
      source: br.source || {},
      target: {
        coverage_h_deg: +document.getElementById("brf-cov-h").value,
        coverage_v_deg: +document.getElementById("brf-cov-v").value,
        band_lo_hz: +document.getElementById("brf-blo").value,
        band_hi_hz: +document.getElementById("brf-bhi").value,     // no clamp: the server validates for real
        di_target_db: document.getElementById("brf-di").value === "" ? null : +document.getElementById("brf-di").value,
        di_slope_target: +document.getElementById("brf-dislope").value,
        z_min: +document.getElementById("brf-zmin").value,
        ...(fw.length ? { freq_weights: { band_hz: fw } } : {}),   // absent = no weighting (schema default)
      },
      weights: Object.fromEntries(TERM_ORDER.map(k => [k, +document.getElementById(`brf-w-${k}`).value])),
      verify_only: document.getElementById("brf-verify-only").checked,
      objective: { version: +document.getElementById("brf-obj").value },
      ...(br.grid ? { grid: br.grid } : {}),                       // carried through, never silently dropped
    };
    const r = await post("/api/brief", { name, brief: newBrief });
    if (r.error) msg.innerHTML = `<div class="alert error">${esc(r.error)}</div>`;
    else msg.innerHTML = `<div class="alert info">Saved to ${esc(r.path || name)}</div>`;
  };

  if (!isNew) {
    // Show families
    document.getElementById("btn-families").onclick = async () => {
      const pre = document.getElementById("families-out");
      pre.style.display = "block";
      pre.textContent = "Loading…";
      try {
        const r = await api("/api/families?brief=" + encodeURIComponent(b.name));
        pre.textContent = r.text || "(no output)";
      } catch (e) { pre.textContent = "Error: " + e.message; }
    };
  }

  if (opts.scroll) det.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── View 6: Launch ─────────────────────────────────────────────────

let _launchPollTimer = null;

async function viewLaunch() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let briefs = [], jobs = [], configs = [], statusData = null;
  try {
    [briefs, jobs, configs, statusData] = await Promise.all([
      api("/api/briefs"),
      api("/api/jobs"),
      api("/api/configs").catch(() => []),
      api("/api/status").catch(() => null),
    ]);
  } catch (e) { ROOT.innerHTML = errBanner(e.message); return; }
  const typs = await api("/api/typologies").catch(() => []);
  if (ROOT !== currentRoot()) return;   // the user navigated away while this loaded
  renderLaunch(briefs, jobs, configs, statusData, typs);
}

function renderLaunch(briefs, jobs, configs, statusData, typs = []) {
  const lock = (statusData || {}).gpu_lock;
  // Live: re-read from /api/status while the page is open (the server re-checks on every launch).
  let gpuBusy = !!(lock && lock.alive);
  const ROOT_LAUNCH = currentRoot();
  const busyNoteHtml = (lk) => (lk && lk.alive)
    ? `<div class="gpu-busy-note" role="status">
        ⚠ GPU busy: ${esc(lk.user || "")} running <em>${esc(lk.command || "")}</em> since ${esc(timeSince(lk.start_time))}.
        GPU actions disabled. Dry-run always available.
      </div>` : "";
  const busyNote = busyNoteHtml(lock);

  // verify_only briefs (12 kHz, P2) are for `verify --brief` only: the CLI refuses them for search/campaign
  const briefOpts = briefs.filter(b => !(b.brief && b.brief.verify_only)).map(b => `<option value="${esc(b.path)}" data-name="${esc(b.name)}">${esc(b.name)}${b.kind === "user" ? " (yours)" : ""}</option>`).join("");
  const pre = new URLSearchParams((location.hash.split("?")[1]) || "");

  // Build config select options grouped by catalog group
  const byGroup = {};
  for (const c of configs) {
    const g = c.group || "Other";
    if (!byGroup[g]) byGroup[g] = [];
    byGroup[g].push(c);
  }
  let configSelectOpts = `<option value="">— select a config —</option>`;
  for (const [grp, cfgs] of Object.entries(byGroup)) {
    configSelectOpts += `<optgroup label="${esc(grp)}">`;
    for (const c of cfgs) {
      const desc = c.description ? ` — ${c.description.slice(0, 60)}` : "";
      const disabled = c.disabled ? "disabled" : "";
      configSelectOpts += `<option value="${esc(c.path)}" ${disabled}>${esc(c.catalog_name || c.name)}${esc(desc)}${c.disabled ? " (disabled)" : ""}</option>`;
    }
    configSelectOpts += `</optgroup>`;
  }

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Launch jobs</div>
        <h2>Launch</h2>
        <div id="launch-busy">${busyNote}</div>
      </div>
      <div class="card stack" style="gap:16px">
        <h3>Job type</h3>
        <div class="btn-row" role="radiogroup" aria-label="job type">
          <button class="job-type-btn" data-type="campaign" aria-pressed="true">Campaign</button>
          <button class="job-type-btn" data-type="search" aria-pressed="false">Search</button>
          <button class="job-type-btn" data-type="dry-run" aria-pressed="false">Dry-run <span class="muted" style="font-size:0.75rem">(always available)</span></button>
        </div>

        <!-- Campaign form -->
        <div id="launch-form-campaign" class="launch-form stack" style="gap:12px">
          <div class="form-grid">
            <label for="lf-brief">Brief</label>
            <select id="lf-brief">${briefOpts}</select>

            <label for="lf-tier">${tip("tier", "Tier")}</label>
            <div>
              <select id="lf-tier">
                <option value="dry-run">dry-run — mesh only, seconds</option>
                <option value="screen" selected>screen — one search per family, minutes</option>
                <option value="compare">compare — two repeats, hours</option>
              </select>
              <div class="hint" id="tier-hint">One search per family; coarse first ranking.</div>
            </div>

            <span class="form-label">Families</span>
            <div>
              <div id="fam-picker" class="fam-picker" role="group" aria-label="Horn families"></div>
              <div class="hint" id="fam-summary"></div>
            </div>
          </div>
          <div class="alert warn" id="compare-warn" style="display:none" role="alert">
            ⚠ <b>Compare tier</b> takes hours. Never run during a live GPU session.
          </div>
        </div>

        <!-- Search form -->
        <div id="launch-form-search" class="launch-form stack" style="display:none;gap:12px" ${gpuBusy ? "aria-disabled='true'" : ""}>
          <div id="search-busy" class="alert warn" ${gpuBusy ? "" : "style='display:none'"}>GPU busy — search disabled while a job is running.</div>
          <div class="form-grid">
            <label for="lf-config">Config</label>
            <select id="lf-config">${configSelectOpts}</select>
            <label for="lf-budget">${tip("budget", "Budget")}</label>
            <div><input id="lf-budget" type="number" value="200" min="1">
              <div class="hint">Number of evaluations the search may run</div></div>
            <label for="lf-seed">${tip("cma_seed", "CMA seed")}</label>
            <div><input id="lf-seed" type="number" value="1234">
              <div class="hint">Change to get a different random search path</div></div>
            <label for="lf-sbrief">Brief</label>
            <select id="lf-sbrief"><option value="">— use config default —</option>${briefOpts}</select>
          </div>
        </div>

        <!-- Dry-run form -->
        <div id="launch-form-dry-run" class="launch-form stack" style="display:none;gap:12px">
          <div class="form-grid">
            <label for="lf-drconfig">Config</label>
            <select id="lf-drconfig">${configSelectOpts}</select>
          </div>
        </div>

        <!-- Command preview -->
        <div class="card" style="background:var(--bg)">
          <div class="eyebrow" style="margin-bottom:6px">Command preview</div>
          <code id="cmd-preview" style="white-space:pre-wrap;word-break:break-all;font-size:0.82rem">hornlab-search campaign …</code>
        </div>
        <div class="btn-row">
          <button id="btn-launch" class="primary" ${gpuBusy && true ? "" : ""}>Start</button>
        </div>
        <div id="launch-error"></div>
      </div>

      <!-- Job list -->
      <div>
        <div class="section-header">
          <h3>Jobs</h3>
          <button id="btn-refresh-jobs">↻ Refresh</button>
        </div>
        <div id="jobs-list" class="stack" style="gap:8px"></div>
      </div>
    </div>`;

  const TIER_HINTS = {
    "dry-run": "Meshes each starting design only — no solving. Takes seconds.",
    "screen": "One search per family, budget max(40, 10×parameters). Coarse ranking in minutes.",
    "compare": "Two repeats, budget max(150, 25×parameters). Needed to claim one family beats another. Hours.",
  };

  // Type toggle
  let currentType = "campaign";
  document.querySelectorAll(".job-type-btn").forEach(btn => {
    btn.onclick = () => {
      currentType = btn.dataset.type;
      document.querySelectorAll(".job-type-btn").forEach(b => b.setAttribute("aria-pressed", "false"));
      btn.setAttribute("aria-pressed", "true");
      document.querySelectorAll(".launch-form").forEach(f => f.style.display = "none");
      document.getElementById(`launch-form-${currentType}`).style.display = "grid";
      // Disable launch if GPU busy and not dry-run
      const launchBtn = document.getElementById("btn-launch");
      launchBtn.disabled = gpuBusy && currentType !== "dry-run";
      if (launchBtn.disabled) launchBtn.title = "GPU busy — only dry-run is available";
      else launchBtn.title = "";
      updatePreview();
    };
  });

  // Tier hint update
  const tierSel = document.getElementById("lf-tier");
  tierSel.addEventListener("change", () => {
    document.getElementById("tier-hint").textContent = TIER_HINTS[tierSel.value] || "";
    document.getElementById("compare-warn").style.display = tierSel.value === "compare" ? "" : "none";
    updatePreview();
  });

  // Family picker: grouped by kind, incompatible families disabled with the CLI's own reason
  const GROUP_LABEL = { classical: "Classical horns", hybrid: "Hybrids", organic: "Organic horns", magnus: "Magnus mesher families", legacy: "Utility / legacy" };
  const selected = new Set((pre.get("families") || "").split(",").filter(Boolean));
  if (pre.get("brief")) {
    const o = [...document.getElementById("lf-brief").options].find(x => x.dataset.name === pre.get("brief"));
    if (o) document.getElementById("lf-brief").value = o.value;
  }
  if (pre.get("tier")) document.getElementById("lf-tier").value = pre.get("tier");
  const briefName = () => document.getElementById("lf-brief").selectedOptions[0]?.dataset.name || "";
  function estMinutes(t, tier) {
    // slowest measured campaign for this family: replayed (cached) campaigns run far faster than fresh
    // ones, so the maximum is the honest upper estimate; ignore near-zero all-cached campaigns
    const ms = (t.results || []).map(x => x.s_per_eval).filter(v => v != null && v >= 0.5);
    if (!ms.length) return null;
    const n = tier === "compare" ? 2 * t.budget.compare : tier === "screen" ? t.budget.screen : 0;
    return n * Math.max(...ms) / 60;
  }
  function renderFamPicker() {
    const bn = briefName(), tier = document.getElementById("lf-tier").value;
    const groups = {};
    for (const t of typs) (groups[t.group] = groups[t.group] || []).push(t);
    const box = document.getElementById("fam-picker");
    box.innerHTML = Object.entries(groups).map(([g, list]) => `
      <fieldset class="fam-group"><legend>${esc(GROUP_LABEL[g] || g)}
        <button type="button" class="linkish" data-all="${esc(g)}">select all that fit</button></legend>
        ${list.map(t => {
          const c = (t.compat || {})[bn] || { ok: true };
          const off = !c.ok || t.disabled;
          const best = (t.results || []).find(r => r.brief === bn);
          const est = estMinutes(t, tier);
          return `<label class="fam-row ${off ? "off" : ""}" title="${esc(off ? (c.reason || "disabled") : (t.description || ""))}">
            <input type="checkbox" value="${esc(t.name)}" ${off ? "disabled" : ""} ${selected.has(t.name) && !off ? "checked" : ""}>
            <span class="fam-name">${esc(t.name)}</span>
            <span class="fam-meta">${esc(t.symmetry === "axisymmetric" ? "axisymmetric" : "H/V")} · ${t.n_knobs} params ·
              ${tier === "compare" ? "2 × " + t.budget.compare : tier === "screen" ? t.budget.screen : "–"} evals${est != null && tier !== "dry-run" ? ` · ≈ ${est < 90 ? Math.round(est) + " min" : (est / 60).toFixed(1) + " h"}` : ""}</span>
            <span class="fam-best">${off ? `<em>${esc(t.disabled ? "disabled" : "does not fit this brief")}</em>` : !best ? "not run on this brief" : best.no_valid ? `<em class="warn-text">no valid design here (${esc(best.tier)})</em>` : `${esc(best.tier)} #${best.rank}/${best.of} · score ${fmt(best.median_j)}`}</span>
          </label>`;
        }).join("")}
      </fieldset>`).join("");
    box.querySelectorAll("input[type=checkbox]").forEach(cb => cb.onchange = () => {
      cb.checked ? selected.add(cb.value) : selected.delete(cb.value); summary(); updatePreview();
    });
    box.querySelectorAll("[data-all]").forEach(b => b.onclick = () => {
      box.querySelectorAll(`fieldset input:not(:disabled)`).forEach(cb => {
        if (cb.closest("fieldset").querySelector("[data-all]") === b) { cb.checked = true; selected.add(cb.value); }
      });
      summary(); updatePreview();
    });
    // drop selections that no longer fit the brief
    for (const n of [...selected]) {
      const cb = box.querySelector(`input[value="${CSS.escape(n)}"]`);
      if (!cb || cb.disabled) selected.delete(n);
    }
    summary();
  }
  function summary() {
    const tier = document.getElementById("lf-tier").value;
    const chosen = typs.filter(t => selected.has(t.name));
    const evals = chosen.reduce((a, t) => a + (tier === "compare" ? 2 * t.budget.compare : tier === "screen" ? t.budget.screen : 0), 0);
    const mins = chosen.map(t => estMinutes(t, tier));
    const known = mins.filter(m => m != null);
    document.getElementById("fam-summary").textContent = !chosen.length
      ? "Nothing selected = every family that fits the brief."
      : `${chosen.length} selected · ${evals.toLocaleString()} evaluations` +
        (tier !== "dry-run" && known.length ? ` · ≈ ${Math.round(known.reduce((a, b) => a + b, 0))} min measured on this machine` +
         (known.length < chosen.length ? ` (+ ${chosen.length - known.length} never timed)` : "") : "");
  }
  const famArg = () => [...selected].join(",");

  // Command preview: asked from the server, which builds the exact argv a launch would run
  let _pv = null;
  function currentJob() {
    if (currentType === "campaign")
      return { kind: "campaign", args: { brief: document.getElementById("lf-brief").value, families: famArg(),
                                         tier: document.getElementById("lf-tier").value } };
    if (currentType === "search")
      return { kind: "search", args: { config: document.getElementById("lf-config").value,
                                       budget: +document.getElementById("lf-budget").value,
                                       cma_seed: document.getElementById("lf-seed").value,
                                       brief: document.getElementById("lf-sbrief").value || undefined } };
    return { kind: "dry-run", args: { config: document.getElementById("lf-drconfig").value } };
  }
  function updatePreview() {
    clearTimeout(_pv);
    _pv = setTimeout(async () => {
      const out = document.getElementById("cmd-preview");
      if (!out) return;
      const r = await post("/api/preview", currentJob());
      out.textContent = r.error ? "— " + r.error : r.command;
      out.classList.toggle("muted", !!r.error);
    }, 150);
  }

  // Wire inputs to preview
  ["lf-brief", "lf-config", "lf-budget", "lf-seed", "lf-sbrief", "lf-drconfig"].forEach(id => {
    const el2 = document.getElementById(id);
    if (el2) el2.addEventListener("input", updatePreview);
    if (el2) el2.addEventListener("change", updatePreview);
  });
  document.getElementById("lf-brief").addEventListener("change", renderFamPicker);
  document.getElementById("lf-tier").addEventListener("change", renderFamPicker);
  renderFamPicker();
  updatePreview();

  // Initial launch button state
  document.getElementById("btn-launch").disabled = false; // campaign is default, no GPU gate for dry-run tier

  // Launch
  document.getElementById("btn-launch").onclick = async () => {
    const errEl = document.getElementById("launch-error");
    errEl.innerHTML = "";
    let kind, args;
    if (currentType === "campaign") {
      const tier = document.getElementById("lf-tier").value;
      if (gpuBusy && tier !== "dry-run") {
        errEl.innerHTML = `<div class="alert error">GPU is busy. Only dry-run tier is available while a job is running.</div>`;
        return;
      }
      if (tier === "compare" && !confirm("Compare tier takes hours. Run it now?")) return;
      ({ kind, args } = currentJob());
    } else if (currentType === "search") {
      if (gpuBusy) { errEl.innerHTML = `<div class="alert error">GPU is busy. Wait for the current job to finish.</div>`; return; }
      ({ kind, args } = currentJob());
    } else {
      ({ kind, args } = currentJob());
    }
    const r = await post("/api/jobs", { kind, args });
    if (r.error) {
      errEl.innerHTML = `<div class="alert error" role="alert"><b>Error:</b> ${esc(r.error)}</div>`;
    } else {
      errEl.innerHTML = `<div class="alert info">Job started: ${esc(r.id)}</div>`;
      refreshJobs();
    }
  };

  renderJobs(jobs);

  document.getElementById("btn-refresh-jobs").onclick = refreshJobs;

  // Poll running jobs every 2s
  clearInterval(_launchPollTimer);
  let tick = 0;
  _launchPollTimer = setInterval(async () => {
    if (!location.hash.startsWith("#/launch")) { clearInterval(_launchPollTimer); _launchPollTimer = null; return; }
    refreshJobs();
    if (++tick % 3) return;                               // GPU state every ~6 s
    const st = await api("/api/status").catch(() => null);
    if (!st || ROOT_LAUNCH !== currentRoot()) return;
    const lk = st.gpu_lock, busy = !!(lk && lk.alive);
    if (busy === gpuBusy) return;
    gpuBusy = busy;
    const nb = document.getElementById("launch-busy");
    if (nb) nb.innerHTML = busyNoteHtml(lk);
    const sb = document.getElementById("search-busy");
    if (sb) sb.style.display = busy ? "" : "none";
    const lb = document.getElementById("btn-launch");
    if (lb) { lb.disabled = busy && currentType === "search"; lb.title = lb.disabled ? "GPU busy — only dry-run is available" : ""; }
    showToast(busy ? "GPU is now busy: GPU actions disabled" : "GPU is free: GPU actions available", busy ? "info" : "good");
  }, 2000);
}

async function refreshJobs() {
  let jobs;
  try { jobs = await api("/api/jobs"); } catch { return; }
  renderJobs(jobs);
}

function renderJobs(jobs) {
  const el2 = document.getElementById("jobs-list");
  if (!el2) return;
  if (!jobs.length) { el2.innerHTML = `<p class="muted">No jobs yet.</p>`; return; }

  el2.innerHTML = jobs.slice().reverse().map(j => {
    const sc = `job-status-${j.status || "done"}`;
    const dur = j.started && j.ended
      ? " · " + ((new Date(j.ended) - new Date(j.started)) / 60000).toFixed(1) + "m"
      : j.status === "running" ? " · running…" : "";

    const logLines = (j.log_tail || []).join("\n");
    const cancelBtn = j.status === "running"
      ? `<button class="btn danger cancel-job-btn" data-job-id="${esc(j.id)}">Cancel</button>` : "";

    // Try to extract run ID from log
    let runLink = "";
    if (j.log_tail) {
      const logText = j.log_tail.join(" ");
      const rm = logText.match(/runs[/\\]([0-9]{8}T[0-9]{6}Z-[a-z]+-[0-9a-f]{6})/);
      if (rm) runLink = `<a class="btn" href="#/run/${esc(rm[1])}" style="font-size:0.8rem">Open run →</a>`;
    }

    return `<div class="job-row">
      <div class="job-head">
        <div>
          <span class="job-title">${esc(j.kind || "")} · <span class="mono">${esc(j.id || "")}</span></span>
          <span class="${sc}"> ${esc(j.status || "")}${esc(dur)}</span>
        </div>
        <div class="btn-row" style="gap:6px">${cancelBtn}${runLink}</div>
      </div>
      <div class="mono muted" style="font-size:0.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc((j.command || j.argv || []).join?.(" ") || j.command || "")}</div>
      ${logLines ? `<div class="log-tail" style="max-height:100px">${esc(logLines)}</div>` : ""}
    </div>`;
  }).join("");

  // Attach cancel event via delegation (avoids XSS risk from inline onclick)
  el2.querySelectorAll(".cancel-job-btn").forEach(btn => {
    btn.onclick = async () => {
      if (!confirm("Cancel this job?")) return;
      const r = await post("/api/job/" + btn.dataset.jobId + "/cancel", {});
      if (r.error) showToast(r.error, "error");
      refreshJobs();
    };
  });
}

// ── View G: Glossary ───────────────────────────────────────────────

function viewGlossary() {
  const ROOT = currentRoot();     // this view's own container (see route())
  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Reference</div>
        <h2>Glossary</h2>
        <p class="muted" style="font-size:0.85rem">Plain-language meaning of every number the GUI shows. Hover any underlined term in the app to see a tooltip.</p>
      </div>
      <div class="glossary-list">
        ${Object.entries(GLOSSARY).map(([key, t]) => `
          <div class="glossary-entry">
            <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap">
              <span class="g-key">${esc(key)}</span>
              <span class="g-label">${esc(t.label)}</span>
              ${t.unit ? `<span class="g-unit">[${esc(t.unit)}]</span>` : ""}
            </div>
            <div class="g-long">${esc(t.long)}</div>
          </div>
        `).join("")}
      </div>
    </div>`;
}

// ── Init ───────────────────────────────────────────────────────────

route();

// Redraw charts on theme change. route() replaces #view-root, so snapshot scroll and
// filter/form state, re-render, then restore once the async view has settled. The one
// requestAnimationFrame retry catches views that render in stages (wallSection cards).
function snapshotViewState() {
  const snap = { y: window.scrollY, fields: [] };
  document.querySelectorAll(".filter-bar input, .form-grid input, .form-grid select, textarea")
    .forEach(el => snap.fields.push([el, el.value]));
  return snap;
}

function restoreViewState(snap) {
  if (!snap) return;
  window.scrollTo(0, snap.y);
  snap.fields.forEach(([el, v]) => {
    if (el.isConnected && el.value !== v) el.value = v;
  });
}

async function routeAndRestore() {
  const snap = snapshotViewState();
  await route();
  restoreViewState(snap);
  requestAnimationFrame(() => restoreViewState(snap));
}

matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", () => {
  // A pinned preference (explicit data-theme) wins; re-rendering here is pure waste.
  if (document.documentElement.hasAttribute("data-theme")) return;
  routeAndRestore();
});
new MutationObserver(() => { routeAndRestore(); })
  .observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

// ── Keyboard access for clickable table rows (rows use onclick for navigation) ──────────────────
new MutationObserver(() => {
  document.querySelectorAll("tr.clickable:not([tabindex]), tr[onclick]:not([tabindex])")
    .forEach(tr => { tr.tabIndex = 0; tr.setAttribute("role", "link"); });
}).observe(document.body, { childList: true, subtree: true });
document.addEventListener("keydown", e => {
  const tr = e.target.closest && e.target.closest("tr[role=link]");
  if (tr && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); tr.click(); }
});

// ── Charts are drawn 1:1 at their measured width: re-render the view after a real width change ──
let _lastW = window.innerWidth, _rsz = null;
window.addEventListener("resize", () => {
  clearTimeout(_rsz);
  _rsz = setTimeout(() => {
    if (Math.abs(window.innerWidth - _lastW) < 40 || !document.querySelector("svg[data-chart]")) return;
    _lastW = window.innerWidth;
    const y = window.scrollY; route(); setTimeout(() => window.scrollTo(0, y), 600);
  }, 350);
});


// ── View: Typologies (every classical horn, hybrid and mesher family) ─────────────────────────────
const TYP_GROUP = {
  classical: ["Classical horns", "Textbook profiles (conical, exponential, hyperbolic-exponential, tractrix, OS) built from their formulas and handed to Magnus's FREEFORM mesher as exact wall anchors."],
  hybrid: ["Hybrids", "Combinations: a different profile in each plane (H/V), a convex blend of two profiles, or small monotone perturbations of a classical wall."],
  magnus: ["Magnus mesher families", "OSSE, R-OSSE, ICW and FREEFORM as Magnus's mesher defines them."],
  legacy: ["Utility / legacy", "Test and adapter configs, not meant for typology comparison."],
};

async function viewTypologies() {
  const ROOT = currentRoot();     // this view's own container (see route())
  skel();
  let typs, briefs;
  try { [typs, briefs] = await Promise.all([api("/api/typologies"), api("/api/briefs")]); }
  catch (e) { ROOT.innerHTML = errBanner("Could not load typologies: " + e.message); return; }
  const groups = {};
  for (const t of typs) (groups[t.group] = groups[t.group] || []).push(t);
  ROOT.innerHTML = `<div class="stack" style="gap:26px">
    <div>
      <div class="eyebrow">Horn families</div>
      <h2>Typologies</h2>
      <p class="muted prose">Every family the search can run. Pick one or more to screen against a brief; a family that cannot meet a brief (an axisymmetric horn on a 90 × 60° brief) is greyed out there. Results are the latest campaign of each tier per brief; the outline is that family's best design so far. Le Cléac'h is disabled until a verifiable published construction is available.</p>
    </div>
    ${Object.entries(groups).map(([g, list]) => `
      <section class="stack" style="gap:12px">
        <div><h3>${esc((TYP_GROUP[g] || [g])[0])}</h3><p class="muted" style="margin:2px 0 0">${esc((TYP_GROUP[g] || ["", ""])[1])}</p></div>
        <div class="typ-grid">${list.map(t => typCard(t, briefs)).join("")}</div>
      </section>`).join("")}
  </div>`;
  requestAnimationFrame(() => {
    ROOT.querySelectorAll("svg.typ-prof").forEach(sv => {
      const t = typs.find(x => x.name === sv.dataset.name);
      const r = (t.results || []).find(x => x.profile);
      if (r) wallSection(sv, [{ profile: r.profile, color: css("--best"), filled: true }], { H: 120, compact: true });
    });
  });
}

function typCard(t, briefs) {
  const res = (t.results || []).map(r => r.no_valid
    ? `<tr><td>${esc(r.brief)}</td><td>${esc(r.tier)}</td><td colspan="3" class="warn-text">no valid design under this brief (starting design outside its size envelope)</td></tr>`
    : `<tr>
      <td>${esc(r.brief)}</td><td>${esc(r.tier)}</td>
      <td class="r">${r.rank}/${r.of}</td>
      <td class="r">${r.best_run_id ? `<a href="#/run/${esc(r.best_run_id)}" title="open the best run">${fmt(r.median_j)}</a>` : fmt(r.median_j)}</td>
      <td class="r">${r.dims ? esc(Math.round(r.dims.mouth_w_mm) + "×" + Math.round(r.dims.mouth_h_mm) + "×" + Math.round(r.dims.depth_mm)) : "–"}</td></tr>`).join("");
  const fits = briefs.map(b => {
    const c = (t.compat || {})[b.name] || { ok: true };
    return c.ok && !t.disabled
      ? `<a class="pill good" href="#/launch?brief=${encodeURIComponent(b.name)}&families=${encodeURIComponent(t.name)}&tier=screen" title="Screen ${esc(t.name)} on ${esc(b.name)}">▶ ${esc(b.name)}</a>`
      : `<span class="pill" title="${esc(c.reason || "disabled")}" style="opacity:0.55">${esc(b.name)}</span>`;
  }).join(" ");
  const hasProf = (t.results || []).some(r => r.profile);
  return `<article class="card typ-card">
    <div class="typ-head">
      <div><div class="typ-name">${esc(t.name)}</div>
        <div class="muted typ-meta">${esc(t.symmetry === "axisymmetric" ? "axisymmetric" : "H/V (different planes)")} · ${t.n_knobs} shape parameters · screen ${t.budget.screen} / compare 2 × ${t.budget.compare} evals</div></div>
      ${hasProf ? `<svg class="typ-prof" data-name="${esc(t.name)}" aria-label="best design cross-section"></svg>` : `<div class="typ-prof empty muted">no solved design yet</div>`}
    </div>
    <p class="typ-desc">${esc(t.description || "")}</p>
    ${res ? `<div class="tbl-wrap"><table class="compact"><thead><tr><th>Brief</th><th>Tier</th><th class="r">Rank</th><th class="r">Score</th><th class="r">W×H×D mm</th></tr></thead><tbody>${res}</tbody></table></div>`
          : `<p class="muted" style="margin:0">Not run in any campaign yet.</p>`}
    <div class="typ-fits"><span class="muted">Screen on:</span> ${fits}</div>
  </article>`;
}
