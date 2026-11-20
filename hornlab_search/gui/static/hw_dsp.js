// hw_dsp.js — hornlab-search GUI   AGPL-3.0-or-later
//
// Horn + woofer · crossover preview, locked (P7 —
// docs/research/system_woofer_2026-11-18/GUI_COMPLETION_HANDOFF_2026-11-19.md §5.9;
// GUI_SENIOR_REVIEW_2026-11-20.md §4 step 13):
//   #/hw/case/<exp>/<case>/crossover
//
// POST /api/hw/dsp-preview {case:"<exp>/<case>"} is the only data source. The response carries the
// committed spec's DSP point/ranges, per-channel filtered SPL and phase bases, the
// validate_dsp_point verdicts, the locked "System sum" record and the permanent captions.
//
// This page applies no acoustics in JS: it formats and plots. It draws each channel on its own
// chart and axis, never overlays them and never produces a summed/combined curve. The controls are
// shown from the payload's spec defaults but disabled; editing and summing wait for owner decision
// 3 (calibration policy, risk R1).

import { chart, niceTicks, css, NS } from "./charts.js";
import { tip } from "./glossary.js";

const esc = s => (s == null ? "—" : String(s))
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

function brk(s) {
  return esc(s).replace(/([_\-./])/g, "$1<wbr>");
}

const num = (v, d = 2) => (v == null || !isFinite(v)) ? "—" : Number(v).toFixed(d);
const isFiniteNum = v => v != null && isFinite(Number(v));

const encKey = key => String(key).split("/").map(encodeURIComponent).join("/");
const caseHref = key => "#/hw/case/" + encKey(key);

const hashQuery = () => new URLSearchParams((location.hash.split("?")[1] || ""));
const readQuery = (q) => {
  if (typeof q !== "string" || !q) return hashQuery();
  return new URLSearchParams(q.replace(/^[#/]+/, "").replace(/^\?/, ""));
};

function skel(root, msg = "") {
  root.setAttribute("aria-busy", "true");
  root.innerHTML = `<div class="stack" style="gap:18px;opacity:0.6" aria-hidden="true">
    <div class="skeleton-block" style="height:2.2rem;width:min(260px,60%)"></div>
    <div class="skeleton-block" style="height:1rem;width:min(400px,80%)"></div>
    <div class="skeleton-block" style="height:180px"></div>
  </div>${msg ? `<p class="sr-only" role="status">${esc(msg)}…</p>` : ""}`;
}
const busyDone = root => root.removeAttribute("aria-busy");

async function apiPost(path, body) {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let msg = r.status + "";
    try { msg += " " + ((await r.json()).error || ""); } catch { /* not JSON */ }
    throw new Error(msg);
  }
  return r.json();
}

const errBanner = msg => `<div class="alert error" role="alert"><b>Error:</b> ${esc(msg)}</div>`;

function pageHead({ eyebrow, title, id, pills = "" }) {
  return `<div>
    <div class="eyebrow">${esc(eyebrow)}</div>
    <h2>${esc(title)}</h2>
    <p id="hwd-head-id" class="mono muted" style="font-size:0.78rem;overflow-wrap:anywhere">${brk(id || "")}</p>
    ${pills ? `<div class="pill-row" style="margin:8px 0 0">${pills}</div>` : ""}
  </div>`;
}

const CHANNEL_NAME = { woofer: "Woofer", horn: "Horn" };
const CHANNEL_REF = {
  woofer: "Pa per 2.83 V",
  horn: "Pa per 1 m/s",
};

// ── Scoped layout styles (this module only; app.css untouched) ──────────────

const STYLE_ID = "hw-dsp-style";
const DSP_CSS = `
#hw-dsp-view { min-width:0; }
#hw-dsp-view [hidden] { display:none !important; }
#hw-dsp-view .hint { font-size:0.8rem; color:var(--muted); line-height:1.45; }
#hw-dsp-view code { overflow-wrap:anywhere; }
#hw-dsp-view .form-grid > * { min-width:0; }
#hw-dsp-view .form-grid input, #hw-dsp-view .form-grid select {
  min-width:0; max-width:100%; }
#hw-dsp-view input:disabled, #hw-dsp-view select:disabled {
  background:var(--bg); color:var(--label); }
#hw-dsp-view .form-grid label { white-space:normal; }

.hwd-phase-row { display:flex; flex-wrap:wrap; gap:8px 12px; align-items:center; min-width:0; }
.hwd-phase-row .form-label { margin:0; }
#hw-dsp-view [data-phase][aria-pressed="true"] {
  background:var(--accent-soft); color:var(--accent); border-color:var(--accent); font-weight:600; }

.hwd-chart { min-width:0; }
.hwd-chart svg { max-width:100%; height:auto; }

.hwd-peq { display:grid; grid-template-columns:max-content repeat(3,minmax(0,1fr));
  gap:6px 8px; align-items:center; min-width:0; }
.hwd-peq .hwd-peq-h { font-family:var(--f-mono); font-size:0.68rem; color:var(--label);
  text-transform:uppercase; letter-spacing:0.04em; overflow-wrap:anywhere; }
.hwd-peq input { width:100%; min-width:0; max-width:100%; }

.hwd-table { width:100%; border-collapse:collapse; font-size:0.8rem; min-width:560px; }
.hwd-table th, .hwd-table td {
  padding:4px 6px; border-bottom:1px solid var(--rule); text-align:left; vertical-align:top;
  overflow-wrap:anywhere; }
.hwd-table th { font-family:var(--f-mono); font-size:0.68rem; color:var(--label);
  text-transform:uppercase; letter-spacing:0.04em; background:var(--surface); position:sticky; top:0; z-index:1; }
.hwd-table td.n, .hwd-table th.n { text-align:right; font-variant-numeric:tabular-nums; }

@media (max-width:700px) {
  .hwd-peq { grid-template-columns:max-content repeat(3,minmax(0,1fr)); }
}
`;

function ensureStyles() {
  if (typeof document === "undefined" || document.getElementById(STYLE_ID)) return;
  const s = document.createElement("style");
  s.id = STYLE_ID;
  s.textContent = DSP_CSS;
  document.head.appendChild(s);
}

// ── chart helpers (plot only; all values arrive from the API) ──────────────

function paddedRange(values) {
  const nums = values.filter(v => v != null && isFinite(Number(v))).map(Number);
  if (!nums.length) return [-1, 1];
  let lo = Math.min(...nums), hi = Math.max(...nums);
  if (hi === lo) { hi = lo + 1; lo -= 1; }
  const pad = (hi - lo) * 0.1;
  return [lo - pad, hi + pad];
}

function drawChart(host, opts) {
  if (!host) return;
  host.innerHTML = "";
  const svg = document.createElementNS(NS, "svg");
  svg.style.width = "100%";
  host.appendChild(svg);
  chart(svg, opts);
}

function channelLabel(c) {
  return CHANNEL_NAME[c.channel] || String(c.channel || "channel");
}

function splChartOpts(c, freqs) {
  const vals = Array.isArray(c.spl_db) ? c.spl_db : [];
  const pts = freqs.map((f, i) => [f, vals[i] == null || !isFinite(vals[i]) ? null : vals[i]]);
  const [lo, hi] = paddedRange(vals);
  const name = channelLabel(c);
  return {
    H: 240, xlog: true,
    xlim: [freqs[0], freqs[freqs.length - 1]],
    ylim: [lo, hi], yticks: niceTicks(lo, hi, 5),
    xlabel: "Hz", ylabel: "dB SPL",
    series: [{ pts, color: css("--accent"), w: 2 }],
    markers: freqs.length <= 40,
    ariaLabel: `${name} filtered SPL in dB SPL per ${c.per_input || "its declared input"}; one channel, not summed.`,
  };
}

function phaseChartOpts(c, freqs, mode) {
  const raw = mode === "unwrapped" ? c.phase_unwrapped_deg : c.phase_deg;
  const vals = Array.isArray(raw) ? raw : [];
  const pts = freqs.map((f, i) => [f, vals[i] == null || !isFinite(vals[i]) ? null : vals[i]]);
  const name = channelLabel(c);
  let lo = -180, hi = 180;
  let yticks = [-180, -90, 0, 90, 180];
  if (mode === "unwrapped") {
    [lo, hi] = paddedRange(vals);
    yticks = niceTicks(lo, hi, 5);
  }
  return {
    H: 240, xlog: true,
    xlim: [freqs[0], freqs[freqs.length - 1]],
    ylim: [lo, hi], yticks,
    xlabel: "Hz", ylabel: "phase (deg)",
    series: [{ pts, color: css("--best"), w: 2 }],
    hlines: [{ y: 0, color: css("--rule"), dash: true }],
    markers: freqs.length <= 40,
    ariaLabel: `${name} filtered phase (${mode}) in degrees; one channel, not summed.`,
  };
}

// ════════════════════════════════════════════════════════════════════════════
// Crossover preview — #/hw/case/<exp>/<case>/crossover
// ════════════════════════════════════════════════════════════════════════════

export async function viewHwDsp(root, exp, caseName, query = "") {
  const key = `${exp}/${caseName}`;
  const route = "#/hw/case/" + encKey(key) + "/crossover";
  const q = readQuery(query);
  const state = { phase: q.get("phase") === "unwrapped" ? "unwrapped" : "wrapped" };
  skel(root, "Loading the crossover preview");
  let r;
  try { r = await apiPost("/api/hw/dsp-preview", { case: key }); }
  catch (e) {
    busyDone(root);
    root.innerHTML = `<div class="stack" style="gap:14px">
      ${pageHead({
        eyebrow: "Horn + woofer · Case · crossover preview",
        title: "Crossover preview (locked)",
        id: key,
        pills: `<span class="pill">per-channel only</span><span class="pill">no system sum</span>`,
      })}
      ${errBanner(e.message)}
      <div class="btn-row"><a class="btn" href="${caseHref(key)}">← Back to the case</a></div>
    </div>`;
    return;
  }
  busyDone(root);
  if (!root.isConnected) return;
  ensureStyles();

  const locked = r && typeof r.locked === "object" ? r.locked : null;
  const dsp = r && r.dsp && typeof r.dsp === "object" ? r.dsp : null;
  const channels = r && Array.isArray(r.channels) ? r.channels : [];
  const freqs = r && Array.isArray(r.frequencies_hz) ? r.frequencies_hz : [];
  const verdicts = r && Array.isArray(r.verdicts) ? r.verdicts : [];
  const captions = r && Array.isArray(r.captions) ? r.captions : [];
  const chartSpecs = [];

  const dec = locked && locked.decision != null ? locked.decision : 3;
  const risk = locked && locked.risk ? locked.risk : "R1";
  const pills = [
    `<span class="pill">per-channel only</span>`,
    `<span class="pill">no system sum</span>`,
    `<span class="pill warn">locked · decision ${esc(dec)} · ${esc(risk)}</span>`,
  ].join("");

  function rangeAttr(rng, which) {
    if (!Array.isArray(rng) || rng.length < 2 || !isFiniteNum(rng[which])) return "";
    return which === 0 ? ` min="${esc(rng[0])}"` : ` max="${esc(rng[1])}"`;
  }

  function controlsHtml(d) {
    const p = d.point || {};
    const rng = d.ranges || {};
    const types = Array.isArray(rng.crossover_types) && rng.crossover_types.length
      ? rng.crossover_types.slice() : (p.crossover_type ? [p.crossover_type] : []);
    if (p.crossover_type && types.indexOf(p.crossover_type) < 0) types.push(p.crossover_type);
    const typeOpts = types.map(t => `<option value="${esc(t)}"${String(t) === String(p.crossover_type) ? " selected" : ""}>${esc(t)}</option>`).join("");
    const pol = Number(p.polarity_woofer) === -1 ? "-1" : "1";
    const peqBands = Array.isArray(p.peq_bands_woofer) ? p.peq_bands_woofer : [];
    const nPeq = Math.max(1, Math.min(2, Number(rng.peq_max_bands) || 2));
    const peqRows = Array.from({ length: nPeq }).map((_, i) => {
      const b = Array.isArray(peqBands[i]) ? peqBands[i] : [];
      const boostMax = isFiniteNum(rng.peq_max_boost_db) ? ` max="${esc(rng.peq_max_boost_db)}"` : "";
      return `<span class="hwd-peq-h">Band ${i + 1}</span>
        <input type="number" disabled value="${esc(b[0] == null ? "" : b[0])}" placeholder="—"
          aria-label="PEQ band ${i + 1} fc (Hz)" title="Locked: owner decision 3 (calibration policy) is open.">
        <input type="number" disabled value="${esc(b[1] == null ? "" : b[1])}" placeholder="—"${boostMax}
          aria-label="PEQ band ${i + 1} gain (dB)" title="Locked: owner decision 3 (calibration policy) is open.">
        <input type="number" disabled value="${esc(b[2] == null ? "" : b[2])}" placeholder="—"
          aria-label="PEQ band ${i + 1} Q" title="Locked: owner decision 3 (calibration policy) is open.">`;
    }).join("");

    return `<section class="card stack" style="gap:12px">
      <div class="fig-head"><h3 style="margin:0;font-size:1rem">DSP point</h3>
        <span class="pill warn">locked · decision ${esc(dec)} · ${esc(risk)}</span></div>
      <p class="hint" role="status">Defaults come from <code>${esc(d.source || "the committed example spec")}</code>.
        Every control is disabled; editing and the system sum wait for owner decision 3
        (${tip("calibration_policy", "calibration policy")}, risk ${esc(risk)}).</p>
      <div class="form-grid">
        <label for="hwd-type">Crossover type</label>
        <div><select id="hwd-type" disabled aria-describedby="hwd-locked-note">${typeOpts}</select></div>

        <label for="hwd-xo">XO frequency (Hz)</label>
        <div><input id="hwd-xo" type="number" disabled value="${esc(p.xo_hz)}"
          ${rangeAttr(rng.xo_hz_range, 0)}${rangeAttr(rng.xo_hz_range, 1)} step="1"
          aria-describedby="hwd-locked-note"></div>

        <label for="hwd-gain-w">Woofer gain (dB)</label>
        <div><input id="hwd-gain-w" type="number" disabled value="${esc(p.gain_db_woofer)}"
          ${rangeAttr(rng.gain_db_range, 0)}${rangeAttr(rng.gain_db_range, 1)} step="0.1"
          aria-describedby="hwd-locked-note"></div>

        <label for="hwd-gain-h">Horn gain (dB)</label>
        <div><input id="hwd-gain-h" type="number" disabled value="${esc(p.gain_db_horn)}"
          ${rangeAttr(rng.gain_db_range, 0)}${rangeAttr(rng.gain_db_range, 1)} step="0.1"
          aria-describedby="hwd-locked-note"></div>

        <label for="hwd-delay">Horn delay (ms, relative to woofer)</label>
        <div><input id="hwd-delay" type="number" disabled value="${esc(p.relative_delay_ms)}"
          ${rangeAttr(rng.relative_delay_ms_range, 0)}${rangeAttr(rng.relative_delay_ms_range, 1)} step="0.1"
          aria-describedby="hwd-locked-note"></div>

        <label for="hwd-polarity">Woofer polarity</label>
        <div><select id="hwd-polarity" disabled aria-describedby="hwd-locked-note">
          <option value="1"${pol === "1" ? " selected" : ""}>Normal (+1)</option>
          <option value="-1"${pol === "-1" ? " selected" : ""}>Inverted (−1)</option>
        </select></div>

        <span class="form-label">PEQ bands</span>
        <div>
          <div class="hwd-peq">
            <span class="hwd-peq-h">Band</span><span class="hwd-peq-h">fc (Hz)</span>
            <span class="hwd-peq-h">Gain (dB)</span><span class="hwd-peq-h">Q</span>
            ${peqRows}
          </div>
          <p class="hint" id="hwd-locked-note" role="status">Up to ${esc(nPeq)} band(s); the default
            point uses ${esc(peqBands.length)}. All controls are read-only until the calibration
            policy is answered.</p>
        </div>
      </div>
    </section>`;
  }

  function phaseToggleHtml() {
    return `<section class="card stack" style="gap:8px">
      <div class="hwd-phase-row">
        <span class="form-label">Phase display</span>
        <div class="btn-row" role="group" aria-label="Phase display">
          <button type="button" class="btn btn-sm" data-phase="wrapped"
            aria-pressed="${state.phase === "wrapped"}">Wrapped</button>
          <button type="button" class="btn btn-sm" data-phase="unwrapped"
            aria-pressed="${state.phase === "unwrapped"}">Unwrapped</button>
        </div>
        <span class="hint" role="status">Applies to every phase chart; the SPL charts do not change.</span>
      </div>
      <p class="hint" role="status">The woofer and horn charts have independent axes. Their dB
        values use different per-input references and are never summed.</p>
    </section>`;
  }

  function channelsHtml(list, gridFreqs) {
    return list.map((c, idx) => {
      const splHost = `hwd-spl-${idx}`;
      const phaseHost = `hwd-phase-${idx}`;
      chartSpecs.push({ id: splHost, kind: "spl", channel: c, freqs: gridFreqs });
      chartSpecs.push({ id: phaseHost, kind: "phase", channel: c, freqs: gridFreqs });
      const pref = c.per_input || "—";
      const refKnown = CHANNEL_REF[c.channel] || "";
      return `<section class="card stack" style="gap:10px">
        <div class="fig-head"><h3 style="margin:0;font-size:1rem">${esc(channelLabel(c))}</h3>
          <span class="pill">${tip("per_input_ref", "per-input reference")}: ${esc(pref)}</span>
          ${c.channel === "horn" ? `<span class="pill">${tip("ideal_horn_source", "ideal horn source")}</span>` : ""}</div>
        <p class="hint" role="status">${esc(refKnown)}${c.reference ? ` · reference ${esc(c.reference)}` : ""}.
          One channel per chart; not summed.</p>
        <div class="grid2">
          <div class="fig">
            <div class="fig-head"><h3>Filtered SPL</h3><span class="muted">${esc(pref)}</span></div>
            <div class="hwd-chart" data-dsp-chart="${splHost}">
              <div class="skeleton-block" style="height:150px"></div>
              <p class="sr-only" role="status">Drawing the SPL chart…</p>
            </div>
            <p class="cap">dB SPL from the API's filtered channel basis; one channel, not summed.</p>
          </div>
          <div class="fig">
            <div class="fig-head"><h3>Filtered phase (<span data-phase-title>${esc(state.phase)}</span>)</h3>
              <span class="muted">${esc(pref)}</span></div>
            <div class="hwd-chart" data-dsp-chart="${phaseHost}">
              <div class="skeleton-block" style="height:150px"></div>
              <p class="sr-only" role="status">Drawing the phase chart…</p>
            </div>
            <p class="cap">Phase in degrees from the API; one channel, not summed.</p>
          </div>
        </div>
      </section>`;
    }).join("");
  }

  root.innerHTML = `<div id="hw-dsp-view" class="stack" style="gap:18px">
    ${pageHead({
      eyebrow: "Horn + woofer · Case · crossover preview",
      title: "Crossover preview (locked)",
      id: key,
      pills,
    })}
    <p class="lede" style="max-width:82ch;margin:0">Per-channel filtered curves from the validated
      analog-prototype filter bank. The woofer (Pa per 2.83 V) and the horn (Pa per 1 m/s) sit on
      their own axes; nothing is summed. The system sum needs a
      ${tip("calibration_policy", "calibration policy")} (owner decision 3, risk R1).</p>
    <div class="btn-row">
      <a class="btn btn-sm" href="${caseHref(key)}">← Back to the case</a>
      <span class="hint" role="status">Story step 7 · read the results; crossover is locked.</span>
    </div>
    ${r && r.probe_id ? `<p class="hint" role="status">Probe <code>${esc(r.probe_id)}</code>${
      r.distance_m != null ? ` · ${num(r.distance_m, 2)} m` : ""}${
      r.point_index != null ? ` · point ${esc(Number(r.point_index) + 1)}` : ""}.</p>` : ""}
    ${channels.length === 1
      ? `<div class="alert info" role="status">This run records only the
         ${esc(channelLabel(channels[0]))} excitation; no other channel is present, so none is drawn.</div>`
      : ""}
    ${r && r.ok === false && !channels.length
      ? errBanner("The preview is not ok; the per-channel curves are omitted. See the verdicts below.")
      : ""}
    ${dsp ? controlsHtml(dsp)
      : `<div class="alert warn" role="status">The payload carries no DSP point/ranges, so the controls
         cannot be shown. See the verdicts below.</div>`}
    ${channels.length
      ? phaseToggleHtml() + channelsHtml(channels, freqs)
      : `<section class="card"><h3>Per-channel filtered curves</h3>
         <div class="alert warn" role="status">No per-channel curves were returned for this case. The
           verdicts below are the server's.</div></section>`}
    ${verdictsHtml(verdicts)}
    ${lockedHtml(locked, dec, risk)}
    ${captionsHtml(captions)}
  </div>`;

  function drawCharts() {
    for (const s of chartSpecs) {
      const host = root.querySelector(`[data-dsp-chart="${s.id}"]`);
      if (!host) continue;
      if (!Array.isArray(s.freqs) || s.freqs.length < 2) {
        host.innerHTML = `<p class="hint" role="status">The payload carries no usable frequency array.</p>`;
        continue;
      }
      const opts = s.kind === "spl"
        ? splChartOpts(s.channel, s.freqs)
        : phaseChartOpts(s.channel, s.freqs, state.phase);
      drawChart(host, opts);
    }
  }

  root.querySelectorAll("[data-phase]").forEach(btn => btn.addEventListener("click", () => {
    const mode = btn.dataset.phase === "unwrapped" ? "unwrapped" : "wrapped";
    if (mode === state.phase) return;
    state.phase = mode;
    root.querySelectorAll("[data-phase]").forEach(b =>
      b.setAttribute("aria-pressed", String(b.dataset.phase === mode)));
    root.querySelectorAll("[data-phase-title]").forEach(el => { el.textContent = mode; });
    const p = new URLSearchParams();
    if (mode === "unwrapped") p.set("phase", "unwrapped");
    history.replaceState(null, "", route + (p.toString() ? "?" + p.toString() : ""));
    drawCharts();
  }));

  drawCharts();
}

// ── verdicts / locked sum / captions (payload text, verbatim) ───────────────

function verdictsHtml(verdicts) {
  const rows = Array.isArray(verdicts) ? verdicts : [];
  if (!rows.length) {
    return `<section class="card"><h3>DSP validation</h3>
      <p class="hint" role="status">No verdicts were returned.</p></section>`;
  }
  return `<section class="card">
    <div class="fig-head"><h3>DSP validation</h3>
      <span class="muted">validate_dsp_point + payload checks</span></div>
    <div class="tbl-wrap" style="margin-top:8px"><table class="hwd-table">
      <thead><tr><th>Check</th><th>Verdict</th><th>Detail</th></tr></thead>
      <tbody>${rows.map(v => `<tr>
        <td><code>${esc(v.check)}</code></td>
        <td><span class="pill ${v.ok ? "good" : "bad"}">${v.ok ? "pass" : "refused"}</span></td>
        <td>${esc(v.detail)}</td>
      </tr>`).join("")}</tbody></table></div>
  </section>`;
}

function lockedHtml(locked, dec, risk) {
  const reason = locked && locked.reason
    ? locked.reason : "The server did not return a locked-panel reason.";
  return `<section class="card stack" style="gap:8px" aria-labelledby="hwd-locked-sum">
    <div class="fig-head"><h3 id="hwd-locked-sum">System sum
      <span class="pill warn">locked</span></h3>
      <span class="muted">${esc(locked && locked.panel ? locked.panel : "system sum")} ·
        decision ${esc(dec)} · risk ${esc(risk)}</span></div>
    <div class="alert warn" role="status">${esc(reason)}</div>
    <p class="hint">No summed or combined field is computed or plotted on this page. The panel unlocks
      only after the channel calibration policy is answered.</p>
  </section>`;
}

function captionsHtml(captions) {
  const rows = Array.isArray(captions) ? captions : [];
  if (!rows.length) return "";
  return `<section class="card"><h3>Permanent captions</h3>
    ${rows.map(c => `<p class="cap">${esc(c)}</p>`).join("")}</section>`;
}
