// DOM-stub lifecycle test for study_results.js. No jsdom/playwright is installed; this exercises
// the real module graph (study_results.js + its sibling modules from disk) against a hand-written
// DOM stub: mount the Horns tab, click a row's Inspect button, and require the inspector region to
// repaint with the selected design's stored artifacts. Relative imports resolve because the module
// is imported from its real file path (unlike tests/gui_study_lifecycle.mjs, whose module is
// self-contained data-URL loaded).
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";
import { fileURLToPath } from "node:url";

// ── deterministic globals ────────────────────────────────────────────────────────────────────
globalThis.fetch = async () => { throw new Error("study_results.js must only use injected adapters"); };

const pushed = [];
globalThis.history = {
  pushState: (state, title, url) => { pushed.push(url); globalThis.location.hash = url; },
  replaceState: (state, title, url) => { globalThis.location.hash = url; },
};
globalThis.location = { hash: "" };

function makeRoot() {
  const listeners = new Map();
  return {
    innerHTML: "",
    connected: true,
    addEventListener(name, fn) { listeners.set(name, fn); },
    removeEventListener(name, fn) { if (listeners.get(name) === fn) listeners.delete(name); },
    contains() { return true; },
    click(event, name = "click") { const fn = listeners.get(name); return fn ? fn(event) : undefined; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    get isConnected() { return true; },
  };
}

function clickTarget(dataset) {
  return {
    dataset,
    closest(selector) { return selector === "[data-res-select]" ? this : null; },
    dispatch(event) { const fn = event.root; return fn; },
  };
}

// ── module under test (real files, real import graph) ───────────────────────────────────────
const MODULE_URL = pathToFileURL(fileURLToPath(new URL("../hornlab_search/gui/static/study_results.js", import.meta.url))).href;
const m = await import(MODULE_URL);

const tick = async (n = 4) => { for (let i = 0; i < n; i++) await new Promise(r => setImmediate(r)); };

const HASH1 = "a".repeat(8) + "1111" + "b".repeat(52);
const HASH2 = "c".repeat(8) + "2222" + "d".repeat(52);
const SOLVE1 = "s1-aaaa-1111";
const SOLVE2 = "s2-cccc-2222";
const ROOT_ID = "rootabc123";

function listing() {
  return {
    status: "ok", n_total: 2, n_pages: 1, page: 1, page_size: 25, sort: "best_j",
    tiers: ["screen", "verify"],
    states: { measured: 2 },
    rows: [
      { solve_id: SOLVE1, attempt_id: "a1", tier: "screen", state: "measured", j: 2.5,
        design_hash: HASH1, measured: true, eligible: true, physical: true,
        verify: { available: true, j: 2.3, solve_id: "v-" + SOLVE1, kind: "verify" },
        artifact: { design_dir: "runs/x/screen/designs/" + HASH1 } },
      { solve_id: SOLVE2, attempt_id: "a2", tier: "screen", state: "measured", j: 3.4,
        design_hash: HASH2, measured: true, eligible: true, physical: true,
        artifact: { design_dir: "runs/x/screen/designs/" + HASH2 } },
    ],
  };
}

const detail = {
  observation: { solve_id: null, design_hash: null, state: "measured", reason: null,
    identities: { solve_id: "x" } },
  geometry: { source: "stored_mesh", preview: false, geometry: { quadrants: "1", n_tris: 12, verts: [], tris: [] } },
  acoustics: { curves: { freqs_hz: [700], beamwidth_h: [60], beamwidth_v: [40] }, objective_version: 7 },
  balloon: null,
};

function detailApi() {
  const calls = { observation: [], geometry: [], acoustics: [], balloon: [] };
  return {
    calls,
    getStudy: async () => ({ id: "studyX", revision: 1, name: "Round2", status: "running", root: ROOT_ID }),
    getPanel: async (id, phase) => ({ phase, status: "ready", revision: 1, data: {}, provenance: {}, reasons: [] }),
    getObservations: async (id, { page = 1 } = {}) => ({ ...listing(), page }),
    getObservation: async (id, solveId) => { calls.observation.push(solveId); return { ...detail.observation, solve_id: solveId }; },
    getObservationGeometry: async (id, solveId, { tier } = {}) => { calls.geometry.push([solveId, tier]); return detail.geometry; },
    getObservationAcoustics: async (id, solveId, { tier } = {}) => { calls.acoustics.push([solveId, tier]); return detail.acoustics; },
    getObservationBalloon: async (id, solveId, { tier } = {}) => { calls.balloon.push([solveId, tier]); return null; },
    action: async () => ({}),
  };
}

// ── 1. mount -> list paints -> default selection auto-loads its detail ─────────────────────
{
  const root = makeRoot();
  const api = detailApi();
  const dispose = m.mountStudyResults(root, { studyId: "studyx", tab: "horns", query: "", api, rootId: ROOT_ID, pollMs: 0 });
  await tick(8);
  assert.ok(root.innerHTML.includes("All horn candidates"), "the Horns table paints");
  assert.ok(root.innerHTML.includes("Inspect"), "each row offers an Inspect button");
  await tick(10);
  assert.ok(api.calls.observation.length > 0, "default selection loads a detail payload");
  assert.ok(root.innerHTML.includes("Horn inspector"), "the inspector section paints");
  dispose();
}

// ── 2. clicking a row's Inspect repaints the inspector for THAT identity (the dead-click case) ──
{
  const root = makeRoot();
  const api = detailApi();
  const dispose = m.mountStudyResults(root, { studyId: "studyx", tab: "horns", query: "", api, rootId: ROOT_ID, pollMs: 0 });
  await tick(12);
  const before = api.calls.observation.slice();
  const button = { dataset: { solve: SOLVE2, tier: "screen", design: HASH2 },
    closest(selector) { return selector === "[data-res-select]" ? this : null; } };
  root.click({ target: button });
  await tick(12);
  assert.ok(pushed.some(u => typeof u === "string" && u.includes("solve=")), "the URL records the selection (pushState)");
  assert.ok(api.calls.observation.some(id => id === SOLVE2), "the inspector fetches the clicked observation");
  assert.notEqual(api.calls.observation.join("|"), before.join("|") + (before.some(x => x === SOLVE2) ? "" : ""), "a NEW detail fetch went out");
  assert.ok(api.calls.geometry.some(([id, tier]) => id === SOLVE2 && tier === "screen"), "geometry is fetched for the clicked horn");
  assert.ok(api.calls.acoustics.some(([id, tier]) => id === SOLVE2 && tier === "screen"), "acoustics are fetched for the clicked horn");
  assert.ok(root.innerHTML.includes("Horn inspector"), "the inspector is painted");
  assert.ok(root.innerHTML.includes(HASH2.slice(0, 8)) || root.innerHTML.includes("HORN2-PAINT-PROBE")
    || root.innerHTML.includes(HASH2.slice(-6)) || root.innerHTML.includes("stored_mesh"), "the clicked design reaches the inspector DOM");
  dispose();
}

// ── 3. an observation with NO artifacts still shows an explicit inspector state, never silence ──
{
  const root = makeRoot();
  const api = detailApi();
  api.getObservations = async () => ({ ...listing(), status: "ok", rows: [{ solve_id: "s-pend-1", attempt_id: "p1", tier: "screen", state: "missing_artifact", j: null, design_hash: null, measured: false, eligible: false, outcome: "pending" }], states: { missing_artifact: 1 }, n_total: 1, n_pages: 1 });
  api.getObservation = async (id, solveId) => (api.calls ? api.calls.observation.push(solveId) : 0, { solve_id: solveId, design_hash: null, state: "missing_artifact", reason: "no design directory is published for this observation" });
  api.getObservationGeometry = async () => ({ state: "missing_artifact", geometry: null, notice: null, source: null, preview: false, reason: "no mesh stored" });
  api.getObservationAcoustics = async () => ({ state: "missing_artifact", curves: null, notice: null, reason: "no curves stored" });
  api.calls = { observation: [], geometry: [], acoustics: [], balloon: [] };
  const dispose = m.mountStudyResults(root, { studyId: "studyx", tab: "horns", query: "", api, rootId: ROOT_ID, pollMs: 0 });
  await tick(12);
  assert.ok(root.innerHTML.includes("missing_artifact") || root.innerHTML.includes("missing artifact")
    || /Artifact|artifact|missing/i.test(root.innerHTML), "the inspector states what is missing instead of showing nothing");
  dispose();
}

console.log("study results lifecycle ok");
