import {requireCompetition,safeReceipt} from './protocol.js';

// Race as well as abort: a provider that ignores cancellation must not lock UI.
export async function bounded(operation,{ms=12000,signal}={}){
 const controller=new AbortController();let timer,listener;
 const cancelled=new Promise((_,reject)=>{
  const stop=()=>{controller.abort();reject(new Error('Request cancelled or timed out.'));};
  listener=stop;if(signal?.aborted)stop();else signal?.addEventListener('abort',stop,{once:true});
  timer=setTimeout(stop,ms);
 });
 try{return await Promise.race([Promise.resolve().then(()=>{if(controller.signal.aborted)throw new Error('Request cancelled or timed out.');return operation(controller.signal);}),cancelled]);}
 finally{clearTimeout(timer);signal?.removeEventListener('abort',listener);}
}

// One in-flight request; never let an older provider snapshot replace new results.
export function receiptReader(config,{fetcher=fetch,ms=12000}={}){
 requireCompetition(config);let inflight=null,latest=null;
 return ()=>{
  if(inflight)return inflight;
  inflight=bounded(async signal=>{
   const url=`https://raw.githubusercontent.com/hulaearth/ai-for-nature-competition/main/site/receipts.json?t=${Date.now()}`;
   const response=await fetcher(url,{signal,cache:'no-store',credentials:'omit'});
   if(!response.ok)throw new Error('Status service unavailable.');
   const d=await response.json();
   if(d.competition!==config.competition_id||d.space_id!==config.space_id||d.schema!==2||!Array.isArray(d.entries)||!Array.isArray(d.requests)||!Array.isArray(d.teams))throw new Error('Receipt isolation check failed.');
   const time=d.updated_at===null?0:Date.parse(d.updated_at);
   if(!Number.isFinite(time))throw new Error('Invalid receipt timestamp.');
   if(latest&&time<latest.time)return {data:latest.data,stale:true};
   latest={data:d,time};return {data:d,stale:false};
  },{ms}).finally(()=>{inflight=null;});return inflight;
 };
}

// Deliberately persist metadata only, never file contents, envelopes or tokens.
export function pendingRecord(request,userId){
 return {id:request.id,userId,team:request.manifest.team_slug,kind:request.manifest.kind,channel:request.manifest.channel,createdAt:Date.now(),receiptNumber:null,stage:'uploading'};
}
export function savePending(storage,userId,records){
 try{storage.setItem(`aifn-pending:${userId}`,JSON.stringify(records.slice(-20).map(r=>({id:r.id,userId,team:r.team,kind:r.kind,channel:r.channel,createdAt:r.createdAt,receiptNumber:r.receiptNumber,stage:r.stage}))));}catch{/* Storage may be blocked; the in-memory receipt still works. */}
}
export function loadPending(storage,userId){
 try{return JSON.parse(storage.getItem(`aifn-pending:${userId}`)??'[]').filter(r=>r.userId===userId&&/^[a-f0-9-]{36}$/.test(r.id)&&['prediction','selection'].includes(r.kind)&&typeof r.team==='string'&&Number.isFinite(r.createdAt)&&Date.now()-r.createdAt<7*86400000&&(r.receiptNumber===null||Number.isSafeInteger(r.receiptNumber))).slice(-20);}catch{return [];}
}
export async function transfer(upload,params,{signal,ms=120000,onSettled=()=>{}}={}){
 try{return safeReceipt(await bounded(abortSignal=>upload({...params,abortSignal}),{signal,ms}));}
 finally{onSettled();}
}
