import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {previewSnapshot} from '../submission-src/leaderboard.js';
const data=JSON.parse(await readFile('site/leaderboard-preview.json'));
test('example choice changes the selected model in public and private rankings',()=>{
 const live=previewSnapshot(data),earlier=previewSnapshot(data,{earlier:true});
 assert.equal(live.rows.length,8);assert.notDeepEqual(live.rows,earlier.rows);
 const a=live.rows.find(r=>r.slug==='example-0'),b=earlier.rows.find(r=>r.slug==='example-0');
 assert.equal(a.submission_issue,102);assert.equal(a.score,.62);assert.equal(b.submission_issue,101);assert.equal(b.score,.52);assert(b.rank>a.rank);
 assert.equal(live.selected['example-0'],102);assert.equal(earlier.selected['example-0'],101);
 const final=previewSnapshot(data,{final:true}),changed=previewSnapshot(data,{final:true,earlier:true});
 assert.equal(final.rows[0].name,'Wetland Watch');assert.equal(changed.rows[0].name,'Woodland Lab');
 assert.equal(changed.rows[0].submission_issue,101);
 assert(changed.rows.every(r=>r.model_points_50>=0&&r.model_points_50<=50));
});
test('equal full-precision AP favors the earlier accepted prediction and only one row per team',()=>{
 const rows=previewSnapshot(data).rows;
 assert(rows.find(r=>r.name==='Meadow Makers').rank<rows.find(r=>r.name==='Urban Canopy').rank);
 assert.equal(new Set(rows.map(r=>r.slug)).size,rows.length);
 assert.throws(()=>previewSnapshot({...data,example_only:false}));
});
