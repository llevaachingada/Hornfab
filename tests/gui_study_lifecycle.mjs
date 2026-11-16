// DOM-stub lifecycle test for studies.js. No jsdom/playwright is installed; this exercises the
// module's mount/dispose/action contract against a hand-written DOM stub, not a real browser.
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";

const studiesSrc = await readFile(process.argv[2], "utf8");
const appSrc = await readFile(process.argv[3], "utf8");
const m = await import("data:text/javascript;base64," + Buffer.from(studiesSrc).toString("base64"));

// ── deterministic stubs ──────────────────────────────────────────────────────────────────────
const intervalState = {next:1, callbacks:new Map(), cleared:[]};
globalThis.setInterval = (fn, _ms) => { const id = intervalState.next++; intervalState.callbacks.set(id, fn); return id; };
globalThis.clearInterval = id => { intervalState.cleared.push(id); intervalState.callbacks.delete(id); };

globalThis.AbortController = class AbortControllerStub {
  static instances = [];
  constructor() {
    this.signal = {aborted:false, listeners:new Set(), addEventListener:(name, fn) => { if (name === "abort") this.signal.listeners.add(fn); }};
    AbortControllerStub.instances.push(this);
  }
  abort() {
    if (this.signal.aborted) return;
    this.signal.aborted = true;
    for (const fn of this.signal.listeners) fn();
  }
};

let keySeq = 0;
Object.defineProperty(globalThis, "crypto", {configurable:true, value:{randomUUID:() => `key-${++keySeq}`}});
globalThis.fetch = async () => { throw new Error("studies.js must only use injected adapters"); };

const tick = async (n = 3) => { for (let i = 0; i < n; i++) await new Promise(r => setImmediate(r)); };
const deferred = () => { let resolve, reject; const promise = new Promise((res, rej) => { resolve = res; reject = rej; }); return {promise, resolve, reject}; };

function makeRoot() {
  const listeners = new Map();
  return {
    innerHTML:"",
    addEventListener(name, fn) { listeners.set(name, fn); },
    removeEventListener(name, fn) { if (listeners.get(name) === fn) listeners.delete(name); },
    contains() { return true; },
    querySelectorAll() { return []; },
    replaceWith() {},
    click(event) { const fn = listeners.get("click"); return fn ? fn(event) : undefined; },
  };
}

function element(dataset, group = null) {
  return {
    dataset,
    disabled:false,
    closest(selector) {
      if (selector.includes("data-study-artifact") && dataset.studyArtifact != null) return this;
      if (selector.includes("data-study-policy") && dataset.studyPolicy != null) return this;
      if (selector.includes("data-study-solve") && dataset.studySolve != null) return this;
      if (selector.includes("data-study-action") && dataset.studyAction != null) return this;
      if (selector.includes("data-study-select") && dataset.studySelect != null) return this;
      if (selector.includes("data-study-action-group")) return group;
      return null;
    },
    querySelectorAll(selector) { return selector.includes("data-study-field") && group ? group.fields : []; },
  };
}

const study = {id:"study1", revision:1, name:"Lifecycle", status:"draft", spec:{protocol:"bo-study-v1.1", policy:{mode:"scalar", seed:1}}};
const ready = {status:"ready", revision:1, provenance:{source:"measured"}, reasons:[]};
const executePanel = {...ready, phase:"execute", data:{lane:"cpu", actions:[{kind:"launch", label:"Launch", enabled:true, package_hash:"a".repeat(64), package_revision:1}]}};

// ── 1. mount -> load -> paint; dispose before a delayed response aborts and never paints ─────
{
  const root = makeRoot();
  const studyDeferred = deferred(), panelDeferred = deferred();
  const api = {getStudy:() => studyDeferred.promise, getPanel:() => panelDeferred.promise, action:async () => ({})};
  const dispose = m.mountStudy(root, {studyId:"study1", phase:"execute", api, pollMs:1000});
  const timerId = [...intervalState.callbacks.keys()].at(-1);
  const controller = AbortController.instances.at(-1);
  dispose();
  assert.equal(controller.signal.aborted, true, "dispose aborts the in-flight controller");
  assert.equal(intervalState.cleared.filter(id => id === timerId).length, 1, "interval cleared exactly once");
  studyDeferred.resolve(study); panelDeferred.resolve(executePanel); await tick();
  assert.equal(root.innerHTML, "", "a delayed response after dispose never paints");
}

// ── 2. route-to-route phase change on the same root does not leak or repaint ─────────────────
{
  const root = makeRoot();
  const oldStudy = deferred(), oldPanel = deferred();
  const oldApi = {getStudy:() => oldStudy.promise, getPanel:() => oldPanel.promise, action:async () => ({})};
  const disposeOld = m.mountStudy(root, {studyId:"study1", phase:"execute", api:oldApi, pollMs:1000});
  const oldTimer = [...intervalState.callbacks.keys()].at(-1);
  disposeOld();
  assert.equal(intervalState.cleared.filter(id => id === oldTimer).length, 1);

  const newApi = {
    getStudy:async () => study,
    getPanel:async () => ({phase:"data", status:"partial", revision:1, data:{marker:"DATA-ROUTE"}, provenance:{}, reasons:[]}),
    action:async () => ({}),
  };
  const disposeNew = m.mountStudy(root, {studyId:"study1", phase:"data", api:newApi, pollMs:0});
  await tick();
  assert.ok(root.innerHTML.includes("DATA-ROUTE"), "new phase painted");
  oldStudy.resolve(study); oldPanel.resolve(executePanel); await tick();
  assert.ok(root.innerHTML.includes("DATA-ROUTE") && !root.innerHTML.includes("Queue run"), "old phase cannot update the new panel");
  disposeNew();
}

// ── 3. slow panels finish before another poll, preventing abort starvation ───────────────────
{
  const root = makeRoot();
  const firstStudy = deferred(), firstPanel = deferred();
  let studyCalls = 0, panelCalls = 0;
  const api = {
    getStudy:() => { studyCalls++; return studyCalls === 1 ? firstStudy.promise : Promise.resolve(study); },
    getPanel:() => { panelCalls++; return panelCalls === 1 ? firstPanel.promise : Promise.resolve({...ready, phase:"execute", data:{marker:"NEW-GENERATION"}}); },
    action:async () => ({}),
  };
  const dispose = m.mountStudy(root, {studyId:"study1", phase:"execute", api, pollMs:1000});
  const poll = [...intervalState.callbacks.values()].at(-1);
  poll();
  await tick();
  assert.equal(studyCalls, 1, "poll does not restart the in-flight study request");
  assert.equal(panelCalls, 1, "poll does not restart the in-flight panel request");
  firstStudy.resolve(study);
  firstPanel.resolve({...ready, phase:"execute", data:{marker:"FIRST-GENERATION"}});
  await tick();
  assert.ok(root.innerHTML.includes("FIRST-GENERATION"), "slow first panel eventually paints");
  poll();
  await tick();
  assert.equal(studyCalls, 2);
  assert.ok(root.innerHTML.includes("NEW-GENERATION"), "next completed poll replaces older data");
  dispose();
}

// ── 4. double-click Launch sends one request with one idempotency key ────────────────────────
{
  const root = makeRoot();
  const calls = [], pending = deferred();
  const api = {getStudy:async () => study, getPanel:async () => executePanel, action:(...args) => { calls.push(args); return pending.promise; }};
  const dispose = m.mountStudy(root, {studyId:"study1", phase:"execute", api, pollMs:0});
  await tick();
  const button = element({studyAction:"0"});
  const first = root.click({target:button});
  await tick();
  await root.click({target:button});
  assert.equal(calls.length, 1, "duplicate click does not dispatch twice");
  assert.equal(calls[0][1], "launch");
  assert.equal(calls[0][2].package_hash, "a".repeat(64));
  assert.equal(calls[0][2].expected_revision, 1);
  assert.ok(calls[0][2].idempotency_key);
  pending.resolve({status:"queued"}); await first; await tick();
  dispose();
}

// ── 5. cancel carries the owned job or package id ───────────────────────────────────────────
{
  const root = makeRoot();
  const calls = [];
  const panel = {...ready, phase:"execute", data:{actions:[
    {kind:"cancel", label:"Cancel job", enabled:true, job_id:"job1", job_status:"running"},
    {kind:"cancel", label:"Cancel package", enabled:true, package_id:"pkg1", package_status:"queued"},
  ]}};
  const api = {getStudy:async () => study, getPanel:async () => panel, action:async (...args) => { calls.push(args); return {}; }};
  const dispose = m.mountStudy(root, {studyId:"study1", phase:"execute", api, pollMs:0});
  await tick();
  await root.click({target:element({studyAction:"0"})}); await tick();
  await root.click({target:element({studyAction:"1"})}); await tick();
  assert.equal(calls.length, 2);
  assert.equal(calls[0][1], "cancel"); assert.equal(calls[0][2].job_id, "job1"); assert.equal(calls[0][2].package_id, undefined);
  assert.equal(calls[1][2].package_id, "pkg1"); assert.equal(calls[1][2].job_id, undefined);
  assert.ok(calls.every(call => call[2].idempotency_key));
  dispose();
}

// ── 6. policy selector posts /revise once with the backend mode ─────────────────────────────
{
  const root = makeRoot();
  const calls = [];
  const panel = {...ready, phase:"propose", data:{policies:[
    {id:"scalar", label:"scalar Bayesian", status:"ready", requires:["training_set"], verification_mode:"scalar"},
    {id:"pareto", label:"coverage/ripple trade-offs", status:"ready", requires:["cohort"], verification_mode:"pareto"},
  ]}};
  const api = {getStudy:async () => study, getPanel:async () => panel, action:async (...args) => { calls.push(args); return {}; }};
  const dispose = m.mountStudy(root, {studyId:"study1", phase:"propose", api, pollMs:0});
  await tick();
  await root.click({target:element({studyPolicy:"pareto"})}); await tick();
  assert.equal(calls.length, 1);
  assert.equal(calls[0][1], "revise");
  assert.equal(calls[0][2].spec.policy.mode, "pareto");
  assert.equal(calls[0][2].expected_revision, 1);
  assert.ok(calls[0][2].idempotency_key);
  assert.equal(study.spec.policy.mode, "scalar", "source study spec is not mutated");
  dispose();
}

// ── 7. decision requires a rationale; a supplied rationale is sent ─────────────────────────
{
  const root = makeRoot();
  const calls = [];
  const panel = {...ready, phase:"decide", data:{actions:[{kind:"decision", label:"Record decision", enabled:true}]}};
  const api = {getStudy:async () => study, getPanel:async () => panel, action:async (...args) => { calls.push(args); return {}; }};
  const dispose = m.mountStudy(root, {studyId:"study1", phase:"decide", api, pollMs:0});
  await tick();
  const blankGroup = {fields:[element({studyField:"outcome"}, null)]}; blankGroup.fields[0].value = "accept";
  await root.click({target:element({studyAction:"0"}, blankGroup)}); await tick();
  assert.equal(calls.length, 0, "no decision without a rationale");
  assert.ok(root.innerHTML.includes("Enter a rationale"));
  const group = {fields:[element({studyField:"outcome"}), element({studyField:"rationale"})]};
  group.fields[0].value = "accept"; group.fields[1].value = "measured parity";
  await root.click({target:element({studyAction:"0"}, group)}); await tick();
  assert.equal(calls.length, 1);
  assert.equal(calls[0][1], "decision");
  assert.equal(calls[0][2].outcome, "accept");
  assert.equal(calls[0][2].rationale, "measured parity");
  assert.equal(calls[0][2].expected_revision, 1);
  dispose();
}

// ── 8. artifact links fetch a bounded panel by kind or sha ──────────────────────────────────
{
  const root = makeRoot();
  const sees = [];
  const panel = {...ready, phase:"decide", data:{artifacts:[{kind:"proposal", label:"Proposal"}]}};
  const api = {
    getStudy:async () => study,
    getPanel:async () => panel,
    getArtifact:async (id, key) => { sees.push([id, key]); return {status:"ready", kind:"proposal", sha256:null, revision:1, data:{marker:"ARTIFACT-PANEL"}, provenance:{}, reasons:[], metadata_only:true}; },
    action:async () => ({}),
  };
  const dispose = m.mountStudy(root, {studyId:"study1", phase:"decide", api, pollMs:0});
  await tick();
  await root.click({target:element({studyArtifact:"proposal"})}); await tick();
  assert.deepEqual(sees, [["study1", "proposal"]]);
  assert.ok(root.innerHTML.includes("ARTIFACT-PANEL"));
  assert.ok(root.innerHTML.includes("binary arrays are never loaded"));
  dispose();
}

// ── 9. 422/503 surfaces the exact unavailable reason; 409 asks for a refresh ─────────────────
{
  for (const [status, expected] of [[422, "Unavailable: no optional engine"], [503, "Unavailable: lane service missing"], [409, "Refresh before continuing"]]) {
    const root = makeRoot();
    const api = {
      getStudy:async () => study,
      getPanel:async () => executePanel,
      action:async () => { const error = new Error(status === 409 ? "stale" : (status === 422 ? "no optional engine" : "lane service missing")); error.status = status; throw error; },
    };
    const dispose = m.mountStudy(root, {studyId:"study1", phase:"execute", api, pollMs:0});
    await tick();
    await root.click({target:element({studyAction:"0"})}); await tick();
    assert.ok(root.innerHTML.includes(expected), `status ${status}: ${expected}`);
    dispose();
  }
}

// ── 10. render model: policy cards, capability card, candidates, package/progress ───────────
{
  const capStudy = {id:"study1", revision:1, spec:{policy:{mode:"scalar"}}};
  const cap = m.renderStudyPanel(capStudy, {phase:"propose", status:"ready", revision:1, data:{
    policies:[{id:"scalar", label:"scalar Bayesian", status:"capability_missing", reason:"BoTorch is unavailable", requires:["training_set"]}],
    actions:[{kind:"propose", label:"Propose", enabled:true}],
  }});
  assert.ok(cap.includes("BoTorch is unavailable"));
  assert.ok(cap.includes('data-study-action="0" disabled'), "Propose stays disabled when the policy is unavailable");

  const candidates = m.renderStudyPanel(capStudy, {phase:"propose", status:"ready", revision:1, data:{
    policies:[{id:"scalar", label:"scalar Bayesian", status:"ready"}],
    candidates:[
      {id:"c1", predicted_j:{value:1.2, lower:1, upper:1.4, unit:"J"}, coverage_deg:{value:60, unit:"deg"}, ripple_db:{value:2, unit:"dB"}, selection_reason:"improvement", feasibility:"feasible", nearest_examples:["g1"]},
      {id:"c2", measured:true, j:3},
    ],
  }});
  assert.ok(candidates.includes("Predicted") && candidates.includes("Measured"));
  assert.ok(candidates.includes("1.2 [1, 1.4] J"));
  assert.ok(candidates.includes("coverage deg") && candidates.includes("60"));
  assert.ok(candidates.includes("improvement") && candidates.includes("feasible") && candidates.includes("g1"));

  const execute = m.renderStudyPanel(capStudy, {phase:"execute", status:"ready", revision:1, data:{
    package:{hash:"b".repeat(64), revision:1},
    budget:{screen:18}, lane:"cpu", deadline:{required:true, seconds:3600},
    stop_recovery:{max_infrastructure_failures:3},
    verification:{finalists:4, audits:2},
    progress:{proposed:3, started:2, solved:1, cached:1, refused:0, infeasible:0, infrastructure_failed:0, verified:0, unknown:0},
    job:{id:"job1", status:"running"},
  }});
  for (const text of ["b".repeat(64), "cpu", "screen", "3", "4 finalists", "2 audits", "job1", "running", "infrastructure failed"]) assert.ok(execute.includes(text), text);

  const blocked = m.renderStudyPanel(capStudy, {phase:"execute", status:"ready", revision:1, data:{actions:[
    {kind:"launch", label:"Launch", enabled:true, package_revision:1},
    {kind:"cancel", label:"Cancel", enabled:true, job_id:"job1", job_status:"complete"},
  ]}});
  assert.ok(blocked.includes('data-study-action="0" disabled') && blocked.includes('data-study-action="1" disabled'));
}

// ── 11. app.js route table and action map contract ──────────────────────────────────────────
{
  const studyRouteAt = appSrc.indexOf("#\\/analysis\\/study\\/");
  const genericRouteAt = appSrc.indexOf("#\\/analysis\\/([^\\/?#]+)$");
  assert.ok(studyRouteAt > 0 && genericRouteAt > 0 && studyRouteAt < genericRouteAt, "study routes precede the generic analysis route");
  for (const fragment of ['package:"package"', 'launch:"launch"', 'cancel:"cancel"', 'decision:"decision"', 'revise:"revise"', 'analyze:"jobs"', 'propose:"jobs"', 'solve_design:"jobs"']) {
    assert.ok(appSrc.includes(fragment), fragment);
  }
  assert.ok(appSrc.includes('kind === "analyze" || kind === "propose"'), "analyze/propose keep the jobs payload");
  assert.ok(appSrc.includes('kind === "solve_design"'), "solve_design posts its kind onto /jobs");
  assert.ok(appSrc.includes('/api/studies/${encodeURIComponent(id)}/artifacts/${encodeURIComponent(artifact)}'), "artifact path is bounded by id encoding");
}

// ── 12. Live tab follows the server package flag on first load; no package -> no Live tab ──
{
  assert.equal(m.hasPackageData({package_present:true}), true, "server flag is package evidence");
  assert.equal(m.hasPackageData({package_present:false}), false, "false flag is not package evidence");
  assert.equal(m.hasPackageData({}), false);

  const overview = data => ({...ready, phase:"overview", data});
  const packaged = m.renderStudyPanel({id:"pkgstudy", revision:1}, overview({package_present:true}));
  assert.ok(packaged.includes("#/bayes/study/pkgstudy/live"), "package_present shows the Live tab on first load");
  const plain = m.renderStudyPanel({id:"plainstudy", revision:1}, overview({}));
  assert.ok(!plain.includes("#/bayes/study/plainstudy/live"), "no package -> no Live tab");
}

// ── 13. a direct live route uses the first panel's flag; package-less falls back to Overview ──
{
  globalThis.location = {hash:""};
  const liveRoot = makeRoot();
  const liveApi = {
    getStudy:async () => ({...study, id:"livestudy"}),
    getPanel:async () => ({...ready, phase:"execute", data:{package_present:true}}),
    action:async () => ({}),
  };
  const disposeLive = m.mountStudy(liveRoot, {studyId:"livestudy", phase:"live", api:liveApi, pollMs:0});
  await tick();
  assert.equal(globalThis.location.hash, "", "first live load of a packaged study does not redirect");
  assert.ok(liveRoot.innerHTML.includes("Live KPIs"), "live view paints from the first fetch");
  disposeLive();

  globalThis.location = {hash:""};
  const plainRoot = makeRoot();
  const plainApi = {
    getStudy:async () => ({...study, id:"plainlive"}),
    getPanel:async () => ({...ready, phase:"execute", data:{}}),
    action:async () => ({}),
  };
  const disposePlain = m.mountStudy(plainRoot, {studyId:"plainlive", phase:"live", api:plainApi, pollMs:0});
  await tick();
  assert.equal(globalThis.location.hash, "#/bayes/study/plainlive/overview", "package-less live route lands on Overview");
  assert.equal(plainRoot.innerHTML, "", "package-less live route does not paint");
  disposePlain();
}

// ── 14. study solves table: counts, 3D links, per-row solve action + disabled reasons ────────
{
  const runId = "20261116T120000Z-studyverify-abcdef";
  const panel = m.renderStudyPanel({id:"study1", revision:1}, {phase:"execute", status:"ready", revision:1, data:{
    solves: {
      rows: [
        {design_hash:"aaaa1111", kind:"screen", j:2.5, physical:true, outcome:"success", verify_run_id:runId},
        {design_hash:"bbbb2222", kind:"screen", j:null, physical:false, outcome:"cheap_refusal", verify_run_id:null},
      ],
      n_total: 4, n_measured: 1, n_refused: 1, truncated: true,
    },
  }});
  assert.ok(panel.includes("<h3>Solves</h3>"), "solves heading renders above artifacts");
  assert.ok(panel.includes("4 observations") && panel.includes("1 measured") && panel.includes("1 refused"));
  assert.ok(panel.includes(`href="#/run/${runId}/3d"`), "a verified design links to its 3D view");
  assert.ok(panel.includes(`href="#/run/${runId}/verify"`), "the verify table stays reachable");
  assert.ok(panel.includes('data-study-solve="aaaa1111">Solve in 3D</button>'), "measured row offers the action");
  assert.ok(panel.includes('data-study-solve="bbbb2222" disabled'), "non-physical row is disabled");
  assert.ok(panel.includes("Showing the first 2 solves by J"), "truncation is explicit");

  const busy = m.renderStudyPanel({id:"study1", revision:1}, {phase:"decide", status:"ready", revision:1, data:{
    solves: {rows:[{design_hash:"aaaa1111", kind:"screen", j:2.5, physical:true, outcome:"success"}],
             n_total:1, n_measured:1, n_refused:0, truncated:false,
             job:{id:"j1", design_hash:"cccc3333", status:"running"}},
  }});
  assert.ok(busy.includes('data-study-solve="aaaa1111" disabled'), "an active solve disables every row");
  assert.ok(busy.includes("Solve running for") && busy.includes("cccc3333"));

  const absent = m.renderStudyPanel({id:"study1", revision:1}, {phase:"execute", status:"ready", revision:1, data:{}});
  assert.ok(!absent.includes("<h3>Solves</h3>"), "no solves data leaves the panel untouched");
}

// ── 15. clicking "Solve in 3D" dispatches one solve_design with one idempotency key ──────────
{
  const root = makeRoot();
  const calls = [], pending = deferred();
  const panel = {...ready, phase:"execute", data:{
    solves: {rows:[{design_hash:"aaaa1111", kind:"screen", j:2.5, physical:true, outcome:"success"}],
             n_total:1, n_measured:1, n_refused:0, truncated:false},
  }};
  const api = {getStudy:async () => study, getPanel:async () => panel, action:(...args) => { calls.push(args); return pending.promise; }};
  const dispose = m.mountStudy(root, {studyId:"study1", phase:"execute", api, pollMs:0});
  await tick();
  const button = element({studySolve:"aaaa1111"});
  const first = root.click({target:button});
  await tick();
  await root.click({target:button});
  assert.equal(calls.length, 1, "a double click dispatches one solve");
  assert.equal(calls[0][1], "solve_design");
  assert.equal(calls[0][2].design_hash, "aaaa1111");
  assert.equal(calls[0][2].expected_revision, 1);
  assert.ok(calls[0][2].idempotency_key);
  pending.resolve({status:"running"}); await first; await tick();
  dispose();

  const blockedRoot = makeRoot();
  const blockedCalls = [];
  const blockedPanel = {...ready, phase:"execute", data:{
    solves: {rows:[{design_hash:"bbbb2222", kind:"screen", j:null, physical:false, outcome:"cheap_refusal"}],
             n_total:1, n_measured:0, n_refused:1, truncated:false},
  }};
  const blockedApi = {getStudy:async () => study, getPanel:async () => blockedPanel, action:async (...args) => { blockedCalls.push(args); return {}; }};
  const disposeBlocked = m.mountStudy(blockedRoot, {studyId:"study1", phase:"execute", api:blockedApi, pollMs:0});
  await tick();
  await blockedRoot.click({target:element({studySolve:"bbbb2222"})}); await tick();
  assert.equal(blockedCalls.length, 0, "a non-physical design never starts a GPU solve");
  assert.ok(blockedRoot.innerHTML.includes("no physical measurement"));
  disposeBlocked();
}

console.log("study lifecycle ok");
