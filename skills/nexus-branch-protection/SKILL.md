---
name: nexus-branch-protection
description: "Branch Protection Rules v1 — per-target-branch merge policy. Use when an OpenJarvis user wants to call Nexus branch.protection (DELETE, GET, PATCH, POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: branch.protection
  source_file: backend/routes/routes_branch_protection.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus branch.protection

Branch Protection Rules v1 — per-target-branch merge policy.

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `branch.protection` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/code-repo/branch-protections` |
| GET | `/workspaces/{workspace_id}/code-repo/branch-protections` |
| PATCH | `/workspaces/{workspace_id}/code-repo/branch-protections/{protection_id}` |
| DELETE | `/workspaces/{workspace_id}/code-repo/branch-protections/{protection_id}` |

## Install

```sh
jarvis skill install nexus:branch-protection
```

Source of truth: `backend/routes/routes_branch_protection.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
