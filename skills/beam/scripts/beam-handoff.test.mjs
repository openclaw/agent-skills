import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { openHandoffs, releaseSource, useDestination } from "./beam-handoff.js";

const endpoint = "https://gateway.example/api/v1/beam/sessions";
const beamId = "a".repeat(32);
const generation = "b".repeat(32);
const payload = { beamId, items: [{ type: "userMessage", text: "Continue this work" }] };
const receipt = { beamId, url: "https://gateway.example/beam/aaaaaaaaaaaa", handoff: { id: generation, owner: "gateway", access: "owned" } };

async function localState(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "beam-handoff-"));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const options = { state: path.join(dir, "handoffs.sqlite") };
  return { dir, options, state: await openHandoffs(options) };
}

test("lost release acknowledgment survives restart and missing source transcript without republishing", async (t) => {
  const { options, state } = await localState(t);
  const uploaded = [];
  await assert.rejects(releaseSource(state, endpoint, payload, async (body) => {
    uploaded.push(body);
    return body.handoffId ? Promise.reject(new Error("lost response")) : { publicationId: generation };
  }), /lost response/);
  assert.equal(state.get(endpoint, beamId).publication_id, generation);
  state.close();
  const resumed = await openHandoffs(options);
  try {
    const result = await releaseSource(resumed, endpoint, { beamId }, async (body) => {
      uploaded.push(body);
      return receipt;
    });
    assert.equal(result.handoff.id, generation);
    assert.equal(uploaded.length, 3);
    assert.equal(uploaded[2].handoffId, generation);
    assert.deepEqual(uploaded[2].items, payload.items);
    assert.equal(resumed.get(endpoint, beamId).payload, null);
    await assert.rejects(releaseSource(resumed, endpoint, { beamId: "f".repeat(32) }, async () => receipt), /No pending handoff/);
  } finally { resumed.close(); }
});

test("a conflicting acknowledgment cannot discard a pending generation or its frozen history", async (t) => {
  const { state } = await localState(t);
  try {
    state.begin(endpoint, payload);
    state.publication(endpoint, beamId, generation);
    assert.throws(() => state.acknowledge(endpoint, beamId, { ...receipt, handoff: { ...receipt.handoff, id: "c".repeat(32) } }), /different handoff generation/);
    assert.deepEqual(JSON.parse(state.get(endpoint, beamId).payload), payload);
    assert.equal(state.get(endpoint, beamId).receipt, null);
  } finally { state.close(); }
});

function cliFixture(dir) {
  const profile = path.join(dir, "profile");
  fs.mkdirSync(profile);
  const file = path.join(profile, "openclaw.json");
  const initial = { url: "wss://gateway.example/", allowed: true, key: null, sessionId: "session-1", messages: [], sends: {}, calls: [] };
  fs.writeFileSync(file, JSON.stringify(initial));
  const cli = path.join(dir, "openclaw-test-cli");
  fs.writeFileSync(cli, `#!${process.execPath}
import fs from 'node:fs';
const file=process.env.OPENCLAW_CONFIG_PATH;
const data=JSON.parse(fs.readFileSync(file,'utf8'));
const args=process.argv.slice(2);
const output=(value)=>console.log(JSON.stringify(value));
if(args[0]==='config') {output(args[2]==='gateway.mode'?'remote':data.url);process.exit(0);}
if(args[args.indexOf('--expect-url')+1]!==data.url || data.changedTarget || !data.allowed) process.exit(1);
if(['OPENCLAW_GATEWAY_URL','OPENCLAW_GATEWAY_PORT','OPENCLAW_GATEWAY_TOKEN','OPENCLAW_GATEWAY_PASSWORD'].some(key=>process.env[key])) process.exit(2);
const method=args[2], params=JSON.parse(args[args.indexOf('--params')+1]);
data.calls.push(method);
let result;
if(method.endsWith('.resolve')) result=data.key?{sessionKey:data.key}:null;
else if(method.endsWith('.continue')) {data.key='agent:main:dashboard:00000000-0000-4000-8000-000000000001';result={sessionKey:data.key};}
else if(method==='chat.history') result={sessionKey:data.key,sessionId:data.sessionId,messages:data.messages};
else if(method==='chat.send') {
  if(params.sessionKey!==data.key || params.sessionId!==data.sessionId) process.exit(3);
  if(!data.sends[params.idempotencyKey]) {data.messages.push({role:'user',content:params.message});data.sends[params.idempotencyKey]={runId:params.idempotencyKey};}
  result=data.sends[params.idempotencyKey];
}
else process.exit(4);
fs.writeFileSync(file,JSON.stringify(data));
if(method==='chat.send'&&data.loseResponse) process.exit(5);
output(result);
`, { mode: 0o700 });
  return {
    options: { "profile-dir": profile, cli },
    read: () => JSON.parse(fs.readFileSync(file, "utf8")),
    update(changes) { fs.writeFileSync(file, JSON.stringify({ ...this.read(), ...changes })); },
  };
}

test("source reads Team turns and continues the same authoritative conversation through normal access", async (t) => {
  const { dir, state } = await localState(t);
  const gateway = cliFixture(dir);
  try {
    state.begin(endpoint, payload);
    state.acknowledge(endpoint, beamId, receipt);
    assert.equal(useDestination(state, endpoint, beamId, gateway.options).status, "pending");
    assert.deepEqual(gateway.read().calls, ["beam.owned.resolve"]);
    useDestination(state, endpoint, beamId, { ...gateway.options, "request-id": "first-turn" }, "Continue in Team");
    gateway.update({ messages: [...gateway.read().messages, { role: "assistant", content: "Team result" }] });
    const read = useDestination(state, endpoint, beamId, gateway.options);
    assert.deepEqual(read.messages.at(-1), { role: "assistant", content: "Team result" });
    const key = gateway.read().key;
    useDestination(state, endpoint, beamId, { ...gateway.options, "request-id": "second-turn" }, "Source follow-up");
    assert.equal(gateway.read().key, key);
    assert.equal(gateway.read().calls.filter((method) => method.endsWith(".continue")).length, 1);
    gateway.update({ allowed: false });
    assert.throws(() => useDestination(state, endpoint, beamId, gateway.options, "Denied"), /normal authentication/);
    assert.equal(gateway.read().messages.length, 3);
  } finally { state.close(); }
});

test("deleted, reset and redirected destinations cannot create replacement conversations", async (t) => {
  const { dir, state } = await localState(t);
  const gateway = cliFixture(dir);
  try {
    state.begin(endpoint, payload);
    state.acknowledge(endpoint, beamId, receipt);
    useDestination(state, endpoint, beamId, gateway.options, "First turn");
    gateway.update({ sessionId: "replacement" });
    assert.throws(() => useDestination(state, endpoint, beamId, gateway.options, "Wrong incarnation"), /deleted or reset/);
    gateway.update({ key: null });
    assert.throws(() => useDestination(state, endpoint, beamId, gateway.options, "Deleted"), /original authoritative/);
    gateway.update({ changedTarget: true });
    assert.throws(() => useDestination(state, endpoint, beamId, gateway.options, "Wrong Gateway"), /normal authentication/);
    assert.equal(gateway.read().messages.length, 1);
  } finally { state.close(); }
});

test("an uncertain send can reuse its exposed request ID without another turn", async (t) => {
  const { dir, state } = await localState(t);
  const gateway = cliFixture(dir);
  try {
    state.begin(endpoint, payload);
    state.acknowledge(endpoint, beamId, receipt);
    gateway.update({ loseResponse: true });
    const options = { ...gateway.options, "request-id": "uncertain-request" };
    assert.throws(() => useDestination(state, endpoint, beamId, options, "Only once"));
    gateway.update({ loseResponse: false });
    assert.deepEqual(useDestination(state, endpoint, beamId, options, "Only once"), { runId: "uncertain-request" });
    assert.equal(gateway.read().messages.length, 1);
  } finally { state.close(); }
});
