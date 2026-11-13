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
const ACTIONS = new Set(["save_draft", "select_evidence", "analyze", "propose", "package", "launch", "cancel", "decision", "revise", "save_seeds", "create_child"]);
const MUTATING_READY = new Set(["select_evidence", "analyze", "propose", "package", "launch", "decision", "save_seeds", "create_child"]);
const ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/;
// RegExp.test coerces its argument, so ID.test(undefined) is true ("undefined"); identity
// checks must require a real string first.
const isId = value => typeof value === "string" && ID.test(value);
const SHA256 = /^[a-f0-9]{64}$/i;
const ARTIFACT_REF = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;
const POLICY_MODES = new Set(["scalar", "pareto", "cma_seed", "exploration"]);
// Frozen fallback labels; ``mode`` is the backend proposal-policy value.
const POLICY_FALLBACKS = [
  {id:"scalar", mode:"scalar", label:"scalar", requires:["training_set"], verification_mode:"scalar"},
  {id:"coverage-ripple", mode:"pareto", label:"coverage-ripple", requires:["cohort", "metric_observations"], verification_mode:"pareto"},
  {id:"cma-seed", mode:"cma_seed", label:"cma-seed", requires:["seeds"], verification_mode:"scalar"},
  {id:"exploration", mode:"exploration", label:"exploration", requires:["pool"], verification_mode:"scalar"},
];
const PROGRESS_KEYS = ["proposed", "started", "solved", "cached", "refused", "infeasible", "infrastructure_failed", "verified", "unknown"];
const UNAVAILABLE = new Set(["missing", "stale", "partial", "unknown", "dependency_missing", "failed", "interrupted", "unavailable", "capability_missing", "pool_exhausted", "no_data", "fit_failed", "busy"]);
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[c]));
const label = s => String(s).replace(/_/g, " ");

export function studyRoute(id, phase = "overview") {
  if (!isId(id) || !STUDY_PHASES.includes(phase)) throw new Error("Invalid study route");
  return `#/analysis/study/${encodeURIComponent(id)}/${phase}`;
}

// Only construct links to existing internal run/verify routes; never trust a provided URL.
export function studyRunLink(runId, studyId, phase = "execute", verify = false) {
  if (!isId(runId) || !isId(studyId) || !STUDY_PHASES.includes(phase)) return null;
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

function validPackageHash(value) {
  return typeof value === "string" && value.length > 0 && value.length <= 128 && !/[\\/]/.test(value);
}

function ownedCancel(action) {
  const jobOwned = ID.test(action.job_id || "") && ["queued", "running"].includes(action.job_status);
  const packageOwned = ID.test(action.package_id || "") && ["queued", "running"].includes(action.package_status || action.job_status);
  return jobOwned || packageOwned;
}

function policyCards(data) {
  const raw = Array.isArray(data?.policies) ? data.policies : null;
  if (!raw || raw.length === 0) return POLICY_FALLBACKS.map(card => ({...card, status:"unknown", reason:"Policy capabilities are not present in this panel.", available:false}));
  return raw.slice(0, 50).map(item => {
    if (!item || typeof item !== "object" || typeof item.id !== "string" || !item.id) return null;
    const status = typeof item.status === "string" ? item.status : "unknown";
    const reason = item.reason == null ? null : String(item.reason).slice(0, 1000);
    return {
      id: item.id,
      mode: typeof item.mode === "string" && item.mode ? item.mode : item.id,
      label: typeof item.label === "string" && item.label ? item.label : item.id,
      status,
      reason: status === "ready" ? reason : (reason || "Policy is unavailable; no reason was recorded."),
      requires: Array.isArray(item.requires) ? item.requires.filter(x => typeof x === "string").slice(0, 20) : [],
      verification_mode: typeof item.verification_mode === "string" ? item.verification_mode : null,
      available: status === "ready",
    };
  }).filter(Boolean);
}

function currentPolicyMode(study, data) {
  const mode = study?.spec?.policy?.mode ?? study?.spec?.policy?.proposal_policy ?? data?.current_policy ?? data?.policy?.mode ?? data?.policy_mode;
  return typeof mode === "string" && mode ? mode : null;
}

function selectedPolicyCard(study, data) {
  const mode = currentPolicyMode(study, data);
  if (!mode) return null;
  return policyCards(data).find(card => card.mode === mode || card.id === mode) || null;
}

function proposeBlocked(study, panel, data) {
  if (panel?.phase !== "propose") return false;
  const card = selectedPolicyCard(study, data);
  return !card || card.status !== "ready";
}

function actionEnabled(action, panel, study, data = null) {
  if (!action || !ACTIONS.has(action.kind) || action.enabled !== true) return false;
  if (MUTATING_READY.has(action.kind) && panel.status !== "ready") return false;
  if (panel.revision !== study.revision) return false;
  if (action.kind === "propose" && proposeBlocked(study, panel, data)) return false;
  if (action.kind === "launch" && (!validPackageHash(action.package_hash) || action.package_revision !== study.revision)) return false;
  if (action.kind === "cancel" && !ownedCancel(action)) return false;
  return true;
}

const safeText = (value, max = 1000) => String(value ?? "").slice(0, max);

function intervalCell(value, fallbackUnit = "") {
  if (value == null) return '<span class="muted">Unknown</span>';
  if (typeof value === "number") return Number.isFinite(value) ? `${esc(value)}${fallbackUnit ? ` ${esc(fallbackUnit)}` : ""}` : '<span class="muted">Unknown</span>';
  if (typeof value === "object") {
    const unit = value.unit != null ? safeText(value.unit, 32) : fallbackUnit;
    const point = value.value ?? value.mean ?? value.j ?? value.J;
    const lo = value.lower ?? value.lo ?? value.min;
    const hi = value.upper ?? value.hi ?? value.max;
    if (point != null && Number.isFinite(Number(point))) {
      const span = lo != null && hi != null && Number.isFinite(Number(lo)) && Number.isFinite(Number(hi)) ? ` [${esc(lo)}, ${esc(hi)}]` : "";
      return `${esc(point)}${span}${unit ? ` ${esc(unit)}` : ""}`;
    }
  }
  return display(value);
}

function candidateTable(data) {
  const rows = Array.isArray(data?.candidates) ? data.candidates.slice(0, 50) : [];
  if (!rows.length) return "";
  return `<section aria-label="Candidates"><h3>Candidate comparison</h3><p class="muted">Predicted values are model output, never measured screen results. Acquisition is a technical ranking diagnostic.</p><table><thead><tr><th>Candidate</th><th>Evidence</th><th>J</th><th>Physical</th><th>Selection reason</th><th>Feasibility</th><th>Nearest known</th></tr></thead><tbody>${rows.map((c, i) => {
    const measured = c?.measured === true || c?.status === "measured" || c?.evidence === "measured";
    const physical = c?.physical ?? (c?.coverage_deg != null || c?.ripple_db != null ? {coverage_deg:c?.coverage_deg, ripple_db:c?.ripple_db} : null);
    return `<tr data-study-candidate="${i}"><td>${esc(c?.label || c?.id || `Candidate ${i + 1}`)}</td><td>${measured ? '<span class="pill">Measured</span>' : '<span class="pill">Predicted</span>'}</td><td>${intervalCell(c?.j ?? c?.predicted_j ?? c?.J, "J")}</td><td>${display(physical)}</td><td>${esc(safeText(c?.selection_reason, 500))}</td><td>${display(c?.feasibility ?? c?.feasible ?? null)}</td><td>${display(c?.nearest_examples ?? c?.nearest ?? null)}</td></tr>`;
  }).join("")}</tbody></table></section>`;
}

function renderPolicySelector(study, panel, data, state) {
  if (panel.phase !== "propose") return "";
  const cards = policyCards(data);
  const current = currentPolicyMode(study, data);
  const selected = selectedPolicyCard(study, data);
  const disabled = state.busy || panel.revision !== study.revision;
  const buttons = cards.map(card => `<button type="button" data-study-policy="${esc(card.mode)}" aria-pressed="${selected && selected.mode === card.mode ? "true" : "false"}" title="${esc(card.reason || "")}"${disabled ? " disabled" : ""}>${esc(card.label)}${card.status !== "ready" ? ` (${esc(card.status)})` : ""}</button>`).join(" ");
  const capability = selected && selected.status !== "ready"
    ? `<section class="study-capability" role="status" data-study-policy-card><p><strong>${esc(label(selected.status))}</strong>: ${esc(selected.reason || "No reason was recorded.")}</p>${selected.requires.length ? `<p class="muted">Requires: ${selected.requires.map(r => esc(label(r))).join(", ")}</p>` : ""}</section>`
    : selected ? "" : '<p class="muted">No proposal policy is recorded in the current spec.</p>';
  return `<section aria-label="Proposal policy"><h3>Proposal policy</h3><p class="muted">Current spec policy: ${selected ? esc(selected.label) : '<span class="muted">not recorded</span>'}${selected?.verification_mode ? ` · verification ${esc(selected.verification_mode)}` : ""}</p><div role="group">${buttons}</div>${capability}</section>`;
}

function renderVerification(verification) {
  if (!verification) return "";
  const bits = [];
  if (verification.finalists != null) bits.push(`${esc(verification.finalists)} finalists`);
  if (verification.audits != null) bits.push(`${esc(verification.audits)} audits`);
  const heading = bits.length ? `Up to ${bits.join(" + ")}` : (verification.description || verification.mode || verification.policy || "Verification policy recorded");
  return `<h4>Verification policy</h4><p>${esc(safeText(heading, 500))}</p>${bits.length && verification.description ? `<p class="muted">${esc(safeText(verification.description, 500))}</p>` : ""}`;
}

function renderProgress(progress) {
  if (!progress) return "";
  const entries = PROGRESS_KEYS.filter(key => progress[key] != null);
  if (!entries.length) return "";
  return `<h4>Progress</h4><ul>${entries.map(key => `<li>${esc(label(key))}: ${esc(progress[key])}</li>`).join("")}</ul>`;
}

function renderExecute(data) {
  const packageData = data?.package && typeof data.package === "object" ? data.package : null;
  const packageHash = data?.package_hash ?? packageData?.hash ?? packageData?.package_hash ?? packageData?.sha256;
  const packageRevision = data?.package_revision ?? packageData?.revision;
  const lane = data?.lane ?? packageData?.lane;
  const deadline = data?.deadline ?? packageData?.deadline;
  const budget = data?.budget ?? packageData?.budget;
  const stop = data?.stop_recovery ?? data?.stop_rules ?? packageData?.stop_recovery ?? packageData?.stop_rules;
  const verification = data?.verification ?? data?.verification_policy ?? packageData?.verification ?? packageData?.verification_policy;
  const job = data?.job || (data?.job_status != null ? {id:data?.job_id, status:data?.job_status} : null);
  if (![packageHash, packageRevision, lane, deadline, budget, stop, verification, job, data?.progress].some(v => v != null)) return "";
  return `<section aria-label="Execution package"><h3>Run package</h3>${packageHash ? `<p>Package hash: <span class="mono">${esc(safeText(packageHash, 128))}</span>${packageRevision != null ? ` · revision ${esc(packageRevision)}` : ""}</p>` : ""}${lane != null || deadline != null ? `<p>${lane != null ? `Lane: ${esc(safeText(lane, 64))}` : ""}${lane != null && deadline != null ? " · " : ""}${deadline != null ? `Deadline: ${display(deadline)}` : ""}</p>` : ""}${budget != null ? `<h4>Budget</h4>${display(budget)}` : ""}${stop != null ? `<h4>Stop and recovery</h4>${display(stop)}` : ""}${renderVerification(verification)}${renderProgress(data?.progress)}${job ? `<h4>Job status</h4><p>${job.id ? `Job ${esc(safeText(job.id, 128))} · ` : ""}${esc(safeText(job.status || "unknown", 64))}</p>` : ""}</section>`;
}

function artifactChip(artifact) {
  if (artifact == null) return null;
  const key = typeof artifact === "string" ? artifact : (artifact.sha256 || artifact.kind || artifact.id);
  if (typeof key !== "string" || (!ARTIFACT_REF.test(key) && !SHA256.test(key))) return null;
  const text = typeof artifact === "string" ? artifact : (artifact.label || artifact.kind || (SHA256.test(key) ? `sha ${key.slice(0, 12)}…` : key));
  return `<button type="button" data-study-artifact="${esc(key)}">${esc(safeText(text, 120))}</button>`;
}

function renderArtifacts(data, state) {
  const links = (Array.isArray(data?.artifacts) ? data.artifacts.slice(0, 50) : []).map(artifactChip).filter(Boolean);
  const panel = state.artifact ? `<div data-study-artifact-panel>${display({status:state.artifact.status, reason:state.artifact.reason, kind:state.artifact.kind, sha256:state.artifact.sha256, revision:state.artifact.revision, data:state.artifact.data, provenance:state.artifact.provenance, reasons:state.artifact.reasons, metadata_only:state.artifact.metadata_only})}<p class="muted">Typed bounded panel; binary arrays are never loaded.</p></div>` : "";
  if (!links.length && !panel) return "";
  return `<section aria-label="Artifacts"><h3>Artifacts</h3>${links.length ? `<p>${links.join(" ")}</p>` : ""}${panel}</section>`;
}

export function renderStudyPanel(study, panel, selected = null, notice = "", state = {}) {
  if (!study || !ID.test(study.id || "") || !STUDY_PHASES.includes(panel?.phase)) throw new Error("Invalid study view");
  const phase = panel.phase;
  const stale = panel.revision !== study.revision;
  const status = stale ? "stale" : (panel.status || "unknown");
  const data = panel.data && typeof panel.data === "object" ? panel.data : {};
  const actions = Array.isArray(data.actions) ? data.actions.map((action, index) => ({action, index})).filter(x => x.action && ACTIONS.has(x.action.kind)) : [];
  const visibleData = Object.fromEntries(Object.entries(data).filter(([k]) => !["actions", "selected_horn", "policies", "candidates", "package", "budget", "lane", "deadline", "stop_recovery", "stop_rules", "verification", "verification_policy", "progress", "job", "job_id", "job_status", "package_hash", "package_revision", "artifacts"].includes(k)));
  const activePanel = {...panel, status};
  const renderState = {busy:state?.busy === true, artifact:state?.artifact || null};
  const tabs = STUDY_PHASES.map(p => `<a href="${esc(studyRoute(study.id, p))}"${p === phase ? ' aria-current="page"' : ""}>${esc(PHASE_LABELS[p])}</a>`).join(" · ");
  const actionHtml = actions.map(({action: a, index: i}) => {
    const inputs = a.kind === "decision" ? `<label>Decision <select data-study-field="outcome"><option value="inconclusive">Inconclusive</option><option value="accept">Accept</option><option value="reject">Reject</option></select></label><label>Rationale <textarea data-study-field="rationale" maxlength="4000"></textarea></label>` : a.kind === "save_draft" || a.kind === "create_child" ? `<label>Study question <input data-study-field="question" maxlength="500"></label>` : "";
    return `<div data-study-action-group="${i}">${inputs} <button type="button" data-study-action="${i}"${actionEnabled(a, activePanel, study, data) && !renderState.busy ? "" : " disabled"}>${esc(a.label || label(a.kind))}</button></div>`;
  }).join(" ");
  const selector = Array.isArray(data.candidates) ? data.candidates.slice(0, 50).map((c, i) => `<button type="button" data-study-select="${i}">${esc(c.label || c.id || `Candidate ${i + 1}`)}</button>`).join(" ") : "";
  const policyHtml = renderPolicySelector(study, activePanel, data, renderState);
  const candidateHtml = phase === "propose" ? candidateTable(data) : "";
  const executeHtml = phase === "execute" ? renderExecute(data) : "";
  const artifactHtml = phase === "decide" ? renderArtifacts(data, renderState) : "";
  return `<section class="study-workspace" aria-label="Study workspace"><header><p><a href="#/analysis">Analysis</a> / Studies</p><h1>${esc(study.name || study.question || study.spec?.question || "Study")}</h1><p>Revision ${esc(study.revision)} · ${esc(study.status || "unknown")} · ${esc(study.protocol || "bo-study-v1.1")}</p><nav aria-label="Study phases">${tabs}</nav></header>
  ${notice ? `<p role="alert">${esc(notice)}</p>` : ""}
  <p role="status"><strong>${esc(label(status))}</strong>${STATES[status] ? `: ${esc(STATES[status])}` : ""}</p>
  ${Array.isArray(panel.reasons) && panel.reasons.length ? display(panel.reasons) : ""}
  <div class="study-layout"><main><h2>${esc(PHASE_LABELS[phase])}</h2>${display(visibleData)}${executeHtml}${policyHtml}${candidateHtml}${artifactHtml}<h3>Provenance</h3>${display(panel.provenance || null)}${selector}<p>${renderLinks(data, study.id, phase)}</p></main>
  <aside aria-label="Selected horn"><h2>Selected horn</h2><p>Predicted, screen, and verified results are distinct.</p>${display(selected || data.selected_horn || null)}${renderLinks(selected, study.id, phase)}</aside></div>
  <section aria-label="Next action"><h2>Next action</h2>${actionHtml || '<p class="muted">No action is currently available.</p>'}</section>
  <p class="muted">Acquisition values are technical ranking diagnostics, not horn quality. No chart selection starts a solve.</p></section>`;
}

function sanitisePayload(raw) {
  const out = {};
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return out;
  for (const [key, value] of Object.entries(raw)) {
    if (!/^[a-z][a-z0-9_]{0,63}$/.test(key) || ["path", "argv", "command", "shell", "idempotency_key"].includes(key)) continue;
    if (value == null || ["string", "number", "boolean"].includes(typeof value)) out[key] = value;
    else if (Array.isArray(value) && value.length <= 20 && value.every(x => ["string", "number", "boolean"].includes(typeof x))) out[key] = value.slice(0, 20);
  }
  return out;
}

function actionFailure(error) {
  const status = Number(error?.status);
  if (status === 409) return "Study or job changed. Refresh before continuing.";
  if (status === 422 || status === 503) return `Unavailable: ${error?.message || "the requested prerequisite is not available."}`;
  return "Request was not confirmed. Check job status before retrying.";
}

/** Mount against injected getStudy/getPanel/action adapters. Returns a disposal function.
 * getPanel returns B4 {phase,status,revision,data,provenance,reasons}; action receives
 * (studyId, kind, payload, {signal}). No URLs, argv or user code come from artifacts.
 */
export function mountStudy(root, {studyId, phase = "overview", api, pollMs = 5000, onError = () => {}}) {
  if (!root || !ID.test(studyId || "") || !STUDY_PHASES.includes(phase) || !api || typeof api.getStudy !== "function" || typeof api.getPanel !== "function") throw new Error("Invalid study mount");
  let disposed = false, controller = null, timer = null, generation = 0, busy = false;
  let study = null, panel = null, selected = null, notice = "", pendingKey = null, artifact = null;
  const makeKey = () => globalThis.crypto?.randomUUID?.() || `study-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const draw = () => { if (!disposed && study && panel) root.innerHTML = renderStudyPanel(study, panel, selected, notice, {busy, artifact}); };
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
  async function loadArtifact(key) {
    if (typeof api.getArtifact !== "function" || (!ARTIFACT_REF.test(key) && !SHA256.test(key))) return;
    const token = generation;
    try {
      const next = await api.getArtifact(studyId, key, {signal: controller?.signal});
      if (disposed || token !== generation) return;
      artifact = next; draw();
    } catch (error) {
      if (disposed || error?.name === "AbortError") return;
      notice = "Artifact could not be loaded."; onError(error); draw();
    }
  }
  async function changePolicy(mode, target) {
    if (!POLICY_MODES.has(mode) || busy || !study || !panel) return;
    if (panel.revision !== study.revision || panel.status !== "ready") return;
    if (currentPolicyMode(study, panel.data) === mode) return;
    if (typeof api.action !== "function") return;
    busy = true; target.disabled = true; draw();
    const policy = {...(study.spec?.policy && typeof study.spec.policy === "object" ? study.spec.policy : {}), mode};
    const spec = {...(study.spec && typeof study.spec === "object" ? study.spec : {}), policy};
    const payload = {spec, expected_revision: study.revision};
    const fingerprint = JSON.stringify(["revise", mode, study.revision]);
    if (!pendingKey || pendingKey.fingerprint !== fingerprint) pendingKey = {fingerprint, key: makeKey()};
    payload.idempotency_key = pendingKey.key;
    const token = generation;
    try {
      await api.action(studyId, "revise", payload, {signal: controller?.signal});
      if (disposed || token !== generation) return;
      pendingKey = null; notice = "Proposal policy saved. Reloading the panel."; await refresh();
    } catch (error) {
      if (disposed || error?.name === "AbortError") return;
      notice = actionFailure(error); onError(error); await refresh();
    } finally { busy = false; draw(); }
  }
  async function click(event) {
    if (disposed) return;
    const artifactTarget = event.target?.closest?.("[data-study-artifact]");
    if (artifactTarget?.dataset?.studyArtifact != null && root.contains(artifactTarget)) { await loadArtifact(artifactTarget.dataset.studyArtifact); return; }
    const policyTarget = event.target?.closest?.("[data-study-policy]");
    if (policyTarget?.dataset?.studyPolicy != null && root.contains(policyTarget)) { await changePolicy(policyTarget.dataset.studyPolicy, policyTarget); return; }
    const target = event.target?.closest?.("[data-study-action], [data-study-select]");
    if (!target?.dataset || (target.dataset.studyAction == null && target.dataset.studySelect == null) || !root.contains(target) || !panel || !study) return;
    if (target.dataset.studySelect != null) {
      selected = panel.data?.candidates?.[Number(target.dataset.studySelect)] || null; draw(); return;
    }
    const action = panel.data?.actions?.[Number(target.dataset.studyAction)];
    if (busy || !actionEnabled(action, panel, study, panel.data) || typeof api.action !== "function") return;
    busy = true; target.disabled = true; draw();
    const payload = sanitisePayload(action.payload);
    payload.expected_revision = study.revision;
    const group = target.closest("[data-study-action-group]");
    for (const field of group?.querySelectorAll("[data-study-field]") || []) payload[field.dataset.studyField] = field.value;
    if (action.kind === "decision" && !String(payload.rationale || "").trim()) {
      notice = "Enter a rationale before recording a decision."; busy = false; draw(); return;
    }
    if (selected && typeof selected.id === "string" && ID.test(selected.id)) payload.selected_id = selected.id;
    if (action.kind === "launch") payload.package_hash = action.package_hash;
    if (action.kind === "cancel") {
      if (ID.test(action.job_id || "")) payload.job_id = action.job_id;
      if (ID.test(action.package_id || "")) payload.package_id = action.package_id;
      if (payload.job_id == null && payload.package_id == null) { busy = false; draw(); return; }
    }
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
      notice = actionFailure(error);
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
