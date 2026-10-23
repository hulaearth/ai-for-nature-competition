#!/usr/bin/env python3
"""Build dependency-free static competition pages. No evaluation data is read here."""
from pathlib import Path
from html import escape
import base64
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
REGISTER = "#register"
WORDMARK = (ROOT / "scripts/content/wordmark.svg").read_text()
NOMINATE = "https://github.com/hulaearth/ai-for-nature-competition/issues/new?template=nomination.yml"
SUBMISSION_FORM = (ROOT / 'scripts/submission_form.html').read_text()
REGISTRATION_FORM = (ROOT / 'scripts/registration_form.html').read_text()
UPLOAD_SHELL = (ROOT / 'scripts/upload_shell.html').read_text()
SUBMISSION_ASSET = 'submission.js?v='+hashlib.sha256((SITE/'submission.js').read_bytes()).hexdigest()[:16]
UPLOAD_SHELL = UPLOAD_SHELL.replace('src="submission.js"', 'src="'+SUBMISSION_ASSET+'"')
(SITE / 'upload.html').write_text(UPLOAD_SHELL.replace('{{SUBMISSION_FORM}}', SUBMISSION_FORM+REGISTRATION_FORM))
INLINE_UPLOAD = re.sub(r'id="([^"]+)"', lambda m: 'id="upload-'+m[1]+'"', SUBMISSION_FORM).replace('<h2>', '<h3>').replace('</h2>', '</h3>')
CSS = (SITE / "style.css").read_text()
CSS_HASH = base64.b64encode(hashlib.sha256(CSS.encode()).digest()).decode()
ENVELOPE = re.sub(r'^export ', '', (SITE / 'envelope.js').read_text(), flags=re.MULTILINE)
APP = (SITE / 'app.js').read_text()
assert APP.startswith('import {encryptCSV, validateCSV, parseCSV} from "./envelope.js";\n')
SCRIPT = (SITE / 'navigation.js').read_text() + '\n(async () => {\n' + ENVELOPE + '\n' + APP.split('\n', 1)[1] + '\n})();\n'
SCRIPT_HASH = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
assert '</script' not in SCRIPT.lower()
# Keep the immutable data contract aligned in both fetchable and embedded config.
# Runtime flags, team state and receipts still come from the private publisher.
CONTRACT_KEYS = ['competition_id', 'dataset_release', 'dataset_manifest_sha256', 'starter_commit',
                 'expected_rows', 'max_csv_bytes', 'max_envelope_bytes',
                 'submission_key_id', 'max_final_submissions', 'max_practice_submissions',
                 'space_id', 'scoring_policy', 'data_release_utc', 'data_release_policy',
                 'alphaearth_drive_url', 'alphaearth_hf_url', 'alphaearth_hf_ready']
frozen_contract = json.loads((ROOT / 'config/challenge.json').read_text())
public_config = json.loads((SITE / 'config.json').read_text())
for key in CONTRACT_KEYS:
    public_config[key] = frozen_contract[key]
(SITE / 'config.json').write_text(json.dumps(public_config, indent=2) + '\n')
PUBLIC_DATA = {name: json.loads((SITE / name).read_text()) for name in ['config.json', 'teams.json', 'leaderboard.json', 'submission-key.json']}
PUBLIC_DATA['test-key-plan.json'] = json.loads((ROOT / 'config/test-key-release.json').read_text())
(SITE / 'test-key-plan.json').write_text(json.dumps(PUBLIC_DATA['test-key-plan.json'], indent=2) + '\n')
PUBLIC_DATA['practice_submission.csv'] = (SITE / 'practice_submission.csv').read_text()
PUBLIC_JSON = json.dumps(PUBLIC_DATA, ensure_ascii=True).replace('<', '\\u003c')


SCHEDULE = json.loads((ROOT / 'config/schedule.json').read_text())
SCHEDULE_ROWS = ''.join('<tr><th scope="row">'+escape(time)+'</th><td>'+escape(activity)+'</td></tr>' for time, activity in SCHEDULE['rows'])
SCHEDULE_HTML = '<h3>Saturday 24 October 2026</h3><p>All times: Europe/Berlin, CEST / MESZ (UTC+02:00). Work: 11:00–17:30 (6.5 hours).</p><div class="table-wrap"><table><thead><tr><th>German time</th><th>Program</th></tr></thead><tbody>'+SCHEDULE_ROWS+'</tbody></table></div>'


def layout(title, page, *, integrated=True):
    config = json.loads((ROOT / "config/challenge.json").read_text())
    drive_url = config.get("alphaearth_drive_url") or config.get("drive_url")
    upload_module = '<script type="module" src="'+SUBMISSION_ASSET+'"></script>' if integrated else ''
    upload_flag = ' data-integrated-upload="true"' if integrated else ''
    initial = 'challenge' if page == 'index.html' else Path(page).stem
    views = []
    for path, view_title, view_content in PAGES:
        route = 'challenge' if path == 'index.html' else Path(path).stem
        if route == 'data' and config.get('alphaearth_hf_ready') is True:
            public_rasters = ('<div class="notice"><strong>German AlphaEarth is ready on Hugging Face.</strong>'
                '<p><a href="https://huggingface.co/datasets/HulaEarth/alphaearth-germany-2024/tree/main" '
                'target="_blank" rel="noopener noreferrer">Download the public AlphaEarth tiles ↗</a> '
                '(87 GeoTIFFs, 148.57 GB), or use the separate Drive folder above. All tile sizes and '
                'SHA256 identifiers match; technical notes and source licenses are included. '
                'This public dataset contains only the native German rasters. The other competition '
                'data remain restricted until their event-day release.</p></div>')
            view_content = view_content.replace('<div class="notice"><strong>Two download stages.</strong>',
                                                public_rasters+'<div class="notice"><strong>Two download stages.</strong>')
            view_content = view_content.replace(
                'A separate HF mirror is being prepared and is not yet certified complete.',
                'The separate <a href="https://huggingface.co/datasets/HulaEarth/alphaearth-germany-2024" target="_blank" rel="noopener noreferrer">public HF raster mirror</a> is complete and verified.')
        if drive_url and drive_url.startswith("https://drive.google.com/"):
            view_content = view_content.replace('href="#" aria-disabled="true" data-drive>Challenge data link forthcoming',
                                                'href="'+escape(drive_url,quote=True)+'" target="_blank" rel="noopener noreferrer" data-drive>Download German AlphaEarth ↗')
            view_content = view_content.replace('data-drive-address>Link forthcoming',
                                                'data-drive-address>'+escape(drive_url))
        for target, _, _ in PAGES:
            target_route = 'challenge' if target == 'index.html' else Path(target).stem
            view_content = view_content.replace('href="'+target+'"', 'href="#'+target_route+'"')
        hidden = '' if route == initial else ' hidden'
        views.append(f'<section id="view-{route}" data-view="{route}" data-title="{escape(view_title,quote=True)} · AI for Nature"{hidden}>{view_content}</section>')
    content = '\n'.join(views)
    nav = ''.join(f'<a href="#{"challenge" if path == "index.html" else Path(path).stem}"'+(' aria-current="page"' if page == path else '')+f'>{name}</a>' for path, name in [
        ('index.html','Challenge'),('data.html','Data'),('rules.html','Rules'),('guide.html','Guide'),('register.html','Register'),('submit.html','Submit'),('leaderboard.html','Leaderboard')])
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#102d27"><meta name="description" content="A bird habitat modeling hackathon using German bird observations and AlphaEarth embeddings.">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; connect-src 'self' https://raw.githubusercontent.com https://huggingface.co; script-src 'self' 'sha256-{SCRIPT_HASH}'; style-src 'self' 'sha256-{CSS_HASH}'; img-src 'self' data:; object-src 'none'; base-uri 'self'; form-action https://github.com">
<title>{title} · AI for Nature</title><style>{CSS}</style></head>
<body data-initial-page="{initial}"{upload_flag}><a class="skip" href="#main">Skip to content</a><header class="nav"><a class="brand" href="#challenge">{WORDMARK}<small>× AI for Nature</small></a><nav aria-label="Main navigation">{nav}</nav></header>
<aside class="backup-banner" aria-label="Backup platform notice">Backup competition platform · Use this site only if organizers direct you here. <a href="https://ai-for-nature.hula.earth/" target="_blank" rel="noopener noreferrer">Main event website ↗</a></aside>
<main id="main">{content}</main>
<footer><a class="brand" href="#challenge">{WORDMARK}<small>× AI for Nature</small></a><p>Germany for learning. Nearby Central Europe for the final test.<br>Reported presence and matched background are not verified occupancy.</p><a href="{REGISTER}">Register a team ↗</a></footer>
<script id="site-data" type="application/json">{PUBLIC_JSON}</script>
<script>{SCRIPT}</script>{upload_module}</body></html>'''


def heading(kicker, title, intro):
    return f'<section class="page-heading"><p class="eyebrow">{kicker}</p><h1>{title}</h1><p class="intro">{intro}</p></section>'


def content(name):
    """Load participant prose; functional fragments remain in their original templates."""
    text = (ROOT / 'scripts/content' / (name + '.html')).read_text()
    registration = re.sub(r'id="([^"]+)"', lambda m: 'id="upload-'+m[1]+'"', REGISTRATION_FORM).replace('<h2>', '<h3>').replace('</h2>', '</h3>')
    for marker, value in {
        '{{SCHEDULE_HTML}}': SCHEDULE_HTML,
        '{{INLINE_UPLOAD}}': INLINE_UPLOAD,
        '{{REGISTRATION_FORM}}': registration,
        '{{LEADERBOARD_PREVIEW}}': (ROOT / 'scripts/leaderboard_preview.html').read_text(),
    }.items():
        text = text.replace(marker, value)
    assert '{{' not in text, 'Unresolved content placeholder: ' + name
    return text


home = content('challenge')
data_page = content('data')
rules = content('rules')
guide = content('guide')
register = content('register')
submit = content('submit')
leaderboard = content('leaderboard')

PAGES = [('index.html','Bird habitat challenge',home),('data.html','Data and inputs',data_page),('rules.html','Competition rules',rules),('guide.html','Practical participant guide',guide),('register.html','Register your team',register),('submit.html','Submit predictions',submit),('leaderboard.html','Leaderboard',leaderboard)]
for name, title, content in PAGES:
    (SITE / name).write_text(layout(title, name))
print('Built seven static pages and participant guide links')

# Keep the backup current while preserving its attachment controls.
main_pages=PAGES
backup=(ROOT/'scripts/legacy_submit_content.html').read_text()
PAGES=[(path,title,backup if path=='submit.html'else content)for path,title,content in main_pages]
(SITE/'legacy-submit.html').write_text(layout('Backup prediction delivery','submit.html',integrated=False))
PAGES=main_pages
