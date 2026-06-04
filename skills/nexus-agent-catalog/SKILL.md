---
name: nexus-agent-catalog
description: "Agent Catalog routes — builtin templates, org-shared agents, marketplace clone. Use when an OpenJarvis user wants to call Nexus agent.catalog (GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: agent.catalog
  source_file: backend/routes/routes_agent_catalog.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus agent.catalog

Agent Catalog routes — builtin templates, org-shared agents, marketplace clone.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `agent.catalog` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/catalog/templates` |
| GET | `/catalog/templates/{template_id}` |
| POST | `/catalog/marketplace/{agent_id}/clone` |
| POST | `/workspaces/{ws_id}/agents/{agent_id}/rate` |

## Install

```sh
jarvis skill install nexus:agent-catalog
```

Source of truth: `backend/routes/routes_agent_catalog.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
