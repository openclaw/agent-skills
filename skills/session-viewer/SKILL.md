---
name: session-viewer
description: "Render Codex, Claude Code, OpenClaw, or Pi session JSONL transcripts as a searchable, shareable single-file HTML viewer."
---

# Session Viewer

Use when asked to view, export, inspect, or share a Codex, Claude Code, OpenClaw, or Pi session transcript in a browser.

## Commands

Resolve `SESSION_VIEWER_SKILL_DIR` to the directory containing this `SKILL.md`.
Use that installed source for commands, independent of the current repository.

When the session path is not known and the `agent-transcript` skill is available, use it first to find the likely JSONL session:
Resolve `TRANSCRIPT_SKILL_DIR` from that skill's actual installation before running:

```bash
"$TRANSCRIPT_SKILL_DIR/scripts/agent-transcript" find \
  --query "$USER_GOAL_OR_TITLE $BRANCH_OR_URL" \
  --cwd "$PWD" \
  --since-days 14
```

Pick the highest-confidence `file` result, then render it with `session-viewer`.

Render with the resolved installation:

```bash
node "$SESSION_VIEWER_SKILL_DIR/scripts/session-viewer.ts" <session.jsonl> --out /tmp/session.html --open
```

Useful modes:

```bash
node "$SESSION_VIEWER_SKILL_DIR/scripts/session-viewer.ts" <session.jsonl> --out session.html
node "$SESSION_VIEWER_SKILL_DIR/scripts/session-viewer.ts" <session.jsonl> --raw --out session.html
node "$SESSION_VIEWER_SKILL_DIR/scripts/session-viewer.ts" --blank --out viewer.html --open
```

Defaults:

- detects `codex`, `claude`, or `pi-openclaw`
- embeds normalized session data into one HTML file
- keeps tool input/output text in the DOM so browser search can find it
- reads the complete session file, preserving full history in both export modes
- `--raw` embeds the original JSONL and lets the browser parse it
- `--blank` creates a reusable file-picker viewer

For an explicitly partial export, use `--max-read-bytes N` with a positive integer byte limit (for example, `--max-read-bytes 8388608` for 8 MiB). Oversized files retain the head and tail, with a visible omission warning in the CLI and exported viewer. Truncated boundary records may be omitted; `--raw` embeds only the retained JSONL. Files at or below the limit remain complete. Short reads are retried; an unexpected end of file fails the export instead of reporting a complete read.

This opt-in read limit applies only to CLI file exports. The browser's file picker continues to load complete files.

## Where Sessions Live

Codex:

```bash
find "${CODEX_HOME:-$HOME/.codex}/sessions" -name 'rollout-*.jsonl' -type f | sort
ls -t "${CODEX_HOME:-$HOME/.codex}"/sessions/*/*/*/rollout-*.jsonl | head
```

Current OpenClaw stores session indexes and transcripts in per-agent SQLite databases.
Use native session discovery:

```bash
openclaw sessions --agent "<agentId>" --json
```

This lists sessions; it does not export a JSONL transcript.
The viewer requires a supported JSONL transcript, not a SQLite database or session-list JSON.
Use OpenClaw's native session view when no compatible JSONL export is available.
See the [OpenClaw sessions reference](https://docs.openclaw.ai/cli/sessions).

Legacy OpenClaw JSONL:

```bash
AGENT_ID="<agentId>"
SESSION_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}/agents/$AGENT_ID/sessions"
ls -t "$SESSION_DIR"/*.jsonl | head
find "${OPENCLAW_STATE_DIR:-$HOME/.openclaw}/agents" -path '*/sessions/*.jsonl' -type f | sort
```

Only legacy file stores use `sessions.json` beside those transcripts to map session keys to ids.
For standalone Pi, select its actual JSONL transcript rather than assuming the OpenClaw directory layout.

Claude Code:

```bash
find "$HOME/.claude/projects" -name '*.jsonl' -type f | sort
ls -t "$HOME/.claude/projects"/**/*.jsonl | head
```

Some Claude installs also keep exported JSON/JSONL under project-specific cache folders; prefer the newest JSONL with the target repo path in its parent folder.

## Development

Scripts are native Node TypeScript. Keep them erasable:

- ok: types, interfaces, unions, `satisfies`
- avoid: enums, namespaces, decorators, parameter properties
- no tsconfig path aliases; use relative imports

Importer ownership:

- `scripts/importers/codex.ts`: Codex rollout JSONL
- `scripts/importers/claude.ts`: Claude Code JSONL
- `scripts/importers/pi-openclaw.ts`: Pi/OpenClaw session JSONL

Validate:

```bash
npm ci --ignore-scripts
npm run typecheck
node --test skills/session-viewer/scripts/session-viewer.test.ts
scripts/validate-skills
```
