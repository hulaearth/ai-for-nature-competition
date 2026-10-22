import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';

const identity='AGE-SECRET-KEY-1'+'A'.repeat(59)+'\n'; // Synthetic, not an age credential.
const plan={not_before_utc:'2026-10-24T11:30:00Z',expires_utc:'2026-10-24T15:30:00Z',identity_sha256:createHash('sha256').update(identity).digest('hex')};
const config={competition_id:'synthetic-key-ui',dataset_release:'synthetic-data'};
const publication={...config,not_before_utc:plan.not_before_utc,published_at_utc:plan.not_before_utc,identity_sha256:plan.identity_sha256,identity};
const script=fs.readFileSync(new URL('../site/app.js',import.meta.url),'utf8');
const source=script.slice(script.indexOf('function testKeyRelease(config)'),script.indexOf('\nconst practiceLink'));

async function harness({primary,backup,now=Date.parse(plan.not_before_utc)+1000}){
  const nodes=new Map(),calls=[],downloads=[],timers=[];
  for(const id of ['status','identity','value','copy','refresh','download'])nodes.set('#test-key-'+id,{textContent:'',hidden:true,href:'',listeners:{},addEventListener(k,f){this.listeners[k]=f;},removeAttribute(){}});
  const fetch=async url=>{calls.push(url);const data=url.startsWith('./')?primary:backup;if(data instanceof Error)throw data;return {ok:!!data,json:async()=>structuredClone(data)};};
  class Clock extends Date{static now(){return now;}}
  const crypto={subtle:{digest:async(_kind,bytes)=>Uint8Array.from(createHash('sha256').update(bytes).digest()).buffer}};
  const run=new Function('$','BUNDLED_DATA','fetch','Date','crypto','setInterval','clearInterval','Blob','URL','config',source+';testKeyRelease(config);');
  run(s=>nodes.get(s),{'test-key-plan.json':plan},fetch,Clock,crypto,f=>timers.push(f),()=>{},Blob,{createObjectURL(blob){downloads.push(blob);return 'blob:verified-key';}},config);
  await new Promise(resolve=>setImmediate(resolve));
  return {nodes,calls,downloads,timers};
}

test('key falls back to GitHub and downloads the verified bytes locally',async()=>{
  const h=await harness({primary:null,backup:publication});
  assert.equal(h.calls.length,2);assert.match(h.calls[1],/^https:\/\/raw\.githubusercontent\.com\//);
  assert.equal(h.nodes.get('#test-key-identity').textContent,identity);
  assert.equal(h.nodes.get('#test-key-value').hidden,false);
  assert.equal(h.nodes.get('#test-key-download').href,'blob:verified-key');
  assert.equal(h.nodes.get('#test-key-download').download,'test-release-key.agekey');
  assert.equal(await h.downloads[0].text(),identity);
});

test('a valid primary release needs no backup request',async()=>{
  const h=await harness({primary:publication,backup:null});
  assert.equal(h.calls.length,1);assert.equal(h.downloads.length,1);
});

test('the page neither requests nor displays a key before release',async()=>{
  const h=await harness({primary:publication,backup:publication,now:Date.parse(plan.not_before_utc)-1});
  assert.equal(h.calls.length,0);assert.equal(h.downloads.length,0);assert.equal(h.nodes.get('#test-key-value').hidden,true);
});

test('bad fingerprints and publication times never expose an identity',async()=>{
  for(const bad of [{identity_sha256:'0'.repeat(64)},{identity:identity.replaceAll('A','B')},{published_at_utc:'2026-10-24T11:29:59Z'},{published_at_utc:'2026-10-24T15:30:01Z'},{competition_id:'another-event'}]){
    const data={...publication,...bad};const h=await harness({primary:data,backup:data});
    assert.equal(h.downloads.length,0);assert.equal(h.nodes.get('#test-key-identity').textContent,'');assert.equal(h.nodes.get('#test-key-value').hidden,true);
  }
});

test('a stale primary does not prevent verification of the current backup',async()=>{
  const h=await harness({primary:{...publication,identity_sha256:'0'.repeat(64)},backup:publication});
  assert.equal(h.calls.length,2);assert.equal(h.downloads.length,1);
});
