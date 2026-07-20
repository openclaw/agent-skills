import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";

const script = path.join(import.meta.dirname, "agent-transcript");
const { sessionScanRecord } = await import(pathToFileURL(script).href);

function tempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "agent-transcript-test-"));
}

function writeJsonl(file, rows) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${rows.map((row) => JSON.stringify(row)).join("\n")}\n`);
}

function run(args, options = {}) {
  return execFileSync(process.execPath, [script, ...args], {
    cwd: import.meta.dirname,
    encoding: "utf8",
    ...options,
  });
}

function copilotEvents(messages) {
  return [
    {
      type: "session.start",
      data: {
        sessionId: "copilot-session",
        producer: "copilot-agent",
      },
    },
    ...messages,
  ];
}

test("CLI runs through a symlinked entry point", (t) => {
  const dir = tempDir();
  const link = path.join(dir, "agent-transcript");
  try {
    fs.symlinkSync(script, link, "file");
  } catch (error) {
    if (error?.code === "EPERM") {
      t.skip("symlink creation is unavailable");
      return;
    }
    throw error;
  }

  const output = execFileSync(process.execPath, [link, "--help"], {
    encoding: "utf8",
  });

  assert.match(output, /Usage:/);
  assert.match(output, /agent-transcript find/);
});

test("find discovers Copilot sessions from the default local session-state root", () => {
  const home = tempDir();
  const session = path.join(home, ".copilot", "session-state", "copilot-session", "events.jsonl");
  writeJsonl(
    session,
    copilotEvents([
      {
        type: "user.message",
        data: {
          content: "Implement portable-copilot-marker in a local checkout.",
        },
      },
    ]),
  );

  const output = run(["find", "--query", "portable-copilot-marker", "--cwd", "."], {
    env: { ...process.env, HOME: home, USERPROFILE: home },
  });
  const matches = JSON.parse(output);

  assert.equal(matches.length, 1);
  assert.equal(matches[0].file, session);
  assert.equal(matches[0].agent, "copilot");
});

test("find detects Copilot producers in explicit roots and scans visible dialogue only", () => {
  const dir = tempDir();
  const home = tempDir();
  const session = path.join(dir, "events.jsonl");
  writeJsonl(
    session,
    copilotEvents([
      {
        type: "user.message",
        data: {
          content: "visible-copilot-marker",
          transformedContent: "PRIVATE_TRANSFORMED_SCAN_MARKER",
        },
      },
    ]),
  );

  const options = {
    env: { ...process.env, HOME: home, USERPROFILE: home },
  };
  const visible = JSON.parse(
    run(["find", "--query", "visible-copilot-marker", "--root", dir, "--since-days", "1"], options),
  );
  const privateField = JSON.parse(
    run(["find", "--query", "PRIVATE_TRANSFORMED_SCAN_MARKER", "--root", dir, "--since-days", "1"], options),
  );

  assert.equal(visible.length, 1);
  assert.equal(visible[0].file, session);
  assert.equal(visible[0].agent, "copilot");
  assert.deepEqual(privateField, []);
});

test("scan avoids complete-row parsing for known Codex and Claude paths", () => {
  const dir = tempDir();
  const claudeConfig = path.join(dir, "claude-config");
  const sessions = [
    {
      agent: "codex",
      file: path.join(dir, ".codex", "sessions", "codex.jsonl"),
    },
    {
      agent: "claude",
      file: path.join(claudeConfig, "projects", "-tmp-project", "claude.jsonl"),
    },
  ];
  const previousClaudeConfig = process.env.CLAUDE_CONFIG_DIR;
  process.env.CLAUDE_CONFIG_DIR = claudeConfig;
  try {
    for (const session of sessions) {
      writeJsonl(session.file, [
        {
          type: "response_item",
          payload: {
            role: "user",
            content: [{ type: "text", text: `${session.agent}-visible-marker` }],
          },
        },
      ]);
      const record = sessionScanRecord(session.file, 120, {
        readCopilotProducerProbe() {
          throw new Error(`producer probe should not run for known ${session.agent} paths`);
        },
        readBoundedJsonlRows() {
          throw new Error(`complete-row parser should not run for known ${session.agent} paths`);
        },
      });

      assert.equal(record.agent, session.agent);
      assert.match(record.haystack, new RegExp(`${session.agent}-visible-marker`));
    }
  } finally {
    if (previousClaudeConfig == null) delete process.env.CLAUDE_CONFIG_DIR;
    else process.env.CLAUDE_CONFIG_DIR = previousClaudeConfig;
  }
});

test("scan promotes an unknown path after a bounded Copilot producer probe", () => {
  const dir = tempDir();
  const session = path.join(dir, "events.jsonl");
  writeJsonl(session, [{ type: "private.event", data: { content: "PRIVATE_SCAN_MARKER" } }]);
  let probeCalls = 0;
  let completeRowCalls = 0;

  const record = sessionScanRecord(session, 120, {
    readCopilotProducerProbe() {
      probeCalls++;
      return copilotEvents([]);
    },
    readBoundedJsonlRows() {
      completeRowCalls++;
      return copilotEvents([
        {
          type: "user.message",
          data: {
            content: "visible-producer-marker",
            transformedContent: "PRIVATE_TRANSFORMED_MARKER",
          },
        },
      ]);
    },
  });

  assert.equal(record.agent, "copilot");
  assert.equal(probeCalls, 1);
  assert.equal(completeRowCalls, 1);
  assert.match(record.haystack, /visible-producer-marker/);
  assert.doesNotMatch(record.haystack, /PRIVATE_SCAN_MARKER|PRIVATE_TRANSFORMED_MARKER/);
});

test("find parses Copilot visible events larger than the scan-byte budget", () => {
  const dir = tempDir();
  const home = tempDir();
  const session = path.join(dir, "events.jsonl");
  writeJsonl(
    session,
    copilotEvents([
      {
        type: "user.message",
        data: {
          content: `prefix-${"x".repeat(400)}-copilot-boundary-marker-${"y".repeat(400)}`,
        },
      },
    ]),
  );

  const output = run(
    [
      "find",
      "--query",
      "copilot-boundary-marker",
      "--root",
      dir,
      "--since-days",
      "1",
      "--scan-bytes",
      "120",
    ],
    { env: { ...process.env, HOME: home, USERPROFILE: home } },
  );
  const matches = JSON.parse(output);

  assert.equal(matches.length, 1);
  assert.equal(matches[0].file, session);
  assert.equal(matches[0].agent, "copilot");
});

test("find parses Copilot visible events up to the boundary record cap", () => {
  const dir = tempDir();
  const home = tempDir();
  const session = path.join(dir, "events.jsonl");
  writeJsonl(
    session,
    copilotEvents([
      {
        type: "user.message",
        data: {
          content: `prefix-${"x".repeat(330 * 1024)}-copilot-large-record-marker`,
        },
      },
    ]),
  );

  const output = run(
    [
      "find",
      "--query",
      "copilot-large-record-marker",
      "--root",
      dir,
      "--since-days",
      "1",
      "--scan-bytes",
      "60000",
    ],
    { env: { ...process.env, HOME: home, USERPROFILE: home } },
  );
  const matches = JSON.parse(output);

  assert.equal(matches.length, 1);
  assert.equal(matches[0].file, session);
  assert.equal(matches[0].agent, "copilot");
});

test("find keeps the first Copilot event after overlapping scan ranges", () => {
  const dir = tempDir();
  const home = tempDir();
  const session = path.join(dir, "events.jsonl");
  writeJsonl(
    session,
    copilotEvents([
      {
        type: "user.message",
        data: {
          content: `prefix-${"x".repeat(800)}`,
        },
      },
      {
        type: "assistant.message",
        data: {
          content: "first-non-overlapping-event-marker",
        },
      },
    ]),
  );

  const output = run(
    [
      "find",
      "--query",
      "first-non-overlapping-event-marker",
      "--root",
      dir,
      "--since-days",
      "1",
      "--scan-bytes",
      "400",
    ],
    { env: { ...process.env, HOME: home, USERPROFILE: home } },
  );
  const matches = JSON.parse(output);

  assert.equal(matches.length, 1);
  assert.equal(matches[0].file, session);
  assert.equal(matches[0].agent, "copilot");
});

test("render keeps visible Copilot dialogue and drops private event data", () => {
  const dir = tempDir();
  const session = path.join(dir, ".copilot", "session-state", "copilot-session", "events.jsonl");
  writeJsonl(
    session,
    copilotEvents([
      {
        type: "system.message",
        data: {
          role: "system",
          content: "PRIVATE_SYSTEM_PROMPT",
        },
      },
      {
        type: "user.message",
        data: {
          content: "Please update /Users/alice/repo/src/index.ts.",
          transformedContent: "PRIVATE_TRANSFORMED_PROMPT",
        },
      },
      {
        type: "assistant.message",
        data: {
          content: "Updated ~/repo/src/index.ts.",
          reasoningOpaque: "PRIVATE_REASONING",
          encryptedContent: "PRIVATE_ENCRYPTED_CONTENT",
        },
      },
      {
        type: "hook.start",
        data: {
          content: "PRIVATE_HOOK_CONTENT",
        },
      },
      {
        type: "response_item",
        payload: {
          role: "assistant",
          content: "PRIVATE_GENERIC_RESPONSE_ITEM",
        },
      },
      {
        type: "assistant",
        content: "PRIVATE_GENERIC_ASSISTANT_ROW",
      },
      {
        type: "compacted",
        payload: {
          replacement_history: [
            {
              role: "assistant",
              content: "PRIVATE_COMPACTED_ROW",
            },
          ],
        },
      },
      {
        type: "tool.execution_start",
        data: {
          toolCallId: "tool-1",
          toolName: "view",
          arguments: {
            path: "/Users/alice/repo/src/index.ts",
          },
        },
      },
      {
        type: "tool.execution_complete",
        data: {
          toolCallId: "tool-1",
          success: true,
          result: "PRIVATE_TOOL_OUTPUT",
        },
      },
      {
        type: "external_tool.requested",
        data: {
          requestId: "tool-2",
          toolName: "powershell",
          arguments: {
            command: "Get-ChildItem",
          },
        },
      },
      {
        type: "external_tool.completed",
        data: {
          requestId: "tool-2",
        },
      },
    ]),
  );

  const output = run(["render", "--session", session]);

  assert.match(output, /<summary>Redacted copilot session transcript<\/summary>/);
  assert.match(output, /\[user\]\nPlease update \[LOCAL_PATH\]/);
  assert.match(output, /\[assistant\]\nUpdated \[HOME_PATH\]/);
  assert.match(output, /1 read, 1 execute; raw tool outputs dropped: 2/);
  assert.doesNotMatch(output, /PRIVATE_SYSTEM_PROMPT/);
  assert.doesNotMatch(output, /PRIVATE_TRANSFORMED_PROMPT/);
  assert.doesNotMatch(output, /PRIVATE_REASONING/);
  assert.doesNotMatch(output, /PRIVATE_ENCRYPTED_CONTENT/);
  assert.doesNotMatch(output, /PRIVATE_HOOK_CONTENT/);
  assert.doesNotMatch(output, /PRIVATE_GENERIC_RESPONSE_ITEM/);
  assert.doesNotMatch(output, /PRIVATE_GENERIC_ASSISTANT_ROW/);
  assert.doesNotMatch(output, /PRIVATE_COMPACTED_ROW/);
  assert.doesNotMatch(output, /PRIVATE_TOOL_OUTPUT/);
});

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

test("render preserves Codex event dialogue and tool summaries", () => {
  const dir = tempDir();
  const session = path.join(dir, "session.jsonl");
  writeJsonl(session, [
    {
      type: "event_msg",
      payload: {
        type: "user_message",
        message: "Existing user message",
      },
    },
    {
      type: "event_msg",
      payload: {
        type: "agent_message",
        message: "Existing assistant message",
      },
    },
    {
      type: "response_item",
      payload: {
        type: "function_call",
        name: "apply_patch",
        arguments: "{}",
      },
    },
    {
      type: "response_item",
      payload: {
        type: "function_call_output",
        output: "PRIVATE_EXISTING_TOOL_OUTPUT",
      },
    },
  ]);

  const output = run(["render", "--session", session]);

  assert.match(output, /<summary>Redacted codex session transcript<\/summary>/);
  assert.match(output, /\[user\]\nExisting user message/);
  assert.match(output, /\[assistant\]\nExisting assistant message/);
  assert.match(output, /1 write; raw tool outputs dropped: 1/);
  assert.doesNotMatch(output, /PRIVATE_EXISTING_TOOL_OUTPUT/);
});
