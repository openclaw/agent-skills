---
name: nexus-mail-rules
description: "Mail rules — if/then automation conditions for email triage. Use when an OpenJarvis user wants to call Nexus mail.rules (DELETE, GET, POST, PUT) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: mail.rules
  source_file: backend/routes/routes_mail_rules.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus mail.rules

Mail rules — if/then automation conditions for email triage.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `mail.rules` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/mail/rules` |
| POST | `/workspaces/{ws_id}/mail/rules` |
| PUT | `/workspaces/{ws_id}/mail/rules/{rule_id}` |
| DELETE | `/workspaces/{ws_id}/mail/rules/{rule_id}` |

## Install

```sh
jarvis skill install nexus:mail-rules
```

Source of truth: `backend/routes/routes_mail_rules.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
