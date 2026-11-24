import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const binary = process.env.BEAM_TEST_NATIVE_CLI;
const released = process.env.BEAM_TEST_V1_SKILL;
const root = fileURLToPath(new URL("../../../", import.meta.url));

function invoke(script, args, env) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [script, ...args], {
      env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let out = "",
      err = "";
    child.stdout.setEncoding("utf8").on("data", (part) => (out += part));
    child.stderr.setEncoding("utf8").on("data", (part) => (err += part));
    child.once("error", reject);
    child.once("close", (code) => resolve({ code, out, err }));
  });
}

test(
  "copied native skill recovers a released JS sender's frozen transfer and uncertain turn",
  {
    skip: !binary || !released || process.platform === "win32",
  },
  async (t) => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "beam-skill-upgrade-"));
    t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
    const install = path.join(dir, "skills");
    execFileSync(
      "python3",
      [path.join(root, "scripts/install-skills"), "--target", install, "--mode", "copy", "beam"],
      { stdio: "pipe" },
    );
    const current = path.join(install, "beam", "scripts", "beam");
    const old = path.join(released, "scripts", "beam");
    const bin = path.join(dir, "bin");
    fs.mkdirSync(bin);
    fs.symlinkSync(fs.realpathSync(binary), path.join(bin, "beam"));
    assert.equal(
      execFileSync(path.join(bin, "beam"), ["skill-v1", "--protocol"], { encoding: "utf8" }),
      "1\n",
    );

    const id = "11111111-1111-4111-8111-111111111111";
    const gen = "22222222222222222222222222222222";
    const transcript = path.join(dir, id + ".jsonl");
    fs.writeFileSync(
      transcript,
      JSON.stringify({
        type: "user",
        sessionId: id,
        message: { role: "user", content: "Keep CSV quoting." },
      }) + "\n",
    );
    const bodies = [];
    const wire = [];
    const snapshots = [];
    const server = http.createServer((request, response) => {
      let data = "";
      request.on("data", (chunk) => (data += chunk));
      request.on("end", () => {
        const packet = JSON.parse(data);
        if (request.url === "/custom-upload" || request.url === "/review/api/v1/beam/sessions") {
          snapshots.push(request.url);
          response.setHeader("content-type", "application/json");
          response.end(JSON.stringify({ ok: true }));
          return;
        }
        bodies.push(packet);
        wire.push(data);
        if (bodies.length === 2) {
          request.socket.destroy();
          return;
        }
        response.setHeader("content-type", "application/json");
        response.end(
          JSON.stringify({
            ok: true,
            beamId: packet.beamId,
            url: "/beam/" + packet.beamId.slice(0, 12),
            ...(packet.handoffId
              ? { handoff: { id: gen, owner: "gateway", access: "owned" } }
              : { publicationId: gen }),
          }),
        );
      });
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    t.after(() => new Promise((resolve) => server.close(resolve)));
    const origin = `http://127.0.0.1:${server.address().port}`;
    const endpoint = origin + "/api/v1/beam/sessions";
    const db = path.join(dir, "handoffs.sqlite");
    const env = {
      ...process.env,
      PATH: bin,
      BEAM_AUTH_TOKEN: "",
      BEAM_ACCESS_TOKEN: "",
      BEAM_STATE: db,
    };
    const routes = ["/custom-upload", "/review/api/v1/beam/sessions"];
    for (const route of routes) {
      const snapshot = await invoke(
        current,
        ["publish", "--snapshot", "--session", transcript, "--endpoint", origin + route],
        env,
      );
      assert.equal(snapshot.code, 0, snapshot.err);
    }
    assert.deepEqual(snapshots, routes);
    assert.equal(fs.existsSync(db), false);
    const first = await invoke(
      old,
      ["handoff", "--session", transcript, "--endpoint", endpoint],
      env,
    );
    assert.equal(first.code, 1);
    assert.equal(bodies.length, 2);
    const beamID = bodies[0].beamId;
    assert.equal(bodies[1].handoffId, gen);
    fs.unlinkSync(transcript);
    const retry = await invoke(
      current,
      ["handoff", "--beam-id", beamID, "--endpoint", endpoint],
      env,
    );
    assert.equal(retry.code, 0, retry.err);
    assert.match(retry.out, /Conversation handed to Team/);
    assert.deepEqual(bodies[2], bodies[1]);
    assert.equal(wire[2], wire[1], "retry must preserve the released sender's exact payload");
    const again = await invoke(
      current,
      ["handoff", "--beam-id", beamID, "--endpoint", endpoint],
      env,
    );
    assert.equal(again.code, 0, again.err);
    assert.equal(bodies.length, 3);

    const profile = path.join(dir, "profile");
    fs.mkdirSync(profile);
    fs.writeFileSync(path.join(profile, "openclaw.json"), "{}");
    const gateway = path.join(dir, "openclaw"),
      sim = path.join(dir, "sim.json");
    fs.writeFileSync(sim, JSON.stringify({ requests: [], attempts: 0 }));
    const remote = origin.replace("http:", "ws:");
    fs.writeFileSync(
      gateway,
      `#!${process.execPath}
const [,,cmd,op,method,...rest]=process.argv;
const fs=require("node:fs");
const db=${JSON.stringify(sim)};
const s=JSON.parse(fs.readFileSync(db));
const persist=()=>fs.writeFileSync(db,JSON.stringify(s));
const output=v=>console.log(JSON.stringify(v));
if(cmd==="config"){output(method==="gateway.mode"?"remote":${JSON.stringify(remote)});process.exit()}
if(cmd!=="gateway"||op!=="call"||rest[rest.indexOf("--expect-url")+1]!==${JSON.stringify(remote)})process.exit(2);
const params=JSON.parse(rest[rest.indexOf("--params")+1]);
switch(method){
case "beam.owned.resolve": output(s.key?{sessionKey:s.key}:{});break;
case "beam.owned.continue": s.key="agent:main:dashboard:synthetic";persist();output({sessionKey:s.key});break;
case "chat.history": output({sessionId:"native-session",messages:[]});break;
case "chat.send": s.attempts++;if(!s.requests.includes(params.idempotencyKey))s.requests.push(params.idempotencyKey);persist();if(s.attempts===1)process.exit(1);output({accepted:true});break;
default:process.exit(3);
}
`,
      { mode: 0o700 },
    );
    const options = [
      "--endpoint",
      endpoint,
      "--beam-id",
      beamID,
      "--profile-dir",
      profile,
      "--cli",
      gateway,
    ];
    const read = await invoke(current, ["read", ...options], env);
    assert.equal(read.code, 0, read.err);
    assert.equal(JSON.parse(read.out).status, "pending");
    const msg = [
      "continue",
      ...options,
      "--message",
      "Finish the Windows test.",
      "--request-id",
      "repeatable-turn",
    ];
    const lost = await invoke(current, msg, env);
    assert.equal(lost.code, 1);
    assert.match(lost.err, /repeatable-turn/);
    const sent = await invoke(current, msg, env);
    assert.equal(sent.code, 0, sent.err);
    assert.equal(JSON.parse(sent.out).accepted, true);
    const state = JSON.parse(fs.readFileSync(sim));
    assert.deepEqual(state.requests, ["repeatable-turn"]);
    assert.equal(state.attempts, 2);
  },
);
