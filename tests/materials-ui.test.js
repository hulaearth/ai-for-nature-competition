import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

test('open pages enable guide and starter automatically; enabled links remain clickable',async()=>{
  const releaseTime='2026-10-24T08:00:00Z';
  const config={competition_id:'synthetic-ui',dataset_release:'synthetic-data',
    materials_release_utc:releaseTime,starter_ref:'synthetic-ref',starter_released:false,
    space_id:'synthetic-space',scoring_policy:{baseline:{starter_commit:'a'.repeat(40)}}};
  function link(){return {attrs:{'aria-disabled':'true'},href:'#',listeners:[],
    setAttribute(name,value){this.attrs[name]=value;},removeAttribute(name){delete this.attrs[name];},
    getAttribute(name){return this.attrs[name]??null;},addEventListener(name,callback){if(name==='click')this.listeners.push(callback);}};}
  const guide=link(),starter=link();let published=false;const timers=[];
  const document={
    querySelector(selector){return selector==='#site-data'?{textContent:JSON.stringify({'config.json':config})}:null;},
    querySelectorAll(selector){
      if(selector==='[data-guide]')return [guide];
      if(selector==='[data-starter]')return [starter];
      if(selector==='a[aria-disabled="true"]')return [guide,starter].filter(x=>x.getAttribute('aria-disabled')==='true');
      return [];
    }
  };
  const fetch=async url=>{
    if(url.includes('config.json'))return {ok:true,json:async()=>structuredClone(config)};
    if(url==='./materials-release.json')return {ok:published,json:async()=>({
      competition_id:config.competition_id,dataset_release:config.dataset_release,
      not_before_utc:releaseTime,published_at_utc:releaseTime,starter_ref:config.starter_ref,
      starter_commit:config.scoring_policy.baseline.starter_commit})};
    throw new Error('Unexpected network request in isolated UI test');
  };
  class Clock extends Date{static now(){return Date.parse(releaseTime)+1000;}}
  const source=fs.readFileSync(new URL('../site/app.js',import.meta.url),'utf8').replace(/^import .*$/gm,'');
  const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
  const run=new AsyncFunction('document','fetch','Date','setInterval','clearInterval',source);
  await run(document,fetch,Clock,callback=>{timers.push(callback);return timers.length;},()=>{});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(guide.getAttribute('aria-disabled'),'true');
  let prevented=false;guide.listeners[0]({preventDefault(){prevented=true;}});assert.equal(prevented,true);
  assert.equal(timers.length,1);
  published=true;timers[0]();await new Promise(resolve=>setImmediate(resolve));
  assert.equal(guide.getAttribute('aria-disabled'),null);
  assert.match(guide.href,/synthetic-space\/resolve\/main\/participant-guide\.pdf/);
  assert.match(starter.href,/tree\/synthetic-ref$/);
  prevented=false;guide.listeners[0]({preventDefault(){prevented=true;}});assert.equal(prevented,false);
});
