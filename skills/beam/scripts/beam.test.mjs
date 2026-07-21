import assert from "node:assert/strict";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import test from "node:test";

const script = path.resolve("skills/beam/scripts/beam");

function tempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "beam-test-"));
}

function writeJsonl(file, rows) {
  fs.writeFileSync(file, `${rows.map((row) => JSON.stringify(row)).join("\n")}\n`);
}

function run(args, options = {}) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [script, ...args], {
      cwd: path.resolve("."),
      env: { ...process.env, ...options.env },
      stdio: ["pipe", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    if (options.stdin) child.stdin.end(options.stdin);
    else child.stdin.end();
    child.on("close", (code) => resolve({ code, stdout, stderr }));
  });
}

function claudeSession() {
  const dir = tempDir();
  const session = path.join(dir, "11111111-2222-4333-8444-555555555555.jsonl");
  writeJsonl(session, [
    { type: "user", message: { role: "user", content: "Fix the upload flow at /Users/tester/project with Bearer abcdefghijklmnopqrstuvwxyz123456" } },
    { type: "assistant", message: { role: "assistant", content: "Implemented the fix." } },
  ]);
  return session;
}

test("publish dry-run emits a sanitized versioned payload", async () => {
  const session = claudeSession();
  const result = await run([
    "publish",
    "--endpoint",
    "http://127.0.0.1:9/api/v1/beam/sessions",
    "--session",
    session,
    "--dry-run",
  ]);

  assert.equal(result.code, 0, result.stderr);
  const start = result.stdout.indexOf("{");
  const payload = JSON.parse(result.stdout.slice(start, result.stdout.lastIndexOf("}") + 1));
  assert.equal(payload.version, 1);
  assert.equal(payload.source, "agent");
  assert.equal(payload.items[0].type, "userMessage");
  assert.match(payload.items[0].text, /\[LOCAL_PATH\]/);
  assert.match(payload.items[0].text, /\[REDACTED_AUTH_HEADER\]/);
  assert.doesNotMatch(result.stdout, /abcdefghijklmnopqrstuvwxyz123456/);
  assert.equal(payload.beamId.length, 32);
});

test("publish accepts IPv6 loopback development endpoints", async () => {
  const session = claudeSession();
  const result = await run([
    "publish",
    "--endpoint",
    "http://[::1]:9/api/v1/beam/sessions",
    "--session",
    session,
    "--dry-run",
    "--quiet",
  ]);

  assert.equal(result.code, 0, result.stderr);
  assert.equal(JSON.parse(result.stdout).version, 1);
});

test("publish fails closed when an explicit session id has no exact transcript", async () => {
  const home = tempDir();
  const configDir = tempDir();
  const projectDir = path.join(configDir, "projects", "-tmp-beam");
  fs.mkdirSync(projectDir, { recursive: true });
  writeJsonl(path.join(projectDir, "11111111-2222-4333-8444-555555555555.jsonl"), [
    { type: "user", message: { role: "user", content: "same working directory" } },
  ]);

  const result = await run(
    [
      "publish",
      "--endpoint",
      "http://127.0.0.1:9/api/v1/beam/sessions",
      "--session-id",
      "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
      "--cwd",
      projectDir,
      "--dry-run",
    ],
    { env: { HOME: home, CLAUDE_CONFIG_DIR: configDir } },
  );

  assert.equal(result.code, 1);
  assert.match(result.stderr, /no matching local coding session was found/);
  assert.equal(result.stdout, "");
});

test("publish keeps display titles out of exact session discovery", async () => {
  const home = tempDir();
  const configDir = tempDir();
  const projectDir = path.join(configDir, "projects", "-tmp-beam");
  fs.mkdirSync(projectDir, { recursive: true });
  const sessionId = "11111111-2222-4333-8444-555555555555";
  writeJsonl(path.join(projectDir, `${sessionId}.jsonl`), [
    { type: "user", message: { role: "user", content: "Original prompt text" } },
  ]);

  const result = await run(
    [
      "publish",
      "--endpoint",
      "http://127.0.0.1:9/api/v1/beam/sessions",
      "--session-id",
      sessionId,
      "--title",
      "Words absent from transcript",
      "--cwd",
      projectDir,
      "--dry-run",
      "--quiet",
    ],
    { env: { HOME: home, CLAUDE_CONFIG_DIR: configDir } },
  );

  assert.equal(result.code, 0, result.stderr);
  assert.equal(JSON.parse(result.stdout).title, "Words absent from transcript");
});

test("publish refuses fuzzy newest-session fallback when no identity is available", async () => {
  const home = tempDir();
  const configDir = tempDir();
  const projectDir = path.join(configDir, "projects", "-tmp-beam");
  fs.mkdirSync(projectDir, { recursive: true });
  writeJsonl(path.join(projectDir, "11111111-2222-4333-8444-555555555555.jsonl"), [
    { type: "user", message: { role: "user", content: "newest local session" } },
  ]);

  const result = await run(
    [
      "publish",
      "--endpoint",
      "http://127.0.0.1:9/api/v1/beam/sessions",
      "--cwd",
      projectDir,
      "--dry-run",
    ],
    {
      env: {
        HOME: home,
        CLAUDE_CONFIG_DIR: configDir,
        CLAUDE_SESSION_ID: "",
        CODEX_THREAD_ID: "",
      },
    },
  );

  assert.equal(result.code, 1);
  assert.match(result.stderr, /could not identify the current session/);
  assert.equal(result.stdout, "");
});

test("publish rejects a missing explicit session path instead of discovering another session", async () => {
  const result = await run([
    "publish",
    "--endpoint",
    "http://127.0.0.1:9/api/v1/beam/sessions",
    "--session",
    path.join(tempDir(), "missing.jsonl"),
    "--dry-run",
  ]);

  assert.equal(result.code, 1);
  assert.match(result.stderr, /session file does not exist/);
  assert.equal(result.stdout, "");
});

test("hook consumes Codex-style stdin and appends the reliable final message", async () => {
  const session = claudeSession();
  const hook = {
    session_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
    transcript_path: session,
    cwd: path.dirname(session),
    hook_event_name: "Stop",
    last_assistant_message:
      "Final response from /Users/tester/private with Bearer abcdefghijklmnopqrstuvwxyz123456.",
  };
  const result = await run(
    ["hook", "--endpoint", "http://127.0.0.1:9/api/v1/beam/sessions", "--dry-run", "--quiet"],
    { stdin: JSON.stringify(hook) },
  );

  assert.equal(result.code, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.hookEvent, "Stop");
  assert.deepEqual(payload.items.at(-1), {
    type: "agentMessage",
    text: "Final response from [LOCAL_PATH] with [REDACTED_AUTH_HEADER]",
  });
  assert.doesNotMatch(result.stdout, /abcdefghijklmnopqrstuvwxyz123456/);
});

test("hook fails fast instead of starting interactive login without credentials", async () => {
  const session = claudeSession();
  const startedAt = Date.now();
  const result = await run(
    ["hook", "--endpoint", "https://beam.invalid/api/v1/beam/sessions", "--quiet"],
    {
      env: { BEAM_ACCESS_TOKEN: "", BEAM_AUTH_TOKEN: "" },
      stdin: JSON.stringify({
        session_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        transcript_path: session,
        hook_event_name: "Stop",
      }),
    },
  );

  assert.equal(result.code, 1);
  assert.match(result.stderr, /no Beam credentials configured/);
  assert.ok(Date.now() - startedAt < 5_000);
});

test(
  "publish asks cloudflared for the application token with --app",
  { skip: process.platform === "win32" },
  async () => {
    const session = claudeSession();
    const binDir = tempDir();
    const argsFile = path.join(binDir, "args.txt");
    const executable = path.join(binDir, "cloudflared");
    fs.writeFileSync(
      executable,
      `#!/bin/sh\nprintf '%s' "$*" > "$BEAM_TEST_ARGS"\nprintf '%s' test-access-token\n`,
    );
    fs.chmodSync(executable, 0o755);

    const result = await run(
      [
        "publish",
        "--endpoint",
        "https://beam.invalid/api/v1/beam/sessions",
        "--session",
        session,
        "--timeout",
        "50",
      ],
      {
        env: {
          BEAM_ACCESS_TOKEN: "",
          BEAM_AUTH_TOKEN: "",
          BEAM_TEST_ARGS: argsFile,
          PATH: `${binDir}${path.delimiter}${process.env.PATH}`,
        },
      },
    );

    assert.equal(result.code, 1);
    assert.equal(fs.readFileSync(argsFile, "utf8").trim(), "access token --app=https://beam.invalid");
  },
);

test("hook does not duplicate the final assistant message when a tool summary follows it", async () => {
  const dir = tempDir();
  const session = path.join(dir, "session.jsonl");
  writeJsonl(session, [
    { type: "response_item", payload: { role: "user", content: [{ type: "text", text: "Run tests." }] } },
    { type: "response_item", payload: { role: "assistant", content: [{ type: "text", text: "Tests pass." }] } },
    { type: "response_item", payload: { type: "function_call", name: "exec_command", arguments: "{}" } },
  ]);
  const result = await run(
    ["hook", "--endpoint", "http://127.0.0.1:9/api/v1/beam/sessions", "--dry-run", "--quiet"],
    {
      stdin: JSON.stringify({
        session_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        transcript_path: session,
        hook_event_name: "Stop",
        last_assistant_message: "Tests pass.",
      }),
    },
  );

  assert.equal(result.code, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.items.filter((item) => item.type === "agentMessage").length, 1);
  assert.equal(payload.items.at(-1).type, "other");
});

test("publish sends Cloudflare Access auth and normalized session JSON", async (t) => {
  const session = claudeSession();
  let requestBody = "";
  let accessToken = "";
  const server = http.createServer((request, response) => {
    accessToken = String(request.headers["cf-access-token"] || "");
    request.setEncoding("utf8");
    request.on("data", (chunk) => {
      requestBody += chunk;
    });
    request.on("end", () => {
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify({ ok: true, url: "/chat?session=catalog%3Abeam%3Agateway%3Ademo" }));
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => server.close());
  const address = server.address();
  const endpoint = `http://127.0.0.1:${address.port}/api/v1/beam/sessions`;

  const result = await run(
    ["publish", "--endpoint", endpoint, "--session", session],
    { env: { BEAM_ACCESS_TOKEN: "test-access-token" } },
  );

  assert.equal(result.code, 0, result.stderr);
  assert.match(result.stdout, new RegExp(`http://127\\.0\\.0\\.1:${address.port}/chat\\?session=`));
  assert.equal(accessToken, "test-access-token");
  const payload = JSON.parse(requestBody);
  assert.equal(payload.version, 1);
  assert.equal(payload.title, "Fix the upload flow at [LOCAL_PATH] with [REDACTED_AUTH_HEADER]");
  assert.equal(payload.completed, false);
});

test("publish refuses redirects without forwarding the Access token or payload", async (t) => {
  const session = claudeSession();
  let redirectedRequests = 0;
  const target = http.createServer((_request, response) => {
    redirectedRequests++;
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({ ok: true }));
  });
  await new Promise((resolve) => target.listen(0, "127.0.0.1", resolve));
  t.after(() => target.close());
  const targetAddress = target.address();

  const source = http.createServer((_request, response) => {
    response.writeHead(307, {
      location: `http://127.0.0.1:${targetAddress.port}/stolen`,
    });
    response.end();
  });
  await new Promise((resolve) => source.listen(0, "127.0.0.1", resolve));
  t.after(() => source.close());
  const sourceAddress = source.address();

  const result = await run(
    [
      "publish",
      "--endpoint",
      `http://127.0.0.1:${sourceAddress.port}/api/v1/beam/sessions`,
      "--session",
      session,
    ],
    { env: { BEAM_ACCESS_TOKEN: "test-access-token" } },
  );

  assert.equal(result.code, 1);
  assert.equal(redirectedRequests, 0);
  assert.doesNotMatch(`${result.stdout}\n${result.stderr}`, /test-access-token/);
});

test("publish ignores unvalidated legacy sessionUrl response fields", async (t) => {
  const session = claudeSession();
  const server = http.createServer((_request, response) => {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(
      JSON.stringify({
        ok: true,
        beamId: "0123456789abcdef0123456789abcdef",
        sessionUrl: "javascript:alert(1)",
      }),
    );
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => server.close());
  const address = server.address();

  const result = await run([
    "publish",
    "--endpoint",
    `http://127.0.0.1:${address.port}/api/v1/beam/sessions`,
    "--session",
    session,
  ]);

  assert.equal(result.code, 0, result.stderr);
  assert.match(result.stdout, /Beamed session: [a-f0-9]{32}/);
  assert.doesNotMatch(result.stdout, /0123456789abcdef0123456789abcdef|javascript:/);
});

test("publish never prints access tokens on receiver errors", async (t) => {
  const session = claudeSession();
  const server = http.createServer((_request, response) => {
    response.writeHead(401, { "content-type": "application/json" });
    const escape = String.fromCharCode(27);
    response.end(JSON.stringify({ ok: false, error: `${escape}[31mnot authorized\nforged${escape}[0m` }));
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => server.close());
  const address = server.address();

  const result = await run(
    ["publish", "--endpoint", `http://127.0.0.1:${address.port}/api/v1/beam/sessions`, "--session", session],
    { env: { BEAM_ACCESS_TOKEN: "super-secret-access-token" } },
  );

  assert.equal(result.code, 1);
  assert.match(result.stderr, /Beam upload failed: not authorized forged/);
  assert.equal(result.stderr.includes(String.fromCharCode(27)), false);
  assert.doesNotMatch(result.stderr, /\nforged/);
  assert.doesNotMatch(`${result.stdout}\n${result.stderr}`, /super-secret-access-token/);
});
