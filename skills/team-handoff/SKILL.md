---
name: team-handoff
description: "Hand local work to a shared OpenClaw Gateway: start a worktree session there as yourself in one request, seeded with a handoff, and get the session URL back."
---

# Team Handoff

Use when the user says "open a session on the team server for this", "hand this
off to <team agent>", or "summarize this for a new agent and start it on
<gateway>", and the target is a shared OpenClaw Gateway behind an identity-aware
proxy (Cloudflare Access).

One Gateway request, as the operator's own identity. No browser automation, no
SSH, no polling.

Script: `scripts/team-handoff.sh`

## Setup (once per machine)

1. Operator config, outside any repo:
   `${XDG_CONFIG_HOME:-~/.config}/openclaw/team-handoff.env`

   ```sh
   OPENCLAW_HANDOFF_URL=https://gateway.example      # the shared Gateway's public origin
   OPENCLAW_HANDOFF_AGENT=main                        # default agent id on that Gateway
   OPENCLAW_HANDOFF_PROJECT=example-project           # default projects.list id
   # optional:
   # OPENCLAW_HANDOFF_CLI=/path/to/openclaw           # installed OpenClaw CLI (default: openclaw on PATH)
   # OPENCLAW_HANDOFF_PROFILE_DIR=~/.openclaw/profiles/team
   # OPENCLAW_HANDOFF_SSH_HOST=gateway-host           # operator fallback only; see below
   ```

2. Isolated CLI profile so the local Gateway config is never touched. The script
   writes it on first `probe` when missing: `OPENCLAW_STATE_DIR` and
   `OPENCLAW_CONFIG_PATH` point at the profile dir, whose `openclaw.json` holds
   only `gateway.mode: "remote"`, `gateway.remote.url`, and an `exec` secret
   provider that runs `cloudflared access token -app=<url>` for the
   `Cf-Access-Token` header (`gateway.remote.edgeAuth`, see the OpenClaw
   docs page "Remote access", section "Gateway behind an identity-aware proxy").
   The provider `command` must be the real `cloudflared` binary, not a symlink.

3. The human logs in once per Access session lifetime (agents cannot):

   ```sh
   cloudflared access login https://gateway.example
   ```

   `probe` prints `ok` when the chain works. `Exec provider "cloudflare-access"
   exited with code 1` or an HTTP 302 on upgrade means the login lapsed: ask the
   human to run it again; do not switch to the SSH fallback on your own.

Why there is no token to mint: with `gateway.auth.mode: "trusted-proxy"` the
proxy authenticates the user and the Gateway maps the identity header to scopes;
first connection auto-pairs a CLI device with the proxy's `deviceAutoApprove`
scopes, which cover `sessions.create`.

## Use

```sh
bash scripts/team-handoff.sh probe
bash scripts/team-handoff.sh create \
  --label "Installed-package entry cap durable fix" \
  --name tree-cap-fix --base origin/main \
  --message-file /path/to/handoff.md
bash scripts/team-handoff.sh status <sessionKey>
bash scripts/team-handoff.sh archive <sessionKey> <sessionId>
```

`create` prints `url:` in the Control UI form
`<origin>/chat/<agent>/<label-slug>-<session-key-uuid-without-dashes>`, plus the
session key and run id. Hand the human that URL. Creation returns before the
worktree is prepared; `running` with `worktree: null` right after is normal, and
the agent's first turn starts once the checkout binds. Read status once; do not
loop.

## Payload

- Branch first. Push the work, pass `--base <branch>`, keep the long handoff in
  the branch (for example `.openclaw/handoff.md`); the message is then three
  lines: what the branch is, what to do first, what not to do. Local files are
  unreachable from the Gateway; commit them or summarize the numbers.
- Without a branch, the whole handoff goes in `--message-file`: a one-line title
  first (it becomes the session title and URL slug), then goal, verified facts
  with numbers, owner files, the agreed plan and order, proof expectations, and
  explicit non-goals.
- Name scope boundaries when a local session keeps part of the work, so two
  agents do not open duplicate PRs.

## Failure modes

- `managed worktree allocation lease .../capacity was lost`: the Gateway lost
  its worktree capacity lease during a slow project refetch. A retry in the same
  session then fails with `branch already exists: openclaw/<name>` because the
  failed attempt leaked its branch. Create a new session with a different
  `--name`; archive the dead one.
- `chat.send` requires `idempotencyKey`; `sessions.patch` lifecycle changes
  require `expectedSessionId`.

## SSH operator fallback

`--via ssh` runs the same `sessions.create` on the Gateway host as the Gateway's
service user (`OPENCLAW_HANDOFF_SSH_HOST`, `OPENCLAW_HANDOFF_REMOTE_CLI`,
`OPENCLAW_HANDOFF_REMOTE_USER`). The session is then owned by the operator
identity, not the human. Use only when the human asks for it; never change
Gateway config or restart anything from this path.

## Don'ts

- Do not drive the Gateway's web UI from an agent browser or sign in to the
  identity provider.
- Do not point the machine's primary `openclaw.json` at the shared Gateway.
- Do not poll session history in a loop.
