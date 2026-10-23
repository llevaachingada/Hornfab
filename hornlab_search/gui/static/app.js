// app.js — hornlab-search GUI   AGPL-3.0-or-later
// Single-page app with hash routing. Views 1–7. No build step, vanilla ES modules.
// Import helpers from charts.js; 3D viewer from view3d.js.

import { chart, heat, cmap, drawCbar, niceTicks, diFromCuts, groupColor,
         el, NS, css, fmt, FT, TERMS, DEFW } from "./charts.js";
import { init3d } from "./view3d.js";

// ── API helpers ────────────────────────────────────────────────────

async function api(path) {
  const r = await fetch(path);
  if (!r.ok) { const t = await r.text().catch(()=>""); throw new Error(`${r.status} ${t}`); }
  return r.json();
}

async function post(path, body) {
  const r = await fetch(path, { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body) });
  const j = await r.json().catch(()=>({ error: "invalid response" }));
  return j;
}

// ── Routing ────────────────────────────────────────────────────────

const ROOT = document.getElementById("view-root");

const ROUTES = [
  { re: /^#\/status$/,               fn: viewStatus },
  { re: /^#\/campaigns$/,            fn: viewCampaignsList },
  { re: /^#\/campaign\/(.+)$/,       fn: (m)=>viewCampaignDetail(m[1]) },
  { re: /^#\/runs$/,                 fn: viewRunsList },
  { re: /^#\/run\/(.+)\/3d$/,        fn: (m)=>viewRun3D(m[1]) },
  { re: /^#\/run\/(.+)$/,            fn: (m)=>viewRunDetail(m[1]) },
  { re: /^#\/compare$/,              fn: viewCompare },
  { re: /^#\/briefs$/,               fn: viewBriefs },
  { re: /^#\/launch$/,               fn: viewLaunch },
];

function route() {
  // Dispose any 3D scene
  const old = document.getElementById("view3d-wrap");
  if (old?._dispose3d) old._dispose3d();

  const hash = location.hash || "#/status";
  const path = hash.split("?")[0];            // views read their own ?query from location.hash
  for (const { re, fn } of ROUTES) {
    const m = path.match(re);
    if (m) { fn(m); updateNav(path); return; }
  }
  ROOT.innerHTML = "";
  const p = document.createElement("p"); p.className = "muted";
  p.textContent = "Unknown view: " + hash;    // textContent: never inject the URL as HTML
  ROOT.appendChild(p);
}

function updateNav(hash) {
  document.querySelectorAll("#app-nav a").forEach(a => {
    const h = a.getAttribute("href");
    a.classList.toggle("active", hash.startsWith(h) && h !== "#/");
  });
  // Special: runs & run detail
  const runsLink = document.querySelector("#app-nav a[href='#/runs']");
  if (runsLink) runsLink.classList.toggle("active", hash.startsWith("#/run") || hash.startsWith("#/runs"));
  const campLink = document.querySelector("#app-nav a[href='#/campaigns']");
  if (campLink) campLink.classList.toggle("active", hash.startsWith("#/campaign"));
  const statusLink = document.querySelector("#app-nav a[href='#/status']");
  if (statusLink) statusLink.classList.toggle("active", hash === "#/status" || hash === "#/");
}

window.addEventListener("hashchange", route);

// ── Shared helpers ─────────────────────────────────────────────────

function loading(msg="Loading…") {
  ROOT.innerHTML = `<p class="muted">${msg}</p>`;
}

function errBanner(msg) {
  return `<div class="alert error" role="alert">${msg}</div>`;
}

function pill(text, cls) {
  return `<span class="pill ${cls}">${text}</span>`;
}

function timeSince(iso) {
  if (!iso) return "–";
  const s = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  if (s < 86400) return `${Math.floor(s/3600)}h ago`;
  return `${Math.floor(s/86400)}d ago`;
}

function failurePills(obj) {
  return Object.entries(obj || {}).map(([k,v]) => `<span class="pill bad">${v}× ${k.replace(/_/g," ")}</span>`).join(" ") || pill("none","good");
}

// ── View 1: Status ─────────────────────────────────────────────────

let _statusTimer = null;

async function viewStatus() {
  loading("Loading status…");
  let data;
  try { data = await api("/api/status"); }
  catch(e) { ROOT.innerHTML = errBanner("Could not load status: " + e.message); return; }
  renderStatus(data);
}

function renderStatus(data) {
  const lock = data.gpu_lock;
  const disk = data.disk || {};
  const ql = data.queue_log || {};
  const wl = data.watchdog_log || [];
  const tail = (ql.tail || []).join("\n");

  let lockCard = "";
  if (lock) {
    const ago = timeSince(lock.start_time);
    const alivePill = lock.alive ? pill("alive","good") : pill("stale","warn");
    lockCard = `
      <div class="status-card gpu-lock-card" aria-label="GPU lock">
        <div class="label">GPU lock</div>
        <div class="value">${lock.user || "–"}</div>
        <div class="sub" title="${lock.command}">${lock.command || "–"}</div>
        <div class="sub">PID ${lock.pid} · started ${ago} ${alivePill}</div>
      </div>`;
  } else {
    lockCard = `<div class="status-card" aria-label="GPU lock">
      <div class="label">GPU lock</div>
      <div class="value good-text">Free</div>
    </div>`;
  }

  const vramPct = data.vram_mib ? "" : "";
  const diskPct = disk.total_gb ? (100 - disk.free_gb / disk.total_gb * 100).toFixed(0) : 0;

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">System</div>
        <h2>Status</h2>
      </div>
      <div class="status-grid">
        ${lockCard}
        <div class="status-card">
          <div class="label">VRAM used</div>
          <div class="value num">${data.vram_mib != null ? data.vram_mib.toFixed(0) : "–"} <small style="font-size:1rem">MiB</small></div>
        </div>
        <div class="status-card">
          <div class="label">Julia procs</div>
          <div class="value num">${data.julia_procs ?? "–"}</div>
        </div>
        <div class="status-card">
          <div class="label">Disk free</div>
          <div class="value num">${disk.free_gb != null ? disk.free_gb.toFixed(1) : "–"} <small style="font-size:1rem">GB</small></div>
          <div class="sub">${disk.total_gb != null ? disk.total_gb.toFixed(0) + " GB total · " + diskPct + "% used" : ""}</div>
        </div>
      </div>
      <div class="btn-row">
        <button id="btn-refresh">↻ Refresh</button>
        <button id="btn-gpuclean" class="danger" ${lock && lock.alive ? "disabled title='A live job holds the lock'" : ""}>gpu-clean</button>
      </div>
      <div class="stack" style="gap:8px">
        <div class="eyebrow">Queue log — ${ql.name || ""}</div>
        <div class="log-tail" id="queue-tail" aria-label="queue log">${escHtml(tail)}</div>
      </div>
      <div class="stack" style="gap:8px">
        <div class="eyebrow">Watchdog log</div>
        <div class="log-tail" aria-label="watchdog log">${escHtml((wl).join("\n"))}</div>
      </div>
    </div>`;

  document.getElementById("btn-refresh").onclick = () => viewStatus();
  document.getElementById("btn-gpuclean").onclick = async () => {
    if (!confirm("Run gpu-clean? This kills stale Julia/BEAT processes.")) return;
    const r = await post("/api/gpu-clean", {});
    if (r.error) alert("Error: " + r.error);
    else alert("gpu-clean: " + (r.text || "done"));
    viewStatus();
  };

  // Auto-refresh every 10s
  clearInterval(_statusTimer);
  _statusTimer = setInterval(() => {
    if (location.hash === "#/status" || !location.hash) viewStatus();
    else clearInterval(_statusTimer);
  }, 10000);
}

function escHtml(s) {
  return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// ── View 2: Campaigns list ─────────────────────────────────────────

async function viewCampaignsList() {
  loading();
  let camps;
  try { camps = await api("/api/campaigns"); }
  catch(e) { ROOT.innerHTML = errBanner(e.message); return; }

  if (!camps.length) { ROOT.innerHTML = "<p class='muted'>No campaigns found.</p>"; return; }

  let rows = camps.map(c => `<tr class="clickable-row" onclick="location.hash='#/campaign/${c.id}'">
    <td><b>${c.id}</b></td>
    <td>${c.tier}</td>
    <td>${c.brief || "–"}</td>
    <td class="r">${c.n_entries}</td>
    <td class="r">${(c.seeds||[]).join(", ")}</td>
    <td>${(c.families||[]).join(", ")}</td>
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

async function viewCampaignDetail(id) {
  loading();
  let camp;
  try { camp = await api("/api/campaign/" + id); }
  catch(e) { ROOT.innerHTML = errBanner(e.message); return; }

  const entries = camp.entries || [];

  // Compute common scale for wall profiles
  let allR = [], allZ = [];
  entries.forEach(e => {
    const p = (e.best || {}).profile || {};
    [["h",1],["v",-1]].forEach(([k,sgn]) => {
      (p[k]||[]).forEach(pt => { allR.push(Math.abs(pt[1])); allZ.push(pt[0]); });
    });
  });
  const sharedRmax = allR.length ? Math.max(...allR)*1.1 : 200;
  const sharedZmin = allZ.length ? Math.min(...allZ)-5 : 0;
  const sharedZmax = allZ.length ? Math.max(...allZ)+5 : 220;

  // Leaderboard rows
  let lbRows = entries.map((e,i) => {
    const gc = groupColor(e.group||"");
    const gpill = `<span class="pill" style="border-color:${gc};color:${gc}">${e.group||"–"}</span>`;
    const pinnedPills = (e.pinned||[]).map(k=>`<span class="pill bad">${k}</span>`).join(" ") || "";
    const failStr = Object.entries(e.failures||{}).map(([k,v])=>`${v}×${k.replace(/_/g," ")}`).join(" ") || "–";
    const seedLinks = (e.jobs||[]).map(j=>j.run_id
      ? `<a href="#/run/${j.run_id}">s${j.seed}</a>` : `s${j.seed}`).join(" ");
    return `<tr>
      <td class="r mono">${i+1}</td>
      <td><b>${e.name}</b></td>
      <td>${gpill}</td>
      <td>${e.symmetry||"–"}</td>
      <td class="r">${fmt(e.best_j)}</td>
      <td class="r">${fmt(e.median_j)}</td>
      <td class="r">${fmt(e.spread)}</td>
      <td class="r">${e.evals||"–"}</td>
      <td style="font-size:0.8em;color:var(--muted)">${failStr}</td>
      <td>${pinnedPills}</td>
      <td>${seedLinks}</td>
    </tr>`;
  }).join("");

  // Separation note
  let separationNote = "";
  for (let i = 0; i < entries.length - 1; i++) {
    const a = entries[i], b = entries[i+1];
    if (a.median_j != null && b.median_j != null) {
      const diff = b.median_j - a.median_j;
      const threshold = Math.max(a.spread||0, b.spread||0);
      if (diff <= threshold) {
        separationNote += `<p class="muted" style="font-size:0.83rem">Ranks ${i+1}–${i+2} (${a.name} vs ${b.name}): medians differ by ${fmt(diff,3)}, spreads ${fmt(a.spread,3)} / ${fmt(b.spread,3)} — not separated.</p>`;
      }
    }
  }

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Campaign · ${camp.tier}</div>
        <h2>${camp.id}</h2>
        <p class="muted">Brief: ${camp.brief||"–"} · Seeds: ${(camp.seeds||[]).join(", ")}</p>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead><tr>
            <th class="r">#</th><th>Name</th><th>Group</th><th>Sym</th>
            <th class="r">Best J</th><th class="r">Median J</th><th class="r">Spread</th>
            <th class="r">Evals</th><th>Failures</th><th>Pinned</th><th>Seeds</th>
          </tr></thead>
          <tbody>${lbRows}</tbody>
        </table>
      </div>
      ${separationNote}
      <div>
        <h3 style="margin-bottom:10px">Wall profiles — best design per family</h3>
        <p class="muted" style="font-size:0.82rem">H right (positive r), V mirrored left. Shared mm scale.</p>
        <div class="camp-grid" id="wall-profiles"></div>
      </div>
      <div>
        <h3 style="margin-bottom:8px">Beamwidth vs target — all families</h3>
        <div class="toggle-row" id="bw-toggle" style="margin-bottom:8px">
          <button aria-pressed="true" id="btn-bw-h">Horizontal</button>
          <button aria-pressed="false" id="btn-bw-v">Vertical</button>
        </div>
        <div class="fig">
          <svg id="bw-chart" style="min-height:160px"></svg>
          <div class="legend" id="bw-legend"></div>
        </div>
      </div>
    </div>`;

  // Wall profiles
  const profGrid = document.getElementById("wall-profiles");
  entries.forEach(e => {
    const cell = document.createElement("div"); cell.className = "camp-prof";
    const h4 = document.createElement("h4"); h4.textContent = e.name; cell.appendChild(h4);
    const gc = groupColor(e.group||"");
    const W=150, H=110, m={l:28,r:4,t:4,b:22};
    const svgEl = document.createElementNS(NS,"svg");
    svgEl.setAttribute("viewBox",`0 0 ${W} ${H}`);
    const Xp = v => m.l + (v + sharedRmax)/(2*sharedRmax)*(W-m.l-m.r);
    const Yp = v => H - m.b - (v - sharedZmin)/(sharedZmax-sharedZmin)*(H-m.t-m.b);
    const gg = document.createElementNS(NS,"g"); gg.setAttribute("class","grid");
    niceTicks(sharedZmin,sharedZmax,4).forEach(t => {
      const ln=document.createElementNS(NS,"line");
      ln.setAttribute("x1",m.l); ln.setAttribute("x2",W-m.r);
      ln.setAttribute("y1",Yp(t)); ln.setAttribute("y2",Yp(t));
      gg.appendChild(ln);
      const tx=document.createElementNS(NS,"text");
      tx.setAttribute("x",m.l-3); tx.setAttribute("y",Yp(t)+3); tx.setAttribute("text-anchor","end");
      tx.setAttribute("style","font-size:8px"); tx.textContent=Math.round(t);
      svgEl.appendChild(tx);
    });
    svgEl.appendChild(gg);
    const cl=document.createElementNS(NS,"line");
    cl.setAttribute("x1",Xp(0)); cl.setAttribute("x2",Xp(0));
    cl.setAttribute("y1",m.t); cl.setAttribute("y2",H-m.b);
    cl.setAttribute("stroke","var(--rule)"); svgEl.appendChild(cl);
    const prof = (e.best||{}).profile||{};
    [["h",1],["v",-1]].forEach(([k,sgn]) => {
      const pts = (prof[k]||[]).map(pt => [Xp(sgn*Math.abs(pt[1])), Yp(pt[0])]).filter(p=>isFinite(p[0])&&isFinite(p[1]));
      if (pts.length>1) {
        const path=document.createElementNS(NS,"path");
        path.setAttribute("d",pts.map((p,i)=>(i?"L":"M")+p[0].toFixed(1)+","+p[1].toFixed(1)).join(""));
        path.setAttribute("fill","none"); path.setAttribute("stroke",gc); path.setAttribute("stroke-width","1.4");
        if(k==="v") path.setAttribute("stroke-dasharray","3 2");
        svgEl.appendChild(path);
      }
    });
    const xl=document.createElementNS(NS,"text");
    xl.setAttribute("x",W/2); xl.setAttribute("y",H-4); xl.setAttribute("text-anchor","middle");
    xl.setAttribute("style","font-size:8px"); xl.textContent="← V · r mm · H →";
    svgEl.appendChild(xl);
    cell.appendChild(svgEl);
    cell.innerHTML += `<div><span class="pill" style="border-color:${gc};color:${gc};font-size:0.62rem">${e.group||""}</span></div>`;
    profGrid.appendChild(cell);
  });

  // BW chart
  const target = (entries[0]||{}).target || {};
  let bwPlane = "h";
  function drawBW() {
    const bwSvg = document.getElementById("bw-chart");
    const legDiv = document.getElementById("bw-legend");
    if (!bwSvg) return;
    const freqsRef = (entries.find(e=>e.best&&e.best.freqs)||{best:{freqs:[]}}).best.freqs||[];
    if (!freqsRef.length) { bwSvg.innerHTML="<text x='10' y='20'>No frequency data</text>"; return; }
    const tgt = bwPlane==="h" ? (target.coverage_h_deg||90) : (target.coverage_v_deg||90);
    const allBW = [];
    entries.forEach(e => {
      const b = e.best||{}, arr = bwPlane==="h" ? (b.bw_h||[]) : (b.bw_v||[]);
      arr.forEach(v => { if(v!=null) allBW.push(v); });
    });
    allBW.push(tgt);
    const bwmax = Math.min(200, Math.max(...allBW)*1.05) || 180;
    const series = entries.map(e => {
      const b=e.best||{}, F2=b.freqs||freqsRef;
      const arr=bwPlane==="h"?(b.bw_h||[]):(b.bw_v||[]);
      return { pts:F2.map((f,i)=>[f,arr[i]??null]), color:groupColor(e.group||""), w:1.6 };
    });
    chart(bwSvg, {
      W:600, H:220, xlog:true, xlim:[freqsRef[0],freqsRef[freqsRef.length-1]],
      ylim:[0,bwmax], xticks:FT, yticks:niceTicks(0,bwmax,5),
      xlabel:"Hz", ylabel:"deg",
      band:[target.band_lo_hz||700, target.band_hi_hz||5500],
      hlines:[{y:tgt, color:css("--muted"), dash:true}],
      series
    });
    legDiv.innerHTML = entries.map(e => {
      const gc=groupColor(e.group||"");
      return `<span><i style="color:${gc};border-top-color:${gc}"></i>${e.name}</span>`;
    }).join("");
  }
  drawBW();
  document.getElementById("btn-bw-h").onclick = () => {
    bwPlane="h";
    document.getElementById("btn-bw-h").setAttribute("aria-pressed","true");
    document.getElementById("btn-bw-v").setAttribute("aria-pressed","false");
    drawBW();
  };
  document.getElementById("btn-bw-v").onclick = () => {
    bwPlane="v";
    document.getElementById("btn-bw-h").setAttribute("aria-pressed","false");
    document.getElementById("btn-bw-v").setAttribute("aria-pressed","true");
    drawBW();
  };
}

// ── View 3: Runs list ──────────────────────────────────────────────

async function viewRunsList() {
  loading();
  let runs;
  try { runs = await api("/api/runs"); }
  catch(e) { ROOT.innerHTML = errBanner(e.message); return; }

  renderRunsList(runs);
}

function renderRunsList(allRuns) {
  ROOT.innerHTML = `
    <div class="stack" style="gap:20px">
      <div>
        <div class="eyebrow">All runs</div>
        <h2>Runs</h2>
      </div>
      <div class="filter-bar">
        <input id="run-filter" type="search" placeholder="Filter by name / family / brief…" aria-label="filter runs">
        <select id="run-sort" class="sort-sel" aria-label="sort runs">
          <option value="date">Newest first</option>
          <option value="best_j">Best J (asc)</option>
          <option value="name">Name</option>
        </select>
      </div>
      <div class="tbl-wrap">
        <table id="runs-table">
          <thead><tr>
            <th>Name</th><th>Family</th><th>Brief</th><th>Mode</th>
            <th class="r">Evals</th><th class="r">Fail</th>
            <th class="r">Seed J</th><th class="r">Best J</th><th class="r">Change</th>
            <th>Started</th>
          </tr></thead>
          <tbody id="runs-tbody"></tbody>
        </table>
      </div>
    </div>`;

  function render(runs) {
    const q = document.getElementById("run-filter").value.toLowerCase();
    const sort = document.getElementById("run-sort").value;
    let filtered = runs.filter(r =>
      (r.name||"").toLowerCase().includes(q) ||
      (r.family||"").toLowerCase().includes(q) ||
      (r.brief||"").toLowerCase().includes(q)
    );
    if (sort==="best_j") filtered.sort((a,b) => (a.best_j??999)-(b.best_j??999));
    else if (sort==="name") filtered.sort((a,b)=>(a.name||"").localeCompare(b.name||""));
    else filtered.sort((a,b)=>(b.started||"").localeCompare(a.started||""));

    const tbody = document.getElementById("runs-tbody");
    tbody.innerHTML = filtered.map(r => {
      const nf = r.n - r.n_ok;
      const ch = (r.best_j!=null && r.seed_j && r.seed_j<900)
        ? ((r.best_j/r.seed_j-1)*100).toFixed(1)+"%" : "–";
      return `<tr class="clickable-row" onclick="location.hash='#/run/${r.id}'">
        <td><b>${r.name}</b><br><span class="mono muted" style="font-size:0.75rem">${r.id}</span></td>
        <td>${r.family||"–"}</td>
        <td>${r.brief||"–"}</td>
        <td>${r.mode||"–"}</td>
        <td class="r">${r.n}</td>
        <td class="r">${nf>0?`<span class="warn-text">${nf}</span>`:nf}</td>
        <td class="r">${r.seed_j!=null&&r.seed_j<900 ? fmt(r.seed_j) : "–"}</td>
        <td class="r"><b>${fmt(r.best_j)}</b></td>
        <td class="r">${ch}</td>
        <td class="muted mono" style="font-size:0.78rem">${timeSince(r.started)}</td>
      </tr>`;
    }).join("") || `<tr><td colspan="10" class="muted" style="text-align:center">No matching runs</td></tr>`;
  }

  render(allRuns);
  document.getElementById("run-filter").addEventListener("input", () => render(allRuns));
  document.getElementById("run-sort").addEventListener("change", () => render(allRuns));
}

// ── View 3 detail: Run detail ──────────────────────────────────────

async function viewRunDetail(id) {
  loading();
  let d;
  try { d = await api("/api/run/" + id); }
  catch(e) { ROOT.innerHTML = errBanner(e.message); return; }

  const sum = d.summary || d; // server may embed summary fields at top level
  const t = d.target || {};
  const S = d.seed || {};
  const B = d.best || {};
  const w = Object.assign({}, DEFW, d.weights || {});

  const nf = sum.n - sum.n_ok;
  const ch = (sum.best_j!=null && sum.seed_j && sum.seed_j<900)
    ? ((sum.best_j/sum.seed_j-1)*100).toFixed(1)+"%" : "–";
  const pinnedSens = (d.sens||[]).filter(s=>Math.max(s.at_lo,s.at_hi)>=4);

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Run · ${sum.family||""} · ${sum.mode||""}</div>
        <h2>${sum.name || id}</h2>
        <p class="muted mono" style="font-size:0.8rem">${id}</p>
      </div>
      <div class="kpis" id="kpi-strip"></div>
      <div class="btn-row">
        ${sum.has_report ? `<a class="btn" href="/runs/${id}/report.html" target="_blank" rel="noopener">Open report ↗</a>` : `<button disabled title="Report not generated">Open report</button>`}
        <button id="btn-step">Export STEP (top 3)</button>
        <a class="btn" href="#/run/${id}/3d">3D view</a>
        <a class="btn" href="#/compare?a=${id}">Compare…</a>
      </div>
      <div class="grid2">
        <div class="fig"><h3>Convergence</h3>
          <div class="cap">Every eval (dots) and running best (line). Failures omitted.</div>
          <svg id="c-conv"></svg></div>
        <div class="fig"><h3>Objective terms</h3>
          <div class="cap">Weighted contribution, seed vs best.</div>
          <svg id="c-terms"></svg></div>
        <div class="fig"><h3>Beamwidth</h3>
          <div class="legend">
            <span><i style="color:var(--seed)" class="dash"></i>seed H</span>
            <span><i style="color:var(--seed)"></i>seed V</span>
            <span><i style="color:var(--best)" class="dash"></i>best H</span>
            <span><i style="color:var(--best)"></i>best V</span>
            <span><i style="color:var(--muted)"></i>targets</span>
          </div>
          <svg id="c-bw"></svg></div>
        <div class="fig"><h3>Directivity index</h3>
          <div class="legend">
            <span><i style="color:var(--seed)"></i>seed</span>
            <span><i style="color:var(--best)"></i>best</span>
            <span><i style="color:var(--muted)" class="dash"></i>DI*</span>
          </div>
          <svg id="c-di"></svg></div>
        <div class="fig"><h3>On-axis (mean removed)</h3>
          <div class="legend">
            <span><i style="color:var(--seed)"></i>seed</span>
            <span><i style="color:var(--best)"></i>best</span>
          </div>
          <svg id="c-axis"></svg></div>
        <div class="fig"><h3>Wall profile</h3>
          <div class="cap">Mesh nodes in mm; radius vs depth. H right, V mirrored left.</div>
          <div class="legend">
            <span><i style="color:var(--seed)"></i>seed</span>
            <span><i style="color:var(--best)"></i>best</span>
          </div>
          <svg id="c-prof"></svg></div>
      </div>
      <div class="fig">
        <h3>Polar maps</h3>
        <div class="cap">Level rel. to on-axis; angle (−90°..+90°) vs frequency (low at bottom). −40..0 dB.</div>
        <div class="maps" id="polar-maps"></div>
        <div class="map">
          <canvas class="cbar" id="polar-cbar" width="400" height="10"></canvas>
          <div class="lbl"><span>−40 dB</span><span>−20</span><span>−6</span><span>0 dB</span></div>
        </div>
      </div>
      <div class="fig">
        <h3>Parameter sensitivity</h3>
        <div class="cap">Spearman ρ with J; at_lo / at_hi: how many of the best 6 designs sit at each bound.</div>
        <div class="tbl-wrap"><table id="sens-table"></table></div>
      </div>
      <div class="stack" style="gap:6px">
        <h3>Failures</h3>
        <div class="pill-row">${failurePills(sum.failures)}</div>
      </div>
      ${d.command ? `<div class="stack" style="gap:6px"><h3>Command</h3><div class="log-tail" style="max-height:60px">${escHtml(d.command)}</div></div>` : ""}
    </div>`;

  // KPI strip
  document.getElementById("kpi-strip").innerHTML = [
    ["Target", `${t.coverage_h_deg??"-"}° × ${t.coverage_v_deg??"-"}°`],
    ["Band",   `${t.band_lo_hz?t.band_lo_hz/1000:"–"}–${t.band_hi_hz?t.band_hi_hz/1000:"–"} kHz`],
    ["Seed J", fmt(sum.seed_j && sum.seed_j<900 ? sum.seed_j : null)],
    ["Best J", fmt(sum.best_j)],
    ["Change", ch],
    ["n", (sum.n||0).toLocaleString()],
    ["Fail", `${nf} (${sum.n?((nf/sum.n)*100).toFixed(1):"–"}%)`],
    ["Pinned", pinnedSens.length > 0 ? `<b class="bad">${pinnedSens.length}</b>` : pill("0","good")],
  ].map(([k,v]) => `<div class="kpi"><span>${k}</span><b>${v}</b></div>`).join("");

  const F = S.freqs || B.freqs || [];
  const band = [t.band_lo_hz||700, t.band_hi_hz||5500];

  // Convergence
  if (d.J && F.length) {
    const Js = (d.J||[]).map((j,i)=>[i,j]).filter(p=>p[1]!=null);
    let rb = Infinity; const runBest = Js.map(p=>[p[0],rb=Math.min(rb,p[1])]);
    const ymax = Math.max((sum.seed_j||0)*1.6, (sum.best_j||0)*2, 1);
    const svg = document.getElementById("c-conv");
    chart(svg, { xlim:[0,sum.n||Js.length], ylim:[0,ymax],
      xticks:niceTicks(0,sum.n||Js.length,5), yticks:niceTicks(0,ymax,5),
      xlabel:"evaluation", ylabel:"J",
      series:[{pts:Js, color:css("--muted"), dots:true, opacity:0.3},
              {pts:runBest, color:css("--best"), w:2.2}],
      hlines:[{y:sum.seed_j, color:css("--seed"), dash:true}]
    });
  }

  // Terms bar chart
  if (d.terms_seed && d.terms_best) {
    const svgT = document.getElementById("c-terms");
    svgT.innerHTML = "";
    const W=460, rowH=32, H=TERMS.length*rowH+30;
    svgT.setAttribute("viewBox",`0 0 ${W} ${H}`);
    const vals = TERMS.map(k=>[w[k]*(d.terms_seed[k]||0), w[k]*(d.terms_best[k]||0)]);
    const vmax = Math.max(...vals.flat(), 1e-9);
    const L=70, R=54, X = v => L + v/vmax*(W-L-R);
    TERMS.forEach((k,i) => {
      const y=6+i*rowH;
      const lab=el("text",{x:L-8,y:y+15,"text-anchor":"end"},svgT); lab.textContent=k+(w[k]?"":" (w=0)");
      [[vals[i][0],"--seed",0],[vals[i][1],"--best",12]].forEach(([v,c,dy]) => {
        el("rect",{x:L,y:y+dy,width:Math.max(0.5,X(v)-L),height:10,rx:2,fill:css(c)},svgT);
        const tv=el("text",{x:X(v)+4,y:y+dy+9},svgT); tv.textContent=v.toFixed(2);
      });
    });
    const lg=el("text",{x:L,y:H-4},svgT); lg.textContent="upper=seed · lower=best · weighted";
  }

  // Beamwidth
  if (F.length && S.bw_h) {
    const bwAll = [...(S.bw_h||[]),...(S.bw_v||[]),...(B.bw_h||[]),...(B.bw_v||[]),t.coverage_h_deg,t.coverage_v_deg].filter(v=>v!=null);
    const bmax = Math.min(200, Math.max(...bwAll)*1.08)||180;
    chart(document.getElementById("c-bw"), { xlog:true, xlim:[F[0],F[F.length-1]], ylim:[0,bmax],
      xticks:FT, yticks:niceTicks(0,bmax,5), xlabel:"Hz", ylabel:"deg", band,
      hlines:[{y:t.coverage_h_deg,color:css("--muted")},{y:t.coverage_v_deg,color:css("--muted")}],
      series:[
        {pts:F.map((f,i)=>[f,S.bw_h[i]]),color:css("--seed"),dash:true},
        {pts:F.map((f,i)=>[f,S.bw_v[i]]),color:css("--seed")},
        {pts:F.map((f,i)=>[f,B.bw_h?.[i]]),color:css("--best"),dash:true,w:2.2},
        {pts:F.map((f,i)=>[f,B.bw_v?.[i]]),color:css("--best"),w:2.2},
      ]
    });
  }

  // DI
  if (F.length && S.di) {
    const dit = t.di_target_db ?? diFromCuts(t.coverage_h_deg||90, t.coverage_v_deg||90);
    const dall = [...(S.di||[]),...(B.di||[]),dit].filter(v=>v!=null);
    const dlo = Math.floor(Math.min(...dall)-1), dhi = Math.ceil(Math.max(...dall)+1);
    chart(document.getElementById("c-di"), { xlog:true, xlim:[F[0],F[F.length-1]], ylim:[dlo,dhi],
      xticks:FT, yticks:niceTicks(dlo,dhi,5), xlabel:"Hz", ylabel:"dB", band,
      hlines:[{y:dit,color:css("--muted"),dash:true}],
      series:[{pts:F.map((f,i)=>[f,S.di[i]]),color:css("--seed")},{pts:F.map((f,i)=>[f,B.di?.[i]]),color:css("--best"),w:2.2}]
    });
  }

  // On-axis
  if (F.length && S.on_axis) {
    const aall = [...(S.on_axis||[]),...(B.on_axis||[])].filter(v=>v!=null);
    const alo=Math.floor(Math.min(...aall)-1), ahi=Math.ceil(Math.max(...aall)+1);
    chart(document.getElementById("c-axis"), { xlog:true, xlim:[F[0],F[F.length-1]], ylim:[alo,ahi],
      xticks:FT, yticks:niceTicks(alo,ahi,5), xlabel:"Hz", ylabel:"dB", band,
      series:[{pts:F.map((f,i)=>[f,S.on_axis[i]]),color:css("--seed")},{pts:F.map((f,i)=>[f,B.on_axis?.[i]]),color:css("--best"),w:2.2}]
    });
  }

  // Wall profile
  const ptsOf = (design, key, sgn) => ((design.profile||{})[key]||[]).map(p=>[sgn*Math.abs(p[1]),p[0]]);
  const allPts = [...ptsOf(S,"h",1),...ptsOf(S,"v",-1),...ptsOf(B,"h",1),...ptsOf(B,"v",-1)];
  if (allPts.length) {
    const rx = Math.max(...allPts.map(p=>Math.abs(p[0])))*1.08||100;
    const zs = allPts.map(p=>p[1]);
    const zlo=Math.min(...zs)-5, zhi=Math.max(...zs)+5;
    chart(document.getElementById("c-prof"), { H:260, xlim:[-rx,rx], ylim:[zlo,zhi],
      xticks:niceTicks(-rx,rx,6), yticks:niceTicks(zlo,zhi,5),
      xlabel:"← V plane · r mm · H plane →", ylabel:"z mm",
      series:[
        {pts:[...ptsOf(S,"h",1),...ptsOf(S,"v",-1)],color:css("--seed"),dots:true,r:1.8,opacity:0.8},
        {pts:[...ptsOf(B,"h",1),...ptsOf(B,"v",-1)],color:css("--best"),dots:true,r:1.8,opacity:0.9},
      ]
    });
  }

  // Polar maps
  const mapsEl = document.getElementById("polar-maps");
  mapsEl.innerHTML = "";
  drawCbar(document.getElementById("polar-cbar"));
  [["Seed · H",S.polar_h],["Best · H",B.polar_h],["Seed · V",S.polar_v],["Best · V",B.polar_v]].forEach(([lbl,rows]) => {
    if (!rows) return;
    const d2 = document.createElement("div"); d2.className="map";
    const c = document.createElement("canvas"); d2.appendChild(c); heat(c, rows);
    const l = document.createElement("div"); l.className="lbl";
    l.innerHTML=`<span>${lbl}</span><span>${F[0]??""} – ${F[F.length-1]??(F[0]||"")} Hz</span>`;
    d2.appendChild(l); mapsEl.appendChild(d2);
  });

  // Sensitivity table
  const sensT = document.getElementById("sens-table");
  if (d.sens && d.sens.length) {
    let s = `<thead><tr><th>Parameter</th><th class="r">Lo</th><th class="r">Hi</th>
      <th class="r">Best</th><th class="r">ρ</th><th></th>
      <th class="r">Top-6 at lo</th><th class="r">at hi</th></tr></thead><tbody>`;
    for (const p of d.sens) {
      const bar = `<svg width="90" height="10" viewBox="0 0 90 10">
        <rect x="45" y="0" width="0.8" height="10" fill="${css("--muted")}"/>
        <rect x="${p.rho<0?45+p.rho*45:45}" y="2" width="${Math.abs(p.rho)*45}" height="6" rx="1"
          fill="${css(p.rho>0?"--seed":"--best")}"/></svg>`;
      const flag = v => v>=4?`<span class="pill bad">${v}/6</span>`:v>=2?`<span class="pill warn">${v}/6</span>`:`${v}/6`;
      const hi = p.at_hi != null ? p.at_hi : (sum.n_ok||1);
      s += `<tr><td class="mono">${p.key}</td>
        <td class="r">${fmt(p.lo,3)}</td><td class="r">${fmt(p.hi,3)}</td>
        <td class="r">${fmt(p.best,3)}</td>
        <td class="r">${p.rho!=null?p.rho.toFixed(2):"–"}</td>
        <td>${bar}</td><td class="r">${flag(p.at_lo||0)}</td><td class="r">${flag(hi)}</td></tr>`;
    }
    sensT.innerHTML = s + "</tbody>";
  } else {
    sensT.innerHTML = "<tr><td class='muted'>No sensitivity data.</td></tr>";
  }

  // Export STEP button
  document.getElementById("btn-step").onclick = async () => {
    const r = await post("/api/jobs", { kind:"export-step", args:{ run:id, top:3 } });
    if (r.error) alert("Error: " + r.error);
    else { alert(`Export job started: ${r.id}`); location.hash = "#/launch"; }
  };
}

// ── View 3 / 7: 3D view ────────────────────────────────────────────

async function viewRun3D(id) {
  loading();
  let runD, meshD;
  try { runD = await api("/api/run/" + id); }
  catch(e) { ROOT.innerHTML = errBanner("Could not load run: " + e.message); return; }
  const hash = (runD.summary || runD).best_hash || (runD.best||{}).hash;
  if (!hash) { ROOT.innerHTML = errBanner("No best design hash for this run."); return; }
  try { meshD = await api("/api/mesh/" + id + "/" + hash); }
  catch(e) { ROOT.innerHTML = errBanner("Could not load mesh: " + e.message); return; }

  const sum = runD.summary || runD;
  ROOT.innerHTML = `
    <div class="stack" style="gap:16px">
      <div>
        <div class="eyebrow">3D view</div>
        <h2>${sum.name||id}</h2>
        <p class="muted" style="font-size:0.82rem">Hash: <span class="mono">${hash}</span> · ${meshD.n_tris||"?"} triangles (mirrored from quarter model)</p>
      </div>
      <div class="btn-row">
        <a class="btn" href="#/run/${id}">← Back to run</a>
      </div>
      <div id="view3d-wrap"><div class="view3d-fallback">Loading 3D…</div></div>
      <p class="muted" style="font-size:0.8rem">Drag to orbit · scroll to zoom · right-drag to pan.</p>
    </div>`;

  const wrap = document.getElementById("view3d-wrap");
  const profile = (runD.best||{}).profile;
  await init3d(wrap, meshD, profile);
}

// ── View 4: Compare ────────────────────────────────────────────────

async function viewCompare() {
  let allRuns = [];
  try { allRuns = await api("/api/runs"); } catch {}

  // Pre-fill from query ?a=...
  const hash = location.hash;
  const qaMatch = hash.match(/[?&]a=([^&]+)/);
  const qbMatch = hash.match(/[?&]b=([^&]+)/);
  const preA = qaMatch ? qaMatch[1] : "";
  const preB = qbMatch ? qbMatch[1] : "";

  const opts = allRuns.map(r=>
    `<option value="${r.id}" >${r.name} — ${r.id.slice(0,20)}… (J=${fmt(r.best_j)})</option>`
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
    try { cmp = await api(`/api/compare?a=${a}&b=${b}`); }
    catch(e) { res.innerHTML = errBanner(e.message); return; }
    if (cmp.error) { res.innerHTML = errBanner(cmp.error); return; }

    const rowData = Object.entries(cmp.rows||{});
    const metricTable = rowData.length ? `
      <div class="tbl-wrap">
        <table>
          <thead><tr><th>Metric</th><th>Unit</th>
            <th class="r">max |A − B|</th><th class="r">mean |A − B|</th><th class="r">n freqs</th></tr></thead>
          <tbody>${rowData.map(([k,v])=>`<tr>
            <td class="mono">${k}</td><td class="mono muted">${v.unit||""}</td>
            <td class="r">${fmt(v.max,3)}</td><td class="r">${fmt(v.mean,3)}</td><td class="r">${v.n??""}</td>
          </tr>`).join("")}</tbody>
        </table>
      </div>` : "<p class='muted'>No metric data.</p>";

    const dA = cmp.a || {}, dB = cmp.b || {};
    const FA = dA.freqs || [], FB = dB.freqs || [];
    const F = FA.length ? FA : FB;
    const band = [700, 5500]; // fallback

    res.innerHTML = `
      <div class="stack" style="gap:20px">
        <h3>Metric comparison</h3>
        <p class="muted">Same numbers as <code>hornlab-search compare</code>: per-frequency |A − B| on the shared grid. Report only. Reference: OSSE full vs quarter mesh 0.023 dB (CP-7d).</p>
        ${metricTable}
        <div class="grid2">
          <div class="fig"><h3>Beamwidth H</h3>
            <div class="legend"><span><i style="color:var(--seed)"></i>A</span><span><i style="color:var(--best)"></i>B</span></div>
            <svg id="cmp-bwh"></svg></div>
          <div class="fig"><h3>Beamwidth V</h3>
            <div class="legend"><span><i style="color:var(--seed)"></i>A</span><span><i style="color:var(--best)"></i>B</span></div>
            <svg id="cmp-bwv"></svg></div>
          <div class="fig"><h3>DI</h3>
            <div class="legend"><span><i style="color:var(--seed)"></i>A</span><span><i style="color:var(--best)"></i>B</span></div>
            <svg id="cmp-di"></svg></div>
          <div class="fig"><h3>On-axis</h3>
            <div class="legend"><span><i style="color:var(--seed)"></i>A</span><span><i style="color:var(--best)"></i>B</span></div>
            <svg id="cmp-axis"></svg></div>
        </div>
      </div>`;

    if (!F.length) return;

    function cmpChart(svgId, keyA, keyB, ylabel) {
      const svg = document.getElementById(svgId);
      if (!svg) return;
      const allV = [...(dA[keyA]||[]),...(dB[keyB]||[])].filter(v=>v!=null);
      if (!allV.length) return;
      const lo=Math.floor(Math.min(...allV)-1), hi=Math.ceil(Math.max(...allV)+1);
      chart(svg, { xlog:true, xlim:[F[0],F[F.length-1]], ylim:[lo,hi],
        xticks:FT, yticks:niceTicks(lo,hi,5), xlabel:"Hz", ylabel, band,
        series:[{pts:F.map((f,i)=>[f,(dA[keyA]||[])[i]??null]),color:css("--seed"),w:1.8},
                {pts:F.map((f,i)=>[f,(dB[keyB]||[])[i]??null]),color:css("--best"),w:1.8}]
      });
    }
    cmpChart("cmp-bwh","bw_h","bw_h","deg");
    cmpChart("cmp-bwv","bw_v","bw_v","deg");
    cmpChart("cmp-di","di","di","dB");
    cmpChart("cmp-axis","on_axis","on_axis","dB");
  }

  document.getElementById("btn-compare").onclick = doCompare;
  if (preA && preB) doCompare();               // a shared #/compare?a=&b= link opens with the result
  if (preA && preB) doCompare();
}

// ── View 5: Briefs ─────────────────────────────────────────────────

async function viewBriefs() {
  loading();
  let briefs;
  try { briefs = await api("/api/briefs"); }
  catch(e) { ROOT.innerHTML = errBanner(e.message); return; }

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Briefs &amp; families</div>
        <h2>Briefs</h2>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px" id="briefs-list"></div>
      <div id="brief-detail"></div>
    </div>`;

  const listEl = document.getElementById("briefs-list");
  briefs.forEach(b => {
    const btn = document.createElement("button");
    btn.className = "card";
    btn.style.cssText = "text-align:left;cursor:pointer;";
    btn.innerHTML = `<div style="font-weight:500">${b.name}</div>
      <div class="muted mono" style="font-size:0.75rem">${b.kind}</div>`;
    btn.onclick = () => showBriefDetail(b, briefs);
    listEl.appendChild(btn);
  });

  // Show first brief by default
  if (briefs.length) showBriefDetail(briefs[0], briefs);
}

async function showBriefDetail(b, allBriefs) {
  const det = document.getElementById("brief-detail");
  det.innerHTML = `<p class="muted">Loading…</p>`;
  const br = b.brief || {};
  const tgt = br.target || {};
  const wt  = br.weights || {};
  const env = br.envelope || {};
  const drv = br.driver || {};

  const bandHiWarn = (tgt.band_hi_hz||0) > 5500
    ? `<span class="warn-text">⚠ band_hi > 5500 Hz — 8 GB GPU limit may apply</span>` : "";

  det.innerHTML = `
    <div class="stack" style="gap:20px">
      <hr class="sep">
      <div>
        <h3>${b.name} <span class="pill" style="font-size:0.7rem;border-color:var(--muted);color:var(--muted)">${b.kind}</span></h3>
        <p class="muted" style="font-size:0.85rem">${br.description||""}</p>
        <p class="muted mono" style="font-size:0.75rem">${b.path||""}</p>
      </div>
      <form id="brief-form" class="stack" style="gap:16px">
        <h4>Target</h4>
        <div class="form-grid">
          <label for="brf-cov-h">coverage_h_deg</label>
          <input id="brf-cov-h" type="number" step="1" value="${tgt.coverage_h_deg??90}" aria-label="coverage_h_deg">
          <label for="brf-cov-v">coverage_v_deg</label>
          <input id="brf-cov-v" type="number" step="1" value="${tgt.coverage_v_deg??90}" aria-label="coverage_v_deg">
          <label for="brf-blo">band_lo_hz</label>
          <input id="brf-blo" type="number" step="1" value="${tgt.band_lo_hz??700}" aria-label="band_lo_hz">
          <label for="brf-bhi">band_hi_hz</label>
          <div>
            <input id="brf-bhi" type="number" step="1" value="${tgt.band_hi_hz??5500}" aria-label="band_hi_hz">
            <div class="hint" id="bhi-warn">${bandHiWarn}</div>
          </div>
          <label for="brf-di">di_target_db</label>
          <input id="brf-di" type="number" step="0.1" value="${tgt.di_target_db??""}" placeholder="auto" aria-label="di_target_db">
          <label for="brf-dislope">di_slope_target</label>
          <input id="brf-dislope" type="number" step="0.01" value="${tgt.di_slope_target??0}" aria-label="di_slope_target">
        </div>
        <h4>Weights</h4>
        <div class="form-grid">
          ${TERMS.map(k=>`<label for="brf-w-${k}">${k}</label>
            <input id="brf-w-${k}" type="number" step="0.1" value="${wt[k]??DEFW[k]}" aria-label="weight ${k}">`).join("")}
        </div>
        <h4>Envelope</h4>
        <div class="form-grid">
          <label for="brf-mw">max_mouth_w_mm</label>
          <input id="brf-mw" type="number" step="1" value="${env.max_mouth_w_mm??360}" aria-label="max_mouth_w_mm">
          <label for="brf-mh">max_mouth_h_mm</label>
          <input id="brf-mh" type="number" step="1" value="${env.max_mouth_h_mm??360}" aria-label="max_mouth_h_mm">
          <label for="brf-md">max_depth_mm</label>
          <input id="brf-md" type="number" step="1" value="${env.max_depth_mm??220}" aria-label="max_depth_mm">
        </div>
        <h4>Driver</h4>
        <div class="form-grid">
          <label for="brf-er">exit_radius_mm</label>
          <input id="brf-er" type="number" step="0.1" value="${drv.exit_radius_mm??12.7}" aria-label="exit_radius_mm">
          <label for="brf-ea">exit_angle_deg</label>
          <input id="brf-ea" type="number" step="0.1" value="${drv.exit_angle_deg??5.0}" aria-label="exit_angle_deg">
        </div>
        <div class="btn-row">
          <div class="form-group" style="flex-direction:row;align-items:center;gap:8px">
            <input id="brf-save-name" type="text" placeholder="new-brief-name" aria-label="save as name"
              style="font:inherit;font-size:0.88rem;background:var(--bg);border:1px solid var(--rule);border-radius:5px;padding:6px 10px;width:180px">
            <button type="button" id="btn-save-brief" class="primary">Save as new brief</button>
          </div>
        </div>
        <div id="brief-save-msg"></div>
      </form>
      <div>
        <h4 style="margin-bottom:8px">Family compatibility (GET /api/families?brief=${b.name})</h4>
        <button id="btn-families">Show families</button>
        <pre class="families-out" id="families-out" style="display:none"></pre>
      </div>
    </div>`;

  // Band-hi warning
  document.getElementById("brf-bhi").addEventListener("input", e => {
    document.getElementById("bhi-warn").innerHTML =
      +e.target.value > 5500 ? `<span class="warn-text">⚠ band_hi > 5500 Hz — 8 GB GPU limit may apply</span>` : "";
  });

  // Save brief
  document.getElementById("btn-save-brief").onclick = async () => {
    const name = document.getElementById("brf-save-name").value.trim();
    if (!name) { document.getElementById("brief-save-msg").innerHTML=`<div class="alert warn">Enter a name.</div>`; return; }
    const newBrief = {
      name, description: br.description||"",
      driver: { exit_radius_mm: +document.getElementById("brf-er").value, exit_angle_deg: +document.getElementById("brf-ea").value },
      envelope: { max_mouth_w_mm: +document.getElementById("brf-mw").value, max_mouth_h_mm: +document.getElementById("brf-mh").value, max_depth_mm: +document.getElementById("brf-md").value },
      symmetry: br.symmetry||"hv", source: br.source||{},
      target: {
        coverage_h_deg: +document.getElementById("brf-cov-h").value,
        coverage_v_deg: +document.getElementById("brf-cov-v").value,
        band_lo_hz: +document.getElementById("brf-blo").value,
        band_hi_hz: +document.getElementById("brf-bhi").value,
        di_target_db: document.getElementById("brf-di").value ? +document.getElementById("brf-di").value : null,
        di_slope_target: +document.getElementById("brf-dislope").value,
        z_min: tgt.z_min??0,
      },
      weights: Object.fromEntries(TERMS.map(k=>[k, +document.getElementById(`brf-w-${k}`).value])),
    };
    const r = await post("/api/brief", { name, brief: newBrief });
    const msg = document.getElementById("brief-save-msg");
    if (r.error) msg.innerHTML = `<div class="alert error">${escHtml(r.error)}</div>`;
    else msg.innerHTML = `<div class="alert info">Saved to ${r.path||name}</div>`;
  };

  // Show families
  document.getElementById("btn-families").onclick = async () => {
    const pre = document.getElementById("families-out");
    pre.style.display = "block";
    pre.textContent = "Loading…";
    try {
      const r = await api("/api/families?brief=" + encodeURIComponent(b.name));
      pre.textContent = r.text || "(no output)";
    } catch(e) { pre.textContent = "Error: " + e.message; }
  };
}

// ── View 6: Launch ─────────────────────────────────────────────────

let _launchPollTimer = null;

async function viewLaunch() {
  loading();
  let briefs = [], jobs = [];
  try { [briefs, jobs] = await Promise.all([api("/api/briefs"), api("/api/jobs")]); }
  catch(e) { ROOT.innerHTML = errBanner(e.message); return; }

  renderLaunch(briefs, jobs);
}

function renderLaunch(briefs, jobs) {
  const briefOpts = briefs.map(b => `<option value="${b.name}">${b.name}</option>`).join("");

  ROOT.innerHTML = `
    <div class="stack" style="gap:24px">
      <div>
        <div class="eyebrow">Launch jobs</div>
        <h2>Launch</h2>
        <p class="muted" style="font-size:0.85rem">⚠ Compare tier takes hours — never run it during a live GPU session.</p>
      </div>
      <div class="card stack" style="gap:16px">
        <h3>Job type</h3>
        <div class="btn-row" role="radiogroup" aria-label="job type">
          <button class="job-type-btn" data-type="campaign" aria-pressed="true">Campaign</button>
          <button class="job-type-btn" data-type="search" aria-pressed="false">Search</button>
          <button class="job-type-btn" data-type="dry-run" aria-pressed="false">Dry-run</button>
        </div>

        <div id="launch-form-campaign" class="launch-form" style="display:grid;gap:12px">
          <div class="form-grid">
            <label for="lf-brief">Brief</label>
            <select id="lf-brief" aria-label="brief">${briefOpts}</select>
            <label for="lf-families">Families (comma-sep)</label>
            <input id="lf-families" type="text" placeholder="osse_axi, hypex, exponential">
            <label for="lf-tier">Tier</label>
            <select id="lf-tier" aria-label="tier">
              <option value="dry-run">dry-run</option>
              <option value="screen" selected>screen</option>
              <option value="compare">compare</option>
            </select>
          </div>
        </div>

        <div id="launch-form-search" class="launch-form" style="display:none;gap:12px">
          <div class="form-grid">
            <label for="lf-config">Config path</label>
            <input id="lf-config" type="text" placeholder="examples/osse_baseline.yaml">
            <label for="lf-budget">Budget</label>
            <input id="lf-budget" type="number" value="200" min="1">
            <label for="lf-seed">CMA seed</label>
            <input id="lf-seed" type="number" value="1234">
            <label for="lf-sbrief">Brief (optional)</label>
            <select id="lf-sbrief" aria-label="brief for search"><option value="">— use config default —</option>${briefOpts}</select>
          </div>
        </div>

        <div id="launch-form-dry-run" class="launch-form" style="display:none;gap:12px">
          <div class="form-grid">
            <label for="lf-drconfig">Config path</label>
            <input id="lf-drconfig" type="text" placeholder="examples/osse_baseline.yaml">
          </div>
        </div>

        <div class="card" style="background:var(--bg)">
          <div class="eyebrow" style="margin-bottom:6px">Command preview</div>
          <code id="cmd-preview" style="white-space:pre-wrap;word-break:break-all">hornlab-search campaign …</code>
        </div>
        <div class="btn-row">
          <button id="btn-launch" class="primary">Start</button>
        </div>
        <div id="launch-error"></div>
      </div>

      <div>
        <div class="section-header">
          <h3>Jobs</h3>
          <button id="btn-refresh-jobs">↻ Refresh</button>
        </div>
        <div id="jobs-list" class="stack" style="gap:8px"></div>
      </div>
    </div>`;

  // Type toggle
  let currentType = "campaign";
  document.querySelectorAll(".job-type-btn").forEach(btn => {
    btn.onclick = () => {
      currentType = btn.dataset.type;
      document.querySelectorAll(".job-type-btn").forEach(b => b.setAttribute("aria-pressed","false"));
      btn.setAttribute("aria-pressed","true");
      document.querySelectorAll(".launch-form").forEach(f => f.style.display="none");
      document.getElementById(`launch-form-${currentType}`).style.display="grid";
      updatePreview();
    };
  });

  // Command preview
  function updatePreview() {
    let cmd = "hornlab-search ";
    if (currentType === "campaign") {
      const brief = document.getElementById("lf-brief").value;
      const fam   = document.getElementById("lf-families").value;
      const tier  = document.getElementById("lf-tier").value;
      cmd += `campaign --brief ${brief}`;
      if (fam) cmd += ` --families ${fam.split(",").map(s=>s.trim()).filter(Boolean).join(",")}`;
      cmd += ` --tier ${tier}`;
    } else if (currentType === "search") {
      const cfg = document.getElementById("lf-config").value;
      const bud = document.getElementById("lf-budget").value;
      const seed= document.getElementById("lf-seed").value;
      const br  = document.getElementById("lf-sbrief").value;
      cmd += `search --config ${cfg||"<config>"} --budget ${bud} --cma-seed ${seed}`;
      if (br) cmd += ` --brief ${br}`;
    } else {
      const cfg = document.getElementById("lf-drconfig").value;
      cmd += `dry-run --config ${cfg||"<config>"}`;
    }
    document.getElementById("cmd-preview").textContent = cmd;
  }

  // Wire inputs to preview
  ["lf-brief","lf-families","lf-tier","lf-config","lf-budget","lf-seed","lf-sbrief","lf-drconfig"].forEach(id => {
    const el2 = document.getElementById(id);
    if (el2) el2.addEventListener("input", updatePreview);
    if (el2) el2.addEventListener("change", updatePreview);
  });
  updatePreview();

  // Launch
  document.getElementById("btn-launch").onclick = async () => {
    const errEl = document.getElementById("launch-error");
    errEl.innerHTML = "";
    let kind, args;
    if (currentType === "campaign") {
      kind = "campaign";
      args = {
        brief: document.getElementById("lf-brief").value,
        families: document.getElementById("lf-families").value.split(",").map(s=>s.trim()).filter(Boolean),
        tier: document.getElementById("lf-tier").value,
      };
    } else if (currentType === "search") {
      kind = "search";
      args = {
        config: document.getElementById("lf-config").value,
        budget: +document.getElementById("lf-budget").value,
        cma_seed: +document.getElementById("lf-seed").value,
        brief: document.getElementById("lf-sbrief").value || undefined,
      };
    } else {
      kind = "dry-run";
      args = { config: document.getElementById("lf-drconfig").value };
    }
    const r = await post("/api/jobs", { kind, args });
    if (r.error) {
      errEl.innerHTML = `<div class="alert error" role="alert"><b>Error:</b> ${escHtml(r.error)}</div>`;
    } else {
      errEl.innerHTML = `<div class="alert info">Job started: ${r.id}</div>`;
      refreshJobs();
    }
  };

  renderJobs(jobs);
  document.getElementById("btn-refresh-jobs").onclick = refreshJobs;

  // Poll running jobs every 2s
  clearInterval(_launchPollTimer);
  _launchPollTimer = setInterval(async () => {
    if (!location.hash.startsWith("#/launch")) { clearInterval(_launchPollTimer); return; }
    refreshJobs();
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
    const sc = `job-status-${j.status||"done"}`;
    const dur = j.started && j.ended
      ? " · " + ((new Date(j.ended)-new Date(j.started))/60000).toFixed(1)+"m"
      : j.started ? " · running" : "";
    const logLines = (j.log_tail||[]).join("\n");
    const cancelBtn = j.status==="running"
      ? `<button class="btn danger" onclick="cancelJob('${j.id}')">Cancel</button>` : "";
    return `<div class="job-row">
      <div class="job-head">
        <div>
          <span class="job-title">${j.kind||""} · <span class="mono">${j.id||""}</span></span>
          <span class="${sc}"> ${j.status||""}${dur}</span>
        </div>
        ${cancelBtn}
      </div>
      <div class="mono muted" style="font-size:0.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escHtml((j.command||j.argv||[]).join?.(" ")||j.command||"")}</div>
      ${logLines ? `<div class="log-tail" style="max-height:100px">${escHtml(logLines)}</div>` : ""}
    </div>`;
  }).join("");
}

window.cancelJob = async (id) => {
  if (!confirm("Cancel this job?")) return;
  const r = await post("/api/job/" + id + "/cancel", {});
  if (r.error) alert("Error: " + r.error);
  refreshJobs();
};

// ── Init ───────────────────────────────────────────────────────────

route();

// Redraw charts on theme change
matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", () => {
  if (location.hash.startsWith("#/run/") || location.hash.startsWith("#/campaign/")) route();
});
new MutationObserver(() => {
  if (location.hash.startsWith("#/run/") || location.hash.startsWith("#/campaign/")) route();
}).observe(document.documentElement, { attributes:true, attributeFilter:["data-theme"] });
