# Lease lifetime and cleanup

Read after [routing and authorization](../SKILL.md).

- For ordinary provisioned/direct leases, TTL counts from creation, including
  hydration; idle timeout counts inactivity once ready. Registered broker leases
  and delegated/native routes retain their own lifetime contract.
  Earlier deadline wins. Defaults: 30m each, 4h maximum. Owner/org overrides can
  allow up to 24h; use effective policy and sanitized clamp notices, not requested
  durations. Policy tightening also applies to live leases.
- `--keep` and `stop: never` do not prevent expiry. Request explicit bounded TTL
  and idle for retained direct leases. Plain heartbeat, setup, sync, SSH, and
  desktop use do not extend total TTL; `run` requests bounded auto-extension only
  while a command executes, within policy, budget, and provider capability.
- Before long source-dependent work, inspect remaining total lifetime. If allowed,
  request one bounded `extend <id> --ttl <desired-total> --json`; extension does
  not reset idle. Denied/budget/unsupported/nonadvancing/inactive outcomes require
  a visible skip or failure, never provider switching or infinite lease chains.
  Creation-fixed providers such as Daytona need enough TTL at allocation.
- Direct guest-refresh failure can leave a longer provider deadline with the old
  on-box deadline. Keep the same local state and retry the original arguments,
  including the same fixed total TTL and reason, only to reconcile; do not treat the failed extension as protection.
- Honor trusted `directLeases: deny`, operator-owned `directLeaseAllow`, and the
  native exemptions for local-only backends. A denied provider
  requires the configured coordinator route; never bypass with direct credentials.
  Testbox retains its native job and idle limits;
  `--ttl` does not extend a delegated workflow.
- `list` shows live coordinator leases; `list --retained` adds kept terminal
  resources whose cleanup is unconfirmed. Use exact-ID inspect/stop for recovery.
  Retain claims and recovery state until a blocking stop confirms completion.

## Source

Portable guidance reconciled from `openclaw/openclaw` at
`0edb7c507f91849570c45158a165f26ecd605698`, `.agents/skills/crabbox/`.
Its [MIT license](../LICENSE) stays with this bundle. Consumer-specific wrapper
contracts remain in the consumer repository.
