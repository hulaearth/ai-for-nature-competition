export const EVENT_ID = 'ai-for-nature-2026';
export const EVENT_SPACE = 'HulaEarth/ai-for-nature-hula-earth';
export const ENVELOPE_PART_BYTES = 4_000_000;
export const REQUEST_FIELDS = ['schema','competition','channel','request_id','kind','team_slug','make_final','target_entry','method_reference','envelope_sha256','envelope_bytes'];
export function requireCompetition(config) {
  if (config.competition_id !== EVENT_ID || config.space_id !== EVENT_SPACE) throw new Error('Competition destination check failed.');
}
export async function sha256(bytes) {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
}
export async function prepareRequest({config,team,kind,channel='final',envelope,makeFinal=false,targetEntry=null,method=''}) {
  requireCompetition(config);
  if (!['prediction','selection','registration','membership','team_admin'].includes(kind)) throw new Error('Invalid request type.');
  if (!/^[a-z0-9][a-z0-9-]{1,39}$/.test(team)) throw new Error('Choose an approved team.');
  if (method.length>2000) throw new Error('Keep the method reference below 2,000 characters.');
  if (kind==='selection' && (! /^(HF|GH)-[1-9][0-9]{0,8}$/.test(targetEntry??''))) throw new Error('Choose an accepted entry.');
  const control=['registration','membership','team_admin'].includes(kind);if(control)channel=kind;
  if(!['practice','final','registration','membership','team_admin'].includes(channel)||kind==='selection'&&channel!=='final')throw new Error('Invalid request channel.');
  const payload = kind!=='selection'?new TextEncoder().encode(JSON.stringify(envelope)):null;
  if (kind!=='selection' && (!envelope||payload.length>(control?16384:config.max_envelope_bytes))) throw new Error('Encrypted upload exceeds the limit.');
  const id=crypto.randomUUID();
  const manifest={schema:2,competition:EVENT_ID,channel,request_id:id,kind,team_slug:team,make_final:!control&&kind==='prediction'&&channel==='final'?!!makeFinal:false,target_entry:kind==='selection'?targetEntry:null,method_reference:control?'':method,envelope_sha256:payload?await sha256(payload):null,envelope_bytes:payload?.length??0};
  const parts=[];
  if(payload)for(let start=0,index=0;start<payload.length;start+=ENVELOPE_PART_BYTES,index++){
    const name=payload.length<=ENVELOPE_PART_BYTES?'prediction.json':`prediction.${String(index).padStart(3,'0')}.json`;
    parts.push({path:`requests/${id}/${name}`,content:new Blob([payload.slice(start,start+ENVELOPE_PART_BYTES)],{type:'application/json'})});
  }
  return {id,manifest,receiptDescription:'AIFN-RECEIPT-V1 sha256='+await sha256(new TextEncoder().encode(JSON.stringify(manifest))),files:[{path:`requests/${id}/request.json`,content:new Blob([JSON.stringify(manifest)])},...parts]};
}
export function safeReceipt(result) {
  if (!result?.pullRequestUrl) throw new Error('Upload finished without a verifiable receipt. Refresh your entries before retrying.');
  const u=new URL(result.pullRequestUrl);
  const prefix=`/spaces/${EVENT_SPACE}/discussions/`;
  if(u.origin!=='https://huggingface.co'||!u.pathname.startsWith(prefix)||!/^\d+$/.test(u.pathname.slice(prefix.length))) throw new Error('Unexpected receipt destination.');
  return {number:Number(u.pathname.slice(prefix.length)),url:u.href,commit:result.commit?.oid??null};
}
export function acceptanceMessage(manifest,record,selected){
 if(manifest.kind==='registration')return 'Team confirmed. Invite teammates from Register, or continue to Submit.';
 if(manifest.kind==='team_admin')return 'Organizer change confirmed.';
 if(manifest.kind==='membership')return ({invite:'Invitation ready. Share the Register link; no email notification is sent.',accept:'You joined the team and can upload predictions.',decline:'Invitation declined.',revoke:'Invitation canceled.',remove:'Member access removed; team entries and allowance are preserved.'}[record.action]??'Team membership updated.');
 if(manifest.kind==='selection')return `Final choice confirmed: ${selected?.[manifest.team_slug]??'check your entries below'}.`;
 if(manifest.channel==='practice')return `Practice ${record.entry_id} accepted. The complete CSV and encryption passed; no final scoring attempt was used.`;
 return `Prediction ${record.entry_id} accepted${selected?.[manifest.team_slug]===record.entry_id?' and selected for final':''}.`;
}
