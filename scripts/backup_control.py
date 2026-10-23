#!/usr/bin/env python3
"""Explicit standby/activation control. No release, scoring or secret-value access."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
import base64

ROOT = Path(__file__).resolve().parents[1]
CONFIG = 'config/backup-control.json'
RECEIPT = 'config/backup-status.json'
CONTROL = '.github/workflows/backup-control.yml'
REPOSITORIES = {'hulaearth/ai-for-nature-competition', 'hulaearth/ai-for-nature-evaluation'}
MODES = ('status', 'stop', 'enable-checks', 'enable-runtime', 'enable-releases')
CONFIRM = 'ACTIVATE HF BACKUP'


class ControlError(RuntimeError):
    pass


def load_config(root=ROOT):
    try:
        config = json.loads((Path(root)/CONFIG).read_text())
        if (config.get('schema_version') != 1 or config.get('repository') not in REPOSITORIES
                or type(config.get('runtime_enabled')) is not bool
                or type(config.get('releases_enabled')) is not bool
                or set(config.get('profiles', {})) != {'checks', 'runtime', 'releases'}):
            raise ValueError()
        paths = [path for group in config['profiles'].values() for path in group]
        if (any(not isinstance(group, list) for group in config['profiles'].values())
                or any(not isinstance(p, str) or '/' in p or not p.endswith('.yml') for p in paths)
                or 'backup-control.yml' in paths or len(paths) != len(set(paths))):
            raise ValueError()
        return config
    except (OSError, ValueError, TypeError):
        raise ControlError('Missing or invalid backup control; operations remain stopped.') from None


def require(capability, root=ROOT):
    config = load_config(root)
    if capability not in ('runtime', 'releases') or config[capability+'_enabled'] is not True:
        raise ControlError('HF backup is in standby for '+capability+'. Use Backup platform control explicitly.')
    return True


class GitHub:
    def __init__(self, token):
        if not token:
            raise ControlError('GITHUB_TOKEN or GH_TOKEN with this repository Actions/Contents write is required.')
        self.token = token

    def __call__(self, method, path, body=None, allowed=(200, 201, 202, 204)):
        request = urllib.request.Request('https://api.github.com'+path, method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={'Authorization': 'Bearer '+self.token, 'Accept': 'application/vnd.github+json',
                     'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json',
                     'User-Agent': 'ai-for-nature-backup-control'})
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                if response.status not in allowed:
                    raise ControlError('Unexpected GitHub API status '+str(response.status))
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            if error.code in allowed:
                return None
            raise ControlError('GitHub API HTTP '+str(error.code)+' for '+method+' '+path) from None
        except (urllib.error.URLError, TimeoutError, ValueError):
            raise ControlError('GitHub API unavailable; verify state before retrying.') from None


def pages(api, prefix, field):
    rows = []
    for page in range(1, 21):
        data = api('GET', prefix+('&' if '?' in prefix else '?')+f'per_page=100&page={page}')
        part = data[field]
        rows.extend(part)
        if len(part) < 100:
            return rows
    raise ControlError('Pagination bound reached; inspect repository before continuing.')


def workflows(api, repo):
    return pages(api, '/repos/'+repo+'/actions/workflows', 'workflows')


def active_runs(api, repo, controlled_ids, own_run):
    # Query statuses separately so an old queued job cannot hide behind recent completions.
    found = {}
    for status in ('queued', 'in_progress', 'waiting', 'pending', 'requested'):
        for run in pages(api, '/repos/'+repo+'/actions/runs?status='+status, 'workflow_runs'):
            if run['workflow_id'] in controlled_ids and str(run['id']) != str(own_run) and run['status'] != 'completed':
                found[run['id']] = run
    return list(found.values())


def put_document(api, repo, path, document, message):
    current = api('GET', '/repos/'+repo+'/contents/'+path+'?ref=main', allowed=(200, 404))
    raw = (json.dumps(document, indent=2)+'\n').encode()
    if current and base64.b64decode(current['content']) == raw:
        return
    payload = {'message': message, 'branch': 'main', 'content': base64.b64encode(raw).decode()}
    if current:
        payload['sha'] = current['sha']
    api('PUT', '/repos/'+repo+'/contents/'+path, payload)


def snapshot(api, config, own_run=''):
    repo = config['repository']
    items = workflows(api, repo)
    controlled = [w for w in items if w['path'] != CONTROL]
    runs = active_runs(api, repo, {w['id'] for w in controlled}, own_run)
    return {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'repository': repo,
            'runtime_enabled': config['runtime_enabled'], 'releases_enabled': config['releases_enabled'],
            'workflows': [{k: w[k] for k in ('id', 'name', 'path', 'state')} for w in controlled],
            'active_runs': [{k: r[k] for k in ('id', 'workflow_id', 'status')} for r in runs],
            'all_stopped': (not config['runtime_enabled'] and not config['releases_enabled']
                            and all(w['state'] != 'active' for w in controlled) and not runs)}


def operate(mode, config, api, *, confirmation='', own_run='', sleep=time.sleep):
    if mode not in MODES:
        raise ControlError('Unknown control mode.')
    if mode.startswith('enable-') and confirmation != CONFIRM:
        raise ControlError('Activation requires the explicit confirmation: '+CONFIRM)
    repo = config['repository']
    metadata = api('GET', '/repos/'+repo)
    if (metadata['full_name'].lower() != repo or metadata['default_branch'] != 'main'
            or (repo.endswith('-evaluation') and metadata['private'] is not True)):
        raise ControlError('Repository/default-branch/privacy guard failed.')
    if mode == 'status':
        return snapshot(api, config, own_run)
    config = json.loads(json.dumps(config))
    listed = workflows(api, repo)
    managed = [w for w in listed if w['path'] != CONTROL]
    by_name = {Path(w['path']).name: w for w in managed}
    if mode.startswith('enable-'):
        profile = mode.removeprefix('enable-')
        intended = config['profiles'][profile]
        if profile == 'runtime':
            intended = intended+config['profiles']['checks']
        if any(name not in by_name for name in intended):
            raise ControlError('Expected activation workflow is missing; configuration unchanged.')
    if mode == 'stop':
        config.update(runtime_enabled=False, releases_enabled=False)
    elif mode == 'enable-runtime':
        config.update(runtime_enabled=True, releases_enabled=False)
    elif mode == 'enable-releases':
        config['releases_enabled'] = True
    # Checks do not change either operational gate.
    put_document(api, repo, CONFIG, config, 'Set HF backup control: '+mode)
    if mode == 'stop':
        for workflow in managed:
            if workflow['state'] == 'active':
                api('PUT', f'/repos/{repo}/actions/workflows/{workflow["id"]}/disable')
        ids = {w['id'] for w in managed}
        pending = active_runs(api, repo, ids, own_run)
        for run in pending:
            api('POST', f'/repos/{repo}/actions/runs/{run["id"]}/cancel', allowed=(202, 409))
        for attempt in range(10):
            pending = active_runs(api, repo, ids, own_run)
            if not pending:
                break
            if attempt == 3:
                for run in pending:
                    api('POST', f'/repos/{repo}/actions/runs/{run["id"]}/force-cancel', allowed=(202, 409))
            sleep(3)
    else:
        profile = mode.removeprefix('enable-')
        names = config['profiles'][profile]
        if profile == 'runtime':
            names = names+config['profiles']['checks']
            # Runtime activation cannot accidentally restore a scheduled release.
            for name in config['profiles']['releases']:
                if name in by_name and by_name[name]['state'] == 'active':
                    api('PUT', f'/repos/{repo}/actions/workflows/{by_name[name]["id"]}/disable')
        for name in names:
            if name not in by_name:
                raise ControlError('Expected workflow is missing: '+name)
            api('PUT', f'/repos/{repo}/actions/workflows/{by_name[name]["id"]}/enable')
    report = snapshot(api, config, own_run)
    report.update(mode=mode, workflow_run_id=str(own_run), control_workflow_remains_available=True,
                  event_flags_changed=False, secrets_read=False, releases_dispatched=False)
    put_document(api, repo, RECEIPT, report, 'Record verified HF backup control state')
    if mode == 'stop' and not report['all_stopped']:
        raise ControlError('Stop is incomplete: inspect backup-status.json and remaining runs.')
    if mode.startswith('enable-'):
        intended = config['profiles'][mode.removeprefix('enable-')]
        states = {Path(w['path']).name: w['state'] for w in report['workflows']}
        if any(states.get(name) != 'active' for name in intended):
            raise ControlError('Activation is incomplete; inspect workflow states.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=MODES, default='status')
    parser.add_argument('--require', choices=('runtime', 'releases'))
    parser.add_argument('--output', type=Path, default=ROOT/'output/backup-control.json')
    args = parser.parse_args()
    try:
        if args.require:
            require(args.require)
            print('Explicit HF backup gate is enabled:', args.require)
            return 0
        config = load_config()
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            if os.environ.get('GITHUB_REPOSITORY') != config['repository'] or os.environ.get('GITHUB_REF') != 'refs/heads/main':
                raise ControlError('Only trusted main in the configured repository can operate this control.')
        report = operate(args.mode, config, GitHub(os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')),
                         confirmation=os.environ.get('BACKUP_ACTIVATION_CONFIRMATION', ''),
                         own_run=os.environ.get('GITHUB_RUN_ID', ''))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2))
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as out:
                out.write('## HF backup control\n\n```json\n'+json.dumps(report, indent=2)+'\n```\n')
        return 0
    except ControlError as error:
        print('Backup control: '+str(error))
        return 1
    except Exception:
        print('Backup control stopped safely; inspect workflow state before retrying. No credential was logged.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
