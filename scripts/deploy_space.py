#!/usr/bin/env python3
"""Upload only the public site allowlist to the specified static HF Space."""
import os
from pathlib import Path
import tempfile
import shutil
import hashlib
import subprocess
import sys
import json
from datetime import datetime, timezone
from huggingface_hub import HfApi, hf_hub_download, CommitOperationDelete

ROOT=Path(__file__).resolve().parents[1]
SPACE='HulaEarth/ai-for-nature-hula-earth'
FILES=['index.html','data.html','rules.html','submit.html','leaderboard.html','style.css','app.js',
       'envelope.js','config.json','teams.json','leaderboard.json','submission-key.json','practice_submission.csv',
       'register.html','leaderboard-preview.json','guide.html','test-key-plan.json','upload.html','upload.css','submission.js','receipts.json','legacy-submit.html']
README='''---
title: AI for Nature Hula Earth
emoji: 🐦
colorFrom: green
colorTo: gray
sdk: static
app_file: index.html
pinned: true
hf_oauth: true
hf_oauth_expiration_minutes: 60
hf_oauth_scopes:
  - write-discussions
license: mit
short_description: Bird habitat modeling challenge and prediction leaderboard
---

# AI for Nature Hula Earth

Static competition pages with native Hugging Face team registration. Participants train on their own compute. Predictions are encrypted in the browser and evaluated by trusted GitHub Actions in a private repository. No evaluation labels or submission-decryption keys are hosted here. The test-input unlock identity is published only at its announced release time.

Germany bird habitat challenge using 2024 observations, AlphaEarth, WorldCover, terrain and historical OpenStreetMap data: ten target species, 6.5 working hours, a shared German development split, and anonymous nearby Central European final inputs.

The main **Submit** tab contains CSV upload, acceptance status and final-choice controls. Sign in with your confirmed team account, submit the CSV directly, and check **Accepted**. The page encrypts and delivers it automatically. Use the final-entry checkbox or **Use for final** beside an accepted entry. Upload slides through the separate Google Form below predictions; no separate GitHub nomination is required. GitHub attachment forms are a conductor-directed backup.

The three tasks are habitat suitability modeling, ecological data insights and visualizations, and an optional cross-species extension. The jury uses 50 model-performance points under a fixed baseline-relative conversion, 30 insight/visualization points, 15 presentation/question points and a 5-point reproducibility checklist. Matching the unchanged shipped starter earns 15 model points; +0.15 AP earns 50. See the Rules view for the full formula, caps and evidence criteria.

- [Challenge data](https://drive.google.com/drive/folders/1gXsJyZnI8QIbk1RQYL0qNqy1yf0eSaoT) (access and upload readiness are announced on the Data page)
- [Register a team](https://huggingface.co/spaces/HulaEarth/ai-for-nature-hula-earth#register)
- [Participant materials and release status](https://huggingface.co/spaces/HulaEarth/ai-for-nature-hula-earth#guide)

Before kickoff, only downloads, technical documentation and environment checks are allowed. Training is unencrypted; the final feature package is encrypted and unlocked at 13:30 German time on Saturday 24 October 2026. Work runs 11:00-17:30 and presentations 17:45-19:45. The competition pages are available now. The participant guide and starter code open at 10:00 on event day; modeling begins at 11:00. Final submissions still require the evaluator launch checks. Dataset attribution and upstream licenses are supplied with the data; the MIT license here applies to the site code.
'''


def deploy(token=None):
    token=token or os.environ.get('HF_TOKEN')
    if not token:raise RuntimeError('HF_TOKEN is required; do not paste it into source code')
    # Rebuild when roster/config/standings JSON changes, including trusted worker publications.
    subprocess.run([sys.executable,str(ROOT/'scripts'/'build_site.py')],check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts'/'check_site.py')],check=True)
    api=HfApi(token=token)
    info=api.repo_info(SPACE,repo_type='space')
    plan=json.loads((ROOT/'config/materials-release.json').read_text())
    if datetime.now(timezone.utc)<datetime.fromisoformat(plan['not_before_utc'].replace('Z','+00:00')):
        if 'participant-guide.pdf' in api.list_repo_files(SPACE,repo_type='space'):
            api.create_commit(repo_id=SPACE,repo_type='space',
                operations=[CommitOperationDelete(path_in_repo='participant-guide.pdf')],
                commit_message='Keep the event-day participant guide behind its scheduled release')
    # Preserve visibility. Creating or changing access is an explicit organizer launch action.
    with tempfile.TemporaryDirectory(prefix='aifn-public-site-') as directory:
        stage=Path(directory)
        for name in FILES:
            # Dynamic team/receipt exports belong to the feedback publisher.
            if name in {'receipts.json','teams.json','leaderboard.json','config.json'}:continue
            source=ROOT/'site'/name
            if not source.is_file():raise RuntimeError('Missing public site asset: '+name)
            shutil.copyfile(source,stage/name)
        (stage/'README.md').write_text(README)
        result=api.upload_folder(repo_id=SPACE,repo_type='space',folder_path=stage,commit_message='Publish competition pages and verified public standings')
        for published in sorted(stage.iterdir()):
            downloaded=Path(hf_hub_download(repo_id=SPACE,repo_type='space',filename=published.name,
                                          revision=result.oid,token=token))
            if hashlib.sha256(downloaded.read_bytes()).digest()!=hashlib.sha256(published.read_bytes()).digest():
                raise RuntimeError('Remote content verification failed: '+published.name)
    if os.environ.get('CLEAN_PARTICIPANT_HISTORY') == 'true':
        # Explicit organizer maintenance only; normal deployments never rewrite history.
        permitted = set(FILES) | {'README.md', '.gitattributes', 'test-key-release.json',
                                  'test-release-key.agekey', 'materials-release.json', 'participant-guide.pdf'}
        obsolete = sorted(set(api.list_repo_files(SPACE, repo_type='space')) - permitted)
        if obsolete:
            api.create_commit(repo_id=SPACE, repo_type='space',
                              operations=[CommitOperationDelete(path_in_repo=name) for name in obsolete],
                              commit_message='Keep current participant materials only')
        api.super_squash_history(repo_id=SPACE, repo_type='space', branch='main',
                                 commit_message='AI for Nature competition materials')
        current = api.repo_info(SPACE, repo_type='space').sha
        if len(api.list_repo_commits(SPACE, repo_type='space')) != 1:
            raise RuntimeError('Space history cleanup was not confirmed')
        for name in FILES:
            remote = Path(hf_hub_download(SPACE, name, repo_type='space', revision=current, token=token))
            if hashlib.sha256(remote.read_bytes()).digest() != hashlib.sha256((ROOT/'site'/name).read_bytes()).digest():
                raise RuntimeError('Content changed during history cleanup: '+name)
        print('Single current Space snapshot verified:', current)
    print('Uploaded and SHA-256 verified',len(FILES)-3,'public assets:',result.oid)
    return result.oid


if __name__=='__main__':deploy()
