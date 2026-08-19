#!/usr/bin/env node
'use strict';

// Standalone LNURL-auth helper for skills repositories. It intentionally uses
// only Node.js built-ins so the skill remains portable after installation.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const https = require('node:https');
const crypto = require('node:crypto');

const VERSION = '1.2.0';
const USER_AGENT = `lnurl-auth/${VERSION} (+https://github.com/dyegolara/lnurl-auth-agents)`;
const DEFAULT_TIMEOUT = 15000;
const MAX_REDIRECTS = 5;
const BECH32_LIMIT = 5000;
const ACTIONS = new Set(['register', 'login', 'link', 'auth']);
const FIELD_PRIME = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2fn;
const CURVE_ORDER = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141n;
const HALF_CURVE_ORDER = CURVE_ORDER >> 1n;
const GENERATOR = {
  x: 0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798n,
  y: 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8n,
};
const BECH32_ALPHABET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l';
const BECH32_VALUES = Object.fromEntries([...BECH32_ALPHABET].map((c, i) => [c, i]));

let quiet = false;

function log(...args) {
  if (!quiet) console.error('[lnurl-auth]', ...args);
}

function usage() {
  return `lnurl-auth - LNURL-auth (LUD-04) signer

Usage:
  node lnurl_auth.js [options] <lnurl1...>
  node lnurl_auth.js --lnurl <lnurl1...> [options]

Options:
  --lnurl <str>       lnurl1... string (or pass it positionally)
  --key <hex>         32-byte master secret as 64 hex characters
  --keyfile <path>    file containing the master secret
  --keyout <path>     path for a generated master secret
  --generate          replace an existing generated secret
  --single-key        use one linking key for every service domain
  --action <action>   assert or override register|login|link|auth
  --callback <url>    override the callback URL
  --dry-run           decode, sign, and build the callback without submitting
  --timeout <ms>      HTTP timeout (default: 15000)
  --json              emit machine-readable JSON
  -q, --quiet         suppress progress logs
  -h, --help          show this help
`;
}

function parseArgs(argv) {
  const opts = { positional: [] };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    const next = () => argv[++i];
    switch (arg) {
      case '-h':
      case '--help':
        opts.help = true;
        break;
      case '--lnurl':
        opts.lnurl = next();
        break;
      case '--key':
        opts.key = next();
        break;
      case '--keyfile':
        opts.keyfile = next();
        break;
      case '--keyout':
        opts.keyout = next();
        break;
      case '--generate':
        opts.generate = true;
        break;
      case '--single-key':
      case '--no-per-domain':
        opts.singleKey = true;
        break;
      case '--no-t':
        // Kept as a harmless compatibility option. This helper never adds t.
        break;
      case '--action':
        opts.action = next();
        break;
      case '--callback':
        opts.callback = next();
        break;
      case '--dry-run':
        opts.dryRun = true;
        break;
      case '--timeout':
        opts.timeout = Number.parseInt(next(), 10);
        break;
      case '--json':
        opts.json = true;
        break;
      case '-q':
      case '--quiet':
        quiet = true;
        opts.quiet = true;
        break;
      default:
        if (arg.startsWith('--')) throw new Error(`Unknown option: ${arg}`);
        opts.positional.push(arg);
    }
  }
  return opts;
}

function hexToBytes(value) {
  const hex = String(value ?? '').trim().replace(/^0x/i, '');
  if (hex.length % 2 !== 0 || !/^[0-9a-f]*$/i.test(hex)) {
    throw new Error('Invalid hex');
  }
  return Buffer.from(hex, 'hex');
}

function bytesToHex(value) {
  return Buffer.from(value).toString('hex');
}

function bytesToBigInt(value) {
  const hex = bytesToHex(value);
  return BigInt(`0x${hex || '0'}`);
}

function bigIntToBytes(value) {
  const hex = value.toString(16).padStart(64, '0');
  if (hex.length > 64) throw new Error('Scalar is too large');
  return Buffer.from(hex, 'hex');
}

function isValidPrivateKey(value) {
  if (value.length !== 32) return false;
  const scalar = bytesToBigInt(value);
  return scalar > 0n && scalar < CURVE_ORDER;
}

function generatePrivateKey() {
  let key;
  do key = crypto.randomBytes(32); while (!isValidPrivateKey(key));
  return key;
}

function deriveLinkingKey(master, domain) {
  let candidate = crypto.createHmac('sha256', master).update(domain, 'utf8').digest();
  while (!isValidPrivateKey(candidate)) {
    candidate = crypto.createHmac('sha256', candidate).update(domain, 'utf8').digest();
  }
  return candidate;
}

function mod(value, modulus) {
  const result = value % modulus;
  return result >= 0n ? result : result + modulus;
}

function inverse(value, modulus) {
  let a = mod(value, modulus);
  let b = modulus;
  let x = 1n;
  let y = 0n;
  if (a === 0n) throw new Error('Cannot invert zero');
  while (a !== 0n) {
    const quotient = b / a;
    [b, a] = [a, b % a];
    [y, x] = [x, y - quotient * x];
  }
  if (b !== 1n) throw new Error('Scalar has no inverse');
  return mod(y, modulus);
}

function pointAdd(left, right) {
  if (!left) return right;
  if (!right) return left;
  if (left.x === right.x) {
    if (left.y !== right.y || left.y === 0n) return null;
    const slope = mod(3n * left.x * left.x * inverse(2n * left.y, FIELD_PRIME), FIELD_PRIME);
    const x = mod(slope * slope - 2n * left.x, FIELD_PRIME);
    return { x, y: mod(slope * (left.x - x) - left.y, FIELD_PRIME) };
  }
  const slope = mod((right.y - left.y) * inverse(right.x - left.x, FIELD_PRIME), FIELD_PRIME);
  const x = mod(slope * slope - left.x - right.x, FIELD_PRIME);
  return { x, y: mod(slope * (left.x - x) - left.y, FIELD_PRIME) };
}

function pointMultiply(scalar, point = GENERATOR) {
  let result = null;
  let addend = point;
  let remaining = scalar;
  while (remaining > 0n) {
    if (remaining & 1n) result = pointAdd(result, addend);
    addend = pointAdd(addend, addend);
    remaining >>= 1n;
  }
  return result;
}

function pointBytes(point) {
  return Buffer.concat([
    Buffer.from([point.y & 1n ? 0x03 : 0x02]),
    bigIntToBytes(point.x),
  ]);
}

function encodeDerScalar(value) {
  let bytes = bigIntToBytes(value);
  while (bytes.length > 1 && bytes[0] === 0) bytes = bytes.subarray(1);
  if (bytes[0] & 0x80) bytes = Buffer.concat([Buffer.from([0]), bytes]);
  return Buffer.concat([Buffer.from([0x02, bytes.length]), bytes]);
}

function encodeDer(r, s) {
  const body = Buffer.concat([encodeDerScalar(r), encodeDerScalar(s)]);
  return Buffer.concat([Buffer.from([0x30, body.length]), body]);
}

function signRaw(message, privateBytes) {
  const privateScalar = bytesToBigInt(privateBytes);
  const messageScalar = bytesToBigInt(message);
  const publicPoint = pointMultiply(privateScalar);
  let r = 0n;
  let s = 0n;
  while (!s) {
    const nonce = bytesToBigInt(crypto.randomBytes(32));
    if (nonce === 0n || nonce >= CURVE_ORDER) continue;
    const point = pointMultiply(nonce);
    const nextR = mod(point.x, CURVE_ORDER);
    if (nextR === 0n) continue;
    const nextS = mod(inverse(nonce, CURVE_ORDER) * (messageScalar + nextR * privateScalar), CURVE_ORDER);
    if (nextS === 0n) continue;
    r = nextR;
    s = nextS;
  }
  if (s > HALF_CURVE_ORDER) s = CURVE_ORDER - s;
  const der = encodeDer(r, s);
  if (!verifySignature(message, r, s, publicPoint)) throw new Error('Self-verification failed');
  return { der, compressed: pointBytes(publicPoint) };
}

function verifySignature(message, r, s, publicPoint) {
  if (r <= 0n || r >= CURVE_ORDER || s <= 0n || s >= CURVE_ORDER) return false;
  const inverseS = inverse(s, CURVE_ORDER);
  const u1 = mod(bytesToBigInt(message) * inverseS, CURVE_ORDER);
  const u2 = mod(r * inverseS, CURVE_ORDER);
  const point = pointAdd(pointMultiply(u1), pointMultiply(u2, publicPoint));
  return Boolean(point) && mod(point.x, CURVE_ORDER) === r;
}

function polymodStep(pre) {
  const top = pre >>> 25;
  return (((pre & 0x1ffffff) << 5) ^
    (-((top >>> 0) & 1) & 0x3b6a57b2) ^
    (-((top >>> 1) & 1) & 0x26508e6d) ^
    (-((top >>> 2) & 1) & 0x1ea119fa) ^
    (-((top >>> 3) & 1) & 0x3d4233dd) ^
    (-((top >>> 4) & 1) & 0x2a1462b3)) >>> 0;
}

function prefixChecksum(prefix) {
  let checksum = 1;
  for (const char of prefix) {
    const code = char.charCodeAt(0);
    if (code < 33 || code > 126) throw new Error('Invalid bech32 prefix');
    checksum = polymodStep(checksum) ^ (code >>> 5);
  }
  checksum = polymodStep(checksum);
  for (const char of prefix) checksum = polymodStep(checksum) ^ (char.charCodeAt(0) & 31);
  return checksum;
}

function convertBits(data, fromBits, toBits, pad) {
  let value = 0;
  let bits = 0;
  const maxValue = (1 << toBits) - 1;
  const result = [];
  for (const item of data) {
    value = (value << fromBits) | item;
    bits += fromBits;
    while (bits >= toBits) {
      bits -= toBits;
      result.push((value >>> bits) & maxValue);
    }
  }
  if (pad) {
    if (bits > 0) result.push((value << (toBits - bits)) & maxValue);
  } else {
    if (bits >= fromBits) throw new Error('Excess bech32 padding');
    if ((value << (toBits - bits)) & maxValue) throw new Error('Non-zero bech32 padding');
  }
  return result;
}

function decodeLnurl(value) {
  const input = String(value ?? '').trim();
  if (!/^lnurl1/i.test(input)) throw new Error('Not an lnurl1 string');
  if (input.length > BECH32_LIMIT) throw new Error('LNURL exceeds length limit');
  const lower = input.toLowerCase();
  const upper = input.toUpperCase();
  if (input !== lower && input !== upper) throw new Error('Mixed-case bech32 string');
  const separator = lower.lastIndexOf('1');
  if (separator < 1) throw new Error('Invalid bech32 separator');
  const prefix = lower.slice(0, separator);
  const payload = lower.slice(separator + 1);
  if (prefix !== 'lnurl' || payload.length < 6) throw new Error('Invalid lnurl prefix or data');
  let checksum = prefixChecksum(prefix);
  const words = [];
  for (let i = 0; i < payload.length; i++) {
    const word = BECH32_VALUES[payload[i]];
    if (word === undefined) throw new Error(`Invalid bech32 character: ${payload[i]}`);
    checksum = polymodStep(checksum) ^ word;
    if (i + 6 < payload.length) words.push(word);
  }
  if (checksum !== 1) throw new Error('Invalid bech32 checksum');
  return Buffer.from(convertBits(words, 5, 8, false)).toString('utf8');
}

function readKeyFile(file) {
  try {
    return hexToBytes(fs.readFileSync(file, 'utf8').trim());
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

function resolveMasterSecret(opts) {
  if (opts.key) {
    const key = hexToBytes(opts.key);
    if (!isValidPrivateKey(key)) throw new Error('--key must be a valid 32-byte private key');
    return key;
  }
  const file = opts.keyfile || opts.keyout || process.env.LNURL_AUTH_KEYFILE ||
    path.join(os.homedir(), '.config', 'lnurl-auth', 'master.key');
  const existing = readKeyFile(file);
  if (existing && !opts.generate) {
    if (!isValidPrivateKey(existing)) throw new Error('Key file must hold a valid 32-byte secret');
    return existing;
  }
  const generated = generatePrivateKey();
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${bytesToHex(generated)}\n`, { mode: 0o600 });
  fs.chmodSync(file, 0o600);
  log(existing ? 'Replaced master secret:' : 'Generated master secret:', file);
  return generated;
}

function httpGet(urlString, timeout, redirects = 0) {
  return new Promise((resolve, reject) => {
    let url;
    try {
      url = new URL(urlString);
    } catch {
      reject(new Error(`Invalid URL: ${urlString}`));
      return;
    }
    if (!['http:', 'https:'].includes(url.protocol)) {
      reject(new Error(`Unsupported URL protocol: ${url.protocol}`));
      return;
    }
    if (redirects > MAX_REDIRECTS) {
      reject(new Error(`Too many redirects (${redirects})`));
      return;
    }
    const client = url.protocol === 'https:' ? https : http;
    const request = client.get(url, { timeout, headers: { 'User-Agent': USER_AGENT } }, (response) => {
      if ([301, 302, 307, 308].includes(response.statusCode) && response.headers.location) {
        response.resume();
        resolve(httpGet(new URL(response.headers.location, url).toString(), timeout, redirects + 1));
        return;
      }
      let body = '';
      response.setEncoding('utf8');
      response.on('data', (chunk) => { body += chunk; });
      response.on('end', () => resolve({ status: response.statusCode, body }));
    });
    request.on('timeout', () => request.destroy(new Error(`Request timed out after ${timeout}ms`)));
    request.on('error', reject);
  });
}

function parseResponse(body) {
  try { return JSON.parse(body); } catch { return null; }
}

async function run(opts) {
  const lnurl = opts.lnurl || opts.positional[0];
  if (!lnurl) throw Object.assign(new Error(`No lnurl provided.\n\n${usage()}`), { exitCode: 2 });
  if (opts.timeout !== undefined && (!Number.isFinite(opts.timeout) || opts.timeout <= 0)) {
    throw Object.assign(new Error('--timeout must be a positive number'), { exitCode: 2 });
  }
  const timeout = opts.timeout || DEFAULT_TIMEOUT;
  const serviceUrl = decodeLnurl(lnurl);
  const parsed = new URL(serviceUrl);
  if (!parsed.hostname) throw new Error('Decoded LNURL has no service hostname');
  const domain = parsed.hostname;
  let k1 = parsed.searchParams.get('k1');
  let action = parsed.searchParams.get('action') || null;
  let callbackFromChallenge;

  if (!k1) {
    log('No k1 in URL; fetching challenge...');
    const challenge = await httpGet(serviceUrl, timeout);
    if (challenge.status !== 200) throw new Error(`Challenge GET failed: HTTP ${challenge.status}`);
    const challengeJson = parseResponse(challenge.body);
    if (!challengeJson) throw new Error('Challenge response was not JSON');
    k1 = challengeJson.k1;
    action = challengeJson.action || action;
    callbackFromChallenge = challengeJson.callback || challengeJson.url;
  }
  if (!/^[0-9a-f]{64}$/i.test(k1 || '')) {
    throw new Error('k1 must be exactly 64 hexadecimal characters (32 bytes)');
  }
  if (opts.action) {
    if (!ACTIONS.has(opts.action)) throw new Error(`Invalid action: ${opts.action}`);
    action = opts.action;
  }

  const master = resolveMasterSecret(opts);
  const linkingKey = opts.singleKey ? master : deriveLinkingKey(master, domain);
  const k1Bytes = Buffer.from(k1, 'hex');
  const signed = signRaw(k1Bytes, linkingKey);
  const callback = new URL(opts.callback || callbackFromChallenge || serviceUrl);
  if (!callback.searchParams.has('k1')) callback.searchParams.set('k1', k1);
  callback.searchParams.delete('sig');
  callback.searchParams.delete('key');
  callback.searchParams.set('sig', bytesToHex(signed.der));
  callback.searchParams.set('key', bytesToHex(signed.compressed));

  const details = {
    serviceUrl,
    domain,
    k1,
    action,
    linkingPubkey: bytesToHex(signed.compressed),
    callbackUrl: callback.toString(),
    method: 'GET',
    dryRun: Boolean(opts.dryRun),
  };
  if (opts.json) console.log(JSON.stringify(details, null, 2));
  else log('Callback URL:', details.callbackUrl);
  if (opts.dryRun) {
    if (!opts.json) console.log('OK (dry-run)');
    return 0;
  }

  log('Submitting authentication callback...');
  const response = await httpGet(details.callbackUrl, timeout);
  const json = parseResponse(response.body);
  if (opts.json) console.log(JSON.stringify({ httpStatus: response.status, response: json || response.body }, null, 2));
  else {
    console.log(`HTTP ${response.status}`);
    console.log(json ? JSON.stringify(json, null, 2) : response.body);
  }
  if (json?.status === 'OK') return 0;
  if (json?.status === 'ERROR') return 3;
  return 4;
}

async function main() {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 2;
    return;
  }
  if (opts.help) {
    console.log(usage());
    return;
  }
  try {
    process.exitCode = await run(opts);
  } catch (error) {
    console.error('lnurl-auth error:', error.message);
    process.exitCode = error.exitCode || 1;
  }
}

main();
