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

import { css, niceTicks, el, fmt, measuredWidth, wallSection, mirrorRing } from "./charts.js";
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

/** The slider's EXPLORE range (2026-10-26, owner: "the sandbox is for seeing what a slider
 *  does"): the catalog's hard schema limits when it has them, otherwise the search box widened
 *  by its own span on each side. Non-negative quantities stay non-negative; a positive box keeps
 *  at least 20 % of its own minimum (a 0 Hz cutoff or a 0 mm length is not a horn). The range
 *  always contains the box and the current value. */
export function exploreRange(box, hard, value, key) {
  const lo0 = box ? Number(box.lo) : NaN, hi0 = box ? Number(box.hi) : NaN;
  const v = value == null ? NaN : Number(value);
  const okBox = isFinite(lo0) && isFinite(hi0);
  const span = okBox && hi0 > lo0 ? hi0 - lo0 : Math.max(Math.abs(isFinite(v) ? v : (okBox ? lo0 : 1)), 1);
  const base = okBox ? { lo: lo0, hi: hi0 } : { lo: isFinite(v) ? v : 0, hi: isFinite(v) ? v : 1 };
  let lo = base.lo - span, hi = base.hi + span;
  if (base.lo >= 0) lo = Math.max(lo, base.lo > 0 ? base.lo * 0.2 : 0);
  const k = String(key || "");
  if (/stop_deg$/.test(k)) { lo = Math.max(lo, 30); hi = Math.min(hi, 350); }
  else if (/_deg$/.test(k)) hi = Math.min(hi, 89);          // a wall/coverage angle stays below 90
  if (k === "q" || /_q$/.test(k)) hi = Math.min(hi, 1);    // OSSE q: 1 is the limit of the law
  const hlo = hard && hard.lo != null && isFinite(Number(hard.lo)) ? Number(hard.lo) : null;
  const hhi = hard && hard.hi != null && isFinite(Number(hard.hi)) ? Number(hard.hi) : null;
  if (hlo != null) lo = Math.max(lo, hlo);
  if (hhi != null) hi = Math.min(hi, hhi);
  if (okBox) { lo = Math.min(lo, lo0); hi = Math.max(hi, hi0); }
  if (isFinite(v)) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
  if (!(hi > lo)) hi = lo + 1;
  return { lo: rndNum(lo), hi: rndNum(hi) };
}

/** CSS custom properties that paint the search box as a band on the slider track. */
export function bandStyle(box, explore) {
  const lo = Number(explore && explore.lo), hi = Number(explore && explore.hi);
  if (!box || !(hi > lo)) return "";
  const pct = x => Math.max(0, Math.min(100, ((Number(x) - lo) / (hi - lo)) * 100)).toFixed(1) + "%";
  return `--band-lo:${pct(box.lo)};--band-hi:${pct(box.hi)}`;
}

/** True when the value sits outside the search box (a run would never visit it). */
export const outsideBox = (v, box) => !!box && isFinite(Number(v))
  && (Number(v) < Number(box.lo) - 1e-9 || Number(v) > Number(box.hi) + 1e-9);

/** The 3D caption, from the payload's own symmetry. */
export function shapeCaption(quadrants) {
  const q = String(quadrants || "");
  const what = q === "1" ? "Quarter model mirrored to the full horn"
    : (q === "12" || q === "14") ? "Half model mirrored to the full horn"
    : q === "1234" ? "Full-ring model (no mirroring)" : "Model";
  return `${what}. It hot-swaps while you work — the camera never resets.`;
}

/** "mouth 433 × 252 mm · depth 214 mm" from the payload's measured dims. */
export function dimsText(dims) {
  if (!dims || !isFinite(Number(dims.w)) || !isFinite(Number(dims.h))) return "";
  const r = x => Math.round(Number(x));
  return `mouth ${r(dims.w)} × ${r(dims.h)} mm` + (isFinite(Number(dims.d)) ? ` · depth ${r(dims.d)} mm` : "");
}

/** Morph knobs the sandbox offers (Ath Morph; the mesher owns the law). */
export const MORPH_KNOBS = [
  { key: "morph_width_mm", lo: 0, hi: 1500, step: "1", label: "target width, mm (full)" },
  { key: "morph_height_mm", lo: 0, hi: 1500, step: "1", label: "target height, mm (full)" },
  { key: "morph_corner_mm", lo: 0, hi: 300, step: "1", label: "corner radius, mm" },
  { key: "morph_exponent", lo: 2, hi: 16, step: "0.1", label: "superellipse exponent (target 3)" },
  { key: "morph_rate", lo: 0, hi: 10, step: "0.1", label: "how early the morph starts" },
  { key: "morph_fixed", lo: 0, hi: 1, step: "0.01", label: "fixed part of the length (0..1)" },
];
export const MORPH_TARGETS = [["0", "off"], ["1", "rectangle"], ["2", "circle"], ["3", "superellipse"]];

/** Ath's OS-SE GUIDING CURVE (OSSE only): a closed curve at a fraction of the length whose shape
 *  sets the coverage angle in EVERY direction. A superformula curve with pinched or pointed lobes
 *  makes the wall flare differently per azimuth, which folds it into the creases seen on Ath's
 *  CORE / TwinRay horns (add a rectangle Morph for the square mouth). `types` = the curve types a
 *  knob applies to. */
export const GCURVE_SPEC = {
  id: "gcurve", title: "Guiding curve (Ath OS-SE)", targetKey: "gcurve_type",
  targets: [["0", "off"], ["1", "superellipse"], ["2", "superformula"]],
  knobs: [
    { key: "gcurve_width_mm", lo: 50, hi: 1500, step: "1", label: "curve width, mm (full)", types: [1, 2] },
    { key: "gcurve_aspect_ratio", lo: 0.2, hi: 3, step: "0.01", label: "height / width", types: [1, 2] },
    { key: "gcurve_dist", lo: 0.05, hi: 1, step: "0.01", label: "where along the length the curve sits (0..1)", types: [1, 2] },
    { key: "gcurve_rot_deg", lo: -90, hi: 90, step: "1", label: "rotation, deg", types: [1, 2] },
    { key: "gcurve_se_n", lo: 1, hi: 20, step: "0.1", label: "superellipse exponent (2 = ellipse, high = rectangle)", types: [1] },
    { key: "gcurve_sf_a", lo: 0.2, hi: 3, step: "0.01", label: "superformula a", types: [2] },
    { key: "gcurve_sf_b", lo: 0.2, hi: 3, step: "0.01", label: "superformula b", types: [2] },
    { key: "gcurve_sf_m1", lo: 0, hi: 12, step: "1", label: "lobes (m1)", types: [2] },
    { key: "gcurve_sf_m2", lo: 0, hi: 12, step: "1", label: "lobes (m2)", types: [2] },
    { key: "gcurve_sf_n1", lo: 0.1, hi: 20, step: "0.1", label: "n1: small = pinched / star, large = round", types: [2] },
    { key: "gcurve_sf_n2", lo: 0.1, hi: 20, step: "0.1", label: "n2: cos-term sharpness", types: [2] },
    { key: "gcurve_sf_n3", lo: 0.1, hi: 20, step: "0.1", label: "n3: sin-term sharpness", types: [2] },
  ],
  presets: [
    { name: "pinched 4-lobe", type: 2, vals: { gcurve_sf_m1: 4, gcurve_sf_m2: 4, gcurve_sf_n1: 0.5, gcurve_sf_n2: 1, gcurve_sf_n3: 1, gcurve_sf_a: 1, gcurve_sf_b: 1 } },
    { name: "diamond", type: 2, vals: { gcurve_sf_m1: 4, gcurve_sf_m2: 4, gcurve_sf_n1: 1, gcurve_sf_n2: 1, gcurve_sf_n3: 1, gcurve_sf_a: 1, gcurve_sf_b: 1 } },
    { name: "soft square", type: 2, vals: { gcurve_sf_m1: 4, gcurve_sf_m2: 4, gcurve_sf_n1: 4, gcurve_sf_n2: 4, gcurve_sf_n3: 4, gcurve_sf_a: 1, gcurve_sf_b: 1 } },
    { name: "rectangle", type: 1, vals: { gcurve_se_n: 8 } },
  ],
};

/** The knobs of a guiding-curve type (pure). */
export const gcurveKnobsFor = type => GCURVE_SPEC.knobs.filter(k => k.types.includes(Number(type)));

/** The search box a Morph knob gets when "search this" is ticked: ±25 % around the value,
 *  inside the knob's explore range. */
export function morphSearchBox(value, lo, hi) {
  const v = Number(value);
  const d = Math.max(Math.abs(v) * 0.25, (hi - lo) * 0.02);
  return { lo: rndNum(Math.max(lo, v - d)), hi: rndNum(Math.min(hi, v + d)) };
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
  const ex = e.explore || null;                      // explore mode: the slider spans the explore range
  const at = ex ? null : atLimitEdge(e.value, b.lo, b.hi);
  if (ex && outsideBox(e.value, b)) chips.push(OUT_OF_BOX_CHIP);
  const title = mergedKnobTitle(doc, key) ?? String(key);
  const step = sliderStep(ex ? ex.lo : b.lo, ex ? ex.hi : b.hi);
  const sMin = ex ? ex.lo : b.lo, sMax = ex ? ex.hi : b.hi;
  return `<div class="sbox-row" data-key="${esc(key)}">`
    + `<span class="mono sbox-kname" tabindex="0" title="${esc(title)}">${esc(key)}</span>`
    + `<input class="sbox-num" type="number" step="any" data-role="lo" aria-label="${esc(key)} — editable minimum bound" value="${numAttr(b.lo)}">`
    + `<input class="sbox-slider${ex ? " banded" : ""}" type="range" data-role="slider" aria-label="${esc(key)} value" min="${numAttr(sMin)}" max="${numAttr(sMax)}" step="${esc(step)}" value="${numAttr(e.value)}"${ex ? ` style="${bandStyle(b, ex)}"` : ""}>`
    + `<input class="sbox-num" type="number" step="any" data-role="hi" aria-label="${esc(key)} — editable maximum bound" value="${numAttr(b.hi)}">`
    + (ex ? `<input class="sbox-num sbox-valin" type="number" step="any" data-role="val" aria-label="${esc(key)} value — type any number" value="${numAttr(Number(e.value))}">`
      : `<span class="sbox-val num${at ? " at-limit" : ""}" data-role="val" data-at="${esc(at || "")}"`
        + (at ? ` title="within 2% of the ${at === "lo" ? "minimum" : "maximum"} bound — pressed against the limit"` : "")
        + `>${esc(fmtKnobValue(e.value, b.lo, b.hi))}</span>`)
    + `<span class="sbox-chips" data-role="chips">${chips.join("")}</span>`
    + `<button type="button" class="sbox-reset" data-role="reset" aria-label="${esc(key)} — restore the typology's published bounds"`
    + ` title="Restore the typology's published bounds (${esc(fmt(Number(cat.lo)))}..${esc(fmt(Number(cat.hi)))})">↺</button>`
    + `</div>`;
}

const OUT_OF_BOX_CHIP = `<span class="pill warn" data-role="oob" title="outside the search box (the band on the slider): a search run would never visit this value">outside search</span>`;

/** A knob the config FIXES in search (search: false, or no bounds row): explore it here; the
 *  run keeps the config's value. */
export function fixedRowHtml(e) {
  const key = String(e.key);
  const title = mergedKnobTitle(e.doc || null, key) ?? String(key);
  const ex = e.explore;
  return `<div class="sbox-row sbox-fixed" data-key="${esc(key)}" data-mode="fixed">`
    + `<span class="mono sbox-kname" tabindex="0" title="${esc(title)}">${esc(key)}</span>`
    + `<span class="muted sbox-fixtag" title="fixed in search: a run uses the config's value (${esc(fmt(Number(e.pinned)))})">fixed</span>`
    + `<input class="sbox-slider" type="range" data-role="slider" aria-label="${esc(key)} value" min="${numAttr(ex.lo)}" max="${numAttr(ex.hi)}" step="${esc(sliderStep(ex.lo, ex.hi))}" value="${numAttr(e.value)}"${e.locked ? " disabled" : ""}>`
    + `<span></span>`
    + (e.locked ? `<span class="sbox-val num" data-role="val" title="search limits on: a run holds this value">${esc(fmtKnobValue(e.value, ex.lo, ex.hi))}</span>`
      : `<input class="sbox-num sbox-valin" type="number" step="any" data-role="val" aria-label="${esc(key)} value — type any number" value="${numAttr(Number(e.value))}">`)
    + `<span class="sbox-chips" data-role="chips">${Number(e.value) !== Number(e.pinned) ? `<span class="pill warn" title="differs from the config's fixed value ${esc(fmt(Number(e.pinned)))}">changed</span>` : ""}</span>`
    + `<button type="button" class="sbox-reset" data-role="unfix" aria-label="${esc(key)} — back to the config's fixed value" title="back to the config's fixed value (${esc(fmt(Number(e.pinned)))})">↺</button>`
    + `</div>`;
}

/** One Morph row: [name | search toggle | slider | box | value | chips | (blank)]. */
export function morphRowHtml(m, value, inSearch, limited) {
  const box = inSearch ? morphSearchBox(value, m.lo, m.hi) : null;
  const locked = !!limited && !box;                 // search limits on: only searched knobs move
  const rng = limited && box ? box : m;
  return `<div class="sbox-row sbox-morph" data-key="${esc(m.key)}" data-mode="morph">`
    + `<span class="mono sbox-kname" tabindex="0" title="${esc(m.label)}">${esc(m.key)}</span>`
    + `<label class="sbox-fixtag" title="add this knob to the typology's search (Save writes it to the YAML)"><input type="checkbox" data-role="msearch"${inSearch ? " checked" : ""}> search</label>`
    + `<input class="sbox-slider${box && !limited ? " banded" : ""}" type="range" data-role="slider" aria-label="${esc(m.key)} value" min="${rng.lo}" max="${rng.hi}" step="${m.step}" value="${numAttr(Number(value))}"${box && !limited ? ` style="${bandStyle(box, m)}"` : ""}${locked ? " disabled" : ""}>`
    + `<span class="muted sbox-box" data-role="mbox">${box ? `${esc(fmt(box.lo))}..${esc(fmt(box.hi))}` : ""}</span>`
    + (limited ? `<span class="sbox-val num" data-role="val">${esc(fmtKnobValue(Number(value), m.lo, m.hi))}</span>`
      : `<input class="sbox-num sbox-valin" type="number" step="any" data-role="val" aria-label="${esc(m.key)} value — type any number" value="${numAttr(Number(value))}">`)
    + `<span class="sbox-chips" data-role="chips"></span><span></span>`
    + `</div>`;
}

/** Show a value in a row's value cell (a plain span, or the free-mode number box). */
export function setValText(el, text) {
  if (!el) return;
  if (el.tagName === "INPUT") { if (document.activeElement !== el) el.value = String(text).replace(/[^0-9eE+\-.]/g, ""); }
  else el.textContent = text;
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
    // PRESERVE each plane's own point order (throat -> mouth for outer, mouth -> throat for the
    // reversed inner). Sorting by z was the defect: a rollback meridian is NOT monotone in z, so
    // the sorted loop self-intersected and the even-odd fill broke into the striped fringe the
    // owner saw on the vertical plane.
    const clean = pts => (pts || []).filter(p => Array.isArray(p) && p.length >= 2 && isFinite(p[0]) && isFinite(p[1]));
    const outer = clean(d.outer), inner = clean(d.inner).reverse();
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
  const chain = pts => mirrorRing(pts)
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
  const col = (payload && payload.__color) || css("--best");
  if (band) {
    el("path", { d: band, fill: col, "fill-rule": "evenodd", "fill-opacity": 0.22, stroke: "none" }, svg);
    el("path", { d: band, fill: "none", stroke: col, "stroke-width": 1.6, "fill-rule": "evenodd" }, svg);
  }
  const innerPts = mirrorRing((mouth || {}).inner);
  if (innerPts.length) {
    const ip = innerPts.map(([x, y], i) => (i ? "L" : "M") + X(x).toFixed(1) + "," + Y(y).toFixed(1)).join("") + "Z";
    el("path", { d: ip, fill: "none", stroke: css("--muted"), "stroke-width": 1.1 }, svg);
  }
  const lbl = el("text", { x: X(R), y: H - 1, "text-anchor": "end" }, svg);
  lbl.textContent = "width mm";
}

/** A catalog-shaped typology built from the config file itself (``/api/configs``), for configs
 *  the generated parameter catalog does not list yet (e.g. a new campaign folder). Knob docs are
 *  then absent; the sliders, bounds and preview work the same. */
export function typologyFromConfigEntry(c) {
  if (!c) return null;
  const bounds = c.bounds || {}, seed = c.seed_params || {};
  const bounds_index = {};
  for (const [k, b] of Object.entries(bounds)) {
    if (b && typeof b === "object") bounds_index[k] = { lo: b.lo, hi: b.hi, search: b.search !== false, file: c.path, key: `bounds.${k}` };
  }
  const keys = [...new Set([...Object.keys(seed), ...Object.keys(bounds)])];
  return {
    name: c.name, group: c.group || "", symmetry: c.symmetry || "", family: c.family,
    kind: c.generator ? ((c.generator_block || {}).name === "grid" ? "rows" : "generator") : "native",
    description: `${c.path} — not in the parameter catalog yet, so the knobs are read from the config file (regenerate with tools/gen_param_catalog.py --write for full tooltips).`,
    brief_file: c.brief_file, bounds_index,
    knobs: keys.map(k => ({ knob: k, default: seed[k] ?? (bounds[k] || {}).lo, hard: null,
                            search: bounds[k] ? { lo: bounds[k].lo, hi: bounds[k].hi, search: bounds[k].search !== false } : null })),
  };
}

async function typologyFromConfig(configName) {
  try {
    const cfgs = await fetchJson("/api/configs");
    return typologyFromConfigEntry((cfgs || []).find(c => c.name === configName));
  } catch { return null; }
}

export async function viewTypologySandbox(root, configName) {
  const ROOT = root;
  ROOT.innerHTML = `<p class="muted">Loading the sandbox…</p>`;
  const cat = await loadParamCatalog();               // never throws; a failed load degrades below
  let t = cat && cat.typologies && cat.typologies[configName];
  if (!t) t = await typologyFromConfig(configName);   // new configs: read the YAML itself
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
  // 2026-10-26: sliders explore a WIDE range; the search box is a band on the track.
  const knobDoc = Object.fromEntries((t.knobs || []).map(k => [k.knob, k]));
  const explore = {};
  for (const e of entries) {
    const k = knobDoc[e.key];
    explore[e.key] = exploreRange({ lo: e.lo, hi: e.hi }, k && k.hard,
      k && typeof k.default === "number" ? k.default : null, e.key);
  }
  // knobs the config fixes in search (no searched bounds row): explorable here, never saved
  const SKIP_FIXED = new Set(["r0_mm", "n_phi", "n_s", "span"]);
  const searchKeys = new Set(entries.map(e => e.key));
  const fixedEntries = (t.knobs || []).flatMap(k => {
    if (!k || searchKeys.has(k.knob) || SKIP_FIXED.has(k.knob)) return [];
    const d = k.default;
    const list = Array.isArray(d) && d.length === 1 && typeof d[0] === "number";
    const v = list ? d[0] : d;
    if (typeof v !== "number" || !isFinite(v)) return [];
    return [{ key: k.knob, pinned: v, list, doc: docFor(configName, k.knob),
              explore: exploreRange(null, k.hard, v, k.knob) }];
  });
  const fixedVals = Object.fromEntries(fixedEntries.map(f => [f.key, f.pinned]));
  // Morph: offered for the knobs this config does NOT already declare (ath_core declares them)
  const declared = new Set((t.knobs || []).map(k => k.knob));
  const morphKnobs = MORPH_KNOBS.filter(m => !declared.has(m.key));
  const morphOffered = !declared.has("morph_target");
  const morph = { target: 0, shrink: 0, vals: {}, search: new Set(), capable: false };
  const gcOffered = !declared.has("gcurve_type");
  const gc = { type: 0, vals: {}, search: new Set(), capable: false };
  // the switch: FREE sandbox (any value) vs SEARCH LIMITS (only what a run can reach); per typology
  const LIMIT_KEY = "hl-sbox-limit:" + configName;
  let limited = false;
  try { limited = localStorage.getItem(LIMIT_KEY) === "1"; } catch { /* private mode: free */ }
  const rangeOf = key => (limited ? rowBounds[key] : explore[key]);

  let briefs = [];
  try { briefs = await fetchJson("/api/briefs"); } catch { briefs = []; }
  if (!ROOT.isConnected) return;                      // navigated away while loading

  // ── state, hydrated from the route query (survives theme/resize route() re-runs) ──
  const q = readQueryState(location.hash);
  let briefSel = (q.brief && briefs.some(b => b.name === q.brief)) ? q.brief
    : (briefs.find(b => b.name === briefFileStem(t.brief_file)) || briefs[0] || { name: "" }).name;
  let rowBounds = Object.fromEntries(entries.map(e => [e.key, (q.bnds && q.bnds[e.key]) || { lo: e.lo, hi: e.hi }]));
  const knobs = initialKnobValues(entries, q.knobs || {});
  for (const e of entries) {
    for (const r of [rowBounds[e.key]]) explore[e.key] = { lo: Math.min(explore[e.key].lo, r.lo), hi: Math.max(explore[e.key].hi, r.hi) };
    const fromUrl = q.knobs && typeof q.knobs[e.key] === "number" ? q.knobs[e.key] : knobs[e.key];
    knobs[e.key] = clampKnob(fromUrl, explore[e.key].lo, explore[e.key].hi);
  }
  for (const f of fixedEntries) if (q.knobs && typeof q.knobs[f.key] === "number") fixedVals[f.key] = q.knobs[f.key];
  if (limited) {
    for (const e of entries) knobs[e.key] = clampKnob(knobs[e.key], rowBounds[e.key].lo, rowBounds[e.key].hi);
    for (const f of fixedEntries) fixedVals[f.key] = f.pinned;
  }
  if (q.knobs && gcOffered) {
    if (typeof q.knobs.gcurve_type === "number") gc.type = Math.round(q.knobs.gcurve_type);
    for (const k of GCURVE_SPEC.knobs) if (typeof q.knobs[k.key] === "number") gc.vals[k.key] = q.knobs[k.key];
  }
  if (q.knobs && morphOffered) {
    if (typeof q.knobs.morph_target === "number") morph.target = Math.round(q.knobs.morph_target);
    if (typeof q.knobs.morph_allow_shrinkage === "number") morph.shrink = q.knobs.morph_allow_shrinkage ? 1 : 0;
    for (const m of morphKnobs) if (typeof q.knobs[m.key] === "number") morph.vals[m.key] = q.knobs[m.key];
  }
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
      <span id="sbox-dims" class="num"></span>
      <span id="sbox-env"></span>
      <span id="sbox-updating" hidden><span class="pill warn" style="cursor:default">updating…</span></span>
      <span id="sbox-dark" class="muted" hidden>${esc(EMPTY_PREVIEW)} — sliders still work from the typology's published bounds</span>
      <span id="sbox-notes" class="muted" style="font-size:0.74rem"></span>
    </div>
    <div class="sbox-grid">
      <div class="fig sbox-side-fig">
        <h3>Side view: wall cross-section</h3>
        <div class="cap">Horizontal plane right, vertical plane mirrored left, throat at the bottom (mm). Filled band = wall thickness.</div>
        <svg id="sbox-side"></svg>
      </div>
      <div class="fig sbox-front-fig">
        <h3>Front view: mouth outline</h3>
        <div class="cap">Mouth ring (mm); dashed: the brief's size envelope.</div>
        <div id="sbox-frontnote" class="cap muted" hidden></div>
        <svg id="sbox-front"></svg>
      </div>
      <div class="fig sbox-3d-fig">
        <div class="fig-head">
          <h3>3D shape</h3>
          <label class="evo-opt" title="the same persisted wall-shadows toggle as every other 3D view">
            <input type="checkbox" id="sbox-shadow" checked> wall shadows</label>
        </div>
        <div class="cap" id="sbox-3dcap">${esc(shapeCaption(t.symmetry === "full" ? "1234" : ""))}</div>
        <div class="cap warn-text" id="sbox-3dwarn" hidden></div>
        <div id="sbox-3d" data-v3d class="sbox-3dwrap"><div class="view3d-fallback">loading…</div></div>
      </div>
      <div class="card sbox-knobs-card" id="sbox-slider-card">
        <div class="fig-head">
          <h3>Shape parameters</h3>
          <span class="btn-row">
            <span id="sbox-save-hint" class="muted" style="font-size:0.76rem"></span>
            <label class="evo-opt" title="show the min / max boxes that set each knob's search box (the band on the slider)"><input type="checkbox" id="sbox-editbox"> edit search boxes</label>
            <label class="evo-opt" title="on: sliders move only inside each search box and fixed knobs stay at the run's values (what a search can reach); off: a free sandbox — any value, type it in the value box"><input type="checkbox" id="sbox-limit"${limited ? " checked" : ""}> search limits only</label>
            <button id="sbox-save" class="primary" ${entries.length ? "" : "disabled"}>Save bounds</button>
          </span>
        </div>
        <details class="sbox-help"><summary>how the sliders work</summary><p class="cap muted"><b>Free sandbox</b> (switch off): drag any slider or type any value in the value box — sliders reach well past what a search explores. <b>Search limits only</b> (switch on): sliders stay inside the search box and fixed knobs stay at the run's values. The shaded band on each track is the <b>search box</b> (the range a run explores); edit it with the min / max boxes, ↺ restores the published box, and Save writes edited boxes to the typology's YAML. Rows marked <b>fixed</b> are held constant by a run; you can still explore them here.</p></details>
        <div id="sbox-knobs" class="sbox-knobs-list">${entries.map(e => sliderRowHtml({
          key: e.key, doc: e.doc, catalog: catalogBounds[e.key], bounds: rowBounds[e.key],
          value: knobs[e.key], edited: false, explore: limited ? null : explore[e.key],
        })).join("") || `<p class="muted">This typology has no searchable shape parameters — its geometry is authored outside the knob search.</p>`}${fixedEntries.map(f => fixedRowHtml({ ...f, value: fixedVals[f.key], locked: limited })).join("")}</div>
        <div id="sbox-morph" class="sbox-morph-card" hidden></div>
        <div id="sbox-gcurve" class="sbox-morph-card" hidden></div>
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
  const dimsEl = document.getElementById("sbox-dims");
  const cap3d = document.getElementById("sbox-3dcap");
  const warn3d = document.getElementById("sbox-3dwarn");
  const morphEl = document.getElementById("sbox-morph");

  emptySvg(sideSvg, "loading the preview…");
  emptySvg(frontSvg, "loading the preview…");

  // ── timing: ONE rAF-throttled 2D lane, ONE idle-scheduled 3D lane, ONE slow debounce ──
  let raf2d = 0, inFlight2d = false, dirty2d = false;
  let slowTimer = null, idle3d = null, inFlight3d = false, dirty3d = false;
  let urlTimer = null, armTimer = null, player3d = null;

  /** What the preview gets: searched knobs, fixed knobs (lists re-wrapped), active Morph. */
  const currentKnobsJson = (forUrl) => {
    const o = {};
    for (const e of entries) o[e.key] = clampKnob(knobs[e.key], rangeOf(e.key).lo, rangeOf(e.key).hi);
    for (const f of fixedEntries) {
      if (fixedVals[f.key] === f.pinned) continue;               // unchanged: the config's own value
      o[f.key] = f.list && !forUrl ? [fixedVals[f.key]] : fixedVals[f.key];
    }
    if (gcOffered && gc.type > 0) {
      // the mesher solves the coverage angle against the guiding curve, so the cross-section
      // must stay circular (exponent 2, aspect 1); the curve's own aspect ratio shapes the outline
      o.exponent = 2; o.aspect_ratio = 1;
      o.gcurve_type = gc.type;
      for (const k of gcurveKnobsFor(gc.type)) if (typeof gc.vals[k.key] === "number") o[k.key] = gc.vals[k.key];
    }
    if (morphOffered && morph.target > 0) {
      o.morph_target = morph.target;
      o.morph_allow_shrinkage = morph.shrink;
      for (const m of morphKnobs) if (typeof morph.vals[m.key] === "number") o[m.key] = morph.vals[m.key];
    }
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
    const refused = Array.isArray(payload.rejected) && payload.rejected.length > 0;
    payload.__color = refused ? css("--bad") : null;
    const loop = combinedSectionLoop(payload.section);
    if (loop) wallSection(sideSvg, [{ profile: loop, color: refused ? css("--bad") : css("--best"), filled: true }], { H: 330 });
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
    const refusedChip = refused
      ? `<span class="pill bad" title="${esc(payload.rejected.join(" · "))}">a search would refuse this shape: ${esc(String(payload.rejected[0]).slice(0, 70))}</span>` : "";
    if (envEl) envEl.innerHTML = (envChip ? envChip.html : "") + refusedChip;
    if (dimsEl) dimsEl.textContent = dimsText(payload.dims);
    if (cap3d && payload.quadrants) cap3d.textContent = shapeCaption(payload.quadrants);
    if (payload.morph_capable && morphOffered && !morph.capable) { morph.capable = true; renderMorph(); }
    if (payload.gcurve_capable && gcOffered && !gc.capable) { gc.capable = true; renderGc(); }
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
        show3dWarnings(s3.warnings);
        player3d.applyMesh(s3.verts, s3.tris, payload.quadrants);
      } else {
        show3dWarnings(s3.warnings);
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

  function show3dWarnings(ws) {
    if (!warn3d) return;
    const list = Array.isArray(ws) ? ws.filter(Boolean) : [];
    warn3d.hidden = !list.length;
    warn3d.textContent = list.join(" · ");
  }

  // ── Morph section (offered when the endpoint says the config can take Morph) ──────────
  function morphDefaults() {
    const d = (lastPayload && lastPayload.dims) || {};
    const base = { morph_width_mm: Math.round(Number(d.w) || 300), morph_height_mm: Math.round(Number(d.h) || 300),
                   morph_corner_mm: 30, morph_exponent: 4, morph_rate: 3, morph_fixed: 0 };
    for (const m of morphKnobs) if (typeof morph.vals[m.key] !== "number") morph.vals[m.key] = base[m.key];
  }
  function renderMorph() {
    if (!morphEl || !morph.capable || !morphKnobs.length) return;
    morphEl.hidden = false;
    const on = morph.target > 0;
    if (on) morphDefaults();
    morphEl.innerHTML = `<div class="fig-head"><h3>Morph</h3>
        <span class="btn-row">
          <label class="evo-opt">target <select data-role="mtarget" aria-label="Morph target shape">
            ${MORPH_TARGETS.map(([v, n]) => `<option value="${v}"${Number(v) === morph.target ? " selected" : ""}>${n}</option>`).join("")}
          </select></label>
          <label class="evo-opt" title="without this, a target smaller than the horn's own mouth changes nothing (the mesher's rule)"><input type="checkbox" data-role="mshrink"${morph.shrink ? " checked" : ""}> allow shrinking</label>
        </span></div>
      <details class="sbox-help"><summary>what Morph does</summary><p class="cap muted">Ath Morph reshapes the mouth outline toward a target (rectangle / circle / superellipse) over the last part of the horn. Width and height are the FULL target mouth. Tick <b>search</b> to add a knob to this typology's search; Save writes it to the YAML with the target shape fixed for the run (a run should not flip shapes).</p></details>
      ${on ? `<div class="sbox-knobs-list">${morphKnobs.map(m => morphRowHtml(m, morph.vals[m.key], morph.search.has(m.key), limited)).join("")}</div>`
           : `<p class="muted" style="font-size:0.8rem">Pick a target shape to start.</p>`}`;
  }
  function morphChanged(commit) {
    request2d(timingDecision(slowNow, commit ? "release" : "input"));
    if (commit || !slowNow) arm3d();
    if (commit) { writeUrl(); refreshSave(); }
  }
  if (morphEl) {
    morphEl.addEventListener("change", ev => {
      const role = ev.target.dataset.role;
      if (role === "mtarget") { morph.target = Number(ev.target.value) || 0; renderMorph(); morphChanged(true); return; }
      if (role === "mshrink") { morph.shrink = ev.target.checked ? 1 : 0; morphChanged(true); return; }
      const row = ev.target.closest(".sbox-row");
      if (!row) return;
      if (role === "msearch") {
        if (ev.target.checked) morph.search.add(row.dataset.key); else morph.search.delete(row.dataset.key);
        renderMorph(); refreshSave(); return;
      }
      if (role === "slider") morphChanged(true);
      if (role === "val") {
        const v = Number(String(ev.target.value).replace(",", "."));
        if (isFinite(v)) { morph.vals[row.dataset.key] = v; renderMorph(); morphChanged(true); }
      }
    });
    morphEl.addEventListener("input", ev => {
      if (ev.target.dataset.role !== "slider") return;
      const row = ev.target.closest(".sbox-row");
      const m = morphKnobs.find(x => x.key === row.dataset.key);
      morph.vals[m.key] = Number(ev.target.value);
      const valEl = row.querySelector('[data-role="val"]');
      if (valEl) setValText(valEl, fmtKnobValue(morph.vals[m.key], m.lo, m.hi));
      if (morph.search.has(m.key)) {
        const box = morphSearchBox(morph.vals[m.key], m.lo, m.hi);
        ev.target.setAttribute("style", bandStyle(box, m));
        const b = row.querySelector('[data-role="mbox"]');
        if (b) b.textContent = `${fmt(box.lo)}..${fmt(box.hi)}`;
      }
      morphChanged(false);
    });
  }
  // ── Guiding-curve card (OSSE): same row/search mechanics as Morph ─────────────────────
  const gcEl = document.getElementById("sbox-gcurve");
  function gcDefaults() {
    const d = (lastPayload && lastPayload.dims) || {};
    const w = Math.round(Number(d.w) || 400), h = Math.round(Number(d.h) || 400);
    const base = { gcurve_width_mm: w, gcurve_aspect_ratio: rndNum(h / w), gcurve_dist: 0.6, gcurve_rot_deg: 0,
                   gcurve_se_n: 4, gcurve_sf_a: 1, gcurve_sf_b: 1, gcurve_sf_m1: 4, gcurve_sf_m2: 4,
                   gcurve_sf_n1: 0.5, gcurve_sf_n2: 1, gcurve_sf_n3: 1 };
    for (const k of GCURVE_SPEC.knobs) if (typeof gc.vals[k.key] !== "number") gc.vals[k.key] = base[k.key];
  }
  function renderGc() {
    if (!gcEl || !gc.capable) return;
    gcEl.hidden = false;
    const on = gc.type > 0;
    if (on) gcDefaults();
    const ks = gcurveKnobsFor(gc.type);
    gcEl.innerHTML = `<div class="fig-head"><h3>${esc(GCURVE_SPEC.title)}</h3>
        <span class="btn-row">
          <label class="evo-opt">curve <select data-role="gctype" aria-label="guiding curve type">
            ${GCURVE_SPEC.targets.map(([v, n]) => `<option value="${v}"${Number(v) === gc.type ? " selected" : ""}>${n}</option>`).join("")}
          </select></label>
        </span></div>
      <details class="sbox-help"><summary>what the guiding curve does</summary><p class="cap muted">A closed curve part-way along the horn whose shape sets the coverage angle in <b>every</b> direction, not just horizontal and vertical. While it is on, the cross-section is held circular (exponent 2, aspect 1 — the mesher's rule; use the curve's own height / width). Pinched or pointed superformula lobes make the wall flare differently per direction, which folds it into the creases on Ath's CORE / TwinRay horns — add a <b>rectangle Morph</b> for the square mouth.</p></details>
      <div class="sbox-presets">presets ${GCURVE_SPEC.presets.map((pr, i) => `<button type="button" class="sbox-reset" data-role="gcpreset" data-i="${i}">${esc(pr.name)}</button>`).join(" ")}</div>
      ${on ? `<div class="sbox-knobs-list">${ks.map(k => morphRowHtml(k, gc.vals[k.key], gc.search.has(k.key), limited)).join("")}</div>`
           : `<p class="muted" style="font-size:0.8rem">Pick a curve type or a preset to start.</p>`}`;
  }
  function gcChanged(commit) {
    request2d(timingDecision(slowNow, commit ? "release" : "input"));
    if (commit || !slowNow) arm3d();
    if (commit) { writeUrl(); refreshSave(); }
  }
  if (gcEl) {
    gcEl.addEventListener("click", ev => {
      const b = ev.target.closest('[data-role="gcpreset"]');
      if (!b) return;
      const pr = GCURVE_SPEC.presets[Number(b.dataset.i)];
      gc.type = pr.type;
      gcDefaults();
      Object.assign(gc.vals, pr.vals);
      renderGc(); gcChanged(true);
    });
    gcEl.addEventListener("change", ev => {
      const role = ev.target.dataset.role;
      if (role === "gctype") { gc.type = Number(ev.target.value) || 0; renderGc(); gcChanged(true); return; }
      const row = ev.target.closest(".sbox-row");
      if (!row) return;
      if (role === "msearch") {
        if (ev.target.checked) gc.search.add(row.dataset.key); else gc.search.delete(row.dataset.key);
        renderGc(); refreshSave(); return;
      }
      if (role === "slider") gcChanged(true);
      if (role === "val") {
        const v = Number(String(ev.target.value).replace(",", "."));
        if (isFinite(v)) { gc.vals[row.dataset.key] = v; renderGc(); gcChanged(true); }
      }
    });
    gcEl.addEventListener("input", ev => {
      if (ev.target.dataset.role !== "slider") return;
      const row = ev.target.closest(".sbox-row");
      const k = GCURVE_SPEC.knobs.find(x => x.key === row.dataset.key);
      gc.vals[k.key] = Number(ev.target.value);
      setValText(row.querySelector('[data-role="val"]'), fmtKnobValue(gc.vals[k.key], k.lo, k.hi));
      gcChanged(false);
    });
  }
  function gcAdds() {
    if (!(gc.type > 0) || !gc.search.size) return {};
    const add = { gcurve_type: { lo: gc.type, hi: gc.type, seed: gc.type, pinned: true } };
    for (const k of gcurveKnobsFor(gc.type)) {
      const v = gc.vals[k.key];
      add[k.key] = gc.search.has(k.key) ? { ...morphSearchBox(v, k.lo, k.hi), seed: v } : { lo: v, hi: v, seed: v, pinned: true };
    }
    return add;
  }

  /** The Morph rows "search" adds: ±25 % boxes + the target shape (and shrink flag) pinned. */
  function morphAdds() {
    if (!(morph.target > 0) || !morph.search.size) return {};
    const add = {
      morph_target: { lo: morph.target, hi: morph.target, seed: morph.target, pinned: true },
      morph_allow_shrinkage: { lo: morph.shrink, hi: morph.shrink, seed: morph.shrink, pinned: true },
    };
    for (const m of morphKnobs) {
      const v = morph.vals[m.key];
      if (morph.search.has(m.key)) add[m.key] = { ...morphSearchBox(v, m.lo, m.hi), seed: v };
      else add[m.key] = { lo: v, hi: v, seed: v, pinned: true };
    }
    return add;
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
      + buildQueryState({ brief: briefSel, knobs: currentKnobsJson(true), bnds: collectChangedBounds(catalogBounds, rowBounds) }));
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
    const b = rowBounds[key];
    if (!b) return;                                    // fixed / Morph rows repaint themselves
    explore[key] = { lo: Math.min(explore[key].lo, b.lo), hi: Math.max(explore[key].hi, b.hi) };
    const ex = rangeOf(key);
    const v = knobs[key] = clampKnob(knobs[key], ex.lo, ex.hi);
    const slider = row.querySelector('[data-role="slider"]');
    if (slider) {
      slider.min = numAttr(ex.lo); slider.max = numAttr(ex.hi);
      slider.step = String(sliderStep(ex.lo, ex.hi));
      slider.value = numAttr(v);
      if (!limited) slider.setAttribute("style", bandStyle(b, ex));
    }
    const valEl = row.querySelector('[data-role="val"]');
    const at = null;
    if (valEl) {
      setValText(valEl, fmtKnobValue(v, b.lo, b.hi));
      valEl.classList.toggle("at-limit", !!at);
      valEl.dataset.at = at || "";
      if (at) valEl.setAttribute("title", `within 2% of the ${at === "lo" ? "minimum" : "maximum"} bound — pressed against the limit`);
      else valEl.removeAttribute("title");
    }
    const edited = collectChangedBounds({ [key]: catalogBounds[key] }, { [key]: { lo: b.lo, hi: b.hi } })[key] != null;
    const chips = [];
    if (edited) chips.push(`<span class="pill warn" title="the editable bounds differ from the typology's published bounds — Save bounds writes them to their YAML home">edited</span>`);
    if (rejected[key]) chips.push(rejectedChipHtml(rejected[key]));
    if (outsideBox(v, b)) chips.push(OUT_OF_BOX_CHIP);
    const c = row.querySelector('[data-role="chips"]');
    if (c) c.innerHTML = chips.join("");
  }
  function repaintAll() { for (const e of entries) repaintRow(e.key); }

  // ── save bounds (two-step arm -> POST -> render; rejections surface per knob) ────────
  let armed = false;
  function refreshSave(face) {
    const changed = collectChangedBounds(catalogBounds, rowBounds);
    const n = Object.keys(changed).length + (Object.keys(morphAdds()).length ? morph.search.size : 0)
      + (Object.keys(gcAdds()).length ? gc.search.size : 0);
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
    const adds = { ...morphAdds(), ...gcAdds() };
    saveBtn.textContent = "Save bounds";
    if (!Object.keys(changed).length && !Object.keys(adds).length) { refreshSave(); return; }
    saveBtn.disabled = true;
    if (saveMsg) saveMsg.textContent = "saving…";
    const body = saveBoundsPayload(configName, changed);
    if (Object.keys(adds).length) body.add = adds;
    const r = await postJson("/api/save-bounds", body);
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
    if (role === "slider" && row.dataset.mode === "fixed") {
      const f = fixedEntries.find(x => x.key === key);
      fixedVals[key] = Number(ev.target.value);
      const valEl = row.querySelector('[data-role="val"]');
      if (valEl) setValText(valEl, fmtKnobValue(fixedVals[key], f.explore.lo, f.explore.hi));
      const c = row.querySelector('[data-role="chips"]');
      if (c) c.innerHTML = fixedVals[key] !== f.pinned ? `<span class="pill warn" title="differs from the config's fixed value ${esc(fmt(f.pinned))}">changed</span>` : "";
      request2d(timingDecision(slowNow, "input"));
      if (!slowNow) arm3d();
      return;
    }
    if (role === "slider") {
      const ex = rangeOf(key);
      const v = clampKnob(Number(ev.target.value), ex.lo, ex.hi);
      knobs[key] = v;
      const valEl = row.querySelector('[data-role="val"]');
      if (valEl) setValText(valEl, fmtKnobValue(v, ex.lo, ex.hi));
      const c = row.querySelector('[data-role="chips"]');
      const oob = c && c.querySelector('[data-role="oob"]');
      if (outsideBox(v, b) && c && !oob) c.insertAdjacentHTML("beforeend", OUT_OF_BOX_CHIP);
      if (!outsideBox(v, b) && oob) oob.remove();
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
    if (role === "val") {                               // free mode: any typed number
      const v = Number(String(ev.target.value).replace(",", "."));
      if (!isFinite(v)) { warnChip(row, "not a number — the edit was refused"); return; }
      if (row.dataset.mode === "fixed") {
        const f = fixedEntries.find(x => x.key === key);
        fixedVals[key] = v;
        f.explore = { lo: Math.min(f.explore.lo, v), hi: Math.max(f.explore.hi, v) };
        row.outerHTML = fixedRowHtml({ ...f, value: v, locked: limited });
      } else {
        explore[key] = { lo: Math.min(explore[key].lo, v), hi: Math.max(explore[key].hi, v) };
        knobs[key] = v;
        repaintRow(key);
      }
      request2d(timingDecision(slowNow, "release"));
      arm3d(); writeUrl();
      return;
    }
    if (role === "lo" || role === "hi") {
      const out = boundEditOutcome(role, b.lo, b.hi, ev.target.value === "" ? NaN : Number(ev.target.value));
      if (!out.ok) {
        ev.target.value = numAttr(role === "lo" ? b.lo : b.hi);
        warnChip(row, out.msg);
        return;
      }
      rowBounds[key] = { lo: out.lo, hi: out.hi };
      repaintRow(key);
    }
    request2d(timingDecision(slowNow, "release"));
    arm3d();
    writeUrl();
    refreshSave();
  });

  knobsEl.addEventListener("click", ev => {
    const unfix = ev.target.closest('[data-role="unfix"]');
    if (unfix) {
      const row = unfix.closest(".sbox-row");
      const f = fixedEntries.find(x => x.key === row.dataset.key);
      fixedVals[f.key] = f.pinned;
      row.outerHTML = fixedRowHtml({ ...f, value: f.pinned });
      request2d(timingDecision(slowNow, "release"));
      arm3d(); writeUrl();
      return;
    }
    const btn = ev.target.closest('[data-role="reset"]');
    if (!btn) return;
    const row = btn.closest(".sbox-row");
    const key = row.dataset.key;
    rowBounds[key] = { ...catalogBounds[key] };
    delete rejected[key];
    const lo = row.querySelector('[data-role="lo"]'), hi = row.querySelector('[data-role="hi"]');
    if (lo) lo.value = numAttr(rowBounds[key].lo);
    if (hi) hi.value = numAttr(rowBounds[key].hi);
    repaintRow(key);
    request2d(timingDecision(slowNow, "release"));
    arm3d();
    writeUrl();
    refreshSave();
  });

  // ── the free / search-limits switch ───────────────────────────────────────────────
  const editBoxEl = document.getElementById("sbox-editbox");
  if (editBoxEl) {
    try { editBoxEl.checked = localStorage.getItem("hl-sbox-editbox") === "1"; } catch { /* default off */ }
    knobsEl.classList.toggle("edit-boxes", editBoxEl.checked);
    editBoxEl.addEventListener("change", () => {
      knobsEl.classList.toggle("edit-boxes", editBoxEl.checked);
      try { localStorage.setItem("hl-sbox-editbox", editBoxEl.checked ? "1" : "0"); } catch { /* private */ }
    });
  }
  const limitEl = document.getElementById("sbox-limit");
  if (limitEl) limitEl.addEventListener("change", () => {
    limited = limitEl.checked;
    try { localStorage.setItem(LIMIT_KEY, limited ? "1" : "0"); } catch { /* private mode */ }
    if (limited) {
      for (const e of entries) knobs[e.key] = clampKnob(knobs[e.key], rowBounds[e.key].lo, rowBounds[e.key].hi);
      for (const f of fixedEntries) fixedVals[f.key] = f.pinned;
    }
    knobsEl.innerHTML = entries.map(e => sliderRowHtml({
      key: e.key, doc: e.doc, catalog: catalogBounds[e.key], bounds: rowBounds[e.key],
      value: knobs[e.key], edited: collectChangedBounds({ [e.key]: catalogBounds[e.key] }, { [e.key]: rowBounds[e.key] })[e.key] != null,
      explore: limited ? null : explore[e.key],
    })).join("") + fixedEntries.map(f => fixedRowHtml({ ...f, value: fixedVals[f.key], locked: limited })).join("");
    renderMorph();
    renderGc();
    request2d(timingDecision(slowNow, "release"));
    arm3d(); writeUrl();
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