const SLUG = /^[a-z0-9][a-z0-9-]{1,39}$/;
const ROW_ID = /^[0-9a-f]{32}$/;
const NUMBER = /^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/;
export const MAX_CSV_BYTES = 8_000_000;

export function parseCSV(text) {
  text = text.replace(/^\uFEFF/, "");
  const rows = []; let row = [], field = "", quoted = false, closed = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i+1] === '"') { field += '"'; i++; }
      else if (ch === '"') { quoted = false; closed = true; }
      else field += ch;
    } else if (ch === '"') {
      if (field || closed) throw new Error("Invalid CSV quoting.");
      quoted = true;
    } else if (ch === ",") {
      row.push(field); field = ""; closed = false;
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i+1] === "\n") i++;
      row.push(field); rows.push(row); row = []; field = ""; closed = false;
    } else {
      if (closed) throw new Error("Unexpected character after a quoted field.");
      field += ch;
    }
  }
  if (quoted) throw new Error("Unclosed CSV quote.");
  if (field || row.length || closed) { row.push(field); rows.push(row); }
  return rows;
}

export function validateCSV(bytes, count, expectedIds = null) {
  if (!(bytes instanceof Uint8Array) || !bytes.length || bytes.length > MAX_CSV_BYTES) throw new Error("CSV must be between 1 byte and 8 MB.");
  const rows = parseCSV(new TextDecoder("utf-8", {fatal: true}).decode(bytes));
  const header=rows.shift();
  if (header?.length!==2 || header[0]!=="row_id" || header[1]!=="score") throw new Error("Use exactly the header row_id,score.");
  if (rows.length !== count) throw new Error(`Expected ${count.toLocaleString()} prediction rows; found ${rows.length.toLocaleString()}.`);
  const ids = new Set();
  for (const row of rows) {
    if (row.length !== 2 || !ROW_ID.test(row[0]) || ids.has(row[0])) throw new Error("Every row needs a unique 32-character row_id.");
    const value = row[1].trim();
    if (!NUMBER.test(value) || !Number.isFinite(Number(value)) || Number(value) < 0 || Number(value) > 1) throw new Error("Every score must be a finite number between 0 and 1.");
    ids.add(row[0]);
  }
  if (expectedIds && (ids.size !== expectedIds.size || [...ids].some(id => !expectedIds.has(id)))) throw new Error("The row IDs do not match the supplied sample submission.");
  return ids;
}

function unbase64(value) { return Uint8Array.from(atob(value), ch => ch.charCodeAt(0)); }
function base64(bytes) {
  let result = "";
  for (let i=0; i<bytes.length; i+=32768) result += String.fromCharCode(...bytes.subarray(i, i+32768));
  return btoa(result);
}
async function sha(bytes) { return [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map(b=>b.toString(16).padStart(2,"0")).join(""); }

export async function encryptCSV(bytes, teamSlug, channel, keyDocument, config) {
  if (!["final", "practice"].includes(channel)) throw new Error("Select an approved team and submission type.");
  return encryptPayload(bytes,teamSlug,channel,keyDocument,config);
}

export async function encryptPayload(bytes, teamSlug, channel, keyDocument, config) {
  if (!globalThis.crypto?.subtle || !globalThis.crypto?.randomUUID) throw new Error("Use a current browser over HTTPS, or the local preview on localhost.");
  if (!SLUG.test(teamSlug) || !["final", "practice", "registration", "membership", "team_admin"].includes(channel)) throw new Error("Select an approved team and submission type.");
  const spki = unbase64(keyDocument.spki_base64);
  if (keyDocument.version !== 1 || keyDocument.competition !== config.competition_id || await sha(spki) !== config.submission_key_id || keyDocument.key_id !== config.submission_key_id) throw new Error("The competition public key does not match the release. Contact an organizer.");
  const rsa = await crypto.subtle.importKey("spki", spki, {name:"RSA-OAEP", hash:"SHA-256"}, false, ["encrypt"]);
  if (rsa.algorithm.modulusLength !== 3072) throw new Error("Unexpected public key size.");
  const aes = await crypto.subtle.generateKey({name:"AES-GCM", length:256}, true, ["encrypt"]);
  const meta = {version:1, competition:config.competition_id, key_id:config.submission_key_id,
    team_slug:teamSlug, channel, submission_id:crypto.randomUUID(), csv_sha256:await sha(bytes), csv_bytes:bytes.length};
  const aad = new TextEncoder().encode(JSON.stringify(["aifn-envelope-v1",meta.competition,meta.key_id,teamSlug,channel,meta.submission_id,meta.csv_sha256,meta.csv_bytes]));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await crypto.subtle.encrypt({name:"AES-GCM", iv, additionalData:aad, tagLength:128}, aes, bytes);
  const wrapped = await crypto.subtle.encrypt({name:"RSA-OAEP"}, rsa, await crypto.subtle.exportKey("raw", aes));
  return {...meta, wrapped_key:base64(new Uint8Array(wrapped)), iv:base64(iv), ciphertext:base64(new Uint8Array(ciphertext))};
}
