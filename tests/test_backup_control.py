import base64
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlsplit, parse_qs

spec = importlib.util.spec_from_file_location('backup_control', Path(__file__).parents[1]/'scripts/backup_control.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class FakeGitHub:
    def __init__(self, config):
        self.config = copy.deepcopy(config)
        names = [p for group in config['profiles'].values() for p in group]
        self.workflows = [{'id': i+1, 'name': n, 'path': '.github/workflows/'+n, 'state': 'active'} for i,n in enumerate(names)]
        self.workflows += [{'id': 90, 'name': 'unknown future workflow', 'path': '.github/workflows/new.yml', 'state': 'active'},
                           {'id': 99, 'name': 'control', 'path': control.CONTROL, 'state': 'active'}]
        self.files = {control.CONFIG: config}
        self.runs = [{'id': 10, 'workflow_id': 1, 'status': 'queued'},
                     {'id': 11, 'workflow_id': 90, 'status': 'in_progress'},
                     {'id': 12, 'workflow_id': 99, 'status': 'in_progress'}]
        self.calls = []

    def __call__(self, method, path, body=None, allowed=()):
        self.calls.append((method, path))
        prefix = '/repos/'+self.config['repository']
        self_path = path.removeprefix(prefix)
        parsed = urlsplit(self_path)
        if method == 'GET' and not self_path:
            return {'full_name': self.config['repository'], 'default_branch': 'main', 'private': True}
        if parsed.path == '/actions/workflows':
            return {'workflows': copy.deepcopy(self.workflows)}
        if parsed.path == '/actions/runs':
            status = parse_qs(parsed.query)['status'][0]
            return {'workflow_runs': [copy.deepcopy(r) for r in self.runs if r['status'] == status]}
        if parsed.path.startswith('/contents/'):
            name = parsed.path.removeprefix('/contents/')
            if method == 'GET':
                return ({'sha': 'a'*40, 'content': base64.b64encode((json.dumps(self.files[name], indent=2)+'\n').encode()).decode()}
                        if name in self.files else None)
            self.files[name] = json.loads(base64.b64decode(body['content']))
            return {'content': {'sha': 'b'*40}}
        if parsed.path.startswith('/actions/workflows/'):
            identifier, action = parsed.path.split('/')[-2:]
            next(w for w in self.workflows if w['id'] == int(identifier))['state'] = 'active' if action == 'enable' else 'disabled_manually'
            return None
        if parsed.path.endswith('/cancel') or parsed.path.endswith('/force-cancel'):
            identifier = int(parsed.path.split('/')[-2])
            next(r for r in self.runs if r['id'] == identifier)['status'] = 'completed'
            return None
        raise AssertionError((method,path))


class BackupControlTests(unittest.TestCase):
    def setUp(self):
        self.config = control.load_config()
        self.config.update(runtime_enabled=False, releases_enabled=False)
        self.api = FakeGitHub(self.config)

    def test_standby_gate_refuses_before_network_or_secret_use(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'config').mkdir()
            (root/control.CONFIG).write_text(json.dumps(self.config))
            for capability in ('runtime', 'releases'):
                with self.assertRaises(control.ControlError):
                    control.require(capability,root)

    def test_missing_invalid_or_cross_destination_config_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(control.ControlError):control.require('runtime',root)
            (root/'config').mkdir()
            for changes in [{'repository': 'attacker/other'}, {'runtime_enabled': 'true'}, {'releases_enabled': None}]:
                (root/control.CONFIG).write_text(json.dumps({**self.config,**changes}))
                with self.assertRaises(control.ControlError):control.require('runtime',root)

    def test_stop_disables_unknown_workflows_and_cancels_both_run_types(self):
        result = control.operate('stop',self.config,self.api,own_run='12',sleep=lambda _:None)
        self.assertTrue(result['all_stopped'])
        self.assertTrue(all(w['state'] != 'active' for w in self.api.workflows if w['path'] != control.CONTROL))
        self.assertEqual(next(w for w in self.api.workflows if w['id']==99)['state'],'active')
        self.assertEqual(next(r for r in self.api.runs if r['id']==12)['status'],'in_progress')
        self.assertFalse(self.api.files[control.CONFIG]['runtime_enabled'])
        self.assertTrue(self.api.files[control.RECEIPT]['all_stopped'])

    def test_stop_is_idempotent_and_preserves_event_and_secrets(self):
        control.operate('stop',self.config,self.api,sleep=lambda _:None)
        second=control.operate('stop',self.api.files[control.CONFIG],self.api,sleep=lambda _:None)
        self.assertTrue(second['all_stopped'])
        self.assertEqual(set(self.api.files),{control.CONFIG,control.RECEIPT})
        self.assertFalse(any('/secrets' in p or '/dispatches' in p for _,p in self.api.calls))

    def test_incomplete_cancellation_fails_and_records_remaining_runs(self):
        def refusing_cancel(method,path,body=None,allowed=()):
            if path.endswith('/cancel') or path.endswith('/force-cancel'):
                return None
            return self.api(method,path,body,allowed)
        with self.assertRaisesRegex(control.ControlError,'Stop is incomplete'):
            control.operate('stop',self.config,refusing_cancel,own_run='12',sleep=lambda _:None)
        self.assertFalse(self.api.files[control.RECEIPT]['all_stopped'])
        self.assertTrue(self.api.files[control.RECEIPT]['active_runs'])
        self.assertFalse(self.api.files[control.CONFIG]['runtime_enabled'])

    def test_runtime_activation_closes_a_previously_enabled_release_gate(self):
        previous={**self.config,'releases_enabled':True}
        self.api.files[control.CONFIG]=previous
        result=control.operate('enable-runtime',previous,self.api,confirmation=control.CONFIRM)
        self.assertTrue(result['runtime_enabled']);self.assertFalse(result['releases_enabled'])
        states={Path(w['path']).name:w['state'] for w in self.api.workflows}
        self.assertTrue(all(states[n]!='active' for n in self.config['profiles']['releases']))

    def test_status_is_read_only(self):
        result=control.operate('status',self.config,self.api)
        self.assertFalse(result['all_stopped'])
        self.assertTrue(all(m=='GET' for m,_ in self.api.calls))

    def test_all_activation_modes_require_explicit_confirmation(self):
        for mode in ('enable-checks','enable-runtime','enable-releases'):
            with self.assertRaises(control.ControlError):control.operate(mode,self.config,self.api)
        self.assertFalse(self.api.calls)

    def test_checks_enable_does_not_open_runtime_or_release_gates(self):
        control.operate('stop',self.config,self.api,sleep=lambda _:None)
        result=control.operate('enable-checks',self.api.files[control.CONFIG],self.api,confirmation=control.CONFIRM)
        self.assertFalse(result['runtime_enabled']);self.assertFalse(result['releases_enabled'])
        active={Path(w['path']).name for w in self.api.workflows if w['state']=='active'}
        self.assertEqual(active,{'backup-control.yml',*self.config['profiles']['checks']})

    def test_runtime_enable_never_enables_releases(self):
        control.operate('stop',self.config,self.api,sleep=lambda _:None)
        result=control.operate('enable-runtime',self.api.files[control.CONFIG],self.api,confirmation=control.CONFIRM)
        self.assertTrue(result['runtime_enabled']);self.assertFalse(result['releases_enabled'])
        states={Path(w['path']).name:w['state'] for w in self.api.workflows}
        self.assertTrue(all(states[n]!='active' for n in self.config['profiles']['releases']))
        self.assertTrue(all(states[n]=='active' for n in self.config['profiles']['runtime']))

    def test_releases_are_separate_and_not_dispatched(self):
        control.operate('stop',self.config,self.api,sleep=lambda _:None)
        result=control.operate('enable-releases',self.api.files[control.CONFIG],self.api,confirmation=control.CONFIRM)
        self.assertFalse(result['runtime_enabled']);self.assertTrue(result['releases_enabled'])
        self.assertFalse(any('/dispatches' in path for _,path in self.api.calls))

    def test_missing_workflow_does_not_change_configuration(self):
        self.api.workflows=[w for w in self.api.workflows if Path(w['path']).name not in self.config['profiles']['runtime']]
        with self.assertRaises(control.ControlError):
            control.operate('enable-runtime',self.config,self.api,confirmation=control.CONFIRM)
        self.assertEqual(self.api.files[control.CONFIG],self.config)

    def test_repository_privacy_guard(self):
        config={**self.config,'repository':'hulaearth/ai-for-nature-evaluation'}
        api=FakeGitHub(config)
        def public(method,path,body=None,allowed=()):
            value=api(method,path,body,allowed)
            if isinstance(value,dict) and 'private' in value:value['private']=False
            return value
        with self.assertRaises(control.ControlError):control.operate('stop',config,public)


if __name__=='__main__':unittest.main()
