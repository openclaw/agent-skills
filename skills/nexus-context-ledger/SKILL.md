---
name: nexus-context-ledger
description: "Context Ledger — Tracks agent context switches for seamless work resumption. Use when an OpenJarvis user wants to call Nexus context.ledger (GET) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: context.ledger
  source_file: backend/routes/routes_context_ledger.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus context.ledger

Context Ledger — Tracks agent context switches for seamless work resumption.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `context.ledger` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/channels/{channel_id}/context-ledger` |
| GET | `/admin/context-ledger` |
| GET | `/admin/context-ledger/stats` |

## Install

```sh
jarvis skill install nexus:context-ledger
```

Source of truth: `backend/routes/routes_context_ledger.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
