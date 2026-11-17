// Results workspace (P1): the human review surface for a BoTorch study.
//
// Read-only by construction: every panel is filled by a GET.  The one expensive action
// ("Verify at higher fidelity") is a separate, confirmed GPU solve and never opens the 3D
// view.  The existing run viewers are reused: view3d.js for the mesh, balloon.js for the
// stored balloon, charts.js for every curve/map, and study_charts.js for the convergence
// panels (no new plotting or meshing code here).
//
// Selection is an identity, never a canvas position:
//   { solve_id, tier, design_hash }  ->  #/bayes/study/<id>/horns?root=…&solve=…&tier=…&design=…
// The URL is the durable store, so refresh / poll / phase switches keep the same horn.
import { chart, catColor, fmt, isobarMap, logTicks, niceTicks, polarMap } from "./charts.js";
import { init3d } from "./view3d.js";
import { initBalloon3d } from "./balloon.js";
import { addIdentityMarkers, designSpaceLimits, drawStudyCharts, paretoLimits } from "./study_charts.js";
import { RESULT_PHASES } from "./studies.js";

const ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/;
const HASH = /^[0-9a-f]{6,64}$/i;
const OBS_STATES = new Set(["measured", "geometry_only", "predicted_only", "missing_artifact", "unsupported_geometry", "stale", "verified"]);
const REFUSAL_OUTCOMES = new Set(["cheap_refusal", "refused", "rejected", "infeasible", "invalid", "failure", "physics_refusal", "gate_failed"]);
const PAGE_SIZE = 50;
const SCAN_PAGE_SIZE = 100;
const MAX_SCAN_PAGES = 40;        // bounded full-list scan for search/filter (4 000 rows)
const COMPARE_SCAN_PAGES = 20;    // bounded lookup of the opposite tier for one design
const DEFAULT_POLL_MS = 20000;
const RESULT_TABS = [
  { id: "results", label: "Overview" },
  { id: "horns", label: "Horns" },
  { id: "explore", label: "Explore" },
];

const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const label = value => String(value ?? "").replace(/_/g, " ");
const isId = value => typeof value === "string" && ID.test(value);
const isHash = value => typeof value === "string" && HASH.test(value);
const num = value => {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
};
const str = value => (typeof value === "string" && value.length ? value : null);
const fmtNum = (value, digits = 3) => {
  const n = num(value);
  return n == null ? "—" : n.toLocaleString("en-US", { maximumFractionDigits: digits });
};
const fmtDelta = value => {
  const n = num(value);
  if (n == null) return "—";
  return `${n > 0 ? "+" : ""}${n.toLocaleString("en-US", { maximumFractionDigits: 3 })}`;
};
const fmtDuration = seconds => {
  const value = num(seconds);
  if (value == null || value < 0) return "—";
  if (value < 90) return `${Math.round(value)} s`;
  const minutes = Math.round(value / 60);
  if (minutes < 120) return `${minutes} min`;
  return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
};
const shortId = value => {
  const s = str(value);
  return s ? (s.length > 18 ? `${s.slice(0, 10)}…${s.slice(-6)}` : s) : "—";
};
const finiteArray = value => Array.isArray(value) ? value.map(num) : [];
const pairSeries = (xs, ys) => {
  const x = Array.isArray(xs) ? xs : [];
  const y = Array.isArray(ys) ? ys : [];
  const out = [];
  for (let i = 0; i < Math.min(x.length, y.length); i += 1) {
    const px = num(x[i]), py = num(y[i]);
    if (px != null && py != null) out.push([px, py]);
  }
  return out;
};
const minFinite = values => {
  const nums = values.map(num).filter(v => v != null);
  return nums.length ? Math.min(...nums) : null;
};

/** Stable route for the Results workspace; selection travels as query params. */
export function resultRoute(studyId, tab = "results", { root = null, solve = null, tier = null, design = null } = {}) {
  if (!isId(studyId) || !RESULT_TABS.some(item => item.id === tab)) throw new Error("Invalid results route");
  const params = new URLSearchParams();
  if (root) params.set("root", root);
  if (solve) params.set("solve", solve);
  if (tier) params.set("tier", tier);
  if (design) params.set("design", design);
  const query = params.toString();
  return `#/bayes/study/${encodeURIComponent(studyId)}/${tab}${query ? `?${query}` : ""}`;
}

// ── payload normalisers ─────────────────────────────────────────────────────────────
// Lane A owns the exact detail payloads.  These readers accept the natural shapes Lane A's
// contract implies, unwrap a `{status, data}` envelope when present, and never invent a
// value.  A missing / 404 endpoint is absence, not an error page.

function envelope(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) return payload;
  for (const key of ["data", "detail", "observation", "row", "item"]) {
    const value = payload[key];
    if (value && typeof value === "object" && !Array.isArray(value)) return { ...payload, ...value };
  }
  return payload;
}

function payloadReason(payload) {
  if (!payload || typeof payload !== "object") return null;
  if (typeof payload.reason === "string" && payload.reason) return payload.reason;
  if (typeof payload.detail === "string" && payload.detail) return payload.detail;
  if (typeof payload.message === "string" && payload.message) return payload.message;
  for (const key of ["reasons", "notes"]) {
    const list = payload[key];
    if (Array.isArray(list)) {
      const first = list.find(item => typeof item === "string" && item.trim());
      if (first) return first;
    }
  }
  return null;
}

function rowsFrom(payload) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return [];
  for (const key of ["rows", "observations", "items", "results"]) {
    if (Array.isArray(payload[key])) return payload[key];
  }
  if (payload.data && typeof payload.data === "object" && !Array.isArray(payload.data)) {
    for (const key of ["rows", "observations", "items"]) {
      if (Array.isArray(payload.data[key])) return payload.data[key];
    }
  }
  return [];
}

function normalizeList(payload) {
  const rows = rowsFrom(payload).map(normalizeRow).filter(Boolean);
  const source = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
  const explicitTotal = num(source.total) ?? num(source.n_total) ?? num(source.count)
    ?? num(source.data?.total);
  return {
    rows,
    total: explicitTotal ?? rows.length,
    hasTotal: explicitTotal != null,
    page: num(source.page) ?? 1,
    pageSize: num(source.page_size) ?? num(source.pageSize) ?? rows.length,
    states: source.states && typeof source.states === "object" ? source.states : null,
    status: source.status || null,
    reason: payloadReason(source),
  };
}

function normalizeRow(raw, index) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const base = envelope(raw);
  const candidate = base.candidate && typeof base.candidate === "object" ? base.candidate : {};
  const result = base.result && typeof base.result === "object" ? base.result : {};
  const solveId = str(base.solve_id) || str(result.solve_id) || str(base.id);
  const designHash = str(base.design_hash) || str(base.designHash) || str(candidate.design_hash)
    || str(result.design_hash) || str(candidate.geometry_hash);
  const geometryHash = str(base.geometry_hash) || str(candidate.geometry_hash) || str(result.geometry_hash);
  const kind = str(base.tier) || str(base.kind) || str(result.kind) || str(candidate.kind);
  const tier = kind === "verify" || kind === "audit" ? "verify" : (kind === "screen" ? "screen" : (kind || null));
  const j = num(base.j) ?? num(base.observed_j) ?? num(base.score) ?? num(result.observed_j) ?? num(result.j);
  const predicted = base.predicted && typeof base.predicted === "object" ? base.predicted
    : (candidate.predicted && typeof candidate.predicted === "object" ? candidate.predicted : null);
  const outcome = str(base.outcome) || str(result.outcome);
  const stateRaw = str(base.state) || str(base.artifact_state) || str(base.evidence_state) || str(base.status);
  let state = OBS_STATES.has(stateRaw) ? stateRaw : null;
  const verifyRaw = base.verify && typeof base.verify === "object" ? base.verify : null;
  const verifyJ = num(verifyRaw?.j) ?? num(verifyRaw?.observed_j);
  const verifySolveId = str(verifyRaw?.solve_id);
  const hasVerify = verifyRaw?.available === true && verifyJ != null && isId(verifySolveId || "");
  const verified = base.verified === true || tier === "verify" || state === "verified";
  let measured = base.measured === true || base.physical === true || base.physical_measurement === true
    || result.physical_measurement === true || result.physical === true || state === "measured" || verified;
  if (state === "predicted_only" || state === "geometry_only" || state === "missing_artifact" || state === "unsupported_geometry") measured = false;
  if (!state) state = verified ? "measured" : (measured ? "measured" : (predicted ? "predicted_only" : null));
  const refused = REFUSAL_OUTCOMES.has(outcome) || state === "refused";
  const rejected = base.rejected === true || outcome === "rejected" || outcome === "refused";
  const params = base.params && typeof base.params === "object" ? base.params
    : (result.params && typeof result.params === "object" ? result.params
      : (candidate.params && typeof candidate.params === "object" ? candidate.params : null));
  const dimensions = base.dimensions && typeof base.dimensions === "object" ? base.dimensions
    : (base.dims && typeof base.dims === "object" ? base.dims
    : (base.descriptors && typeof base.descriptors === "object" ? base.descriptors
      : (candidate.descriptors && typeof candidate.descriptors === "object" ? candidate.descriptors
        : (result.descriptors && typeof result.descriptors === "object" ? result.descriptors : null))));
  const generator = candidate.generator && typeof candidate.generator === "object" ? candidate.generator : null;
  const typology = str(base.typology) || str(base.family) || str(base.family_name)
    || str(candidate.family) || str(params?.family) || str(generator?.family);
  const reasons = Array.isArray(base.reasons) ? base.reasons.filter(item => typeof item === "string") : [];
  const reason = str(base.reason) || str(base.status_reason) || str(base.selection_reason)
    || str(result.reason) || (reasons.length ? reasons[0] : null) || outcome;
  const verificationDelta = num(base.verification_delta) ?? num(base.verify_delta)
    ?? num(base.verify_minus_screen) ?? num(base.delta_j) ?? num(result.verification_delta);
  const attempt = num(base.attempt) ?? num(base.observation_seq) ?? num(base.seq) ?? index;
  const searchText = [
    solveId, designHash, geometryHash, tier, typology, reason, outcome, state,
    ...(dimensions ? Object.values(dimensions).slice(0, 12) : []),
    ...(params ? Object.values(params).slice(0, 12) : []),
  ].filter(value => value != null).join(" ").toLowerCase();
  return {
    solveId, designHash, geometryHash, tier, state, measured, verified, refused, rejected,
    hasVerify, verifyJ, verifySolveId,
    verifyKind: str(verifyRaw?.kind),
    artifact: base.artifact && typeof base.artifact === "object" ? base.artifact : null,
    acquisition: base.acquisition && typeof base.acquisition === "object" ? base.acquisition : null,
    selectionReason: str(base.selection_reason) || str(candidate.selection_reason),
    newIncumbent: base.new_incumbent === true || base.new_best === true || base.incumbent === true || base.is_incumbent === true,
    pareto: base.pareto === true || base.nondominated === true || base.is_pareto === true
      || base.pareto_front === true || base.front === true,
    j, predicted, outcome, params, dimensions, typology, reason, reasons,
    verificationDelta, attempt, searchText,
    predictedMean: predicted ? (num(predicted.j_mean) ?? num(predicted.mean) ?? num(predicted.value)) : null,
    predictedLower: predicted ? (num(predicted.j_lower) ?? num(predicted.lower) ?? num(predicted.lo)) : null,
    predictedUpper: predicted ? (num(predicted.j_upper) ?? num(predicted.upper) ?? num(predicted.hi)) : null,
    intervalLabel: predicted ? str(predicted.interval_label) : null,
    raw: base,
  };
}

function normalizeDetail(payload) {
  const base = envelope(payload);
  if (!base || typeof base !== "object" || Array.isArray(base)) return null;
  return {
    ...base,
    solveId: str(base.solve_id) || str(base.solveId) || str(base.id),
    designHash: str(base.design_hash) || str(base.designHash),
    state: str(base.state) || str(base.status),
    reasons: Array.isArray(base.reasons) ? base.reasons.filter(item => typeof item === "string") : [],
    objectiveVersion: num(base.objective_version) ?? num(base.objectiveVersion),
    brief: base.brief || base.brief_name || null,
    target: base.target || null,
  };
}

function normalizeAcoustics(payload) {
  if (!payload) return null;
  const candidates = [
    payload.acoustics, payload.curves, payload.design, payload.data,
    payload.observation?.acoustics, payload.geometry?.acoustics, payload,
  ];
  const source = candidates.find(item => item && typeof item === "object" && !Array.isArray(item)
    && (Array.isArray(item.freqs) || Array.isArray(item.freqs_hz))
    && (item.bw_h != null || item.bw_h_deg != null || item.di != null || item.di_db != null
      || Array.isArray(item.polar_h) || Array.isArray(item.spl_h_db)));
  if (!source) return null;
  const freqs = finiteArray(source.freqs ?? source.freqs_hz);
  const scoreWindow = (source.score_window && typeof source.score_window === "object" ? source.score_window : null)
    || (payload.score_window && typeof payload.score_window === "object" ? payload.score_window : null)
    || (source.scoring_view?.coverage && typeof source.scoring_view.coverage === "object" ? source.scoring_view.coverage : null);
  const scoring = (source.scoring_view && typeof source.scoring_view === "object" ? source.scoring_view : null)
    || (payload.scoring_view && typeof payload.scoring_view === "object" ? payload.scoring_view : null);
  const angles = finiteArray(source.angles ?? source.h_angles_deg);
  const polarH = Array.isArray(source.polar_h) ? source.polar_h
    : (Array.isArray(source.spl_h_db) ? source.spl_h_db : null);
  const polarV = Array.isArray(source.polar_v) ? source.polar_v
    : (Array.isArray(source.spl_v_db) ? source.spl_v_db : null);
  return {
    source,
    freqs,
    bwH: finiteArray(source.bw_h ?? source.bw_h_deg),
    bwV: finiteArray(source.bw_v ?? source.bw_v_deg),
    di: finiteArray(source.di ?? source.di_db),
    diSource: source.di_source ?? null,
    onAxis: finiteArray(source.on_axis ?? source.on_axis_db),
    ripH: finiteArray(source.rip_h ?? source.ripple_h_db),
    ripV: finiteArray(source.rip_v ?? source.ripple_v_db),
    zRe: finiteArray(source.z_re ?? source.z_throat_real),
    zIm: finiteArray(source.z_im ?? source.z_throat_imag),
    angles,
    polarH,
    polarV,
    profile: source.profile ?? payload.profile ?? null,
    params: source.params ?? payload.params ?? null,
    scoreWindow,
    scoring,
    objectiveVersion: num(source.objective_version) ?? num(scoring?.objective_version)
      ?? num(payload.objective_version),
    brief: source.brief ?? payload.brief ?? null,
    target: source.target ?? payload.target ?? null,
    gates: source.gates ?? payload.gates ?? null,
    row: source.row ?? payload.row ?? null,
  };
}

function normalizeGeometry(payload) {
  if (!payload) return null;
  const candidates = [payload.mesh, payload.geometry, payload.surface, payload.data, payload];
  const mesh = candidates.find(item => item && typeof item === "object" && !Array.isArray(item)
    && Array.isArray(item.verts) && Array.isArray(item.tris));
  if (!mesh) return null;
  return {
    mesh,
    profile: mesh.profile ?? payload.profile ?? payload.geometry?.profile ?? null,
    mounting: mesh.mounting ?? null,
    quadrants: mesh.quadrants ?? null,
    nTris: num(mesh.n_tris),
    state: str(payload.state),
    reason: str(payload.reason),
    source: str(payload.source),
    preview: payload.preview === true,
    notice: str(payload.notice),
  };
}

function normalizeBalloon(payload) {
  if (!payload) return null;
  const candidates = [payload.balloon, payload.data, payload.payload, payload];
  const value = candidates.find(item => item && typeof item === "object" && !Array.isArray(item)
    && (Array.isArray(item.spl) || Array.isArray(item.spl_db)) && Array.isArray(item.freqs_hz || item.freqs)
    && (Array.isArray(item.balloon_grid) || Array.isArray(item.grid)));
  if (!value) return null;
  const grid = value.balloon_grid || value.grid;
  return {
    ...value,
    freqs_hz: value.freqs_hz || value.freqs,
    spl: value.spl || value.spl_db,
    balloon_grid: grid,
  };
}

function errorReason(kind, response) {
  if (!response) return `The ${kind} artifact is unavailable.`;
  if (response.reason) return response.reason;
  if (response.missing) return `This server does not expose the ${kind} endpoint yet.`;
  if (response.status === 404) return `No ${kind} artifact is recorded for this observation (404).`;
  if (response.state === "unsupported_geometry") return "This geometry family is unsupported by the canonical preview API; no substitute mesh is drawn.";
  const detail = response.error?.message ? `: ${response.error.message}` : "";
  return `The ${kind} artifact could not be loaded${detail}.`;
}

/** Keep the envelope's typed state/reason on the transport result for empty payloads. */
function decorateResource(response) {
  if (!response || !response.ok) return response;
  const payload = envelope(response.payload);
  const source = payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
  return {
    ...response,
    state: str(source.state),
    reason: str(source.reason),
    notice: str(source.notice),
    preview: source.preview === true,
    source: str(source.source),
  };
}

// ── list shaping ───────────────────────────────────────────────────────────────────

function verifiedJ(rows) {
  return minFinite(rows.filter(row => row.verified && row.measured).map(row => row.j));
}
function screenJ(rows) {
  return minFinite(rows.filter(row => !row.verified && row.measured).map(row => row.j));
}
function deriveDelta(row, state) {
  if (row.verificationDelta != null) return { value: row.verificationDelta, derived: false };
  if (row.hasVerify && row.j != null && row.verifyJ != null) {
    return { value: row.verifyJ - row.j, derived: true };
  }
  if (!row.designHash) return { value: null, derived: false };
  const pool = [...(state?.crossRows || []), ...(state?.rows || [])];
  const same = pool.filter(item => item.designHash === row.designHash && item.measured);
  const screen = minFinite(same.filter(item => item.verifyJ == null).map(item => item.j));
  const verify = minFinite(same.map(item => item.verifyJ).filter(value => value != null));
  return screen != null && verify != null
    ? { value: verify - screen, derived: true }
    : { value: null, derived: false };
}

function groupRows(rows) {
  const groups = new Map();
  for (const row of rows) {
    const key = row.designHash || row.geometryHash || row.solveId || `row-${row.attempt}`;
    let group = groups.get(key);
    if (!group) {
      group = {
        key, designHash: row.designHash, geometryHash: row.geometryHash,
        typology: row.typology, attempts: [], screenJ: null, verifyJ: null,
        predicted: null, state: row.state, reason: row.reason, pareto: false,
        newIncumbent: false, rejected: false, measured: false, verified: false,
      };
      groups.set(key, group);
    }
    group.attempts.push(row);
    if (row.typology) group.typology = row.typology;
    if (row.j != null && row.measured) {
      if (row.verified) group.verifyJ = group.verifyJ == null ? row.j : Math.min(group.verifyJ, row.j);
      else group.screenJ = group.screenJ == null ? row.j : Math.min(group.screenJ, row.j);
    }
    if (row.verifyJ != null) {
      group.verifyJ = group.verifyJ == null ? row.verifyJ : Math.min(group.verifyJ, row.verifyJ);
    }
    if (row.predicted && !group.predicted) group.predicted = row;
    group.measured = group.measured || row.measured;
    group.verified = group.verified || row.hasVerify || row.verified;
    group.pareto = group.pareto || row.pareto;
    group.newIncumbent = group.newIncumbent || row.newIncumbent;
    group.rejected = group.rejected || row.rejected;
    if (!group.reason && row.reason) group.reason = row.reason;
  }
  for (const group of groups.values()) {
    group.attempts.sort((a, b) => (num(a.attempt) ?? 0) - (num(b.attempt) ?? 0));
    group.primary = group.attempts.find(row => row.measured && !row.verified && row.j != null)
      || group.attempts.find(row => row.j != null)
      || group.attempts[0];
    group.delta = group.screenJ != null && group.verifyJ != null ? group.verifyJ - group.screenJ : null;
  }
  return [...groups.values()];
}

function matchesFilter(row, filter) {
  if (!filter || filter === "all") return true;
  if (filter === "measured") return row.measured === true;
  if (filter === "verified") return row.hasVerify === true || row.verified === true;
  if (filter === "new_incumbent") return row.newIncumbent === true;
  if (filter === "rejected") return row.rejected === true || row.refused === true;
  if (filter === "pareto") return row.pareto === true;
  return true;
}

function sortRows(rows, sort) {
  const copy = [...rows];
  const value = row => {
    if (sort === "screen_j") return row.verified ? null : row.j;
    if (sort === "verified_j") return row.verifyJ ?? (row.verified ? row.j : null);
    if (sort === "attempt") return row.attempt;
    return row.j;
  };
  copy.sort((a, b) => {
    const av = value(a), bv = value(b);
    if (av == null && bv == null) return (num(a.attempt) ?? 0) - (num(b.attempt) ?? 0);
    if (av == null) return 1;
    if (bv == null) return -1;
    return av - bv;
  });
  return copy;
}

/** The reads endpoint accepts best_j / worst_j / attempt / seq.  Screen/verified sorts are
 * client-side refinements over the best_j order, so they must not send an unknown sort. */
function backendSort(sort) {
  return sort === "attempt" ? "attempt" : "best_j";
}

function searchMatch(row, query) {
  const needle = String(query || "").trim().toLowerCase();
  return !needle || row.searchText.includes(needle);
}

function visibleRows(state) {
  let rows = [...state.rows];
  rows = rows.filter(row => matchesFilter(row, state.filter) && searchMatch(row, state.search));
  return sortRows(rows, state.sort);
}

function pageSlice(state) {
  const rows = visibleRows(state);
  const size = PAGE_SIZE;
  if (state.scanned) {
    const pages = Math.max(1, Math.ceil(rows.length / size));
    const page = Math.min(Math.max(1, state.localPage), pages);
    return { rows: rows.slice((page - 1) * size, page * size), page, pages, total: rows.length, scanned: true };
  }
  const pages = Math.max(1, Math.ceil((num(state.total) ?? state.rows.length) / size));
  return { rows, page: Math.min(Math.max(1, state.page), pages), pages, total: state.total, scanned: false };
}

// ── rendering: shell and tabs ──────────────────────────────────────────────────────

function tabUrl(state, tabId) {
  const selection = state.selection || {};
  return resultRoute(state.studyId, tabId, {
    root: state.rootRef,
    solve: selection.solveId || null,
    tier: selection.tier || null,
    design: selection.designHash || null,
  });
}

function oldPhaseLinks(state) {
  const study = state.study || {};
  const root = state.rootRef;
  const link = phase => `#/bayes/study/${encodeURIComponent(state.studyId)}/${phase}${root ? `?root=${encodeURIComponent(root)}` : ""}`;
  return ["live", "overview", "data", "explain", "propose", "execute", "decide"]
    .filter(phase => phase !== "live" || state.studyHasPackage)
    .map(phase => `<a href="${esc(link(phase))}">${esc(label(phase === "execute" ? "Run & Verify" : phase))}</a>`)
    .join(" · ");
}

function renderShell(state) {
  const study = state.study || {};
  const title = study.name || study.question || study.spec?.question || "Study results";
  const policy = study.spec?.policy?.proposal_policy || study.spec?.policy?.mode;
  const tabs = RESULT_TABS.map(item => `<a role="tab" aria-selected="${item.id === state.tab ? "true" : "false"}"${item.id === state.tab ? ' aria-current="page"' : ""} href="${esc(tabUrl(state, item.id))}">${esc(item.label)}</a>`).join("");
  const body = state.tab === "horns" ? renderHorns(state)
    : state.tab === "explore" ? renderExplore(state)
      : renderOverview(state);
  return `<section class="study-workspace res-workspace" aria-label="Study results workspace">
  <header>
    <p><a href="#/bayes/studies">Bayes</a> / Studies / <span class="muted">Results</span></p>
    ${identityStrip(state)}
    <h1>${esc(title)}</h1>
    <p class="muted res-meta">${esc(study.status || "unknown")}${policy ? ` · ${esc(label(policy))}` : ""} · revision ${esc(study.revision ?? "—")}${state.rootRef ? ` · <span class="mono">${esc(study.root_label || state.rootRef)}</span>` : ""}</p>
    <nav class="res-subtabs" role="tablist" aria-label="Results views">${tabs}</nav>
    <nav class="res-oldnav muted" aria-label="Authoring phases">${renderOldNavLabel(state)} ${oldPhaseLinks(state)}</nav>
  </header>
  ${state.notice ? `<p role="status" class="alert info">${esc(state.notice)}</p>` : ""}
  ${state.error ? `<p role="alert" class="alert error">${esc(state.error)}</p>` : ""}
  ${body}
</section>`;
}

function renderOldNavLabel() {
  return `<span>Authoring:</span>`;
}

function loadingBlock(message = "Loading…") {
  return `<p class="muted" role="status">${esc(message)}</p>`;
}

function emptyBlock(title, reason = "", detail = "") {
  return `<div class="res-empty" role="status"><strong>${esc(title)}</strong>${reason ? `<p>${esc(reason)}</p>` : ""}${detail ? `<p class="muted">${esc(detail)}</p>` : ""}</div>`;
}

function kpi(name, value, detail = "") {
  return `<div class="bo-kpi" role="listitem"><span class="bo-kpi-label">${esc(name)}</span><strong class="bo-kpi-value mono">${esc(value)}</strong>${detail ? `<span class="muted bo-kpi-detail">${esc(detail)}</span>` : ""}</div>`;
}

// ── CMA-run-style header data: target/floor/band from the recorded payload, never a guess ─────
function headerTargetFields(state) {
  const ti = state.dataPanel?.data?.bo?.target_integrity;
  const raw = ti?.scoring_target_available === true && ti.target && typeof ti.target === "object" ? ti.target : null;
  const detailTarget = state.detail?.acoustics?.target && typeof state.detail.acoustics.target === "object"
    ? { coverage_h_deg: state.detail.acoustics.target.hDeg, coverage_v_deg: state.detail.acoustics.target.vDeg,
        band_lo_hz: state.detail.acoustics.target.bandLo, band_hi_hz: state.detail.acoustics.target.bandHi,
        f0_hz: state.detail.acoustics.target.f0Hz }
    : null;
  const t = raw || detailTarget;
  return {
    t,
    unavailable: !t && ti && ti.scoring_target_available === false,
    h: t ? num(t.coverage_h_deg) : null,
    v: t ? num(t.coverage_v_deg) : null,
    lo: t ? num(t.band_lo_hz) : null,
    hi: t ? num(t.band_hi_hz) : null,
    f0: t ? num(t.f0_hz) ?? num(t.f0_v_hz) : null,
  };
}

function hornSizeText(dims) {
  if (!dims || typeof dims !== "object") return null;
  const w = num(dims.mouth_w_mm), h = num(dims.mouth_h_mm), d = num(dims.depth_mm);
  if (w == null && h == null && d == null) return null;
  return [w, h, d].map(v => v == null ? "—" : fmtNum(v, 0)).join(" × ");
}

function identityStrip(state) {
  const study = state.study || {};
  const policy = study.spec?.policy?.proposal_policy || study.spec?.policy?.mode;
  const task = study.spec?.task?.name || (typeof study.spec?.task === "string" ? study.spec.task : null)
    || state.dataPanel?.data?.bo?.data_summary?.task?.name || null;
  const brief = study.spec?.brief?.name || (typeof study.spec?.brief === "string" ? study.spec.brief : null)
    || state.dataPanel?.data?.bo?.target_integrity?.target_identity?.brief_name || null;
  const bits = ["STUDY RESULTS",
    policy ? `POLICY ${label(policy).toUpperCase()}` : null,
    task ? `TASK ${String(task).toUpperCase()}` : null,
    brief ? `BRIEF ${String(brief).toUpperCase()}` : null,
    `REVISION ${String(study.revision ?? "—").toUpperCase()}`,
    state.rootRef ? `ROOT ${String(study.root_label || state.rootRef)}` : null,
  ].filter(Boolean);
  return `<p class="res-identity mono" aria-label="Study identity">${bits.map(esc).join(" · ")}</p>`;
}

// ── Overview ───────────────────────────────────────────────────────────────────────

function renderOverview(state) {
  if (state.loadingOverview && !state.overview) return loadingBlock("Loading the study results…");
  if (!state.overview) {
    return `${emptyBlock("Results are not published yet",
      state.overviewError ? state.overviewError.message || String(state.overviewError) : "The execute panel returned no data.",
      "A results artifact is created after the study has measured screen solves. Existing authoring tabs remain below.")}`;
  }
  const data = state.overview.data && typeof state.overview.data === "object" ? state.overview.data : {};
  const bo = data.bo && typeof data.bo === "object" ? data.bo : {};
  const conv = bo.convergence && typeof bo.convergence === "object" ? bo.convergence : null;
  const run = bo.run && typeof bo.run === "object" ? bo.run : {};
  const budget = (run.budget && typeof run.budget === "object" ? run.budget : null)
    || (conv?.budget && typeof conv.budget === "object" ? conv.budget : null)
    || (data.budget && typeof data.budget === "object" ? data.budget : null) || {};
  const progress = (data.progress && typeof data.progress === "object" ? data.progress : null)
    || (conv?.progress && typeof conv.progress === "object" ? conv.progress : null) || {};
  const counts = data.call_counts && typeof data.call_counts === "object" ? data.call_counts : {};
  const arms = Array.isArray(conv?.arms) ? conv.arms : [];
  const bestVerify = minFinite(arms.map(arm => arm?.best_verify_j));
  const bestScreen = minFinite(arms.map(arm => arm?.best_j));
  const eta = conv?.eta && typeof conv.eta === "object" ? conv.eta : null;
  const etaTotal = eta ? [num(eta.screen_seconds), num(eta.verify_seconds)] : [null, null];
  const etaText = etaTotal.every(value => value != null) ? fmtDuration(etaTotal[0] + etaTotal[1]) : "—";
  const usedScreens = num(counts.screen_calls) ?? num(progress.screens) ?? null;
  const usedVerify = num(counts.verify_calls) ?? num(progress.verify) ?? null;
  const totalScreens = num(budget.screen_calls);
  const totalVerify = num(budget.verify_calls);
  const measured = num(progress.solved) ?? num(progress.measured) ?? null;
  const verified = num(progress.verified) ?? null;
  const refused = num(progress.refused) ?? num(progress.cheap_refusals) ?? null;
  const attempts = num(progress.attempts) ?? num(progress.proposed) ?? null;
  const ds = state.dataPanel?.data?.bo?.data_summary;
  const targetIntegrity = state.dataPanel?.data?.bo?.target_integrity;
  const targetIdentity = targetIntegrity?.target_identity && typeof targetIntegrity.target_identity === "object"
    ? targetIntegrity.target_identity : {};
  const objectiveVersion = num(ds?.objective_version) ?? num(conv?.objective_version)
    ?? num(targetIdentity.objective_version);
  const spec = state.study?.spec && typeof state.study.spec === "object" ? state.study.spec : {};
  const task = spec.task?.name || spec.task || state.study?.task || ds?.task?.name || null;
  const brief = spec.brief?.name || spec.brief || spec.target?.name
    || targetIdentity.brief_name || null;
  const target = (spec.target && typeof spec.target === "object" ? spec.target : null)
    || (targetIntegrity?.scoring_target_available === true && targetIntegrity.target
      && typeof targetIntegrity.target === "object" ? targetIntegrity.target : null);
  const targetText = target
    ? [num(target.coverage_h_deg) != null ? `H ${fmtNum(target.coverage_h_deg, 0)}°` : null,
      num(target.coverage_v_deg) != null ? `V ${fmtNum(target.coverage_v_deg, 0)}°` : null,
      num(target.band_lo_hz) != null || num(target.band_hi_hz) != null
        ? `${fmtNum(target.band_lo_hz, 0)}–${fmtNum(target.band_hi_hz, 0)} Hz` : null].filter(Boolean).join(" · ")
    : (targetIntegrity && targetIntegrity.scoring_target_available === false ? "scoring target unavailable" : null);
  const hasConvergence = conv && conv.status !== "not_applicable" && arms.some(arm => Array.isArray(arm?.points) && arm.points.length);
  const ht = headerTargetFields(state);
  const kpis = [
    kpi("Coverage target", ht.t ? [ht.h != null ? `H ${fmtNum(ht.h, 0)}°` : null, ht.v != null ? `V ${fmtNum(ht.v, 0)}°` : null].filter(Boolean).join(" · ") || "—"
      : (ht.unavailable ? "scoring target unavailable" : "—"),
      ht.t ? "the resolved target the scorer actually used" : "not a typology guess"),
    kpi("Scoring floor", ht.f0 != null ? `F ≥ ${fmtNum(ht.f0, 0)} Hz` : "—",
      ht.f0 == null && ht.t ? "no f0 recorded in the resolved target" : "scores below f0 are masked"),
    kpi("Band", ht.lo != null || ht.hi != null ? `${ht.lo != null ? fmtNum(ht.lo, 0) : "?"}–${ht.hi != null ? fmtNum(ht.hi, 0) : "?"} Hz` : "—",
      "scored band of the brief"),
    kpi("Best VERIFIED J", bestVerify == null ? "not yet verified" : fmtNum(bestVerify),
      bestVerify == null ? "No verify-tier measurement is recorded." : "verify tier — the comparison endpoint"),
    kpi("Best SCREEN J", bestScreen == null ? "not yet measured" : fmtNum(bestScreen),
      bestScreen == null ? "No screen-tier measurement is recorded." : "screen tier — never labelled verified"),
    kpi("Screens used / total", `${usedScreens == null ? "—" : fmtNum(usedScreens, 0)} / ${totalScreens == null ? "—" : fmtNum(totalScreens, 0)}`,
      num(budget.attempts) != null ? `${fmtNum(budget.attempts, 0)} attempts budgeted` : ""),
    kpi("Verify used / total", `${usedVerify == null ? "—" : fmtNum(usedVerify, 0)} / ${totalVerify == null ? "—" : fmtNum(totalVerify, 0)}`,
      "verify is substantially more expensive than a screen"),
    kpi("Measured / attempts", `${measured == null ? "—" : fmtNum(measured, 0)} / ${attempts == null ? "—" : fmtNum(attempts, 0)}`,
      refused == null ? "" : `${fmtNum(refused, 0)} cheap refusals`),
    kpi("Verified solves", verified == null ? "not recorded" : fmtNum(verified, 0)),
    kpi("ETA", etaText, eta ? `screen ${fmtDuration(eta.screen_seconds)} · verify ${fmtDuration(eta.verify_seconds)}` : "No solve timings recorded yet."),
  ].join("");
  const chart = hasConvergence
    ? `<div class="study-chart"><svg data-study-chart="convergence" role="img" aria-label="Best recorded J by solve index"></svg><div class="study-chart-legend"></div></div>
       <p class="muted">Best-so-far line from recorded rows. Screen J is reported but does not decide; verify J is the comparison endpoint.</p>`
    : emptyBlock("Convergence is not recorded", conv?.reason || "The execute panel has no measured series yet.");
  const contextRows = [
    ["Task", task ? `<span class="mono">${esc(task)}</span>` : "not recorded"],
    ["Objective version", objectiveVersion != null ? `v${esc(objectiveVersion)}` : "not recorded"],
    ["Brief / actual target", brief ? esc(label(brief)) : (targetText || "not recorded in the study spec")],
    ["Typology", ds?.typology || spec.typology || spec.task?.typology || "not recorded"],
    ["Policy", policyText(state.study) || "not recorded"],
    ["Solver / lane", run.lane || state.overview.data?.lane || "not recorded"],
    ["Study state", state.study?.status || "unknown"],
    ["Root", state.rootRef ? `<span class="mono">${esc(state.study?.root_label || state.rootRef)}</span>` : "not resolved"],
  ].map(([key, value]) => `<dt>${esc(key)}</dt><dd>${value}</dd>`).join("");
  const comparison = `<p>Screen and verify are separate physical tiers. This page never promotes a screen J to "verified":
    <span class="pill">screen ${bestScreen == null ? "not measured" : fmtNum(bestScreen)}</span>
    <span class="pill ${bestVerify == null ? "" : "good"}">verified ${bestVerify == null ? "not yet verified" : fmtNum(bestVerify)}</span></p>`;
  return `<div class="bo-kpis" role="list" aria-label="Results KPIs">${kpis}</div>
  <section class="bo-panel"><div class="bo-head"><h3>Convergence</h3><span class="pill">${hasConvergence ? "recorded" : "not recorded"}</span></div>${chart}</section>
  <section class="bo-panel"><div class="bo-head"><h3>Study context</h3></div><dl class="res-dl">${contextRows}</dl>${comparison}</section>
  <p class="res-cta"><a class="btn" href="${esc(tabUrl(state, "horns"))}">Browse every horn candidate →</a> <a class="btn" href="${esc(tabUrl(state, "explore"))}">Explore the design space →</a></p>`;
}

function policyText(study) {
  const policy = study?.spec?.policy;
  if (!policy) return null;
  return policy.proposal_policy || policy.mode || null;
}

// ── Horns: list, controls, table ────────────────────────────────────────────────────

function renderHorns(state) {
  return `<div class="bo-kpis res-kpi-strip" role="list" aria-label="Horn candidates KPIs">${hornsKpiStrip(state)}</div>${hornsBody(state)}`;
}

function hornsKpiStrip(state) {
  const ht = headerTargetFields(state);
  const scoped = state.crossScanDone && Array.isArray(state.crossRows) && state.crossRows.length ? state.crossRows : (state.rows || []);
  const bestScreen = minFinite(scoped.map(row => row.j).filter(value => value != null));
  const bestVerified = minFinite(scoped.map(row => row.hasVerify ? row.verifyJ : null).filter(value => value != null));
  const sel = state.selection || {};
  const selRow = state.rows.find(row => row.solveId === sel.solveId && row.tier === sel.tier)
    || (state.crossRows || []).find(row => row.solveId === sel.solveId && row.tier === sel.tier) || null;
  const selSize = hornSizeText(selRow?.dimensions) || hornSizeText(state.currentRow?.dimensions);
  const measured = num(state.states?.measured);
  const verifiedCount = scoped.filter(row => row.hasVerify || row.verified).length;
  const scope = state.crossScanDone ? "full scan" : `first ${fmtNum(state.rows.length, 0)} of ${fmtNum(state.total, 0)} loaded`;
  const extraStates = state.states && typeof state.states === "object"
    ? Object.entries(state.states).filter(([key, value]) => num(value) > 0 && key !== "measured")
      .map(([key, value]) => `${label(key)} ${fmtNum(value, 0)}`).join(" · ") : "";
  return [
    kpi("Coverage target", ht.t ? [ht.h != null ? `H ${fmtNum(ht.h, 0)}°` : null, ht.v != null ? `V ${fmtNum(ht.v, 0)}°` : null].filter(Boolean).join(" · ") || "—"
      : (ht.unavailable ? "scoring target unavailable" : "—"),
      ht.t ? "the resolved target the scorer actually used" : "not a typology guess"),
    kpi("Scoring floor", ht.f0 != null ? `F ≥ ${fmtNum(ht.f0, 0)} Hz` : "—", "scores below f0 are masked"),
    kpi("Band", ht.lo != null || ht.hi != null ? `${ht.lo != null ? fmtNum(ht.lo, 0) : "?"}–${ht.hi != null ? fmtNum(ht.hi, 0) : "?"} Hz` : "—", "scored band of the brief"),
    kpi("Best SCREEN J", bestScreen == null ? "—" : fmtNum(bestScreen), `${scope}, screen tier`),
    kpi("Best VERIFIED J", bestVerified == null ? "not yet verified" : fmtNum(bestVerified), "verify tier — comparison endpoint"),
    kpi("Selected horn", selSize || "—", sel.solveId ? `solve ${String(sel.solveId).slice(0, 10)}… · ${sel.tier || "screen"}` : "click Inspect on a row"),
    kpi("Observations", `${measured != null ? fmtNum(measured, 0) : "—"} measured${verifiedCount ? ` · ${fmtNum(verifiedCount, 0)} verified` : ""}`,
      extraStates),
  ].join("");
}

function hornsBody(state) {
  const stateCounts = state.states && typeof state.states === "object"
    ? Object.entries(state.states).filter(([, value]) => num(value) > 0)
      .map(([key, value]) => `<span class="pill ${key === "measured" ? "good" : key === "missing_artifact" || key === "stale" ? "warn" : ""}">${esc(label(key))} ${fmtNum(value, 0)}</span>`).join(" ")
    : "";
  const counts = `<span class="pill">${fmtNum(state.total, 0)} observations</span>${stateCounts}${state.scanned ? ` <span class="pill">${fmtNum(state.rows.length, 0)} loaded</span>` : ""}${state.scanTruncated ? ` <span class="pill warn">scan truncated</span>` : ""}`;
  const controls = `<form class="res-controls" data-res-controls>
    <label class="res-search">Search / ID <input type="search" data-res-search value="${esc(state.search)}" placeholder="design hash, solve id, typology…" autocomplete="off"></label>
    <label>Sort <select data-res-sort>${[
      ["best_j", "Best J"], ["screen_j", "Screen J"], ["verified_j", "Verified J"], ["attempt", "Attempt order"],
    ].map(([value, text]) => `<option value="${value}"${state.sort === value ? " selected" : ""}>${esc(text)}</option>`).join("")}</select></label>
    <div class="res-filters" role="group" aria-label="Candidate filters">${[
      ["all", "All"], ["measured", "Measured"], ["verified", "Verified"],
      ["new_incumbent", "New incumbent"], ["rejected", "Rejected / refused"], ["pareto", "Pareto"],
    ].map(([value, text]) => `<button type="button" data-res-filter="${value}" aria-pressed="${state.filter === value ? "true" : "false"}">${esc(text)}</button>`).join("")}</div>
    <label class="res-toggle"><input type="checkbox" data-res-group${state.group ? " checked" : ""}> Group repeated designs</label>
    <button type="button" data-res-scan${state.scanned || state.scanning ? " disabled" : ""}>${state.scanning ? "Scanning…" : "Search all candidates"}</button>
  </form>
  <p class="muted res-list-note">${listNote(state)}</p>`;
  const list = state.listError && !state.rows.length
    ? emptyBlock("No observation artifacts are published yet", state.listError, "This study may still be running, or its results artifact has no readable observations. The authoring tabs remain available below.")
    : `<div data-res-list>${renderListBody(state)}</div><div data-res-pager>${renderPager(state)}</div>`;
  return `<div class="res-horns">
    <section class="bo-panel res-list-panel"><div class="bo-head"><h3>All horn candidates</h3><span class="pill-row">${counts}</span></div>${controls}${state.loadingList && !state.rows.length ? loadingBlock("Loading observations…") : list}</section>
    ${renderInspector(state)}
  </div>`;
}

function listNote(state) {
  if (state.scanning) return "Scanning every published observation for search and filters. The table below still shows the current page.";
  if (state.scanned) {
    return `Searching ${fmtNum(state.rows.length, 0)} loaded observations${state.total > state.rows.length ? ` of ${fmtNum(state.total, 0)}` : ""}${state.scanTruncated ? " (scan cap reached)" : ""}.`;
  }
  if (state.search.trim() || state.filter !== "all") {
    return "Filtering the current page until the full scan completes; use “Search all candidates” to scan every observation now.";
  }
  return "Paginated from the observations endpoint. Grouped rows keep every attempt in an expandable list.";
}

function renderListBody(state) {
  if (state.loadingList && !state.rows.length) return loadingBlock("Loading observations…");
  const page = pageSlice(state);
  if (!page.rows.length) {
    const reason = state.listReason || (state.rows.length ? "No candidates match the current search / filter." : "No observations are listed yet.");
    return emptyBlock(state.rows.length ? "No matching candidates" : "No observations published yet", reason,
      state.rows.length ? "Clear the search or choose another filter." : "");
  }
  return state.group ? renderGroupedTable(state, page.rows) : renderFlatTable(state, page.rows);
}

function statusBadges(row) {
  const physical = row.refused ? "refused" : row.verified ? "verified" : row.measured ? "measured" : "not measured";
  const cls = row.refused ? "bad" : row.verified ? "good" : row.measured ? "" : "warn";
  const badges = [`<span class="pill ${cls}">${physical}</span>`];
  if (row.hasVerify && !row.verified) {
    badges.push(`<span class="pill good" title="a verify-tier measurement is recorded for this design">verified ${fmtNum(row.verifyJ)}</span>`);
  }
  if (row.tier && row.tier !== "screen") badges.push(`<span class="pill">${esc(label(row.tier))}</span>`);
  if (row.state && row.state !== "measured" && row.state !== "verified") {
    badges.push(`<span class="pill warn" title="observation artifact state">${esc(label(row.state))}</span>`);
  }
  if (row.newIncumbent) badges.push('<span class="pill good">new incumbent</span>');
  if (row.pareto) badges.push('<span class="pill">Pareto</span>');
  if (row.rejected) badges.push('<span class="pill bad">rejected</span>');
  return badges.join(" ");
}

function scoreCell(row) {
  if (row.measured && row.j != null) {
    const verify = row.hasVerify ? `<br><span class="pill good">verified ${fmtNum(row.verifyJ)}</span>` : "";
    return `<span class="mono">${fmtNum(row.j)}</span><br><span class="muted">screen / attempt</span>${verify}`;
  }
  if (row.predictedMean != null) {
    const span = row.predictedLower != null && row.predictedUpper != null
      ? ` [${fmtNum(row.predictedLower)}, ${fmtNum(row.predictedUpper)}]` : "";
    return `<span class="mono">${fmtNum(row.predictedMean)}${span}</span><br><span class="pill warn" title="model credible interval — never a measured curve">model interval, not measured</span>`;
  }
  return "—";
}

function acquisitionText(row) {
  const raw = row?.raw?.acquisition;
  if (raw == null) return null;
  const value = num(typeof raw === "object" ? (raw.value ?? raw.acq_value ?? raw.score) : raw);
  return value == null ? null : `acq ${fmtNum(value, 3)}`;
}

function dimensionsText(row) {
  if (!row.dimensions || typeof row.dimensions !== "object") return "—";
  const entries = Object.entries(row.dimensions)
    .filter(([, value]) => (num(value) != null) || (typeof value === "string" && value.length))
    .slice(0, 4);
  return entries.length ? entries.map(([key, value]) => `${esc(label(key))} ${esc(value)}`).join(" · ") : "—";
}

function openButton(row, text = "Inspect") {
  if (!row) return "";
  return `<button type="button" data-res-select data-solve="${esc(row.solveId || "")}" data-tier="${esc(row.tier || "")}" data-design="${esc(row.designHash || "")}"${row.solveId || row.designHash ? "" : " disabled"}>${esc(text)}</button>`;
}

function renderFlatTable(state, rows) {
  const body = rows.map(row => {
    const delta = deriveDelta(row, state);
    return `<tr data-res-row data-solve="${esc(row.solveId || "")}" data-tier="${esc(row.tier || "")}" data-design="${esc(row.designHash || "")}">
      <td><span class="mono">${esc(shortId(row.designHash))}</span>${row.typology ? `<br><span class="muted">${esc(row.typology)}</span>` : ""}</td>
      <td><span class="mono">${esc(shortId(row.solveId))}</span><br><span class="muted">attempt ${esc(fmtNum(row.attempt, 0))}${row.tier ? ` · ${esc(label(row.tier))}` : ""}</span></td>
      <td>${scoreCell(row)}</td>
      <td class="r mono"${delta.derived ? ' title="derived from the best screen and verified rows for this design"' : ""}>${fmtDelta(delta.value)}</td>
      <td>${dimensionsText(row)}</td>
      <td>${statusBadges(row)}${row.reason ? `<br><span class="muted">${esc(row.reason)}</span>` : ""}${acquisitionText(row) ? `<br><span class="muted mono" title="ranking diagnostic, not a probability or a measured quality">${esc(acquisitionText(row))}</span>` : ""}</td>
      <td>${openButton(row)}</td>
    </tr>`;
  }).join("");
  return `<div class="tbl-scroll"><table class="res-table"><thead><tr><th>Design</th><th>Attempt / solve</th><th>J</th><th class="r">Verify − screen</th><th>Dimensions</th><th>Status / reason</th><th></th></tr></thead><tbody>${body}</tbody></table></div><p class="bo-scroll-hint">Scroll horizontally for all columns →</p>`;
}

function renderAttemptTable(group) {
  const rows = group.attempts.map(row => `<tr><td>${openButton(row, "Open")}</td><td class="mono">${esc(shortId(row.solveId))}</td><td>${esc(label(row.tier || "—"))}</td><td class="r mono">${fmtNum(row.j)}</td><td>${statusBadges(row)}</td><td>${esc(row.reason || "—")}</td></tr>`).join("");
  return `<table class="res-attempt-table"><thead><tr><th></th><th>Solve</th><th>Tier</th><th class="r">J</th><th>Status</th><th>Reason</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderGroupedTable(state, rows) {
  const groups = groupRows(rows);
  const body = groups.map(group => {
    const primary = group.primary || {};
    const n = group.attempts.length;
    const score = group.screenJ != null
      ? `<span class="mono">${fmtNum(group.screenJ)}</span> <span class="muted">screen</span>${group.verifyJ != null ? `<br><span class="pill good">verified ${fmtNum(group.verifyJ)}</span>` : ""}`
      : group.verifyJ != null
        ? `<span class="mono">${fmtNum(group.verifyJ)}</span> <span class="pill good">verified</span>`
        : scoreCell(primary);
    return `<tr class="res-group-row" data-res-row data-solve="${esc(primary.solveId || "")}" data-tier="${esc(primary.tier || "")}" data-design="${esc(primary.designHash || "")}">
      <td><span class="mono">${esc(shortId(group.designHash))}</span>${group.typology ? `<br><span class="muted">${esc(group.typology)}</span>` : ""}</td>
      <td><span class="pill">${n} attempt${n === 1 ? "" : "s"}</span>${group.screenJ != null ? `<br><span class="muted">screen ${fmtNum(group.screenJ)}</span>` : ""}${group.verifyJ != null ? `<br><span class="muted">verified ${fmtNum(group.verifyJ)}</span>` : ""}</td>
      <td>${score}</td>
      <td class="r mono">${fmtDelta(group.delta)}</td>
      <td>${dimensionsText(primary)}</td>
      <td>${statusBadges(primary)}${group.reason ? `<br><span class="muted">${esc(group.reason)}</span>` : ""}${acquisitionText(primary) ? `<br><span class="muted mono" title="ranking diagnostic, not a probability or a measured quality">${esc(acquisitionText(primary))}</span>` : ""}</td>
      <td>${openButton(primary)}</td>
    </tr>
    <tr class="res-group-detail"><td colspan="7"><details><summary>Attempt-level evidence (${n})</summary>${renderAttemptTable(group)}</details></td></tr>`;
  }).join("");
  return `<div class="tbl-scroll"><table class="res-table"><thead><tr><th>Design</th><th>Attempts</th><th>Best J</th><th class="r">Verify − screen</th><th>Dimensions</th><th>Status / reason</th><th></th></tr></thead><tbody>${body}</tbody></table></div><p class="bo-scroll-hint">Scroll horizontally for all columns →</p>`;
}

function renderPager(state) {
  const page = pageSlice(state);
  const disabledPrev = page.page <= 1;
  const disabledNext = page.page >= page.pages;
  const range = page.rows.length
    ? `${fmtNum((page.page - 1) * PAGE_SIZE + 1, 0)}–${fmtNum((page.page - 1) * PAGE_SIZE + page.rows.length, 0)}`
    : "0";
  return `<div class="res-pager">
    <button type="button" data-res-page="prev"${disabledPrev ? " disabled" : ""}>← Previous</button>
    <span class="muted">Page ${fmtNum(page.page, 0)} of ${fmtNum(page.pages, 0)} · ${range} of ${fmtNum(page.total ?? 0, 0)}</span>
    <button type="button" data-res-page="next"${disabledNext ? " disabled" : ""}>Next →</button>
    ${state.scanned ? '<span class="pill">full scan</span>' : ""}
  </div>`;
}

// ── Horn inspector ─────────────────────────────────────────────────────────────────

function scoringTarget(state) {
  const detail = state.detail || {};
  const ac = detail.acoustics || {};
  const sw = ac.scoreWindow && typeof ac.scoreWindow === "object" ? ac.scoreWindow : {};
  const target = ac.target && typeof ac.target === "object" ? ac.target : (detail.observation?.target || {});
  const version = num(ac.objectiveVersion) ?? num(detail.observation?.objectiveVersion)
    ?? num(state.dataPanel?.data?.bo?.data_summary?.objective_version);
  const hDeg = num(sw.h_deg) ?? num(target.coverage_h_deg);
  const vDeg = num(sw.v_deg) ?? num(target.coverage_v_deg);
  const bandLo = num(sw.band_lo_hz) ?? num(target.band_lo_hz) ?? (ac.freqs?.length ? ac.freqs[0] : null);
  const bandHi = num(sw.band_hi_hz) ?? num(target.band_hi_hz) ?? (ac.freqs?.length ? ac.freqs[ac.freqs.length - 1] : null);
  const loH = num(sw.h_lo_hz) ?? num(target.f0_hz) ?? bandLo;
  const loV = num(sw.v_lo_hz) ?? num(target.f0_v_hz) ?? loH;
  const f0 = num(target.f0_hz) ?? loH;
  const di = ac.scoring?.di && typeof ac.scoring.di === "object" ? ac.scoring.di : null;
  const diTarget = di && di.level_scored === true ? num(di.level_db) : null;
  const floor = ac.scoring?.bw8k_floor && typeof ac.scoring.bw8k_floor === "object" ? ac.scoring.bw8k_floor : null;
  const floorHz = floor ? num(floor.floor_hz) : null;
  const floorHDeg = floor ? num(floor.floor_h_deg) : null;
  const floorVDeg = floor ? num(floor.floor_v_deg) : null;
  return {
    version, hDeg, vDeg, bandLo, bandHi, loH, loV, f0, diTarget,
    floorHz, floorHDeg, floorVDeg,
    available: hDeg != null || vDeg != null || diTarget != null || floorHDeg != null || floorVDeg != null,
    brief: ac.brief?.name || ac.brief?.label || (typeof ac.brief === "string" ? ac.brief : null)
      || (typeof detail.observation?.brief === "string" ? detail.observation.brief : null),
  };
}

function targetSummary(target) {
  if (!target.available) {
    return `<p class="muted">Scoring target unavailable — the stored acoustics artifact does not record the resolved target. It is not guessed from the typology.</p>`;
  }
  const bits = [];
  if (target.hDeg != null) bits.push(`H ${fmtNum(target.hDeg, 0)}°`);
  if (target.vDeg != null) bits.push(`V ${fmtNum(target.vDeg, 0)}°`);
  if (target.diTarget != null) bits.push(`DI ${fmtNum(target.diTarget, 2)} dB`);
  if (target.floorHDeg != null || target.floorVDeg != null) {
    bits.push(`8 kHz floor${target.floorHDeg != null ? ` H ${fmtNum(target.floorHDeg, 0)}°` : ""}${target.floorVDeg != null ? ` V ${fmtNum(target.floorVDeg, 0)}°` : ""}`);
  }
  const band = target.bandLo != null && target.bandHi != null ? `${fmtNum(target.bandLo, 0)}–${fmtNum(target.bandHi, 0)} Hz` : null;
  return `<p class="res-target"><strong>Recorded scoring target</strong> ${esc(bits.join(" · "))}${band ? ` · ${esc(band)}` : ""}${target.version != null ? ` · objective v${esc(target.version)}` : ""}${target.brief ? ` · brief ${esc(label(target.brief))}` : ""}</p>`;
}

function renderObservationSummary(state) {
  const row = state.currentRow || {};
  const obs = state.detail?.observation || {};
  const designHash = state.selection?.designHash || row.designHash || obs.designHash;
  const solveId = state.selection?.solveId || row.solveId || obs.solveId;
  const tier = state.selection?.tier || row.tier || "—";
  const stateText = obs.state || row.state;
  const physical = row.refused ? "refused" : row.verified || tier === "verify" ? "verified"
    : row.measured ? "measured" : (row.state === "predicted_only" || row.predictedMean != null) ? "predicted only" : "not measured";
  const reasons = [...(obs.reasons || []), ...(row.reasons || [])].filter(Boolean).slice(0, 4);
  const dims = row.dimensions ? Object.entries(row.dimensions).filter(([, v]) => num(v) != null || (typeof v === "string" && v)).slice(0, 12) : [];
  return `<section class="bo-panel res-detail-head">
    <div class="bo-head"><h3>Selected horn</h3><div class="pill-row">
      <span class="pill ${physical === "verified" ? "good" : physical === "refused" ? "bad" : ""}">${esc(physical)}</span>
      <span class="pill">${esc(label(tier))}</span>
      ${stateText && stateText !== "measured" ? `<span class="pill warn">evidence: ${esc(label(stateText))}</span>` : ""}
    </div></div>
    <dl class="res-dl">
      <dt>Design hash</dt><dd class="mono">${esc(designHash || "not published")}</dd>
      <dt>Solve</dt><dd class="mono">${esc(solveId || "not published")}</dd>
      <dt>Typology</dt><dd>${esc(row.typology || obs.typology || "not recorded")}</dd>
      <dt>J</dt><dd>${row.measured || row.verified ? `<span class="mono">${fmtNum(row.j)}</span>` : (row.predictedMean != null ? `<span class="mono">${fmtNum(row.predictedMean)}</span> <span class="pill warn">model interval, not measured</span>` : "—")}</dd>
      ${row.hasVerify && !row.verified ? `<dt>Verified J</dt><dd><span class="mono">${fmtNum(row.verifyJ)}</span> <span class="pill good">verify tier</span></dd>` : ""}
      ${dims.map(([key, value]) => `<dt>${esc(label(key))}</dt><dd class="mono">${esc(value)}</dd>`).join("")}
      ${row.reason ? `<dt>Reason</dt><dd>${esc(row.reason)}</dd>` : ""}
      ${obs.selection_reason ? `<dt>Selection reason</dt><dd>${esc(obs.selection_reason)}</dd>` : ""}
      ${obs.fallback ? `<dt>Fallback</dt><dd>${esc(label(String(obs.fallback)))}</dd>` : ""}
      ${obs.acquisition && (num(obs.acquisition.value) != null || num(obs.acquisition.rank) != null)
        ? `<dt>Acquisition</dt><dd>${num(obs.acquisition.value) != null ? `value ${fmtNum(obs.acquisition.value)}${obs.acquisition.units ? ` ${esc(obs.acquisition.units)}` : ""}` : ""}${num(obs.acquisition.rank) != null ? ` · rank ${fmtNum(obs.acquisition.rank, 0)}` : ""} <span class="muted">ranking signal, not a probability or a measured quality</span></dd>` : ""}
      ${reasons.length ? `<dt>Notes</dt><dd>${reasons.map(esc).join("; ")}</dd>` : ""}
    </dl>
    ${physical === "predicted only" ? `<p class="alert warn">No physical measurement exists for this candidate yet. The J shown is a model credible interval — it is never a measured curve or a verified score.</p>` : ""}
  </section>`;
}

function chartCard(key, title, caption, extra = "") {
  return `<figure class="study-chart res-chart-card"><figcaption><strong>${esc(title)}</strong></figcaption><svg data-res-chart="${esc(key)}" role="img" aria-label="${esc(title)}"></svg>${extra}<figcaption class="muted">${esc(caption)}</figcaption></figure>`;
}

function renderAcousticCards(state) {
  const ac = state.detail?.acoustics;
  if (!ac) {
    return emptyBlock("Acoustic artifacts are not published yet", errorReason("acoustics", state.detail?.resource?.acoustics), "No curves are drawn when the stored artifact is absent; nothing is interpolated.");
  }
  const cards = [];
  if (ac.bwH.some(v => v != null) || ac.bwV.some(v => v != null)) {
    cards.push(chartCard("bw", "Beamwidth H / V vs frequency",
      "−6 dB beamwidth. Dotted guides are the recorded scoring targets, drawn only across the scored band."));
  }
  if (ac.polarH && ac.angles.length) {
    cards.push(chartCard("iso_h", "Isobar map — horizontal", "Level relative to on-axis, 3 dB bands. Coverage guides follow the recorded target.", `<div class="iso-legend">${isoLegend()}</div>`));
  }
  if (ac.polarV && ac.angles.length) {
    cards.push(chartCard("iso_v", "Isobar map — vertical", "Level relative to on-axis, 3 dB bands. Coverage guides follow the recorded target."));
  }
  if (ac.polarH && ac.angles.length) cards.push(chartCard("polar_h", "Horizontal cuts", "Directional level by angle and frequency."));
  if (ac.polarV && ac.angles.length) cards.push(chartCard("polar_v", "Vertical cuts", "Directional level by angle and frequency."));
  if (ac.onAxis.some(v => v != null)) cards.push(chartCard("on_axis", "On-axis response", "Measured on-axis response, normalised per the stored artifact."));
  if (ac.di.some(v => v != null)) cards.push(chartCard("di", "Directivity index", ac.diSource ? `Stored DI source: ${esc(ac.diSource)}.` : "DI as stored; source not recorded."));
  if (ac.zRe.some(v => v != null) || ac.zIm.some(v => v != null)) cards.push(chartCard("impedance", "Throat impedance", "Stored real and imaginary throat impedance."));
  if (ac.ripH.some(v => v != null) || ac.ripV.some(v => v != null)) cards.push(chartCard("ripple", "Acoustic ripple", "Stored ripple by plane; this is a measured result, not a scoring contribution."));
  if (!cards.length) {
    return emptyBlock("Acoustic arrays are empty", "The artifact exists but carries no drawable curve for this design.", "No placeholder curve is synthesised.");
  }
  return `<div class="res-chart-grid">${cards.join("")}</div>`;
}

function isoLegend() {
  return `<span class="iso-key"><span class="swatch dashed"></span>coverage target</span><span class="iso-key"><span class="swatch"></span>−6 dB edge</span>`;
}

function renderScoring(state) {
  const target = scoringTarget(state);
  const ac = state.detail?.acoustics;
  const coverage = ac && ac.freqs.length
    ? `Frequency coverage: ${fmtNum(ac.freqs[0], 0)}–${fmtNum(ac.freqs[ac.freqs.length - 1], 0)} Hz · ${fmtNum(ac.freqs.length, 0)} solved frequencies.`
    : "Frequency coverage is not recorded in the acoustics artifact.";
  const identity = `${target.version != null ? `objective v${esc(target.version)}` : "objective version not recorded"}${target.brief ? ` · brief ${esc(label(target.brief))}` : ""}`;
  return `<section class="bo-panel"><div class="bo-head"><h3>Objective and scoring context</h3><span class="pill">${target.available ? "recorded" : "unavailable"}</span></div><p class="muted">${identity}</p>${targetSummary(target)}<p class="muted">${esc(coverage)}</p><p class="muted">The guide lines come from the stored target/objective payload. Curves are measured results; scoring terms are not converted into degrees or dB.</p></section>`;
}

function renderInspector(state) {
  const selection = state.selection;
  if (!selection) {
    return `<section class="bo-panel"><div class="bo-head"><h3>Horn inspector</h3></div>${emptyBlock("Select a horn", "Choose a row in the table to open its stored geometry and acoustics.")}</section>`;
  }
  const detail = state.detail;
  const head = `<div class="bo-head"><h3>Horn inspector</h3><div class="pill-row"><a href="${esc(resultRoute(state.studyId, "horns", { root: state.rootRef, solve: null, tier: null, design: null }))}" data-res-all>← All horns</a></div></div>`;
  if (!detail) {
    return `<section class="bo-panel res-inspector">${head}${state.loadingList
      ? loadingBlock("Loading the stored geometry and acoustics…")
      : emptyBlock("No observation artifacts are published yet", state.listError || state.listReason || "The selected observation has no detail payload.", "The list remains the source of truth; nothing is synthesised here.")}</section>`;
  }
  if (detail.loading) return `<section class="bo-panel res-inspector">${head}${loadingBlock("Loading the stored geometry and acoustics…")}</section>`;
  const geo = detail.geometry;
  const geoError = errorReason("geometry", detail.resource?.geometry);
  const canProfile = !!detail.acoustics?.profile || !!geo?.profile;
  const threeD = geo
    ? `<div class="res-3d" data-res-3d data-v3d></div>${geo.preview ? `<p class="alert warn">${esc(geo.notice || "Geometry-only preview from the pinned design/config. This is not the stored solved surface and no BEM was run.")}</p>` : ""}<p class="muted">${geo.preview ? "Geometry-only preview" : `Stored ${esc(state.selection.tier || "screen")} mesh`}${geo.nTris ? ` · ${fmtNum(geo.nTris, 0)} triangles` : ""}. Read-only GET; no solve is started by opening this view.</p>`
    : canProfile
      ? `<div class="res-3d" data-res-3d data-v3d></div><p class="muted">Stored mesh is missing; showing the recorded wall profile only (not a solved surface). ${esc(geoError)}</p>`
      : `<div class="res-3d-missing">${esc(geoError)}</div><p class="muted">Opening this page never starts a solve. A higher-fidelity verification is a deliberate action below.</p>`;
  return `<section class="bo-panel res-inspector" aria-label="Horn inspector">
    ${head}
    ${renderObservationSummary(state)}
    ${renderScoring(state)}
    <div class="res-split">
      <div class="res-3d-card"><h4>Geometry</h4>${threeD}</div>
      <div class="res-acoustic-card"><h4>Acoustic panels</h4>${renderAcousticCards(state)}</div>
    </div>
    ${renderCompare(state)}
    ${renderBalloon(state)}
    ${renderVerifyAction(state)}
    ${renderAdvanced(state)}
  </section>`;
}

function renderCompareCard(labelText, row, ac, key, error) {
  const j = row?.j;
  return `<div class="res-compare-card">
    <h5>${esc(labelText)}</h5>
    <p>${row ? `<span class="pill ${row.verified ? "good" : ""}">${row.verified ? "verified" : "screen"}</span> <span class="mono">J ${fmtNum(j)}</span>${row.coverage_deg != null ? ` · coverage ${fmtNum(row.coverage_deg, 3)}°` : ""}${row.ripple_db != null ? ` · ripple ${fmtNum(row.ripple_db, 3)} dB` : ""}` : '<span class="muted">not recorded</span>'}</p>
    ${ac ? `<svg data-res-compare-chart="${esc(key)}" role="img" aria-label="${esc(`${labelText} beamwidth`)}"></svg>` : `<p class="muted">${esc(error || "No acoustic artifact for this tier.")}</p>`}
  </div>`;
}

function renderCompare(state) {
  const sel = state.selection;
  const detail = state.detail;
  if (!detail || !sel) return "";
  const compare = detail.compare;
  const currentTier = (sel.tier || state.currentRow?.tier || detail.observation?.tier) === "verify" ? "verify" : "screen";
  const currentRow = state.currentRow || { tier: currentTier, verified: currentTier === "verify" };
  const currentAc = detail.acoustics;
  if (!compare || compare.missing) {
    const other = currentTier === "verify" ? "screen" : "verify";
    return `<section class="bo-panel"><div class="bo-head"><h3>Screen vs verify</h3><span class="pill">${other} not recorded</span></div><p class="muted">${esc(compare?.reason || `No ${other}-tier measurement is recorded for this design. The ${currentTier} result stands alone; the two tiers are never merged.`)}</p></section>`;
  }
  const otherTier = compare.tier;
  const screenRow = currentTier === "screen" ? currentRow : compare.row;
  const verifyRow = currentTier === "verify" ? currentRow : compare.row;
  const screenAc = currentTier === "screen" ? currentAc : compare.acoustics;
  const verifyAc = currentTier === "verify" ? currentAc : compare.acoustics;
  const delta = num(screenRow?.j) != null && num(verifyRow?.j) != null ? Number(verifyRow.j) - Number(screenRow.j) : null;
  return `<section class="bo-panel"><div class="bo-head"><h3>Screen vs verify</h3><span class="pill">${esc(delta == null ? "separate tiers" : `verify − screen ${fmtDelta(delta)} J`)}</span></div>
    <div class="res-compare-grid">
      ${renderCompareCard("Screen tier", screenRow, screenAc, "screen", errorReason("screen acoustics", compare?.error))}
      ${renderCompareCard("Verify tier", verifyRow, verifyAc, "verify", errorReason("verify acoustics", compare?.error))}
    </div>
    <p class="muted">Both panels come from their own recorded tier. The delta is shown only when both scores exist; source identities are preserved.</p></section>`;
}

function renderBalloon(state) {
  const balloon = state.detail?.balloon;
  if (!balloon) {
    const reason = errorReason("balloon", state.detail?.resource?.balloon);
    return `<section class="bo-panel"><div class="bo-head"><h3>Balloon</h3><span class="pill">not recorded</span></div><p class="muted">${esc(reason)}</p><p class="muted">A balloon is shown only when the stored response carries a full balloon grid; cuts alone are never relabelled as a balloon.</p></section>`;
  }
  const freqs = Array.isArray(balloon.freqs_hz) ? balloon.freqs_hz : [];
  const options = freqs.map((f, index) => `<option value="${index}">${esc(fmtNum(f, 0))} Hz</option>`).join("");
  return `<section class="bo-panel"><div class="bo-head"><h3>Balloon</h3><span class="pill good">stored grid ${esc((balloon.balloon_grid || []).join("×"))}</span></div>
    <div class="res-balloon" data-res-balloon data-v3d></div>
    ${options ? `<label class="res-balloon-freq">Frequency <select data-res-balloon-freq>${options}</select></label>` : ""}
    <p class="muted">Rendered from the stored balloon response. No interpolation or solve is added here.</p></section>`;
}

function renderVerifyAction(state) {
  const row = state.currentRow;
  const sel = state.selection;
  const obs = state.detail?.observation;
  const design = sel?.designHash || row?.designHash;
  const isVerified = sel?.tier === "verify" || row?.verified === true;
  const physical = row ? (row.measured || row.refused) : (obs ? obs.state !== "predicted_only" && obs.physical_measurement !== false : true);
  const disabled = !design || isVerified || !physical || state.busy;
  const reason = isVerified ? "This observation is already a verified solve."
    : !design ? "No design hash is published for this observation, so no verification can be requested from here."
      : !physical ? "This design has no physical measurement; verification is not available."
        : "";
  return `<section class="bo-panel res-verify"><div class="bo-head"><h3>Verify at higher fidelity</h3><span class="pill warn">separate GPU action</span></div>
    <p>Opening the mesh, curves or balloon is a read-only GET. Verification is a different, explicitly costed action: one GPU verify solve, substantially more expensive than a screen solve. It is not required to review the stored results.</p>
    <button type="button" data-res-verify="${esc(design || "")}"${disabled ? " disabled" : ""}${reason ? ` title="${esc(reason)}"` : ""}>Verify at higher fidelity…</button>
    ${reason ? `<p class="muted">${esc(reason)}</p>` : ""}
    <p class="muted">The stored screen/verify artifacts stay available before, during and after this action.</p></section>`;
}

function renderAdvanced(state) {
  const sel = state.selection || {};
  const res = state.detail?.resource || {};
  const obs = state.detail?.observation || {};
  const identities = obs.identities && typeof obs.identities === "object" ? obs.identities : {};
  const statuses = Object.entries(res).map(([key, value]) => `${key}: ${value?.ok ? "available" : value?.status === 404 ? "404" : value?.missing ? "endpoint not exposed" : "unavailable"}`).join(" · ");
  const identityRows = Object.entries(identities)
    .filter(([, value]) => typeof value === "string" && value)
    .slice(0, 12)
    .map(([key, value]) => `<dt>${esc(label(key))}</dt><dd class="mono">${esc(value)}</dd>`).join("");
  return `<details class="study-advanced"><summary>Advanced — observation artifact identities</summary>
    <dl class="res-dl"><dt>solve_id</dt><dd class="mono">${esc(sel.solveId || obs.solveId || "—")}</dd><dt>tier</dt><dd>${esc(sel.tier || obs.tier || "—")}</dd><dt>design_hash</dt><dd class="mono">${esc(sel.designHash || obs.designHash || "—")}</dd>${identityRows}<dt>Endpoints</dt><dd>${esc(statuses || "not requested")}</dd></dl>
  </details>`;
}

// ── Explore ────────────────────────────────────────────────────────────────────────

function renderExplore(state) {
  if (state.loadingExplore && !state.explain) return loadingBlock("Loading the design-space and frontier panels…");
  const bo = state.explain?.data?.bo && typeof state.explain.data.bo === "object" ? state.explain.data.bo : {};
  const space = bo.design_space;
  const pareto = bo.pareto;
  const conv = state.exploreExec?.data?.bo?.convergence;
  const cards = [];
  if (space && ["ready", "partial"].includes(space.status) && Array.isArray(space.points) && space.points.length) {
    const unresolved = space.points.filter(point => !point.design_hash).length;
    cards.push(`<section class="bo-panel"><div class="bo-head"><h3>Design-space map (PCA)</h3><span class="pill">${space.points.length} points</span></div>
      <div class="study-chart"><svg data-res-explore="space" role="img" aria-label="Two-dimensional PCA projection of designs; identity-bearing points open the horn inspector"></svg></div>
      <p class="muted">Axes are a projection, not acoustics. ${unresolved ? `${fmtNum(unresolved, 0)} training point${unresolved === 1 ? " has" : "s have"} no resolvable design hash and are drawn hollow — they cannot open a horn.` : "Every plotted point carries a design hash."}</p>
      <p class="muted" data-res-unresolved-note></p></section>`);
  }
  if (pareto && ["ready", "partial"].includes(pareto.status) && Array.isArray(pareto.points) && pareto.points.length) {
    cards.push(`<section class="bo-panel"><div class="bo-head"><h3>Coverage × ripple frontier</h3><span class="pill">measured</span></div>
      <div class="study-chart"><svg data-res-explore="pareto" role="img" aria-label="Measured coverage error against ripple error; identity-bearing points open the horn inspector"></svg></div>
      <p class="muted">Frontier axes are plain coverage error (deg) and ripple error (dB). J is shown beside each point in the list; it is not the frontier objective.</p></section>`);
  }
  if (conv && conv.status !== "not_applicable" && Array.isArray(conv.arms) && conv.arms.some(arm => Array.isArray(arm?.points) && arm.points.length)) {
    cards.push(`<section class="bo-panel"><div class="bo-head"><h3>Convergence</h3><span class="pill">recorded</span></div>
      <div class="study-chart"><svg data-study-chart="convergence" role="img" aria-label="Best recorded J by solve index"></svg><div class="study-chart-legend"></div></div>
      <p class="muted">Markers are best-so-far and individual solves. The convergence payload does not yet carry a design/solve identity per marker; use the measured-candidate list below to open the same inspector by identity.</p></section>`);
  }
  if (state.exploreRows?.length) {
    const buttons = state.exploreRows.slice(0, 20).map(row => `<button type="button" class="res-explore-row" data-res-select data-solve="${esc(row.solveId || "")}" data-tier="${esc(row.tier || "")}" data-design="${esc(row.designHash || "")}"><span class="mono">${esc(shortId(row.designHash))}</span> <span class="muted">${esc(label(row.tier || "tier"))}</span> <span class="mono">J ${fmtNum(row.j)}</span></button>`).join("");
    cards.push(`<section class="bo-panel"><div class="bo-head"><h3>Measured candidates</h3><span class="pill">click one to inspect</span></div><div class="res-explore-list">${buttons}</div><p class="muted">Every row opens the inspector by solve_id/design_hash. Prediction-only rows are never listed as measured.</p></section>`);
  }
  if (!cards.length) {
    const reason = bo.design_space?.reason || bo.pareto?.reason || state.explainError?.message || "No design-space, frontier or measured-candidate data is published for this study yet.";
    return emptyBlock("Nothing to explore yet", reason);
  }
  return `<div class="res-explore">${cards.join("")}</div>`;
}

// ── chart drawing ──────────────────────────────────────────────────────────────────

function drawBw(svg, ac, target, { W = 520, H = 250, title = "" } = {}) {
  if (!svg || !ac || !ac.freqs.length) return false;
  const h = pairSeries(ac.freqs, ac.bwH);
  const v = pairSeries(ac.freqs, ac.bwV);
  if (!h.length && !v.length) return false;
  const series = [
    { pts: h, color: catColor(0), w: 2 },
    { pts: v, color: catColor(1), w: 2 },
  ];
  if (target?.floorHz != null) {
    const floorPoints = [];
    if (target.floorHDeg != null) floorPoints.push([target.floorHz, target.floorHDeg]);
    if (target.floorVDeg != null) floorPoints.push([target.floorHz, target.floorVDeg]);
    if (floorPoints.length) series.push({ pts: floorPoints, dots: true, r: 3.6, color: catColor(3), opacity: 1 });
  }
  const allY = [...h, ...v].map(point => point[1]);
  const targetY = [target?.hDeg, target?.vDeg, target?.floorHDeg, target?.floorVDeg].filter(value => value != null);
  const ymax = Math.max(1, ...allY, ...targetY);
  const xlim = [ac.freqs[0], ac.freqs[ac.freqs.length - 1]];
  const refLines = [];
  if (target?.available) {
    const end = Math.min(target.bandHi ?? xlim[1], xlim[1]);
    if (target.hDeg != null) {
      const lo = Math.max(target.loH ?? xlim[0], xlim[0]);
      refLines.push({ pts: [[lo, target.hDeg], [end, target.hDeg]], label: `target H ${fmtNum(target.hDeg, 0)}°` });
    }
    if (target.vDeg != null) {
      const lo = Math.max(target.loV ?? xlim[0], xlim[0]);
      refLines.push({ pts: [[lo, target.vDeg], [end, target.vDeg]], label: `target V ${fmtNum(target.vDeg, 0)}°` });
    }
  }
  const vlines = [];
  if (target?.f0 != null && target.f0 > xlim[0] && target.f0 < xlim[1]) {
    vlines.push({ x: target.f0, dash: true, label: `f0 ${target.f0 != null ? fmtNum(target.f0, 0) : ""} Hz` });
  }
  if (target?.floorHz != null && target.floorHz > xlim[0] && target.floorHz < xlim[1]) {
    vlines.push({ x: target.floorHz, dash: true, label: "8 kHz beamwidth floor" });
  }
  chart(svg, {
    W, H, xlog: true, xlim, ylim: [0, ymax * 1.08],
    xticks: logTicks(xlim[0], xlim[1]), yticks: niceTicks(0, ymax * 1.08, 5),
    xlabel: "frequency (Hz)", ylabel: "−6 dB beamwidth (deg)",
    series, refLines, vlines,
    ariaLabel: `${title || "Beamwidth H and V against frequency, with recorded scoring targets"}`,
  });
  return true;
}

function drawLine(svg, ac, key, ylabel, title, { W = 460, H = 220 } = {}) {
  if (!svg || !ac || !ac.freqs.length) return false;
  const series = [];
  if (key === "on_axis") series.push({ pts: pairSeries(ac.freqs, ac.onAxis), color: catColor(0), w: 2 });
  if (key === "di") series.push({ pts: pairSeries(ac.freqs, ac.di), color: catColor(0), w: 2 });
  if (key === "ripple") {
    series.push({ pts: pairSeries(ac.freqs, ac.ripH), color: catColor(0), w: 2 });
    series.push({ pts: pairSeries(ac.freqs, ac.ripV), color: catColor(1), w: 2 });
  }
  if (key === "impedance") {
    series.push({ pts: pairSeries(ac.freqs, ac.zRe), color: catColor(0), w: 2 });
    series.push({ pts: pairSeries(ac.freqs, ac.zIm), color: catColor(1), w: 2 });
  }
  const points = series.flatMap(item => item.pts);
  if (!points.length) return false;
  const ys = points.map(point => point[1]);
  const ylim = [Math.min(...ys), Math.max(...ys)];
  const pad = Math.max(0.05, Math.abs(ylim[1] - ylim[0]) * 0.08);
  const xlim = [ac.freqs[0], ac.freqs[ac.freqs.length - 1]];
  chart(svg, {
    W, H, xlog: true, xlim, ylim: [ylim[0] - pad, ylim[1] + pad],
    xticks: logTicks(xlim[0], xlim[1]), yticks: niceTicks(ylim[0] - pad, ylim[1] + pad, 5),
    xlabel: "frequency (Hz)", ylabel, series,
    ariaLabel: title,
  });
  return true;
}

function drawDI(svg, ac, target) {
  if (!svg || !ac || !ac.freqs.length || !ac.di.some(v => v != null)) return false;
  const pts = pairSeries(ac.freqs, ac.di);
  if (!pts.length) return false;
  const ys = pts.map(point => point[1]);
  if (target?.diTarget != null) ys.push(target.diTarget);
  const ylim = [Math.min(...ys), Math.max(...ys)];
  const pad = Math.max(0.2, Math.abs(ylim[1] - ylim[0]) * 0.1);
  const xlim = [ac.freqs[0], ac.freqs[ac.freqs.length - 1]];
  const refLines = target?.diTarget != null
    ? [{ y: target.diTarget, label: `DI target ${fmtNum(target.diTarget, 2)} dB (recorded)` }] : [];
  chart(svg, {
    W: 460, H: 220, xlog: true, xlim, ylim: [ylim[0] - pad, ylim[1] + pad],
    xticks: logTicks(xlim[0], xlim[1]), yticks: niceTicks(ylim[0] - pad, ylim[1] + pad, 5),
    xlabel: "frequency (Hz)", ylabel: "DI (dB)",
    series: [{ pts, color: catColor(0), w: 2 }], refLines,
    ariaLabel: "Directivity index against frequency, with the recorded DI target when present",
  });
  return true;
}

function drawIsobar(svg, ac, target, plane) {
  if (!svg || !ac) return false;
  const rows = plane === "h" ? ac.polarH : ac.polarV;
  if (!rows || !ac.angles.length || ac.freqs.length < 2) return false;
  const deg = plane === "h" ? target?.hDeg : target?.vDeg;
  const lo = plane === "h" ? target?.loH : target?.loV;
  const xlim = target?.bandLo != null && target?.bandHi != null ? [target.bandLo, target.bandHi] : undefined;
  isobarMap(svg, rows, ac.angles, ac.freqs, {
    H: 300, title: plane === "h" ? "Horizontal" : "Vertical", legend: true,
    f0: target?.f0 ?? undefined, target: deg ?? undefined, targetLoHz: lo ?? undefined, xlim,
  });
  return true;
}

function drawPolar(svg, ac, plane) {
  if (!svg || !ac) return false;
  const rows = plane === "h" ? ac.polarH : ac.polarV;
  if (!rows || !ac.angles.length) return false;
  polarMap(svg, rows, ac.angles, ac.freqs, { H: 230 });
  return true;
}

function drawAcousticCharts(state) {
  const ac = state.detail?.acoustics;
  if (!ac) return;
  const target = scoringTarget(state);
  const find = key => state.root?.querySelector?.(`svg[data-res-chart="${key}"]`);
  drawBw(find("bw"), ac, target);
  drawIsobar(find("iso_h"), ac, target, "h");
  drawIsobar(find("iso_v"), ac, target, "v");
  drawPolar(find("polar_h"), ac, "h");
  drawPolar(find("polar_v"), ac, "v");
  drawLine(find("on_axis"), ac, "on_axis", "on-axis (dB)", "On-axis response against frequency");
  drawDI(find("di"), ac, target);
  drawLine(find("impedance"), ac, "impedance", "throat impedance (Ω)", "Throat impedance against frequency");
  drawLine(find("ripple"), ac, "ripple", "ripple (dB)", "Acoustic ripple against frequency");
  const compare = state.detail?.compare;
  if (compare && compare.acoustics) {
    const screenAc = state.selection?.tier === "screen" ? ac : compare.acoustics;
    const verifyAc = state.selection?.tier === "verify" ? ac : compare.acoustics;
    drawBw(state.root?.querySelector?.('svg[data-res-compare-chart="screen"]'), screenAc, target, { W: 360, H: 200, title: "Screen-tier beamwidth" });
    drawBw(state.root?.querySelector?.('svg[data-res-compare-chart="verify"]'), verifyAc, target, { W: 360, H: 200, title: "Verify-tier beamwidth" });
  }
}

function drawExploreCharts(state) {
  const bo = state.explain?.data?.bo && typeof state.explain.data.bo === "object" ? state.explain.data.bo : {};
  const root = state.root;
  if (!root || typeof root.querySelector !== "function") return;
  if (state.exploreExec) drawStudyCharts(root, state.exploreExec);
  const spaceSvg = root.querySelector('svg[data-res-explore="space"]');
  if (spaceSvg && bo.design_space) {
    const limits = designSpaceLimits(bo.design_space);
    if (limits) {
      chart(spaceSvg, {
        W: 560, H: 320, xlim: limits.xlim, ylim: limits.ylim,
        xticks: niceTicks(limits.xlim[0], limits.xlim[1], 5),
        yticks: niceTicks(limits.ylim[0], limits.ylim[1], 5),
        xlabel: "component 1", ylabel: "component 2",
        series: [
          { pts: bo.design_space.points.filter(point => point.source === "training").map(point => [point.x, point.y]), dots: true, r: 2.2, opacity: 0.55, color: catColor(7) },
          { pts: bo.design_space.points.filter(point => point.source !== "training").map(point => [point.x, point.y]), dots: true, r: 3, opacity: 0.9, color: catColor(0) },
        ],
        ariaLabel: "Two-dimensional PCA projection of designs; identity-bearing points open the horn inspector",
      });
      const markers = bo.design_space.points.map(point => ({
        x: point.x, y: point.y, j: point.j,
        designHash: point.design_hash || null, solveId: point.solve_id || null,
      }));
      const result = addIdentityMarkers(spaceSvg, markers, ({ designHash }) => selectDesign(state, designHash));
      const note = root.querySelector("[data-res-unresolved-note]");
      if (note && result.unresolved) {
        note.textContent = `${result.unresolved} plotted training point${result.unresolved === 1 ? "" : "s"} has no resolvable design hash; the hollow ring${result.unresolved === 1 ? " is" : "s are"} not clickable.`;
      }
    }
  }
  const paretoSvg = root.querySelector('svg[data-res-explore="pareto"]');
  if (paretoSvg && bo.pareto) {
    const limits = paretoLimits(bo.pareto);
    if (limits) {
      const points = bo.pareto.points || [];
      chart(paretoSvg, {
        W: 560, H: 320, xlim: limits.xlim, ylim: limits.ylim,
        xticks: niceTicks(limits.xlim[0], limits.xlim[1], 5),
        yticks: niceTicks(limits.ylim[0], limits.ylim[1], 5),
        xlabel: "coverage error (deg)", ylabel: "ripple error (dB)",
        series: [
          { pts: points.filter(point => !point.nondominated).map(point => [point.coverage_deg, point.ripple_db]), dots: true, r: 2.3, opacity: 0.55, color: catColor(7) },
          { pts: points.filter(point => point.nondominated).map(point => [point.coverage_deg, point.ripple_db]), dots: true, r: 3.2, opacity: 0.95, color: catColor(2) },
        ],
        ariaLabel: "Measured coverage error against ripple error; identity-bearing points open the horn inspector",
      });
      addIdentityMarkers(paretoSvg, points.map(point => ({
        coverage_deg: point.coverage_deg, ripple_db: point.ripple_db, j: point.j,
        designHash: point.design_hash || null, solveId: point.solve_id || null,
      })), ({ designHash }) => selectDesign(state, designHash));
    }
  }
}

// ── data access (injected adapters only) ───────────────────────────────────────────

async function get(fn, args) {
  if (typeof fn !== "function") return { ok: false, missing: true };
  try {
    return { ok: true, payload: await fn(...args) };
  } catch (error) {
    if (error?.name === "AbortError") return { ok: false, aborted: true };
    return { ok: false, error, status: Number(error?.status) || null };
  }
}

function verifyRowFor(row) {
  if (!row || !row.hasVerify) return null;
  return {
    ...row,
    solveId: row.verifySolveId,
    tier: "verify",
    kind: row.verifyKind || "verify",
    verified: true,
    measured: true,
    j: row.verifyJ,
    hasVerify: true,
    verifyJ: row.verifyJ,
  };
}

function findRow(state, selection) {
  if (!selection) return null;
  const pool = [...(state.crossRows || []), ...state.rows];
  if (selection.solveId) {
    const match = pool.find(row => row.solveId === selection.solveId);
    if (match) return match;
    const withVerify = pool.find(row => row.verifySolveId === selection.solveId);
    if (withVerify) return verifyRowFor(withVerify);
  }
  if (selection.designHash) {
    const candidates = pool.filter(row => row.designHash === selection.designHash);
    if (selection.tier === "verify") {
      const withVerify = candidates.find(row => row.hasVerify);
      if (withVerify) return verifyRowFor(withVerify);
    }
    return candidates.find(row => row.measured && !row.verified)
      || candidates.find(row => row.measured)
      || candidates[0] || null;
  }
  return null;
}

function defaultSelection(rows) {
  const verified = rows.filter(row => row.measured && row.hasVerify && row.verifyJ != null);
  if (verified.length) {
    const best = verified.reduce((a, b) => (b.verifyJ < a.verifyJ ? b : a));
    return { solveId: best.verifySolveId, tier: "verify", designHash: best.designHash };
  }
  const measured = rows.filter(row => row.measured && row.j != null);
  const choice = measured[0] || rows.find(row => row.predictedMean != null) || rows[0];
  return choice ? { solveId: choice.solveId, tier: choice.tier || "screen", designHash: choice.designHash } : null;
}

async function fetchAllPages(state, signal, { pages = MAX_SCAN_PAGES, size = SCAN_PAGE_SIZE } = {}) {
  let page = 1, rows = [], total = 0, status = null, reason = null, truncated = false;
  let hasTotal = false;
  while (page <= pages) {
    const response = await state.api.getObservations(state.studyId, {
      page, pageSize: size, sort: backendSort(state.sort), root: state.rootRef, signal,
    });
    const parsed = normalizeList(response);
    const before = rows.length;
    const seen = new Set(rows.map(row => row.solveId || `${row.designHash}|${row.tier}|${row.attempt}`));
    for (const row of parsed.rows) {
      const key = row.solveId || `${row.designHash}|${row.tier}|${row.attempt}`;
      if (!seen.has(key)) { seen.add(key); rows.push(row); }
    }
    hasTotal = hasTotal || parsed.hasTotal;
    total = parsed.total;
    status = parsed.status;
    reason = parsed.reason || reason;
    if (!parsed.rows.length || rows.length === before) break;   // empty or a repeated page
    if (hasTotal && rows.length >= total) break;
    page += 1;
  }
  if (hasTotal && rows.length < total) truncated = true;
  return { rows, total: Math.max(total, rows.length), hasTotal, status, reason, truncated };
}

async function scanForDesign(state, designHash, tier, signal) {
  if (!designHash) return null;
  const cached = (state.crossRows || []).find(row => row.designHash === designHash && (!tier || row.tier === tier));
  if (cached) return cached;
  if (state.crossScanDone) return null;
  state.crossScanDone = true;
  const parsed = await fetchAllPages(state, signal, { pages: COMPARE_SCAN_PAGES });
  state.crossRows = parsed.rows;
  return parsed.rows.find(row => row.designHash === designHash && (!tier || row.tier === tier)) || null;
}

async function loadDetailData(state, selection, signal, token) {
  const row = findRow(state, selection);
  state.currentRow = row;
  const solveId = selection.solveId || row?.solveId || null;
  const tier = selection.tier || row?.tier || "screen";
  if (!isId(solveId || "")) {
    state.detail = {
      loading: false, observation: null, geometry: null, acoustics: null, balloon: null,
      resource: { observation: { missing: true }, geometry: { missing: true }, acoustics: { missing: true }, balloon: { missing: true } },
      compare: { missing: true, reason: "No solve_id is published for this design, so its artifacts cannot be resolved yet." },
    };
    return;
  }
  const args = [state.studyId, solveId];
  const [observation, geometry, acoustics, balloon] = await Promise.all([
    get(state.api.getObservation, [...args, { root: state.rootRef, signal }]),
    get(state.api.getObservationGeometry, [...args, { tier, root: state.rootRef, signal }]),
    get(state.api.getObservationAcoustics, [...args, { tier, root: state.rootRef, signal }]),
    get(state.api.getObservationBalloon, [...args, { tier, root: state.rootRef, signal }]),
  ]);
  if (token !== state.op || signal.aborted) return;
  const detail = {
    loading: false,
    observation: observation.ok ? normalizeDetail(observation.payload) : null,
    geometry: geometry.ok ? normalizeGeometry(geometry.payload) : null,
    acoustics: acoustics.ok ? normalizeAcoustics(acoustics.payload) : null,
    balloon: balloon.ok ? normalizeBalloon(balloon.payload) : null,
    resource: {
      observation: decorateResource(observation),
      geometry: decorateResource(geometry),
      acoustics: decorateResource(acoustics),
      balloon: decorateResource(balloon),
    },
    compare: null,
  };
  if (detail.geometry && !detail.geometry.profile && detail.acoustics?.profile) {
    detail.geometry.profile = detail.acoustics.profile;
  }
  state.detail = detail;
  // One bounded lookup of the opposite tier; absence is a normal result and a scan failure
  // must not blank the inspector the user already opened.
  const design = selection.designHash || row?.designHash || detail.observation?.designHash;
  if (design) {
    const otherTier = tier === "verify" ? "screen" : "verify";
    try {
      // The listing attaches every verify attempt to its screen row as `verify`, so the opposite
      // tier usually needs no extra scan.  A deep link that lands outside the loaded page is the
      // one case that still resolves through the bounded design scan.
      let screenRow = findRow(state, { designHash: design, tier: "screen" });
      if (!screenRow) screenRow = await scanForDesign(state, design, "screen", signal);
      if (token !== state.op || signal.aborted) return;
      const other = otherTier === "verify" ? verifyRowFor(screenRow || row) : screenRow;
      if (!other) {
        detail.compare = { missing: true, tier: otherTier };
      } else {
        const result = await get(state.api.getObservationAcoustics, [state.studyId, other.solveId, {
          tier: otherTier, root: state.rootRef, signal,
        }]);
        if (token !== state.op || signal.aborted) return;
        detail.compare = {
          tier: otherTier, row: other,
          acoustics: result.ok ? normalizeAcoustics(result.payload) : null,
          error: decorateResource(result),
        };
      }
    } catch (error) {
      if (error?.name === "AbortError") throw error;
      detail.compare = { missing: true, tier: otherTier, reason: "The opposite-tier lookup could not be completed." };
    }
  }
}

// ── mount ──────────────────────────────────────────────────────────────────────────

const selectionMemory = new Map();

export function mountStudyResults(root, {
  studyId, tab = "results", query = "", api, rootId = null,
  pollMs = DEFAULT_POLL_MS, onError = () => {},
} = {}) {
  if (!root || !isId(studyId) || !RESULT_PHASES.includes(tab)) throw new Error("Invalid results mount");
  if (!api || typeof api.getStudy !== "function" || typeof api.getPanel !== "function"
    || typeof api.getObservations !== "function") throw new Error("Invalid results API");
  const params = new URLSearchParams(query || "");
  let rootRef = isId(rootId || "") ? rootId : (isId(params.get("root") || "") ? params.get("root") : null);
  const initial = {
    solveId: str(params.get("solve")),
    tier: params.get("tier") === "verify" ? "verify" : (params.get("tier") === "screen" ? "screen" : null),
    designHash: str(params.get("design")),
  };
  const memoryKey = `${studyId}|${rootRef || ""}`;
  const remembered = selectionMemory.get(memoryKey);
  let selection = (initial.solveId || initial.designHash) ? initial : (remembered || null);
  const state = {
    root, api, studyId, tab, rootRef, selection: null,
    study: null, studyHasPackage: false,
    overview: null, dataPanel: null, overviewError: null, loadingOverview: false,
    rows: [], total: 0, page: 1, localPage: 1, sort: "best_j", filter: "all", search: "",
    group: true, scanned: false, scanning: false, scanTruncated: false,
    loadingList: false, listError: null, listReason: null, listStatus: null, states: null,
    detail: null, currentRow: null, crossRows: [], crossScanDone: false,
    explain: null, exploreExec: null, exploreRows: [], explainError: null, loadingExplore: false,
    notice: "", error: "", busy: false, op: 0, focus: null,
  };
  if (selection) state.selection = selection;
  let disposed = false, controller = null, timer = null, paint = 0;

  const draw = () => {
    if (disposed) return;
    disposeViewers();
    root.innerHTML = renderShell(state);
    const token = ++paint;
    const focus = state.focus;
    state.focus = null;
    if (focus) {
      const field = root.querySelector?.(`[data-res-${focus.key}]`);
      if (field) {
        try {
          field.focus();
          if (typeof field.setSelectionRange === "function" && focus.pos != null) {
            field.setSelectionRange(focus.pos, focus.pos);
          }
        } catch (_) { /* a headless shim may not implement focus */ }
      }
    }
    void hydrate(token);
  };

  function disposeViewers() {
    if (typeof root.querySelectorAll !== "function") return;
    root.querySelectorAll("[data-v3d]").forEach(node => {
      try { node._dispose3d?.(); } catch (_) { /* already disposed */ }
    });
  }

  async function hydrate(token) {
    if (disposed || token !== paint) return;
    if (state.tab === "results" && state.overview) {
      try { drawStudyCharts(root, state.overview); } catch (error) { onError(error); }
      return;
    }
    if (state.tab === "horns") {
      try { drawAcousticCharts(state); } catch (error) { onError(error); }
      await mountGeometry(token);
      await mountBalloon(token);
      return;
    }
    if (state.tab === "explore") {
      try { drawExploreCharts(state); } catch (error) { onError(error); }
    }
  }

  async function mountGeometry(token) {
    const box = root.querySelector?.("[data-res-3d]");
    if (!box) return;
    const detail = state.detail;
    const geo = detail?.geometry;
    const profile = detail?.acoustics?.profile || geo?.profile || null;
    if (!geo && !profile) return;
    try {
      await init3d(box, geo?.mesh || {}, profile, null, false);
      if (disposed || token !== paint || !box.isConnected) {
        try { box._dispose3d?.(); } catch (_) { /* detached mid-load */ }
      }
    } catch (error) {
      if (token === paint && !disposed && box.isConnected) {
        box.innerHTML = `<div class="view3d-fallback">The stored geometry could not be rendered.</div>`;
      }
      onError(error);
    }
  }

  async function mountBalloon(token) {
    const box = root.querySelector?.("[data-res-balloon]");
    const payload = state.detail?.balloon;
    if (!box || !payload) return;
    try {
      const viewer = await initBalloon3d(box, payload, {});
      if (disposed || token !== paint) { viewer?.dispose?.(); return; }
      state.balloonViewer = viewer;
      const select = root.querySelector?.("[data-res-balloon-freq]");
      if (select && viewer?.setFreq) {
        select.addEventListener("change", () => {
          const index = Number(select.value);
          if (Number.isFinite(index)) viewer.setFreq(index);
        });
      }
    } catch (error) {
      onError(error);
    }
  }

  function syncUrl(next, push = false) {
    const hash = resultRoute(studyId, tab, {
      root: rootRef,
      solve: next?.solveId || null,
      tier: next?.tier || null,
      design: next?.designHash || null,
    });
    try {
      if (push && typeof globalThis.history?.pushState === "function") globalThis.history.pushState(null, "", hash);
      else if (typeof globalThis.history?.replaceState === "function") globalThis.history.replaceState(null, "", hash);
      else if (typeof globalThis.location === "object") globalThis.location.hash = hash;
    } catch (_) { /* a sandboxed document may refuse history writes; the UI state still holds */ }
  }

  function setSelection(next, { push = false } = {}) {
    state.selection = next;
    if (next) selectionMemory.set(memoryKey, next);
    else selectionMemory.delete(memoryKey);
    syncUrl(next, push);
  }

  async function refreshStudy() {
    const result = await get(api.getStudy, [studyId, { root: rootRef, signal: controller?.signal }]);
    if (!result.ok) {
      if (result.aborted) return false;
      state.error = "The study record could not be loaded.";
      onError(result.error);
      return false;
    }
    const study = result.payload || {};
    state.study = study;
    state.studyHasPackage = study.package_present === true || study.package != null;
    if (!rootRef && isId(study.root || "")) rootRef = study.root;
    return true;
  }

  async function refreshOverview() {
    state.loadingOverview = true;
    state.overviewError = null;
    draw();
    const token = ++state.op;
    controller?.abort();
    controller = new AbortController();
    try {
      const [execute, dataPanel] = await Promise.all([
        get(api.getPanel, [studyId, "execute", { root: rootRef, signal: controller.signal }]),
        get(api.getPanel, [studyId, "data", { root: rootRef, signal: controller.signal }]),
      ]);
      if (disposed || token !== state.op) return;
      if (execute.ok) state.overview = execute.payload;
      else if (!execute.aborted) {
        state.overviewError = execute.error;
        onError(execute.error);
      }
      if (dataPanel.ok) state.dataPanel = dataPanel.payload;
    } finally {
      if (!disposed && token === state.op) {
        state.loadingOverview = false;
        draw();
      }
    }
  }

  async function refreshHorns() {
    state.loadingList = true;
    state.listError = null;
    draw();
    const token = ++state.op;
    controller?.abort();
    controller = new AbortController();
    try {
      const dataPromise = state.dataPanel ? Promise.resolve({ ok: true, payload: state.dataPanel }) : get(api.getPanel, [studyId, "data", { root: rootRef, signal: controller.signal }]);
      const [response, dataPanel] = await Promise.all([
        get(api.getObservations, [studyId, {
          page: state.page, pageSize: PAGE_SIZE, sort: backendSort(state.sort), root: rootRef, signal: controller.signal,
        }]),
        dataPromise,
      ]);
      if (dataPanel?.ok) state.dataPanel = dataPanel.payload;
      if (disposed || token !== state.op || response.aborted) return;
      if (!response.ok) {
        state.listError = errorReason("observations", response);
        state.rows = [];
        state.total = 0;
        if (state.selection) {
          state.detail = {
            loading: false, observation: null, geometry: null, acoustics: null, balloon: null,
            resource: { observation: response, geometry: response, acoustics: response, balloon: response },
            compare: { missing: true },
          };
        }
        onError(response.error);
        return;
      }
      const parsed = normalizeList(response.payload);
      state.rows = parsed.rows;
      state.total = parsed.total;
      state.states = parsed.states;
      state.listStatus = parsed.status;
      state.listReason = parsed.reason;
      state.scanned = false;
      state.localPage = 1;
      if (!state.selection) {
        // The default rule is "best verified measured, else best screen measured".  The first
        // page is sorted by J, not by tier, so one bounded scan is needed to find the best
        // verified row when it sits deeper in the list.  It runs once: after this the URL
        // carries the selection and polls keep it.
        let chosen = defaultSelection(parsed.rows);
        try {
          const all = await fetchAllPages(state, controller.signal, { pages: COMPARE_SCAN_PAGES });
          if (disposed || token !== state.op) return;
          if (all.rows.length > parsed.rows.length) {
            state.crossRows = all.rows;
            state.crossScanDone = true;
            chosen = defaultSelection(all.rows) || chosen;
          }
        } catch (error) {
          if (error?.name === "AbortError") return;
          // The page-level choice is still a valid, labelled selection.
        }
        if (chosen) setSelection(chosen, false);
      }
      if (state.selection) await loadDetailData(state, state.selection, controller.signal, token);
    } finally {
      if (!disposed && token === state.op) {
        state.loadingList = false;
        draw();
      }
    }
  }

  async function refreshExplore() {
    state.loadingExplore = true;
    state.explainError = null;
    draw();
    const token = ++state.op;
    controller?.abort();
    controller = new AbortController();
    try {
      const [explain, execute, observations] = await Promise.all([
        get(api.getPanel, [studyId, "explain", { root: rootRef, signal: controller.signal }]),
        get(api.getPanel, [studyId, "execute", { root: rootRef, signal: controller.signal }]),
        get(api.getObservations, [studyId, { page: 1, pageSize: 20, sort: "best_j", root: rootRef, signal: controller.signal }]),
      ]);
      if (disposed || token !== state.op) return;
      if (explain.ok) state.explain = explain.payload;
      else if (!explain.aborted) { state.explainError = explain.error; onError(explain.error); }
      if (execute.ok) state.exploreExec = execute.payload;
      if (observations.ok) state.exploreRows = normalizeList(observations.payload).rows.filter(row => row.measured);
    } finally {
      if (!disposed && token === state.op) {
        state.loadingExplore = false;
        draw();
      }
    }
  }

  async function ensureScan() {
    if (state.scanned || state.scanning) return;
    state.scanning = true;
    paintList();
    const token = ++state.op;
    controller?.abort();
    controller = new AbortController();
    try {
      const parsed = await fetchAllPages(state, controller.signal);
      if (disposed || token !== state.op) return;
      state.rows = parsed.rows;
      state.total = parsed.total;
      state.listReason = parsed.reason || state.listReason;
      state.listError = null;
      state.scanTruncated = parsed.truncated;
      state.scanned = true;
      state.localPage = 1;
      if (state.selection) await loadDetailData(state, state.selection, controller.signal, token);
    } catch (error) {
      if (!disposed && error?.name !== "AbortError") {
        state.listError = "The full candidate scan could not be loaded.";
        onError(error);
      }
    } finally {
      if (!disposed && token === state.op) {
        state.scanning = false;
        draw();
      }
    }
  }

  async function loadSelected() {
    if (!state.selection) return;
    state.detail = { loading: true };
    draw();
    const token = ++state.op;
    controller?.abort();
    controller = new AbortController();
    try {
      await loadDetailData(state, state.selection, controller.signal, token);
    } catch (error) {
      if (error?.name !== "AbortError") {
        state.detail = {
          loading: false, observation: null, geometry: null, acoustics: null, balloon: null,
          resource: {}, compare: { missing: true, reason: "The observation detail could not be loaded." },
        };
        onError(error);
      }
    } finally {
      if (!disposed && token === state.op) draw();
    }
  }

  function presentRow(row) {
    if (!row) return;
    setSelection({ solveId: row.solveId || null, tier: row.tier || null, designHash: row.designHash || null }, { push: true });
    void loadSelected();
  }

  async function selectDesign(stateRef, designHash) {
    if (!designHash) return;
    let row = findRow(stateRef, { designHash });
    if (!row) row = await scanForDesign(stateRef, designHash, null, undefined);
    if (row) {
      selectionMemory.set(memoryKey, { solveId: row.solveId, tier: row.tier, designHash: row.designHash });
      if (typeof globalThis.location === "object") {
        globalThis.location.hash = resultRoute(studyId, "horns", {
          root: rootRef, solve: row.solveId, tier: row.tier, design: row.designHash,
        });
      }
      return;
    }
    state.notice = `Design ${designHash} has no resolvable solve in the published observations yet.`;
    draw();
  }

  async function verifyDesign(designHash) {
    if (!isHash(designHash)) { state.notice = "This design has no verifiable hash."; draw(); return; }
    if (!state.study || typeof api.action !== "function") return;
    const message = `Verify design ${designHash} at higher fidelity?\n\nThis starts one GPU verify solve. It is not needed to view the stored mesh, curves or balloon (those are read-only). Verify is substantially more expensive than a screen solve.`;
    const confirm = globalThis.confirm;
    if (typeof confirm !== "function") {
      state.notice = "Verification needs an explicit confirmation, which this browser context cannot show. No solve was started.";
      draw();
      return;
    }
    if (!confirm(message)) return;
    state.busy = true;
    draw();
    const key = globalThis.crypto?.randomUUID?.() || `verify-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const token = ++state.op;
    controller?.abort();
    controller = new AbortController();
    try {
      await api.action(studyId, "solve_design", {
        design_hash: designHash,
        expected_revision: state.study.revision,
        idempotency_key: key,
      }, { root: rootRef, signal: controller.signal });
      if (disposed || token !== state.op) return;
      state.notice = "Verification queued. The stored results remain available while it runs.";
      await refreshHorns();
    } catch (error) {
      if (disposed || error?.name === "AbortError") return;
      const status = Number(error?.status);
      state.notice = status === 409
        ? "The study changed. Refresh before requesting verification."
        : (status === 422 || status === 503 ? `Verification unavailable: ${error?.message || "prerequisite missing"}` : "Verification was not confirmed. Check the job status before retrying.");
      onError(error);
    } finally {
      state.busy = false;
      draw();
    }
  }

  function paintList() {
    if (disposed) return;
    const list = root.querySelector?.("[data-res-list]");
    if (list) list.innerHTML = renderListBody(state);
    const pager = root.querySelector?.("[data-res-pager]");
    if (pager) pager.innerHTML = renderPager(state);
    const note = root.querySelector?.(".res-list-note");
    if (note) note.textContent = listNote(state);
  }

  async function click(event) {
    const target = event.target?.closest?.("[data-res-select]");
    if (target && root.contains(target)) {
      presentRow({
        solveId: target.dataset.solve || null,
        tier: target.dataset.tier || null,
        designHash: target.dataset.design || null,
      });
      return;
    }
    const page = event.target?.closest?.("[data-res-page]");
    if (page && root.contains(page)) {
      const direction = page.dataset.resPage;
      if (state.scanned) {
        const max = Math.max(1, Math.ceil(visibleRows(state).length / PAGE_SIZE));
        state.localPage = Math.min(max, Math.max(1, state.localPage + (direction === "next" ? 1 : -1)));
        paintList();
      } else {
        const max = Math.max(1, Math.ceil((num(state.total) ?? 0) / PAGE_SIZE));
        const next = Math.min(max, Math.max(1, state.page + (direction === "next" ? 1 : -1)));
        if (next !== state.page) { state.page = next; await refreshHorns(); }
      }
      return;
    }
    const filter = event.target?.closest?.("[data-res-filter]");
    if (filter && root.contains(filter)) {
      state.filter = filter.dataset.resFilter || "all";
      state.localPage = 1;
      state.page = 1;
      paintList();
      if ((state.filter !== "all" || state.search.trim()) && !state.scanned) void ensureScan();
      return;
    }
    const scan = event.target?.closest?.("[data-res-scan]");
    if (scan && root.contains(scan)) { void ensureScan(); return; }
    const verify = event.target?.closest?.("[data-res-verify]");
    if (verify && root.contains(verify)) { await verifyDesign(verify.dataset.resVerify || ""); return; }
  }

  function input(event) {
    const field = event.target?.closest?.("[data-res-search]");
    if (!field || !root.contains(field)) return;
    state.search = field.value;
    state.localPage = 1;
    state.page = 1;
    state.focus = { key: "search", pos: field.selectionStart };
    paintList();
    if ((state.search.trim() || state.filter !== "all") && !state.scanned) {
      clearTimeout(state.scanTimer);
      state.scanTimer = setTimeout(() => { if (!disposed) void ensureScan(); }, 350);
    }
  }

  function change(event) {
    const sort = event.target?.closest?.("[data-res-sort]");
    if (sort && root.contains(sort)) {
      state.sort = sort.value || "best_j";
      state.page = 1;
      state.localPage = 1;
      if (state.sort === "verified_j") {
        // The endpoint cannot order by verify J; sort the full bounded scan locally.
        state.scanned = false;
        void ensureScan();
      } else if (state.scanned) {
        paintList();
      } else {
        void refreshHorns();
      }
      return;
    }
    const group = event.target?.closest?.("[data-res-group]");
    if (group && root.contains(group)) {
      state.group = group.checked === true;
      paintList();
    }
  }

  const submit = event => {
    if (event.target?.matches?.("[data-res-controls]")) event.preventDefault();
  };
  root.addEventListener("click", click);
  root.addEventListener("input", input);
  root.addEventListener("change", change);
  root.addEventListener("submit", submit);

  (async () => {
    if (!(await refreshStudy())) { draw(); return; }
    if (tab === "horns") await refreshHorns();
    else if (tab === "explore") await refreshExplore();
    else await refreshOverview();
  })().catch(error => { if (error?.name !== "AbortError") { state.error = "The Results workspace could not be loaded."; onError(error); draw(); } });

  if (Number.isFinite(pollMs) && pollMs > 0) {
    timer = setInterval(() => {
      if (disposed || state.busy) return;
      const running = ["running", "queued"].includes(state.study?.status);
      if (!running) return;
      if (tab === "horns") {
        // Keep a user's full scan/search result stable; a page-only poll would replace it.
        if (state.scanned || state.search.trim() || state.filter !== "all") return;
        void refreshHorns();
      } else if (tab === "explore") { void refreshExplore(); }
      else { void refreshOverview(); }
    }, Math.max(5000, pollMs));
  }

  return () => {
    disposed = true;
    state.op += 1;
    clearTimeout(state.scanTimer);
    controller?.abort();
    if (timer != null) clearInterval(timer);
    disposeViewers();
    try {
      root.removeEventListener("click", click);
      root.removeEventListener("input", input);
      root.removeEventListener("change", change);
      root.removeEventListener("submit", submit);
    } catch (_) { /* detached root */ }
  };
}
