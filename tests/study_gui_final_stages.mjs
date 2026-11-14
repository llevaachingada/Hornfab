import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source = readFileSync(process.argv[2], 'utf8');
const {renderStudyPanel} = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const study = {id:'study1', revision:1, spec:{policy:{proposal_policy:'scalar'}}};
const hash = 'a'.repeat(64);
const execute = renderStudyPanel(study, {phase:'execute', revision:1, status:'unknown', data:{actions:[
  {kind:'package', enabled:true},
  {kind:'launch', enabled:true, package_hash:hash, package_revision:1}
]}});
assert.match(execute, /data-study-action="0">/);
assert.match(execute, /data-study-action="1">/);
assert.match(execute, /\/api\/studies\/study1\/export/);
const decide = renderStudyPanel(study, {phase:'decide', revision:1, status:'missing', data:{actions:[
  {kind:'decision', enabled:true, allowed_outcomes:['inconclusive'], reason:'Verification missing'}
]}});
assert.match(decide, /data-study-action="0">/);
assert.match(decide, /option value="inconclusive"/);
assert.doesNotMatch(decide, /option value="accept"/);
const propose = renderStudyPanel(study, {phase:'propose', revision:1, status:'unknown', data:{
  candidates:[{id:'candidate1', j:{j_mean:3, j_lower:-1, j_upper:7}}]
}});
assert.match(propose, /3 \[-1, 7\] J/);
console.log('study final stages ok');
