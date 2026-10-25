// sandbox.js — the typology shape sandbox (#/typology/<name>)   AGPL-3.0-or-later
//
// P9 ask (owner): a clickable per-typology sandbox with manually draggable shape knobs showing
// the H/V wall section, the mouth, and the 3D shape — plus editable min/max on either side of
// each slider, saved to the place those bounds actually live (the bounds' own YAML home).
//
// Contracts frozen by the orchestrator (built against exactly; the endpoints land before this
// work is integrated, so every absent surface degrades honestly instead of breaking):
//   GET  /api/preview-shape/<config_name>?brief=<brief_name>&detail=2d|3d&knobs=<urlencoded JSON>
//        -> {version, config, brief, kind, units:"mm", quadrants, available, knobs:{effective},
//            section:{h:{inner,outer}, v:{inner,outer}}, mouth:{inner,outer},
//            envelope:{available,overshoot}|{available:false,reason},
//            shape3d:{available,roles,verts,tris}|{available:false,reason},
//            slow, timings_ms, notes}
//        QUARTER payload (quadrants "1"): the 3D card mirrors via view3d.js::mirrorMesh, the SVG
//        sections draw the mirrored halves exactly like the evolution page already does.
//        `slow:true` = rows kinds are march-bound: NO fetch per input event — honest
//        release-debounce with an explicit "updating…" chip, never a pretend-live drag.
//   POST /api/save-bounds {config, bounds:{key:{lo,hi}}} (only the rows that differ)
//        -> {ok:true, file, applied:[{key,from:{lo,hi},to:{lo,hi}}], notes:[…]} (config_sha
//        honesty — every returned note is rendered VERBATIM)
//        | {ok:false, rejected:[{key,reason}], applied:[]} — all-or-nothing; 404 unknown config.
//
// Knobs/bounds/labels come from the GENERATED parameter catalog (gui/static/param-catalog.v1.json)
// through the existing paramtips.js helpers — names, summaries, ranges and the `detail` physics
// sentence are never invented here, and a missing catalog degrades to the raw key site-wide.

import { css, niceTicks, el, fmt, measuredWidth, wallSection } from "./charts.js";
import { mirrorMesh, loadThree, normalizeRenderPrefs } from "./view3d.js";
import { loadParamCatalog, formatParamTitle, formatSearchRange, docFor } from "./paramtips.js";

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const EMPTY_PREVIEW = "preview endpoint unavailable";
const AT_LIMIT_PCT = 0.02;   // "within 2% of a bound" — the evolution knob mark's own rule

// ── pure helpers (the node-testable core) ──────────────────────────────────────────

/** URL-safe rounding: pages share the URL as state, so numbers stay short and stable. */
export const rndNum = v => (typeof v === "number" && isFinite(v)) ? Math.round(v * 1e3) / 1e3 : v;

/** The per-event fetch plan — the honest live/debounce split the sandbox spike measured
 *  (generator/grid/native 17–35 ms per full tick live; rows ~148–580 ms, march-bound).
 *  ev: "input" (a drag frame / keystroke) | "release" (change/pointerup/Enter).
 *  fast input  -> {fetch:"raf", updating:false, arms3d:false}   rAF-coalesced live 2D
 *  fast release-> {fetch:"now", updating:false, arms3d:true}    commit + idle-scheduled 3D
 *  slow input  -> {fetch:"defer", updating:true, arms3d:false}  NO fetch; the chip tells the truth
 *  slow release-> {fetch:"releaseDebounce", updating:true, arms3d:true}
 *  The 3D detail NEVER rebuilds per drag frame: it is idle-scheduled after release for both
 *  kinds (fast kinds also refresh after a short idle while a drag is held). */
export function timingDecision(slow, ev) {
  if (slow) {
    return ev === "release"
      ? { fetch: "releaseDebounce", updating: true, arms3d: true }
      : { fetch: "defer", updating: true, arms3d: false };
  }
  return ev === "release"
    ? { fetch: "now", updating: false, arms3d: true }
    : { fetch: "raf", updating: false, arms3d: false };
}

/** Which bound the value presses against, or null. "within 2% of a bound" = the existing
 *  `.at-limit` red marker treatment (evolution.js knob mark). Degenerate range -> null. */
export function atLimitEdge(value, lo, hi) {
  if (!isFinite(value) || !isFinite(lo) || !isFinite(hi)) return null;
  const span = hi - lo;
  if (!(span > 0)) return null;
  if (value <= lo + span * AT_LIMIT_PCT + 1e-12) return "lo";
  if (value >= hi - span * AT_LIMIT_PCT - 1e-12) return "hi";
  return null;
}

/** The brief-envelope chip: `overshoot > 0` -> a prominent red chip (the run/evolution
 *  at-limit vocabulary — red already means "outside a limit"; no second language invented). */
export function envelopeChip(overshoot) {
  if (!(typeof overshoot === "number") || !isFinite(overshoot) || overshoot <= 0) return null;
  const pct = Math.round(overshoot * 1000) / 10;
  return {
    pct,
    html: `<span class="pill bad" title="the design's extent overshoots the brief's size envelope — the endpoint measured its own march">outside the brief envelope (+${pct}%)</span>`,
  };
}

/** Clamp a knob value into a (possibly user-edited) row range. */
export function clampKnob(v, lo, hi) {
  const n = Number(v);
  if (!isFinite(n)) return 0;
  if (!isFinite(lo) || !isFinite(hi) || !(hi > lo)) return n;
  return Math.min(hi, Math.max(lo, n));
}

/** Starting knob values from the row catalog: the endpoint's own effective knobs win when one
 *  answered, then the catalog's published seed default, then the midpoint of the published
 *  bounds (derived, never invented). */
export function initialKnobValues(entries, effective) {
  const out = {};
  for (const e of entries || []) {
    if (!e || !e.key) continue;
    const eff = (effective || {})[e.key];
    if (typeof eff === "number" && isFinite(eff)) { out[e.key] = eff; continue; }
    const dflt = e.doc && typeof e.doc.default === "number" && isFinite(e.doc.default)
      ? e.doc.default : null;
    if (dflt != null) { out[e.key] = clampKnob(dflt, e.lo, e.hi); continue; }
    out[e.key] = clampKnob((e.lo + e.hi) / 2, e.lo, e.hi);
  }
  return out;
}

/** The generator's clamped/effective knobs ARE the truth of the geometry — after a payload
 *  lands, rows adopt the effective value (the slider follows the clamp, it never fights it). */
export function adoptEffectiveKnobs(requested, effective) {
  const out = { ...(requested || {}) };
  for (const [k, v] of Object.entries(effective || {})) {
    if (typeof v === "number" && isFinite(v)) out[k] = v;
  }
  return out;
}

/** The tooltip title for a sandbox knob row: the paramtips sentence (label [unit]: summary +
 *  search range) with the knob's `detail` physics sentence merged in — when the whole thing
 *  still fits the 300-char native-title cap; otherwise paramtips' own assembly (already
 *  capped) wins, exactly like every other data surface. The visible text stays the raw key. */
export function mergedKnobTitle(doc, key) {
  if (!doc || typeof doc !== "object") return null;
  let detail = String(doc.detail ?? "").trim();
  if (detail && !/[.!?]$/.test(detail)) detail += ".";
  if (!detail) return formatParamTitle(doc, key, null);
  const label = doc.label != null && doc.label !== "" ? String(doc.label) : "";
  const unit = doc.unit != null && doc.unit !== "" ? String(doc.unit) : "";
  if (!label) return formatParamTitle(doc, key, null);  // labelless docs keep the paramtips shape
  const summary = doc.summary != null && doc.summary !== "" ? String(doc.summary) : "";
  const range = formatSearchRange(doc);
  const head = `${label}${unit ? " [" + unit + "]" : ""}`;
  const mid = [summary, detail].filter(Boolean).join(" ");
  const full = `${head}: ${mid}${range ? " " + range : ""}`;
  return full.length <= 300 ? full : formatParamTitle(doc, key, null);
}

/** Value readout formatting — the evolution knob's own span-based decimals. */
export function fmtKnobValue(v, lo, hi) {
  return fmt(v, Math.abs(hi - lo) < 2 ? 3 : 1);
}

/** Slider step: whole-bounded knobs get step 1, everything else a 1–2–5 ladder of span/100,
 *  or the literal "any" when the range is invalid (the input stays editable, never "0"). */
export function sliderStep(lo, hi) {
  if (!(hi > lo)) return "any";
  if (Number.isInteger(lo) && Number.isInteger(hi)) return "1";
  const raw = (hi - lo) / 100;
  const p = Math.pow(10, Math.floor(Math.log10(raw)));
  for (const k of [1, 2, 5, 10]) if (k * p >= raw) return String(k * p);
  return String(10 * p);
}

const numAttr = v => (typeof v === "number" && isFinite(v)) ? String(v) : "0";

/** Red rejection chip for one knob (the reason stays honest: truncated words + full reason in
 *  the title and in the save-result block — never a crash, never an invented message). */
export function rejectedChipHtml(reason) {
  const r = String(reason ?? "");
  const short = r.length > 48 ? r.slice(0, 48).trimEnd() + "…" : r;
  return `<span class="pill bad" title="${esc(r)}">rejected: ${esc(short)}</span>`;
}

/** One full slider row (pure): [ raw-key name | min input | range slider | max input | value |
 *  state chips | reset ]. The name keeps the cross-surface raw key; the hover carries the
 *  catalog's label, meaning, `detail` physics sentence and search range. */
export function sliderRowHtml(e) {
  const key = String(e.key);
  const doc = e.doc || null;
  const cat = e.catalog || e.bounds || {};
  const b = e.bounds || { lo: cat.lo ?? 0, hi: cat.hi ?? 1 };
  const chips = [];
  if (e.edited) chips.push(`<span class="pill warn" title="the editable bounds differ from the typology's published bounds — Save bounds writes them to their YAML home">edited</span>`);
  if (e.rejected) chips.push(rejectedChipHtml(e.rejected));
  const at = atLimitEdge(e.value, b.lo, b.hi);
  const title = mergedKnobTitle(doc, key) ?? String(key);
  const step = sliderStep(b.lo, b.hi);
  return `<div class="sbox-row" data-key="${esc(key)}">`
    + `<span class="mono sbox-kname" tabindex="0" title="${esc(title)}">${esc(key)}</span>`
    + `<input class="sbox-num" type="number" step="any" data-role="lo" aria-label="${esc(key)} — editable minimum bound" value="${numAttr(b.lo)}">`
    + `<input class="sbox-slider" type="range" data-role="slider" aria-label="${esc(key)} value" min="${numAttr(b.lo)}" max="${numAttr(b.hi)}" step="${esc(step)}" value="${numAttr(e.value)}">`
    + `<input class="sbox-num" type="number" step="any" data-role="hi" aria-label="${esc(key)} — editable maximum bound" value="${numAttr(b.hi)}">`
    + `<span class="sbox-val num${at ? " at-limit" : ""}" data-role="val" data-at="${esc(at || "")}"`
    + (at ? ` title="within 2% of the ${at === "lo" ? "minimum" : "maximum"} bound — pressed against the limit"` : "")
    + `>${esc(fmtKnobValue(e.value, b.lo, b.hi))}</span>`
    + `<span class="sbox-chips" data-role="chips">${chips.join("")}</span>`
    + `<button type="button" class="sbox-reset" data-role="reset" aria-label="${esc(key)} — restore the typology's published bounds"`
    + ` title="Restore the typology's published bounds (${esc(fmt(Number(cat.lo)))}..${esc(fmt(Number(cat.hi)))})">↺</button>`
    + `</div>`;
}

/** One bound edit, validated honestly: NaN and lo>=hi are refused — the input reverts, a warn
 *  chip explains why; the slider range is never left invalid and nothing is silently swapped. */
export function boundEditOutcome(role, lo, hi, raw) {
  const n = typeof raw === "number" ? raw : Number(String(raw).replace(",", "."));
  if (!isFinite(n)) return { ok: false, lo, hi, msg: "not a number — the edit was refused" };
  const next = role === "lo" ? { lo: n, hi } : { lo, hi: n };
  if (!(next.hi > next.lo)) {
    return { ok: false, lo, hi, msg: "the minimum must stay below the maximum — the edit was refused" };
  }
  return { ok: true, lo: next.lo, hi: next.hi, msg: "" };
}

// ── URL state (#/typology/<name>?brief=..&knobs=<json>&bnds=<json>) ────────────────
// Theme change and >=40 px resize re-run route(); the page rehydrates {brief, knobs, edited
// bounds} from its own query (the evolution ?f=/&mode= precedent). Writes go through
// history.replaceState — never location.hash, which would re-trigger route() mid-drag.

export function buildQueryState(state) {
  const p = new URLSearchParams();
  const st = state || {};
  if (st.brief) p.set("brief", String(st.brief));
  const knobs = {};
  for (const [k, v] of Object.entries(st.knobs || {})) {
    const n = rndNum(Number(v));
    if (typeof n === "number" && isFinite(n)) knobs[k] = n;
  }
  if (Object.keys(knobs).length) p.set("knobs", JSON.stringify(knobs));
  const bnds = {};
  for (const [k, b] of Object.entries(st.bnds || {})) {
    if (!b || !isFinite(Number(b.lo)) || !isFinite(Number(b.hi))) continue;
    bnds[k] = { lo: rndNum(Number(b.lo)), hi: rndNum(Number(b.hi)) };
  }
  if (Object.keys(bnds).length) p.set("bnds", JSON.stringify(bnds));
  const s = p.toString();
  return s ? "?" + s : "";
}

/** Defensive parse of the route hash: junk JSON / wrong shapes are dropped (the page falls
 *  back to the catalog), never a broken page. Returns {brief, knobs, bnds} (null = absent). */
export function readQueryState(hash) {
  const qs = String(hash ?? "").split("?")[1] || "";
  const p = new URLSearchParams(qs);
  const jObj = s => {
    if (s == null) return null;
    try {
      const o = JSON.parse(s);
      return (o && typeof o === "object" && !Array.isArray(o)) ? o : null;
    } catch { return null; }
  };
  let knobs = jObj(p.get("knobs"));
  if (knobs) {
    const clean = {};
    for (const [k, v] of Object.entries(knobs)) {
      const n = Number(v);
      if (typeof k === "string" && k && isFinite(n)) clean[k] = n;
    }
    knobs = Object.keys(clean).length ? clean : null;
  }
  let bnds = jObj(p.get("bnds"));
  if (bnds) {
    const clean = {};
    for (const [k, b] of Object.entries(bnds)) {
      if (!b || typeof b !== "object") continue;
      const lo = Number(b.lo), hi = Number(b.hi);
      if (isFinite(lo) && isFinite(hi) && hi > lo) clean[k] = { lo, hi };
    }
    bnds = Object.keys(clean).length ? clean : null;
  }
  return { brief: p.get("brief") || null, knobs, bnds };
}

/** The frozen endpoint contract, built literally (encodeURIComponent over the JSON object). */
export function previewShapeUrl(configName, brief, detail, knobs) {
  return "/api/preview-shape/" + encodeURIComponent(String(configName))
    + "?brief=" + encodeURIComponent(String(brief ?? ""))
    + "&detail=" + (detail === "3d" ? "3d" : "2d")
    + "&knobs=" + encodeURIComponent(JSON.stringify(knobs || {}));
}

/** Save payload: ONLY the rows whose min/max differ from the catalog (the contract is
 *  all-or-nothing on exactly what the page sends). */
export function collectChangedBounds(catalogBounds, current) {
  const out = {};
  for (const [k, cur] of Object.entries(current || {})) {
    const cat = (catalogBounds || {})[k];
    if (!cat || !cur) continue;
    const lo = Number(cur.lo), hi = Number(cur.hi);
    if (!isFinite(lo) || !isFinite(hi)) continue;
    if (Math.abs(lo - Number(cat.lo)) > 1e-9 || Math.abs(hi - Number(cat.hi)) > 1e-9) {
      out[k] = { lo, hi };
    }
  }
  return out;
}

export const saveBoundsPayload = (config, changed) => ({ config: String(config ?? ""), bounds: changed || {} });

/** The save arm as a pure step (the repo's wireTwoStepArm semantics, node-testable):
 *  idle  --click--> armed ("Confirm save" face)          timeout from any state -> idle
 *  armed --click--> {fire:true} (commit the POST)
 *  The wiring auto-disarms after 5 s exactly like the kill-run button. */
export function armStep(state, event) {
  if (event === "timeout") return { state: "idle", fire: false };
  if (state === "armed") return { state: "idle", fire: true };
  return { state: "armed", fire: false };
}

const boundPair = b => (b && isFinite(Number(b.lo)) && isFinite(Number(b.hi)))
  ? `${fmt(Number(b.lo))}..${fmt(Number(b.hi))}` : "–";

const appliedRowHtml = a => {
  const key = esc(a && a.key != null ? a.key : "");
  return `<li><span class="mono">${key}</span> <span class="muted">${esc(boundPair(a && a.from))} → ${esc(boundPair(a && a.to))}</span></li>`;
};

const notesHtml = notes => (notes || []).filter(Boolean).length
  ? `<div class="sbox-notes">${notes.filter(Boolean).map(n => `<div>${esc(String(n))}</div>`).join("")}</div>` : "";

/** The save-result block for the POST response — `applied` rows and every returned `note`
 *  rendered VERBATIM (config_sha / resume honesty: the wording is the server's, never ours). */
export function saveResultHtml(r) {
  if (!r || typeof r !== "object") return "";
  if (r.error != null) {
    return `<div class="alert error" role="alert"><b>Error:</b> ${esc(r.error)}</div>`;
  }
  if (r.ok === true) {
    const applied = Array.isArray(r.applied) ? r.applied : [];
    return `<div class="alert info">Saved ${applied.length} bound row${applied.length === 1 ? "" : "s"} to <span class="mono">${esc(r.file ?? "")}</span>.</div>`
      + (applied.length ? `<ul class="sbox-applied">${applied.map(appliedRowHtml).join("")}</ul>` : "")
      + notesHtml(r.notes);
  }
  if (r.ok === false) {
    const rejected = Array.isArray(r.rejected) ? r.rejected : [];
    return `<div class="alert error" role="alert"><b>Nothing saved — every row was refused (the write is all-or-nothing):</b>`
      + ` <ul class="sbox-rejected">${rejected.map(x => `<li><span class="mono">${esc(x && x.key != null ? x.key : "")}</span> — ${esc((x && x.reason) ?? "")}</li>`).join("") || "<li>no reason given</li>"}</ul></div>`
      + notesHtml(r.notes);
  }
  return "";
}

// ── section geometry helpers (pure) ────────────────────────────────────────────────

/** Extents for the section/mouth drawings: z span, max |r| over both planes, max mouth |x|,|y|. */
export function sectionExtents(section, mouth) {
  let z0 = Infinity, z1 = -Infinity, rmax = 0, mmax = 0;
  for (const d of [section && section.h, section && section.v]) {
    for (const pts of [d && d.inner, d && d.outer]) {
      for (const p of pts || []) {
        if (!Array.isArray(p) || p.length < 2 || !isFinite(p[0]) || !isFinite(p[1])) continue;
        z0 = Math.min(z0, p[0]); z1 = Math.max(z1, p[0]); rmax = Math.max(rmax, Math.abs(p[1]));
      }
    }
  }
  for (const pts of [mouth && mouth.inner, mouth && mouth.outer]) {
    for (const p of pts || []) {
      if (!Array.isArray(p) || p.length < 2 || !isFinite(p[0]) || !isFinite(p[1])) continue;
      mmax = Math.max(mmax, Math.abs(p[0]), Math.abs(p[1]));
    }
  }
  return { z0, z1, rmax, mmax };
}

/** The wall band as ONE closed loop per plane (outer forward, inner reversed — both z-sorted),
 *  shaped exactly like the run page's {kind:"section"} profile so charts.js::wallSection fills
 *  it even-odd: interior = wall, bore stays background. H is drawn at +r, V mirrored at −r —
 *  the established half-mirrored section display. */
export function combinedSectionLoop(section) {
  const loop = d => {
    if (!d) return null;
    const zSort = (pts, dir) => (pts || []).filter(p => Array.isArray(p) && p.length >= 2)
      .sort((a, b) => (a[0] - b[0]) * dir);
    const outer = zSort(d.outer, 1), inner = zSort(d.inner, -1);
    if (outer.length >= 2 && inner.length >= 2) return outer.concat(inner);
    if (outer.length >= 2) return outer;              // a lone wall still draws (no band)
    if (inner.length >= 2) return inner;
    return null;
  };
  const h = loop(section && section.h), v = loop(section && section.v);
  if (!h && !v) return null;
  return { kind: "section", h: h || [], v: v || [] };
}

/** The mouth ring band (outer + inner reversed, even-odd) — "" when there is no outer ring. */
export function mouthBandPath(mouth, X, Y) {
  const chain = pts => (pts || []).filter(p => Array.isArray(p) && p.length >= 2)
    .map(([x, y], i) => (i ? "L" : "M") + X(x).toFixed(1) + "," + Y(y).toFixed(1));
  const outer = chain((mouth || {}).outer);
  if (!outer.length) return "";
  const inner = chain(((mouth || {}).inner || []).slice().reverse());
  return outer.join("") + inner.join("") + "Z";
}

// ── 3D: one scene, hot-swapped geometry (the frame-player's discipline: never a per-frame
// rebuild; old geometries disposed; camera dolly-out only). view3d.js::init3d builds a whole
// renderer per call and its look/chip helpers are module-private there (not this lane's
// file), so the sandbox mirrors that scene's exact shape — same tokens, same material recipe,
// same light rig, same persisted render-prefs key through view3d.js's exported
// normalizeRenderPrefs — so the owner's saved prefs apply here AND edits made here persist to
// every other 3D surface.
const RENDER_KEY = "hl-v3d-render";       // view3d.js::RENDER_PREF_KEY (shared key, same meaning)
const SHADOW_KEY = "hl-v3d-shadows";      // the existing wall-shadows toggle the 3D pages persist
// Existing named colours of view3d.js (module-private there), mirrored by value: the sandbox's
// 3D must read identically to every other 3D surface; no NEW palette entry is introduced.
const HORN_BODY = 0xdfe4e8, WIRE_COLOR = 0xf4f7f9, HEMI_GROUND = 0x8fa3ad, LIGHT_COLOR = 0xffffff;
const SURF_PRESETS = {                    // mirror of view3d.js::RENDER_PRESETS (defaults = today's look)
  satin:    { colorScale: 1.0,  roughness: 0.55, metalness: 0.05, wireOpacity: 0.28, light: { hemi: 0.45, key: 1.15, fill: 0.35, rim: 0.85 } },
  matte:    { colorScale: 0.88, roughness: 0.85, metalness: 0.02, wireOpacity: 0.18, light: { hemi: 0.45, key: 1.15, fill: 0.35, rim: 0.85 } },
  metallic: { colorScale: 1.0,  roughness: 0.32, metalness: 0.35, wireOpacity: 0.28, light: { hemi: 0.45, key: 1.15, fill: 0.35, rim: 0.85 } },
  studio:   { colorScale: 1.0,  roughness: 0.45, metalness: 0.05, wireOpacity: 0.28, light: { hemi: 0.55, key: 1.55, fill: 0.70, rim: 1.15 } },
};

function loadPrefs3d() {
  try { return normalizeRenderPrefs(localStorage.getItem(RENDER_KEY)); }
  catch { return normalizeRenderPrefs(null); }
}

function savePrefs3d(prefs) {
  const p = normalizeRenderPrefs(prefs);
  try { localStorage.setItem(RENDER_KEY, JSON.stringify(p)); } catch { /* private mode */ }
  return p;
}

/** The persisted render-settings chip (surface / ridges / light) for the sandbox's hot-swap
 *  scene: same control set, same storage key, same in-place application as
 *  view3d.js::applyRenderControls — which is module-private there and cannot be imported. */
function renderControlsChip(container, onChange) {
  const prefs = loadPrefs3d();
  if (getComputedStyle(container).position === "static") container.style.position = "relative";
  const chip = document.createElement("div");
  chip.style.cssText = "position:absolute;top:8px;right:8px;z-index:2;display:flex;" +
    "align-items:center;flex-wrap:wrap;gap:4px 10px;max-width:calc(100% - 16px);padding:3px 8px;" +
    "font-family:var(--f-mono);font-size:0.72rem;line-height:1.5;border-radius:4px;" +
    "color:var(--ink,#222);background:var(--surface,#fff);border:1px solid var(--rule,#ccc);" +
    "opacity:0.94;pointer-events:auto";
  const lblStyle = "display:inline-flex;align-items:center;gap:4px";
  const selStyle = "font:inherit;font-size:0.72rem;background:var(--surface,#fff);color:var(--ink,#222);" +
    "border:1px solid var(--rule,#ccc);border-radius:4px;padding:0 3px";
  const opt = (v, cur, label) => `<option value="${esc(v)}"${v === cur ? " selected" : ""}>${esc(label)}</option>`;
  chip.innerHTML =
    `<label style="${lblStyle}">surface<select data-sbox-pref="surface" style="${selStyle}">` +
      ["satin", "matte", "metallic", "studio"].map(s => opt(s, prefs.surface, s === "satin" ? "satin (default)" : s)).join("") +
    `</select></label>` +
    `<label style="${lblStyle}">ridges<select data-sbox-pref="ridges" style="${selStyle}">` +
      ["on", "thin", "off"].map(s => opt(s, prefs.ridges, s === "on" ? "on (default)" : s)).join("") +
    `</select></label>` +
    `<label style="${lblStyle}">light` +
      `<input type="range" data-sbox-pref="light" min="0.5" max="2" step="0.1" value="${esc(prefs.light)}" aria-label="light intensity multiplier" style="width:72px;accent-color:var(--accent)">` +
      `<span data-sbox-light-val>${esc(prefs.light)}×</span></label>`;
  container.appendChild(chip);
  const surf = chip.querySelector('[data-sbox-pref="surface"]');
  const rid = chip.querySelector('[data-sbox-pref="ridges"]');
  const lit = chip.querySelector('[data-sbox-pref="light"]');
  const val = chip.querySelector("[data-sbox-light-val]");
  const commit = () => {
    const next = savePrefs3d({ surface: surf.value, ridges: rid.value, light: Number(lit.value) });
    val.textContent = `${next.light}×`;
    onChange(next);
  };
  surf.addEventListener("change", commit);
  rid.addEventListener("change", commit);
  lit.addEventListener("input", commit);
  return chip;
}

/**
 * The sandbox 3D player. Builds ONE scene from the first shape3d payload and returns
 * {applyMesh(verts, tris, quadrants), dispose} — applyMesh hot-swaps geometry (mirrorMesh +
 * fresh BufferGeometry; the previous geometry + wireframe disposed), keeping camera, lights
 * and orbit state alive. The container carries data-v3d and receives _dispose3d, so route()'
 * sweep disposes renderer/scene/geometries on navigation. Resolves null when three.js cannot
 * load (the caller keeps its honest fallback text).
 */
export async function initSandbox3d(container, first, opts = {}) {
  container.innerHTML = "";
  const ok3d = await loadThree();
  if (!container.isConnected) return null;
  if (!ok3d) {
    const msg = document.createElement("div");
    msg.className = "view3d-fallback";
    msg.textContent = opts.fallback3d || "3D unavailable (three.js did not load) — the wall sections carry the geometry.";
    container.appendChild(msg);
    return null;
  }
  const THREE = ok3d;
  const cs = getComputedStyle(document.documentElement);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(
    cs.getPropertyValue("--viz-canvas").trim() || cs.getPropertyValue("--surface").trim() || "#ffffff");

  const mat = new THREE.MeshStandardMaterial({
    color: HORN_BODY, roughness: 0.55, metalness: 0.05,
    side: THREE.DoubleSide, transparent: false,
    polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
  });
  const wireMat = new THREE.LineBasicMaterial({ color: WIRE_COLOR, transparent: true, opacity: 0.28 });
  const mesh = new THREE.Mesh(new THREE.BufferGeometry(), mat);
  const wire = new THREE.LineSegments(new THREE.BufferGeometry(), wireMat);
  scene.add(mesh, wire);
  const shadows = (typeof opts.shadows === "boolean") ? opts.shadows : true;
  mesh.castShadow = mesh.receiveShadow = shadows;

  const hemi = new THREE.HemisphereLight(LIGHT_COLOR, HEMI_GROUND, 0.45);
  scene.add(hemi);
  const key2 = new THREE.DirectionalLight(LIGHT_COLOR, 1.15);
  const fill = new THREE.DirectionalLight(LIGHT_COLOR, 0.35);
  const rim = new THREE.DirectionalLight(LIGHT_COLOR, 0.85);
  scene.add(key2, fill, rim);
  scene.add(key2.target);                              // target must live in the scene to move it
  const lights = { hemi, key: key2, fill, rim };

  /** In-place prefs application — the same surface/ridges/light model as view3d.js. */
  function applyLook(prefs) {
    const p = normalizeRenderPrefs(prefs);
    const preset = SURF_PRESETS[p.surface] || SURF_PRESETS.satin;
    mat.color.setHex(HORN_BODY).multiplyScalar(preset.colorScale);
    mat.roughness = preset.roughness;
    mat.metalness = preset.metalness;
    wireMat.opacity = p.ridges === "thin" ? 0.12 : preset.wireOpacity;
    if (p.ridges === "off") scene.remove(wire);
    else scene.add(wire);
    lights.key.intensity = preset.light.key * p.light;
    lights.fill.intensity = preset.light.fill * p.light;
    lights.rim.intensity = preset.light.rim * p.light;
    lights.hemi.intensity = preset.light.hemi;
  }
  applyLook(loadPrefs3d());

  let groundGeo = null, groundMat = null;
  function buildGround(dim) {
    if (!shadows) return;
    key2.castShadow = true;
    key2.shadow.mapSize.set(1024, 1024);
    key2.shadow.camera.left = -0.8 * dim; key2.shadow.camera.right = 0.8 * dim;
    key2.shadow.camera.top = 0.8 * dim;   key2.shadow.camera.bottom = -0.8 * dim;
    key2.shadow.camera.near = 0.1;        key2.shadow.camera.far = 4 * dim;
    key2.shadow.normalBias = 0.01 * dim;  key2.shadow.bias = 0;
    groundGeo = new THREE.PlaneGeometry(3.0 * dim, 3.0 * dim);
    groundMat = new THREE.ShadowMaterial({ opacity: 0.22 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.position.set(0, -0.02 * dim, 0);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);
  }

  const w = container.clientWidth || 600, h = container.clientHeight || 400;
  const camera = new THREE.PerspectiveCamera(45, w / h, 0.001, 100);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(w, h);
  if (shadows) { renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap; }
  container.appendChild(renderer.domElement);

  const { OrbitControls: OC } = await import("three/addons/controls/OrbitControls.js");
  if (!container.isConnected) return null;             // navigated away mid-load: build nothing
  const controls = new OC(camera, renderer.domElement);
  controls.update();

  const ro = new ResizeObserver(entries => {
    for (const e of entries) {
      if (!(e.contentRect.width > 0 && e.contentRect.height > 0)) continue;
      renderer.setSize(e.contentRect.width, e.contentRect.height);
      camera.aspect = e.contentRect.width / e.contentRect.height;
      camera.updateProjectionMatrix();
    }
  });
  ro.observe(container);

  renderControlsChip(container, applyLook);

  let curGeo = null, curWireGeo = null, fitDim = 0;
  /** Hot-swap: mirror the quarter payload, build fresh geometry, dispose the old. */
  function applyMesh(verts, tris, quadrants) {
    const m = mirrorMesh(verts, tris, quadrants ?? "1");
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(Float32Array.from(m.verts), 3));
    geo.setIndex(new THREE.BufferAttribute(Uint32Array.from(m.tris), 1));
    geo.computeVertexNormals();
    geo.scale(0.001, 0.001, 0.001);                    // payload is mm; the stage is metres
    geo.computeBoundingBox();
    const center = new THREE.Vector3();
    geo.boundingBox.getCenter(center);
    const size = new THREE.Vector3();
    geo.boundingBox.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z);
    if (!isFinite(maxDim) || maxDim <= 0) { geo.dispose(); return; }
    const wireGeo = new THREE.WireframeGeometry(geo);
    if (curGeo) curGeo.dispose();
    if (curWireGeo) curWireGeo.dispose();
    curGeo = geo;
    curWireGeo = wireGeo;
    mesh.geometry = geo;
    wire.geometry = wireGeo;
    // First geometry fits the camera; later swaps keep the orbit — dolly OUT only when the
    // horn outgrew the fit (the frame-player's "one camera" rule, with an honest escape hatch).
    if (fitDim === 0) {
      fitDim = maxDim;
      buildGround(maxDim);
      camera.position.set(center.x + maxDim * 1.2, center.y + maxDim * 0.8, center.z + maxDim * 1.5);
      camera.lookAt(center);
      controls.target.copy(center);
      controls.update();
      key2.position.set(center.x + maxDim * 1.6, center.y + maxDim * 2.2, center.z + maxDim * 1.8);
      fill.position.set(center.x - maxDim * 1.8, center.y + maxDim * 0.6, center.z + maxDim * 1.2);
      rim.position.set(center.x - maxDim * 1.2, center.y - maxDim, center.z - maxDim * 2.2);
      key2.target.position.copy(center);
    } else if (maxDim > fitDim * 1.01) {
      const factor = maxDim / fitDim;
      const dir = camera.position.clone().sub(controls.target);
      camera.position.copy(controls.target).addScaledVector(dir.normalize(), dir.length() * factor);
      fitDim = maxDim;
    }
  }
  applyMesh(first.verts, first.tris, first.quadrants);

  let raf;
  (function animate() {
    raf = requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  })();

  container._dispose3d = () => {                       // route()'s [data-v3d] sweep kills everything
    cancelAnimationFrame(raf);
    ro.disconnect();
    controls.dispose();
    renderer.dispose();
    if (curGeo) curGeo.dispose();
    if (curWireGeo) curWireGeo.dispose();
    mat.dispose();
    wireMat.dispose();
    hemi.dispose();
    key2.dispose();
    fill.dispose();
    rim.dispose();
    if (groundGeo) groundGeo.dispose();
    if (groundMat) groundMat.dispose();
    while (scene.children.length) scene.remove(scene.children[0]);
  };
  return { applyMesh, dispose: container._dispose3d };
}

// ── the view ───────────────────────────────────────────────────────────────────────

/** brief_file ("../briefs/x.yaml") -> stem "x" — the same matcher the Compose wizard uses. */
const briefFileStem = f => String(f || "").replace(/\\/g, "/").split("/").pop().replace(/\.(yaml|yml)$/, "");

async function fetchJson(path) {
  const r = await fetch(path);
  if (!r.ok) { const t = await r.text().catch(() => ""); throw new Error(r.status + " " + t); }
  return r.json();
}

async function postJson(path, body) {
  try {
    const r = await fetch(path, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    let j = await r.json().catch(() => ({}));
    if (!r.ok && (j == null || j.error == null)) j = { error: "HTTP " + r.status };
    return j;
  } catch (e) {
    return { error: String((e && e.message) || e) };
  }
}

/** Group label wording mirrors the Typologies page's own captions. */
const GROUP_LABEL = {
  classical: "Classical horns", hybrid: "Hybrids", magnus: "Magnus mesher families",
  organic: "Organic / rollback", legacy: "Utility / legacy", uncatalogued: "Uncatalogued",
};

/** Empty-state text inside an SVG figure (honest absence, never a blank box). */
function emptySvg(svg, msg) {
  svg.innerHTML = "";
  const W = Math.max(260, measuredWidth(svg, 400)), H = 330;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("width", W);
  svg.setAttribute("height", H);
  const t = el("text", { x: W / 2, y: H / 2 + 4, "text-anchor": "middle" }, svg);
  t.textContent = msg;
}

/** Front view: mouth ring band + the SELECTED brief's size envelope as a dashed rect. */
function drawFront(svg, payload, envelope, emptyMsg) {
  svg.innerHTML = "";
  const mouth = (payload || {}).mouth || {};
  const outer = (mouth.outer || []).filter(p => Array.isArray(p) && p.length >= 2);
  if (!outer.length) { emptySvg(svg, emptyMsg || (payload || {}).shapeUnavailable || EMPTY_PREVIEW); return; }
  const ext = sectionExtents((payload || {}).section, mouth);
  const envHalf = envelope ? Math.max(envelope.w, envelope.h) / 2 : 0;
  const R = Math.max(ext.mmax, envHalf, 10) * 1.08;
  const W = Math.max(260, measuredWidth(svg, 400)), H = 330;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("width", W);
  svg.setAttribute("height", H);
  const m = { l: 36, r: 10, t: 10, b: 28 }, pw = W - m.l - m.r, ph = H - m.t - m.b;
  const sc = Math.min(pw, ph) / (2 * R), cx = m.l + pw / 2, cy = m.t + ph / 2;
  const X = x => cx + x * sc, Y = y => cy - y * sc;
  const g = el("g", { class: "grid" }, svg);
  for (const t of niceTicks(-R, R, 6)) {
    el("line", { x1: X(t), x2: X(t), y1: Y(R), y2: Y(-R) }, g);
    el("line", { x1: X(-R), x2: X(R), y1: Y(t), y2: Y(t) }, g);
    el("text", { x: X(t), y: H - 10, "text-anchor": "middle" }, svg).textContent = Math.abs(t);
    el("text", { x: X(-R) - 4, y: Y(t) + 3, "text-anchor": "end" }, svg).textContent = Math.abs(t);
  }
  if (envelope) {
    el("rect", {
      x: X(-envelope.w / 2), y: Y(envelope.h / 2), width: envelope.w * sc, height: envelope.h * sc,
      fill: "none", stroke: css("--warn"), "stroke-dasharray": "6 4", "stroke-width": 1.2,
    }, svg);
  }
  const band = mouthBandPath(mouth, X, Y);
  if (band) {
    el("path", { d: band, fill: css("--best"), "fill-rule": "evenodd", "fill-opacity": 0.22, stroke: "none" }, svg);
    el("path", { d: band, fill: "none", stroke: css("--best"), "stroke-width": 1.6, "fill-rule": "evenodd" }, svg);
  }
  const innerPts = ((mouth || {}).inner || []).filter(p => Array.isArray(p) && p.length >= 2);
  if (innerPts.length) {
    const ip = innerPts.map(([x, y], i) => (i ? "L" : "M") + X(x).toFixed(1) + "," + Y(y).toFixed(1)).join("") + "Z";
    el("path", { d: ip, fill: "none", stroke: css("--muted"), "stroke-width": 1.1 }, svg);
  }
  const lbl = el("text", { x: X(R), y: H - 1, "text-anchor": "end" }, svg);
  lbl.textContent = "width mm";
}

export async function viewTypologySandbox(root, configName) {
  const ROOT = root;
  ROOT.innerHTML = `<p class="muted">Loading the sandbox…</p>`;
  const cat = await loadParamCatalog();               // never throws; a failed load degrades below
  const t = cat && cat.typologies && cat.typologies[configName];
  if (!t) {
    ROOT.innerHTML = `<div class="stack" style="gap:14px">
      <div class="alert error" role="alert">Typology <span class="mono">${esc(configName)}</span> is not in the parameter catalog — the sandbox cannot list its knobs honestly. <a href="#/typologies">← back to typologies</a></div>
    </div>`;
    return;
  }
  const entries = Object.keys(t.bounds_index || {})
    .filter(k => { const bi = t.bounds_index[k]; return bi && bi.search !== false && isFinite(Number(bi.lo)) && isFinite(Number(bi.hi)) && Number(bi.hi) > Number(bi.lo); })
    .map(k => {
      const bi = t.bounds_index[k];
      return { key: k, lo: Number(bi.lo), hi: Number(bi.hi), doc: docFor(configName, k),
               boundsSource: bi.file ? { file: bi.file, key: bi.key } : null };
    });
  const catalogBounds = Object.fromEntries(entries.map(e => [e.key, { lo: e.lo, hi: e.hi }]));

  let briefs = [];
  try { briefs = await fetchJson("/api/briefs"); } catch { briefs = []; }
  if (!ROOT.isConnected) return;                      // navigated away while loading

  // ── state, hydrated from the route query (survives theme/resize route() re-runs) ──
  const q = readQueryState(location.hash);
  let briefSel = (q.brief && briefs.some(b => b.name === q.brief)) ? q.brief
    : (briefs.find(b => b.name === briefFileStem(t.brief_file)) || briefs[0] || { name: "" }).name;
  let rowBounds = Object.fromEntries(entries.map(e => [e.key, (q.bnds && q.bnds[e.key]) || { lo: e.lo, hi: e.hi }]));
  const knobs = initialKnobValues(entries, q.knobs || {});
  for (const e of entries) knobs[e.key] = clampKnob(knobs[e.key], rowBounds[e.key].lo, rowBounds[e.key].hi);
  let rejected = {};                                   // key -> reason (until the next save attempt)
  let slowNow = false;                                 // authoritative once a payload lands
  let backendDark = false;                             // any preview-shape failure (404 / network)
  let lastPayload = null;                              // last 2D payload (sections/notes redraw)

  ROOT.innerHTML = `<div class="stack" style="gap:18px">
    <div>
      <div class="eyebrow">Typologies · shape sandbox</div>
      <h2>${esc(t.name)}</h2>
      <p class="muted typ-meta">${esc(GROUP_LABEL[t.group] || t.group || "")} · ${esc(t.symmetry || "?")}
        · ${esc(t.kind || "")} · ${entries.length} shape parameters ·
        <a href="#/typologies">← back to typologies</a></p>
      <p class="muted prose" style="margin-top:4px">${esc(t.description || "")}</p>
    </div>
    <div class="card sbox-status" id="sbox-status" aria-live="polite">
      <label class="evo-opt" for="sbox-brief">brief
        <select id="sbox-brief" aria-label="brief — changing it re-previews the shape">
          ${briefs.map(b => `<option value="${esc(b.name)}"${b.name === briefSel ? " selected" : ""}>${esc(b.name)}${b.kind === "user" ? " (yours)" : ""}</option>`).join("") || `<option value="">brief list unavailable</option>`}
        </select></label>
      <span id="sbox-env"></span>
      <span id="sbox-updating" hidden><span class="pill warn" style="cursor:default">updating…</span></span>
      <span id="sbox-dark" class="muted" hidden>${esc(EMPTY_PREVIEW)} — sliders still work from the typology's published bounds</span>
      <span id="sbox-notes" class="muted" style="font-size:0.74rem"></span>
    </div>
    <div class="sbox-grid">
      <div class="fig">
        <h3>Side view: wall cross-section</h3>
        <div class="cap">Horizontal plane right, vertical plane mirrored left, throat at the bottom (mm). Filled band = wall thickness.</div>
        <svg id="sbox-side"></svg>
      </div>
      <div class="fig">
        <h3>Front view: mouth outline</h3>
        <div class="cap">Mouth ring (mm); dashed: the brief's size envelope.</div>
        <div id="sbox-frontnote" class="cap muted" hidden></div>
        <svg id="sbox-front"></svg>
      </div>
      <div class="fig">
        <div class="fig-head">
          <h3>3D shape</h3>
          <label class="evo-opt" title="the same persisted wall-shadows toggle as every other 3D view">
            <input type="checkbox" id="sbox-shadow" checked> wall shadows</label>
        </div>
        <div class="cap">Quarter payload mirrored to the full horn. It hot-swaps while you work — the camera never resets.</div>
        <div id="sbox-3d" data-v3d class="sbox-3dwrap"><div class="view3d-fallback">loading…</div></div>
      </div>
      <div class="card" id="sbox-slider-card">
        <div class="fig-head">
          <h3>Shape parameters</h3>
          <span class="btn-row">
            <span id="sbox-save-hint" class="muted" style="font-size:0.76rem"></span>
            <button id="sbox-save" class="primary" ${entries.length ? "" : "disabled"}>Save bounds</button>
          </span>
        </div>
        <p class="cap muted">Drag a slider to reshape the horn. Edit the min / max boxes to widen the search box the slider can reach — the value turns red when it presses against a bound, and ↺ restores the typology's published bounds. Saving writes only the edited rows to where those bounds live.</p>
        <div id="sbox-knobs" class="sbox-knobs-list">${entries.map(e => sliderRowHtml({
          key: e.key, doc: e.doc, catalog: catalogBounds[e.key], bounds: rowBounds[e.key],
          value: clampKnob(knobs[e.key], rowBounds[e.key].lo, rowBounds[e.key].hi), edited: false,
        })).join("") || `<p class="muted">This typology has no searchable shape parameters — its geometry is authored outside the knob search.</p>`}</div>
        <div id="sbox-save-msg" class="hint" aria-live="polite"></div>
        <div id="sbox-save-result" style="margin-top:8px"></div>
      </div>
    </div>
  </div>`;
  if (!entries.length) return;                        // CAD-only typology: honest empty card, done

  const shBox = document.getElementById("sbox-shadow");
  if (shBox) {
    try { shBox.checked = localStorage.getItem(SHADOW_KEY) !== "0"; } catch { /* defaults on */ }
  }

  // ── element handles ──
  const knobsEl = document.getElementById("sbox-knobs");
  const sideSvg = document.getElementById("sbox-side");
  const frontSvg = document.getElementById("sbox-front");
  const frontNote = document.getElementById("sbox-frontnote");
  const cv3d = document.getElementById("sbox-3d");
  const envEl = document.getElementById("sbox-env");
  const updEl = document.getElementById("sbox-updating");
  const darkEl = document.getElementById("sbox-dark");
  const notesEl = document.getElementById("sbox-notes");
  const saveBtn = document.getElementById("sbox-save");
  const saveHint = document.getElementById("sbox-save-hint");
  const saveMsg = document.getElementById("sbox-save-msg");
  const saveResult = document.getElementById("sbox-save-result");
  const briefEl = document.getElementById("sbox-brief");

  emptySvg(sideSvg, "loading the preview…");
  emptySvg(frontSvg, "loading the preview…");

  // ── timing: ONE rAF-throttled 2D lane, ONE idle-scheduled 3D lane, ONE slow debounce ──
  let raf2d = 0, inFlight2d = false, dirty2d = false;
  let slowTimer = null, idle3d = null, inFlight3d = false, dirty3d = false;
  let urlTimer = null, armTimer = null, player3d = null;

  const currentKnobsJson = () => {
    const o = {};
    for (const e of entries) o[e.key] = clampKnob(knobs[e.key], rowBounds[e.key].lo, rowBounds[e.key].hi);
    return o;
  };

  function setUpdating(on) { if (updEl) updEl.hidden = !on; }
  function setDark(on, why) {
    if (on) backendDark = true;
    else backendDark = false;                          // any successful response proves the endpoint
    if (darkEl) {
      darkEl.hidden = !backendDark;
      if (why) darkEl.setAttribute("title", String(why));
      else darkEl.removeAttribute("title");
    }
  }

  const previewUrl = detail => previewShapeUrl(configName, briefSel, detail, currentKnobsJson());

  async function fetchPayload(detail) {
    const r = await fetch(previewUrl(detail));
    if (!r.ok) throw new Error(r.status + " " + (await r.text().catch(() => "")));
    return r.json();
  }

  function envelopeForBrief() {
    const b = briefs.find(x => x.name === briefSel);
    const e = b && b.brief && b.brief.envelope;
    const w = e && Number(e.max_mouth_w_mm), h = e && Number(e.max_mouth_h_mm);
    return (isFinite(w) && isFinite(h) && w > 0 && h > 0) ? { w, h } : null;
  }

  function drawPayload(payload, unavailableMsg) {
    lastPayload = payload;
    const loop = combinedSectionLoop(payload.section);
    if (loop) wallSection(sideSvg, [{ profile: loop, color: css("--best"), filled: true }], { H: 330 });
    else emptySvg(sideSvg, unavailableMsg || EMPTY_PREVIEW);
    const env = envelopeForBrief();
    drawFront(frontSvg, payload, env, unavailableMsg);
    if (frontNote) {
      const e = payload.envelope;
      if (e && e.available === false && e.reason) {
        frontNote.hidden = false;
        frontNote.textContent = `size envelope unavailable — ${e.reason}`;
      } else frontNote.hidden = true;
    }
    const envChip = envelopeChip(payload.envelope && payload.envelope.available
      ? Number(payload.envelope.overshoot) : null);
    if (envEl) envEl.innerHTML = envChip ? envChip.html : "";
    const notes = Array.isArray(payload.notes) ? payload.notes.filter(Boolean) : [];
    if (notesEl) notesEl.textContent = notes.length ? notes.join(" · ") : "";
  }

  async function fire2d() {
    if (!ROOT.isConnected) return;                     // a re-route replaced this view: fetch nothing
    if (inFlight2d) { dirty2d = true; return; }
    inFlight2d = true;
    setUpdating(true);
    try {
      const payload = await fetchPayload("2d");
      if (!ROOT.isConnected) return;
      setDark(false);                                  // a real response: the endpoint is alive
      slowNow = payload.slow === true;
      const before = { ...knobs };
      const eff = adoptEffectiveKnobs(knobs, payload.knobs);
      for (const k of Object.keys(eff)) knobs[k] = eff[k];
      drawPayload(payload, payload.available === false
        ? "the generator refused these values — see the note" : null);
      for (const e of entries) if (before[e.key] !== knobs[e.key]) repaintRow(e.key);
    } catch (e) {
      if (!ROOT.isConnected) return;
      setDark(true, String((e && e.message) || e));
      emptySvg(sideSvg, EMPTY_PREVIEW);
      emptySvg(frontSvg, EMPTY_PREVIEW);
      if (envEl) envEl.innerHTML = "";
      if (notesEl) notesEl.textContent = "";
    } finally {
      inFlight2d = false;
      if (ROOT.isConnected) setUpdating(dirty2d || (slowTimer != null));
      if (ROOT.isConnected && dirty2d) { dirty2d = false; fire2d(); }
    }
  }

  function request2d(plan) {
    if (plan.fetch === "defer") { setUpdating(true); return; }        // slow input: the chip tells the truth
    if (plan.fetch === "raf") {                                      // fast input: rAF-coalesced
      if (!raf2d) raf2d = requestAnimationFrame(() => { raf2d = 0; fire2d(); });
      return;
    }
    if (plan.fetch === "now") { fire2d(); return; }                  // fast release: commit now
    if (plan.fetch === "releaseDebounce") {                          // slow release: debounced
      if (slowTimer) clearTimeout(slowTimer);
      setUpdating(true);
      slowTimer = setTimeout(() => { slowTimer = null; fire2d(); }, 250);
    }
  }

  /** 3D refresh — idle-scheduled (never per drag frame); one fetch in flight, newest wins. */
  function arm3d(delay) {
    if (idle3d) clearTimeout(idle3d);
    idle3d = setTimeout(() => { idle3d = null; fire3d(); }, delay == null ? 450 : delay);
  }

  async function fire3d() {
    if (!cv3d || !ROOT.isConnected) return;            // a re-route replaced this view: fetch nothing
    if (inFlight3d) { dirty3d = true; return; }
    inFlight3d = true;
    try {
      const payload = await fetchPayload("3d");
      if (!ROOT.isConnected) return;
      setDark(false);
      const s3 = payload.shape3d;
      if (!s3 || s3.available === false || !Array.isArray(s3.verts) || !s3.verts.length ||
          !Array.isArray(s3.tris) || !s3.tris.length) {
        show3dUnavailable((s3 && s3.reason) || "no preview geometry for this design");
      } else if (player3d) {
        player3d.applyMesh(s3.verts, s3.tris, payload.quadrants);
      } else {
        player3d = await initSandbox3d(cv3d, { verts: s3.verts, tris: s3.tris, quadrants: payload.quadrants },
          { shadows: shadowsOn() });
      }
    } catch (e) {
      if (!ROOT.isConnected) return;
      setDark(true, String((e && e.message) || e));
      show3dUnavailable(EMPTY_PREVIEW);
    } finally {
      inFlight3d = false;
      if (ROOT.isConnected && dirty3d) { dirty3d = false; arm3d(50); }
    }
  }

  function show3dUnavailable(reason) {
    if (!cv3d || player3d) return;                     // keep the last honest geometry on screen
    cv3d.innerHTML = `<div class="view3d-fallback">${esc(reason)}</div>`;
  }

  const shadowsOn = () => !(shBox && !shBox.checked);

  // ── URL writes (committed changes only — release/reset/brief; never per drag frame) ──
  function writeUrlNow() {
    if (urlTimer) { clearTimeout(urlTimer); urlTimer = null; }
    history.replaceState(null, "", "#/typology/" + encodeURIComponent(configName)
      + buildQueryState({ brief: briefSel, knobs: currentKnobsJson(), bnds: collectChangedBounds(catalogBounds, rowBounds) }));
  }
  function writeUrl() {
    if (urlTimer) clearTimeout(urlTimer);
    urlTimer = setTimeout(() => { urlTimer = null; writeUrlNow(); }, 400);
  }

  // ── row repaint / chips ──────────────────────────────────────────────────────────────
  const rowEl = key => knobsEl.querySelector(`.sbox-row[data-key="${CSS.escape(key)}"]`);
  function repaintRow(key) {
    const row = rowEl(key);
    if (!row) return;
    const b = rowBounds[key], v = clampKnob(knobs[key], b.lo, b.hi);
    const slider = row.querySelector('[data-role="slider"]');
    if (slider) {
      slider.min = numAttr(b.lo); slider.max = numAttr(b.hi);
      slider.step = String(sliderStep(b.lo, b.hi));
      slider.value = numAttr(v);
    }
    const valEl = row.querySelector('[data-role="val"]');
    const at = atLimitEdge(v, b.lo, b.hi);
    if (valEl) {
      valEl.textContent = fmtKnobValue(v, b.lo, b.hi);
      valEl.classList.toggle("at-limit", !!at);
      valEl.dataset.at = at || "";
      if (at) valEl.setAttribute("title", `within 2% of the ${at === "lo" ? "minimum" : "maximum"} bound — pressed against the limit`);
      else valEl.removeAttribute("title");
    }
    const edited = collectChangedBounds({ [key]: catalogBounds[key] }, { [key]: { lo: b.lo, hi: b.hi } })[key] != null;
    const chips = [];
    if (edited) chips.push(`<span class="pill warn" title="the editable bounds differ from the typology's published bounds — Save bounds writes them to their YAML home">edited</span>`);
    if (rejected[key]) chips.push(rejectedChipHtml(rejected[key]));
    const c = row.querySelector('[data-role="chips"]');
    if (c) c.innerHTML = chips.join("");
  }
  function repaintAll() { for (const e of entries) repaintRow(e.key); }

  // ── save bounds (two-step arm -> POST -> render; rejections surface per knob) ────────
  let armed = false;
  function refreshSave(face) {
    const changed = collectChangedBounds(catalogBounds, rowBounds);
    const n = Object.keys(changed).length;
    if (face != null) saveBtn.textContent = face;
    saveBtn.disabled = armed ? false : (n === 0 || backendDark);
    saveBtn.title = armed ? "click again to confirm the write"
      : backendDark ? "the preview API has not answered yet — saving stays off until the server responds"
      : n === 0 ? "no rows differ from the typology's catalog bounds"
      : `write ${n} changed bound row${n === 1 ? "" : "s"} to their YAML home`;
    if (saveHint) saveHint.textContent = armed ? "" : (n ? `${n} row${n === 1 ? "" : "s"} edited` : "");
    if (saveMsg && !armed) saveMsg.textContent = "";
  }
  saveBtn.onclick = async () => {
    const step = armStep(armed ? "armed" : "idle", "click");
    if (!step.fire) {                                   // click 1: arm (5 s auto-disarm, kill-run style)
      armed = true;
      if (armTimer) clearTimeout(armTimer);
      saveBtn.textContent = "Confirm save";
      const changed = collectChangedBounds(catalogBounds, rowBounds);
      const n = Object.keys(changed).length;
      const files = [...new Set(Object.keys(changed)
        .map(k => { const e = entries.find(x => x.key === k); return e && e.boundsSource && e.boundsSource.file; })
        .filter(Boolean))];
      if (saveMsg) saveMsg.innerHTML =
        `<span class="warn-text">click again to confirm — writes ${n} edited bound row${n === 1 ? "" : "s"} to ${files.length ? esc(files.join(", ")) : "the typology's YAML home"}</span>`;
      refreshSave();
      armTimer = setTimeout(() => { armed = false; refreshSave("Save bounds"); }, 5000);
      return;
    }
    armed = false;
    if (armTimer) { clearTimeout(armTimer); armTimer = null; }
    const changed = collectChangedBounds(catalogBounds, rowBounds);
    saveBtn.textContent = "Save bounds";
    if (!Object.keys(changed).length) { refreshSave(); return; }
    saveBtn.disabled = true;
    if (saveMsg) saveMsg.textContent = "saving…";
    const r = await postJson("/api/save-bounds", saveBoundsPayload(configName, changed));
    if (!ROOT.isConnected) return;
    saveResult.innerHTML = saveResultHtml(r);
    if (r && r.ok === true) {
      rejected = {};
      for (const a of r.applied || []) {                // the YAML is the new home of these bounds
        if (a && a.key != null && a.to && isFinite(Number(a.to.lo)) && isFinite(Number(a.to.hi))) {
          catalogBounds[a.key] = { lo: Number(a.to.lo), hi: Number(a.to.hi) };
          rowBounds[a.key] = { ...catalogBounds[a.key] };
        }
      }
      repaintAll();
      setDark(false);
    } else if (r && r.ok === false) {
      rejected = {};
      for (const rej of r.rejected || []) if (rej && rej.key != null) rejected[String(rej.key)] = rej.reason ?? "";
      repaintAll();
    } else {
      setDark(true, String((r && r.error) || "save failed"));
    }
    refreshSave("Save bounds");
  };

  // ── row wiring (event delegation: inputs, commits, resets) ─────────────────────────
  function warnChip(row, msg) {
    const c = row && row.querySelector('[data-role="chips"]');
    if (!c) return;
    c.insertAdjacentHTML("beforeend",
      `<span class="pill warn" data-role="warn" title="${esc(msg)}">${esc(msg.length > 26 ? "invalid bound" : msg)}</span>`);
    setTimeout(() => { const w = c.querySelector('[data-role="warn"]'); if (w) w.remove(); }, 3500);
  }

  knobsEl.addEventListener("input", ev => {
    const row = ev.target.closest(".sbox-row");
    if (!row) return;
    const key = row.dataset.key;
    const role = ev.target.dataset.role;
    const b = rowBounds[key];
    if (role === "slider") {
      const v = clampKnob(Number(ev.target.value), b.lo, b.hi);
      knobs[key] = v;
      const valEl = row.querySelector('[data-role="val"]');
      const at = atLimitEdge(v, b.lo, b.hi);
      if (valEl) {
        valEl.textContent = fmtKnobValue(v, b.lo, b.hi);
        valEl.classList.toggle("at-limit", !!at);
        valEl.dataset.at = at || "";
        if (at) valEl.setAttribute("title", `within 2% of the ${at === "lo" ? "minimum" : "maximum"} bound — pressed against the limit`);
        else valEl.removeAttribute("title");
      }
      request2d(timingDecision(slowNow, "input"));
      if (!slowNow) arm3d();                                          // held drag: 3D follows after the idle
      return;
    }
    // number inputs may only COMMIT (change): free typing never reverts mid-keystroke.
    if (role === "lo" || role === "hi") return;
  });

  knobsEl.addEventListener("change", ev => {
    const row = ev.target.closest(".sbox-row");
    if (!row) return;
    const key = row.dataset.key;
    const role = ev.target.dataset.role;
    const b = rowBounds[key];
    if (role === "lo" || role === "hi") {
      const out = boundEditOutcome(role, b.lo, b.hi, ev.target.value === "" ? NaN : Number(ev.target.value));
      if (!out.ok) {
        ev.target.value = numAttr(role === "lo" ? b.lo : b.hi);
        warnChip(row, out.msg);
        return;
      }
      rowBounds[key] = { lo: out.lo, hi: out.hi };
      knobs[key] = clampKnob(knobs[key], out.lo, out.hi);
      repaintRow(key);
    }
    request2d(timingDecision(slowNow, "release"));
    arm3d();
    writeUrl();
    refreshSave();
  });

  knobsEl.addEventListener("click", ev => {
    const btn = ev.target.closest('[data-role="reset"]');
    if (!btn) return;
    const row = btn.closest(".sbox-row");
    const key = row.dataset.key;
    rowBounds[key] = { ...catalogBounds[key] };
    delete rejected[key];
    knobs[key] = clampKnob(knobs[key], rowBounds[key].lo, rowBounds[key].hi);
    const lo = row.querySelector('[data-role="lo"]'), hi = row.querySelector('[data-role="hi"]');
    if (lo) lo.value = numAttr(rowBounds[key].lo);
    if (hi) hi.value = numAttr(rowBounds[key].hi);
    repaintRow(key);
    request2d(timingDecision(slowNow, "release"));
    arm3d();
    writeUrl();
    refreshSave();
  });

  // ── brief select: changing re-previews everything ──────────────────────────────────
  briefEl.addEventListener("change", () => {
    briefSel = briefEl.value;
    drawPayload(lastPayload || { section: {}, mouth: {} }, lastPayload ? null : "loading…");
    fire2d();
    arm3d(150);
    writeUrlNow();
    refreshSave();
  });

  // ── shadows toggle (persisted, shared with every other 3D surface) ─────────────────
  if (shBox) shBox.onchange = async () => {
    try { localStorage.setItem(SHADOW_KEY, shBox.checked ? "1" : "0"); } catch { /* private mode */ }
    if (player3d) {
      if (player3d.dispose) player3d.dispose();
      player3d = null;
      cv3d.innerHTML = `<div class="view3d-fallback">loading…</div>`;
      arm3d(50);
    }
  };

  // ── cleanup: timers/listeners never outlive the route (evolution's {once:true} rule) ─
  function cleanup() {
    if (raf2d) cancelAnimationFrame(raf2d);
    for (const t of [slowTimer, idle3d, urlTimer, armTimer]) if (t) clearTimeout(t);
    raf2d = 0; slowTimer = idle3d = urlTimer = armTimer = null;
    dirty2d = dirty3d = false;
  }
  window.addEventListener("hashchange", cleanup, { once: true });

  // ── boot: initial preview (the first answer also sets slowNow to the kind's real value) ──
  setUpdating(true);
  fire2d();
  arm3d(300);
  refreshSave();
}