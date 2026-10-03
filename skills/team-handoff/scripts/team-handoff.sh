#!/usr/bin/env bash
# Start, inspect, or archive worktree sessions on a shared OpenClaw Gateway as the
# operator's own identity (Cloudflare Access token via an isolated CLI profile).
set -euo pipefail

CONFIG_FILE="${OPENCLAW_HANDOFF_ENV:-${XDG_CONFIG_HOME:-$HOME/.config}/openclaw/team-handoff.env}"
if [ -f "$CONFIG_FILE" ]; then
  # The file supplies defaults only; variables already in the environment win.
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; esac
    key="${line%%=*}"; value="${line#*=}"
    case "$key" in OPENCLAW_HANDOFF_*) ;; *) continue ;; esac
    if [ -z "${!key+x}" ]; then
      export "$key=$value"
    fi
  done < "$CONFIG_FILE"
fi

URL="${OPENCLAW_HANDOFF_URL:-}"
AGENT_DEFAULT="${OPENCLAW_HANDOFF_AGENT:-main}"
PROJECT_DEFAULT="${OPENCLAW_HANDOFF_PROJECT:-}"
PROFILE_DIR="${OPENCLAW_HANDOFF_PROFILE_DIR:-$HOME/.openclaw/profiles/team}"
CLI="${OPENCLAW_HANDOFF_CLI:-openclaw}"
SSH_HOST="${OPENCLAW_HANDOFF_SSH_HOST:-}"
REMOTE_CLI="${OPENCLAW_HANDOFF_REMOTE_CLI:-openclaw}"
REMOTE_USER="${OPENCLAW_HANDOFF_REMOTE_USER:-openclaw}"
CLOUDFLARED="${OPENCLAW_HANDOFF_CLOUDFLARED:-}"

usage() {
  cat <<'EOF'
Usage:
  team-handoff.sh probe [--via profile|ssh]
  team-handoff.sh create --label <text> --message-file <path> [--name <worktree>] [--base <ref>]
                         [--agent <id>] [--project <id>] [--via profile|ssh] [--dry-run]
  team-handoff.sh status <sessionKey> [--via profile|ssh]
  team-handoff.sh archive <sessionKey> <sessionId> [--via profile|ssh]

Config: ${XDG_CONFIG_HOME:-~/.config}/openclaw/team-handoff.env (OPENCLAW_HANDOFF_URL, _AGENT,
_PROJECT, _CLI, _PROFILE_DIR, _SSH_HOST, _REMOTE_CLI, _REMOTE_USER, _CLOUDFLARED)
EOF
}

require_url() {
  [ -n "$URL" ] || { echo "OPENCLAW_HANDOFF_URL is not set (see SKILL.md setup)" >&2; exit 2; }
}

ws_url() {
  printf '%s' "$URL" | sed -e 's#^https://#wss://#' -e 's#^http://#ws://#'
}

ensure_profile() {
  if [ -f "$PROFILE_DIR/openclaw.json" ]; then
    # A cached profile pins both the remote URL and the Access app; refuse to send to a stale target.
    python3 - "$PROFILE_DIR/openclaw.json" "$URL" "$(ws_url)" <<'PY' || return 2
import json, sys
path, url, ws = sys.argv[1:4]
config = json.load(open(path))
remote = config.get("gateway", {}).get("remote", {}).get("url")
args = config.get("secrets", {}).get("providers", {}).get("cloudflare-access", {}).get("args", [])
app = next((a[len("-app="):] for a in args if isinstance(a, str) and a.startswith("-app=")), None)
if remote != ws or app != url:
    sys.exit(f"profile {path} targets {remote} / {app}, not {url}; move it aside or fix it before using this URL")
PY
    return 0
  fi
  local bin
  bin="${CLOUDFLARED:-$(command -v cloudflared || true)}"
  [ -n "$bin" ] || { echo "cloudflared not found; install it or set OPENCLAW_HANDOFF_CLOUDFLARED" >&2; return 2; }
  bin="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$bin")"
  mkdir -p "$PROFILE_DIR"
  python3 - "$PROFILE_DIR/openclaw.json" "$bin" "$URL" "$(ws_url)" <<'PY'
import json, os, sys
path, binary, url, ws = sys.argv[1:5]
config = {
    "secrets": {"providers": {"cloudflare-access": {
        "source": "exec", "command": binary, "args": ["access", "token", f"-app={url}"],
        "jsonOnly": False, "passEnv": ["HOME"], "trustedDirs": [os.path.dirname(binary)]}}},
    "gateway": {"mode": "remote", "remote": {"url": ws, "edgeAuth": {
        "Cf-Access-Token": {"source": "exec", "provider": "cloudflare-access", "id": "token"}}}},
}
with open(path, "w") as handle:
    json.dump(config, handle, indent=2)
os.chmod(path, 0o600)
print(f"wrote {path}", file=sys.stderr)
PY
}

gateway_call() {
  # gateway_call <via> <method> <params-json>
  local via="$1" method="$2" params="$3"
  case "$via" in
    profile)
      require_url
      ensure_profile
      command -v "$CLI" >/dev/null 2>&1 || [ -x "$CLI" ] || { echo "OpenClaw CLI not found: $CLI (set OPENCLAW_HANDOFF_CLI)" >&2; return 2; }
      OPENCLAW_STATE_DIR="$PROFILE_DIR" OPENCLAW_CONFIG_PATH="$PROFILE_DIR/openclaw.json" \
        "$CLI" gateway call "$method" --json --timeout 120000 --params "$params" 2>&1
      ;;
    ssh)
      [ -n "$SSH_HOST" ] || { echo "OPENCLAW_HANDOFF_SSH_HOST is not set; the SSH fallback is opt-in" >&2; return 2; }
      # The payload travels on stdin and stays in the remote shell's memory; no shared temp file.
      printf '%s' "$params" | ssh -o BatchMode=yes "$SSH_HOST" "params=\$(cat); sudo -n -u $REMOTE_USER -H $REMOTE_CLI gateway call $method --json --timeout 120000 --params \"\$params\" 2>&1"
      ;;
    *) echo "unknown --via $via" >&2; return 2 ;;
  esac
}

pretty_url() {
  # pretty_url <agent> <label> <sessionKey>
  python3 - "$1" "$2" "$3" "$URL" <<'PY'
import re, sys
agent, label, key, base = sys.argv[1:5]
uuid = key.rsplit(":", 1)[-1].replace("-", "")
slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", label.lower())).strip("-")
print(f"{base.rstrip('/')}/chat/{agent}/{slug}-{uuid}")
PY
}

cmd="${1:-}"; shift || true
via=profile; label=""; name=""; base="origin/main"; message_file=""; agent="$AGENT_DEFAULT"; project="$PROJECT_DEFAULT"; dry=0
positional=()
while [ $# -gt 0 ]; do
  case "$1" in
    --via) via="$2"; shift 2 ;;
    --label) label="$2"; shift 2 ;;
    --name) name="$2"; shift 2 ;;
    --base) base="$2"; shift 2 ;;
    --message-file) message_file="$2"; shift 2 ;;
    --agent) agent="$2"; shift 2 ;;
    --project) project="$2"; shift 2 ;;
    --dry-run) dry=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) positional+=("$1"); shift ;;
  esac
done

case "$cmd" in
  probe)
    out="$(gateway_call "$via" health '{}')" || { printf '%s\n' "$out" >&2; exit 1; }
    printf '%s' "$out" | python3 -c 'import sys,json; d=json.load(sys.stdin); ok = d.get("ok", True) and not d.get("error"); print("ok" if ok else json.dumps(d.get("error"))); sys.exit(0 if ok else 1)'
    ;;
  create)
    [ -n "$label" ] && [ -n "$message_file" ] || { usage; exit 2; }
    [ -n "$project" ] || { echo "no project id: pass --project or set OPENCLAW_HANDOFF_PROJECT" >&2; exit 2; }
    [ -f "$message_file" ] || { echo "no such message file: $message_file" >&2; exit 2; }
    params="$(python3 - "$agent" "$project" "$label" "$name" "$base" "$message_file" <<'PY'
import json, sys
agent, project, label, name, base, path = sys.argv[1:7]
p = {"agentId": agent, "label": label, "message": open(path).read(), "projectId": project,
     "worktree": True, "worktreeBaseRef": base}
if name:
    p["worktreeName"] = name
print(json.dumps(p))
PY
)"
    if [ "$dry" = 1 ]; then printf '%s\n' "$params" | python3 -c 'import sys,json; d=json.load(sys.stdin); d["message"]=d["message"][:80]+"…"; print(json.dumps(d,indent=2))'; exit 0; fi
    [ "$via" = ssh ] || require_url
    out="$(gateway_call "$via" sessions.create "$params")" || { printf '%s\n' "$out" >&2; exit 1; }
    key="$(printf '%s' "$out" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("key","") if d.get("ok") else "")' 2>/dev/null || true)"
    if [ -z "$key" ]; then printf '%s\n' "$out" >&2; exit 1; fi
    if [ -n "$URL" ]; then printf 'url: %s\n' "$(pretty_url "$agent" "$label" "$key")"; fi
    printf 'key: %s\n' "$key"
    # sessions.create can succeed while the initial turn is rejected (runStarted:false + runError).
    printf '%s' "$out" | python3 -c '
import sys, json
d = json.load(sys.stdin)
identity = sys.argv[1]
if d.get("runStarted") is False or d.get("runError"):
    print("runStarted: false | runError:", json.dumps(d.get("runError")), "| the session exists but the handoff turn did not start", file=sys.stderr)
    sys.exit(1)
print("runId:", d.get("runId"), "| status:", d.get("status"), "| identity:", identity)' "$([ "$via" = ssh ] && echo 'Gateway operator (ssh fallback)' || echo 'operator via Access')"
    ;;
  status)
    key="${positional[0]:-}"; [ -n "$key" ] || { usage; exit 2; }
    out="$(gateway_call "$via" chat.history "$(printf '{"sessionKey":"%s","limit":3}' "$key")")" || { printf '%s\n' "$out" >&2; exit 1; }
    printf '%s' "$out" | python3 -c '
import sys, json
d = json.load(sys.stdin)
if not d.get("ok", True) or d.get("error"):
    print(json.dumps(d.get("error"))); sys.exit(1)
si = d.get("sessionInfo", {})
print("status:", si.get("status"), "| worktree:", json.dumps(si.get("worktree")), "| messages:", len(d.get("messages", [])))
for m in d.get("messages", [])[-2:]:
    c = m.get("content")
    if isinstance(c, list):
        c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
    print("-", m.get("role"), ":", str(c)[:200].replace("\n", " "))'
    ;;
  archive)
    key="${positional[0]:-}"; sid="${positional[1]:-}"; [ -n "$key" ] && [ -n "$sid" ] || { usage; exit 2; }
    out="$(gateway_call "$via" sessions.patch "$(printf '{"key":"%s","expectedSessionId":"%s","archived":true}' "$key" "$sid")")" || { printf '%s\n' "$out" >&2; exit 1; }
    printf '%s' "$out" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("archived" if d.get("ok") else json.dumps(d.get("error")))'
    ;;
  *) usage; exit 2 ;;
esac
