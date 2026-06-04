---
name: nexus-research-chat
description: "SSE wrapper around :func:`research_chat_stream.research_chat_stream`. Use when an OpenJarvis user wants to call Nexus research.chat (POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: research.chat
  source_file: backend/routes/routes_research_chat.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus research.chat

SSE wrapper around :func:`research_chat_stream.research_chat_stream`.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `research.chat` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/research/chat/stream` |

## Install

```sh
jarvis skill install nexus:research-chat
```

Source of truth: `backend/routes/routes_research_chat.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
