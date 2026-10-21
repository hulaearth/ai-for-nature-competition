#!/usr/bin/env python3
"""One-off, guarded public release of the two participant repositories and Space.

The evaluation repository is deliberately outside the mutation allowlist.
Verification keeps current visibility and never publishes the release receipt.
"""
import argparse
import base64
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPOSITORIES = ('hulaearth/ai-for-nature-competition', 'hulaearth/ai-for-nature-codebase')
SPACE = 'Hula-Tech/ai-for-nature-hula-earth'
PLAN_FILE = 'config/materials-release.json'
RECEIPT = 'materials-release.json'


class ReleaseError(Exception):
    pass


def utc(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ReleaseError('A timezone is required.')
    return result.astimezone(timezone.utc)


def load_plan():
    plan = json.loads((ROOT / PLAN_FILE).read_text())
    event = json.loads((ROOT / 'config/challenge.json').read_text())
    if tuple(plan['repositories']) != REPOSITORIES or plan['space_id'] != SPACE:
        raise ReleaseError('Only the two participant repositories and named Space may be released.')
    if plan.get('early_public_repositories', []) not in ([], [REPOSITORIES[0]]):
        raise ReleaseError('Early public access is limited to the competition inbox, never the starter or evaluator.')
    if not isinstance(plan.get('early_public_space', False), bool):
        raise ReleaseError('Early Space publication requires an explicit boolean decision.')
    for key in ('competition_id', 'dataset_release', 'space_id'):
        if plan[key] != event[key]:
            raise ReleaseError('Materials and event plans differ.')
    if plan['not_before_utc'] != event['materials_release_utc'] or not utc(plan['not_before_utc']) < utc(event['start_utc']):
        raise ReleaseError('Materials must be released at the announced time before modeling.')
    if not utc(plan['not_before_utc']) < utc(plan['expires_utc']) <= utc(event['deadline_utc']):
        raise ReleaseError('Invalid one-off release window.')
    if plan['starter_ref'] != event['starter_ref']:
        raise ReleaseError('Starter version differs from the published contract.')
    if hashlib.sha256((ROOT / 'site/participant-guide.pdf').read_bytes()).hexdigest() != plan['guide_sha256']:
        raise ReleaseError('Participant guide changed after the materials freeze.')
    return plan


def guard(plan, now):
    if now.tzinfo is None or not utc(plan['not_before_utc']) <= now <= utc(plan['expires_utc']):
        raise ReleaseError('Outside the one-off materials release window; nothing was released.')


def github(token, method, path, payload=None):
    request = urllib.request.Request('https://api.github.com' + path,
        data=None if payload is None else json.dumps(payload).encode(), method=method,
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2026-03-10', 'Content-Type': 'application/json',
                 'User-Agent': 'ai-for-nature-materials-release'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Provider response bodies can contain credential-bearing details.
        raise ReleaseError('GitHub permission/readback check failed (HTTP ' + str(error.code) + ').') from None


def check_github(plan, token, verify_write=False):
    for repo in REPOSITORIES:
        info = github(token, 'GET', '/repos/' + repo)
        if info.get('full_name', '').lower() != repo or info.get('default_branch') != 'main':
            raise ReleaseError('Unexpected repository or default branch.')
        if (datetime.now(timezone.utc) < utc(plan['not_before_utc']) and info['private'] is not True
                and repo not in plan.get('early_public_repositories', [])):
            raise ReleaseError('A participant repository is already public before the embargo ends.')
        if verify_write:
            # Same-value PATCH proves Administration permission without widening access.
            unchanged = github(token, 'PATCH', '/repos/' + repo, {'private': info['private']})
            if unchanged['private'] != info['private']:
                raise ReleaseError('Visibility preservation check failed.')
    tag = github(token, 'GET', '/repos/' + REPOSITORIES[1] + '/git/ref/tags/' + plan['starter_ref'])
    if tag['object']['type'] != 'commit' or tag['object']['sha'] != plan['starter_commit']:
        raise ReleaseError('Starter tag does not match the frozen commit.')
    current = github(token, 'GET', '/repos/' + REPOSITORIES[0] + '/contents/' + PLAN_FILE + '?ref=main')
    if json.loads(base64.b64decode(current['content'])) != plan:
        raise ReleaseError('Main-branch materials plan changed; publication stopped.')


def receipt(plan, now):
    guard(plan, now)
    return {'schema_version': 1, 'competition_id': plan['competition_id'],
            'dataset_release': plan['dataset_release'], 'not_before_utc': plan['not_before_utc'],
            'published_at_utc': now.isoformat(), 'starter_ref': plan['starter_ref'],
            'starter_commit': plan['starter_commit'], 'guide_sha256': plan['guide_sha256'],
            'starter_url': 'https://github.com/' + REPOSITORIES[1] + '/tree/' + plan['starter_ref']}


def wait_until_release(plan):
    while True:
        remaining = (utc(plan['not_before_utc']) - datetime.now(timezone.utc)).total_seconds()
        if remaining <= 0:
            guard(plan, datetime.now(timezone.utc))
            return
        if remaining > 3600:
            raise ReleaseError('Warm-up may begin only in the last hour before release.')
        time.sleep(min(remaining, 10))


def run(mode):
    plan = load_plan()
    now = datetime.now(timezone.utc)
    if mode == 'window':
        ready = utc(plan['not_before_utc']) - timedelta(hours=1) <= now <= utc(plan['expires_utc'])
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                output.write('ready=' + str(ready).lower() + '\n')
        print('One-off materials window:', 'open' if ready else 'closed')
        return
    if os.environ.get('GITHUB_ACTIONS') == 'true' and (os.environ.get('GITHUB_REPOSITORY') != REPOSITORIES[0] or os.environ.get('GITHUB_REF') != 'refs/heads/main'):
        raise ReleaseError('Only trusted main may operate this release.')
    token = os.environ.get('MATERIALS_RELEASE_TOKEN', '')
    hf_token = os.environ.get('HF_TOKEN', '')
    if not hf_token:
        raise ReleaseError('Existing HF_TOKEN or HF_SPACE_TOKEN is required.')
    from huggingface_hub import HfApi, hf_hub_download
    api = HfApi(token=hf_token)
    info = api.repo_info(SPACE, repo_type='space')
    guide = Path(hf_hub_download(SPACE, 'participant-guide.pdf', repo_type='space', revision=info.sha, token=hf_token))
    if hashlib.sha256(guide.read_bytes()).hexdigest() != plan['guide_sha256']:
        raise ReleaseError('Deploy and verify the frozen participant guide before release.')
    if mode == 'verify':
        if now < utc(plan['not_before_utc']) and not info.private and not plan.get('early_public_space', False):
            raise ReleaseError('Space is already public before the embargo ends.')
        api.update_repo_settings(SPACE, repo_type='space', visibility='private' if info.private else 'public')
        if token:
            check_github(plan, token, verify_write=True)
        setup = {'schema_version': 1, 'competition_id': plan['competition_id'],
                 'not_before_utc': plan['not_before_utc'], 'guide_verified': True,
                 'github_permissions_verified': bool(token), 'armed': bool(token),
                 'verified_at_utc': now.isoformat(), 'source_commit': os.environ.get('GITHUB_SHA')}
        api.upload_file(repo_id=SPACE, repo_type='space', path_in_repo='materials-release-setup.json',
                        path_or_fileobj=io.BytesIO((json.dumps(setup, indent=2) + '\n').encode()),
                        commit_message='Verify materials embargo and release setup without publication')
        if not token:
            raise ReleaseError('MATERIALS_RELEASE_TOKEN is missing; the timed materials release is not armed.')
        print('Materials release permissions and frozen assets verified; visibility was preserved.')
        return
    if mode == 'open-platform':
        if (plan.get('early_public_repositories') != [REPOSITORIES[0]]
                or plan.get('early_public_space') is not True or not token):
            raise ReleaseError('Opening the platform requires the explicit approved allowlist and release credential.')
        if now >= utc(plan['expires_utc']):
            raise ReleaseError('The platform publication plan has expired.')
        check_github(plan, token)
        github(token, 'PATCH', '/repos/' + REPOSITORIES[0], {'private': False})
        if github(token, 'GET', '/repos/' + REPOSITORIES[0])['private']:
            raise ReleaseError('Competition inbox publication did not pass readback.')
        api.update_repo_settings(SPACE, repo_type='space', visibility='public')
        if api.repo_info(SPACE, repo_type='space').private:
            raise ReleaseError('Space publication did not pass readback.')
        print('Approved competition inbox and Space are public. Starter schedule and test-key schedule are unchanged.')
        return
    if not token:
        raise ReleaseError('MATERIALS_RELEASE_TOKEN is required; nothing was released.')
    wait_until_release(plan)
    if load_plan() != plan:
        raise ReleaseError('Local materials plan changed during warm-up.')
    check_github(plan, token)
    for repo in reversed(REPOSITORIES):
        guard(plan, datetime.now(timezone.utc))
        github(token, 'PATCH', '/repos/' + repo, {'private': False})
        if github(token, 'GET', '/repos/' + repo)['private']:
            raise ReleaseError('Repository publication did not pass readback.')
    guard(plan, datetime.now(timezone.utc))
    # No secret is in this receipt. Ordinary site deployments retain this endpoint.
    files = api.list_repo_files(SPACE, repo_type='space')
    if RECEIPT in files:
        existing = json.loads(Path(hf_hub_download(SPACE, RECEIPT, repo_type='space', token=hf_token)).read_text())
        if existing != receipt(plan, utc(existing['published_at_utc'])):
            raise ReleaseError('An incompatible materials release receipt already exists.')
    else:
        data = (json.dumps(receipt(plan, datetime.now(timezone.utc)), indent=2) + '\n').encode()
        api.upload_file(repo_id=SPACE, repo_type='space', path_in_repo=RECEIPT,
                        path_or_fileobj=io.BytesIO(data), commit_message='Release the frozen participant materials')
    guard(plan, datetime.now(timezone.utc))
    api.update_repo_settings(SPACE, repo_type='space', visibility='public')
    if api.repo_info(SPACE, repo_type='space').private:
        raise ReleaseError('Space publication did not pass readback.')
    print('Participant repositories and Space released; evaluator visibility was never modified.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['window', 'verify', 'publish', 'open-platform'], default='verify')
    try:
        run(parser.parse_args().mode)
    except ReleaseError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
    except Exception as error:
        print('Materials release stopped (' + type(error).__name__ + '); no credential was logged.', file=sys.stderr)
        raise SystemExit(1)
