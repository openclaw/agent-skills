# AGENTS.md

Public shared skills for agent workflows.

## Rules

- Canonical shared skills live under `skills/<name>/SKILL.md`.
- Keep repo-specific workflows out unless they are useful as public examples.
- Keep secrets, private hostnames, private account IDs, and private URLs out.
- Skill descriptions: short trigger phrase, not full documentation.
- Skill bodies: operational, terse, current.
- Helper scripts belong under `skills/<name>/scripts/`.
- Validate after edits: `scripts/validate-skills`.
- Do not edit generated/vendor copies in downstream repos; update here, then sync.

## Layout

- `skills/autoreview`: shared closeout/code-review helper.
- `skills/beam`: redacted read-only coding-session publication.
- `skills/crabbox`: shared Crabbox/Testbox remote validation workflow.
