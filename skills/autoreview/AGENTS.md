# Autoreview Skill

- Canonical source: `openclaw/agent-skills`, under `skills/autoreview`.
- Before editing any copy, fetch the canonical repository and fast-forward the checkout from its canonical main remote (`upstream/main` in a fork checkout, otherwise `origin/main`). Reconcile downstream-only dirty work semantically; never overwrite newer canonical behavior with an older package copy.
- Make shared changes in canonical `skills/autoreview` first, then run `python3 skills/autoreview/scripts/validate-autoreview.py` from the repository root.
- When model-backed release evidence is required, also run `skills/autoreview/scripts/test-review-harness --release-gate --artifact-dir PATH` and retain the artifacts.
- After validation, sync the complete `skills/autoreview` directory into downstream repos. Preserve only downstream installer/provenance metadata, then rerun the canonical gate with `--compare-downstream PATH` so an installed copy does not need its own Git checkout.
- Never create repo-local behavior variants; downstream differences belong in repo-level validation, not the skill.
- Keep `CLAUDE.md` as the exact `@AGENTS.md` import so Claude and other agents receive one maintenance contract.
