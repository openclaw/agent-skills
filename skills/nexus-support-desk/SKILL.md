---
name: nexus-support-desk
description: "Support Desk — lightweight JSD (Jira Service Desk) for internal/external ticket management. Use when an OpenJarvis user wants to call Nexus support.desk (GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: support.desk
  source_file: backend/routes/routes_support_desk.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus support.desk

Support Desk — lightweight JSD (Jira Service Desk) for internal/external ticket management

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `support.desk` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/support/tickets` |
| GET | `/support/tickets` |
| GET | `/support/tickets/my` |
| GET | `/support/tickets/assigned` |
| GET | `/support/tickets/{ticket_id}` |
| PUT | `/support/tickets/{ticket_id}` |
| POST | `/support/tickets/{ticket_id}/replies` |
| GET | `/support/tickets/{ticket_id}/replies` |
| GET | `/support/tickets/{ticket_id}/activity` |
| GET | `/support/dashboard` |
| GET | `/support/sla-policies` |
| PUT | `/support/tickets/{ticket_id}/sla` |
| GET | `/support/suggested-articles` |
| GET | `/support/config` |
| POST | `/support/tickets/{ticket_id}/attachments` |
| GET | `/support/tickets/{ticket_id}/attachments` |
| GET | `/support/ticket-attachments/{att_id}` |
| GET | `/support/queues` |
| GET | `/support/queues/{queue_type}` |

## Install

```sh
jarvis skill install nexus:support-desk
```

Source of truth: `backend/routes/routes_support_desk.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
