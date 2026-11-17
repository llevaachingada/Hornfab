// Study workspace. The host owns routes, HTTP protection and the concrete service API.
// This module consumes B4 StudyPanel models and never computes or ranks scores.
export const STUDY_PHASES = ["overview", "data", "explain", "propose", "execute", "decide"];
// "live" is a view over the execute panel (same backend data), shown as a tab only when a package exists.
export const LIVE_PHASE = "live";
// P1 Results workspace: read-only review of the stored observations.  The three tabs share the
// existing `#/bayes/study/<id>` route family; the old authoring phases stay untouched.
export const RESULT_PHASES = ["results", "horns", "explore"];
const ROUTE_PHASES = [LIVE_PHASE, ...STUDY_PHASES, ...RESULT_PHASES];
const LIVE_POLL_MS = 10000;
const PHASE_LABELS = {live: "Live", overview: "Overview", data: "Data", explain: "Explain", propose: "Propose", execute: "Run & Verify", decide: "Decide", results: "Results", horns: "Horns", explore: "Explore"};
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
const ACTIONS = new Set(["save_draft", "select_evidence", "analyze", "propose", "diagnose", "package", "launch", "cancel", "decision", "revise", "save_seeds", "create_child", "queue_study", "solve_design"]);
const MUTATING_READY = new Set(["select_evidence", "analyze", "propose", "diagnose", "package", "launch", "decision", "save_seeds", "create_child"]);
const ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/;
// RegExp.test coerces its argument, so ID.test(undefined) is true ("undefined"); identity
// checks must require a real string first.
const isId = value => typeof value === "string" && ID.test(value);
const SHA256 = /^[a-f0-9]{64}$/i;
const ARTIFACT_REF = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;
const POLICY_MODES = new Set(["scalar", "turbo", "pareto", "cma_seed", "exploration"]);
// Frozen fallback labels; ``mode`` is the backend proposal-policy value.
const POLICY_FALLBACKS = [
  {id:"scalar", mode:"scalar", label:"scalar", requires:["training_set"], verification_mode:"scalar"},
  {id:"turbo", mode:"turbo", label:"scalar, trust region", requires:["training_set", "pool"], verification_mode:"scalar"},
  {id:"coverage-ripple", mode:"pareto", label:"coverage-ripple", requires:["cohort", "metric_observations"], verification_mode:"pareto"},
  {id:"cma-seed", mode:"cma_seed", label:"cma-seed", requires:["seeds"], verification_mode:"scalar"},
  {id:"exploration", mode:"exploration", label:"exploration", requires:["pool"], verification_mode:"scalar"},
];
// Plain-language strategy copy (handoff §4).  The backend status is still the source of truth.
const POLICY_COPY = {
  scalar: {
    title: "Best single score",
    summary: "Learns a map of J from everything solved so far, then solves the design most likely to beat the best. Every 4th pick explores somewhere new.",
    use: "Use when you want the best horn under the current brief.",
    success: "Best verify J improves and the model calibration holds.",
  },
  turbo: {
    title: "Polish the winner",
    summary: "Searches only a box around the current best. The box grows when it keeps improving and shrinks when it stops; a collapsed box means converged.",
    use: "Use after scalar has found a good region.",
    success: "Best verify J improves without the box collapsing too early.",
  },
  pareto: {
    title: "Show me the options",
    summary: "Ignores J's weights and finds the best coverage-vs-ripple balances, using a frozen reference box.",
    use: "Use when choosing what you want to hear rather than trusting the weights.",
    success: "New nondominated designs appear that the scalar arm did not find.",
  },
  cma_seed: {
    title: "Seed from CMA",
    summary: "Picks a candidate from an explicit CMA archive seed pack; no score model and no predictions.",
    use: "Use when a CMA archive already contains a promising basin.",
    success: "The seed verifies well and gives the study a head start.",
  },
  exploration: {
    title: "Explore the space",
    summary: "Chooses a maximin-diverse candidate from the legal pool. Labelled non-BO; no predictions.",
    use: "Use when there is no trustworthy model or you want a space-filling sample.",
    success: "The sample covers new geometry and feeds a later model.",
  },
};
const PROGRESS_KEYS = ["proposed", "started", "solved", "cached", "refused", "infeasible", "infrastructure_failed", "verified", "unknown"];
const UNAVAILABLE = new Set(["missing", "stale", "partial", "unknown", "dependency_missing", "failed", "interrupted", "unavailable", "capability_missing", "pool_exhausted", "no_data", "fit_failed", "busy"]);
const esc = value => String(value ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[c]));
const label = s => String(s).replace(/_/g, " ");

export function studyRoute(id, phase = "overview", rootId = null) {
  if (!isId(id) || !ROUTE_PHASES.includes(phase)) throw new Error("Invalid study route");
  if (rootId != null && !isId(rootId)) throw new Error("Invalid study root");
  const query = rootId ? `?${new URLSearchParams({root: rootId})}` : "";
  return `#/bayes/study/${encodeURIComponent(id)}/${phase}${query}`;
}

// True when a panel carries run-package evidence (server package flag, hash/revision, job or package object).
// ``package_present`` is authoritative on the first fetch, before the execute panel was ever visited.
export function hasPackageData(data) {
  if (!data || typeof data !== "object") return false;
  return data.package_present === true || data.package_hash != null || data.package_revision != null
    || (data.package !== null && typeof data.package === "object")
    || (data.job !== null && typeof data.job === "object") || data.job_id != null;
}

// Packages seen this session (per module instance); used to decide whether the Live tab shows.
const packagedStudies = new Set();

function studyIsRunning(study, data) {
  const running = ["running", "queued"];
  const jobStatus = data?.run_status?.status ?? data?.job_status ?? data?.job?.status;
  return running.includes(study?.status) || running.includes(jobStatus);
}

// Only construct links to existing internal run/verify routes; never trust a provided URL.
export function studyRunLink(runId, studyId, phase = "execute", verify = false, rootId = null) {
  if (!isId(runId) || !isId(studyId) || !STUDY_PHASES.includes(phase)) return null;
  if (rootId != null && !isId(rootId)) return null;
  const back = studyRoute(studyId, phase, rootId);
  const params = {return: back, study: studyId};
  if (rootId) params.root = rootId;
  return `#/run/${encodeURIComponent(runId)}${verify ? "/verify" : ""}?${new URLSearchParams(params)}`;
}

// A design drill-down through the existing balloon view (which owns a design selector).
export function studyDesignLink(runId, designHash, studyId, phase = "execute", rootId = null) {
  if (!isId(runId) || !isId(studyId) || !STUDY_PHASES.includes(phase)) return null;
  if (typeof designHash !== "string" || !/^[0-9a-f]{6,64}$/.test(designHash)) return null;
  const back = studyRoute(studyId, phase, rootId);
  const params = {design: designHash, return: back, study: studyId};
  if (rootId) params.root = rootId;
  return `#/run/${encodeURIComponent(runId)}/balloon?${new URLSearchParams(params)}`;
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

function renderLinks(data, studyId, phase, rootId = null) {
  const links = [];
  const runId = data?.run_id || data?.run?.run_id;
  const verifyRunId = data?.verify_run_id || data?.run?.verify_run_id;
  for (const [key, isVerify, text] of [[runId, false, "Open run"], [verifyRunId, true, "Open verification"]]) {
    const href = studyRunLink(key, studyId, phase, isVerify, rootId || data?.root || null);
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
  const mode = study?.spec?.policy?.proposal_policy ?? study?.spec?.policy?.mode ?? data?.current_policy ?? data?.policy?.mode ?? data?.policy_mode;
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
  if (MUTATING_READY.has(action.kind) && panel.status !== "ready" && !["analyze", "propose", "diagnose", "package", "launch", "decision", "create_child", "queue_study"].includes(action.kind)) return false;
  if (panel.status === "stale") return false;
  if (panel.revision !== study.revision) return false;
  if (action.kind === "propose" && proposeBlocked(study, panel, data)) return false;
    if (action.kind === "launch" && (!validPackageHash(action.package_hash) || action.package_revision !== study.revision)) return false;
    if (action.kind === "queue_study" && (!validPackageHash(action.package_hash) || action.package_revision !== study.revision)) return false;
  if (action.kind === "cancel" && !ownedCancel(action)) return false;
  return true;
}

const safeText = (value, max = 1000) => String(value ?? "").slice(0, max);

function intervalCell(value, fallbackUnit = "") {
  if (value == null) return '<span class="muted">Unknown</span>';
  if (typeof value === "number") return Number.isFinite(value) ? `${esc(value)}${fallbackUnit ? ` ${esc(fallbackUnit)}` : ""}` : '<span class="muted">Unknown</span>';
  if (typeof value === "object") {
    const unit = value.unit != null ? safeText(value.unit, 32) : fallbackUnit;
    const point = value.value ?? value.mean ?? value.j_mean ?? value.j ?? value.J;
    const lo = value.lower ?? value.j_lower ?? value.lo ?? value.min;
    const hi = value.upper ?? value.j_upper ?? value.hi ?? value.max;
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
  const buttons = cards.map(card => {
    const copy = POLICY_COPY[card.mode] || {};
    return `<button type="button" data-study-policy="${esc(card.mode)}" aria-pressed="${selected && selected.mode === card.mode ? "true" : "false"}" title="${esc(card.reason || copy.use || "")}"${disabled ? " disabled" : ""}>${esc(card.label)}${card.status !== "ready" ? ` (${esc(card.status)})` : ""}</button>`;
  }).join(" ");
  const copy = selected ? POLICY_COPY[selected.mode] : null;
  const capability = selected && selected.status !== "ready"
    ? `<section class="study-capability" role="status" data-study-policy-card><p><strong>${esc(label(selected.status))}</strong>: ${esc(selected.reason || "No reason was recorded.")}</p>${selected.requires.length ? `<p class="muted">Requires: ${selected.requires.map(r => esc(label(r))).join(", ")}</p>` : ""}</section>`
    : selected ? "" : '<p class="muted">No proposal policy is recorded in the current spec.</p>';
  const strategy = copy ? `<div class="study-strategy"><p><strong>${esc(copy.title)}</strong> ${esc(copy.summary)}</p><p class="muted">Use when: ${esc(copy.use)} Success looks like: ${esc(copy.success)}</p></div>` : "";
  return `<section aria-label="Proposal policy"><h3>Proposal policy</h3><p class="muted">Current spec policy: ${selected ? esc(selected.label) : '<span class="muted">not recorded</span>'}${selected?.verification_mode ? ` · verification ${esc(selected.verification_mode)}` : ""}</p><div role="group">${buttons}</div>${capability}${strategy}</section>`;
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
  const counts = data?.call_counts;
  const measuredProgress = data?.run_status || counts ? `<section aria-label="Measured study progress"><h3>Study execution</h3><p>Status: ${esc(data?.run_status?.cancelled ? "cancellation requested" : data?.run_status?.status || "not launched")}</p>${counts ? `<table><thead><tr><th>Screen solve calls</th><th>Verify solve calls</th><th>Total solve calls</th></tr></thead><tbody><tr><td>${esc(counts.screen_calls ?? 0)}</td><td>${esc(counts.verify_calls ?? 0)}</td><td>${esc(counts.total_calls ?? 0)}</td></tr></tbody></table><p class="muted">Counts are persisted backend calls. Cache hits and cheap refusals consume no solve calls.</p>` : ""}${renderProgress(data?.progress)}</section>` : "";
  if (![packageHash, packageRevision, lane, deadline, budget, stop, verification, job, data?.progress].some(v => v != null)) return "";
  return `${measuredProgress}<section aria-label="Execution package"><h3>Run package</h3>${packageHash ? `<p>Package hash: <span class="mono">${esc(safeText(packageHash, 128))}</span>${packageRevision != null ? ` · revision ${esc(packageRevision)}` : ""}</p>` : ""}${lane != null || deadline != null ? `<p>${lane != null ? `Lane: ${esc(safeText(lane, 64))}` : ""}${lane != null && deadline != null ? " · " : ""}${deadline != null ? `Deadline: ${display(deadline)}` : ""}</p>` : ""}${budget != null ? `<h4>Budget</h4>${display(budget)}` : ""}${stop != null ? `<h4>Stop and recovery</h4>${display(stop)}` : ""}${renderVerification(verification)}${!measuredProgress ? renderProgress(data?.progress) : ""}${job ? `<h4>Job status</h4><p>${job.id ? `Job ${esc(safeText(job.id, 128))} · ` : ""}${esc(safeText(job.status || "unknown", 64))}</p>` : ""}</section>`;
}

// A study has no `runs/<ts>-screen-*` folder; the results artifact's observations are its solve
// list.  A measured design can be re-solved into a real standalone verify run by the `solve_design`
// GPU action, and that run's 3D route already renders `designs/<hash>`.
function solve3dLink(runId) {
  return isId(runId) ? `#/run/${encodeURIComponent(runId)}/3d` : null;
}

function solveVerifyLink(runId) {
  return isId(runId) ? `#/run/${encodeURIComponent(runId)}/verify` : null;
}

function renderSolves(data, phase, study) {
  const solves = data?.solves && typeof data.solves === "object" ? data.solves : null;
  if (!solves) return "";
  // A bounded preview may append a "... N more items not shown" string; only real rows render.
  const rows = Array.isArray(solves.rows)
    ? solves.rows.filter(row => row && typeof row === "object").slice(0, 50) : [];
  const job = solves.job && typeof solves.job === "object" ? solves.job : null;
  const counts = `<p><span class="pill">${fmtNum(solves.n_total, 0)} observations</span> <span class="pill">${fmtNum(solves.n_measured, 0)} measured</span>${solves.n_refused != null ? ` <span class="pill warn">${fmtNum(solves.n_refused, 0)} refused</span>` : ""}</p>`;
  const heading = `<h3>Solves</h3><p class="muted">The study's own observations. "Solve in 3D" re-solves one measured design through the verified pipeline and opens its run views; it is one GPU solve.</p>`;
  if (!rows.length) {
    return `<section aria-label="Solves">${heading}${counts}<p class="muted">${esc(solves.reason || "No solves are listed yet.")}</p></section>`;
  }
  const body = rows.map((row, index) => {
    const hash = typeof row?.design_hash === "string" ? row.design_hash : "";
    const runLink = solve3dLink(row?.verify_run_id);
    const design = !hash ? "—" : runLink ? `<a class="mono" href="${esc(runLink)}">${esc(hash)}</a>` : `<span class="mono">${esc(hash)}</span>`;
    const physical = row?.physical === true;
    const disabled = !physical || !!job;
    const reason = !physical ? "This design has no physical measurement." : job ? `A solve is already active for ${job.design_hash || "another design"}.` : "";
    const action = hash ? `<button type="button" data-study-solve="${esc(hash)}"${disabled ? " disabled" : ""}${reason ? ` title="${esc(reason)}"` : ""}>Solve in 3D</button>` : "";
    const verify = solveVerifyLink(row?.verify_run_id);
    return `<tr data-study-solve-row="${index}"><td>${design}</td><td>${esc(row?.kind || "—")}</td><td class="r mono">${fmtNum(row?.j)}</td><td>${physical ? '<span class="pill good">measured</span>' : '<span class="pill warn">not physical</span>'}</td><td>${esc(row?.outcome || "—")}</td><td>${action}${verify ? ` <a href="${esc(verify)}">verify</a>` : ""}</td></tr>`;
  }).join("");
  return `<section aria-label="Solves">${heading}${counts}${job ? `<p class="muted">Solve running for <span class="mono">${esc(job.design_hash || "?")}</span> (${esc(job.status || "running")}).</p>` : ""}<div class="tbl-scroll"><table><thead><tr><th>Design</th><th>Kind</th><th class="r">J</th><th>Physical</th><th>Outcome</th><th>Action</th></tr></thead><tbody>${body}</tbody></table></div>${solves.truncated ? `<p class="muted">Showing the first ${fmtNum(rows.length, 0)} solves by J; the results artifact holds ${fmtNum(solves.n_total, 0)} observations.</p>` : ""}</section>`;
}

const fmtNum = (value, digits = 3) => {
  const number = Number(value);
  return value == null || !Number.isFinite(number) ? "—" :
    number.toLocaleString("en-US", {maximumFractionDigits: digits});
};

const fmtDuration = seconds => {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value < 0) return "—";
  if (value < 90) return `${Math.round(value)} s`;
  const minutes = Math.round(value / 60);
  if (minutes < 120) return `${minutes} min`;
  return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
};

function boStatusClass(status) {
  if (status === "ready") return "good";
  if (status === "partial") return "warn";
  if (status === "failed") return "bad";
  return "";
}

function boPanel(key, title, view, body = "") {
  if (!view || typeof view !== "object") return "";
  const status = view.status || "unknown";
  const reason = view.reason ? `<p class="muted">${esc(view.reason)}</p>` : "";
  const notes = (Array.isArray(view.notes) ? view.notes : []).filter(Boolean).slice(0, 6);
  return `<section class="bo-panel" data-bo-view="${esc(key)}"><div class="bo-head"><h3>${esc(title)}</h3><span class="pill ${boStatusClass(status)}">${esc(label(status))}</span></div>${reason}${body}${notes.length ? `<ul class="bo-notes">${notes.map(note => `<li>${esc(note)}</li>`).join("")}</ul>` : ""}</section>`;
}

function chartBlock(name, label) {
  return `<div class="study-chart"><svg data-study-chart="${esc(name)}" role="img" aria-label="${esc(label)}"></svg><div class="study-chart-legend"></div></div>`;
}

function renderRunStrip(run, convergence) {
  if (!run || !["ready", "partial"].includes(run.status)) return "";
  if (!run.run_id && !run.budget) return "";
  const budget = run.budget;
  const budgetText = budget ? `${fmtNum(budget.screen_calls, 0)} screens + ${fmtNum(budget.verify_calls, 0)} verify (${fmtNum(budget.total_calls, 0)} calls)` : "no budget recorded";
  const eta = convergence?.eta;
  const etaText = eta
    ? `Screen ${fmtDuration(eta.screen_seconds)} · verify ${fmtDuration(eta.verify_seconds)} remaining`
    : "ETA is unavailable until this run records solve times.";
  return boPanel("run", "Run budget and next solve", run,
    `<p>${budgetText}${run.budget_profile ? ` · profile <span class="mono">${esc(run.budget_profile)}</span>` : ""}${run.lane ? ` · lane ${esc(run.lane)}` : ""}</p><p class="muted">${esc(etaText)}</p>${run.deadline ? `<p class="muted">Deadline: <span class="mono">${esc(run.deadline)}</span></p>` : ""}`);
}

function renderConvergence(view) {
  if (!view) return "";
  const arms = Array.isArray(view.arms) ? view.arms : [];
  const rows = arms.map(arm => `<tr><td>${esc(arm.label || arm.id)}</td><td>${esc(arm.method || "—")}</td><td class="r mono">${fmtNum(arm.screens, 0)}</td><td class="r mono">${fmtNum(arm.best_j)}</td><td class="r mono">${fmtNum(arm.best_verify_j)}</td><td class="r mono">${arm.screens_to_target == null ? "—" : fmtNum(arm.screens_to_target, 0)}</td></tr>`).join("");
  const mixed = view.versions_mixed ? `<p class="alert warn" role="alert">These arms use different objective versions; J is not comparable across them.</p>` : "";
  const incumbent = view.incumbent ? `<p class="muted">Incumbent: J ${fmtNum(view.incumbent.j)}${view.incumbent.label ? ` · ${esc(view.incumbent.label)}` : ""}</p>` : "";
  return boPanel("convergence", "Convergence (best recorded J)", view,
    `${mixed}${chartBlock("convergence", "Best recorded J by solve index for each optimiser arm")}${incumbent}${rows ? `<div class="tbl-scroll"><table><thead><tr><th>Arm</th><th>Method</th><th class="r">Screens</th><th class="r">Best J</th><th class="r">Best verify J</th><th class="r">Screens to target</th></tr></thead><tbody>${rows}</tbody></table></div><p class="bo-scroll-hint">Scroll horizontally for all columns →</p>` : ""}<p class="muted">The line is best-so-far; individual solves outside the visible J range are omitted so the useful band stays readable. Screen J is reported but does not decide. Verify J is the comparison endpoint.</p>`);
}

function modelProvenanceHtml(prov) {
  if (!prov || typeof prov !== "object") return "";
  const bits = [];
  if (prov.retrospective === true) bits.push("retrospective refit");
  if (prov.retrospective === false) bits.push("recorded at proposal time");
  if (prov.model_revision != null) bits.push(`model revision ${prov.model_revision}`);
  if (prov.generated_utc) bits.push(String(prov.generated_utc));
  if (prov.artifact_sha256) bits.push(`sha ${String(prov.artifact_sha256).slice(0, 12)}…`);
  const note = prov.note ? ` — ${prov.note}` : "";
  return `<p class="muted">Model provenance: ${esc(bits.join(" · ") || "not recorded")}${esc(note)}</p>`;
}

function intervalEvidenceHtml(evidence, fallbackLabel = "model credible interval") {
  const ev = evidence && typeof evidence === "object" ? evidence : {};
  const supported = ev.calibrated_95_supported === true;
  const note = ev.note || (supported
    ? "The recorded evidence supports a calibrated 95 % interval."
    : `${fallbackLabel} is not presented as a calibrated 95 % interval unless the recorded evidence supports it.`);
  return `<p class="muted">${esc(note)}</p>`;
}

function renderSequentialValidation(seq) {
  const points = Array.isArray(seq.points) ? seq.points : [];
  const rows = points.slice(0, 50).map(point => `<tr><td class="mono">${esc(point.solve_id)}</td><td class="r mono">${fmtNum(point.predicted)}</td><td class="r mono">[${fmtNum(point.lower)}, ${fmtNum(point.upper)}]</td><td class="r mono">${fmtNum(point.measured)}</td><td>${point.inside ? '<span class="pill good">inside</span>' : '<span class="pill warn">outside</span>'}</td></tr>`).join("");
  const ev = seq.interval_evidence || {};
  const supported = ev.calibrated_95_supported === true;
  const coverage = seq.coverage_percent != null ? seq.coverage_percent : (seq.coverage != null ? seq.coverage * 100 : null);
  const chips = `<p><span class="pill">n ${fmtNum(seq.n, 0)}</span> <span class="pill">out of sample</span>${coverage != null ? ` <span class="pill">inside recorded interval ${fmtNum(coverage, 1)} %</span>` : ""}${seq.rank_correlation != null ? ` <span class="pill">rank ρ ${fmtNum(seq.rank_correlation, 3)}</span>` : ""}${supported ? ' <span class="pill good">calibrated 95 % supported</span>' : ""}</p>`;
  return `<h4>Sequential validation</h4><p class="muted">${esc(seq.label || "Proposals vs subsequently measured J")}</p>${chartBlock("calibration", "Predicted model J against measured screen J with the y equals x guide")}${chips}<p class="muted">${esc(seq.interval_label || "Model credible interval")}</p>${intervalEvidenceHtml(ev, seq.interval_label || "Model credible interval")}${rows ? `<div class="tbl-scroll"><table><thead><tr><th>Solve</th><th class="r">Predicted</th><th class="r">Interval</th><th class="r">Measured</th><th>Inside</th></tr></thead><tbody>${rows}</tbody></table></div><p class="bo-scroll-hint">Scroll horizontally for all columns →</p>` : ""}${modelProvenanceHtml(seq.model_provenance)}`;
}

function renderLoo(loo) {
  if (!loo) return "";
  if (loo.available !== true) {
    const ev = loo.interval_evidence || {};
    return `<h4>Efficient LOO on the training cohort</h4><p class="muted">${loo.can_compute ? "Not computed yet. Use “Compute model diagnostics” in the actions above." : "Not recorded."}</p>${intervalEvidenceHtml(ev, "The LOO interval")}${modelProvenanceHtml(loo.model_provenance)}`;
  }
  const sm = loo.summary && typeof loo.summary === "object" ? loo.summary : {};
  const ev = loo.interval_evidence || {};
  const supported = ev.calibrated_95_supported === true;
  const coverage = loo.coverage_95_percent != null ? loo.coverage_95_percent : (sm.coverage_95 != null ? sm.coverage_95 * 100 : null);
  const chips = `<p><span class="pill">n ${fmtNum(loo.n, 0)}${loo.truncated ? " (truncated)" : ""}</span>${coverage != null ? ` <span class="pill">inside ±2σ ${fmtNum(coverage, 1)} %</span>` : ""}${loo.rank_correlation != null ? ` <span class="pill">rank ρ ${fmtNum(loo.rank_correlation, 3)}</span>` : (sm.spearman != null ? ` <span class="pill">rank ρ ${fmtNum(sm.spearman, 3)}</span>` : "")}${sm.rmse != null ? ` <span class="pill">RMSE ${fmtNum(sm.rmse, 3)}</span>` : ""}${supported ? ' <span class="pill good">calibrated 95 % supported</span>' : ""}</p>`;
  return `<h4>Efficient LOO on the training cohort</h4><p class="muted">${esc(loo.label || "Leave-one-out on the original training cohort")}</p>${chartBlock("calibration_loo", "Leave-one-out predicted J against observed J with whiskers")}${chips}<p class="muted">${esc(loo.method || "Leave-one-out from the fitted model; no refit per row.")}</p>${intervalEvidenceHtml(ev, "The LOO interval")}${modelProvenanceHtml(loo.model_provenance)}`;
}

function renderCalibration(view) {
  if (!view) return "";
  const seq = view.sequential_validation && typeof view.sequential_validation === "object" ? view.sequential_validation : null;
  const loo = view.efficient_loo_cv && typeof view.efficient_loo_cv === "object" ? view.efficient_loo_cv : null;
  if (seq || loo) {
    return boPanel("calibration", "Model performance", view,
      `${seq ? renderSequentialValidation(seq) : ""}${renderLoo(loo || view.loo)}<p class="muted">These are two different checks and are not interchangeable: sequential validation tracks later proposals out of sample; efficient LOO is on the original training cohort with hyperparameters held fixed.</p>`);
  }
  const points = Array.isArray(view.points) ? view.points : [];
  const rows = points.slice(0, 50).map(point => `<tr><td class="mono">${esc(point.solve_id)}</td><td class="r mono">${fmtNum(point.predicted)}</td><td class="r mono">[${fmtNum(point.lower)}, ${fmtNum(point.upper)}]</td><td class="r mono">${fmtNum(point.measured)}</td><td>${point.inside ? '<span class="pill good">inside</span>' : '<span class="pill warn">outside</span>'}</td></tr>`).join("");
  const stats = `<p><span class="pill">n ${fmtNum(view.n, 0)}</span>${view.coverage != null ? ` <span class="pill">inside recorded interval ${fmtNum(view.coverage * 100, 1)} %</span>` : ""}${view.spearman != null ? ` <span class="pill">rank ρ ${fmtNum(view.spearman, 3)}</span>` : ""}</p>`;
  return boPanel("calibration", "Predicted vs measured J", view,
    `${chartBlock("calibration", "Predicted model J against measured screen J with the y equals x guide")}${stats}<p class="muted">${esc(view.interval_label || "Model credible interval")}</p>${rows ? `<div class="tbl-scroll"><table><thead><tr><th>Solve</th><th class="r">Predicted</th><th class="r">Interval</th><th class="r">Measured</th><th>Inside</th></tr></thead><tbody>${rows}</tbody></table></div><p class="bo-scroll-hint">Scroll horizontally for all columns →</p>` : ""}${renderLoo(view.loo)}`);
}

// Knob keys arrive as identifiers (throat_ext_angle_deg, az_a_cos_amp).  A slice caption reads
// like a knob name: words instead of underscores, with a trailing unit in brackets.  The unit is
// carried by the key suffix because the study space has no separate unit field.
const KNOB_UNITS = new Set(["mm", "cm", "m", "deg", "hz", "khz", "db", "ms"]);
function knobName(key) {
  const words = String(key ?? "").replace(/_+/g, " ").trim().split(/\s+/).filter(Boolean);
  if (!words.length) return "knob";
  let unit = "";
  if (words.length > 1 && KNOB_UNITS.has(words[words.length - 1].toLowerCase())) unit = words.pop();
  const body = words.join(" ");
  return unit ? `${body} (${unit})` : body;
}

function feasibilityWarningHtml(warning) {
  if (!warning || typeof warning !== "object") return "";
  const status = String(warning.status || "unknown");
  const cls = status === "warned" ? "warn" : status === "clear" ? "good" : "";
  const detail = warning.reason || (status === "unknown"
    ? "cheap feasibility was not evaluated for this slice; a 1-D slice can pass through geometrically invalid combinations"
    : "");
  return `<p class="muted"><span class="pill ${cls}">feasibility: ${esc(status)}</span>${warning.invalid_count != null ? ` · ${fmtNum(warning.invalid_count, 0)} invalid` : ""}${detail ? ` — ${esc(detail)}` : ""}</p>`;
}

function renderSlices(view) {
  const block = view.posterior_slices && typeof view.posterior_slices === "object" ? view.posterior_slices : null;
  const slices = Array.isArray(block?.items) ? block.items : (Array.isArray(view.slices) ? view.slices : []);
  if (!slices.length) {
    return view.diagnostics?.can_compute ? `<p class="muted">1-D model slices: not computed yet. Use “Compute model diagnostics” in the actions above.</p>` : "";
  }
  const labels = (block?.labels && typeof block.labels === "object" ? block.labels : {}) || (view.labels || {});
  const caveat = labels.caveat || "how strongly the model thinks J changes with each knob; a model belief, not a measurement";
  const anchor = labels.anchor || block?.other_knobs || "other knobs are held at the incumbent";
  // One name per small multiple: the figure caption.  The chart itself draws no second axis label.
  const cells = slices.map(item => {
    const name = knobName(item.key);
    const warning = item.feasibility_warning;
    const itemLabels = item.labels && typeof item.labels === "object" ? item.labels : {};
    const itemCaveat = itemLabels.caveat || caveat;
    const itemAnchor = itemLabels.anchor || anchor;
    return `<figure class="study-chart"><svg data-study-slice="${esc(item.key)}" role="img" aria-label="${esc(`Model J along ${name}; the shaded band is ±2σ around the model mean and the tick marks the incumbent`)}"></svg><figcaption class="bo-slice-label">${esc(name)}</figcaption>${feasibilityWarningHtml(warning)}<p class="muted">${esc(itemCaveat)}</p><p class="muted">${esc(itemAnchor)}</p></figure>`;
  }).join("");
  return `<h4>Model slices through the incumbent</h4><div class="bo-slices">${cells}</div><p class="muted">Line is the model mean, the shaded band is ±2σ, the vertical tick is the incumbent.</p>`;
}

function renderSensitivity(view) {
  if (!view) return "";
  const knobs = Array.isArray(view.knobs) ? view.knobs : [];
  const rows = knobs.map(knob => {
    const pct = Math.max(0, Math.min(100, Math.round((Number(knob.importance) || 0) * 100)));
    return `<div class="bo-bar-row"><span class="bo-bar-label mono">${esc(knob.key)}</span><div class="bo-bar-track" aria-hidden="true"><i style="width:${pct}%"></i></div><span class="bo-bar-value mono">${pct} %</span><span class="muted mono">ℓ ${fmtNum(knob.lengthscale, 3)}</span></div>`;
  }).join("");
  const caveat = view.labels?.knobs || view.posterior_slices?.labels?.caveat || "Relative knob sensitivity is 1/lengthscale, normalized; it describes the model, not a proven acoustic effect.";
  return boPanel("sensitivity", "How strongly J reacts to each knob", view,
    `<div class="bo-bars">${rows}</div><p class="muted">${esc(caveat)} Engine: ${esc(view.engine?.engine || "—")} ${esc(view.engine?.torch || "")}</p>${renderSlices(view)}`);
}

function renderTrustRegion(view) {
  if (!view) return "";
  const terminal = view.terminal && typeof view.terminal === "object" ? view.terminal : {};
  const terminalLabel = terminal.label || (terminal.collapsed === true ? "converged" : "active");
  const latest = `<p><span class="pill ${terminal.collapsed ? "good" : ""}">${esc(terminalLabel)}</span> ${esc(terminal.note || (terminal.collapsed ? "A collapsed box means local convergence; it is not necessarily global convergence." : "The trust region is still active."))}</p>`;
  const changes = Array.isArray(view.length_over_attempts) ? view.length_over_attempts.filter(step => step && step.change) : [];
  const changeChips = changes.slice(-12).map(step => `<span class="pill ${step.change === "expansion" ? "good" : "warn"}">${esc(step.change)} @ ${esc(fmtNum(step.proposal_index, 0))}</span>`).join(" ");
  const counters = `<p><span class="pill">L ${fmtNum(view.length_series?.at(-1)?.[1], 4)}</span> <span class="pill">successes ${fmtNum(view.success_counter, 0)}</span> <span class="pill">failures ${fmtNum(view.failure_counter, 0)}</span>${view.budget?.used != null ? ` <span class="pill">screens ${fmtNum(view.budget.used, 0)}${view.budget.total != null ? ` / ${fmtNum(view.budget.total, 0)}` : ""}</span>` : ""}${view.budget?.unspent != null ? ` <span class="pill">unspent ${fmtNum(view.budget.unspent, 0)}</span>` : ""}</p>`;
  const proposalCounts = `<p><span class="pill">inside ${fmtNum(view.proposals_inside, 0)}</span> <span class="pill">outside ${fmtNum(view.proposals_outside, 0)}</span>${view.proposals_unknown ? ` <span class="pill warn">unknown ${fmtNum(view.proposals_unknown, 0)}</span>` : ""}</p>`;
  const expansion = Array.isArray(view.expansion_steps) ? view.expansion_steps : [];
  const shrink = Array.isArray(view.shrink_steps) ? view.shrink_steps : [];
  const stepText = (expansion.length || shrink.length)
    ? `<p class="muted"><span class="pill good">${fmtNum(expansion.length, 0)} expansions</span> <span class="pill warn">${fmtNum(shrink.length, 0)} shrinks</span>${changeChips ? ` ${changeChips}` : ""}</p>` : "";
  const center = view.center_identity && typeof view.center_identity === "object" ? view.center_identity : null;
  const centerHtml = center
    ? `<p class="muted">Centre identity: ${center.resolved
      ? `<span class="mono">${esc(center.design_hash || center.id || "—")}</span>${center.geometry_hash ? ` · geometry <span class="mono">${esc(center.geometry_hash)}</span>` : ""}${center.distance_l2 != null ? ` · distance ${fmtNum(center.distance_l2, 4)}` : ""}`
      : esc(center.status || "not resolved against a training row")}</p>`
    : "";
  const bounds = Array.isArray(view.normalized_parameter_bounds) ? view.normalized_parameter_bounds : [];
  const bars = bounds.length ? bounds.map(item => {
    const lo = Number(item.lo), hi = Number(item.hi);
    if (!Number.isFinite(lo) || !Number.isFinite(hi)) return "";
    const left = Math.max(0, Math.min(1, lo)) * 100;
    const width = Math.max(0, Math.min(1, hi) - Math.min(1, lo)) * 100;
    return `<div class="bo-bar-row"><span class="bo-bar-label mono">${esc(item.key)}</span><div class="bo-box-track" aria-hidden="true"><i style="left:${left}%;width:${width}%"></i></div><span class="bo-bar-value mono">${fmtNum(lo, 2)}–${fmtNum(hi, 2)}</span><span class="muted mono">${esc(item.space || "normalized")}</span></div>`;
  }).join("") : (view.box && Array.isArray(view.box.lo) && Array.isArray(view.box.hi) ? view.box.lo.map((lo, index) => {
    const hi = Number(view.box.hi[index]);
    const left = Math.max(0, Math.min(1, Number(lo))) * 100;
    const width = Math.max(0, Math.min(1, hi) - Math.min(1, Number(lo))) * 100;
    return `<div class="bo-bar-row"><span class="bo-bar-label mono">${esc(Array.isArray(view.active_keys) ? view.active_keys[index] : `knob_${index + 1}`)}</span><div class="bo-box-track" aria-hidden="true"><i style="left:${left}%;width:${width}%"></i></div><span class="bo-bar-value mono">${fmtNum(lo, 2)}–${fmtNum(hi, 2)}</span></div>`;
  }).join("") : "");
  return boPanel("trust_region", "Trust region (TuRBO)", view,
    `${chartBlock("trust_region", "Trust-region length over proposals, with the collapse floor and maximum")}${latest}${counters}${proposalCounts}${stepText}${centerHtml}${bars ? `<div class="bo-bars">${bars}</div>` : ""}<p class="muted">A collapsed box means the local search has converged; it is not necessarily global convergence. Unspent budget stays visible.</p>`);
}

// The diagnostics artifact's pareto block lists its front by training-row id.  A Pareto row
// carries that id as ``observation_id``; ``design_hash`` is a shorter, independent id in the
// shipped payload, so matching only on it would mark nothing.  Match either identity, exactly,
// and never fabricate a member.
function paretoFrontIds(diag) {
  const ids = Array.isArray(diag?.front_ids) ? diag.front_ids.filter(id => typeof id === "string" && id) : [];
  return ids.length ? new Set(ids) : null;
}
const onDiagnosticsFront = (point, front) => !!front
  && [point?.observation_id, point?.design_hash].some(id => typeof id === "string" && id && front.has(id));

// ``hv_trace`` is [[training_row, prefix_hypervolume], ...]; a bounded-panel marker can sit in the
// list, so every row is type-checked (null or a string is rejected, never coerced to 0).  Two
// readable rows are the minimum for a line.
function diagnosticsHvTrace(diag) {
  const rows = (Array.isArray(diag?.hv_trace) ? diag.hv_trace : [])
    .filter(row => Array.isArray(row)
      && typeof row[0] === "number" && Number.isFinite(row[0])
      && typeof row[1] === "number" && Number.isFinite(row[1]))
    .map(row => [row[0], row[1]]);
  return rows.length >= 2 ? rows : [];
}

/** Model-diagnostics half of the Pareto card: front size, then the hypervolume trace. */
function renderParetoDiagnostics(diag, front, trace) {
  if ((!diag || diag.available !== true) && !trace.length) return "";
  const nFront = front ? front.size : null;
  const rowsSeen = trace.length ? trace[trace.length - 1][0] : null;
  const summary = nFront == null ? "" :
    `<p><span class="pill">model diagnostics front</span> ${esc(fmtNum(nFront, 0))} design${nFront === 1 ? "" : "s"}${rowsSeen == null ? "" : ` across the ${esc(fmtNum(rowsSeen, 0))} training rows the diagnostics job used`}. <span class="muted">The table below is the measured nondominated set, a separate front.</span></p>`;
  const hv = trace.length
    ? `${chartBlock("pareto_hv", "Prefix hypervolume of the diagnostics training rows against training-row order")}<p class="muted">Bottom axis: training-row order (k). Up axis: hypervolume of the first k rows. The value only moves up on a row that adds hypervolume, so a flat stretch means that row added none.</p>`
    : "";
  return `${summary}${hv}`;
}

function renderPareto(view, study, phase, rootId) {
  if (!view) return "";
  const reference = view.reference || {};
  const limits = reference.limits || [];
  const axes = view.frontier_axes && typeof view.frontier_axes === "object" ? view.frontier_axes : {};
  const xUnit = axes.units?.[0] || "deg";
  const yUnit = axes.units?.[1] || "dB";
  const points = Array.isArray(view.nondominated) && view.nondominated.length
    ? view.nondominated
    : (Array.isArray(view.points) ? view.points : []).filter(point => point.nondominated);
  const excluded = Array.isArray(view.excluded_points) ? view.excluded_points : [];
  const predicted = Array.isArray(view.predicted) ? view.predicted : [];
  const diag = view.diagnostics && typeof view.diagnostics === "object" ? view.diagnostics : null;
  const diagnosticsOn = diag?.available === true;
  const front = diagnosticsOn ? paretoFrontIds(diag) : null;
  const trace = diagnosticsOn ? diagnosticsHvTrace(diag) : [];
  const hvTrace = trace.length ? trace : (Array.isArray(view.hypervolume_trace) ? diagnosticsHvTrace({hv_trace: view.hypervolume_trace}) : []);
  const rows = points.slice(0, 50).map(point => {
    const link = studyDesignLink(view.run_id || view.run?.run_id || "", point.design_hash, study.id, phase, rootId || study.root);
    const design = point.design_hash ? (link ? `<a class="mono" href="${esc(link)}">${esc(point.design_hash)}</a>` : `<span class="mono">${esc(point.design_hash)}</span>`) : "—";
    const onFront = onDiagnosticsFront(point, front) ? ' <span class="pill">model front</span>' : "";
    return `<tr><td>${design}${onFront}</td><td class="r mono">${fmtNum(point.coverage_deg, 3)}</td><td class="r mono">${fmtNum(point.ripple_db, 3)}</td><td class="r mono">${fmtNum(point.j)}</td><td>${point.finalist ? '<span class="pill good">finalist</span>' : ""}</td></tr>`;
  }).join("");
  const excludedRows = excluded.slice(0, 25).map(point => `<tr><td class="mono">${esc(point.observation_id || "—")}</td><td>${esc(point.status || "not recorded")}</td><td class="r mono">${fmtNum(point.coverage_deg, 3)}</td><td class="r mono">${fmtNum(point.ripple_db, 3)}</td><td class="muted">${esc(point.reason || "—")}</td></tr>`).join("");
  const predictedRows = predicted.slice(0, 25).map(point => {
    const cov = point.coverage_deg && typeof point.coverage_deg === "object" ? point.coverage_deg : {};
    const rip = point.ripple_db && typeof point.ripple_db === "object" ? point.ripple_db : {};
    return `<tr><td class="mono">${esc(point.design_hash || "—")}</td><td class="r mono">${fmtNum(cov.mean, 3)}</td><td class="r mono">${fmtNum(rip.mean, 3)}</td><td><span class="pill warn">model prediction, not measured</span></td></tr>`;
  }).join("");
  const metrics = `<p>${view.hypervolume != null ? `<span class="pill">hypervolume ${fmtNum(view.hypervolume, 4)}</span>` : ""} ${limits.length === 2 ? `<span class="pill">reference ${fmtNum(limits[0])} ${esc(xUnit)} × ${fmtNum(limits[1])} ${esc(yUnit)}</span>` : ""} ${view.n_complete != null ? `<span class="pill">complete ${fmtNum(view.n_complete, 0)}</span>` : ""}${view.n_excluded ? ` <span class="pill warn">excluded ${fmtNum(view.n_excluded, 0)}</span>` : ""}</p>`;
  const axesNote = `<p class="muted">Frontier axes: ${esc(axes.note || `coverage (${xUnit}) × ripple (${yUnit}); J is a per-point scalar, never an axis.`)}</p>`;
  const diagnostics = (diagnosticsOn || hvTrace.length) ? renderParetoDiagnostics(diag, front, hvTrace) : "";
  return boPanel("pareto", "Coverage × ripple frontier", view,
    `${chartBlock("pareto", `Measured coverage error (${xUnit}) against ripple (${yUnit}); nondominated, excluded and predicted points are separate marks`)}${metrics}${axesNote}${diagnostics}${rows ? `<div class="tbl-scroll"><table><thead><tr><th>Design</th><th class="r">Coverage (${esc(xUnit)})</th><th class="r">Ripple (${esc(yUnit)})</th><th class="r">J</th><th>Verify</th></tr></thead><tbody>${rows}</tbody></table></div><p class="bo-scroll-hint">Scroll horizontally for all columns →</p>` : ""}${excludedRows ? `<details class="an-details"><summary>Excluded points (${fmtNum(excluded.length, 0)})</summary><div class="tbl-scroll"><table><thead><tr><th>Observation</th><th>Status</th><th class="r">Coverage</th><th class="r">Ripple</th><th>Reason</th></tr></thead><tbody>${excludedRows}</tbody></table></div></details>` : ""}${predictedRows ? `<details class="an-details"><summary>Predicted points (${fmtNum(predicted.length, 0)}) — not measured</summary><div class="tbl-scroll"><table><thead><tr><th>Design</th><th class="r">Coverage mean</th><th class="r">Ripple mean</th><th>Evidence</th></tr></thead><tbody>${predictedRows}</tbody></table></div></details>` : ""}<p class="muted">Coverage is plain physical coverage error (owner decision 2026-11-15); J is shown beside it. Training uses frontier/crowding; rows beyond the frozen reference still train but add no hypervolume. Predicted points are never plotted as measured.</p>`);
}

function renderDesignSpace(view) {
  if (!view) return "";
  const explained = Array.isArray(view.explained) ? view.explained : [];
  return boPanel("design_space", "Design-space map", view,
    `${chartBlock("design_space", "Two-dimensional projection of training and proposed designs")}<p class="muted">2-D PCA of encoded design vectors${explained.length ? `; components explain ${explained.map(value => `${fmtNum(value * 100, 1)} %`).join(" / ")}` : ""}. Axes are not acoustic.</p>`);
}

function renderDataSummary(view) {
  if (!view) return "";
  const training = view.training || {};
  const source = training.sources || {};
  const sourceBits = Object.entries(source).map(([key, value]) => `<li>${esc(label(key))}: <span class="mono">${esc(value)}</span></li>`).join("");
  const keys = Array.isArray(training.active_keys) ? training.active_keys : [];
  return boPanel("data_summary", "Training data", view,
    `<p><span class="pill">n ${fmtNum(training.n, 0)}</span> <span class="pill">minimum ${fmtNum(training.n_min, 0)}</span>${training.n_eligible != null ? ` <span class="pill">eligible ${fmtNum(training.n_eligible, 0)}</span>` : ""}${view.objective_version != null ? ` <span class="pill">objective v${esc(view.objective_version)}</span>` : ""}${training.excluded_ids ? ` <span class="pill warn">excluded ${fmtNum(training.excluded_ids, 0)}</span>` : ""}</p>${keys.length ? `<p class="muted">Knobs: ${keys.map(key => `<span class="mono">${esc(key)}</span>`).join(", ")}</p>` : ""}${training.subset_policy ? `<p class="muted">Subset: ${esc(training.subset_policy)}</p>` : ""}${sourceBits ? `<ul class="bo-notes">${sourceBits}</ul>` : ""}`);
}

function renderTargetIntegrity(view) {
  if (!view) return "";
  const available = view.scoring_target_available === true;
  const identity = view.target_identity && typeof view.target_identity === "object" ? view.target_identity : {};
  const target = view.target && typeof view.target === "object" ? view.target : null;
  const labels = view.labels && typeof view.labels === "object" ? view.labels : {};
  const identityBits = [
    identity.objective_version != null ? `objective v${esc(identity.objective_version)}` : null,
    identity.brief_name ? `brief ${esc(identity.brief_name)}` : null,
    identity.config_name ? `config ${esc(identity.config_name)}` : null,
  ].filter(Boolean);
  const targetRows = target
    ? Object.entries(target).filter(([, value]) => value != null)
      .slice(0, 40)
      .map(([key, value]) => `<dt>${esc(label(key))}</dt><dd class="mono">${esc(typeof value === "object" ? JSON.stringify(value).slice(0, 200) : value)}</dd>`).join("")
    : "";
  const legend = [
    labels.target ? `<span class="pill">target: ${esc(labels.target)}</span>` : "",
    labels.measured ? `<span class="pill">measured: ${esc(labels.measured)}</span>` : "",
    labels.tolerance ? `<span class="pill">tolerance: ${esc(labels.tolerance)}</span>` : "",
  ].filter(Boolean).join(" ");
  return boPanel("target_integrity", "Scoring target integrity", view,
    `${available ? "" : '<p class="alert warn"><strong>scoring target unavailable</strong></p>'}<p class="muted">${esc(view.source || (available ? "recorded scorer target" : "no recorded scoring target; it is not derived from the typology name"))}</p>${identityBits.length ? `<p class="muted">${identityBits.join(" · ")}</p>` : ""}${available && targetRows ? `<dl class="bo-artifact-dl">${targetRows}</dl>` : ""}${available ? `<p class="muted">${esc(view.separate_from_measurements ? "Target curves are kept separate from measured curves." : "Target and measured values are separate; they are never merged.")}</p>` : ""}${legend ? `<p class="bo-tag-row">${legend}</p>` : ""}${view.note ? `<p class="muted">${esc(view.note)}</p>` : ""}`);
}

function statusKindsHtml(statusKinds) {
  if (!statusKinds || typeof statusKinds !== "object") return "";
  const physical = statusKinds.physical && typeof statusKinds.physical === "object"
    ? (statusKinds.physical.summary || JSON.stringify(statusKinds.physical).slice(0, 160))
    : statusKinds.physical;
  const labels = statusKinds.labels && typeof statusKinds.labels === "object" ? statusKinds.labels : {};
  const bits = [
    statusKinds.analysis != null ? `<span class="pill">analysis: ${esc(label(String(statusKinds.analysis)))}</span>` : "",
    statusKinds.artifact_validation != null ? `<span class="pill">artifact validation: ${esc(label(String(statusKinds.artifact_validation)))}</span>` : "",
    physical != null ? `<span class="pill">physical: ${esc(String(physical))}</span>` : "",
  ].filter(Boolean);
  if (!bits.length) return "";
  return `<p class="bo-tag-row" title="${esc(Object.values(labels).join(" · "))}">${bits.join(" ")}</p>`;
}

function renderProposalExplanation(view) {
  if (!view) return "";
  const acq = view.acquisition && typeof view.acquisition === "object" ? view.acquisition : {};
  const predicted = view.predicted && typeof view.predicted === "object" ? view.predicted : null;
  const nearest = view.nearest_training_designs && typeof view.nearest_training_designs === "object" ? view.nearest_training_designs : {};
  const nearestRows = Array.isArray(nearest.items) ? nearest.items.slice(0, 6).map(item => `<tr><td class="mono">${esc(item.id || item.design_hash || "—")}</td><td class="r mono">${fmtNum(item.distance_l2, 5)}</td><td class="r mono">${fmtNum(item.j)}</td><td class="mono">${esc(item.design_hash || "—")}</td></tr>`).join("") : "";
  const delta = view.parameter_delta_vs_incumbent && typeof view.parameter_delta_vs_incumbent === "object" ? view.parameter_delta_vs_incumbent : {};
  const deltaRows = Array.isArray(delta.items) ? delta.items.slice(0, 20).map(item => `<tr><td class="mono">${esc(item.key)}</td><td class="r mono">${fmtNum(item.incumbent, 4)}</td><td class="r mono">${fmtNum(item.candidate, 4)}</td><td class="r mono">${fmtNum(item.delta, 4)}</td></tr>`).join("") : "";
  const checks = view.cheap_check_feasibility && typeof view.cheap_check_feasibility === "object" ? view.cheap_check_feasibility : {};
  const checkBits = checks.checks && typeof checks.checks === "object"
    ? Object.entries(checks.checks).map(([key, value]) => `<span class="pill ${value === true ? "good" : value === false ? "warn" : ""}">${esc(label(key))}: ${esc(value === true ? "ok" : value === false ? "failed" : String(value))}</span>`).join(" ") : esc(checks.status || "not recorded");
  const model = view.model_version && typeof view.model_version === "object" ? view.model_version : {};
  const modelBits = [
    model.status ? `status ${model.status}` : null,
    model.policy ? `policy ${model.policy}` : null,
    model.generated_utc ? String(model.generated_utc) : null,
    model.artifact_sha256 ? `sha ${String(model.artifact_sha256).slice(0, 12)}…` : null,
    model.hyperparameters_recorded === true ? "hyperparameters recorded" : null,
  ].filter(Boolean);
  const predictedHtml = predicted
    ? `<p><span class="pill">model credible interval</span> ${fmtNum(predicted.j_mean)}${predicted.j_lower != null && predicted.j_upper != null ? ` [${fmtNum(predicted.j_lower)}, ${fmtNum(predicted.j_upper)}]` : ""}${predicted.interval_label ? ` · ${esc(predicted.interval_label)}` : ""}</p><p class="muted">Predicted J is model output, never a measured result.</p>`
    : `<p class="muted">Predicted J: ${esc(typeof view.predicted === "string" ? view.predicted : "not recorded")}</p>`;
  return boPanel("proposal_explanation", "Why this candidate was proposed", view,
    `${statusKindsHtml(view.status_kinds)}<p><span class="pill">policy ${esc(view.policy || "—")}</span> <span class="pill">proposal ${esc(view.proposal_index ?? "—")}</span><span class="pill ${view.designation === "fallback" ? "warn" : ""}">${esc(view.designation || "not recorded")}</span>${view.fallback === true ? ' <span class="pill warn">fallback</span>' : ""}</p>
    <p class="muted">${esc(view.selection_reason || "Selection reason not recorded")}</p>
    ${predictedHtml}
    ${acq.value != null || acq.rank != null ? `<p><span class="pill">acquisition ${acq.value != null ? fmtNum(acq.value) : "—"}${acq.units ? ` ${esc(acq.units)}` : ""}</span>${acq.rank != null ? ` <span class="pill">rank ${fmtNum(acq.rank, 0)}</span>` : ""}${acq.is_ranking_signal ? ' <span class="pill warn">ranking signal only</span>' : ""}</p><p class="muted">${esc(acq.meaning || "Acquisition values are ranking signals, not probabilities or measured horn quality.")}</p>` : ""}
    ${modelBits.length ? `<p class="muted">Model: ${modelBits.map(esc).join(" · ")}</p>` : ""}
    ${modelProvenanceHtml(view.model_provenance)}
    <p class="muted">Cheap checks: ${checkBits}${checks.note ? ` — ${esc(checks.note)}` : ""}</p>
    ${nearestRows ? `<h4>Nearest training designs</h4><div class="tbl-scroll"><table><thead><tr><th>Training id</th><th class="r">Distance (L2)</th><th class="r">J</th><th>Design hash</th></tr></thead><tbody>${nearestRows}</tbody></table></div>` : `<p class="muted">Nearest training designs: ${esc(nearest.reason || nearest.status || "not recorded")}</p>`}
    ${deltaRows ? `<h4>Parameter delta vs incumbent</h4><div class="tbl-scroll"><table><thead><tr><th>Knob</th><th class="r">Incumbent</th><th class="r">Candidate</th><th class="r">Delta</th></tr></thead><tbody>${deltaRows}</tbody></table></div><p class="bo-scroll-hint">Scroll horizontally for all columns →</p>` : ""}
    ${view.active_vector_delta_vs_incumbent?.available === true ? `<p class="muted">Active-space distance to incumbent: ${fmtNum(view.active_vector_delta_vs_incumbent.distance_l2, 5)}</p>` : ""}`);
}

function renderBoVerification(view) {
  if (!view) return "";
  const finalists = Array.isArray(view.finalists) ? view.finalists : [];
  const audits = Array.isArray(view.audits) ? view.audits : [];
  return boPanel("verification", "Verification selection", view,
    `<p>${finalists.length ? finalists.map(id => `<span class="pill mono">${esc(id)}</span>`).join(" ") : '<span class="muted">No finalists recorded</span>'}</p>${audits.length ? `<p class="muted">Audits: ${audits.map(id => `<span class="mono">${esc(id)}</span>`).join(", ")}</p>` : ""}${view.shortfall ? `<p class="alert warn">Finalist shortfall: ${fmtNum(view.shortfall, 0)}</p>` : ""}${view.audit_shortfall ? `<p class="alert warn">Audit shortfall: ${fmtNum(view.audit_shortfall, 0)}</p>` : ""}`);
}

function renderBo(phase, data, study, rootId) {
  const bo = data?.bo;
  if (!bo || typeof bo !== "object") return "";
  const present = (view) => view && view.status !== "not_applicable";
  const chunks = [];
  if (["overview", "data", "execute", "decide"].includes(phase) && present(bo.run)) {
    chunks.push(renderRunStrip(bo.run, bo.convergence));
  }
  if (phase === "execute") {
    if (present(bo.convergence)) chunks.push(renderConvergence(bo.convergence));
    if (present(bo.trust_region)) chunks.push(renderTrustRegion(bo.trust_region));
    if (present(bo.pareto)) chunks.push(renderPareto(bo.pareto, study, phase, rootId));
  }
  if (phase === "explain") {
    if (present(bo.calibration)) chunks.push(renderCalibration(bo.calibration));
    if (present(bo.sensitivity)) chunks.push(renderSensitivity(bo.sensitivity));
    if (present(bo.design_space)) chunks.push(renderDesignSpace(bo.design_space));
  }
  if (phase === "data") {
    if (present(bo.data_summary)) chunks.push(renderDataSummary(bo.data_summary));
    if (present(bo.target_integrity)) chunks.push(renderTargetIntegrity(bo.target_integrity));
    if (present(bo.design_space)) chunks.push(renderDesignSpace(bo.design_space));
  }
  if (phase === "propose") {
    if (present(bo.proposal_explanation)) chunks.push(renderProposalExplanation(bo.proposal_explanation));
  }
  if (phase === "decide") {
    if (present(bo.pareto)) chunks.push(renderPareto(bo.pareto, study, phase, rootId));
    if (present(bo.verification)) chunks.push(renderBoVerification(bo.verification));
  }
  return chunks.join("");
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

const DASH = "–";
const finiteOrNull = value => (value != null && Number.isFinite(Number(value)) ? Number(value) : null);
const minOf = values => { const nums = values.map(finiteOrNull).filter(v => v != null); return nums.length ? Math.min(...nums) : null; };
const ratioText = (used, total) => {
  const u = finiteOrNull(used);
  if (u == null) return DASH;
  const t = finiteOrNull(total);
  return `${fmtNum(u, 0)} / ${t == null ? DASH : fmtNum(t, 0)}`;
};
const jOrDash = value => (value == null ? DASH : fmtNum(value));
function kpiCell(name, value, detail = "") {
  return `<div class="bo-kpi"><span class="bo-kpi-label">${esc(name)}</span><strong class="bo-kpi-value mono">${esc(value)}</strong>${detail ? `<span class="muted bo-kpi-detail">${detail}</span>` : ""}</div>`;
}

/** Live view: KPI strip, convergence chart and current pick, all from the execute panel's bo/progress data. */
function renderLive(data, selected) {
  const bo = data.bo && typeof data.bo === "object" ? data.bo : {};
  const run = bo.run && typeof bo.run === "object" ? bo.run : {};
  const conv = bo.convergence && typeof bo.convergence === "object" ? bo.convergence : null;
  const trust = bo.trust_region && typeof bo.trust_region === "object" ? bo.trust_region : {};
  const counts = data.call_counts && typeof data.call_counts === "object" ? data.call_counts : {};
  const arms = Array.isArray(conv?.arms) ? conv.arms : [];
  const budget = run.budget && typeof run.budget === "object" ? run.budget : {};
  const eta = conv?.eta && typeof conv.eta === "object" ? conv.eta : null;
  const etaSeconds = eta ? [finiteOrNull(eta.screen_seconds), finiteOrNull(eta.verify_seconds)] : [null, null];
  const etaTotal = etaSeconds.every(v => v != null) ? fmtDuration(etaSeconds[0] + etaSeconds[1]) : DASH;
  const etaDetail = eta ? `screen ${fmtDuration(eta.screen_seconds)} · verify ${fmtDuration(eta.verify_seconds)}` : "ETA is unavailable until this run records solve times";
  const refused = data.progress && typeof data.progress === "object" ? data.progress.refused : null;
  const kpis = [
    kpiCell("Screens used / total", ratioText(counts.screen_calls ?? trust.budget?.used, budget.screen_calls ?? trust.budget?.total)),
    kpiCell("Verify used / total", ratioText(counts.verify_calls, budget.verify_calls)),
    kpiCell("Best verify J", jOrDash(minOf(arms.map(a => a?.best_verify_j)))),
    kpiCell("Best screen J", jOrDash(minOf(arms.map(a => a?.best_j)))),
    kpiCell("ETA", etaTotal, etaDetail),
    kpiCell("Refusals", finiteOrNull(refused) == null ? DASH : fmtNum(refused, 0)),
  ].join("");
  const pick = conv?.incumbent ?? data.selected_horn ?? selected;
  const pickHtml = pick && typeof pick === "object"
    ? `<section class="bo-pick" aria-label="Current pick"><h3>Current pick</h3><p>${esc(safeText(pick.label || pick.id || "Best so far", 200))}</p><p class="mono">J ${esc(fmtNum(pick.j ?? pick.best_j ?? NaN))}</p><p class="muted">Screen J is reported but does not decide; verify J is the comparison endpoint.</p></section>`
    : `<section class="bo-pick" aria-label="Current pick"><h3>Current pick</h3><p class="muted">No pick is recorded yet.</p></section>`;
  const convergence = conv && conv.status !== "not_applicable" ? renderConvergence(conv) : '<p class="muted">Convergence is not recorded for this study yet.</p>';
  return `<div class="bo-kpis" role="list" aria-label="Live KPIs">${kpis}</div>${convergence}${pickHtml}`;
}

// P1: the three status families are different questions and must not share one badge.
//   * artifact validation  -> the stored byte-level view (ready / unknown / stale / missing)
//   * physical solve       -> measured / verified / refused, from the ledger and solves table
//   * analysis availability-> recorded / not recorded, never "invalid"
function semanticCard(name, value, detail = "") {
  return `<div class="study-semantic-card" role="listitem"><span class="study-semantic-label">${esc(name)}</span><strong>${esc(value)}</strong>${detail ? `<span class="muted">${detail}</span>` : ""}</div>`;
}

function renderSemanticSummary(phase, data, status) {
  const solves = data?.solves && typeof data.solves === "object" ? data.solves : null;
  const progress = data?.progress && typeof data.progress === "object" ? data.progress : null;
  const counts = data?.call_counts && typeof data.call_counts === "object" ? data.call_counts : null;
  const physical = [];
  if (solves) {
    if (finiteOrNull(solves.n_measured) != null) physical.push(`${fmtNum(solves.n_measured, 0)} measured`);
    if (finiteOrNull(solves.n_refused) != null) physical.push(`${fmtNum(solves.n_refused, 0)} refused`);
  }
  if (progress) {
    if (finiteOrNull(progress.verified) != null) physical.push(`${fmtNum(progress.verified, 0)} verified`);
    if (finiteOrNull(progress.refused) != null) physical.push(`${fmtNum(progress.refused, 0)} cheap refusals`);
  }
  if (counts) {
    if (finiteOrNull(counts.screen_calls) != null) physical.push(`${fmtNum(counts.screen_calls, 0)} screen calls`);
    if (finiteOrNull(counts.verify_calls) != null) physical.push(`${fmtNum(counts.verify_calls, 0)} verify calls`);
  }
  const cards = [
    semanticCard("Artifact validation", label(status), STATES[status] ? safeText(STATES[status], 160) : ""),
    semanticCard("Physical solves", physical.length ? physical.join(" · ") : "not recorded",
      physical.length ? "" : "No measured/verify rows are present in this panel."),
  ];
  if (["explain", "propose", "execute", "decide"].includes(phase)) {
    const loo = data?.bo?.calibration?.loo;
    const diag = data?.bo?.sensitivity?.diagnostics;
    const recorded = loo?.available === true || diag?.available === true;
    const canCompute = loo?.can_compute === true || diag?.can_compute === true;
    cards.push(semanticCard("Analysis availability",
      recorded ? "model diagnostics recorded" : "not recorded",
      recorded ? "" : (canCompute ? "A CPU diagnostics job can compute it; no BEM solve is needed." : "The stored artifacts do not include model diagnostics.")));
  }
  return `<div class="study-semantic-cards" role="list" aria-label="Status summary">${cards.join("")}</div>`;
}

export function renderStudyPanel(study, panel, selected = null, notice = "", state = {}) {
  if (!study || !ID.test(study.id || "") || !ROUTE_PHASES.includes(panel?.phase)) throw new Error("Invalid study view");
  const phase = panel.phase;
  const stale = panel.revision !== study.revision;
  const status = stale ? "stale" : (panel.status || "unknown");
  const data = panel.data && typeof panel.data === "object" ? panel.data : {};
  const actions = Array.isArray(data.actions) ? data.actions.map((action, index) => ({action, index})).filter(x => x.action && ACTIONS.has(x.action.kind)) : [];
  const visibleData = Object.fromEntries(Object.entries(data).filter(([k]) => !["actions", "selected_horn", "policies", "candidates", "package", "budget", "lane", "deadline", "stop_recovery", "stop_rules", "verification", "verification_policy", "progress", "job", "job_id", "job_status", "package_hash", "package_revision", "package_present", "artifacts", "bo", "solves"].includes(k)));
  const activePanel = {...panel, status};
  const renderState = {busy:state?.busy === true, artifact:state?.artifact || null};
  const isLive = phase === LIVE_PHASE;
  const linkPhase = isLive ? "execute" : phase;
  const hasPackage = state?.hasPackage === true || packagedStudies.has(study.id) || hasPackageData(data);
  const liveTab = hasPackage ? `<a href="${esc(studyRoute(study.id, LIVE_PHASE, study.root || null))}"${isLive ? ' aria-current="page"' : ""}>${esc(PHASE_LABELS[LIVE_PHASE])}</a>` : "";
  const resultsTab = `<a href="${esc(studyRoute(study.id, "results", study.root || null))}"${RESULT_PHASES.includes(phase) ? ' aria-current="page"' : ""}>${esc(PHASE_LABELS.results)}</a>`;
  const tabs = [liveTab, resultsTab, ...STUDY_PHASES.map(p => `<a href="${esc(studyRoute(study.id, p, study.root || null))}"${p === phase ? ' aria-current="page"' : ""}>${esc(PHASE_LABELS[p])}</a>`)].filter(Boolean).join(" · ");
  const actionHtml = actions.map(({action: a, index: i}) => {
    const outcomes = Array.isArray(a.allowed_outcomes) ? a.allowed_outcomes.filter(x => ["inconclusive", "accept", "reject"].includes(x)) : ["inconclusive", "accept", "reject"];
    const inputs = a.kind === "decision" ? `<label>Decision <select data-study-field="outcome">${outcomes.map(x => `<option value="${x}">${esc(label(x))}</option>`).join("")}</select></label><label>Rationale <textarea data-study-field="rationale" maxlength="4000"></textarea></label>` : a.kind === "save_draft" ? `<label>Study question <input data-study-field="question" maxlength="500"></label>` : a.kind === "create_child" ? `<label>Child study question <input data-study-field="question" maxlength="500"></label><label>Child policy <select data-study-field="policy"><option value="scalar">scalar</option><option value="turbo">turbo (trust region)</option><option value="pareto">coverage-ripple</option></select></label>` : "";
    const packageInputs = a.kind === "package" ? `<label>Solve lane <select data-study-field="lane"><option value="gpu">GPU</option><option value="cpu">CPU</option></select></label><label>Stop deadline (ISO 8601 with timezone) <input data-study-field="deadline" placeholder="2026-11-15T18:00:00-05:00" required></label>` : "";
    return `<div data-study-action-group="${i}">${a.reason ? `<p>${esc(a.reason)}</p>` : ""}${inputs}${packageInputs} <button type="button" data-study-action="${i}"${actionEnabled(a, activePanel, study, data) && !renderState.busy ? "" : " disabled"}>${esc(a.label || label(a.kind))}</button></div>`;
  }).join(" ");
  const selector = Array.isArray(data.candidates) ? data.candidates.slice(0, 50).map((c, i) => `<button type="button" data-study-select="${i}">${esc(c.label || c.id || `Candidate ${i + 1}`)}</button>`).join(" ") : "";
  const policyHtml = renderPolicySelector(study, activePanel, data, renderState);
  const candidateHtml = phase === "propose" ? candidateTable(data) : "";
  const executeHtml = phase === "execute" ? renderExecute(data) : "";
  const solvesHtml = phase === "execute" || phase === "decide" ? renderSolves(data, phase, study) : "";
  const boHtml = renderBo(phase, data, study, study.root || null);
  const artifactHtml = phase === "decide" ? renderArtifacts(data, renderState) : "";
  const semanticHtml = renderSemanticSummary(phase, data, status);
  // Raw phase payloads stay reachable for provenance, but never dominate the default view.
  const advancedHtml = `<details class="study-advanced"><summary>Advanced — raw artifact data</summary><p class="muted">Bounded preview of the stored phase payload. Identities are the source of truth; long lists and hashes are collapsed here on purpose.</p>${display(visibleData)}</details>`;
  const bodyHtml = isLive
    ? renderLive(data, selected)
    : `${semanticHtml}${candidateHtml}${executeHtml}${solvesHtml}${boHtml}${policyHtml}${advancedHtml}`;
  const selectedHorn = selected || data.selected_horn || null;
  const hasSolveRows = Array.isArray(data?.solves?.rows) && data.solves.rows.length > 0;
  const asideBody = selectedHorn
    ? display(selectedHorn)
    : hasSolveRows
      ? `<p class="muted">An explicit selection is not recorded on this authoring tab. Open <a href="${esc(studyRoute(study.id, "horns", study.root || null))}">Results → Horns</a> for the default best verified / screen horn.</p>`
      : '<p class="muted">No horn is recorded yet.</p>';
  return `<section class="study-workspace" aria-label="Study workspace"><header><p><a href="#/bayes/studies">Bayes</a> / Studies</p><h1>${esc(study.name || study.question || study.spec?.question || "Study")}</h1><p>Revision ${esc(study.revision)} · ${esc(study.status || "unknown")} · ${esc(study.protocol || "bo-study-v1.1")}${study.root_label ? ` · ${esc(study.root_label)}` : ""}</p><nav aria-label="Study phases">${tabs}</nav></header>
  ${notice ? `<p role="alert">${esc(notice)}</p>` : ""}
  <p role="status"><strong>Artifact validation: ${esc(label(status))}</strong>${STATES[status] ? `: ${esc(STATES[status])}` : ""}</p>
  ${Array.isArray(panel.reasons) && panel.reasons.length ? display(panel.reasons) : ""}
  <div class="study-layout"><main><h2>${esc(PHASE_LABELS[phase])}</h2>${bodyHtml}${artifactHtml}<details class="study-advanced"><summary>Provenance and raw identities</summary><h3>Provenance</h3>${display(panel.provenance || null)}</details>${selector}<p>${renderLinks(data, study.id, linkPhase, study.root || null)}</p></main>
  <aside aria-label="Selected horn"><h2>Selected horn</h2><p>Predicted, screen, and verified results are distinct.</p>${asideBody}${renderLinks(selected, study.id, linkPhase, study.root || null)}</aside></div>
  <section aria-label="Next action"><h2>Next action</h2>${actionHtml || '<p class="muted">No action is currently available.</p>'}</section>
  <p><a href="/api/studies/${encodeURIComponent(study.id)}/export" download="study-${esc(study.id)}.json">Export study record and artifact identities</a></p>
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
export function mountStudy(root, {studyId, phase = "overview", api, pollMs = 5000, onError = () => {}, rootId = null, drawCharts = null}) {
  if (!root || !ID.test(studyId || "") || !ROUTE_PHASES.includes(phase) || !api || typeof api.getStudy !== "function" || typeof api.getPanel !== "function") throw new Error("Invalid study mount");
  let rootRef = isId(rootId || "") ? rootId : null;
  let disposed = false, controller = null, timer = null, generation = 0, busy = false, refreshing = false;
  let study = null, panel = null, selected = null, notice = "", pendingKey = null, artifact = null;
  const isLive = phase === LIVE_PHASE;
  const fetchPhase = isLive ? "execute" : phase;
  const makeKey = () => globalThis.crypto?.randomUUID?.() || `study-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const draw = () => {
    if (disposed || !study || !panel) return;
    root.innerHTML = renderStudyPanel(study, panel, selected, notice, {busy, artifact, hasPackage: packagedStudies.has(studyId) || hasPackageData(panel.data)});
    if (typeof drawCharts === "function") {
      try { drawCharts(root, panel); }
      catch (error) { onError(error); }
    }
  };
  async function refresh() {
    // A slow panel must be allowed to finish. Polling must not repeatedly abort
    // it and leave the workspace blank under CPU/solver load.
    if (refreshing || disposed) return;
    refreshing = true;
    const current = ++generation;
    controller?.abort(); controller = new AbortController();
    try {
      const [nextStudy, nextPanel] = await Promise.all([api.getStudy(studyId, {root: rootRef, signal: controller.signal}), api.getPanel(studyId, fetchPhase, {root: rootRef, signal: controller.signal})]);
      if (disposed || current !== generation) return;
      if (!rootRef && isId(nextStudy?.root || "")) rootRef = nextStudy.root;
      if (study && study.revision !== nextStudy.revision) selected = null;
      if (hasPackageData(nextPanel?.data)) packagedStudies.add(studyId);
      // The Live view is only for studies with a run package; otherwise land on Overview.
      if (isLive && !packagedStudies.has(studyId)) { location.hash = studyRoute(studyId, "overview", rootRef || null); return; }
      study = nextStudy; panel = isLive ? {...nextPanel, phase: LIVE_PHASE} : nextPanel; draw();
    } catch (error) {
      if (disposed || current !== generation || error?.name === "AbortError") return;
      notice = "Study data could not be loaded. Retry or inspect the service status."; onError(error); draw();
      if (!study || !panel) root.innerHTML = `<p role="alert">${esc(notice)}</p>`;
    } finally {
      refreshing = false;
    }
  }
  async function loadArtifact(key) {
    if (typeof api.getArtifact !== "function" || (!ARTIFACT_REF.test(key) && !SHA256.test(key))) return;
    const token = generation;
    try {
      const next = await api.getArtifact(studyId, key, {root: rootRef, signal: controller?.signal});
      if (disposed || token !== generation) return;
      artifact = next; draw();
    } catch (error) {
      if (disposed || error?.name === "AbortError") return;
      notice = "Artifact could not be loaded."; onError(error); draw();
    }
  }
  async function solveDesign(designHash, target) {
    // One GPU verify solve for one measured study design.  Server-side validation is the source
    // of truth; this guard keeps a double click from dispatching twice.
    if (disposed || busy || !study || !panel) return;
    if (typeof designHash !== "string" || !/^[0-9a-f]{6,64}$/.test(designHash)) return;
    const rows = Array.isArray(panel.data?.solves?.rows) ? panel.data.solves.rows : [];
    const row = rows.find(item => item && item.design_hash === designHash);
    if (!row || row.physical !== true) { notice = "This design has no physical measurement."; draw(); return; }
    if (panel.data?.solves?.job) { notice = "A solve is already active."; draw(); return; }
    if (typeof api.action !== "function") return;
    const payload = {design_hash: designHash, expected_revision: study.revision};
    const fingerprint = JSON.stringify(["solve_design", designHash, study.revision]);
    if (!pendingKey || pendingKey.fingerprint !== fingerprint) pendingKey = {fingerprint, key: makeKey()};
    payload.idempotency_key = pendingKey.key;
    busy = true; if (target) target.disabled = true; draw();
    const token = generation;
    try {
      await api.action(studyId, "solve_design", payload, {root: rootRef, signal: controller?.signal});
      if (disposed || token !== generation) return;
      pendingKey = null;
      notice = "Solve queued. Its 3D view opens when the verify run finishes.";
      await refresh();
    } catch (error) {
      if (disposed || error?.name === "AbortError") return;
      notice = actionFailure(error); onError(error); await refresh();
    } finally { busy = false; draw(); }
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
      await api.action(studyId, "revise", payload, {root: rootRef, signal: controller?.signal});
      if (disposed || token !== generation) return;
      pendingKey = null; notice = "Proposal policy saved. Reloading the panel."; await refresh();
    } catch (error) {
      if (disposed || error?.name === "AbortError") return;
      notice = actionFailure(error); onError(error); await refresh();
    } finally { busy = false; draw(); }
  }
  async function click(event) {
    if (disposed) return;
    const solveTarget = event.target?.closest?.("[data-study-solve]");
    if (solveTarget?.dataset?.studySolve != null && root.contains(solveTarget)) {
      await solveDesign(solveTarget.dataset.studySolve, solveTarget);
      return;
    }
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
    const payload = sanitisePayload(action.payload);
    payload.expected_revision = study.revision;
    const group = target.closest("[data-study-action-group]");
    for (const field of group?.querySelectorAll("[data-study-field]") || []) payload[field.dataset.studyField] = field.value;
    busy = true; target.disabled = true; draw();
    if (action.kind === "decision" && !String(payload.rationale || "").trim()) {
      notice = "Enter a rationale before recording a decision."; busy = false; draw(); return;
    }
    if (action.kind === "decision" && Array.isArray(action.allowed_outcomes) && !action.allowed_outcomes.includes(payload.outcome)) {
      notice = "Complete verification before accepting or rejecting this study."; busy = false; draw(); return;
    }
    if (selected && typeof selected.id === "string" && ID.test(selected.id)) payload.selected_id = selected.id;
    if (action.kind === "launch" || action.kind === "queue_study") payload.package_hash = action.package_hash;
    if (action.kind === "queue_study") payload.expected_revision = study.revision;
    if (action.kind === "cancel") {
      delete payload.expected_revision;
      if (ID.test(action.job_id || "")) payload.job_id = action.job_id;
      if (ID.test(action.package_id || "")) payload.package_id = action.package_id;
      if (payload.job_id == null && payload.package_id == null) { busy = false; draw(); return; }
    }
    const fingerprint = JSON.stringify([action.kind, payload]);
    if (!pendingKey || pendingKey.fingerprint !== fingerprint) pendingKey = {fingerprint, key: makeKey()};
    payload.idempotency_key = pendingKey.key;
    const token = generation;
    try {
      const result = await api.action(studyId, action.kind, payload, {root: rootRef, signal: controller?.signal});
      if (disposed || token !== generation) return;
      pendingKey = null;
      if (action.kind === "create_child" && isId(result?.id || "")) {
        busy = false;
        location.hash = studyRoute(result.id, "overview", rootRef || study.root || null);
        return;
      }
      notice = action.kind === "queue_study"
        ? `Night file written: ${result?.path || "runs/nights/"}. ${result?.note || "It was not launched."}`
        : "Request recorded. Status will update from the registry.";
      await refresh();
    } catch (error) {
      if (disposed || error?.name === "AbortError") return;
      notice = actionFailure(error);
      onError(error); await refresh();
    } finally { busy = false; draw(); }
  }
  root.addEventListener("click", click);
  refresh();
  // Live polls every 10 s, and only while the study is running; the timer is cleared on dispose.
  const livePoll = isLive ? LIVE_POLL_MS : pollMs;
  if (Number.isFinite(livePoll) && livePoll > 0) timer = setInterval(() => {
    if (busy) return;
    if (isLive && !studyIsRunning(study, panel?.data)) return;
    refresh();
  }, Math.max(1000, livePoll));
  return () => { disposed = true; generation++; controller?.abort(); if (timer != null) clearInterval(timer); root.removeEventListener("click", click); };
}

export function renderStudyList(studies, notice = "") {
  if (!Array.isArray(studies) || studies.length > 100) throw new Error("Invalid study list");
  const rows = studies.map(s => ID.test(s?.id || "") ? `<li><a href="${esc(studyRoute(s.id, LIVE_PHASE, s.root || null))}">${esc(s.name || s.question || s.id)}</a> · revision ${esc(s.revision ?? "unknown")} · ${esc(s.status || "draft")}${s.root_label ? ` · <span class="muted mono">${esc(s.root_label)}</span>` : ""}</li>` : "").join("");
  return `<section aria-label="Studies"><h1>Studies</h1><p><a href="#/analysis">Analysis reports</a> · <a href="#/bayes/board">Method board</a></p>${notice ? `<p role="alert">${esc(notice)}</p>` : ""}<h2>Existing studies</h2>${rows ? `<ul>${rows}</ul>` : "<p>No studies are available.</p>"}<h2>New draft</h2><form data-study-create><label>Study question <input name="question" maxlength="500" required></label><label>Horn task <select name="task"><option value="p80x60__osse_ext_throat_home700_v7_seed5678">Home 80 × 60 / 700 Hz — current solver cohort, seed 5678 (v7)</option><option value="p80x60__osse_ext_throat_home700_v7">Home 80 × 60 / 700 Hz — original cohort (v7)</option><option value="native__ath_core_v4">Frozen native ATH validation (v4)</option></select></label><fieldset><legend>Compatible measured cohort (explicit paths for home task)</legend><label>Offline scores JSON <input name="scores_json"></label><label>Catalog CSV <input name="catalog_csv"></label><label>Dataset directory <input name="dataset_root"></label><label>Candidate pool JSON (optional) <input name="pool_json"></label></fieldset><button type="submit">Save draft</button></form></section>`;
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
    const form = new FormData(event.target);
    const question = String(form.get("question") || "").trim();
    const task = String(form.get("task") || "native__ath_core_v4");
    const source = Object.fromEntries(["scores_json", "catalog_csv", "dataset_root", "pool_json"].map(k => [k, String(form.get(k) || "").trim()]).filter(([,v]) => v));
    const spec = {protocol:"bo-study-v1.1", question, task:{name:task}, policy:{proposal_policy:"scalar"}, ...(Object.keys(source).length ? {source} : {})};
    if (!question || question.length > 500) { notice = "Enter a study question."; draw(); return; }
    busy = true;
    const button = event.target.querySelector("button"); if (button) button.disabled = true;
    const fingerprint = JSON.stringify(spec);
    if (!pending || pending.fingerprint !== fingerprint) pending = {fingerprint, key: globalThis.crypto?.randomUUID?.() || `draft-${Date.now()}-${Math.random().toString(36).slice(2)}`};
    try {
      const created = await api.createStudy({spec, key:pending.key}, {signal:controller.signal});
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
