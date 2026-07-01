# Vision

OpenClaw Agent Skills is the curated public source for small, reusable agent
workflows. A skill belongs here when several repositories or agents benefit
from one shared operational contract.

## What Belongs Here

- A distinct recurring workflow, tool boundary, or evidence contract—not
  generic engineering judgment restated as instructions.
- Portable behavior that is useful across projects and agent runtimes.
- A narrow responsibility with explicit inputs, outputs, failure modes, and
  safety boundaries.
- Proportionate implementation and proof. Dependencies, privileges, and new
  automation must be necessary for the workflow itself.
- Public, vendor-neutral guidance where practical. Provider-specific behavior
  is acceptable when its real contract is documented and tested directly.

Examples include review closeout, source-blind behavior validation, remote
validation, transcript handling, and focused handoff workflows.

## Boundaries

- Product-specific skills, generated API catalogs, and service-owned workflows
  stay with their source project or a community catalog such as ClawHub.
- Repository instructions and callers own product policy, durable memory, and
  task context. Shared helpers should consume bounded explicit inputs rather
  than create parallel policy or persistence systems.
- Do not hide materially different provider cost, quality, eligibility, or
  failure semantics behind one portable convenience flag. Prefer explicit
  controls; require exact runtime proof for provider-specific tiers or modes.
- Repository-relative, bounded, read-only inputs are the default. Broader host
  paths, external repositories, credentials, publishing, or privileged
  automation require a narrow ownership model and end-to-end isolation proof.
- Distribution infrastructure is not bundled merely to publish one skill.
  Prefer existing source-repository and community publication paths.

## Evolution

- Solve one coherent user problem at a time; split unrelated policy,
  persistence, provider, and publishing surfaces.
- Validate the installed or built workflow through the real affected boundary.
  Dry runs, fixtures, and command-construction tests support but do not replace
  runtime proof for claims about external tools or services.
- Keep public CLI and artifact contracts predictable. Add compatibility only
  for explicit shipped contracts, not speculative future use.
- Prefer a smaller catalog with clear ownership and strong proof over broad
  coverage with duplicated judgment or hidden operational risk.
