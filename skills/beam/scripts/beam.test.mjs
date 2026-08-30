import assert from "node:assert/strict";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import test from "node:test";
import {
  renderSession,
  resolveClaudeSession,
  resolveCodexSession,
  sanitizeVisibleText,
} from "./beam-session.js";

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

async function beamReceiverEndpoint(t, urlForPayload, basePath = "") {
  const server = http.createServer((request, response) => {
    let body = "";
    request.setEncoding("utf8");
    request.on("data", (chunk) => {
      body += chunk;
    });
    request.on("end", () => {
      const payload = JSON.parse(body);
      response.writeHead(200, {
        "content-type": "application/json",
        connection: "close",
      });
      response.end(JSON.stringify({ ok: true, url: urlForPayload(payload, request) }));
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => server.close());
  const address = server.address();
  return `http://127.0.0.1:${address.port}${basePath}/api/v1/beam/sessions`;
}

function claudeSession() {
  const dir = tempDir();
  const session = path.join(dir, "11111111-2222-4333-8444-555555555555.jsonl");
  writeJsonl(session, [
    { type: "user", sessionId: "11111111-2222-4333-8444-555555555555", message: { role: "user", content: "Fix the upload flow at /Users/tester/project with Bearer abcdefghijklmnopqrstuvwxyz123456" } },
    { type: "user", isCompactSummary: true, message: { role: "user", content: "hidden compact summary with /workspace/private" } },
    { type: "assistant", message: { role: "assistant", content: "Implemented the fix." } },
  ]);
  return session;
}

test("standalone redaction strips internal wrappers, credentials, and local paths", () => {
  const value = sanitizeVisibleText(
    `<system-reminder>private policy text</system-reminder>\n<environment_context>cwd=/workspace/private timezone=secret</environment_context>\nUse /root, /customer-secret.db, /app/customers/acme, D:/src/private, and file:///Users/tester/project with Bearer abcdefghijklmnopqrstuvwxyz123456, github_pat_abcdefghijklmnopqrstuvwxyz123456, BEAM_AUTH_TOKEN="opaque-secret-value", DATABASE_URL=postgres://user:pass@localhost/db, {"access_token":"structured-secret-value"}, X-API-Key: header-secret-value, and https://example.test/callback#access_token=opaquecredentialvalue.`,
  );
  assert.equal(
    value,
    "[REDACTED_SECRET_LINE]",
  );
});

test("standalone redaction covers GitLab tokens and session-cookie assignments", () => {
  const value = sanitizeVisibleText(
    `token glpat-abcdefghijklmnopqrstuvwx\ndeploy gldt-abcdefghijklmnopqrstuvwx\nfeed glft-abcdefghijklmnopqrstuvwx\nlabel global-navigation-component\nPHPSESSID=abcdefghijklmnopqrstuvwx12`,
  );
  assert.equal(
    value,
    "token [REDACTED_API_KEY]\ndeploy [REDACTED_API_KEY]\nfeed [REDACTED_API_KEY]\nlabel global-navigation-component\n[REDACTED_SECRET_LINE]",
  );
  assert.doesNotMatch(value, /glpat-|gldt-|glft-|PHPSESSID|abcdefghijklmnopqrstuvwx/);
});

test("standalone redaction removes YAML secret block bodies", () => {
  const value = sanitizeVisibleText(
    `password: |\n  correct horse battery\n  second secret line\nnext: visible\nclient_secret: correct horse battery staple`,
  );
  assert.equal(
    value,
    "[REDACTED_SECRET_LINE]\nnext: visible\n[REDACTED_SECRET_LINE]",
  );
});

test("standalone redaction removes multiline structured values and PASS assignments", () => {
  const value = sanitizeVisibleText(
    `{"access_token":\n  "multiline-secret-value",\n  "visible": "ok"\n}\nDB_PASS=\\\n  multiline-pass-value\nDB_PASS_B64=encoded-pass\nDBPASS=joined-pass\nPASS_B64=bare-pass\nPGPASSFILE=pg-pass\nBYPASS_PASS=bypass-secret\nCOMPASS_PASSPHRASE=compass-secret\nMY_APP_PASS=app-value\nSERVICE_ACCOUNT_PASS=service-value\nMYSQL_PASS=mysql-value\nGPG_PASSPHRASE=gpg-value\nMFA_PASSCODE=123456\nSSH_PASS_PHRASE=phrase-value\nSSH_PASSPHRASE_FILE=/root/phrase\nDATABASE_URL=postgres://user:pass@localhost/db\nCookie:[REDACTED] sid=live-cookie`,
  );
  const lines = value.split("\n");
  assert.deepEqual(lines.slice(0, 2), ["[REDACTED_SECRET_LINE]", "}"]);
  assert.equal(lines.length, 18);
  assert.equal(lines.slice(2).every((line) => line === "[REDACTED_SECRET_LINE]"), true);
  assert.doesNotMatch(
    value,
    /multiline-secret-value|multiline-pass-value|encoded-pass|joined-pass|bare-pass|pg-pass|bypass-secret|compass-secret|app-value|service-value|mysql-value|gpg-value|123456|phrase-value|\/root\/phrase|user:pass|live-cookie/,
  );
});

test("standalone redaction removes full header, CLI, assignment, and quoted path values", () => {
  const value = sanitizeVisibleText(
    `Authorization: AWS4-HMAC Credential=abc Signature=def\nCookie: sid=secret-one; csrf=secret-two\ncurl -H 'Authorization: Token opaque-secret-value' https://example.test\ndeploy --password=correct-horse --api-key opaque-value password=lowercase-value cwd:'/Users/Jane Doe/private' source=/Users/alice/Client Secret/file.js; cat >/Users/alice/private/output.txt`,
  );
  assert.equal(
    value,
    "[REDACTED_SECRET_LINE]\n[REDACTED_SECRET_LINE]\n[REDACTED_SECRET_LINE]\n[REDACTED_SECRET_LINE]",
  );
});

test("standalone redaction handles root, spaced, file URL, and shell-adjacent paths", () => {
  const value = sanitizeVisibleText(
    `Use /root, /customer-secret.db, /Users/alice/Client Secret/file.js, D:/src/private, file:///Users/tester/project, and run cat >/Users/alice/private/output.txt`,
  );
  assert.equal(
    value,
    "Use [LOCAL_PATH], [LOCAL_PATH], [LOCAL_PATH], [LOCAL_PATH], [LOCAL_PATH], and run cat >[LOCAL_PATH]",
  );
});

test("standalone sanitizer keeps ordinary pass-related fields", () => {
  assert.equal(
    sanitizeVisibleText('{"passed":true,"bypass":"enabled","compass":"north","passengers":3,"first-pass":true,"pass-through":"open","slug":"session-cookie-assignments"}\nBYPASS_MODE=on\nCOMPASS_HEADING=north\nPASSED_TESTS=3\nPASSENGERS=4'),
    '{"passed":true,"bypass":"enabled","compass":"north","passengers":3,"first-pass":true,"pass-through":"open","slug":"session-cookie-assignments"}\nBYPASS_MODE=on\nCOMPASS_HEADING=north\nPASSED_TESTS=3\nPASSENGERS=4',
  );
});

test("standalone redaction inspects local paths inside network URL parameters", () => {
  const value = sanitizeVisibleText(
    "Open https://example.test/report?file=%252525252FUsers%252525252Falice%252525252Fprivate#cwd=%2Ftmp%2Fwork and https://example.test/#/Users/alice/a=b?view=1 and https://example.test/open?note=see%20%2FUsers%2Falice%2Fprivate&redirect=https%3A%2F%2Fother.test%2F%3Ffile%3Dfile%253A%252F%252F%252Ftmp%252Fx and https://example.test/?files=%5B%2FUsers%2Falice%2Fprivate%5D and https://example.test/?meta=path%3D~%2F.private%2Fcredentials and https://example.test/?=/Users/alice/private&=/tmp/work and [report](https://example.test/?file=/Users/alice/private),",
  );
  assert.equal(
    value,
    "Open https://example.test/report?file=[LOCAL_PATH]#cwd=[LOCAL_PATH] and https://example.test/#[LOCAL_PATH] and https://example.test/open?note=[LOCAL_PATH]&redirect=[LOCAL_PATH] and https://example.test/?files=[LOCAL_PATH] and https://example.test/?meta=[LOCAL_PATH] and https://example.test/?=[LOCAL_PATH]&=[LOCAL_PATH] and [report](https://example.test/?file=[LOCAL_PATH]),",
  );
});

test("standalone URL redaction fails closed on encoded keys, invalid UTF-8, and excess nesting", () => {
  let deeplyEncoded = "/Users/alice/private";
  for (let index = 0; index < 10; index++) deeplyEncoded = encodeURIComponent(deeplyEncoded);
  const value = sanitizeVisibleText(
    `Open https://example.test/?%2FUsers%2Falice%2Fprivate=1 and https://example.test/?broken=%FF%2FUsers%2Falice and https://example.test/?malformed=%ZZ/Users/alice/private and https://example.test/?deep=${deeplyEncoded} and https://example.test/search?q=100%25`,
  );
  assert.equal(
    value,
    "Open https://example.test/?[LOCAL_PATH] and https://example.test/?broken=[LOCAL_PATH] and https://example.test/?malformed=[LOCAL_PATH] and https://example.test/?deep=[LOCAL_PATH] and https://example.test/search?q=100%25",
  );
});

test("standalone sanitizer keeps ordinary AGENTS.md tasks", () => {
  assert.equal(
    sanitizeVisibleText("Update AGENTS.md with your instructions for the new command."),
    "Update AGENTS.md with your instructions for the new command.",
  );
});

test("standalone Claude discovery requires one exact session-id filename", () => {
  const configDir = tempDir();
  const projectDir = path.join(configDir, "projects", "demo");
  fs.mkdirSync(projectDir, { recursive: true });
  const id = "11111111-2222-4333-8444-555555555555";
  const session = path.join(projectDir, `${id}.jsonl`);
  writeJsonl(session, [
    { type: "user", sessionId: id, message: { role: "user", content: "Exact Claude session" } },
  ]);

  assert.equal(resolveClaudeSession(id, { CLAUDE_CONFIG_DIR: configDir }).file, fs.realpathSync(session));
});

test("standalone discovery fails closed when the file scan is incomplete", () => {
  const configDir = tempDir();
  const projectDir = path.join(configDir, "projects", "demo");
  fs.mkdirSync(projectDir, { recursive: true });
  const id = "12121212-3434-4567-8899-abcdefabcdef";
  writeJsonl(path.join(projectDir, `${id}.jsonl`), [
    { type: "user", sessionId: id, message: { role: "user", content: "candidate" } },
  ]);
  writeJsonl(path.join(projectDir, "other.jsonl"), [
    { type: "user", message: { role: "user", content: "other" } },
  ]);

  assert.throws(
    () => resolveClaudeSession(id, { CLAUDE_CONFIG_DIR: configDir }, { maxFiles: 1 }),
    /discovery exceeded its file limit/,
  );
});

test("standalone Codex discovery verifies metadata across active and archived rollouts", () => {
  const codexHome = tempDir();
  const activeDir = path.join(codexHome, "sessions", "2026", "07", "21");
  const archivedDir = path.join(codexHome, "archived_sessions");
  fs.mkdirSync(activeDir, { recursive: true });
  fs.mkdirSync(archivedDir, { recursive: true });
  const wanted = "22222222-3333-4444-8555-666666666666";
  const decoy = path.join(activeDir, `rollout-decoy-${wanted}.jsonl`);
  const archived = path.join(archivedDir, `rollout-2026-07-21-${wanted}.jsonl`);
  writeJsonl(decoy, [{ type: "session_meta", payload: { id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee" } }]);
  writeJsonl(archived, [
    { type: "session_meta", payload: { id: wanted } },
    { type: "event_msg", payload: { type: "user_message", message: "Archived Codex session" } },
  ]);

  assert.equal(resolveCodexSession(wanted, { CODEX_HOME: codexHome }).file, fs.realpathSync(archived));
});

test("standalone Claude parser omits wrappers, thinking, and tool output", () => {
  const session = path.join(tempDir(), "claude.jsonl");
  writeJsonl(session, [
    {
      type: "user",
      isMeta: true,
      message: { role: "user", content: "hidden skill expansion metadata" },
    },
    {
      type: "user",
      uuid: "root-user",
      parentUuid: null,
      sessionId: "44444444-5555-4666-8777-888888888888",
      message: {
        role: "user",
        content: [
          { type: "text", text: "<system-reminder>private policy</system-reminder>\nInspect /Users/tester/code" },
          { type: "tool_result", content: "raw private result" },
        ],
      },
    },
    {
      type: "assistant",
      uuid: "sidechain-message",
      parentUuid: "root-user",
      isSidechain: true,
      message: { role: "assistant", content: "hidden sidechain response" },
    },
    {
      type: "assistant",
      uuid: "abandoned-branch",
      parentUuid: "root-user",
      message: { role: "assistant", content: "hidden abandoned response" },
    },
    {
      type: "assistant",
      uuid: "active-response",
      parentUuid: "root-user",
      message: {
        role: "assistant",
        content: [
          { type: "thinking", thinking: "private chain" },
          { type: "text", text: "Inspection complete" },
          { type: "tool_use", name: "Read", input: { file: "/private" } },
        ],
      },
    },
  ]);

  const rendered = renderSession(session, { source: "claude" });
  assert.deepEqual(rendered.items.slice(0, 2), [
    { type: "userMessage", text: "Inspect [LOCAL_PATH]" },
    { type: "agentMessage", text: "Inspection complete" },
  ]);
  assert.deepEqual(rendered.items.at(-1), {
    type: "other",
    text: "1 read; raw tool outputs dropped: 1",
  });
  assert.doesNotMatch(
    JSON.stringify(rendered),
    /hidden skill expansion metadata|hidden sidechain response|hidden abandoned response|private policy|raw private result|private chain/,
  );
});

test("standalone Claude parser supports dedicated sidechain transcript files", () => {
  const session = path.join(tempDir(), "agent-sidechain.jsonl");
  writeJsonl(session, [
    { type: "system", subtype: "metadata", content: "unflagged metadata" },
    { type: "user", uuid: "agent-user", parentUuid: null, isSidechain: true, message: { role: "user", content: "Subagent task" } },
    { type: "assistant", uuid: "agent-reply", parentUuid: "agent-user", isSidechain: true, message: { role: "assistant", content: "Subagent result" } },
  ]);

  assert.deepEqual(renderSession(session, { source: "claude" }).items, [
    { type: "userMessage", text: "Subagent task" },
    { type: "agentMessage", text: "Subagent result" },
  ]);
});

test("standalone Claude parser follows logical parents across compaction", () => {
  const session = path.join(tempDir(), "compacted.jsonl");
  writeJsonl(session, [
    { type: "user", uuid: "before-user", parentUuid: null, message: { role: "user", content: "Before compact" } },
    { type: "assistant", uuid: "before-assistant", parentUuid: "before-user", message: { role: "assistant", content: "Earlier answer" } },
    { type: "user", uuid: "preserved-sibling", parentUuid: "unrelated-old-parent", message: { role: "user", content: "Preserved sibling" } },
    {
      type: "system",
      subtype: "compact_boundary",
      uuid: "boundary",
      parentUuid: null,
      logicalParentUuid: "before-assistant",
      compactMetadata: {
        preservedMessages: { uuids: ["preserved-sibling"] },
        preservedSegment: {
          headUuid: "preserved-sibling",
          anchorUuid: "compact-summary",
          tailUuid: "preserved-sibling",
        },
      },
    },
    { type: "user", uuid: "compact-summary", parentUuid: "boundary", isCompactSummary: true, message: { role: "user", content: "hidden compact summary" } },
    { type: "user", uuid: "after-user", parentUuid: "compact-summary", message: { role: "user", content: "After compact" } },
    { type: "progress", uuid: "dangling-progress", parentUuid: "before-assistant", content: "stale progress" },
  ]);

  assert.deepEqual(renderSession(session, { source: "claude" }).items, [
    { type: "userMessage", text: "Before compact" },
    { type: "agentMessage", text: "Earlier answer" },
    { type: "userMessage", text: "Preserved sibling" },
    { type: "userMessage", text: "After compact" },
  ]);
});

test("standalone parser preserves legitimately repeated turns", () => {
  const session = path.join(tempDir(), "repeated.jsonl");
  writeJsonl(session, [
    { type: "user", message: { role: "user", content: "continue" } },
    { type: "assistant", message: { role: "assistant", content: "working" } },
    { type: "user", message: { role: "user", content: "continue" } },
    { type: "assistant", message: { role: "assistant", content: "working" } },
  ]);

  assert.deepEqual(renderSession(session, { source: "claude" }).items, [
    { type: "userMessage", text: "continue" },
    { type: "agentMessage", text: "working" },
    { type: "userMessage", text: "continue" },
    { type: "agentMessage", text: "working" },
  ]);
});

test("standalone parser handles modern Codex items without reasoning or raw output", () => {
  const session = path.join(tempDir(), "rollout.jsonl");
  writeJsonl(session, [
    { type: "session_meta", payload: { id: "33333333-4444-4555-8666-777777777777" } },
    { type: "event_msg", payload: { type: "item_completed", item: { type: "user_message", content: [{ type: "text", text: "Run proof" }] } } },
    { type: "event_msg", payload: { type: "item_completed", item: { type: "reasoning", text: "private reasoning" } } },
    { type: "event_msg", payload: { type: "item_completed", item: { type: "web_search", query: "docs" } } },
    { type: "event_msg", payload: { type: "item_completed", item: { type: "file_change", changes: ["file.ts"] } } },
    { type: "event_msg", payload: { type: "item_completed", item: { type: "command_execution", command: ["npm", "test"], aggregatedOutput: "raw command output" } } },
    { type: "event_msg", payload: { type: "item_completed", item: { type: "mcp_tool_call", result: { content: "raw MCP result" } } } },
    { type: "event_msg", payload: { type: "item_completed", item: { type: "agent_message", content: [{ type: "text", text: "Proof passed" }] } } },
  ]);

  const rendered = renderSession(session, { source: "codex" });
  assert.equal(rendered.identity, "33333333-4444-4555-8666-777777777777");
  assert.deepEqual(rendered.items.slice(0, 2), [
    { type: "userMessage", text: "Run proof" },
    { type: "agentMessage", text: "Proof passed" },
  ]);
  assert.deepEqual(rendered.items.at(-1), {
    type: "other",
    text: "1 write, 2 execute, 1 network; raw tool outputs dropped: 2",
  });
  assert.doesNotMatch(
    JSON.stringify(rendered),
    /private reasoning|raw command output|raw MCP result/,
  );
});

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
  assert.equal(payload.source, "claude");
  assert.equal(payload.items[0].type, "userMessage");
  assert.match(payload.items[0].text, /\[LOCAL_PATH\]/);
  assert.match(payload.items[0].text, /\[REDACTED_AUTH_HEADER\]/);
  assert.doesNotMatch(result.stdout, /abcdefghijklmnopqrstuvwxyz123456|hidden compact summary/);
  assert.equal(payload.beamId.length, 32);
});

test("publish bounds transcript item count for the receiver schema", async () => {
  const session = path.join(tempDir(), "many-messages.jsonl");
  writeJsonl(
    session,
    Array.from({ length: 205 }, (_, index) => ({
      type: index % 2 === 0 ? "user" : "assistant",
      message: { role: index % 2 === 0 ? "user" : "assistant", content: `message-${index}` },
    })),
  );
  const result = await run([
    "publish",
    "--endpoint",
    "http://127.0.0.1:9/api/v1/beam/sessions",
    "--session",
    session,
    "--dry-run",
    "--quiet",
  ]);

  assert.equal(result.code, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.items.length, 200);
  assert.equal(payload.truncated, true);
  assert.equal(payload.items[0].text, "message-5");
});

test("publish honors the total max-chars disclosure limit", async () => {
  const session = path.join(tempDir(), "limited.jsonl");
  writeJsonl(session, [
    { type: "user", message: { role: "user", content: "alpha ".repeat(16) } },
    { type: "assistant", message: { role: "assistant", content: "bravo ".repeat(16) } },
  ]);
  const result = await run([
    "publish",
    "--endpoint",
    "http://127.0.0.1:9/api/v1/beam/sessions",
    "--session",
    session,
    "--max-chars",
    "50",
    "--title",
    "   ",
    "--dry-run",
    "--quiet",
  ]);

  assert.equal(result.code, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.truncated, true);
  assert.ok(payload.items.reduce((sum, item) => sum + item.text.length, 0) <= 50);
  assert.doesNotMatch(payload.title, /^alpha/);
});

test("publish preserves a visible message when byte trimming drops tool summaries", async () => {
  const session = path.join(tempDir(), "multibyte.jsonl");
  writeJsonl(session, [
    { type: "user", message: { role: "user", content: "🦞".repeat(20_000) } },
    { type: "tool_use", name: "exec" },
  ]);
  const result = await run([
    "publish",
    "--endpoint",
    "http://127.0.0.1:9/api/v1/beam/sessions",
    "--session",
    session,
    "--max-chars",
    "48000",
    "--entry-max-chars",
    "48000",
    "--dry-run",
    "--quiet",
  ]);

  assert.equal(result.code, 0, result.stderr);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.items.some((item) => item.type === "userMessage"), true);
  assert.equal(payload.items.every((item) => item.type !== "other"), true);
  assert.equal(payload.truncated, true);
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
  assert.match(result.stderr, /no exact Claude session transcript was found/);
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
      "Share /workspace/private with Bearer abcdefghijklmnopqrstuvwxyz123456",
      "--cwd",
      projectDir,
      "--dry-run",
      "--quiet",
    ],
    { env: { HOME: home, CLAUDE_CONFIG_DIR: configDir } },
  );

  assert.equal(result.code, 0, result.stderr);
  assert.equal(
    JSON.parse(result.stdout).title,
    "Share [LOCAL_PATH] with [REDACTED_AUTH_HEADER]",
  );
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

test("root live hooks ignore subagent Stop events", async () => {
  const session = claudeSession();
  const result = await run(
    ["hook", "--endpoint", "http://127.0.0.1:9/api/v1/beam/sessions", "--dry-run", "--quiet"],
    {
      stdin: JSON.stringify({
        transcript_path: session,
        hook_event_name: "Stop",
        agent_id: "child-agent",
      }),
    },
  );

  assert.equal(result.code, 0, result.stderr);
  assert.equal(result.stdout, "");
});

test("root hooks publish even when the configured path contains subagents", async () => {
  const dir = path.join(tempDir(), "subagents", "custom-root");
  fs.mkdirSync(dir, { recursive: true });
  const session = path.join(dir, "root.jsonl");
  writeJsonl(session, [
    { type: "user", message: { role: "user", content: "Root hook under custom path" } },
  ]);
  const result = await run(
    ["hook", "--endpoint", "http://127.0.0.1:9/api/v1/beam/sessions", "--dry-run", "--quiet"],
    { stdin: JSON.stringify({ transcript_path: session, hook_event_name: "Stop" }) },
  );

  assert.equal(result.code, 0, result.stderr);
  assert.match(result.stdout, /Root hook under custom path/);
});

test("hook file failures do not print the local path", async () => {
  const missing = path.join(tempDir(), "private", "missing.jsonl");
  const result = await run(
    ["hook", "--endpoint", "http://127.0.0.1:9/api/v1/beam/sessions", "--dry-run", "--quiet"],
    {
      stdin: JSON.stringify({ transcript_path: missing, hook_event_name: "Stop" }),
    },
  );

  assert.equal(result.code, 1);
  assert.match(result.stderr, /hook transcript file does not exist/);
  assert.doesNotMatch(result.stderr, new RegExp(missing.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
});

test("hook identifiers override stale ambient session variables", async () => {
  const configDir = tempDir();
  const projectDir = path.join(configDir, "projects", "demo");
  fs.mkdirSync(projectDir, { recursive: true });
  const hookId = "77777777-8888-4999-8aaa-bbbbbbbbbbbb";
  const staleId = "88888888-9999-4aaa-8bbb-cccccccccccc";
  writeJsonl(path.join(projectDir, `${hookId}.jsonl`), [
    { type: "user", sessionId: hookId, message: { role: "user", content: "Authoritative hook session" } },
  ]);
  writeJsonl(path.join(projectDir, `${staleId}.jsonl`), [
    { type: "user", sessionId: staleId, message: { role: "user", content: "Stale ambient session" } },
  ]);
  const result = await run(
    ["hook", "--endpoint", "http://127.0.0.1:9/api/v1/beam/sessions", "--dry-run", "--quiet"],
    {
      env: { CLAUDE_CONFIG_DIR: configDir, CODEX_HOME: tempDir(), CLAUDE_SESSION_ID: staleId, CODEX_THREAD_ID: "" },
      stdin: JSON.stringify({ session_id: hookId, hook_event_name: "Stop" }),
    },
  );

  assert.equal(result.code, 0, result.stderr);
  assert.match(result.stdout, /Authoritative hook session/);
  assert.doesNotMatch(result.stdout, /Stale ambient session/);
});

test("hook identifiers fail closed when both native stores contain the same id", async () => {
  const configDir = tempDir();
  const codexHome = tempDir();
  const claudeDir = path.join(configDir, "projects", "demo");
  const codexDir = path.join(codexHome, "sessions", "2026", "07", "22");
  fs.mkdirSync(claudeDir, { recursive: true });
  fs.mkdirSync(codexDir, { recursive: true });
  const id = "abababab-cdcd-4efe-8aaa-bcbcbcbcbcbc";
  writeJsonl(path.join(claudeDir, `${id}.jsonl`), [
    { type: "user", sessionId: id, message: { role: "user", content: "Claude copy" } },
  ]);
  writeJsonl(path.join(codexDir, `rollout-${id}.jsonl`), [
    { type: "session_meta", payload: { id } },
    { type: "event_msg", payload: { type: "user_message", message: "Codex copy" } },
  ]);
  const result = await run(
    ["hook", "--endpoint", "http://127.0.0.1:9/api/v1/beam/sessions", "--dry-run", "--quiet"],
    {
      env: { CLAUDE_CONFIG_DIR: configDir, CODEX_HOME: codexHome, CLAUDE_SESSION_ID: "", CODEX_THREAD_ID: "" },
      stdin: JSON.stringify({ session_id: id, hook_event_name: "Stop" }),
    },
  );

  assert.equal(result.code, 1);
  assert.match(result.stderr, /matches both Claude and Codex transcripts/);
  assert.equal(result.stdout, "");
});

test("unresolved hook identifiers fail closed instead of using ambient sessions", async () => {
  const configDir = tempDir();
  const projectDir = path.join(configDir, "projects", "demo");
  fs.mkdirSync(projectDir, { recursive: true });
  const staleId = "99999999-aaaa-4bbb-8ccc-dddddddddddd";
  writeJsonl(path.join(projectDir, `${staleId}.jsonl`), [
    { type: "user", sessionId: staleId, message: { role: "user", content: "Ambient session must not publish" } },
  ]);
  const result = await run(
    ["hook", "--endpoint", "http://127.0.0.1:9/api/v1/beam/sessions", "--dry-run", "--quiet"],
    {
      env: { CLAUDE_CONFIG_DIR: configDir, CODEX_HOME: tempDir(), CLAUDE_SESSION_ID: staleId, CODEX_THREAD_ID: "" },
      stdin: JSON.stringify({
        session_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        hook_event_name: "Stop",
      }),
    },
  );

  assert.equal(result.code, 1);
  assert.match(result.stderr, /no exact transcript was found for the hook session id/);
  assert.doesNotMatch(result.stdout, /Ambient session/);
});

test("hook prefers transcript_path over agent_transcript_path", async () => {
  const authoritative = claudeSession();
  const stale = path.join(tempDir(), "stale.jsonl");
  writeJsonl(stale, [
    { type: "user", message: { role: "user", content: "Wrong transcript" } },
  ]);
  const result = await run(
    ["hook", "--endpoint", "http://127.0.0.1:9/api/v1/beam/sessions", "--dry-run", "--quiet"],
    {
      stdin: JSON.stringify({
        session_id: "11111111-2222-4333-8444-555555555555",
        transcript_path: authoritative,
        agent_transcript_path: stale,
        hook_event_name: "Stop",
      }),
    },
  );

  assert.equal(result.code, 0, result.stderr);
  assert.match(result.stdout, /Fix the upload flow/);
  assert.doesNotMatch(result.stdout, /Wrong transcript/);
});

test("hook resolves an exact Claude session from session_id when no path is supplied", async () => {
  const configDir = tempDir();
  const projectDir = path.join(configDir, "projects", "demo");
  fs.mkdirSync(projectDir, { recursive: true });
  const sessionId = "66666666-7777-4888-8999-000000000000";
  writeJsonl(path.join(projectDir, `${sessionId}.jsonl`), [
    { type: "user", sessionId, message: { role: "user", content: "Hook id fallback" } },
  ]);
  const result = await run(
    ["hook", "--endpoint", "http://127.0.0.1:9/api/v1/beam/sessions", "--dry-run", "--quiet"],
    {
      env: { CLAUDE_CONFIG_DIR: configDir, CODEX_HOME: tempDir(), CLAUDE_SESSION_ID: "", CODEX_THREAD_ID: "" },
      stdin: JSON.stringify({ session_id: sessionId, hook_event_name: "Stop" }),
    },
  );

  assert.equal(result.code, 0, result.stderr);
  assert.match(result.stdout, /Hook id fallback/);
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

test("hook can publish the reliable final message before transcript flush", async () => {
  const session = path.join(tempDir(), "empty.jsonl");
  writeJsonl(session, [{ type: "summary", summary: "hidden context" }]);
  const result = await run(
    ["hook", "--endpoint", "http://127.0.0.1:9/api/v1/beam/sessions", "--dry-run", "--quiet"],
    {
      stdin: JSON.stringify({
        transcript_path: session,
        hook_event_name: "Stop",
        last_assistant_message: "Final response before flush",
      }),
    },
  );

  assert.equal(result.code, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout).items, [
    { type: "agentMessage", text: "Final response before flush" },
  ]);
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
      const received = JSON.parse(requestBody);
      response.writeHead(200, { "content-type": "application/json" });
      response.end(
        JSON.stringify({
          ok: true,
          url: `/beam/${received.beamId.slice(0, 12)}`,
        }),
      );
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
  assert.match(
    result.stdout,
    new RegExp(`http://127\\.0\\.0\\.1:${address.port}/beam/[a-f0-9]{12}`),
  );
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

test("publish rejects receiver URLs containing reflected credentials", async (t) => {
  const session = claudeSession();
  const server = http.createServer((_request, response) => {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(
      JSON.stringify({ ok: true, url: "/chat?note=100%&credential=%74est-access-token" }),
    );
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => server.close());
  const address = server.address();

  const result = await run(
    ["publish", "--endpoint", `http://127.0.0.1:${address.port}/api/v1/beam/sessions`, "--session", session],
    { env: { BEAM_ACCESS_TOKEN: "test-access-token" } },
  );

  assert.equal(result.code, 1);
  assert.match(result.stderr, /unsafe session URL/);
  assert.doesNotMatch(`${result.stdout}\n${result.stderr}`, /test-access-token/);
});

test("publish accepts bare and named Beam URLs below the endpoint-derived base path", async (t) => {
  const session = claudeSession();
  let makePath;
  let returnedPath;
  const endpoint = await beamReceiverEndpoint(
    t,
    ({ beamId }) => (returnedPath = `/openclaw/beam/${makePath(beamId)}`),
    "/openclaw",
  );
  const cases = [
    ["bare prefix", (beamId) => beamId.slice(0, 12)],
    ["bare full id", (beamId) => beamId],
    ["current title", (beamId) => `current-session-title-${beamId.slice(0, 12)}`],
    ["stale title", (beamId) => `previous-title-${beamId.slice(0, 12)}`],
    ["named full id", (beamId) => `collision-fallback-${beamId}`],
    ["maximum title length", (beamId) => `${"a".repeat(48)}-${beamId.slice(0, 12)}`],
  ];

  for (const [label, pathFactory] of cases) {
    makePath = pathFactory;
    const result = await run([
      "publish",
      "--endpoint",
      endpoint,
      "--session",
      session,
      "--title",
      "Current session title",
    ]);

    assert.equal(result.code, 0, `${label}: ${result.stderr}`);
    assert.ok(result.stdout.includes(returnedPath), label);
  }
});

test("publish accepts the current canonical catalog URL during rollout", async (t) => {
  const session = claudeSession();
  const endpoint = await beamReceiverEndpoint(
    t,
    (payload) =>
      `/chat/roboclaw?catalog=beam&host=gateway&thread=${payload.beamId}`,
  );
  const result = await run([
    "publish",
    "--endpoint",
    endpoint,
    "--session",
    session,
  ]);

  assert.equal(result.code, 0, result.stderr);
  assert.match(
    result.stdout,
    /\/chat\/roboclaw\?catalog=beam&host=gateway&thread=[a-f0-9]{32}/,
  );
});

test("publish rejects malformed pretty Beam URLs", async (t) => {
  const session = claudeSession();
  let makeUrl;
  const endpoint = await beamReceiverEndpoint(t, (payload, request) =>
    makeUrl(payload, request),
  );
  const cases = [
    ["short id", ({ beamId }) => `/beam/${beamId.slice(0, 11)}`],
    ["uppercase id", ({ beamId }) => `/beam/${beamId.slice(0, 12).toUpperCase()}`],
    ["nonhex id", ({ beamId }) => `/beam/${beamId.slice(0, 11)}g`],
    ["long id", ({ beamId }) => `/beam/${beamId}0`],
    ["uppercase title", ({ beamId }) => `/beam/Current-title-${beamId.slice(0, 12)}`],
    ["long title", ({ beamId }) => `/beam/${"a".repeat(49)}-${beamId.slice(0, 12)}`],
    ["empty title", ({ beamId }) => `/beam/-${beamId.slice(0, 12)}`],
    ["title with empty word", ({ beamId }) => `/beam/current--title-${beamId.slice(0, 12)}`],
    ["title with trailing hyphen", ({ beamId }) => `/beam/current-title--${beamId.slice(0, 12)}`],
    ["title with punctuation", ({ beamId }) => `/beam/current_title-${beamId.slice(0, 12)}`],
    ["encoded title", ({ beamId }) => `/beam/current%2ftitle-${beamId.slice(0, 12)}`],
    ["named short id", ({ beamId }) => `/beam/current-title-${beamId.slice(0, 11)}`],
    ["named uppercase id", ({ beamId }) => `/beam/current-title-${beamId.slice(0, 12).toUpperCase()}`],
    ["named nonhex id", ({ beamId }) => `/beam/current-title-${beamId.slice(0, 11)}g`],
    ["named long id", ({ beamId }) => `/beam/current-title-${beamId}0`],
    [
      "wrong prefix",
      ({ beamId }) => `/beam/${beamId[0] === "0" ? "1" : "0"}${beamId.slice(1, 12)}`,
    ],
    [
      "named wrong prefix",
      ({ beamId }) => `/beam/current-title-${beamId[0] === "0" ? "1" : "0"}${beamId.slice(1, 12)}`,
    ],
    ["extra segment", ({ beamId }) => `/beam/${beamId.slice(0, 12)}/extra`],
    ["query", ({ beamId }) => `/beam/${beamId.slice(0, 12)}?view=debug`],
    [
      "duplicate query",
      ({ beamId }) => `/beam/${beamId.slice(0, 12)}?thread=${beamId}&thread=${beamId}`,
    ],
    ["wrong base path", ({ beamId }) => `/secret-prefix/beam/${beamId.slice(0, 12)}`],
    ["foreign origin", ({ beamId }) => `https://example.test/beam/${beamId.slice(0, 12)}`],
    [
      "credentials",
      ({ beamId }, request) =>
        `http://user@${request.headers.host}/beam/${beamId.slice(0, 12)}`,
    ],
    ["hash", ({ beamId }) => `/beam/${beamId.slice(0, 12)}#fragment`],
    ["control", ({ beamId }) => `/beam/${beamId.slice(0, 12)}\n`],
    ["non-http", ({ beamId }) => `ftp://example.test/beam/${beamId.slice(0, 12)}`],
  ];

  for (const [label, urlFactory] of cases) {
    makeUrl = urlFactory;
    const result = await run([
      "publish",
      "--endpoint",
      endpoint,
      "--session",
      session,
    ]);
    assert.equal(result.code, 1, label);
    assert.match(result.stderr, /unsafe session URL/, label);
  }
});

test("publish rejects malformed rollout catalog URLs", async (t) => {
  const session = claudeSession();
  let makeUrl;
  const endpoint = await beamReceiverEndpoint(t, (payload) => makeUrl(payload));
  const canonical = (beamId) =>
    `/chat/roboclaw?catalog=beam&host=gateway&thread=${beamId}`;
  const cases = [
    ["duplicate thread", ({ beamId }) => `${canonical(beamId)}&thread=extra`],
    ["extra query", ({ beamId }) => `${canonical(beamId)}&view=debug`],
    ["wrong base path", ({ beamId }) => `/secret-prefix${canonical(beamId)}`],
    [
      "missing agent",
      ({ beamId }) => `/chat?catalog=beam&host=gateway&thread=${beamId}`,
    ],
    [
      "extra segment",
      ({ beamId }) =>
        `/chat/roboclaw/extra?catalog=beam&host=gateway&thread=${beamId}`,
    ],
    [
      "legacy beta session",
      ({ beamId }) =>
        `/chat?session=${encodeURIComponent(`catalog:beam:gateway:${beamId}`)}`,
    ],
    [
      "wrong catalog",
      ({ beamId }) => `/chat/roboclaw?catalog=other&host=gateway&thread=${beamId}`,
    ],
    [
      "wrong host",
      ({ beamId }) => `/chat/roboclaw?catalog=beam&host=other&thread=${beamId}`,
    ],
    ["wrong thread", () => "/chat/roboclaw?catalog=beam&host=gateway&thread=other"],
    [
      "invalid agent",
      ({ beamId }) => `/chat/Bad.Agent?catalog=beam&host=gateway&thread=${beamId}`,
    ],
  ];

  for (const [label, urlFactory] of cases) {
    makeUrl = urlFactory;
    const result = await run([
      "publish",
      "--endpoint",
      endpoint,
      "--session",
      session,
    ]);
    assert.equal(result.code, 1, label);
    assert.match(result.stderr, /unsafe session URL/, label);
  }
});

test("publish never prints access tokens on receiver errors", async (t) => {
  const session = claudeSession();
  const server = http.createServer((_request, response) => {
    response.writeHead(401, { "content-type": "application/json" });
    const escape = String.fromCharCode(27);
    response.end(
      JSON.stringify({
        ok: false,
        error: `not authorized super-secret-\n${escape}[31maccess-token\nforged${escape}[0m`,
      }),
    );
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(() => server.close());
  const address = server.address();

  const result = await run(
    ["publish", "--endpoint", `http://127.0.0.1:${address.port}/api/v1/beam/sessions`, "--session", session],
    { env: { BEAM_ACCESS_TOKEN: "super-secret-access-token" } },
  );

  assert.equal(result.code, 1);
  assert.match(result.stderr, /Beam upload failed: HTTP 401/);
  assert.equal(result.stderr.includes(String.fromCharCode(27)), false);
  assert.doesNotMatch(result.stderr, /\nforged/);
  assert.doesNotMatch(`${result.stdout}\n${result.stderr}`, /super-secret-access-token/);
});
