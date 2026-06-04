---
name: nexus-notifications
description: "Notification system for AI agent completion and other events. Use when an OpenJarvis user wants to call Nexus notifications (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: notifications
  source_file: backend/routes/routes_notifications.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus notifications

Notification system for AI agent completion and other events.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `notifications` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/notifications` |
| PUT | `/notifications/{notification_id}/read` |
| POST | `/notifications/{notification_id}/read` |
| PUT | `/notifications/read-all` |
| POST | `/notifications/mark-all-read` |
| GET | `/notifications/unread-count` |
| DELETE | `/notifications/{notification_id}` |
| DELETE | `/notifications` |
| GET | `/notifications/settings` |
| PUT | `/notifications/settings` |

## Install

```sh
jarvis skill install nexus:notifications
```

Source of truth: `backend/routes/routes_notifications.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
