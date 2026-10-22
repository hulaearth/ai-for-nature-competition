import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('feedback',ROOT/'scripts/publish_feedback.py')
feedback=importlib.util.module_from_spec(spec);spec.loader.exec_module(feedback)

class FeedbackPublication(unittest.TestCase):
    def test_only_sanitized_public_documents_are_allowed(self):
        docs=feedback.documents()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'site').mkdir()
            for name,value in docs.items():(root/'site'/name).write_text(json.dumps(value))
            self.assertEqual(feedback.documents(root),docs)
            broken=copy.deepcopy(docs['receipts.json']);broken['teams']=[{'members':['private nickname']}]
            (root/'site/receipts.json').write_text(json.dumps(broken))
            with self.assertRaisesRegex(RuntimeError,'Private field'):feedback.documents(root)
            broken['teams']=[];broken['competition']='synthetic-pilot'
            (root/'site/receipts.json').write_text(json.dumps(broken))
            with self.assertRaisesRegex(RuntimeError,'destination'):feedback.documents(root)

class MirrorScheduling(unittest.TestCase):
    def test_one_snapshot_is_used_even_if_main_changes_during_reads(self):
        import base64,io
        docs=feedback.documents();calls=[];sha='a'*40
        def opener(request,timeout):
            calls.append(request.full_url)
            value=({'object':{'sha':sha}}if request.full_url.endswith('/git/ref/heads/main')else
                {'content':base64.encodebytes(json.dumps(docs[request.full_url.split('/site/')[1].split('?')[0]]).encode()).decode()})
            return io.BytesIO(json.dumps(value).encode())
        result=feedback.github_documents('synthetic-not-a-credential',opener=opener)
        self.assertEqual(result,docs)
        self.assertEqual(len(calls),5)
        self.assertTrue(all(x.endswith('?ref='+sha)for x in calls[1:]))

    def test_mirror_spacing_is_bounded_and_small_sleep_steps_are_used(self):
        from datetime import datetime,timezone,timedelta
        now=datetime(2026,10,24,10,tzinfo=timezone.utc)
        for age,expected in [(10,80),(89,1),(100,0),(-600,90)]:
            self.assertEqual(feedback.mirror_wait({'mirror_published_at_utc':(now-timedelta(seconds=age)).isoformat()},now),expected)
        steps=[];feedback.sleep_bounded(89,sleep=steps.append);self.assertEqual(steps,[30,30,29])
        self.assertEqual(feedback.mirror_wait({},now),0)

    def test_config_change_is_mirrored_even_with_unchanged_receipt_generation(self):
        first=feedback.documents();second=copy.deepcopy(first)
        second['config.json']['presentation_form_open']=not first['config.json']['presentation_form_open']
        self.assertNotEqual(feedback.fingerprint(first),feedback.fingerprint(second))

    def test_retry_schedule_is_limited_to_this_event_and_closing_window(self):
        from datetime import datetime,timezone
        cfg=feedback.documents()['config.json']
        for date,expected in [('2026-10-24T08:00:00+00:00',True),('2026-10-24T19:30:00+00:00',True),
                              ('2026-10-23T10:00:00+00:00',False),('2027-10-24T10:00:00+00:00',False),
                              ('2026-10-24T19:31:00+00:00',False)]:
            self.assertEqual(feedback.scheduled_window(cfg,datetime.fromisoformat(date)),expected)

    def exercise(self,versions,current,commit_error=None):
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        snapshot=Path(folder.name)/'current.json';snapshot.write_text(json.dumps(current))
        hub=Mock();hub.repo_info.return_value=SimpleNamespace(sha='b'*40)
        hub.create_commit.side_effect=commit_error if commit_error else lambda **k:SimpleNamespace(oid='c'*40)
        module=SimpleNamespace(HfApi=lambda **k:hub,hf_hub_download=lambda *a,**k:snapshot,CommitOperationAdd=lambda **k:SimpleNamespace(**k))
        wait=Mock()
        with patch.dict('sys.modules',{'huggingface_hub':module}),patch.dict('os.environ',{'HF_TOKEN':'synthetic','GITHUB_TOKEN':'synthetic'}),\
             patch.object(feedback,'configure_hub_http'),patch.object(feedback,'github_documents',side_effect=versions),\
             patch.object(feedback,'sleep_bounded',wait):
            feedback.publish()
        return hub,wait

    def test_burst_publishes_latest_trusted_snapshot_after_spacing(self):
        first=feedback.documents();latest=copy.deepcopy(first)
        latest['receipts.json']['generation']+=1
        hub,wait=self.exercise([first,latest],first['receipts.json'])
        self.assertEqual(hub.create_commit.call_count,1)
        ops=hub.create_commit.call_args.kwargs['operations']
        sent=json.loads(next(x.path_or_fileobj for x in ops if x.path_in_repo=='receipts.json'))
        self.assertEqual(sent['generation'],latest['receipts.json']['generation'])
        self.assertIn('mirror_content_sha256',sent);self.assertIn('mirror_published_at_utc',sent)
        self.assertEqual(hub.create_commit.call_args.kwargs['parent_commit'],'b'*40)

    def test_identical_and_newer_mirrors_do_not_make_empty_or_old_commits(self):
        docs=feedback.documents()
        for current in [dict(docs['receipts.json'],mirror_content_sha256=feedback.fingerprint(docs)),
                        dict(docs['receipts.json'],generation=docs['receipts.json']['generation']+1)]:
            hub,wait=self.exercise([docs],current)
            hub.create_commit.assert_not_called();wait.assert_not_called()

    def test_long_provider_cooldown_is_not_retried_in_a_tight_loop(self):
        from types import SimpleNamespace
        docs=feedback.documents();error=RuntimeError('synthetic quota')
        error.response=SimpleNamespace(status_code=429,headers={'retry-after':'3600'})
        with self.assertRaisesRegex(RuntimeError,'rate-limited'):
            self.exercise([docs,copy.deepcopy(docs)],docs['receipts.json'],commit_error=error)
