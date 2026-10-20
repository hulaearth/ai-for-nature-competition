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
                       {'guide_sha256':'0'*64}]:
            real_read = Path.read_text
            def read(path, *args, **kwargs):
                return json.dumps({**self.plan, **change}) if path == original else real_read(path, *args, **kwargs)
            with patch.object(Path, 'read_text', read):
                with self.assertRaises(release.ReleaseError):
                    release.load_plan()

    def exercise_fake_hosts(self, mode, when, token='synthetic'):
        import base64
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            files = {'participant-guide.pdf': release.ROOT / 'site/participant-guide.pdf'}
            visibility = {repo: True for repo in release.REPOSITORIES}
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
            hub = Hub()
            def api(token, method, path, payload=None):
                if '/contents/' in path:
                    return {'content':base64.b64encode(json.dumps(self.plan).encode()).decode()}
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
            module = SimpleNamespace(HfApi=lambda **kwargs:hub,
                hf_hub_download=lambda repo, name, **kwargs:files[name])
            with patch.dict('sys.modules', {'huggingface_hub':module}), patch.dict('os.environ',
                    {'MATERIALS_RELEASE_TOKEN':token,'HF_TOKEN':'synthetic','GITHUB_ACTIONS':'false'}), \
                    patch.object(release,'datetime',clock), patch.object(release,'github',side_effect=api):
                release.run(mode)
                if mode == 'publish':
                    release.run(mode)  # same receipt, safe completion after a repeated dispatch
            return visibility, hub.private, operations, {name:path.read_bytes() for name,path in files.items()}

    def test_verify_checks_permissions_without_releasing(self):
        repos, private, operations, files = self.exercise_fake_hosts('verify','2026-10-23T08:00:00Z')
        self.assertTrue(all(repos.values()))
        self.assertTrue(private)
        self.assertNotIn(release.RECEIPT, files)
        self.assertTrue(json.loads(files['materials-release-setup.json'])['armed'])

    def test_full_release_and_idempotent_retry_use_only_two_participant_repos(self):
        repos, private, operations, files = self.exercise_fake_hosts('publish','2026-10-24T08:00:00Z')
        self.assertFalse(any(repos.values()))
        self.assertFalse(private)
        self.assertEqual(sum(x == ('hf-file',release.RECEIPT) for x in operations), 1)
        self.assertEqual(json.loads(files[release.RECEIPT])['starter_commit'],self.plan['starter_commit'])
        self.assertFalse(any('evaluation' in str(x) for x in operations))


if __name__ == '__main__':
    unittest.main()
