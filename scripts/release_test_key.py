#!/usr/bin/env python3
"""Publish only the test-input age identity, never before the configured UTC instant."""
import argparse
import base64
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.hub_http import configure_hub_http
PUBLICATION = 'test-key-release.json'
IDENTITY_FILE = 'test-release-key.agekey'


class ReleaseError(Exception):
    pass


def utc(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ReleaseError('Release timestamps must include their timezone.')
    return parsed.astimezone(timezone.utc)


def load_plan():
    plan = json.loads((ROOT / 'config/test-key-release.json').read_text())
    event = json.loads((ROOT / 'config/challenge.json').read_text())
    for name in ['competition_id', 'dataset_release', 'space_id']:
        if plan[name] != event[name]:
            raise ReleaseError('Release plan does not match the challenge configuration.')
    if utc(plan['not_before_utc']) != utc(event['test_release_utc']):
        raise ReleaseError('Release time does not match the announced test unlock time.')
    if utc(plan['expires_utc']) <= utc(plan['not_before_utc']):
        raise ReleaseError('Release window is invalid.')
    return plan


def identity_from(value, expected_sha):
    lines = [line.strip() for line in value.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if len(lines) != 1 or not re.fullmatch(r'AGE-SECRET-KEY-1[A-Z0-9]+', lines[0]):
        raise ReleaseError('TEST_RELEASE_KEY must contain the test-input age identity, not the submission RSA key.')
    identity = lines[0] + '\n'
    if hashlib.sha256(identity.encode()).hexdigest() != expected_sha:
        raise ReleaseError('Test-input identity fingerprint does not match the frozen release.')
    return identity


def guard(plan, now):
    if now.tzinfo is None:
        raise ReleaseError('Publisher clock must be timezone-aware.')
    if now < utc(plan['not_before_utc']):
        raise ReleaseError('Refusing to publish before the configured release instant.')
    if now > utc(plan['expires_utc']):
        raise ReleaseError('This one-off release window has expired.')


def payload(plan, identity, now):
    guard(plan, now)
    identity = identity_from(identity, plan['identity_sha256'])
    return {
        'schema_version': 1,
        'competition_id': plan['competition_id'],
        'dataset_release': plan['dataset_release'],
        'not_before_utc': plan['not_before_utc'],
        'published_at_utc': now.astimezone(timezone.utc).isoformat(),
        'identity_sha256': plan['identity_sha256'],
        'identity': identity,
    }


def setup_receipt(plan, now):
    # Public operational evidence contains no identity value or other credentials.
    return {'schema_version': 1, 'competition_id': plan['competition_id'],
            'dataset_release': plan['dataset_release'], 'not_before_utc': plan['not_before_utc'],
            'identity_sha256': plan['identity_sha256'], 'secret_fingerprint_verified': True,
            'key_published': False, 'verified_at_utc': now.astimezone(timezone.utc).isoformat(),
            'source_commit': os.environ.get('GITHUB_SHA'), 'workflow_run_id': os.environ.get('GITHUB_RUN_ID')}


def wait_until_release(plan, clock=lambda: datetime.now(timezone.utc), sleep=time.sleep):
    while True:
        now = clock()
        remaining = (utc(plan['not_before_utc']) - now).total_seconds()
        if remaining <= 0:
            guard(plan, now)
            return
        if remaining > 3600:
            raise ReleaseError('Warm-up may start at most one hour before release.')
        sleep(min(remaining, 10))


def check_current_main_plan(plan):
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        return
    repo = os.environ.get('GITHUB_REPOSITORY')
    token = os.environ.get('GITHUB_TOKEN')
    expected = json.loads((ROOT / 'config/challenge.json').read_text())['competition_repository']
    if repo != expected or not token:
        raise ReleaseError('Cannot recheck the trusted main-branch release plan.')
    request = urllib.request.Request(
        'https://api.github.com/repos/' + repo + '/contents/config/test-key-release.json?ref=main',
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                 'User-Agent': 'ai-for-nature-test-release'},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        remote = json.load(response)
    current = json.loads(base64.b64decode(remote['content']))
    if current != plan:
        raise ReleaseError('The release plan changed on main during warm-up; publication stopped.')


def publish(plan, identity, token):
    from huggingface_hub import HfApi, CommitOperationAdd, hf_hub_download
    configure_hub_http()
    api = HfApi(token=token)
    # Both files are outside the ordinary deployment allowlist, so later site deployments retain them.
    for attempt in range(3):
        guard(plan, datetime.now(timezone.utc))
        info = api.repo_info(plan['space_id'], repo_type='space')
        files = api.list_repo_files(plan['space_id'], repo_type='space', revision=info.sha)
        if PUBLICATION in files:
            existing = json.loads(Path(hf_hub_download(plan['space_id'], PUBLICATION, repo_type='space', revision=info.sha, token=token)).read_text())
            if existing.get('identity_sha256') != plan['identity_sha256'] or existing.get('not_before_utc') != plan['not_before_utc']:
                raise ReleaseError('A different release already occupies the Space key endpoint.')
            if existing != payload_for_existing(plan, identity, existing):
                raise ReleaseError('Existing publication failed its identity/time validation.')
            raw = Path(hf_hub_download(plan['space_id'], IDENTITY_FILE, repo_type='space', revision=info.sha, token=token)).read_text()
            if raw != identity:
                raise ReleaseError('Existing key download differs from the verified identity.')
            print('The configured test-data identity is already published and verified.')
            return info.sha
        data = payload(plan, identity, datetime.now(timezone.utc))
        encoded = (json.dumps(data, indent=2) + '\n').encode()
        try:
            result = api.create_commit(
                repo_id=plan['space_id'], repo_type='space', parent_commit=info.sha,
                operations=[CommitOperationAdd(path_in_repo=PUBLICATION, path_or_fileobj=io.BytesIO(encoded)),
                            CommitOperationAdd(path_in_repo=IDENTITY_FILE, path_or_fileobj=io.BytesIO(identity.encode()))],
                commit_message='Release verified competition test-input unlock key',
            )
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)
            continue
        for name, expected in [(PUBLICATION, encoded), (IDENTITY_FILE, identity.encode())]:
            remote = Path(hf_hub_download(plan['space_id'], name, repo_type='space', revision=result.oid, token=token))
            if remote.read_bytes() != expected:
                raise ReleaseError('Published key bytes failed verification.')
        print('Test-input key released and verified on the configured Space. Commit:', result.oid)
        return result.oid


def payload_for_existing(plan, identity, existing):
    # An idempotent retry must verify the original publication time, not rewrite it.
    return payload(plan, identity, utc(existing['published_at_utc']))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['window', 'verify', 'publish'], default='verify')
    args = parser.parse_args()
    plan = load_plan()
    now = datetime.now(timezone.utc)
    if args.mode == 'window':
        ready = utc(plan['not_before_utc']) - timedelta(hours=1) <= now <= utc(plan['expires_utc'])
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                output.write('ready=' + str(ready).lower() + '\n')
        print('One-off release window:', 'open' if ready else 'closed')
        return
    identity = identity_from(os.environ.get('TEST_RELEASE_KEY') or os.environ.get('TEST_DATA_UNLOCK_KEY', ''), plan['identity_sha256'])
    token = os.environ.get('HF_TOKEN')
    if not token:
        raise ReleaseError('The existing HF_TOKEN or HF_SPACE_TOKEN secret is required.')
    if args.mode == 'verify':
        from huggingface_hub import HfApi
        configure_hub_http()
        api = HfApi(token=token)
        api.repo_info(plan['space_id'], repo_type='space')
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            safe = (json.dumps(setup_receipt(plan, now), indent=2) + '\n').encode()
            result = api.upload_file(repo_id=plan['space_id'], repo_type='space',
                                     path_in_repo='test-key-release-setup.json', path_or_fileobj=io.BytesIO(safe),
                                     commit_message='Verify timed key-release configuration without exposing the key')
            print('Secret fingerprint verified; safe setup receipt recorded. No unlock key published. Commit:', result.oid)
        else:
            print('Test-input identity fingerprint, release plan and HF read access verified. No unlock key published.')
        return
    wait_until_release(plan)
    # Re-read local configuration immediately before publication and compare it with the job plan.
    if load_plan() != plan:
        raise ReleaseError('Release configuration changed during warm-up; publication stopped.')
    check_current_main_plan(plan)
    publish(plan, identity, token)


if __name__ == '__main__':
    try:
        main()
    except ReleaseError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
    except Exception as error:
        # Do not print provider response bodies, request payloads or any identity value.
        print('Timed release failed (' + type(error).__name__ + '); no key value was logged.', file=sys.stderr)
        raise SystemExit(1)
