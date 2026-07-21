import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const script = path.resolve("skills/agent-transcript/scripts/agent-transcript");

function tempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "agent-transcript-test-"));
}

function writeJsonl(file, rows) {
  fs.writeFileSync(file, `${rows.map((row) => JSON.stringify(row)).join("\n")}\n`);
}

function run(args, options = {}) {
  return execFileSync(process.execPath, [script, ...args], {
    cwd: path.resolve("."),
    encoding: "utf8",
    ...options,
  });
}

test("render redacts common secrets and local identifiers", () => {
  const dir = tempDir();
  const session = path.join(dir, "session.jsonl");
  writeJsonl(session, [
    {
      type: "response_item",
      payload: {
        role: "user",
        content: [
          {
            type: "text",
            text: "Use /Users/ahmed/project, email person@example.com, and header Bearer abcdefghijklmnopqrstuvwxyz123456.",
          },
        ],
      },
    },
    { type: "response_item", payload: { role: "assistant", content: [{ type: "text", text: "Done." }] } },
  ]);

  const output = run(["render", "--session", session]);
  assert.match(output, /\[LOCAL_PATH\]/);
  assert.match(output, /\[REDACTED_EMAIL\]/);
  assert.match(output, /\[REDACTED_AUTH_HEADER\]/);
  assert.doesNotMatch(output, /person@example\.com/);
  assert.doesNotMatch(output, /abcdefghijklmnopqrstuvwxyz123456/);
});

test("render drops raw tool outputs but keeps a compact tool summary", () => {
  const dir = tempDir();
  const session = path.join(dir, "session.jsonl");
  writeJsonl(session, [
    { type: "response_item", payload: { role: "user", content: [{ type: "text", text: "Run tests." }] } },
    { type: "response_item", payload: { type: "function_call", name: "exec_command", arguments: "npm test" } },
    {
      type: "response_item",
      payload: { type: "function_call_output", output: "raw output with sk-abcdefghijklmnopqrstuvwxyz123456" },
    },
  ]);

  const output = run(["render", "--session", session]);
  assert.match(output, /tool summary/);
  assert.match(output, /1 execute/);
  assert.doesNotMatch(output, /raw output/);
  assert.doesNotMatch(output, /sk-abcdefghijklmnopqrstuvwxyz123456/);
});

test("append-body replaces an existing transcript section", () => {
  const dir = tempDir();
  const session = path.join(dir, "session.jsonl");
  const body = path.join(dir, "body.md");
  writeJsonl(session, [
    { type: "response_item", payload: { role: "user", content: [{ type: "text", text: "New scoped work." }] } },
    { type: "response_item", payload: { role: "assistant", content: [{ type: "text", text: "Implemented." }] } },
  ]);
  fs.writeFileSync(
    body,
    "# PR\n\n<!-- agent-transcript:start -->\nold transcript\n<!-- agent-transcript:end -->\n"
  );

  const output = run(["append-body", "--body", body, "--session", session]);
  assert.match(output, /# PR/);
  assert.match(output, /New scoped work/);
  assert.doesNotMatch(output, /old transcript/);
  assert.equal((output.match(/agent-transcript:start/g) || []).length, 1);
});

test("find scans CLAUDE_CONFIG_DIR projects and labels them as Claude", () => {
  const dir = tempDir();
  const home = tempDir();
  const projectDir = path.join(dir, "projects", "-tmp-agent-transcript");
  fs.mkdirSync(projectDir, { recursive: true });
  const session = path.join(projectDir, "11111111-2222-4333-8444-555555555555.jsonl");
  writeJsonl(session, [
    { type: "user", message: { role: "user", content: "claude-config-dir-marker" } },
    { type: "assistant", message: { role: "assistant", content: "Done." } },
  ]);

  const output = run(["find", "--query", "claude-config-dir-marker", "--since-days", "1", "--max-files", "20"], {
    env: { ...process.env, HOME: home, CLAUDE_CONFIG_DIR: `${dir}${path.sep}` },
  });
  const matches = JSON.parse(output);

  assert.equal(matches.length, 1);
  assert.equal(matches[0].file, session);
  assert.equal(matches[0].agent, "claude");
});

test("find labels explicit roots under trailing-slash CLAUDE_CONFIG_DIR as Claude", () => {
  const dir = tempDir();
  const home = tempDir();
  const projectRoot = path.join(dir, "projects");
  const projectDir = path.join(projectRoot, "-tmp-agent-transcript");
  fs.mkdirSync(projectDir, { recursive: true });
  const session = path.join(projectDir, "22222222-3333-4444-8555-666666666666.jsonl");
  writeJsonl(session, [
    { type: "user", message: { role: "user", content: "claude-config-dir-explicit-root-marker" } },
    { type: "assistant", message: { role: "assistant", content: "Done." } },
  ]);

  const output = run(
    [
      "find",
      "--query",
      "claude-config-dir-explicit-root-marker",
      "--since-days",
      "1",
      "--max-files",
      "20",
      "--root",
      projectRoot,
    ],
    { env: { ...process.env, HOME: home, CLAUDE_CONFIG_DIR: `${dir}${path.sep}` } }
  );
  const matches = JSON.parse(output);

  assert.equal(matches.length, 1);
  assert.equal(matches[0].file, session);
  assert.equal(matches[0].agent, "claude");
});

test("find scans CODEX_HOME sessions and archived sessions", () => {
  const home = tempDir();
  const codexHome = tempDir();
  const sessionDir = path.join(codexHome, "sessions", "2026", "07", "20");
  const archivedDir = path.join(codexHome, "archived_sessions");
  fs.mkdirSync(sessionDir, { recursive: true });
  fs.mkdirSync(archivedDir, { recursive: true });
  const active = path.join(sessionDir, "rollout-2026-07-20T12-00-00-11111111-2222-4333-8444-555555555555.jsonl");
  const archived = path.join(archivedDir, "rollout-2026-07-19T12-00-00-22222222-3333-4444-8555-666666666666.jsonl");
  writeJsonl(active, [{ type: "event_msg", payload: { type: "user_message", message: "active-codex-marker" } }]);
  writeJsonl(archived, [{ type: "event_msg", payload: { type: "user_message", message: "archived-codex-marker" } }]);

  const env = { ...process.env, HOME: home, CODEX_HOME: codexHome };
  const activeMatches = JSON.parse(
    run(["find", "--query", "active-codex-marker", "--since-days", "7"], { env }),
  );
  const archivedMatches = JSON.parse(
    run(["find", "--query", "archived-codex-marker", "--since-days", "7"], { env }),
  );

  assert.equal(activeMatches[0].file, active);
  assert.equal(activeMatches[0].agent, "codex");
  assert.equal(archivedMatches[0].file, archived);
  assert.equal(archivedMatches[0].agent, "codex");
});

test("render-json normalizes paginated Codex completed items and metadata thread id", () => {
  const dir = tempDir();
  const session = path.join(dir, "rollout.jsonl");
  writeJsonl(session, [
    {
      type: "session_meta",
      payload: { id: "33333333-4444-4555-8666-777777777777", session_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee" },
    },
    {
      type: "event_msg",
      payload: {
        type: "item_completed",
        item: { type: "user_message", id: "u1", content: [{ type: "text", text: "Modern user turn" }] },
      },
    },
    {
      type: "event_msg",
      payload: {
        type: "item_completed",
        item: { type: "agent_message", id: "a1", content: [{ type: "text", text: "Modern assistant turn" }] },
      },
    },
    {
      type: "event_msg",
      payload: {
        type: "item_completed",
        item: { type: "command_execution", id: "t1", command: ["npm", "test"] },
      },
    },
  ]);

  const output = JSON.parse(run(["render-json", "--session", session]));
  assert.equal(output.version, 1);
  assert.equal(output.agent, "codex");
  assert.equal(output.threadId, "33333333-4444-4555-8666-777777777777");
  assert.deepEqual(output.items.slice(0, 2), [
    { role: "user", text: "Modern user turn" },
    { role: "assistant", text: "Modern assistant turn" },
  ]);
  assert.deepEqual(output.items.at(-1), {
    role: "tool summary",
    text: "1 execute; raw tool outputs dropped: 0",
  });
});
