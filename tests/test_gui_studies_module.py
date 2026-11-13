from pathlib import Path
import subprocess

MODULE = Path(__file__).resolve().parents[1] / "hornlab_search/gui/static/studies.js"


def test_study_workspace_offline(tmp_path):
    script = tmp_path / "study_test.mjs"
    script.write_text(r'''
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
const src = await readFile(process.argv[2], "utf8");
const m = await import("data:text/javascript;base64," + Buffer.from(src).toString("base64"));
const study = {id:"study1", revision:3, name:"<img src=x>", status:"draft"};
assert.ok(m.renderStudyPanel({id:"nested",revision:1,spec:{question:"Nested question"}}, {phase:"overview",status:"missing",revision:1,data:{}}).includes("Nested question"));
const common = {status:"ready", revision:3, provenance:{source:"measured", unit:"dB"}, reasons:[]};
for (const phase of m.STUDY_PHASES) {
  const panel = {...common, phase, data:{predicted:{J:1}, screen:{J:2}, verified:{J:3},
    raw:{coverage:"4 deg"}, normalized:{coverage:2}, weighted:{coverage:2},
    parameter_effects:"observed", exclusions:7, support:"limited", budget:{screen:18}, lane:"cpu",
    actions:[{kind:"launch",label:"Queue run",enabled:true,package_hash:"a".repeat(64),package_revision:3}]}};
  const html = m.renderStudyPanel(study, panel);
  assert.ok(html.includes("&lt;img src=x&gt;") && !html.includes("<img src=x>"));
  for (const text of ["Predicted", "screen", "verified", "normalized", "weighted", "support", "exclusions", "Provenance", "Queue run"]) assert.ok(html.includes(text));
  assert.ok(!html.includes('data-study-action="0" disabled'));
  assert.ok(m.renderStudyPanel(study, {...panel, revision:2}).includes('data-study-action="0" disabled'));
}
const safeButtons = m.renderStudyPanel(study, {...common, phase:"execute", data:{actions:[{kind:"unsupported"},{kind:"analyze",label:"Analyze",enabled:true},{kind:"launch",label:"Launch",enabled:true,package_hash:"a".repeat(64),package_revision:3}]}});
assert.ok(safeButtons.includes('data-study-action="1">Analyze'));
assert.ok(safeButtons.includes('data-study-action="2">Launch'));
const blank = {...common, phase:"data", status:"dependency_missing", data:{}};
assert.ok(m.renderStudyPanel(study, blank).includes("dependency is unavailable"));
assert.ok(m.renderStudyPanel(study, {...blank,status:"no_data"}).includes("No compatible data"));
const link = m.studyRunLink("run1", "study1", "execute", true);
assert.ok(link.startsWith("#/run/run1/verify?") && link.includes("study=study1") && link.includes("return="));
assert.equal(m.studyRunLink("javascript:alert", "study1"), null);
assert.throws(() => m.studyRoute("../x"));

let clickHandler, requests = 0, sends = 0, aborted = false, resolveAction;
const root = {innerHTML:"", addEventListener:(name,fn)=>clickHandler=fn, removeEventListener:(name,fn)=>{if(fn===clickHandler) clickHandler=null;}, contains:()=>true};
const action = {kind:"launch",enabled:true,package_hash:"a".repeat(64),package_revision:3};
const api = {getStudy:async (_id,{signal}) => {requests++; signal.addEventListener("abort",()=>aborted=true); return study;},
 getPanel:async()=>({...common,phase:"execute",data:{actions:[action]}}),
 action:async (_id,kind,payload)=>{ sends++; assert.equal(kind,"launch"); assert.equal(payload.expected_revision,3); assert.ok(payload.idempotency_key); await new Promise(r=>resolveAction=r); }};
const dispose = m.mountStudy(root,{studyId:"study1",phase:"execute",api,pollMs:0});
await new Promise(r=>setImmediate(r));
const button = {dataset:{studyAction:"0"}, disabled:false, closest(sel){return sel.includes("data-study-action-group") ? null : this;}};
const first = clickHandler({target:button});
await new Promise(r=>setImmediate(r));
await clickHandler({target:button});
assert.equal(sends,1);
resolveAction(); await first;
assert.ok(requests >= 2 && aborted);
dispose(); assert.equal(clickHandler,null);
assert.ok(m.renderStudyList([{id:"study1",question:"<script>x</script>",revision:3}]).includes("&lt;script&gt;"));
let submitHandler, created, createdCalls = 0;
const listRoot = {innerHTML:"", addEventListener:(_n,fn)=>submitHandler=fn, removeEventListener:()=>submitHandler=null};
globalThis.FormData = class { get() { return "A useful question"; } };
const unmount = m.mountStudyList(listRoot, {api:{listStudies:async()=>[{id:"study1",revision:3}],
  createStudy:async (request)=>{createdCalls++; assert.equal(request.spec.protocol,"bo-study-v1.1");
    assert.equal(request.spec.question,"A useful question"); assert.ok(request.key); return {id:"new1"};}},
  onCreated:value=>created=value});
await new Promise(r=>setImmediate(r));
const form = {matches:()=>true, querySelector:()=>({disabled:false})};
await submitHandler({target:form,preventDefault(){}});
assert.equal(createdCalls,1); assert.equal(created.id,"new1");
unmount(); assert.equal(submitHandler,null);
console.log("study workspace ok");
''', encoding="utf-8")
    result = subprocess.run(["node", str(script), str(MODULE)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "study workspace ok" in result.stdout
