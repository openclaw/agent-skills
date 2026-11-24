import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const cli = fileURLToPath(new URL("./beam", import.meta.url));

for (const lostReceipt of [false, true]) {
  test(
    `installed hook uses the negotiated native skill protocol${lostReceipt ? " after lost acknowledgement" : ""}`,
    { skip: process.platform === "win32" },
    (t) => {
      const dir = fs.mkdtempSync(path.join(os.tmpdir(), "beam-skill-bridge-"));
      t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
      const sessionID = "22222222-2222-4333-8444-555555555555";
      const session = path.join(dir, sessionID + ".jsonl");
      fs.writeFileSync(
        session,
        JSON.stringify({
          type: "user",
          sessionId: sessionID,
          message: { role: "user", content: "Fix CSV import" },
        }) + "\n",
      );
      const capture = path.join(dir, "invocations");
      const exe = path.join(dir, "beam");
      fs.writeFileSync(
        exe,
        `#!/bin/sh
if [ "$1" = skill-v1 ] && [ "$2" = --protocol ]; then
  echo 1
  exit 0
fi
IFS= read -r request
printf '%s\\n' "$request" >> "$TEST_BEAM_CAPTURE"
if [ "$TEST_BEAM_LOST_RECEIPT" = yes ]; then
  echo "native receipt unavailable" >&2
  exit 1
fi
echo '{"ok":true}'
`,
        { mode: 0o700 },
      );
      const state = path.join(dir, "handoffs.sqlite");
      const result = spawnSync(
        process.execPath,
        [
          cli,
          "hook",
          "--quiet",
          "--endpoint",
          "http://127.0.0.1:1/api/v1/beam/sessions",
          "--state",
          state,
        ],
        {
          encoding: "utf8",
          env: {
            ...process.env,
            PATH: dir,
            TEST_BEAM_CAPTURE: capture,
            TEST_BEAM_LOST_RECEIPT: lostReceipt ? "yes" : "no",
          },
          input: JSON.stringify({
            hook_event_name: "Stop",
            transcript_path: session,
            session_id: sessionID,
          }),
        },
      );
      assert.equal(result.status, lostReceipt ? 1 : 0, result.stderr);
      assert.ok(fs.existsSync(capture), result.stderr);
      const lines = fs.readFileSync(capture, "utf8").trim().split("\n");
      assert.equal(lines.length, 1);
      const request = JSON.parse(lines[0]);
      assert.equal(request.operation, "share");
      assert.equal(request.hook, true);
      assert.equal(request.state, state);
      assert.equal(JSON.parse(request.packet).items[0].text, "Fix CSV import");
      assert.equal(result.stdout, "");
      if (lostReceipt) assert.match(result.stderr, /native receipt unavailable/);
      assert.equal(fs.existsSync(state), false);
    },
  );
}
