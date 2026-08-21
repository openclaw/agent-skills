import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { promisify } from "node:util";
import { parseSessionDocument } from "./core/detect.ts";
import { parseJsonl } from "./core/jsonl.ts";
import { resolveOpenBrowserCommand } from "./open-browser.ts";

const execFileAsync = promisify(execFile);

function parse(text: string) {
  const { records } = parseJsonl(text);
  return parseSessionDocument(records, "fixture.jsonl");
}

test("opens hostile Windows paths without a command shell", () => {
  for (const filePath of [
    "C:\\Reports\\session & calc.exe.html",
    "C:\\Reports\\session | whoami.html",
    "C:\\Reports\\%COMSPEC%.html",
    "C:\\Reports\\session ^& echo injected.html",
  ]) {
    assert.deepEqual(resolveOpenBrowserCommand("win32", filePath), {
      executable: "explorer.exe",
      args: [filePath],
    });
  }
});

test("parses Codex rollout tool calls and outputs", () => {
  const doc = parse(
    [
      JSON.stringify({
        timestamp: "2026-05-25T10:00:00Z",
        type: "session_meta",
        payload: { id: "codex-session", cwd: "/tmp/project" },
      }),
      JSON.stringify({
        timestamp: "2026-05-25T10:00:01Z",
        type: "response_item",
        payload: {
          type: "message",
          role: "assistant",
          content: [{ type: "output_text", text: "hello" }],
        },
      }),
      JSON.stringify({
        timestamp: "2026-05-25T10:00:02Z",
        type: "response_item",
        payload: {
          type: "function_call",
          name: "functions.exec_command",
          call_id: "call-1",
          arguments: JSON.stringify({ cmd: "pwd" }),
        },
      }),
      JSON.stringify({
        timestamp: "2026-05-25T10:00:03Z",
        type: "response_item",
        payload: {
          type: "function_call_output",
          call_id: "call-1",
          output: "Process exited with code 0\nOutput:\n/tmp/project",
        },
      }),
    ].join("\n"),
  );
  assert.equal(doc.format, "codex");
  assert.equal(
    doc.events.some((event) => event.kind === "tool_call"),
    true,
  );
  assert.equal(
    doc.events.some((event) => event.kind === "tool_result" && event.status === "ok"),
    true,
  );
});

test("hides encrypted Codex reasoning items", () => {
  const doc = parse(
    [
      JSON.stringify({
        timestamp: "2026-05-25T10:00:00Z",
        type: "session_meta",
        payload: { id: "codex-session" },
      }),
      JSON.stringify({
        timestamp: "2026-05-25T10:00:01Z",
        type: "response_item",
        payload: {
          type: "reasoning",
          id: "rs_1",
          encrypted_content: "gAAAAABhidden",
          summary: [],
        },
      }),
      JSON.stringify({
        timestamp: "2026-05-25T10:00:02Z",
        type: "response_item",
        payload: {
          type: "message",
          role: "assistant",
          content: [{ type: "output_text", text: "visible" }],
        },
      }),
    ].join("\n"),
  );
  assert.equal(
    doc.events.some((event) => event.kind === "reasoning"),
    false,
  );
  assert.equal(
    doc.events
      .map((event) => event.text)
      .join("\n")
      .includes("encrypted"),
    false,
  );
});

test("collapses Codex turn-aborted markers into one concise event", () => {
  const doc = parse(
    [
      JSON.stringify({
        timestamp: "2026-05-25T10:00:00Z",
        type: "session_meta",
        payload: { id: "codex-session" },
      }),
      JSON.stringify({
        timestamp: "2026-05-25T10:00:01Z",
        type: "response_item",
        payload: {
          type: "message",
          role: "user",
          content: [
            {
              type: "input_text",
              text: [
                "<turn_aborted>",
                "The user interrupted the previous turn on purpose. Any running unified exec processes may still be running in the background.",
                "</turn_aborted>",
              ].join("\n"),
            },
          ],
        },
      }),
      JSON.stringify({
        timestamp: "2026-05-25T10:00:02Z",
        type: "event_msg",
        payload: {
          type: "turn_aborted",
          reason: "interrupted",
          duration_ms: 277039,
        },
      }),
    ].join("\n"),
  );
  assert.equal(doc.events.filter((event) => event.title === "Turn aborted").length, 1);
  assert.equal(
    doc.events.some((event) => event.kind === "message"),
    false,
  );
  assert.equal(doc.events[0]?.text, "Turn aborted by user.");
});

test("keeps Codex turn-aborted-shaped messages without event rows", () => {
  const marker = "<turn_aborted>\nExample only.\n</turn_aborted>";
  const doc = parse(
    [
      JSON.stringify({
        timestamp: "2026-05-25T10:00:00Z",
        type: "session_meta",
        payload: { id: "codex-session" },
      }),
      JSON.stringify({
        timestamp: "2026-05-25T10:00:01Z",
        type: "response_item",
        payload: {
          type: "message",
          role: "user",
          content: [{ type: "input_text", text: marker }],
        },
      }),
    ].join("\n"),
  );
  assert.equal(doc.events.length, 1);
  assert.equal(doc.events[0]?.kind, "message");
  assert.equal(doc.events[0]?.text, marker);
});

test("collapses memory citations into memory notes", () => {
  const citation = [
    "<oai-mem-citation>",
    "<citation_entries>",
    "MEMORY.md:89-97|note=[checked prior transcript-import context]",
    "</citation_entries>",
    "<rollout_ids>",
    "019e5515-7528-7393-80a4-d7a70dcb8e37",
    "</rollout_ids>",
    "</oai-mem-citation>",
  ].join("\n");
  const doc = parse(
    [
      JSON.stringify({
        timestamp: "2026-05-25T10:00:00Z",
        type: "session_meta",
        payload: { id: "codex-session" },
      }),
      JSON.stringify({
        timestamp: "2026-05-25T10:00:01Z",
        type: "response_item",
        payload: {
          type: "message",
          role: "assistant",
          content: [{ type: "output_text", text: `Done.\n\n${citation}` }],
        },
      }),
    ].join("\n"),
  );
  assert.equal(doc.events.length, 2);
  assert.equal(doc.events[0]?.kind, "message");
  assert.equal(doc.events[0]?.text, "Done.");
  assert.equal(doc.events[1]?.kind, "memory");
  assert.equal(doc.events[1]?.title, "Memory note");
  assert.equal(doc.events[1]?.text.includes("<oai-mem-citation>"), true);
});

test("keeps quoted memory citation examples in transcript text", () => {
  const citation = "<oai-mem-citation>example</oai-mem-citation>";
  const doc = parse(
    [
      JSON.stringify({
        timestamp: "2026-05-25T10:00:00Z",
        type: "session_meta",
        payload: { id: "codex-session" },
      }),
      JSON.stringify({
        timestamp: "2026-05-25T10:00:01Z",
        type: "response_item",
        payload: {
          type: "message",
          role: "user",
          content: [{ type: "input_text", text: `Please render ${citation} literally.` }],
        },
      }),
    ].join("\n"),
  );
  assert.equal(doc.events.length, 1);
  assert.equal(doc.events[0]?.kind, "message");
  assert.equal(doc.events[0]?.text.includes(citation), true);
});

test("only splits trailing memory citation footers", () => {
  const quoted = "<oai-mem-citation>quoted</oai-mem-citation>";
  const footer = "<oai-mem-citation>footer</oai-mem-citation>";
  const doc = parse(
    [
      JSON.stringify({
        timestamp: "2026-05-25T10:00:00Z",
        type: "session_meta",
        payload: { id: "codex-session" },
      }),
      JSON.stringify({
        timestamp: "2026-05-25T10:00:01Z",
        type: "response_item",
        payload: {
          type: "message",
          role: "assistant",
          content: [
            { type: "output_text", text: `Quoted example: ${quoted}\n\nDone.\n\n${footer}` },
          ],
        },
      }),
    ].join("\n"),
  );
  assert.equal(doc.events.length, 2);
  assert.equal(doc.events[0]?.text.includes(quoted), true);
  assert.equal(doc.events[0]?.text.includes(footer), false);
  assert.equal(doc.events[1]?.kind, "memory");
  assert.equal(doc.events[1]?.text, footer);
});

test("renders Codex image blocks as message attachments", () => {
  const image = "data:image/png;base64,iVBORw0KGgo=";
  const doc = parse(
    [
      JSON.stringify({
        timestamp: "2026-05-25T10:00:00Z",
        type: "session_meta",
        payload: { id: "codex-session" },
      }),
      JSON.stringify({
        timestamp: "2026-05-25T10:00:01Z",
        type: "response_item",
        payload: {
          type: "message",
          role: "user",
          content: [
            { type: "input_text", text: "<image name=[Image #1]>" },
            { type: "input_image", image_url: { url: image }, detail: "high" },
            { type: "input_text", text: "</image>" },
            { type: "input_text", text: "[Image #1] can we show the image?" },
          ],
        },
      }),
    ].join("\n"),
  );
  const event = doc.events.find((item) => item.kind === "message");
  assert.equal(event?.text, "can we show the image?");
  assert.equal(event?.images?.length, 1);
  assert.equal(event?.images?.[0]?.src, image);
  assert.equal(event?.images?.[0]?.detail, "high");
});

test("keeps literal image tags when no image block exists", () => {
  const doc = parse(
    [
      JSON.stringify({
        timestamp: "2026-05-25T10:00:00Z",
        type: "session_meta",
        payload: { id: "codex-session" },
      }),
      JSON.stringify({
        timestamp: "2026-05-25T10:00:01Z",
        type: "response_item",
        payload: {
          type: "message",
          role: "assistant",
          content: [{ type: "output_text", text: 'Use <image href="x.png"></image> in XML.' }],
        },
      }),
    ].join("\n"),
  );
  assert.equal(
    doc.events.find((item) => item.kind === "message")?.text,
    'Use <image href="x.png"></image> in XML.',
  );
});

test("keeps literal image tags beside image attachments", () => {
  const image = "data:image/png;base64,iVBORw0KGgo=";
  const doc = parse(
    [
      JSON.stringify({
        timestamp: "2026-05-25T10:00:00Z",
        type: "session_meta",
        payload: { id: "codex-session" },
      }),
      JSON.stringify({
        timestamp: "2026-05-25T10:00:01Z",
        type: "response_item",
        payload: {
          type: "message",
          role: "user",
          content: [
            { type: "input_image", image_url: image },
            { type: "input_text", text: 'Use <image href="x.png"></image> in XML.' },
          ],
        },
      }),
    ].join("\n"),
  );
  const event = doc.events.find((item) => item.kind === "message");
  assert.equal(event?.text, 'Use <image href="x.png"></image> in XML.');
  assert.equal(event?.images?.[0]?.src, image);
});

test("parses Claude Code tool use and result blocks", () => {
  const doc = parse(
    [
      JSON.stringify({ type: "summary", summary: "Fix parser" }),
      JSON.stringify({
        type: "assistant",
        timestamp: "2026-05-25T10:00:00Z",
        message: {
          role: "assistant",
          content: [
            { type: "text", text: "running ls" },
            { type: "tool_use", id: "toolu-1", name: "Bash", input: { command: "ls" } },
          ],
        },
      }),
      JSON.stringify({
        type: "user",
        timestamp: "2026-05-25T10:00:01Z",
        message: {
          role: "user",
          content: [{ type: "tool_result", tool_use_id: "toolu-1", content: "ok" }],
        },
      }),
    ].join("\n"),
  );
  assert.equal(doc.format, "claude");
  assert.equal(doc.title, "Fix parser");
  assert.equal(doc.events.filter((event) => event.kind === "tool_call").length, 1);
  assert.equal(doc.events.filter((event) => event.kind === "tool_result").length, 1);
});

test("keeps Claude thinking content blocks", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "assistant",
        timestamp: "2026-05-25T10:00:00Z",
        message: {
          role: "assistant",
          content: [{ type: "thinking", content: "visible thinking" }],
        },
      }),
    ].join("\n"),
  );
  assert.equal(doc.format, "claude");
  assert.equal(doc.events.filter((event) => event.kind === "reasoning").length, 1);
  assert.equal(doc.events.find((event) => event.kind === "reasoning")?.text, "visible thinking");
});

test("parses Pi/OpenClaw message and tool result entries", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "session",
        id: "openclaw-session",
        timestamp: "2026-05-25T10:00:00Z",
      }),
      JSON.stringify({
        type: "message",
        id: "m1",
        message: {
          role: "assistant",
          content: [
            { type: "text", text: "I will check." },
            { type: "toolCall", id: "call-1", name: "read", arguments: { path: "a.ts" } },
          ],
        },
      }),
      JSON.stringify({
        type: "message",
        id: "m2",
        message: {
          role: "toolResult",
          toolCallId: "call-1",
          toolName: "read",
          content: [{ type: "text", text: "contents" }],
        },
      }),
    ].join("\n"),
  );
  assert.equal(doc.format, "pi-openclaw");
  assert.equal(
    doc.events.some((event) => event.kind === "message" && event.text.includes("check")),
    true,
  );
  assert.equal(
    doc.events.some((event) => event.kind === "tool_call"),
    true,
  );
  assert.equal(
    doc.events.some((event) => event.kind === "tool_result"),
    true,
  );
});

test("keeps Pi/OpenClaw numeric message timestamps", () => {
  const doc = parse(
    JSON.stringify({
      type: "message",
      id: "m1",
      message: { role: "assistant", timestamp: 1748165000000, content: [{ type: "text", text: "ok" }] },
    }),
  );
  assert.equal(doc.format, "pi-openclaw");
  assert.equal(doc.events[0]?.timestamp, "2025-05-25T09:23:20.000Z");
});

test("drops out-of-range Pi/OpenClaw numeric message timestamps", () => {
  for (const timestamp of [1e300, Number.NaN, Number.POSITIVE_INFINITY, -8.64e15 - 1]) {
    const doc = parse(
      JSON.stringify({
        type: "message",
        id: "m1",
        message: { role: "assistant", timestamp, content: [{ type: "text", text: "ok" }] },
      }),
    );
    assert.equal(doc.format, "pi-openclaw");
    assert.equal(doc.events.length, 1);
    assert.equal(doc.events[0]?.timestamp, undefined);
  }
});

test("parses Pi/OpenClaw direct image data blocks", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "session",
        id: "openclaw-session",
      }),
      JSON.stringify({
        type: "message",
        id: "m1",
        message: {
          role: "user",
          content: [
            { type: "image", data: "iVBORw0KGgo=", mimeType: "image/png" },
            { type: "text", text: "screenshot" },
          ],
        },
      }),
    ].join("\n"),
  );
  const event = doc.events.find((item) => item.kind === "message");
  assert.equal(event?.text, "screenshot");
  assert.equal(event?.images?.[0]?.src, "data:image/png;base64,iVBORw0KGgo=");
});

test("keeps Pi/OpenClaw relative media URL image-only turns", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "session",
        id: "openclaw-session",
      }),
      JSON.stringify({
        type: "message",
        id: "m1",
        message: {
          role: "user",
          content: [{ type: "image", url: "/api/chat/media/image-1.png" }],
        },
      }),
    ].join("\n"),
  );
  const event = doc.events.find((item) => item.kind === "message");
  assert.equal(event?.text, "");
  assert.equal(event?.images?.[0]?.src, "/api/chat/media/image-1.png");
});

test("keeps Pi/OpenClaw protocol-relative media URL image-only turns", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "session",
        id: "openclaw-session",
      }),
      JSON.stringify({
        type: "message",
        id: "m1",
        message: {
          role: "user",
          content: [{ type: "image", url: "//cdn.example.test/photo.webp" }],
        },
      }),
    ].join("\n"),
  );
  const event = doc.events.find((item) => item.kind === "message");
  assert.equal(event?.text, "");
  assert.equal(event?.images?.[0]?.src, "//cdn.example.test/photo.webp");
});

test("keeps Pi/OpenClaw bare relative media path image-only turns", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "session",
        id: "openclaw-session",
      }),
      JSON.stringify({
        type: "message",
        id: "m1",
        message: {
          role: "user",
          content: [{ type: "image", url: "media/inbound/photo.png" }],
        },
      }),
    ].join("\n"),
  );
  const event = doc.events.find((item) => item.kind === "message");
  assert.equal(event?.text, "");
  assert.equal(event?.images?.[0]?.src, "media/inbound/photo.png");
});

test("rejects active-scheme image URLs", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "session",
        id: "openclaw-session",
      }),
      JSON.stringify({
        type: "message",
        id: "m1",
        message: {
          role: "user",
          content: [{ type: "image", url: "javascript:alert(1).png" }],
        },
      }),
    ].join("\n"),
  );
  assert.equal(doc.events.length, 0);
});

test("keeps Pi/OpenClaw message-level media path image-only turns", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "session",
        id: "openclaw-session",
      }),
      JSON.stringify({
        type: "message",
        id: "m1",
        message: {
          role: "user",
          content: "",
          MediaPaths: ["/tmp/a.png"],
          MediaTypes: ["image/png"],
        },
      }),
    ].join("\n"),
  );
  const event = doc.events.find((item) => item.kind === "message");
  assert.equal(event?.text, "");
  assert.equal(event?.images?.[0]?.src, "/tmp/a.png");
});

test("keeps Pi/OpenClaw message-level media URL image-only turns", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "session",
        id: "openclaw-session",
      }),
      JSON.stringify({
        type: "message",
        id: "m1",
        message: {
          role: "user",
          content: "",
          MediaUrls: ["https://example.com/photo.png"],
          MediaUrl: "https://example.com/photo.png",
          MediaTypes: ["image/png"],
        },
      }),
    ].join("\n"),
  );
  const event = doc.events.find((item) => item.kind === "message");
  assert.equal(event?.text, "");
  assert.equal(event?.images?.length, 1);
  assert.equal(event?.images?.[0]?.src, "https://example.com/photo.png");
});

test("keeps Pi/OpenClaw media refs aligned with media types", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "session",
        id: "openclaw-session",
      }),
      JSON.stringify({
        type: "message",
        id: "m1",
        message: {
          role: "user",
          content: "",
          MediaPaths: ["", "/tmp/photo.png"],
          MediaUrls: ["https://cdn.example/audio.mp3", "/tmp/photo.png"],
          MediaTypes: ["audio/mpeg", "image/png"],
        },
      }),
    ].join("\n"),
  );
  const event = doc.events.find((item) => item.kind === "message");
  assert.equal(event?.images?.length, 1);
  assert.equal(event?.images?.[0]?.src, "/tmp/photo.png");
  assert.equal(event?.images?.[0]?.detail, "image/png");
});

test("does not apply shifted Pi/OpenClaw media types to earlier refs", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "session",
        id: "openclaw-session",
      }),
      JSON.stringify({
        type: "message",
        id: "m1",
        message: {
          role: "user",
          content: "",
          MediaPaths: ["audio.bin", "photo.bin"],
          MediaTypes: ["image/png"],
        },
      }),
    ].join("\n"),
  );
  assert.equal(doc.events.length, 0);
});

test("rejects active-scheme Pi/OpenClaw message-level media refs", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "session",
        id: "openclaw-session",
      }),
      JSON.stringify({
        type: "message",
        id: "m1",
        message: {
          role: "user",
          content: "",
          MediaPath: "javascript:alert(1).png",
          MediaType: "image/png",
        },
      }),
    ].join("\n"),
  );
  assert.equal(doc.events.length, 0);
});

test("keeps Windows Pi/OpenClaw message-level image paths", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "session",
        id: "openclaw-session",
      }),
      JSON.stringify({
        type: "message",
        id: "m1",
        message: {
          role: "user",
          content: "",
          MediaPath: "C:\\OpenClaw QA\\photo.png",
          MediaType: "image/png",
        },
      }),
    ].join("\n"),
  );
  const event = doc.events.find((item) => item.kind === "message");
  assert.equal(event?.images?.[0]?.src, "C:\\OpenClaw QA\\photo.png");
});

test("parses Pi/OpenClaw tool result image blocks", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "session",
        id: "openclaw-session",
      }),
      JSON.stringify({
        type: "message",
        id: "m1",
        message: {
          role: "toolResult",
          toolCallId: "call-1",
          content: [
            { type: "image", data: "iVBORw0KGgo=", mimeType: "image/png" },
            { type: "text", text: "generated" },
          ],
        },
      }),
    ].join("\n"),
  );
  const event = doc.events.find((item) => item.kind === "tool_result");
  assert.equal(event?.text, "generated");
  assert.equal(event?.images?.[0]?.src, "data:image/png;base64,iVBORw0KGgo=");
});

test("keeps visible Pi/OpenClaw thinking blocks", () => {
  const doc = parse(
    [
      JSON.stringify({
        type: "session",
        id: "openclaw-session",
      }),
      JSON.stringify({
        type: "message",
        id: "m1",
        message: {
          role: "assistant",
          content: [{ type: "thinking", thinking: "visible reasoning" }],
        },
      }),
    ].join("\n"),
  );
  assert.equal(doc.format, "pi-openclaw");
  assert.equal(doc.events.filter((event) => event.kind === "reasoning").length, 1);
  assert.equal(doc.events.find((event) => event.kind === "reasoning")?.text, "visible reasoning");
});

test("CLI writes a one-file HTML export", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "session-viewer-"));
  const input = path.join(dir, "session.jsonl");
  const output = path.join(dir, "session.html");
  await fs.writeFile(
    input,
    JSON.stringify({
      timestamp: "2026-05-25T10:00:00Z",
      type: "session_meta",
      payload: { id: "codex-session", cwd: dir },
    }) +
      "\n" +
      JSON.stringify({
        timestamp: "2026-05-25T10:00:01Z",
        type: "response_item",
        payload: {
          type: "message",
          role: "assistant",
          content: [{ type: "output_text", text: "exported" }],
        },
      }) +
      "\n",
    "utf8",
  );
  await execFileAsync(process.execPath, [
    "skills/session-viewer/scripts/session-viewer.ts",
    input,
    "--out",
    output,
  ]);
  const html = await fs.readFile(output, "utf8");
  assert.match(html, /Session Viewer/);
  assert.match(html, /viewer-payload/);
  const payload = /<script id="viewer-payload" type="application\/json">([^<]*)<\/script>/u.exec(
    html,
  )?.[1];
  assert.ok(payload);
  assert.equal(JSON.parse(payload).kind, "normalized");
});
