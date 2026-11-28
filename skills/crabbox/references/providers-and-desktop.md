# Provider and desktop recipes

Read only for selected provider or requested desktop/cross-OS proof.
[Routing and proof rules](../SKILL.md#route-first) still apply: no provider
escalation or waiting for capacity.

## Direct AWS

```sh
"$CRABBOX" run --provider aws --timing-json --shell -- "<check-command>"
```

For a longer bounded command, request the required lifetime before preparation:

```sh
"$CRABBOX" run --provider aws --idle-timeout 90m --ttl 240m \
  --timing-json --shell -- "<check-command>"
```

- Stale sync: retry `--full-resync` once. Still bad: fresh lease.
- One-shot should stop itself; failure/interruption: verify `"$CRABBOX" list --provider aws`.
  Use `--retained` to find kept terminal resources with unconfirmed cleanup;
  inspect and stop the exact owned ID. A missing live-list row is not deletion
  proof. Follow the [lifetime and cleanup rules](lease-lifetime.md).

Broker auth, not cloud keys:

```sh
"$CRABBOX" config show
"$CRABBOX" doctor
"$CRABBOX" whoami
"$CRABBOX" login --url <broker-url> --provider aws
```

Normal validation asks for AWS keys: usually wrong path.

## Fresh PR / Container

- `--fresh-pr <owner/repo#123>`: clean remote checkout. `--apply-local-patch`
  only for intentional local fixup. Direct providers only.

Local Docker only when resolved configuration selects it or user explicitly
requests local-container lane:

```sh
"$CRABBOX" run \
  --provider local-container \
  --local-container-image <container-image> \
  --no-hydrate --fresh-pr <owner/repo#number> \
  --timing-json --shell -- \
  "<install-and-check-command>"
```

- Report `local-container`; not AWS/Testbox. Keep `--no-hydrate`.
- Host-mounted caches cannot cross filesystems: use repository-local dependency cache.

## Desktop / Cross-OS

Static hosts:

```sh
"$CRABBOX" run --provider ssh --target macos \
  --static-host <macos-host> -- <check-command>
"$CRABBOX" run --provider ssh --target windows --windows-mode normal \
  --static-host <windows-host> -- pwsh -NoProfile -Command '<check-command>'
"$CRABBOX" run --provider ssh --target windows --windows-mode wsl2 \
  --static-host <windows-host> -- <check-command>
```

- Windows/WSL2: prefer Azure when advertised/configured.
- Native Windows: OpenSSH + PowerShell + Git + tar. Actions hydration Linux-only.

Brokered macOS: paid EC2 Mac. First quota/no-spend preflight.
No silent substitution for Linux proof.

```sh
"$CRABBOX" admin hosts quota --provider aws --target macos \
  --region eu-west-1 --type mac2.metal --json
"$CRABBOX" admin hosts allocate --provider aws --target macos \
  --region eu-west-1 --type mac2.metal --dry-run --json
```

Human desktop: prefer WebVNC when resolved provider supports it.
Never change providers only to gain desktop support.

```sh
"$CRABBOX" warmup --desktop --browser --ttl 2h --idle-timeout 30m --keep
"$CRABBOX" desktop launch --id <id> \
  --browser --url https://example.com --webvnc --open --take-control
"$CRABBOX" desktop doctor --id <id>
"$CRABBOX" webvnc status --id <id>
"$CRABBOX" artifacts collect --id <id> --all --output artifacts/<slug>
```

Before handoff: prove CLI/app from neutral `~`:

```sh
"$CRABBOX" run --id <id> --shell -- \
  "cd ~ && command -v <command> && <command> --version"
```

- Visible desktop alone proves nothing. Keep browser windowed unless capture task.
- Never commit proof assets to product repo.

- Desktop activity does not extend total TTL. Save artifacts before the effective
  deadline; `--keep` is not persistence. Follow the lifetime rules before handoff.
