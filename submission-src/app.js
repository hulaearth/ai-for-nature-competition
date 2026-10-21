import {oauthLoginUrl,oauthHandleRedirect,uploadFiles} from '@huggingface/hub';
import {validateCSV,encryptCSV} from './envelope.js';
import {requireCompetition,prepareRequest,acceptanceMessage} from './protocol.js';
import {bounded,receiptReader,pendingRecord,loadPending,savePending,transfer} from './lifecycle.js';
const $=s=>document.querySelector(s),enc=new TextEncoder(),RAW='https://raw.githubusercontent.com/hulaearth/ai-for-nature-competition/main/site/';
let auth=null,config,key,teams=[],practiceIds,busy=false,pending=[],reader,refreshing=null,feed=null,view='',activeUpload=null,lastConfigRead=0,lastHealthRead=0;
const show=(message,error=false)=>{const el=$('#status');el.textContent=message;el.className=error?'status error':'status';};
async function data(name){return bounded(async signal=>{
 let response;try{response=await fetch(RAW+name+'?t='+Date.now(),{signal,cache:'no-store',credentials:'omit'});}catch{if(signal.aborted)throw Error();}
 if(!response?.ok)response=await fetch('./'+name,{signal,cache:'no-store',credentials:'omit'});
 if(!response.ok)throw new Error('Cannot load competition settings.');return response.json();
});}
function finalOpen(){const t=Date.now();return config?.hf_submissions_enabled&&config.final_submissions_enabled&&t>=Date.parse(config.test_release_utc)&&t<Date.parse(config.deadline_utc);}
function controls(){
 const current=auth&&Date.now()<auth.accessTokenExpiresAt.getTime(),team=teams.find(t=>t.active&&t.slug===$('#team').value&&t.hf_id===auth?.userInfo?.sub),final=$('#channel').value==='final';
 $('#submit').disabled=busy||!config?.hf_submissions_enabled||!current||!team||(final?!finalOpen()||team.practice_only:!config?.practice_enabled||Date.now()>=Date.parse(config.deadline_utc));$('#submit').textContent=busy?'Sending…':'Submit prediction';
 $('#logout').hidden=!auth;$('#logout').disabled=busy;$('#signin').hidden=!!auth;$('#cancel').hidden=!activeUpload;
 for(const id of ['team','channel','csv','sample'])$('#'+id).disabled=busy;
 $('#sample-label').hidden=!final;$('#sample').required=final;$('#final-label').hidden=!final;
 $('#identity').textContent=auth?`Signed in as ${auth.userInfo.preferred_username??auth.userInfo.name}.`:'Sign in with the Hugging Face account registered as your team’s captain.';
 $('#window-note').textContent=final?(finalOpen()?'Final predictions are open. Five accepted final entries per team; choose one for final evaluation.':'Final predictions are closed. They require the announced test release and organizer launch checks.'):'Practice checks the 120-row CSV, encryption and delivery. It uses no final scoring attempt and produces no model score.';
 document.querySelectorAll('#entries button').forEach(b=>b.disabled=busy||!current||!finalOpen());
}
function syncTeams(){
 const previous=$('#team').value;$('#team').replaceChildren();for(const t of teams.filter(t=>t.active&&t.hf_id===auth?.userInfo?.sub)){const o=document.createElement('option');o.value=t.slug;o.textContent=t.name;$('#team').append(o);}
 if([...$('#team').options].some(o=>o.value===previous))$('#team').value=previous;
 $('#team-note').textContent=auth&&!$('#team').options.length?'No approved team is linked to this account yet. Give the organizer your Hugging Face username; keep using the same captain account.':'';controls();
}
function cell(row,value){const c=document.createElement('td');c.textContent=String(value??'—');row.append(c);return c;}
function persist(){if(auth)savePending(sessionStorage,auth.userInfo.sub,pending);}
function render(){
 if(!feed)return;const mine=feed.entries.filter(e=>teams.some(t=>t.slug===e.team_slug&&t.hf_id===auth?.userInfo?.sub));
 const next=JSON.stringify([mine,feed.selected,auth?.userInfo?.sub]);
 if(view!==next){view=next;const body=$('#entries tbody');body.replaceChildren();for(const e of mine){const row=document.createElement('tr');cell(row,e.entry_id);cell(row,e.channel==='practice'?'Practice':'Final');cell(row,e.status);cell(row,e.public_score==null?'—':Number(e.public_score).toFixed(6));const chosen=feed.selected?.[e.team_slug]===e.entry_id;cell(row,chosen?'Final choice':e.reason??'');const action=cell(row,'');if(e.status==='accepted'&&e.channel==='final'&&!chosen){const b=document.createElement('button');b.type='button';b.textContent='Use for final';b.addEventListener('click',()=>sendSelection(e));action.append(b);}body.append(row);}}
 $('#empty').hidden=mine.length>0;const list=$('#pending');list.replaceChildren();for(const p of pending){const li=document.createElement('li');li.textContent=`${p.kind==='selection'?'Final choice':'Prediction'} ${p.receiptNumber?'HF-'+p.receiptNumber:p.id}: ${p.stage==='received'?'uploaded; waiting for evaluation':p.stage==='uploading'&&busy?'upload in progress':'upload not confirmed; check status before retrying'}.`;list.append(li);}
 $('#updated').textContent=feed.updated_at?`Results last published: ${new Date(feed.updated_at).toLocaleString()}.`:'Waiting for the first evaluator update.';controls();
}
function refresh(){
 if(refreshing)return refreshing;$('#refresh').disabled=true;$('#refresh').textContent='Checking…';$('#refresh-note').textContent='Checking published evaluation receipts…';
 refreshing=(async()=>{try{
  const result=await reader();feed=result.data;teams=feed.teams;syncTeams();let confirmed;
  pending=pending.filter(p=>{const r=feed.requests.find(r=>r.team_slug===p.team&&(r.request_id===p.id||r.pr_number===p.receiptNumber));if(!r||!['accepted','rejected'].includes(r.status))return true;confirmed={p,r};return false;});persist();render();
  $('#refresh-note').textContent=`Checked at ${new Date().toLocaleTimeString()}. ${result.stale?'An older provider snapshot was ignored.':pending.length?'Your upload is waiting for evaluation. Keep the receipt; refreshing does not resubmit it.':'Showing the latest published results.'}`;
  if(confirmed&&!busy){const {p,r}=confirmed;show(r.status==='accepted'?acceptanceMessage({kind:p.kind,channel:p.channel,team_slug:p.team},r,feed.selected):`Not accepted (${r.reason}). No accepted scoring attempt was used; your earlier final choice is unchanged.`,r.status==='rejected');}
  if(Date.now()-lastHealthRead>60000){lastHealthRead=Date.now();void data('worker-status.json').then(h=>{if(h.competition_id!==config.competition_id)return;const age=Date.now()-Date.parse(h.updated_at),published=Date.parse(feed?.updated_at);$('#worker-note').textContent=Number.isFinite(published)&&Date.now()-published<120000&&published>Date.parse(h.updated_at??'1970-01-01')?'Evaluation results were published recently. Accepted entries are saved; pending receipts will update here.':!Number.isFinite(age)?'Evaluator health has not been reported yet. Keep your receipt if a result is pending.':age>420000?'No recent evaluator health update. If your result is pending, keep the receipt and ask a conductor.':h.status==='retrying'?'The evaluator is retrying after a service problem. Keep your receipt; no resubmission is needed.':'Evaluator health checked recently. Uploaded requests are processed automatically.';}).catch(()=>{$('#worker-note').textContent='Evaluator health is unavailable. Existing results and receipts are kept.';});}
  if(Date.now()-lastConfigRead>60000){lastConfigRead=Date.now();void data('config.json').then(next=>{requireCompetition(next);config=next;controls();}).catch(()=>{});}
 }catch{$('#refresh-note').textContent='Status check failed or timed out. Your last results and receipt are kept. Try Refresh status again.';}
 finally{$('#refresh').disabled=false;$('#refresh').textContent='Refresh status';refreshing=null;}})();return refreshing;
}
async function login(){const cache={};const url=await oauthLoginUrl({scopes:'openid profile write-discussions',redirectUrl:location.origin+location.pathname,localStorage:cache});sessionStorage.setItem('aifn-pkce',JSON.stringify(cache));location.assign(url);}
function requireSession(){if(!auth||Date.now()>=auth.accessTokenExpiresAt.getTime())throw new Error('Sign in again; your temporary session expired.');}
async function send(request){
 requireSession();busy=true;const record=pendingRecord(request,auth.userInfo.sub);pending.push(record);persist();activeUpload=new AbortController();controls();render();show(request.manifest.kind==='selection'?'Sending your final choice…':'Uploading your encrypted prediction…');$('#receipt').textContent='Request ID: '+request.id;
 try{
  const receipt=await transfer(uploadFiles,{repo:{type:'space',name:config.space_id},accessToken:auth.accessToken,isPullRequest:true,commitTitle:`AIFN ${request.manifest.kind} ${request.id}`,commitDescription:request.receiptDescription,files:request.files,useWebWorkers:false,useXet:false},{signal:activeUpload.signal,onSettled:()=>{busy=false;activeUpload=null;controls();}});
  record.receiptNumber=receipt.number;record.stage='received';persist();$('#receipt').textContent=`Receipt HF-${receipt.number} · ${request.id}`;show(`HF-${receipt.number} uploaded. You can continue using this page while evaluation runs. A receipt confirms delivery; acceptance appears below.`);
 }catch{record.stage='unconfirmed';persist();show('Upload not confirmed: transfer failed, timed out or was stopped. It may still have arrived. Check status before trying again and keep the request ID below.',true);}
 finally{busy=false;activeUpload=null;controls();render();}void refresh();
}
function safeError(e){const m=String(e?.message??'');return /^(CSV |Expected |Use exactly |Every |The row IDs |Invalid CSV |Unexpected character |Unclosed CSV |Choose |Select |Competition |Final |Practice |Sign in |Sign-in |Keep the method |Encrypted upload |Invalid request |Sample CSV |Cannot load )/.test(m)?m.slice(0,300):'The request could not be completed. Check status, then sign in again if needed.';}
async function sendSelection(entry){if(busy)return;busy=true;controls();try{requireSession();if(!finalOpen())throw new Error('Final selections are closed.');await send(await prepareRequest({config,team:entry.team_slug,kind:'selection',channel:'final',targetEntry:entry.entry_id,method:$('#method').value.trim()}));}catch(e){show(safeError(e),true);}finally{busy=false;controls();}}
$('#form').addEventListener('submit',async event=>{event.preventDefault();if(busy)return;busy=true;controls();show('Checking and encrypting on your computer…');try{
 requireSession();if(!config.hf_submissions_enabled)throw new Error('Competition upload is temporarily disabled. Ask a conductor about backup delivery.');const channel=$('#channel').value;if(channel==='final'&&!finalOpen())throw new Error('Final predictions are closed.');if(channel==='practice'&&!config.practice_enabled)throw new Error('Practice is closed.');
 await new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0)));const file=$('#csv').files[0];if(!file)throw new Error('Choose your prediction CSV first.');if(file.size>config.max_csv_bytes)throw new Error('CSV exceeds the 8 MB limit.');const bytes=new Uint8Array(await file.arrayBuffer());let expected=practiceIds;
 if(channel==='final'){const sample=$('#sample').files[0];if(!sample)throw new Error('Choose the supplied final sample CSV for the row-ID check.');if(sample.size>config.max_csv_bytes)throw new Error('Sample CSV exceeds 8 MB.');expected=validateCSV(new Uint8Array(await sample.arrayBuffer()),config.expected_rows);}
 validateCSV(bytes,channel==='final'?config.expected_rows:120,expected);const envelope=await encryptCSV(bytes,$('#team').value,channel,key,config);await send(await prepareRequest({config,team:$('#team').value,kind:'prediction',channel,envelope,makeFinal:$('#make-final').checked,method:$('#method').value.trim()}));
 }catch(e){show(safeError(e),true);}finally{busy=false;controls();}});
$('#cancel').addEventListener('click',()=>activeUpload?.abort());$('#logout').addEventListener('click',()=>{auth=null;pending=[];sessionStorage.removeItem('aifn-pkce');syncTeams();render();show('Signed out. No access token is stored on this device.');});$('#refresh').addEventListener('click',()=>{if(reader)void refresh();});$('#channel').addEventListener('change',controls);$('#team').addEventListener('change',controls);
(async()=>{try{
 [config,key]=await Promise.all([data('config.json'),data('submission-key.json')]);requireCompetition(config);reader=receiptReader(config);lastConfigRead=Date.now();practiceIds=await bounded(async signal=>{const r=await fetch('./practice_submission.csv',{signal,credentials:'omit'});if(!r.ok)throw new Error('Practice sample unavailable.');return validateCSV(enc.encode(await r.text()),120);});$('#signin').href=location.origin+location.pathname+'?signin=1';
 let cancelled=false;if(new URLSearchParams(location.search).has('error')){cancelled=true;sessionStorage.removeItem('aifn-pkce');history.replaceState({},'',location.pathname);}
 else if(new URLSearchParams(location.search).has('code')){const p=JSON.parse(sessionStorage.getItem('aifn-pkce')??'null');if(!p?.nonce||!p?.codeVerifier)throw new Error('Sign-in session missing. Start again in this tab.');auth=await oauthHandleRedirect({nonce:p.nonce,codeVerifier:p.codeVerifier,redirectedUrl:location.href});sessionStorage.removeItem('aifn-pkce');history.replaceState({},'',location.pathname);pending=loadPending(sessionStorage,auth.userInfo.sub);setTimeout(()=>{auth=null;pending=[];syncTeams();render();show('Sign-in expired. Sign in again to upload.');},Math.max(0,auth.accessTokenExpiresAt.getTime()-Date.now()));}
 else if(new URLSearchParams(location.search).has('signin')){await login();return;}
 syncTeams();show(cancelled?'Sign-in was cancelled or declined. You can sign in again when ready.':auth?'Choose your prediction CSV, then submit.':'Ready. Sign in to submit a Practice file.');void refresh();setInterval(()=>void refresh(),15000);
 }catch(e){show(safeError(e),true);$('#submit').disabled=true;}})();
