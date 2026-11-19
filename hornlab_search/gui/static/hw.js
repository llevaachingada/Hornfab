// hw.js — hornlab-search GUI   AGPL-3.0-or-later
//
// Horn + woofer system views (G0, docs/research/system_woofer_2026-11-18/GUI_SYSTEM_PLAN_2026-11-19.md):
//   #/hw/cases                 ledger of every staged / solved / refused Boundary Lab case
//   #/hw/case/<exp>/<case>     one case: placeholders, geometry, per-channel bases, polars, provenance
//   #/hw/readiness             risk register R1-R17 + open owner decisions
//
// Read-only. Every number comes from /api/hw/* (Python readers); JS only formats and plots.
// Channels are never summed here: the woofer basis is Pa per 2.83 V, the horn basis Pa per 1 m/s,
// and no calibration policy exists yet (risk R1).

import { chart, polarMap, logTicks, niceTicks, css, el, NS, wireScrollHints } from "./charts.js";

const esc = s => (s == null ? "–" : String(s))
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

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
const caseHref = key => "#/hw/case/" + key.split("/").map(encodeURIComponent).join("/");
const num = (v, d = 0) => (v == null || !isFinite(v)) ? "–" : Number(v).toFixed(d);

// Plain-English glosses for the tokens the system package records. Shown next to the verbatim token.
const GLOSS = {
  DEMO_MOTOR: "Boundary Lab's default motor, not a real driver's Thiele/Small parameters.",
  DEMO_TRANSDUCER_SHAPE: "Default cone, surround and dust-cap geometry; the real driver's shape is not modelled.",
  IDEAL_HORN_SOURCE: "The horn throat is driven at a fixed 1 m/s; there is no compression-driver model.",
  LF_NOT_SOLVED: "No data at low frequencies, so the box tuning cannot be seen.",
  CONVERGENCE_UNCHECKED: "Only one mesh was solved; how much the answer moves with a finer mesh is unknown.",
  BODY_CLEARANCE_VIOLATION: "The horn and the box are closer than 1 mm or overlap. Do not solve.",
  BODY_CLEARANCE_UNPROVEN: "The gap between horn and box could not be proven; treated as unsafe.",
  MANIFEST_INTEGRITY_FAILED: "The case's manifest no longer matches its own checksum.",
  UNDECLARED: "Not in the readiness registry, so no fidelity label is claimed.",
};
const tokenKey = t => String(t).split(/[\[:]/)[0];
const glossFor = t => GLOSS[tokenKey(t)] || (String(t).startsWith("STAGE_FAILED")
  ? "Staging stopped before a usable project existed (Boundary Lab refusal or adapter check)." : "");

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
  return `<span class="pill ${cls}" title="${esc(f === "UNDECLARED" ? GLOSS.UNDECLARED : "Declared in readiness.yaml")}">${esc(f)}</span>`;
}

function roleBadge(label, v) {
  if (!v) return "";
  const cls = v === "real" ? "good" : v === "demo" ? "warn" : "";
  return `<span class="pill ${cls}" title="${esc(label)}">${esc(label)}: ${esc(v)}</span>`;
}

function clearancePill(c) {
  if (!c) return `<span class="muted">–</span>`;
  const cls = c.status === "PASS" ? "good" : c.status === "NOT_CHECKED" ? "" : "bad";
  const gap = c.aabb_gap_m != null ? ` ${num(c.aabb_gap_m * 1000, 1)} mm` : "";
  const src = c.source === "replay" ? " (replayed)" : "";
  const tip = c.status === "PASS"
    ? "Proven minimum gap (bounding-box lower bound)" + src
    : (GLOSS[c.status] || c.reason || "") + src;
  return `<span class="pill ${cls}" title="${esc(tip)}">${esc(c.status === "PASS" ? "gap" : c.status)}${esc(c.status === "PASS" ? gap : "")}</span>`;
}

function tokenChips(tokens) {
  return (tokens || []).map(t =>
    `<span class="pill bad" title="${esc(glossFor(t))}">${esc(t.length > 70 ? t.slice(0, 67) + "…" : t)}</span>`).join(" ");
}

function boxText(b) {
  if (!b) return "–";
  return `${num(b.width_mm)}×${num(b.height_mm)}×${num(b.depth_mm)} mm · port ${num(b.port_area_cm2, 0)} cm²`;
}

// ── Cases ledger ─────────────────────────────────────────────────────────────

const FILTERS = [
  ["bl", "Boundary Lab cases"], ["declared", "In registry"], ["solved", "Solved"],
  ["problems", "Problems"], ["all", "Everything"],
];

export async function viewHwCases(root, query = "") {
  root.innerHTML = `<p class="muted">Loading cases…</p>`;
  let data;
  try { data = await api("/api/hw/cases"); } catch (e) { root.innerHTML = errBanner(e.message); return; }
  const params = new URLSearchParams(query);
  let filter = params.get("f") || "bl";
  const c = data.counts || {};
  const kpi = (label, v, cls = "") => `<div class="kpi"><span>${esc(label)}</span><b class="${cls}">${esc(v ?? 0)}</b></div>`;

  root.innerHTML = `
    <div class="section-header"><h1>Horn + woofer cases</h1></div>
    <p class="muted" style="max-width:72ch">Every Boundary Lab case on disk under <code>${esc(data.store)}</code>.
      Status, box and gap come from the case files. Fidelity, motor and driver shape come from
      <code>${esc(data.registry)}</code>; cases missing from it show <b>UNDECLARED</b>. Nothing here sums the
      woofer and horn channels.</p>
    ${data.registry_error ? errBanner(data.registry_error) : ""}
    ${(data.declared_missing || []).length ? `<div class="alert warn" role="alert">Registry cases missing on disk:
      ${data.declared_missing.map(m => `<code>${esc(m.key)}</code>`).join(", ")}</div>` : ""}
    <div class="kpis">${kpi("Solved", c.solved, "good")}${kpi("Staged", c.staged)}${kpi("Stage failed", c.stage_failed, c.stage_failed ? "bad" : "")}${kpi("Solve failed", c.solve_failed, c.solve_failed ? "bad" : "")}</div>
    <div class="btn-row" role="group" aria-label="Filter cases" style="margin:14px 0 8px">
      ${FILTERS.map(([k, l]) => `<button class="btn${k === filter ? " primary" : ""}" data-f="${k}" aria-pressed="${k === filter}">${esc(l)}</button>`).join("")}
      <a class="btn" href="#/hw/readiness" style="margin-left:auto">Readiness →</a>
    </div>
    <div class="tbl-wrap" id="hw-table"></div>
    ${data.fidelity_note ? `<p class="muted" style="max-width:72ch;font-size:0.82rem">${esc(data.fidelity_note)}</p>` : ""}`;

  const draw = () => {
    const rows = data.cases.filter(r =>
      filter === "all" ? true :
      filter === "bl" ? r.family === "bl_case" :
      filter === "declared" ? r.declared :
      filter === "solved" ? r.state === "solved" :
      filter === "problems" ? (r.tokens || []).length > 0 || /failed/.test(r.state) : true);
    const body = rows.map(r => {
      const solve = r.solve && r.solve.fmin_hz != null ? `${num(r.solve.fmin_hz)}–${num(r.solve.fmax_hz)} Hz` : "–";
      const horn = r.horn ? `${esc((r.horn.translation_mm || [])[2] ?? "–")} mm ${clearancePill(r.clearance)}` : `<span class="muted">vented only</span>`;
      return `<tr class="clickable" data-key="${esc(r.key)}" tabindex="0">
        <td>${esc(r.ref || "")}</td>
        <td><a href="${caseHref(r.key)}">${esc(r.experiment)}</a><br><small class="muted">${esc(r.case)}</small></td>
        <td style="white-space:normal;min-width:180px">${esc(r.gate || "")}${r.note ? `<br><small class="warn-text">${esc(r.note)}</small>` : ""}</td>
        <td>${statePill(r)}</td>
        <td>${roleBadge("motor", r.motor)}<br>${roleBadge("shape", r.transducer_shape)}</td>
        <td>${esc(boxText(r.box))}</td>
        <td>${horn}</td>
        <td>${esc(solve)}</td>
        <td>${fidelityBadge(r.fidelity)}</td>
        <td style="white-space:normal;max-width:280px">${tokenChips(r.tokens)}</td>
      </tr>`;
    }).join("");
    const t = root.querySelector("#hw-table");
    t.innerHTML = rows.length ? `<table>
      <thead><tr><th>Ref</th><th>Case</th><th>Gate</th><th>State</th><th>Motor / shape</th><th>Box</th>
        <th>Horn offset / gap</th><th>Solved band</th><th>Fidelity</th><th>Tokens</th></tr></thead>
      <tbody>${body}</tbody></table>` : `<p class="muted">No cases match this filter.</p>`;
    t.querySelectorAll("tr[data-key]").forEach(tr => {
      const go = () => { location.hash = caseHref(tr.dataset.key); };
      tr.addEventListener("click", e => { if (!e.target.closest("a")) go(); });
      tr.addEventListener("keydown", e => { if (e.key === "Enter") go(); });
    });
    wireScrollHints(root);
  };
  root.querySelectorAll("button[data-f]").forEach(b => b.addEventListener("click", () => {
    filter = b.dataset.f;
    root.querySelectorAll("button[data-f]").forEach(x => {
      x.classList.toggle("primary", x === b); x.setAttribute("aria-pressed", String(x === b));
    });
    history.replaceState(null, "", "#/hw/cases" + (filter === "bl" ? "" : "?f=" + filter));
    draw();
  }));
  draw();
}

// ── Case detail ──────────────────────────────────────────────────────────────

export async function viewHwCase(root, key) {
  root.innerHTML = `<p class="muted">Loading case…</p>`;
  let d;
  try { d = await api("/api/hw/case/" + key.split("/").map(encodeURIComponent).join("/")); }
  catch (e) { root.innerHTML = `<p><a href="#/hw/cases">← All cases</a></p>` + errBanner(e.message); return; }
  const r = d.row;
  const run = d.run;
  const pair = r.pair_with ? `<a class="btn" href="${caseHref(r.pair_with)}">Paired case →</a>` : "";
  const parent = r.parent ? `<a class="btn" href="${caseHref(r.parent)}">Staged project →</a>` : "";

  root.innerHTML = `
    <p><a href="#/hw/cases">← All cases</a></p>
    <div class="section-header"><h1>${esc(r.ref && r.ref !== "-" ? r.ref + " · " : "")}${esc(r.gate || r.experiment)}</h1></div>
    <p class="muted"><code>${esc(r.key)}</code> · ${esc(r.kind || "no manifest")}</p>
    <div class="pill-row" style="margin:8px 0">${statePill(r)} ${fidelityBadge(r.fidelity)}
      ${roleBadge("motor", r.motor)} ${roleBadge("shape", r.transducer_shape)}
      ${r.horn ? clearancePill(r.clearance) : ""} ${r.integrity !== "ok" ? `<span class="pill bad" title="${esc(r.integrity)}">manifest ${esc(r.integrity.split(":")[0])}</span>` : ""}</div>
    ${r.note ? `<div class="alert warn" role="note">${esc(r.note)}</div>` : ""}
    ${d.refusal ? `<div class="alert error" role="alert"><b>Staging failed (${esc(d.refusal.error_type)}):</b> ${esc(d.refusal.error)}</div>` : ""}
    ${(r.tokens || []).length ? `<div class="pill-row" style="margin:8px 0">${tokenChips(r.tokens)}</div>` : ""}
    ${placeholderBlock(d.placeholders)}
    <div class="btn-row" style="margin:10px 0">${parent}${pair}</div>
    <div class="grid2" style="gap:16px;align-items:start">
      <section class="card"><h2 style="margin-top:0">Geometry</h2><div id="hw-geo"></div></section>
      <section class="card"><h2 style="margin-top:0">Box and horn</h2>${boxTable(r, d)}</section>
    </div>
    <section class="card" style="margin-top:16px" id="hw-bases"><h2 style="margin-top:0">Per-channel response</h2></section>
    <section class="card" style="margin-top:16px" id="hw-polars"><h2 style="margin-top:0">Polar cuts</h2></section>
    <section class="card" style="margin-top:16px"><h2 style="margin-top:0">Provenance</h2>${provenanceBlock(d)}</section>`;

  drawGeometry(root.querySelector("#hw-geo"), d.geometry, r);
  const bases = root.querySelector("#hw-bases");
  const polars = root.querySelector("#hw-polars");
  if (!run) {
    const why = r.state === "staged" ? "Staged and validated, not solved." : "No solved run in this case.";
    bases.insertAdjacentHTML("beforeend", `<p class="muted">${esc(why)}</p>`);
    polars.remove();
  } else if (run.error) {
    bases.insertAdjacentHTML("beforeend", errBanner("Result reader refused: " + run.error));
    polars.remove();
  } else {
    await drawBases(bases, key, run, d.observation_caption);
    await drawPolars(polars, key, run, d.observation_caption);
  }
  wireScrollHints(root);
}

function placeholderBlock(items) {
  if (!items || !items.length) return "";
  return `<div class="alert warn" role="note" style="margin:8px 0"><b>Placeholders in this case</b>
    <ul style="margin:6px 0 0 18px;padding:0">${items.map(p =>
      `<li><code>${esc(p.token)}</code> ${esc(p.text)}</li>`).join("")}</ul></div>`;
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
    pairs.push(["Port", esc(`${num(b.port_area_cm2, 1)} cm², length ${num(b.port_length_mm, 1)} mm, y ${num(b.port_y_mm, 1)} mm, flare ${b.port_nfr ?? "–"}`)]);
    pairs.push(["Mesh size", esc(`${num(b.mesh_size_mm)} mm / detail ${num(b.detail_size_mm)} mm`)]);
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
    pairs.push(["Real driver geometry", `${g.complete ? "complete" : `<span class="warn-text">incomplete</span>`}: ${esc(Object.keys(g.refusals || {}).join(", ") || "–")} unavailable`]);
  }
  return kvTable(pairs);
}

// Two to-scale elevations (front x-y, side z-y), mm, in one SVG.
function drawGeometry(host, g, r) {
  if (!g) { host.innerHTML = `<p class="muted">No staged meshes on disk for this case.</p>`; return; }
  const [blo, bhi] = g.box_bbox_mm;
  const hb = g.horn_bbox_mm;
  const lo = hb ? blo.map((v, i) => Math.min(v, hb[0][i])) : blo;
  const hi = hb ? bhi.map((v, i) => Math.max(v, hb[1][i])) : bhi;
  const W = Math.max(320, host.clientWidth || 520), pad = 26, gapX = 34;
  const frontW = hi[0] - lo[0], sideW = hi[2] - lo[2], tall = hi[1] - lo[1];
  const s = Math.min((W - 2 * pad - gapX) / (frontW + sideW), 360 / tall);
  const H = tall * s + 2 * pad + 14;
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("width", "100%");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Front and side elevations of the box and horn, to scale");
  const ink = css("--ink"), muted = css("--muted"), accent = css("--accent") || "#2a78d6";
  const bad = css("--bad"), good = css("--good");
  const Y = y => pad + 14 + (hi[1] - y) * s;
  const FX = x => pad + (x - lo[0]) * s;
  const ox = pad + frontW * s + gapX;
  const SX = z => ox + (z - lo[2]) * s;
  const label = (x, y, t, anchor = "start", col = muted) => {
    const e = el("text", { x, y, "text-anchor": anchor, style: `fill:${col};font-size:11px` }, svg); e.textContent = t;
  };
  label(pad, 12, "Front (x–y)"); label(ox, 12, "Side (z–y), front face →");
  // box
  el("rect", { x: FX(blo[0]), y: Y(bhi[1]), width: (bhi[0] - blo[0]) * s, height: (bhi[1] - blo[1]) * s,
    fill: "none", stroke: ink, "stroke-width": 1.4 }, svg);
  el("rect", { x: SX(blo[2]), y: Y(bhi[1]), width: (bhi[2] - blo[2]) * s, height: (bhi[1] - blo[1]) * s,
    fill: "none", stroke: ink, "stroke-width": 1.4 }, svg);
  // driver + port cutouts on the front view (source parameters; centred at x = 0)
  const b = r.box;
  if (b && b.driver_diameter_mm) {
    el("circle", { cx: FX(0), cy: Y(b.driver_y_mm), r: b.driver_diameter_mm / 2 * s, fill: "none",
      stroke: muted, "stroke-dasharray": "4 3" }, svg);
    label(FX(0), Y(b.driver_y_mm) - b.driver_diameter_mm / 2 * s - 3, `driver Ø${num(b.driver_diameter_mm)}`, "middle");
  }
  if (b && b.port_area_cm2) {
    const pr = Math.sqrt(b.port_area_cm2 * 100 / Math.PI);
    el("circle", { cx: FX(0), cy: Y(b.port_y_mm), r: pr * s, fill: "none", stroke: muted, "stroke-dasharray": "2 2" }, svg);
    label(FX(0), Y(b.port_y_mm) + pr * s + 12, "port", "middle");
  }
  const poly = (pts, X, col) => el("polygon", { points: pts.map(p => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(" "),
    fill: col, "fill-opacity": 0.18, stroke: col, "stroke-width": 1.4 }, svg);
  if (g.horn_front) poly(g.horn_front, FX, accent);
  if (g.horn_side) poly(g.horn_side, SX, accent);
  // gap dimension on the side view
  const c = r.clearance;
  if (hb && c && c.status) {
    const ok = c.status === "PASS";
    const z0 = bhi[2], z1 = hb[0][2], yy = Math.min(bhi[1], hb[1][1]) + 0;
    el("line", { x1: SX(z0), x2: SX(z1), y1: Y(yy) - 8, y2: Y(yy) - 8, stroke: ok ? good : bad, "stroke-width": 2 }, svg);
    label(SX(Math.max(z0, z1)) + 4, Y(yy) - 4, ok ? `gap ${num(c.aabb_gap_m * 1000, 1)} mm` : `${c.status}`, "start", ok ? good : bad);
  }
  if (g.horn_missing) label(pad, H - 4, g.horn_missing);
  // scale bar: 100 mm
  el("line", { x1: pad, x2: pad + 100 * s, y1: H - 6, y2: H - 6, stroke: muted, "stroke-width": 2 }, svg);
  label(pad + 100 * s + 4, H - 2, "100 mm");
  host.innerHTML = "";
  host.appendChild(svg);
  host.insertAdjacentHTML("beforeend", `<p class="muted" style="font-size:0.8rem;margin:6px 0 0">Outlines are convex hulls of the
    stored meshes in the Boundary Lab project frame. Driver and port circles are drawn from the source parameters.</p>`);
}

function unitLabel(ex) {
  return ex.per_input === "V_rms" ? "dB SPL per 2.83 V" : ex.per_input === "normal_velocity_mps" ? "dB SPL per 1 m/s" : "dB SPL per " + (ex.per_input || "?");
}
function channelName(ex) {
  return ex.per_input === "V_rms" ? "Woofer (voltage port)" : ex.per_input === "normal_velocity_mps" ? "Horn (ideal velocity source)" : ex.id;
}

async function drawBases(host, key, run, caption) {
  const probes = run.domains.filter(x => x.kind === "point_probe");
  if (!probes.length) { host.insertAdjacentHTML("beforeend", `<p class="muted">No point probes in this run.</p>`); return; }
  const fmin = Math.min(...run.frequencies_hz), fmax = Math.max(...run.frequencies_hz);
  host.insertAdjacentHTML("beforeend", `
    <p class="muted" style="max-width:80ch">Each channel is plotted on its own axis, per its own reference input. They are
      <b>not summed</b>: the woofer is referenced to 2.83 V and the horn to 1 m/s, and there is no calibration policy yet (R1).
      Shaded: below ${num(fmin)} Hz nothing was solved.</p>
    <label>Probe <select id="hw-probe">${probes.map(p =>
      `<option value="${esc(p.id)}">${esc(p.probe_id || p.id)} (${num(p.distance_m, 2)} m)</option>`).join("")}</select></label>
    <div class="grid2" id="hw-basis-charts" style="gap:12px;margin-top:10px"></div>
    <p class="muted" style="font-size:0.8rem">${esc(caption)}</p>`);
  const sel = host.querySelector("#hw-probe"), box = host.querySelector("#hw-basis-charts");
  const xlim = [20, Math.max(5000, fmax * 1.2)];
  const draw = async () => {
    box.innerHTML = `<p class="muted">Loading…</p>`;
    let b;
    try { b = await api(`/api/hw/basis/${key.split("/").map(encodeURIComponent).join("/")}?domain=${encodeURIComponent(sel.value)}`); }
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
      chart(mag, { W: 420, H: 200, xlog: true, xlim, ylim: [ylo, yhi], yticks: niceTicks(ylo, yhi, 5),
        xlabel: "Hz", ylabel: unitLabel(ex), series: [{ pts, color, w: 2 }, { pts, color, dots: true, r: 2.2 }],
        unscored: [{ x0: xlim[0], x1: fmin, label: "not solved" }],
        ariaLabel: `${channelName(ex)} level at ${sel.value}` });
      chart(ph, { W: 420, H: 150, xlog: true, xlim, ylim: [-180, 180], yticks: [-180, -90, 0, 90, 180],
        xlabel: "Hz", ylabel: "phase (deg, wrapped)",
        series: [{ pts: b.frequencies_hz.map((f, k) => [f, ex.phase_deg[k]]), color, dots: true, r: 2.2 }],
        unscored: [{ x0: xlim[0], x1: fmin }],
        ariaLabel: `${channelName(ex)} phase at ${sel.value}` });
    });
  };
  sel.addEventListener("change", draw);
  await draw();
}

async function drawPolars(host, key, run, caption) {
  const cuts = run.domains.filter(x => x.kind === "polar_observation");
  if (!cuts.length) { host.remove(); return; }
  host.insertAdjacentHTML("beforeend", `<p class="muted" style="max-width:80ch">Level relative to each channel's own 0° value at each
    frequency, −90° to +90°. Low frequencies at the bottom. ${esc(caption)}</p><div class="grid2" id="hw-polar-grid" style="gap:12px"></div>`);
  const grid = host.querySelector("#hw-polar-grid");
  const key2 = key.split("/").map(encodeURIComponent).join("/");
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
      // polarMap draws once at the measured width (no resize redraw), so the SVG must already be
      // full-width when measured; an unsized SVG measures 300 px and is then CSS-stretched.
      svg.dataset.chart = "1"; svg.style.width = "100%";
      cell.appendChild(svg); grid.appendChild(cell);
      const rows = ex.rel_db.map(row => keep.map(([, i]) => row[i] == null ? null : Math.max(-40, Math.min(0, row[i]))));
      polarMap(svg, rows, angles, b.frequencies_hz, { H: 220 });
    }
  }
}

function provenanceBlock(d) {
  const r = d.row, run = d.run, pairs = [];
  pairs.push(["Manifest integrity", r.integrity === "ok" ? `<span class="pill good">ok</span>` : `<span class="pill bad">${esc(r.integrity)}</span>`]);
  const h = d.highlights || {};
  if (h.authorized_by) pairs.push(["Authorized by", esc(h.authorized_by)]);
  if (h.project_sha256) pairs.push(["Project sha256", `<code>${esc(h.project_sha256)}</code>`]);
  if (d.validate) pairs.push(["BL validate", esc(`rc ${d.validate.returncode} · valid ${d.validate.valid}`)]);
  if (d.bl_root) pairs.push(["Boundary Lab", esc(`${d.bl_root.version || "?"} @ ${(d.bl_root.git_head || "").slice(0, 12) || "?"} (${d.bl_root.path || ""})`)]);
  if (run && !run.error) {
    const p = run.provenance || {};
    pairs.push(["Solve", esc(`${p.backend_id} · ${p.solve_kind} · ${p.status} · ${run.frequencies_hz.length} freqs`)]);
    pairs.push(["Phasor", esc(`${p.phasor_convention} → ${p.phasor_conversion}`)]);
    pairs.push(["Geometry identity", `<code>${esc(p.source_geometry_hash)}</code>`]);
    pairs.push(["Run manifest sha256", `<code>${esc(p.manifest_sha256)}</code>`]);
    if (run.solver_options) pairs.push(["Solver options", `<code style="white-space:pre-wrap">${esc(JSON.stringify(run.solver_options))}</code>`]);
    pairs.push(["Started / finished", esc(`${run.started_at_utc || "?"} → ${run.finished_at_utc || "?"}`)]);
    const dq = run.data_quality || {};
    pairs.push(["Claims allowed", esc((dq.claims_allowed || []).join(", "))]);
    pairs.push(["Claims refused", esc((dq.claims_refused || []).join(", "))]);
  }
  pairs.push(["Files", `<code style="white-space:normal">${esc((d.files || []).join("  "))}</code>`]);
  return kvTable(pairs);
}

// ── Readiness board ──────────────────────────────────────────────────────────

export async function viewHwReadiness(root) {
  root.innerHTML = `<p class="muted">Loading…</p>`;
  let d;
  try { d = await api("/api/hw/readiness"); } catch (e) { root.innerHTML = errBanner(e.message); return; }
  const lvl = { CRITICAL: "bad", HIGH: "warn", MEDIUM: "", LOW: "" };
  const st = { open: "", in_progress: "warn", closed: "good" };
  const c = d.counts || {};
  root.innerHTML = `
    <p><a href="#/hw/cases">← All cases</a></p>
    <div class="section-header"><h1>Horn + woofer readiness</h1></div>
    <p class="muted" style="max-width:72ch">From <code>${esc(d.registry)}</code> (updated ${esc(d.updated)}), which mirrors
      <code>${esc(d.handoff)}</code>. Case counts are live from disk: ${esc(c.solved ?? 0)} solved, ${esc(c.staged ?? 0)} staged,
      ${esc(c.stage_failed ?? 0)} stage failed, ${esc(c.solve_failed ?? 0)} solve failed.</p>
    ${d.registry_error ? errBanner(d.registry_error) : ""}
    <h2>Open owner decisions</h2>
    <div class="tbl-wrap"><table><thead><tr><th>#</th><th>Decision</th><th>Recommendation</th><th>Status</th></tr></thead><tbody>
      ${d.decisions.map(x => `<tr><td>${esc(x.id)}</td><td style="white-space:normal">${esc(x.question)}</td>
        <td style="white-space:normal">${esc(x.recommendation)}</td><td><span class="pill">${esc(x.status)}</span></td></tr>`).join("")}
    </tbody></table></div>
    <h2>Risk register</h2>
    <div class="tbl-wrap"><table><thead><tr><th>Risk</th><th>Level</th><th>Status</th><th>What</th><th>Closes under</th><th>Blocked by</th><th>Evidence</th></tr></thead><tbody>
      ${d.risks.map(x => `<tr><td>${esc(x.id)}</td><td><span class="pill ${lvl[x.level] || ""}">${esc(x.level)}</span></td>
        <td><span class="pill ${st[x.status] || ""}">${esc(String(x.status).replace("_", " "))}</span></td>
        <td style="white-space:normal;min-width:220px">${esc(x.title)}</td><td>${esc(x.wp)}</td>
        <td style="white-space:normal">${esc(x.blocked_by || "")}</td>
        <td style="white-space:normal;max-width:320px"><small>${esc(x.evidence)}</small></td></tr>`).join("")}
    </tbody></table></div>`;
  wireScrollHints(root);
}
