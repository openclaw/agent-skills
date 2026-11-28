# Blacksmith directory downloads

Read after [trusted Testbox routing](../SKILL.md#trusted-testbox).

- Blacksmith CLI 0.4.60 (verified 2026-09-19): **remote directory argument**
  needs trailing `/` for recursive SCP; otherwise fails with `not a regular file`.
- Local trailing slash cannot help. SCP may add `/` in error text even when caller
  omitted it.

```sh
mkdir -p ./downloads
blacksmith testbox download --id <tbx_id> screenshots/ ./downloads/
```

- Explicit destination: writes `./downloads/screenshots/`; omission can duplicate
  basename (`screenshots/screenshots/`).
- Reuse task-owned lease + existing key path (`--ssh-private-key` when needed).
- Verify downloaded tree + hashes; recheck workaround after CLI upgrades.
