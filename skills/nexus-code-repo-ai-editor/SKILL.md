---
name: nexus-code-repo-ai-editor
description: "Repo AI editor — Cursor-parity endpoints (completion / edit / chat). Use when an OpenJarvis user wants to call Nexus code.repo.ai.editor (POST) endpoints."
license: Apache-2.0
metadata:
  catalog: nexus-skills
  catalog_version: "1.0.0"
  version: "1.0.0"
  surface: code.repo.ai.editor
  source_file: backend/routes/routes_code_repo_ai_editor.py
  auth: bearer_token
  auth_env: NEXUS_API_TOKEN
  scope: nexus.api
compatibility: "Requires a Nexus deployment reachable via NEXUS_BASE_URL with a bearer token in NEXUS_API_TOKEN."
---

# Nexus code.repo.ai.editor

Repo AI editor — Cursor-parity endpoints (completion / edit / chat).

## When to use

Activate when an OpenJarvis user wants to call any endpoint under the `code.repo.ai.editor` surface against a Nexus deployment. The skill carries the bearer-token auth contract and lists the verbs and paths the surface exposes.

## Auth

- Method: `bearer_token`
- Env: `NEXUS_API_TOKEN` (token must carry the `nexus.api` scope)
- Base URL: `NEXUS_BASE_URL` (e.g. `https://nexus.example.com`)

## Endpoints

| Method | Path |
| ------ | ---- |
| POST | `/workspaces/{workspace_id}/code-repo/ai-complete` |
| POST | `/workspaces/{workspace_id}/code-repo/ai-edit-preview` |
| POST | `/workspaces/{workspace_id}/code-repo/ai-selection-edit` |
| POST | `/workspaces/{workspace_id}/code-repo/chat` |
| POST | `/workspaces/{workspace_id}/code-repo/ai-multi-edit-preview` |
| POST | `/workspaces/{workspace_id}/code-repo/ai-edit-multi/conflicts` |
| POST | `/workspaces/{workspace_id}/code-repo/ai-edit-multi` |

## Install

```sh
jarvis skill install nexus:code-repo-ai-editor
```

Source of truth: `backend/routes/routes_code_repo_ai_editor.py` in the Nexus repo. Regenerate this bundle with `python scripts/generate_agentskills.py`.
