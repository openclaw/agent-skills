---
name: nexus-smart-inbox
description: "Smart Inbox core routes — threads, triage, actions, search. Use when an OpenJarvis user wants to call Nexus smart.inbox (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: smart.inbox
  source_file: backend/routes/routes_smart_inbox.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus smart.inbox

Smart Inbox core routes — threads, triage, actions, search.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `smart.inbox` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/mail/threads` |
| GET | `/workspaces/{ws_id}/mail/threads/{thread_id}` |
| GET | `/workspaces/{ws_id}/mail/search` |
| POST | `/workspaces/{ws_id}/mail/triage` |
| POST | `/workspaces/{ws_id}/mail/actions` |
| GET | `/workspaces/{ws_id}/mail/review` |
| POST | `/workspaces/{ws_id}/mail/review/{action_id}/approve` |
| POST | `/workspaces/{ws_id}/mail/review/{action_id}/dismiss` |
| GET | `/workspaces/{ws_id}/mail/stats` |
| POST | `/workspaces/{ws_id}/mail/auto-process` |
| POST | `/workspaces/{ws_id}/mail/drafts` |
| GET | `/workspaces/{ws_id}/mail/drafts` |
| POST | `/workspaces/{ws_id}/mail/drafts/{draft_id}/send` |
| DELETE | `/workspaces/{ws_id}/mail/drafts/{draft_id}` |
| POST | `/workspaces/{ws_id}/mail/webhook-test` |
| POST | `/workspaces/{ws_id}/mail/delegate` |
| POST | `/workspaces/{ws_id}/mail/actions/{action_id}/rollback` |
| GET | `/workspaces/{ws_id}/mail/digest` |

## Install

```sh
jarvis skill install nexus:smart-inbox
```

Source of truth: `backend/routes/routes_smart_inbox.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
