import {ownedTeams,isCaptain} from './registration.js';
let memberView='',invitationView='';
let $=s=>document.querySelector(s);
const text=(tag,value)=>{const node=document.createElement(tag);node.textContent=value;return node;};

export function renderWorkspace({teams,feed,subject,config,onAction,getBusy,query}){
 if(query)$=query;
 const team=ownedTeams(teams,subject)[0],captain=isCaptain(team,subject);
 $('#workspace').hidden=!team;
 if(team){
  if($('#workspace').previousElementSibling?.id!==$('#incoming-panel').id)$('#incoming-panel').after($('#workspace'));
  const used=feed.entries.filter(e=>e.team_slug===team.slug&&e.status==='accepted'&&e.channel==='final').length;
  $('#workspace-summary').textContent=`${team.name} · You are ${captain?'the captain':'a team member'}. ${used}/${config.max_final_submissions} accepted predictions used by the whole team.`;
  $('#invite-form').hidden=!captain;
  const identity=JSON.stringify([team,subject]);
  if(identity!==memberView){
   memberView=identity;const list=$('#account-list');list.replaceChildren();
   list.append(text('li',team.hf_id===subject?'Captain (you)':team.hf_username?'@'+team.hf_username+' · Captain':'Captain'));
   for(const member of team.member_accounts??[]){
    const row=text('li',`@${member.hf_username}${member.hf_id===subject?' (you)':''} · can upload predictions `);
    if(captain){const remove=text('button','Remove member');remove.type='button';remove.className='membership-action';remove.addEventListener('click',()=>onAction('remove',member.hf_id,team.slug));row.append(remove);}
    list.append(row);
   }
   $('#workspace-role').textContent=captain?'You can invite teammates and choose any accepted team prediction as final.':'You can upload and inspect all team predictions. The captain chooses the final entry.';
  }
 }
 const invitations=(feed.invitations??[]).filter(i=>i.status==='pending'&&Date.parse(i.expires_at)>Date.now());
 const incoming=invitations.filter(i=>i.invitee_hf_id===subject);
 const outgoing=team?invitations.filter(i=>i.team_slug===team.slug):[];
 const state=JSON.stringify([incoming,outgoing,teams.map(t=>[t.slug,t.name]),subject,captain,team?.active]);
 $('#incoming-note').textContent=!subject?'Sign in above to see and accept invitations. You do not need to create another team.':incoming.length?'Accept an invitation below to share the team’s submission allowance.':'No pending invitations for this account. Ask your captain to invite your Hugging Face username.';
 if(state===invitationView)return;
 invitationView=state;const inbox=$('#incoming-list'),outbox=$('#outgoing-list');inbox.replaceChildren();outbox.replaceChildren();
 for(const invitation of incoming){
  const target=teams.find(t=>t.slug===invitation.team_slug);if(!target)continue;
  const row=document.createElement('div');row.className='invitation';row.append(text('h3',`Invitation to ${target.name}`));
  const label=document.createElement('label');label.className='check';const consent=document.createElement('input');consent.type='checkbox';consent.id='consent-'+invitation.id;label.append(consent,document.createTextNode('I agree to one competition team per account, the shared team submission allowance, and my Hugging Face account binding being public.'));row.append(label);
  const accept=text('button','Accept invitation');accept.type='button';accept.className='membership-action';accept.dataset.consent=consent.id;accept.disabled=true;
  consent.addEventListener('change',()=>{accept.disabled=getBusy()||!consent.checked;});
  accept.addEventListener('click',()=>{if(consent.checked)onAction('accept',invitation.id,target.slug);});row.append(accept,document.createTextNode(' '));
  const decline=text('button','Decline');decline.type='button';decline.className='membership-action secondary';decline.addEventListener('click',()=>onAction('decline',invitation.id,target.slug));row.append(decline);inbox.append(row);
 }
 for(const invitation of outgoing){
  const row=text('li',`@${invitation.hf_username} · waiting for acceptance `);
  if(captain){const revoke=text('button','Cancel invitation');revoke.type='button';revoke.className='membership-action';revoke.addEventListener('click',()=>onAction('revoke',invitation.id,team.slug));row.append(revoke);}
  outbox.append(row);
 }
}
