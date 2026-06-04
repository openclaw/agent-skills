# Nexus skill bundle (DRAFT contribution)

This DRAFT PR adds 230 `nexus-*` skills under `skills/`, sourced from the Nexus
backend's `backend/routes/*.py` surfaces. Each skill is an
[agentskills.io](https://agentskills.io/specification)-conformant
`SKILL.md` (YAML frontmatter + Markdown body + endpoint table).

## At a glance

- **Catalog**: `nexus-skills@1.0.0`
- **Skills added**: 230 (one per Nexus route surface)
- **Endpoints covered**: 2120
- **Files skipped at source**: 22 (`routes_admin*`, `routes_*_admin`, `health`,
  `internal`, `webhooks`, `webhook_admin`, websocket-only, widget loaders,
  dispatch push)
- **Auth contract per skill**: `bearer_token`, env `NEXUS_API_TOKEN`,
  scope `nexus.api`, base URL via `NEXUS_BASE_URL`
- **Flagged families** (declared in `metadata.flags`): streaming SSE,
  multipart upload (`files`, `media`, `image_gen`, `image_understanding`)

## Catalog index

`NEXUS_CATALOG.yaml` (this directory) is a copy of the Nexus-side
`skills/agentskills/manifest.yaml` and lists every skill with its source
file, endpoint count, and flags.

## Source of truth

The bundle is regenerated deterministically from the Nexus repo by
`scripts/generate_agentskills.py`. PRs to the Nexus repo that touch a route
re-run the generator and re-validate the spec contract.

- Upstream PR: kelliott-cloud/Nexus-10.0-A#785
- Generator: `scripts/generate_agentskills.py` in the Nexus repo

## Operator review notes

- 230 new skill folders is large for this catalog (was 5). Promotion strategy
  is operator's call: accept as-is, move to a `skills/nexus/` subdir (requires
  scripts/install-skills update), or keep a curated subset and let the
  remaining surfaces stay catalog-only via `NEXUS_CATALOG.yaml`.
- All skill names follow the agentskills.io spec (`a-z0-9-`, ≤64 chars, parent
  dir matches name).
- Skills validate against the existing `scripts/validate-skills` rule
  (`name` + `description` present in frontmatter).
