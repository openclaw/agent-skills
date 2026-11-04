---
name: beam
description: "Share a redacted coding session or hand its logical conversation to an authenticated OpenClaw Gateway."
---

# Beam

Use when the user explicitly asks to beam, publish, or share the current local coding session with an authenticated OpenClaw receiver.

## Contract

- Treat invoking this skill as approval for one snapshot upload to the named destination.
- Never upload raw JSONL, reasoning, system/developer prompts, tool output, environment values, credentials, browser state, cookies, or local paths.
- The helper is self-contained: it resolves and parses exact Claude Code or Codex transcripts, then uploads only locally redacted user/assistant messages and compact tool counts.
- Ordinary publishing shares a read-only snapshot. A separately requested `handoff` releases the source Beam identity and moves its logical conversation to Team. After handoff, use Beam's authenticated `read` and `continue` commands for subsequent work; do not resume independent source work or publish another transcript copy.
- Team owns one durable conversation after release. The source history imports once; reads, reconnects and continuations resolve that same conversation. Native provider runtime IDs need not survive. Do not connect a node, expose a terminal, transfer credentials or grant filesystem/tool access.
- Require HTTPS except for loopback development endpoints.
- Guests use their existing personal Cloudflare Access sign-in or `BEAM_ACCESS_TOKEN`; never request, share, or copy a Gateway token for guest uploads. `BEAM_AUTH_TOKEN` remains the ordinary operator Gateway-auth fallback, not a guest credential. Never print token values.
- Live synchronization is opt-in persistent behavior. Do not install hooks unless the user explicitly asks for live Beam updates.

## Snapshot

Set or obtain the destination receiver URL first:

```bash
export BEAM_ENDPOINT="https://gateway.example.com/api/v1/beam/sessions"
```

Prefer the harness-specific exact identifier. Resolve the directory containing this `SKILL.md` as `BEAM_SKILL_DIR` first.

Claude Code exposes the current session id:

```bash
node "$BEAM_SKILL_DIR/scripts/beam" publish \
  --endpoint "$BEAM_ENDPOINT" \
  --session-id "${CLAUDE_SESSION_ID}"
```

In Codex, resolve the directory containing this `SKILL.md` as `BEAM_SKILL_DIR`; normal shell-tool children expose the current thread id:

```bash
node "$BEAM_SKILL_DIR/scripts/beam" publish \
  --endpoint "$BEAM_ENDPOINT" \
  --thread-id "$CODEX_THREAD_ID"
```

Prefer exact harness metadata when available:

- Claude Code: `${CLAUDE_SESSION_ID}` identifies the current local conversation; the helper finds its transcript.
- Codex shell tools: `CODEX_THREAD_ID` identifies the current thread.
- Hook adapters: pass their JSON to `beam hook`; `transcript_path` is authoritative.
- Exact fallback: Beam scans only the native Claude/Codex session roots for the supplied id and fails closed on no match or ambiguity.

Useful options:

```bash
node "$BEAM_SKILL_DIR/scripts/beam" publish --endpoint "$BEAM_ENDPOINT" --session /path/to/session.jsonl
node "$BEAM_SKILL_DIR/scripts/beam" publish --endpoint "$BEAM_ENDPOINT" --thread-id "$CODEX_THREAD_ID"
node "$BEAM_SKILL_DIR/scripts/beam" publish --endpoint "$BEAM_ENDPOINT" --title "Fix upload flow"
node "$BEAM_SKILL_DIR/scripts/beam" publish --endpoint "$BEAM_ENDPOINT" --complete
node "$BEAM_SKILL_DIR/scripts/beam" publish --endpoint "$BEAM_ENDPOINT" --dry-run
```

`--dry-run` prints the sanitized payload locally and performs no network request.

On success, return only the Beam URL and a short disclosure summary: source harness, shared message count, whether older entries were truncated, and whether the beam is complete. The URL uses the endpoint-derived Control UI base path followed by `/beam/<title-slug>-<id-prefix>`, for example `https://gateway.example.com/beam/fix-upload-flow-0123456789ab`. The title comes from `--title` or the first shared user message. The stable ID suffix identifies the session; links with an earlier title remain valid.

If the receipt includes `canView: false`, say that the upload succeeded and the link is for authorized Team operators; upload-only access does not let the guest open it. Do not present it as a guest-viewable link. Staff and older receipts may omit `canView`; omission is not a new access grant.

Guest access requires receiver-side support and operator authorization. Sender support alone does not mean it is deployed.
Current Visitor-enabled receivers let active verified publishers create, refresh, list, and read only their own snapshots.
They grant no shared-catalog access or deletion. Updated receivers allow authorized continuation of a publisher's own explicitly released Beam, subject to normal destination creation, model, account and session permissions. Older upload-only receivers can return `canView: false`; honor that receipt.
Guests need no shared secret. If personal access expires, sign in again outside hooks or refresh the personal `BEAM_ACCESS_TOKEN`.
Revoked access needs an authorized operator to restore it. Never blindly retry an uncertain upload.

## Live logical handoff

Only perform this when the user asks to move or continue the conversation in Team; permission to share a snapshot alone is insufficient. Requires Node 22.13+ and an updated receiver.

```sh
node "$BEAM_SKILL_DIR/scripts/beam" handoff --endpoint "$BEAM_ENDPOINT" --thread-id "$CODEX_THREAD_ID"
node "$BEAM_SKILL_DIR/scripts/beam" read --endpoint "$BEAM_ENDPOINT" --beam-id BEAM_ID --profile-dir /path/to/own/remote-profile
node "$BEAM_SKILL_DIR/scripts/beam" continue --endpoint "$BEAM_ENDPOINT" --beam-id BEAM_ID --profile-dir /path/to/own/remote-profile --message "Continue the work"
```

Use `--session-id` for Claude Code. The handoff receipt prints `BEAM_ID`. `--profile-dir` selects an existing normal OpenClaw remote profile for that exact Gateway; configure your own authentication first. No shared account or provider token is requested or copied. Permission or runtime denial stays a denial.

The helper durably retires this source identity before network dispatch. A pending handoff stays retired after errors; recover with `handoff --endpoint "$BEAM_ENDPOINT" --beam-id BEAM_ID`, including when the source transcript is gone. Never delete the retirement record to retry. Snapshot expiry or archive cannot restore source ownership. A `read` with no destination returns a visible pending result and creates nothing; `continue` creates the destination once. Deleted or reset destinations require reconciliation, not a new transcript copy.

Source model/version metadata is normalized against models available and permitted at Team. If unavailable, the destination's configured default resolves normally; authentication/setup requirements remain in force. The original local harness is not stopped or remotely controlled. Local turns after handoff are not canonical Team turns.

Continuation returns the Gateway's normal run acknowledgment. Keep the printed request ID: after an uncertain send, retry the same message with `--request-id ID` to avoid a duplicate turn. `read` obtains the current Team history. The local SQLite record contains only sanitized pending history and ownership metadata; acknowledged history is discarded locally. Default location: the user's `.local/state/openclaw-beam/handoffs.sqlite`; `--state FILE` selects an explicit local store. Preserve it while the handed-off identity can be used.

The helper also accepts bare `/beam/<id-prefix>` links and, during rollout, the current server's exact `/chat/<agent>?catalog=beam&host=gateway&thread=<full-beam-id>` response. It still rejects the obsolete `?session=catalog:...` beta form.

## Live Hooks

The helper accepts the snake_case JSON emitted by both Claude Code and Codex lifecycle hooks:

```bash
node "$BEAM_SKILL_DIR/scripts/beam" hook --endpoint "$BEAM_ENDPOINT" --quiet
```

Configure root `Stop` hooks for turn-by-turn updates. Claude Code can also use `SessionEnd` for finalization; Codex finalization uses an explicit `publish --complete`. See:

- `references/claude-code-hooks.json`
- `references/codex-hooks.toml`

Hook failures must not block the coding session. Keep ordinary success quiet (including upload-only receipts); a retired Beam emits a concise direction to read/continue through Team even with `--quiet`. Log one concise redacted error on failure. Hooks never start interactive authentication or automatically hand off ownership.

Full installation, authentication, data-boundary, and hook documentation:
[`README.md`](README.md).

## Development

```bash
node --check skills/beam/scripts/beam
node --check skills/beam/scripts/beam-session.js
node --check skills/beam/scripts/beam-handoff.js
node --test skills/beam/scripts/beam.test.mjs skills/beam/scripts/beam-handoff.test.mjs
scripts/validate-skills
```
