---
name: nexus-mcp-servers
description: "MCP Server Management — Configure, connect, and interact with external MCP servers. Use when an OpenJarvis user wants to call Nexus mcp.servers (DELETE, GET, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: mcp.servers
  source_file: backend/routes/routes_mcp_servers.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus mcp.servers

MCP Server Management — Configure, connect, and interact with external MCP servers.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `mcp.servers` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| GET | `/workspaces/{ws_id}/mcp-servers` |
| POST | `/workspaces/{ws_id}/mcp-servers` |
| DELETE | `/workspaces/{ws_id}/mcp-servers/{server_id}` |
| POST | `/workspaces/{ws_id}/mcp-servers/{server_id}/test` |
| GET | `/workspaces/{ws_id}/mcp-servers/{server_id}/tools` |
| POST | `/workspaces/{ws_id}/mcp-servers/{server_id}/tools/{tool_name}/execute` |

## Install

```sh
jarvis skill install nexus:mcp-servers
```

Source of truth: `backend/routes/routes_mcp_servers.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
