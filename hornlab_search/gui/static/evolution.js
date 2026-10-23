// evolution.js — time-lapse of a search: how the horn's shape and score evolved, evaluation by evaluation.
// AGPL-3.0-or-later. Data: GET /api/evolution/<run> (hornlab_search/gui/data.py::evolution). Geometry is
// what the search meshed; axes are fixed for the whole run so on-screen motion is the design changing.
import { css, niceTicks, NS, el, familyColor } from "./charts.js";

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (v, d = 2) => v == null || !isFinite(v) ? "–" : Number(v).toFixed(d);
const GHOSTS = 4;                                   // onion-skin: previous best designs drawn faded

export async function viewEvolution(root, runId) {
  root.innerHTML = `<p class="muted">Preparing the time-lapse (first time per run reads every saved mesh; a few seconds)…</p>`;
  let E;
  try {
    const r = await fetch("/api/evolution/" + encodeURIComponent(runId));
    if (!r.ok) throw new Error(r.status + " " + (await r.text()));
    E = await r.json();
  } catch (e) { root.innerHTML = `<div class="alert error">Could not load: ${esc(e.message)}</div>`; return; }
  const F = E.frames || [];
  if (!F.length) { root.innerHTML = `<p class="muted">This run has no evaluations yet.</p>`; return; }

  root.innerHTML = `<div class="stack evo" style="gap:16px">
    <div>
      <div class="eyebrow">Search time-lapse</div>
      <h2>${esc(E.name || runId)}</h2>
      <p class="muted" style="margin:2px 0 0">${F.length} evaluations, ${E.n_improvements} improvements.
        Side view and mouth are drawn at true scale on fixed axes for the whole run; faded outlines are the previous best designs.
        <a href="#/run/${esc(runId)}">← back to the run</a></p>
    </div>
    <div class="evo-controls card" role="group" aria-label="Playback">
      <button id="evo-play" class="primary" aria-label="Play">▶ Play</button>
      <button id="evo-prev" aria-label="Previous frame">⟨</button>
      <button id="evo-next" aria-label="Next frame">⟩</button>
      <input id="evo-scrub" type="range" min="0" max="0" value="0" aria-label="Frame">
      <span id="evo-pos" class="mono evo-pos"></span>
      <label class="evo-opt"><select id="evo-mode" aria-label="Frames">
        <option value="best">improvements only</option><option value="all">every candidate</option></select></label>
      <label class="evo-opt">speed <select id="evo-speed" aria-label="Speed">
        <option value="1200">slow</option><option value="500" selected>normal</option><option value="150">fast</option><option value="40">very fast</option></select></label>
      <label class="evo-opt"><input type="checkbox" id="evo-loop" checked> loop</label>
    </div>
    <div class="evo-status card" id="evo-status" aria-live="polite"></div>
    <div class="evo-grid">
      <div class="fig"><h3>Side view: wall cross-section</h3>
        <div class="cap">Horizontal plane right, vertical plane mirrored left, throat at the bottom (mm).</div>
        <svg id="evo-side"></svg></div>
      <div class="fig"><h3>Front view: mouth outline</h3>
        <div class="cap">Outer rim of the mouth, shell included (mm). Dashed: the brief's size envelope.</div>
        <svg id="evo-front"></svg></div>
    </div>
    <div class="evo-grid">
      <div class="fig"><h3>Score over the search</h3>
        <div class="cap">Dots: every evaluation (lower is better). Line: best so far. Red ticks: failed designs. Playhead: current frame.</div>
        <svg id="evo-score"></svg></div>
      <div class="fig"><h3>Shape parameters within their limits</h3>
        <div class="cap">Each bar spans a parameter's search limits; the marker is the current design. Red = pressed against a limit.</div>
        <div id="evo-knobs" class="evo-knobs"></div></div>
    </div>
  </div>`;

  const ext = E.extent, env = await envelopeFor(E);
  const side = document.getElementById("evo-side"), front = document.getElementById("evo-front");
  const score = document.getElementById("evo-score"), knobsEl = document.getElementById("evo-knobs");
  const scrub = document.getElementById("evo-scrub"), pos = document.getElementById("evo-pos");
  const statusEl = document.getElementById("evo-status");
  let mode = "best", idx = 0, timer = null;
  let seq = [];                                     // indices into F for the current mode

  function buildSeq() {
    seq = mode === "best" ? F.map((f, i) => i).filter(i => F[i].improved) : F.map((f, i) => i);
    if (!seq.length) seq = [0];
    scrub.max = String(seq.length - 1);
  }

  // ── static layers (drawn once per mode / resize) ──────────────────────────────────────────────
  let S = {}, Fr = {}, Sc = {};
  function layout() {
    S = sideFrame(side, ext); Fr = frontFrame(front, ext, env); Sc = scoreFrame(score, F);
    knobsEl.innerHTML = Object.entries(E.bounds || {}).map(([k, b]) => `
      <div class="evo-knob"><span class="mono evo-kname" title="${esc(k)}">${esc(k)}</span>
        <span class="evo-kbar"><span class="evo-kmark" data-k="${esc(k)}"></span></span>
        <span class="mono evo-kval" data-v="${esc(k)}"></span></div>`).join("");
  }

  function show(i) {
    idx = Math.max(0, Math.min(seq.length - 1, i));
    scrub.value = String(idx);
    const fi = seq[idx], f = F[fi];
    // ghosts: previous improvements before this frame (shape history)
    const prevBest = [];
    for (let k = fi - 1; k >= 0 && prevBest.length < GHOSTS; k--) if (F[k].improved && F[k].geo) prevBest.push(F[k]);
    // best design so far (the one the score line is at)
    let bestF = null;
    for (let k = fi; k >= 0; k--) if (F[k].improved) { bestF = F[k]; break; }
    drawSide(S, f, prevBest, bestF);
    drawFront(Fr, f, prevBest, bestF);
    Sc.playhead(fi);
    for (const [k, [lo, hi]] of Object.entries(E.bounds || {})) {
      const v = f.knobs ? f.knobs[k] : null;
      const m = knobsEl.querySelector(`[data-k="${CSS.escape(k)}"]`), t = knobsEl.querySelector(`[data-v="${CSS.escape(k)}"]`);
      if (!m) continue;
      if (v == null) { m.style.display = "none"; t.textContent = "–"; continue; }
      m.style.display = ""; m.style.left = `calc(${(Math.max(0, Math.min(1, v)) * 100).toFixed(1)}% - 5px)`;
      m.classList.toggle("at-limit", v <= 0.02 + 1e-6 || v >= 0.98 - 1e-6);   // "at limit" = within 2 % of a bound, as in the run page
      t.textContent = fmt(lo + v * (hi - lo), Math.abs(hi - lo) < 2 ? 3 : 1);
    }
    const fail = !f.ok ? `<span class="pill bad">${esc(f.kind || "failed")}</span>` : "";
    const imp = f.improved ? `<span class="pill good">new best</span>` : "";
    statusEl.innerHTML = `<span class="mono">evaluation ${f.n + 1} / ${F.length}</span>
      <span>score <b>${fmt(f.j)}</b></span><span>best so far <b>${fmt(f.best_j)}</b></span>
      ${imp} ${fail} ${f.cached ? `<span class="pill">replayed from cache</span>` : ""}
      ${f.geo ? "" : `<span class="muted">no mesh saved for this design</span>`}`;
    pos.textContent = `${idx + 1} / ${seq.length}`;
  }

  function play() {
    if (timer) { stop(); return; }
    document.getElementById("evo-play").textContent = "❚❚ Pause";
    const step = () => {
      if (idx >= seq.length - 1) {
        if (!document.getElementById("evo-loop").checked) { stop(); return; }
        show(0);
      } else show(idx + 1);
      timer = setTimeout(step, +document.getElementById("evo-speed").value);
    };
    timer = setTimeout(step, 0);
  }
  function stop() { clearTimeout(timer); timer = null; const b = document.getElementById("evo-play"); if (b) b.textContent = "▶ Play"; }

  document.getElementById("evo-play").onclick = play;
  document.getElementById("evo-prev").onclick = () => { stop(); show(idx - 1); };
  document.getElementById("evo-next").onclick = () => { stop(); show(idx + 1); };
  scrub.oninput = () => { stop(); show(+scrub.value); };
  document.getElementById("evo-mode").onchange = e => { stop(); const cur = seq[idx]; mode = e.target.value; buildSeq();
    let j = seq.findIndex(s => s >= cur); show(j < 0 ? seq.length - 1 : j); };
  const onKey = e => {
    if (!document.getElementById("evo-scrub")) { document.removeEventListener("keydown", onKey); stop(); return; }
    if (["INPUT", "SELECT", "TEXTAREA"].includes(e.target.tagName) && e.target.type !== "range") return;
    if (e.key === " ") { e.preventDefault(); play(); }
    else if (e.key === "ArrowRight") { e.preventDefault(); stop(); show(idx + 1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); stop(); show(idx - 1); }
    else if (e.key === "Home") { stop(); show(0); } else if (e.key === "End") { stop(); show(seq.length - 1); }
  };
  document.addEventListener("keydown", onKey);
  window.addEventListener("hashchange", stop, { once: true });

  const q = new URLSearchParams(location.hash.split("?")[1] || "");
  if (q.get("mode") === "all") { mode = "all"; document.getElementById("evo-mode").value = "all"; }
  buildSeq(); layout(); show(q.get("f") === "last" ? seq.length - 1 : (+q.get("f") || 0));
}

// The brief's size envelope (outer mouth width / height) for the front view, when the run names a brief.
async function envelopeFor(E) {
  try {
    const run = await (await fetch("/api/run/" + encodeURIComponent(E.run_id))).json();
    const env = (run.brief || {}).envelope;
    return env && env.max_mouth_w_mm ? { w: env.max_mouth_w_mm, h: env.max_mouth_h_mm } : null;
  } catch { return null; }
}

// ── side view ─────────────────────────────────────────────────────────────────────────────────────
function sideFrame(svg, ext) {
  svg.innerHTML = "";
  const W = Math.max(280, Math.round(svg.getBoundingClientRect().width || 460)), H = 330;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("width", W); svg.setAttribute("height", H);
  const m = { l: 40, r: 10, t: 10, b: 28 }, pw = W - m.l - m.r, ph = H - m.t - m.b;
  const sc = Math.min(pw / (2 * ext.rmax * 1.05), ph / ((ext.z1 - ext.z0) * 1.05));
  const cx = m.l + pw / 2, by = m.t + ph - (ph - (ext.z1 - ext.z0) * sc) / 2;
  const X = r => cx + r * sc, Y = z => by - (z - ext.z0) * sc;
  const g = el("g", { class: "grid" }, svg);
  for (const t of niceTicks(-ext.rmax, ext.rmax, 6)) { el("line", { x1: X(t), x2: X(t), y1: m.t, y2: m.t + ph }, g);
    el("text", { x: X(t), y: H - 10, "text-anchor": "middle" }, svg).textContent = Math.abs(t); }
  for (const t of niceTicks(ext.z0, ext.z1, 4)) { el("line", { x1: m.l, x2: m.l + pw, y1: Y(t), y2: Y(t) }, g);
    el("text", { x: m.l - 5, y: Y(t) + 3, "text-anchor": "end" }, svg).textContent = t; }
  el("line", { x1: cx, x2: cx, y1: m.t, y2: m.t + ph, stroke: css("--muted"), "stroke-dasharray": "3 3", "stroke-opacity": 0.6 }, svg);
  el("text", { x: m.l + pw, y: H - 1, "text-anchor": "end" }, svg).textContent = "r mm (H →)";
  el("text", { x: m.l, y: H - 1 }, svg).textContent = "(← V)";
  const layer = el("g", {}, svg);
  return { svg, layer, X, Y };
}
function sectionPath(sec, X, Y) {
  if (!sec || sec.kind !== "section") return "";
  let d = "";
  for (const [k, s] of [["h", 1], ["v", -1]]) {
    const pts = sec[k] || [];
    if (pts.length) d += pts.map(([z, r], i) => (i ? "L" : "M") + X(s * r).toFixed(1) + "," + Y(z).toFixed(1)).join("") + "Z";
  }
  return d;
}
function drawSide(S, f, ghosts, bestF) {
  S.layer.innerHTML = "";
  ghosts.slice().reverse().forEach((g, i) => el("path", { d: sectionPath(g.geo.section, S.X, S.Y), fill: "none",
    stroke: css("--muted"), "stroke-opacity": 0.15 + 0.12 * i, "stroke-width": 1 }, S.layer));
  if (bestF && bestF !== f && bestF.geo)
    el("path", { d: sectionPath(bestF.geo.section, S.X, S.Y), fill: "none", stroke: css("--best"), "stroke-width": 1.2, "stroke-dasharray": "4 3" }, S.layer);
  if (f.geo) el("path", { d: sectionPath(f.geo.section, S.X, S.Y), fill: f.ok ? css("--best") : css("--bad"),
    "fill-opacity": 0.3, stroke: f.ok ? css("--best") : css("--bad"), "stroke-width": 1.6, "stroke-linejoin": "round" }, S.layer);
}

// ── front view ────────────────────────────────────────────────────────────────────────────────────
function frontFrame(svg, ext, env) {
  svg.innerHTML = "";
  const W = Math.max(260, Math.round(svg.getBoundingClientRect().width || 400)), H = 330;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("width", W); svg.setAttribute("height", H);
  const R = Math.max(ext.mmax, env ? Math.max(env.w, env.h) / 2 : 0) * 1.08;
  const m = { l: 36, r: 10, t: 10, b: 28 }, pw = W - m.l - m.r, ph = H - m.t - m.b;
  const sc = Math.min(pw, ph) / (2 * R), cx = m.l + pw / 2, cy = m.t + ph / 2;
  const X = x => cx + x * sc, Y = y => cy - y * sc;
  const g = el("g", { class: "grid" }, svg);
  for (const t of niceTicks(-R, R, 6)) {
    el("line", { x1: X(t), x2: X(t), y1: Y(R), y2: Y(-R) }, g); el("line", { x1: X(-R), x2: X(R), y1: Y(t), y2: Y(t) }, g);
    el("text", { x: X(t), y: H - 10, "text-anchor": "middle" }, svg).textContent = Math.abs(t);
    el("text", { x: X(-R) - 4, y: Y(t) + 3, "text-anchor": "end" }, svg).textContent = Math.abs(t);
  }
  if (env) el("rect", { x: X(-env.w / 2), y: Y(env.h / 2), width: env.w * sc, height: env.h * sc, fill: "none",
    stroke: css("--warn"), "stroke-dasharray": "6 4", "stroke-width": 1.2 }, svg);
  el("text", { x: X(R), y: H - 1, "text-anchor": "end" }, svg).textContent = "width mm";
  const layer = el("g", {}, svg);
  return { svg, layer, X, Y };
}
function mouthPath(m, X, Y) { return m && m.length ? m.map(([x, y], i) => (i ? "L" : "M") + X(x).toFixed(1) + "," + Y(y).toFixed(1)).join("") + "Z" : ""; }
function drawFront(Fr, f, ghosts, bestF) {
  Fr.layer.innerHTML = "";
  ghosts.slice().reverse().forEach((g, i) => el("path", { d: mouthPath(g.geo.mouth, Fr.X, Fr.Y), fill: "none",
    stroke: css("--muted"), "stroke-opacity": 0.15 + 0.12 * i }, Fr.layer));
  if (bestF && bestF !== f && bestF.geo)
    el("path", { d: mouthPath(bestF.geo.mouth, Fr.X, Fr.Y), fill: "none", stroke: css("--best"), "stroke-dasharray": "4 3" }, Fr.layer);
  if (f.geo && f.geo.mouth) el("path", { d: mouthPath(f.geo.mouth, Fr.X, Fr.Y), fill: f.ok ? css("--best") : css("--bad"),
    "fill-opacity": 0.25, stroke: f.ok ? css("--best") : css("--bad"), "stroke-width": 1.6 }, Fr.layer);
}

// ── score chart with playhead ─────────────────────────────────────────────────────────────────────
function scoreFrame(svg, F) {
  svg.innerHTML = "";
  const W = Math.max(280, Math.round(svg.getBoundingClientRect().width || 460)), H = 230;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("width", W); svg.setAttribute("height", H);
  const m = { l: 40, r: 10, t: 18, b: 26 }, pw = W - m.l - m.r, ph = H - m.t - m.b;
  const ok = F.filter(f => f.ok).map(f => f.j);
  const best = F.map(f => f.best_j).filter(v => v != null);
  const lo = 0, hi = Math.max(...(best.length ? [best[0] * 1.5] : [1]), Math.min(Math.max(...ok, 1), (best[0] || 1) * 3));
  const X = i => m.l + (F.length > 1 ? i / (F.length - 1) : 0) * pw, Y = v => m.t + ph - (Math.min(v, hi) - lo) / (hi - lo) * ph;
  const g = el("g", { class: "grid" }, svg);
  for (const t of niceTicks(lo, hi, 4)) { el("line", { x1: m.l, x2: m.l + pw, y1: Y(t), y2: Y(t) }, g);
    el("text", { x: m.l - 5, y: Y(t) + 3, "text-anchor": "end" }, svg).textContent = t; }
  for (const t of niceTicks(0, F.length, 5)) el("text", { x: X(Math.min(t, F.length - 1)), y: H - 8, "text-anchor": "middle" }, svg).textContent = t;
  el("text", { x: m.l - 5, y: 11, "text-anchor": "end" }, svg).textContent = "score";
  el("text", { x: m.l + pw, y: H - 1, "text-anchor": "end" }, svg).textContent = "evaluation";
  F.forEach((f, i) => {
    if (f.ok) el("circle", { cx: X(i), cy: Y(f.j), r: 1.6, fill: css("--muted"), opacity: f.j > hi ? 0.25 : 0.45 }, svg);
    else el("line", { x1: X(i), x2: X(i), y1: m.t + ph, y2: m.t + ph - 6, stroke: css("--bad"), "stroke-opacity": 0.6 }, svg);
  });
  const pts = F.map((f, i) => f.best_j == null ? null : [X(i), Y(f.best_j)]).filter(Boolean);
  if (pts.length) el("path", { d: pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + "," + p[1].toFixed(1)).join(""),
    fill: "none", stroke: css("--best"), "stroke-width": 2 }, svg);
  const ph1 = el("line", { y1: m.t, y2: m.t + ph, stroke: css("--seed"), "stroke-width": 1.5 }, svg);
  const dot = el("circle", { r: 4, fill: css("--seed") }, svg);
  return { playhead(i) { const x = X(i); ph1.setAttribute("x1", x); ph1.setAttribute("x2", x);
    const f = F[i]; if (f.ok) { dot.setAttribute("cx", x); dot.setAttribute("cy", Y(f.j)); dot.style.display = ""; } else dot.style.display = "none"; } };
}
