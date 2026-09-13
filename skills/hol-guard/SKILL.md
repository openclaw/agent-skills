---
name: hol-guard
description: "Protect supported local coding-agent harnesses with HOL Guard before mutation-bearing tool use."
---

# HOL Guard

Use HOL Guard as the local runtime boundary before a supported coding agent performs mutation-bearing tool work. Keep repository review, client permissions, provider authorization, sandboxing, and remote safeguards authoritative.

## Setup

Probe the real CLI:

```sh
hol-guard --version
```

If it is unavailable and runtime setup is in scope, install the vetted release pin used by this skill:

```sh
uv tool install "hol-guard[cisco]==2.2.128"
hol-guard --version
```

The pin is the official Hashgraph Online `v2.2.128` release and PyPI `hol-guard` distribution. Require the version check to report `2.2.128`; do not replace the pin with `latest`, a branch URL, or an unversioned package. If installation is not authorized or `uv` is unavailable, stop and report the missing runtime rather than weakening the boundary.

Resolve support and the exact harness identifier from HOL Guard itself:

```sh
hol-guard detect --json
```

Use only a supported identifier returned by `detect`. Do not maintain a separate alias list.

## Protect the harness

Run the Guard-owned setup and protected launch flow:

```sh
hol-guard bootstrap
hol-guard install <detected-harness>
hol-guard run <detected-harness> --dry-run
hol-guard run <detected-harness>
hol-guard doctor <detected-harness> --json
hol-guard status
```

Treat an unprotected fallback as failure. If the dry run, protected launch, doctor, or status cannot prove the expected protection state, stop mutation-bearing tool work and report the failing command. Do not retry by launching the agent directly.

## Approvals and evidence

When Guard blocks or queues work, inspect the actual request before deciding what to do:

```sh
hol-guard approvals
hol-guard approvals open
hol-guard receipts
```

Approve or deny only through Guard-owned commands after reviewing the risk reason and requested scope. Do not bypass a Guard decision by editing harness configuration manually.

For troubleshooting or evidence, prefer:

```sh
hol-guard doctor <detected-harness> --json
hol-guard diff <detected-harness>
hol-guard receipts
hol-guard events
```

Report the command that ran, what Guard found, what remains blocked or risky, and the evidence available. Never claim protection or approval without Guard output proving it.

## Boundary

HOL Guard protects the local supported-agent runtime. It does not replace repository policy, code review, operating-system isolation, application authorization, provider-side access controls, or any remote service's own safety checks.
