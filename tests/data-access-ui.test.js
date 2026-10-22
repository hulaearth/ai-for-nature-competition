import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

test('the download button and copied address offer only AlphaEarth before release',()=>{
  const source=fs.readFileSync(new URL('../site/app.js',import.meta.url),'utf8');
  const renderSource=source.slice(source.indexOf('function renderConfig('),source.indexOf('async function materialsRelease('));
  const config={data_release_utc:'2026-10-24T08:00:00Z',materials_release_utc:'2026-10-24T08:00:00Z',
    alphaearth_drive_url:'https://drive.google.com/drive/folders/alpha-only',
    drive_url:'https://drive.google.com/drive/folders/event-data',data_ready:true};
  for(const [when,expected,label] of [
    ['2026-10-24T07:59:59Z',config.alphaearth_drive_url,'Download German AlphaEarth'],
    ['2026-10-24T08:00:00Z',config.drive_url,'Open Challenge data']]){
    const link={removeAttribute(){}};const address={};const copy={};const notice={};
    const nodes={'[data-drive]':[link],'[data-drive-address]':[address],'[data-copy-drive]':[copy],'[data-data-readiness]':[notice]};
    const document={querySelectorAll:s=>nodes[s]||[]};
    class Clock extends Date{static now(){return Date.parse(when);}}
    const render=new Function('document','Date','date','isFinalOpen',renderSource+';return renderConfig;')(document,Clock,()=>'',()=>false);
    render(config);
    assert.equal(link.href,expected);assert.equal(address.textContent,expected);
    assert.ok(link.textContent.startsWith(label));assert.equal(copy.disabled,false);
    assert.equal(typeof copy.onclick,'function');
    if(when<'2026-10-24T08:00:00Z')assert.match(notice.textContent,/only Germany’s full AlphaEarth/);
    else assert.match(notice.textContent,/Encrypted test inputs unlock at 13:30/);
  }
});
