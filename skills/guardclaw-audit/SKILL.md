---
name: guardclaw-audit
description: "Cryptographically logs and verifies autonomous agent tool executions into a tamper-evident, Ed25519 hash-chained GEF ledger."
---

# GuardClaw Cryptographic Execution Audit

Best-effort local-only cryptographic flight recorder for OpenClaw agents. Use during autonomous coding, terminal commands, file mutations, or database operations to produce offline-verifiable proof that agent actions were unaltered.

## Contract & Safety Boundaries

- **Zero Network Egress**: Key generation, hashing, and verification operate 100% offline. No telemetry, network requests, or cloud dependencies are invoked.
- **RFC 8785 Canonicalization**: JSON payloads are normalized using RFC 8785 (JSON Canonicalization Scheme) prior to hashing.
- **SHA-256 Causal Chaining**: Every execution record incorporates the SHA-256 hash of the preceding record envelope.
- **Credential & Secret Redaction**: Secrets, authorization tokens, API keys, and environment variables must be scrubbed before logging.
- **Non-Privileged Execution**: Operates strictly within user-designated storage paths without requiring elevated or root system privileges.
- **Offline Verifiable**: Any user or CI process can verify chain integrity using `guardclaw verify <DIR> --pinned-key <KEY>`.

## Inputs & Outputs

- **Inputs**: Tool name (`str`), payload/parameters (`dict`), local storage directory (`Path`).
- **Outputs**: Append-only `ledger.jsonl` with detached Ed25519 signatures and causal hash chains.
- **Failure Modes**: Missing keys or corrupted entries yield `INVALID` during verification; runtime emission failures log warnings without blocking foreground agent workflows.

## Quickstart

Install the lightweight audit library (pinned release):

```bash
pip install "guardclaw==0.8.2"
```

### 1. Emit Signed Intent & Execution Receipts

```python
from pathlib import Path
from guardclaw import GEFLedger, Ed25519KeyManager, RecordType

# 1. Load or persist trusted signing key outside the audited directory
trusted_key_dir = Path.home() / ".openclaw" / "keys"
trusted_key_dir.mkdir(parents=True, exist_ok=True)
key_file = trusted_key_dir / "agent_signing_key.json"

if key_file.exists():
    key_mgr = Ed25519KeyManager.load(str(key_file))
else:
    key_mgr = Ed25519KeyManager.generate()
    key_mgr.save(str(key_file))

# Store the expected public key in a secure, trusted configuration location
trusted_pubkey = key_mgr.public_key_hex

# 2. Initialize ledger
ledger = GEFLedger(
    key_manager=key_mgr,
    agent_id="openclaw-agent",
    ledger_path="./.agent_audit",
)

# Record intent before running a high-stakes command
intent = ledger.emit(
    record_type=RecordType.TOOL_CALL,
    payload={
        "tool": "terminal.execute",
        "command": "git push origin main",
        "purpose": "Deploying release candidate",
    },
)

# Record result after execution
ledger.emit(
    record_type=RecordType.TOOL_RESULT,
    payload={
        "tool": "terminal.execute",
        "status": "success",
        "intent_record_id": intent.record_id,
    },
)
```

### 2. Verify Ledger Integrity Against Pinned Signer

Verify from the command line:

```bash
guardclaw verify ./.agent_audit --pinned-key "$TRUSTED_PUBKEY"
```

Or verify in Python against the pinned trusted public key:

```python
from pathlib import Path
from guardclaw import verify_ledger, Ed25519KeyManager

# 1. Load expected public key from trusted location (outside audited directory)
trusted_key_file = Path.home() / ".openclaw" / "keys" / "agent_signing_key.json"
key_mgr = Ed25519KeyManager.load(str(trusted_key_file))
trusted_pubkey = key_mgr.public_key_hex

# 2. Verify ledger integrity against anchored identity
summary = verify_ledger("./.agent_audit")

if summary["chain_valid"] and summary.get("signer_public_key") == trusted_pubkey:
    print(f"Verified {summary['verified_count']} records with zero tampering from trusted agent.")
else:
    print(f"Verification failed or untrusted signer: {summary.get('failure_detail')}")
```
