# Beam

Beam publishes a sanitized local Claude Code or Codex session to an authenticated
OpenClaw Gateway. The Gateway shows the result in its existing external-session
viewer; it never gains access to the source machine's filesystem, terminal,
tools, credentials, or node runtime.

## How it works

The `beam` helper is self-contained. It does not require `agent-transcript`,
`session-viewer`, an SDK, or another installed skill.

1. It resolves one exact transcript:
   - Claude Code: `${CLAUDE_CONFIG_DIR:-~/.claude}/projects/**/<session-id>.jsonl`
   - Codex: `${CODEX_HOME:-~/.codex}/{sessions,archived_sessions}/**/*.jsonl`,
     verified against `session_meta.payload.id`
   - lifecycle hooks: their exact `transcript_path`
   - explicit use: `--session <file>`
2. It reads a bounded transcript window and recognizes visible Claude Code and
   Codex messages, including modern Codex `item_completed` records.
3. It drops system/developer setup, reasoning, raw tool inputs/outputs, images,
   browser state, and unknown records. Tool activity becomes aggregate family
   counts such as `2 read, 1 execute`.
4. It strips internal hook wrappers and redacts credentials, auth headers,
   private keys, email addresses, phone numbers, secret query parameters, and
   broad local paths.
5. It uploads a closed, size-bounded JSON payload. The receiver is expected to
   expose it as a passive catalog, not a resumable session.

Beam refuses fuzzy discovery. If an exact session cannot be resolved or multiple
exact candidates exist, publication stops without choosing the newest nearby
session.

## Install

Install only Beam from the canonical skills checkout:

```sh
scripts/install-skills beam
```

A copied installation is also standalone:

```sh
scripts/install-skills --mode copy --target ~/.agents/skills beam
```

## Publish a snapshot

Set the installed skill directory and receiver endpoint:

```sh
export BEAM_SKILL_DIR="${AGENTS_HOME:-$HOME/.agents}/skills/beam"
export BEAM_ENDPOINT="https://gateway.example.com/api/v1/beam/sessions"
```

Claude Code:

```sh
node "$BEAM_SKILL_DIR/scripts/beam" publish \
  --endpoint "$BEAM_ENDPOINT" \
  --session-id "$CLAUDE_SESSION_ID"
```

Codex:

```sh
node "$BEAM_SKILL_DIR/scripts/beam" publish \
  --endpoint "$BEAM_ENDPOINT" \
  --thread-id "$CODEX_THREAD_ID"
```

Explicit transcript:

```sh
node "$BEAM_SKILL_DIR/scripts/beam" publish \
  --endpoint "$BEAM_ENDPOINT" \
  --session /path/to/session.jsonl
```

Inspect the exact sanitized payload without networking:

```sh
node "$BEAM_SKILL_DIR/scripts/beam" publish \
  --endpoint http://127.0.0.1:9/api/v1/beam/sessions \
  --session /path/to/session.jsonl \
  --dry-run --quiet
```

## Authentication

For ordinary Gateway token or password authentication:

```sh
export BEAM_AUTH_TOKEN="..."
```

For a Cloudflare Access application token:

```sh
export BEAM_ACCESS_TOKEN="..."
```

For an interactive snapshot, Beam can ask the installed `cloudflared` CLI for
an application token. Browser authentication stays between Cloudflare and the
configured identity provider; Beam does not receive a GitHub token.

Lifecycle hooks never start interactive authentication. Configure one of the
token variables before enabling live hooks.

## Live updates

Beam accepts the snake_case JSON emitted on stdin by Claude Code and Codex
`Stop`, `SessionEnd`, and `SubagentStop` command hooks:

```sh
node "$BEAM_SKILL_DIR/scripts/beam" hook \
  --endpoint "$BEAM_ENDPOINT" \
  --quiet
```

Templates:

- [`references/claude-code-hooks.json`](references/claude-code-hooks.json)
- [`references/codex-hooks.toml`](references/codex-hooks.toml)

`Stop` refreshes the snapshot after a completed turn. `SessionEnd` marks it
complete. Hook failures exit nonzero but do not emit a blocking hook decision.

## Receiver contract

The OpenClaw Beam plugin accepts `POST /api/v1/beam/sessions` through normal
Gateway HTTP authentication. Uploads require `operator.write` or
`operator.admin`. Every `operator.read` client on that Gateway can view the
catalog, so a separate Gateway remains the isolation boundary between teams.

The catalog has no continue, archive, terminal, tool, or node capability.

OpenClaw plugin documentation:
https://docs.openclaw.ai/plugins/beam

## Development

```sh
node --check skills/beam/scripts/beam
node --check skills/beam/scripts/beam-session.js
node --test skills/beam/scripts/beam.test.mjs
python scripts/validate-skills
```
