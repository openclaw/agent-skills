# Diagnostics and E2E

## Observability

Prefer built-ins:

- `--preflight`: target/workspace/tool probes.
- `--debug --timing-json`: sync, command, total timing.
- `--script <file>` / `--script-stdin`: safe multiline direct-provider command.
- `--allow-env NAME` + `--env-from-profile <file>`: exact direct-provider env.
- `CRABBOX_ENV_ALLOW=NAME,...`: exact ambient env allowlist.
- `--capture-stdout`, `--capture-stderr`: direct-provider local capture.
- `--capture-on-fail`: test artifacts; secret-bearing until reviewed.
- `--keep-on-failure`: retain failed lease for debugging.
- `--results-auto` / `--junit <path>`: structured failure digest.
- `CRABBOX_PHASE:<name>` lines: phase timing.

- Secrets: exact key only; one command. Never print, repo file, or shell history.
- No safe injection path: report live auth blocked. No fake-key upgrade to “live proof.”

## Real E2E

Follow the requested proof scope and the consumer repository's requirements.
Remote focused tests or builds prove only those checks.
Use this recipe when the user or consumer requires real user-path proof.
Never describe remote unit tests as real E2E.

1. Reproduce entrypoint when feasible.
2. Patch. Narrow local test.
3. Remote install/update/onboard/CLI/service/API path.
4. Record provider, id, command, environment shape, redacted secret source,
   observed result.
5. Cleanup.

Route:

- Install/package: pack tarball; install like user; matching Docker/package lane.
- Provider/auth: real provider; scrub unrelated provider vars.
- Integration: setup, config, send/receive; inspect redacted logs.
- Service/session/tool: real CLI or API; inspect persisted state and result.
- Parser/config: focused tests enough only when OS/package/service cannot matter.

- Before/after: same Testbox when practical. Detached temp worktrees under `/tmp`.
  Never checkout refs in synced root.
- Native Testbox: prepare/compare both revisions within one synced invocation;
  later runs sync local checkout again.
- Full-screen CLI: real PTY. Interactive Clack: exact arrows/Enter; raw search typing can lie.
- Use consumer's documented temporary state/config directory; proof must never
  mutate operator's normal installation.

## Failure Triage

Identify layer: wrapper, provider, hydration, sync, SSH, command.

```sh
"$CRABBOX" doctor
"$CRABBOX" status --id <id>
"$CRABBOX" inspect --id <id> --json
"$CRABBOX" history --limit 20
"$CRABBOX" logs <run_id>
"$CRABBOX" results <run_id>
blacksmith testbox list --all
blacksmith testbox status --id <tbx_id>
```

- Provider/CLI old: follow consumer's trusted Crabbox update path.
- Config/auth: `config show`, `doctor`, `whoami`.
- Sync quiet/stale: inspect `--debug --timing-json`. Direct providers support
  `--full-resync`; Testbox uses native sync and the skill's
  [input checks](../SKILL.md#verify-synced-inputs).
- Testbox capacity: follow the [proof and capacity rules](../SKILL.md#crabbox).
- Command failure: read phase, failed test, JUnit, skipped shell segment. Focused
  rerun first.
- Cleanup unclear: list exact provider. Stop only owned ids.
- Consumer wrapper broken: installed Crabbox CLI only to isolate wrapper;
  preserve same resolved provider.

Crabbox stop: no `--timing-json`.
