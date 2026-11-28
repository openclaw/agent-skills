# Untrusted AWS

- Use only when AWS semantics required or explicitly requested + lease immediately
  available. Otherwise: secretless fork CI. Never escalate providers.

- Clean trusted default-branch checkout. Installed trusted Crabbox binary.
- Fresh lease per reviewed full head SHA. No instance role, Tailscale, hydration.
- Only `CI` forwarded. Trusted bootstrap uploaded beside `--fresh-pr`.

```sh
cd <clean-trusted-default-branch-checkout>
env -u CRABBOX_AWS_INSTANCE_PROFILE \
  "$CRABBOX" config show --json | \
  jq -e '.aws.instanceProfile == ""' >/dev/null

env -u CRABBOX_AWS_INSTANCE_PROFILE \
  -u CRABBOX_TAILSCALE \
  -u CRABBOX_TAILSCALE_AUTH_KEY \
  -u CRABBOX_TAILSCALE_AUTH_KEY_ENV \
  -u CRABBOX_TAILSCALE_EXIT_NODE \
  -u CRABBOX_TAILSCALE_EXIT_NODE_ALLOW_LAN_ACCESS \
  -u CRABBOX_TAILSCALE_HOSTNAME_TEMPLATE \
  -u CRABBOX_TAILSCALE_TAGS \
  "$CRABBOX" warmup \
  --provider aws --network public --tailscale=false \
  --tailscale-exit-node= \
  --tailscale-exit-node-allow-lan-access=false \
  --ttl 4h --idle-timeout 90m --keep --timing-json

"$CRABBOX" inspect --provider aws --id <cbx_id> --json | \
  jq -e '.network == "public" and .tailscale == null' >/dev/null

env -u CRABBOX_AWS_INSTANCE_PROFILE \
  CRABBOX_ENV_ALLOW=CI \
  "$CRABBOX" run \
  --provider aws --id <cbx_id> \
  --fresh-pr <owner/repo#number> \
  --no-hydrate --timing-json \
  --script <trusted-bootstrap-script> -- \
  <expected_full_head_sha> <check-command>

env -u CRABBOX_AWS_INSTANCE_PROFILE \
  "$CRABBOX" stop --provider aws <cbx_id>
```

- Consumer-owned bootstrap: prove IMDSv2 IAM credential endpoint returns 404;
  verify full SHA; remove inherited runtime injection variables; pin repository
  toolchain; isolate `HOME`; install; test.

- Head moved: stop + rewarm. No reuse across revisions.
- No remote PR or no-role proof unavailable: secretless fork CI. No exceptions.
