// Study workspace. The host owns routes, HTTP protection and the concrete service API.
// This module consumes B4 StudyPanel models and never computes or ranks scores.
export const STUDY_PHASES = ["overview", "data", "explain", "propose", "execute", "decide"];
const PHASE_LABELS = {overview: "Overview", data: "Data", explain: "Explain", propose: "Propose", execute: "Run & Verify", decide: "Decide"};
const STATES = {
  missing: "Evidence is missing. Prepare the required input before continuing.",
  stale: "This evidence belongs to an older revision. Refresh it before continuing.",
  partial: "Evidence is partial. Review missing inputs before making a decision.",
  unknown: "The state is unknown. Reconcile the evidence or job before continuing.",
  dependency_missing: "A required dependency is unavailable. Install or configure the approved engine.",
  failed: "The operation failed. Inspect its diagnostics before retrying.",
  interrupted: "The job was interrupted. Reconcile its state before resuming.",
  no_data: "No compatible data is available. Select an evidenced cohort.",
  fit_failed: "Model fitting failed. Review diagnostics or use the labeled exploration fallback.",
  busy: "The requested lane is busy. Review the actual queue status.",
};
const ACTIONS = new Set(["save_draft", "select_evidence", "analyze", "propose", "package", "launch", "cancel", "decision", "save_seeds", "create_child"]);
const MUTATING_READY = new Set(["select_evidence", "analyze", "propose", "package", "launch", "decision", "save_seeds", "create_child"]);
const ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/;
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[c]));
const label = s => String(s).replace(/_/g, " ");

export function studyRoute(id, phase = "overview") {
  if (!ID.test(id) || !STUDY_PHASES.includes(phase)) throw new Error("Invalid study route");
  return `#/analysis/study/${encodeURIComponent(id)}/${phase}`;
}

// Only construct links to existing internal run/verify routes; never trust a provided URL.
export function studyRunLink(runId, studyId, phase = "execute", verify = false) {
  if (!ID.test(runId) || !ID.test(studyId) || !STUDY_PHASES.includes(phase)) return null;
  const back = studyRoute(studyId, phase);
  return `#/run/${encodeURIComponent(runId)}${verify ? "/verify" : ""}?${new URLSearchParams({return: back, study: studyId})}`;
}

function display(value, depth = 0) {
  if (value == null) return '<span class="muted">Unknown</span>';
  if (typeof value === "number") return Number.isFinite(value) ? esc(value) : '<span class="muted">Unknown</span>';
  if (typeof value === "boolean" || typeof value === "string") return esc(value);
  if (depth >= 5) return '<span class="muted">Details unavailable</span>';
  if (Array.isArray(value)) return value.length ? `<ul>${value.slice(0, 50).map(v => `<li>${display(v, depth + 1)}</li>`).join("")}</ul>` : '<span class="muted">None recorded</span>';
  if (typeof value === "object") return `<dl>${Object.entries(value).slice(0, 50).map(([k, v]) => `<dt>${esc(label(k))}</dt><dd>${display(v, depth + 1)}</dd>`).join("")}</dl>`;
  return '<span class="muted">Unknown</span>';
}

function renderLinks(data, studyId, phase) {
  const links = [];
  for (const [key, isVerify, text] of [["run_id", false, "Open run"], ["verify_run_id", true, "Open verification"]]) {
    const href = studyRunLink(data?.[key], studyId, phase, isVerify);
    if (href) links.push(`<a href="${esc(href)}">${text}</a>`);
  }
  return links.join(" · ");
}

function actionEnabled(action, panel, study) {
  if (!action || !ACTIONS.has(action.kind) || action.enabled !== true) return false;
  if (MUTATING_READY.has(action.kind) && panel.status !== "ready") return false;
  if (panel.revision !== study.revision) return false;
  if (action.kind === "launch" && (!action.package_hash || action.package_revision !== study.revision)) return false;
  if (action.kind === "cancel" && (!ID.test(action.job_id || "") || !["queued", "running"].includes(action.job_status))) return false;
  return true;
}

export function renderStudyPanel(study, panel, selected = null, notice = "") {
  if (!study || !ID.test(study.id || "") || !STUDY_PHASES.includes(panel?.phase)) throw new Error("Invalid study view");
  const phase = panel.phase;
  const stale = panel.revision !== study.revision;
  const status = stale ? "stale" : (panel.status || "unknown");
  const data = panel.data && typeof panel.data === "object" ? panel.data : {};
  const actions = Array.isArray(data.actions) ? data.actions.map((action, index) => ({action, index})).filter(x => x.action && ACTIONS.has(x.action.kind)) : [];
  const visibleData = Object.fromEntries(Object.entries(data).filter(([k]) => !["actions", "selected_horn"].includes(k)));
  const activePanel = {...panel, status};
  const tabs = STUDY_PHASES.map(p => `<a href="${esc(studyRoute(study.id, p))}"${p === phase ? ' aria-current="page"' : ""}>${esc(PHASE_LABELS[p])}</a>`).join(" · ");
  const actionHtml = actions.map(({action: a, index: i}) => {
    const inputs = a.kind === "decision" ? `<label>Decision <select data-study-field="outcome"><option value="inconclusive">Inconclusive</option><option value="accept">Accept</option><option value="reject">Reject</option></select></label><label>Rationale <textarea data-study-field="rationale" maxlength="4000"></textarea></label>` : a.kind === "save_draft" || a.kind === "create_child" ? `<label>Study question <input data-study-field="question" maxlength="500"></label>` : "";
    return `<div data-study-action-group="${i}">${inputs} <button type="button" data-study-action="${i}"${actionEnabled(a, activePanel, study) ? "" : " disabled"}>${esc(a.label || label(a.kind))}</button></div>`;
  }).join(" ");
  const selector = Array.isArray(data.candidates) ? data.candidates.slice(0, 50).map((c, i) => `<button type="button" data-study-select="${i}">${esc(c.label || c.id || `Candidate ${i + 1}`)}</button>`).join(" ") : "";
  return `<section class="study-workspace" aria-label="Study workspace"><header><p><a href="#/analysis">Analysis</a> / Studies</p><h1>${esc(study.name || study.question || study.spec?.question || "Study")}</h1><p>Revision ${esc(study.revision)} · ${esc(study.status || "unknown")} · ${esc(study.protocol || "bo-study-v1.1")}</p><nav aria-label="Study phases">${tabs}</nav></header>
  ${notice ? `<p role="alert">${esc(notice)}</p>` : ""}
  <p role="status"><strong>${esc(label(status))}</strong>${STATES[status] ? `: ${esc(STATES[status])}` : ""}</p>
  ${Array.isArray(panel.reasons) && panel.reasons.length ? display(panel.reasons) : ""}
  <div class="study-layout"><main><h2>${esc(PHASE_LABELS[phase])}</h2>${display(visibleData)}<h3>Provenance</h3>${display(panel.provenance || null)}${selector}<p>${renderLinks(data, study.id, phase)}</p></main>
  <aside aria-label="Selected horn"><h2>Selected horn</h2><p>Predicted, screen, and verified results are distinct.</p>${display(selected || data.selected_horn || null)}${renderLinks(selected, study.id, phase)}</aside></div>
  <section aria-label="Next action"><h2>Next action</h2>${actionHtml || '<p class="muted">No action is currently available.</p>'}</section>
  <p class="muted">Acquisition values are technical ranking diagnostics, not horn quality. No chart selection starts a solve.</p></section>`;
}

/** Mount against injected getStudy/getPanel/action adapters. Returns a disposal function.
 * getPanel returns B4 {phase,status,revision,data,provenance,reasons}; action receives
 * (studyId, kind, payload, {signal}). No URLs, argv or user code come from artifacts.
 */
export function mountStudy(root, {studyId, phase = "overview", api, pollMs = 5000, onError = () => {}}) {
  if (!root || !ID.test(studyId || "") || !STUDY_PHASES.includes(phase) || !api || typeof api.getStudy !== "function" || typeof api.getPanel !== "function") throw new Error("Invalid study mount");
  let disposed = false, controller = null, timer = null, generation = 0, busy = false;
  let study = null, panel = null, selected = null, notice = "", pendingKey = null;
  const makeKey = () => globalThis.crypto?.randomUUID?.() || `study-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const draw = () => { if (!disposed && study && panel) root.innerHTML = renderStudyPanel(study, panel, selected, notice); };
  async function refresh() {
    const current = ++generation;
    controller?.abort(); controller = new AbortController();
    try {
      const [nextStudy, nextPanel] = await Promise.all([api.getStudy(studyId, {signal: controller.signal}), api.getPanel(studyId, phase, {signal: controller.signal})]);
      if (disposed || current !== generation) return;
      if (study && study.revision !== nextStudy.revision) selected = null;
      study = nextStudy; panel = nextPanel; draw();
    } catch (error) {
      if (disposed || current !== generation || error?.name === "AbortError") return;
      notice = "Study data could not be loaded. Retry or inspect the service status."; onError(error); draw();
      if (!study || !panel) root.innerHTML = `<p role="alert">${esc(notice)}</p>`;
    }
  }
  async function click(event) {
    const target = event.target?.closest?.("[data-study-action], [data-study-select]");
    if (!target || !root.contains(target) || disposed || !panel || !study) return;
    if (target.dataset.studySelect != null) {
      selected = panel.data?.candidates?.[Number(target.dataset.studySelect)] || null; draw(); return;
    }
    const action = panel.data?.actions?.[Number(target.dataset.studyAction)];
    if (busy || !actionEnabled(action, panel, study) || typeof api.action !== "function") return;
    busy = true; target.disabled = true;
    const payload = {...(action.payload || {}), expected_revision: study.revision};
    const group = target.closest("[data-study-action-group]");
    for (const field of group?.querySelectorAll("[data-study-field]") || []) payload[field.dataset.studyField] = field.value;
    if (action.kind === "decision" && !String(payload.rationale || "").trim()) {
      notice = "Enter a rationale before recording a decision."; busy = false; draw(); return;
    }
    if (selected && typeof selected.id === "string" && ID.test(selected.id)) payload.selected_id = selected.id;
    if (action.kind === "launch") payload.package_hash = action.package_hash;
    if (action.kind === "cancel") payload.job_id = action.job_id;
    const fingerprint = JSON.stringify([action.kind, payload]);
    if (!pendingKey || pendingKey.fingerprint !== fingerprint) pendingKey = {fingerprint, key: makeKey()};
    payload.idempotency_key = pendingKey.key;
    const token = generation;
    try {
      await api.action(studyId, action.kind, payload, {signal: controller?.signal});
      if (disposed || token !== generation) return;
      pendingKey = null; notice = "Request recorded. Status will update from the registry."; await refresh();
    } catch (error) {
      if (disposed || error?.name === "AbortError") return;
      notice = error?.status === 409 ? "Study or job changed. Refresh before continuing." : "Request was not confirmed. Check job status before retrying.";
      onError(error); await refresh();
    } finally { busy = false; draw(); }
  }
  root.addEventListener("click", click);
  refresh();
  if (Number.isFinite(pollMs) && pollMs > 0) timer = setInterval(() => { if (!busy) refresh(); }, Math.max(1000, pollMs));
  return () => { disposed = true; generation++; controller?.abort(); if (timer != null) clearInterval(timer); root.removeEventListener("click", click); };
}

export function renderStudyList(studies, notice = "") {
  if (!Array.isArray(studies) || studies.length > 100) throw new Error("Invalid study list");
  const rows = studies.map(s => ID.test(s?.id || "") ? `<li><a href="${esc(studyRoute(s.id))}">${esc(s.name || s.question || s.id)}</a> · revision ${esc(s.revision ?? "unknown")} · ${esc(s.status || "draft")}</li>` : "").join("");
  return `<section aria-label="Studies"><h1>Studies</h1><p><a href="#/analysis">Analysis reports</a></p>${notice ? `<p role="alert">${esc(notice)}</p>` : ""}<h2>Existing studies</h2>${rows ? `<ul>${rows}</ul>` : "<p>No studies are available.</p>"}<h2>New draft</h2><form data-study-create><label>Study question <input name="question" maxlength="500" required></label> <button type="submit">Save draft</button></form></section>`;
}

/** List/create entry point. api.listStudies({signal}); api.createStudy({spec,key},{signal}). */
export function mountStudyList(root, {api, onError = () => {}, onCreated = () => {}}) {
  if (!root || !api || typeof api.listStudies !== "function") throw new Error("Invalid study list mount");
  const controller = new AbortController();
  let disposed = false, busy = false, list = [], notice = "", pending = null;
  const draw = () => { if (!disposed) root.innerHTML = renderStudyList(list, notice); };
  const load = async () => {
    try {
      const rows = await api.listStudies({signal: controller.signal});
      if (disposed) return;
      list = Array.isArray(rows) ? rows : rows.studies;
      if (!Array.isArray(list) || list.length > 100) throw new Error("Invalid study list");
      draw();
    } catch (error) {
      if (disposed || error?.name === "AbortError") return;
      notice = "Studies could not be loaded. Check the service status."; onError(error); draw();
    }
  };
  const submit = async event => {
    if (!event.target?.matches?.("[data-study-create]")) return;
    event.preventDefault();
    if (disposed || busy || typeof api.createStudy !== "function") return;
    const question = String(new FormData(event.target).get("question") || "").trim();
    if (!question || question.length > 500) { notice = "Enter a study question."; draw(); return; }
    busy = true;
    const button = event.target.querySelector("button"); if (button) button.disabled = true;
    if (!pending || pending.question !== question) pending = {question, key: globalThis.crypto?.randomUUID?.() || `draft-${Date.now()}-${Math.random().toString(36).slice(2)}`};
    try {
      const created = await api.createStudy({spec:{protocol:"bo-study-v1.1", question}, key:pending.key}, {signal:controller.signal});
      if (disposed) return;
      if (!ID.test(created?.id || "")) throw new Error("Invalid created study identity");
      pending = null; notice = "Draft saved."; await load(); if (!disposed) onCreated(created);
    } catch (error) {
      if (disposed || error?.name === "AbortError") return;
      notice = "Draft creation was not confirmed. Retry to check the same request."; onError(error); draw();
    } finally { busy = false; }
  };
  root.addEventListener("submit", submit); draw(); load();
  return () => { disposed = true; controller.abort(); root.removeEventListener("submit", submit); };
}
