"""Coalesce sanitized feedback with finite waits and optimistic HF commits."""
import base64
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.hub_http import configure_hub_http
SPACE='HulaEarth/ai-for-nature-hula-earth'
REPO='hulaearth/ai-for-nature-competition'
FILES=('receipts.json','leaderboard.json','teams.json','config.json')
MIN_MIRROR_INTERVAL=90


def validate_documents(result):
    if set(result)!=set(FILES):raise RuntimeError('Feedback file allowlist mismatch')
    c=result['config.json'];r=result['receipts.json']
    if c.get('competition_id')!='ai-for-nature-2026' or c.get('space_id')!=SPACE or r.get('competition')!=c['competition_id'] or r.get('space_id')!=SPACE or r.get('schema')!=2:
        raise RuntimeError('Feedback destination mismatch')
    if not isinstance(r.get('generation',0),int) or not isinstance(r.get('teams'),list) or not isinstance(r.get('entries'),list):
        raise RuntimeError('Feedback schema mismatch')
    forbidden={'members','captain_history','account_history','wrapped_key','iv','ciphertext','label','labels','private_score','predictions','csv_sha256','invitation_id'}
    def inspect(value):
        if isinstance(value,dict):
            if forbidden & value.keys():raise RuntimeError('Private field in feedback')
            for item in value.values():inspect(item)
        elif isinstance(value,list):
            for item in value:inspect(item)
    for name in ('receipts.json','teams.json'):inspect(result[name])
    return result


def documents(root=ROOT):
    return validate_documents({name:json.loads((root/'site'/name).read_text())for name in FILES})


def github_documents(token, opener=urllib.request.urlopen):
    """Reload all files at one trusted immutable main commit after coalescing."""
    def get(path):
        req=urllib.request.Request('https://api.github.com/repos/'+REPO+path,
            headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json'})
        with opener(req,timeout=20)as response:return json.loads(response.read())
    sha=get('/git/ref/heads/main')['object']['sha']
    if not re.fullmatch('[0-9a-f]{40}',sha):raise RuntimeError('Unexpected public snapshot')
    return validate_documents({name:json.loads(base64.b64decode(''.join(get('/contents/site/'+name+'?ref='+sha)['content'].split()),validate=True))for name in FILES})


def fingerprint(docs):
    return hashlib.sha256(json.dumps(docs,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def mirror_wait(current,now):
    value=current.get('mirror_published_at_utc')
    if value is None:return 0
    stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
    if stamp.tzinfo is None:raise RuntimeError('Invalid feedback publication time')
    return min(MIN_MIRROR_INTERVAL,max(0,MIN_MIRROR_INTERVAL-(now-stamp).total_seconds()))


def sleep_bounded(seconds,sleep=time.sleep):
    while seconds>0:
        step=min(30,seconds);sleep(step);seconds-=step


def scheduled_window(config,now):
    start=datetime.fromisoformat(config['materials_release_utc'].replace('Z','+00:00'))
    stop=datetime.fromisoformat(config['deadline_utc'].replace('Z','+00:00'))+timedelta(hours=4)
    return start<=now<=stop


def publish():
    from huggingface_hub import HfApi,hf_hub_download,CommitOperationAdd
    configure_hub_http()
    api=HfApi(token=os.environ['HF_TOKEN'])
    def latest():
        token=os.environ.get('GITHUB_TOKEN')
        return github_documents(token)if token else documents()
    def read_head():
        head=api.repo_info(SPACE,repo_type='space').sha
        current=json.loads(Path(hf_hub_download(SPACE,'receipts.json',repo_type='space',revision=head,token=os.environ['HF_TOKEN'])).read_text())
        if current.get('competition')!='ai-for-nature-2026' or current.get('space_id')!=SPACE or current.get('schema')!=2:
            raise RuntimeError('Current HF receipt isolation check failed')
        return head,current
    docs=latest();head,current=read_head()
    if current.get('generation',0)>docs['receipts.json'].get('generation',0):
        print('Newer public receipts already published; older snapshot skipped.');return
    if current.get('mirror_content_sha256')==fingerprint(docs):
        print('Identical public snapshot already mirrored; no commit needed.');return
    sleep_bounded(mirror_wait(current,datetime.now(timezone.utc)))
    for attempt in range(3):
        docs=latest();head,current=read_head()
        if current.get('generation',0)>docs['receipts.json'].get('generation',0):
            print('Newer public receipts already published; older snapshot skipped.');return
        digest=fingerprint(docs)
        if current.get('mirror_content_sha256')==digest:
            print('Identical public snapshot already mirrored; no commit needed.');return
        docs['receipts.json'].update(mirror_content_sha256=digest,mirror_published_at_utc=datetime.now(timezone.utc).isoformat())
        operations=[CommitOperationAdd(path_in_repo=name,path_or_fileobj=(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode())for name,value in docs.items()]
        try:
            result=api.create_commit(repo_id=SPACE,repo_type='space',parent_commit=head,operations=operations,commit_message='Publish verified teams and submission feedback')
            print('Public feedback generation',docs['receipts.json'].get('generation',0),'published:',result.oid);return
        except Exception as error:
            response=getattr(error,'response',None);status=getattr(response,'status_code',None)
            if status==429:
                value=getattr(response,'headers',{}).get('retry-after','')
                delay=int(value)if value.isdigit()else 120
                if delay>90 or attempt==2:
                    raise RuntimeError('HF feedback mirror rate-limited; GitHub receipts remain authoritative. Event-window retry will reload the newest snapshot.')from None
                sleep_bounded(delay)
            elif status in {409,412,422} and attempt<2:sleep_bounded(2)
            else:raise RuntimeError('HF feedback mirror needs retry; private processing and GitHub receipts are preserved.')from None


if __name__=='__main__':
    if os.environ.get('GITHUB_EVENT_NAME')=='schedule'and not scheduled_window(documents()['config.json'],datetime.now(timezone.utc)):
        print('Outside the single event retry window; no publication attempted.')
    else:publish()
