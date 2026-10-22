const text=(tag,value)=>{const n=document.createElement(tag);n.textContent=String(value);return n;};
const entry=value=>value==null?'Not chosen':String(value).startsWith('HF-')||String(value).startsWith('GH-')?String(value):'#'+value;

export function renderBoard(root,{rows,selected={},final=false,limit=5}){
 root.replaceChildren();
 if(!rows.length){root.append(text('p','No accepted scored predictions yet.'));return;}
 const table=document.createElement('table');table.setAttribute('aria-label',final?'Final private leaderboard':'Provisional public leaderboard');
 const head=document.createElement('thead'),hr=document.createElement('tr');
 const points=final&&rows.some(r=>Number.isFinite(r.model_points_50));
 for(const title of ['Rank','Team',final?'Private AP':'Best public AP',...(points?['Model / 50']:[]),'Accepted',final?'Evaluated entry':'Best public entry',...(!final?['Final choice']:[])]){const th=text('th',title);th.scope='col';hr.append(th);}
 head.append(hr);table.append(head);const body=document.createElement('tbody');
 for(const row of rows){
  const tr=document.createElement('tr');
  for(const value of [row.rank,row.name,Number(row.score).toFixed(6),...(points?[Number.isFinite(row.model_points_50)?Number(row.model_points_50).toFixed(2):'Pending']:[]),`${row.accepted_submissions} / ${limit}`,entry(row.submission_issue),...(!final?[entry(selected[row.slug])]:[])])tr.append(text('td',value));
  body.append(tr);
 }
 table.append(body);root.append(table);
}

export function previewSnapshot(data,{final=false,earlier=false}={}){
 if(data.example_only!==true)throw new Error('Example leaderboard required.');
 const scenario=earlier?data.earlier:data.latest;
 return {rows:(final?scenario.final:scenario.public).teams,selected:scenario.selected,final,limit:data.max_submissions};
}

export async function initLeaderboardPreview(){
 const root=document.querySelector('#preview-board');if(!root)return;
 try{
  const response=await fetch('./leaderboard-preview.json',{credentials:'omit'});if(!response.ok)throw new Error();
  const data=await response.json();let final=false;
  const publicButton=document.querySelector('#preview-public'),finalButton=document.querySelector('#preview-final'),choice=document.querySelector('#preview-choice');
  const update=()=>{
   publicButton.setAttribute('aria-pressed',String(!final));finalButton.setAttribute('aria-pressed',String(final));
   renderBoard(root,previewSnapshot(data,{final,earlier:choice.checked}));
   document.querySelector('#preview-note').textContent=final?'Final example: private AP is calculated only for each captain’s chosen entry. Toggle the Woodland Lab choice to see its rank change. Jury insight, presentation and reproducibility points are added separately.':'Live example: each team appears once, ranked by its best public AP. Changing the captain’s final choice changes the last column, while the public ranking stays the same. Private scores remain hidden until organizers release final results.';
  };
  publicButton.addEventListener('click',()=>{final=false;update();});finalButton.addEventListener('click',()=>{final=true;update();});choice.addEventListener('change',update);update();
 }catch{root.replaceChildren(text('p','The example leaderboard could not be loaded. Refresh to try again.'));}
}
