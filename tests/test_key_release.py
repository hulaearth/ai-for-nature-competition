import hashlib
import ast
import base64
import importlib.util
import io
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

spec = importlib.util.spec_from_file_location('release', Path(__file__).parents[1] / 'scripts/release_test_key.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        # Deliberately synthetic identity; no real test unlock material is used in tests.
        self.identity = 'AGE-SECRET-KEY-1' + 'A' * 59 + '\n'
        self.at = datetime(2026, 10, 24, 13, tzinfo=timezone.utc)
        self.plan = dict(competition_id='synthetic', dataset_release='synthetic',
                         not_before_utc=self.at.isoformat(), expires_utc=(self.at + timedelta(hours=2)).isoformat(),
                         identity_sha256=hashlib.sha256(self.identity.encode()).hexdigest())

    def test_never_builds_public_payload_early(self):
        with self.assertRaises(release.ReleaseError):
            release.payload(self.plan, self.identity, self.at - timedelta(microseconds=1))
        self.assertEqual(release.payload(self.plan, self.identity, self.at)['identity'], self.identity)

    def test_rejects_wrong_identity_and_submission_key(self):
        for value in ['-----BEGIN PRIVATE KEY-----', self.identity.replace('A', 'B'), '']:
            with self.assertRaises(release.ReleaseError):
                release.identity_from(value, self.plan['identity_sha256'])

    def test_comments_and_crlf_do_not_change_identity(self):
        value = '# synthetic test comment\r\n' + self.identity.replace('\n', '\r\n')
        self.assertEqual(release.identity_from(value, self.plan['identity_sha256']), self.identity)

    def test_expired_or_naive_clock_is_rejected(self):
        for value in [self.at.replace(tzinfo=None), self.at + timedelta(days=365)]:
            with self.assertRaises(release.ReleaseError):
                release.guard(self.plan, value)

    def test_warmup_waits_until_server_time(self):
        times = iter([self.at - timedelta(seconds=11), self.at - timedelta(seconds=1), self.at])
        sleeps = []
        release.wait_until_release(self.plan, clock=lambda: next(times), sleep=sleeps.append)
        self.assertEqual(sleeps, [10, 1])

    def test_early_warmup_is_bounded(self):
        with self.assertRaises(release.ReleaseError):
            release.wait_until_release(self.plan, clock=lambda: self.at - timedelta(days=1))

    def test_requested_saturday_time_and_later_deployments(self):
        plan = release.load_plan()
        german = release.utc(plan['not_before_utc']).astimezone(ZoneInfo('Europe/Berlin'))
        self.assertEqual((german.year, german.month, german.day, german.hour, german.minute, german.weekday()),
                         (2026, 10, 24, 13, 30, 5))
        tree = ast.parse((release.ROOT / 'scripts/deploy_space.py').read_text())
        files = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'FILES' for t in n.targets))
        self.assertNotIn(release.PUBLICATION, files)
        self.assertNotIn(release.IDENTITY_FILE, files)

    def test_changed_main_branch_plan_stops_old_warmup(self):
        changed = dict(self.plan, not_before_utc=(self.at + timedelta(days=1)).isoformat())
        response = json.dumps({'content': base64.b64encode(json.dumps(changed).encode()).decode()}).encode()
        env = {'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': 'hulaearth/ai-for-nature-competition',
               'GITHUB_TOKEN': 'synthetic-test-token'}
        with patch.dict('os.environ', env), patch.object(release.urllib.request, 'urlopen', return_value=io.BytesIO(response)):
            with self.assertRaises(release.ReleaseError):
                release.check_current_main_plan(self.plan)

    def test_setup_receipt_contains_no_unlock_identity(self):
        receipt = release.setup_receipt(self.plan, self.at - timedelta(days=1))
        self.assertNotIn(self.identity.strip(), json.dumps(receipt))
        self.assertNotIn('identity', receipt)
        self.assertTrue(receipt['secret_fingerprint_verified'])
        self.assertFalse(receipt['key_published'])


if __name__ == '__main__':
    unittest.main()
