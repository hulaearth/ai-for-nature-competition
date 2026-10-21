#!/usr/bin/env python3
"""Public-only structural, link and contract checks."""
from html.parser import HTMLParser
import csv
import base64
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1];SITE=ROOT/'site'


class Document(HTMLParser):
    def __init__(self):
        super().__init__();self.headings=0;self.references=[];self.ids=[]
        self.styles=[];self.in_style=False;self.csp=''
        self.scripts=[];self.in_script=False;self.views=[];self.initial=''
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='h1':self.headings+=1
        if tag=='style':self.in_style=True;self.styles.append('')
        if tag=='script':self.in_script=True;self.scripts.append({'type':a.get('type',''),'src':a.get('src'),'text':''})
        if tag=='body':self.initial=a.get('data-initial-page','')
        if 'data-view' in a:self.views.append(a)
        if tag=='meta' and a.get('http-equiv','').lower()=='content-security-policy':self.csp=a.get('content','')
        if 'id' in a:self.ids.append(a['id'])
        for key in ['href','src']:
            if key in a:self.references.append(a[key])
    def handle_endtag(self,tag):
        if tag=='style':self.in_style=False
        if tag=='script':self.in_script=False
    def handle_data(self,data):
        if self.in_style:self.styles[-1]+=data
        if self.in_script:self.scripts[-1]['text']+=data


checked_scripts=set()
for page in SITE.glob('*.html'):
    d=Document();d.feed(page.read_text());assert d.headings==6,page
    assert {v['data-view'] for v in d.views}=={'challenge','data','rules','guide','submit','leaderboard'},page
    assert [v['data-view'] for v in d.views if 'hidden' not in v]==[d.initial],page
    css=(SITE/'style.css').read_text()
    assert d.styles==[css],('Page must carry the complete shared design',page)
    css_hash=base64.b64encode(hashlib.sha256(css.encode()).digest()).decode()
    assert "'sha256-"+css_hash+"'" in d.csp,('Embedded styles must be allowed by their exact hash',page)
    assert "'unsafe-inline'" not in d.csp,page
    assert len(d.scripts)==2 and all(s['src'] is None for s in d.scripts),page
    script=next(s['text'] for s in d.scripts if s['type']!='application/json')
    script_hash=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    assert "'sha256-"+script_hash+"'" in d.csp,('Inline logic must be allowed by its exact hash',page)
    if script_hash not in checked_scripts:
        subprocess.run(['node','--check'],input=script,text=True,check=True,capture_output=True)
        checked_scripts.add(script_hash)
    public=json.loads(next(s['text'] for s in d.scripts if s['type']=='application/json'))
    assert set(public)=={'config.json','teams.json','leaderboard.json','submission-key.json','practice_submission.csv','test-key-plan.json'},page
    for name,value in public.items():
        expected=(SITE/name).read_text() if name.endswith('.csv') else json.loads((SITE/name).read_text())
        assert value==expected,('Embedded public fallback must be current',page,name)
    assert len(set(d.ids))==len(d.ids),page
    for ref in d.references:
        u=urlsplit(ref)
        if not u.scheme and u.path:assert (SITE/u.path).is_file(),(page,ref)
    assert all(term not in page.read_text() for term in ['grid_id','BioT','Bavaria','macro_auroc','UTC-daily']),page
    assert '1a7b2U9YQRhpJG5TsPhPa1hHkVUpeOlPS' not in page.read_text(),page
    assert '1ULqUyStGWCF2osa6hzUXWuA9v9lR3kuhzu2kRWW1Z9M/edit' not in page.read_text(),page
c=json.loads((SITE/'config.json').read_text());assert c['expected_rows']==63590
assert c['max_final_submissions']==5 and c['dataset_release']=='bird-habitat-2024'
assert c['jury_performance_points']=='baseline-relative-v1'
assert c['space_id']=='HulaEarth/ai-for-nature-hula-earth'
plan=json.loads((ROOT/'config/test-key-release.json').read_text())
assert plan['not_before_utc']==c['test_release_utc']
materials=json.loads((ROOT/'config/materials-release.json').read_text())
assert materials['not_before_utc']==c['materials_release_utc']=='2026-10-24T08:00:00Z'
assert materials['starter_ref']==c['starter_ref']=='hackathon-2026'
assert len(materials['guide_sha256'])==64
assert not (SITE/'participant-guide.pdf').exists(), 'Guide must stay in private starter until release'
assert 'identity' not in plan and 'key' not in plan
assert c['preparation_policy']=='environment-checks-only'
assert c['drive_url']=='https://drive.google.com/drive/folders/1gXsJyZnI8QIbk1RQYL0qNqy1yf0eSaoT'
assert 'data-guide' in (SITE/'guide.html').read_text()
assert len(list(SITE.glob('*.html')))==6
assert len(c['dataset_manifest_sha256'])==64
assert c['dataset_manifest_sha256']==json.loads((ROOT/'config/challenge.json').read_text())['dataset_manifest_sha256']
with (SITE/'practice_submission.csv').open() as f:
    rows=list(csv.DictReader(f));assert len(rows)==120 and set(rows[0])=={'row_id','score'}
for p in SITE.iterdir():
    if p.is_file():assert b'-----BEGIN PRIVATE KEY' not in p.read_bytes(),p
print('Six styled pages, private guide gating, local links, IDs, practice schema and frozen contract passed')

policy=json.loads((ROOT/'config/scoring.json').read_text())
assert c['rubric']==policy.pop('rubric')=={'model_performance':50,'insights':30,'presentation':15,'reproducibility_checklist':5}
assert c['scoring_policy']==policy
assert policy['baseline']['starter_ref']=='hackathon-2026' and policy['stretch_ap']==.15
for page in SITE.glob('*.html'):
    text=page.read_text()
    assert '76.1 MB' in text and '188.40 GB' in text
    assert '39.8 MB' not in text and 'passed delivery checks' not in text
    assert '50 × private AP' not in text and 'Method and reproducibility</td>' not in text
    assert '19.7' in text and '26.7' in text and '38.3' in text

for page in SITE.glob('*.html'):
    text=page.read_text()
    assert '$50' not in text and 'Google GPU' not in text
    assert 'optional advanced award' not in text
    assert 'Choose / confirm final entry' in text
