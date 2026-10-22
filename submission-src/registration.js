import {sha256} from './protocol.js';

export async function teamSlug(hfId,epoch=''){
 if(!/^[0-9a-f]{24}$/.test(hfId))throw new Error('Sign in again; the account identity is invalid.');
 return 'team-'+(await sha256(new TextEncoder().encode(epoch?hfId+':'+epoch:hfId))).slice(0,16);
}

function clean(value,min=1){
 if(typeof value!=='string')throw new Error('Team details must be text.');
 const result=value.normalize('NFKC').trim();
 if([...result].length<min||[...result].length>60||/\p{C}/u.test(result))throw new Error('Team name needs 2–60 characters; each nickname needs 1–60 characters, without control characters.');
 return result.replace(/\s+/gu,' ');
}

export function registrationPayload({name,members,accepted,config}){
 const teamName=clean(name,2);
 const roster=members.split(/\r?\n/).map(s=>s.trim()).filter(Boolean).map(s=>clean(s));
 if(roster.length<2||roster.length>3||new Set(roster.map(s=>s.toLowerCase())).size!==roster.length)throw new Error('Team roster needs 2 or 3 different nicknames, one per line, including the captain.');
 if(!accepted)throw new Error('Team registration needs your acceptance of the competition rules and public-name notice.');
 const result={team_name:teamName,members:roster,rules_version:config.registration_rules_version,accepted_rules:true};
 if(new TextEncoder().encode(JSON.stringify(result)).length>4096)throw new Error('Team details exceed the size limit.');
 return result;
}

export function ownedTeams(teams,subject){return teams.filter(t=>t.hf_id===subject||t.member_accounts?.some(m=>m.hf_id===subject));}
export function isCaptain(team,subject){return !!subject&&team?.hf_id===subject;}
export function isOrganizer(config,subject){return !!subject&&config.organizer_hf_ids?.includes(subject);}
export const requestLabel=kind=>({registration:'Registration',team_admin:'Organizer change',membership:'Team membership',selection:'Final choice',prediction:'Prediction'}[kind]??'Request');
export const rejectionMessage=code=>({
 ALREADY_REGISTERED:'This account already belongs to a team or has previously belonged to one. Ask an organizer to correct the existing team.',
 TEAM_NAME_TAKEN:'That team name is already used. Choose another name.',
 REGISTRATION_CLOSED:'Registration is closed. Existing teams can still submit.',
 TEAM_CAPACITY:'The competition team limit has been reached. Ask an organizer for help.',
 RULES:'Refresh the page and accept the current competition rules.',
 REGISTRATION_FORMAT:'Check the team name and provide 2 or 3 different member nicknames.',
 ORGANIZER:'This account cannot change organizer settings.',
 CAPTAIN:'Only the captain can manage members or choose the final entry.',
 INVITATION:'This invitation is not pending for your account. Refresh the team status.',
 INVITE_EXISTS:'An invitation to this account is already pending.',
 INVITE_EXPIRED:'This invitation expired. Ask the captain for a new one.',
 TEAM_FULL:'The declared team is full, including pending invitations.',
 MEMBERSHIP_FORMAT:'Check the membership details and accept the shared-team rules.',
 CAPTAIN_ACCOUNT:'Enter an existing individual Hugging Face username.',
 TEAM:'The account is not an active member of this team.',
 QUOTA:'This team has used its accepted submission allowance.',
 RECEIPT_REQUIRED:'Reload the page and submit through the current page; this request has no deadline commitment.',
 RECEIPT_HASH:'The request differs from its original deadline commitment. Reload and submit a fresh request.',
 RECEIPT_EDITED:'The original request description was edited. Submit a fresh request before the deadline.',
 CLOSED:'Submissions are closed.',
 DUPLICATE:'These predictions were already accepted for this team.',
}[code]??`Request not accepted (${code}).`);
