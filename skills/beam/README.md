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
5. It uploads a closed, size-bounded JSON payload. The receiver exposes a passive
   transcript projection, not remote access to the local coding session.

Beam refuses fuzzy discovery. If an exact session cannot be resolved or multiple
exact candidates exist, publication stops without choosing the newest nearby
session. Discovery permits up to 20,000 JSONL files across the native roots;
non-session files and empty directories do not consume that budget. Reads retry
short filesystem results and stop publication on unexpected EOF, so an incomplete
read cannot be uploaded as a complete snapshot.

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

On success, Beam prints the endpoint-derived Control UI URL in its short share
form, for example:

```text
Beamed session: https://gateway.example.com/beam/fix-upload-flow-0123456789ab
```

When a receiver returns `canView: false`, the upload still succeeded, but Beam
instead prints:

```text
Beam upload succeeded: https://gateway.example.com/beam/fix-upload-flow-0123456789ab
This link is for authorized Team operators; upload-only access does not let you open it.
```

Share that link with the authorized Team operator for the handoff; do not promise
the guest can view it. Staff and older receipts may omit `canView`; the helper
preserves their existing output without treating omission as a new access grant.

A Gateway mounted below a base path returns that same base path, such as
`https://gateway.example.com/openclaw/beam/fix-upload-flow-0123456789ab`.

The Gateway builds the optional title slug from the redacted `--title` value or
the first shared user message. It contains up to 48 lowercase alphanumeric
characters and hyphens. The final 12–32 lowercase hex characters identify the
session independently of its title, so earlier named links still work after a
rename. Bare `/beam/<id-prefix>` links remain accepted.

Explicit transcript:

```sh
node "$BEAM_SKILL_DIR/scripts/beam" publish \
  --endpoint "$BEAM_ENDPOINT" \
  --session /path/to/session.jsonl \
  --title "Fix upload flow"
```

Inspect the exact sanitized payload without networking:

```sh
node "$BEAM_SKILL_DIR/scripts/beam" publish \
  --endpoint http://127.0.0.1:9/api/v1/beam/sessions \
  --session /path/to/session.jsonl \
  --dry-run --quiet
```

## Authentication

### Personal guest access

Restricted guest uploads require receiver-side support and explicit operator
authorization. This sender support does **not** announce deployed guest access.
Once enabled, guests use their existing personal Cloudflare Access sign-in or a
personal application token:

```sh
export BEAM_ACCESS_TOKEN="..."
```

For an interactive snapshot, Beam can ask the installed `cloudflared` CLI for
an application token, using a cached sign-in or opening browser login when needed.
Browser authentication stays between Cloudflare and the configured identity
provider; Beam does not receive a GitHub token. Use only the receiver endpoint
provided by the authorized operator.

Guests need no shared secret. Do not distribute or request a shared Gateway
token, password, or another person's Access token for guest uploads.
Current Visitor-enabled receivers let active verified publishers create, refresh,
list, and read their own snapshots. These routes grant no access to other
publishers' snapshots or permission to delete or continue sessions.
Older upload-only receivers can return `canView: false`; honor that restriction.

Expired Access credentials can cause authentication failure. Sign in again outside
hooks (for example, `cloudflared access login https://gateway.example.com` for the
configured application), or replace the expired personal `BEAM_ACCESS_TOKEN`.
If access was revoked, reauthentication does not restore permission: an authorized
operator must restore it. Do not work around a denial with a shared Gateway token.
Beam does not automatically retry uploads. After a timeout or uncertain response,
ask the operator to confirm receipt before trying again.

### Ordinary operator access

Existing Gateway token or password authentication remains available to operators:

```sh
export BEAM_AUTH_TOKEN="..."
```

`BEAM_ACCESS_TOKEN` takes precedence over `BEAM_AUTH_TOKEN`. The bearer fallback
is not a guest onboarding mechanism.

Lifecycle hooks never start interactive authentication. Configure one of the
appropriate personal/operator token variables before enabling live hooks; expired
or revoked access yields a concise error rather than browser login inside a hook.

## Live updates

Beam accepts the snake_case JSON emitted on stdin by root Claude Code and Codex
`Stop` hooks, plus Claude Code `SessionEnd` hooks. Subagent hooks are ignored:

```sh
node "$BEAM_SKILL_DIR/scripts/beam" hook \
  --endpoint "$BEAM_ENDPOINT" \
  --quiet
```

Templates:

- [`references/claude-code-hooks.json`](references/claude-code-hooks.json)
- [`references/codex-hooks.toml`](references/codex-hooks.toml)

`Stop` refreshes the snapshot after a completed root turn. Claude Code
`SessionEnd` marks it complete. Codex users can publish a final snapshot with
`publish --complete`; the public Codex template intentionally does not claim an
automatic completion hook. Hook failures exit nonzero but do not emit a blocking
hook decision.

## Receiver contract

The OpenClaw Beam plugin accepts `POST /api/v1/beam/sessions`. Ordinary Gateway
HTTP-authenticated uploads require `operator.write` or `operator.admin`. Every
`operator.read` client on that Gateway can view the catalog, so a separate Gateway
remains the isolation boundary between teams. Restricted personal guest access
requires receiver-side support and an active verified Visitor identity. It grants
no `operator.read` scope or shared-catalog access. Separate publisher-bound routes
allow listing and reading only that publisher's snapshots. They recheck current
authority and ownership before returning data. Guests cannot delete or continue sessions.

The request remains version `1`. The normal receipt remains
`{ "ok": true, "beamId": "...", "url": "..." }`. Current guest receipts add
`"canView": true` for owned-snapshot viewing. Older upload-only receivers can
return `"canView": false`. Staff and older receivers may omit `canView`; if present
it must be a boolean. The receipt is not a credential or an access grant.
Viewing still requires current publisher authority and snapshot ownership.
The same origin, endpoint-derived base path, and Beam ID URL checks apply whether
or not the publisher can view the result.

The receiver rejects transcript item text longer than 6,000 characters.
Accordingly, explicit `--entry-max-chars` values above 6,000 fail locally
before upload.

Authorized staff can continue from the catalog by copying the shared transcript
into a new Team session. This is a transcript handoff, not remote access to the
publisher's machine or continuation of the local harness; it grants no terminal,
tool, filesystem, credential, or node access. Guests cannot continue sessions,
including snapshots they can view.

For rollout compatibility, the helper also accepts the current server's exact
`/chat/<agent>?catalog=beam&host=gateway&thread=<full-beam-id>` URL. This is a
narrow transition path: the obsolete `?session=catalog:...` beta URL remains
rejected.

OpenClaw plugin documentation:
https://docs.openclaw.ai/plugins/beam

## Development

```sh
node --check skills/beam/scripts/beam
node --check skills/beam/scripts/beam-session.js
node --test skills/beam/scripts/beam.test.mjs
python scripts/validate-skills
```
