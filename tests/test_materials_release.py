"""Embargo tests use synthetic API clients and never change actual visibility."""
import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

spec = importlib.util.spec_from_file_location('release_materials', Path(__file__).parents[1] / 'scripts/release_materials.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class MaterialsReleaseTests(unittest.TestCase):
    def setUp(self):
        self.plan = release.load_plan()

    def test_exact_german_release_and_not_modeling_start(self):
        from zoneinfo import ZoneInfo
        local = release.utc(self.plan['not_before_utc']).astimezone(ZoneInfo('Europe/Berlin'))
        self.assertEqual(local.isoformat(), '2026-10-24T10:00:00+02:00')
        event = json.loads((release.ROOT / 'config/challenge.json').read_text())
        self.assertEqual(event['start_utc'], '2026-10-24T09:00:00Z')
        self.assertEqual(event['test_release_utc'], '2026-10-24T11:30:00Z')

    def test_embargo_deadline_and_next_year(self):
        for value in ['2026-10-24T07:59:59Z', '2026-10-24T15:30:01Z', '2027-10-24T08:00:00Z']:
            with self.assertRaises(release.ReleaseError):
                release.guard(self.plan, release.utc(value))
        release.guard(self.plan, release.utc('2026-10-24T08:00:00Z'))

    def test_naive_clock_and_receipt_rejected(self):
        with self.assertRaises(release.ReleaseError):
            release.receipt(self.plan, datetime(2026, 10, 24, 8))
        with self.assertRaises(release.ReleaseError):
            release.receipt(self.plan, release.utc('2026-10-24T07:59:59Z'))

    def test_receipt_is_pinned_and_contains_no_credentials(self):
        result = release.receipt(self.plan, release.utc('2026-10-24T08:00:00Z'))
        self.assertEqual(result['starter_ref'], 'hackathon-2026')
        self.assertIn('/tree/hackathon-2026', result['starter_url'])
        self.assertEqual(set(result), {'schema_version','competition_id','dataset_release','not_before_utc',
            'published_at_utc','starter_ref','starter_commit','guide_sha256','starter_url'})

    def test_changed_main_plan_prevents_release(self):
        import base64
        calls = []
        def api(token, method, path, payload=None):
            calls.append((method, path, payload))
            if '/contents/' in path:
                changed = {**self.plan, 'not_before_utc': '2026-10-24T07:00:00Z'}
                return {'content': base64.b64encode(json.dumps(changed).encode()).decode()}
            if '/git/ref/' in path:
                return {'object': {'type':'commit', 'sha':self.plan['starter_commit']}}
            return {'full_name':path.removeprefix('/repos/'), 'private':True, 'default_branch':'main'}
        with patch.object(release, 'github', side_effect=api):
            with self.assertRaises(release.ReleaseError):
                release.check_github(self.plan, 'synthetic')
        self.assertTrue(all(method == 'GET' for method, _, _ in calls))
        self.assertTrue(all('evaluation' not in path for _, path, _ in calls))

    def test_other_repository_and_changed_guide_fail_before_network(self):
        original = release.ROOT / 'config/materials-release.json'
        for change in [{'repositories':[*release.REPOSITORIES, 'hulaearth/ai-for-nature-evaluation']},
                       {'early_public_repositories':[release.REPOSITORIES[1]]},
                       {'early_public_repositories':['hulaearth/ai-for-nature-evaluation']},
                       {'early_public_space':'yes'},
                       {'guide_sha256':'malformed'}]:
            real_read = Path.read_text
            def read(path, *args, **kwargs):
                return json.dumps({**self.plan, **change}) if path == original else real_read(path, *args, **kwargs)
            with patch.object(Path, 'read_text', read):
                with self.assertRaises(release.ReleaseError):
                    release.load_plan()

    def exercise_fake_hosts(self, mode, when, token='synthetic', early_public=False):
        import base64
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            files = {}
            guide_bytes=b'%PDF-1.7 synthetic event-day guide'
            import hashlib
            plan={**self.plan,'guide_sha256':hashlib.sha256(guide_bytes).hexdigest()}
            visibility = {repo: True for repo in release.REPOSITORIES}
            if early_public:
                visibility[release.REPOSITORIES[0]] = False
            operations = []
            class Hub:
                private = True
                def repo_info(self, *args, **kwargs):
                    return SimpleNamespace(private=self.private, sha='synthetic')
                def list_repo_files(self, *args, **kwargs):
                    return list(files)
                def update_repo_settings(self, repo, **kwargs):
                    operations.append(('hf-visibility', kwargs['visibility']))
                    self.private = kwargs['visibility'] == 'private'
                def upload_file(self, **kwargs):
                    name = kwargs['path_in_repo']
                    files[name] = directory / name
                    files[name].write_bytes(kwargs['path_or_fileobj'].read())
                    operations.append(('hf-file', name))
                def create_commit(self, **kwargs):
                    for op in kwargs['operations']:
                        self.upload_file(path_in_repo=op.path_in_repo,path_or_fileobj=op.path_or_fileobj)
            hub = Hub()
            def api(token, method, path, payload=None):
                if '/contents/docs/participant-guide.pdf' in path:
                    return {'content':base64.b64encode(guide_bytes).decode()}
                if '/contents/' in path:
                    return {'content':base64.b64encode(json.dumps(plan).encode()).decode()}
                if '/git/ref/' in path:
                    return {'object':{'type':'commit','sha':self.plan['starter_commit']}}
                repo = path.removeprefix('/repos/')
                self.assertIn(repo, visibility)
                if method == 'PATCH':
                    visibility[repo] = payload['private']
                    operations.append(('github-visibility', repo, payload['private']))
                return {'full_name':repo,'private':visibility[repo],'default_branch':'main'}
            clock = Mock(wraps=datetime)
            clock.now.return_value = release.utc(when)
            module = SimpleNamespace(HfApi=lambda **kwargs:hub,CommitOperationAdd=lambda **kwargs:SimpleNamespace(**kwargs),
                hf_hub_download=lambda repo, name, **kwargs:files[name])
            with patch.dict('sys.modules', {'huggingface_hub':module}), patch.dict('os.environ',
                    {'MATERIALS_RELEASE_TOKEN':token,'HF_TOKEN':'synthetic','GITHUB_ACTIONS':'false'}), \
                    patch.object(release,'configure_hub_http'), patch.object(release,'datetime',clock), patch.object(release,'github',side_effect=api), patch.object(release,'load_plan',return_value=plan):
                release.run(mode)
                if mode == 'publish':
                    release.run(mode)  # same receipt, safe completion after a repeated dispatch
            return visibility, hub.private, operations, {name:path.read_bytes() for name,path in files.items()}

    def test_verify_checks_permissions_without_releasing(self):
        repos, private, operations, files = self.exercise_fake_hosts('verify','2026-10-23T08:00:00Z')
        self.assertTrue(all(repos.values()))
        self.assertTrue(private)
        self.assertNotIn(release.RECEIPT, files)
        self.assertNotIn('participant-guide.pdf',files)
        self.assertTrue(json.loads(files['materials-release-setup.json'])['armed'])
        setup = json.loads(files['materials-release-setup.json'])
        for field in ['starter_ref','starter_commit']:
            self.assertEqual(setup[field],self.plan[field])
        import hashlib
        self.assertEqual(setup['guide_sha256'],hashlib.sha256(b'%PDF-1.7 synthetic event-day guide').hexdigest())

    def test_full_release_and_idempotent_retry_use_only_two_participant_repos(self):
        repos, private, operations, files = self.exercise_fake_hosts('publish','2026-10-24T08:00:00Z')
        self.assertFalse(any(repos.values()))
        self.assertFalse(private)
        self.assertEqual(sum(x == ('hf-file',release.RECEIPT) for x in operations), 1)
        self.assertEqual(json.loads(files[release.RECEIPT])['starter_commit'],self.plan['starter_commit'])
        self.assertFalse(any('evaluation' in str(x) for x in operations))

    def test_approved_inbox_can_open_early_without_space_starter_or_release_receipt(self):
        repos, private, operations, files = self.exercise_fake_hosts('open-inbox','2026-10-21T10:00:00Z')
        self.assertFalse(repos[release.REPOSITORIES[0]])
        self.assertTrue(repos[release.REPOSITORIES[1]])
        self.assertTrue(private)
        self.assertNotIn(release.RECEIPT, files)
        self.assertFalse(any('evaluation' in str(x) for x in operations))
        self.assertFalse(any(x[0] == 'hf-visibility' for x in operations))

    def test_verify_preserves_explicitly_approved_early_public_platform(self):
        repos, private, operations, files = self.exercise_fake_hosts('verify','2026-10-21T10:00:00Z',early_public=True)
        self.assertFalse(repos[release.REPOSITORIES[0]])
        self.assertTrue(repos[release.REPOSITORIES[1]])
        self.assertTrue(private)
        self.assertNotIn(release.RECEIPT, files)
        self.assertNotIn('participant-guide.pdf',files)
        self.assertTrue(json.loads(files['materials-release-setup.json'])['armed'])


if __name__ == '__main__':
    unittest.main()
