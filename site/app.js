import {encryptCSV, validateCSV, parseCSV} from "./envelope.js";
const REPO = "https://github.com/hulaearth/ai-for-nature-competition";
const RAW = "https://raw.githubusercontent.com/hulaearth/ai-for-nature-competition/main/site/";
const $ = selector => document.querySelector(selector);
const make = (tag, text, cls) => {const e=document.createElement(tag); if(text!==undefined)e.textContent=String(text); if(cls)e.className=cls; return e;};
const BUNDLED_DATA = JSON.parse($("#site-data")?.textContent || "{}");

async function data(name) {
  // Bundled copies keep the Space useful while GitHub is private or temporarily unavailable.
  try {const r=await fetch(RAW+name+"?v="+Math.floor(Date.now()/30000),{cache:"no-store",credentials:"omit",signal:AbortSignal.timeout(4000)});if(r.ok)return await r.json();} catch {}
  if(Object.hasOwn(BUNDLED_DATA,name))return BUNDLED_DATA[name];
  const r=await fetch("./"+name,{cache:"no-store",credentials:"same-origin",signal:AbortSignal.timeout(4000)});if(!r.ok)throw new Error("Competition information is temporarily unavailable.");return r.json();
}
function date(value) {return value?new Date(value).toLocaleString(undefined,{timeZone:"Europe/Berlin",timeZoneName:"short"}):"To be announced";}
function isFinalOpen(c) {const t=Date.now();return c.final_submissions_enabled&&c.test_release_utc&&c.deadline_utc&&t>=Date.parse(c.test_release_utc)&&t<Date.parse(c.deadline_utc);}

function renderConfig(c) {
  document.querySelectorAll("[data-materials]").forEach(e=>e.textContent=date(c.materials_release_utc));
  document.querySelectorAll("[data-start]").forEach(e=>e.textContent=date(c.start_utc));
  document.querySelectorAll("[data-release]").forEach(e=>e.textContent=date(c.test_release_utc));
  document.querySelectorAll("[data-deadline]").forEach(e=>e.textContent=date(c.deadline_utc));
  const conversion={"baseline-relative-v1":"Matching the frozen shipped reference earns 15/50 model points. Improvements of +0.02, +0.05, +0.10 and +0.15 AP earn 19.7, 26.7, 38.3 and 50. Below the reference, points rise from 0 at constant-score AP to 15 at the baseline. Full formula and caps follow."};
  if(conversion[c.jury_performance_points])document.querySelectorAll("[data-performance-points]").forEach(e=>e.textContent=conversion[c.jury_performance_points]);
  document.querySelectorAll("[data-status]").forEach(e=>e.textContent=isFinalOpen(c)?"Final predictions open":c.deadline_utc&&Date.now()>=Date.parse(c.deadline_utc)?"Submissions closed":"Registration and preparation");
  document.querySelectorAll("[data-drive]").forEach(e=>{
    if(c.drive_url?.startsWith("https://drive.google.com/")){e.href=c.drive_url;e.target="_blank";e.rel="noopener noreferrer";e.textContent="Open Challenge data ↗";e.removeAttribute("aria-disabled");}
  });
  document.querySelectorAll("[data-drive-address]").forEach(e=>{if(c.drive_url?.startsWith("https://drive.google.com/"))e.textContent=c.drive_url;});
  document.querySelectorAll("[data-copy-drive]").forEach(e=>{
    e.disabled=!c.drive_url?.startsWith("https://drive.google.com/");
    e.onclick=async()=>{try{await navigator.clipboard.writeText(c.drive_url);$("[data-drive-copy-status]").textContent="Link copied. Paste it into a new browser tab.";}catch{$("[data-drive-copy-status]").textContent="Select and copy the address above, then open it in a new browser tab.";}};
  });
  document.querySelectorAll("[data-data-readiness]").forEach(e=>e.textContent=c.data_ready?"Challenge data is ready. Use your approved Google account and verify SHA256SUMS after downloading.":"Challenge data upload and participant access checks are in progress. The folder link is ready; access may still require organizer approval.");
  const presentationClosed=c.deadline_utc&&Date.now()>=Date.parse(c.deadline_utc);
  const presentationOpen=!presentationClosed&&c.presentation_form_open&&c.presentation_form_url?.startsWith("https://docs.google.com/forms/");
  document.querySelectorAll("[data-presentation]").forEach(e=>{
    if(presentationOpen){e.href=c.presentation_form_url;e.textContent="Upload your final presentation ↗";e.target="_blank";e.rel="noopener";e.removeAttribute("aria-disabled");}
    else{e.href="#";e.setAttribute("aria-disabled","true");e.textContent=presentationClosed?"Presentation deadline passed":"Presentation form not yet open";}
  });
  document.querySelectorAll("[data-presentation-status]").forEach(e=>e.textContent=presentationClosed?"The 17:30 deadline has passed. The organizer uses the latest complete valid response received before closure.":presentationOpen?"Upload through Google Forms. A Google sign-in is required; response files are private to the organizers. Retain the confirmation page.":"The form is prepared but unpublished. Participant access and the live upload link still need to be opened by the organizer.");
  document.querySelectorAll("[data-starter]").forEach(e=>{
    if(c.starter_released){e.href="https://github.com/hulaearth/ai-for-nature-codebase/tree/"+c.starter_ref;e.textContent="Open the starter code ↗";e.removeAttribute("aria-disabled");}
  });
}

async function board() {
  const root=$("#board");if(!root)return;
  try {
    const d=await data("leaderboard.json");root.replaceChildren();
    $("#board-type").textContent=d.private_results_released?"Final private results":"Provisional public results";
    if(!d.teams.length){root.append(make("div","No scored predictions yet. Practice checks do not appear in the leaderboard.","empty"));return;}
    const table=make("table");table.setAttribute("aria-label","Competition standings");
    const head=make("thead"),hr=make("tr");for(const x of ["Rank","Team",d.private_results_released?"Private macro AP":"Public macro AP",...(d.private_results_released?["Model points / 50"]:[]),"Accepted / 5","Prediction"]){const h=make("th",x);h.scope="col";hr.append(h);}head.append(hr);table.append(head);
    const body=make("tbody");for(const t of d.teams){const r=make("tr");r.append(make("td",t.rank),make("td",t.name),make("td",Number(t.score).toFixed(6)),...(d.private_results_released?[make("td",Number.isFinite(t.model_points_50)?Number(t.model_points_50).toFixed(2):"Pending")]:[]),make("td",t.accepted_submissions));const cell=make("td"),a=make("a","#"+t.submission_issue);a.href=REPO+"/issues/"+Number(t.submission_issue);cell.append(a);r.append(cell);body.append(r);}table.append(body);root.append(table);
    $("#board-updated").textContent="Last published: "+date(d.updated_at)+". Exact AP ties favor the earlier relevant accepted prediction. AP is compared at full precision and displayed to six decimals."+(d.award_scoring?" Frozen reference private AP: "+Number(d.award_scoring.reference_private_ap).toFixed(6)+". Model points use baseline-relative-v1; the overall jury award is separate.":"");
  } catch(error){root.replaceChildren(make("div","Standings could not be refreshed. Try again shortly.","notice"));}
}

async function uploader(config) {
  const form=$("#prediction-form");if(!form)return;
  const status=$("#submission-status");let key,teams,currentBlobUrl=null,currentEnvelopeText="";
  try{[key,teams]=await Promise.all([data("submission-key.json"),data("teams.json")]);}catch(error){status.textContent=error.message;return;}
  const select=$("#team");for(const t of teams.teams.filter(t=>t.active)){const o=make("option",`${t.name} · ${t.slug}`);o.value=t.slug;select.append(o);}
  if(!teams.teams.some(t=>t.active))status.textContent="Register first. Your approved team will appear here after an organizer adds it.";
  function controls(){const final=$("#channel").value==="final";$("#encrypt").disabled=!select.value||(final&&!isFinalOpen(config));$("#window-note").textContent=final?(isFinalOpen(config)?"Final-test predictions are open. Use the decrypted competition sample submission.":"Final-test encryption opens at the announced test release time."):"Practice uses the 120-row sample below. It checks format and delivery, not model performance.";}
  form.addEventListener("change",()=>{controls();$("#after-encrypt").hidden=true;status.textContent="";currentEnvelopeText="";$("#encrypted-copy-status").textContent="";$("#encrypted-manual").hidden=true;});controls();
  $("#copy-encrypted").addEventListener("click",async()=>{
    if(!currentEnvelopeText)return;
    $("#encrypted-manual").hidden=false;$("#encrypted-text").textContent=currentEnvelopeText;$("#encrypted-text").value=currentEnvelopeText;
    try{await navigator.clipboard.writeText(currentEnvelopeText);$("#encrypted-copy-status").textContent="Encrypted JSON copied. Save it in a file ending .encrypted.json, then attach that file on GitHub.";}
    catch{$("#encrypted-manual").hidden=false;$("#encrypted-text").value=currentEnvelopeText;$("#encrypted-copy-status").textContent="Select the encrypted text below and save it in a .encrypted.json file, then attach it on GitHub.";}
  });
  form.addEventListener("submit",async event=>{
    event.preventDefault();$("#encrypt").disabled=true;$("#after-encrypt").hidden=true;status.textContent="Checking and encrypting locally…";
    try{
      const file=$("#csv").files[0],channel=$("#channel").value,teamSlug=select.value;if(!file)throw new Error("Select your prediction CSV.");
      if(channel==="final"&&!isFinalOpen(config))throw new Error("Final-test submissions are closed.");
      if(file.size>5_000_000)throw new Error("CSV exceeds 5 MB.");
      const bytes=new Uint8Array(await file.arrayBuffer());let expected=null;
      if(channel==="practice"){
        let practice=BUNDLED_DATA["practice_submission.csv"];
        if(!practice){const response=await fetch("./practice_submission.csv");if(!response.ok)throw new Error("Practice sample unavailable.");practice=await response.text();}
        expected=new Set(parseCSV(practice).slice(1).map(r=>r[0]));
      }
      const sample=$("#sample").files[0];if(sample){if(sample.size>5_000_000)throw new Error("Sample exceeds 5 MB.");const sampleBytes=new Uint8Array(await sample.arrayBuffer());expected=validateCSV(sampleBytes,channel==="final"?35510:120);}
      validateCSV(bytes,channel==="final"?35510:120,expected);
      const envelope=await encryptCSV(bytes,teamSlug,channel,key,config);
      currentEnvelopeText=JSON.stringify(envelope);
      const blob=new Blob([currentEnvelopeText],{type:"application/json"});
      if(currentBlobUrl)URL.revokeObjectURL(currentBlobUrl);
      currentBlobUrl=URL.createObjectURL(blob);
      const download=$("#download-encrypted");download.href=currentBlobUrl;download.download=`aifn-${teamSlug}-${envelope.submission_id}.encrypted.json`;
      $("#issue-link").href=REPO+`/issues/new?template=${channel==="final"?"prediction":"practice"}.yml&title=`+encodeURIComponent(`[${channel==="final"?"Prediction":"Practice"}] ${teamSlug}`)+"&team-slug="+encodeURIComponent(teamSlug);
      $("#after-encrypt").hidden=false;status.textContent=`Encrypted ${bytes.length.toLocaleString()} bytes. Use the download button below, then attach the file on GitHub. Your CSV has not been uploaded. CSV SHA256: ${envelope.csv_sha256}`;
    }catch(error){status.textContent=error.message||"Encryption failed. Contact an organizer.";}finally{controls();}
  });
}

function testKeyRelease(config) {
  const plan=BUNDLED_DATA['test-key-plan.json'],status=$('#test-key-status');
  if(!plan||!status)return;
  const scheduled=new Date(plan.not_before_utc).toLocaleString('de-DE',{timeZone:'Europe/Berlin',timeZoneName:'short'});
  const pending='Scheduled for '+scheduled+' (German time). The organizer publishes the key at release time; this page checks automatically.';
  status.textContent=pending;
  let identity=null,busy=false;
  async function check() {
    if(busy||identity)return;busy=true;
    try {
      const r=await fetch('./test-key-release.json',{cache:'no-store',credentials:'same-origin',signal:AbortSignal.timeout(4000)});
      if(!r.ok){status.textContent=Date.now()<Date.parse(plan.not_before_utc)?pending:'The key is not available in this view yet. Check again, or open the key download after the announced release time.';return;}
      const released=await r.json();
      if(released.competition_id!==config.competition_id||released.dataset_release!==config.dataset_release||released.not_before_utc!==plan.not_before_utc||released.identity_sha256!==plan.identity_sha256||!Number.isFinite(Date.parse(released.published_at_utc))||Date.parse(released.published_at_utc)<Date.parse(plan.not_before_utc))throw new Error('Release metadata mismatch');
      if(typeof released.identity!=='string'||!/^AGE-SECRET-KEY-1[A-Z0-9]+\n$/.test(released.identity))throw new Error('Invalid age identity');
      const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(released.identity)))].map(b=>b.toString(16).padStart(2,'0')).join('');
      if(hash!==plan.identity_sha256)throw new Error('Identity fingerprint mismatch');
      identity=released.identity;$('#test-key-identity').textContent=identity;$('#test-key-value').hidden=false;$('#test-key-copy').hidden=false;
      status.textContent='The verified test-data unlock key is available. Download the age identity file or copy the key below.';
    }catch{status.textContent='The key could not be verified in this view. Check again or use the key download after release; contact a conductor if the problem persists.';}
    finally{busy=false;}
  }
  $('#test-key-refresh').addEventListener('click',check);
  $('#test-key-copy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(identity);$('#test-key-copy').textContent='Copied';}catch{status.textContent='Copy was unavailable. Use the key download or select the displayed key.';}});
  check();
  const timer=setInterval(()=>{if(identity){clearInterval(timer);return;}if(Date.now()>=Date.parse(plan.not_before_utc)-60000)check();},5000);
}

const practiceLink=document.querySelector('a[href="practice_submission.csv"]');
if(practiceLink&&BUNDLED_DATA["practice_submission.csv"]){practiceLink.href=URL.createObjectURL(new Blob([BUNDLED_DATA["practice_submission.csv"]],{type:"text/csv"}));practiceLink.download="practice_submission.csv";}
try{const config=await data("config.json");
  // This endpoint is created server-side at release and survives later scoring syncs.
  // Repository/Space visibility enforces the embargo; the browser clock does not.
  try{const released=await data("materials-release.json");
    if(released.competition_id===config.competition_id&&released.dataset_release===config.dataset_release&&released.not_before_utc===config.materials_release_utc&&released.starter_ref===config.starter_ref&&Date.parse(released.published_at_utc)>=Date.parse(config.materials_release_utc))config.starter_released=true;
  }catch{}
  renderConfig(config);testKeyRelease(config);await uploader(config);}catch(error){document.querySelectorAll("[data-status]").forEach(e=>e.textContent="Schedule unavailable");}
$("#refresh")?.addEventListener("click",board);await board();
document.querySelectorAll('a[aria-disabled="true"]').forEach(a=>a.addEventListener("click",e=>e.preventDefault()));
