import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {parseCSV,validateCSV,encryptCSV} from "../site/envelope.js";
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const encoder=new TextEncoder();
const id="0".repeat(32),other="1".repeat(32);
test("CSV supports BOM, quoted values and CRLF, and keyed order",()=>{
  const b=encoder.encode(`\uFEFFrow_id,score\r\n"${other}","0.8"\r\n${id},1e-2\r\n`);
  assert.equal(validateCSV(b,2,new Set([id,other])).size,2);
  assert.deepEqual(parseCSV('a,b\n"hello, there",2\n'),[['a','b'],['hello, there','2']]);
});
test("Rejects malformed, duplicate, non-finite and wrong-grid CSVs",()=>{
  for(const value of ["NaN","Infinity","-1","1.01","","0x1"])
    assert.throws(()=>validateCSV(encoder.encode(`row_id,score\n${id},${value}\n`),1));
  assert.throws(()=>validateCSV(encoder.encode(`row_id,score\n${id},0\n${id},1\n`),2));
  assert.throws(()=>validateCSV(encoder.encode(`row_id,score\n${id},0\n`),1,new Set([other])));
  assert.throws(()=>parseCSV('a,b\n"oops,b'));
});
test("WebCrypto envelope is authenticated and randomized",async()=>{
 const pair=await crypto.subtle.generateKey({name:'RSA-OAEP',modulusLength:3072,publicExponent:new Uint8Array([1,0,1]),hash:'SHA-256'},true,['encrypt','decrypt']);
 const spki=new Uint8Array(await crypto.subtle.exportKey('spki',pair.publicKey));
 const kid=Buffer.from(await crypto.subtle.digest('SHA-256',spki)).toString('hex');
 const doc={version:1,competition:'test',key_id:kid,spki_base64:Buffer.from(spki).toString('base64')};
 const cfg={competition_id:'test',submission_key_id:kid};const plain=encoder.encode(`row_id,score\n${id},0.5\n`);
 const a=await encryptCSV(plain,'test-team','practice',doc,cfg),b=await encryptCSV(plain,'test-team','practice',doc,cfg);
 assert.notEqual(a.ciphertext,b.ciphertext);assert.notEqual(a.submission_id,b.submission_id);
 const raw=await crypto.subtle.decrypt({name:'RSA-OAEP'},pair.privateKey,Buffer.from(a.wrapped_key,'base64'));
 const aes=await crypto.subtle.importKey('raw',raw,'AES-GCM',false,['decrypt']);
 const aad=encoder.encode(JSON.stringify(['aifn-envelope-v1',a.competition,a.key_id,a.team_slug,a.channel,a.submission_id,a.csv_sha256,a.csv_bytes]));
 const decoded=await crypto.subtle.decrypt({name:'AES-GCM',iv:Buffer.from(a.iv,'base64'),additionalData:aad},aes,Buffer.from(a.ciphertext,'base64'));
 assert.deepEqual(new Uint8Array(decoded),plain);
 aad[0]^=1;await assert.rejects(crypto.subtle.decrypt({name:'AES-GCM',iv:Buffer.from(a.iv,'base64'),additionalData:aad},aes,Buffer.from(a.ciphertext,'base64')));
});

test("Expanded test CSV follows the explicit published byte cap and preserves exact row-ID checking",()=>{
 const count=220_000;
 const rows=Array.from({length:count},(_,i)=>`${i.toString(16).padStart(32,'0')},0.1234567890123456`);
 const bytes=encoder.encode('row_id,score\n'+rows.join('\n')+'\n');
 assert(bytes.length>8_000_000 && bytes.length<16_000_000);
 assert.throws(()=>validateCSV(bytes,count),/8 MB/);
 const ids=validateCSV(bytes,count,null,16_000_000);
 assert.equal(ids.size,count);
 assert.equal(validateCSV(bytes,count,ids,16_000_000).size,count);
 ids.delete('0'.repeat(32));ids.add('f'.repeat(32));
 assert.throws(()=>validateCSV(bytes,count,ids,16_000_000),/row IDs/);
 for(const maxBytes of [0,-1,NaN,32_000_001])assert.throws(()=>validateCSV(bytes,count,null,maxBytes),/size setting/);
});
