import base64
from contextlib import redirect_stdout
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts import release_test_key as release


class FakeGitHub:
    def __init__(self, plan):
        self.head = 'a' * 40
        self.revisions = {self.head: {'config/test-key-release.json': json.dumps(plan).encode()}}
        self.trees = {}
        self.writes = []
        self.conflict = False
        self.private = False

    def call(self, token, method, path, data=None):
        base = '/repos/' + release.COMPETITION_REPO
        if method == 'GET' and path == base:
            return {'full_name': release.COMPETITION_REPO, 'private': self.private, 'default_branch': 'main'}
        if method == 'GET' and path == base + '/git/ref/heads/main':
            return {'object': {'sha': self.head}}
        if method == 'GET' and path.startswith(base + '/contents/'):
            name, revision = path.split('/contents/', 1)[1].split('?ref=')
            content = self.revisions[revision].get(name)
            if content is None:
                raise release.GitHubError(404)
            return {'type': 'file', 'encoding': 'base64', 'content': base64.b64encode(content).decode()}
        if method == 'GET' and path.startswith(base + '/git/commits/'):
            revision = path.rsplit('/', 1)[1]
            return {'tree': {'sha': revision}}
        self.writes.append((method, path, data))
        if method == 'POST' and path == base + '/git/trees':
            files = dict(self.revisions[data['base_tree']])
            files.update({r['path']: r['content'].encode() for r in data['tree']})
            name = 'tree' + str(len(self.trees)); self.trees[name] = files
            return {'sha': name}
        if method == 'POST' and path == base + '/git/commits':
            name = f'{len(self.revisions):040x}'
            self.revisions[name] = self.trees[data['tree']]
            return {'sha': name}
        if method == 'PATCH' and path == base + '/git/refs/heads/main':
            if data['force'] is not False:
                raise AssertionError('Never force the public branch')
            if self.conflict:
                self.conflict = False
                files = dict(self.revisions[self.head]); files['unrelated-feedback.json'] = b'keep'
                self.head = 'f' * 40; self.revisions[self.head] = files
                raise release.GitHubError(422)
            self.head = data['sha']; return {'object': {'sha': self.head}}
        raise AssertionError('Unexpected API operation')

    def anonymous(self, name, revision, expected):
        if self.revisions[revision].get(name) != expected:
            raise AssertionError('Anonymous bytes differ')


class KeyBackupTests(unittest.TestCase):
    def setUp(self):
        self.identity = 'AGE-SECRET-KEY-1' + 'A' * 59 + '\n'  # Synthetic fixture only.
        self.at = datetime(2026, 10, 24, 11, 30, tzinfo=timezone.utc)
        self.plan = {'competition_id': 'synthetic', 'dataset_release': 'synthetic', 'space_id': 'synthetic-space',
            'not_before_utc': self.at.isoformat(), 'expires_utc': (self.at + timedelta(hours=4)).isoformat(),
            'identity_sha256': hashlib.sha256(self.identity.encode()).hexdigest()}
        self.fake = FakeGitHub(self.plan)
        self.addCleanup(patch.stopall)
        patch.object(release, 'github', self.fake.call).start()
        patch.object(release, 'anonymous_backup_bytes', self.fake.anonymous).start()
        patch.dict(os.environ, {'GITHUB_REPOSITORY': release.COMPETITION_REPO}).start()
        patch('sys.stdout', new=io.StringIO()).start()

    def publish(self, **kwargs):
        return release.publish_github(self.plan, self.identity, 'synthetic-token', clock=lambda: self.at, **kwargs)

    def test_before_or_after_window_refuses_before_any_api_write(self):
        for at in [self.at - timedelta(microseconds=1), self.at + timedelta(days=1)]:
            with self.assertRaises(release.ReleaseError):
                release.publish_github(self.plan, self.identity, 'synthetic-token', clock=lambda: at)
        self.assertEqual(self.fake.writes, [])

    def test_publication_is_atomic_and_idempotent(self):
        first = self.publish(); writes = len(self.fake.writes)
        second = release.publish_github(self.plan, self.identity, 'synthetic-token', clock=lambda: self.at + timedelta(minutes=5))
        self.assertEqual(first, second); self.assertEqual(len(self.fake.writes), writes)
        files = self.fake.revisions[first]
        self.assertEqual(files[release.BACKUP_PREFIX + release.IDENTITY_FILE], self.identity.encode())
        receipt = json.loads(files[release.BACKUP_PREFIX + release.PUBLICATION])
        self.assertEqual(receipt['published_at_utc'], self.at.isoformat())
        tree = next(data for method, path, data in self.fake.writes if path.endswith('/git/trees'))
        self.assertEqual({r['path'] for r in tree['tree']}, {release.BACKUP_PREFIX + n for n in [release.IDENTITY_FILE, release.PUBLICATION]})

    def test_setup_before_release_contains_no_identity(self):
        revision = release.publish_github(self.plan, None, 'synthetic-token', verify_only=True, clock=lambda: self.at - timedelta(days=1))
        files = self.fake.revisions[revision]
        self.assertNotIn(release.BACKUP_PREFIX + release.IDENTITY_FILE, files)
        self.assertNotIn(release.BACKUP_PREFIX + release.PUBLICATION, files)
        raw = files[release.BACKUP_PREFIX + 'setup.json']
        self.assertNotIn(b'AGE-SECRET-KEY-1', raw); self.assertFalse(json.loads(raw)['key_published'])

    def test_changed_main_plan_stops_publication(self):
        self.fake.revisions[self.fake.head]['config/test-key-release.json'] = b'{}'
        with self.assertRaises(release.ReleaseError): self.publish()
        self.assertEqual(self.fake.writes, [])

    def test_private_destination_and_wrong_identity_are_rejected(self):
        self.fake.private = True
        with self.assertRaises(release.ReleaseError): self.publish()
        self.fake.private = False
        with self.assertRaises(release.ReleaseError):
            release.publish_github(self.plan, 'invalid', 'synthetic-token', clock=lambda: self.at)
        self.assertEqual(self.fake.writes, [])

    def test_concurrent_feedback_is_preserved_without_force_push(self):
        self.fake.conflict = True
        revision = self.publish()
        self.assertEqual(self.fake.revisions[revision]['unrelated-feedback.json'], b'keep')
        self.assertEqual(self.fake.revisions[revision][release.BACKUP_PREFIX + release.IDENTITY_FILE], self.identity.encode())

    def test_conflicting_existing_key_is_not_replaced(self):
        self.fake.revisions[self.fake.head][release.BACKUP_PREFIX + release.IDENTITY_FILE] = b'different'
        with self.assertRaises(release.ReleaseError): self.publish()
        self.assertEqual(self.fake.writes, [])

    def test_github_backup_survives_hf_outage_but_both_failures_are_not_success(self):
        environment = {'TEST_RELEASE_KEY': self.identity, 'HF_TOKEN': 'synthetic-hf', 'GITHUB_TOKEN': 'synthetic-gh', 'GITHUB_ACTIONS': 'true'}
        with patch.dict(os.environ, environment), patch('sys.argv', ['release_test_key.py', '--mode', 'publish']), \
             patch.object(release, 'load_plan', return_value=self.plan), patch.object(release, 'wait_until_release'), \
             patch.object(release, 'check_current_main_plan'), patch.object(release, 'publish', side_effect=TimeoutError), \
             patch.object(release, 'publish_github', return_value='verified') as backup:
            release.main(); self.assertEqual(backup.call_count, 1)
            backup.side_effect = TimeoutError
            with self.assertRaises(release.ReleaseError): release.main()

    def test_hf_rate_limit_does_not_trigger_a_tight_retry(self):
        class QuotaError(Exception):
            response = SimpleNamespace(status_code=429)
        api = SimpleNamespace(repo_info=Mock(return_value=SimpleNamespace(sha='a'*40)),
            list_repo_files=Mock(return_value=[]), create_commit=Mock(side_effect=QuotaError))
        module = SimpleNamespace(HfApi=lambda **_: api, CommitOperationAdd=lambda **kw: kw, hf_hub_download=Mock())
        with patch.dict('sys.modules', {'huggingface_hub': module}), patch.object(release, 'configure_hub_http'), \
             patch.object(release, 'guard'), patch.object(release, 'payload', return_value={}), patch.object(release.time, 'sleep') as sleep:
            with self.assertRaises(QuotaError): release.publish(self.plan, self.identity, 'synthetic')
            self.assertEqual(api.create_commit.call_count, 1); sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
