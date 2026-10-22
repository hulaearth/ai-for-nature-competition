"""Publish sanitized receipts without a site build, preserving newer generations."""
from pathlib import Path
import json
import os
import time

ROOT=Path(__file__).resolve().parents[1]
SPACE='HulaEarth/ai-for-nature-hula-earth'
FILES=('receipts.json','leaderboard.json','teams.json','config.json')

def documents(root=ROOT):
    result={name:json.loads((root/'site'/name).read_text())for name in FILES}
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

def publish():
    from huggingface_hub import HfApi,hf_hub_download,CommitOperationAdd
    api=HfApi(token=os.environ['HF_TOKEN']);docs=documents()
    for attempt in range(3):
        head=api.repo_info(SPACE,repo_type='space').sha
        current=json.loads(Path(hf_hub_download(SPACE,'receipts.json',repo_type='space',revision=head,token=os.environ['HF_TOKEN'])).read_text())
        if current.get('generation',0)>docs['receipts.json'].get('generation',0):
            print('Newer public receipts already published; older snapshot skipped.');return
        operations=[CommitOperationAdd(path_in_repo=name,path_or_fileobj=(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode())for name,value in docs.items()]
        try:
            result=api.create_commit(repo_id=SPACE,repo_type='space',parent_commit=head,operations=operations,commit_message='Publish verified teams and submission feedback')
            print('Public feedback generation',docs['receipts.json'].get('generation',0),'published:',result.oid);return
        except Exception:
            if attempt==2:raise RuntimeError('Feedback publication needs retry')from None
            time.sleep(2)

if __name__=='__main__':publish()
